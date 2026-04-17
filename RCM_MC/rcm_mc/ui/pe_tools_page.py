"""SeekingChartis PE Tools — value bridge, debt model, predicted vs actual.

Connects pe/ modules to browser-rendered pages.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from .shell_v2 import shell_v2
from .models_page import _model_nav
from .brand import PALETTE


def render_value_bridge(deal_id: str, deal_name: str, bridge: Dict[str, Any]) -> str:
    """Render EBITDA value bridge as a browser page."""
    levers = bridge.get("levers", bridge.get("items", []))
    current = bridge.get("current_ebitda", 0)
    target = bridge.get("target_ebitda", bridge.get("total_ebitda", 0))
    total_impact = bridge.get("total_ebitda_impact", bridge.get("total_impact", 0))

    kpis = (
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">${current/1e6:.1f}M</div>'
        f'<div class="cad-kpi-label">Current EBITDA</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{PALETTE["positive"]};">'
        f'${(current+total_impact)/1e6:.1f}M</div>'
        f'<div class="cad-kpi-label">Target EBITDA</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{PALETTE["brand_accent"]};">'
        f'+${total_impact/1e6:.1f}M</div>'
        f'<div class="cad-kpi-label">Total Uplift</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(levers)}</div>'
        f'<div class="cad-kpi-label">Value Levers</div></div>'
        f'</div>'
    )

    # Waterfall bars
    # Get ramp curves for timeline info
    ramp_info: Dict[str, str] = {}
    try:
        from ..pe.ramp_curves import curve_for_metric, family_for_metric
        for metric_key in ["denial_rate", "days_in_ar", "coding_accuracy", "payer_mix",
                           "cost_to_collect", "clean_claim_rate", "volume_growth"]:
            try:
                curve = curve_for_metric(metric_key)
                fam = family_for_metric(metric_key)
                ramp_info[fam] = f"{curve.months_to_full}mo"
            except Exception:
                pass
    except Exception:
        pass

    bars = ""
    max_impact = max((abs(float(l.get("impact", l.get("ebitda_impact", 0)))) for l in levers), default=1)
    for l in levers:
        name = html.escape(str(l.get("lever", l.get("name", l.get("label", "")))))
        impact = float(l.get("impact", l.get("ebitda_impact", 0)))
        prob = float(l.get("probability", l.get("prob", 1.0)))
        weighted = impact * prob
        bar_w = min(100, abs(impact) / max(max_impact, 1) * 80)
        color = PALETTE["positive"] if impact > 0 else PALETTE["negative"]
        # Try to find ramp timeline for this lever
        ramp_label = ""
        name_lower = name.lower()
        for fam, months in ramp_info.items():
            if fam.lower() in name_lower or name_lower in fam.lower():
                ramp_label = f' <span style="font-size:9px;color:{PALETTE["text_muted"]};">({months} ramp)</span>'
                break
        bars += (
            f'<div style="display:flex;align-items:center;gap:12px;padding:8px 0;'
            f'border-bottom:1px solid {PALETTE["border"]};">'
            f'<div style="width:200px;font-size:12.5px;font-weight:500;">{name}{ramp_label}</div>'
            f'<div style="flex:1;display:flex;align-items:center;gap:8px;">'
            f'<div style="flex:1;background:{PALETTE["bg_tertiary"]};border-radius:4px;height:20px;'
            f'position:relative;">'
            f'<div style="width:{bar_w:.0f}%;background:{color};border-radius:4px;height:20px;'
            f'display:flex;align-items:center;justify-content:flex-end;padding-right:6px;'
            f'font-size:10px;color:white;font-weight:600;">'
            f'${impact/1e6:.1f}M</div></div>'
            f'<span class="cad-mono" style="font-size:11px;color:{PALETTE["text_muted"]};width:50px;">'
            f'{prob:.0%} prob</span>'
            f'<span class="cad-mono" style="font-size:11px;color:{color};width:70px;text-align:right;">'
            f'${weighted/1e6:.1f}M wtd</span>'
            f'</div></div>'
        )

    bridge_section = (
        f'<div class="cad-card">'
        f'<h2>EBITDA Bridge — 7 Lever Model</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:12px;">'
        f'Each lever shows gross impact, probability of achievement, and probability-weighted value.</p>'
        f'{bars}</div>'
    )

    actions = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/models/dcf/{html.escape(deal_id)}" class="cad-btn" style="text-decoration:none;">DCF</a>'
        f'<a href="/models/lbo/{html.escape(deal_id)}" class="cad-btn" style="text-decoration:none;">LBO</a>'
        f'<a href="/models/playbook/{html.escape(deal_id)}" class="cad-btn" style="text-decoration:none;">Playbook</a>'
        f'<a href="/analysis/{html.escape(deal_id)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Full Analysis</a></div>'
    )

    # Interpretation
    uplift_pct = total_impact / current * 100 if current > 0 else 0
    top_lever = max(levers, key=lambda l: abs(float(l.get("impact", l.get("ebitda_impact", 0))) * float(l.get("probability", 1))), default={})
    top_name = str(top_lever.get("lever", top_lever.get("name", "unknown")))
    top_wtd = float(top_lever.get("impact", 0)) * float(top_lever.get("probability", 1))
    interp = (
        f'<div class="cad-card" style="border-left:3px solid {PALETTE["positive"]};">'
        f'<h2>What This Means</h2>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'<p>The 7-lever model projects a <strong>{uplift_pct:.0f}% EBITDA uplift</strong> '
        f'from ${current/1e6:.0f}M to ${(current+total_impact)/1e6:.0f}M. '
        f'The highest-impact lever is <strong>{html.escape(top_name)}</strong> '
        f'at ${top_wtd/1e6:.1f}M probability-weighted.</p>'
        f'<p style="margin-top:6px;"><strong>IC talking point:</strong> '
        f'"We see ${total_impact/1e6:.0f}M in annual EBITDA improvement, '
        f'primarily from {html.escape(top_name.lower())}. At an 11x multiple, '
        f'this represents ${total_impact * 11 / 1e6:.0f}M in equity value creation."</p>'
        f'</div></div>'
    )

    nav = _model_nav(deal_id, "bridge")
    body = f'{nav}{kpis}{bridge_section}{interp}{actions}'
    return shell_v2(body, f"Value Bridge — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"Current ${current/1e6:.0f}M → Target ${(current+total_impact)/1e6:.0f}M (+${total_impact/1e6:.1f}M)")


def render_comparable_hospitals(deal_id: str, deal_name: str,
                                 comparables: List[Dict[str, Any]],
                                 target_profile: Dict[str, Any]) -> str:
    """Render comparable hospital finder results."""
    rows = ""
    for c in comparables[:20]:
        ccn = html.escape(str(c.get("ccn", "")))
        name = html.escape(str(c.get("name", ""))[:45])
        state = html.escape(str(c.get("state", "")))
        beds = c.get("beds", c.get("bed_count", 0))
        rev = c.get("net_patient_revenue", c.get("revenue", 0))
        dist = c.get("distance", c.get("similarity", 0))
        dist_pct = max(0, 100 - float(dist) * 10) if dist else 0
        rows += (
            f'<tr>'
            f'<td><a href="/hospital/{ccn}">{name}</a></td>'
            f'<td>{state}</td>'
            f'<td class="num">{int(beds):,}</td>'
            f'<td class="num">${float(rev)/1e6:,.0f}M</td>'
            f'<td class="num">{dist_pct:.0f}%</td>'
            f'</tr>'
        )

    body = (
        f'<div class="cad-card">'
        f'<h2>Comparable Hospitals ({len(comparables)})</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:10px;">'
        f'Hospitals most similar to {html.escape(deal_name)} by numeric profile distance '
        f'(bed count, revenue, margins, payer mix).</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Hospital</th><th>State</th><th>Beds</th><th>NPR</th><th>Similarity</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'

        f'<div class="cad-card" style="display:flex;gap:8px;">'
        f'<a href="/models/market/{html.escape(deal_id)}" class="cad-btn" style="text-decoration:none;">'
        f'Market Analysis</a>'
        f'<a href="/analysis/{html.escape(deal_id)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Full Analysis</a></div>'
    )

    return shell_v2(body, f"Comparables — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"{len(comparables)} comparable hospitals found")


def render_anomaly_report(deal_id: str, deal_name: str,
                           anomalies: List[Dict[str, Any]]) -> str:
    """Render anomaly detection results."""
    rows = ""
    for a in anomalies:
        metric = html.escape(str(a.get("metric", a.get("field", ""))))
        value = a.get("value", 0)
        expected = a.get("expected", a.get("benchmark", 0))
        zscore = a.get("z_score", a.get("deviation", 0))
        severity = "high" if abs(float(zscore)) > 3 else ("medium" if abs(float(zscore)) > 2 else "low")
        sev_cls = {"high": "cad-badge-red", "medium": "cad-badge-amber"}.get(severity, "cad-badge-muted")
        rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{metric}</td>'
            f'<td class="num">{float(value):,.2f}</td>'
            f'<td class="num">{float(expected):,.2f}</td>'
            f'<td class="num">{float(zscore):+.1f}σ</td>'
            f'<td><span class="cad-badge {sev_cls}">{severity}</span></td>'
            f'</tr>'
        )

    n_high = sum(1 for a in anomalies if abs(float(a.get("z_score", a.get("deviation", 0)))) > 3)

    body = (
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(anomalies)}</div>'
        f'<div class="cad-kpi-label">Anomalies Detected</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{PALETTE["negative"]};">'
        f'{n_high}</div>'
        f'<div class="cad-kpi-label">High Severity</div></div>'
        f'</div>'

        f'<div class="cad-card">'
        f'<h2>Data Anomalies</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:10px;">'
        f'Metrics that deviate significantly from HCRIS benchmarks. '
        f'High severity (&gt;3σ) may indicate data quality issues or genuine outliers.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Metric</th><th>Value</th><th>Expected</th><th>Z-Score</th><th>Severity</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'

        f'<div class="cad-card" style="display:flex;gap:8px;">'
        f'<a href="/models/questions/{html.escape(deal_id)}" class="cad-btn" style="text-decoration:none;">'
        f'Diligence Questions</a>'
        f'<a href="/analysis/{html.escape(deal_id)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Full Analysis</a></div>'
    )

    return shell_v2(body, f"Anomaly Report — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"{len(anomalies)} anomalies, {n_high} high severity")


def render_service_lines(deal_id: str, deal_name: str,
                          lines: List[Dict[str, Any]]) -> str:
    """Render service line profitability analysis."""
    rows = ""
    total_rev = sum(float(l.get("revenue", 0)) for l in lines)
    for l in lines:
        name = html.escape(str(l.get("service_line", l.get("name", ""))))
        rev = float(l.get("revenue", 0))
        margin = float(l.get("margin", l.get("contribution_margin", 0)))
        vol = l.get("volume", l.get("cases", 0))
        pct = rev / total_rev * 100 if total_rev > 0 else 0
        margin_color = PALETTE["positive"] if margin > 0.10 else (PALETTE["warning"] if margin > 0 else PALETTE["negative"])
        rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{name}</td>'
            f'<td class="num">${rev/1e6:.1f}M</td>'
            f'<td class="num">{pct:.1f}%</td>'
            f'<td class="num" style="color:{margin_color};">{margin:.1%}</td>'
            f'<td class="num">{int(vol):,}</td>'
            f'</tr>'
        )

    body = (
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(lines)}</div>'
        f'<div class="cad-kpi-label">Service Lines</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">${total_rev/1e6:.0f}M</div>'
        f'<div class="cad-kpi-label">Total Revenue</div></div>'
        f'</div>'

        f'<div class="cad-card">'
        f'<h2>Service Line Profitability</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:10px;">'
        f'Revenue and margin contribution by service line. Identifies where value is created '
        f'and where operational improvement has the highest impact.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Service Line</th><th>Revenue</th><th>% Mix</th><th>Margin</th><th>Volume</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'

        f'<div class="cad-card" style="display:flex;gap:8px;">'
        f'<a href="/models/denial/{html.escape(deal_id)}" class="cad-btn" style="text-decoration:none;">'
        f'Denial Drivers</a>'
        f'<a href="/analysis/{html.escape(deal_id)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Full Analysis</a></div>'
    )

    return shell_v2(body, f"Service Lines — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"{len(lines)} service lines | ${total_rev/1e6:.0f}M total revenue")
