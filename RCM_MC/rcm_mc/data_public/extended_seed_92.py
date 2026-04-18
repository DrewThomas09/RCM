"""Extended seed 92: Gastroenterology / endoscopy / colonoscopy PE deals.

This module contains a curated set of 15 healthcare private equity deal
records focused on the gastroenterology / endoscopy / colonoscopy sub-
sector. The theme covers:

- Gastroenterology physician practice platforms delivering office-based
  consultations, IBD / IBS / GERD medical management, hepatology, and
  motility services alongside an in-office ancillary endoscopy suite or
  affiliated ASC endoscopy center under the PE-backed GI aggregation
  thesis pioneered by GI Alliance, US Digestive Partners, Unio Health,
  One GI, and Gastro Health
- Endoscopy ambulatory surgical center (ASC) operators delivering
  screening and diagnostic upper endoscopy (EGD), colonoscopy with
  biopsy / polypectomy, ERCP, and endoscopic ultrasound (EUS) under
  CMS ASC fee schedule rates and HOPPS APC-equivalent benchmarking,
  with the CMS APC 5313 (Level 3 Lower GI Procedures) and APC 5312
  (Level 2 Lower GI Procedures) packaged payments anchoring revenue
- Colonoscopy screening operators capturing the demographic tailwind
  from the 2021 USPSTF recommendation lowering the colorectal cancer
  screening start age from 50 to 45 and the corresponding CMS rule
  change expanding Medicare screening colonoscopy coverage to age-45-
  plus beneficiaries, combined with CBO savings estimates on downstream
  colorectal cancer cost avoidance driving payer coverage expansion
- GI hospitalist groups delivering inpatient GI consults, inpatient EGD
  / colonoscopy for GI bleed workup, and ERCP coverage for hospital
  systems under professional-fee arrangements on CPT 43235 / 45378 /
  43260 with stipend support for low-volume inpatient call coverage
- GI pathology operators delivering biopsy reads on CPT 88305 with
  H. pylori IHC 88342, Barrett's esophagus surveillance with FISH
  88365, and dysplasia screening to independent GI practices and ASC
  endoscopy centers under pathologist-shortage-driven GI-subspecialty
  wage arbitrage

Gastroenterology and endoscopy economics are distinguished by a
commercial-heavy payer mix (commercial 38-55%, Medicare 30-45%,
Medicaid 5-12%, self-pay balance) reflecting the average colonoscopy
patient population skewing toward age-45-through-Medicare-age baby-
boomer and Gen-X cohorts, CPT-code-driven revenue mechanics on the
CMS Medicare Physician Fee Schedule (CPT 45378 diagnostic colonoscopy,
45380 with biopsy, 45385 with snare polypectomy, 43235 diagnostic EGD,
43239 EGD with biopsy) paired with facility-fee revenue under the
ASC payment system or HOPPS APC packaged payments for hospital
outpatient departments, anesthesia-services revenue under the CMS
2018 policy change permitting separate billing for MAC / propofol
anesthesia during screening colonoscopy, CRNA / MD anesthesia carve-
outs creating an adjacent revenue stream (increasingly targeted by
payer-driven medical-necessity review on routine-risk patients), the
USPSTF 2021 / CMS 2022 age-45 screening threshold expansion driving
a structural volume tailwind estimated by CBO at 4-6 million additional
annual screening eligibles, waived Medicare cost-sharing on screening
colonoscopy including when a polyp-removal conversion occurs (the ACA
screening loophole fix fully phased in 2030), and the HOPPS / ASC
site-of-service differential (ASC APC-equivalent rates are 55-60% of
HOPPS) making freestanding ASC endoscopy economically attractive for
payers and PE sponsors. Value creation in PE-backed GI platforms
centers on same-store provider productivity optimization (RVU / work-
day lift), ASC migration capturing facility-fee revenue previously
flowing to hospital HOPPS partners, anesthesia-services insourcing
via CRNA or MD-led MAC programs capturing propofol anesthesia revenue,
in-office GI pathology and infusion ancillaries, GI hospitalist call-
coverage contracts with hospital systems, and roll-up acquisition of
independent single-shingle GI groups into regional MSO platforms
modeled on GI Alliance (Waud Capital / Apollo), US Digestive Partners
(Amulet Capital), One GI (FFL Partners), Gastro Health (Omers), and
Unio Health (Altamont Capital). Each record captures deal economics
(EV, EV/EBITDA, margins), return profile (MOIC, IRR, hold period),
payer mix, regional footprint, sponsor, realization status, and a
short deal narrative. These records are synthesized for modeling,
backtesting, and scenario analysis use cases.
"""

EXTENDED_SEED_DEALS_92 = [
    {
        "company_name": "Meridian Digestive Health",
        "sector": "Gastroenterology Practice",
        "buyer": "Waud Capital Partners",
        "year": 2017,
        "region": "Southwest",
        "ev_mm": 425.0,
        "ev_ebitda": 13.0,
        "ebitda_mm": 95.19,
        "ebitda_margin": 0.23,
        "revenue_mm": 413.87,
        "hold_years": 6.0,
        "moic": 3.4,
        "irr": 0.2264,
        "status": "Realized",
        "payer_mix": {"commercial": 0.48, "medicare": 0.38, "medicaid": 0.08, "self_pay": 0.06},
        "comm_pct": 0.48,
        "deal_narrative": (
            "Southwest multi-site gastroenterology practice platform "
            "serving as an early PE-backed GI aggregation roll-up in the "
            "vein of GI Alliance and US Digestive Partners. Long hold "
            "consolidated 42 single-shingle GI groups onto a shared MSO, "
            "migrated screening colonoscopy volume from HOPPS hospital "
            "outpatient to affiliated ASC endoscopy centers capturing the "
            "ASC / HOPPS site-of-service differential, insourced propofol "
            "MAC anesthesia through a CRNA-led program, captured the "
            "USPSTF 2021 age-45 screening tailwind in late-hold years, and "
            "exited to a strategic GI consolidator at 3.4x MOIC on "
            "multi-state platform scarcity value."
        ),
    },
    {
        "company_name": "Ridgeline Endoscopy Partners",
        "sector": "Endoscopy ASC",
        "buyer": "Audax Private Equity",
        "year": 2018,
        "region": "Southeast",
        "ev_mm": 315.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 63.00,
        "ebitda_margin": 0.25,
        "revenue_mm": 252.00,
        "hold_years": 5.5,
        "moic": 3.0,
        "irr": 0.2184,
        "status": "Realized",
        "payer_mix": {"commercial": 0.52, "medicare": 0.34, "medicaid": 0.08, "self_pay": 0.06},
        "comm_pct": 0.52,
        "deal_narrative": (
            "Southeast regional endoscopy ASC operator running 18 free-"
            "standing endoscopy centers delivering screening colonoscopy "
            "(CPT 45378 / 45380 / 45385), diagnostic EGD (43235 / 43239), "
            "and ERCP (43260). Long hold captured the ASC / HOPPS site-of-"
            "service differential (ASC APC-equivalent rates ~55-60% of "
            "HOPPS) as payers steered screening volume to freestanding "
            "ASCs, insourced MD-led MAC / propofol anesthesia capturing "
            "the carve-out revenue, absorbed CMS APC 5312 / 5313 packaged "
            "payment recalibrations, and exited to a strategic ASC "
            "platform at a 3.0x MOIC."
        ),
    },
    {
        "company_name": "Coastal Colorectal Screening",
        "sector": "Colonoscopy Screening",
        "buyer": "Amulet Capital Partners",
        "year": 2022,
        "region": "West",
        "ev_mm": 225.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 40.50,
        "ebitda_margin": 0.22,
        "revenue_mm": 184.09,
        "hold_years": 3.0,
        "moic": 1.8,
        "irr": 0.2164,
        "status": "Active",
        "payer_mix": {"commercial": 0.50, "medicare": 0.36, "medicaid": 0.08, "self_pay": 0.06},
        "comm_pct": 0.50,
        "deal_narrative": (
            "West Coast screening-focused colonoscopy platform built to "
            "capture the USPSTF 2021 recommendation lowering colorectal "
            "cancer screening start age from 50 to 45 and the CMS 2022 "
            "rule change extending Medicare screening colonoscopy "
            "coverage to age-45-plus beneficiaries. Early hold targets "
            "the CBO-estimated 4-6 million additional annual screening "
            "eligibles, layers direct-to-employer screening contracts, "
            "maintains waived cost-sharing on ACA-covered screening "
            "colonoscopy including polyp-removal conversion under the "
            "screening-loophole fix, and navigates commercial payer "
            "medical-policy interpretation on the age-45 threshold."
        ),
    },
    {
        "company_name": "Alpine GI Hospitalists",
        "sector": "GI Hospitalist",
        "buyer": "Shore Capital Partners",
        "year": 2019,
        "region": "Midwest",
        "ev_mm": 95.0,
        "ev_ebitda": 10.5,
        "ebitda_mm": 14.48,
        "ebitda_margin": 0.17,
        "revenue_mm": 85.15,
        "hold_years": 5.0,
        "moic": 2.2,
        "irr": 0.1713,
        "status": "Realized",
        "payer_mix": {"commercial": 0.42, "medicare": 0.42, "medicaid": 0.10, "self_pay": 0.06},
        "comm_pct": 0.42,
        "deal_narrative": (
            "Midwest GI hospitalist group delivering inpatient GI consults, "
            "inpatient EGD / colonoscopy for upper and lower GI bleed "
            "workup, and ERCP coverage under CPT 43235 / 45378 / 43260 "
            "professional-fee arrangements with 14 community hospitals. "
            "Long hold negotiated call-coverage stipends from partner "
            "hospitals for low-volume ERCP and weekend coverage, expanded "
            "advanced-endoscopy subspecialty coverage (EUS, ESD) capturing "
            "higher CPT reimbursement, and exited to a strategic hospital-"
            "based-physician platform at 2.2x MOIC."
        ),
    },
    {
        "company_name": "Summit GI Pathology Group",
        "sector": "GI Pathology",
        "buyer": "Webster Equity Partners",
        "year": 2018,
        "region": "Northeast",
        "ev_mm": 165.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 29.70,
        "ebitda_margin": 0.22,
        "revenue_mm": 135.00,
        "hold_years": 5.5,
        "moic": 2.7,
        "irr": 0.2018,
        "status": "Realized",
        "payer_mix": {"commercial": 0.51, "medicare": 0.36, "medicaid": 0.08, "self_pay": 0.05},
        "comm_pct": 0.51,
        "deal_narrative": (
            "Northeast GI pathology specialist delivering CPT 88305 biopsy "
            "reads, H. pylori IHC 88342, Barrett's esophagus surveillance "
            "with FISH 88365, and dysplasia screening to independent GI "
            "practices and ASC endoscopy centers. Long hold captured "
            "pathologist-shortage arbitrage on GI-subspecialty reads "
            "($500K-$650K comp band), rolled up three regional GI path "
            "groups, deployed digital whole-slide imaging for remote "
            "sign-out, partnered with PE-backed GI aggregators as "
            "preferred pathology vendor, and exited to a strategic "
            "anatomic pathology consolidator at 2.7x MOIC."
        ),
    },
    {
        "company_name": "Harborpoint Digestive Partners",
        "sector": "Gastroenterology Practice",
        "buyer": "Apollo Global Management",
        "year": 2020,
        "region": "National",
        "ev_mm": 785.0,
        "ev_ebitda": 15.0,
        "ebitda_mm": 164.85,
        "ebitda_margin": 0.25,
        "revenue_mm": 659.40,
        "hold_years": 4.5,
        "moic": 2.3,
        "irr": 0.2044,
        "status": "Active",
        "payer_mix": {"commercial": 0.49, "medicare": 0.37, "medicaid": 0.08, "self_pay": 0.06},
        "comm_pct": 0.49,
        "deal_narrative": (
            "National GI aggregation platform modeled on GI Alliance with "
            "320+ gastroenterologists across 12 states, integrated "
            "endoscopy ASCs, in-office GI pathology and infusion "
            "ancillaries. Mid-hold strategy captures USPSTF age-45 "
            "screening volume tailwind (CBO estimates 4-6M additional "
            "annual eligibles), migrates remaining HOPPS endoscopy volume "
            "to affiliated ASCs on the HOPPS / ASC site-of-service spread, "
            "insources propofol MAC anesthesia via CRNA-led programs, "
            "and pursues direct-to-employer and ACO REACH arrangements "
            "sharing in downstream colorectal cancer cost-avoidance "
            "savings."
        ),
    },
    {
        "company_name": "Pinecrest Endoscopy Centers",
        "sector": "Endoscopy ASC",
        "buyer": "Linden Capital Partners",
        "year": 2019,
        "region": "Mid-Atlantic",
        "ev_mm": 245.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 49.00,
        "ebitda_margin": 0.26,
        "revenue_mm": 188.46,
        "hold_years": 5.0,
        "moic": 2.6,
        "irr": 0.2108,
        "status": "Realized",
        "payer_mix": {"commercial": 0.50, "medicare": 0.36, "medicaid": 0.09, "self_pay": 0.05},
        "comm_pct": 0.50,
        "deal_narrative": (
            "Mid-Atlantic endoscopy ASC operator with 11 freestanding "
            "centers delivering screening colonoscopy, diagnostic EGD, "
            "and advanced endoscopy (EUS, ERCP) under CMS ASC fee "
            "schedule rates benchmarked to HOPPS APC 5312 / 5313 packaged "
            "payments. Long hold navigated the CMS 2018 policy change "
            "allowing separate billing for MAC / propofol anesthesia on "
            "screening colonoscopy (monetizing the carve-out through a "
            "captive anesthesia company), absorbed CMS annual APC / ASC "
            "rate recalibrations, added two de-novo centers in CON-friendly "
            "states, and exited to a strategic ASC chain at 2.6x MOIC."
        ),
    },
    {
        "company_name": "Laurelwood Screening Colonoscopy",
        "sector": "Colonoscopy Screening",
        "buyer": "FFL Partners",
        "year": 2023,
        "region": "Southeast",
        "ev_mm": 145.0,
        "ev_ebitda": 16.0,
        "ebitda_mm": 23.20,
        "ebitda_margin": 0.20,
        "revenue_mm": 116.00,
        "hold_years": 2.5,
        "moic": 1.5,
        "irr": 0.1818,
        "status": "Active",
        "payer_mix": {"commercial": 0.45, "medicare": 0.40, "medicaid": 0.09, "self_pay": 0.06},
        "comm_pct": 0.45,
        "deal_narrative": (
            "Southeast direct-to-consumer screening colonoscopy operator "
            "launched specifically to address the USPSTF 2021 / CMS 2022 "
            "age-45 screening coverage expansion gap, partnering with "
            "self-insured employers, ACO REACH entities, and Medicare "
            "Advantage plans seeking HEDIS colorectal cancer screening "
            "rate improvement. Early hold builds a hub-and-spoke network "
            "of screening ASCs with bundled pricing, captures waived ACA "
            "patient cost-sharing on screening colonoscopy, navigates "
            "commercial payer medical-policy review of FIT-DNA Cologuard "
            "substitution, and markets CBO-endorsed downstream colorectal "
            "cancer cost-avoidance savings to risk-bearing payer partners."
        ),
    },
    {
        "company_name": "Bayridge GI Medical Group",
        "sector": "Gastroenterology Practice",
        "buyer": "Altamont Capital Partners",
        "year": 2016,
        "region": "West",
        "ev_mm": 285.0,
        "ev_ebitda": 11.5,
        "ebitda_mm": 62.70,
        "ebitda_margin": 0.21,
        "revenue_mm": 298.57,
        "hold_years": 6.5,
        "moic": 3.8,
        "irr": 0.2243,
        "status": "Realized",
        "payer_mix": {"commercial": 0.50, "medicare": 0.35, "medicaid": 0.09, "self_pay": 0.06},
        "comm_pct": 0.50,
        "deal_narrative": (
            "West Coast GI platform founded as an early regional anchor "
            "for a national aggregation thesis resembling the Unio Health "
            "playbook. Long 6.5-year hold rolled up 28 single-shingle and "
            "small-group GI practices, migrated 65% of endoscopy volume "
            "from HOPPS to affiliated ASCs, insourced propofol MAC "
            "anesthesia via an owned anesthesia management company, "
            "captured late-hold USPSTF age-45 screening tailwind, and "
            "exited to a strategic national GI consolidator at 3.8x MOIC "
            "on scarcity value in the Western U.S. GI market."
        ),
    },
    {
        "company_name": "Foxhollow Endoscopy Centers",
        "sector": "Endoscopy ASC",
        "buyer": "Riverside Company",
        "year": 2021,
        "region": "Southeast",
        "ev_mm": 185.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 40.70,
        "ebitda_margin": 0.26,
        "revenue_mm": 156.54,
        "hold_years": 3.5,
        "moic": 1.7,
        "irr": 0.1594,
        "status": "Active",
        "payer_mix": {"commercial": 0.54, "medicare": 0.32, "medicaid": 0.08, "self_pay": 0.06},
        "comm_pct": 0.54,
        "deal_narrative": (
            "Southeast ASC endoscopy operator with 7 centers delivering "
            "screening and diagnostic colonoscopy / EGD on CMS ASC "
            "fee schedule rates. Value creation navigates ongoing CMS "
            "HOPPS APC 5312 / 5313 recalibrations flowing through to ASC "
            "benchmark rates, faces rising payer scrutiny on propofol "
            "MAC anesthesia medical necessity for routine-risk screening "
            "(ASA I-II) patients as commercial payers pilot anesthesia "
            "carve-out denials, partners with regional PE-backed GI "
            "aggregators as preferred ASC site, and pursues de-novo ASC "
            "expansion in adjacent CON-relaxed states."
        ),
    },
    {
        "company_name": "Crestwood GI Hospitalists",
        "sector": "GI Hospitalist",
        "buyer": "Kelso & Company",
        "year": 2020,
        "region": "National",
        "ev_mm": 175.0,
        "ev_ebitda": 11.0,
        "ebitda_mm": 28.00,
        "ebitda_margin": 0.18,
        "revenue_mm": 155.56,
        "hold_years": 4.0,
        "moic": 1.9,
        "irr": 0.1763,
        "status": "Active",
        "payer_mix": {"commercial": 0.40, "medicare": 0.45, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.40,
        "deal_narrative": (
            "National GI hospitalist platform delivering inpatient "
            "endoscopy, ERCP coverage, and GI consult services to 60+ "
            "hospital partners under professional-fee plus stipend "
            "contracts. Mid-hold strategy centralizes scheduling and "
            "credentialing across state lines, expands advanced endoscopy "
            "(EUS, ESD, POEM) capability capturing higher CPT "
            "reimbursement, negotiates hospital stipend increases "
            "reflecting post-2022 inflation and GI physician shortage, "
            "and positions for an exit to a strategic hospital-based-"
            "physician platform or a PE-backed GI aggregator seeking "
            "inpatient-referral feeder channel."
        ),
    },
    {
        "company_name": "Trillium GI Pathology",
        "sector": "GI Pathology",
        "buyer": "Gryphon Investors",
        "year": 2021,
        "region": "National",
        "ev_mm": 215.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 51.60,
        "ebitda_margin": 0.24,
        "revenue_mm": 215.00,
        "hold_years": 3.5,
        "moic": 1.6,
        "irr": 0.1418,
        "status": "Active",
        "payer_mix": {"commercial": 0.52, "medicare": 0.35, "medicaid": 0.08, "self_pay": 0.05},
        "comm_pct": 0.52,
        "deal_narrative": (
            "National GI pathology roll-up serving PE-backed GI "
            "aggregation platforms (GI Alliance, US Digestive, One GI, "
            "Gastro Health) as preferred pathology partner on CPT 88305 "
            "biopsy reads with ancillary H. pylori IHC 88342 and Barrett's "
            "FISH 88365. Mid-hold captures GI-subspecialty pathologist-"
            "shortage wage arbitrage, deploys centralized digital "
            "pathology whole-slide-imaging sign-out across four regional "
            "hubs, negotiates multi-year GI-platform contracts tied to "
            "the age-45 screening volume ramp, and navigates commercial "
            "payer prior-auth review on specialty IHC ancillaries."
        ),
    },
    {
        "company_name": "Northgate Digestive Partners",
        "sector": "Gastroenterology Practice",
        "buyer": "Omers Private Equity",
        "year": 2019,
        "region": "Southeast",
        "ev_mm": 525.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 136.50,
        "ebitda_margin": 0.26,
        "revenue_mm": 525.00,
        "hold_years": 5.0,
        "moic": 2.5,
        "irr": 0.2011,
        "status": "Active",
        "payer_mix": {"commercial": 0.47, "medicare": 0.39, "medicaid": 0.08, "self_pay": 0.06},
        "comm_pct": 0.47,
        "deal_narrative": (
            "Southeast-anchored multi-state GI aggregation platform "
            "modeled on Gastro Health with 180+ gastroenterologists, "
            "22 affiliated endoscopy ASCs, integrated anesthesia, GI "
            "pathology, and specialty pharmacy ancillaries. Mid-hold "
            "captures USPSTF age-45 screening volume tailwind, migrates "
            "remaining hospital-based endoscopy volume to affiliated ASCs "
            "on the HOPPS / ASC site-of-service spread (ASC rates ~55-60% "
            "of HOPPS), expands direct-to-employer screening partnerships "
            "marketing CBO-estimated downstream colorectal cancer cost-"
            "avoidance savings, and positions for a secondary exit to a "
            "larger sovereign / pension-aligned sponsor."
        ),
    },
    {
        "company_name": "Evergreen Endoscopy Surgical Centers",
        "sector": "Endoscopy ASC",
        "buyer": "Thomas H. Lee Partners",
        "year": 2017,
        "region": "Northeast",
        "ev_mm": 265.0,
        "ev_ebitda": 12.0,
        "ebitda_mm": 58.30,
        "ebitda_margin": 0.27,
        "revenue_mm": 215.93,
        "hold_years": 6.0,
        "moic": 2.9,
        "irr": 0.1976,
        "status": "Realized",
        "payer_mix": {"commercial": 0.55, "medicare": 0.30, "medicaid": 0.09, "self_pay": 0.06},
        "comm_pct": 0.55,
        "deal_narrative": (
            "Northeast ASC endoscopy chain with 14 freestanding centers "
            "capturing the HOPPS-to-ASC site-of-service migration in a "
            "heavily-commercially-insured region. Long hold absorbed CMS "
            "HOPPS APC 5312 / 5313 packaged-payment recalibrations, "
            "captured the CMS 2018 propofol MAC anesthesia separate-"
            "billing policy via a captive CRNA-led anesthesia company, "
            "added early USPSTF age-45 screening volume in the late "
            "hold years, remediated CPT 45380 / 45385 polypectomy coding "
            "accuracy on the screening-to-diagnostic colonoscopy "
            "conversion (pre-2030 cost-sharing phase-in), and exited to "
            "a strategic ASC operator at 2.9x MOIC."
        ),
    },
    {
        "company_name": "Kingsbridge Colorectal Care",
        "sector": "Colonoscopy Screening",
        "buyer": "Leonard Green & Partners",
        "year": 2024,
        "region": "National",
        "ev_mm": 365.0,
        "ev_ebitda": 17.5,
        "ebitda_mm": 66.43,
        "ebitda_margin": 0.22,
        "revenue_mm": 301.96,
        "hold_years": 2.5,
        "moic": 1.4,
        "irr": 0.1479,
        "status": "Active",
        "payer_mix": {"commercial": 0.43, "medicare": 0.44, "medicaid": 0.07, "self_pay": 0.06},
        "comm_pct": 0.43,
        "deal_narrative": (
            "National colorectal cancer screening platform acquired at "
            "the top of the ASC / GI multiple cycle to capture the full "
            "demographic ramp of the USPSTF 2021 / CMS 2022 age-45 "
            "screening threshold (CBO estimates 4-6M additional annual "
            "screening eligibles, with peak incremental volume reaching "
            "the Medicare-edge baby-boomer and Gen-X cohorts mid-decade). "
            "Early hold builds direct-to-employer and Medicare Advantage "
            "screening contracts, navigates rising commercial payer "
            "scrutiny on propofol MAC anesthesia medical necessity for "
            "routine-risk (ASA I-II) screening patients, prepares for "
            "the ACA screening-loophole fix fully phasing in by 2030 "
            "eliminating patient cost-sharing on polyp-removal "
            "conversions, and partners with risk-bearing ACO REACH "
            "entities sharing downstream colorectal cancer cost-"
            "avoidance savings."
        ),
    },
]
