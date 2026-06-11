"""PE Desk PE Returns & Covenant — connects pe/pe_math.py to browser.

Shows computed returns (IRR, MOIC) and covenant headroom analysis.
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


def _covenant_runway_svg(
    actual_lev: float, max_lev: float,
    cov_ebitda: float, trips_at: float,
) -> str:
    """The leverage runway, drawn instead of described.

    A fixed scale from 0 to past the covenant ceiling: the current
    leverage as a bar toned by remaining headroom, the covenant max
    as a hard red line, and the headroom gap shaded — plus a second
    strip showing the same risk in EBITDA terms (current EBITDA vs
    the level where the covenant trips). Missing covenant data
    renders nothing.
    """
    if max_lev <= 0 or actual_lev < 0:
        return ""
    headroom = max_lev - actual_lev
    scale_max = max(max_lev * 1.2, actual_lev * 1.1)
    tone = ("#0a8a5f" if headroom > 1.5
            else "#b8732a" if headroom > 0.5 else "#b5321e")

    width, bar_h = 720, 26
    pad_l, pad_top = 8, 22
    strip2 = cov_ebitda > 0 and trips_at > 0
    height = pad_top + bar_h + 28 + ((bar_h + 34) if strip2 else 0)

    def _x(v: float) -> float:
        return pad_l + (width - 2 * pad_l) * v / scale_max

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;display:block;" role="img" '
        f'aria-label="Leverage vs covenant ceiling">'
        f'<text x="{pad_l}" y="{pad_top - 8}" font-size="9" '
        f'letter-spacing="1" fill="#7a8699">LEVERAGE RUNWAY · TURNS OF '
        f'EBITDA</text>'
        # Track to the ceiling, then the headroom zone.
        f'<rect x="{pad_l}" y="{pad_top}" '
        f'width="{_x(max_lev) - pad_l:.1f}" height="{bar_h}" rx="3" '
        f'fill="#7a8699" fill-opacity="0.12"/>'
        f'<rect x="{pad_l}" y="{pad_top}" '
        f'width="{max(_x(min(actual_lev, scale_max)) - pad_l, 2):.1f}" '
        f'height="{bar_h}" rx="3" fill="{tone}" fill-opacity="0.85"/>'
        f'<line x1="{_x(max_lev):.1f}" y1="{pad_top - 6}" '
        f'x2="{_x(max_lev):.1f}" y2="{pad_top + bar_h + 6}" '
        f'stroke="#b5321e" stroke-width="2"/>'
        f'<text x="{_x(max_lev):.1f}" y="{pad_top + bar_h + 18}" '
        f'text-anchor="middle" font-size="9.5" font-weight="700" '
        f'fill="#b5321e">COVENANT {max_lev:.1f}x</text>'
        f'<text x="{_x(actual_lev) - 6:.1f}" '
        f'y="{pad_top + bar_h / 2 + 3.5:.1f}" text-anchor="end" '
        f'font-size="11" font-weight="700" fill="#ffffff">'
        f'{actual_lev:.1f}x</text>'
        f'<text x="{_x(max_lev) + 6:.1f}" '
        f'y="{pad_top + bar_h / 2 + 3.5:.1f}" font-size="10" '
        f'fill="{tone}" font-weight="600">{headroom:.1f}x HEADROOM</text>'
    ]
    if strip2:
        y2 = pad_top + bar_h + 34
        e_max = max(cov_ebitda, trips_at) * 1.15

        def _xe(v: float) -> float:
            return pad_l + (width - 2 * pad_l) * v / e_max

        parts.append(
            f'<text x="{pad_l}" y="{y2 - 6}" font-size="9" '
            f'letter-spacing="1" fill="#7a8699">SAME RISK IN EBITDA '
            f'TERMS · COVENANT TRIPS AT ${trips_at / 1e6:.0f}M</text>'
            f'<rect x="{pad_l}" y="{y2}" '
            f'width="{_xe(cov_ebitda) - pad_l:.1f}" height="{bar_h}" '
            f'rx="3" fill="{tone}" fill-opacity="0.25"/>'
            f'<rect x="{pad_l}" y="{y2}" '
            f'width="{max(_xe(trips_at) - pad_l, 2):.1f}" '
            f'height="{bar_h}" rx="3" fill="#b5321e" fill-opacity="0.55"/>'
            f'<text x="{_xe(trips_at) + 6:.1f}" '
            f'y="{y2 + bar_h / 2 + 3.5:.1f}" font-size="10" '
            f'fill="#1a2332">cushion ${max(cov_ebitda - trips_at, 0) / 1e6:.0f}M '
            f'of ${cov_ebitda / 1e6:.0f}M EBITDA</text>'
        )
    parts.append("</svg>")
    return (
        '<div class="ck-covenant-runway" style="margin:4px 0 12px;">'
        + "".join(parts) + "</div>"
    )


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
        + ck_kpi_block(
            "IRR", irr_value, "to equity",
            help={
                "definition": (
                    "Internal rate of return on the LP equity check. "
                    "The 20% hurdle is the conventional PE healthcare "
                    "underwriting target; below 15% is below-par for "
                    "the sector and risks LP push-back on the next "
                    "fund raise."
                ),
            },
        )
        + ck_kpi_block(
            "MOIC", moic_value, "exit/entry",
            help={
                "definition": (
                    "Multiple on invested capital: exit proceeds plus "
                    "interim distributions divided by entry equity. "
                    "Less hold-period-sensitive than IRR; 2.5x in 5 "
                    "years and 2.5x in 7 years tell different IRR "
                    "stories but the same dollar-return story."
                ),
            },
        )
        + ck_kpi_block(
            "Entry Equity", f"${entry_eq/1e6:.0f}M", "LP check",
            help={
                "definition": (
                    "Total equity the LPs put up at close, after debt "
                    "financing. This is the denominator for both IRR "
                    "and MOIC: bigger entry checks need bigger exit "
                    "proceeds to hit the same multiple."
                ),
            },
        )
        + ck_kpi_block("Exit Proceeds", f"${exit_proc/1e6:.0f}M", "terminal")
        + ck_kpi_block(
            "Total Distributions", f"${total_dist/1e6:.0f}M", "interim + exit",
            help={
                "definition": (
                    "All cash returned to LPs over the hold: exit "
                    "proceeds plus any interim dividends, recaps, or "
                    "tax distributions. Used for IRR/MOIC calc; "
                    "interim distributions front-load the cash flow "
                    "and lift IRR vs. a back-loaded exit."
                ),
            },
        )
        + ck_kpi_block(
            "Hold Period", f"{hold:.1f}yr", "exit - entry",
            help={
                "definition": (
                    "Years from acquisition close to exit. PE "
                    "healthcare median is 5–6 years; below 4 is a "
                    "quick flip (often distressed or strategic "
                    "premium); above 7 typically means the thesis "
                    "took longer than planned."
                ),
            },
        )
        + '</div>'
    )

    # Interpretation
    irr_assessment = (
        "Strong: exceeds the 20% hurdle with margin"
        if irr > 0.25 else
        "Meets hurdle: passes the typical 20% IRR bar"
        if irr > 0.20 else
        "Marginal: in the 15-20% range, needs operational upside"
        if irr > 0.15 else
        "Below hurdle: requires significant value creation to meet return targets"
    )
    interp = (
        f'<div class="cad-card" style="border-left:3px solid {irr_color};">'
        f'<h2>Returns Assessment</h2>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'<p><strong>{irr_assessment}.</strong> At {irr:.1%} IRR and {moic:.2f}x MOIC over '
        f'{hold:.0f} years, every $1 invested returns ${moic:.2f}.</p>'
        f'<p style="margin-top:6px;">Entry equity of ${entry_eq/1e6:.0f}M grows to '
        f'${total_dist/1e6:.0f}M in total distributions: a ${(total_dist-entry_eq)/1e6:.0f}M gain.</p>'
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
        + _covenant_runway_svg(actual_lev, max_lev, cov_ebitda, trips_at)
        + f'<div class="cad-kpi-grid">'
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
        f'{"This is comfortable headroom." if cushion > 0.25 else "This is tight: stress test carefully." if cushion > 0.10 else "Very thin: covenant breach risk is high."}'
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
    next_up = ck_next_section(
        "Pressure-test these returns",
        "/diligence/risk-workbench?demo=steward",
        eyebrow="Up next",
        italic_word="pressure-test",
    )
    # Lead takeaway — surface the computed return (MOIC/IRR + the
    # dollar gain to LPs) at the top, before the dense KPI grid and the
    # Returns Assessment card. All figures come from the returns dict;
    # tone tracks the IRR hurdle so the band reads green/amber/red.
    _ret_tone = (
        "positive" if irr > 0.20
        else "warning" if irr > 0.15
        else "negative"
    )
    lead_anchor = ck_value_anchor(
        "PE RETURNS",
        f"{moic:.2f}x MOIC",
        delta=f"{irr:.1%} levered IRR",
        opportunity=f"${(total_dist - entry_eq) / 1e6:.0f}M total gain",
        target=f"${entry_eq / 1e6:.0f}M in → ${exit_proc / 1e6:.0f}M exit",
        tone=_ret_tone,
    )
    # 2026-05-28 batch 28 · Phase 3 · universal strict 5-block head.
    from ._chartis_kit import ck_editorial_head
    head = ck_editorial_head(
        eyebrow="PE RETURNS & COVENANTS",
        title=f"Returns & covenants · {html.escape(deal_name)}",
        meta=(
            f"IRR {irr:.1%} · "
            f"MOIC {moic:.2f}x · "
            f"COVENANT CUSHION {cushion:.0%}"
        ),
        lede_italic_phrase="Where the leverage and returns meet.",
        lede_body=(
            "Levered returns + covenant headroom in one view. "
            "The IRR / MOIC tiles read the equity outcome; "
            "the covenant tiles read structural risk. EBITDA "
            "cushion below 15% usually triggers a working-"
            "capital review."
        ),
    )
    body = f'{head}{nav}{lead_anchor}{kpis}{interp}{cov_section}{actions}{next_up}'

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, f"Returns & Covenant · {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"IRR: {irr:.1%} | MOIC: {moic:.2f}x | Covenant cushion: {cushion:.0%}")
