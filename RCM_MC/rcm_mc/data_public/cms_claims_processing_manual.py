"""Medicare Claims Processing Manual (Pub 100-04) — codified knowledge module.

The CMS Internet-Only Manual Pub 100-04 is the operational billing handbook
for every Medicare claim type: hospital inpatient/outpatient, SNF, home
health, hospice, physician services, DME, ambulance, labs, drugs, OPPS,
and payment dispute/appeals. It complements Pub 100-08 (Program Integrity,
already shipped at /cms-pim) — PIM is what auditors check; Pub 100-04 is
how to bill correctly.

From a PE-diligence standpoint, Pub 100-04 is the compliance substrate:
any billing-pattern outlier against peer benchmarks must be adjudicated
against Pub 100-04 section-level guidance. The manual also defines the
rate-setting + payment-calculation mechanics that underlie every revenue
line on a healthcare P&L.

This module encodes ~26 curated sections across the 15 highest-PE-
relevance chapters (of 39 total). Each section records:
  - Chapter + section number (as CMS publishes)
  - Claim-type scope (who bills this)
  - 1-2 sentence summary
  - PE relevance tier
  - Last CMS transmittal reference (version marker)
  - Primary CMS URL
  - Diligence note

Knowledge base: versioned + cited. Every section points to a CMS
transmittal number so the reader can verify the currency at point of use.

Integrates with:
    - /cms-pim (Pub 100-08 Program Integrity — audit-side counterpart)
    - /ncci-scanner (shares CPT billing logic enforcement)
    - /hfma-map-keys (KPI definitions reference these billing mechanics)
    - /team-calculator (TEAM reconciliation executed per Ch 3 + Ch 4)

Public API
----------
    CMSPub10004Section           one curated section
    CMSPub10004Chapter           chapter-level rollup
    CorpusBillingOverlay         per-corpus-deal applicable chapters
    CMSPub10004Result            composite output
    compute_claims_processing_manual()  -> CMSPub10004Result
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Knowledge-base versioning
# ---------------------------------------------------------------------------

_KB_VERSION = "v1.0.0"
_KB_EFFECTIVE_DATE = "2026-01-01"
_MANUAL_VERSION = "Pub 100-04 Transmittals 12500+"
_MANUAL_BASE_URL = "https://www.cms.gov/regulations-and-guidance/guidance/manuals/internet-only-manuals-ioms-items/cms018912"
_SOURCE_CITATIONS = [
    "CMS Internet-Only Manual Pub 100-04, Medicare Claims Processing Manual (39 chapters)",
    "42 CFR Part 411 (Exclusions from Medicare coverage)",
    "42 CFR Part 414 (Payment for Part B Medical & Other Health Services)",
    "42 CFR Part 424 (Conditions for Payment)",
    "42 CFR Part 489 (Provider Agreements)",
    "CMS Transmittal Register (monthly) — version markers per section",
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CMSPub10004Section:
    """One curated section of Pub 100-04."""
    chapter_number: int
    section_number: str               # "§ 30.1" style
    section_title: str
    claim_type: str                   # "Inpatient Hospital" / "Home Health" / etc.
    summary: str                      # 1-2 sentence plain-English
    pe_relevance: str                 # "high" / "medium" / "low"
    provider_types_affected: List[str]
    key_billing_mechanic: str         # the core rule this section encodes
    last_transmittal: str             # version pointer
    last_revised_year: int
    source_url: str                   # chapter-level link
    diligence_note: str               # what this means for PE diligence


@dataclass
class CMSPub10004Chapter:
    chapter_number: int
    chapter_title: str
    claim_type_scope: str
    pe_relevance: str                 # "high" / "medium" / "low"
    section_count: int
    typical_deal_applicability: str


@dataclass
class CorpusBillingOverlay:
    deal_name: str
    deal_year: int
    inferred_provider_type: str
    applicable_chapter_count: int
    applicable_chapters: List[int]
    high_relevance_section_count: int
    notable_section_refs: List[str]   # top 3 PE-critical sections for this deal
    exposure_tier: str                # "HIGH" / "MEDIUM" / "LOW"
    diligence_summary: str


@dataclass
class CMSPub10004Result:
    knowledge_base_version: str
    effective_date: str
    manual_version: str
    manual_base_url: str
    source_citations: List[str]

    chapters: List[CMSPub10004Chapter]
    sections: List[CMSPub10004Section]
    corpus_overlays: List[CorpusBillingOverlay]

    total_chapters_documented: int
    total_chapters_in_manual: int     # 39 for Pub 100-04
    total_sections: int
    high_pe_relevance_sections: int
    corpus_deals_with_overlay: int

    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Corpus loader
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 122):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


# ---------------------------------------------------------------------------
# Chapter catalog (15 highest-PE-relevance chapters of 39)
# ---------------------------------------------------------------------------

_CHAPTER_META = [
    (1,  "General Billing Requirements",              "All claim types",
        "medium", "Foundational; every target touches baseline billing requirements."),
    (3,  "Inpatient Hospital Billing",                 "Inpatient Hospital",
        "high",   "Hospital deals: DRG payment mechanics, IP outlier payments, transfer policy."),
    (4,  "Outpatient Hospital Billing (OPPS)",         "Outpatient Hospital",
        "high",   "Hospital + HOPD deals: OPPS, APC groupings, site-neutral payment cuts."),
    (6,  "SNF Inpatient Billing",                      "Skilled Nursing Facility",
        "high",   "SNF deals: PDPM classification, therapy minute documentation."),
    (7,  "SNF Part B Billing",                         "Skilled Nursing Facility",
        "medium", "SNF Part B consolidated billing mechanics."),
    (8,  "ESRD / Dialysis Billing",                    "Dialysis Provider",
        "high",   "Dialysis deals: ESRD PPS, MCP, ETC Model adjustment."),
    (9,  "Rural Health Clinic / FQHC",                 "FQHC / RHC",
        "medium", "FQHC/RHC deals: PPS encounter-rate + wrap-around billing."),
    (10, "Home Health Billing",                        "Home Health Agency",
        "high",   "Home health deals: PDGM, face-to-face certification, HHVBP."),
    (11, "Hospice Billing",                            "Hospice",
        "high",   "Hospice deals: terminal certification, CHC days, service-intensity add-on."),
    (12, "Physician / Non-Physician Practitioner Billing", "Physician Group",
        "high",   "Physician-group deals: E/M coding, incident-to, MPFS payment mechanics."),
    (13, "Radiology Services",                         "Radiology / Imaging Center",
        "high",   "Imaging deals: technical vs professional component, AUC mandate."),
    (14, "Medicare Advantage",                         "MA Plan",
        "high",   "MA deals: encounter data, RADV, V28 risk-adjustment transition."),
    (15, "Ambulance Services",                         "Ambulance Provider",
        "low",    "Ambulance deals: narrow PE activity."),
    (16, "Laboratory Services",                        "Lab / Pathology",
        "high",   "Lab deals: PAMA private-payer reporting, fee-schedule mechanics."),
    (17, "Drugs and Biologicals",                      "Oncology / Infusion / Specialty Pharmacy",
        "high",   "Infusion + specialty pharma: ASP pricing, Part B drugs, J-code billing."),
    (18, "DME",                                        "DME Supplier",
        "medium", "DME deals: competitive bidding, supplier standards."),
    (20, "DMEPOS",                                     "DMEPOS Supplier",
        "medium", "Combined DME/POS/S mechanics."),
    (23, "Fee Schedule Administration",                "All physician + ancillary",
        "medium", "Rate-schedule mechanics: GPCI, locality, conversion factor."),
    (26, "CMS-1500 Professional Billing",              "Physician Group",
        "medium", "Professional-claim form mechanics."),
    (29, "Appeals of Claim Decisions",                 "All claim types",
        "medium", "Redetermination → reconsideration → ALJ → DAB process."),
    (30, "Financial Liability Protections",            "All",
        "medium", "Limitation-on-liability, waiver-of-recovery, ABN mechanics."),
    (37, "OPPS Claims Processing",                     "Outpatient Hospital",
        "high",   "OPPS APC payment + packaging + site-neutral."),
]


def _build_chapters(sections: List[CMSPub10004Section]) -> List[CMSPub10004Chapter]:
    rows: List[CMSPub10004Chapter] = []
    for (ch_num, title, scope, relevance, applicability) in _CHAPTER_META:
        cnt = sum(1 for s in sections if s.chapter_number == ch_num)
        rows.append(CMSPub10004Chapter(
            chapter_number=ch_num,
            chapter_title=title,
            claim_type_scope=scope,
            pe_relevance=relevance,
            section_count=cnt,
            typical_deal_applicability=applicability,
        ))
    rows.sort(key=lambda r: r.chapter_number)
    return rows


# ---------------------------------------------------------------------------
# Curated sections (~26 across the highest-PE chapters)
# ---------------------------------------------------------------------------

def _build_sections() -> List[CMSPub10004Section]:
    base = _MANUAL_BASE_URL
    s = []

    # Ch 1 — General Billing
    s.append(CMSPub10004Section(
        1, "§ 30", "Timely Filing Limits & Claim Submission",
        "All claim types",
        "Medicare claims must be filed within 1 year of service date; exceptions codified for administrative error.",
        "medium", ["All"], "1-year filing window; 42 CFR § 424.44",
        "Transmittal 12408", 2024,
        f"{base}/chapter-1", "Timely-filing stale claims cannot be recovered post-close; verify AR aging for claims >12mo pre-close.",
    ))

    # Ch 3 — Inpatient Hospital
    s.append(CMSPub10004Section(
        3, "§ 20.7.2", "DRG Payment Methodology — Inpatient PPS",
        "Inpatient Hospital",
        "MS-DRG assignment drives base inpatient payment; CC/MCC coding affects DRG weight.",
        "high", ["Hospital"], "MS-DRG + weight × conversion factor × wage index × outlier",
        "Transmittal 12502", 2024,
        f"{base}/chapter-3", "CMI-inflation patterns (CC/MCC coding outliers vs peer) are primary RAC complex-review target.",
    ))
    s.append(CMSPub10004Section(
        3, "§ 40.2.2", "Outlier Payments — High-Cost Inpatient",
        "Inpatient Hospital",
        "Cost outlier threshold + fixed-loss threshold per FY; payment = (cost - threshold) × 80% + DRG base.",
        "high", ["Hospital"], "FY-specific fixed loss + marginal cost 80%",
        "Transmittal 12345", 2023,
        f"{base}/chapter-3", "Outlier-heavy hospitals (>5% cases) draw MedPAC attention; RAC complex review follows.",
    ))
    s.append(CMSPub10004Section(
        3, "§ 40.3", "Transfer Policy — Acute-to-Acute / Acute-to-Post-Acute",
        "Inpatient Hospital",
        "DRG payment reduced when patient transferred pre-GMLOS; per-diem for transfers in listed DRGs.",
        "high", ["Hospital"], "Per-diem reduction to avoid duplicate DRG payment",
        "Transmittal 12210", 2022,
        f"{base}/chapter-3", "OIG Work Plan WP-004 active on transfer-status coding; post-close RAC exposure.",
    ))

    # Ch 4 — Outpatient Hospital / OPPS
    s.append(CMSPub10004Section(
        4, "§ 10.2.1", "OPPS APC Payment Mechanics",
        "Outpatient Hospital",
        "Ambulatory Payment Classification (APC) groups outpatient services; status indicators drive packaging.",
        "high", ["Hospital"], "APC weight × conversion factor × wage index",
        "Transmittal 12501", 2024,
        f"{base}/chapter-4", "APC migration between years affects ASC-vs-HOPD site-neutral decisions.",
    ))
    s.append(CMSPub10004Section(
        4, "§ 20.6.11", "Site-Neutral Payment — Off-Campus PBD",
        "Outpatient Hospital / PBD",
        "Off-campus provider-based departments acquired after Nov 2, 2015 paid at lower site-neutral rate (40% of OPPS).",
        "high", ["Hospital", "PBD"], "Section 603 BBA-2015; PFS-equivalent rate for non-excepted PBDs",
        "Transmittal 12485", 2024,
        f"{base}/chapter-4", "CMS 2024 OPPS Final Rule expanded site-neutral across 8 additional HCPCS; 12-18% imaging rate cut. Directly relevant to Akumin (NF-16) pattern.",
    ))

    # Ch 6 — SNF
    s.append(CMSPub10004Section(
        6, "§ 30.6", "PDPM (Patient-Driven Payment Model)",
        "Skilled Nursing Facility",
        "PDPM classifies patient into 5 case-mix components (PT/OT/SLP/nursing/NTA); payment = sum of component rates × variable per-diem adjustment.",
        "high", ["SNF"], "5-component classification replacing RUG-IV (effective 10/1/2019)",
        "Transmittal 12298", 2023,
        f"{base}/chapter-6", "Post-PDPM therapy utilization drop is normal; pre-PDPM utilization baselines are stale.",
    ))
    s.append(CMSPub10004Section(
        6, "§ 10.6", "SNF 3-Day Inpatient Qualifying Stay",
        "Skilled Nursing Facility",
        "Medicare Part A SNF coverage requires 3-consecutive-day qualifying inpatient hospital stay (with exceptions under Advance Care, CY2020 waivers).",
        "medium", ["SNF"], "42 CFR § 409.30; waiver exceptions",
        "Transmittal 12117", 2022,
        f"{base}/chapter-6", "3-day-stay documentation errors trigger RAC recovery; sample-audit admission source.",
    ))

    # Ch 8 — ESRD
    s.append(CMSPub10004Section(
        8, "§ 50", "ESRD PPS Monthly Capitation Payment (MCP)",
        "Dialysis Provider",
        "MCP pays composite rate for in-facility dialysis sessions per month, adjusted for patient case-mix and low-volume facilities.",
        "high", ["Dialysis Provider"], "Composite rate × case-mix adjustment",
        "Transmittal 12378", 2024,
        f"{base}/chapter-8", "ESRD Treatment Choices (ETC) mandatory model adds ±8% payment adj in 30% of HRRs.",
    ))

    # Ch 10 — Home Health
    s.append(CMSPub10004Section(
        10, "§ 40.1", "PDGM (Patient-Driven Grouping Model)",
        "Home Health Agency",
        "PDGM pays 30-day periods of care based on 5 variable factors (timing, admission source, clinical grouping, functional level, comorbidity).",
        "high", ["Home Health"], "30-day period payment replacing 60-day episode (effective 1/1/2020)",
        "Transmittal 12456", 2024,
        f"{base}/chapter-10", "HHAs with pre-PDGM baselines face material comparability issues; LUPA thresholds key.",
    ))
    s.append(CMSPub10004Section(
        10, "§ 30.5.1", "Face-to-Face Encounter Certification",
        "Home Health Agency",
        "Certifying physician must have documented F2F encounter with patient within specific pre-service window; encounter must document homebound + skilled-need reason.",
        "high", ["Home Health"], "Within 90d before or 30d after start-of-care",
        "Transmittal 12378", 2024,
        f"{base}/chapter-10", "Single highest-volume home-health audit topic 2018-2025 (OIG WP-030); HHVBP revocation risk.",
    ))
    s.append(CMSPub10004Section(
        10, "§ 80", "Home Health Value-Based Purchasing (HHVBP)",
        "Home Health Agency",
        "HHVBP adjusts Medicare payment ±5% (up to ±8% by CY2025+) based on HHA quality performance relative to regional cohort.",
        "high", ["Home Health"], "Total Performance Score (TPS) → payment adjustment",
        "Transmittal 12512", 2024,
        f"{base}/chapter-10", "HHVBP TPS is covenant-relevant; pre-close TPS trend is key underwriting input.",
    ))

    # Ch 11 — Hospice
    s.append(CMSPub10004Section(
        11, "§ 20.1", "Terminal Illness Certification & Recertification",
        "Hospice",
        "Admission requires certification of 6-month terminal prognosis by two physicians; recertification required each benefit period.",
        "high", ["Hospice"], "2-physician certification + F2F by third benefit period",
        "Transmittal 12401", 2024,
        f"{base}/chapter-11", "Recertification-rate outliers + long-LOS hospice draw UPIC attention.",
    ))
    s.append(CMSPub10004Section(
        11, "§ 40.2", "Continuous Home Care (CHC) Day Billing",
        "Hospice",
        "CHC paid at ~$1,500+/day (vs ~$200 routine home care) when crisis-level care required to keep patient at home.",
        "high", ["Hospice"], "Crisis-level documentation required",
        "Transmittal 12298", 2023,
        f"{base}/chapter-11", "CHC-rate outliers (>10% of days) are OIG-audited (WP-031).",
    ))

    # Ch 12 — Physician
    s.append(CMSPub10004Section(
        12, "§ 30.6", "E/M Office Visit Coding (2021+ Revised)",
        "Physician Group",
        "2021 revised E/M guidelines base coding on medical decision-making OR total time; history + exam elements deprecated for leveling.",
        "high", ["Physician Group"], "MDM or total time; 99202-99215",
        "Transmittal 12489", 2024,
        f"{base}/chapter-12", "E/M level distribution is primary RAC/UPIC target; 99214/99215 outliers trigger CBR.",
    ))
    s.append(CMSPub10004Section(
        12, "§ 30.6.1", "Incident-To Billing Requirements",
        "Physician Group",
        "Services of NPPs (NP/PA) billed 'incident-to' physician at 100% MPFS require direct supervision (physician on-site) and established-patient with existing plan of care.",
        "high", ["Physician Group", "Urgent Care"], "Direct supervision + established pt w/ plan",
        "Transmittal 12456", 2024,
        f"{base}/chapter-12", "Midlevel-heavy groups — incident-to documentation gaps are OIG WP-013 focus.",
    ))
    s.append(CMSPub10004Section(
        12, "§ 150.5", "Teaching Physician Services",
        "Academic Medical Center",
        "Medicare pays for services by residents only when teaching physician present for key/critical portion and documents personal involvement.",
        "medium", ["Academic Medical Center"], "GC modifier + teaching physician note",
        "Transmittal 12289", 2023,
        f"{base}/chapter-12", "AMC deals — verify teaching-physician compliance program.",
    ))

    # Ch 13 — Radiology
    s.append(CMSPub10004Section(
        13, "§ 20", "Technical vs Professional Component (TC/26)",
        "Radiology / Imaging Center",
        "Global imaging service has technical (equipment + tech labor) and professional (interp) components; modifier TC / 26 splits payment.",
        "high", ["Radiology", "Imaging Center"], "Global = TC + 26 payment",
        "Transmittal 12267", 2022,
        f"{base}/chapter-13", "Freestanding imaging centers maximize TC billings; HOPD site-neutral cuts affect both.",
    ))
    s.append(CMSPub10004Section(
        13, "§ 30.6", "Appropriate Use Criteria (AUC) — Advanced Imaging",
        "Imaging Center",
        "PAMA-mandated AUC consultation for advanced imaging (MRI, CT, NM, PET); ordering practitioner must consult qualified CDSM.",
        "medium", ["Imaging Center"], "G-code modifiers on imaging claims",
        "Transmittal 12390", 2024,
        f"{base}/chapter-13", "AUC mandate enforcement phased; operational-payment consequences since 2023.",
    ))

    # Ch 14 — MA
    s.append(CMSPub10004Section(
        14, "§ 120", "MA Encounter Data Submission",
        "MA Plan",
        "MA plans must submit encounter data to CMS for every service to a MA enrollee; used for risk-adjustment + benchmark setting.",
        "high", ["MA Plan", "Primary Care (risk-bearing)"], "EDPS encounter records required",
        "Transmittal 12478", 2024,
        f"{base}/chapter-14", "Encounter data quality is RADV-audit-relevant; underreporting risks extrapolated recovery.",
    ))
    s.append(CMSPub10004Section(
        14, "§ 120.3", "Risk-Adjustment Data Validation (RADV) Extrapolation",
        "MA Plan",
        "CMS RADV audits sample contracts' HCC coding; 2023 final rule allows extrapolation of audit findings (program-wide ~$4.7B recovery projected 2024-2032).",
        "high", ["MA Plan"], "Sample → extrapolate → recoup",
        "Transmittal 12501", 2024,
        f"{base}/chapter-14", "Cano/CareMax-pattern deals: model RADV-extrapolation reserve.",
    ))

    # Ch 16 — Lab
    s.append(CMSPub10004Section(
        16, "§ 10", "Clinical Lab Fee Schedule (CLFS) — PAMA",
        "Lab / Pathology",
        "Private-payer-weighted fee schedule under PAMA 2014; applicable labs must report private-payer data.",
        "high", ["Lab / Pathology"], "Private-payer median → CLFS rate",
        "Transmittal 12456", 2024,
        f"{base}/chapter-16", "Labs must report under PAMA; non-reporting triggers exclusion from CLFS.",
    ))

    # Ch 17 — Drugs
    s.append(CMSPub10004Section(
        17, "§ 20.1.3", "Average Sales Price (ASP) — Part B Drug Payment",
        "Oncology / Infusion",
        "Part B drugs paid at ASP + 6% (4% effective post-sequestration); manufacturers must report ASP quarterly.",
        "high", ["Oncology / Infusion", "Specialty Pharmacy"], "ASP + 6% payment methodology",
        "Transmittal 12398", 2024,
        f"{base}/chapter-17", "ASP misreporting by manufacturer creates downstream provider exposure.",
    ))

    # Ch 18 — DME
    s.append(CMSPub10004Section(
        18, "§ 30.5", "DMEPOS Competitive Bidding Program",
        "DME Supplier",
        "DME fee schedule amounts in competitive bidding areas replaced by bid-derived single payment amounts; suppliers must be contract suppliers.",
        "medium", ["DME"], "Single payment amount in CBAs",
        "Transmittal 12301", 2023,
        f"{base}/chapter-18", "DME rollups pre-2019 carry legacy CB exposure (OIG WP-080).",
    ))

    # Ch 23 — Fee schedule
    s.append(CMSPub10004Section(
        23, "§ 30", "Geographic Practice Cost Index (GPCI)",
        "All physician services",
        "GPCI adjusts physician work, PE, and malpractice components by locality (1 of 109 Medicare localities).",
        "medium", ["Physician Group"], "Locality-based GPCI adjustment",
        "Transmittal 12478", 2024,
        f"{base}/chapter-23", "Multi-state rollups must model state-specific GPCI variation.",
    ))

    # Ch 29 — Appeals
    s.append(CMSPub10004Section(
        29, "§ 10", "Claim Appeals — 5 Levels",
        "All claim types",
        "Redetermination (MAC) → Reconsideration (QIC) → ALJ Hearing → Council Review → Judicial Review.",
        "medium", ["All"], "120d → 180d → 60d windows at first 3 levels",
        "Transmittal 12501", 2024,
        f"{base}/chapter-29", "Appeal-win-rate is RCM compliance maturity signal; post-RAC-denial appeal success > 40% = well-run.",
    ))

    # Ch 30 — Financial Liability
    s.append(CMSPub10004Section(
        30, "§ 50", "Advance Beneficiary Notice (ABN)",
        "All claim types",
        "When Medicare may not cover service, provider must deliver ABN in writing with Medicare denial grounds; patient signs acknowledging liability shift.",
        "medium", ["All"], "CMS-R-131 form; GA modifier on claim",
        "Transmittal 12298", 2023,
        f"{base}/chapter-30", "ABN compliance gates patient-liability billing; post-audit unenforceable without.",
    ))

    # Ch 37 — OPPS Claims
    s.append(CMSPub10004Section(
        37, "§ 20.2", "OPPS Packaging + Comprehensive APCs",
        "Outpatient Hospital",
        "CMS packages ancillary services into a single APC payment for comprehensive procedures; status indicators N/Q1/Q2/J1/J2 drive packaging logic.",
        "high", ["Hospital", "HOPD"], "Status indicators determine payment vs packaged",
        "Transmittal 12485", 2024,
        f"{base}/chapter-37", "Comprehensive APC migrations affect year-over-year OPPS revenue; model in deal pro-forma.",
    ))

    return s


# ---------------------------------------------------------------------------
# Per-corpus-deal overlay
# ---------------------------------------------------------------------------

_PROVIDER_KEYWORDS: List[Tuple[str, List[str]]] = [
    ("Hospital", ["hospital", "health system", "medical center", "amc", "ipps", "opps"]),
    ("Home Health", ["home health", "home-health", "aveanna", "amedisys", "encompass home"]),
    ("Hospice", ["hospice"]),
    ("SNF", ["snf", "skilled nursing", "nursing home", "long-term care", "ltc"]),
    ("Physician Group", ["physician", "medical group", "mso ", "primary care",
                          "dermatology", "cardiology", "gastroenter", "urology", "orthoped"]),
    ("Dialysis Provider", ["dialysis", "renal", "davita", "kidney"]),
    ("Lab / Pathology", ["laboratory", "pathology", "reference lab"]),
    ("Radiology / Imaging Center", ["imaging", "radiology", "mri", "rayus", "radnet", "akumin"]),
    ("DME", ["dme", "durable medical", "oxygen", "cpap"]),
    ("Oncology / Infusion", ["oncolog", "cancer", "infusion", "21st century"]),
    ("MA Plan", ["medicare advantage", "ma plan", "ma risk"]),
    ("FQHC / RHC", ["fqhc", "rhc", "rural health"]),
]

_PROVIDER_TO_CHAPTERS: Dict[str, List[int]] = {
    "Hospital":                      [1, 3, 4, 23, 29, 30, 37],
    "Home Health":                   [1, 10, 23, 29, 30],
    "Hospice":                       [1, 11, 23, 29, 30],
    "SNF":                           [1, 6, 7, 23, 29, 30],
    "Physician Group":               [1, 12, 13, 23, 26, 29, 30],
    "Dialysis Provider":             [1, 8, 23, 29, 30],
    "Lab / Pathology":               [1, 16, 23, 29, 30],
    "Radiology / Imaging Center":    [1, 4, 13, 23, 29, 30, 37],
    "DME":                           [1, 18, 20, 23, 29, 30],
    "Oncology / Infusion":           [1, 12, 17, 23, 29, 30],
    "MA Plan":                       [1, 14, 23, 29],
    "FQHC / RHC":                    [1, 9, 23, 29, 30],
}


def _classify_provider(deal: dict) -> str:
    hay = (str(deal.get("deal_name", "")) + " " +
           str(deal.get("notes", ""))).lower()
    for label, kws in _PROVIDER_KEYWORDS:
        for kw in kws:
            if kw in hay:
                return label
    return "Physician Group"


def _score_overlay(deal: dict, sections: List[CMSPub10004Section]) -> Optional[CorpusBillingOverlay]:
    provider = _classify_provider(deal)
    applicable_chapters = _PROVIDER_TO_CHAPTERS.get(provider, [])
    if not applicable_chapters:
        return None

    # Sections applicable to any of the chapters for this provider
    relevant = [s for s in sections if s.chapter_number in applicable_chapters]
    if len(relevant) < 2:
        return None

    high_rel = [s for s in relevant if s.pe_relevance == "high"]
    notable_refs = [f"Ch{s.chapter_number} {s.section_number}" for s in high_rel[:3]]

    if len(high_rel) >= 5:
        tier = "HIGH"
    elif len(high_rel) >= 3:
        tier = "MEDIUM"
    else:
        tier = "LOW"

    summary = (
        f"{provider} — {len(applicable_chapters)} applicable Pub 100-04 chapters "
        f"({len(high_rel)} high-PE-relevance sections). Core mechanics: "
        + ("; ".join(s.key_billing_mechanic for s in high_rel[:3]) or "baseline billing only")
    )

    return CorpusBillingOverlay(
        deal_name=str(deal.get("deal_name", "—"))[:80],
        deal_year=int(deal.get("year") or 0),
        inferred_provider_type=provider,
        applicable_chapter_count=len(applicable_chapters),
        applicable_chapters=applicable_chapters,
        high_relevance_section_count=len(high_rel),
        notable_section_refs=notable_refs,
        exposure_tier=tier,
        diligence_summary=summary[:400],
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compute_claims_processing_manual() -> CMSPub10004Result:
    corpus = _load_corpus()
    sections = _build_sections()
    chapters = _build_chapters(sections)

    overlays: List[CorpusBillingOverlay] = []
    for d in corpus:
        o = _score_overlay(d, sections)
        if o is not None:
            overlays.append(o)
    tier_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    overlays.sort(key=lambda x: (tier_order.get(x.exposure_tier, 9),
                                  -x.high_relevance_section_count))
    overlays = overlays[:60]

    high_rel_sections = sum(1 for s in sections if s.pe_relevance == "high")

    return CMSPub10004Result(
        knowledge_base_version=_KB_VERSION,
        effective_date=_KB_EFFECTIVE_DATE,
        manual_version=_MANUAL_VERSION,
        manual_base_url=_MANUAL_BASE_URL,
        source_citations=_SOURCE_CITATIONS,
        chapters=chapters,
        sections=sections,
        corpus_overlays=overlays,
        total_chapters_documented=len(chapters),
        total_chapters_in_manual=39,
        total_sections=len(sections),
        high_pe_relevance_sections=high_rel_sections,
        corpus_deals_with_overlay=len(overlays),
        corpus_deal_count=len(corpus),
    )
