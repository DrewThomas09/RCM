"""Vintage Performance page — /vintage-perf.

Year-by-year corpus performance: P50 MOIC bar chart, deal count histogram,
vintage heatmap (year × MOIC tier), and detailed stats table.
"""
from __future__ import annotations

import html as _html
import importlib
import math
from typing import Any, Dict, List


def _load_corpus() -> List[Dict[str, Any]]:
    from rcm_mc.data_public.deals_corpus import _SEED_DEALS
    from rcm_mc.data_public.extended_seed import EXTENDED_SEED_DEALS
    result = list(_SEED_DEALS) + list(EXTENDED_SEED_DEALS)
    for i in range(2, 32):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            result += list(getattr(mod, f"EXTENDED_SEED_DEALS_{i}"))
        except (ImportError, AttributeError):
            pass
    return result


def _moic_color(moic: float) -> str:
    if moic >= 3.0: return "#22c55e"
    if moic >= 2.0: return "#3b82f6"
    if moic >= 1.5: return "#f59e0b"
    return "#ef4444"


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def _moic_bar_chart(stats: List[Any], width: int = 600, height: int = 160) -> str:
    """Horizontal bar chart: year (y-axis) × P50 MOIC (x-axis) with P25/P75 whiskers."""
    if not stats:
        return ""
    margin = {"l": 45, "r": 10, "t": 10, "b": 20}
    W = width - margin["l"] - margin["r"]
    max_moic = max(s.moic_p75 for s in stats)
    max_moic = max(max_moic, 4.0)

    row_h = max(8, (height - margin["t"] - margin["b"]) // len(stats))
    actual_h = row_h * len(stats) + margin["t"] + margin["b"]

    def px(m): return int(margin["l"] + m / max_moic * W)

    elements = []
    # grid
    for m in (1.0, 2.0, 3.0, 4.0, 5.0):
        if m > max_moic: break
        gx = px(m)
        elements.append(f'<line x1="{gx}" y1="{margin["t"]}" x2="{gx}" y2="{margin["t"]+row_h*len(stats)}" stroke="#1e293b" stroke-width="0.8"/>')
        elements.append(f'<text x="{gx}" y="{margin["t"]+row_h*len(stats)+12}" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="8" fill="#475569">{m:.0f}x</text>')
    # 1x reference
    ref_x = px(1.0)
    elements.append(f'<line x1="{ref_x}" y1="{margin["t"]}" x2="{ref_x}" y2="{margin["t"]+row_h*len(stats)}" stroke="#ef4444" stroke-width="0.8" stroke-dasharray="3,3"/>')

    for i, s in enumerate(stats):
        y = margin["t"] + i * row_h
        bar_h = max(2, row_h - 3)
        bar_w = max(1, px(s.moic_p50) - margin["l"])
        color = _moic_color(s.moic_p50)
        # bar
        elements.append(f'<rect x="{margin["l"]}" y="{y+1}" width="{bar_w}" height="{bar_h}" fill="{color}" opacity="0.75"/>')
        # whisker P25-P75
        wx25, wx75 = px(s.moic_p25), px(s.moic_p75)
        mid_y = y + bar_h // 2 + 1
        elements.append(f'<line x1="{wx25}" y1="{mid_y-3}" x2="{wx75}" y2="{mid_y-3}" stroke="#94a3b8" stroke-width="1.2"/>')
        elements.append(f'<line x1="{wx25}" y1="{mid_y-5}" x2="{wx25}" y2="{mid_y-1}" stroke="#64748b" stroke-width="1"/>')
        elements.append(f'<line x1="{wx75}" y1="{mid_y-5}" x2="{wx75}" y2="{mid_y-1}" stroke="#64748b" stroke-width="1"/>')
        # year label
        elements.append(f'<text x="{margin["l"]-3}" y="{y+bar_h-1}" text-anchor="end" font-family="JetBrains Mono,monospace" font-size="8" fill="#94a3b8">{s.year}</text>')
        # P50 value
        label_x = px(s.moic_p50) + 3
        elements.append(f'<text x="{label_x}" y="{y+bar_h-1}" font-family="JetBrains Mono,monospace" font-size="7.5" fill="{color}">{s.moic_p50:.2f}x</text>')

    return (
        f'<svg width="{width}" height="{actual_h}" xmlns="http://www.w3.org/2000/svg">'
        f'{"".join(elements)}'
        f'</svg>'
    )


def _deal_count_histogram(stats: List[Any], width: int = 600, height: int = 80) -> str:
    """Bar chart of deal count per vintage year."""
    if not stats:
        return ""
    max_n = max(s.n_deals for s in stats)
    bar_w = max(4, (width - 20) // len(stats))
    W = bar_w * len(stats)
    elements = []
    for i, s in enumerate(stats):
        bh = max(2, int(s.n_deals / max_n * (height - 20)))
        bx = 10 + i * bar_w
        by = height - 12 - bh
        color = "#1d4ed8"
        elements.append(f'<rect x="{bx}" y="{by}" width="{max(1,bar_w-2)}" height="{bh}" fill="{color}" opacity="0.8"/>')
        if bar_w >= 16:
            elements.append(
                f'<text x="{bx+bar_w//2}" y="{height-2}" text-anchor="middle" '
                f'font-family="JetBrains Mono,monospace" font-size="7" fill="#475569">{s.year}</text>'
            )
    return (
        f'<svg width="{W+20}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        f'{"".join(elements)}'
        f'</svg>'
    )


def _heatmap_svg(stats: List[Any], width: int = 600) -> str:
    """MOIC-tier heatmap: one cell per vintage year, colored by tier."""
    if not stats:
        return ""
    cell_w = max(30, min(60, (width - 20) // len(stats)))
    cell_h = 28
    elements = []
    for i, s in enumerate(stats):
        cx = 10 + i * cell_w
        color = _moic_color(s.moic_p50)
        elements.append(f'<rect x="{cx}" y="0" width="{cell_w-2}" height="{cell_h}" fill="{color}" opacity="0.85" rx="1"/>')
        elements.append(
            f'<text x="{cx+cell_w//2-1}" y="11" text-anchor="middle" '
            f'font-family="JetBrains Mono,monospace" font-size="8.5" fill="#0a0e17" font-weight="600">{s.year}</text>'
        )
        elements.append(
            f'<text x="{cx+cell_w//2-1}" y="23" text-anchor="middle" '
            f'font-family="JetBrains Mono,monospace" font-size="8" fill="#0a0e17">{s.moic_p50:.1f}x</text>'
        )
    W = 20 + len(stats) * cell_w
    return (
        f'<svg width="{W}" height="{cell_h}" xmlns="http://www.w3.org/2000/svg">'
        f'{"".join(elements)}'
        f'</svg>'
    )


def render_vintage_perf() -> str:
    from rcm_mc.ui._chartis_kit import chartis_shell, ck_section_header, ck_kpi_block
    from rcm_mc.data_public.vintage_analytics import compute_vintage_stats

    corpus = _load_corpus()
    stats = compute_vintage_stats(corpus)

    if not stats:
        return chartis_shell("<p>No vintage data available.</p>", title="Vintage Performance", active_nav="/vintage-perf")

    total_deals = sum(s.n_deals for s in stats)
    best = max(stats, key=lambda s: s.moic_p50)
    worst = min(stats, key=lambda s: s.moic_p50)
    all_moics = [s.moic_p50 for s in stats]
    avg_p50 = sum(all_moics) / len(all_moics)
    total_yrs = len(stats)

    kpis = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Vintages", f'<span class="mn">{total_yrs}</span>', f"{stats[0].year}–{stats[-1].year}")
        + ck_kpi_block("Total Deals", f'<span class="mn">{total_deals}</span>', "across all vintages")
        + ck_kpi_block("Avg P50 MOIC", f'<span class="mn" style="color:{_moic_color(avg_p50)}">{avg_p50:.2f}x</span>', "vintage-weighted")
        + ck_kpi_block("Best Vintage", f'<span class="mn" style="color:#22c55e">{best.year}</span>', f"P50 {best.moic_p50:.2f}x")
        + ck_kpi_block("Worst Vintage", f'<span class="mn" style="color:#ef4444">{worst.year}</span>', f"P50 {worst.moic_p50:.2f}x")
        + '</div>'
    )

    heatmap = _heatmap_svg(stats, width=700)
    heatmap_panel = f"""
<div class="ck-panel">
  <div class="ck-panel-title">Vintage Heatmap — P50 MOIC by Entry Year</div>
  <div style="padding:12px 16px;overflow-x:auto;">
    {heatmap}
    <div style="margin-top:6px;font-size:9px;color:#475569;">
      Green ≥3.0× · Blue ≥2.0× · Amber ≥1.5× · Red &lt;1.5×
    </div>
  </div>
</div>"""

    moic_chart = _moic_bar_chart(stats, width=640)
    moic_panel = f"""
<div class="ck-panel">
  <div class="ck-panel-title">P50 MOIC by Vintage (bar=P50, whiskers=P25/P75)</div>
  <div style="padding:12px 16px;overflow-x:auto;">
    {moic_chart}
  </div>
</div>"""

    count_chart = _deal_count_histogram(stats, width=640)
    count_panel = f"""
<div class="ck-panel">
  <div class="ck-panel-title">Deal Count by Vintage Year</div>
  <div style="padding:12px 16px;overflow-x:auto;">
    {count_chart}
  </div>
</div>"""

    chart_grid = f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:0;">{moic_panel}{count_panel}</div>'

    # Table
    rows = []
    for i, s in enumerate(stats):
        stripe = ' style="background:#0f172a"' if i % 2 == 1 else ""
        mc = _moic_color(s.moic_p50)
        sectors_html = "".join(
            f'<span style="display:inline-block;margin:1px 2px;padding:1px 5px;border:1px solid #1e293b;'
            f'font-size:8.5px;font-family:var(--ck-mono);color:#64748b;">{_html.escape(sec[:16])}</span>'
            for sec in s.top_sectors[:3]
        )
        rows.append(f"""<tr{stripe}>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:center;font-weight:600;">{s.year}</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{s.n_deals}</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;color:#64748b;">{s.moic_p25:.2f}x</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;color:{mc};font-weight:500;">{s.moic_p50:.2f}x</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;color:#64748b;">{s.moic_p75:.2f}x</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{s.irr_p50*100:.1f}%</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{s.avg_hold:.1f}y</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;
      color:{'#ef4444' if s.loss_rate>0.2 else '#f59e0b' if s.loss_rate>0.1 else '#22c55e'};">{s.loss_rate*100:.1f}%</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">${s.avg_ev_mm:.0f}M</td>
  <td style="padding:5px 8px;">{sectors_html}</td>
</tr>""")

    table = f"""
<div class="ck-panel">
  <div class="ck-panel-title">Vintage Detail — {total_yrs} years · {total_deals} deals</div>
  <div class="ck-table-wrap" style="max-height:500px;overflow-y:auto;">
    <table class="ck-table" style="width:100%;">
      <thead style="position:sticky;top:0;background:#111827;z-index:2;">
        <tr>
          <th style="padding:5px 8px;text-align:center;color:#64748b;">Year</th>
          <th style="padding:5px 8px;text-align:right;color:#64748b;">Deals</th>
          <th style="padding:5px 8px;text-align:right;color:#64748b;">P25 MOIC</th>
          <th style="padding:5px 8px;text-align:right;color:#64748b;">P50 MOIC</th>
          <th style="padding:5px 8px;text-align:right;color:#64748b;">P75 MOIC</th>
          <th style="padding:5px 8px;text-align:right;color:#64748b;">P50 IRR</th>
          <th style="padding:5px 8px;text-align:right;color:#64748b;">Avg Hold</th>
          <th style="padding:5px 8px;text-align:right;color:#64748b;">Loss %</th>
          <th style="padding:5px 8px;text-align:right;color:#64748b;">Avg EV</th>
          <th style="padding:5px 8px;color:#64748b;">Top Sectors</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </div>
</div>"""

    body = kpis + ck_section_header("VINTAGE HEATMAP", "P50 MOIC by entry year — macro timing view") + heatmap_panel + ck_section_header("PERFORMANCE CHARTS", "P50 MOIC with P25/P75 range · deal count by year") + chart_grid + ck_section_header("VINTAGE DETAIL", "year-by-year breakdown") + table

    return chartis_shell(
        body,
        title="Vintage Performance",
        active_nav="/vintage-perf",
        subtitle=(
            f"{total_yrs} vintages · {total_deals} deals · "
            f"best {best.year} ({best.moic_p50:.2f}x) · "
            f"worst {worst.year} ({worst.moic_p50:.2f}x) · "
            f"avg P50 {avg_p50:.2f}x"
        ),
    )
