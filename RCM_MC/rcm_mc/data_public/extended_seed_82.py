"""Extended seed 82: Home health, hospice, and palliative care PE deals.

This module contains a curated set of 15 healthcare private equity deal
records focused on the in-home care continuum. The theme covers:

- Medicare-certified home health agencies (post-acute skilled nursing,
  PT/OT/ST) operating under PDGM
- Hospice providers (Medicare Hospice Benefit, four levels of care) with
  per-beneficiary aggregate cap exposure
- Community-based palliative care programs (interdisciplinary teams
  serving seriously ill patients upstream of hospice)
- Home infusion therapies (ambulatory infusion suites, specialty
  pharmacy enablement)
- Private duty / non-medical home care (companion, personal care, ADL
  support) funded by private pay, LTC insurance, and Medicaid HCBS

Home-based care economics are distinguished by heavy Medicare
concentration (Medicare FFS and Medicare Advantage dominate home health
and hospice), the operational sensitivity to PDGM case-mix weights and
LUPA thresholds in home health, hospice cap compliance and average length
of stay, Medicare Conditions of Participation (CoP) scrutiny, and clinical
labor supply constraints (RN/LPN/HHA). Value creation in PE-backed
platforms centers on de novo/CON-limited market entry, census growth via
referral source density (hospitals, SNFs, ACOs), Medicare Advantage
contracting, clinical productivity (visits per clinician per day), and
tuck-in acquisitions of sub-scale agencies.

Each record captures deal economics (EV, EV/EBITDA, margins), return
profile (MOIC, IRR, hold period), payer mix, regional footprint, sponsor,
realization status, and a short deal narrative. These records are
synthesized for modeling, backtesting, and scenario analysis use cases.
"""

EXTENDED_SEED_DEALS_82 = [
    {
        "company_name": "Evergreen Home Health Partners",
        "sector": "Home Health",
        "buyer": "Audax",
        "year": 2017,
        "region": "Northeast",
        "ev_mm": 385.0,
        "ev_ebitda": 12.0,
        "ebitda_mm": 32.08,
        "ebitda_margin": 0.18,
        "revenue_mm": 178.22,
        "hold_years": 6.0,
        "moic": 2.7,
        "irr": 0.18,
        "status": "Realized",
        "payer_mix": {"commercial": 0.08, "medicare": 0.72, "medicaid": 0.15, "self_pay": 0.05},
        "comm_pct": 0.08,
        "deal_narrative": (
            "Northeast Medicare-certified home health platform spanning 40+ "
            "branches across New England and New York. Thesis executed through "
            "PDGM transition with disciplined case-mix coding, LUPA rate "
            "management, and Medicare Advantage episodic contracting that "
            "offset rate pressure and drove EBITDA margin expansion of ~250 bps."
        ),
    },
    {
        "company_name": "Compassion Hospice Holdings",
        "sector": "Hospice",
        "buyer": "Welsh Carson",
        "year": 2018,
        "region": "Southeast",
        "ev_mm": 625.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 46.30,
        "ebitda_margin": 0.22,
        "revenue_mm": 210.45,
        "hold_years": 5.5,
        "moic": 3.0,
        "irr": 0.2211,
        "status": "Realized",
        "payer_mix": {"commercial": 0.02, "medicare": 0.90, "medicaid": 0.06, "self_pay": 0.02},
        "comm_pct": 0.02,
        "deal_narrative": (
            "Southeastern hospice platform serving ~4,200 ADC across Florida, "
            "Georgia, Alabama, and Tennessee. Careful management of the per-"
            "beneficiary aggregate cap through diversified referral mix (hospital, "
            "SNF, physician, community) and stable ALOS in the 85-95 day band "
            "supported consistent margin delivery and a 3.0x MOIC at exit."
        ),
    },
    {
        "company_name": "Meridian Palliative Care",
        "sector": "Palliative Care",
        "buyer": "New Mountain",
        "year": 2020,
        "region": "National",
        "ev_mm": 180.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 12.41,
        "ebitda_margin": 0.17,
        "revenue_mm": 73.0,
        "hold_years": 3.5,
        "moic": 1.7,
        "irr": 0.1637,
        "status": "Active",
        "payer_mix": {"commercial": 0.22, "medicare": 0.58, "medicaid": 0.15, "self_pay": 0.05},
        "comm_pct": 0.22,
        "deal_narrative": (
            "Community-based palliative care platform contracting with Medicare "
            "Advantage plans and ACOs under capitated and PMPM arrangements. "
            "Interdisciplinary team model (MD, NP, SW, chaplain) drives ED and "
            "hospitalization avoidance, with upstream referral flow feeding "
            "affiliated hospice programs as patients elect the Medicare Hospice Benefit."
        ),
    },
    {
        "company_name": "Heartland Home Infusion",
        "sector": "Home Infusion",
        "buyer": "TA Associates",
        "year": 2019,
        "region": "Midwest",
        "ev_mm": 420.0,
        "ev_ebitda": 13.0,
        "ebitda_mm": 32.31,
        "ebitda_margin": 0.21,
        "revenue_mm": 153.86,
        "hold_years": 5.0,
        "moic": 2.4,
        "irr": 0.1914,
        "status": "Active",
        "payer_mix": {"commercial": 0.55, "medicare": 0.28, "medicaid": 0.12, "self_pay": 0.05},
        "comm_pct": 0.55,
        "deal_narrative": (
            "Midwest home infusion platform delivering anti-infective, TPN, IVIG, "
            "and specialty biologic therapies through a network of 22 ambulatory "
            "infusion suites and a clinical nursing organization. Commercial-heavy "
            "mix insulates from Medicare Part B pricing pressure, with growth "
            "levered to specialty drug pipeline and payer preference for site-of-"
            "care shift out of hospital outpatient departments."
        ),
    },
    {
        "company_name": "Golden Shores Private Duty",
        "sector": "Private Duty Home Care",
        "buyer": "Shore Capital",
        "year": 2021,
        "region": "West",
        "ev_mm": 85.0,
        "ev_ebitda": 11.5,
        "ebitda_mm": 7.39,
        "ebitda_margin": 0.16,
        "revenue_mm": 46.19,
        "hold_years": 3.0,
        "moic": 1.6,
        "irr": 0.1696,
        "status": "Active",
        "payer_mix": {"commercial": 0.06, "medicare": 0.04, "medicaid": 0.32, "self_pay": 0.58},
        "comm_pct": 0.06,
        "deal_narrative": (
            "West Coast non-medical private duty home care agency serving private "
            "pay, long-term care insurance, and Medicaid HCBS waiver clients across "
            "California and Arizona. Growth thesis anchored on caregiver recruitment "
            "and retention programs to combat sector-wide turnover above 65% and on "
            "Medicaid waiver rate increases in 1915(c) programs."
        ),
    },
    {
        "company_name": "Summit Hospice Services",
        "sector": "Hospice",
        "buyer": "Cressey",
        "year": 2016,
        "region": "Southwest",
        "ev_mm": 310.0,
        "ev_ebitda": 11.0,
        "ebitda_mm": 28.18,
        "ebitda_margin": 0.23,
        "revenue_mm": 122.52,
        "hold_years": 6.5,
        "moic": 3.6,
        "irr": 0.2178,
        "status": "Realized",
        "payer_mix": {"commercial": 0.02, "medicare": 0.91, "medicaid": 0.05, "self_pay": 0.02},
        "comm_pct": 0.02,
        "deal_narrative": (
            "Southwest hospice platform scaled from 6 to 28 locations across Texas, "
            "Oklahoma, and New Mexico. Rigorous compliance posture around eligibility "
            "documentation, face-to-face encounter requirements, and hospice cap "
            "monitoring avoided TPE audit disruption and supported a 3.6x MOIC "
            "realized exit to a strategic hospice consolidator."
        ),
    },
    {
        "company_name": "Atlantic Home Health Group",
        "sector": "Home Health",
        "buyer": "Webster Equity",
        "year": 2019,
        "region": "Southeast",
        "ev_mm": 265.0,
        "ev_ebitda": 12.8,
        "ebitda_mm": 20.70,
        "ebitda_margin": 0.19,
        "revenue_mm": 108.95,
        "hold_years": 4.5,
        "moic": 2.2,
        "irr": 0.1915,
        "status": "Active",
        "payer_mix": {"commercial": 0.10, "medicare": 0.68, "medicaid": 0.17, "self_pay": 0.05},
        "comm_pct": 0.10,
        "deal_narrative": (
            "Southeast home health platform operating 30 CON-protected branches "
            "across Florida and the Carolinas. Investment thesis leveraged CON "
            "barriers to entry, hospital and SNF referral density, and clinician "
            "productivity initiatives targeting 5.5-6.0 visits per day while "
            "preserving star ratings and CoP compliance under surveyor scrutiny."
        ),
    },
    {
        "company_name": "Tranquility Hospice & Palliative",
        "sector": "Hospice",
        "buyer": "Nautic",
        "year": 2020,
        "region": "Midwest",
        "ev_mm": 155.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 12.40,
        "ebitda_margin": 0.20,
        "revenue_mm": 62.0,
        "hold_years": 4.0,
        "moic": 1.9,
        "irr": 0.1741,
        "status": "Active",
        "payer_mix": {"commercial": 0.03, "medicare": 0.88, "medicaid": 0.07, "self_pay": 0.02},
        "comm_pct": 0.03,
        "deal_narrative": (
            "Midwest hospice operator with an integrated upstream palliative arm "
            "serving Ohio, Indiana, and Michigan. Dual-program model lengthens "
            "patient relationships from serious-illness diagnosis through end of "
            "life, improving average length of stay toward the cap-efficient 70-"
            "90 day window and supporting margin stability despite routine home "
            "care base-rate pressure."
        ),
    },
    {
        "company_name": "BlueRidge Home Health",
        "sector": "Home Health",
        "buyer": "Harren",
        "year": 2022,
        "region": "Southeast",
        "ev_mm": 110.0,
        "ev_ebitda": 11.8,
        "ebitda_mm": 9.32,
        "ebitda_margin": 0.17,
        "revenue_mm": 54.82,
        "hold_years": 2.5,
        "moic": 1.4,
        "irr": 0.1441,
        "status": "Held",
        "payer_mix": {"commercial": 0.09, "medicare": 0.70, "medicaid": 0.16, "self_pay": 0.05},
        "comm_pct": 0.09,
        "deal_narrative": (
            "Regional Medicare-certified home health agency in Virginia, North "
            "Carolina, and Tennessee. Early hold focused on PDGM 30-day period "
            "optimization, OASIS coding accuracy, and rebalancing institutional "
            "vs. community referral mix to recover from negative PDGM behavioral "
            "adjustment and budget-neutral recalibration headwinds."
        ),
    },
    {
        "company_name": "Sunrise Palliative Network",
        "sector": "Palliative Care",
        "buyer": "Frazier",
        "year": 2021,
        "region": "West",
        "ev_mm": 95.0,
        "ev_ebitda": 15.5,
        "ebitda_mm": 6.13,
        "ebitda_margin": 0.18,
        "revenue_mm": 34.06,
        "hold_years": 3.0,
        "moic": 1.5,
        "irr": 0.1447,
        "status": "Active",
        "payer_mix": {"commercial": 0.28, "medicare": 0.52, "medicaid": 0.15, "self_pay": 0.05},
        "comm_pct": 0.28,
        "deal_narrative": (
            "West Coast home-based palliative care platform contracted with several "
            "Medicare Advantage plans under shared-savings and PMPM models. "
            "Interdisciplinary teams manage advanced illness populations with "
            "documented reductions in 30-day hospitalization and downstream "
            "conversion into the affiliated hospice benefit at clinically "
            "appropriate prognosis thresholds."
        ),
    },
    {
        "company_name": "Cornerstone Hospice Partners",
        "sector": "Hospice",
        "buyer": "KKR",
        "year": 2017,
        "region": "National",
        "ev_mm": 780.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 55.71,
        "ebitda_margin": 0.24,
        "revenue_mm": 232.13,
        "hold_years": 6.0,
        "moic": 2.8,
        "irr": 0.1872,
        "status": "Realized",
        "payer_mix": {"commercial": 0.02, "medicare": 0.89, "medicaid": 0.07, "self_pay": 0.02},
        "comm_pct": 0.02,
        "deal_narrative": (
            "National hospice platform with ~6,500 ADC at exit across 20 states. "
            "Scale economics in clinical management, pharmacy, and DME, combined "
            "with disciplined admissions governance around the six-month terminal "
            "prognosis standard, delivered durable EBITDA margins and supported "
            "a 2.8x MOIC exit to a strategic acquirer."
        ),
    },
    {
        "company_name": "Caring Hands Home Care",
        "sector": "Private Duty Home Care",
        "buyer": "Varsity",
        "year": 2020,
        "region": "Midwest",
        "ev_mm": 60.0,
        "ev_ebitda": 10.5,
        "ebitda_mm": 5.71,
        "ebitda_margin": 0.16,
        "revenue_mm": 35.69,
        "hold_years": 3.5,
        "moic": 1.6,
        "irr": 0.1437,
        "status": "Active",
        "payer_mix": {"commercial": 0.05, "medicare": 0.02, "medicaid": 0.48, "self_pay": 0.45},
        "comm_pct": 0.05,
        "deal_narrative": (
            "Midwest non-medical home care franchise serving private-pay seniors "
            "and Medicaid HCBS waiver beneficiaries across Illinois, Wisconsin, "
            "and Minnesota. Value creation emphasizes digital caregiver scheduling, "
            "reduced overtime, and case hour growth; margin remains constrained "
            "by sector-wide caregiver wage inflation and state Medicaid rate lags."
        ),
    },
    {
        "company_name": "PinnacleInfusion Health",
        "sector": "Home Infusion",
        "buyer": "Warburg Pincus",
        "year": 2018,
        "region": "National",
        "ev_mm": 705.0,
        "ev_ebitda": 14.2,
        "ebitda_mm": 49.65,
        "ebitda_margin": 0.22,
        "revenue_mm": 225.68,
        "hold_years": 5.5,
        "moic": 3.2,
        "irr": 0.2355,
        "status": "Realized",
        "payer_mix": {"commercial": 0.60, "medicare": 0.25, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.60,
        "deal_narrative": (
            "National home and alternate-site infusion platform with 45+ ambulatory "
            "infusion suites and a URAC/ACHC-accredited specialty pharmacy. Growth "
            "driven by payer site-of-care programs steering IVIG, biologics, and "
            "anti-infective therapies from HOPD into lower-cost home and AIS "
            "settings, compounding commercial-weighted revenue at a mid-teens CAGR."
        ),
    },
    {
        "company_name": "Prairie State Home Health",
        "sector": "Home Health",
        "buyer": "Silversmith",
        "year": 2021,
        "region": "Midwest",
        "ev_mm": 140.0,
        "ev_ebitda": 12.2,
        "ebitda_mm": 11.48,
        "ebitda_margin": 0.17,
        "revenue_mm": 67.53,
        "hold_years": 3.0,
        "moic": 1.5,
        "irr": 0.1447,
        "status": "Active",
        "payer_mix": {"commercial": 0.10, "medicare": 0.66, "medicaid": 0.19, "self_pay": 0.05},
        "comm_pct": 0.10,
        "deal_narrative": (
            "Illinois and Iowa home health platform assembled through roll-up of "
            "six independent agencies. Integration playbook emphasizes Homecare "
            "Homebase standardization, OASIS coding audits, and LUPA mitigation "
            "via visit-pattern analytics; early Medicare Advantage contracting has "
            "begun to offset base-rate compression under PDGM."
        ),
    },
    {
        "company_name": "Legacy Hospice of America",
        "sector": "Hospice",
        "buyer": "Thomas H Lee",
        "year": 2016,
        "region": "National",
        "ev_mm": 540.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 43.20,
        "ebitda_margin": 0.23,
        "revenue_mm": 187.83,
        "hold_years": 6.5,
        "moic": 3.4,
        "irr": 0.2072,
        "status": "Realized",
        "payer_mix": {"commercial": 0.02, "medicare": 0.90, "medicaid": 0.06, "self_pay": 0.02},
        "comm_pct": 0.02,
        "deal_narrative": (
            "Multi-state hospice platform expanded from 25 to 70 program locations "
            "during a 6.5-year hold. Disciplined same-store census growth, GIP and "
            "respite level-of-care mix optimization, and cap-compliant ALOS "
            "management supported durable low-20s EBITDA margins and a 3.4x MOIC "
            "realized exit via secondary sale to a mega-cap healthcare services sponsor."
        ),
    },
]
