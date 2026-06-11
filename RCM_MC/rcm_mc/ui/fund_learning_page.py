"""PE Desk Fund Learning Dashboard — cross-deal accuracy.

Shows the compounding moat: every closed deal improves the next
underwrite. Displays fund-level bridge realization, per-lever bias,
adjustment factors, and the accuracy narrative for LP reporting.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from ._chartis_kit import (
    chartis_shell, ck_fmt_num, ck_fmt_pct, ck_kpi_block,
    ck_next_section, ck_provenance_tooltip, ck_value_anchor,
)
from .brand import PALETTE


def _fm(val: float) -> str:
    if abs(val) >= 1e9:
        return f"${val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val/1e6:.1f}M"
    if abs(val) >= 1e3:
        return f"${val/1e3:.0f}K"
    return f"${val:,.0f}"


def _lever_realization_svg(lever_biases: list) -> str:
    """Planned vs realized per lever, as geometry not arithmetic.

    For each lever: the planned uplift as a hollow track and the
    realized dollars as a filled bar on the same axis, toned by the
    page's realization bands (≥85% green / ≥60% amber / below red) —
    so "we planned $4M from denial recovery and got $1.5M" reads as a
    visible shortfall instead of two table columns. Sorted by planned
    size. Levers with zero plan are skipped; nothing renders nothing.
    """
    rows = [
        (str(b.lever), float(b.planned_total), float(b.actual_total),
         float(b.realization_pct))
        for b in lever_biases
        if float(getattr(b, "planned_total", 0) or 0) > 0
    ]
    if not rows:
        return ""
    rows.sort(key=lambda r: -r[1])
    max_v = max(max(p, a) for _, p, a, _ in rows)

    label_w, bar_w_max, right_w = 190, 360, 110
    row_h, gap, pad_top, pad_bot = 20, 8, 8, 8
    width = label_w + bar_w_max + right_w
    height = pad_top + len(rows) * (row_h + gap) - gap + pad_bot

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;display:block;" role="img" '
        f'aria-label="Planned vs realized EBITDA uplift per lever">'
    ]
    for i, (lever, planned, actual, r_pct) in enumerate(rows):
        y = pad_top + i * (row_h + gap)
        ty = y + row_h / 2 + 3.5
        tone = ("#0a8a5f" if r_pct >= 0.85
                else "#b8732a" if r_pct >= 0.60 else "#b5321e")
        short = lever if len(lever) <= 25 else lever[:24] + "…"
        parts.append(
            f'<text x="{label_w - 8}" y="{ty:.1f}" text-anchor="end" '
            f'font-size="10.5" fill="#465366">{_html.escape(short)}</text>'
        )
        pw = max(2.0, bar_w_max * planned / max_v)
        parts.append(
            f'<rect x="{label_w}" y="{y}" width="{pw:.1f}" '
            f'height="{row_h}" rx="2" fill="none" stroke="#9b9382" '
            f'stroke-width="1" stroke-dasharray="3,2"/>'
        )
        aw = max(2.0, bar_w_max * max(actual, 0) / max_v)
        parts.append(
            f'<rect x="{label_w}" y="{y + 3}" width="{aw:.1f}" '
            f'height="{row_h - 6}" rx="2" fill="{tone}" '
            f'fill-opacity="0.85"/>'
        )
        parts.append(
            f'<text x="{label_w + max(pw, aw) + 6:.1f}" y="{ty:.1f}" '
            f'font-size="10" font-weight="600" fill="{tone}">'
            f'{r_pct:.0%} of {_fm(planned)}</text>'
        )
    parts.append("</svg>")
    note = (
        '<p style="font-size:10px;color:var(--cad-text3);'
        'letter-spacing:0.06em;margin:4px 0 0;">'
        'DASHED OUTLINE = PLANNED UPLIFT · FILLED BAR = REALIZED · '
        'TONE = REALIZATION BAND (≥85% / ≥60% / BELOW)</p>'
    )
    return (
        '<div class="ck-lever-realization" style="margin:4px 0 12px;">'
        + "".join(parts) + note + "</div>"
    )


def render_fund_learning(db_path: str) -> str:
    """Render the fund learning dashboard."""
    from ..ml.fund_learning import compute_fund_accuracy

    accuracy = compute_fund_accuracy(db_path)

    if not accuracy:
        return chartis_shell(
            '<div class="cad-card">'
            '<h2>Fund Learning</h2>'
            '<p style="color:var(--cad-text2);font-size:13px;margin-bottom:12px;">'
            'No value creation plans exist yet. Freeze an EBITDA bridge as a plan '
            'and record quarterly actuals to start building the fund\'s learning history.</p>'
            '<div style="display:flex;gap:8px;">'
            '<a href="/predictive-screener" class="cad-btn cad-btn-primary" '
            'style="text-decoration:none;">Find Deals</a>'
            '<a href="/pipeline" class="cad-btn" style="text-decoration:none;">Pipeline</a>'
            '</div></div>',
            "Fund Learning",
            subtitle="No value creation data yet",
        )

    # KPIs
    r_color = "var(--cad-pos)" if accuracy.fund_realization_pct >= 0.80 else (
        "var(--cad-warn)" if accuracy.fund_realization_pct >= 0.60 else "var(--cad-neg)")

    # Cycle 53 — port to ck_kpi_block + provenance.
    realization_value = ck_provenance_tooltip(
        "Fund realization rate",
        f'<span style="color:{r_color};">{ck_fmt_pct(accuracy.fund_realization_pct)}</span>',
        explainer=(
            f"Realized vs. planned EBITDA uplift across "
            f"{accuracy.n_closed_deals} closed deals. Above 80% "
            f"green (track record holds); below 60% red (the "
            f"fund is over-projecting underwriting). The lever-"
            f"bias table below decomposes this by lever."
        ),
    )
    kpis = (
        '<div class="ck-kpi-grid" style="grid-template-columns:repeat(4,1fr);">'
        + ck_kpi_block("Deals with Data", ck_fmt_num(accuracy.n_closed_deals), "in fund history")
        + ck_kpi_block("Total Planned", _fm(accuracy.total_planned), "EBITDA uplift")
        + ck_kpi_block("Total Realized", f'<span style="color:{r_color};">{_fm(accuracy.total_realized)}</span>',
                       "vs underwriting")
        + ck_kpi_block("Fund Realization", realization_value, "calibration signal")
        + '</div>'
    )

    # Narrative
    # 2026-05-28 batch 30 · Tier-4 trope removal — drops decorative
    # 3px accent stripe.
    narrative = (
        f'<div class="cad-card">'
        f'<h2>Fund Learning Summary</h2>'
        f'<p style="font-size:13px;color:var(--cad-text2);line-height:1.7;">'
        f'{_html.escape(accuracy.narrative)}</p></div>'
    )

    # Lever bias table
    lever_rows = ""
    for b in accuracy.lever_biases:
        r_pct = b.realization_pct
        r_color_l = "var(--cad-pos)" if r_pct >= 0.85 else (
            "var(--cad-warn)" if r_pct >= 0.60 else "var(--cad-neg)")
        bias_badge = {
            "accurate": ('<span style="color:var(--cad-pos);font-weight:600;">Accurate</span>'),
            "overestimates": ('<span style="color:var(--cad-neg);font-weight:600;">Overestimates</span>'),
            "underestimates": ('<span style="color:var(--cad-accent);font-weight:600;">Underestimates</span>'),
        }.get(b.bias_direction, "")

        adj_str = f"{b.adjustment_factor:.2f}x"
        adj_color = "var(--cad-text2)" if 0.9 <= b.adjustment_factor <= 1.1 else (
            "var(--cad-neg)" if b.adjustment_factor < 0.9 else "var(--cad-accent)")

        lever_rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{_html.escape(b.lever[:25])}</td>'
            f'<td class="num">{_fm(b.planned_total)}</td>'
            f'<td class="num">{_fm(b.actual_total)}</td>'
            f'<td class="num" style="color:{r_color_l};font-weight:600;">{r_pct:.0%}</td>'
            f'<td>{bias_badge}</td>'
            f'<td class="num" style="color:{adj_color};">{adj_str}</td>'
            f'<td class="num">{b.n_deals}</td>'
            f'</tr>'
        )

    lever_section = ""
    if lever_rows:
        lever_section = (
            f'<div class="cad-card">'
            f'<h2>Per-Lever Accuracy & Bias</h2>'
            f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:8px;">'
            f'Adjustment factors are applied to future bridge predictions automatically. '
            f'A factor of 0.82x means the model overestimates this lever by 18%.</p>'
            + _lever_realization_svg(accuracy.lever_biases)
            + f'<table class="cad-table"><thead><tr>'
            f'<th>Lever</th><th>Planned</th><th>Actual</th><th>Realization</th>'
            f'<th>Bias</th><th>Adj Factor</th><th>Deals</th>'
            f'</tr></thead><tbody>{lever_rows}</tbody></table></div>'
        )

    # Flywheel explanation
    flywheel = (
        f'<div class="cad-card" style="border-left:3px solid var(--cad-pos);">'
        f'<h2>The Compounding Moat</h2>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;'
        f'font-size:12.5px;color:var(--cad-text2);line-height:1.7;">'
        f'<div>'
        f'<div style="font-weight:600;color:var(--cad-accent);margin-bottom:4px;">'
        f'1. Underwrite</div>'
        f'EBITDA bridge models improvement potential. ML predicts realization rate. '
        f'Bridge is frozen as the value creation plan at close.</div>'
        f'<div>'
        f'<div style="font-weight:600;color:var(--cad-accent);margin-bottom:4px;">'
        f'2. Track</div>'
        f'Quarterly actuals recorded per lever. Realization computed against plan. '
        f'Deviations flagged in portfolio monitor.</div>'
        f'<div>'
        f'<div style="font-weight:600;color:var(--cad-accent);margin-bottom:4px;">'
        f'3. Learn</div>'
        f'Systematic biases detected across closed deals. Adjustment factors applied '
        f'to future bridge predictions. Each deal makes the next underwrite better.</div>'
        f'</div></div>'
    )

    # Nav
    nav = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/pipeline" class="cad-btn cad-btn-primary" style="text-decoration:none;">Pipeline</a>'
        f'<a href="/pipeline/bridge" class="cad-btn" style="text-decoration:none;">Portfolio Bridge</a>'
        f'<a href="/model-validation" class="cad-btn" style="text-decoration:none;">Model Validation</a>'
        f'<a href="/portfolio/monitor" class="cad-btn" style="text-decoration:none;">Portfolio Monitor</a>'
        f'</div>'
    )

    next_up = ck_next_section(
        "Open the model validation surface",
        "/model-validation",
        eyebrow="Up next",
        italic_word="validation",
    )
    # Lead takeaway — surface the fund's calibration signal (realized
    # vs planned EBITDA uplift across closed deals) at the top, before
    # the KPI grid and the lever-bias table. Tone tracks the 80%/60%
    # realization bands.
    _fl_tone = (
        "positive" if accuracy.fund_realization_pct >= 0.80
        else "warning" if accuracy.fund_realization_pct >= 0.60
        else "negative"
    )
    lead_anchor = ck_value_anchor(
        "FUND CALIBRATION",
        f"{_fm(accuracy.total_realized)} realized",
        delta=f"{accuracy.fund_realization_pct:.0%} of plan",
        opportunity=f"{_fm(accuracy.total_planned)} planned uplift",
        target=f"{accuracy.n_closed_deals} closed deals",
        tone=_fl_tone,
    )
    # 2026-05-28 batch 28 · Phase 3 · universal strict 5-block head.
    from ._chartis_kit import ck_editorial_head
    head = ck_editorial_head(
        eyebrow="PORTFOLIO · FUND LEARNING",
        title="Fund Learning",
        meta=(
            f"{accuracy.n_closed_deals} CLOSED DEAL"
            f"{'S' if accuracy.n_closed_deals != 1 else ''} · "
            f"{accuracy.fund_realization_pct:.0%} REALIZATION · "
            f"{len(accuracy.lever_biases)} LEVERS TRACKED"
        ),
        lede_italic_phrase=(
            "Per-fund lever biases learned from realized "
            "outcomes vs. underwriting projections."
        ),
        lede_body=(
            "Use this "
            "to calibrate the next deal's bridge — if your "
            "fund consistently over-projects RCM uplift by "
            "20%, the next underwriting should reflect that."
        ),
    )
    body = f'{head}{lead_anchor}{kpis}{narrative}{lever_section}{flywheel}{nav}{next_up}'

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body, "Fund Learning",
        active_nav="/pipeline",
        subtitle=(
            f"{accuracy.n_closed_deals} deals | "
            f"{accuracy.fund_realization_pct:.0%} realization | "
            f"{len(accuracy.lever_biases)} levers tracked"
        ),
    )
