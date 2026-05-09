"""SeekingChartis Advanced Tools — debt model, challenge solver, IRS 990, trends.

Connects remaining high-value backend modules to browser pages.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from ._chartis_kit import chartis_shell
from .models_page import _model_nav
from .brand import PALETTE


def render_debt_model(deal_id: str, deal_name: str, debt: Dict[str, Any]) -> str:
    """Render debt trajectory projections."""
    schedule = debt.get("schedule", debt.get("years", []))
    summary = debt.get("summary", {})
    entry_leverage = summary.get("entry_leverage", debt.get("entry_leverage", 0))
    exit_leverage = summary.get("exit_leverage", debt.get("exit_leverage", 0))
    total_debt = summary.get("total_debt", debt.get("total_debt", 0))

    # P26 follow-up: debt-summary KPIs migrated to kpi_strip.
    from ._ui_kit import kpi_strip
    exit_tone = (
        "positive" if exit_leverage < 4
        else "warning" if exit_leverage < 6
        else "negative"
    )
    kpis = kpi_strip([
        {"label": "Entry Leverage", "value": f"{entry_leverage:.1f}x"},
        {"label": "Exit Leverage", "value": f"{exit_leverage:.1f}x", "tone": exit_tone},
        {"label": "Total Debt at Entry", "value": f"${total_debt/1e6:.2f}M"},
    ])

    rows = ""
    for yr in schedule:
        year = yr.get("year", "")
        balance = yr.get("balance", yr.get("debt_balance", 0))
        payment = yr.get("payment", yr.get("principal", 0))
        interest = yr.get("interest", yr.get("interest_expense", 0))
        leverage = yr.get("leverage", yr.get("net_debt_ebitda", 0))
        lev_color = PALETTE["positive"] if float(leverage) < 4 else (
            PALETTE["warning"] if float(leverage) < 6 else PALETTE["negative"])
        rows += (
            f'<tr>'
            f'<td class="num" style="font-weight:600;">Year {year}</td>'
            f'<td class="num">${float(balance)/1e6:.2f}M</td>'
            f'<td class="num">${float(payment)/1e6:.2f}M</td>'
            f'<td class="num">${float(interest)/1e6:.2f}M</td>'
            f'<td class="num" style="color:{lev_color};">{float(leverage):.1f}x</td>'
            f'</tr>'
        )

    table = (
        f'<div class="cad-card">'
        f'<h2>Debt Schedule</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:10px;">'
        f'Annual debt balance, mandatory repayment, interest expense, and leverage trajectory.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Year</th><th>Balance</th><th>Principal</th><th>Interest</th><th>Leverage</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
    ) if rows else ""

    actions = (
        f'<div class="cad-card" style="display:flex;gap:8px;">'
        f'<a href="/models/lbo/{html.escape(deal_id)}" class="cad-btn" style="text-decoration:none;">LBO</a>'
        f'<a href="/models/waterfall/{html.escape(deal_id)}" class="cad-btn" style="text-decoration:none;">Waterfall</a>'
        f'<a href="/deal/{html.escape(deal_id)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Deal Dashboard</a></div>'
    )

    # Interpretation
    deleverage = entry_leverage - exit_leverage
    interp = (
        f'<div class="cad-card" style="border-left:3px solid {PALETTE["brand_accent"]};">'
        f'<h2>What This Means</h2>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'<p>Entry leverage of {entry_leverage:.1f}x deleverages to {exit_leverage:.1f}x '
        f'over the hold period — a {deleverage:.1f}x reduction. '
        f'{"Strong deleveraging — equity returns benefit from debt paydown." if deleverage > 2 else "Moderate deleveraging." if deleverage > 1 else "Limited deleveraging — returns must come from EBITDA growth."}</p>'
        f'<p style="margin-top:6px;">Check the '
        f'<a href="/models/returns/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">returns & covenant</a> '
        f'page to see how leverage affects covenant headroom.</p>'
        f'</div></div>'
    ) if entry_leverage > 0 else ""

    nav = _model_nav(deal_id, "debt")
    body = f'{nav}{kpis}{table}{interp}{actions}'
    return chartis_shell(body, f"Debt Model — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"Leverage: {entry_leverage:.1f}x entry → {exit_leverage:.1f}x exit")


def render_challenge_solver(deal_id: str, deal_name: str, result: Dict[str, Any]) -> str:
    """Render reverse challenge solver results."""
    target = result.get("target_ebitda_drag", result.get("target", 0))
    solutions = result.get("solutions", result.get("assumptions", []))

    # P26 follow-up: challenge-solver summary migrated to kpi_strip.
    from ._ui_kit import kpi_strip
    kpis = kpi_strip([
        {"label": "Target EBITDA Drag", "value": f"${abs(float(target))/1e6:.2f}M"},
        {"label": "Assumption Sets Found", "value": str(len(solutions))},
    ])

    rows = ""
    for s in solutions[:10]:
        desc = html.escape(str(s.get("description", s.get("scenario", ""))))
        kpi = html.escape(str(s.get("kpi", s.get("metric", ""))))
        required = s.get("required_value", s.get("value", 0))
        current = s.get("current_value", s.get("current", 0))
        rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{desc or kpi}</td>'
            f'<td class="num">{float(current):.2f}</td>'
            f'<td class="num" style="color:{PALETTE["warning"]};">{float(required):.2f}</td>'
            f'<td class="num">{abs(float(required)-float(current)):.2f}</td>'
            f'</tr>'
        )

    table = (
        f'<div class="cad-card">'
        f'<h2>Reverse Challenge: What Hits the Target?</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:10px;">'
        f'Shows what KPI assumptions would need to be true to produce the target EBITDA drag. '
        f'Useful for IC presentations: "the deal fails only if denial rate exceeds X%."</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Assumption</th><th>Current</th><th>Required</th><th>Gap</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
    ) if rows else ""

    # Interpretation
    interp = ""
    if solutions:
        biggest = max(solutions, key=lambda s: abs(float(s.get("required_value", 0)) - float(s.get("current_value", 0))))
        biggest_kpi = str(biggest.get("description", biggest.get("kpi", "")))
        interp = (
            f'<div class="cad-card" style="border-left:3px solid {PALETTE["warning"]};">'
            f'<h2>What This Means</h2>'
            f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
            f'<p><strong>IC talking point:</strong> "The deal fails only if {html.escape(biggest_kpi.lower())}. '
            f'We believe this scenario is unlikely because [your thesis here]."</p>'
            f'<p style="margin-top:6px;">Use this analysis to frame the downside case in your IC memo. '
            f'See <a href="/models/denial/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">denial drivers</a> '
            f'for root cause analysis and <a href="/pressure?deal_id={html.escape(deal_id)}" '
            f'style="color:{PALETTE["text_link"]};">pressure test</a> for stress scenarios.</p>'
            f'</div></div>'
        )

    nav = _model_nav(deal_id, "challenge")
    body = f'{nav}{kpis}{table}{interp}'
    return chartis_shell(body, f"Challenge Solver — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle="Reverse solver: what breaks the deal?")


def render_irs990_crosscheck(deal_id: str, deal_name: str, data: Dict[str, Any]) -> str:
    """Render IRS 990 cross-check for non-profit hospitals."""
    match = data.get("match", {})
    comparisons = data.get("comparisons", [])
    is_nonprofit = data.get("is_nonprofit", False)

    status = "Non-Profit (990 Filed)" if is_nonprofit else "For-Profit or No 990 Found"
    status_cls = "cad-badge-green" if is_nonprofit else "cad-badge-muted"

    # P26 follow-up: 990-cross-check summary migrated to kpi_strip.
    # The legacy block conditionally appended Revenue + Assets tiles
    # when the match had data; the migration uses list-append to keep
    # that conditional behaviour intact.
    from ._ui_kit import kpi_strip
    irs_items: list[dict] = [
        {"label": "Tax Status",
         "value": (
             f'<span class="cad-badge {status_cls}" '
             f'style="font-size:13px;padding:4px 12px;">{status}</span>'
         )},
    ]
    if match:
        rev_990 = match.get("total_revenue", 0)
        assets = match.get("total_assets", 0)
        irs_items.append({"label": "990 Total Revenue",
                          "value": f"${float(rev_990)/1e6:.2f}M"})
        irs_items.append({"label": "990 Total Assets",
                          "value": f"${float(assets)/1e6:.2f}M"})
    kpis = kpi_strip(irs_items)

    comp_rows = ""
    for c in comparisons:
        field = html.escape(str(c.get("field", "")))
        hcris_val = c.get("hcris_value", 0)
        irs_val = c.get("irs_value", 0)
        diff = c.get("difference_pct", 0)
        color = PALETTE["positive"] if abs(float(diff)) < 10 else (
            PALETTE["warning"] if abs(float(diff)) < 25 else PALETTE["negative"])
        comp_rows += (
            f'<tr><td>{field}</td>'
            f'<td class="num">${float(hcris_val)/1e6:.2f}M</td>'
            f'<td class="num">${float(irs_val)/1e6:.2f}M</td>'
            f'<td class="num" style="color:{color};">{float(diff):+.1f}%</td></tr>'
        )

    comp_table = (
        f'<div class="cad-card">'
        f'<h2>HCRIS vs IRS 990 Cross-Check</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:10px;">'
        f'Compares HCRIS cost report figures against IRS Form 990 filings. '
        f'Large discrepancies (&gt;25%) may indicate data quality issues or timing differences.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Field</th><th>HCRIS</th><th>IRS 990</th><th>Difference</th>'
        f'</tr></thead><tbody>{comp_rows}</tbody></table></div>'
    ) if comp_rows else (
        f'<div class="cad-card"><p style="color:{PALETTE["text_muted"]};">'
        f'No IRS 990 data available for cross-checking. '
        f'This hospital may be for-profit or the 990 has not been filed/loaded.</p></div>'
    )

    nav = _model_nav(deal_id, "irs990")
    body = f'{nav}{kpis}{comp_table}'
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
        dir_color = PALETTE["positive"] if "improv" in str(direction).lower() or slope > 0 else (
            PALETTE["negative"] if "deteri" in str(direction).lower() or slope < 0 else PALETTE["text_muted"])
        dir_icon = "&#9650;" if slope > 0 else ("&#9660;" if slope < 0 else "&#9654;")
        rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{metric}</td>'
            f'<td style="color:{dir_color};">{dir_icon} {html.escape(str(direction))}</td>'
            f'<td class="num" style="color:{dir_color};">{float(slope):+.3f}/qtr</td>'
            f'<td class="num">{float(forecast):.2f}</td>'
            f'<td class="num">{float(confidence):.0%}</td>'
            f'</tr>'
        )

    improving = sum(1 for t in trends if float(t.get("slope", 0)) > 0)
    declining = sum(1 for t in trends if float(t.get("slope", 0)) < 0)

    nav = _model_nav(deal_id, "trends")
    # P26 follow-up: trend-summary KPIs migrated to kpi_strip. The
    # tone field carries improving/declining color signal that the
    # legacy inline-color attribute carried.
    from ._ui_kit import kpi_strip
    trend_kpis = kpi_strip([
        {"label": "Metrics Tracked", "value": str(len(trends))},
        {"label": "Improving", "value": str(improving),
         "tone": "positive" if improving else "neutral"},
        {"label": "Declining", "value": str(declining),
         "tone": "negative" if declining else "neutral"},
    ])
    body = (
        f'{nav}'
        f'{trend_kpis}'

        f'<div class="cad-card">'
        f'<h2>Trend Detection &amp; Forecast</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:10px;">'
        f'Per-metric time-series trend detection with short-horizon forecasts. '
        f'Direction and slope estimated from historical data points.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Metric</th><th>Direction</th><th>Slope</th><th>Next Forecast</th><th>Confidence</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'

        f'<div class="cad-card" style="display:flex;gap:8px;">'
        f'<a href="/models/anomalies/{html.escape(deal_id)}" class="cad-btn" style="text-decoration:none;">'
        f'Anomaly Detection</a>'
        f'<a href="/deal/{html.escape(deal_id)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Deal Dashboard</a></div>'
    )

    return chartis_shell(body, f"Trend Forecast — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"{improving} improving, {declining} declining across {len(trends)} metrics")
