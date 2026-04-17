"""Corpus Intelligence Dashboard — /corpus-dashboard.

Executive summary of all 635-deal corpus analytics:
- Top-line KPIs (deal count, avg MOIC, sectors, vintages)
- Mini sparkline SVGs from sector/vintage/size/payer dimensions
- Quick-navigation tiles to all corpus intel pages
- Recent data quality summary
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


def _pct(vals: List[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    idx = p / 100.0 * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def _moic_color(m: float) -> str:
    if m >= 3.0: return "#22c55e"
    if m >= 2.0: return "#3b82f6"
    if m >= 1.5: return "#f59e0b"
    return "#ef4444"


# ---------------------------------------------------------------------------
# Mini SVG charts for dashboard tiles
# ---------------------------------------------------------------------------

def _mini_moic_hist(moics: List[float], width: int = 140, height: int = 50) -> str:
    """Mini MOIC histogram for dashboard tile."""
    if not moics:
        return ""
    buckets = [0] * 8  # 0-1, 1-2, 2-3, 3-4, 4-5, 5-6, 6-8, 8+
    edges = [0, 1, 2, 3, 4, 5, 6, 8, 99]
    for m in moics:
        for i in range(len(edges)-1):
            if edges[i] <= m < edges[i+1]:
                buckets[i] += 1
                break
    max_n = max(buckets) or 1
    bar_w = (width - 4) // len(buckets)
    elements = []
    for i, cnt in enumerate(buckets):
        bh = max(0, int(cnt / max_n * (height - 8)))
        bx = 2 + i * bar_w
        by = height - 4 - bh
        color = "#22c55e" if i >= 2 else ("#f59e0b" if i == 1 else "#ef4444")
        elements.append(f'<rect x="{bx}" y="{by}" width="{max(1,bar_w-1)}" height="{bh}" fill="{color}" opacity="0.8"/>')
    return (
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        f'{"".join(elements)}'
        f'</svg>'
    )


def _mini_sparkline(ys: List[float], width: int = 120, height: int = 30) -> str:
    """Simple line sparkline."""
    if len(ys) < 2:
        return ""
    min_y, max_y = min(ys), max(ys)
    rng = max(0.01, max_y - min_y)
    step = (width - 4) / max(1, len(ys) - 1)
    def py(v): return int(2 + (1 - (v - min_y) / rng) * (height - 4))
    pts = " ".join(f"{int(2+i*step)},{py(v)}" for i, v in enumerate(ys))
    return (
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        f'<polyline points="{pts}" fill="none" stroke="#3b82f6" stroke-width="1.5"/>'
        f'</svg>'
    )


def _nav_tile(title: str, href: str, subtitle: str, value: str, value_color: str = "#e2e8f0", svg: str = "") -> str:
    return f"""
<a href="{_html.escape(href)}" style="display:block;text-decoration:none;border:1px solid #1e293b;padding:12px;background:#111827;border-radius:2px;">
  <div style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px;">{_html.escape(title)}</div>
  <div style="font-family:'JetBrains Mono',monospace;font-size:18px;font-variant-numeric:tabular-nums;color:{value_color};line-height:1.1;">{value}</div>
  <div style="font-size:9px;color:#475569;margin-top:2px;">{_html.escape(subtitle)}</div>
  {f'<div style="margin-top:6px;">{svg}</div>' if svg else ''}
</a>"""


def render_corpus_dashboard() -> str:
    from rcm_mc.ui._chartis_kit import chartis_shell, ck_section_header, ck_kpi_block
    from rcm_mc.data_public.sector_intelligence import compute_sector_stats
    from rcm_mc.data_public.vintage_analytics import compute_vintage_stats
    from rcm_mc.data_public.size_analytics import compute_size_analytics
    from rcm_mc.data_public.deal_quality_score import score_corpus_quality

    corpus = _load_corpus()

    # Core MOIC stats
    moics = [float(d["realized_moic"]) for d in corpus if d.get("realized_moic") is not None]
    irrs  = [float(d["realized_irr"])  for d in corpus if d.get("realized_irr")  is not None]
    holds = [float(d["hold_years"])    for d in corpus if d.get("hold_years")     is not None]
    evs   = [float(d["ev_mm"])         for d in corpus if d.get("ev_mm")          is not None]

    n = len(corpus)
    moic_p50  = _pct(moics, 50)
    irr_p50   = _pct(irrs, 50)
    hold_avg  = sum(holds) / len(holds) if holds else 0
    loss_rate = sum(1 for m in moics if m < 1.0) / len(moics) if moics else 0
    ev_p50    = _pct(evs, 50)

    # Sector stats
    sector_stats = compute_sector_stats(corpus)
    top_sectors  = sector_stats[:5]
    n_sectors    = len(sector_stats)

    # Vintage stats
    vintage_stats = compute_vintage_stats(corpus)
    vintage_p50s  = [s.moic_p50 for s in vintage_stats]

    # Size stats
    size_profile = compute_size_analytics(corpus)

    # Quality
    quality_scores = score_corpus_quality(corpus)
    from collections import Counter
    tier_counts = Counter(s.tier for s in quality_scores)
    avg_quality = sum(s.quality_score for s in quality_scores) / n if n else 0

    # With sector
    n_with_sector = sum(1 for d in corpus if d.get("sector"))

    # Top-line KPIs
    kpis = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Corpus Deals", f'<span class="mn">{n:,}</span>', "in analysis")
        + ck_kpi_block("P50 MOIC", f'<span class="mn" style="color:{_moic_color(moic_p50)}">{moic_p50:.2f}x</span>', f"P25: {_pct(moics,25):.2f}x · P75: {_pct(moics,75):.2f}x")
        + ck_kpi_block("P50 IRR", f'<span class="mn">{irr_p50*100:.1f}%</span>', "realized median")
        + ck_kpi_block("Loss Rate", f'<span class="mn" style="color:{"#ef4444" if loss_rate>0.15 else "#f59e0b"}">{loss_rate*100:.1f}%</span>', "MOIC < 1.0×")
        + ck_kpi_block("Avg Hold", f'<span class="mn">{hold_avg:.1f}y</span>', "years to exit")
        + ck_kpi_block("Avg Quality", f'<span class="mn">{avg_quality:.1f}/100</span>', f"A:{tier_counts.get('A',0)} B:{tier_counts.get('B',0)} C+D:{tier_counts.get('C',0)+tier_counts.get('D',0)}")
        + '</div>'
    )

    # MOIC distribution mini panel
    moic_hist_svg = _mini_moic_hist(moics, width=300, height=70)
    moic_panel = f"""
<div class="ck-panel" style="grid-column:span 2;">
  <div class="ck-panel-title">MOIC Distribution — {len(moics):,} deals</div>
  <div style="padding:12px 16px;display:flex;align-items:flex-end;gap:24px;">
    {moic_hist_svg}
    <table style="font-size:9.5px;line-height:2.0;">
      <tr><td class="dim">P10</td><td class="mono" style="padding-left:12px;">{_pct(moics,10):.2f}x</td></tr>
      <tr><td class="dim">P25</td><td class="mono" style="padding-left:12px;">{_pct(moics,25):.2f}x</td></tr>
      <tr><td class="dim">P50</td><td class="mono" style="padding-left:12px;color:{_moic_color(moic_p50)}">{moic_p50:.2f}x</td></tr>
      <tr><td class="dim">P75</td><td class="mono" style="padding-left:12px;">{_pct(moics,75):.2f}x</td></tr>
      <tr><td class="dim">P90</td><td class="mono" style="padding-left:12px;">{_pct(moics,90):.2f}x</td></tr>
    </table>
    <div style="font-size:9px;color:#475569;max-width:180px;line-height:1.6;">
      Bars: 0–1 (red) · 1–2 (amber) · 2+ (green)<br>
      {sum(1 for m in moics if m>=2)}/{len(moics)} deals achieved ≥2× ({100*sum(1 for m in moics if m>=2)/len(moics):.0f}%)
    </div>
  </div>
</div>"""

    # Vintage trend mini
    vintage_svg = _mini_sparkline(vintage_p50s, width=160, height=40)
    yr_range = f"{vintage_stats[0].year}–{vintage_stats[-1].year}" if vintage_stats else "—"

    # Nav tiles grid
    sector_list = ", ".join(s.sector[:14].replace("_"," ") for s in top_sectors[:3])
    tiles = f"""
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:0 0 4px 0;">
  {_nav_tile("Sector Intelligence", "/sector-intel",
    f"{n_with_sector} tagged · {n_sectors} sectors",
    f"{top_sectors[0].moic_p50:.2f}x" if top_sectors else "—",
    _moic_color(top_sectors[0].moic_p50) if top_sectors else "#e2e8f0",
    "")}
  {_nav_tile("Vintage Performance", "/vintage-perf",
    f"{yr_range} · {len(vintage_stats)} vintages",
    f"{_pct(vintage_p50s,50):.2f}x" if vintage_p50s else "—",
    _moic_color(_pct(vintage_p50s,50)) if vintage_p50s else "#e2e8f0",
    vintage_svg)}
  {_nav_tile("Deal Size Intelligence", "/size-intel",
    f"P50 EV ${size_profile.ev_p50:.0f}M · {len(size_profile.buckets)} buckets",
    f"${size_profile.ev_p50:.0f}M",
    "#3b82f6",
    "")}
  {_nav_tile("Payer Intelligence", "/payer-intel",
    f"commercial/medicare/medicaid/self-pay",
    f"{n} deals",
    "#94a3b8",
    "")}
  {_nav_tile("Leverage Intelligence", "/leverage-intel",
    "capital structure by bucket",
    f"{n} deals",
    "#94a3b8",
    "")}
  {_nav_tile("Deal Quality", "/deal-quality",
    f"A:{tier_counts.get('A',0)} B:{tier_counts.get('B',0)} C:{tier_counts.get('C',0)} D:{tier_counts.get('D',0)}",
    f"{avg_quality:.0f}/100",
    "#22c55e" if avg_quality >= 70 else "#f59e0b",
    "")}
  {_nav_tile("Underwriting", "/underwriting",
    "LBO model · sensitivity table",
    "LBO",
    "#64748b",
    "")}
  {_nav_tile("Portfolio Optimizer", "/portfolio-optimizer",
    "HHI · sector weights vs optimal",
    "HHI",
    "#64748b",
    "")}
  {_nav_tile("Backtester", "/backtest",
    "OLS calibration · R² · MAE",
    "OLS",
    "#64748b",
    "")}
  {_nav_tile("Comparables", "/comparables",
    "similarity-weighted peer set",
    "Peers",
    "#64748b",
    "")}
  {_nav_tile("Risk Matrix", "/risk-matrix",
    "entry risk vs realized MOIC",
    "Risk",
    "#64748b",
    "")}
  {_nav_tile("Sponsor League", "/sponsor-league",
    "sponsor consistency scores",
    "SPO",
    "#64748b",
    "")}
</div>"""

    # Top sectors table
    top_sector_rows = []
    for i, s in enumerate(sector_stats[:15]):
        stripe = ' style="background:#0f172a"' if i % 2 == 1 else ""
        mc = _moic_color(s.moic_p50)
        top_sector_rows.append(f"""<tr{stripe}>
  <td style="padding:4px 8px;font-size:10px;">{_html.escape(s.sector[:30].replace('_',' '))}</td>
  <td style="padding:4px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{s.n_deals}</td>
  <td style="padding:4px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;color:{mc}">{s.moic_p50:.2f}x</td>
  <td style="padding:4px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{s.irr_p50*100:.1f}%</td>
  <td style="padding:4px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;
      color:{'#ef4444' if s.loss_rate>0.2 else '#f59e0b' if s.loss_rate>0.1 else '#22c55e'};">{s.loss_rate*100:.0f}%</td>
</tr>""")

    sector_table = f"""
<div class="ck-panel">
  <div class="ck-panel-title">Top Sectors by P50 MOIC</div>
  <div class="ck-table-wrap">
    <table class="ck-table" style="width:100%;">
      <thead><tr>
        <th style="padding:5px 8px;color:#64748b;">Sector</th>
        <th style="padding:5px 8px;color:#64748b;text-align:right;">Deals</th>
        <th style="padding:5px 8px;color:#64748b;text-align:right;">P50 MOIC</th>
        <th style="padding:5px 8px;color:#64748b;text-align:right;">P50 IRR</th>
        <th style="padding:5px 8px;color:#64748b;text-align:right;">Loss %</th>
      </tr></thead>
      <tbody>{''.join(top_sector_rows)}</tbody>
    </table>
  </div>
  <div style="padding:0 16px 8px;font-size:9px;color:#475569;">
    <a href="/sector-intel" style="color:#3b82f6;text-decoration:none;">→ Full sector intelligence</a>
  </div>
</div>"""

    # Vintage mini table
    vintage_rows = []
    for i, s in enumerate(vintage_stats[-10:]):  # last 10 vintages
        stripe = ' style="background:#0f172a"' if i % 2 == 1 else ""
        mc = _moic_color(s.moic_p50)
        vintage_rows.append(f"""<tr{stripe}>
  <td style="padding:4px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;">{s.year}</td>
  <td style="padding:4px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{s.n_deals}</td>
  <td style="padding:4px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;color:{mc}">{s.moic_p50:.2f}x</td>
  <td style="padding:4px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;
      color:{'#ef4444' if s.loss_rate>0.2 else '#f59e0b' if s.loss_rate>0.1 else '#22c55e'};">{s.loss_rate*100:.0f}%</td>
</tr>""")

    vintage_table = f"""
<div class="ck-panel">
  <div class="ck-panel-title">Recent Vintages</div>
  <div class="ck-table-wrap">
    <table class="ck-table" style="width:100%;">
      <thead><tr>
        <th style="padding:5px 8px;color:#64748b;">Year</th>
        <th style="padding:5px 8px;color:#64748b;text-align:right;">Deals</th>
        <th style="padding:5px 8px;color:#64748b;text-align:right;">P50 MOIC</th>
        <th style="padding:5px 8px;color:#64748b;text-align:right;">Loss %</th>
      </tr></thead>
      <tbody>{''.join(vintage_rows)}</tbody>
    </table>
  </div>
  <div style="padding:0 16px 8px;font-size:9px;color:#475569;">
    <a href="/vintage-perf" style="color:#3b82f6;text-decoration:none;">→ Full vintage analysis</a>
  </div>
</div>"""

    body = (
        kpis
        + ck_section_header("MOIC PROFILE", f"distribution across {len(moics):,} realized deals")
        + moic_panel
        + ck_section_header("CORPUS INTEL PAGES", "click to explore each analytical dimension")
        + tiles
        + ck_section_header("BENCHMARKS", "sector and vintage summary")
        + f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:0;">{sector_table}{vintage_table}</div>'
    )

    return chartis_shell(
        body,
        title="Corpus Dashboard",
        active_nav="/corpus-dashboard",
        subtitle=(
            f"{n:,} deals · P50 MOIC {moic_p50:.2f}x · P50 IRR {irr_p50*100:.1f}% · "
            f"loss rate {loss_rate*100:.1f}% · avg quality {avg_quality:.0f}/100"
        ),
    )
