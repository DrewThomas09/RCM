"""Genetic Testing — molecular & genomic diagnostics (germline, prenatal, somatic).

Deals-only deep-dive (no public genomic-lab census is vendored — CLIA
certificates and molecular-lab registries are not in our files — so geography
is omitted rather than fabricated and the SOURCED layer is the sector's deal
history). The qualitative sections are authored around the thing that actually
decides these deals: reimbursement is a *coverage* story, not a science story.
Molecular tests are largely lab-developed tests run under CLIA, priced on the
CLFS via gapfill/crosswalk, gated by MolDX coverage and Z-codes and payer
prior-auth — so cash lags volume, gross-to-net dominates, and genetic-testing
fraud enforcement (EKRA/AKS, the DOJ "CGx" takedowns) can zero a revenue line.
Consumes ``genetic_testing_deep_dive()`` for SOURCED corpus deal figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="genetic_testing",
    name="Genetic Testing",
    care_setting="Dx & labs",
    naics="621511",
    one_line_def=(
        "Molecular and genomic diagnostic testing — hereditary/germline (cancer "
        "risk, carrier screening), reproductive (NIPT/cfDNA), somatic/tumor "
        "profiling (NGS panels, liquid biopsy, minimal-residual-disease), "
        "pharmacogenomics, and rare-disease exome/genome sequencing. Most are "
        "lab-developed tests run under CLIA and priced under the Clinical "
        "Laboratory Fee Schedule via gapfill/crosswalk, with MolDX coverage, a "
        "registered Z-code, and payer prior-auth gating whether they pay at all."),
    tam_headline=TamHeadline(
        value=18.0, unit="$B", growth_pct=11.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "US clinical genetic/genomic testing is commercial- and "
            "sponsor-heavy and not a single published figure; ~$18B is the "
            "modeled composite of germline, reproductive, oncology somatic, "
            "pharmacogenomics, and rare-disease segments. The GOV anchor is the "
            "Medicare molecular slice paid through CLFS gapfill/crosswalk "
            "(directional). Growth is the modeled composite of oncology and "
            "NIPT adoption, net of coverage lag and PAMA/CLFS rate erosion."),
    ),
    executive_summary=[
        "Genetic testing is several different businesses with different "
        "economics, competition, and enforcement exposure: hereditary/germline "
        "(cancer risk, carrier), reproductive (NIPT/cfDNA), oncology somatic "
        "profiling (NGS, liquid biopsy, MRD), pharmacogenomics, and rare-disease "
        "exome/genome. Which one you are buying is the whole diligence.",
        "Reimbursement is a coverage story, not a science story. A clinically "
        "validated assay can lack a priced CPT/PLA code and MolDX/commercial "
        "coverage for years — cash lags volume, DSO runs long, prior-auth and "
        "retroactive denials are structural. Gross-to-net and DSO ARE the deal.",
        "Almost all of these are lab-developed tests run on CLIA alone. The 2024 "
        "FDA rule to regulate LDTs as devices was vacated by a federal court in "
        "2025 and is on appeal — an existential overhang left in limbo. "
        "Underwrite both worlds.",
        "Genetic testing is a fraud-enforcement magnet. DOJ/OIG cancer-genomic "
        "(CGx) telemarketing and specimen-referral schemes drove large "
        "takedowns; EKRA reaches even commercial referrals. A margin line built "
        "on a slick referral funnel is a settlement waiting to happen.",
        "The market is barbelled: a few scaled public platforms (Natera, "
        "Guardant, Exact, Myriad, Tempus) with sales, medical-affairs, and "
        "payer-dossier muscle, plus a long fragmented tail of hospital and "
        "regional molecular labs. PE plays the specialty/regional tail.",
        "Invitae — the hereditary-testing volume leader — went bankrupt in 2024. "
        "The lesson the whole sector absorbed: coverage and unit economics, not "
        "menu breadth, decide survival. Scale without gross-to-net is fatal.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Physician / genetic counselor / telehealth orders a test with "
            "medical necessity (family history, tumor type, indication)",
            "Sample collected — blood, buccal swab, saliva, or tumor FFPE block / "
            "liquid-biopsy tube",
            "Accessioning + nucleic-acid extraction and library preparation",
            "Sequencing / genotyping on the platform (NGS, Sanger, ddPCR, array, "
            "MLPA)",
            "Bioinformatics pipeline — alignment, variant calling, annotation",
            "Variant interpretation & ACMG classification + clinical report "
            "sign-out (lab director / MD / PhD)",
            "Result to the ordering clinician; genetic counseling where indicated",
            "Claim under CLFS (gapfill/crosswalk) with MolDX Z-code / prior-auth; "
            "patient-responsibility billing and appeals",
        ],
        sites_of_care=[
            "Centralized high-complexity molecular reference lab (the core asset)",
            "Hospital / academic molecular pathology lab",
            "Specialty oncology genomics lab (tumor profiling + liquid biopsy)",
            "Reproductive genetics lab (NIPT + expanded carrier)",
            "Direct-to-consumer / consumer-initiated genomics (a separate model)",
        ],
        money_flow=(
            "A genetic test is generally a lab-developed test priced under the "
            "Clinical Laboratory Fee Schedule via GAPFILL (contractor-set) or "
            "CROSSWALK (to an existing code) for its CPT or Proprietary "
            "Laboratory Analysis (PLA) code. For most molecular assays, Medicare "
            "payment gates on MolDX coverage (a Palmetto GBA-run framework), a "
            "registered Z-code that identifies the specific test, and often "
            "prior authorization — so an assay can be clinically ordered long "
            "before it earns a covered, priced code. Commercial payers apply "
            "their own coverage and medical-necessity rules (for example, "
            "average-risk versus high-risk NIPT, NCCN criteria for hereditary "
            "panels), frequently through a genetic-test prior-auth vendor. The "
            "lab bills the payer and, increasingly, the patient — high-deductible "
            "balances are large, and many labs cap patient out-of-pocket to "
            "preserve order flow. The engine is billable volume times realized "
            "rate per test, net of denials and bad debt, against a high-fixed-"
            "cost sequencing, bioinformatics, and medical-affairs base."),
        key_players=(
            "A handful of scaled, mostly public specialty platforms dominate the "
            "visible menu: Natera (reproductive plus oncology MRD/Signatera), "
            "Guardant Health (liquid biopsy), Exact Sciences (Cologuard plus "
            "Genomic Health's Oncotype), Myriad Genetics (hereditary cancer, "
            "prenatal, PGx), Tempus (oncology data + testing), and Fulgent, with "
            "Labcorp and Quest running broad menus and buying assets (Labcorp "
            "acquired Invitae assets). Illumina and Thermo Fisher supply the "
            "sequencing platforms and sit adjacent to the economics. The "
            "acquirable PE pool is the regional molecular/oncology-lab tail and "
            "niche-menu tuck-ins."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("US genetic/genomic testing (modeled composite)",
                    "~$18B (directional)",
                    "ILLUSTRATIVE · modeled segment composite"),
            Segment("Oncology somatic profiling + liquid biopsy + MRD",
                    "fastest-growing, highest-value",
                    "ILLUSTRATIVE · modeled segment growth"),
            Segment("Reproductive — NIPT/cfDNA + expanded carrier",
                    "large, coverage-expanding",
                    "ILLUSTRATIVE · modeled segment"),
            Segment("Hereditary/germline cancer + cardio panels",
                    "mature, price-competitive",
                    "ILLUSTRATIVE · modeled segment"),
            Segment("Medicare molecular (CLFS gapfill/crosswalk)",
                    "the Part B / CLFS slice (directional)",
                    "GOV · CMS CLFS molecular pricing (mechanic, directional)"),
        ],
        growth_drivers=[
            "Oncology precision medicine — genomic profiling, liquid biopsy, MRD",
            "NIPT toward standard prenatal care + expanded carrier screening",
            "Guideline-driven hereditary testing (NCCN) + cascade family testing",
            "Falling sequencing cost widens the profitably-offerable menu",
            "Pharmacogenomics + whole-exome/genome for rare disease",
            "Coverage lag, PAMA/CLFS gapfill pricing, and fraud enforcement drag",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial": 0.50,
            "Medicare / MA": 0.30,
            "Medicaid / self-pay / other": 0.20,
        },
        rate_mechanics=[
            "Molecular tests priced under CLFS via GAPFILL (contractor-set) or "
            "CROSSWALK (to existing codes); PLA codes for branded proprietary "
            "assays.",
            "MolDX (Palmetto GBA) coverage + Z-code registration gate Medicare "
            "payment for most molecular assays across the MolDX MAC "
            "jurisdictions.",
            "Prior authorization and medical-necessity policies (payer-specific) "
            "— average-risk vs high-risk NIPT, NCCN hereditary-panel criteria, "
            "and unit-of-service edits.",
            "ADLT (Advanced Diagnostic Laboratory Test) status — a single-lab "
            "test can earn its own PAMA pricing pathway (initial list charge, "
            "then market rate).",
            "14-day / date-of-service rule — governs whether the lab or the "
            "hospital bills for molecular tests ordered after discharge.",
            "Patient responsibility + patient-assistance / cash programs — "
            "high-deductible balances, with out-of-pocket caps used to preserve "
            "order flow.",
            "Commercial contracting / in-network status and lab-benefit-manager "
            "prior-auth vendors shape the realized rate.",
        ],
        reimbursement_risk=(
            "The dominant risk is coverage and coding lag: a clinically adopted "
            "assay may lack a priced CPT/PLA code or MolDX/commercial coverage "
            "for years, so revenue trails volume, DSO runs long, and "
            "denials/appeals are structural — retroactive coverage changes can "
            "claw back recognized revenue. Prior-auth and medical-necessity "
            "edits cap covered volume, and PAMA/CLFS gapfill pricing can reset "
            "molecular rates downward. Genetic testing also carries acute "
            "enforcement risk — cancer-genomic (CGx) telemarketing schemes and "
            "specimen/referral arrangements under EKRA and the Anti-Kickback "
            "Statute — that can zero a revenue line and drive settlements. The "
            "FDA lab-developed-test rule (2024, vacated 2025, on appeal) adds "
            "market-access and compliance-cost uncertainty to the CLIA-only "
            "model the whole sector was built on."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Clinical Laboratory Improvement Amendments (CLIA, 42 CFR 493)",
                 "The high-complexity molecular certification regime every "
                 "genetic-testing lab operates under — personnel, quality, and "
                 "proficiency standards gate what a lab may run.",
                 "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-493"),
            Rule("MolDX program (Palmetto GBA) — molecular coverage & Z-codes",
                 "The contractor framework that determines coverage, coding "
                 "(Z-codes), and gapfill pricing for molecular diagnostics "
                 "across most of the country — the gate to Medicare payment.",
                 "https://www.palmettogba.com/moldx"),
            Rule("FDA final rule on laboratory-developed tests (2024)",
                 "Phased out FDA enforcement discretion and regulated LDTs as "
                 "devices — an existential shift for the CLIA-only genomic model; "
                 "vacated by a federal court (E.D. Tex.) in 2025 and on appeal, "
                 "leaving status in flux.",
                 "https://www.fda.gov/medical-devices/in-vitro-diagnostics/laboratory-developed-tests"),
            Rule("EKRA (18 USC 220) + Anti-Kickback Statute",
                 "The all-payer and Medicare anti-kickback statutes reaching "
                 "genetic-testing referral, specimen, and marketing arrangements "
                 "— the basis of the DOJ 'CGx' cancer-genomic takedowns.",
                 "https://www.justice.gov/"),
            Rule("Genetic Information Nondiscrimination Act (GINA)",
                 "Bars health-insurance and employment genetic discrimination "
                 "(not life/disability); shapes consumer trust and data "
                 "handling for germline and consumer testing.",
                 "https://www.eeoc.gov/genetic-information-discrimination"),
            Rule("PAMA / CLFS + PLA molecular coding (AMA CPT)",
                 "The pricing pipeline for molecular codes — market-based CLFS "
                 "resets and the PLA coding pathway for branded assays.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/clinical-laboratory-fee-schedule"),
        ],
        policy_watch=[
            "FDA LDT rule appeal outcome and any VALID Act legislative revival",
            "MolDX coverage & gapfill decisions on new oncology and MRD assays",
            "DOJ/OIG genetic-testing (CGx) and telehealth-referral enforcement",
            "Commercial payer expansion of average-risk NIPT coverage",
            "PAMA/CLFS reform (SALSA) affecting molecular gapfill pricing",
            "Medicare coverage of multi-cancer early detection (MCED)",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Barbelled. A cohort of scaled public specialty platforms (Natera, "
            "Guardant, Exact/Genomic Health, Myriad, Tempus, Fulgent) with the "
            "sales forces, medical-affairs teams, and payer dossiers to win "
            "coverage, plus Labcorp and Quest with broad menus and acquisition "
            "firepower — against a long fragmented tail of hospital, academic, "
            "and regional molecular labs. No public genomic-lab facility census "
            "is vendored (CLIA certificates are not in our files), so a "
            "facility-count HHI is honestly omitted; the acquirable PE pool sits "
            "in the regional/specialty tail and niche-menu tuck-ins."),
        hhi_or_share=(
            "Concentration is best read by test category, not in aggregate: NIPT "
            "and hereditary cancer are led by a few players (Natera, Myriad, "
            "Labcorp incl. prior Invitae assets); liquid biopsy skews to Guardant "
            "and Foundation/Roche; MRD is an emerging race (Natera Signatera, "
            "Guardant Reveal, others). No single owner dominates the whole "
            "market."),
        consolidation=(
            "A volatile roll-up and shakeout. The 2010s saw aggressive VC/PE-"
            "funded scaling and menu land-grabs; the 2020s brought a reckoning — "
            "Invitae (hereditary volume leader) filed Chapter 11 in 2024 and "
            "sold assets to Labcorp, and several DTC and startup genomics names "
            "retrenched. Strategics (Labcorp, Quest, Roche, Thermo) buy menu, "
            "coverage, and volume, while public platforms consolidate "
            "adjacencies. The lesson: coverage and unit economics, not menu "
            "breadth, decide survival."),
        pe_activity=(
            "PE concentrates on the specialty/regional tail — oncology "
            "molecular, reproductive, and niche hereditary/PGx labs — where "
            "coverage, menu, and scale can be built, rather than competing with "
            "the scaled public platforms or the routine duopoly. "
            "Quality-of-earnings centers on payer coverage and coding durability "
            "(CPT/PLA, MolDX, prior-auth), realized rate net of denials and "
            "patient bad debt, revenue-recognition and DSO, sales-force "
            "productivity, and EKRA/AKS compliance on every referral and "
            "marketing arrangement."),
        notable_players=[
            "Natera", "Guardant Health", "Exact Sciences (Genomic Health)",
            "Myriad Genetics", "Tempus", "Labcorp (incl. Invitae assets)",
            "Quest Diagnostics", "Fulgent Genetics",
            "Foundation Medicine (Roche)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Revenue / test (realized, blended)",
                "$300-3,000+ (assay-dependent)",
                "NIPT and hereditary panels lower; comprehensive oncology NGS "
                "and exome higher — realized well below gross list after "
                "denials."),
            Kpi("Gross-to-net / collection rate", "often ~40-70% of billed",
                "Denials, prior-auth, and patient bad debt separate billed from "
                "collected — the number that actually matters."),
            Kpi("Coverage status of top assays", "covered vs non-covered mix",
                "The single biggest revenue-quality determinant — MolDX and "
                "commercial policy coverage on the material tests."),
            Kpi("COGS / test (sequencing + reagents)", "falling with platform cost",
                "Illumina/competition drive per-test sequencing cost down; "
                "bioinformatics and interpretation labor persist."),
            Kpi("DSO / cash-collection cycle", "long (60-120+ days)",
                "Appeals and prior-auth stretch collections — a working-capital "
                "and revenue-recognition risk."),
            Kpi("EBITDA margin", "wide range; scale + coverage dependent",
                "Negative sub-scale or pre-coverage; strongly positive for "
                "covered, high-volume assays at scale."),
        ],
        margin_profile=(
            "Genetic-testing economics hinge on two variables that dwarf "
            "everything else: whether the top assays are covered, and the "
            "gross-to-net that turns billed revenue into cash. COGS per test "
            "keeps falling as sequencing platforms cheapen, so a covered, "
            "high-volume assay at scale is highly profitable — but sales, "
            "medical-affairs, market-access, and bioinformatics are heavy fixed "
            "costs, and an uncovered or newly-launched assay can be deeply "
            "cash-negative while it builds a reimbursement dossier. The gap "
            "between list price, allowed amount, denials, and patient bad debt "
            "means realized revenue can be a fraction of billed, so gross-to-net, "
            "DSO, and coverage mix are the margin story, not menu breadth. "
            "Invitae's collapse showed that scale without unit economics is a "
            "liability, not a moat."),
    ),
    risks=[
        Risk("Coverage & coding lag / denials", "High",
             "Assays outrun the payment system; revenue trails volume, DSO is "
             "long, and retroactive denials can claw back recognized revenue."),
        Risk("Genetic-testing fraud enforcement (EKRA/AKS/CGx)", "High",
             "DOJ/OIG cancer-genomic telemarketing and specimen-referral schemes "
             "— a margin line can become a settlement."),
        Risk("Gross-to-net / patient bad debt", "High",
             "Realized rate is a fraction of billed after denials and "
             "high-deductible patient balances — the crux of revenue quality."),
        Risk("FDA lab-developed-test regulation uncertainty", "Medium",
             "The 2024 rule was vacated in 2025 and is on appeal; device-grade "
             "compliance cost and market-access overhang sit on the CLIA-only "
             "model."),
        Risk("Payer prior-auth & medical-necessity limits", "Medium",
             "Average-risk NIPT, hereditary-panel criteria, and prior-auth "
             "vendors cap covered volume."),
        Risk("Platform commoditization + price competition", "Medium",
             "Falling sequencing cost and crowded NIPT/hereditary menus compress "
             "price."),
    ],
    diligence_questions=[
        "What is the assay-level revenue and volume mix, and what share of "
        "revenue is in covered vs non-covered tests?",
        "What is gross-to-net by top assay — billed vs allowed vs collected — "
        "and the denial/appeal and patient-bad-debt history?",
        "What is the MolDX/commercial coverage and coding status (CPT/PLA, "
        "Z-code, prior-auth) for each material test, and the pending-coverage "
        "pipeline?",
        "What is revenue-recognition policy and DSO, and how much recognized "
        "revenue is at risk of retroactive denial?",
        "What is the EKRA/AKS compliance posture on referrals, specimen "
        "collection, telehealth ordering, and sales/marketing compensation?",
        "What is FDA LDT exposure and the validation/compliance plan under each "
        "rule scenario?",
        "What is the CLIA/CAP certificate posture and any proficiency-testing or "
        "accreditation deficiency history?",
        "What is sales-force productivity (tests per rep) and the CAC vs "
        "contribution per covered test?",
    ],
    insider_lens=[
        "Revenue quality is a gross-to-net story. A genetic-testing P&L can show "
        "big 'billed' revenue that collects at 40-60 cents on the dollar after "
        "denials, prior-auth, and patient balances. Underwrite collected revenue "
        "and DSO, not the requisition count.",
        "Coverage is the asset, not the science. A brilliant assay with strong "
        "clinical volume can be cash-flow negative for years without a priced "
        "code and MolDX/commercial coverage — the value is in the reimbursement "
        "dossier and the payer-policy wins, not the menu slide.",
        "Genetic testing is an enforcement magnet with a specific playbook: "
        "telemarketed cancer-genomic (CGx) tests, 'free' swabs, doctor-signature "
        "mills, and specimen/marketing fees. EKRA reaches even commercial "
        "referrals. A revenue line built on a slick referral funnel is a "
        "settlement waiting to happen.",
        "Invitae is the cautionary tale. It led hereditary-testing volume and "
        "still went bankrupt because it priced for share while collecting below "
        "cost — proof that in this business scale without unit economics is "
        "fatal.",
        "The FDA LDT whiplash matters. The industry ran for decades on "
        "CLIA-only LDTs; the 2024 device rule threatened that, then a court "
        "vacated it in 2025. Underwrite both worlds — a covered, compliant lab "
        "gains if enforcement returns; a compliance-light lab is exposed either "
        "way.",
        "NIPT and hereditary are price wars; oncology MRD and comprehensive "
        "profiling are where value and coverage momentum sit. Where a lab lands "
        "on that spectrum predicts its pricing power and growth.",
    ],
    connections=default_connections(
        "genetic_testing",
        deals_sector="genetic_testing",
        extra_pages=[
            ("/industry/genetic_testing",
             "Industry deep-dive — genetic-testing deal history + structure"),
        ],
        connectors=[
            ("cms_open_data_pos_clinical_labs",
             "CMS Provider of Services — clinical laboratories (CLIA-enrolled "
             "molecular labs)"),
            ("cms_open_data_lab_fee_private_payer_rates",
             "CMS PAMA private-payer lab rate reporting — the CLFS molecular "
             "gapfill input"),
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare utilization by HCPCS — molecular/genomic test volume & "
             "allowed amounts"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — molecular pathology / clinical-lab / "
             "genetic-counselor enrollment"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded entities (genetic-testing / CGx integrity "
             "screen)"),
            ("open_payments",
             "CMS Open Payments — industry payments to ordering physicians "
             "(referral-integrity signal)"),
        ],
    ),
    sources=[
        Source("CMS — Clinical Laboratory Fee Schedule & molecular "
               "gapfill/crosswalk pricing", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/clinical-laboratory-fee-schedule"),
        Source("Palmetto GBA MolDX — molecular diagnostics coverage, Z-codes & "
               "gapfill", "GOV", "https://www.palmettogba.com/moldx"),
        Source("CLIA regulations (42 CFR 493)", "GOV",
               "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-493"),
        Source("FDA — laboratory-developed tests final rule (2024) & litigation",
               "GOV",
               "https://www.fda.gov/medical-devices/in-vitro-diagnostics/laboratory-developed-tests"),
        Source("HHS OIG / DOJ — genetic-testing (CGx) fraud enforcement "
               "(EKRA / AKS)", "GOV",
               "https://oig.hhs.gov/reports-and-publications/all-reports-and-publications/"),
        Source("Association for Molecular Pathology (AMP) — molecular "
               "diagnostics coding & policy", "INDUSTRY",
               "https://www.amp.org/"),
        Source("PE Desk industry deep-dive (genetic testing) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=genetic_testing"),
    ],
    live_figures=live_figures_from_dive("genetic_testing"),
    trends=(
        "Genetic testing went from a niche add-on to a central pillar of "
        "precision medicine over the last decade — oncology genomic profiling "
        "and liquid biopsy, NIPT becoming near-standard prenatal care, expanded "
        "carrier screening, guideline-driven hereditary panels, and emerging MRD "
        "monitoring and multi-cancer early detection. Sequencing cost collapsed "
        "as Illumina and competitors pushed the addressable menu wider each "
        "year. But the payment system never kept pace: molecular codes and "
        "coverage (CPT/PLA, MolDX gapfill/crosswalk, commercial prior-auth) lag "
        "clinical adoption, so cash trails volume and denials are structural. "
        "The 2010s land-grab — VC/PE-funded platforms pricing for share — gave "
        "way to a 2020s shakeout, epitomized by Invitae's 2024 bankruptcy "
        "despite category-leading volume: proof that coverage and gross-to-net, "
        "not menu breadth, decide survival. Enforcement tightened around "
        "cancer-genomic (CGx) telemarketing and specimen-referral schemes "
        "(EKRA/AKS, DOJ takedowns), and the 2024 FDA rule to regulate LDTs as "
        "devices — vacated by a federal court in 2025 and on appeal — hangs over "
        "the CLIA-only model the whole industry was built on. The forward story "
        "is durable clinical demand (oncology, reproductive, hereditary, MRD, "
        "MCED) throttled by coverage lag, gapfill pricing, patient bad debt, and "
        "compliance cost."),
    growth_levers=[
        GrowthLever(
            "Oncology precision testing (CGP, liquid biopsy, MRD)",
            "Comprehensive genomic profiling, liquid biopsy, and recurring "
            "minimal-residual-disease monitoring are the fastest-growing, "
            "highest-value category; monitoring creates repeat volume.",
            "+ segment growth", "ILLUSTRATIVE"),
        GrowthLever(
            "NIPT + expanded carrier screening adoption",
            "NIPT moving toward standard prenatal care and average-risk coverage "
            "expansion widen covered reproductive volume.",
            "+ covered volume", "ILLUSTRATIVE"),
        GrowthLever(
            "Guideline-driven hereditary testing + cascade",
            "NCCN criteria and family cascade testing widen eligible germline "
            "volume off a maturing base.",
            "+ volume", "ILLUSTRATIVE"),
        GrowthLever(
            "Falling sequencing cost",
            "Platform-cost declines widen the profitably-offerable menu and lift "
            "margin on covered assays.",
            "+ margin / menu", "ILLUSTRATIVE"),
        GrowthLever(
            "Coverage lag + gapfill + enforcement drag",
            "MolDX/commercial coverage lag, PAMA/CLFS gapfill pricing, and "
            "EKRA/AKS enforcement subtract from realized revenue.",
            "coverage & rate risk", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Guideline-covered ordered volume × the oncology/reproductive "
               "mix shift",
        analysis=(
            "Demand is the number of ordered tests that actually convert to "
            "covered, collectible volume — and it is expanding fastest in "
            "oncology (comprehensive genomic profiling, liquid biopsy, and "
            "recurring MRD monitoring) and reproductive genetics (NIPT toward "
            "standard-of-care, expanded carrier screening), with guideline-driven "
            "hereditary panels adding germline volume and cascade family testing. "
            "Falling sequencing cost widens the menu a lab can offer profitably. "
            "But unlike a physician-demand business, the binding constraint is "
            "the payer, not the clinician: a test only becomes revenue once it "
            "earns a priced code and coverage (CPT/PLA, MolDX, commercial "
            "policy) and clears prior-auth — so ordered volume and collected "
            "revenue decouple, and the growth that matters is covered, "
            "collectible volume net of denials and patient bad debt."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Sequencing, reagents & consumables", "~20-35% of cost",
            "NGS flow cells, library-prep kits, genotyping/PCR reagents, and "
            "instrument depreciation — falling with platform cost and volume.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Labor — techs, bioinformaticians, variant scientists, MD/PhD "
            "directors", "~25-35% of cost",
            "High-complexity molecular staffing plus bioinformatics and ACMG "
            "variant interpretation and clinical sign-out.", "ILLUSTRATIVE"),
        CostDriver(
            "Sales, marketing & medical affairs", "~15-25% of cost",
            "Specialty sales force, KOL/medical-affairs, and payer "
            "market-access teams — the coverage-winning engine.", "ILLUSTRATIVE"),
        CostDriver(
            "Billing, prior-auth, denials & patient bad debt", "~10-20% of net",
            "Molecular billing, prior-auth work, appeals, and uncollected "
            "patient balances — the gross-to-net drag.", "ILLUSTRATIVE"),
        CostDriver(
            "R&D, validation & compliance (CLIA/CAP/FDA LDT)", "~8-15% of cost",
            "Assay development and validation, proficiency testing, "
            "accreditation, and the emerging FDA LDT compliance burden.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No public genomic-lab facility census is vendored (CLIA certificates "
        "and molecular-lab registries are not in our files), so state geography "
        "is omitted rather than fabricated. Qualitatively, high-complexity "
        "molecular testing is highly centralized — a handful of reference labs "
        "serve the country via overnight logistics — so geography matters far "
        "less than payer contracts and MolDX MAC jurisdiction; specialty and "
        "academic molecular labs cluster near oncology and research centers (the "
        "Bay Area, Boston, Research Triangle Park, San Diego, Houston). The CMS "
        "Provider of Services clinical-labs and NPI-taxonomy connectors linked "
        "below give a real CLIA-enrolled facility read."),
)

register(REPORT)
