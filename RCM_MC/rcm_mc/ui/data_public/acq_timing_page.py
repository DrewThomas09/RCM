"""Acquisition Timing Analyzer page — /acq-timing.

Entry multiple vs. MOIC cycle analysis: shows how buying at different
points in the valuation cycle affects realized returns.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_section_header, ck_kpi_block, ck_fmt_moic,
)

CYCLE_COLORS = {
    "Peak":       "#b5321e",
    "ZIRP Peak":  "#8a1e0e",
    "Trough":     "#0a8a5f",
    "Recovery":   "#2fb3ad",
    "Mid-Cycle":  "#465366",
    "Expansion":  "#b8732a",
    "Late Cycle": "#f97316",
    "Neutral":    "#7a8699",
}


def _cycle_badge(label: str) -> str:
    color = CYCLE_COLORS.get(label, P["text_faint"])
    return (
        f'<span style="display:inline-block;background:{color};color:#000;'
        f'font-size:9px;padding:1px 5px;border-radius:2px;font-weight:700;'
        f'letter-spacing:.06em">{_html.escape(label)}</span>'
    )


def _dual_axis_svg(
    year_stats: List[Any],
    width: int = 680,
    height: int = 200,
) -> str:
    """Line chart: EV/EBITDA P50 (primary) + MOIC P50 (secondary) by year."""
    if not year_stats:
        return ""
    ml, mr, mt, mb = 45, 45, 12, 28
    W = width - ml - mr
    H = height - mt - mb

    years = [s.year for s in year_stats]
    if len(years) < 2:
        return ""

    ee_vals = [s.ee_p50 for s in year_stats if s.ee_p50 is not None]
    moic_vals = [s.moic_p50 for s in year_stats if s.moic_p50 is not None]

    if not ee_vals or not moic_vals:
        return ""

    min_ee = max(0, min(ee_vals) - 1)
    max_ee = max(ee_vals) + 1
    min_m = max(0, min(moic_vals) - 0.5)
    max_m = max(moic_vals) + 0.5

    min_yr = years[0]
    max_yr = years[-1]

    def px(yr: int) -> int:
        if max_yr == min_yr:
            return ml + W // 2
        return int(ml + (yr - min_yr) / (max_yr - min_yr) * W)

    def py_ee(v: float) -> int:
        return int(mt + H - (v - min_ee) / (max_ee - min_ee + 0.001) * H)

    def py_m(v: float) -> int:
        return int(mt + H - (v - min_m) / (max_m - min_m + 0.001) * H)

    lines = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block">'
    ]

    # Shade cycle peaks
    for s in year_stats:
        if "Peak" in s.cycle_label:
            x = px(s.year)
            lines.append(
                f'<rect x="{x-8}" y="{mt}" width="16" height="{H}" '
                f'fill="{CYCLE_COLORS.get(s.cycle_label, P["negative"])}" opacity="0.08"/>'
            )

    # Grid lines
    for gv in [8, 10, 12, 14, 16]:
        if min_ee <= gv <= max_ee:
            y = py_ee(gv)
            lines.append(
                f'<line x1="{ml}" y1="{y}" x2="{ml+W}" y2="{y}" '
                f'stroke="{P["border"]}" stroke-width="1" stroke-dasharray="3,3"/>'
            )
            lines.append(
                f'<text x="{ml-4}" y="{y+4}" text-anchor="end" font-size="9" '
                f'fill="{P["text_faint"]}" font-family="JetBrains Mono,monospace">'
                f'{gv}×</text>'
            )

    # MOIC right axis
    for gv in [1.5, 2.0, 2.5, 3.0, 3.5]:
        if min_m <= gv <= max_m:
            y = py_m(gv)
            lines.append(
                f'<text x="{ml+W+4}" y="{y+4}" font-size="9" '
                f'fill="{P["positive"]}" font-family="JetBrains Mono,monospace">'
                f'{gv:.1f}×</text>'
            )

    # Year x-axis labels
    for s in year_stats:
        x = px(s.year)
        lines.append(
            f'<text x="{x}" y="{mt+H+16}" text-anchor="middle" font-size="9" '
            f'fill="{CYCLE_COLORS.get(s.cycle_label, P["text_faint"])}" '
            f'font-family="JetBrains Mono,monospace">{s.year}</text>'
        )

    # EV/EBITDA band (P25–P75)
    band_pts_top = []
    band_pts_bot = []
    for s in year_stats:
        if s.ee_p25 is not None and s.ee_p75 is not None:
            x = px(s.year)
            band_pts_top.append((x, py_ee(s.ee_p75)))
            band_pts_bot.append((x, py_ee(s.ee_p25)))
    if band_pts_top:
        poly = (
            " ".join(f"{x},{y}" for x, y in band_pts_top)
            + " "
            + " ".join(f"{x},{y}" for x, y in reversed(band_pts_bot))
        )
        lines.append(
            f'<polygon points="{poly}" fill="{P["accent"]}" opacity="0.12"/>'
        )

    # EV/EBITDA P50 line
    ee_pts = [(px(s.year), py_ee(s.ee_p50)) for s in year_stats if s.ee_p50 is not None]
    if len(ee_pts) >= 2:
        path = "M " + " L ".join(f"{x},{y}" for x, y in ee_pts)
        lines.append(
            f'<path d="{path}" fill="none" stroke="{P["accent"]}" stroke-width="2"/>'
        )
    for x, y in ee_pts:
        lines.append(f'<circle cx="{x}" cy="{y}" r="3" fill="{P["accent"]}"/>')

    # MOIC P50 line
    m_pts = [(px(s.year), py_m(s.moic_p50)) for s in year_stats if s.moic_p50 is not None]
    if len(m_pts) >= 2:
        path = "M " + " L ".join(f"{x},{y}" for x, y in m_pts)
        lines.append(
            f'<path d="{path}" fill="none" stroke="{P["positive"]}" stroke-width="2" stroke-dasharray="5,3"/>'
        )
    for x, y in m_pts:
        lines.append(f'<circle cx="{x}" cy="{y}" r="3" fill="{P["positive"]}"/>')

    # Legend
    lines.append(
        f'<rect x="{ml+8}" y="{mt+4}" width="12" height="2" fill="{P["accent"]}"/>'
        f'<text x="{ml+24}" y="{mt+9}" font-size="9" fill="{P["accent"]}" '
        f'font-family="Inter,sans-serif">Entry EV/EBITDA P50</text>'
        f'<line x1="{ml+8}" y1="{mt+18}" x2="{ml+20}" y2="{mt+18}" '
        f'stroke="{P["positive"]}" stroke-width="2" stroke-dasharray="4,2"/>'
        f'<text x="{ml+24}" y="{mt+22}" font-size="9" fill="{P["positive"]}" '
        f'font-family="Inter,sans-serif">Realized MOIC P50</text>'
    )

    lines.append("</svg>")
    return "\n".join(lines)


def _year_table(year_stats: List[Any]) -> str:
    rows = []
    for s in year_stats:
        badge = _cycle_badge(s.cycle_label)
        ee_html = (
            f'<span class="mn">{s.ee_p50:.1f}×</span>'
            if s.ee_p50 else "—"
        )
        moic_color = (
            P["positive"] if (s.moic_p50 or 0) >= 3.0
            else P["text"] if (s.moic_p50 or 0) >= 2.0
            else P["warning"]
        )
        cdim = P["text_dim"]
        cfaint = P["text_faint"]
        rows.append(
            f"<tr>"
            f"<td class='r mn'>{s.year}</td>"
            f"<td>{badge}</td>"
            f"<td class='r mn'>{s.n}</td>"
            f"<td class='r mn' style='color:{cdim}'>"
            f"{f'{s.ee_p25:.1f}×' if s.ee_p25 else '—'}</td>"
            f"<td class='r'>{ee_html}</td>"
            f"<td class='r mn' style='color:{cdim}'>"
            f"{f'{s.ee_p75:.1f}×' if s.ee_p75 else '—'}</td>"
            f"<td class='r mn' style='color:{moic_color}'>"
            f"{f'{s.moic_p50:.2f}×' if s.moic_p50 else '—'}</td>"
            f"<td class='r mn' style='color:{cfaint}'>"
            f"{f'{s.avg_hold:.1f}yr' if s.avg_hold else '—'}</td>"
            f"</tr>"
        )
    return (
        '<table class="ck-table">'
        "<thead><tr>"
        "<th class='r'>Year</th><th>Cycle</th><th class='r'>N</th>"
        "<th class='r'>P25 EE</th><th class='r'>P50 EE</th>"
        "<th class='r'>P75 EE</th><th class='r'>P50 MOIC</th>"
        "<th class='r'>Avg Hold</th>"
        "</tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody>"
        "</table>"
    )


def _quintile_table(quintiles: List[Any]) -> str:
    rows = []
    for q in quintiles:
        moic_color = (
            P["positive"] if (q.moic_p50 or 0) >= 3.0
            else P["text"] if (q.moic_p50 or 0) >= 2.0
            else P["warning"]
        )
        loss_color = P["negative"] if q.loss_rate >= 0.15 else P["warning"] if q.loss_rate >= 0.05 else P["text_faint"]
        cdim = P["text_dim"]
        cfaint = P["text_faint"]
        rows.append(
            f"<tr>"
            f"<td class='r mn'>Q{q.quintile}</td>"
            f"<td class='mn' style='color:{cdim}'>{_html.escape(q.ee_range)}</td>"
            f"<td class='r mn'>{q.n}</td>"
            f"<td class='r mn' style='color:{cfaint}'>"
            f"{f'{q.moic_p25:.2f}×' if q.moic_p25 else '—'}</td>"
            f"<td class='r mn' style='color:{moic_color}'>"
            f"{f'{q.moic_p50:.2f}×' if q.moic_p50 else '—'}</td>"
            f"<td class='r mn' style='color:{cfaint}'>"
            f"{f'{q.moic_p75:.2f}×' if q.moic_p75 else '—'}</td>"
            f"<td class='r mn' style='color:{loss_color}'>{q.loss_rate*100:.1f}%</td>"
            f"</tr>"
        )
    return (
        '<table class="ck-table">'
        "<thead><tr>"
        "<th class='r'>Quintile</th><th>EV/EBITDA Range</th>"
        "<th class='r'>N</th><th class='r'>P25 MOIC</th>"
        "<th class='r'>P50 MOIC</th><th class='r'>P75 MOIC</th>"
        "<th class='r'>Loss Rate</th>"
        "</tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody>"
        "</table>"
    )


def render_acq_timing(params: Dict[str, str]) -> str:
    from rcm_mc.data_public.acq_timing import compute_acq_timing

    result = compute_acq_timing()

    timing_prem = result.timing_premium_moic
    prem_html = (
        f'<span class="mn pos">+{timing_prem:.2f}×</span>'
        if timing_prem and timing_prem > 0
        else f'<span class="mn neg">{timing_prem:.2f}×</span>'
        if timing_prem else "—"
    )

    kpi_grid = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block(
            "Corpus Deals",
            f'<span class="mn">{result.n_total}</span>',
            "analyzed for timing",
        )
        + ck_kpi_block(
            "Peak Year P50 MOIC",
            ck_fmt_moic(result.peak_moic_p50),
            f"years: {', '.join(str(y) for y in result.peak_years[:5])}",
        )
        + ck_kpi_block(
            "Trough Year P50 MOIC",
            ck_fmt_moic(result.trough_moic_p50),
            f"years: {', '.join(str(y) for y in result.trough_years[:5])}",
        )
        + ck_kpi_block(
            "Q1 vs Q5 Timing Premium",
            prem_html,
            "MOIC gain: buy cheap vs. peak",
        )
        + ck_kpi_block(
            "Corpus EV/EBITDA P50",
            f'<span class="mn">{result.corpus_ee_p50:.1f}×</span>' if result.corpus_ee_p50 else "—",
            "all-in entry multiple",
        )
        + "</div>"
    )

    dual_chart = _dual_axis_svg(result.by_year)
    year_table = _year_table(result.by_year)
    quin_table = _quintile_table(result.quintiles)

    body = f"""
{kpi_grid}
{ck_section_header("Entry Multiple & MOIC by Vintage Year", "Blue = EV/EBITDA P50 (left), Green dashed = MOIC P50 (right). Red shading = cycle peak years.")}
<div style="overflow-x:auto;margin-bottom:24px">{dual_chart}</div>
{ck_section_header("Year-by-Year Statistics")}
<div style="overflow-x:auto;margin-bottom:24px">{year_table}</div>
{ck_section_header("Entry Multiple Quintile Analysis", "Q1 = lowest EE paid (best timing), Q5 = highest (worst timing)")}
<div style="overflow-x:auto;margin-bottom:24px">{quin_table}</div>
<p style="font-size:11px;color:{P["text_faint"]}">
  Timing premium = Q1 P50 MOIC − Q5 P50 MOIC. Positive = lower entry multiples produce
  materially better returns. Cycle labels are corpus-calibrated benchmarks.
</p>
"""

    return chartis_shell(
        body=body,
        title="Acquisition Timing Analyzer",
        active_nav="/acq-timing",
        subtitle="Entry EV/EBITDA vs. realized MOIC by vintage year — cycle timing impact",
    )
