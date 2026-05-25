"""Concentration Risk page — HHI/CR3/CR5 portfolio diversification analysis."""
from __future__ import annotations

import html
import math
from typing import List

from rcm_mc.ui._chartis_kit import (
    ck_illustrative_note,
    P, _MONO, _SANS, chartis_shell, ck_fmt_num, ck_kpi_block,
    ck_page_title, ck_provenance_tooltip, ck_section_header,
)


def _hhi_gauge(hhi: float, w: int = 120, h: int = 24) -> str:
    """Horizontal bar gauge for HHI (0–10000)."""
    pct = min(1.0, hhi / 10000)
    bar_w = int(pct * (w - 2))
    col = P["positive"] if hhi < 1000 else (P["warning"] if hhi < 1800 else (P["negative"] if hhi < 2500 else "#b5321e"))
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
        "Highly Concentrated": "#b5321e",
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
            f'<tr>'
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


def _chow_consolidation_panel() -> str:
    """Real CMS change-of-ownership (CHOW) anchor — actual provider
    consolidation in SNF + hospital, the live market force behind
    rising concentration. The corpus HHI dimensions below are
    illustrative; this panel is real public CMS ownership-change data,
    so the page anchors its concentration thesis in observable
    market behaviour rather than the seed corpus alone."""
    from rcm_mc.data import snf_chow as _c
    snf = _c.chow_summary()
    if not snf.get("total_chows"):
        return ""
    hosp = _c.hospital_chow_summary()
    top = _c.top_chow_states(5)
    by_year = _c.chow_by_year()

    border = P["border"]
    tprim = P["text"]
    tdim = P["text_dim"]
    acc = P["accent"]

    top_cells = "".join(
        f'<span style="display:inline-block;margin-right:10px;font-family:{_MONO};'
        f'font-size:11px;color:{tprim}">{html.escape(str(r["state"]))} '
        f'<span style="color:{acc};font-variant-numeric:tabular-nums">{int(r["chow_count"]):,}</span></span>'
        for r in top
    )
    # compact year sparkline of CHOW counts (full years only)
    yrs = [r for r in by_year if int(r["year"]) < snf.get("year_max", 0)] or by_year
    spark = ""
    if yrs:
        mx = max(int(r["chow_count"]) for r in yrs) or 1
        bars = "".join(
            f'<rect x="{i*14}" y="{30-int(int(r["chow_count"])/mx*28)}" width="10" '
            f'height="{int(int(r["chow_count"])/mx*28)}" fill="{acc}" opacity="0.75"/>'
            for i, r in enumerate(yrs)
        )
        labels = "".join(
            f'<text x="{i*14+5}" y="40" text-anchor="middle" font-size="6" '
            f'fill="{P["text_faint"]}" font-family="{_MONO}">{str(r["year"])[2:]}</text>'
            for i, r in enumerate(yrs)
        )
        spark = f'<svg width="{len(yrs)*14}" height="42">{bars}{labels}</svg>'

    snf_n = int(snf.get("total_chows", 0))
    hosp_n = int(hosp.get("total_chows", 0))
    y0, y1 = snf.get("year_min"), snf.get("year_max")

    return f'''
<div style="background:{P["panel"]};border:1px solid {border};border-left:3px solid {acc};
  padding:12px;margin-bottom:16px">
  <div style="font-family:{_MONO};font-size:10px;color:{tdim};
    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
    Real CMS consolidation backdrop &mdash; change-of-ownership
    <span style="color:{acc};font-weight:600"> · LIVE</span>
  </div>
  <div style="display:grid;grid-template-columns:auto auto 1fr;gap:18px;align-items:start">
    <div>
      <div style="font-family:{_MONO};font-size:20px;color:{tprim};
        font-variant-numeric:tabular-nums">{snf_n:,}</div>
      <div style="font-size:10px;color:{tdim}">SNF ownership changes<br>{y0}&ndash;{y1}</div>
    </div>
    <div>
      <div style="font-family:{_MONO};font-size:20px;color:{tprim};
        font-variant-numeric:tabular-nums">{hosp_n:,}</div>
      <div style="font-size:10px;color:{tdim}">Hospital ownership changes<br>{y0}&ndash;{y1}</div>
    </div>
    <div>
      <div style="font-size:9px;color:{P["text_faint"]};font-family:{_SANS};margin-bottom:2px">SNF CHOWs BY YEAR</div>
      {spark}
    </div>
  </div>
  <div style="margin-top:8px;font-size:10px;color:{tdim}">
    <span style="color:{P["text_faint"]}">Top SNF CHOW states:</span> {top_cells}
  </div>
  <div style="margin-top:6px;font-size:10px;color:{P["text_faint"]}">
    CMS public ownership/CHOW files. Real market consolidation &mdash;
    the corpus HHI dimensions below are illustrative; use them as the
    structural lens, this panel as the observed-market reality.
  </div>
</div>'''


def render_concentration_risk() -> str:
    from rcm_mc.data_public.concentration_analytics import compute_concentration

    cr = compute_concentration()

    # Summary KPI strip — cycle 41 ports to ck_kpi_block + adds
    # provenance on the highest-stakes dimension (sector HHI).
    dims = [cr.sector, cr.sponsor, cr.payer_regime, cr.vintage, cr.region, cr.size_bucket, cr.sector_ev]
    sector_hhi_value = ck_provenance_tooltip(
        "Sector HHI",
        ck_fmt_num(cr.sector.hhi),
        explainer=(
            "Herfindahl-Hirschman Index of sector concentration "
            "in the deal corpus. DOJ/FTC thresholds: below 1,000 "
            "= competitive; 1,000-1,800 = moderate; 1,800-2,500 "
            "= concentrated; above 2,500 = highly concentrated."
        ),
    )
    kpi_blocks = []
    for i, d in enumerate(dims):
        label = f"{d.name.split(' ')[0]} HHI".title()
        value = sector_hhi_value if i == 0 else ck_fmt_num(d.hhi)
        kpi_blocks.append(ck_kpi_block(
            label,
            value,
            sub=d.interpretation,
        ))
    kpi_strip = (
        f'<div class="ck-kpi-grid" style="grid-template-columns:repeat(7,1fr);gap:6px;margin-bottom:16px">'
        f'{"".join(kpi_blocks)}</div>'
    )

    hhi_legend = (
        f'<div style="font-size:9px;color:{P["text_faint"]};font-family:{_SANS};margin-bottom:14px">'
        f'HHI thresholds (DOJ/FTC): &lt;1,000 = Competitive, 1,000–1,800 = Moderate, 1,800–2,500 = Concentrated, &gt;2,500 = Highly Concentrated. '
        f'CR3/CR5 = top 3/5 entity share of corpus deal count. N = {cr.corpus_size} transactions.'
        f'</div>'
    )

    # B11 — pre-fix, this page had no h1. It used ck_section_header
    # ("CONCENTRATION RISK", "Portfolio diversification analysis — N
    # corpus transactions", None) as a de-facto title — but
    # ck_section_header is an h2-level primitive for sections within
    # a page, not a page-level h1. Adding ck_page_title and removing
    # the now-redundant ck_section_header (its eyebrow + subtitle
    # text are absorbed into the new page_title's eyebrow + meta).
    # Meta highlights the sector HHI specifically since the page's
    # ck_provenance_tooltip already singles out sector concentration
    # as the highest-stakes dimension.
    page_title = ck_page_title(
        "Concentration Risk Analysis",
        eyebrow="CONCENTRATION RISK",
        meta=(
            f"{cr.corpus_size} corpus deals · "
            f"sector HHI {cr.sector.hhi:,.0f} · "
            f"{cr.sector.interpretation}"
        ),
    )
    body = f"""
<div style="padding:16px 20px;max-width:1200px">
  {page_title}
  {_chow_consolidation_panel()}
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

    return chartis_shell(ck_illustrative_note("concentration-risk figures") + body, "Concentration Risk", active_nav="/concentration-risk",
                         subtitle=f"HHI analysis — {cr.corpus_size} deals",
        editorial_intro={
            "eyebrow": "CONCENTRATION RISK",
            "headline": "Where the diversification breaks.",
            "italic_word": "breaks",
            "body": (
                f"Herfindahl-Hirschman Index across {cr.corpus_size} "
                f"corpus deals - by sector, payer, and geography. "
                f"HHI above 2,500 marks a concentrated regime; "
                f"every basis point of further concentration "
                f"narrows the surviving exit channels."
            ),
        })
