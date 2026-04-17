"""SeekingChartis Hospital History — multi-year financial timeline.

Treats each hospital like a stock: historical financials, YoY growth,
COVID resilience, peer comparison, and trend projections.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .shell_v2 import shell_v2
from .brand import PALETTE


def _fmt_m(val: Any) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    try:
        v = float(val)
        if abs(v) >= 1e9:
            return f"${v/1e9:.1f}B"
        return f"${v/1e6:.0f}M"
    except (TypeError, ValueError):
        return "—"


def _growth(curr: float, prev: float) -> Tuple[str, str]:
    """Returns (formatted growth, color)."""
    if prev == 0 or curr == 0:
        return "—", PALETTE["text_muted"]
    g = (curr - prev) / abs(prev)
    color = PALETTE["positive"] if g > 0.01 else (PALETTE["negative"] if g < -0.01 else PALETTE["text_muted"])
    return f"{g:+.1%}", color


def _trend_arrow(values: List[float]) -> Tuple[str, str]:
    """Simple trend from a list of values: arrow + color."""
    if len(values) < 2:
        return "—", PALETTE["text_muted"]
    if values[-1] > values[0] * 1.02:
        return "&#9650; Growing", PALETTE["positive"]
    elif values[-1] < values[0] * 0.98:
        return "&#9660; Declining", PALETTE["negative"]
    return "&#9654; Stable", PALETTE["text_muted"]


def _cagr(start: float, end: float, years: int) -> float:
    if start <= 0 or end <= 0 or years <= 0:
        return 0
    return (end / start) ** (1 / years) - 1


def _covid_resilience_score(trend_df: pd.DataFrame) -> Tuple[int, str]:
    """Score 0-100 based on COVID-era performance vs peers.

    Factors: margin change 2020→2022, revenue recovery, bed stability.
    """
    if len(trend_df) < 2:
        return 50, "Insufficient data"

    rev_col = "net_patient_revenue"
    opex_col = "operating_expenses"

    scores = []
    revs = trend_df[rev_col].fillna(0).tolist() if rev_col in trend_df.columns else []
    opexs = trend_df[opex_col].fillna(0).tolist() if opex_col in trend_df.columns else []

    # Revenue recovery: did they grow through COVID?
    if len(revs) >= 2 and revs[0] > 0:
        rev_growth = (revs[-1] - revs[0]) / revs[0]
        scores.append(min(100, max(0, 50 + rev_growth * 200)))

    # Margin trajectory: improving or compressing?
    margins = []
    for r, o in zip(revs, opexs):
        if r > 1e5 and o > 0:
            margins.append(max(-1, min(1, (r - o) / r)))
    if len(margins) >= 2:
        margin_change = margins[-1] - margins[0]
        scores.append(min(100, max(0, 50 + margin_change * 500)))

    # Bed stability
    beds = trend_df["beds"].fillna(0).tolist() if "beds" in trend_df.columns else []
    if len(beds) >= 2 and beds[0] > 0:
        bed_change = (beds[-1] - beds[0]) / beds[0]
        scores.append(min(100, max(0, 50 + bed_change * 200)))

    if not scores:
        return 50, "Insufficient data"

    score = int(np.mean(scores))
    if score >= 75:
        label = "Resilient — strong COVID recovery"
    elif score >= 55:
        label = "Moderate — some COVID impact but recovering"
    elif score >= 40:
        label = "Stressed — slow recovery from COVID"
    else:
        label = "Distressed — significant COVID damage"

    return score, label


def render_hospital_history(
    ccn: str,
    name: str,
    trend_df: pd.DataFrame,
    state: str = "",
    peer_avg: Optional[Dict[str, List[float]]] = None,
    projections: Optional[Dict[str, List[float]]] = None,
) -> str:
    """Render multi-year hospital financial history."""
    ccn_esc = html.escape(ccn)
    name_esc = html.escape(name)
    state_esc = html.escape(state)
    years = sorted(trend_df["fiscal_year"].unique()) if "fiscal_year" in trend_df.columns else []
    n_years = len(years)

    rev_col = "net_patient_revenue"
    opex_col = "operating_expenses"

    # === Financial Timeline Table ===
    header = "".join(f'<th>FY{int(y)}</th>' for y in years)
    if n_years >= 2:
        header += '<th>YoY (Latest)</th><th>CAGR</th>'

    metrics_to_show = [
        ("Net Patient Revenue", rev_col, True),
        ("Operating Expenses", opex_col, True),
        ("Operating Margin", "_margin", False),
        ("Net Income", "net_income", True),
        ("Licensed Beds", "beds", False),
        ("Total Patient Days", "total_patient_days", False),
        ("Medicare Day %", "medicare_day_pct", False),
        ("Medicaid Day %", "medicaid_day_pct", False),
    ]

    table_rows = ""
    for label, key, is_money in metrics_to_show:
        cells = ""
        values = []
        for y in years:
            yr_data = trend_df[trend_df["fiscal_year"] == y]
            if yr_data.empty:
                cells += '<td class="num">—</td>'
                values.append(0)
                continue

            row = yr_data.iloc[0]
            if key == "_margin":
                r = float(row.get(rev_col, 0))
                o = float(row.get(opex_col, 0))
                val = (r - o) / r if r > 1e5 and o > 0 else 0
                val = max(-1, min(1, val))
                color = PALETTE["positive"] if val > 0.02 else (PALETTE["negative"] if val < -0.02 else PALETTE["text_muted"])
                cells += f'<td class="num" style="color:{color};">{val:.1%}</td>'
                values.append(val)
            elif is_money:
                val = float(row.get(key, 0))
                cells += f'<td class="num">{_fmt_m(val)}</td>'
                values.append(val)
            elif "pct" in key:
                val = float(row.get(key, 0))
                cells += f'<td class="num">{val:.0%}</td>'
                values.append(val)
            else:
                val = row.get(key, 0)
                try:
                    val = float(val)
                    cells += f'<td class="num">{val:,.0f}</td>'
                except (TypeError, ValueError):
                    cells += f'<td class="num">—</td>'
                    val = 0
                values.append(val)

        # YoY and CAGR
        yoy_cell = ""
        cagr_cell = ""
        if n_years >= 2 and len(values) >= 2:
            yoy_str, yoy_color = _growth(values[-1], values[-2])
            yoy_cell = f'<td class="num" style="color:{yoy_color};font-weight:600;">{yoy_str}</td>'
            cagr_val = _cagr(values[0], values[-1], n_years - 1) if values[0] != 0 else 0
            cagr_color = PALETTE["positive"] if cagr_val > 0.01 else (PALETTE["negative"] if cagr_val < -0.01 else PALETTE["text_muted"])
            cagr_cell = f'<td class="num" style="color:{cagr_color};">{cagr_val:+.1%}</td>'

        table_rows += f'<tr><td style="font-weight:500;">{html.escape(label)}</td>{cells}{yoy_cell}{cagr_cell}</tr>'

    timeline_table = (
        f'<div class="cad-card">'
        f'<h2>Financial Timeline</h2>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Metric</th>{header}'
        f'</tr></thead><tbody>{table_rows}</tbody></table></div>'
    )

    # === KPI Summary ===
    revs = []
    margins = []
    for y in years:
        yr_data = trend_df[trend_df["fiscal_year"] == y]
        if not yr_data.empty:
            r = float(yr_data.iloc[0].get(rev_col, 0))
            o = float(yr_data.iloc[0].get(opex_col, 0))
            revs.append(r)
            if r > 1e5 and o > 0:
                margins.append(max(-1, min(1, (r - o) / r)))

    rev_cagr = _cagr(revs[0], revs[-1], n_years - 1) if len(revs) >= 2 and revs[0] > 0 else 0
    rev_arrow, rev_color = _trend_arrow(revs)
    margin_arrow, margin_color = _trend_arrow(margins)
    covid_score, covid_label = _covid_resilience_score(trend_df)
    covid_color = PALETTE["positive"] if covid_score >= 65 else (PALETTE["warning"] if covid_score >= 45 else PALETTE["negative"])

    kpis = (
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fmt_m(revs[-1]) if revs else "—"}</div>'
        f'<div class="cad-kpi-label">Latest Revenue (FY{int(years[-1]) if years else "?"})</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{rev_color};">{rev_cagr:+.1%}</div>'
        f'<div class="cad-kpi-label">Revenue CAGR ({n_years}yr)</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{margin_color};">'
        f'{margins[-1]:.1%}</div>' if margins else f'—</div>'
        f'<div class="cad-kpi-label">Latest Margin</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{covid_color};">'
        f'{covid_score}/100</div>'
        f'<div class="cad-kpi-label">COVID Resilience</div></div>'
        f'</div>'
    )

    # === COVID Impact Analysis ===
    covid_section = ""
    if n_years >= 2 and 2020 in years:
        fy20 = trend_df[trend_df["fiscal_year"] == 2020].iloc[0] if not trend_df[trend_df["fiscal_year"] == 2020].empty else None
        latest = trend_df[trend_df["fiscal_year"] == years[-1]].iloc[0] if not trend_df[trend_df["fiscal_year"] == years[-1]].empty else None

        if fy20 is not None and latest is not None:
            rev_20 = float(fy20.get(rev_col, 0))
            rev_latest = float(latest.get(rev_col, 0))
            recovery = (rev_latest - rev_20) / rev_20 if rev_20 > 0 else 0

            covid_section = (
                f'<div class="cad-card" style="border-left:3px solid {covid_color};">'
                f'<h2>COVID Impact & Recovery</h2>'
                f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
                f'<p><strong>Resilience Score: {covid_score}/100</strong> — {html.escape(covid_label)}</p>'
                f'<p>Revenue recovery from FY2020 to FY{int(years[-1])}: '
                f'<strong style="color:{PALETTE["positive"] if recovery > 0 else PALETTE["negative"]};">'
                f'{recovery:+.1%}</strong> ({_fmt_m(rev_20)} → {_fmt_m(rev_latest)})</p>'
                f'<p style="margin-top:6px;">FY2020 captured the initial COVID shock. '
                f'{"Strong recovery indicates operational resilience and payer diversification." if recovery > 0.05 else "Slow recovery suggests structural challenges beyond COVID."}'
                f'</p></div></div>'
            )

    # === Trend Direction Summary ===
    trend_items = ""
    metric_trends = [
        ("Revenue", revs, False),
        ("Operating Margin", margins, False),
    ]
    beds_list = trend_df["beds"].fillna(0).tolist() if "beds" in trend_df.columns else []
    if beds_list:
        metric_trends.append(("Beds", [float(b) for b in beds_list], False))
    med_list = trend_df["medicare_day_pct"].fillna(0).tolist() if "medicare_day_pct" in trend_df.columns else []
    if med_list:
        metric_trends.append(("Medicare Mix", [float(m) for m in med_list], True))

    for label, vals, invert in metric_trends:
        if len(vals) < 2:
            continue
        arrow, color = _trend_arrow(vals if not invert else [-v for v in vals])
        trend_items += (
            f'<div style="display:flex;justify-content:space-between;padding:6px 0;'
            f'border-bottom:1px solid {PALETTE["border"]};">'
            f'<span>{html.escape(label)}</span>'
            f'<span style="color:{color};">{arrow}</span></div>'
        )

    trend_section = (
        f'<div class="cad-card">'
        f'<h2>Trend Summary</h2>'
        f'{trend_items}</div>'
    ) if trend_items else ""

    # === Peer Comparison ===
    peer_section = ""
    if peer_avg and revs:
        peer_revs = peer_avg.get("revenue", [])
        peer_margins = peer_avg.get("margin", [])
        if peer_revs and peer_margins:
            peer_section = (
                f'<div class="cad-card">'
                f'<h2>vs State Average ({state_esc})</h2>'
                f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">'
                f'<div>'
                f'<div style="font-size:12px;color:{PALETTE["text_muted"]};margin-bottom:4px;">Revenue Growth</div>'
                f'<div style="display:flex;gap:12px;">'
                f'<div><span class="cad-mono" style="font-size:16px;">{rev_cagr:+.1%}</span>'
                f'<div style="font-size:10px;color:{PALETTE["text_muted"]};">This Hospital</div></div>'
                f'<div><span class="cad-mono" style="font-size:16px;">'
                f'{_cagr(peer_revs[0], peer_revs[-1], len(peer_revs)-1):+.1%}</span>'
                f'<div style="font-size:10px;color:{PALETTE["text_muted"]};">State Avg</div></div>'
                f'</div></div>'
                f'<div>'
                f'<div style="font-size:12px;color:{PALETTE["text_muted"]};margin-bottom:4px;">Latest Margin</div>'
                f'<div style="display:flex;gap:12px;">'
                f'<div><span class="cad-mono" style="font-size:16px;">{margins[-1]:.1%}</span>'
                f'<div style="font-size:10px;color:{PALETTE["text_muted"]};">This Hospital</div></div>'
                f'<div><span class="cad-mono" style="font-size:16px;">{peer_margins[-1]:.1%}</span>'
                f'<div style="font-size:10px;color:{PALETTE["text_muted"]};">State Avg</div></div>'
                f'</div></div>'
                f'</div></div>'
            )

    # === Projections ===
    proj_section = ""
    if projections and revs:
        proj_revs = projections.get("revenue", [])
        proj_margins = projections.get("margin", [])
        if proj_revs:
            proj_rows = ""
            for i, pr in enumerate(proj_revs[:3]):
                yr = int(years[-1]) + i + 1 if years else 2023 + i
                pm = proj_margins[i] if i < len(proj_margins) else margins[-1] if margins else 0
                proj_rows += (
                    f'<tr>'
                    f'<td class="num" style="font-weight:600;">FY{yr} (proj)</td>'
                    f'<td class="num">{_fmt_m(pr)}</td>'
                    f'<td class="num">{pm:.1%}</td>'
                    f'</tr>'
                )
            proj_section = (
                f'<div class="cad-card">'
                f'<h2>Projections (FY{int(years[-1])+1 if years else 2023}-{int(years[-1])+3 if years else 2025})</h2>'
                f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:8px;">'
                f'Extrapolated from {n_years}-year trend using linear projection. '
                f'Does not account for regulatory or market changes.</p>'
                f'<table class="cad-table"><thead><tr>'
                f'<th>Year</th><th>Revenue (proj)</th><th>Margin (proj)</th>'
                f'</tr></thead><tbody>{proj_rows}</tbody></table></div>'
            )

    # === Actions ===
    actions = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/hospital/{ccn_esc}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Hospital Profile</a>'
        f'<a href="/models/dcf/{ccn_esc}" class="cad-btn" style="text-decoration:none;">DCF Model</a>'
        f'<a href="/models/market/{ccn_esc}" class="cad-btn" style="text-decoration:none;">Market Analysis</a>'
        f'<a href="/models/comparables/{ccn_esc}" class="cad-btn" style="text-decoration:none;">Comparables</a>'
        f'<a href="/market-data/state/{state_esc}" class="cad-btn" style="text-decoration:none;">'
        f'{state_esc} Market</a>'
        f'</div>'
    )

    body = f'{kpis}{timeline_table}{covid_section}{trend_section}{peer_section}{proj_section}{actions}'

    return shell_v2(
        body, f"{name_esc} — History",
        active_nav="/market-data/map",
        subtitle=f"CCN {ccn_esc} | {n_years}-year financial timeline | COVID resilience: {covid_score}/100",
    )
