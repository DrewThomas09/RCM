"""Deal Size Intelligence page — /size-intel.

EV distribution across the corpus, performance by size bucket,
log-scale EV vs MOIC scatter, and deal count histogram.
"""
from __future__ import annotations

import html as _html
import importlib
import math
from typing import Any, Dict, List, Tuple


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


def _moic_color(m: float) -> str:
    if m >= 3.0: return "#22c55e"
    if m >= 2.0: return "#2fb3ad"
    if m >= 1.5: return "#b8732a"
    return "#b5321e"


def _log_scale_scatter(points: List[Tuple[float, float, str]], width: int = 500, height: int = 260) -> str:
    """Log-scale EV (x) vs MOIC (y) scatter."""
    if not points:
        return ""
    margin = {"l": 50, "r": 10, "t": 10, "b": 35}
    W = width - margin["l"] - margin["r"]
    H = height - margin["t"] - margin["b"]

    evs   = [p[0] for p in points]
    moics = [p[1] for p in points]
    log_min = math.log10(max(1.0, min(evs)))
    log_max = math.log10(max(evs))
    max_moic = max(moics)
    max_moic = max(max_moic, 4.0)

    def sx(ev): return int(margin["l"] + (math.log10(max(1.0, ev)) - log_min) / max(0.001, log_max - log_min) * W)
    def sy(m):  return int(margin["t"] + (1 - m / max_moic) * H)

    elements = []
    for ev_tick in (10, 50, 100, 300, 500, 1000, 3000, 10000):
        if ev_tick < min(evs) * 0.5 or ev_tick > max(evs) * 2:
            continue
        gx = sx(ev_tick)
        if gx < margin["l"] or gx > margin["l"] + W:
            continue
        elements.append(f'<line x1="{gx}" y1="{margin["t"]}" x2="{gx}" y2="{margin["t"]+H}" stroke="#d6cfc3" stroke-width="0.8"/>')
        label = f"${ev_tick}M" if ev_tick < 1000 else f"${ev_tick//1000}B"
        elements.append(f'<text x="{gx}" y="{margin["t"]+H+12}" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="7" fill="#475569">{label}</text>')
    for m in (1.0, 2.0, 3.0, 4.0):
        if m > max_moic: break
        gy = sy(m)
        elements.append(f'<line x1="{margin["l"]}" y1="{gy}" x2="{margin["l"]+W}" y2="{gy}" stroke="#d6cfc3" stroke-width="0.8"/>')
        elements.append(f'<text x="{margin["l"]-3}" y="{gy+3}" text-anchor="end" font-family="JetBrains Mono,monospace" font-size="8" fill="#475569">{m:.0f}x</text>')

    for ev, moic, name in points:
        cx = sx(ev); cy = sy(moic)
        color = _moic_color(moic)
        elements.append(f'<circle cx="{cx}" cy="{cy}" r="2.5" fill="{color}" opacity="0.7"><title>{_html.escape(name[:40])} · ${ev:.0f}M · {moic:.2f}x</title></circle>')

    elements.append(f'<text x="{margin["l"]+W//2}" y="{height-2}" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="9" fill="#7a8699">EV (log scale)</text>')
    elements.append(f'<text x="9" y="{margin["t"]+H//2}" text-anchor="middle" transform="rotate(-90,9,{margin["t"]+H//2})" font-family="JetBrains Mono,monospace" font-size="9" fill="#7a8699">MOIC</text>')
    return (
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        f'{"".join(elements)}'
        f'</svg>'
    )


def _ev_histogram(evs: List[float], width: int = 480, height: int = 90) -> str:
    """Log-scale bucket histogram of EV distribution."""
    if not evs:
        return ""
    buckets_def = [(0, 50), (50, 100), (100, 200), (200, 400), (400, 750), (750, 1500), (1500, 5000), (5000, 1e9)]
    bucket_counts = [sum(1 for ev in evs if lo <= ev < hi) for lo, hi in buckets_def]
    max_n = max(bucket_counts) or 1
    bar_w = (width - 20) // len(bucket_counts)
    elements = []
    for i, (cnt, (lo, hi)) in enumerate(zip(bucket_counts, buckets_def)):
        bh = max(0, int(cnt / max_n * (height - 20)))
        bx = 10 + i * bar_w
        by = height - 12 - bh
        color = "#475569" if lo < 100 else ("#2fb3ad" if lo < 300 else ("#b8732a" if lo < 1000 else "#b5321e"))
        elements.append(f'<rect x="{bx}" y="{by}" width="{max(1,bar_w-2)}" height="{bh}" fill="{color}" opacity="0.8"/>')
        label = f"${int(lo)}M" if lo < 1000 else f"${int(lo)//1000}B"
        elements.append(f'<text x="{bx+bar_w//2}" y="{height-1}" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="6.5" fill="#475569">{label}</text>')
        if bh > 0:
            elements.append(f'<text x="{bx+bar_w//2}" y="{by-2}" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="7" fill="#465366">{cnt}</text>')
    return (
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        f'{"".join(elements)}'
        f'</svg>'
    )


def render_size_intel() -> str:
    from rcm_mc.ui._chartis_kit import chartis_shell, ck_section_header, ck_kpi_block
    from rcm_mc.data_public.size_analytics import compute_size_analytics

    corpus = _load_corpus()
    profile = compute_size_analytics(corpus)

    corr = profile.size_moic_corr
    best_bucket = max(profile.buckets, key=lambda b: b.moic_p50, default=None)

    kpis = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Deals w/ EV", f'<span class="mn">{profile.n_total}</span>', "have EV data")
        + ck_kpi_block("EV P25", f'<span class="mn">${profile.ev_p25:.0f}M</span>', "25th percentile")
        + ck_kpi_block("EV P50", f'<span class="mn">${profile.ev_p50:.0f}M</span>', "median deal size")
        + ck_kpi_block("EV P75", f'<span class="mn">${profile.ev_p75:.0f}M</span>', "75th percentile")
        + ck_kpi_block("Size↔MOIC Corr",
                       f'<span class="mn" style="color:{"#22c55e" if corr>0.1 else "#b5321e" if corr<-0.1 else "#b8732a"}">{corr:+.2f}</span>',
                       "Spearman ρ")
        + (ck_kpi_block("Best Size Bucket", f'<span class="mn">{_html.escape(best_bucket.label)}</span>', f'P50 {best_bucket.moic_p50:.2f}x') if best_bucket else "")
        + '</div>'
    )

    scatter = _log_scale_scatter(profile.ev_moic_points)
    evs_only = [p[0] for p in profile.ev_moic_points]
    hist = _ev_histogram(evs_only)

    scatter_panel = f"""
<div class="ck-panel">
  <div class="ck-panel-title">EV vs MOIC — log scale · {profile.n_total} deals</div>
  <div style="padding:12px 16px;">
    {scatter}
    <div style="margin-top:6px;font-size:9px;color:#475569;">
      x-axis log-scale · Green ≥3.0× · Blue ≥2.0× · Amber ≥1.5× · Red &lt;1.5× · Hover for deal
    </div>
  </div>
</div>"""

    hist_panel = f"""
<div class="ck-panel">
  <div class="ck-panel-title">EV Distribution Histogram</div>
  <div style="padding:12px 16px;">
    {hist}
    <div style="margin-top:6px;font-size:9px;color:#475569;">
      Gray &lt;$100M · Blue $100–300M · Amber $300M–$1B · Red &gt;$1B
    </div>
  </div>
</div>"""

    # Size bucket table
    bucket_rows = []
    for i, b in enumerate(profile.buckets):
        stripe = ' style="background:#faf7f0"' if i % 2 == 1 else ""
        mc = _moic_color(b.moic_p50)
        optimal_badge = f'<span style="margin-left:4px;font-size:8px;color:#22c55e;font-family:var(--ck-mono);">★</span>' if best_bucket and b.label == best_bucket.label else ""
        hi_label = f"${b.ev_range[1]:.0f}M" if b.ev_range[1] < 1000 else ("$1B+" if b.ev_range[1] < 1e6 else "—")
        lo_label = f"${b.ev_range[0]:.0f}M" if b.ev_range[0] < 1000 else f"${int(b.ev_range[0])//1000}B"
        bucket_rows.append(f"""<tr{stripe}>
  <td style="padding:5px 8px;">
    <span style="display:inline-block;width:8px;height:8px;background:{b.color};border-radius:1px;margin-right:4px;vertical-align:middle;"></span>
    <span style="font-size:10.5px;">{_html.escape(b.label)}{optimal_badge}</span>
  </td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-size:9.5px;color:#7a8699;">{lo_label}–{hi_label}</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{b.n_deals}</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;color:#7a8699;">${b.avg_ev_mm:.0f}M</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;color:#7a8699;">{b.moic_p25:.2f}x</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;color:{mc};font-weight:500;">{b.moic_p50:.2f}x</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;color:#7a8699;">{b.moic_p75:.2f}x</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{b.irr_p50*100:.1f}%</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{b.avg_hold:.1f}y</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;
      color:{'#b5321e' if b.loss_rate>0.2 else '#b8732a' if b.loss_rate>0.1 else '#22c55e'};">{b.loss_rate*100:.1f}%</td>
</tr>""")

    bucket_table = f"""
<div class="ck-panel">
  <div class="ck-panel-title">Performance by Deal Size Bucket</div>
  <div class="ck-table-wrap">
    <table class="ck-table" style="width:100%;">
      <thead>
        <tr>
          <th style="padding:5px 8px;color:#7a8699;">Bucket</th>
          <th style="padding:5px 8px;color:#7a8699;">EV Range</th>
          <th style="padding:5px 8px;color:#7a8699;text-align:right;">Deals</th>
          <th style="padding:5px 8px;color:#7a8699;text-align:right;">Avg EV</th>
          <th style="padding:5px 8px;color:#7a8699;text-align:right;">P25 MOIC</th>
          <th style="padding:5px 8px;color:#7a8699;text-align:right;">P50 MOIC</th>
          <th style="padding:5px 8px;color:#7a8699;text-align:right;">P75 MOIC</th>
          <th style="padding:5px 8px;color:#7a8699;text-align:right;">P50 IRR</th>
          <th style="padding:5px 8px;color:#7a8699;text-align:right;">Avg Hold</th>
          <th style="padding:5px 8px;color:#7a8699;text-align:right;">Loss %</th>
        </tr>
      </thead>
      <tbody>{''.join(bucket_rows)}</tbody>
    </table>
  </div>
  <div style="padding:6px 16px 10px;font-size:9px;color:#475569;">
    ★ = highest P50 MOIC bucket · Loss = MOIC &lt;1.0 · ρ(size,MOIC)={corr:+.2f}
  </div>
</div>"""

    body = (
        kpis
        + ck_section_header("SIZE ANALYSIS", "EV distribution and returns by deal size")
        + f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:0;">{scatter_panel}{hist_panel}</div>'
        + ck_section_header("SIZE BUCKETS", "P25/P50/P75 MOIC by enterprise value range")
        + bucket_table
    )

    return chartis_shell(
        body,
        title="Size Intelligence",
        active_nav="/size-intel",
        subtitle=(
            f"{profile.n_total} deals · "
            f"P50 EV ${profile.ev_p50:.0f}M · "
            f"ρ(size,MOIC)={corr:+.2f}"
            + (f" · best {best_bucket.label}" if best_bucket else "")
        ),
    )
