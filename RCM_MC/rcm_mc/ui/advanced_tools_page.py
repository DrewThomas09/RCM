"""PE Desk Advanced Tools — debt model, challenge solver, IRS 990, trends.

Connects remaining high-value backend modules to browser pages.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_next_section, ck_panel,
    ck_section_intro, ck_signal_badge,
)
from .models_page import _model_nav
from .brand import PALETTE


_AT_CHART_CAPTION_CSS = """
<style>
.at-chart-caption {
  font-family: "Inter Tight","Inter",sans-serif;
  font-size: .72rem; color: #5C6878;
  text-align: center; letter-spacing: 0.06em;
  text-transform: uppercase; margin: -.5rem 0 1.25rem;
}
@media print {
  .at-chart-caption { color: #1a2332; }
  svg { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
</style>
"""


def _trend_slope_chart(trends: List[Dict[str, Any]],
                       width: int = 720, height: int = 260) -> str:
    """Diverging-bar chart of per-metric quarterly slope.

    Bars project right (improving, green) or left (declining, red)
    from a centered zero axis. Confidence (r2) modulates opacity so
    high-confidence trends read stronger.
    """
    items: List[Dict[str, Any]] = []
    for t in trends:
        try:
            slope = float(t.get("slope", t.get("change_per_quarter", 0)))
        except (TypeError, ValueError):
            continue
        try:
            conf = float(t.get("confidence", t.get("r2", 0)))
        except (TypeError, ValueError):
            conf = 0.0
        items.append({
            "metric": str(t.get("metric", t.get("kpi", ""))),
            "slope": slope,
            "conf": max(0.0, min(1.0, conf)),
        })
    if not items:
        return ""
    items.sort(key=lambda i: -i["slope"])
    max_abs = max((abs(i["slope"]) for i in items), default=1) or 1

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
        slope = item["slope"]
        bw = abs(slope) / max_abs * half_w
        is_pos = slope > 0
        bx = mid_x if is_pos else mid_x - bw
        fill = "#3F7D4D" if is_pos else ("#A53A2D" if slope < 0 else "#8A92A0")
        # Confidence drives opacity: 0.45 floor so low-conf still visible
        opacity = 0.45 + 0.5 * item["conf"]
        label_x = mid_x + 8 if not is_pos else mid_x - 8
        label_anchor = "start" if not is_pos else "end"
        val_x = (bx + bw + 6) if is_pos else (bx - 6)
        val_anchor = "start" if is_pos else "end"
        bars_svg += (
            f'<rect x="{bx:.1f}" y="{cy - row_h * 0.30:.1f}" '
            f'width="{bw:.1f}" height="{row_h * 0.58:.1f}" '
            f'fill="{fill}" opacity="{opacity:.2f}" rx="1"/>'
            f'<text x="{label_x:.1f}" y="{cy + 3:.1f}" '
            f'font-family="Inter Tight,sans-serif" font-size="10.5" '
            f'font-weight="600" fill="#1a2332" '
            f'text-anchor="{label_anchor}">'
            f'{html.escape(item["metric"])}</text>'
            f'<text x="{val_x:.1f}" y="{cy + 3:.1f}" '
            f'font-family="JetBrains Mono,monospace" font-size="9.5" '
            f'font-weight="700" fill="{fill}" '
            f'text-anchor="{val_anchor}">'
            f'{slope:+.3f}/q</text>'
        )

    axis_svg = (
        f'<line x1="{mid_x:.1f}" y1="{pad_t}" x2="{mid_x:.1f}" '
        f'y2="{pad_t + plot_h}" stroke="#1a2332" stroke-width="1.2"/>'
    )
    bottom_svg = (
        f'<text x="{mid_x - half_w / 2:.1f}" y="{height - 8}" '
        f'font-family="Inter Tight,sans-serif" font-size="10" '
        f'font-weight="700" letter-spacing="0.08em" '
        f'fill="#A53A2D" text-anchor="middle">◀ DECLINING</text>'
        f'<text x="{mid_x + half_w / 2:.1f}" y="{height - 8}" '
        f'font-family="Inter Tight,sans-serif" font-size="10" '
        f'font-weight="700" letter-spacing="0.08em" '
        f'fill="#3F7D4D" text-anchor="middle">IMPROVING ▶</text>'
        f'<text x="{mid_x:.1f}" y="{pad_t - 8}" '
        f'font-family="JetBrains Mono,monospace" font-size="9" '
        f'font-weight="700" fill="#5C6878" text-anchor="middle">0/q</text>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="width:100%;max-width:{width}px;height:auto;display:block;'
        f'margin:0 auto 1rem;">'
        f'{axis_svg}{bars_svg}{bottom_svg}</svg>'
    )


def render_debt_model(deal_id: str, deal_name: str, debt: Dict[str, Any]) -> str:
    """Render debt trajectory projections."""
    schedule = debt.get("schedule", debt.get("years", []))
    summary = debt.get("summary", {})
    entry_leverage = summary.get("entry_leverage", debt.get("entry_leverage", 0))
    exit_leverage = summary.get("exit_leverage", debt.get("exit_leverage", 0))
    total_debt = summary.get("total_debt", debt.get("total_debt", 0))

    intro = ck_section_intro(
        eyebrow="DEBT MODEL",
        headline=f"{html.escape(deal_name)} — annual leverage trajectory.",
        italic_word="trajectory",
        body=(
            f"Entry {entry_leverage:.1f}x → exit {exit_leverage:.1f}x. "
            "Annual debt balance, mandatory repayment, interest "
            "expense, and leverage path through the hold."
        ),
    )
    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Entry Leverage", f"{entry_leverage:.1f}x",
            help={
                "definition": (
                    "Total debt ÷ EBITDA at acquisition close. PE "
                    "healthcare deals cluster at 5.5-6.5x; above 7x "
                    "signals an aggressive capital structure that "
                    "needs strong deleveraging or EBITDA growth to "
                    "clear covenants."
                ),
            },
        )
        + ck_kpi_block(
            "Exit Leverage", f"{exit_leverage:.1f}x",
            help={
                "definition": (
                    "Modeled debt-to-EBITDA at exit. Entry → Exit "
                    "gap is the deleveraging story. A 2-turn drop "
                    "(6.0x → 4.0x) over a 5-year hold is the typical "
                    "PE healthcare path; less = the deal leans more "
                    "on multiple expansion than operational delevering."
                ),
            },
        )
        + ck_kpi_block(
            "Total Debt at Entry", f"${total_debt/1e6:.0f}M",
            help={
                "definition": (
                    "Aggregate debt across senior, second-lien, and "
                    "mezz tranches at close. Determines the equity "
                    "check size given an enterprise value — and "
                    "determines covenant covenants. Compare against "
                    "the deal's annual EBITDA × 6.5 for a quick "
                    "leverage-headroom read."
                ),
            },
        )
        + '</div>'
    )

    rows = ""
    for yr in schedule:
        year = yr.get("year", "")
        balance = yr.get("balance", yr.get("debt_balance", 0))
        payment = yr.get("payment", yr.get("principal", 0))
        interest = yr.get("interest", yr.get("interest_expense", 0))
        leverage = yr.get("leverage", yr.get("net_debt_ebitda", 0))
        lev_cls = "cad-pos" if float(leverage) < 4 else (
            "cad-warn" if float(leverage) < 6 else "cad-neg")
        rows += (
            f'<tr>'
            f'<td class="num"><strong>Year {year}</strong></td>'
            f'<td class="num">${float(balance)/1e6:.1f}M</td>'
            f'<td class="num">${float(payment)/1e6:.1f}M</td>'
            f'<td class="num">${float(interest)/1e6:.1f}M</td>'
            f'<td class="num {lev_cls}">{float(leverage):.1f}x</td>'
            f'</tr>'
        )

    table = ck_panel(
        '<p class="ck-section-body">'
        'Annual debt balance, mandatory repayment, interest expense, and leverage trajectory.</p>'
        '<table class="cad-table"><thead><tr>'
        '<th>Year</th><th>Balance</th><th>Principal</th><th>Interest</th><th>Leverage</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>',
        title="Debt Schedule",
    ) if rows else ""

    actions = ck_panel(
        '<p class="ck-section-body">'
        f'<a href="/models/lbo/{html.escape(deal_id)}" class="cad-btn">LBO</a> '
        f'<a href="/models/waterfall/{html.escape(deal_id)}" class="cad-btn">Waterfall</a> '
        f'<a href="/deal/{html.escape(deal_id)}" class="cad-btn cad-btn-primary">Deal Dashboard</a>'
        '</p>',
        title="Cross-links",
    )

    # Interpretation
    deleverage = entry_leverage - exit_leverage
    interp = ck_panel(
        '<p class="ck-section-body">'
        f'Entry leverage of {entry_leverage:.1f}x deleverages to {exit_leverage:.1f}x '
        f'over the hold period — a {deleverage:.1f}x reduction. '
        f'{"Strong deleveraging — equity returns benefit from debt paydown." if deleverage > 2 else "Moderate deleveraging." if deleverage > 1 else "Limited deleveraging — returns must come from EBITDA growth."}</p>'
        '<p class="ck-section-body">Check the '
        f'<a href="/models/returns/{html.escape(deal_id)}" class="ck-link">returns & covenant</a> '
        'page to see how leverage affects covenant headroom.</p>',
        title="What This Means",
    ) if entry_leverage > 0 else ""

    nav = _model_nav(deal_id, "debt")
    next_up = ck_next_section(
        "Open returns & covenant",
        f"/models/returns/{html.escape(deal_id)}",
        eyebrow="Continue —",
        italic_word="returns",
    )
    body = f'{nav}{intro}{kpis}{table}{interp}{actions}{next_up}'
    return chartis_shell(body, f"Debt Model — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"Leverage: {entry_leverage:.1f}x entry → {exit_leverage:.1f}x exit")


def render_challenge_solver(deal_id: str, deal_name: str, result: Dict[str, Any]) -> str:
    """Render reverse challenge solver results."""
    target = result.get("target_ebitda_drag", result.get("target", 0))
    solutions = result.get("solutions", result.get("assumptions", []))

    intro = ck_section_intro(
        eyebrow="CHALLENGE SOLVER",
        headline=f"{html.escape(deal_name)} — what would have to be true.",
        italic_word="have",
        body=(
            "Reverse-solve: which KPI assumptions would have to "
            "hold to produce the target EBITDA drag? Frames the "
            "downside case in 'we believe X is unlikely' terms."
        ),
    )
    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Target EBITDA Drag", f"${abs(float(target))/1e6:.1f}M",
            help={
                "definition": (
                    "EBITDA drag level the challenge solver was asked "
                    "to reverse-engineer. The solver finds combinations "
                    "of input assumptions that would produce this "
                    "specific outcome — used to surface the 'what "
                    "breaks the deal?' scenarios partners want to "
                    "stress-test at IC."
                ),
            },
        )
        + ck_kpi_block(
            "Assumption Sets Found", f"{len(solutions)}",
            help={
                "definition": (
                    "Distinct assumption combinations that produce "
                    "the target outcome. Few sets = the failure mode "
                    "has a narrow trigger (one or two inputs); many "
                    "sets = the deal is broadly fragile and many "
                    "things could go wrong at once. The latter is "
                    "the harder bear case to refute."
                ),
            },
        )
        + '</div>'
    )

    rows = ""
    for s in solutions[:10]:
        desc = html.escape(str(s.get("description", s.get("scenario", ""))))
        kpi = html.escape(str(s.get("kpi", s.get("metric", ""))))
        required = s.get("required_value", s.get("value", 0))
        current = s.get("current_value", s.get("current", 0))
        rows += (
            f'<tr>'
            f'<td><strong>{desc or kpi}</strong></td>'
            f'<td class="num">{float(current):.2f}</td>'
            f'<td class="num cad-warn">{float(required):.2f}</td>'
            f'<td class="num">{abs(float(required)-float(current)):.2f}</td>'
            f'</tr>'
        )

    table = ck_panel(
        '<p class="ck-section-body">'
        'Shows what KPI assumptions would need to be true to produce the target EBITDA drag. '
        'Useful for IC presentations: "the deal fails only if denial rate exceeds X%."</p>'
        '<table class="cad-table"><thead><tr>'
        '<th>Assumption</th><th>Current</th><th>Required</th><th>Gap</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>',
        title="Reverse Challenge: What Hits the Target?",
    ) if rows else ""

    # Interpretation
    interp = ""
    if solutions:
        biggest = max(solutions, key=lambda s: abs(float(s.get("required_value", 0)) - float(s.get("current_value", 0))))
        biggest_kpi = str(biggest.get("description", biggest.get("kpi", "")))
        interp = ck_panel(
            '<p class="ck-section-body">'
            f'<strong>IC talking point:</strong> "The deal fails only if {html.escape(biggest_kpi.lower())}. '
            'We believe this scenario is unlikely because [your thesis here]."</p>'
            '<p class="ck-section-body">Use this analysis to frame the downside case in your IC memo. '
            f'See <a href="/models/denial/{html.escape(deal_id)}" class="ck-link">denial drivers</a> '
            f'for root cause analysis and <a href="/pressure?deal_id={html.escape(deal_id)}" class="ck-link">'
            'pressure test</a> for stress scenarios.</p>',
            title="What This Means",
        )

    nav = _model_nav(deal_id, "challenge")
    next_up = ck_next_section(
        "Open the pressure test",
        f"/pressure?deal_id={html.escape(deal_id)}",
        eyebrow="Continue —",
        italic_word="pressure",
    )
    body = f'{nav}{intro}{kpis}{table}{interp}{next_up}'
    return chartis_shell(body, f"Challenge Solver — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle="Reverse solver: what breaks the deal?")


def render_irs990_crosscheck(deal_id: str, deal_name: str, data: Dict[str, Any]) -> str:
    """Render IRS 990 cross-check for non-profit hospitals."""
    match = data.get("match", {})
    comparisons = data.get("comparisons", [])
    is_nonprofit = data.get("is_nonprofit", False)

    status = "Non-Profit (990 Filed)" if is_nonprofit else "For-Profit or No 990 Found"
    status_badge = ck_signal_badge(
        status, tone="positive" if is_nonprofit else "neutral",
    )

    intro = ck_section_intro(
        eyebrow="IRS 990 CROSS-CHECK",
        headline=f"{html.escape(deal_name)} — non-profit reconciliation.",
        italic_word="reconciliation",
        body=(
            "Compares HCRIS cost-report figures against IRS Form 990 "
            "filings. Large discrepancies (>25%) flag either data "
            "quality issues or genuine timing differences."
        ),
    )
    kpi_inner = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Tax Status", status_badge)
    )
    if match:
        rev_990 = match.get("total_revenue", 0)
        assets = match.get("total_assets", 0)
        kpi_inner += (
            ck_kpi_block("990 Total Revenue", f"${float(rev_990)/1e6:.0f}M")
            + ck_kpi_block("990 Total Assets", f"${float(assets)/1e6:.0f}M")
        )
    kpis = kpi_inner + '</div>'

    comp_rows = ""
    for c in comparisons:
        field = html.escape(str(c.get("field", "")))
        hcris_val = c.get("hcris_value", 0)
        irs_val = c.get("irs_value", 0)
        diff = c.get("difference_pct", 0)
        cls = "cad-pos" if abs(float(diff)) < 10 else (
            "cad-warn" if abs(float(diff)) < 25 else "cad-neg")
        comp_rows += (
            f'<tr><td>{field}</td>'
            f'<td class="num">${float(hcris_val)/1e6:.1f}M</td>'
            f'<td class="num">${float(irs_val)/1e6:.1f}M</td>'
            f'<td class="num {cls}">{float(diff):+.1f}%</td></tr>'
        )

    comp_table = ck_panel(
        '<p class="ck-section-body">'
        'Compares HCRIS cost report figures against IRS Form 990 filings. '
        'Large discrepancies (&gt;25%) may indicate data quality issues or timing differences.</p>'
        '<table class="cad-table"><thead><tr>'
        '<th>Field</th><th>HCRIS</th><th>IRS 990</th><th>Difference</th>'
        f'</tr></thead><tbody>{comp_rows}</tbody></table>',
        title="HCRIS vs IRS 990 Cross-Check",
    ) if comp_rows else ck_panel(
        '<p class="ck-section-body">'
        'No IRS 990 data available for cross-checking. '
        'This hospital may be for-profit or the 990 has not been filed/loaded.</p>',
        title="IRS 990 Cross-Check",
    )

    nav = _model_nav(deal_id, "irs990")
    body = f'{nav}{intro}{kpis}{comp_table}'
    return chartis_shell(body, f"IRS 990 Cross-Check — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle="Non-profit hospital financial verification")


def render_trend_forecast(deal_id: str, deal_name: str, trends: List[Dict[str, Any]]) -> str:
    """Render temporal trend detection and forecasts."""
    rows = ""
    for t in trends:
        metric = html.escape(str(t.get("metric", t.get("kpi", ""))))
        direction = t.get("direction", t.get("trend", "flat"))
        slope = t.get("slope", t.get("change_per_quarter", 0))
        forecast = t.get("forecast_next", t.get("predicted", 0))
        confidence = t.get("confidence", t.get("r2", 0))
        dir_cls = "cad-pos" if "improv" in str(direction).lower() or slope > 0 else (
            "cad-neg" if "deteri" in str(direction).lower() or slope < 0 else "")
        dir_icon = "&#9650;" if slope > 0 else ("&#9660;" if slope < 0 else "&#9654;")
        rows += (
            f'<tr>'
            f'<td><strong>{metric}</strong></td>'
            f'<td class="{dir_cls}">{dir_icon} {html.escape(str(direction))}</td>'
            f'<td class="num {dir_cls}">{float(slope):+.3f}/qtr</td>'
            f'<td class="num">{float(forecast):.2f}</td>'
            f'<td class="num">{float(confidence):.0%}</td>'
            f'</tr>'
        )

    improving = sum(1 for t in trends if float(t.get("slope", 0)) > 0)
    declining = sum(1 for t in trends if float(t.get("slope", 0)) < 0)

    intro = ck_section_intro(
        eyebrow="TREND FORECAST",
        headline=f"{html.escape(deal_name)} — where the metrics are heading.",
        italic_word="heading",
        body=(
            f"{len(trends)} time-series trends detected · {improving} improving, "
            f"{declining} declining. Per-metric slope, direction, "
            "and short-horizon forecast against the latest priors."
        ),
    )
    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Metrics Tracked", f"{len(trends)}")
        + ck_kpi_block(
            "Improving", f"{improving}",
            help={
                "definition": (
                    "Metrics with positive slope across the most-"
                    "recent four quarters. The 'winds at our back' "
                    "set — if improving outnumbers declining 2:1, "
                    "the operating team is executing; 1:1 = mixed "
                    "performance; declining-dominant = a turnaround "
                    "story the partner is still mid-execution."
                ),
            },
        )
        + ck_kpi_block(
            "Declining", f"{declining}",
            help={
                "definition": (
                    "Metrics with negative slope across the most-"
                    "recent four quarters. Watch the table below for "
                    "which specific KPIs are dragging — a few "
                    "concentrated declines (say, denial rate + AR "
                    "days) signal a fixable RCM issue, while broad "
                    "declines across margin + volume + payer mix "
                    "signal structural sector exposure."
                ),
            },
        )
        + '</div>'
    )

    nav = _model_nav(deal_id, "trends")
    slope_chart = _trend_slope_chart(trends)
    slope_caption = (
        '<div class="at-chart-caption">'
        'Quarterly slope per metric · bar opacity scales with confidence (r²)'
        '</div>'
    ) if slope_chart else ""
    body = (
        f'{_AT_CHART_CAPTION_CSS}{nav}{intro}{kpis}'
        + ck_panel(
            '<p class="ck-section-body">'
            'Per-metric time-series trend detection with short-horizon forecasts. '
            'Direction and slope estimated from historical data points.</p>'
            + slope_chart + slope_caption +
            '<table class="cad-table"><thead><tr>'
            '<th>Metric</th><th>Direction</th><th>Slope</th><th>Next Forecast</th><th>Confidence</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>',
            title="Trend Detection & Forecast",
        )
        + ck_panel(
            '<p class="ck-section-body">'
            f'<a href="/models/anomalies/{html.escape(deal_id)}" class="cad-btn">Anomaly Detection</a> '
            f'<a href="/deal/{html.escape(deal_id)}" class="cad-btn cad-btn-primary">Deal Dashboard</a>'
            '</p>',
            title="Cross-links",
        )
        + ck_next_section(
            "Open anomaly detection",
            f"/models/anomalies/{html.escape(deal_id)}",
            eyebrow="Continue —",
            italic_word="anomaly",
        )
    )

    return chartis_shell(body, f"Trend Forecast — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"{improving} improving, {declining} declining across {len(trends)} metrics")
