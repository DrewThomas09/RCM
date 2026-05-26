"""PE Desk Competitive Intelligence — peer rankings & gap analysis.

For any hospital, shows percentile rank on every metric across four
peer groups: national, state, size-matched, and system type. Gaps to
P75 and P90 quantify value creation opportunity on each dimension.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ._chartis_kit import (
    chartis_shell, ck_fmt_num, ck_fmt_pct, ck_kpi_block, ck_next_section,
    ck_page_title, ck_provenance_tooltip,
)
from .data_public.state_profile_page import state_context_panel
_EXPLAINER_CSS = """<style>
.ck-ci-explainer{font-family:var(--sc-serif,'Georgia',serif);
  font-size:15px;line-height:1.55;color:var(--sc-text-dim,#465366);
  margin:0 0 var(--sc-s-6,18px) 0;max-width:72ch;}
.ck-ci-explainer em{color:var(--sc-teal-ink,#155752);font-style:italic;}
</style>"""
from ._glossary_link import metric_label_link
from ._provenance_tooltip import provenance_tooltip
from .brand import PALETTE
from .provenance import build_provenance_graph


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


_CI_CHART_CAPTION_CSS = (
    ".ci-figcap{font-size:11px;color:#6b6456;margin:6px 0 8px;"
    "font-family:'JetBrains Mono',ui-monospace,monospace;"
    "letter-spacing:0.02em;}"
)


def _gap_to_p75_chart(
    gaps: List[Dict[str, Any]], width: int = 700, row_h: int = 26
) -> str:
    """Percentile-progress bars per gap metric against the P75 target.

    Each metric the target trails on is a 0–100 percentile bar with a
    dashed P75 target marker; the unfilled remainder to P75 is the
    quantifiable value-creation opportunity. Sorted by widest gap.
    Reads the same percentile the table shows; empty input returns "".
    """
    rows = [g for g in (gaps or []) if g.get("metric")]
    rows = sorted(rows, key=lambda g: g.get("pctile", 100))[:10]
    if not rows:
        return ""

    pad_l, pad_r, pad_t = 200, 44, 16
    bar_max = width - pad_l - pad_r
    height = pad_t + row_h * len(rows) + 20

    pos = PALETTE["positive"]
    warn = PALETTE["warning"]
    neg = PALETTE["negative"]
    track = PALETTE.get("gridline", "#E8E0D0")
    rule = PALETTE.get("border", "#BFB6A2")
    txt = PALETTE.get("text_secondary", "#4a5568")

    p75_x = pad_l + 0.75 * bar_max

    parts: List[str] = [
        f'<svg viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" role="img" '
        f'aria-label="Current percentile vs P75 target by metric" '
        f'style="width:100%;max-width:{width}px;height:auto;'
        f'print-color-adjust:exact;-webkit-print-color-adjust:exact;">'
    ]
    # P75 target marker.
    parts.append(
        f'<line x1="{p75_x:.1f}" y1="{pad_t - 4}" x2="{p75_x:.1f}" '
        f'y2="{height - 16}" stroke="{pos}" stroke-width="1" '
        f'stroke-dasharray="4 3" opacity="0.6"/>'
        f'<text x="{p75_x:.1f}" y="{height - 4}" text-anchor="middle" '
        f'font-size="9" font-family="JetBrains Mono,ui-monospace,monospace" '
        f'fill="{pos}">P75 TARGET</text>'
    )
    for i, g in enumerate(rows):
        name = _html.escape(str(g["metric"])[:30])
        pct = max(0.0, min(100.0, g.get("pctile", 0)))
        color = neg if pct <= 25 else (warn if pct < 75 else pos)
        y = pad_t + i * row_h
        w = pct / 100.0 * bar_max
        parts.append(
            f'<text x="{pad_l - 8}" y="{y + row_h / 2 + 3:.1f}" '
            f'text-anchor="end" font-size="11" '
            f'font-family="Inter Tight,system-ui,sans-serif" '
            f'fill="{txt}">{name}</text>'
        )
        gap = max(0.0, 75.0 - pct)
        tip = _html.escape(
            f"{g['metric']}: currently P{pct:.0f}"
            + (f" · {gap:.0f} pts below P75 target" if gap > 0
               else " · at or above P75 target")
        )
        # Full track to 100, then the filled current percentile.
        parts.append(
            f'<rect x="{pad_l}" y="{y + 5:.1f}" width="{bar_max:.1f}" '
            f'height="{row_h - 13}" rx="2" fill="{track}"/>'
            f'<rect x="{pad_l}" y="{y + 5:.1f}" width="{max(w, 0.5):.1f}" '
            f'height="{row_h - 13}" rx="2" fill="{color}" opacity="0.85">'
            f'<title>{tip}</title></rect>'
        )
        parts.append(
            f'<text x="{pad_l + w + 6:.1f}" y="{y + row_h / 2 + 3:.1f}" '
            f'text-anchor="start" font-size="10" '
            f'font-family="JetBrains Mono,ui-monospace,monospace" '
            f'fill="{color}">P{pct:.0f}</text>'
        )
    parts.append(
        f'<line x1="{pad_l}" y1="{pad_t - 4}" x2="{pad_l}" '
        f'y2="{height - 16}" stroke="{rule}" stroke-width="1"/>'
    )
    parts.append("</svg>")
    return "".join(parts)


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

    margin_value = ck_provenance_tooltip(
        "Operating margin (national percentile)",
        ck_fmt_pct(margin),
        explainer=(
            f"P{nat_pctile:.0f} nationally - this hospital sits "
            f"above {nat_pctile:.0f}% of the HCRIS universe on "
            f"operating margin. P75+ = top quartile; below P25 "
            f"flags structural margin pressure that the value-"
            f"creation thesis has to fix."
        ),
    )
    kpis = (
        '<div class="ck-kpi-grid" style="grid-template-columns:repeat(5,1fr);">'
        + ck_kpi_block(
            "Net Revenue", _fm(rev), "annual NPR",
            help={
                "definition": (
                    "Net Patient Revenue — gross patient charges less "
                    "contractual allowances, charity care, and bad "
                    "debt. The top-line number every hospital CFO "
                    "reports; HCRIS Worksheet G-3 line 3."
                ),
            },
        )
        + ck_kpi_block(
            f"Margin (P{nat_pctile:.0f})", margin_value, "national rank",
            help={
                "definition": (
                    "Operating margin percentile within the HCRIS "
                    "national universe. P75 = better than 75% of "
                    "peers; P25 means three-quarters of hospitals "
                    "perform better. PE healthcare buyers usually "
                    "target P50+ at entry."
                ),
            },
        )
        + ck_kpi_block("Beds", ck_fmt_num(int(beds)), "licensed")
        + ck_kpi_block("National Universe", ck_fmt_num(len(df)), "HCRIS hospitals")
        + ck_kpi_block(
            "Peer Groups", ck_fmt_num(len(peer_groups)), "comparison sets",
            help={
                "definition": (
                    "Number of peer cohorts this hospital is compared "
                    "against — typically size-banded (similar beds), "
                    "state, region, and teaching status. More groups "
                    "= a more robust percentile read."
                ),
            },
        )
        + '</div>'
    )

    # ── Multi-group percentile table ──
    group_names = list(peer_groups.keys())
    header = '<th>Metric</th><th>Value</th>' + ''.join(
        f'<th style="font-size:11px;">{_html.escape(g)}<br>(n={len(peer_groups[g]):,})</th>'
        for g in group_names
    ) + '<th>Direction</th>'

    metric_rows = ""
    gap_opportunities = []

    # Phase 4C: build a ProvenanceGraph once per render so per-
    # row value cells can render a "where did this number come
    # from?" tooltip. The hospital is a pandas Series; convert
    # to dict so the graph constructor can iterate it. ml_
    # predictions is empty here (this page reads HCRIS-derived
    # values directly from the dataframe).
    prov_graph = build_provenance_graph(
        ccn=str(ccn),
        hcris_profile=dict(hospital),
        ml_predictions={},
    )
    # Track first-call so only the first per-row tooltip
    # injects the <style> block — avoids 11 duplicate styles.
    _first_tooltip = True

    for col, label, fmt, direction in _METRIC_DEFS:
        if col not in df.columns:
            continue
        val = _safe_float(hospital.get(col))
        if val == 0 and col not in ("medicaid_day_pct",):
            continue

        # Phase 4A: wrap label in /metric-glossary anchor when
        # `col` is a registered glossary key (operating_margin,
        # occupancy_rate, medicare_day_pct, medicaid_day_pct
        # are direct matches today; the helper falls through to
        # plain text for the other 8 columns).
        cells = f'<td style="font-weight:500;">{metric_label_link(label, col)}</td>'
        # Phase 4C: wrap the value cell in provenance_tooltip.
        # 11 of 12 _METRIC_DEFS cols resolve to glossary entries
        # post-loop-114; the 12th (beds) falls through to plain
        # text via the helper's "unknown key" path.
        _tip = provenance_tooltip(
            label=label, value=_fmt_val(val, fmt),
            graph=prov_graph, metric_key=col,
            inject_css=_first_tooltip,
        )
        _first_tooltip = False
        cells += f'<td class="num" style="font-weight:600;">{_tip}</td>'

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
                    "col": col,
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
            f'<td style="font-weight:500;">{metric_label_link(g["metric"], g.get("col", ""))}</td>'
            f'<td class="num">{_fmt_val(g["current"], g["fmt"])}</td>'
            f'<td class="num" style="color:var(--cad-pos);">{_fmt_val(g["p75"], g["fmt"])}</td>'
            f'<td class="num" style="color:var(--cad-pos);font-weight:600;">{improvement}</td>'
            f'<td class="num" style="color:{pct_color};">P{g["pctile"]:.0f}</td>'
            f'<td class="num">{impact_str}</td>'
            f'</tr>'
        )

    gap_section = ""
    if gap_rows:
        _gap_chart = _gap_to_p75_chart(gap_opportunities)
        _gap_fig = (
            f'<style>{_CI_CHART_CAPTION_CSS}</style>'
            f'<div class="ci-figcap">Current percentile vs P75 target '
            f'&middot; unfilled gap to the dashed line = value-creation '
            f'opportunity</div>'
            f'{_gap_chart}'
        ) if _gap_chart else ""
        gap_section = (
            f'<div class="cad-card" style="border-left:3px solid var(--cad-pos);">'
            f'<h2>Value Creation Gaps — Path to P75</h2>'
            f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:10px;">'
            f'Metrics where the target trails size-matched P75 peers. Each gap represents '
            f'quantifiable value creation opportunity. Estimated EBITDA impact assumes '
            f'linear improvement proportional to revenue.</p>'
            f'{_gap_fig}'
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
    # Consistent per-deal context ribbon (same one the model pages
    # use) replaces the bespoke cad-btn bar — every sibling analysis is
    # one click away, in the editorial pill styling.
    from .models_page import _model_nav
    deal_ribbon = _model_nav(ccn, active="comp_intel")

    next_up = ck_next_section(
        "Take this peer view back into the deal profile",
        f"/deal/{_html.escape(ccn)}",
        eyebrow="Continue —",
        italic_word="profile",
    )
    page_title = ck_page_title(
        "Competitive Intelligence",
        eyebrow=f"COMPETITIVE INTELLIGENCE · {_html.escape(ccn)}",
        meta=(
            f"{_html.escape(name)} · {_html.escape(state)} · {beds:.0f} beds · "
            f"nat'l margin P{nat_pctile:.0f} · {len(gap_opportunities)} gaps to P75"
        ),
    )
    ci_explainer = (
        '<p class="ck-ci-explainer">'
        f"<em>{_html.escape(name)}.</em> "
        "Per-metric percentile ranks against state and national benchmarks, "
        "with named gap opportunities that would lift this hospital to P75 "
        "of its cohort. Read the gap rows as the value-creation thesis the "
        "deal needs to support."
        "</p>"
    )
    geo_ctx = state_context_panel(state)
    body = deal_ribbon + page_title + ci_explainer + f'{kpis}{percentile_section}{gap_section}{peer_section}{geo_ctx}{next_up}'

    return chartis_shell(
        body,
        f"Competitive Intelligence — {_html.escape(name)}",
        extra_css=_EXPLAINER_CSS,
    )
