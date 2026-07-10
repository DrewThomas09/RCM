"""In-Depth content — Question 1: how 911, IFT and NEMT differ.

Authored 2026-07-10 from the suite's cited corpus (ift_study taxonomy,
ift_unit_economics, ift_demand_evidence, ift_growth_evidence,
ift_npi_landscape). Every evidence line carries its basis + source; company
or contract facts that are not public are marked as diligence requests.
"""
from __future__ import annotations

from .ift_indepth import Block, Evidence, QuestionDef, SubQ

_E = Evidence
_S = SubQ


_DEFINITIONS = Block(
    "q1-definitions", "Definitions and market boundaries",
    conclusion=(
        "The three markets are separated by ORIGIN/DESTINATION and BUYER, "
        "not by vehicle: 911 is scene-to-ED public emergency response bought "
        "by municipalities; IFT is facility-to-facility movement ordered and "
        "often paid by hospitals; NEMT is a Medicaid benefit moving "
        "ambulatory members between home and care, bought by state programs "
        "through brokers."),
    why_true=(
        "The practical definitions hold across every regulatory source: 911 "
        "= unscheduled response to a public emergency call, transport to the "
        "nearest appropriate ED; IFT = medically supervised movement BETWEEN "
        "healthcare facilities, ordered by a hospital or transfer center; "
        "NEMT = non-emergency transport of Medicaid members with no medical "
        "monitoring en route, a federally mandated benefit (42 CFR 431.53).",
        "Acuity, urgency and vehicle type all CROSS the boundaries — an IFT "
        "trip can be a ventilated critical-care transfer (higher acuity than "
        "most 911 calls) or a scheduled BLS discharge; what never crosses is "
        "who ordered the trip and where it begins and ends.",
        "CCT/SCT is a tier WITHIN IFT (the top of its acuity ladder, HCPCS "
        "A0434 at 3.25x the BLS relative value), not a separate market; "
        "wheelchair/stretcher-van work without medical monitoring sits in "
        "NEMT even when the passenger is leaving a facility.",
        "The consistent classification rule for ambiguous trips: classify by "
        "origin/destination + buyer first, acuity second, vehicle last. A "
        "facility-ordered stretcher discharge with monitoring is IFT; the "
        "same route as an unmonitored Medicaid livery ride is NEMT."),
    why_matters=(
        "Sizing or benchmarking IFT off the whole ambulance market (911-"
        "dominated) or off NEMT (a separate benefit with ~10x the trip count "
        "at ~1/20th the revenue per trip) is the single largest analytical "
        "error available in this space — the buyer, the economics and the "
        "operating requirements are different systems."),
    evidence=(
        _E("Medicare FFS ground ambulance: 11.3M transports, $5.3B, ~10,600 "
           "organizations (2024) — the ambulance universe IFT sits inside",
           "GOV", "MedPAC Ambulance Payment Basics, Oct 2024",
           "https://www.medpac.gov/wp-content/uploads/2024/10/MedPAC_Payment_Basics_24_ambulance_FINAL_SEC.pdf"),
        _E("Measured acute IFT base: 1.97M/yr adult ED-to-ED transfers "
           "(NEDS 2018-2022) + ~1.5M/yr inpatient interhospital transfers "
           "(NIS) — facility-origin by definition",
           "ACADEMIC", "Nikolla et al., J Emerg Med 2025; HCUP NIS",
           "https://doi.org/10.1016/j.jemermed.2025.12.020"),
        _E("NEMT is a distinct federally mandated Medicaid benefit "
           "(assurance of transportation), not an ambulance service line",
           "GOV", "42 CFR 431.53 / 440.170",
           "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-431/subpart-B/section-431.53"),
        _E("SCT (A0434) carries a 3.25 relative value vs BLS 1.00 — the "
           "acuity ladder lives INSIDE the IFT boundary",
           "GOV", "CMS Ambulance Fee Schedule RVUs (Claims Processing "
           "Manual ch.15)", ""),
    ),
    subqs=(
        _S("What is the most practical definition of 911 transportation?",
           "Unscheduled response to a public emergency call, dispatched by a "
           "PSAP, transporting from scene to the nearest appropriate ED."),
        _S("What is the most practical definition of IFT?",
           "Medically supervised patient movement BETWEEN healthcare "
           "facilities, ordered by a hospital/transfer center, scheduled or "
           "urgent, BLS through critical care."),
        _S("What is the most practical definition of NEMT?",
           "Non-emergency transport of Medicaid members to/from covered "
           "services with no medical monitoring en route — a benefit "
           "administered mostly through capitated brokers."),
        _S("Which characteristics definitively separate the three markets?",
           "Origin/destination (scene vs facility-to-facility vs "
           "home-to-service) and buyer (municipality vs hospital vs state "
           "Medicaid program)."),
        _S("Is the primary distinction origin/destination?",
           "Yes — jointly with buyer; the two travel together."),
        _S("Is the primary distinction clinical acuity?",
           "No — acuity crosses all three (a CCT transfer out-ranks most "
           "911 calls); acuity sets the tier within IFT, not the market."),
        _S("Is the primary distinction urgency?",
           "No — IFT spans scheduled to emergent; urgency drives dispatch "
           "priority, not market membership."),
        _S("Is the primary distinction dispatch channel?",
           "Partially — PSAP vs transfer-center/booking is a reliable "
           "SYMPTOM of the market, but it follows from the buyer."),
        _S("Is the primary distinction vehicle type?",
           "No — the same ambulance runs 911 and IFT; vehicle indicates "
           "capability, not market."),
        _S("Is the primary distinction medical necessity?",
           "No — necessity gates REIMBURSEMENT (42 CFR 410.40) in every "
           "market, it does not define the market."),
        _S("Is the primary distinction the buyer?",
           "Yes — municipality (911), health system (IFT), state Medicaid "
           "program/broker (NEMT)."),
        _S("Is the primary distinction the payer?",
           "Only loosely — Medicare/commercial pay across 911 and IFT; the "
           "payer distinguishes NEMT (Medicaid benefit) best."),
        _S("Which distinctions are operationally meaningful vs merely "
           "reimbursement classifications?",
           "Buyer, origin/destination, dispatch channel and readiness model "
           "are operational; HCPCS level and emergency modifiers are "
           "billing overlays on top of them."),
        _S("Can an IFT trip be urgent or clinically complex without being "
           "a 911 trip?",
           "Yes — routinely: STEMI/stroke up-transfers and ventilated CCT "
           "moves are urgent, facility-ordered, and never touch the PSAP."),
        _S("When does a low-acuity facility transfer qualify as IFT rather "
           "than NEMT?",
           "When it is facility-ordered and requires clinical supervision "
           "or a stretcher with monitoring; an unmonitored ambulatory/"
           "wheelchair ride is NEMT even from a facility door."),
        _S("Where do wheelchair, stretcher, BLS, ALS and critical-care "
           "transport fit?",
           "Wheelchair/livery → NEMT; unmonitored stretcher van → NEMT/gray "
           "zone (state-regulated); BLS/ALS/ALS2/SCT → IFT tiers when "
           "facility-ordered; the same BLS truck on a scene call → 911."),
        _S("Which trip categories create the most ambiguity?",
           "Unmonitored stretcher vans, facility-to-home discharges, "
           "dialysis round-trips (IFT by origin, NEMT-like economics), and "
           "psychiatric transfers (monitored but low-tech)."),
        _S("How should ambiguous trips be classified consistently?",
           "By the rule origin/destination + buyer first, clinical "
           "supervision second, vehicle last — applied once, suite-wide."),
        _S("What terminology avoids mixing service, vehicle and "
           "reimbursement categories?",
           "Say MARKET (911/IFT/NEMT), TIER (wheelchair/BLS/ALS/CCT), and "
           "CODE (A0426-A0434) as three separate words — never 'BLS' to "
           "mean a market or 'ambulance' to mean IFT."),
    ),
)


_CUSTOMER = Block(
    "q1-customer", "Customer and decision structure",
    conclusion=(
        "In IFT the requester (bedside/case management), the selector "
        "(transfer center or a call list), the contract-holder (supply "
        "chain), the payer (Medicare/commercial/Medicaid or the hospital "
        "itself) and the accountable party are DIFFERENT people — this "
        "separation, unique among the three markets, is what makes IFT "
        "purchasing weak and service quality sticky-bad."),
    why_true=(
        "911: the public requests, the municipality selects and contracts "
        "once (an exclusive franchise or a fire department), insurers pay — "
        "one accountable operator, politically supervised.",
        "NEMT: the member requests, the BROKER selects from a subcontracted "
        "network, the state pays a capitated broker — accountability is "
        "contractual and consolidated at the broker.",
        "IFT: a nurse or case manager requests, a transfer center or an "
        "open call list selects trip by trip, procurement may hold a "
        "preferred-provider agreement it cannot enforce, the payer is "
        "whoever the patient's coverage says — and when the trip fails, "
        "the delay lands on nursing and bed management, not on any party "
        "with contract leverage.",
        "The user–buyer–payer separation is near-total in IFT: the patient "
        "(user) almost never chooses; the hospital (buyer) frequently does "
        "not pay; the payer (insurer) never sees the service level."),
    why_matters=(
        "A provider that can collapse this separation — one accountable "
        "counterparty, contracted at the system level, with performance "
        "reporting to the people who feel the failures — is selling "
        "governance as much as transport. That is the opening for a "
        "dedicated model, and why trip-by-trip markets under-invest in "
        "capacity."),
    evidence=(
        _E("~60% of ground ambulance rides were out-of-network in 2022 — "
           "the payer is structurally distant from the service relationship",
           "SOURCED", "FAIR Health, 2023",
           "https://www.fairhealth.org/article/nearly-60-percent-of-ground-ambulance-rides-were-out-of-network-in-2022-according-to-new-fair-health-study"),
        _E("19.7% of ambulance transports collect nothing — someone other "
           "than the requester routinely absorbs the cost of the trip",
           "SOURCED", "CMS GADCS Year 1-4 appendix (Dec 2025), via AAA "
           "coverage",
           "https://ambulance.org/2025/12/09/cms-releases-new-gadcs-report/"),
        _E("Hospitals order the transfer under EMTALA appropriate-transfer "
           "duties whether or not any contracted capacity exists",
           "GOV", "42 CFR 489.24",
           "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-489/subpart-B/section-489.24"),
    ),
    subqs=(
        _S("Who is the principal customer in each market?",
           "911: the municipality. IFT: the health system. NEMT: the state "
           "Medicaid program (via its broker)."),
        _S("Who requests the transportation?",
           "911: the public. IFT: bedside nurse / case manager / transfer "
           "center. NEMT: the member (or clinic on their behalf)."),
        _S("Who selects the provider?",
           "911: the franchise/PSAP (pre-selected). IFT: transfer center or "
           "staff working a call list. NEMT: the broker's assignment "
           "algorithm."),
        _S("Who contracts with the provider?",
           "911: the city/county. IFT: hospital supply chain (when a "
           "contract exists at all). NEMT: the broker, under a state "
           "capitation."),
        _S("Who determines the appropriate modality?",
           "IFT: the ordering clinician (with uneven rules); 911: dispatch "
           "protocol (EMD); NEMT: the broker's screening script."),
        _S("Who pays the provider?",
           "911/IFT: Medicare, Medicaid, commercial, self-pay per patient "
           "coverage — plus the HOSPITAL directly for non-covered IFT; "
           "NEMT: the broker out of its capitation."),
        _S("Who bears the cost if reimbursement is denied?",
           "The provider first (19.7% of transports collect nothing), then "
           "by contract the hospital for facility-responsible trips; the "
           "patient only where balance-billing survives."),
        _S("Who is accountable when service is late or unavailable?",
           "911: the franchisee against response-time standards. NEMT: the "
           "broker against state SLAs. IFT: usually NO ONE with contractual "
           "teeth — the gap this study keeps finding."),
        _S("How often is the user different from the buyer?",
           "Almost always in all three markets — the patient rarely chooses "
           "any of these services."),
        _S("How often is the buyer different from the payer?",
           "In IFT, most of the time: hospitals order trips that Medicare/"
           "commercial plans pay for; they pay directly only for "
           "non-covered/facility-responsible trips."),
        _S("How does this separation affect service quality and purchasing?",
           "It suppresses both: the party feeling the failure (nursing, "
           "flow) is not the party holding the contract, so poor "
           "reliability persists without commercial consequence — until "
           "purchasing is centralized."),
    ),
)


_DEMAND = Block(
    "q1-demand", "Demand characteristics",
    conclusion=(
        "IFT demand is generated by facility-level care transitions — "
        "admissions, discharges, and capability gaps — which makes it "
        "substantially forecastable (by facility, hour, and modality) in a "
        "way 911 scene demand never is, and recurring in a way that "
        "resembles NEMT only at the low-acuity end."),
    why_true=(
        "The demand drivers are institutional: ED arrivals needing a higher "
        "level of care (2.4-2.8% of ~155M annual ED visits transfer), "
        "inpatient discharges to post-acute settings (~1.5M interhospital "
        "moves plus SNF/IRF/LTCH discharge legs), and recurring "
        "facility-origin treatment round-trips (dialysis, wound care).",
        "Scheduling splits demand: discharge and post-acute legs book hours "
        "ahead; ED up-transfers are urgent-but-not-emergent (minutes-to-"
        "hours); a thin critical slice (6.6% of ED transfers involve a "
        "critical procedure) needs immediate CCT readiness.",
        "Demand concentrates in daylight discharge windows (late morning "
        "through evening) and around weekday procedure schedules — the "
        "inverse of 911's flatter, weather-and-event-driven profile.",
        "When demand exceeds capacity, IFT queues INSIDE the hospital: "
        "patients board in EDs and occupy staffed beds — the cost of "
        "shortfall lands on the buyer, which is why reliability outranks "
        "price in mature purchasing."),
    why_matters=(
        "Forecastable, buyer-concentrated demand is what makes DEDICATED "
        "capacity economically possible at all: a provider can staff to a "
        "known discharge curve. It also means IFT performance is really a "
        "hospital-throughput variable, not a transportation statistic."),
    evidence=(
        _E("2.4% of US ED visits ended in transfer to another hospital "
           "(2021; 2.8% in 2018) on ~140-155M annual visits",
           "GOV", "NHAMCS / NCHS", ""),
        _E("6.6% of adult ED transfers involved at least one critical "
           "procedure — the immediate-readiness slice — and it is rising "
           "(OR 1.09/yr)",
           "ACADEMIC", "Nikolla et al., J Emerg Med 2025",
           "https://doi.org/10.1016/j.jemermed.2025.12.020"),
        _E("Rural EDs transfer at 6.2% vs 2.0% urban — geography multiplies "
           "the transfer propensity 3x",
           "ACADEMIC", "Greenwood-Ericksen et al., JAMA Network Open 2021",
           "https://doi.org/10.1001/jamanetworkopen.2021.34980"),
        _E("ED visits arriving via interfacility EMS transfer rose 15% "
           "(2017-19) and 35% (2020-22) vs the 2014-16 baseline — demand is "
           "measured to be growing",
           "ACADEMIC", "Peters et al., Am J Emerg Med 2026",
           "https://doi.org/10.1016/j.ajem.2026.04.025"),
    ),
    subqs=(
        _S("What creates demand in each market?",
           "911: community emergencies. IFT: care transitions (capability "
           "gaps, discharges, recurring treatment). NEMT: covered-service "
           "appointments for members without transport."),
        _S("How predictable is demand?",
           "IFT is the most forecastable of the three at the "
           "facility×hour×modality grain (discharge curves, procedure "
           "schedules); 911 is only statistically predictable at "
           "population scale; NEMT is booking-driven and highly known."),
        _S("How much demand can be scheduled?",
           "Most discharge/post-acute and recurring legs (booked hours to "
           "days ahead); the urgent up-transfer slice cannot — a working "
           "planning split is scheduled-majority / urgent-minority, "
           "measured per facility rather than assumed."),
        _S("How much demand is urgent but not emergent?",
           "The ED up-transfer book — minutes-to-hours windows; nationally "
           "~1.3-2.0M ED-origin transfers/yr sit in this band."),
        _S("How does demand vary by time of day and week?",
           "Discharge legs pile into late morning-evening and weekdays; "
           "urgent transfers run 24/7 but skew to ED peak hours; weekends "
           "drop scheduled volume and keep the urgent floor."),
        _S("What are the most common origins and destinations?",
           "ED→higher-acuity hospital; inpatient→SNF/IRF/LTCH; "
           "hospital→home; facility↔dialysis; hub→spoke repatriation."),
        _S("What percentage of trips are recurring?",
           "Not published as a national IFT figure — flagged; the "
           "recurring share is dominated by dialysis/wound-care "
           "round-trips and is a per-account data pull (RSNAT-eligible "
           "volume is its Medicare proxy)."),
        _S("What level of response readiness is required?",
           "Tiers: scheduled (appointment-keeping), urgent (a promised "
           "ETA in minutes-to-hours), critical (immediate CCT) — readiness "
           "is a portfolio, not one number."),
        _S("What happens when demand exceeds capacity?",
           "The queue forms inside the hospital: ED boarding, occupied "
           "beds, missed placement windows — the shortfall cost lands on "
           "the buyer."),
        _S("How does demand density affect operating efficiency?",
           "Directly: MedPAC finds a strong inverse volume-to-cost-per-"
           "response relationship; dense books chain trips, cut deadhead, "
           "and lift unit-hour utilization."),
    ),
)


_OPERATING = Block(
    "q1-operating", "Operating model",
    conclusion=(
        "The three markets run three different operating systems: 911 "
        "posts idle capacity against unknown emergencies (readiness "
        "economics), IFT plans capacity against known facility demand "
        "(logistics economics), and NEMT batches high-volume low-acuity "
        "rides through broker networks (routing economics)."),
    why_true=(
        "911 buys readiness: units posted to hit contractual response "
        "times, utilization deliberately held low (0.30-0.50 UHU band), "
        "cost per transport carried up by idle coverage — GADCS mean cost "
        "$2,673 with governmental agencies at $3,127.",
        "IFT converts the same assets to logistics: trips are known, "
        "chainable and positionable, so a scheduled book targets UHU "
        "ABOVE the 911 band; private for-profit cost per transport "
        "(GADCS $1,778) already reflects part of that gap.",
        "Staffing follows the market: EMD-driven 911 crews vs IFT crews "
        "matched to trip acuity (EMT/paramedic/nurse) vs NEMT drivers "
        "without clinical credentials; deadhead and wait time — not wages "
        "— are where IFT economics are won or lost.",
        "Rural geometry changes everything: long legs, one-way flows and "
        "thin density push deadhead up and UHU down, which is why the "
        "super-rural Medicare add-on (+22.6%) exists at all."),
    why_matters=(
        "A fleet tuned for one system underperforms in another — the "
        "operational reason shared 911/IFT fleets deprioritize transfers, "
        "and the reason cost comparisons across the three markets mislead "
        "unless the readiness model is named."),
    evidence=(
        _E("Mean cost per transport $2,673 all agencies / $3,127 "
           "governmental / $1,778 private for-profit; labor 70.7% of cost",
           "SOURCED", "CMS/RAND GADCS Year 1-2 + Year 1-4 reports (via "
           "trade coverage; re-verify)",
           "https://ambulance.org/2025/12/09/cms-releases-new-gadcs-report/"),
        _E("911 systems target ~0.30-0.50 unit-hour utilization; "
           "non-emergency providers target higher (AIMHI survey mean "
           "0.508)",
           "SOURCED", "AIMHI benchmarking / EMS1",
           "https://aimhi.mobi/benchmarking-resources/"),
        _E("Strong inverse relationship between response volume and cost "
           "per response — density is the cost lever",
           "SOURCED", "MedPAC assessment of GADCS data, Dec 2025",
           "https://www.medpac.gov/wp-content/uploads/2025/12/Tab-M-Ambulance-Dec-2025.pdf"),
        _E("Super-rural base-rate add-on of +22.6% (with +2% urban / +3% "
           "rural), extended through 2027 — the statutory recognition of "
           "rural operating geometry",
           "GOV", "CAA 2026 §6203 / 42 CFR 414 subpart H", ""),
    ),
    subqs=(
        _S("How are trips initiated and dispatched?",
           "911: PSAP→EMD→nearest unit. IFT: booking/transfer-center "
           "request→scheduler assigns from the plan. NEMT: broker "
           "portal→network assignment, often day-ahead."),
        _S("How are vehicles assigned?",
           "911 by proximity/posting; IFT by schedule fit, acuity match "
           "and chaining; NEMT by route batching."),
        _S("Is capacity shared or dedicated?",
           "911: exclusive to the jurisdiction. NEMT: pooled across the "
           "broker network. IFT: the open question — shared fleets serve "
           "it opportunistically; dedicated models reserve it."),
        _S("Where are vehicles positioned?",
           "911: posts chosen for response-time geometry. IFT: at/near "
           "the demand-generating facilities. NEMT: garage-based routes."),
        _S("What staffing and clinical credentials are required?",
           "Tier-driven: drivers (NEMT), EMTs (BLS), paramedics (ALS), "
           "nurses/specialty crews (CCT) — IFT spans the full ladder."),
        _S("How much time is waiting versus transporting?",
           "No public national split — flagged; wait is concentrated at "
           "hospital doors (patient-not-ready) and is the main "
           "controllable loss in IFT operations."),
        _S("How much mileage is loaded versus empty?",
           "Not published nationally; Medicare pays only LOADED miles "
           "(A0425), so every empty mile is pure cost — deadhead share is "
           "a core diligence metric to pull from operating data."),
        _S("What are the main causes of low utilization?",
           "911: readiness by design. IFT: patient-not-ready waits, "
           "one-way legs, over-buffered schedules. NEMT: no-shows."),
        _S("What determines how many vehicles must be available?",
           "911: response-time geometry. IFT: peak transfer/discharge "
           "curves + acuity mix + promised ETAs. NEMT: booked route "
           "volume."),
        _S("How does the model change across urban/suburban/rural?",
           "Density falls, legs lengthen, backhaul disappears; rural IFT "
           "becomes corridor logistics (hence the +22.6% super-rural "
           "add-on and air-ground boundary effects)."),
        _S("Which cost categories are structurally different?",
           "Readiness/idle cost (911-heavy), deadhead miles (IFT/rural-"
           "heavy), broker administration (NEMT), and clinical labor mix "
           "(rises with IFT acuity tiers)."),
    ),
)


_PURCHASING = Block(
    "q1-purchasing", "Purchasing and contracting",
    conclusion=(
        "911 and NEMT are bought through formal, exclusive, SLA-bearing "
        "contracts; most IFT is still bought trip-by-trip off call lists "
        "or through unenforced preferred-provider letters — the least "
        "mature purchasing of the three, and the reason capacity "
        "under-investment persists."),
    why_true=(
        "911 procurement is a municipal franchise/EOA: exclusive, "
        "multi-year, response-time SLAs with penalties, publicly rebid — "
        "the strongest contract form in the space.",
        "NEMT is bought as a capitated broker contract per state: "
        "exclusive by region, performance-audited, with the broker "
        "subcontracting a network under rate schedules.",
        "Hospital IFT sits at the other extreme in the footprint evidence: "
        "few named system-wide transport contracts exist in public view; "
        "call lists and informal first-call habits dominate, exclusivity "
        "is rare, and volume commitments rarer — no public contract "
        "registry documents them (recorded as not-found, and consistent "
        "with the fragmentation in the NPPES landscape).",
        "Without committed volume, providers rationally refuse to add "
        "dedicated units — the purchasing structure itself creates the "
        "capacity problem hospitals then experience."),
    why_matters=(
        "Purchasing maturity is the demand-side unlock for a dedicated "
        "model: the sale is not 'better trips' but 'a contract form that "
        "makes reliable capacity rational' — minimums, dedicated units, "
        "and enforceable service levels."),
    evidence=(
        _E("Nebraska EMS structure: 751 org NPIs across NE/IA with ~85-90% "
           "municipal/volunteer in NE — a supply base contracted for 911 "
           "coverage, not hospital IFT",
           "SOURCED", "CMS NPPES registry sweep, vendored 2026-07-10", ""),
        _E("Nebraska's state EMS assessment: 'Nebraska may have an excess "
           "of licensed EMS transporting agencies, which may be "
           "exacerbating shortages and creating inefficiencies'",
           "GOV", "NE DHHS Statewide EMS Assessment 2023-24 (re-verify)",
           "https://dhhs.ne.gov/OEHS%20Program%20Documents/NE%20Statewide%20EMS%20Assessment%20v2024.pdf"),
        _E("No public hospital-by-hospital IFT contract data exists for "
           "the footprint systems (Nebraska Medicine, Methodist, Bryan, "
           "Madonna) — an honest not-found, itself evidence of informal "
           "purchasing",
           "FRAMEWORK", "2026-07-10 research sweep (dead-end log)", ""),
    ),
    subqs=(
        _S("Who owns the procurement decision in each market?",
           "911: city/county councils. NEMT: state Medicaid agencies. "
           "IFT: nominally hospital supply chain — often nobody in "
           "practice."),
        _S("How is the service acquired?",
           "911: municipal award/franchise. NEMT: broker capitation. IFT: "
           "the full spectrum — open call list, preferred letter, rare "
           "dedicated contract."),
        _S("How centralized is purchasing?",
           "911/NEMT: fully. IFT: facility-fragmented except in mature "
           "systems with transfer-center governance."),
        _S("Are contracts exclusive?",
           "911: yes (EOA/franchise). NEMT: yes by region. IFT: rarely — "
           "exclusivity appears only in dedicated deals."),
        _S("Is capacity guaranteed? Are minimum volumes included?",
           "911: coverage guaranteed by SLA. NEMT: network adequacy "
           "standards. IFT: almost never — the defining gap."),
        _S("How long are contracts / how often rebid?",
           "911: multi-year (3-5+) with formal rebids. NEMT: 3-5 year "
           "state cycles. IFT: where contracts exist, short and quietly "
           "renewed; no public rebid cadence."),
        _S("Which service levels are contractually defined?",
           "911: response times by priority. NEMT: pickup windows, "
           "complaint rates. IFT: typically none — ETAs are best-efforts "
           "unless a dedicated contract defines them."),
        _S("Are penalties or service credits included?",
           "Standard in 911 and NEMT; exceptional in IFT."),
        _S("How much emphasis on price versus reliability?",
           "Trip-priced IFT buying over-weights rate cards; every "
           "operational failure in Question 7 argues reliability is worth "
           "more — mature buyers price the bed-day, not the trip."),
        _S("Which purchasing elements encourage or discourage capacity "
           "investment?",
           "Encourage: minimums, dedicated-unit fees, term length, "
           "exclusivity. Discourage: trip-by-trip awards, no-commitment "
           "call lists, price-only RFPs."),
    ),
)


_REIMBURSEMENT = Block(
    "q1-reimbursement", "Reimbursement and unit economics",
    conclusion=(
        "IFT bills the same Medicare fee ladder as 911 but lives on a "
        "different P&L: scheduled non-emergency codes at lower relative "
        "values, a 19.7% never-paid share, commercial rates near 2x "
        "Medicare, and a hospital direct-pay channel that exists in "
        "neither other market — payer mix and deadhead, not the base "
        "rate, decide which trips providers will accept."),
    why_true=(
        "The fee ladder is public arithmetic: CY2025 conversion factor "
        "$278.98 × RVUs (BLS 1.00 / BLS-E 1.60 / ALS1 1.20 / ALS1-E 1.90 "
        "/ ALS2 2.75 / SCT 3.25) + ~$8/loaded-mile Medicare mileage; "
        "Medicare's all-in average payment is $469/transport.",
        "Payment realization is the real variable: 19.7% of transports "
        "collect nothing (GADCS); commercial pays ~2.0x Medicare (HCCI "
        "2022) with ~60% of rides out-of-network (FAIR Health); dialysis "
        "BLS non-emergency is cut 23% below the schedule with RSNAT "
        "prior-auth gating repetitive volume.",
        "Documentation gates the non-emergency book: a Physician "
        "Certification Statement and medical-necessity showing (42 CFR "
        "410.40) — the top denial exposure sits exactly in scheduled IFT.",
        "The unattractive-but-necessary trips are structural: long "
        "one-way rural legs, Medicaid/unfunded discharges, and "
        "psychiatric transfers — the trips hospitals most need moved and "
        "payers least reward, which is where hospital direct payment and "
        "availability retainers enter."),
    why_matters=(
        "Reimbursement adequacy sets MARKET CAPACITY: when the payable "
        "mix thins, providers shrink to profitable corridors and "
        "hospitals feel it as unavailability. Any credible model must "
        "price the unattractive-but-necessary book explicitly rather "
        "than cross-subsidizing it silently."),
    evidence=(
        _E("CY2025 AFS conversion factor $278.98; SCT relative value 3.25 "
           "→ ~$907 national base before adjustments",
           "GOV", "CMS AFS / MedPAC Payment Basics 2025 (re-verify CF "
           "against the PUF)", ""),
        _E("Commercial ESI base rate 2.0x Medicare ($718 vs $365, 2022); "
           "mileage $17 vs $8",
           "SOURCED", "Health Care Cost Institute",
           "https://healthcostinstitute.org/all-hcci-reports/commercial-prices-for-ground-ambulance-are-double-medicare-rates/"),
        _E("Mean reimbursement per transport $1,147 across all payers vs "
           "mean cost $2,673 — the published mean spread is negative",
           "SOURCED", "CMS/RAND GADCS Year 1-2 (via coverage; re-verify)",
           "https://emsmc.com/in-the-news/takeaways-from-the-first-cms-data-collection-report-on-ambulance-services-and-what-we-need-to-do-about-it/"),
        _E("ESRD dialysis-related non-emergency BLS pays fee schedule "
           "minus 23% since Oct 2018",
           "GOV", "42 CFR 414 subpart H",
           "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-414/subpart-H"),
        _E("Ground ambulance is EXCLUDED from the No Surprises Act; the "
           "GAPB committee recommends banning OON balance billing with "
           "cost-sharing capped at the lesser of $100 or 10%",
           "GOV", "CMS GAPB Advisory Committee report, 2024",
           "https://www.cms.gov/files/document/report-advisory-committee-ground-ambulance-and-patient-billing.pdf"),
    ),
    subqs=(
        _S("Who submits the claim?", "The transport provider, in all "
           "three markets (the broker pays subcontractors in NEMT)."),
        _S("Who receives the claim?",
           "Medicare MACs, Medicaid/MCOs, commercial plans — or the "
           "hospital directly for facility-responsible IFT trips."),
        _S("When is the health system directly responsible for payment?",
           "Non-covered transfers it orders (convenience/repatriation/"
           "capacity moves), denied trips under contract terms, and any "
           "availability-retainer fees in dedicated deals."),
        _S("How are base, mileage, waiting, equipment and attendants "
           "reimbursed?",
           "Base by HCPCS level; loaded mileage via A0425; waiting time, "
           "extra attendants and most equipment are NOT separately paid "
           "by Medicare — they ride on the base or on facility "
           "contracts."),
        _S("What documentation is necessary?",
           "Non-emergency: PCS + medical-necessity (bed-confined or "
           "alternative-contraindicated); repetitive trips: RSNAT prior "
           "authorization; emergencies: run documentation."),
        _S("What are the most common reasons for denial?",
           "Medical necessity not supported, missing/late PCS, "
           "origin-destination not covered, level-of-service downcodes."),
        _S("How do economics differ across payers?",
           "Medicare = the $469 fee-schedule anchor; Medicaid below it; "
           "commercial ~2x with OON friction; self-pay largely "
           "uncollectible — mix IS the margin."),
        _S("How does payer mix affect willingness to accept trips?",
           "Directly: thin-mix books get slow ETAs and quiet refusals; "
           "this is the mechanism behind 'no capacity' complaints."),
        _S("How much provider cost comes from empty mileage?",
           "No published national share — flagged; structurally larger in "
           "rural one-way corridors, and unpaid by Medicare, so it "
           "functions as a pure margin tax."),
        _S("Which trip types are most economically attractive?",
           "Commercially insured ALS2/SCT and dense chained urban BLS "
           "with backhaul."),
        _S("Which are operationally necessary but economically "
           "unattractive?",
           "Long rural one-ways, Medicaid/unfunded discharges, "
           "psychiatric transfers, dialysis round-trips post-RSNAT."),
        _S("How does reimbursement adequacy affect market capacity?",
           "It IS the capacity mechanism: negative published mean spreads "
           "plus a rising unpaid share shrink supply until hospitals "
           "backstop it contractually."),
    ),
)


_COMPETITIVE = Block(
    "q1-competitive", "Competitive characteristics",
    conclusion=(
        "All three markets are local at the point of service, but they "
        "concentrate differently: 911 is one-winner-per-jurisdiction, "
        "NEMT is broker-consolidated above a fragmented driver base, and "
        "IFT is the most fragmented of all — thousands of small "
        "operators, no national brand advantage, where fleet density, "
        "workforce and hospital relationships decide winners "
        "market-by-market."),
    why_true=(
        "The registry shows the fragmentation directly: 751 ambulance "
        "organization NPIs across just NE+IA, ~85-90% of Nebraska's "
        "municipal/volunteer, a thin private layer, and no operator with "
        "meaningful multi-state IFT density besides the roll-ups now "
        "forming (MMT/Harbour Point, AmeriPro/Whistler, AMR/KKR).",
        "Entry is cheap at one truck and brutal at scale: vehicles are "
        "purchasable, but density (enough contracted volume to chain "
        "trips), credentialed labor in a shrinking volunteer state, and "
        "transfer-center trust each take years — they are the actual "
        "barriers.",
        "Switching costs are relational and infrastructural, not legal: "
        "embedded scheduling habits, first-call status, integration into "
        "discharge workflow, and the absence of any alternative with "
        "spare capacity.",
        "What standardizes across markets: dispatch technology, revenue "
        "cycle, clinical protocols, recruiting engines. What stays "
        "irreducibly local: density, relationships, and licensure."),
    why_matters=(
        "This is a consolidation map: a platform that industrializes the "
        "standardizable layers and buys/builds local density can compound "
        "advantages that single-market incumbents cannot answer — which "
        "is precisely the PE thesis being tested in Questions 8-10."),
    evidence=(
        _E("751 unique ambulance org NPIs in NE+IA alone; NE private "
           "layer = 58 organizations",
           "SOURCED", "CMS NPPES sweep, vendored 2026-07-10", ""),
        _E("~10,600 ground ambulance organizations bill Medicare "
           "nationally — an extremely long tail",
           "GOV", "MedPAC, Oct 2024",
           "https://www.medpac.gov/wp-content/uploads/2024/10/MedPAC_Payment_Basics_24_ambulance_FINAL_SEC.pdf"),
        _E("Both large private IFT platforms in the footprint are now "
           "PE-owned: MMT (Harbour Point, 2022) and AmeriPro/Priority "
           "(Whistler, Feb 2025) — consolidation is underway",
           "SOURCED", "Deal press releases, 2022-2025",
           "https://www.prnewswire.com/news-releases/ameripro-health-acquires-priority-medical-transport-and-expands-midwest-presence-302372373.html"),
        _E("80%+ of Nebraska EMS agencies are all-volunteer and the base "
           "is contracting — workforce is the binding local constraint",
           "GOV", "NE DHHS EMS Assessment 2023-24 (re-verify)",
           "https://dhhs.ne.gov/OEHS%20Program%20Documents/NE%20Statewide%20EMS%20Assessment%20v2024.pdf"),
    ),
    subqs=(
        _S("How fragmented is each market?",
           "911: consolidated per jurisdiction. NEMT: broker oligopoly "
           "over fragmented drivers. IFT: most fragmented — 10,600 "
           "Medicare-billing organizations nationally."),
        _S("Are the primary competitors local, regional, or national?",
           "Local incumbents everywhere; a handful of national platforms "
           "(AMR/GMR) and emerging PE regionals (MMT, AmeriPro) layer on "
           "top."),
        _S("What determines the geographic boundaries of competition?",
           "Drive-time economics of a leg, state licensure, and where a "
           "fleet can maintain density — competition is metro/corridor "
           "sized."),
        _S("How important is fleet density?",
           "Decisive — it drives chaining, deadhead, UHU and therefore "
           "cost per trip (the MedPAC volume-cost curve in local form)."),
        _S("How important is workforce availability?",
           "Co-decisive in this footprint: crews, not trucks, are the "
           "scarce input (labor ~70.7% of cost; volunteer base "
           "shrinking)."),
        _S("How important is local payer enrollment?",
           "Table stakes: Medicaid/MCO enrollment and commercial network "
           "status gate whole books of volume."),
        _S("How important is clinical capability?",
           "It defines the serviceable book: CCT capability is scarce, "
           "high-value, and hard to staff — the tier where competition "
           "thins to a few names."),
        _S("How important is dispatch technology?",
           "Increasingly separating: ETA credibility, visibility, and "
           "chaining efficiency are software outcomes; still replicable "
           "by a funded competitor."),
        _S("How important are hospital or municipal relationships?",
           "The demand side of the moat: first-call status and franchise "
           "awards ARE the market in 911/dedicated IFT."),
        _S("What prevents a new competitor from entering?",
           "Nothing at one-truck scale; at contract scale — density "
           "economics, credentialed labor, licensure timelines, and "
           "incumbent first-call relationships."),
        _S("Which capabilities require the most time and capital?",
           "CCT programs, multi-market density, and a trusted operating "
           "record; fleet capital is the easy part."),
        _S("Which advantages remain local? Which standardize?",
           "Local: density, relationships, licenses, labor pools. "
           "Standardizable: dispatch tech, RCM, protocols, recruiting, "
           "procurement."),
        _S("What creates customer switching costs?",
           "Workflow embedding (booking, integration, first-call habit), "
           "dedicated capacity that alternatives cannot re-create "
           "quickly, and pooled performance data."),
    ),
)


Q1 = QuestionDef(
    num=1,
    slug="markets",
    title="How are 911 transportation, IFT, and NEMT fundamentally "
          "different?",
    storyline=(
        "They are three different operating systems — different buyers, "
        "different demand physics, different contracts, different P&Ls — "
        "that happen to share vehicles; origin/destination plus buyer, "
        "not acuity or vehicle, draws the boundaries."),
    visual_key="three-systems",
    blocks=(_DEFINITIONS, _CUSTOMER, _DEMAND, _OPERATING, _PURCHASING,
            _REIMBURSEMENT, _COMPETITIVE),
)

QUESTIONS = (Q1,)
