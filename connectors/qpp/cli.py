"""CLI for the CMS Quality Payment Program (QPP) connector.

Stdlib ``argparse`` only, mirroring the rest of RCM-MC's CLIs. Subcommands::

    python -m connectors.qpp.cli datasets
    python -m connectors.qpp.cli registry
    python -m connectors.qpp.cli discover
    python -m connectors.qpp.cli fetch --dataset benchmarks [--year 2025]
    python -m connectors.qpp.cli fetch --dataset eligibility --npis N1,N2 [--year 2025]
    python -m connectors.qpp.cli query <dataset_id> [--filter f=v ...]
                                       [--select c,c] [--sort -c] [--limit N]
    python -m connectors.qpp.cli aggregate <dataset_id> --group-by c[,c]
    python -m connectors.qpp.cli lookup-clinician <npi>
    python -m connectors.qpp.cli lookup-benchmarks <measure_id> [--year Y]
    python -m connectors.qpp.cli serve [--host H] [--port P] [--root DIR]

The ``--root`` dir holds the SQLite db. The eligibility fetch is
roster-driven (``--npis``) because the QPP Eligibility API is per-NPI;
the benchmarks fetch runs unattended, one request per performance year.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .connector import QppConnector
from .endpoints import ENDPOINTS, get_endpoint
from .lookup import lookup_benchmarks, lookup_clinician
from .normalize import normalize
from .query import QueryError, aggregate, query
from .registry import registry_as_dicts
from .tables import QppStore


def _db_path(root: str) -> str:
    base = Path(root)
    base.mkdir(parents=True, exist_ok=True)
    return str(base / "qpp.db")


def _store(root: str) -> QppStore:
    return QppStore(_db_path(root))


def _store_read(root: str) -> QppStore:
    """Store for READ verbs: never creates the root dir or the db file.

    A plain ``query``/``lookup-*`` on a never-ingested root must not
    mkdir the root or write an empty schema db as a side effect of a
    read; open ``:memory:`` instead (the same discipline the RCM-MC
    bridge applies) so reads stay side-effect free.
    """
    db = Path(root) / "qpp.db"
    if not db.is_file():
        return QppStore(":memory:")
    return QppStore(str(db))


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def cmd_datasets(_args: argparse.Namespace) -> int:
    _print(registry_as_dicts())
    return 0


cmd_registry = cmd_datasets


def cmd_discover(_args: argparse.Namespace) -> int:
    conn = QppConnector()
    _print([{"key": s.key, "kind": s.kind, "path": s.path,
             "target_table": s.target_table,
             "refresh_cadence": s.refresh_cadence,
             "default_params": dict(s.default_params)}
            for s in conn.discover()])
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    spec = get_endpoint(args.dataset)
    if spec.kind in ("eligibility", "organizations") and not args.npis:
        print("fetch --dataset eligibility needs --npis N1,N2,… "
              "(the QPP Eligibility API is per-NPI)", file=sys.stderr)
        return 2
    store = _store(args.root)
    conn = QppConnector()
    params: Dict[str, Any] = {}
    if args.year:
        params["year"] = args.year
    if args.npis:
        params["npis"] = args.npis
    written = 0
    skipped: List[str] = []
    cursor: Optional[Dict[str, Any]] = None
    for _ in range(args.max_steps):
        res = conn.fetch(spec, params, cursor)
        nres = normalize(spec, res.rows)
        for table, rws in nres.rows.items():
            written += store.upsert(table, rws)
        skipped.extend(res.skipped_npis)
        if res.next_cursor is None:
            break
        cursor = res.next_cursor
    _print({"ingested": written, "dataset": spec.key,
            "skipped_npis": skipped})
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
                        filters=filters, metrics=args.metric, limit=args.limit)
    except QueryError as exc:
        print(f"aggregate error: {exc}", file=sys.stderr)
        return 2
    _print(res.as_dict())
    return 0


def cmd_lookup_clinician(args: argparse.Namespace) -> int:
    _print(lookup_clinician(_store_read(args.root), args.npi))
    return 0


def cmd_lookup_benchmarks(args: argparse.Namespace) -> int:
    _print(lookup_benchmarks(_store_read(args.root), args.measure_id,
                             args.year))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .api_server import serve
    serve(_db_path(args.root), host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="connectors.qpp.cli",
        description="CMS Quality Payment Program (QPP) connector")
    p.add_argument("--root", default="./.qpp_data",
                   help="working dir for the SQLite db")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("datasets").set_defaults(func=cmd_datasets)
    sub.add_parser("registry").set_defaults(func=cmd_registry)
    sub.add_parser("discover").set_defaults(func=cmd_discover)

    f = sub.add_parser("fetch")
    f.add_argument("--dataset", required=True, choices=sorted(ENDPOINTS))
    f.add_argument("--year", default="")
    f.add_argument("--npis", default="",
                   help="comma-joined NPI roster (eligibility only)")
    f.add_argument("--max-steps", type=int, default=400)
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

    lc = sub.add_parser("lookup-clinician")
    lc.add_argument("npi")
    lc.set_defaults(func=cmd_lookup_clinician)

    lb = sub.add_parser("lookup-benchmarks")
    lb.add_argument("measure_id")
    lb.add_argument("--year", default="")
    lb.set_defaults(func=cmd_lookup_benchmarks)

    srv = sub.add_parser("serve")
    srv.add_argument("--host", default="127.0.0.1")
    srv.add_argument("--port", type=int, default=8100)
    srv.set_defaults(func=cmd_serve)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if not hasattr(args, "root"):
        args.root = "./.qpp_data"
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
