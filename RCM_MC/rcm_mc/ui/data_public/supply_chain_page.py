"""Supply Chain page — /supply-chain."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _spend_bars_svg(cats) -> str:
    if not cats: return ""
    sorted_c = sorted(cats, key=lambda c: -c.annual_spend_mm)
    w = 540; row_h = 24
    h = len(sorted_c) * row_h + 30
    pad_l = 220; pad_r = 60
    inner_w = w - pad_l - pad_r
    max_v = max(c.annual_spend_mm for c in sorted_c) or 1
    bg = P["panel"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]
    var_colors = {"above": P["negative"], "benchmark": P["accent"], "below": P["positive"]}
    bars = []
    for i, c in enumerate(sorted_c):
        y = 20 + i * row_h
        bh = 14
        bw = c.annual_spend_mm / max_v * inner_w
        color = var_colors.get(c.variance, text_dim)
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh - 1}" fill="{text_dim}" font-size="10" text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(c.category[:26])}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bh}" fill="{color}" opacity="0.85"/>'
            f'<text x="{pad_l + bw + 4:.1f}" y="{y + bh - 1}" fill="{P["text_dim"]}" font-size="10" font-family="JetBrains Mono,monospace">${c.annual_spend_mm:,.2f}M · {c.pct_of_revenue * 100:.1f}%</text>'
        )
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{"".join(bars)}'
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Supply Spend by Category</text></svg>')


def _savings_svg(levers) -> str:
    if not levers: return ""
    sorted_l = sorted(levers, key=lambda l: -l.annual_savings_mm)
    w = 540; row_h = 22
    h = len(sorted_l) * row_h + 30
    pad_l = 260; pad_r = 80
    inner_w = w - pad_l - pad_r
    max_v = max(l.annual_savings_mm for l in sorted_l) or 1
    bg = P["panel"]; pos = P["positive"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]
    risk_colors = {"low": pos, "medium": P["warning"], "high": P["negative"]}
    bars = []
    for i, l in enumerate(sorted_l):
        y = 20 + i * row_h
        bh = 12
        bw = l.annual_savings_mm / max_v * inner_w
        rc = risk_colors.get(l.risk, text_dim)
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh - 1}" fill="{text_dim}" font-size="10" text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(l.lever[:35])}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bh}" fill="{pos}" opacity="0.85"/>'
            f'<text x="{pad_l + bw + 4:.1f}" y="{y + bh - 1}" fill="{P["text_dim"]}" font-size="10" font-family="JetBrains Mono,monospace">${l.annual_savings_mm:,.2f}M</text>'
            f'<text x="{w - 4}" y="{y + bh - 1}" fill="{rc}" font-size="9" text-anchor="end" font-family="JetBrains Mono,monospace">{l.risk}</text>'
        )
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{"".join(bars)}'
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Annual Savings by Lever</text></svg>')


def _spend_table(cats) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    var_colors = {"above": P["negative"], "benchmark": P["accent"], "below": P["positive"]}
    cols = [("Category","left"),("Annual Spend ($M)","right"),("% of Rev","right"),("% of Supply","right"),("Benchmark %","right"),("Variance","left"),("Top Vendor","left"),("Vendor Share","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(cats):
        rb = panel_alt if i % 2 == 0 else bg
        vc = var_colors.get(c.variance, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${c.annual_spend_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.pct_of_revenue * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.pct_of_total_supply * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">{c.benchmark_pct_revenue * 100:.2f}%</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{vc};border:1px solid {vc};border-radius:2px;letter-spacing:0.06em">{c.variance}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.top_vendor)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.top_vendor_share * 100:.0f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _levers_table(levers) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    risk_colors = {"low": pos, "medium": P["warning"], "high": P["negative"]}
    cols = [("Lever","left"),("Current","left"),("Target","left"),("Annual Savings ($M)","right"),("One-Time ($M)","right"),("Timeline (mo)","right"),("Risk","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, l in enumerate(levers):
        rb = panel_alt if i % 2 == 0 else bg
        rc = risk_colors.get(l.risk, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(l.lever)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(l.current_state)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{P["accent"]}">{_html.escape(l.target_state)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${l.annual_savings_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${l.one_time_cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{l.timeline_months}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{l.risk}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _vendors_table(vendors) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    risk_colors = {"low": P["positive"], "medium": P["warning"], "high": P["negative"], "critical": P["negative"]}
    cols = [("Vendor","left"),("Category","left"),("Annual Spend ($M)","right"),("Contract End","right"),("Alternatives","right"),("Switching Cost ($M)","right"),("Risk","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, v in enumerate(vendors):
        rb = panel_alt if i % 2 == 0 else bg
        rc = risk_colors.get(v.risk_flag, text_dim)
        alt_c = P["positive"] if v.alternatives_available >= 3 else (P["warning"] if v.alternatives_available >= 2 else P["negative"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(v.vendor)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(v.category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${v.annual_spend_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(v.contract_end)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{alt_c}">{v.alternatives_available}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${v.switching_cost_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{v.risk_flag}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _capex_table(projects) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    prio_colors = {"high": P["negative"], "medium": P["warning"], "low": P["text_faint"]}
    cols = [("Project","left"),("One-Time ($M)","right"),("Annual Savings ($M)","right"),("Payback (yrs)","right"),("Strategic Value","left"),("Priority","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(projects):
        rb = panel_alt if i % 2 == 0 else bg
        pc = prio_colors.get(p.priority, text_dim)
        pay_str = f"{p.payback_years:.1f}" if p.payback_years < 99 else "n/a"
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(p.project)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${p.one_time_cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${p.annual_savings_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{pay_str}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.strategic_value)}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{p.priority}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _inventory_table(inv) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    stat_colors = {"above-benchmark": P["negative"], "above": P["negative"], "below": P["warning"], "benchmark": P["positive"]}
    cols = [("Metric","left"),("Current","right"),("Benchmark","right"),("Unit","left"),("Status","left"),("Capital Tied Up ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, k in enumerate(inv):
        rb = panel_alt if i % 2 == 0 else bg
        sc = stat_colors.get(k.status, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(k.metric)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{k.current:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">{k.benchmark:.3f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(k.unit)}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{k.status}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"] if k.tied_up_capital_mm else text_dim}">${k.tied_up_capital_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_supply_chain(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Physician Services") or "Physician Services"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    revenue = _f("revenue", 80.0)
    mult = _f("mult", 11.0)

    from rcm_mc.data_public.supply_chain import compute_supply_chain
    r = compute_supply_chain(sector=sector, revenue_mm=revenue, exit_multiple=mult)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Supply Spend", f"${r.total_supply_spend_mm:,.1f}M", "", "") +
        ck_kpi_block("Supply % Rev", f"{r.supply_pct_revenue * 100:.1f}%", "", "") +
        ck_kpi_block("Savings Opp", f"${r.total_savings_opportunity_mm:,.1f}M", "", "") +
        ck_kpi_block("EV Uplift", f"${r.ev_uplift_mm:,.0f}M", "", "") +
        ck_kpi_block("Categories", str(len(r.spend_categories)), "", "") +
        ck_kpi_block("Levers", str(len(r.gpo_levers)), "", "") +
        ck_kpi_block("Top Vendors", str(len(r.top_vendors)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    spend_svg = _spend_bars_svg(r.spend_categories)
    savings_svg = _savings_svg(r.gpo_levers)
    spend_tbl = _spend_table(r.spend_categories)
    levers_tbl = _levers_table(r.gpo_levers)
    vendors_tbl = _vendors_table(r.top_vendors)
    capex_tbl = _capex_table(r.capex_projects)
    inv_tbl = _inventory_table(r.inventory_kpis)

    form = f"""
<form method="GET" action="/supply-chain" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector)}" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:160px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Revenue ($M)
    <input name="revenue" value="{revenue}" type="number" step="10" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Exit Multiple
    <input name="mult" value="{mult}" type="number" step="0.5" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Procurement &amp; Supply Chain Analyzer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">GPO leverage, vendor contracts, CapEx, inventory — {_html.escape(sector)} — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  {form}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}"><div style="{h3}">Spend by Category</div>{spend_svg}</div>
    <div style="{cell}"><div style="{h3}">Savings Lever Potential</div>{savings_svg}</div>
  </div>
  <div style="{cell}"><div style="{h3}">Spend Category Detail</div>{spend_tbl}</div>
  <div style="{cell}"><div style="{h3}">Procurement Lever Portfolio</div>{levers_tbl}</div>
  <div style="{cell}"><div style="{h3}">Top Vendor Inventory</div>{vendors_tbl}</div>
  <div style="{cell}"><div style="{h3}">CapEx Project Portfolio</div>{capex_tbl}</div>
  <div style="{cell}"><div style="{h3}">Inventory KPIs</div>{inv_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Supply Chain Thesis:</strong> ${r.total_supply_spend_mm:,.1f}M annual supply spend
    ({r.supply_pct_revenue * 100:.1f}% of revenue). Top 3 levers (GPO tier upgrade, implant standardization,
    direct manufacturer) unlock ~${r.total_savings_opportunity_mm * 0.65:,.1f}M. Total opportunity
    ${r.total_savings_opportunity_mm:,.1f}M annual → ${r.ev_uplift_mm:,.0f}M EV uplift at exit.
  </div>
</div>"""

    return chartis_shell(body, "Supply Chain", active_nav="/supply-chain")
