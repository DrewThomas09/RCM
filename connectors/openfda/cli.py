"""CLI for the openFDA connector.

Stdlib ``argparse`` only, mirroring the rest of RCM-MC's CLIs. Subcommands::

    python -m connectors.openfda.cli discover
    python -m connectors.openfda.cli registry
    python -m connectors.openfda.cli backfill   [--endpoint K ...] [--root DIR]
    python -m connectors.openfda.cli incremental [--lookback-days N] [--root DIR]
    python -m connectors.openfda.cli query <dataset_id> [--filter f=v ...]
                                            [--select c,c] [--sort -c] [--limit N]
    python -m connectors.openfda.cli lookup-drug   <ndc>   [--root DIR]
    python -m connectors.openfda.cli lookup-device <product_code> [--root DIR]
    python -m connectors.openfda.cli dq [--reconcile] [--root DIR]

The ``--root`` dir holds the SQLite db, the raw lake, and STATE/PROGRESS/
DECISIONS Markdown — everything needed to resume a hard-killed run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import dq as dq_mod
from . import market_map as mm
from .connector import OpenFdaConnector
from .endpoints import ENDPOINTS
from .lookup import lookup_device, lookup_drug
from .pipeline import OpenFdaPipeline, PipelineConfig
from .query import AggregateResult, QueryError, aggregate, query
from .raw_store import RawStore, parquet_available
from .registry import registry_as_dicts
from .rxnorm_adapter import make_resolver
from .state import StateStore
from .tables import OpenFdaStore


def _paths(root: str) -> Dict[str, str]:
    base = Path(root)
    base.mkdir(parents=True, exist_ok=True)
    return {
        "db": str(base / "openfda.db"),
        "raw": str(base / "raw"),
        "state": str(base),
    }


def _open(root: str) -> Dict[str, Any]:
    p = _paths(root)
    return {
        "store": OpenFdaStore(p["db"]),
        "raw": RawStore(p["raw"]),
        "state": StateStore(p["state"]),
        "paths": p,
    }


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def cmd_discover(_args: argparse.Namespace) -> int:
    conn = OpenFdaConnector()
    _print([{"key": s.key, "noun": s.noun, "path": s.path,
             "target_table": s.target_table, "date_field": s.date_field,
             "refresh_cadence": s.refresh_cadence}
            for s in conn.discover()])
    return 0


def cmd_registry(_args: argparse.Namespace) -> int:
    _print(registry_as_dicts())
    return 0


def _resolver(args: argparse.Namespace):
    return make_resolver() if getattr(args, "resolve_rxnorm", False) else None


def cmd_backfill(args: argparse.Namespace) -> int:
    ctx = _open(args.root)
    pipe = OpenFdaPipeline(
        ctx["store"], ctx["state"], ctx["raw"],
        config=PipelineConfig(mode="backfill", backfill_start=args.start),
        rxcui_resolver=_resolver(args))
    states = pipe.run(endpoints=args.endpoint or None)
    _print({k: {"status": s.status, "rows": s.rows_ingested,
                "requests": s.requests_made} for k, s in states.items()})
    return 0


def cmd_incremental(args: argparse.Namespace) -> int:
    ctx = _open(args.root)
    pipe = OpenFdaPipeline(
        ctx["store"], ctx["state"], ctx["raw"],
        config=PipelineConfig(mode="incremental",
                              incremental_lookback_days=args.lookback_days),
        rxcui_resolver=_resolver(args))
    states = pipe.run(endpoints=args.endpoint or None)
    _print({k: {"status": s.status, "rows": s.rows_ingested}
            for k, s in states.items()})
    return 0


def cmd_aggregate(args: argparse.Namespace) -> int:
    ctx = _open(args.root)
    filters: Dict[str, Any] = {}
    for f in args.filter or []:
        if "=" in f:
            k, v = f.split("=", 1)
            filters[k] = v
    try:
        res = aggregate(ctx["store"], args.dataset,
                        group_by=args.group_by.split(","), filters=filters,
                        limit=args.limit)
    except QueryError as exc:
        print(f"aggregate error: {exc}", file=sys.stderr)
        return 2
    _print(res.as_dict())
    return 0


def cmd_market_map(args: argparse.Namespace) -> int:
    ctx = _open(args.root)
    fn = mm.MARKET_MAPS[args.name]
    kwargs: Dict[str, Any] = {"limit": args.limit}
    if args.name == "clearance_timeline" and args.product_code:
        kwargs["product_code"] = args.product_code
    _print({"market_map": args.name, "rows": fn(ctx["store"], **kwargs)})
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    ctx = _open(args.root)
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
        res = query(ctx["store"], args.dataset, filters=filters, select=select,
                    sort=sort, limit=args.limit, offset=args.offset)
    except QueryError as exc:
        print(f"query error: {exc}", file=sys.stderr)
        return 2
    _print(res.as_dict())
    return 0


def cmd_lookup_drug(args: argparse.Namespace) -> int:
    ctx = _open(args.root)
    _print(lookup_drug(ctx["store"], args.ndc))
    return 0


def cmd_lookup_device(args: argparse.Namespace) -> int:
    ctx = _open(args.root)
    _print(lookup_device(ctx["store"], args.product_code))
    return 0


def cmd_dq(args: argparse.Namespace) -> int:
    ctx = _open(args.root)
    conn = OpenFdaConnector() if args.reconcile else None
    report = dq_mod.run_all(ctx["store"], connector=conn, reconcile=args.reconcile)
    _print(report.as_dict())
    return 0 if report.ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="connectors.openfda.cli",
        description="openFDA PEDesk connector")
    p.add_argument("--root", default="./.openfda_data",
                   help="working dir for db + raw lake + STATE files")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("discover").set_defaults(func=cmd_discover)
    sub.add_parser("registry").set_defaults(func=cmd_registry)

    b = sub.add_parser("backfill")
    b.add_argument("--endpoint", action="append", choices=sorted(ENDPOINTS))
    b.add_argument("--start", default="20040101")
    b.add_argument("--resolve-rxnorm", action="store_true",
                   help="resolve NDC->RxCUI live via RxNav (needs egress)")
    b.set_defaults(func=cmd_backfill)

    inc = sub.add_parser("incremental")
    inc.add_argument("--endpoint", action="append", choices=sorted(ENDPOINTS))
    inc.add_argument("--lookback-days", type=int, default=7)
    inc.add_argument("--resolve-rxnorm", action="store_true",
                     help="resolve NDC->RxCUI live via RxNav (needs egress)")
    inc.set_defaults(func=cmd_incremental)

    agg = sub.add_parser("aggregate")
    agg.add_argument("dataset")
    agg.add_argument("--group-by", required=True, help="comma-separated columns")
    agg.add_argument("--filter", action="append")
    agg.add_argument("--limit", type=int, default=50)
    agg.set_defaults(func=cmd_aggregate)

    mmp = sub.add_parser("market-map")
    mmp.add_argument("name", choices=sorted(mm.MARKET_MAPS))
    mmp.add_argument("--product-code")
    mmp.add_argument("--limit", type=int, default=100)
    mmp.set_defaults(func=cmd_market_map)

    q = sub.add_parser("query")
    q.add_argument("dataset")
    q.add_argument("--filter", action="append")
    q.add_argument("--select")
    q.add_argument("--sort")
    q.add_argument("--limit", type=int, default=50)
    q.add_argument("--offset", type=int, default=0)
    q.set_defaults(func=cmd_query)

    ld = sub.add_parser("lookup-drug")
    ld.add_argument("ndc")
    ld.set_defaults(func=cmd_lookup_drug)

    lv = sub.add_parser("lookup-device")
    lv.add_argument("product_code")
    lv.set_defaults(func=cmd_lookup_device)

    d = sub.add_parser("dq")
    d.add_argument("--reconcile", action="store_true")
    d.set_defaults(func=cmd_dq)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    # Root is consumed by the per-command opener; make sure subcommands see it.
    if not hasattr(args, "root"):
        args.root = "./.openfda_data"
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
