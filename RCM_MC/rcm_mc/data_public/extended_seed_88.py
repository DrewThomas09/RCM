"""Extended seed 88: Telehealth, virtual care, and digital therapeutics PE deals.

This module contains a curated set of 15 healthcare private equity deal
records focused on the telehealth / virtual care / digital therapeutics
subsector. The theme covers:

- Telehealth platforms delivering synchronous audio/video primary, urgent,
  and specialty care under CMS telehealth flexibilities extended through
  the Consolidated Appropriations Act (CAA) telehealth extension
- Virtual primary care operators executing longitudinal risk-bearing
  primary care across commercial and Medicare Advantage populations
- Digital therapeutics (DTx / PDT) companies delivering FDA-cleared
  prescription software as a medical device (SaMD) for chronic disease,
  behavioral health, and neurological indications
- Remote patient monitoring (RPM) and remote therapeutic monitoring
  (RTM) platforms billing CPT 99453-99458 and 98975-98981 for cellular
  device enablement, data transmission, and clinician management time
- Virtual behavioral health operators delivering tele-psychiatry,
  tele-therapy, and measurement-based care under CPT G-codes and
  expanded CMS behavioral health telehealth coverage

Virtual care economics are distinguished by a commercial-heavy payer
mix (younger digitally-engaged members), sensitivity to the public
health emergency (PHE) telehealth cliff expiration and the CMS
telehealth extension through December 2024 and subsequent extensions,
OIG and MedPAC scrutiny of audio-only coverage, Ryan Haight Act
controlled-substance prescribing flexibilities, PDT reimbursement
progress through the Access to Prescription Digital Therapeutics Act
and state Medicaid PDT coverage, RPM CPT 99453-99458 recurring
technical and professional fee economics, FDA SaMD clearance pathways
(510(k), De Novo), and BPCI/ACO shared-savings tie-ins. Value creation
in PE-backed virtual care platforms centers on payer contracting with
self-insured employers and health plans, provider network density in
50-state licensure, asynchronous-to-synchronous visit mix optimization,
RPM device fleet scaling, PDT payer coverage wins, and embedded care
navigation ancillaries driving per-member-per-month (PMPM) economics.

Each record captures deal economics (EV, EV/EBITDA, margins), return
profile (MOIC, IRR, hold period), payer mix, regional footprint, sponsor,
realization status, and a short deal narrative. These records are
synthesized for modeling, backtesting, and scenario analysis use cases.
"""

EXTENDED_SEED_DEALS_88 = [
    {
        "company_name": "Meridian Virtual Health",
        "sector": "Telehealth Platform",
        "buyer": "Warburg Pincus",
        "year": 2020,
        "region": "National",
        "ev_mm": 625.0,
        "ev_ebitda": 16.5,
        "ebitda_mm": 37.88,
        "ebitda_margin": 0.22,
        "revenue_mm": 172.16,
        "hold_years": 4.5,
        "moic": 2.8,
        "irr": 0.2545,
        "status": "Active",
        "payer_mix": {"commercial": 0.68, "medicare": 0.18, "medicaid": 0.09, "self_pay": 0.05},
        "comm_pct": 0.68,
        "deal_narrative": (
            "National telehealth platform delivering synchronous urgent care, "
            "primary care, and specialty consults across all 50 states under a "
            "50-state licensed provider network. Growth thesis capitalizes on "
            "the CMS telehealth extension beyond the PHE cliff under the CAA, "
            "self-insured employer direct-contracting wins, and expanded CPT "
            "telehealth code coverage driving per-visit economics, while "
            "mitigating PHE cliff exposure through multi-payer contracting."
        ),
    },
    {
        "company_name": "Beacon Primary Virtual",
        "sector": "Virtual Primary Care",
        "buyer": "General Atlantic",
        "year": 2021,
        "region": "National",
        "ev_mm": 485.0,
        "ev_ebitda": 15.0,
        "ebitda_mm": 32.33,
        "ebitda_margin": 0.20,
        "revenue_mm": 161.67,
        "hold_years": 4.0,
        "moic": 2.2,
        "irr": 0.2204,
        "status": "Active",
        "payer_mix": {"commercial": 0.65, "medicare": 0.20, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.65,
        "deal_narrative": (
            "National virtual primary care operator delivering longitudinal PMPM-"
            "based care across commercial self-insured employers and Medicare "
            "Advantage risk contracts. Value creation scales the panel size per "
            "virtualist under asynchronous messaging workflows, captures CMS "
            "telehealth extension tailwinds through 2024 and beyond, and layers "
            "embedded RPM CPT 99453-99458 billing for hypertension and diabetes "
            "cohorts to lift PMPM yield across attributed lives."
        ),
    },
    {
        "company_name": "Lumos Digital Therapeutics",
        "sector": "Digital Therapeutics",
        "buyer": "TPG Growth",
        "year": 2022,
        "region": "National",
        "ev_mm": 340.0,
        "ev_ebitda": 17.0,
        "ebitda_mm": 20.00,
        "ebitda_margin": 0.22,
        "revenue_mm": 90.91,
        "hold_years": 3.5,
        "moic": 1.7,
        "irr": 0.1608,
        "status": "Active",
        "payer_mix": {"commercial": 0.70, "medicare": 0.15, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.70,
        "deal_narrative": (
            "Digital therapeutics company with an FDA De Novo SaMD clearance for "
            "chronic insomnia CBT-I and a 510(k)-cleared pediatric ADHD PDT. "
            "Growth thesis advances PDT reimbursement through state Medicaid "
            "coverage wins, pursues Access to Prescription Digital Therapeutics "
            "Act passage for Medicare coverage, and scales commercial payer "
            "contracting with health plans and PBMs under a per-prescription "
            "net price model while expanding the SaMD-cleared indication set."
        ),
    },
    {
        "company_name": "Vantage Remote Monitoring",
        "sector": "Remote Patient Monitoring",
        "buyer": "Welsh Carson",
        "year": 2021,
        "region": "National",
        "ev_mm": 395.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 27.24,
        "ebitda_margin": 0.23,
        "revenue_mm": 118.44,
        "hold_years": 4.0,
        "moic": 2.3,
        "irr": 0.2309,
        "status": "Active",
        "payer_mix": {"commercial": 0.58, "medicare": 0.28, "medicaid": 0.09, "self_pay": 0.05},
        "comm_pct": 0.58,
        "deal_narrative": (
            "National RPM platform billing CPT 99453 device setup, 99454 device "
            "supply, and 99457-99458 clinician management time across cellular "
            "BP cuffs, glucometers, and pulse oximeters. Value creation scales "
            "device fleet size per clinician, captures the CMS RPM reimbursement "
            "expansion and RTM CPT 98975-98981 coverage, and layers chronic "
            "care management CPT 99490/99487 overlay for recurring PMPM "
            "technical and professional fee economics across Medicare cohorts."
        ),
    },
    {
        "company_name": "Haven Virtual Behavioral",
        "sector": "Virtual Behavioral Health",
        "buyer": "Oak HC/FT",
        "year": 2020,
        "region": "National",
        "ev_mm": 285.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 21.11,
        "ebitda_margin": 0.23,
        "revenue_mm": 91.79,
        "hold_years": 5.0,
        "moic": 2.6,
        "irr": 0.2114,
        "status": "Realized",
        "payer_mix": {"commercial": 0.62, "medicare": 0.18, "medicaid": 0.15, "self_pay": 0.05},
        "comm_pct": 0.62,
        "deal_narrative": (
            "National virtual behavioral health platform delivering "
            "tele-psychiatry, tele-therapy, and measurement-based care under "
            "CPT 90791/90834/90837 and G-codes for collaborative care. Exit "
            "thesis delivered on the CMS behavioral health telehealth "
            "permanent coverage, the Ryan Haight Act controlled-substance "
            "prescribing flexibility extension for Schedule II-V, commercial "
            "EAP contracting wins, and a strategic exit to a diversified "
            "behavioral health platform at a 2.6x MOIC."
        ),
    },
    {
        "company_name": "Ridgeline Telehealth Networks",
        "sector": "Telehealth Platform",
        "buyer": "Bain Capital",
        "year": 2018,
        "region": "National",
        "ev_mm": 520.0,
        "ev_ebitda": 14.8,
        "ebitda_mm": 35.14,
        "ebitda_margin": 0.21,
        "revenue_mm": 167.32,
        "hold_years": 6.0,
        "moic": 3.4,
        "irr": 0.2266,
        "status": "Realized",
        "payer_mix": {"commercial": 0.66, "medicare": 0.19, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.66,
        "deal_narrative": (
            "National telehealth platform for urgent care and primary care "
            "consults across health plan and employer channels. Long hold "
            "captured the PHE-era telehealth utilization surge, executed on "
            "the CAA CMS telehealth extension that deferred the PHE cliff, "
            "built out a 50-state licensed provider network with async visit "
            "mix optimization, and realized a strategic exit to a national "
            "payer at a 3.4x MOIC following commercial contracting scaling."
        ),
    },
    {
        "company_name": "Arcadia Primary Virtual Care",
        "sector": "Virtual Primary Care",
        "buyer": "Insight Partners",
        "year": 2019,
        "region": "National",
        "ev_mm": 410.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 29.29,
        "ebitda_margin": 0.22,
        "revenue_mm": 133.12,
        "hold_years": 5.5,
        "moic": 2.9,
        "irr": 0.2168,
        "status": "Realized",
        "payer_mix": {"commercial": 0.64, "medicare": 0.21, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.64,
        "deal_narrative": (
            "National virtual primary care platform operating a PMPM-based "
            "longitudinal care model across self-insured employers and MA risk "
            "contracts. Long hold scaled the panel economics under the CMS "
            "telehealth extension, layered CPT G-codes for care management and "
            "RPM 99453-99458 device-backed hypertension and diabetes programs, "
            "and delivered shared-savings capture across attributed MA lives "
            "supporting a strategic exit at a 2.9x realization."
        ),
    },
    {
        "company_name": "Cadence PDT Holdings",
        "sector": "Digital Therapeutics",
        "buyer": "KKR",
        "year": 2023,
        "region": "National",
        "ev_mm": 215.0,
        "ev_ebitda": 16.0,
        "ebitda_mm": 13.44,
        "ebitda_margin": 0.21,
        "revenue_mm": 64.00,
        "hold_years": 3.0,
        "moic": 1.5,
        "irr": 0.1447,
        "status": "Held",
        "payer_mix": {"commercial": 0.72, "medicare": 0.13, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.72,
        "deal_narrative": (
            "Prescription digital therapeutics holding company anchored by a "
            "510(k)-cleared SaMD for substance use disorder and a De Novo-"
            "cleared PDT for major depressive disorder adjunctive to SSRIs. "
            "Early hold pursues PDT reimbursement through CMS benefit category "
            "advocacy under the Access to Prescription Digital Therapeutics "
            "Act, scales state Medicaid PDT coverage wins, and builds "
            "commercial payer formulary placement across national health plans."
        ),
    },
    {
        "company_name": "Stellar RPM Partners",
        "sector": "Remote Patient Monitoring",
        "buyer": "Frazier",
        "year": 2019,
        "region": "Southeast",
        "ev_mm": 265.0,
        "ev_ebitda": 13.0,
        "ebitda_mm": 20.38,
        "ebitda_margin": 0.22,
        "revenue_mm": 92.64,
        "hold_years": 5.5,
        "moic": 2.7,
        "irr": 0.2010,
        "status": "Realized",
        "payer_mix": {"commercial": 0.55, "medicare": 0.30, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.55,
        "deal_narrative": (
            "Southeast RPM platform across Florida, Georgia, and the Carolinas "
            "billing CPT 99453-99458 for cellular-enabled BP, weight, and "
            "glucose monitoring in Medicare FFS and MA populations. Long hold "
            "captured CMS RPM code expansion, layered RTM CPT 98975-98981 "
            "respiratory and musculoskeletal monitoring, scaled device fleet "
            "to 120,000 units, and exited to a strategic chronic care "
            "management platform at a 2.7x MOIC."
        ),
    },
    {
        "company_name": "Northpeak Tele-Behavioral",
        "sector": "Virtual Behavioral Health",
        "buyer": "TA Associates",
        "year": 2022,
        "region": "National",
        "ev_mm": 445.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 30.69,
        "ebitda_margin": 0.21,
        "revenue_mm": 146.14,
        "hold_years": 3.5,
        "moic": 1.8,
        "irr": 0.1793,
        "status": "Active",
        "payer_mix": {"commercial": 0.60, "medicare": 0.17, "medicaid": 0.18, "self_pay": 0.05},
        "comm_pct": 0.60,
        "deal_narrative": (
            "National virtual behavioral health platform with specialized "
            "tele-psychiatry for Schedule II-V prescribing under the Ryan "
            "Haight Act flexibility extension and collaborative care billing "
            "under CPT G-codes 2214-2216. Value creation scales the network "
            "under the CMS permanent behavioral health telehealth coverage, "
            "wins Medicaid MCO contracts for SMI populations, and integrates "
            "measurement-based care with PHQ-9 and GAD-7 outcomes reporting."
        ),
    },
    {
        "company_name": "Horizon Virtual Specialty",
        "sector": "Telehealth Platform",
        "buyer": "Silver Lake",
        "year": 2022,
        "region": "National",
        "ev_mm": 195.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 15.60,
        "ebitda_margin": 0.19,
        "revenue_mm": 82.11,
        "hold_years": 3.0,
        "moic": 1.5,
        "irr": 0.1447,
        "status": "Active",
        "payer_mix": {"commercial": 0.67, "medicare": 0.18, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.67,
        "deal_narrative": (
            "National virtual specialty care platform delivering tele-"
            "dermatology, tele-cardiology, and tele-nephrology consults across "
            "commercial and MA channels. Early hold navigates the post-PHE "
            "cliff environment under the CMS telehealth extension through "
            "2024, scales asynchronous store-and-forward dermatology under "
            "CPT 99451-99452, and pursues direct-to-employer contracting to "
            "build commercial volume independent of traditional health plans."
        ),
    },
    {
        "company_name": "Crescent Virtual Primary",
        "sector": "Virtual Primary Care",
        "buyer": "Thoma Bravo",
        "year": 2023,
        "region": "West",
        "ev_mm": 155.0,
        "ev_ebitda": 11.5,
        "ebitda_mm": 13.48,
        "ebitda_margin": 0.18,
        "revenue_mm": 74.88,
        "hold_years": 2.5,
        "moic": 1.4,
        "irr": 0.1472,
        "status": "Held",
        "payer_mix": {"commercial": 0.63, "medicare": 0.22, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.63,
        "deal_narrative": (
            "West Coast virtual primary care platform serving commercial "
            "self-insured employers and MA plans across California, Nevada, "
            "and Arizona under a PMPM arrangement. Early hold executes on the "
            "CMS telehealth extension tailwind, scales async messaging visit "
            "mix to expand panel size per virtualist, and layers RPM CPT "
            "99453-99458 hypertension programs across MA attributed lives to "
            "lift PMPM yield under shared-savings contracts."
        ),
    },
    {
        "company_name": "Aurora SaMD Therapeutics",
        "sector": "Digital Therapeutics",
        "buyer": "Vista Equity",
        "year": 2021,
        "region": "National",
        "ev_mm": 295.0,
        "ev_ebitda": 18.0,
        "ebitda_mm": 16.39,
        "ebitda_margin": 0.22,
        "revenue_mm": 74.49,
        "hold_years": 4.5,
        "moic": 1.9,
        "irr": 0.1491,
        "status": "Active",
        "payer_mix": {"commercial": 0.71, "medicare": 0.14, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.71,
        "deal_narrative": (
            "National SaMD therapeutics company with a De Novo-cleared PDT for "
            "pediatric amblyopia and a 510(k)-cleared SaMD for post-stroke "
            "rehabilitation. Value creation scales PDT reimbursement through "
            "state Medicaid coverage wins, pursues Medicare benefit category "
            "advocacy under the Access to Prescription Digital Therapeutics "
            "Act, builds employer direct-contracting channels, and expands the "
            "FDA-cleared SaMD indication pipeline into adult neuro-rehab."
        ),
    },
    {
        "company_name": "Piedmont RPM Health",
        "sector": "Remote Patient Monitoring",
        "buyer": "Audax",
        "year": 2023,
        "region": "Southeast",
        "ev_mm": 115.0,
        "ev_ebitda": 11.0,
        "ebitda_mm": 10.45,
        "ebitda_margin": 0.16,
        "revenue_mm": 65.34,
        "hold_years": 2.5,
        "moic": 1.4,
        "irr": 0.1472,
        "status": "Held",
        "payer_mix": {"commercial": 0.52, "medicare": 0.32, "medicaid": 0.11, "self_pay": 0.05},
        "comm_pct": 0.52,
        "deal_narrative": (
            "Southeast RPM platform across Tennessee, Kentucky, and the "
            "Carolinas billing CPT 99453 setup, 99454 supply, and 99457-99458 "
            "clinician management time across Medicare FFS hypertension and "
            "CHF cohorts. Early hold captures ongoing CMS RPM and RTM CPT "
            "98975-98981 expansion, builds cellular device fleet density, and "
            "layers chronic care management CPT 99490 overlay for recurring "
            "PMPM professional fee economics across attributed panels."
        ),
    },
    {
        "company_name": "Summit Tele-Psychiatry",
        "sector": "Virtual Behavioral Health",
        "buyer": "Shore Capital",
        "year": 2017,
        "region": "National",
        "ev_mm": 175.0,
        "ev_ebitda": 12.0,
        "ebitda_mm": 14.58,
        "ebitda_margin": 0.19,
        "revenue_mm": 76.75,
        "hold_years": 6.5,
        "moic": 3.2,
        "irr": 0.1939,
        "status": "Realized",
        "payer_mix": {"commercial": 0.59, "medicare": 0.19, "medicaid": 0.17, "self_pay": 0.05},
        "comm_pct": 0.59,
        "deal_narrative": (
            "National tele-psychiatry platform delivering medication management "
            "and therapy across commercial EAP, Medicaid MCO, and MA contracts. "
            "Long hold rode the PHE-era behavioral health telehealth surge, "
            "captured the CMS permanent behavioral health telehealth coverage "
            "and Ryan Haight Act Schedule II-V prescribing flexibility "
            "extension, scaled a 50-state licensed prescriber network, and "
            "realized a strategic exit to a diversified behavioral platform."
        ),
    },
]
