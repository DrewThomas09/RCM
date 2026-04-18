"""Sector Correlation Matrix page — /sector-correlation.

Heatmap of pairwise Pearson correlations between sector MOIC time series.
Identifies natural diversifiers and correlated bets for portfolio construction.
"""
from __future__ import annotations

import html as _html
import math
from typing import Any, Dict, List, Optional, Tuple

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_section_header, ck_kpi_block,
)


def _r_color(r: float) -> str:
    """Diverging color: red for high positive, blue for high negative, gray for ~0."""
    if r >= 0.7:
        return "#dc2626"
    if r >= 0.4:
        return "#f59e0b"
    if r >= 0.1:
        return "#94a3b8"
    if r >= -0.1:
        return "#64748b"
    if r >= -0.4:
        return "#60a5fa"
    return "#3b82f6"


def _r_bg(r: float) -> str:
    """Cell background for heatmap."""
    if r >= 0.7:
        return "rgba(220,38,38,.5)"
    if r >= 0.5:
        return "rgba(245,158,11,.35)"
    if r >= 0.3:
        return "rgba(245,158,11,.15)"
    if r >= 0.1:
        return "rgba(148,163,184,.08)"
    if r >= -0.1:
        return "rgba(100,116,139,.05)"
    if r >= -0.3:
        return "rgba(96,165,250,.15)"
    if r >= -0.5:
        return "rgba(59,130,246,.30)"
    return "rgba(59,130,246,.50)"


def _heatmap_table(
    sectors: List[str],
    matrix: Dict[Tuple[str, str], float],
    max_sectors: int = 18,
) -> str:
    """Dense HTML table heatmap — truncate to max_sectors for readability."""
    secs = sectors[:max_sectors]
    short = [s[:16] for s in secs]

    header = "<tr><th></th>" + "".join(
        f'<th style="writing-mode:vertical-rl;transform:rotate(180deg);'
        f'font-size:9px;padding:2px 4px;color:{P["text_dim"]};'
        f'font-family:Inter,sans-serif;white-space:nowrap;max-height:90px">'
        f'{_html.escape(s)}</th>'
        for s in short
    ) + "</tr>"

    rows = []
    for i, row_sec in enumerate(secs):
        cells = [
            f'<td style="font-size:9px;color:{P["text_dim"]};padding:2px 6px;'
            f'white-space:nowrap;font-family:Inter,sans-serif">'
            f'{_html.escape(short[i])}</td>'
        ]
        for j, col_sec in enumerate(secs):
            if i == j:
                cells.append(
                    f'<td style="background:#1e293b;text-align:center;'
                    f'font-size:9px;padding:2px 4px;color:{P["text_faint"]}" title="{_html.escape(row_sec)}">—</td>'
                )
            else:
                r = matrix.get((row_sec, col_sec))
                if r is None:
                    cells.append(
                        f'<td style="background:{P["bg_secondary"] if P.get("bg_secondary") else "#0b0f16"};'
                        f'text-align:center;font-size:9px;padding:2px 4px;color:{P["text_faint"]}">·</td>'
                    )
                else:
                    bg = _r_bg(r)
                    color = _r_color(r)
                    title = f"{row_sec} vs {col_sec}: r={r:.3f}"
                    cells.append(
                        f'<td style="background:{bg};text-align:center;'
                        f'font-size:9px;padding:2px 4px;font-family:JetBrains Mono,monospace;'
                        f'font-variant-numeric:tabular-nums;color:{color}" title="{_html.escape(title)}">'
                        f'{r:+.2f}</td>'
                    )
        rows.append("<tr>" + "".join(cells) + "</tr>")

    return (
        '<table style="border-collapse:collapse;font-size:9px">'
        "<thead>" + header + "</thead>"
        "<tbody>" + "".join(rows) + "</tbody>"
        "</table>"
    )


def _pairs_table(pairs: List[Any], label: str, positive: bool) -> str:
    rows = []
    for p in pairs:
        r = p.correlation
        color = _r_color(r)
        rows.append(
            f"<tr>"
            f"<td>{_html.escape(p.sector_a[:28])}</td>"
            f"<td>{_html.escape(p.sector_b[:28])}</td>"
            f"<td class='r mn' style='color:{color}'>{r:+.3f}</td>"
            f"<td class='r mn'>{p.n_overlap_years}</td>"
            f"</tr>"
        )
    return (
        f'<p class="ck-sub-header">{_html.escape(label)}</p>'
        '<table class="ck-table">'
        "<thead><tr>"
        "<th>Sector A</th><th>Sector B</th>"
        "<th class='r'>Pearson r</th><th class='r'>Overlap Years</th>"
        "</tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody>"
        "</table>"
    )


def _time_series_svg(
    ts_list: List[Any],
    all_years: List[int],
    width: int = 640,
    height: int = 180,
    max_series: int = 8,
) -> str:
    """Multi-line chart of avg MOIC per year per sector."""
    if not ts_list or not all_years:
        return ""
    ml, mr, mt, mb = 40, 20, 10, 28
    W = width - ml - mr
    H = height - mt - mb

    ts_show = sorted(ts_list, key=lambda t: -(t.n_deals))[:max_series]
    all_moics = [m for ts in ts_show for m in ts.avg_moics]
    if not all_moics:
        return ""
    min_v = max(0.0, min(all_moics) - 0.5)
    max_v = max(all_moics) + 0.5

    def px(yr: int) -> int:
        if len(all_years) <= 1:
            return ml + W // 2
        return int(ml + (yr - all_years[0]) / (all_years[-1] - all_years[0]) * W)

    def py(v: float) -> int:
        return int(mt + H - (v - min_v) / (max_v - min_v) * H)

    SERIES_COLORS = [
        "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
        "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16",
    ]

    lines = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block">'
    ]

    # Grid
    for gv in [1.0, 2.0, 3.0, 4.0]:
        if min_v <= gv <= max_v:
            y = py(gv)
            lines.append(
                f'<line x1="{ml}" y1="{y}" x2="{ml+W}" y2="{y}" '
                f'stroke="{P["border"]}" stroke-width="1"/>'
            )
            lines.append(
                f'<text x="{ml-4}" y="{y+4}" text-anchor="end" font-size="9" '
                f'fill="{P["text_faint"]}" font-family="JetBrains Mono,monospace">'
                f'{gv:.0f}×</text>'
            )

    # Year labels
    for yr in all_years[::2]:
        x = px(yr)
        lines.append(
            f'<text x="{x}" y="{mt+H+16}" text-anchor="middle" font-size="9" '
            f'fill="{P["text_faint"]}" font-family="Inter,sans-serif">{yr}</text>'
        )

    # Series
    for idx, ts in enumerate(ts_show):
        color = SERIES_COLORS[idx % len(SERIES_COLORS)]
        pts = [(px(yr), py(m)) for yr, m in zip(ts.years, ts.avg_moics)]
        if len(pts) >= 2:
            path = "M " + " L ".join(f"{x},{y}" for x, y in pts)
            lines.append(
                f'<path d="{path}" fill="none" stroke="{color}" '
                f'stroke-width="1.5" opacity="0.85"/>'
            )
        for x, y in pts:
            lines.append(f'<circle cx="{x}" cy="{y}" r="2.5" fill="{color}"/>')
        # Label at last point
        if pts:
            lx, ly = pts[-1]
            lines.append(
                f'<text x="{lx+5}" y="{ly+4}" font-size="8" fill="{color}" '
                f'font-family="Inter,sans-serif">{_html.escape(ts.sector[:12])}</text>'
            )

    lines.append("</svg>")
    return "\n".join(lines)


def render_sector_correlation(params: Dict[str, str]) -> str:
    from rcm_mc.data_public.sector_correlation import compute_sector_correlation

    try:
        min_deals = max(3, int(params.get("min_deals", "5")))
    except (TypeError, ValueError):
        min_deals = 5

    result = compute_sector_correlation(min_sector_deals=min_deals)

    n_pairs = len(result.matrix) // 2
    avg_r = (
        round(sum(result.matrix.values()) / len(result.matrix), 3)
        if result.matrix
        else 0.0
    )

    # Count high-correlation pairs
    n_high_r = sum(1 for r in result.matrix.values() if r >= 0.6)

    kpi_grid = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block(
            "Sectors in Matrix",
            f'<span class="mn">{len(result.sectors)}</span>',
            f"min {min_deals} deals each",
        )
        + ck_kpi_block(
            "Correlated Pairs (r≥0.6)",
            f'<span class="mn" style="color:{P["warning"]}">{n_high_r // 2}</span>',
            "MOIC moves together",
        )
        + ck_kpi_block(
            "Avg Pairwise r",
            f'<span class="mn">{avg_r:+.3f}</span>',
            "across all sector pairs",
        )
        + ck_kpi_block(
            "Best Diversifier Pair",
            f'<span class="mn pos">{result.top_pairs_negative[0].correlation:+.3f}</span>' if result.top_pairs_negative else "—",
            (
                f'{result.top_pairs_negative[0].sector_a[:20]} × {result.top_pairs_negative[0].sector_b[:20]}'
                if result.top_pairs_negative else ""
            ),
        )
        + "</div>"
    )

    heatmap = _heatmap_table(result.sectors, result.matrix)
    ts_chart = _time_series_svg(
        [t for t in result.time_series if t.n_deals >= 5],
        result.all_years,
    )
    pos_pairs = _pairs_table(result.top_pairs_positive, "Highest Correlation — Same-Direction Risk", True)
    neg_pairs = _pairs_table(result.top_pairs_negative, "Lowest Correlation — Best Diversifiers", False)

    min_opts = "".join(
        f'<option value="{v}" {"selected" if str(v) == str(min_deals) else ""}>{v}+ deals</option>'
        for v in [3, 5, 8, 10, 15]
    )
    filter_bar = f"""
<form method="get" action="/sector-correlation" class="ck-filters">
  <span class="ck-filter-label">Min Sector Deals</span>
  <select name="min_deals" class="ck-sel" onchange="this.form.submit()">{min_opts}</select>
</form>"""

    body = f"""
{filter_bar}
{kpi_grid}
{ck_section_header("MOIC Time Series by Sector", "Average realized MOIC per vintage year")}
<div style="overflow-x:auto;margin-bottom:24px">{ts_chart}</div>
{ck_section_header("Sector Correlation Matrix", "Pearson r of avg MOIC across shared vintage years")}
<p style="font-size:11px;color:{P["text_faint"]};margin-bottom:8px">
  Red = highly correlated (concentrated exposure), Blue = anti-correlated (diversifying), Dot = insufficient overlap.
  Hover cells for detail.
</p>
<div style="overflow-x:auto;margin-bottom:24px">{heatmap}</div>
<div style="display:flex;gap:32px;flex-wrap:wrap;margin-bottom:24px">
  <div style="flex:1;min-width:280px">{pos_pairs}</div>
  <div style="flex:1;min-width:280px">{neg_pairs}</div>
</div>
<p style="font-size:11px;color:{P["text_faint"]}">
  Correlation computed on vintage-year average MOIC bins. Requires ≥3 overlapping
  years between sectors. Small sample sizes reduce reliability.
</p>
"""

    return chartis_shell(
        body=body,
        title="Sector Correlation Matrix",
        active_nav="/sector-correlation",
        subtitle="Pairwise MOIC correlations across healthcare sectors — portfolio diversification lens",
    )
