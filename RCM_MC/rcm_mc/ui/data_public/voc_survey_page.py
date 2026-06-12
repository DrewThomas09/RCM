"""Voice-of-Customer survey evidence page — /voc-survey.

NPS by segment, KPC gap matrix, willingness-to-pay — the customer-
evidence half of a CDD readout that the desk previously had no surface
for. Renders from rcm_mc.data_public.voc_survey.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_data_cell, ck_illustrative_note, ck_kpi_block,
    ck_page_title,
)

def _kpc_gap_svg(rows) -> str:
    """Diverging gap bars, importance-sorted: green right = target ahead
    of the best competitor, red left = behind. The single chart a CDD
    readout opens the customer section with."""
    if not rows:
        return ""
    w = 560
    row_h = 26
    pad_l, pad_t = 250, 36
    h = pad_t + len(rows) * row_h + 16
    mid = pad_l + (w - pad_l - 20) / 2
    half = (w - pad_l - 20) / 2
    max_gap = max(abs(r.gap) for r in rows) or 1.0
    parts = [
        f'<rect width="{w}" height="{h}" fill="{P["panel"]}"/>',
        f'<text x="10" y="20" fill="{P["text_dim"]}" font-size="10" '
        f'font-family="Inter,sans-serif">KPC gap vs best competitor '
        f'(sorted by stated importance)</text>',
        f'<line x1="{mid}" y1="{pad_t - 6}" x2="{mid}" y2="{h - 10}" '
        f'stroke="{P["border"]}" stroke-width="1"/>',
    ]
    tone_fill = {"DIFFERENTIATOR": P["positive"],
                 "VULNERABILITY": P["negative"],
                 "TABLE_STAKES": P["text_faint"]}
    for i, r in enumerate(rows):
        y = pad_t + i * row_h
        bw = abs(r.gap) / max_gap * (half - 30)
        x = mid if r.gap >= 0 else mid - bw
        fill = tone_fill[r.classification]
        label = r.criterion if len(r.criterion) <= 34 else r.criterion[:33] + "…"
        lx = mid + bw + 6 if r.gap >= 0 else mid - bw - 6
        anchor = "start" if r.gap >= 0 else "end"
        parts.append(
            f'<text x="{pad_l - 8}" y="{y + 15}" fill="{P["text_dim"]}" '
            f'font-size="10" text-anchor="end" '
            f'font-family="JetBrains Mono,monospace">{_html.escape(label)} '
            f'({r.importance:.1f})</text>'
            f'<rect x="{x:.1f}" y="{y + 4}" width="{max(bw, 1):.1f}" height="14" '
            f'fill="{fill}" opacity="0.85"/>'
            f'<text x="{lx:.1f}" y="{y + 15}" fill="{P["text_dim"]}" font-size="9" '
            f'text-anchor="{anchor}" font-family="JetBrains Mono,monospace">'
            f'{r.gap:+.1f}</text>'
        )
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" '
            f'xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>')


def _segments_table(segments) -> str:
    border = P["border"]; text_dim = P["text_dim"]
    cols = [("Segment", "left"), ("N", "right"), ("NPS", "right"),
            ("Repurchase intent", "right"), ("Churn intent", "right"),
            ("Dominant verbatim theme", "left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid '
        f'{border};font-size:10px;color:{text_dim};letter-spacing:0.05em">'
        f'{c}</th>' for c, a in cols)
    trs = []
    for s in segments:
        nps_tone = "pos" if s.nps >= 30 else ("dim" if s.nps >= 0 else "neg")
        trs.append("<tr>" + "".join([
            ck_data_cell(_html.escape(s.segment), mono=True, weight=600),
            ck_data_cell(str(s.n_respondents), align="right", mono=True),
            ck_data_cell(f"{s.nps:+d}", align="right", mono=True, tone=nps_tone),
            ck_data_cell(f"{s.repurchase_intent_pct:.1f}%", align="right", mono=True),
            ck_data_cell(f"{s.churn_intent_pct:.1f}%", align="right", mono=True,
                         tone="neg" if s.churn_intent_pct >= 12 else "dim"),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;'
            f'color:{text_dim};max-width:320px">{_html.escape(s.verbatim_theme)}</td>',
        ]) + "</tr>")
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody>'
            f'</table></div>')


def _kpc_table(rows) -> str:
    border = P["border"]; text_dim = P["text_dim"]
    cols = [("Purchase criterion", "left"), ("Importance /5", "right"),
            ("Target /10", "right"), ("Best comp /10", "right"),
            ("Gap", "right"), ("Read", "left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid '
        f'{border};font-size:10px;color:{text_dim};letter-spacing:0.05em">'
        f'{c}</th>' for c, a in cols)
    trs = []
    for r in rows:
        tone = P["positive"] if r.classification == "DIFFERENTIATOR" else (
            P["negative"] if r.classification == "VULNERABILITY"
            else P["text_faint"])
        chip = (f'<span style="display:inline-block;padding:2px 8px;'
                f'font-size:10px;font-family:JetBrains Mono,monospace;'
                f'color:{tone};border:1px solid {tone};border-radius:2px;'
                f'letter-spacing:0.06em">{r.classification.replace("_", " ")}'
                f'</span>')
        trs.append("<tr>" + "".join([
            ck_data_cell(_html.escape(r.criterion), mono=True, weight=600),
            ck_data_cell(f"{r.importance:.1f}", align="right", mono=True),
            ck_data_cell(f"{r.target_score:.1f}", align="right", mono=True),
            ck_data_cell(f"{r.best_competitor_score:.1f}", align="right",
                         mono=True),
            ck_data_cell(f"{r.gap:+.1f}", align="right", mono=True,
                         tone="pos" if r.gap > 0 else
                         ("neg" if r.gap < 0 else "dim")),
            ck_data_cell(chip),
        ]) + "</tr>")
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody>'
            f'</table></div>')


def _wtp_bars(bands) -> str:
    """Horizontal share bars for the willingness-to-pay bands."""
    if not bands:
        return ""
    w, row_h, pad_l, pad_t = 560, 26, 230, 16
    h = pad_t + len(bands) * row_h + 10
    max_share = max(b.share_pct for b in bands) or 1
    inner = w - pad_l - 70
    parts = [f'<rect width="{w}" height="{h}" fill="{P["panel"]}"/>']
    for i, b in enumerate(bands):
        y = pad_t + i * row_h
        bw = b.share_pct / max_share * inner
        fill = P["accent"] if "Accept" in b.label else (
            P["negative"] if "concession" in b.label else P["text_faint"])
        parts.append(
            f'<text x="{pad_l - 8}" y="{y + 15}" fill="{P["text_dim"]}" '
            f'font-size="10" text-anchor="end" '
            f'font-family="JetBrains Mono,monospace">'
            f'{_html.escape(b.label)}</text>'
            f'<rect x="{pad_l}" y="{y + 4}" width="{bw:.1f}" height="14" '
            f'fill="{fill}" opacity="0.85"/>'
            f'<text x="{pad_l + bw + 6:.1f}" y="{y + 15}" fill="{P["text_dim"]}" '
            f'font-size="10" font-family="JetBrains Mono,monospace">'
            f'{b.share_pct:.1f}%</text>')
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" '
            f'xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>')


def render_voc_survey(params: dict = None) -> str:
    params = params or {}
    from rcm_mc.data_public.voc_survey import SECTORS, compute_voc
    sector = params.get("sector", SECTORS[0]) or SECTORS[0]
    r = compute_voc(sector=sector)

    panel = P["panel"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]

    kpi_strip = (
        ck_kpi_block("Blended NPS", f"{r.blended_nps:+d}", "", "") +
        ck_kpi_block("Respondents", str(r.n_total), "", "") +
        ck_kpi_block("Segments", str(len(r.segments)), "", "") +
        ck_kpi_block("Differentiators", str(len(r.differentiators)), "", "") +
        ck_kpi_block("Vulnerabilities", str(len(r.vulnerabilities)), "", "") +
        ck_kpi_block("Top WTP band", f"{r.wtp_bands[0].share_pct:.1f}%",
                     _html.escape(r.wtp_bands[0].label), "")
    )

    options = "".join(
        f'<option value="{_html.escape(s)}"'
        f'{" selected" if s == r.sector else ""}>{_html.escape(s)}</option>'
        for s in SECTORS)
    form = f"""
<form method="GET" action="/voc-survey" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Survey panel
    <select name="sector" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace">{options}</select>
  </label>
  <button type="submit"
    style="background:{border};color:{text};border:1px solid {border};
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Load panel</button>
</form>"""

    cell = (f"background:{panel};border:1px solid {border};padding:16px;"
            f"margin-bottom:16px")
    h3 = (f"font-size:11px;font-weight:600;letter-spacing:0.08em;"
          f"color:{text_dim};text-transform:uppercase;margin-bottom:10px")

    page_title = ck_page_title(
        "Voice of Customer / Survey Evidence",
        eyebrow="CDD · CUSTOMER EVIDENCE",
        meta=(f"{r.sector} · N={r.n_total} across {len(r.segments)} segments "
              f"· NPS {r.blended_nps:+d} · {len(r.differentiators)} "
              f"differentiator(s), {len(r.vulnerabilities)} vulnerability(ies)"),
    )

    headline = (f'<div style="{cell};border-left:3px solid {P["accent"]}">'
                f'<div style="{h3}">Survey read</div>'
                f'<div style="font-size:14px;color:{text}">'
                f'{_html.escape(r.headline)}</div></div>')

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {ck_illustrative_note("survey panel")}
  {form}
  <div class="ck-kpi-grid">{kpi_strip}</div>
  {headline}
  <div style="{cell}">
    <div style="{h3}">KPC gap matrix — importance × performance vs best competitor</div>
    {_kpc_gap_svg(r.kpc_rows)}
    {_kpc_table(r.kpc_rows)}
  </div>
  <div style="{cell}">
    <div style="{h3}">NPS &amp; retention intent by segment</div>
    {_segments_table(r.segments)}
  </div>
  <div style="{cell}">
    <div style="{h3}">Willingness to pay — price-increase tolerance</div>
    {_wtp_bars(r.wtp_bands)}
  </div>
</div>"""
    return chartis_shell(body, title="Voice of Customer",
                         active_nav="/voc-survey")
