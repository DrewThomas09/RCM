"""CMS Public Data Browser — /cms-data-browser."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell
from rcm_mc.ui.chartis._helpers import render_page_explainer


def _datasets_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Dataset","left"),("Category","center"),("Update Freq","center"),("Last Refresh","center"),
            ("Records","right"),("Primary Use","left"),("Status","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = pos if d.ingestion_status == "current" else P["warning"]
        cells = [
            f'{ck_data_cell(f"""{_html.escape(d.dataset_name)}""", mono=True, weight=600)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(d.category)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(d.update_frequency)}</td>',
            f'{ck_data_cell(f"""{_html.escape(d.last_refresh)}""", align="center", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{d.record_count:,}""", align="right", mono=True)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.primary_use_case)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{s_c};font-weight:700">{_html.escape(d.ingestion_status.upper())}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _fee_schedule_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("CPT/HCPCS","left"),("Descriptor","left"),("Work RVU","right"),("Total RVU","right"),
            ("Facility Rate","right"),("Non-Facility Rate","right"),("Year","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(f.cpt_hcpcs)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{_html.escape(f.descriptor)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{f.work_rvu:,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{f.total_rvu:,.2f}""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""${f.facility_rate:,.2f}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""${f.non_facility_rate:,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{f.effective_year}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _drg_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("MS-DRG","left"),("Description","left"),("Weight","right"),("Geo LOS","right"),
            ("Arith LOS","right"),("Base Payment ($)","right"),("FY","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{d.drg_code:03d}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{_html.escape(d.drg_description)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{d.weight:,.4f}""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""{d.geometric_los:,.1f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{d.arithmetic_los:,.1f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${d.base_rate:,.0f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{d.fy_payment_year}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _hcris_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Provider Type","left"),("Reports","right"),("Filing Year","right"),("Median Occupancy","right"),
            ("Median Margin","right"),("Median CMI","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, h in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        m_c = pos if h.median_total_margin_pct >= 5.0 else (acc if h.median_total_margin_pct >= 2.0 else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(h.provider_type)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{h.reports_filed_latest:,}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{h.latest_filing_year}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{h.median_occupancy_pct:.1f}%""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{h.median_total_margin_pct:,.2f}%</td>',
            f'{ck_data_cell(f"""{h.median_case_mix_index:,.2f}""", align="right", mono=True, tone="acc")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _connections_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Source","left"),("Endpoint","left"),("Version","center"),("Auth","center"),
            ("Rate Limit","center"),("Cache TTL (hr)","right"),("Last Pull","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        a_c = P["warning"] if c.auth_required else pos
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.source)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;font-family:JetBrains Mono,monospace;color:{acc}">{_html.escape(c.api_endpoint)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.api_version)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{a_c};font-weight:700">{"YES" if c.auth_required else "NO"}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.rate_limit)}</td>',
            f'{ck_data_cell(f"""{c.cache_ttl_hours}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(c.last_successful_pull)}""", mono=True, tone="pos")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _quality_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Measure","left"),("Program","center"),("Type","center"),("Reporting Year","right"),
            ("National Median","right"),("Measure Steward","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, q in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        val = q.national_median
        disp = f"{val * 100:.1f}%" if 0 < val < 1.5 else f"{val:.2f}"
        cells = [
            f'{ck_data_cell(f"""{_html.escape(q.measure)}""", mono=True, weight=600)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(q.program)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(q.measure_type)}</td>',
            f'{ck_data_cell(f"""{q.reporting_year}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{disp}""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(q.measure_steward)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_cms_data_browser(params: dict = None) -> str:
    from rcm_mc.data_public.cms_data_browser import compute_cms_data_browser
    r = compute_cms_data_browser()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Datasets", str(r.total_datasets), "", "") +
        ck_kpi_block("Active", str(r.datasets_active), "", "") +
        ck_kpi_block("Total Records", f"{r.total_records_mm:,}M", "", "") +
        ck_kpi_block("Last Full Refresh", r.last_full_refresh[:10], "", "") +
        ck_kpi_block("API Connections", str(len(r.connections)), "", "") +
        ck_kpi_block("HCRIS Provider Types", str(len(r.hcris_samples)), "", "") +
        ck_kpi_block("Quality Measures", str(len(r.quality_measures)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    d_tbl = _datasets_table(r.datasets)
    f_tbl = _fee_schedule_table(r.fee_schedule_sample)
    drg_tbl = _drg_table(r.drg_sample)
    h_tbl = _hcris_table(r.hcris_samples)
    c_tbl = _connections_table(r.connections)
    q_tbl = _quality_table(r.quality_measures)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">CMS Public Data Browser</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Curated catalog of 20 CMS public datasets used in diligence · API connections · sample records · quality measures — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Dataset Catalog</div>{d_tbl}</div>
  <div style="{cell}"><div style="{h3}">Medicare PFS — Fee Schedule Sample (2025)</div>{f_tbl}</div>
  <div style="{cell}"><div style="{h3}">MS-DRG / IPPS Base Rate Sample (FY2025)</div>{drg_tbl}</div>
  <div style="{cell}"><div style="{h3}">HCRIS Cost Reports — Provider Type Aggregates</div>{h_tbl}</div>
  <div style="{cell}"><div style="{h3}">API Connection Status</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Quality Measure National Medians</div>{q_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">CMS Data Browser:</strong> {r.total_datasets} public datasets active — {r.total_records_mm}M+ records aggregate.
    PFS, OPPS, and MS-DRG rate data refreshed annually in Nov/Dec (calendar year) or Aug (fiscal year) cycles.
    HCRIS cost reports refreshed quarterly — median hospital operating margin 2.85% on 5,250 annual filings.
    Public API endpoints are rate-limited; Socrata auth token recommended for sustained pulls.
    Quality measure data links to /health-equity and /ma-contracts for MA Stars context, and /clinical-outcomes for provider-level benchmarking.
  </div>
</div>"""

    explainer = render_page_explainer(
        what=(
            "Inventory of CMS public datasets available to the "
            "platform: dataset name, update frequency, last refresh, "
            "record count, primary use case, and ingestion status "
            "across PFS, OPPS, MS-DRG, HCRIS, and quality-measure "
            "feeds."
        ),
        source="data_public/cms_data_browser.py; CMS.gov public-data APIs.",
        page_key="cms-data-browser",
    )
    return chartis_shell(explainer + body, "CMS Data Browser", active_nav="/cms-data-browser",
        editorial_intro={
            "eyebrow": "CMS DATA BROWSER",
            "headline": "What the cms data browser page reveals on this deal.",
            "italic_word": "reveals",
        })
