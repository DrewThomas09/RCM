"""Extended seed 87: Cardiology, cath lab, and electrophysiology PE deals.

This module contains a curated set of 15 healthcare private equity deal
records focused on the cardiovascular care continuum. The theme covers:

- Cardiology physician practice management (PPM) platforms consolidating
  general and invasive cardiology groups with integrated ancillaries
  (echo, nuclear, stress testing, vascular ultrasound)
- Cath lab / vascular platforms delivering diagnostic catheterization,
  percutaneous coronary intervention (PCI), peripheral vascular
  intervention (PVI), and office-based lab (OBL) site-of-service
  migration from hospital-outpatient-department (HOPD) settings
- Electrophysiology (EP) practices and ablation platforms specialized
  in atrial fibrillation (AFib) ablation, device implants (PPM/ICD/CRT),
  and Watchman LAA occlusion procedures
- Interventional cardiology platforms executing TAVR (transcatheter
  aortic valve replacement), MitraClip, and structural heart programs
  under CMS National Coverage Determination (NCD) volume requirements
- Cardiac imaging operators delivering outpatient echo, nuclear
  cardiology (SPECT/PET MPI), cardiac CT angiography (CCTA), and
  cardiac MRI under shifting MPFS and HOPPS reimbursement

Cardiology economics are distinguished by a Medicare-heavy payer mix
(predominantly 65+ procedural population), exposure to the CMS
site-neutral payment policies driving the CV-PB (cardiovascular
physician-based) site-of-service shift from HOPD to OBL/ASC, TAVR and
PCI bundled-payment models (BPCI Advanced cardiac bundles), OBL global
fee economics that deliver favorable technical-component margin versus
HOPD facility rates, CCTA HOPPS repricing tailwinds, and EP ablation
procedural mix skew toward commercial AFib patients. Value creation in
PE-backed cardiology platforms centers on CV-PB site-of-service
migration, OBL/ASC de novo buildouts, TAVR heart-team program
certification, EP ablation volume scaling, bundled-payment episode
management, ancillary imaging integration, and commercial payer
contracting leverage across consolidated cardiology groups.

Each record captures deal economics (EV, EV/EBITDA, margins), return
profile (MOIC, IRR, hold period), payer mix, regional footprint, sponsor,
realization status, and a short deal narrative. These records are
synthesized for modeling, backtesting, and scenario analysis use cases.
"""

EXTENDED_SEED_DEALS_87 = [
    {
        "company_name": "Cardinal Heart Partners",
        "sector": "Cardiology Practice",
        "buyer": "Webster Equity",
        "year": 2019,
        "region": "Northeast",
        "ev_mm": 385.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 28.52,
        "ebitda_margin": 0.22,
        "revenue_mm": 129.64,
        "hold_years": 5.0,
        "moic": 2.6,
        "irr": 0.2106,
        "status": "Realized",
        "payer_mix": {"commercial": 0.30, "medicare": 0.55, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.30,
        "deal_narrative": (
            "Northeast cardiology PPM platform of 110 cardiologists across New "
            "York, New Jersey, and Connecticut with integrated echo, nuclear "
            "MPI, and vascular ultrasound ancillaries. Exit thesis delivered on "
            "the CV-PB site-of-service shift migrating diagnostic cath and PCI "
            "volume from HOPD to office-based lab, BPCI Advanced cardiac bundle "
            "participation, and commercial payer contracting leverage supporting "
            "a strategic exit to a diversified multi-specialty platform."
        ),
    },
    {
        "company_name": "Summit Cardiovascular Institute",
        "sector": "Cath Lab / Vascular",
        "buyer": "Welsh Carson",
        "year": 2020,
        "region": "Southeast",
        "ev_mm": 520.0,
        "ev_ebitda": 14.2,
        "ebitda_mm": 36.62,
        "ebitda_margin": 0.24,
        "revenue_mm": 152.58,
        "hold_years": 4.5,
        "moic": 2.4,
        "irr": 0.2116,
        "status": "Active",
        "payer_mix": {"commercial": 0.32, "medicare": 0.53, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.32,
        "deal_narrative": (
            "Southeast cath lab and vascular platform operating 14 office-based "
            "labs across Florida, Georgia, and the Carolinas delivering "
            "diagnostic catheterization, PCI, and peripheral vascular "
            "intervention. Value creation executes on the CV-PB site-of-service "
            "shift from HOPD to OBL, scales same-day-discharge PCI volume under "
            "CMS outpatient PCI coverage, and builds out de novo OBLs in "
            "CON-light markets with favorable HOPPS-to-OBL spread economics."
        ),
    },
    {
        "company_name": "Apex Electrophysiology Associates",
        "sector": "Electrophysiology",
        "buyer": "TA Associates",
        "year": 2021,
        "region": "National",
        "ev_mm": 445.0,
        "ev_ebitda": 15.0,
        "ebitda_mm": 29.67,
        "ebitda_margin": 0.25,
        "revenue_mm": 118.67,
        "hold_years": 4.0,
        "moic": 2.2,
        "irr": 0.2165,
        "status": "Active",
        "payer_mix": {"commercial": 0.34, "medicare": 0.52, "medicaid": 0.09, "self_pay": 0.05},
        "comm_pct": 0.34,
        "deal_narrative": (
            "National electrophysiology platform of 60 EPs across 9 states "
            "specializing in AFib ablation, PPM/ICD/CRT device implants, and "
            "Watchman LAA occlusion. Growth thesis scales pulsed-field ablation "
            "(PFA) adoption lifting AFib ablation throughput, executes the EP "
            "lab site-of-service shift from HOPD to ASC under the CMS ASC "
            "covered-procedures list expansion, and integrates remote device "
            "monitoring ancillaries for recurring technical-component revenue."
        ),
    },
    {
        "company_name": "Pacific Structural Heart Partners",
        "sector": "Interventional Cardiology",
        "buyer": "Warburg Pincus",
        "year": 2018,
        "region": "Pacific",
        "ev_mm": 610.0,
        "ev_ebitda": 15.5,
        "ebitda_mm": 39.35,
        "ebitda_margin": 0.26,
        "revenue_mm": 151.36,
        "hold_years": 5.5,
        "moic": 3.0,
        "irr": 0.2221,
        "status": "Realized",
        "payer_mix": {"commercial": 0.28, "medicare": 0.57, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.28,
        "deal_narrative": (
            "Pacific interventional cardiology platform with a flagship "
            "structural heart program executing TAVR, MitraClip, and Watchman "
            "across 7 heart-team-certified hubs in California, Oregon, and "
            "Washington. Long hold delivered on TAVR volume scaling within CMS "
            "NCD minimum-volume thresholds, MitraClip growth following COAPT "
            "trial label expansion, BPCI Advanced TAVR bundle participation, "
            "and commercial contracting leverage supporting a 3.0x realization."
        ),
    },
    {
        "company_name": "Heartland Cardiac Imaging",
        "sector": "Cardiac Imaging",
        "buyer": "Shore Capital",
        "year": 2022,
        "region": "Midwest",
        "ev_mm": 145.0,
        "ev_ebitda": 11.8,
        "ebitda_mm": 12.29,
        "ebitda_margin": 0.19,
        "revenue_mm": 64.69,
        "hold_years": 3.0,
        "moic": 1.6,
        "irr": 0.1696,
        "status": "Active",
        "payer_mix": {"commercial": 0.31, "medicare": 0.54, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.31,
        "deal_narrative": (
            "Midwest outpatient cardiac imaging platform delivering echo, "
            "nuclear MPI (SPECT/PET), cardiac CT angiography, and cardiac MRI "
            "across 22 sites in Illinois, Indiana, and Ohio. Value creation "
            "executes on the CCTA HOPPS repricing tailwind following the CMS "
            "APC reclassification, CV-PB site-of-service migration from "
            "hospital imaging suites to freestanding IDTFs, and PET MPI "
            "capacity buildout capturing the SPECT-to-PET modality shift."
        ),
    },
    {
        "company_name": "Bayview Cardiology Group",
        "sector": "Cardiology Practice",
        "buyer": "Audax",
        "year": 2017,
        "region": "Northeast",
        "ev_mm": 295.0,
        "ev_ebitda": 12.8,
        "ebitda_mm": 23.05,
        "ebitda_margin": 0.20,
        "revenue_mm": 115.23,
        "hold_years": 5.5,
        "moic": 2.5,
        "irr": 0.1862,
        "status": "Realized",
        "payer_mix": {"commercial": 0.29, "medicare": 0.56, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.29,
        "deal_narrative": (
            "Northeast cardiology PPM of 75 cardiologists across Massachusetts "
            "and Rhode Island with integrated ancillaries including echo, "
            "stress testing, and vascular ultrasound. Hold executed the CV-PB "
            "site-of-service shift of diagnostic cath volume to a de novo "
            "office-based lab, BPCI Advanced cardiac bundle participation for "
            "CHF and AMI episodes, and ancillary imaging integration that "
            "lifted technical-component revenue into a strategic exit."
        ),
    },
    {
        "company_name": "Cascade Cath Lab Network",
        "sector": "Cath Lab / Vascular",
        "buyer": "Frazier",
        "year": 2023,
        "region": "Pacific",
        "ev_mm": 225.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 18.0,
        "ebitda_margin": 0.21,
        "revenue_mm": 85.71,
        "hold_years": 2.5,
        "moic": 1.5,
        "irr": 0.1761,
        "status": "Held",
        "payer_mix": {"commercial": 0.33, "medicare": 0.52, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.33,
        "deal_narrative": (
            "Pacific Northwest office-based lab network of 6 OBLs across "
            "Washington and Oregon delivering diagnostic cath, PCI, and "
            "peripheral vascular intervention. Early hold is executing on the "
            "CV-PB site-of-service shift from HOPD to OBL, de novo OBL "
            "buildouts in CON-light geographies, same-day-discharge PCI "
            "program rollout, and commercial payer contracting to capture "
            "favorable global fee economics versus hospital facility rates."
        ),
    },
    {
        "company_name": "Continental EP Specialists",
        "sector": "Electrophysiology",
        "buyer": "Thomas H Lee",
        "year": 2019,
        "region": "National",
        "ev_mm": 565.0,
        "ev_ebitda": 15.8,
        "ebitda_mm": 35.76,
        "ebitda_margin": 0.27,
        "revenue_mm": 132.44,
        "hold_years": 5.5,
        "moic": 2.9,
        "irr": 0.2146,
        "status": "Realized",
        "payer_mix": {"commercial": 0.35, "medicare": 0.50, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.35,
        "deal_narrative": (
            "National electrophysiology platform of 85 EPs across 12 states "
            "focused on AFib ablation, complex ablation, and CIED implants. "
            "Long hold scaled EP ablation volumes through cryoablation and "
            "RF platform expansion, captured the CMS ASC EP procedure "
            "coverage expansion migrating select ablations from HOPD to ASC, "
            "grew Watchman LAA occlusion volumes post-CHAMPION-AF readouts, "
            "and integrated remote device monitoring for recurring revenue."
        ),
    },
    {
        "company_name": "Lone Star Interventional Cardiology",
        "sector": "Interventional Cardiology",
        "buyer": "KKR",
        "year": 2017,
        "region": "Southwest",
        "ev_mm": 480.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 33.10,
        "ebitda_margin": 0.23,
        "revenue_mm": 143.91,
        "hold_years": 6.0,
        "moic": 3.1,
        "irr": 0.2075,
        "status": "Realized",
        "payer_mix": {"commercial": 0.27, "medicare": 0.58, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.27,
        "deal_narrative": (
            "Southwest interventional cardiology platform across Texas, "
            "Oklahoma, and Arkansas with 5 TAVR-certified heart-team hubs, "
            "integrated structural heart program, and complex PCI lines of "
            "service. Long hold delivered on TAVR volume growth within CMS "
            "NCD volume thresholds, MitraClip expansion under COAPT, BPCI "
            "Advanced TAVR and PCI bundle participation, and de novo OBL "
            "buildouts for diagnostic cath site-of-service economics."
        ),
    },
    {
        "company_name": "MidAtlantic Cardiology Holdings",
        "sector": "Cardiology Practice",
        "buyer": "New Mountain",
        "year": 2020,
        "region": "Mid-Atlantic",
        "ev_mm": 410.0,
        "ev_ebitda": 13.8,
        "ebitda_mm": 29.71,
        "ebitda_margin": 0.23,
        "revenue_mm": 129.17,
        "hold_years": 4.5,
        "moic": 2.1,
        "irr": 0.1832,
        "status": "Active",
        "payer_mix": {"commercial": 0.30, "medicare": 0.55, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.30,
        "deal_narrative": (
            "Mid-Atlantic cardiology PPM of 130 cardiologists and advanced "
            "practitioners across Virginia, Maryland, and DC with integrated "
            "imaging, EP, and interventional lines of service. Growth thesis "
            "executes the CV-PB site-of-service shift with two de novo OBLs, "
            "BPCI Advanced cardiac bundle participation for AMI and CHF "
            "episodes, CCTA capacity expansion under HOPPS repricing, and "
            "commercial payer contracting leverage across consolidated groups."
        ),
    },
    {
        "company_name": "Northstar Cardiac Imaging Partners",
        "sector": "Cardiac Imaging",
        "buyer": "Harren",
        "year": 2022,
        "region": "Midwest",
        "ev_mm": 88.0,
        "ev_ebitda": 10.5,
        "ebitda_mm": 8.38,
        "ebitda_margin": 0.17,
        "revenue_mm": 49.30,
        "hold_years": 3.0,
        "moic": 1.5,
        "irr": 0.1447,
        "status": "Active",
        "payer_mix": {"commercial": 0.28, "medicare": 0.58, "medicaid": 0.09, "self_pay": 0.05},
        "comm_pct": 0.28,
        "deal_narrative": (
            "Upper-Midwest cardiac imaging platform operating 12 outpatient "
            "sites across Minnesota, Wisconsin, and the Dakotas delivering "
            "echo, nuclear MPI, and CCTA. Value creation captures the CCTA "
            "HOPPS repricing tailwind following APC reclassification, migrates "
            "hospital-based imaging volume to freestanding IDTF site-of-service "
            "for favorable technical-component economics, and builds out PET "
            "MPI capacity under the SPECT-to-PET modality shift."
        ),
    },
    {
        "company_name": "Crescent Heart & Vascular",
        "sector": "Cath Lab / Vascular",
        "buyer": "Silversmith",
        "year": 2021,
        "region": "Southeast",
        "ev_mm": 195.0,
        "ev_ebitda": 12.2,
        "ebitda_mm": 15.98,
        "ebitda_margin": 0.20,
        "revenue_mm": 79.92,
        "hold_years": 3.5,
        "moic": 1.7,
        "irr": 0.1601,
        "status": "Active",
        "payer_mix": {"commercial": 0.31, "medicare": 0.54, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.31,
        "deal_narrative": (
            "Gulf Coast office-based lab operator across Louisiana, "
            "Mississippi, and Alabama delivering diagnostic cath, peripheral "
            "vascular intervention, and venous procedures. Value creation "
            "executes the CV-PB site-of-service shift from HOPD to OBL, "
            "same-day-discharge PCI program rollout under CMS outpatient PCI "
            "coverage, de novo OBL buildouts in CON-light geographies, and "
            "CLI (critical limb ischemia) PVI volume growth in diabetes-dense "
            "markets with favorable OBL global fee economics."
        ),
    },
    {
        "company_name": "Sentinel EP Holdings",
        "sector": "Electrophysiology",
        "buyer": "Cressey",
        "year": 2018,
        "region": "Midwest",
        "ev_mm": 340.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 24.29,
        "ebitda_margin": 0.23,
        "revenue_mm": 105.59,
        "hold_years": 5.0,
        "moic": 2.5,
        "irr": 0.2011,
        "status": "Realized",
        "payer_mix": {"commercial": 0.33, "medicare": 0.52, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.33,
        "deal_narrative": (
            "Midwest electrophysiology platform of 45 EPs across Ohio, "
            "Michigan, and Indiana specializing in AFib ablation, CIED "
            "implants, and Watchman LAA occlusion. Exit thesis delivered on "
            "EP ablation volume scaling through cryo and RF, CMS ASC EP "
            "covered-procedure list expansion migrating select ablations to "
            "ASC, remote device monitoring ancillary integration for "
            "recurring revenue, and a strategic exit to a diversified "
            "multi-state cardiovascular platform at a 2.5x MOIC."
        ),
    },
    {
        "company_name": "Evergreen Structural Heart Network",
        "sector": "Interventional Cardiology",
        "buyer": "Blackstone",
        "year": 2016,
        "region": "National",
        "ev_mm": 825.0,
        "ev_ebitda": 17.5,
        "ebitda_mm": 47.14,
        "ebitda_margin": 0.28,
        "revenue_mm": 168.37,
        "hold_years": 6.5,
        "moic": 3.6,
        "irr": 0.2163,
        "status": "Realized",
        "payer_mix": {"commercial": 0.27, "medicare": 0.58, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.27,
        "deal_narrative": (
            "National interventional cardiology platform anchored by 11 "
            "TAVR-certified heart-team hubs and 24 PCI-capable cath labs "
            "across 15 states. Long-hold value creation captured the TAVR "
            "low-risk label expansion post-PARTNER 3 and Evolut Low Risk, "
            "MitraClip growth under COAPT, Watchman LAA occlusion adoption, "
            "BPCI Advanced TAVR and AMI bundle optimization, and CV-PB "
            "site-of-service migration of diagnostic cath volume to OBL "
            "supporting a 3.6x MOIC strategic realization."
        ),
    },
    {
        "company_name": "Horizon Cardiology Associates",
        "sector": "Cardiology Practice",
        "buyer": "Nautic",
        "year": 2023,
        "region": "West",
        "ev_mm": 165.0,
        "ev_ebitda": 11.5,
        "ebitda_mm": 14.35,
        "ebitda_margin": 0.18,
        "revenue_mm": 79.71,
        "hold_years": 2.5,
        "moic": 1.4,
        "irr": 0.1472,
        "status": "Held",
        "payer_mix": {"commercial": 0.32, "medicare": 0.53, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.32,
        "deal_narrative": (
            "Mountain West cardiology PPM of 50 cardiologists across Colorado, "
            "Utah, and Idaho with integrated echo, stress, and vascular "
            "ultrasound ancillaries. Early hold executes the CV-PB site-of-"
            "service shift through a de novo office-based lab for diagnostic "
            "cath and peripheral vascular intervention, BPCI Advanced cardiac "
            "bundle enrollment for CHF and AMI episodes, CCTA capacity "
            "buildout, and consolidated commercial payer contracting leverage."
        ),
    },
]
