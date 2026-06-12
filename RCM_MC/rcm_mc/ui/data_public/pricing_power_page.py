"""Pricing Power analyzer page — /pricing-power.

Per-segment price-response curves (EBITDA change vs price move), the
window-optimal move per segment, and the portfolio EBITDA prize.
Renders from rcm_mc.data_public.pricing_power.
"""
from __future__ import annotations

import html as _html
from urllib.parse import quote as _url_quote

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_data_cell, ck_illustrative_note, ck_kpi_block,
    ck_page_title,
)

_CURVE_COLORS = ["#155752", "#0b2341", "#b8732a", "#b5321e", "#0a8a5f"]


def _curves_svg(segments) -> str:
    """All segment EBITDA curves on one frame: x = price move %,
    y = EBITDA change. The zero lines make the read instant — anything
    above the horizontal line at a given x is a profitable move."""
    drawable = [s for s in segments if not s.price_locked]
    if not drawable:
        return ""
    w, h = 620, 240
    pad_l, pad_r, pad_t, pad_b = 70, 160, 24, 30
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    all_pts = [pt for s in drawable for pt in s.curve]
    y_lo = min(pt.ebitda_change_usd for pt in all_pts)
    y_hi = max(pt.ebitda_change_usd for pt in all_pts)
    span = (y_hi - y_lo) or 1.0

    def _xy(pt):
        x = pad_l + (pt.price_change_pct + 15) / 30 * inner_w
        y = pad_t + (1 - (pt.ebitda_change_usd - y_lo) / span) * inner_h
        return x, y

    parts = [
        f'<rect width="{w}" height="{h}" fill="{P["panel"]}"/>',
        f'<text x="10" y="16" fill="{P["text_dim"]}" font-size="10" '
        f'font-family="Inter,sans-serif">EBITDA change vs price move '
        f'(±15% window) — dot marks each segment\'s optimum</text>',
    ]
    x0 = pad_l + 0.5 * inner_w
    parts.append(f'<line x1="{x0}" y1="{pad_t}" x2="{x0}" y2="{h - pad_b}" '
                 f'stroke="{P["border"]}" stroke-width="1" '
                 f'stroke-dasharray="3,3"/>')
    if y_lo < 0 < y_hi:
        y0 = pad_t + (1 - (0 - y_lo) / span) * inner_h
        parts.append(f'<line x1="{pad_l}" y1="{y0:.1f}" x2="{w - pad_r}" '
                     f'y2="{y0:.1f}" stroke="{P["border"]}" '
                     f'stroke-width="1"/>')
    for lbl, dp in (("-15%", -15.0), ("0", 0.0), ("+15%", 15.0)):
        x = pad_l + (dp + 15) / 30 * inner_w
        parts.append(f'<text x="{x:.1f}" y="{h - 10}" fill="{P["text_faint"]}" '
                     f'font-size="9" text-anchor="middle" '
                     f'font-family="JetBrains Mono,monospace">{lbl}</text>')
    for i, s in enumerate(drawable):
        color = _CURVE_COLORS[i % len(_CURVE_COLORS)]
        pts = " ".join(f"{x:.1f},{y:.1f}"
                       for x, y in (_xy(pt) for pt in s.curve))
        parts.append(f'<polyline points="{pts}" fill="none" '
                     f'stroke="{color}" stroke-width="2" opacity="0.9"/>')
        opt = next(pt for pt in s.curve
                   if pt.price_change_pct == s.optimal_price_change_pct)
        ox, oy = _xy(opt)
        parts.append(f'<circle cx="{ox:.1f}" cy="{oy:.1f}" r="4" '
                     f'fill="{color}"/>')
        ly = pad_t + 14 + i * 14
        name = s.segment if len(s.segment) <= 24 else s.segment[:23] + "…"
        parts.append(
            f'<rect x="{w - pad_r + 8}" y="{ly - 8}" width="10" height="3" '
            f'fill="{color}"/>'
            f'<text x="{w - pad_r + 22}" y="{ly - 3}" fill="{P["text_dim"]}" '
            f'font-size="9" font-family="JetBrains Mono,monospace">'
            f'{_html.escape(name)}</text>')
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" '
            f'xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>')


def _segments_table(segments) -> str:
    border = P["border"]; text_dim = P["text_dim"]
    cols = [("Segment", "left"), ("Elasticity", "right"),
            ("Optimal move", "right"), ("EBITDA gain ($)", "right"),
            ("Volume response", "right"), ("Pricing dynamics", "left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid '
        f'{border};font-size:10px;color:{text_dim};letter-spacing:0.05em">'
        f'{c}</th>' for c, a in cols)
    trs = []
    for s in segments:
        if s.price_locked:
            move = "LOCKED"
            move_tone = "dim"
            vol = "—"
        else:
            move = f"{s.optimal_price_change_pct:+.1f}%"
            move_tone = ("pos" if s.optimal_price_change_pct > 0
                         else "neg" if s.optimal_price_change_pct < 0
                         else "dim")
            opt = next(pt for pt in s.curve
                       if pt.price_change_pct == s.optimal_price_change_pct)
            vol = f"{opt.volume_change_pct:+.1f}%"
        trs.append("<tr>" + "".join([
            ck_data_cell(_html.escape(s.segment), mono=True, weight=600),
            ck_data_cell("—" if s.price_locked else f"{s.elasticity:.2f}",
                         align="right", mono=True),
            ck_data_cell(move, align="right", mono=True, weight=600,
                         tone=move_tone),
            ck_data_cell(f"${s.optimal_ebitda_gain_usd:,.2f}",
                         align="right", mono=True,
                         tone="pos" if s.optimal_ebitda_gain_usd > 0
                         else "dim"),
            ck_data_cell(vol, align="right", mono=True),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;'
            f'color:{text_dim};max-width:320px">{_html.escape(s.note)}</td>',
        ]) + "</tr>")
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody>'
            f'</table></div>')


def render_pricing_power(params: dict = None) -> str:
    params = params or {}
    from rcm_mc.data_public.pricing_power import (
        SECTORS, compute_pricing_power,
    )
    sector = params.get("sector", SECTORS[0]) or SECTORS[0]

    def _pf(name, default=0.0):
        try:
            return float(params.get(name, default))
        except (TypeError, ValueError):
            return default

    # Analyst-supplied segment: revenue in $M, margin and elasticity as
    # entered. Elasticity is clamped to [-5, 0] — positive demand
    # response to price is a data-entry error, not a Giffen good.
    custom_rev_m = max(_pf("custom_rev"), 0.0)
    custom_margin = min(max(_pf("custom_margin", 55.0), 1.0), 100.0)
    custom_eps = min(max(_pf("custom_eps", -0.8), -5.0), 0.0)
    extra = None
    if custom_rev_m > 0:
        from rcm_mc.data_public.pricing_power import SegmentPricing
        extra = SegmentPricing(
            "Custom segment (your inputs)", custom_rev_m * 1_000_000,
            custom_margin, custom_eps,
            f"Analyst inputs: {custom_margin:.1f}% contribution margin, "
            f"elasticity {custom_eps:.2f}")
    r = compute_pricing_power(sector=sector, extra_segment=extra)

    panel = P["panel"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]

    locked = [s for s in r.segments if s.price_locked]
    kpi_strip = (
        ck_kpi_block("Book revenue", f"${r.total_revenue_usd / 1e6:,.2f}M",
                     "", "") +
        ck_kpi_block("Blended elasticity", f"{r.blended_elasticity:.2f}",
                     "revenue-weighted", "") +
        ck_kpi_block("Pricing prize",
                     f"${r.portfolio_optimal_ebitda_gain_usd / 1e6:,.2f}M",
                     "EBITDA at segment-optimal moves", "") +
        ck_kpi_block("Segments", str(len(r.segments)), "", "") +
        ck_kpi_block("Rate-locked", str(len(locked)),
                     "no in-term price lever", "")
    )

    options = "".join(
        f'<option value="{_html.escape(s)}"'
        f'{" selected" if s == r.sector else ""}>{_html.escape(s)}</option>'
        for s in SECTORS)
    form = f"""
<form method="GET" action="/pricing-power" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Revenue book
    <select name="sector" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace">{options}</select>
  </label>
  <label style="font-size:11px;color:{text_dim}">+ Custom segment — revenue ($M)
    <input name="custom_rev" value="{custom_rev_m:g}" type="number" step="1" min="0"
      style="margin-left:4px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 6px;font-size:11px;font-family:JetBrains Mono,monospace;width:64px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">margin %
    <input name="custom_margin" value="{custom_margin:g}" type="number" step="5" min="1" max="100"
      style="margin-left:4px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 6px;font-size:11px;font-family:JetBrains Mono,monospace;width:58px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">elasticity
    <input name="custom_eps" value="{custom_eps:g}" type="number" step="0.1" max="0" min="-5"
      style="margin-left:4px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 6px;font-size:11px;font-family:JetBrains Mono,monospace;width:58px"/>
  </label>
  <button type="submit"
    style="background:{border};color:{text};border:1px solid {border};
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Load book</button>
  <a href="/pricing-power.xlsx?sector={_html.escape(_url_quote(r.sector))}" download
    style="background:#155752;color:#fffdf9;border:1px solid #155752;text-decoration:none;
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace"
    title="Per-segment price-move inputs with live elasticity math">Download model (.xlsx)</a>
</form>"""

    cell = (f"background:{panel};border:1px solid {border};padding:16px;"
            f"margin-bottom:16px")
    h3 = (f"font-size:11px;font-weight:600;letter-spacing:0.08em;"
          f"color:{text_dim};text-transform:uppercase;margin-bottom:10px")

    page_title = ck_page_title(
        "Pricing Power Analyzer",
        eyebrow="CDD · PRICING",
        meta=(f"{r.sector} · ${r.total_revenue_usd / 1e6:,.2f}M book · "
              f"blended elasticity {r.blended_elasticity:.2f} · "
              f"${r.portfolio_optimal_ebitda_gain_usd / 1e6:,.2f}M prize at "
              f"segment-optimal moves"),
    )

    headline = (f'<div style="{cell};border-left:3px solid {P["accent"]}">'
                f'<div style="{h3}">Pricing read</div>'
                f'<div style="font-size:14px;color:{text}">'
                f'{_html.escape(r.headline)} Optima at the ±15% window edge '
                f'mean the curve is still rising there — treat the window '
                f'as the credible bound, not the true optimum.</div></div>')

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {ck_illustrative_note("segment elasticities")}
  {form}
  <div class="ck-kpi-grid">{kpi_strip}</div>
  {headline}
  <div style="{cell}">
    <div style="{h3}">Price-response curves by segment</div>
    {_curves_svg(r.segments)}
  </div>
  <div style="{cell}">
    <div style="{h3}">Segment optima &amp; pricing dynamics</div>
    {_segments_table(r.segments)}
  </div>
</div>"""
    return chartis_shell(body, title="Pricing Power Analyzer",
                         active_nav="/pricing-power")


def pricing_power_xlsx(params: dict = None) -> bytes:
    """Workbook twin: per-segment price-move *inputs* (blue) with live
    volume / revenue / EBITDA-delta formulas, so the analyst can test
    moves in Excel instead of re-deriving the elasticity math. The page
    shows the window-optimal answer; the workbook lets them argue with
    it."""
    from rcm_mc.exports.xlsx_writer import F, Sheet, write_xlsx
    from rcm_mc.data_public.pricing_power import SECTORS, _BOOKS

    params = params or {}
    sector = params.get("sector", SECTORS[0]) or SECTORS[0]
    book = _BOOKS.get(sector) or _BOOKS[SECTORS[0]]

    r: list = []
    r.append([("PRICING POWER MODEL", "header")] + [("", "header")] * 7)
    r.append(["Blue cells = inputs (edit these). Black cells = live "
              "formulas. Volume response = (1+move)^elasticity."])
    r.append([f"Book: {sector}. Rate-locked segments carry no move "
              "input — administered pricing has no lever."])
    r.append([""])
    r.append([("Segment", "header"), ("Revenue ($)", "header"),
              ("Contribution margin", "header"), ("Elasticity", "header"),
              ("Price move", "header"), ("Volume response", "header"),
              ("Revenue Δ ($)", "header"), ("EBITDA Δ ($)", "header")])
    first = 6
    for i, seg in enumerate(book):
        n = first + i
        if seg.price_locked:
            r.append([seg.segment, (seg.revenue_usd, "input_money"),
                      (seg.contribution_margin_pct / 100.0, "input_pct"),
                      "—", "LOCKED", "—", (0, "money2"), (0, "money2")])
        else:
            r.append([
                seg.segment,
                (seg.revenue_usd, "input_money"),
                (seg.contribution_margin_pct / 100.0, "input_pct"),
                (seg.elasticity, "input_num"),
                (0.03, "input_pct"),
                (F(f"(1+E{n})^D{n}-1"), "pct"),
                (F(f"B{n}*(1+E{n})*(1+F{n})-B{n}"), "money2"),
                # EBITDA Δ = margin·volume effect + pure-margin price
                # component on the surviving volume.
                (F(f"B{n}*C{n}*F{n}+B{n}*(1+F{n})*E{n}"), "money2"),
            ])
    last = first + len(book) - 1
    r.append([("Total", "label"), (F(f"SUM(B{first}:B{last})"), "money2"),
              "", "", "", "",
              (F(f"SUM(G{first}:G{last})"), "money2"),
              (F(f"SUM(H{first}:H{last})"), "money2")])
    return write_xlsx([Sheet("Pricing Model", r,
                             col_widths=[36, 15, 18, 11, 11, 15, 14, 14])])
