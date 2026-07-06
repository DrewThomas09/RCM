"""CLI for the cdc_data (data.cdc.gov Socrata SODA) connector.

Stdlib ``argparse`` only, mirroring the rest of RCM-MC's CLIs.
Subcommands::

    python -m connectors.cdc_data.cli datasets
    python -m connectors.cdc_data.cli discover [--max-pages N] [--page-size N]
    python -m connectors.cdc_data.cli fetch --dataset K [--filter f=v ...]
                                      [--where SOQL] [--max-pages N]
                                      [--page-size N]
    python -m connectors.cdc_data.cli query <dataset_id> [--filter f=v ...]
                                      [--select c,c] [--sort -c] [--limit N]
    python -m connectors.cdc_data.cli catalog-search --q TEXT [--limit N]
    python -m connectors.cdc_data.cli lookup-county-health <fips>
    python -m connectors.cdc_data.cli lookup-cdc-dataset <4x4>
    python -m connectors.cdc_data.cli serve [--host H] [--port P]

``--db`` names the SQLite file and defaults to ``:memory:`` — handy for
smoke runs (fetch + report counts, nothing persisted); point it at a
real path to build a durable slice. ``fetch --dataset`` accepts a
curated key (``places_county``), a full dataset id
(``cdc_data_places_county``), ``catalog``, or ANY raw 4x4 id (which
lands in the generic ``cdc_data_rows`` table).
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from .connector import CdcDataConnector
from .lookup import lookup_cdc_dataset, lookup_county_health
from .query import QueryError, query
from .registry import registry_as_dicts
from .tables import CdcDataStore


def _store(args: argparse.Namespace) -> CdcDataStore:
    return CdcDataStore(args.db)


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
    conn = CdcDataConnector()
    rows = conn.discover(store=store, max_pages=args.max_pages,
                         page_size=args.page_size)
    _print({
        "datasets_in_catalog": len(rows),
        "cdc_data_catalog_rows": store.count("cdc_data_catalog"),
        "sample": [{"dataset_uid": r["dataset_uid"], "name": r["name"],
                    "category": r["category"]} for r in rows[:5]],
    })
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    store = _store(args)
    conn = CdcDataConnector()
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
    fast and works offline once the catalog is synced.
    """
    store = _store(args)
    if store.count("cdc_data_catalog") == 0:
        print("catalog is empty — run `discover` first to sync it",
              file=sys.stderr)
        return 2
    needle = f"%{args.q}%"
    rows = store.fetchall(
        "SELECT dataset_uid, name, category, data_updated_at, data_uri "
        "FROM cdc_data_catalog "
        "WHERE name LIKE ? OR description LIKE ? OR category LIKE ? "
        "ORDER BY data_updated_at DESC LIMIT ?",
        (needle, needle, needle, args.limit))
    _print({"q": args.q, "count": len(rows), "results": [dict(r) for r in rows]})
    return 0


def cmd_lookup_county_health(args: argparse.Namespace) -> int:
    _print(lookup_county_health(_store(args), args.fips))
    return 0


def cmd_lookup_cdc_dataset(args: argparse.Namespace) -> int:
    _print(lookup_cdc_dataset(_store(args), args.dataset_uid))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .api_server import serve
    serve(args.db, host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="connectors.cdc_data.cli",
        description="data.cdc.gov (Socrata SODA) connector")
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
                   help="endpoint key, cdc_data_* id, or a raw 4x4")
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
    cs.set_defaults(func=cmd_catalog_search)

    lch = sub.add_parser("lookup-county-health")
    lch.add_argument("fips")
    lch.set_defaults(func=cmd_lookup_county_health)

    lcd = sub.add_parser("lookup-cdc-dataset")
    lcd.add_argument("dataset_uid")
    lcd.set_defaults(func=cmd_lookup_cdc_dataset)

    srv = sub.add_parser("serve")
    srv.add_argument("--host", default="127.0.0.1")
    srv.add_argument("--port", type=int, default=8099)
    srv.set_defaults(func=cmd_serve)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
