"""
Extended seed dataset 43 — 15 PE healthcare deals.
Sectors: neonatal transport/NICU, pediatric rehab, adult day health,
senior living/CCRC, home infusion therapy, outpatient cardiac rehab,
radiation therapy management, dialysis alternative/ESRD non-dialysis,
urology/men's health, female pelvic medicine/urogynecology,
integrative oncology, oral-maxillofacial surgery, podiatry/foot & ankle,
hand surgery/peripheral nerve, concussion/TBI rehabilitation.
"""

EXTENDED_SEED_DEALS_43 = [
    {
        "source_id": "ext43_001",
        "source": "seed",
        "company_name": "NovaStar Neonatal Transport Systems",
        "sector": "Neonatal Transport / NICU",
        "year": 2016,
        "buyer": "Varsity Healthcare Partners",
        "ev_mm": 320.0,
        "ebitda_at_entry_mm": 32.0,        # EV/EBITDA = 10.0x
        "moic": 3.4,
        "irr": 0.29,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.42,
            "medicare": 0.18,
            "medicaid": 0.35,
            "other": 0.05,
        },
        "notes": (
            "Neonatal ground and air transport generates highly variable claim complexity "
            "due to per-mile billing, multiple simultaneous CPT codes, and frequent "
            "medicaid retroactive eligibility changes for premature newborns."
        ),
    },
    {
        "source_id": "ext43_002",
        "source": "seed",
        "company_name": "BrightPath Pediatric Rehab Group",
        "sector": "Pediatric Rehabilitation",
        "year": 2018,
        "buyer": "Revelstoke Capital Partners",
        "ev_mm": 210.0,
        "ebitda_at_entry_mm": 21.0,        # EV/EBITDA = 10.0x
        "moic": 3.1,
        "irr": 0.26,
        "hold_years": 5.0,
        "payer_mix": {
            "commercial": 0.38,
            "medicare": 0.04,
            "medicaid": 0.52,
            "other": 0.06,
        },
        "notes": (
            "Pediatric therapy billing spans PT, OT, and SLP codes with school-based "
            "Medicaid carve-outs requiring separate credentialing and encounter tracking; "
            "prior-authorization denial rates are elevated versus adult rehab settings."
        ),
    },
    {
        "source_id": "ext43_003",
        "source": "seed",
        "company_name": "DayBridge Adult Health Services",
        "sector": "Adult Day Health Services",
        "year": 2015,
        "buyer": "Sterling Partners",
        "ev_mm": 145.0,
        "ebitda_at_entry_mm": 16.1,        # EV/EBITDA ≈ 9.0x
        "moic": 2.8,
        "irr": 0.24,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.08,
            "medicare": 0.22,
            "medicaid": 0.63,
            "other": 0.07,
        },
        "notes": (
            "Adult day health centers face complex Medicaid managed-care encounter "
            "reconciliation across multiple state waiver programs, with per-diem rates "
            "that vary significantly by county and level-of-care classification."
        ),
    },
    {
        "source_id": "ext43_004",
        "source": "seed",
        "company_name": "HarborView Senior Living & Care Communities",
        "sector": "Senior Living / CCRC with Skilled Nursing",
        "year": 2017,
        "buyer": "Warburg Pincus",
        "ev_mm": 1250.0,
        "ebitda_at_entry_mm": 104.2,       # EV/EBITDA ≈ 12.0x
        "moic": 3.2,
        "irr": 0.27,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.30,
            "medicare": 0.38,
            "medicaid": 0.24,
            "other": 0.08,
        },
        "notes": (
            "CCRCs with embedded skilled nursing face simultaneous RCM workflows for "
            "private-pay continuing care contracts, Medicare Part A SNF claims, and "
            "Medicaid nursing facility rates, each governed by distinct documentation "
            "and level-of-care assessment requirements."
        ),
    },
    {
        "source_id": "ext43_005",
        "source": "seed",
        "company_name": "InfusCare Home Therapy Partners",
        "sector": "Home Infusion Therapy",
        "year": 2019,
        "buyer": "New Mountain Capital",
        "ev_mm": 580.0,
        "ebitda_at_entry_mm": 52.7,        # EV/EBITDA ≈ 11.0x
        "moic": 3.6,
        "irr": 0.31,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.55,
            "medicare": 0.28,
            "medicaid": 0.12,
            "other": 0.05,
        },
        "notes": (
            "Home infusion billing requires coordination of pharmacy drug claims under "
            "Part D and professional/supply claims under Part B, with payer-specific "
            "prior-auth and delivery-confirmation documentation driving high denial rates "
            "for specialty biologics."
        ),
    },
    {
        "source_id": "ext43_006",
        "source": "seed",
        "company_name": "CardioStep Outpatient Cardiac Rehab Centers",
        "sector": "Outpatient Cardiac Rehabilitation",
        "year": 2014,
        "buyer": "Riverside Company",
        "ev_mm": 165.0,
        "ebitda_at_entry_mm": 18.3,        # EV/EBITDA ≈ 9.0x
        "moic": 2.9,
        "irr": 0.25,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.34,
            "medicare": 0.50,
            "medicaid": 0.10,
            "other": 0.06,
        },
        "notes": (
            "Outpatient cardiac rehab is reimbursed under a session-based Medicare "
            "benefit with strict 36-session lifetime caps and mandatory physician-referral "
            "documentation; any eligibility gap in the qualifying cardiac event triggers "
            "full claim recoupment."
        ),
    },
    {
        "source_id": "ext43_007",
        "source": "seed",
        "company_name": "PrecisionBeam Radiation Therapy Management",
        "sector": "Radiation Therapy Management",
        "year": 2020,
        "buyer": "Ridgemont Equity Partners",
        "ev_mm": 490.0,
        "ebitda_at_entry_mm": 44.5,        # EV/EBITDA ≈ 11.0x
        "moic": 3.3,
        "irr": 0.30,
        "hold_years": 3.5,
        "payer_mix": {
            "commercial": 0.46,
            "medicare": 0.40,
            "medicaid": 0.09,
            "other": 0.05,
        },
        "notes": (
            "Radiation therapy management companies must navigate the technical/professional "
            "component split billing under HOPD and freestanding rules, with IMRT and "
            "SBRT coding subject to ongoing CMS revaluation that creates revenue-per-fraction "
            "volatility across contract years."
        ),
    },
    {
        "source_id": "ext43_008",
        "source": "seed",
        "company_name": "RenalChoice ESRD Alternative Care Network",
        "sector": "Dialysis Alternative / ESRD Non-Dialysis",
        "year": 2021,
        "buyer": "Welsh Carson Anderson & Stowe",
        "ev_mm": 420.0,
        "ebitda_at_entry_mm": 42.0,        # EV/EBITDA = 10.0x
        "moic": 3.0,
        "irr": 0.28,
        "hold_years": 3.0,
        "payer_mix": {
            "commercial": 0.25,
            "medicare": 0.58,
            "medicaid": 0.12,
            "other": 0.05,
        },
        "notes": (
            "ESRD non-dialysis care models participate in the Kidney Care Choices "
            "demonstration, requiring sophisticated attribution and reconciliation logic "
            "under total cost-of-care benchmarks that interact with Part D and transplant "
            "episode-of-care payments."
        ),
    },
    {
        "source_id": "ext43_009",
        "source": "seed",
        "company_name": "UroCentric Men's Health Partners",
        "sector": "Urology / Men's Health Practices",
        "year": 2018,
        "buyer": "Audax Private Equity",
        "ev_mm": 390.0,
        "ebitda_at_entry_mm": 39.0,        # EV/EBITDA = 10.0x
        "moic": 3.5,
        "irr": 0.30,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.52,
            "medicare": 0.36,
            "medicaid": 0.07,
            "other": 0.05,
        },
        "notes": (
            "Urology practices bill an unusually broad mix of E&M, surgical, diagnostic "
            "imaging, and in-office pathology codes, with in-office ancillary service "
            "designation critical to revenue integrity but subject to ongoing payor "
            "scrutiny and self-referral compliance risk."
        ),
    },
    {
        "source_id": "ext43_010",
        "source": "seed",
        "company_name": "PelvicAxis Female Pelvic Medicine Group",
        "sector": "Female Pelvic Medicine / Urogynecology",
        "year": 2019,
        "buyer": "Shore Capital Partners",
        "ev_mm": 260.0,
        "ebitda_at_entry_mm": 26.0,        # EV/EBITDA = 10.0x
        "moic": 3.2,
        "irr": 0.27,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.58,
            "medicare": 0.28,
            "medicaid": 0.09,
            "other": 0.05,
        },
        "notes": (
            "Female pelvic medicine billing spans OBGYN and urology specialty codes, "
            "with mesh-revision and neuromodulation procedures frequently subject to "
            "commercial prior-auth requirements and ICD-10 specificity standards that "
            "differ materially between surgical and conservative-management encounters."
        ),
    },
    {
        "source_id": "ext43_011",
        "source": "seed",
        "company_name": "WholeCare Integrative Oncology Centers",
        "sector": "Integrative Oncology / Cancer Support",
        "year": 2017,
        "buyer": "Frazier Healthcare Partners",
        "ev_mm": 185.0,
        "ebitda_at_entry_mm": 20.6,        # EV/EBITDA ≈ 9.0x
        "moic": 2.7,
        "irr": 0.23,
        "hold_years": 5.0,
        "payer_mix": {
            "commercial": 0.62,
            "medicare": 0.22,
            "medicaid": 0.06,
            "other": 0.10,
        },
        "notes": (
            "Integrative oncology programs mix covered services such as acupuncture "
            "and palliative counseling with non-covered wellness offerings, requiring "
            "careful unbundling and patient-responsibility documentation to avoid "
            "inadvertent balance-billing violations under commercial contracts."
        ),
    },
    {
        "source_id": "ext43_012",
        "source": "seed",
        "company_name": "MaxiloSurgical Oral & Facial Partners",
        "sector": "Oral-Maxillofacial Surgery Practices",
        "year": 2016,
        "buyer": "Harvest Partners",
        "ev_mm": 310.0,
        "ebitda_at_entry_mm": 34.4,        # EV/EBITDA ≈ 9.0x
        "moic": 3.4,
        "irr": 0.29,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.60,
            "medicare": 0.14,
            "medicaid": 0.18,
            "other": 0.08,
        },
        "notes": (
            "OMS practices must coordinate between medical and dental insurance for "
            "procedures such as jaw reconstruction and implant-related bone grafting, "
            "with dual-benefit coordination rules frequently leading to underpayment "
            "when medical necessity documentation is not cross-submitted to both payers."
        ),
    },
    {
        "source_id": "ext43_013",
        "source": "seed",
        "company_name": "StepForward Podiatry & Foot Surgery Group",
        "sector": "Podiatry / Foot and Ankle",
        "year": 2013,
        "buyer": "Blue Sea Capital",
        "ev_mm": 130.0,
        "ebitda_at_entry_mm": 14.4,        # EV/EBITDA ≈ 9.0x
        "moic": 4.0,
        "irr": 0.35,
        "hold_years": 5.5,
        "payer_mix": {
            "commercial": 0.45,
            "medicare": 0.38,
            "medicaid": 0.12,
            "other": 0.05,
        },
        "notes": (
            "Podiatry RCM is complicated by Medicare's routine-foot-care exclusions, "
            "which require documented systemic conditions such as peripheral neuropathy "
            "or vascular disease on every claim to avoid automatic denial of nail and "
            "callus debridement services."
        ),
    },
    {
        "source_id": "ext43_014",
        "source": "seed",
        "company_name": "NervePoint Hand & Peripheral Nerve Specialists",
        "sector": "Hand Surgery / Peripheral Nerve",
        "year": 2020,
        "buyer": "Gridiron Capital",
        "ev_mm": 280.0,
        "ebitda_at_entry_mm": 28.0,        # EV/EBITDA = 10.0x
        "moic": 3.3,
        "irr": 0.31,
        "hold_years": 3.5,
        "payer_mix": {
            "commercial": 0.64,
            "medicare": 0.26,
            "medicaid": 0.06,
            "other": 0.04,
        },
        "notes": (
            "Hand and peripheral nerve surgery billing involves complex modifier usage "
            "for bilateral procedures and multiple-surgery reduction rules, with nerve "
            "decompression CPT codes subject to high commercial pre-certification denial "
            "rates absent standardized functional-impairment scoring documentation."
        ),
    },
    {
        "source_id": "ext43_015",
        "source": "seed",
        "company_name": "ClearHead Concussion & TBI Rehab Centers",
        "sector": "Concussion / TBI Rehabilitation",
        "year": 2022,
        "buyer": "Linden Capital Partners",
        "ev_mm": 230.0,
        "ebitda_at_entry_mm": 23.0,        # EV/EBITDA = 10.0x
        "moic": 2.6,
        "irr": 0.24,
        "hold_years": 3.0,
        "payer_mix": {
            "commercial": 0.55,
            "medicare": 0.15,
            "medicaid": 0.20,
            "other": 0.10,
        },
        "notes": (
            "Concussion and TBI rehabilitation programs bill across neuropsychology, "
            "vestibular PT, and cognitive remediation codes that lack uniform payer "
            "coverage policies, resulting in high rates of medical-necessity appeals "
            "and frequent coordination-of-benefits disputes between workers' comp, "
            "auto liability, and health insurance payors."
        ),
    },
]
