"""US Healthcare Operational & Benchmarking Reference — /benchmark-reference.

The granular benchmark-data layer: six chart-ready data domains (quality
measure weights, procedure/code frequency, physician compensation &
productivity, hospital cost structure, disease prevalence, and
utilization/spending) populated with current sourced figures.

Unlike the seed-corpus analyzer pages, every figure here is a published
national reference number with a named primary source, so the page carries its
own per-row source column + a caveats panel rather than the blanket
illustrative-corpus banner.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_bar_row, ck_data_cell, ck_kpi_block,
    ck_page_actions, ck_page_title, ck_source_purpose, ck_value_anchor,
)

_ACCESS_TONE = {"free": P["positive"], "proprietary": P["warning"], "estimate": P["text_dim"]}


def _access_chip(access: str) -> str:
    c = _ACCESS_TONE.get(access, P["text_dim"])
    return (f'<span style="display:inline-block;padding:1px 7px;font-size:9px;'
            f'font-family:JetBrains Mono,monospace;color:{c};border:1px solid {c};'
            f'border-radius:2px;letter-spacing:0.06em;text-transform:uppercase">'
            f'{_html.escape(access)}</span>')


def _table(cols, rows) -> str:
    ths = "".join(ck_data_cell(c, align=a, is_header=True) for c, a in cols)
    trs = "".join(f'<tr>{"".join(r)}</tr>' for r in rows)
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table></div>')


def _star_section(items) -> str:
    rows = []
    bar_max = max(s.weight_2026 for s in items) or 1.0
    for s in items:
        delta = s.weight_2026 - s.weight_2025
        d_c = P["negative"] if delta < 0 else (P["positive"] if delta > 0 else P["text_dim"])
        rows.append([
            ck_data_cell(_html.escape(s.category), mono=True, weight=700),
            ck_data_cell(f"{s.weight_2025:.0f}x", align="right", mono=True, tone="dim"),
            ck_data_cell(f"{s.weight_2026:.0f}x", align="right", mono=True, weight=700,
                         bar=s.weight_2026 / bar_max * 100),
            f'<td class="ck-cell ck-cell-r ck-cell-mono" style="color:{d_c};font-weight:700">{delta:+.0f}</td>',
            f'<td class="ck-cell" style="font-size:10px;color:{P["text_dim"]}">{_html.escape(s.note)}</td>',
        ])
    chart = "".join(
        ck_bar_row(s.category, f"{s.weight_2026:.0f}x", s.weight_2026 / 5.0 * 100.0,
                   tone=("negative" if s.weight_2026 < s.weight_2025 else "teal"))
        for s in items
    )
    cols = [("Measure category", "left"), ("2025 wt", "right"), ("2026 wt", "right"),
            ("Δ", "right"), ("Note", "left")]
    return chart + _table(cols, rows)


def _cpt_section(items) -> str:
    rows = []
    bar_max = max(c.pct_of_procedures for c in items) or 1.0
    for c in items:
        rows.append([
            ck_data_cell(c.code, mono=True, weight=700, tone="acc"),
            f'<td class="ck-cell" style="font-size:10px;color:{P["text_dim"]}">{_html.escape(c.description)}</td>',
            ck_data_cell(f"{c.pct_of_procedures:.2f}%", align="right", mono=True, weight=700,
                         bar=c.pct_of_procedures / bar_max * 100),
            ck_data_cell(f"${c.medicare_2026:,.2f}" if c.medicare_2026 else "—", align="right", mono=True),
            ck_data_cell(f"{c.work_rvu:.2f}" if c.work_rvu else "—", align="right", mono=True, tone="dim"),
        ])
    cols = [("CPT", "left"), ("Description", "left"), ("% of procedures", "right"),
            ("2026 Medicare", "right"), ("Work RVU", "right")]
    return _table(cols, rows)


def _drg_section(items) -> str:
    rows = []
    bar_max = max(d.pct_of_volume for d in items) or 1.0
    chart = "".join(
        ck_bar_row(f"DRG {d.drg} · {d.description[:34]}", f"{d.pct_of_volume:.2f}%",
                   d.pct_of_volume / bar_max * 100.0,
                   tone="navy" if d.rank == 1 else "teal")
        for d in items
    )
    for d in items:
        rows.append([
            ck_data_cell(str(d.rank), align="right", mono=True, tone="dim"),
            ck_data_cell(d.drg, mono=True, weight=700, tone="acc"),
            f'<td class="ck-cell" style="font-size:10px;color:{P["text"]}">{_html.escape(d.description)}</td>',
            ck_data_cell(f"{d.pct_of_volume:.2f}%", align="right", mono=True, weight=700,
                         bar=d.pct_of_volume / bar_max * 100),
        ])
    cols = [("#", "right"), ("DRG", "left"), ("Description", "left"), ("% of volume", "right")]
    return chart + _table(cols, rows)


def _partb_section(items) -> str:
    rows = []
    bar_max = max(d.spend_2022_b for d in items) or 1.0
    onc_tones = {"Cancer": "negative", "Cancer/arthritis": "negative", "Cancer/eye": "negative"}
    chart = "".join(
        ck_bar_row(f"{d.brand} · {d.therapy}", f"${d.spend_2022_b:.1f}B",
                   d.spend_2022_b / bar_max * 100.0,
                   tone=onc_tones.get(d.therapy, "teal"))
        for d in items
    )
    for d in items:
        rows.append([
            ck_data_cell(str(d.rank), align="right", mono=True, tone="dim"),
            ck_data_cell(_html.escape(d.brand), mono=True, weight=700),
            ck_data_cell(_html.escape(d.jcode), align="left", mono=True, tone="dim"),
            f'<td class="ck-cell" style="font-size:10px;color:{P["text_dim"]}">{_html.escape(d.therapy)}</td>',
            ck_data_cell(f"${d.spend_2022_b:.1f}B", align="right", mono=True, weight=700,
                         bar=d.spend_2022_b / bar_max * 100),
        ])
    cols = [("#", "right"), ("Drug", "left"), ("HCPCS/Generic", "left"),
            ("Therapy", "left"), ("2022 spend", "right")]
    return chart + _table(cols, rows)


def _comp_section(items) -> str:
    rows = []
    bar_max = max(c.median_comp for c in items) or 1.0
    for c in items:
        rows.append([
            ck_data_cell(_html.escape(c.specialty), mono=True, weight=700),
            ck_data_cell(f"${c.median_comp:,.0f}", align="right", mono=True, weight=700,
                         bar=c.median_comp / bar_max * 100),
            ck_data_cell(f"{c.median_wrvu:,.0f}", align="right", mono=True, tone="dim"),
            ck_data_cell(f"${c.dollar_per_wrvu:,.2f}", align="right", mono=True, tone="acc"),
            f'<td class="ck-cell ck-cell-c">{_access_chip(c.access)}</td>',
        ])
    cols = [("Specialty", "left"), ("Median total comp", "right"), ("Median wRVU", "right"),
            ("$/wRVU", "right"), ("Access", "center")]
    return _table(cols, rows)


def _shortage_section(items) -> str:
    span = max(abs(s.high) for s in items) or 1.0
    rows = []
    for s in items:
        tone = "negative" if s.low > 0 else "warning"
        label = (f"{s.low:,} – {s.high:,}" if s.low >= 0
                 else f"{s.low:,} (surplus) – {s.high:,} (shortage)")
        rows.append(ck_bar_row(s.group, label, abs(s.high) / span * 100.0, tone=tone))
    return "".join(rows)


def _margin_section(items) -> str:
    bar_max = max(m.operating_margin_pct for m in items) or 1.0
    rows = []
    for m in items:
        tone = "positive" if m.operating_margin_pct >= 4.0 else ("warning" if m.operating_margin_pct >= 1.0 else "negative")
        rows.append(ck_bar_row(f"{m.period} · {m.label}", f"{m.operating_margin_pct:.1f}%",
                               m.operating_margin_pct / bar_max * 100.0, tone=tone))
    return "".join(rows)


def _cost_section(items) -> str:
    rows = []
    for c in items:
        if c.unit == "%":
            val = f"{c.value:.1f}%"
        elif c.unit == "$":
            val = f"${c.value:,.0f}"
        elif c.unit == "$B":
            val = f"${c.value:,.1f}B"
        else:
            val = f"{c.value:,.1f}{c.unit}"
        rows.append([
            ck_data_cell(_html.escape(c.item), mono=True, weight=600),
            ck_data_cell(val, align="right", mono=True, weight=700),
            f'<td class="ck-cell" style="font-size:10px;color:{P["text_dim"]}">{_html.escape(c.note)}</td>',
        ])
    cols = [("Metric", "left"), ("Value", "right"), ("Basis", "left")]
    return _table(cols, rows)


def _prevalence_section(items) -> str:
    counts = [p.count_millions for p in items if p.count_millions]
    bar_max = max(counts) if counts else 1.0
    rows = []
    for p in items:
        cnt = f"{p.count_millions:.1f}M" if p.count_millions else "—"
        pct = f"{p.pct_of_pop:.1f}%" if p.pct_of_pop else "—"
        rows.append([
            ck_data_cell(_html.escape(p.condition), mono=True, weight=600),
            ck_data_cell(cnt, align="right", mono=True, weight=700,
                         bar=(p.count_millions / bar_max * 100) if p.count_millions else None),
            ck_data_cell(pct, align="right", mono=True, tone="acc"),
            f'<td class="ck-cell" style="font-size:10px;color:{P["text_dim"]}">{_html.escape(p.source)}</td>',
        ])
    cols = [("Condition / denominator", "left"), ("Count", "right"), ("% of pop", "right"), ("Source", "left")]
    return _table(cols, rows)


def _deaths_section(items) -> str:
    bar_max = max(d.deaths_2023 for d in items) or 1
    chart = "".join(
        ck_bar_row(f"{d.rank}. {d.cause}", f"{d.deaths_2023:,}" + ("~" if d.approx else ""),
                   d.deaths_2023 / bar_max * 100.0,
                   tone="navy" if d.rank <= 2 else "teal")
        for d in items
    )
    return chart


def _nhe_section(cats, payers) -> str:
    cat_max = max(c.dollars_b for c in cats) or 1.0
    cat_rows = []
    for c in cats:
        g = f"{c.growth_pct:+.1f}%" if c.growth_pct else "—"
        cat_rows.append([
            ck_data_cell(_html.escape(c.category), mono=True, weight=600),
            ck_data_cell(f"${c.dollars_b:,.1f}B", align="right", mono=True, weight=700,
                         bar=c.dollars_b / cat_max * 100),
            ck_data_cell(f"{c.share_pct:.0f}%", align="right", mono=True, tone="acc"),
            ck_data_cell(g, align="right", mono=True, tone="dim"),
        ])
    pay_max = max(p.dollars_b for p in payers) or 1.0
    pay_rows = []
    for p in payers:
        g = f"{p.growth_pct:+.1f}%" if p.growth_pct else "—"
        pay_rows.append([
            ck_data_cell(_html.escape(p.payer), mono=True, weight=600),
            ck_data_cell(f"${p.dollars_b:,.1f}B", align="right", mono=True, weight=700,
                         bar=p.dollars_b / pay_max * 100),
            ck_data_cell(f"{p.share_pct:.0f}%", align="right", mono=True, tone="acc"),
            ck_data_cell(g, align="right", mono=True, tone="dim"),
        ])
    c_cols = [("Category", "left"), ("Spend", "right"), ("Share", "right"), ("YoY", "right")]
    p_cols = [("Payer", "left"), ("Spend", "right"), ("Share", "right"), ("YoY", "right")]
    return (f'<div style="font-size:10px;color:{P["text_dim"]};margin-bottom:6px;'
            'text-transform:uppercase;letter-spacing:0.06em">By category</div>'
            + _table(c_cols, cat_rows)
            + f'<div style="font-size:10px;color:{P["text_dim"]};margin:12px 0 6px;'
            'text-transform:uppercase;letter-spacing:0.06em">By payer</div>'
            + _table(p_cols, pay_rows))


def _sources_section(items) -> str:
    rows = []
    for s in items:
        rows.append([
            f'<td class="ck-cell" style="font-size:10px;color:{P["text_dim"]}">{_html.escape(s.domain)}</td>',
            ck_data_cell(_html.escape(s.dataset), mono=True, weight=600),
            ck_data_cell(_html.escape(s.publisher), align="left", mono=True, tone="acc"),
            ck_data_cell(_html.escape(s.vintage), align="right", mono=True, tone="dim"),
            f'<td class="ck-cell ck-cell-c">{_access_chip(s.access)}</td>',
        ])
    cols = [("Domain", "left"), ("Dataset", "left"), ("Publisher", "left"),
            ("Vintage", "right"), ("Access", "center")]
    return _table(cols, rows)


def render_benchmark_reference(params: dict = None) -> str:
    from rcm_mc.data_public.benchmark_reference import compute_benchmark_reference
    r = compute_benchmark_reference()

    panel = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("National Health Spend", f"${r.nhe_total_t:.1f}T", f"{r.nhe_gdp_pct:.1f}% of GDP", "") +
        ck_kpi_block("Per Capita", f"${r.nhe_per_capita:,.0f}", "2023 NHE", "") +
        ck_kpi_block("Hospital Op Margin", f"{r.hospital_op_margin_pct:.1f}%", "median YTD Dec 2025", "") +
        ck_kpi_block("Top Inpatient DRG", r.top_drg, "sepsis", "") +
        ck_kpi_block("Top Physician Code", r.top_cpt, "E/M established", "") +
        ck_kpi_block("Top Part B Drug", r.top_partb_drug, "of $46.9B FFS", "") +
        ck_kpi_block("Data Domains", str(r.domain_count), "chart-ready", "") +
        ck_kpi_block("Named Sources", str(len(r.sources)), "CMS · MGMA · CDC · …", "")
    )

    value_anchor = ck_value_anchor(
        "NATIONAL HEALTH EXPENDITURE",
        f"${r.nhe_total_t:.1f}T",
        delta=f"{r.nhe_gdp_pct:.1f}% of GDP · ${r.nhe_per_capita:,.0f} per person",
        opportunity="Hospital care 31% · physician 20% · drugs 9%",
        target="2023 (CMS Office of the Actuary)",
        tone="teal",
    )

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = (f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};"
          "text-transform:uppercase;margin-bottom:10px")
    src = lambda s: (f'<div style="font-size:10px;color:{text_dim};margin-top:8px;'
                     f'font-family:JetBrains Mono,monospace">Source: {_html.escape(s)}</div>')

    page_title = ck_page_title(
        "Healthcare Operational & Benchmarking Reference",
        eyebrow="BENCHMARK REFERENCE · THE GRANULAR LAYER",
        meta=(f"Six chart-ready data domains · {len(r.sources)} named primary sources "
              f"(CMS · MGMA · AAMC · SEER/ACS · CDC/NCHS · KFF · Kaufman Hall · AHA · "
              f"MedPAC · NCQA) · figures tagged to measurement/vintage year"),
    )

    # Honest data-source disclosure (audited by
    # scripts/audit_page_data_sources.py): these are PUBLISHED national
    # reference figures with named primary sources — not the illustrative
    # seed corpus — so the page carries a source/purpose header rather
    # than the blanket ck_illustrative_note banner.
    source_header = ck_source_purpose(
        purpose=("Ground charting and deal benchmarking in published "
                 "national reference figures rather than modeled outputs "
                 "over the seed corpus."),
        universe="research", confidence="derived",
        source=("Published national benchmarks — CMS · MGMA · AAMC · "
                "SEER/ACS · CDC/NCHS · KFF · Kaufman Hall · AHA · MedPAC · "
                "NCQA — each row carries its named source, access flag and "
                "measurement/vintage year"),
        next_action="Read the caveats panel before charting any figure")

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {source_header}
  <div style="background:{panel};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;margin-bottom:16px;font-size:11px;color:{text_dim}">
    <b style="color:{text};font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:0.08em">REFERENCE DATA · NAMED PRIMARY SOURCES</b><br>
    These are published national benchmark figures with named sources — not modeled outputs over the seed corpus. Each row carries its source and an access flag
    ({_access_chip("free")} primary file · {_access_chip("proprietary")} subscription/member-only · {_access_chip("estimate")} rounded/derived). Star weights and HEDIS sets change annually, so figures are tagged to a measurement / vintage year.
  </div>
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}

  <div style="{cell}"><div style="{h3}">Domain 1 · Quality Measure Weights — MA-PD Star Ratings (2025 → 2026)</div>{_star_section(r.star_weights)}{src("CMS MA-PD Star Ratings Technical Notes. 2026 inflection: patient-experience/access weight 4→2.")}</div>

  <div style="{cell}"><div style="{h3}">Domain 2a · Top Physician CPT Codes (% of all procedures, 2024)</div>{_cpt_section(r.cpt_codes)}{src("Definitive Healthcare all-payer claims (2024); 2026 Medicare rates from the PFS. 99214/99213 ≈ 10% of all physician procedures.")}</div>

  <div style="{cell}"><div style="{h3}">Domain 2b · Top Inpatient MS-DRGs by Volume (CY2024)</div>{_drg_section(r.drgs)}{src("Definitive Healthcare / CMS SAF. Top 10 ≈ 30% of Medicare inpatient volume. DRG 470 (joint replacement) migrated to outpatient/ASC post-2018.")}</div>

  <div style="{cell}"><div style="{h3}">Domain 2c · Top Medicare Part B Drugs by Spend ($B, 2022 FFS)</div>{_partb_section(r.partb_drugs)}{src("MedPAC July 2024 Data Book (FFS only). Total Part B drug spend $46.9B; top 10 = $18.5B (39%). Red = oncology.")}</div>

  <div style="{cell}"><div style="{h3}">Domain 3a · Physician Compensation & Productivity by Specialty</div>{_comp_section(r.comp_benchmarks)}{src("MGMA-derived, 2024 data. DataDive percentile cells are PROPRIETARY (member-only) — aggregator-reported approximations shown, not official MGMA figures.")}</div>

  <div style="{cell}"><div style="{h3}">Domain 3b · Projected Physician Shortage by 2036 (low–high)</div>{_shortage_section(r.shortages)}{src("AAMC, Physician Supply & Demand Projections 2021–2036 (2024). Total shortage 13,500–86,000.")}</div>

  <div style="{cell}"><div style="{h3}">Domain 4a · Hospital Operating Margin Trend (median, incl. allocations)</div>{_margin_section(r.margin_trend)}{src("Kaufman Hall National Hospital Flash Report (~1,300 hospitals). 2024 FY 4.9% vs 2025 YTD 1.3% — 'historically slim'.")}</div>

  <div style="{cell}"><div style="{h3}">Domain 4b · Cost-Structure & 340B Reference</div>{_cost_section(r.cost_structure)}{src("Kaufman Hall Physician Flash Report (Q4 2025); AHA / HRSA 340B figures (2022–2024).")}</div>

  <div style="{cell}"><div style="{h3}">Domain 5a · Chronic-Condition & Demographic Denominators</div>{_prevalence_section(r.prevalence)}</div>

  <div style="{cell}"><div style="{h3}">Domain 5b · Leading Causes of Death (CDC/NCHS final 2023)</div>{_deaths_section(r.causes_of_death)}{src("CDC/NCHS final 2023. Heart disease + cancer = 41.9% of all deaths; top 10 = 70.9%. ~ = rounded.")}</div>

  <div style="{cell}"><div style="{h3}">Domain 6 · National Health Expenditure (2023)</div>{_nhe_section(r.nhe_categories, r.nhe_payers)}{src("CMS Office of the Actuary, NHE 2023. $4.9T total, +7.5%, 17.6% of GDP.")}</div>

  <div style="{cell}"><div style="{h3}">Source Register & Access Tiering</div>{_sources_section(r.sources)}</div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {P['warning']};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Caveats before charting:</strong>
    Proprietary compensation data (MGMA / SullivanCotter / Doximity) is subscription-only — only summary ranges are public; treat aggregator numbers as approximate.
    DRG/CPT rankings are Definitive Healthcare percentage shares, not raw counts — exact discharge counts require the free CMS MEDPAR PUF.
    MedPAC Part B figures are FFS-only (exclude Medicare Advantage) and round to $0.1B.
    Forward-looking items (2026/2027 Star changes, NHE projections, AAMC shortage ranges) are proposals/projections, not realized data.
    Do not conflate all-payer per-beneficiary spending with Medicare-program spending.
  </div>
</div>"""

    body = body + ck_page_actions()
    return chartis_shell(body, "Benchmark Reference", active_nav="/benchmark-reference",
        editorial_intro={
            "eyebrow": "BENCHMARK REFERENCE",
            "headline": "The granular benchmark layer beneath every vertical model.",
            "italic_word": "granular",
        })
