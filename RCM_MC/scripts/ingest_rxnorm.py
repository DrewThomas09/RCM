#!/usr/bin/env python3
"""Ingest the RxNorm / RxNav slice into a SQLite DB.

Drives the resumable, idempotent pipeline in
``rcm_mc/data_public/rxnorm/pipeline.py``. Offline by default (uses the
committed representative seed — this environment's network policy blocks
``rxnav.nlm.nih.gov``); pass ``--live`` to hit the real RxNav API where the
environment permits.

The pipeline owns the NDC→RxCUI crosswalk plus the concept / related /
drug-class tables, maintains ``STATE.md`` + ``PROGRESS.log`` next to the
connector, and resumes from ``STATE.md`` after a hard kill.

Run::

    python scripts/ingest_rxnorm.py --db rx.db            # offline seed
    python scripts/ingest_rxnorm.py --db rx.db --live     # live RxNav
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make the package importable when run as a loose script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rcm_mc.data_public.rxnorm import run, validation  # noqa: E402
from rcm_mc.portfolio.store import PortfolioStore  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Ingest the RxNorm slice.")
    ap.add_argument("--db", required=True, help="SQLite DB path")
    ap.add_argument("--live", action="store_true",
                    help="Use the live RxNav API (default: offline seed)")
    ap.add_argument("--state-dir", default=None,
                    help="Where to keep STATE.md/PROGRESS.log "
                         "(default: alongside the connector)")
    args = ap.parse_args(argv)

    store = PortfolioStore(args.db)
    report = run(store, live=args.live,
                 state_dir=Path(args.state_dir) if args.state_dir else None)
    report["openfda_join"] = validation.openfda_ndc_match_rate(store)
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
