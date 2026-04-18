"""Extended seed 84: Orthopedic rehab, physical therapy, and sports medicine PE deals.

This module contains a curated set of 15 healthcare private equity deal
records focused on the outpatient musculoskeletal (MSK) rehabilitation
continuum. The theme covers:

- Outpatient physical therapy (PT) clinic platforms operating under
  Medicare Part B fee schedule and commercial PPO contracting
- Sports medicine and orthopedic rehab practices co-located with
  orthopedic surgery groups and ASCs
- Occupational therapy (OT), hand therapy (CHT), and workers'
  compensation-focused rehab
- Pediatric therapy platforms (PT/OT/ST) serving early-intervention,
  school-based, and outpatient populations
- Home-based PT and telehealth-enabled MSK digital-plus-in-person models

Outpatient rehab economics are distinguished by a predominantly
commercial and workers' comp payer mix, Medicare Part B MPPR (Multiple
Procedure Payment Reduction) sensitivity, PTA (physical therapy
assistant) modifier discounts at 85% of PT rates, CPT 97xxx timed-code
productivity dynamics, value-based bundled payment exposure (CJR, BPCI-A
for post-surgical ortho episodes), and clinician supply constraints
driving wage inflation. Value creation in PE-backed platforms centers on
de novo clinic cadence (typically 8-15% of footprint annually), visits-
per-clinician-per-day productivity, MPT-to-PTA mix optimization, payer
contract uplifts, workers' comp carrier and TPA relationships, ortho-
surgeon joint ventures, and tuck-in acquisitions of sub-scale clinic
operators.

Each record captures deal economics (EV, EV/EBITDA, margins), return
profile (MOIC, IRR, hold period), payer mix, regional footprint, sponsor,
realization status, and a short deal narrative. These records are
synthesized for modeling, backtesting, and scenario analysis use cases.
"""

EXTENDED_SEED_DEALS_84 = [
    {
        "company_name": "Summit Physical Therapy Partners",
        "sector": "Physical Therapy",
        "buyer": "Audax",
        "year": 2017,
        "region": "Northeast",
        "ev_mm": 420.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 33.6,
        "ebitda_margin": 0.20,
        "revenue_mm": 168.0,
        "hold_years": 5.5,
        "moic": 2.8,
        "irr": 0.2059,
        "status": "Realized",
        "payer_mix": {"commercial": 0.62, "medicare": 0.22, "medicaid": 0.08, "self_pay": 0.08},
        "comm_pct": 0.62,
        "deal_narrative": (
            "Northeast outpatient PT platform spanning 115 clinics across New York, "
            "New Jersey, and Pennsylvania. Value creation combined a disciplined de "
            "novo cadence of 10-12 clinics per year, MPT-to-PTA staffing mix "
            "rebalancing that lifted visits per therapist from 10.5 to 12.0, and "
            "commercial payer uplifts with BCBS and Aetna that offset Medicare MPPR "
            "and PTA modifier headwinds at exit."
        ),
    },
    {
        "company_name": "Apex Sports Medicine Institute",
        "sector": "Sports Medicine",
        "buyer": "Welsh Carson",
        "year": 2019,
        "region": "Southeast",
        "ev_mm": 685.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 48.93,
        "ebitda_margin": 0.24,
        "revenue_mm": 203.88,
        "hold_years": 5.0,
        "moic": 2.9,
        "irr": 0.2373,
        "status": "Realized",
        "payer_mix": {"commercial": 0.68, "medicare": 0.18, "medicaid": 0.06, "self_pay": 0.08},
        "comm_pct": 0.68,
        "deal_narrative": (
            "Southeast sports medicine and ortho rehab platform integrated with a "
            "70-surgeon orthopedic group and 4 ASCs across Florida, Georgia, and the "
            "Carolinas. Thesis delivered on BPCI-A bundled payment participation for "
            "total joint episodes, sports-team contracts with SEC and high-school "
            "athletic programs, and ancillary-rich per-visit economics driving mid-"
            "20s margin at exit to a strategic MSK consolidator."
        ),
    },
    {
        "company_name": "Heartland Occupational Therapy Group",
        "sector": "Occupational Therapy",
        "buyer": "Shore Capital",
        "year": 2021,
        "region": "Midwest",
        "ev_mm": 125.0,
        "ev_ebitda": 11.5,
        "ebitda_mm": 10.87,
        "ebitda_margin": 0.18,
        "revenue_mm": 60.39,
        "hold_years": 3.0,
        "moic": 1.6,
        "irr": 0.1696,
        "status": "Active",
        "payer_mix": {"commercial": 0.55, "medicare": 0.15, "medicaid": 0.08, "self_pay": 0.22},
        "comm_pct": 0.55,
        "deal_narrative": (
            "Midwest OT and certified hand therapy (CHT) platform serving industrial "
            "rehab and workers' comp referrals across Ohio, Indiana, and Michigan. "
            "Value creation anchored on workers' comp carrier and TPA panel "
            "contracting, functional capacity evaluation (FCE) service-line build-"
            "out, and de novo cadence of 3-4 clinics per year targeting manufacturing "
            "corridor employer density."
        ),
    },
    {
        "company_name": "PinnacleOrtho Rehab Network",
        "sector": "Orthopedic Rehab",
        "buyer": "TA Associates",
        "year": 2018,
        "region": "National",
        "ev_mm": 780.0,
        "ev_ebitda": 15.0,
        "ebitda_mm": 52.0,
        "ebitda_margin": 0.25,
        "revenue_mm": 208.0,
        "hold_years": 6.0,
        "moic": 3.2,
        "irr": 0.2139,
        "status": "Realized",
        "payer_mix": {"commercial": 0.65, "medicare": 0.20, "medicaid": 0.07, "self_pay": 0.08},
        "comm_pct": 0.65,
        "deal_narrative": (
            "National orthopedic rehab platform of 240 clinics co-located with "
            "orthopedic practices and ASCs in 18 states. Hold period executed "
            "disciplined MPT-to-PTA mix optimization to 45/55, BPCI-A and CJR "
            "bundled-payment participation on total knee and hip episodes, and a "
            "digital MSK overlay for post-op remote therapeutic monitoring (RTM) "
            "that preserved margin through Medicare Part B base-rate pressure."
        ),
    },
    {
        "company_name": "LittleSteps Pediatric Therapy",
        "sector": "Pediatric Therapy",
        "buyer": "Silversmith",
        "year": 2022,
        "region": "West",
        "ev_mm": 165.0,
        "ev_ebitda": 12.2,
        "ebitda_mm": 13.52,
        "ebitda_margin": 0.19,
        "revenue_mm": 71.16,
        "hold_years": 3.0,
        "moic": 1.7,
        "irr": 0.1935,
        "status": "Active",
        "payer_mix": {"commercial": 0.48, "medicare": 0.02, "medicaid": 0.42, "self_pay": 0.08},
        "comm_pct": 0.48,
        "deal_narrative": (
            "West Coast pediatric PT/OT/ST platform serving outpatient clinic, "
            "school-based, and early-intervention IDEA Part C populations across "
            "California, Oregon, and Washington. Value creation thesis combines "
            "school-district contract wins for IEP-aligned service delivery, "
            "Medicaid EPSDT-based reimbursement, and de novo clinic expansion into "
            "autism and developmental-delay specialty pods."
        ),
    },
    {
        "company_name": "Cascade Physical Therapy Holdings",
        "sector": "Physical Therapy",
        "buyer": "Nautic",
        "year": 2020,
        "region": "Pacific",
        "ev_mm": 235.0,
        "ev_ebitda": 12.8,
        "ebitda_mm": 18.36,
        "ebitda_margin": 0.19,
        "revenue_mm": 96.63,
        "hold_years": 4.0,
        "moic": 2.1,
        "irr": 0.2038,
        "status": "Active",
        "payer_mix": {"commercial": 0.60, "medicare": 0.25, "medicaid": 0.07, "self_pay": 0.08},
        "comm_pct": 0.60,
        "deal_narrative": (
            "Pacific Northwest outpatient PT platform with 65 clinics across "
            "Washington, Oregon, and Idaho. Growth thesis levers home-based PT "
            "telehealth extension contracted with commercial payers post-PHE, "
            "Medicare G-code RTM billing for post-surgical ortho populations, and "
            "disciplined de novo cadence of 6-8 clinics annually into secondary "
            "markets under-served by hospital-affiliated competitors."
        ),
    },
    {
        "company_name": "BlueRidge Sports & Spine",
        "sector": "Sports Medicine",
        "buyer": "Cressey",
        "year": 2016,
        "region": "Southeast",
        "ev_mm": 340.0,
        "ev_ebitda": 13.0,
        "ebitda_mm": 26.15,
        "ebitda_margin": 0.22,
        "revenue_mm": 118.86,
        "hold_years": 6.5,
        "moic": 3.4,
        "irr": 0.2072,
        "status": "Realized",
        "payer_mix": {"commercial": 0.66, "medicare": 0.18, "medicaid": 0.06, "self_pay": 0.10},
        "comm_pct": 0.66,
        "deal_narrative": (
            "Southeast sports medicine and spine rehab platform serving collegiate "
            "athletic programs and orthopedic spine practices across Tennessee, "
            "Virginia, and the Carolinas. Long hold delivered durable returns via "
            "workers' comp carrier panel expansion, CJR and BPCI-A bundled payment "
            "participation, and ortho-surgeon joint-venture clinic builds that "
            "captured post-op PT referrals at high conversion rates."
        ),
    },
    {
        "company_name": "Meridian Ortho Rehab Services",
        "sector": "Orthopedic Rehab",
        "buyer": "New Mountain",
        "year": 2020,
        "region": "Midwest",
        "ev_mm": 295.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 21.85,
        "ebitda_margin": 0.21,
        "revenue_mm": 104.05,
        "hold_years": 4.5,
        "moic": 2.3,
        "irr": 0.2033,
        "status": "Active",
        "payer_mix": {"commercial": 0.63, "medicare": 0.22, "medicaid": 0.07, "self_pay": 0.08},
        "comm_pct": 0.63,
        "deal_narrative": (
            "Midwest ortho rehab platform of 85 clinics integrated with orthopedic "
            "MSOs across Illinois, Wisconsin, and Minnesota. Thesis leverages value-"
            "based bundled payment participation on total joint episodes, "
            "MPT-to-PTA mix rebalancing toward 50/50 to mitigate Medicare PTA "
            "modifier 85% reimbursement, and commercial payer uplift negotiations "
            "driven by outcomes data (FOTO, KOOS, DASH) benchmarking."
        ),
    },
    {
        "company_name": "Lakeside Work Rehab Partners",
        "sector": "Occupational Therapy",
        "buyer": "Harren",
        "year": 2022,
        "region": "Southwest",
        "ev_mm": 78.0,
        "ev_ebitda": 10.5,
        "ebitda_mm": 7.43,
        "ebitda_margin": 0.17,
        "revenue_mm": 43.71,
        "hold_years": 2.5,
        "moic": 1.5,
        "irr": 0.1761,
        "status": "Held",
        "payer_mix": {"commercial": 0.45, "medicare": 0.10, "medicaid": 0.05, "self_pay": 0.40},
        "comm_pct": 0.45,
        "deal_narrative": (
            "Southwest industrial rehab and workers' comp OT platform serving "
            "Texas, Oklahoma, and New Mexico oil-and-gas, construction, and "
            "logistics employers. Early hold is executing on workers' comp carrier "
            "panel expansion (Texas Mutual, ICW, Travelers), FCE and work-hardening "
            "program build-out, and on-site employer clinic partnerships for post-"
            "injury return-to-work pathway management."
        ),
    },
    {
        "company_name": "Crescent Physical Therapy Group",
        "sector": "Physical Therapy",
        "buyer": "Webster Equity",
        "year": 2023,
        "region": "Southeast",
        "ev_mm": 95.0,
        "ev_ebitda": 10.8,
        "ebitda_mm": 8.8,
        "ebitda_margin": 0.16,
        "revenue_mm": 55.0,
        "hold_years": 2.5,
        "moic": 1.4,
        "irr": 0.1441,
        "status": "Held",
        "payer_mix": {"commercial": 0.58, "medicare": 0.24, "medicaid": 0.10, "self_pay": 0.08},
        "comm_pct": 0.58,
        "deal_narrative": (
            "Gulf South outpatient PT operator assembled from a carve-out of a "
            "regional health system's ambulatory rehab division, with 40 clinics "
            "across Louisiana, Mississippi, and Alabama. Early hold focused on "
            "commercial payer re-contracting at market rates, visits-per-therapist "
            "productivity recovery to 11.0+, and de novo cadence entering secondary "
            "MSA markets adjacent to existing clinic clusters."
        ),
    },
    {
        "company_name": "Granite Sports Performance",
        "sector": "Sports Medicine",
        "buyer": "Frazier",
        "year": 2019,
        "region": "Northeast",
        "ev_mm": 265.0,
        "ev_ebitda": 13.2,
        "ebitda_mm": 20.08,
        "ebitda_margin": 0.23,
        "revenue_mm": 87.30,
        "hold_years": 5.0,
        "moic": 2.6,
        "irr": 0.2106,
        "status": "Realized",
        "payer_mix": {"commercial": 0.70, "medicare": 0.14, "medicaid": 0.06, "self_pay": 0.10},
        "comm_pct": 0.70,
        "deal_narrative": (
            "New England sports medicine and performance platform serving NCAA "
            "D1 athletic programs, professional sports teams, and commercially "
            "insured orthopedic referrals. Exit thesis delivered on ortho-surgeon "
            "joint-venture clinic expansion, premium cash-pay athletic performance "
            "and return-to-sport program monetization, and BPCI-A total joint "
            "bundle participation lifting post-op volume capture."
        ),
    },
    {
        "company_name": "Brightside Pediatric Therapy",
        "sector": "Pediatric Therapy",
        "buyer": "Varsity",
        "year": 2021,
        "region": "Southeast",
        "ev_mm": 68.0,
        "ev_ebitda": 11.0,
        "ebitda_mm": 6.18,
        "ebitda_margin": 0.17,
        "revenue_mm": 36.35,
        "hold_years": 3.5,
        "moic": 1.6,
        "irr": 0.1437,
        "status": "Active",
        "payer_mix": {"commercial": 0.42, "medicare": 0.01, "medicaid": 0.50, "self_pay": 0.07},
        "comm_pct": 0.42,
        "deal_narrative": (
            "Southeast pediatric PT/OT/ST platform focused on school-based "
            "contracting under IDEA Part B and Medicaid-financed early-intervention "
            "services across Florida, Georgia, and the Carolinas. Value creation "
            "levered school-district RFP wins, autism-specialty pod build-out, and "
            "clinician recruitment pipelines tied to university DPT and OTD "
            "affiliate programs to combat sector-wide pediatric therapist scarcity."
        ),
    },
    {
        "company_name": "HorizonOrtho Rehab Holdings",
        "sector": "Orthopedic Rehab",
        "buyer": "KKR",
        "year": 2017,
        "region": "National",
        "ev_mm": 820.0,
        "ev_ebitda": 16.0,
        "ebitda_mm": 51.25,
        "ebitda_margin": 0.27,
        "revenue_mm": 189.81,
        "hold_years": 6.0,
        "moic": 3.1,
        "irr": 0.2075,
        "status": "Realized",
        "payer_mix": {"commercial": 0.67, "medicare": 0.19, "medicaid": 0.06, "self_pay": 0.08},
        "comm_pct": 0.67,
        "deal_narrative": (
            "National ortho rehab and PT platform scaled from 180 to 420 clinics "
            "across 22 states during hold, with deep orthopedic MSO joint ventures "
            "and a proprietary digital MSK care-navigation overlay. Value creation "
            "delivered on BPCI-A and CJR bundled payment participation, commercial "
            "payer value-based contracting tied to FOTO outcome benchmarks, and "
            "disciplined MPT-to-PTA mix that supported best-in-class 27% margin."
        ),
    },
    {
        "company_name": "StrideWell Home PT Services",
        "sector": "Physical Therapy",
        "buyer": "Thomas H Lee",
        "year": 2018,
        "region": "National",
        "ev_mm": 520.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 35.86,
        "ebitda_margin": 0.23,
        "revenue_mm": 155.91,
        "hold_years": 5.5,
        "moic": 2.7,
        "irr": 0.1979,
        "status": "Realized",
        "payer_mix": {"commercial": 0.55, "medicare": 0.30, "medicaid": 0.08, "self_pay": 0.07},
        "comm_pct": 0.55,
        "deal_narrative": (
            "National home-based PT platform delivering in-home and telehealth-"
            "enabled rehab to post-acute ortho and chronic-MSK populations through "
            "Medicare Advantage, commercial, and value-based bundled-payment "
            "channels. Exit thesis scaled home-visit density through proprietary "
            "routing software, captured RTM CPT G-code reimbursement, and expanded "
            "payer partnerships with MA plans steering post-op ortho episodes home."
        ),
    },
    {
        "company_name": "Cornerstone Sports Rehab",
        "sector": "Sports Medicine",
        "buyer": "Warburg Pincus",
        "year": 2016,
        "region": "National",
        "ev_mm": 605.0,
        "ev_ebitda": 14.8,
        "ebitda_mm": 40.88,
        "ebitda_margin": 0.26,
        "revenue_mm": 157.23,
        "hold_years": 6.5,
        "moic": 3.5,
        "irr": 0.2126,
        "status": "Realized",
        "payer_mix": {"commercial": 0.69, "medicare": 0.15, "medicaid": 0.06, "self_pay": 0.10},
        "comm_pct": 0.69,
        "deal_narrative": (
            "Multi-state sports medicine and ortho rehab platform with 160 clinics "
            "embedded alongside orthopedic surgery groups and ASCs. Long hold "
            "executed a disciplined de novo cadence of 12-15 clinics per year, "
            "BPCI-A total knee and hip bundled-payment participation, commercial "
            "payer value-based contracts tied to outcome benchmarks, and ortho "
            "joint-venture clinic builds that delivered a 3.5x MOIC at exit."
        ),
    },
]
