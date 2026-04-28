"""Healthcare REIT / Sale-Leaseback Analyzer — /reit-analyzer."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _assets_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("ID","left"),("Asset Type","left"),("Location","left"),("SqFt","right"),
            ("NOI ($M)","right"),("Cap Rate","right"),("Market ($M)","right"),
            ("Book ($M)","right"),("Unrealized Gain ($M)","right"),("Occupancy","right"),("Status","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(a.asset_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(a.asset_type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(a.location)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{a.building_sqft:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${a.annual_noi_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{a.cap_rate_implied * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${a.market_value_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${a.book_value_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${a.unrealized_gain_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{a.occupancy_pct * 100:.1f}%</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(a.lease_status)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _scenarios_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Scenario","left"),("Asset Type","left"),("Proceeds ($M)","right"),("Initial Rent ($M)","right"),
            ("Escalation","right"),("Term (yr)","right"),("Coverage (EBITDAR/Rent)","right"),
            ("NPV Benefit ($M)","right"),("Tax Gain ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        npv_c = pos if s.npv_benefit_mm > 0 else neg
        cov_c = pos if s.coverage_ratio >= 2.5 else (acc if s.coverage_ratio >= 2.0 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(s.scenario)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(s.asset_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${s.sale_proceeds_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">${s.initial_rent_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.rent_escalation_pct * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.term_years}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cov_c};font-weight:700">{s.coverage_ratio:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{npv_c};font-weight:700">${s.npv_benefit_mm:+,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">${s.tax_gain_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _buyers_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Buyer","left"),("Type","left"),("Focus","left"),("Typical Cap","right"),
            ("Avg Deal ($M)","right"),("Pipeline ($M)","right"),("Credit","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cr_c = pos if b.credit_rating.startswith("BBB") else (text_dim if b.credit_rating == "N/A" else acc)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(b.buyer_name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(b.buyer_type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(b.focus_asset_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{b.typical_cap_rate * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${b.avg_deal_size_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${b.pipeline_capacity_mm:,.0f}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{cr_c};font-weight:600">{_html.escape(b.credit_rating)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _coverage_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Metric","left"),("Pre-SLB","right"),("Post-SLB","right"),
            ("Δ %","right"),("Covenant","right"),("Headroom","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        hr_c = pos if r.headroom_pct > 0.25 else (warn if r.headroom_pct > 0 else neg)
        d_c = pos if r.delta_pct > 0 else (warn if r.delta_pct > -0.15 else neg)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(r.metric)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{r.pre_slb_value:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{r.post_slb_value:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:600">{r.delta_pct * 100:+.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.covenant_threshold:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{hr_c};font-weight:600">{r.headroom_pct * 100:+.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _uses_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Use of Proceeds","left"),("Allocation %","right"),("Amount ($M)","right"),
            ("Rationale","left"),("MOIC Uplift","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, u in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(u.use_category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{u.allocation_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${u.allocation_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(u.rationale)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">+{u.moic_uplift:.2f}x</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _mv_vs_bv_svg(assets) -> str:
    if not assets: return ""
    w, h = 560, 220
    pad_l, pad_r, pad_t, pad_b = 50, 20, 30, 70
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    max_v = max(a.market_value_mm for a in assets) or 1
    bg = P["panel"]; pos = P["positive"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]
    n = len(assets)
    bar_w = (inner_w - (n - 1) * 10) / n
    bars = []
    for i, a in enumerate(assets):
        x = pad_l + i * (bar_w + 10)
        mh = a.market_value_mm / max_v * inner_h
        bh = a.book_value_mm / max_v * inner_h
        y_m = (h - pad_b) - mh
        y_b = (h - pad_b) - bh
        bars.append(
            f'<rect x="{x:.1f}" y="{y_m:.1f}" width="{bar_w:.1f}" height="{mh:.1f}" fill="{pos}" opacity="0.4"/>'
            f'<rect x="{x:.1f}" y="{y_b:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{text_dim}" opacity="0.85"/>'
            f'<text x="{x + bar_w / 2:.1f}" y="{y_m - 4:.1f}" fill="{pos}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:700">${a.market_value_mm:.0f}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">{_html.escape(a.asset_id)}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 26}" fill="{text_faint}" font-size="8" text-anchor="middle" font-family="JetBrains Mono,monospace">{_html.escape(a.asset_type[:16])}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 38}" fill="{text_faint}" font-size="8" text-anchor="middle" font-family="JetBrains Mono,monospace">{a.cap_rate_implied * 100:.2f}% cap</text>'
        )
    legend = (
        f'<rect x="10" y="{h - 18}" width="10" height="10" fill="{pos}" opacity="0.4"/><text x="24" y="{h - 9}" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">market value</text>'
        f'<rect x="110" y="{h - 18}" width="10" height="10" fill="{text_dim}"/><text x="124" y="{h - 9}" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">book value</text>'
    )
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{"".join(bars)}{legend}'
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Market Value vs Book Value by Asset — Hidden Equity on Balance Sheet</text></svg>')


def render_reit_analyzer(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    platform = params.get("platform", "Hospital System")
    ebitdar = _f("ebitdar", 85.0)

    from rcm_mc.data_public.reit_analyzer import compute_reit_analyzer
    r = compute_reit_analyzer(platform_type=platform, platform_ebitdar_mm=ebitdar)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Total Assets", str(r.total_assets), "", "") +
        ck_kpi_block("Book Value", f"${r.total_book_value_mm:,.1f}M", "", "") +
        ck_kpi_block("Market Value", f"${r.total_market_value_mm:,.1f}M", "", "") +
        ck_kpi_block("Unrealized Gain", f"${r.total_unrealized_gain_mm:,.1f}M", "", "") +
        ck_kpi_block("Weighted Cap", f"{r.weighted_cap_rate * 100:.2f}%", "", "") +
        ck_kpi_block("Max Proceeds", f"${r.max_proceeds_mm:,.0f}M", "", "") +
        ck_kpi_block("Recommendation", r.recommended_scenario[:16], "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    svg = _mv_vs_bv_svg(r.assets)
    assets_tbl = _assets_table(r.assets)
    scen_tbl = _scenarios_table(r.scenarios)
    buy_tbl = _buyers_table(r.reit_buyers)
    cov_tbl = _coverage_table(r.rent_coverage)
    uses_tbl = _uses_table(r.proceeds_uses)

    platforms = ["Hospital System", "Senior Living Portfolio", "Behavioral Health Platform", "ASC Platform"]
    plat_opts = "".join(f'<option value="{_html.escape(s)}"{" selected" if s == platform else ""}>{_html.escape(s)}</option>' for s in platforms)

    form = f"""
<form method="GET" action="/reit-analyzer" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Platform Type<select name="platform" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace">{plat_opts}</select></label>
  <label style="font-size:11px;color:{text_dim}">Platform EBITDAR ($M)<input name="ebitdar" value="{ebitdar}" type="number" step="5" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:90px"/></label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Healthcare REIT / Sale-Leaseback Analyzer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Real-estate monetization · cap-rate comps · rent coverage · REIT buyer landscape · proceeds allocation — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  {form}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Market vs Book Value — Hidden Equity by Asset</div>{svg}</div>
  <div style="{cell}"><div style="{h3}">Real Estate Portfolio Roster</div>{assets_tbl}</div>
  <div style="{cell}"><div style="{h3}">Sale-Leaseback Scenario Matrix</div>{scen_tbl}</div>
  <div style="{cell}"><div style="{h3}">REIT Buyer Landscape — Public + Private Capital</div>{buy_tbl}</div>
  <div style="{cell}"><div style="{h3}">Rent Coverage &amp; Covenant Impact</div>{cov_tbl}</div>
  <div style="{cell}"><div style="{h3}">Proceeds Allocation Plan</div>{uses_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Sale-Leaseback Thesis:</strong> {r.total_assets} owned assets carry ${r.total_market_value_mm:,.1f}M market value on ${r.total_book_value_mm:,.1f}M book,
    producing ${r.total_unrealized_gain_mm:,.1f}M hidden equity. Weighted cap rate {r.weighted_cap_rate * 100:.2f}% is sellable into public REITs (BBB-rated, 6-9% targets) or private
    real estate credit funds. Recommended scenario: <strong style="color:{text}">{_html.escape(r.recommended_scenario)}</strong>, producing ${r.max_proceeds_mm:,.0f}M proceeds.
    Post-SLB rent coverage remains comfortably above 1.75x covenant. Proceeds deployed 42% to debt paydown, 28% to bolt-on M&A, 15% to dividend recap — producing meaningful MOIC uplift at exit.
    Ground-lease optionality provides a tax-advantaged hybrid alternative if full SLB creates covenant stress.
  </div>
</div>"""

    return chartis_shell(body, "REIT / SLB", active_nav="/reit-analyzer")
