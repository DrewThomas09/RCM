"""Sponsor × Sector Performance Heatmap — /sponsor-heatmap."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block
from rcm_mc.ui.chartis._helpers import render_page_explainer


def _tier_color(tier: str) -> str:
    if tier == "top quartile": return P["positive"]
    if tier == "above avg": return P["accent"]
    if tier == "avg": return P["text_dim"]
    if tier == "below avg": return P["warning"]
    return P["negative"]


def _cells_table(cells) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Sponsor","left"),("Sector","left"),("Deals","right"),
            ("Avg MOIC","right"),("Median MOIC","right"),("Avg IRR","right"),
            ("Total EV ($M)","right"),("Realized","right"),("Tier","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(cells[:50]):
        rb = panel_alt if i % 2 == 0 else bg
        tc = _tier_color(c.performance_tier)
        moic_c = pos if c.avg_moic >= 2.8 else (P["accent"] if c.avg_moic >= 2.0 else text_dim)
        cells_html = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.sponsor)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(c.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.deal_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c};font-weight:700">{c.avg_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.median_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.avg_irr * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${c.total_ev_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.realized_pct * 100:.0f}%</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.performance_tier)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells_html)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _profiles_table(profiles) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Sponsor","left"),("Deals","right"),("Avg MOIC","right"),("Avg IRR","right"),
            ("Median Hold","right"),("Total EV ($M)","right"),("Sectors","right"),
            ("Top Sector","left"),("Concentration","right"),("Realized","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(profiles):
        rb = panel_alt if i % 2 == 0 else bg
        moic_c = pos if p.avg_moic >= 2.8 else (acc if p.avg_moic >= 2.0 else text_dim)
        conc_c = P["warning"] if p.sector_concentration_pct >= 0.40 else text_dim
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(p.sponsor)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{p.total_deals}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c};font-weight:700">{p.avg_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{p.avg_irr * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.median_hold_years:.1f}y</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${p.total_ev_deployed_mm:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.sector_count}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(p.top_sector[:24])}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{conc_c}">{p.sector_concentration_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{p.realized_pct * 100:.0f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _leaders_table(leaders) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Sector","left"),("Top Sponsor","left"),("Top MOIC","right"),
            ("Top IRR","right"),("Deals","right"),("Runner Up","left"),("Runner MOIC","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, lead in enumerate(leaders[:40]):
        rb = panel_alt if i % 2 == 0 else bg
        moic_c = pos if lead.top_moic >= 2.8 else (acc if lead.top_moic >= 2.0 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(lead.sector)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(lead.top_sponsor)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c};font-weight:700">{lead.top_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{lead.top_irr * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{lead.deal_count}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(lead.runner_up)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{lead.runner_up_moic:.2f}x</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _vintage_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Sponsor","left"),("2016-2019 MOIC","right"),("2016-2019 Deals","right"),
            ("2020-2024 MOIC","right"),("2020-2024 Deals","right"),("Trend","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    trend_c = {"improving": pos, "stable": text_dim, "declining": neg}
    for i, v in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        tc = trend_c.get(v.trend, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(v.sponsor)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{v.vintage_2016_2019_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{v.vintage_2016_2019_deals}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{v.vintage_2020_2024_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{v.vintage_2020_2024_deals}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em">{_html.escape(v.trend)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _hold_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Hold Bucket","left"),("Deals","right"),("Avg MOIC","right"),
            ("Avg IRR","right"),("Best MOIC","right"),("Best Deal","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, h in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        moic_c = pos if h.avg_moic >= 2.4 else (acc if h.avg_moic >= 2.0 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(h.hold_bucket)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{h.deal_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c};font-weight:700">{h.avg_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{h.avg_irr * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{h.best_moic:.2f}x</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(h.best_deal)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _heatmap_svg(cells, top_sponsors, leaders) -> str:
    # Grid: top 12 sponsors (by avg moic) x top 12 sectors (by deal count in cells)
    if not cells: return ""
    top_sp_names = [p.sponsor for p in top_sponsors[:12]]
    sector_count: dict = {}
    for c in cells:
        sector_count[c.sector] = sector_count.get(c.sector, 0) + c.deal_count
    top_sectors = [s for s, _ in sorted(sector_count.items(), key=lambda x: x[1], reverse=True)[:12]]

    lookup = {(c.sponsor, c.sector): c for c in cells}

    cell_w, cell_h = 90, 22
    label_l = 150
    label_t = 85
    w = label_l + cell_w * len(top_sectors) + 20
    h = label_t + cell_h * len(top_sp_names) + 20
    bg = P["panel"]; bg_alt = P["panel_alt"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]

    elts = [f'<rect width="{w}" height="{h}" fill="{bg}"/>']
    # Column headers (sectors) — rotated
    for j, sect in enumerate(top_sectors):
        x = label_l + j * cell_w + cell_w / 2
        y = label_t - 5
        elts.append(
            f'<text x="{x}" y="{y}" fill="{text_dim}" font-size="9" text-anchor="end" '
            f'font-family="JetBrains Mono,monospace" transform="rotate(-45 {x} {y})">{_html.escape(sect[:22])}</text>'
        )
    # Row headers (sponsors)
    for i, sp in enumerate(top_sp_names):
        y = label_t + i * cell_h + cell_h * 0.7
        elts.append(
            f'<text x="{label_l - 8}" y="{y}" fill="{text_dim}" font-size="10" text-anchor="end" '
            f'font-family="JetBrains Mono,monospace">{_html.escape(sp[:18])}</text>'
        )
    # Cells
    for i, sp in enumerate(top_sp_names):
        for j, sect in enumerate(top_sectors):
            x = label_l + j * cell_w
            y = label_t + i * cell_h
            c = lookup.get((sp, sect))
            if c:
                color = _tier_color(c.performance_tier)
                elts.append(
                    f'<rect x="{x}" y="{y}" width="{cell_w - 1}" height="{cell_h - 1}" fill="{color}" opacity="0.6" stroke="{bg_alt}" stroke-width="0.5"/>'
                    f'<text x="{x + cell_w / 2}" y="{y + cell_h * 0.65}" fill="#fff" font-size="10" text-anchor="middle" '
                    f'font-family="JetBrains Mono,monospace" font-weight="700">{c.avg_moic:.2f}x</text>'
                )
            else:
                elts.append(f'<rect x="{x}" y="{y}" width="{cell_w - 1}" height="{cell_h - 1}" fill="{bg_alt}" stroke="{bg}" stroke-width="0.5"/>')
    elts.append(
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Sponsor × Sector MOIC Heatmap (avg across deals; green = top quartile, red = bottom)</text>'
    )
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'{"".join(elts)}</svg>')


def render_sponsor_heatmap(params: dict = None) -> str:
    params = params or {}

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    min_cell = _i("min_cell", 2)
    min_sponsor = _i("min_sponsor", 4)

    from rcm_mc.data_public.sponsor_heatmap import compute_sponsor_heatmap
    r = compute_sponsor_heatmap(
        min_deals_per_cell=min_cell, min_deals_per_sponsor=min_sponsor,
    )

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Total Sponsors", f"{r.total_sponsors:,}", "", "") +
        ck_kpi_block("Total Sectors", f"{r.total_sectors:,}", "", "") +
        ck_kpi_block("Matrix Cells", f"{len(r.matrix_cells):,}", "", "") +
        ck_kpi_block("Top Sponsors", f"{len(r.top_sponsors)}", "", "") +
        ck_kpi_block("Sector Leaders", f"{len(r.sector_leaders)}", "", "") +
        ck_kpi_block("Portfolio MOIC", f"{r.avg_portfolio_moic:.2f}x", "", "") +
        ck_kpi_block("Vintage Cuts", f"{len(r.vintage_cuts)}", "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    svg = _heatmap_svg(r.matrix_cells, r.top_sponsors, r.sector_leaders)
    cells_tbl = _cells_table(r.matrix_cells)
    profiles_tbl = _profiles_table(r.top_sponsors)
    leaders_tbl = _leaders_table(r.sector_leaders)
    vintage_tbl = _vintage_table(r.vintage_cuts)
    hold_tbl = _hold_table(r.hold_strat)

    form = f"""
<form method="GET" action="/sponsor-heatmap" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Min deals per cell<input name="min_cell" value="{min_cell}" type="number" step="1" min="1" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/></label>
  <label style="font-size:11px;color:{text_dim}">Min deals per sponsor<input name="min_sponsor" value="{min_sponsor}" type="number" step="1" min="1" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/></label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Sponsor × Sector Performance Heatmap</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">2-D performance grid — which sponsors win in which sectors · vintage &amp; hold cuts — {r.corpus_deal_count:,} normalized deals</p>
  </div>
  {form}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Sponsor × Sector MOIC Heatmap</div>{svg}</div>
  <div style="{cell}"><div style="{h3}">Sponsor × Sector Matrix Detail (top 50)</div>{cells_tbl}</div>
  <div style="{cell}"><div style="{h3}">Top Sponsor Profiles</div>{profiles_tbl}</div>
  <div style="{cell}"><div style="{h3}">Sector-Level Leaders</div>{leaders_tbl}</div>
  <div style="{cell}"><div style="{h3}">Vintage Cuts — 2016-2019 vs 2020-2024</div>{vintage_tbl}</div>
  <div style="{cell}"><div style="{h3}">Hold-Period Stratification</div>{hold_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Track-Record Thesis:</strong> {r.corpus_deal_count:,} normalized deals across {r.total_sponsors:,} unique sponsors and {r.total_sectors:,} sector strings produce {len(r.matrix_cells)} sponsor-sector cells with ≥2 deals.
    Portfolio-weighted average MOIC {r.avg_portfolio_moic:.2f}x. Use the heatmap to identify sponsor-sector pairs where a prior platform produced top-quartile results (green cells) — and where runner-up sponsors lost material value (red cells).
    Vintage cuts reveal which sponsors have maintained discipline as multiples have compressed post-2020. Long-hold (6+ years) deals consistently produce highest MOIC but depress IRR.
  </div>
</div>"""

    explainer = render_page_explainer(
        what=(
            "Sponsor × sector MOIC heatmap over the 655-deal corpus. "
            "Cells show average MOIC, median MOIC, IRR, total EV, and "
            "realized count for every sponsor-sector pair with at "
            "least two deals, colored by performance tier."
        ),
        source="data_public/sponsor_heatmap.py (sponsor × sector roll-up).",
        page_key="sponsor-heatmap",
    )
    return chartis_shell(explainer + body, "Sponsor Heatmap", active_nav="/sponsor-heatmap")
