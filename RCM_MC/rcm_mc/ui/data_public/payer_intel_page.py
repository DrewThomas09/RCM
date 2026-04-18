"""Payer Intelligence page — /payer-intel.

Corpus-calibrated payer mix analysis:
- Corpus-average payer mix donut (SVG)
- P50 MOIC by commercial % regime
- Commercial% vs MOIC scatter
- Regime table with P25/P50/P75 MOIC, IRR, loss rate
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
    if m >= 2.0: return "#3b82f6"
    if m >= 1.5: return "#f59e0b"
    return "#ef4444"


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def _payer_pie_svg(comm: float, medicare: float, medicaid: float, self_pay: float,
                   size: int = 120) -> str:
    """SVG pie chart for payer mix."""
    cx = cy = size // 2
    r = size // 2 - 4
    slices = [
        (comm, "#3b82f6", "Commercial"),
        (medicare, "#22c55e", "Medicare"),
        (medicaid, "#f59e0b", "Medicaid"),
        (self_pay, "#64748b", "Self-Pay"),
    ]
    total = sum(v for v, _, _ in slices) or 1.0
    elements = []
    angle = -math.pi / 2
    for val, color, label in slices:
        sweep = val / total * 2 * math.pi
        if sweep < 0.001:
            continue
        x1 = cx + r * math.cos(angle)
        y1 = cy + r * math.sin(angle)
        x2 = cx + r * math.cos(angle + sweep)
        y2 = cy + r * math.sin(angle + sweep)
        large = 1 if sweep > math.pi else 0
        elements.append(
            f'<path d="M{cx},{cy} L{x1:.1f},{y1:.1f} A{r},{r} 0 {large},1 {x2:.1f},{y2:.1f} Z" '
            f'fill="{color}" opacity="0.9">'
            f'<title>{label}: {val*100:.1f}%</title></path>'
        )
        angle += sweep
    # inner circle (donut)
    ir = r * 0.45
    elements.append(f'<circle cx="{cx}" cy="{cy}" r="{ir:.0f}" fill="#0a0e17"/>')
    return (
        f'<svg width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">'
        f'{"".join(elements)}'
        f'</svg>'
    )


def _payer_legend(comm: float, medicare: float, medicaid: float, self_pay: float) -> str:
    items = [
        ("#3b82f6", "Commercial", comm),
        ("#22c55e", "Medicare",   medicare),
        ("#f59e0b", "Medicaid",   medicaid),
        ("#64748b", "Self-Pay",   self_pay),
    ]
    rows = []
    for color, label, val in items:
        rows.append(
            f'<div style="display:flex;align-items:center;gap:6px;margin:3px 0;">'
            f'<div style="width:10px;height:10px;background:{color};border-radius:1px;flex-shrink:0;"></div>'
            f'<div style="font-size:10px;color:#94a3b8;min-width:90px;">{label}</div>'
            f'<div style="font-family:var(--ck-mono);font-variant-numeric:tabular-nums;'
            f'font-size:10px;color:#e2e8f0;">{val*100:.1f}%</div>'
            f'</div>'
        )
    return "".join(rows)


def _scatter_svg(corpus: List[Dict[str, Any]], width: int = 440, height: int = 240) -> str:
    """Commercial % (x) vs MOIC (y) scatter."""
    margin = {"l": 40, "r": 10, "t": 10, "b": 30}
    W = width - margin["l"] - margin["r"]
    H = height - margin["t"] - margin["b"]

    deals_with_data = [
        d for d in corpus
        if isinstance(d.get("payer_mix"), dict) and d.get("realized_moic") is not None
    ]
    if not deals_with_data:
        return ""

    max_moic = max(float(d["realized_moic"]) for d in deals_with_data)
    max_moic = max(max_moic, 4.0)

    def sx(c): return int(margin["l"] + c * W)
    def sy(m): return int(margin["t"] + (1 - m / max_moic) * H)

    elements = []
    # grid
    for pct in (0.2, 0.4, 0.6, 0.8):
        gx = sx(pct)
        elements.append(f'<line x1="{gx}" y1="{margin["t"]}" x2="{gx}" y2="{margin["t"]+H}" stroke="#1e293b" stroke-width="0.8"/>')
        elements.append(f'<text x="{gx}" y="{margin["t"]+H+12}" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="8" fill="#475569">{pct*100:.0f}%</text>')
    for m in (1.0, 2.0, 3.0, 4.0):
        if m > max_moic: break
        gy = sy(m)
        elements.append(f'<line x1="{margin["l"]}" y1="{gy}" x2="{margin["l"]+W}" y2="{gy}" stroke="#1e293b" stroke-width="0.8"/>')
        elements.append(f'<text x="{margin["l"]-3}" y="{gy+3}" text-anchor="end" font-family="JetBrains Mono,monospace" font-size="8" fill="#475569">{m:.0f}x</text>')

    for d in deals_with_data:
        comm = float(d["payer_mix"].get("commercial", 0) or 0)
        moic = float(d["realized_moic"])
        cx = sx(comm); cy = sy(moic)
        color = _moic_color(moic)
        elements.append(
            f'<circle cx="{cx}" cy="{cy}" r="3" fill="{color}" opacity="0.6">'
            f'<title>{_html.escape(d.get("deal_name","")[:40])} · {comm*100:.0f}% comm · {moic:.2f}x</title>'
            f'</circle>'
        )

    # axis labels
    elements.append(f'<text x="{margin["l"]+W//2}" y="{height-2}" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="9" fill="#64748b">Commercial %</text>')
    elements.append(
        f'<text x="9" y="{margin["t"]+H//2}" text-anchor="middle" transform="rotate(-90,9,{margin["t"]+H//2})" '
        f'font-family="JetBrains Mono,monospace" font-size="9" fill="#64748b">Realized MOIC</text>'
    )
    return (
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        f'{"".join(elements)}'
        f'</svg>'
    )


def _regime_moic_bar(p25: float, p50: float, p75: float, width: int = 100) -> str:
    max_m = 6.0
    def x(m): return int(min(width, max(0, m / max_m * width)))
    x25, x50, x75 = x(p25), x(p50), x(p75)
    color = _moic_color(p50)
    return (
        f'<svg width="{width}" height="12" xmlns="http://www.w3.org/2000/svg">'
        f'<rect x="0" y="4" width="{width}" height="4" fill="#1e293b"/>'
        f'<rect x="{x25}" y="2" width="{max(1,x75-x25)}" height="8" fill="#1d3a5c"/>'
        f'<line x1="{x50}" y1="0" x2="{x50}" y2="12" stroke="{color}" stroke-width="2"/>'
        f'</svg>'
    )


def render_payer_intel() -> str:
    from rcm_mc.ui._chartis_kit import chartis_shell, ck_section_header, ck_kpi_block
    from rcm_mc.data_public.payer_intelligence import compute_payer_intelligence

    corpus = _load_corpus()
    profile = compute_payer_intelligence(corpus)

    n_with_payer = sum(1 for d in corpus if d.get("payer_mix"))
    comm_corr = profile.commercial_moic_corr
    maid_corr = profile.medicaid_moic_corr

    kpis = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Deals w/ Payer Mix", f'<span class="mn">{n_with_payer}</span>', f"of {len(corpus)} corpus")
        + ck_kpi_block("Avg Commercial %", f'<span class="mn">{profile.avg_commercial*100:.1f}%</span>', "corpus-weighted")
        + ck_kpi_block("Avg Medicare %",   f'<span class="mn">{profile.avg_medicare*100:.1f}%</span>', "corpus-weighted")
        + ck_kpi_block("Avg Medicaid %",   f'<span class="mn">{profile.avg_medicaid*100:.1f}%</span>', "corpus-weighted")
        + ck_kpi_block("Comm↔MOIC Corr",
                       f'<span class="mn" style="color:{"#22c55e" if comm_corr>0.1 else "#f59e0b" if comm_corr>0 else "#ef4444"}">'
                       f'{comm_corr:+.2f}</span>', "Spearman rank")
        + '</div>'
    )

    # Pie + legend panel
    pie = _payer_pie_svg(profile.avg_commercial, profile.avg_medicare, profile.avg_medicaid, profile.avg_self_pay, 130)
    legend = _payer_legend(profile.avg_commercial, profile.avg_medicare, profile.avg_medicaid, profile.avg_self_pay)
    mix_panel = f"""
<div class="ck-panel">
  <div class="ck-panel-title">Corpus-Average Payer Mix</div>
  <div style="padding:12px 16px;display:flex;align-items:center;gap:24px;">
    {pie}
    <div>
      {legend}
      <div style="margin-top:8px;font-size:9px;color:#475569;">
        Hover slices for exact %. Based on {n_with_payer:,} deals with payer mix data.
      </div>
    </div>
  </div>
</div>"""

    # Scatter panel
    scatter = _scatter_svg(corpus)
    corr_direction = "positive" if comm_corr > 0.05 else ("negative" if comm_corr < -0.05 else "neutral")
    corr_interp = f"{'Higher' if comm_corr > 0.05 else 'Lower' if comm_corr < -0.05 else 'No clear'} commercial → higher MOIC (ρ={comm_corr:+.2f})"
    scatter_panel = f"""
<div class="ck-panel">
  <div class="ck-panel-title">Commercial % vs Realized MOIC — {n_with_payer} deals</div>
  <div style="padding:12px 16px;">
    {scatter}
    <div style="margin-top:6px;font-size:9px;color:#475569;">
      {corr_interp} · Green ≥3.0× · Blue ≥2.0× · Amber ≥1.5× · Red &lt;1.5×
    </div>
  </div>
</div>"""

    # Regime table
    regime_rows = []
    for i, r in enumerate(profile.regime_stats):
        stripe = ' style="background:#0f172a"' if i % 2 == 1 else ""
        mc = _moic_color(r.moic_p50)
        regime_rows.append(f"""<tr{stripe}>
  <td style="padding:5px 8px;font-size:10.5px;">{_html.escape(r.regime)}</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-size:9.5px;color:#64748b;">{r.commercial_range[0]*100:.0f}–{min(100,r.commercial_range[1]*100):.0f}%</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{r.n_deals}</td>
  <td style="padding:5px 8px;text-align:center;">{_regime_moic_bar(r.moic_p25, r.moic_p50, r.moic_p75)}</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;color:#64748b;">{r.moic_p25:.2f}x</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;color:{mc};font-weight:500;">{r.moic_p50:.2f}x</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;color:#64748b;">{r.moic_p75:.2f}x</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{r.irr_p50*100:.1f}%</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;
      color:{'#ef4444' if r.loss_rate>0.2 else '#f59e0b' if r.loss_rate>0.1 else '#22c55e'};">{r.loss_rate*100:.1f}%</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{r.avg_commercial_pct*100:.1f}%</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{r.avg_medicare_pct*100:.1f}%</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;">{r.avg_medicaid_pct*100:.1f}%</td>
</tr>""")

    regime_table = f"""
<div class="ck-panel">
  <div class="ck-panel-title">Performance by Payer Regime</div>
  <div class="ck-table-wrap">
    <table class="ck-table" style="width:100%;">
      <thead>
        <tr>
          <th style="padding:5px 8px;color:#64748b;text-align:left;">Regime</th>
          <th style="padding:5px 8px;color:#64748b;">Range</th>
          <th style="padding:5px 8px;color:#64748b;text-align:right;">Deals</th>
          <th style="padding:5px 8px;color:#64748b;min-width:110px;">MOIC Range</th>
          <th style="padding:5px 8px;color:#64748b;text-align:right;">P25</th>
          <th style="padding:5px 8px;color:#64748b;text-align:right;">P50</th>
          <th style="padding:5px 8px;color:#64748b;text-align:right;">P75</th>
          <th style="padding:5px 8px;color:#64748b;text-align:right;">P50 IRR</th>
          <th style="padding:5px 8px;color:#64748b;text-align:right;">Loss %</th>
          <th style="padding:5px 8px;color:#64748b;text-align:right;">Avg Comm%</th>
          <th style="padding:5px 8px;color:#64748b;text-align:right;">Avg Med%</th>
          <th style="padding:5px 8px;color:#64748b;text-align:right;">Avg Maid%</th>
        </tr>
      </thead>
      <tbody>{''.join(regime_rows)}</tbody>
    </table>
  </div>
  <div style="padding:6px 16px 10px;font-size:9px;color:#475569;">
    Medicaid↔MOIC ρ={maid_corr:+.2f} · Range bar: box=P25–P75, line=P50 · Loss = MOIC &lt;1.0
  </div>
</div>"""

    body = (
        kpis
        + ck_section_header("PAYER MIX", "corpus-average composition and return correlation")
        + f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:0;">{mix_panel}{scatter_panel}</div>'
        + ck_section_header("PAYER REGIME ANALYSIS", "P25/P50/P75 MOIC by commercial % bucket")
        + regime_table
    )

    return chartis_shell(
        body,
        title="Payer Intelligence",
        active_nav="/payer-intel",
        subtitle=(
            f"{n_with_payer} deals · "
            f"avg commercial {profile.avg_commercial*100:.1f}% · "
            f"comm↔MOIC ρ={comm_corr:+.2f} · "
            f"{len(profile.regime_stats)} regimes"
        ),
    )
