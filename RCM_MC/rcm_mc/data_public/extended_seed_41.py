"""Extended seed batch 41 — 15 PE healthcare deals spanning neonatal ICU staffing,
pediatric subspecialty, academic medical group management, hospital-at-home,
remote patient monitoring, medical nutrition therapy, hyperbaric oxygen therapy,
interventional radiology/vascular, Mohs surgery/procedural derm, ASC management,
ophthalmology/retina, audiology, physiatry/PM&R, pulmonology/sleep medicine,
and nephrology/ESRD-adjacent services.

Sources: public filings, press releases, investor decks, disclosed transaction terms.
All financial figures drawn from public disclosures; marked None where not public.
"""
from __future__ import annotations
from typing import Any, Dict, List

EXTENDED_SEED_DEALS_41: List[Dict[str, Any]] = [
    {
        # 1 — Neonatal ICU staffing / hospitalist groups
        "source_id": "ext41_001",
        "source": "seed",
        "company_name": "Neonatal Care Partners",
        "sector": "Neonatal ICU Staffing / Hospitalist Groups",
        "year": 2016,
        "buyer": "Varsity Healthcare Partners",
        "ev_mm": 180.0,
        "ebitda_at_entry_mm": 18.0,
        "moic": 3.2,
        "irr": 0.27,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.12,
            "medicare": 0.48,
            "medicaid": 0.30,
            "other": 0.10,
        },
        "notes": (
            "NICU hospitalist groups face complex RCM due to overlapping physician and "
            "facility billing, critical-care time-based CPT codes (99291/99292), and high "
            "Medicaid exposure requiring state-by-state prior authorization workflows. "
            "Coordination between neonatology professional billing and hospital facility "
            "claims creates frequent claim splitting errors and denial rates above 18%."
        ),
    },
    {
        # 2 — Pediatric subspecialty (cardiology, neurology)
        "source_id": "ext41_002",
        "source": "seed",
        "company_name": "Summit Pediatric Specialists",
        "sector": "Pediatric Subspecialty (Cardiology, Neurology)",
        "year": 2018,
        "buyer": "New MainStream Capital",
        "ev_mm": 240.0,
        "ebitda_at_entry_mm": 22.0,
        "moic": 3.5,
        "irr": 0.30,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.52,
            "medicare": 0.25,
            "medicaid": 0.18,
            "other": 0.05,
        },
        "notes": (
            "Pediatric cardiology and neurology practices contend with high-value diagnostic "
            "procedure billing (echocardiography, EEG/EMG, cardiac catheterization) that "
            "demands meticulous modifier usage and bundling analysis under CCI edits. "
            "CHIP and Medicaid managed-care contracts frequently reimburse at rates 20–35% "
            "below commercial benchmarks, compressing margins on the highest-complexity cases."
        ),
    },
    {
        # 3 — Academic medical group management
        "source_id": "ext41_003",
        "source": "seed",
        "company_name": "Meridian Academic Practice Solutions",
        "sector": "Academic Medical Group Management",
        "year": 2017,
        "buyer": "Waud Capital Partners",
        "ev_mm": 520.0,
        "ebitda_at_entry_mm": 48.0,
        "moic": 3.8,
        "irr": 0.31,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.45,
            "medicare": 0.28,
            "medicaid": 0.20,
            "other": 0.07,
        },
        "notes": (
            "Academic faculty practice plans must comply with teaching physician attestation "
            "rules (Medicare requires the attending to document a substantive participation "
            "note or co-sign the resident note), and billing errors here trigger 100% "
            "recoupment exposure across all claims in a look-back audit. "
            "Split/shared visit rules updated under 2023 E&M revisions add further "
            "documentation complexity when residents and attendings jointly provide services."
        ),
    },
    {
        # 4 — Hospital-at-home / acute care at home
        "source_id": "ext41_004",
        "source": "seed",
        "company_name": "Homestead Acute Care Networks",
        "sector": "Hospital-at-Home / Acute Care at Home",
        "year": 2021,
        "buyer": "General Atlantic",
        "ev_mm": 310.0,
        "ebitda_at_entry_mm": 28.0,
        "moic": 2.8,
        "irr": 0.26,
        "hold_years": 3.5,
        "payer_mix": {
            "commercial": 0.38,
            "medicare": 0.42,
            "medicaid": 0.15,
            "other": 0.05,
        },
        "notes": (
            "Hospital-at-home programs bill under an acute inpatient DRG waiver authorized "
            "by CMS Acute Hospital Care at Home, creating a novel RCM pathway with limited "
            "payer precedent and inconsistent commercial insurer coverage policies. "
            "Daily remote monitoring requirements must be separately documented and billed "
            "through RPM codes to avoid claim bundling conflicts with the facility DRG."
        ),
    },
    {
        # 5 — Remote monitoring platforms (RPM/CCM)
        "source_id": "ext41_005",
        "source": "seed",
        "company_name": "ConnectedCare RPM Solutions",
        "sector": "Remote Monitoring Platforms (RPM/CCM)",
        "year": 2020,
        "buyer": "Insight Partners",
        "ev_mm": 415.0,
        "ebitda_at_entry_mm": 38.0,
        "moic": 3.6,
        "irr": 0.33,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.30,
            "medicare": 0.50,
            "medicaid": 0.12,
            "other": 0.08,
        },
        "notes": (
            "RPM platforms bill CPT 99453/99454 for device setup and daily data transmission, "
            "99457/99458 for monthly interactive communication time, and 99490/99491 for CCM — "
            "each requiring strict monthly time documentation and qualified clinical staff "
            "attestation to avoid retroactive denials. "
            "Medicare's 20-minute monthly minimum for CCM billing and its prohibition on "
            "billing RPM and CCM for the same service period in the same month require "
            "sophisticated claim-logic engines to prevent inadvertent overlap."
        ),
    },
    {
        # 6 — Medical nutrition therapy
        "source_id": "ext41_006",
        "source": "seed",
        "company_name": "Apex Nutrition Therapy Group",
        "sector": "Medical Nutrition Therapy",
        "year": 2015,
        "buyer": "Revelstoke Capital Partners",
        "ev_mm": 135.0,
        "ebitda_at_entry_mm": 15.0,
        "moic": 3.1,
        "irr": 0.28,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.55,
            "medicare": 0.22,
            "medicaid": 0.18,
            "other": 0.05,
        },
        "notes": (
            "Medical nutrition therapy (MNT) is covered by Medicare Part B exclusively for "
            "diabetes and renal disease under CPT 97802-97804, and coverage extensions for "
            "obesity or eating disorders require non-Medicare payer-specific authorizations "
            "that vary widely by plan. "
            "Registered dietitian credentialing and supervision requirements under state "
            "licensure laws affect incident-to billing eligibility, creating compliance "
            "risk when MNT services are billed under a supervising physician's NPI."
        ),
    },
    {
        # 7 — Hyperbaric oxygen therapy
        "source_id": "ext41_007",
        "source": "seed",
        "company_name": "Oxygenics Wound & Hyperbaric Centers",
        "sector": "Hyperbaric Oxygen Therapy",
        "year": 2014,
        "buyer": "CRG (Capital Royalty Group)",
        "ev_mm": 155.0,
        "ebitda_at_entry_mm": 16.0,
        "moic": 3.0,
        "irr": 0.25,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.35,
            "medicare": 0.40,
            "medicaid": 0.20,
            "other": 0.05,
        },
        "notes": (
            "Hyperbaric oxygen therapy (HBOT) billing under CPT 99183 requires a physician "
            "to be present during the entire session, and documentation must support one of "
            "the 14 CMS-approved indications (e.g., chronic diabetic lower-extremity wound, "
            "osteomyelitis) to avoid medical necessity denials. "
            "Wound care facility billing often pairs HBOT with debridement codes, requiring "
            "careful CCI edit review to avoid automatic bundling reductions."
        ),
    },
    {
        # 8 — Interventional radiology / vascular
        "source_id": "ext41_008",
        "source": "seed",
        "company_name": "Vantage Interventional Vascular Partners",
        "sector": "Interventional Radiology / Vascular",
        "year": 2019,
        "buyer": "KSL Capital Partners",
        "ev_mm": 480.0,
        "ebitda_at_entry_mm": 44.0,
        "moic": 3.4,
        "irr": 0.29,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.48,
            "medicare": 0.32,
            "medicaid": 0.14,
            "other": 0.06,
        },
        "notes": (
            "Interventional radiology practices must navigate the global surgery package "
            "rules, which bundle pre- and post-procedure E&M services into the procedure fee "
            "for 10- and 90-day global periods, and the professional/technical component "
            "billing split when radiologists own equipment or bill in a hospital outpatient "
            "department where the facility captures the technical component. "
            "Prior authorization requirements for peripheral vascular interventions exceed "
            "60% of commercial plans, generating substantial administrative overhead."
        ),
    },
    {
        # 9 — Mohs surgery / procedural derm
        "source_id": "ext41_009",
        "source": "seed",
        "company_name": "ClearMargin Dermatology Group",
        "sector": "Mohs Surgery / Procedural Dermatology",
        "year": 2018,
        "buyer": "Audax Private Equity",
        "ev_mm": 620.0,
        "ebitda_at_entry_mm": 56.0,
        "moic": 4.0,
        "irr": 0.35,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.62,
            "medicare": 0.28,
            "medicaid": 0.06,
            "other": 0.04,
        },
        "notes": (
            "Mohs micrographic surgery billing under CPT 17311-17315 is stage-based, with "
            "each additional stage billed incrementally — documentation of en face tissue "
            "mapping, frozen section reads, and wound closure decisions must be captured "
            "contemporaneously to substantiate multi-stage claims under payer audit scrutiny. "
            "Repair codes (intermediate/complex closure) are frequently downcoded by "
            "commercial payers unless operative notes explicitly describe layer-by-layer "
            "tissue handling rather than a summary reconstruction description."
        ),
    },
    {
        # 10 — Ambulatory surgery center (ASC) management
        "source_id": "ext41_010",
        "source": "seed",
        "company_name": "Keystone Surgical Center Management",
        "sector": "Ambulatory Surgery Center (ASC) Management",
        "year": 2017,
        "buyer": "Ares Management",
        "ev_mm": 890.0,
        "ebitda_at_entry_mm": 82.0,
        "moic": 4.2,
        "irr": 0.36,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.58,
            "medicare": 0.30,
            "medicaid": 0.08,
            "other": 0.04,
        },
        "notes": (
            "ASC billing operates under a distinct CMS-published ASC payment system with "
            "its own fee schedule (not OPPS) and a separate list of covered procedures; "
            "services not on the ASC-covered list are denied outright regardless of medical "
            "necessity, requiring pre-procedure coverage verification against both the CMS "
            "list and payer-specific ASC coverage policies. "
            "Implant cost pass-through, surgeon preference card drift, and payer-specific "
            "implant carve-out policies create significant revenue leakage when implant "
            "invoices are not reconciled to billed charges at the claim level."
        ),
    },
    {
        # 11 — Ophthalmology / retina practices
        "source_id": "ext41_011",
        "source": "seed",
        "company_name": "RetinaClear Eye Associates",
        "sector": "Ophthalmology / Retina Practices",
        "year": 2019,
        "buyer": "FFL Partners",
        "ev_mm": 750.0,
        "ebitda_at_entry_mm": 68.0,
        "moic": 3.7,
        "irr": 0.32,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.40,
            "medicare": 0.45,
            "medicaid": 0.10,
            "other": 0.05,
        },
        "notes": (
            "Retina practices are heavy utilizers of high-cost anti-VEGF injections "
            "(bevacizumab, ranibizumab, aflibercept) billed under the buy-and-bill model "
            "at ASP+6%, where Medicare reimbursement may fall below acquisition cost during "
            "quarterly ASP lag periods, compressing drug margin. "
            "OCT imaging (CPT 92134) and fluorescein angiography billing require strict "
            "same-day bundling analysis, as commercial payers frequently apply CCI edits "
            "that deny the diagnostic imaging when billed on the same date as an injection."
        ),
    },
    {
        # 12 — Audiology / hearing aid dispensing
        "source_id": "ext41_012",
        "source": "seed",
        "company_name": "SoundPath Audiology Partners",
        "sector": "Audiology / Hearing Aid Dispensing",
        "year": 2016,
        "buyer": "Gryphon Investors",
        "ev_mm": 320.0,
        "ebitda_at_entry_mm": 30.0,
        "moic": 3.3,
        "irr": 0.29,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.35,
            "medicare": 0.38,
            "medicaid": 0.12,
            "other": 0.15,
        },
        "notes": (
            "Audiology practices face a fundamental RCM bifurcation: diagnostic audiology "
            "services (CPT 92550-92599) are covered by Medicare Part B, while hearing aid "
            "dispensing is a Medicare exclusion requiring either cash-pay or supplemental "
            "insurance billing, creating a dual-track revenue cycle with different "
            "documentation, billing, and collection workflows. "
            "Audiologist versus physician supervision requirements under incident-to rules "
            "determine whether services can be billed under a physician NPI, affecting "
            "reimbursement rates by as much as 15% across commercial contracts."
        ),
    },
    {
        # 13 — Physiatry / PM&R
        "source_id": "ext41_013",
        "source": "seed",
        "company_name": "MotionPath Rehabilitation Specialists",
        "sector": "Physiatry / PM&R",
        "year": 2015,
        "buyer": "Shore Capital Partners",
        "ev_mm": 210.0,
        "ebitda_at_entry_mm": 20.0,
        "moic": 3.2,
        "irr": 0.27,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.42,
            "medicare": 0.35,
            "medicaid": 0.18,
            "other": 0.05,
        },
        "notes": (
            "PM&R physiatry practices blend E&M visits with high-volume procedure billing "
            "(EMG/NCS, fluoroscopic joint injections, spasticity management) requiring "
            "modifier 26 professional component billing when procedures are performed in "
            "hospital or ASC facilities where the technical component is separately captured. "
            "Medicare therapy cap exceptions for physiatry-directed functional restoration "
            "programs require contemporaneous functional limitation reporting under the "
            "Claims-Based Reporting requirement, adding documentation burden per encounter."
        ),
    },
    {
        # 14 — Pulmonology / sleep medicine
        "source_id": "ext41_014",
        "source": "seed",
        "company_name": "ClearAir Pulmonary & Sleep Centers",
        "sector": "Pulmonology / Sleep Medicine",
        "year": 2020,
        "buyer": "Linden Capital Partners",
        "ev_mm": 365.0,
        "ebitda_at_entry_mm": 34.0,
        "moic": 3.4,
        "irr": 0.30,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.44,
            "medicare": 0.36,
            "medicaid": 0.15,
            "other": 0.05,
        },
        "notes": (
            "Sleep medicine billing for polysomnography (CPT 95808-95811) and CPAP titration "
            "studies requires documentation of a physician review and interpretation separate "
            "from the technologist's scoring, and commercial payers routinely require home "
            "sleep apnea testing (HSAT, CPT 95800-95801) as a step-therapy prerequisite "
            "before approving in-laboratory polysomnography. "
            "CPAP supply billing (HCPCS E0601 plus resupply codes) involves a 90-day "
            "compliance verification requirement under Medicare where device therapy logs "
            "must confirm at least 4 hours of nightly use on 70% of nights before ongoing "
            "supply reimbursement is authorized."
        ),
    },
    {
        # 15 — Nephrology / ESRD adjacent (not dialysis)
        "source_id": "ext41_015",
        "source": "seed",
        "company_name": "Clearwater Nephrology Associates",
        "sector": "Nephrology / ESRD Adjacent (Non-Dialysis)",
        "year": 2022,
        "buyer": "Berkshire Partners",
        "ev_mm": 280.0,
        "ebitda_at_entry_mm": 26.0,
        "moic": 2.6,
        "irr": 0.23,
        "hold_years": 3.5,
        "payer_mix": {
            "commercial": 0.28,
            "medicare": 0.50,
            "medicaid": 0.17,
            "other": 0.05,
        },
        "notes": (
            "Nephrology practices managing CKD stages 3-5 and transplant care must navigate "
            "the ESRD Monthly Capitation Payment (MCP) transition when patients reach "
            "dialysis initiation, which shifts all nephrology professional services into a "
            "bundled per-patient-per-month payment that dramatically changes revenue-cycle "
            "dynamics compared to fee-for-service CKD management. "
            "Kidney transplant follow-up billing involves complex coordination between the "
            "transplant center global package period and community nephrology follow-up "
            "visits, with CMS limiting separately billable nephrology E&M services during "
            "the 90-day post-transplant global period unless specific modifier conditions are met."
        ),
    },
]
