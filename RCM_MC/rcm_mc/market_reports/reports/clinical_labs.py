"""Clinical Labs — independent clinical laboratories & anatomic pathology.

Deals-only deep-dive (no public independent-lab census is vendored — CLIA
certificates are not in our files — so geography is omitted rather than
fabricated and the SOURCED layer is the sector's lab deal history). The
qualitative sections are authored around the two payment regimes that govern
this subsector — the Clinical Laboratory Fee Schedule (CLFS) reset by PAMA
market-based pricing for clinical tests, and the MPFS technical/professional
split for anatomic pathology — plus the routine/esoteric divide, the Quest/
Labcorp network duopoly, and the FDA lab-developed-test rule. Consumes
``clinical_labs_deep_dive()`` for SOURCED corpus deal figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="clinical_labs",
    name="Clinical Labs",
    care_setting="Dx & labs",
    naics="621511",
    one_line_def=(
        "CLIA-certified clinical laboratories that run the blood, urine, "
        "tissue, and molecular tests physicians order — routine/reference "
        "chemistry and hematology, anatomic pathology, esoteric and molecular/"
        "genomic assays, microbiology, and toxicology. Clinical tests are paid "
        "under the Clinical Laboratory Fee Schedule (CLFS); anatomic pathology "
        "is paid under the Physician Fee Schedule with a technical/professional "
        "split."),
    tam_headline=TamHeadline(
        value=85.0, unit="$B", growth_pct=4.5, basis_label="ILLUSTRATIVE",
        basis_note=(
            "US all-payer clinical-laboratory and pathology services revenue is "
            "commercial- and hospital-heavy and not a single published figure; "
            "~$85B is the modeled composite. The GOV anchor is Medicare CLFS "
            "spend (~$8-9B, CMS PAMA reporting, directional) in the segments "
            "below. Growth is the modeled composite of test-volume growth and "
            "molecular mix shift, net of PAMA rate cuts."),
    ),
    executive_summary=[
        "There are two very different lab businesses. Routine/reference testing "
        "is a scale-and-automation volume game (thin margin per test, enormous "
        "throughput) dominated by Quest and Labcorp; esoteric, molecular, and "
        "anatomic-pathology testing is a higher-margin, reimbursement-risky "
        "specialty game. Which one you are buying determines the entire "
        "diligence.",
        "PAMA is the governing rate mechanic and the standing threat. The "
        "Clinical Laboratory Fee Schedule is reset by private-payer rates that "
        "'applicable labs' report to CMS; that market-based reform cut routine "
        "test prices materially, and further scheduled cuts have been "
        "repeatedly delayed — deferred, not cancelled (SALSA reform is the "
        "watch).",
        "Anatomic pathology behaves like imaging, not like routine labs: the "
        "study splits into a technical component (slide prep) and a "
        "professional component (the pathologist's read, -26), paid under MPFS "
        "— and in-office/self-referred pathology sits under Stark and the "
        "anti-markup rule.",
        "Network access is the moat. Quest and Labcorp hold exclusive or "
        "preferred national commercial contracts, so an independent lab's "
        "realized rate turns on whether it is in-network — out-of-network lab "
        "billing has been squeezed hard by payers.",
        "Molecular/genomics is where growth AND reimbursement risk both live: a "
        "test can be clinically adopted years before it earns a CPT/PLA code "
        "and MolDX coverage, so cash lags volume, and the 2024 FDA rule to "
        "regulate lab-developed tests as devices threatens the CLIA-only "
        "esoteric model.",
        "Toxicology and genetic testing are fraud-enforcement magnets. EKRA and "
        "the Anti-Kickback Statute police lab referral arrangements; "
        "definitive-vs-presumptive tox billing and specimen/kickback schemes "
        "have repriced whole segments.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Physician orders a test panel (with a diagnosis / medical necessity)",
            "Specimen collected (patient service center, draw station, in-office)",
            "Logistics — courier / cold-chain transport to the lab (accessioning)",
            "Analysis on automated lines or esoteric/molecular platforms (TC)",
            "Pathologist / director interpretation & sign-out where applicable (PC)",
            "Result reported to the ordering physician / EHR interface",
            "Claim to payer under CLFS (clinical) or MPFS (pathology); "
            "patient-responsibility billing",
            "Coverage/coding maintenance (MolDX, gapfill/crosswalk, Z-codes) for "
            "new assays",
        ],
        sites_of_care=[
            "National reference lab (high-automation core lab)",
            "Regional independent / specialty lab (esoteric, molecular, tox)",
            "Hospital laboratory + hospital outreach (outpatient) business",
            "Anatomic pathology lab (histology + pathologist read)",
            "Patient service centers / phlebotomy draw stations",
            "Point-of-care / physician-office lab (CLIA-waived or PPM)",
        ],
        money_flow=(
            "Clinical tests (chemistry, hematology, microbiology, molecular) are "
            "paid off the Clinical Laboratory Fee Schedule — a national list of "
            "per-test prices that, unlike the physician schedule, is NOT "
            "RVU-based. Under PAMA, those CLFS prices are reset to the "
            "volume-weighted median of private-payer rates that applicable labs "
            "report to CMS. Anatomic pathology is paid instead under the "
            "Physician Fee Schedule and splits into a technical component "
            "(histology/slide prep) and a professional component (the "
            "pathologist's interpretation, -26). New molecular assays are priced "
            "by CROSSWALK (to an existing code) or GAPFILL (contractor-set) and "
            "often gate on MolDX coverage before they pay at all. Commercial "
            "payers pay contracted rates that hinge on in-network status, and "
            "rising patient deductibles push a growing slice of the bill to "
            "patient responsibility — where collection is hard. The engine is "
            "volume × realized rate per accession against a high-fixed-cost "
            "automation and logistics base."),
        key_players=(
            "Routine/reference is a duopoly: Quest Diagnostics and Labcorp, each "
            "a multi-billion-dollar national network, plus large hospital "
            "outreach labs (many now sold to the duopoly). Specialty and "
            "molecular is fragmented and fast-growing: NeoGenomics (oncology), "
            "Natera, Guardant Health, Exact Sciences, and Myriad (genomics/"
            "screening), Sonic Healthcare's US anatomic-pathology roll-up, and a "
            "long tail of regional independents, toxicology, and pathology "
            "groups. Reagent/instrument vendors (Roche, Abbott, Siemens, "
            "Illumina) and MolDX contractors sit adjacent to the economics."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Medicare CLFS spend", "~$8-9B (directional)",
                    "GOV · CMS PAMA CLFS reporting (directional)"),
            Segment("Routine / reference testing", "the volume base",
                    "ILLUSTRATIVE · modeled test-mix, directional"),
            Segment("Molecular / genomic testing",
                    "fastest-growing, highest reimbursement risk",
                    "ILLUSTRATIVE · modeled segment growth"),
            Segment("Anatomic pathology (TC + PC)",
                    "MPFS-paid, imaging-like split",
                    "GOV · MPFS pathology (mechanic)"),
            Segment("Toxicology / drugs-of-abuse",
                    "enforcement-heavy niche",
                    "ILLUSTRATIVE · segment, directional"),
        ],
        growth_drivers=[
            "Aging + chronic-disease burden lifts routine test volume",
            "Molecular / genomic mix shift — higher $ per accession",
            "Oncology precision testing (NGS panels, MRD, liquid biopsy)",
            "Decentralization + direct-to-consumer and employer testing",
            "PAMA CLFS rate cuts and payer network exclusivity as the drag",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial": 0.55,
            "Medicare / MA": 0.25,
            "Medicaid / self-pay / other": 0.20,
        },
        rate_mechanics=[
            "Clinical Laboratory Fee Schedule (CLFS) — a national per-test price "
            "list for clinical tests; not RVU-based.",
            "PAMA market-based pricing — 'applicable labs' report private-payer "
            "rates and CMS resets CLFS to the volume-weighted median; the cuts "
            "phased in and have been repeatedly delayed (SALSA reform pending).",
            "Anatomic pathology under MPFS — technical component (slide prep) "
            "and professional component (pathologist read, -26), separately "
            "billable.",
            "Molecular pricing — CROSSWALK vs GAPFILL for new CPT/PLA codes, "
            "with MolDX (Palmetto) coverage and Z-code registration gating "
            "payment for many assays.",
            "Date-of-service / 14-day rule — governs whether the lab or the "
            "hospital bills for tests ordered after discharge and for Advanced "
            "Diagnostic Laboratory Tests (ADLTs).",
            "Network status & out-of-network limits — commercial realized rate "
            "depends on in-network access; payers have curtailed OON lab "
            "billing hard.",
            "Patient responsibility — high-deductible plans shift more of the "
            "bill to patients; bad debt is a material yield drag.",
        ],
        reimbursement_risk=(
            "PAMA is the central risk: because CLFS is now set from reported "
            "private-payer rates, routine test prices ratcheted down and the "
            "remaining scheduled cuts are only deferred — a structural headwind "
            "for volume-based routine labs. For molecular labs the risk inverts "
            "into coverage and coding: a clinically adopted assay may lack a "
            "priced CPT/PLA code or MolDX coverage for years, so revenue "
            "recognition lags test volume and can be denied retroactively. "
            "Network exclusivity caps independent-lab realized rates, patient "
            "bad debt erodes yield, and toxicology/genetic testing carry acute "
            "audit and EKRA/AKS enforcement exposure that can zero a revenue "
            "line. The FDA lab-developed-test rule adds a compliance-cost and "
            "market-access overhang to the esoteric model."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Clinical Laboratory Improvement Amendments (CLIA, 42 CFR 493)",
                 "The federal certification regime every lab operates under — "
                 "certificate type (waiver / PPM / compliance / accreditation) "
                 "and personnel/quality standards gate what a lab may run.",
                 "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-493"),
            Rule("PAMA — Clinical Laboratory Fee Schedule market-based pricing",
                 "Resets CLFS to reported private-payer medians; the rate reform "
                 "that cut routine test prices and remains a scheduled overhang.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/clinical-laboratory-fee-schedule/pama-regulations"),
            Rule("FDA final rule on laboratory-developed tests (2024)",
                 "Phases out FDA enforcement discretion and regulates LDTs as "
                 "medical devices — an existential shift for the CLIA-only "
                 "esoteric-lab model (subject to litigation).",
                 "https://www.fda.gov/medical-devices/in-vitro-diagnostics/laboratory-developed-tests"),
            Rule("Eliminating Kickbacks in Recovery Act (EKRA, 18 USC 220)",
                 "An all-payer anti-kickback statute reaching lab and "
                 "toxicology referral arrangements — broader than the AKS and a "
                 "live enforcement tool.",
                 "https://www.justice.gov/"),
            Rule("Stark self-referral + Medicare anti-markup rule (pathology)",
                 "Govern physician referrals to owned pathology and the price a "
                 "billing physician may charge for a purchased professional or "
                 "technical component.",
                 "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
            Rule("MolDX program (Palmetto GBA) — molecular coverage & Z-codes",
                 "The contractor framework that determines coverage, coding, and "
                 "pricing for molecular diagnostics across most of the country.",
                 "https://www.palmettogba.com/moldx"),
        ],
        policy_watch=[
            "SALSA / PAMA reform — the scope and timing of remaining CLFS cuts",
            "FDA LDT rule implementation and the pending litigation outcome",
            "EKRA / DOJ enforcement on toxicology and genetic-testing referrals",
            "Molecular coverage & gapfill pricing decisions (MolDX)",
            "Payer network exclusivity and out-of-network lab-billing limits",
            "Direct-to-consumer / employer testing regulatory treatment",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "A barbell. Routine/reference testing is highly concentrated — Quest "
            "and Labcorp form a national duopoly and have absorbed many hospital "
            "outreach books — while specialty, molecular, anatomic-pathology, "
            "and toxicology testing is fragmented across public specialty labs "
            "and a long tail of regional independents. The acquirable pool sits "
            "almost entirely in that specialty/regional tail; no public "
            "independent-lab facility census is vendored, so a facility-count "
            "HHI is honestly omitted."),
        hhi_or_share=(
            "Routine testing is a two-firm oligopoly (Quest + Labcorp) with high "
            "concentration; specialty and molecular are fragmented with several "
            "scaled public names (NeoGenomics, Natera, Guardant, Exact "
            "Sciences) but no single dominant owner. Concentration is best read "
            "by test category, not in aggregate."),
        consolidation=(
            "Two decades of roll-up. Quest and Labcorp grew by acquiring "
            "regional labs and buying hospital outreach businesses; Sonic "
            "Healthcare and others consolidated anatomic pathology; and public "
            "molecular platforms scaled through M&A and menu expansion. "
            "Hospital systems continue to divest outreach labs to the "
            "duopoly, feeding the consolidation."),
        pe_activity=(
            "PE concentrates on the specialty tail — molecular, anatomic "
            "pathology, toxicology, and clinical-trial/central labs — where "
            "menu, coverage, and scale can be built, rather than competing with "
            "the routine duopoly. Quality-of-earnings centers on PAMA/CLFS rate "
            "exposure, molecular coverage and coding durability, payer "
            "in-network access, patient bad debt, and EKRA/AKS compliance in "
            "any tox or genetic-testing line."),
        notable_players=[
            "Quest Diagnostics", "Labcorp", "Sonic Healthcare (US pathology)",
            "NeoGenomics", "Natera", "Guardant Health", "Exact Sciences",
            "Regional independent & toxicology labs",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Revenue / accession (blended)", "$10-40 routine, $300-3,000+ molecular",
                "Routine tests are cents-to-dollars per analyte at massive "
                "volume; molecular/genomic assays are high-dollar and "
                "coverage-dependent."),
            Kpi("Cost / test (routine, automated)", "low single dollars",
                "High automation and reagent scale drive routine cost down; "
                "the model is volume leverage, not price."),
            Kpi("Esoteric / molecular mix", "the margin lever",
                "Higher-value assays carry the margin; menu breadth and "
                "send-out capture drive the blend."),
            Kpi("Payer / bad-debt yield", "net of patient responsibility",
                "High-deductible plans shift cost to patients; collection rate "
                "on patient balances is a real drag on realized revenue."),
            Kpi("Turnaround time (TAT)", "hours (routine) → days (molecular)",
                "Clinical utility and physician retention hinge on TAT; it "
                "also drives logistics and staffing cost."),
            Kpi("Lab EBITDA margin", "15-20% routine at scale; variable specialty",
                "Routine is a scale business with mid-teens margins; specialty "
                "swings widely with coverage and menu."),
        ],
        margin_profile=(
            "Routine labs are automation-and-logistics scale businesses: the "
            "core-lab instruments, courier network, and IT are largely fixed, "
            "so contribution margin is about driving accession volume across a "
            "fixed automation line — mid-teens to ~20% EBITDA at national scale, "
            "far thinner sub-scale, and directly exposed to PAMA price cuts. "
            "Specialty, molecular, and anatomic-pathology labs invert the "
            "model: revenue per accession is high but reimbursement is "
            "coverage- and coding-dependent, R&D and validation are real, and "
            "sales/medical-affairs cost is heavy — margins swing from excellent "
            "to negative on whether an assay is covered and in-network. Patient "
            "bad debt and denial write-offs sit between gross and net for "
            "both."),
    ),
    risks=[
        Risk("PAMA / CLFS routine-rate cuts", "High",
             "Market-based CLFS pricing already cut routine test prices; the "
             "remaining scheduled cuts are deferred, not cancelled — a "
             "structural headwind for volume labs."),
        Risk("Molecular coverage & coding lag", "High",
             "New assays can lack a priced CPT/PLA code or MolDX coverage for "
             "years; revenue lags volume and can be denied retroactively."),
        Risk("EKRA / Anti-Kickback enforcement (tox & genetics)", "High",
             "Referral, specimen, and marketing arrangements in toxicology and "
             "genetic testing are active DOJ/OIG targets that can zero a "
             "revenue line."),
        Risk("FDA lab-developed-test regulation", "Medium",
             "The 2024 LDT rule adds device-grade compliance cost and market-"
             "access risk to the CLIA-only esoteric model (litigation pending)."),
        Risk("Payer network exclusivity", "Medium",
             "Quest/Labcorp preferred contracts and OON limits cap an "
             "independent lab's realized commercial rate."),
        Risk("Patient bad debt on high-deductible plans", "Medium",
             "A growing share of the bill is patient responsibility with low "
             "collection — a persistent yield drag."),
    ],
    diligence_questions=[
        "What is the test-mix revenue split (routine vs esoteric/molecular vs "
        "anatomic pathology vs toxicology), and where is the margin?",
        "What is CLFS/PAMA exposure by test — which top codes face scheduled "
        "cuts, and what is the modeled rate bridge?",
        "For molecular assays, what is the coverage/coding status (CPT/PLA, "
        "MolDX, Z-code) and the denial/appeal history?",
        "What is the payer mix and in-network access, and what is realized "
        "revenue per accession after denials and patient bad debt?",
        "Is there any toxicology or genetic-testing line, and what is the EKRA/"
        "AKS compliance posture on referrals and marketing?",
        "What is the CLIA certificate posture and any CAP/accreditation or "
        "proficiency-testing deficiency history?",
        "How exposed is the esoteric menu to the FDA LDT rule, and what is the "
        "validation/compliance plan?",
        "What is the automation/logistics fixed-cost base and the volume "
        "needed to cover it — how sub-scale or scaled is the lab?",
    ],
    insider_lens=[
        "PAMA quietly re-rated the whole routine business. Because CLFS is now "
        "set from private-payer rates the big labs report, the price of a basic "
        "metabolic panel fell — and because Quest and Labcorp dominate the "
        "reported data, the reform partly reflects their own rates. Model the "
        "CLFS bridge, not last year's fee schedule.",
        "In molecular labs, revenue recognition is a coverage story, not a "
        "science story. A brilliant assay with strong clinical volume can be "
        "cash-flow negative for years if it has no priced code or MolDX "
        "coverage — the value is in the reimbursement dossier, not the "
        "menu slide.",
        "Network access is worth more than list price. Quest and Labcorp's "
        "exclusive national contracts mean an independent's realized rate hinges "
        "on being in-network; a great gross fee schedule out-of-network "
        "collects cents on the dollar.",
        "Toxicology and genetic testing look like gold mines and hide "
        "landmines. Definitive-vs-presumptive tox billing, specimen "
        "arrangements, and marketing fees are EKRA/AKS enforcement staples — a "
        "line that prints margin today can be a settlement tomorrow.",
        "Anatomic pathology is really an imaging business in disguise: it splits "
        "into a technical component and a professional read, sits under MPFS and "
        "Stark, and the self-referred in-office pathology model faces the same "
        "utilization scrutiny as self-referred imaging.",
    ],
    connections=default_connections(
        "clinical_labs",
        deals_sector="clinical_labs",
        extra_pages=[
            ("/industry/clinical_labs",
             "Industry deep-dive — clinical-lab deal history + structure"),
        ],
        connectors=[
            ("cms_open_data_lab_fee_private_payer_rates",
             "CMS PAMA private-payer lab rate reporting — the CLFS rate-setting "
             "input"),
            ("cms_open_data_pos_clinical_labs",
             "CMS Provider of Services — clinical laboratories (CLIA-enrolled "
             "facilities)"),
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare utilization by HCPCS — lab test volume & allowed "
             "amounts"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — clinical-lab & pathology enrollment"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded entities (toxicology / genetic-testing "
             "integrity screen)"),
            ("census_acs_cbsa_profile",
             "Census ACS — CBSA demographics for testing-demand mapping"),
        ],
    ),
    sources=[
        Source("CMS — Clinical Laboratory Fee Schedule & PAMA private-payer "
               "rate reporting", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/clinical-laboratory-fee-schedule"),
        Source("CLIA regulations (42 CFR 493)", "GOV",
               "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-493"),
        Source("FDA — laboratory-developed tests final rule (2024)", "GOV",
               "https://www.fda.gov/medical-devices/in-vitro-diagnostics/laboratory-developed-tests"),
        Source("HHS OIG / DOJ — laboratory and toxicology fraud enforcement "
               "(EKRA / AKS)", "GOV",
               "https://oig.hhs.gov/reports-and-publications/all-reports-and-publications/"),
        Source("Palmetto GBA MolDX — molecular diagnostics coverage & coding",
               "GOV", "https://www.palmettogba.com/moldx"),
        Source("American Clinical Laboratory Association (ACLA) — industry data",
               "INDUSTRY", "https://www.acla.com/"),
        Source("PE Desk industry deep-dive (clinical labs) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=clinical_labs"),
    ],
    live_figures=live_figures_from_dive("clinical_labs"),
    trends=(
        "The clinical-lab industry has been reshaped by two forces pulling in "
        "opposite directions. PAMA's market-based CLFS reset cut routine test "
        "prices and rewarded only the largest, most automated networks — "
        "accelerating a duopoly (Quest, Labcorp) that also kept absorbing "
        "hospital outreach labs. At the same time, molecular and genomic "
        "testing exploded: oncology NGS panels, minimal-residual-disease and "
        "liquid-biopsy assays, hereditary and prenatal screening, and "
        "pharmacogenomics created a high-growth, high-value specialty layer that "
        "the routine giants and a cohort of public specialty labs both chase. "
        "That growth outran the payment system — codes and coverage (CPT/PLA, "
        "MolDX gapfill/crosswalk) lag clinical adoption, so cash trails volume "
        "and denials bite. Enforcement tightened around the edges (EKRA and AKS "
        "cases in toxicology and genetics), and the 2024 FDA rule to regulate "
        "lab-developed tests as devices now hangs over the esoteric model that "
        "ran for decades on CLIA alone. The forward story is molecular mix shift "
        "and decentralization/DTC volume on the top line, against PAMA rate "
        "erosion, coverage lag, and compliance cost on the bottom."),
    growth_levers=[
        GrowthLever(
            "Chronic-disease + aging test volume",
            "More patients with more chronic conditions drives routine and "
            "monitoring test volume across the menu.",
            "+~2-3%/yr volume", "ILLUSTRATIVE"),
        GrowthLever(
            "Molecular / genomic mix shift",
            "High-dollar NGS, MRD, liquid-biopsy, and hereditary assays replace "
            "or add to lower-value tests, lifting revenue per accession.",
            "+ revenue/accession", "ILLUSTRATIVE"),
        GrowthLever(
            "Oncology precision testing",
            "Comprehensive genomic profiling and monitoring in oncology is the "
            "fastest-growing, highest-value category.",
            "+ segment growth", "ILLUSTRATIVE"),
        GrowthLever(
            "Decentralization + DTC / employer testing",
            "Consumer-initiated and employer testing open volume outside the "
            "physician-order channel.",
            "+ new channel", "ILLUSTRATIVE"),
        GrowthLever(
            "PAMA / CLFS rate + coverage-lag drag",
            "Market-based CLFS cuts on routine tests and molecular coverage/"
            "coding lag on new assays subtract from realized revenue.",
            "rate & coverage risk", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Ordered-test volume × the molecular mix shift",
        analysis=(
            "Demand is the number of ordered tests and their shift toward "
            "higher-value molecular assays. The routine base grows steadily with "
            "an aging, more chronically-ill population and expanding "
            "screening/monitoring, but the price-per-test is falling under PAMA, "
            "so routine revenue is nearly flat-to-down even as volume rises. The "
            "real value engine is the molecular/genomic shift — oncology genomic "
            "profiling, minimal-residual-disease and liquid-biopsy monitoring, "
            "hereditary and prenatal screening, and pharmacogenomics — which "
            "multiplies revenue per accession. That growth, however, is "
            "throttled by the payment system rather than by physicians: an assay "
            "must earn a priced code and coverage (CPT/PLA, MolDX) before its "
            "clinical volume converts to cash, and decentralized/DTC channels "
            "add volume outside the traditional physician-order path. Net demand "
            "is ordered volume, weighted to molecular, net of coverage denials "
            "and patient bad debt."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Reagents, consumables & instruments", "~25-35% of cost",
            "Analyzer reagents, molecular kits, and instrument "
            "depreciation/lease — scale drives reagent pricing and the "
            "automation break-even.", "ILLUSTRATIVE"),
        CostDriver(
            "Labor (techs, med-techs, pathologists, PhDs)", "~25-35% of cost",
            "Licensed medical technologists on the line plus pathologist and "
            "PhD directors for esoteric/molecular sign-out.", "ILLUSTRATIVE"),
        CostDriver(
            "Logistics & specimen transport", "~10-15% of cost",
            "The courier / cold-chain network moving specimens to central labs "
            "— a defining fixed cost of the routine model.", "ILLUSTRATIVE"),
        CostDriver(
            "Billing, denials & patient bad debt", "~8-15% of net",
            "Complex payer billing, molecular denial/appeal work, and "
            "uncollected patient responsibility on high-deductible plans.",
            "ILLUSTRATIVE"),
        CostDriver(
            "R&D, validation & compliance (CLIA / CAP / FDA LDT)",
            "~5-12% of cost",
            "Assay development and validation, proficiency testing, "
            "accreditation, and the emerging FDA LDT compliance burden.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No public independent-lab facility census is vendored (CLIA "
        "certificates are not in our files), so state geography is omitted "
        "rather than fabricated. Qualitatively, routine-lab economics are "
        "national (centralized core labs plus courier logistics), so geography "
        "matters less than payer contracts; specialty and pathology labs "
        "cluster near academic and oncology referral centers. The CMS Provider "
        "of Services clinical-labs and NPI-taxonomy connectors linked below "
        "give a real CLIA-enrolled facility read."),
)

register(REPORT)
