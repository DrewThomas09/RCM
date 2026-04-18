"""Capital Efficiency page — /capital-efficiency.

MOIC per turn of entry multiple, IRR density, and value creation rate
by sector, size, payer regime, and vintage. Identifies highest-return-
density deal profiles from the corpus.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_section_header, ck_kpi_block, ck_fmt_moic,
)


def _eff_color(v: Optional[float], corpus_p50: float) -> str:
    if v is None:
        return P["text_faint"]
    if v >= corpus_p50 * 1.3:
        return P["positive"]
    if v >= corpus_p50 * 0.8:
        return P["text"]
    return P["warning"]


def _bar_chart_svg(
    dims: List[Any],
    value_key: str,
    title: str,
    width: int = 580,
    height: int = 220,
    fmt: str = ".3f",
) -> str:
    """Horizontal bar chart for a dimension breakdown."""
    if not dims:
        return ""
    ml, mr, mt, mb = 110, 50, 24, 20
    W = width - ml - mr
    H = height - mt - mb

    vals = [getattr(d, value_key) for d in dims if getattr(d, value_key) is not None]
    if not vals:
        return ""
    max_v = max(vals) * 1.15 or 1.0
    bar_h = max(12, H // len(dims) - 4)
    row_h = H // len(dims)

    def px(v: float) -> int:
        return int(ml + v / max_v * W)

    def py(i: int) -> int:
        return mt + i * row_h + (row_h - bar_h) // 2

    lines = [
        f'<svg viewBox="0 0 {width} {height + 10}" width="{width}" height="{height + 10}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block">'
    ]

    # Title
    lines.append(
        f'<text x="{ml}" y="14" font-size="10" fill="{P["text_dim"]}" '
        f'font-family="Inter,sans-serif" font-weight="600">'
        f'{_html.escape(title)}</text>'
    )

    # Grid
    for gv in [0.1, 0.2, 0.3, 0.4]:
        if gv > max_v:
            break
        x = px(gv)
        lines.append(
            f'<line x1="{x}" y1="{mt}" x2="{x}" y2="{mt+H}" '
            f'stroke="{P["border"]}" stroke-width="1"/>'
        )

    for i, d in enumerate(dims):
        v = getattr(d, value_key)
        if v is None:
            continue
        y = py(i)
        bar_w = max(2, px(v) - ml)
        color = P["positive"] if i == 0 else P["accent"] if i < 3 else P["text_faint"]
        lines.append(
            f'<rect x="{ml}" y="{y}" width="{bar_w}" height="{bar_h}" '
            f'fill="{color}" opacity="0.8" rx="2"/>'
        )
        lines.append(
            f'<text x="{ml - 4}" y="{y + bar_h//2 + 4}" '
            f'text-anchor="end" font-size="9" fill="{P["text_dim"]}" '
            f'font-family="Inter,sans-serif">'
            f'{_html.escape(str(d.label)[:18])}</text>'
        )
        label = format(v, fmt) + ("×" if "moic" in value_key.lower() else "")
        lines.append(
            f'<text x="{ml + bar_w + 4}" y="{y + bar_h//2 + 4}" '
            f'font-size="9" fill="{color}" '
            f'font-family="JetBrains Mono,monospace" font-variant-numeric="tabular-nums">'
            f'{label}</text>'
        )

    lines.append("</svg>")
    return "\n".join(lines)


def _dim_table(dims: List[Any], corpus_p50: float) -> str:
    rows = []
    for d in dims:
        me_color = _eff_color(d.moic_eff_p50, corpus_p50)
        me_html = (
            f'<span class="mn" style="color:{me_color}">{d.moic_eff_p50:.4f}</span>'
            if d.moic_eff_p50 else "—"
        )
        me75_html = (
            f'<span class="mn" style="color:{P["text_dim"]}">{d.moic_eff_p75:.4f}</span>'
            if d.moic_eff_p75 else "—"
        )
        irr_html = (
            f'<span class="mn">{d.irr_density_p50*100:.2f}%/yr</span>'
            if d.irr_density_p50 else "—"
        )
        vc_html = (
            f'<span class="mn">{d.value_creation_p50:.3f}×/yr</span>'
            if d.value_creation_p50 else "—"
        )
        ee_html = (
            f'<span class="mn" style="color:{P["text_faint"]}">{d.avg_ev_ebitda:.1f}×</span>'
            if d.avg_ev_ebitda else "—"
        )
        moic_color = (
            P["positive"] if (d.avg_moic or 0) >= 3.0
            else P["text"] if (d.avg_moic or 0) >= 2.0
            else P["warning"]
        )
        moic_html = (
            f'<span class="mn" style="color:{moic_color}">{d.avg_moic:.2f}×</span>'
            if d.avg_moic else "—"
        )
        rows.append(
            f"<tr>"
            f"<td>{_html.escape(d.label)}</td>"
            f"<td class='r mn'>{d.n}</td>"
            f"<td class='r'>{me_html}</td>"
            f"<td class='r'>{me75_html}</td>"
            f"<td class='r'>{vc_html}</td>"
            f"<td class='r'>{irr_html}</td>"
            f"<td class='r'>{ee_html}</td>"
            f"<td class='r'>{moic_html}</td>"
            f"</tr>"
        )
    return (
        '<table class="ck-table">'
        "<thead><tr>"
        "<th>Segment</th><th class='r'>N</th>"
        "<th class='r'>MOIC Eff. P50</th><th class='r'>MOIC Eff. P75</th>"
        "<th class='r'>VC Rate P50</th><th class='r'>IRR Density P50</th>"
        "<th class='r'>Avg EV/EBITDA</th><th class='r'>Avg MOIC</th>"
        "</tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody>"
        "</table>"
    )


def _top_deals_table(deals: List[Any], label: str, corpus_p50: float) -> str:
    rows = []
    for d in deals:
        me_color = _eff_color(d.moic_efficiency, corpus_p50)
        rows.append(
            f"<tr>"
            f"<td>{_html.escape(d.company_name[:32] or d.source_id)}</td>"
            f"<td>{_html.escape(d.sector[:24])}</td>"
            f"<td class='r mn'>{d.year}</td>"
            f"<td class='r mn'>{f'{d.ev_ebitda:.1f}×' if d.ev_ebitda else '—'}</td>"
            f"<td class='r mn'>{d.moic:.2f}×</td>"
            f"<td class='r mn'>{d.hold_years:.1f}yr</td>"
            f"<td class='r mn' style='color:{me_color}'>{d.moic_efficiency:.4f}</td>"
            f"<td class='r mn'>{d.value_creation:.3f}×/yr</td>"
            f"</tr>"
        )
    return (
        f'<p class="ck-sub-header">{_html.escape(label)}</p>'
        '<table class="ck-table">'
        "<thead><tr>"
        "<th>Company</th><th>Sector</th><th class='r'>Yr</th>"
        "<th class='r'>EV/EBITDA</th><th class='r'>MOIC</th>"
        "<th class='r'>Hold</th><th class='r'>MOIC Eff.</th>"
        "<th class='r'>VC Rate</th>"
        "</tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody>"
        "</table>"
    )


def render_capital_efficiency(params: Dict[str, str]) -> str:
    from rcm_mc.data_public.capital_efficiency import compute_capital_efficiency

    try:
        min_n = max(2, int(params.get("min_n", "3")))
    except (TypeError, ValueError):
        min_n = 3

    result = compute_capital_efficiency(min_n=min_n)
    cp50 = result.corpus_moic_eff_p50 or 0.25

    kpi_grid = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block(
            "Deals Analyzed",
            f'<span class="mn">{result.total_deals}</span>',
            "with MOIC + hold data",
        )
        + ck_kpi_block(
            "Corpus MOIC Eff. P50",
            f'<span class="mn">{cp50:.4f}</span>',
            "MOIC ÷ EV/EBITDA (P50)",
        )
        + ck_kpi_block(
            "VC Rate P50",
            f'<span class="mn">{(result.corpus_value_creation_p50 or 0):.3f}×/yr</span>',
            "(MOIC−1) ÷ hold years",
        )
        + ck_kpi_block(
            "Top Sector (Eff.)",
            f'<span class="mn">{_html.escape(result.by_sector[0].label if result.by_sector else "—")}</span>',
            f'P50 {result.by_sector[0].moic_eff_p50:.4f}' if result.by_sector and result.by_sector[0].moic_eff_p50 else "",
        )
        + "</div>"
    )

    sec_chart = _bar_chart_svg(
        result.by_sector[:12], "moic_eff_p50", "MOIC Efficiency by Sector"
    )
    size_chart = _bar_chart_svg(
        result.by_size, "moic_eff_p50", "MOIC Efficiency by Deal Size"
    )
    pr_chart = _bar_chart_svg(
        result.by_payer_regime, "moic_eff_p50", "MOIC Efficiency by Payer Regime"
    )

    body = f"""
{kpi_grid}
{ck_section_header("By Sector", "P50 MOIC Efficiency = MOIC ÷ EV/EBITDA")}
<div style="overflow-x:auto;margin-bottom:8px">{sec_chart}</div>
<div style="overflow-x:auto;margin-bottom:24px">{_dim_table(result.by_sector, cp50)}</div>
<div style="display:flex;gap:32px;flex-wrap:wrap;margin-bottom:24px">
  <div style="flex:1;min-width:240px">
    {size_chart}
    {_dim_table(result.by_size, cp50)}
  </div>
  <div style="flex:1;min-width:240px">
    {pr_chart}
    {_dim_table(result.by_payer_regime, cp50)}
  </div>
</div>
{ck_section_header("By Vintage Cohort")}
<div style="overflow-x:auto;margin-bottom:24px">{_dim_table(result.by_vintage, cp50)}</div>
{ck_section_header("Highest Capital Efficiency Deals", "Top 10 by MOIC ÷ EV/EBITDA")}
<div style="overflow-x:auto;margin-bottom:24px">
{_top_deals_table(result.top_moic_eff, "Top 10 — Highest MOIC per Turn of Multiple", cp50)}
</div>
{ck_section_header("Lowest Capital Efficiency Deals", "Bottom 10 — paid most per unit of return")}
<div style="overflow-x:auto">
{_top_deals_table(result.bottom_moic_eff, "Bottom 10 — Lowest MOIC per Turn of Multiple", cp50)}
</div>
<p style="font-size:11px;color:var(--ck-text-faint);margin-top:12px">
  MOIC Efficiency = realized MOIC ÷ entry EV/EBITDA. Higher is better — more return per dollar of entry premium.<br>
  VC Rate = (MOIC − 1) ÷ hold_years. Measures net return velocity per year held.
</p>
"""

    return chartis_shell(
        body=body,
        title="Capital Efficiency Analysis",
        active_nav="/capital-efficiency",
        subtitle="Return density per unit of entry multiple — corpus-wide and by segment",
    )
