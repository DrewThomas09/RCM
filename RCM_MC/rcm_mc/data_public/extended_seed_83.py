"""Extended seed 83: Infusion, IV therapy, and specialty injectable PE deals.

This module contains a curated set of 15 healthcare private equity deal
records focused on the infusion and specialty injectables continuum. The
theme covers:

- Home infusion providers delivering anti-infectives, TPN, IVIG, and
  specialty biologics via clinical nursing organizations and in-home
  pump therapy
- Ambulatory infusion centers (AICs) offering physician-adjacent,
  non-HOPD sites of care for office-administered biologics (Remicade,
  Entyvio, Ocrevus, etc.)
- Specialty pharmacy operators dispensing limited-distribution drugs
  under white-bagging / brown-bagging workflows
- IVIG / SCIG therapy platforms serving neurology, hematology, and PIDD
  populations
- Infusion pharmacy compounders operating under USP <797>/<800>
  sterile compounding standards with 503A/503B capabilities

Infusion economics are distinguished by heavy commercial insurance
exposure (buy-and-bill + ASP+6% Medicare Part B for in-office J-code
drugs, or pharmacy-benefit adjudication for home infusion SCIG and
self-administered biologics), payer-driven site-of-care (SOC) steerage
from HOPD to AIC/home, margin sensitivity to biosimilar substitution
(infliximab, bevacizumab, trastuzumab, pegfilgrastim), drug-pricing risk
from the IRA Medicare negotiation and ASP inflation caps, and operating
leverage from nursing productivity, chair utilization, and payer
contracting. Value creation in PE-backed platforms centers on payer SOC
contracts, specialty-drug limited-distribution access, AIC de novo
expansion, white-bagging workflow orchestration, and URAC/ACHC
accreditation supporting manufacturer hub designations.

Each record captures deal economics (EV, EV/EBITDA, margins), return
profile (MOIC, IRR, hold period), payer mix, regional footprint, sponsor,
realization status, and a short deal narrative. These records are
synthesized for modeling, backtesting, and scenario analysis use cases.
"""

EXTENDED_SEED_DEALS_83 = [
    {
        "company_name": "Cascade Home Infusion Group",
        "sector": "Home Infusion",
        "buyer": "Audax",
        "year": 2020,
        "region": "Pacific",
        "ev_mm": 540.0,
        "ev_ebitda": 13.0,
        "ebitda_mm": 41.54,
        "ebitda_margin": 0.22,
        "revenue_mm": 188.82,
        "hold_years": 4.5,
        "moic": 2.5,
        "irr": 0.2258,
        "status": "Active",
        "payer_mix": {"commercial": 0.62, "medicare": 0.22, "medicaid": 0.11, "self_pay": 0.05},
        "comm_pct": 0.62,
        "deal_narrative": (
            "Pacific Northwest home infusion platform delivering anti-infective, "
            "TPN, IVIG, and biologic therapies through a URAC-accredited specialty "
            "pharmacy and 18 ambulatory infusion suites. Growth thesis leverages "
            "commercial payer AIC site-of-care steerage programs shifting Remicade "
            "and Entyvio volume out of HOPD, with buy-and-bill economics preserved "
            "under ASP+ contracting."
        ),
    },
    {
        "company_name": "BlueHarbor Specialty Injectables",
        "sector": "Specialty Injectables",
        "buyer": "Warburg Pincus",
        "year": 2018,
        "region": "National",
        "ev_mm": 680.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 46.9,
        "ebitda_margin": 0.24,
        "revenue_mm": 195.42,
        "hold_years": 5.5,
        "moic": 3.1,
        "irr": 0.2284,
        "status": "Realized",
        "payer_mix": {"commercial": 0.65, "medicare": 0.20, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.65,
        "deal_narrative": (
            "National specialty injectables platform with limited-distribution "
            "access to oncology and rare-disease biologics and a hub-services "
            "offering supporting manufacturer patient support programs. Exit thesis "
            "delivered on commercial payer white-bagging expansion and disciplined "
            "navigation of biosimilar Herceptin/Avastin substitution that preserved "
            "gross margin despite ASP erosion on the reference molecules."
        ),
    },
    {
        "company_name": "Piedmont Ambulatory Infusion",
        "sector": "Ambulatory Infusion",
        "buyer": "Shore Capital",
        "year": 2022,
        "region": "Southeast",
        "ev_mm": 195.0,
        "ev_ebitda": 12.0,
        "ebitda_mm": 16.25,
        "ebitda_margin": 0.19,
        "revenue_mm": 85.53,
        "hold_years": 3.0,
        "moic": 1.6,
        "irr": 0.1696,
        "status": "Active",
        "payer_mix": {"commercial": 0.58, "medicare": 0.24, "medicaid": 0.13, "self_pay": 0.05},
        "comm_pct": 0.58,
        "deal_narrative": (
            "Southeast AIC roll-up of 14 physician-adjacent infusion centers "
            "across the Carolinas, Georgia, and Tennessee, serving rheumatology, "
            "GI, and neurology referrals. Thesis is payer site-of-care steerage "
            "from hospital outpatient to AIC (30-50% total cost-of-care savings) "
            "combined with commercial buy-and-bill margin on J-code biologics and "
            "biosimilar Inflectra/Avsola adoption."
        ),
    },
    {
        "company_name": "LakeShore IVIG Partners",
        "sector": "IVIG Therapy",
        "buyer": "TA Associates",
        "year": 2019,
        "region": "Midwest",
        "ev_mm": 420.0,
        "ev_ebitda": 12.8,
        "ebitda_mm": 32.81,
        "ebitda_margin": 0.21,
        "revenue_mm": 156.24,
        "hold_years": 5.0,
        "moic": 2.9,
        "irr": 0.2373,
        "status": "Realized",
        "payer_mix": {"commercial": 0.60, "medicare": 0.23, "medicaid": 0.12, "self_pay": 0.05},
        "comm_pct": 0.60,
        "deal_narrative": (
            "Midwest IVIG and SCIG therapy platform serving CIDP, MMN, and PIDD "
            "populations through a mix of home infusion, AIC, and white-bagged "
            "ambulatory settings. Scarce-product sourcing relationships with plasma "
            "fractionators (Takeda, Grifols, CSL) supported supply continuity during "
            "the 2019-2020 IVIG shortage and drove premium commercial margin at exit."
        ),
    },
    {
        "company_name": "Summit Peak Infusion Pharmacy",
        "sector": "Infusion Pharmacy",
        "buyer": "Cressey",
        "year": 2021,
        "region": "West",
        "ev_mm": 310.0,
        "ev_ebitda": 11.5,
        "ebitda_mm": 26.96,
        "ebitda_margin": 0.17,
        "revenue_mm": 158.59,
        "hold_years": 3.5,
        "moic": 1.9,
        "irr": 0.2013,
        "status": "Active",
        "payer_mix": {"commercial": 0.55, "medicare": 0.26, "medicaid": 0.14, "self_pay": 0.05},
        "comm_pct": 0.55,
        "deal_narrative": (
            "West Coast 503A/503B compounding infusion pharmacy serving hospital, "
            "clinic, and home infusion channels. Investment thesis anchored on USP "
            "<797>/<800> sterile compounding compliance, brown-bagging workflow for "
            "health-system partners, and expansion into patient-specific oncology "
            "admixtures where biosimilar bevacizumab adoption enables margin share."
        ),
    },
    {
        "company_name": "Juniper Home IV Services",
        "sector": "Home Infusion",
        "buyer": "Harren",
        "year": 2022,
        "region": "Southwest",
        "ev_mm": 95.0,
        "ev_ebitda": 10.5,
        "ebitda_mm": 9.05,
        "ebitda_margin": 0.16,
        "revenue_mm": 56.56,
        "hold_years": 2.5,
        "moic": 1.5,
        "irr": 0.1761,
        "status": "Held",
        "payer_mix": {"commercial": 0.52, "medicare": 0.28, "medicaid": 0.15, "self_pay": 0.05},
        "comm_pct": 0.52,
        "deal_narrative": (
            "Southwest regional home infusion operator serving Arizona, New Mexico, "
            "and West Texas with a clinical nursing organization and CMS-recognized "
            "home infusion supplier designation under the 21st Century Cures Act. "
            "Early hold focused on expanding buy-and-bill anti-infective and SCIG "
            "volume while navigating Medicare Part B home infusion transitional "
            "reimbursement pressure."
        ),
    },
    {
        "company_name": "HarborLight Ambulatory Infusion",
        "sector": "Ambulatory Infusion",
        "buyer": "Nautic",
        "year": 2020,
        "region": "Northeast",
        "ev_mm": 155.0,
        "ev_ebitda": 11.8,
        "ebitda_mm": 13.14,
        "ebitda_margin": 0.18,
        "revenue_mm": 73.0,
        "hold_years": 4.0,
        "moic": 2.0,
        "irr": 0.1892,
        "status": "Active",
        "payer_mix": {"commercial": 0.60, "medicare": 0.22, "medicaid": 0.13, "self_pay": 0.05},
        "comm_pct": 0.60,
        "deal_narrative": (
            "Northeast AIC platform of 10 infusion centers in Massachusetts, "
            "Connecticut, and New York serving rheumatology and neurology referrals "
            "for Ocrevus, Tysabri, Actemra, and Entyvio. Commercial payer site-of-"
            "care contracts (BCBS, Cigna, UHC) have migrated volume out of HOPD "
            "while maintaining physician supervision aligned to CPT 96365-96368 "
            "infusion administration codes."
        ),
    },
    {
        "company_name": "Meridian National Infusion",
        "sector": "Home Infusion",
        "buyer": "Welsh Carson",
        "year": 2017,
        "region": "National",
        "ev_mm": 770.0,
        "ev_ebitda": 15.2,
        "ebitda_mm": 50.66,
        "ebitda_margin": 0.25,
        "revenue_mm": 202.64,
        "hold_years": 5.5,
        "moic": 3.1,
        "irr": 0.2284,
        "status": "Realized",
        "payer_mix": {"commercial": 0.63, "medicare": 0.22, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.63,
        "deal_narrative": (
            "National home and alternate-site infusion platform serving 30+ states "
            "with URAC/ACHC-accredited specialty pharmacy, 40+ AICs, and a "
            "manufacturer hub-services arm. Payer site-of-care steerage programs "
            "and limited-distribution access to new-launch biologics (Ocrevus, "
            "Vyepti, Leqembi) drove mid-teens organic CAGR and supported a 3.1x MOIC "
            "exit to a strategic PBM-adjacent acquirer."
        ),
    },
    {
        "company_name": "Apex Specialty Biologics",
        "sector": "Specialty Injectables",
        "buyer": "KKR",
        "year": 2016,
        "region": "National",
        "ev_mm": 825.0,
        "ev_ebitda": 16.5,
        "ebitda_mm": 50.0,
        "ebitda_margin": 0.27,
        "revenue_mm": 185.19,
        "hold_years": 6.5,
        "moic": 3.5,
        "irr": 0.2126,
        "status": "Realized",
        "payer_mix": {"commercial": 0.68, "medicare": 0.18, "medicaid": 0.09, "self_pay": 0.05},
        "comm_pct": 0.68,
        "deal_narrative": (
            "Multi-channel specialty injectables and pharmacy platform spanning "
            "oncology, immunology, and rare-disease categories with deep limited-"
            "distribution manufacturer relationships. Value creation navigated "
            "biosimilar substitution across infliximab, trastuzumab, and "
            "pegfilgrastim while growing white-bagging and brown-bagging contract "
            "volume with commercial health plans steering off buy-and-bill economics."
        ),
    },
    {
        "company_name": "Keystone Home Infusion Co",
        "sector": "Home Infusion",
        "buyer": "Varsity",
        "year": 2023,
        "region": "Midwest",
        "ev_mm": 75.0,
        "ev_ebitda": 10.0,
        "ebitda_mm": 7.5,
        "ebitda_margin": 0.17,
        "revenue_mm": 44.12,
        "hold_years": 2.5,
        "moic": 1.5,
        "irr": 0.1761,
        "status": "Held",
        "payer_mix": {"commercial": 0.50, "medicare": 0.30, "medicaid": 0.15, "self_pay": 0.05},
        "comm_pct": 0.50,
        "deal_narrative": (
            "Ohio-Indiana-Kentucky home infusion operator with community-pharmacy "
            "adjacency and a field nursing organization serving anti-infective, TPN, "
            "and SCIG populations. Early hold is executing on Medicare Part B home "
            "infusion G-code reimbursement capture and targeted AIC de novo builds "
            "for commercially-insured biologic referrals from regional IDNs."
        ),
    },
    {
        "company_name": "Lakeview IVIG & Neurology Infusion",
        "sector": "IVIG Therapy",
        "buyer": "Silversmith",
        "year": 2022,
        "region": "Northeast",
        "ev_mm": 130.0,
        "ev_ebitda": 11.2,
        "ebitda_mm": 11.61,
        "ebitda_margin": 0.18,
        "revenue_mm": 64.5,
        "hold_years": 3.0,
        "moic": 1.6,
        "irr": 0.1696,
        "status": "Active",
        "payer_mix": {"commercial": 0.58, "medicare": 0.25, "medicaid": 0.12, "self_pay": 0.05},
        "comm_pct": 0.58,
        "deal_narrative": (
            "Northeast neurology-focused IVIG and biologics infusion platform "
            "co-located with MS and neuromuscular referral practices. Thesis "
            "leverages payer AIC site-of-care steerage mandates, white-bagged "
            "product acquisition from specialty pharmacy partners, and expansion of "
            "SCIG self-administration programs that shift eligible CIDP patients to "
            "lower-cost maintenance therapy."
        ),
    },
    {
        "company_name": "Granite State Ambulatory Infusion",
        "sector": "Ambulatory Infusion",
        "buyer": "New Mountain",
        "year": 2019,
        "region": "Northeast",
        "ev_mm": 365.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 27.04,
        "ebitda_margin": 0.22,
        "revenue_mm": 122.91,
        "hold_years": 4.5,
        "moic": 2.4,
        "irr": 0.2148,
        "status": "Realized",
        "payer_mix": {"commercial": 0.62, "medicare": 0.22, "medicaid": 0.11, "self_pay": 0.05},
        "comm_pct": 0.62,
        "deal_narrative": (
            "New England AIC platform of 22 non-HOPD infusion centers with "
            "integrated specialty pharmacy buy-and-bill operations. Commercial "
            "payer site-of-care programs and disciplined biosimilar conversion to "
            "Renflexis and Zarxio accelerated EBITDA margin expansion from ~17% to "
            "~22% and delivered a 2.4x MOIC exit to a strategic infusion consolidator."
        ),
    },
    {
        "company_name": "Gulf Coast Infusion Pharmacy",
        "sector": "Infusion Pharmacy",
        "buyer": "Frazier",
        "year": 2020,
        "region": "Southeast",
        "ev_mm": 255.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 20.4,
        "ebitda_margin": 0.20,
        "revenue_mm": 102.0,
        "hold_years": 5.0,
        "moic": 2.7,
        "irr": 0.2198,
        "status": "Active",
        "payer_mix": {"commercial": 0.57, "medicare": 0.25, "medicaid": 0.13, "self_pay": 0.05},
        "comm_pct": 0.57,
        "deal_narrative": (
            "Gulf South infusion pharmacy operator combining 503A patient-specific "
            "compounding with 503B outsourcing-facility registration serving hospital "
            "and AIC customers. Value creation driven by USP <800> hazardous-drug "
            "readiness, white-bagging adjudication infrastructure for commercial "
            "plans, and expansion into brown-bagged biologics for community "
            "rheumatology and GI practices."
        ),
    },
    {
        "company_name": "Cedar Valley Home IV",
        "sector": "Home Infusion",
        "buyer": "Webster Equity",
        "year": 2023,
        "region": "US",
        "ev_mm": 110.0,
        "ev_ebitda": 10.8,
        "ebitda_mm": 10.19,
        "ebitda_margin": 0.16,
        "revenue_mm": 63.69,
        "hold_years": 3.5,
        "moic": 1.9,
        "irr": 0.2013,
        "status": "Active",
        "payer_mix": {"commercial": 0.51, "medicare": 0.29, "medicaid": 0.15, "self_pay": 0.05},
        "comm_pct": 0.51,
        "deal_narrative": (
            "Multi-state home infusion operator emerging from carve-out of a regional "
            "health system's specialty pharmacy and home infusion business. Thesis "
            "focuses on re-contracting with commercial payers around competitive "
            "site-of-care rates, expanding AIC chair capacity for brown-bagged "
            "biologics, and capturing Medicare Part B home infusion G-code "
            "professional-services reimbursement."
        ),
    },
    {
        "company_name": "Crescent Specialty Infusion",
        "sector": "Specialty Injectables",
        "buyer": "Thomas H Lee",
        "year": 2018,
        "region": "Southeast",
        "ev_mm": 595.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 42.5,
        "ebitda_margin": 0.23,
        "revenue_mm": 184.78,
        "hold_years": 6.0,
        "moic": 3.0,
        "irr": 0.2009,
        "status": "Realized",
        "payer_mix": {"commercial": 0.66, "medicare": 0.20, "medicaid": 0.09, "self_pay": 0.05},
        "comm_pct": 0.66,
        "deal_narrative": (
            "Southeast specialty injectables and AIC platform serving oncology, "
            "immunology, and neurology with 30+ infusion chairs, URAC accreditation, "
            "and limited-distribution manufacturer designations. A disciplined "
            "response to IRA Medicare negotiation signaling, biosimilar trastuzumab "
            "conversion, and commercial payer white-bagging mandates preserved "
            "gross margin and delivered a 3.0x MOIC at exit to a national consolidator."
        ),
    },
]
