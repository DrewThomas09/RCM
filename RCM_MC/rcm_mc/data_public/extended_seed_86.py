"""Extended seed 86: Dialysis, kidney care, and nephrology PE deals.

This module contains a curated set of 15 healthcare private equity deal
records focused on the end-stage renal disease (ESRD) and chronic
kidney disease (CKD) care continuum. The theme covers:

- In-center hemodialysis clinic platforms operating under the ESRD
  Prospective Payment System (PPS) bundled rate and Medicare Advantage
  capitated contracts
- Home dialysis operators (peritoneal dialysis, home hemodialysis)
  accelerating the Advancing American Kidney Health (AAKH) home
  modality shift from ~12% to the HHS 80% home-or-transplant target
- Value-based kidney care management platforms participating in the
  CMS Kidney Care Choices (KCC) and Comprehensive Kidney Care
  Contracting (CKCC) models for CKD stage 4-5 and ESRD populations
- Nephrology physician practice management (PPM) platforms
  consolidating nephrology groups with integrated dialysis JVs
- Vascular access centers delivering AV fistula/graft placement,
  endovascular interventions, and joint ventures with dialysis operators

Dialysis and kidney care economics are distinguished by a predominantly
Medicare-financed payer mix (ESRD beneficiaries are Medicare-eligible
regardless of age after 3 months), ESRD PPS bundled-rate sensitivity,
commercial payer 30-month coordination-of-benefits window driving margin
concentration, Transitional Drug Add-on Payment Adjustment (TDAPA) and
Transitional Add-on Payment Adjustment for New and Innovative Equipment
and Supplies (TPNIES) policy exposure, home modality mix economics
(peritoneal dialysis payer yield vs. in-center HD), CKCC shared-savings
upside, and vascular access procedure volume. Value creation in PE-backed
kidney-care platforms centers on home modality penetration, CKCC and
KCC model participation, nephrologist JV alignment, vascular access
joint ventures, TDAPA formulary management, commercial payer 30-month
capture optimization, and de novo clinic expansion into under-penetrated
CKD-dense geographies.

Each record captures deal economics (EV, EV/EBITDA, margins), return
profile (MOIC, IRR, hold period), payer mix, regional footprint, sponsor,
realization status, and a short deal narrative. These records are
synthesized for modeling, backtesting, and scenario analysis use cases.
"""

EXTENDED_SEED_DEALS_86 = [
    {
        "company_name": "Meridian Dialysis Partners",
        "sector": "Dialysis Center",
        "buyer": "Welsh Carson",
        "year": 2018,
        "region": "Southeast",
        "ev_mm": 420.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 31.11,
        "ebitda_margin": 0.22,
        "revenue_mm": 141.41,
        "hold_years": 5.5,
        "moic": 2.7,
        "irr": 0.1979,
        "status": "Realized",
        "payer_mix": {"commercial": 0.22, "medicare": 0.62, "medicaid": 0.12, "self_pay": 0.04},
        "comm_pct": 0.22,
        "deal_narrative": (
            "Southeast in-center hemodialysis platform spanning 88 clinics across "
            "Florida, Georgia, and the Carolinas operating under the ESRD "
            "Prospective Payment System bundled rate. Value creation optimized "
            "commercial 30-month coordination-of-benefits capture, executed a "
            "home modality shift from 11% to 22% of census consistent with "
            "Advancing American Kidney Health targets, and added three vascular "
            "access JVs with local interventional nephrology groups at exit."
        ),
    },
    {
        "company_name": "Cascade Home Dialysis Services",
        "sector": "Home Dialysis",
        "buyer": "Frazier",
        "year": 2020,
        "region": "Pacific",
        "ev_mm": 285.0,
        "ev_ebitda": 12.0,
        "ebitda_mm": 23.75,
        "ebitda_margin": 0.20,
        "revenue_mm": 118.75,
        "hold_years": 4.0,
        "moic": 2.1,
        "irr": 0.2038,
        "status": "Active",
        "payer_mix": {"commercial": 0.24, "medicare": 0.60, "medicaid": 0.13, "self_pay": 0.03},
        "comm_pct": 0.24,
        "deal_narrative": (
            "Pacific Northwest home dialysis operator focused on peritoneal "
            "dialysis and home hemodialysis training across Washington, Oregon, "
            "and Northern California. Growth thesis accelerates the Advancing "
            "American Kidney Health home-modality shift toward the HHS 80% "
            "home-or-transplant target, leveraging ESRD PPS bundled-payment "
            "economics and nephrologist training-unit partnerships to drive "
            "PD catheter placement volume and home-to-census conversion."
        ),
    },
    {
        "company_name": "Apex Kidney Care Management",
        "sector": "Kidney Care Management",
        "buyer": "New Mountain",
        "year": 2019,
        "region": "National",
        "ev_mm": 640.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 44.14,
        "ebitda_margin": 0.24,
        "revenue_mm": 183.92,
        "hold_years": 6.0,
        "moic": 3.1,
        "irr": 0.2075,
        "status": "Realized",
        "payer_mix": {"commercial": 0.26, "medicare": 0.58, "medicaid": 0.13, "self_pay": 0.03},
        "comm_pct": 0.26,
        "deal_narrative": (
            "National value-based kidney care management platform participating "
            "in the CMS Kidney Care Choices (KCC) and Comprehensive Kidney Care "
            "Contracting (CKCC) models across 14 states covering CKD stage 4-5 "
            "and ESRD lives. Long hold delivered on CKCC shared-savings capture, "
            "home modality conversion consistent with Advancing American Kidney "
            "Health targets, and Medicare Advantage capitated kidney-care "
            "contracting at premium per-member per-month economics."
        ),
    },
    {
        "company_name": "Heartland Nephrology Associates",
        "sector": "Nephrology Practice",
        "buyer": "Shore Capital",
        "year": 2021,
        "region": "Midwest",
        "ev_mm": 180.0,
        "ev_ebitda": 11.5,
        "ebitda_mm": 15.65,
        "ebitda_margin": 0.19,
        "revenue_mm": 82.37,
        "hold_years": 3.5,
        "moic": 1.8,
        "irr": 0.1829,
        "status": "Active",
        "payer_mix": {"commercial": 0.25, "medicare": 0.60, "medicaid": 0.12, "self_pay": 0.03},
        "comm_pct": 0.25,
        "deal_narrative": (
            "Midwest nephrology physician practice management platform spanning "
            "Ohio, Indiana, and Michigan with 55 nephrologists and integrated "
            "dialysis joint-venture economics. Value creation builds out CKCC "
            "model participation for CKD stage 4-5 attribution, vascular access "
            "JV formation for AV fistula and graft placement, and home dialysis "
            "training-unit density to capture Advancing American Kidney Health "
            "modality-shift incentives and shared-savings upside."
        ),
    },
    {
        "company_name": "Lakeside Vascular Access Centers",
        "sector": "Vascular Access",
        "buyer": "Harren",
        "year": 2023,
        "region": "Southeast",
        "ev_mm": 95.0,
        "ev_ebitda": 10.8,
        "ebitda_mm": 8.8,
        "ebitda_margin": 0.17,
        "revenue_mm": 51.76,
        "hold_years": 2.5,
        "moic": 1.5,
        "irr": 0.1761,
        "status": "Held",
        "payer_mix": {"commercial": 0.20, "medicare": 0.65, "medicaid": 0.12, "self_pay": 0.03},
        "comm_pct": 0.20,
        "deal_narrative": (
            "Southeast vascular access center operator delivering AV fistula and "
            "graft placement, fistulograms, and endovascular interventions for "
            "ESRD patients across Florida, Georgia, and Tennessee. Early hold is "
            "executing on dialysis-operator vascular access JV formation, CKCC "
            "model alignment with participating nephrology groups, and office-"
            "based lab (OBL) site-of-service economics that deliver favorable "
            "reimbursement versus hospital-outpatient-department placements."
        ),
    },
    {
        "company_name": "Summit ESRD Holdings",
        "sector": "Dialysis Center",
        "buyer": "KKR",
        "year": 2017,
        "region": "National",
        "ev_mm": 520.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 37.14,
        "ebitda_margin": 0.23,
        "revenue_mm": 161.48,
        "hold_years": 5.5,
        "moic": 2.8,
        "irr": 0.2059,
        "status": "Realized",
        "payer_mix": {"commercial": 0.23, "medicare": 0.63, "medicaid": 0.11, "self_pay": 0.03},
        "comm_pct": 0.23,
        "deal_narrative": (
            "National independent dialysis platform of 140 in-center hemodialysis "
            "clinics across 18 states acquired as a carve-out from a strategic. "
            "Hold period captured ESRD Prospective Payment System bundled-rate "
            "updates, expanded home modality penetration from 10% to 18% of "
            "census under Advancing American Kidney Health tailwinds, scaled "
            "commercial 30-month coordination-of-benefits economics, and layered "
            "CKCC model participation for upside shared-savings capture."
        ),
    },
    {
        "company_name": "BlueRidge Nephrology Partners",
        "sector": "Nephrology Practice",
        "buyer": "TA Associates",
        "year": 2018,
        "region": "Southeast",
        "ev_mm": 360.0,
        "ev_ebitda": 13.0,
        "ebitda_mm": 27.69,
        "ebitda_margin": 0.21,
        "revenue_mm": 131.86,
        "hold_years": 5.0,
        "moic": 2.5,
        "irr": 0.2011,
        "status": "Realized",
        "payer_mix": {"commercial": 0.26, "medicare": 0.59, "medicaid": 0.12, "self_pay": 0.03},
        "comm_pct": 0.26,
        "deal_narrative": (
            "Southeast nephrology PPM platform of 95 nephrologists and 12 "
            "dialysis JVs across Tennessee, Virginia, and the Carolinas. Exit "
            "thesis delivered on CKCC model enrollment capturing CKD stage 4-5 "
            "attribution, home dialysis modality shift to 20% of census under "
            "Advancing American Kidney Health goals, bundled-payment alignment "
            "with the ESRD Prospective Payment System, and vascular access JV "
            "integration supporting a strategic exit to a diversified operator."
        ),
    },
    {
        "company_name": "Crescent Home Kidney Services",
        "sector": "Home Dialysis",
        "buyer": "Silversmith",
        "year": 2022,
        "region": "Southwest",
        "ev_mm": 145.0,
        "ev_ebitda": 11.8,
        "ebitda_mm": 12.29,
        "ebitda_margin": 0.18,
        "revenue_mm": 68.28,
        "hold_years": 3.0,
        "moic": 1.6,
        "irr": 0.1696,
        "status": "Active",
        "payer_mix": {"commercial": 0.21, "medicare": 0.64, "medicaid": 0.12, "self_pay": 0.03},
        "comm_pct": 0.21,
        "deal_narrative": (
            "Southwest home dialysis operator serving Texas, Oklahoma, and New "
            "Mexico with a peritoneal dialysis-first operating model and home "
            "hemodialysis training units. Value creation executes on the "
            "Advancing American Kidney Health home-modality shift, CKCC model "
            "alignment with partnering nephrology groups, and PD catheter "
            "placement partnerships with vascular access centers to drive "
            "incident-patient home-modality starts versus in-center crashes."
        ),
    },
    {
        "company_name": "Continental Kidney Care",
        "sector": "Kidney Care Management",
        "buyer": "Warburg Pincus",
        "year": 2017,
        "region": "National",
        "ev_mm": 720.0,
        "ev_ebitda": 15.5,
        "ebitda_mm": 46.45,
        "ebitda_margin": 0.26,
        "revenue_mm": 178.65,
        "hold_years": 6.0,
        "moic": 3.2,
        "irr": 0.2139,
        "status": "Realized",
        "payer_mix": {"commercial": 0.27, "medicare": 0.57, "medicaid": 0.13, "self_pay": 0.03},
        "comm_pct": 0.27,
        "deal_narrative": (
            "National value-based kidney-care platform covering 180,000+ "
            "attributed CKD and ESRD lives across CKCC, KCC, and Medicare "
            "Advantage capitated contracts. Long hold scaled CKCC shared-"
            "savings capture, drove home modality penetration to 25% of "
            "attributed ESRD lives in line with Advancing American Kidney "
            "Health targets, and integrated nephrologist-aligned dialysis "
            "and vascular access JVs that underwrote a 3.2x MOIC realization."
        ),
    },
    {
        "company_name": "Granite Dialysis Group",
        "sector": "Dialysis Center",
        "buyer": "Nautic",
        "year": 2020,
        "region": "Northeast",
        "ev_mm": 260.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 20.8,
        "ebitda_margin": 0.20,
        "revenue_mm": 104.0,
        "hold_years": 4.5,
        "moic": 2.2,
        "irr": 0.1915,
        "status": "Active",
        "payer_mix": {"commercial": 0.25, "medicare": 0.60, "medicaid": 0.12, "self_pay": 0.03},
        "comm_pct": 0.25,
        "deal_narrative": (
            "Northeast in-center hemodialysis operator with 48 clinics across "
            "New York, Massachusetts, and Connecticut operating under the ESRD "
            "Prospective Payment System bundle. Hold thesis executes commercial "
            "30-month coordination-of-benefits optimization, home modality "
            "shift consistent with Advancing American Kidney Health targets, "
            "CKCC model participation via nephrology group alignment, and "
            "vascular access JV formation to capture procedural margin."
        ),
    },
    {
        "company_name": "NovaRenal Nephrology Holdings",
        "sector": "Nephrology Practice",
        "buyer": "Cressey",
        "year": 2019,
        "region": "West",
        "ev_mm": 390.0,
        "ev_ebitda": 13.2,
        "ebitda_mm": 29.55,
        "ebitda_margin": 0.22,
        "revenue_mm": 134.32,
        "hold_years": 5.0,
        "moic": 2.6,
        "irr": 0.2106,
        "status": "Realized",
        "payer_mix": {"commercial": 0.27, "medicare": 0.58, "medicaid": 0.12, "self_pay": 0.03},
        "comm_pct": 0.27,
        "deal_narrative": (
            "West Coast nephrology PPM across California, Nevada, and Arizona "
            "with 70 nephrologists and integrated dialysis JV economics. Value "
            "creation delivered on CKCC model enrollment lifting CKD stage 4-5 "
            "attribution, home dialysis training-unit expansion toward "
            "Advancing American Kidney Health targets, vascular access JV "
            "formation for AV fistula procedural revenue, and bundled-payment "
            "alignment with the ESRD Prospective Payment System at exit."
        ),
    },
    {
        "company_name": "Sentinel Vascular Access Network",
        "sector": "Vascular Access",
        "buyer": "Varsity",
        "year": 2022,
        "region": "Midwest",
        "ev_mm": 75.0,
        "ev_ebitda": 10.5,
        "ebitda_mm": 7.14,
        "ebitda_margin": 0.16,
        "revenue_mm": 44.62,
        "hold_years": 3.0,
        "moic": 1.5,
        "irr": 0.1447,
        "status": "Active",
        "payer_mix": {"commercial": 0.19, "medicare": 0.66, "medicaid": 0.12, "self_pay": 0.03},
        "comm_pct": 0.19,
        "deal_narrative": (
            "Midwest vascular access center operator delivering AV fistula "
            "creation, graft placement, and endovascular interventions across "
            "Illinois, Indiana, and Missouri. Value creation executes on a "
            "dialysis-operator vascular access JV rollup strategy, ESRD "
            "Prospective Payment System bundled-rate alignment, CKCC model "
            "participation with nephrology group partners, and office-based "
            "lab site-of-service migration for favorable procedural margins."
        ),
    },
    {
        "company_name": "Pinnacle Dialysis Holdings",
        "sector": "Dialysis Center",
        "buyer": "DaVita",
        "year": 2016,
        "region": "National",
        "ev_mm": 805.0,
        "ev_ebitda": 16.0,
        "ebitda_mm": 50.31,
        "ebitda_margin": 0.27,
        "revenue_mm": 186.33,
        "hold_years": 6.5,
        "moic": 3.5,
        "irr": 0.2126,
        "status": "Realized",
        "payer_mix": {"commercial": 0.24, "medicare": 0.62, "medicaid": 0.11, "self_pay": 0.03},
        "comm_pct": 0.24,
        "deal_narrative": (
            "National independent dialysis platform scaled from 160 to 320 "
            "clinics across 24 states during hold, with integrated home "
            "dialysis training units and vascular access JVs. Long-hold value "
            "creation executed a home modality shift to 24% of census under "
            "Advancing American Kidney Health, commercial 30-month "
            "coordination-of-benefits capture discipline, ESRD Prospective "
            "Payment System bundled-rate margin optimization, and CKCC "
            "participation that supported a 3.5x MOIC strategic exit."
        ),
    },
    {
        "company_name": "Horizon Kidney Care Solutions",
        "sector": "Kidney Care Management",
        "buyer": "Audax",
        "year": 2021,
        "region": "Southeast",
        "ev_mm": 235.0,
        "ev_ebitda": 12.2,
        "ebitda_mm": 19.26,
        "ebitda_margin": 0.19,
        "revenue_mm": 101.37,
        "hold_years": 3.5,
        "moic": 1.9,
        "irr": 0.2013,
        "status": "Active",
        "payer_mix": {"commercial": 0.24, "medicare": 0.61, "medicaid": 0.12, "self_pay": 0.03},
        "comm_pct": 0.24,
        "deal_narrative": (
            "Southeast value-based kidney care management platform contracting "
            "with Medicare Advantage plans and participating in the CKCC model "
            "across Florida, Georgia, and the Carolinas. Growth thesis scales "
            "CKD stage 4-5 attribution, accelerates home modality conversion "
            "in line with Advancing American Kidney Health targets, deepens "
            "nephrologist alignment economics, and layers vascular access JV "
            "revenue through partnered interventional nephrology centers."
        ),
    },
    {
        "company_name": "Pacific Renal Network",
        "sector": "Nephrology Practice",
        "buyer": "Thomas H Lee",
        "year": 2019,
        "region": "Pacific",
        "ev_mm": 465.0,
        "ev_ebitda": 14.2,
        "ebitda_mm": 32.75,
        "ebitda_margin": 0.25,
        "revenue_mm": 131.0,
        "hold_years": 5.0,
        "moic": 2.7,
        "irr": 0.2198,
        "status": "Realized",
        "payer_mix": {"commercial": 0.28, "medicare": 0.57, "medicaid": 0.12, "self_pay": 0.03},
        "comm_pct": 0.28,
        "deal_narrative": (
            "Pacific nephrology PPM platform of 85 nephrologists with "
            "integrated dialysis JVs and home modality training units across "
            "Washington, Oregon, and Northern California. Exit thesis delivered "
            "on CKCC model shared-savings capture, home modality penetration "
            "of 26% of attributed ESRD lives consistent with Advancing "
            "American Kidney Health targets, bundled-payment alignment under "
            "the ESRD Prospective Payment System, and vascular access JV scale."
        ),
    },
]
