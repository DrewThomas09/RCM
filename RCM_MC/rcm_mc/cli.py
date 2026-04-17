from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

import pandas as pd

from .core.calibration import calibrate_config, write_yaml
from .pe.breakdowns import simulate_compare_with_breakdowns
from .analysis.stress import run_stress_suite
from .reports.html_report import generate_html_report
from .infra.config import load_and_validate
from .data.data_scrub import scrub_simulation_data
from .reports.reporting import (
    strategic_priority_matrix,
    assumption_summary,
    actionable_insights,
    correlation_sensitivity,
    METRIC_LABELS,
    plot_deal_summary,
    plot_denial_drivers_chart,
    plot_ebitda_drag_distribution,
    plot_underpayments_chart,
    pretty_money,
    summary_table,
    waterfall_ebitda_drag,
)
from .core.simulator import simulate_compare
from .pe.value_creation import run_value_creation
from .pe.value_plan import load_value_plan
from .infra.provenance import write_provenance_json
from .infra.trace import write_trace_json


def _ensure_outdir(path: str) -> str:
    outdir = str(path)
    os.makedirs(outdir, exist_ok=True)
    return outdir


def build_arg_parser() -> argparse.ArgumentParser:
    from . import __version__
    ap = argparse.ArgumentParser(
        description=(
            "RCM Monte Carlo: compare Actual vs Benchmark and quantify EBITDA/Economic drag. "
            "Optional: calibrate from diligence data; optional: run a value-creation plan that closes a fraction of the gap."
        )
    )
    ap.add_argument("--version", action="version",
                    version=f"%(prog)s {__version__}")

    ap.add_argument("--actual", required=True, help="Path to actual scenario YAML")
    ap.add_argument("--benchmark", required=True, help="Path to benchmark scenario YAML")

    ap.add_argument(
        "--actual-data-dir",
        default=None,
        help=(
            "Optional path to an Actual diligence data package directory. "
            "If provided, the model will calibrate key assumptions from claims_summary.csv / denials.csv / ar_aging.csv."
        ),
    )
    ap.add_argument(
        "--benchmark-data-dir",
        default=None,
        help=(
            "Optional path to a Benchmark data package directory (uncommon). "
            "Most diligence use-cases only calibrate Actual, while Benchmark stays best-practice."
        ),
    )

    ap.add_argument("--n-sims", type=int, default=30000, help="Number of Monte Carlo simulations")
    ap.add_argument("--seed", type=int, default=42, help="Random seed")
    ap.add_argument("--outdir", default="outputs", help="Output directory")

    ap.add_argument(
        "--no-align-profile",
        dest="align_profile",
        action="store_false",
        help=(
            "Disable hospital profile alignment. By default, Benchmark is aligned to Actual for annual_revenue, "
            "payer revenue_share, and avg_claim_dollars so the comparison isolates RCM performance rather than volume/mix."
        ),
    )
    ap.set_defaults(align_profile=True)

    ap.add_argument("--multiple", type=float, default=8.0, help="EBITDA multiple for translating steady-state uplift into EV")

    ap.add_argument(
        "--no-breakdowns",
        dest="breakdowns",
        action="store_false",
        help="Disable mean driver breakdown outputs (payer x denial type, payer x stage).",
    )
    ap.set_defaults(breakdowns=True)

    ap.add_argument(
        "--stress",
        action="store_true",
        help="Run a standard stress test suite (parameter shocks) and write stress_tests.csv.",
    )
    ap.add_argument(
        "--stress-sims",
        type=int,
        default=5000,
        help="Monte Carlo sims for each stress scenario (default: 5000).",
    )
    ap.add_argument(
        "--no-report",
        dest="report",
        action="store_false",
        help="Disable HTML report generation (report.html).",
    )
    ap.set_defaults(report=True)

    ap.add_argument(
        "--partner-brief",
        dest="partner_brief",
        action="store_true",
        help=(
            "Also generate partner_brief.html — a one-page, IC-ready executive "
            "summary stripped of analyst-facing narration. Good for circulating "
            "before IC; read alongside the full report during IC."
        ),
    )

    ap.add_argument(
        "--no-bundle",
        dest="bundle",
        action="store_false",
        help="Skip diligence_workbook.xlsx / data_requests.md and leave every output at the top of --outdir.",
    )
    ap.set_defaults(bundle=True)

    ap.add_argument(
        "--no-portfolio",
        action="store_true",
        help="Skip portfolio auto-register even when deal.portfolio_deal_id is set.",
    )
    ap.add_argument(
        "--portfolio-db",
        default=None,
        metavar="PATH",
        help="Portfolio DB path for auto-register (default: ~/.rcm_mc/portfolio.db).",
    )

    ap.add_argument(
        "--value-plan",
        default=None,
        help=(
            "Optional path to a value_plan.yaml. If provided, the CLI will generate a Target scenario by "
            "closing a fraction of the Actual-to-Benchmark gap and will output uplift/ROI metrics."
        ),
    )

    ap.add_argument(
        "--pressure-test",
        default=None,
        metavar="PLAN_YAML",
        help=(
            "Path to a management plan YAML (see scenarios/management_plan_example.yaml). "
            "Classifies each target conservative/stretch/aggressive/aspirational and runs "
            "Monte Carlo at 100/75/50/0%% of plan achievement."
        ),
    )
    ap.add_argument(
        "--pressure-sims",
        type=int,
        default=2000,
        help="Monte Carlo sims per pressure-test achievement level (default 2000).",
    )

    ap.add_argument(
        "--initiatives",
        action="store_true",
        help="Run initiative ranking and 100-day plan; write hundred_day_plan.csv and initiative_rankings.csv.",
    )
    ap.add_argument(
        "--initiative-sims",
        type=int,
        default=1000,
        help="Monte Carlo sims per initiative when --initiatives is used (default: 1000).",
    )

    ap.add_argument(
        "--attribution",
        action="store_true",
        help="Run OAT value attribution and add attribution outputs to report.",
    )
    ap.add_argument(
        "--attr-sims",
        type=int,
        default=3000,
        help="Monte Carlo sims per attribution scenario (default: 3000).",
    )

    ap.add_argument(
        "--full-report",
        action="store_true",
        help="Run initiatives, stress, attribution + generate full_report.html with Input Requirements, Config Reference, Numbers Source Map.",
    )

    ap.add_argument(
        "--trace-iteration",
        type=int,
        default=None,
        metavar="N",
        help=(
            "If set, write simulation_trace.json: one pre-scrub Monte Carlo draw (Actual vs Benchmark) "
            "for iteration N (0-based), using the same RNG stream as the main run."
        ),
    )

    # Step 37: Validate-only mode
    ap.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate configs and exit without running simulation.",
    )

    # Step 82: Deal screening mode
    ap.add_argument(
        "--screen",
        action="store_true",
        help="Quick 1000-sim screening; prints one-line summary and exits.",
    )

    # Step 33: Template support
    ap.add_argument(
        "--template",
        default=None,
        help="Load a config template as the starting actual config (e.g., community_hospital_500m).",
    )

    # Step 36: Config diff
    ap.add_argument(
        "--diff",
        nargs=2,
        metavar=("CONFIG_A", "CONFIG_B"),
        default=None,
        help="Compare two config files and print differences.",
    )

    # Step 86: JSON output
    ap.add_argument("--json-output", action="store_true", help="Write summary.json alongside summary.csv.")

    # Step 87: Markdown report
    ap.add_argument("--markdown", action="store_true", help="Generate a Markdown report (report.md).")

    # Step 88: Theme
    ap.add_argument("--theme", default="default", choices=["default", "dark", "print", "minimal"],
                     help="HTML report theme.")

    # Step 90: Comparison report
    ap.add_argument("--compare-to", default=None, help="Path to a prior output directory for comparison.")

    ap.add_argument("--pptx", action="store_true", help="Write report.pptx (requires python-pptx).")
    ap.add_argument("--list-runs", action="store_true", help="List recent runs from runs.sqlite in --outdir and exit.")
    ap.add_argument(
        "--scenario",
        default=None,
        help="JSON file path with scenario adjustments (idr_delta_by_payer, fte_change, annual_revenue).",
    )
    ap.add_argument(
        "--explain-config",
        action="store_true",
        help="Print flattened config keys from --actual and exit.",
    )

    return ap


def run_main(argv: Optional[list[str]] = None, prog: str = "rcm-mc") -> None:
    """Flat-form Monte Carlo runner (the original CLI).

    Retained as the ``run`` subcommand's implementation and as the back-compat
    path for anyone still invoking ``rcm-mc --actual ... --benchmark ...``.
    """
    ap = build_arg_parser()
    ap.prog = prog
    args = ap.parse_args(argv)

    if getattr(args, "explain_config", False):
        from .infra.config import flatten_config, load_and_validate as _lv
        cfg = _lv(args.actual)
        rows = flatten_config(cfg)
        print("\n| Parameter | Value (truncated) | Type |")
        print("|-----------|-------------------|------|")
        for r in rows[:200]:
            k = str(r.get("parameter", ""))[:80]
            v = str(r.get("value", ""))[:60]
            t = str(r.get("type", ""))[:20]
            print(f"| `{k}` | {v} | {t} |")
        if len(rows) > 200:
            print(f"| ... | ({len(rows) - 200} more keys) | ... |")
        return

    # Step 36: Config diff mode
    if args.diff:
        from .infra.config import load_and_validate as _lv, diff_configs as _dc
        cfg_a = _lv(args.diff[0])
        cfg_b = _lv(args.diff[1])
        diffs = _dc(cfg_a, cfg_b)
        if diffs:
            print(f"\n{'Parameter':<50} {'Change':<12} {'Value A':<20} {'Value B':<20} {'Delta'}")
            print("-" * 120)
            for d in diffs:
                key = d["key"][:49]
                change = d.get("change", "")
                va = str(d.get("value_a", ""))[:19]
                vb = str(d.get("value_b", ""))[:19]
                delta = str(d.get("delta", ""))[:10]
                print(f"{key:<50} {change:<12} {va:<20} {vb:<20} {delta}")
        else:
            print("Configs are identical.")
        return

    # Step 37: Validate-only mode
    if args.validate_only:
        from .infra.config import validate_config_from_path
        all_valid = True
        for label, path in [("Actual", args.actual), ("Benchmark", args.benchmark)]:
            valid, issues = validate_config_from_path(path)
            if valid:
                print(f"  {label}: VALID")
            else:
                print(f"  {label}: INVALID")
                for issue in issues:
                    print(f"    - {issue}")
                all_valid = False
        import sys
        sys.exit(0 if all_valid else 1)

    # Step 82: Deal screening mode
    if getattr(args, "screen", False):
        actual_cfg = load_and_validate(args.actual)
        bench_cfg = load_and_validate(args.benchmark)
        from .core.simulator import simulate_compare as _sc
        df = _sc(actual_cfg, bench_cfg, n_sims=1000, seed=int(args.seed), align_profile=bool(args.align_profile))
        drag = df["ebitda_drag"]
        mult = float(args.multiple)
        print(f"SCREEN: EBITDA drag: ${drag.mean()/1e6:,.1f}M "
              f"(P10: ${drag.quantile(0.10)/1e6:,.1f}M, P90: ${drag.quantile(0.90)/1e6:,.1f}M) "
              f"| EV @ {mult}x: ${drag.mean()*mult/1e6:,.1f}M")
        return

    # Step 4 (v2): Wire --template flag
    actual_path = args.actual
    if getattr(args, "template", None):
        tpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "configs", "templates")
        tpl_file = os.path.join(tpl_dir, f"{args.template}.yaml")
        if os.path.exists(tpl_file):
            actual_path = tpl_file
            print(f"Using template: {tpl_file}")
        else:
            print(f"Warning: template '{args.template}' not found at {tpl_file}; using --actual")

    outdir = _ensure_outdir(args.outdir)

    if getattr(args, "list_runs", False):
        from .infra.run_history import list_runs
        runs = list_runs(outdir, limit=30)
        if not runs:
            print(f"No run history in {outdir}/runs.sqlite")
        else:
            for r in runs:
                print(r)
        return

    actual_cfg = load_and_validate(actual_path)
    bench_cfg = load_and_validate(args.benchmark)

    if getattr(args, "scenario", None):
        from .scenarios.scenario_builder import apply_scenario_dict
        from .infra.config import validate_config
        with open(args.scenario, "r", encoding="utf-8") as sf:
            adj = json.load(sf)
        actual_cfg = validate_config(apply_scenario_dict(actual_cfg, adj))

    # Step 1 (v2): Compute hospital_name early so all branches can use it
    hospital_name = actual_cfg.get("hospital", {}).get("name", "Hospital")

    # Optional calibration from diligence data
    if args.actual_data_dir:
        print(f"\n=== Calibrating ACTUAL config from data package: {args.actual_data_dir} ===")
        actual_cfg, report, cal_quality = calibrate_config(actual_cfg, args.actual_data_dir)
        report_path = os.path.join(outdir, "calibration_actual_report.csv")
        report.round(4).to_csv(report_path, index=False)
        cal_quality.write_json(os.path.join(outdir, "data_quality_report.json"))
        calibrated_path = os.path.join(outdir, "calibrated_actual.yaml")
        write_yaml(actual_cfg, calibrated_path)
        print(f"Wrote: {report_path}")
        print(f"Wrote: {calibrated_path}")
        print(f"Wrote: {os.path.join(outdir, 'data_quality_report.json')}")
        from .analysis.anomaly_detection import detect_anomalies
        anom = detect_anomalies(actual_cfg)
        if anom.has_warnings:
            apath = os.path.join(outdir, "anomalies.json")
            with open(apath, "w", encoding="utf-8") as af:
                json.dump(anom.to_list(), af, indent=2)
            print(f"Wrote: {apath} ({len(anom.to_list())} anomaly flags)")

    if args.benchmark_data_dir:
        print(f"\n=== Calibrating BENCHMARK config from data package: {args.benchmark_data_dir} ===")
        bench_cfg, report_b, _ = calibrate_config(bench_cfg, args.benchmark_data_dir)
        report_path = os.path.join(outdir, "calibration_benchmark_report.csv")
        report_b.round(4).to_csv(report_path, index=False)
        calibrated_path = os.path.join(outdir, "calibrated_benchmark.yaml")
        write_yaml(bench_cfg, calibrated_path)
        print(f"Wrote: {report_path}")
        print(f"Wrote: {calibrated_path}")

    # Document input assumptions (rounded for readability)
    for cfg, name in [(actual_cfg, "actual"), (bench_cfg, "benchmark")]:
        assump = assumption_summary(cfg, n_draws=5000, seed=args.seed if name == "actual" else args.seed + 100)
        assump.round(3).to_csv(os.path.join(outdir, f"assumptions_{name}.csv"), index=False)

    # Baseline: Actual vs Benchmark
    if bool(getattr(args, "breakdowns", True)):
        df, bds = simulate_compare_with_breakdowns(
            actual_cfg,
            bench_cfg,
            n_sims=args.n_sims,
            seed=args.seed,
            align_profile=bool(args.align_profile),
        )
        # Persist mean driver breakdowns (audit-ready)
        bds["actual"]["payer_denial_type"].to_csv(os.path.join(outdir, "drivers_denial_type_actual_mean.csv"), index=False)
        bds["benchmark"]["payer_denial_type"].to_csv(os.path.join(outdir, "drivers_denial_type_benchmark_mean.csv"), index=False)
        bds["drag"]["payer_denial_type"].to_csv(os.path.join(outdir, "drivers_denial_type_drag_mean.csv"), index=False)

        bds["actual"]["payer_stage"].to_csv(os.path.join(outdir, "drivers_stage_actual_mean.csv"), index=False)
        bds["benchmark"]["payer_stage"].to_csv(os.path.join(outdir, "drivers_stage_benchmark_mean.csv"), index=False)
        bds["drag"]["payer_stage"].to_csv(os.path.join(outdir, "drivers_stage_drag_mean.csv"), index=False)

        bds["actual"]["payer_underpayments"].to_csv(os.path.join(outdir, "drivers_underpayments_actual_mean.csv"), index=False)
        bds["benchmark"]["payer_underpayments"].to_csv(os.path.join(outdir, "drivers_underpayments_benchmark_mean.csv"), index=False)
        bds["drag"]["payer_underpayments"].to_csv(os.path.join(outdir, "drivers_underpayments_drag_mean.csv"), index=False)
    else:
        df = simulate_compare(
            actual_cfg,
            bench_cfg,
            n_sims=args.n_sims,
            seed=args.seed,
            align_profile=bool(args.align_profile),
        )

    # Board-ready scrub: winsorize outliers, standardize naming (sim -> iteration)
    hosp = actual_cfg.get("hospital", {}) or {}
    econ = actual_cfg.get("economics", {}) or {}
    revenue = float(hosp.get("annual_revenue", 0))
    df, scrub_report = scrub_simulation_data(df, actual_cfg, revenue=revenue if revenue > 0 else None)

    # Save simulation-level results
    sim_path = os.path.join(outdir, "simulations.csv")
    df.to_csv(sim_path, index=False)

    # Summary table (include actual + benchmark for report clarity)
    metrics = [
        "ebitda_drag",
        "economic_drag",
        "drag_denial_writeoff",
        "drag_underpay_leakage",
        "drag_denial_rework_cost",
        "drag_underpay_cost",
        "drag_dar_total",
    ]
    extra_cols = []
    if "actual_rcm_ebitda_impact" in df.columns:
        extra_cols.append("actual_rcm_ebitda_impact")
    if "bench_rcm_ebitda_impact" in df.columns:
        extra_cols.append("bench_rcm_ebitda_impact")
    summary = summary_table(df, metrics + extra_cols)
    summary_path = os.path.join(outdir, "summary.csv")
    summary_rounded = summary.copy()
    for m in summary_rounded.index:
        summary_rounded.loc[m] = summary_rounded.loc[m].round(1 if "dar" in str(m) else 0)
    summary_rounded.to_csv(summary_path)

    prov_path = write_provenance_json(
        outdir,
        summary,
        n_sims=int(args.n_sims),
        seed=int(args.seed),
        align_profile=bool(args.align_profile),
        actual_config_path=actual_path,
        benchmark_config_path=args.benchmark,
        scrub_report=scrub_report.to_dict() if scrub_report else None,
        actual_cfg=actual_cfg,
    )
    print(f"Wrote: {prov_path}")

    # Step 86: JSON output
    if getattr(args, "json_output", False):
        from .infra.output_formats import write_summary_json, write_column_docs
        json_path = write_summary_json(summary, outdir, n_sims=int(args.n_sims), seed=int(args.seed))
        print(f"Wrote: {json_path}")
        col_path = write_column_docs(outdir)
        print(f"Wrote: {col_path}")

    # Step 87: Markdown report (v2 Step 1: hospital_name now defined earlier)
    if getattr(args, "markdown", False):
        from .reports.markdown_report import generate_markdown_report
        md_path = generate_markdown_report(
            outdir,
            hospital_name=hospital_name,
            ev_multiple=float(args.multiple),
            annual_revenue=revenue,
            n_sims=int(args.n_sims),
        )
        if md_path:
            print(f"Wrote: {md_path}")

    # Step 90: Comparison report
    if getattr(args, "compare_to", None):
        from .analysis.compare_runs import compare_run_dirs, narrative_comparison
        try:
            comp_df = compare_run_dirs(args.compare_to, outdir)
            comp_path = os.path.join(outdir, "run_comparison.csv")
            comp_df.to_csv(comp_path, index=False)
            print(f"Wrote: {comp_path}")
            print(narrative_comparison(comp_df))
        except Exception as e:
            print(f"Comparison failed: {e}")

    if getattr(args, "trace_iteration", None) is not None:
        trace_path = os.path.join(outdir, "simulation_trace.json")
        write_trace_json(
            trace_path,
            actual_cfg,
            bench_cfg,
            iteration=int(args.trace_iteration),
            seed=int(args.seed),
            align_profile=bool(args.align_profile),
        )
        print(f"Wrote: {trace_path}")

    wf_path = os.path.join(outdir, "waterfall.png")
    ebitda_margin = float(hosp.get("ebitda_margin", 0.08))
    reported_ebitda = float(hosp.get("annual_revenue", 0)) * ebitda_margin if hosp.get("annual_revenue") else None
    waterfall_ebitda_drag(df, wf_path, reported_ebitda=reported_ebitda if reported_ebitda and reported_ebitda > 0 else None)

    dist_path = os.path.join(outdir, "ebitda_drag_distribution.png")
    debt = econ.get("debt") or hosp.get("debt")
    covenant_trigger = None
    if debt and reported_ebitda and reported_ebitda > 0:
        max_ratio = 6.0  # Typical covenant: Net Debt/EBITDA <= 6x
        covenant_trigger = reported_ebitda - (float(debt) / max_ratio)
    p10_drag = float(summary.loc["ebitda_drag", "p10"]) if "ebitda_drag" in summary.index else None
    plot_ebitda_drag_distribution(
        df, dist_path,
        covenant_trigger_drag=covenant_trigger,
        management_case_drag=p10_drag,  # P10 as "Management Case" (optimistic proxy)
    )

    mult = float(actual_cfg.get("economics", {}).get("ev_multiple") or args.multiple)
    deal_path = os.path.join(outdir, "deal_summary.png")
    plot_deal_summary(summary, mult, deal_path)

    denial_drag_path = os.path.join(outdir, "drivers_denial_type_drag_mean.csv")
    if os.path.exists(denial_drag_path):
        dt_drag_df = pd.read_csv(denial_drag_path)
        plot_denial_drivers_chart(dt_drag_df, os.path.join(outdir, "denial_drivers_chart.png"))
    up_drag_path = os.path.join(outdir, "drivers_underpayments_drag_mean.csv")
    if os.path.exists(up_drag_path):
        up_drag_df = pd.read_csv(up_drag_path)
        plot_underpayments_chart(up_drag_df, os.path.join(outdir, "underpayments_chart.png"))

    sens = None
    driver_cols = [
        c for c in df.columns
        if c.startswith("actual_") and any(k in c for k in ("idr_", "fwr_", "dar_clean_", "upr_"))
    ]
    if driver_cols:
        sens = correlation_sensitivity(df, driver_cols=driver_cols, target_col="ebitda_drag", top_n=10)
        sens.to_csv(os.path.join(outdir, "sensitivity.csv"), index=False)
        priority_df = strategic_priority_matrix(sens)
        priority_df.to_csv(os.path.join(outdir, "strategic_priority_matrix.csv"), index=False)

    ev_mean = float(summary.loc["ebitda_drag", "mean"]) * mult
    ev_p90 = float(summary.loc["ebitda_drag", "p90"]) * mult
    insights = actionable_insights(summary, sens, ev_multiple=mult)

    # hospital_name already defined after config loading (v2 Step 1)

    # --- Polished console output (client-ready) ---
    align_note = " (profile-aligned)" if getattr(args, "align_profile", True) else ""
    print("\n" + "═" * 70)
    print("  RCM MONTE CARLO — Executive Summary")
    print(f"  Actual vs Benchmark{align_note}")
    print("═" * 70)
    print("\n  ┌─ Distribution Summary (mean | P10 | P90) ────────────────────────┐")
    for m in metrics:
        if m not in summary.index:
            continue
        label = METRIC_LABELS.get(m, m.replace("_", " "))
        r = summary.loc[m]
        if "dar" in m:
            vals = f"{float(r['mean']):.1f}  |  {float(r['p10']):.1f}  |  {float(r['p90']):.1f}"
        else:
            vals = f"{pretty_money(r['mean'])}  |  {pretty_money(r['p10'])}  |  {pretty_money(r['p90'])}"
        print(f"  │  {label:<32} {vals:<30} │")
    print("  └──────────────────────────────────────────────────────────────────┘")

    print(f"\n  EV Translation at {mult:.1f}x EBITDA multiple")
    print("  " + "─" * 50)
    print(f"  Mean EV impact:  {ev_mean:,.0f}")
    print(f"  P90 EV impact:   {ev_p90:,.0f}")

    print("\n  Actionable insights")
    print("  " + "─" * 50)
    for i, ins in enumerate(insights, 1):
        print(f"  {i}. {ins}")

    if sens is not None and len(sens) > 0:
        print("\n  Top sensitivity drivers (correlation to EBITDA drag)")
        print("  " + "─" * 50)
        for _, row in sens.head(5).iterrows():
            lbl = row.get("driver_label", row.get("driver", ""))
            corr = row.get("corr", 0)
            print(f"  • {lbl}: {corr:.2f}")

    outputs_list = [
        summary_path,
        prov_path,
        wf_path,
        dist_path,
        deal_path,
        os.path.join(outdir, "sensitivity.csv"),
    ]
    if getattr(args, "trace_iteration", None) is not None:
        outputs_list.append(os.path.join(outdir, "simulation_trace.json"))
    if bool(getattr(args, "report", True)):
        outputs_list.append(os.path.join(outdir, "report.html"))
    if bool(getattr(args, "attribution", False)):
        outputs_list.extend([
            os.path.join(outdir, "attribution_oat.csv"),
            os.path.join(outdir, "attribution_tornado.png"),
        ])
    print("\n  Outputs written:")
    for o in outputs_list:
        print(f"    • {o}")
    print("═" * 70 + "\n")

    # Optional: OAT attribution
    attr_results = None
    if bool(getattr(args, "attribution", False)):
        from .pe.attribution import run_attribution, plot_tornado
        print("\n=== Running OAT value attribution ===")
        attr_sims = int(getattr(args, "attr_sims", 3000))
        attr_results = run_attribution(
            actual_cfg, bench_cfg,
            n_sims=attr_sims,
            seed=int(args.seed) + 200,
            align_profile=bool(args.align_profile),
        )
        attr_results["oat"].to_csv(os.path.join(outdir, "attribution_oat.csv"), index=False)
        plot_tornado(attr_results["oat"], os.path.join(outdir, "attribution_tornado.png"), attr_results["baseline_drag"])
        print(f"Wrote: {os.path.join(outdir, 'attribution_oat.csv')}")
        print(f"Wrote: {os.path.join(outdir, 'attribution_tornado.png')}")

    # Optional: management plan pressure-test
    if getattr(args, "pressure_test", None):
        from .analysis.pressure_test import load_management_plan, run_pressure_test
        print(f"\n=== Pressure-testing management plan: {args.pressure_test} ===")
        plan = load_management_plan(args.pressure_test)
        pt = run_pressure_test(
            actual_cfg, bench_cfg, plan,
            n_sims=int(getattr(args, "pressure_sims", 2000)),
            seed=int(args.seed) + 400,
            align_profile=bool(args.align_profile),
        )
        pt_assess_path = os.path.join(outdir, "pressure_test_assessments.csv")
        pt_miss_path = os.path.join(outdir, "pressure_test_miss_scenarios.csv")
        pt["assessments_df"].to_csv(pt_assess_path, index=False)
        pt["miss_scenarios_df"].to_csv(pt_miss_path, index=False)
        print(f"Wrote: {pt_assess_path}")
        print(f"Wrote: {pt_miss_path}")
        # Short terminal summary — partners want the top-line read in the console
        print("  Target assessments:")
        for a in pt["assessments"]:
            ramp = f", median ramp {a.median_ramp_months:.0f}mo" if a.median_ramp_months else ""
            print(f"    • {a.target_key}: {a.classification} ({a.target_value:g} from {a.actual_blended:g}){ramp}")
        if pt["risk_flags"]:
            print("  Risk flags:")
            for f in pt["risk_flags"]:
                print(f"    ⚠ {f}")

    # Data confidence (from calibration report if present)
    conf_path = os.path.join(outdir, "calibration_actual_report.csv")
    data_confidence_path = None
    if os.path.exists(conf_path):
        from .reports.html_report import _build_data_confidence
        data_confidence_path = _build_data_confidence(conf_path, os.path.join(outdir, "data_confidence.csv"))

    # Auto peer comparison when the actual config carries a CMS CCN (flows
    # through from `rcm-intake --from-ccn`). Gracefully no-ops on missing data.
    # ── PE deal-math auto-compute (Brick 46) ──
    # When `deal:` is present in actual.yaml, materialize bridge / returns /
    # hold grid / covenant artifacts off the simulation's mean uplift.
    if actual_cfg.get("deal"):
        from .pe.pe_integration import compute_and_persist_pe_math
        pe_paths = compute_and_persist_pe_math(outdir, actual_cfg, summary)
        for p in pe_paths:
            print(f"Wrote: {p}")

        # ── Portfolio auto-register (Brick 51) ──
        # If the deal carries a portfolio_deal_id + portfolio_stage, snapshot
        # it into the default portfolio DB. Skipped when --no-portfolio is set.
        _auto_register_portfolio_snapshot(outdir, actual_cfg, args)

    target_ccn = (actual_cfg.get("hospital") or {}).get("ccn")
    if target_ccn:
        try:
            from .data.hcris import find_peers, compute_peer_percentiles, trend_signals
            peers_df = find_peers(str(target_ccn), n=15)
            pcts_df = compute_peer_percentiles(str(target_ccn), peers_df)
            peers_path = os.path.join(outdir, "peer_comparison.csv")
            pcts_path = os.path.join(outdir, "peer_target_percentiles.csv")
            peers_df.to_csv(peers_path, index=False)
            pcts_df.to_csv(pcts_path, index=False)
            print(f"Wrote: {peers_path}")
            print(f"Wrote: {pcts_path}")
            # Headline percentile summary in terminal — partners like this visibly
            npsr_row = pcts_df[pcts_df["kpi"] == "net_patient_revenue"]
            if not npsr_row.empty:
                pct = npsr_row.iloc[0]["target_percentile"]
                print(f"  Peer position: target NPSR at {pct:.0f}th percentile of {len(peers_df)} matched peers")
            # Multi-year diligence signals — only materializes when ≥2 years on file
            signals_df = trend_signals(str(target_ccn))
            if not signals_df.empty:
                signals_path = os.path.join(outdir, "trend_signals.csv")
                signals_df.to_csv(signals_path, index=False)
                print(f"Wrote: {signals_path}")
        except (ValueError, FileNotFoundError) as exc:
            print(f"  (peer comparison skipped: {exc})")

    # Optional: initiative ranking + 100-day plan
    if bool(getattr(args, "initiatives", False)):
        from .rcm.initiative_optimizer import rank_initiatives, build_100_day_plan

        init_sims = int(getattr(args, "initiative_sims", 1000))
        rank_df = rank_initiatives(
            actual_cfg,
            bench_cfg,
            n_sims=init_sims,
            seed=int(args.seed) + 300,
            ev_multiple=float(args.multiple),
            align_profile=bool(args.align_profile),
        )
        plan_df = build_100_day_plan(rank_df)
        rank_path = os.path.join(outdir, "initiative_rankings.csv")
        plan_path = os.path.join(outdir, "hundred_day_plan.csv")
        rank_df.to_csv(rank_path, index=False)
        plan_df.to_csv(plan_path, index=False)
        print(f"Wrote: {rank_path}")
        print(f"Wrote: {plan_path}")

    # Optional: stress tests (Leap 8)
    if bool(getattr(args, "stress", False)):
        stress_df = run_stress_suite(
            actual_cfg=actual_cfg,
            benchmark_cfg=bench_cfg,
            n_sims=int(getattr(args, "stress_sims", 5000)),
            seed=int(args.seed) + 100,
            align_profile=bool(args.align_profile),
        )
        stress_path = os.path.join(outdir, "stress_tests.csv")
        stress_df.to_csv(stress_path, index=False)
        print(f"Wrote: {stress_path}")

    # Optional: HTML report (Leap 8)
    playbook_path = None
    if args.actual:
        config_dir = os.path.dirname(os.path.abspath(args.actual))
        candidate = os.path.join(config_dir, "playbook.yaml")
        if os.path.exists(candidate):
            playbook_path = candidate
        elif os.path.exists(os.path.join(os.getcwd(), "configs", "playbook.yaml")):
            playbook_path = os.path.join(os.getcwd(), "configs", "playbook.yaml")

    debt = econ.get("debt") or hosp.get("debt")
    debt_val = float(debt) if debt is not None else None
    rcm_spend = hosp.get("rcm_spend_annual")
    rcm_spend_val = float(rcm_spend) if rcm_spend is not None else None
    ebitda_margin = float(hosp.get("ebitda_margin", 0.08))

    if bool(getattr(args, "report", True)):
        generate_html_report(
            outdir,
            title="RCM Monte Carlo — Executive Report",
            hospital_name=hospital_name,
            ev_multiple=mult,
            annual_revenue=float(hosp.get("annual_revenue", 0)),
            wacc=float(econ.get("wacc_annual", 0.12)),
            attribution_results=attr_results,
            playbook_path=playbook_path,
            data_confidence_path=data_confidence_path,
            debt=debt_val,
            ebitda_margin=ebitda_margin,
            rcm_spend_annual=rcm_spend_val,
            n_sims=int(args.n_sims),
            actual_config_path=actual_path,
            benchmark_config_path=args.benchmark,
            theme=getattr(args, "theme", "default"),
        )

    if bool(getattr(args, "partner_brief", False)):
        try:
            from .reports._partner_brief import build_partner_brief
            brief_path = build_partner_brief(
                outdir,
                hospital_name=hospital_name,
                ev_multiple=mult,
                actual_config_path=actual_path,
                benchmark_config_path=args.benchmark,
            )
            print(f"Wrote: {brief_path}")
        except Exception as exc:  # nicety, not a core output — don't fail the run
            print(f"  (partner brief skipped: {type(exc).__name__}: {exc})")

    # Full report: run initiatives + stress + attribution if not already, then generate full_report.html
    if bool(getattr(args, "full_report", False)):
        # Run initiatives if not already run
        if not bool(getattr(args, "initiatives", False)):
            from .rcm.initiative_optimizer import rank_initiatives, build_100_day_plan
            init_sims = int(getattr(args, "initiative_sims", 1000))
            rank_df = rank_initiatives(actual_cfg, bench_cfg, n_sims=init_sims, seed=int(args.seed) + 300,
                ev_multiple=float(args.multiple), align_profile=bool(args.align_profile))
            plan_df = build_100_day_plan(rank_df)
            rank_df.to_csv(os.path.join(outdir, "initiative_rankings.csv"), index=False)
            plan_df.to_csv(os.path.join(outdir, "hundred_day_plan.csv"), index=False)
        # Run stress if not already run
        if not bool(getattr(args, "stress", False)):
            stress_df = run_stress_suite(
                actual_cfg=actual_cfg,
                benchmark_cfg=bench_cfg,
                n_sims=int(getattr(args, "stress_sims", 5000)),
                seed=int(args.seed) + 100,
                align_profile=bool(args.align_profile),
            )
            stress_df.to_csv(os.path.join(outdir, "stress_tests.csv"), index=False)
        # Run OAT attribution if not already run
        if not bool(getattr(args, "attribution", False)):
            from .pe.attribution import run_attribution, plot_tornado
            attr_results = run_attribution(
                actual_cfg, bench_cfg,
                n_sims=int(getattr(args, "attr_sims", 3000)),
                seed=int(args.seed) + 200,
                align_profile=bool(args.align_profile),
            )
            attr_results["oat"].to_csv(os.path.join(outdir, "attribution_oat.csv"), index=False)
            plot_tornado(attr_results["oat"], os.path.join(outdir, "attribution_tornado.png"), attr_results["baseline_drag"])
        # Run preset payer policy shocks for Scenario Explorer (full report only)
        shock_results = []
        try:
            from .scenarios.scenario_shocks import run_preset_shocks
            shock_results = run_preset_shocks(
                actual_path,
                args.benchmark,
                n_sims=int(getattr(args, "stress_sims", 3000)),
                seed=int(args.seed) + 200,
            )
        except Exception as e:
            from .infra.logger import logger
            logger.warning("Scenario shock loading failed (non-fatal): %s", e)
        from .reports.full_report import generate_full_html_report
        full_path = generate_full_html_report(
            outdir,
            actual_path=actual_path,
            benchmark_path=args.benchmark,
            hospital_name=hospital_name,
            ev_multiple=mult,
            annual_revenue=float(hosp.get("annual_revenue", 0)),
            wacc=float(econ.get("wacc_annual", 0.12)),
            attribution_results=attr_results,
            playbook_path=playbook_path,
            data_confidence_path=data_confidence_path,
            debt=debt_val,
            ebitda_margin=ebitda_margin,
            rcm_spend_annual=rcm_spend_val,
            shock_results=shock_results,
            n_sims=int(args.n_sims),
        )
        print(f"Wrote: {full_path}")

    try:
        from .infra.run_history import record_run
        if "ebitda_drag" in summary.index:
            record_run(
                outdir,
                actual_config_path=actual_path,
                benchmark_config_path=args.benchmark,
                n_sims=int(args.n_sims),
                seed=int(args.seed),
                ebitda_drag_mean=float(summary.loc["ebitda_drag", "mean"]),
                ebitda_drag_p10=float(summary.loc["ebitda_drag", "p10"]),
                ebitda_drag_p90=float(summary.loc["ebitda_drag", "p90"]),
                ev_impact=float(summary.loc["ebitda_drag", "mean"]) * mult,
                hospital_name=hospital_name,
            )
    except Exception as e:
        from .infra.logger import logger
        logger.warning("record_run failed: %s", e)

    if getattr(args, "pptx", False):
        from .reports.pptx_export import generate_pptx
        pptx_path = generate_pptx(
            outdir,
            hospital_name=hospital_name,
            ev_multiple=float(mult),
            annual_revenue=revenue,
            n_sims=int(args.n_sims),
        )
        if pptx_path:
            print(f"Wrote: {pptx_path}")

    # Optional: Value-creation plan
    if args.value_plan:
        plan = load_value_plan(args.value_plan)
        vc = run_value_creation(
            actual_cfg=actual_cfg,
            benchmark_cfg=bench_cfg,
            plan=plan,
            n_sims=int(args.n_sims),
            seed=int(args.seed),
            align_profile=bool(args.align_profile),
            ev_multiple=float(args.multiple),
        )

        # Persist the generated Target scenario for auditability
        target_cfg_path = os.path.join(outdir, "target_from_value_plan.yaml")
        write_yaml(vc["target_cfg"], target_cfg_path)

        # Simulation-level value creation outputs
        vc_sims_path = os.path.join(outdir, "value_creation_simulations.csv")
        vc["vc_sims"].to_csv(vc_sims_path, index=False)

        # Summary and deal pack
        vc_summary_path = os.path.join(outdir, "value_creation_summary.csv")
        vc["vc_summary"].to_csv(vc_summary_path)

        deal_path = os.path.join(outdir, "deal_pack.csv")
        vc["deal_pack"].to_csv(deal_path, index=False)

        print("\n=== Value creation plan outputs ===")
        print(f"Wrote: {target_cfg_path}")
        print(f"Wrote: {vc_sims_path}")
        print(f"Wrote: {vc_summary_path}")
        print(f"Wrote: {deal_path}")

    # Deliverable bundle: collapse 20+ output files into a workbook + data requests,
    # and sweep detail CSVs/charts into outputs/_detail/.
    if bool(getattr(args, "bundle", True)):
        try:
            from .infra._bundle import finalize_bundle
            bundle = finalize_bundle(
                outdir,
                summary,
                actual_cfg,
                hospital_name=hospital_name,
            )
            print(f"Wrote: {bundle['workbook']}")
            print(f"Wrote: {bundle['data_requests']}")
            if bundle["detail_moved"]:
                print(f"Moved {len(bundle['detail_moved'])} detail files to {os.path.join(outdir, '_detail')}/")
        except Exception as e:
            # The bundle is a post-processing nicety; never let it fail the main run.
            print(f"Warning: bundle generation failed ({type(e).__name__}: {e}); core outputs are still in {outdir}")

    # UI-3 / UI-6 / UI-7: wrap every human-readable output in styled HTML
    # (text blocks, PE JSON payloads, short CSVs) so clicking from the
    # index lands on a readable page rather than raw text/json/csv.
    try:
        from .ui.csv_to_html import wrap_csvs_in_folder
        from .ui.json_to_html import wrap_pe_artifacts_in_folder
        from .ui.text_to_html import wrap_text_files_in_folder
        wrap_text_files_in_folder(outdir)
        wrap_pe_artifacts_in_folder(outdir)
        wrap_csvs_in_folder(outdir)
    except (OSError, ValueError) as exc:
        print(f"  (HTML companions skipped: {exc})")

    # UI-4: auto-generate a navigable landing page so opening the output
    # folder yields one clickable link instead of 40 files.
    try:
        from .infra.output_index import build_indices_recursive
        build_indices_recursive(outdir)
    except (OSError, ValueError) as exc:
        print(f"  (index generation skipped: {exc})")

    run_target_ccn = (actual_cfg.get("hospital") or {}).get("ccn")
    _print_run_complete_banner(outdir, args, target_ccn=run_target_ccn)


def _auto_register_portfolio_snapshot(
    outdir: str,
    actual_cfg: Dict[str, Any],
    args: argparse.Namespace,
) -> None:
    """Snapshot this run into the portfolio DB if the deal block supplies
    ``portfolio_deal_id`` + ``portfolio_stage``.

    Skipped when ``--no-portfolio`` is set or the env var
    ``RCM_MC_NO_PORTFOLIO=1`` is exported — an analyst may want to run
    ad-hoc sensitivities without polluting the portfolio store.

    Degrades silently (stderr warning) on any persistence error —
    portfolio tracking is a convenience, not a critical path of `run`.
    """
    if bool(getattr(args, "no_portfolio", False)):
        return
    if os.environ.get("RCM_MC_NO_PORTFOLIO") == "1":
        return

    deal = actual_cfg.get("deal") or {}
    deal_id = deal.get("portfolio_deal_id")
    stage = deal.get("portfolio_stage")
    if not (deal_id and stage):
        return

    try:
        from .portfolio.store import PortfolioStore
        from .portfolio.portfolio_snapshots import register_snapshot
        db_path = getattr(args, "portfolio_db", None) or os.path.expanduser(
            "~/.rcm_mc/portfolio.db"
        )
        store = PortfolioStore(db_path)
        sid = register_snapshot(
            store,
            deal_id=str(deal_id),
            stage=str(stage),
            run_dir=outdir,
            notes=f"auto-registered by `rcm-mc run` from {outdir}",
        )
        print(f"Portfolio: registered snapshot #{sid} (deal={deal_id}, stage={stage})")
    except (OSError, ValueError) as exc:
        import sys as _sys
        _sys.stderr.write(
            f"Portfolio auto-register skipped ({type(exc).__name__}: {exc})\n"
        )


def _print_run_complete_banner(
    outdir: str,
    args: argparse.Namespace,
    target_ccn: Optional[str] = None,
) -> None:
    """Unmistakable terminal message: where outputs live (avoids 'nothing happened' confusion)."""
    from .infra._terminal import completion_box

    abs_out = os.path.abspath(outdir)
    bundled = bool(getattr(args, "bundle", True))

    items: list = [("Folder:", abs_out)]
    if bool(getattr(args, "report", True)):
        items.append(("Report:", f"file://{os.path.join(abs_out, 'report.html')}"))
    if bool(getattr(args, "partner_brief", False)):
        items.append(("Brief:", f"file://{os.path.join(abs_out, 'partner_brief.html')}"))
    if bundled:
        items.append(("Workbook:", os.path.join(abs_out, "diligence_workbook.xlsx")))
        items.append(("Requests:", os.path.join(abs_out, "data_requests.md")))
    items.append(("Tables:", [
        os.path.join(abs_out, "summary.csv"),
        os.path.join(abs_out, "simulations.csv"),
    ]))
    if bundled:
        items.append(("Detail:", os.path.join(abs_out, "_detail") + os.sep))

    # Append the IC one-liner when we have a CCN — ties the pipeline back to
    # the pre-intake screen so the analyst sees the diligence read on exit.
    if target_ccn:
        try:
            from .data.lookup import format_one_liner
            one_liner = format_one_liner(str(target_ccn))
            if one_liner:
                items.append(("Summary:", one_liner))
        except (ValueError, FileNotFoundError):
            pass  # one-liner is a nicety; never let it fail the banner

    print(completion_box("RUN COMPLETE — outputs are on disk", items))


# ── Top-level subcommand dispatcher ──────────────────────────────────────

_SUBCOMMANDS = ("run", "intake", "lookup", "ingest", "challenge", "deal",
                "hcris", "pe", "portfolio", "serve")

_TOP_LEVEL_HELP = """\
rcm-mc — RCM Monte Carlo diligence tool

Usage:
  rcm-mc <command> [options]

Commands:
  deal      One-command orchestrator: intake → ingest → run.
            `rcm-mc deal new --dir PATH [--ccn X] [--data-source PATH]`
  run       Run the Monte Carlo pipeline (simulate → report → bundle).
  intake    Interactive wizard to build actual.yaml in ~90 seconds.
            Use --from-ccn to pre-fill hospital fields from CMS HCRIS.
  lookup    Search CMS HCRIS (~6,000 US hospitals) from the command line.
  ingest    Turn a messy seller data pack (zip/folder/xlsx) into a
            calibration-ready directory of canonical CSVs.
  challenge Reverse solver: given a target EBITDA drag, find the assumption
            changes that would get there (joint + per-lever).
  hcris     Developer tool: rebuild or inspect the shipped HCRIS bundle.
  pe        PE deal-math: value bridge, IRR/MOIC, sensitivity, covenants.
            `rcm-mc pe {bridge|returns|grid|covenant} --help`
  portfolio Portfolio-level tracking: snapshot deals, list, roll up.
            `rcm-mc portfolio {register|list|show|rollup} --help`
  serve     Start a local web server for the portfolio + outputs.
            `rcm-mc serve [--port N] [--open]`  (no CLI flags needed day-to-day)
  analysis  Build a Deal Analysis Packet (JSON) for one deal.
            `rcm-mc analysis <deal_id> [--scenario X] [--as-of DATE] [--out PATH]`
  data      Refresh or inspect CMS public-data sources (HCRIS, Care Compare,
            Medicare Utilization, IRS 990). `rcm-mc data {refresh|status} --help`

Run `rcm-mc <command> --help` for command-specific options.

Back-compat: `rcm-mc --actual X --benchmark Y` without an explicit
subcommand is still accepted and routes to `run` unchanged.

For full docs: https://github.com/... (see README.md)
"""


def data_main(argv: list, prog: str = "rcm-mc data") -> int:
    """``rcm-mc data {refresh|status} [--source X]``

    Refresh or inspect the four CMS public-data sources that feed the
    hospital_benchmarks table (HCRIS / Care Compare / Utilization /
    IRS 990). ``status`` is read-only; ``refresh`` may hit the network
    unless downloads are cached.
    """
    ap = argparse.ArgumentParser(prog=prog, description="CMS public-data refresh")
    sub = ap.add_subparsers(dest="action", required=True)

    r = sub.add_parser("refresh", help="Download + load one or all sources")
    r.add_argument("--db", default="portfolio.db", help="Path to SQLite store")
    r.add_argument("--source", default="all",
                   help="hcris | care_compare | utilization | irs990 | all")
    r.add_argument("--interval-days", type=int, default=30,
                   help="Stamp the next-refresh schedule this many days out")

    s = sub.add_parser("status", help="Show freshness of each data source")
    s.add_argument("--db", default="portfolio.db", help="Path to SQLite store")

    args = ap.parse_args(argv)
    from .portfolio.store import PortfolioStore
    from .data import data_refresh as dr
    store = PortfolioStore(args.db)

    if args.action == "status":
        dr.schedule_refresh(store, interval_days=30)
        dr.mark_stale_sources(store)
        rows = dr.get_status(store)
        if not rows:
            sys.stdout.write("no data sources registered\n")
            return 0
        # Compact table
        sys.stdout.write(f"{'SOURCE':<14}  {'STATUS':<6}  {'RECORDS':>8}  "
                         f"{'LAST REFRESH':<27}  {'NEXT REFRESH'}\n")
        for row in rows:
            sys.stdout.write(
                f"{row['source_name']:<14}  {row.get('status') or '':<6}  "
                f"{row.get('record_count') or 0:>8}  "
                f"{row.get('last_refresh_at') or '—':<27}  "
                f"{row.get('next_refresh_at') or '—'}\n"
            )
        return 0

    # refresh
    sources = None
    if args.source and args.source != "all":
        sources = [s.strip() for s in args.source.split(",") if s.strip()]
        for name in sources:
            if name not in dr.KNOWN_SOURCES:
                sys.stderr.write(f"unknown source {name!r}; known: {dr.KNOWN_SOURCES}\n")
                return 2
    dr.schedule_refresh(store, interval_days=int(args.interval_days))
    report = dr.refresh_all_sources(store, sources=sources,
                                    interval_days=int(args.interval_days))
    for r in report.per_source:
        marker = "OK" if r.status == "OK" else "FAIL"
        sys.stdout.write(
            f"[{marker}] {r.source}: {r.record_count} records in {r.duration_secs:.1f}s"
            + (f"  ({r.error_detail})" if r.error_detail else "")
            + "\n"
        )
    return 1 if report.any_errors else 0


def analysis_main(argv: list, prog: str = "rcm-mc analysis") -> int:
    """``rcm-mc analysis <deal_id> [--scenario X] [--as-of YYYY-MM-DD] [--out PATH]``

    Build (or retrieve cached) Deal Analysis Packet for a deal. Prints
    the JSON to stdout by default, or writes to ``--out`` if provided.
    ``--rebuild`` forces a new run_id + cache write even when inputs
    haven't changed.
    """
    from datetime import date as _date
    ap = argparse.ArgumentParser(prog=prog, description="Build or load a Deal Analysis Packet.")
    ap.add_argument("deal_id", help="Deal identifier (matches the deals table)")
    ap.add_argument("--db", default="portfolio.db", help="Path to SQLite portfolio store")
    ap.add_argument("--scenario", default=None, help="Scenario id / path")
    ap.add_argument("--as-of", default=None, help="Report as-of date (YYYY-MM-DD)")
    ap.add_argument("--out", default=None, help="Output JSON path (default: stdout)")
    ap.add_argument("--rebuild", action="store_true", help="Force rebuild, bypass cache")
    ap.add_argument("--skip-sim", action="store_true", default=True,
                    help="Skip Monte Carlo (default true; pass --run-sim to enable)")
    ap.add_argument("--run-sim", dest="skip_sim", action="store_false",
                    help="Actually run the Monte Carlo simulator")
    ap.add_argument("--indent", type=int, default=2, help="JSON indent")
    args = ap.parse_args(argv)

    as_of = None
    if args.as_of:
        try:
            as_of = _date.fromisoformat(args.as_of)
        except ValueError:
            sys.stderr.write(f"invalid --as-of {args.as_of!r}; want YYYY-MM-DD\n")
            return 2

    from .portfolio.store import PortfolioStore
    from .analysis.analysis_store import get_or_build_packet
    store = PortfolioStore(args.db)
    try:
        packet = get_or_build_packet(
            store, args.deal_id,
            scenario_id=args.scenario, as_of=as_of,
            force_rebuild=bool(args.rebuild),
            skip_simulation=bool(args.skip_sim),
        )
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"build failed: {exc}\n")
        return 1
    payload = packet.to_json(indent=args.indent)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(payload)
        sys.stderr.write(f"wrote {args.out} ({len(payload)} bytes, run_id={packet.run_id})\n")
    else:
        sys.stdout.write(payload)
        sys.stdout.write("\n")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    """Top-level dispatcher for `rcm-mc` subcommands.

    Dispatch table:

    - ``rcm-mc run ...``     → :func:`run_main`
    - ``rcm-mc intake ...``  → :func:`rcm_mc.intake.main`
    - ``rcm-mc lookup ...``  → :func:`rcm_mc.lookup.main`
    - ``rcm-mc hcris ...``   → :func:`rcm_mc.hcris._main`
    - ``rcm-mc --actual X``  → legacy flat-form, routed to ``run_main``
    - ``rcm-mc`` / ``-h``    → top-level help
    """
    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv or argv[0] in ("-h", "--help", "help"):
        sys.stdout.write(_TOP_LEVEL_HELP)
        return 0

    first = argv[0]

    if first == "run":
        run_main(argv[1:], prog="rcm-mc run")
        return 0
    if first == "intake":
        from .data.intake import main as intake_main
        return intake_main(argv[1:], prog="rcm-mc intake")
    if first == "lookup":
        from .data.lookup import main as lookup_main
        return lookup_main(argv[1:], prog="rcm-mc lookup")
    if first == "ingest":
        from .data.ingest import main as ingest_main
        return ingest_main(argv[1:], prog="rcm-mc ingest")
    if first == "challenge":
        from .analysis.challenge import main as challenge_main
        return challenge_main(argv[1:], prog="rcm-mc challenge")
    if first == "deal":
        from .deals.deal import main as deal_main
        return deal_main(argv[1:], prog="rcm-mc deal")
    if first == "hcris":
        from .data.hcris import _main as hcris_main
        return hcris_main(argv[1:], prog="rcm-mc hcris")
    if first == "pe":
        from .pe_cli import main as pe_main
        return pe_main(argv[1:], prog="rcm-mc pe")
    if first == "portfolio":
        from .portfolio_cmd import main as portfolio_main
        return portfolio_main(argv[1:], prog="rcm-mc portfolio")
    if first == "serve":
        from .server import main as serve_main
        return serve_main(argv[1:], prog="rcm-mc serve")
    if first == "analysis":
        return analysis_main(argv[1:], prog="rcm-mc analysis")
    if first == "data":
        return data_main(argv[1:], prog="rcm-mc data")

    # Back-compat: flat-form flag at position 1 → treat as `run`.
    # (Nearly every existing script uses this form.)
    if first.startswith("-"):
        run_main(argv, prog="rcm-mc")
        return 0

    sys.stderr.write(f"Unknown command: {first!r}\n\n")
    sys.stderr.write(_TOP_LEVEL_HELP)
    return 2


if __name__ == "__main__":
    sys.exit(main() or 0)