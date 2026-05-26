"""Single source of truth for DATA REQUIRED page activation.

Each DATA REQUIRED page activates on the user's own uploaded deal/fund data.
This registry pairs every such route with: what to upload, who to request it
from, what the page computes once activated, the import template, and a
grouping category. It is consumed by:

  • the Guide page-contexts (manual_page_contexts.py),
  • the per-page "Data needed to activate" panels (indirectly), and
  • the Data Activation Center hub (/data-activation).

Keeping it here means those stay in sync. No fabricated values anywhere —
this only describes the data a user must supply.
"""
from __future__ import annotations

from typing import Dict, List, NamedTuple


class Activation(NamedTuple):
    route: str
    title: str
    upload: str          # what to upload
    request_from: str    # who to ask
    activates: str       # what it computes once live
    template: str        # import template filename (docs/import_templates/)
    category: str        # grouping key


_CATEGORIES = {
    "internal_fund": "Internal / fund / deal ops",
    "rcm_risk": "Revenue cycle & risk",
    "ops_other": "Insurance · litigation · cyber · real estate · HCIT",
    "calculators": "Per-roster calculators",
}

# (route, title, upload, request_from, activates, template, category)
_ROWS = [
    ("/mgmt-comp", "Management Compensation", "executive comp (base/bonus/equity/FMV)", "CFO / HR / comp consultant", "comp-vs-FMV benchmarking + Stark/AKS overlap flags", "management_compensation_template.csv", "internal_fund"),
    ("/partner-economics", "Partner Economics", "partner points/carry/draws/distributions", "Fund CFO / fund administrator", "carry waterfall + partner economics roll-up", "partner_economics_template.csv", "internal_fund"),
    ("/mgmt-fee-tracker", "Management Fee Tracker", "fund mgmt-fee schedule + basis + offsets", "Fund CFO / fund administrator", "fee drag + offset tracking", "mgmt_fee_schedule_template.csv", "internal_fund"),
    ("/key-person", "Key Person", "key execs, tenure, succession, dependency", "Management / HR", "key-person dependency + succession-gap risk", "key_person_template.csv", "internal_fund"),
    ("/treasury", "Treasury", "cash, debt schedule, facilities, covenants", "Portfolio-company CFO", "liquidity runway + covenant headroom + refi timing", "treasury_debt_schedule_template.csv", "internal_fund"),
    ("/fundraising", "Fundraising", "fund target, LP commitments, pipeline", "IR / fundraising team", "fund-close tracking + LP pipeline coverage", "fundraising_template.csv", "internal_fund"),
    ("/nav-loan-tracker", "NAV Loan Tracker", "NAV facilities, advance rate, LTV, cost", "Fund CFO / NAV lender", "advance-rate headroom, LTV, all-in cost", "nav_loan_template.csv", "internal_fund"),
    ("/secondaries-tracker", "Secondaries Tracker", "secondary offers, NAV, discount, buyer", "Fund CFO / secondary advisor", "offer-vs-NAV discount + buyer pipeline", "secondaries_template.csv", "internal_fund"),
    ("/continuation-vehicle", "Continuation Vehicle", "CV assets, NAV, rollover %, terms", "Fund CFO / CV advisor", "rollover-vs-new-capital mix + CV terms", "continuation_vehicle_template.csv", "internal_fund"),
    ("/coinvest-pipeline", "Co-Invest Pipeline", "co-invest opportunities, sizing, LP demand", "Deal team / IR", "co-invest sizing vs LP-demand coverage", "coinvest_pipeline_template.csv", "internal_fund"),
    ("/board-governance", "Board Governance", "board roster, committees, cadence", "Corporate secretary / GC", "board independence + committee coverage", "board_governance_template.csv", "internal_fund"),
    ("/capex-budget", "Capex Budget", "capex projects, budget/actual, ROI", "Portfolio-company CFO / FP&A", "budget-vs-actual + maintenance/growth split + ROI", "capex_budget_template.csv", "internal_fund"),
    ("/operating-partners", "Operating Partners", "OP roster, assignments, value-add KPIs", "Operating-partner team", "OP coverage + value-add KPI tracking", "operating_partners_template.csv", "internal_fund"),
    ("/compliance-attestation", "Compliance Attestation", "attestations, owners, due dates, status", "Compliance officer / GC", "attestation completion + overdue tracking", "compliance_attestation_template.csv", "internal_fund"),
    ("/transition-services", "Transition Services (TSA)", "TSA scope, duration, cost, exit plan", "Seller / integration management office", "TSA cost + exit-timeline tracking", "tsa_template.csv", "internal_fund"),
    ("/pmi-integration", "PMI Integration", "integration workstreams, milestones, synergy", "Integration lead / IMO", "milestone + synergy-capture tracking", "pmi_integration_template.csv", "internal_fund"),
    ("/pmi-playbook", "PMI Playbook", "playbook tasks by function, owners, timing", "Integration lead / IMO", "100-day playbook task tracking", "pmi_integration_template.csv", "internal_fund"),
    ("/sellside-process", "Sell-Side Process", "process timeline, buyer list, bids", "Sell-side advisor / banker", "process timeline + bid tracking", "sellside_process_template.csv", "internal_fund"),
    ("/diligence-vendors", "Diligence Vendors", "vendor list, scope, fees, status", "Deal team", "vendor scope + fee + deliverable tracking", "diligence_vendors_template.csv", "internal_fund"),
    ("/vdr-tracker", "VDR Tracker", "data-room index, request log, Q&A", "Deal team / seller", "data-room completeness + outstanding requests", "vdr_tracker_template.csv", "internal_fund"),
    ("/vcp-tracker", "Value-Creation Plan Tracker", "VCP initiatives, owners, $ impact", "Value-creation lead / deal team", "VCP progress + EBITDA-impact roll-up", "vcp_tracker_template.csv", "internal_fund"),
    ("/zbb-tracker", "Zero-Based Budget Tracker", "cost lines, baseline, target, savings", "FP&A / portfolio-company CFO", "zero-based savings vs baseline", "zbb_tracker_template.csv", "internal_fund"),
    ("/platform-maturity", "Platform Maturity", "maturity dimensions, self-scores, evidence", "Management / portfolio operations", "maturity self-assessment vs target", "platform_maturity_template.csv", "internal_fund"),
    ("/ai-operating-model", "AI Operating Model", "AI use-cases, adoption, ROI, risk", "CIO / digital transformation lead", "AI use-case adoption + ROI + risk tracking", "ai_operating_model_template.csv", "internal_fund"),
    ("/direct-lending", "Direct Lending", "loan book, spreads, covenants, defaults", "Credit / private-credit team", "loan-book spread, covenant, default tracking", "direct_lending_template.csv", "internal_fund"),
    ("/revenue-leakage", "Revenue Leakage", "charge master, 835 remittance, denial codes, AR aging", "RCM / revenue-cycle lead", "denial-driven leakage + underpayment detection", "claims_denials_template.csv", "rcm_risk"),
    ("/rcm-red-flags", "RCM Red Flags", "claims extract, denial codes, AR aging, encounter volume", "RCM / revenue-cycle lead", "RCM red-flag detection (denials, DAR, aged AR)", "claims_denials_template.csv", "rcm_risk"),
    ("/redflag-scanner", "Red-Flag Scanner", "financials, KPIs, payer mix, AR aging", "CFO / FP&A / deal team", "cross-financial red-flag scan", "ar_aging_template.csv", "rcm_risk"),
    ("/risk-matrix", "Risk Matrix", "risk register (likelihood/impact/owner/mitigation)", "Deal team / risk owners", "likelihood×impact risk heatmap", "risk_register_template.csv", "rcm_risk"),
    ("/insurance-tracker", "Insurance Tracker", "policy schedule, limits, premiums, claims history", "Risk manager / insurance broker", "coverage adequacy + premium trend + renewal calendar", "insurance_schedule_template.csv", "ops_other"),
    ("/rw-insurance", "RW Insurance", "policy list, coverage, renewal, loss runs", "Risk manager / broker", "coverage + loss-run review", "insurance_schedule_template.csv", "ops_other"),
    ("/litigation", "Litigation", "matter list, status, exposure, reserves", "General counsel / litigation counsel", "litigation exposure + reserve adequacy", "litigation_matters_template.csv", "ops_other"),
    ("/cyber-risk", "Cyber Risk", "controls inventory, frameworks, incidents", "CISO / IT security", "control-framework coverage + gap assessment", "cyber_controls_template.csv", "ops_other"),
    ("/medical-realestate", "Medical Real Estate", "lease schedule, rent, term, options, owned RE", "Real estate / facilities", "lease cost, term, renewal-option exposure", "lease_schedule_template.csv", "ops_other"),
    ("/real-estate", "Real Estate", "property list, lease/own, value, NOI", "Real estate / facilities", "owned-vs-leased mix, NOI, lease exposure", "lease_schedule_template.csv", "ops_other"),
    ("/hcit-platform", "HCIT Platform", "EHR/RCM vendor stack, contracts, modules", "CIO / IT", "EHR/RCM stack cost + contract-renewal map", "ehr_vendor_stack_template.csv", "ops_other"),
    ("/tech-stack", "Tech Stack", "application inventory, spend, contracts", "CIO / IT", "application inventory + spend + renewals", "ehr_vendor_stack_template.csv", "ops_other"),
    ("/clinical-ai", "Clinical AI", "AI tools, vendors, use-cases, validation", "CMIO / clinical informatics", "clinical-AI tool inventory + adoption + validation", "ai_operating_model_template.csv", "ops_other"),
    ("/digital-front-door", "Digital Front Door", "patient-access channels, volumes, conversion", "Patient access / marketing", "access-channel volume + conversion + leakage", "digital_front_door_template.csv", "ops_other"),
    ("/direct-employer", "Direct Employer", "employer contracts, lives, PEPM, services", "Sales / employer-contracting", "direct-employer roster + PEPM economics", "direct_employer_template.csv", "ops_other"),
    ("/diligence/physician-eu", "Physician Economic Unit", "provider roster, wRVU, collections, comp, payer mix", "CFO / practice management / RCM", "real per-provider P&L + roster optimization", "management_compensation_template.csv", "calculators"),
    ("/diligence/risk-workbench", "Risk Workbench", "risk register / regulatory inputs", "Deal team / risk owners", "the nine-panel risk panorama from your real inputs", "risk_register_template.csv", "calculators"),
]

ACTIVATIONS: List[Activation] = [Activation(*r) for r in _ROWS]
ACTIVATION_BY_ROUTE: Dict[str, Activation] = {a.route: a for a in ACTIVATIONS}


def category_label(key: str) -> str:
    return _CATEGORIES.get(key, key)


def categories() -> List[str]:
    return list(_CATEGORIES)
