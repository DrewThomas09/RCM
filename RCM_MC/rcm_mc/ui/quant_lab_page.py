"""PE Desk Quant Lab — full quant stack in browser.

Surfaces Bayesian calibration, DEA efficiency frontier, queueing theory,
survival analysis, market intelligence, causal inference, and cross-deal
learning. The complete analytical moat in one page.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_next_section, ck_panel,
    ck_section_intro,
)
from .brand import PALETTE


def _fmt(val: float, kind: str = "num") -> str:
    if kind == "pct":
        return f"{val:.1%}"
    if kind == "money":
        if abs(val) >= 1e9:
            return f"${val/1e9:.2f}B"
        if abs(val) >= 1e6:
            return f"${val/1e6:.1f}M"
        return f"${val:,.0f}"
    if kind == "days":
        return f"{val:.1f}d"
    return f"{val:,.1f}"


_QUANT_CACHE: dict = {}


def _dea_frontier_scatter(eff_scores: List[Any]) -> str:
    """SVG scatter: opex (input) on x-axis vs. NPR (output) on y-axis,
    one dot per hospital. Color-coded by efficiency score; frontier
    hospitals (score ≥ 0.95) drawn as stars on top.

    This is THE canonical DEA visualization — partners see the
    efficient envelope curve at the top-left, with everyone else
    falling away. Bubble color shifts from green (frontier) → amber
    (mid) → red (bottom 30%) so the inefficiency is visible
    even without reading the score.
    """
    points = []
    for s in eff_scores:
        inp = s.input_levels.get("operating_expenses")
        out = s.output_levels.get("net_patient_revenue")
        if inp is None or out is None or inp <= 0 or out <= 0:
            continue
        points.append((float(inp), float(out), s))
    if not points:
        return ""

    width = 720
    height = 380
    pad_l, pad_r, pad_t, pad_b = 64, 24, 32, 48
    inner_w = width - pad_l - pad_r
    inner_h = height - pad_t - pad_b

    # Log-scale both axes since hospital sizes span ~4 orders of
    # magnitude — linear would crush everything in the corner.
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    log_xs = [_np_log(v) for v in xs]
    log_ys = [_np_log(v) for v in ys]
    x_lo, x_hi = min(log_xs), max(log_xs)
    y_lo, y_hi = min(log_ys), max(log_ys)
    # Pad the bounds 5%
    x_pad = (x_hi - x_lo) * 0.05 or 0.5
    y_pad = (y_hi - y_lo) * 0.05 or 0.5
    x_lo -= x_pad
    x_hi += x_pad
    y_lo -= y_pad
    y_hi += y_pad

    def sx(v: float) -> float:
        return pad_l + (_np_log(v) - x_lo) / (x_hi - x_lo) * inner_w

    def sy(v: float) -> float:
        return pad_t + inner_h - (_np_log(v) - y_lo) / (y_hi - y_lo) * inner_h

    # Axis ticks at 10^k that fall in range
    import math as _math
    def _decades(lo: float, hi: float) -> list:
        out = []
        k = int(_math.floor(lo / _math.log(10)))
        while k * _math.log(10) <= hi:
            v = 10.0 ** k
            if _math.log(v) >= lo:
                out.append(v)
            k += 1
        return out

    def _fmt_money(v: float) -> str:
        if v >= 1e9:
            return f"${v/1e9:.0f}B"
        if v >= 1e6:
            return f"${v/1e6:.0f}M"
        if v >= 1e3:
            return f"${v/1e3:.0f}K"
        return f"${v:.0f}"

    grid = []
    for v in _decades(x_lo, x_hi):
        x = sx(v)
        grid.append(
            f'<line x1="{x:.1f}" x2="{x:.1f}" '
            f'y1="{pad_t}" y2="{pad_t + inner_h}" '
            f'stroke="#d6cfc0" stroke-dasharray="2,4" />'
            f'<text x="{x:.1f}" y="{pad_t + inner_h + 14}" '
            f'fill="#7a8699" text-anchor="middle" font-size="10" '
            f'font-family="JetBrains Mono, monospace">'
            f'{_fmt_money(v)}</text>'
        )
    for v in _decades(y_lo, y_hi):
        y = sy(v)
        grid.append(
            f'<line x1="{pad_l}" x2="{pad_l + inner_w}" '
            f'y1="{y:.1f}" y2="{y:.1f}" '
            f'stroke="#d6cfc0" stroke-dasharray="2,4" />'
            f'<text x="{pad_l - 6}" y="{y + 3:.1f}" '
            f'fill="#7a8699" text-anchor="end" font-size="10" '
            f'font-family="JetBrains Mono, monospace">'
            f'{_fmt_money(v)}</text>'
        )

    # Plot non-frontier dots first (background), then frontier stars
    # on top so they pop visually.
    dots = []
    stars = []
    for inp, out, s in points:
        cx = sx(inp)
        cy = sy(out)
        score = float(s.efficiency_score)
        if s.is_frontier:
            # 4-pointed star marker for frontier
            size = 6
            stars.append(
                f'<polygon points="'
                f'{cx:.1f},{cy - size:.1f} '
                f'{cx + size*0.4:.1f},{cy - size*0.4:.1f} '
                f'{cx + size:.1f},{cy:.1f} '
                f'{cx + size*0.4:.1f},{cy + size*0.4:.1f} '
                f'{cx:.1f},{cy + size:.1f} '
                f'{cx - size*0.4:.1f},{cy + size*0.4:.1f} '
                f'{cx - size:.1f},{cy:.1f} '
                f'{cx - size*0.4:.1f},{cy - size*0.4:.1f}" '
                f'fill="#0a8a5f" stroke="#fff" stroke-width="1.2">'
                f'<title>★ {_html.escape(s.hospital_name)} '
                f'(efficiency {score:.2f}) — on the frontier</title>'
                f'</polygon>'
            )
        else:
            color = (
                "#b8732a" if score >= 0.5
                else "#b5321e" if score >= 0.3
                else "#7a3478"
            )
            dots.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.5" '
                f'fill="{color}" fill-opacity="0.55" '
                f'stroke="none">'
                f'<title>{_html.escape(s.hospital_name)} '
                f'(efficiency {score:.2f})</title>'
                f'</circle>'
            )

    axis_labels = (
        f'<text x="{pad_l + inner_w / 2:.1f}" y="{height - 8}" '
        f'fill="#1a2332" text-anchor="middle" font-size="12" '
        f'font-family="Inter, sans-serif" font-weight="600">'
        f'Operating expenses (log scale)</text>'
        f'<text x="14" y="{pad_t + inner_h/2:.1f}" '
        f'fill="#1a2332" text-anchor="middle" font-size="12" '
        f'font-family="Inter, sans-serif" font-weight="600" '
        f'transform="rotate(-90 14 {pad_t + inner_h/2:.1f})">'
        f'Net patient revenue (log scale)</text>'
    )

    legend = (
        f'<text x="{pad_l + inner_w - 12}" y="{pad_t + 14}" '
        f'fill="#0a8a5f" text-anchor="end" font-size="10" '
        f'font-family="Inter, sans-serif" font-weight="600" '
        f'fill-opacity="0.85">★ FRONTIER (top-left envelope)</text>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;background:transparent;'
        f'margin:8px 0 16px;">'
        f'{"".join(grid)}'
        f'{"".join(dots)}'
        f'{"".join(stars)}'
        f'{axis_labels}'
        f'{legend}'
        f'</svg>'
    )


def _queue_utilization_chart(queues: List[Any], width: int = 720,
                             height: int = 220) -> str:
    """Horizontal utilization bars per queue, tone-coded by threshold.

    >85% util → red (over capacity)
    >70% util → amber (warning)
    else      → teal-deep (healthy)
    Dashed reference line at 70% (warn threshold) and 85% (danger).
    """
    if not queues:
        return ""
    pad_l, pad_r, pad_t, pad_b = 170, 90, 26, 32
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    n = len(queues)
    row_h = plot_h / n

    bars_svg = ""
    for i, q in enumerate(queues):
        util = float(getattr(q, "utilization", 0))
        cy = pad_t + row_h * i + row_h / 2
        bw = max(0, min(1.0, util)) * plot_w
        fill = (
            "#A53A2D" if util > 0.85
            else "#b8732a" if util > 0.70
            else "#155752"
        )
        wait = float(getattr(q, "avg_wait_time", 0))
        bars_svg += (
            f'<text x="{pad_l - 10}" y="{cy + 3:.1f}" '
            f'font-family="Inter Tight,sans-serif" font-size="11" '
            f'font-weight="600" fill="#1a2332" text-anchor="end">'
            f'{_html.escape(getattr(q, "queue_name", ""))}</text>'
            f'<rect x="{pad_l}" y="{cy - row_h * 0.28:.1f}" '
            f'width="{bw:.1f}" height="{row_h * 0.54:.1f}" '
            f'fill="{fill}" opacity="0.9" rx="1"/>'
            f'<text x="{pad_l + bw + 6:.1f}" y="{cy + 4:.1f}" '
            f'font-family="JetBrains Mono,monospace" font-size="10.5" '
            f'font-weight="700" fill="#1a2332">'
            f'{util * 100:.0f}%</text>'
            f'<text x="{pad_l + bw + 6:.1f}" y="{cy + 16:.1f}" '
            f'font-family="JetBrains Mono,monospace" font-size="9" '
            f'fill="#5C6878">'
            f'{wait:.1f}d wait</text>'
        )

    # Threshold reference lines at 70% and 85%
    warn_x = pad_l + 0.70 * plot_w
    danger_x = pad_l + 0.85 * plot_w
    threshold_svg = (
        f'<line x1="{warn_x:.1f}" y1="{pad_t}" x2="{warn_x:.1f}" '
        f'y2="{pad_t + plot_h}" stroke="#b8732a" stroke-width="1" '
        f'stroke-dasharray="3,2" opacity="0.7"/>'
        f'<text x="{warn_x:.1f}" y="{pad_t - 6}" '
        f'font-family="Inter Tight,sans-serif" font-size="9" '
        f'font-weight="700" letter-spacing="0.06em" '
        f'fill="#b8732a" text-anchor="middle">70%</text>'
        f'<line x1="{danger_x:.1f}" y1="{pad_t}" x2="{danger_x:.1f}" '
        f'y2="{pad_t + plot_h}" stroke="#A53A2D" stroke-width="1" '
        f'stroke-dasharray="3,2" opacity="0.7"/>'
        f'<text x="{danger_x:.1f}" y="{pad_t - 6}" '
        f'font-family="Inter Tight,sans-serif" font-size="9" '
        f'font-weight="700" letter-spacing="0.06em" '
        f'fill="#A53A2D" text-anchor="middle">85%</text>'
    )

    # x-axis ticks at 0/25/50/75/100%
    tick_svg = ""
    for pct in (0, 25, 50, 75, 100):
        tx = pad_l + (pct / 100) * plot_w
        tick_svg += (
            f'<line x1="{tx:.1f}" y1="{pad_t + plot_h}" x2="{tx:.1f}" '
            f'y2="{pad_t + plot_h + 4}" stroke="#BFB6A2" stroke-width="0.8"/>'
            f'<text x="{tx:.1f}" y="{pad_t + plot_h + 16}" '
            f'font-family="JetBrains Mono,monospace" font-size="9" '
            f'fill="#5C6878" text-anchor="middle">{pct}%</text>'
        )

    base_svg = (
        f'<line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{pad_l + plot_w}" '
        f'y2="{pad_t + plot_h}" stroke="#BFB6A2" stroke-width="1"/>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="width:100%;max-width:{width}px;height:auto;display:block;'
        f'margin:0 auto 1rem;">'
        f'{threshold_svg}{bars_svg}{base_svg}{tick_svg}</svg>'
    )


_QL_CHART_CAPTION_CSS = """
<style>
.ql-chart-caption {
  font-family: "Inter Tight","Inter",sans-serif;
  font-size: .72rem; color: #5C6878;
  text-align: center; letter-spacing: 0.06em;
  text-transform: uppercase; margin: -.5rem 0 1.25rem;
}
@media print {
  .ql-chart-caption { color: #1a2332; }
  svg { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
</style>
"""


def _np_log(v: float) -> float:
    """Wrapper used so callers can override for tests; pulls in math."""
    import math
    return math.log(v) if v > 0 else 0.0


def render_quant_lab(hcris_df: pd.DataFrame) -> str:
    """Render the Quant Lab national dashboard."""
    from ..ml.efficiency_frontier import compute_efficiency_frontier
    from ..ml.market_intelligence import compute_state_markets
    from ..ml.distress_predictor import train_distress_model
    from ..ml.queueing_model import analyze_rcm_operations

    # Cache expensive computations (invalidated by server restart)
    cache_key = len(hcris_df)
    if cache_key not in _QUANT_CACHE:
        _QUANT_CACHE[cache_key] = {
            "eff": compute_efficiency_frontier(hcris_df),
            "markets": compute_state_markets(hcris_df),
            "distress": train_distress_model(hcris_df),
        }
    cached = _QUANT_CACHE[cache_key]

    # ── DEA Efficiency Frontier ──
    df_eff, eff_scores = cached["eff"]
    frontier_count = sum(1 for s in eff_scores if s.is_frontier)
    bottom_count = sum(1 for s in eff_scores if s.efficiency_score < 0.3)

    eff_rows = ""
    for s in eff_scores[:20]:
        sc = s.efficiency_score
        sc_cls = "cad-pos" if sc >= 0.8 else ("cad-warn" if sc >= 0.5 else "cad-neg")
        eff_rows += (
            f'<tr>'
            f'<td><a href="/hospital/{_html.escape(s.ccn)}" class="ck-link">'
            f'{_html.escape(s.hospital_name)}</a></td>'
            f'<td>{_html.escape(s.state)}</td>'
            f'<td class="num {sc_cls}"><strong>{sc:.3f}</strong></td>'
            f'<td class="num">P{s.efficiency_percentile:.0f}</td>'
            f'<td>{"&#9733;" if s.is_frontier else ""}</td>'
            f'</tr>'
        )

    eff_scatter = _dea_frontier_scatter(eff_scores)
    eff_section = ck_panel(
        '<p class="ck-section-body">'
        f'Data Envelopment Analysis: {frontier_count} hospitals on the efficient frontier, '
        f'{bottom_count} in the bottom 30%. Inputs: beds + operating expenses. '
        'Outputs: net patient revenue + patient days. Frontier (★) is '
        'the top-left envelope — hospitals producing the most revenue '
        'per dollar of input.</p>'
        f'{eff_scatter}'
        '<table class="cad-table"><thead><tr>'
        '<th>Hospital</th><th>State</th><th>Efficiency</th><th>Percentile</th><th>Frontier</th>'
        f'</tr></thead><tbody>{eff_rows}</tbody></table>',
        title="Operational Efficiency Frontier (DEA)",
    )

    # ── Market Intelligence ──
    markets = cached["markets"]
    mkt_rows = ""
    for m in markets[:20]:
        inv_cls = "cad-pos" if m.investability_grade in ("A", "B") else (
            "cad-warn" if m.investability_grade == "C" else "cad-neg")
        mkt_rows += (
            f'<tr>'
            f'<td><a href="/market-data/state/{_html.escape(m.state)}" class="ck-link">{_html.escape(m.state)}</a></td>'
            f'<td class="num">{m.n_hospitals}</td>'
            f'<td class="num">{_fmt(m.total_revenue, "money")}</td>'
            f'<td class="num">{m.median_margin:.1%}</td>'
            f'<td class="num">{m.hhi:,.0f}</td>'
            f'<td>{_html.escape(m.market_concentration[:12])}</td>'
            f'<td class="num {inv_cls}"><strong>{m.investability_score:.0f} ({m.investability_grade})</strong></td>'
            f'<td class="num cad-neg">{m.distress_rate:.0%}</td>'
            f'</tr>'
        )

    mkt_section = ck_panel(
        '<p class="ck-section-body">'
        f'{len(markets)} markets analyzed. HHI (Herfindahl-Hirschman Index) measures concentration: '
        '&gt;2500 = highly concentrated, &gt;1500 = moderate. Investability combines market depth, '
        'growth, health, and payer quality.</p>'
        '<table class="cad-table"><thead><tr>'
        '<th>State</th><th>Hospitals</th><th>Revenue</th><th>Median Margin</th>'
        '<th>HHI</th><th>Concentration</th><th>Investability</th><th>Distress</th>'
        f'</tr></thead><tbody>{mkt_rows}</tbody></table>',
        title="State Market Intelligence",
    )

    # ── Queueing Theory Demo ──
    queues = analyze_rcm_operations()
    q_rows = ""
    for q in queues:
        util_cls = "cad-neg" if q.utilization > 0.85 else (
            "cad-warn" if q.utilization > 0.7 else "cad-pos")
        sla_cls = "cad-neg" if q.sla_breach_prob > 0.2 else (
            "cad-warn" if q.sla_breach_prob > 0.05 else "cad-pos")
        q_rows += (
            f'<tr>'
            f'<td><strong>{_html.escape(q.queue_name)}</strong></td>'
            f'<td class="num">{q.arrival_rate:.0f}/day</td>'
            f'<td class="num">{q.n_servers}</td>'
            f'<td class="num {util_cls}"><strong>{q.utilization:.0%}</strong></td>'
            f'<td class="num">{q.avg_wait_time:.1f}d</td>'
            f'<td class="num {sla_cls}">{q.sla_breach_prob:.0%}</td>'
            f'<td class="num"><strong>{q.recommended_servers}</strong></td>'
            f'<td>{"&#9888;" if q.bottleneck else "&#10003;"}</td>'
            f'</tr>'
        )

    queue_chart = _queue_utilization_chart(queues)
    queue_caption = (
        '<div class="ql-chart-caption">'
        'Utilization per queue · dashed lines mark 70% (warn) + 85% (over-capacity)'
        '</div>'
    ) if queue_chart else ""
    queue_section = ck_panel(
        '<p class="ck-section-body">'
        'Operations research model of RCM workqueues as M/M/c systems. Shows utilization, '
        'wait times, SLA breach probability, and recommended staffing. Uses Erlang C formula + '
        'Little\'s Law. Inputs are configurable per hospital.</p>'
        + queue_chart + queue_caption +
        '<table class="cad-table"><thead><tr>'
        '<th>Queue</th><th>Arrivals</th><th>Staff</th><th>Utilization</th>'
        '<th>Avg Wait</th><th>SLA Breach</th><th>Rec. Staff</th><th>Status</th>'
        f'</tr></thead><tbody>{q_rows}</tbody></table>',
        title="RCM Queueing Analysis (M/M/c)",
    )

    # ── Bayesian Calibration Demo ──
    from ..ml.bayesian_calibration import calibrate_rate_metric
    bayes_scenarios = [
        ("Strong data (n=500)", 0.12, 500, 200),
        ("Moderate data (n=50)", 0.12, 50, 200),
        ("Weak data (n=5)", 0.12, 5, 200),
        ("No data (prior only)", None, 0, 200),
        ("Low observed (n=100)", 0.03, 100, 200),
        ("High observed (n=100)", 0.25, 100, 200),
    ]
    bayes_rows = ""
    for label, obs, n, beds in bayes_scenarios:
        est = calibrate_rate_metric("denial_rate", obs, n, beds=beds)
        shrink_cls = "cad-pos" if est.shrinkage_factor < 0.3 else (
            "cad-warn" if est.shrinkage_factor < 0.7 else "cad-neg")
        bayes_rows += (
            f'<tr>'
            f'<td>{_html.escape(label)}</td>'
            f'<td class="num">{est.observed_mean:.1%}</td>'
            f'<td class="num">{est.observed_n}</td>'
            f'<td class="num">{est.prior_mean:.1%}</td>'
            f'<td class="num"><strong>{est.posterior_mean:.1%}</strong></td>'
            f'<td class="num">[{est.credible_interval_90[0]:.1%}, {est.credible_interval_90[1]:.1%}]</td>'
            f'<td class="num {shrink_cls}">{est.shrinkage_factor:.0%}</td>'
            f'<td>{est.data_quality}</td>'
            f'</tr>'
        )

    bayes_section = ck_panel(
        '<p class="ck-section-body">'
        'Denial rate estimation under varying data quality. With strong data, posterior converges '
        'to observed. With weak/no data, posterior shrinks toward peer-group prior (8.5% for '
        'medium hospitals). Shrinkage factor = how much weight goes to prior vs data. '
        '90% credible intervals widen with uncertainty.</p>'
        '<table class="cad-table"><thead><tr>'
        '<th>Scenario</th><th>Observed</th><th>n</th><th>Prior</th>'
        '<th>Posterior</th><th>90% CI</th><th>Shrinkage</th><th>Quality</th>'
        f'</tr></thead><tbody>{bayes_rows}</tbody></table>',
        title="Bayesian Calibration (Beta-Binomial Partial Pooling)",
    )

    # ── Model AUC + Stats ──
    _, _, _, auc, n_train, feats = cached["distress"]

    # 2026-05-28 batch 23 · universal strict 5-block head.
    from ._chartis_kit import ck_editorial_head
    intro = ck_editorial_head(
        eyebrow="QUANT LAB",
        title="Where the analytical moat lives.",
        meta=(
            f"{len(hcris_df):,} HOSPITALS · "
            f"{len(markets)} MARKETS · "
            f"12 MODELS · "
            f"DISTRESS AUC {auc:.3f} (N={n_train:,})"
        ),
        lede_italic_phrase="Where the analytical moat lives.",
        lede_body=(
            f"{len(hcris_df):,} hospitals, {len(markets)} markets, "
            "12 quantitative models — from Bayesian calibration "
            "through DEA efficiency frontiers, queueing theory, and "
            "distress prediction. Zero external dependencies."
        ),
    )

    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Hospitals", f"{len(hcris_df):,}")
        + ck_kpi_block("Markets", f"{len(markets)}")
        + ck_kpi_block(
            "Frontier Hospitals", f"{frontier_count}",
            help={
                "definition": (
                    "Hospitals on the efficiency frontier — those whose "
                    "margin/quality combination isn't dominated by any "
                    "peer in the same size band. Use these as the "
                    "operational targets when underwriting: 'what does "
                    "best-in-class look like in this sub-market?'"
                ),
            },
        )
        + ck_kpi_block(
            "Distress AUC", f"{auc:.3f}",
            help={
                "definition": (
                    "Area-under-curve of the distress-prediction model "
                    "on the labeled corpus — how well it separates "
                    "distressed from healthy hospitals. 0.50 = no "
                    "better than coin flip; 0.80+ = strong; 0.90+ = "
                    "the model rarely confuses the two classes."
                ),
            },
        )
        + ck_kpi_block("Quant Models", "12")
        + ck_kpi_block(
            "External Deps", "0",
            help={
                "definition": (
                    "Zero third-party Python packages beyond stdlib + "
                    "numpy/pandas/matplotlib. No PyTorch, no scikit "
                    "ensemble wrappers, no Bayesian frameworks — every "
                    "model is implemented in-house so the platform "
                    "stays auditable + supply-chain-safe."
                ),
            },
        )
        + '</div>'
    )

    # ── Quant Stack Summary ──
    stack = ck_panel(
        '<div class="ck-card-grid">'
        '<div><strong>ECONOMETRICS</strong>'
        '<ul class="ck-list">'
        '<li>OLS with VIF + state R²</li>'
        '<li>Ridge regression + elastic net</li>'
        '<li>Per-hospital residual analysis</li>'
        '<li>Cross-sectional price elasticity</li></ul></div>'
        '<div><strong>BIOSTATISTICS</strong>'
        '<ul class="ck-list">'
        '<li>Beta-Binomial partial pooling</li>'
        '<li>Gamma-Lognormal hierarchies</li>'
        '<li>Survival/hazard for margin runway</li>'
        '<li>Missing-data scoring (MNAR)</li></ul></div>'
        '<div><strong>OPERATIONS RESEARCH</strong>'
        '<ul class="ck-list">'
        '<li>M/M/c queueing (Erlang C)</li>'
        "<li>Little's Law backlog analysis</li>"
        '<li>DEA efficiency frontier</li>'
        '<li>Staffing optimization</li></ul></div>'
        '<div><strong>MACHINE LEARNING</strong>'
        '<ul class="ck-list">'
        '<li>K-means hospital clustering</li>'
        '<li>Logistic distress prediction</li>'
        '<li>Ensemble (Ridge + k-NN + median)</li>'
        '<li>Conformal prediction intervals</li></ul></div>'
        '<div><strong>CAUSAL INFERENCE</strong>'
        '<ul class="ck-list">'
        '<li>Interrupted Time Series</li>'
        '<li>Difference-in-Differences</li>'
        '<li>Counterfactual estimation</li>'
        '<li>Cross-deal learning / shrinkage</li></ul></div>'
        '<div><strong>SIMULATION</strong>'
        '<ul class="ck-list">'
        '<li>Two-source Monte Carlo</li>'
        '<li>Latin Hypercube sampling</li>'
        '<li>Correlated lever draws</li>'
        '<li>P10/P50/P90 EBITDA/MOIC/IRR</li></ul></div>'
        '</div>',
        title="PE Desk Quant Stack",
    )

    nav = ck_panel(
        '<p class="ck-section-body">'
        '<a href="/ml-insights" class="cad-btn cad-btn-primary">ML Insights</a> '
        '<a href="/portfolio/regression" class="cad-btn">Regression</a> '
        '<a href="/market-data/map" class="cad-btn">Market Heatmap</a> '
        '<a href="/screen" class="cad-btn">Screener</a> '
        '<a href="/methodology" class="cad-btn">Methodology</a>'
        '</p>',
        title="Cross-links",
    )

    next_up = ck_next_section(
        "Open the methodology reference",
        "/methodology",
        eyebrow="Continue —",
        italic_word="methodology",
    )
    body = (
        f'{_QL_CHART_CAPTION_CSS}'
        f'{intro}{kpis}{stack}{bayes_section}{eff_section}'
        f'{mkt_section}{queue_section}{nav}{next_up}'
    )

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body, "Quant Lab",
        active_nav="/quant-lab",
        subtitle=(
            f"{len(hcris_df):,} hospitals | 12 models | "
            f"{len(markets)} markets | {frontier_count} frontier hospitals"
        ),
    )
