"""SeekingChartis Competitive Intelligence — peer rankings & gap analysis.

For any hospital, shows percentile rank on every metric across four
peer groups: national, state, size-matched, and system type. Gaps to
P75 and P90 quantify value creation opportunity on each dimension.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ._chartis_kit import chartis_shell
from .brand import PALETTE


def _safe_float(val, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        f = float(val)
        return default if f != f else f
    except (TypeError, ValueError):
        return default


def _fm(val: float) -> str:
    if abs(val) >= 1e9:
        return f"${val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val/1e6:.1f}M"
    if abs(val) >= 1e3:
        return f"${val/1e3:.0f}K"
    return f"${val:,.0f}"


_METRIC_DEFS = [
    ("net_patient_revenue", "Net Patient Revenue", "dollars", "higher"),
    ("operating_margin", "Operating Margin", "pct", "higher"),
    ("beds", "Bed Count", "count", "neutral"),
    ("revenue_per_bed", "Revenue per Bed", "dollars", "higher"),
    ("occupancy_rate", "Occupancy Rate", "pct", "higher"),
    ("net_to_gross_ratio", "Net-to-Gross Ratio", "pct", "higher"),
    ("expense_per_bed", "Expense per Bed", "dollars", "lower"),
    ("medicare_day_pct", "Medicare Day %", "pct", "neutral"),
    ("medicaid_day_pct", "Medicaid Day %", "pct", "neutral"),
    ("commercial_pct", "Commercial Payer %", "pct", "higher"),
    ("payer_diversity", "Payer Diversity Index", "index", "higher"),
    ("total_patient_days", "Total Patient Days", "count", "higher"),
]


def _fmt_val(val: float, fmt: str) -> str:
    if fmt == "dollars":
        return _fm(val)
    if fmt == "pct":
        return f"{val:.1%}" if abs(val) < 2 else f"{val:.1f}%"
    if fmt == "count":
        return f"{val:,.0f}"
    return f"{val:.3f}"


def _pctile_color(pctile: float, direction: str) -> str:
    if direction == "higher":
        if pctile >= 75:
            return "var(--cad-pos)"
        if pctile <= 25:
            return "var(--cad-neg)"
    elif direction == "lower":
        if pctile <= 25:
            return "var(--cad-pos)"
        if pctile >= 75:
            return "var(--cad-neg)"
    return "var(--cad-text2)"


def _pctile_bar(pctile: float, direction: str) -> str:
    color = _pctile_color(pctile, direction)
    return (
        f'<div style="display:flex;align-items:center;gap:4px;">'
        f'<div style="width:60px;background:var(--cad-bg3);border-radius:2px;height:8px;">'
        f'<div style="width:{pctile:.0f}%;background:{color};border-radius:2px;height:8px;"></div>'
        f'</div>'
        f'<span class="cad-mono" style="font-size:10px;color:{color};">P{pctile:.0f}</span>'
        f'</div>'
    )


def _add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "revenue_per_bed" not in df.columns and "net_patient_revenue" in df.columns and "beds" in df.columns:
        df["revenue_per_bed"] = df["net_patient_revenue"] / df["beds"].replace(0, np.nan)
    if "operating_margin" not in df.columns and "net_patient_revenue" in df.columns and "operating_expenses" in df.columns:
        safe_rev = df["net_patient_revenue"].where(df["net_patient_revenue"] > 1e5)
        df["operating_margin"] = ((safe_rev - df["operating_expenses"]) / safe_rev).clip(-0.5, 1.0)
    if "occupancy_rate" not in df.columns and "total_patient_days" in df.columns and "bed_days_available" in df.columns:
        df["occupancy_rate"] = df["total_patient_days"] / df["bed_days_available"].replace(0, np.nan)
    if "commercial_pct" not in df.columns:
        mc = df.get("medicare_day_pct", pd.Series(0, index=df.index)).fillna(0)
        md = df.get("medicaid_day_pct", pd.Series(0, index=df.index)).fillna(0)
        df["commercial_pct"] = (1.0 - mc - md).clip(0, 1)
    if "net_to_gross_ratio" not in df.columns and "gross_patient_revenue" in df.columns:
        df["net_to_gross_ratio"] = (
            df["net_patient_revenue"] / df["gross_patient_revenue"].replace(0, np.nan)
        ).clip(0, 1)
    if "expense_per_bed" not in df.columns and "operating_expenses" in df.columns and "beds" in df.columns:
        df["expense_per_bed"] = df["operating_expenses"] / df["beds"].replace(0, np.nan)
    if "payer_diversity" not in df.columns:
        mc = df.get("medicare_day_pct", pd.Series(0, index=df.index)).fillna(0)
        md = df.get("medicaid_day_pct", pd.Series(0, index=df.index)).fillna(0)
        cm = df.get("commercial_pct", pd.Series(0, index=df.index)).fillna(0)
        df["payer_diversity"] = 1 - (mc**2 + md**2 + cm**2)
    return df


def _compute_peer_stats(
    hospital_val: float,
    peer_series: pd.Series,
    fmt: str,
    direction: str,
) -> Dict[str, Any]:
    vals = peer_series.dropna()
    if len(vals) < 5:
        return {"n": len(vals), "pctile": 50, "p25": 0, "median": 0, "p75": 0, "p90": 0, "gap_to_p75": 0, "gap_to_p90": 0}
    pctile = float((vals < hospital_val).mean() * 100)
    p25 = float(vals.quantile(0.25))
    median = float(vals.median())
    p75 = float(vals.quantile(0.75))
    p90 = float(vals.quantile(0.90))

    if direction == "higher":
        gap_75 = max(0, p75 - hospital_val)
        gap_90 = max(0, p90 - hospital_val)
    elif direction == "lower":
        gap_75 = max(0, hospital_val - p25)
        gap_90 = max(0, hospital_val - float(vals.quantile(0.10)))
    else:
        gap_75 = 0
        gap_90 = 0

    return {
        "n": len(vals), "pctile": round(pctile, 1),
        "p25": p25, "median": median, "p75": p75, "p90": p90,
        "gap_to_p75": gap_75, "gap_to_p90": gap_90,
    }


def render_competitive_intel(ccn: str, hcris_df: pd.DataFrame) -> str:
    """Render competitive intelligence page for a hospital."""
    df = _add_features(hcris_df)
    match = df[df["ccn"] == ccn]
    if match.empty:
        return chartis_shell(
            f'<div class="cad-card"><p>Hospital {_html.escape(ccn)} not found.</p></div>',
            "Competitive Intelligence",
        )

    hospital = match.iloc[0]
    name = str(hospital.get("name", f"Hospital {ccn}"))
    state = str(hospital.get("state", ""))
    beds = _safe_float(hospital.get("beds"))

    # Define peer groups
    size_lo = max(10, beds * 0.5)
    size_hi = beds * 2.0
    peer_groups = {
        "National": df[df["ccn"] != ccn],
        f"{state} State": df[(df["state"] == state) & (df["ccn"] != ccn)] if state else pd.DataFrame(),
        "Size-Matched": df[(df["beds"] >= size_lo) & (df["beds"] <= size_hi) & (df["ccn"] != ccn)],
    }
    # Add state + size group
    st_size = df[(df["state"] == state) & (df["beds"] >= size_lo) & (df["beds"] <= size_hi) & (df["ccn"] != ccn)]
    if len(st_size) >= 5:
        peer_groups[f"{state} Size-Matched"] = st_size

    # ── KPIs ──
    margin = _safe_float(hospital.get("operating_margin"))
    rev = _safe_float(hospital.get("net_patient_revenue"))
    nat_margins = df["operating_margin"].dropna()
    nat_pctile = float((nat_margins < margin).mean() * 100) if len(nat_margins) > 10 else 50

    kpis = (
        f'<div class="cad-kpi-grid" style="grid-template-columns:repeat(5,1fr);">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fm(rev)}</div>'
        f'<div class="cad-kpi-label">Net Revenue</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{margin:.1%}</div>'
        f'<div class="cad-kpi-label">Margin (P{nat_pctile:.0f})</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{beds:.0f}</div>'
        f'<div class="cad-kpi-label">Beds</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(df):,}</div>'
        f'<div class="cad-kpi-label">National Universe</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(peer_groups)}</div>'
        f'<div class="cad-kpi-label">Peer Groups</div></div>'
        f'</div>'
    )

    # ── Multi-group percentile table ──
    group_names = list(peer_groups.keys())
    header = '<th>Metric</th><th>Value</th>' + ''.join(
        f'<th style="font-size:11px;">{_html.escape(g)}<br>(n={len(peer_groups[g]):,})</th>'
        for g in group_names
    ) + '<th>Direction</th>'

    metric_rows = ""
    gap_opportunities = []

    for col, label, fmt, direction in _METRIC_DEFS:
        if col not in df.columns:
            continue
        val = _safe_float(hospital.get(col))
        if val == 0 and col not in ("medicaid_day_pct",):
            continue

        cells = f'<td style="font-weight:500;">{_html.escape(label)}</td>'
        cells += f'<td class="num" style="font-weight:600;">{_fmt_val(val, fmt)}</td>'

        for gname in group_names:
            gdf = peer_groups[gname]
            if gdf.empty or col not in gdf.columns:
                cells += '<td style="color:var(--cad-text3);">—</td>'
                continue
            stats = _compute_peer_stats(val, gdf[col], fmt, direction)
            cells += f'<td>{_pctile_bar(stats["pctile"], direction)}</td>'

            # Track gap opportunities for size-matched peers
            if "Size" in gname and stats["gap_to_p75"] > 0 and direction != "neutral":
                gap_opportunities.append({
                    "metric": label,
                    "current": val,
                    "p75": stats["p75"],
                    "gap": stats["gap_to_p75"],
                    "fmt": fmt,
                    "direction": direction,
                    "pctile": stats["pctile"],
                })

        dir_icon = {"higher": "&#9650;", "lower": "&#9660;", "neutral": "&#9654;"}.get(direction, "")
        dir_color = {"higher": "var(--cad-pos)", "lower": "var(--cad-neg)", "neutral": "var(--cad-text3)"}.get(direction, "")
        cells += f'<td style="color:{dir_color};font-size:11px;">{dir_icon} {direction}</td>'

        metric_rows += f'<tr>{cells}</tr>'

    percentile_section = (
        f'<div class="cad-card">'
        f'<h2>Percentile Rankings — All Metrics</h2>'
        f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:10px;">'
        f'Percentile rank across {len(group_names)} peer groups. Bar shows position: '
        f'left = bottom of peers, right = top. Green = favorable direction, red = unfavorable. '
        f'Direction: &#9650; higher is better, &#9660; lower is better, &#9654; neutral.'
        f'<br><span style="font-size:10.5px;color:var(--cad-text3);">'
        f'Data: CMS HCRIS FY2022 | {len(df):,} hospitals with complete financials</span></p>'
        f'<div style="overflow-x:auto;">'
        f'<table class="cad-table"><thead><tr>{header}'
        f'</tr></thead><tbody>{metric_rows}</tbody></table></div></div>'
    )

    # ── Gap-to-Best-in-Class ──
    gap_opportunities.sort(key=lambda g: -g["gap"])
    gap_rows = ""
    for g in gap_opportunities[:10]:
        if g["direction"] == "higher":
            gap_val = g["gap"]
            improvement = f"+{_fmt_val(gap_val, g['fmt'])}"
        else:
            gap_val = g["gap"]
            improvement = f"-{_fmt_val(gap_val, g['fmt'])}"

        # Estimate EBITDA impact
        if g["fmt"] == "pct" and rev > 0:
            ebitda_est = abs(gap_val) * rev
            impact_str = f'~{_fm(ebitda_est)}'
        elif g["fmt"] == "dollars" and beds > 0:
            ebitda_est = abs(gap_val) * beds * 0.1
            impact_str = f'~{_fm(ebitda_est)}'
        else:
            impact_str = "—"

        pct_color = _pctile_color(g["pctile"], g["direction"])
        gap_rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{_html.escape(g["metric"])}</td>'
            f'<td class="num">{_fmt_val(g["current"], g["fmt"])}</td>'
            f'<td class="num" style="color:var(--cad-pos);">{_fmt_val(g["p75"], g["fmt"])}</td>'
            f'<td class="num" style="color:var(--cad-pos);font-weight:600;">{improvement}</td>'
            f'<td class="num" style="color:{pct_color};">P{g["pctile"]:.0f}</td>'
            f'<td class="num">{impact_str}</td>'
            f'</tr>'
        )

    gap_section = ""
    if gap_rows:
        gap_section = (
            f'<div class="cad-card" style="border-left:3px solid var(--cad-pos);">'
            f'<h2>Value Creation Gaps — Path to P75</h2>'
            f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:10px;">'
            f'Metrics where the target trails size-matched P75 peers. Each gap represents '
            f'quantifiable value creation opportunity. Estimated EBITDA impact assumes '
            f'linear improvement proportional to revenue.</p>'
            f'<table class="cad-table"><thead><tr>'
            f'<th>Metric</th><th>Current</th><th>P75 Target</th><th>Gap</th>'
            f'<th>Percentile</th><th>Est. Impact</th>'
            f'</tr></thead><tbody>{gap_rows}</tbody></table></div>'
        )

    # ── Top peers table ──
    size_peers = peer_groups.get("Size-Matched", peer_groups.get("National", pd.DataFrame()))
    if not size_peers.empty and "operating_margin" in size_peers.columns:
        top_peers = size_peers.nlargest(10, "net_patient_revenue")
    else:
        top_peers = pd.DataFrame()

    peer_rows = ""
    for _, row in top_peers.iterrows():
        p_name = _html.escape(str(row.get("name", ""))[:30])
        p_ccn = str(row.get("ccn", ""))
        p_st = str(row.get("state", ""))
        p_beds = _safe_float(row.get("beds"))
        p_rev = _safe_float(row.get("net_patient_revenue"))
        p_margin = _safe_float(row.get("operating_margin"))
        p_mc = _safe_float(row.get("medicare_day_pct"))
        m_color = "var(--cad-pos)" if p_margin > 0.05 else ("var(--cad-warn)" if p_margin > 0 else "var(--cad-neg)")
        peer_rows += (
            f'<tr>'
            f'<td><a href="/hospital/{_html.escape(p_ccn)}" '
            f'style="color:var(--cad-link);text-decoration:none;">{p_name}</a></td>'
            f'<td>{_html.escape(p_st)}</td>'
            f'<td class="num">{p_beds:.0f}</td>'
            f'<td class="num">{_fm(p_rev)}</td>'
            f'<td class="num" style="color:{m_color};">{p_margin:.1%}</td>'
            f'<td class="num">{p_mc:.0%}</td>'
            f'</tr>'
        )

    peer_section = (
        f'<div class="cad-card">'
        f'<h2>Top Size-Matched Peers</h2>'
        f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:10px;">'
        f'{size_lo:.0f}–{size_hi:.0f} beds, ranked by revenue. Click any peer for full profile.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Hospital</th><th>State</th><th>Beds</th><th>Revenue</th>'
        f'<th>Margin</th><th>Medicare</th>'
        f'</tr></thead>'
        f'<tbody>'
        f'<tr style="background:var(--cad-bg3);font-weight:600;">'
        f'<td>{_html.escape(name[:30])} (Target)</td>'
        f'<td>{_html.escape(state)}</td>'
        f'<td class="num">{beds:.0f}</td>'
        f'<td class="num">{_fm(rev)}</td>'
        f'<td class="num">{margin:.1%}</td>'
        f'<td class="num">{_safe_float(hospital.get("medicare_day_pct")):.0%}</td>'
        f'</tr>{peer_rows}</tbody></table></div>'
    ) if peer_rows else ""

    # ── Nav ──
    nav = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/hospital/{_html.escape(ccn)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Hospital Profile</a>'
        f'<a href="/ebitda-bridge/{_html.escape(ccn)}" class="cad-btn" '
        f'style="text-decoration:none;">EBITDA Bridge</a>'
        f'<a href="/ic-memo/{_html.escape(ccn)}" class="cad-btn" '
        f'style="text-decoration:none;">IC Memo</a>'
        f'<a href="/ml-insights/hospital/{_html.escape(ccn)}" class="cad-btn" '
        f'style="text-decoration:none;">ML Analysis</a>'
        f'<a href="/scenarios/{_html.escape(ccn)}" class="cad-btn" '
        f'style="text-decoration:none;">Scenarios</a>'
        f'<a href="/predictive-screener" class="cad-btn" '
        f'style="text-decoration:none;">Deal Screener</a>'
        f'</div>'
    )

    body = f'{kpis}{percentile_section}{gap_section}{peer_section}{nav}'

    return chartis_shell(
        body,
        f"Competitive Intelligence — {_html.escape(name)}",
        subtitle=(
            f"CCN {_html.escape(ccn)} | {_html.escape(state)} | {beds:.0f} beds | "
            f"Nat'l margin P{nat_pctile:.0f} | {len(gap_opportunities)} gaps to P75"
        ),
    )
