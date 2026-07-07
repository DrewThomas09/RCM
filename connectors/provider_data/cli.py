"""CLI for the Provider Data Catalog connector.

Stdlib ``argparse`` only, mirroring the rest of RCM-MC's CLIs.
Subcommands::

    python -m connectors.provider_data.cli datasets
    python -m connectors.provider_data.cli discover           [--db PATH]
    python -m connectors.provider_data.cli fetch --dataset K  [--db PATH]
        [--state XX] [--filter col=value ...] [--max-pages N] [--page-size N]
    python -m connectors.provider_data.cli query <dataset_id> [--db PATH]
        [--filter f=v ...] [--select c,c] [--sort -c] [--limit N] [--offset N]
    python -m connectors.provider_data.cli catalog-search --q TEXT [--db PATH]
    python -m connectors.provider_data.cli serve [--host H] [--port P] [--db PATH]

``--db`` defaults to ``:memory:`` — fine for a one-shot look, but pass a
file path to keep what you ingest (e.g. ``--db ./provider_data.db``).

``fetch --dataset`` accepts a curated key (``hospital_general``), a full
dataset id (``provider_data_hospital_general``) or any DKAN 4x4
identifier from the catalog (``xubh-q36u`` → generic rows table).
``--state XX`` is sugar for the server-side equality condition the Care
Compare files all support; ``--filter col=value`` adds any other one.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from .connector import ProviderDataConnector
from .query import QueryError, aggregate, query
from .registry import registry_as_dicts
from .tables import ProviderDataStore


def _store(args: argparse.Namespace) -> ProviderDataStore:
    return ProviderDataStore(args.db)


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _parse_kv(pairs: Optional[List[str]], flag: str) -> Optional[Dict[str, str]]:
    out: Dict[str, str] = {}
    for f in pairs or []:
        if "=" not in f:
            raise SystemExit(f"bad {flag} {f!r}; expected key=value")
        k, v = f.split("=", 1)
        out[k] = v
    return out or None


def cmd_datasets(_args: argparse.Namespace) -> int:
    _print(registry_as_dicts())
    return 0


def cmd_discover(args: argparse.Namespace) -> int:
    store = _store(args)
    conn = ProviderDataConnector()
    counts = conn.refresh(store, "catalog")
    counts["db"] = args.db
    _print(counts)
    store.close()
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    store = _store(args)
    conn = ProviderDataConnector()
    conditions = _parse_kv(args.filter, "--filter") or {}
    if args.state:
        conditions["state"] = args.state.upper()
    try:
        counts = conn.refresh(
            store, args.dataset,
            max_pages=args.max_pages, page_size=args.page_size,
            conditions=conditions or None)
    except KeyError as exc:
        print(f"fetch error: {exc}", file=sys.stderr)
        store.close()
        return 2
    counts["db"] = args.db
    _print(counts)
    store.close()
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    store = _store(args)
    filters = _parse_kv(args.filter, "--filter") or {}
    select = args.select.split(",") if args.select else None
    sort = args.sort.split(",") if args.sort else None
    try:
        res = query(store, args.dataset, filters=filters, select=select,
                    sort=sort, limit=args.limit, offset=args.offset)
    except QueryError as exc:
        print(f"query error: {exc}", file=sys.stderr)
        store.close()
        return 2
    _print(res.as_dict())
    store.close()
    return 0

def cmd_aggregate(args: argparse.Namespace) -> int:
    store = _store(args)
    filters = _parse_kv(args.filter, "--filter") or {}
    try:
        res = aggregate(store, args.dataset, group_by=args.group_by.split(","),
                        filters=filters, metrics=args.metric, limit=args.limit)
    except QueryError as exc:
        print(f"aggregate error: {exc}", file=sys.stderr)
        store.close()
        return 2
    _print(res.as_dict())
    store.close()
    return 0


def cmd_catalog_search(args: argparse.Namespace) -> int:
    """LIKE-search the synced catalog; syncs it first when empty.

    The auto-sync means ``catalog-search`` "just works" against the
    default in-memory db, at the cost of one live catalog request.
    """
    store = _store(args)
    if store.count("provider_data_catalog") == 0:
        ProviderDataConnector().refresh(store, "catalog")
    needle = f"%{args.q}%"
    rows = store.fetchall(
        "SELECT identifier, title, themes, modified, landing_page "
        "FROM provider_data_catalog "
        "WHERE title LIKE ? OR description LIKE ? OR keywords LIKE ? "
        "OR themes LIKE ? ORDER BY title LIMIT ?",
        (needle, needle, needle, needle, args.limit))
    _print({"q": args.q, "count": len(rows), "rows": [dict(r) for r in rows]})
    store.close()
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .api_server import serve
    serve(args.db, host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="connectors.provider_data.cli",
        description="CMS Provider Data Catalog / Care Compare (DKAN) connector")
    p.add_argument("--db", default=":memory:",
                   help="SQLite db path (default :memory:)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("datasets").set_defaults(func=cmd_datasets)
    sub.add_parser("discover").set_defaults(func=cmd_discover)

    f = sub.add_parser("fetch")
    f.add_argument("--dataset", required=True,
                   help="curated key, provider_data_* id, or 4x4 identifier")
    f.add_argument("--state", help="two-letter state equality condition")
    f.add_argument("--filter", action="append",
                   help="col=value server-side equality condition")
    f.add_argument("--max-pages", type=int, default=None,
                   help="page cap (default 5; raise for bulk pulls)")
    f.add_argument("--page-size", type=int, default=None,
                   help="rows per page (default 500, API max 1500)")
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

    cs = sub.add_parser("catalog-search")
    cs.add_argument("--q", required=True, help="text to search the catalog for")
    cs.add_argument("--limit", type=int, default=25)
    cs.set_defaults(func=cmd_catalog_search)

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
