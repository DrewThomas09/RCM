"""Extended seed 91: Lab / pathology / diagnostics PE deals.

This module contains a curated set of 15 healthcare private equity deal
records focused on the lab / pathology / diagnostics subsector. The
theme covers:

- Clinical laboratory operators delivering routine chemistry,
  hematology, microbiology, and immunoassay testing to physician
  offices, hospitals, and skilled nursing facilities under PAMA-
  reset Clinical Laboratory Fee Schedule (CLFS) pricing, CPT 80048
  basic metabolic / 80053 comprehensive metabolic / 85025 CBC-with-
  differential fee compression, and CLIA high-complexity oversight
- Anatomic pathology platforms delivering surgical pathology, GI
  pathology, dermatopathology, urology (uropath), and cytology
  under CPT 88305 / 88307 / 88309 surgical pathology tiers with
  pathologist shortage driving wage inflation and LCD coverage
  variability on specialty IHC and FISH stains (88341, 88342, 88365)
- Molecular diagnostics operators delivering NGS panels, single-
  gene oncology hotspot testing, liquid biopsy ctDNA, hereditary
  cancer panels, and pharmacogenomics under CPT 81xxx Tier 1 / Tier
  2 / GSP codes with MolDx (Palmetto) LCD coverage determinations,
  ADLT (Advanced Diagnostic Laboratory Test) pricing pathways, and
  PAMA private-payer reporting on molecular test reimbursement
- Toxicology labs delivering pain-management urine drug screening
  (presumptive G0480-G0483) and definitive confirmation (CPT 80305-
  80307, 80320-80377) to addiction-treatment, pain-management, and
  behavioral-health clients under 2016 CMS toxicology code consolida-
  tion, LCA / LCD medical-necessity edits, and prior-authorization
  shift pressure
- Reference lab platforms delivering specialty esoteric testing
  (endocrinology, autoimmune, infectious disease, transplant
  monitoring) as send-out partners to hospital outreach labs and
  integrated delivery networks under PAMA CLFS rate cuts and the
  FDA LDT rule finalized in 2024 phasing in FDA oversight on
  laboratory-developed tests

Lab and diagnostics economics are distinguished by a commercial-
heavy payer mix (commercial 45-65%, Medicare 22-35%, Medicaid 6-14%,
self-pay balance), CPT-code-driven revenue mechanics on the Clinical
Laboratory Fee Schedule (CLFS) with triennial PAMA-reset private-
payer-data-weighted rate cycles, MolDx jurisdictional LCD coverage
variability driving uncertainty on molecular test reimbursement,
pathologist shortage-driven subspecialty wage inflation (GI path,
dermpath, hematopath command $400-$650K comp), LDT (laboratory-
developed test) regulatory overhang from the FDA LDT rule finalized
in 2024 phasing in premarket review over four years, ADLT pricing
pathways offering 3-year protected reimbursement for novel molecular
tests, prior-authorization and utilization-management pressure on
high-cost molecular panels, 14-day rule / CMS Medicare-hospital-
outreach-billing complexity, and the ongoing shift from physician-
office lab (POL) to reference-send-out as PAMA rate compression
hits high-volume routine chemistry hardest. Value creation in PE-
backed lab platforms centers on specimen-volume consolidation across
regional draw stations, IT / LIS modernization with EHR interfaces,
revenue cycle remediation on CPT coding accuracy and prior-auth
capture, molecular menu expansion into higher-reimbursement NGS
oncology and MRD panels, dermatopathology / GI pathology roll-ups
capturing pathologist-shortage arbitrage, toxicology client retention
through compliant utilization patterns, and ADLT designation pursuit
on proprietary molecular assays.

Each record captures deal economics (EV, EV/EBITDA, margins), return
profile (MOIC, IRR, hold period), payer mix, regional footprint,
sponsor, realization status, and a short deal narrative. These
records are synthesized for modeling, backtesting, and scenario
analysis use cases.
"""

EXTENDED_SEED_DEALS_91 = [
    {
        "company_name": "Meridian Clinical Labs",
        "sector": "Clinical Laboratory",
        "buyer": "Warburg Pincus",
        "year": 2017,
        "region": "Southeast",
        "ev_mm": 485.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 35.93,
        "ebitda_margin": 0.22,
        "revenue_mm": 163.30,
        "hold_years": 6.0,
        "moic": 3.2,
        "irr": 0.2163,
        "status": "Realized",
        "payer_mix": {"commercial": 0.56, "medicare": 0.28, "medicaid": 0.10, "self_pay": 0.06},
        "comm_pct": 0.56,
        "deal_narrative": (
            "Southeast regional clinical laboratory platform delivering "
            "routine chemistry, hematology, and immunoassay testing to "
            "physician offices, urgent care, and SNF clients on CPT 80048, "
            "80053, 85025, and 84443 TSH volume. Long hold consolidated "
            "specimen draw stations from 180 to 420 locations, absorbed "
            "three consecutive PAMA CLFS rate cuts through automation-"
            "driven unit-cost reduction on high-volume CMP / CBC lines, "
            "added a molecular diagnostics menu capturing higher CPT 81xxx "
            "reimbursement, and exited to a strategic national lab at 3.2x "
            "MOIC after PAMA rate stabilization improved platform visibility."
        ),
    },
    {
        "company_name": "Pinecrest Pathology Partners",
        "sector": "Anatomic Pathology",
        "buyer": "Avista Healthcare Partners",
        "year": 2018,
        "region": "National",
        "ev_mm": 625.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 43.10,
        "ebitda_margin": 0.25,
        "revenue_mm": 172.41,
        "hold_years": 5.5,
        "moic": 2.9,
        "irr": 0.2076,
        "status": "Realized",
        "payer_mix": {"commercial": 0.58, "medicare": 0.26, "medicaid": 0.09, "self_pay": 0.07},
        "comm_pct": 0.58,
        "deal_narrative": (
            "National anatomic pathology roll-up delivering surgical "
            "pathology, GI pathology, and dermatopathology subspecialty "
            "reads on CPT 88305 / 88307 / 88309 tiers plus IHC 88341-88342 "
            "and FISH 88365 ancillaries. Long hold rolled up 14 regional "
            "pathology groups capturing pathologist-shortage arbitrage on "
            "GI path and dermpath subspecialty comp, centralized histology "
            "processing into two GMP-grade hubs, deployed digital pathology "
            "whole-slide imaging for remote sign-out, navigated LCD coverage "
            "variability on specialty IHC panels, and exited to a strategic "
            "hospital-outreach lab at a 2.9x MOIC."
        ),
    },
    {
        "company_name": "Riverbend Molecular Diagnostics",
        "sector": "Molecular Diagnostics",
        "buyer": "Ampersand Capital",
        "year": 2019,
        "region": "Mid-Atlantic",
        "ev_mm": 545.0,
        "ev_ebitda": 16.0,
        "ebitda_mm": 34.06,
        "ebitda_margin": 0.24,
        "revenue_mm": 141.93,
        "hold_years": 5.0,
        "moic": 2.7,
        "irr": 0.2199,
        "status": "Realized",
        "payer_mix": {"commercial": 0.62, "medicare": 0.24, "medicaid": 0.08, "self_pay": 0.06},
        "comm_pct": 0.62,
        "deal_narrative": (
            "Mid-Atlantic molecular diagnostics operator delivering NGS "
            "oncology hotspot panels, hereditary cancer panels, and "
            "pharmacogenomics testing under CPT 81445, 81455, 81432, and "
            "Tier 2 codes. Long hold pursued ADLT designation on a "
            "proprietary 52-gene solid-tumor NGS panel securing 3-year "
            "protected reimbursement, navigated MolDx (Palmetto) LCD "
            "coverage determinations across four MAC jurisdictions, "
            "remediated CPT coding accuracy lifting clean-claim rate 12 "
            "points, and exited to a strategic oncology diagnostics "
            "consolidator at a 2.7x MOIC on molecular menu depth."
        ),
    },
    {
        "company_name": "Cascade Toxicology Labs",
        "sector": "Toxicology Lab",
        "buyer": "Shore Capital Partners",
        "year": 2018,
        "region": "West",
        "ev_mm": 195.0,
        "ev_ebitda": 11.5,
        "ebitda_mm": 35.09,
        "ebitda_margin": 0.19,
        "revenue_mm": 184.70,
        "hold_years": 4.5,
        "moic": 2.1,
        "irr": 0.1818,
        "status": "Realized",
        "payer_mix": {"commercial": 0.52, "medicare": 0.25, "medicaid": 0.13, "self_pay": 0.10},
        "comm_pct": 0.52,
        "deal_narrative": (
            "West Coast toxicology lab serving pain-management, addiction-"
            "treatment, and behavioral-health clients with presumptive "
            "urine drug screening (G0480-G0483) and LC-MS/MS definitive "
            "confirmation (CPT 80305-80307, 80320-80377). Hold navigated "
            "the 2016 CMS toxicology code consolidation rate cycle, "
            "remediated LCA / LCD medical-necessity edits driving initial "
            "denials on excessive confirmation panels, shifted the client "
            "base toward compliant utilization-pattern pain clinics, and "
            "exited to a strategic toxicology consolidator at 2.1x MOIC."
        ),
    },
    {
        "company_name": "Ashbury Reference Labs",
        "sector": "Reference Lab",
        "buyer": "New Mountain Capital",
        "year": 2016,
        "region": "National",
        "ev_mm": 735.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 52.50,
        "ebitda_margin": 0.23,
        "revenue_mm": 228.26,
        "hold_years": 6.5,
        "moic": 3.5,
        "irr": 0.2040,
        "status": "Realized",
        "payer_mix": {"commercial": 0.55, "medicare": 0.29, "medicaid": 0.10, "self_pay": 0.06},
        "comm_pct": 0.55,
        "deal_narrative": (
            "National reference lab platform delivering specialty esoteric "
            "testing (endocrinology, autoimmune, infectious disease, "
            "transplant monitoring) as send-out partner to hospital "
            "outreach labs and IDN lab-outreach programs. Long hold "
            "absorbed two PAMA CLFS reset cycles via esoteric-menu mix "
            "shift to CPT 83xxx / 86xxx higher-reimbursement codes, "
            "prepared for FDA LDT rule compliance on 150+ laboratory-"
            "developed assays, added a transplant-monitoring cell-free "
            "DNA molecular panel, and exited to a strategic national lab "
            "at a 3.5x MOIC on reference-testing scale economics."
        ),
    },
    {
        "company_name": "Summit GI Pathology",
        "sector": "Anatomic Pathology",
        "buyer": "Webster Equity Partners",
        "year": 2020,
        "region": "Northeast",
        "ev_mm": 285.0,
        "ev_ebitda": 13.0,
        "ebitda_mm": 21.94,
        "ebitda_margin": 0.23,
        "revenue_mm": 95.38,
        "hold_years": 4.0,
        "moic": 2.0,
        "irr": 0.1892,
        "status": "Active",
        "payer_mix": {"commercial": 0.60, "medicare": 0.25, "medicaid": 0.09, "self_pay": 0.06},
        "comm_pct": 0.60,
        "deal_narrative": (
            "Northeast GI pathology specialist serving independent "
            "gastroenterology practices and ASC endoscopy centers with "
            "CPT 88305 biopsy reads, H. pylori IHC 88342, and FISH 88365 "
            "for Barrett's esophagus surveillance. Value creation captures "
            "pathologist-shortage arbitrage on GI-subspecialty reads "
            "(comp $500K-$650K), rolls up three regional GI path groups, "
            "deploys digital pathology whole-slide imaging enabling remote "
            "sign-out, and navigates LCD coverage variability on specialty "
            "IHC ancillaries under tightening prior-authorization review."
        ),
    },
    {
        "company_name": "Trillium NGS Oncology",
        "sector": "Molecular Diagnostics",
        "buyer": "General Atlantic",
        "year": 2021,
        "region": "National",
        "ev_mm": 785.0,
        "ev_ebitda": 17.5,
        "ebitda_mm": 44.86,
        "ebitda_margin": 0.26,
        "revenue_mm": 172.53,
        "hold_years": 3.5,
        "moic": 1.6,
        "irr": 0.1405,
        "status": "Active",
        "payer_mix": {"commercial": 0.63, "medicare": 0.23, "medicaid": 0.08, "self_pay": 0.06},
        "comm_pct": 0.63,
        "deal_narrative": (
            "National NGS oncology diagnostics platform delivering solid-"
            "tumor comprehensive genomic profiling (523-gene panel on CPT "
            "81455), liquid biopsy ctDNA, and hematologic malignancy MRD "
            "assays. Value creation pursues ADLT designation on the flagship "
            "CGP panel, navigates MolDx LCD coverage across seven MAC "
            "jurisdictions, responds to FDA LDT rule Stage 1 premarket "
            "review preparation on three high-volume assays, and captures "
            "molecular test reimbursement upside as NCCN guideline inclusion "
            "drives commercial payer medical-policy coverage expansion "
            "despite ongoing prior-authorization friction."
        ),
    },
    {
        "company_name": "Harborside Dermatopathology",
        "sector": "Anatomic Pathology",
        "buyer": "Linden Capital Partners",
        "year": 2019,
        "region": "Southwest",
        "ev_mm": 215.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 17.20,
        "ebitda_margin": 0.24,
        "revenue_mm": 71.67,
        "hold_years": 5.0,
        "moic": 2.5,
        "irr": 0.2011,
        "status": "Realized",
        "payer_mix": {"commercial": 0.61, "medicare": 0.24, "medicaid": 0.09, "self_pay": 0.06},
        "comm_pct": 0.61,
        "deal_narrative": (
            "Southwest dermatopathology platform serving 400+ dermatology "
            "practices with CPT 88305 shave / punch biopsy reads, MART-1 / "
            "S-100 / SOX10 IHC 88342 for melanoma margin assessment, and "
            "MOHS frozen-section support. Long hold rolled up four regional "
            "dermpath groups capturing pathologist-shortage wage arbitrage, "
            "deployed DermPath Dx digital pathology for remote sign-out, "
            "navigated CMS MPPR (multiple procedure payment reduction) "
            "policy on stacked IHC stains, and exited to a strategic "
            "pathology consolidator at a 2.5x MOIC."
        ),
    },
    {
        "company_name": "Blackwood Clinical Labs",
        "sector": "Clinical Laboratory",
        "buyer": "Wind Point Partners",
        "year": 2022,
        "region": "Midwest",
        "ev_mm": 165.0,
        "ev_ebitda": 11.0,
        "ebitda_mm": 26.40,
        "ebitda_margin": 0.17,
        "revenue_mm": 155.29,
        "hold_years": 3.0,
        "moic": 1.5,
        "irr": 0.1447,
        "status": "Active",
        "payer_mix": {"commercial": 0.49, "medicare": 0.32, "medicaid": 0.12, "self_pay": 0.07},
        "comm_pct": 0.49,
        "deal_narrative": (
            "Midwest regional clinical laboratory serving primary care, "
            "hospital outreach, and SNF clients with routine chemistry "
            "(CPT 80048, 80053), hematology (85025), and A1c monitoring "
            "(83036). Value creation navigates the post-PAMA CLFS rate "
            "environment through specimen-volume consolidation across "
            "two regional hubs, LIS modernization with Epic / Cerner EHR "
            "interfaces, revenue cycle remediation on the 14-day rule "
            "Medicare-hospital-outreach billing, and molecular menu "
            "expansion into respiratory and women's health PCR panels."
        ),
    },
    {
        "company_name": "Winthrop Toxicology Services",
        "sector": "Toxicology Lab",
        "buyer": "Abry Partners",
        "year": 2017,
        "region": "Southeast",
        "ev_mm": 135.0,
        "ev_ebitda": 10.0,
        "ebitda_mm": 29.16,
        "ebitda_margin": 0.18,
        "revenue_mm": 162.00,
        "hold_years": 5.5,
        "moic": 1.8,
        "irr": 0.1120,
        "status": "Realized",
        "payer_mix": {"commercial": 0.48, "medicare": 0.26, "medicaid": 0.14, "self_pay": 0.12},
        "comm_pct": 0.48,
        "deal_narrative": (
            "Southeast toxicology lab serving pain-management, OUD / MAT "
            "buprenorphine clinics, and behavioral-health residential "
            "programs with presumptive UDS (G0480-G0483) and LC-MS/MS "
            "confirmation (CPT 80320-80377). Long hold managed CMS "
            "toxicology code consolidation rate compression, navigated "
            "tightening LCA / LCD medical-necessity edits limiting "
            "confirmation-panel utilization, pivoted the client book "
            "toward compliant pain-clinic and OUD medication-assisted "
            "treatment programs, and exited to a smaller strategic at a "
            "1.8x MOIC reflecting toxicology rate-cycle headwinds."
        ),
    },
    {
        "company_name": "Crestwood Esoteric Reference",
        "sector": "Reference Lab",
        "buyer": "Thomas H. Lee Partners",
        "year": 2020,
        "region": "National",
        "ev_mm": 425.0,
        "ev_ebitda": 15.0,
        "ebitda_mm": 28.33,
        "ebitda_margin": 0.22,
        "revenue_mm": 128.79,
        "hold_years": 4.0,
        "moic": 1.9,
        "irr": 0.1752,
        "status": "Active",
        "payer_mix": {"commercial": 0.57, "medicare": 0.27, "medicaid": 0.10, "self_pay": 0.06},
        "comm_pct": 0.57,
        "deal_narrative": (
            "National esoteric reference lab delivering specialty "
            "autoimmune, endocrine, and infectious-disease send-out "
            "testing to hospital outreach programs and IDN outreach "
            "labs. Value creation prepares for FDA LDT rule Stage 1 "
            "premarket review on 80+ LDT assays, absorbs PAMA CLFS "
            "reset cycle rate cuts through esoteric-menu mix shift to "
            "CPT 83xxx hormones and 86xxx autoimmune panels with "
            "stable reimbursement, adds a transplant monitoring cfDNA "
            "panel under MolDx coverage, and positions for a strategic "
            "national-lab exit as PAMA data-reporting visibility improves."
        ),
    },
    {
        "company_name": "Evergreen Molecular Labs",
        "sector": "Molecular Diagnostics",
        "buyer": "Frazier Healthcare Partners",
        "year": 2023,
        "region": "West",
        "ev_mm": 345.0,
        "ev_ebitda": 16.5,
        "ebitda_mm": 20.91,
        "ebitda_margin": 0.25,
        "revenue_mm": 83.64,
        "hold_years": 2.5,
        "moic": 1.4,
        "irr": 0.1479,
        "status": "Active",
        "payer_mix": {"commercial": 0.64, "medicare": 0.22, "medicaid": 0.08, "self_pay": 0.06},
        "comm_pct": 0.64,
        "deal_narrative": (
            "West Coast molecular diagnostics lab focused on hereditary "
            "cancer panels (CPT 81432, 81433), non-invasive prenatal "
            "testing (NIPT), and reproductive-health carrier screening. "
            "Early hold focuses on FDA LDT rule compliance planning as "
            "Stage 1 premarket review phases in on high-volume hereditary-"
            "cancer panels, MolDx LCD coverage expansion across MAC "
            "jurisdictions, negotiating commercial payer medical-policy "
            "coverage on expanded carrier screens, and preparing CPT 81479 "
            "unlisted-code claims strategy for novel assay reimbursement."
        ),
    },
    {
        "company_name": "Foxhollow Hematopathology",
        "sector": "Anatomic Pathology",
        "buyer": "Riverside Company",
        "year": 2019,
        "region": "Mid-Atlantic",
        "ev_mm": 175.0,
        "ev_ebitda": 12.0,
        "ebitda_mm": 14.00,
        "ebitda_margin": 0.22,
        "revenue_mm": 63.64,
        "hold_years": 5.5,
        "moic": 2.6,
        "irr": 0.1881,
        "status": "Realized",
        "payer_mix": {"commercial": 0.54, "medicare": 0.30, "medicaid": 0.10, "self_pay": 0.06},
        "comm_pct": 0.54,
        "deal_narrative": (
            "Mid-Atlantic hematopathology specialist delivering bone-"
            "marrow biopsy reads (CPT 88305, 88307), flow cytometry "
            "(88184-88189), and FISH (88367-88368) for lymphoma / "
            "leukemia workups serving community oncology and academic "
            "medical center clients. Long hold captured hematopathologist-"
            "shortage subspecialty wage arbitrage, added a molecular "
            "hematologic malignancy NGS panel under MolDx LCD coverage, "
            "navigated CMS flow-cytometry stacking policy, and exited "
            "to a strategic specialty pathology roll-up at a 2.6x MOIC."
        ),
    },
    {
        "company_name": "Kingsbridge Clinical Diagnostics",
        "sector": "Clinical Laboratory",
        "buyer": "Altaris Capital Partners",
        "year": 2021,
        "region": "Northeast",
        "ev_mm": 265.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 21.20,
        "ebitda_margin": 0.20,
        "revenue_mm": 106.00,
        "hold_years": 3.5,
        "moic": 1.7,
        "irr": 0.1620,
        "status": "Active",
        "payer_mix": {"commercial": 0.51, "medicare": 0.31, "medicaid": 0.11, "self_pay": 0.07},
        "comm_pct": 0.51,
        "deal_narrative": (
            "Northeast clinical laboratory serving primary-care and "
            "specialty physician clients with routine chemistry, "
            "hematology, thyroid panels, and vitamin D (CPT 82306). "
            "Value creation navigates ongoing PAMA CLFS rate cycles on "
            "high-volume CPT 80053 CMP and 85025 CBC lines, executes "
            "specimen-volume consolidation across 85 draw stations into "
            "a single hub-and-spoke model, adds molecular respiratory "
            "pathogen PCR menu capturing CPT 87636 reimbursement, and "
            "remediates the 14-day rule hospital-outreach billing risk."
        ),
    },
    {
        "company_name": "Northgate Reference Diagnostics",
        "sector": "Reference Lab",
        "buyer": "TPG",
        "year": 2024,
        "region": "National",
        "ev_mm": 845.0,
        "ev_ebitda": 18.0,
        "ebitda_mm": 46.94,
        "ebitda_margin": 0.28,
        "revenue_mm": 167.66,
        "hold_years": 2.5,
        "moic": 1.4,
        "irr": 0.1479,
        "status": "Active",
        "payer_mix": {"commercial": 0.59, "medicare": 0.26, "medicaid": 0.09, "self_pay": 0.06},
        "comm_pct": 0.59,
        "deal_narrative": (
            "National reference lab platform delivering specialty "
            "esoteric, molecular, and transplant-monitoring send-out "
            "testing to hospital outreach programs. Recent acquisition "
            "at the top of the reference-lab multiple cycle. Early hold "
            "focuses on FDA LDT rule Stage 1-4 phased compliance program "
            "across 200+ LDT assays, absorbing the next PAMA CLFS reset "
            "through esoteric mix shift, pursuing ADLT designation on "
            "three proprietary molecular panels, navigating MolDx LCD "
            "coverage across all MAC jurisdictions, and capturing IDN "
            "hospital-outreach-lab outsourcing demand as health systems "
            "exit sub-scale reference-send-out operations."
        ),
    },
]
