"""Geographic Market Analyzer page — /geo-market.

CBSA-level white-space scoring, competitive density, demographic/economic overlay,
market entry scenarios.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_value_anchor, ck_scatter, ck_illustrative_note


def _markets_scatter(items):
    """Quadrant — 5yr growth vs white-space score per CBSA, so high-growth
    high-whitespace markets (upper-right) are the entry priority."""
    import statistics
    pts, xs, ys = [], [], []
    for m in items:
        x = m.growth_5yr_pct * 100.0
        t = (m.tier or "").lower()
        tn = ('positive' if 'priority' in t else 'warning' if 'watch' in t else 'navy')
        pts.append((x, m.white_space_score, m.cbsa, tn)); xs.append(x); ys.append(m.white_space_score)
    return ck_scatter(
        pts, x_label='5-yr growth %', y_label='White-space score',
        x_ref=(statistics.median(xs) if xs else None), y_ref=(statistics.median(ys) if ys else None),
        caption='Each dot = a CBSA · upper-right = high growth + high white-space (entry priority) · tone = tier',
    )


def _tier_distribution_svg(priority: int, watch: int, secondary: int, avoid: int) -> str:
    w, h = 540, 80
    pad_l, pad_r, pad_t = 20, 20, 30
    inner_w = w - pad_l - pad_r
    bar_h = 28

    total = priority + watch + secondary + avoid or 1

    bg = P["panel"]; text_dim = P["text_dim"]; text = P["text"]

    segments = [
        ("Priority", priority, P["positive"]),
        ("Watch", watch, P["accent"]),
        ("Secondary", secondary, P["warning"]),
        ("Avoid", avoid, P["negative"]),
    ]

    segs = []
    x = pad_l
    for label, count, color in segments:
        seg_w = count / total * inner_w
        if seg_w < 1:
            continue
        segs.append(
            f'<rect x="{x:.1f}" y="{pad_t}" width="{seg_w:.1f}" height="{bar_h}" fill="{color}" opacity="0.88"/>'
        )
        if seg_w > 60:
            segs.append(
                f'<text x="{x + seg_w / 2:.1f}" y="{pad_t + bar_h / 2 + 4}" fill="{text}" font-size="10" '
                f'text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">{label}: {count}</text>'
            )
        x += seg_w

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(segs) +
        f'<text x="{pad_l}" y="18" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Market Tier Distribution ({total} CBSAs)</text>'
        f'</svg>'
    )


def _scatter_svg(markets) -> str:
    """Scatter: X = growth, Y = white-space score; size = population, color = tier."""
    if not markets:
        return ""
    w, h = 560, 280
    pad_l, pad_r, pad_t, pad_b = 45, 30, 25, 35
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    max_growth = max(m.growth_5yr_pct for m in markets)
    min_growth = min(m.growth_5yr_pct for m in markets)
    g_range = max_growth - min_growth or 1
    max_pop = max(m.population_k for m in markets) or 1

    bg = P["panel"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]
    tier_colors = {"Priority": P["positive"], "Watch": P["accent"], "Secondary": P["warning"], "Avoid": P["negative"]}

    dots = []
    for m in markets:
        x = pad_l + (m.growth_5yr_pct - min_growth) / g_range * inner_w
        y = (h - pad_b) - (m.white_space_score / 100) * inner_h
        r = 3 + (m.population_k / max_pop) * 10
        color = tier_colors.get(m.tier, text_dim)
        dots.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{color}" opacity="0.7" stroke="{P["text"]}" stroke-width="0.5"/>'
        )

    # Grid + labels
    grid = []
    for pct in [20, 40, 60, 80]:
        yp = (h - pad_b) - (pct / 100) * inner_h
        grid.append(
            f'<line x1="{pad_l}" y1="{yp:.1f}" x2="{w - pad_r}" y2="{yp:.1f}" stroke="{border}" stroke-width="0.5" opacity="0.5"/>'
            f'<text x="{pad_l - 4}" y="{yp + 3:.1f}" fill="{text_faint}" font-size="9" text-anchor="end" '
            f'font-family="JetBrains Mono,monospace">{pct}</text>'
        )

    # X-axis labels
    x_labels = []
    for g in [0.0, 0.05, 0.10, 0.15]:
        if min_growth <= g <= max_growth:
            x = pad_l + (g - min_growth) / g_range * inner_w
            x_labels.append(
                f'<text x="{x:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" '
                f'text-anchor="middle" font-family="JetBrains Mono,monospace">{g * 100:.0f}%</text>'
            )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(grid) + "".join(x_labels) + "".join(dots) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">5-yr Growth × White-Space Score (bubble = pop)</text>'
        f'<text x="{pad_l}" y="{h - 5}" fill="{text_faint}" font-size="9" font-family="Inter,sans-serif">5-yr Growth →</text>'
        f'</svg>'
    )


def _markets_table(markets) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    tier_colors = {"Priority": P["positive"], "Watch": P["accent"], "Secondary": P["warning"], "Avoid": P["negative"]}
    cols = [("CBSA","left"),("Pop (K)","right"),("65+%","right"),("Income ($K)","right"),
            ("PCP/1K","right"),("HHI","right"),("Comm %","right"),("Growth 5yr","right"),
            ("Score","right"),("Tier","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, m in enumerate(markets):
        rb = panel_alt if i % 2 == 0 else bg
        tc = tier_colors.get(m.tier, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(m.cbsa)}""", mono=True)}',
            f'{ck_data_cell(f"""{m.population_k:,.0f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{m.pct_65plus:.1f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${m.median_income_k:.0f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{m.pcp_per_1k:.1f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{m.hhi:,}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{m.comm_pct * 100:.0f}%""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"] if m.growth_5yr_pct >= 0.05 else (P["warning"] if m.growth_5yr_pct >= 0.02 else P["negative"])}">{m.growth_5yr_pct * 100:+.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{tc};font-weight:600">{m.white_space_score:.1f}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{m.tier}</span>""")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _components_table(components) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Dimension","left"),("Avg Value","right"),("Score","right"),
            ("Weight","right"),("Contribution","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, c in enumerate(components):
        rb = panel_alt if i % 2 == 0 else bg
        # Format value based on dimension
        fmt_val = f"{c.value:,.2f}" if isinstance(c.value, float) else f"{c.value:,}"
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.dimension)}""", mono=True)}',
            f'{ck_data_cell(f"""{fmt_val}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{c.normalized_score:.0f}""", align="right", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{c.weight * 100:.0f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{c.contribution:.1f}""", align="right", mono=True, tone="pos", weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _scenarios_table(scenarios) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("CBSA","left"),("Strategy","left"),("Y1 Rev","right"),("Y3 Rev","right"),
            ("Y5 Rev","right"),("CapEx","right"),("Payback (yrs)","right"),("Expected MOIC","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(scenarios):
        rb = panel_alt if i % 2 == 0 else bg
        moic_c = pos if s.expected_moic >= 2.5 else P["warning"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text}">{_html.escape(s.cbsa[:34])}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.entry_strategy)}</td>',
            f'{ck_data_cell(f"""${s.year1_revenue_mm:,.2f}M""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${s.year3_revenue_mm:,.2f}M""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${s.year5_revenue_mm:,.2f}M""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${s.capex_mm:,.2f}M</td>',
            f'{ck_data_cell(f"""{s.payback_years:.1f}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c};font-weight:600">{s.expected_moic:.2f}x</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _tiers_table(tiers) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    tier_colors = {"Priority": P["positive"], "Watch": P["accent"], "Secondary": P["warning"], "Avoid": P["negative"]}
    cols = [("Tier","left"),("# CBSAs","right"),("Avg Pop (K)","right"),
            ("Avg HHI","right"),("Avg Growth","right"),("Recommended Action","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, t in enumerate(tiers):
        rb = panel_alt if i % 2 == 0 else bg
        tc = tier_colors.get(t.tier, text_dim)
        cells = [
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{t.tier}</span>""")}',
            f'{ck_data_cell(f"""{t.cbsa_count}""", align="right", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{t.avg_population_k:,.0f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{t.avg_hhi:,}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{t.avg_growth * 100:+.1f}%""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(t.recommended_action)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_geo_market(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Physician Services") or "Physician Services"

    from rcm_mc.data_public.geo_market import compute_geo_market
    r = compute_geo_market(sector=sector)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    top_market = r.markets[0] if r.markets else None
    top_name = top_market.cbsa.split(",")[0] if top_market else "—"
    top_score = top_market.white_space_score if top_market else 0

    kpi_strip = (
        ck_kpi_block("CBSAs Analyzed", str(len(r.markets)), "", "") +
        ck_kpi_block("Priority Markets", str(r.priority_markets), "", "") +
        ck_kpi_block("Watch Markets", str(r.watch_markets), "", "") +
        ck_kpi_block("Secondary", str(r.secondary_markets), "", "") +
        ck_kpi_block("Addressable Pop", f"{r.total_addressable_pop_mm:,.1f}M", "", "") +
        ck_kpi_block("Top Market", top_name[:16], f"{top_score:.0f}", "") +
        ck_kpi_block("Sector", sector, "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    dist_svg = _tier_distribution_svg(r.priority_markets, r.watch_markets, r.secondary_markets, r.avoid_markets)
    scatter_svg = _scatter_svg(r.markets)
    markets_tbl = _markets_table(r.markets)
    markets_scatter = _markets_scatter(r.markets)
    value_anchor = ck_value_anchor(
        "Geographic Priority",
        f"{r.priority_markets} priority markets",
        delta=f"{len(r.markets)} CBSAs screened · {r.watch_markets} watch · {r.secondary_markets} secondary",
        tone="teal",
    )
    comp_tbl = _components_table(r.components)
    scen_tbl = _scenarios_table(r.entry_scenarios)
    tier_tbl = _tiers_table(r.tiers)

    form = f"""
<form method="GET" action="/geo-market" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector)}"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:180px"/>
  </label>
  <button type="submit"
    style="background:{border};color:{text};border:1px solid {border};
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    page_title = ck_page_title(
        "Geographic Market Analyzer",
        eyebrow="GEO MARKET",
        meta=f"{sector} sector · {len(r.markets)} CBSAs analyzed covering {r.total_addressable_pop_mm:,.1f}M people · {r.priority_markets} priority / {r.watch_markets} watch / {r.secondary_markets} secondary / {r.avoid_markets} avoid · top market: {top_name} (score {top_score:.0f})",
    )

    # Cross-link to the real-data companion. /geo-market is the illustrative
    # CBSA white-space analyzer; /market-intel/geo does the same geographic-
    # attractiveness job with REAL CMS/SimplyAnalytics data (demand, provider
    # supply, consolidation, MA). Steer users to the real page.
    real_xlink = (
        f'<div style="background:{panel};border:1px solid {border};'
        f'border-left:3px solid {acc};padding:10px 14px;margin:0 0 14px;font-size:12px;'
        f'color:{text_dim}">For <b style="color:{text}">real</b> market data — this metro '
        f'(CBSA) view has a real-data counterpart in '
        f'<a href="/metro-markets" style="color:{acc};font-weight:600">Metro Markets</a> '
        f'(real Census/ACS demographics per CBSA). For state-level — provider supply, '
        f'shortage areas, SNF consolidation, Medicare Advantage, patient experience — '
        f'use the <a href="/geo-intel" style="color:{acc};font-weight:600">Geographic Intelligence</a> '
        f'suite (<a href="/state-rankings" style="color:{acc}">rank states</a> · '
        f'<a href="/state-compare" style="color:{acc}">compare</a> · '
        f'<a href="/state-profile" style="color:{acc}">profile</a> · '
        f'<a href="/state-peers" style="color:{acc}">find similar</a>), or '
        f'<a href="/market-intel/geo" style="color:{acc}">Market Intelligence (Geographic) &rarr;</a>. '
        f'This page is an <b style="color:{text}">illustrative</b> CBSA white-space analyzer '
        f'(seed corpus); its competitive-density (HHI), 5-yr-growth and payer-mix inputs are '
        f'synthetic, so the tiers are directional, not real-data screening.</div>')

    body = f"""
<div class="ck-page-wrap">

  {page_title}
  {real_xlink}

  {form}

  {value_anchor}
  <div class="ck-kpi-grid" style="margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="{cell}">
    <div style="{h3}">Market Tier Distribution</div>
    {dist_svg}
  </div>

  <div style="display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Growth × White-Space Scatter</div>
      {scatter_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">Score Components</div>
      {comp_tbl}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Market Rankings — {len(r.markets)} CBSAs</div>
    {markets_scatter}{markets_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Market Tier Summary</div>
    {tier_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Entry Strategy Scenarios (Top 5 Markets × De Novo / Acquisition)</div>
    {scen_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Geographic Thesis:</strong>
    Top market: {_html.escape(top_name)} (score {top_score:.0f}). {r.priority_markets + r.watch_markets} CBSAs in Priority/Watch
    tiers covering {r.total_addressable_pop_mm:,.1f}M people. Growth + low HHI + favorable payer mix drive scoring.
    Sun Belt (TX, AZ, FL, NC) and tech corridors (RTP, Austin) dominate the priority list.
  </div>

</div>"""

    return chartis_shell(ck_illustrative_note("geographic-market aggregates — built from the bundled illustrative seed deals, not your ingested portfolio") + body, "Geographic Market", active_nav="/geo-market",
        editorial_intro={
            "eyebrow": "GEO MARKET",
            "headline": "What the geo market page reveals on this deal.",
            "italic_word": "reveals",
        })
