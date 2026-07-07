"""CLI for the ICD-10 (NLM Clinical Tables) connector.

Stdlib ``argparse`` only, mirroring the rest of RCM-MC's CLIs. Subcommands::

    python -m connectors.icd10.cli datasets
    python -m connectors.icd10.cli registry
    python -m connectors.icd10.cli discover
    python -m connectors.icd10.cli ingest [--dataset cm|pcs] [--terms T]
                                          [--q code:E11*] [--root DIR]
    python -m connectors.icd10.cli query <dataset_id> [--filter f=v ...]
                                         [--select c,c] [--sort -c] [--limit N]
    python -m connectors.icd10.cli aggregate <dataset_id> --group-by c[,c]
    python -m connectors.icd10.cli lookup-code <code> [--type cm|pcs]
    python -m connectors.icd10.cli lookup-category <cat> [--type cm|pcs]
    python -m connectors.icd10.cli search <code_type> <term> [--limit N]
    python -m connectors.icd10.cli serve [--host H] [--port P] [--root DIR]

The ``--root`` dir holds the SQLite db.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .connector import MAX_PAGES_PER_STEP, Icd10Connector
from .endpoints import ENDPOINTS, get_endpoint
from .lookup import lookup_category, lookup_code, search_codes
from .normalize import normalize
from .query import QueryError, aggregate, query
from .registry import registry_as_dicts
from .tables import Icd10Store


def _db_path(root: str) -> str:
    base = Path(root)
    base.mkdir(parents=True, exist_ok=True)
    return str(base / "icd10.db")


def _store(root: str) -> Icd10Store:
    return Icd10Store(_db_path(root))


def _store_read(root: str) -> Icd10Store:
    """Store for READ verbs: never creates the root dir or the db file.

    A plain ``query``/``lookup-*``/``search`` on a never-ingested root
    used to mkdir ``./.icd10_data`` and write an empty schema db as a
    side effect of a read; open ``:memory:`` instead (the same discipline
    the RCM-MC bridge applies) so reads stay side-effect free.
    """
    db = Path(root) / "icd10.db"
    if not db.is_file():
        return Icd10Store(":memory:")
    return Icd10Store(str(db))


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def cmd_datasets(_args: argparse.Namespace) -> int:
    _print(registry_as_dicts())
    return 0


cmd_registry = cmd_datasets


def cmd_discover(_args: argparse.Namespace) -> int:
    conn = Icd10Connector()
    _print([{"key": s.key, "code_type": s.code_type, "path": s.path,
             "df": list(s.df), "target_table": s.target_table,
             "refresh_cadence": s.refresh_cadence, "seeds": len(s.seeds)}
            for s in conn.discover()])
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    store = _store(args.root)
    conn = Icd10Connector()
    specs = [get_endpoint(args.dataset)] if args.dataset else conn.discover()
    written = 0
    for spec in specs:
        params: Dict[str, Any] = {}
        if args.terms:
            params["terms"] = args.terms
        if args.q:
            params["q"] = args.q
        cursor: Optional[Dict[str, Any]] = None
        for _ in range(args.max_steps):
            res = conn.fetch(spec, params, cursor)
            nres = normalize(spec, res.rows)
            for table, rws in nres.rows.items():
                written += store.upsert(table, rws)
            if res.next_cursor is None:
                break
            cursor = res.next_cursor
    _print({"ingested": written,
            "datasets": [s.key for s in specs]})
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    store = _store_read(args.root)
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
    _print(res.as_dict())
    return 0


def cmd_aggregate(args: argparse.Namespace) -> int:
    store = _store_read(args.root)
    filters: Dict[str, Any] = {}
    for f in args.filter or []:
        if "=" in f:
            k, v = f.split("=", 1)
            filters[k] = v
    try:
        res = aggregate(store, args.dataset, group_by=args.group_by.split(","),
                        filters=filters, limit=args.limit)
    except QueryError as exc:
        print(f"aggregate error: {exc}", file=sys.stderr)
        return 2
    _print(res.as_dict())
    return 0


def cmd_lookup_code(args: argparse.Namespace) -> int:
    _print(lookup_code(_store_read(args.root), args.code, args.type))
    return 0


def cmd_lookup_category(args: argparse.Namespace) -> int:
    _print(lookup_category(_store_read(args.root), args.category, args.type))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    _print(search_codes(_store_read(args.root), args.code_type, args.term,
                        limit=args.limit))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .api_server import serve
    serve(_db_path(args.root), host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="connectors.icd10.cli",
        description="ICD-10 (NLM Clinical Tables) connector")
    p.add_argument("--root", default="./.icd10_data",
                   help="working dir for the SQLite db")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("datasets").set_defaults(func=cmd_datasets)
    sub.add_parser("registry").set_defaults(func=cmd_registry)
    sub.add_parser("discover").set_defaults(func=cmd_discover)

    ing = sub.add_parser("ingest")
    ing.add_argument("--dataset", choices=sorted(ENDPOINTS))
    ing.add_argument("--terms", default="")
    ing.add_argument("--q", default="", help="Elasticsearch filter, e.g. code:E11*")
    ing.add_argument("--max-steps", type=int, default=MAX_PAGES_PER_STEP * 64)
    ing.set_defaults(func=cmd_ingest)

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
    agg.add_argument("--limit", type=int, default=50)
    agg.set_defaults(func=cmd_aggregate)

    lc = sub.add_parser("lookup-code")
    lc.add_argument("code")
    lc.add_argument("--type", default="cm", choices=["cm", "pcs"])
    lc.set_defaults(func=cmd_lookup_code)

    lcat = sub.add_parser("lookup-category")
    lcat.add_argument("category")
    lcat.add_argument("--type", default="cm", choices=["cm", "pcs"])
    lcat.set_defaults(func=cmd_lookup_category)

    s = sub.add_parser("search")
    s.add_argument("code_type", choices=["cm", "pcs"])
    s.add_argument("term")
    s.add_argument("--limit", type=int, default=50)
    s.set_defaults(func=cmd_search)

    srv = sub.add_parser("serve")
    srv.add_argument("--host", default="127.0.0.1")
    srv.add_argument("--port", type=int, default=8098)
    srv.set_defaults(func=cmd_serve)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if not hasattr(args, "root"):
        args.root = "./.icd10_data"
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
