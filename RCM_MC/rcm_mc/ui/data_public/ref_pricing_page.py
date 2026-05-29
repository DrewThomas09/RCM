"""Reference Pricing / Payer Contract Analyzer page — /ref-pricing.

CPT-level rate benchmarking, contract renewal calendar, uplift scenarios.
"""
from __future__ import annotations

import html as _html

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_illustrative_note, ck_value_anchor, ck_source_purpose


def _rate_ladder_svg(cpt_rows) -> str:
    if not cpt_rows:
        return ""
    w = 560
    row_h = 30
    h = 30 + len(cpt_rows) * row_h + 20
    pad_l = 120
    pad_r = 40
    inner_w = w - pad_l - pad_r

    # Find max rate across all codes to normalize
    max_rate = max(c.comm_p75 for c in cpt_rows) or 1

    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]
    mcr_col = "#a98545"

    bars = []
    for i, c in enumerate(cpt_rows):
        y = 25 + i * row_h
        # Scale Medicare / current / median / P75 to x positions
        def _x(rate):
            return pad_l + (rate / max_rate) * inner_w

        x_mcr = _x(c.medicare_rate)
        x_cur = _x(c.current_avg_rate)
        x_med = _x(c.comm_median)
        x_p75 = _x(c.comm_p75)

        # Background line
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + 12}" fill="{text_dim}" font-size="10" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{c.cpt_code}</text>'
            # Range line MCR -> P75
            f'<line x1="{x_mcr:.1f}" y1="{y + 8}" x2="{x_p75:.1f}" y2="{y + 8}" stroke="{border}" stroke-width="1" opacity="0.5"/>'
            # Medicare dot (purple)
            f'<circle cx="{x_mcr:.1f}" cy="{y + 8}" r="4" fill="{mcr_col}"/>'
            # Current (accent)
            f'<circle cx="{x_cur:.1f}" cy="{y + 8}" r="5" fill="{acc}" stroke="{P["text"]}" stroke-width="1"/>'
            # Median
            f'<circle cx="{x_med:.1f}" cy="{y + 8}" r="4" fill="{P["warning"]}"/>'
            # P75 (pos target)
            f'<circle cx="{x_p75:.1f}" cy="{y + 8}" r="4" fill="{pos}"/>'
            # Rate labels below
            f'<text x="{x_cur:.1f}" y="{y + 22}" fill="{acc}" font-size="9" text-anchor="middle" '
            f'font-family="JetBrains Mono,monospace">${c.current_avg_rate:,.0f}</text>'
        )

    legend = (
        f'<circle cx="{pad_l}" cy="12" r="4" fill="{mcr_col}"/>'
        f'<text x="{pad_l + 8}" y="15" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">Medicare</text>'
        f'<circle cx="{pad_l + 85}" cy="12" r="4" fill="{acc}"/>'
        f'<text x="{pad_l + 93}" y="15" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">Current</text>'
        f'<circle cx="{pad_l + 160}" cy="12" r="4" fill="{P["warning"]}"/>'
        f'<text x="{pad_l + 168}" y="15" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">Market Median</text>'
        f'<circle cx="{pad_l + 275}" cy="12" r="4" fill="{pos}"/>'
        f'<text x="{pad_l + 283}" y="15" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">Market P75</text>'
    )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + legend + "".join(bars)
        + f'</svg>'
    )


def _index_gauge_svg(current: float, median: float, p75: float) -> str:
    w, h = 280, 150
    pad_l, pad_r, pad_t, pad_b = 30, 30, 30, 30
    inner_w = w - pad_l - pad_r

    # Scale: 0 to 2.5x Medicare
    scale_max = max(p75 * 1.15, 2.5)

    bg = P["panel"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]
    border = P["border"]
    mcr_col = "#a98545"

    y_line = h / 2

    def _x(val):
        return pad_l + (val / scale_max) * inner_w

    # Horizontal axis
    line = f'<line x1="{pad_l}" y1="{y_line}" x2="{w - pad_r}" y2="{y_line}" stroke="{border}" stroke-width="2"/>'

    # Markers
    markers = ""
    for val, color, label in [(1.0, mcr_col, "MCR"), (current, P["accent"], "Current"),
                               (median, P["warning"], "Median"), (p75, P["positive"], "P75")]:
        x = _x(val)
        markers += (
            f'<line x1="{x:.1f}" y1="{y_line - 15}" x2="{x:.1f}" y2="{y_line + 15}" stroke="{color}" stroke-width="3"/>'
            f'<text x="{x:.1f}" y="{y_line - 20}" fill="{color}" font-size="10" text-anchor="middle" '
            f'font-family="JetBrains Mono,monospace;font-weight:600">{val:.2f}x</text>'
            f'<text x="{x:.1f}" y="{y_line + 28}" fill="{text_dim}" font-size="9" text-anchor="middle" '
            f'font-family="Inter,sans-serif">{label}</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + line + markers +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Rate Index to Medicare</text>'
        f'</svg>'
    )


def _cpt_table(cpt_rows) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("CPT","left"),("Description","left"),("Volume","right"),("MCR","right"),
            ("Current Rate","right"),("Comm Median","right"),("Comm P75","right"),
            ("Gap to Med","right"),("Uplift Median ($M)","right"),("Uplift P75 ($M)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, c in enumerate(cpt_rows):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{c.cpt_code}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:220px">{_html.escape(c.description)}</td>',
            f'{ck_data_cell(f"""{c.volume_annual:,}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${c.medicare_rate:.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${c.current_avg_rate:.2f}""", align="right", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${c.comm_median:.2f}</td>',
            f'{ck_data_cell(f"""${c.comm_p75:.2f}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""+{c.gap_to_median_pct * 100:.1f}%""", align="right", mono=True, tone="pos")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${c.uplift_to_median_mm:,.2f}</td>',
            f'{ck_data_cell(f"""${c.uplift_to_p75_mm:,.2f}""", align="right", mono=True, tone="pos", weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _contracts_table(contracts) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    stat_colors = {"current": P["positive"], "expiring": P["warning"], "open": P["negative"]}
    lev_colors = {"high": P["positive"], "medium": P["accent"], "low": P["text_faint"]}
    cols = [("Payer","left"),("Contract Type","left"),("Renewal","right"),
            ("Annual Volume ($M)","right"),("Index to MCR","right"),("Status","left"),("Leverage","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, c in enumerate(contracts):
        rb = panel_alt if i % 2 == 0 else bg
        sc = stat_colors.get(c.status, text_dim)
        lc = lev_colors.get(c.leverage, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.payer)}""", mono=True)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.contract_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.renewal_date)}</td>',
            f'{ck_data_cell(f"""${c.annual_volume_mm:,.2f}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]};font-weight:600">{c.blended_index_to_mcr:.2f}x</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{c.status}</span>""")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{lc};border:1px solid {lc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{c.leverage}</span>""")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _scenarios_table(scenarios) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    comp_colors = {"low": P["positive"], "medium": P["warning"], "high": P["negative"]}
    cols = [("Scenario","left"),("Target Index","right"),("Revenue Uplift ($M)","right"),
            ("EBITDA Uplift ($M)","right"),("EV Impact ($M)","right"),("Complexity","left"),("Probability","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(scenarios):
        rb = panel_alt if i % 2 == 0 else bg
        cc = comp_colors.get(s.execution_complexity, text_dim)
        val_c = pos if s.ev_impact_mm >= 0 else neg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.scenario)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{s.target_index_to_mcr:.2f}x""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{val_c}">${s.annual_revenue_uplift_mm:+,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{val_c}">${s.ebitda_uplift_mm:+,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{val_c};font-weight:600">${s.ev_impact_mm:+,.1f}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{cc};border:1px solid {cc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{s.execution_complexity}</span>""")}',
            f'{ck_data_cell(f"""{s.probability * 100:.0f}%""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _colorado_rbp_section(params: dict) -> str:
    """REAL Colorado provider reimbursement-vs-Medicare from CIVHC RBP data
    (public). LIVE-labeled, distinct from the illustrative CPT/contract model
    below. Optional ?org= name filter, ?claim_type= filter."""
    try:
        from rcm_mc.data import payer_data as _pd
        df = _pd.reference_pricing_summary(
            claim_type=params.get("claim_type", "All"))
    except Exception:
        return ""
    if df is None or not len(df):
        return ""
    org_q = (params.get("org") or "").strip().lower()
    if org_q:
        df = df[df["organization_name"].astype(str).str.lower().str.contains(org_q)]
    n_prov = int(df["organization_name"].nunique())
    med = df["hospital_pct_medicare"].dropna()
    statewide_median = float(med.median()) if len(med) else None

    hdr = ck_source_purpose(
        purpose=("Benchmark a Colorado provider's commercial reimbursement "
                 "against Medicare (hospital % of Medicare) using real CIVHC "
                 "all-payer data — provider-level, 2021–2024."),
        universe="cms", confidence="derived",
        source="CIVHC / CO APCD — Medicare Reference-Based Pricing (public, FY2026)",
        next_action="Search a provider name to compare its % of Medicare")

    rows = "".join(
        f'<tr><td style="padding:4px 8px">{_html.escape(str(r.organization_name))}</td>'
        f'<td style="padding:4px 8px">{_html.escape(str(r.claim_type))}</td>'
        f'<td style="padding:4px 8px">{_html.escape(str(r.county))}</td>'
        f'<td style="padding:4px 8px;text-align:right;font-variant-numeric:tabular-nums">'
        f'{("%.2fx" % r.hospital_pct_medicare) if r.hospital_pct_medicare==r.hospital_pct_medicare else "—"}</td>'
        f'<td style="padding:4px 8px;text-align:right;font-variant-numeric:tabular-nums">'
        f'{int(r.claims):,}</td></tr>'
        for r in df.head(40).itertuples())
    med_txt = f"{statewide_median:.2f}x" if statewide_median is not None else "—"
    form = (
        f'<form method="get" action="/ref-pricing" style="margin:10px 0;display:flex;gap:8px">'
        f'<input type="text" name="org" value="{_html.escape(params.get("org",""))}" '
        f'placeholder="Search Colorado provider" style="padding:6px 9px;border:1px solid '
        f'{P["border"]};border-radius:2px;min-width:260px;font-size:13px">'
        f'<button type="submit" style="padding:7px 14px;background:{P["accent"]};color:#fff;'
        f'border:none;border-radius:2px;font-size:12px;cursor:pointer">Search</button></form>')
    # 2026-05-28 batch 33 · Tier-4 trope removal — strip 3px accent.
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:2px;padding:14px 16px;margin-bottom:18px">'
        f'<div style="font-size:11px;font-weight:600;letter-spacing:0.08em;'
        f'text-transform:uppercase;color:{P["text_dim"]};margin-bottom:8px">'
        f'Colorado provider reimbursement vs Medicare · LIVE (CIVHC)</div>'
        f'{hdr}{form}'
        f'<p style="font-size:12px;color:{P["text_dim"]};margin:4px 0 8px">'
        f'<b style="color:{P["text"]}">{n_prov:,}</b> Colorado providers · statewide '
        f'median <b style="color:{P["text"]}">{med_txt}</b> of Medicare · % of Medicare '
        f'= commercial-to-Medicare reimbursement ratio (higher = more expensive vs Medicare).</p>'
        f'<table style="width:100%;border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
        f'<thead><tr style="border-bottom:1px solid {P["border"]};color:{P["text_dim"]}">'
        f'<th style="padding:4px 8px;text-align:left">Provider</th>'
        f'<th style="padding:4px 8px;text-align:left">Claim Type</th>'
        f'<th style="padding:4px 8px;text-align:left">County</th>'
        f'<th style="padding:4px 8px;text-align:right">% of Medicare</th>'
        f'<th style="padding:4px 8px;text-align:right">Claims</th></tr></thead>'
        f'<tbody>{rows}</tbody></table></div>')


def render_ref_pricing(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Physician Services") or "Physician Services"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    revenue = _f("revenue", 80.0)
    idx = _f("idx", 1.55)
    margin = _f("margin", 0.18)
    mult = _f("mult", 11.0)

    from rcm_mc.data_public.ref_pricing import compute_ref_pricing
    r = compute_ref_pricing(sector=sector, revenue_mm=revenue, current_index_to_mcr=idx,
                             ebitda_margin=margin, exit_multiple=mult)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    gap_median_pct = (r.market_median_index / r.current_weighted_index - 1) if r.current_weighted_index else 0
    gap_p75_pct = (r.market_p75_index / r.current_weighted_index - 1) if r.current_weighted_index else 0

    kpi_strip = (
        ck_kpi_block("Current Index", f"{r.current_weighted_index:.2f}x", "MCR", "") +
        ck_kpi_block("Market Median", f"{r.market_median_index:.2f}x", "MCR", "") +
        ck_kpi_block("Market P75", f"{r.market_p75_index:.2f}x", "MCR", "") +
        ck_kpi_block("Gap to Median", f"+{gap_median_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Gap to P75", f"+{gap_p75_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Uplift to Median", f"${r.total_uplift_to_median_mm:,.1f}M", "", "") +
        ck_kpi_block("Uplift to P75", f"${r.total_uplift_to_p75_mm:,.1f}M", "", "") +
        ck_kpi_block("CPTs Analyzed", str(len(r.cpt_rows)), "", "")
    )

    ladder_svg = _rate_ladder_svg(r.cpt_rows)
    gauge_svg = _index_gauge_svg(r.current_weighted_index, r.market_median_index, r.market_p75_index)
    cpt_tbl = _cpt_table(r.cpt_rows)
    contracts_tbl = _contracts_table(r.payer_contracts)
    scen_tbl = _scenarios_table(r.uplift_scenarios)

    form = f"""
<form method="GET" action="/ref-pricing" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector)}"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:160px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Net Revenue ($M)
    <input name="revenue" value="{revenue}" type="number" step="5"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Current Index
    <input name="idx" value="{idx}" type="number" step="0.05"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
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
        "Reference Pricing &amp; Payer Contract Analyzer",
        eyebrow="REF PRICING",
        meta=f"""CPT-level rate benchmarking vs Medicare / Commercial P50 / P75, contract calendar, uplift scenarios — {_html.escape(sector)} — {r.corpus_deal_count:,} corpus deals""",
    )
    
    value_anchor = ck_value_anchor(
        "Reference Pricing",
        f"{r.current_weighted_index:.2f}x MCR (weighted index)",
        delta=f"market median {r.market_median_index:.2f}x · P75 {r.market_p75_index:.2f}x · +{gap_median_pct * 100:.1f}% to median",
        tone="warning" if gap_median_pct >= 0.10 else "teal",
    )

    body = f"""
<div class="ck-page-wrap">

  {page_title}

  {_colorado_rbp_section(params or {})}

  <div style="font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:{text_dim};margin:18px 0 4px">Illustrative rate-negotiation model (calculator below)</div>
  {ck_illustrative_note("CPT rate ladders, contract calendar, and uplift scenarios")}

  {form}

  <div class="ck-kpi-grid" style="margin-bottom:20px">
    {kpi_strip}
  </div>

  {value_anchor}

  <div style="display:grid;grid-template-columns:1.3fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">CPT-Level Rate Ladder (MCR → Current → Median → P75)</div>
      {ladder_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">Weighted Index Positioning</div>
      {gauge_svg}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">CPT-Level Benchmarking Detail</div>
    {cpt_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Payer Contract Calendar &amp; Leverage</div>
    {contracts_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Rate Uplift Scenarios</div>
    {scen_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Pricing Thesis:</strong>
    Current weighted index {r.current_weighted_index:.2f}x Medicare. Market median is {r.market_median_index:.2f}x
    (uplift ${r.total_uplift_to_median_mm:,.1f}M), P75 is {r.market_p75_index:.2f}x (uplift ${r.total_uplift_to_p75_mm:,.1f}M).
    Anthem &amp; BCBS Local expiring in next 18 months offer highest renegotiation leverage. Rate changes typically
    fall through ~100% to EBITDA.
  </div>

</div>"""

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "Reference Pricing", active_nav="/ref-pricing",
        editorial_intro={
            "eyebrow": "REF PRICING",
            "headline": "What the ref pricing page reveals on this deal.",
            "italic_word": "reveals",
        })
