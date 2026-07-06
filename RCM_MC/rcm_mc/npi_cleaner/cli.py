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
    ap.add_argument("file", nargs="?", default=None,
                    help="claims file to clean (.csv/.tsv/.xlsx, X12 "
                         ".837/.835, or a .zip batch of files); optional "
                         "when using --refdata-status/--refdata-pull")
    ap.add_argument("--refdata-status", action="store_true",
                    help="show reference-data pack status (installed, "
                         "rows, source) and exit")
    ap.add_argument("--refdata-pull", default=None, metavar="PACK",
                    help="download and install a reference pack "
                         "(taxonomy|icd10cm|hcpcs|leie|all), then exit; "
                         "needs outbound HTTPS to the public source")
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
    ap.add_argument("--bundle", action="store_true",
                    help="also write <stem>_bundle.zip with every artifact "
                         "(cleaned file, workbook, change log, exec report, "
                         "scorecard JSON, data dictionary, worklists)")
    args = ap.parse_args(argv)

    if args.refdata_status or args.refdata_pull:
        from . import refdata_packs as _packs
        if args.refdata_pull:
            ids = (list(_packs.PACKS) if args.refdata_pull == "all"
                   else [args.refdata_pull])
            rc = 0
            for pid in ids:
                try:
                    info = _packs.pull(pid)
                    sys.stdout.write(
                        f"{pid}: {info['rows']:,} rows from "
                        f"{info['source']}\n")
                except ValueError as exc:
                    sys.stderr.write(f"{pid}: {exc}\n")
                    rc = 1
            if rc:
                return rc
        for p in _packs.status():
            state = (f"{p['rows']:,} rows · "
                     f"{p.get('source', '')}" if p["installed"]
                     else "not installed")
            sys.stdout.write(f"{p['id']:10s} {state}\n")
        return 0

    if not args.file:
        ap.error("a claims file is required (or use --refdata-status / "
                 "--refdata-pull)")
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
    # clean_path handles both sizes: small files take the normal in-memory
    # pipeline, huge ones stream in bounded-memory chunks (bigfile.py) —
    # the cron door accepts the same 10 GB extracts the web door does.
    from . import bigfile
    res = bigfile.clean_path(str(src), src.name,
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

    if args.bundle:
        import csv as _csvm
        import io as _iom
        import zipfile as _zfm
        from datetime import datetime, timezone
        from .exec_report import build_exec_report
        bpath = outdir / (src.stem + "_bundle.zip")
        with _zfm.ZipFile(bpath, "w", _zfm.ZIP_DEFLATED) as z:
            for path, name_ in ((res.out_path, res.out_name),
                                (res.workbook_path, res.workbook_name),
                                (res.changelog_path, res.changelog_name),
                                (res.companion_path, res.companion_name)):
                if path:
                    z.write(path, name_)
            z.writestr("exec_report.html", build_exec_report(
                sc, src.name,
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")))
            z.writestr("scorecard.json",
                       json.dumps(sc, indent=2, default=str))
            if res.dictionary:
                z.writestr("data_dictionary.csv", engine.dictionary_csv(res))
            if res.population:
                from . import analytics as _analytics
                enc_csv = _analytics.encounters_csv(res.population)
                if enc_csv:
                    z.writestr("encounters.csv", enc_csv)
            if res.flag_rows and res.out_path \
                    and res.out_name.endswith(".csv"):
                # Bounded per rule inside the bundle (mirrors the server
                # bundle): 70 rules × 50k rows of StringIO is GBs.
                _WL_BUNDLE_ROWS = 5000
                want: dict = {}
                for rule, idxs in res.flag_rows.items():
                    for i2 in idxs[:_WL_BUNDLE_ROWS]:
                        want.setdefault(i2, []).append(rule)
                sinks = {rule: _iom.StringIO()
                         for rule, idxs in res.flag_rows.items() if idxs}
                writers = {k: _csvm.writer(v) for k, v in sinks.items()}
                with open(res.out_path, encoding="utf-8") as fh:
                    rd = _csvm.reader(fh)
                    hdr = next(rd, None)
                    if hdr:
                        for w_ in writers.values():
                            w_.writerow(["_row"] + hdr)
                    for i2, row in enumerate(rd, start=1):
                        for rule in want.get(i2, ()):
                            writers[rule].writerow([i2] + row)
                for rule, sink in sinks.items():
                    safe = "".join(c for c in rule
                                   if c.isalnum() or c == "-")
                    z.writestr(f"worklists/{safe}.csv", sink.getvalue())
        written.append(str(bpath))

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
