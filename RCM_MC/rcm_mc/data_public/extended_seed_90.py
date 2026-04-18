"""Extended seed 90: Pharma services, CRO, CDMO, and CMO PE deals.

This module contains a curated set of 15 healthcare private equity deal
records focused on the pharma services / contract research organization
(CRO) / contract development and manufacturing organization (CDMO) /
contract manufacturing organization (CMO) subsector. The theme covers:

- Clinical CROs delivering Phase I-IV trial execution, site management
  organizations (SMOs), decentralized clinical trial (DCT) platforms,
  biostatistics, medical writing, and regulatory submission services
  under ICH-GCP, FDA 21 CFR Part 11, and EMA CTR compliance
- CDMO platforms delivering small-molecule API, oral solid dose (OSD),
  sterile fill-finish, lyophilization, highly potent API (HPAPI),
  and biologics drug substance / drug product manufacturing under
  cGMP with FDA Form 483 and EIR inspection exposure
- CMO packaging operators delivering primary (bottle, blister, vial)
  and secondary (carton, serialization, DSCSA-compliant track-and-
  trace) packaging, cold-chain 2-8C and -20C handling, and clinical
  trial supply labeling under GxP
- Biologics / biosimilar capacity platforms delivering mammalian cell
  culture (CHO, NS0) drug substance, microbial fermentation, single-
  use bioreactor capacity, and biosimilar tech-transfer manufacturing
- Specialty pharma services including bioanalytical labs, central
  labs, IRT/RTSM, clinical trial logistics with cold-chain couriers,
  and pharmacovigilance / safety case processing

Pharma services economics are distinguished by a B2B commercial-heavy
client mix (biopharma sponsors fund 85-92% of revenue with de minimis
government payer exposure), multi-year master service agreement (MSA)
backlog providing revenue visibility, project-based milestone and
pass-through billing structures in CRO, fixed + variable manufacturing
economics in CDMO/CMO with utilization leverage on sterile fill-finish
suites, regulatory capital-intensive FDA Form 483 remediation and
pre-approval inspection (PAI) readiness, biologics drug-substance
capacity scarcity driving premium pricing on 2,000L and 5,000L CHO
bioreactor slots, sterile fill-finish capacity bottlenecks from the
COVID-era vaccine build-out, HPAPI containment (OEB 4/5) premium
pricing, GLP-1 demand surge (semaglutide, tirzepatide) driving sterile
injectable capacity scarcity, and biosimilar tech-transfer demand as
Humira, Stelara, and Eylea biosimilars launch. Value creation in PE-
backed pharma services platforms centers on capacity expansion capex
(new sterile suites, additional bioreactor trains), DCT and hybrid
trial capability build-out, site consolidation of sub-scale legacy
facilities, FDA Form 483 remediation with warning-letter clearance,
tuck-in acquisitions adding modalities (peptides, mRNA, ADC, viral
vector), and geographic reach into Europe and APAC under MRA / MHRA
/ PMDA inspection coverage.

Each record captures deal economics (EV, EV/EBITDA, margins), return
profile (MOIC, IRR, hold period), client mix, regional footprint,
sponsor, realization status, and a short deal narrative. These
records are synthesized for modeling, backtesting, and scenario
analysis use cases.
"""

EXTENDED_SEED_DEALS_90 = [
    {
        "company_name": "Addenbrook Clinical Research",
        "sector": "CRO - Clinical Research",
        "buyer": "Genstar Capital",
        "year": 2019,
        "region": "National",
        "ev_mm": 615.0,
        "ev_ebitda": 15.0,
        "ebitda_mm": 41.00,
        "ebitda_margin": 0.20,
        "revenue_mm": 205.00,
        "hold_years": 5.0,
        "moic": 2.8,
        "irr": 0.2286,
        "status": "Realized",
        "payer_mix": {"commercial": 0.88, "medicare": 0.04, "medicaid": 0.02, "self_pay": 0.06},
        "comm_pct": 0.88,
        "deal_narrative": (
            "Mid-market clinical CRO delivering Phase II-III trial execution "
            "for biopharma sponsors across oncology, CNS, and metabolic "
            "indications. Long hold built out a decentralized clinical trial "
            "(DCT) platform with eCOA / ePRO and remote patient monitoring, "
            "scaled the SMO site network from 120 to 310 investigator sites, "
            "remediated two FDA Form 483 observations on monitoring oversight "
            "with full warning-letter clearance, and exited to a strategic "
            "top-10 CRO consolidator at a 2.8x MOIC on multi-year MSA backlog."
        ),
    },
    {
        "company_name": "Northbrook Sterile Manufacturing",
        "sector": "CDMO - Manufacturing",
        "buyer": "Carlyle Group",
        "year": 2018,
        "region": "Midwest",
        "ev_mm": 785.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 54.14,
        "ebitda_margin": 0.24,
        "revenue_mm": 225.57,
        "hold_years": 6.0,
        "moic": 3.3,
        "irr": 0.2221,
        "status": "Realized",
        "payer_mix": {"commercial": 0.90, "medicare": 0.03, "medicaid": 0.02, "self_pay": 0.05},
        "comm_pct": 0.90,
        "deal_narrative": (
            "Midwest CDMO platform delivering sterile fill-finish for vials, "
            "pre-filled syringes, and cartridges across biologics and small-"
            "molecule injectables. Long hold added two isolator-based sterile "
            "suites lifting annual fill capacity from 45M to 120M units, "
            "captured GLP-1 demand surge from semaglutide and tirzepatide "
            "sponsors at premium pricing, remediated an FDA Form 483 on "
            "environmental monitoring with successful PAI clearance, and "
            "exited to a strategic global CDMO acquirer at a 3.3x MOIC."
        ),
    },
    {
        "company_name": "Cresthaven Packaging Solutions",
        "sector": "CMO - Packaging",
        "buyer": "Arsenal Capital Partners",
        "year": 2020,
        "region": "Northeast",
        "ev_mm": 215.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 17.20,
        "ebitda_margin": 0.19,
        "revenue_mm": 90.53,
        "hold_years": 4.5,
        "moic": 2.3,
        "irr": 0.2013,
        "status": "Active",
        "payer_mix": {"commercial": 0.86, "medicare": 0.05, "medicaid": 0.03, "self_pay": 0.06},
        "comm_pct": 0.86,
        "deal_narrative": (
            "Northeast CMO packaging operator delivering primary bottle and "
            "blister packaging for oral solid dose and secondary carton / "
            "serialization for DSCSA-compliant track-and-trace across "
            "commercial and clinical trial supply. Value creation adds a "
            "cold-chain 2-8C handling suite for biologics, consolidates "
            "three sub-scale legacy facilities into a single GMP campus, "
            "and layers DSCSA aggregation and EPCIS event capture services "
            "as wholesaler and dispenser compliance deadlines accelerate."
        ),
    },
    {
        "company_name": "Harrowgate Biologics CDMO",
        "sector": "CDMO - Manufacturing",
        "buyer": "EQT",
        "year": 2021,
        "region": "West",
        "ev_mm": 825.0,
        "ev_ebitda": 17.0,
        "ebitda_mm": 48.53,
        "ebitda_margin": 0.26,
        "revenue_mm": 186.65,
        "hold_years": 4.0,
        "moic": 2.1,
        "irr": 0.2035,
        "status": "Active",
        "payer_mix": {"commercial": 0.91, "medicare": 0.02, "medicaid": 0.02, "self_pay": 0.05},
        "comm_pct": 0.91,
        "deal_narrative": (
            "West Coast biologics CDMO delivering mammalian cell culture "
            "(CHO, NS0) drug substance manufacturing for monoclonal "
            "antibody and Fc-fusion programs. Value creation expands "
            "biologics capacity from two 2,000L single-use bioreactor "
            "trains to six trains plus one 5,000L stainless steel reactor, "
            "captures biosimilar tech-transfer demand as Humira, Stelara, "
            "and Eylea biosimilars scale, and builds a late-phase / "
            "commercial drug product fill-finish capability for end-to-end "
            "biologics service integration under MRA-covered GMP."
        ),
    },
    {
        "company_name": "Brayton Pharma Services",
        "sector": "Pharma Services",
        "buyer": "GTCR",
        "year": 2017,
        "region": "National",
        "ev_mm": 485.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 35.93,
        "ebitda_margin": 0.22,
        "revenue_mm": 163.30,
        "hold_years": 6.5,
        "moic": 3.4,
        "irr": 0.2019,
        "status": "Realized",
        "payer_mix": {"commercial": 0.89, "medicare": 0.03, "medicaid": 0.02, "self_pay": 0.06},
        "comm_pct": 0.89,
        "deal_narrative": (
            "National pharma services platform delivering bioanalytical "
            "labs, central lab services, and pharmacovigilance / safety "
            "case processing for biopharma sponsors. Long hold scaled "
            "the bioanalytical LC-MS/MS assay portfolio, added IRT/RTSM "
            "and clinical trial supply management capabilities via three "
            "tuck-ins, expanded into Europe under MHRA and EMA inspection "
            "coverage, and exited to a strategic global CRO consolidator "
            "at a 3.4x MOIC on multi-year MSA backlog from top-20 pharma."
        ),
    },
    {
        "company_name": "Silverpoint Clinical Logistics",
        "sector": "Clinical Trial Logistics",
        "buyer": "Partners Group",
        "year": 2022,
        "region": "National",
        "ev_mm": 325.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 23.21,
        "ebitda_margin": 0.21,
        "revenue_mm": 110.52,
        "hold_years": 3.0,
        "moic": 1.6,
        "irr": 0.1696,
        "status": "Active",
        "payer_mix": {"commercial": 0.87, "medicare": 0.04, "medicaid": 0.03, "self_pay": 0.06},
        "comm_pct": 0.87,
        "deal_narrative": (
            "National clinical trial logistics platform delivering cold-"
            "chain 2-8C, -20C, and -80C courier services, biospecimen "
            "transport, and investigational medicinal product (IMP) "
            "depot distribution for Phase I-III trials. Value creation "
            "expands the validated cold-chain courier lane network, "
            "deploys IoT temperature-monitoring across shipments with "
            "GDP-compliant chain-of-custody documentation, and captures "
            "cell and gene therapy cryogenic LN2 dry-vapor shipping "
            "demand as autologous CAR-T and allogeneic programs scale."
        ),
    },
    {
        "company_name": "Eastbourne Oral Solid Dose",
        "sector": "CDMO - Manufacturing",
        "buyer": "Advent International",
        "year": 2016,
        "region": "Southeast",
        "ev_mm": 395.0,
        "ev_ebitda": 11.5,
        "ebitda_mm": 34.35,
        "ebitda_margin": 0.21,
        "revenue_mm": 163.57,
        "hold_years": 6.0,
        "moic": 3.1,
        "irr": 0.2068,
        "status": "Realized",
        "payer_mix": {"commercial": 0.85, "medicare": 0.05, "medicaid": 0.04, "self_pay": 0.06},
        "comm_pct": 0.85,
        "deal_narrative": (
            "Southeast CDMO platform delivering oral solid dose (OSD) "
            "tablet and capsule manufacturing plus high-shear wet "
            "granulation and direct compression for branded generic "
            "and specialty pharma clients. Long hold consolidated four "
            "sub-scale legacy OSD facilities into two GMP campuses, "
            "added a highly potent API (HPAPI) OEB 4/5 containment "
            "suite capturing oncology and hormone-therapy premium "
            "pricing, remediated a legacy FDA Form 483 observation on "
            "cleaning validation, and exited to a strategic CDMO at "
            "3.1x MOIC following site consolidation-driven margin lift."
        ),
    },
    {
        "company_name": "Weatherford DPT Services",
        "sector": "Pharma Services",
        "buyer": "Ampersand Capital",
        "year": 2019,
        "region": "Southwest",
        "ev_mm": 175.0,
        "ev_ebitda": 13.0,
        "ebitda_mm": 13.46,
        "ebitda_margin": 0.18,
        "revenue_mm": 74.78,
        "hold_years": 5.0,
        "moic": 2.4,
        "irr": 0.1910,
        "status": "Realized",
        "payer_mix": {"commercial": 0.84, "medicare": 0.05, "medicaid": 0.04, "self_pay": 0.07},
        "comm_pct": 0.84,
        "deal_narrative": (
            "Southwest drug product technology (DPT) services platform "
            "delivering formulation development, spray-dried dispersion, "
            "hot-melt extrusion, and bioavailability enhancement for "
            "poorly soluble small-molecule APIs. Long hold scaled the "
            "formulation development FTE bench, added a GMP Phase I/II "
            "clinical manufacturing suite for early-phase fill-finish, "
            "captured a wave of NCE sponsor programs requiring solubility "
            "enhancement, and exited to a strategic CDMO at a 2.4x MOIC."
        ),
    },
    {
        "company_name": "Pinehurst Biosimilar Manufacturing",
        "sector": "CDMO - Manufacturing",
        "buyer": "Blackstone",
        "year": 2020,
        "region": "National",
        "ev_mm": 695.0,
        "ev_ebitda": 16.5,
        "ebitda_mm": 42.12,
        "ebitda_margin": 0.25,
        "revenue_mm": 168.48,
        "hold_years": 4.5,
        "moic": 2.2,
        "irr": 0.1924,
        "status": "Active",
        "payer_mix": {"commercial": 0.92, "medicare": 0.02, "medicaid": 0.02, "self_pay": 0.04},
        "comm_pct": 0.92,
        "deal_narrative": (
            "National biosimilar manufacturing CDMO delivering mammalian "
            "cell culture drug substance and sterile fill-finish drug "
            "product for biosimilar sponsors. Value creation builds out "
            "biologics capacity with two additional 2,000L single-use "
            "bioreactor trains, executes tech-transfer for Humira "
            "(adalimumab), Stelara (ustekinumab), and Eylea (aflibercept) "
            "biosimilar programs, adds upstream process development for "
            "biosimilar analytical comparability packages, and positions "
            "for exit to a strategic global CDMO as biosimilar share "
            "accelerates in commercial and Medicare Part B channels."
        ),
    },
    {
        "company_name": "Trenton Fill-Finish Partners",
        "sector": "CDMO - Manufacturing",
        "buyer": "Cinven",
        "year": 2021,
        "region": "Mid-Atlantic",
        "ev_mm": 545.0,
        "ev_ebitda": 15.5,
        "ebitda_mm": 35.16,
        "ebitda_margin": 0.23,
        "revenue_mm": 152.87,
        "hold_years": 3.5,
        "moic": 1.8,
        "irr": 0.1828,
        "status": "Active",
        "payer_mix": {"commercial": 0.90, "medicare": 0.03, "medicaid": 0.02, "self_pay": 0.05},
        "comm_pct": 0.90,
        "deal_narrative": (
            "Mid-Atlantic sterile fill-finish CDMO delivering vial and "
            "pre-filled syringe filling with lyophilization for biologics "
            "and sterile injectables. Value creation adds an automated "
            "isolator-based fill line lifting pre-filled syringe capacity "
            "60%, captures sterile capacity scarcity from the COVID "
            "vaccine build-out overhang and GLP-1 demand surge, and "
            "executes FDA PAI readiness on two commercial-stage sponsor "
            "programs. Active hold positioned for a high-single-digit "
            "EBITDA multiple exit given biologics fill-finish scarcity."
        ),
    },
    {
        "company_name": "Oakridge Central Labs",
        "sector": "CRO - Clinical Research",
        "buyer": "Hellman & Friedman",
        "year": 2018,
        "region": "National",
        "ev_mm": 425.0,
        "ev_ebitda": 13.0,
        "ebitda_mm": 32.69,
        "ebitda_margin": 0.22,
        "revenue_mm": 148.58,
        "hold_years": 5.5,
        "moic": 2.7,
        "irr": 0.1964,
        "status": "Realized",
        "payer_mix": {"commercial": 0.88, "medicare": 0.04, "medicaid": 0.02, "self_pay": 0.06},
        "comm_pct": 0.88,
        "deal_narrative": (
            "National central lab CRO services platform delivering "
            "specialty testing, safety labs, biomarker assays, and "
            "flow cytometry across Phase I-III trials for oncology, "
            "immunology, and rare disease sponsors. Long hold scaled "
            "the flow cytometry and biomarker assay portfolio for "
            "checkpoint inhibitor programs, added two bioanalytical "
            "labs in Europe under MHRA inspection coverage, built a "
            "21 CFR Part 11 compliant LIMS replacement, and exited "
            "to a strategic global CRO at a 2.7x MOIC on MSA backlog."
        ),
    },
    {
        "company_name": "Gloucester Packaging CMO",
        "sector": "CMO - Packaging",
        "buyer": "Nordic Capital",
        "year": 2023,
        "region": "Northeast",
        "ev_mm": 95.0,
        "ev_ebitda": 10.5,
        "ebitda_mm": 9.05,
        "ebitda_margin": 0.17,
        "revenue_mm": 53.22,
        "hold_years": 2.5,
        "moic": 1.4,
        "irr": 0.1479,
        "status": "Active",
        "payer_mix": {"commercial": 0.83, "medicare": 0.05, "medicaid": 0.04, "self_pay": 0.08},
        "comm_pct": 0.83,
        "deal_narrative": (
            "Northeast CMO packaging operator delivering clinical trial "
            "supply labeling, blinding, and IRT-integrated kit assembly "
            "for Phase I-III sponsors. Early hold focuses on adding "
            "DSCSA serialization and aggregation capability on two "
            "additional packaging lines, building a GxP cold-chain 2-8C "
            "clinical supply depot, and positioning for a larger platform "
            "tuck-in. Platform suits a strategic CDMO acquirer integrating "
            "packaging into a broader end-to-end sterile fill-finish and "
            "clinical supply service offering for biopharma sponsors."
        ),
    },
    {
        "company_name": "Ashford HPAPI Manufacturing",
        "sector": "CDMO - Manufacturing",
        "buyer": "KKR",
        "year": 2017,
        "region": "National",
        "ev_mm": 575.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 41.07,
        "ebitda_margin": 0.27,
        "revenue_mm": 152.11,
        "hold_years": 6.0,
        "moic": 3.6,
        "irr": 0.2379,
        "status": "Realized",
        "payer_mix": {"commercial": 0.90, "medicare": 0.03, "medicaid": 0.02, "self_pay": 0.05},
        "comm_pct": 0.90,
        "deal_narrative": (
            "National highly potent API (HPAPI) CDMO platform delivering "
            "OEB 4/5 containment small-molecule API and oral solid dose "
            "manufacturing for oncology, hormone-therapy, and cytotoxic "
            "programs. Long hold expanded HPAPI containment capacity with "
            "two new isolator suites capturing 30-40% premium pricing "
            "versus standard cGMP API, added an antibody-drug conjugate "
            "(ADC) linker-payload capability on the back of Enhertu and "
            "Trodelvy commercial success, remediated an FDA Form 483 on "
            "change-control procedures, and exited to a strategic at 3.6x."
        ),
    },
    {
        "company_name": "Langford Decentralized Trials",
        "sector": "CRO - Clinical Research",
        "buyer": "Vista Equity Partners",
        "year": 2022,
        "region": "National",
        "ev_mm": 265.0,
        "ev_ebitda": 17.5,
        "ebitda_mm": 15.14,
        "ebitda_margin": 0.19,
        "revenue_mm": 79.68,
        "hold_years": 3.0,
        "moic": 1.5,
        "irr": 0.1447,
        "status": "Active",
        "payer_mix": {"commercial": 0.86, "medicare": 0.04, "medicaid": 0.03, "self_pay": 0.07},
        "comm_pct": 0.86,
        "deal_narrative": (
            "National decentralized clinical trial (DCT) specialist CRO "
            "delivering hybrid and fully-virtual Phase II-III trial "
            "execution with eCOA / ePRO, wearables, telemedicine visits, "
            "and direct-to-patient IMP shipment. Value creation scales "
            "the DCT technology stack under FDA 21 CFR Part 11 and ICH-"
            "GCP E6(R3) compliance, adds a home-health nurse network "
            "for in-home dosing and sample collection, and positions "
            "for tuck-in acquisition by a top-10 CRO building DCT "
            "capability amid slower-than-expected DCT adoption curves."
        ),
    },
    {
        "company_name": "Rothwell Biologics Capacity",
        "sector": "CDMO - Manufacturing",
        "buyer": "Permira",
        "year": 2024,
        "region": "Mid-Atlantic",
        "ev_mm": 835.0,
        "ev_ebitda": 18.0,
        "ebitda_mm": 46.39,
        "ebitda_margin": 0.28,
        "revenue_mm": 165.68,
        "hold_years": 2.5,
        "moic": 1.4,
        "irr": 0.1479,
        "status": "Active",
        "payer_mix": {"commercial": 0.92, "medicare": 0.02, "medicaid": 0.02, "self_pay": 0.04},
        "comm_pct": 0.92,
        "deal_narrative": (
            "Mid-Atlantic biologics drug substance CDMO delivering "
            "late-phase and commercial mammalian cell culture (CHO) "
            "manufacturing at 2,000L and 5,000L scale for monoclonal "
            "antibody and bispecific programs. Recent acquisition at "
            "peak biologics capacity scarcity pricing post the COVID "
            "build-out. Early hold focuses on qualifying two additional "
            "bioreactor trains, executing PAI on three sponsor commercial "
            "programs, adding a drug product fill-finish capability for "
            "end-to-end biologics service, and capturing tech-transfer "
            "demand from Humira and Stelara biosimilar launch waves."
        ),
    },
]
