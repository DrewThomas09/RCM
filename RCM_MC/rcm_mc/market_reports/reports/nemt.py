"""NEMT — Non-Emergency Medical Transportation.

Deals-only deep-dive (no vendored facility file): a federally-mandated Medicaid
benefit delivered through a broker-over-fleet structure. The qualitative
sections are authored around the broker/fleet split, standing-order dialysis
economics, capitation-adequacy risk, and the OIG/DOJ fraud environment. Live
figures come from ``nemt_deep_dive()`` (the realized-deal corpus); geography is
honestly omitted (state broker contracts aren't vendored) so ``cms_trend`` and
``state_breakdown`` are left unset and the renderer shows the honest note.
"""
from __future__ import annotations

from .. import (
    Competition, CostDriver, GrowthLever, HowItWorks, Kpi, MarketReport,
    MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment, Source,
    TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="nemt",
    name="NEMT",
    care_setting="Other services",
    naics="485991",
    one_line_def=(
        "Scheduled, non-emergency rides to and from covered medical care "
        "(dialysis, behavioral health, wound care, PCP) for Medicaid — and "
        "increasingly Medicare Advantage — members who lack other "
        "transportation, delivered through transportation brokers over a "
        "fragmented fleet of livery, ambulette, and wheelchair-van operators, "
        "paid per-trip or per-member-per-month under state Medicaid."),
    tam_headline=TamHeadline(
        value=6.0, unit="$B", growth_pct=6.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "There is no single published CMS line item for NEMT spend — it is "
            "embedded in Medicaid administrative and service costs. The ~$5-8B "
            "US figure is modeled from state broker-contract values and trip "
            "volumes; growth is the modeled composite of Medicaid enrollment, "
            "chronic-disease/dialysis prevalence, and MA supplemental adoption "
            "net of post-PHE redetermination drag."),
    ),
    executive_summary=[
        "NEMT is a federally mandated Medicaid benefit (42 CFR 431.53) — states "
        "must assure transportation to and from covered care. That mandate is "
        "the demand floor, but it is under political pressure: some states have "
        "sought §1115 waivers to cap or waive it.",
        "The economic structure is the broker model. States contract a "
        "transportation broker (Modivcare, MTM, Verida, Access2Care) — usually "
        "on a per-member-per-month capitation — and the broker keeps the spread "
        "between the capitation and what it pays the fleet. These are two very "
        "different businesses: the broker (utilization arbitrage) and the "
        "transportation provider (per-trip, fleet + labor).",
        "Utilization is dominated by a small high-frequency population. "
        "Dialysis patients (three round-trips a week on standing orders) and "
        "behavioral-health/methadone runs are the bulk of trips; route density "
        "and standing-order concentration ARE the margin.",
        "Extreme fragmentation at the fleet layer — tens of thousands of small "
        "livery/ambulette operators under a handful of national brokers — makes "
        "this a classic broker-consolidator structure and a perennial OIG/DOJ "
        "fraud hotspot (phantom trips, ambulette-vs-livery upcoding, "
        "standing-order kickbacks).",
        "The growth adjacency is the Medicare Advantage supplemental "
        "transportation benefit (opened by CMS's 2019 reinterpretation) and "
        "rideshare (Uber Health, Lyft), which took the low-acuity curb-to-curb "
        "trips and left the wheelchair/stretcher and rural long-haul work — "
        "higher cost, thinner margin — to the legacy fleet.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Member/facility requests a ride (standing order or on-demand)",
            "Broker verifies Medicaid eligibility + level of service (ambulatory "
            "/ wheelchair / stretcher)",
            "Trip assigned to a network transportation provider",
            "Transport — pickup, wait, dropoff, return (round-trip)",
            "Trip verification (GPS/telephony, member signature, no-load edits)",
            "Provider claims the trip; broker reconciles vs. capitation and pays "
            "the per-trip rate",
            "State pays the broker its per-member-per-month capitation",
        ],
        sites_of_care=[
            "Member home ↔ dialysis center (the standing-order core)",
            "Member home ↔ behavioral-health / methadone clinic",
            "Member home ↔ physician office / hospital outpatient",
            "Adult day health, wound care, and facility discharge transport",
        ],
        money_flow=(
            "State Medicaid pays a broker a per-member-per-month (PMPM) "
            "capitation — or, in a shrinking set of states, a fee-for-service "
            "administrative fee — to manage the whole benefit and take "
            "utilization risk. The broker pays the transportation provider a "
            "negotiated per-trip rate that varies by level of service "
            "(ambulatory sedan < wheelchair van < non-ambulance stretcher) plus "
            "loaded-mile and wait-time add-ons. The broker's margin is the "
            "spread between capitation revenue and paid claims net of "
            "call-center/scheduling cost; the provider's margin is per-trip "
            "revenue net of driver wages, vehicle, fuel, and dead-head miles. MA "
            "plans fund the supplemental benefit either through the same brokers "
            "or directly."),
        key_players=(
            "Brokers — Modivcare (the scaled leader, formerly LogistiCare / "
            "Provado), Medical Transportation Management (MTM), Verida "
            "(formerly Southeastrans), Access2Care (a Global Medical Response "
            "company), and Veyo. Rideshare entrants — Uber Health and Lyft "
            "Healthcare in the low-acuity segment. The fleet layer is tens of "
            "thousands of local livery, ambulette, and wheelchair-van "
            "operators — the atomized pool a fleet roll-up consolidates."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Medicaid NEMT (FFS + managed-care carve-in)",
                    "the core of trip volume",
                    "ILLUSTRATIVE · modeled from state broker contracts"),
            Segment("Standing-order trips (dialysis + behavioral)",
                    "~40-60% of trip volume",
                    "ILLUSTRATIVE · trip-mix estimate"),
            Segment("Medicare Advantage supplemental transportation",
                    "the growth channel",
                    "ILLUSTRATIVE · CMS supplemental-benefit filings"),
            Segment("Facility/discharge & private-pay transport",
                    "adjacent commercial book",
                    "ILLUSTRATIVE · modeled"),
        ],
        growth_drivers=[
            "Medicaid enrollment (a near-term headwind as PHE redeterminations "
            "unwind)",
            "Chronic-disease / dialysis prevalence — the standing-order engine",
            "MA supplemental transportation adoption post-2019",
            "Rideshare expansion of the addressable low-acuity trip pool",
            "Aging + wheelchair/ambulette demand",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicaid (FFS + managed-care carve-in)": 0.72,
            "Medicare Advantage supplemental": 0.13,
            "Commercial / private-pay / facility": 0.10,
            "Other (VA, county, ADRC)": 0.05,
        },
        rate_mechanics=[
            "Broker capitation (PMPM) — the state pays a per-member-per-month "
            "rate and the broker assumes utilization risk; its P&L is the "
            "capitation minus paid claims and admin.",
            "Per-trip fee schedule by level of service — ambulatory sedan, "
            "wheelchair van, non-ambulance stretcher — plus loaded-mile add-ons "
            "and wait time. Level-of-service determination is the key revenue "
            "and fraud lever.",
            "Managed-care carve-in — many states fold NEMT into MCO capitation; "
            "the MCO then subcontracts a broker, adding a margin layer.",
            "MA supplemental benefit — since CMS's CY2019 reinterpretation of "
            "'primarily health-related,' MA plans may offer transportation as a "
            "supplemental benefit funded from rebate dollars.",
            "FFS residual (public-utility model) — some states still pay "
            "providers fee-for-service without a broker intermediary.",
            "Fraud controls — GPS/telephony trip verification, phantom-trip and "
            "no-load edits, and prior authorization for standing orders.",
        ],
        reimbursement_risk=(
            "The risk is dual. On the broker side, capitation adequacy: if "
            "utilization (especially standing-order dialysis) runs above the "
            "bid, the broker eats it — under-bid contracts have bankrupted "
            "brokers and triggered service failures and state penalties for "
            "missed or late trips. On the provider side, per-trip rates set by "
            "the broker are thin and the enforcement environment is severe: "
            "NEMT is a perennial OIG/DOJ fraud target (billing for trips not "
            "taken, upcoding a wheelchair van when the member is ambulatory, "
            "kickbacks to facilities or members for standing orders), with "
            "False Claims Act and exclusion exposure. Post-PHE redeterminations "
            "and any state move to waive or cap the NEMT mandate are structural "
            "volume risks."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicaid NEMT assurance (42 CFR 431.53 / SSA §1902(a)(4))",
                 "States must ensure necessary transportation to and from "
                 "covered providers — the mandate that is the demand floor for "
                 "the entire vertical.",
                 "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-431/subpart-A/section-431.53"),
            Rule("NEMT codified as a required benefit "
                 "(Consolidated Appropriations Act 2021 §209)",
                 "Codified NEMT in statute and directed CMS to set "
                 "driver/vehicle standards — hardening a benefit states had "
                 "tried to waive.",
                 "https://www.congress.gov/bill/116th-congress/house-bill/133"),
            Rule("MA supplemental benefit expansion (CMS CY2019 reinterpretation)",
                 "Broadened 'primarily health-related' so MA plans could fund "
                 "transportation — the commercial-payer channel beyond Medicaid.",
                 "https://www.cms.gov/newsroom/fact-sheets/2019-medicare-advantage-and-part-d-rate-announcement-and-call-letter"),
            Rule("Local-transportation Anti-Kickback safe harbor "
                 "(42 CFR 1001.952(bb))",
                 "Bounds what a provider may give a patient in free/discounted "
                 "transportation without triggering AKS — the compliance frame "
                 "for standing-order arrangements.",
                 "https://oig.hhs.gov/compliance/safe-harbor-regulations/"),
            Rule("State broker procurement & performance standards",
                 "On-time percentage, complaint rate, network adequacy, and "
                 "missed-trip penalties in each state contract — the "
                 "rebid/retention risk.",
                 None),
        ],
        policy_watch=[
            "§1115 waiver attempts to cap or waive the NEMT mandate",
            "Post-PHE Medicaid redeterminations shrinking the covered pool",
            "State rebids moving to full-risk broker capitation",
            "Rideshare regulatory treatment (driver credentialing, ADA access)",
            "DOJ/OIG NEMT fraud enforcement sweeps and CMPs",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "A barbell: a handful of national brokers over a very long tail of "
            "small local fleets. The broker layer is concentrated (Modivcare "
            "and MTM cover a large share of state lives); the "
            "transportation-provider layer is atomized — owner-operators with a "
            "few vans — which is the acquisition whitespace for a fleet "
            "roll-up. No public roster of fleet operators exists, so a precise "
            "fleet-layer HHI is honestly omitted."),
        hhi_or_share=(
            "Broker layer concentrated among ~4-5 nationals; fleet layer highly "
            "fragmented and unrostered — a precise HHI is omitted rather than "
            "fabricated."),
        consolidation=(
            "Brokers consolidated aggressively — LogistiCare + Provado became "
            "Modivcare, Southeastrans became Verida, and Veyo folded into "
            "Modivcare. Fleet roll-ups are earlier and regional. Rideshare "
            "entry reshaped the low-acuity segment and compressed broker "
            "economics on curb-to-curb trips."),
        pe_activity=(
            "PE owns the broker layer and is building regional fleet platforms. "
            "The thesis is either broker-margin durability against rideshare "
            "disruption, or fleet consolidation for standing-order route "
            "density. Quality-of-earnings turns on capitation adequacy by state "
            "contract and the OIG/fraud posture, not on headline trip growth."),
        notable_players=[
            "Modivcare", "Medical Transportation Management (MTM)",
            "Verida (Southeastrans)", "Access2Care (Global Medical Response)",
            "Veyo", "Uber Health", "Lyft Healthcare",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Revenue per trip (provider)",
                "$25-60 ambulatory / $40-90 wheelchair / $150-300 stretcher",
                "Level of service plus loaded mileage drive it; the "
                "level-of-service call is the revenue and fraud lever."),
            Kpi("PMPM capitation (broker)", "varies by state (~$3-12 PMPM)",
                "The broker's revenue base; adequacy versus actual utilization "
                "is the whole game."),
            Kpi("Trips per vehicle per day (fleet utilization)", "8-16",
                "Route density and standing orders set it; dead-head miles "
                "destroy it."),
            Kpi("Standing-order share of volume", "40-60%",
                "Dialysis/behavioral recurring trips are predictable, dense, "
                "and margin-rich — and the favorite OIG audit target."),
            Kpi("On-time performance / missed-trip rate", "contractual",
                "Missed and late trips trigger contract penalties and rebid "
                "risk; the number that loses a state."),
            Kpi("Dead-head (unloaded) mile ratio", "route-dependent",
                "Unpaid miles between trips are the fleet's single biggest "
                "margin leak."),
        ],
        margin_profile=(
            "Broker EBITDA margins are thin (mid-single to low-double digits) "
            "and swing on capitation-versus-utilization; a single mispriced "
            "state contract can erase profit. Fleet EBITDA margins are also "
            "thin and labor/fuel-driven, improved only by route density — "
            "standing orders and geographic clustering that raise "
            "trips-per-vehicle-hour and cut dead-head miles. Scale spreads the "
            "call center and dispatch but does not change the underlying "
            "capitation arithmetic. Ranges are ILLUSTRATIVE."),
    ),
    risks=[
        Risk("Capitation adequacy / underwriting loss", "High",
             "Utilization above the bid on a full-risk broker contract — "
             "especially a dialysis cluster — turns the contract underwater."),
        Risk("OIG/DOJ fraud enforcement", "High",
             "Phantom trips, level-of-service upcoding, and standing-order "
             "kickbacks carry False Claims Act and exclusion exposure."),
        Risk("Medicaid enrollment / redetermination", "High",
             "Post-PHE disenrollment shrinks the covered pool and trip base."),
        Risk("Rideshare disintermediation", "Medium",
             "Uber/Lyft compress low-acuity curb-to-curb economics and shift "
             "the mix toward higher-cost wheelchair/stretcher work."),
        Risk("Driver labor & fuel", "Medium",
             "Wage inflation and fuel volatility on thin per-trip rates cap "
             "fleet margin."),
        Risk("Mandate / political risk", "Medium",
             "§1115 waiver attempts to cap or waive the NEMT benefit remove "
             "the demand floor in specific states."),
    ],
    diligence_questions=[
        "What is the capitation-versus-paid-claims trend by state contract, and "
        "which contracts are running underwater?",
        "What is the standing-order concentration (dialysis/behavioral), and "
        "how is medical necessity documented?",
        "What is the level-of-service mix, and what is the audit/denial "
        "history on wheelchair vs. ambulatory determinations?",
        "What are the on-time/missed-trip penalties and the contract-renewal "
        "calendar — what is at rebid in the next 24 months?",
        "What is the dead-head mile ratio and route density by market?",
        "What share of trips has shifted to rideshare, and at what margin?",
        "What is the OIG/LEIE and False Claims Act history?",
        "How large and fast-growing is the MA supplemental transportation "
        "book, and how is it contracted?",
    ],
    insider_lens=[
        "It is two businesses masquerading as one. The broker arbitrages "
        "capitation against utilization; the fleet sells labor per loaded mile. "
        "Underwrite whichever one you are buying — a broker's 'margin' is an "
        "actuarial bet, a fleet's margin is route density.",
        "Dialysis standing orders are the whole ballgame and the whole risk. "
        "Three-times-a-week recurring trips are the densest, most predictable "
        "volume — and exactly what OIG audits for phantom and kickback "
        "patterns. A book that is all standing orders is efficient and exposed.",
        "Level-of-service is where the fraud lives. Billing a wheelchair van "
        "when the member could walk, or a stretcher when a wheelchair suffices, "
        "is the classic upcode — and the easiest thing for a UPIC to prove with "
        "a records pull.",
        "The capitation bid is a landmine. Win a state on an aggressive PMPM "
        "and a bad utilization year turns the contract underwater; brokers have "
        "handed back contracts, and states have penalized the service failures "
        "that follow.",
        "Rideshare took the easy trips. Uber and Lyft cream the low-acuity "
        "curb-to-curb rides and leave the wheelchair, stretcher, and rural "
        "long-haul trips — higher cost, thinner margin — to the legacy fleet. "
        "Model the mix shift, not just the volume.",
    ],
    connections=default_connections(
        "nemt",
        deals_sector="nemt",
        connectors=[
            ("medicaid_data_managed_care_by_state_2024",
             "Medicaid — managed-care penetration by state (broker carve-in map)"),
            ("medicaid_data_enrollment_monthly",
             "Medicaid — monthly enrollment (the covered-pool trend post-PHE)"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded entities (NEMT fraud/exclusion screen)"),
            ("census_acs_cbsa_profile",
             "Census ACS — senior + disability density for demand mapping"),
        ],
    ),
    sources=[
        Source("GAO — Medicaid Non-Emergency Medical Transportation reports "
               "(access, oversight, program integrity)", "GOV",
               "https://www.gao.gov/"),
        Source("CMS — Medicaid NEMT guidance and 42 CFR 431.53", "GOV",
               "https://www.medicaid.gov/medicaid/benefits/non-emergency-medical-transportation/index.html"),
        Source("HHS Office of Inspector General — NEMT vulnerability and fraud "
               "reports", "GOV",
               "https://oig.hhs.gov/reports-and-publications/all-reports-and-publications/"),
        Source("MACPAC — Medicaid transportation benefit analyses", "GOV",
               "https://www.macpac.gov/"),
        Source("Non-Emergency Medical Transportation Accreditation Commission "
               "(NEMTAC) / Medical Transportation Access Coalition — industry "
               "standards & utilization", "INDUSTRY",
               "https://nemtac.org/"),
        Source("PE Desk industry deep-dive (deals-only) + realized-deal corpus",
               "INTERNAL", "/diligence/tam-sam?template=nemt"),
    ],
    live_figures=live_figures_from_dive("nemt"),
    trends=(
        "NEMT spent the last decade consolidating at the broker layer while its "
        "economics were quietly re-drawn underneath. LogistiCare and Provado "
        "became Modivcare, Southeastrans became Verida, and Veyo folded in — a "
        "national broker oligopoly now sits over a still-atomized fleet. Three "
        "forces reshaped the trajectory. First, CMS's 2019 supplemental-benefit "
        "reinterpretation opened a Medicare Advantage channel beyond Medicaid, "
        "giving brokers and fleets a commercially-funded book. Second, rideshare "
        "(Uber Health, Lyft) entered the low-acuity curb-to-curb segment, "
        "compressing broker economics and pushing the legacy fleet toward the "
        "higher-cost wheelchair/stretcher and rural long-haul work. Third, the "
        "post-PHE Medicaid redetermination unwind removed members from the "
        "covered pool, a genuine near-term volume headwind. Underneath it all, "
        "standing-order dialysis and behavioral trips remain the dense, "
        "predictable core — and the enduring OIG/DOJ fraud target — so "
        "quality-of-earnings now centers on capitation adequacy and integrity "
        "posture, not trip growth."),
    growth_levers=[
        GrowthLever(
            "Medicaid enrollment & chronic-disease prevalence",
            "The demand base — dialysis, behavioral, and wound-care patients "
            "generate recurring trips; near-term dampened by the redetermination "
            "unwind.",
            "demand base (PHE drag)", "ILLUSTRATIVE"),
        GrowthLever(
            "MA supplemental transportation adoption",
            "CMS's 2019 rule lets MA plans fund transportation from rebate "
            "dollars — a commercially-funded channel beyond Medicaid.",
            "primary new channel", "ILLUSTRATIVE"),
        GrowthLever(
            "Standing-order route density (dialysis + behavioral)",
            "Clustering three-times-a-week recurring trips raises "
            "trips-per-vehicle-hour and cuts dead-head miles — the fleet's "
            "margin lever.",
            "margin lever", "ILLUSTRATIVE"),
        GrowthLever(
            "Rideshare partnership (asset-light low-acuity)",
            "Uber/Lyft absorb curb-to-curb trips at variable cost — expands "
            "capacity but compresses the broker spread on those legs.",
            "mix shift (double-edged)", "ILLUSTRATIVE"),
        GrowthLever(
            "Fleet roll-up / broker consolidation",
            "Consolidating the atomized fleet layer or scaling broker lives "
            "spreads dispatch and call-center fixed cost.",
            "consolidation", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Standing-order recurring trips (dialysis + behavioral health)",
        analysis=(
            "The dominant demand driver is not the on-demand ride — it is the "
            "recurring standing order. A single dialysis patient generates three "
            "round-trips a week for the life of their treatment; behavioral "
            "health and methadone maintenance add further high-frequency, "
            "predictable volume. This concentrated core drives the bulk of trip "
            "count, dictates route density (and therefore fleet margin), and "
            "grows with ESRD and chronic-disease prevalence and Medicaid "
            "enrollment. It is also the single largest program-integrity target "
            "— phantom standing-order trips and facility kickbacks are the "
            "classic fraud pattern — so the same volume that makes the P&L makes "
            "the risk. The offsetting driver is the post-PHE redetermination "
            "unwind, which removes members and trips from the covered pool."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Driver labor & benefits", "~40-50% of provider cost",
            "The dominant fleet cost; wage inflation on thin per-trip rates is "
            "the primary margin constraint.", "ILLUSTRATIVE"),
        CostDriver(
            "Vehicle, fuel & maintenance", "~20-30% of provider cost",
            "Fleet capital, fuel volatility, and upkeep — sensitive to loaded- "
            "versus dead-head mileage.", "ILLUSTRATIVE"),
        CostDriver(
            "Dispatch, scheduling & call center (broker)", "broker's core opex",
            "The broker's largest controllable cost; automation and eligibility "
            "verification are where broker margin is defended.", "ILLUSTRATIVE"),
        CostDriver(
            "Dead-head / unloaded miles", "route-dependent margin leak",
            "Unpaid miles between trips — minimized only by route density and "
            "standing-order clustering.", "ILLUSTRATIVE"),
        CostDriver(
            "Insurance & compliance", "auto liability + credentialing",
            "Commercial auto liability, driver credentialing, and trip-"
            "verification technology (GPS/telephony).", "ILLUSTRATIVE"),
    ],
)

register(REPORT)
