"""CLI for the Open Payments connector.

Stdlib ``argparse`` only, mirroring the rest of RCM-MC's CLIs.
Subcommands::

    python -m connectors.open_payments.cli datasets
    python -m connectors.open_payments.cli discover        [--db PATH]
    python -m connectors.open_payments.cli fetch --dataset K
        [--state XX] [--npi N] [--filter f=v ...]
        [--max-pages N] [--page-size N] [--db PATH]
    python -m connectors.open_payments.cli query <dataset_id>
        [--filter f=v ...] [--select c,c] [--sort -c] [--limit N] [--db PATH]
    python -m connectors.open_payments.cli catalog-search --q TEXT [--db PATH]
    python -m connectors.open_payments.cli serve [--host H] [--port P] [--db PATH]

``--db`` defaults to ``:memory:`` — handy for smoke tests, but pass a
real path to keep what you ingest.

``fetch --dataset`` accepts a curated key (``general_payments_2024``),
a full dataset id (``open_payments_general_payments_2024``), or ANY
catalog UUID — unknown keys are treated as UUIDs and land in the generic
``open_payments_rows`` table, which is how older program years are
pulled without code changes.

SCALE NOTE: payment files exceed 15M rows/year, so ``fetch`` defaults to
3 pages × 500 rows and is meant to be filter-driven (``--state``,
``--npi``, ``--filter applicable_...name=...``). ``--state``/``--npi``
map onto the right native column per dataset (ownership rows key on
``physician_npi``, profiles on ``entity_npi``, ...).
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from .connector import DEFAULT_MAX_PAGES, PAGE_LIMIT, OpenPaymentsConnector
from .endpoints import ENDPOINTS
from .query import QueryError, aggregate, query
from .registry import registry_as_dicts
from .tables import OpenPaymentsStore

_PREFIX = "open_payments_"

# Fallback aliases when fetching an arbitrary catalog UUID (the payment
# detail files all share these native column names).
_GENERIC_ALIASES = {"state": "recipient_state", "npi": "covered_recipient_npi"}


def _print(obj: Any) -> int:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))
    return 0


def _err(msg: str) -> int:
    print(msg, file=sys.stderr)
    return 2


def _parse_filters(pairs: Optional[List[str]]) -> Optional[Dict[str, str]]:
    filters: Dict[str, str] = {}
    for f in pairs or []:
        if "=" not in f:
            raise ValueError(
                f"bad --filter {f!r}; expected field=value or field__op=value")
        k, v = f.split("=", 1)
        filters[k] = v
    return filters


def cmd_datasets(_args: argparse.Namespace) -> int:
    return _print(registry_as_dicts())


def cmd_discover(args: argparse.Namespace) -> int:
    """Sync the full DKAN catalog (~74 datasets) into the catalog table."""
    store = OpenPaymentsStore(args.db)
    try:
        counts = OpenPaymentsConnector().refresh(store, "catalog")
        return _print(counts)
    finally:
        store.close()


def cmd_fetch(args: argparse.Namespace) -> int:
    key = args.dataset
    if key.startswith(_PREFIX):
        key = key[len(_PREFIX):]
    try:
        filters = _parse_filters(args.filter) or {}
    except ValueError as exc:
        return _err(str(exc))

    spec = ENDPOINTS.get(key)
    if spec is not None and spec.kind == "generic":
        return _err("pass the target catalog UUID directly as --dataset; "
                    "'fetched_rows' is the landing table, not a fetchable id")
    aliases = spec.filter_aliases if spec is not None else _GENERIC_ALIASES
    for flag, value in (("state", args.state), ("npi", args.npi)):
        if value is None:
            continue
        col = aliases.get(flag)
        if col is None:
            return _err(f"--{flag} is not meaningful for dataset {key!r}")
        filters[col] = value

    store = OpenPaymentsStore(args.db)
    conn = OpenPaymentsConnector()
    try:
        if spec is None:
            # Not a curated key → treat as a catalog UUID (generic rows).
            counts = conn.refresh(store, "fetched_rows", filters,
                                  dataset_key=key, max_pages=args.max_pages,
                                  page_size=args.page_size)
        else:
            counts = conn.refresh(store, key, filters,
                                  max_pages=args.max_pages,
                                  page_size=args.page_size)
        return _print(counts)
    finally:
        store.close()


def cmd_query(args: argparse.Namespace) -> int:
    store = OpenPaymentsStore(args.db)
    try:
        filters = _parse_filters(args.filter)
    except ValueError as exc:
        store.close()
        return _err(str(exc))
    select = args.select.split(",") if args.select else None
    sort = args.sort.split(",") if args.sort else None
    try:
        res = query(store, args.dataset, filters=filters, select=select,
                    sort=sort, limit=args.limit, offset=args.offset)
        return _print(res.as_dict())
    except QueryError as exc:
        return _err(f"query error: {exc}")
    finally:
        store.close()

def cmd_aggregate(args: argparse.Namespace) -> int:
    store = OpenPaymentsStore(args.db)
    try:
        filters = _parse_filters(args.filter)
    except ValueError as exc:
        store.close()
        return _err(str(exc))
    try:
        res = aggregate(store, args.dataset, group_by=args.group_by.split(","),
                        filters=filters, metrics=args.metric, limit=args.limit)
        return _print(res.as_dict())
    except QueryError as exc:
        return _err(f"aggregate error: {exc}")
    finally:
        store.close()


def cmd_catalog_search(args: argparse.Namespace) -> int:
    """Find datasets in the synced catalog by title/description/keyword."""
    store = OpenPaymentsStore(args.db)
    try:
        if store.count("open_payments_catalog") == 0:
            return _err("catalog table is empty — run "
                        "`python -m connectors.open_payments.cli discover "
                        "--db <path>` first (use the same --db)")
        like = f"%{args.q}%"
        rows = store.fetchall(
            "SELECT identifier, title, theme, modified, temporal, api_url "
            "FROM open_payments_catalog "
            "WHERE title LIKE ? OR description LIKE ? OR keyword LIKE ? "
            "ORDER BY modified DESC LIMIT ?",
            (like, like, like, args.limit))
        return _print({"q": args.q, "count": len(rows),
                       "datasets": [dict(r) for r in rows]})
    finally:
        store.close()


def cmd_serve(args: argparse.Namespace) -> int:
    from .api_server import serve
    serve(args.db, host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="connectors.open_payments.cli",
        description="CMS Open Payments (Sunshine Act, DKAN) connector")
    # A parent parser so --db is accepted AFTER the subcommand (the
    # natural place to type it), on every verb that opens a store.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", default=":memory:",
                        help="SQLite db path (default :memory:)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("datasets").set_defaults(func=cmd_datasets)
    sub.add_parser("discover", parents=[common]).set_defaults(func=cmd_discover)

    f = sub.add_parser("fetch", parents=[common])
    f.add_argument("--dataset", required=True,
                   help="curated key, dataset id, or any catalog UUID")
    f.add_argument("--state", help="state filter (mapped per dataset)")
    f.add_argument("--npi", help="NPI filter (mapped per dataset)")
    f.add_argument("--filter", action="append",
                   help="native filter field=value (repeatable; field__op=value)")
    f.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    f.add_argument("--page-size", type=int, default=PAGE_LIMIT)
    f.set_defaults(func=cmd_fetch)

    q = sub.add_parser("query", parents=[common])
    q.add_argument("dataset")
    q.add_argument("--filter", action="append")
    q.add_argument("--select")
    q.add_argument("--sort")
    q.add_argument("--limit", type=int, default=50)
    q.add_argument("--offset", type=int, default=0)
    q.set_defaults(func=cmd_query)

    agg = sub.add_parser("aggregate", parents=[common])
    agg.add_argument("dataset")
    agg.add_argument("--group-by", required=True, help="comma-separated columns")
    agg.add_argument("--filter", action="append")
    agg.add_argument("--metric", action="append",
                     help="func:field metric (sum/avg/min/max; repeatable)")
    agg.add_argument("--limit", type=int, default=50)
    agg.set_defaults(func=cmd_aggregate)

    cs = sub.add_parser("catalog-search", parents=[common])
    cs.add_argument("--q", required=True)
    cs.add_argument("--limit", type=int, default=20)
    cs.set_defaults(func=cmd_catalog_search)

    srv = sub.add_parser("serve", parents=[common])
    srv.add_argument("--host", default="127.0.0.1")
    srv.add_argument("--port", type=int, default=8099)
    srv.set_defaults(func=cmd_serve)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
