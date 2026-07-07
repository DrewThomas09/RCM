"""CLI for the NPI Registry connector.

Stdlib ``argparse`` only, mirroring the rest of RCM's CLIs. Subcommands::

    python -m connectors.npi_registry.cli discover
    python -m connectors.npi_registry.cli datasets
    python -m connectors.npi_registry.cli ingest   [--endpoint K ...] [--root DIR]
    python -m connectors.npi_registry.cli query <dataset_id> [--filter f=v ...]
                                          [--select c,c] [--sort -c] [--limit N]
    python -m connectors.npi_registry.cli aggregate <dataset_id> --group-by c,c
    python -m connectors.npi_registry.cli lookup-provider <npi>    [--root DIR]
    python -m connectors.npi_registry.cli lookup-taxonomy <code>   [--root DIR]
    python -m connectors.npi_registry.cli validate <npi>
    python -m connectors.npi_registry.cli serve [--host H] [--port P] [--root DIR]

``--root`` holds the SQLite db (``npi_registry.db``).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .connector import NppesConnector
from .endpoints import ENDPOINTS, get_endpoint
from .lookup import lookup_provider, lookup_taxonomy
from .normalize import normalize
from .query import QueryError, aggregate, query
from .registry import registry_as_dicts
from .tables import NpiStore
from .validate import validate_npi


def _paths(root: str) -> Dict[str, str]:
    base = Path(root)
    base.mkdir(parents=True, exist_ok=True)
    return {"db": str(base / "npi_registry.db"), "root": str(base)}


def _store(root: str) -> NpiStore:
    return NpiStore(_paths(root)["db"])


def _store_read(root: str) -> NpiStore:
    """Store for READ verbs: never creates the root dir or the db file.

    A plain ``query``/``lookup-*`` on a never-ingested root used to mkdir
    ``./.npi_registry_data`` and write an empty schema db as a side effect of
    a read; open ``:memory:`` instead (the same discipline the RCM-MC
    bridge applies) so reads stay side-effect free.
    """
    db = Path(root) / "npi_registry.db"
    if not db.is_file():
        return NpiStore(":memory:")
    return NpiStore(str(db))


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def cmd_discover(_args: argparse.Namespace) -> int:
    conn = NppesConnector()
    _print([{"key": s.key, "enumeration_type": s.enumeration_type,
             "target_table": s.target_table, "seeds": list(s.seeds),
             "refresh_cadence": s.refresh_cadence}
            for s in conn.discover()])
    return 0


def cmd_datasets(_args: argparse.Namespace) -> int:
    _print(registry_as_dicts())
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    store = _store(args.root)
    conn = NppesConnector()
    keys = args.endpoint or list(ENDPOINTS)
    summary: Dict[str, Any] = {}
    for key in keys:
        spec = get_endpoint(key)
        rows_ingested = 0
        for seed in conn.seeds(spec):
            raw = conn.fetch_seed(spec, seed)
            res = normalize(spec, raw)
            for table, rows in res.rows.items():
                rows_ingested += store.upsert(table, rows)
        summary[key] = {"rows": rows_ingested}
    _print(summary)
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


def cmd_lookup_provider(args: argparse.Namespace) -> int:
    _print(lookup_provider(_store_read(args.root), args.npi))
    return 0


def cmd_lookup_taxonomy(args: argparse.Namespace) -> int:
    _print(lookup_taxonomy(_store_read(args.root), args.code, limit=args.limit))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    res = validate_npi(args.npi)
    _print(res)
    return 0 if res["valid"] else 1


def cmd_serve(args: argparse.Namespace) -> int:
    from .api_server import serve
    serve(_paths(args.root)["db"], host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="connectors.npi_registry.cli",
        description="NPPES NPI Registry connector")
    p.add_argument("--root", default="./.npi_registry_data",
                   help="working dir for the SQLite db")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("discover").set_defaults(func=cmd_discover)
    sub.add_parser("datasets").set_defaults(func=cmd_datasets)

    ing = sub.add_parser("ingest")
    ing.add_argument("--endpoint", action="append", choices=sorted(ENDPOINTS))
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

    lp = sub.add_parser("lookup-provider")
    lp.add_argument("npi")
    lp.set_defaults(func=cmd_lookup_provider)

    lt = sub.add_parser("lookup-taxonomy")
    lt.add_argument("code")
    lt.add_argument("--limit", type=int, default=200)
    lt.set_defaults(func=cmd_lookup_taxonomy)

    v = sub.add_parser("validate")
    v.add_argument("npi")
    v.set_defaults(func=cmd_validate)

    srv = sub.add_parser("serve")
    srv.add_argument("--host", default="127.0.0.1")
    srv.add_argument("--port", type=int, default=8098)
    srv.set_defaults(func=cmd_serve)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if not hasattr(args, "root"):
        args.root = "./.npi_registry_data"
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
