"""Specialty Rx — specialty pharmacy for high-cost, complex therapies.

Deals-only vertical (NCPDP pharmacy files aren't vendored, so no facility
census), authored off the hospice copy-template. The report is built around the
three facts that decide a specialty-pharmacy deal: the Big-3 PBMs own the
channel, limited-distribution-drug (LDD) access is the moat, and the money is in
services and 340B capture — the ingredient spread itself is thin.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="specialty_pharmacy",
    name="Specialty Rx",
    care_setting="Pharmacy & infusion",
    naics="446110",
    one_line_def=(
        "Dispensing and clinical management of high-cost, complex therapies — "
        "biologics, oral oncology, specialty injectables, and rare-disease and "
        "limited-distribution drugs — with prior-authorization support, patient "
        "assistance, adherence programs, and manufacturer hub services."),
    tam_headline=TamHeadline(
        value=300.0, unit="$B", growth_pct=9.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "US specialty-drug spend dispensed through the specialty channel, "
            "modeled at ~$300B — specialty is now well over half of total US "
            "drug spend (IQVIA/CMS). This is drug revenue flowing through the "
            "channel, not pharmacy gross margin, which is a thin spread on top; "
            "growth is the modeled composite of pipeline, price, and mix."),
    ),
    executive_summary=[
        "The Big-3 PBMs own the channel. CVS Specialty (Caremark), Accredo "
        "(Express Scripts/Cigna), and Optum Specialty (UnitedHealth) — each "
        "vertically integrated with an insurer — steer the majority of "
        "specialty scripts to their own pharmacies. An independent's thesis is "
        "either a rare-disease LDD niche or health-system enablement.",
        "It is a spread-plus-services business, not a dispensing business. The "
        "ingredient spread is thin (low-single-digit percent), so real economics "
        "come from manufacturer hub/data/adherence fees, dispensing fees, and — "
        "for covered entities — 340B contract-pharmacy capture.",
        "Limited-distribution-drug (LDD) access is the moat. Manufacturers "
        "restrict many specialty drugs to a handful of pharmacies; you cannot "
        "dispense what you are not in the network for, so LDD wins are the asset.",
        "Gross-to-net is a trap for the unwary. The sticker (WAC/AWP) is a "
        "fiction — rebates flow to the PBM/plan, and DIR fees claw back Part D "
        "reimbursement after the fact. Underwrite net realized margin, not list.",
        "The live independent plays are rare-disease/LDD pure-plays (PANTHERx, "
        "Orsini) and health-system specialty enablement (Shields, Trellis) that "
        "captures a system's own script leakage plus 340B — the acquirable pool "
        "outside the PBM-owned giants.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Prescription + referral (often from a health-system specialist)",
            "Benefit investigation + prior authorization + appeals",
            "Financial assistance — copay cards, foundations, patient support",
            "Drug sourcing (wholesaler / GPO; 340B for covered entities)",
            "Dispense — cold-chain ship to patient or provider (or on-site)",
            "Clinical management — adherence (PDC), monitoring, REMS",
            "Manufacturer hub services + data reporting (a fee stream)",
            "Refill management — the recurring specialty annuity",
        ],
        sites_of_care=[
            "Central mail-order specialty pharmacy (the volume base)",
            "Health-system-embedded specialty pharmacy (leakage + 340B capture)",
            "Retail specialty (limited walk-in for certain therapies)",
            "Provider office (white-bag / medical-benefit dispensing)",
        ],
        money_flow=(
            "The pharmacy buys the drug (from a wholesaler, or at deeply "
            "discounted 340B pricing for covered entities) and is reimbursed by "
            "the PBM/plan at a contracted rate benchmarked to WAC/AWP/NADAC "
            "plus a dispensing fee. The gross spread is thin and, in Part D, "
            "reduced after the fact by DIR fees. The durable money is elsewhere: "
            "manufacturers pay hub-service, data, and adherence fees to the "
            "pharmacies in their limited-distribution networks; copay/foundation "
            "assistance keeps patients on therapy; and 340B contract-pharmacy "
            "arrangements let hospitals and FQHCs capture the discount-to-"
            "reimbursement spread on their own patients' specialty scripts. So "
            "specialty pharmacy earns on services and access, not on the "
            "dispensing act itself."),
        key_players=(
            "The Big-3 PBM-owned pharmacies dominate: CVS Specialty (Caremark), "
            "Accredo (Express Scripts / Cigna Evernorth), and Optum Specialty "
            "(UnitedHealth). Around them: McKesson's oncology-focused Biologics "
            "and Onco360; rare-disease and LDD specialists PANTHERx, Orsini, and "
            "AscellaHealth; and the health-system enablement models Shields "
            "Health Solutions (Walgreens) and Trellis Rx (CPS). Health systems "
            "increasingly stand up their own specialty pharmacies to capture "
            "leakage and 340B."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Specialty share of US drug spend", ">50% of drug spend",
                    "GOV · CMS / IQVIA specialty-spend analyses"),
            Segment("Oncology + hematology (oral + injectable)",
                    "the largest therapeutic block",
                    "ILLUSTRATIVE · therapeutic-mix model"),
            Segment("Immunology / autoimmune (self-injected biologics)",
                    "a major recurring block",
                    "ILLUSTRATIVE · therapeutic-mix model"),
            Segment("Rare disease / limited-distribution drugs",
                    "highest-margin niche (LDD access)",
                    "ILLUSTRATIVE · LDD network economics"),
            Segment("Health-system specialty (leakage + 340B capture)",
                    "fastest-growing channel",
                    "ILLUSTRATIVE · health-system enablement model"),
        ],
        growth_drivers=[
            "Specialty pipeline (oncology, immunology, rare, cell/gene) ~+8%/yr",
            "Continued list-price growth on branded specialty drugs ~+3-5%/yr",
            "Shift of new launches into specialty vs. traditional pharmacy",
            "Health-system specialty build-out capturing leakage + 340B",
            "Biosimilar entry — volume up, per-unit revenue down (mixed)",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial / PBM (self-insured + fully insured)": 0.50,
            "Medicare Part D / MA": 0.30,
            "Medicaid / 340B / other": 0.20,
        },
        rate_mechanics=[
            "Ingredient cost benchmark — reimbursement set off WAC / AWP / "
            "NADAC minus a discount, plus a dispensing fee; the spread to "
            "acquisition cost is the thin gross margin.",
            "DIR fees (Part D) — direct and indirect remuneration clawed back "
            "after adjudication; the 2024 reform moved DIR to point of sale, "
            "changing cash-flow timing but not the net.",
            "Manufacturer service fees — hub, data, and adherence fees paid to "
            "in-network specialty pharmacies (a real, non-dispensing revenue "
            "line).",
            "340B contract pharmacy — covered entities capture the discounted-"
            "acquisition-to-reimbursement spread on their patients' scripts.",
            "Copay assistance + foundations — copay cards and charitable "
            "foundations keep patients on high-cost therapy (adherence economics).",
            "Gross-to-net — rebates flow to the PBM/plan, so list price (WAC) "
            "overstates realized revenue; underwrite net.",
        ],
        reimbursement_risk=(
            "The margin is squeezed from several directions at once. The Big-3 "
            "PBMs set the contracted rate and steer their own book to their own "
            "pharmacies, compressing independents. DIR fees and gross-to-net "
            "erode net realized margin below what list implies. The 340B "
            "contract-pharmacy spread — which quietly underwrites much of the "
            "independent and health-system economics — is under active attack as "
            "manufacturers restrict contract-pharmacy shipments. And the IRA "
            "Medicare drug-price negotiation lowers the price base on some of the "
            "highest-revenue specialty molecules. Durable economics depend on "
            "LDD access and manufacturer service fees that the PBMs and price "
            "controls cannot easily strip."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicare Part D + pharmacy DIR fee reform (2024)",
                 "Governs specialty reimbursement and the DIR clawback; the "
                 "2024 point-of-sale reform reshaped pharmacy cash flow.",
                 "https://www.cms.gov/medicare/payment/prescription-drug-coverage"),
            Rule("340B Drug Pricing Program + contract-pharmacy dispute",
                 "The discount that underwrites much independent and health-"
                 "system specialty economics — and the contract-pharmacy fight "
                 "is the sector's largest regulatory risk.",
                 "https://www.hrsa.gov/opa"),
            Rule("Inflation Reduction Act — Medicare Drug Price Negotiation",
                 "Negotiated Medicare prices on top specialty molecules lower "
                 "the revenue base beginning 2026.",
                 "https://www.cms.gov/inflation-reduction-act-and-medicare/medicare-drug-price-negotiation"),
            Rule("PBM transparency / reform + FTC scrutiny",
                 "Federal and state PBM legislation and FTC action target the "
                 "vertical integration that squeezes independents.",
                 "https://www.ftc.gov/"),
            Rule("URAC / ACHC specialty pharmacy accreditation",
                 "Payer and manufacturer network access requires accreditation "
                 "— table stakes and an operating cost.",
                 "https://www.urac.org/"),
            Rule("State 'any willing pharmacy' + PBM regulation",
                 "State laws on network access and PBM conduct shape whether "
                 "independents can reach covered lives.",
                 None),
        ],
        policy_watch=[
            "340B contract-pharmacy manufacturer restrictions + litigation",
            "IRA negotiated-price expansion to more specialty drugs",
            "PBM reform (delinking, transparency) at the federal level",
            "DIR reform cash-flow effects working through the channel",
            "Biosimilar interchangeability + formulary placement",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Concentration at the top, fragmentation in the niches. The Big-3 "
            "PBM-owned pharmacies handle the majority of specialty script "
            "volume, while a long tail of rare-disease/LDD specialists and "
            "health-system pharmacies competes for access-gated niches. The "
            "acquirable pool is that tail — where LDD networks and 340B "
            "relationships, not scale alone, confer defensibility."),
        hhi_or_share=(
            "The Big-3 (CVS/Caremark, Cigna/Express Scripts, UnitedHealth/"
            "OptumRx) control the majority of specialty script volume — a "
            "highly concentrated channel. No vendored dispensing dataset lets "
            "us compute a defensible national HHI, so a precise figure is "
            "omitted."),
        consolidation=(
            "Vertical integration is the dominant structure — payer + PBM + "
            "specialty pharmacy under one roof (CVS/Aetna, Cigna/Express "
            "Scripts, UnitedHealth/Optum). Independent consolidation runs in the "
            "rare-disease/LDD lane (PANTHERx, Orsini, AscellaHealth) and in "
            "health-system enablement (Shields, Trellis). Multiples reflect LDD "
            "access and service-fee durability more than script count."),
        pe_activity=(
            "Sponsor interest concentrates where the PBMs cannot easily "
            "vertically foreclose: rare-disease and limited-distribution "
            "pure-plays with manufacturer relationships, and health-system "
            "specialty enablement that monetizes a system's own leakage and "
            "340B. Diligence centers on LDD network breadth, manufacturer "
            "service-fee mix, and 340B exposure."),
        notable_players=[
            "CVS Specialty (Caremark)", "Accredo (Express Scripts / Cigna)",
            "Optum Specialty (UnitedHealth)", "PANTHERx Rare", "Orsini",
            "Shields Health Solutions (Walgreens)", "Trellis Rx",
            "Biologics / Onco360 (McKesson)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Revenue / script", "$5,000-$50,000+",
                "Specialty scripts carry very high revenue per fill; the drug "
                "dominates the dollar figure."),
            Kpi("Gross margin / script", "2-6% of revenue",
                "The ingredient spread is thin on a percentage basis — the "
                "reason services and 340B, not dispensing, drive economics."),
            Kpi("LDD access (# of networks)", "the moat metric",
                "How many limited-distribution drug networks the pharmacy is "
                "in — the primary determinant of addressable volume."),
            Kpi("Adherence (PDC) / turnaround time", "PDC 80%+",
                "Proportion-of-days-covered and days-to-fill drive manufacturer "
                "and payer scorecards that gate network inclusion."),
            Kpi("Manufacturer service-fee mix", "% of gross profit",
                "Hub, data, and adherence fees — the durable, non-dispensing "
                "profit that PBM steering cannot easily strip."),
            Kpi("340B capture (health-system model)", "spread per script",
                "The discounted-acquisition-to-reimbursement spread that "
                "underwrites much health-system specialty economics."),
        ],
        margin_profile=(
            "On a percentage basis specialty pharmacy is a razor-thin gross-"
            "margin business — low single digits on the ingredient spread, "
            "further reduced by DIR and gross-to-net. Profitability is built by "
            "layering non-dispensing revenue on top: manufacturer hub/data/"
            "adherence fees, and, for covered entities, 340B contract-pharmacy "
            "spread. Scale matters for wholesaler/GPO purchasing and for "
            "spreading the clinical and prior-auth cost base, but access — LDD "
            "network inclusion — is what determines whether there is volume to "
            "earn on at all."),
    ),
    risks=[
        Risk("PBM vertical integration + steering", "High",
             "The Big-3 direct their own book to their own pharmacies, "
             "structurally squeezing independents out of covered lives."),
        Risk("340B contract-pharmacy restriction", "High",
             "Manufacturer limits on contract-pharmacy shipments threaten the "
             "spread that underwrites independent and health-system economics."),
        Risk("Loss of LDD network access", "High",
             "A manufacturer dropping the pharmacy from a limited-distribution "
             "network removes the addressable volume overnight."),
        Risk("DIR / gross-to-net compression", "Medium",
             "Clawbacks and rebate flows erode net realized margin below what "
             "list price implies."),
        Risk("IRA drug-price negotiation", "Medium",
             "Negotiated Medicare prices lower the revenue base on top specialty "
             "molecules from 2026."),
        Risk("Biosimilar substitution", "Medium",
             "Biosimilar entry raises volume but compresses per-unit revenue and "
             "reshuffles manufacturer relationships."),
    ],
    diligence_questions=[
        "How many and which limited-distribution-drug networks is the pharmacy "
        "in, and how concentrated is revenue in the top LDDs?",
        "What share of gross profit is manufacturer service fees versus "
        "ingredient spread versus 340B capture?",
        "What is the 340B exposure, and how vulnerable is it to contract-"
        "pharmacy restrictions?",
        "What is the payer/PBM concentration, and how much volume is at risk to "
        "Big-3 steering into their own pharmacies?",
        "What are adherence (PDC) and turnaround metrics against payer and "
        "manufacturer scorecards that gate network inclusion?",
        "What is net realized margin after DIR and gross-to-net, versus gross "
        "billed revenue?",
        "What is the therapeutic concentration, and what is the IRA-negotiation "
        "and biosimilar exposure of the top molecules?",
    ],
    insider_lens=[
        "It is a spread-plus-services business, not a dispensing business. The "
        "pharmacy earns a razor-thin ingredient spread and makes real money on "
        "manufacturer hub/data/adherence fees and 340B capture — model those "
        "lines, not the script count.",
        "LDD access is the asset. You cannot dispense a drug the manufacturer "
        "won't let you touch; the number and quality of limited-distribution "
        "networks a pharmacy is in is the single best proxy for defensible "
        "volume.",
        "The Big-3 own the channel and steer their own book to their own "
        "pharmacies. Any independent thesis has to answer why the PBMs can't "
        "foreclose it — usually rare-disease LDD niche or health-system "
        "leakage/340B capture they don't control.",
        "340B quietly underwrites a large share of independent and health-"
        "system specialty economics, and manufacturers are actively cutting "
        "off contract-pharmacy spread. That single policy fight can swing the "
        "P&L more than any operational lever.",
        "Gross-to-net makes list price a fiction. WAC and AWP overstate what "
        "the pharmacy actually realizes after rebates and DIR — a book that "
        "looks high-revenue can be low-margin once you net it down.",
    ],
    connections=default_connections(
        "specialty_pharmacy",
        deals_sector="specialty_pharmacy",
        connectors=[
            ("cms_open_data_mup_partd_prescriber_by_provider_drug",
             "CMS Part D prescriber-by-drug — specialty molecule dispensing "
             "and prescriber concentration"),
            ("cms_open_data_part_d_spending_by_drug",
             "CMS Part D drug spending — specialty-drug dollars and price "
             "trend"),
            ("cms_open_data_part_b_spending_by_drug",
             "CMS Part B drug spending — provider-administered / medical-"
             "benefit specialty spend"),
            ("medicaid_data_sdud_2025",
             "Medicaid State Drug Utilization Data — specialty-drug volume and "
             "the 340B/Medicaid overlap"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — specialty pharmacy enrollment and footprint"),
            ("open_payments_general_payments_2024",
             "CMS Open Payments — manufacturer ties across prescribing "
             "specialists"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded individuals/entities (integrity screen)"),
        ],
    ),
    sources=[
        Source("CMS / IQVIA analyses of specialty-drug share of US drug spend "
               "and channel revenue", "GOV",
               "https://www.cms.gov/data-research/statistics-trends-and-reports/national-health-expenditure-data"),
        Source("HRSA Office of Pharmacy Affairs — 340B Drug Pricing Program",
               "GOV", "https://www.hrsa.gov/opa"),
        Source("CMS Medicare Part D — payment, DIR reform, and drug-pricing "
               "rules", "GOV",
               "https://www.cms.gov/medicare/payment/prescription-drug-coverage"),
        Source("CMS Inflation Reduction Act — Medicare Drug Price Negotiation "
               "Program", "GOV",
               "https://www.cms.gov/inflation-reduction-act-and-medicare/medicare-drug-price-negotiation"),
        Source("Federal Trade Commission — PBM industry study and enforcement",
               "GOV", "https://www.ftc.gov/"),
        Source("PE Desk industry deep-dive (specialty pharmacy) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=specialty_pharmacy"),
    ],
    live_figures=live_figures_from_dive("specialty_pharmacy"),
    trends=(
        "Specialty pharmacy has moved from a niche to the center of drug spend: "
        "specialty is now well over half of all US drug dollars and captures the "
        "large majority of new launches. Two structural forces define the "
        "sector. First, vertical integration — the Big-3 PBMs, each married to a "
        "national insurer, own the channel and steer their own membership to "
        "their own pharmacies, compressing independents and inviting FTC and "
        "state PBM-reform scrutiny. Second, the economics migrated away from the "
        "dispensing act toward services and access: manufacturer hub/data/"
        "adherence fees and 340B contract-pharmacy capture became the durable "
        "profit, while the ingredient spread stayed razor-thin and DIR clawed "
        "back the rest. Now three policy vectors are converging on the model — "
        "the 340B contract-pharmacy fight, IRA drug-price negotiation on top "
        "molecules, and PBM reform — pushing independent capital toward the two "
        "defensible lanes the PBMs cannot easily foreclose: rare-disease/LDD "
        "pure-plays and health-system specialty enablement."),
    growth_levers=[
        GrowthLever(
            "Specialty drug pipeline (oncology / immunology / rare / cell-gene)",
            "The flow of new high-cost specialty launches expands the "
            "addressable dispensing base structurally.",
            "+8%/yr pipeline", "ILLUSTRATIVE"),
        GrowthLever(
            "Branded specialty list-price growth",
            "Continued price increases on branded specialty drugs lift revenue "
            "per script (partly offset by gross-to-net).",
            "+3-5%/yr price", "ILLUSTRATIVE"),
        GrowthLever(
            "Health-system specialty build-out",
            "Systems capture their own script leakage and 340B by standing up "
            "or partnering on specialty pharmacies — the fastest-growing "
            "channel.",
            "channel shift", "ILLUSTRATIVE"),
        GrowthLever(
            "Manufacturer service-fee expansion",
            "Hub, data, and adherence programs grow as manufacturers push "
            "patient-support economics onto the pharmacy.",
            "margin mix", "ILLUSTRATIVE"),
        GrowthLever(
            "Biosimilar entry",
            "Biosimilars lift dispensed volume but compress per-unit revenue "
            "and reshuffle manufacturer networks — a mixed lever.",
            "volume up / price down", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="The specialty-drug pipeline and its share of drug spend",
        analysis=(
            "The dominant demand driver is the pharmaceutical pipeline itself: "
            "the steady flow of new biologics, oral oncology agents, and rare-"
            "disease and cell/gene therapies, and the fact that a growing "
            "majority of new launches are specialty rather than traditional "
            "drugs. Specialty already represents well over half of US drug "
            "spend and continues to gain share, so the dispensing base expands "
            "even before any single disease's prevalence changes. Layered on "
            "top, branded list prices keep rising and health systems keep "
            "internalizing their own specialty volume to capture leakage and "
            "340B. The counterweights are policy, not demand — IRA price "
            "negotiation and biosimilar entry lower per-unit revenue on the "
            "biggest molecules even as unit volume grows — so the driver is "
            "durable in units and contested in dollars."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Drug acquisition (inventory)",
            "~90%+ of revenue",
            "The medication itself dwarfs every other line; the entire business "
            "model is a thin spread taken on top of this cost.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Clinical + prior-authorization labor",
            "the #1 controllable cost",
            "Pharmacists, benefit-investigation and prior-auth staff, and "
            "adherence/patient-support teams — the service engine that earns "
            "manufacturer fees.", "ILLUSTRATIVE"),
        CostDriver(
            "Fulfillment, cold-chain & shipping",
            "~5-10% of operating cost",
            "Temperature-controlled dispensing and direct-to-patient shipping "
            "for high-value biologics.", "ILLUSTRATIVE"),
        CostDriver(
            "Accreditation, technology & compliance",
            "~5-8% of operating cost",
            "URAC/ACHC accreditation, specialty pharmacy systems, REMS, and "
            "manufacturer data reporting — table stakes for network access.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Bad debt / copay assistance operations",
            "varies by book",
            "Patient copay-assistance administration and uncollected patient "
            "responsibility on very high-cost therapies.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "NCPDP and state-board pharmacy files are not vendored, so a national "
        "specialty-pharmacy facility census is unavailable and geography is not "
        "the structural read — it is omitted rather than fabricated. Specialty "
        "pharmacy is largely a central-fill, ship-to-patient model whose "
        "footprint follows licensure (pharmacies carry multi-state licenses to "
        "reach covered lives), LDD network access, and health-system "
        "relationships rather than a physical catchment. Use the corpus deal "
        "history and the Part D / Medicaid drug-utilization connectors to "
        "triangulate prescribing geography."),
)

register(REPORT)
