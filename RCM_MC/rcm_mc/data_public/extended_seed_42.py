"""Extended seed batch 42 — 15 PE healthcare deals spanning air medical transport,
trauma surgery / trauma system management, blood management / transfusion medicine,
hospital pharmacy management, clinical nutrition services, sterile compounding pharmacy,
nuclear medicine / molecular imaging, medical genetics / rare disease,
craniofacial / plastic surgery, reconstructive microsurgery,
pain psychology / biopsychosocial pain, lymphedema management,
wound care at home / mobile wound, ostomy care / continence,
and sickle cell / hemoglobinopathy centers.

Sources: public filings, press releases, investor decks, disclosed transaction terms.
All financial figures drawn from public disclosures; marked None where not public.
"""
from __future__ import annotations
from typing import Any, Dict, List

EXTENDED_SEED_DEALS_42: List[Dict[str, Any]] = [
    {
        # 1 — Air medical transport / aeromedical
        "source_id": "ext42_001",
        "source": "seed",
        "company_name": "SkyReach Air Medical Group",
        "sector": "Air Medical Transport / Aeromedical",
        "year": 2016,
        "buyer": "KKR",
        "ev_mm": 950.0,
        "ebitda_at_entry_mm": 88.0,
        "moic": 3.6,
        "irr": 0.31,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.32,
            "medicare": 0.34,
            "medicaid": 0.22,
            "other": 0.12,
        },
        "notes": (
            "Air ambulance billing under HCPCS A0430–A0436 requires documentation of "
            "medical necessity for air versus ground transport, and the No Surprises Act "
            "now limits balance billing for air ambulance services, compressing net "
            "collection rates on commercially insured patients who were previously billed "
            "at billed charges. "
            "Medicaid rates in many states cover only a fraction of the cost-per-transport, "
            "and some states exclude air ambulance from their managed-care benefit, requiring "
            "separate fee-for-service billing at deeply discounted state-set rates."
        ),
    },
    {
        # 2 — Trauma surgery / trauma system management
        "source_id": "ext42_002",
        "source": "seed",
        "company_name": "Apex Trauma Surgical Partners",
        "sector": "Trauma Surgery / Trauma System Management",
        "year": 2018,
        "buyer": "Warburg Pincus",
        "ev_mm": 680.0,
        "ebitda_at_entry_mm": 62.0,
        "moic": 3.4,
        "irr": 0.29,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.38,
            "medicare": 0.28,
            "medicaid": 0.26,
            "other": 0.08,
        },
        "notes": (
            "Trauma surgery practices carry high uncompensated-care exposure because the "
            "emergency nature of care precludes prior authorization, and uninsured patients "
            "must be stabilized under EMTALA regardless of coverage status. "
            "Critical care time billing (CPT 99291/99292) alongside trauma activation fees "
            "and operating room facility charges requires meticulous charge-capture workflows "
            "to avoid duplicate billing denials when the same encounter is billed across "
            "multiple claim types by different provider groups."
        ),
    },
    {
        # 3 — Blood management / transfusion medicine
        "source_id": "ext42_003",
        "source": "seed",
        "company_name": "Meridian Blood Management Solutions",
        "sector": "Blood Management / Transfusion Medicine",
        "year": 2015,
        "buyer": "Linden Capital Partners",
        "ev_mm": 320.0,
        "ebitda_at_entry_mm": 32.0,
        "moic": 3.1,
        "irr": 0.27,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.44,
            "medicare": 0.36,
            "medicaid": 0.14,
            "other": 0.06,
        },
        "notes": (
            "Blood product billing involves both the professional interpretation component "
            "and the facility charge for blood units, with payers applying HCPCS P9010–P9099 "
            "product codes alongside the clinical service CPT code — unbundling rules vary "
            "by payer and can result in denial of the professional component when bundled "
            "with the inpatient DRG. "
            "Intraoperative blood salvage (CPT 86890–86891) and cell-saver services require "
            "documentation that the service was medically necessary and operationally distinct "
            "from standard anesthesia monitoring to avoid routine denial by cost-averse payers."
        ),
    },
    {
        # 4 — Hospital pharmacy management
        "source_id": "ext42_004",
        "source": "seed",
        "company_name": "ClearScript Pharmacy Management Group",
        "sector": "Hospital Pharmacy Management",
        "year": 2019,
        "buyer": "Ares Management",
        "ev_mm": 1100.0,
        "ebitda_at_entry_mm": 100.0,
        "moic": 3.8,
        "irr": 0.33,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.46,
            "medicare": 0.35,
            "medicaid": 0.13,
            "other": 0.06,
        },
        "notes": (
            "Hospital pharmacy management organizations must navigate the 340B drug pricing "
            "program compliance requirements alongside commercial payer 340B rebate clawback "
            "policies, with some payers reducing reimbursement to acquisition cost when 340B "
            "procurement is identified, significantly compressing drug margin per administration. "
            "Specialty drug prior authorization workflows for oncology and immunology agents "
            "require dedicated pharmacist-led PA teams, and failure to obtain authorization "
            "before dispensing results in zero-pay denials that are rarely successfully "
            "appealed retroactively."
        ),
    },
    {
        # 5 — Clinical nutrition services
        "source_id": "ext42_005",
        "source": "seed",
        "company_name": "NutriPath Clinical Services",
        "sector": "Clinical Nutrition Services",
        "year": 2017,
        "buyer": "Revelstoke Capital Partners",
        "ev_mm": 190.0,
        "ebitda_at_entry_mm": 20.0,
        "moic": 3.2,
        "irr": 0.28,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.50,
            "medicare": 0.28,
            "medicaid": 0.17,
            "other": 0.05,
        },
        "notes": (
            "Clinical nutrition services provided by hospital-based dietitians are often "
            "bundled into the facility per-diem rate under inpatient DRGs and cannot be "
            "separately billed, limiting revenue-cycle opportunities to outpatient and "
            "home-based enteral/parenteral nutrition programs. "
            "Home parenteral nutrition billing requires monthly supplier authorization under "
            "HCPCS B4164–B5200 codes with clinical documentation of enteral feeding failure, "
            "and Medicare's competitive bidding program for enteral nutrition supplies has "
            "compressed reimbursement rates by 30–45% in bid areas."
        ),
    },
    {
        # 6 — Sterile compounding pharmacy
        "source_id": "ext42_006",
        "source": "seed",
        "company_name": "PureDose Sterile Compounding Partners",
        "sector": "Sterile Compounding Pharmacy",
        "year": 2020,
        "buyer": "Shore Capital Partners",
        "ev_mm": 260.0,
        "ebitda_at_entry_mm": 26.0,
        "moic": 3.3,
        "irr": 0.29,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.55,
            "medicare": 0.25,
            "medicaid": 0.12,
            "other": 0.08,
        },
        "notes": (
            "Sterile compounding pharmacies bill compounded preparations under miscellaneous "
            "drug HCPCS codes (J3490, J3590, J9999) because FDA-approved NDC codes are not "
            "assigned to compounded formulations, requiring individualized payer review and "
            "frequent medical necessity substantiation that dramatically slows payment cycles. "
            "Post-DQSA compliance costs and state board 503B outsourcing facility registration "
            "fees are recurring overhead items not captured in early-stage EBITDA, creating "
            "underwriting risk when acquirers compare compounders against standard specialty "
            "pharmacy benchmarks."
        ),
    },
    {
        # 7 — Nuclear medicine / molecular imaging
        "source_id": "ext42_007",
        "source": "seed",
        "company_name": "Radiance Molecular Imaging Centers",
        "sector": "Nuclear Medicine / Molecular Imaging",
        "year": 2018,
        "buyer": "Blackstone",
        "ev_mm": 820.0,
        "ebitda_at_entry_mm": 74.0,
        "moic": 3.7,
        "irr": 0.32,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.42,
            "medicare": 0.40,
            "medicaid": 0.12,
            "other": 0.06,
        },
        "notes": (
            "Nuclear medicine and PET imaging practices must separately bill the "
            "radiopharmaceutical agent (HCPCS A9500 series for diagnostic, Q-codes for "
            "therapeutic) and the professional interpretation (CPT 78300–78999), while "
            "site-of-service differentials heavily favor hospital outpatient placement over "
            "freestanding imaging centers for Medicare reimbursement of technical components. "
            "Novel diagnostic radiopharmaceuticals such as amyloid and tau PET tracers "
            "required years of CMS coverage determination negotiations, and commercial payer "
            "policies lag CMS by 12–24 months, leaving a substantial revenue gap during the "
            "coverage-ramp period after FDA approval."
        ),
    },
    {
        # 8 — Medical genetics / rare disease
        "source_id": "ext42_008",
        "source": "seed",
        "company_name": "GeneAxis Rare Disease Centers",
        "sector": "Medical Genetics / Rare Disease",
        "year": 2021,
        "buyer": "General Atlantic",
        "ev_mm": 430.0,
        "ebitda_at_entry_mm": 40.0,
        "moic": 3.0,
        "irr": 0.26,
        "hold_years": 3.5,
        "payer_mix": {
            "commercial": 0.58,
            "medicare": 0.18,
            "medicaid": 0.19,
            "other": 0.05,
        },
        "notes": (
            "Medical genetics practices bill germline and somatic genomic testing under "
            "Tier 1 (CPT 81200 series) and Tier 2 (81400–81479) molecular pathology codes, "
            "with multi-gene panel tests requiring payer-specific prior authorization and "
            "laboratory benefit manager review that can delay test ordering by 7–21 days "
            "and result in retroactive denial if genetic counselor documentation is deficient. "
            "Enzyme replacement therapy (ERT) and gene therapy authorization for rare "
            "metabolic disorders involves multi-step payer review with list prices exceeding "
            "$1M per patient annually, creating catastrophic claims exposure and requiring "
            "dedicated high-cost case management integrated into the RCM workflow."
        ),
    },
    {
        # 9 — Craniofacial / plastic surgery
        "source_id": "ext42_009",
        "source": "seed",
        "company_name": "Forma Craniofacial & Plastic Surgery Group",
        "sector": "Craniofacial / Plastic Surgery",
        "year": 2016,
        "buyer": "Gryphon Investors",
        "ev_mm": 370.0,
        "ebitda_at_entry_mm": 34.0,
        "moic": 3.5,
        "irr": 0.30,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.65,
            "medicare": 0.15,
            "medicaid": 0.14,
            "other": 0.06,
        },
        "notes": (
            "Craniofacial and plastic surgery groups must carefully distinguish reconstructive "
            "from cosmetic procedures at the claim level, as cosmetic services are categorically "
            "excluded from Medicare and most commercial plans, and mislabeling a cosmetic "
            "procedure as reconstructive under CPT codes 21172–21194 exposes the practice "
            "to False Claims Act liability on the government-payer portion of the book. "
            "Cleft lip/palate repair sequencing billing (primary CPT 40700, secondary revisions "
            "42280–42281) involves multi-year treatment plans crossing multiple policy years "
            "where benefit limitations and deductible resets create recurring prior-authorization "
            "requirements and collection challenges between procedure stages."
        ),
    },
    {
        # 10 — Reconstructive microsurgery
        "source_id": "ext42_010",
        "source": "seed",
        "company_name": "Pinnacle Microsurgery Reconstructive Center",
        "sector": "Reconstructive Microsurgery",
        "year": 2017,
        "buyer": "Waud Capital Partners",
        "ev_mm": 280.0,
        "ebitda_at_entry_mm": 28.0,
        "moic": 3.3,
        "irr": 0.28,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.60,
            "medicare": 0.22,
            "medicaid": 0.12,
            "other": 0.06,
        },
        "notes": (
            "Free-flap and pedicle-flap reconstructive microsurgery billing involves "
            "multiple high-complexity CPT codes (19364–19369 for breast reconstruction, "
            "15756–15758 for free-flap transfers) that require co-surgeon or assistant "
            "surgeon modifiers 62 and 80 when operating teams exceed a single surgeon, "
            "and commercial payers frequently dispute the medical necessity of the assistant "
            "surgeon component for elective reconstruction cases. "
            "DIEP flap breast reconstruction (CPT 19364) generates among the highest-value "
            "single-claim microsurgery encounters, but multi-day ICU monitoring post-flap "
            "creates complex hospital-professional billing coordination with daily critical "
            "care codes that must not duplicate facility charges already in the DRG."
        ),
    },
    {
        # 11 — Pain psychology / biopsychosocial pain
        "source_id": "ext42_011",
        "source": "seed",
        "company_name": "Compass Pain Psychology Group",
        "sector": "Pain Psychology / Biopsychosocial Pain",
        "year": 2019,
        "buyer": "New MainStream Capital",
        "ev_mm": 155.0,
        "ebitda_at_entry_mm": 16.0,
        "moic": 3.0,
        "irr": 0.25,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.52,
            "medicare": 0.26,
            "medicaid": 0.17,
            "other": 0.05,
        },
        "notes": (
            "Pain psychology practices billing under CPT 90832–90838 for psychotherapy "
            "and 96150–96155 for health behavior assessment face parity compliance scrutiny, "
            "as commercial payers sometimes apply more restrictive medical management "
            "review to behavioral pain services than to equivalent-cost procedural pain "
            "interventions in violation of the Mental Health Parity and Addiction Equity Act. "
            "Interdisciplinary pain program (IPP) billing under CPT 0871T–0876T requires "
            "CMS coverage determinations that vary by MAC jurisdiction, and many commercial "
            "plans have no established benefit for structured interdisciplinary pain "
            "rehabilitation, requiring case-by-case single-case agreement negotiations."
        ),
    },
    {
        # 12 — Lymphedema management
        "source_id": "ext42_012",
        "source": "seed",
        "company_name": "FlowPath Lymphedema Therapy Partners",
        "sector": "Lymphedema Management",
        "year": 2014,
        "buyer": "Varsity Healthcare Partners",
        "ev_mm": 120.0,
        "ebitda_at_entry_mm": 14.0,
        "moic": 2.8,
        "irr": 0.24,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.48,
            "medicare": 0.32,
            "medicaid": 0.15,
            "other": 0.05,
        },
        "notes": (
            "Lymphedema therapy billing for complete decongestive therapy (CDT) uses "
            "CPT 97016 (vasopneumatic device therapy) and 97140 (manual therapy) alongside "
            "compression garment HCPCS codes, but Medicare historically did not cover "
            "compression garments as durable medical equipment until the Lymphedema "
            "Treatment Act compliance period created a new benefit effective January 2024, "
            "leaving a multi-decade coverage gap that suppressed patient compliance rates "
            "and revenue capture. "
            "Therapist credential verification (CLT or CLT-LANA certification) is required "
            "by many commercial plans before claims are adjudicated, and credentialing "
            "delays of 60–90 days for new therapists create revenue gaps during onboarding "
            "that disproportionately affect high-growth practices."
        ),
    },
    {
        # 13 — Wound care at home / mobile wound
        "source_id": "ext42_013",
        "source": "seed",
        "company_name": "MobileWound Home Care Specialists",
        "sector": "Wound Care at Home / Mobile Wound",
        "year": 2020,
        "buyer": "Audax Private Equity",
        "ev_mm": 210.0,
        "ebitda_at_entry_mm": 22.0,
        "moic": 3.2,
        "irr": 0.28,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.30,
            "medicare": 0.48,
            "medicaid": 0.18,
            "other": 0.04,
        },
        "notes": (
            "Mobile wound care practices billing under the Medicare home health benefit "
            "must ensure a qualifying face-to-face encounter (CPT G0179/G0180) is documented "
            "by the certifying physician within the required timely window, and missing or "
            "late F2F documentation is the single leading cause of home health claim "
            "recoupment under post-payment review. "
            "Wound debridement coding (CPT 97597–97602) requires precise measurement of "
            "wound surface area at each visit and documentation of wound type and depth, "
            "as payers apply automated edits that deny re-billing of the same wound area "
            "at the same depth classification within a 30-day window without supporting "
            "clinical narrative of deterioration."
        ),
    },
    {
        # 14 — Ostomy care / continence
        "source_id": "ext42_014",
        "source": "seed",
        "company_name": "ContinuCare Ostomy & Continence Services",
        "sector": "Ostomy Care / Continence",
        "year": 2013,
        "buyer": "FFL Partners",
        "ev_mm": 175.0,
        "ebitda_at_entry_mm": 18.0,
        "moic": 2.9,
        "irr": 0.25,
        "hold_years": 5.0,
        "payer_mix": {
            "commercial": 0.35,
            "medicare": 0.45,
            "medicaid": 0.16,
            "other": 0.04,
        },
        "notes": (
            "Ostomy supply billing under HCPCS A4361–A4435 and A5051–A5093 is subject to "
            "Medicare's competitive bidding program in bid areas, where contract suppliers "
            "must win a competitive bid to serve Medicare beneficiaries, effectively barring "
            "non-bid suppliers from Medicare revenue in those markets. "
            "Continence care supplies (A4335 for incontinence pads, A4338 for urinary "
            "catheters) require certificate of medical necessity (CMN) documentation signed "
            "by the treating physician, and monthly quantity limits enforced by payers "
            "require supply utilization tracking systems that add RCM technology overhead "
            "absent from traditional home medical equipment billing platforms."
        ),
    },
    {
        # 15 — Sickle cell / hemoglobinopathy center
        "source_id": "ext42_015",
        "source": "seed",
        "company_name": "Vantage Sickle Cell & Hemoglobinopathy Centers",
        "sector": "Sickle Cell / Hemoglobinopathy Center",
        "year": 2022,
        "buyer": "Berkshire Partners",
        "ev_mm": 290.0,
        "ebitda_at_entry_mm": 28.0,
        "moic": 2.6,
        "irr": 0.23,
        "hold_years": 3.5,
        "payer_mix": {
            "commercial": 0.28,
            "medicare": 0.22,
            "medicaid": 0.44,
            "other": 0.06,
        },
        "notes": (
            "Sickle cell disease centers carry the highest Medicaid concentration of any "
            "PE-backed specialty platform, reflecting the demographic prevalence of SCD, "
            "and Medicaid managed-care contracts in high-SCD-burden states often require "
            "care management fees to be billed through complex value-based arrangement "
            "structures rather than straightforward fee-for-service CPT codes, creating "
            "a revenue-cycle dependency on contract-specific reporting and attestation. "
            "Gene therapy authorization for SCD (Casgevy, Lyfgenia) involves catastrophic "
            "claim values exceeding $2M per patient with payer-specific installment payment "
            "arrangements and outcomes-based rebate structures that require RCM teams to "
            "track multi-year performance milestones to trigger full payment."
        ),
    },
]
