"""CLI for the Census ACS connector.

Stdlib ``argparse`` only, mirroring the rest of RCM-MC's CLIs.
Subcommands::

    python -m connectors.census_acs.cli datasets
    python -m connectors.census_acs.cli discover
    python -m connectors.census_acs.cli fetch --dataset county_profile
                                          [--year 2023] [--state 48] [--db PATH]
    python -m connectors.census_acs.cli query <dataset_id> [--filter f=v ...]
                                          [--select c,c] [--sort -c] [--limit N]
    python -m connectors.census_acs.cli lookup-county 48201  [--db PATH]
    python -m connectors.census_acs.cli lookup-state  48     [--db PATH]
    python -m connectors.census_acs.cli serve [--host H] [--port P] [--db PATH]

``--db`` defaults to ``:memory:`` — handy for a smoke fetch (counts print
either way); point it at a file to persist between ``fetch`` and
``serve``/``query``. Live fetches need ``$CENSUS_API_KEY`` (the API
requires a key on every data request; free signup at
https://api.census.gov/data/key_signup.html).
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from .connector import CensusAcsConnector
from .endpoints import DEFAULT_YEAR
from .lookup import lookup_county_demographics, lookup_state_demographics
from .query import QueryError, aggregate, query
from .registry import registry_as_dicts
from .tables import CensusAcsStore
from .transport import CensusAcsApiError


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def cmd_datasets(_args: argparse.Namespace) -> int:
    _print(registry_as_dicts())
    return 0


def cmd_discover(_args: argparse.Namespace) -> int:
    conn = CensusAcsConnector()
    _print([{"key": s.key, "dataset_id": s.dataset_id, "geo_for": s.geo_for,
             "target_table": s.target_table, "join_keys": list(s.join_keys),
             "refresh_cadence": s.refresh_cadence,
             "supports_state_filter": s.supports_in_state or s.key == "state_profile"}
            for s in conn.discover()])
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    store = CensusAcsStore(args.db)
    conn = CensusAcsConnector()
    try:
        summary = conn.refresh(store, args.dataset,
                               year=args.year, state=args.state)
    except (CensusAcsApiError, ValueError, KeyError) as exc:
        print(f"fetch error: {exc}", file=sys.stderr)
        return 2
    finally:
        store.close()
    _print(summary)
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    store = CensusAcsStore(args.db)
    filters: Dict[str, Any] = {}
    for f in args.filter or []:
        if "=" not in f:
            print(f"bad --filter {f!r}; expected field=value or field__op=value",
                  file=sys.stderr)
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
    finally:
        store.close()
    _print(res.as_dict())
    return 0

def cmd_aggregate(args: argparse.Namespace) -> int:
    store = CensusAcsStore(args.db)
    filters: Dict[str, Any] = {}
    for f in args.filter or []:
        if "=" not in f:
            print(f"bad --filter {f!r}; expected field=value or field__op=value",
                  file=sys.stderr)
            return 2
        k, v = f.split("=", 1)
        filters[k] = v
    try:
        res = aggregate(store, args.dataset, group_by=args.group_by.split(","),
                        filters=filters, metrics=args.metric, limit=args.limit)
    except QueryError as exc:
        print(f"aggregate error: {exc}", file=sys.stderr)
        return 2
    finally:
        store.close()
    _print(res.as_dict())
    return 0


def cmd_lookup_county(args: argparse.Namespace) -> int:
    store = CensusAcsStore(args.db)
    try:
        _print(lookup_county_demographics(store, args.fips5))
    finally:
        store.close()
    return 0


def cmd_lookup_state(args: argparse.Namespace) -> int:
    store = CensusAcsStore(args.db)
    try:
        _print(lookup_state_demographics(store, args.fips2))
    finally:
        store.close()
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .api_server import serve
    serve(args.db, host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="connectors.census_acs.cli",
        description="US Census ACS 5-year demographic profiles connector")
    p.add_argument("--db", default=":memory:",
                   help="SQLite db path (default :memory:)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("datasets").set_defaults(func=cmd_datasets)
    sub.add_parser("discover").set_defaults(func=cmd_discover)

    f = sub.add_parser("fetch")
    f.add_argument("--dataset", required=True,
                   help="county_profile | state_profile | cbsa_profile "
                        "(census_acs_ prefix accepted)")
    f.add_argument("--year", type=int, default=DEFAULT_YEAR)
    f.add_argument("--state", default=None,
                   help="2-digit state FIPS filter (county/state profiles)")
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

    lc = sub.add_parser("lookup-county")
    lc.add_argument("fips5")
    lc.set_defaults(func=cmd_lookup_county)

    ls = sub.add_parser("lookup-state")
    ls.add_argument("fips2")
    ls.set_defaults(func=cmd_lookup_state)

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
