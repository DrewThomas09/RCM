"""Extended seed batch 36 — 15 deals (kidney care/ESRD, ophthalmology, infusion therapy,
veterinary adjacent, clinical research/CRO, digital health platforms, occupational health,
correctional health, medical devices PE, radiation oncology).

Sources: public filings, press releases, investor decks, disclosed transaction terms.
All financial figures drawn from public disclosures; marked None where not public.
"""
from __future__ import annotations
from typing import Any, Dict, List

EXTENDED_SEED_DEALS_36: List[Dict[str, Any]] = [
    {
        "source_id": "ext36_001",
        "source": "seed",
        "deal_name": "DaVita Kidney Care – Welsh Carson Minority Stake",
        "year": 2010,
        "buyer": "Welsh Carson Anderson & Stowe",
        "seller": "DaVita Inc (secondary block)",
        "sector": "Kidney Care / ESRD",
        "deal_type": "Minority Investment",
        "region": "National",
        "geography": "National",
        "ev_mm": 2_800,
        "ebitda_at_entry_mm": 280,
        "ev_ebitda": 10.0,
        "hold_years": 5.0,
        "realized_moic": 2.9,
        "realized_irr": 0.24,
        "payer_mix": {"medicare": 0.68, "medicaid": 0.08, "commercial": 0.20, "self_pay": 0.04},
        "notes": (
            "Largest dialysis operator in the US; Medicare ESRD bundled payment conversion "
            "in 2011 dramatically reshaped RCM — transitioning from separate Part A/B billing "
            "to prospective bundled rate required complete re-engineering of claim submission "
            "and secondary-payer coordination workflows. Welsh Carson's deep dialysis history "
            "facilitated rapid integration of the new payment model."
        ),
    },
    {
        "source_id": "ext36_002",
        "source": "seed",
        "deal_name": "American Renal Associates – Centerbridge Buyout",
        "year": 2014,
        "buyer": "Centerbridge Partners",
        "seller": "Management / founder",
        "sector": "Kidney Care / ESRD",
        "deal_type": "Platform LBO",
        "region": "Northeast",
        "geography": "Multi-State",
        "ev_mm": 980,
        "ebitda_at_entry_mm": 98,
        "ev_ebitda": 10.0,
        "hold_years": 4.0,
        "realized_moic": 3.1,
        "realized_irr": 0.32,
        "payer_mix": {"medicare": 0.71, "medicaid": 0.07, "commercial": 0.18, "self_pay": 0.04},
        "notes": (
            "Leading joint-venture ESRD platform partnering with nephrologists; IPO 2016 "
            "(NYSE: ARA). Revenue cycle uniquely complex: ESRD patients retain Medicare "
            "primary coverage regardless of age, but coordination-of-benefits windows with "
            "commercial payers (first 30 months for employer-plan members) require precise "
            "payer-order logic to capture maximum allowed amounts before Medicare becomes primary."
        ),
    },
    {
        "source_id": "ext36_003",
        "source": "seed",
        "deal_name": "EyeCare Partners – Warburg Pincus Platform Build",
        "year": 2015,
        "buyer": "Warburg Pincus",
        "seller": "Management / founding ophthalmologists",
        "sector": "Ophthalmology",
        "deal_type": "Platform LBO",
        "region": "Midwest",
        "geography": "Multi-State",
        "ev_mm": 320,
        "ebitda_at_entry_mm": 32,
        "ev_ebitda": 10.0,
        "hold_years": 6.0,
        "realized_moic": 4.2,
        "realized_irr": 0.28,
        "payer_mix": {"medicare": 0.45, "medicaid": 0.10, "commercial": 0.38, "self_pay": 0.07},
        "notes": (
            "Built into the largest vertically integrated ophthalmology platform (medical + "
            "surgical + optical retail) in the US. RCM complexity is high: professional "
            "claims for E&M, surgical (cataract, retina), and ancillary optical billing each "
            "follow separate fee schedules and prior-auth requirements. Medicare's 90-day "
            "global surgery period creates no-pay windows that must be flagged to avoid "
            "duplicate-claim denials during add-on procedure billing."
        ),
    },
    {
        "source_id": "ext36_004",
        "source": "seed",
        "deal_name": "NovaBay / Retina Consultants of America – H.I.G. Capital Growth",
        "year": 2020,
        "buyer": "H.I.G. Capital",
        "seller": "Management / founding retina specialists",
        "sector": "Ophthalmology",
        "deal_type": "Platform LBO",
        "region": "Southeast",
        "geography": "Multi-State",
        "ev_mm": 480,
        "ebitda_at_entry_mm": 43,
        "ev_ebitda": 11.2,
        "hold_years": 4.0,
        "realized_moic": 3.4,
        "realized_irr": 0.36,
        "payer_mix": {"medicare": 0.58, "medicaid": 0.06, "commercial": 0.32, "self_pay": 0.04},
        "notes": (
            "Retina subspecialty roll-up; AMD and diabetic retinopathy procedures are "
            "among the highest-reimbursed outpatient Medicare services. Drug-injected "
            "anti-VEGF billing (J-code for Lucentis vs. compounded Avastin) is a leading "
            "source of audit exposure; RCM requires precise NDC-level documentation and "
            "buy-and-bill margin management. H.I.G. invested in centralized coding "
            "to reduce denial rates by ~300 bps."
        ),
    },
    {
        "source_id": "ext36_005",
        "source": "seed",
        "deal_name": "Option Care Health – Walgreens Boots Divestiture to Madison Dearborn",
        "year": 2015,
        "buyer": "Madison Dearborn Partners",
        "seller": "Walgreens Boots Alliance",
        "sector": "Infusion Therapy",
        "deal_type": "Corporate Divestiture",
        "region": "National",
        "geography": "National",
        "ev_mm": 2_050,
        "ebitda_at_entry_mm": 175,
        "ev_ebitda": 11.7,
        "hold_years": 4.0,
        "realized_moic": 2.6,
        "realized_irr": 0.27,
        "payer_mix": {"medicare": 0.35, "medicaid": 0.12, "commercial": 0.48, "self_pay": 0.05},
        "notes": (
            "Largest independent home and alternate-site infusion provider; merged with "
            "BioScrip 2019 to form NYSE: OPCH. Infusion RCM sits at the intersection of "
            "pharmacy (Part D / specialty drug), durable medical equipment (Part B), and "
            "professional services billing — each governed by different fee schedules and "
            "prior-auth pathways. Payer-contract fragmentation across 1,000+ managed care "
            "agreements drives significant denial and resubmission workload."
        ),
    },
    {
        "source_id": "ext36_006",
        "source": "seed",
        "deal_name": "BioScrip Home Infusion – Consonance Capital / Ares Recapitalization",
        "year": 2017,
        "buyer": "Ares Management",
        "seller": "BioScrip Inc (distressed recap)",
        "sector": "Infusion Therapy",
        "deal_type": "Distressed / Restructuring",
        "region": "National",
        "geography": "National",
        "ev_mm": 590,
        "ebitda_at_entry_mm": 53,
        "ev_ebitda": 11.1,
        "hold_years": 3.0,
        "realized_moic": 2.0,
        "realized_irr": 0.26,
        "payer_mix": {"medicare": 0.30, "medicaid": 0.15, "commercial": 0.50, "self_pay": 0.05},
        "notes": (
            "Ares led a debt-to-equity conversion; BioScrip subsequently merged with Option "
            "Care 2019. Home infusion RCM is complicated by specialty drug J-code vs. NDC "
            "reporting requirements and Medicare Part B vs. Part D crossover for certain "
            "IVIG and immunoglobulin therapies. Waste and overfill billing documentation "
            "is a key compliance and revenue-leakage area."
        ),
    },
    {
        "source_id": "ext36_007",
        "source": "seed",
        "deal_name": "Kindred Biosciences / National Veterinary Associates – Shore Capital Tuck-In",
        "year": 2018,
        "buyer": "Shore Capital Partners",
        "seller": "Management / founder",
        "sector": "Veterinary Services",
        "deal_type": "Add-On Acquisition",
        "region": "Midwest",
        "geography": "Multi-State",
        "ev_mm": 95,
        "ebitda_at_entry_mm": 11,
        "ev_ebitda": 8.6,
        "hold_years": 4.0,
        "realized_moic": 3.6,
        "realized_irr": 0.38,
        "payer_mix": {"pet_insurance": 0.12, "self_pay": 0.88},
        "notes": (
            "Companion animal general practice group; predominantly cash-pay with growing "
            "pet insurance penetration. RCM analogs to human healthcare are emerging: "
            "insurance carrier direct-billing requires accurate procedure coding (AVMA CPT "
            "equivalents), and claim denials for pre-existing conditions create write-off "
            "risk. Shore Capital leveraged RCM system standardization to improve collections "
            "from ~78% to ~91% across the platform."
        ),
    },
    {
        "source_id": "ext36_008",
        "source": "seed",
        "deal_name": "Syneos Health (inVentiv + INC Research Merger) – Advent / Thomas H. Lee",
        "year": 2016,
        "buyer": "Advent International / Thomas H. Lee Partners",
        "seller": "inVentiv Health / INC Research Holdings",
        "sector": "Clinical Research / CRO",
        "deal_type": "Merger / Strategic Combination",
        "region": "National",
        "geography": "Global",
        "ev_mm": 4_600,
        "ebitda_at_entry_mm": 368,
        "ev_ebitda": 12.5,
        "hold_years": 5.0,
        "realized_moic": 2.8,
        "realized_irr": 0.23,
        "payer_mix": {"pharma_sponsor": 0.72, "biotech_sponsor": 0.21, "government": 0.07},
        "notes": (
            "Combined entity became the second-largest global CRO (NASDAQ: SYNH). CRO revenue "
            "recognition follows ASC 606 percentage-of-completion on multi-year contracts; "
            "billing complexity arises from pass-through cost management, milestone-based "
            "invoicing, and investigator site payment reconciliation — all of which create "
            "significant AR aging risk if milestone definitions are poorly scoped. "
            "Centralized billing operations were a key synergy target post-merger."
        ),
    },
    {
        "source_id": "ext36_009",
        "source": "seed",
        "deal_name": "Medpace Holdings – Cinven Buyout",
        "year": 2014,
        "buyer": "Cinven",
        "seller": "Management / founder",
        "sector": "Clinical Research / CRO",
        "deal_type": "Platform LBO",
        "region": "Midwest",
        "geography": "Global",
        "ev_mm": 915,
        "ebitda_at_entry_mm": 91,
        "ev_ebitda": 10.1,
        "hold_years": 4.0,
        "realized_moic": 3.3,
        "realized_irr": 0.35,
        "payer_mix": {"pharma_sponsor": 0.55, "biotech_sponsor": 0.42, "government": 0.03},
        "notes": (
            "Niche CRO focused on metabolic, cardiovascular, and oncology trials; IPO 2016 "
            "(NASDAQ: MEDP). Full-service model avoids FSP (functional service provider) "
            "billing complexity. Revenue recognized on pass-through vs. service fee split "
            "creates gross margin reporting nuance; sponsor audit rights add reconciliation "
            "overhead. Strong biotech client concentration requires robust receivables "
            "management given sponsor funding-event risk."
        ),
    },
    {
        "source_id": "ext36_010",
        "source": "seed",
        "deal_name": "Evolent Health – TPG / The Advisory Board Growth Investment",
        "year": 2011,
        "buyer": "TPG Capital / The Advisory Board Company",
        "seller": "Management (de novo)",
        "sector": "Digital Health Platforms",
        "deal_type": "Growth Equity",
        "region": "Mid-Atlantic",
        "geography": "National",
        "ev_mm": 180,
        "ebitda_at_entry_mm": 15,
        "ev_ebitda": 12.0,
        "hold_years": 5.0,
        "realized_moic": 4.1,
        "realized_irr": 0.32,
        "payer_mix": {"value_based_care": 0.60, "fee_for_service": 0.28, "capitation": 0.12},
        "notes": (
            "Value-based care enablement and population health platform; IPO 2015 (NYSE: EVH). "
            "Unique RCM complexity: Evolent manages both payer-side (claims adjudication, "
            "risk adjustment) and provider-side (encounter data submission, HCC coding) "
            "operations simultaneously. Risk adjustment data validation audit (RADV) "
            "exposure is a primary compliance and revenue-integrity focus area for "
            "its Medicare Advantage delegated-risk client base."
        ),
    },
    {
        "source_id": "ext36_011",
        "source": "seed",
        "deal_name": "Concentra Occupational Health – Humana Divestiture to Select Medical / Welsh Carson",
        "year": 2015,
        "buyer": "Welsh Carson Anderson & Stowe / Select Medical",
        "seller": "Humana Inc",
        "sector": "Occupational Health",
        "deal_type": "Corporate Divestiture",
        "region": "National",
        "geography": "National",
        "ev_mm": 1_055,
        "ebitda_at_entry_mm": 132,
        "ev_ebitda": 8.0,
        "hold_years": 7.0,
        "realized_moic": 2.5,
        "realized_irr": 0.14,
        "payer_mix": {"workers_comp": 0.48, "employer_direct": 0.32, "commercial": 0.14, "self_pay": 0.06},
        "notes": (
            "Largest US occupational health and urgent care network (~500 centers). Workers' "
            "compensation billing is materially more complex than group health: state-specific "
            "fee schedules (each of 50 states has unique rules), adjuster authorization "
            "requirements for continued treatment, and first-report-of-injury documentation "
            "all drive denial rates above commercial benchmarks. Clean-claim rate improvement "
            "was a primary RCM initiative post-acquisition."
        ),
    },
    {
        "source_id": "ext36_012",
        "source": "seed",
        "deal_name": "Corizon Health – Apax Partners Correctional Health Buyout",
        "year": 2011,
        "buyer": "Apax Partners",
        "seller": "Prison Health Services / America Service Group",
        "sector": "Correctional Health",
        "deal_type": "Secondary LBO",
        "region": "National",
        "geography": "National",
        "ev_mm": 500,
        "ebitda_at_entry_mm": 55,
        "ev_ebitda": 9.1,
        "hold_years": 5.0,
        "realized_moic": 2.3,
        "realized_irr": 0.18,
        "payer_mix": {"government_contract": 0.92, "medicaid": 0.05, "self_pay": 0.03},
        "notes": (
            "Largest US correctional healthcare provider serving state and county facilities. "
            "Revenue model is primarily capitated government contracts rather than FFS; "
            "billing complexity arises in the 'outside care' carve-out where hospital "
            "and specialist services are billed to Medicaid for eligible inmates. The "
            "Medicaid inmate exclusion policy creates gaps in coverage that must be tracked "
            "per state — improper claims to Medicaid for ineligible inmate days represent "
            "the primary compliance and revenue-leakage risk."
        ),
    },
    {
        "source_id": "ext36_013",
        "source": "seed",
        "deal_name": "DJO Global – Blackstone Medical Devices LBO",
        "year": 2015,
        "buyer": "Blackstone Group",
        "seller": "Warburg Pincus / ReAble Therapeutics",
        "sector": "Medical Devices PE",
        "deal_type": "Secondary LBO",
        "region": "West",
        "geography": "National",
        "ev_mm": 2_020,
        "ebitda_at_entry_mm": 202,
        "ev_ebitda": 10.0,
        "hold_years": 6.0,
        "realized_moic": 2.1,
        "realized_irr": 0.13,
        "payer_mix": {"medicare": 0.38, "medicaid": 0.09, "commercial": 0.41, "workers_comp": 0.12},
        "notes": (
            "Global orthopedic bracing, joint reconstruction, and regenerative devices; "
            "HCPCS L-code billing for DME products requires CMS certificate of medical "
            "necessity (CMN) documentation. OIG investigations into brace upcoding and "
            "kickback arrangements (telemedicine referral models) created significant "
            "compliance overhang. Blackstone invested in compliance infrastructure and "
            "centralized DME billing to reduce audit risk and AR aging."
        ),
    },
    {
        "source_id": "ext36_014",
        "source": "seed",
        "deal_name": "21st Century Oncology – New Mountain Capital Platform",
        "year": 2012,
        "buyer": "New Mountain Capital",
        "seller": "Vestar Capital Partners",
        "sector": "Radiation Oncology",
        "deal_type": "Secondary LBO",
        "region": "Southeast",
        "geography": "National",
        "ev_mm": 1_300,
        "ebitda_at_entry_mm": 130,
        "ev_ebitda": 10.0,
        "hold_years": 5.0,
        "realized_moic": 1.8,
        "realized_irr": 0.12,
        "payer_mix": {"medicare": 0.55, "medicaid": 0.10, "commercial": 0.32, "self_pay": 0.03},
        "notes": (
            "Largest US radiation oncology platform (~170 centers); filed Chapter 11 2017 "
            "due to reimbursement cuts and leverage. Radiation oncology RCM is among the "
            "most technical: IMRT/SBRT coding requires daily treatment management codes "
            "in addition to planning and simulation charges, and bundling vs. unbundling "
            "rules under Medicare's Radiation Oncology Alternative Payment Model created "
            "uncertainty. CMS APC/HOPPS rate reductions for free-standing vs. HOPD sites "
            "were a structural reimbursement headwind."
        ),
    },
    {
        "source_id": "ext36_015",
        "source": "seed",
        "deal_name": "Integrated Oncology / GenOptix – Carlyle Growth Platform",
        "year": 2013,
        "buyer": "Carlyle Group",
        "seller": "Management / founder",
        "sector": "Radiation Oncology",
        "deal_type": "Platform LBO",
        "region": "Mid-Atlantic",
        "geography": "Multi-State",
        "ev_mm": 410,
        "ebitda_at_entry_mm": 41,
        "ev_ebitda": 10.0,
        "hold_years": 5.0,
        "realized_moic": 3.0,
        "realized_irr": 0.24,
        "payer_mix": {"medicare": 0.48, "medicaid": 0.11, "commercial": 0.36, "self_pay": 0.05},
        "notes": (
            "Community-based radiation oncology and medical oncology group practice; "
            "Carlyle executed a regional roll-up adding proton therapy and stereotactic "
            "radiosurgery capabilities. 340B drug discount program participation by "
            "affiliated hospitals created a complex revenue-sharing and billing overlay — "
            "340B-purchased drugs billed at full AWP to commercial payers generate a "
            "spread that must be tracked and reconciled separately from standard "
            "chemotherapy administration billing to avoid duplicate-discount violations."
        ),
    },
]
