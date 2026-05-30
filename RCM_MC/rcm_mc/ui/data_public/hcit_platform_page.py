"""HCIT / SaaS Platform Analyzer — /hcit-platform."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_illustrative_note, ck_bar_row, ck_value_anchor, ck_scatter, ck_source_purpose
from rcm_mc.ui.data_public._benchmark_panels import data_required_panel


def _tam_scatter(items):
    """Quadrant — current penetration vs revenue opportunity, so low-
    penetration / high-opportunity sub-TAMs (upper-left) = whitespace."""
    import statistics
    pts, xs, ys = [], [], []
    for t in items:
        x = t.current_penetration_pct * 100.0; y = t.revenue_opportunity_mm
        tn = ('positive' if t.current_penetration_pct < 0.10 else 'teal' if t.current_penetration_pct < 0.30 else 'navy')
        pts.append((x, y, t.sub_tam, tn)); xs.append(x); ys.append(y)
    return ck_scatter(
        pts, x_label='Current penetration %', y_label='Revenue opportunity ($M)',
        x_ref=(statistics.median(xs) if xs else None), y_ref=(statistics.median(ys) if ys else None),
        caption='Each dot = a sub-TAM · upper-left = low penetration + high opportunity (whitespace) · tone = headroom',
    )


def _segments_chart(items) -> str:
    """Lead chart — HCIT segments ranked by ARR (tone by NRR)."""
    total = sum(s.annual_arr_mm for s in items) or 1.0
    rows = []
    for s in sorted(items, key=lambda s: s.annual_arr_mm, reverse=True):
        tone = "positive" if s.nrr_pct >= 1.10 else ("teal" if s.nrr_pct >= 1.0 else "warning")
        rows.append(ck_bar_row(s.segment, f"${s.annual_arr_mm:,.1f}M",
                               s.annual_arr_mm / total * 100.0, tone=tone))
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of total ARR \u00b7 '
            'value = ARR ($M) \u00b7 tone = net revenue retention</div></div>')



def _segments_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]; warn = P["warning"]
    cols = [("Segment","left"),("Customers","right"),("ACV ($k)","right"),("ARR ($M)","right"),
            ("NRR","right"),("Gross Churn","right"),("LTV ($k)","right"),("CAC Payback (mo)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        nrr_c = pos if s.nrr_pct >= 1.12 else (acc if s.nrr_pct >= 1.06 else warn)
        pb_c = pos if s.cac_payback_months <= 15 else (acc if s.cac_payback_months <= 20 else warn)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.segment)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{s.customer_count}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${s.acv_k:,.1f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${s.annual_arr_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{nrr_c};font-weight:700">{s.nrr_pct:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]}">{s.gross_churn_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""${s.ltv_k:,.0f}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pb_c};font-weight:600">{s.cac_payback_months}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _products_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Product","left"),("Category","center"),("ARR ($M)","right"),("YoY Growth","right"),("Gross Margin","right"),("Users","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        g_c = pos if p.growth_yoy_pct >= 0.40 else (acc if p.growth_yoy_pct >= 0.20 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.product)}""", mono=True, weight=600)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(p.category)}</td>',
            f'{ck_data_cell(f"""${p.arr_mm:,.2f}""", align="right", mono=True, weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{g_c};font-weight:700">{p.growth_yoy_pct * 100:+.1f}%</td>',
            f'{ck_data_cell(f"""{p.gross_margin_pct * 100:.1f}%""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""{p.users:,}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _metrics_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]; warn = P["warning"]
    cols = [("Metric","left"),("Current","right"),("Top Quartile","right"),("Median","right"),("Percentile","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = pos if m.percentile >= 75 else (acc if m.percentile >= 55 else warn)
        if m.unit == "pct":
            cv, tq, md = f"{m.current * 100:.1f}%", f"{m.benchmark_top_quartile * 100:.1f}%", f"{m.benchmark_median * 100:.1f}%"
        elif m.unit == "mult":
            cv, tq, md = f"{m.current:.2f}x", f"{m.benchmark_top_quartile:.2f}x", f"{m.benchmark_median:.2f}x"
        else:
            cv, tq, md = f"{m.current:.1f}", f"{m.benchmark_top_quartile:.1f}", f"{m.benchmark_median:.1f}"
        cells = [
            f'{ck_data_cell(f"""{_html.escape(m.metric)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{cv}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{tq}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""{md}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">P{m.percentile}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _tam_chart(items) -> str:
    """Summary chart — sub-TAMs by revenue opportunity (tone by headroom)."""
    def _tone(t):
        if t.current_penetration_pct < 0.10: return "positive"
        if t.current_penetration_pct < 0.30: return "teal"
        return "navy"
    top = sorted(items, key=lambda t: t.revenue_opportunity_mm, reverse=True)
    total = sum(t.revenue_opportunity_mm for t in top) or 1.0
    rows = [ck_bar_row(f"{t.sub_tam}",
            f"${t.revenue_opportunity_mm:,.1f}M opp · {t.current_penetration_pct * 100:.0f}% pen",
            t.revenue_opportunity_mm / total * 100.0, tone=_tone(t)) for t in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of revenue opportunity by sub-TAM '
            '· value = opportunity ($M) + penetration · tone = headroom (low pen = more upside)</div></div>')


def _tam_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Sub-TAM","left"),("TAM ($M)","right"),("Serviceable ($M)","right"),("Current Penetration","right"),
            ("Y3 Target","right"),("Revenue Opportunity ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(t.sub_tam)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${t.tam_mm:,.0f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${t.serviceable_tam_mm:,.0f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{t.current_penetration_pct * 100:.2f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{t.y3_target_penetration_pct * 100:.2f}%""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""${t.revenue_opportunity_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _comps_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]; neg = P["negative"]
    cols = [("Company","left"),("ARR ($M)","right"),("Growth","right"),("EV/Rev Mult","right"),("Implied EV ($M)","right"),("Profile","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        g_c = pos if c.growth_yoy_pct > 0.25 else (acc if c.growth_yoy_pct > 0.10 else (text_dim if c.growth_yoy_pct >= 0 else neg))
        mult_c = pos if c.ev_revenue_multiple >= 10.0 else (acc if c.ev_revenue_multiple >= 5.0 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.company)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${c.arr_mm:,.0f}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{g_c};font-weight:700">{c.growth_yoy_pct * 100:+.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{mult_c};font-weight:700">{c.ev_revenue_multiple:.2f}x</td>',
            f'{ck_data_cell(f"""${c.implied_ev_mm:,.0f}""", align="right", mono=True, tone="pos", weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.profile)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_hcit_platform(params: dict = None) -> str:
    from rcm_mc.data_public.hcit_platform import compute_hcit_platform
    r = compute_hcit_platform()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Total ARR", f"${r.total_arr_mm:,.1f}M", "", "") +
        ck_kpi_block("Growth YoY", f"{r.arr_growth_pct * 100:+.1f}%", "", "") +
        ck_kpi_block("NRR", f"{r.total_nrr_pct:.2f}x", "", "") +
        ck_kpi_block("Gross Margin", f"{r.total_gross_margin_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Rule of 40", f"{r.rule_of_40_score * 100:.0f}", "", "") +
        ck_kpi_block("Magic Number", f"{r.magic_number:.2f}", "", "") +
        ck_kpi_block("Customers", f"{r.total_customers:,}", "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    s_chart = _segments_chart(r.segments)
    s_tbl = _segments_table(r.segments)
    value_anchor = ck_value_anchor(
        "HCIT Platform",
        f"${r.total_arr_mm:,.1f}M ARR",
        delta=f"{r.arr_growth_pct * 100:.0f}% growth \u00b7 Rule-of-40 {r.rule_of_40_score * 100:.0f} \u00b7 {r.total_nrr_pct * 100:.0f}% NRR \u00b7 {r.total_customers:,} customers",
        tone="positive",
    )
    p_tbl = _products_table(r.products)
    m_tbl = _metrics_table(r.metrics)
    t_tbl = _tam_table(r.tam)
    t_chart = _tam_chart(r.tam)
    t_scatter = _tam_scatter(r.tam)
    c_tbl = _comps_table(r.comps)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    tam_opp = sum(t.revenue_opportunity_mm for t in r.tam)
    # 2026-05-30 audit P5 editorial: in healthcare PE, HCIT platforms
    # ARE the SaaS category being analyzed — the slash-dual was a
    # subtype restatement. Eyebrow reads HCIT PLATFORM.
    page_title = ck_page_title(
        "HCIT Platform Analyzer",
        eyebrow="HCIT PLATFORM",
        meta=f"${r.total_arr_mm:,.1f}M ARR growing {r.arr_growth_pct * 100:+.1f}% YoY · {r.total_nrr_pct:.2f}x NRR at {r.total_gross_margin_pct * 100:.1f}% gross margin · Rule of 40: {r.rule_of_40_score * 100:.0f} · Magic Number: {r.magic_number:.2f} · ${tam_opp:,.0f}M TAM opportunity across {len(r.tam)} sub-markets",
    )

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {data_required_panel(P, title="HCIT Platform", needed=[("system","system / application"),("vendor","vendor"),("category","EHR / RCM / PM / analytics"),("annual_cost","annual $"),("contract_end","contract end (YYYY-MM-DD)"),("modules","modules in use")], template="ehr_vendor_stack_template.csv", request_from="CIO / IT", activates="EHR/RCM stack cost + contract-renewal map", guide_hint="What HCIT/EHR vendor-stack data do I need to upload?")}
  {ck_illustrative_note("figures")}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Customer Segment Economics</div>{s_chart}{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Product Line Portfolio</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">SaaS Benchmark Metrics</div>{m_tbl}</div>
  <div style="{cell}"><div style="{h3}">Sub-TAM Penetration &amp; Revenue Opportunity</div>{t_chart}{t_scatter}{t_tbl}</div>
  <div style="{cell}"><div style="{h3}">Public &amp; Private Comp Universe</div>{c_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">HCIT SaaS Thesis:</strong> ${r.total_arr_mm:,.1f}M ARR growing {r.arr_growth_pct * 100:+.0f}% with {r.total_nrr_pct:.2f}x NRR and {r.total_gross_margin_pct * 100:.0f}% gross margin.
    Rule of 40 at {r.rule_of_40_score * 100:.0f} places platform in top third of healthcare SaaS; magic number {r.magic_number:.2f} signals efficient growth.
    Large health system / payer / PE-backed customer segments generate highest LTV and NRR (1.12-1.18x) — expansion motion is a reliable revenue compounder.
    Aggregate TAM opportunity ${tam_opp:,.0f}M over 3-year horizon across 6 sub-markets.
    Public comp set trades 3-13x EV/Revenue depending on growth/margin profile; private comps (Cotiviti, HealthEdge, Clario) support premium exit multiples for scaled platforms with defensible data assets.
  </div>
</div>"""

    body = ck_source_purpose(
        purpose="Assess an HCIT / SaaS platform target.",
        universe="illustrative", source="No platform-data source",
        next_action="Define source/scope or defer") + body
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "HCIT Platform", active_nav="/hcit-platform",
        editorial_intro={
            "eyebrow": "HCIT PLATFORM",
            "headline": "What the hcit platform page reveals on this deal.",
            "italic_word": "reveals",
        })
