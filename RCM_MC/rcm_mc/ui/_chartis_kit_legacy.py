"""Chartis Kit — dark institutional shared shell for Corpus Intelligence pages.

Bloomberg Terminal / Palantir Foundry aesthetic.
Every number rendered in JetBrains Mono with tabular-nums.
No gradients. No glows. No rounded corners beyond 4px.

Usage:
    from rcm_mc.ui._chartis_kit import chartis_shell, ck_table, ck_fmt_num, ck_signal_badge

Public API:
    chartis_shell(body, title, *, active_nav, subtitle, extra_css, extra_js) -> str
    ck_table(rows, columns, *, caption, sortable) -> str
    ck_fmt_num(value, decimals, suffix, na) -> str
    ck_fmt_pct(value, decimals) -> str
    ck_fmt_moic(value) -> str
    ck_fmt_currency(value_mm, decimals) -> str
    ck_signal_badge(signal) -> str
    ck_grade_badge(grade) -> str
    ck_kpi_block(label, value, unit, delta) -> str
    ck_section_header(title, subtitle, count) -> str
"""
from __future__ import annotations

import html as _html
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Palette — matches analysis_workbench.py exactly
# ---------------------------------------------------------------------------

P = {
    "bg":          "#0a0e17",
    "panel":       "#111827",
    "panel_alt":   "#0f172a",
    "border":      "#1e293b",
    "border_dim":  "#0f1a2e",
    "text":        "#e2e8f0",
    "text_dim":    "#94a3b8",
    "text_faint":  "#64748b",
    "accent":      "#3b82f6",   # links ONLY
    "positive":    "#10b981",
    "negative":    "#ef4444",
    "warning":     "#f59e0b",
    "critical":    "#dc2626",
    "row_stripe":  "#0f172a",
}

_MONO = "'JetBrains Mono', 'SF Mono', 'Fira Code', 'Consolas', monospace"
_SANS = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"

# ---------------------------------------------------------------------------
# Nav items for Corpus Intelligence section
# ---------------------------------------------------------------------------

_CORPUS_NAV = [
    # RCM DILIGENCE — the analyst's front door. New top-level workspace
    # organised around the four-phase RCM Diligence Playbook. Placed
    # first because it's where the analyst lives during a 3-week
    # sprint; everything else is downstream context.
    {"label": "RCM DILIGENCE", "separator": True},
    {"label": "Ingestion",       "href": "/diligence/ingest",     "icon": "▤"},
    {"label": "Benchmarks",      "href": "/diligence/benchmarks", "icon": "▦"},
    {"label": "Root Cause",      "href": "/diligence/root-cause", "icon": "▥"},
    {"label": "Value Creation",  "href": "/diligence/value",      "icon": "◈"},
    {"label": "QoE Memo",        "href": "/diligence/qoe-memo",   "icon": "▣"},
    {"label": "Engagements",     "href": "/engagements",          "icon": "◉"},

    # PLATFORM — day-to-day operator entries. Alerts removed from nav
    # — portfolio-ops concept the analyst doesn't need. The alerts/
    # package and tables stay intact; a portfolio-ops user can re-
    # expose them via a non-default route if needed.
    {"label": "PLATFORM", "separator": True},
    {"label": "Home",        "href": "/home",    "icon": "◎"},
    {"label": "Dashboard",   "href": "/",        "icon": "◈"},
    {"label": "Import Deal", "href": "/import",  "icon": "▣"},
    {"label": "Audit",       "href": "/audit",   "icon": "▥"},

    # ANALYTICS — the scored / brain views. Partner-facing analysis.
    {"label": "ANALYTICS", "separator": True},
    {"label": "PE Intelligence Hub", "href": "/pe-intelligence",       "icon": "◈"},
    {"label": "Deal Screening",      "href": "/deal-screening",        "icon": "◉"},
    {"label": "Portfolio Analytics", "href": "/portfolio-analytics",   "icon": "◈"},
    {"label": "Sponsor Track Record","href": "/sponsor-track-record",  "icon": "▤"},
    {"label": "Payer Intelligence",  "href": "/payer-intelligence",    "icon": "▦"},
    {"label": "RCM Benchmarks",      "href": "/rcm-benchmarks",        "icon": "▤"},
    {"label": "Corpus Backtest",     "href": "/corpus-backtest",       "icon": "◉"},

    # REFERENCE — docs + catalogs. Look-up, not analysis.
    {"label": "REFERENCE", "separator": True},
    {"label": "Library",      "href": "/library",      "icon": "▤"},
    {"label": "Methodology",  "href": "/methodology",  "icon": "▥"},
    {"label": "API Docs",     "href": "/api/docs",     "icon": "▧"},
    {"label": "Module Index", "href": "/module-index", "icon": "▥"},

    # NOTE: everything previously under "CORPUS INTEL" and the back-
    # link row remains served by the router — only the sidebar listing
    # is consolidated. High-value routes are reachable via the Cmd+K
    # palette; the long tail is linked from the pages that stay in-nav.
]


# Legacy nav entries preserved as a detached list. Not rendered in
# the sidebar after the Phase 5 consolidation, but kept so any code
# that iterates legacy routes can still find them.
_CORPUS_NAV_LEGACY = [
    {"label": "Deals Library",  "href": "/library",          "icon": "▤"},
    {"label": "Comparables",    "href": "/comparables",      "icon": "▣"},
    {"label": "Risk Matrix",    "href": "/risk-matrix",      "icon": "▦"},
    {"label": "Underwriting",   "href": "/underwriting",    "icon": "▣"},
    {"label": "Market Rates",   "href": "/market-rates",    "icon": "▦"},
    {"label": "Backtest",       "href": "/backtest",         "icon": "▣"},
    {"label": "Portfolio Opt.", "href": "/portfolio-optimizer", "icon": "▦"},
    {"label": "Deal Quality",   "href": "/deal-quality",       "icon": "▣"},
    {"label": "Sector Intel",   "href": "/sector-intel",       "icon": "▦"},
    {"label": "Vintage Perf",   "href": "/vintage-perf",       "icon": "▣"},
    {"label": "Payer Intel",    "href": "/payer-intel",        "icon": "▦"},
    {"label": "Leverage Intel", "href": "/leverage-intel",     "icon": "▣"},
    {"label": "Size Intel",     "href": "/size-intel",         "icon": "▦"},
    {"label": "Corpus Dashboard","href": "/corpus-dashboard",   "icon": "◈"},
    {"label": "Deal Search",    "href": "/deal-search",        "icon": "▦"},
    {"label": "IC Memo Gen.",   "href": "/corpus-ic-memo",     "icon": "▣"},
    {"label": "Return Attrib.", "href": "/return-attribution", "icon": "▦"},
    {"label": "Deal Flow Map",  "href": "/deal-flow-heatmap",  "icon": "▣"},
    {"label": "Concentration",  "href": "/concentration-risk", "icon": "▦"},
    {"label": "Hold Analysis",  "href": "/hold-analysis",      "icon": "▣"},
    {"label": "IRR Dispersion", "href": "/irr-dispersion",    "icon": "▦"},
    {"label": "Payer Trends",   "href": "/payer-rate-trends", "icon": "▣"},
    {"label": "Entry Multiple", "href": "/entry-multiple",    "icon": "▦"},
    {"label": "Coverage Report","href": "/corpus-coverage",   "icon": "▣"},
    {"label": "Find Comps",     "href": "/find-comps",          "icon": "▦"},
    {"label": "Sector Momentum","href": "/sector-momentum",    "icon": "▣"},
    {"label": "GP Benchmarking","href": "/gp-benchmarking",   "icon": "▦"},
    {"label": "Red Flag Detect.","href": "/rcm-red-flags",   "icon": "▣"},
    {"label": "Hold Optimizer", "href": "/hold-optimizer",   "icon": "▦"},
    {"label": "Payer Stress",   "href": "/payer-stress",     "icon": "▣"},
    {"label": "Multiple Decomp","href": "/multiple-decomp",  "icon": "▦"},
    {"label": "Capital Eff.",  "href": "/capital-efficiency","icon": "▣"},
    {"label": "Risk Scores",   "href": "/deal-risk-scores",  "icon": "▦"},
    {"label": "Sector Corr.",  "href": "/sector-correlation","icon": "▣"},
    {"label": "Acq. Timing",  "href": "/acq-timing",        "icon": "▦"},
    {"label": "Portfolio Sim","href": "/portfolio-sim",     "icon": "▣"},
    {"label": "QoE Analyzer", "href": "/qoe-analyzer",     "icon": "▦"},
    {"label": "Covenant Mon.", "href": "/covenant-monitor", "icon": "▣"},
    {"label": "Provider Net.", "href": "/provider-network", "icon": "▦"},
    {"label": "Exit Multiple", "href": "/exit-multiple",   "icon": "▣"},
    {"label": "Diligence Chk.", "href": "/diligence-checklist","icon": "▦"},
    {"label": "Value Creation","href": "/value-creation",     "icon": "▣"},
    {"label": "UW Model",     "href": "/underwriting-model", "icon": "▦"},
    {"label": "Fee Tracker",  "href": "/mgmt-fee-tracker",  "icon": "▣"},
    {"label": "LP Dashboard", "href": "/lp-dashboard",      "icon": "▦"},
    {"label": "Bolt-on M&A",  "href": "/bolton-analyzer",   "icon": "▣"},
    {"label": "Working Cap.", "href": "/working-capital",   "icon": "▦"},
    {"label": "Debt Service", "href": "/debt-service",      "icon": "▣"},
    {"label": "Mgmt Comp",    "href": "/mgmt-comp",         "icon": "▦"},
    {"label": "Physician Prod.","href": "/physician-productivity","icon": "▣"},
    {"label": "Regulatory Risk","href": "/regulatory-risk",  "icon": "▦"},
    {"label": "Cost Structure","href": "/cost-structure",     "icon": "▣"},
    {"label": "Quality Scorecard","href": "/quality-scorecard","icon": "▦"},
    {"label": "ESG Dashboard",   "href": "/esg-dashboard",   "icon": "▣"},
    {"label": "Exit Readiness",  "href": "/exit-readiness",  "icon": "▦"},
    {"label": "Tax Structure",   "href": "/tax-structure",   "icon": "▣"},
    {"label": "Fund Attribution","href": "/fund-attribution","icon": "▦"},
    {"label": "Unit Economics", "href": "/unit-economics",  "icon": "▣"},
    {"label": "Deal Pipeline",  "href": "/deal-pipeline",   "icon": "▦"},
    {"label": "Payer Shift",    "href": "/payer-shift",     "icon": "▣"},
    {"label": "Key Person Risk","href": "/key-person",      "icon": "▦"},
    {"label": "Scenario MC",   "href": "/scenario-mc",      "icon": "▣"},
    {"label": "TSA Tracker",    "href": "/transition-services","icon": "▦"},
    {"label": "Revenue Leakage","href": "/revenue-leakage",   "icon": "▣"},
    {"label": "Reference Pricing","href": "/ref-pricing",     "icon": "▦"},
    {"label": "Geo Market",      "href": "/geo-market",       "icon": "▣"},
    {"label": "Capital Schedule","href": "/capital-schedule", "icon": "▦"},
    {"label": "Peer Valuation", "href": "/peer-valuation",   "icon": "▣"},
    {"label": "VCP / 100-Day",  "href": "/value-creation-plan","icon": "▦"},
    {"label": "Cap Structure",  "href": "/cap-structure",    "icon": "▣"},
    {"label": "Real Estate",    "href": "/real-estate",      "icon": "▦"},
    {"label": "Workforce Plan", "href": "/workforce-planning","icon": "▣"},
    {"label": "Tech Stack",     "href": "/tech-stack",       "icon": "▦"},
    {"label": "Growth Runway",  "href": "/growth-runway",    "icon": "▣"},
    {"label": "Dividend Recap", "href": "/dividend-recap",   "icon": "▦"},
    {"label": "Continuation Veh","href": "/continuation-vehicle","icon": "▣"},
    {"label": "Earnout",        "href": "/earnout",          "icon": "▦"},
    {"label": "Clinical Outcomes","href": "/clinical-outcomes","icon": "▣"},
    {"label": "Competitive Intel","href": "/competitive-intel","icon": "▦"},
    {"label": "Patient Exp / NPS","href": "/patient-experience","icon": "▣"},
    {"label": "Supply Chain",   "href": "/supply-chain",     "icon": "▦"},
    {"label": "Provider Retention","href": "/provider-retention","icon": "▣"},
    {"label": "Demand Forecast","href": "/demand-forecast",  "icon": "▦"},
    {"label": "Reinvestment",   "href": "/reinvestment",     "icon": "▣"},
    {"label": "Partner Economics","href": "/partner-economics","icon": "▦"},
    {"label": "Insurance Tracker","href": "/insurance-tracker","icon": "▣"},
    {"label": "ACO Economics",   "href": "/aco-economics",    "icon": "▦"},
    {"label": "Phys Comp Plan",  "href": "/phys-comp-plan",   "icon": "▦"},
    {"label": "Locum Workforce", "href": "/locum-tracker",    "icon": "▣"},
    {"label": "MA Contracts",    "href": "/ma-contracts",     "icon": "▦"},
    {"label": "340B Drug Pricing","href": "/drug-pricing-340b","icon": "▣"},
    {"label": "Sponsor Heatmap", "href": "/sponsor-heatmap",   "icon": "▤"},
    {"label": "Payer Concentr.", "href": "/payer-concentration","icon": "▦"},
    {"label": "Roll-Up Economics","href": "/rollup-economics",  "icon": "▣"},
    {"label": "CIN Analyzer",    "href": "/cin-analyzer",      "icon": "▦"},
    {"label": "Base Rates",      "href": "/base-rates",        "icon": "▤"},
    {"label": "REIT / SLB",      "href": "/reit-analyzer",     "icon": "▣"},
    {"label": "Capital Pacing",  "href": "/capital-pacing",    "icon": "▦"},
    {"label": "Covenant Headroom","href": "/covenant-headroom", "icon": "▣"},
    {"label": "Red-Flag Scanner", "href": "/redflag-scanner",   "icon": "▦"},
    {"label": "Value Backtester","href": "/backtester",         "icon": "▣"},
    {"label": "Direct Employer", "href": "/direct-employer",    "icon": "▦"},
    {"label": "Deal Origination","href": "/deal-origination",   "icon": "▣"},
    {"label": "Trial Site Econ", "href": "/trial-site-econ",    "icon": "▦"},
    {"label": "HCIT Platform",   "href": "/hcit-platform",      "icon": "▣"},
    {"label": "Biosimilars",     "href": "/biosimilars",        "icon": "▦"},
    {"label": "Telehealth Econ", "href": "/telehealth-econ",    "icon": "▣"},
    {"label": "De Novo Expansion","href": "/denovo-expansion",  "icon": "▦"},
    {"label": "Health Equity",   "href": "/health-equity",      "icon": "▣"},
    {"label": "Physician Labor", "href": "/physician-labor",    "icon": "▦"},
    {"label": "Platform Maturity","href": "/platform-maturity", "icon": "▣"},
    {"label": "Direct Lending",  "href": "/direct-lending",    "icon": "▦"},
    {"label": "PMI Playbook",    "href": "/pmi-playbook",       "icon": "▣"},
    {"label": "FWA Detection",   "href": "/fraud-detection",    "icon": "▦"},
    {"label": "Drug Shortage",   "href": "/drug-shortage",      "icon": "▣"},
    {"label": "Anti-Trust Scr.", "href": "/antitrust-screener", "icon": "▦"},
    {"label": "AI Operating Mdl","href": "/ai-operating-model", "icon": "▣"},
    {"label": "Cyber Risk",      "href": "/cyber-risk",          "icon": "▦"},
    {"label": "ZBB Tracker",     "href": "/zbb-tracker",         "icon": "▣"},
    {"label": "CMS Data Browser","href": "/cms-data-browser",    "icon": "▥"},
    {"label": "MSA Concentrat.", "href": "/msa-concentration",   "icon": "▦"},
    {"label": "IC Memo Generator","href": "/ic-memo-gen",         "icon": "▣"},
    {"label": "Module Index",    "href": "/module-index",         "icon": "▥"},
    {"label": "Deal Post-Mortem","href": "/deal-postmortem",      "icon": "▣"},
    {"label": "Secondaries",     "href": "/secondaries-tracker",   "icon": "▦"},
    {"label": "Tax Structure An.","href": "/tax-structure-analyzer","icon": "▣"},
    {"label": "Diligence Vendors","href": "/diligence-vendors",    "icon": "▦"},
    {"label": "Refi Optimizer",  "href": "/refi-optimizer",        "icon": "▣"},
    {"label": "LP Reporting",    "href": "/lp-reporting",          "icon": "▦"},
    {"label": "LBO Stress Test", "href": "/lbo-stress",            "icon": "▣"},
    {"label": "Board Governance","href": "/board-governance",      "icon": "▦"},
    {"label": "VDR Tracker",     "href": "/vdr-tracker",           "icon": "▦"},
    {"label": "Escrow & Earnout","href": "/escrow-earnout",        "icon": "▣"},
    {"label": "Debt Financing",  "href": "/debt-financing",        "icon": "▣"},
    {"label": "VCP Tracker",     "href": "/vcp-tracker",           "icon": "▣"},
    {"label": "Co-Invest Pipeline","href": "/coinvest-pipeline",   "icon": "▤"},
    {"label": "DPI Tracker",     "href": "/dpi-tracker",           "icon": "▣"},
    {"label": "NAV Loan Tracker","href": "/nav-loan-tracker",      "icon": "▣"},
    {"label": "Medical RE Tracker","href": "/medical-realestate",  "icon": "▦"},
    {"label": "CMS APM Tracker", "href": "/cms-apm",               "icon": "▥"},
    {"label": "MA / Stars Tracker","href": "/ma-star",             "icon": "▥"},
    {"label": "GPO / Supply",    "href": "/gpo-supply",            "icon": "▤"},
    {"label": "Capital Call",    "href": "/capital-call",          "icon": "▣"},
    {"label": "Litigation",      "href": "/litigation",            "icon": "▥"},
    {"label": "Fundraising",     "href": "/fundraising",           "icon": "▣"},
    {"label": "Operating Partners","href": "/operating-partners",  "icon": "▤"},
    {"label": "Compliance / SOC 2","href": "/compliance-attestation", "icon": "▥"},
    {"label": "ESG / Impact",    "href": "/esg-impact",            "icon": "▤"},
    {"label": "340B Program",    "href": "/tracker-340b",          "icon": "▥"},
    {"label": "Risk Adj / HCC",  "href": "/risk-adjustment",       "icon": "▥"},
    {"label": "Clinical AI",     "href": "/clinical-ai",           "icon": "▥"},
    {"label": "Specialty Benchmarks","href": "/specialty-benchmarks","icon": "▥"},
    {"label": "Peer Transactions","href": "/peer-transactions",    "icon": "▥"},
    {"label": "NSA / IDR",       "href": "/nsa-tracker",           "icon": "▥"},
    {"label": "Medicaid Unwinding","href": "/medicaid-unwinding",  "icon": "▥"},
    {"label": "Workforce Retention","href": "/workforce-retention","icon": "▤"},
    {"label": "Digital Front Door","href": "/digital-front-door", "icon": "▤"},
    {"label": "Hospital Anchor", "href": "/hospital-anchor",       "icon": "▥"},
    {"label": "Payer Contracts", "href": "/payer-contracts",       "icon": "▥"},
    {"label": "Capex Budget",    "href": "/capex-budget",          "icon": "▣"},
    {"label": "PMI Integration", "href": "/pmi-integration",       "icon": "▣"},
    {"label": "Tax Credits",     "href": "/tax-credits",           "icon": "▣"},
    {"label": "Deal Sourcing",   "href": "/deal-sourcing",         "icon": "▤"},
    {"label": "Treasury",        "href": "/treasury",              "icon": "▣"},
    {"label": "Sell-Side Process","href": "/sellside-process",     "icon": "▣"},
    {"label": "R&W Insurance",   "href": "/rw-insurance",          "icon": "▥"},
    {"label": "Vintage Cohorts", "href": "/vintage-cohorts",       "icon": "▣"},
    {"label": "Sponsor League", "href": "/sponsor-league",    "icon": "▤"},
    {"label": "Exit Timing",    "href": "/exit-timing",     "icon": "▦"},
    {"label": "CMS Sources",    "href": "/cms-sources",      "icon": "▥"},
    {"label": "Data Admin",     "href": "/admin/data-sources", "icon": "▧"},
]

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

_BASE_CSS = f"""
:root {{
  --ck-bg:          {P['bg']};
  --ck-panel:       {P['panel']};
  --ck-panel-alt:   {P['panel_alt']};
  --ck-border:      {P['border']};
  --ck-border-dim:  {P['border_dim']};
  --ck-text:        {P['text']};
  --ck-text-dim:    {P['text_dim']};
  --ck-text-faint:  {P['text_faint']};
  --ck-accent:      {P['accent']};
  --ck-pos:         {P['positive']};
  --ck-neg:         {P['negative']};
  --ck-warn:        {P['warning']};
  --ck-stripe:      {P['row_stripe']};
  --ck-mono:        {_MONO};
  --ck-sans:        {_SANS};
  --ck-nav-w:       200px;
  --ck-bar-h:       36px;
}}

*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

html, body {{
  height: 100%;
  background: var(--ck-bg);
  color: var(--ck-text);
  font-family: var(--ck-sans);
  font-size: 12px;
  line-height: 1.45;
  -webkit-font-smoothing: antialiased;
}}

a {{ color: var(--ck-accent); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}

/* Top bar */
.ck-bar {{
  position: fixed;
  top: 0; left: 0; right: 0;
  height: var(--ck-bar-h);
  background: var(--ck-panel);
  border-bottom: 1px solid var(--ck-border);
  display: flex;
  align-items: center;
  padding: 0 14px;
  z-index: 100;
  gap: 10px;
}}
.ck-bar-logo {{
  font-family: var(--ck-mono);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--ck-text);
  text-transform: uppercase;
  white-space: nowrap;
}}
.ck-bar-section {{
  font-family: var(--ck-mono);
  font-size: 9px;
  letter-spacing: 0.15em;
  color: var(--ck-text-faint);
  text-transform: uppercase;
  border-left: 1px solid var(--ck-border);
  padding-left: 10px;
  white-space: nowrap;
}}
.ck-bar-title {{
  font-family: var(--ck-mono);
  font-size: 10px;
  color: var(--ck-text-dim);
  margin-left: auto;
}}
.ck-bar-time {{
  font-family: var(--ck-mono);
  font-size: 10px;
  font-variant-numeric: tabular-nums;
  color: var(--ck-text-faint);
  white-space: nowrap;
}}

/* Layout */
.ck-layout {{
  display: flex;
  height: 100vh;
  padding-top: var(--ck-bar-h);
}}

/* Sidebar */
.ck-nav {{
  width: var(--ck-nav-w);
  flex-shrink: 0;
  background: var(--ck-panel);
  border-right: 1px solid var(--ck-border);
  overflow-y: auto;
  padding: 8px 0;
  position: sticky;
  top: var(--ck-bar-h);
  height: calc(100vh - var(--ck-bar-h));
}}
.ck-nav-sep {{
  font-family: var(--ck-mono);
  font-size: 8.5px;
  letter-spacing: 0.15em;
  color: var(--ck-text-faint);
  text-transform: uppercase;
  padding: 12px 12px 4px;
  border-top: 1px solid var(--ck-border-dim);
  margin-top: 6px;
}}
.ck-nav-sep:first-child {{ border-top: none; margin-top: 0; }}
.ck-nav-item {{
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 5px 12px;
  font-size: 11.5px;
  color: var(--ck-text-dim);
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.1s;
}}
.ck-nav-item:hover {{ background: var(--ck-panel-alt); color: var(--ck-text); }}
.ck-nav-item.active {{ background: var(--ck-panel-alt); color: var(--ck-text); border-left: 2px solid var(--ck-accent); padding-left: 10px; }}
.ck-nav-icon {{
  font-size: 10px;
  width: 14px;
  text-align: center;
  color: var(--ck-text-faint);
  flex-shrink: 0;
}}
.ck-nav-item.active .ck-nav-icon {{ color: var(--ck-accent); }}

/* Main content */
.ck-main {{
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  min-width: 0;
}}

/* Page header */
.ck-page-header {{
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--ck-border);
}}
.ck-page-title {{
  font-family: var(--ck-mono);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--ck-text);
  text-transform: uppercase;
}}
.ck-page-sub {{
  font-size: 11px;
  color: var(--ck-text-faint);
  margin-top: 2px;
}}

/* Section header */
.ck-section {{
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 14px 0 6px;
}}
.ck-section-label {{
  font-family: var(--ck-mono);
  font-size: 9px;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--ck-text-faint);
  border-left: 2px solid var(--ck-accent);
  padding-left: 6px;
}}
.ck-section-count {{
  font-family: var(--ck-mono);
  font-size: 9px;
  color: var(--ck-text-faint);
  background: var(--ck-panel);
  border: 1px solid var(--ck-border);
  padding: 1px 5px;
  border-radius: 2px;
}}

/* Panel */
.ck-panel {{
  background: var(--ck-panel);
  border: 1px solid var(--ck-border);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 14px;
}}
.ck-panel-title {{
  font-family: var(--ck-mono);
  font-size: 9.5px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ck-text-dim);
  padding: 7px 10px 6px;
  border-bottom: 1px solid var(--ck-border);
  background: var(--ck-panel-alt);
}}

/* Dense table */
.ck-table-wrap {{
  overflow-x: auto;
  border-radius: 3px;
}}
table.ck-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 11.5px;
  table-layout: fixed;
}}
table.ck-table thead {{
  position: sticky;
  top: 0;
  z-index: 10;
}}
table.ck-table th {{
  background: var(--ck-panel-alt);
  border-bottom: 1px solid var(--ck-border);
  padding: 6px 8px;
  font-family: var(--ck-mono);
  font-size: 9.5px;
  font-weight: 600;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--ck-text-dim);
  white-space: nowrap;
  text-align: left;
}}
table.ck-table th.num {{ text-align: right; }}
table.ck-table td {{
  padding: 5px 8px;
  border-bottom: 1px solid var(--ck-border-dim);
  color: var(--ck-text);
  vertical-align: middle;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
table.ck-table tr:nth-child(even) td {{ background: var(--ck-stripe); }}
table.ck-table td.num {{
  text-align: right;
  font-family: var(--ck-mono);
  font-variant-numeric: tabular-nums;
}}
table.ck-table td.mono {{
  font-family: var(--ck-mono);
  font-size: 10.5px;
}}
table.ck-table td.dim {{ color: var(--ck-text-dim); }}
table.ck-table td.faint {{ color: var(--ck-text-faint); font-size: 10.5px; }}
table.ck-table tr:hover td {{ background: #162032; }}

/* Sortable table headers */
table.ck-table.sortable th {{
  cursor: pointer;
  user-select: none;
}}
table.ck-table.sortable th:hover {{ color: var(--ck-text); background: #1a2744; }}
table.ck-table.sortable th[data-sorted]::after {{ content: " ▾"; color: var(--ck-accent); }}
table.ck-table.sortable th[data-sorted="asc"]::after {{ content: " ▴"; color: var(--ck-accent); }}

/* Signal badges */
.ck-sig {{
  display: inline-block;
  font-family: var(--ck-mono);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  padding: 2px 5px;
  border-radius: 2px;
  white-space: nowrap;
}}
.ck-sig-green  {{ background: rgba(16,185,129,0.15); color: {P['positive']}; border: 1px solid rgba(16,185,129,0.3); }}
.ck-sig-yellow {{ background: rgba(245,158,11,0.15); color: {P['warning']};  border: 1px solid rgba(245,158,11,0.3); }}
.ck-sig-red    {{ background: rgba(239,68,68,0.15);  color: {P['negative']}; border: 1px solid rgba(239,68,68,0.3); }}
.ck-sig-na     {{ background: rgba(100,116,139,0.15); color: var(--ck-text-faint); border: 1px solid var(--ck-border); }}

/* Grade badges */
.ck-grade {{ display: inline-block; font-family: var(--ck-mono); font-size: 10px; font-weight: 700;
  width: 22px; text-align: center; padding: 1px 0; border-radius: 2px; }}
.ck-grade-a {{ background: rgba(16,185,129,0.18); color: {P['positive']}; }}
.ck-grade-b {{ background: rgba(59,130,246,0.18); color: {P['accent']}; }}
.ck-grade-c {{ background: rgba(245,158,11,0.18); color: {P['warning']}; }}
.ck-grade-d {{ background: rgba(239,68,68,0.18);  color: {P['negative']}; }}

/* KPI block */
.ck-kpi-grid {{ display: flex; gap: 1px; background: var(--ck-border); border: 1px solid var(--ck-border); border-radius: 3px; overflow: hidden; margin-bottom: 14px; }}
.ck-kpi {{
  background: var(--ck-panel);
  padding: 10px 14px;
  flex: 1;
  min-width: 110px;
}}
.ck-kpi-label {{ font-family: var(--ck-mono); font-size: 8.5px; letter-spacing: 0.15em; text-transform: uppercase; color: var(--ck-text-faint); margin-bottom: 4px; }}
.ck-kpi-value {{ font-family: var(--ck-mono); font-size: 20px; font-variant-numeric: tabular-nums; font-weight: 600; color: var(--ck-text); line-height: 1; }}
.ck-kpi-unit  {{ font-family: var(--ck-mono); font-size: 10px; color: var(--ck-text-faint); margin-top: 2px; }}
.ck-kpi-delta {{ font-family: var(--ck-mono); font-size: 9.5px; font-variant-numeric: tabular-nums; margin-top: 3px; }}
.ck-delta-pos {{ color: var(--ck-pos); }}
.ck-delta-neg {{ color: var(--ck-neg); }}

/* Filter bar */
.ck-filters {{
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
  flex-wrap: wrap;
}}
.ck-filter-label {{ font-family: var(--ck-mono); font-size: 9.5px; color: var(--ck-text-faint); letter-spacing: 0.12em; text-transform: uppercase; }}
select.ck-sel, input.ck-input {{
  background: var(--ck-panel);
  border: 1px solid var(--ck-border);
  color: var(--ck-text);
  font-family: var(--ck-mono);
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 3px;
  outline: none;
}}
select.ck-sel:focus, input.ck-input:focus {{ border-color: var(--ck-accent); }}
input.ck-input {{ width: 200px; }}
button.ck-btn {{
  background: var(--ck-accent);
  color: #fff;
  border: none;
  font-family: var(--ck-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  padding: 5px 12px;
  border-radius: 3px;
  cursor: pointer;
}}
button.ck-btn:hover {{ background: #2563eb; }}
button.ck-btn-ghost {{
  background: transparent;
  color: var(--ck-text-dim);
  border: 1px solid var(--ck-border);
  font-family: var(--ck-mono);
  font-size: 10px;
  padding: 4px 10px;
  border-radius: 3px;
  cursor: pointer;
}}
button.ck-btn-ghost:hover {{ border-color: var(--ck-accent); color: var(--ck-text); }}

/* Scrollbar */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: var(--ck-bg); }}
::-webkit-scrollbar-thumb {{ background: var(--ck-border); border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--ck-text-faint); }}

/* Mono number spans */
.mn {{ font-family: var(--ck-mono); font-variant-numeric: tabular-nums; }}
.pos {{ color: var(--ck-pos); }}
.neg {{ color: var(--ck-neg); }}
.warn {{ color: var(--ck-warn); }}
.dim  {{ color: var(--ck-text-dim); }}
.faint {{ color: var(--ck-text-faint); }}
"""

# ---------------------------------------------------------------------------
# KEEP features ported from shell_v2 (see docs/UI_CONSISTENCY_AUDIT.md
# appendix). Four behaviours that chartis needs for feature parity:
#   1. CSRF token patcher      — security, non-optional
#   2. Alert-badge poller      — UX, hits /api/alerts/active-count
#   3. Cmd+K command palette   — power-user jump
#   4. Vim-style shortcuts     — power-user keyboard nav (?, /, g+<key>)
# ---------------------------------------------------------------------------

# Curated shortcut list for the Cmd+K palette. Mirrors the three nav
# groups (PLATFORM / ANALYTICS / REFERENCE) and adds the highest-value
# legacy routes that are no longer in the sidebar after the Phase 5
# consolidation. Hard-capped at 30 — the palette is a curated jump
# list, not a directory.
_PALETTE_ENTRIES = [
    # NAV — PLATFORM group
    ("NAV", "Home",                     "/home"),
    ("NAV", "Dashboard",                "/"),
    ("NAV", "Pipeline",                 "/pipeline"),
    ("NAV", "Portfolio",                "/portfolio"),
    ("NAV", "Alerts",                   "/alerts"),
    ("NAV", "Import Deal",              "/import"),
    ("NAV", "Audit",                    "/audit"),
    # ANL — ANALYTICS group + high-value legacy analytics
    ("ANL", "PE Intelligence",          "/pe-intelligence"),
    ("ANL", "Deal Screening",           "/deal-screening"),
    ("ANL", "Portfolio Analytics",      "/portfolio-analytics"),
    ("ANL", "Corpus Backtest",          "/corpus-backtest"),
    ("ANL", "Sponsor Track Record",     "/sponsor-track-record"),
    ("ANL", "Payer Intelligence",       "/payer-intelligence"),
    ("ANL", "RCM Benchmarks",           "/rcm-benchmarks"),
    ("ANL", "Hospital Screener",        "/screen"),
    ("ANL", "Market Data",              "/market-data/map"),
    ("ANL", "Deal Search",              "/deal-search"),
    ("ANL", "Corpus Dashboard",         "/corpus-dashboard"),
    ("ANL", "Quant Lab",                "/quant-lab"),
    ("ANL", "Base Rates",               "/base-rates"),
    ("ANL", "Sponsor Heatmap",          "/sponsor-heatmap"),
    ("ANL", "Vintage Cohorts",          "/vintage-cohorts"),
    ("ANL", "Find Comps",               "/find-comps"),
    ("ANL", "Exit Readiness",           "/exit-readiness"),
    # REF — REFERENCE group
    ("REF", "Library (Corpus)",         "/library"),
    ("REF", "Methodology",              "/methodology"),
    ("REF", "API Docs",                 "/api/docs"),
    ("REF", "Module Index",             "/module-index"),
    ("REF", "News",                     "/news"),
    ("REF", "Settings",                 "/settings"),
]


def _palette_html() -> str:
    """Cmd+K command palette — hidden modal rendered on every chartis page."""
    items = []
    for cat, label, href in _PALETTE_ENTRIES:
        items.append(
            f'<a class="ck-palette-item" data-label="{_html.escape(label.lower())}" '
            f'href="{href}">'
            f'<span class="ck-palette-item-label">{_html.escape(label)}</span>'
            f'<span class="ck-palette-item-cat">{cat}</span></a>'
        )
    return (
        '<div class="ck-palette-backdrop" id="ck-palette-bd" role="dialog" '
        'aria-label="Command palette" aria-hidden="true">'
        '<div class="ck-palette">'
        '<input type="text" class="ck-palette-input" id="ck-palette-input" '
        'placeholder="Type a command or page…" aria-label="Command palette">'
        f'<div class="ck-palette-results" id="ck-palette-results">{"".join(items)}</div>'
        '<div class="ck-palette-hint">'
        '<span><kbd>&uarr;&darr;</kbd> Navigate</span>'
        '<span><kbd>&crarr;</kbd> Open</span>'
        '<span><kbd>Esc</kbd> Close</span>'
        '</div>'
        '</div></div>'
    )


def _kb_help_html() -> str:
    """Vim-style shortcut help modal — toggled by `?` key."""
    rows = [
        ("?",     "Show / hide this help"),
        ("/",     "Focus search (if present)"),
        ("Cmd/Ctrl + K", "Open command palette"),
        ("g h",   "Home"),
        ("g a",   "Analysis landing"),
        ("g p",   "Portfolio"),
        ("g s",   "Hospital Screener"),
        ("g m",   "Market Data"),
        ("g n",   "News"),
        ("g r",   "Portfolio Regression"),
        ("g l",   "Library (corpus)"),
        ("g i",   "Import Deal"),
        ("g d",   "API Docs"),
        ("g b",   "PE Intelligence Brain"),
        ("g o",   "Portfolio Analytics"),
    ]
    items = "".join(
        f'<div class="ck-kbhelp-row">'
        f'<kbd class="ck-kbd">{_html.escape(k)}</kbd>'
        f'<span>{_html.escape(d)}</span>'
        f'</div>'
        for k, d in rows
    )
    return (
        '<div class="ck-kbhelp-backdrop" id="ck-kbhelp-bd" role="dialog" '
        'aria-label="Keyboard shortcuts" aria-hidden="true">'
        '<div class="ck-kbhelp">'
        '<div class="ck-kbhelp-title">Keyboard Shortcuts</div>'
        f'<div class="ck-kbhelp-list">{items}</div>'
        '<div class="ck-kbhelp-hint">Press <kbd class="ck-kbd">?</kbd> or '
        '<kbd class="ck-kbd">Esc</kbd> to close</div>'
        '</div></div>'
    )


def _alert_bell_html() -> str:
    """Topbar bell — returns empty string now that alerts are hidden
    from the analyst UI. The function is retained (rather than its
    call site deleted) so the surrounding shell layout doesn't need
    to be touched. A portfolio-ops variant can re-enable by flipping
    this to return the bell markup."""
    return ""


# CSS for the four ported features. Kept in a separate constant so it's
# easy to see what was added for the shell_v2 port.
_KEEP_FEATURES_CSS = f"""
/* ── Alert-bell in topbar (ported from shell_v2) ── */
.ck-bar-bell {{
  color: var(--ck-text-dim);
  text-decoration: none;
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: 8px;
}}
.ck-bar-bell:hover {{ color: {P['accent']}; }}
.ck-bar-bell-icon {{ font-size: 14px; line-height: 1; }}
.ck-bar-bell-count {{
  background: {P['negative']};
  color: #fff;
  font-family: var(--ck-mono);
  font-size: 9px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 8px;
  letter-spacing: 0.04em;
  min-width: 16px;
  text-align: center;
}}

/* ── Cmd+K command palette (ported from shell_v2) ── */
.ck-palette-backdrop {{
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: none;
  align-items: flex-start;
  justify-content: center;
  padding-top: 15vh;
  z-index: 1000;
}}
.ck-palette-backdrop.open {{ display: flex; }}
.ck-palette {{
  width: 100%; max-width: 560px;
  background: var(--ck-panel);
  border: 1px solid var(--ck-border);
  border-radius: 6px;
  box-shadow: 0 20px 40px rgba(0,0,0,0.5);
  overflow: hidden;
  display: flex; flex-direction: column;
  max-height: 60vh;
}}
.ck-palette-input {{
  width: 100%;
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--ck-border);
  color: var(--ck-text);
  font-family: var(--ck-mono);
  font-size: 13px;
  padding: 14px 18px;
  outline: none;
  letter-spacing: 0.02em;
}}
.ck-palette-input::placeholder {{ color: var(--ck-text-faint); }}
.ck-palette-results {{
  overflow-y: auto;
  flex: 1;
  padding: 4px 0;
}}
.ck-palette-item {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 18px;
  color: var(--ck-text-dim);
  text-decoration: none;
  font-size: 12px;
  gap: 10px;
}}
.ck-palette-item:hover,
.ck-palette-item.sel {{
  background: var(--ck-panel-alt);
  color: var(--ck-text);
}}
.ck-palette-item-label {{ font-weight: 500; }}
.ck-palette-item-cat {{
  font-family: var(--ck-mono);
  font-size: 9px;
  letter-spacing: 0.12em;
  color: var(--ck-text-faint);
  background: var(--ck-panel-alt);
  padding: 2px 6px;
  border: 1px solid var(--ck-border);
  border-radius: 2px;
}}
.ck-palette-item.sel .ck-palette-item-cat {{
  color: {P['accent']};
  border-color: {P['accent']};
}}
.ck-palette-hint {{
  border-top: 1px solid var(--ck-border);
  padding: 8px 18px;
  display: flex;
  gap: 14px;
  font-size: 10px;
  color: var(--ck-text-faint);
  font-family: var(--ck-mono);
  letter-spacing: 0.05em;
}}
.ck-palette-hint kbd {{
  font-family: var(--ck-mono);
  font-size: 10px;
  background: var(--ck-panel-alt);
  border: 1px solid var(--ck-border);
  padding: 1px 5px;
  border-radius: 2px;
  margin-right: 4px;
}}

/* ── Vim-style keyboard help modal (ported from shell_v2) ── */
.ck-kbhelp-backdrop {{
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: none;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}}
.ck-kbhelp-backdrop.open {{ display: flex; }}
.ck-kbhelp {{
  background: var(--ck-panel);
  border: 1px solid var(--ck-border);
  border-radius: 6px;
  box-shadow: 0 20px 40px rgba(0,0,0,0.5);
  padding: 20px 24px;
  min-width: 320px;
  max-width: 400px;
}}
.ck-kbhelp-title {{
  font-family: var(--ck-mono);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ck-text);
  border-bottom: 1px solid var(--ck-border);
  padding-bottom: 10px;
  margin-bottom: 10px;
}}
.ck-kbhelp-list {{
  display: flex;
  flex-direction: column;
  gap: 6px;
}}
.ck-kbhelp-row {{
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11.5px;
  color: var(--ck-text-dim);
}}
.ck-kbhelp-row kbd {{ flex-shrink: 0; }}
.ck-kbhelp-hint {{
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px solid var(--ck-border);
  font-size: 10px;
  color: var(--ck-text-faint);
  font-family: var(--ck-mono);
}}
.ck-kbd {{
  font-family: var(--ck-mono);
  font-size: 10.5px;
  background: var(--ck-panel-alt);
  border: 1px solid var(--ck-border);
  padding: 2px 7px;
  border-radius: 2px;
  color: var(--ck-text);
  letter-spacing: 0.04em;
  white-space: nowrap;
  min-width: 56px;
  display: inline-block;
  text-align: center;
}}
"""


# Compatibility CSS — maps the .cad-* class names used in pages that were
# originally written against shell_v2 onto chartis's CSS variables. Added
# so Wave 1/2/3 migrations can be a pure shell-import swap without having
# to rewrite every page's body HTML. Covers the 40 most-used .cad-*
# classes (~95% of references). See UI_CONSISTENCY_AUDIT.md appendix.
#
# This block is intentionally additive — it does not override any .ck-*
# rules. Pages that reference both .cad-* and .ck-* will render both.
# The block can be deleted when every page has been ported off .cad-*
# class names (out of scope for this migration wave).
_CAD_COMPAT_CSS = f"""
/* ── cad-compat: shell_v2 class aliases for migrated pages ── */

/* Layout */
.cad-main {{ flex: 1; overflow-y: auto; padding: 16px 20px; min-width: 0; }}

/* Text tones */
.cad-text   {{ color: var(--ck-text); }}
.cad-text2  {{ color: var(--ck-text-dim); }}
.cad-text3  {{ color: var(--ck-text-faint); }}
.cad-mono   {{ font-family: var(--ck-mono); }}
.cad-pos    {{ color: {P['positive']}; }}
.cad-neg    {{ color: {P['negative']}; }}
.cad-warn   {{ color: {P['warning']}; }}
.cad-amber  {{ color: {P['warning']}; }}
.cad-accent {{ color: {P['accent']}; }}
.cad-link   {{ color: {P['accent']}; text-decoration: none; }}
.cad-link:hover {{ text-decoration: underline; }}

/* Backgrounds */
.cad-bg2    {{ background: var(--ck-panel); }}
.cad-bg3    {{ background: var(--ck-panel-alt); }}
.cad-border    {{ border-color: var(--ck-border) !important; }}
.cad-border-lt {{ border-color: var(--ck-border-dim) !important; }}

/* Cards / panels — map to .ck-panel look */
.cad-card {{
  background: var(--ck-panel);
  border: 1px solid var(--ck-border);
  border-radius: 3px;
  padding: 12px 14px;
  margin-bottom: 14px;
  overflow: hidden;
}}
.cad-card h2 {{
  font-family: var(--ck-mono);
  font-size: 12px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--ck-text);
  margin-bottom: 10px;
}}

/* KPI grid */
.cad-kpi-grid {{
  display: flex;
  gap: 1px;
  background: var(--ck-border);
  border: 1px solid var(--ck-border);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 14px;
}}
.cad-kpi {{
  background: var(--ck-panel);
  padding: 10px 14px;
  flex: 1;
  min-width: 110px;
}}
.cad-kpi-value {{
  font-family: var(--ck-mono);
  font-size: 20px;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  color: var(--ck-text);
  line-height: 1;
}}
.cad-kpi-label {{
  font-family: var(--ck-mono);
  font-size: 8.5px;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--ck-text-faint);
  margin-top: 4px;
}}
.cad-kpi-delta {{
  font-family: var(--ck-mono);
  font-size: 9.5px;
  font-variant-numeric: tabular-nums;
  margin-top: 3px;
}}

/* Buttons */
.cad-btn {{
  display: inline-block;
  background: var(--ck-panel-alt);
  border: 1px solid var(--ck-border);
  color: var(--ck-text);
  font-family: var(--ck-mono);
  font-size: 10.5px;
  letter-spacing: 0.08em;
  padding: 5px 12px;
  border-radius: 3px;
  cursor: pointer;
  text-decoration: none;
}}
.cad-btn:hover {{ border-color: {P['accent']}; color: {P['accent']}; }}
.cad-btn-primary {{
  background: {P['accent']};
  border-color: {P['accent']};
  color: #fff;
  font-weight: 600;
}}
.cad-btn-primary:hover {{ background: #2563eb; border-color: #2563eb; color: #fff; }}

/* Tables */
.cad-table {{ width: 100%; border-collapse: collapse; font-size: 11.5px; }}
.cad-table th {{
  background: var(--ck-panel-alt);
  border-bottom: 1px solid var(--ck-border);
  padding: 6px 8px;
  font-family: var(--ck-mono);
  font-size: 9.5px;
  font-weight: 600;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--ck-text-dim);
  text-align: left;
  white-space: nowrap;
}}
.cad-table th.num {{ text-align: right; }}
.cad-table td {{
  padding: 5px 8px;
  border-bottom: 1px solid var(--ck-border-dim);
  color: var(--ck-text);
  vertical-align: middle;
}}
.cad-table td.num {{
  text-align: right;
  font-family: var(--ck-mono);
  font-variant-numeric: tabular-nums;
}}
.cad-table tr:nth-child(even) td {{ background: var(--ck-stripe); }}

/* Badges */
.cad-badge {{
  display: inline-block;
  font-family: var(--ck-mono);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  padding: 2px 5px;
  border-radius: 2px;
  white-space: nowrap;
}}
.cad-badge-green {{ background: rgba(16,185,129,0.15); color: {P['positive']}; border: 1px solid rgba(16,185,129,0.3); }}
.cad-badge-amber {{ background: rgba(245,158,11,0.15); color: {P['warning']};  border: 1px solid rgba(245,158,11,0.3); }}
.cad-badge-red   {{ background: rgba(239,68,68,0.15);  color: {P['negative']}; border: 1px solid rgba(239,68,68,0.3); }}
.cad-badge-blue  {{ background: rgba(59,130,246,0.15); color: {P['accent']};   border: 1px solid rgba(59,130,246,0.3); }}
.cad-badge-muted {{ background: rgba(100,116,139,0.15); color: var(--ck-text-faint); border: 1px solid var(--ck-border); }}

/* Section code chip — small Bloomberg-style tag */
.cad-section-code {{
  font-family: var(--ck-mono);
  font-size: 9px;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--ck-text-faint);
  background: var(--ck-panel-alt);
  border: 1px solid var(--ck-border);
  padding: 1px 6px;
  border-radius: 2px;
}}

/* Form fields */
.cad-input, .cad-field input, .cad-field textarea, .cad-field select {{
  background: var(--ck-panel-alt);
  border: 1px solid var(--ck-border);
  color: var(--ck-text);
  font-family: var(--ck-mono);
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 3px;
  outline: none;
}}
.cad-input:focus, .cad-field input:focus, .cad-field textarea:focus, .cad-field select:focus {{
  border-color: {P['accent']};
}}
.cad-field {{ display: flex; flex-direction: column; gap: 4px; }}
.cad-field label {{
  font-family: var(--ck-mono);
  font-size: 10px;
  letter-spacing: 0.10em;
  color: var(--ck-text-faint);
  text-transform: uppercase;
}}

/* Ticker-id chip (used on a few pages for deal identifiers) */
.cad-ticker-id {{
  font-family: var(--ck-mono);
  font-size: 10.5px;
  letter-spacing: 0.08em;
  color: var(--ck-text-dim);
  border: 1px solid var(--ck-border);
  padding: 1px 6px;
  border-radius: 2px;
}}
.cad-ticker-id:hover {{ border-color: {P['accent']}; color: {P['accent']}; }}

/* Status bar items — shown only where pages include the old status row */
.cad-status-item {{ display: inline-flex; align-items: baseline; gap: 6px; margin-right: 14px; }}
.cad-status-key {{
  font-family: var(--ck-mono);
  font-size: 9px;
  letter-spacing: 0.15em;
  color: var(--ck-text-faint);
  text-transform: uppercase;
}}
.cad-status-val {{
  font-family: var(--ck-mono);
  font-size: 10.5px;
  color: var(--ck-text);
  font-variant-numeric: tabular-nums;
}}

/* Deal-identity strip used on deal dashboard + per-deal pages */
.cad-deal-ident {{
  font-family: var(--ck-mono);
  font-size: 10.5px;
  color: var(--ck-text-dim);
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}}
.cad-deal-ident .ident-key {{ color: var(--ck-text-faint); margin-right: 3px; }}
.cad-deal-ident .ident-val {{ color: var(--ck-text); font-weight: 600; }}
.cad-deal-ident .ident-sep {{ color: var(--ck-border); padding: 0 6px; }}

/* Heatmap cells — three-tier color scale used by a few pages */
.cad-heat-1 {{ background: rgba(239,68,68,0.18); color: {P['negative']}; }}
.cad-heat-2 {{ background: rgba(245,158,11,0.18); color: {P['warning']}; }}
.cad-heat-3 {{ background: rgba(16,185,129,0.18); color: {P['positive']}; }}

/* Legacy sticky-layout opt-out: shell_v2 set body overflow:hidden +
 * height:100vh. Chartis is scrollable. Force pages to behave. */
body.caduceus {{
  background: var(--ck-bg);
  color: var(--ck-text);
  font-family: var(--ck-sans);
  font-size: 12px;
  overflow: auto;
  height: auto;
}}
"""


# JavaScript for the four features. Concatenated into the shell's
# <script> block at render time. Each block is a self-contained IIFE so
# one failure can't take the others down.
_KEEP_FEATURES_JS = """
/* 1. CSRF token patcher — reads rcm_csrf cookie, injects csrf_token into
 *    POST forms and sets X-CSRF-Token on non-GET fetch() calls.
 *    Harmless if the cookie is absent (open mode). */
(function(){
  function c(n){var m=document.cookie.match(new RegExp('(?:^|; )'+n+'=([^;]*)'));
    return m?decodeURIComponent(m[1]):null;}
  document.addEventListener('submit',function(e){
    var t=c('rcm_csrf');if(!t)return;
    var f=e.target;if(!f||f.tagName!=='FORM')return;
    if(f.method&&f.method.toLowerCase()!=='post')return;
    var x=f.querySelector('input[name=csrf_token]');
    if(!x){x=document.createElement('input');x.type='hidden';
      x.name='csrf_token';f.appendChild(x);}
    x.value=t;
  },true);
  var of=window.fetch;
  if(of){window.fetch=function(u,o){
    o=o||{};var t=c('rcm_csrf');
    if(t&&o.method&&o.method.toUpperCase()!=='GET'){
      o.headers=o.headers||{};
      if(!o.headers['X-CSRF-Token'])o.headers['X-CSRF-Token']=t;
    }
    return of(u,o);
  };}
})();

/* 2. Alert badge poll — fetch /api/alerts/active-count once on load,
 *    show red pill with count when > 0. Silent on network error. */
(function(){
  fetch('/api/alerts/active-count')
    .then(function(r){return r.json();})
    .then(function(d){
      var b=document.getElementById('ck-alert-count');
      if(b&&d&&d.count>0){b.textContent=d.count;b.style.display='inline';}
    })
    .catch(function(){});
})();

/* 3. Vim-style shortcuts: ? opens help, / focuses search, g+<key> jumps.
 *    Disabled while typing in inputs/textareas/selects. */
(function(){
  var gMode=false,gTimer=null;
  var shortcuts={
    "h":"/home","a":"/analysis","p":"/portfolio","s":"/screen",
    "m":"/market-data/map","n":"/news","r":"/portfolio/regression",
    "l":"/library","i":"/import","d":"/api/docs",
    "b":"/pe-intelligence","o":"/portfolio-analytics"
  };
  document.addEventListener('keydown',function(e){
    if(e.target&&(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA'
        ||e.target.tagName==='SELECT'))return;
    // '?' toggles help (? == shift+/ so check for shift)
    if(e.key==='?'){
      e.preventDefault();
      var bd=document.getElementById('ck-kbhelp-bd');
      if(!bd)return;
      if(bd.classList.contains('open')){
        bd.classList.remove('open');bd.setAttribute('aria-hidden','true');
      } else {
        bd.classList.add('open');bd.setAttribute('aria-hidden','false');
      }
      return;
    }
    if(e.key==='Escape'){
      var bd=document.getElementById('ck-kbhelp-bd');
      if(bd&&bd.classList.contains('open')){
        bd.classList.remove('open');bd.setAttribute('aria-hidden','true');
        e.preventDefault();return;
      }
    }
    if(e.key==='/'){
      // Forward to the command palette if the page has no search input.
      var si=document.querySelector('input[type=search],input[name=q]');
      if(si){e.preventDefault();si.focus();return;}
    }
    if(e.key==='g'&&!gMode){
      gMode=true;clearTimeout(gTimer);
      gTimer=setTimeout(function(){gMode=false;},800);
      return;
    }
    if(gMode){
      gMode=false;clearTimeout(gTimer);
      var dest=shortcuts[e.key];
      if(dest){e.preventDefault();window.location.href=dest;}
    }
  });
})();

/* 4. Cmd+K command palette: modal with fuzzy filter, arrow nav, Enter to
 *    open the highlighted entry. Opens on Cmd+K (or Ctrl+K on non-Mac). */
(function(){
  var bd=document.getElementById('ck-palette-bd');
  var inp=document.getElementById('ck-palette-input');
  var res=document.getElementById('ck-palette-results');
  if(!bd||!inp||!res)return;
  var items=Array.prototype.slice.call(res.querySelectorAll('.ck-palette-item'));
  function render(q){
    q=(q||'').trim().toLowerCase();
    var firstMatch=null;
    items.forEach(function(el){
      var lbl=el.getAttribute('data-label')||'';
      var match=!q||lbl.indexOf(q)!==-1;
      el.style.display=match?'flex':'none';
      el.classList.remove('sel');
      if(match&&!firstMatch){firstMatch=el;}
    });
    if(firstMatch)firstMatch.classList.add('sel');
  }
  function open(){
    bd.classList.add('open');bd.setAttribute('aria-hidden','false');
    inp.value='';render('');
    setTimeout(function(){inp.focus();},10);
  }
  function close(){
    bd.classList.remove('open');bd.setAttribute('aria-hidden','true');
  }
  function move(dir){
    var visible=items.filter(function(el){return el.style.display!=='none';});
    if(!visible.length)return;
    var curIdx=visible.findIndex(function(el){return el.classList.contains('sel');});
    if(curIdx<0)curIdx=0;
    visible[curIdx].classList.remove('sel');
    curIdx=(curIdx+dir+visible.length)%visible.length;
    visible[curIdx].classList.add('sel');
    visible[curIdx].scrollIntoView({block:'nearest'});
  }
  function pick(){
    var s=res.querySelector('.ck-palette-item.sel');
    if(s&&s.style.display!=='none'){window.location.href=s.getAttribute('href');}
  }
  document.addEventListener('keydown',function(e){
    var cmd=e.metaKey||e.ctrlKey;
    if(cmd&&(e.key==='k'||e.key==='K')){
      e.preventDefault();
      if(bd.classList.contains('open'))close();else open();
      return;
    }
    if(!bd.classList.contains('open'))return;
    if(e.key==='Escape'){e.preventDefault();close();}
    else if(e.key==='ArrowDown'){e.preventDefault();move(1);}
    else if(e.key==='ArrowUp'){e.preventDefault();move(-1);}
    else if(e.key==='Enter'){e.preventDefault();pick();}
  });
  inp.addEventListener('input',function(){render(inp.value);});
  res.addEventListener('click',function(e){
    var a=e.target.closest('.ck-palette-item');if(a)close();
  });
  bd.addEventListener('click',function(e){if(e.target===bd)close();});
})();
"""


_SORTABLE_JS = """
(function() {
  const tables = document.querySelectorAll('table.sortable');
  tables.forEach(function(tbl) {
    const ths = tbl.querySelectorAll('thead th');
    const tbody = tbl.querySelector('tbody');
    let sortCol = -1, sortAsc = false;
    ths.forEach(function(th, col) {
      th.addEventListener('click', function() {
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const prevSorted = tbl.querySelector('thead th[data-sorted]');
        if (prevSorted) prevSorted.removeAttribute('data-sorted');
        if (sortCol === col) { sortAsc = !sortAsc; }
        else { sortCol = col; sortAsc = true; }
        th.setAttribute('data-sorted', sortAsc ? 'asc' : 'desc');
        rows.sort(function(a, b) {
          const ca = a.cells[col] ? a.cells[col].getAttribute('data-val') || a.cells[col].textContent.trim() : '';
          const cb = b.cells[col] ? b.cells[col].getAttribute('data-val') || b.cells[col].textContent.trim() : '';
          const na = parseFloat(ca), nb = parseFloat(cb);
          if (!isNaN(na) && !isNaN(nb)) return sortAsc ? na - nb : nb - na;
          return sortAsc ? ca.localeCompare(cb) : cb.localeCompare(ca);
        });
        rows.forEach(function(r) { tbody.appendChild(r); });
      });
    });
  });
  // Live search for tables with data-search-target
  const inputs = document.querySelectorAll('input[data-search-target]');
  inputs.forEach(function(inp) {
    inp.addEventListener('input', function() {
      const q = inp.value.toLowerCase();
      const tbl = document.querySelector(inp.getAttribute('data-search-target'));
      if (!tbl) return;
      tbl.querySelectorAll('tbody tr').forEach(function(row) {
        row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
    });
  });
})();
"""


# ---------------------------------------------------------------------------
# Number formatting utilities
# ---------------------------------------------------------------------------

def ck_fmt_num(value: Any, decimals: int = 1, suffix: str = "", na: str = "—") -> str:
    """Format a number with tabular-nums span. Returns HTML."""
    if value is None:
        return f'<span class="faint">{na}</span>'
    try:
        f = float(value)
        formatted = f"{f:,.{decimals}f}"
        col = ""
        if suffix == "x" and f < 1.0:
            col = " neg"
        elif suffix == "x" and f >= 3.0:
            col = " pos"
        return f'<span class="mn{col}">{formatted}{suffix}</span>'
    except (TypeError, ValueError):
        return f'<span class="faint">{na}</span>'


def ck_fmt_pct(value: Any, decimals: int = 1, signed: bool = False) -> str:
    """Format a fraction (0-1) as percentage."""
    if value is None:
        return '<span class="faint">—</span>'
    try:
        f = float(value) * 100.0
        sign = "+" if signed and f > 0 else ""
        col = " pos" if signed and f > 0 else (" neg" if signed and f < 0 else "")
        return f'<span class="mn{col}">{sign}{f:.{decimals}f}%</span>'
    except (TypeError, ValueError):
        return '<span class="faint">—</span>'


def ck_fmt_moic(value: Any) -> str:
    """Format MOIC with color coding."""
    if value is None:
        return '<span class="faint">—</span>'
    try:
        f = float(value)
        col = "neg" if f < 1.0 else ("pos" if f >= 2.5 else "")
        return f'<span class="mn {col}">{f:.2f}x</span>'
    except (TypeError, ValueError):
        return '<span class="faint">—</span>'


def ck_fmt_currency(value_mm: Any, decimals: int = 0) -> str:
    """Format value in $M with tabular-nums."""
    if value_mm is None:
        return '<span class="faint">—</span>'
    try:
        f = float(value_mm)
        if abs(f) >= 1000:
            return f'<span class="mn">${f/1000:,.{max(0,decimals-0)}f}B</span>'
        return f'<span class="mn">${f:,.{decimals}f}M</span>'
    except (TypeError, ValueError):
        return '<span class="faint">—</span>'


def ck_fmt_irr(value: Any) -> str:
    """Format IRR as percentage."""
    if value is None:
        return '<span class="faint">—</span>'
    try:
        f = float(value) * 100.0
        col = "neg" if f < 15 else ("pos" if f >= 25 else "")
        return f'<span class="mn {col}">{f:.1f}%</span>'
    except (TypeError, ValueError):
        return '<span class="faint">—</span>'


def ck_signal_badge(signal: Optional[str]) -> str:
    """Return HTML for a signal badge (green/yellow/red)."""
    if not signal:
        return '<span class="ck-sig ck-sig-na">N/A</span>'
    s = signal.lower()
    cls = {
        "green": "ck-sig-green",
        "yellow": "ck-sig-yellow",
        "red": "ck-sig-red",
        "additive": "ck-sig-green",
        "neutral": "ck-sig-yellow",
        "concentrating": "ck-sig-red",
    }.get(s, "ck-sig-na")
    label = {
        "green": "GREEN",
        "yellow": "YELLOW",
        "red": "RED",
        "additive": "ADDITIVE",
        "neutral": "NEUTRAL",
        "concentrating": "CONCENTRATING",
    }.get(s, signal.upper())
    return f'<span class="ck-sig {cls}">{_html.escape(label)}</span>'


def ck_grade_badge(grade: Optional[str]) -> str:
    """Return HTML for a data grade badge (A/B/C/D)."""
    if not grade:
        return '<span class="ck-grade ck-grade-d">?</span>'
    cls = {"A": "ck-grade-a", "B": "ck-grade-b", "C": "ck-grade-c", "D": "ck-grade-d"}.get(grade.upper(), "ck-grade-d")
    return f'<span class="ck-grade {cls}">{_html.escape(grade.upper())}</span>'


def ck_regime_badge(regime: Optional[str]) -> str:
    """Return HTML for a vintage regime badge."""
    if not regime:
        return '<span class="ck-sig ck-sig-na">—</span>'
    cls = {
        "expansion": "ck-sig-green",
        "recovery": "ck-sig-green",
        "normalization": "ck-sig-yellow",
        "peak": "ck-sig-red",
        "correction": "ck-sig-yellow",
        "contraction": "ck-sig-red",
    }.get(regime.lower(), "ck-sig-na")
    return f'<span class="ck-sig {cls}">{_html.escape(regime.upper())}</span>'


# ---------------------------------------------------------------------------
# Table builder
# ---------------------------------------------------------------------------

def ck_table(
    rows: List[Dict[str, Any]],
    columns: List[Dict[str, Any]],
    *,
    caption: str = "",
    sortable: bool = True,
    id: str = "ck-tbl",
) -> str:
    """Build an institutional dense table.

    Args:
        rows:    List of row dicts
        columns: List of {"key": ..., "label": ..., "type": "str|num|badge|moic|pct|irr|currency",
                          "width": ..., "nowrap": bool}
        caption: Table caption/title
        sortable: Enable client-side sorting
        id:      HTML id for the table element
    """
    sort_cls = " sortable" if sortable else ""
    header_cols = []
    for col in columns:
        num_cls = ' class="num"' if col.get("type") in ("num", "moic", "pct", "irr", "currency") else ""
        w = f' style="width:{col["width"]}"' if col.get("width") else ""
        header_cols.append(f'<th{num_cls}{w}>{_html.escape(str(col["label"]))}</th>')

    tbody_rows = []
    for row in rows:
        cells = []
        for col in columns:
            key = col["key"]
            ctype = col.get("type", "str")
            val = row.get(key)
            raw_val = val

            if ctype == "moic":
                cell_html = ck_fmt_moic(val)
                cls = 'class="num"'
            elif ctype == "pct":
                cell_html = ck_fmt_pct(val, col.get("decimals", 1))
                cls = 'class="num"'
            elif ctype == "irr":
                cell_html = ck_fmt_irr(val)
                cls = 'class="num"'
            elif ctype == "currency":
                cell_html = ck_fmt_currency(val, col.get("decimals", 0))
                cls = 'class="num"'
            elif ctype == "num":
                cell_html = ck_fmt_num(val, col.get("decimals", 1), col.get("suffix", ""))
                cls = 'class="num"'
            elif ctype == "signal":
                cell_html = ck_signal_badge(str(val) if val is not None else None)
                cls = 'class=""'
                raw_val = val
            elif ctype == "grade":
                cell_html = ck_grade_badge(str(val) if val is not None else None)
                cls = 'class=""'
            elif ctype == "regime":
                cell_html = ck_regime_badge(str(val) if val is not None else None)
                cls = 'class=""'
            elif ctype == "link":
                href = col.get("href_key")
                href_val = _html.escape(str(row.get(href, "#"))) if href else "#"
                display = _html.escape(str(val) if val is not None else "—")
                cell_html = f'<a href="{href_val}">{display}</a>'
                cls = 'class=""'
            else:
                display = _html.escape(str(val) if val is not None else "—")
                if val is None:
                    display = '<span class="faint">—</span>'
                cell_html = display
                cls = 'class="dim"' if col.get("dim") else 'class=""'

            data_val = ""
            try:
                if raw_val is not None:
                    fv = float(raw_val)
                    data_val = f' data-val="{fv}"'
            except (TypeError, ValueError):
                if raw_val is not None:
                    data_val = f' data-val="{str(raw_val)}"'

            cells.append(f'<td {cls}{data_val}>{cell_html}</td>')
        tbody_rows.append(f'<tr>{"".join(cells)}</tr>')

    panel_title = f'<div class="ck-panel-title">{_html.escape(caption)}</div>' if caption else ""
    return (
        f'<div class="ck-panel">'
        f'{panel_title}'
        f'<div class="ck-table-wrap">'
        f'<table class="ck-table{sort_cls}" id="{id}">'
        f'<thead><tr>{"".join(header_cols)}</tr></thead>'
        f'<tbody>{"".join(tbody_rows)}</tbody>'
        f'</table>'
        f'</div>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# KPI / section header helpers
# ---------------------------------------------------------------------------

def ck_kpi_block(label: str, value: str, unit: str = "", delta: str = "") -> str:
    """Render a single KPI tile."""
    delta_html = ""
    if delta:
        cls = "ck-delta-pos" if delta.startswith("+") else ("ck-delta-neg" if delta.startswith("-") else "")
        delta_html = f'<div class="ck-kpi-delta {cls}">{_html.escape(delta)}</div>'
    return (
        f'<div class="ck-kpi">'
        f'<div class="ck-kpi-label">{_html.escape(label)}</div>'
        f'<div class="ck-kpi-value">{value}</div>'
        f'<div class="ck-kpi-unit">{_html.escape(unit)}</div>'
        f'{delta_html}'
        f'</div>'
    )


def ck_section_header(title: str, subtitle: str = "", count: Optional[int] = None) -> str:
    """Render a section header with optional count badge."""
    count_html = f'<span class="ck-section-count">{count}</span>' if count is not None else ""
    sub_html = f'<span class="dim" style="font-size:10px;margin-left:8px;">{_html.escape(subtitle)}</span>' if subtitle else ""
    return (
        f'<div class="ck-section">'
        f'<span class="ck-section-label">{_html.escape(title)}</span>'
        f'{sub_html}'
        f'{count_html}'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Nav builder
# ---------------------------------------------------------------------------

def _nav_html(active_path: str = "") -> str:
    parts = []
    for item in _CORPUS_NAV:
        if item.get("separator"):
            parts.append(f'<div class="ck-nav-sep">{_html.escape(item["label"])}</div>')
        else:
            href = item.get("href", "#")
            is_active = " active" if href == active_path else ""
            icon = _html.escape(item.get("icon", "·"))
            label = _html.escape(item["label"])
            parts.append(
                f'<a href="{href}" class="ck-nav-item{is_active}">'
                f'<span class="ck-nav-icon">{icon}</span>'
                f'{label}'
                f'</a>'
            )
    return f'<nav class="ck-nav">{"".join(parts)}</nav>'


# ---------------------------------------------------------------------------
# Shell
# ---------------------------------------------------------------------------

def chartis_shell(
    body: str,
    title: str,
    *,
    active_nav: str = "",
    subtitle: str = "",
    extra_css: str = "",
    extra_js: str = "",
) -> str:
    """Render a full dark institutional page.

    Args:
        body:       Inner HTML content
        title:      Page title (shown in top bar and <title>)
        active_nav: Path matching a nav item href to highlight
        subtitle:   Optional subtitle below page title
        extra_css:  Additional CSS
        extra_js:   Additional JS
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sub_html = f'<div class="ck-page-sub">{_html.escape(subtitle)}</div>' if subtitle else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_html.escape(title)} — Seeking Chartis Corpus</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
<style>
{_BASE_CSS}
{_KEEP_FEATURES_CSS}
{_CAD_COMPAT_CSS}
{extra_css}
</style>
</head>
<body>
<div class="ck-bar">
  <span class="ck-bar-logo">Seeking Chartis</span>
  <span class="ck-bar-section">Corpus Intelligence</span>
  <span class="ck-bar-title">{_html.escape(title)}</span>
  <span class="ck-bar-time">{now}</span>
  {_alert_bell_html()}
</div>
<div class="ck-layout">
  {_nav_html(active_nav)}
  <main class="ck-main">
    <div class="ck-page-header">
      <div class="ck-page-title">{_html.escape(title)}</div>
      {sub_html}
    </div>
    {body}
  </main>
</div>
{_palette_html()}
{_kb_help_html()}
<script>
{_SORTABLE_JS}
{_KEEP_FEATURES_JS}
{extra_js}
</script>
</body>
</html>"""
