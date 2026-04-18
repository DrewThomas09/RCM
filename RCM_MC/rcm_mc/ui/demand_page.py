"""SeekingChartis Demand Analysis — disease density, stickiness, elasticity.

Renders the demand defensibility analysis for a hospital's operating region.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from ._chartis_kit import chartis_shell
from .brand import PALETTE


def render_demand_analysis(profile: Dict[str, Any]) -> str:
    """Render the full demand analysis page."""
    ccn = html.escape(str(profile.get("ccn", "")))
    name = html.escape(str(profile.get("hospital_name", "")))
    county = html.escape(str(profile.get("county", "")))
    state = html.escape(str(profile.get("state", "")))
    density = profile.get("disease_density_index", 50)
    stickiness = profile.get("stickiness_score", 50)
    elasticity = profile.get("price_elasticity", -0.3)
    tailwind = profile.get("tailwind_score", 0)

    density_color = PALETTE["positive"] if density > 60 else (PALETTE["warning"] if density > 40 else PALETTE["text_muted"])
    stick_color = PALETTE["positive"] if stickiness > 60 else (PALETTE["warning"] if stickiness > 40 else PALETTE["negative"])
    elas_color = PALETTE["positive"] if abs(elasticity) < 0.2 else (PALETTE["warning"] if abs(elasticity) < 0.4 else PALETTE["negative"])
    tw_color = PALETTE["positive"] if tailwind > 10 else (PALETTE["negative"] if tailwind < -10 else PALETTE["text_muted"])

    elas_label = "Inelastic" if abs(elasticity) < 0.2 else ("Moderate" if abs(elasticity) < 0.4 else "Elastic")

    # KPIs
    kpis = (
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{density_color};">'
        f'{density:.0f}/100</div>'
        f'<div class="cad-kpi-label">Disease Density Index</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{stick_color};">'
        f'{stickiness:.0f}/100</div>'
        f'<div class="cad-kpi-label">Demand Stickiness</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{elas_color};">'
        f'{elasticity:.2f}</div>'
        f'<div class="cad-kpi-label">Price Elasticity ({elas_label})</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{tw_color};">'
        f'{tailwind:+.0f}</div>'
        f'<div class="cad-kpi-label">Tailwind Score</div></div>'
        f'</div>'
    )

    # County disease prevalence table
    conditions = profile.get("top_conditions", [])
    cond_rows = ""
    for c in conditions[:12]:
        cond_name = html.escape(str(c.get("condition", "")))
        pct = c.get("prevalence_pct", 0)
        nat = c.get("national_avg_pct", 0)
        delta = c.get("delta_pct", 0)
        weight = c.get("acuity_weight", 1.0)
        delta_color = PALETTE["positive"] if delta > 1 else (PALETTE["negative"] if delta < -1 else PALETTE["text_muted"])
        cond_rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{cond_name}</td>'
            f'<td class="num">{pct:.1f}%</td>'
            f'<td class="num">{nat:.1f}%</td>'
            f'<td class="num" style="color:{delta_color};font-weight:600;">{delta:+.1f}pp</td>'
            f'<td class="num">{weight:.1f}x</td>'
            f'</tr>'
        )

    prevalence_section = (
        f'<div class="cad-card">'
        f'<h2>County Disease Prevalence — {county}, {state}</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:10px;">'
        f'Medicare chronic condition rates in this hospital\'s county vs national average. '
        f'Higher prevalence = more inpatient demand. Acuity weight reflects revenue intensity.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Condition</th><th>County %</th><th>National %</th>'
        f'<th>Delta</th><th>Acuity</th>'
        f'</tr></thead><tbody>{cond_rows}</tbody></table></div>'
    ) if cond_rows else ""

    # Stickiness breakdown
    breakdown = profile.get("stickiness_breakdown", {})
    stick_items = ""
    for label, val in [
        ("Condition Chronicity", breakdown.get("chronicity", 0)),
        ("Geographic Monopoly", breakdown.get("geographic_monopoly", 0)),
        ("Switching Cost", breakdown.get("switching_cost", 0)),
    ]:
        max_val = 34 if "Switching" in label else 33
        pct = val / max_val * 100 if max_val > 0 else 0
        bar_color = PALETTE["positive"] if pct > 60 else (PALETTE["warning"] if pct > 30 else PALETTE["negative"])
        stick_items += (
            f'<div style="margin-bottom:8px;">'
            f'<div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:2px;">'
            f'<span>{html.escape(label)}</span>'
            f'<span class="cad-mono">{val:.0f}/{max_val}</span></div>'
            f'<div style="background:{PALETTE["bg_tertiary"]};border-radius:4px;height:10px;">'
            f'<div style="width:{pct:.0f}%;background:{bar_color};border-radius:4px;height:10px;"></div>'
            f'</div></div>'
        )

    comp_count = profile.get("competitor_count", 0)
    stick_section = (
        f'<div class="cad-card">'
        f'<h2>Demand Stickiness Breakdown</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:10px;">'
        f'{comp_count} competitor hospitals in the market area.</p>'
        f'{stick_items}</div>'
    )

    # Price elasticity detail
    elas_detail = profile.get("elasticity_detail", [])
    elas_rows = ""
    for e in elas_detail[:8]:
        drg = html.escape(str(e.get("drg_code", "")))
        desc = html.escape(str(e.get("drg_description", e.get("condition", "")))[:40])
        vol = e.get("volume", 0)
        elas_val = e.get("elasticity", 0)
        sticky = e.get("sticky", False)
        badge = "cad-badge-green" if sticky else "cad-badge-muted"
        elas_rows += (
            f'<tr>'
            f'<td>{drg}</td>'
            f'<td>{desc}</td>'
            f'<td class="num">{vol:,}</td>'
            f'<td class="num">{elas_val:.2f}</td>'
            f'<td><span class="cad-badge {badge}">{"Sticky" if sticky else "Elastic"}</span></td>'
            f'</tr>'
        )

    elas_section = (
        f'<div class="cad-card">'
        f'<h2>Price Elasticity by DRG</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:10px;">'
        f'A 10% cut in Medicare reimbursement would reduce volume by ~{abs(elasticity)*10:.0f}%. '
        f'Sticky DRGs (chronic conditions) are highly inelastic.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>DRG</th><th>Description</th><th>Volume</th><th>Elasticity</th><th>Type</th>'
        f'</tr></thead><tbody>{elas_rows}</tbody></table></div>'
    ) if elas_rows else ""

    # Tailwind assessment
    tw_detail = profile.get("tailwind_detail", [])
    tw_items = ""
    for t in tw_detail[:6]:
        cond = html.escape(str(t.get("condition", "")))
        delta = t.get("delta_pct", 0)
        direction = t.get("direction", "neutral")
        impact = t.get("impact", 0)
        dir_color = PALETTE["positive"] if direction == "tailwind" else (PALETTE["negative"] if direction == "headwind" else PALETTE["text_muted"])
        arrow = "&#9650;" if direction == "tailwind" else ("&#9660;" if direction == "headwind" else "&#9654;")
        tw_items += (
            f'<div style="display:flex;justify-content:space-between;padding:6px 0;'
            f'border-bottom:1px solid {PALETTE["border"]};">'
            f'<span>{cond}</span>'
            f'<span style="color:{dir_color};">{arrow} {delta:+.1f}pp ({direction})</span>'
            f'</div>'
        )

    tw_section = (
        f'<div class="cad-card">'
        f'<h2>Demand Tailwinds & Headwinds</h2>'
        f'{tw_items}</div>'
    ) if tw_items else ""

    # Interpretation
    explanations = profile.get("explanations", {})
    interp = (
        f'<div class="cad-card" style="border-left:3px solid {PALETTE["brand_accent"]};">'
        f'<h2>What This Means for Diligence</h2>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.8;">'
        f'<p>{html.escape(explanations.get("density", ""))}</p>'
        f'<p>{html.escape(explanations.get("stickiness", ""))}</p>'
        f'<p>{html.escape(explanations.get("elasticity", ""))}</p>'
        f'<p>{html.escape(explanations.get("tailwind", ""))}</p>'
        f'</div></div>'
    )

    # Actions
    actions = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/hospital/{ccn}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Hospital Profile</a>'
        f'<a href="/hospital/{ccn}/history" class="cad-btn" style="text-decoration:none;">3-Year History</a>'
        f'<a href="/models/market/{ccn}" class="cad-btn" style="text-decoration:none;">Market Analysis</a>'
        f'<a href="/models/denial/{ccn}" class="cad-btn" style="text-decoration:none;">Denial Drivers</a>'
        f'<a href="/market-data/state/{state}" class="cad-btn" style="text-decoration:none;">'
        f'{state} Market</a>'
        f'</div>'
    )

    body = f'{kpis}{prevalence_section}{stick_section}{elas_section}{tw_section}{interp}{actions}'

    return chartis_shell(
        body, f"Demand Analysis — {name}",
        active_nav="/market-data/map",
        subtitle=f"{county}, {state} | Density: {density:.0f} | Stickiness: {stickiness:.0f} | Elasticity: {elasticity:.2f}",
    )
