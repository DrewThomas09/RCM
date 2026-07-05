"""`rcm-mc npi-clean` — the claims cleaner as a batch command.

The web page is the interactive front door; this is the cron/pipeline door.
Runs the exact same engine (same rules, same scorecard, same audit trail)
on a local file and writes every artifact beside the input, so scripted
nightly extracts get the identical treatment a drag-and-drop upload gets —
including a terminal quality grade suitable for CI-style gating (exit code
1 when the grade falls below a threshold, if one is set).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Optional


def main(argv: Optional[list] = None, prog: str = "rcm-mc npi-clean") -> int:
    ap = argparse.ArgumentParser(
        prog=prog,
        description="Clean a claims file offline (CSV/TSV/XLSX) — same "
                    "engine as /npi-cleaner, batch-friendly.")
    ap.add_argument("file",
                    help="claims file to clean (.csv/.tsv/.xlsx/.837 X12)")
    ap.add_argument("--profile", default=None, metavar="NAME",
                    help="apply a saved cleaning profile (rule suite + "
                         "thresholds) by name")
    ap.add_argument("--mapping", default=None, metavar="NAME",
                    help="apply a saved column-mapping template by name")
    ap.add_argument("--no-dedupe", action="store_true",
                    help="keep exact-duplicate rows")
    ap.add_argument("--deid", action="store_true",
                    help="de-identify patient PHI in the output")
    ap.add_argument("--json", action="store_true",
                    help="print the full scorecard as JSON instead of the "
                         "human summary")
    ap.add_argument("--min-score", type=int, default=None, metavar="N",
                    help="exit 1 if the quality score is below N (CI gate)")
    ap.add_argument("--outdir", default=None,
                    help="directory for outputs (default: beside the input)")
    args = ap.parse_args(argv)

    src = Path(args.file)
    if not src.is_file():
        sys.stderr.write(f"error: no such file: {src}\n")
        return 2

    from . import engine
    prof_cfg = None
    if args.profile:
        from . import profiles as _profiles
        prof_cfg = _profiles.get_profile(args.profile)
        if prof_cfg is None:
            sys.stderr.write(f"error: no such profile: {args.profile}\n")
            return 2
    overrides = None
    if args.mapping:
        from . import mappings as _mappings
        overrides = _mappings.get_mapping(args.mapping)
        if overrides is None:
            sys.stderr.write(
                f"error: no such mapping template: {args.mapping}\n")
            return 2
    res = engine.clean_bytes(src.read_bytes(), src.name,
                             drop_duplicates=not args.no_dedupe,
                             deid=args.deid, profile=prof_cfg,
                             overrides=overrides)
    sc = res.as_scorecard()

    outdir = Path(args.outdir) if args.outdir else src.parent
    outdir.mkdir(parents=True, exist_ok=True)
    written = []
    for path, name in ((res.out_path, res.out_name),
                       (res.changelog_path, res.changelog_name),
                       (res.companion_path, res.companion_name),
                       (res.workbook_path, res.workbook_name)):
        if path:
            dest = outdir / name
            shutil.copyfile(path, dest)
            written.append(str(dest))

    if args.json:
        sc["written"] = written
        sys.stdout.write(json.dumps(sc, indent=2, default=str) + "\n")
    else:
        q = sc.get("quality") or {}
        sys.stdout.write(
            f"{src.name}: grade {q.get('letter', '—')} "
            f"({q.get('score', '—')}/100) · "
            f"{sc.get('rows_in', 0):,} rows in → "
            f"{sc.get('rows_out', 0):,} out · "
            f"{sc.get('repairs_total', 0):,} repairs · "
            f"{sc.get('changes_logged', 0):,} cells changed\n")
        sanity = sc.get("sanity") or {}
        if sanity:
            sys.stdout.write("findings:\n")
            for rule, n in sorted(sanity.items(), key=lambda kv: -kv[1]):
                sys.stdout.write(f"  {rule:32s} {n:>8,}\n")
        for w in written:
            sys.stdout.write(f"wrote {w}\n")

    if args.min_score is not None:
        score = int((sc.get("quality") or {}).get("score") or 0)
        if score < args.min_score:
            sys.stderr.write(
                f"quality gate failed: score {score} < {args.min_score}\n")
            return 1
    return 0
