"""SeekingChartis Analytics — causal inference, counterfactual, benchmarks, scenario comparison.

Connects analytics/, pe/predicted_vs_actual, data/benchmark_evolution, and
mc/scenario_comparison to browser pages.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from ._chartis_kit import chartis_shell
from .models_page import _model_nav
from .brand import PALETTE


def render_causal_page(deal_id: str, deal_name: str, estimates: List[Dict[str, Any]]) -> str:
    """Render causal inference results for initiative impacts."""
    rows = ""
    for e in estimates:
        method = html.escape(str(e.get("method", "")))
        effect = e.get("estimated_effect", 0)
        ci_low = e.get("ci_low", 0)
        ci_high = e.get("ci_high", 0)
        conf = e.get("confidence", "low")
        p_val = e.get("p_value", 1.0)
        conf_cls = {"high": "cad-badge-green", "medium": "cad-badge-amber"}.get(conf, "cad-badge-muted")
        eff_color = PALETTE["positive"] if effect > 0 else PALETTE["negative"]
        rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{method}</td>'
            f'<td class="num" style="color:{eff_color};">{effect:+.2f}</td>'
            f'<td class="num">[{ci_low:.2f}, {ci_high:.2f}]</td>'
            f'<td class="num">{p_val:.3f}</td>'
            f'<td><span class="cad-badge {conf_cls}">{html.escape(conf)}</span></td>'
            f'</tr>'
        )

    sig_count = sum(1 for e in estimates if float(e.get("p_value", 1)) < 0.05)

    interp = (
        f'<div class="cad-card" style="border-left:3px solid {PALETTE["brand_accent"]};">'
        f'<h2>What This Means</h2>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'<p>{sig_count} of {len(estimates)} estimates are statistically significant (p&lt;0.05). '
        f'{"Strong evidence of initiative impact — include in IC memo." if sig_count > len(estimates) // 2 else "Limited statistical evidence — more data points needed."}</p>'
        f'<p style="margin-top:6px;">Methods: Interrupted Time Series (trend break), '
        f'Difference-in-Differences (vs control), and Pre-Post comparison with CIs.</p>'
        f'</div></div>'
    )

    nav = _model_nav(deal_id, "")
    body = (
        f'{nav}'
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(estimates)}</div>'
        f'<div class="cad-kpi-label">Causal Estimates</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{sig_count}</div>'
        f'<div class="cad-kpi-label">Significant (p&lt;0.05)</div></div>'
        f'</div>'
        f'<div class="cad-card">'
        f'<h2>Initiative Impact Estimates</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:10px;">'
        f'Three causal inference methods applied to each initiative.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Method</th><th>Effect</th><th>95% CI</th><th>p-value</th><th>Confidence</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
        f'{interp}'
    )

    return chartis_shell(body, f"Causal Inference — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"{len(estimates)} estimates, {sig_count} significant")


def render_counterfactual_page(deal_id: str, deal_name: str, result: Dict[str, Any]) -> str:
    """Render counterfactual analysis — what would have happened without the initiative."""
    actual = result.get("actual_trajectory", [])
    counter = result.get("counterfactual_trajectory", [])
    delta = result.get("delta_per_period", [])
    cumulative = result.get("cumulative_delta", 0)
    method = result.get("methodology", "pre-post with ramp adjustment")

    # Period comparison table
    rows = ""
    for i, (a, c, d) in enumerate(zip(actual, counter, delta)):
        color = PALETTE["positive"] if d > 0 else PALETTE["negative"]
        rows += (
            f'<tr>'
            f'<td class="num">Period {i+1}</td>'
            f'<td class="num">${float(a)/1e6:.1f}M</td>'
            f'<td class="num">${float(c)/1e6:.1f}M</td>'
            f'<td class="num" style="color:{color};">${float(d)/1e6:.1f}M</td>'
            f'</tr>'
        )

    cum_color = PALETTE["positive"] if cumulative > 0 else PALETTE["negative"]

    interp = (
        f'<div class="cad-card" style="border-left:3px solid {cum_color};">'
        f'<h2>What This Means</h2>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'<p>Without the initiative, EBITDA would have been <strong>${abs(cumulative)/1e6:.1f}M '
        f'{"higher" if cumulative < 0 else "lower"}</strong> over the period. '
        f'{"The initiative clearly created value." if cumulative > 0 else "The initiative did not deliver expected results."}</p>'
        f'<p style="margin-top:6px;">Methodology: {html.escape(method)}. '
        f'See <a href="/models/causal/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">'
        f'causal inference</a> for statistical significance.</p>'
        f'</div></div>'
    )

    nav = _model_nav(deal_id, "")
    body = (
        f'{nav}'
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{cum_color};">'
        f'${cumulative/1e6:.1f}M</div>'
        f'<div class="cad-kpi-label">Cumulative Initiative Impact</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(actual)}</div>'
        f'<div class="cad-kpi-label">Periods Analyzed</div></div>'
        f'</div>'
        f'<div class="cad-card">'
        f'<h2>Actual vs Counterfactual</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:10px;">'
        f'"What would EBITDA be if we hadn\'t done this initiative?"</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Period</th><th>Actual</th><th>Counterfactual</th><th>Delta</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
        f'{interp}'
    )

    return chartis_shell(body, f"Counterfactual — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"Initiative impact: ${cumulative/1e6:.1f}M cumulative")


def render_benchmark_drift(drifts: List[Dict[str, Any]]) -> str:
    """Render benchmark evolution — how industry benchmarks are changing."""
    rows = ""
    improving = 0
    declining = 0
    for d in drifts:
        metric = html.escape(str(d.get("metric_key", "")).replace("_", " ").title())
        current = d.get("current_p50", 0)
        prior = d.get("prior_p50", 0)
        drift = d.get("drift_pp", 0)
        direction = d.get("direction", "stable")
        if "improving" in direction:
            improving += 1
            dir_cls = "cad-badge-green"
        elif "declining" in direction:
            declining += 1
            dir_cls = "cad-badge-red"
        else:
            dir_cls = "cad-badge-muted"
        drift_color = PALETTE["positive"] if drift > 0 else (PALETTE["negative"] if drift < 0 else PALETTE["text_muted"])
        rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{metric}</td>'
            f'<td class="num">{float(prior):.2f}</td>'
            f'<td class="num">{float(current):.2f}</td>'
            f'<td class="num" style="color:{drift_color};">{float(drift):+.2f}pp</td>'
            f'<td><span class="cad-badge {dir_cls}">{html.escape(direction.replace("_", " ").title())}</span></td>'
            f'</tr>'
        )

    body = (
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(drifts)}</div>'
        f'<div class="cad-kpi-label">Benchmarks Tracked</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{PALETTE["positive"]};">'
        f'{improving}</div><div class="cad-kpi-label">Industry Improving</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{PALETTE["negative"]};">'
        f'{declining}</div><div class="cad-kpi-label">Industry Declining</div></div>'
        f'</div>'

        f'<div class="cad-card">'
        f'<h2>Benchmark Evolution</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:10px;">'
        f'How industry P50 benchmarks are shifting year-over-year. '
        f'Drifts &gt;1pp trigger automatic target re-marking.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Metric</th><th>Prior P50</th><th>Current P50</th><th>Drift</th><th>Direction</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'

        f'<div class="cad-card" style="border-left:3px solid {PALETTE["brand_accent"]};">'
        f'<h2>What This Means</h2>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'<p>{improving} benchmarks are improving industry-wide (the bar is rising), '
        f'{declining} are declining. When benchmarks shift, your deal\'s relative position changes '
        f'even without operational improvement. Factor this into your bridge assumptions.</p>'
        f'</div></div>'
    )

    return chartis_shell(body, "Benchmark Evolution",
                    subtitle=f"{len(drifts)} benchmarks tracked | {improving} improving, {declining} declining")


def render_predicted_vs_actual(deal_id: str, deal_name: str,
                                comparisons: List[Dict[str, Any]],
                                report: Dict[str, Any]) -> str:
    """Render predicted-at-diligence vs actual-at-hold comparison."""
    pct_ci = report.get("pct_within_ci", 0)
    mae = report.get("mean_absolute_error", 0)
    n_metrics = report.get("n_metrics", 0)

    rows = ""
    for c in comparisons:
        metric = html.escape(str(c.get("metric_key", "")).replace("_", " ").title())
        predicted = c.get("predicted_at_diligence", 0)
        actual = c.get("actual_now", 0)
        variance = c.get("variance_pct", 0)
        within = c.get("within_ci", False)
        var_color = PALETTE["positive"] if abs(variance) < 10 else (
            PALETTE["warning"] if abs(variance) < 25 else PALETTE["negative"])
        ci_badge = "cad-badge-green" if within else "cad-badge-red"
        rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{metric}</td>'
            f'<td class="num">{float(predicted):.2f}</td>'
            f'<td class="num">{float(actual):.2f}</td>'
            f'<td class="num" style="color:{var_color};">{float(variance):+.1f}%</td>'
            f'<td><span class="cad-badge {ci_badge}">{"In CI" if within else "Outside CI"}</span></td>'
            f'</tr>'
        )

    accuracy_color = PALETTE["positive"] if pct_ci > 0.7 else (
        PALETTE["warning"] if pct_ci > 0.5 else PALETTE["negative"])

    interp = (
        f'<div class="cad-card" style="border-left:3px solid {accuracy_color};">'
        f'<h2>What This Means</h2>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'<p>{pct_ci:.0%} of predictions fell within their confidence intervals — '
        f'{"strong prediction accuracy, our models are well-calibrated." if pct_ci > 0.7 else "moderate accuracy, consider widening CIs or improving feature set." if pct_ci > 0.5 else "low accuracy — review model assumptions and data quality."}</p>'
        f'<p style="margin-top:6px;">Mean absolute error: {mae:.2f}. '
        f'Metrics outside CI may indicate either data quality issues or genuine operational changes '
        f'since diligence.</p>'
        f'</div></div>'
    )

    nav = _model_nav(deal_id, "")
    body = (
        f'{nav}'
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{accuracy_color};">'
        f'{pct_ci:.0%}</div>'
        f'<div class="cad-kpi-label">Within Confidence Interval</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{mae:.2f}</div>'
        f'<div class="cad-kpi-label">Mean Absolute Error</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{n_metrics}</div>'
        f'<div class="cad-kpi-label">Metrics Compared</div></div>'
        f'</div>'

        f'<div class="cad-card">'
        f'<h2>Predicted at Diligence vs Actual</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:10px;">'
        f'How accurate were our predictions? Compares the earliest analysis packet against current data.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Metric</th><th>Predicted</th><th>Actual</th><th>Variance</th><th>In CI?</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
        f'{interp}'
    )

    return chartis_shell(body, f"Predicted vs Actual — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"{pct_ci:.0%} accuracy | {n_metrics} metrics | MAE: {mae:.2f}")
