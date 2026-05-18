"""HCIT / SaaS Platform Analyzer — /hcit-platform."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title


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

    s_tbl = _segments_table(r.segments)
    p_tbl = _products_table(r.products)
    m_tbl = _metrics_table(r.metrics)
    t_tbl = _tam_table(r.tam)
    c_tbl = _comps_table(r.comps)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    tam_opp = sum(t.revenue_opportunity_mm for t in r.tam)
    page_title = ck_page_title(
        "HCIT / SaaS Platform Analyzer",
        eyebrow="HCIT PLATFORM",
        meta=f"${r.total_arr_mm:,.1f}M ARR growing {r.arr_growth_pct * 100:+.1f}% YoY · {r.total_nrr_pct:.2f}x NRR at {r.total_gross_margin_pct * 100:.1f}% gross margin · Rule of 40: {r.rule_of_40_score * 100:.0f} · Magic Number: {r.magic_number:.2f} · ${tam_opp:,.0f}M TAM opportunity across {len(r.tam)} sub-markets",
    )

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Customer Segment Economics</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Product Line Portfolio</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">SaaS Benchmark Metrics</div>{m_tbl}</div>
  <div style="{cell}"><div style="{h3}">Sub-TAM Penetration &amp; Revenue Opportunity</div>{t_tbl}</div>
  <div style="{cell}"><div style="{h3}">Public &amp; Private Comp Universe</div>{c_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">HCIT SaaS Thesis:</strong> ${r.total_arr_mm:,.1f}M ARR growing {r.arr_growth_pct * 100:+.0f}% with {r.total_nrr_pct:.2f}x NRR and {r.total_gross_margin_pct * 100:.0f}% gross margin.
    Rule of 40 at {r.rule_of_40_score * 100:.0f} places platform in top third of healthcare SaaS; magic number {r.magic_number:.2f} signals efficient growth.
    Large health system / payer / PE-backed customer segments generate highest LTV and NRR (1.12-1.18x) — expansion motion is a reliable revenue compounder.
    Aggregate TAM opportunity ${tam_opp:,.0f}M over 3-year horizon across 6 sub-markets.
    Public comp set trades 3-13x EV/Revenue depending on growth/margin profile; private comps (Cotiviti, HealthEdge, Clario) support premium exit multiples for scaled platforms with defensible data assets.
  </div>
</div>"""

    return chartis_shell(body, "HCIT Platform", active_nav="/hcit-platform",
        editorial_intro={
            "eyebrow": "HCIT PLATFORM",
            "headline": "What the hcit platform page reveals on this deal.",
            "italic_word": "reveals",
        })
