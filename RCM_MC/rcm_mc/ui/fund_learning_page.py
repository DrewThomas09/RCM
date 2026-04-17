"""SeekingChartis Fund Learning Dashboard — cross-deal accuracy.

Shows the compounding moat: every closed deal improves the next
underwrite. Displays fund-level bridge realization, per-lever bias,
adjustment factors, and the accuracy narrative for LP reporting.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from .shell_v2 import shell_v2
from .brand import PALETTE


def _fm(val: float) -> str:
    if abs(val) >= 1e9:
        return f"${val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val/1e6:.1f}M"
    if abs(val) >= 1e3:
        return f"${val/1e3:.0f}K"
    return f"${val:,.0f}"


def render_fund_learning(db_path: str) -> str:
    """Render the fund learning dashboard."""
    from ..ml.fund_learning import compute_fund_accuracy

    accuracy = compute_fund_accuracy(db_path)

    if not accuracy:
        return shell_v2(
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

    kpis = (
        f'<div class="cad-kpi-grid" style="grid-template-columns:repeat(4,1fr);">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{accuracy.n_closed_deals}</div>'
        f'<div class="cad-kpi-label">Deals with Data</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fm(accuracy.total_planned)}</div>'
        f'<div class="cad-kpi-label">Total Planned</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{r_color};">'
        f'{_fm(accuracy.total_realized)}</div>'
        f'<div class="cad-kpi-label">Total Realized</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{r_color};">'
        f'{accuracy.fund_realization_pct:.0%}</div>'
        f'<div class="cad-kpi-label">Fund Realization</div></div>'
        f'</div>'
    )

    # Narrative
    narrative = (
        f'<div class="cad-card" style="border-left:3px solid var(--cad-accent);">'
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
            f'<table class="cad-table"><thead><tr>'
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

    body = f'{kpis}{narrative}{lever_section}{flywheel}{nav}'

    return shell_v2(
        body, "Fund Learning",
        active_nav="/pipeline",
        subtitle=(
            f"{accuracy.n_closed_deals} deals | "
            f"{accuracy.fund_realization_pct:.0%} realization | "
            f"{len(accuracy.lever_biases)} levers tracked"
        ),
    )
