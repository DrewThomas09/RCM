"""CLI surface for the CDD analytics registry.

Run with ``python -m rcm_mc.cdd``. This is the wired entrypoint: every feature
is reachable here because it registered itself. Examples::

    python -m rcm_mc.cdd list
    python -m rcm_mc.cdd run NEW-01 --internal
    python -m rcm_mc.cdd run NEW-01            # partner view
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from . import registry


def _cmd_list(_: argparse.Namespace) -> int:
    for f in registry.all_features():
        print(f"{f.feature_id:<12} {f.audience:<8} {f.title}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    try:
        out = registry.run(args.feature_id, internal_mode=args.internal)
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(out, indent=2, default=str))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="rcm_mc.cdd",
        description="CDD analytics: enumerate and run registered exhibits.",
    )
    sub = ap.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List registered CDD features.")
    p_list.set_defaults(func=_cmd_list)

    p_run = sub.add_parser("run", help="Run a feature and print its exhibit.")
    p_run.add_argument("feature_id", help="Feature id, e.g. NEW-01.")
    p_run.add_argument(
        "--internal",
        action="store_true",
        help="Internal mode: include assumption nodes and internal-only series.",
    )
    p_run.set_defaults(func=_cmd_run)
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
