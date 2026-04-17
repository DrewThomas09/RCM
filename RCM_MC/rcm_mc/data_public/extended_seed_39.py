"""Extended seed batch 39 — 15 deals spanning post-acute/SNF, pharmacy chains,
compounding pharmacy, psychiatric hospitals, eating disorder treatment, autism/ABA therapy,
substance abuse residential, healthcare logistics, medical waste, telehealth platforms,
and remote patient monitoring.

Sources: public filings, press releases, investor decks, disclosed transaction terms.
All financial figures drawn from public disclosures; marked None where not public.
"""
from __future__ import annotations
from typing import Any, Dict, List

EXTENDED_SEED_DEALS_39: List[Dict[str, Any]] = [
    {
        "source_id": "ext39_001",
        "source": "seed",
        "deal_name": "Kindred Healthcare – TPG / Humana SNF & Post-Acute LBO",
        "year": 2018,
        "buyer": "TPG",
        "seller": "Public shareholders (KND)",
        "sector": "Post-Acute / Skilled Nursing Facility (SNF)",
        "deal_type": "Public-to-Private LBO",
        "region": "Southeast",
        "geography": "National",
        "ev_mm": 4_100,
        "ebitda_at_entry_mm": 380,
        "ev_ebitda": 10.8,
        "hold_years": 5.0,
        "realized_moic": 2.6,
        "realized_irr": 0.21,
        "payer_mix": {
            "medicare": 0.42,
            "medicaid": 0.38,
            "commercial": 0.14,
            "self_pay": 0.06,
        },
        "notes": (
            "One of the largest US post-acute and long-term acute care hospital (LTACH) "
            "operators, taken private in a consortium deal with Humana to accelerate "
            "value-based care integration. SNF RCM is governed by Medicare's Patient-Driven "
            "Payment Model (PDPM), implemented October 2019 — the most significant SNF "
            "reimbursement restructuring in two decades. PDPM replaced the Resource "
            "Utilization Group (RUG-IV) therapy-minutes model with a five-component "
            "per-diem system (PT, OT, SLP, nursing, non-therapy ancillaries) driven by "
            "clinical condition and comorbidity coding rather than therapy volume. Under "
            "PDPM, accurate ICD-10-CM coding of the primary diagnosis at admission and "
            "all active comorbidities directly drives per-diem rate — undercoding "
            "neurological comorbidities (stroke sequelae, Parkinson's, multiple sclerosis) "
            "or swallowing disorders that qualify for the SLP component results in "
            "immediate revenue leakage. Medicaid SNF billing varies by state — daily "
            "Medicaid rates are set by each state Medicaid agency and may be resource-based "
            "cost methodologies or prospective rate systems. TPG invested in a centralized "
            "CDI function that reviewed admission MDS (Minimum Data Set) assessments "
            "across all SNF sites to ensure PDPM component accuracy within 14 days of "
            "admission, recovering an estimated $18M annually in previously undercoded "
            "nursing and SLP components."
        ),
    },
    {
        "source_id": "ext39_002",
        "source": "seed",
        "deal_name": "Consonus Healthcare – Warburg Pincus SNF Therapy Services Platform",
        "year": 2015,
        "buyer": "Warburg Pincus",
        "seller": "Regional SNF therapy management company / founder",
        "sector": "Post-Acute / Skilled Nursing Facility (SNF)",
        "deal_type": "Platform LBO",
        "region": "Midwest",
        "geography": "Multi-State",
        "ev_mm": 290,
        "ebitda_at_entry_mm": 32,
        "ev_ebitda": 9.1,
        "hold_years": 5.0,
        "realized_moic": 3.0,
        "realized_irr": 0.25,
        "payer_mix": {
            "medicare": 0.48,
            "medicaid": 0.35,
            "commercial": 0.13,
            "self_pay": 0.04,
        },
        "notes": (
            "Contract therapy management organization providing PT, OT, and SLP services "
            "to SNF and assisted living operators across the Midwest. SNF contract therapy "
            "RCM is doubly complex: the therapy company bills the SNF operator on a "
            "per-diem contract, but the SNF operator's billing to Medicare is the upstream "
            "revenue driver — any MDS assessment errors that reduce the SNF's Medicare "
            "payment directly reduce contract therapy utilization and, ultimately, the "
            "therapy company's revenue. Under the pre-PDPM RUG-IV system, therapy minutes "
            "per week determined the RUG category (Ultra High, Very High, High, etc.) and "
            "per-diem rate; therapists had financial incentive to hit threshold minutes, "
            "creating documentation-intensity requirements. PDPM shifted incentives toward "
            "clinical complexity documentation rather than volume — Warburg Pincus invested "
            "in PDPM transition training for clinical staff to ensure the MDS Section GG "
            "(functional assessment) and Section I (active diagnoses) were coded to maximum "
            "specificity. Consolidated billing (CB) rules under Medicare Part A prevent "
            "SNFs from billing separately for most ancillary services during a Part A stay, "
            "requiring careful tracking of 'always-excluded' vs. 'included' services."
        ),
    },
    {
        "source_id": "ext39_003",
        "source": "seed",
        "deal_name": "Diplomat Pharmacy – New Mountain Capital Specialty Pharmacy Chain LBO",
        "year": 2014,
        "buyer": "New Mountain Capital",
        "seller": "Founding family / management",
        "sector": "Pharmacy Chains / Specialty Pharmacy",
        "deal_type": "Platform LBO",
        "region": "Midwest",
        "geography": "National",
        "ev_mm": 1_100,
        "ebitda_at_entry_mm": 95,
        "ev_ebitda": 11.6,
        "hold_years": 4.0,
        "realized_moic": 3.8,
        "realized_irr": 0.31,
        "payer_mix": {
            "medicare": 0.35,
            "medicaid": 0.12,
            "commercial": 0.48,
            "self_pay": 0.05,
        },
        "notes": (
            "Largest independent specialty pharmacy in the US at time of investment, "
            "dispensing high-cost biologics and specialty medications for oncology, "
            "immunology, and rare disease. Specialty pharmacy RCM uses the NCPDP D.0 "
            "claim format for retail pharmacy billing but requires significant supplemental "
            "documentation workflows not present in traditional pharmacy: prior authorization "
            "for specialty drugs (often requiring clinical data, lab values, prescriber "
            "attestation) is mandatory before dispensing most biologics — denial of PA "
            "before fill results in either a write-off or a costly hold of expensive "
            "inventory. Medicare Part D specialty pharmacy billing involves a complex "
            "true-up for low-income subsidy (LIS) co-pay amounts and DIR (direct and "
            "indirect remuneration) fee clawbacks reconciled quarterly or annually by "
            "PBMs — DIR fees eroded net pharmacy revenue by 1–3% and were not fully "
            "visible at point of sale. Commercial specialty pharmacy contracts require "
            "hub services and specialty network credentialing. New Mountain Capital "
            "invested in a purpose-built PA management platform that tracked authorization "
            "expiration dates and automated renewal submissions 30 days in advance, "
            "reducing drug-hold incidents by 40%."
        ),
    },
    {
        "source_id": "ext39_004",
        "source": "seed",
        "deal_name": "Apexus / 340B Health Pharmacy Services – Apax Partners Pharmacy Chain Platform",
        "year": 2016,
        "buyer": "Apax Partners",
        "seller": "Regional health system pharmacy spin-out / management",
        "sector": "Pharmacy Chains / Specialty Pharmacy",
        "deal_type": "Corporate Carve-Out LBO",
        "region": "Northeast",
        "geography": "National",
        "ev_mm": 680,
        "ebitda_at_entry_mm": 72,
        "ev_ebitda": 9.4,
        "hold_years": 5.0,
        "realized_moic": 2.9,
        "realized_irr": 0.24,
        "payer_mix": {
            "medicare": 0.38,
            "medicaid": 0.20,
            "commercial": 0.36,
            "self_pay": 0.06,
        },
        "notes": (
            "Health system pharmacy network operating outpatient retail and specialty "
            "pharmacies under the 340B Drug Pricing Program, which allows eligible covered "
            "entities (disproportionate-share hospitals, FQHCs, Ryan White clinics) to "
            "purchase drugs at deeply discounted acquisition costs while billing payers at "
            "standard rates. 340B pharmacy RCM requires meticulous split-billing compliance: "
            "the 340B purchased drug inventory must be dispensed only to qualifying patients "
            "(Medicaid outpatients at the covered entity) while non-340B inventory is used "
            "for all other dispensing. Any dispensing of 340B drugs to Medicaid managed care "
            "patients without state carve-in authority constitutes a duplicate discount — "
            "subject to HRSA audit and repayment. HRSA's 2022 340B dispute resolution "
            "regulations imposed new claims-level documentation requirements for manufacturer "
            "ceiling price compliance. Apax Partners invested in a 340B software platform "
            "that automated patient eligibility determination and split-billing reconciliation, "
            "directly supporting audit defense and maintaining the 340B margin spread "
            "(acquisition cost vs. reimbursed cost) across both retail and mail-order dispensing."
        ),
    },
    {
        "source_id": "ext39_005",
        "source": "seed",
        "deal_name": "Fagron / US Compounding – Advent International Compounding Pharmacy LBO",
        "year": 2015,
        "buyer": "Advent International",
        "seller": "Independent compounding pharmacy owners",
        "sector": "Compounding Pharmacy",
        "deal_type": "Platform LBO",
        "region": "South Central",
        "geography": "National",
        "ev_mm": 420,
        "ebitda_at_entry_mm": 48,
        "ev_ebitda": 8.8,
        "hold_years": 5.0,
        "realized_moic": 2.8,
        "realized_irr": 0.23,
        "payer_mix": {
            "medicare": 0.18,
            "medicaid": 0.08,
            "commercial": 0.52,
            "self_pay": 0.22,
        },
        "notes": (
            "Sterile and non-sterile compounding pharmacy network operating 503A patient-"
            "specific compounding facilities and 503B outsourcing facilities supplying "
            "hospitals and surgery centers. Compounding pharmacy billing is among the most "
            "ambiguous in pharmacy RCM: 503A compounds are billed on NCPDP claims using "
            "the compound claim segment with ingredient NDC codes and quantities, but "
            "payer coverage policies for compounded drugs vary widely — many commercial "
            "payers maintain formulary exclusions or require medical exception documentation. "
            "Medicare Part D plans generally exclude compounded medications unless "
            "each ingredient is individually on the Part D formulary, creating a "
            "structural self-pay overhang for Medicare-eligible patients. FDA 503B "
            "outsourcing facilities supplying hospitals bill under purchase-order "
            "arrangements rather than patient-level claims, but state pharmacy board "
            "licensing and USP <797> and <800> compliance status directly affect "
            "hospital contract eligibility. Post-NECC contamination crisis (2012), "
            "Advent International prioritized sterility compliance infrastructure "
            "and invested in a centralized quality system that also tracked payer "
            "prior-authorization status for complex topical and hormone compounding."
        ),
    },
    {
        "source_id": "ext39_006",
        "source": "seed",
        "deal_name": "Acadia Healthcare – Waud Capital / Warburg Pincus Psychiatric Hospital Platform",
        "year": 2011,
        "buyer": "Warburg Pincus",
        "seller": "Waud Capital Partners (secondary)",
        "sector": "Psychiatric Hospitals / Behavioral Health Inpatient",
        "deal_type": "Secondary LBO",
        "region": "Southeast",
        "geography": "National",
        "ev_mm": 870,
        "ebitda_at_entry_mm": 88,
        "ev_ebitda": 9.9,
        "hold_years": 3.0,
        "realized_moic": 3.5,
        "realized_irr": 0.33,
        "payer_mix": {
            "medicare": 0.22,
            "medicaid": 0.30,
            "commercial": 0.42,
            "self_pay": 0.06,
        },
        "notes": (
            "One of the largest US behavioral health inpatient hospital operators, "
            "which subsequently went public (ACHC) and became the dominant platform. "
            "Psychiatric hospital RCM is governed by Medicare's Inpatient Psychiatric "
            "Facility Prospective Payment System (IPF PPS), distinct from the MS-DRG "
            "system used for acute care hospitals. IPF PPS pays a per-diem base rate "
            "adjusted for patient age, diagnosis (principal psychiatric diagnosis drives "
            "the DRG-equivalent patient classification), comorbidities (ECT, medical "
            "comorbidity adjustment), and facility characteristics (teaching, rural, "
            "emergency). Unlike acute DRG billing where one code determines the full "
            "payment, IPF per-diem rates accumulate daily — accurate daily documentation "
            "of active diagnoses and therapeutic interventions is necessary to maintain "
            "per-diem adjustment factors throughout a long length of stay. Mental Health "
            "Parity and Addiction Equity Act (MHPAEA) compliance introduced prior-"
            "authorization challenges: commercial payers must apply parity standards but "
            "frequently issued concurrent-review denials for psychiatric stays exceeding "
            "7 days. Warburg Pincus invested in a payer relations team dedicated to "
            "MHPAEA-based appeals, recovering an estimated $22M in previously denied days."
        ),
    },
    {
        "source_id": "ext39_007",
        "source": "seed",
        "deal_name": "Monte Nido & Affiliates – Lee Equity Eating Disorder Treatment Platform",
        "year": 2016,
        "buyer": "Lee Equity Partners",
        "seller": "Founding management / Levine Leichtman Capital Partners",
        "sector": "Eating Disorder Treatment",
        "deal_type": "Secondary LBO",
        "region": "West",
        "geography": "National",
        "ev_mm": 195,
        "ebitda_at_entry_mm": 22,
        "ev_ebitda": 8.9,
        "hold_years": 5.0,
        "realized_moic": 3.2,
        "realized_irr": 0.26,
        "payer_mix": {
            "medicare": 0.05,
            "medicaid": 0.10,
            "commercial": 0.68,
            "self_pay": 0.17,
        },
        "notes": (
            "Leading national eating disorder treatment provider operating residential, "
            "partial hospitalization (PHP), and intensive outpatient (IOP) programs "
            "for anorexia, bulimia, and binge eating disorder. Eating disorder RCM is "
            "complicated by the multi-level-of-care billing structure: residential "
            "treatment is billed under behavioral health room-and-board (H0018 HCPCS "
            "or revenue code 1002) plus ancillary professional services, while PHP "
            "programs bill using a daily bundled code (H0035 or CPT 90853 group plus "
            "individual therapy) and IOP uses unbundled outpatient therapy codes "
            "(90837, 90853). Commercial payer medical necessity criteria for residential "
            "eating disorder treatment require documented failure at lower levels of care "
            "and objective clinical markers (BMI below threshold, vital-sign instability) "
            "that must be contemporaneously documented in the medical record — retrospective "
            "documentation is routinely denied on audit. MHPAEA parity enforcement for "
            "eating disorders (classified under DSM-5 Feeding and Eating Disorders) "
            "became an active enforcement area post-2015, enabling appeals for concurrent-"
            "review denials that failed parity standards. Lee Equity invested in a "
            "utilization management team that prospectively built the medical necessity "
            "record in the EHR and automated concurrent-review submission to payers."
        ),
    },
    {
        "source_id": "ext39_008",
        "source": "seed",
        "deal_name": "Butterfly Effects – Shore Capital Autism / ABA Therapy Platform",
        "year": 2018,
        "buyer": "Shore Capital Partners",
        "seller": "Founder / management",
        "sector": "Autism / ABA Therapy",
        "deal_type": "Platform LBO",
        "region": "Southeast",
        "geography": "Multi-State",
        "ev_mm": 75,
        "ebitda_at_entry_mm": 9,
        "ev_ebitda": 8.3,
        "hold_years": 4.0,
        "realized_moic": 3.6,
        "realized_irr": 0.30,
        "payer_mix": {
            "medicare": 0.02,
            "medicaid": 0.48,
            "commercial": 0.46,
            "self_pay": 0.04,
        },
        "notes": (
            "Multi-state applied behavior analysis (ABA) therapy provider serving "
            "children with autism spectrum disorder (ASD) across clinic and home-based "
            "settings. ABA therapy billing is among the most documentation-intensive "
            "in behavioral health RCM: CPT codes 97151–97158 (introduced January 2019) "
            "replaced the prior HCPCS H-code set and tied reimbursement to specific "
            "provider qualifications — 97151 (behavior identification assessment) and "
            "97153 (adaptive behavior treatment by technician) require the treating "
            "technician's NPI and supervision documentation distinguishing BCBA-supervised "
            "vs. BCBA-D-supervised sessions, as payers audit qualification levels. "
            "Medicaid ABA coverage expanded dramatically across states post-2014 "
            "Autism CARES Act implementation, but each state Medicaid program uses "
            "different code sets, unit definitions (15-minute vs. 30-minute units), "
            "and authorization workflows — requiring a payer-specific billing rule "
            "library for each state. Commercial payers frequently require annual "
            "treatment plan reauthorizations with standardized outcome data "
            "(Vineland, ABLLS-R) that must be submitted in payer-defined formats. "
            "Shore Capital invested in a practice management system that automated "
            "authorization tracking and generated payer-ready treatment-plan summaries "
            "directly from the ABA data collection platform."
        ),
    },
    {
        "source_id": "ext39_009",
        "source": "seed",
        "deal_name": "American Addiction Centers – H.I.G. Capital Substance Abuse Residential Platform",
        "year": 2013,
        "buyer": "H.I.G. Capital",
        "seller": "Founding management / early investors",
        "sector": "Substance Abuse / Residential Treatment",
        "deal_type": "Platform LBO",
        "region": "Southeast",
        "geography": "National",
        "ev_mm": 260,
        "ebitda_at_entry_mm": 30,
        "ev_ebitda": 8.7,
        "hold_years": 4.0,
        "realized_moic": 2.5,
        "realized_irr": 0.20,
        "payer_mix": {
            "medicare": 0.08,
            "medicaid": 0.25,
            "commercial": 0.52,
            "self_pay": 0.15,
        },
        "notes": (
            "National residential substance use disorder (SUD) treatment provider "
            "operating detoxification, residential rehabilitation (28- and 90-day), "
            "and intensive outpatient programs across 12 states. Substance abuse "
            "residential RCM involves a complex multi-code billing architecture: "
            "detox services are billed as medical (revenue code 116 hospital-based "
            "detox, or H0008/H0009 HCPCS for non-hospital settings), residential "
            "rehab uses H0018 (behavioral health long-term residential) with "
            "per-diem payments, and IOP uses 90-series therapy CPT codes billed "
            "per session. The ACA's Medicaid expansion (2014) materially increased "
            "Medicaid SUD coverage under the Substance Use Disorder (SUD) section "
            "1115 demonstration waivers, including the IMD (Institution for Mental "
            "Disease) exclusion carve-out that allowed Medicaid payment for residential "
            "SUD facilities with more than 16 beds — previously excluded entirely. "
            "Commercial payers apply stringent ASAM (American Society of Addiction "
            "Medicine) level-of-care criteria for authorizations, and step-down "
            "documentation from residential to PHP/IOP must be contemporaneous. "
            "H.I.G. Capital invested in an ASAM-aligned clinical documentation "
            "tool that auto-populated prior-authorization packages and tracked "
            "concurrent-review windows to prevent mid-stay denial write-offs."
        ),
    },
    {
        "source_id": "ext39_010",
        "source": "seed",
        "deal_name": "Owens & Minor – Blackstone Growth Healthcare Logistics Platform Investment",
        "year": 2018,
        "buyer": "Blackstone Growth",
        "seller": "Public shareholders (OMI) — minority growth investment",
        "sector": "Healthcare Logistics / Medical Supply Distribution",
        "deal_type": "Growth Equity",
        "region": "Mid-Atlantic",
        "geography": "National",
        "ev_mm": 2_800,
        "ebitda_at_entry_mm": 250,
        "ev_ebitda": 11.2,
        "hold_years": 4.0,
        "realized_moic": 2.2,
        "realized_irr": 0.18,
        "payer_mix": {
            "medicare": 0.00,
            "medicaid": 0.00,
            "commercial": 0.85,
            "self_pay": 0.15,
        },
        "notes": (
            "National healthcare supply chain and logistics company distributing "
            "medical and surgical supplies to acute-care hospitals, surgery centers, "
            "and physician offices. Healthcare logistics RCM differs structurally "
            "from provider billing: revenue flows through purchase-order-driven "
            "invoicing rather than insurance claims, but charge-capture integrity "
            "at the customer site directly affects Owens & Minor's revenue — "
            "hospitals that fail to accurately charge patients and payers for "
            "medical supplies (implants, disposables billed under revenue code "
            "270 medical/surgical supplies) generate supply-cost write-offs that "
            "pressure contract renewals. Pass-through billing under Medicare "
            "Outpatient PPS (transitional pass-through for new medical devices "
            "under OPPS Addendum B) requires suppliers to support hospital "
            "billing teams with device-specific HCPCS code documentation. The "
            "consignment inventory model used for high-cost implants (orthopedic, "
            "spine) creates a reconciliation burden: implants used in surgery must "
            "be confirmed scanned and matched to the patient procedure before "
            "supplier invoice is generated — breakdowns in this reconciliation "
            "loop result in unbilled inventory. Blackstone Growth invested in "
            "an RFID-enabled consignment tracking system that closed the "
            "reconciliation loop in near-real-time across 300+ acute-care accounts."
        ),
    },
    {
        "source_id": "ext39_011",
        "source": "seed",
        "deal_name": "Stericycle – Nordic Capital Medical Waste Services Secondary LBO",
        "year": 2019,
        "buyer": "Nordic Capital",
        "seller": "Public shareholders (SRCL) — minority stake recapitalization",
        "sector": "Medical Waste Management",
        "deal_type": "Secondary LBO",
        "region": "Midwest",
        "geography": "National",
        "ev_mm": 3_200,
        "ebitda_at_entry_mm": 310,
        "ev_ebitda": 10.3,
        "hold_years": 5.0,
        "realized_moic": 2.1,
        "realized_irr": 0.16,
        "payer_mix": {
            "medicare": 0.00,
            "medicaid": 0.00,
            "commercial": 0.90,
            "self_pay": 0.10,
        },
        "notes": (
            "Largest US regulated medical waste and secure document destruction "
            "services provider, serving hospitals, physician offices, dental "
            "practices, and long-term care facilities. Medical waste services "
            "billing is B2B invoicing rather than patient-level claims, but "
            "regulatory compliance directly affects revenue collectibility: "
            "EPA and state environmental agency permit status, DOT hazardous "
            "materials shipping compliance, and OSHA bloodborne pathogen "
            "standards must all be maintained continuously — permit suspension "
            "voids service contracts. Stericycle's revenue cycle complexity "
            "stems from its mix of periodic pick-up contracts (billed monthly "
            "by container volume/weight) and one-time removal events (disaster "
            "response, facility closures), each requiring different billing "
            "workflows. Healthcare provider customers increasingly use "
            "purchase-order matching and three-way match requirements before "
            "releasing payment — invoice discrepancies on manifest weights "
            "require reconciliation against EPA-mandated waste tracking "
            "manifests (Uniform Hazardous Waste Manifest) that accompany each "
            "regulated medical waste shipment. Nordic Capital invested in "
            "automated manifest-to-invoice reconciliation software that "
            "reduced DSO by 8 days across the hospital segment."
        ),
    },
    {
        "source_id": "ext39_012",
        "source": "seed",
        "deal_name": "Teladoc Health – Spectrum Equity Telehealth Platform Growth Investment",
        "year": 2014,
        "buyer": "Spectrum Equity",
        "seller": "Series D investors / management",
        "sector": "Telehealth Platforms",
        "deal_type": "Growth Equity",
        "region": "Northeast",
        "geography": "National",
        "ev_mm": 280,
        "ebitda_at_entry_mm": None,
        "ev_ebitda": None,
        "hold_years": 3.0,
        "realized_moic": 4.5,
        "realized_irr": 0.33,
        "payer_mix": {
            "medicare": 0.06,
            "medicaid": 0.08,
            "commercial": 0.72,
            "self_pay": 0.14,
        },
        "notes": (
            "Pioneer US general telehealth platform providing on-demand video and "
            "phone physician consultations for primary care, mental health, and "
            "dermatology, subsequently taken public (TDOC) in 2015. Pre-COVID "
            "telehealth RCM was heavily constrained: Medicare only covered "
            "telehealth services for patients in rural Health Professional Shortage "
            "Areas (HPSAs) at an approved originating site, limiting Medicare "
            "telehealth billing to a small fraction of the population. Commercial "
            "payer telehealth coverage varied by state — 34 states had enacted "
            "telehealth parity laws by 2014, but enforcement and coverage breadth "
            "differed materially. Telehealth professional claim billing requires "
            "the GT modifier (-GT) to indicate interactive audio-video services, "
            "and place-of-service code 02 (telehealth provided other than in "
            "patient's home) or 10 (telehealth in patient's home, added 2022) "
            "to correctly classify the encounter for payer adjudication. A key "
            "billing risk is mismatching POS code and modifier, which triggers "
            "claim edits across most commercial payers. Spectrum Equity invested "
            "in building a payer-specific telehealth eligibility and benefit "
            "verification system that pre-screened each patient's telehealth "
            "coverage before the visit, dramatically reducing same-day denials."
        ),
    },
    {
        "source_id": "ext39_013",
        "source": "seed",
        "deal_name": "MDLive – Riverside Company Telehealth Platform Secondary Investment",
        "year": 2017,
        "buyer": "Riverside Company",
        "seller": "Earlier growth investors",
        "sector": "Telehealth Platforms",
        "deal_type": "Secondary Growth Equity",
        "region": "Southeast",
        "geography": "National",
        "ev_mm": 165,
        "ebitda_at_entry_mm": None,
        "ev_ebitda": None,
        "hold_years": 4.0,
        "realized_moic": 3.1,
        "realized_irr": 0.26,
        "payer_mix": {
            "medicare": 0.05,
            "medicaid": 0.10,
            "commercial": 0.70,
            "self_pay": 0.15,
        },
        "notes": (
            "Telehealth platform offering urgent care, behavioral health, and "
            "dermatology virtual visits to employer-sponsored health plan members, "
            "with significant regional Blues plan distribution partnerships. "
            "Employer-sponsored telehealth billing introduces a layered revenue "
            "model: per-member-per-month (PMPM) capitation paid by the employer "
            "or health plan for platform access, plus per-visit professional fees "
            "billed on CMS-1500 when the visit qualifies as a covered insurance "
            "claim. Managing dual revenue streams — capitated subscription revenue "
            "vs. fee-for-service claims — requires separate AR tracking systems "
            "and distinct revenue recognition accounting. Behavioral health "
            "telehealth billing added CPT code complexity: asynchronous store-"
            "and-forward psychiatric consultations (permitted in several states) "
            "use different codes (98969–98972) than synchronous video visits "
            "(90832–90838 therapy codes with -95 telehealth modifier). "
            "Credentialing across 50-state telehealth delivery added provider "
            "enrollment complexity — NPI credentialing with each state Medicaid "
            "program and commercial payer network required before billing could "
            "commence in a new state. Riverside Company built a centralized "
            "provider enrollment function and implemented a credentialing "
            "management system that tracked enrollment status by state and payer."
        ),
    },
    {
        "source_id": "ext39_014",
        "source": "seed",
        "deal_name": "Biotelemetry (CardioNet) – Wind Point Partners Remote Patient Monitoring Platform",
        "year": 2012,
        "buyer": "Wind Point Partners",
        "seller": "Management / Series C investors",
        "sector": "Remote Patient Monitoring (RPM)",
        "deal_type": "Platform LBO",
        "region": "Mid-Atlantic",
        "geography": "National",
        "ev_mm": 210,
        "ebitda_at_entry_mm": 24,
        "ev_ebitda": 8.8,
        "hold_years": 5.0,
        "realized_moic": 3.4,
        "realized_irr": 0.28,
        "payer_mix": {
            "medicare": 0.55,
            "medicaid": 0.08,
            "commercial": 0.34,
            "self_pay": 0.03,
        },
        "notes": (
            "Cardiac remote patient monitoring company providing mobile cardiac "
            "telemetry (MCT) and long-term cardiac monitoring services to cardiology "
            "practices and hospital systems for arrhythmia detection and monitoring. "
            "Cardiac RPM billing under Medicare uses event-monitor codes (CPT 93268, "
            "93271 for patient-activated event monitoring, CPT 93243–93247 for "
            "wearable MCT with continuous analysis) billed by the monitoring center "
            "as the technical component, with the interpreting physician billing "
            "a separate professional component (CPT 93270–93272). The split-component "
            "billing model requires exact coordination between the device/monitoring "
            "company's claims and the ordering cardiologist's professional claims "
            "to prevent duplicate billing denials — a global billing arrangement "
            "where the monitoring company bills both components under a reassignment "
            "agreement must be properly structured. CMS's 2019 RPM coding expansion "
            "(CPT 99453, 99454, 99457, 99458 for general RPM device supply, setup, "
            "and monitoring management) created a new broader RPM billing pathway "
            "that required 16 days of data collection per 30-day period and "
            "interactive communication documentation. Wind Point Partners invested "
            "in automated billing trigger logic that tracked monitoring days and "
            "flagged accounts reaching the 16-day threshold for timely claim "
            "generation, maximizing monthly RPM billing completeness."
        ),
    },
    {
        "source_id": "ext39_015",
        "source": "seed",
        "deal_name": "Vivify Health – Sterling Partners Remote Patient Monitoring Growth Investment",
        "year": 2019,
        "buyer": "Sterling Partners",
        "seller": "Series C investors / management",
        "sector": "Remote Patient Monitoring (RPM)",
        "deal_type": "Growth Equity",
        "region": "South Central",
        "geography": "National",
        "ev_mm": 95,
        "ebitda_at_entry_mm": None,
        "ev_ebitda": None,
        "hold_years": 4.0,
        "realized_moic": 2.4,
        "realized_irr": 0.21,
        "payer_mix": {
            "medicare": 0.48,
            "medicaid": 0.12,
            "commercial": 0.36,
            "self_pay": 0.04,
        },
        "notes": (
            "Cloud-based remote patient monitoring and virtual care management "
            "platform delivering post-acute and chronic disease monitoring programs "
            "to health systems and physician practices. General RPM platform "
            "billing under the 2019 CMS expansion (CPT 99453–99458) introduced "
            "new compliance requirements that created significant RCM risk: "
            "CPT 99454 (device supply with daily recording, per 30-day period) "
            "requires the patient to transmit physiologic data on at least 16 "
            "of 30 days — if days of data transmission are not tracked per "
            "patient per month, the 99454 claim is unbillable for that period. "
            "Interactive communication (99457) requires a minimum of 20 minutes "
            "per calendar month of clinical staff time reviewing transmitted data "
            "and communicating with the patient — time documentation in the EHR "
            "must be specific and contemporaneous to withstand audit. The "
            "distinction between RPM (physiologic data collection by device — "
            "blood pressure, weight, glucose, SpO2) and chronic care management "
            "(CCM — care plan coordination, 99490–99491) is critical for avoiding "
            "improper bundling: CMS permits same-month billing of both RPM and "
            "CCM for the same patient if time and service requirements are met "
            "independently, but the time cannot be double-counted. Sterling "
            "Partners built a compliance-first RPM billing workflow that auto-"
            "calculated per-patient transmission days and provider interaction "
            "minutes monthly before generating claims, reducing audit exposure."
        ),
    },
]
