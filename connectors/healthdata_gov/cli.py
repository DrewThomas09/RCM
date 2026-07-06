"""CLI for the healthdata_gov (healthdata.gov Socrata SODA) connector.

Stdlib ``argparse`` only, mirroring the rest of RCM-MC's CLIs.
Subcommands::

    python -m connectors.healthdata_gov.cli datasets
    python -m connectors.healthdata_gov.cli discover [--max-pages N]
                                          [--page-size N]
    python -m connectors.healthdata_gov.cli fetch --dataset K [--filter f=v ...]
                                          [--where SOQL] [--max-pages N]
                                          [--page-size N]
    python -m connectors.healthdata_gov.cli query <dataset_id> [--filter f=v ...]
                                          [--select c,c] [--sort -c] [--limit N]
    python -m connectors.healthdata_gov.cli catalog-search --q TEXT [--limit N]
                                          [--hub-only] [--unattributed]
    python -m connectors.healthdata_gov.cli lookup-hhs-dataset <4x4>
    python -m connectors.healthdata_gov.cli lookup-hospital-capacity <ccn>
    python -m connectors.healthdata_gov.cli serve [--host H] [--port P]

``--db`` is a GLOBAL flag naming the SQLite file and defaults to
``:memory:`` — handy for smoke runs (fetch + report counts, nothing
persisted); point it at a real path to build a durable slice.

``fetch --dataset`` accepts a curated key (``hospital_ids``), a full
dataset id (``healthdata_gov_hospital_ids``), ``catalog``, or ANY raw
4x4 id (which lands in the generic ``healthdata_gov_rows`` table).
``--max-pages`` defaults to 5 as a politeness guard: the facility
capacity file alone is ~1M rows, and a full drain must be an explicit
choice.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from .connector import HealthdataGovConnector
from .lookup import lookup_hhs_dataset, lookup_hospital_capacity
from .query import QueryError, query
from .registry import registry_as_dicts
from .tables import HealthdataGovStore


def _store(args: argparse.Namespace) -> HealthdataGovStore:
    return HealthdataGovStore(args.db)


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _parse_filters(pairs: Optional[List[str]]) -> Optional[Dict[str, Any]]:
    filters: Dict[str, Any] = {}
    for f in pairs or []:
        if "=" not in f:
            raise SystemExit(
                f"bad --filter {f!r}; expected field=value or field__op=value")
        k, v = f.split("=", 1)
        filters[k] = v
    return filters or None


def cmd_datasets(_args: argparse.Namespace) -> int:
    _print(registry_as_dicts())
    return 0


def cmd_discover(args: argparse.Namespace) -> int:
    store = _store(args)
    conn = HealthdataGovConnector()
    rows = conn.discover(store=store, max_pages=args.max_pages,
                         page_size=args.page_size)
    # Verified live: datahub.hhs.gov = HHS's own hub records (the class
    # whose tabular assets serve rows here); healthdata.gov = copies
    # federated in from state/city portals (403 on /resource/).
    hub = sum(1 for r in rows if r.get("domain") == "datahub.hhs.gov")
    _print({
        "datasets_in_catalog": len(rows),
        "hhs_hub_records": hub,
        "state_portal_copies": len(rows) - hub,
        "healthdata_gov_catalog_rows": store.count("healthdata_gov_catalog"),
        "sample": [{"dataset_uid": r["dataset_uid"], "name": r["name"],
                    "domain": r["domain"], "attribution": r["attribution"]}
                   for r in rows[:5]],
    })
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    store = _store(args)
    conn = HealthdataGovConnector()
    params: Dict[str, Any] = _parse_filters(args.filter) or {}
    if args.where:
        params["$where"] = args.where
    result = conn.refresh(store, args.dataset, params or None,
                          max_pages=args.max_pages, page_size=args.page_size)
    _print(result)
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    store = _store(args)
    select = args.select.split(",") if args.select else None
    sort = args.sort.split(",") if args.sort else None
    try:
        res = query(store, args.dataset, filters=_parse_filters(args.filter),
                    select=select, sort=sort, limit=args.limit,
                    offset=args.offset)
    except QueryError as exc:
        print(f"query error: {exc}", file=sys.stderr)
        return 2
    _print(res.as_dict())
    return 0


def cmd_catalog_search(args: argparse.Namespace) -> int:
    """LIKE-search the locally synced catalog by name/description/category.

    Purely local (run ``discover`` first) — no API round-trip, so it is
    fast and works offline once the catalog is synced. ``--hub-only``
    restricts to HHS's own hub records (``domain=datahub.hhs.gov`` —
    verified live as the class containing every row-serving native
    dataset), excluding the 2,500 copies federated in from state/city
    portals; ``--unattributed`` additionally drops hub records whose
    ``attribution`` names another portal (href mirrors of data.cdc.gov,
    data.medicaid.gov, … that other estate connectors already cover).
    """
    store = _store(args)
    if store.count("healthdata_gov_catalog") == 0:
        print("catalog is empty — run `discover` first to sync it",
              file=sys.stderr)
        return 2
    needle = f"%{args.q}%"
    sql = ("SELECT dataset_uid, name, category, domain, attribution, "
           "data_updated_at, data_uri FROM healthdata_gov_catalog "
           "WHERE (name LIKE ? OR description LIKE ? OR category LIKE ?)")
    params: List[Any] = [needle, needle, needle]
    if args.hub_only or args.unattributed:
        sql += " AND domain = 'datahub.hhs.gov'"
    if args.unattributed:
        sql += (" AND (attribution IS NULL OR attribution = '' "
                "OR attribution LIKE '%Health & Human Services%')")
    sql += " ORDER BY data_updated_at DESC LIMIT ?"
    params.append(args.limit)
    rows = store.fetchall(sql, params)
    _print({"q": args.q, "count": len(rows), "results": [dict(r) for r in rows]})
    return 0


def cmd_lookup_hhs_dataset(args: argparse.Namespace) -> int:
    _print(lookup_hhs_dataset(_store(args), args.dataset_uid))
    return 0


def cmd_lookup_hospital_capacity(args: argparse.Namespace) -> int:
    _print(lookup_hospital_capacity(_store(args), args.ccn))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .api_server import serve
    serve(args.db, host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="connectors.healthdata_gov.cli",
        description="healthdata.gov (HHS Socrata meta-catalog) connector")
    p.add_argument("--db", default=":memory:",
                   help="SQLite db path (default :memory:)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("datasets").set_defaults(func=cmd_datasets)

    d = sub.add_parser("discover")
    d.add_argument("--max-pages", type=int, default=None)
    d.add_argument("--page-size", type=int, default=None)
    d.set_defaults(func=cmd_discover)

    f = sub.add_parser("fetch")
    f.add_argument("--dataset", required=True,
                   help="endpoint key, healthdata_gov_* id, or a raw 4x4")
    f.add_argument("--filter", action="append",
                   help="column=value SoQL equality (repeatable)")
    f.add_argument("--where", help="raw SoQL $where clause")
    f.add_argument("--max-pages", type=int, default=None)
    f.add_argument("--page-size", type=int, default=None)
    f.set_defaults(func=cmd_fetch)

    q = sub.add_parser("query")
    q.add_argument("dataset")
    q.add_argument("--filter", action="append")
    q.add_argument("--select")
    q.add_argument("--sort")
    q.add_argument("--limit", type=int, default=50)
    q.add_argument("--offset", type=int, default=0)
    q.set_defaults(func=cmd_query)

    cs = sub.add_parser("catalog-search")
    cs.add_argument("--q", required=True)
    cs.add_argument("--limit", type=int, default=20)
    cs.add_argument("--hub-only", action="store_true",
                    help="only HHS hub records (domain=datahub.hhs.gov), "
                         "excluding state/city portal copies")
    cs.add_argument("--unattributed", action="store_true",
                    help="hub records not attributed to another portal — "
                         "the best in-catalog proxy for row-serving natives")
    cs.set_defaults(func=cmd_catalog_search)

    lhd = sub.add_parser("lookup-hhs-dataset")
    lhd.add_argument("dataset_uid")
    lhd.set_defaults(func=cmd_lookup_hhs_dataset)

    lhc = sub.add_parser("lookup-hospital-capacity")
    lhc.add_argument("ccn")
    lhc.set_defaults(func=cmd_lookup_hospital_capacity)

    srv = sub.add_parser("serve")
    srv.add_argument("--host", default="127.0.0.1")
    srv.add_argument("--port", type=int, default=8104)
    srv.set_defaults(func=cmd_serve)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
