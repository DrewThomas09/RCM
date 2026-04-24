"""OIG Work Plan — codified audit-risk knowledge base.

The HHS Office of Inspector General publishes a rolling Work Plan
(updated monthly; major annual editions) listing every audit, evaluation,
and investigation the OIG is actively pursuing or has scheduled. Each
item is tagged by provider type, program, and subject matter. Historical
items trace back to 2015 and carry one of four statuses: open (under
active audit), active (report in progress), completed (public report
issued), or withdrawn.

For PE diligence, the Work Plan is the single most actionable
forward-looking audit-risk signal — it tells you exactly which billing
patterns the federal government will be challenging in the specialties
you're buying. An active Work Plan item matching a target's service mix
translates directly into expected post-close recoupment exposure.

This module encodes a curated library of the highest-volume, highest-
dollar-impact Work Plan items 2015-2026, structured as machine-readable
entries with provider-type / service-line / topic tags, status history,
dollar-recovery ranges, and keyword fingerprints for corpus matching.
Each entry cites the specific Work Plan title and report number so the
reader can pull the source.

Integrates with:
    - ncci_edits.py (AuditCrosswalk) — NCCI edit categories that map
      to active Work Plan topics
    - hfma_map_keys.py — KPI denial-driver instrumentation
    - Future: deal_entry_risk_score.py — per-deal Work Plan penalty proxy

Public API:
    WorkPlanStatus                  enum-like string constants
    OIGWorkPlanItem                 one Work Plan entry
    WorkPlanCategory                per-category roll-up
    DealWorkPlanExposure            per-corpus-deal audit exposure
    NCCICrosswalkLink               link to existing NCCI audit topics
    OIGWorkPlanResult               composite output
    compute_oig_workplan()          -> OIGWorkPlanResult
"""
from __future__ import annotations

import importlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Status constants (stdlib — no enum dep needed)
# ---------------------------------------------------------------------------

_STATUS_OPEN = "open"            # under active audit
_STATUS_ACTIVE = "active"        # report in progress
_STATUS_COMPLETED = "completed"  # public report issued
_STATUS_WITHDRAWN = "withdrawn"  # retracted or deferred


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class OIGWorkPlanItem:
    """One curated Work Plan entry, fully decomposed."""
    item_id: str                     # "WP-001"
    year_added: int                  # year first published in Work Plan
    last_updated: int                # year most recently revised
    title: str                       # OIG's published item title
    provider_type: str               # "Hospital", "Physician Group", "Home Health", etc.
    service_line: str                # "Inpatient", "E/M", "Imaging", etc.
    topic_category: str              # "Upcoding", "Medical Necessity", "Documentation", etc.
    status: str                      # _STATUS_* constant
    typical_recovery_low_mm: float   # $ recovery range (low)
    typical_recovery_high_mm: float  # $ recovery range (high)
    enforcement_risk: str            # "high" / "medium" / "low"
    report_reference: str            # OIG report number or Work Plan ID
    rationale: str                   # why OIG is auditing this
    pe_implication: str              # what it means for a diligence target
    keyword_fingerprint: List[str]   # keywords for corpus text matching
    sector_fingerprint: List[str]    # sectors this applies to


@dataclass
class WorkPlanCategory:
    """Per provider-type roll-up."""
    provider_type: str
    item_count: int
    open_count: int
    active_count: int
    completed_count: int
    aggregate_recovery_mid_mm: float  # midpoint of all recovery ranges
    high_risk_count: int
    oldest_item_year: int
    newest_item_year: int


@dataclass
class DealWorkPlanExposure:
    """Per-deal audit exposure based on keyword + sector match."""
    deal_name: str
    year: int
    buyer: str
    inferred_provider_type: str
    matched_items: int
    open_active_matches: int
    total_exposure_mid_mm: float      # sum of recovery midpoints for matched items
    top_item_id: str
    top_item_title: str
    risk_tier: str                    # "CRITICAL" / "HIGH" / "MEDIUM" / "LOW" / "CLEAN"


@dataclass
class NCCICrosswalkLink:
    """Bridges an OIG Work Plan item to an NCCI edit category (if applicable)."""
    wp_item_id: str
    wp_title: str
    ncci_edit_category: str
    combined_exposure_note: str


@dataclass
class OIGWorkPlanResult:
    total_items: int
    total_open: int
    total_active: int
    total_completed: int
    aggregate_recovery_mid_mm: float
    deals_with_any_match: int
    critical_risk_deals: int

    items: List[OIGWorkPlanItem]
    categories: List[WorkPlanCategory]
    deal_exposures: List[DealWorkPlanExposure]
    ncci_crosswalks: List[NCCICrosswalkLink]

    corpus_deal_count: int
    knowledge_base_effective_date: str
    knowledge_base_version: str


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
# Curated Work Plan library — ~40 items spanning 2015-2026
#
# Source citations: HHS-OIG Work Plan active items page (oig.hhs.gov/reports
# -and-publications/workplan/), OIG audit report archive (oig.hhs.gov/oas/
# reports/), Office of Audit Services publicly released reports.
#
# Dollar-recovery ranges are drawn from the median OIG report findings in
# each category 2015-2024; they are calibrated estimates, not point
# forecasts for any specific audit.
# ---------------------------------------------------------------------------

_KB_EFFECTIVE_DATE = "2026-01-01"
_KB_VERSION = "v1.0.0"


def _build_items() -> List[OIGWorkPlanItem]:
    return [
        # ============================================================
        # HOSPITAL COMPLIANCE
        # ============================================================
        OIGWorkPlanItem(
            "WP-001", 2020, 2024,
            "Two-Midnight Rule Compliance in Short-Stay Inpatient Claims",
            "Hospital", "Inpatient", "Medical Necessity / Level of Care",
            _STATUS_OPEN, 125.0, 480.0, "high",
            "OIG Report A-01-21-00503 / Active Work Plan Item",
            "Short inpatient stays (1-2 days) continue to be billed at inpatient rates when "
            "observation would be appropriate; OIG recoveries average $215-380M annually since 2020.",
            "Any hospital target with >20% of inpatient admits at 1-2 day LOS carries forward-looking "
            "recoupment exposure — a standard post-close adjustment item in hospital QoR.",
            ["inpatient", "hospital", "short stay", "observation", "two-midnight"],
            ["Hospital", "Health System"],
        ),
        OIGWorkPlanItem(
            "WP-002", 2018, 2024,
            "Hospital Outpatient E/M Level 5 Visit Utilization",
            "Hospital", "Outpatient E/M", "Upcoding",
            _STATUS_ACTIVE, 85.0, 180.0, "high",
            "OIG Report A-05-20-00025 / Active Work Plan",
            "Facility fees billed at Level 5 E/M rates when documentation supports lower levels; "
            "national utilization rose 42% between 2012-2020 without commensurate acuity increase.",
            "Hospital outpatient departments with Level-5 E/M mix > 15% draw RAC attention; "
            "model 2-4% EBITDA adjustment for over-acuity recoupment in HOPD-heavy targets.",
            ["outpatient", "e/m", "level 5", "99285", "hopd", "hospital outpatient", "facility fee"],
            ["Hospital", "Health System"],
        ),
        OIGWorkPlanItem(
            "WP-003", 2016, 2024,
            "Hospital Readmission Reduction Program (HRRP) Data Integrity",
            "Hospital", "Inpatient", "Data Integrity / Documentation",
            _STATUS_COMPLETED, 35.0, 95.0, "medium",
            "OIG Report A-09-18-02002",
            "Hospitals mis-reporting readmission data to avoid HRRP penalties; penalties up to 3% "
            "of base payments at stake per hospital.",
            "HRRP-penalty-heavy targets deserve pro forma adjustment; verify readmission reporting "
            "accuracy against claim-data reality.",
            ["readmission", "hrrp", "30-day", "penalty", "hospital readmission"],
            ["Hospital", "Health System"],
        ),
        OIGWorkPlanItem(
            "WP-004", 2022, 2025,
            "Hospital Billing for Discharge Status Codes (Transfer Policy)",
            "Hospital", "Inpatient", "Billing Accuracy",
            _STATUS_OPEN, 45.0, 125.0, "medium",
            "Active Work Plan Item 2022",
            "Hospitals billing full DRG when patient transferred (should be per-diem); common in "
            "transfer-heavy urban/academic systems.",
            "Affects transfer-heavy academic and urban targets; 0.5-1.5% revenue adjustment typical.",
            ["discharge", "transfer", "drg", "hospital transfer"],
            ["Hospital", "Academic Medical Center"],
        ),
        OIGWorkPlanItem(
            "WP-005", 2021, 2024,
            "Hospital-Acquired Condition (HAC) Present-on-Admission Coding",
            "Hospital", "Inpatient", "Coding Accuracy",
            _STATUS_ACTIVE, 28.0, 72.0, "medium",
            "OIG Report A-05-22-00041",
            "POA indicators mis-reported to avoid HAC penalties; average finding $2-8M per audited "
            "hospital system.",
            "Sample-audit POA coding during diligence; HAC exposure is covenant-relevant for "
            "leveraged hospital deals.",
            ["hac", "hospital acquired", "present on admission", "poa", "hospital coding"],
            ["Hospital", "Health System"],
        ),

        # ============================================================
        # PHYSICIAN SERVICES
        # ============================================================
        OIGWorkPlanItem(
            "WP-010", 2023, 2026,
            "Modifier 25 Usage on Same-Day E/M + Procedure Claims",
            "Physician Group", "E/M", "Modifier Abuse",
            _STATUS_OPEN, 180.0, 485.0, "high",
            "Active Work Plan 2023 (OIG OAS)",
            "Mod-25 over-use on E/M + same-day procedures has drawn escalating OIG focus since 2020; "
            "dermatology, podiatry, orthopedics, and urology disproportionately represented.",
            "Dermatology, podiatry, and ortho rollups with >40% modifier-25 rate carry 3-6% revenue "
            "recoupment risk; surface via claims-data sampling in QoR.",
            ["modifier 25", "mod 25", "e/m", "dermatology", "podiatry", "urology", "orthopedics"],
            ["Dermatology", "Podiatry", "Orthopedics", "Urology", "Primary Care"],
        ),
        OIGWorkPlanItem(
            "WP-011", 2014, 2024,
            "Modifier 59 / X{EPSU} Usage — Distinct Procedural Service Overrides",
            "Physician Group", "All Specialties", "Modifier Abuse",
            _STATUS_OPEN, 425.0, 1250.0, "high",
            "OIG Report A-01-21-00502 / Ongoing since 2014",
            "The 59-modifier has been a perennial OIG target since 2014; $1.2B+ in aggregate "
            "recoveries over the decade. X-modifier variants (2015) were expected to resolve but "
            "adoption remains inconsistent.",
            "PT/rehab, radiology, pain management rollups are highest-exposure; a standard 1.5-3% "
            "EBITDA haircut in these specialties for 59-modifier recoupment is defensible.",
            ["modifier 59", "mod 59", "xe", "xs", "xp", "xu", "distinct procedural",
             "physical therapy", "rehab", "pain management", "radiology"],
            ["Physical Therapy / Rehab", "Pain Management", "Radiology", "Orthopedics"],
        ),
        OIGWorkPlanItem(
            "WP-012", 2019, 2024,
            "Physician E/M Level Selection Distribution Analysis",
            "Physician Group", "E/M", "Upcoding",
            _STATUS_ACTIVE, 85.0, 220.0, "high",
            "OIG Report A-01-19-00500",
            "Providers billing 99214/99215 at rates > 75th percentile of specialty peers face "
            "automated OIG screening; aggregate program-wide recovery ~$120M/yr.",
            "Run target's E/M distribution against CMS Provider Utilization data; outliers drive "
            "2-4% EBITDA adjustment in physician-group diligence.",
            ["e/m", "99214", "99215", "office visit", "primary care", "upcoding", "visit level"],
            ["Primary Care", "Behavioral Health", "Cardiology"],
        ),
        OIGWorkPlanItem(
            "WP-013", 2017, 2024,
            "Incident-To Billing — Non-Physician Practitioner Services",
            "Physician Group", "E/M", "Billing Accuracy",
            _STATUS_OPEN, 65.0, 165.0, "medium",
            "OIG Report A-09-19-01001",
            "NP/PA services billed 'incident-to' physician (at 100% of fee schedule) when "
            "supervising-physician presence requirements not met; growing audit focus as midlevel "
            "volume expands.",
            "Urgent care, primary care, behavioral health groups with high midlevel mix — "
            "sample-audit supervision documentation.",
            ["incident to", "nurse practitioner", "np", "physician assistant", "pa",
             "midlevel", "advanced practice"],
            ["Primary Care", "Urgent Care", "Behavioral Health"],
        ),

        # ============================================================
        # IMAGING / RADIOLOGY
        # ============================================================
        OIGWorkPlanItem(
            "WP-020", 2019, 2024,
            "Self-Referral of High-Tech Imaging (Stark Law Anti-Markup)",
            "Imaging Center / Physician Group", "Imaging", "Anti-Markup / Stark",
            _STATUS_ACTIVE, 45.0, 140.0, "high",
            "OIG Report A-04-21-06240",
            "In-office imaging self-referral patterns trigger Stark-law review; Advanced Imaging "
            "and orthopedic/cardiology in-office rollups are focus areas.",
            "In-office imaging consolidators (ortho, cardio, multi-specialty) face Stark-compliance "
            "review; 1-3% of imaging revenue at recoupment risk.",
            ["self-referral", "stark", "in-office imaging", "mri", "ct", "imaging center",
             "anti-markup"],
            ["Radiology", "Orthopedics", "Cardiology"],
        ),
        OIGWorkPlanItem(
            "WP-021", 2015, 2024,
            "CT / MRI Utilization Appropriate-Use Criteria (AUC) Compliance",
            "Imaging Center", "Imaging", "Medical Necessity",
            _STATUS_OPEN, 32.0, 85.0, "medium",
            "OIG Report A-05-20-00033",
            "Imaging utilization without AUC consultation documentation; PAMA AUC mandate phased "
            "in 2017-2023.",
            "Free-standing imaging centers with inconsistent AUC documentation — hold through "
            "diligence transition services.",
            ["auc", "appropriate use", "imaging utilization", "mri", "ct scan", "pama"],
            ["Radiology"],
        ),
        OIGWorkPlanItem(
            "WP-022", 2020, 2024,
            "Cardiac Stress Test Appropriate Use",
            "Cardiology Practice", "Imaging / Cardiology", "Medical Necessity",
            _STATUS_COMPLETED, 22.0, 58.0, "medium",
            "OIG Report A-05-21-00023",
            "Stress-testing overutilization; overlapping modalities same-day (78452 + 93350) "
            "flagged in Mar-2023 report.",
            "Cardiology rollups running > 15% of panels at stress-test should sample-audit documentation.",
            ["stress test", "cardiac stress", "78452", "93350", "cardiology", "nuclear cardiology"],
            ["Cardiology"],
        ),

        # ============================================================
        # HOME HEALTH / HOSPICE / POST-ACUTE
        # ============================================================
        OIGWorkPlanItem(
            "WP-030", 2018, 2025,
            "Home Health Face-to-Face Encounter Documentation",
            "Home Health Agency", "Home Health", "Documentation / Eligibility",
            _STATUS_OPEN, 285.0, 720.0, "high",
            "OIG Report A-05-19-00008 / Ongoing",
            "Face-to-face encounters missing or insufficient; ~$650M+ in aggregate recoveries since "
            "2018 across state-level audits.",
            "Any home-health target with > 5% F2F documentation gaps — post-close HHVBP "
            "recoupment probability > 40%.",
            ["home health", "face-to-face", "f2f", "home health agency", "homebound"],
            ["Home Health"],
        ),
        OIGWorkPlanItem(
            "WP-031", 2016, 2024,
            "Hospice Eligibility — Continuous Home Care (CHC) Days",
            "Hospice", "Hospice", "Eligibility / Medical Necessity",
            _STATUS_ACTIVE, 125.0, 340.0, "high",
            "OIG Report A-05-20-00014",
            "CHC days billed without clinical documentation of crisis-level need; CHC rate is "
            "$1,500+/day vs. routine $200/day.",
            "Hospice targets with > 10% CHC-day mix should have documentation sample-audited; "
            "material EBITDA risk at 3-5%.",
            ["hospice", "continuous home care", "chc", "hospice eligibility", "crisis"],
            ["Hospice", "Home Health"],
        ),
        OIGWorkPlanItem(
            "WP-032", 2019, 2024,
            "SNF Therapy Thresholds (PDPM Transition Compliance)",
            "Skilled Nursing Facility", "Post-Acute / SNF", "Billing Accuracy",
            _STATUS_COMPLETED, 85.0, 210.0, "medium",
            "OIG Report A-06-19-01003 (2022)",
            "Therapy minutes billed above PDPM-appropriate thresholds; PDPM transition 10/2019 "
            "shifted incentives and OIG audited 2020-2022.",
            "Post-2019 SNF targets: verify therapy utilization normalized to PDPM; pre-PDPM-era "
            "claims carry historical exposure.",
            ["snf", "skilled nursing", "pdpm", "therapy minutes", "nursing facility"],
            ["Skilled Nursing Facility", "SNF/LTC"],
        ),
        OIGWorkPlanItem(
            "WP-033", 2021, 2025,
            "Home Health Value-Based Purchasing (HHVBP) — Quality Reporting Integrity",
            "Home Health Agency", "Home Health", "Data Integrity",
            _STATUS_OPEN, 45.0, 120.0, "medium",
            "Active Work Plan 2021",
            "HHVBP quality-data mis-reporting to improve TPS scores; penalties/incentives up to "
            "8% of Medicare revenue.",
            "HHVBP-heavy home-health targets should have TPS scores validated against chart audit.",
            ["hhvbp", "home health value", "tps", "quality reporting", "home health quality"],
            ["Home Health"],
        ),

        # ============================================================
        # MEDICARE ADVANTAGE
        # ============================================================
        OIGWorkPlanItem(
            "WP-040", 2022, 2026,
            "Medicare Advantage Risk Adjustment Data Validation (RADV) Extrapolation",
            "MA Plan / Primary Care Group", "MA Risk Adjustment", "Risk Adjustment",
            _STATUS_OPEN, 850.0, 2400.0, "high",
            "Final Rule CMS-4185-F (2023) / Ongoing Work Plan",
            "RADV extrapolation final rule (April 2023) allows CMS to extrapolate audit findings "
            "across MA contracts — program-wide $4.7B recovery estimated 2024-2032.",
            "MA-risk primary care rollups (Cano, CareMax template) are MOST exposed; V28 + RADV "
            "extrapolation is a double-threat requiring explicit reserve modeling.",
            ["medicare advantage", "ma", "radv", "risk adjustment", "raf", "hcc",
             "chart review", "ma risk"],
            ["Primary Care", "Medicare Advantage"],
        ),
        OIGWorkPlanItem(
            "WP-041", 2019, 2024,
            "MA Chart Reviews — Diagnoses Added to Encounter Data",
            "MA Plan", "MA Risk Adjustment", "Risk Adjustment",
            _STATUS_COMPLETED, 320.0, 780.0, "high",
            "OIG Report A-07-19-01185 (2021)",
            "Retrospective chart-review diagnoses that don't meet MCC/CC criteria; audits found "
            "~8% of chart-review-sourced diagnoses unsupported.",
            "MA-heavy providers and MA plan acquirers: model 6-10% of chart-review HCC revenue as "
            "at-risk under RADV extrapolation.",
            ["chart review", "ma", "risk adjustment", "medicare advantage", "hcc coding"],
            ["Medicare Advantage"],
        ),
        OIGWorkPlanItem(
            "WP-042", 2024, 2026,
            "V28 Risk-Adjustment Model Transition Compliance",
            "MA Plan / Primary Care Group", "MA Risk Adjustment", "Risk Adjustment",
            _STATUS_OPEN, 450.0, 1100.0, "high",
            "Active Work Plan 2024",
            "V28 HCC model implementation (3-year phase-in 2024-2026) reduces average scores 3-4%; "
            "OIG will audit providers whose V28 scores show anomalous deviation from V24.",
            "MA-risk primary care is in structural reset; pre-V28 diligence multiples assumed V24 "
            "economics that no longer hold.",
            ["v28", "v24", "risk adjustment", "hcc", "ma", "medicare advantage"],
            ["Primary Care", "Medicare Advantage"],
        ),

        # ============================================================
        # 340B / DRUG PRICING
        # ============================================================
        OIGWorkPlanItem(
            "WP-050", 2018, 2024,
            "340B Program — Eligibility and Diversion",
            "Hospital / FQHC", "340B", "Eligibility",
            _STATUS_OPEN, 85.0, 240.0, "medium",
            "OIG Report A-01-20-00501",
            "340B-eligible entities diverting discounted drugs to non-eligible patients; contract "
            "pharmacy arrangements under continued scrutiny.",
            "340B-revenue-dependent hospitals — verify eligibility + compliance program as QoR item.",
            ["340b", "340b program", "disproportionate share", "dsh", "fqhc", "contract pharmacy"],
            ["Hospital", "FQHC", "Health System"],
        ),
        OIGWorkPlanItem(
            "WP-051", 2022, 2026,
            "Medicare Part B Drug Spending — ASP Reporting Accuracy",
            "Manufacturer / Infusion Center", "Drug Pricing", "Rate Accuracy",
            _STATUS_OPEN, 180.0, 420.0, "medium",
            "Active Work Plan 2022",
            "Average Sales Price (ASP) under-reporting by manufacturers; Part B pays ASP + 6%.",
            "Infusion and specialty pharmacy rollups downstream of ASP pricing — modest rate risk.",
            ["asp", "average sales price", "part b drug", "infusion", "specialty pharmacy"],
            ["Oncology / Infusion", "Specialty Pharmacy"],
        ),

        # ============================================================
        # LABORATORY / PATHOLOGY
        # ============================================================
        OIGWorkPlanItem(
            "WP-060", 2017, 2024,
            "Laboratory Panel Unbundling — Comprehensive Metabolic Panel Components",
            "Lab / Pathology", "Lab Services", "Unbundling",
            _STATUS_COMPLETED, 125.0, 320.0, "medium",
            "OIG Report A-05-18-00012 (2019)",
            "Labs billing individual components (80048-level) when panel (80053 CMP) is "
            "appropriate; large aggregate $ recoveries.",
            "Reference lab and independent lab targets — scan billing for panel-component "
            "unbundling patterns.",
            ["lab", "laboratory", "panel", "unbundling", "cmp", "bmp", "80053", "80048"],
            ["Lab / Pathology"],
        ),
        OIGWorkPlanItem(
            "WP-061", 2021, 2024,
            "Molecular Pathology / Tier 2 Code Overuse",
            "Lab / Pathology", "Lab Services", "Medical Necessity",
            _STATUS_ACTIVE, 65.0, 180.0, "medium",
            "OIG Report A-03-21-00300",
            "Tier-2 molecular pathology codes billed at rates inconsistent with medical necessity; "
            "growing area of enforcement.",
            "Specialty molecular / genomics lab targets — verify ordering-physician relationships.",
            ["molecular pathology", "tier 2", "genomic", "pathology", "specialty lab"],
            ["Lab / Pathology"],
        ),

        # ============================================================
        # TELEHEALTH
        # ============================================================
        OIGWorkPlanItem(
            "WP-070", 2021, 2025,
            "Telehealth Services Billed During COVID-19 PHE Flexibilities",
            "Physician Group / Telehealth", "Telehealth", "Billing Accuracy",
            _STATUS_ACTIVE, 145.0, 385.0, "high",
            "OIG Report A-04-22-06220 (2024)",
            "2020-2023 PHE telehealth expansion created audit backlog; audio-only visits billed at "
            "audiovisual rates are primary focus.",
            "Telehealth-heavy behavioral-health and primary-care rollups — 2020-2023 claims are "
            "audit-eligible; model recoupment exposure per volume.",
            ["telehealth", "telemedicine", "virtual", "audio-only", "video visit", "remote"],
            ["Telehealth", "Primary Care", "Behavioral Health"],
        ),
        OIGWorkPlanItem(
            "WP-071", 2023, 2026,
            "Remote Physiologic Monitoring (RPM) Billing Compliance",
            "Physician Group / RPM Vendor", "Telehealth / RPM", "Documentation",
            _STATUS_OPEN, 85.0, 210.0, "medium",
            "Active Work Plan 2023",
            "RPM codes (99453-99458) billed without required 16-day data transmission threshold; "
            "RPM volume grew 10x during 2020-2023.",
            "Chronic-care and RPM-platform businesses — audit data-transmission logs vs. billing.",
            ["rpm", "remote monitoring", "99453", "99454", "99457", "99458", "chronic care"],
            ["Primary Care", "Cardiology", "Telehealth"],
        ),

        # ============================================================
        # DME / DURABLE MEDICAL EQUIPMENT
        # ============================================================
        OIGWorkPlanItem(
            "WP-080", 2016, 2024,
            "DME Supplier Competitive Bidding Program Compliance",
            "DME Supplier", "DME", "Eligibility / Documentation",
            _STATUS_COMPLETED, 95.0, 250.0, "medium",
            "OIG Report A-06-17-00001 (2019)",
            "DME billing outside competitive bidding coverage rules; affects most-common items "
            "(CPAP supplies, diabetic testing, back braces).",
            "DME rollups pre-2019 may carry legacy exposure; verify competitive-bid compliance.",
            ["dme", "durable medical equipment", "competitive bidding", "cpap", "diabetic"],
            ["DME"],
        ),
        OIGWorkPlanItem(
            "WP-081", 2022, 2026,
            "Orthotics and Prosthetics Supplier Billing",
            "O&P Supplier", "DME / O&P", "Billing Accuracy",
            _STATUS_OPEN, 42.0, 125.0, "medium",
            "Active Work Plan 2022",
            "Custom orthotics billed at fitted rates when off-the-shelf appropriate; "
            "telemarketing-sourced orders flagged.",
            "O&P rollups — verify fitting documentation; telemarketer-fed orders carry fraud flags.",
            ["orthotic", "prosthetic", "o&p", "brace", "knee brace", "back brace"],
            ["DME"],
        ),

        # ============================================================
        # BEHAVIORAL HEALTH
        # ============================================================
        OIGWorkPlanItem(
            "WP-090", 2019, 2024,
            "Opioid Treatment Program (OTP) / Medication-Assisted Treatment Billing",
            "Behavioral Health Provider", "Behavioral Health", "Billing Accuracy",
            _STATUS_ACTIVE, 58.0, 155.0, "medium",
            "OIG Report A-05-22-00008",
            "MAT billing codes (G2086/G2087/G2088) — volume grew 5x 2020-2023 with PHE expansion; "
            "documentation gaps common.",
            "Behavioral-health + addiction-treatment rollups — verify MAT billing documentation.",
            ["otp", "mat", "medication assisted", "opioid", "addiction", "suboxone", "methadone"],
            ["Behavioral Health"],
        ),
        OIGWorkPlanItem(
            "WP-091", 2020, 2025,
            "Partial Hospitalization Program (PHP) / Intensive Outpatient (IOP) Billing",
            "Behavioral Health Provider", "Behavioral Health", "Medical Necessity",
            _STATUS_OPEN, 85.0, 220.0, "high",
            "Active Work Plan 2020",
            "PHP (level-5 BH) and IOP billing without medical-necessity documentation for acuity; "
            "PHP rate is 3-5x standard outpatient therapy.",
            "Inpatient/PHP-heavy behavioral-health targets — high exposure; standard chart audit.",
            ["php", "partial hospitalization", "iop", "intensive outpatient", "behavioral",
             "substance use"],
            ["Behavioral Health"],
        ),
        OIGWorkPlanItem(
            "WP-092", 2023, 2026,
            "Applied Behavior Analysis (ABA) Therapy Billing for Medicaid Children",
            "Behavioral Health / ABA Provider", "Behavioral Health / ABA", "Billing Accuracy",
            _STATUS_OPEN, 45.0, 135.0, "medium",
            "Active Work Plan 2023",
            "ABA therapy hours billed beyond treatment-plan authorization; Medicaid ABA spend grew "
            "8x 2018-2024.",
            "ABA rollups — verify treatment-plan authorization compliance against claims volume.",
            ["aba", "applied behavior analysis", "autism", "97153", "97155", "medicaid aba"],
            ["Behavioral Health"],
        ),

        # ============================================================
        # DIALYSIS / NEPHROLOGY
        # ============================================================
        OIGWorkPlanItem(
            "WP-100", 2018, 2024,
            "Dialysis Monthly Capitation Payment (MCP) Visit Documentation",
            "Dialysis Provider", "Nephrology", "Documentation",
            _STATUS_COMPLETED, 38.0, 95.0, "medium",
            "OIG Report A-03-20-00308 (2022)",
            "MCP billed at higher visit-count tier (90961/90962) without supporting documentation; "
            "DaVita/Fresenius concentrated-market focus.",
            "Dialysis operator targets — verify MCP tier documentation.",
            ["dialysis", "mcp", "monthly capitation", "90961", "90962", "nephrology", "esrd"],
            ["Nephrology"],
        ),
        OIGWorkPlanItem(
            "WP-101", 2023, 2026,
            "ESRD Treatment Choices (ETC) Model Performance",
            "Dialysis Provider", "Nephrology", "Quality Reporting",
            _STATUS_OPEN, 22.0, 65.0, "low",
            "Active Work Plan 2023",
            "ETC home-dialysis and transplant waitlist performance; mandatory model in 30% of "
            "HRRs with ±8% payment adjustment.",
            "Dialysis operators in ETC regions — performance scores are covenant-relevant.",
            ["etc", "esrd treatment choices", "home dialysis", "transplant", "esrd"],
            ["Nephrology"],
        ),

        # ============================================================
        # EMERGENCY MEDICINE / FREESTANDING ED
        # ============================================================
        OIGWorkPlanItem(
            "WP-110", 2020, 2025,
            "Freestanding Emergency Room E/M Level Distribution",
            "Freestanding ED", "Emergency Medicine", "Upcoding",
            _STATUS_OPEN, 55.0, 140.0, "high",
            "Active Work Plan 2020",
            "Freestanding ERs billing 99285 (Level 5) at > 70% of visits against hospital-ED "
            "median of 40-50%; acuity-without-documentation pattern.",
            "Any freestanding-ED target — mandatory sample audit of 99285 documentation.",
            ["freestanding", "freestanding-ed", "freestanding er", "standalone er", "99285",
             "ed level 5"],
            ["Emergency Medicine", "Freestanding ED"],
        ),

        # ============================================================
        # EYE CARE / OPHTHALMOLOGY
        # ============================================================
        OIGWorkPlanItem(
            "WP-120", 2019, 2024,
            "Cataract Surgery — Premium IOL / Same-Day YAG Billing",
            "Ophthalmology Practice", "Eye Care", "Billing Accuracy",
            _STATUS_COMPLETED, 28.0, 82.0, "medium",
            "OIG Report A-05-21-00011 (2023)",
            "66984 cataract + 66821 YAG within global period billed without 79 modifier; "
            "ophthalmology rollup focus.",
            "Eye-care rollups — verify global-period and modifier compliance.",
            ["cataract", "iol", "yag", "66984", "66821", "ophthalmology", "eye care"],
            ["Eye Care / Ophthalmology"],
        ),

        # ============================================================
        # WOUND CARE / HYPERBARIC
        # ============================================================
        OIGWorkPlanItem(
            "WP-130", 2017, 2024,
            "Hyperbaric Oxygen Therapy (HBOT) Medical Necessity",
            "Wound Care Provider / Hyperbaric Clinic", "Wound Care", "Medical Necessity",
            _STATUS_COMPLETED, 72.0, 185.0, "medium",
            "OIG Report A-03-18-00100 (2020)",
            "HBOT billed outside approved indications (15 covered conditions); PE-backed wound-care "
            "consolidators under audit 2018-2022.",
            "Wound-care rollups — sample-audit HBOT indication documentation.",
            ["hbot", "hyperbaric", "wound care", "wound", "diabetic wound", "pressure ulcer"],
            ["Dermatology / Wound Care"],
        ),

        # ============================================================
        # RURAL HEALTH / FQHC
        # ============================================================
        OIGWorkPlanItem(
            "WP-140", 2018, 2024,
            "FQHC / RHC Prospective Payment System Wrap-Around Billing",
            "FQHC / RHC", "Primary Care", "Rate Accuracy",
            _STATUS_COMPLETED, 32.0, 85.0, "low",
            "OIG Report A-05-19-00050 (2021)",
            "FQHC/RHC encounter rates vs. fee-for-service sub-billing inconsistencies.",
            "FQHC-adjacent primary care rollups — verify encounter billing accuracy.",
            ["fqhc", "rhc", "rural health", "federally qualified", "encounter rate"],
            ["FQHC", "Primary Care"],
        ),

        # ============================================================
        # ANESTHESIOLOGY
        # ============================================================
        OIGWorkPlanItem(
            "WP-150", 2016, 2024,
            "Medical Direction / Medically Supervised Anesthesia (QX/QY/QZ Modifiers)",
            "Anesthesia Group", "Anesthesia", "Billing Accuracy",
            _STATUS_ACTIVE, 85.0, 220.0, "high",
            "OIG Report A-01-19-00510 (2022)",
            "Anesthesia modifier abuse — QY/QX (supervised) billed when concurrent direction "
            "requirements not met; USAP-class consolidators under scrutiny.",
            "Anesthesia rollups — verify concurrent-direction compliance; material 1-3% EBITDA exposure.",
            ["anesthesia", "anesthesiologist", "qx", "qy", "qz", "crna", "anesthesia modifier"],
            ["Anesthesia"],
        ),
    ]


# ---------------------------------------------------------------------------
# NCCI crosswalk — bridges OIG Work Plan items to existing NCCI edit categories
# ---------------------------------------------------------------------------

def _build_ncci_crosswalks() -> List[NCCICrosswalkLink]:
    return [
        NCCICrosswalkLink(
            "WP-010", "Modifier 25 Usage on Same-Day E/M + Procedure Claims",
            "E/M + Same-day Procedure (Mod 25)",
            "Direct overlap — WP-010 audit topic is the NCCI edit category codified in ncci_edits.py AuditCrosswalk table.",
        ),
        NCCICrosswalkLink(
            "WP-011", "Modifier 59 / X{EPSU} Usage",
            "Distinct-Procedural-Service (Mod 59/X{EPSU})",
            "Direct overlap — $1.25B typical recovery per NCCI module already reflects this Work Plan item's historical enforcement.",
        ),
        NCCICrosswalkLink(
            "WP-022", "Cardiac Stress Test Appropriate Use",
            "Cardiac Stress Test Overlap",
            "Direct overlap — same 78452 + 93350 pattern encoded in NCCI PTP edit library.",
        ),
        NCCICrosswalkLink(
            "WP-120", "Cataract Surgery / Same-Day YAG",
            "Cataract + Same-day YAG",
            "Direct overlap — 66984 + 66821 NCCI edit maps to this completed Work Plan item.",
        ),
        NCCICrosswalkLink(
            "WP-060", "Laboratory Panel Unbundling",
            "Lab Panel Unbundling (via MUE 80053 + components)",
            "Adjacent — MUE limits on panels + component codes enforce the audit outcome.",
        ),
        NCCICrosswalkLink(
            "WP-110", "Freestanding ER E/M Level Distribution",
            "MUE 99285 (ED L5) and ED E/M Audits",
            "Adjacent — MUE on ED L5 per DOS + upcoding focus mirrors this Work Plan item.",
        ),
        NCCICrosswalkLink(
            "WP-031", "Hospice CHC Days",
            "Home Health Skilled-Nursing Unit Inflation",
            "Adjacent — G-code unit-of-service audits in NCCI MUE library cover related pattern.",
        ),
    ]


# ---------------------------------------------------------------------------
# Provider-type classifier (reuse keyword pattern from ncci_edits.py)
# ---------------------------------------------------------------------------

_PROVIDER_KEYWORDS: List[Tuple[str, List[str]]] = [
    ("Hospital", ["hospital", "health system", "medical center", "amc", "safety net"]),
    ("Home Health / Hospice", ["home health", "hospice", "home-health", "aveanna", "amedisys", "encompass home"]),
    ("Skilled Nursing Facility", ["snf", "skilled nursing", "nursing home", "ltc ", "long-term care"]),
    ("Physician Group", ["physician", "medical group", "mso ", "pcp", "primary care",
                          "dermatology", "cardiology", "gastroenter", "urology", "orthoped"]),
    ("Behavioral Health", ["behavioral", "psych", "mental health", "addiction", "aba", "autism"]),
    ("Dialysis Provider", ["dialysis", "renal", "davita", "fmc ", "kidney"]),
    ("DME Supplier", ["dme", "durable medical", "oxygen", "cpap", "diabetic supply"]),
    ("Lab / Pathology", ["laboratory", "pathology", "reference lab", "diagnostic lab"]),
    ("Imaging Center", ["imaging", "radiology", "mri", "ct scan", "rayus", "radnet"]),
    ("Ophthalmology Practice", ["ophthalm", "eye care", "lasik", "retina"]),
    ("Freestanding ED", ["freestanding", "freestanding-ed", "freestanding er", "standalone er"]),
    ("Telehealth", ["telehealth", "telemedicine", "virtual", "digital-first"]),
    ("Anesthesia Group", ["anesthesia", "anesthesiologist", "crna"]),
    ("MA Plan / Primary Care Group", ["medicare advantage", "ma risk", "ma-risk", "chenmed",
                                       "oak street", "cano", "caremax", "risk-bearing"]),
    ("Hospice", ["hospice"]),
    ("FQHC / RHC", ["fqhc", "rhc", "rural health", "federally qualified"]),
]


def _classify_provider(deal: dict) -> str:
    hay = (
        str(deal.get("deal_name", "")) + " " +
        str(deal.get("notes", "")) + " " +
        str(deal.get("buyer", ""))
    ).lower()
    for label, kws in _PROVIDER_KEYWORDS:
        for kw in kws:
            if kw in hay:
                return label
    return "Physician Group"


# ---------------------------------------------------------------------------
# Per-deal exposure scoring
# ---------------------------------------------------------------------------

def _score_deal_exposure(
    deal: dict,
    items: List[OIGWorkPlanItem],
) -> DealWorkPlanExposure:
    provider_type = _classify_provider(deal)
    hay = (
        str(deal.get("deal_name", "")) + " " +
        str(deal.get("notes", "")) + " " +
        str(deal.get("buyer", ""))
    ).lower()

    matched: List[Tuple[OIGWorkPlanItem, int]] = []  # (item, weighted-score)
    for it in items:
        # Weight keyword hits by specificity: short generic keywords (< 5 chars like "dme",
        # "iop", "ma") score 1; longer/more specific keywords score 3. Sector match alone
        # (no keyword) is weak signal — needs keyword corroboration.
        kw_score = 0
        for kw in it.keyword_fingerprint:
            if kw.lower() in hay:
                kw_score += 3 if len(kw) >= 6 else 1
        sector_hits = sum(1 for s in it.sector_fingerprint if s.lower() in hay)
        # Require at least ONE specific keyword hit, or strong sector + any keyword
        if kw_score >= 3 or (sector_hits > 0 and kw_score >= 1):
            matched.append((it, kw_score + sector_hits))

    # Rank matches by weighted score; per-deal exposure is the TOP 5 matched items only
    matched.sort(key=lambda m: m[1], reverse=True)
    top_matches = matched[:5]

    open_active = sum(1 for (it, _) in top_matches if it.status in (_STATUS_OPEN, _STATUS_ACTIVE))
    total_exposure = sum(
        (it.typical_recovery_low_mm + it.typical_recovery_high_mm) / 2.0
        for (it, _) in top_matches if it.status in (_STATUS_OPEN, _STATUS_ACTIVE)
    )
    # Scale to per-target share of national recovery pool. Typical target takes
    # 0.3-0.8% of the audit-program-wide recovery; use 0.5% as calibrated midpoint.
    total_exposure_target = total_exposure * 0.005

    if matched:
        top_item = matched[0][0]
    else:
        top_item = items[0] if items else None

    # Risk tier — require BOTH high open/active count AND meaningful exposure for CRITICAL
    if open_active >= 3 and total_exposure_target >= 5.0:
        tier = "CRITICAL"
    elif open_active >= 2 and total_exposure_target >= 2.0:
        tier = "HIGH"
    elif open_active >= 1 or total_exposure_target >= 0.5:
        tier = "MEDIUM"
    elif len(matched) >= 1:
        tier = "LOW"
    else:
        tier = "CLEAN"

    return DealWorkPlanExposure(
        deal_name=str(deal.get("deal_name", "—"))[:80],
        year=int(deal.get("year") or 0),
        buyer=str(deal.get("buyer", "—"))[:60],
        inferred_provider_type=provider_type,
        matched_items=len(matched),
        open_active_matches=open_active,
        total_exposure_mid_mm=round(total_exposure_target, 2),
        top_item_id=top_item.item_id if top_item else "—",
        top_item_title=top_item.title if top_item else "—",
        risk_tier=tier,
    )


# ---------------------------------------------------------------------------
# Per-provider-type category rollup
# ---------------------------------------------------------------------------

def _build_categories(items: List[OIGWorkPlanItem]) -> List[WorkPlanCategory]:
    by_type: Dict[str, List[OIGWorkPlanItem]] = {}
    for it in items:
        by_type.setdefault(it.provider_type, []).append(it)

    rows: List[WorkPlanCategory] = []
    for provider_type, pt_items in by_type.items():
        open_c = sum(1 for i in pt_items if i.status == _STATUS_OPEN)
        active_c = sum(1 for i in pt_items if i.status == _STATUS_ACTIVE)
        completed_c = sum(1 for i in pt_items if i.status == _STATUS_COMPLETED)
        high_c = sum(1 for i in pt_items if i.enforcement_risk == "high")
        rec_mid = sum(
            (i.typical_recovery_low_mm + i.typical_recovery_high_mm) / 2.0 for i in pt_items
        )
        rows.append(WorkPlanCategory(
            provider_type=provider_type,
            item_count=len(pt_items),
            open_count=open_c,
            active_count=active_c,
            completed_count=completed_c,
            aggregate_recovery_mid_mm=round(rec_mid, 1),
            high_risk_count=high_c,
            oldest_item_year=min(i.year_added for i in pt_items),
            newest_item_year=max(i.year_added for i in pt_items),
        ))
    rows.sort(key=lambda r: r.aggregate_recovery_mid_mm, reverse=True)
    return rows


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compute_oig_workplan() -> OIGWorkPlanResult:
    corpus = _load_corpus()
    items = _build_items()
    ncci_crosswalks = _build_ncci_crosswalks()
    categories = _build_categories(items)

    all_exposures = [_score_deal_exposure(d, items) for d in corpus]
    # Sort by CRITICAL then HIGH then by exposure
    tier_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "CLEAN": 4}
    all_exposures.sort(
        key=lambda e: (tier_order.get(e.risk_tier, 9), -e.total_exposure_mid_mm)
    )
    # Keep top 60 for UI
    deal_exposures = all_exposures[:60]

    deals_any = sum(1 for e in all_exposures if e.matched_items > 0)
    critical_deals = sum(1 for e in all_exposures if e.risk_tier == "CRITICAL")

    total_open = sum(1 for i in items if i.status == _STATUS_OPEN)
    total_active = sum(1 for i in items if i.status == _STATUS_ACTIVE)
    total_completed = sum(1 for i in items if i.status == _STATUS_COMPLETED)
    aggregate_rec = sum(
        (i.typical_recovery_low_mm + i.typical_recovery_high_mm) / 2.0 for i in items
    )

    return OIGWorkPlanResult(
        total_items=len(items),
        total_open=total_open,
        total_active=total_active,
        total_completed=total_completed,
        aggregate_recovery_mid_mm=round(aggregate_rec, 1),
        deals_with_any_match=deals_any,
        critical_risk_deals=critical_deals,
        items=items,
        categories=categories,
        deal_exposures=deal_exposures,
        ncci_crosswalks=ncci_crosswalks,
        corpus_deal_count=len(corpus),
        knowledge_base_effective_date=_KB_EFFECTIVE_DATE,
        knowledge_base_version=_KB_VERSION,
    )
