"""Medicare Advantage Contract Analyzer — /ma-contracts."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _plans_table(plans) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Plan","left"),("Type","left"),("Enrollees","right"),("RAF","right"),
            ("Benchmark PMPM","right"),("Bid PMPM","right"),("Rebate","right"),("Star","center"),
            ("Bonus","right"),("MLR","right"),("Margin PMPM","right"),("Revenue ($M)","right"),("Margin ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(plans):
        rb = panel_alt if i % 2 == 0 else bg
        star_c = pos if p.star_rating >= 4.0 else (P["warning"] if p.star_rating >= 3.5 else P["negative"])
        mlr_c = neg if p.mlr_pct > 0.88 else (P["warning"] if p.mlr_pct > 0.85 else pos)
        mpmpm_c = pos if p.margin_pmpm > 75 else (acc if p.margin_pmpm > 40 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(p.plan_name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(p.plan_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{p.enrollment:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{p.raf_score:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${p.benchmark_pmpm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${p.bid_pmpm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${p.rebate_pmpm:,.2f}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{star_c};font-weight:700">{p.star_rating:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos if p.quality_bonus_pct > 0 else text_dim}">{p.quality_bonus_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{mlr_c};font-weight:600">{p.mlr_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{mpmpm_c};font-weight:600">${p.margin_pmpm:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${p.annual_revenue_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${p.annual_margin_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _raf_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; warn = P["warning"]; acc = P["accent"]
    cols = [("HCC Category","left"),("Prevalence","right"),("RAF Contrib","right"),
            ("Current Capture","right"),("Target Capture","right"),("Gap","right"),("Incremental Rev ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        gap = r.target_capture_pct - r.current_capture_pct
        gap_c = warn if gap > 0.12 else text_dim
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(r.hcc_category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.prevalence_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{r.avg_raf_contribution:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{r.current_capture_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{r.target_capture_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{gap_c};font-weight:600">+{gap * 100:.1f}pp</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${r.incremental_revenue_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _stars_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Measure Domain","left"),("Current","right"),("Target","right"),
            ("Weight","right"),("Bonus Revenue ($M)","right"),("Priority","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    pri_colors = {"critical": neg, "high": warn, "standard": text_dim}
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        pc = pri_colors.get(s.priority, text_dim)
        curr_c = pos if s.current_score >= 4.0 else (warn if s.current_score >= 3.5 else neg)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.measure_domain)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{curr_c};font-weight:700">{s.current_score:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{s.target_score:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.weight * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${s.bonus_revenue_mm:,.2f}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;letter-spacing:0.06em">{_html.escape(s.priority)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _v28_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Plan Segment","left"),("V24 RAF","right"),("V28 RAF","right"),
            ("Delta","right"),("Revenue Impact ($M)","right"),("Full Blend Year","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, v in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(v.plan_segment)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{v.v24_raf:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{v.v28_raf:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">{v.raf_delta:+.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">${v.revenue_impact_mm:+,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{v.transition_year}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _mlr_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Component","left"),("PMPM Cost","right"),("% Premium","right"),
            ("YTD Actual","right"),("Target","right"),("Variance","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        var_c = neg if m.variance > 0.002 else (pos if m.variance < -0.002 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(m.component)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${m.pmpm_cost:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{m.pct_of_premium * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{m.ytd_actual * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{m.target * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{var_c};font-weight:600">{m.variance * 100:+.2f}pp</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _supplemental_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Benefit","left"),("Utilization","right"),("Cost PMPM","right"),
            ("Enrollment Impact","left"),("ROI Score","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        roi_c = pos if s.roi_score >= 4.0 else (acc if s.roi_score >= 3.5 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.benefit)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s.utilization_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${s.cost_pmpm:.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.enrollment_impact)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{roi_c};font-weight:700">{s.roi_score:.1f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _plan_margin_svg(plans) -> str:
    if not plans: return ""
    w, h = 560, 220
    pad_l, pad_r, pad_t, pad_b = 50, 20, 30, 70
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    max_v = max(p.annual_revenue_mm for p in plans) or 1
    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]
    n = len(plans)
    bar_w = (inner_w - (n - 1) * 8) / n
    bars = []
    for i, p in enumerate(plans):
        x = pad_l + i * (bar_w + 8)
        rev_h = p.annual_revenue_mm / max_v * inner_h
        margin_h = p.annual_margin_mm / max_v * inner_h
        y_rev = (h - pad_b) - rev_h
        y_margin = (h - pad_b) - margin_h
        bars.append(
            f'<rect x="{x:.1f}" y="{y_rev:.1f}" width="{bar_w:.1f}" height="{rev_h:.1f}" fill="{acc}" opacity="0.35"/>'
            f'<rect x="{x:.1f}" y="{y_margin:.1f}" width="{bar_w:.1f}" height="{margin_h:.1f}" fill="{pos}" opacity="0.9"/>'
            f'<text x="{x + bar_w / 2:.1f}" y="{y_rev - 4:.1f}" fill="{text_dim}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">${p.annual_revenue_mm:.0f}M</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">{_html.escape(p.plan_name[:16])}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 26}" fill="{text_faint}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">{_html.escape(p.plan_type)}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 38}" fill="{text_faint}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">★ {p.star_rating:.1f}</text>'
        )
    legend = (
        f'<rect x="10" y="{h - 18}" width="10" height="10" fill="{acc}" opacity="0.35"/><text x="24" y="{h - 9}" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">revenue</text>'
        f'<rect x="90" y="{h - 18}" width="10" height="10" fill="{pos}"/><text x="104" y="{h - 9}" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">margin</text>'
    )
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{"".join(bars)}{legend}'
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Annual Revenue vs Margin by MA Plan</text></svg>')


def render_ma_contracts(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    lives = _i("lives", 85000)
    benchmark = _f("benchmark", 1050.0)

    from rcm_mc.data_public.ma_contracts import compute_ma_contracts
    r = compute_ma_contracts(total_lives=lives, regional_benchmark_pmpm=benchmark)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]

    kpi_strip = (
        ck_kpi_block("Enrollment", f"{r.total_enrollment:,}", "", "") +
        ck_kpi_block("Bench PMPM", f"${r.blended_benchmark_pmpm:,.0f}", "", "") +
        ck_kpi_block("Bid PMPM", f"${r.blended_bid_pmpm:,.0f}", "", "") +
        ck_kpi_block("Star (wtd)", f"{r.weighted_star_rating:.2f}", "", "") +
        ck_kpi_block("MLR", f"{r.blended_mlr * 100:.1f}%", "", "") +
        ck_kpi_block("Revenue", f"${r.annual_revenue_mm:,.0f}M", "", "") +
        ck_kpi_block("Margin", f"${r.annual_margin_mm:,.0f}M", f"({r.margin_pct * 100:.1f}%)", "") +
        ck_kpi_block("V28 Net", f"${r.v28_net_impact_mm:+,.1f}M", "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    plans_tbl = _plans_table(r.plans)
    svg = _plan_margin_svg(r.plans)
    raf_tbl = _raf_table(r.raf)
    stars_tbl = _stars_table(r.stars)
    v28_tbl = _v28_table(r.v28)
    mlr_tbl = _mlr_table(r.mlr_components)
    supp_tbl = _supplemental_table(r.supplemental)

    form = f"""
<form method="GET" action="/ma-contracts" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">MA Lives<input name="lives" value="{lives}" type="number" step="5000" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:100px"/></label>
  <label style="font-size:11px;color:{text_dim}">Benchmark PMPM<input name="benchmark" value="{benchmark}" type="number" step="25" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:90px"/></label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    raf_opportunity = sum(x.incremental_revenue_mm for x in r.raf)
    star_opportunity = sum(x.bonus_revenue_mm for x in r.stars)

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Medicare Advantage Contract Analyzer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Bid/benchmark · RAF optimization · Stars · MLR · V28 transition · supplementals — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  {form}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Revenue vs Margin by MA Plan</div>{svg}</div>
  <div style="{cell}"><div style="{h3}">MA Plan Portfolio — Benchmark, Bid, Star, MLR, Margin</div>{plans_tbl}</div>
  <div style="{cell}"><div style="{h3}">RAF Optimization — HCC Capture Opportunities</div>{raf_tbl}</div>
  <div style="{cell}"><div style="{h3}">Star Rating Roadmap — Quality Bonus Unlock</div>{stars_tbl}</div>
  <div style="{cell}"><div style="{h3}">V28 Risk Model Transition — Revenue Headwind</div>{v28_tbl}</div>
  <div style="{cell}"><div style="{h3}">MLR Waterfall — Medical Cost Components vs Target</div>{mlr_tbl}</div>
  <div style="{cell}"><div style="{h3}">Supplemental Benefit Portfolio — Utilization &amp; ROI</div>{supp_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">MA Thesis:</strong> {r.total_enrollment:,} MA lives at ${r.blended_bid_pmpm:,.0f} bid PMPM.
    ${r.annual_revenue_mm:,.0f}M revenue, ${r.annual_margin_mm:,.0f}M margin ({r.margin_pct * 100:.1f}%), MLR {r.blended_mlr * 100:.1f}%, weighted star {r.weighted_star_rating:.2f}.
    V28 phase-in erodes ${abs(r.v28_net_impact_mm):,.1f}M revenue by 2026. Offset via RAF capture (${raf_opportunity:,.1f}M incremental)
    and star uplift to 4.5 (${star_opportunity:,.1f}M bonus). D-SNP/I-SNP segments carry highest margin per life
    but face steepest V28 headwind. Supplemental benefit dollar should follow ROI ranking — OTC and Flex cards lead.
  </div>
</div>"""

    return chartis_shell(body, "Medicare Advantage", active_nav="/ma-contracts")
