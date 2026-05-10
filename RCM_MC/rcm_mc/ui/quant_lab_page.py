"""SeekingChartis Quant Lab — full quant stack in browser.

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
    chartis_shell, ck_kpi_block, ck_panel, ck_section_intro,
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

    eff_section = ck_panel(
        '<p class="ck-section-body">'
        f'Data Envelopment Analysis: {frontier_count} hospitals on the efficient frontier, '
        f'{bottom_count} in the bottom 30%. Inputs: beds + operating expenses. '
        'Outputs: net patient revenue + patient days.</p>'
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

    queue_section = ck_panel(
        '<p class="ck-section-body">'
        'Operations research model of RCM workqueues as M/M/c systems. Shows utilization, '
        'wait times, SLA breach probability, and recommended staffing. Uses Erlang C formula + '
        'Little\'s Law. Inputs are configurable per hospital.</p>'
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

    intro = ck_section_intro(
        eyebrow="QUANT LAB",
        headline="Where the analytical moat lives.",
        italic_word="lives",
        body=(
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
        + ck_kpi_block("Frontier Hospitals", f"{frontier_count}")
        + ck_kpi_block("Distress AUC", f"{auc:.3f}")
        + ck_kpi_block("Quant Models", "12")
        + ck_kpi_block("External Deps", "0")
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
        title="SeekingChartis Quant Stack",
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

    body = f'{intro}{kpis}{stack}{bayes_section}{eff_section}{mkt_section}{queue_section}{nav}'

    return chartis_shell(
        body, "Quant Lab",
        active_nav="/quant-lab",
        subtitle=(
            f"{len(hcris_df):,} hospitals | 12 models | "
            f"{len(markets)} markets | {frontier_count} frontier hospitals"
        ),
    )
