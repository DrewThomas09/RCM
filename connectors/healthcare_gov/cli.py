"""CLI for the data.healthcare.gov connector.

Stdlib ``argparse`` only, mirroring the rest of the estate's CLIs.
Subcommands::

    python -m connectors.healthcare_gov.cli datasets
    python -m connectors.healthcare_gov.cli discover      [--db PATH]
    python -m connectors.healthcare_gov.cli fetch --dataset <key-or-DKAN-id>
                                          [--filter k=v ...] [--max-pages N]
                                          [--page-size N] [--offset N] [--db PATH]
    python -m connectors.healthcare_gov.cli catalog-search --q TEXT [--db PATH]
    python -m connectors.healthcare_gov.cli query <dataset_id> [--filter f=v ...]
                                          [--select c,c] [--sort -c] [--limit N]
    python -m connectors.healthcare_gov.cli lookup-plan   <plan_id>  [--db PATH]
    python -m connectors.healthcare_gov.cli lookup-county <fips>     [--db PATH]
    python -m connectors.healthcare_gov.cli serve [--host H] [--port P] [--db PATH]

``--db`` is the SQLite path and defaults to ``:memory:`` (handy for
smoke tests; point it at a file to keep data between commands).
``fetch --dataset`` accepts a curated endpoint key (see ``datasets``) or
any DKAN dataset identifier from the catalog — unknown keys fall through
to the generic ``healthcare_gov_rows`` path, so every one of the
catalog's datasets is one command away. Fetch pulls at most
``--max-pages`` pages (default 5 × 500 rows) per invocation — a
deliberate politeness cap; repeat with ``--offset`` (the printed
``next_offset``) or a larger ``--max-pages`` to go deeper.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from .connector import HealthcareGovConnector
from .endpoints import ENDPOINTS
from .lookup import lookup_county_plans, lookup_marketplace_plan
from .query import QueryError, aggregate, query
from .registry import registry_as_dicts
from .tables import HealthcareGovStore


def _store(db: str) -> HealthcareGovStore:
    return HealthcareGovStore(db)


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _filters(pairs: Optional[List[str]]) -> Optional[Dict[str, Any]]:
    filters: Dict[str, Any] = {}
    for f in pairs or []:
        if "=" not in f:
            raise SystemExit(
                f"bad --filter {f!r}; expected field=value or field__op=value")
        k, v = f.split("=", 1)
        filters[k] = v
    return filters


def cmd_datasets(_args: argparse.Namespace) -> int:
    _print(registry_as_dicts())
    return 0


def cmd_discover(args: argparse.Namespace) -> int:
    """Sync the full DKAN catalog into ``healthcare_gov_catalog``."""
    store = _store(args.db)
    conn = HealthcareGovConnector()
    summary = conn.refresh(store, "catalog")
    summary["table_count"] = store.count("healthcare_gov_catalog")
    _print(summary)
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    store = _store(args.db)
    conn = HealthcareGovConnector()
    filters = _filters(args.filter)
    kw: Dict[str, Any] = dict(max_pages=args.max_pages,
                              page_size=args.page_size,
                              start_offset=args.offset)
    if args.dataset in ENDPOINTS and args.dataset != "fetched_rows":
        summary = conn.refresh(store, args.dataset, filters, **kw)
    else:
        # Anything else is treated as a DKAN identifier → generic rows.
        summary = conn.refresh_dataset(store, args.dataset, filters, **kw)
    _print(summary)
    return 0


def cmd_catalog_search(args: argparse.Namespace) -> int:
    """Substring search over the locally synced catalog (run discover first)."""
    store = _store(args.db)
    needle = f"%{args.q}%"
    rows = [dict(r) for r in store.fetchall(
        "SELECT identifier, title, modified, accrual_periodicity, format, "
        "download_url FROM healthcare_gov_catalog "
        "WHERE title LIKE ? OR description LIKE ? OR keyword LIKE ? "
        "ORDER BY modified DESC LIMIT ?",
        (needle, needle, needle, max(1, args.limit)))]
    _print({"q": args.q, "count": len(rows), "rows": rows})
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    store = _store(args.db)
    select = args.select.split(",") if args.select else None
    sort = args.sort.split(",") if args.sort else None
    try:
        res = query(store, args.dataset, filters=_filters(args.filter),
                    select=select, sort=sort, limit=args.limit,
                    offset=args.offset)
    except QueryError as exc:
        print(f"query error: {exc}", file=sys.stderr)
        return 2
    _print(res.as_dict())
    return 0


def cmd_aggregate(args: argparse.Namespace) -> int:
    store = _store(args.db)
    try:
        res = aggregate(store, args.dataset, group_by=args.group_by.split(","),
                        filters=_filters(args.filter),
                        metrics=args.metric, limit=args.limit)
    except QueryError as exc:
        print(f"aggregate error: {exc}", file=sys.stderr)
        return 2
    _print(res.as_dict())
    return 0


def cmd_lookup_plan(args: argparse.Namespace) -> int:
    _print(lookup_marketplace_plan(_store(args.db), args.plan_id))
    return 0


def cmd_lookup_county(args: argparse.Namespace) -> int:
    _print(lookup_county_plans(_store(args.db), args.fips))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .api_server import serve
    serve(args.db, host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="connectors.healthcare_gov.cli",
        description="data.healthcare.gov (DKAN Marketplace catalog) connector")
    p.add_argument("--db", default=":memory:",
                   help="SQLite db path (default :memory:)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("datasets").set_defaults(func=cmd_datasets)
    sub.add_parser("discover").set_defaults(func=cmd_discover)

    f = sub.add_parser("fetch")
    f.add_argument("--dataset", required=True,
                   help="endpoint key (see `datasets`) or any DKAN dataset id")
    f.add_argument("--filter", action="append",
                   help="equality filter field=value (repeatable)")
    f.add_argument("--max-pages", type=int, default=None,
                   help="pages of 500 to pull this run (default 5)")
    f.add_argument("--page-size", type=int, default=None,
                   help="rows per page, max 500 (DKAN hard cap)")
    f.add_argument("--offset", type=int, default=0,
                   help="resume offset from a previous run's next_offset")
    f.set_defaults(func=cmd_fetch)

    cs = sub.add_parser("catalog-search")
    cs.add_argument("--q", required=True)
    cs.add_argument("--limit", type=int, default=25)
    cs.set_defaults(func=cmd_catalog_search)

    q = sub.add_parser("query")
    q.add_argument("dataset")
    q.add_argument("--filter", action="append")
    q.add_argument("--select")
    q.add_argument("--sort")
    q.add_argument("--limit", type=int, default=50)
    q.add_argument("--offset", type=int, default=0)
    q.set_defaults(func=cmd_query)

    agg = sub.add_parser("aggregate")
    agg.add_argument("dataset")
    agg.add_argument("--group-by", required=True, help="comma-separated columns")
    agg.add_argument("--filter", action="append")
    agg.add_argument("--metric", action="append",
                     help="func:field metric (sum/avg/min/max; repeatable)")
    agg.add_argument("--limit", type=int, default=50)
    agg.set_defaults(func=cmd_aggregate)

    lp = sub.add_parser("lookup-plan")
    lp.add_argument("plan_id")
    lp.set_defaults(func=cmd_lookup_plan)

    lc = sub.add_parser("lookup-county")
    lc.add_argument("fips")
    lc.set_defaults(func=cmd_lookup_county)

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
