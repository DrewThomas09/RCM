"""PE Desk Waterfall — returns waterfall visualization.

Connects pe/waterfall.py to the browser. Shows LP/GP split,
tier-by-tier allocation, IRR, and MOIC.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from ._chartis_kit import (
    chartis_shell, ck_fmt_pct, ck_kpi_block, ck_next_section,
    ck_provenance_tooltip, ck_value_anchor,
)
from .models_page import _model_nav
from .brand import PALETTE


def render_waterfall_page(deal_id: str, deal_name: str, result: Dict[str, Any]) -> str:
    """Render a returns waterfall as a browser page."""
    lp_total = result.get("lp_total", 0)
    gp_total = result.get("gp_total", 0)
    lp_moic = result.get("lp_moic", 0)
    gp_moic = result.get("gp_moic", 0)
    lp_irr = result.get("lp_irr", 0)
    gross_moic = result.get("gross_moic", 0)
    gross_irr = result.get("gross_irr", 0)
    invested = result.get("invested", 0)
    exit_proceeds = result.get("exit_proceeds", 0)
    hold_years = result.get("hold_years", 0)

    irr_color = PALETTE["positive"] if gross_irr > 0.20 else (
        PALETTE["warning"] if gross_irr > 0.15 else PALETTE["negative"])

    # Cycle 50 — port to ck_kpi_block + provenance.
    irr_value = ck_provenance_tooltip(
        "Gross levered IRR",
        f'<span style="color:{irr_color};">{ck_fmt_pct(gross_irr)}</span>',
        explainer=(
            "Gross deal IRR before management fees + GP carry. "
            "Above 20% green, 15-20% amber, below 15% negative. "
            "The waterfall below splits this into LP and GP "
            "tiers - LP net IRR is what actually matters for "
            "fund-level returns."
        ),
    )
    moic_value = ck_provenance_tooltip(
        "Gross deal MOIC",
        f"{gross_moic:.2f}x",
        explainer=(
            "Gross multiple of invested capital before fees / "
            "carry. The LP/GP split visualization above shows "
            "how this number redistributes; the tier table "
            "shows the hurdle / catch-up / carry mechanics."
        ),
        inject_css=False,
    )
    kpis = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block(
            "Gross IRR", irr_value, "before fees",
            help={
                "definition": (
                    "Deal-level IRR before management fees and carry "
                    "are deducted. The 'before fees' read; LP IRR will "
                    "be 200-400 bps lower depending on fee structure "
                    "and carry waterfall mechanics."
                ),
            },
        )
        + ck_kpi_block(
            "Gross MOIC", moic_value, "before fees",
            help={
                "definition": (
                    "Multiple on invested capital before fees + carry. "
                    "Gross 3.0x typically becomes LP-net 2.4-2.6x "
                    "after a standard 2-and-20 fee structure across a "
                    "5-year hold."
                ),
            },
        )
        + ck_kpi_block("Invested", f"${invested/1e6:.0f}M", "equity check")
        + ck_kpi_block("Exit Proceeds", f"${exit_proceeds/1e6:.0f}M", "total return")
        + ck_kpi_block("Hold Period", f"{hold_years:.1f}yr", "exit year - entry")
        + '</div>'
    )

    # LP/GP split visualization
    total = lp_total + gp_total
    lp_pct = lp_total / total * 100 if total > 0 else 80
    gp_pct = 100 - lp_pct
    split = (
        f'<div class="cad-card">'
        f'<h2>LP / GP Split</h2>'
        f'<div style="display:flex;gap:4px;height:32px;border-radius:6px;overflow:hidden;margin-bottom:8px;">'
        f'<div style="width:{lp_pct:.0f}%;background:{PALETTE["brand_accent"]};" '
        f'title="LP: ${lp_total/1e6:.1f}M"></div>'
        f'<div style="width:{gp_pct:.0f}%;background:{PALETTE["positive"]};" '
        f'title="GP: ${gp_total/1e6:.1f}M"></div></div>'
        f'<div style="display:flex;gap:24px;font-size:13px;">'
        f'<div><span style="color:{PALETTE["brand_accent"]};">&#9632;</span> '
        f'<strong>LP:</strong> ${lp_total/1e6:.1f}M ({lp_moic:.2f}x MOIC, {lp_irr:.1%} IRR)</div>'
        f'<div><span style="color:{PALETTE["positive"]};">&#9632;</span> '
        f'<strong>GP:</strong> ${gp_total/1e6:.1f}M ({gp_moic:.2f}x MOIC)</div>'
        f'</div></div>'
    )

    # Tier breakdown
    tiers = result.get("tiers", [])
    tier_rows = ""
    for t in tiers:
        tier_name = html.escape(str(t.get("tier_name", t.get("name", ""))))
        lp_amt = t.get("lp_amount", t.get("lp", 0))
        gp_amt = t.get("gp_amount", t.get("gp", 0))
        hurdle = t.get("hurdle_rate", t.get("hurdle", 0))
        carry = t.get("carry_rate", t.get("carry", 0))
        tier_rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{tier_name}</td>'
            f'<td class="num">{hurdle:.1%}</td>'
            f'<td class="num">{carry:.0%}</td>'
            f'<td class="num">${float(lp_amt)/1e6:.1f}M</td>'
            f'<td class="num">${float(gp_amt)/1e6:.1f}M</td>'
            f'</tr>'
        )

    tier_section = (
        f'<div class="cad-card">'
        f'<h2>Waterfall Tiers</h2>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Tier</th><th>Hurdle</th><th>Carry</th><th>LP</th><th>GP</th>'
        f'</tr></thead><tbody>{tier_rows}</tbody></table></div>'
    ) if tier_rows else ""

    actions = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/models/lbo/{html.escape(deal_id)}" class="cad-btn" '
        f'style="text-decoration:none;">LBO Model</a>'
        f'<a href="/models/dcf/{html.escape(deal_id)}" class="cad-btn" '
        f'style="text-decoration:none;">DCF Model</a>'
        f'<a href="/analysis/{html.escape(deal_id)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Full Analysis</a></div>'
    )

    # Interpretation
    # 2026-05-28 batch 34 · Tier-4 trope removal — strip decorative
    # brand-accent stripe from the waterfall interpretation card.
    lp_share = lp_total / (lp_total + gp_total) * 100 if (lp_total + gp_total) > 0 else 80
    interp = (
        f'<div class="cad-card">'
        f'<h2>What This Means</h2>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'<p>LPs receive {lp_share:.0f}% of total distributions (${lp_total/1e6:.1f}M) '
        f'at a {lp_moic:.2f}x return on invested capital. '
        f'{"The GP carry is well-earned — strong returns." if gross_irr > 0.20 else "Consider negotiating carry terms given the return profile."}</p>'
        f'<p style="margin-top:6px;"><strong>Context:</strong> See the '
        f'<a href="/models/returns/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">returns & covenant</a> '
        f'page for IRR sensitivity and covenant headroom analysis.</p>'
        f'</div></div>'
    )

    nav = _model_nav(deal_id, "waterfall")
    next_up = ck_next_section(
        "Open the returns & covenant view",
        f"/models/returns/{html.escape(deal_id)}",
        eyebrow="Continue —",
        italic_word="returns",
    )
    # Lead takeaway — surface the computed waterfall result (gross
    # MOIC/IRR + the dollars that actually reach LPs vs GP carry) at the
    # top, before the KPI grid and the LP/GP split card. All figures
    # come from the result dict; tone tracks the gross IRR hurdle.
    _wf_tone = (
        "positive" if gross_irr > 0.20
        else "warning" if gross_irr > 0.15
        else "negative"
    )
    lead_anchor = ck_value_anchor(
        "RETURNS WATERFALL",
        f"{gross_moic:.2f}x gross MOIC",
        delta=f"{gross_irr:.1%} gross IRR",
        opportunity=f"${lp_total / 1e6:.0f}M to LPs ({lp_moic:.2f}x)",
        target=f"${gp_total / 1e6:.0f}M GP carry",
        tone=_wf_tone,
    )
    # 2026-05-28 batch 26 · Phase 3 · universal strict 5-block head.
    from ._chartis_kit import ck_editorial_head
    head = ck_editorial_head(
        eyebrow="RETURNS WATERFALL",
        title=f"Returns waterfall — {html.escape(deal_name)}",
        meta=(
            f"GROSS IRR {gross_irr:.1%} · "
            f"MOIC {gross_moic:.2f}x · "
            f"HOLD {hold_years:.1f}YR · "
            f"LP {lp_moic:.2f}x"
        ),
        lede_italic_phrase="Where the equity actually splits.",
        lede_body=(
            "Tier-by-tier waterfall from gross deal returns "
            "to LP / GP economics. Compare gross MOIC to LP "
            "net MOIC to read the fee + carry drag. The split "
            "between hurdle, catch-up, and carry tiers shows "
            "where each tier's payout sits."
        ),
    )
    body = f'{head}{nav}{lead_anchor}{kpis}{split}{interp}{tier_section}{actions}{next_up}'

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, f"Returns Waterfall — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"Gross IRR: {gross_irr:.1%} | MOIC: {gross_moic:.2f}x | Hold: {hold_years:.1f}yr")
