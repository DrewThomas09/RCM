"""Unified connectors CLI — one entry point over the whole API estate.

    python -m connectors.cli connectors          # the estate: connectors + counts
    python -m connectors.cli datasets [--connector NAME] [--json]
    python -m connectors.cli catalog             # full catalog as JSON
    python -m connectors.cli catalog-search Q --db DIR [--connector NAME]
    python -m connectors.cli serve [--db DIR|:memory:] [--host H] [--port P]

Per-connector operations (ingest, per-endpoint query against a live DB) stay
in each connector's own CLI (``python -m connectors.<name>.cli``). This one is
the estate-level, read-the-catalog / serve-everything front door.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from . import registry as estate


def _cmd_connectors(_args: argparse.Namespace) -> int:
    for row in estate.connectors_summary():
        base = ", ".join(row["base_urls"])
        print(f"{row['connector']:14} {row['n_datasets']:2} datasets  "
              f"{row['label']}")
        print(f"{'':14}    {base}")
    return 0


def _cmd_datasets(args: argparse.Namespace) -> int:
    rows = estate.all_registry_rows()
    if args.connector:
        rows = [r for r in rows if r["connector"] == args.connector]
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
        return 0
    if not rows:
        print("(no datasets)")
        return 0
    width = max(len(r["dataset_id"]) for r in rows)
    for r in rows:
        print(f"{r['dataset_id']:<{width}}  {r['connector']:14} "
              f"{r['target_table']:24} {r['endpoint']}")
    return 0


def _cmd_catalog(_args: argparse.Namespace) -> int:
    print(json.dumps(estate.catalog(), indent=2, default=str))
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:  # pragma: no cover
    from . import api_server
    api_server.serve(args.db, host=args.host, port=args.port)
    return 0


def _cmd_refresh(args: argparse.Namespace) -> int:
    from . import refresh as refresh_mod
    names = args.connector or None
    try:
        planned = refresh_mod.plan(quick=not args.full, connectors=names)
    except KeyError:
        # Manual-only connectors (openfda, npi_registry, icd10) and typos
        # both land here — a traceback would read as a crash.
        plannable = ", ".join(refresh_mod.plan())
        manual = ", ".join(refresh_mod.UNPLANNED)
        print(f"no refresh plan for: {names}\n"
              f"plannable: {plannable}\n"
              f"manual-only (use their own CLIs): {manual}", file=sys.stderr)
        return 2
    if args.dry_run:
        for name, steps in planned.items():
            for argv in steps:
                print(f"{name:16} {' '.join(argv)}")
        return 0
    report = refresh_mod.refresh(args.db, quick=not args.full, connectors=names)
    if getattr(args, "json", False):
        print(json.dumps(report.as_dict(), indent=2, default=str))
    else:
        print(report.summary())
    return 0 if report.ok else 1


def _cmd_catalog_search(args: argparse.Namespace) -> int:
    """Search every synced open-data catalog at once.

    The registered datasets are the curated slice; the synced catalogs are
    everything the upstream publishers list (tens of thousands of rows).
    This finds a dataset by keyword across all of them so it can then be
    pulled through its connector's generic fetched-rows path.

    Needs a real ``--db`` dir: the catalogs live in the ingested SQLite
    files, so an unseeded estate honestly returns nothing rather than
    pretending. Run ``connectors.cli refresh --db DIR`` first — every
    catalog connector's plan starts with a ``discover`` (catalog sync).
    """
    from .api_server import open_stores
    stores = open_stores(args.db)
    try:
        res = estate.catalog_search_all(
            stores, args.q, limit=args.limit,
            per_connector_limit=args.per_connector_limit,
            connectors=args.connector or None)
    finally:
        for store in stores.values():
            store.close()
    if args.json:
        print(json.dumps(res, indent=2, default=str))
        return 0
    if not res["results"]:
        searched = ", ".join(res["connectors_searched"]) or "none"
        print(f"no catalog dataset matches {args.q!r} "
              f"(catalogs searched: {searched})", file=sys.stderr)
        return 1
    for row in res["results"]:
        print(f"{row['connector']:15} {row['dataset_id']:38} {row['title']}")
    print(f"\n{res['count']} of {res['total_before_limit']} hits across "
          f"{len(res['connectors_searched'])} catalogs")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="connectors", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("connectors", help="list connectors + dataset counts")
    sp.set_defaults(func=_cmd_connectors)

    sp = sub.add_parser("datasets", help="list every dataset in the estate")
    sp.add_argument("--connector", help="filter to one connector")
    sp.add_argument("--json", action="store_true", help="emit JSON")
    sp.set_defaults(func=_cmd_datasets)

    sp = sub.add_parser("catalog", help="full estate catalog as JSON")
    sp.set_defaults(func=_cmd_catalog)

    sp = sub.add_parser(
        "catalog-search",
        help="keyword-search every synced open-data catalog at once")
    sp.add_argument("q", help="keyword matched against title OR description")
    sp.add_argument("--db", required=True,
                    help="directory holding the per-connector DBs "
                         "(the catalogs live in the ingested files)")
    sp.add_argument("--connector", action="append",
                    help="limit to one catalog connector (repeatable)")
    sp.add_argument("--limit", type=int, default=50,
                    help="max merged rows returned (default 50)")
    sp.add_argument("--per-connector-limit", type=int, default=50,
                    help="max hits each catalog contributes, so one large "
                         "catalog cannot crowd out the others (default 50)")
    sp.add_argument("--json", action="store_true", help="emit JSON")
    sp.set_defaults(func=_cmd_catalog_search)

    sp = sub.add_parser("serve", help="serve the unified /v1 surface")
    sp.add_argument("--db", default=":memory:",
                    help="directory for per-connector DBs, or ':memory:'")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8100)
    sp.set_defaults(func=_cmd_serve)

    sp = sub.add_parser(
        "refresh",
        help="ingest a polite slice of every connector into a db dir")
    sp.add_argument("--db", required=True,
                    help="directory for per-connector DBs (e.g. var/connectors)")
    sp.add_argument("--connector", action="append",
                    help="limit to one connector (repeatable)")
    sp.add_argument("--full", action="store_true",
                    help="widen page caps (still never unbounded pulls)")
    sp.add_argument("--dry-run", action="store_true",
                    help="print the planned CLI invocations without running")
    sp.add_argument("--json", action="store_true",
                    help="emit the machine-readable report (also persisted "
                         "to {db}/_refresh_report.json on every real run)")
    sp.set_defaults(func=_cmd_refresh)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
