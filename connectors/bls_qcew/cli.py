"""CLI for the BLS QCEW connector.

Stdlib ``argparse`` only, mirroring the rest of RCM-MC's CLIs. The
storage flag is a single GLOBAL ``--db PATH`` (the estate refresh
driver assumes this shape for new connectors)::

    python -m connectors.bls_qcew.cli [--db PATH] datasets
    python -m connectors.bls_qcew.cli [--db PATH] discover
    python -m connectors.bls_qcew.cli [--db PATH] fetch
        --dataset industry_area --industry 622 --year 2024 --qtr 1
        [--max-rows N | --full]
    python -m connectors.bls_qcew.cli [--db PATH] fetch
        --dataset area_industry --area 48453 [--year Y --qtr Q]
    python -m connectors.bls_qcew.cli [--db PATH] query <dataset_id>
        [--filter f=v ...] [--select c,c] [--sort -c] [--limit N]
    python -m connectors.bls_qcew.cli [--db PATH] lookup-labor-market 48453
    python -m connectors.bls_qcew.cli [--db PATH] lookup-industry-employment 622
    python -m connectors.bls_qcew.cli [--db PATH] serve [--host H] [--port P]

``--db`` defaults to ``:memory:`` — handy for smoke tests, but pass a
file path when you want ``fetch`` output to persist for
``query``/``lookup-*``/``serve``.

``fetch`` defaults to the pinned latest published quarter (2025 Q4,
verified live 2026-07-06) and the dataset's default slice code (NAICS
62 for ``industry_area``, US000 for ``area_industry``) when the flags
are omitted.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from .connector import DEFAULT_MAX_ROWS, BlsQcewConnector
from .endpoints import ENDPOINTS, get_endpoint
from .lookup import lookup_industry_employment, lookup_labor_market
from .query import QueryError, aggregate, query
from .registry import registry_as_dicts
from .tables import BlsQcewStore


def _store(args: argparse.Namespace) -> BlsQcewStore:
    return BlsQcewStore(args.db)


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _dataset_key(raw: str) -> str:
    """Accept both the short key and the fully-prefixed dataset id."""
    key = raw.strip()
    if key.startswith("bls_qcew_"):
        key = key[len("bls_qcew_"):]
    return key


def cmd_datasets(_args: argparse.Namespace) -> int:
    _print(registry_as_dicts())
    return 0


def cmd_discover(_args: argparse.Namespace) -> int:
    _print([{"key": s.key, "dataset_id": s.dataset_id,
             "slice_kind": s.slice_kind, "path_template": s.path_template,
             "default_params": dict(s.default_params),
             "target_table": s.target_table,
             "refresh_cadence": s.refresh_cadence}
            for s in BlsQcewConnector().discover()])
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    key = _dataset_key(args.dataset)
    if key not in ENDPOINTS:
        print(f"unknown dataset {args.dataset!r}; known: {sorted(ENDPOINTS)}",
              file=sys.stderr)
        return 2
    spec = get_endpoint(key)
    # Route the slice-code flags: --industry belongs to industry_area,
    # --area to area_industry. Passing the wrong one is an error, not a
    # silent fetch of the default slice.
    params: Dict[str, Any] = {}
    for flag, value in (("industry", args.industry), ("area", args.area)):
        if value is None:
            continue
        if flag != spec.code_param:
            print(f"--{flag} does not apply to dataset {key!r} "
                  f"(it takes --{spec.code_param})", file=sys.stderr)
            return 2
        params[flag] = value
    if args.year is not None:
        params["year"] = args.year
    if args.qtr is not None:
        params["qtr"] = args.qtr
    max_rows: Optional[int] = None if args.full else args.max_rows
    store = _store(args)
    conn = BlsQcewConnector()
    try:
        counts = conn.refresh(store, key, params, max_rows=max_rows)
    except ValueError as exc:  # pre-network validation (bad year/qtr/code)
        print(str(exc), file=sys.stderr)
        return 2
    counts["table_totals"] = {spec.target_table:
                              store.count(spec.target_table)}
    _print(counts)
    store.close()
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    store = _store(args)
    filters: Dict[str, Any] = {}
    for f in args.filter or []:
        if "=" not in f:
            print(f"bad --filter {f!r}; expected field=value or "
                  f"field__op=value", file=sys.stderr)
            return 2
        k, v = f.split("=", 1)
        filters[k] = v
    select = args.select.split(",") if args.select else None
    sort = args.sort.split(",") if args.sort else None
    try:
        res = query(store, args.dataset, filters=filters, select=select,
                    sort=sort, limit=args.limit, offset=args.offset)
    except QueryError as exc:
        print(f"query error: {exc}", file=sys.stderr)
        return 2
    _print(res.as_dict())
    return 0

def cmd_aggregate(args: argparse.Namespace) -> int:
    store = _store(args)
    filters: Dict[str, Any] = {}
    for f in args.filter or []:
        if "=" not in f:
            print(f"bad --filter {f!r}; expected field=value or "
                  f"field__op=value", file=sys.stderr)
            return 2
        k, v = f.split("=", 1)
        filters[k] = v
    try:
        res = aggregate(store, args.dataset, group_by=args.group_by.split(","),
                        filters=filters, metrics=args.metric, limit=args.limit)
    except QueryError as exc:
        print(f"aggregate error: {exc}", file=sys.stderr)
        return 2
    _print(res.as_dict())
    return 0


def cmd_lookup_labor_market(args: argparse.Namespace) -> int:
    _print(lookup_labor_market(_store(args), args.area_fips,
                               args.year, args.qtr, args.limit))
    return 0


def cmd_lookup_industry_employment(args: argparse.Namespace) -> int:
    _print(lookup_industry_employment(_store(args), args.naics,
                                      args.year, args.qtr, args.limit))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .api_server import serve
    serve(args.db, host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="connectors.bls_qcew.cli",
        description="BLS Quarterly Census of Employment & Wages "
                    "(open CSV slice API) connector")
    p.add_argument("--db", default=":memory:",
                   help="SQLite db path (default :memory:)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("datasets").set_defaults(func=cmd_datasets)
    sub.add_parser("discover").set_defaults(func=cmd_discover)

    f = sub.add_parser("fetch")
    f.add_argument("--dataset", required=True,
                   help=f"one of {sorted(ENDPOINTS)} (bls_qcew_ prefix ok)")
    f.add_argument("--industry",
                   help="NAICS code for industry_area (e.g. 62, 621, 622, "
                        "623, 6216); defaults to 62")
    f.add_argument("--area",
                   help="QCEW area code for area_industry (e.g. 48453, "
                        "48000, C4266, US000); defaults to US000")
    f.add_argument("--year", type=int,
                   help="4-digit year (defaults to the pinned latest "
                        "published year)")
    f.add_argument("--qtr",
                   help="quarter 1-4 (defaults to the pinned latest "
                        "published quarter)")
    f.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS,
                   help=f"row cap per slice (default {DEFAULT_MAX_ROWS})")
    f.add_argument("--full", action="store_true",
                   help="ingest the whole slice (ignores --max-rows)")
    f.set_defaults(func=cmd_fetch)

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

    lm = sub.add_parser("lookup-labor-market")
    lm.add_argument("area_fips")
    lm.add_argument("--year")
    lm.add_argument("--qtr")
    lm.add_argument("--limit", type=int, default=25)
    lm.set_defaults(func=cmd_lookup_labor_market)

    ie = sub.add_parser("lookup-industry-employment")
    ie.add_argument("naics")
    ie.add_argument("--year")
    ie.add_argument("--qtr")
    ie.add_argument("--limit", type=int, default=25)
    ie.set_defaults(func=cmd_lookup_industry_employment)

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
