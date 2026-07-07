"""CLI for the CMS Open Data connector.

Stdlib ``argparse`` only, mirroring the rest of RCM-MC's CLIs.
Subcommands::

    python -m connectors.cms_open_data.cli datasets
    python -m connectors.cms_open_data.cli discover --db PATH
    python -m connectors.cms_open_data.cli fetch --dataset KEY [--filter col=v ...]
                                          [--max-pages N] [--size N] --db PATH
    python -m connectors.cms_open_data.cli query <dataset_id> [--filter f=v ...]
                                          [--select c,c] [--sort -c] [--limit N] --db PATH
    python -m connectors.cms_open_data.cli catalog-search --q TEXT --db PATH
    python -m connectors.cms_open_data.cli serve --db PATH [--host H] [--port P]

``--db`` defaults to ``:memory:`` (handy for dry runs; pass a path to
persist). ``fetch --dataset`` accepts a curated key (``acos``), a full
dataset id (``cms_open_data_acos``), a catalog title slug, or a raw
dataset UUID — the last two land in the generic ``cms_open_data_rows``
store. Fetch-time ``--filter`` uses the API's ORIGINAL column names
(they become native ``filter[COL]=v`` params); ``query`` uses the
uniform snake_cased grammar over what's already ingested.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from .connector import CmsOpenDataConnector
from .query import QueryError, aggregate, query
from .registry import registry_as_dicts
from .tables import CmsOpenDataStore


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _parse_filters(pairs: Optional[List[str]]) -> Optional[Dict[str, str]]:
    filters: Dict[str, str] = {}
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
    store = CmsOpenDataStore(args.db)
    conn = CmsOpenDataConnector()
    n = conn.sync_catalog(store)
    _print({"catalog_rows": n, "table": "cms_open_data_catalog", "db": args.db})
    store.close()
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    store = CmsOpenDataStore(args.db)
    conn = CmsOpenDataConnector()
    try:
        result = conn.refresh(
            store, args.dataset, _parse_filters(args.filter),
            max_pages=args.max_pages, page_size=args.size)
    except KeyError as exc:
        print(f"fetch error: {exc}", file=sys.stderr)
        store.close()
        return 2
    result["db"] = args.db
    _print(result)
    store.close()
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    store = CmsOpenDataStore(args.db)
    select = args.select.split(",") if args.select else None
    sort = args.sort.split(",") if args.sort else None
    try:
        res = query(store, args.dataset, filters=_parse_filters(args.filter) or {},
                    select=select, sort=sort, limit=args.limit, offset=args.offset)
    except QueryError as exc:
        print(f"query error: {exc}", file=sys.stderr)
        store.close()
        return 2
    _print(res.as_dict())
    store.close()
    return 0

def cmd_aggregate(args: argparse.Namespace) -> int:
    store = CmsOpenDataStore(args.db)
    try:
        res = aggregate(store, args.dataset,
                        group_by=args.group_by.split(","),
                        filters=_parse_filters(args.filter) or {},
                        metrics=args.metric, limit=args.limit)
    except QueryError as exc:
        print(f"aggregate error: {exc}", file=sys.stderr)
        store.close()
        return 2
    _print(res.as_dict())
    store.close()
    return 0


def cmd_catalog_search(args: argparse.Namespace) -> int:
    store = CmsOpenDataStore(args.db)
    like = f"%{args.q}%"
    rows = store.fetchall(
        "SELECT dataset_key, uuid, title, periodicity, modified, api_url "
        "FROM cms_open_data_catalog "
        "WHERE title LIKE ? OR description LIKE ? ORDER BY title LIMIT ?",
        (like, like, args.limit))
    _print({"q": args.q, "count": len(rows), "results": [dict(r) for r in rows]})
    store.close()
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .api_server import serve
    serve(args.db, host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="connectors.cms_open_data.cli",
        description="CMS Open Data (data.cms.gov data-api v1) connector")
    # --db rides on each subcommand (not the root) so
    # `cli discover --db PATH` parses the way people type it.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", default=":memory:",
                        help="SQLite db path (default: in-memory)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("datasets", parents=[common]).set_defaults(func=cmd_datasets)
    sub.add_parser("discover", parents=[common]).set_defaults(func=cmd_discover)

    f = sub.add_parser("fetch", parents=[common])
    f.add_argument("--dataset", required=True,
                   help="curated key, dataset_id, catalog slug, or UUID")
    f.add_argument("--filter", action="append",
                   help="native equality col=value (ORIGINAL column names)")
    f.add_argument("--max-pages", type=int, default=None,
                   help="page cap for this fetch (default 5)")
    f.add_argument("--size", type=int, default=None,
                   help="page size (default 1000, max 5000)")
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
    cs.add_argument("--q", required=True, help="substring of title/description")
    cs.add_argument("--limit", type=int, default=50)
    cs.set_defaults(func=cmd_catalog_search)

    srv = sub.add_parser("serve", parents=[common])
    srv.add_argument("--host", default="127.0.0.1")
    srv.add_argument("--port", type=int, default=8103)
    srv.set_defaults(func=cmd_serve)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
