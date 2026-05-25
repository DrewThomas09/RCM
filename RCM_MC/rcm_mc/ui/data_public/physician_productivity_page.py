"""Physician Productivity Analyzer page — /physician-productivity.

wRVU benchmarking vs MGMA/AMGA, utilization metrics, and capacity-to-EV scenarios.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_value_anchor, ck_source_purpose


def _benchmark_svg(benchmarks) -> str:
    """Horizontal floating bar per specialty — P25/P50/P75 range with marker at actual."""
    if not benchmarks:
        return ""
    n = len(benchmarks)
    w = 540
    row_h = 26
    h = 30 + n * row_h + 20
    pad_l = 150
    pad_r = 50
    inner_w = w - pad_l - pad_r

    max_v = max(b.p75_wrvu for b in benchmarks) * 1.20 if benchmarks else 12000
    min_v = min(b.p25_wrvu for b in benchmarks) * 0.80 if benchmarks else 3000

    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]
    warn = P["warning"]; neg = P["negative"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]

    bars = []
    for i, b in enumerate(benchmarks):
        y = 30 + i * row_h + 8

        def _x(v):
            return pad_l + (v - min_v) / (max_v - min_v) * inner_w

        # P25-P75 range bar
        x25 = _x(b.p25_wrvu)
        x50 = _x(b.median_wrvu)
        x75 = _x(b.p75_wrvu)
        xA = _x(b.actual_wrvu)

        # Color based on percentile
        if b.percentile >= 75:
            mkr = pos
        elif b.percentile >= 50:
            mkr = acc
        elif b.percentile >= 25:
            mkr = warn
        else:
            mkr = neg

        bars.append(
            f'<text x="{pad_l - 8}" y="{y + 5}" fill="{text_dim}" font-size="10" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(b.specialty[:20])}</text>'
            # Range bar (P25-P75)
            f'<rect x="{x25:.1f}" y="{y}" width="{(x75 - x25):.1f}" height="8" fill="{P["border_dim"]}" stroke="{border}"/>'
            # Median tick
            f'<line x1="{x50:.1f}" y1="{y - 2}" x2="{x50:.1f}" y2="{y + 10}" stroke="{text_faint}" stroke-width="1"/>'
            # Actual marker
            f'<circle cx="{xA:.1f}" cy="{y + 4}" r="4" fill="{mkr}" stroke="{P["text"]}" stroke-width="1"/>'
            # Percentile label
            f'<text x="{w - pad_r + 6}" y="{y + 6}" fill="{mkr}" font-size="9" '
            f'font-family="JetBrains Mono,monospace">{b.percentile:.0f}%</text>'
        )

    # Scale ticks
    ticks = []
    for v in [5000, 7500, 10000]:
        if min_v < v < max_v:
            xp = pad_l + (v - min_v) / (max_v - min_v) * inner_w
            ticks.append(
                f'<line x1="{xp:.1f}" y1="25" x2="{xp:.1f}" y2="{h - 20}" stroke="{border}" stroke-width="0.5" stroke-dasharray="2,3"/>'
                f'<text x="{xp:.1f}" y="20" fill="{text_faint}" font-size="9" '
                f'text-anchor="middle" font-family="JetBrains Mono,monospace">{v:,}</text>'
            )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(ticks) + "".join(bars)
        + f'<text x="10" y="12" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">wRVU Production vs. MGMA Benchmarks (P25 → P75 range; marker = actual)</text>'
        + f'</svg>'
    )


def _capacity_svg(scenarios, corpus_ev_uplift_range: tuple = None) -> str:
    if not scenarios:
        return ""
    w, h = 540, 180
    pad_l, pad_r, pad_t, pad_b = 120, 40, 20, 30
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    row_h = (inner_h - 10) / max(len(scenarios), 1)

    max_v = max(abs(s.implied_ev_uplift_mm) for s in scenarios) * 1.15 or 1.0

    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]

    bars = []
    zero_x = pad_l + (max_v / (2 * max_v)) * inner_w   # center zero
    center_x = pad_l + inner_w / 2

    for i, s in enumerate(scenarios):
        y = pad_t + i * row_h + 2
        bh = row_h - 8
        color = pos if s.implied_ev_uplift_mm >= 0 else neg
        # Bar width proportional to value relative to max
        bw = abs(s.implied_ev_uplift_mm) / max_v * (inner_w / 2)
        if s.implied_ev_uplift_mm >= 0:
            xr = center_x
        else:
            xr = center_x - bw
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh / 2 + 3}" fill="{text_dim}" font-size="11" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(s.scenario)}</text>'
            f'<rect x="{xr:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{color}" opacity="0.85"/>'
            f'<text x="{xr + bw + 6 if s.implied_ev_uplift_mm >= 0 else xr - 6:.1f}" y="{y + bh / 2 + 3}" fill="{color}" '
            f'font-size="11" text-anchor="{"start" if s.implied_ev_uplift_mm >= 0 else "end"}" '
            f'font-family="JetBrains Mono,monospace;font-weight:600">${s.implied_ev_uplift_mm:+,.1f}M</text>'
        )

    # Center line
    axis = (
        f'<line x1="{center_x:.1f}" y1="{pad_t - 4}" x2="{center_x:.1f}" y2="{h - pad_b + 4}" '
        f'stroke="{border}" stroke-width="1"/>'
    )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + axis + "".join(bars)
        + f'</svg>'
    )


def _provider_table(providers) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    pctile_colors = {"P75+": P["positive"], "P50": P["accent"], "P25": P["warning"], "Below P25": P["negative"]}
    cols = [("Specialty","left"),("FTE","right"),("wRVU/FTE","right"),("Percentile","left"),
            ("Total wRVU","right"),("Comp ($M)","right"),("Collections ($M)","right"),("Comp/Coll %","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, p in enumerate(providers):
        rb = panel_alt if i % 2 == 0 else bg
        pcolor = pctile_colors.get(p.percentile, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.specialty)}""", mono=True)}',
            f'{ck_data_cell(f"""{p.fte_count:.1f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{p.annual_wrvu_per_fte:,.0f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pcolor};border:1px solid {pcolor};border-radius:2px">{_html.escape(p.percentile)}</span>""")}',
            f'{ck_data_cell(f"""{p.total_annual_wrvu:,.0f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${p.total_comp_mm:,.2f}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">${p.collections_mm:,.2f}</td>',
            f'{ck_data_cell(f"""{p.comp_to_collection_pct * 100:.1f}%""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _utilization_table(utilization) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    status_colors = {"strong": P["positive"], "benchmark": P["accent"], "below": P["negative"]}
    cols = [("Metric","left"),("Value","right"),("Unit","left"),("Benchmark","right"),("Status","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, u in enumerate(utilization):
        rb = panel_alt if i % 2 == 0 else bg
        scolor = status_colors.get(u.status, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(u.metric)}""", mono=True)}',
            f'{ck_data_cell(f"""{u.value:,.1f}""", align="right", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(u.unit)}""", tone="dim")}',
            f'{ck_data_cell(f"""{u.benchmark:,.1f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{scolor};border:1px solid {scolor};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{u.status}</span>""")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _capacity_table(scenarios) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Scenario","left"),("% of P75","right"),("wRVU Lift %","right"),
            ("Rev Lift ($M)","right"),("EBITDA Lift ($M)","right"),("EV Uplift ($M)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(scenarios):
        rb = panel_alt if i % 2 == 0 else bg
        ec = pos if s.implied_ev_uplift_mm >= 0 else neg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.scenario)}""", mono=True)}',
            f'{ck_data_cell(f"""{s.productivity_pct_of_p75 * 100:.0f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{s.implied_wrvu_lift_pct * 100:+.1f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${s.implied_revenue_lift_mm:+,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${s.implied_ebitda_lift_mm:+,.2f}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ec};font-weight:600">${s.implied_ev_uplift_mm:+,.1f}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_physician_productivity(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    revenue = _f("revenue", 80.0)
    margin = _f("margin", 0.18)
    mult = _f("mult", 11.0)

    from rcm_mc.data_public.physician_productivity import compute_physician_productivity
    r = compute_physician_productivity(revenue_mm=revenue, ebitda_margin=margin, exit_multiple=mult)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Total FTE", f"{r.total_fte:.1f}", "", "") +
        ck_kpi_block("Total wRVU", f"{r.total_wrvu:,.0f}", "", "") +
        ck_kpi_block("Productivity Score", f"{r.productivity_score:.0f}", "/100", "") +
        ck_kpi_block("Collections", f"${r.total_collections_mm:,.1f}M", "", "") +
        ck_kpi_block("Provider Comp", f"${r.total_provider_comp_mm:,.1f}M", "", "") +
        ck_kpi_block("Blended C/C", f"{r.blended_comp_to_coll_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Specialties", f"{len(r.providers)}", "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    bench_svg = _benchmark_svg(r.benchmarks)
    cap_svg = _capacity_svg(r.capacity_scenarios)
    provider_tbl = _provider_table(r.providers)
    util_tbl = _utilization_table(r.utilization)
    cap_tbl = _capacity_table(r.capacity_scenarios)

    form = f"""
<form method="GET" action="/physician-productivity" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Revenue ($M)
    <input name="revenue" value="{revenue}" type="number" step="5"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">EBITDA Margin
    <input name="margin" value="{margin}" type="number" step="0.01"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Exit Multiple
    <input name="mult" value="{mult}" type="number" step="0.5"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <button type="submit"
    style="background:{border};color:{text};border:1px solid {border};
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    page_title = ck_page_title(
        "Physician Productivity Analyzer",
        eyebrow="PHYSICIAN PRODUCTIVITY",
        meta=f"""wRVU benchmarking vs MGMA/AMGA, utilization metrics, and capacity-to-EV scenarios — {r.corpus_deal_count:,} corpus deals""",
    )
    
    value_anchor = ck_value_anchor(
        "Physician Productivity",
        f"${r.total_collections_mm:,.1f}M collections",
        delta=f"{r.total_fte:.1f} FTE · {r.total_wrvu:,.0f} wRVU · {r.productivity_score:.0f}/100 productivity",
        tone="teal",
    )

    body = f"""
<div class="ck-page-wrap">

  {page_title}

  {form}

  <div class="ck-kpi-grid" style="margin-bottom:20px">
    {kpi_strip}
  </div>

  {value_anchor}

  <div style="display:grid;grid-template-columns:1.2fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">wRVU Benchmark Positioning</div>
      {bench_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">Capacity → EV Uplift Scenarios</div>
      {cap_svg}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Provider Cohort Detail</div>
    {provider_tbl}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Utilization Metrics</div>
      {util_tbl}
    </div>
    <div style="{cell}">
      <div style="{h3}">Capacity Scenarios</div>
      {cap_tbl}
    </div>
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Productivity Thesis:</strong>
    Current group at {r.productivity_score:.0f}th percentile. Reaching P75 productivity
    across cohort implies ${r.capacity_scenarios[1].implied_ev_uplift_mm if len(r.capacity_scenarios) > 1 else 0:+,.1f}M of EV uplift
    — a concrete value creation lever the sponsor can execute post-close.
  </div>

</div>"""

    # Real HRSA primary-care shortage CONTEXT (market workforce framing).
    try:
        from rcm_mc.data import hrsa_data as _hrsa
        _hs = _hrsa.hpsa_summary()
        _top = _hrsa.top_shortage_states(8)
        if _hs.get("total_designated"):
            _rows = "".join(
                f'<tr><td style="padding:3px 10px">{_html.escape(str(t["state"]))}</td>'
                f'<td style="padding:3px 10px;text-align:right;font-variant-numeric:tabular-nums">{int(t["designated_pc_hpsas"]):,}</td>'
                f'<td style="padding:3px 10px;text-align:right;font-variant-numeric:tabular-nums">{t["median_hpsa_score"]:.0f}</td></tr>'
                for t in _top)
            _hrsa_panel = (
                f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
                f'border-left:3px solid {P["accent"]};padding:14px 16px;margin-bottom:16px">'
                f'<div style="font-size:11px;font-weight:600;letter-spacing:0.08em;'
                f'text-transform:uppercase;color:{P["text_dim"]};margin-bottom:6px">'
                f'Primary-care workforce shortage context · LIVE (HRSA)</div>'
                f'<p style="font-size:12px;color:{P["text_dim"]};margin:0 0 8px">'
                f'<b style="color:{P["text"]}">{_hs["total_designated"]:,}</b> designated '
                f'primary-care HPSAs nationally — context for recruitment/retention '
                f'risk. Higher HPSA score = greater shortage.</p>'
                f'<table style="border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
                f'<thead><tr style="border-bottom:1px solid {P["border"]};color:{P["text_dim"]}">'
                f'<th style="padding:3px 10px;text-align:left">State</th>'
                f'<th style="padding:3px 10px;text-align:right">PC HPSAs</th>'
                f'<th style="padding:3px 10px;text-align:right">Median score</th></tr></thead>'
                f'<tbody>{_rows}</tbody></table>'
                f'<p style="font-size:11px;color:{P["text_dim"]};margin:8px 0 0">'
                f'Real HRSA market/access context — <b>not</b> provider-specific and '
                f'<b>not</b> a productivity measure.</p></div>')
            body = _hrsa_panel + body
    except Exception:
        pass

    body = ck_source_purpose(
        purpose="Gauge physician productivity (wRVU / panel) vs specialty "
                "benchmarks — a calculator on the inputs you provide, plus real "
                "HRSA workforce-shortage context.",
        universe="derived", confidence="derived",
        source="Representative MGMA/AMGA-style specialty benchmark ranges "
               "(illustrative, not licensed MGMA tables) + real HRSA shortage context",
        next_action="Attach CMS Part B / PECOS provider data for real utilization") + body
    return chartis_shell(body, "Physician Productivity", active_nav="/physician-productivity",
        editorial_intro={
            "eyebrow": "PHYSICIAN PRODUCTIVITY",
            "headline": "What the physician productivity page reveals on this deal.",
            "italic_word": "reveals",
        })
