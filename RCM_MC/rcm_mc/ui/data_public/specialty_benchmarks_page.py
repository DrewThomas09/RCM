"""Specialty Benchmarks Library — /specialty-benchmarks."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title


def _benchmarks_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Specialty","left"),("Category","left"),("Median Comp ($K)","right"),
            ("P25 / P75","right"),("Median wRVU","right"),("$/wRVU","right"),
            ("Patients/Day","right"),("Overhead %","right"),("Collections/wRVU","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(b.specialty)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(b.category)}</td>',
            f'{ck_data_cell(f"""${b.median_total_comp_k:,.1f}K""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""${b.p25_comp_k:,.0f} / ${b.p75_comp_k:,.0f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{b.median_wrvu_production:,}""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""${b.median_wrvu_comp_per_rvu:.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{b.median_patient_per_day}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{b.median_overhead_pct * 100:.0f}%""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""${b.median_collections_per_rvu:.2f}""", align="right", mono=True, tone="pos", weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _econ_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Specialty","left"),("Rev/FTE ($K)","right"),("EBITDA %","right"),
            ("Commercial %","right"),("Medicare %","right"),("Medicaid %","right"),
            ("PTO Days","right"),("Signing ($K)","right"),("Loan Repay ($K)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        eb_c = pos if e.median_ebitda_margin_pct >= 0.25 else (acc if e.median_ebitda_margin_pct >= 0.15 else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(e.specialty)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${e.median_revenue_per_fte_k:,.1f}K""", align="right", mono=True, weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{eb_c};font-weight:700">{e.median_ebitda_margin_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{e.median_payer_mix_commercial * 100:.0f}%""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""{e.median_payer_mix_medicare * 100:.0f}%""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{e.median_payer_mix_medicaid * 100:.0f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{e.avg_pto_days}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${e.typical_signing_bonus_k}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${e.loan_repayment_k}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _np_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Specialty","left"),("New/Month","right"),("New Rev/Month ($K)","right"),
            ("Mkt Cost/New ($K)","right"),("Referral %","right"),("Digital %","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, n in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(n.specialty)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{n.median_new_patients_monthly}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${n.median_new_patient_spend_monthly_k:.1f}K""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""${n.avg_marketing_cost_per_new_k:.2f}K""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{n.referral_vs_direct_pct * 100:.0f}%""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{n.digital_channel_pct * 100:.0f}%""", align="right", mono=True, tone="acc")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _anc_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Specialty","left"),("Ancillary Services","left"),("Ancillary Rev %","right"),
            ("Capex ($K)","right"),("Payback (mo)","right"),("Incremental EBITDA %","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = pos if a.median_ancillary_rev_pct >= 0.40 else (acc if a.median_ancillary_rev_pct >= 0.30 else text_dim)
        p_c = pos if a.payback_months <= 20 else (acc if a.payback_months <= 25 else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(a.specialty)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:320px">{_html.escape(a.ancillary_services)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{a.median_ancillary_rev_pct * 100:.0f}%</td>',
            f'{ck_data_cell(f"""${a.typical_capex_required_k:,}""", align="right", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">{a.payback_months}</td>',
            f'{ck_data_cell(f"""+{a.incremental_ebitda_pct * 100:.1f}%""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _quality_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Specialty","left"),("Measure","left"),("Industry Median","right"),
            ("Top Decile","right"),("Portfolio","right"),("MIPS Weight","center"),("Payer Incentive (bps)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, q in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = pos if q.portfolio_median >= q.top_decile * 0.9 else (acc if q.portfolio_median >= q.industry_median else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(q.specialty)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text_dim};max-width:340px">{_html.escape(q.measure)}</td>',
            f'{ck_data_cell(f"""{q.industry_median:.3f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{q.top_decile:.3f}""", align="right", mono=True, tone="pos", weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">{q.portfolio_median:.3f}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(q.mips_weight)}</td>',
            f'{ck_data_cell(f"""{q.payer_incentive_bps}""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _staffing_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Specialty","left"),("Role","left"),("Median Ratio","right"),
            ("P25 Ratio","right"),("P75 Ratio","right"),("Typical Comp ($K)","right"),("Turnover %","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = pos if s.turnover_pct <= 0.12 else (acc if s.turnover_pct <= 0.20 else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.specialty)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(s.role)}</td>',
            f'{ck_data_cell(f"""{s.median_per_physician:.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{s.p25_ratio:.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{s.p75_ratio:.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${s.typical_comp_k:.1f}K""", align="right", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{t_c};font-weight:700">{s.turnover_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_specialty_benchmarks(params: dict = None) -> str:
    from rcm_mc.data_public.specialty_benchmarks import compute_specialty_benchmarks
    r = compute_specialty_benchmarks()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Specialties", str(r.total_specialties), "", "") +
        ck_kpi_block("Portfolio Coverage", str(r.specialties_with_portfolio_coverage), "", "") +
        ck_kpi_block("Avg Comp", f"${r.avg_comp_k:,.1f}K", "", "") +
        ck_kpi_block("Avg wRVU", f"{r.avg_wrvu:,.0f}", "", "") +
        ck_kpi_block("Avg Overhead", f"{r.avg_overhead_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Avg EBITDA", f"{r.avg_ebitda_margin_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Quality Measures", str(len(r.quality)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    b_tbl = _benchmarks_table(r.benchmarks)
    e_tbl = _econ_table(r.economics)
    n_tbl = _np_table(r.new_patients)
    a_tbl = _anc_table(r.ancillary)
    q_tbl = _quality_table(r.quality)
    s_tbl = _staffing_table(r.staffing)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    page_title = ck_page_title(
        "Specialty Benchmarks Library",
        eyebrow="SPECIALTY BENCHMARKS",
        meta=f"""{r.total_specialties} specialties · portfolio coverage {r.specialties_with_portfolio_coverage} · MGMA + Sullivan Cotter + Radford sourced · avg comp ${r.avg_comp_k:,.1f}K / {r.avg_wrvu:,.0f} wRVU / {r.avg_overhead_pct * 100:.1f}% overhead / {r.avg_ebitda_margin_pct * 100:.1f}% EBITDA — {r.corpus_deal_count:,} corpus deals""",
    )
    
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Physician Compensation & Productivity Benchmarks</div>{b_tbl}</div>
  <div style="{cell}"><div style="{h3}">Practice Economics by Specialty</div>{e_tbl}</div>
  <div style="{cell}"><div style="{h3}">New Patient Acquisition Benchmarks</div>{n_tbl}</div>
  <div style="{cell}"><div style="{h3}">Ancillary Revenue Opportunities</div>{a_tbl}</div>
  <div style="{cell}"><div style="{h3}">Clinical Quality Benchmarks</div>{q_tbl}</div>
  <div style="{cell}"><div style="{h3}">Staffing Ratios & Labor Benchmarks</div>{s_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Specialty Library Summary:</strong> {r.total_specialties} specialty benchmarks cover physician services, medical specialties, surgical specialties, hospital-based, and procedural categories.
    Compensation range: pediatrics ($245K median) to interventional cardiology ($725K) and orthopedic sports medicine ($785K); wRVU production ranges 4,800 (family medicine) to 9,500 (ortho sports).
    EBITDA margin leaders: plastic surgery aesthetic (42.5%), orthopedic sports medicine (38.5%), dermatology (31.5%) — driven by ancillary revenue mix and commercial payer concentration.
    Top ancillary opportunities: oncology infusion suite (55% ancillary, +18% EBITDA), orthopedic ASC (+14.5%), GI endoscopy center (+12.5%), derma Mohs/aesthetics (+10.5%).
    Quality benchmarks span 13 measures across 8 specialties; portfolio tracks ≥industry median on all measures, reaches top-decile on dermatology biopsy concordance (0.94) and psychiatry depression screening (0.72).
    Staffing ratios: MA-to-physician 1.5-2.2 standard; orthopedic surgery PA/NP leverage 0.8 drives productivity. Turnover watchlist: OR tech/surgical scrub (13.5%), primary care front desk (28.5%), behavioral tech (24.5%).
  </div>
</div>"""

    return chartis_shell(body, "Specialty Benchmarks", active_nav="/specialty-benchmarks",
        editorial_intro={
            "eyebrow": "SPECIALTY BENCHMARKS",
            "headline": "What the specialty benchmarks page reveals on this deal.",
            "italic_word": "reveals",
        })
