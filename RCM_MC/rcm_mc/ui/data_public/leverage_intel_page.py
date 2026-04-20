"""Leverage Intelligence page — /leverage-intel.

Corpus-calibrated capital structure analysis:
- Leverage distribution histogram (direct + proxied from EV/EBITDA)
- MOIC vs leverage scatter
- P25/P50/P75 MOIC by leverage bucket
- Optimal leverage range from realized returns
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


def _moic_color(m: float) -> str:
    if m >= 3.0: return "#22c55e"
    if m >= 2.0: return "#2fb3ad"
    if m >= 1.5: return "#b8732a"
    return "#b5321e"


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def _leverage_histogram(points: List[Any], width: int = 440, height: int = 100) -> str:
    """Histogram of leverage_pct in 5% buckets."""
    if not points:
        return ""
    n_buckets = 20  # 5% each from 0-100%
    buckets_d = [0] * n_buckets   # direct
    buckets_p = [0] * n_buckets   # proxied
    for pt in points:
        idx = min(n_buckets - 1, int(pt.leverage_pct * n_buckets))
        if pt.is_direct:
            buckets_d[idx] += 1
        else:
            buckets_p[idx] += 1
    max_n = max(buckets_d[i] + buckets_p[i] for i in range(n_buckets)) or 1
    bar_w = (width - 20) // n_buckets
    elements = []
    for i in range(n_buckets):
        bx = 10 + i * bar_w
        nd = buckets_d[i]; np_ = buckets_p[i]; nt = nd + np_
        bh_total = max(0, int(nt / max_n * (height - 20)))
        bh_d = int(nd / max(1, nt) * bh_total)
        bh_p = bh_total - bh_d
        by = height - 12 - bh_total
        if bh_p > 0:
            elements.append(f'<rect x="{bx}" y="{by}" width="{max(1,bar_w-1)}" height="{bh_p}" fill="#1d3a5c" opacity="0.7"/>')
        if bh_d > 0:
            elements.append(f'<rect x="{bx}" y="{by+bh_p}" width="{max(1,bar_w-1)}" height="{bh_d}" fill="#2fb3ad" opacity="0.9"/>')
        if i % 4 == 0:
            elements.append(f'<text x="{bx+bar_w//2}" y="{height-1}" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="7" fill="#475569">{i*5}%</text>')
    return (
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        f'{"".join(elements)}'
        f'</svg>'
    )


def _scatter_svg(points: List[Any], width: int = 440, height: int = 240) -> str:
    """Leverage% (x) vs MOIC (y) scatter."""
    if not points:
        return ""
    margin = {"l": 40, "r": 10, "t": 10, "b": 30}
    W = width - margin["l"] - margin["r"]
    H = height - margin["t"] - margin["b"]
    max_moic = max(p.moic for p in points)
    max_moic = max(max_moic, 4.0)

    def sx(lev): return int(margin["l"] + lev * W)
    def sy(m): return int(margin["t"] + (1 - m / max_moic) * H)

    elements = []
    for pct in (0.3, 0.45, 0.6, 0.7, 0.85):
        gx = sx(pct)
        elements.append(f'<line x1="{gx}" y1="{margin["t"]}" x2="{gx}" y2="{margin["t"]+H}" stroke="#d6cfc3" stroke-width="0.8"/>')
        elements.append(f'<text x="{gx}" y="{margin["t"]+H+12}" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="8" fill="#475569">{pct*100:.0f}%</text>')
    for m in (1.0, 2.0, 3.0, 4.0):
        if m > max_moic: break
        gy = sy(m)
        elements.append(f'<line x1="{margin["l"]}" y1="{gy}" x2="{margin["l"]+W}" y2="{gy}" stroke="#d6cfc3" stroke-width="0.8"/>')
        elements.append(f'<text x="{margin["l"]-3}" y="{gy+3}" text-anchor="end" font-family="JetBrains Mono,monospace" font-size="8" fill="#475569">{m:.0f}x</text>')

    for p in points:
        cx = sx(p.leverage_pct); cy = sy(p.moic)
        color = _moic_color(p.moic)
        shape = "circle" if p.is_direct else "rect"
        if p.is_direct:
            elements.append(f'<circle cx="{cx}" cy="{cy}" r="3.5" fill="{color}" opacity="0.85"><title>{_html.escape(p.deal_name[:40])} · lev {p.leverage_pct*100:.0f}% · {p.moic:.2f}x (direct)</title></circle>')
        else:
            elements.append(f'<rect x="{cx-2}" y="{cy-2}" width="4" height="4" fill="{color}" opacity="0.5"><title>{_html.escape(p.deal_name[:40])} · lev {p.leverage_pct*100:.0f}% · {p.moic:.2f}x (proxy)</title></rect>')

    elements.append(f'<text x="{margin["l"]+W//2}" y="{height-2}" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="9" fill="#7a8699">Leverage %</text>')
    elements.append(f'<text x="9" y="{margin["t"]+H//2}" text-anchor="middle" transform="rotate(-90,9,{margin["t"]+H//2})" font-family="JetBrains Mono,monospace" font-size="9" fill="#7a8699">Realized MOIC</text>')
    return (
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        f'{"".join(elements)}'
        f'</svg>'
    )


def _bucket_chart(buckets: List[Any], width: int = 300, height: int = 100) -> str:
    """P50 MOIC by leverage bucket — grouped bar."""
    if not buckets:
        return ""
    max_moic = max(b.moic_p75 for b in buckets)
    max_moic = max(max_moic, 3.0)
    bar_w = (width - 20) // len(buckets)
    elements = []
    for i, b in enumerate(buckets):
        bx = 10 + i * bar_w
        bh = max(2, int(b.moic_p50 / max_moic * (height - 20)))
        by = height - 12 - bh
        elements.append(f'<rect x="{bx}" y="{by}" width="{max(1,bar_w-4)}" height="{bh}" fill="{b.color}" opacity="0.85"/>')
        elements.append(f'<text x="{bx+bar_w//2-2}" y="{height-1}" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="8" fill="#7a8699">{b.label[:4]}</text>')
        elements.append(f'<text x="{bx+bar_w//2-2}" y="{by-2}" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="8" fill="{b.color}">{b.moic_p50:.2f}x</text>')
    return (
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        f'{"".join(elements)}'
        f'</svg>'
    )


def render_leverage_intel() -> str:
    from rcm_mc.ui._chartis_kit import chartis_shell, ck_section_header, ck_kpi_block
    from rcm_mc.data_public.leverage_analytics import compute_leverage_analytics

    corpus = _load_corpus()
    profile = compute_leverage_analytics(corpus)

    n_total = profile.n_direct + profile.n_proxied
    corr = profile.lev_moic_corr
    corr_dir = "inverse" if corr < -0.05 else ("positive" if corr > 0.05 else "neutral")

    kpis = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Direct Leverage Data", f'<span class="mn">{profile.n_direct}</span>', "explicit leverage_pct")
        + ck_kpi_block("Proxied (EV/EBITDA)", f'<span class="mn">{profile.n_proxied}</span>', "estimated from EV/EBITDA")
        + ck_kpi_block("Avg Leverage (direct)", f'<span class="mn">{profile.avg_leverage_direct*100:.1f}%</span>', "direct-data deals")
        + ck_kpi_block("Lev↔MOIC Corr",
                       f'<span class="mn" style="color:{"#b5321e" if corr<-0.1 else "#22c55e" if corr>0.1 else "#b8732a"}">{corr:+.2f}</span>',
                       f"{corr_dir} — Spearman ρ")
        + ck_kpi_block("Optimal Bucket", f'<span class="mn" style="font-size:11px;">{_html.escape(profile.optimal_bucket)}</span>', "highest P50 MOIC")
        + '</div>'
    )

    hist = _leverage_histogram(profile.points)
    scatter = _scatter_svg(profile.points)
    bucket_chart = _bucket_chart(profile.buckets)

    hist_panel = f"""
<div class="ck-panel">
  <div class="ck-panel-title">Leverage Distribution — {n_total} deals</div>
  <div style="padding:12px 16px;">
    {hist}
    <div style="margin-top:6px;font-size:9px;color:#475569;">
      Blue = direct leverage_pct · Dark = EV/EBITDA proxy · x-axis = leverage % in 5pp buckets
    </div>
  </div>
</div>"""

    scatter_panel = f"""
<div class="ck-panel">
  <div class="ck-panel-title">Leverage % vs Realized MOIC (ρ={corr:+.2f})</div>
  <div style="padding:12px 16px;">
    {scatter}
    <div style="margin-top:6px;font-size:9px;color:#475569;">
      Circles = direct data · Squares = EV/EBITDA proxy · Hover for deal detail
    </div>
  </div>
</div>"""

    # Bucket table
    bucket_rows = []
    for i, b in enumerate(profile.buckets):
        stripe = ' style="background:#faf7f0"' if i % 2 == 1 else ""
        mc = _moic_color(b.moic_p50)
        optimal_badge = (
            f'<span style="margin-left:4px;font-size:8px;color:#22c55e;font-family:var(--ck-mono);">★ OPTIMAL</span>'
            if b.label == profile.optimal_bucket else ""
        )
        bucket_rows.append(f"""<tr{stripe}>
  <td style="padding:5px 8px;font-size:10.5px;">
    <span style="display:inline-block;width:8px;height:8px;background:{b.color};border-radius:1px;margin-right:4px;vertical-align:middle;"></span>
    {_html.escape(b.label)}{optimal_badge}
  </td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-size:9.5px;color:#7a8699;">{b.lev_range[0]*100:.0f}–{min(100,b.lev_range[1]*100):.0f}%</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{b.n_deals}</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{b.avg_leverage*100:.1f}%</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;color:#7a8699;">{b.moic_p25:.2f}x</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;color:{mc};font-weight:500;">{b.moic_p50:.2f}x</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;color:#7a8699;">{b.moic_p75:.2f}x</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{b.irr_p50*100:.1f}%</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;
      color:{'#b5321e' if b.loss_rate>0.2 else '#b8732a' if b.loss_rate>0.1 else '#22c55e'};">{b.loss_rate*100:.1f}%</td>
  <td style="padding:5px 8px;font-size:9px;color:#7a8699;">{'direct' if b.is_direct else 'proxy'}</td>
</tr>""")

    bucket_table = f"""
<div class="ck-panel">
  <div class="ck-panel-title">MOIC by Leverage Bucket</div>
  <div style="padding:12px 16px;display:grid;grid-template-columns:auto 1fr;gap:16px;align-items:start;">
    <div>{bucket_chart}</div>
    <div class="ck-table-wrap">
      <table class="ck-table" style="width:100%;">
        <thead>
          <tr>
            <th style="padding:5px 8px;color:#7a8699;">Bucket</th>
            <th style="padding:5px 8px;color:#7a8699;">Range</th>
            <th style="padding:5px 8px;color:#7a8699;text-align:right;">Deals</th>
            <th style="padding:5px 8px;color:#7a8699;text-align:right;">Avg Lev</th>
            <th style="padding:5px 8px;color:#7a8699;text-align:right;">P25</th>
            <th style="padding:5px 8px;color:#7a8699;text-align:right;">P50</th>
            <th style="padding:5px 8px;color:#7a8699;text-align:right;">P75</th>
            <th style="padding:5px 8px;color:#7a8699;text-align:right;">P50 IRR</th>
            <th style="padding:5px 8px;color:#7a8699;text-align:right;">Loss %</th>
            <th style="padding:5px 8px;color:#7a8699;">Source</th>
          </tr>
        </thead>
        <tbody>{''.join(bucket_rows)}</tbody>
      </table>
    </div>
  </div>
  <div style="padding:0 16px 10px;font-size:9px;color:#475569;">
    Proxy leverage = 55% × (debt/EBITDA) / (EV/EBITDA) — approximation only
    · Optimal = highest P50 MOIC bucket
    · {profile.n_direct} direct observations · {profile.n_proxied} EV/EBITDA proxies
  </div>
</div>"""

    body = (
        kpis
        + ck_section_header("LEVERAGE DISTRIBUTION", f"{n_total} deals — direct data + EV/EBITDA proxy")
        + f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:0;">{hist_panel}{scatter_panel}</div>'
        + ck_section_header("BUCKET ANALYSIS", "P25/P50/P75 MOIC by leverage regime")
        + bucket_table
    )

    return chartis_shell(
        body,
        title="Leverage Intelligence",
        active_nav="/leverage-intel",
        subtitle=(
            f"{profile.n_direct} direct + {profile.n_proxied} proxied · "
            f"avg direct leverage {profile.avg_leverage_direct*100:.1f}% · "
            f"ρ(lev,MOIC)={corr:+.2f} · optimal: {profile.optimal_bucket}"
        ),
    )
