"""SeekingChartis PE Returns & Covenant — connects pe/pe_math.py to browser.

Shows computed returns (IRR, MOIC) and covenant headroom analysis.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from ._chartis_kit import chartis_shell
from .models_page import _model_nav
from .brand import PALETTE


def render_returns_page(deal_id: str, deal_name: str, returns: Dict[str, Any],
                        covenant: Dict[str, Any]) -> str:
    """Render PE returns + covenant analysis."""
    # Returns section
    irr = returns.get("irr", 0)
    moic = returns.get("moic", 0)
    entry_eq = returns.get("entry_equity", 0)
    exit_proc = returns.get("exit_proceeds", 0)
    hold = returns.get("hold_years", 5)
    total_dist = returns.get("total_distributions", 0)

    # P26 follow-up: kpi_strip migration. The IRR-band logic that
    # previously coloured the IRR cell now flows through the strip's
    # ``tone`` field instead of an inline style attribute. The
    # legacy ``irr_color`` variable is preserved because the
    # downstream Returns Assessment card reads it for its border.
    from ._ui_kit import format_value, kpi_strip

    irr_color = PALETTE["positive"] if irr > 0.20 else (
        PALETTE["warning"] if irr > 0.15 else PALETTE["negative"])
    irr_tone = (
        "positive" if irr > 0.20
        else "warning" if irr > 0.15
        else "negative"
    )
    kpis = kpi_strip([
        {"label": "IRR", "value": format_value(irr, kind="percent"),
         "tone": irr_tone},
        {"label": "MOIC", "value": format_value(moic, kind="multiple")},
        {"label": "ENTRY EQUITY",
         "value": format_value(entry_eq, kind="money")},
        {"label": "EXIT PROCEEDS",
         "value": format_value(exit_proc, kind="money")},
        {"label": "TOTAL DISTRIBUTIONS",
         "value": format_value(total_dist, kind="money")},
        {"label": "HOLD PERIOD", "value": f"{hold:.1f}yr"},
    ])

    # Interpretation
    irr_assessment = (
        "Strong — exceeds the 20% hurdle with margin"
        if irr > 0.25 else
        "Meets hurdle — passes the typical 20% IRR bar"
        if irr > 0.20 else
        "Marginal — in the 15-20% range, needs operational upside"
        if irr > 0.15 else
        "Below hurdle — requires significant value creation to meet return targets"
    )
    interp = (
        f'<div class="cad-card" style="border-left:3px solid {irr_color};">'
        f'<h2>Returns Assessment</h2>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'<p><strong>{irr_assessment}.</strong> At {irr:.1%} IRR and {moic:.2f}x MOIC over '
        f'{hold:.0f} years, every $1 invested returns ${moic:.2f}.</p>'
        f'<p style="margin-top:6px;">Entry equity of ${entry_eq/1e6:.0f}M grows to '
        f'${total_dist/1e6:.0f}M in total distributions — a ${(total_dist-entry_eq)/1e6:.0f}M gain.</p>'
        f'</div></div>'
    )

    # Covenant section
    cov_ebitda = covenant.get("ebitda", 0)
    cov_debt = covenant.get("debt", 0)
    actual_lev = covenant.get("actual_leverage", 0)
    max_lev = covenant.get("covenant_max_leverage", 0)
    headroom = covenant.get("covenant_headroom_turns", 0)
    cushion = covenant.get("ebitda_cushion_pct", 0)
    trips_at = covenant.get("covenant_trips_at_ebitda", 0)
    coverage = covenant.get("interest_coverage", 0)

    headroom_color = PALETTE["positive"] if headroom > 1.5 else (
        PALETTE["warning"] if headroom > 0.5 else PALETTE["negative"])
    cushion_color = PALETTE["positive"] if cushion > 0.25 else (
        PALETTE["warning"] if cushion > 0.10 else PALETTE["negative"])

    headroom_tone = (
        "positive" if headroom > 1.5
        else "warning" if headroom > 0.5
        else "negative"
    )
    cushion_tone = (
        "positive" if cushion > 0.25
        else "warning" if cushion > 0.10
        else "negative"
    )
    cov_items = [
        {"label": "Actual Leverage", "value": f"{actual_lev:.1f}x"},
        {"label": "Covenant Max",    "value": f"{max_lev:.1f}x"},
        {"label": "Headroom (turns)",
         "value": f"{headroom:.1f}x", "tone": headroom_tone},
        {"label": "EBITDA Cushion",
         "value": f"{cushion:.0%}", "tone": cushion_tone},
    ]
    if trips_at > 0:
        cov_items.append({
            "label": "Covenant Trips at",
            "value": f"${trips_at/1e6:.0f}M",
        })
    if coverage > 0:
        cov_items.append({
            "label": "Interest Coverage",
            "value": f"{coverage:.1f}x",
        })

    cov_section = (
        f'<div class="cad-card">'
        f'<h2>Covenant Headroom</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:12px;">'
        f'How much EBITDA can compress before the leverage covenant trips?</p>'
        + kpi_strip(cov_items)
        + f'<div style="margin-top:12px;font-size:12.5px;color:{PALETTE["text_secondary"]};">'
        + f'<strong>Plain English:</strong> EBITDA can decline {cushion:.0%} '
        + f'(from ${cov_ebitda/1e6:.0f}M to ${trips_at/1e6:.0f}M) before the {max_lev:.1f}x leverage covenant trips. '
        + f'{"This is comfortable headroom." if cushion > 0.25 else "This is tight — stress test carefully." if cushion > 0.10 else "Very thin — covenant breach risk is high."}'
        + f'</div></div>'
    ) if cov_ebitda > 0 else ""

    actions = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/models/lbo/{html.escape(deal_id)}" class="cad-btn" style="text-decoration:none;">LBO Model</a>'
        f'<a href="/models/debt/{html.escape(deal_id)}" class="cad-btn" style="text-decoration:none;">Debt Schedule</a>'
        f'<a href="/models/challenge/{html.escape(deal_id)}" class="cad-btn" style="text-decoration:none;">Challenge Solver</a>'
        f'<a href="/deal/{html.escape(deal_id)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">View deal dashboard</a></div>'
    )

    nav = _model_nav(deal_id, "")
    body = f'{nav}{kpis}{interp}{cov_section}{actions}'

    return chartis_shell(body, f"Returns & Covenant — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"IRR: {irr:.1%} | MOIC: {moic:.2f}x | Covenant cushion: {cushion:.0%}")
