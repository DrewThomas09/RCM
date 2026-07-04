"""CLI for the CMS Coverage connector.

Stdlib ``argparse`` only, mirroring the rest of RCM-MC's CLIs.
Subcommands::

    python -m connectors.cms_coverage.cli discover
    python -m connectors.cms_coverage.cli datasets
    python -m connectors.cms_coverage.cli query <dataset_id> [--filter f=v ...]
                                          [--select c,c] [--sort -c] [--limit N]
    python -m connectors.cms_coverage.cli lookup-document   <document_id>  [--root DIR]
    python -m connectors.cms_coverage.cli lookup-contractor <contractor_id> [--root DIR]
    python -m connectors.cms_coverage.cli serve [--host H] [--port P] [--root DIR]

The ``--root`` dir holds the SQLite db.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .connector import CmsCoverageConnector
from .lookup import lookup_contractor, lookup_document
from .query import QueryError, query
from .registry import registry_as_dicts
from .tables import CmsCoverageStore


def _paths(root: str) -> Dict[str, str]:
    base = Path(root)
    base.mkdir(parents=True, exist_ok=True)
    return {"db": str(base / "cms_coverage.db"), "root": str(base)}


def _store(root: str) -> CmsCoverageStore:
    return CmsCoverageStore(_paths(root)["db"])


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def cmd_discover(_args: argparse.Namespace) -> int:
    conn = CmsCoverageConnector()
    _print([{"key": s.key, "path": s.path, "coverage_level": s.coverage_level,
             "document_type": s.document_type, "target_table": s.target_table,
             "paginated": s.paginated, "refresh_cadence": s.refresh_cadence}
            for s in conn.discover()])
    return 0


def cmd_datasets(_args: argparse.Namespace) -> int:
    _print(registry_as_dicts())
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    store = _store(args.root)
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


def cmd_lookup_document(args: argparse.Namespace) -> int:
    _print(lookup_document(_store(args.root), args.document_id))
    return 0


def cmd_lookup_contractor(args: argparse.Namespace) -> int:
    _print(lookup_contractor(_store(args.root), args.contractor_id))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .api_server import serve
    serve(_paths(args.root)["db"], host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="connectors.cms_coverage.cli",
        description="CMS Coverage (Medicare Coverage Database) connector")
    p.add_argument("--root", default="./.cms_coverage_data",
                   help="working dir for the SQLite db")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("discover").set_defaults(func=cmd_discover)
    sub.add_parser("datasets").set_defaults(func=cmd_datasets)

    q = sub.add_parser("query")
    q.add_argument("dataset")
    q.add_argument("--filter", action="append")
    q.add_argument("--select")
    q.add_argument("--sort")
    q.add_argument("--limit", type=int, default=50)
    q.add_argument("--offset", type=int, default=0)
    q.set_defaults(func=cmd_query)

    ld = sub.add_parser("lookup-document")
    ld.add_argument("document_id")
    ld.set_defaults(func=cmd_lookup_document)

    lc = sub.add_parser("lookup-contractor")
    lc.add_argument("contractor_id")
    lc.set_defaults(func=cmd_lookup_contractor)

    srv = sub.add_parser("serve")
    srv.add_argument("--host", default="127.0.0.1")
    srv.add_argument("--port", type=int, default=8098)
    srv.set_defaults(func=cmd_serve)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if not hasattr(args, "root"):
        args.root = "./.cms_coverage_data"
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
