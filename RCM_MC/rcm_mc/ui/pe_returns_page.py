"""SeekingChartis PE Returns & Covenant — connects pe/pe_math.py to browser.

Shows computed returns (IRR, MOIC) and covenant headroom analysis.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from ._chartis_kit import (
    chartis_shell, ck_fmt_pct, ck_kpi_block, ck_provenance_tooltip,
)
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

    irr_color = PALETTE["positive"] if irr > 0.20 else (
        PALETTE["warning"] if irr > 0.15 else PALETTE["negative"])

    # Cycle 56 — port to ck_kpi_block + provenance.
    irr_value = ck_provenance_tooltip(
        "Levered IRR",
        f'<span style="color:{irr_color};">{ck_fmt_pct(irr)}</span>',
        explainer=(
            "Internal rate of return on the equity check. Above "
            "20% green (above hurdle), 15-20% amber (in carry "
            "tier but unlikely to clear catch-up), below 15% "
            "red (LP returns inadequate to justify illiquidity)."
        ),
    )
    moic_value = ck_provenance_tooltip(
        "Multiple of invested capital",
        f"{moic:.2f}x",
        explainer=(
            "Exit proceeds + interim distributions, divided by "
            "entry equity. 2.5x is rough industry median over a "
            "5-year hold; 3.0x+ is a strong outcome that "
            "anchors fund-level returns."
        ),
        inject_css=False,
    )
    kpis = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("IRR", irr_value, "to equity")
        + ck_kpi_block("MOIC", moic_value, "exit/entry")
        + ck_kpi_block("Entry Equity", f"${entry_eq/1e6:.0f}M", "LP check")
        + ck_kpi_block("Exit Proceeds", f"${exit_proc/1e6:.0f}M", "terminal")
        + ck_kpi_block("Total Distributions", f"${total_dist/1e6:.0f}M", "interim + exit")
        + ck_kpi_block("Hold Period", f"{hold:.1f}yr", "exit - entry")
        + '</div>'
    )

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

    cov_section = (
        f'<div class="cad-card">'
        f'<h2>Covenant Headroom</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:12px;">'
        f'How much EBITDA can compress before the leverage covenant trips?</p>'
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{actual_lev:.1f}x</div>'
        f'<div class="cad-kpi-label">Actual Leverage</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{max_lev:.1f}x</div>'
        f'<div class="cad-kpi-label">Covenant Max</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{headroom_color};">'
        f'{headroom:.1f}x</div><div class="cad-kpi-label">Headroom (turns)</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{cushion_color};">'
        f'{cushion:.0%}</div><div class="cad-kpi-label">EBITDA Cushion</div></div>'
        + (f'<div class="cad-kpi"><div class="cad-kpi-value">${trips_at/1e6:.0f}M</div>'
           f'<div class="cad-kpi-label">Covenant Trips at</div></div>' if trips_at > 0 else "")
        + (f'<div class="cad-kpi"><div class="cad-kpi-value">{coverage:.1f}x</div>'
           f'<div class="cad-kpi-label">Interest Coverage</div></div>' if coverage > 0 else "")
        + f'</div>'
        f'<div style="margin-top:12px;font-size:12.5px;color:{PALETTE["text_secondary"]};">'
        f'<strong>Plain English:</strong> EBITDA can decline {cushion:.0%} '
        f'(from ${cov_ebitda/1e6:.0f}M to ${trips_at/1e6:.0f}M) before the {max_lev:.1f}x leverage covenant trips. '
        f'{"This is comfortable headroom." if cushion > 0.25 else "This is tight — stress test carefully." if cushion > 0.10 else "Very thin — covenant breach risk is high."}'
        f'</div></div>'
    ) if cov_ebitda > 0 else ""

    actions = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/models/lbo/{html.escape(deal_id)}" class="cad-btn" style="text-decoration:none;">LBO Model</a>'
        f'<a href="/models/debt/{html.escape(deal_id)}" class="cad-btn" style="text-decoration:none;">Debt Schedule</a>'
        f'<a href="/models/challenge/{html.escape(deal_id)}" class="cad-btn" style="text-decoration:none;">Challenge Solver</a>'
        f'<a href="/deal/{html.escape(deal_id)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Deal Dashboard</a></div>'
    )

    nav = _model_nav(deal_id, "")
    body = f'{nav}{kpis}{interp}{cov_section}{actions}'

    return chartis_shell(body, f"Returns & Covenant — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"IRR: {irr:.1%} | MOIC: {moic:.2f}x | Covenant cushion: {cushion:.0%}",
        editorial_intro={
            "eyebrow": "PE RETURNS & COVENANTS",
            "headline": "Where the leverage and returns meet.",
            "italic_word": "meet",
            "body": (
                "Levered returns + covenant headroom in one view. "
                "The IRR / MOIC tiles read the equity outcome; "
                "the covenant tiles read structural risk. EBITDA "
                "cushion below 15% usually triggers a working-"
                "capital review."
            ),
        })
