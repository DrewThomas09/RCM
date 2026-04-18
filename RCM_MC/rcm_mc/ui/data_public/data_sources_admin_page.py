"""Data Sources Admin page — /admin/data-sources.

Inventory of corpus seed files, CMS public datasets, scrapers, and their status.
Shows coverage by sector/year, record counts, freshness, and scraper availability.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_kpi_block, ck_section_header,
)


def _status_badge(status: str) -> str:
    colors = {
        "active": P["positive"],
        "available": P["positive"],
        "stale": P["warning"],
        "disabled": P["text_faint"],
        "error": P["negative"],
        "import_error": P["negative"],
        "pending": P["warning"],
    }
    color = colors.get(status, P["text_dim"])
    return (
        f'<span style="display:inline-block;padding:2px 8px;font-size:10px;'
        f'font-family:JetBrains Mono,monospace;color:{color};'
        f'border:1px solid {color};border-radius:2px;text-transform:uppercase;'
        f'letter-spacing:0.06em">{_html.escape(status)}</span>'
    )


def _sources_table(sources) -> str:
    bg = P["panel"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]
    acc = P["accent"]

    type_colors = {
        "corpus_seed": "#8b5cf6",
        "cms_public": P["accent"],
        "scraper": P["warning"],
        "manual": P["text_faint"],
    }

    header_cols = [
        ("Source", "left"), ("Type", "left"), ("Records", "right"),
        ("Last Updated", "right"), ("Status", "left"), ("Coverage", "left"),
    ]
    ths = "".join(
        f'<th style="text-align:{align};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em;white-space:nowrap">{col}</th>'
        for col, align in header_cols
    )
    header = f'<thead><tr style="background:{bg}">{ths}</tr></thead>'

    trs = []
    for i, s in enumerate(sources):
        row_bg = panel_alt if i % 2 == 0 else bg
        type_color = type_colors.get(s.source_type, text_dim)
        rec_str = f"{s.record_count:,}" if s.record_count > 0 else "—"
        name_cell = (
            f'<a href="{_html.escape(s.url)}" target="_blank" style="color:{acc};text-decoration:none">'
            f'{_html.escape(s.name)}</a>'
            if s.url else _html.escape(s.name)
        )
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{name_cell}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;font-family:JetBrains Mono,monospace;color:{type_color}">{_html.escape(s.source_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{rec_str}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(s.last_updated)}</td>',
            f'<td style="text-align:left;padding:5px 10px">{_status_badge(s.status)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:280px">{_html.escape(s.coverage_notes)}</td>',
        ]
        trs.append(f'<tr style="background:{row_bg}">{"".join(cells)}</tr>')

    body = f'<tbody>{"".join(trs)}</tbody>'
    return (
        f'<div style="overflow-x:auto;margin-top:12px">'
        f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'{header}{body}</table></div>'
    )


def _scraper_table(scrapers) -> str:
    bg = P["panel"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]

    header_cols = [
        ("Scraper", "left"), ("Module", "left"), ("Status", "left"),
        ("Last Run", "right"), ("Error", "left"),
    ]
    ths = "".join(
        f'<th style="text-align:{align};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{col}</th>'
        for col, align in header_cols
    )
    header = f'<thead><tr style="background:{bg}">{ths}</tr></thead>'

    trs = []
    for i, s in enumerate(scrapers):
        row_bg = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(s.name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(s.module)}</td>',
            f'<td style="text-align:left;padding:5px 10px">{_status_badge(s.status)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(s.last_run)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{P["negative"] if s.error_msg else text_dim}">{_html.escape(s.error_msg) if s.error_msg else "—"}</td>',
        ]
        trs.append(f'<tr style="background:{row_bg}">{"".join(cells)}</tr>')

    body = f'<tbody>{"".join(trs)}</tbody>'
    return (
        f'<div style="overflow-x:auto;margin-top:12px">'
        f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'{header}{body}</table></div>'
    )


def _sector_coverage_svg(by_sector: dict) -> str:
    """Top-20 sector horizontal bar."""
    if not by_sector:
        return ""
    top = list(by_sector.items())[:15]
    max_count = max(v for _, v in top) if top else 1
    w, h = 480, max(220, len(top) * 22 + 30)
    pad_l, pad_r, pad_t = 160, 50, 20
    inner_w = w - pad_l - pad_r
    bar_h = 13
    row_h = 20

    bg = P["panel"]
    acc = P["accent"]
    text_dim = P["text_dim"]
    text_faint = P["text_faint"]

    bars = []
    for i, (sector, count) in enumerate(top):
        bw = int(count / max_count * inner_w)
        y = pad_t + i * row_h
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bar_h - 1}" fill="{text_dim}" font-size="9" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(sector[:24])}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{bw}" height="{bar_h}" fill="{acc}" opacity="0.7"/>'
            f'<text x="{pad_l + bw + 4}" y="{y + bar_h - 1}" fill="{text_faint}" font-size="9" '
            f'font-family="JetBrains Mono,monospace">{count}</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(bars)
        + f'</svg>'
    )


def _year_coverage_svg(by_year: dict) -> str:
    """Deal count by year bar chart."""
    if not by_year:
        return ""
    items = sorted(by_year.items())
    max_count = max(v for _, v in items) if items else 1
    w, h, pad_l, pad_b = 480, 160, 40, 30
    inner_w = w - pad_l - 20
    inner_h = h - pad_b - 20
    bar_w = max(6, inner_w // len(items) - 3)

    bg = P["panel"]
    pos = P["positive"]
    text_faint = P["text_faint"]
    border = P["border"]

    bars = []
    for i, (yr, count) in enumerate(items):
        bh = int(count / max_count * inner_h)
        x = pad_l + i * (inner_w // len(items)) + 1
        y = (h - pad_b) - bh
        bars.append(
            f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bh}" fill="{pos}" opacity="0.75"/>'
            f'<text x="{x + bar_w//2}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="8" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{yr}</text>'
        )

    ticks = []
    for v in [0, max_count // 2, max_count]:
        if v >= 0:
            yp = int((h - pad_b) - v / max_count * inner_h)
            ticks.append(
                f'<line x1="{pad_l - 4}" y1="{yp}" x2="{w - 20}" y2="{yp}" stroke="{border}" stroke-width="1"/>'
                f'<text x="{pad_l - 6}" y="{yp + 3}" fill="{text_faint}" font-size="8" text-anchor="end" '
                f'font-family="JetBrains Mono,monospace">{v}</text>'
            )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(ticks) + "".join(bars)
        + f'</svg>'
    )


def render_data_sources_admin() -> str:
    from rcm_mc.data_public.data_sources_admin import compute_data_sources_admin
    result = compute_data_sources_admin()
    cov = result.corpus_coverage

    bg = P["bg"]
    panel = P["panel"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]
    text_faint = P["text_faint"]

    kpi_strip = (
        ck_kpi_block("Corpus Deals", str(result.total_seed_deals), "", "") +
        ck_kpi_block("Seed Files", str(result.seed_file_count), "", "") +
        ck_kpi_block("Sectors", str(cov.sector_count), "", "") +
        ck_kpi_block("Year Range", f"{cov.year_range[0]}–{cov.year_range[1]}", "", "") +
        ck_kpi_block("Avg Deal EV", f"${cov.avg_ev_mm:,.0f}M", "", "") +
        ck_kpi_block("Median MOIC", f"{cov.median_moic:.2f}x", "", "") +
        ck_kpi_block("Data Sources", str(len(result.data_sources)), "", "") +
        ck_kpi_block("Scrapers", str(len(result.scraper_statuses)), "", "")
    )

    sector_svg = _sector_coverage_svg(cov.by_sector)
    year_svg = _year_coverage_svg(cov.by_year)
    sources_tbl = _sources_table(result.data_sources)
    scrapers_tbl = _scraper_table(result.scraper_statuses)

    cell_style = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3_style = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">

  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Data Sources Admin</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      Corpus inventory, CMS public datasets, scraper status — {result.total_seed_deals:,} deals across {cov.sector_count} sectors
    </p>
  </div>

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell_style}">
      <div style="{h3_style}">Corpus Coverage by Sector (Top 15)</div>
      {sector_svg}
    </div>
    <div style="{cell_style}">
      <div style="{h3_style}">Deal Count by Vintage Year</div>
      {year_svg}
    </div>
  </div>

  <div style="{cell_style}">
    <div style="{h3_style}">Data Source Inventory ({len(result.data_sources)} sources)</div>
    {sources_tbl}
  </div>

  <div style="{cell_style}">
    <div style="{h3_style}">Scraper Module Status</div>
    {scrapers_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {P['warning']};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Corpus Note</strong> — All deal data is synthetic and constructed from
    healthcare PE market priors for diligence modeling purposes. CMS public datasets listed above are
    real and available for integration. Scrapers require separate configuration.
  </div>

</div>"""

    return chartis_shell(body, "Data Sources Admin", active_nav="/admin/data-sources")
