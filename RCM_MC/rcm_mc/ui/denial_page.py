"""PE Desk Denial Drivers — browser-rendered denial analysis.

Renders the denial driver decomposition as a visual page instead of raw JSON.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from ._chartis_kit import (
    chartis_shell, ck_fmt_num, ck_kpi_block, ck_next_section,
    ck_provenance_tooltip, ck_value_anchor,
)
from .models_page import _model_nav
from .brand import PALETTE


def render_denial_page(deal_id: str, deal_name: str, analysis: Dict[str, Any]) -> str:
    """Render denial driver analysis as a browser page."""
    drivers = analysis.get("drivers", [])
    summary = analysis.get("summary", {})
    recommendations = analysis.get("recommendations", [])

    # Summary KPIs
    total_impact = summary.get("total_annual_impact", 0)
    denial_rate = summary.get("current_denial_rate", 0)
    target_rate = summary.get("target_denial_rate", 0)
    # Cycle 50 — port to ck_kpi_block + provenance.
    current_value = ck_provenance_tooltip(
        "Current denial rate",
        f'<span style="color:{PALETTE["negative"]};">{denial_rate:.1f}%</span>',
        explainer=(
            "Initial denial rate (IDR) = denied claims / total "
            "claims submitted. Industry average is 8-12%; above "
            "15% flags a roll-up audit-recovery opportunity. "
            "The drivers below decompose by root cause."
        ),
    )
    impact_value = ck_provenance_tooltip(
        "Recoverable annual revenue",
        f"${total_impact/1e6:.1f}M",
        explainer=(
            "Sum of EBITDA recovery opportunities across the "
            "identified drivers, weighted by historical appeal-"
            "success rates. Conservative; the 'addressable' "
            "bucket only - not the gross denial dollar volume."
        ),
        inject_css=False,
    )
    kpis = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block(
            "Current Denial Rate", current_value, "initial denial rate",
            help={
                "definition": (
                    "Share of submitted claims initially denied by "
                    "payers before any appeals. The starting line for "
                    "any RCM uplift — every other lever (clean DAR, "
                    "final write-off, cash conversion) downstream of "
                    "denial reduction."
                ),
            },
        )
        + ck_kpi_block(
            "Target Denial Rate", f"{target_rate:.1f}%", "post-uplift goal",
            help={
                "definition": (
                    "Denial rate this hospital should hit post-RCM "
                    "intervention, based on its peer cohort's P75. "
                    "The recoverable-revenue figure assumes the "
                    "hospital reaches this target on a 24-month "
                    "ramp; aggressive plans front-load to 12 months."
                ),
            },
        )
        + ck_kpi_block(
            "Recoverable Revenue", impact_value, "annual EBITDA",
            help={
                "definition": (
                    "Annual EBITDA recoverable if denial rate moves "
                    "from current → target. Computed by applying the "
                    "denial-rate delta to net patient revenue, "
                    "discounting for appeals that already recover "
                    "some denied claims. Use this as the upper bound "
                    "of denial-driver-only RCM uplift."
                ),
            },
        )
        + ck_kpi_block(
            "Root Causes", ck_fmt_num(len(drivers)), "drivers identified",
            help={
                "definition": (
                    "Distinct denial-driver categories (eligibility, "
                    "authorization, medical-necessity, coding, "
                    "duplicate claim, etc.) the model identified for "
                    "this hospital. More drivers = scattered issues "
                    "needing broad workflow fixes; fewer = a specific "
                    "structural problem that targeted intervention "
                    "could solve."
                ),
            },
        )
        + '</div>'
    )

    # Drivers table
    driver_rows = ""
    for d in drivers:
        name = html.escape(str(d.get("driver", d.get("name", ""))))
        pct = d.get("contribution_pct", d.get("pct", 0))
        impact = d.get("annual_impact", d.get("impact", 0))
        severity = d.get("severity", "medium")
        sev_cls = {"high": "cad-badge-red", "medium": "cad-badge-amber"}.get(severity, "cad-badge-muted")
        bar_w = min(100, abs(pct) * 5) if pct else 0
        driver_rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{name}</td>'
            f'<td class="num">{pct:.1f}%</td>'
            f'<td class="num">${impact/1e6:.1f}M</td>'
            f'<td><span class="cad-badge {sev_cls}">{html.escape(severity)}</span></td>'
            f'<td><div style="background:{PALETTE["bg_tertiary"]};border-radius:4px;height:8px;">'
            f'<div style="width:{bar_w:.0f}%;background:{PALETTE["negative"]};'
            f'border-radius:4px;height:8px;"></div></div></td>'
            f'</tr>'
        )

    drivers_section = (
        f'<div class="cad-card">'
        f'<h2>Denial Root Causes</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:10px;">'
        f'Decomposition of denial rate into root causes, sized by annual dollar impact.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Driver</th><th>Contribution</th><th>Annual Impact</th>'
        f'<th>Severity</th><th>Magnitude</th>'
        f'</tr></thead><tbody>{driver_rows}</tbody></table></div>'
    ) if driver_rows else ""

    # Recommendations
    rec_html = ""
    if recommendations:
        rec_items = ""
        for r in recommendations[:10]:
            title = html.escape(str(r.get("title", r.get("recommendation", ""))))
            desc = html.escape(str(r.get("description", r.get("detail", ""))))
            category = html.escape(str(r.get("category", "")))
            rec_items += (
                f'<div style="padding:10px 0;border-bottom:1px solid {PALETTE["border"]};">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<span style="font-weight:500;">{title}</span>'
                f'<span class="cad-badge cad-badge-blue">{category}</span></div>'
                f'<div style="font-size:12px;color:{PALETTE["text_secondary"]};margin-top:4px;">'
                f'{desc}</div></div>'
            )
        rec_html = (
            f'<div class="cad-card">'
            f'<h2>Expert Recommendations</h2>'
            f'{rec_items}</div>'
        )

    # Actions
    actions = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/api/deals/{html.escape(deal_id)}/denial-drivers" class="cad-btn" '
        f'style="text-decoration:none;">Raw JSON</a>'
        f'<a href="/models/dcf/{html.escape(deal_id)}" class="cad-btn" '
        f'style="text-decoration:none;">DCF Model</a>'
        f'<a href="/analysis/{html.escape(deal_id)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Full Analysis</a></div>'
    )

    # Interpretation
    dr_level = (
        "critically high — top priority for IC discussion" if denial_rate > 18
        else "above industry average — significant improvement opportunity" if denial_rate > 12
        else "moderate — in line with industry norms" if denial_rate > 8
        else "below average — strong operational performance"
    )
    interp = (
        f'<div class="cad-card" style="border-left:3px solid {PALETTE["warning"]};">'
        f'<h2>What This Means</h2>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'<p>At {denial_rate:.1f}%, this hospital\'s denial rate is {dr_level}. '
        f'Reducing to the target of {target_rate:.1f}% would recover an estimated '
        f'<strong>${total_impact/1e6:.1f}M per year</strong> in revenue.</p>'
        f'<p style="margin-top:6px;"><strong>Next steps:</strong> '
        f'Request the payer-level denial breakdown in '
        f'<a href="/models/questions/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">diligence questions</a>. '
        f'See the full value creation plan in the '
        f'<a href="/models/playbook/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">playbook</a>. '
        f'Model the EBITDA impact via the '
        f'<a href="/models/bridge/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">EBITDA bridge</a>.</p>'
        f'</div></div>'
    )

    nav = _model_nav(deal_id, "denial")
    next_up = ck_next_section(
        "Open the EBITDA bridge",
        f"/models/bridge/{html.escape(deal_id)}",
        eyebrow="Continue —",
        italic_word="bridge",
    )
    # Lead takeaway — surface the computed denial-recovery opportunity
    # (recoverable EBITDA from moving denial rate to target) at the top,
    # before the KPI grid and the driver table. All figures come from
    # the analysis summary.
    lead_anchor = ck_value_anchor(
        "DENIAL RECOVERY",
        f"{denial_rate:.1f}% denial rate",
        delta=f"target {target_rate:.1f}%",
        opportunity=f"${total_impact / 1e6:.1f}M recoverable EBITDA",
        target=f"{len(drivers)} root causes identified",
        tone="teal",
    )
    # 2026-05-28 batch 27 · Phase 3 · universal strict 5-block head.
    from ._chartis_kit import ck_editorial_head
    head = ck_editorial_head(
        eyebrow="DENIAL DRIVERS",
        title=f"Denial drivers — {html.escape(deal_name)}",
        meta=(
            f"DENIAL RATE {denial_rate:.1f}% · "
            f"${total_impact/1e6:.1f}M RECOVERABLE EBITDA · "
            f"{len(drivers)} ROOT CAUSE"
            f"{'S' if len(drivers) != 1 else ''}"
        ),
        lede_italic_phrase=(
            "Where the denials actually come from."
        ),
        lede_body=(
            "Decompose this hospital's denial rate by payer, "
            "denial code, and CARC category. Recoverable "
            "EBITDA estimate weights each driver by historical "
            "appeal-success rates — the addressable bucket, "
            "not the gross denial rate."
        ),
    )
    body = f'{head}{nav}{lead_anchor}{kpis}{drivers_section}{interp}{rec_html}{actions}{next_up}'

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body, f"Denial Drivers — {html.escape(deal_name)}",
        active_nav="/analysis",
        subtitle=f"Current: {denial_rate:.1f}% | Recoverable: ${total_impact/1e6:.1f}M/year",
    )
