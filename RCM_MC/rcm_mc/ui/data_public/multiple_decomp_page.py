"""Acquisition Multiple Decomposition page — /multiple-decomp.

Breaks down entry EV/EBITDA into: sector baseline, size adjustment,
payer mix premium, and unexplained premium. Shows historical MOIC
for deals at similar premium levels.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_section_header, ck_kpi_block, ck_fmt_moic,
)


def _waterfall_svg(components: List[Any], total: float, width: int = 640, height: int = 160) -> str:
    """Stacked horizontal bar decomposing EV/EBITDA into components."""
    if not components:
        return ""
    ml, mr, mt, mb = 20, 60, 10, 30
    W = width - ml - mr
    bar_h = 38
    gap = 8
    total_h = (bar_h + gap) * len(components) + mt + mb

    COLORS = {
        "Sector Baseline":     P["accent"],
        "Size Adjustment":     "#0ea5e9",
        "Payer Mix Adjustment": "#8b5cf6",
        "Unexplained Premium": "#f59e0b" if total > 0 else P["negative"],
    }

    lines = [
        f'<svg viewBox="0 0 {width} {total_h}" width="{width}" height="{total_h}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block">'
    ]

    for i, c in enumerate(components):
        y = mt + i * (bar_h + gap)
        pct = abs(c.pct_of_total)
        v = c.value
        bar_w = max(2, int(pct / 100 * W))
        color = COLORS.get(c.label, P["text_dim"])
        # Negative values shown as grey
        if v < 0:
            color = P["negative"]
        bx = ml

        lines.append(
            f'<rect x="{bx}" y="{y}" width="{bar_w}" height="{bar_h}" '
            f'fill="{color}" opacity="0.85" rx="2"/>'
        )
        sign = "+" if v > 0 else ""
        vstr = f"{sign}{v:.1f}×"
        lines.append(
            f'<text x="{bx + bar_w + 6}" y="{y + bar_h//2 + 5}" '
            f'font-size="11" fill="{color}" '
            f'font-family="JetBrains Mono,monospace" font-variant-numeric="tabular-nums">'
            f'{vstr} ({abs(c.pct_of_total):.0f}%)</text>'
        )
        lines.append(
            f'<text x="{bx - 4}" y="{y + bar_h//2 + 5}" '
            f'text-anchor="end" font-size="10" fill="{P["text_dim"]}" '
            f'font-family="Inter,sans-serif">{_html.escape(c.label)}</text>'
        )

    lines.append("</svg>")
    return "\n".join(lines)


def _sector_bench_table(benchmarks: List[Any]) -> str:
    rows = []
    for b in benchmarks:
        ee_html = (
            f'<span class="mn">{b.median_ev_ebitda:.1f}×</span>'
            if b.median_ev_ebitda else "—"
        )
        p25_html = (
            f'<span class="mn" style="color:{P["text_faint"]}">{b.p25_ev_ebitda:.1f}×</span>'
            if b.p25_ev_ebitda else "—"
        )
        p75_html = (
            f'<span class="mn" style="color:{P["text_faint"]}">{b.p75_ev_ebitda:.1f}×</span>'
            if b.p75_ev_ebitda else "—"
        )
        moic_color = (
            P["positive"] if (b.median_moic or 0) >= 3.0
            else P["warning"] if (b.median_moic or 0) >= 2.0
            else P["negative"]
        )
        moic_html = (
            f'<span class="mn" style="color:{moic_color}">{b.median_moic:.2f}×</span>'
            if b.median_moic else "—"
        )
        slope_color = P["positive"] if b.premium_moic_slope > 0 else P["negative"]
        rows.append(
            f"<tr>"
            f"<td>{_html.escape(b.sector)}</td>"
            f"<td class='r mn'>{b.n}</td>"
            f"<td class='r'>{p25_html}</td>"
            f"<td class='r'>{ee_html}</td>"
            f"<td class='r'>{p75_html}</td>"
            f"<td class='r'>{moic_html}</td>"
            f"<td class='r mn' style='color:{slope_color}'>{b.premium_moic_slope:+.3f}</td>"
            f"<td class='r mn'>{b.premium_moic_slope_r2:.3f}</td>"
            f"</tr>"
        )
    return (
        '<table class="ck-table">'
        "<thead><tr>"
        "<th>Sector</th><th class='r'>N</th>"
        "<th class='r'>P25 EV/EBITDA</th><th class='r'>P50 EV/EBITDA</th>"
        "<th class='r'>P75 EV/EBITDA</th><th class='r'>P50 MOIC</th>"
        "<th class='r'>EE→MOIC Slope</th><th class='r'>R²</th>"
        "</tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody>"
        "</table>"
    )


def _peer_table(peers: List[Dict[str, Any]]) -> str:
    rows = []
    for d in peers:
        ev = d.get("ev_mm")
        eb = d.get("ebitda_at_entry_mm")
        ee = float(ev) / float(eb) if ev and eb and float(eb) > 0 else None
        m = None
        for k in ("moic", "realized_moic"):
            v = d.get(k)
            if v is not None:
                try:
                    m = float(v)
                    break
                except (TypeError, ValueError):
                    pass
        moic_color = (
            P["positive"] if (m or 0) >= 3.0
            else P["warning"] if (m or 0) >= 2.0
            else P["negative"] if m else P["text_faint"]
        )
        rows.append(
            f"<tr>"
            f"<td>{_html.escape(d.get('company_name') or d.get('deal_name') or '—')}</td>"
            f"<td>{_html.escape(d.get('sector') or '—')}</td>"
            f"<td class='r mn'>{d.get('year', '—')}</td>"
            f"<td class='r mn'>{'$' + str(int(float(ev))) + 'M' if ev else '—'}</td>"
            f"<td class='r mn'>{f'{ee:.1f}×' if ee else '—'}</td>"
            f"<td class='r mn' style='color:{moic_color}'>"
            f"{f'{m:.2f}×' if m else '—'}</td>"
            f"</tr>"
        )
    if not rows:
        return '<p class="ck-empty">No comparable deals found.</p>'
    return (
        '<table class="ck-table">'
        "<thead><tr>"
        "<th>Company</th><th>Sector</th><th class='r'>Yr</th>"
        "<th class='r'>EV</th><th class='r'>EV/EBITDA</th><th class='r'>MOIC</th>"
        "</tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody>"
        "</table>"
    )


def _input_form(params: Dict[str, str]) -> str:
    sector = _html.escape(params.get("sector", ""))
    ev_mm = params.get("ev_mm", "")
    ev_ebitda = params.get("ev_ebitda", "12.0")
    comm_pct = params.get("comm_pct", "")
    return f"""
<form method="get" action="/multiple-decomp" class="ck-form">
  <div class="ck-form-row">
    <div class="ck-form-group">
      <label class="ck-label">Sector</label>
      <input type="text" name="sector" class="ck-input w200"
        placeholder="e.g. Behavioral Health" value="{sector}">
    </div>
    <div class="ck-form-group">
      <label class="ck-label">Entry EV ($M)</label>
      <input type="number" name="ev_mm" class="ck-input w130"
        placeholder="e.g. 300" value="{_html.escape(ev_mm)}" step="10">
    </div>
    <div class="ck-form-group">
      <label class="ck-label">Entry EV/EBITDA (×) *</label>
      <input type="number" name="ev_ebitda" class="ck-input w130"
        value="{_html.escape(ev_ebitda)}" step="0.5" min="3" max="40" required>
    </div>
    <div class="ck-form-group">
      <label class="ck-label">Commercial % (0–1)</label>
      <input type="number" name="comm_pct" class="ck-input w130"
        placeholder="e.g. 0.65" value="{_html.escape(comm_pct)}" step="0.05" min="0" max="1">
    </div>
    <div class="ck-form-group" style="align-self:flex-end">
      <button type="submit" class="ck-btn">Decompose</button>
    </div>
  </div>
</form>"""


def render_multiple_decomp(params: Dict[str, str]) -> str:
    from rcm_mc.data_public.multiple_decomp import compute_multiple_decomp

    sector = params.get("sector", "")
    ev_mm: Optional[float] = None
    comm_pct: Optional[float] = None
    try:
        ev_ebitda = float(params.get("ev_ebitda") or "12.0")
    except (TypeError, ValueError):
        ev_ebitda = 12.0
    try:
        if params.get("ev_mm"):
            ev_mm = float(params["ev_mm"])
    except (TypeError, ValueError):
        pass
    try:
        if params.get("comm_pct"):
            comm_pct = float(params["comm_pct"])
    except (TypeError, ValueError):
        pass

    result = compute_multiple_decomp(
        sector=sector,
        ev_mm=ev_mm,
        ev_ebitda=ev_ebitda,
        comm_pct=comm_pct,
    )

    # Signal: premium vs. expected
    unexp = result.unexplained_premium
    if unexp > 3.0:
        signal_html = '<span class="mn" style="color:#ef4444">HIGH PREMIUM — caution</span>'
    elif unexp > 1.0:
        signal_html = f'<span class="mn" style="color:#f59e0b">+{unexp:.1f}× above fundamentals</span>'
    elif unexp < -1.0:
        signal_html = f'<span class="mn pos">Discount: {unexp:.1f}× below fundamentals</span>'
    else:
        signal_html = '<span class="mn" style="color:#94a3b8">Inline with fundamentals</span>'

    kpi_grid = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block(
            "Entry EV/EBITDA",
            f'<span class="mn">{ev_ebitda:.1f}×</span>',
            f"sector: {_html.escape(sector or 'all')}",
        )
        + ck_kpi_block(
            "Sector Baseline",
            f'<span class="mn">{result.sector_baseline:.1f}×</span>',
            f"n={result.sector_n} peers",
        )
        + ck_kpi_block(
            "Unexplained Premium",
            f'<span class="mn">{result.unexplained_premium:+.1f}×</span>',
            signal_html,
        )
        + ck_kpi_block(
            "Similar Premium P50 MOIC",
            ck_fmt_moic(result.similar_premium_moic_p50),
            "deals at similar premium",
        )
        + ck_kpi_block(
            "High Premium P50 MOIC",
            ck_fmt_moic(result.high_premium_moic_p50),
            "entry >3× above sector median",
        )
        + "</div>"
    )

    chart = _waterfall_svg(result.components, ev_ebitda)

    body = f"""
{_input_form(params)}
{kpi_grid}
{ck_section_header("Multiple Decomposition", f"Entry {ev_ebitda:.1f}× broken into components")}
<div style="overflow-x:auto;margin-bottom:24px">{chart}</div>
{ck_section_header("Sector Benchmarks", "Corpus EV/EBITDA ranges and premium-MOIC relationship")}
<div style="overflow-x:auto;margin-bottom:24px">{_sector_bench_table(result.sector_benchmarks)}</div>
{ck_section_header("Comparable Deals", "Closest matches by multiple and size")}
<div style="overflow-x:auto">{_peer_table(result.peer_deals)}</div>
"""

    extra_css = """
.ck-form { margin-bottom: 24px; }
.ck-form-row { display:flex; flex-wrap:wrap; gap:12px; align-items:flex-start; }
.ck-form-group { display:flex; flex-direction:column; gap:4px; }
.ck-label { font-size:11px; color:var(--ck-text-dim); text-transform:uppercase; letter-spacing:.06em; }
.ck-input {
  background:var(--ck-panel-alt); border:1px solid var(--ck-border);
  color:var(--ck-text); padding:6px 10px; font-size:12px;
  font-family:'JetBrains Mono',monospace; border-radius:3px;
}
.w200 { width:200px; }
.w130 { width:130px; }
.ck-input:focus { outline:1px solid var(--ck-accent); }
.ck-btn {
  background:var(--ck-accent); color:#fff; border:none; padding:7px 18px;
  font-size:12px; border-radius:3px; cursor:pointer; letter-spacing:.04em;
}
.ck-btn:hover { filter:brightness(1.15); }
"""

    return chartis_shell(
        body=body,
        title="Acquisition Multiple Decomposition",
        active_nav="/multiple-decomp",
        subtitle="Entry EV/EBITDA decomposed: sector baseline, size, payer mix, unexplained premium",
        extra_css=extra_css,
    )
