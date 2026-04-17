"""
Full HTML Report: comprehensive run + report with Input Requirements, Config Reference, and Numbers Source Map.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd



def _build_input_requirements_section() -> str:
    """HTML section: what data files are needed and required columns."""
    return """
<h2>Input Requirements and Data Sources</h2>
<p class='section-desc'><strong>Why this matters:</strong> The model's accuracy depends entirely on input quality. This table specifies what data files are needed, what columns they require, and how each feeds the simulation. During diligence, use this as a data request checklist.</p>
<table>
<tr><th>Data File</th><th>Location</th><th>Required Fields</th><th>Purpose</th></tr>
<tr><td><strong>claims_summary.csv</strong></td><td><code>--actual-data-dir</code> or <code>data_demo/target_pkg/</code></td><td>payer, net_revenue, claim_count</td><td>Calibration: revenue mix, claim volumes</td></tr>
<tr><td><strong>denials.csv</strong></td><td>Same</td><td>payer, denial_amount, writeoff_amount, appeal_level, denial_category, days_to_resolve</td><td>Calibration: IDR, FWR, stage mix by payer</td></tr>
<tr><td><strong>ar_aging.csv</strong></td><td>Same (optional)</td><td>payer, ar_amount</td><td>Calibration: A/R days by payer</td></tr>
<tr><td><strong>actual.yaml</strong></td><td><code>configs/actual.yaml</code></td><td>hospital, payers, economics, appeals, operations</td><td>Actual scenario parameters (or use calibrated_actual.yaml)</td></tr>
<tr><td><strong>benchmark.yaml</strong></td><td><code>configs/benchmark.yaml</code></td><td>Same structure</td><td>Best-practice baseline</td></tr>
<tr><td><strong>initiatives_library.yaml</strong></td><td><code>configs/initiatives_library.yaml</code></td><td>initiatives[].id, name, affected_parameters, costs, ramp_months</td><td>100-day plan initiative definitions</td></tr>
<tr><td><strong>playbook.yaml</strong></td><td><code>configs/playbook.yaml</code></td><td>Driver bucket → lever, kpi, diligence</td><td>Action plan text for report</td></tr>
<tr><td><strong>value_plan.yaml</strong></td><td>Optional</td><td>gap_closure, costs, timeline</td><td>Value-creation Target scenario</td></tr>
<tr><td><strong>scenario YAML</strong></td><td><code>scenarios/*.yaml</code></td><td>name, shocks[]</td><td>Parameter shocks for scenario overlay</td></tr>
</table>
"""


def _build_config_reference_section(actual_path: str, benchmark_path: str) -> str:
    """HTML section: which config key controls what."""
    return f"""
<h2>Configuration Reference</h2>
<p class='section-desc'><strong>Why this matters:</strong> Every number in the report traces back to a configuration parameter. This reference maps each input to what it controls, so the deal team can adjust assumptions and re-run without guessing. Files: <code>{actual_path}</code>, <code>{benchmark_path}</code>.</p>
<table>
<tr><th>Configuration Parameter</th><th>What It Controls</th></tr>
<tr><td><code>hospital.annual_revenue</code></td><td>Base net patient revenue; scales all dollar outputs</td></tr>
<tr><td><code>hospital.name</code></td><td>Hospital name displayed in report headers</td></tr>
<tr><td><code>economics.wacc_annual</code></td><td>Weighted average cost of capital for working capital cost calculations</td></tr>
<tr><td><code>economics.ev_multiple</code></td><td>EBITDA-to-enterprise-value multiple for valuation bridge</td></tr>
<tr><td><code>economics.debt</code></td><td>Total debt for covenant sensitivity analysis (optional)</td></tr>
<tr><td><code>hospital.ebitda_margin</code></td><td>EBITDA as a percentage of net patient revenue (default 8%)</td></tr>
<tr><td><code>hospital.rcm_spend_annual</code></td><td>Total annual RCM operating spend for cost-to-collect benchmarking</td></tr>
<tr><td><code>payers.[payer].revenue_share</code></td><td>Share of total revenue by payer (e.g., Medicare 0.42)</td></tr>
<tr><td><code>payers.[payer].avg_claim_dollars</code></td><td>Average claim size by payer</td></tr>
<tr><td><code>payers.[payer].denials.idr</code></td><td>Initial denial rate (distribution: mean, standard deviation, bounds)</td></tr>
<tr><td><code>payers.[payer].denials.fwr</code></td><td>Final write-off rate (percentage of denied claims never recovered)</td></tr>
<tr><td><code>payers.[payer].denials.stage_mix</code></td><td>Appeal mix across Level 1 / Level 2 / Level 3</td></tr>
<tr><td><code>payers.[payer].dar_clean_days</code></td><td>Clean-claim days in accounts receivable (mean, min, max)</td></tr>
<tr><td><code>payers.[payer].underpayments.upr</code></td><td>Underpayment rate (share of claims paid below contracted amount)</td></tr>
<tr><td><code>payers.[payer].underpayments.severity</code></td><td>Average underpayment severity (% below contract)</td></tr>
<tr><td><code>payers.[payer].underpayments.recovery</code></td><td>Recovery success rate on identified underpayments</td></tr>
<tr><td><code>appeals.stages.L1/L2/L3.cost</code></td><td>Cost per appeal at each stage</td></tr>
<tr><td><code>appeals.stages.L1/L2/L3.days</code></td><td>Average days to resolve at each appeal stage</td></tr>
<tr><td><code>operations.denial_capacity.fte</code></td><td>Denial management team headcount; drives capacity constraints</td></tr>
<tr><td><code>analysis.n_sims</code></td><td>Number of Monte Carlo iterations (default 30,000)</td></tr>
<tr><td><code>analysis.seed</code></td><td>Random seed for reproducibility</td></tr>
</table>
"""


def _build_numbers_source_map_section(outdir: str) -> str:
    """HTML section: where each key number comes from and how to change it."""
    rows: List[tuple] = [
        ("Metric", "Source File", "Column / Key", "How to Adjust"),
        ("Total EBITDA Drag (Mean, P10, P90)", "summary.csv", "ebitda_drag: mean, p10, p90", "Denial rates, write-off rates, and A/R days in payer configs"),
        ("Metric Formulas and Run Manifest", "provenance.json", "Per-metric formula, config keys, aggregations", "Auto-generated each run; see Metric Provenance documentation"),
        ("Single-Iteration Audit Trail", "simulation_trace.json", "Pre-scrub Actual vs Benchmark for one iteration", "CLI flag: --trace-iteration N"),
        ("Working Capital Cost (Economic Drag)", "summary.csv", "economic_drag: mean", "A/R days by payer in configuration"),
        ("Enterprise Value Opportunity", "summary.csv x ev_multiple", "ebitda_drag.mean x multiple", "EBITDA multiple in config or --multiple flag"),
        ("Denial Write-Off Drag", "summary.csv", "drag_denial_writeoff", "Write-off rate and denial rate by payer"),
        ("Underpayment Leakage", "summary.csv", "drag_underpay_leakage", "Underpayment rate and severity by payer"),
        ("Excess Days in A/R", "summary.csv", "drag_dar_total", "A/R days by payer in configuration"),
        ("Sensitivity Rankings", "sensitivity.csv", "driver, correlation", "Model output; shows which parameters move EBITDA most"),
        ("Initiative Rankings", "initiative_rankings.csv", "ebitda_uplift_mean, payback_months", "Initiative library configuration"),
        ("100-Day Plan", "hundred_day_plan.csv", "rank, name, owner, kpi, phase", "Initiative library configuration"),
        ("Diligence Requests", "sensitivity.csv (derived)", "Top 3 drivers with data requests", "Built from sensitivity analysis"),
        ("Stress Test Results", "stress_tests.csv", "scenario, ebitda_drag variants", "Run with --stress flag"),
        ("Value Creation Uplift", "value_creation_summary.csv", "ebitda_uplift variants", "Value plan configuration: gap closure, costs"),
    ]
    trows = []
    for i, r in enumerate(rows):
        if i == 0:
            trows.append("<tr><th>" + "</th><th>".join(r) + "</th></tr>")
        else:
            trows.append("<tr><td>" + "</td><td>".join(str(x) for x in r) + "</td></tr>")
    base = os.path.basename(outdir) or "outputs"
    return f"""
<h2>Numbers Source Map</h2>
<p class='section-desc'><strong>Why this matters:</strong> For audit and diligence purposes, every number in this report must be traceable to a specific source file and column. This map provides that traceability. Output folder: <code>{outdir}</code>.</p>
<table>
{chr(10).join(trows)}
</table>
<p class='section-desc'><strong>summary.csv</strong> is derived from <strong>simulations.csv</strong> (the raw Monte Carlo output). To change any distribution: edit the configuration files and re-run the simulation.</p>
"""


def generate_full_html_report(
    outdir: str,
    actual_path: str,
    benchmark_path: str,
    hospital_name: Optional[str] = None,
    ev_multiple: float = 8.0,
    annual_revenue: float = 0.0,
    wacc: float = 0.12,
    attribution_results: Optional[Dict[str, Any]] = None,
    playbook_path: Optional[str] = None,
    data_confidence_path: Optional[str] = None,
    debt: Optional[float] = None,
    ebitda_margin: float = 0.08,
    rcm_spend_annual: Optional[float] = None,
    shock_results: Optional[List[Dict[str, Any]]] = None,
    n_sims: int = 0,
) -> str:
    """
    Generate full_report.html with Input Requirements, Config Reference, Numbers Source Map,
    plus all standard report sections. Calls the existing html_report generator for content.
    """
    from .html_report import generate_html_report

    outdir = str(outdir)
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # Build doc sections
    doc_html = []
    doc_html.append("<h1>RCM Monte Carlo — Full Report</h1>")
    doc_html.append(f"<p class='meta'>Generated: {ts} | Output: <code>{outdir}</code></p>")
    doc_html.append("<p><strong>This report includes:</strong> Input requirements, configuration reference, numbers source map, and all analysis sections.</p>")
    doc_html.append(_build_input_requirements_section())
    doc_html.append(_build_config_reference_section(actual_path, benchmark_path))

    df_summary = None
    summary_path = os.path.join(outdir, "summary.csv")
    if os.path.exists(summary_path):
        df_summary = pd.read_csv(summary_path, index_col=0)
    doc_html.append(_build_numbers_source_map_section(outdir))

    # Generate standard report (writes report.html) and extract content
    report_path = generate_html_report(
        outdir,
        title="RCM Monte Carlo — Executive Report",
        hospital_name=hospital_name,
        ev_multiple=ev_multiple,
        annual_revenue=annual_revenue,
        wacc=wacc,
        attribution_results=attribution_results,
        playbook_path=playbook_path,
        data_confidence_path=data_confidence_path,
        debt=debt,
        ebitda_margin=ebitda_margin,
        rcm_spend_annual=rcm_spend_annual,
        shock_results=shock_results or [],
        n_sims=n_sims,
        actual_config_path=actual_path,
        benchmark_config_path=benchmark_path,
    )

    # Read the generated report and extract only the inner content (no duplicate <html>/<head>)
    with open(report_path, "r", encoding="utf-8") as f:
        report_content = f.read()

    # Extract <style> block and body content from the executive report
    import re
    style_match = re.search(r"<style>(.*?)</style>", report_content, re.DOTALL)
    all_styles = style_match.group(1) if style_match else ""
    # Collect any additional <style> blocks
    for extra_style in re.finditer(r"<style>(.*?)</style>", report_content, re.DOTALL):
        if extra_style.group(1) != all_styles:
            all_styles += "\n" + extra_style.group(1)

    # Extract body content (everything inside <div class="container">...</div></body>)
    body_start = report_content.find('<div class="container">')
    body_end = report_content.rfind("</body>")
    if body_start >= 0 and body_end >= 0:
        report_body = report_content[body_start + len('<div class="container">'):body_end]
        # Strip trailing </div> that closes the container
        if report_body.rstrip().endswith("</div>"):
            report_body = report_body.rstrip()[:-len("</div>")]
    else:
        report_body = report_content

    # Use df_summary for a summary stats preamble in the doc sections
    if df_summary is not None and "ebitda_drag" in df_summary.index:
        _mean = float(df_summary.loc["ebitda_drag", "mean"])
        _p10 = float(df_summary.loc["ebitda_drag", "p10"])
        _p90 = float(df_summary.loc["ebitda_drag", "p90"])
        doc_html.append(
            f'<div style="background:#f0f9ff;border-left:4px solid #0f4c81;padding:1rem 1.25rem;border-radius:8px;margin:1rem 0;">'
            f'<strong>Quick Reference:</strong> EBITDA Drag Mean: ${_mean/1e6:,.1f}M | '
            f'P10: ${_p10/1e6:,.1f}M | P90: ${_p90/1e6:,.1f}M</div>'
        )

    # Build full report as single cohesive document
    full_html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>RCM Monte Carlo — Full Report</title>
  <style>
    {all_styles}
    .divider {{ border-top: 3px solid var(--primary, #0f4c81); margin: 3rem 0; padding-top: 2rem; }}
  </style>
</head>
<body>
<div class="container">
"""
    full_html += "\n".join(doc_html)
    full_html += '<div class="divider"><h2>Analysis Results</h2><p class="section-desc">Full simulation results and executive report sections follow.</p></div>\n'
    full_html += report_body
    full_html += "\n</div></body></html>"

    out_path = os.path.join(outdir, "full_report.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    return out_path
