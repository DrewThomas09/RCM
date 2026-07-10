"""In-Depth content — Questions 2 & 3: the dedicated-IFT operating model and
the patient-journey map.

Authored 2026-07-10 from the suite's cited corpus (ift_clinical_demand,
ift_demand_evidence, ift_growth_evidence, ift_unit_economics, ift_insourcing,
ift_moat, ift_study, ift_health_systems, ift_company) plus the 2026-07-10
research dossiers (operational-failure quantification; NEMT / 911 / Medicare
payment rules). Every evidence line carries its basis + source; " (re-verify)"
marks search-excerpt-grade captures per the dossier legends. Company or
contract internals that are not public are marked as diligence requests.
"""
from __future__ import annotations

from .ift_indepth import Block, Evidence, QuestionDef, SubQ

_E = Evidence
_S = SubQ


# ═════════════════════════════════════════════════════════════════════════════
# Question 2 — why dedicated IFT competes on different dimensions from EMS
# ═════════════════════════════════════════════════════════════════════════════

_MISSION = Block(
    "q2-mission", "Core operating mission",
    conclusion=(
        "Traditional EMS is engineered to minimize response time to unknown "
        "emergencies — which requires deliberately idle, geographically "
        "posted capacity — while dedicated IFT is engineered to keep "
        "promises to facilities: pickup windows, ETAs and bed-to-bed "
        "reliability against demand that is largely known in advance. The "
        "two missions reward opposite uses of the same truck."),
    why_true=(
        "911 systems hold unit-hour utilization in a 0.30-0.50 band ON "
        "PURPOSE — idle units are the product (coverage); an IFT book "
        "inverts the objective and targets utilization above that band by "
        "chaining known trips.",
        "The cost signature follows the mission: GADCS mean cost per "
        "transport is $2,673 all-agency and $3,127 governmental "
        "(readiness-heavy) versus $1,778 private for-profit — the spread "
        "is mostly paid-for idleness, with labor at 70.7% of total cost "
        "either way.",
        "A 911-tuned fleet fails IFT mechanically, not culturally: its "
        "units are posted for response-time geometry rather than at "
        "hospital doors, its dispatch reassigns any available unit to the "
        "next emergency, and a scheduled discharge is always the lowest "
        "bidder for the next unit-hour.",
        "Back-office resources pool across both missions (billing, "
        "medical direction, fleet maintenance, recruiting, training); the "
        "front-line resources — staffed unit-hours, posting plans, and "
        "the dispatch queue itself — cannot serve two objective functions "
        "at once."),
    why_matters=(
        "This is the structural reason 'we also do transfers' providers "
        "disappoint hospitals: the failure is the optimization target, "
        "not the operator's effort — and it is why a dedicated model can "
        "win on reliability without out-spending anyone."),
    evidence=(
        _E("911-only agencies typically target 0.30-0.50 unit-hour "
           "utilization; the AIMHI survey mean is 0.508; non-emergency "
           "books target higher",
           "SOURCED", "AIMHI benchmarking / EMS1",
           "https://aimhi.mobi/benchmarking-resources/"),
        _E("Mean cost per transport $2,673 all agencies / $3,127 "
           "governmental / $1,778 private for-profit; labor 70.7% of cost",
           "SOURCED", "CMS/RAND GADCS Year 1-2 + Year 1-4 reports, via "
           "trade coverage (re-verify)",
           "https://ambulance.org/2025/12/09/cms-releases-new-gadcs-report/"),
        _E("Strong inverse relationship between response volume and cost "
           "per response — the scheduled book monetizes density the "
           "readiness book cannot",
           "SOURCED", "MedPAC assessment of GADCS data, Dec 2025",
           "https://www.medpac.gov/wp-content/uploads/2025/01/Tab-M-Ambulance-Dec-2025.pdf"),
        _E("Three-fourths of California hospitals detained EMS crews more "
           "than one hour; one-third delayed return to service by more "
           "than three hours — hospital-door time is where shared fleets "
           "bleed the unit-hours IFT needs",
           "ACADEMIC", "Backer et al., Prehosp Emerg Care 2018 (830,637 "
           "CA transports)",
           "https://doi.org/10.1080/10903127.2018.1525456"),
    ),
    subqs=(
        _S("What is a traditional EMS system designed to optimize?",
           "Response time to unknown scene emergencies — coverage "
           "geometry, fractile response standards (urban norm 8:59 at the "
           "90th percentile), and deliberately low utilization."),
        _S("What is a dedicated IFT system designed to optimize?",
           "Commitment-keeping against known facility demand: on-time "
           "pickups, credible ETAs, acceptance rate, and unit-hour "
           "utilization above the 911 band via trip chaining."),
        _S("How does emergency readiness differ from facility-transfer "
           "reliability?",
           "Readiness is spatial (be near the next unknown call, so idle "
           "= good); reliability is temporal (be at a named door at a "
           "promised time, so idle = waste and lateness = the failure)."),
        _S("Why can a fleet perform well in 911 service but poorly in "
           "IFT?",
           "Its posting, dispatch priority and staffing are all solved "
           "for the response-time objective — every scheduled transfer is "
           "structurally the first thing sacrificed when the emergency "
           "queue moves."),
        _S("Which resources can be shared between 911 and IFT?",
           "The scale layers: billing/revenue cycle, medical direction "
           "and protocols, fleet purchasing and maintenance, recruiting "
           "and training pipelines, quality/compliance infrastructure."),
        _S("Which resources should remain dedicated?",
           "Staffed unit-hours and their schedule, the dispatch queue and "
           "its priority rules, facility-posted units, and the scheduling "
           "/transfer-center interface — the things that carry the "
           "promise."),
        _S("What trade-offs occur when the same fleet serves both "
           "markets?",
           "Emergencies preempt transfers (ETA credibility dies), "
           "posting compromises between coverage and hospital doors, and "
           "utilization economics are hostage to readiness — one fleet, "
           "two objective functions, neither met at peak."),
    ),
)


_PREDICTABILITY = Block(
    "q2-predictability", "Demand predictability",
    conclusion=(
        "IFT demand is generated by institutional care transitions — "
        "measured at ~1.97M adult ED-to-ED transfers/yr, ~1.5M inpatient "
        "interhospital moves/yr, plus the discharge and recurring-"
        "treatment book — so it can be forecast at the facility x hour x "
        "modality grain in a way scene demand never can; only the thin "
        "urgent-transfer slice must be held as readiness."),
    why_true=(
        "The generators are countable hospital activities: 2.4-2.8% of "
        "~140-155M annual ED visits end in transfer (6.2% rural vs 2.0% "
        "urban), inpatient discharges feed a mapped post-acute network, "
        "and dialysis creates Medicare-defined repetitive round-trips "
        "(3+ in 10 days, or weekly for 3+ weeks).",
        "The suite's clinical registry maps 32 acute-transfer scenarios "
        "across three families (19 escalation, 9 step-down, 4 direct-"
        "admit/load-balancing), each tied to a published national volume "
        "and a demographic growth rate — demand decomposes into named, "
        "forecastable streams.",
        "Timing concentrates: discharge and post-acute legs book hours "
        "ahead and pile into weekday late-morning-to-evening windows; "
        "recurring dialysis runs on fixed schedules; urgent ED "
        "up-transfers arrive around ED peak hours with a 24/7 floor.",
        "The urgent slice is real but bounded: 6.6% of adult ED transfers "
        "involve a critical procedure (rising, OR 1.09/yr) — the part of "
        "the book that needs immediate CCT readiness rather than "
        "schedule planning."),
    why_matters=(
        "Forecastability is the economic license for dedicated capacity: "
        "a provider can staff to a known discharge curve and sell the "
        "residual readiness explicitly — the exact planning move a "
        "911-anchored operator cannot make."),
    evidence=(
        _E("9,867,701 adult ED-to-ED transfers 2018-2022 (~1.97M/yr); "
           "6.6% involved a critical procedure, rising at OR 1.09/yr",
           "ACADEMIC", "Nikolla et al., J Emerg Med 2025 (HCUP NEDS)",
           "https://doi.org/10.1016/j.jemermed.2025.12.020"),
        _E("~1.5M/yr acute-to-acute interhospital transfers = 3.5% of "
           "inpatient admissions",
           "ACADEMIC", "Mueller et al., 2014 (HCUP NIS)",
           "https://pubmed.ncbi.nlm.nih.gov/25397857/"),
        _E("Rural EDs transfer 6.2% of visits vs 2.0% urban — the "
           "transfer propensity is a stable facility attribute, which is "
           "what makes per-facility forecasting work",
           "ACADEMIC", "Greenwood-Ericksen et al., JAMA Network Open 2021",
           "https://doi.org/10.1001/jamanetworkopen.2021.34980"),
        _E("ED visits arriving via interfacility EMS transfer rose 15% "
           "(2017-19) and 35% (2020-22) vs the 2014-16 baseline — the "
           "trend itself is measured, not assumed",
           "ACADEMIC", "Peters et al., Am J Emerg Med 2026",
           "https://doi.org/10.1016/j.ajem.2026.04.025"),
        _E("Medicare defines repetitive scheduled non-emergent transport "
           "as 3+ round trips in 10 days or 1+/week for 3+ weeks; a RSNAT "
           "prior-auth affirmation covers 120 round trips over 180 days — "
           "regulation literally presumes this demand is schedulable",
           "GOV", "CMS RSNAT prior-authorization model rules", ""),
    ),
    subqs=(
        _S("How much IFT demand can be forecast?",
           "Most of it — the discharge, post-acute and recurring books "
           "are bookable in advance and the urgent slice is "
           "statistically stable per facility; the exact split is a "
           "per-account data pull, not a published national figure."),
        _S("Which hospital activities predict IFT demand?",
           "ED census and transfer propensity, inpatient discharge "
           "volume by destination, procedure/OR schedules, transfer-"
           "center request logs, bed-management escalations, and the "
           "dialysis roster."),
        _S("Can discharge patterns predict transport volume?",
           "Yes — discharges to SNF/IRF/LTACH/home-health are the "
           "highest-volume legs and follow stable weekday/daypart "
           "curves; ~1.8M Medicare-covered SNF stays/yr alone anchor "
           "the pattern."),
        _S("Can scheduled procedures predict return trips?",
           "Yes — dialysis (3x/week per patient), wound care, radiation "
           "and infusion schedules generate fixed round-trips; Medicare's "
           "RSNAT definition (3+ round trips in 10 days) exists because "
           "this book is schedulable."),
        _S("Can historical origin-destination patterns predict vehicle "
           "requirements?",
           "Yes — origin-destination pairs repeat (same EDs feed the "
           "same hubs, same floors discharge to the same SNFs), so trip "
           "history converts into posts, staffed unit-hours and chaining "
           "plans."),
        _S("How does demand vary by facility?",
           "By transfer propensity (rural 6.2% vs urban 2.0% of ED "
           "visits), bed count, service-line gaps, and post-acute "
           "orientation — each facility has a characteristic volume and "
           "mix that holds year to year."),
        _S("How does demand vary by modality?",
           "The escalation book skews high-acuity (volume-weighted "
           "~56% CCT/SCT/specialty-team in the registry) while the "
           "discharge book skews BLS/wheelchair — modality mix is a "
           "function of which journey leg dominates the account."),
        _S("How does demand vary by hour and weekday?",
           "Scheduled legs concentrate weekday late-morning through "
           "evening (discharge windows); urgent transfers run 24/7 "
           "skewed to ED peaks; weekends drop scheduled volume to a "
           "floor and keep the urgent base."),
        _S("How much capacity must remain available for urgent "
           "transfers?",
           "Enough to cover the critical slice — 6.6% of ED transfers "
           "involve critical procedures — plus promised urgent ETAs; the "
           "right number is a per-market queueing calculation off the "
           "facility's own urgent arrival rate."),
        _S("What proportion of demand is sufficiently predictable to "
           "support dedicated planning?",
           skip="Not published — a national scheduled-vs-urgent trip "
                "split; requires operator dispatch data (booked-ahead "
                "share by account), a diligence request."),
    ),
)


_CAPACITY = Block(
    "q2-capacity", "Capacity allocation",
    conclusion=(
        "Capacity should be allocated to demand density: units posted at "
        "or near the facilities that generate the trips, sized to the "
        "known peak curves plus an explicit urgent buffer — because "
        "density is the one variable that simultaneously improves "
        "response time, deadhead, labor productivity and cost per "
        "transport."),
    why_true=(
        "MedPAC's read of the GADCS data finds a strong inverse "
        "volume-to-cost-per-response relationship — scale and density, "
        "not wages, are the cost lever; labor is 70.7% of cost, so every "
        "chained trip amortizes the same crew-hour.",
        "Medicare pays only loaded mileage (A0425), so every empty mile "
        "is uncompensated cost — dense books cut deadhead directly, and "
        "thin rural geometry inverts the economics badly enough that "
        "Congress maintains a +22.6% super-rural base-rate add-on.",
        "Dedication is a volume threshold, not a philosophy: when one "
        "system's forecastable book can fill a unit's schedule (the "
        "discharge curve plus intra-system lanes), a dedicated unit "
        "beats pooling; below that threshold shared capacity across "
        "facilities is the only way to keep utilization above the 911 "
        "band.",
        "Guaranteed volume converts the provider's capacity decision "
        "from a gamble into arithmetic — the purchasing evidence shows "
        "trip-by-trip markets under-invest in capacity precisely "
        "because nobody commits the volume that would justify adding "
        "units."),
    why_matters=(
        "Capacity allocation is where the dedicated thesis is won or "
        "lost financially: the same staffed unit-hour is a loss at 911 "
        "utilization and a profit chained across a dense scheduled "
        "book — contract structure (minimums, dedicated-unit fees) is "
        "what moves a market from one state to the other."),
    evidence=(
        _E("Strong inverse relationship between ambulance response "
           "volume and cost per response",
           "SOURCED", "MedPAC assessment of GADCS data, Dec 2025",
           "https://www.medpac.gov/wp-content/uploads/2025/01/Tab-M-Ambulance-Dec-2025.pdf"),
        _E("Labor (wages + benefits) is 70.7% of ambulance cost — the "
           "crew-hour is the unit everything else must amortize",
           "SOURCED", "GADCS Year 1-4 appendix via AAA coverage "
           "(re-verify)",
           "https://ambulance.org/2025/12/09/cms-releases-new-gadcs-report/"),
        _E("Medicare pays loaded miles only (A0425); ~$8/mile vs "
           "commercial ~$17 — deadhead is a pure margin tax",
           "SOURCED", "HCCI ground-ambulance price analysis (2022 data)",
           "https://healthcostinstitute.org/all-hcci-reports/commercial-prices-for-ground-ambulance-are-double-medicare-rates/"),
        _E("Super-rural base-rate add-on +22.6% (urban +2%, rural +3%) "
           "extended through 2027 — statutory recognition that thin "
           "density breaks ambulance economics",
           "GOV", "CAA 2026 §6203 / 42 CFR 414 subpart H", ""),
        _E("911 UHU band 0.30-0.50 vs higher non-emergency targets — the "
           "utilization spread IS the capacity-allocation prize",
           "SOURCED", "AIMHI benchmarking / EMS1",
           "https://aimhi.mobi/benchmarking-resources/"),
    ),
    subqs=(
        _S("How should capacity be allocated across facilities?",
           "Proportional to each facility's forecast trip curve by "
           "daypart and modality, with units posted at the highest-"
           "volume campuses and pooled coverage over the tail."),
        _S("How close must vehicles be positioned to major demand "
           "centers?",
           "Close enough that pickup ETA is set by the schedule, not "
           "travel — in practice on-campus or minutes away for anchor "
           "hospitals (co-located posts), corridor-staged for rural "
           "spokes."),
        _S("How many vehicles are required to satisfy peak demand?",
           "Peak concurrent trips ÷ achievable trips per unit-hour, by "
           "modality — a queueing calculation off the facility curves; "
           "the suite's reference equation is legs x ~1.6 crew-hours / "
           "(UHU x 4,380 staffed hours/unit/yr)."),
        _S("How much spare capacity is needed?",
           "An explicit urgent buffer sized to the critical slice (6.6% "
           "of ED transfers involve critical procedures) and the "
           "promised urgent ETA — held as named readiness, not hidden "
           "slack."),
        _S("When should capacity be dedicated to one health system?",
           "When that system's committed volume fills the unit's "
           "schedule at target utilization — dense intra-system lanes "
           "and a contracted minimum make dedication cheaper than "
           "pooling for both sides."),
        _S("When is shared capacity more efficient?",
           "Thin or spiky demand: small facilities, rural corridors, "
           "off-peak hours, and specialty tiers (CCT) whose volume no "
           "single account can fill."),
        _S("How does local trip density affect response time?",
           "Directly — dense node clusters keep the next unit minutes "
           "from the next pickup; thin geography turns every request "
           "into a long positioning leg."),
        _S("How does density affect empty mileage?",
           "Dense origin-destination webs create backhauls (drop at the "
           "SNF, pick up the return trip nearby); rural one-way flows "
           "have no return load, so deadhead approaches loaded mileage."),
        _S("How does density affect labor productivity?",
           "Labor is 70.7% of cost, so productivity IS chained trips "
           "per crew-shift; the MedPAC volume-cost curve is this effect "
           "measured across the industry."),
        _S("How does guaranteed volume change the provider's "
           "willingness to add capacity?",
           "It is the whole game: a committed minimum or dedicated-unit "
           "fee underwrites the fixed crew cost, so capacity gets added "
           "ahead of demand instead of rationed behind it."),
        _S("What creates the most efficient balance between dedicated "
           "and flexible capacity?",
           "Dedicate to the forecastable core (anchor-campus curves, "
           "recurring lanes), float a shared layer over the tail and "
           "the urgent buffer, and re-cut the split quarterly from "
           "actual trip data."),
    ),
)


_DISPATCH = Block(
    "q2-dispatch", "Dispatch priorities",
    conclusion=(
        "In a shared 911/IFT operation the dispatch queue itself is the "
        "conflict: emergencies lawfully and culturally preempt accepted "
        "transfers, reassignments destroy ETA credibility, and the "
        "hospital has no visibility into the competing demand that just "
        "consumed its truck. A dedicated queue is the only structural "
        "fix — priority rules can then rank scheduled, urgent and "
        "critical transfers against each other instead of against 911."),
    why_true=(
        "A 911-anchored dispatcher treats an accepted IFT trip as the "
        "reserve capacity for the next emergency — the transfer is "
        "bumped, the crew is reassigned, and the hospital learns of it "
        "only when the ETA lapses.",
        "Hospital-door time compounds the queue problem in both "
        "directions: 75% of California hospitals detained crews over an "
        "hour (2017 data), and the national median offload is 10.9 "
        "minutes with a skewed urban tail — wall time consumes exactly "
        "the unit-hours the scheduled book was promised.",
        "The failure is measurable enough to regulate: California's AB "
        "40 set a 30-minute offload standard to be met 90% of the time, "
        "with monthly per-hospital monitoring — queue discipline at the "
        "hospital door is now a compliance object, not a courtesy.",
        "A dedicated provider can make firmer commitments because its "
        "queue contains only facility work: priority becomes a stated "
        "policy (critical immediately, urgent within a promised window, "
        "scheduled protected from cannibalization) rather than an "
        "emergent outcome of 911 load."),
    why_matters=(
        "ETA credibility is the actual product in IFT — a hospital "
        "plans beds, staffing and placements against the quoted time, "
        "so a dispatch model that cannot protect its promises is "
        "selling numbers it does not control."),
    evidence=(
        _E("Three-fourths of hospitals detained EMS crews >1 hour, 40% "
           ">2 hours, one-third >3 hours before return to service "
           "(California 2017, 830,637 transports)",
           "ACADEMIC", "Backer et al., Prehosp Emerg Care 2018",
           "https://doi.org/10.1080/10903127.2018.1525456"),
        _E("Median ambulance patient offload time 10.9 min (IQR "
           "6.6-17.5) across 7.24M records; 3.3% of agencies had ≥25% "
           "of transports offloading >30 min, skewed urban",
           "ACADEMIC", "Shaw et al., Prehosp Emerg Care 2025 (ESO 2024)",
           "https://doi.org/10.1080/10903127.2025.2535576"),
        _E("California AB 40 (2023): ambulance patient offload standard "
           "not to exceed 30 minutes 90% of the time, with EMSA monthly "
           "per-hospital monitoring",
           "GOV", "CA AB 40 / EMSA APOT program (re-verify)",
           "https://emsa.ca.gov/apot"),
        _E("NEMT broker contracts run ≥95% on-time-pickup standards "
           "with penalties (TX benchmark 85% with capped fines) — "
           "adjacent transport markets already contract dispatch "
           "performance; hospital IFT typically does not",
           "SOURCED", "Broker contract standards / TX MTP program "
           "(re-verify)", ""),
    ),
    subqs=(
        _S("How are IFT trips prioritized by traditional EMS operators?",
           "Below emergencies, by design — scheduled transfers are the "
           "flexible workload that absorbs 911 variance, and they are "
           "served when the emergency queue permits."),
        _S("What happens when an emergency call arrives after an IFT "
           "trip has been accepted?",
           "The nearest capable unit — often the one committed to the "
           "transfer — is reassigned; the transfer re-queues behind an "
           "unknown wait and the hospital's plan breaks."),
        _S("How frequently can an IFT vehicle be reassigned?",
           skip="Not published — reassignment/bump rates per accepted "
                "trip; an operator CAD-log metric, a diligence request."),
        _S("How do reassignments affect ETA accuracy?",
           "They convert a point estimate into a fiction — each bump "
           "resets the clock, and the quoted ETA stops correlating with "
           "arrival, which is worse than a longer honest window."),
        _S("How are delayed trips communicated to the hospital?",
           "In the default model, by the hospital calling to ask — "
           "status flows outbound only on inquiry; pushed status/ETA "
           "updates are exactly what dedicated, integrated operators "
           "sell against."),
        _S("Does the health system have visibility into competing "
           "demand?",
           "No — the hospital cannot see the 911 queue or other "
           "facilities' bookings that consumed its unit; asymmetric "
           "visibility is why late trips read as broken promises."),
        _S("Can a dedicated IFT provider create firmer dispatch "
           "commitments?",
           "Yes — a facility-only queue plus committed units makes "
           "pickup windows contractable (the NEMT world already writes "
           "≥95% on-time standards with penalties; hospital IFT rarely "
           "does)."),
        _S("How should scheduled, urgent, and critical transfers be "
           "prioritized against one another?",
           "Critical preempts immediately with the reserved buffer; "
           "urgent gets a promised window served ahead of schedule "
           "slack; scheduled trips are protected from cannibalization "
           "except by declared critical need — and every preemption is "
           "reported, not silent."),
    ),
)


_INTEGRATION = Block(
    "q2-integration", "Health-system integration",
    conclusion=(
        "Transportation is the last unintegrated step of hospital flow: "
        "discharge planning, bed management, transfer centers and "
        "procedure schedules all generate transport demand hours before "
        "anyone books a truck, and the measured transfer timelines show "
        "the referring-hospital interval — not the drive — is where the "
        "time goes. Integration that moves the request upstream attacks "
        "the dominant interval; integration that only displays status "
        "improves visibility, not physics."),
    why_true=(
        "The demand signal exists early: a discharge order, an accepted "
        "transfer, or tomorrow's dialysis roster each precede the "
        "transport request by hours — the booking is late because the "
        "workflow is disconnected, not because the demand was unknown.",
        "Measured stroke-transfer timelines localize the delay: 82.8% "
        "of total transfer time is spent at the referring hospital, and "
        "of a 171.4-minute mean door-in-door-out, imaging-to-door is "
        "153.1 minutes versus 18.3 for door-to-imaging — the "
        "disposition-and-transport interval dominates.",
        "Integration effects are measurable where tested: EMS "
        "prenotification cut stroke door-in-door-out by 20.1 minutes in "
        "the GWTG registry — a workflow connection, not a faster "
        "vehicle.",
        "Trip data compounds: a provider that logs every request, wait "
        "and completion per unit/floor/hour holds the demand curve both "
        "sides need for staffing and capacity planning — data the "
        "phone-call model never captures."),
    why_matters=(
        "Integration is the difference between selling rides and "
        "selling throughput: the buyer's bed-hours are recovered "
        "upstream of the vehicle, which is why embedded workflow (not "
        "an app) is the durable form of the relationship."),
    evidence=(
        _E("82.8% of stroke interfacility transfer time was spent at "
           "the referring hospital (door-in-door-out 106 min); 37.3% of "
           "DIDO >120 min",
           "ACADEMIC", "Ng et al., Stroke 2017",
           "https://doi.org/10.1161/STROKEAHA.117.017235"),
        _E("Mean DIDO 171.4 min: door-to-imaging 18.3 min, "
           "imaging-to-door 153.1 min — disposition/transport is the "
           "dominant interval",
           "ACADEMIC", "JAMA Network Open 2024 (n=28,887)",
           "https://doi.org/10.1001/jamanetworkopen.2024.31183"),
        _E("EMS prenotification associated with 20.1 minutes shorter "
           "stroke DIDO; median DIDO 174 min, only 27.3% within the "
           "120-min guideline",
           "ACADEMIC", "JAMA 2023 (GWTG-Stroke, n=108,913)",
           "https://doi.org/10.1001/jama.2023.12739"),
        _E("Pending care-management/transportation needs were the most "
           "frequent uncompleted discharge task (47%) in a single-site "
           "improvement study — the booking arrives late in the "
           "workflow",
           "ACADEMIC", "Single-site discharge QI study, PMC11023539 "
           "(re-verify)", ""),
    ),
    subqs=(
        _S("How is transportation demand connected to discharge "
           "planning?",
           "Weakly today — the discharge order predicts the leg hours "
           "ahead, but booking typically waits for the bedside 'patient "
           "is ready' call; connecting the order to a provisional "
           "booking is the integration prize."),
        _S("How is it connected to bed management?",
           "Every outbound transport is a bed-management event (a bed "
           "unblocked); mature systems let the capacity hub see and "
           "trigger transport, most still treat it as a floor-level "
           "phone task."),
        _S("How is it connected to transfer-center activity?",
           "The transfer center is the natural integration point — it "
           "already accepts the patient and knows acuity and timing; "
           "systems like CHI Health's 24/7 center accept STEMI/stroke "
           "transfers explicitly to expedite transport arrangement."),
        _S("How is it connected to procedure schedules?",
           "Recurring treatment schedules (dialysis 3x/week, radiation, "
           "wound care) can auto-generate standing bookings — the RSNAT "
           "affirmation (120 round trips/180 days) is this connection "
           "in regulatory form."),
        _S("How early in the patient journey is transportation "
           "requested?",
           skip="Not published — order-to-request lead-time "
                "distribution; measurable from hospital + operator "
                "timestamps, a diligence request."),
        _S("Can the provider see future demand?",
           "Only if integrated — a portal or interface exposing "
           "tomorrow's discharge queue and standing schedules converts "
           "the provider from reactive to staffed-ahead."),
        _S("Can hospital staff see provider capacity?",
           "Almost never today; publishing available unit-hours and "
           "slot availability is the reciprocal half of integration "
           "and what makes 'book the 14:00 slot' possible."),
        _S("Can ETA information be integrated into hospital workflows?",
           "Technically yes (CAD-to-portal or EHR feeds); the operating "
           "point is that pushed ETA changes reach the charge nurse and "
           "bed hub without a phone call."),
        _S("Can trip status be monitored without repeated phone calls?",
           "Yes with CAD/AVL-fed status boards — the phone-call model "
           "is a workflow artifact, and its elimination is a direct "
           "nursing-time save (vendor claims of 2-3 nurse-hours/shift "
           "on transport tasks are unverified — treat as a question, "
           "not a fact)."),
        _S("Can transportation data be used for future staffing and "
           "capacity planning?",
           "Yes — request/wait/completion logs by facility-hour are "
           "exactly the demand curves both parties need; pooled "
           "history is a compounding asset the incumbent accrues."),
        _S("Does deeper integration meaningfully improve performance, "
           "or merely improve visibility?",
           "Both, in order: visibility kills the phone tax immediately; "
           "performance moves when integration shifts the REQUEST "
           "upstream — the measured analog (prenotification, -20.1 min "
           "DIDO) shows workflow timing changes outcomes."),
    ),
)


_CLINICAL = Block(
    "q2-clinical", "Clinical matching",
    conclusion=(
        "Modality selection — wheelchair van through critical care — is "
        "made by the ordering clinician under Medicare's necessity rules "
        "(42 CFR 410.40), with uneven decision support and no published "
        "interfacility over-triage rate; the audit record shows the "
        "boundary is policed hard from the payment side (13.2% improper "
        "payment, 27.5% of it medical necessity), while under-triage is "
        "policed only by adverse events."),
    why_true=(
        "The rule set is explicit: non-emergency ambulance is covered "
        "only if the patient is bed-confined (unable to get up, "
        "ambulate, or sit — all three) or the condition contraindicates "
        "other transport, certified via a PCS — the wheelchair-vs-"
        "stretcher-vs-ambulance line is a regulatory object, not a "
        "preference.",
        "Over-triage is expensive twice: a higher-acuity vehicle burns "
        "scarce ALS/CCT unit-hours on a BLS-appropriate patient, and "
        "the claim invites denial — CERT attributes 27.5% of the "
        "ambulance improper-payment rate to medical necessity.",
        "Under-triage is the clinical tail risk: the escalation book "
        "runs high-acuity (the registry's volume-weighted escalation "
        "mix is ~56% CCT/SCT/specialty-team) and 6.6% of ED transfers "
        "involve critical procedures — a stable-looking patient on the "
        "wrong truck is a crew without the drugs, vent or authority the "
        "trip may need.",
        "A multi-modality network changes the economics of the "
        "decision: when one provider fields wheelchair, BLS, ALS and "
        "CCT (as dedicated platforms like MMT do), the dispatcher can "
        "re-tier a trip inside one system instead of re-brokering it "
        "across vendors."),
    why_matters=(
        "Matching accuracy is a direct margin and safety lever: every "
        "over-tiered trip wastes the scarcest crew type, every "
        "under-tiered trip is an incident report — and the provider "
        "that can measure and re-tier in-network turns a compliance "
        "problem into dispatch flexibility."),
    evidence=(
        _E("Non-emergency ambulance covered only if bed-confined (all "
           "three functional criteria) or transport otherwise "
           "contraindicated; PCS certification required, repetitive PCS "
           "dated ≤60 days ahead",
           "GOV", "42 CFR 410.40(e); MAC guidance",
           "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-410/subpart-B/section-410.40"),
        _E("Ambulance improper payment rate 13.2% (~$595.1M projected); "
           "63.5% insufficient documentation, 27.5% medical necessity",
           "GOV", "CMS CERT 2024 supplemental improper-payment data "
           "(re-verify)", ""),
        _E("Escalation-family transport mix, volume-weighted across the "
           "mapped scenarios: ~56% CCT/SCT + neonatal/peds specialty "
           "team, ~12% ALS/ALS2, ~32% low-acuity/behavioral",
           "DERIVED", "ift_clinical_demand.mission_mix() — GOV condition "
           "volumes x authored transport-acuity tiers (equation: "
           "tier share = Σ volume_tier / Σ volume_escalation)", ""),
        _E("Facial-fracture transfer study: ED-discharge-on-arrival "
           "share rose 151% while operative intervention fell — "
           "measured secondary over-triage in a transfer stream",
           "ACADEMIC", "Wasicek et al., Plast Reconstr Surg 2022 (NTDB "
           "2007-2015)",
           "https://doi.org/10.1097/PRS.0000000000009039"),
    ),
    subqs=(
        _S("How is the required level of transport determined?",
           "By the ordering clinician (physician/RN/case manager) "
           "against the patient's monitoring needs and Medicare's "
           "410.40 necessity criteria, documented via the PCS for "
           "non-emergency trips."),
        _S("Which clinical inputs drive modality selection?",
           "Ambulation/bed-confinement status, monitoring need "
           "(cardiac, neuro checks), airway/oxygen/ventilator, IV "
           "drips and med administrations, behavioral risk, and "
           "isolation/bariatric logistics."),
        _S("How often is a patient assigned to a higher-acuity vehicle "
           "than necessary?",
           skip="Not published — no interfacility-specific over-triage "
                "rate exists (adjacent literature only); measurable "
                "from requested-vs-required tier audits, a diligence "
                "request."),
        _S("How often is the initially requested modality "
           "insufficient?",
           skip="Not published — upgrade-en-route / re-tier rates are "
                "operator CAD data; a diligence request."),
        _S("How costly is over-triage?",
           "Roughly the tier spread per trip (SCT bills 3.25x the BLS "
           "relative value) plus the opportunity cost of a scarce "
           "ALS/CCT unit-hour — and denial exposure when the billed "
           "level outruns documented necessity."),
        _S("What risks arise from under-triage?",
           "A crew without the scope, drugs or equipment the patient "
           "deteriorates into mid-transport — the highest-severity "
           "failure mode, invisible in averages because it surfaces as "
           "individual adverse events."),
        _S("Who has authority to change the modality?",
           "The ordering clinician; the provider can refuse or query a "
           "mismatch and dispatch can propose a re-tier, but the order "
           "and its certification stay clinical."),
        _S("Can the provider support multiple modalities within one "
           "network?",
           "Yes, and it is the operating answer — a wheelchair-to-CCT "
           "ladder under one dispatch lets the trip be re-tiered "
           "without re-brokering; dedicated platforms field exactly "
           "this range."),
        _S("Does broader service capability improve dispatch "
           "flexibility?",
           "Materially — one queue can substitute vehicle types, "
           "absorb misclassified requests, and keep the account when "
           "the mix shifts; single-tier vendors bounce whatever they "
           "cannot serve."),
        _S("How should modality-selection accuracy be measured?",
           "Requested-vs-delivered-vs-clinically-required tier "
           "concordance, upgrade/downgrade-en-route rate, "
           "necessity-denial rate by tier, and adverse events per "
           "1,000 transports by tier."),
    ),
)


_PERFORMANCE = Block(
    "q2-performance", "Performance dimensions",
    conclusion=(
        "IFT performance is a commitment ledger, not a stopwatch: the "
        "measures that matter are on-time pickup against the accepted "
        "ETA, acceptance rate, provider-caused cancellations and "
        "turnaround — measured separately for scheduled and urgent "
        "trips and with patient-not-ready time carved out — because the "
        "hospital's real unit of account is the bed-hour, not the "
        "response minute."),
    why_true=(
        "911's headline metric (fractile response time) is meaningless "
        "for a scheduled discharge; the transfer analogs are "
        "commitment metrics — window hit-rate for scheduled trips, "
        "request-to-ETA and ETA-to-arrival for urgent ones.",
        "The buyer's economics anchor the KPI weights: boarding among "
        "admitted seniors runs 85.2% ≥2 hours with mean boarding up "
        "from 138 to 343 minutes (2018→2022) — the bed-hours a "
        "reliable transport partner returns are the value, so "
        "acceptance and punctuality outrank price-per-trip.",
        "Attribution must be honest to be useful: hospital-caused "
        "delay is real and large (75% of CA hospitals detained crews "
        ">1 hour; median offload 10.9 min with a long tail), so "
        "patient-not-ready and door-detention time must be clocked "
        "separately from provider lateness or the metric war poisons "
        "the relationship.",
        "Provider economics ride a different set — unit-hour "
        "utilization, deadhead share, payer/tier mix and denial rate — "
        "and the dedicated model's pitch is precisely that its "
        "commitment metrics and its economics improve together via "
        "density, instead of trading off."),
    why_matters=(
        "Whoever defines the scoreboard wins the renewal: a dedicated "
        "operator wants commitment metrics in the contract because "
        "they expose the shared-fleet weakness; a rate-card vendor "
        "wants no metrics at all — the KPI sheet is the moat made "
        "legible."),
    evidence=(
        _E("85.2% of admitted ED patients 65+ boarded ≥2 hours; mean "
           "boarding 138 min (2018) → 343 min (2022), 501 min with "
           "Alzheimer's-related dementia",
           "ACADEMIC", "Lee et al., Ann Emerg Med 2026 (NHAMCS "
           "2015-2022)",
           "https://doi.org/10.1016/j.annemergmed.2026.03.011"),
        _E("Median offload 10.9 min but 3.3% of agencies had ≥25% of "
           "transports >30 min — turnaround needs a distribution "
           "measure, not a mean",
           "ACADEMIC", "Shaw et al., Prehosp Emerg Care 2025",
           "https://doi.org/10.1080/10903127.2025.2535576"),
        _E("Adjacent-market precedent: broker NEMT contracts carry "
           "≥95% on-time-pickup standards; Texas runs an 85% benchmark "
           "with penalties; a state audit found ~5.8% late/missed — "
           "~3x the contractual limit — at one broker",
           "SOURCED", "Broker contract standards; Mississippi Today "
           "Sep 2024 (re-verify)", ""),
        _E("Urban 911 contracts define the alternative KPI regime — "
           "8:59 at 90% fractile with penalties — useful contrast, "
           "wrong measures for scheduled facility work",
           "SOURCED", "Municipal EMS performance contracts "
           "(re-verify)", ""),
    ),
    subqs=(
        _S("Which performance measures matter most in IFT?",
           "On-time pickup (window hit-rate), trip acceptance rate, "
           "provider cancellation rate, ETA accuracy, turnaround/"
           "handoff time, and after-hours performance — the "
           "commitment ledger."),
        _S("How should on-time pickup be defined?",
           "Arrival within a stated window around the committed time "
           "(e.g. ±15 min scheduled), with the commitment logged at "
           "acceptance — a definition both sides can audit from "
           "timestamps."),
        _S("Should performance be measured against the requested time "
           "or the accepted ETA?",
           "Both, separately: accepted-ETA performance measures "
           "execution honesty; requested-vs-accepted gap measures "
           "capacity adequacy — collapsing them hides whether the "
           "problem is trucks or truthfulness."),
        _S("How should urgent and scheduled trips be measured "
           "differently?",
           "Scheduled: window hit-rate against the booking. Urgent: "
           "request-to-quoted-ETA and quoted-vs-actual arrival. "
           "Critical: activation-to-rolling and rolling-to-door — "
           "three clocks, never one blended average."),
        _S("How should trip acceptance be calculated?",
           "Accepted ÷ requested within the contracted service scope, "
           "by tier and daypart, counting re-brokered and 'call back "
           "later' responses as declines."),
        _S("How should provider cancellations be measured?",
           "Provider-initiated cancels after acceptance per 100 trips, "
           "time-stamped by notice given, and split from "
           "hospital/patient cancels — late cancels are the most "
           "damaging failure and deserve their own line."),
        _S("How should patient-not-ready delays be separated from "
           "provider delays?",
           "Clock segmentation at the door: arrival, patient-contact, "
           "wheels-rolling timestamps assign each waiting minute to a "
           "party — the same discipline California now applies to "
           "hospital offload detention."),
        _S("How should handoff and turnaround time be measured?",
           "Door-to-clear at both ends (arrive→patient handed off→unit "
           "back in service), reported as median and 90th percentile — "
           "the tail, not the mean, eats unit-hours."),
        _S("How should after-hours performance be measured?",
           "Same metrics, separate cut: nights/weekends acceptance and "
           "window hit-rate reported on their own, because the "
           "shared-fleet failure mode concentrates exactly there."),
        _S("Which performance measures matter most to the health "
           "system?",
           "The bed-hour ones: acceptance at peak, on-time discharge "
           "pickups (they unblock beds), urgent ETA reliability, and "
           "boarding-hour reduction — throughput, not transport, "
           "language."),
        _S("Which performance measures drive provider economics?",
           "Unit-hour utilization, deadhead share, trips per "
           "crew-shift, payer/tier mix, denial rate and days-in-AR — "
           "the density ledger behind the commitment ledger."),
        _S("Which KPIs best distinguish a dedicated provider from a "
           "general EMS operator?",
           "Acceptance rate at peak and after hours, scheduled-window "
           "hit-rate, reassignment/bump rate on accepted trips, and "
           "ETA variance — the four places a 911-anchored queue "
           "cannot hide."),
    ),
)


_MOAT = Block(
    "q2-moat", "Sustainability of the advantage",
    conclusion=(
        "Dedicated capacity by itself is a contract clause a rival can "
        "match; the durable advantage is the compound of local density, "
        "accumulated demand data, embedded workflow and multi-tier "
        "service breadth — with the footprint's own history (the "
        "Wichita insource-to-AMR flip) proving that incumbency without "
        "those compounding layers is only as durable as the owner's "
        "intent."),
    why_true=(
        "The moat decomposes into scored factors — first-call status, "
        "share-of-wallet (the operator thesis targets 85%+), co-located "
        "assets, workflow integration, local density, switching costs "
        "and cross-market proof — and the strongest observed forms are "
        "combinations: Superior's embedded coordinators at Mount "
        "Carmel, Ryan Brothers' 60-year Madison relationships, AMR's "
        "co-branded UofL units.",
        "Density is the one factor with directly measured economics "
        "(the MedPAC volume-cost inverse curve): a dense incumbent "
        "chains trips a thin entrant cannot, so matching the rate card "
        "does not match the cost base.",
        "Replication is cheap in capital and slow in everything else: "
        "trucks are purchasable in months, but credentialed crews (in "
        "a market where 80%+ of Nebraska agencies are all-volunteer "
        "and shrinking), transfer-center trust, and a season of "
        "reliable performance each take years — and the entrant must "
        "run sub-scale economics while earning them.",
        "The counter-proof disciplines the thesis: Wesley/HCA moved "
        "~77% of county IFT to AMR in 2022 — tenure without embedded "
        "workflow and shared data flipped on an ownership decision, so "
        "the durable layers are the ones a successor cannot inherit "
        "on day one."),
    why_matters=(
        "For an investor the question is which advantages compound "
        "with each additional account — density, data and workflow do; "
        "rate cards, vehicles and software licenses do not — and the "
        "diligence test is whether the target's book is held by the "
        "compounding layers or merely by habit."),
    evidence=(
        _E("Seven-factor stickiness frame (first-call, 85%+ "
           "share-of-wallet target, co-located assets, workflow "
           "integration, density, switching costs, cross-market proof) "
           "— combinations, never software alone",
           "FRAMEWORK", "ift_moat operator-thesis scorecard (density "
           "factor SOURCED from node counts)", ""),
        _E("Wichita proof point: Wesley/HCA moved ~77% of county IFT "
           "(~4,873 of 2020 volume) to AMR in 2022 — durability tracks "
           "ownership intent, not tenure",
           "SOURCED", "ift_geo public/analyst read, public-web "
           "(re-verify)", ""),
        _E("Strong inverse volume-to-cost-per-response relationship — "
           "the density moat has measured economics",
           "SOURCED", "MedPAC assessment of GADCS data, Dec 2025",
           "https://www.medpac.gov/wp-content/uploads/2025/01/Tab-M-Ambulance-Dec-2025.pdf"),
        _E("80%+ of Nebraska EMS agencies are all-volunteer; only 31% "
           "of volunteer agencies report adequate staffing; 28% expect "
           "to be unable to operate within 5 years — credentialed labor "
           "is the replication bottleneck",
           "GOV", "NE DHHS Statewide EMS Assessment 2023-24 "
           "(re-verify)",
           "https://dhhs.ne.gov/OEHS%20Program%20Documents/NE%20Statewide%20EMS%20Assessment%20v2024.pdf"),
    ),
    subqs=(
        _S("Is dedicated capacity itself a moat, or merely a "
           "contractual feature?",
           "A feature — any funded rival can promise units; it becomes "
           "moat only when fused with density, embedded workflow and a "
           "performance record the buyer can verify."),
        _S("Does local density create a sustainable advantage?",
           "Yes — it is the cost-side moat with measured economics "
           "(the volume-cost inverse curve): the dense incumbent's "
           "chained trips undercut any thin entrant at equal rates."),
        _S("Does historical demand data improve future performance?",
           "Yes — per-facility trip curves sharpen staffing, posting "
           "and ETA quoting, and the data accrues only to whoever runs "
           "the volume; it is the quietest compounding asset."),
        _S("Does embedded workflow integration increase switching "
           "costs?",
           "Materially — replacing an operator wired into scheduling, "
           "coordinators and status feeds means retraining staff and "
           "rebuilding interfaces, not just re-papering rates (the "
           "Mount Carmel-Superior model)."),
        _S("Do dedicated contracts improve recruitment and scheduling?",
           "Yes — committed volume supports predictable shifts (a "
           "hiring advantage over 911 posting), funds full-time crews, "
           "and stabilizes the roster in a labor-scarce market."),
        _S("Does service breadth make it easier to match the correct "
           "modality?",
           "Yes — a wheelchair-to-CCT ladder under one dispatch "
           "re-tiers trips in-network, captures the whole account mix, "
           "and denies rivals a wedge tier."),
        _S("How easily can a traditional EMS provider replicate the "
           "model?",
           "The visible parts quickly (trucks, a rate card, an IFT "
           "division on paper); the operating parts slowly — a "
           "protected scheduled queue conflicts with its 911 economics, "
           "and the trust record cannot be bought."),
        _S("What investment would replication require?",
           "Fleet and posts (the easy capital), credentialed crews in "
           "a shrinking labor pool, dispatch/CAD and integration "
           "build-out, and one to two years of sub-scale operating "
           "losses while density accrues."),
        _S("How long would replication take?",
           "Years, not quarters: licensure and credentialing measure "
           "in months, first-call trust and a defensible performance "
           "record in renewal cycles — and incumbent data advantages "
           "keep moving the target."),
        _S("Which aspects are operationally difficult but "
           "strategically valuable?",
           "24/7 multi-tier reliability at contract scale, CCT "
           "crewing, honest performance reporting, and the "
           "urgent-buffer discipline — hard to run, exactly what the "
           "buyer cannot get elsewhere."),
        _S("Which supposed advantages are easily copied?",
           "Rate cards, vehicle counts, dispatch software licenses, "
           "and 'dedicated unit' language in a proposal — everything "
           "that fits in an RFP response."),
        _S("Which advantages compound as the provider gains customers "
           "and density?",
           "Unit economics (chaining/deadhead), demand-data depth, "
           "crew scale and scheduling flexibility, cross-account "
           "backhaul, and referenceable proof points — each new "
           "account makes the next cheaper to serve and easier to "
           "win."),
    ),
)


Q2 = QuestionDef(
    num=2,
    slug="dedicated",
    title="Why does dedicated IFT compete on different dimensions from "
          "traditional EMS?",
    storyline=(
        "Same trucks, opposite engines: 911 posts idle capacity against "
        "unknown emergencies while dedicated IFT converts forecastable "
        "facility demand into scheduled, committed, measured logistics — "
        "so capacity, dispatch, integration and every KPI split along "
        "that line, and the durable edge is density + data + embedded "
        "workflow, not the vehicles."),
    visual_key="two-engines",
    blocks=(_MISSION, _PREDICTABILITY, _CAPACITY, _DISPATCH, _INTEGRATION,
            _CLINICAL, _PERFORMANCE, _MOAT),
)


# ═════════════════════════════════════════════════════════════════════════════
# Question 3 — where IFT fits into the patient journey
# ═════════════════════════════════════════════════════════════════════════════

_SETTINGS = Block(
    "q3-settings", "Care settings",
    conclusion=(
        "EDs and inpatient floors generate most IFT demand; tertiary hubs "
        "and the post-acute network receive it — a mapped destination "
        "universe of 35,481 facilities (14,699 SNF, 12,392 home-health, "
        "6,852 hospice, 1,221 IRF, 317 LTACH) whose entire admitted "
        "census arrives by transport. Acuity of the leg, not prestige of "
        "the building, decides ambulance versus wheelchair."),
    why_true=(
        "The acute generators are measured: 2.4-2.8% of ~140-155M annual "
        "ED visits end in transfer (~1.97M adult ED-to-ED transfers/yr), "
        "plus ~1.5M inpatient interhospital moves — rural and capability-"
        "thin sites transfer at 3x the urban rate, and freestanding "
        "EDs/REH conversions transfer every patient they cannot keep "
        "(REHs hold no inpatient beds at all).",
        "The post-acute receivers are countable: every IRF, LTACH and "
        "SNF admission from an acute stay is by definition an "
        "interfacility leg — Madonna's ~430 post-acute beds in the "
        "footprint are a census that arrives entirely by IFT.",
        "Recurring-treatment settings anchor the scheduled floor: "
        ">808,000 Americans live with ESRD (~68% on dialysis at 3 "
        "sessions/week), and behavioral-health placement adds ~6M "
        "mental-health ED visits/yr with psychiatric-bed scarcity "
        "driving secure transfers.",
        "Modality tracks the leg: hospital-to-hospital escalations run "
        "ambulance tiers (BLS through CCT); med-surg-to-SNF and "
        "residence legs run heavily wheelchair/stretcher-van; the "
        "clinical registry tiers each of its 32 scenarios accordingly."),
    why_matters=(
        "Reading demand by setting turns 'the hospital market' into an "
        "account map: which doors generate trips, which doors receive "
        "them, and which tier each door needs — the raw material for "
        "posting, contracting and pricing."),
    evidence=(
        _E("2.4% of US ED visits ended in transfer to another hospital "
           "(2021; 2.8% in 2018) on ~140-155M annual visits",
           "GOV", "NHAMCS / NCHS", ""),
        _E("Post-acute destination supply: 14,699 SNFs, 1,221 IRFs, 317 "
           "LTACHs, 12,392 home-health agencies, 6,852 hospices = 35,481 "
           "mapped destinations",
           "SOURCED", "CMS Care Compare / Provider-of-Services files via "
           "ift_clinical_demand.destination_supply()", ""),
        _E("Rural EDs transfer 6.2% of visits vs 2.0% urban; rural ED "
           "volume grew from 16.7M to 28.4M visits 2005-2016",
           "ACADEMIC", "Greenwood-Ericksen et al., JAMA Network Open "
           "2021 / 2019",
           "https://doi.org/10.1001/jamanetworkopen.2021.34980"),
        _E("REH designation: converted rural hospitals discontinue "
           "inpatient services, cap stays under 24 hours, and must hold "
           "transfer agreements — 40-50 conversions since Jan 2023, "
           "nearly half in KS/TX/NE/OK",
           "ACADEMIC", "J Rural Health 2026",
           "https://doi.org/10.1111/jrh.70112"),
        _E(">808,000 Americans living with ESRD, ~68% on dialysis — the "
           "recurring-transport base",
           "GOV", "NIDDK / USRDS kidney disease statistics (re-verify)",
           "https://www.niddk.nih.gov/health-information/health-statistics/kidney-disease"),
    ),
    subqs=(
        _S("Which care settings generate the most IFT demand?",
           "Inpatient floors (discharge legs — the volume engine) and "
           "EDs (~1.97M adult transfers/yr), then SNFs (to-hospital and "
           "to-dialysis round trips) and dialysis schedules."),
        _S("Which settings receive the most transferred patients?",
           "SNFs by count (~1.8M Medicare-covered stays/yr), tertiary/"
           "quaternary hubs by acuity, then IRF (~383k stays), LTACH "
           "(~90k cases) and hospice — every one an inbound IFT leg."),
        _S("How does demand differ across: Emergency departments? "
           "Freestanding emergency departments? Community hospitals? "
           "Academic and tertiary hospitals? Specialty hospitals? "
           "Behavioral health facilities? Rehabilitation facilities? "
           "Skilled nursing facilities? Long-term acute care hospitals? "
           "Dialysis centers? Outpatient sites? Patient residences?",
           "EDs: urgent up-transfers (2.4-2.8% of visits; 6.2% rural). "
           "Freestanding EDs: transfer everything they admit — no beds. "
           "Community hospitals: send acuity up, receive repatriations. "
           "Academic/tertiary: net receivers inbound, discharge and "
           "repatriation engines outbound. Specialty hospitals: "
           "scheduled inbound admissions. Behavioral: secure transfers "
           "off ~6M MH ED visits/yr. IRF/rehab: scheduled stretcher "
           "inbound (~383k stays). SNFs: the biggest two-way node. "
           "LTACHs: vent-level inbound (~90k). Dialysis: fixed 3x/week "
           "round trips. Outpatient sites: episodic wheelchair legs. "
           "Residences: discharge endpoints and recurring-trip "
           "origins."),
        _S("Which settings rely most heavily on ambulance transport?",
           "The acute-to-acute lanes (ED up-transfers, ICU moves, "
           "LTACH admissions) and behavioral transfers — monitoring, "
           "equipment or security needs rule lower tiers out."),
        _S("Which settings rely more heavily on wheelchair or "
           "stretcher transportation?",
           "Med-surg-to-SNF discharges, dialysis and clinic round "
           "trips, and facility-to-residence legs — ambulatory or "
           "stable-bedbound patients with no en-route monitoring "
           "need."),
    ),
)


_MOVEMENTS = Block(
    "q3-movements", "Major patient movements",
    conclusion=(
        "The journey decomposes into a small set of repeating routes — "
        "ED-to-hub escalation, inpatient-to-post-acute step-down, "
        "recurring dialysis round trips, hub-to-spoke repatriation, and "
        "behavioral placement — and they are different businesses: "
        "volume concentrates in step-down and recurring legs, revenue "
        "per trip in escalation, and each route deserves its own "
        "operating and pricing treatment."),
    why_true=(
        "The escalation lane is measured at ~1.97M adult ED-to-ED "
        "transfers/yr plus ~1.5M inpatient moves; it skews high-acuity "
        "(volume-weighted ~56% CCT/SCT/specialty in the mapped "
        "escalation book) and time-critical (STEMI/stroke windows).",
        "The step-down lane is the volume engine: ~1.8M Medicare SNF "
        "stays, ~383k IRF stays and ~90k LTACH cases a year, every one "
        "an inbound transport, mostly scheduled BLS/stretcher — plus "
        "home-health and hospice tails.",
        "Recurring treatment is the metronome: dialysis at 3 "
        "sessions/week per patient generates the round-trip base "
        "Medicare's RSNAT rules were built to police; repatriation "
        "mirrors escalation (~1:1 per episode where systems run it), "
        "doubling mission count per transfer episode.",
        "Economics differ by route: SCT bills 3.25x the BLS relative "
        "value (~$907 vs ~$279 national base), while long rural "
        "one-ways and dialysis post-RSNAT sit at the "
        "necessary-but-unattractive end — route mix IS the P&L."),
    why_matters=(
        "Treating IFT as one market blends five submarkets with "
        "different urgency, modality, wait and deadhead profiles — the "
        "operator and the investor both need the route-level view to "
        "know what is being won and what it costs to serve."),
    evidence=(
        _E("~1.97M adult ED-to-ED transfers/yr (NEDS 2018-2022); ~1.5M "
           "inpatient interhospital transfers/yr (NIS)",
           "ACADEMIC", "Nikolla et al., J Emerg Med 2025; Mueller et "
           "al., 2014",
           "https://doi.org/10.1016/j.jemermed.2025.12.020"),
        _E("Medicare fee ladder: SCT (A0434) 3.25 RVU vs BLS 1.00 → "
           "~$907 vs ~$279 national base at the CY2025 conversion "
           "factor $278.98",
           "DERIVED", "CMS AFS RVUs x CY2025 CF (re-verify CF against "
           "the PUF); base = CF x RVU", ""),
        _E("Post-acute volumes: ~1.8M Medicare-covered SNF stays/yr, "
           "~383k IRF stays, ~90k LTACH cases",
           "GOV", "MedPAC payment-basics series (SNF/IRF/LTCH)", ""),
        _E("Repatriation/back-transfer runs ~1:1 with escalations "
           "where systems operate it — the return leg roughly doubles "
           "missions per transfer episode",
           "FRAMEWORK", "ift_clinical_demand load-balancing registry "
           "(no defensible single national count; mirrors up-transfer "
           "volume)", ""),
    ),
    subqs=(
        _S("What are the most common origin-destination pairs?",
           "ED→tertiary hub; inpatient floor→SNF/IRF/LTACH; "
           "hospital→home/hospice; SNF↔hospital; facility↔dialysis; "
           "hub→origin community hospital (repatriation)."),
        _S("Which routes generate the highest trip volume?",
           "Step-down and recurring: discharge-to-post-acute legs and "
           "dialysis round trips dwarf the acute lanes trip-for-trip."),
        _S("Which routes generate the highest revenue?",
           "Escalation CCT/SCT legs (3.25x BLS relative value, "
           "commercial ~2x Medicare on top) and long loaded-mile "
           "corridors with paying coverage."),
        _S("Which routes require the highest clinical acuity?",
           "ICU-to-ICU escalations (cardiogenic shock, ARDS/ECMO "
           "candidates), neonatal/peds team transfers, and "
           "vent-dependent LTACH admissions."),
        _S("Which routes are most time-sensitive?",
           "STEMI and stroke up-transfers (DIDO guidelines: 30 and 120 "
           "minutes; medians 68 and 174 minutes — mostly missed), "
           "trauma and obstetric emergencies."),
        _S("Which routes are typically scheduled?",
           "Post-acute discharges (SNF/IRF/LTACH admissions book "
           "hours-to-days ahead), dialysis and treatment round trips, "
           "repatriations, and direct admits with a reserved bed."),
        _S("Which routes are most likely to require a return trip?",
           "Dialysis and clinic runs (round trips by definition), "
           "SNF-to-ED evaluations that bounce back, and every "
           "escalation a hub intends to repatriate."),
        _S("Which routes involve the greatest wait time?",
           "Discharge legs — patient-not-ready at the sending floor "
           "and paperwork at the receiving SNF; ED-origin urgent legs "
           "wait on the referring hospital's workup (82.8% of transfer "
           "time sits there)."),
        _S("Which routes produce the most empty mileage?",
           "Rural long one-ways (spoke-to-hub with no backhaul) and "
           "any corridor without paired repatriation flow — Medicare "
           "pays loaded miles only, so these routes carry a structural "
           "deadhead tax."),
        _S("Which movements should be treated as distinct submarkets?",
           "Five: acute escalation (up), post-acute step-down (down), "
           "recurring treatment (round trip), repatriation/load-"
           "balancing (lateral), and behavioral placement — different "
           "urgency, modality, waits and economics."),
    ),
)


_REASONS = Block(
    "q3-reasons", "Reason for transportation",
    conclusion=(
        "Every IFT trip exists because required care and the patient are "
        "in different buildings — capability gaps pull patients up, "
        "recovery pushes them down, treatment schedules cycle them, and "
        "capacity management shuffles them laterally; delay-sensitivity "
        "tracks the reason, from minutes (STEMI, stroke) to days "
        "(placement)."),
    why_true=(
        "Capability gaps are widening structurally: 331 rural hospitals "
        "dropped obstetrics 2011-2024, 194 rural hospitals have closed "
        "since 2005, and REH conversions eliminate inpatient beds "
        "outright — each service cut converts local admissions into "
        "transfers (51.6% of Nebraska counties are already "
        "maternity-care deserts).",
        "Step-down reasons are payment-defined: IRF admission turns on "
        "3-hour therapy tolerance and the 60%-rule conditions, LTACH "
        "rates on ≥3 ICU days or ≥96 vent-hours, SNF on the 3-day "
        "qualifying stay — the reason for the trip is written in the "
        "post-acute rulebook.",
        "Capacity management is a real and growing reason: transfer "
        "centers decompress boarding EDs and full hubs by moving "
        "patients to open beds (Intermountain diverted >5,100 "
        "quaternary bed-days over 4 years), and repatriation frees hub "
        "beds by sending recovered patients back.",
        "Delay-sensitivity orders the reasons: STEMI transfer DIDO >30 "
        "minutes carries an adjusted mortality odds ratio of 1.56; a "
        "lost SNF placement, by contrast, costs bed-days rather than "
        "survival — same market, different clocks."),
    why_matters=(
        "The reason for the trip predicts its urgency, modality, payer "
        "and failure cost better than any other single attribute — a "
        "provider that triages its book by reason is pricing and "
        "staffing the real risk."),
    evidence=(
        _E("331 rural hospitals stopped offering OB services 2011-2024 "
           "(~27% of rural OB units); Iowa lost 22 facilities, the most "
           "of any state",
           "SOURCED", "Chartis rural health state-of-the-state "
           "(re-verify)",
           "https://www.chartis.com/insights/2025-rural-health-state-state"),
        _E("STEMI transfer: median DIDO 68 min, only 11% ≤30 min; DIDO "
           ">30 min associated with 5.9% vs 2.7% mortality, adjusted OR "
           "1.56 (95% CI 1.15-2.12)",
           "ACADEMIC", "Wang et al., JAMA 2011 (n=14,821)",
           "https://doi.org/10.1001/jama.2011.862"),
        _E("194 rural hospital closures since 2005 (151 after 2010); "
           "432 more at risk",
           "SOURCED", "UNC Sheps Center tracker; Chartis 2025 "
           "(re-verify)",
           "https://www.shepscenter.unc.edu/programs-projects/rural-health/rural-hospital-closures/"),
        _E("Mental-health-related ED visits ~6M/yr (~1 in 8 ED visits "
           "MH/SUD) — the behavioral-placement demand base",
           "GOV", "CDC/SAMHSA ED utilization", ""),
    ),
    subqs=(
        _S("Why is the patient being transported?",
           "Because required care and the patient are in different "
           "buildings — a capability gap (up), recovery to a lower "
           "setting (down), a recurring treatment (cycle), a placement "
           "(behavioral/post-acute), or a capacity decision (lateral)."),
        _S("Is the patient moving to receive a higher level of care?",
           "The escalation family: ~1.97M ED transfers/yr led by "
           "cardiac, stroke, sepsis, respiratory failure and trauma — "
           "urgent-to-critical, ambulance-tier by definition."),
        _S("Is the patient moving because a specialty service is "
           "unavailable?",
           "Increasingly — 331 rural OB closures, thinning cardiology "
           "and psychiatry coverage, and REH conversions make "
           "'we don't offer that here' a growing share of transfers."),
        _S("Is the patient being discharged to post-acute care?",
           "The highest-volume reason: SNF/IRF/LTACH/hospice "
           "admissions off ~35M annual discharges — scheduled, "
           "repeatable, and the throughput lever hospitals feel most."),
        _S("Is the patient returning to the original facility?",
           "Repatriation — the deliberate return leg that frees hub "
           "beds; roughly paired 1:1 with escalations where systems "
           "run it as policy."),
        _S("Is the patient traveling for a recurring treatment?",
           "Dialysis dominates (3 sessions/week; >808k ESRD patients, "
           "~68% on dialysis), plus wound care, radiation and "
           "infusion — the schedulable metronome of the book."),
        _S("Is the trip driven by behavioral health placement?",
           "A distinct lane: medically-cleared psychiatric patients "
           "boarding in EDs until a bed opens — low medical acuity, "
           "security/monitoring needs, often long legs to wherever "
           "the bed is."),
        _S("Is the trip driven by hospital capacity management?",
           "Yes and growing — transfer-center load-balancing moves "
           "patients from full hubs to open system beds; boarding "
           "pressure makes this the fastest-emerging reason."),
        _S("Is the patient moving within the same health system or "
           "outside it?",
           "Consolidation pulls trips intra-system (70% of community "
           "hospitals are system-affiliated; intra-IDN lanes like "
           "CHI's Omaha-Kearney-Lincoln web), while capability gaps "
           "still force out-of-system escalations."),
        _S("Which transfer reasons are most sensitive to delay?",
           "Time-critical escalations (STEMI OR 1.56 mortality beyond "
           "30-min DIDO; stroke, trauma, obstetric emergencies), then "
           "placement-window trips (a bed released to the next "
           "referral), then scheduled treatments (a missed dialysis "
           "slot becomes an emergent visit)."),
    ),
)


_URGENCY = Block(
    "q3-urgency", "Urgency and scheduling",
    conclusion=(
        "The journey sorts into three clocks — emergent (minutes: STEMI, "
        "stroke, trauma, neonatal), urgent-but-not-emergent "
        "(minutes-to-hours: general up-transfers, direct admits, "
        "decompression) and scheduled (hours-to-days: discharges, "
        "recurring treatment, repatriation) — and each clock has its own "
        "booking horizon, after-hours profile and routing logic."),
    why_true=(
        "The emergent slice is small and rising: 6.6% of adult ED "
        "transfers involve a critical procedure (OR 1.09/yr), and the "
        "guideline clocks (STEMI 30-minute, stroke 120-minute DIDO) are "
        "mostly missed today — medians 68 and 174 minutes.",
        "The scheduled book has regulatory proof of its bookability: "
        "RSNAT prior-auth affirms 120 round trips per 180 days in "
        "advance, and post-acute admissions clear insurance and bed "
        "acceptance before the trip is booked.",
        "Readiness at request time is the weak link in scheduling: "
        "boarding data (85.2% of admitted seniors ≥2h) and "
        "referring-hospital DIDO dominance show the patient frequently "
        "is not ready at the stated time — requested times are "
        "estimates, not commitments, unless workflow makes them real.",
        "After-hours load is structural, not incidental: urgent "
        "transfers follow ED peaks into evenings and weekends, "
        "behavioral placements often move at night when beds post, "
        "while SNFs stop accepting in the late afternoon — the urgent "
        "book requires 24/7; the scheduled book clusters in business "
        "hours."),
    why_matters=(
        "Urgency mix is the staffing model: the scheduled clock can be "
        "planned to high utilization, the urgent clock needs promised "
        "windows, the emergent clock needs held capacity — pricing and "
        "rostering follow the three clocks, not the average."),
    evidence=(
        _E("6.6% of adult ED transfers involved a critical procedure, "
           "rising at OR 1.09/yr — the emergent readiness slice",
           "ACADEMIC", "Nikolla et al., J Emerg Med 2025",
           "https://doi.org/10.1016/j.jemermed.2025.12.020"),
        _E("Stroke transfer median DIDO 174 min (IQR 116-276); only "
           "27.3% within the 120-min guideline",
           "ACADEMIC", "JAMA 2023 (GWTG-Stroke, n=108,913)",
           "https://doi.org/10.1001/jama.2023.12739"),
        _E("RSNAT: repetitive non-emergent transport defined as 3+ "
           "round trips in 10 days or 1+/week for 3+ weeks; one "
           "affirmation covers 120 round trips over 180 days",
           "GOV", "CMS RSNAT prior-authorization model rules", ""),
        _E("85.2% of admitted ED patients 65+ boarded ≥2 hours — "
           "stated readiness times routinely slip on the hospital "
           "side",
           "ACADEMIC", "Lee et al., Ann Emerg Med 2026 (NHAMCS)",
           "https://doi.org/10.1016/j.annemergmed.2026.03.011"),
    ),
    subqs=(
        _S("Which transitions are emergent?",
           "STEMI, stroke and trauma up-transfers, obstetric and "
           "neonatal emergencies, ICU-to-ICU rescue moves — the "
           "critical-procedure slice (6.6% of ED transfers) plus "
           "guideline-clocked escalations."),
        _S("Which are urgent but not emergent?",
           "The general ED up-transfer book, direct admits with a "
           "waiting bed, ED-decompression moves, and SNF-to-hospital "
           "evaluations — minutes-to-hours windows with a promised "
           "ETA."),
        _S("Which are scheduled?",
           "Discharges to SNF/IRF/LTACH/home, dialysis and treatment "
           "round trips, repatriations, and planned direct admissions "
           "— bookable hours to days ahead."),
        _S("How far in advance can each trip type be booked?",
           "Recurring: weeks (standing orders; RSNAT affirms 180-day "
           "blocks). Discharges: hours to a day. Urgent: minutes to "
           "hours. Emergent: none — held capacity, not booking."),
        _S("How frequently does the requested pickup time change?",
           skip="Not published — reschedule rates per booked trip; an "
                "operator/hospital timestamp metric, a diligence "
                "request."),
        _S("How often is the patient ready at the requested time?",
           skip="Not published nationally — patient-not-ready rates "
                "are operator door-timestamp data; the boarding and "
                "DIDO evidence implies readiness slips are routine, "
                "but the rate is a diligence request."),
        _S("Which trip types most frequently occur after hours?",
           "Urgent up-transfers (ED peaks run into the night), "
           "behavioral placements (beds post at all hours), and "
           "load-balancing moves — the scheduled book is daytime-"
           "weekday by construction."),
        _S("Which require 24/7 availability?",
           "The emergent and urgent lanes — EMTALA-driven "
           "up-transfers, behavioral placement and hub decompression "
           "do not observe business hours; discharge and recurring "
           "lanes do."),
        _S("Which trip types can be routed together?",
           "Recurring dialysis/clinic runs (batchable by schedule and "
           "geography), wheelchair discharge legs, and paired "
           "discharge+repatriation flows on the same corridor — the "
           "chaining book."),
        _S("Which require immediate point-to-point service?",
           "Emergent escalations (STEMI/stroke/trauma/neonatal) and "
           "any CCT move with active drips or vent support — no "
           "multi-stop routing, crew and vehicle committed door to "
           "door."),
    ),
)


_MODALITY = Block(
    "q3-modality", "Modality and acuity",
    conclusion=(
        "Each journey leg carries a characteristic modality — wheelchair "
        "van for ambulatory discharge and clinic runs, BLS stretcher for "
        "stable post-acute admissions, ALS/ALS2 for monitored patients, "
        "CCT/SCT plus specialty teams for the escalation book — and the "
        "scarce end of the ladder (CCT, neonatal/peds teams, secure "
        "behavioral) is where capacity constraints bind."),
    why_true=(
        "The tier is set by en-route need, not diagnosis: monitoring "
        "(cardiac, post-event neuro checks), oxygen and airway "
        "(COPD/pneumonia recovery, vent dependence), IV therapy "
        "(insulin or vasopressor drips → ALS2/CCT), ventilators "
        "(ARDS escalations, LTACH admissions), and specialty crews "
        "(neonatal isolette, peds, ECMO, balloon pump) map directly to "
        "the Medicare ladder from A0428 to A0434.",
        "The mapped escalation book skews high: volume-weighted, ~56% "
        "of escalation scenarios sit at CCT/SCT or specialty-team tier "
        "versus ~12% ALS and ~32% low-acuity/behavioral — while the "
        "step-down book inverts toward BLS and wheelchair.",
        "Over-triage concentrates where documentation meets habit "
        "(stretcher ordered for a chair-capable discharge; ambulance "
        "for a wheelchair-appropriate dialysis run) — no interfacility-"
        "specific rate is published, but CERT's 27.5% medical-necessity "
        "share of ambulance improper payments shows the payer sees it "
        "constantly.",
        "Under-triage risk concentrates in escalations: the patient "
        "who looked BLS-stable at dispatch and needed critical "
        "intervention en route — the rising critical-procedure share "
        "(6.6%, OR 1.09/yr) says this tail is growing, and it is the "
        "reason up-transfer tiering errs high."),
    why_matters=(
        "Modality mix is both the safety envelope and the cost "
        "structure: the low tiers are won on price and routing, the "
        "high tiers on credentialed-crew scarcity — a network that "
        "fields the whole ladder can price each leg on its own "
        "economics instead of averaging them."),
    evidence=(
        _E("Escalation transport mix, volume-weighted: ~56% "
           "CCT/SCT/neonatal/peds, ~12% ALS/ALS2, ~32% low-acuity "
           "incl. behavioral; step-down book skews BLS/wheelchair",
           "DERIVED", "ift_clinical_demand.mission_mix() — GOV volumes "
           "x authored acuity tiers (share = tier volume / family "
           "volume)", ""),
        _E("Medicare ambulance ladder: BLS 1.00 → ALS1 1.20/1.90 → "
           "ALS2 2.75 → SCT 3.25 relative values; ESRD dialysis BLS "
           "non-emergency pays fee schedule minus 23%",
           "GOV", "CMS AFS RVUs / 42 CFR 414 subpart H",
           "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-414/subpart-H"),
        _E("Ambulance medical necessity gates the low end: bed-confined "
           "(all three functional criteria) or condition-"
           "contraindicated — otherwise wheelchair/stretcher-van "
           "territory (Medicare pays $0 for stretcher van)",
           "GOV", "42 CFR 410.40(e); HCPCS T2049 state placements",
           "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-410/subpart-B/section-410.40"),
        _E("Ambulance improper payment 13.2% / $595.1M projected; "
           "27.5% medical necessity — the over-tiering audit trail",
           "GOV", "CMS CERT 2024 supplemental (re-verify)", ""),
    ),
    subqs=(
        _S("What modality is typically used for each major transition?",
           "ED→hub: ALS-to-CCT. ICU→ICU/LTACH: CCT, often vented. "
           "Floor→IRF/SNF: BLS stretcher (wheelchair when ambulatory). "
           "Dialysis/clinic: wheelchair van. Behavioral: secure "
           "BLS-with-monitoring. Repatriation: BLS."),
        _S("What determines whether a patient needs wheelchair, "
           "stretcher, BLS, ALS, or critical care?",
           "En-route requirements: ambulation/bed-confinement, "
           "monitoring, oxygen/airway, IV therapy intensity, vent "
           "dependence, and behavioral risk — codified for Medicare in "
           "410.40's necessity criteria."),
        _S("Which clinical conditions require monitoring?",
           "Cardiac transfers (chest pain, post-MI, arrhythmia), "
           "sepsis on treatment, post-stroke and post-seizure "
           "patients, high-risk OB — anything where deterioration "
           "en route is plausible."),
        _S("Which require oxygen?",
           "Respiratory legs: COPD and pneumonia escalations and "
           "recoveries, vent-weaning LTACH admissions, home-oxygen "
           "patients on any leg."),
        _S("Which require IV support?",
           "Active infusion legs — sepsis on antibiotics/pressors, "
           "DKA on insulin, cardiac drips — the ALS2/CCT boundary "
           "(≥3 medication administrations or an ALS procedure defines "
           "ALS2)."),
        _S("Which require a ventilator?",
           "ARDS/respiratory-failure escalations (to ECMO-capable "
           "centers at the extreme) and the post-vent LTACH admission "
           "stream (≥96 vent-hours qualifies the LTCH rate) — "
           "CCT-tier by definition."),
        _S("Which require specialty crews?",
           "Neonatal (isolette team), pediatric critical care, ECMO "
           "and balloon-pump moves, and bariatric logistics — "
           "hospital-affiliated or contracted specialty teams, the "
           "scarcest crew type."),
        _S("Which transitions most frequently involve over-triage?",
           "Discharge legs (stretcher ordered for chair-capable "
           "patients) and recurring dialysis runs booked as ambulance "
           "— no published interfacility rate; the CERT "
           "medical-necessity findings are the payer-side shadow of "
           "it."),
        _S("Which transitions carry the greatest risk of under-triage?",
           "Urgent up-transfers dispatched BLS on a stable snapshot — "
           "sepsis, GI bleed and cardiac patients who deteriorate en "
           "route; the growing critical-procedure share says the tail "
           "is fattening."),
        _S("Which modalities are capacity constrained?",
           "CCT/SCT (credentialed nurses/paramedics are the "
           "bottleneck), neonatal/peds teams (few per region), and "
           "secure behavioral transport — the tiers where acceptance "
           "fails first."),
    ),
)


_PROCESS = Block(
    "q3-process", "Request and handoff process",
    conclusion=(
        "An IFT trip is a relay of at least six roles — orderer, "
        "readiness confirmer, destination acceptor, clinical documenter, "
        "modality selector, and handoff nurse — run today as sequential "
        "phone calls; the measured timelines say the stall lives in the "
        "referring facility's disposition-to-departure interval, exactly "
        "the segment parallel workflow and early booking compress."),
    why_true=(
        "The roles are stable across transitions: bedside/case "
        "management or the transfer center initiates; the sending nurse "
        "confirms readiness; the receiving physician plus bed "
        "management accept (EMTALA obliges an appropriate transfer with "
        "qualified personnel and equipment); the ordering clinician "
        "sets modality and signs the PCS for non-emergency Medicare "
        "trips; crews and nurses execute the physical handoff.",
        "The steps run sequentially by habit, not necessity: "
        "destination acceptance, transport booking and paperwork can "
        "proceed in parallel once disposition is decided — the "
        "sequential phone chain is why the imaging-to-door interval "
        "(153.1 of 171.4 DIDO minutes) dwarfs the clinical workup "
        "(18.3 minutes).",
        "Arrival monitoring is the orphan step: no role owns watching "
        "the trip, so status flows only when someone calls — the "
        "operational gap integrated status feeds exist to fill.",
        "The stall point is documented at the referring side: 82.8% of "
        "stroke-transfer time accrues at the primary center, and EMS "
        "prenotification (a process change alone) cuts 20.1 minutes — "
        "process, not distance, is the controllable variable."),
    why_matters=(
        "Whoever fixes the relay owns the account: the provider that "
        "slots into the process as its coordinator — booking early, "
        "parallelizing confirmation, pushing status — removes the "
        "stall the hospital cannot remove alone, and becomes very hard "
        "to unwire."),
    evidence=(
        _E("EMTALA appropriate-transfer duties: the sending hospital "
           "must effect transfer through qualified personnel and "
           "transportation equipment, with receiving-facility "
           "acceptance and records",
           "GOV", "42 CFR 489.24",
           "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-489/subpart-B/section-489.24"),
        _E("Non-emergency Medicare trips require a signed physician "
           "certification statement; repetitive PCS in advance, dated "
           "≤60 days; a PCS alone does not establish necessity",
           "GOV", "42 CFR 410.40; MAC guidance (re-verify)", ""),
        _E("Mean DIDO 171.4 min = 18.3 door-to-imaging + 153.1 "
           "imaging-to-door — the disposition/transport interval is "
           "the stall",
           "ACADEMIC", "JAMA Network Open 2024 (n=28,887)",
           "https://doi.org/10.1001/jamanetworkopen.2024.31183"),
        _E("EMS prenotification associated with 20.1 min shorter "
           "stroke DIDO — a pure process lever, no new vehicle or "
           "road",
           "ACADEMIC", "JAMA 2023 (GWTG-Stroke)",
           "https://doi.org/10.1001/jama.2023.12739"),
    ),
    subqs=(
        _S("Who initiates the trip for each transition?",
           "Up-transfers: the referring clinician via the transfer "
           "center. Discharges: case management/discharge planning. "
           "Recurring: standing orders. SNF-to-hospital: the SNF "
           "nurse. Load-balancing: the capacity hub."),
        _S("Who confirms the patient is ready?",
           "The sending bedside nurse — meds given, lines secured, "
           "paperwork and belongings assembled; the step that most "
           "often slips against the stated time."),
        _S("Who confirms that the destination can receive the "
           "patient?",
           "The receiving physician (clinical acceptance) plus bed "
           "management/admissions (physical acceptance) — for "
           "EMTALA transfers, documented acceptance is a legal "
           "precondition."),
        _S("Who provides the patient's clinical information?",
           "The sending clinician: report to the receiving team, the "
           "transfer packet, and for non-emergency Medicare trips the "
           "PCS establishing transport-level necessity."),
        _S("Who selects the modality?",
           "The ordering clinician, constrained by 410.40 necessity "
           "criteria; dispatch can query a mismatch but the order is "
           "clinical."),
        _S("Who communicates with the provider?",
           "Usually a unit clerk, case manager or transfer-center "
           "coordinator by phone — the role integration replaces with "
           "a booking interface."),
        _S("Who monitors arrival?",
           "In the default process, nobody — the floor discovers "
           "lateness by noticing; assigning this step (or automating "
           "it with pushed ETAs) is a cheap, high-value fix."),
        _S("Who completes the handoff?",
           "Sending nurse to transport crew at the origin bedside; "
           "crew to receiving nurse at the destination — two clinical "
           "handoffs per trip, each a timestamp and a liability "
           "boundary."),
        _S("Which steps occur sequentially?",
           "Today: decision → acceptance → readiness → booking → "
           "pickup, each waiting on the prior phone call — booking "
           "last is why the truck arrives to a patient who has been "
           "'ready' for an hour, or waits for one who is not."),
        _S("Which can occur in parallel?",
           "Acceptance, transport booking, PCS/paperwork and "
           "readiness preparation can all run from the moment "
           "disposition is decided — prenotification's measured 20-min "
           "saving is this parallelism applied to one lane."),
        _S("Where does the process most often stall?",
           "Inside the referring facility between disposition and "
           "departure — 82.8% of transfer time, 153 of 171 DIDO "
           "minutes — with destination-acceptance hunting (especially "
           "behavioral and SNF placement) the runner-up."),
    ),
)


_DELAY = Block(
    "q3-delay", "Consequences of delay",
    conclusion=(
        "Transport delay converts into the hospital's scarcest "
        "commodities at a measured exchange rate: boarding hours in the "
        "ED, occupied staffed beds, lost placements and reversed "
        "discharges on the floors, and — on time-critical escalations — "
        "mortality; the sending facility retains clinical and legal "
        "responsibility for the patient until handoff, so every delayed "
        "minute stays on its ledger."),
    why_true=(
        "The clinical exchange rate is published: STEMI transfers with "
        "DIDO >30 minutes carried 5.9% vs 2.7% in-hospital mortality "
        "(adjusted OR 1.56); stroke guidelines set 120 minutes and the "
        "national median is 174 — delay on these lanes is an outcomes "
        "variable, not an inconvenience.",
        "The capacity exchange rate is published too: mean boarding "
        "for admitted seniors rose from 138 to 343 minutes (501 with "
        "dementia); delayed discharges average 22.8% of stays across "
        "64 studies; one US academic center found 3.5% of "
        "hospitalizations consumed 27.2% of bed-days — and the "
        "dominant non-medical barrier was facility placement, the "
        "step a missed transport window re-opens.",
        "Placement and reversal are real cliff effects: SNFs stop "
        "accepting in the late afternoon, so a slipped pickup loses "
        "the bed to the next referral, un-discharges the patient, and "
        "buys another inpatient day (hospital expense averages "
        "~$3,132/day as a cost proxy).",
        "Until the destination handoff, the sending facility keeps "
        "medication schedules, monitoring and EMTALA responsibility — "
        "and the receiving side pays in disrupted staffing: admission "
        "slots, therapy schedules and dialysis chairs held for a "
        "patient who arrives hours late or not at all."),
    why_matters=(
        "This is the buyer's arithmetic for the whole study: transport "
        "is bought by the trip but its failures are priced in "
        "bed-days, boarding hours and outcomes — which is why "
        "reliability, not rate, is the rational purchasing criterion "
        "and why the dedicated model has a willing customer."),
    evidence=(
        _E("STEMI DIDO >30 min: mortality 5.9% vs 2.7%, adjusted OR "
           "1.56 (95% CI 1.15-2.12); only 11% of transfers met 30 min",
           "ACADEMIC", "Wang et al., JAMA 2011",
           "https://doi.org/10.1001/jama.2011.862"),
        _E("Mean ED boarding for admitted patients 65+: 138 min (2018) "
           "→ 343 min (2022); 501 min with Alzheimer's-related "
           "dementia; 85.2% boarded ≥2h",
           "ACADEMIC", "Lee et al., Ann Emerg Med 2026 (NHAMCS)",
           "https://doi.org/10.1016/j.annemergmed.2026.03.011"),
        _E("Delayed discharges: weighted mean 22.8% of stays (range "
           "1.6-91.3%) across 64 studies; delay costs $142-$31,935 "
           "PPP-adjusted",
           "ACADEMIC", "Landeiro et al., The Gerontologist 2019",
           "https://doi.org/10.1093/geront/gnx028"),
        _E("3.5% of hospitalizations accounted for 27.2% of 23,934 "
           "inpatient days; the most common non-medical barrier at "
           "every timepoint was facility placement",
           "ACADEMIC", "Gao & Berland, Brown J Hosp Med 2022",
           "https://doi.org/10.56305/001c.36593"),
        _E("Hospital adjusted expense per inpatient day ~$3,132 (2023) "
           "— the bed-day cost proxy for delay arithmetic",
           "SOURCED", "KFF state health facts (expense proxy, not "
           "marginal cost) (re-verify)", ""),
    ),
    subqs=(
        _S("What happens if the trip is delayed by 30 minutes?",
           "A bed stays blocked, a discharge window narrows, crew and "
           "receiving slots idle — and on STEMI/stroke lanes 30 "
           "minutes is the measured mortality threshold, not a grace "
           "period."),
        _S("What happens if it is delayed by several hours?",
           "The placement can lapse, the discharge reverses, the "
           "patient re-boards, after-hours receiving windows close — "
           "the trip often rolls to tomorrow and the hospital buys "
           "the bed-day."),
        _S("Can the destination placement be lost?",
           "Yes — SNF and behavioral beds are released to the next "
           "referral when the patient misses the acceptance window; "
           "placement was the dominant non-medical discharge barrier "
           "in the measured cohort."),
        _S("Can the patient's discharge be reversed?",
           "Yes — a missed late-afternoon window un-discharges the "
           "patient: orders reinstated, bed re-occupied, the whole "
           "relay re-run the next day."),
        _S("Can the delay create another inpatient day?",
           "Directly — that is the standard failure: a slipped "
           "pickup past the receiving cutoff converts into a full "
           "extra day at ~$3,132 expense per day, with delayed-"
           "discharge patients consuming bed-days far out of "
           "proportion to their numbers."),
        _S("Does the sending facility retain responsibility for "
           "medications and monitoring?",
           "Yes — until handoff to the transport crew (and legally "
           "through an EMTALA-appropriate transfer), the sender owns "
           "med passes, monitoring and deterioration risk for a "
           "patient it has already clinically released."),
        _S("Does the receiving facility incur staffing disruption?",
           "Yes — admission nurses, therapy evaluations and dialysis "
           "chairs are scheduled against the promised arrival; a "
           "late patient wastes those slots and a very late one "
           "forfeits them."),
        _S("Can delays affect clinical outcomes?",
           "On time-critical lanes, measurably: STEMI DIDO >30 min "
           "carries adjusted mortality OR 1.56; stroke treatment is "
           "time-dependent and 72.7% of transfers miss the 120-min "
           "guideline."),
        _S("Which transitions create the greatest hospital-capacity "
           "impact?",
           "Outbound step-down legs — every delayed SNF/IRF/LTACH "
           "departure holds an acute bed, and boarding propagates the "
           "block back into the ED; load-balancing delays hold the "
           "scarcest (ICU/hub) beds of all."),
        _S("Which transitions create the greatest patient-experience "
           "impact?",
           "Behavioral placements (medically-cleared patients boarding "
           "days in EDs), elderly boarding (343-501 minute means), "
           "missed dialysis runs, and end-of-life hospice transfers "
           "where hours genuinely matter to families."),
    ),
)


Q3 = QuestionDef(
    num=3,
    slug="journey",
    title="Where does IFT fit into the patient journey?",
    storyline=(
        "IFT is the connective tissue of the care continuum: every "
        "escalation, step-down, recurring treatment, repatriation and "
        "placement is a mission with its own clock, modality and "
        "failure cost — and the measured stall sits inside the sending "
        "facility, which is why transport reliability is really "
        "hospital throughput."),
    visual_key="journey-map",
    blocks=(_SETTINGS, _MOVEMENTS, _REASONS, _URGENCY, _MODALITY,
            _PROCESS, _DELAY),
)

QUESTIONS = (Q2, Q3)
