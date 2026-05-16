"""PE Desk Analytics — causal inference, counterfactual, benchmarks, scenario comparison.

Connects analytics/, pe/predicted_vs_actual, data/benchmark_evolution, and
mc/scenario_comparison to browser pages.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_next_section, ck_page_title, ck_panel,
    ck_section_intro,
)

_BENCH_EXPLAINER_CSS = """
.ck-be-explainer{font-family:var(--sc-serif);font-size:15px;line-height:1.6;
color:var(--sc-text-dim);max-width:68ch;
margin:var(--sc-s-4) 0 var(--sc-s-6);}
.ck-be-explainer em{color:var(--sc-teal-ink);font-style:italic;}
"""
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
        eff_cls = "cad-pos" if effect > 0 else "cad-neg"
        rows += (
            f'<tr>'
            f'<td><strong>{method}</strong></td>'
            f'<td class="num {eff_cls}">{effect:+.2f}</td>'
            f'<td class="num">[{ci_low:.2f}, {ci_high:.2f}]</td>'
            f'<td class="num">{p_val:.3f}</td>'
            f'<td><span class="cad-badge {conf_cls}">{html.escape(conf)}</span></td>'
            f'</tr>'
        )

    sig_count = sum(1 for e in estimates if float(e.get("p_value", 1)) < 0.05)

    intro = ck_section_intro(
        eyebrow="CAUSAL INFERENCE",
        headline=f"{html.escape(deal_name)} — what actually moved the needle.",
        italic_word="moved",
        body=(
            f"{len(estimates)} initiative-level estimates run through "
            "three causal methods (interrupted time series, "
            "difference-in-differences, pre-post). The scorecard "
            "below shows the effect size, 95% CI, p-value, and "
            "confidence band per estimate."
        ),
    )

    interp = ck_panel(
        '<p class="ck-section-body">'
        f'{sig_count} of {len(estimates)} estimates are statistically significant (p&lt;0.05). '
        f'{"Strong evidence of initiative impact — include in IC memo." if sig_count > len(estimates) // 2 else "Limited statistical evidence — more data points needed."}</p>'
        '<p class="ck-section-body">Methods: Interrupted Time Series (trend break), '
        'Difference-in-Differences (vs control), and Pre-Post comparison with CIs.</p>',
        title="What This Means",
    )

    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Causal Estimates", f"{len(estimates)}")
        + ck_kpi_block("Significant (p<0.05)", f"{sig_count}")
        + '</div>'
    )

    nav = _model_nav(deal_id, "")
    body = (
        f'{nav}{intro}{kpis}'
        + ck_panel(
            '<p class="ck-section-body">Three causal inference methods applied to each initiative.</p>'
            '<table class="cad-table"><thead><tr>'
            '<th>Method</th><th>Effect</th><th>95% CI</th><th>p-value</th><th>Confidence</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>',
            title="Initiative Impact Estimates",
        )
        + interp
        + ck_next_section(
            "Open the counterfactual view",
            f"/models/counterfactual/{html.escape(deal_id)}",
            eyebrow="Continue —",
            italic_word="counterfactual",
        )
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
        cls = "cad-pos" if d > 0 else "cad-neg"
        rows += (
            f'<tr>'
            f'<td class="num">Period {i+1}</td>'
            f'<td class="num">${float(a)/1e6:.1f}M</td>'
            f'<td class="num">${float(c)/1e6:.1f}M</td>'
            f'<td class="num {cls}">${float(d)/1e6:.1f}M</td>'
            f'</tr>'
        )

    cum_cls = "cad-pos" if cumulative > 0 else "cad-neg"

    intro = ck_section_intro(
        eyebrow="COUNTERFACTUAL",
        headline=f"{html.escape(deal_name)} — what would have happened without it.",
        italic_word="without",
        body=(
            "Side-by-side actual vs counterfactual EBITDA "
            "trajectory. The cumulative delta is the initiative's "
            "attributable value-creation; pair with causal inference "
            "for statistical significance."
        ),
    )

    interp = ck_panel(
        '<p class="ck-section-body">'
        f'Without the initiative, EBITDA would have been <strong>${abs(cumulative)/1e6:.1f}M '
        f'{"higher" if cumulative < 0 else "lower"}</strong> over the period. '
        f'{"The initiative clearly created value." if cumulative > 0 else "The initiative did not deliver expected results."}</p>'
        '<p class="ck-section-body">Methodology: '
        f'{html.escape(method)}. '
        f'See <a href="/models/causal/{html.escape(deal_id)}" class="ck-link">'
        'causal inference</a> for statistical significance.</p>',
        title="What This Means",
    )

    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Cumulative Initiative Impact",
            f'<span class="{cum_cls}">${cumulative/1e6:.1f}M</span>',
        )
        + ck_kpi_block("Periods Analyzed", f"{len(actual)}")
        + '</div>'
    )

    nav = _model_nav(deal_id, "")
    body = (
        f'{nav}{intro}{kpis}'
        + ck_panel(
            '<p class="ck-section-body">'
            '"What would EBITDA be if we hadn\'t done this initiative?"</p>'
            '<table class="cad-table"><thead><tr>'
            '<th>Period</th><th>Actual</th><th>Counterfactual</th><th>Delta</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>',
            title="Actual vs Counterfactual",
        )
        + interp
        + ck_next_section(
            "Open the causal inference view",
            f"/models/causal/{html.escape(deal_id)}",
            eyebrow="Continue —",
            italic_word="causal",
        )
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
        drift_cls = "cad-pos" if drift > 0 else ("cad-neg" if drift < 0 else "")
        rows += (
            f'<tr>'
            f'<td><strong>{metric}</strong></td>'
            f'<td class="num">{float(prior):.2f}</td>'
            f'<td class="num">{float(current):.2f}</td>'
            f'<td class="num {drift_cls}">{float(drift):+.2f}pp</td>'
            f'<td><span class="cad-badge {dir_cls}">{html.escape(direction.replace("_", " ").title())}</span></td>'
            f'</tr>'
        )

    title_block = ck_page_title(
        "Benchmark Evolution", eyebrow="BENCHMARK EVOLUTION",
        meta=f"{len(drifts)} benchmarks · {improving} improving · {declining} declining",
    )
    explainer_html = (
        '<p class="ck-be-explainer">'
        '<em>How the bar is moving on you, year over year.</em> '
        "Industry P50 drift across the metrics that drive the bridge. "
        "When benchmarks shift, a deal's relative position changes even "
        "without operational improvement — factor this into "
        "target-margin assumptions before IC."
        '</p>'
    )

    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Benchmarks Tracked", f"{len(drifts)}")
        + ck_kpi_block("Industry Improving", f"{improving}")
        + ck_kpi_block("Industry Declining", f"{declining}")
        + '</div>'
    )

    body = (
        title_block + explainer_html + kpis
        + ck_panel(
            '<p class="ck-section-body">'
            'How industry P50 benchmarks are shifting year-over-year. '
            'Drifts &gt;1pp trigger automatic target re-marking.</p>'
            '<table class="cad-table"><thead><tr>'
            '<th>Metric</th><th>Prior P50</th><th>Current P50</th><th>Drift</th><th>Direction</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>',
            title="Benchmark Evolution",
        )
        + ck_panel(
            '<p class="ck-section-body">'
            f'{improving} benchmarks are improving industry-wide (the bar is rising), '
            f'{declining} are declining. When benchmarks shift, your deal\'s relative position changes '
            'even without operational improvement. Factor this into your bridge assumptions.</p>',
            title="What This Means",
        )
    )

    return chartis_shell(
        body, "Benchmark Evolution",
        active_nav="/benchmarks",
        extra_css=_BENCH_EXPLAINER_CSS,
    )


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
        var_cls = "cad-pos" if abs(variance) < 10 else (
            "cad-warn" if abs(variance) < 25 else "cad-neg")
        ci_badge = "cad-badge-green" if within else "cad-badge-red"
        rows += (
            f'<tr>'
            f'<td><strong>{metric}</strong></td>'
            f'<td class="num">{float(predicted):.2f}</td>'
            f'<td class="num">{float(actual):.2f}</td>'
            f'<td class="num {var_cls}">{float(variance):+.1f}%</td>'
            f'<td><span class="cad-badge {ci_badge}">{"In CI" if within else "Outside CI"}</span></td>'
            f'</tr>'
        )

    intro = ck_section_intro(
        eyebrow="PREDICTED VS ACTUAL",
        headline=f"{html.escape(deal_name)} — how the diligence-era forecast aged.",
        italic_word="aged",
        body=(
            f"{n_metrics} metrics from the original analysis packet "
            "compared against current operational data. Within-CI "
            "rate measures model calibration; variance % flags the "
            "metrics that drifted most since underwriting."
        ),
    )

    interp = ck_panel(
        '<p class="ck-section-body">'
        f'{pct_ci:.0%} of predictions fell within their confidence intervals — '
        f'{"strong prediction accuracy, our models are well-calibrated." if pct_ci > 0.7 else "moderate accuracy, consider widening CIs or improving feature set." if pct_ci > 0.5 else "low accuracy — review model assumptions and data quality."}</p>'
        '<p class="ck-section-body">'
        f'Mean absolute error: {mae:.2f}. '
        'Metrics outside CI may indicate either data quality issues or genuine operational changes '
        'since diligence.</p>',
        title="What This Means",
    )

    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Within Confidence Interval", f"{pct_ci:.0%}")
        + ck_kpi_block("Mean Absolute Error", f"{mae:.2f}")
        + ck_kpi_block("Metrics Compared", f"{n_metrics}")
        + '</div>'
    )

    nav = _model_nav(deal_id, "")
    body = (
        f'{nav}{intro}{kpis}'
        + ck_panel(
            '<p class="ck-section-body">'
            'How accurate were our predictions? Compares the earliest analysis packet against current data.</p>'
            '<table class="cad-table"><thead><tr>'
            '<th>Metric</th><th>Predicted</th><th>Actual</th><th>Variance</th><th>In CI?</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>',
            title="Predicted at Diligence vs Actual",
        )
        + interp
    )

    return chartis_shell(body, f"Predicted vs Actual — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"{pct_ci:.0%} accuracy | {n_metrics} metrics | MAE: {mae:.2f}")
