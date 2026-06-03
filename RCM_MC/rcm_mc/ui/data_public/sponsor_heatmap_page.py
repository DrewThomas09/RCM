"""Sponsor × Sector Performance Heatmap — /sponsor-heatmap."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_data_cell, ck_kpi_block, ck_paired_block, ck_page_title,
    ck_bar_row)


def _profiles_chart(items):
    """Summary chart — top sponsors by avg MOIC (tone by avg IRR)."""
    def _tone(p):
        if p.avg_irr >= 0.20: return "positive"
        if p.avg_irr >= 0.15: return "teal"
        return "warning"
    top = sorted(items, key=lambda p: p.avg_moic, reverse=True)
    mx = max((p.avg_moic for p in top), default=0.0) or 1.0
    rows = [ck_bar_row(f"{p.sponsor}",
            f"{p.avg_moic:.2f}x · {p.avg_irr * 100:.0f}% IRR · {p.total_deals} deals",
            p.avg_moic / mx * 100.0, tone=_tone(p)) for p in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = avg MOIC vs top sponsor '
            '· value = avg MOIC + IRR + deal count · tone = avg IRR</div></div>')


def _leaders_paired_rows(leaders) -> tuple:
    """Sector-leaders data for the heatmap's paired dataset.

    Returns ``(headers, rows, hot_rows)`` for ``ck_paired_block``.
    Each row is one sector with its top sponsor + runner-up — the
    interpretation of the bright cells the heatmap shows. ``leaders``
    arrives sorted (by top-sponsor MOIC desc, per compute_sponsor_heatmap),
    so ``hot_rows=[0]`` highlights the best sector-leader pair.
    Caps at 20 rows to match the right-side width of the paired block.
    """
    headers = [
        "Sector", "Top Sponsor", "Top MOIC", "Top IRR",
        "Deals", "Runner Up", "Runner MOIC",
    ]
    rows: list = [
        [
            ld.sector,
            ld.top_sponsor,
            f"{ld.top_moic:.2f}x",
            f"{ld.top_irr * 100:.1f}%",
            str(ld.deal_count),
            ld.runner_up,
            f"{ld.runner_up_moic:.2f}x",
        ]
        for ld in leaders[:20]
    ]
    return headers, rows, ([0] if rows else [])
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
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(cells[:50]):
        rb = panel_alt if i % 2 == 0 else bg
        tc = _tier_color(c.performance_tier)
        moic_c = pos if c.avg_moic >= 2.8 else (P["accent"] if c.avg_moic >= 2.0 else text_dim)
        cells_html = [
            f'{ck_data_cell(f"""{_html.escape(c.sponsor)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(c.sector)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{c.deal_count}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c};font-weight:700">{c.avg_moic:.2f}x</td>',
            f'{ck_data_cell(f"""{c.median_moic:.2f}x""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{c.avg_irr * 100:.1f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${c.total_ev_mm:,.1f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{c.realized_pct * 100:.0f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.performance_tier)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells_html)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _profiles_table(profiles) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Sponsor","left"),("Deals","right"),("Avg MOIC","right"),("Avg IRR","right"),
            ("Median Hold","right"),("Total EV ($M)","right"),("Sectors","right"),
            ("Top Sector","left"),("Concentration","right"),("Realized","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(profiles):
        rb = panel_alt if i % 2 == 0 else bg
        moic_c = pos if p.avg_moic >= 2.8 else (acc if p.avg_moic >= 2.0 else text_dim)
        conc_c = P["warning"] if p.sector_concentration_pct >= 0.40 else text_dim
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.sponsor)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{p.total_deals}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c};font-weight:700">{p.avg_moic:.2f}x</td>',
            f'{ck_data_cell(f"""{p.avg_irr * 100:.1f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{p.median_hold_years:.1f}y""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${p.total_ev_deployed_mm:,.0f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{p.sector_count}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(p.top_sector[:24])}""", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{conc_c}">{p.sector_concentration_pct * 100:.0f}%</td>',
            f'{ck_data_cell(f"""{p.realized_pct * 100:.0f}%""", align="right", mono=True)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _vintage_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Sponsor","left"),("2016-2019 MOIC","right"),("2016-2019 Deals","right"),
            ("2020-2024 MOIC","right"),("2020-2024 Deals","right"),("Trend","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    trend_c = {"improving": pos, "stable": text_dim, "declining": neg}
    for i, v in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        tc = trend_c.get(v.trend, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(v.sponsor)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{v.vintage_2016_2019_moic:.2f}x""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{v.vintage_2016_2019_deals}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{v.vintage_2020_2024_moic:.2f}x""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{v.vintage_2020_2024_deals}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em">{_html.escape(v.trend)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _hold_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Hold Bucket","left"),("Deals","right"),("Avg MOIC","right"),
            ("Avg IRR","right"),("Best MOIC","right"),("Best Deal","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, h in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        moic_c = pos if h.avg_moic >= 2.4 else (acc if h.avg_moic >= 2.0 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(h.hold_bucket)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{h.deal_count}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c};font-weight:700">{h.avg_moic:.2f}x</td>',
            f'{ck_data_cell(f"""{h.avg_irr * 100:.1f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{h.best_moic:.2f}x""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""{_html.escape(h.best_deal)}""", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


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
    # Render wide (was capped at the intrinsic width inside a half-width paired
    # column, which scaled the text down to unreadable). Full-width up to 1040px
    # makes the cells and labels legible.
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:1040px;min-width:min(100%,640px)" xmlns="http://www.w3.org/2000/svg">'
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
    profiles_chart = _profiles_chart(r.top_sponsors)
    vintage_tbl = _vintage_table(r.vintage_cuts)
    hold_tbl = _hold_table(r.hold_strat)

    # Signature paired viz+dataset block from the handoff: the
    # sponsor × sector heatmap on the left, the per-sector leaders
    # (top sponsor + runner-up) on the right, one outer rule. The
    # leaders are the literal interpretation of the heatmap's bright
    # cells — the pair turns "look at this color grid" into "and here
    # is who's winning each row."
    heatmap_viz = (
        f'<div style="font-size:9px;color:{P["text_dim"]};'
        f'font-family:JetBrains Mono,monospace;letter-spacing:0.1em;'
        f'text-transform:uppercase;font-weight:700;margin-bottom:8px;">'
        'Sponsor &times; sector MOIC heatmap</div>'
        f'{svg}'
    )
    lead_headers, lead_rows, lead_hot = _leaders_paired_rows(r.sector_leaders)
    # Heatmap renders FULL WIDTH (below), not squeezed into ck_paired_block's
    # 1.4fr viz column where the viewBox scaled the labels to unreadable. The
    # sector-leaders interpretation table gets its own full-width panel.
    def _ld_cell(c, i):
        return ck_data_cell(str(c), mono=True, align=("left" if i == 0 else "right"),
                            weight=(600 if i == 0 else 400), tone=("" if i == 0 else "dim"))
    _ld_ths = "".join(
        ck_data_cell(h, align=("left" if i == 0 else "right"), is_header=True)
        for i, h in enumerate(lead_headers))
    _ld_trs = "".join(
        f'<tr>{"".join(_ld_cell(c, i) for i, c in enumerate(row))}</tr>'
        for row in lead_rows)
    leaders_tbl = (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{_ld_ths}</tr></thead><tbody>{_ld_trs}</tbody></table></div>')

    form = f"""
<form method="GET" action="/sponsor-heatmap" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Min deals per cell<input name="min_cell" value="{min_cell}" type="number" step="1" min="1" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/></label>
  <label style="font-size:11px;color:{text_dim}">Min deals per sponsor<input name="min_sponsor" value="{min_sponsor}" type="number" step="1" min="1" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/></label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    page_title = ck_page_title(
        "Sponsor × Sector Performance Heatmap",
        eyebrow="SPONSOR HEATMAP",
        meta=f"""2-D performance grid — which sponsors win in which sectors · vintage &amp; hold cuts — {r.corpus_deal_count:,} normalized deals""",
    )
    
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {form}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Sponsor × Sector MOIC grid — green = top-quartile</div>
    <div style="overflow-x:auto">{heatmap_viz}</div></div>
  <div style="{cell}"><div style="{h3}">Sector leaders — top sponsor + runner-up</div>{leaders_tbl}</div>
  <div style="{cell}"><div style="{h3}">Sponsor × Sector Matrix Detail (top 50)</div>{cells_tbl}</div>
  <div style="{cell}"><div style="{h3}">Top Sponsor Profiles</div>{profiles_chart}{profiles_tbl}</div>
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
            "Sponsor × sector MOIC heatmap over the deal corpus. "
            "Cells show average MOIC, median MOIC, IRR, total EV, and "
            "realized count for every sponsor-sector pair with at "
            "least two deals, colored by performance tier."
        ),
        source="data_public/sponsor_heatmap.py (sponsor × sector roll-up).",
        page_key="sponsor-heatmap",
    )
    from rcm_mc.ui._chartis_kit import ck_illustrative_note as _ckn
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(explainer + _ckn("sponsor figures (illustrative seed corpus)") + body, "Sponsor Heatmap", active_nav="/sponsor-heatmap",
        editorial_intro={
            "eyebrow": "SPONSOR HEATMAP",
            "headline": "What the sponsor heatmap page reveals on this deal.",
            "italic_word": "reveals",
        })
