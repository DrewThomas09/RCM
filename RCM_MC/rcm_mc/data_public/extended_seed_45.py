"""Extended seed deals – batch 45.

Covers niche behavioral health, rehabilitation, and durable medical equipment
sectors with distinct RCM/billing complexity profiles.
"""

EXTENDED_SEED_DEALS_45 = [
    {
        "source_id": "ext45_001",
        "source": "seed",
        "company_name": "RecoveryBridge SUD Outpatient Centers",
        "sector": "Addiction Medicine / SUD Outpatient (Non-Residential)",
        "year": 2018,
        "buyer": "Nautic Partners",
        "ev_mm": 210.0,
        "ebitda_at_entry_mm": 21.0,
        "moic": 3.2,
        "irr": 0.28,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.38,
            "medicare": 0.10,
            "medicaid": 0.45,
            "other": 0.07,
        },
        "notes": (
            "SUD outpatient billing requires matching CPT codes for individual vs. group "
            "therapy, ASAM level-of-care documentation, and state-specific Medicaid "
            "substance-use carve-out authorizations. Denials spike when intake assessments "
            "lack LCSW or LADC co-signature requirements mandated by payer contracts."
        ),
    },
    {
        "source_id": "ext45_002",
        "source": "seed",
        "company_name": "HarborLight OTP Network",
        "sector": "Methadone Clinic / OTP Network",
        "year": 2016,
        "buyer": "Riverside Partners",
        "ev_mm": 145.0,
        "ebitda_at_entry_mm": 14.5,
        "moic": 3.5,
        "irr": 0.30,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.18,
            "medicare": 0.12,
            "medicaid": 0.62,
            "other": 0.08,
        },
        "notes": (
            "OTP networks bill a bundled daily methadone dispensing fee under HCPCS H0020, "
            "but Medicaid rates vary dramatically by state and many programs operate under "
            "fee-for-service carve-outs that require separate credentialing from MCOs. "
            "Counseling sessions must be separately documented and billed to avoid bundling "
            "denials from Medicaid managed-care plans."
        ),
    },
    {
        "source_id": "ext45_003",
        "source": "seed",
        "company_name": "Ascend Adolescent Behavioral Health",
        "sector": "Adolescent Behavioral Health",
        "year": 2019,
        "buyer": "Shore Capital Partners",
        "ev_mm": 185.0,
        "ebitda_at_entry_mm": 18.5,
        "moic": 3.8,
        "irr": 0.33,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.52,
            "medicare": 0.04,
            "medicaid": 0.38,
            "other": 0.06,
        },
        "notes": (
            "Adolescent behavioral health billing is complicated by HIPAA minor-consent "
            "rules that can prevent parental insurance use, requiring self-pay or Medicaid "
            "as alternative payers mid-episode. Residential vs. outpatient level-of-care "
            "determinations trigger prior-authorization battles with commercial payers "
            "citing medical-necessity criteria inconsistent with ASAM guidelines."
        ),
    },
    {
        "source_id": "ext45_004",
        "source": "seed",
        "company_name": "ElderMind Geriatric Psychiatry Group",
        "sector": "Geriatric Psychiatry",
        "year": 2017,
        "buyer": "Frazier Healthcare Partners",
        "ev_mm": 155.0,
        "ebitda_at_entry_mm": 15.5,
        "moic": 3.1,
        "irr": 0.27,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.22,
            "medicare": 0.58,
            "medicaid": 0.14,
            "other": 0.06,
        },
        "notes": (
            "Geriatric psychiatry practices depend heavily on Medicare Part B, where the "
            "2013 psychiatric billing overhaul replaced 90-minute psychotherapy add-ons "
            "with time-based E&M codes, requiring precise documentation of medical decision "
            "making alongside psychotherapy minutes. Incident-to billing restrictions for "
            "mid-level providers further constrain revenue capture in nursing-facility settings."
        ),
    },
    {
        "source_id": "ext45_005",
        "source": "seed",
        "company_name": "MindBridge Telepsychiatry Platform",
        "sector": "Telepsychiatry Platforms",
        "year": 2020,
        "buyer": "Warburg Pincus",
        "ev_mm": 520.0,
        "ebitda_at_entry_mm": 48.0,
        "moic": 4.0,
        "irr": 0.36,
        "hold_years": 3.5,
        "payer_mix": {
            "commercial": 0.60,
            "medicare": 0.20,
            "medicaid": 0.15,
            "other": 0.05,
        },
        "notes": (
            "Telepsychiatry platforms face a fragmented reimbursement landscape where "
            "originating-site rules, audio-only vs. audio-visual modality distinctions, "
            "and state parity-law enforcement vary by payer and jurisdiction. Post-pandemic "
            "permanent vs. temporary telehealth waivers created billing-code uncertainty "
            "that drove elevated claim-edit rates across commercial contracts."
        ),
    },
    {
        "source_id": "ext45_006",
        "source": "seed",
        "company_name": "StabilisCenter Psychiatric Urgent Care",
        "sector": "Crisis Stabilization / Psychiatric Urgent Care",
        "year": 2021,
        "buyer": "New MainStream Capital",
        "ev_mm": 175.0,
        "ebitda_at_entry_mm": 16.5,
        "moic": 2.8,
        "irr": 0.24,
        "hold_years": 3.5,
        "payer_mix": {
            "commercial": 0.33,
            "medicare": 0.15,
            "medicaid": 0.47,
            "other": 0.05,
        },
        "notes": (
            "Crisis stabilization units bill under facility-based revenue codes but often "
            "lack the licensed-bed designation needed for inpatient DRG reimbursement, "
            "leaving revenue at lower observation or outpatient facility rates. CCBHC "
            "Medicaid prospective payment adoption is uneven, creating dual-coding burdens "
            "for practices transitioning between fee-for-service and bundled models."
        ),
    },
    {
        "source_id": "ext45_007",
        "source": "seed",
        "company_name": "RenewPath Eating Disorder PHP/IOP Network",
        "sector": "Eating Disorder / PHP/IOP Residential",
        "year": 2018,
        "buyer": "Behavioral Healthcare Capital",
        "ev_mm": 240.0,
        "ebitda_at_entry_mm": 24.0,
        "moic": 3.6,
        "irr": 0.31,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.68,
            "medicare": 0.06,
            "medicaid": 0.20,
            "other": 0.06,
        },
        "notes": (
            "Eating disorder programs bill across PHP (H0035), IOP (H2036), and residential "
            "levels simultaneously as patients step down, requiring level-of-care "
            "re-authorization every 7–14 days under most commercial contracts. Mental health "
            "parity litigation has pressured insurers but concurrent-review denials and "
            "retrospective claim audits remain a primary revenue-cycle risk."
        ),
    },
    {
        "source_id": "ext45_008",
        "source": "seed",
        "company_name": "NeuroReclaim TBI Rehab Centers",
        "sector": "Traumatic Brain Injury / Neurobehavioral Rehab",
        "year": 2015,
        "buyer": "ABRY Partners",
        "ev_mm": 190.0,
        "ebitda_at_entry_mm": 19.0,
        "moic": 3.3,
        "irr": 0.29,
        "hold_years": 5.0,
        "payer_mix": {
            "commercial": 0.42,
            "medicare": 0.28,
            "medicaid": 0.20,
            "other": 0.10,
        },
        "notes": (
            "TBI neurobehavioral rehab billing straddles physical medicine CPT codes and "
            "neuropsychological testing codes, with Medicare Part A vs. Part B distinctions "
            "determining facility vs. professional billing pathways. Workers' comp and "
            "auto-liability payers, which comprise a meaningful share of the 'other' mix, "
            "require case-management coordination and lien-resolution workflows that add "
            "significant days to cash collection."
        ),
    },
    {
        "source_id": "ext45_009",
        "source": "seed",
        "company_name": "InclusionPath I/DD Waiver Services",
        "sector": "Intellectual Disability Services / I/DD Waiver",
        "year": 2016,
        "buyer": "Sterling Partners",
        "ev_mm": 130.0,
        "ebitda_at_entry_mm": 13.0,
        "moic": 3.0,
        "irr": 0.26,
        "hold_years": 5.0,
        "payer_mix": {
            "commercial": 0.06,
            "medicare": 0.08,
            "medicaid": 0.82,
            "other": 0.04,
        },
        "notes": (
            "I/DD waiver services are billed under state-specific Home and Community-Based "
            "Services (HCBS) waiver codes with unit-based rather than time-based rates, "
            "making accurate time-tracking and EVV electronic visit verification compliance "
            "essential to preventing Medicaid recoupment. Annual waiver re-enrollment and "
            "person-centered plan updates must be documented within strict state-mandated "
            "deadlines to maintain billable eligibility."
        ),
    },
    {
        "source_id": "ext45_010",
        "source": "seed",
        "company_name": "SparkABA Autism Outpatient Group",
        "sector": "Autism Spectrum / ABA Outpatient (Non-Residential)",
        "year": 2019,
        "buyer": "Lee Equity Partners",
        "ev_mm": 380.0,
        "ebitda_at_entry_mm": 35.0,
        "moic": 4.2,
        "irr": 0.37,
        "hold_years": 3.5,
        "payer_mix": {
            "commercial": 0.55,
            "medicare": 0.03,
            "medicaid": 0.38,
            "other": 0.04,
        },
        "notes": (
            "ABA outpatient billing relies on HCPCS H-codes (H2019, H2014) and CPT 97151–"
            "97158, with commercial payer contracts often capping covered hours annually "
            "and requiring behavior analyst supervision ratios to be documented at every "
            "session. Medicaid ABA billing adds EPSDT mandates that obligate coverage but "
            "require separate prior-authorization pathways across managed-care organizations."
        ),
    },
    {
        "source_id": "ext45_011",
        "source": "seed",
        "company_name": "ClearChannel Deaf & HoH Communication Services",
        "sector": "Deaf/Hard of Hearing / Communication Support",
        "year": 2014,
        "buyer": "Consonance Capital Partners",
        "ev_mm": 80.0,
        "ebitda_at_entry_mm": 8.0,
        "moic": 3.0,
        "irr": 0.27,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.30,
            "medicare": 0.35,
            "medicaid": 0.25,
            "other": 0.10,
        },
        "notes": (
            "Deaf and hard-of-hearing service providers bill audiological rehabilitation "
            "CPT codes alongside sign-language interpreter facilitation fees, but payers "
            "rarely reimburse interpreter costs directly, requiring creative bundling or "
            "grant-funded cost offsets. Medicare coverage for aural rehabilitation (V5362, "
            "92626) is narrow and frequently confused with hearing-aid dispensing exclusions, "
            "generating high initial-denial rates requiring robust appeal workflows."
        ),
    },
    {
        "source_id": "ext45_012",
        "source": "seed",
        "company_name": "BrightSight Vision Rehabilitation Centers",
        "sector": "Vision Rehabilitation",
        "year": 2017,
        "buyer": "Thurston Group",
        "ev_mm": 95.0,
        "ebitda_at_entry_mm": 9.5,
        "moic": 2.9,
        "irr": 0.25,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.35,
            "medicare": 0.42,
            "medicaid": 0.15,
            "other": 0.08,
        },
        "notes": (
            "Vision rehabilitation therapy (CPT 97003, 92065) sits at the intersection of "
            "ophthalmology and occupational therapy, with Medicare Part B covering low-vision "
            "aids under DME benefit rules while therapeutic services are billed under "
            "the outpatient rehabilitation benefit. Dual-benefit coordination and modifier "
            "usage (GO vs. GN) create frequent claim-edit errors that require specialty "
            "billing expertise to resolve."
        ),
    },
    {
        "source_id": "ext45_013",
        "source": "seed",
        "company_name": "VoiceForward AAC & Assistive Technology",
        "sector": "Assistive Technology / AAC (Augmentative Communication)",
        "year": 2015,
        "buyer": "Serent Capital",
        "ev_mm": 110.0,
        "ebitda_at_entry_mm": 11.0,
        "moic": 3.4,
        "irr": 0.29,
        "hold_years": 5.0,
        "payer_mix": {
            "commercial": 0.40,
            "medicare": 0.30,
            "medicaid": 0.24,
            "other": 0.06,
        },
        "notes": (
            "AAC device claims require a detailed written order from a physician plus a "
            "speech-language pathology evaluation confirming medical necessity under "
            "Medicare's DME speech-generating device rules (HCPCS E2500–E2599). Commercial "
            "payers have inconsistent coverage policies for dedicated AAC devices vs. "
            "tablet-based apps, and Medicaid requires EPSDT or state plan amendment "
            "authority, creating a multi-payer billing matrix with high denial variability."
        ),
    },
    {
        "source_id": "ext45_014",
        "source": "seed",
        "company_name": "ApexLimb Prosthetics & Orthotics Group",
        "sector": "Prosthetics and Orthotics (O&P)",
        "year": 2020,
        "buyer": "Kinderhook Industries",
        "ev_mm": 320.0,
        "ebitda_at_entry_mm": 29.0,
        "moic": 3.7,
        "irr": 0.32,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.38,
            "medicare": 0.45,
            "medicaid": 0.12,
            "other": 0.05,
        },
        "notes": (
            "O&P billing under Medicare requires functional classification (K-level) "
            "documentation for lower-limb prosthetics and must conform to the L-code "
            "HCPCS system where components are billed individually or as base-plus-additions, "
            "creating significant charge-capture complexity for multi-component devices. "
            "Post-2015 competitive bidding exclusion for custom O&P preserved fee-schedule "
            "rates but heightened auditor scrutiny around medical-necessity documentation "
            "and claims of off-the-shelf vs. custom-fabricated designations."
        ),
    },
    {
        "source_id": "ext45_015",
        "source": "seed",
        "company_name": "MobilityFirst DME & Complex Rehab Technology",
        "sector": "Durable Medical Equipment / Complex Rehab Technology",
        "year": 2013,
        "buyer": "H.I.G. Capital",
        "ev_mm": 430.0,
        "ebitda_at_entry_mm": 40.0,
        "moic": 3.9,
        "irr": 0.34,
        "hold_years": 5.5,
        "payer_mix": {
            "commercial": 0.28,
            "medicare": 0.52,
            "medicaid": 0.15,
            "other": 0.05,
        },
        "notes": (
            "Complex rehab technology billing under Medicare requires CRT-specific HCPCS "
            "codes (K0835–K0864 for power wheelchairs) with a face-to-face examination, "
            "written order, and detailed product-description letter before delivery, and "
            "competitive bidding program exclusions for CRT must be actively maintained "
            "through accreditation cycles. Capped rental vs. purchase election rules for "
            "standard DME items create ongoing beneficiary-communication requirements and "
            "downstream ownership-transfer billing milestones that generate collections risk."
        ),
    },
]
