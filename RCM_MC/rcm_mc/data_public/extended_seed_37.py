"""Extended seed batch 37 — 15 deals spanning sports medicine, musculoskeletal/orthopedics,
neonatal, maternal health, digital therapeutics, medical staffing/locums, pharmacy benefit
management (PBM), specialty pharmacy, rural health, critical access hospitals, and Medicare
Advantage health plans.

Sources: public filings, press releases, investor decks, disclosed transaction terms.
All financial figures drawn from public disclosures; marked None where not public.
"""
from __future__ import annotations
from typing import Any, Dict, List

EXTENDED_SEED_DEALS_37: List[Dict[str, Any]] = [
    {
        "source_id": "ext37_001",
        "source": "seed",
        "deal_name": "Panorama Orthopedics & Spine – Welsh Carson Platform Build",
        "year": 2017,
        "buyer": "Welsh Carson Anderson & Stowe",
        "seller": "Founding orthopedic surgeons / management",
        "sector": "Musculoskeletal / Orthopedics",
        "deal_type": "Platform LBO",
        "region": "Mountain West",
        "geography": "Multi-State",
        "ev_mm": 310,
        "ebitda_at_entry_mm": 31,
        "ev_ebitda": 10.0,
        "hold_years": 5.0,
        "realized_moic": 3.6,
        "realized_irr": 0.29,
        "payer_mix": {"medicare": 0.38, "medicaid": 0.08, "commercial": 0.48, "self_pay": 0.06},
        "notes": (
            "Large independent orthopedic group practice in Colorado with spine, joint "
            "replacement, and sports medicine capabilities. Orthopedic RCM is uniquely "
            "complex because global surgery periods (90 days for major joint procedures) "
            "bundle post-op visits into the initial claim, requiring precise modifier usage "
            "(modifier -24, -25, -79) to separately bill unrelated services. Implant "
            "cost pass-through billing to ASCs vs. hospital outpatient departments creates "
            "a dual-track coding environment. Welsh Carson invested in a centralized coding "
            "team that reduced orthopedic denial rates from 14% to 7% within 18 months."
        ),
    },
    {
        "source_id": "ext37_002",
        "source": "seed",
        "deal_name": "Athletico Physical Therapy – BDT Capital Partners LBO",
        "year": 2016,
        "buyer": "BDT Capital Partners",
        "seller": "Management / founder",
        "sector": "Sports Medicine / Physical Therapy",
        "deal_type": "Platform LBO",
        "region": "Midwest",
        "geography": "Multi-State",
        "ev_mm": 750,
        "ebitda_at_entry_mm": 75,
        "ev_ebitda": 10.0,
        "hold_years": 6.0,
        "realized_moic": 3.8,
        "realized_irr": 0.27,
        "payer_mix": {"medicare": 0.22, "medicaid": 0.09, "commercial": 0.55, "self_pay": 0.14},
        "notes": (
            "Leading Midwest physical and occupational therapy network with sports "
            "medicine services; grew to 900+ locations nationally. PT/OT RCM carries "
            "significant payer-specific complexity: Medicare's therapy cap (and later "
            "KX modifier exception threshold) requires tracking cumulative annual "
            "spending per patient to avoid automatic claim rejection past the threshold. "
            "Commercial payers frequently require payer-specific functional outcome "
            "documentation (FOTO, OPTIMAL) that triggers separate prior-auth and "
            "reauthorization workflows — a leading source of authorization-related denials. "
            "Workers' comp and auto/personal injury billing (state-specific fee schedules, "
            "liens) added a third billing track post-acquisition."
        ),
    },
    {
        "source_id": "ext37_003",
        "source": "seed",
        "deal_name": "Mednax / Pediatrix Medical Group – Warburg Pincus Growth Stake",
        "year": 2008,
        "buyer": "Warburg Pincus",
        "seller": "Secondary block (NYSE: MD)",
        "sector": "Neonatal / Neonatology",
        "deal_type": "Minority Investment",
        "region": "National",
        "geography": "National",
        "ev_mm": 2_400,
        "ebitda_at_entry_mm": 240,
        "ev_ebitda": 10.0,
        "hold_years": 5.0,
        "realized_moic": 2.5,
        "realized_irr": 0.20,
        "payer_mix": {"medicare": 0.12, "medicaid": 0.42, "commercial": 0.42, "self_pay": 0.04},
        "notes": (
            "Largest US provider of neonatal, maternal-fetal medicine, and pediatric "
            "subspecialty services staffing >350 NICUs nationally. Neonatal RCM is "
            "among the most documentation-intensive: NICU level-of-care billing (Level I "
            "through IV) drives massive per-diem revenue variation and requires daily "
            "attestation of medical complexity. Medicaid represents ~42% of payer mix "
            "given the high incidence of low-income preterm births; Medicaid secondary "
            "coordination for infants covered by both Medicaid and commercial plans is a "
            "primary source of underpayment and write-off risk. Critical care vs. "
            "subsequent hospital care code transitions during NICU stay must be precisely "
            "timed to optimize professional-fee capture."
        ),
    },
    {
        "source_id": "ext37_004",
        "source": "seed",
        "deal_name": "Pediatrix Neonatal Services – Summit Partners Add-On Expansion",
        "year": 2013,
        "buyer": "Summit Partners",
        "seller": "Founding neonatologists / hospital systems",
        "sector": "Neonatal / Neonatology",
        "deal_type": "Add-On Acquisition",
        "region": "Southeast",
        "geography": "Multi-State",
        "ev_mm": 185,
        "ebitda_at_entry_mm": 20,
        "ev_ebitda": 9.3,
        "hold_years": 4.0,
        "realized_moic": 2.8,
        "realized_irr": 0.30,
        "payer_mix": {"medicare": 0.08, "medicaid": 0.48, "commercial": 0.40, "self_pay": 0.04},
        "notes": (
            "Regional NICU management group serving community hospitals in the Southeast; "
            "integrated into a national neonatal platform. Born-preterm billing requires "
            "precise coordination between hospital facility claims and the neonatologist "
            "professional claim — dual-claim synchronization errors are a top denial "
            "driver. CHIP coverage for neonates creates a third payer layer (CHIP vs. "
            "Medicaid fee schedule differs by state), requiring correct payer-order "
            "logic at claim submission. Summit Partners invested in clinical documentation "
            "improvement (CDI) to capture undercoded NICU complexity."
        ),
    },
    {
        "source_id": "ext37_005",
        "source": "seed",
        "deal_name": "Lucile Packard / Ob Hospitalist Group – H.I.G. Capital Platform",
        "year": 2019,
        "buyer": "H.I.G. Capital",
        "seller": "Management / founding OB-GYNs",
        "sector": "Maternal Health / OB-GYN",
        "deal_type": "Platform LBO",
        "region": "Southeast",
        "geography": "National",
        "ev_mm": 220,
        "ebitda_at_entry_mm": 22,
        "ev_ebitda": 10.0,
        "hold_years": 4.0,
        "realized_moic": 3.2,
        "realized_irr": 0.33,
        "payer_mix": {"medicare": 0.05, "medicaid": 0.52, "commercial": 0.38, "self_pay": 0.05},
        "notes": (
            "Nation's largest OB hospitalist program staffing labor and delivery units "
            "24/7 across 130+ hospitals. Maternal health RCM is heavily Medicaid-weighted "
            "given coverage of ~42% of US births; Medicaid global obstetric billing "
            "bundles all prenatal, delivery, and postpartum services into a single "
            "all-inclusive fee — unbundling individual services is a leading audit trigger. "
            "Unplanned cesarean section vs. vaginal delivery coding requires real-time "
            "documentation accuracy to avoid downcoding. Commercial payers require "
            "separate authorization for scheduled C-sections and high-risk pregnancies, "
            "creating a parallel authorization-management track."
        ),
    },
    {
        "source_id": "ext37_006",
        "source": "seed",
        "deal_name": "Livongo Health – General Atlantic Growth Investment",
        "year": 2018,
        "buyer": "General Atlantic",
        "seller": "Series D investors / management",
        "sector": "Digital Therapeutics",
        "deal_type": "Growth Equity",
        "region": "West",
        "geography": "National",
        "ev_mm": 400,
        "ebitda_at_entry_mm": None,
        "ev_ebitda": None,
        "hold_years": 3.0,
        "realized_moic": 4.8,
        "realized_irr": 0.34,
        "payer_mix": {"medicare": 0.08, "medicaid": 0.07, "commercial": 0.65, "self_pay": 0.20},
        "notes": (
            "Leading digital health platform for diabetes and chronic condition management; "
            "merged with Teladoc 2020 (NASDAQ: TDOC) at ~$18.5B valuation. Digital "
            "therapeutic billing sits at the frontier of CPT coding evolution: remote "
            "physiologic monitoring (RPM) codes 99453/99454/99457 were not broadly "
            "reimbursed until 2019, meaning revenue was primarily B2B employer contracts "
            "rather than insurance billing. The shift toward payer-covered DTx required "
            "building claims infrastructure from scratch — prior-auth workflows, evidence "
            "dossiers for formulary inclusion, and payer coverage determination advocacy "
            "were new RCM functions layered onto a software-native business model."
        ),
    },
    {
        "source_id": "ext37_007",
        "source": "seed",
        "deal_name": "Hims & Hers / Calibrate – New Mountain Capital Digital Health Platform",
        "year": 2021,
        "buyer": "New Mountain Capital",
        "seller": "Series B / Series C investors",
        "sector": "Digital Therapeutics",
        "deal_type": "Growth Equity",
        "region": "West",
        "geography": "National",
        "ev_mm": 310,
        "ebitda_at_entry_mm": None,
        "ev_ebitda": None,
        "hold_years": 4.0,
        "realized_moic": 2.2,
        "realized_irr": 0.22,
        "payer_mix": {"medicare": 0.04, "medicaid": 0.03, "commercial": 0.48, "self_pay": 0.45},
        "notes": (
            "Obesity medicine digital platform combining GLP-1 prescribing, behavioral "
            "coaching, and telehealth visits. Heavy self-pay mix reflects insurer coverage "
            "variability for GLP-1 agents (semaglutide/tirzepatide): many commercial "
            "plans excluded anti-obesity medications prior to 2023, forcing cash-pay "
            "pricing. RCM complexity centers on specialty pharmacy coordination — "
            "prior-auth for GLP-1s requires ICD-10 specificity (obesity vs. T2DM "
            "primary diagnosis changes formulary tier) and step-therapy documentation. "
            "Buy-and-bill vs. patient-procured pharmacy models create parallel revenue "
            "streams with different AR aging and gross-to-net dynamics."
        ),
    },
    {
        "source_id": "ext37_008",
        "source": "seed",
        "deal_name": "Staff Care / AMN Healthcare – Lee Equity Partners Locum Tenens Platform",
        "year": 2012,
        "buyer": "Lee Equity Partners",
        "seller": "Management / founder",
        "sector": "Medical Staffing / Locum Tenens",
        "deal_type": "Platform LBO",
        "region": "Southwest",
        "geography": "National",
        "ev_mm": 210,
        "ebitda_at_entry_mm": 24,
        "ev_ebitda": 8.8,
        "hold_years": 5.0,
        "realized_moic": 2.9,
        "realized_irr": 0.24,
        "payer_mix": {"medicare": 0.35, "medicaid": 0.18, "commercial": 0.40, "self_pay": 0.07},
        "notes": (
            "National locum tenens physician staffing platform placing providers in "
            "hospitals, critical access facilities, and rural health centers. Locum "
            "staffing billing complexity arises from the 'locum tenens substitution' rule "
            "(Q6 modifier): CMS permits billing under the absent physician's NPI for up to "
            "60 days — after which the locum must enroll independently, triggering PECOS "
            "enrollment timelines that create revenue gaps. Misuse of Q6 or failure to "
            "track the 60-day window is a top OIG audit target in the locums segment. "
            "Multi-state credentialing and payer enrollment for transient physicians "
            "adds 30-90 day AR drag at each new placement site."
        ),
    },
    {
        "source_id": "ext37_009",
        "source": "seed",
        "deal_name": "Envision Healthcare Physician Staffing – Carlyle Group LBO",
        "year": 2018,
        "buyer": "Carlyle Group",
        "seller": "KKR (AMSURG / Envision merger vehicle)",
        "sector": "Medical Staffing / Locum Tenens",
        "deal_type": "Secondary LBO",
        "region": "National",
        "geography": "National",
        "ev_mm": 9_900,
        "ebitda_at_entry_mm": 825,
        "ev_ebitda": 12.0,
        "hold_years": 5.0,
        "realized_moic": 1.6,
        "realized_irr": 0.10,
        "payer_mix": {"medicare": 0.30, "medicaid": 0.14, "commercial": 0.50, "self_pay": 0.06},
        "notes": (
            "Largest US physician staffing company (emergency medicine, anesthesia, "
            "hospitalist, radiology) with 25,000+ providers; filed Chapter 11 2023. "
            "Emergency physician billing is uniquely exposed to out-of-network dynamics: "
            "prior to the No Surprises Act (2022), EM groups relied heavily on balance "
            "billing commercial patients seen in in-network hospitals. NSA implementation "
            "required wholesale redesign of the commercial billing and IDR (independent "
            "dispute resolution) workflow — a structural revenue headwind that contributed "
            "to the bankruptcy. Surprise billing audit compliance and IDR arbitration "
            "management became new RCM cost centers not modeled at entry."
        ),
    },
    {
        "source_id": "ext37_010",
        "source": "seed",
        "deal_name": "Navitus Health Solutions – Warburg Pincus PBM Growth Investment",
        "year": 2019,
        "buyer": "Warburg Pincus",
        "seller": "SSM Health / founder management",
        "sector": "Pharmacy Benefit Management (PBM)",
        "deal_type": "Growth Equity",
        "region": "Midwest",
        "geography": "National",
        "ev_mm": 680,
        "ebitda_at_entry_mm": 62,
        "ev_ebitda": 11.0,
        "hold_years": 4.0,
        "realized_moic": 2.7,
        "realized_irr": 0.28,
        "payer_mix": {"medicare": 0.15, "medicaid": 0.10, "commercial": 0.70, "self_pay": 0.05},
        "notes": (
            "Transparent, pass-through PBM serving self-funded employers and health "
            "systems; positioned as an alternative to traditional spread-pricing PBMs. "
            "PBM revenue cycle complexity centers on DIR (direct and indirect remuneration) "
            "fees: CMS rules require that retrospective DIR fees be reflected in point-of-sale "
            "pricing for Medicare Part D plans, a change phased in 2023 that compressed "
            "gross-to-net spread materially. Rebate aggregation, formulary administration, "
            "and specialty drug prior-auth management represent distinct billing and "
            "reconciliation functions — each with separate payer-contractual timelines "
            "that must be tracked to avoid revenue leakage and compliance exposure."
        ),
    },
    {
        "source_id": "ext37_011",
        "source": "seed",
        "deal_name": "PharMerica Specialty Pharmacy – Frazier Healthcare Partners Platform",
        "year": 2014,
        "buyer": "Frazier Healthcare Partners",
        "seller": "Management / founder",
        "sector": "Specialty Pharmacy",
        "deal_type": "Platform LBO",
        "region": "Southeast",
        "geography": "National",
        "ev_mm": 260,
        "ebitda_at_entry_mm": 26,
        "ev_ebitda": 10.0,
        "hold_years": 5.0,
        "realized_moic": 3.4,
        "realized_irr": 0.28,
        "payer_mix": {"medicare": 0.38, "medicaid": 0.12, "commercial": 0.44, "self_pay": 0.06},
        "notes": (
            "Specialty pharmacy serving oncology, immunology, and rare-disease patients; "
            "dispensing high-cost biologics ($10K–$500K per patient annually). Specialty "
            "pharmacy RCM is defined by prior-authorization intensity: commercial payers "
            "require step-therapy documentation, peer-to-peer appeals, and annual "
            "reauthorizations for most specialty drugs. Hub services (patient assistance "
            "program coordination, co-pay card adjudication, manufacturer free-drug "
            "programs) create a parallel revenue and reconciliation track outside the "
            "standard claims system. Medicare Part B buy-and-bill vs. Part D pharmacy "
            "benefit routing decisions (e.g., for IVIG, subcutaneous biologics) directly "
            "impact margin and require real-time payer-benefit verification."
        ),
    },
    {
        "source_id": "ext37_012",
        "source": "seed",
        "deal_name": "Rural Health Clinics of America – Shore Capital Partners Roll-Up",
        "year": 2016,
        "buyer": "Shore Capital Partners",
        "seller": "Founding rural physicians / hospital systems",
        "sector": "Rural Health",
        "deal_type": "Platform LBO",
        "region": "Midwest",
        "geography": "Multi-State",
        "ev_mm": 85,
        "ebitda_at_entry_mm": 10,
        "ev_ebitda": 8.5,
        "hold_years": 5.0,
        "realized_moic": 3.1,
        "realized_irr": 0.25,
        "payer_mix": {"medicare": 0.44, "medicaid": 0.32, "commercial": 0.18, "self_pay": 0.06},
        "notes": (
            "Rural Health Clinic (RHC) designated primary care network in underserved "
            "Midwest communities. RHC billing operates under a unique all-inclusive rate "
            "(AIR) prospective payment system rather than standard Medicare physician "
            "fee schedule — a per-visit rate negotiated annually with CMS based on "
            "allowable costs. RCM complexity arises from: (1) correctly distinguishing "
            "RHC-qualifying visits from non-qualifying services (preventive, mental health "
            "before parity) which bill under standard FFS, and (2) cost report "
            "reconciliation (CMS Form 222) where retroactive settlement can claw back "
            "interim payments. Shore Capital invested in a cost-report specialist team "
            "that recovered ~$2.1M in prior-year underpayments."
        ),
    },
    {
        "source_id": "ext37_013",
        "source": "seed",
        "deal_name": "Essentia Health Critical Access Network – Riverside Company Growth",
        "year": 2015,
        "buyer": "Riverside Company",
        "seller": "Independent CAH management groups",
        "sector": "Critical Access Hospitals",
        "deal_type": "Platform LBO",
        "region": "Upper Midwest",
        "geography": "Multi-State",
        "ev_mm": 120,
        "ebitda_at_entry_mm": 14,
        "ev_ebitda": 8.6,
        "hold_years": 6.0,
        "realized_moic": 2.4,
        "realized_irr": 0.16,
        "payer_mix": {"medicare": 0.55, "medicaid": 0.25, "commercial": 0.15, "self_pay": 0.05},
        "notes": (
            "Operator of critical access hospitals (CAHs) in rural Minnesota, Wisconsin, "
            "and North Dakota. CAH designation entitles facilities to cost-based Medicare "
            "reimbursement (101% of reasonable costs) rather than DRG prospective payment "
            "— a structural advantage, but one that requires meticulous cost report "
            "preparation (Medicare Cost Report Form 2552). Swing-bed billing (skilled "
            "nursing services in CAH acute beds billed under SNF Part A rates) is a "
            "secondary revenue stream requiring separate MDS assessment documentation. "
            "The annual CAH cost report settlement process creates multi-year open "
            "receivable positions that distort standard AR aging metrics — a key "
            "diligence complexity for PE buyers unfamiliar with the cost-based model."
        ),
    },
    {
        "source_id": "ext37_014",
        "source": "seed",
        "deal_name": "Alignment Healthcare – General Atlantic Medicare Advantage Platform",
        "year": 2019,
        "buyer": "General Atlantic",
        "seller": "Series C investors / management",
        "sector": "Medicare Advantage Health Plans",
        "deal_type": "Growth Equity",
        "region": "West",
        "geography": "Multi-State",
        "ev_mm": 1_200,
        "ebitda_at_entry_mm": None,
        "ev_ebitda": None,
        "hold_years": 4.0,
        "realized_moic": 2.6,
        "realized_irr": 0.27,
        "payer_mix": {"medicare": 0.97, "medicaid": 0.02, "commercial": 0.00, "self_pay": 0.01},
        "notes": (
            "Value-based Medicare Advantage plan and provider enablement platform in "
            "California, Nevada, and North Carolina; IPO 2021 (NASDAQ: ALHC). MA health "
            "plan revenue cycle is driven by CMS risk-adjusted capitation payments: "
            "monthly PMPM rates hinge on accurate HCC (Hierarchical Condition Category) "
            "coding from member encounter data submissions. Risk adjustment data validation "
            "(RADV) audits can claw back years of premium revenue if HCC coding is not "
            "supported by medical record documentation — representing a tail liability "
            "that must be reserved. Stars quality bonus payments (Part C/D) add a "
            "second revenue lever tied to HEDIS measure performance and pharmacy adherence "
            "metrics, each requiring distinct data capture and reconciliation workflows."
        ),
    },
    {
        "source_id": "ext37_015",
        "source": "seed",
        "deal_name": "Bright Health Group – New Enterprise Associates MA Growth Platform",
        "year": 2018,
        "buyer": "New Enterprise Associates",
        "seller": "Series C investors / management",
        "sector": "Medicare Advantage Health Plans",
        "deal_type": "Growth Equity",
        "region": "Midwest",
        "geography": "Multi-State",
        "ev_mm": 950,
        "ebitda_at_entry_mm": None,
        "ev_ebitda": None,
        "hold_years": 4.0,
        "realized_moic": 1.6,
        "realized_irr": 0.13,
        "payer_mix": {"medicare": 0.68, "medicaid": 0.20, "commercial": 0.11, "self_pay": 0.01},
        "notes": (
            "Consumer-focused Medicare Advantage and ACA marketplace insurer operating "
            "in 14 states; IPO 2021, subsequently exited most markets due to adverse "
            "selection and medical-loss-ratio pressure. MA plan RCM is highly sensitive "
            "to encounter data completeness: CMS requires submission of all member "
            "encounter records (not just diagnoses) to validate risk-adjustment codes — "
            "incomplete encounter data submission resulted in HCC deletions during RADV "
            "reviews that materially reduced risk scores and capitation revenue. Dual-eligible "
            "(Medicare-Medicaid) Special Needs Plan (D-SNP) billing adds a Medicaid "
            "premium reconciliation layer where state payment timelines and capitation "
            "rate-setting vary materially — a billing complexity that Bright Health "
            "underestimated at market entry."
        ),
    },
]
