"""PE Desk PE Tools — value bridge, debt model, predicted vs actual.

Connects pe/ modules to browser-rendered pages.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_next_section, ck_panel,
    ck_section_intro,
)
from .models_page import _model_nav
from .brand import PALETTE


_PE_STYLES = f"""
<style>
.pet-bar-row{{display:flex;align-items:center;gap:12px;padding:8px 0;
border-bottom:1px solid {PALETTE["border"]};}}
.pet-bar-name{{width:200px;font-size:12.5px;font-weight:500;}}
.pet-bar-flex{{flex:1;display:flex;align-items:center;gap:8px;}}
.pet-bar-track{{flex:1;background:{PALETTE["bg_tertiary"]};
border-radius:4px;height:20px;position:relative;}}
.pet-bar-fill{{border-radius:4px;height:20px;display:flex;
align-items:center;justify-content:flex-end;padding-right:6px;
font-size:10px;color:white;font-weight:600;}}
.pet-bar-meta{{font-size:11px;width:50px;}}
.pet-bar-meta-r{{font-size:11px;width:70px;text-align:right;}}
.pet-ramp{{font-size:9px;color:{PALETTE["text_muted"]};}}
</style>
"""


def render_value_bridge(deal_id: str, deal_name: str, bridge: Dict[str, Any]) -> str:
    """Render EBITDA value bridge as a browser page."""
    levers = bridge.get("levers", bridge.get("items", []))
    current = bridge.get("current_ebitda", 0)
    target = bridge.get("target_ebitda", bridge.get("total_ebitda", 0))
    total_impact = bridge.get("total_ebitda_impact", bridge.get("total_impact", 0))

    intro = ck_section_intro(
        eyebrow="VALUE BRIDGE",
        headline=f"{html.escape(deal_name)} — where the EBITDA uplift comes from.",
        italic_word="comes",
        body=(
            f"7-lever EBITDA bridge from current ${current/1e6:.0f}M "
            f"to target ${(current+total_impact)/1e6:.0f}M. Each "
            "lever shows gross impact, probability of achievement, "
            "and probability-weighted contribution."
        ),
    )

    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Current EBITDA", f"${current/1e6:.1f}M")
        + ck_kpi_block("Target EBITDA", f"${(current+total_impact)/1e6:.1f}M")
        + ck_kpi_block("Total Uplift", f"+${total_impact/1e6:.1f}M")
        + ck_kpi_block("Value Levers", f"{len(levers)}")
        + '</div>'
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
        cls = "cad-pos" if impact > 0 else "cad-neg"
        # Try to find ramp timeline for this lever
        ramp_label = ""
        name_lower = name.lower()
        for fam, months in ramp_info.items():
            if fam.lower() in name_lower or name_lower in fam.lower():
                ramp_label = f' <span class="pet-ramp">({months} ramp)</span>'
                break
        bars += (
            '<div class="pet-bar-row">'
            f'<div class="pet-bar-name">{name}{ramp_label}</div>'
            '<div class="pet-bar-flex">'
            '<div class="pet-bar-track">'
            f'<div class="pet-bar-fill" style="width:{bar_w:.0f}%;background:{color};">'
            f'${impact/1e6:.1f}M</div></div>'
            f'<span class="cad-mono pet-bar-meta">{prob:.0%} prob</span>'
            f'<span class="cad-mono pet-bar-meta-r {cls}">${weighted/1e6:.1f}M wtd</span>'
            '</div></div>'
        )

    bridge_section = ck_panel(
        '<p class="ck-section-body">'
        'Each lever shows gross impact, probability of achievement, and probability-weighted value.</p>'
        f'{bars}',
        title="EBITDA Bridge — 7 Lever Model",
    )

    actions = ck_panel(
        '<p class="ck-section-body">'
        f'<a href="/models/dcf/{html.escape(deal_id)}" class="cad-btn">DCF</a> '
        f'<a href="/models/lbo/{html.escape(deal_id)}" class="cad-btn">LBO</a> '
        f'<a href="/models/playbook/{html.escape(deal_id)}" class="cad-btn">Playbook</a> '
        f'<a href="/analysis/{html.escape(deal_id)}" class="cad-btn cad-btn-primary">Full Analysis</a>'
        '</p>',
        title="Cross-links",
    )

    # Interpretation
    uplift_pct = total_impact / current * 100 if current > 0 else 0
    top_lever = max(levers, key=lambda l: abs(float(l.get("impact", l.get("ebitda_impact", 0))) * float(l.get("probability", 1))), default={})
    top_name = str(top_lever.get("lever", top_lever.get("name", "unknown")))
    top_wtd = float(top_lever.get("impact", 0)) * float(top_lever.get("probability", 1))
    interp = ck_panel(
        '<p class="ck-section-body">'
        f'The 7-lever model projects a <strong>{uplift_pct:.0f}% EBITDA uplift</strong> '
        f'from ${current/1e6:.0f}M to ${(current+total_impact)/1e6:.0f}M. '
        f'The highest-impact lever is <strong>{html.escape(top_name)}</strong> '
        f'at ${top_wtd/1e6:.1f}M probability-weighted.</p>'
        '<p class="ck-section-body">'
        '<strong>IC talking point:</strong> '
        f'"We see ${total_impact/1e6:.0f}M in annual EBITDA improvement, '
        f'primarily from {html.escape(top_name.lower())}. At an 11x multiple, '
        f'this represents ${total_impact * 11 / 1e6:.0f}M in equity value creation."</p>',
        title="What This Means",
    )

    nav = _model_nav(deal_id, "bridge")
    next_up = ck_next_section(
        "Open the playbook",
        f"/models/playbook/{html.escape(deal_id)}",
        eyebrow="Continue —",
        italic_word="playbook",
    )
    body = f'{_PE_STYLES}{nav}{intro}{kpis}{bridge_section}{interp}{actions}{next_up}'
    return chartis_shell(body, f"Value Bridge — {html.escape(deal_name)}",
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

    intro = ck_section_intro(
        eyebrow="COMPARABLE HOSPITALS",
        headline=f"{html.escape(deal_name)} — closest peers by profile distance.",
        italic_word="closest",
        body=(
            f"{len(comparables)} hospitals most similar to "
            f"{html.escape(deal_name)} on bed count, revenue, "
            "margins, and payer mix. Use as a base-rate sanity "
            "check for the bridge."
        ),
    )
    body = (
        intro
        + ck_panel(
            '<table class="cad-table"><thead><tr>'
            '<th>Hospital</th><th>State</th><th>Beds</th><th>NPR</th><th>Similarity</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>',
            title=f"Comparable Hospitals ({len(comparables)})",
        )
        + ck_panel(
            '<p class="ck-section-body">'
            f'<a href="/models/market/{html.escape(deal_id)}" class="cad-btn">Market Analysis</a> '
            f'<a href="/analysis/{html.escape(deal_id)}" class="cad-btn cad-btn-primary">Full Analysis</a>'
            '</p>',
            title="Cross-links",
        )
        + ck_next_section(
            "Open the market analysis",
            f"/models/market/{html.escape(deal_id)}",
            eyebrow="Continue —",
            italic_word="market",
        )
    )

    return chartis_shell(body, f"Comparables — {html.escape(deal_name)}",
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
            f'<td><strong>{metric}</strong></td>'
            f'<td class="num">{float(value):,.2f}</td>'
            f'<td class="num">{float(expected):,.2f}</td>'
            f'<td class="num">{float(zscore):+.1f}σ</td>'
            f'<td><span class="cad-badge {sev_cls}">{severity}</span></td>'
            f'</tr>'
        )

    n_high = sum(1 for a in anomalies if abs(float(a.get("z_score", a.get("deviation", 0)))) > 3)

    intro = ck_section_intro(
        eyebrow="ANOMALY REPORT",
        headline=f"{html.escape(deal_name)} — metrics that don't match the cohort.",
        italic_word="don't",
        body=(
            f"{len(anomalies)} anomalies detected vs HCRIS "
            "benchmarks. High-severity (>3σ) flags either data "
            "quality issues or genuine outliers worth a follow-up."
        ),
    )
    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Anomalies Detected", f"{len(anomalies)}")
        + ck_kpi_block("High Severity", f"{n_high}")
        + '</div>'
    )

    body = (
        f'{intro}{kpis}'
        + ck_panel(
            '<p class="ck-section-body">'
            'Metrics that deviate significantly from HCRIS benchmarks. '
            'High severity (&gt;3σ) may indicate data quality issues or genuine outliers.</p>'
            '<table class="cad-table"><thead><tr>'
            '<th>Metric</th><th>Value</th><th>Expected</th><th>Z-Score</th><th>Severity</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>',
            title="Data Anomalies",
        )
        + ck_panel(
            '<p class="ck-section-body">'
            f'<a href="/models/questions/{html.escape(deal_id)}" class="cad-btn">Diligence Questions</a> '
            f'<a href="/analysis/{html.escape(deal_id)}" class="cad-btn cad-btn-primary">Full Analysis</a>'
            '</p>',
            title="Cross-links",
        )
        + ck_next_section(
            "Open the diligence questions",
            f"/models/questions/{html.escape(deal_id)}",
            eyebrow="Continue —",
            italic_word="questions",
        )
    )

    return chartis_shell(body, f"Anomaly Report — {html.escape(deal_name)}",
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
        margin_cls = "cad-pos" if margin > 0.10 else ("cad-warn" if margin > 0 else "cad-neg")
        rows += (
            f'<tr>'
            f'<td><strong>{name}</strong></td>'
            f'<td class="num">${rev/1e6:.1f}M</td>'
            f'<td class="num">{pct:.1f}%</td>'
            f'<td class="num {margin_cls}">{margin:.1%}</td>'
            f'<td class="num">{int(vol):,}</td>'
            f'</tr>'
        )

    intro = ck_section_intro(
        eyebrow="SERVICE LINES",
        headline=f"{html.escape(deal_name)} — where value is actually created.",
        italic_word="actually",
        body=(
            f"{len(lines)} service lines · ${total_rev/1e6:.0f}M "
            "total revenue. Identifies which lines drive margin "
            "and where operational improvement has the highest "
            "impact."
        ),
    )
    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Service Lines", f"{len(lines)}")
        + ck_kpi_block("Total Revenue", f"${total_rev/1e6:.0f}M")
        + '</div>'
    )

    body = (
        f'{intro}{kpis}'
        + ck_panel(
            '<p class="ck-section-body">'
            'Revenue and margin contribution by service line. Identifies where value is created '
            'and where operational improvement has the highest impact.</p>'
            '<table class="cad-table"><thead><tr>'
            '<th>Service Line</th><th>Revenue</th><th>% Mix</th><th>Margin</th><th>Volume</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>',
            title="Service Line Profitability",
        )
        + ck_panel(
            '<p class="ck-section-body">'
            f'<a href="/models/denial/{html.escape(deal_id)}" class="cad-btn">Denial Drivers</a> '
            f'<a href="/analysis/{html.escape(deal_id)}" class="cad-btn cad-btn-primary">Full Analysis</a>'
            '</p>',
            title="Cross-links",
        )
        + ck_next_section(
            "Open denial drivers",
            f"/models/denial/{html.escape(deal_id)}",
            eyebrow="Continue —",
            italic_word="denial",
        )
    )

    return chartis_shell(body, f"Service Lines — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"{len(lines)} service lines | ${total_rev/1e6:.0f}M total revenue")
