"""PE Desk Data Explorer — browse and explore all public data sources.

Connects cms_care_compare, cms_utilization, system_network, benchmark_evolution,
irs990, and sec_edgar to a unified browsable interface.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

import pandas as pd

from ._chartis_kit import (
    chartis_shell, ck_fmt_num, ck_kpi_block,
    ck_next_section, ck_page_title, ck_provenance_tooltip,
)
from .brand import PALETTE

_EXPLAINER_CSS = """<style>
.ck-de-explainer{font-family:var(--sc-serif,'Georgia',serif);
  font-size:15px;line-height:1.55;color:var(--sc-text-dim,#4a4a4a);
  margin:0 0 var(--sc-s-6,18px) 0;max-width:72ch;}
.ck-de-explainer em{color:var(--sc-teal-ink,#155752);font-style:italic;}
</style>"""


def render_data_explorer(
    hcris_count: int = 0,
    sources_status: Optional[Dict[str, Any]] = None,
) -> str:
    """Render the data sources explorer page."""
    sources_status = sources_status or {}

    # Source cards with actual status
    source_cards = ""
    sources = [
        {
            "name": "HCRIS Cost Reports",
            "provider": "CMS (Centers for Medicare & Medicaid Services)",
            "records": f"{hcris_count:,}" if hcris_count else "Not loaded",
            "description": "Annual financial data for every Medicare-certified hospital: "
                           "revenue, expenses, bed counts, patient days, payer mix, and geographic data.",
            "fields": "~50 fields per hospital",
            "update": "Annual (12-18 month lag)",
            "browse_url": "/market-data/map",
            "browse_label": "Browse Heatmap",
            "status": "loaded" if hcris_count > 0 else "not_loaded",
        },
        {
            "name": "CMS Care Compare",
            "provider": "CMS Hospital Compare",
            "records": sources_status.get("care_compare_count", "Available"),
            "description": "Hospital quality ratings: overall star rating (1-5), "
                           "readmission rates, mortality rates, patient experience (HCAHPS), "
                           "value-based purchasing scores, and hospital-acquired condition scores.",
            "fields": "Star rating, readmission, mortality, HCAHPS, VBP, HAC",
            "update": "Quarterly",
            "browse_url": "/screen?preset=large_cap",
            "browse_label": "Screen Hospitals",
            "status": "available",
        },
        {
            "name": "Medicare Utilization",
            "provider": "CMS Inpatient Hospital Utilization",
            "records": sources_status.get("utilization_count", "Available"),
            "description": "Medicare inpatient utilization by DRG: discharges, covered days, "
                           "charges, and payments. Identifies which procedures generate the most "
                           "volume and revenue at each hospital.",
            "fields": "DRG-level volume, charges, payments",
            "update": "Annual",
            "browse_url": "/market-data/map",
            "browse_label": "Market Intelligence",
            "status": "available",
        },
        {
            "name": "IRS Form 990",
            "provider": "Internal Revenue Service",
            "records": sources_status.get("irs990_count", "~58% of hospitals"),
            "description": "Tax filings for non-profit hospitals. Cross-checks HCRIS financial "
                           "data against independently-filed tax returns. Includes total revenue, "
                           "total assets, executive compensation, and community benefit spending.",
            "fields": "Revenue, assets, compensation, community benefit",
            "update": "Annual (1-2 year lag)",
            "browse_url": "/methodology",
            "browse_label": "Methodology",
            "status": "available",
        },
        {
            "name": "FRED Economic Data",
            "provider": "Federal Reserve Bank of St. Louis",
            "records": "Live API",
            "description": "Treasury yields, CPI, and healthcare spending macro indicators. "
                           "Used for WACC calculations, market pulse indicators, and DCF models. "
                           "Falls back to static benchmarks when API is unavailable.",
            "fields": "10Y Treasury (DGS10), Healthcare CPI",
            "update": "Daily",
            "browse_url": "/home",
            "browse_label": "Market Pulse",
            "status": "live",
        },
        {
            "name": "SEC EDGAR",
            "provider": "Securities and Exchange Commission",
            "records": "Public filings",
            "description": "10-K and 10-Q filings from publicly-traded hospital systems "
                           "(HCA, Tenet, UHS, CYH, Lifepoint). Provides transaction multiples "
                           "and peer comparison data for valuation context.",
            "fields": "Financial statements, MD&A, segment data",
            "update": "Quarterly",
            "browse_url": "/news",
            "browse_label": "News & Research",
            "status": "available",
        },
    ]

    for s in sources:
        status_cls = {
            "loaded": "cad-badge-green", "live": "cad-badge-green",
            "available": "cad-badge-blue", "not_loaded": "cad-badge-muted",
        }.get(s["status"], "cad-badge-muted")
        status_label = {
            "loaded": "Loaded", "live": "Live",
            "available": "Available", "not_loaded": "Not Loaded",
        }.get(s["status"], "Unknown")

        source_cards += (
            f'<div class="cad-card">'
            f'<div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:8px;">'
            f'<div>'
            f'<h2 style="margin-bottom:2px;">{html.escape(s["name"])}</h2>'
            f'<div style="font-size:11px;color:{PALETTE["text_muted"]};">{html.escape(s["provider"])}</div>'
            f'</div>'
            f'<div style="display:flex;gap:6px;align-items:center;">'
            f'<span class="cad-badge {status_cls}">{status_label}</span>'
            f'<span class="cad-mono" style="font-size:11px;color:{PALETTE["text_secondary"]};">'
            f'{s["records"]}</span>'
            f'</div></div>'
            f'<p style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.6;margin-bottom:8px;">'
            f'{html.escape(s["description"])}</p>'
            f'<div style="display:flex;gap:16px;font-size:11px;color:{PALETTE["text_muted"]};margin-bottom:8px;">'
            f'<span><strong>Fields:</strong> {html.escape(s["fields"])}</span>'
            f'<span><strong>Update:</strong> {html.escape(s["update"])}</span>'
            f'</div>'
            f'<a href="{s["browse_url"]}" class="cad-btn" style="text-decoration:none;font-size:12px;">'
            f'{html.escape(s["browse_label"])} &rarr;</a>'
            f'</div>'
        )

    # Data pipeline status
    pipeline = (
        f'<div class="cad-card">'
        f'<h2>Data Pipeline</h2>'
        f'<p style="font-size:12.5px;color:{PALETTE["text_secondary"]};margin-bottom:12px;">'
        f'PE Desk ingests public data from CMS, IRS, FRED, and SEC. '
        f'Data flows through validation, scrubbing, and normalization before being available '
        f'for analysis. Every number in the platform traces back to one of these sources.</p>'
        f'<div style="display:flex;gap:12px;flex-wrap:wrap;">'
        f'<a href="/methodology" class="cad-btn" style="text-decoration:none;">Methodology</a>'
        f'<a href="/portfolio/regression" class="cad-btn" style="text-decoration:none;">Regression</a>'
        f'<a href="/market-data/map" class="cad-btn" style="text-decoration:none;">Market Heatmap</a>'
        f'<a href="/screen" class="cad-btn" style="text-decoration:none;">Hospital Screener</a>'
        f'</div></div>'
    )

    # Analytical modules status
    modules_status = []
    module_checks = [
        # Use CCN 010001 (Southeast Health) as sample for deal-specific pages
        ("PE Math (IRR, MOIC, Covenants)", "rcm_mc.pe.pe_math", "/models/returns/010001"),
        ("EBITDA Bridge (7 Levers)", "rcm_mc.pe.rcm_ebitda_bridge", "/models/bridge/010001"),
        ("Returns Waterfall", "rcm_mc.pe.waterfall", "/models/waterfall/010001"),
        ("Debt Trajectory", "rcm_mc.pe.debt_model", "/models/debt/010001"),
        ("Ramp Curves (S-curve)", "rcm_mc.pe.ramp_curves", "/models/bridge/010001"),
        ("Lever Dependencies", "rcm_mc.pe.lever_dependency", "/models/bridge/010001"),
        ("PE Attribution", "rcm_mc.pe.attribution", "/portfolio"),
        ("Predicted vs Actual", "rcm_mc.pe.predicted_vs_actual", "/models/predicted/010001"),
        ("Value Creation Plan", "rcm_mc.pe.value_plan", "/models/playbook/010001"),
        ("DCF Model", "rcm_mc.finance.dcf_model", "/models/dcf/010001"),
        ("LBO Model", "rcm_mc.finance.lbo_model", "/models/lbo/010001"),
        ("3-Statement Model", "rcm_mc.finance.three_statement", "/models/financials/010001"),
        ("Market Analysis (Moat)", "rcm_mc.finance.market_analysis", "/models/market/010001"),
        ("Denial Drivers", "rcm_mc.finance.denial_drivers", "/models/denial/010001"),
        ("OLS Regression", "rcm_mc.finance.regression", "/portfolio/regression"),
        ("Monte Carlo Simulator", "rcm_mc.core.simulator", "/analysis"),
        ("Conformal Prediction", "rcm_mc.ml.conformal", "/analysis"),
        ("Ridge Predictor", "rcm_mc.ml.ridge_predictor", "/analysis"),
        ("Comparable Finder", "rcm_mc.ml.comparable_finder", "/models/comparables/010001"),
        ("Anomaly Detector", "rcm_mc.ml.anomaly_detector", "/models/anomalies/010001"),
        ("Temporal Forecaster", "rcm_mc.ml.temporal_forecaster", "/models/trends/010001"),
        ("Portfolio Learning", "rcm_mc.ml.portfolio_learning", "/portfolio"),
        ("Feature Engineering", "rcm_mc.ml.feature_engineering", "/portfolio/regression"),
        ("Causal Inference", "rcm_mc.analytics.causal_inference", "/models/causal/010001"),
        ("Counterfactual Modeling", "rcm_mc.analytics.counterfactual", "/models/counterfactual/010001"),
        ("Service Line Analysis", "rcm_mc.analytics.service_lines", "/models/service-lines/010001"),
        ("Deal Screener", "rcm_mc.analysis.deal_screener", "/screen?preset=turnaround"),
        ("Deal Sourcer", "rcm_mc.analysis.deal_sourcer", "/source"),
        ("Diligence Questions", "rcm_mc.analysis.diligence_questions", "/models/questions/010001"),
        ("Playbook Builder", "rcm_mc.analysis.playbook", "/models/playbook/010001"),
        ("Challenge Solver", "rcm_mc.analysis.challenge", "/models/challenge/010001"),
        ("Pressure Test", "rcm_mc.analysis.pressure_test", "/pressure"),
        ("Deal Query Engine", "rcm_mc.analysis.deal_query", "/query"),
        ("Hospital Screener", "rcm_mc.intelligence.screener_engine", "/screen"),
        ("Market Pulse", "rcm_mc.intelligence.market_pulse", "/home"),
        ("Insights Generator", "rcm_mc.intelligence.insights_generator", "/home"),
        ("PE Desk Score", "rcm_mc.intelligence.caduceus_score", "/hospital/010001"),
        ("Economic Ontology", "rcm_mc.domain.econ_ontology", "/methodology"),
        ("CMS Care Compare", "rcm_mc.data.cms_care_compare", "/hospital/010001"),
        ("CMS Utilization", "rcm_mc.data.cms_utilization", "/hospital/010001"),
        ("IRS Form 990", "rcm_mc.data.irs990", "/models/irs990/010001"),
        ("SEC EDGAR", "rcm_mc.data.sec_edgar", "/news?cat=earnings"),
        ("EDI 837/835 Parser", "rcm_mc.data.edi_parser", "/import"),
        ("Claim Analytics", "rcm_mc.data.claim_analytics", "/models/denial/010001"),
        ("Benchmark Evolution", "rcm_mc.data.benchmark_evolution", "/benchmarks"),
        ("System Network", "rcm_mc.data.system_network", "/hospital/010001"),
        ("Price Transparency", "rcm_mc.infra.transparency", "/hospital/010001"),
        ("Scenario Shocks", "rcm_mc.scenarios.scenario_shocks", "/scenarios"),
        ("Vertical: ASC", "rcm_mc.verticals.asc.bridge", "/verticals"),
        ("Vertical: Behavioral Health", "rcm_mc.verticals.behavioral_health.bridge", "/verticals"),
        ("Vertical: MSO", "rcm_mc.verticals.mso.bridge", "/verticals"),
    ]

    mod_rows = ""
    loaded = 0
    for name, mod_path, page_url in module_checks:
        try:
            __import__(mod_path)
            loaded += 1
            status_cls = "cad-badge-green"
            status = "Loaded"
        except Exception:
            status_cls = "cad-badge-muted"
            status = "Not Available"
        mod_rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{html.escape(name)}</td>'
            f'<td style="font-size:11px;color:{PALETTE["text_muted"]};">'
            f'<code>{html.escape(mod_path)}</code></td>'
            f'<td><span class="cad-badge {status_cls}">{status}</span></td>'
            f'<td><a href="{page_url}" style="color:{PALETTE["text_link"]};font-size:12px;">'
            f'View &rarr;</a></td>'
            f'</tr>'
        )

    modules_section = (
        f'<div class="cad-card">'
        f'<h2>Analytical Modules ({loaded}/{len(module_checks)} loaded)</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:10px;">'
        f'Every Python module powering PE Desk analysis. Click "View" to see the output.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Module</th><th>Package</th><th>Status</th><th>Page</th>'
        f'</tr></thead><tbody>{mod_rows}</tbody></table></div>'
    )

    # Cycle 48 — KPI strip + provenance.
    n_sources = len(sources)
    modules_value = ck_provenance_tooltip(
        "Analytical modules loaded",
        f"{loaded} / {len(module_checks)}",
        explainer=(
            f"Production modules currently importable in this "
            f"server. {loaded} of {len(module_checks)} are live; "
            f"the rest are either pending dependencies or "
            f"intentionally disabled in this deployment."
        ),
    )
    hcris_value = ck_provenance_tooltip(
        "HCRIS hospital records",
        ck_fmt_num(hcris_count) if hcris_count else "Not loaded",
        explainer=(
            "Annual financial filings for every Medicare-certified "
            "hospital. Source: CMS HCRIS. Each row carries ~50 "
            "fields - revenue, expenses, beds, payer mix, geo. "
            "12-18 month publication lag from CMS."
        ),
        inject_css=False,
    )
    kpi_strip = (
        '<div class="ck-kpi-grid" style="grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px;">'
        + ck_kpi_block("Public Sources", ck_fmt_num(n_sources), "ingested")
        + ck_kpi_block("HCRIS Records", hcris_value, "hospitals on file")
        + ck_kpi_block("Modules Loaded", modules_value, "analytical")
        + '</div>'
    )

    next_up = ck_next_section(
        "Open the data catalog",
        "/data",
        eyebrow="Continue —",
        italic_word="catalog",
    )
    page_title = ck_page_title(
        "Data Explorer",
        eyebrow="DATA EXPLORER",
        meta=f"{loaded} modules loaded · {hcris_count:,} hospital profiles · {n_sources} sources",
    )
    de_explainer = (
        '<p class="ck-de-explainer">'
        "<em>Where the underlying data lives.</em> "
        "Inventory of every public-data source the platform ingests — "
        "HCRIS, IRS 990, sector reference data, FRED macro indicators. "
        "Use this to confirm a number's provenance before citing it."
        "</p>"
    )
    body = (
        page_title
        + de_explainer
        + kpi_strip
        + f'{source_cards}{modules_section}{pipeline}{next_up}'
    )

    return chartis_shell(
        body, "Data Explorer",
        extra_css=_EXPLAINER_CSS,
    )
