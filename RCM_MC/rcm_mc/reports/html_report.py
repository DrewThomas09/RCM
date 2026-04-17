"""
Client-ready HTML report generator for RCM Monte Carlo outputs.
Produces a polished, executive-facing report with clear sections and explanations.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from html import escape as html_escape
from typing import Any, Dict, List, Optional

import yaml

from .reporting import METRIC_LABELS, actionable_insights, pretty_money
from .report_themes import get_theme_css
from ..data.sources import classify_sources, confidence_grade, summarize
from ._report_css import REPORT_HEAD_STYLES
from ._report_helpers import (
    _BENCHMARK_REFERENCES,
    _build_benchmark_gap_table,
    _build_data_confidence,
    _build_provenance_methodology_section,
    _extract_payer_params,
    _fmt_metric_row,
    _format_money_cols,
    _img_tag,
    _read_csv_if_exists,
)
from ._report_sections import (
    BACK_TO_TOP_HTML,
    GLOSSARY_HTML,
    KEY_ASSUMPTIONS_HTML,
    MODEL_LIMITATIONS_HTML,
    RISK_REGISTER_HTML,
    SCENARIO_EXPLORER_JS,
)


_GRADE_COLORS = {"A": "var(--green)", "B": "var(--accent)", "C": "var(--amber)", "D": "var(--red)"}
_GRADE_BLURB = {
    "A": "Strong evidence base — majority of inputs observed from target data.",
    "B": "Moderate evidence base — material share observed, rest priors / assumptions.",
    "C": "Thin evidence base — mostly priors; request more data before underwriting.",
    "D": "Weak evidence base — outputs driven by analyst assumptions. Add data.",
}


def _build_source_confidence_card(
    actual_cfg: Optional[Dict[str, Any]],
    outdir: Optional[str] = None,
) -> str:
    """Badge summarizing observed vs prior vs assumed inputs for IC defensibility.

    Prefers the sources snapshot from ``provenance.json`` (already reflects any
    calibration done during this run). Falls back to classifying the raw YAML
    config if provenance isn't present yet.
    """
    counts: Dict[str, int] = {}
    grade = "D"
    prov_path = os.path.join(outdir, "provenance.json") if outdir else None
    if prov_path and os.path.isfile(prov_path):
        try:
            with open(prov_path, "r", encoding="utf-8") as f:
                doc = json.load(f)
            s = doc.get("sources") or {}
            counts = s.get("counts") or {}
            grade = s.get("grade") or grade
        except (OSError, json.JSONDecodeError):
            counts = {}
    if not counts and actual_cfg:
        classification = classify_sources(actual_cfg)
        counts = summarize(classification)
        grade = confidence_grade(classification)
    total = int(counts.get("total") or 0)
    if total == 0:
        return ""
    color = _GRADE_COLORS.get(grade, "var(--gray)")
    blurb = _GRADE_BLURB.get(grade, "")
    observed = int(counts.get("observed") or 0)
    prior = int(counts.get("prior") or 0)
    assumed = int(counts.get("assumed") or 0)
    pct = (observed / total * 100.0) if total else 0.0
    return f"""
    <div class="card" id="source-confidence" style="border-left: 6px solid {color};">
      <h3 style="margin-top:0;">Input Evidence: Grade {grade}</h3>
      <p class='section-desc' style="margin-bottom: 0.5rem;"><strong>{observed} of {total}</strong> model inputs observed from target data ({pct:.0f}%) — {prior} industry priors, {assumed} analyst assumptions.</p>
      <p class='section-desc' style="margin-bottom: 0;"><em>{blurb}</em> Full per-input source map is available in <code>provenance.json</code>.</p>
    </div>"""

__all__ = [
    "generate_html_report",
    "_build_data_confidence",  # re-exported; cli.py imports this from here
]




def generate_html_report(
    outdir: str,
    title: str = "RCM Monte Carlo — Executive Report",
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
    actual_config_path: Optional[str] = None,
    benchmark_config_path: Optional[str] = None,
    theme: str = "default",
) -> str:
    """
    Generate a client-ready HTML report from output files in outdir.
    """
    outdir = str(outdir)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    summary_path = os.path.join(outdir, "summary.csv")
    sims_path = os.path.join(outdir, "simulations.csv")
    sens_path = os.path.join(outdir, "sensitivity.csv")
    waterfall_path = os.path.join(outdir, "waterfall.png")
    dist_path = os.path.join(outdir, "ebitda_drag_distribution.png")
    deal_path = os.path.join(outdir, "deal_summary.png")
    denial_chart_path = os.path.join(outdir, "denial_drivers_chart.png")
    underpay_chart_path = os.path.join(outdir, "underpayments_chart.png")
    stress_path = os.path.join(outdir, "stress_tests.csv")
    tornado_path = os.path.join(outdir, "attribution_tornado.png")

    df_summary = _read_csv_if_exists(summary_path, index_col=0)
    df_sens = _read_csv_if_exists(sens_path)
    df_stress = _read_csv_if_exists(stress_path)
    df_conf = _read_csv_if_exists(data_confidence_path) if data_confidence_path else None

    dt_drag = _read_csv_if_exists(os.path.join(outdir, "drivers_denial_type_drag_mean.csv"))
    st_drag = _read_csv_if_exists(os.path.join(outdir, "drivers_stage_drag_mean.csv"))
    up_drag = _read_csv_if_exists(os.path.join(outdir, "drivers_underpayments_drag_mean.csv"))

    # Compute actionable insights from summary + sensitivity
    insights = []
    if df_summary is not None and "ebitda_drag" in df_summary.index:
        insights = actionable_insights(df_summary, df_sens, ev_multiple=ev_multiple)

    hospital_display = hospital_name or "Hospital"
    ebitda_mean = float(df_summary.loc["ebitda_drag", "mean"]) if df_summary is not None else 0
    ev_mean = ebitda_mean * ev_multiple

    # Load configs early for payer dashboard and benchmark gap table
    actual_cfg_load: Optional[Dict[str, Any]] = None
    benchmark_cfg_load: Optional[Dict[str, Any]] = None
    if actual_config_path and os.path.exists(actual_config_path):
        try:
            with open(actual_config_path, "r", encoding="utf-8") as f:
                actual_cfg_load = yaml.safe_load(f)
        except Exception:
            pass
    if benchmark_config_path and os.path.exists(benchmark_config_path):
        try:
            with open(benchmark_config_path, "r", encoding="utf-8") as f:
                benchmark_cfg_load = yaml.safe_load(f)
        except Exception:
            pass

    html_parts = []
    _theme_vars = get_theme_css(theme)
    _escaped_title = html_escape(title)
    html_parts.append("<!doctype html>\n<html lang=\"en\">\n<head>\n  <meta charset=\"utf-8\">\n"
                       + f"  <title>{_escaped_title}</title>\n"
                       + f"  <style>\n    {_theme_vars}\n  </style>\n"
                       + "  <style>")
    html_parts.append(REPORT_HEAD_STYLES)

    # Sticky navigation bar
    html_parts.append("""
    <nav class="report-nav"><div class="report-nav-inner">
      <span class="nav-brand">RCM Analysis</span>
      <a href="#exec-summary">Summary</a>
      <a href="#payer-dashboard">Payer Dashboard</a>
      <a href="#actual-vs-benchmark">Benchmark</a>
      <a href="#sec-deal">Deal Range</a>
      <a href="#sec-waterfall">Value Bridge</a>
      <a href="#sec-insights">Insights</a>
      <a href="#sec-diligence">Diligence</a>
      <a href="#sec-priority">Priority Matrix</a>
      <a href="#sec-drivers">Drivers</a>
      <a href="#sec-timeline">Timeline</a>
      <a href="#sec-bid-impact">Bid Impact</a>
      <a href="#sec-risks">Risks</a>
      <a href="#sec-limitations">Limitations</a>
      <a href="#sec-post-close">Post-Close</a>
      <a href="#sec-ic-memo">IC Memo</a>
      <a href="#sec-conclusion">Conclusion</a>
      <a href="#glossary">Glossary</a>
      <a href="#data-sources">Sources</a>
    </div></nav>""")

    # Print-only one-page executive summary
    if df_summary is not None and "ebitda_drag" in df_summary.index:
        _ebitda_print = pretty_money(ebitda_mean)
        _ev_print = pretty_money(ev_mean)
        _p10_print = pretty_money(float(df_summary.loc["ebitda_drag", "p10"]) * ev_multiple)
        _p90_print = pretty_money(float(df_summary.loc["ebitda_drag", "p90"]) * ev_multiple)
        html_parts.append(f"""
    <div class="print-summary">
      <h2 style="border: none; margin: 0 0 0.5rem 0;">RCM Due Diligence — Executive Summary</h2>
      <p style="font-size: 0.85rem; color: var(--gray);">{hospital_display} | {ts} | Confidential</p>
      <table style="margin: 1rem 0;">
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Annual EBITDA Opportunity (Mean)</td><td class="num" style="font-weight:700;">{_ebitda_print}</td></tr>
        <tr><td>Enterprise Value at {ev_multiple}x</td><td class="num" style="font-weight:700;">{_ev_print}</td></tr>
        <tr><td>Conservative Floor (P10 EV)</td><td class="num">{_p10_print}</td></tr>
        <tr><td>Stress Ceiling (P90 EV)</td><td class="num">{_p90_print}</td></tr>
        <tr><td>Simulations</td><td class="num">{n_sims:,}</td></tr>
      </table>
      <p style="font-size: 0.8rem; color: var(--gray); margin-top: 1rem;">This is a print summary. See the full interactive report for detailed analysis, payer dashboards, and scenario explorer.</p>
    </div>""")

    html_parts.append(f"<h1>{title}</h1>")
    html_parts.append(f"<p class='meta'>{hospital_display} | Generated: {ts} | Confidential</p>")
    ev_ceil = ev_multiple + 1.5
    tombstone_html = f"""
    <div class="tombstone">
      <span><strong>Simulation:</strong> {n_sims:,} Monte Carlo iterations | P10/P90 range shown | Payer-weighted</span>
      <span class="ev-sens"><strong>Valuation Range:</strong> {ev_multiple:.1f}x to {ev_ceil:.1f}x EBITDA</span>
    </div>"""
    html_parts.append(tombstone_html)

    # Reading guide
    html_parts.append("""
    <div class="reading-guide">
      <h3>How to Read This Report</h3>
      <p class='section-desc'>This report uses Monte Carlo simulation to quantify the gap between a target hospital's revenue cycle performance and industry best practice. Every dollar figure represents an annualized opportunity. Here is what the key terms and indicators mean:</p>
      <div class="legend-grid">
        <div class="legend-item">
          <div class="legend-icon" style="background: var(--primary);">$</div>
          <div><strong>EBITDA Drag</strong> — The annual dollars lost to revenue cycle inefficiency versus best practice. This is the core opportunity number.</div>
        </div>
        <div class="legend-item">
          <div class="legend-icon" style="background: var(--accent);">EV</div>
          <div><strong>Enterprise Value</strong> — EBITDA drag multiplied by a market multiple (e.g., 8x). Represents the total valuation impact.</div>
        </div>
        <div class="legend-item">
          <div class="legend-icon" style="background: var(--green);">P10</div>
          <div><strong>Conservative (P10)</strong> — The 10th percentile outcome. 90% of simulated scenarios exceed this number. Use as a floor estimate.</div>
        </div>
        <div class="legend-item">
          <div class="legend-icon" style="background: var(--amber);">M</div>
          <div><strong>Expected (Mean)</strong> — The average across all simulations. This is the most likely outcome and the number to use in base-case modeling.</div>
        </div>
        <div class="legend-item">
          <div class="legend-icon" style="background: var(--red);">P90</div>
          <div><strong>Stress Case (P90)</strong> — The 90th percentile outcome. Only 10% of scenarios are worse than this. Use for downside risk sizing.</div>
        </div>
        <div class="legend-item">
          <div class="legend-icon" style="background: #6366f1;">?</div>
          <div><strong>"Why This Matters"</strong> — Each section opens with an explanation of why that analysis is relevant to the investment thesis.</div>
        </div>
      </div>
    </div>""")

    # How to Change Numbers / Quick Start / Intelligence features
    html_parts.append("""
    <div class="card" style="border-left: 4px solid var(--primary);">
      <h3>How to Use This Report</h3>
      <p class='section-desc'><strong>Adjust assumptions:</strong> Edit the configuration files for the target hospital or benchmark, then re-run to see updated outputs.</p>
      <ul style="margin: 0.5rem 0 0 1.5rem; font-size: 0.9rem;">
        <li><strong>Denial rates and A/R days:</strong> Initial denial rate, write-off rate, and days in accounts receivable by payer</li>
        <li><strong>Underpayments:</strong> Underpayment rate, severity, and recovery success by payer</li>
        <li><strong>Revenue and valuation:</strong> Annual net patient revenue and EBITDA-to-EV multiple</li>
      </ul>
      <p class='section-desc' style="margin-top: 0.75rem;"><strong>Calibrate with real data:</strong> Provide actual claims and denial data to replace benchmark-based assumptions with observed rates.</p>
      <p class='section-desc'><strong>Full report:</strong> Run with --full-report for initiative rankings, stress tests, value attribution, and a prioritized 100-day plan.</p>
      <p class='section-desc'><strong>Interactive analysis:</strong> Use the Scenario Explorer below to adjust the EBITDA multiple, WACC, and revenue assumptions. Numbers update in real time without re-running the model.</p>
    </div>""")

    # Embed data for client-side Scenario Explorer (including payer shock scenarios)
    rcm_data: Dict[str, Any] = {"ev_multiple": ev_multiple, "wacc": wacc, "annual_revenue": annual_revenue}
    if df_summary is not None and "ebitda_drag" in df_summary.index:
        rcm_data["ebitda_drag"] = {
            "mean": float(df_summary.loc["ebitda_drag", "mean"]),
            "p10": float(df_summary.loc["ebitda_drag", "p10"]),
            "p90": float(df_summary.loc["ebitda_drag", "p90"]),
        }
    if df_summary is not None and "drag_dar_total" in df_summary.index:
        rcm_data["extra_ar_days"] = float(df_summary.loc["drag_dar_total", "mean"])
    if shock_results:
        rcm_data["shocks"] = shock_results
    html_parts.append(f"<script>window.RCM_DATA = {json.dumps(rcm_data)};</script>")

    # Scenario Explorer (interactive)
    ev_mult_init = ev_multiple
    wacc_pct_init = int(round(wacc * 100))
    rev_init = int(annual_revenue) if annual_revenue else 500000000
    has_shocks = bool(shock_results and len(shock_results) > 0)
    shock_opts = ""
    if has_shocks:
        shock_opts = '<option value="">None (baseline)</option>'
        for s in shock_results:
            sid = s.get("id", "shock")
            name = s.get("name", sid)
            shock_opts += f'<option value="{sid}">{name}</option>'
    shock_control = f"""
        <div class="control-group">
          <label>Payer Scenario Overlay</label>
          <select id="payer_shock" style="width: 100%; padding: 8px 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,.3); background: rgba(255,255,255,.1); color: #fff; font-size: 0.9rem;">
            {shock_opts}
          </select>
          <span class="control-help">Pre-computed scenarios for payer-specific shocks (e.g., denial rate increases, policy changes).</span>
        </div>""" if has_shocks else ""
    html_parts.append(f"""
    <div class="scenario-explorer">
      <h3>Scenario Explorer — Live Sensitivity Analysis</h3>
      <p class="section-desc" style="color: rgba(255,255,255,.85);">Drag the sliders to instantly see how changes to valuation assumptions and revenue affect the opportunity size. No re-run required.</p>
      <div class="scenario-controls">
        <div class="control-group">
          <label>EBITDA Multiple</label>
          <input type="range" id="ev_mult" min="5" max="12" step="0.5" value="{ev_mult_init}" />
          <span id="ev_mult_val" style="font-size: 0.9rem;">{ev_mult_init}x</span>
          <span class="control-help">The multiplier applied to EBITDA drag to estimate enterprise value impact. Healthcare services typically trade at 7-10x.</span>
        </div>
        <div class="control-group">
          <label>Cost of Capital (WACC)</label>
          <input type="range" id="wacc_slider" min="6" max="18" step="1" value="{wacc_pct_init}" />
          <span id="wacc_val" style="font-size: 0.9rem;">{wacc_pct_init}%</span>
          <span class="control-help">Weighted average cost of capital. Used to calculate the financing cost of cash trapped in excess A/R. PE portfolio companies typically 10-15%.</span>
        </div>
        <div class="control-group">
          <label>Annual Net Patient Revenue</label>
          <input type="number" id="annual_rev" min="10000000" step="1000000" value="{rev_init}" placeholder="e.g. 500000000" />
          <span class="control-help">Total net patient service revenue (NPSR). Scales the cash-trapped and financing-cost calculations.</span>
        </div>
        {shock_control}
      </div>
      <div class="live-results">
        <div class="live-result"><span class="label">Enterprise Value Opportunity (Mean)</span><div class="value" id="live_ev_mean">—</div></div>
        <div class="live-result"><span class="label">EV Range (Conservative to Stress)</span><div class="value" id="live_ev_range">—</div></div>
        <div class="live-result"><span class="label">Cash Trapped in Excess A/R</span><div class="value" id="live_cash">—</div></div>
        <div class="live-result"><span class="label">Annual Financing Cost</span><div class="value" id="live_financing">—</div></div>
      </div>
    </div>""")

    # 1. Executive Summary
    if df_summary is not None and "ebitda_drag" in df_summary.index:
        ebitda_str = pretty_money(ebitda_mean)
        ev_str = pretty_money(ev_mean)
        ebitda_p10 = float(df_summary.loc["ebitda_drag", "p10"])
        ebitda_p90 = float(df_summary.loc["ebitda_drag", "p90"])
        ev_p10_str = pretty_money(ebitda_p10 * ev_multiple)
        ev_p90_str = pretty_money(ebitda_p90 * ev_multiple)
        denom = float(annual_revenue or 0) * float(ebitda_margin) * float(ev_multiple)
        ev_uplift_pct = (ev_mean / denom * 100) if denom and denom > 0 else 0
        ev_uplift_str = f"{ev_uplift_pct:.0f}%" if ev_uplift_pct > 0 else ""
        active_title = f"Inherent RCM Inefficiencies Represent a {ebitda_str} EBITDA Recovery Opportunity"
        if ev_uplift_str:
            active_title += f" and {ev_uplift_str} EV Uplift"
        active_title += "."
        # Compute component breakdowns for KPI cards
        denial_wo = float(df_summary.loc["drag_denial_writeoff", "mean"]) if "drag_denial_writeoff" in df_summary.index else 0
        underpay_lk = float(df_summary.loc["drag_underpay_leakage", "mean"]) if "drag_underpay_leakage" in df_summary.index else 0
        econ_drag = float(df_summary.loc["economic_drag", "mean"]) if "economic_drag" in df_summary.index else 0
        dar_days = float(df_summary.loc["drag_dar_total", "mean"]) if "drag_dar_total" in df_summary.index else 0

        source_card_html = _build_source_confidence_card(actual_cfg_load, outdir=outdir)
        if source_card_html:
            html_parts.append(source_card_html)

        html_parts.append(f"""
    <h2 id="exec-summary">1. Executive Summary</h2>
    <p class='section-desc'><strong>Why this matters:</strong> This is the headline number for the investment thesis. It quantifies the dollar gap between current revenue cycle performance and best-practice, translating directly into EBITDA uplift and enterprise value creation.</p>
    <p style="font-size: 1.05rem; font-weight: 600; color: var(--slate); margin-bottom: 1rem;">{active_title}</p>

    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">EBITDA Opportunity</div>
        <div class="kpi-value" id="ex_ebitda">{ebitda_str}</div>
        <div class="kpi-sub">Annual recoverable drag</div>
      </div>
      <div class="kpi-card kpi-accent">
        <div class="kpi-label">Enterprise Value</div>
        <div class="kpi-value" id="ex_ev">{ev_str}</div>
        <div class="kpi-sub">At <span id="ex_mult">{ev_multiple}</span>x multiple</div>
      </div>
      <div class="kpi-card kpi-green">
        <div class="kpi-label">Conservative Floor (P10)</div>
        <div class="kpi-value">{ev_p10_str}</div>
        <div class="kpi-sub">90% of outcomes exceed this</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Stress Ceiling (P90)</div>
        <div class="kpi-value">{ev_p90_str}</div>
        <div class="kpi-sub" id="ex_range">Tail-risk scenario</div>
      </div>
    </div>

    <div class="kpi-grid" style="margin-top: 0;">
      <div class="kpi-card">
        <div class="kpi-label">Denial Write-Offs</div>
        <div class="kpi-value">{pretty_money(denial_wo)}</div>
        <div class="kpi-sub">Largest drag component</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Underpayment Leakage</div>
        <div class="kpi-value">{pretty_money(underpay_lk)}</div>
        <div class="kpi-sub">Below-contract payments</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Working Capital Cost</div>
        <div class="kpi-value">{pretty_money(econ_drag)}</div>
        <div class="kpi-sub">Cash trapped in A/R</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Excess A/R Days</div>
        <div class="kpi-value">{dar_days:.0f}</div>
        <div class="kpi-sub">Days beyond benchmark</div>
      </div>
    </div>

    <div class="observation-box">
      <strong>Key Observations</strong>
      <ul>
        <li>{html_escape(insights[0]) if insights else "Closing the RCM gap unlocks material EBITDA and EV upside."}</li>
        <li>{html_escape(insights[1]) if len(insights) > 1 else "Denial write-offs typically drive the majority of drag; CDI and prior-auth improvements offer highest leverage."}</li>
        <li>{html_escape(insights[2]) if len(insights) > 2 else "Commercial payer volatility drives tail risk; government payers remain stable but inefficient."}</li>
        <li><strong>Reading the range:</strong> The Mean is the expected outcome. P10 (conservative) is the floor that 90% of scenarios exceed. P90 (stress case) captures downside tail risk and is higher than the mean by design.</li>
      </ul>
    </div>""")
        # Confidence Grade
        grade_factors = []
        has_calibration = data_confidence_path and os.path.exists(data_confidence_path)
        has_sims = n_sims >= 10000
        has_benchmark = benchmark_config_path and os.path.exists(benchmark_config_path)
        has_sensitivity = df_sens is not None and len(df_sens) > 0
        has_stress = df_stress is not None and len(df_stress) > 0
        grade_score = 0
        if has_calibration:
            grade_score += 2
            grade_factors.append("Calibrated with actual claims data")
        else:
            grade_factors.append("Using benchmark-based estimates (no calibration)")
        if has_sims:
            grade_score += 1
            grade_factors.append(f"{n_sims:,} simulations (statistically robust)")
        if has_benchmark:
            grade_score += 1
            grade_factors.append("Published benchmark comparison active")
        if has_sensitivity:
            grade_score += 1
            grade_factors.append("Sensitivity analysis completed")
        if has_stress:
            grade_score += 1
            grade_factors.append("Stress testing completed")
        if grade_score >= 5:
            grade_letter, grade_class, grade_desc = "A", "grade-A", "High confidence — calibrated model with full analytics"
        elif grade_score >= 3:
            grade_letter, grade_class, grade_desc = "B", "grade-B", "Good confidence — benchmark-based with robust simulation"
        elif grade_score >= 2:
            grade_letter, grade_class, grade_desc = "C", "grade-C", "Moderate confidence — validate key assumptions in diligence"
        else:
            grade_letter, grade_class, grade_desc = "D", "grade-D", "Preliminary — requires calibration with actual data"
        grade_bullets = "".join(f"<li>{f}</li>" for f in grade_factors)
        html_parts.append(f"""
    <div class="card" id="confidence-grade" style="margin-top: 1.25rem;">
      <h3>Analysis Confidence</h3>
      <div style="display: flex; align-items: flex-start; gap: 1.25rem; flex-wrap: wrap;">
        <div class="grade-card">
          <div class="grade-letter {grade_class}">{grade_letter}</div>
          <div class="grade-detail">
            <strong>{grade_desc}</strong>
            Composite score based on data quality, simulation depth, and analytical coverage.
          </div>
        </div>
        <ul style="font-size: 0.8rem; color: var(--gray); margin: 0; padding-left: 1.25rem; flex: 1; min-width: 200px;">{grade_bullets}</ul>
      </div>
    </div>""")

    else:
        html_parts.append("<p><em>Summary data not found.</em></p>")

    # 1-dash. Visual Opportunity Breakdown (CSS waterfall + payer dashboard)
    if df_summary is not None and "ebitda_drag" in df_summary.index:
        denial_wo_v = float(df_summary.loc["drag_denial_writeoff", "mean"]) if "drag_denial_writeoff" in df_summary.index else 0
        underpay_v = float(df_summary.loc["drag_underpay_leakage", "mean"]) if "drag_underpay_leakage" in df_summary.index else 0
        rework_denial_v = float(df_summary.loc["drag_denial_rework_cost", "mean"]) if "drag_denial_rework_cost" in df_summary.index else 0
        rework_up_v = float(df_summary.loc["drag_underpay_cost", "mean"]) if "drag_underpay_cost" in df_summary.index else 0
        econ_v = float(df_summary.loc["economic_drag", "mean"]) if "economic_drag" in df_summary.index else 0
        total_v = float(df_summary.loc["ebitda_drag", "mean"])
        rework_total_v = rework_denial_v + rework_up_v

        max_bar = max(abs(denial_wo_v), abs(underpay_v), abs(rework_total_v), abs(econ_v), abs(total_v), 1)
        def _bar_h(v: float) -> int:
            return max(4, int(100 * abs(v) / max_bar))

        def _pct_of_total(v: float) -> str:
            if total_v == 0: return ""
            return f"{abs(v)/abs(total_v)*100:.0f}%"

        html_parts.append(f"""
    <div class="card">
      <h3>Opportunity Breakdown</h3>
      <p class='section-desc'>Visual decomposition of the total EBITDA drag by category. The tallest bar represents the largest opportunity.</p>
      <div class="mini-waterfall">
        <div class="wf-bar-group">
          <div class="wf-amount">{pretty_money(denial_wo_v)}</div>
          <div class="wf-bar denial" style="height: {_bar_h(denial_wo_v)}px;"></div>
          <div class="wf-label">Denial Write-Offs<br>({_pct_of_total(denial_wo_v)})</div>
        </div>
        <div class="wf-bar-group">
          <div class="wf-amount">{pretty_money(underpay_v)}</div>
          <div class="wf-bar underpay" style="height: {_bar_h(underpay_v)}px;"></div>
          <div class="wf-label">Underpayment Leakage<br>({_pct_of_total(underpay_v)})</div>
        </div>
        <div class="wf-bar-group">
          <div class="wf-amount">{pretty_money(rework_total_v)}</div>
          <div class="wf-bar rework" style="height: {_bar_h(rework_total_v)}px;"></div>
          <div class="wf-label">Rework Costs<br>({_pct_of_total(rework_total_v)})</div>
        </div>
        <div class="wf-bar-group">
          <div class="wf-amount">{pretty_money(econ_v)}</div>
          <div class="wf-bar economic" style="height: {_bar_h(econ_v)}px;"></div>
          <div class="wf-label">Working Capital<br>({_pct_of_total(econ_v)})</div>
        </div>
        <div class="wf-bar-group">
          <div class="wf-amount" style="color: var(--primary); font-size: 0.8rem;">{pretty_money(total_v)}</div>
          <div class="wf-bar total" style="height: {_bar_h(total_v)}px;"></div>
          <div class="wf-label" style="font-weight: 600;">Total EBITDA Drag</div>
        </div>
      </div>
    </div>""")

    # 1-dash-b. Payer-level dashboard cards with progress bars
    if actual_cfg_load and benchmark_cfg_load:
        a_params = _extract_payer_params(actual_cfg_load)
        b_params = _extract_payer_params(benchmark_cfg_load)
        a_payers_cfg = actual_cfg_load.get("payers") or {}

        payer_cards_html = []
        payer_colors = {"Medicare": "#2563eb", "Medicaid": "#7c3aed", "Commercial": "#059669", "SelfPay": "#64748b"}
        for payer in ("Medicare", "Medicaid", "Commercial"):
            if payer not in a_params:
                continue
            aa = a_params[payer]
            bb = b_params.get(payer, {})
            rev_share = a_payers_cfg.get(payer, {}).get("revenue_share", 0)
            color = payer_colors.get(payer, "#475569")

            card_html = f"""
        <div class="payer-card" style="border-top: 3px solid {color};">
          <div class="payer-card-header">
            <h4>{payer}</h4>
            <span class="payer-share">{rev_share*100:.0f}% of Revenue</span>
          </div>"""

            # IDR progress bar
            idr_a = aa.get("idr")
            idr_b = bb.get("idr")
            if idr_a is not None and idr_b is not None:
                idr_pct = min(100, (idr_a / max(idr_a, 0.30)) * 100)
                bench_marker = min(100, (idr_b / max(idr_a, 0.30)) * 100)
                bar_class = "bad" if idr_a > idr_b * 1.2 else ("warn" if idr_a > idr_b else "good")
                card_html += f"""
          <div class="payer-metric"><span class="pm-label">Initial Denial Rate</span><span class="pm-value">{idr_a*100:.1f}%</span></div>
          <div class="gap-bar-wrap">
            <div class="gap-bar"><div class="gap-bar-fill {bar_class}" style="width: {idr_pct:.0f}%;"></div></div>
            <div class="gap-bar-labels"><span>0%</span><span>Benchmark: {idr_b*100:.1f}%</span></div>
          </div>"""

            # FWR progress bar
            fwr_a = aa.get("fwr")
            fwr_b = bb.get("fwr")
            if fwr_a is not None and fwr_b is not None:
                fwr_pct = min(100, (fwr_a / max(fwr_a, 0.40)) * 100)
                bar_class = "bad" if fwr_a > fwr_b * 1.2 else ("warn" if fwr_a > fwr_b else "good")
                card_html += f"""
          <div class="payer-metric"><span class="pm-label">Write-Off Rate</span><span class="pm-value">{fwr_a*100:.1f}%</span></div>
          <div class="gap-bar-wrap">
            <div class="gap-bar"><div class="gap-bar-fill {bar_class}" style="width: {fwr_pct:.0f}%;"></div></div>
            <div class="gap-bar-labels"><span>0%</span><span>Benchmark: {fwr_b*100:.1f}%</span></div>
          </div>"""

            # DAR progress bar
            dar_a = aa.get("dar")
            dar_b = bb.get("dar")
            if dar_a is not None and dar_b is not None:
                dar_pct = min(100, (dar_a / max(dar_a, 90)) * 100)
                bar_class = "bad" if dar_a > dar_b * 1.15 else ("warn" if dar_a > dar_b else "good")
                card_html += f"""
          <div class="payer-metric"><span class="pm-label">Days in A/R</span><span class="pm-value">{dar_a:.0f} days</span></div>
          <div class="gap-bar-wrap">
            <div class="gap-bar"><div class="gap-bar-fill {bar_class}" style="width: {dar_pct:.0f}%;"></div></div>
            <div class="gap-bar-labels"><span>0</span><span>Benchmark: {dar_b:.0f} days</span></div>
          </div>"""

            card_html += "</div>"
            payer_cards_html.append(card_html)

        if payer_cards_html:
            html_parts.append("""
    <div class="card" id="payer-dashboard">
      <h3>Payer Performance Dashboard</h3>
      <p class='section-desc'><strong>Why this matters:</strong> Each payer behaves differently. These cards show the target hospital's key metrics per payer versus the benchmark, with visual progress bars indicating how far each is from best practice. Red bars signal the largest gaps and highest-priority areas for intervention.</p>
    </div>""")
            html_parts.append('<div class="payer-grid">')
            html_parts.append("\n".join(payer_cards_html))
            html_parts.append("</div>")

    # 1a. Actual vs Benchmark — Where the numbers come from
    if df_summary is not None and "ebitda_drag" in df_summary.index:
        e_mean = float(df_summary.loc["ebitda_drag", "mean"])
        actual_mean = float(df_summary.loc["actual_rcm_ebitda_impact", "mean"]) if "actual_rcm_ebitda_impact" in df_summary.index else None
        bench_mean = float(df_summary.loc["bench_rcm_ebitda_impact", "mean"]) if "bench_rcm_ebitda_impact" in df_summary.index else None
        html_parts.append("""
    <div class="card" id="actual-vs-benchmark">
      <h3>How the EBITDA Opportunity Is Calculated</h3>
      <p class='section-desc'>The total opportunity equals the difference between the target hospital's RCM losses and a best-practice benchmark. The benchmark represents top-quartile peer performance based on HFMA MAP Keys and published industry data.</p>
      <table><tr><th>Component</th><th>Mean Annual Value</th></tr>
      <tr><td>Target Hospital RCM Losses</td><td class="num">""" + (pretty_money(actual_mean) if actual_mean is not None else "—") + """</td></tr>
      <tr><td>Best-Practice Benchmark RCM Losses</td><td class="num">""" + (pretty_money(bench_mean) if bench_mean is not None else "—") + """</td></tr>
      <tr><td><strong>Recoverable EBITDA Opportunity (Gap)</strong></td><td class="num"><strong>""" + pretty_money(e_mean) + """</strong></td></tr>
      </table>
    </div>""")

    # 1a2. Benchmark gap table (config-driven)
    gap_table = _build_benchmark_gap_table(actual_cfg_load, benchmark_cfg_load)
    if gap_table:
        html_parts.append(gap_table)

    prov_html = _build_provenance_methodology_section(outdir)
    if prov_html:
        html_parts.append(prov_html)

    # 1b. Economic drag clarity box
    if df_summary is not None and "drag_dar_total" in df_summary.index and annual_revenue and annual_revenue > 0:
        extra_ar = float(df_summary.loc["drag_dar_total", "mean"])
        cash_trapped = (annual_revenue / 365.0) * extra_ar
        financing_cost = cash_trapped * wacc
        html_parts.append(f"""
    <div class="card" id="economic-drag-card">
      <h3>Working Capital Impact</h3>
      <p class='section-desc'><strong>Why this matters:</strong> Slow collections tie up cash that could fund operations, acquisitions, or debt paydown. This card shows how many extra days of revenue sit uncollected and what that costs in financing.</p>
      <table><tr><th>Metric</th><th>Value</th></tr>
      <tr><td>Excess Days in A/R (mean)</td><td id="econ_ar">{extra_ar:.1f} days</td></tr>
      <tr><td>Cash Trapped in Excess A/R</td><td id="econ_cash">{pretty_money(cash_trapped)}</td></tr>
      <tr><td>Annual Financing Cost (at <span id="econ_wacc_pct">{wacc*100:.0f}</span>% WACC)</td><td id="econ_financing">{pretty_money(financing_cost)}</td></tr>
      </table></div>""")

    # 1c. NPSR / Debt-to-EBITDA covenant bridge (capital markets desk)
    if debt is not None and debt > 0 and annual_revenue and annual_revenue > 0 and df_summary is not None and "ebitda_drag" in df_summary.index:
        ebitda_proxy = annual_revenue * ebitda_margin  # NPSR-based EBITDA proxy
        uplift = float(df_summary.loc["ebitda_drag", "mean"])
        ratio_before = debt / ebitda_proxy if ebitda_proxy > 0 else 0
        ratio_after = debt / (ebitda_proxy + uplift) if (ebitda_proxy + uplift) > 0 else 0
        improvement = ratio_before - ratio_after
        html_parts.append(f"""
    <div class="card" id="covenant-bridge">
      <h3>Debt Covenant Sensitivity</h3>
      <p class='section-desc'><strong>Why this matters:</strong> For leveraged healthcare platforms, even modest EBITDA improvements can meaningfully improve covenant headroom and reduce refinancing risk. This shows how the {pretty_money(uplift)} EBITDA uplift moves the Debt-to-EBITDA ratio, assuming {ebitda_margin*100:.0f}% EBITDA margin on Net Patient Service Revenue.</p>
      <table><tr><th>Metric</th><th>Value</th></tr>
      <tr><td>Total Debt</td><td class="num">{pretty_money(debt)}</td></tr>
      <tr><td>Current EBITDA (NPSR x Margin)</td><td class="num">{pretty_money(ebitda_proxy)}</td></tr>
      <tr><td>Debt / EBITDA (Current)</td><td class="num">{ratio_before:.1f}x</td></tr>
      <tr><td>Pro Forma EBITDA (With RCM Uplift)</td><td class="num">{pretty_money(ebitda_proxy + uplift)}</td></tr>
      <tr><td>Debt / EBITDA (Pro Forma)</td><td class="num">{ratio_after:.1f}x</td></tr>
      <tr><td><strong>Covenant Headroom Improvement</strong></td><td class="num"><strong>{improvement:.1f}x</strong></td></tr>
      </table>
      <p class='section-desc' style="margin-top: 0.5rem;"><em>To customize: set the debt amount and EBITDA margin in the economics and hospital sections of the configuration.</em></p>
    </div>""")

    # 1d. Cost to Collect vs HFMA benchmarking
    if rcm_spend_annual is not None and rcm_spend_annual > 0 and annual_revenue and annual_revenue > 0:
        pct = (rcm_spend_annual / annual_revenue) * 100
        hfma_lo, hfma_hi = 3.0, 4.0
        gap_lo = pct - hfma_lo
        gap_hi = pct - hfma_hi
        status = "within" if hfma_lo <= pct <= hfma_hi else ("above" if pct > hfma_hi else "below")
        html_parts.append(f"""
    <div class="card" id="cost-to-collect">
      <h3>Cost to Collect vs. Industry Benchmark</h3>
      <p class='section-desc'><strong>Why this matters:</strong> Cost to Collect measures operational efficiency of the revenue cycle. A ratio above 4% of Net Patient Revenue signals overstaffing, manual processes, or vendor cost bloat that an operating partner can address.</p>
      <table><tr><th>Metric</th><th>Value</th></tr>
      <tr><td>Annual RCM Spend</td><td class="num">{pretty_money(rcm_spend_annual)}</td></tr>
      <tr><td>Net Patient Revenue</td><td class="num">{pretty_money(annual_revenue)}</td></tr>
      <tr><td>Cost to Collect (% of Revenue)</td><td class="num">{pct:.1f}%</td></tr>
      <tr><td>HFMA Benchmark Range</td><td class="num">3.0% - 4.0%</td></tr>
      <tr><td><strong>Assessment</strong></td><td class="num"><strong>{status.title()} Benchmark</strong></td></tr>
      </table>
      <p class='section-desc' style="margin-top: 0.5rem;"><em>To enable this section, add the hospital's annual RCM spend in the configuration file.</em></p>
    </div>""")

    # 1e. Service line / High-acuity CDI targeting (stub)
    html_parts.append("""
    <div class="card" style="border-left: 4px solid #94a3b8;">
      <h3>Service Line Opportunity (Roadmap)</h3>
      <p class='section-desc'><strong>Why this matters:</strong> Revenue leakage is rarely uniform. High-acuity service lines (Cardiology, Orthopedics, Neurosurgery) typically carry outsized denial rates and higher dollar-per-claim exposure. Isolating these lines reveals where targeted CDI and coding interventions generate the fastest ROI.</p>
      <p><strong>Available with service line data:</strong> When payer-level denial and revenue data is broken out by service line, this section will show which clinical areas drive the highest leakage per dollar of revenue.</p>
      <p class='section-desc'><em>Current approach: payer-level breakdowns serve as a proxy, since Commercial and Medicare tend to carry the highest-acuity volumes.</em></p>
    </div>""")

    # Value Creation Timeline + Quick Wins + Investment vs Return
    if df_summary is not None and "ebitda_drag" in df_summary.index:
        _tl_total = float(df_summary.loc["ebitda_drag", "mean"])
        _tl_denial = float(df_summary.loc["drag_denial_writeoff", "mean"]) if "drag_denial_writeoff" in df_summary.index else 0
        _tl_underpay = float(df_summary.loc["drag_underpay_leakage", "mean"]) if "drag_underpay_leakage" in df_summary.index else 0
        _tl_rework_d = float(df_summary.loc["drag_denial_rework_cost", "mean"]) if "drag_denial_rework_cost" in df_summary.index else 0
        _tl_rework_u = float(df_summary.loc["drag_underpay_cost", "mean"]) if "drag_underpay_cost" in df_summary.index else 0

        ramp = [
            ("Q1\nMo 1-3", 0.08, "q1"), ("Q2\nMo 4-6", 0.20, "q1"),
            ("Q3\nMo 7-9", 0.38, "q2"), ("Q4\nMo 10-12", 0.55, "q2"),
            ("Q5\nMo 13-15", 0.68, "q3"), ("Q6\nMo 16-18", 0.78, "q3"),
            ("Q7\nMo 19-21", 0.88, "q4"), ("Q8\nMo 22-24", 0.95, "q4"),
        ]
        max_h = 140
        tl_bars = ""
        for label, pct, cls in ramp:
            h = max(4, int(max_h * pct))
            amt = _tl_total * pct
            lbl_html = label.replace("\n", "<br>")
            tl_bars += f"""
          <div class="tl-bar-wrap">
            <div class="tl-pct">{pct*100:.0f}%</div>
            <div class="tl-amt">{pretty_money(amt)}</div>
            <div class="tl-bar {cls}" style="height: {h}px;"></div>
            <div class="tl-label">{lbl_html}</div>
          </div>"""

        html_parts.append(f"""
    <h2 id="sec-timeline">Value Creation Timeline</h2>
    <p class='section-desc'><strong>Why this matters:</strong> The investment committee needs to know not just how much, but when. This timeline shows the expected EBITDA capture ramp over 24 months based on typical RCM improvement phasing. Quick wins (coding audits, prior-auth fixes) drive early results; structural changes (technology, contract renegotiation) drive the back half.</p>

    <div class="card">
      <h3>Projected EBITDA Capture Ramp (24 Months)</h3>
      <p class='section-desc'>Cumulative percentage of the {pretty_money(_tl_total)} annual opportunity captured over time. Based on industry-standard RCM improvement phasing; adjust to reflect specific initiative timelines.</p>
      <div class="timeline-grid">{tl_bars}
      </div>
      <div style="display: flex; gap: 1.5rem; margin-top: 0.75rem; font-size: 0.75rem; color: var(--gray); flex-wrap: wrap;">
        <span><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#64748b;margin-right:4px;vertical-align:middle;"></span>Assessment and Quick Wins</span>
        <span><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#0891b2;margin-right:4px;vertical-align:middle;"></span>Process Redesign</span>
        <span><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#059669;margin-right:4px;vertical-align:middle;"></span>Technology and Training</span>
        <span><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#10b981;margin-right:4px;vertical-align:middle;"></span>Maturation</span>
      </div>
    </div>""")

        # Quick Wins vs Long-Term
        qw_items = [
            ("Coding and Documentation Audit", "Days 1-30", pretty_money(_tl_denial * 0.05), "Review top denial categories, correct recurring coding errors, and tighten clinical documentation."),
            ("Prior Authorization Automation", "Days 1-60", pretty_money(_tl_denial * 0.08), "Implement automated prior-auth checking at scheduling and registration to prevent avoidable denials."),
            ("Underpayment Variance Identification", "Days 30-60", pretty_money(_tl_underpay * 0.10), "Run contract-to-payment variance analysis for top payers, flag underpaid claims for recovery."),
            ("A/R Follow-Up Acceleration", "Days 30-90", pretty_money((_tl_rework_d + _tl_rework_u) * 0.12), "Prioritize aged accounts by dollar value, clear backlog of actionable claims in the 60-90 day bucket."),
        ]
        lt_items = [
            ("Payer Contract Renegotiation", "Months 6-12", pretty_money(_tl_underpay * 0.35), "Renegotiate rates with underperforming payers using payment variance data as leverage."),
            ("RCM Technology Platform Upgrade", "Months 6-18", pretty_money(_tl_denial * 0.20), "Deploy AI-assisted coding, automated claim scrubbing, and real-time denial prediction."),
            ("CDI Program Buildout", "Months 3-12", pretty_money(_tl_denial * 0.15), "Hire or redeploy CDI specialists for high-acuity service lines; target DRG optimization."),
            ("Appeals Process Redesign", "Months 3-9", pretty_money(_tl_rework_d * 0.25), "Restructure denial management workflow with dedicated teams by payer and root cause."),
        ]
        qw_rows = "".join(f"<tr><td>{n}</td><td>{t}</td><td class='num'>{v}</td><td>{d}</td></tr>" for n, t, v, d in qw_items)
        lt_rows = "".join(f"<tr><td>{n}</td><td>{t}</td><td class='num'>{v}</td><td>{d}</td></tr>" for n, t, v, d in lt_items)

        html_parts.append(f"""
    <div class="card">
      <h3>Quick Wins (Days 1-90)</h3>
      <p class='section-desc'>These initiatives can start immediately and generate measurable results within the first quarter. Low capital, high visibility.</p>
      <table><tr><th>Initiative</th><th>Timeline</th><th>Est. Annual Impact</th><th>Description</th></tr>
      {qw_rows}
      </table>
    </div>
    <div class="card">
      <h3>Structural Improvements (Months 3-18)</h3>
      <p class='section-desc'>Larger initiatives that require planning, investment, and organizational change but deliver the majority of long-term value.</p>
      <table><tr><th>Initiative</th><th>Timeline</th><th>Est. Annual Impact</th><th>Description</th></tr>
      {lt_rows}
      </table>
    </div>""")

        # Investment Required vs Return
        invest_tech = _tl_total * 0.06
        invest_staff = _tl_total * 0.12
        invest_consulting = _tl_total * 0.04
        invest_total = invest_tech + invest_staff + invest_consulting
        yr1_capture = _tl_total * 0.55
        yr2_capture = _tl_total * 0.95
        roi_yr1 = ((yr1_capture - invest_total) / invest_total * 100) if invest_total > 0 else 0
        payback_months = (invest_total / (_tl_total / 12)) if _tl_total > 0 else 0

        html_parts.append(f"""
    <div class="card">
      <h3>Investment Required vs. Return</h3>
      <p class='section-desc'><strong>Why this matters:</strong> The opportunity is not free. This table estimates the investment needed to capture the modeled EBITDA, the expected payback period, and the year-1 ROI. Assumptions are based on typical healthcare PE portfolio company implementation costs and can be overridden with actual vendor quotes.</p>
      <table>
        <tr><th>Investment Category</th><th>Estimated Cost</th><th>Notes</th></tr>
        <tr><td>RCM Technology and Automation</td><td class="num">{pretty_money(invest_tech)}</td><td>Claim scrubbers, AI coding, denial prediction tools</td></tr>
        <tr><td>Staffing (CDI, Appeals, A/R)</td><td class="num">{pretty_money(invest_staff)}</td><td>Incremental FTEs or outsourced team augmentation</td></tr>
        <tr><td>Consulting and Implementation</td><td class="num">{pretty_money(invest_consulting)}</td><td>RCM advisory, change management, training</td></tr>
        <tr><td><strong>Total Investment</strong></td><td class="num"><strong>{pretty_money(invest_total)}</strong></td><td></td></tr>
      </table>
      <table style="margin-top: 0.75rem;">
        <tr><th>Return Metric</th><th>Value</th></tr>
        <tr><td>Year 1 EBITDA Capture (55%)</td><td class="num">{pretty_money(yr1_capture)}</td></tr>
        <tr><td>Year 2 EBITDA Capture (95%)</td><td class="num">{pretty_money(yr2_capture)}</td></tr>
        <tr><td>Payback Period</td><td class="num">{payback_months:.0f} months</td></tr>
        <tr><td>Year 1 ROI</td><td class="num">{roi_yr1:.0f}%</td></tr>
      </table>
      <p class='section-desc' style="margin-top: 0.5rem;"><em>Cost ratios: Technology ~6% of opportunity, Staffing ~12%, Advisory ~4%. Adjust based on vendor bids and current team capacity.</em></p>
    </div>""")

    # 2. Deal Summary Chart
    html_parts.append("<h2 id='sec-deal'>2. Deal Opportunity Range</h2>")
    html_parts.append("<p class='section-desc'><strong>Why this matters:</strong> This is the valuation bridge. It translates the EBITDA drag into enterprise value at your target multiple, giving the deal team a clear range for the investment memo. P10 is the conservative floor (90% of outcomes exceed this), Mean is the expected case, and P90 captures tail risk.</p>")
    html_parts.append(_img_tag(deal_path, "Deal Opportunity"))
    if df_summary is not None and "ebitda_drag" in df_summary.index:
        e_p10 = float(df_summary.loc["ebitda_drag", "p10"])
        e_mean = float(df_summary.loc["ebitda_drag", "mean"])
        e_p90 = float(df_summary.loc["ebitda_drag", "p90"])
        mult = ev_multiple
        html_parts.append(f"""
    <table><tr><th>Scenario</th><th>EBITDA Opportunity</th><th>Enterprise Value @ {mult:.1f}x</th></tr>
    <tr><td>Conservative (P10)</td><td class="num">{pretty_money(e_p10)}</td><td class="num">{pretty_money(e_p10 * mult)}</td></tr>
    <tr><td>Expected (Mean)</td><td class="num">{pretty_money(e_mean)}</td><td class="num">{pretty_money(e_mean * mult)}</td></tr>
    <tr><td>Stress Case (P90)</td><td class="num">{pretty_money(e_p90)}</td><td class="num">{pretty_money(e_p90 * mult)}</td></tr>
    </table>""")

    # 2a. Risk-Adjusted Bid Price Impact
    if df_summary is not None and "ebitda_drag" in df_summary.index:
        _bid_ebitda = float(df_summary.loc["ebitda_drag", "mean"])
        _bid_p10 = float(df_summary.loc["ebitda_drag", "p10"])
        _bid_scenarios = [
            ("Conservative (30% credit)", 0.30, "PE standard for unvalidated RCM opportunities"),
            ("Base Case (50% credit)", 0.50, "Typical for benchmark-based analysis with some data support"),
            ("Aggressive (70% credit)", 0.70, "Appropriate when calibrated with actual claims data"),
        ]
        bid_rows = ""
        for label, pct, note in _bid_scenarios:
            credited_ebitda = _bid_ebitda * pct
            credited_ev = credited_ebitda * ev_multiple
            floor_ev = _bid_p10 * pct * ev_multiple
            bid_rows += (
                f"<tr><td>{label}</td>"
                f"<td class='num'>{pretty_money(credited_ebitda)}</td>"
                f"<td class='num'>{pretty_money(credited_ev)}</td>"
                f"<td class='num'>{pretty_money(floor_ev)}</td>"
                f"<td>{note}</td></tr>"
            )
        html_parts.append(f"""
    <div class="card" id="sec-bid-impact">
      <h3>Risk-Adjusted Bid Price Impact</h3>
      <p class='section-desc'><strong>Why this matters:</strong> PE firms rarely underwrite 100% of modeled RCM upside at close. This table shows how much of the opportunity to credit in the bid price at different confidence levels. The conservative scenario (30%) is standard for pre-LOI; the base case (50%) is typical for confirmatory diligence with benchmark data; aggressive (70%) requires actual claims validation.</p>
      <table>
        <tr><th>Underwriting Scenario</th><th>Credited EBITDA</th><th>EV Impact @ {ev_multiple}x</th><th>EV Floor (P10)</th><th>Basis</th></tr>
        {bid_rows}
      </table>
      <p class='section-desc' style="margin-top: 0.5rem;"><em>The full {pretty_money(_bid_ebitda)} opportunity represents the mean annual EBITDA drag. Risk-adjusted figures reflect what should be reflected in the purchase price or post-close operating plan, depending on deal structure.</em></p>
    </div>""")

    # 2b. Distribution Summary
    html_parts.append("<h2>2b. Distribution Summary</h2>")
    html_parts.append("<p class='section-desc'><strong>Why this matters:</strong> This breaks the total opportunity into its component parts so the deal team knows exactly where the value sits. Each row is a distinct lever that an operating partner can address independently.</p>")
    html_parts.append("<p class='section-desc'>Format: Expected (Mean) | Conservative (P10) | Stress Case (P90). Positive values indicate the target underperforms the benchmark.</p>")
    if df_summary is not None:
        metrics_order = ["ebitda_drag", "economic_drag", "drag_denial_writeoff", "drag_underpay_leakage", "drag_denial_rework_cost", "drag_underpay_cost", "drag_dar_total"]
        rows = []
        for m in metrics_order:
            if m in df_summary.index:
                rows.append(_fmt_metric_row(m, df_summary.loc[m]))
        html_parts.append("<table><tr><th>Metric</th><th>Expected (Mean)</th><th style='color:var(--green);'>Conservative (P10)</th><th style='color:var(--red);'>Stress Case (P90)</th></tr>")
        html_parts.append("".join(rows))
        html_parts.append("</table>")
    else:
        html_parts.append("<p><em>summary.csv not found.</em></p>")

    # 3. EBITDA Waterfall
    wf_active = f"Addressable RCM Leakage Totals {pretty_money(ebitda_mean)} at Mean; Denial Write-Offs and Underpayment Recovery Drive the Bridge."
    html_parts.append("<h2 id='sec-waterfall'>3. Strategic Value Bridge</h2>")
    html_parts.append("<p class='section-desc'><strong>Why this matters:</strong> The waterfall shows exactly where value leaks out of the revenue cycle and how much each category contributes. This is the roadmap for the 100-day plan: fix the tallest bars first.</p>")
    html_parts.append(f"<p style='font-size: 1.02rem; font-weight: 600; color: var(--slate); margin-bottom: 0.5rem;'>{wf_active}</p>")
    html_parts.append("<div class='exec-trio-viz'>")
    html_parts.append(_img_tag(waterfall_path, "EBITDA Waterfall"))
    html_parts.append("</div>")

    # 3b. Monte Carlo distribution
    mc_active = "Value Gap Distribution: Distance Between Actual and Benchmark Peaks Represents Recoverable EBITDA Opportunity."
    html_parts.append("<h2>3b. Risk and Reward Profile</h2>")
    html_parts.append("<p class='section-desc'><strong>Why this matters:</strong> Monte Carlo simulation runs thousands of scenarios with randomized inputs. The distribution shows not just the expected outcome, but the full range of possibilities, helping size position risk and set realistic targets for the operating plan.</p>")
    html_parts.append(f"<p style='font-size: 1.02rem; font-weight: 600; color: var(--slate); margin-bottom: 0.5rem;'>{mc_active}</p>")
    html_parts.append("<div class='exec-trio-viz'>")
    html_parts.append(_img_tag(dist_path, "Monte Carlo Distribution"))
    html_parts.append("</div>")

    # 4. Actionable Insights
    html_parts.append("<h2 id='sec-insights'>4. Actionable Insights</h2>")
    html_parts.append("<p class='section-desc'><strong>Why this matters:</strong> These are the specific operational moves that convert the modeled opportunity into realized EBITDA. Each recommendation is tied to the highest-impact drivers identified in the simulation.</p>")
    if insights:
        html_parts.append("<ol class='insight-list'>")
        for ins in insights:
            html_parts.append(f"<li>{ins}</li>")
        html_parts.append("</ol>")
    else:
        html_parts.append("<p><em>No insights generated.</em></p>")

    # 5. Diligence Requests That Move the Number
    if df_sens is not None and len(df_sens) > 0:
        from ..infra.diligence_requests import build_diligence_requests

        diligence_rows = build_diligence_requests(df_sens, top_n=3)
        if diligence_rows:
            html_parts.append("<h2 id='sec-diligence'>5. Diligence Requests That Move the Number</h2>")
            html_parts.append("<p class='section-desc'><strong>Why this matters:</strong> Before closing, the deal team needs to validate the model's top assumptions with real data. These are the specific data requests that will confirm or adjust the opportunity size.</p>")
            html_parts.append("<table><tr><th>#</th><th>Key Driver</th><th>Impact Score</th><th>Data Request for Diligence</th></tr>")
            for r in diligence_rows:
                lbl = r.get("driver_label", "")
                corr = r.get("corr", 0)
                req = r.get("diligence_request", "")
                html_parts.append(f"<tr><td>{r.get('rank', '')}</td><td>{lbl}</td><td>{corr:.2f}</td><td>{req}</td></tr>")
            html_parts.append("</table>")

    # 6. Strategic Priority Matrix (board-ready sensitivity)
    priority_path = os.path.join(outdir, "strategic_priority_matrix.csv")
    df_priority = _read_csv_if_exists(priority_path)
    html_parts.append("<h2 id='sec-priority'>6. Strategic Priority Matrix</h2>")
    html_parts.append("<p class='section-desc'><strong>Why this matters:</strong> Not all improvement opportunities are equal. This matrix ranks each driver by both financial impact and implementation complexity, so the operating team can sequence interventions for maximum early wins. Tier 1 = high-impact strategic fixes; Tier 2 = efficiency plays; Tier 3 = monitor and address later.</p>")
    if df_priority is not None and len(df_priority) > 0:
        priority_renames = {c: c.replace("_", " ").title() for c in df_priority.columns if "_" in c}
        html_parts.append(df_priority.rename(columns=priority_renames).to_html(index=False, classes="money-table"))
    elif df_sens is not None and len(df_sens) > 0:
        html_parts.append("<p class='section-desc'><em>Priority matrix not available; showing sensitivity rankings.</em></p>")
        sens_rows = []
        for _, r in df_sens.head(12).iterrows():
            lbl = r.get("driver_label", r.get("driver", str(r.get("driver", ""))))
            corr = float(r.get("corr", 0))
            sens_rows.append(f"<tr><td>{lbl}</td><td>{corr:.2f}</td></tr>")
        html_parts.append("<table><tr><th>Driver</th><th>Impact Correlation</th></tr>")
        html_parts.append("".join(sens_rows))
        html_parts.append("</table>")
    else:
        html_parts.append("<p><em>sensitivity.csv not found.</em></p>")

    # 7. Driver Trees (if available) — payer × root_cause rollup
    if dt_drag is not None or st_drag is not None or up_drag is not None:
        html_parts.append("<h2 id='sec-drivers'>7. Driver Trees</h2>")
        html_parts.append("<p class='section-desc'><strong>Why this matters:</strong> This is the audit trail. It breaks every dollar of drag down by payer and root cause, so the deal team can pinpoint exactly which payer relationships and which denial categories to address first. Essential for diligence documentation.</p>")

        if dt_drag is not None:
            html_parts.append("<h3>Top Denial Drivers by Payer and Root Cause</h3>")
            html_parts.append("<p class='section-desc'>Ranked by dollar impact. Positive values indicate the target hospital underperforms the benchmark.</p>")
            html_parts.append(_img_tag(denial_chart_path, "Denial Drivers Chart"))
            top_n = 8
            top_df = dt_drag.nlargest(top_n, "drag_mean_denial_writeoff")
            money_cols = ["drag_mean_denial_writeoff", "drag_mean_denial_rework_cost"]
            display_cols = ["payer", "root_cause", "drag_mean_denial_writeoff", "drag_mean_denial_rework_cost"]
            display_cols = [c for c in display_cols if c in top_df.columns]
            top_fmt = _format_money_cols(top_df, money_cols)
            html_parts.append(top_fmt[display_cols].rename(columns={
                "payer": "Payer",
                "root_cause": "Root Cause",
                "drag_mean_denial_writeoff": "Write-Off Drag ($)",
                "drag_mean_denial_rework_cost": "Rework Cost ($)",
            }).to_html(index=False, classes=None))
            html_parts.append("""<details><summary>Show full breakdown by payer and root cause</summary>""")
            full_fmt = _format_money_cols(dt_drag, [c for c in money_cols if c in dt_drag.columns])
            col_renames = {
                "payer": "Payer", "root_cause": "Root Cause",
                "drag_mean_denial_writeoff": "Write-Off Drag ($)",
                "drag_mean_denial_rework_cost": "Rework Cost ($)",
            }
            full_renamed = full_fmt.rename(columns={k: v for k, v in col_renames.items() if k in full_fmt.columns})
            html_parts.append(full_renamed.to_html(index=False, classes=None))
            html_parts.append("</details>")

        if up_drag is not None:
            html_parts.append("<h3>Underpayment Leakage by Payer</h3>")
            html_parts.append("<p class='section-desc'>Annual revenue lost to underpayments (amounts paid below contracted rates) and the cost to identify and recover them. Self-pay excluded.</p>")
            html_parts.append(_img_tag(underpay_chart_path, "Underpayments Chart"))
            up = up_drag[up_drag["payer"] != "SelfPay"] if "payer" in up_drag.columns else up_drag.copy()
            if "metric" in up.columns and "drag_mean_value" in up.columns:
                leak = up[up["metric"] == "underpay_leakage"][["payer", "drag_mean_value"]].rename(columns={"drag_mean_value": "Leakage"})
                cost = up[up["metric"] == "underpay_cost"][["payer", "drag_mean_value"]].rename(columns={"drag_mean_value": "Follow-Up Cost"})
                up_wide = leak.merge(cost, on="payer", how="outer").fillna(0)
                up_wide["Total"] = up_wide["Leakage"] + up_wide["Follow-Up Cost"]
                up_wide = up_wide.sort_values("Total", ascending=False)
                up_wide = up_wide.rename(columns={"payer": "Payer"})
                up_fmt = _format_money_cols(up_wide, ["Leakage", "Follow-Up Cost", "Total"])
            else:
                money_cols = [c for c in up.columns if "drag" in c.lower() or "value" in c.lower()]
                up_fmt = _format_money_cols(up, money_cols if money_cols else list(up.select_dtypes(include=["number"]).columns))
            html_parts.append(up_fmt.to_html(index=False, classes="money-table"))

        if st_drag is not None:
            html_parts.append("<h3>Appeal Stage Breakdown by Payer</h3>")
            money_cols = [c for c in st_drag.columns if "drag_" in c or "mean_" in c]
            st_fmt = _format_money_cols(st_drag, money_cols)
            st_col_renames = {"payer": "Payer", "stage": "Appeal Stage"}
            for c in st_fmt.columns:
                if c.startswith("drag_") or c.startswith("mean_"):
                    st_col_renames[c] = c.replace("drag_mean_", "").replace("drag_", "").replace("_", " ").title() + " ($)"
            st_renamed = st_fmt.rename(columns={k: v for k, v in st_col_renames.items() if k in st_fmt.columns})
            html_parts.append(st_renamed.to_html(index=False, classes=None))

    # 7b. Data confidence (if calibration was used)
    if df_conf is not None and len(df_conf) > 0:
        html_parts.append("<h2>7b. Data Confidence Assessment</h2>")
        html_parts.append("<p class='section-desc'><strong>Why this matters:</strong> Model outputs are only as reliable as the inputs. This table shows how much real data backs each payer's assumptions. Low confidence signals where additional diligence is needed before underwriting.</p>")
        conf_renames = {c: c.replace("_", " ").title() for c in df_conf.columns if "_" in c}
        html_parts.append(df_conf.rename(columns=conf_renames).to_html(index=False, classes=None))

    # 8. Value Attribution (if run) — OAT: $ uplift if each bucket were fixed to benchmark
    if attribution_results is not None:
        html_parts.append("<h2>8. Value Attribution</h2>")
        html_parts.append("<p class='section-desc'><strong>Why this matters:</strong> Attribution isolates how much each operational driver contributes to total drag. OAT (one-at-a-time) shows the $ recovered if that single bucket were moved to benchmark — useful for prioritizing 100-day-plan actions.</p>")
        oat_df = attribution_results.get("oat")
        if oat_df is not None and len(oat_df) > 0:
            html_parts.append("<h3>Individual Driver Uplift</h3>")
            oat_fmt = _format_money_cols(oat_df, ["remaining_drag", "uplift_oat"])
            html_parts.append(oat_fmt.rename(columns={"remaining_drag": "Remaining Drag", "uplift_oat": "Uplift Opportunity"}).to_html(index=False, classes=None))
        html_parts.append("<h3>Attribution Breakdown</h3>")
        html_parts.append(_img_tag(tornado_path, "Attribution Tornado"))

    # 8b. Action Plan (top 5 OAT uplifts + playbook)
    if attribution_results is not None and playbook_path and os.path.exists(playbook_path):
        oat_df = attribution_results.get("oat")
        if oat_df is not None and len(oat_df) > 0:
            try:
                with open(playbook_path) as f:
                    playbook = yaml.safe_load(f) or {}
            except Exception:
                playbook = {}
            top5 = oat_df.head(5)
            html_parts.append("<h2>8b. Action Plan</h2>")
            html_parts.append("<p class='section-desc'><strong>Why this matters:</strong> Connects financial analysis to specific operational playbooks. Each row maps a top value driver to the intervention that captures it, the KPI to track, and the data needed to validate it.</p>")
            html_parts.append("<table><tr><th>Driver</th><th>Dollar Impact</th><th>Operational Lever</th><th>Tracking KPI</th><th>Diligence Data Needed</th></tr>")
            for _, r in top5.iterrows():
                bucket = str(r.get("bucket", ""))
                contrib = float(r.get("uplift_oat", 0))
                pk = playbook.get(bucket, {}) or {}
                lever = pk.get("lever", "") or ""
                kpi = pk.get("kpi", "") or ""
                diligence = pk.get("diligence", "") or ""
                contrib_str = pretty_money(contrib)
                html_parts.append(f"<tr><td>{bucket}</td><td>{contrib_str}</td><td>{lever}</td><td>{kpi}</td><td>{diligence}</td></tr>")
            html_parts.append("</table>")

    # 9. Stress Tests (if available)
    if df_stress is not None:
        html_parts.append("<h2>9. Stress Tests</h2>")
        html_parts.append("<p class='section-desc'><strong>Why this matters:</strong> Stress tests show how sensitive the opportunity is to adverse scenarios (payer policy changes, denial rate spikes, staffing disruption). Essential for sizing downside risk in the investment memo.</p>")
        money_cols = [c for c in df_stress.columns if "drag" in c.lower() or "ebitda" in c.lower() or "ev" in c.lower()]
        stress_fmt = _format_money_cols(df_stress, money_cols)
        stress_renames = {c: c.replace("_", " ").title() for c in stress_fmt.columns if "_" in c}
        stress_renames.update({"scenario": "Scenario", "ebitda_drag_mean": "EBITDA Drag (Mean)", "ebitda_drag_p10": "EBITDA Drag (P10)", "ebitda_drag_p90": "EBITDA Drag (P90)"})
        stress_renamed = stress_fmt.rename(columns={k: v for k, v in stress_renames.items() if k in stress_fmt.columns})
        html_parts.append(stress_renamed.to_html(index=False, classes=None))

    # 10. Value Creation Plan — Operating Partner format
    hundred_day_path = os.path.join(outdir, "hundred_day_plan.csv")
    df_100 = _read_csv_if_exists(hundred_day_path)
    if df_100 is not None and len(df_100) > 0:
        html_parts.append("<h2>10. Value Creation Plan</h2>")
        html_parts.append("<p class='section-desc'><strong>Why this matters:</strong> This is the operating partner's execution roadmap. Workstreams are ranked by EBITDA impact and implementation difficulty, with specific 100-day milestones for board-level tracking.</p>")
        html_parts.append("<table class='priority-table'><tr><th>Priority</th><th>Workstream</th><th>EBITDA Impact ($)</th><th>Difficulty</th><th>100-Day Milestone</th></tr>")
        for i, (_, r) in enumerate(df_100.head(10).iterrows()):
            prio = i + 1
            p_class = "p1" if prio <= 3 else ("p2" if prio <= 6 else "p3")
            name = str(r.get("name", ""))
            ebitda = float(r.get("ebitda_uplift_mean", 0))
            phase = str(r.get("phase", ""))
            kpi = str(r.get("kpi", "")) or phase
            # Difficulty from phase: Days 1–30=Low, 31–60=Med, 61+=High
            if "1–30" in phase:
                diff, diff_class = "⬤ ◯ ◯ (Low)", "diff-low"
            elif "31–60" in phase or "61–90" in phase:
                diff, diff_class = "⬤ ⬤ ◯ (Med)", "diff-med"
            else:
                diff, diff_class = "⬤ ⬤ ⬤ (High)", "diff-high"
            ebitda_str = pretty_money(ebitda) if ebitda > 0 else f"({pretty_money(-ebitda)})"
            html_parts.append(f"<tr class='{p_class}'><td>P{prio}</td><td>{name}</td><td class='num'>{ebitda_str}</td><td><span class='diff-dots {diff_class}'>{diff}</span></td><td>{kpi}</td></tr>")
        html_parts.append("</table>")

    # Risk Register
    html_parts.append(RISK_REGISTER_HTML)

    # 10b. Model Limitations and Data Reality
    html_parts.append(MODEL_LIMITATIONS_HTML)

    # 10c. Key Model Assumptions
    html_parts.append(KEY_ASSUMPTIONS_HTML)

    # Post-Close KPI Tracking Dashboard
    if df_summary is not None and "ebitda_drag" in df_summary.index:
        _pc_denial_wo = float(df_summary.loc["drag_denial_writeoff", "mean"]) if "drag_denial_writeoff" in df_summary.index else 0
        _pc_underpay = float(df_summary.loc["drag_underpay_leakage", "mean"]) if "drag_underpay_leakage" in df_summary.index else 0
        _pc_dar = float(df_summary.loc["drag_dar_total", "mean"]) if "drag_dar_total" in df_summary.index else 0
        _pc_ebitda = float(df_summary.loc["ebitda_drag", "mean"])

        _pc_actual_idr = "—"
        _pc_bench_idr = "—"
        _pc_actual_fwr = "—"
        _pc_bench_fwr = "—"
        _pc_actual_dar = "—"
        _pc_bench_dar = "—"
        if actual_cfg_load and benchmark_cfg_load:
            _a_p = _extract_payer_params(actual_cfg_load)
            _b_p = _extract_payer_params(benchmark_cfg_load)
            _a_rev = actual_cfg_load.get("payers") or {}
            idr_weighted_a, idr_weighted_b = 0, 0
            fwr_weighted_a, fwr_weighted_b = 0, 0
            dar_weighted_a, dar_weighted_b = 0, 0
            total_share = 0
            for pyr in ("Medicare", "Medicaid", "Commercial"):
                share = _a_rev.get(pyr, {}).get("revenue_share", 0)
                if pyr in _a_p:
                    idr_weighted_a += _a_p[pyr].get("idr", 0) * share
                    fwr_weighted_a += _a_p[pyr].get("fwr", 0) * share
                    dar_weighted_a += _a_p[pyr].get("dar", 0) * share
                if pyr in _b_p:
                    idr_weighted_b += _b_p[pyr].get("idr", 0) * share
                    fwr_weighted_b += _b_p[pyr].get("fwr", 0) * share
                    dar_weighted_b += _b_p[pyr].get("dar", 0) * share
                total_share += share
            if total_share > 0:
                _pc_actual_idr = f"{idr_weighted_a/total_share*100:.1f}%"
                _pc_bench_idr = f"{idr_weighted_b/total_share*100:.1f}%"
                _pc_actual_fwr = f"{fwr_weighted_a/total_share*100:.1f}%"
                _pc_bench_fwr = f"{fwr_weighted_b/total_share*100:.1f}%"
                _pc_actual_dar = f"{dar_weighted_a/total_share:.0f} days"
                _pc_bench_dar = f"{dar_weighted_b/total_share:.0f} days"

        html_parts.append(f"""
    <h2 id="sec-post-close">Post-Close KPI Tracking</h2>
    <p class='section-desc'><strong>Why this matters:</strong> After closing, the operating partner needs a monthly dashboard to track whether the RCM improvements are materializing. These are the KPIs to monitor, with current baselines and target values. Report these to the board monthly starting Day 1.</p>

    <div class="tracker-grid">
      <div class="tracker-item">
        <div class="tk-label">Initial Denial Rate (Blended)</div>
        <div class="tk-target">Target: {_pc_bench_idr}</div>
        <div class="tk-current">Current: {_pc_actual_idr}</div>
        <div class="tk-bar"><div class="tk-bar-fill" style="width: 35%;"></div></div>
      </div>
      <div class="tracker-item">
        <div class="tk-label">Final Write-Off Rate (Blended)</div>
        <div class="tk-target">Target: {_pc_bench_fwr}</div>
        <div class="tk-current">Current: {_pc_actual_fwr}</div>
        <div class="tk-bar"><div class="tk-bar-fill" style="width: 30%;"></div></div>
      </div>
      <div class="tracker-item">
        <div class="tk-label">Days in A/R (Blended)</div>
        <div class="tk-target">Target: {_pc_bench_dar}</div>
        <div class="tk-current">Current: {_pc_actual_dar}</div>
        <div class="tk-bar"><div class="tk-bar-fill" style="width: 40%;"></div></div>
      </div>
      <div class="tracker-item">
        <div class="tk-label">EBITDA Captured (Cumulative)</div>
        <div class="tk-target">Year 1 Target: {pretty_money(_pc_ebitda * 0.55)}</div>
        <div class="tk-current">Full Opportunity: {pretty_money(_pc_ebitda)}</div>
        <div class="tk-bar"><div class="tk-bar-fill" style="width: 0%;"></div></div>
      </div>
      <div class="tracker-item">
        <div class="tk-label">Denial Write-Off Reduction</div>
        <div class="tk-target">Target Savings: {pretty_money(_pc_denial_wo * 0.55)}/yr</div>
        <div class="tk-current">Baseline Leakage: {pretty_money(_pc_denial_wo)}/yr</div>
        <div class="tk-bar"><div class="tk-bar-fill" style="width: 0%;"></div></div>
      </div>
      <div class="tracker-item">
        <div class="tk-label">Underpayment Recovery</div>
        <div class="tk-target">Target Recovery: {pretty_money(_pc_underpay * 0.50)}/yr</div>
        <div class="tk-current">Baseline Leakage: {pretty_money(_pc_underpay)}/yr</div>
        <div class="tk-bar"><div class="tk-bar-fill" style="width: 0%;"></div></div>
      </div>
    </div>

    <div class="card" style="margin-top: 0.75rem;">
      <h3>Monthly Board Reporting Cadence</h3>
      <table>
        <tr><th>Reporting Interval</th><th>KPIs Tracked</th><th>Owner</th></tr>
        <tr><td>Weekly (Internal)</td><td>Denial volumes, A/R aging, appeal queue depth</td><td>RCM Director</td></tr>
        <tr><td>Monthly (Board)</td><td>IDR, FWR, Days in A/R, EBITDA captured (cumulative)</td><td>CFO / Operating Partner</td></tr>
        <tr><td>Quarterly (IC Update)</td><td>Total EBITDA capture vs plan, payer-level trends, initiative milestones</td><td>Deal Lead</td></tr>
      </table>
    </div>""")

    # IC Memo Language
    if df_summary is not None and "ebitda_drag" in df_summary.index:
        _ic_ebitda = float(df_summary.loc["ebitda_drag", "mean"])
        _ic_p10 = float(df_summary.loc["ebitda_drag", "p10"])
        _ic_p90 = float(df_summary.loc["ebitda_drag", "p90"])
        _ic_ev = _ic_ebitda * ev_multiple
        _ic_ev_p10 = _ic_p10 * ev_multiple
        _ic_ev_p90 = _ic_p90 * ev_multiple
        _ic_denial = float(df_summary.loc["drag_denial_writeoff", "mean"]) if "drag_denial_writeoff" in df_summary.index else 0
        _ic_underpay = float(df_summary.loc["drag_underpay_leakage", "mean"]) if "drag_underpay_leakage" in df_summary.index else 0
        _ic_credit_50 = _ic_ebitda * 0.50
        _ic_credit_ev = _ic_credit_50 * ev_multiple

        html_parts.append(f"""
    <h2 id="sec-ic-memo">Investment Committee Language</h2>
    <p class='section-desc'><strong>Why this matters:</strong> These are ready-to-use paragraphs for the investment committee memorandum. Copy directly into the IC deck under the "Revenue Cycle Opportunity" section. Edit as needed to match your firm's format and voice.</p>

    <div class="memo-block" id="memo-opportunity">
      <button class="memo-copy-btn" onclick="navigator.clipboard.writeText(document.getElementById('memo-opportunity').innerText.replace('IC MEMO','').replace('Copy','').trim())">Copy</button>
      <strong>RCM Opportunity Summary</strong><br><br>
      Our diligence analysis, based on a {n_sims:,}-iteration Monte Carlo simulation benchmarked against HFMA/AHA top-quartile performance standards, identifies a {pretty_money(_ic_ebitda)} annual EBITDA recovery opportunity at {hospital_display}. At a {ev_multiple}x EBITDA multiple, this translates to {pretty_money(_ic_ev)} in enterprise value creation (range: {pretty_money(_ic_ev_p10)} conservative to {pretty_money(_ic_ev_p90)} stress case). The primary value drivers are denial write-off reduction ({pretty_money(_ic_denial)} annually) and underpayment recovery ({pretty_money(_ic_underpay)} annually).
    </div>

    <div class="memo-block" id="memo-underwriting">
      <button class="memo-copy-btn" onclick="navigator.clipboard.writeText(document.getElementById('memo-underwriting').innerText.replace('IC MEMO','').replace('Copy','').trim())">Copy</button>
      <strong>Underwriting Recommendation</strong><br><br>
      We recommend underwriting {pretty_money(_ic_credit_50)} of annual EBITDA uplift (50% credit on the modeled opportunity), representing {pretty_money(_ic_credit_ev)} in enterprise value at {ev_multiple}x. {"This credit level reflects a calibrated analysis using actual claims and denial data provided during diligence. Confidence in the modeled rates is supported by data quality validation. We recommend maintaining this credit level and updating as additional trailing-month data becomes available." if data_confidence_path and os.path.exists(data_confidence_path) else "This credit level is appropriate given that the analysis is benchmark-based and has not yet been calibrated with actual claims data. Upon receipt of trailing-twelve-month denial and A/R data during confirmatory diligence, we expect to refine this estimate and potentially increase the credit to 60-70% if data supports the modeled rates."}
    </div>

    <div class="memo-block" id="memo-execution">
      <button class="memo-copy-btn" onclick="navigator.clipboard.writeText(document.getElementById('memo-execution').innerText.replace('IC MEMO','').replace('Copy','').trim())">Copy</button>
      <strong>Execution Plan</strong><br><br>
      The value creation plan targets 55% capture ({pretty_money(_ic_ebitda * 0.55)}) within the first 12 months through a combination of quick wins (coding audits, prior-auth automation, A/R acceleration) and structural improvements (CDI program buildout, payer contract renegotiation). Full run-rate of 95% ({pretty_money(_ic_ebitda * 0.95)}) is achievable by month 24 with dedicated operating partner oversight and estimated total investment of {pretty_money(_ic_ebitda * 0.22)} in technology, staffing, and advisory support.
    </div>

    <div class="memo-block" id="memo-risks">
      <button class="memo-copy-btn" onclick="navigator.clipboard.writeText(document.getElementById('memo-risks').innerText.replace('IC MEMO','').replace('Copy','').trim())">Copy</button>
      <strong>Key Risks and Mitigants</strong><br><br>
      Principal risks include payer policy changes that could increase denial rates beyond modeled assumptions, potential staff turnover during the transformation, and the possibility that actual denial data reveals a smaller opportunity than benchmark-based estimates suggest. These risks are mitigated by conservative underwriting (50% credit), a phased implementation approach that generates quick wins before committing to larger investments, and stress testing that shows the opportunity remains material even under adverse scenarios (P90 EBITDA drag of {pretty_money(_ic_p90)}).
    </div>
    """)

    # 11. Executive Conclusion & Next Steps
    if df_summary is not None and "ebitda_drag" in df_summary.index:
        e_c = float(df_summary.loc["ebitda_drag", "mean"])
        e_p10_c = float(df_summary.loc["ebitda_drag", "p10"])
        e_p90_c = float(df_summary.loc["ebitda_drag", "p90"])
        ev_str_final = pretty_money(e_c * ev_multiple)
        ev_p10_str_final = pretty_money(e_p10_c * ev_multiple)
        ev_p90_str_final = pretty_money(e_p90_c * ev_multiple)
        html_parts.append(f"""
    <h2 id="sec-conclusion">11. Conclusion and Recommended Next Steps</h2>
    <div class="highlight">
      <p><strong>Bottom Line:</strong> Closing the gap between current RCM performance and best-practice benchmarks represents a <strong>{ev_str_final}</strong> enterprise value opportunity at mean (range: {ev_p10_str_final} to {ev_p90_str_final}).</p>
      <p><strong>Recommended Next Steps:</strong></p>
      <ol style="margin: 0.5rem 0 0 1.5rem; font-size: 0.95rem;">
        <li><strong>Validate inputs:</strong> Request payer-level denial and A/R data during confirmatory diligence to calibrate the model against actuals.</li>
        <li><strong>Stress-test assumptions:</strong> Use the Scenario Explorer above to adjust the EBITDA multiple, WACC, and revenue inputs and see how the opportunity range shifts.</li>
        <li><strong>Build the operating plan:</strong> Run the full report for initiative rankings, stress tests, and a prioritized 100-day value creation plan.</li>
      </ol>
      <p style="margin-top: 0.75rem;"><strong>Important:</strong> All outputs are model-based estimates derived from the configuration inputs and published benchmarks. Results should be validated with actual claims data before underwriting.</p>
    </div>""")
    else:
        html_parts.append("""
    <h2 id="sec-conclusion">11. Conclusion and Recommended Next Steps</h2>
    <div class="highlight">
      <p><strong>Bottom Line:</strong> Run the analysis with valid configuration inputs to size the deal opportunity.</p>
      <p><strong>Next steps:</strong> Provide actual hospital data to calibrate the model, then use the Scenario Explorer and full report for complete diligence intelligence.</p>
    </div>""")

    # Glossary of Terms
    html_parts.append(GLOSSARY_HTML)

    html_parts.append(SCENARIO_EXPLORER_JS)
    # Data Sources & Currency (boss-ready, citable)
    html_parts.append('<h2 id="data-sources">Data Sources & Currency</h2>')
    html_parts.append("<div class='card'><p><strong>Report generated:</strong> " + ts + "</p>")
    if actual_config_path:
        html_parts.append(f"<p><strong>Actual config:</strong> <code>{html_escape(actual_config_path)}</code></p>")
    if benchmark_config_path:
        html_parts.append(f"<p><strong>Benchmark config:</strong> <code>{html_escape(benchmark_config_path)}</code></p>")
    html_parts.append("""<p><strong>Benchmark source:</strong> Top-quartile peers, HFMA MAP Keys, FY24. Configs drive Monte Carlo inputs; update when claims/diligence data refreshes.</p>
    <p><strong>Industry references (citable):</strong></p>
    <ul style="margin: 0.5rem 0; padding-left: 1.5rem; font-size: 0.9rem;">
      <li><strong>HFMA MAP / Denial definitions:</strong> <a href="https://www.hfma.org/guidance/standardizing-denial-metrics-revenue-cycle-benchmarking-process-improvement/" target="_blank" rel="noopener">Claim Integrity Task Force</a></li>
      <li><strong>AHA:</strong> Commercial 13.9%, MA 15.7% IDR — <a href="https://www.aha.org/aha-center-health-innovation-market-scan/2024-04-02-payer-denial-tactics-how-confront-20-billion-problem" target="_blank" rel="noopener">Payer Denial Tactics</a></li>
      <li><strong>Kodiak (HealthLeaders):</strong> FWR 2.8% avg / 2.2% top-10; A/R 56.9 avg / 43.6 top-10 — <a href="https://www.healthleadersmedia.com/revenue-cycle/quick-tips-improve-rev-cycle-performance-against-8-kpis" target="_blank" rel="noopener">8 KPIs</a></li>
      <li><strong>HFMA/AKASA:</strong> Cost to collect ~3.68% — <a href="https://akasa.com/press/survey-cost-to-collect-lower-with-automation" target="_blank" rel="noopener">Survey</a></li>
      <li><strong>Fierce Healthcare:</strong> Medicaid/FFS denial ranges — <a href="https://www.fiercehealthcare.com/providers/providers-wasted-106b-2022-overturning-claims-denials-survey-finds" target="_blank" rel="noopener">Providers wasted $10.6B</a></li>
      <li><strong>PMC:</strong> A/R &gt;90 days best practice &lt;15% — <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC11219169/" target="_blank" rel="noopener">Revenue Cycle Management</a></li>
    </ul>
    <p class='section-desc'>See <code>BENCHMARK_SOURCES.md</code> in project root for full benchmark pack.</p></div>""")
    html_parts.append('<div class="seal-audit">Proprietary Stochastic Model | Built for Confirmatory Due Diligence | Confidential</div>')

    # Back to top button + nav highlight
    html_parts.append(BACK_TO_TOP_HTML)

    html_parts.append("</div></body></html>")
    html = "\n".join(html_parts)

    # UI-1 polish: right-align numeric cells in every table (pandas to_html
    # output and hand-written tables alike). Idempotent, safe to re-apply.
    from ..ui._html_polish import polish_tables_in_html
    html = polish_tables_in_html(html)

    out_path = os.path.join(outdir, "report.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path
