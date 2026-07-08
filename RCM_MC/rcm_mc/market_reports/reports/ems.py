"""EMS — ground ambulance (emergency 911 + non-emergency medical transport).

Deals-only market-report module (no vendored NEMSIS agency-level facility file,
so no computed state_breakdown or supply trend). Live SOURCED figures wire from
``ems_deep_dive()`` — the sector's own realized-deal corpus. The qualitative
sections are authored around the two facts that define ground-ambulance
economics: the payer mix on 911 calls is the worst in healthcare, and ground
ambulance was carved OUT of the No Surprises Act, so balance-billing survives
where state law allows — a fragile, politically exposed margin.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="ems",
    name="EMS",
    care_setting="Other services",
    naics="621910",
    one_line_def=(
        "Ground ambulance services — 911 emergency response under exclusive "
        "operating-area contracts plus scheduled non-emergency and "
        "interfacility transport — paid a Medicare Ambulance Fee Schedule base "
        "rate plus mileage, against a payer mix dominated by Medicare, "
        "Medicaid, and self-pay."),
    tam_headline=TamHeadline(
        value=22.0, unit="$B", growth_pct=4.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled total US ground-ambulance revenue across all payers. The "
            "GOV anchor is Medicare ground-ambulance fee-schedule spend (~$6B, "
            "GAO/MedPAC); municipal 911 subsidies and non-emergency transport "
            "add the rest. Growth is the modeled composite (utilization + rate "
            "add-on extenders)."),
    ),
    executive_summary=[
        "The payer mix on 911 calls is the worst in healthcare: Medicare, "
        "Medicaid, and self-pay/uninsured dominate the unscheduled book, so net "
        "collection is a fraction of billed charges. You cannot choose your "
        "patients when you hold the 911 contract — the mix comes with the "
        "territory.",
        "Ground ambulance was deliberately carved OUT of the federal No "
        "Surprises Act. Balance-billing the patient for the out-of-network "
        "balance is still legal where state law allows — a real but fragile "
        "margin source that a growing number of states are now regulating.",
        "The business is two businesses stapled together: low-margin (often "
        "money-losing) municipal 911 contracts that win the franchise, "
        "cross-subsidized by higher-margin scheduled non-emergency and "
        "interfacility transport. The mix between them is the whole P&L.",
        "Medicare's rural, super-rural, and urban add-on payments are temporary "
        "and repeatedly extended by Congress — a perennial legislative-cliff "
        "risk sitting under the rate base, now compounded by the mandatory "
        "Ground Ambulance Data Collection System that could drive rate rebasing.",
        "Labor is the binding constraint and the largest cost: the "
        "paramedic/EMT shortage and wage inflation cap unit-hour utilization and "
        "growth. Consolidation is real but fragile — Global Medical Response "
        "(KKR) scaled the roll-up and then had to restructure its debt.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "911 call or scheduled transport request (facility discharge / dialysis)",
            "Dispatch and response under the exclusive-operating-area contract",
            "On-scene assessment and level-of-service determination (BLS/ALS/SCT)",
            "Transport + mileage to the appropriate destination",
            "Run-report documentation and medical-necessity coding",
            "Claim to Medicare AFS / Medicaid / commercial, then patient balance",
            "Collections against a low-net-yield, high-self-pay payer mix",
        ],
        sites_of_care=[
            "911 emergency response (exclusive operating area / municipal contract)",
            "Interfacility / hospital-discharge transport (higher-margin book)",
            "Non-emergency scheduled transport (incl. dialysis BLS — fraud-scrutinized)",
            "Critical-care and specialty-care transport (SCT, highest acuity)",
            "Community paramedicine / mobile integrated health (emerging, thin pay)",
        ],
        money_flow=(
            "Medicare pays under the Ambulance Fee Schedule (AFS): a base rate "
            "set by level of service — Basic Life Support (BLS), Advanced Life "
            "Support (ALS1/ALS2), and Specialty Care Transport (SCT) — plus a "
            "per-mile amount, with temporary geographic add-ons for rural, "
            "super-rural, and urban areas. Medicaid pays substantially less and "
            "self-pay/uninsured often pay little, so on 911 volume the net "
            "collection rate is low. Commercial payers pay more, and where "
            "ground ambulance is out-of-network and state law permits, the "
            "provider may balance-bill the patient — the No Surprises Act does "
            "not cover ground transport. Municipal 911 contracts frequently "
            "carry a subsidy or are run at a loss to hold the franchise, with "
            "profit coming from the scheduled non-emergency and interfacility book."),
        key_players=(
            "The scaled consolidator is Global Medical Response (KKR) — parent "
            "of American Medical Response (AMR) on the ground and Air Evac in the "
            "air. Other multi-market operators include Falck, Priority Ambulance, "
            "Acadian Ambulance, and Medline/regional players. The rest of the "
            "market is intensely local: municipal fire-based EMS, hospital-based "
            "transport, county and district services, nonprofits, and volunteer "
            "corps. The acquirable pool is the private for-profit operators and "
            "the interfacility/non-emergency books — municipal 911 is contracted, "
            "not bought."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Medicare ground-ambulance FFS spend (the GOV anchor)",
                    "~$6B/yr",
                    "GOV · GAO / MedPAC ground-ambulance analyses"),
            Segment("Total US ground-ambulance revenue (all payers)",
                    "~$22B (modeled)",
                    "ILLUSTRATIVE · all-payer + municipal-subsidy build"),
            Segment("911 emergency vs non-emergency transport",
                    "911 is high-volume / low-yield; scheduled carries margin",
                    "ILLUSTRATIVE · book-of-business split"),
            Segment("Provider mix — public / private / nonprofit / volunteer",
                    "highly fragmented, municipality-anchored",
                    "INDUSTRY · trade-association structure"),
        ],
        growth_drivers=[
            "Call-volume growth with aging + population ~2-3%/yr",
            "Medicare AFS updates + temporary add-on extenders ~2-3%/yr",
            "Interfacility / non-emergency transport demand (hospital throughput)",
            "Community paramedicine / treat-in-place reimbursement (emerging)",
            "Labor cost inflation — a negative lever that caps unit-hour utilization",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare / MA": 0.35,
            "Medicaid": 0.25,
            "Commercial": 0.22,
            "Self-pay / uninsured": 0.18,
        },
        rate_mechanics=[
            "Medicare Ambulance Fee Schedule (AFS) — base rate by level of "
            "service (BLS, ALS1, ALS2, SCT) plus a statutory per-mile amount.",
            "Temporary add-on payments — rural, super-rural, and urban bonuses "
            "that Congress repeatedly extends; a standing legislative-cliff risk.",
            "Ground Ambulance Data Collection System (GADCS) — CMS-mandated cost "
            "reporting that may drive a future rate rebasing.",
            "No Surprises Act CARVE-OUT — ground ambulance is excluded from "
            "federal OON balance-billing protection; state law governs instead.",
            "Medical-necessity + level-of-service documentation gates payment; "
            "non-emergency BLS (esp. dialysis transport) is a fraud-audit target.",
            "Municipal contract economics — 911 exclusivity often comes with a "
            "subsidy or a loss leader, recovered on the scheduled book.",
        ],
        reimbursement_risk=(
            "Two risks dominate. First, payer mix: the 911 book is Medicare-, "
            "Medicaid-, and self-pay-heavy, so net collection runs far below "
            "billed charges and is highly sensitive to Medicaid rates and "
            "uninsured share. Second, the balance-billing overhang: ground "
            "ambulance's carve-out from the No Surprises Act lets providers bill "
            "the OON balance where state law allows, but a growing number of "
            "states are regulating or banning it, and a federal advisory "
            "committee has recommended extending protections — so a real slice "
            "of margin is politically exposed. Layered on: the temporary add-on "
            "extenders, GADCS-driven rebasing, and non-emergency-transport "
            "medical-necessity audits and recoupment."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicare Ambulance Fee Schedule (SSA §1834(l))",
                 "Sets the base rates, mileage, and level-of-service definitions "
                 "that govern the largest single payer — the core price.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/ambulance"),
            Rule("Ground Ambulance Data Collection System (GADCS)",
                 "Mandatory cost-data collection from a rotating sample of "
                 "providers; the analytic basis for a possible rate rebasing.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/ambulance/ground-ambulance-data-collection-system"),
            Rule("No Surprises Act — ground-ambulance carve-out",
                 "Ground ambulance is excluded from federal OON balance-billing "
                 "limits; an advisory committee has urged extending protection.",
                 "https://www.cms.gov/nosurprises"),
            Rule("State EMS licensure + exclusive operating areas / COPCN",
                 "State EMS offices license providers and localities award "
                 "franchise 911 territories — the contract is the moat.",
                 None),
            Rule("Anti-Kickback + non-emergency-transport fraud enforcement",
                 "OIG/DOJ have repeatedly prosecuted non-emergency (esp. "
                 "dialysis) transport fraud and kickbacks — a compliance flashpoint.",
                 "https://oig.hhs.gov/reports-and-publications/all-reports-and-publications/"),
        ],
        policy_watch=[
            "State balance-billing laws closing the NSA ground-ambulance gap",
            "Medicare add-on extender reauthorization (the recurring cliff)",
            "GADCS results and any move toward AFS rate rebasing",
            "Treat-in-place / community-paramedicine payment pathways",
            "Medicaid ambulance rate adequacy and supplemental-payment programs",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "One of the most fragmented verticals in healthcare: thousands of "
            "providers split across municipal fire-based EMS, hospital-based "
            "transport, county/district services, private for-profits, "
            "nonprofits, and volunteer corps. Structure is set locality by "
            "locality through the exclusive-operating-area franchise, so "
            "'market share' is really a portfolio of individual municipal "
            "contracts. No national facility file is vendored, so geography is "
            "honestly omitted; the corpus deal history stands in its place below."),
        hhi_or_share=(
            "No meaningful national concentration — the relevant unit is the "
            "single 911 contract or catchment. Even the largest operator holds a "
            "small share of a market defined by local franchises."),
        consolidation=(
            "Private roll-up has been active but structurally hard: Global "
            "Medical Response (KKR) assembled AMR and the air platforms into the "
            "scaled national operator, and Priority, Falck, and Acadian expanded "
            "regionally. But the model is capital- and labor-intensive with a "
            "brutal payer mix, and GMR itself had to restructure a heavy debt "
            "load — a caution on over-levering a low-net-yield business."),
        pe_activity=(
            "The marquee thesis was GMR (KKR): consolidate fragmented private "
            "ground and air transport, professionalize billing, and capture the "
            "interfacility book. It scaled — and then had to restructure debt in "
            "the higher-rate environment. Sponsors weigh the fragmentation "
            "tailwind against the payer-mix and labor headwinds and the "
            "balance-billing policy overhang; the durable value is in the "
            "scheduled/interfacility book, not the 911 franchise."),
        notable_players=[
            "Global Medical Response / AMR (KKR)", "Falck",
            "Priority Ambulance", "Acadian Ambulance",
            "Municipal fire-based EMS", "Hospital-based transport",
            "Regional / county services",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Net collection rate (911 book)", "~30-45% of billed",
                "The defining metric — payer mix and self-pay share crush "
                "realization on emergency transports."),
            Kpi("Unit-hour utilization (UHU)", "~0.3-0.5",
                "Transports per staffed ambulance-hour — the true efficiency and "
                "labor-productivity lever."),
            Kpi("Cost per transport", "labor-dominated",
                "Crew (2 per unit), vehicle, fuel, and dispatch; scale spreads "
                "dispatch and fleet overhead."),
            Kpi("Response-time compliance", "contractual SLA",
                "911 contracts impose penalties for missed response times — a "
                "staffing-cost and franchise-risk driver."),
            Kpi("Payer mix (self-pay share)", "the value swing",
                "Self-pay/uninsured and Medicaid share on 911 is the biggest "
                "determinant of realization."),
            Kpi("Non-emergency / interfacility mix", "the margin book",
                "Higher-yield scheduled transport carries the profit that "
                "subsidizes the 911 franchise."),
        ],
        margin_profile=(
            "Ground ambulance is a labor- and capital-intensive fixed-cost "
            "business (two-person crews, vehicles, dispatch, deployment posts) "
            "with a punishing top line: on 911 volume, net collection is a "
            "fraction of billed charges because of the Medicare/Medicaid/self-pay "
            "mix. Margin is therefore made on unit-hour utilization, on the "
            "higher-yield interfacility/non-emergency book, and — where state "
            "law still allows — on balance-billing the OON commercial balance. "
            "Municipal 911 contracts are frequently run at or below breakeven to "
            "hold the franchise, with the scheduled book carrying the P&L."),
    ),
    risks=[
        Risk("Payer mix / low net collection on 911 volume", "High",
             "Medicare/Medicaid/self-pay-heavy emergency book yields a fraction "
             "of billed charges — the structural ceiling on margin."),
        Risk("Balance-billing regulation closing the NSA carve-out", "High",
             "State laws (and a possible federal fix) that limit OON "
             "balance-billing remove a real, politically exposed margin source."),
        Risk("Paramedic / EMT shortage and wage inflation", "High",
             "Labor is the binding constraint; wages and turnover cap unit-hour "
             "utilization, growth, and response-time compliance."),
        Risk("Medicare add-on extender / GADCS rate risk", "Medium",
             "Temporary rural/urban add-ons must be reauthorized, and GADCS cost "
             "data could drive an unfavorable rate rebasing."),
        Risk("Non-emergency-transport fraud/audit exposure", "Medium",
             "OIG/DOJ scrutiny of dialysis and non-emergency BLS transport, with "
             "recoupment and exclusion risk."),
        Risk("Over-leverage on a low-net-yield business", "Medium",
             "The GMR debt restructuring is the caution — thin cash conversion "
             "does not carry aggressive leverage."),
    ],
    diligence_questions=[
        "What is the net collection rate by payer and by book (911 vs "
        "interfacility vs non-emergency)?",
        "What share of revenue and margin depends on balance-billing, and what "
        "is the state-law exposure to that closing?",
        "What is the mix of contracted municipal 911 versus higher-yield "
        "scheduled transport, and how profitable is each?",
        "What are the 911 contract terms — subsidy, response-time penalties, "
        "term, and renewal/competition risk?",
        "What is unit-hour utilization, and how is it constrained by paramedic/EMT "
        "staffing and wages?",
        "What is the exposure to Medicare add-on extenders and to a GADCS-driven "
        "rate rebasing?",
        "What is the non-emergency-transport compliance and audit history "
        "(medical necessity, dialysis BLS)?",
        "What is the leverage and cash-conversion profile against this payer mix?",
    ],
    insider_lens=[
        "You do not choose your patients when you hold the 911 contract — the "
        "payer mix comes with the territory, and it is the worst in healthcare. "
        "Underwrite net collection, not billed charges; the gap is enormous.",
        "The No Surprises Act carve-out is the quiet margin story. Ground "
        "ambulance can still balance-bill the OON commercial balance where state "
        "law allows — a real profit source that is one statute away from "
        "disappearing, and states are moving.",
        "It is two businesses: the 911 franchise you bid at or below cost to win, "
        "and the interfacility/non-emergency book you actually make money on. A "
        "target that is all 911 and no scheduled transport is a subsidy machine, "
        "not a margin machine.",
        "Labor is the ceiling, not demand. The paramedic/EMT shortage caps how "
        "many units you can staff and how high unit-hour utilization can run — "
        "and response-time penalties turn understaffing into contract risk.",
        "The Medicare add-ons are a perennial extender. A material slice of the "
        "rate base rides on Congress reauthorizing rural/urban bonuses on "
        "schedule — model the cliff, and watch GADCS for the rebasing that could "
        "reset the whole fee schedule.",
    ],
    connections=default_connections(
        "ems",
        deals_sector="ems",
        extra_pages=[
            ("/diligence/tam-sam?template=ems",
             "EMS deep-dive — sizing build + realized-deal history"),
        ],
        connectors=[
            ("cms_open_data_catalog",
             "CMS Open Data — ambulance fee schedule & utilization"),
            ("npi_provider",
             "NPI Registry — ambulance suppliers & EMS agencies (taxonomy 341600000X)"),
            ("medicaid_data_benefits_covered_nonemergency_medical_transportation",
             "Medicaid — non-emergency medical transportation benefit coverage"),
            ("oig_leie",
             "OIG LEIE — excluded entities (non-emergency-transport fraud screen)"),
        ],
    ),
    sources=[
        Source("GAO — Ambulance Services / ground-ambulance cost and payment "
               "reports", "GOV", "https://www.gao.gov/"),
        Source("MedPAC — ambulance services analyses", "GOV",
               "https://www.medpac.gov/"),
        Source("CMS Ambulance Fee Schedule + Ground Ambulance Data Collection "
               "System", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/ambulance"),
        Source("No Surprises Act Advisory Committee on Ground Ambulance and "
               "Patient Billing — report/recommendations", "GOV",
               "https://www.cms.gov/nosurprises"),
        Source("HHS Office of Inspector General — non-emergency transport fraud "
               "and vulnerability reports", "GOV",
               "https://oig.hhs.gov/reports-and-publications/all-reports-and-publications/"),
        Source("PE Desk industry deep-dive (EMS sizing) + realized-deal corpus",
               "INTERNAL", "/diligence/tam-sam?template=ems"),
    ],
    live_figures=live_figures_from_dive("ems"),
    trends=(
        "The ground-ambulance trajectory is defined by a widening gap between "
        "cost and realization. Call volume rises with population and aging, but "
        "the 911 payer mix — Medicare, Medicaid, and self-pay — keeps net "
        "collection low, while the paramedic/EMT shortage and post-2021 wage "
        "inflation push cost per transport up and cap unit-hour utilization. "
        "Two policy vectors bracket the outlook. On the downside, ground "
        "ambulance's carve-out from the No Surprises Act — long a margin cushion "
        "via balance-billing — is being closed state by state, and a federal "
        "advisory committee has recommended extending protections. On the rate "
        "side, the temporary Medicare add-ons keep riding short-term extenders "
        "while the new Ground Ambulance Data Collection System assembles the "
        "cost basis that could rebase the fee schedule. Consolidation continues "
        "but has proven fragile — Global Medical Response scaled the roll-up and "
        "then restructured its debt — so the durable value has shifted toward "
        "the higher-yield interfacility and non-emergency book and away from the "
        "money-losing 911 franchise."),
    growth_levers=[
        GrowthLever(
            "Call-volume growth (aging + population)",
            "Emergency and interfacility transport demand rises with the 65+ "
            "population and hospital throughput — structural, non-discretionary.",
            "+2-3%/yr volume", "GOV"),
        GrowthLever(
            "Medicare AFS updates + add-on extenders",
            "Base rates and the temporary rural/urban add-ons step the fee "
            "schedule up when Congress reauthorizes them.",
            "+2-3%/yr rate", "GOV"),
        GrowthLever(
            "Interfacility / non-emergency mix shift",
            "Growing the higher-yield scheduled and interfacility book lifts "
            "blended realization above the 911 baseline.",
            "margin-accretive mix", "ILLUSTRATIVE"),
        GrowthLever(
            "Community paramedicine / treat-in-place",
            "New payment pathways for mobile integrated health and treat-in-place "
            "add reimbursable volume off the transport-only model.",
            "emerging, thin pay", "ILLUSTRATIVE"),
        GrowthLever(
            "Labor cost inflation (a negative lever)",
            "Paramedic/EMT wages and turnover cap unit-hour utilization and raise "
            "cost per transport faster than rate updates.",
            "margin drag", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="911 call volume + interfacility transport (aging × throughput)",
        analysis=(
            "Demand has two engines. The 911 book grows with population and "
            "aging: more people, older and sicker, generate more emergency "
            "responses — non-discretionary volume that comes bundled with the "
            "exclusive-operating-area franchise and its unforgiving payer mix. "
            "The interfacility/non-emergency book grows with hospital "
            "throughput and post-acute activity: discharges, dialysis runs, and "
            "facility-to-facility transfers scale with the acute and post-acute "
            "system around the provider. The key asymmetry is economic, not "
            "volumetric — 911 volume is plentiful but low-yield, while the "
            "scheduled/interfacility volume is scarcer but carries the margin. "
            "Growth that matters is therefore mix-weighted: winning more "
            "interfacility contracts is worth far more per transport than "
            "adding 911 call volume."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Crew labor (paramedics, EMTs, dispatch)",
            "~50-60% of cost",
            "Two-person crews plus 24/7 deployment and dispatch; the binding "
            "constraint on capacity and the driver of the post-2021 cost surge.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Fleet, fuel & equipment",
            "~15-20% of cost",
            "Ambulance acquisition and maintenance, fuel, and onboard medical "
            "equipment — capital-intensive and inflation-exposed.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Deployment / readiness (posts, standby)",
            "~10-15% of cost",
            "Maintaining coverage and response-time SLAs requires paid standby "
            "capacity independent of billable transports.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Billing, collections & bad debt",
            "~8-12% of cost",
            "Complex payer billing plus heavy self-pay collections and write-offs "
            "— the cost of a low-net-yield revenue base.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Compliance, medical direction & insurance",
            "~5-8% of cost",
            "Medical oversight, licensure/compliance, and liability coverage on "
            "an emergency-services risk profile.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=None,
    cms_trend=None,
)

register(REPORT)
