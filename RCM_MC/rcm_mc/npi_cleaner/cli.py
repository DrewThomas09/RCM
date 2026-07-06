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


def _fmt_ts(ts) -> str:
    """Epoch float → readable UTC minute. Guarded: a NULL/garbage timestamp
    must render as a dash while listing, never raise mid-table."""
    from datetime import datetime, timezone
    try:
        return datetime.fromtimestamp(
            float(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError, OSError, OverflowError):
        return "—"


def _emit_json(obj) -> int:
    """Print a management payload as JSON (honoring the global --json flag)
    and return the success exit code."""
    sys.stdout.write(json.dumps(obj, indent=2, default=str) + "\n")
    return 0


def _handle_mgmt(args) -> Optional[int]:
    """Profiles / mapping-templates / run-history / wishlist CRUD from the
    CLI — the same stores the web UI edits, exposed to cron and scripts.

    Returns an exit code when a management flag was supplied (short-circuit,
    exactly like --refdata-status), or None to fall through to file
    cleaning. Store modules are imported lazily and every mutating call is
    guarded so a broken/empty store lists empty and returns 0 rather than
    tracebacking. Not-found / invalid args write to stderr and return 2,
    mirroring the existing --profile / --mapping error style.
    """
    as_json = args.json

    # ---- cleaning profiles ----
    if args.list_profiles:
        from . import profiles as _profiles
        rows = _profiles.list_profiles()
        if as_json:
            return _emit_json(rows)
        if not rows:
            sys.stdout.write("(no profiles)\n")
            return 0
        for p in rows:
            sys.stdout.write(
                f"{str(p.get('name', '')):24s} "
                f"{_fmt_ts(p.get('updated'))}  "
                f"disabled={len(p.get('disabled_rules') or []):<3d} "
                f"accepted={len(p.get('accepted_rules') or []):<3d}\n")
        return 0

    if args.show_profile is not None:
        from . import profiles as _profiles
        cfg = _profiles.get_profile(args.show_profile)
        if cfg is None:
            sys.stderr.write(
                f"error: no such profile: {args.show_profile}\n")
            return 2
        if as_json:
            return _emit_json(cfg)
        sys.stdout.write(f"profile: {cfg.get('name', args.show_profile)}\n")
        sys.stdout.write(
            "  disabled_rules: "
            f"{', '.join(cfg.get('disabled_rules') or []) or '—'}\n")
        sys.stdout.write(
            "  accepted_rules: "
            f"{', '.join(cfg.get('accepted_rules') or []) or '—'}\n")
        thr = cfg.get("thresholds") or {}
        for k in sorted(thr):
            sys.stdout.write(f"  {k}: {thr[k]}\n")
        return 0

    if args.delete_profile is not None:
        from . import profiles as _profiles
        try:
            ok = _profiles.delete_profile(args.delete_profile)
        except Exception:  # noqa: BLE001 — a broken store must not traceback
            ok = False
        if not ok:
            sys.stderr.write(
                f"error: no such profile: {args.delete_profile}\n")
            return 2
        if as_json:
            return _emit_json({"deleted": args.delete_profile})
        sys.stdout.write(f"deleted profile: {args.delete_profile}\n")
        return 0

    # ---- mapping templates ----
    if args.list_mappings:
        from . import mappings as _mappings
        rows = _mappings.list_mappings()
        if as_json:
            return _emit_json(rows)
        if not rows:
            sys.stdout.write("(no mapping templates)\n")
            return 0
        for m in rows:
            sys.stdout.write(
                f"{str(m.get('name', '')):24s} "
                f"{_fmt_ts(m.get('updated'))}  "
                f"roles={int(m.get('roles') or 0)}\n")
        return 0

    if args.show_mapping is not None:
        from . import mappings as _mappings
        mp = _mappings.get_mapping(args.show_mapping)
        if mp is None:
            sys.stderr.write(
                f"error: no such mapping template: {args.show_mapping}\n")
            return 2
        if as_json:
            return _emit_json(mp)
        sys.stdout.write(f"mapping: {args.show_mapping}\n")
        for role in sorted(mp):
            sys.stdout.write(f"  {role:28s} -> {mp[role]}\n")
        return 0

    if args.delete_mapping is not None:
        from . import mappings as _mappings
        try:
            ok = _mappings.delete_mapping(args.delete_mapping)
        except Exception:  # noqa: BLE001
            ok = False
        if not ok:
            sys.stderr.write(
                f"error: no such mapping template: {args.delete_mapping}\n")
            return 2
        if as_json:
            return _emit_json({"deleted": args.delete_mapping})
        sys.stdout.write(f"deleted mapping template: {args.delete_mapping}\n")
        return 0

    # ---- run history ----
    if args.history is not None:
        from . import history as _history
        n = args.history if isinstance(args.history, int) else 20
        rows = _history.list_runs(max(1, n))
        if as_json:
            return _emit_json(rows)
        if not rows:
            sys.stdout.write("(no runs recorded)\n")
            return 0
        for r in rows:
            sys.stdout.write(
                f"{str(r.get('run_id', '')):14s} "
                f"{_fmt_ts(r.get('ts'))}  "
                f"{str(r.get('letter', '—')):2s} "
                f"{int(r.get('score') or 0):3d}/100  "
                f"{int(r.get('rows_in') or 0):>8,} → "
                f"{int(r.get('rows_out') or 0):<8,}  "
                f"{str(r.get('file_name', ''))}\n")
        return 0

    if args.show_run is not None:
        from . import history as _history
        run = _history.get_run(args.show_run)
        if run is None:
            sys.stderr.write(f"error: no such run: {args.show_run}\n")
            return 2
        if as_json:
            return _emit_json(run)
        sys.stdout.write(
            f"run: {run.get('run_id')}  {_fmt_ts(run.get('ts'))}\n")
        sys.stdout.write(f"  file:  {run.get('file_name')}\n")
        sys.stdout.write(
            f"  grade: {run.get('letter', '—')} "
            f"({run.get('score', '—')}/100)\n")
        sys.stdout.write(
            f"  rows:  {int(run.get('rows_in') or 0):,} in → "
            f"{int(run.get('rows_out') or 0):,} out · "
            f"{int(run.get('dupes') or 0):,} dupes · "
            f"{int(run.get('changes') or 0):,} changes\n")
        san = run.get("sanity") or {}
        if san:
            sys.stdout.write("  findings:\n")
            for rule, cnt in sorted(san.items(),
                                    key=lambda kv: -int(kv[1] or 0)):
                sys.stdout.write(
                    f"    {str(rule):32s} {int(cnt or 0):>8,}\n")
        return 0

    if args.compare_runs is not None:
        from . import history as _history
        a_id, b_id = args.compare_runs
        cmp_ = _history.compare_runs(a_id, b_id)
        if cmp_ is None:
            sys.stderr.write(
                f"error: could not compare runs {a_id} and {b_id} "
                "(one or both not found)\n")
            return 2
        if as_json:
            return _emit_json(cmp_)
        a = cmp_.get("a") or {}
        b = cmp_.get("b") or {}
        sys.stdout.write(
            f"A {a.get('run_id')} ({a.get('file_name')}): "
            f"{a.get('score')}/100\n")
        sys.stdout.write(
            f"B {b.get('run_id')} ({b.get('file_name')}): "
            f"{b.get('score')}/100\n")
        sys.stdout.write(f"score delta: {cmp_.get('score_delta'):+d}\n")
        for d in cmp_.get("rule_delta") or []:
            sys.stdout.write(
                f"  {str(d.get('rule')):32s} "
                f"{int(d.get('a') or 0):>6,} → "
                f"{int(d.get('b') or 0):<6,} "
                f"({int(d.get('delta') or 0):+d})\n")
        return 0

    # ---- wishlist ----
    if args.wishlist is not None:
        from . import wishlist as _wishlist
        status = args.wishlist or None
        rows = _wishlist.list_requests(status)
        if as_json:
            return _emit_json(rows)
        if not rows:
            sys.stdout.write("(no wishlist requests)\n")
            return 0
        for r in rows:
            sys.stdout.write(
                f"#{int(r.get('id') or 0):<5d} "
                f"{_fmt_ts(r.get('created'))}  "
                f"{str(r.get('status', '')):9s} "
                f"{str(r.get('category', '')):11s} "
                f"{str(r.get('title', ''))}\n")
        return 0

    if args.wishlist_add is not None:
        from . import wishlist as _wishlist
        category, title = args.wishlist_add
        try:
            rec = _wishlist.add_request(category, title)
        except (ValueError, TypeError) as exc:
            sys.stderr.write(f"error: {exc}\n")
            return 2
        except Exception:  # noqa: BLE001
            sys.stderr.write("error: could not add wishlist request\n")
            return 2
        if as_json:
            return _emit_json(rec)
        sys.stdout.write(
            f"added wishlist request #{rec.get('id')} "
            f"({rec.get('category')}): {rec.get('title')}\n")
        return 0

    if args.wishlist_status is not None:
        from . import wishlist as _wishlist
        rid_s, new_status = args.wishlist_status
        try:
            rid = int(rid_s)
        except (TypeError, ValueError):
            sys.stderr.write(f"error: invalid request id: {rid_s}\n")
            return 2
        try:
            ok = _wishlist.set_status(rid, new_status)
        except Exception:  # noqa: BLE001
            ok = False
        if not ok:
            sys.stderr.write(
                f"error: could not set status (unknown id {rid} or invalid "
                f"status '{new_status}'; valid: "
                "open/planned/shipped/declined)\n")
            return 2
        if as_json:
            return _emit_json({"id": rid, "status": new_status})
        sys.stdout.write(f"wishlist #{rid} → {new_status}\n")
        return 0

    if args.wishlist_delete is not None:
        from . import wishlist as _wishlist
        try:
            rid = int(args.wishlist_delete)
        except (TypeError, ValueError):
            sys.stderr.write(
                f"error: invalid request id: {args.wishlist_delete}\n")
            return 2
        try:
            ok = _wishlist.delete_request(rid)
        except Exception:  # noqa: BLE001
            ok = False
        if not ok:
            sys.stderr.write(f"error: no such wishlist request: {rid}\n")
            return 2
        if as_json:
            return _emit_json({"deleted": rid})
        sys.stdout.write(f"deleted wishlist request #{rid}\n")
        return 0

    return None


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
    ap.add_argument("--enrich", action="store_true",
                    help="go online: verify & recover NPIs against NPPES, "
                         "fill blank provider fields, resolve drugs "
                         "(needs outbound network)")
    ap.add_argument("--deep", action="store_true",
                    help="deep recovery — the full networked v49 pipeline "
                         "(implies --enrich; slower, needs network)")
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
    # Management (CRUD) subcommands — profiles / mapping templates / run
    # history / wishlist, usable from cron and scripts, not just the web UI.
    # Each is optional, short-circuits, and returns an exit code, exactly
    # like --refdata-status above (the positional file stays optional).
    ap.add_argument("--list-profiles", action="store_true",
                    help="list saved cleaning profiles and exit")
    ap.add_argument("--show-profile", default=None, metavar="NAME",
                    help="print one saved profile's config and exit")
    ap.add_argument("--delete-profile", default=None, metavar="NAME",
                    help="delete a saved profile and exit")
    ap.add_argument("--list-mappings", action="store_true",
                    help="list saved column-mapping templates and exit")
    ap.add_argument("--show-mapping", default=None, metavar="NAME",
                    help="print one mapping template (role -> column) and exit")
    ap.add_argument("--delete-mapping", default=None, metavar="NAME",
                    help="delete a mapping template and exit")
    ap.add_argument("--history", nargs="?", type=int, const=20, default=None,
                    metavar="N",
                    help="list the last N recorded runs (default 20) and exit")
    ap.add_argument("--show-run", default=None, metavar="RUN_ID",
                    help="print one recorded run's summary and exit")
    ap.add_argument("--compare-runs", nargs=2, default=None,
                    metavar=("A", "B"),
                    help="compare two recorded runs by id and exit")
    ap.add_argument("--wishlist", nargs="?", const="", default=None,
                    metavar="STATUS",
                    help="list wishlist requests (optional status filter: "
                         "open/planned/shipped/declined) and exit")
    ap.add_argument("--wishlist-add", nargs=2, default=None,
                    metavar=("CATEGORY", "TITLE"),
                    help="add a wishlist request (category + title) and exit")
    ap.add_argument("--wishlist-status", nargs=2, default=None,
                    metavar=("ID", "NEWSTATUS"),
                    help="set a wishlist request's status and exit")
    ap.add_argument("--wishlist-delete", default=None, metavar="ID",
                    help="delete a wishlist request by id and exit")
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

    mgmt_rc = _handle_mgmt(args)
    if mgmt_rc is not None:
        return mgmt_rc

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
                             overrides=overrides,
                             enrich=args.enrich or args.deep,
                             deep=args.deep)
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
