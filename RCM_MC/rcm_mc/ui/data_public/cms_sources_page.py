"""CMS Sources page — /cms-sources.

Shows known CMS Open Data endpoints, their description, dataset IDs,
update cadence, and record counts. Allows manual trigger of test fetches.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional


# CMS endpoint registry for display
_CMS_SOURCES = [
    {
        "key": "physician_payments",
        "name": "Medicare Physician & Other Practitioners",
        "dataset_id": "9552",
        "url": "https://data.cms.gov/data-api/v1/dataset/9552/data",
        "description": "Annual Medicare payments by NPI — services, beneficiary counts, allowed charges, reimbursement. Primary source for provider-level utilization benchmarking.",
        "update": "Annual (calendar year lag ~18 months)",
        "granularity": "NPI × HCPCS code × year",
        "key_cols": "Rndrng_NPI, Tot_Srvcs, Tot_Benes, Tot_Mdcr_Pymt_Amt",
        "use_case": "Market concentration (HHI/CR3), provider regime classification, opportunity ranking",
        "rows_est": "~10M per year",
        "status": "active",
    },
    {
        "key": "part_d_prescribers",
        "name": "Medicare Part D Prescribers",
        "dataset_id": "9548",
        "url": "https://data.cms.gov/data-api/v1/dataset/9548/data",
        "description": "Drug prescribing patterns by NPI — drug name, claim count, cost, beneficiary demographics. Critical for specialty pharmacy and pharma services diligence.",
        "update": "Annual",
        "granularity": "NPI × drug × year",
        "key_cols": "Prscrbr_NPI, Tot_Clms, Tot_Drug_Cst, Tot_Benes",
        "use_case": "Specialty pharmacy benchmarking, biosimilar penetration analysis",
        "rows_est": "~25M per year",
        "status": "active",
    },
    {
        "key": "inpatient_hospitals",
        "name": "Medicare Inpatient Hospitals",
        "dataset_id": "9545",
        "url": "https://data.cms.gov/data-api/v1/dataset/9545/data",
        "description": "DRG-level charges and payments for inpatient stays. Charge-to-payment ratio reveals pricing aggressiveness vs. Medicare reimbursement norms.",
        "update": "Annual",
        "granularity": "CCN × DRG × year",
        "key_cols": "Rndrng_Prvdr_CCN, DRG_Cd, Avg_Tot_Pymt_Amt, Avg_Mdcr_Pymt_Amt",
        "use_case": "Hospital efficiency benchmarking, charge capture analysis, case-mix validation",
        "rows_est": "~200K per year",
        "status": "active",
    },
    {
        "key": "outpatient_hospitals",
        "name": "Medicare Outpatient Hospitals",
        "dataset_id": "9546",
        "url": "https://data.cms.gov/data-api/v1/dataset/9546/data",
        "description": "APC-level outpatient charges and payments. Tracks ambulatory surgery center (ASC) migration opportunity and outpatient volume trends.",
        "update": "Annual",
        "granularity": "CCN × APC × year",
        "key_cols": "Rndrng_Prvdr_CCN, APC_Cd, Avg_Tot_Pymt_Amt",
        "use_case": "ASC conversion opportunity analysis, outpatient volume benchmarking",
        "rows_est": "~500K per year",
        "status": "active",
    },
    {
        "key": "ma_enrollment",
        "name": "Medicare Advantage Enrollment",
        "dataset_id": "9549",
        "url": "https://data.cms.gov/data-api/v1/dataset/9549/data",
        "description": "MA plan enrollment by contract, county, and plan type. Tracks MA penetration growth — critical for value-based care deal analysis.",
        "update": "Monthly",
        "granularity": "Contract × plan × county × month",
        "key_cols": "Contract_ID, Enroll_AMT, Plan_Type",
        "use_case": "MA penetration trend, provider-payer alignment scoring, VBC opportunity sizing",
        "rows_est": "~1M per year",
        "status": "active",
    },
    {
        "key": "open_payments",
        "name": "CMS Open Payments (Sunshine Act)",
        "dataset_id": "open-payments",
        "url": "https://openpaymentsdata.cms.gov/api/1/datastore/query",
        "description": "Drug/device manufacturer payments to physicians and teaching hospitals. Identifies conflict-of-interest exposure and pharma alignment.",
        "update": "Annual",
        "granularity": "NPI × manufacturer × payment type × year",
        "key_cols": "physician_npi, total_amount_of_payment_usdollars, name_of_manufacturer",
        "use_case": "Physician referral pattern analysis, conflict screening for acquisitions",
        "rows_est": "~12M per year",
        "status": "reference",
    },
    {
        "key": "cost_reports",
        "name": "Medicare Cost Reports (HCRIS)",
        "dataset_id": "HCRIS",
        "url": "https://www.cms.gov/research-statistics-data-and-systems/downloadable-public-use-files/cost-reports",
        "description": "Hospital cost report data — total costs, revenues, payer mix, FTE counts. Gold standard for hospital financial diligence. Annual bulk download.",
        "update": "Annual (18-month lag)",
        "granularity": "CCN × cost report period",
        "key_cols": "Prov_Num, Total_Costs, Total_Revenues, Medicaid_Days, Medicare_Days",
        "use_case": "Payer mix verification, cost structure benchmarking, margin validation",
        "rows_est": "~6K facilities per year",
        "status": "download",
    },
]


def _status_badge(status: str) -> str:
    cls = {
        "active": "ck-sig-green",
        "reference": "ck-sig-yellow",
        "download": "ck-sig-na",
    }.get(status, "ck-sig-na")
    label = {
        "active": "API LIVE",
        "reference": "REFERENCE",
        "download": "BULK DL",
    }.get(status, status.upper())
    return f'<span class="ck-sig {cls}">{label}</span>'


def _source_table(sources: List[Dict[str, Any]]) -> str:
    rows_html = []
    for i, src in enumerate(sources):
        stripe = ' style="background:#faf7f0"' if i % 2 == 0 else ""
        name_html = f'<strong style="font-family:var(--ck-mono);font-size:11.5px;">{_html.escape(src["name"])}</strong>'
        desc_html = f'<div style="color:var(--ck-text-dim);font-size:11px;margin-top:3px;white-space:normal;">{_html.escape(src["description"])}</div>'
        cols_html = f'<div style="font-family:var(--ck-mono);font-size:9.5px;color:var(--ck-text-faint);margin-top:4px;">{_html.escape(src["key_cols"])}</div>'

        rows_html.append(f"""
<tr{stripe}>
  <td style="padding:10px 10px;vertical-align:top;width:300px;">{name_html}{desc_html}{cols_html}</td>
  <td class="mono dim" style="vertical-align:top;padding:10px 8px;width:80px;">{_html.escape(src['dataset_id'])}</td>
  <td style="vertical-align:top;padding:10px 8px;width:90px;">{_status_badge(src['status'])}</td>
  <td class="dim" style="vertical-align:top;padding:10px 8px;font-size:10.5px;white-space:normal;width:140px;">{_html.escape(src['update'])}</td>
  <td class="mono dim" style="vertical-align:top;padding:10px 8px;font-size:10px;width:80px;">{_html.escape(src['rows_est'])}</td>
  <td style="vertical-align:top;padding:10px 8px;font-size:10.5px;color:var(--ck-text-dim);white-space:normal;">{_html.escape(src['use_case'])}</td>
</tr>""")

    return f"""
<div class="ck-panel">
  <div class="ck-panel-title">CMS Open Data Endpoint Registry</div>
  <div class="ck-table-wrap">
    <table class="ck-table" style="table-layout:fixed;">
      <colgroup>
        <col style="width:300px"><col style="width:80px"><col style="width:90px">
        <col style="width:140px"><col style="width:80px"><col>
      </colgroup>
      <thead>
        <tr>
          <th>Dataset / Description</th>
          <th>ID</th>
          <th>Status</th>
          <th>Cadence</th>
          <th>Volume</th>
          <th>Diligence Use Case</th>
        </tr>
      </thead>
      <tbody>{''.join(rows_html)}</tbody>
    </table>
  </div>
</div>"""


def _api_client_docs() -> str:
    return """
<div class="ck-panel">
  <div class="ck-panel-title">CMS API Client — Quick Reference</div>
  <div style="padding:14px 16px;">
    <div class="ck-section-label" style="margin-bottom:8px;">Python Usage</div>
    <pre style="background:#f5f1ea;border:1px solid #d6cfc3;border-radius:3px;padding:12px 14px;
                font-family:var(--ck-mono);font-size:11px;color:#1a2332;overflow-x:auto;
                white-space:pre;line-height:1.6;">
<span style="color:#465366"># rcm_mc/data_public/cms_api_client.py</span>
from rcm_mc.data_public.cms_api_client import fetch_pages, fetch_provider_utilization

<span style="color:#465366"># Low-level: fetch raw paginated JSON</span>
rows = fetch_pages(
    "https://data.cms.gov/data-api/v1/dataset/9552/data",
    limit=5000,
    max_pages=3,
    retry_count=3,
)

<span style="color:#465366"># High-level: physician utilization with normalization</span>
providers = fetch_provider_utilization(
    state="TX",
    specialty="Cardiology",
    year=2022,
    max_pages=5,
)
<span style="color:#465366"># → List[Dict] with: npi, provider_name, state, specialty,
#   total_services, total_beneficiaries, total_payment</span>

<span style="color:#465366"># Winsorize heavy-tailed payment columns</span>
from rcm_mc.data_public.cms_api_client import winsorize_column
clean = winsorize_column([col for col in payments], upper_quantile=0.95)
    </pre>
    <div style="margin-top:12px;">
      <div class="ck-section-label" style="margin-bottom:6px;">Key Functions</div>
      <table class="ck-table" style="width:auto;min-width:600px;">
        <thead><tr><th style="width:220px">Function</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td class="mono">fetch_pages(endpoint, ...)</td><td class="dim">Raw paginated fetch with retry. Returns List[Dict].</td></tr>
          <tr style="background:#faf7f0"><td class="mono">fetch_provider_utilization(state, specialty, year, ...)</td><td class="dim">Physician utilization, filtered and normalized.</td></tr>
          <tr><td class="mono">fetch_geographic_variation(state, ...)</td><td class="dim">Geographic variation dataset for regional benchmarking.</td></tr>
          <tr style="background:#faf7f0"><td class="mono">normalize_row(row)</td><td class="dim">Map CMS column names → internal canonical names.</td></tr>
          <tr><td class="mono">winsorize_column(values, upper_quantile)</td><td class="dim">Clip heavy tails for comparability analysis.</td></tr>
          <tr style="background:#faf7f0"><td class="mono">safe_float(value, default)</td><td class="dim">Null-safe numeric coercion from CMS string fields.</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>"""


def _integration_panel() -> str:
    return """
<div class="ck-panel">
  <div class="ck-panel-title">Integration with Corpus Analytics</div>
  <div style="padding:14px 16px;color:var(--ck-text-dim);font-size:11.5px;line-height:1.7;white-space:normal;">
    <p>CMS data feeds three analytical layers in the corpus:</p>
    <div style="margin-top:10px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:1px;background:var(--ck-border);">
      <div style="background:var(--ck-panel-alt);padding:10px 12px;">
        <div style="font-family:var(--ck-mono);font-size:9px;letter-spacing:0.12em;text-transform:uppercase;color:var(--ck-text-faint);margin-bottom:6px;">Market Structure</div>
        <div style="font-size:11px;color:var(--ck-text);">HHI / CR3 / CR5 concentration by state-specialty. Feeds white-space scoring and M&amp;A opportunity ranking.</div>
        <div style="margin-top:6px;font-family:var(--ck-mono);font-size:9.5px;color:var(--ck-accent);">→ market_concentration.py</div>
      </div>
      <div style="background:var(--ck-panel-alt);padding:10px 12px;">
        <div style="font-family:var(--ck-mono);font-size:9px;letter-spacing:0.12em;text-transform:uppercase;color:var(--ck-text-faint);margin-bottom:6px;">Provider Regime</div>
        <div style="font-size:11px;color:var(--ck-text);">Classify providers as durable_growth / steady / stagnant / declining using multi-year payment trends.</div>
        <div style="margin-top:6px;font-family:var(--ck-mono);font-size:9.5px;color:var(--ck-accent);">→ regime_classifier.py</div>
      </div>
      <div style="background:var(--ck-panel-alt);padding:10px 12px;">
        <div style="font-family:var(--ck-mono);font-size:9px;letter-spacing:0.12em;text-transform:uppercase;color:var(--ck-text-faint);margin-bottom:6px;">Consensus Ranking</div>
        <div style="font-size:11px;color:var(--ck-text);">Blended opportunity rank across volume, payment, regime, and investability lenses for target screening.</div>
        <div style="margin-top:6px;font-family:var(--ck-mono);font-size:9.5px;color:var(--ck-accent);">→ cms_provider_ranking.py</div>
      </div>
    </div>
  </div>
</div>"""


def render_cms_sources() -> str:
    from rcm_mc.ui._chartis_kit import chartis_shell, ck_kpi_block, ck_section_header

    active_count = sum(1 for s in _CMS_SOURCES if s["status"] == "active")
    kpis = (
        f'<div class="ck-kpi-grid">'
        + ck_kpi_block("CMS Sources", f'<span class="mn">{len(_CMS_SOURCES)}</span>', "in registry")
        + ck_kpi_block("Live API", f'<span class="mn pos">{active_count}</span>', "real-time endpoints")
        + ck_kpi_block("Estimated Volume", '<span class="mn">~50M</span>', "rows per year combined")
        + ck_kpi_block("Update Lag", '<span class="mn warn">18 mo</span>', "typical CMS release delay")
        + '</div>'
    )

    body = (
        kpis
        + ck_section_header("DATA SOURCES", "CMS Open Data endpoints powering corpus analytics")
        + _source_table(_CMS_SOURCES)
        + ck_section_header("API CLIENT", "rcm_mc/data_public/cms_api_client.py")
        + _api_client_docs()
        + ck_section_header("ANALYTICS INTEGRATION", "how CMS data feeds corpus modules")
        + _integration_panel()
    )

    return chartis_shell(
        body,
        title="CMS Data Sources",
        active_nav="/cms-sources",
        subtitle=f"{len(_CMS_SOURCES)} datasets registered · {active_count} live API endpoints · stdlib-only client",
    )
