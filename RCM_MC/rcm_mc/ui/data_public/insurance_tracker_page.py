"""Insurance Tracker page — /insurance-tracker."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _coverage_svg(coverages) -> str:
    if not coverages: return ""
    sorted_c = sorted(coverages, key=lambda c: -c.annual_premium_mm)
    w = 540; row_h = 24
    h = len(sorted_c) * row_h + 30
    pad_l = 240; pad_r = 80
    inner_w = w - pad_l - pad_r
    max_v = max(c.annual_premium_mm for c in sorted_c) or 1
    bg = P["panel"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]
    trend_colors = {"hardening": P["negative"], "stable": P["accent"], "softening": P["positive"]}
    bars = []
    for i, c in enumerate(sorted_c):
        y = 20 + i * row_h
        bh = 14
        bw = c.annual_premium_mm / max_v * inner_w
        tc = trend_colors.get(c.market_trend, text_dim)
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh - 1}" fill="{text_dim}" font-size="10" text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(c.coverage_type[:34])}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bh}" fill="{tc}" opacity="0.80"/>'
            f'<text x="{pad_l + bw + 4:.1f}" y="{y + bh - 1}" fill="{P["text_dim"]}" font-size="10" font-family="JetBrains Mono,monospace">${c.annual_premium_mm:,.2f}M</text>'
            f'<text x="{w - 4}" y="{y + bh - 1}" fill="{tc}" font-size="9" text-anchor="end" font-family="JetBrains Mono,monospace">{c.market_trend}</text>'
        )
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{"".join(bars)}'
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Annual Insurance Premium by Coverage Type</text></svg>')


def _coverages_table(coverages) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    trend_colors = {"hardening": P["negative"], "stable": P["accent"], "softening": P["positive"]}
    cols = [("Coverage Type","left"),("Premium ($M)","right"),("% of Rev","right"),("Limits ($M)","right"),("Retention ($M)","right"),("Carrier","left"),("Renewal","left"),("Market Trend","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(coverages):
        rb = panel_alt if i % 2 == 0 else bg
        tc = trend_colors.get(c.market_trend, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.coverage_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${c.annual_premium_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.pct_of_revenue * 100:.3f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">${c.limits_mm:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${c.retention_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.carrier)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.renewal_date)}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{c.market_trend}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _specialty_table(specs) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    cols = [("Specialty","left"),("Headcount","right"),("Premium/Provider ($K)","right"),("Total Annual ($K)","right"),("Claim Freq /100","right"),("Avg Severity ($K)","right"),("Loss Ratio","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(specs):
        rb = panel_alt if i % 2 == 0 else bg
        lr_c = P["positive"] if s.loss_ratio < 0.6 else (P["warning"] if s.loss_ratio < 0.9 else P["negative"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.specialty)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s.headcount}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${s.premium_per_provider_k:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${s.total_annual_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.claim_frequency:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${s.avg_severity_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{lr_c};font-weight:600">{s.loss_ratio:.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _claims_table(claims) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    stat_colors = {"open": P["warning"], "litigation": P["negative"], "settled": P["accent"], "closed": P["positive"]}
    cols = [("Claim ID","left"),("Specialty","left"),("Accident Year","right"),("Reserve ($M)","right"),("Case ($M)","right"),("Status","left"),("Projected Resolution","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(claims):
        rb = panel_alt if i % 2 == 0 else bg
        sc = stat_colors.get(c.status, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(c.claim_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.specialty)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.accident_year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]};font-weight:600">${c.reserve_mm:,.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${c.case_mm:,.3f}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{c.status}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.projected_resolution)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _tail_table(tail) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Structure","left"),("Upfront Cost ($M)","right"),("Coverage (yrs)","right"),("Ongoing Risk ($M)","right"),("Recommended","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, t in enumerate(tail):
        rb = panel_alt if i % 2 == 0 else bg
        rec_c = pos if t.recommended else P["text_faint"]
        yrs_str = "unlimited" if t.coverage_period_yrs >= 99 else f"{t.coverage_period_yrs}"
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(t.structure)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${t.upfront_cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{yrs_str}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"] if t.ongoing_risk_mm else text_dim}">${t.ongoing_risk_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rec_c};border:1px solid {rec_c};border-radius:2px;letter-spacing:0.06em">{"RECOMMENDED" if t.recommended else "—"}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _captive_table(captive) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Structure","left"),("Retained Loss ($M)","right"),("Tax Benefit ($M)","right"),("Admin Cost ($M)","right"),("Net Benefit ($M)","right"),("Viable","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(captive):
        rb = panel_alt if i % 2 == 0 else bg
        vc = pos if c.viable else P["text_faint"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.structure)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${c.annual_retained_loss_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${c.tax_benefit_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${c.admin_cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${c.net_benefit_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{vc};border:1px solid {vc};border-radius:2px;letter-spacing:0.06em">{"viable" if c.viable else "not-viable"}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_insurance(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Physician Services") or "Physician Services"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    revenue = _f("revenue", 100.0)
    providers = _i("providers", 50)

    from rcm_mc.data_public.insurance_tracker import compute_insurance
    r = compute_insurance(sector=sector, revenue_mm=revenue, total_providers=providers)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Annual Insurance", f"${r.total_annual_insurance_mm:,.2f}M", "", "") +
        ck_kpi_block("% of Revenue", f"{r.insurance_pct_of_revenue * 100:.2f}%", "", "") +
        ck_kpi_block("Coverage Limits", f"${r.total_coverage_limits_mm:,.0f}M", "total", "") +
        ck_kpi_block("Open Reserves", f"${r.risk_adjusted_reserve_mm:,.2f}M", "", "") +
        ck_kpi_block("Deal Tail Cost", f"${r.total_deal_insurance_cost_mm:,.2f}M", "", "") +
        ck_kpi_block("Market Hardening", f"+${r.market_hardening_impact_mm:,.2f}M", "next renewal", "") +
        ck_kpi_block("Coverages", str(len(r.coverages)), "", "") +
        ck_kpi_block("Open Claims", str(sum(1 for c in r.open_claims if c.status in ("open", "litigation"))), "", "")
    )

    cov_svg = _coverage_svg(r.coverages)
    cov_tbl = _coverages_table(r.coverages)
    spec_tbl = _specialty_table(r.specialty_premiums)
    claim_tbl = _claims_table(r.open_claims)
    tail_tbl = _tail_table(r.tail_coverage)
    captive_tbl = _captive_table(r.captive)

    form = f"""
<form method="GET" action="/insurance-tracker" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector<input name="sector" value="{_html.escape(sector)}" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:160px"/></label>
  <label style="font-size:11px;color:{text_dim}">Revenue ($M)<input name="revenue" value="{revenue}" type="number" step="10" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/></label>
  <label style="font-size:11px;color:{text_dim}">Providers<input name="providers" value="{providers}" type="number" step="5" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/></label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Insurance &amp; Malpractice Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Malpractice, D&amp;O, cyber, tail coverage, captive analysis — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  {form}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Premium by Coverage Type</div>{cov_svg}</div>
  <div style="{cell}"><div style="{h3}">Coverage Portfolio Detail</div>{cov_tbl}</div>
  <div style="{cell}"><div style="{h3}">Malpractice Premium by Specialty</div>{spec_tbl}</div>
  <div style="{cell}"><div style="{h3}">Open Claim Reserves</div>{claim_tbl}</div>
  <div style="{cell}"><div style="{h3}">Tail Coverage Options (Transaction)</div>{tail_tbl}</div>
  <div style="{cell}"><div style="{h3}">Captive Insurance Analysis</div>{captive_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Insurance Thesis:</strong> ${r.total_annual_insurance_mm:,.2f}M annual insurance spend
    ({r.insurance_pct_of_revenue * 100:.2f}% of revenue) across {len(r.coverages)} coverage lines. Hardening market adds
    ~${r.market_hardening_impact_mm:,.2f}M at next renewal. Deal-time tail coverage cost ${r.total_deal_insurance_cost_mm:,.2f}M —
    non-negotiable for rep and warranty clarity. Captive analysis shows material savings opportunity at scale.
  </div>
</div>"""

    return chartis_shell(body, "Insurance Tracker", active_nav="/insurance-tracker")
