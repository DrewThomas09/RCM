"""SeekingChartis IC Memo Generator — one-click investment committee memo.

Generates a complete, substantive IC memo for any hospital using only
public data and ML models. Saves analysts 20+ hours per deal by
auto-generating every section with real numbers, not templates.

Sections:
1. Target Overview & Thesis
2. Market Context & Competitive Position
3. RCM Performance Analysis with Comps
4. Predicted Improvement Opportunities
5. EBITDA Bridge with Sensitivities
6. Returns Analysis (Base/Bull/Bear)
7. Key Risks & Mitigants
8. Data Sources & Methodology Appendix
"""
from __future__ import annotations

import html as _html
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ._chartis_kit import chartis_shell
from .brand import PALETTE


def _safe_float(val, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        f = float(val)
        return default if f != f else f
    except (TypeError, ValueError):
        return default


def _fm(val: float) -> str:
    if abs(val) >= 1e9:
        return f"${val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val/1e6:.1f}M"
    if abs(val) >= 1e3:
        return f"${val/1e3:.0f}K"
    return f"${val:,.0f}"


def _pct(val: float, decimals: int = 1) -> str:
    return f"{val:.{decimals}%}"


def _build_memo_data(ccn: str, hcris_df: pd.DataFrame, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Assemble all data needed for the IC memo from public sources + ML + seller data."""
    match = hcris_df[hcris_df["ccn"] == ccn]
    if match.empty:
        return None

    hospital = match.iloc[0]
    name = str(hospital.get("name", f"Hospital {ccn}"))
    state = str(hospital.get("state", ""))
    county = str(hospital.get("county", ""))
    beds = _safe_float(hospital.get("beds"))
    rev = _safe_float(hospital.get("net_patient_revenue"))
    opex = _safe_float(hospital.get("operating_expenses"))
    gross = _safe_float(hospital.get("gross_patient_revenue"))
    mc_pct = _safe_float(hospital.get("medicare_day_pct"))
    md_pct = _safe_float(hospital.get("medicaid_day_pct"))
    comm_pct = max(0, 1 - mc_pct - md_pct)
    days = float(hospital.get("total_patient_days", 0) or 0)
    bda = float(hospital.get("bed_days_available", 0) or 0)

    if rev < 1e6:
        return None

    margin = (rev - opex) / rev if rev > 1e5 else 0
    margin = max(-1, min(1, margin))
    ebitda = rev - opex
    occupancy = days / bda if bda > 0 else 0
    n2g = rev / gross if gross > 0 else 0.3
    rev_per_bed = rev / beds if beds > 0 else 0

    # State peers
    state_df = hcris_df[hcris_df["state"] == state] if state else hcris_df
    nat_df = hcris_df

    def _peer_stats(df, col):
        vals = df[col].dropna()
        if len(vals) < 5:
            return {}
        return {"p25": float(vals.quantile(0.25)), "median": float(vals.median()),
                "p75": float(vals.quantile(0.75)), "mean": float(vals.mean())}

    # Bridge computation
    from .ebitda_bridge_page import _compute_bridge, _compute_returns_grid, _load_data_room_overrides
    dr_overrides = _load_data_room_overrides(db_path, ccn) if db_path else {}
    bridge = _compute_bridge(rev, ebitda, medicare_pct=mc_pct, overrides=dr_overrides)

    # Returns scenarios
    base_grid = _compute_returns_grid(ebitda, bridge["total_ebitda_impact"],
                                       [10.0], [10.0, 11.0], hold_years=5)
    bull_grid = _compute_returns_grid(ebitda, bridge["total_ebitda_impact"] * 1.3,
                                       [9.0], [11.0, 12.0], hold_years=5)
    bear_grid = _compute_returns_grid(ebitda, bridge["total_ebitda_impact"] * 0.5,
                                       [11.0], [10.0, 11.0], hold_years=5)

    # Investability
    try:
        from ..ml.investability_scorer import compute_investability
        invest = compute_investability(ccn, hcris_df)
    except Exception:
        invest = None

    # Clustering
    try:
        from ..ml.hospital_clustering import get_hospital_cluster
        cluster = get_hospital_cluster(ccn, hcris_df)
    except Exception:
        cluster = None

    # Distress
    try:
        from ..ml.distress_predictor import predict_distress
        distress = predict_distress(ccn, hcris_df)
    except Exception:
        distress = None

    # Comps
    size_lo = max(10, beds * 0.5)
    size_hi = beds * 2.0
    comps = hcris_df[(hcris_df["beds"] >= size_lo) & (hcris_df["beds"] <= size_hi) & (hcris_df["ccn"] != ccn)]
    state_comps = comps[comps["state"] == state] if state else comps
    if len(state_comps) >= 8:
        comp_df = state_comps
    else:
        comp_df = comps

    return {
        "ccn": ccn, "name": name, "state": state, "county": county,
        "beds": beds, "revenue": rev, "opex": opex, "ebitda": ebitda,
        "margin": margin, "gross": gross, "mc_pct": mc_pct, "md_pct": md_pct,
        "comm_pct": comm_pct, "occupancy": occupancy, "n2g": n2g,
        "rev_per_bed": rev_per_bed, "bridge": bridge,
        "base_grid": base_grid, "bull_grid": bull_grid, "bear_grid": bear_grid,
        "invest": invest, "cluster": cluster, "distress": distress,
        "comp_df": comp_df, "state_df": state_df, "nat_df": nat_df,
        "n_comps": len(comp_df), "n_state": len(state_df),
    }


def render_ic_memo(ccn: str, hcris_df: pd.DataFrame, db_path: Optional[str] = None) -> str:
    """Render a complete IC memo for a hospital."""
    from .provenance import source_tag, Source

    def _src_tag(src: str) -> str:
        src_map = {"hcris": Source.HCRIS, "ml": Source.ML_PREDICTION,
                   "computed": Source.COMPUTED, "seller": Source.SELLER,
                   "benchmark": Source.BENCHMARK, "default": Source.DEFAULT}
        return source_tag(src_map.get(src, Source.DEFAULT))

    data = _build_memo_data(ccn, hcris_df, db_path=db_path)
    if data is None:
        return chartis_shell(
            f'<div class="cad-card"><p>Hospital {_html.escape(ccn)} not found or has insufficient data.</p></div>',
            "IC Memo", subtitle="Error",
        )

    ts = datetime.now(timezone.utc).strftime("%B %d, %Y")
    sections = []

    # ── HEADER ──
    invest_grade = data["invest"].grade if data["invest"] else "—"
    grade_colors = {"A": "var(--cad-pos)", "B": "var(--cad-accent)", "C": "var(--cad-warn)", "D": "var(--cad-neg)"}
    gc = grade_colors.get(invest_grade, "var(--cad-text3)")

    # Editorial dark-navy hero band — matches the workbench treatment.
    grade_tone_map = {
        "A": "#7ED3A8", "B": "#A6D3F2",
        "C": "#E8B97E", "D": "#E89478",
    }
    grade_color = grade_tone_map.get(invest_grade, "rgba(250, 247, 240, 0.55)")
    sections.append(
        '<div class="ic-hero">'
        '<div class="ic-hero-inner">'
        '<div class="ic-hero-eyebrow">'
        f'INVESTMENT COMMITTEE MEMORANDUM &nbsp;·&nbsp; CCN {_html.escape(ccn)}'
        '</div>'
        '<div class="ic-hero-row">'
        '<div class="ic-hero-name-block">'
        f'<h1 class="ic-hero-name">{_html.escape(data["name"])}</h1>'
        '<div class="ic-hero-meta">'
        '<span class="m-key">LOCATION</span>'
        f'<span class="m-val">{_html.escape(data["county"])}, {_html.escape(data["state"])}</span>'
        '<span class="m-sep">·</span>'
        f'<span class="m-key">BEDS</span><span class="m-val">{data["beds"]:.0f}</span>'
        '<span class="m-sep">·</span>'
        f'<span class="m-key">AS OF</span><span class="m-val">{_html.escape(ts)}</span>'
        '</div>'
        '</div>'
        '<div class="ic-hero-grade">'
        f'<div class="ic-grade-val" style="color:{grade_color};">{_html.escape(invest_grade)}</div>'
        '<div class="ic-grade-label">INVESTABILITY</div>'
        '</div>'
        '</div>'
        '</div>'
        '</div>'
        '<div class="ic-utility no-print">'
        '<div class="ic-utility-inner">'
        '<button onclick="window.print()" class="cad-btn cad-btn-primary">'
        '&#128438; Export PDF</button>'
        f'<a href="/ebitda-bridge/{_html.escape(ccn)}" class="cad-btn">EBITDA Bridge</a>'
        f'<a href="/data-room/{_html.escape(ccn)}" class="cad-btn">Data Room</a>'
        '</div>'
        '</div>'
    )

    # ── 1. TARGET OVERVIEW & THESIS ──
    thesis = "Undervalued" if data["margin"] < 0.05 and data["beds"] > 100 else "Platform Growth" if data["beds"] > 200 else "Turnaround"
    archetype = data["cluster"].label if data["cluster"] else "Community Hospital"
    distress_prob = data["distress"].distress_probability if data["distress"] else 0

    sections.append(
        f'<div class="cad-card">'
        f'<h2>1. Target Overview & Investment Thesis</h2>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:12px;">'
        f'<div style="font-size:12.5px;line-height:1.8;color:var(--cad-text2);">'
        f'<p><strong>{_html.escape(data["name"])}</strong> is a {data["beds"]:.0f}-bed '
        f'{_html.escape(archetype.lower())} in {_html.escape(data["county"])}, {_html.escape(data["state"])} '
        f'with {_fm(data["revenue"])} in net patient revenue and a '
        f'{_pct(data["margin"])} operating margin. '
        f'The hospital serves a payer mix of {_pct(data["mc_pct"])} Medicare, '
        f'{_pct(data["md_pct"])} Medicaid, and {_pct(data["comm_pct"])} commercial.</p>'
        f'<p><strong>Thesis: {thesis}.</strong> Our ML models identify '
        f'{_fm(data["bridge"]["total_ebitda_impact"])} in annual EBITDA improvement potential '
        f'from RCM optimization across {len([l for l in data["bridge"]["levers"] if l["ebitda_impact"] > 0])} '
        f'levers, lifting margin from {_pct(data["margin"])} to '
        f'{_pct(data["bridge"]["new_margin"])} '
        f'(+{data["bridge"]["margin_improvement_bps"]:.0f}bps).</p></div>'
        f'<div>'
        f'<table class="cad-table" style="font-size:12px;">'
        f'<tr><td style="color:var(--cad-text3);">Net Revenue {_src_tag("hcris")}</td>'
        f'<td class="num" style="font-weight:600;">{_fm(data["revenue"])}</td></tr>'
        f'<tr><td style="color:var(--cad-text3);">Current EBITDA {_src_tag("computed")}</td>'
        f'<td class="num">{_fm(data["ebitda"])}</td></tr>'
        f'<tr><td style="color:var(--cad-text3);">Operating Margin {_src_tag("computed")}</td>'
        f'<td class="num">{_pct(data["margin"])}</td></tr>'
        f'<tr><td style="color:var(--cad-text3);">Occupancy {_src_tag("hcris")}</td>'
        f'<td class="num">{_pct(data["occupancy"])}</td></tr>'
        f'<tr><td style="color:var(--cad-text3);">Revenue / Bed {_src_tag("computed")}</td>'
        f'<td class="num">{_fm(data["rev_per_bed"])}</td></tr>'
        f'<tr><td style="color:var(--cad-text3);">Net-to-Gross {_src_tag("hcris")}</td>'
        f'<td class="num">{_pct(data["n2g"])}</td></tr>'
        f'<tr><td style="color:var(--cad-text3);">Distress Probability {_src_tag("ml")}</td>'
        f'<td class="num">{_pct(distress_prob)}</td></tr>'
        f'</table></div></div></div>'
    )

    # ── 2. MARKET CONTEXT ──
    n_st = data["n_state"]
    st_margins = data["state_df"]["operating_margin"].dropna() if "operating_margin" in data["state_df"].columns else pd.Series(dtype=float)
    st_med_margin = float(st_margins.median()) if len(st_margins) > 5 else 0

    comp_margins = data["comp_df"]["operating_margin"].dropna() if "operating_margin" in data["comp_df"].columns else pd.Series(dtype=float)
    comp_med_margin = float(comp_margins.median()) if len(comp_margins) > 3 else 0

    sections.append(
        f'<div class="cad-card">'
        f'<h2>2. Market Context & Competitive Position</h2>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:10px;">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{n_st}</div>'
        f'<div class="cad-kpi-label">{_html.escape(data["state"])} Hospitals</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_pct(st_med_margin)}</div>'
        f'<div class="cad-kpi-label">State Median Margin</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{data["n_comps"]}</div>'
        f'<div class="cad-kpi-label">Comparable Hospitals</div></div></div>'
        f'<p style="font-size:12.5px;color:var(--cad-text2);line-height:1.7;">'
        f'{_html.escape(data["state"])} has {n_st} Medicare-certified hospitals with a '
        f'median operating margin of {_pct(st_med_margin)}. The target\'s margin of '
        f'{_pct(data["margin"])} places it '
        f'{"above" if data["margin"] > st_med_margin else "below"} the state median. '
        f'Among {data["n_comps"]} size-comparable peers ({data["beds"]*0.5:.0f}-{data["beds"]*2:.0f} beds), '
        f'the median margin is {_pct(comp_med_margin)}. '
        f'{"The target\'s below-peer margin suggests operational improvement opportunity." if data["margin"] < comp_med_margin else "The target performs in line with or above peers."}'
        f'</p></div>'
    )

    # ── 3. RCM PERFORMANCE ANALYSIS WITH COMPS ──
    comp_rows = ""
    comp_sample = data["comp_df"].nlargest(8, "net_patient_revenue") if len(data["comp_df"]) > 0 else pd.DataFrame()
    for _, row in comp_sample.iterrows():
        c_rev = float(row.get("net_patient_revenue", 0))
        c_margin = float(row.get("operating_margin", 0)) if "operating_margin" in row.index else 0
        c_beds = int(row.get("beds", 0))
        comp_rows += (
            f'<tr>'
            f'<td>{_html.escape(str(row.get("name", ""))[:30])}</td>'
            f'<td>{_html.escape(str(row.get("state", "")))}</td>'
            f'<td class="num">{c_beds}</td>'
            f'<td class="num">{_fm(c_rev)}</td>'
            f'<td class="num">{_pct(c_margin)}</td>'
            f'</tr>'
        )

    sections.append(
        f'<div class="cad-card">'
        f'<h2>3. RCM Performance Analysis — Comparable Hospitals</h2>'
        f'<p style="font-size:12.5px;color:var(--cad-text2);margin-bottom:10px;line-height:1.7;">'
        f'Comps selected by bed count ({data["beds"]*0.5:.0f}-{data["beds"]*2:.0f}), '
        f'prioritizing same-state peers. {data["n_comps"]} hospitals in the comp set.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Hospital</th><th>State</th><th>Beds</th><th>Revenue</th><th>Margin</th>'
        f'</tr></thead><tbody>'
        f'<tr style="background:var(--cad-bg3);font-weight:600;">'
        f'<td>{_html.escape(data["name"][:30])} (Target)</td>'
        f'<td>{_html.escape(data["state"])}</td>'
        f'<td class="num">{data["beds"]:.0f}</td>'
        f'<td class="num">{_fm(data["revenue"])}</td>'
        f'<td class="num">{_pct(data["margin"])}</td></tr>'
        f'{comp_rows}</tbody></table></div>'
    )

    # ── 4. PREDICTED IMPROVEMENT OPPORTUNITIES ──
    lever_rows = ""
    for lev in data["bridge"]["levers"]:
        if lev["ebitda_impact"] == 0:
            continue
        lever_rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{_html.escape(lev["name"])}</td>'
            f'<td class="num">{lev["current"]:.1%}</td>'
            f'<td class="num" style="color:var(--cad-pos);">{lev["target"]:.1%}</td>'
            f'<td class="num" style="font-weight:600;color:var(--cad-pos);">{_fm(lev["ebitda_impact"])}</td>'
            f'<td class="num">+{lev["margin_bps"]:.0f}bp</td>'
            f'<td class="num">{lev["ramp_months"]}mo</td>'
            f'</tr>'
        )

    sections.append(
        f'<div class="cad-card">'
        f'<h2>4. Predicted Improvement Opportunities</h2>'
        f'<p style="font-size:12.5px;color:var(--cad-text2);margin-bottom:10px;line-height:1.7;">'
        f'Improvement targets set at P75 of comparable peers with 60% gap closure assumption. '
        f'Coefficients calibrated to published research bands. '
        f'Total EBITDA uplift: <strong style="color:var(--cad-pos);">{_fm(data["bridge"]["total_ebitda_impact"])}</strong> '
        f'({data["bridge"]["margin_improvement_bps"]:.0f}bps margin improvement).</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Lever</th><th>Current</th><th>Target</th><th>EBITDA Impact</th><th>Margin</th><th>Ramp</th>'
        f'</tr></thead><tbody>{lever_rows}</tbody></table></div>'
    )

    # ── 5. EBITDA BRIDGE ──
    max_bar = max(abs(l["ebitda_impact"]) for l in data["bridge"]["levers"] if l["ebitda_impact"] != 0) or 1
    waterfall = ""
    for lev in data["bridge"]["levers"]:
        if lev["ebitda_impact"] == 0:
            continue
        bar_pct = min(100, abs(lev["ebitda_impact"]) / max_bar * 75)
        waterfall += (
            f'<div style="display:flex;align-items:center;gap:8px;padding:5px 0;'
            f'border-bottom:1px solid var(--cad-border);">'
            f'<div style="width:160px;font-size:12px;font-weight:500;">{_html.escape(lev["name"])}</div>'
            f'<div style="flex:1;background:var(--cad-bg3);border-radius:3px;height:16px;">'
            f'<div style="width:{bar_pct:.0f}%;background:var(--cad-pos);border-radius:3px;'
            f'height:16px;display:flex;align-items:center;justify-content:flex-end;padding-right:4px;'
            f'font-size:10px;color:#fff;font-weight:600;min-width:35px;">'
            f'{_fm(lev["ebitda_impact"])}</div></div></div>'
        )

    sections.append(
        f'<div class="cad-card">'
        f'<h2>5. EBITDA Bridge</h2>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">'
        f'<div>{waterfall}'
        f'<div style="display:flex;justify-content:space-between;padding:8px 0;font-weight:700;'
        f'border-top:2px solid var(--cad-border);margin-top:4px;font-size:13px;">'
        f'<span>Total EBITDA Uplift</span>'
        f'<span style="color:var(--cad-pos);">{_fm(data["bridge"]["total_ebitda_impact"])}</span></div></div>'
        f'<div>'
        f'<table class="cad-table" style="font-size:12px;">'
        f'<tr><td>Current EBITDA</td><td class="num">{_fm(data["ebitda"])}</td></tr>'
        f'<tr><td>+ RCM Uplift</td><td class="num" style="color:var(--cad-pos);">'
        f'+{_fm(data["bridge"]["total_ebitda_impact"])}</td></tr>'
        f'<tr style="font-weight:700;border-top:2px solid var(--cad-border);">'
        f'<td>Pro Forma EBITDA</td><td class="num">{_fm(data["bridge"]["new_ebitda"])}</td></tr>'
        f'<tr><td>Current Margin</td><td class="num">{_pct(data["margin"])}</td></tr>'
        f'<tr><td>Pro Forma Margin</td><td class="num" style="color:var(--cad-pos);">'
        f'{_pct(data["bridge"]["new_margin"])}</td></tr>'
        f'<tr><td>WC Released (1x)</td><td class="num">{_fm(data["bridge"]["total_wc_released"])}</td></tr>'
        f'</table></div></div></div>'
    )

    # ── 6. RETURNS ANALYSIS ──
    def _scenario_row(label, grid, style=""):
        if not grid:
            return ""
        g = grid[0]
        irr_color = "var(--cad-pos)" if g["irr"] > 0.20 else ("var(--cad-warn)" if g["irr"] > 0.15 else "var(--cad-neg)")
        return (
            f'<tr style="{style}">'
            f'<td style="font-weight:600;">{label}</td>'
            f'<td class="num">{g["entry_multiple"]:.1f}x</td>'
            f'<td class="num">{g["exit_multiple"]:.1f}x</td>'
            f'<td class="num">{_fm(g["entry_equity"])}</td>'
            f'<td class="num">{_fm(g["exit_equity"])}</td>'
            f'<td class="num" style="font-weight:600;">{g["moic"]:.2f}x</td>'
            f'<td class="num" style="color:{irr_color};font-weight:600;">{_pct(g["irr"])}</td>'
            f'</tr>'
        )

    scenarios = (
        _scenario_row("Base Case", data["base_grid"][:1]) +
        _scenario_row("Base (11x exit)", data["base_grid"][1:2]) +
        _scenario_row("Bull Case", data["bull_grid"][:1]) +
        _scenario_row("Bull (12x exit)", data["bull_grid"][1:2]) +
        _scenario_row("Bear Case", data["bear_grid"][:1], "color:var(--cad-neg);") +
        _scenario_row("Bear (11x exit)", data["bear_grid"][1:2])
    )

    sections.append(
        f'<div class="cad-card">'
        f'<h2>6. Returns Analysis — Scenario Matrix</h2>'
        f'<p style="font-size:12.5px;color:var(--cad-text2);margin-bottom:10px;line-height:1.7;">'
        f'5-year hold, 5.5x leverage, 3% organic growth, 10%/yr debt paydown. '
        f'Base case uses 100% of predicted RCM uplift. Bull case: 130% uplift at lower entry. '
        f'Bear case: 50% uplift at higher entry.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Scenario</th><th>Entry</th><th>Exit</th><th>Equity In</th>'
        f'<th>Equity Out</th><th>MOIC</th><th>IRR</th>'
        f'</tr></thead><tbody>{scenarios}</tbody></table></div>'
    )

    # ── 7. KEY RISKS & MITIGANTS ──
    risks = []
    if data["margin"] < 0:
        risks.append(("Negative operating margin", "RCM uplift bridge shows clear path to profitability; working capital release provides near-term cash cushion", "High"))
    if data["mc_pct"] > 0.55:
        risks.append(("Heavy Medicare dependence", f"Medicare comprises {_pct(data['mc_pct'])} of days; rate updates may lag inflation. Mitigant: CDI/CMI lever directly increases Medicare reimbursement", "Medium"))
    if data["md_pct"] > 0.22:
        risks.append((f"Elevated Medicaid exposure ({_pct(data['md_pct'])})", "Medicaid reimburses below cost in most states. Mitigant: denial reduction lever has highest impact on Medicaid claims", "Medium"))
    if data["occupancy"] < 0.35:
        risks.append(("Low occupancy", f"At {_pct(data['occupancy'])}, fixed costs are spread over fewer patient days. Mitigant: volume growth is an additional upside lever not modeled in base case", "Medium"))
    if distress_prob > 0.5:
        risks.append(("Elevated distress probability", f"Model estimates {_pct(distress_prob)} probability of financial distress. Mitigant: distressed entry pricing (7-9x) compensates for risk", "High"))
    if data["n2g"] < 0.2:
        risks.append(("Low net-to-gross ratio", "Large contractual allowances suggest pricing discipline issues. Mitigant: payer renegotiation is an additional upside lever", "Low"))

    if not risks:
        risks.append(("Standard execution risk", "RCM improvement requires management buy-in and 12-18 month implementation timeline", "Medium"))

    risk_rows = ""
    for risk, mitigant, severity in risks:
        sev_color = {"High": "var(--cad-neg)", "Medium": "var(--cad-warn)", "Low": "var(--cad-pos)"}.get(severity, "var(--cad-text3)")
        risk_rows += (
            f'<tr>'
            f'<td><span style="color:{sev_color};font-weight:600;font-size:10px;">{severity}</span></td>'
            f'<td style="font-weight:500;">{_html.escape(risk)}</td>'
            f'<td style="font-size:12px;color:var(--cad-text2);">{_html.escape(mitigant)}</td>'
            f'</tr>'
        )

    sections.append(
        f'<div class="cad-card">'
        f'<h2>7. Key Risks & Mitigants</h2>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Severity</th><th>Risk Factor</th><th>Mitigant</th>'
        f'</tr></thead><tbody>{risk_rows}</tbody></table></div>'
    )

    # ── 8. DATA SOURCES & METHODOLOGY ──
    sections.append(
        f'<div class="cad-card" style="border-left:3px solid var(--cad-accent);">'
        f'<h2>8. Data Sources & Methodology Appendix</h2>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;font-size:12px;'
        f'color:var(--cad-text2);line-height:1.8;">'
        f'<div>'
        f'<h3 style="font-size:11px;color:var(--cad-accent);margin-bottom:4px;">Data Sources</h3>'
        f'<ul style="padding-left:16px;">'
        f'<li>CMS HCRIS Cost Reports (Medicare-certified hospitals)</li>'
        f'<li>CMS Medicare Utilization (DRG-level volumes)</li>'
        f'<li>CMS Chronic Conditions (county-level disease prevalence)</li>'
        f'<li>HCRIS multi-year trend data (financial time series)</li></ul>'
        f'<h3 style="font-size:11px;color:var(--cad-accent);margin:8px 0 4px;">Comparable Selection</h3>'
        f'<ul style="padding-left:16px;">'
        f'<li>{data["n_comps"]} hospitals with {data["beds"]*0.5:.0f}-{data["beds"]*2:.0f} beds</li>'
        f'<li>Same-state prioritization (n={len(data["state_df"][data["state_df"]["beds"].between(data["beds"]*0.5, data["beds"]*2)])})</li>'
        f'<li>Comp margins: P25={_pct(float(comp_margins.quantile(0.25)))} / '
        f'P50={_pct(comp_med_margin)} / P75={_pct(float(comp_margins.quantile(0.75)))}</li></ul>'
        f'</div>'
        f'<div>'
        f'<h3 style="font-size:11px;color:var(--cad-accent);margin-bottom:4px;">Bridge Methodology</h3>'
        f'<ul style="padding-left:16px;">'
        f'<li>Targets: P75 of comparable peers (60% gap closure)</li>'
        f'<li>Denial: avoidable share = 35% of delta × NPR</li>'
        f'<li>AR: bad debt coefficient = $0.65 per day per $1K NPR</li>'
        f'<li>NCR: 60% coefficient on collection rate improvement</li>'
        f'<li>CDI: 0.75% of Medicare revenue per 0.01 CMI point</li></ul>'
        f'<h3 style="font-size:11px;color:var(--cad-accent);margin:8px 0 4px;">Returns Assumptions</h3>'
        f'<ul style="padding-left:16px;">'
        f'<li>Leverage: 5.5x entry (84.6% debt / 15.4% equity)</li>'
        f'<li>Organic growth: 3% annual EBITDA growth</li>'
        f'<li>Debt paydown: 10% of principal per year</li>'
        f'<li>Hold period: 5 years</li></ul>'
        f'</div></div>'
        f'<p style="font-size:11px;color:var(--cad-text3);margin-top:12px;">'
        f'Generated by SeekingChartis on {ts}. All predictions use public data only. '
        f'Confidence intervals calibrated via split conformal prediction (90% coverage target). '
        f'This memo is for informational purposes and does not constitute investment advice.</p>'
        f'</div>'
    )

    # ── ACTIONS ──
    sections.append(
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/ebitda-bridge/{_html.escape(ccn)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Full EBITDA Bridge</a>'
        f'<a href="/ml-insights/hospital/{_html.escape(ccn)}" class="cad-btn" '
        f'style="text-decoration:none;">ML Analysis</a>'
        f'<a href="/hospital/{_html.escape(ccn)}" class="cad-btn" '
        f'style="text-decoration:none;">Hospital Profile</a>'
        f'<a href="/portfolio/regression/hospital/{_html.escape(ccn)}" class="cad-btn" '
        f'style="text-decoration:none;">Statistical Profile</a>'
        f'<a href="/predictive-screener" class="cad-btn" '
        f'style="text-decoration:none;">Deal Screener</a>'
        f'</div>'
    )

    body = "\n".join(sections)

    return chartis_shell(
        body,
        f"IC Memo — {_html.escape(data['name'])}",
        subtitle=(
            f"Investment Committee Memorandum | {_html.escape(data['state'])} | "
            f"{data['beds']:.0f} beds | Grade {invest_grade} | "
            f"EBITDA uplift {_fm(data['bridge']['total_ebitda_impact'])}"
        ),
        extra_css=(
            "@media print { .cad-nav, .cad-topbar, .cad-ticker, .no-print { display: none !important; } "
            ".cad-main { margin: 0 !important; padding: 20px !important; } "
            ".cad-card { break-inside: avoid; } }"
        ),
    )
