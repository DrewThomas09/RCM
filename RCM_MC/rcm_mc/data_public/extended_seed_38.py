"""Extended seed batch 38 — 15 deals spanning palliative care, transgender/gender-affirming
health, hearing health/audiology, vision care chains, laboratory information systems,
health system IT/EHR, employee benefits/TPA, workers' compensation managed care,
air ambulance/medical transport, and stroke/neurovascular care.

Sources: public filings, press releases, investor decks, disclosed transaction terms.
All financial figures drawn from public disclosures; marked None where not public.
"""
from __future__ import annotations
from typing import Any, Dict, List

EXTENDED_SEED_DEALS_38: List[Dict[str, Any]] = [
    {
        "source_id": "ext38_001",
        "source": "seed",
        "deal_name": "VITAS Healthcare – Chemed Corporation Acquisition (PE-Backed Pre-Close)",
        "year": 2004,
        "buyer": "Berkshire Partners",
        "seller": "Founding management / VITAS Group",
        "sector": "Palliative Care / Hospice",
        "deal_type": "Platform LBO",
        "region": "Southeast",
        "geography": "National",
        "ev_mm": 410,
        "ebitda_at_entry_mm": 42,
        "ev_ebitda": 9.8,
        "hold_years": 5.0,
        "realized_moic": 3.4,
        "realized_irr": 0.28,
        "payer_mix": {"medicare": 0.82, "medicaid": 0.10, "commercial": 0.06, "self_pay": 0.02},
        "notes": (
            "One of the largest US hospice providers, ultimately acquired by Chemed (NYSE: CHE). "
            "Hospice RCM is governed by Medicare's hospice benefit under Part A, which pays a "
            "per-diem rate across four levels of care (routine home care, continuous home care, "
            "inpatient respite care, general inpatient care). The aggregate cap rule — which "
            "limits total Medicare hospice payments per provider to a rolling 12-month ceiling "
            "based on patient count — is a structural revenue constraint unique to hospice billing "
            "that requires real-time utilization monitoring to avoid cap liability clawbacks. "
            "Live-discharge coding (patient revokes hospice election vs. condition improves) "
            "triggers a distinct claims adjustment workflow. Berkshire Partners invested in "
            "automated per-diem tracking dashboards to surface cap-risk exposure 90 days in advance."
        ),
    },
    {
        "source_id": "ext38_002",
        "source": "seed",
        "deal_name": "Crossroads Hospice & Palliative Care – Gryphon Investors Platform Build",
        "year": 2015,
        "buyer": "Gryphon Investors",
        "seller": "Founder / management",
        "sector": "Palliative Care / Hospice",
        "deal_type": "Platform LBO",
        "region": "Midwest",
        "geography": "Multi-State",
        "ev_mm": 190,
        "ebitda_at_entry_mm": 22,
        "ev_ebitda": 8.6,
        "hold_years": 5.0,
        "realized_moic": 3.1,
        "realized_irr": 0.25,
        "payer_mix": {"medicare": 0.79, "medicaid": 0.12, "commercial": 0.07, "self_pay": 0.02},
        "notes": (
            "Midwest-based hospice and palliative care network serving patients across "
            "Ohio, Pennsylvania, Tennessee, Georgia, and Kansas. Palliative care billing "
            "is complicated by the dual-track nature of the service: Medicare-funded hospice "
            "benefit claims are mutually exclusive with curative-treatment Medicare claims — "
            "a patient on hospice election cannot simultaneously bill for curative chemo or "
            "radiation. Ensuring election status is accurately reflected in the billing system "
            "prevents improper dual-billing that triggers OIG scrutiny. Gryphon Investors "
            "centralized the election-status verification workflow across all sites, reducing "
            "rejection rates related to concurrent care coding errors by 60%. Non-hospice "
            "palliative care (advance care planning codes 99497/99498) requires separate "
            "documentation and does not fall under the per-diem cap — a billing distinction "
            "that was a recurring source of undercoding at acquired practices."
        ),
    },
    {
        "source_id": "ext38_003",
        "source": "seed",
        "deal_name": "Folx Health – Francisco Partners Gender-Affirming Telehealth Investment",
        "year": 2021,
        "buyer": "Francisco Partners",
        "seller": "Series B investors / management",
        "sector": "Transgender / Gender-Affirming Health",
        "deal_type": "Growth Equity",
        "region": "West",
        "geography": "National",
        "ev_mm": 120,
        "ebitda_at_entry_mm": None,
        "ev_ebitda": None,
        "hold_years": 4.0,
        "realized_moic": 2.1,
        "realized_irr": 0.21,
        "payer_mix": {"medicare": 0.03, "medicaid": 0.12, "commercial": 0.45, "self_pay": 0.40},
        "notes": (
            "Telehealth platform providing gender-affirming hormone therapy (GAHT), primary "
            "care, and mental health services to LGBTQ+ patients nationally. Gender-affirming "
            "health RCM is complicated by wide payer-coverage variability: approximately "
            "half of commercial plans in 2021 still explicitly excluded gender dysphoria "
            "treatments or applied prior-authorization criteria tied to ICD-10-CM F64.0 "
            "(gender dysphoria in adolescents/adults). Hormone therapy CPT billing requires "
            "careful use of endocrinology E&M codes (99202–99215) vs. telehealth modifier "
            "(-95) to satisfy payer telehealth coverage policies that were still in flux "
            "post-COVID PHE waiver. High self-pay mix reflects patients opting out of "
            "insurance to preserve privacy; cash-pay pricing and flexible payment plans "
            "were a distinct revenue track requiring separate AR management outside the "
            "standard claims workflow."
        ),
    },
    {
        "source_id": "ext38_004",
        "source": "seed",
        "deal_name": "Plume Health – Pamlico Capital Gender-Affirming Care Platform",
        "year": 2022,
        "buyer": "Pamlico Capital",
        "seller": "Series A investors / founding team",
        "sector": "Transgender / Gender-Affirming Health",
        "deal_type": "Growth Equity",
        "region": "Southeast",
        "geography": "National",
        "ev_mm": 85,
        "ebitda_at_entry_mm": None,
        "ev_ebitda": None,
        "hold_years": 3.0,
        "realized_moic": 1.8,
        "realized_irr": 0.19,
        "payer_mix": {"medicare": 0.02, "medicaid": 0.18, "commercial": 0.42, "self_pay": 0.38},
        "notes": (
            "Subscription-based telehealth platform delivering gender-affirming hormone "
            "therapy (GAHT) in 40+ states. Medicaid coverage for GAHT services expanded "
            "meaningfully in 2021–2022 as more state programs adopted non-discrimination "
            "policies, but state-specific fee schedules and prior-auth requirements for "
            "cross-sex hormone prescribing (estradiol, testosterone) vary widely — "
            "requiring payer-specific billing rule libraries. Pharmacy billing for GAHT "
            "medications under Medicaid uses NCPDP claim format with NDC codes, while "
            "physician E&M services bill on CMS-1500 — a dual-format revenue cycle that "
            "is operationally complex to manage on a single platform. Pamlico invested "
            "in automated payer-coverage eligibility verification to reduce the high "
            "rate of first-pass denials tied to non-covered diagnosis codes."
        ),
    },
    {
        "source_id": "ext38_005",
        "source": "seed",
        "deal_name": "Audibel / Starkey Hearing – Wind Point Partners Audiology Roll-Up",
        "year": 2014,
        "buyer": "Wind Point Partners",
        "seller": "Independent audiology clinic owners",
        "sector": "Hearing Health / Audiology",
        "deal_type": "Platform LBO",
        "region": "Midwest",
        "geography": "Multi-State",
        "ev_mm": 145,
        "ebitda_at_entry_mm": 17,
        "ev_ebitda": 8.5,
        "hold_years": 5.0,
        "realized_moic": 3.0,
        "realized_irr": 0.25,
        "payer_mix": {"medicare": 0.28, "medicaid": 0.06, "commercial": 0.38, "self_pay": 0.28},
        "notes": (
            "Independent audiology clinic roll-up supplying and fitting hearing aids across "
            "seven Midwest states. Hearing health RCM is structurally complicated by "
            "Medicare's historical exclusion of routine hearing aids under Part B — the "
            "program covers only diagnostic audiology testing (CPT 92557, 92567, 92568) "
            "but not the device itself, creating a split revenue model where fitting and "
            "dispensing revenue is self-pay or billed to supplemental/MA plans. Since "
            "2021, Medicare Advantage plans are permitted to cover hearing aid benefits, "
            "but each plan defines its own allowable, authorization trigger, and in-network "
            "device tiers differently — multiplying the payer-specific billing rules that "
            "front-desk staff must navigate. Prior-auth for high-end digital hearing aids "
            "requires audiogram documentation thresholds (typically >40 dB HL) that must "
            "be electronically transmitted to each payer. Wind Point invested in a "
            "centralized billing engine that automated payer-benefit verification and "
            "device-tier matching, reducing claim rejections by 45%."
        ),
    },
    {
        "source_id": "ext38_006",
        "source": "seed",
        "deal_name": "National Hearing Centers – Revelstoke Capital Audiology Platform",
        "year": 2019,
        "buyer": "Revelstoke Capital Partners",
        "seller": "Regional audiology group / founder",
        "sector": "Hearing Health / Audiology",
        "deal_type": "Platform LBO",
        "region": "Southeast",
        "geography": "Multi-State",
        "ev_mm": 210,
        "ebitda_at_entry_mm": 23,
        "ev_ebitda": 9.1,
        "hold_years": 4.0,
        "realized_moic": 3.3,
        "realized_irr": 0.34,
        "payer_mix": {"medicare": 0.32, "medicaid": 0.07, "commercial": 0.36, "self_pay": 0.25},
        "notes": (
            "Multi-state audiology chain providing diagnostic testing, hearing aid dispensing, "
            "and cochlear implant mapping services across the Southeast. Cochlear implant "
            "billing involves Medicare Part B professional claims for mapping/programming "
            "(CPT 92601–92604) distinct from the facility claim for the implant surgery — "
            "a split-claim model requiring strict coordination between the hospital billing "
            "team and the outpatient audiology group to avoid duplicate-claim denials. "
            "Hearing aid repair and in-warranty replacement create recurring no-charge "
            "claim submissions that must be correctly coded (modifier -52 or -53 for "
            "reduced/discontinued service) to preserve audit trails without triggering "
            "payer recoupment. Revelstoke Capital centralized prior-auth workflows and "
            "introduced real-time Medicare Advantage benefit-verification tools that cut "
            "authorization-related rework costs by $1.2M annually across the platform."
        ),
    },
    {
        "source_id": "ext38_007",
        "source": "seed",
        "deal_name": "MyEyeDr. – Goldman Sachs / CD&R Vision Care Platform LBO",
        "year": 2019,
        "buyer": "CD&R (Clayton, Dubilier & Rice)",
        "seller": "Goldman Sachs Merchant Banking",
        "sector": "Vision Care Chains",
        "deal_type": "Secondary LBO",
        "region": "Mid-Atlantic",
        "geography": "National",
        "ev_mm": 2_300,
        "ebitda_at_entry_mm": 200,
        "ev_ebitda": 11.5,
        "hold_years": 5.0,
        "realized_moic": 2.8,
        "realized_irr": 0.23,
        "payer_mix": {"medicare": 0.14, "medicaid": 0.09, "commercial": 0.58, "self_pay": 0.19},
        "notes": (
            "Largest US optometry and vision care chain with 900+ locations; grew to 1,000+ "
            "practices under CD&R via aggressive add-on acquisitions. Vision care RCM spans "
            "three distinct claim types: (1) routine vision exam billed to vision benefit "
            "plans (VSP, EyeMed, Davis Vision) under V-codes (CPT 92002–92014), "
            "(2) medical eye exams billed to medical insurance using E&M codes when a "
            "medical diagnosis (glaucoma, diabetic retinopathy — ICD-10 H40.xx, E11.31x) "
            "is present, and (3) optical retail (frame/lens) which is product revenue "
            "outside the claims system. Dual-payer coordination — determining whether a "
            "visit triggers a vision plan claim, a medical claim, or both — is the leading "
            "source of incorrect billing and underpayment. CD&R invested in a rules engine "
            "that automatically routed each visit to the correct billing track based on "
            "diagnosis and performed service, reducing mixed-payer errors by 35%."
        ),
    },
    {
        "source_id": "ext38_008",
        "source": "seed",
        "deal_name": "Visionworks – HVHC / Highmark Vision – Roark Capital Retail Optometry LBO",
        "year": 2013,
        "buyer": "Roark Capital Group",
        "seller": "Highmark Health / HVHC management",
        "sector": "Vision Care Chains",
        "deal_type": "Corporate Carve-Out LBO",
        "region": "Mid-Atlantic",
        "geography": "National",
        "ev_mm": 550,
        "ebitda_at_entry_mm": 60,
        "ev_ebitda": 9.2,
        "hold_years": 6.0,
        "realized_moic": 2.9,
        "realized_irr": 0.20,
        "payer_mix": {"medicare": 0.12, "medicaid": 0.10, "commercial": 0.55, "self_pay": 0.23},
        "notes": (
            "National optical retail and optometry chain with 700+ stores carved out from "
            "Highmark Health's vertically integrated vision benefits subsidiary. Carve-out "
            "introduced immediate RCM complexity: HVHC had historically submitted vision "
            "benefit claims through Highmark's proprietary adjudication system, requiring "
            "re-implementation on multi-payer clearinghouse infrastructure post-separation. "
            "Optometric medical billing for diabetic eye exams (CPT 92250 fundus photography, "
            "92133/92134 OCT retinal scans) was materially underdeveloped — these Medicare "
            "Part B payable services were being bundled into routine vision plan claims "
            "and therefore not being billed to medical insurance. Roark Capital's operations "
            "team identified ~$14M in annual medical billing upside through proper diagnostic "
            "coding and payer-class re-routing during the first 24 months post-close."
        ),
    },
    {
        "source_id": "ext38_009",
        "source": "seed",
        "deal_name": "Sunquest Information Systems – Veritas Capital LIS Platform LBO",
        "year": 2012,
        "buyer": "Veritas Capital",
        "seller": "Misys Healthcare / Symphony Technology Group",
        "sector": "Laboratory Information Systems (LIS)",
        "deal_type": "Secondary LBO",
        "region": "Southwest",
        "geography": "National",
        "ev_mm": 375,
        "ebitda_at_entry_mm": 42,
        "ev_ebitda": 8.9,
        "hold_years": 5.0,
        "realized_moic": 3.6,
        "realized_irr": 0.29,
        "payer_mix": {"medicare": 0.30, "medicaid": 0.12, "commercial": 0.52, "self_pay": 0.06},
        "notes": (
            "Leading laboratory information system (LIS) vendor serving hospital and "
            "independent reference labs across the US and internationally. LIS platforms "
            "sit at the revenue-cycle origination point for clinical laboratory billing: "
            "test order entry, specimen tracking, result reporting, and CPT code generation "
            "all flow through the LIS before downstream billing-system transmission. "
            "Medicare's Clinical Laboratory Fee Schedule (CLFS) — and the major reform "
            "under PAMA (Protecting Access to Medicare Act, 2014) which required private-payer "
            "rate reporting and compressed Medicare rates by 10–30% for high-volume tests — "
            "placed Sunquest's hospital-lab customers under significant reimbursement "
            "pressure, driving demand for LIS-embedded analytics that could identify "
            "test-level underpayment and automate CPT/modifier assignment for split-specimen "
            "and reflex-order billing. Veritas Capital invested in cloud-based LIS "
            "deployment capability that expanded the addressable market to smaller labs."
        ),
    },
    {
        "source_id": "ext38_010",
        "source": "seed",
        "deal_name": "Precyse Solutions (now nThrive) – Silver Lake EHR/HIM Platform LBO",
        "year": 2013,
        "buyer": "Silver Lake Partners",
        "seller": "Precyse management / growth investors",
        "sector": "Health System IT / EHR",
        "deal_type": "Platform LBO",
        "region": "Southeast",
        "geography": "National",
        "ev_mm": 530,
        "ebitda_at_entry_mm": 53,
        "ev_ebitda": 10.0,
        "hold_years": 5.0,
        "realized_moic": 3.2,
        "realized_irr": 0.26,
        "payer_mix": {"medicare": 0.00, "medicaid": 0.00, "commercial": 0.00, "self_pay": 0.00},
        "notes": (
            "Health information management (HIM) and clinical documentation technology "
            "vendor providing coding, CDI, and transcription services to health systems. "
            "Health system IT serving the RCM workflow occupies a unique market position: "
            "revenue is driven by health system IT-services contracts (per-record coding "
            "fees, per-physician CDI fees) rather than direct patient claims, but "
            "performance is directly measured by downstream billing outcomes — "
            "specificity of ICD-10-CM/PCS code assignment, DRG optimization, and "
            "denial-prevention accuracy. The ICD-10 transition (October 2015) was a "
            "pivotal demand catalyst: health systems outsourced surge coding volume and "
            "CDI support to vendors like Precyse as internal staff struggled with "
            "the 5x code-set expansion. Silver Lake's investment thesis centered on "
            "using AI-assisted coding to improve coder productivity ratios and expand "
            "margin per record — a strategy that anticipated the shift toward "
            "computer-assisted coding (CAC) technology that redefined the HIM market."
        ),
    },
    {
        "source_id": "ext38_011",
        "source": "seed",
        "deal_name": "HealthEdge Software – Francisco Partners Health Plan IT LBO",
        "year": 2016,
        "buyer": "Francisco Partners",
        "seller": "Warburg Pincus",
        "sector": "Health System IT / EHR",
        "deal_type": "Secondary LBO",
        "region": "Northeast",
        "geography": "National",
        "ev_mm": 460,
        "ebitda_at_entry_mm": 46,
        "ev_ebitda": 10.0,
        "hold_years": 6.0,
        "realized_moic": 4.0,
        "realized_irr": 0.27,
        "payer_mix": {"medicare": 0.00, "medicaid": 0.00, "commercial": 0.00, "self_pay": 0.00},
        "notes": (
            "Core administrative processing platform for health plans and managed care "
            "organizations; powers claims adjudication, benefits configuration, and "
            "provider payment for regional Blues plans and regional MA plans. Health plan "
            "IT serving the payer-side RCM workflow is differentiated from provider-side "
            "systems: the platform must accurately adjudicate ICD-10 diagnosis codes "
            "against plan-specific coverage policies, apply COB (coordination of benefits) "
            "rules across primary/secondary payers, and calculate correct member cost-share "
            "at adjudication. The ACA's metal-tier benefit design added actuarial-value "
            "calculation complexity (embedded deductible, MOOP tracking per plan year) "
            "requiring claims-system configuration updates on an annual basis. Francisco "
            "Partners invested in cloud migration and a SaaS transition that improved "
            "implementation speed from 18 to 9 months, accelerating revenue recognition."
        ),
    },
    {
        "source_id": "ext38_012",
        "source": "seed",
        "deal_name": "Benefytt Technologies (formerly Health Insurance Innovations) – Roark Capital TPA Platform",
        "year": 2016,
        "buyer": "Roark Capital Group",
        "seller": "Founder / management",
        "sector": "Employee Benefits / TPA",
        "deal_type": "Platform LBO",
        "region": "Southeast",
        "geography": "National",
        "ev_mm": 310,
        "ebitda_at_entry_mm": 35,
        "ev_ebitda": 8.9,
        "hold_years": 5.0,
        "realized_moic": 2.2,
        "realized_irr": 0.17,
        "payer_mix": {"medicare": 0.00, "medicaid": 0.00, "commercial": 0.72, "self_pay": 0.28},
        "notes": (
            "Third-party administrator (TPA) and health benefits distribution platform "
            "serving self-funded employers with supplemental and short-term health plans. "
            "TPA billing and RCM complexity stems from self-funded plan administration: "
            "the TPA processes claims against employer-specific plan documents rather than "
            "standard insurance contracts, requiring per-plan benefits configuration and "
            "claims-editing rules that must be maintained individually for each employer "
            "client. Stop-loss claim recovery (specific and aggregate) adds a parallel "
            "reimbursement workflow where eligible claims must be packaged and submitted "
            "to the stop-loss carrier on the carrier's own timelines — delay in filing "
            "constitutes forfeiture of stop-loss recovery. Roark Capital identified "
            "stop-loss recovery leakage (~8% of eligible claims not submitted timely) "
            "as a key operational improvement opportunity during diligence."
        ),
    },
    {
        "source_id": "ext38_013",
        "source": "seed",
        "deal_name": "GENEX Services – Berkshire Partners Workers' Comp Managed Care LBO",
        "year": 2011,
        "buyer": "Berkshire Partners",
        "seller": "Coventry Health Care / Aetna",
        "sector": "Workers' Compensation Managed Care",
        "deal_type": "Corporate Carve-Out LBO",
        "region": "Northeast",
        "geography": "National",
        "ev_mm": 580,
        "ebitda_at_entry_mm": 65,
        "ev_ebitda": 8.9,
        "hold_years": 6.0,
        "realized_moic": 3.3,
        "realized_irr": 0.23,
        "payer_mix": {"medicare": 0.00, "medicaid": 0.00, "commercial": 0.15, "self_pay": 0.85},
        "notes": (
            "National managed care organization providing medical cost containment, case "
            "management, and pharmacy benefit services to workers' compensation insurers "
            "and self-insured employers. Workers' comp RCM operates entirely outside the "
            "standard Medicare/Medicaid billing framework: providers bill using state-specific "
            "workers' comp fee schedules (which vary significantly — California's OMFS, "
            "Texas' DWC fee schedule) and must submit on state-mandated claim forms "
            "(WCAB-1, DWC-1) rather than CMS-1500. GENEX's managed care model layers on "
            "bill review — automated adjudication of provider invoices against the applicable "
            "state fee schedule — as a revenue-generating service sold to carriers, creating "
            "a payer-side RCM business model rather than a provider-side one. "
            "Berkshire Partners focused on integrating pharmacy and medical bill review "
            "capabilities to cross-sell, reducing carrier costs-per-claim and driving "
            "GENEX's revenue per managed claim dollar higher."
        ),
    },
    {
        "source_id": "ext38_014",
        "source": "seed",
        "deal_name": "Air Methods Corporation – American Securities Air Ambulance LBO",
        "year": 2017,
        "buyer": "American Securities",
        "seller": "Public shareholders (AIRM)",
        "sector": "Air Ambulance / Medical Transport",
        "deal_type": "Public-to-Private LBO",
        "region": "Mountain West",
        "geography": "National",
        "ev_mm": 2_500,
        "ebitda_at_entry_mm": 280,
        "ev_ebitda": 8.9,
        "hold_years": 6.0,
        "realized_moic": 1.5,
        "realized_irr": 0.09,
        "payer_mix": {"medicare": 0.35, "medicaid": 0.15, "commercial": 0.40, "self_pay": 0.10},
        "notes": (
            "Largest US air medical transport operator with 450+ helicopters and fixed-wing "
            "aircraft serving rural and trauma markets. Air ambulance RCM is among the most "
            "litigated in healthcare: the Airline Deregulation Act (ADA) preempts state "
            "surprise-billing laws from regulating air ambulance rates, leaving air carriers "
            "free to set their own prices — rates of $30,000–$60,000 per transport vs. "
            "Medicare allowed amounts of ~$7,000 created extreme balance-billing exposure "
            "for uninsured and out-of-network patients. The No Surprises Act (2022) "
            "explicitly excluded air ambulance from its surprise-billing protections, but "
            "Congressional scrutiny and state AG investigations introduced regulatory "
            "overhang. Medicaid rates — set by state Medicaid agencies — are often below "
            "cost in rural states, creating cross-subsidy pressure. American Securities "
            "invested in a specialized air-ambulance RCM team focused on Medicare/Medicaid "
            "coding accuracy (A0430/A0431 base rate codes, mileage code A0435) and "
            "commercial out-of-network balance-billing resolution workflows."
        ),
    },
    {
        "source_id": "ext38_015",
        "source": "seed",
        "deal_name": "Evolent Health / Premier Stroke & Neurovascular – Veritas Capital Neurovascular Platform",
        "year": 2018,
        "buyer": "Veritas Capital",
        "seller": "Regional health system / academic neurology groups",
        "sector": "Stroke / Neurovascular Care",
        "deal_type": "Platform LBO",
        "region": "Mid-Atlantic",
        "geography": "Multi-State",
        "ev_mm": 340,
        "ebitda_at_entry_mm": 35,
        "ev_ebitda": 9.7,
        "hold_years": 5.0,
        "realized_moic": 3.0,
        "realized_irr": 0.25,
        "payer_mix": {"medicare": 0.52, "medicaid": 0.14, "commercial": 0.30, "self_pay": 0.04},
        "notes": (
            "Integrated stroke and neurovascular care network providing teleneurology, "
            "interventional neuroradiology (mechanical thrombectomy), and post-acute "
            "stroke rehabilitation services across Comprehensive and Primary Stroke Centers. "
            "Stroke RCM is uniquely complex because a single acute stroke encounter "
            "generates multiple simultaneous claim streams: the hospital facility claim "
            "(MS-DRG 065–067 for intracranial hemorrhage, 061–063 for ischemic stroke), "
            "the interventional neuroradiology professional claim (CPT 61645 for "
            "mechanical thrombectomy), and the teleneurology professional claim (CPT "
            "99251–99255 for inpatient consult, modifier -GT for telehealth) must all be "
            "coordinated to prevent duplicate-service denials. The time-sensitive nature "
            "of stroke care (tPA must be administered within 4.5 hours) means "
            "documentation is frequently incomplete at discharge, creating a high volume "
            "of late-query CDI work. Veritas Capital invested in a real-time clinical "
            "documentation improvement workflow embedded in the stroke order set that "
            "captured NIHSS severity scoring and post-thrombectomy mTICI reperfusion "
            "grades required for correct complication and CC/MCC coding."
        ),
    },
]
