"""Win/Loss analyzer page — /win-loss.

Win rate by named competitor, loss-reason decomposition, and the
price-gap read on lost deals. Renders from rcm_mc.data_public.win_loss.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_data_cell, ck_illustrative_note, ck_kpi_block,
    ck_page_title,
)


def _win_rate_svg(competitors) -> str:
    if not competitors:
        return ""
    w, row_h, pad_l, pad_t = 560, 26, 230, 36
    h = pad_t + len(competitors) * row_h + 12
    inner = w - pad_l - 80
    parts = [
        f'<rect width="{w}" height="{h}" fill="{P["panel"]}"/>',
        f'<text x="10" y="20" fill="{P["text_dim"]}" font-size="10" '
        f'font-family="Inter,sans-serif">Head-to-head win rate by '
        f'competitor (50% line marked)</text>',
    ]
    x50 = pad_l + 0.5 * inner
    parts.append(f'<line x1="{x50}" y1="{pad_t - 4}" x2="{x50}" y2="{h - 8}" '
                 f'stroke="{P["border"]}" stroke-width="1" '
                 f'stroke-dasharray="3,3"/>')
    for i, c in enumerate(competitors):
        y = pad_t + i * row_h
        bw = c.win_rate_pct / 100 * inner
        fill = P["positive"] if c.win_rate_pct >= 50 else P["negative"]
        name = (c.competitor if len(c.competitor) <= 30
                else c.competitor[:29] + "…")
        parts.append(
            f'<text x="{pad_l - 8}" y="{y + 15}" fill="{P["text_dim"]}" '
            f'font-size="10" text-anchor="end" '
            f'font-family="JetBrains Mono,monospace">{_html.escape(name)}</text>'
            f'<rect x="{pad_l}" y="{y + 4}" width="{bw:.1f}" height="14" '
            f'fill="{fill}" opacity="0.8"/>'
            f'<text x="{pad_l + bw + 6:.1f}" y="{y + 15}" fill="{P["text_dim"]}" '
            f'font-size="10" font-family="JetBrains Mono,monospace">'
            f'{c.win_rate_pct:.1f}% ({c.wins}/{c.contested})</text>')
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" '
            f'xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>')


def _loss_mix_svg(mix) -> str:
    if not mix:
        return ""
    items = sorted(mix.items(), key=lambda kv: -kv[1])
    w, row_h, pad_l, pad_t = 560, 24, 230, 16
    h = pad_t + len(items) * row_h + 10
    inner = w - pad_l - 70
    max_v = max(v for _, v in items) or 1
    parts = [f'<rect width="{w}" height="{h}" fill="{P["panel"]}"/>']
    for i, (reason, share) in enumerate(items):
        y = pad_t + i * row_h
        bw = share / max_v * inner
        fill = P["negative"] if reason == "PRICE" else (
            P["warning"] if reason == "CAPABILITY" else P["text_faint"])
        parts.append(
            f'<text x="{pad_l - 8}" y="{y + 14}" fill="{P["text_dim"]}" '
            f'font-size="10" text-anchor="end" '
            f'font-family="JetBrains Mono,monospace">'
            f'{_html.escape(reason)}</text>'
            f'<rect x="{pad_l}" y="{y + 3}" width="{bw:.1f}" height="13" '
            f'fill="{fill}" opacity="0.8"/>'
            f'<text x="{pad_l + bw + 6:.1f}" y="{y + 14}" fill="{P["text_dim"]}" '
            f'font-size="10" font-family="JetBrains Mono,monospace">'
            f'{share:.1f}%</text>')
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" '
            f'xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>')


def _trend_svg(trend) -> str:
    """Quarterly win-rate line — four points, labelled."""
    if not trend:
        return ""
    w, h = 560, 150
    pad_l, pad_r, pad_t, pad_b = 60, 30, 26, 28
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    vals = [t.win_rate_pct for t in trend]
    lo, hi = min(vals) - 3, max(vals) + 3
    span = (hi - lo) or 1
    pts = []
    for i, t in enumerate(trend):
        x = pad_l + (i / max(len(trend) - 1, 1)) * inner_w
        y = pad_t + (1 - (t.win_rate_pct - lo) / span) * inner_h
        pts.append((x, y, t))
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in pts)
    parts = [
        f'<rect width="{w}" height="{h}" fill="{P["panel"]}"/>',
        f'<text x="10" y="17" fill="{P["text_dim"]}" font-size="10" '
        f'font-family="Inter,sans-serif">Win-rate trend (contested '
        f'opportunities per quarter)</text>',
        f'<polyline points="{polyline}" fill="none" stroke="{P["accent"]}" '
        f'stroke-width="2"/>',
    ]
    for x, y, t in pts:
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{P["accent"]}"/>'
            f'<text x="{x:.1f}" y="{y - 8:.1f}" fill="{P["text_dim"]}" '
            f'font-size="9" text-anchor="middle" '
            f'font-family="JetBrains Mono,monospace">{t.win_rate_pct:.1f}%</text>'
            f'<text x="{x:.1f}" y="{h - 10}" fill="{P["text_faint"]}" '
            f'font-size="9" text-anchor="middle" '
            f'font-family="JetBrains Mono,monospace">{_html.escape(t.quarter)}'
            f' (n={t.opportunities})</text>')
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" '
            f'xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>')


def _competitors_table(competitors) -> str:
    border = P["border"]; text_dim = P["text_dim"]
    cols = [("Competitor", "left"), ("Contested", "right"), ("Wins", "right"),
            ("Win rate", "right"), ("Dominant loss reason", "left"),
            ("Price gap on losses", "right"), ("Pattern", "left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid '
        f'{border};font-size:10px;color:{text_dim};letter-spacing:0.05em">'
        f'{c}</th>' for c, a in cols)
    trs = []
    for c in competitors:
        gap_tone = "neg" if c.median_price_gap_pct > 0 else "pos"
        trs.append("<tr>" + "".join([
            ck_data_cell(_html.escape(c.competitor), mono=True, weight=600),
            ck_data_cell(str(c.contested), align="right", mono=True),
            ck_data_cell(str(c.wins), align="right", mono=True),
            ck_data_cell(f"{c.win_rate_pct:.1f}%", align="right", mono=True,
                         tone="pos" if c.win_rate_pct >= 50
                         else "neg", weight=600),
            f'<td style="text-align:left;padding:5px 10px;font-family:'
            f'JetBrains Mono,monospace;font-size:10px;color:{text_dim}">'
            f'{_html.escape(c.dominant_loss_reason)}</td>',
            ck_data_cell(f"{c.median_price_gap_pct:+.1f}%", align="right",
                         mono=True, tone=gap_tone),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;'
            f'color:{text_dim};max-width:300px">{_html.escape(c.note)}</td>',
        ]) + "</tr>")
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody>'
            f'</table></div>')


def _segments_table(segments) -> str:
    border = P["border"]; text_dim = P["text_dim"]
    cols = [("Opportunity segment", "left"), ("Opportunities", "right"),
            ("Wins", "right"), ("Win rate", "right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid '
        f'{border};font-size:10px;color:{text_dim};letter-spacing:0.05em">'
        f'{c}</th>' for c, a in cols)
    trs = []
    for s in segments:
        trs.append("<tr>" + "".join([
            ck_data_cell(_html.escape(s.segment), mono=True, weight=600),
            ck_data_cell(str(s.opportunities), align="right", mono=True),
            ck_data_cell(str(s.wins), align="right", mono=True),
            ck_data_cell(f"{s.win_rate_pct:.1f}%", align="right", mono=True,
                         tone="pos" if s.win_rate_pct >= 50
                         else "neg", weight=600),
        ]) + "</tr>")
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody>'
            f'</table></div>')


def render_win_loss(params: dict = None) -> str:
    params = params or {}
    from rcm_mc.data_public.win_loss import SECTORS, compute_win_loss
    sector = params.get("sector", SECTORS[0]) or SECTORS[0]
    r = compute_win_loss(sector=sector)

    panel = P["panel"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]

    kpi_strip = (
        ck_kpi_block("Overall win rate", f"{r.overall_win_rate_pct:.1f}%",
                     "", "") +
        ck_kpi_block("Opportunities", str(r.total_opportunities), "", "") +
        ck_kpi_block("Wins", str(r.total_wins), "", "") +
        ck_kpi_block("Price-led losses", f"{r.price_loss_share_pct:.1f}%",
                     "share of all losses", "") +
        ck_kpi_block("Latest quarter", f"{r.trend[-1].win_rate_pct:.1f}%",
                     _html.escape(r.trend[-1].quarter), "") +
        ck_kpi_block("Named competitors", str(len(r.competitors)), "", "")
    )

    options = "".join(
        f'<option value="{_html.escape(s)}"'
        f'{" selected" if s == r.sector else ""}>{_html.escape(s)}</option>'
        for s in SECTORS)
    form = f"""
<form method="GET" action="/win-loss" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Opportunity log
    <select name="sector" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace">{options}</select>
  </label>
  <button type="submit"
    style="background:{border};color:{text};border:1px solid {border};
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Load log</button>
</form>"""

    cell = (f"background:{panel};border:1px solid {border};padding:16px;"
            f"margin-bottom:16px")
    h3 = (f"font-size:11px;font-weight:600;letter-spacing:0.08em;"
          f"color:{text_dim};text-transform:uppercase;margin-bottom:10px")

    page_title = ck_page_title(
        "Win/Loss Analyzer",
        eyebrow="CDD · COMPETITIVE CONVERSION",
        meta=(f"{r.sector} · {r.total_wins}/{r.total_opportunities} won "
              f"({r.overall_win_rate_pct:.1f}%) · price-led losses "
              f"{r.price_loss_share_pct:.1f}% · trend "
              f"{r.trend[0].win_rate_pct:.1f}% → "
              f"{r.trend[-1].win_rate_pct:.1f}%"),
    )

    headline = (f'<div style="{cell};border-left:3px solid {P["accent"]}">'
                f'<div style="{h3}">Conversion read</div>'
                f'<div style="font-size:14px;color:{text}">'
                f'{_html.escape(r.headline)}</div></div>')

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {ck_illustrative_note("opportunity log")}
  {form}
  <div class="ck-kpi-grid">{kpi_strip}</div>
  {headline}
  <div style="{cell}">
    <div style="{h3}">Head-to-head record by competitor</div>
    {_win_rate_svg(r.competitors)}
    {_competitors_table(r.competitors)}
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
    <div style="{cell}">
      <div style="{h3}">Loss-reason mix</div>
      {_loss_mix_svg(r.loss_reason_mix)}
    </div>
    <div style="{cell}">
      <div style="{h3}">Win-rate trend</div>
      {_trend_svg(r.trend)}
    </div>
  </div>
  <div style="{cell}">
    <div style="{h3}">Win rate by opportunity segment</div>
    {_segments_table(r.segments)}
  </div>
</div>"""
    return chartis_shell(body, title="Win/Loss Analyzer",
                         active_nav="/win-loss")
