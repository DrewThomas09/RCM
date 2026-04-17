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

from .shell_v2 import shell_v2
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
        sc_color = "var(--cad-pos)" if sc >= 0.8 else ("var(--cad-warn)" if sc >= 0.5 else "var(--cad-neg)")
        eff_rows += (
            f'<tr>'
            f'<td><a href="/hospital/{_html.escape(s.ccn)}" '
            f'style="color:var(--cad-link);text-decoration:none;">'
            f'{_html.escape(s.hospital_name)}</a></td>'
            f'<td>{_html.escape(s.state)}</td>'
            f'<td class="num" style="color:{sc_color};font-weight:600;">{sc:.3f}</td>'
            f'<td class="num">P{s.efficiency_percentile:.0f}</td>'
            f'<td>{"&#9733;" if s.is_frontier else ""}</td>'
            f'</tr>'
        )

    eff_section = (
        f'<div class="cad-card">'
        f'<h2>Operational Efficiency Frontier (DEA)</h2>'
        f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:10px;">'
        f'Data Envelopment Analysis: {frontier_count} hospitals on the efficient frontier, '
        f'{bottom_count} in the bottom 30%. Inputs: beds + operating expenses. '
        f'Outputs: net patient revenue + patient days.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Hospital</th><th>State</th><th>Efficiency</th><th>Percentile</th><th>Frontier</th>'
        f'</tr></thead><tbody>{eff_rows}</tbody></table></div>'
    )

    # ── Market Intelligence ──
    markets = cached["markets"]
    mkt_rows = ""
    for m in markets[:20]:
        inv_color = "var(--cad-pos)" if m.investability_grade in ("A", "B") else (
            "var(--cad-warn)" if m.investability_grade == "C" else "var(--cad-neg)")
        mkt_rows += (
            f'<tr>'
            f'<td><a href="/market-data/state/{_html.escape(m.state)}" '
            f'style="color:var(--cad-link);text-decoration:none;">{_html.escape(m.state)}</a></td>'
            f'<td class="num">{m.n_hospitals}</td>'
            f'<td class="num">{_fmt(m.total_revenue, "money")}</td>'
            f'<td class="num">{m.median_margin:.1%}</td>'
            f'<td class="num">{m.hhi:,.0f}</td>'
            f'<td>{_html.escape(m.market_concentration[:12])}</td>'
            f'<td class="num" style="color:{inv_color};font-weight:600;">'
            f'{m.investability_score:.0f} ({m.investability_grade})</td>'
            f'<td class="num" style="color:var(--cad-neg);">{m.distress_rate:.0%}</td>'
            f'</tr>'
        )

    mkt_section = (
        f'<div class="cad-card">'
        f'<h2>State Market Intelligence</h2>'
        f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:10px;">'
        f'{len(markets)} markets analyzed. HHI (Herfindahl-Hirschman Index) measures concentration: '
        f'&gt;2500 = highly concentrated, &gt;1500 = moderate. Investability combines market depth, '
        f'growth, health, and payer quality.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>State</th><th>Hospitals</th><th>Revenue</th><th>Median Margin</th>'
        f'<th>HHI</th><th>Concentration</th><th>Investability</th><th>Distress</th>'
        f'</tr></thead><tbody>{mkt_rows}</tbody></table></div>'
    )

    # ── Queueing Theory Demo ──
    queues = analyze_rcm_operations()
    q_rows = ""
    for q in queues:
        util_color = "var(--cad-neg)" if q.utilization > 0.85 else (
            "var(--cad-warn)" if q.utilization > 0.7 else "var(--cad-pos)")
        sla_color = "var(--cad-neg)" if q.sla_breach_prob > 0.2 else (
            "var(--cad-warn)" if q.sla_breach_prob > 0.05 else "var(--cad-pos)")
        q_rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{_html.escape(q.queue_name)}</td>'
            f'<td class="num">{q.arrival_rate:.0f}/day</td>'
            f'<td class="num">{q.n_servers}</td>'
            f'<td class="num" style="color:{util_color};font-weight:600;">{q.utilization:.0%}</td>'
            f'<td class="num">{q.avg_wait_time:.1f}d</td>'
            f'<td class="num" style="color:{sla_color};">{q.sla_breach_prob:.0%}</td>'
            f'<td class="num" style="font-weight:500;">{q.recommended_servers}</td>'
            f'<td>{"&#9888;" if q.bottleneck else "&#10003;"}</td>'
            f'</tr>'
        )

    queue_section = (
        f'<div class="cad-card">'
        f'<h2>RCM Queueing Analysis (M/M/c)</h2>'
        f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:10px;">'
        f'Operations research model of RCM workqueues as M/M/c systems. Shows utilization, '
        f'wait times, SLA breach probability, and recommended staffing. Uses Erlang C formula + '
        f'Little\'s Law. Inputs are configurable per hospital.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Queue</th><th>Arrivals</th><th>Staff</th><th>Utilization</th>'
        f'<th>Avg Wait</th><th>SLA Breach</th><th>Rec. Staff</th><th>Status</th>'
        f'</tr></thead><tbody>{q_rows}</tbody></table></div>'
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
        shrink_color = "var(--cad-pos)" if est.shrinkage_factor < 0.3 else (
            "var(--cad-warn)" if est.shrinkage_factor < 0.7 else "var(--cad-neg)")
        bayes_rows += (
            f'<tr>'
            f'<td>{_html.escape(label)}</td>'
            f'<td class="num">{est.observed_mean:.1%}</td>'
            f'<td class="num">{est.observed_n}</td>'
            f'<td class="num">{est.prior_mean:.1%}</td>'
            f'<td class="num" style="font-weight:600;">{est.posterior_mean:.1%}</td>'
            f'<td class="num">[{est.credible_interval_90[0]:.1%}, {est.credible_interval_90[1]:.1%}]</td>'
            f'<td class="num" style="color:{shrink_color};">{est.shrinkage_factor:.0%}</td>'
            f'<td style="font-size:11px;">{est.data_quality}</td>'
            f'</tr>'
        )

    bayes_section = (
        f'<div class="cad-card">'
        f'<h2>Bayesian Calibration (Beta-Binomial Partial Pooling)</h2>'
        f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:10px;">'
        f'Denial rate estimation under varying data quality. With strong data, posterior converges '
        f'to observed. With weak/no data, posterior shrinks toward peer-group prior (8.5% for '
        f'medium hospitals). Shrinkage factor = how much weight goes to prior vs data. '
        f'90% credible intervals widen with uncertainty.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Scenario</th><th>Observed</th><th>n</th><th>Prior</th>'
        f'<th>Posterior</th><th>90% CI</th><th>Shrinkage</th><th>Quality</th>'
        f'</tr></thead><tbody>{bayes_rows}</tbody></table></div>'
    )

    # ── Model AUC + Stats ──
    _, _, _, auc, n_train, feats = cached["distress"]

    # ── KPIs ──
    kpis = (
        f'<div class="cad-kpi-grid" style="grid-template-columns:repeat(6,1fr);">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(hcris_df):,}</div>'
        f'<div class="cad-kpi-label">Hospitals</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(markets)}</div>'
        f'<div class="cad-kpi-label">Markets</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{frontier_count}</div>'
        f'<div class="cad-kpi-label">Frontier Hospitals</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{auc:.3f}</div>'
        f'<div class="cad-kpi-label">Distress AUC</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">12</div>'
        f'<div class="cad-kpi-label">Quant Models</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">0</div>'
        f'<div class="cad-kpi-label">External Deps</div></div>'
        f'</div>'
    )

    # ── Quant Stack Summary ──
    stack = (
        f'<div class="cad-card" style="border-left:3px solid var(--cad-accent);">'
        f'<h2>SeekingChartis Quant Stack</h2>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;font-size:12px;">'
        f'<div>'
        f'<h3 style="font-size:11px;color:var(--cad-accent);margin-bottom:4px;">ECONOMETRICS</h3>'
        f'<ul style="padding-left:14px;color:var(--cad-text2);line-height:1.8;">'
        f'<li>OLS with VIF + state R&sup2;</li>'
        f'<li>Ridge regression + elastic net</li>'
        f'<li>Per-hospital residual analysis</li>'
        f'<li>Cross-sectional price elasticity</li></ul></div>'
        f'<div>'
        f'<h3 style="font-size:11px;color:var(--cad-accent);margin-bottom:4px;">BIOSTATISTICS</h3>'
        f'<ul style="padding-left:14px;color:var(--cad-text2);line-height:1.8;">'
        f'<li>Beta-Binomial partial pooling</li>'
        f'<li>Gamma-Lognormal hierarchies</li>'
        f'<li>Survival/hazard for margin runway</li>'
        f'<li>Missing-data scoring (MNAR)</li></ul></div>'
        f'<div>'
        f'<h3 style="font-size:11px;color:var(--cad-accent);margin-bottom:4px;">OPERATIONS RESEARCH</h3>'
        f'<ul style="padding-left:14px;color:var(--cad-text2);line-height:1.8;">'
        f'<li>M/M/c queueing (Erlang C)</li>'
        f'<li>Little\'s Law backlog analysis</li>'
        f'<li>DEA efficiency frontier</li>'
        f'<li>Staffing optimization</li></ul></div>'
        f'<div>'
        f'<h3 style="font-size:11px;color:var(--cad-accent);margin-bottom:4px;">MACHINE LEARNING</h3>'
        f'<ul style="padding-left:14px;color:var(--cad-text2);line-height:1.8;">'
        f'<li>K-means hospital clustering</li>'
        f'<li>Logistic distress prediction</li>'
        f'<li>Ensemble (Ridge + k-NN + median)</li>'
        f'<li>Conformal prediction intervals</li></ul></div>'
        f'<div>'
        f'<h3 style="font-size:11px;color:var(--cad-accent);margin-bottom:4px;">CAUSAL INFERENCE</h3>'
        f'<ul style="padding-left:14px;color:var(--cad-text2);line-height:1.8;">'
        f'<li>Interrupted Time Series</li>'
        f'<li>Difference-in-Differences</li>'
        f'<li>Counterfactual estimation</li>'
        f'<li>Cross-deal learning / shrinkage</li></ul></div>'
        f'<div>'
        f'<h3 style="font-size:11px;color:var(--cad-accent);margin-bottom:4px;">SIMULATION</h3>'
        f'<ul style="padding-left:14px;color:var(--cad-text2);line-height:1.8;">'
        f'<li>Two-source Monte Carlo</li>'
        f'<li>Latin Hypercube sampling</li>'
        f'<li>Correlated lever draws</li>'
        f'<li>P10/P50/P90 EBITDA/MOIC/IRR</li></ul></div>'
        f'</div></div>'
    )

    # ── Nav ──
    nav = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/ml-insights" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">ML Insights</a>'
        f'<a href="/portfolio/regression" class="cad-btn" '
        f'style="text-decoration:none;">Regression</a>'
        f'<a href="/market-data/map" class="cad-btn" '
        f'style="text-decoration:none;">Market Heatmap</a>'
        f'<a href="/screen" class="cad-btn" '
        f'style="text-decoration:none;">Screener</a>'
        f'<a href="/methodology" class="cad-btn" '
        f'style="text-decoration:none;">Methodology</a>'
        f'</div>'
    )

    body = f'{kpis}{stack}{bayes_section}{eff_section}{mkt_section}{queue_section}{nav}'

    return shell_v2(
        body, "Quant Lab",
        active_nav="/quant-lab",
        subtitle=(
            f"{len(hcris_df):,} hospitals | 12 models | "
            f"{len(markets)} markets | {frontier_count} frontier hospitals"
        ),
    )
