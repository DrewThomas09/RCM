"""``rcm-mc deal new`` — one-command diligence pipeline orchestrator.

Turns the Monday-to-IC workflow into a single invocation::

    rcm-mc deal new --dir ~/deals/acme --ccn 360180 \
                    --data-source ~/Downloads/acme_pack.zip

which sequences:

1. **Intake** — runs the wizard (HCRIS pre-fill if ``--ccn`` supplied) and
   writes ``{dir}/actual.yaml``
2. **Ingest** — if a seller data pack is provided, turns it into
   ``{dir}/intake_data/`` (canonical CSVs + audit report)
3. **Run** — the main ``rcm-mc run`` pipeline with calibration
   enabled when ingest produced usable data; writes to ``{dir}/outputs/``
4. **Deal state** — writes ``{dir}/deal.yaml`` capturing hospital name,
   CCN, timestamps, output paths, and completion status

Each step can be skipped with a flag (``--no-intake`` if the analyst
already has ``actual.yaml``, ``--no-data`` if no seller data). Failures
in optional steps (ingest) are recoverable — the pipeline continues
uncalibrated and the deal.yaml records the reason.

This brick is pure orchestration over existing CLI entry points; no new
simulation or modeling logic.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# ── Deal state ─────────────────────────────────────────────────────────────

def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _default_benchmark_path() -> str:
    """Ship-with-package benchmark config.

    Post-refactor: this file is rcm_mc/deals/deal.py. The benchmark
    YAML lives at the project root under configs/, which is
    parent.parent.parent.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    return str(repo_root / "configs" / "benchmark.yaml")


def _write_deal_yaml(deal_dir: Path, state: Dict[str, Any]) -> Path:
    path = deal_dir / "deal.yaml"
    with open(path, "w") as f:
        yaml.safe_dump(state, f, sort_keys=False)
    return path


def _load_deal_yaml(deal_dir: Path) -> Dict[str, Any]:
    path = deal_dir / "deal.yaml"
    if not path.is_file():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _capture_baseline(
    actual_path: Path,
    benchmark_path: str,
    outputs_dir: Path,
) -> Dict[str, Any]:
    """Snapshot blended KPIs and modeled drag at deal close.

    Pulled from the actual_cfg + benchmark_cfg + summary.csv so a later
    ``deal track`` call can compute variance without re-running anything.
    """
    from ..infra.config import load_and_validate
    from ..data.intake import _blended_mean
    from ..analysis.pressure_test import _TARGET_METRICS

    baseline: Dict[str, Any] = {
        "captured_at": _now_utc(),
        "blended": {},
        "benchmark_targets": {},
    }
    try:
        actual = load_and_validate(str(actual_path))
        bench = load_and_validate(str(benchmark_path))
    except (FileNotFoundError, ValueError):
        return baseline

    # Align metric names with the actuals loader's canonical keys so `deal
    # track` can compare the two sources without a translation shim.
    key_to_name = {
        "idr_blended": "idr",
        "fwr_blended": "fwr",
        "dar_blended": "dar_clean_days",
    }
    for key, metric_name in key_to_name.items():
        path = _TARGET_METRICS[key]
        actual_val = _blended_mean(actual, path)
        bench_val = _blended_mean(bench, path)
        if actual_val is not None:
            baseline["blended"][metric_name] = float(actual_val)
        if bench_val is not None:
            baseline["benchmark_targets"][metric_name] = float(bench_val)

    # Hospital-level numbers from the actual config
    hosp = actual.get("hospital") or {}
    if "annual_revenue" in hosp:
        baseline["blended"]["annual_revenue"] = float(hosp["annual_revenue"])

    # Modeled drag (mean + P10/P90) from the summary.csv if present
    summary_path = outputs_dir / "summary.csv"
    if summary_path.is_file():
        try:
            import pandas as pd
            summary = pd.read_csv(summary_path, index_col=0)
            if "ebitda_drag" in summary.index:
                row = summary.loc["ebitda_drag"]
                baseline["modeled_ebitda_drag"] = {
                    "mean": float(row.get("mean", 0)),
                    "p10": float(row.get("p10", 0)),
                    "p90": float(row.get("p90", 0)),
                }
        except (OSError, ValueError, KeyError):
            pass

    return baseline


# ── Step runners ───────────────────────────────────────────────────────────

def _run_intake(deal_dir: Path, ccn: Optional[str]) -> Path:
    """Drive the intake wizard; returns the written actual.yaml path."""
    from ..data.intake import interactive_intake

    out = deal_dir / "actual.yaml"
    if not sys.stdin.isatty():
        raise RuntimeError(
            "intake requires an interactive terminal. Provide --actual with an "
            "existing actual.yaml, or run `rcm-mc deal new` in a TTY."
        )
    interactive_intake(str(out), ccn_prefill=ccn)
    return out


def _run_ingest(source: Path, out_dir: Path) -> Optional[str]:
    """Ingest a seller data pack. Returns the out_dir path on success, else None."""
    from ..data.ingest import ingest_path

    report = ingest_path(str(source), str(out_dir))
    return str(out_dir) if report.classified_count > 0 else None


def _run_simulation(
    *,
    actual: Path,
    benchmark: str,
    outdir: Path,
    data_dir: Optional[str],
    n_sims: int,
    partner_brief: bool,
) -> None:
    """Invoke the main run subcommand in-process."""
    from ..cli import run_main

    argv: List[str] = [
        "--actual", str(actual),
        "--benchmark", benchmark,
        "--outdir", str(outdir),
        "--n-sims", str(n_sims),
    ]
    if data_dir:
        argv += ["--actual-data-dir", data_dir]
    if partner_brief:
        argv.append("--partner-brief")
    run_main(argv, prog="rcm-mc run")


# ── Orchestrator ───────────────────────────────────────────────────────────

def create_deal(
    deal_dir: str,
    *,
    ccn: Optional[str] = None,
    data_source: Optional[str] = None,
    actual_path: Optional[str] = None,
    benchmark: Optional[str] = None,
    n_sims: int = 10_000,
    partner_brief: bool = True,
    skip_intake: bool = False,
    skip_ingest: bool = False,
    skip_run: bool = False,
) -> Dict[str, Any]:
    """Create a deal folder and sequence intake / ingest / run.

    Returns the final ``deal.yaml`` state dict. Always writes the file even
    if a step fails — the state captures ``status: "failed_at: {step}"`` so
    the analyst can recover.
    """
    root = Path(deal_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    benchmark = benchmark or _default_benchmark_path()

    state: Dict[str, Any] = {
        "deal": {
            "name": None,
            "ccn": ccn,
            "created_at": _now_utc(),
            "status": "in_progress",
            "dir": str(root),
        },
        "files": {},
        "steps": [],
    }
    _write_deal_yaml(root, state)

    # ── 1. Intake ──
    actual: Optional[Path]
    if skip_intake and actual_path:
        actual = Path(actual_path).resolve()
        state["steps"].append({"step": "intake", "skipped": True,
                               "reason": f"existing actual supplied at {actual}"})
    else:
        try:
            actual = _run_intake(root, ccn=ccn)
            state["steps"].append({"step": "intake", "status": "ok", "output": str(actual)})
        except Exception as exc:
            state["deal"]["status"] = "failed_at: intake"
            state["steps"].append({"step": "intake", "status": "failed", "error": str(exc)})
            _write_deal_yaml(root, state)
            raise

    state["files"]["actual_config"] = str(actual)
    # Read hospital.name / ccn back out of the written actual.yaml
    try:
        with open(actual) as f:
            cfg = yaml.safe_load(f) or {}
        hosp = (cfg.get("hospital") or {})
        state["deal"]["name"] = hosp.get("name")
        if hosp.get("ccn"):
            state["deal"]["ccn"] = hosp.get("ccn")
    except (OSError, yaml.YAMLError):
        pass
    _write_deal_yaml(root, state)

    # ── 2. Ingest (optional) ──
    data_dir: Optional[str] = None
    if data_source and not skip_ingest:
        intake_out = root / "intake_data"
        try:
            data_dir = _run_ingest(Path(data_source), intake_out)
            if data_dir:
                state["files"]["data_dir"] = data_dir
                state["steps"].append({"step": "ingest", "status": "ok", "output": data_dir})
            else:
                state["steps"].append({
                    "step": "ingest", "status": "no_data",
                    "note": "no signature-matching tables found; continuing uncalibrated",
                })
        except Exception as exc:
            # Ingest is optional — record and continue
            state["steps"].append({"step": "ingest", "status": "failed", "error": str(exc)})
    else:
        state["steps"].append({"step": "ingest", "skipped": True,
                               "reason": "no --data-source provided"})
    _write_deal_yaml(root, state)

    # ── 3. Run ──
    if not skip_run:
        outputs_dir = root / "outputs"
        try:
            _run_simulation(
                actual=actual,
                benchmark=benchmark,
                outdir=outputs_dir,
                data_dir=data_dir,
                n_sims=int(n_sims),
                partner_brief=partner_brief,
            )
            state["files"]["outputs"] = str(outputs_dir)
            # Common deliverables an analyst opens first
            for nm in ("report.html", "partner_brief.html",
                       "diligence_workbook.xlsx", "data_requests.md"):
                p = outputs_dir / nm
                if p.exists():
                    state["files"][nm.split(".")[0]] = str(p)
            state["steps"].append({"step": "run", "status": "ok"})
            # Snapshot baseline KPIs + modeled drag for later `deal track` calls.
            state["baseline"] = _capture_baseline(actual, benchmark, outputs_dir)
        except Exception as exc:
            state["deal"]["status"] = "failed_at: run"
            state["steps"].append({"step": "run", "status": "failed", "error": str(exc)})
            _write_deal_yaml(root, state)
            raise

    state["deal"]["status"] = "complete"
    state["deal"]["completed_at"] = _now_utc()
    _write_deal_yaml(root, state)
    return state


# ── Post-close tracker ─────────────────────────────────────────────────────

# Canonical actuals columns (case-insensitive lookup via _first_matching_col).
_ACTUALS_ALIASES: Dict[str, List[str]] = {
    "month":           ["month", "period", "date", "reporting_period"],
    "idr":             ["idr", "initial_denial_rate", "denial_rate"],
    "fwr":             ["fwr", "final_write_off_rate", "writeoff_rate", "write_off_rate"],
    "dar_clean_days":  ["dar_clean_days", "ar_days", "days_in_ar", "dar", "days_ar"],
    "net_patient_revenue": [
        "net_patient_revenue", "npsr", "net_revenue", "revenue",
    ],
}


def _parse_pct_or_decimal(v: Any) -> Optional[float]:
    """Convert raw percent-style values (13.5, 13.5%, 0.135) to decimal."""
    if v is None:
        return None
    if isinstance(v, float) and (v != v):   # NaN
        return None
    s = str(v).strip().rstrip("%").replace(",", "")
    if not s:
        return None
    try:
        f = float(s)
    except ValueError:
        return None
    if f > 1.0:
        f = f / 100.0
    return f


def _load_actuals(actuals_path: str) -> "pandas.DataFrame":  # noqa: F821
    """Load a monthly-actuals CSV with alias-aware column names."""
    import pandas as pd

    from ..core._calib_schema import _clean_currency, _first_matching_col

    df = pd.read_csv(actuals_path)
    if df.empty:
        return df

    canonical: Dict[str, Any] = {}
    for key, aliases in _ACTUALS_ALIASES.items():
        col = _first_matching_col(df, aliases)
        if col is None:
            continue
        if key == "month":
            canonical[key] = df[col].astype(str).str.strip()
        elif key in ("idr", "fwr"):
            canonical[key] = df[col].apply(_parse_pct_or_decimal)
        elif key == "dar_clean_days":
            canonical[key] = pd.to_numeric(df[col], errors="coerce")
        elif key == "net_patient_revenue":
            canonical[key] = _clean_currency(df[col])

    if not canonical or "month" not in canonical:
        raise ValueError(
            "actuals CSV must have a 'month' column and at least one KPI "
            "(idr / fwr / dar / net_patient_revenue)"
        )
    return pd.DataFrame(canonical)


def _pct_to_benchmark(actual_value: float, baseline_value: float, benchmark_value: float) -> Optional[float]:
    """Fraction of actual→benchmark gap closed by moving from baseline to actual.

    Positive = improvement toward benchmark; negative = worse than baseline;
    >1.0 = past benchmark. Returns None if the gap is zero.
    """
    gap = baseline_value - benchmark_value
    if abs(gap) < 1e-9:
        return None
    return (baseline_value - actual_value) / gap


def _track_one_month(
    month: str,
    actuals_row: Dict[str, float],
    baseline: Dict[str, Any],
) -> Dict[str, Any]:
    """Build a single tracking entry with variance + alert flags."""
    entry: Dict[str, Any] = {
        "month": month,
        "actuals": {k: v for k, v in actuals_row.items() if v is not None},
        "variance_vs_baseline": {},
        "pct_to_benchmark": {},
        "alerts": [],
    }
    blended = baseline.get("blended", {}) or {}
    targets = baseline.get("benchmark_targets", {}) or {}

    for metric in ("idr", "fwr", "dar_clean_days", "net_patient_revenue"):
        actual_v = actuals_row.get(metric)
        if actual_v is None:
            continue
        base_v = blended.get(metric)
        if base_v is None:
            continue

        variance = float(actual_v) - float(base_v)
        entry["variance_vs_baseline"][metric] = round(variance, 6)

        bench_v = targets.get(metric)
        if bench_v is not None:
            pct = _pct_to_benchmark(float(actual_v), float(base_v), float(bench_v))
            if pct is not None:
                entry["pct_to_benchmark"][metric] = round(pct, 4)

        # Alert: any "lower-is-better" metric moving the wrong way
        is_lower_better = metric in ("idr", "fwr", "dar_clean_days")
        if is_lower_better and variance > 0:
            entry["alerts"].append(
                f"{metric} moved against plan (+{variance:.4f} vs baseline)"
            )

    return entry


def track_deal(deal_dir: str, actuals_path: str) -> Dict[str, Any]:
    """Ingest a month(s) of actuals, append to deal.yaml tracking history,
    and write tracking_history.csv + tracking_report.md next to the deal.

    Supports multi-row actuals CSVs (each row = one month).
    """
    import pandas as pd

    root = Path(deal_dir).resolve()
    state = _load_deal_yaml(root)
    if not state:
        raise FileNotFoundError(f"No deal.yaml at {root}")
    baseline = state.get("baseline") or {}
    if not baseline.get("blended"):
        raise ValueError(
            f"{root}/deal.yaml has no 'baseline.blended' block; re-run `rcm-mc "
            "deal new` to capture it (or supply it manually before tracking)."
        )

    df = _load_actuals(actuals_path)
    tracking = state.setdefault("tracking", [])
    new_entries: List[Dict[str, Any]] = []

    for _, row in df.iterrows():
        month = str(row.get("month", "")).strip()
        if not month or month.lower() == "nan":
            continue
        actuals_dict = {
            k: (None if pd.isna(row.get(k)) else float(row[k]))
            for k in ("idr", "fwr", "dar_clean_days", "net_patient_revenue")
            if k in row.index and not pd.isna(row.get(k))
        }
        entry = _track_one_month(month, actuals_dict, baseline)
        tracking.append(entry)
        new_entries.append(entry)

    state["tracking"] = tracking
    _write_deal_yaml(root, state)

    # Flatten history to CSV (one row per month)
    if tracking:
        rows: List[Dict[str, Any]] = []
        for e in tracking:
            flat = {"month": e.get("month", "")}
            for k, v in (e.get("actuals") or {}).items():
                flat[f"actual_{k}"] = v
            for k, v in (e.get("variance_vs_baseline") or {}).items():
                flat[f"variance_{k}"] = v
            for k, v in (e.get("pct_to_benchmark") or {}).items():
                flat[f"pct_to_benchmark_{k}"] = v
            flat["alert_count"] = len(e.get("alerts") or [])
            rows.append(flat)
        pd.DataFrame(rows).to_csv(root / "tracking_history.csv", index=False)

    # Markdown summary (partner-friendly)
    _write_tracking_report(root, state)

    return {"new_entries": new_entries, "state": state}


def _write_tracking_report(deal_dir: Path, state: Dict[str, Any]) -> Path:
    lines: List[str] = []
    lines.append("# Post-Close Tracking Report")
    lines.append("")
    deal = state.get("deal") or {}
    name = deal.get("name") or "Unknown target"
    lines.append(f"**Target:** {name}")
    if deal.get("ccn"):
        lines.append(f"**CCN:** {deal['ccn']}")
    lines.append(f"**Generated:** {_now_utc()}")
    lines.append("")

    baseline = state.get("baseline") or {}
    blended = baseline.get("blended") or {}
    if blended:
        lines.append("## Baseline at close")
        lines.append("")
        for k, v in blended.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")

    tracking = state.get("tracking") or []
    if not tracking:
        lines.append("_No tracking data yet. Run `rcm-mc deal track --actuals FILE.csv`._")
        lines.append("")
    else:
        lines.append("## Monthly trajectory")
        lines.append("")
        lines.append("| Month | IDR | FWR | DAR days | NPSR | Alerts |")
        lines.append("|-------|-----|-----|----------|------|--------|")
        for e in tracking:
            a = e.get("actuals") or {}
            def _fmt(k):
                v = a.get(k)
                if v is None:
                    return "—"
                if k in ("idr", "fwr"):
                    return f"{v*100:.1f}%"
                if k == "net_patient_revenue":
                    return f"${v/1e6:.1f}M"
                return f"{v:.1f}"
            alerts = len(e.get("alerts") or [])
            alerts_str = f"⚠ {alerts}" if alerts else "—"
            lines.append(
                f"| {e.get('month')} | {_fmt('idr')} | {_fmt('fwr')} | "
                f"{_fmt('dar_clean_days')} | {_fmt('net_patient_revenue')} | {alerts_str} |"
            )
        lines.append("")

        # Surface any alerts verbatim for easy IC/partner reading
        all_alerts = [(e["month"], msg) for e in tracking for msg in (e.get("alerts") or [])]
        if all_alerts:
            lines.append("## Alerts")
            lines.append("")
            for month, msg in all_alerts:
                lines.append(f"- **{month}**: {msg}")
            lines.append("")

    path = deal_dir / "tracking_report.md"
    path.write_text("\n".join(lines) + "\n")
    return path


# ── CLI ─────────────────────────────────────────────────────────────────────

def _build_parser(prog: str = "rcm-mc deal") -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog=prog,
        description=(
            "Orchestrate a full diligence deal (intake → ingest → run) and "
            "track post-close monthly actuals against the baseline."
        ),
        epilog=(
            "Examples:\n"
            "  rcm-mc deal new --dir ~/deals/acme --ccn 360180\n"
            "  rcm-mc deal new --dir ~/deals/acme --ccn 360180 \\\n"
            "                  --data-source ~/Downloads/acme_pack.zip\n"
            "  rcm-mc deal track --dir ~/deals/acme --actuals may_2026.csv\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="action", required=True)

    new = sub.add_parser("new", help="Create a new deal folder and run the pipeline")
    new.add_argument("--dir", required=True, help="Deal directory (created if missing)")
    new.add_argument("--ccn", default=None, help="Medicare CCN for HCRIS pre-fill")
    new.add_argument(
        "--data-source", default=None,
        help="Optional: path to a seller data pack (zip/folder/xlsx) for calibration",
    )
    new.add_argument(
        "--actual", default=None,
        help="Optional: existing actual.yaml to use instead of running intake",
    )
    new.add_argument(
        "--benchmark", default=None,
        help=f"Benchmark YAML (default: shipped configs/benchmark.yaml)",
    )
    new.add_argument("--n-sims", type=int, default=10_000, help="Monte Carlo iterations (default 10,000)")
    new.add_argument("--no-partner-brief", dest="partner_brief", action="store_false",
                     help="Skip partner_brief.html generation")
    new.set_defaults(partner_brief=True)
    new.add_argument("--skip-intake", action="store_true",
                     help="Skip the intake wizard; requires --actual")
    new.add_argument("--skip-ingest", action="store_true",
                     help="Skip ingest even if --data-source given")
    new.add_argument("--skip-run", action="store_true",
                     help="Skip the simulation run (just set up deal folder)")

    track = sub.add_parser(
        "track",
        help="Ingest monthly actuals and compute variance against the deal baseline",
    )
    track.add_argument("--dir", required=True, help="Deal directory (contains deal.yaml)")
    track.add_argument(
        "--actuals", required=True,
        help="CSV with a 'month' column plus any of: idr, fwr, dar_clean_days, net_patient_revenue",
    )

    # Prompt 23: one-name auto-populate. Drops a pre-filled profile
    # into the portfolio store (or prints it) and reports what's
    # still missing.
    ap_new = sub.add_parser(
        "auto-populate",
        help="Look up a hospital by name/CCN, report coverage + gaps",
    )
    ap_new.add_argument("--name", required=True,
                        help="Hospital name, CCN, or 'Name, ST'")
    ap_new.add_argument("--db", default="portfolio.db",
                        help="Portfolio SQLite path")
    ap_new.add_argument("--deal-id", default=None,
                        help="Upsert the deal into the store with this ID")
    ap_new.add_argument("--json", action="store_true",
                        help="Emit the full result as JSON instead of prose")
    return ap


def _dispatch_track(args: argparse.Namespace) -> int:
    from ..infra._terminal import banner, info, success, warn

    print(banner(f"Deal track: {args.dir}"))
    try:
        result = track_deal(args.dir, args.actuals)
    except (FileNotFoundError, ValueError) as exc:
        sys.stderr.write(f"deal track failed: {exc}\n")
        return 1

    new_entries = result["new_entries"]
    if not new_entries:
        print(warn("no valid monthly rows in actuals CSV"))
        return 1

    for entry in new_entries:
        month = entry.get("month", "?")
        n_alerts = len(entry.get("alerts") or [])
        if n_alerts:
            print(warn(f"{month}: {n_alerts} alert(s)"))
            for a in entry["alerts"]:
                print(info(f"  - {a}"))
        else:
            print(info(f"{month}: on plan"))

    root = Path(args.dir).resolve()
    print()
    print(success(f"wrote {root / 'tracking_history.csv'}"))
    print(success(f"wrote {root / 'tracking_report.md'}"))
    print(success(f"appended to {root / 'deal.yaml'} (tracking block)"))
    return 0


def _dispatch_auto_populate(args: argparse.Namespace) -> int:
    """Handle ``rcm-mc deal auto-populate --name "…"``."""
    import json as _json
    from ..data.auto_populate import auto_populate
    from ..portfolio.store import PortfolioStore
    store = PortfolioStore(args.db)
    result = auto_populate(store, args.name)
    if args.json:
        sys.stdout.write(_json.dumps(result.to_dict(), indent=2, default=str) + "\n")
        return 0
    # Prose summary.
    sys.stdout.write(f"Query: {result.query!r}\n")
    if not result.matches:
        sys.stdout.write("No hospital matched that query.\n")
        return 1
    sys.stdout.write(f"Candidates ({len(result.matches)}):\n")
    for m in result.matches:
        marker = "→" if (result.selected and m.ccn == result.selected.ccn) else " "
        sys.stdout.write(
            f"  {marker} [{m.ccn}] {m.name}, {m.city} {m.state}  "
            f"beds={m.bed_count}  conf={m.confidence:.2f}\n"
        )
    if result.selected is None:
        sys.stdout.write(
            "\nNo single candidate cleared the 0.90 confidence bar — "
            "rerun with the CCN directly or a tighter name.\n"
        )
        return 0
    sys.stdout.write(f"\n{result.summary}\n")
    sys.stdout.write(
        f"Coverage: {result.coverage_pct:.1f}% of the 38-metric registry.\n",
    )
    if result.gaps:
        sys.stdout.write("\nTop gaps (by EBITDA sensitivity):\n")
        for g in result.gaps[:10]:
            sys.stdout.write(
                f"  #{g.ebitda_sensitivity_rank:>2}  {g.display_name}\n"
            )
    if args.deal_id:
        store.upsert_deal(
            args.deal_id, name=result.selected.name,
            profile=result.profile,
        )
        sys.stdout.write(
            f"\nUpserted deal '{args.deal_id}' into {args.db}.\n"
        )
    return 0


def main(argv: Optional[List[str]] = None, prog: str = "rcm-mc deal") -> int:
    ap = _build_parser(prog=prog)
    args = ap.parse_args(argv)

    if args.action == "track":
        return _dispatch_track(args)
    if args.action == "auto-populate":
        return _dispatch_auto_populate(args)

    if args.action != "new":
        ap.print_help()
        return 2

    if args.skip_intake and not args.actual:
        sys.stderr.write("--skip-intake requires --actual <path-to-existing-yaml>\n")
        return 2

    from ..infra._terminal import banner, info, success, warn

    print(banner(f"Deal: {args.dir}"))
    print(info(f"CCN:         {args.ccn or '(none — full wizard)'}"))
    print(info(f"Data source: {args.data_source or '(none — uncalibrated)'}"))
    print(info(f"Sims:        {args.n_sims:,}"))
    print()

    try:
        state = create_deal(
            args.dir,
            ccn=args.ccn,
            data_source=args.data_source,
            actual_path=args.actual,
            benchmark=args.benchmark,
            n_sims=args.n_sims,
            partner_brief=args.partner_brief,
            skip_intake=args.skip_intake,
            skip_ingest=args.skip_ingest,
            skip_run=args.skip_run,
        )
    except Exception as exc:
        print()
        sys.stderr.write(f"deal pipeline failed: {exc}\n")
        sys.stderr.write(f"  (state written to {Path(args.dir) / 'deal.yaml'})\n")
        return 1

    print()
    print(success(f"deal complete: status = {state['deal'].get('status')}"))
    print(info(f"Target:    {state['deal'].get('name') or 'unknown'}"))
    if state["deal"].get("ccn"):
        print(info(f"CCN:       {state['deal']['ccn']}"))
    for k in ("report", "partner_brief", "diligence_workbook", "data_requests"):
        p = state["files"].get(k)
        if p:
            print(info(f"{k:22s} {p}"))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
