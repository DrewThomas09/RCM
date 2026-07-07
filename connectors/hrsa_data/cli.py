"""CLI for the HRSA data connector.

Stdlib ``argparse`` only, mirroring the rest of RCM-MC's CLIs.
Subcommands::

    python -m connectors.hrsa_data.cli discover
    python -m connectors.hrsa_data.cli datasets
    python -m connectors.hrsa_data.cli fetch --dataset hpsa_primary_care
                                          [--max-rows N | --full] [--root DIR]
    python -m connectors.hrsa_data.cli query <dataset_id> [--filter f=v ...]
                                          [--select c,c] [--sort -c] [--limit N]
    python -m connectors.hrsa_data.cli lookup-shortage-area <ST> [--root DIR]
    python -m connectors.hrsa_data.cli lookup-health-center <ST> [--root DIR]
    python -m connectors.hrsa_data.cli serve [--host H] [--port P] [--root DIR]

The ``--root`` dir holds the SQLite db. ``fetch`` defaults to a
50,000-row cap because the source CSVs run 10-60 MB; pass ``--full``
for a complete pull (the transport streams, so a capped fetch only
downloads what it parses).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .connector import DEFAULT_MAX_ROWS, HrsaDataConnector
from .endpoints import ENDPOINTS
from .lookup import lookup_health_center, lookup_shortage_area
from .query import QueryError, query
from .registry import registry_as_dicts
from .tables import HrsaDataStore


def _paths(root: str) -> Dict[str, str]:
    base = Path(root)
    base.mkdir(parents=True, exist_ok=True)
    return {"db": str(base / "hrsa_data.db"), "root": str(base)}


def _store(root: str) -> HrsaDataStore:
    return HrsaDataStore(_paths(root)["db"])


def _store_read(root: str) -> HrsaDataStore:
    """Store for READ verbs: never creates the root dir or the db file.

    A plain ``query``/``lookup-*`` on a never-ingested root used to mkdir
    ``./.hrsa_data_data`` and write an empty schema db as a side effect of
    a read; open ``:memory:`` instead (the same discipline the RCM-MC
    bridge applies) so reads stay side-effect free.
    """
    db = Path(root) / "hrsa_data.db"
    if not db.is_file():
        return HrsaDataStore(":memory:")
    return HrsaDataStore(str(db))


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _dataset_key(raw: str) -> str:
    """Accept both the short key and the fully-prefixed dataset id."""
    key = raw.strip()
    if key.startswith("hrsa_data_"):
        key = key[len("hrsa_data_"):]
    return key


def cmd_discover(_args: argparse.Namespace) -> int:
    conn = HrsaDataConnector()
    _print([{"key": s.key, "file": s.file_name, "path": s.path,
             "dataset_kind": s.dataset_kind, "discipline": s.discipline,
             "target_table": s.target_table,
             "refresh_cadence": s.refresh_cadence}
            for s in conn.discover()])
    return 0


def cmd_datasets(_args: argparse.Namespace) -> int:
    _print(registry_as_dicts())
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    key = _dataset_key(args.dataset)
    if key not in ENDPOINTS:
        print(f"unknown dataset {args.dataset!r}; known: {sorted(ENDPOINTS)}",
              file=sys.stderr)
        return 2
    max_rows: Optional[int] = None if args.full else args.max_rows
    store = _store(args.root)
    conn = HrsaDataConnector()
    counts = conn.refresh(store, key, max_rows=max_rows)
    counts["table_totals"] = {
        t: store.count(t) for t in sorted({ENDPOINTS[key].target_table})}
    _print(counts)
    store.close()
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


def cmd_lookup_shortage_area(args: argparse.Namespace) -> int:
    _print(lookup_shortage_area(_store_read(args.root), args.state, args.limit))
    return 0


def cmd_lookup_health_center(args: argparse.Namespace) -> int:
    _print(lookup_health_center(_store_read(args.root), args.state, args.limit))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .api_server import serve
    serve(_paths(args.root)["db"], host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="connectors.hrsa_data.cli",
        description="HRSA data downloads (HPSA / MUA / health center sites) connector")
    p.add_argument("--root", default="./.hrsa_data",
                   help="working dir for the SQLite db")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("discover").set_defaults(func=cmd_discover)
    sub.add_parser("datasets").set_defaults(func=cmd_datasets)

    f = sub.add_parser("fetch")
    f.add_argument("--dataset", required=True,
                   help=f"one of {sorted(ENDPOINTS)} (hrsa_data_ prefix ok)")
    f.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS,
                   help=f"row cap per file (default {DEFAULT_MAX_ROWS})")
    f.add_argument("--full", action="store_true",
                   help="ingest the whole file (ignores --max-rows)")
    f.set_defaults(func=cmd_fetch)

    q = sub.add_parser("query")
    q.add_argument("dataset")
    q.add_argument("--filter", action="append")
    q.add_argument("--select")
    q.add_argument("--sort")
    q.add_argument("--limit", type=int, default=50)
    q.add_argument("--offset", type=int, default=0)
    q.set_defaults(func=cmd_query)

    ls = sub.add_parser("lookup-shortage-area")
    ls.add_argument("state")
    ls.add_argument("--limit", type=int, default=25)
    ls.set_defaults(func=cmd_lookup_shortage_area)

    lh = sub.add_parser("lookup-health-center")
    lh.add_argument("state")
    lh.add_argument("--limit", type=int, default=25)
    lh.set_defaults(func=cmd_lookup_health_center)

    srv = sub.add_parser("serve")
    srv.add_argument("--host", default="127.0.0.1")
    srv.add_argument("--port", type=int, default=8099)
    srv.set_defaults(func=cmd_serve)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if not hasattr(args, "root"):
        args.root = "./.hrsa_data"
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
