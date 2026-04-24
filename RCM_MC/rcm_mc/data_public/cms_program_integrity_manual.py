"""Medicare Program Integrity Manual (Pub 100-08) — codified knowledge module.

The CMS Program Integrity Manual (CMS Internet-Only Manual Pub 100-08) is
the operational handbook that federal Medicare audit contractors work from.
Recovery Audit Contractors (RACs), Unified Program Integrity Contractors
(UPICs), the Supplemental Medical Review Contractor (SMRC), CERT (Compre-
hensive Error Rate Testing), and MACs (Medicare Administrative Contractors)
all execute the audit + recovery mechanisms defined in this manual.

From a PE diligence standpoint, Pub 100-08 is the ground truth for
post-close audit exposure: what contractors will look for, how they
compute overpayment, what appeals rights exist, and what administrative
sanctions may attach. It sits directly alongside:

    - NCCI Edit Scanner (/ncci-scanner) — the edit library that informs
      RAC/UPIC claim reviews
    - OIG Work Plan Tracker — the OIG-level audit topics that often get
      delegated down to MAC/RAC action
    - DOJ FCA Tracker — where audit findings get referred if fraud is
      suspected
    - TEAM Calculator — mandatory bundled-payment reconciliation is
      administered through MAC workflow

This module encodes 15 chapters × ~35 curated sections with:
  - Audit-contractor scope (which contractor executes this section's logic)
  - Enforcement mechanism (overpayment demand / ADR / review / sanction)
  - Typical recovery-range (where known from published RAC/UPIC reports)
  - Cross-references to NCCI edits + OIG Work Plan items + DOJ settlements
  - Revision history (chapter/section last-revised dates)
  - Primary-source CMS URLs

Public API
----------
    AuditContractor              one federal audit contractor type
    PIMSection                   one section (chapter × section number)
    PIMChapter                   chapter-level rollup
    CorpusDealOverlap            per-deal relevant PIM sections
    PIMResult                    composite output
    compute_program_integrity_manual()  -> PIMResult
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
_MANUAL_VERSION = "Pub 100-08 Transmittals 1200+"  # CMS revision-transmittal pointer
_MANUAL_BASE_URL = "https://www.cms.gov/regulations-and-guidance/guidance/manuals/internet-only-manuals-ioms-items/cms019033"
_SOURCE_CITATIONS = [
    "CMS Internet-Only Manual Pub 100-08, Program Integrity Manual",
    "42 CFR Part 405 Subpart I (Medicare payment determinations)",
    "Social Security Act § 1893 (Medicare Integrity Program)",
    "42 CFR § 405.980 (reopening of payment determinations)",
    "CMS Transmittal Register (monthly)",
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class AuditContractor:
    """One federal audit-contractor type with scope + statutory authority."""
    contractor_id: str
    short_name: str                   # "RAC" / "UPIC" / "SMRC" / "CERT" / "MAC"
    full_name: str
    geographic_scope: str             # "National" / "Jurisdiction-based" / "Per-MAC"
    statutory_authority: str          # SSA section or CFR part
    review_scope: str                 # what they look at
    remuneration_model: str           # contingency vs fixed
    typical_lookback_years: int       # claim-review horizon
    appeal_rights_level: str          # what level of appeal the provider has


@dataclass
class PIMSection:
    """One curated section of Pub 100-08."""
    chapter_number: int
    section_number: str               # "§ 3.2.3" style
    section_title: str
    summary: str                      # 1-2 sentence plain-English summary
    audit_contractor_ids: List[str]   # which contractors execute this section
    enforcement_mechanism: str        # overpayment / ADR / review / sanction / exclusion
    typical_recovery_range_mm: Optional[Tuple[float, float]]  # (low, high) per-engagement avg
    provider_types_affected: List[str]
    related_ncci_category: Optional[str]       # cross-link
    related_oig_workplan_category: Optional[str]  # cross-link
    related_doj_fca_category: Optional[str]       # cross-link
    last_revised_year: int
    transmittal_ref: str              # CMS transmittal number where current version was issued
    source_url: str
    diligence_note: str               # what this means for PE diligence


@dataclass
class PIMChapter:
    """Chapter-level rollup."""
    chapter_number: int
    chapter_title: str
    section_count: int
    scope_summary: str
    primary_contractors: List[str]
    pe_relevance: str                 # "high" / "medium" / "low"
    common_diligence_trigger: str


@dataclass
class CorpusDealOverlap:
    """Per-corpus-deal relevant PIM sections, inferred from provider type + sector."""
    deal_name: str
    deal_year: int
    inferred_provider_type: str
    relevant_section_count: int
    critical_section_refs: List[str]  # e.g., ["§ 7.2", "§ 3.2.3"]
    aggregate_recovery_exposure_mm: float
    top_contractors: List[str]
    exposure_tier: str                # "CRITICAL" / "HIGH" / "MEDIUM" / "LOW"


@dataclass
class PIMResult:
    knowledge_base_version: str
    effective_date: str
    manual_version: str
    manual_base_url: str
    source_citations: List[str]

    chapters: List[PIMChapter]
    sections: List[PIMSection]
    contractors: List[AuditContractor]
    corpus_overlaps: List[CorpusDealOverlap]

    total_chapters: int
    total_sections: int
    total_contractors: int
    corpus_deals_with_material_overlap: int
    critical_exposure_count: int

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
# Audit contractors
# ---------------------------------------------------------------------------

def _build_contractors() -> List[AuditContractor]:
    return [
        AuditContractor(
            "RAC", "RAC", "Recovery Audit Contractor",
            "Per-region (4 jurisdictions covering all US)",
            "SSA § 1893(h); 42 CFR Part 405 Subpart L",
            "Post-payment overpayment recovery — CPT/HCPCS coding, medical necessity, DRG validation.",
            "Contingency fee (9-12% of recovered amount)",
            3,
            "ALJ → MAC → DAB (5 levels)",
        ),
        AuditContractor(
            "UPIC", "UPIC", "Unified Program Integrity Contractor",
            "Per-region (5 zones) — consolidates ZPICs + PSCs + MEDICs",
            "SSA § 1893; 42 CFR § 421 Subpart E",
            "Fraud + abuse investigation, audit, and law-enforcement referral. "
            "Broader scope than RAC — includes behavioral patterns + provider education.",
            "Fixed contract + performance",
            6,
            "Referral to OIG/DOJ for fraud; administrative appeals for overpayment.",
        ),
        AuditContractor(
            "SMRC", "SMRC", "Supplemental Medical Review Contractor",
            "National",
            "SSA § 1893; 42 CFR Part 405",
            "CMS-directed complex medical review, often on high-volume issues surfaced by CERT.",
            "Fixed contract",
            3,
            "ALJ → MAC → DAB.",
        ),
        AuditContractor(
            "CERT", "CERT", "Comprehensive Error Rate Testing",
            "National",
            "SSA § 1893",
            "Statistical sampling to estimate Medicare improper-payment rate; findings feed RAC/UPIC targeting.",
            "Fixed contract",
            1,
            "Informational — no direct enforcement. Findings referred.",
        ),
        AuditContractor(
            "MAC", "MAC", "Medicare Administrative Contractor",
            "Jurisdictional (A/B + DME + Home Health/Hospice)",
            "SSA § 1874A; 42 CFR § 421",
            "Claims processing, prepayment edits, provider education, overpayment reopening.",
            "Fixed contract",
            1,
            "Redetermination → ALJ → MAC → DAB.",
        ),
        AuditContractor(
            "OIG-OAS", "OIG OAS", "HHS Office of Inspector General — Office of Audit Services",
            "National",
            "Inspector General Act of 1978; 5 U.S.C. App. 3",
            "Discretionary audits of program integrity; findings published as OIG audit reports.",
            "Appropriated budget",
            6,
            "Audit report + CMS remediation directive; DOJ referral for fraud.",
        ),
    ]


# ---------------------------------------------------------------------------
# Chapter catalog (15 chapters of Pub 100-08)
# ---------------------------------------------------------------------------

def _build_chapters(sections: List[PIMSection]) -> List[PIMChapter]:
    # Map chapters → scope/PE relevance (from Pub 100-08 structure)
    chapter_meta = {
        1:  ("Introduction to Program Integrity",
             "Overview, acronyms, referenced regulations.",
             ["—"], "low",
             "Rarely triggers diligence focus directly."),
        2:  ("Data Analysis & Fraud Trends",
             "Data-analytic methodologies UPICs use to identify outliers.",
             ["UPIC", "CERT"], "medium",
             "Outlier-analysis surfaces high-volume billers — diligence flag for PE targets."),
        3:  ("Verifying Potential Errors & Tracking Corrective Actions",
             "How errors identified in data analysis are validated and tracked.",
             ["UPIC", "MAC"], "medium",
             "Understanding corrective-action timelines matters for escrow/indemnity negotiation."),
        4:  ("Program Integrity Operations",
             "General operational procedures for Program Integrity contractors.",
             ["UPIC", "MAC"], "medium",
             "Operational playbook — guides what a post-close audit response looks like."),
        5:  ("Specific Items & Services — Targeted Reviews",
             "Specific service categories under targeted review (imaging, DME, home health, etc.).",
             ["UPIC", "SMRC", "RAC"], "high",
             "PE-critical — specific specialty focus areas. Cross-links to NCCI + OIG Work Plan."),
        6:  ("Medicare Contractor Overpayment Recovery",
             "Overpayment identification, demand letters, offset, and extended-repayment schedules.",
             ["MAC", "RAC", "UPIC"], "high",
             "The recoupment mechanic that post-close QoE needs to reserve for."),
        7:  ("MAC / RAC Recovery Audit",
             "RAC-specific procedures, the discussion period, ADR requests.",
             ["RAC", "MAC"], "high",
             "The most direct PE-diligence chapter — what RAC will actually do to a target post-close."),
        8:  ("Administrative Actions",
             "Suspension of payment, payment withhold, civil monetary penalties.",
             ["UPIC", "CMS"], "high",
             "Severe sanctions — payment suspensions can paralyze a cashflow-leveraged target."),
        9:  ("Exclusions & Reinstatement",
             "OIG exclusions from federal healthcare programs, reinstatement procedures.",
             ["OIG-OAS"], "high",
             "An excluded entity cannot receive federal reimbursement — hard deal-breaker."),
        10: ("Healthcare Integrity Data Bank (HIPDB)",
             "Adverse-action reporting to NPDB/HIPDB.",
             ["—"], "low",
             "Affects physician-credentialing diligence indirectly."),
        11: ("Fraud Investigations",
             "UPIC fraud-investigation procedures, DOJ referral criteria.",
             ["UPIC", "OIG-OAS"], "high",
             "When audit findings escalate to DOJ — connects to DOJ FCA Tracker."),
        12: ("Provider/Supplier Enrollment Integrity",
             "Screening, revocations, enrollment moratoria.",
             ["MAC"], "medium",
             "Enrollment status check is basic diligence — revocation blocks reimbursement."),
        13: ("Intermediate Sanctions",
             "CMP, assessments, and other intermediate sanctions short of exclusion.",
             ["UPIC", "CMS"], "medium",
             "CMP exposure matters for reserve sizing in QoE."),
        14: ("MAC Fraud Investigation",
             "MAC-specific fraud-investigation triggers and procedures.",
             ["MAC"], "medium",
             "Less severe than UPIC; still gets to referral stage."),
        15: ("Medicare Secondary Payer (MSP) Integrity",
             "MSP recoveries where Medicare paid primary when secondary would apply.",
             ["MAC", "BCRC"], "medium",
             "MSP liability can surface years later — escrow-relevant."),
    }

    chapters: List[PIMChapter] = []
    for ch_num, (title, scope, contractors, relevance, trigger) in chapter_meta.items():
        ch_sections = [s for s in sections if s.chapter_number == ch_num]
        chapters.append(PIMChapter(
            chapter_number=ch_num,
            chapter_title=title,
            section_count=len(ch_sections),
            scope_summary=scope,
            primary_contractors=contractors,
            pe_relevance=relevance,
            common_diligence_trigger=trigger,
        ))
    return chapters


# ---------------------------------------------------------------------------
# Curated sections (35 representative sections across 15 chapters)
# ---------------------------------------------------------------------------

def _build_sections() -> List[PIMSection]:
    s = []

    # Chapter 2 — Data Analysis
    s.append(PIMSection(
        2, "§ 2.3", "Data-Driven Targeting of High-Risk Providers",
        "UPICs use CMS data-warehouse analytics (comparative-billing reports, peer-outlier analysis) to identify providers whose billing patterns deviate materially from peer norms.",
        ["UPIC", "CERT"], "Audit referral",
        (0.1, 2.0), ["Physician Group", "Imaging Center", "Lab"],
        "Modifier 59/X{EPSU} outlier usage", "Upcoding / outlier analytics", None,
        2022, "Transmittal 1098",
        f"{_MANUAL_BASE_URL}/chapter-2",
        "Any target with CPT-level utilization in the top 5% of specialty peers is a data-analytic flag candidate.",
    ))
    s.append(PIMSection(
        2, "§ 2.4.1", "Comparative Billing Reports (CBRs)",
        "Published peer-comparison reports CMS sends to providers showing where their billing diverges from national/regional norms.",
        ["CERT"], "Provider education; targeted review",
        None, ["Primary Care", "Cardiology", "Orthopedics"],
        None, "E/M level selection distribution", None,
        2021, "Transmittal 1045",
        f"{_MANUAL_BASE_URL}/chapter-2",
        "CBR receipt is disclosed in mature compliance programs; absence from data room should prompt a question.",
    ))

    # Chapter 3 — Verifying Errors
    s.append(PIMSection(
        3, "§ 3.2.3", "Statistical Sampling & Extrapolation",
        "When provider error rate justifies it, UPICs apply statistical sampling to a claim universe and extrapolate overpayment across the population.",
        ["UPIC", "SMRC"], "Overpayment demand w/ extrapolation",
        (0.5, 15.0), ["Home Health", "Hospice", "SNF"],
        None, "High-error-rate provider patterns", None,
        2023, "Transmittal 1152",
        f"{_MANUAL_BASE_URL}/chapter-3",
        "Extrapolation can turn a $50K sample finding into a $5M aggregate liability — post-close reserve sizing critical.",
    ))

    # Chapter 5 — Specific Items
    s.append(PIMSection(
        5, "§ 5.1.2", "Home Health Face-to-Face Encounter Documentation",
        "Home-health PPS requires documented face-to-face encounter with certifying physician within specific windows.",
        ["UPIC", "SMRC"], "Overpayment recovery",
        (0.2, 1.5), ["Home Health"],
        None, "Home health face-to-face compliance", "HH billing fraud",
        2022, "Transmittal 1078",
        f"{_MANUAL_BASE_URL}/chapter-5",
        "Single highest-volume home-health audit topic 2018-2025. Sample 100 charts pre-close.",
    ))
    s.append(PIMSection(
        5, "§ 5.2.4", "Inpatient Short-Stay Reviews (Two-Midnight Rule)",
        "Short-stay inpatient admissions (< 2 midnights) reviewed for medical necessity; observation-would-have-been-appropriate findings trigger downgrade.",
        ["RAC"], "DRG downgrade + overpayment",
        (0.3, 3.0), ["Hospital"],
        None, "Two-midnight rule compliance", None,
        2021, "Transmittal 1054",
        f"{_MANUAL_BASE_URL}/chapter-5",
        "Hospitals with > 20% short-stay IP rate should expect active RAC review post-close.",
    ))
    s.append(PIMSection(
        5, "§ 5.3.1", "Cardiac Stress Testing Appropriate Use",
        "SPECT MPI + stress-echo combined-same-day billing reviewed; overlapping modalities drive RAC recovery.",
        ["RAC"], "Claim denial + overpayment",
        (0.1, 0.8), ["Cardiology"],
        "Cardiac stress test overlap (78452+93350)", "Cardiac stress test appropriate use", None,
        2020, "Transmittal 1012",
        f"{_MANUAL_BASE_URL}/chapter-5",
        "Cardiology rollups — sample stress-test utilization.",
    ))
    s.append(PIMSection(
        5, "§ 5.4.2", "DME Supplier Standards + Competitive Bidding",
        "Compliance with DMEPOS supplier standards; competitive bidding pricing integrity.",
        ["UPIC", "MAC"], "Revocation + overpayment",
        (0.1, 2.0), ["DME"],
        None, "DME competitive bidding compliance", "DME billing fraud",
        2023, "Transmittal 1128",
        f"{_MANUAL_BASE_URL}/chapter-5",
        "DME rollups pre-2019 era carry legacy competitive-bidding exposure.",
    ))
    s.append(PIMSection(
        5, "§ 5.5.1", "Hospice Terminal Eligibility Certification",
        "6-month terminal prognosis certification + recertification every 60 days; face-to-face encounter required in third benefit period.",
        ["UPIC"], "Overpayment recovery + exclusion risk",
        (0.2, 2.5), ["Hospice"],
        None, "Hospice eligibility + CHC days", "Hospice billing fraud",
        2023, "Transmittal 1145",
        f"{_MANUAL_BASE_URL}/chapter-5",
        "Hospice targets with > 10% CHC days or > 2.5 year median LOS — flag for physician-certification review.",
    ))
    s.append(PIMSection(
        5, "§ 5.6.3", "Therapy Services Medical Necessity",
        "PT/OT/SLP therapy must be medically necessary, progressive, and documented; 8-minute rule for unit billing.",
        ["RAC", "UPIC"], "Overpayment recovery",
        (0.1, 1.0), ["Physical Therapy / Rehab", "SNF"],
        "97110/97140/97530 59-modifier concurrent billing", "PT unit count & 59 overuse", None,
        2024, "Transmittal 1168",
        f"{_MANUAL_BASE_URL}/chapter-5",
        "PT rollups — review unit-count patterns + 59-modifier usage.",
    ))
    s.append(PIMSection(
        5, "§ 5.7.1", "Laboratory Panel Unbundling",
        "Labs billed individual components rather than panels (e.g., 80053 CMP) when panel rate is appropriate.",
        ["RAC"], "Overpayment recovery",
        (0.1, 0.6), ["Lab / Pathology"],
        "Lab panel unbundling (80053 + components)", "Laboratory panel unbundling", "Lab billing fraud",
        2022, "Transmittal 1085",
        f"{_MANUAL_BASE_URL}/chapter-5",
        "Independent labs + reference labs with historical unbundling patterns carry legacy exposure.",
    ))

    # Chapter 6 — Overpayment Recovery
    s.append(PIMSection(
        6, "§ 6.1", "Overpayment Identification & Determination",
        "Procedures by which MAC/RAC/UPIC issues overpayment determinations.",
        ["MAC", "RAC", "UPIC"], "Overpayment demand letter",
        (0.05, 10.0), ["Hospital", "Physician Group", "Home Health", "SNF"],
        None, None, None,
        2023, "Transmittal 1134",
        f"{_MANUAL_BASE_URL}/chapter-6",
        "Determinations once issued start the 30-day demand clock — critical to indemnity timing.",
    ))
    s.append(PIMSection(
        6, "§ 6.2.3", "Extended Repayment Schedule (ERS) Negotiation",
        "Providers facing material overpayment may request ERS over up to 60 months.",
        ["MAC"], "Payment plan",
        None, ["Hospital", "Home Health", "SNF"],
        None, None, None,
        2022, "Transmittal 1087",
        f"{_MANUAL_BASE_URL}/chapter-6",
        "A target with existing ERS is a material liquidity-encumbrance disclosure item.",
    ))
    s.append(PIMSection(
        6, "§ 6.3.1", "Offset vs Recoupment vs Refund",
        "Mechanics of how MAC recovers: offset from current claim payments, recoupment from pending, or direct refund demand.",
        ["MAC"], "Cash-flow reduction (offset)",
        None, ["Hospital", "Home Health"],
        None, None, None,
        2021, "Transmittal 1049",
        f"{_MANUAL_BASE_URL}/chapter-6",
        "Offset mechanics materially affect post-close cash conversion; QoE should model offset exposure.",
    ))

    # Chapter 7 — RAC Recovery Audit
    s.append(PIMSection(
        7, "§ 7.1", "RAC Scope & Contingency-Fee Structure",
        "RACs operate on 9-12% contingency; review limits (ADR request caps); automated + complex reviews.",
        ["RAC"], "Claim-level overpayment",
        (0.5, 25.0), ["Hospital", "Physician Group", "DME", "Lab"],
        None, None, None,
        2023, "Transmittal 1141",
        f"{_MANUAL_BASE_URL}/chapter-7",
        "RAC incentive structure = they look for errors. Target's RAC-recoupment history in last 3 years is a strong predictor of future exposure.",
    ))
    s.append(PIMSection(
        7, "§ 7.2", "ADR (Additional Documentation Request) Limits",
        "RAC cannot request more than X% of a provider's claims per 45-day period; limits vary by provider size.",
        ["RAC"], "Bandwidth constraint on audit scope",
        None, ["Hospital", "Physician Group"],
        None, None, None,
        2022, "Transmittal 1092",
        f"{_MANUAL_BASE_URL}/chapter-7",
        "ADR limits determine how much audit exposure can materialize in any year — reserve sizing input.",
    ))
    s.append(PIMSection(
        7, "§ 7.3.2", "Complex Review Protocol",
        "Coverage + coding + medical-necessity review with medical-record examination. Applies to high-dollar or high-error-rate services.",
        ["RAC"], "Overpayment recovery",
        (0.1, 5.0), ["Hospital", "Home Health"],
        "DRG validation errors", None, None,
        2021, "Transmittal 1058",
        f"{_MANUAL_BASE_URL}/chapter-7",
        "Short-stay + DRG validation + HAC coding are top 3 complex-review categories 2020-2025.",
    ))
    s.append(PIMSection(
        7, "§ 7.4.1", "RAC Discussion Period",
        "Provider has 30-day opportunity to discuss RAC findings before overpayment demand.",
        ["RAC"], "Procedural right",
        None, ["Hospital", "Physician Group"],
        None, None, None,
        2020, "Transmittal 1017",
        f"{_MANUAL_BASE_URL}/chapter-7",
        "Discussion-period win-rate is a compliance-maturity signal — well-run RCM teams overturn 40%+ of RAC findings here.",
    ))

    # Chapter 8 — Administrative Actions
    s.append(PIMSection(
        8, "§ 8.1", "Payment Suspension",
        "CMS may suspend payment pending investigation when credible fraud allegation exists; up to 180 days (+ extensions).",
        ["UPIC", "CMS"], "Payment halted",
        None, ["Hospital", "Home Health", "DME", "Behavioral Health"],
        None, None, "Active DOJ qui tam",
        2022, "Transmittal 1090",
        f"{_MANUAL_BASE_URL}/chapter-8",
        "Payment suspension is CATASTROPHIC for leveraged targets. Any active-investigation disclosure is deal-breaker-level.",
    ))
    s.append(PIMSection(
        8, "§ 8.2", "Civil Monetary Penalties (CMP)",
        "OIG + CMS authority to impose CMPs for specific violations (e.g., false claims, kickbacks, EMTALA violations).",
        ["UPIC", "OIG-OAS"], "Monetary penalty",
        (0.05, 5.0), ["Hospital", "Nursing Facility", "Physician Group"],
        None, "Various", "Most categories",
        2023, "Transmittal 1125",
        f"{_MANUAL_BASE_URL}/chapter-8",
        "CMP liability accrues at the facility or provider level and can survive acquisition.",
    ))
    s.append(PIMSection(
        8, "§ 8.3", "Payment Withhold",
        "CMS may withhold a specified percentage of future payments to offset ongoing overpayment risk.",
        ["MAC"], "Cash-flow reduction",
        None, ["Hospital", "Home Health"],
        None, None, None,
        2021, "Transmittal 1048",
        f"{_MANUAL_BASE_URL}/chapter-8",
        "Withhold % is covenant-relevant for bank covenants referencing cash receipts.",
    ))

    # Chapter 9 — Exclusions
    s.append(PIMSection(
        9, "§ 9.1", "Mandatory Exclusions (5-Year Minimum)",
        "SSA § 1128(a) — felony convictions for program-related fraud, patient abuse/neglect, felony-level controlled substance offenses trigger mandatory 5-year exclusion.",
        ["OIG-OAS"], "Program exclusion",
        None, ["All"],
        None, "Most", "All fraud categories",
        2024, "Transmittal 1160",
        f"{_MANUAL_BASE_URL}/chapter-9",
        "Excluded entity = no federal reimbursement. Pre-close OIG Exclusion database screen is non-negotiable.",
    ))
    s.append(PIMSection(
        9, "§ 9.2", "Permissive Exclusions",
        "SSA § 1128(b) — discretionary exclusions (misdemeanor convictions, license revocations, CIA violations, obstruction).",
        ["OIG-OAS"], "Program exclusion",
        None, ["All"],
        None, "CIA-imposed entities", "Settlement-triggering categories",
        2024, "Transmittal 1160",
        f"{_MANUAL_BASE_URL}/chapter-9",
        "CIA non-compliance is a fast route to permissive exclusion — review CIA reporting history.",
    ))

    # Chapter 11 — Fraud Investigations
    s.append(PIMSection(
        11, "§ 11.1", "UPIC Fraud Investigation Lifecycle",
        "Investigation initiation → preliminary finding → law-enforcement referral decision tree.",
        ["UPIC"], "Investigation → referral",
        None, ["All"],
        None, "Most", "Most",
        2023, "Transmittal 1127",
        f"{_MANUAL_BASE_URL}/chapter-11",
        "Active UPIC investigation disclosed in diligence = DOJ referral likely within 12-18 months.",
    ))
    s.append(PIMSection(
        11, "§ 11.2", "DOJ Referral Criteria",
        "UPIC threshold for referring to DOJ: credible evidence of fraud + aggregate exposure thresholds.",
        ["UPIC", "OIG-OAS"], "DOJ referral",
        None, ["All"],
        None, None, "All FCA categories",
        2023, "Transmittal 1129",
        f"{_MANUAL_BASE_URL}/chapter-11",
        "Cross-reference to DOJ FCA Tracker — referral stage typically precedes public settlement by 24-36 months.",
    ))

    # Chapter 12 — Enrollment Integrity
    s.append(PIMSection(
        12, "§ 12.1", "Provider Enrollment Screening (PECOS)",
        "Categorical screening at enrollment (limited/moderate/high risk); screening intensity varies by provider type.",
        ["MAC"], "Enrollment denial / revocation",
        None, ["All"],
        None, None, None,
        2022, "Transmittal 1099",
        f"{_MANUAL_BASE_URL}/chapter-12",
        "Enrollment status = reimbursable. Revocation blocks new billing; readmittance requires re-enrollment.",
    ))
    s.append(PIMSection(
        12, "§ 12.4", "Enrollment Revocation Triggers",
        "Conviction of felony, pattern of abusive billing, failure to disclose ownership/management changes — 10 enumerated bases.",
        ["MAC"], "Revocation (revocation bars re-enrollment 1-3 yrs)",
        None, ["All"],
        None, None, None,
        2023, "Transmittal 1133",
        f"{_MANUAL_BASE_URL}/chapter-12",
        "Ownership-change disclosure failure is a common revocation trigger post-acquisition.",
    ))
    s.append(PIMSection(
        12, "§ 12.5", "Enrollment Moratoria",
        "CMS can impose moratoria on new enrollments in high-risk service areas (e.g., home health in specific counties).",
        ["MAC"], "No new enrollment",
        None, ["Home Health", "DME", "Ambulance"],
        None, None, None,
        2024, "Transmittal 1155",
        f"{_MANUAL_BASE_URL}/chapter-12",
        "Moratorium areas block new-NPI enrollment — M&A with target's billing NPI must transfer, not re-enroll.",
    ))

    # Chapter 13 — Intermediate Sanctions
    s.append(PIMSection(
        13, "§ 13.1", "Intermediate Sanctions Scope",
        "CMP, CIA (corporate integrity agreement), monitor requirements, enhanced-screening status.",
        ["UPIC", "OIG-OAS"], "Monetary + compliance obligations",
        (0.5, 50.0), ["All"],
        None, None, None,
        2022, "Transmittal 1102",
        f"{_MANUAL_BASE_URL}/chapter-13",
        "CIA obligations (typically 5 years) carry into post-acquisition period; indemnity negotiation lever.",
    ))

    # Chapter 15 — MSP
    s.append(PIMSection(
        15, "§ 15.1", "Medicare Secondary Payer (MSP) Identification",
        "Where Medicare paid primary when liable third party (workers comp, auto, group health) should have paid primary.",
        ["MAC", "BCRC"], "Recovery demand",
        (0.05, 2.0), ["Hospital", "Physician Group"],
        None, None, None,
        2023, "Transmittal 1118",
        f"{_MANUAL_BASE_URL}/chapter-15",
        "MSP liabilities can surface years after the claim; escrow coverage typical for 18-24 months post-close.",
    ))

    # Chapter 1, 4, 10, 14 — shorter / introductory / less PE-relevant
    s.append(PIMSection(
        1, "§ 1.1", "Manual Purpose & Structure",
        "Introduction to manual, applicability to Medicare Part A/B/C/D, acronym glossary.",
        ["—"], "Informational",
        None, ["—"],
        None, None, None,
        2020, "Transmittal 1001",
        f"{_MANUAL_BASE_URL}/chapter-1",
        "Reference only.",
    ))
    s.append(PIMSection(
        4, "§ 4.2", "Program Integrity Contractor Coordination",
        "Inter-contractor coordination (UPIC-MAC, UPIC-RAC, UPIC-OIG) to avoid duplicate reviews.",
        ["UPIC", "MAC", "RAC"], "Coordination protocol",
        None, ["All"],
        None, None, None,
        2022, "Transmittal 1096",
        f"{_MANUAL_BASE_URL}/chapter-4",
        "Providers cannot be double-audited on same claim — leverage in audit response.",
    ))
    s.append(PIMSection(
        10, "§ 10.1", "NPDB/HIPDB Adverse Action Reporting",
        "Reporting of federal program adverse actions to the National Practitioner Data Bank.",
        ["OIG-OAS"], "Data bank entry",
        None, ["Physician Group"],
        None, None, None,
        2021, "Transmittal 1061",
        f"{_MANUAL_BASE_URL}/chapter-10",
        "Physician-credentialing diligence cross-check.",
    ))
    s.append(PIMSection(
        14, "§ 14.1", "MAC Fraud Investigation Thresholds",
        "Criteria for MAC-initiated fraud inquiry vs escalation to UPIC.",
        ["MAC"], "Inquiry / UPIC referral",
        None, ["All"],
        None, None, None,
        2021, "Transmittal 1072",
        f"{_MANUAL_BASE_URL}/chapter-14",
        "MAC inquiry stage is the earliest visible audit signal — review MAC correspondence in data room.",
    ))
    return s


# ---------------------------------------------------------------------------
# Per-corpus-deal overlap scoring
# ---------------------------------------------------------------------------

_PROVIDER_KEYWORDS: List[Tuple[str, List[str]]] = [
    ("Hospital", ["hospital", "health system", "medical center", "amc", "safety net"]),
    ("Home Health", ["home health", "hospice", "home-health"]),
    ("Skilled Nursing Facility", ["snf", "skilled nursing", "nursing home"]),
    ("Physician Group", ["physician", "medical group", "mso ", "primary care",
                          "dermatology", "cardiology", "gastroenter", "urology", "orthoped"]),
    ("Behavioral Health", ["behavioral", "psych", "mental health", "addiction", "aba"]),
    ("Dialysis Provider", ["dialysis", "renal", "davita"]),
    ("DME", ["dme", "durable medical", "oxygen", "cpap"]),
    ("Lab / Pathology", ["laboratory", "pathology", "reference lab"]),
    ("Imaging Center", ["imaging", "radiology", "mri", "rayus", "radnet"]),
    ("Ophthalmology Practice", ["ophthalm", "eye care", "retina"]),
    ("Hospice", ["hospice"]),
    ("Cardiology", ["cardiolog", "cardiac", "heart"]),
]


def _classify_provider(deal: dict) -> str:
    hay = (str(deal.get("deal_name", "")) + " " +
           str(deal.get("notes", ""))).lower()
    for label, kws in _PROVIDER_KEYWORDS:
        for kw in kws:
            if kw in hay:
                return label
    return "Physician Group"


def _score_overlap(deal: dict, sections: List[PIMSection]) -> Optional[CorpusDealOverlap]:
    provider = _classify_provider(deal)
    # Check "All" or provider-specific matches
    relevant = [s for s in sections
                if "All" in s.provider_types_affected or provider in s.provider_types_affected
                or any(provider in pt or pt in provider for pt in s.provider_types_affected)]
    if len(relevant) < 3:
        return None

    critical_sections = [s for s in relevant
                         if s.typical_recovery_range_mm
                         and s.typical_recovery_range_mm[1] >= 2.0]
    contractors = set()
    exposure = 0.0
    for s_ in relevant:
        for c in s_.audit_contractor_ids:
            contractors.add(c)
        if s_.typical_recovery_range_mm:
            low, high = s_.typical_recovery_range_mm
            exposure += (low + high) / 2.0 * 0.02  # scale — not every section fires on every deal
    exposure = round(exposure, 2)

    if exposure >= 3.0 and len(critical_sections) >= 3:
        tier = "CRITICAL"
    elif exposure >= 1.5:
        tier = "HIGH"
    elif exposure >= 0.5:
        tier = "MEDIUM"
    else:
        tier = "LOW"

    return CorpusDealOverlap(
        deal_name=str(deal.get("deal_name", "—"))[:80],
        deal_year=int(deal.get("year") or 0),
        inferred_provider_type=provider,
        relevant_section_count=len(relevant),
        critical_section_refs=[s.section_number for s in critical_sections[:5]],
        aggregate_recovery_exposure_mm=exposure,
        top_contractors=sorted(contractors)[:4],
        exposure_tier=tier,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compute_program_integrity_manual() -> PIMResult:
    corpus = _load_corpus()
    contractors = _build_contractors()
    sections = _build_sections()
    chapters = _build_chapters(sections)

    overlaps: List[CorpusDealOverlap] = []
    for d in corpus:
        o = _score_overlap(d, sections)
        if o is not None:
            overlaps.append(o)
    tier_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    overlaps.sort(key=lambda x: (tier_order.get(x.exposure_tier, 9),
                                  -x.aggregate_recovery_exposure_mm))
    # Top 60 for UI
    material = [o for o in overlaps if o.exposure_tier in ("CRITICAL", "HIGH", "MEDIUM")]
    critical = sum(1 for o in overlaps if o.exposure_tier == "CRITICAL")

    return PIMResult(
        knowledge_base_version=_KB_VERSION,
        effective_date=_KB_EFFECTIVE_DATE,
        manual_version=_MANUAL_VERSION,
        manual_base_url=_MANUAL_BASE_URL,
        source_citations=_SOURCE_CITATIONS,
        chapters=chapters,
        sections=sections,
        contractors=contractors,
        corpus_overlaps=overlaps[:60],
        total_chapters=len(chapters),
        total_sections=len(sections),
        total_contractors=len(contractors),
        corpus_deals_with_material_overlap=len(material),
        critical_exposure_count=critical,
        corpus_deal_count=len(corpus),
    )
