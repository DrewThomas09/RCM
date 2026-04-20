"""Concentration Risk page — HHI/CR3/CR5 portfolio diversification analysis."""
from __future__ import annotations

import html
import math
from typing import List

from rcm_mc.ui._chartis_kit import P, _MONO, _SANS, chartis_shell, ck_section_header


def _hhi_gauge(hhi: float, w: int = 120, h: int = 24) -> str:
    """Horizontal bar gauge for HHI (0–10000)."""
    pct = min(1.0, hhi / 10000)
    bar_w = int(pct * (w - 2))
    col = P["positive"] if hhi < 1000 else (P["warning"] if hhi < 1800 else (P["negative"] if hhi < 2500 else "#dc2626"))
    label_col = P["text"] if pct < 0.7 else P["panel"]
    return (
        f'<svg width="{w}" height="{h}">'
        f'<rect x="0" y="4" width="{w}" height="12" fill="{P["panel_alt"]}" stroke="{P["border"]}" stroke-width="1"/>'
        f'<rect x="1" y="5" width="{bar_w}" height="10" fill="{col}"/>'
        f'<text x="{w//2}" y="16" text-anchor="middle" fill="{P["text"]}" font-size="9" font-family="{_MONO}" font-variant-numeric="tabular-nums">{hhi:,.0f}</text>'
        f'</svg>'
    )


def _interp_badge(interp: str) -> str:
    cols = {
        "Competitive": P["positive"],
        "Moderate": P["warning"],
        "Concentrated": P["negative"],
        "Highly Concentrated": "#dc2626",
    }
    col = cols.get(interp, P["text_dim"])
    return (
        f'<span style="font-size:9px;font-family:{_SANS};font-weight:700;letter-spacing:.06em;'
        f'color:{col};border:1px solid {col};padding:1px 5px">{html.escape(interp).upper()}</span>'
    )


def _treemap_svg(top5: list, total_n: int, w: int = 300, h: int = 80) -> str:
    """Horizontal proportional bar showing top-5 shares."""
    if not top5 or total_n == 0:
        return ""

    colors = [P["accent"], "#1e5a8e", "#1a3a5c", P["text_dim"], P["text_faint"]]
    parts = []
    x = 0
    for i, (label, cnt, share_pct) in enumerate(top5):
        bar_w = max(1, int(share_pct / 100 * w))
        col = colors[i % len(colors)]
        trunc = label[:14]
        parts.append(f'<rect x="{x}" y="0" width="{bar_w}" height="30" fill="{col}"/>')
        if bar_w > 20:
            parts.append(f'<text x="{x+3}" y="12" fill="{P["text"]}" font-size="8" font-family="{_SANS}">{html.escape(trunc)}</text>')
            parts.append(f'<text x="{x+3}" y="24" fill="{P["text"]}" font-size="8" font-family="{_MONO}" font-variant-numeric="tabular-nums">{share_pct:.1f}%</text>')
        x += bar_w

    other_pct = max(0, 100 - sum(s for _, _, s in top5))
    if other_pct > 0.5:
        other_w = w - x
        parts.append(f'<rect x="{x}" y="0" width="{other_w}" height="30" fill="{P["panel"]}"/>')
        if other_w > 20:
            parts.append(f'<text x="{x+3}" y="12" fill="{P["text_faint"]}" font-size="8" font-family="{_SANS}">Other</text>')
            parts.append(f'<text x="{x+3}" y="24" fill="{P["text_faint"]}" font-size="8" font-family="{_MONO}">{other_pct:.1f}%</text>')

    return f'<svg width="{w}" height="30" style="display:block">{"".join(parts)}</svg>'


def _dim_card(dim) -> str:
    top5_rows = ""
    for i, (label, cnt, share_pct) in enumerate(dim.top_5):
        bg = P["row_stripe"] if i % 2 else P["panel"]
        bar_w = int(share_pct / 100 * 120)
        top5_rows += (
            f'<tr style="background:{bg}">'
            f'<td style="padding:3px 8px;font-size:10px">{html.escape(label[:28])}</td>'
            f'<td style="padding:3px 8px;text-align:right;font-size:10px;font-family:{_MONO};font-variant-numeric:tabular-nums">{cnt}</td>'
            f'<td style="padding:3px 8px">'
            f'<svg width="120" height="10"><rect x="0" y="2" width="{bar_w}" height="6" fill="{P["accent"]}"/></svg>'
            f'<span style="font-size:9px;font-family:{_MONO};font-variant-numeric:tabular-nums;margin-left:4px">{share_pct:.1f}%</span>'
            f'</td>'
            f'</tr>'
        )

    return f"""<div style="background:{P['panel_alt']};border:1px solid {P['border']};padding:12px;margin-bottom:12px">
  <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.08em;margin-bottom:8px">{html.escape(dim.name).upper()}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr auto;gap:12px;align-items:center;margin-bottom:10px">
    <div>
      <div style="font-size:9px;color:{P['text_faint']};font-family:{_SANS};margin-bottom:3px">HHI</div>
      {_hhi_gauge(dim.hhi)}
    </div>
    <div>
      <div style="font-size:9px;color:{P['text_faint']};font-family:{_SANS};margin-bottom:3px">CR3 / CR5</div>
      <div style="font-size:13px;font-family:{_MONO};font-variant-numeric:tabular-nums;color:{P['text']}">{dim.cr3:.1f}% / {dim.cr5:.1f}%</div>
    </div>
    <div>{_interp_badge(dim.interpretation)}</div>
    <div style="font-size:9px;color:{P['text_faint']};font-family:{_SANS}">N={dim.total_n}</div>
  </div>
  <div style="margin-bottom:8px">{_treemap_svg(dim.top_5, dim.total_n)}</div>
  <table style="width:100%;border-collapse:collapse;font-size:10px">
    <thead><tr style="background:{P['panel']}">
      <th style="padding:3px 8px;font-size:8px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.06em;text-align:left">LABEL</th>
      <th style="padding:3px 8px;font-size:8px;color:{P['text_dim']};font-family:{_SANS};text-align:right">DEALS</th>
      <th style="padding:3px 8px;font-size:8px;color:{P['text_dim']};font-family:{_SANS}">SHARE</th>
    </tr></thead>
    <tbody>{top5_rows}</tbody>
  </table>
</div>"""


def render_concentration_risk() -> str:
    from rcm_mc.data_public.concentration_analytics import compute_concentration

    cr = compute_concentration()

    # summary KPI strip
    dims = [cr.sector, cr.sponsor, cr.payer_regime, cr.vintage, cr.region, cr.size_bucket, cr.sector_ev]
    kpis = "".join(
        f'<div style="background:{P["panel_alt"]};border:1px solid {P["border"]};padding:8px 12px">'
        f'<div style="font-size:8px;color:{P["text_dim"]};font-family:{_SANS};letter-spacing:.06em;margin-bottom:3px">{html.escape(d.name.split(" ")[0]).upper()} HHI</div>'
        f'<div style="font-size:14px;font-family:{_MONO};font-variant-numeric:tabular-nums;color:{P["text"]}">{d.hhi:,.0f}</div>'
        f'<div style="font-size:9px;margin-top:2px">{_interp_badge(d.interpretation)}</div>'
        f'</div>'
        for d in dims
    )
    kpi_strip = f'<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:6px;margin-bottom:16px">{kpis}</div>'

    hhi_legend = (
        f'<div style="font-size:9px;color:{P["text_faint"]};font-family:{_SANS};margin-bottom:14px">'
        f'HHI thresholds (DOJ/FTC): &lt;1,000 = Competitive, 1,000–1,800 = Moderate, 1,800–2,500 = Concentrated, &gt;2,500 = Highly Concentrated. '
        f'CR3/CR5 = top 3/5 entity share of corpus deal count. N = {cr.corpus_size} transactions.'
        f'</div>'
    )

    body = f"""
<div style="padding:16px 20px;max-width:1200px">
  {ck_section_header("CONCENTRATION RISK", f"Portfolio diversification analysis — {cr.corpus_size} corpus transactions", None)}
  {kpi_strip}
  {hhi_legend}
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
    {_dim_card(cr.sector)}
    {_dim_card(cr.sector_ev)}
    {_dim_card(cr.sponsor)}
    {_dim_card(cr.payer_regime)}
    {_dim_card(cr.vintage)}
    {_dim_card(cr.region)}
    {_dim_card(cr.size_bucket)}
  </div>
</div>"""

    return chartis_shell(body, "Concentration Risk", active_nav="/concentration-risk",
                         subtitle=f"HHI analysis — {cr.corpus_size} deals")
