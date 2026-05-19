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
.bd-chart-caption {
  font-family: "Inter Tight","Inter",sans-serif;
  font-size: .72rem; color: #5C6878;
  text-align: center; letter-spacing: 0.06em;
  text-transform: uppercase; margin: -.5rem 0 1.25rem;
}
@media print {
  .bd-chart-caption { color: #1a2332; }
  svg { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
"""


def _benchmark_drift_chart(drifts: List[Dict[str, Any]],
                           width: int = 720,
                           height: int = 260) -> str:
    """Diverging horizontal-bar chart of benchmark drift per metric.

    Bars project left (declining industry, red) or right (improving
    industry, green) from a centered zero axis. Metric label on the
    outer rail per direction; numeric drift in pp at bar end.
    """
    items: List[Dict[str, Any]] = []
    for d in drifts:
        try:
            drift = float(d.get("drift_pp", 0))
        except (TypeError, ValueError):
            continue
        items.append({
            "metric": str(d.get("metric_key", "")).replace("_", " ").title(),
            "drift": drift,
            "direction": str(d.get("direction", "stable")),
        })
    if not items:
        return ""
    # Sort by drift descending so improvers stack at top, decliners at bottom
    items.sort(key=lambda i: -i["drift"])
    max_abs = max((abs(i["drift"]) for i in items), default=1) or 1

    pad_l, pad_r, pad_t, pad_b = 18, 18, 28, 38
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    n = len(items)
    row_h = plot_h / max(n, 1)
    mid_x = pad_l + plot_w / 2
    half_w = plot_w / 2 - 6

    bars_svg = ""
    for i, item in enumerate(items):
        cy = pad_t + row_h * i + row_h / 2
        drift = item["drift"]
        bw = abs(drift) / max_abs * half_w
        is_pos = drift > 0
        bx = mid_x if is_pos else mid_x - bw
        if "improving" in item["direction"]:
            fill = "#3F7D4D"  # editorial green
        elif "declining" in item["direction"]:
            fill = "#A53A2D"  # editorial red
        else:
            fill = "#8A92A0"  # neutral
        # Metric label sits on the OPPOSITE side of the bar
        label_x = mid_x + 8 if not is_pos else mid_x - 8
        label_anchor = "start" if not is_pos else "end"
        # Drift value sits at the OUTER end of the bar
        val_x = (bx + bw + 6) if is_pos else (bx - 6)
        val_anchor = "start" if is_pos else "end"
        bars_svg += (
            f'<rect x="{bx:.1f}" y="{cy - row_h * 0.30:.1f}" '
            f'width="{bw:.1f}" height="{row_h * 0.58:.1f}" '
            f'fill="{fill}" opacity="0.9" rx="1"/>'
            f'<text x="{label_x:.1f}" y="{cy + 3:.1f}" '
            f'font-family="Inter Tight,sans-serif" font-size="10.5" '
            f'font-weight="600" fill="#1a2332" '
            f'text-anchor="{label_anchor}">'
            f'{html.escape(item["metric"])}</text>'
            f'<text x="{val_x:.1f}" y="{cy + 3:.1f}" '
            f'font-family="JetBrains Mono,monospace" font-size="10" '
            f'font-weight="700" fill="{fill}" '
            f'text-anchor="{val_anchor}">'
            f'{drift:+.2f}pp</text>'
        )

    # Zero-axis vertical line
    axis_svg = (
        f'<line x1="{mid_x:.1f}" y1="{pad_t}" x2="{mid_x:.1f}" '
        f'y2="{pad_t + plot_h}" stroke="#1a2332" stroke-width="1.2"/>'
    )
    # Bottom-axis labels
    bottom_svg = (
        f'<text x="{mid_x - half_w / 2:.1f}" y="{height - 8}" '
        f'font-family="Inter Tight,sans-serif" font-size="10" '
        f'font-weight="700" letter-spacing="0.08em" '
        f'fill="#A53A2D" text-anchor="middle">'
        f'◀ INDUSTRY DECLINING</text>'
        f'<text x="{mid_x + half_w / 2:.1f}" y="{height - 8}" '
        f'font-family="Inter Tight,sans-serif" font-size="10" '
        f'font-weight="700" letter-spacing="0.08em" '
        f'fill="#3F7D4D" text-anchor="middle">'
        f'INDUSTRY IMPROVING ▶</text>'
        f'<text x="{mid_x:.1f}" y="{pad_t - 8}" '
        f'font-family="JetBrains Mono,monospace" font-size="9" '
        f'font-weight="700" letter-spacing="0.06em" '
        f'fill="#5C6878" text-anchor="middle">0pp</text>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="width:100%;max-width:{width}px;height:auto;display:block;'
        f'margin:0 auto 1rem;">'
        f'{axis_svg}{bars_svg}{bottom_svg}</svg>'
    )
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


def _counterfactual_trajectory_chart(
    actual: List[float],
    counter: List[float],
) -> str:
    """SVG line chart of Actual vs Counterfactual EBITDA trajectory.

    Two lines on a shared axis — actual (solid green) sits above (or
    below) counterfactual (dashed grey). The shaded area between is
    the cumulative initiative impact. Partner-readable summary of
    "what we did" vs. "what would have happened" without scanning
    the period-by-period table.
    """
    if not actual or not counter or len(actual) != len(counter):
        return ""
    n = len(actual)
    width = 720
    height = 280
    pad_l, pad_r, pad_t, pad_b = 64, 28, 32, 44
    inner_w = width - pad_l - pad_r
    inner_h = height - pad_t - pad_b

    all_vals = [float(v) for v in actual] + [float(v) for v in counter]
    y_min = min(all_vals)
    y_max = max(all_vals)
    span = y_max - y_min or 1.0
    y_lo = y_min - span * 0.08
    y_hi = y_max + span * 0.08

    def sx(i: int) -> float:
        if n == 1:
            return pad_l + inner_w / 2
        return pad_l + (i / (n - 1)) * inner_w

    def sy(v: float) -> float:
        return pad_t + inner_h - (v - y_lo) / (y_hi - y_lo) * inner_h

    # 4 horizontal gridlines + tick labels
    grid = []
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        v = y_lo + (y_hi - y_lo) * frac
        y = pad_t + inner_h - frac * inner_h
        grid.append(
            f'<line x1="{pad_l}" x2="{pad_l + inner_w}" '
            f'y1="{y:.1f}" y2="{y:.1f}" stroke="#d6cfc0" '
            f'stroke-dasharray="2,4" />'
            f'<text x="{pad_l - 6}" y="{y + 3:.1f}" '
            f'fill="#7a8699" text-anchor="end" font-size="10" '
            f'font-family="JetBrains Mono, monospace">'
            f'${v/1e6:.0f}M</text>'
        )

    # Shaded area between the two trajectories — green tint when
    # actual > counter (initiative created value), red when below
    cumulative = sum(float(a) - float(c) for a, c in zip(actual, counter))
    fill_color = "#0a8a5f" if cumulative >= 0 else "#b5321e"
    actual_pts = [(sx(i), sy(float(a))) for i, a in enumerate(actual)]
    counter_pts = [(sx(i), sy(float(c))) for i, c in enumerate(counter)]
    poly_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in actual_pts)
    poly_points += " " + " ".join(
        f"{x:.1f},{y:.1f}" for x, y in reversed(counter_pts)
    )
    shade = (
        f'<polygon points="{poly_points}" '
        f'fill="{fill_color}" fill-opacity="0.10" />'
    )

    # Counterfactual line: dashed grey
    counter_path = "M " + " L ".join(
        f"{x:.1f},{y:.1f}" for x, y in counter_pts
    )
    counter_line = (
        f'<path d="{counter_path}" stroke="#5d6b7a" '
        f'stroke-width="2" stroke-dasharray="5,3" fill="none" />'
    )

    # Actual line: solid green/red (matches the cumulative sign)
    actual_path = "M " + " L ".join(
        f"{x:.1f},{y:.1f}" for x, y in actual_pts
    )
    actual_color = "#0a8a5f" if cumulative >= 0 else "#b5321e"
    actual_line = (
        f'<path d="{actual_path}" stroke="{actual_color}" '
        f'stroke-width="2.5" fill="none" />'
    )

    # Period dots on actual line
    actual_dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" '
        f'fill="{actual_color}" stroke="#fff" stroke-width="1.5" />'
        for x, y in actual_pts
    )
    # Period labels along the x-axis
    period_labels = []
    for i in range(n):
        x = sx(i)
        period_labels.append(
            f'<text x="{x:.1f}" y="{height - pad_b + 14}" '
            f'fill="#7a8699" text-anchor="middle" font-size="10" '
            f'font-family="JetBrains Mono, monospace">'
            f'P{i + 1}</text>'
        )

    legend = (
        f'<g transform="translate({pad_l + inner_w - 200}, {pad_t + 6})">'
        # actual swatch
        f'<line x1="0" x2="20" y1="6" y2="6" '
        f'stroke="{actual_color}" stroke-width="2.5" />'
        f'<text x="26" y="9" fill="#1a2332" font-size="11" '
        f'font-family="Inter, sans-serif">Actual</text>'
        # counter swatch
        f'<line x1="80" x2="100" y1="6" y2="6" '
        f'stroke="#5d6b7a" stroke-width="2" stroke-dasharray="5,3" />'
        f'<text x="106" y="9" fill="#1a2332" font-size="11" '
        f'font-family="Inter, sans-serif">Counterfactual</text>'
        f'</g>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;background:transparent;'
        f'margin:8px 0 16px;">'
        f'{"".join(grid)}'
        f'{shade}'
        f'{counter_line}'
        f'{actual_line}'
        f'{actual_dots}'
        f'{"".join(period_labels)}'
        f'{legend}'
        f'</svg>'
    )


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

    trajectory_chart = _counterfactual_trajectory_chart(actual, counter)
    nav = _model_nav(deal_id, "")
    body = (
        f'{nav}{intro}{kpis}'
        + ck_panel(
            '<p class="ck-section-body">'
            '"What would EBITDA be if we hadn\'t done this initiative?" '
            'Solid line = actual; dashed grey = counterfactual; shaded '
            'area = the attributable initiative impact.</p>'
            f'{trajectory_chart}'
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

    drift_chart = _benchmark_drift_chart(drifts)
    drift_caption = (
        '<div class="bd-chart-caption">'
        'YoY P50 drift per metric · left = industry declining · right = industry improving'
        '</div>'
    ) if drift_chart else ""
    body = (
        title_block + explainer_html + kpis
        + ck_panel(
            '<p class="ck-section-body">'
            'How industry P50 benchmarks are shifting year-over-year. '
            'Drifts &gt;1pp trigger automatic target re-marking.</p>'
            + drift_chart + drift_caption +
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
