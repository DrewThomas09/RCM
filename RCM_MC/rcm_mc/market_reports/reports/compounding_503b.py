"""503B Compounding — FDA-registered sterile outsourcing facilities.

Deals-only vertical (the FDA 503B registry is public but not vendored as a
facility roll), authored off the hospice copy-template. The report is organized
around the truth that decides a 503B deal: this is a sterile-manufacturing
business, not a pharmacy — the economics, the risk, and the diligence are cGMP
quality, and a single FDA sterility finding can shut the plant (NECC and
PharMEDium are the ghosts in the room).
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="compounding_503b",
    name="503B Compounding",
    care_setting="Pharmacy & infusion",
    naics="325412",
    one_line_def=(
        "FDA-registered outsourcing facilities that compound sterile (and some "
        "non-sterile) drugs in bulk without patient-specific prescriptions, for "
        "'office use' by hospitals, ASCs, and clinics — created by the Drug "
        "Quality and Security Act of 2013 and required to operate under FDA "
        "current Good Manufacturing Practice (cGMP)."),
    tam_headline=TamHeadline(
        value=4.0, unit="$B", growth_pct=10.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "US 503B outsourcing / sterile-compounding market, modeled at ~$4B "
            "of B2B product sales to hospitals and clinics — there is no CMS "
            "fee-schedule line because 503Bs sell product, not billed services. "
            "Growth is modeled and volatile (the GLP-1 shortage boom-bust "
            "illustrates the shortage dependency)."),
    ),
    executive_summary=[
        "It is a sterile-manufacturing business, not a pharmacy. The economics, "
        "the risk, and the diligence are cGMP manufacturing — underwrite the "
        "quality system first, the P&L second, because a single FDA sterility "
        "finding can shut the plant (NECC and PharMEDium are the precedents).",
        "Shortage-dependent revenue is a trap. The GLP-1 boom-bust showed it — "
        "volume built on a drug shortage evaporates the day FDA delists the "
        "drug. Durable 503Bs are built on the ready-to-administer and hospital-"
        "standardization value proposition, not on copying a shortage molecule.",
        "The value to the hospital is labor, USP <797> burden, and waste — not "
        "just a cheaper molecule. A 503B that takes the sterile-compounding risk "
        "and labor off the hospital pharmacy is far stickier than one selling "
        "price arbitrage.",
        "It is a B2B product business, not a reimbursed one. The 503B sells to "
        "hospitals, ASCs, and clinics (often through GPOs and at 340B pricing) "
        "who then bill payers for the administered drug — the 503B's revenue is "
        "manufacturing margin on product sales.",
        "The durable niches are ophthalmic (compounded anti-VEGF, injectables) "
        "and anesthesia ready-to-administer syringes; office-use dermatology, "
        "hormone, and med-spa work is higher-margin but higher-scrutiny.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Identify demand — drug shortage, ready-to-administer, or standard "
            "concentration need",
            "Source bulk drug substances (must be on the 503B Bulks List or an "
            "approved-drug shortage)",
            "cGMP sterile manufacturing — batch production, not patient-specific",
            "Sterility + stability + endotoxin release testing (QC)",
            "DSCSA serialization + distribution to facility customers",
            "Sell B2B — direct or via GPO contract; 340B pricing for entities",
            "Customer administers the drug and bills the payer downstream",
            "FDA inspection + ongoing cGMP quality-system maintenance",
        ],
        sites_of_care=[
            "Hospital + health-system pharmacies (standardized concentrations, "
            "RTA syringes)",
            "Ambulatory surgery centers + anesthesia groups (OR-ready syringes)",
            "Ophthalmology + specialty clinics (compounded injectables)",
            "Physician offices / dermatology / med-spa (office-use products)",
        ],
        money_flow=(
            "A 503B is paid B2B: it manufactures sterile drug product and sells "
            "it to hospitals, ASCs, and clinics at a product price — directly or "
            "through group-purchasing-organization contracts, and at 340B "
            "pricing for covered entities. It earns a manufacturing gross margin "
            "over cGMP production cost, not a payer fee-schedule amount. The "
            "reimbursement event happens downstream: the customer administers "
            "the drug to a patient and bills Medicare Part B, Medicaid, or a "
            "commercial plan for the administered product (often as an "
            "unclassified J-code because compounded preparations lack their own "
            "NDC). So the 503B's revenue is decoupled from patient billing — it "
            "is a specialty sterile manufacturer whose demand is set by hospital "
            "purchasing, drug shortages, and the labor/waste/quality economics "
            "of in-house compounding."),
        key_players=(
            "A concentrating field of sterile outsourcers: QuVa Pharma, Nephron "
            "Pharmaceuticals, Fagron Sterile Services, SCA Pharmaceuticals, "
            "Leiters (ophthalmic + hospital), Olympia Pharmaceuticals, and "
            "Empower Pharmacy (a large 503A+503B, GLP-1-heavy). ImprimisRx "
            "(Harrow) anchors ophthalmology. B. Braun's CAPS runs hospital "
            "admixture. The cautionary tale is PharMEDium (AmerisourceBergen), "
            "which was shut down after FDA quality findings — a reminder that "
            "scale does not immunize a 503B against a sterility failure."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Hospital / health-system sterile products",
                    "the core B2B channel",
                    "ILLUSTRATIVE · hospital-outsourcing model"),
            Segment("Anesthesia ready-to-administer syringes",
                    "durable OR-ready annuity",
                    "ILLUSTRATIVE · RTA-demand model"),
            Segment("Ophthalmic injectables (compounded anti-VEGF etc.)",
                    "durable specialty niche",
                    "ILLUSTRATIVE · ophthalmic-compounding model"),
            Segment("Drug-shortage fill volume",
                    "large but volatile (shortage-gated)",
                    "GOV · FDA drug shortage list dependency"),
            Segment("Office-use (derm / hormone / med-spa)",
                    "higher-margin, higher-scrutiny",
                    "ILLUSTRATIVE · office-use model"),
        ],
        growth_drivers=[
            "Persistent sterile-injectable drug shortages ~structural",
            "Hospital outsourcing of <797> labor, waste, and risk",
            "Ready-to-administer standardization for patient safety",
            "Ophthalmic + specialty compounded-injectable demand",
            "Regulatory whipsaw (GLP-1 delisting) — a volatile, two-way driver",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "End-market: Medicare Part B / Part D": 0.45,
            "End-market: Commercial": 0.40,
            "End-market: Medicaid / 340B / other": 0.15,
        },
        rate_mechanics=[
            "B2B product sales — the 503B is paid a product price by the "
            "facility, not a payer fee schedule; revenue is manufacturing "
            "margin over cGMP cost.",
            "GPO contracting — much volume flows through hospital group-"
            "purchasing-organization agreements that set price and access.",
            "340B pricing — covered-entity customers buy at 340B discounts, "
            "shaping the price the 503B can command.",
            "Downstream billing — the customer administers the drug and bills "
            "Medicare Part B / commercial, often as an unclassified J-code "
            "(compounded products lack an NDC).",
            "Shortage-dependent legality — compounding a copy of an approved "
            "drug is permissible chiefly when it is on the FDA shortage list; "
            "delisting removes both the legality and the revenue.",
            "Value pricing vs. in-house cost — the 503B prices against the "
            "hospital's fully-loaded cost of compounding in-house (labor, <797>, "
            "waste), not against a reimbursement benchmark.",
        ],
        reimbursement_risk=(
            "The 503B does not face payer reimbursement risk directly — it faces "
            "demand and quality risk. Demand is gated by drug shortages (the "
            "GLP-1 delisting whipsaw wiped out a large compounded volume when FDA "
            "removed semaglutide and tirzepatide from the shortage list) and by "
            "hospital make-versus-buy economics. The existential risk is quality: "
            "an FDA cGMP inspection finding (Form 483), warning letter, or recall "
            "can halt production and destroy customer trust, and a sterility "
            "failure carries catastrophic patient-safety and liability exposure "
            "(the NECC 2012 fungal-meningitis outbreak that killed dozens created "
            "this entire regulatory regime). Downstream, customers' 340B and GPO "
            "economics shape the price the 503B can hold."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Drug Quality and Security Act (DQSA) 2013 / FDCA §503B",
                 "The enabling statute that created FDA-registered outsourcing "
                 "facilities after the NECC outbreak — the legal foundation of "
                 "the entire model.",
                 "https://www.fda.gov/drugs/human-drug-compounding/compounding-and-fda-questions-and-answers"),
            Rule("FDA cGMP for outsourcing facilities + inspection",
                 "503Bs must meet current Good Manufacturing Practice and are "
                 "FDA-inspected; a 483 / warning letter / recall is existential.",
                 "https://www.fda.gov/drugs/human-drug-compounding/registered-outsourcing-facilities"),
            Rule("503B Bulks List (§503B(a)(2))",
                 "Defines which bulk drug substances a 503B may compound — the "
                 "boundary of the legally-compoundable menu.",
                 "https://www.fda.gov/drugs/human-drug-compounding/bulk-drug-substances-used-compounding-under-section-503b-fdc-act"),
            Rule("FDA drug shortage list (§506E)",
                 "Compounding copies of approved drugs is generally permissible "
                 "only during shortage; delisting removes both legality and "
                 "revenue (the GLP-1 case).",
                 "https://www.accessdata.fda.gov/scripts/drugshortages/"),
            Rule("USP <797> sterile / <800> hazardous compounding",
                 "The sterile and hazardous-drug standards that 503B operations "
                 "and their hospital customers are measured against.",
                 "https://www.usp.org/compounding"),
            Rule("DSCSA track-and-trace + state dual-licensure",
                 "Drug Supply Chain Security Act serialization plus state "
                 "pharmacy/manufacturer licensure layered on FDA registration.",
                 "https://www.fda.gov/drugs/drug-supply-chain-security-act-dscsa"),
        ],
        policy_watch=[
            "FDA additions/removals on the 503B Bulks List",
            "Drug-shortage-list changes (GLP-1 delisting aftermath)",
            "FDA inspection cadence + enforcement posture on outsourcers",
            "Office-use / bulk-substance policy clarifications",
            "State board conflicts with the federal 503B framework",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Concentrating from a fragmented base. cGMP capital intensity and "
            "FDA scrutiny favor scaled, well-capitalized operators; a tail of "
            "smaller 503Bs and dual 503A/503B pharmacies persists but the "
            "quality bar is pushing consolidation. The acquirable pool is the "
            "mid-scale outsourcer with a clean inspection record and durable "
            "hospital relationships."),
        hhi_or_share=(
            "No single dominant 503B; QuVa, Nephron, Fagron, SCA, and Leiters "
            "are among the scaled names. The FDA 503B registry is public but not "
            "vendored as a facility roll here, so a national HHI is omitted "
            "rather than fabricated."),
        consolidation=(
            "Consolidation is quality- and capital-driven. Well-capitalized "
            "outsourcers (QuVa, Nephron, Fagron, SCA) expand capacity and buy "
            "smaller operators, while the PharMEDium shutdown showed how a "
            "quality failure removes capacity from the market. Sponsor-backed "
            "platforms build around clean inspection histories and hospital / "
            "GPO relationships."),
        pe_activity=(
            "Sponsor interest is real but quality-gated: 503Bs offer specialty-"
            "manufacturing margins and a structural shortage-fill role, but the "
            "diligence is a cGMP-plant diligence — inspection history, quality "
            "systems, and product concentration — more than a healthcare-"
            "services diligence. Shortage-dependent (e.g. GLP-1-heavy) revenue "
            "is discounted heavily."),
        notable_players=[
            "QuVa Pharma", "Nephron Pharmaceuticals", "Fagron Sterile Services",
            "SCA Pharmaceuticals", "Leiters", "Olympia Pharmaceuticals",
            "Empower Pharmacy", "ImprimisRx (Harrow)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("FDA inspection record (483s / warning letters)", "clean = the "
                "asset",
                "The single most important diligence input — a quality finding "
                "can halt production; a clean history is the value."),
            Kpi("Product / therapy concentration", "durable vs. shortage-gated",
                "How much revenue is durable RTA/standardization vs. shortage-"
                "dependent copies (the GLP-1 exposure)."),
            Kpi("Capacity utilization (cleanroom / lines)", "manufacturing "
                "metric",
                "Sterile-manufacturing operating leverage — fixed cleanroom and "
                "QC cost spread across batch volume."),
            Kpi("Gross margin on product", "specialty-manufacturing range",
                "Manufacturing margin over cGMP cost — higher on office-use and "
                "specialty, thinner on commodity hospital fill."),
            Kpi("Customer / GPO concentration", "commercial-risk metric",
                "Reliance on a few health-system or GPO accounts that can "
                "in-source or re-contract."),
            Kpi("Batch-failure / recall rate", "quality-cost metric",
                "Failed batches and any recall history — a direct hit to margin "
                "and to customer trust."),
        ],
        margin_profile=(
            "A 503B earns a specialty-manufacturing gross margin — the spread "
            "between a product price (set against the hospital's in-house "
            "make cost, or against a branded alternative) and the fully-loaded "
            "cGMP production cost. Cleanroom, QC/testing, and quality-system "
            "overhead are largely fixed, so utilization drives operating "
            "leverage. Office-use, ophthalmic, and specialty products carry "
            "richer margins than commodity hospital fill. But the margin is "
            "hostage to quality: a batch failure, a recall, or an FDA-driven "
            "production halt can erase a year's profit, which is why the quality "
            "system — not the price list — is the real economic engine."),
    ),
    risks=[
        Risk("FDA cGMP finding / warning letter / recall", "High",
             "A 483, warning letter, or recall can halt production and destroy "
             "customer trust — the existential 503B risk (see PharMEDium)."),
        Risk("Sterility failure / contamination liability", "High",
             "A sterility breach carries catastrophic patient-safety and legal "
             "exposure — the NECC outbreak created this whole regime."),
        Risk("Drug-shortage dependency", "High",
             "Revenue built on a shortage evaporates when FDA delists the drug "
             "(the GLP-1 whipsaw) — a structural earnings-quality risk."),
        Risk("Bulks-list / office-use policy change", "Medium",
             "FDA changes to compoundable substances or office-use rules can "
             "remove a product line."),
        Risk("Customer / GPO concentration", "Medium",
             "A few health-system or GPO accounts can in-source or re-contract, "
             "swinging volume."),
        Risk("Manufacturer re-entry / biosimilars", "Medium",
             "When the branded manufacturer resupplies or a biosimilar enters, "
             "the compounded volume can disappear."),
    ],
    diligence_questions=[
        "What is the full FDA inspection history — 483 observations, warning "
        "letters, recalls — and the state of the quality system?",
        "What share of revenue is durable (RTA / standardization / ophthalmic) "
        "versus shortage-dependent copies (GLP-1 exposure)?",
        "What is customer and GPO concentration, and how in-source-able is the "
        "top-account volume?",
        "What is cleanroom capacity utilization and the batch-failure / recall "
        "rate?",
        "How is each key product's legality anchored — on the 503B Bulks List "
        "or on a current drug shortage?",
        "What is the product-liability and insurance posture given sterility "
        "risk?",
        "What is the gross-margin mix across hospital fill, RTA, ophthalmic, "
        "and office-use lines?",
    ],
    insider_lens=[
        "Underwrite the quality system, not the P&L. A 503B is a sterile-drug "
        "plant; a single FDA sterility finding can shut it down (PharMEDium and "
        "NECC are the ghosts in every diligence). The clean inspection record "
        "is the asset — everything else is downstream of it.",
        "Shortage revenue is a trap dressed as growth. The GLP-1 boom-bust "
        "proved it: build a P&L on a drug shortage and it vanishes the day FDA "
        "delists the molecule. Value the durable RTA/standardization book "
        "separately from the shortage-fill book.",
        "You're selling labor and risk relief, not a cheaper molecule. The "
        "stickiest 503B pitch to a hospital is 'we take the <797> compounding "
        "labor, waste, and sterility risk off your pharmacy' — that's a "
        "relationship a price war can't easily dislodge.",
        "Ophthalmic and anesthesia RTA are the good annuities; office-use derm/"
        "hormone/med-spa is higher-margin but higher-scrutiny. Two 503Bs with "
        "the same revenue can carry very different risk profiles by mix.",
        "503A and 503B are a licensing and liability chasm. Many operators run "
        "both; the 503B side (cGMP, office-use, FDA-inspected) is the scalable, "
        "defensible half — and the capital- and compliance-heavy one that the "
        "whole valuation hinges on.",
    ],
    connections=default_connections(
        "compounding_503b",
        deals_sector="compounding",
        connectors=[
            ("openfda_drug_enforcement",
             "openFDA drug enforcement / recalls — the central quality and "
             "recall screen for sterile compounders"),
            ("openfda_drug_ndc",
             "openFDA NDC directory — registered drug products and the "
             "manufacturer/outsourcer landscape"),
            ("openfda_drug_label",
             "openFDA drug labeling — approved-product references for shortage "
             "and copy analysis"),
            ("cms_open_data_part_b_spending_by_drug",
             "CMS Part B drug spending — downstream administered-drug dollars "
             "for compounded categories"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — pharmacy / outsourcing-facility and downstream "
             "customer enrollment"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded individuals/entities (integrity screen)"),
        ],
    ),
    sources=[
        Source("FDA — Human Drug Compounding, Registered Outsourcing "
               "Facilities (§503B)", "GOV",
               "https://www.fda.gov/drugs/human-drug-compounding/registered-outsourcing-facilities"),
        Source("Drug Quality and Security Act (DQSA) of 2013 — FDA compounding "
               "framework", "GOV",
               "https://www.fda.gov/drugs/human-drug-compounding/compounding-and-fda-questions-and-answers"),
        Source("FDA Drug Shortages database (§506E) — shortage status "
               "governing compoundability", "GOV",
               "https://www.accessdata.fda.gov/scripts/drugshortages/"),
        Source("USP General Chapters <797> / <800> — sterile and hazardous "
               "compounding standards", "INDUSTRY",
               "https://www.usp.org/compounding"),
        Source("New England Journal of Medicine / peer-reviewed analyses of the "
               "2012 NECC fungal-meningitis outbreak and compounding safety",
               "ACADEMIC", "https://www.nejm.org/"),
        Source("PE Desk industry deep-dive (503B compounding) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=compounding_503b"),
    ],
    live_figures=live_figures_from_dive("compounding_503b"),
    trends=(
        "The 503B segment exists because of a disaster: the 2012 New England "
        "Compounding Center fungal-meningitis outbreak, which killed dozens and "
        "prompted the 2013 Drug Quality and Security Act creating FDA-registered "
        "outsourcing facilities under cGMP. Since then the sector has been pulled "
        "by two durable tailwinds and whipsawed by a third factor. The tailwinds "
        "are persistent sterile-injectable drug shortages (503Bs are the relief "
        "valve) and hospitals outsourcing the labor, waste, and USP <797> risk of "
        "in-house sterile compounding, especially for ready-to-administer "
        "anesthesia syringes and standardized concentrations. The whipsaw is "
        "regulatory: the 2022-2024 GLP-1 (semaglutide/tirzepatide) compounding "
        "boom, built on those drugs' shortage status, collapsed when FDA removed "
        "them from the shortage list — a vivid lesson that shortage-gated revenue "
        "is not durable. Underneath, the sector is consolidating on quality and "
        "capital, and the PharMEDium shutdown remains the cautionary tale that a "
        "single sterility failure — not a payer cut — is what ends a 503B."),
    growth_levers=[
        GrowthLever(
            "Sterile-injectable drug shortages",
            "Chronic shortages of sterile injectables make 503Bs the structural "
            "relief valve — durable in aggregate, volatile drug-by-drug.",
            "structural", "GOV"),
        GrowthLever(
            "Hospital outsourcing of <797> labor + risk",
            "Hospitals shift sterile-compounding labor, waste, and liability to "
            "503Bs, especially ready-to-administer products.",
            "make → buy shift", "ILLUSTRATIVE"),
        GrowthLever(
            "Ready-to-administer standardization",
            "Patient-safety and error-reduction drives demand for pre-filled, "
            "standardized-concentration syringes and bags.",
            "safety-driven", "ILLUSTRATIVE"),
        GrowthLever(
            "Ophthalmic + specialty injectables",
            "Compounded anti-VEGF and other ophthalmic and specialty injectables "
            "are a durable, higher-margin niche.",
            "niche demand", "ILLUSTRATIVE"),
        GrowthLever(
            "Regulatory whipsaw (shortage delistings)",
            "FDA shortage-list and bulks-list changes add or remove entire "
            "product lines — a genuine two-way swing (the GLP-1 case).",
            "two-way", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Hospital make-versus-buy on sterile compounding (plus shortages)",
        analysis=(
            "The dominant demand driver is a hospital procurement decision: "
            "whether to compound sterile preparations in-house or buy them from "
            "a 503B. That make-versus-buy calculus is moving structurally toward "
            "buy, pushed by the labor and cost of maintaining a USP <797> "
            "cleanroom, drug-waste economics, patient-safety pressure for ready-"
            "to-administer standardized products, and the liability of doing "
            "sterile compounding on-site. Overlaid on that durable shift is a "
            "volatile second driver — drug shortages — which spike demand for "
            "compounded copies of specific molecules and then collapse it when "
            "the shortage resolves or FDA delists the drug (the GLP-1 episode is "
            "the archetype). A quality 503B thesis therefore rests on the "
            "durable outsourcing shift and the ready-to-administer/ophthalmic "
            "annuity, treating shortage-fill volume as a cyclical, discountable "
            "overlay rather than the base."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Bulk drug substances + raw materials",
            "~35-50% of COGS",
            "Active pharmaceutical ingredients and sterile raw materials — the "
            "input cost of the compounded product.", "ILLUSTRATIVE"),
        CostDriver(
            "Quality systems, QC testing & regulatory",
            "the defining cost intensity",
            "Sterility/stability/endotoxin testing, quality-assurance staff, and "
            "FDA cGMP compliance — the cost that IS the business and the moat.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Cleanroom facility + equipment (fixed)",
            "~15-20% of cost",
            "The cGMP cleanroom, isolators, fill lines, and environmental "
            "controls — a fixed base that utilization leverages.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Manufacturing / compounding labor",
            "~10-15% of cost",
            "Skilled aseptic-processing technicians and pharmacists running "
            "batch production.", "ILLUSTRATIVE"),
        CostDriver(
            "Distribution + DSCSA serialization",
            "~5-8% of cost",
            "Cold-chain distribution to facility customers plus track-and-trace "
            "serialization compliance.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "The FDA maintains a public registry of 503B outsourcing facilities, "
        "but it is not vendored here as a clean facility roll, so a computed "
        "state map is omitted rather than fabricated. Geography is not the "
        "structural read for a B2B sterile manufacturer in any case — a single "
        "cGMP plant ships nationally to hospital and GPO customers — so the "
        "relevant concentration is by facility and inspection record, not by "
        "state. Use the FDA registry and the openFDA recall/enforcement "
        "connectors to profile individual outsourcers and their quality "
        "history."),
)

register(REPORT)
