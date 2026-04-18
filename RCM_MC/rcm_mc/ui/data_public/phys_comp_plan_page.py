"""Physician Compensation Plan Designer — /phys-comp-plan."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _models_table(models) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Plan Type","left"),("Base %","right"),("Prod %","right"),("Quality %","right"),
            ("Call %","right"),("Signing %","right"),("Ramp (mo)","right"),("Retention","right"),("Suitable For","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, m in enumerate(models):
        rb = panel_alt if i % 2 == 0 else bg
        ret_c = pos if m.retention_score >= 80 else (P["warning"] if m.retention_score >= 70 else P["negative"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(m.plan_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{m.base_salary_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{m.productivity_bonus_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{m.quality_bonus_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{m.call_pay_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{m.signing_bonus_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{m.ramp_period_months}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ret_c};font-weight:600">{m.retention_score}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.suitable_for)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _providers_table(providers) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Provider","left"),("Specialty","left"),("wRVUs","right"),("Pctile","right"),
            ("Base ($k)","right"),("Prod ($k)","right"),("Quality ($k)","right"),("Call ($k)","right"),
            ("Total ($k)","right"),("$/wRVU","right"),("Comp/Coll","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(providers):
        rb = panel_alt if i % 2 == 0 else bg
        pct_c = pos if p.wrvu_percentile >= 75 else (acc if p.wrvu_percentile >= 50 else text_dim)
        cpc_c = P["warning"] if p.comp_to_collection_pct > 0.75 else (pos if p.comp_to_collection_pct < 0.55 else text)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(p.provider_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(p.specialty)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{p.wrvu_production:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pct_c};font-weight:600">{p.wrvu_percentile}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${p.base_salary_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">${p.productivity_pay_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${p.quality_bonus_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${p.call_stipend_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${p.total_comp_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${p.comp_per_wrvu:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cpc_c};font-weight:600">{p.comp_to_collection_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _quality_table(pools) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Quality Metric","left"),("Weight","right"),("Threshold","left"),("Max Bonus","right"),("Current","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, q in enumerate(pools):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(q.metric)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{q.weight_pct * 100:.0f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(q.threshold)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]};font-weight:600">{q.max_bonus_pct_of_base * 100:.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{P["warning"]}">{_html.escape(q.current_performance)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _sims_table(sims) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Scenario","left"),("Top 10% ($k)","right"),("Median ($k)","right"),("Bottom 10% ($k)","right"),
            ("Total Pool ($M)","right"),("Retention","right"),("Recruit Score","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(sims):
        rb = panel_alt if i % 2 == 0 else bg
        ret_c = pos if s.retention_projected_pct >= 0.80 else (P["warning"] if s.retention_projected_pct >= 0.70 else P["negative"])
        rec_c = pos if s.recruitment_attractiveness >= 80 else (acc if s.recruitment_attractiveness >= 70 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.scenario)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${s.top_10pct_comp_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.median_comp_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${s.bottom_10pct_comp_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">${s.total_physician_pool_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ret_c};font-weight:600">{s.retention_projected_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{rec_c};font-weight:600">{s.recruitment_attractiveness}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _benchmarks_table(benchmarks) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Specialty","left"),("MGMA Median ($k)","right"),("Our Median ($k)","right"),("Delta","right"),("Position","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    pos_colors = {"above market": pos, "at market": P["accent"], "below market": neg}
    for i, b in enumerate(benchmarks):
        rb = panel_alt if i % 2 == 0 else bg
        delta_c = pos if b.delta_pct > 0.03 else (neg if b.delta_pct < -0.03 else text_dim)
        pc = pos_colors.get(b.market_position, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(b.specialty)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${b.median_comp_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${b.our_median_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{delta_c};font-weight:600">{b.delta_pct * 100:+.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;letter-spacing:0.06em">{_html.escape(b.market_position)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _pool_stacked_svg(sims) -> str:
    if not sims: return ""
    w, h = 560, 220
    pad_l, pad_r, pad_t, pad_b = 50, 20, 30, 60
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    max_v = max(s.top_10pct_comp_k for s in sims) or 1
    bg = P["panel"]; pos = P["positive"]; acc = P["accent"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]
    n = len(sims)
    bar_w = (inner_w - (n - 1) * 12) / n
    bars = []
    for i, s in enumerate(sims):
        x = pad_l + i * (bar_w + 12)
        for val, color in [(s.top_10pct_comp_k, pos), (s.median_comp_k, acc), (s.bottom_10pct_comp_k, text_dim)]:
            bh = val / max_v * inner_h
            y = (h - pad_b) - bh
            bars.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{color}" opacity="0.85" stroke="{bg}" stroke-width="1"/>'
            )
        # Label
        bars.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">{_html.escape(s.scenario[:18])}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 26}" fill="{text_faint}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">ret {s.retention_projected_pct * 100:.0f}%</text>'
        )
    legend = (
        f'<rect x="10" y="{h - 18}" width="10" height="10" fill="{pos}"/><text x="24" y="{h - 9}" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">top 10%</text>'
        f'<rect x="90" y="{h - 18}" width="10" height="10" fill="{acc}"/><text x="104" y="{h - 9}" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">median</text>'
        f'<rect x="170" y="{h - 18}" width="10" height="10" fill="{text_dim}"/><text x="184" y="{h - 9}" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">bottom 10%</text>'
    )
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{"".join(bars)}{legend}'
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Comp Distribution by Plan Scenario</text></svg>')


def render_phys_comp_plan(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    sector = params.get("sector", "Primary Care")
    revenue = _f("revenue", 100.0)
    physicians = _i("physicians", 30)

    from rcm_mc.data_public.phys_comp_plan import compute_phys_comp_plan
    r = compute_phys_comp_plan(sector=sector, practice_revenue_mm=revenue, total_physicians=physicians)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    pool_pct = (r.total_physician_pool_mm / r.practice_revenue_mm) if r.practice_revenue_mm else 0
    kpi_strip = (
        ck_kpi_block("Practice Revenue", f"${r.practice_revenue_mm:,.1f}M", "", "") +
        ck_kpi_block("Physicians", f"{r.total_physicians}", "", "") +
        ck_kpi_block("Physician Pool", f"${r.total_physician_pool_mm:,.2f}M", "", "") +
        ck_kpi_block("Pool / Revenue", f"{pool_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Comp / Coll", f"{r.comp_to_collection_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Plan Models", str(len(r.models)), "", "") +
        ck_kpi_block("Quality Pools", str(len(r.quality_pools)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    sims_svg = _pool_stacked_svg(r.simulations)
    models_tbl = _models_table(r.models)
    providers_tbl = _providers_table(r.providers)
    quality_tbl = _quality_table(r.quality_pools)
    sims_tbl = _sims_table(r.simulations)
    bench_tbl = _benchmarks_table(r.benchmarks)

    sectors = ["Primary Care", "Orthopedics", "Cardiology", "Dermatology", "Gastroenterology", "Physician Services"]
    sector_opts = "".join(f'<option value="{_html.escape(s)}"{" selected" if s == sector else ""}>{_html.escape(s)}</option>' for s in sectors)

    form = f"""
<form method="GET" action="/phys-comp-plan" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector<select name="sector" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace">{sector_opts}</select></label>
  <label style="font-size:11px;color:{text_dim}">Revenue ($M)<input name="revenue" value="{revenue}" type="number" step="10" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/></label>
  <label style="font-size:11px;color:{text_dim}">Physicians<input name="physicians" value="{physicians}" type="number" step="1" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/></label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Physician Compensation Plan Designer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">wRVU production · quality pools · partner track · VBC — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  {form}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Comp Plan Model Library</div>{models_tbl}</div>
  <div style="{cell}"><div style="{h3}">Plan Simulation — Distribution & Retention</div>{sims_svg}</div>
  <div style="{cell}"><div style="{h3}">Plan Scenario Detail</div>{sims_tbl}</div>
  <div style="{cell}"><div style="{h3}">Per-Provider Compensation (Sample)</div>{providers_tbl}</div>
  <div style="{cell}"><div style="{h3}">Quality Bonus Pool Structure</div>{quality_tbl}</div>
  <div style="{cell}"><div style="{h3}">MGMA Specialty Benchmarking</div>{bench_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Comp Plan Thesis:</strong> {r.total_physicians} physicians at ${r.practice_revenue_mm:,.1f}M revenue.
    Recommended plan: <strong style="color:{text}">{_html.escape(r.recommended_model)}</strong>.
    Total physician pool ${r.total_physician_pool_mm:,.2f}M ({pool_pct * 100:.1f}% of revenue);
    comp-to-collection {r.comp_to_collection_pct * 100:.1f}%. Hybrid production + quality plans consistently outperform on both
    retention (82+) and recruitment attractiveness, vs pure-base plans that underpay top quartile and pure-EWYK plans that fail to retain.
  </div>
</div>"""

    return chartis_shell(body, "Physician Comp Plan", active_nav="/phys-comp-plan")
