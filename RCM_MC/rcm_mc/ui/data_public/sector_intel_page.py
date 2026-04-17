"""Sector Intelligence page — /sector-intel.

Corpus-calibrated performance benchmarks by sector:
P25/P50/P75 MOIC, IRR, loss rate, deal count, vintage sparklines,
and an SVG scatter (P50 MOIC vs loss rate) with sector labels.
"""
from __future__ import annotations

import html as _html
import importlib
import math
from typing import Any, Dict, List, Optional


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


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def _moic_spread_bar(p25: float, p50: float, p75: float, width: int = 120) -> str:
    """Box-whisker style range bar for MOIC P25/P50/P75."""
    max_m = 8.0
    def x(m): return int(min(width, max(0, m / max_m * width)))
    x25, x50, x75 = x(p25), x(p50), x(p75)
    return (
        f'<svg width="{width}" height="12" xmlns="http://www.w3.org/2000/svg">'
        f'<rect x="0" y="4" width="{width}" height="4" rx="0" fill="#1e293b"/>'
        f'<rect x="{x25}" y="2" width="{max(1,x75-x25)}" height="8" rx="0" fill="#1e3a5c"/>'
        f'<line x1="{x50}" y1="0" x2="{x50}" y2="12" stroke="#3b82f6" stroke-width="2"/>'
        f'</svg>'
    )


def _sparkline(vintage_moic: Dict[int, List[float]], width: int = 80, height: int = 20) -> str:
    """P50 MOIC by year sparkline."""
    if not vintage_moic:
        return f'<svg width="{width}" height="{height}"><line x1="0" y1="{height//2}" x2="{width}" y2="{height//2}" stroke="#1e293b" stroke-width="1"/></svg>'
    years = sorted(vintage_moic.keys())
    pts = []
    for yr in years:
        vals = sorted(vintage_moic[yr])
        pts.append((yr, vals[len(vals) // 2]))
    if len(pts) < 2:
        return f'<svg width="{width}" height="{height}"></svg>'
    min_y = min(p[1] for p in pts)
    max_y = max(p[1] for p in pts)
    rng = max(0.1, max_y - min_y)
    min_yr, max_yr = pts[0][0], pts[-1][0]
    yr_rng = max(1, max_yr - min_yr)

    def px(yr): return int((yr - min_yr) / yr_rng * (width - 2) + 1)
    def py(m): return int((1 - (m - min_y) / rng) * (height - 2) + 1)

    coords = " ".join(f"{px(yr)},{py(m)}" for yr, m in pts)
    return (
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        f'<polyline points="{coords}" fill="none" stroke="#3b82f6" stroke-width="1.2"/>'
        f'</svg>'
    )


def _scatter_svg(stats: List[Any], width: int = 480, height: int = 320) -> str:
    """P50 MOIC (x) vs loss rate (y) scatter with sector labels."""
    margin = {"l": 40, "r": 10, "t": 20, "b": 30}
    W = width - margin["l"] - margin["r"]
    H = height - margin["t"] - margin["b"]

    max_moic = max((s.moic_p75 for s in stats), default=6.0)
    max_moic = max(max_moic, 5.0)

    def sx(m): return int(margin["l"] + m / max_moic * W)
    def sy(r): return int(margin["t"] + (1 - r) * H)

    elements = []
    # grid lines
    for m in (1.0, 2.0, 3.0, 4.0, 5.0):
        gx = sx(m)
        elements.append(f'<line x1="{gx}" y1="{margin["t"]}" x2="{gx}" y2="{margin["t"]+H}" stroke="#1e293b" stroke-width="0.8"/>')
        elements.append(f'<text x="{gx}" y="{margin["t"]+H+12}" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="8" fill="#475569">{m:.0f}x</text>')
    for r in (0.0, 0.1, 0.2, 0.3, 0.5):
        gy = sy(r)
        elements.append(f'<line x1="{margin["l"]}" y1="{gy}" x2="{margin["l"]+W}" y2="{gy}" stroke="#1e293b" stroke-width="0.8"/>')
        elements.append(f'<text x="{margin["l"]-3}" y="{gy+3}" text-anchor="end" font-family="JetBrains Mono,monospace" font-size="8" fill="#475569">{r*100:.0f}%</text>')

    # points — color by moic tier
    for s in stats:
        cx = sx(s.moic_p50)
        cy = sy(s.loss_rate)
        r = max(3, min(9, int(math.sqrt(s.n_deals) * 1.5)))
        color = "#22c55e" if s.moic_p50 >= 3.0 else ("#3b82f6" if s.moic_p50 >= 2.0 else "#f59e0b" if s.moic_p50 >= 1.5 else "#ef4444")
        label = s.sector[:18].replace("_", " ")
        elements.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}" opacity="0.8">'
            f'<title>{_html.escape(s.sector)} · P50 MOIC {s.moic_p50:.2f}x · loss {s.loss_rate*100:.1f}% · {s.n_deals} deals</title>'
            f'</circle>'
        )
        if s.n_deals >= 5:
            elements.append(
                f'<text x="{cx+r+2}" y="{cy+3}" font-family="JetBrains Mono,monospace" font-size="7" fill="#64748b">'
                f'{_html.escape(label)}</text>'
            )

    # Axis labels
    elements.append(f'<text x="{margin["l"]+W//2}" y="{height-2}" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="9" fill="#64748b">P50 MOIC</text>')
    elements.append(
        f'<text x="{9}" y="{margin["t"]+H//2}" text-anchor="middle" transform="rotate(-90,9,{margin["t"]+H//2})" '
        f'font-family="JetBrains Mono,monospace" font-size="9" fill="#64748b">Loss Rate</text>'
    )

    return (
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        f'{"".join(elements)}'
        f'</svg>'
    )


def _moic_color(moic: float) -> str:
    if moic >= 3.0: return "#22c55e"
    if moic >= 2.0: return "#3b82f6"
    if moic >= 1.5: return "#f59e0b"
    return "#ef4444"


def render_sector_intel(min_deals: int = 3, sort_by: str = "moic_p50") -> str:
    from rcm_mc.ui._chartis_kit import chartis_shell, ck_section_header, ck_kpi_block
    from rcm_mc.data_public.sector_intelligence import compute_sector_stats

    corpus = _load_corpus()
    all_stats = compute_sector_stats(corpus)
    # Filter by min deals
    stats = [s for s in all_stats if s.n_deals >= min_deals]

    # Sort
    sort_keys = {
        "moic_p50":    lambda s: -s.moic_p50,
        "moic_p25":    lambda s: -s.moic_p25,
        "moic_p75":    lambda s: -s.moic_p75,
        "loss_rate":   lambda s: s.loss_rate,
        "n_deals":     lambda s: -s.n_deals,
        "avg_hold":    lambda s: s.avg_hold,
        "sharpe":      lambda s: -s.sharpe_proxy,
        "irr_p50":     lambda s: -s.irr_p50,
    }
    stats.sort(key=sort_keys.get(sort_by, lambda s: -s.moic_p50))

    total_sectors = len(all_stats)
    total_deals_with_sector = sum(s.n_deals for s in all_stats)
    avg_p50 = sum(s.moic_p50 for s in stats) / len(stats) if stats else 0
    top_sector = stats[0].sector.replace("_", " ").title() if stats else "—"
    worst_loss = max((s for s in stats), key=lambda s: s.loss_rate, default=None)

    # KPIs
    kpis = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Sectors Analyzed", f'<span class="mn">{len(stats)}</span>', f"{total_sectors} total in corpus")
        + ck_kpi_block("Deals w/ Sector", f'<span class="mn">{total_deals_with_sector}</span>', "have sector tag")
        + ck_kpi_block("Avg P50 MOIC", f'<span class="mn" style="color:{_moic_color(avg_p50)}">{avg_p50:.2f}x</span>', "filtered sectors")
        + ck_kpi_block("Top Sector", f'<span class="mn" style="font-size:11px;">{_html.escape(top_sector[:20])}</span>',
                        f'P50 {stats[0].moic_p50:.2f}x' if stats else "—")
        + (ck_kpi_block("Highest Loss Rate",
                        f'<span class="mn" style="color:#ef4444">{worst_loss.loss_rate*100:.1f}%</span>',
                        _html.escape(worst_loss.sector[:22].replace("_"," ")))
           if worst_loss else "")
        + '</div>'
    )

    # Scatter panel
    scatter = _scatter_svg(stats)
    scatter_panel = f"""
<div class="ck-panel">
  <div class="ck-panel-title">P50 MOIC vs Loss Rate — bubble size = deal count</div>
  <div style="padding:12px 16px;overflow-x:auto;">
    {scatter}
    <div style="margin-top:6px;font-size:9px;color:#475569;">
      Green ≥3.0× · Blue ≥2.0× · Amber ≥1.5× · Red &lt;1.5× P50 MOIC
      &nbsp;|&nbsp; Hover for sector details
    </div>
  </div>
</div>"""

    # Sort controls
    sort_links = "".join(
        f'<a href="/sector-intel?min_deals={min_deals}&sort_by={k}" style="margin-right:8px;font-size:10px;'
        f'color:{"#3b82f6" if k==sort_by else "#64748b"};text-decoration:none;">{k.replace("_"," ")}</a>'
        for k in ("moic_p50", "moic_p25", "moic_p75", "loss_rate", "n_deals", "avg_hold", "sharpe", "irr_p50")
    )
    filter_bar = f"""
<div class="ck-panel">
  <div style="padding:8px 16px;display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
    <div>
      <span style="font-size:9px;color:#475569;text-transform:uppercase;letter-spacing:0.08em;margin-right:6px;">Sort</span>
      {sort_links}
    </div>
    <div>
      <span style="font-size:9px;color:#475569;text-transform:uppercase;letter-spacing:0.08em;margin-right:6px;">Min Deals</span>
      {"".join(
        f'<a href="/sector-intel?min_deals={n}&sort_by={sort_by}" style="margin-right:6px;font-size:10px;'
        f'color:{"#3b82f6" if n==min_deals else "#64748b"};text-decoration:none;">{n}+</a>'
        for n in (1, 3, 5, 10)
      )}
    </div>
  </div>
</div>"""

    # Table header
    def _th(label: str, key: str) -> str:
        color = "#e2e8f0" if sort_by == key else "#64748b"
        return (
            f'<th style="padding:5px 8px;white-space:nowrap;cursor:pointer;">'
            f'<a href="/sector-intel?min_deals={min_deals}&sort_by={key}" style="color:{color};text-decoration:none;">{label}</a></th>'
        )

    rows = []
    for i, s in enumerate(stats):
        stripe = ' style="background:#0f172a"' if i % 2 == 1 else ""
        mc = _moic_color(s.moic_p50)
        rows.append(f"""<tr{stripe}>
  <td style="padding:5px 8px;font-size:10px;white-space:nowrap;">{_html.escape(s.sector[:40].replace('_',' '))}</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{s.n_deals}</td>
  <td style="padding:5px 8px;text-align:center;">
    {_moic_spread_bar(s.moic_p25, s.moic_p50, s.moic_p75)}
  </td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;color:#64748b;">{s.moic_p25:.2f}x</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;color:{mc};font-weight:500;">{s.moic_p50:.2f}x</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;color:#64748b;">{s.moic_p75:.2f}x</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{s.irr_p50*100:.1f}%</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;
      color:{'#ef4444' if s.loss_rate>0.2 else '#f59e0b' if s.loss_rate>0.1 else '#22c55e'};">{s.loss_rate*100:.1f}%</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{s.avg_hold:.1f}y</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">${s.avg_ev_mm:.0f}M</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;color:#3b82f6;">{s.sharpe_proxy:.2f}</td>
  <td style="padding:5px 8px;">{_sparkline(s.vintage_moic)}</td>
</tr>""")

    table = f"""
<div class="ck-panel">
  <div class="ck-panel-title">Sector Performance — {len(stats)} sectors · {total_deals_with_sector} tagged deals</div>
  <div class="ck-table-wrap" style="max-height:600px;overflow-y:auto;">
    <table class="ck-table" style="width:100%;">
      <thead style="position:sticky;top:0;background:#111827;z-index:2;">
        <tr>
          {_th("Sector", "sector")}
          {_th("Deals", "n_deals")}
          <th style="padding:5px 8px;color:#64748b;min-width:130px;">MOIC Range</th>
          {_th("P25", "moic_p25")}
          {_th("P50", "moic_p50")}
          {_th("P75", "moic_p75")}
          {_th("P50 IRR", "irr_p50")}
          {_th("Loss %", "loss_rate")}
          {_th("Avg Hold", "avg_hold")}
          <th style="padding:5px 8px;color:#64748b;">Avg EV</th>
          {_th("Sharpe", "sharpe")}
          <th style="padding:5px 8px;color:#64748b;">Trend</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </div>
  <div style="padding:6px 16px 10px;font-size:9px;color:#475569;">
    P25/P50/P75 = corpus percentile MOIC · Loss % = fraction with MOIC &lt;1.0 · Sharpe = (P50−1) / (P75−P25) · Trend = vintage P50 sparkline
  </div>
</div>"""

    body = kpis + ck_section_header("SECTOR SCATTER", "P50 MOIC vs loss rate — portfolio positioning map") + scatter_panel + filter_bar + ck_section_header("SECTOR BENCHMARKS", f"P25/P50/P75 MOIC · IRR · loss rate · hold — sorted by {sort_by.replace('_',' ')}") + table

    return chartis_shell(
        body,
        title="Sector Intelligence",
        active_nav="/sector-intel",
        subtitle=(
            f"{len(stats)} sectors · {total_deals_with_sector} tagged deals · "
            f"avg P50 MOIC {avg_p50:.2f}x · sorted by {sort_by.replace('_', ' ')}"
        ),
    )
