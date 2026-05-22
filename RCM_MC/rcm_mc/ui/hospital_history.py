"""PE Desk Hospital History — multi-year financial timeline.

Treats each hospital like a stock: historical financials, YoY growth,
COVID resilience, peer comparison, and trend projections.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_next_section, ck_panel,
    ck_section_intro, ck_sparkline,
)
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
                cls = "cad-pos" if val > 0.02 else ("cad-neg" if val < -0.02 else "")
                cells += f'<td class="num {cls}">{val:.1%}</td>'
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
            yoy_cls = "cad-pos" if yoy_color == PALETTE["positive"] else ("cad-neg" if yoy_color == PALETTE["negative"] else "")
            yoy_cell = f'<td class="num {yoy_cls}"><strong>{yoy_str}</strong></td>'
            cagr_val = _cagr(values[0], values[-1], n_years - 1) if values[0] != 0 else 0
            cagr_cls = "cad-pos" if cagr_val > 0.01 else ("cad-neg" if cagr_val < -0.01 else "")
            cagr_cell = f'<td class="num {cagr_cls}">{cagr_val:+.1%}</td>'

        table_rows += f'<tr><td><strong>{html.escape(label)}</strong></td>{cells}{yoy_cell}{cagr_cell}</tr>'

    timeline_table = ck_panel(
        '<table class="cad-table"><thead><tr>'
        f'<th>Metric</th>{header}'
        f'</tr></thead><tbody>{table_rows}</tbody></table>',
        title="Financial Timeline",
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

    intro = ck_section_intro(
        eyebrow=f"HOSPITAL HISTORY · CCN {ccn_esc}",
        headline=f"{name_esc} — multi-year financial timeline.",
        italic_word="timeline",
        body=(
            f"{n_years}-year revenue, margin, payer-mix, and bed "
            "trajectory. Treats the hospital like a stock: CAGR, "
            "YoY growth, COVID resilience, and peer comparison "
            "side-by-side."
        ),
    )
    # Sparklines for the trajectory KPIs — both have time-series
    # data already on hand. ck_sparkline returns empty for <2 points
    # so it self-suppresses on thin datasets.
    rev_spark = ck_sparkline(revs) if revs else None
    margin_spark = ck_sparkline(margins) if margins else None
    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            f"Latest Revenue (FY{int(years[-1]) if years else '?'})",
            _fmt_m(revs[-1]) if revs else "—",
            chart=rev_spark,
            help={
                "definition": (
                    "Most-recent fiscal-year revenue from CMS HCRIS. "
                    "Lags the calendar by ~18 months due to filing "
                    "cadence; treat as a structural baseline, not a "
                    "current quarter."
                ),
                "citation": "CMS HCRIS",
            },
        )
        + ck_kpi_block(
            f"Revenue CAGR ({n_years}yr)", f"{rev_cagr:+.1%}",
            chart=rev_spark,
            help={
                "definition": (
                    "Compound annual growth rate of revenue across "
                    "the available HCRIS years. Healthcare margins "
                    "are tight — partners look for 3-6% organic "
                    "growth in community hospitals; >10% usually "
                    "means a step-change (acquisition, service-line "
                    "launch) worth understanding separately."
                ),
            },
        )
        + ck_kpi_block(
            "Latest Margin",
            f"{margins[-1]:.1%}" if margins else "—",
            chart=margin_spark,
            help={
                "definition": (
                    "Operating margin in the most-recent fiscal "
                    "year. Read alongside the trend line below — a "
                    "high latest margin on a declining slope is "
                    "different from a stable mediocre margin."
                ),
            },
        )
        + ck_kpi_block(
            "COVID Resilience", f"{covid_score}/100",
            sub=html.escape(covid_label),
            help={
                "definition": (
                    "Composite score measuring how the hospital "
                    "weathered the 2020-2022 disruption. Reads "
                    "margin recovery speed, revenue trough depth, "
                    "and post-COVID re-baseline. 80+ = stress-"
                    "tested; <40 = the hospital is structurally "
                    "weaker than its peers."
                ),
            },
        )
        + '</div>'
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

            recovery_cls = "cad-pos" if recovery > 0 else "cad-neg"
            covid_section = ck_panel(
                '<p class="ck-section-body">'
                f'<strong>Resilience Score: {covid_score}/100</strong> — {html.escape(covid_label)}</p>'
                '<p class="ck-section-body">'
                f'Revenue recovery from FY2020 to FY{int(years[-1])}: '
                f'<strong class="{recovery_cls}">{recovery:+.1%}</strong> '
                f'({_fmt_m(rev_20)} → {_fmt_m(rev_latest)}).</p>'
                '<p class="ck-section-body">FY2020 captured the initial COVID shock. '
                f'{"Strong recovery indicates operational resilience and payer diversification." if recovery > 0.05 else "Slow recovery suggests structural challenges beyond COVID."}'
                '</p>',
                title="COVID Impact & Recovery",
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
        cls = "cad-pos" if color == PALETTE["positive"] else ("cad-neg" if color == PALETTE["negative"] else "")
        trend_items += (
            '<div class="hh-trend-row">'
            f'<span>{html.escape(label)}</span>'
            f'<span class="{cls}">{arrow}</span></div>'
        )

    trend_section = ck_panel(
        trend_items, title="Trend Summary",
    ) if trend_items else ""

    # === Peer Comparison ===
    peer_section = ""
    if peer_avg and revs:
        peer_revs = peer_avg.get("revenue", [])
        peer_margins = peer_avg.get("margin", [])
        if peer_revs and peer_margins:
            peer_inner = (
                '<div class="ck-kpi-strip">'
                + ck_kpi_block(
                    f"Revenue Growth — {state_esc}",
                    f"{rev_cagr:+.1%}",
                    sub="this hospital",
                )
                + ck_kpi_block(
                    "State Avg Growth",
                    f"{_cagr(peer_revs[0], peer_revs[-1], len(peer_revs)-1):+.1%}",
                    sub="state median",
                )
                + ck_kpi_block(
                    "Latest Margin — this hospital",
                    f"{margins[-1]:.1%}",
                )
                + ck_kpi_block(
                    "Latest Margin — state avg",
                    f"{peer_margins[-1]:.1%}",
                )
                + '</div>'
            )
            peer_section = ck_panel(
                peer_inner,
                title=f"vs State Average ({state_esc})",
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
            proj_section = ck_panel(
                '<p class="ck-section-body">'
                f'Extrapolated from {n_years}-year trend using linear projection. '
                'Does not account for regulatory or market changes.</p>'
                '<table class="cad-table"><thead><tr>'
                '<th>Year</th><th>Revenue (proj)</th><th>Margin (proj)</th>'
                f'</tr></thead><tbody>{proj_rows}</tbody></table>',
                title=f"Projections (FY{int(years[-1])+1 if years else 2023}-{int(years[-1])+3 if years else 2025})",
            )

    # === Actions ===
    # Standard per-deal context ribbon (consistent with every other
    # per-deal surface) handles generic deal navigation; the panel
    # keeps only the state-market link the ribbon doesn't carry.
    from .models_page import _model_nav
    deal_ribbon = _model_nav(ccn, active="")
    actions = ck_panel(
        '<p class="ck-section-body">'
        f'<a href="/market-data/state/{state_esc}" class="cad-btn">{state_esc} Market</a>'
        '</p>',
        title="Market context",
    )

    hh_styles = f"""
<style>
.hh-trend-row{{display:flex;justify-content:space-between;padding:6px 0;
border-bottom:1px solid {PALETTE['border']};}}
</style>
"""
    next_up = ck_next_section(
        "Back to the hospital profile",
        f"/hospital/{ccn_esc}",
        eyebrow="Continue —",
        italic_word="profile",
    )
    body = (
        f'{deal_ribbon}{hh_styles}{intro}{kpis}{timeline_table}{covid_section}'
        f'{trend_section}{peer_section}{proj_section}{actions}{next_up}'
    )

    return chartis_shell(
        body, f"{name_esc} — History",
        active_nav="/market-data/map",
        subtitle=f"CCN {ccn_esc} | {n_years}-year financial timeline | COVID resilience: {covid_score}/100",
    )
