"""Crisis Services — the behavioral-health crisis continuum (988 / mobile / beds).

Deals-only deep-dive (SAMHSA crisis-program rosters are not vendored, so
geography is omitted rather than fabricated). Consumes
``crisis_services_deep_dive()`` for SOURCED corpus figures where the corpus
tags them. This is an emerging, braided-funding vertical, so the sections are
authored around the 'Crisis Now' model (someone to talk to / respond / a place
to go), the 988 build-out, the ARPA mobile-crisis Medicaid match, and the core
economic problem — a payer-agnostic mandate on a fragmented public-funding base.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="crisis_services",
    name="Crisis Services",
    care_setting="Behavioral",
    naics="623220",
    one_line_def=(
        "The behavioral-health crisis continuum — the 988 Suicide & Crisis "
        "Lifeline (someone to talk to), mobile crisis teams (someone to "
        "respond), and crisis receiving / stabilization facilities and 23-hour "
        "observation (a place to go) — built to divert psychiatric emergencies "
        "from 911, jails, and emergency-department boarding, and funded by a "
        "braid of Medicaid, state 988 fees, and federal block grants."),
    tam_headline=TamHeadline(
        value=8.0, unit="$B", growth_pct=12.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "US crisis-services spending is modeled at ~$6-10B of braided "
            "public funding (Medicaid + state 988 telecom fees + SAMHSA block "
            "grants + local), scaling fast off the 988 launch; the volume "
            "anchor is a GOV figure (988 handled ~5M+ contacts in its first "
            "year). Growth is the modeled composite of 988 adoption (+8.0%), "
            "Medicaid mobile-crisis expansion (+3.0%), and facility build-out "
            "(+1.0%)."),
    ),
    executive_summary=[
        "Crisis services are organized by the 'Crisis Now' model: someone to "
        "talk to (988 call/text/chat centers), someone to respond (mobile "
        "crisis teams), and a place to go (crisis receiving and stabilization "
        "facilities). The investable thesis is the third leg — facility-based "
        "stabilization — because it carries real assets and Medicaid billing; "
        "988 and mobile are largely grant- and Medicaid-funded public "
        "infrastructure.",
        "The core economic problem is payer-agnostic access. Crisis programs "
        "must serve everyone regardless of insurance — that is the mandate — so "
        "the uninsured/uncompensated load is high and sustainability depends on "
        "braiding Medicaid, state 988 telecom fees, SAMHSA block grants, and "
        "local dollars into a durable rate. No single payer covers the cost.",
        "The value case is downstream cost offset. A crisis continuum diverts "
        "psychiatric patients from 911, emergency-department boarding, "
        "inpatient psych beds, and jails — so payers and states fund it as an "
        "avoided-cost play, which makes the economics a policy argument, not a "
        "fee schedule.",
        "988 (live July 2022) is the demand catalyst and the funding lever. It "
        "created a national front door that surfaced latent crisis volume, and "
        "it gave states authority to add a 988 fee to phone bills — a dedicated, "
        "growing funding stream that is uneven state to state.",
        "It is a nonprofit/quasi-public field with a thin but real private "
        "layer. Connections Health Solutions is the marquee PE-backed crisis-"
        "facility operator; RI International originated the model; Vibrant "
        "administers 988. The whitespace is scaling the crisis-receiving-"
        "facility asset where Medicaid and state funding can sustain it.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Someone to talk to — 988 call/text/chat center triage and de-"
            "escalation (a large share resolve by phone)",
            "Someone to respond — mobile crisis team dispatch to the person in "
            "the community (police-alternative response)",
            "A place to go — crisis receiving center / 23-hour observation "
            "('no-wrong-door', no-refusal admission)",
            "Short-term crisis stabilization (sub-acute, typically <7 days)",
            "Warm hand-off to ongoing outpatient / CCBHC / SUD treatment",
            "Follow-up / caring contacts and care coordination",
            "Funding reconciliation across Medicaid, 988 fees, block grants, "
            "and local contracts",
        ],
        sites_of_care=[
            "988 crisis call/text/chat center (in-state answer point)",
            "Mobile crisis team (community response; police diversion)",
            "Crisis receiving / stabilization facility ('living room' model, "
            "no-wrong-door)",
            "23-hour crisis observation / EmPATH-style unit",
            "Short-term residential crisis / sub-acute stabilization beds",
            "Emergency department (the setting crisis services exist to divert "
            "FROM — psychiatric boarding)",
        ],
        money_flow=(
            "Crisis funding is braided rather than billed to a single payer. "
            "The 988 Lifeline is funded by SAMHSA grants plus state 988 "
            "surcharges (states may add a fee to telecom bills, as the "
            "designation act authorized), so the call layer is largely public "
            "infrastructure, not fee-for-service. Mobile crisis increasingly "
            "bills Medicaid — the American Rescue Plan Act created a state-plan "
            "option with an enhanced federal match for qualifying community "
            "mobile-crisis intervention — while also drawing on SAMHSA Mental "
            "Health Block Grant crisis set-asides and local government "
            "contracts. Facility-based crisis stabilization is where real "
            "third-party revenue concentrates: Medicaid pays per-diem or bundled "
            "rates for crisis-stabilization and 23-hour observation, sometimes "
            "inside a CCBHC's prospective payment, supplemented by state and "
            "county dollars for the uninsured. Because programs must accept "
            "everyone regardless of coverage, the uncompensated-care load is "
            "structural, and financial viability depends on assembling Medicaid "
            "rates, 988 fees, block grants, and local contracts into a rate that "
            "covers a fixed, always-on capacity."),
        key_players=(
            "A largely nonprofit and quasi-public field. RI International "
            "pioneered the crisis-receiving 'Crisis Now' model; Connections "
            "Health Solutions is the leading (growth-equity-backed) operator of "
            "high-volume crisis facilities; Vibrant Emotional Health "
            "administers the national 988 Lifeline; Solari, Behavioral Health "
            "Link, and ProtoCall provide crisis-line and technology "
            "infrastructure. Community mental-health centers and CCBHCs operate "
            "much of the local mobile and stabilization capacity, with states "
            "and counties as the contracting counterparties. The private, "
            "acquirable layer is thin and concentrated in facility operators and "
            "crisis-tech vendors."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("US crisis-services spending (modeled, braided funding)",
                    "~$6-10B", "ILLUSTRATIVE · Medicaid + 988 fees + block "
                    "grants + local"),
            Segment("988 Lifeline contacts (first year)", "~5M+",
                    "GOV · SAMHSA / Vibrant 988 performance data"),
            Segment("Crisis-facility / stabilization segment",
                    "the investable core",
                    "ILLUSTRATIVE · service-model structure, directional"),
            Segment("ED psychiatric boarding (the diverted cost)",
                    "large avoidable spend",
                    "ACADEMIC · ED boarding literature, directional"),
            Segment("States with a 988 telecom fee", "a growing minority",
                    "GOV · state 988 funding legislation"),
        ],
        growth_drivers=[
            "988 adoption + awareness surfacing latent volume ~8.0%/yr",
            "Medicaid mobile-crisis option (ARPA enhanced match) ~3.0%/yr",
            "Crisis-facility build-out (state crisis-continuum plans) ~1.0%/yr",
            "ED-boarding + jail-diversion cost pressure funding the model",
            "State 988 telecom-fee enactment creating dedicated funding",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicaid / MCO": 0.45,
            "State / local government + 988 fees": 0.30,
            "Federal block grants (SAMHSA)": 0.15,
            "Commercial / Medicare / other": 0.10,
        },
        rate_mechanics=[
            "988 funding — SAMHSA grants plus state 988 telecom surcharges "
            "(authorized by the National Suicide Hotline Designation Act); the "
            "call layer is public infrastructure, not fee-for-service.",
            "Medicaid mobile-crisis option — the ARPA §9813 state-plan option "
            "provided an enhanced (85%) federal match for qualifying community "
            "mobile-crisis intervention for a limited window, seeding Medicaid "
            "billing for mobile response.",
            "Crisis-stabilization / 23-hour observation — Medicaid per-diem or "
            "bundled facility rates, sometimes folded into a CCBHC prospective "
            "payment; supplemented by state/county funds for the uninsured.",
            "SAMHSA Mental Health Block Grant crisis set-aside — a required "
            "percentage of the block grant directed to crisis services.",
            "Local government contracts — county/city funding for mobile teams "
            "and stabilization as a 911/jail-diversion investment.",
            "Payer-agnostic access mandate — programs serve everyone regardless "
            "of coverage, so uncompensated care is a structural line the funding "
            "braid must cover.",
        ],
        reimbursement_risk=(
            "The defining risk is funding durability rather than rate level. "
            "Because crisis programs must serve everyone regardless of "
            "insurance, no single payer covers the cost, and viability rests on "
            "braiding Medicaid, state 988 telecom fees, SAMHSA block grants, and "
            "local contracts — a stack in which several strands are appropriation- "
            "or grant-dependent and can shift with budget cycles. The ARPA "
            "enhanced Medicaid match for mobile crisis was time-limited, so the "
            "steady-state Medicaid rate matters more than the launch incentive; "
            "988 telecom-fee adoption is uneven across states, leaving call "
            "centers unevenly funded; and block-grant dollars are finite and "
            "contested. The economic case for sustained funding is the "
            "downstream offset — diverting psychiatric patients from ED "
            "boarding, inpatient beds, and jails — but that is a policy argument "
            "a state has to keep choosing to fund, not a claim a provider can "
            "bill. For an investor, the durable revenue sits in facility-based "
            "Medicaid stabilization; the call and mobile layers are closer to "
            "publicly-funded infrastructure."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("National Suicide Hotline Designation Act (988)",
                 "Designated 988 as the national behavioral-crisis number (live "
                 "July 2022) and authorized states to levy 988 telecom fees — "
                 "the demand catalyst and the dedicated-funding lever.",
                 "https://www.fcc.gov/988-suicide-and-crisis-lifeline"),
            Rule("ARPA §9813 — Medicaid community mobile-crisis option",
                 "Created a state-plan option with a time-limited enhanced "
                 "federal match for qualifying mobile-crisis intervention — the "
                 "seed of Medicaid-billed mobile response.",
                 "https://www.medicaid.gov/medicaid/home-community-based-services/guidance/section-9813-of-the-american-rescue-plan-act-of-2021"),
            Rule("SAMHSA National Guidelines for Behavioral Health Crisis Care",
                 "Defines the 'Crisis Now' continuum (call / mobile / "
                 "facility) and best-practice standards states build toward.",
                 "https://www.samhsa.gov/find-help/988"),
            Rule("EMTALA + IMD exclusion (the ED-boarding backdrop)",
                 "EMTALA obligates EDs to screen/stabilize psychiatric "
                 "emergencies while the IMD exclusion limits adult Medicaid "
                 "psych-bed funding — the boarding problem crisis services "
                 "divert.",
                 "https://www.cms.gov/medicare/regulations-guidance/legislation/emergency-medical-treatment-labor-act"),
            Rule("SAMHSA Mental Health Block Grant crisis set-aside",
                 "Requires states to direct a portion of the block grant to "
                 "crisis services — a funding-braid strand and a compliance "
                 "condition.",
                 "https://www.samhsa.gov/grants/block-grants"),
        ],
        policy_watch=[
            "State 988 telecom-fee enactment and the funding it generates",
            "Steady-state (post-ARPA) Medicaid mobile-crisis rates by state",
            "State crisis-continuum plans and crisis-facility build-out",
            "Payer-obligation rules (commercial coverage of crisis services)",
            "Jail-diversion / police-alternative-response mandates",
            "CCBHC crisis-scope funding and expansion",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Fragmented and mostly public/nonprofit. Crisis capacity is built "
            "locally by community mental-health centers, CCBHCs, and regional "
            "nonprofits under state and county contracts, with a thin layer of "
            "specialized facility operators and crisis-line/technology vendors "
            "on top. Because funding is braided and geographically uneven, the "
            "market is a patchwork of state and regional systems rather than a "
            "national provider market — which is exactly the gap a scaled "
            "facility operator aims to fill."),
        hhi_or_share=(
            "No national concentration; the field is dominated by local "
            "public/nonprofit providers with a few specialized national "
            "operators. SAMHSA crisis-program rosters are not vendored, so "
            "operator concentration is honestly not measured here — the deal "
            "corpus below is the real trading history."),
        consolidation=(
            "Early and thin. Connections Health Solutions has scaled the "
            "high-volume crisis-facility model with growth equity and is the "
            "clearest consolidation vehicle; RI International advances the model "
            "as a nonprofit; crisis-tech vendors (Solari, Behavioral Health "
            "Link) consolidate the call/dispatch layer. Most capacity remains "
            "under state/county contracts with community providers, so "
            "'consolidation' looks more like a few operators winning multi-site "
            "state contracts than classic roll-up."),
        pe_activity=(
            "Nascent. The payer-agnostic mandate and braided public funding make "
            "durable margin hard, so private capital has concentrated in the "
            "facility-based stabilization asset (where Medicaid per-diems and "
            "state funding can sustain a fixed capacity) and in crisis "
            "technology. Diligence centers on the funding braid's durability, "
            "Medicaid rate sufficiency, contract concentration with states/"
            "counties, and the credibility of the downstream-cost-offset case "
            "that justifies continued funding."),
        notable_players=[
            "Connections Health Solutions", "RI International",
            "Vibrant Emotional Health (988 administrator)", "Solari",
            "Behavioral Health Link", "ProtoCall Services",
            "CCBHCs / community mental-health centers", "Recovery Innovations",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Blended funding / episode (braided)", "program-specific",
                "Revenue is a stack of Medicaid, 988 fees, block grants, and "
                "local dollars — the braid, not a single rate, defines the "
                "economics."),
            Kpi("Uncompensated-care load", "material",
                "The payer-agnostic mandate means a structural share of care is "
                "uninsured — the number the funding braid must cover."),
            Kpi("988 call resolution rate (by phone)", "high",
                "A large share of contacts resolve without dispatch or a "
                "facility visit — the cost-leverage of the call layer."),
            Kpi("Crisis-facility throughput / length of stay",
                "<24h obs, <7d stab",
                "Fast-turn, high-throughput stabilization is the facility "
                "economic engine on a fixed always-on cost base."),
            Kpi("Downstream diversion (ED-boarding / inpatient avoided)",
                "the value metric",
                "The avoided-cost the model is funded to produce — the argument "
                "that sustains the rate."),
            Kpi("Operating margin", "thin / funding-dependent (illustrative)",
                "A function of the braid's completeness; facility Medicaid "
                "billing is the most margin-durable strand."),
        ],
        margin_profile=(
            "Crisis-services economics are governed by a fixed, always-on "
            "capacity meeting a payer-agnostic access mandate — a combination "
            "that makes margin a funding-completeness question rather than a "
            "utilization one. A 988 center or mobile team must be staffed to "
            "answer whatever comes, and a crisis-receiving facility must accept "
            "no-refusal admissions, so the cost base is fixed and the "
            "uncompensated-care load is structural. Financial viability is "
            "achieved by braiding revenue: Medicaid (the most durable, "
            "especially for facility stabilization), state 988 telecom fees, "
            "SAMHSA block grants, and local government contracts. The strand "
            "with the clearest third-party-billing margin is facility-based "
            "Medicaid crisis stabilization and 23-hour observation, where "
            "high-throughput, short-stay care spreads the fixed cost; the call "
            "and mobile layers behave more like publicly-funded infrastructure "
            "whose 'return' is the downstream cost avoided. The durable operator "
            "is the one that has assembled a complete, contractually-secured "
            "funding braid and can evidence the diversion that keeps states "
            "paying."),
    ),
    risks=[
        Risk("Funding-braid durability (grant/appropriation dependence)",
             "High",
             "Several revenue strands are grant- or appropriation-based and "
             "shift with budget cycles; no single payer covers the cost."),
        Risk("Payer-agnostic mandate → uncompensated care", "High",
             "Serving everyone regardless of coverage is the mission and the "
             "structural margin problem."),
        Risk("Post-ARPA Medicaid mobile-crisis rate sufficiency", "Medium",
             "The enhanced federal match was time-limited; steady-state "
             "Medicaid rates must sustain mobile response."),
        Risk("Uneven state 988 telecom-fee adoption", "Medium",
             "Call-center funding varies widely because many states have not "
             "enacted a dedicated 988 fee."),
        Risk("Workforce (crisis clinicians, peers, mobile responders)",
             "Medium",
             "Always-on staffing of a scarce behavioral workforce constrains "
             "capacity and drives cost."),
        Risk("Contract concentration with states/counties", "Medium",
             "Revenue can concentrate in a few government contracts subject to "
             "re-bid and political change."),
    ],
    diligence_questions=[
        "What is the funding braid by program — the mix of Medicaid, 988 fees, "
        "block grants, and local contracts — and how secured/durable is each "
        "strand?",
        "What is the uncompensated-care load, and how is it covered?",
        "For facility stabilization: what are the Medicaid per-diem/bundled "
        "rates, throughput, and length of stay?",
        "What is the post-ARPA steady-state Medicaid mobile-crisis rate in each "
        "operating state?",
        "How concentrated is revenue in individual state/county contracts, and "
        "what is the re-bid schedule?",
        "What downstream diversion (ED boarding, inpatient, jail) can the "
        "program actually evidence to justify continued funding?",
        "What is the crisis-workforce staffing model and vacancy rate for "
        "always-on capacity?",
        "Which operating states have enacted a 988 telecom fee, and what does it "
        "fund?",
    ],
    insider_lens=[
        "You cannot bill your way to margin when you must take everyone. The "
        "payer-agnostic access mandate is the mission and the financial trap at "
        "once — the whole skill is braiding Medicaid, 988 fees, block grants, "
        "and local dollars into a rate that covers a fixed, always-on capacity. "
        "Underwrite the braid, not a fee schedule.",
        "Of the three legs, only one really carries an asset and a bill. 988 "
        "and mobile response are mostly publicly-funded infrastructure; the "
        "crisis-receiving facility is where Medicaid per-diems, real estate, and "
        "throughput economics live — which is why the private capital that "
        "exists (Connections Health Solutions) is in facilities.",
        "The product is avoided cost, and the customer is the state. Crisis "
        "services are funded because they divert psychiatric patients from ED "
        "boarding, inpatient beds, and jail — so the economics are a policy "
        "argument a state keeps choosing to fund, and the operator's job is to "
        "evidence the diversion that keeps the money flowing.",
        "988 did two things at once: it surfaced latent demand and it created a "
        "funding lever. The national number generated a wave of contacts, and "
        "the authority to add a 988 fee to phone bills gave states a dedicated "
        "revenue source — but adoption is uneven, so the same program is "
        "well-funded in one state and starved in the next.",
        "The ARPA match was a starter, not the meal. The 85% enhanced Medicaid "
        "match for mobile crisis was time-limited; the deals that last are "
        "priced on the steady-state Medicaid rate a state will actually pay "
        "after the incentive lapses — not on the launch subsidy.",
        "Throughput is the facility's margin. A crisis-receiving center runs on "
        "no-wrong-door, sub-24-hour observation and short stabilization stays; "
        "the faster it safely turns people to the right next setting, the more a "
        "fixed always-on cost base earns — the opposite of a length-of-stay "
        "business.",
    ],
    connections=default_connections(
        "crisis_services",
        deals_sector="behavioral_health",
        extra_pages=[
            ("/industry/crisis_services",
             "Industry deep-dive — crisis-services deal history + structure"),
        ],
        connectors=[
            ("cdc_data_injury_violence_county",
             "CDC injury/violence (suicide & self-harm) by county — the crisis "
             "demand curve"),
            ("cdc_data_vsrr_drug_overdose",
             "CDC provisional overdose deaths — overlapping SUD-crisis demand"),
            ("medicaid_data_enrollment_monthly",
             "Medicaid enrollment — the durable payer strand for facility "
             "stabilization"),
            ("hrsa_data_hpsa_mental_health",
             "HRSA Mental-Health HPSAs — shortage geography the crisis system "
             "backstops"),
            ("cdc_data_places_county",
             "CDC PLACES — county mental-distress prevalence as a demand proxy"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded providers (integrity screen)"),
        ],
    ),
    sources=[
        Source("SAMHSA — 988 Suicide & Crisis Lifeline performance data and "
               "National Guidelines for Behavioral Health Crisis Care", "GOV",
               "https://www.samhsa.gov/find-help/988"),
        Source("FCC — 988 Suicide & Crisis Lifeline (designation + state fees)",
               "GOV", "https://www.fcc.gov/988-suicide-and-crisis-lifeline"),
        Source("Medicaid — ARPA §9813 community mobile-crisis intervention "
               "state-plan option", "GOV",
               "https://www.medicaid.gov/medicaid/home-community-based-services/guidance/section-9813-of-the-american-rescue-plan-act-of-2021"),
        Source("Crisis Now / National Association of State Mental Health "
               "Program Directors (NASMHPD) — crisis-continuum model", "INDUSTRY",
               "https://crisisnow.com/"),
        Source("Health Affairs / academic literature on ED psychiatric "
               "boarding and crisis-care cost offset", "ACADEMIC",
               "https://www.healthaffairs.org/"),
        Source("PE Desk industry deep-dive (crisis services) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=crisis_services"),
    ],
    live_figures=live_figures_from_dive("crisis_services"),
    trends=(
        "Crisis services are the newest investable corner of behavioral health, "
        "and their trajectory is being written in real time by policy. For "
        "decades, psychiatric emergencies defaulted to 911, emergency "
        "departments, and jails — an expensive, ineffective backstop epitomized "
        "by ED 'boarding,' in which psychiatric patients wait days for a bed. "
        "The response coalesced around the 'Crisis Now' model: someone to talk "
        "to, someone to respond, a place to go. Three policy moves then "
        "accelerated it. The launch of 988 in July 2022 created a national "
        "front door that surfaced latent demand and — crucially — authorized "
        "states to fund call centers through telecom fees. The American Rescue "
        "Plan Act added a time-limited enhanced Medicaid match for community "
        "mobile-crisis teams, seeding Medicaid billing for the response layer. "
        "And SAMHSA guidelines plus block-grant crisis set-asides pushed states "
        "to build the continuum. The result is fast volume growth on a still-"
        "immature funding base: the economics remain a braid of Medicaid, 988 "
        "fees, block grants, and local contracts against a payer-agnostic "
        "mandate, so sustainability — not demand — is the open question. The "
        "forward story is the durability of that braid after the ARPA incentive "
        "lapses, the unevenness of state 988-fee adoption, and the maturation of "
        "facility-based stabilization (Connections Health Solutions the marquee "
        "operator) into the one strand with genuinely investable, Medicaid-"
        "billable economics."),
    growth_levers=[
        GrowthLever(
            "988 adoption + awareness",
            "The national crisis line surfaced large latent contact volume "
            "(~5M+ in year one) and normalized reaching out — the primary "
            "demand catalyst.",
            "+8.0%/yr contacts", "GOV"),
        GrowthLever(
            "Medicaid mobile-crisis expansion",
            "The ARPA state-plan option seeded Medicaid billing for mobile "
            "response; steady-state Medicaid rates carry it forward.",
            "+3.0%/yr covered response", "GOV"),
        GrowthLever(
            "Crisis-facility build-out",
            "State crisis-continuum plans fund crisis-receiving and "
            "stabilization capacity — the investable, asset-backed leg.",
            "+1.0%/yr capacity", "ILLUSTRATIVE"),
        GrowthLever(
            "ED-boarding + jail-diversion cost pressure",
            "The avoided cost of psychiatric boarding and incarceration is the "
            "argument that pulls state and payer funding into the model.",
            "funding pull", "ACADEMIC"),
        GrowthLever(
            "State 988 telecom-fee enactment",
            "Each state that levies a 988 fee creates a dedicated, recurring "
            "funding stream for the call layer.",
            "+ dedicated funding", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Behavioral-crisis incidence surfaced by 988, backstopping ED "
               "boarding",
        analysis=(
            "The demand base is behavioral-health crisis events — suicidal and "
            "self-harm presentations, acute psychiatric decompensation, and "
            "substance-use crises — which are large, rising, and historically "
            "under-served by anything other than 911 and the emergency "
            "department. The launch of 988 in July 2022 acted as a demand "
            "catalyst rather than a demand creator: it gave a national, "
            "easy-to-reach front door to a population that previously had "
            "nowhere good to turn, and it handled several million contacts in "
            "its first year. Underlying incidence is driven by rising suicide "
            "and overdose mortality and by the same mental-health and SUD "
            "prevalence that feeds the rest of behavioral health. The crucial "
            "structural point is that this demand already exists and is already "
            "being served expensively in the wrong settings — EDs, inpatient "
            "psych beds, and jails — so the growth of crisis services is largely "
            "a diversion of existing volume into a lower-cost, purpose-built "
            "continuum. That makes the realized 'market' a function of how fast "
            "states fund and build capacity to absorb the diverted volume, not "
            "of new demand appearing."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Crisis workforce (clinicians, peers, mobile responders, "
            "call-center staff)",
            "~55-68% of cost",
            "Always-on staffing of a scarce behavioral workforce for a "
            "no-refusal, 24/7 service — the dominant, largely fixed cost.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Facilities (crisis-receiving / stabilization real estate)",
            "~10-16% of cost",
            "The fixed, always-open facility chassis for the 'place to go' leg "
            "— throughput must cover it.", "ILLUSTRATIVE"),
        CostDriver(
            "Technology (call/text/chat, dispatch, bed-registry, EHR)",
            "~6-12% of cost",
            "The routing, dispatch, and real-time-bed-availability "
            "infrastructure that makes the continuum function.", "ILLUSTRATIVE"),
        CostDriver(
            "Uncompensated care (payer-agnostic mandate)",
            "structural",
            "The cost of serving everyone regardless of coverage — not a line "
            "item so much as a load the funding braid must absorb.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Administration, compliance & reporting",
            "~5-9% of cost",
            "Multi-funder grant management, SAMHSA/Medicaid reporting, and "
            "contract compliance across a braided funding stack.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "SAMHSA crisis-program rosters are not vendored and crisis capacity is "
        "built under state- and county-specific arrangements with no single "
        "national provider file, so state geography is omitted rather than "
        "fabricated. State is nonetheless the decisive variable: whether a state "
        "has enacted a 988 telecom fee, adopted the Medicaid mobile-crisis "
        "option and at what rate, and funded a crisis-continuum plan determines "
        "whether a viable market exists there at all. The CDC injury/overdose, "
        "Medicaid-enrollment, and HRSA-shortage connectors linked below are the "
        "honest way to map crisis demand and the payer base by geography."),
)

register(REPORT)
