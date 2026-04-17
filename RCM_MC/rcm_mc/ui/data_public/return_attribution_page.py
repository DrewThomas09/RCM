"""Return Attribution page — MOIC decomposition by deal dimensions.

Shows P25/P50/P75 MOIC by sector, vintage, payer regime, size bucket,
hold duration, and entry multiple. Inline SVG bar charts, dense tables.
"""
from __future__ import annotations

import html
import math
from typing import List, Optional

from rcm_mc.ui._chartis_kit import (
    P, _MONO, _SANS,
    chartis_shell, ck_section_header,
)


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def _range_bar_chart(
    slices: list,
    title: str,
    corpus_p50: Optional[float] = None,
    w: int = 380,
    row_h: int = 22,
    pad_l: int = 140,
    pad_r: int = 60,
    pad_t: int = 18,
) -> str:
    """Horizontal P25–P75 range bars with P50 tick and corpus baseline."""
    valid = [s for s in slices if s.moic_p50 is not None]
    if not valid:
        return ""

    all_vals = []
    for s in valid:
        for v in [s.moic_p25, s.moic_p50, s.moic_p75]:
            if v is not None:
                all_vals.append(v)
    if corpus_p50:
        all_vals.append(corpus_p50)

    vmin, vmax = 0, max(all_vals) * 1.08
    chart_w = w - pad_l - pad_r
    total_h = pad_t + len(valid) * row_h + 20

    def xp(v: float) -> float:
        return pad_l + (v - vmin) / (vmax - vmin) * chart_w

    parts = [
        f'<text x="{w//2}" y="12" text-anchor="middle" fill="{P["text_dim"]}" font-size="9" font-family="{_SANS}" font-weight="600" letter-spacing=".08em">{html.escape(title)}</text>'
    ]

    # x-axis grid lines
    step = 0.5
    v = 0.0
    while v <= vmax:
        tx = xp(v)
        parts.append(f'<line x1="{tx:.1f}" y1="{pad_t-4}" x2="{tx:.1f}" y2="{total_h-16}" stroke="{P["border_dim"]}" stroke-width="1"/>')
        parts.append(f'<text x="{tx:.1f}" y="{total_h-6}" text-anchor="middle" fill="{P["text_faint"]}" font-size="7" font-family="{_MONO}" font-variant-numeric="tabular-nums">{v:.1f}×</text>')
        v += step

    # corpus baseline
    if corpus_p50 is not None:
        cx = xp(corpus_p50)
        parts.append(f'<line x1="{cx:.1f}" y1="{pad_t}" x2="{cx:.1f}" y2="{total_h-16}" stroke="{P["text_faint"]}" stroke-width="1" stroke-dasharray="3,3"/>')

    for i, s in enumerate(valid):
        y_mid = pad_t + i * row_h + row_h // 2
        label_color = P["text"] if i % 2 == 0 else P["text_dim"]
        trunc = s.label[:22]
        parts.append(f'<text x="{pad_l-6}" y="{y_mid+4}" text-anchor="end" fill="{label_color}" font-size="9" font-family="{_SANS}">{html.escape(trunc)}</text>')

        if s.moic_p25 is not None and s.moic_p75 is not None:
            x1, x2 = xp(s.moic_p25), xp(s.moic_p75)
            bar_color = P["panel"]
            if (s.moic_p50 or 0) >= 3.0:
                bar_color = "#0d2218"
            elif (s.moic_p50 or 0) >= 2.0:
                bar_color = "#0d1a2a"
            parts.append(f'<rect x="{x1:.1f}" y="{y_mid-5}" width="{x2-x1:.1f}" height="10" fill="{bar_color}" stroke="{P["border"]}" stroke-width="1"/>')

        if s.moic_p50 is not None:
            tx = xp(s.moic_p50)
            col = P["positive"] if s.moic_p50 >= 2.5 else (P["warning"] if s.moic_p50 >= 2.0 else P["negative"])
            parts.append(f'<line x1="{tx:.1f}" y1="{y_mid-7}" x2="{tx:.1f}" y2="{y_mid+7}" stroke="{col}" stroke-width="2"/>')
            parts.append(f'<text x="{xp(vmax)+4:.1f}" y="{y_mid+4}" fill="{col}" font-size="9" font-family="{_MONO}" font-variant-numeric="tabular-nums">{s.moic_p50:.2f}×</text>')

    return f'<svg width="{w}" height="{total_h}" style="overflow:visible">{"".join(parts)}</svg>'


def _slice_table(slices: list, corpus_p50: Optional[float] = None) -> str:
    if not slices:
        return ""

    th = (
        f"padding:4px 8px;font-size:9px;letter-spacing:.08em;"
        f"color:{P['text_dim']};font-family:{_SANS};font-weight:600;"
        f"border-bottom:1px solid {P['border']};white-space:nowrap;"
        f"position:sticky;top:0;background:{P['panel_alt']}"
    )

    header = f"""<tr style="background:{P['panel_alt']}">
  <th style="{th}">DIMENSION</th>
  <th style="{th};text-align:right">N</th>
  <th style="{th};text-align:right">MOIC P25</th>
  <th style="{th};text-align:right">MOIC P50</th>
  <th style="{th};text-align:right">MOIC P75</th>
  <th style="{th};text-align:right">SPREAD</th>
  <th style="{th};text-align:right">IRR P50</th>
  <th style="{th};text-align:right">WIN%</th>
  <th style="{th};text-align:right">TOTAL EV</th>
</tr>"""

    rows = ""
    for i, s in enumerate(slices):
        bg = P["row_stripe"] if i % 2 else P["panel"]
        p50 = s.moic_p50 or 0
        col = P["positive"] if p50 >= 2.5 else (P["warning"] if p50 >= 2.0 else (P["negative"] if p50 < 1.5 else P["text"]))
        vs_corpus = ""
        if corpus_p50 and s.moic_p50:
            diff = s.moic_p50 - corpus_p50
            vs_corpus = f' <span style="font-size:8px;color:{P["positive"] if diff > 0 else P["negative"]}">{"+" if diff > 0 else ""}{diff:.2f}×</span>'

        ev = s.total_ev_mm
        ev_str = f"${ev/1000:.1f}B" if ev and ev >= 1000 else (f"${ev:,.0f}M" if ev else "—")
        p25_s = f"{s.moic_p25:.2f}×" if s.moic_p25 else "—"
        p50_s = f"{s.moic_p50:.2f}×" if s.moic_p50 else "—"
        p75_s = f"{s.moic_p75:.2f}×" if s.moic_p75 else "—"
        spr_s = f"{s.moic_spread:.2f}×" if s.moic_spread else "—"
        irr_s = f"{s.irr_p50*100:.1f}%" if s.irr_p50 else "—"
        win_s = f"{s.win_rate*100:.0f}%" if s.win_rate is not None else "—"

        rows += f"""<tr style="background:{bg}">
  <td style="padding:4px 8px;font-size:11px;white-space:nowrap">{html.escape(s.label)}</td>
  <td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{s.deal_count}</td>
  <td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;color:{P['text_dim']};font-variant-numeric:tabular-nums">{p25_s}</td>
  <td style="padding:4px 8px;font-size:12px;font-family:{_MONO};text-align:right;font-weight:700;color:{col};font-variant-numeric:tabular-nums">{p50_s}{vs_corpus}</td>
  <td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;color:{P['text_dim']};font-variant-numeric:tabular-nums">{p75_s}</td>
  <td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{spr_s}</td>
  <td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{irr_s}</td>
  <td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{win_s}</td>
  <td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{ev_str}</td>
</tr>"""

    return f"""<div style="overflow-x:auto;border:1px solid {P['border']}">
<table style="width:100%;border-collapse:collapse;min-width:700px">
<thead>{header}</thead>
<tbody>{rows}</tbody>
</table>
</div>"""


def _dim_panel(title: str, slices: list, corpus_p50: Optional[float]) -> str:
    chart = _range_bar_chart(slices, title, corpus_p50)
    table = _slice_table(slices, corpus_p50)
    return f"""<div style="margin-bottom:20px">
  <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.1em;
              margin-bottom:8px;border-bottom:1px solid {P['border']};padding-bottom:4px">
    {html.escape(title)}
  </div>
  <div style="display:grid;grid-template-columns:auto 1fr;gap:16px;align-items:start">
    <div style="background:{P['panel_alt']};border:1px solid {P['border']};padding:10px">
      {chart}
    </div>
    {table}
  </div>
</div>"""


def render_return_attribution() -> str:
    from rcm_mc.data_public.return_attribution import compute_return_attribution

    ra = compute_return_attribution()
    cp50 = ra.corpus_moic_p50
    ci50 = ra.corpus_irr_p50

    p50_str = f"{cp50:.2f}×" if cp50 else "—"
    irr_str = f"{ci50*100:.1f}%" if ci50 else "—"

    # KPI strip
    kpis = "".join(
        f'<div style="background:{P["panel_alt"]};border:1px solid {P["border"]};padding:8px 14px">'
        f'<div style="font-size:9px;color:{P["text_dim"]};font-family:{_SANS};letter-spacing:.08em;margin-bottom:3px">{lbl}</div>'
        f'<div style="font-size:16px;font-family:{_MONO};font-variant-numeric:tabular-nums;color:{P["text"]}">{val}</div>'
        f'</div>'
        for lbl, val in [
            ("CORPUS N", str(ra.corpus_size)),
            ("CORPUS MOIC P50", p50_str),
            ("CORPUS IRR P50", irr_str),
            ("SECTORS TRACKED", str(len(ra.by_sector))),
            ("VINTAGE BUCKETS", str(len(ra.by_vintage))),
        ]
    )
    kpi_strip = f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-bottom:16px">{kpis}</div>'

    legend = (
        f'<div style="font-size:9px;color:{P["text_faint"]};font-family:{_SANS};margin-bottom:14px">'
        f'Bar = P25–P75 band. Vertical tick = P50. Dashed baseline = corpus P50 {p50_str}. '
        f'Right column delta shows difference from corpus P50. Win rate = deals with MOIC ≥ 2.0×.'
        f'</div>'
    )

    body = f"""
<div style="padding:16px 20px;max-width:1400px">
  {ck_section_header("RETURN ATTRIBUTION", f"MOIC decomposition by deal dimension — {ra.corpus_size} transactions", None)}
  {kpi_strip}
  {legend}
  {_dim_panel("BY SECTOR — MOIC DISTRIBUTION (P25 / P50 / P75)", ra.by_sector[:20], cp50)}
  {_dim_panel("BY VINTAGE BUCKET — MOIC DISTRIBUTION", ra.by_vintage, cp50)}
  {_dim_panel("BY PAYER REGIME — MOIC DISTRIBUTION", ra.by_payer_regime, cp50)}
  {_dim_panel("BY DEAL SIZE — MOIC DISTRIBUTION", ra.by_size_bucket, cp50)}
  {_dim_panel("BY HOLD DURATION — MOIC DISTRIBUTION", ra.by_hold_bucket, cp50)}
  {_dim_panel("BY ENTRY MULTIPLE (EV/EBITDA) — MOIC DISTRIBUTION", ra.by_ev_ebitda_bucket, cp50)}
</div>"""

    return chartis_shell(body, "Return Attribution", active_nav="/return-attribution", subtitle=f"Corpus: {ra.corpus_size} deals")
