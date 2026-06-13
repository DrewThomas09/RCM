"""Command-line entrypoint for the NPPES connector.

Usage::

    python -m connectors.nppes.cli build --db nppes.db [--from-fixtures DIR]
    python -m connectors.nppes.cli discover
    python -m connectors.nppes.cli lookup --db nppes.db --npi 1003456789
    python -m connectors.nppes.cli query  --db nppes.db --dataset dim_provider \\
        --filter state=TX --filter entity_type=2 --limit 10

``build`` runs the full pipeline. With no ``--monthly`` it generates the
synthetic verification universe (the live CMS download is network-blocked in
this environment) into a temp dir and ingests that — proving the slice
end-to-end. Point ``--monthly``/``--nucc`` at a staged real dissemination
file to ingest the real universe through the identical code path.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from . import api, pipeline, synth
from .connector import NppesConnector
from .store import NppesStore


def _cmd_discover(args) -> int:
    conn = NppesConnector()
    for row in conn.discover():
        print(f"{row['dataset_id']:32s} {row['ingest_mode']:10s} "
              f"-> {row['target_table']}")
    return 0


def _cmd_build(args) -> int:
    store = NppesStore(args.db)
    if args.monthly:
        report = pipeline.run(
            store, monthly_path=args.monthly, nucc_path=args.nucc,
            monthly_version=args.version or "manual",
            weekly_paths=args.weekly or [],
            othername_path=args.othername,
            practice_location_path=args.practice_location,
            endpoint_path=args.endpoint,
            landing_root=args.landing_root)
    else:
        tmp = args.from_fixtures or tempfile.mkdtemp(prefix="nppes_synth_")
        manifest = synth.generate(tmp)
        report = pipeline.run(
            store, monthly_path=manifest["monthly_path"],
            nucc_path=manifest["nucc_path"],
            monthly_version=manifest["monthly_version"],
            monthly_header_count=manifest["monthly_header_count"],
            weekly_paths=manifest["weekly_paths"],
            othername_path=manifest["othername_path"],
            practice_location_path=manifest["practice_location_path"],
            endpoint_path=manifest["endpoint_path"],
            landing_root=args.landing_root)
    print(json.dumps({"dq_all_passed": report["dq_all_passed"],
                      "dq": report["stages"]["dq"]}, indent=2))
    return 0 if report["dq_all_passed"] else 1


def _cmd_lookup(args) -> int:
    store = NppesStore(args.db)
    res = api.lookup_provider(store, args.npi)
    print(json.dumps(res, indent=2, default=str))
    return 0 if res else 1


def _cmd_query(args) -> int:
    store = NppesStore(args.db)
    filters = {}
    for f in args.filter or []:
        k, _, v = f.partition("=")
        if v.isdigit():
            v = int(v)
        filters[k] = v
    res = api.query_dataset(store, args.dataset, filters=filters,
                            limit=args.limit)
    print(json.dumps(res, indent=2, default=str))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="connectors.nppes.cli")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("discover"); sp.set_defaults(fn=_cmd_discover)

    sp = sub.add_parser("build")
    sp.add_argument("--db", default="nppes.db")
    sp.add_argument("--monthly"); sp.add_argument("--nucc")
    sp.add_argument("--version"); sp.add_argument("--weekly", action="append")
    sp.add_argument("--othername"); sp.add_argument("--practice-location")
    sp.add_argument("--endpoint"); sp.add_argument("--from-fixtures")
    sp.add_argument("--landing-root")
    sp.set_defaults(fn=_cmd_build)

    sp = sub.add_parser("lookup")
    sp.add_argument("--db", default="nppes.db"); sp.add_argument("--npi", required=True)
    sp.set_defaults(fn=_cmd_lookup)

    sp = sub.add_parser("query")
    sp.add_argument("--db", default="nppes.db")
    sp.add_argument("--dataset", required=True)
    sp.add_argument("--filter", action="append")
    sp.add_argument("--limit", type=int, default=20)
    sp.set_defaults(fn=_cmd_query)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
