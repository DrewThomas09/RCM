"""LP Portfolio Dashboard page — /lp-dashboard.

Fund-level KPIs (TVPI/DPI/RVPI, gross/net MOIC, IRR, loss rate),
vintage J-curve, sector exposure table, payer bucket analysis,
top/bottom performers. Partner-ready LP reporting view.
"""
from __future__ import annotations

import html as _html
from typing import Dict, List, Optional

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_kpi_block, ck_section_header,
    ck_fmt_num, ck_fmt_pct, ck_fmt_moic, ck_fmt_currency,
)


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def _vintage_moic_svg(rows) -> str:
    """Bar chart of median MOIC by vintage year."""
    if not rows:
        return ""
    w, h, pad_l, pad_b = 640, 200, 50, 40
    inner_w = w - pad_l - 20
    inner_h = h - pad_b - 20

    max_moic = max((r.median_moic for r in rows), default=3.0)
    max_moic = max(max_moic, 0.1) * 1.15

    bar_w = max(4, inner_w // len(rows) - 4)

    bars = []
    for i, r in enumerate(rows):
        bh = int(r.median_moic / max_moic * inner_h)
        x = pad_l + i * (inner_w // len(rows)) + 2
        y = (h - pad_b) - bh
        color = P["positive"] if r.median_moic >= 2.0 else (P["warning"] if r.median_moic >= 1.0 else P["negative"])
        bars.append(
            f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bh}" fill="{color}" opacity="0.85"/>'
            f'<text x="{x + bar_w//2}" y="{y - 4}" fill="{P["text_dim"]}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">{r.median_moic:.1f}x</text>'
            f'<text x="{x + bar_w//2}" y="{h - pad_b + 14}" fill="{P["text_faint"]}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">{r.year}</text>'
        )

    # y-axis
    ticks = []
    for v in [0, 1.0, 2.0, 3.0]:
        if v <= max_moic:
            yp = int((h - pad_b) - v / max_moic * inner_h)
            ticks.append(
                f'<line x1="{pad_l - 4}" y1="{yp}" x2="{w - 20}" y2="{yp}" stroke="{P["border"]}" stroke-width="1"/>'
                f'<text x="{pad_l - 8}" y="{yp + 4}" fill="{P["text_faint"]}" font-size="9" text-anchor="end" font-family="JetBrains Mono,monospace">{v:.1f}x</text>'
            )

    bg = P["panel"]
    border = P["border"]
    label = P["text_dim"]
    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(ticks)
        + "".join(bars)
        + f'<text x="{pad_l}" y="14" fill="{label}" font-size="10" font-family="{_SANS_LABEL}">Median MOIC by Vintage Year</text>'
        f'</svg>'
    )


def _tvpi_dpi_svg(rows) -> str:
    """Stacked bar: DPI (realized) + RVPI (unrealized) by vintage."""
    if not rows:
        return ""
    w, h, pad_l, pad_b = 640, 180, 50, 40
    inner_w = w - pad_l - 20
    inner_h = h - pad_b - 20

    max_tvpi = max((r.tvpi for r in rows), default=2.5)
    max_tvpi = max(max_tvpi, 0.1) * 1.15
    bar_w = max(4, inner_w // len(rows) - 4)

    bars = []
    for i, r in enumerate(rows):
        x = pad_l + i * (inner_w // len(rows)) + 2
        # DPI (realized, positive green)
        dpi_h = int(r.dpi / max_tvpi * inner_h)
        rvpi_h = int((r.tvpi - r.dpi) / max_tvpi * inner_h)
        y_dpi = (h - pad_b) - dpi_h
        y_rvpi = y_dpi - rvpi_h
        bars.append(
            f'<rect x="{x}" y="{y_dpi}" width="{bar_w}" height="{dpi_h}" fill="{P["positive"]}" opacity="0.85"/>'
            f'<rect x="{x}" y="{y_rvpi}" width="{bar_w}" height="{rvpi_h}" fill="{P["accent"]}" opacity="0.6"/>'
            f'<text x="{x + bar_w//2}" y="{h - pad_b + 14}" fill="{P["text_faint"]}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">{r.year}</text>'
        )

    legend_text = P["text_dim"]
    pos = P["positive"]
    acc = P["accent"]
    bg = P["panel"]
    border = P["border"]
    label = P["text_dim"]
    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(bars)
        + f'<rect x="{pad_l}" y="8" width="10" height="10" fill="{pos}"/>'
        f'<text x="{pad_l + 14}" y="17" fill="{legend_text}" font-size="9" font-family="JetBrains Mono,monospace">DPI (Realized)</text>'
        f'<rect x="{pad_l + 110}" y="8" width="10" height="10" fill="{acc}" opacity="0.7"/>'
        f'<text x="{pad_l + 124}" y="17" fill="{legend_text}" font-size="9" font-family="JetBrains Mono,monospace">RVPI (Unrealized)</text>'
        f'</svg>'
    )


_SANS_LABEL = "Inter,-apple-system,sans-serif"


def _sector_bar_svg(exposures) -> str:
    """Horizontal bar chart of sector EV concentration."""
    if not exposures:
        return ""
    top = exposures[:12]
    w, h = 500, max(180, len(top) * 24 + 30)
    pad_l, pad_r, pad_t, pad_b = 140, 20, 20, 10
    inner_w = w - pad_l - pad_r
    bar_h = 14
    row_h = 22

    max_pct = max((s.pct_of_portfolio for s in top), default=0.01)

    bars = []
    for i, s in enumerate(top):
        bw = int(s.pct_of_portfolio / max_pct * inner_w) if max_pct else 0
        y = pad_t + i * row_h
        color = P["accent"] if i % 2 == 0 else P["brand"] if hasattr(P, "brand") else "#2563eb"
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bar_h - 2}" fill="{P["text_dim"]}" font-size="9" text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(s.sector[:22])}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{bw}" height="{bar_h}" fill="{P["accent"]}" opacity="0.75"/>'
            f'<text x="{pad_l + bw + 4}" y="{y + bar_h - 2}" fill="{P["text_dim"]}" font-size="9" font-family="JetBrains Mono,monospace">{s.pct_of_portfolio*100:.1f}%</text>'
        )

    bg = P["panel"]
    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(bars)
        + f'</svg>'
    )


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def _vintage_table(rows) -> str:
    bg = P["panel"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]
    pos = P["positive"]
    neg = P["negative"]
    warn = P["warning"]

    header_cols = [
        ("Year", "left"), ("Deals", "right"), ("EV ($M)", "right"),
        ("Med MOIC", "right"), ("P25", "right"), ("P75", "right"),
        ("Med IRR", "right"), ("TVPI", "right"), ("DPI", "right"),
        ("Realized", "right"), ("Losses", "right"), ("Home Runs", "right"),
    ]
    ths = "".join(
        f'<th style="text-align:{align};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em;white-space:nowrap">{col}</th>'
        for col, align in header_cols
    )
    header = f'<thead><tr style="background:{bg}">{ths}</tr></thead>'

    trs = []
    for i, r in enumerate(rows):
        row_bg = panel_alt if i % 2 == 0 else bg
        moic_color = pos if r.median_moic >= 2.0 else (warn if r.median_moic >= 1.0 else neg)
        irr_color = pos if r.median_irr >= 0.20 else (warn if r.median_irr >= 0.10 else neg)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{r.year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{r.deal_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${r.total_ev_mm:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_color};font-weight:600">{r.median_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.p25_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.p75_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{irr_color}">{r.median_irr*100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{r.tvpi:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{r.dpi:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.realized_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg if r.loss_count else text_dim}">{r.loss_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos if r.home_run_count else text_dim}">{r.home_run_count}</td>',
        ]
        trs.append(f'<tr style="background:{row_bg}">{"".join(cells)}</tr>')

    body = f'<tbody>{"".join(trs)}</tbody>'
    return (
        f'<div style="overflow-x:auto;margin-top:12px">'
        f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'{header}{body}</table></div>'
    )


def _sector_table(exposures) -> str:
    bg = P["panel"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]
    pos = P["positive"]
    neg = P["negative"]
    warn = P["warning"]

    header_cols = [
        ("Sector", "left"), ("Deals", "right"), ("Total EV ($M)", "right"),
        ("% Portfolio", "right"), ("Median MOIC", "right"), ("Median IRR", "right"),
        ("Loss Rate", "right"), ("Home Run Rate", "right"),
    ]
    ths = "".join(
        f'<th style="text-align:{align};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{col}</th>'
        for col, align in header_cols
    )
    header = f'<thead><tr style="background:{bg}">{ths}</tr></thead>'

    trs = []
    for i, s in enumerate(exposures):
        row_bg = panel_alt if i % 2 == 0 else bg
        moic_color = pos if s.median_moic >= 2.0 else (warn if s.median_moic >= 1.0 else neg)
        loss_color = neg if s.loss_rate > 0.10 else (warn if s.loss_rate > 0.05 else text_dim)
        hr_color = pos if s.home_run_rate >= 0.15 else text_dim
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(s.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s.deal_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.total_ev_mm:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s.pct_of_portfolio*100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_color};font-weight:600">{s.median_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.median_irr*100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{loss_color}">{s.loss_rate*100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{hr_color}">{s.home_run_rate*100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{row_bg}">{"".join(cells)}</tr>')

    body = f'<tbody>{"".join(trs)}</tbody>'
    return (
        f'<div style="overflow-x:auto;margin-top:12px">'
        f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'{header}{body}</table></div>'
    )


def _payer_table(buckets) -> str:
    bg = P["panel"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]
    pos = P["positive"]
    warn = P["warning"]

    header_cols = [
        ("Payer Bucket", "left"), ("Deals", "right"), ("% Portfolio", "right"),
        ("Avg EV ($M)", "right"), ("Median MOIC", "right"), ("Median IRR", "right"),
    ]
    ths = "".join(
        f'<th style="text-align:{align};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{col}</th>'
        for col, align in header_cols
    )
    header = f'<thead><tr style="background:{bg}">{ths}</tr></thead>'
    trs = []
    for i, b in enumerate(buckets):
        row_bg = panel_alt if i % 2 == 0 else bg
        moic_color = pos if b.median_moic >= 2.0 else warn
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(b.label)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{b.deal_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{b.pct_of_portfolio*100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${b.avg_ev_mm:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_color};font-weight:600">{b.median_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{b.median_irr*100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{row_bg}">{"".join(cells)}</tr>')
    body = f'<tbody>{"".join(trs)}</tbody>'
    return (
        f'<div style="overflow-x:auto;margin-top:12px">'
        f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'{header}{body}</table></div>'
    )


def _performers_table(performers: List[dict], title: str, color: str) -> str:
    bg = P["panel"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]

    header_cols = [
        ("Company", "left"), ("Sector", "left"), ("Year", "right"),
        ("EV ($M)", "right"), ("Hold (yrs)", "right"), ("MOIC", "right"), ("IRR", "right"),
    ]
    ths = "".join(
        f'<th style="text-align:{align};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{col}</th>'
        for col, align in header_cols
    )
    header = f'<thead><tr style="background:{bg}">{ths}</tr></thead>'
    trs = []
    for i, p in enumerate(performers):
        row_bg = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(str(p.get("company","—")))}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(str(p.get("sector","—")))}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.get("year","—")}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${p.get("ev_mm",0):,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.get("hold_years",0):.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{color};font-weight:600">{p.get("moic",0):.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.get("irr",0)*100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{row_bg}">{"".join(cells)}</tr>')
    body = f'<tbody>{"".join(trs)}</tbody>'
    return (
        f'<div style="overflow-x:auto;margin-top:12px">'
        f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'{header}{body}</table></div>'
    )


# ---------------------------------------------------------------------------
# Page renderer
# ---------------------------------------------------------------------------

def render_lp_dashboard(params: dict = None) -> str:
    params = params or {}
    sector_filter = params.get("sector", "")
    vintage_from = int(params["vintage_from"]) if params.get("vintage_from", "").isdigit() else 0
    vintage_to = int(params["vintage_to"]) if params.get("vintage_to", "").isdigit() else 9999
    min_ev = float(params["min_ev"]) if params.get("min_ev") else 0.0

    from rcm_mc.data_public.lp_dashboard import compute_lp_dashboard
    result = compute_lp_dashboard(
        sector_filter=sector_filter,
        vintage_from=vintage_from,
        vintage_to=vintage_to,
        min_ev_mm=min_ev,
    )
    kpis = result.fund_kpis

    bg = P["bg"]
    panel = P["panel"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]
    text_faint = P["text_faint"]
    pos = P["positive"]
    neg = P["negative"]
    warn = P["warning"]
    acc = P["accent"]

    # KPI strip
    kpi_strip = (
        ck_kpi_block("Total Deals", str(kpis.total_deals), "", "") +
        ck_kpi_block("Total EV", f"${kpis.total_ev_deployed_mm:,.0f}M", "", "") +
        ck_kpi_block("Gross MOIC", f"{kpis.gross_moic:.2f}x", "", "") +
        ck_kpi_block("Net MOIC", f"{kpis.net_moic:.2f}x", "", "") +
        ck_kpi_block("TVPI", f"{kpis.tvpi:.2f}x", "", "") +
        ck_kpi_block("DPI", f"{kpis.dpi:.2f}x", "", "") +
        ck_kpi_block("Gross IRR", f"{kpis.irr_gross*100:.1f}%", "", "") +
        ck_kpi_block("Net IRR", f"{kpis.irr_net*100:.1f}%", "", "")
    )
    kpi_strip2 = (
        ck_kpi_block("Realized", str(kpis.realized_deals), "", "") +
        ck_kpi_block("Active", str(kpis.active_deals), "", "") +
        ck_kpi_block("Avg Hold", f"{kpis.avg_hold_years:.1f} yrs", "", "") +
        ck_kpi_block("Loss Rate", f"{kpis.loss_rate*100:.1f}%", "", "") +
        ck_kpi_block("Home Run Rate", f"{kpis.home_run_rate*100:.1f}%", "", "") +
        ck_kpi_block("% Commercial", f"{kpis.pct_commercial_payer*100:.1f}%", "", "") +
        ck_kpi_block("Median EV", f"${kpis.median_ev_mm:,.0f}M", "", "") +
        ck_kpi_block("Corpus Deals", str(result.corpus_deal_count), "", "")
    )

    vintage_svg = _vintage_moic_svg(result.vintage_rows)
    tvpi_svg = _tvpi_dpi_svg(result.vintage_rows)
    sector_svg = _sector_bar_svg(result.sector_exposures)
    vintage_tbl = _vintage_table(result.vintage_rows)
    sector_tbl = _sector_table(result.sector_exposures)
    payer_tbl = _payer_table(result.payer_buckets)
    top_tbl = _performers_table(result.top_performers, "Top Performers", pos)
    bot_tbl = _performers_table(result.bottom_performers, "Bottom Performers", neg)

    # Filter form
    filter_form = f"""
<form method="GET" action="/lp-dashboard" style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector_filter)}" placeholder="All"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:140px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Vintage From
    <input name="vintage_from" value="{vintage_from if vintage_from else ''}" placeholder="2015"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Vintage To
    <input name="vintage_to" value="{vintage_to if vintage_to < 9999 else ''}" placeholder="2024"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Min EV ($M)
    <input name="min_ev" value="{min_ev if min_ev else ''}" placeholder="0"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  <button type="submit"
    style="background:{border};color:{text};border:1px solid {border};
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">
    Filter
  </button>
</form>"""

    cell_style = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3_style = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">

  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">LP Portfolio Dashboard</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Fund-level KPIs, vintage curves, and sector exposure — {result.corpus_deal_count:,} corpus deals</p>
  </div>

  {filter_form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip2}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell_style}">
      <div style="{h3_style}">Median MOIC by Vintage</div>
      {vintage_svg}
    </div>
    <div style="{cell_style}">
      <div style="{h3_style}">TVPI / DPI Stacking by Vintage</div>
      {tvpi_svg}
    </div>
  </div>

  <div style="display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell_style}">
      <div style="{h3_style}">Vintage Performance Detail</div>
      {vintage_tbl}
    </div>
    <div style="{cell_style}">
      <div style="{h3_style}">Sector Concentration</div>
      {sector_svg}
    </div>
  </div>

  <div style="{cell_style}">
    <div style="{h3_style}">Sector Exposure ({len(result.sector_exposures)} sectors)</div>
    {sector_tbl}
  </div>

  <div style="{cell_style}">
    <div style="{h3_style}">Payer Mix Bucket Analysis</div>
    {payer_tbl}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell_style}">
      <div style="{h3_style}">Top 10 Performers (by MOIC)</div>
      {top_tbl}
    </div>
    <div style="{cell_style}">
      <div style="{h3_style}">Bottom 10 Performers (by MOIC)</div>
      {bot_tbl}
    </div>
  </div>

</div>"""

    return chartis_shell(body, "LP Portfolio Dashboard", active_nav="/lp-dashboard")
