"""CLI for the OIG LEIE connector.

Stdlib ``argparse`` only, mirroring the rest of RCM-MC's CLIs.
Subcommands::

    python -m connectors.oig_leie.cli [--db PATH] datasets
    python -m connectors.oig_leie.cli [--db PATH] discover
    python -m connectors.oig_leie.cli [--db PATH] fetch --dataset exclusions
                                          [--max-rows N | --full]
                                          [--year YYYY --month M]
    python -m connectors.oig_leie.cli [--db PATH] query <dataset_id>
                                          [--filter f=v ...] [--select c,c]
                                          [--sort -c] [--limit N]
    python -m connectors.oig_leie.cli [--db PATH] lookup-exclusion <NPI>
    python -m connectors.oig_leie.cli [--db PATH] lookup-exclusion-name <NAME>
                                          [--first F] [--limit N]
    python -m connectors.oig_leie.cli [--db PATH] serve [--host H] [--port P]

``--db`` is a GLOBAL flag (the estate refresh driver assumes this for
new connectors) and defaults to ``:memory:`` — handy for smoke tests,
but pass a file path when you want ``fetch`` output to persist for
``query``/``lookup-*``/``serve``.

``fetch --dataset exclusions`` pulls the full-replacement UPDATED.csv;
the default ``--max-rows`` of 100,000 covers the whole ~83k-row file (a
compliance list must not be silently partial). ``--dataset supplement``
/ ``--dataset reinstatements`` pull a monthly delta: pass ``--year`` +
``--month`` for a specific month, or neither for the newest published
month (the connector walks back — some months publish no file).
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from .connector import DEFAULT_MAX_ROWS, OigLeieConnector
from .endpoints import ENDPOINTS
from .lookup import lookup_exclusion, lookup_exclusion_name
from .query import QueryError, query
from .registry import registry_as_dicts
from .tables import OigLeieStore


def _store(args: argparse.Namespace) -> OigLeieStore:
    return OigLeieStore(args.db)


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _dataset_key(raw: str) -> str:
    """Accept both the short key and the fully-prefixed dataset id."""
    key = raw.strip()
    if key.startswith("oig_leie_"):
        key = key[len("oig_leie_"):]
    return key


def cmd_datasets(_args: argparse.Namespace) -> int:
    _print(registry_as_dicts())
    return 0


def cmd_discover(_args: argparse.Namespace) -> int:
    conn = OigLeieConnector()
    _print([{"key": s.key, "path": s.path_template,
             "dataset_kind": s.dataset_kind, "file_kind": s.file_kind,
             "target_table": s.target_table,
             "refresh_cadence": s.refresh_cadence}
            for s in conn.discover()])
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    key = _dataset_key(args.dataset)
    if key not in ENDPOINTS:
        print(f"unknown dataset {args.dataset!r}; known: {sorted(ENDPOINTS)}",
              file=sys.stderr)
        return 2
    if (args.year is None) != (args.month is None):
        print("--year and --month must be given together", file=sys.stderr)
        return 2
    max_rows: Optional[int] = None if args.full else args.max_rows
    store = _store(args)
    conn = OigLeieConnector()
    counts = conn.refresh(store, key, max_rows=max_rows,
                          year=args.year, month=args.month)
    counts["table_totals"] = {
        t: store.count(t) for t in sorted({ENDPOINTS[key].target_table})}
    if counts.get("warning"):
        # e.g. a row-capped pull of the full-replacement file merged
        # without deleting the previous snapshot — make it unmissable.
        print(f"WARNING: {counts['warning']}", file=sys.stderr)
    _print(counts)
    store.close()
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    store = _store(args)
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


def cmd_lookup_exclusion(args: argparse.Namespace) -> int:
    _print(lookup_exclusion(_store(args), args.npi, args.limit))
    return 0


def cmd_lookup_exclusion_name(args: argparse.Namespace) -> int:
    _print(lookup_exclusion_name(_store(args), args.name, args.first,
                                 args.limit))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .api_server import serve
    serve(args.db, host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="connectors.oig_leie.cli",
        description="HHS OIG LEIE (List of Excluded Individuals/Entities) "
                    "connector")
    p.add_argument("--db", default=":memory:",
                   help="SQLite db path (default :memory:)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("datasets").set_defaults(func=cmd_datasets)
    sub.add_parser("discover").set_defaults(func=cmd_discover)

    f = sub.add_parser("fetch")
    f.add_argument("--dataset", required=True,
                   help=f"one of {sorted(ENDPOINTS)} (oig_leie_ prefix ok)")
    f.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS,
                   help=f"row cap (default {DEFAULT_MAX_ROWS}, which covers "
                        "the whole full file)")
    f.add_argument("--full", action="store_true",
                   help="ingest the whole file uncapped (ignores --max-rows)")
    f.add_argument("--year", type=int,
                   help="supplement month's year, e.g. 2026 (supplement/"
                        "reinstatements only; omit for newest published)")
    f.add_argument("--month", type=int,
                   help="supplement month 1-12 (with --year)")
    f.set_defaults(func=cmd_fetch)

    q = sub.add_parser("query")
    q.add_argument("dataset")
    q.add_argument("--filter", action="append")
    q.add_argument("--select")
    q.add_argument("--sort")
    q.add_argument("--limit", type=int, default=50)
    q.add_argument("--offset", type=int, default=0)
    q.set_defaults(func=cmd_query)

    le = sub.add_parser("lookup-exclusion")
    le.add_argument("npi")
    le.add_argument("--limit", type=int, default=25)
    le.set_defaults(func=cmd_lookup_exclusion)

    ln = sub.add_parser("lookup-exclusion-name")
    ln.add_argument("name")
    ln.add_argument("--first", default="")
    ln.add_argument("--limit", type=int, default=25)
    ln.set_defaults(func=cmd_lookup_exclusion_name)

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
