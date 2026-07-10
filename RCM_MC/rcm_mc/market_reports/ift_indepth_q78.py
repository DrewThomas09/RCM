"""In-Depth content — Questions 7 (operational failures, quantified) and 8
(MMT's operating model).

Authored 2026-07-10 from the suite's cited corpus (ift_company, ift_mmt,
ift_geo presence tiers, ift_unit_economics, ift_growth_evidence,
ift_demand_evidence, ift_health_systems, ift_npi_landscape, ift_insourcing,
ift_study) plus the failure-quantification and NEMT/payment dossiers. Every
evidence line carries its basis + source; excerpt-grade captures carry
"(re-verify)". Q8 rule: answered from PUBLIC evidence where it exists;
company-internal figures are diligence requests, never inventions.
"""
from __future__ import annotations

from .ift_indepth import Block, Evidence, QuestionDef, SubQ

_E = Evidence
_S = SubQ


# ═════════════════════════════ QUESTION 7 ════════════════════════════════════

_MISMATCH = Block(
    "q7-mismatch", "Demand-capacity mismatch",
    conclusion=(
        "IFT demand exceeds capacity at predictable times, yet the shortfall "
        "is recorded almost nowhere: the one public footprint series (a "
        "statewide transfer center confirming 146 of 234, then 113 of 168, "
        "requested transfers) shows demand outrunning placement-plus-"
        "transport capacity, and the published economics say much of the "
        "'missing' capacity exists but is serving other masters — 911 "
        "readiness and better-paying books."),
    why_true=(
        "Peaks are calendar-shaped: discharge legs pile into weekday "
        "late-morning-to-evening windows and procedure schedules — the most "
        "forecastable demand of the three markets (Question 1) — so "
        "recurring shortfall is a planning-and-contracting failure, not an "
        "act of God.",
        "Capacity is often committed elsewhere rather than absent: shared "
        "911/IFT fleets shed scheduled transfers to protect response times, "
        "and thin-payer books get slow ETAs and quiet refusals — "
        "unavailability functioning as a price signal.",
        "The persistent floor is economic and demographic: 19.7% of "
        "transports collect nothing, labor is 70.7% of cost, and Nebraska's "
        "volunteer base (80%+ of agencies all-volunteer) is contracting — "
        "providers staff to the paying book, not the demand curve.",
        "Geography multiplies the gap: rural EDs transfer at 6.2% vs 2.0% "
        "urban — 3x the transfer propensity exactly where supply is "
        "thinnest and shrinking fastest."),
    why_matters=(
        "The shortfall queues inside the hospital (boarding, occupied "
        "beds), so diagnosing WHY capacity is short decides the remedy: "
        "if it is serving other customers, contracts with commitments fix "
        "it; if it genuinely does not exist, only capital and labor do."),
    evidence=(
        _E("Nebraska's statewide transfer center confirmed 146 of 234 "
           "requested transfers (Sep 2021) and 113 of 168 (Oct 2021) — "
           "measured episodes of demand exceeding capacity",
           "SOURCED", "Omaha World-Herald / Journal Star, Nov 2021 "
           "(re-verify)", ""),
        _E("19.7% of ambulance transports collect nothing; labor is 70.7% "
           "of cost — the economics behind selective availability",
           "SOURCED", "CMS/RAND GADCS Year 1-4 appendix (Dec 2025), via "
           "AAA coverage",
           "https://ambulance.org/2025/12/09/cms-releases-new-gadcs-report/"),
        _E("Rural EDs transfer 6.2% of visits vs 2.0% urban — the demand "
           "multiplier sits where supply is thinnest",
           "ACADEMIC", "Greenwood-Ericksen et al., JAMA Network Open 2021",
           "https://doi.org/10.1001/jamanetworkopen.2021.34980"),
        _E("80%+ of Nebraska EMS agencies are all-volunteer and the base "
           "is contracting — the rural slack is disappearing",
           "GOV", "NE DHHS Statewide EMS Assessment 2023-24 (re-verify)",
           "https://dhhs.ne.gov/OEHS%20Program%20Documents/NE%20Statewide%20EMS%20Assessment%20v2024.pdf"),
        _E("ED visits arriving by interfacility EMS transfer rose 35% "
           "(2020-22 vs 2014-16) — demand is measured to be growing into "
           "the gap",
           "ACADEMIC", "Peters et al., Am J Emerg Med 2026",
           "https://doi.org/10.1016/j.ajem.2026.04.025"),
    ),
    subqs=(
        _S("When does demand most frequently exceed capacity?",
           "Weekday discharge windows (late morning-evening) and ED census "
           "peaks; the measured Nebraska episodes were fall-2021 census "
           "surges layered on the structural floor."),
        _S("Which facilities experience the largest shortfalls?",
           "Rural/CAH senders — 3x the urban transfer propensity with the "
           "thinnest private supply; no national facility ranking is "
           "published."),
        _S("Which modalities are most constrained?",
           "CCT/SCT (scarce credentialed crews; the 6.6% critical-"
           "procedure transfer slice needs immediate readiness) and long "
           "rural one-way BLS legs nobody wants."),
        _S("Is insufficient capacity persistent or episodic?",
           "Both: a persistent thin-payer/rural floor, plus episodic "
           "census peaks — the Nebraska 2021 series shows episodes "
           "stacked on a floor."),
        _S("Are peaks predictable?",
           "Largely yes — discharge curves and procedure schedules are "
           "calendar-shaped; that predictability is what makes dedicated "
           "capacity plannable at all."),
        _S("Is capacity unavailable because it does not exist or because "
           "it is serving other customers?",
           "In metros, mostly serving other customers (911-shared trucks, "
           "better-paying books); in contracting volunteer rural "
           "territory, increasingly it does not exist."),
        _S("How much of the problem is caused by poor planning?",
           "No published decomposition — flagged; booking ahead of true "
           "readiness (the readiness block) is the observable "
           "planning-side failure."),
        _S("How much is caused by reimbursement economics?",
           "The structural share: a 19.7% never-paid rate and negative "
           "published mean spreads shrink supply to profitable corridors "
           "— Question 1's capacity mechanism."),
        _S("How much is caused by labor shortages?",
           "Labor is 70.7% of cost and the volunteer subsidy is "
           "dissolving — crews, not trucks, are the binding input."),
        _S("How much is caused by geographic coverage?",
           "Rural transfer propensity 3x urban against the thinnest, "
           "fastest-shrinking supply — geography converts modest demand "
           "into long unavailability windows."),
    ),
)


_ACCEPTANCE = Block(
    "q7-acceptance", "Trip acceptance and cancellation",
    conclusion=(
        "No national statistic measures IFT trip acceptance — the closest "
        "published gauges (a statewide transfer center confirming 62-67% of "
        "requests; NEMT brokers contracted to 85-95% on-time standards with "
        "documented misses) bracket a market where acceptance is informal, "
        "sequential, and unrecorded — and that absence of measurement is "
        "itself the finding."),
    why_true=(
        "The only public footprint series: Nebraska's statewide transfer "
        "center confirmed 146/234 (62%) and 113/168 (67%) of requested "
        "transfers — but the split between bed-declines and "
        "transport-declines is not published.",
        "The adjacent regulated market shows what measurement looks like: "
        "NEMT broker contracts carry 85-95% on-time-performance standards "
        "with penalties (Texas: 85% benchmark), and journalism still "
        "documented ~5.8% late/missed Modivcare trips in Mississippi (~3x "
        "the contractual limit) — where SLAs exist, misses get counted; in "
        "IFT they mostly are not.",
        "Call-list purchasing makes declination invisible: a trip refused "
        "by phone leaves no record, and the time consumed by sequential "
        "offering is published nowhere — flagged as a diligence stopwatch "
        "metric.",
        "Cancellation runs both directions — provider-side (crew coverage, "
        "prior trips running long) and hospital-side (patient not ready, "
        "bed lost, order changed) — and no public dataset separates them."),
    why_matters=(
        "An operator that logs acceptance, declines, and cancellations — "
        "with hospital-caused vs provider-caused attribution — converts an "
        "unmanaged failure into a contractible SLA; buyers should demand "
        "those logs in diligence rather than expect them in the "
        "literature."),
    evidence=(
        _E("Statewide transfer center confirmed 62% (Sep 2021) and 67% "
           "(Oct 2021) of requested transfers — placement + transport "
           "combined",
           "SOURCED", "Omaha World-Herald / Journal Star, Nov 2021 "
           "(re-verify)", ""),
        _E("Modivcare Mississippi: ~3,000 of >52,000 July trips late or "
           "missed (~5.8%) — roughly 3x the contractual limit; NJ fined "
           "Modivcare ~$1.7M (2017-22)",
           "SOURCED", "Mississippi Today, Sep 2024 (re-verify)", ""),
        _E("Texas Medical Transportation Program: 85% on-time-pickup "
           "benchmark with a $15,000 penalty cap — the SLA form IFT lacks",
           "SOURCED", "TX HHSC MTP contract terms (re-verify)", ""),
        _E("19.7% of transports collect nothing — the payer-mix mechanism "
           "behind quiet refusals",
           "SOURCED", "CMS/RAND GADCS Year 1-4 appendix, via AAA coverage",
           "https://ambulance.org/2025/12/09/cms-releases-new-gadcs-report/"),
    ),
    subqs=(
        _S("What percentage of trips are accepted?",
           "Not published for IFT; the Nebraska transfer-center series "
           "(62-67% of requests confirmed, placement + transport combined) "
           "is the only public footprint gauge."),
        _S("How long does acceptance take?",
           "No published figure — flagged; call-list markets take minutes "
           "to hours of sequential phoning (diligence: timestamped "
           "dispatch logs)."),
        _S("What percentage are declined?",
           "Not published; the 33-38% unconfirmed share in the Nebraska "
           "series is a ceiling proxy that includes bed declines."),
        _S("Why are trips declined?",
           "Crew unavailability, payer mix (thin-mix books draw quiet "
           "refusals), long one-way distance/deadhead, and acuity beyond "
           "the provider's credentialed capability."),
        _S("How frequently are accepted trips later canceled by the "
           "provider?", "",
           skip="Company data — diligence request: provider-initiated "
           "cancellation rate by cause code."),
        _S("Why do providers cancel?",
           "911 surges pulling shared trucks, crew callouts, and prior "
           "trips running long against detained-crew wall time — the "
           "documented shared-fleet mechanisms."),
        _S("How frequently does the health system cancel?", "",
           skip="Company data — diligence request: hospital-initiated "
           "cancellation share of booked trips."),
        _S("Why does the health system cancel?",
           "Patient not ready (paperwork, meds, final orders), receiving "
           "bed lost, clinical status change, or a duplicate booking "
           "placed across multiple vendors."),
        _S("How should cancellations caused by patient readiness be "
           "separated from provider performance?",
           "Timestamp booked-ready vs actually-ready vs vehicle-arrival "
           "and code the cause at cancellation — the attribution "
           "discipline NEMT SLAs already force on brokers."),
    ),
)


_ETA = Block(
    "q7-eta", "ETA reliability",
    conclusion=(
        "No published study measures IFT ETA accuracy — but the transfer-"
        "timing literature shows why promises fail: the transport-dependent "
        "interval dominates door-in-door-out time (153.1 of 171.4 mean "
        "minutes), and the upstream tail (crews detained over an hour at "
        "75% of California hospitals) makes any point-estimate ETA "
        "dishonest; the honest product is a distribution, updated live."),
    why_true=(
        "The interval an ETA promises is the one that dominates: stroke "
        "transfers spend a mean 153.1 of 171.4 door-in-door-out minutes "
        "AFTER imaging — the disposition-and-transport phase, not "
        "diagnostics, is the clock.",
        "Upstream variance is measured and large: three-quarters of "
        "California hospitals detained EMS crews more than one hour, 40% "
        "more than two, and a third more than three (830,637 transports, "
        "2017) — a crew's next ETA inherits the last hospital's wall time.",
        "The national median offload is benign (10.9 minutes) but 3.3% of "
        "agencies are chronically prolonged and the problem skews urban — "
        "tail risk, not the mean, is what breaks promised windows.",
        "Communication measurably moves the clock: EMS prenotification cut "
        "stroke door-in-door-out time by 20.1 minutes — evidence that "
        "information flow, not vehicle speed, is the recoverable ETA "
        "lever."),
    why_matters=(
        "An optimistic short ETA triggers premature patient prep, wasted "
        "nurse time, and forfeited re-planning; a contracted, measured, "
        "live-updated ETA is among the cheapest reliability upgrades a "
        "dedicated model sells — and nothing forces it in a call-list "
        "market."),
    evidence=(
        _E("Stroke transfer mean DIDO 171.4 min: door-to-imaging 18.3, "
           "imaging-to-door 153.1 — the transport-dependent interval "
           "dominates",
           "ACADEMIC", "JAMA Network Open 2024 (n=28,887)",
           "https://doi.org/10.1001/jamanetworkopen.2024.31183"),
        _E("California 2017: 75% of hospitals detained crews >1h, 40% "
           ">2h, 33% >3h (830,637 transports) — the upstream ETA tail",
           "ACADEMIC", "Backer et al., Prehospital Emergency Care 2018",
           "https://doi.org/10.1080/10903127.2018.1525456"),
        _E("National median ambulance patient offload time 10.9 min (IQR "
           "6.6-17.5); 3.3% of agencies had ≥25% of transports >30 min, "
           "skewed urban (7.24M records, 2024)",
           "ACADEMIC", "Shaw et al., Prehospital Emergency Care 2025",
           "https://doi.org/10.1080/10903127.2025.2535576"),
        _E("EMS prenotification cut stroke door-in-door-out time by 20.1 "
           "minutes — information flow moves the clock",
           "ACADEMIC", "GWTG-Stroke analysis, JAMA 2023 (n=108,913)",
           "https://doi.org/10.1001/jama.2023.12739"),
    ),
    subqs=(
        _S("How is the original ETA generated?",
           "In call-list markets, verbally by a dispatcher off unit "
           "intuition; CAD/AVL systems compute it from live position and "
           "drive time — there is no market standard."),
        _S("How accurate is it?",
           "No published IFT ETA-accuracy statistic — flagged; the DIDO "
           "spread (median 174, IQR 116-276 min for stroke) shows the "
           "transfer clock is wide even where measured."),
        _S("How frequently is it updated?",
           "Not published; phone-mediated markets update only on demand — "
           "someone has to call — which is the visibility failure of the "
           "communication block."),
        _S("How much variation exists between promised and actual "
           "arrival?",
           "Unmeasured publicly — diligence: request promised-vs-actual "
           "arrival distributions from operators; every modern CAD "
           "records both."),
        _S("Which trip types have the least reliable ETA?",
           "Urgent unscheduled legs competing with 911 surges, and long "
           "rural one-ways whose crews are exposed to offload detention "
           "at the prior hospital."),
        _S("Which providers have the most reliable ETA?",
           "Structurally, dedicated scheduled fleets that do not shed IFT "
           "to protect response times; no published provider ranking "
           "exists."),
        _S("How does ETA reliability change during peaks?",
           "Offload tails lengthen (the California detention "
           "distribution) and shared fleets re-task — promised windows "
           "widen exactly when beds are scarcest."),
        _S("How does it change after hours?",
           "Thinner staffed coverage lengthens response; no published "
           "after-hours IFT series — flagged."),
        _S("Is an inaccurate short ETA worse operationally than an "
           "accurate longer ETA?",
           "Yes — a false short ETA burns nurse prep, holds beds in "
           "limbo, and forfeits re-planning; an honest longer ETA lets "
           "the hospital schedule around it."),
    ),
)


_READINESS = Block(
    "q7-readiness", "Patient readiness",
    conclusion=(
        "The vehicle-waiting-on-patient problem is the mirror image of the "
        "patient-waiting-on-vehicle problem, and neither side is nationally "
        "measured: discharge-task audits find pending care-management/"
        "transportation the most frequent uncompleted item (47% at one "
        "site), while crews' unpaid wall time at hospital doors is the main "
        "controllable loss in IFT operations."),
    why_true=(
        "Readiness failure is documented as the dominant discharge-task "
        "gap: a single-site improvement audit found pending care-"
        "management/transportation needs the most frequent uncompleted "
        "discharge task (47%).",
        "The causes are a boring quartet — paperwork (PCS and orders), "
        "unfinished medications, unconfirmed receiving beds, and pending "
        "final physician orders — each named in the delayed-discharge "
        "literature's non-clinical factor lists.",
        "Booking runs ahead of truth: transport is ordered off predicted "
        "readiness to hedge slow vendors, so early vehicles wait — and "
        "Medicare pays nothing for waiting time, making the wait a pure "
        "provider loss that reprices into rates or refusals.",
        "In the one setting with a measured split (a 307-patient PACU "
        "cohort — a non-US single center, magnitude only), 61.2% of "
        "discharge delays were non-clinical, with transport unavailability "
        "(11.1%) second only to bed unavailability (22.5%)."),
    why_matters=(
        "Every idle vehicle-hour at a door is capacity subtracted from the "
        "next trip: synchronizing booking with true readiness (bed "
        "confirmed, PCS signed, meds done) is free capacity — and today "
        "the cost of failure lands on whichever party holds less contract "
        "leverage."),
    evidence=(
        _E("Pending care-management/transportation needs were the most "
           "frequent uncompleted discharge task (47%) at a US academic "
           "site",
           "ACADEMIC", "Single-site discharge QI study, PMC11023539 "
           "(re-verify)", ""),
        _E("PACU cohort: 61.2% of discharge delays non-clinical; lack of "
           "hospital patient transport second-most-common cause (11.1% vs "
           "bed unavailability 22.5%) — non-US, magnitude only",
           "ACADEMIC", "Ego et al., Ann Med Surg 2022",
           "https://doi.org/10.1016/j.amsu.2022.104680"),
        _E("Medicare pays base + loaded mileage only — waiting time is "
           "not separately reimbursed, so door delay is uncompensated "
           "provider cost",
           "GOV", "CMS Ambulance Fee Schedule / Claims Processing Manual "
           "ch.15", ""),
        _E("Delayed discharges: weighted mean 22.8% of patients across 64 "
           "studies — the population readiness failure feeds",
           "ACADEMIC", "Landeiro et al., The Gerontologist 2019",
           "https://doi.org/10.1093/geront/gnx028"),
    ),
    subqs=(
        _S("How often is the patient not ready when the vehicle arrives?",
           "No national rate — flagged; diligence: pull operators' "
           "at-door wait-time distributions (every CAD records them)."),
        _S("What causes lack of readiness?",
           "The quartet — incomplete paperwork, unfinished medications, "
           "unconfirmed receiving beds, pending final orders — plus "
           "booking unsynchronized with any of them."),
        _S("Is paperwork incomplete?",
           "Often: the PCS/medical-necessity packet is the top ambulance "
           "documentation failure (insufficient documentation is 63.5% of "
           "improper payments)."),
        _S("Are medications unfinished?",
           "A named non-clinical delay cause in discharge audits (final "
           "doses, scripts to fill) — no separate published rate."),
        _S("Is the receiving bed unconfirmed?",
           "Frequently the binding item — facility placement is the most "
           "common non-medical discharge barrier in the US series."),
        _S("Is the patient awaiting a final order?",
           "Yes, commonly — pending physician sign-off is a standing "
           "entry on uncompleted-discharge-task audits."),
        _S("How early is transportation booked relative to true "
           "readiness?",
           "Unmeasured publicly; hedging slow vendors pushes booking "
           "earlier, manufacturing wait — diligence: booked-time vs "
           "ready-time deltas."),
        _S("How much vehicle and crew capacity is lost to waiting?",
           "No public national wait-vs-transport split — flagged; the 911 "
           "analog (crews detained >1h at 75% of CA hospitals) shows door "
           "time can rival drive time."),
        _S("Who bears the cost of that wait?",
           "The provider first (Medicare pays nothing for waiting), then "
           "hospitals through repriced rates and quiet refusals."),
        _S("How can provider and hospital scheduling be better "
           "synchronized?",
           "Confirm the readiness quartet before dispatch, share live "
           "discharge milestones, and book against bed-confirmed times — "
           "the integration a dedicated partner contracts for."),
    ),
)


_MODALITY = Block(
    "q7-modality", "Modality errors",
    conclusion=(
        "No clean national rate exists for wrong-level IFT requests; the "
        "measurable shadows are payment-integrity data (27.5% of improper "
        "ambulance payments fail medical necessity) and secondary-"
        "overtriage studies — enough to prove both over- and "
        "under-selection happen, not enough to size them."),
    why_true=(
        "The payment record shows selection failure at scale: ambulance "
        "improper payments run 13.2% ($595.1M projected), of which 63.5% "
        "is insufficient documentation and 27.5% medical necessity — the "
        "necessity share is substantially level-of-service mis-selection.",
        "Over-triage is measured in adjacent transfer literature: facial-"
        "fracture transfers saw a 151% rise in patients discharged "
        "straight from the receiving ED — transferred, at full cost, for "
        "care they did not need.",
        "Under-selection is riskier and less visible: a BLS crew on what "
        "becomes an ALS patient generates a clinical event, not a billing "
        "line, and no registry captures it — recorded as not-found.",
        "Policy proves selection responds to rules: RSNAT prior "
        "authorization produced a 61% reduction in the probability of "
        "repetitive-transport use while emergency dialysis use rose 19% — "
        "modality choice moves when someone checks it."),
    why_matters=(
        "A wrong-level request creates all three costs at once — delay "
        "(queueing for the scarce higher tier), money (paying the ALS/SCT "
        "multiple for a BLS need), and clinical risk (the reverse) — and "
        "structured request tools with embedded modality rules are the "
        "cheapest control available."),
    evidence=(
        _E("Ambulance improper payment rate 13.2%, $595.1M projected; "
           "insufficient documentation 63.5%, medical necessity 27.5%",
           "GOV", "CMS CERT 2024 supplemental improper-payment data "
           "(re-verify)", ""),
        _E("Facial-fracture transfers: 151% increase in the share "
           "discharged from the receiving ED on arrival — measured "
           "secondary overtriage",
           "ACADEMIC", "Wasicek et al., Plast Reconstr Surg 2022 (NTDB "
           "2007-2015)", "https://doi.org/10.1097/PRS.0000000000009039"),
        _E("RSNAT prior authorization: 61% reduction in RSNAT-use "
           "probability, 77% reduction in RSNAT spend, 19% rise in "
           "emergency dialysis use among ESRD beneficiaries",
           "ACADEMIC", "Contreary et al., JAMA Health Forum 2022",
           "https://doi.org/10.1001/jamahealthforum.2022.2093"),
        _E("21% of ambulance suppliers met ≥1 of 7 questionable-billing "
           "measures; 4 metros = 18% of transports but 52% of "
           "questionable ones",
           "GOV", "HHS OIG OEI-09-12-00351, 2015 (re-verify)", ""),
    ),
    subqs=(
        _S("How often is the wrong transport level requested?",
           "No IFT-specific published rate — flagged; the 27.5% medical-"
           "necessity share of improper payments is the payment-side "
           "shadow."),
        _S("How often is a trip upgraded?",
           "Not published; upgrades surface as crew-initiated ALS "
           "intercepts — diligence: request upgrade/downgrade logs."),
        _S("How often is it downgraded?",
           "Not published; payer level-of-service downcoding is the "
           "visible trace on the remittance side."),
        _S("What are the principal causes of incorrect selection?",
           "Ordering clinicians without modality training, inconsistent "
           "facility rules, defensive over-ordering, and vendor steering "
           "toward higher-billing levels (the OIG questionable-billing "
           "pattern)."),
        _S("Does incorrect selection create delay?",
           "Yes — an over-specified request queues for scarce ALS/CCT "
           "units while a suitable BLS truck idles."),
        _S("Does it create unnecessary cost?",
           "Yes — ALS1 bills 1.2x and SCT 3.25x the BLS relative value; "
           "over-selection pays the multiple for nothing."),
        _S("Does it create clinical risk?",
           "Under-selection does — an unmonitored deteriorating patient; "
           "that asymmetric tail is what drives defensive over-ordering."),
        _S("Are modality rules consistent across facilities?",
           "No — the ordering clinician decides under uneven rules "
           "(Question 1's finding); no cross-system standard exists."),
        _S("Can request tools guide users toward the correct modality?",
           "Yes — structured intake with clinical criteria (the NEMT "
           "broker-screening analog) is proven practice; adoption in IFT "
           "is the gap."),
    ),
)


_FRAGMENTATION = Block(
    "q7-fragmentation", "Fragmented vendor management",
    conclusion=(
        "Fragmentation is documented on the supply side — ~10,600 Medicare-"
        "billing ambulance organizations nationally, 751 org NPIs in NE+IA "
        "alone — and its management cost is documented nowhere: the "
        "sequential phone canvass, the absent accountable party, and "
        "non-comparable performance data are the operating price of a "
        "market bought without contracts."),
    why_true=(
        "The denominator is real: ~10,600 ground ambulance organizations "
        "bill Medicare; NE+IA alone carry 751 organizational NPIs, ~85-90% "
        "of Nebraska's municipal/volunteer — a long tail no hospital can "
        "manage as a vendor panel.",
        "Nebraska's own assessment says fragmentation harms service: "
        "'Nebraska may have an excess of licensed EMS transporting "
        "agencies, which may be exacerbating shortages and creating "
        "inefficiencies.'",
        "Sequential offering is the workflow consequence: with no "
        "committed vendor, staff work down a call list trip by trip; the "
        "time this consumes is unpublished — flagged as the diligence "
        "stopwatch metric.",
        "Fragmentation splits volume below the dedicated-capacity "
        "threshold: no single provider receives enough committed volume to "
        "staff units against it — Question 1's purchasing finding restated "
        "as an operations cost."),
    why_matters=(
        "Fragmentation trades theoretical redundancy for practical "
        "unaccountability — every vendor can blame another, performance "
        "data never aggregates, and the buyer holds no lever; consolidated "
        "first-call contracts are the tested counterfactual."),
    evidence=(
        _E("~10,600 ground ambulance organizations bill Medicare — an "
           "extremely long supplier tail",
           "GOV", "MedPAC Ambulance Payment Basics, Oct 2024",
           "https://www.medpac.gov/wp-content/uploads/2024/10/MedPAC_Payment_Basics_24_ambulance_FINAL_SEC.pdf"),
        _E("751 unique ambulance org NPIs across NE+IA; NE ~82% "
           "municipal/fire/volunteer with a 58-org private layer",
           "SOURCED", "CMS NPPES registry sweep, vendored 2026-07-10", ""),
        _E("'Nebraska may have an excess of licensed EMS transporting "
           "agencies, which may be exacerbating shortages and creating "
           "inefficiencies'",
           "GOV", "NE DHHS Statewide EMS Assessment 2023-24 (re-verify)",
           "https://dhhs.ne.gov/OEHS%20Program%20Documents/NE%20Statewide%20EMS%20Assessment%20v2024.pdf"),
    ),
    subqs=(
        _S("How many vendors must staff contact for a typical trip?",
           "No published count — flagged; call-list depth is a "
           "per-facility diligence pull from phone logs."),
        _S("How often is a request offered sequentially to multiple "
           "providers?",
           "Routinely wherever no first-call contract exists — the "
           "structural default in unconsolidated markets; frequency is "
           "unmeasured."),
        _S("How much time does this take?",
           "Unpublished — the NEMT analog (broker call centers) exists "
           "precisely because sequential canvassing does not scale."),
        _S("Is there one accountable provider?",
           "Usually not — Question 1's central finding: in IFT, no party "
           "carries contractual teeth when service fails."),
        _S("Does fragmentation improve access or reduce accountability?",
           "It reduces accountability without improving access: many "
           "licensed agencies, thin actual availability — the Nebraska "
           "assessment's exact paradox."),
        _S("Does each provider receive enough volume to support dedicated "
           "capacity?",
           "No — split volume is why providers rationally refuse to add "
           "committed units; the purchasing structure creates the "
           "capacity problem."),
        _S("Are service standards consistent?",
           "No — standards exist in 911 (response times) and NEMT "
           "(on-time performance), almost never in trip-by-trip IFT."),
        _S("Is performance data comparable?",
           "No — each vendor's logs are private and unstandardized; no "
           "common denominator exists to rank them."),
        _S("Are providers able to blame one another for failures?",
           "Yes — sequential offering means every failure has a plausible "
           "other party; a single accountable partner is the structural "
           "fix."),
    ),
)


_VISIBILITY = Block(
    "q7-visibility", "Visibility and communication",
    conclusion=(
        "In trip-by-trip markets hospital staff cannot see capacity, "
        "vehicle location, live ETA, or delay reasons — the entire "
        "information layer runs by phone — and the one measured "
        "communication intervention (EMS prenotification, −20.1 minutes of "
        "stroke door-in-door-out time) proves information flow moves "
        "clinical clocks."),
    why_true=(
        "The default stack is telephony: booking, status checks, "
        "escalation, and cancellation each require a call; no calls-per-"
        "trip figure has ever been published (recorded as a research "
        "dead-end — itself evidence that nobody measures it).",
        "The technology exists and is standard in the adjacent markets: "
        "911 CAD/AVL and NEMT broker portals show live position and trip "
        "status as a matter of course — IFT's gap is commercial, not "
        "technical.",
        "Communication is measured to change outcomes where studied: "
        "prenotification cut stroke door-in-door-out time by 20.1 minutes "
        "across 108,913 transfers.",
        "Re-entry and conflicting information follow from the "
        "architecture: each phone hop re-keys the same trip into another "
        "system, and parallel phone chains (to dispatcher, to crew) "
        "guarantee divergent answers."),
    why_matters=(
        "Invisibility converts small delays into large ones — nobody can "
        "re-plan around what they cannot see — and consumes clinical labor "
        "as a status-checking switchboard; shared visibility is the "
        "cheapest component of the dedicated-model bundle."),
    evidence=(
        _E("EMS prenotification associated with a 20.1-minute reduction "
           "in stroke door-in-door-out time",
           "ACADEMIC", "GWTG-Stroke analysis, JAMA 2023 (n=108,913)",
           "https://doi.org/10.1001/jama.2023.12739"),
        _E("No published calls-per-trip or coordination-telephony figure "
           "exists for hospital transport — an honest dead-end, recorded",
           "FRAMEWORK", "2026-07-10 research sweep (dead-end log)", ""),
        _E("California AB 40 requires monthly per-hospital offload-time "
           "monitoring against a 30-min/90% standard — proof the "
           "measurement infrastructure is buildable",
           "GOV", "CA EMSA APOT program / AB 40 (2023) (re-verify)", ""),
    ),
    subqs=(
        _S("Can hospital staff see available capacity?",
           "Not in call-list markets — availability is discovered by "
           "phoning; portal visibility exists only inside dedicated or "
           "broker arrangements."),
        _S("Can they see vehicle location?",
           "Generally no — AVL data stays inside the provider's CAD; "
           "sharing it is a contract feature, not a market norm."),
        _S("Can they see current ETA?",
           "Only by calling; live ETA feeds are the exception."),
        _S("Can they see the reason for a delay?",
           "Almost never — delay causes are rarely coded at all, let "
           "alone shared; hospital-vs-provider attribution is impossible "
           "without them."),
        _S("Can receiving facilities see trip status?",
           "Typically not — the receiving side learns by phone at door "
           "time, which is how placement windows get lost."),
        _S("How much communication occurs by phone?",
           "Essentially all of it in unconsolidated markets; the "
           "proportion is unmeasured — flagged."),
        _S("How many calls are made per trip?",
           "No published figure (a documented dead-end); diligence: count "
           "from call logs at one facility for one week."),
        _S("How often do staff receive conflicting information?",
           "Unmeasured; the mechanism — parallel phone chains to "
           "dispatcher and crew — guarantees divergence."),
        _S("How frequently must requests be re-entered?",
           "Every hop between unintegrated systems re-keys the trip; "
           "frequency unpublished."),
        _S("Which communication failures create the largest operational "
           "burden?",
           "Status invisibility (drives repeated calling) and unshared "
           "delay reasons (blocks re-planning and attribution) — the two "
           "a dedicated model contracts away."),
    ),
)


_FLOW = Block(
    "q7-flow", "Hospital-flow impact",
    conclusion=(
        "Delayed discharge affects a weighted mean 22.8% of patients, a "
        "small delayed cohort (3.5% of admissions) can consume 27.2% of "
        "bed-days, and boarding among admitted seniors more than doubled "
        "from 2018 to 2022 — transportation is a named minority "
        "contributor inside those totals, and no US series isolates its "
        "exact share; that attribution gap is the honest headline."),
    why_true=(
        "The totals are measured: delayed discharges ran 1.6-91.3% across "
        "64 studies with a weighted mean of 22.8%; at one US academic "
        "hospital, 101 hospitalizations (3.5%) accounted for 6,518 of "
        "23,934 inpatient days (27.2%).",
        "Boarding is measured and worsening: 85.2% of admitted patients "
        "65+ boarded ≥2 hours; mean boarding rose from 138 minutes (2018) "
        "to 343 (2022), reaching 501 minutes for patients with dementia.",
        "Transfer-out delay is measured at the acute end: stroke door-in-"
        "door-out median 174 minutes with only 27.3% inside the 120-minute "
        "guideline; STEMI DIDO median 68 minutes, 11% within 30, with "
        "mortality 5.9% vs 2.7% (adjusted OR 1.56) past the mark — and "
        "82.8% of stroke transfer time is spent at the referring hospital.",
        "Transportation's isolated share is published in no US series: "
        "transport is named among non-medical discharge barriers (facility "
        "placement is the top one), so attribution requires local "
        "timestamping — a diligence design, not a literature lookup."),
    why_matters=(
        "This is where IFT failure becomes hospital economics: bed-days, "
        "boarding hours, and missed placement windows are the units — and "
        "average length of stay ran +19% (2019→2022, +24% for post-acute "
        "discharges), so the flow cost is rising regardless of whose fault "
        "each hour is."),
    evidence=(
        _E("Delayed discharges: 1.6-91.3% across 64 studies, weighted "
           "mean 22.8%; delay costs $142-31,935 per case (USD PPP)",
           "ACADEMIC", "Landeiro et al., The Gerontologist 2019",
           "https://doi.org/10.1093/geront/gnx028"),
        _E("3.5% of hospitalizations consumed 27.2% of inpatient days; "
           "facility placement the most common non-medical barrier at "
           "every timepoint",
           "ACADEMIC", "Gao & Berland, Brown J Hosp Med 2022",
           "https://doi.org/10.56305/001c.36593"),
        _E("85.2% of admitted 65+ boarded ≥2h; mean boarding 138→343 min "
           "(2018→2022), 501 min with Alzheimer's-related dementia",
           "ACADEMIC", "Lee et al., Ann Emerg Med 2026 (NHAMCS)",
           "https://doi.org/10.1016/j.annemergmed.2026.03.011"),
        _E("STEMI transfer DIDO median 68 min, 11% ≤30 min; mortality "
           "5.9% vs 2.7%, adjusted OR 1.56 for DIDO >30 min",
           "ACADEMIC", "Wang et al., JAMA 2011 (n=14,821)",
           "https://doi.org/10.1001/jama.2011.862"),
        _E("Hospital ALOS +19% 2019→2022; +24% for patients discharged "
           "to post-acute care",
           "SOURCED", "AHA Issue Brief, Dec 2022 (re-verify)", ""),
    ),
    subqs=(
        _S("How often does delayed transportation delay discharge?",
           "No US share is published; transport is a named minority cause "
           "inside the 22.8% weighted-mean delayed-discharge total — "
           "local timestamping is required to attribute it."),
        _S("How often does it prevent bed turnover?",
           "Every delayed departure is a blocked bed by definition; the "
           "delayed cohort's 27.2%-of-bed-days footprint bounds the "
           "stakes."),
        _S("How often does it contribute to ED boarding?",
           "Boarding is the queue's visible end (85.2% ≥2h; 343-minute "
           "mean by 2022); the transport-attributable slice is "
           "unmeasured."),
        _S("How often does it delay transfer to higher-acuity care?",
           "Measurably often: 72.7% of stroke transfers miss the "
           "120-minute DIDO guideline and 89% of STEMI transfers miss 30 "
           "minutes — with 82.8% of transfer time spent at the referring "
           "hospital."),
        _S("How often is a post-acute placement lost?",
           "Not published as a rate; facility placement is the top "
           "non-medical barrier, and a missed pickup window can forfeit a "
           "bed offer — flagged for local measurement."),
        _S("How often does a patient remain overnight solely because "
           "transportation was unavailable?",
           "Documented in delayed-discharge audits as a named cause, "
           "never as a national rate — flagged."),
        _S("Which facilities experience the greatest effect?",
           "Rural/CAH senders (3x transfer propensity) and high-occupancy "
           "receivers where every boarded hour cascades through the ED."),
        _S("Which trip types produce the greatest throughput impact?",
           "Time-critical up-transfers (mortality-bearing DIDO) and "
           "post-acute discharge legs (bed-day-bearing volume) — two "
           "different failure currencies."),
        _S("How can transportation effects be separated from other "
           "discharge barriers?",
           "Timestamp clinically-ready vs transport-booked vs departed "
           "and code delay causes — the same attribution discipline the "
           "ETA and readiness blocks require."),
    ),
)


_LABOR = Block(
    "q7-labor", "Labor impact",
    conclusion=(
        "The nurse and case-manager time consumed by transport "
        "coordination is the least-evidenced cost in this study: the only "
        "circulating figure (2-3 hours per shift) is an unverified vendor "
        "claim, no peer-reviewed time-motion study exists, and calls-per-"
        "trip has never been published — the measurement gap IS the "
        "finding."),
    why_true=(
        "The search record is the evidence: no peer-reviewed time-motion "
        "study of hospital transport coordination was found (documented "
        "dead-end), and the one circulating figure is a vendor blog claim "
        "— labeled as such and never load-bearing here.",
        "The mechanism is documented even where the minutes are not: "
        "sequential vendor canvassing, status-check telephony, and "
        "re-entry (the fragmentation and visibility blocks) are labor by "
        "construction.",
        "Duplication is structural: the requester, the transfer center, "
        "and case management each touch the same trip, and shift-boundary "
        "handoffs re-run the coordination from scratch.",
        "What is measured is adjacent: uncompleted discharge tasks "
        "cluster in care-management/transportation (47% in one audit) — "
        "coordination work visibly displaces other discharge work."),
    why_matters=(
        "Unmeasured labor is unpriced labor — it appears in no trip rate "
        "and no business case, which is exactly why integration (one "
        "accountable vendor, shared visibility, booking integration) is "
        "undervalued by buyers; the diligence fix is a two-week "
        "time-motion study, not a longer literature search."),
    evidence=(
        _E("No peer-reviewed time-motion study of hospital transport-"
           "coordination labor found; no calls-per-trip figure published",
           "FRAMEWORK", "2026-07-10 research sweep (dead-end log)", ""),
        _E("Vendor claim: nurses spend '2-3 hours per shift' on transport "
           "tasks — unverified marketing, cited only to show what "
           "circulates in the absence of research",
           "FRAMEWORK", "VectorCare vendor blog (re-verify)", ""),
        _E("Pending care-management/transportation needs the most "
           "frequent uncompleted discharge task (47%) at one site",
           "ACADEMIC", "Single-site discharge QI study, PMC11023539 "
           "(re-verify)", ""),
    ),
    subqs=(
        _S("How much time do nurses spend coordinating trips?",
           "No peer-reviewed figure; the circulating vendor claim (2-3 "
           "hrs/shift) is unverified — diligence: commission a "
           "time-motion study."),
        _S("How much time do case managers spend calling vendors?",
           "Unmeasured publicly — same instrument; call logs make it "
           "countable in a week."),
        _S("How much time do transfer-center staff spend escalating "
           "delays?",
           "Unpublished; escalation minutes are recoverable from "
           "transfer-center phone systems — a diligence pull, not a "
           "mystery."),
        _S("How much duplicated work occurs?",
           "Structurally guaranteed — three roles touch each trip and "
           "every unintegrated system boundary forces re-entry — but "
           "never quantified."),
        _S("How frequently does transport coordination extend beyond a "
           "staff member's shift?",
           "Unmeasured; shift-spanning trips force handoffs that re-run "
           "coordination — flagged for the time-motion design."),
        _S("Does poor transportation performance contribute to overtime?",
           "Plausible and unproven — no published link; test locally "
           "against overtime and delay logs."),
        _S("Which activities could be eliminated through better "
           "integration?",
           "The canvass (one accountable vendor), the status calls "
           "(shared visibility), and the re-entry (booking integration) — "
           "the fragmentation and visibility blocks are this block's "
           "task list."),
    ),
)


_PATIENT = Block(
    "q7-patient", "Patient impact",
    conclusion=(
        "Patients wait out transport failure in clinical spaces — boarded "
        "in EDs (mean 343 minutes for admitted seniors by 2022, 501 with "
        "dementia) or occupying the bed they were discharged from — and at "
        "the acute end the waiting is mortality-bearing: STEMI transfer "
        "mortality 5.9% vs 2.7% past the 30-minute door-in-door-out mark."),
    why_true=(
        "The waits are measured where clinical registries reach: 85.2% of "
        "admitted patients 65+ boarded ≥2 hours; DIDO medians of 174 "
        "(stroke) and 68 (STEMI) minutes with guideline compliance of "
        "27.3% and 11% respectively.",
        "Harm is measured at the time-critical end: STEMI DIDO over 30 "
        "minutes carried an adjusted odds ratio of 1.56 for in-hospital "
        "mortality — delay is a clinical exposure, not an inconvenience.",
        "The public feels it: 44% of US adults report prolonged post-ED "
        "waits before admission or transfer for themselves or a loved "
        "one; 16% report waits of 13 hours or more.",
        "The burden concentrates in identifiable groups: the old (the "
        "boarding series), dementia patients (501-minute means), rural "
        "patients (3x transfer dependence), and dialysis and psychiatric "
        "patients (recurring and hard-to-place books) — those least able "
        "to advocate wait longest."),
    why_matters=(
        "Patient experience is the governance argument for fixing IFT "
        "even where the finance case is contested — and safety-bearing "
        "delay (missed guideline windows) is regulatory and liability "
        "exposure, not just dissatisfaction."),
    evidence=(
        _E("Mean ED boarding for admitted 65+ rose 138→343 min "
           "(2018→2022); 501 min with Alzheimer's-related dementia",
           "ACADEMIC", "Lee et al., Ann Emerg Med 2026",
           "https://doi.org/10.1016/j.annemergmed.2026.03.011"),
        _E("STEMI transfer mortality 5.9% vs 2.7% (adjusted OR 1.56) "
           "beyond the 30-minute DIDO guideline",
           "ACADEMIC", "Wang et al., JAMA 2011",
           "https://doi.org/10.1001/jama.2011.862"),
        _E("44% of US adults report prolonged post-ED waits (self or "
           "loved one); 16% report ≥13 hours",
           "ACADEMIC", "ACEP / Morning Consult national poll, Oct 2023 "
           "(n=2,164)",
           "https://www.acep.org/news/acep-newsroom-articles/new-poll-alarming-number-of-patients-would-avoid-emergency-care-because-of-boarding-concerns"),
        _E("Stroke transfer DIDO median 174 min; 27.3% within the "
           "120-minute guideline",
           "ACADEMIC", "GWTG-Stroke analysis, JAMA 2023",
           "https://doi.org/10.1001/jama.2023.12739"),
    ),
    subqs=(
        _S("How long do patients wait after being clinically ready?",
           "Nationally unmeasured for discharge legs; the admitted-senior "
           "boarding series (343-minute mean by 2022) is the "
           "best-measured analog."),
        _S("Where do they wait?",
           "ED hallways and treatment rooms (boarding) or the inpatient "
           "bed they no longer need — clinical spaces either way."),
        _S("Are they still occupying a clinical bed?",
           "Yes in the discharge case — that is precisely the throughput "
           "cost (the delayed cohort's 27.2% of bed-days)."),
        _S("Are their medication, food, mobility, and hygiene needs "
           "supported?",
           "The boarding literature documents degraded routine care "
           "during long ED holds; no IFT-specific study exists — "
           "flagged."),
        _S("Are patients and families informed?",
           "Only as well as staff are — and staff cannot see ETAs (the "
           "visibility block), so families receive the same "
           "non-answers."),
        _S("Does delay create anxiety or dissatisfaction?",
           "Yes — measured as public sentiment: 44% report prolonged "
           "waits, and the same poll finds people avoiding emergency care "
           "over boarding concerns."),
        _S("Does delay create safety risk?",
           "At the time-critical end, measured mortality (STEMI adjusted "
           "OR 1.56); at the boarding end, the geriatric and dementia "
           "series tie prolonged boarding to harm."),
        _S("Does it disrupt continuity of care?",
           "Yes — missed placement windows and after-hours arrivals at "
           "post-acute facilities degrade handoffs; the rate is "
           "unpublished."),
        _S("Which patient groups are most affected?",
           "Elderly and dementia patients, rural patients (3x transfer "
           "dependence), and psychiatric and dialysis patients — the "
           "recurring, hard-to-place, or long-leg books."),
    ),
)


_FINANCIAL = Block(
    "q7-financial", "Financial impact",
    conclusion=(
        "The costs of IFT failure are real but scattered across ledgers "
        "that never meet — bed-days (~$3,132 adjusted expense per "
        "inpatient day), denied and never-paid claims (13.2% improper; "
        "19.7% collect nothing), unpaid crew wait, and uncounted "
        "coordination labor — so no single owner sees the total, and no "
        "single owner funds the fix."),
    why_true=(
        "The bed-day is the biggest line: adjusted expense ~$3,132 per "
        "inpatient day (an expense proxy, not marginal cost — labeled), "
        "against delayed-discharge costs measured from $142 to $31,935 "
        "per case.",
        "The claims lines are measured: 13.2% ambulance improper payment "
        "($595.1M projected) and 19.7% of transports collecting nothing — "
        "denial and non-payment costs that reprice into everyone's rates.",
        "The hidden lines are structurally hidden: crew wait (unpaid by "
        "Medicare), coordination labor (no time-motion study exists), and "
        "missed placements (no published rate) appear on no ledger — "
        "hidden is a data property, not a statement of size.",
        "The benefit of improvement splits three ways — the hospital "
        "gains bed capacity, the payer gains shorter stays, the provider "
        "gains utilization — and misaligned capture is why "
        "underinvestment persists (Question 1's purchasing finding, "
        "priced)."),
    why_matters=(
        "Whoever prices the bed-day, not the trip, buys correctly: one "
        "avoided bed-day (~$3,132 expense proxy) is worth roughly 6-7 "
        "Medicare-average transports ($469 each) — that arithmetic, both "
        "inputs cited, is the entire commercial argument for paying for "
        "reliability."),
    evidence=(
        _E("Adjusted expense per inpatient day ~$3,132 (2023; nonprofit "
           "$3,288, for-profit $2,529) — an expense proxy, not marginal "
           "cost",
           "SOURCED", "KFF state indicator on AHA survey data (re-verify)",
           ""),
        _E("Delayed-discharge costs $142-31,935 per case (USD PPP) "
           "across the systematic review",
           "ACADEMIC", "Landeiro et al., The Gerontologist 2019",
           "https://doi.org/10.1093/geront/gnx028"),
        _E("Ambulance improper payments 13.2% / $595.1M projected "
           "(insufficient documentation 63.5%)",
           "GOV", "CMS CERT 2024 supplemental data (re-verify)", ""),
        _E("19.7% of transports collect nothing — the provider-side "
           "non-payment tax",
           "SOURCED", "CMS/RAND GADCS Year 1-4 appendix, via AAA coverage",
           "https://ambulance.org/2025/12/09/cms-releases-new-gadcs-report/"),
        _E("Medicare FFS average payment $469/transport ($5.3B / 11.3M, "
           "2024) — the trip-side unit for the bed-day comparison",
           "DERIVED", "MedPAC Ambulance Payment Basics, Oct 2024 (both "
           "inputs GOV)",
           "https://www.medpac.gov/wp-content/uploads/2024/10/MedPAC_Payment_Basics_24_ambulance_FINAL_SEC.pdf"),
    ),
    subqs=(
        _S("What is the cost of additional bed occupancy?",
           "~$3,132 adjusted expense per inpatient day (proxy, not "
           "marginal); delayed-discharge case costs measured at "
           "$142-31,935."),
        _S("What is the opportunity cost of an unavailable bed?",
           "The forgone admission's contribution margin — larger than "
           "the expense proxy at capacity; no national figure, model it "
           "locally."),
        _S("What labor cost is created by coordination?",
           "Unmeasured (the labor block) — the study's largest "
           "known-unknown; a time-motion study prices it."),
        _S("What cost is created by unnecessary high-acuity transport?",
           "The tier spread: SCT bills 3.25x and ALS1 1.2x the BLS "
           "relative value — over-selection pays the multiple for "
           "nothing."),
        _S("What cost is created by provider wait time?",
           "Crew hours Medicare does not pay — absorbed by providers, "
           "then repriced into rates or withdrawn availability."),
        _S("What cost is created by denied claims?",
           "The 13.2%/$595.1M improper-payment exposure plus the 19.7% "
           "never-paid share — both ultimately reprice into the market."),
        _S("What cost is created by missed appointments or placements?",
           "Priced only in the NEMT analog: RSNAT's 19% rise in emergency "
           "dialysis use shows a missed scheduled run converting into an "
           "emergency episode; unpriced in IFT."),
        _S("Which costs are recorded directly?",
           "Trip invoices, claim denials, and (sometimes) hospital "
           "transport subsidies — the small, visible minority."),
        _S("Which costs remain hidden across departments?",
           "Bed-days (nursing/flow), boarding hours (ED), coordination "
           "labor (case management), lost placements (post-acute) — each "
           "on a different budget, none labeled transport."),
        _S("Who captures the economic benefit from improvement?",
           "Mostly the hospital (beds, labor) and the payer (shorter "
           "stays), not the transport provider — the misalignment "
           "availability-retainer contracts exist to fix."),
    ),
)


Q7 = QuestionDef(
    num=7,
    slug="failures",
    title="What operational challenges exist under current models?",
    storyline=(
        "Every failure mode drains into the same reservoir — the queue "
        "forms inside the hospital, measured in boarded hours, occupied "
        "bed-days, and missed guideline windows — while the biggest costs "
        "(crew waits, coordination labor, lost placements) are precisely "
        "the ones nobody records."),
    visual_key="cascade",
    blocks=(_MISMATCH, _ACCEPTANCE, _ETA, _READINESS, _MODALITY,
            _FRAGMENTATION, _VISIBILITY, _FLOW, _LABOR, _PATIENT,
            _FINANCIAL),
)


# ═════════════════════════════ QUESTION 8 ════════════════════════════════════

_SCOPE = Block(
    "q8-scope", "Service scope",
    conclusion=(
        "MMT's public service scope is an IFT ladder — BLS/ALS "
        "interfacility transport, specialty/critical-care transport, and "
        "wheelchair/para-transit — explicitly positioned as 'not a 911 "
        "service', with air ambulance a historic line (Midwest MedAir) "
        "whose current status is unconfirmed; every mix percentage behind "
        "that list is company data."),
    why_true=(
        "The deal record defines the core: 'advanced life support and "
        "basic life support inter-facility transports (IFT) and specialty "
        "transports to large and mid-sized health systems, critical "
        "access hospitals and long-term care facilities' (sponsor "
        "release, Jan 2022).",
        "The fleet claim confirms the low-acuity edge: '500+ vehicles "
        "(ambulances, helicopters, para-transit vans)' — wheelchair/"
        "para-transit capacity is in the estate by the company's own "
        "description.",
        "The boundary is drawn by the company itself: 'Midwest Medical "
        "Transport is not a 911 service—it provides inter-facility "
        "medical transportation, taking patients from hospital to "
        "hospital, nursing home to hospital, and vice versa.'",
        "Air is historic and flagged: Midwest MedAir flew 400+ emergency "
        "helicopter calls alongside 30,000 ground calls in a reported "
        "year, and the flagship NPI still carries the Air Ambulance "
        "taxonomy — but no post-2022 confirmation of the air line exists; "
        "recorded as unconfirmed, not asserted either way."),
    why_matters=(
        "The scope matches the dedicated-IFT archetype this study "
        "contrasts against 911-first platforms — but without trip and "
        "revenue mix by modality, the acuity-mix economics (the SCT "
        "premium, the para-transit availability book) cannot be "
        "underwritten from public data."),
    evidence=(
        _E("'advanced life support and basic life support inter-facility "
           "transports (IFT) and specialty transports to large and "
           "mid-sized health systems, critical access hospitals and "
           "long-term care facilities'",
           "SOURCED", "Businesswire / Harbour Point Capital deal release, "
           "Jan 25 2022",
           "https://www.businesswire.com/news/home/20220125006174/en/"),
        _E("'500+ vehicles (ambulances, helicopters, para-transit vans)'; "
           "13 states; 2,800+ team members",
           "SOURCED", "mmtamb.com About Us (company self-report, 2026)",
           "https://mmtamb.com/about-us/"),
        _E("'Midwest Medical Transport is not a 911 service—it provides "
           "inter-facility medical transportation…'",
           "SOURCED", "Siouxland Chamber directory (company positioning)",
           "https://directory.siouxlandchamber.com/list/member/midwest-medical-transport-company-6143"),
        _E("Midwest MedAir: 30,000 ambulance calls + 400+ emergency "
           "helicopter calls in a reported year — the historic air line",
           "SOURCED", "Omaha World-Herald (Midwest MedAir coverage)",
           "https://omaha.com/news/air-ambulance-team-adds-hastings-based-helicopter/article_0038cb3a-8f7d-52fc-9a70-7003fec324b2.html"),
    ),
    subqs=(
        _S("Which transportation modalities does MMT provide?",
           "Publicly: BLS and ALS interfacility, specialty/critical-care "
           "transport, and wheelchair/para-transit vans; historically air "
           "(Midwest MedAir, current status unconfirmed)."),
        _S("Which modalities are core?",
           "ALS/BLS interfacility plus specialty transports — the deal "
           "release's own definition of the business."),
        _S("Which modalities are offered only in selected markets?", "",
           skip="Company data — diligence request: modality availability "
           "by market (air and CCT footprints are the likely variables)."),
        _S("What percentage of trips falls into each modality?", "",
           skip="Company data — diligence request: trip mix by modality "
           "(BLS/ALS/CCT/wheelchair)."),
        _S("What percentage of revenue falls into each modality?", "",
           skip="Company data — diligence request: revenue mix by "
           "modality."),
        _S("How does service mix differ by customer?", "",
           skip="Company data — diligence request: mix by account class "
           "(health system vs CAH vs long-term care)."),
        _S("How does service mix differ by geography?", "",
           skip="Company data — diligence request: mix by market; the "
           "NPI estate (rural Iowa stations vs metro posts) implies "
           "variation without quantifying it."),
        _S("Does MMT provide both scheduled and urgent transportation?",
           "The customer set (health systems + CAHs + long-term care) "
           "implies both scheduled discharge and urgent transfer work; no "
           "public statement quantifies the split."),
        _S("Does it operate 24/7 in every market?", "",
           skip="Company data — diligence request: staffed coverage hours "
           "by station."),
        _S("Which trip categories does it not serve?",
           "911 scene response, by its own positioning ('not a 911 "
           "service'); everything else is unstated publicly."),
    ),
)


_CUSTOMERS = Block(
    "q8-customers", "Customer scope",
    conclusion=(
        "MMT names its customer classes (large and mid-sized health "
        "systems, critical access hospitals, long-term care facilities) "
        "and its longevity ('over 35 years') but not one countable "
        "customer metric — customer count, facility count, concentration, "
        "tenure, and retention are all company data, and no public "
        "contract with any named system is documented."),
    why_true=(
        "Customer classes are on the record twice: the 2022 deal release "
        "(health systems, CAHs, long-term care) and the company site "
        "('For over 35 years, MMT has partnered with some of the largest "
        "and most prestigious health systems across the country').",
        "The origin story is single-customer: founded 1987 'with one "
        "ambulance, doing a few transfers a week out of the Columbus "
        "Hospital' — the archetype of account-anchored growth.",
        "The footprint implies but does not prove accounts: MMT stations "
        "sit in metros anchored by CHI Health, Bryan, Methodist, Nebraska "
        "Medicine, and Great Plains Health, yet no public registry "
        "documents a single MMT hospital contract — recorded as "
        "not-found, consistent with Question 1's finding that IFT "
        "contracts are publicly invisible everywhere.",
        "Growth events are account-shaped: the expansion NPIs (Kansas "
        "City 2024, Columbus OH, Indianapolis, Milwaukee, Rhode Island) "
        "each imply a market entry whose customer anchor is unnamed."),
    why_matters=(
        "Revenue concentration is the single largest un-derisked item: a "
        "13-state platform whose footprint metros are each anchored by "
        "one or two health systems could be well-diversified or "
        "dangerously concentrated — only the customer ledger can say "
        "which."),
    evidence=(
        _E("'For over 35 years, MMT has partnered with some of the "
           "largest and most prestigious health systems across the "
           "country'",
           "SOURCED", "mmtamb.com About Us (company self-report, 2026)",
           "https://mmtamb.com/about-us/"),
        _E("Founded 1987 'with one ambulance, doing a few transfers a "
           "week out of the Columbus Hospital'",
           "SOURCED", "Omaha World-Herald / Columbus Telegram "
           "retrospectives on the 2015 sale",
           "https://omaha.com/news/nation-world/business/midwest-medical-transport-ready-to-take-flight-with-new-owners/article_b6fa47d3-9c50-5bee-85e2-528815926374.html"),
        _E("No public hospital contract naming MMT was found for any "
           "footprint system — an honest not-found, consistent with the "
           "market-wide invisibility of IFT contracts",
           "FRAMEWORK", "2026-07-10 research sweep (dead-end log)", ""),
    ),
    subqs=(
        _S("How many health-system customers does MMT serve?", "",
           skip="Company data — diligence request: customer count by "
           "class (system / CAH / long-term care)."),
        _S("How many facilities does it serve?", "",
           skip="Company data — diligence request: served-facility "
           "roster."),
        _S("Does it contract at the health-system or facility level?", "",
           skip="Company data — diligence request: contract structure by "
           "account; no public contract is documented at either level."),
        _S("What portion of customers use MMT across multiple "
           "facilities?", "",
           skip="Company data — diligence request: multi-facility "
           "penetration by account."),
        _S("What portion use multiple service modalities?", "",
           skip="Company data — diligence request: modality cross-sell "
           "by account."),
        _S("How concentrated is revenue?", "",
           skip="Company data — diligence request: top-5 / top-10 "
           "revenue concentration."),
        _S("How concentrated is trip volume?", "",
           skip="Company data — diligence request: trip-volume "
           "concentration by account."),
        _S("What is average customer tenure?",
           "Not published; the 1987 Columbus Hospital origin proves at "
           "least one multi-decade relationship class exists — the "
           "distribution is a diligence request."),
        _S("What is customer retention?", "",
           skip="Company data — diligence request: gross/net retention "
           "and named churn events."),
        _S("How often does MMT expand within an existing account?", "",
           skip="Company data — diligence request: expansion history; "
           "the one-truck-to-13-states arc implies land-and-expand "
           "without documenting it."),
        _S("What causes customer expansion?",
           "Publicly unattributable for MMT; structurally (Questions "
           "1-7): reliability on the routine book and transfer-center "
           "integration are the share-of-wallet levers."),
        _S("What causes customer loss?",
           "Not published for MMT; the visible footprint mechanism is "
           "competitive capture — AmeriPro's acquisition of Priority "
           "(North Platte, Feb 2025) buys incumbency at the anchor "
           "hospital."),
    ),
)


_CAPACITY = Block(
    "q8-capacity", "Capacity model",
    conclusion=(
        "The one capacity fact in public view is the posture: an IFT-only "
        "fleet (500+ vehicles) with no 911 mandate to shed it against — "
        "which removes Question 7's shared-truck failure mode by "
        "construction; everything the phrase 'dedicated capacity' must "
        "mean in a contract (reserved units, minimums, overflow, who pays "
        "for idle) is company data."),
    why_true=(
        "Structural dedication is public: 'not a 911 service' means no "
        "PSAP can pre-empt an IFT booking — the shared-fleet shedding "
        "mechanism behind Question 7's acceptance and ETA failures is "
        "absent by design.",
        "Scale is claimed but the components never align in one year: "
        "500+ vehicles / 2,800+ team members / 13 states (company site, "
        "2026) vs 200,000+ missions/yr at the Jan 2022 deal — when the "
        "deal release said 10 states while the sell-side advisor said "
        "seven states and ~1,000 employees; the conflict is shown, never "
        "blended.",
        "Third-party estimates make capacity inference unusable: the "
        "estimators disagree ~3x on revenue and headcount and all "
        "disagree with the company's own 2,800+ claim.",
        "No public document describes reservation mechanics — no "
        "minimums, dedicated-unit fees, or overflow protocol has "
        "surfaced — consistent with the market-wide absence of public "
        "IFT contract terms."),
    why_matters=(
        "'Dedicated' is the product: whether it is contractual (reserved "
        "units, guaranteed minimums, penalties) or rhetorical (a "
        "scheduling preference) determines whether MMT's model actually "
        "solves Question 7 — and only the contracts can answer it."),
    evidence=(
        _E("'not a 911 service' — dedication as positioning, from the "
           "company's own directory listing",
           "SOURCED", "Siouxland Chamber directory",
           "https://directory.siouxlandchamber.com/list/member/midwest-medical-transport-company-6143"),
        _E("200,000+ missions/yr at the Jan 2022 recapitalization (deal "
           "release, then 10 states); sell-side advisor simultaneously: "
           "'seven states and nearly 1,000 employees'",
           "SOURCED", "Harbour Point release + Lincoln International "
           "transaction notice, 2022",
           "https://www.businesswire.com/news/home/20220125006174/en/"),
        _E("Revenue estimates conflict ~3x: $296.4M/784 employees "
           "(Growjo) vs $293.6M (ZoomInfo) vs $100-250M/~700 (LeadIQ) — "
           "unusable for underwriting",
           "SOURCED", "Growjo / ZoomInfo / LeadIQ estimates, 2026 "
           "(unaudited; re-verify)", ""),
    ),
    subqs=(
        _S("What does MMT mean by dedicated capacity?", "",
           skip="Company data — diligence request: contract language "
           "defining dedication (reserved units vs scheduling "
           "preference)."),
        _S("Are particular vehicles reserved?", "",
           skip="Company data — diligence request: unit reservation by "
           "account."),
        _S("Are particular crews reserved?", "",
           skip="Company data — diligence request: crew dedication by "
           "account."),
        _S("Is capacity dedicated by facility, health system, modality, "
           "or geography?", "",
           skip="Company data — diligence request: the dedication grain "
           "in contracts."),
        _S("Is there a guaranteed minimum?", "",
           skip="Company data — diligence request: volume or availability "
           "minimums in either direction."),
        _S("Can dedicated units serve other customers?", "",
           skip="Company data — diligence request: exclusivity and "
           "backfill rules."),
        _S("How is overflow managed?", "",
           skip="Company data — diligence request: overflow/mutual-aid "
           "protocol; no public subcontracting arrangement is "
           "documented."),
        _S("How is spare capacity determined?", "",
           skip="Company data — diligence request: reserve staffing "
           "policy."),
        _S("How is demand forecast?",
           "Not published; the demand curve is forecastable in principle "
           "(Question 1's facility×hour×modality grain) — whether MMT "
           "forecasts it is a diligence request."),
        _S("How frequently is capacity adjusted?", "",
           skip="Company data — diligence request: staffing-adjustment "
           "cadence."),
        _S("Who pays for underutilized dedicated capacity?",
           "Not published for MMT; market-wide, availability retainers "
           "and dedicated-unit fees are the instruments — whether MMT's "
           "contracts carry them is the diligence question."),
        _S("Who bears the risk when demand exceeds forecasts?", "",
           skip="Company data — diligence request: SLA and penalty "
           "allocation at peak demand."),
    ),
)


_DISPATCH = Block(
    "q8-dispatch", "Dispatch model",
    conclusion=(
        "Whether dispatch is centralized or market-based, how trips are "
        "prioritized, and what customers can see are all company data; "
        "what the public record fixes is the architecture's anchor points "
        "— the historic Columbus NE headquarters estate, an Omaha "
        "corporate NPI added in 2023, and an IFT-only mission profile "
        "whose dispatch problem (scheduled plus urgent, no 911 "
        "pre-emption) differs from EMS CAD by construction."),
    why_true=(
        "The estate shows the anchors: the flagship NPI sits at the "
        "historic Columbus NE headquarters (2155 33rd Ave, alongside the "
        "1987 predecessor entity), with an Omaha corporate NPI enumerated "
        "Nov 2023 under the current leadership — a two-node core "
        "consistent with centralized functions, without proving them.",
        "IFT dispatch is a scheduling problem, not a proximity race: "
        "assignment optimizes chaining, acuity match, and promised "
        "windows (Question 1's operating read) — the correct benchmark "
        "for any MMT dispatch diligence.",
        "Nothing public describes MMT's CAD, prioritization scheme, or "
        "customer visibility — recorded as not-found across company "
        "materials.",
        "The multi-state estate (23 active NPIs across 11 states) makes "
        "centralize-vs-local the material question: dispatch is a classic "
        "standardizable layer (Question 1's competitive read), and "
        "roll-ups win or lose on it."),
    why_matters=(
        "Dispatch is where the dedicated thesis becomes measurable: ETA "
        "accuracy, delay-cause coding, and hospital-caused vs "
        "provider-caused attribution (Question 7's asks) either exist in "
        "MMT's dispatch data or the Question 7 failures live unfixed "
        "inside the model too."),
    evidence=(
        _E("Flagship NPI 1871991125 at 2155 33rd Ave, Columbus NE "
           "(historic HQ; enumerated 2014, predecessor entity 2005); "
           "Omaha corporate NPI 1356115562 enumerated 2023-11-08",
           "SOURCED", "CMS NPPES registry pull, 2026-07-10",
           "https://npiregistry.cms.hhs.gov/"),
        _E("23 active organizational NPIs across NE/IA/SD/MO/OH/IN/WI/"
           "CO/RI/NC/VA — the estate any dispatch architecture must span",
           "SOURCED", "CMS NPPES registry pull, 2026-07-10",
           "https://npiregistry.cms.hhs.gov/"),
        _E("No public description of MMT's CAD, prioritization, or "
           "customer-facing visibility was found",
           "FRAMEWORK", "2026-07-10 research sweep (dead-end log)", ""),
    ),
    subqs=(
        _S("Is dispatch centralized or market-based?",
           "Not published; the Columbus NE historic HQ plus Omaha "
           "corporate core is consistent with centralization but does "
           "not prove it — diligence: dispatch org design."),
        _S("How are trips entered?", "",
           skip="Company data — diligence request: intake channels "
           "(phone / portal / integration) by account."),
        _S("How are they prioritized?", "",
           skip="Company data — diligence request: priority scheme "
           "across scheduled, urgent, and critical requests."),
        _S("How are vehicles assigned?", "",
           skip="Company data — diligence request: assignment logic "
           "(chaining, acuity match, post proximity)."),
        _S("How are scheduled and urgent requests balanced?", "",
           skip="Company data — diligence request: reserve policy for "
           "urgent inserts into a scheduled board."),
        _S("How are critical-care trips prioritized?", "",
           skip="Company data — diligence request: CCT queueing and "
           "crew staging."),
        _S("How are cancellations managed?", "",
           skip="Company data — diligence request: cancellation workflow "
           "and cause coding."),
        _S("How are delays communicated?", "",
           skip="Company data — diligence request: proactive "
           "notification practice."),
        _S("Can customers see vehicle and ETA information?", "",
           skip="Company data — diligence request: customer-facing "
           "visibility — Question 7's checklist, applied to MMT."),
        _S("How is dispatch performance measured?", "",
           skip="Company data — diligence request: KPI set (on-time %, "
           "promised-vs-actual ETA, at-door wall time)."),
        _S("How does dispatch differ from traditional EMS?",
           "Structurally answerable: no PSAP and no response-time "
           "geometry — the problem is chaining known trips against "
           "promised windows, so IFT dispatch resembles logistics "
           "software more than 911 CAD."),
    ),
)


_GEOGRAPHY = Block(
    "q8-geography", "Geographic model",
    conclusion=(
        "Geography is the best-documented layer of the whole model: a "
        "contiguous NE/IA/SD legacy core (15 of 23 NPIs; 22 counties, "
        "~1.56M people on the I-80 spine) built over 35 years, and a "
        "2023-26 expansion ring (Kansas City, Columbus OH, Indianapolis, "
        "Milwaukee, Colorado Springs, Rhode Island, North Carolina) that "
        "is discontiguous by design — an account-led, not corridor-led, "
        "growth pattern."),
    why_true=(
        "The registry dates the build: legacy-core NPIs enumerate "
        "2005-2016 (Columbus predecessor 2005, flagship 2014, Council "
        "Bluffs 2015, Sioux City and Aberdeen 2016); the expansion NPIs "
        "cluster in 2023-24 (Des Moines Aug 2023, Omaha corporate Nov "
        "2023, Kansas City Mar 2024) — two distinct eras under two "
        "ownership regimes.",
        "Presence quality is tiered, not uniform: NPI-verified in six "
        "footprint metros, company/web-listed in four more (Lincoln, "
        "North Platte, Grand Island/Kearney, Cincinnati), adjacent-only "
        "for NW Indiana and Northern Virginia, and unverified in eight "
        "registry metros — and the 13-state claim outruns the 11 states "
        "with NPI evidence.",
        "The legacy core is corridor geometry: five Nebraska metros on "
        "the I-80 spine roughly 40-90 miles apart plus western Iowa — "
        "contiguous and backhaul-friendly — while the expansion ring "
        "(Rhode Island, North Carolina, coastal Virginia) shares no "
        "border with it.",
        "Anchoring varies by market and is documented at the metro "
        "grain: Columbus NE is a single-hospital market, Omaha holds "
        "four anchor systems, and North Platte is a single-hub long-leg "
        "market contested by AmeriPro's Priority acquisition."),
    why_matters=(
        "Discontiguous expansion forfeits corridor density — the "
        "strongest published cost lever (MedPAC's inverse volume-cost "
        "curve) — unless each new market is anchored by a committed "
        "account; the unnamed customer behind each 2023-26 NPI is "
        "therefore the central geographic diligence question."),
    evidence=(
        _E("23 active org NPIs: NE 4 · IA 9 · SD 2 · MO 1 · OH 1 · IN 1 "
           "· WI 1 · CO 1 · RI 1 · NC 1 · VA 1 (the VA record's same-org "
           "link unconfirmed — flagged)",
           "SOURCED", "CMS NPPES registry pull, 2026-07-10",
           "https://npiregistry.cms.hhs.gov/"),
        _E("MMT presence tiers by metro: NPI-verified (Omaha, Columbus "
           "NE, Columbus OH, Kansas City, Milwaukee, Des Moines), "
           "company/web (Lincoln, North Platte, GI/Kearney, Cincinnati), "
           "adjacent or unverified elsewhere",
           "SOURCED", "NPPES + company-web presence sweep, 2026-07-10",
           ""),
        _E("Legacy-core footprint: 22 counties, ~1.56M people (2020 "
           "Census) across 7 OMB CBSAs on the Omaha-Lincoln-Grand "
           "Island-Kearney-North Platte corridor",
           "GOV", "OMB 2023 CBSA delineations × 2020 Census county "
           "populations", ""),
        _E("Strong inverse relationship between response volume and cost "
           "per response — density is the cost lever new markets start "
           "without",
           "SOURCED", "MedPAC assessment of GADCS data, Dec 2025",
           "https://www.medpac.gov/wp-content/uploads/2025/01/Tab-M-Ambulance-Dec-2025.pdf"),
    ),
    subqs=(
        _S("In which markets does MMT operate?",
           "NPI-verified: Columbus NE, Omaha/Council Bluffs, Sioux City, "
           "Des Moines plus six smaller Iowa stations, Aberdeen/Huron SD, "
           "Kansas City, Columbus OH, Indianapolis, Milwaukee, Colorado "
           "Springs, Pawtucket RI, Elizabeth City NC; web-tier: Lincoln, "
           "North Platte, Grand Island/Kearney/Hastings, Cincinnati."),
        _S("How large is each market?",
           "The legacy core spans 22 counties / ~1.56M people (the "
           "8-county Omaha MSA is the largest); expansion-market service "
           "areas are publicly undefined."),
        _S("How long has each market operated?",
           "Columbus NE since 1987; Council Bluffs / Sioux City / "
           "Aberdeen since ~2015-16; the expansion ring since 2023-24 "
           "(NPI enumeration dates bound the timing)."),
        _S("What is fleet density by market?", "",
           skip="Company data — diligence request: units and posts by "
           "market; the 500+ vehicle total is not allocated publicly."),
        _S("How concentrated is demand?",
           "In the core, corridor-concentrated (five I-80 metros, "
           "Omaha-dominant); account-level concentration is a company-"
           "data ask."),
        _S("How contiguous is the footprint?",
           "The NE/IA/SD core is contiguous; the 2023-26 ring is "
           "discontiguous — Rhode Island, North Carolina, and coastal "
           "Virginia share nothing with it."),
        _S("Which markets are anchored by one major health-system "
           "customer?",
           "Structurally single-anchor: Columbus NE (Columbus Community "
           "Hospital) and North Platte (Great Plains Health); actual "
           "contract status is unconfirmed."),
        _S("Which markets serve multiple customers?",
           "Omaha (four anchor systems) and the other multi-system "
           "metros, structurally; the account roster per market is "
           "company data."),
        _S("What minimum demand is required to enter a market?", "",
           skip="Company data — diligence request: market-entry "
           "underwriting criteria."),
        _S("How long does market launch take?", "",
           skip="Company data — diligence request: launch playbook and "
           "time-to-breakeven; NPI dates bound only the licensure "
           "timing."),
        _S("How does a new market reach operating efficiency?",
           "Not published for MMT; the public benchmark is MedPAC's "
           "inverse volume-cost curve — density (chaining, backhaul) is "
           "the mechanism, and ramp curves are a diligence request."),
        _S("Which capabilities are centralized versus rebuilt locally?",
           "Not published; Question 1's split is the frame to test — "
           "dispatch, revenue cycle, protocols, and recruiting "
           "standardize, while density, licenses, and relationships stay "
           "local."),
    ),
)


_WORKFORCE = Block(
    "q8-workforce", "Workforce model",
    conclusion=(
        "Headcount is public and steep — 350+ (2015) to ~1,000 (2022) to "
        "2,800+ (2026) — and so is the friction: three FLSA wage-and-hour "
        "suits in three federal districts (OH 2020, WI 2023, NE 2024) "
        "plus a closed NLRB charge, the classic pattern of crew-comp "
        "practices scaling faster than compliance; turnover, wages, "
        "overtime, and scheduling are all company data."),
    why_true=(
        "The headcount trajectory is documented at three points: 350+ "
        "employees at the 2015 sale, ~1,000 at the 2022 deal (sell-side "
        "advisor), 2,800+ on the 2026 company site — roughly a tripling "
        "per ownership era — while third-party estimators still publish "
        "~700-784, disagreeing with the company by up to ~4x.",
        "The litigation registry is public: Reust (N.D. Ohio, 2020), "
        "Wroblewski (E.D. Wis., 2023), and Meysenburg (D. Neb., 2024) — "
        "all FLSA wage-and-hour, outcomes sealed without PACER — plus "
        "NLRB case 14-CA-251082 (Wichita, 2019, closed).",
        "The industry cost structure makes labor the binding constraint: "
        "70.7% of ambulance cost is labor, and MMT's core state is losing "
        "its volunteer EMS subsidy (80%+ of Nebraska agencies "
        "all-volunteer, contracting) — a hiring tailwind for paid "
        "platforms and a wage-pressure headwind at once.",
        "Credential tiers define the recruiting problem: EMT (BLS) → "
        "paramedic (ALS) → nurse/specialty crew (CCT) — the scarce tiers "
        "are exactly the high-relative-value ones."),
    why_matters=(
        "At a 70.7% labor share, workforce IS the unit economics: "
        "turnover, overtime, and wage trajectory move margin more than "
        "any pricing lever — and the FLSA docket is the cheapest "
        "early-warning signal a buyer gets before payroll data arrives."),
    evidence=(
        _E("2015 sale: a one-state operation with 350+ employees, 13 "
           "ground locations, two helicopter bases",
           "SOURCED", "Lincoln Journal Star, Feb 2015",
           "https://journalstar.com/business/local/private-equity-firm-buys-nebraska-ambulance-company/article_f17387c0-ec6f-5872-b159-3c99a212dd03.html"),
        _E("'one of the largest, independently owned providers of "
           "private ground ambulance services with operations currently "
           "in seven states and nearly 1,000 employees' (2022)",
           "SOURCED", "Lincoln International transaction notice, 2022",
           "https://www.lincolninternational.com/transactions/panorama-point-partners-dixon-midland-and-orix-have-sold-midwest-medical-transport-to-harbour-point-capital/"),
        _E("Three FLSA wage-and-hour suits: N.D. Ohio 1:20-cv-01548 "
           "(2020), E.D. Wis. 2:23-cv-00877 (2023), D. Neb. "
           "4:2024-cv-03107 (2024); NLRB 14-CA-251082 (Wichita 2019, "
           "closed)",
           "SOURCED", "Justia / CourtListener / NLRB public dockets",
           "https://www.courtlistener.com/docket/67552669/wroblewski-v-midwest-medical-transport-company-llc/"),
        _E("Labor is 70.7% of ambulance service cost — the industry's "
           "binding input",
           "SOURCED", "CMS/RAND GADCS Year 1-4 appendix, via AAA coverage",
           "https://ambulance.org/2025/12/09/cms-releases-new-gadcs-report/"),
    ),
    subqs=(
        _S("How many employees and crews operate in each market?", "",
           skip="Company data — diligence request: headcount and staffed "
           "crews by market; only the 2,800+ total is public."),
        _S("What credentials are required?",
           "Tier-driven, industry-wide: EMT for BLS, paramedic for ALS, "
           "nurse/specialty crew for CCT; MMT's staffing matrices are "
           "company data."),
        _S("How does MMT recruit?", "",
           skip="Company data — diligence request: recruiting engine and "
           "pipeline; public job postings (Cincinnati, 2025-26) show "
           "active hiring without quantifying it."),
        _S("How does compensation compare with local alternatives?", "",
           skip="Company data — diligence request: wage benchmarks vs "
           "fire departments and hospital employers; the FLSA docket "
           "makes comp-practice review non-optional."),
        _S("How are schedules designed?", "",
           skip="Company data — diligence request: shift patterns; FLSA "
           "wage-and-hour suits are the standard shift-pay/overtime fact "
           "pattern for this question."),
        _S("How much overtime is used?", "",
           skip="Company data — diligence request: overtime hours as a "
           "share of paid hours."),
        _S("What is employee turnover?", "",
           skip="Company data — diligence request: turnover by role and "
           "market."),
        _S("Which roles are hardest to fill?",
           "Structurally, paramedics and CCT-credentialed crews — the "
           "scarce, high-relative-value tiers; MMT's vacancy data is a "
           "diligence request."),
        _S("How does dedicated volume improve workforce planning?",
           "Scheduled books make shifts plannable (Question 1: "
           "forecastable demand) — the structural claim; whether MMT "
           "realizes it will show in its overtime ratio."),
        _S("How does MMT maintain clinical consistency across markets?",
           "",
           skip="Company data — diligence request: medical direction, "
           "protocol, and QA structure across the 11 NPI states."),
        _S("How does labor availability constrain growth?",
           "Industry-wide it is the binding constraint (70.7% cost "
           "share; volunteer contraction in the core state); MMT's "
           "market-entry pacing against staffing is a diligence "
           "request."),
    ),
)


_TECH = Block(
    "q8-tech", "Technology model",
    conclusion=(
        "Technology is the least-documented layer of MMT's model — no "
        "public source describes its booking, CAD/AVL, customer "
        "visibility, integrations, or reporting — a not-found that "
        "matters because Question 7's failure modes (ETA, visibility, "
        "delay attribution) are exactly what IFT technology exists to "
        "fix."),
    why_true=(
        "The research sweep found no MMT technology description — no "
        "named CAD vendor, no customer portal, no integration "
        "announcement — recorded as not-found, not as absence of a "
        "stack.",
        "The capability bar is set by the market: dispatch/CAD-AVL, "
        "transfer-center integration, and ETA visibility are what "
        "separate a first-call partner from a spot vendor — so the stack "
        "is thesis-critical whether or not it is public.",
        "The measurable asks are known in advance: future-demand intake, "
        "modality guidance, delay-cause coding, and hospital-vs-provider "
        "delay attribution — Question 7 defines the checklist any "
        "product demo must answer.",
        "Proprietary-vs-third-party is an economics question, not a "
        "feature question: third-party CAD is replicable by any funded "
        "competitor (Question 1's competitive read), so durable "
        "differentiation must live in workflow integration, not the "
        "software license."),
    why_matters=(
        "If the technology cannot separate hospital-caused from "
        "provider-caused delay, MMT cannot prove its own reliability "
        "story to a buyer or a hospital — the reporting layer is what "
        "converts 'dedicated' from a claim into a contract metric."),
    evidence=(
        _E("No public description of MMT's booking, CAD/AVL, portal, or "
           "reporting stack was found",
           "FRAMEWORK", "2026-07-10 research sweep (dead-end log)", ""),
        _E("Information flow measurably moves transfer clocks: EMS "
           "prenotification cut stroke door-in-door-out time 20.1 "
           "minutes — the class of gain IFT technology targets",
           "ACADEMIC", "GWTG-Stroke analysis, JAMA 2023",
           "https://doi.org/10.1001/jama.2023.12739"),
    ),
    subqs=(
        _S("What technology does MMT use for booking?", "",
           skip="Company data — diligence request: booking channels and "
           "systems."),
        _S("What technology supports dispatch?", "",
           skip="Company data — diligence request: CAD/AVL vendor or "
           "in-house build."),
        _S("What customer-facing visibility is available?", "",
           skip="Company data — diligence request: portal, ETA feeds, "
           "and status notifications."),
        _S("Are health-system integrations available?", "",
           skip="Company data — diligence request: EHR / transfer-center "
           "integrations live today."),
        _S("Can the system receive future scheduled demand?", "",
           skip="Company data — diligence request: advance-booking and "
           "standing-order support."),
        _S("Can it support modality guidance?", "",
           skip="Company data — diligence request: structured intake "
           "with level-of-service logic (Question 7's modality fix)."),
        _S("Can it track delay reasons?", "",
           skip="Company data — diligence request: delay-cause coding "
           "taxonomy."),
        _S("Can it separate hospital-caused and provider-caused delays?",
           "",
           skip="Company data — diligence request: attribution reporting "
           "— the single most valuable artifact for validating the "
           "reliability story."),
        _S("What performance reporting is provided?", "",
           skip="Company data — diligence request: customer-facing KPI "
           "reports (on-time %, promised-vs-actual ETA, wall time)."),
        _S("Is the technology proprietary, third-party, or combined?", "",
           skip="Company data — diligence request: stack ownership and "
           "vendor contracts."),
        _S("Which technology capabilities are meaningfully "
           "differentiated?",
           "Answerable only structurally: differentiation must live in "
           "workflow integration and delay-attribution reporting, since "
           "CAD itself is purchasable by any competitor."),
    ),
)


_ECONOMICS = Block(
    "q8-economics", "Economics",
    conclusion=(
        "No MMT financial figure in public view is usable — the three "
        "estimators disagree ~3x ($100M to $296M) and all conflict with "
        "the company's own headcount — so the economics answer is the "
        "industry ledger MMT must beat: $1,147 mean reimbursement vs "
        "$1,778 private-for-profit mean cost per transport, with payer "
        "mix, unit-hour utilization, and density as the levers that make "
        "a dedicated book positive."),
    why_true=(
        "The estimate conflict is disqualifying by itself: $296.4M / 784 "
        "employees (Growjo) vs $293.6M (ZoomInfo) vs $100-250M / ~700 "
        "(LeadIQ) — shown side by side, never blended, never used for "
        "underwriting.",
        "The published mean spread is negative — $1,147 mean "
        "reimbursement vs $2,673 all-agency mean cost — because the mean "
        "carries municipal readiness books; the private for-profit cost "
        "mean ($1,778) plus a scheduled book's higher unit-hour "
        "utilization is the structural path to a positive spread — the "
        "IFT thesis in one line.",
        "Revenue per trip is fee-ladder arithmetic: BLS 1.00 → ALS1 1.20 "
        "→ ALS2 2.75 → SCT 3.25 relative values on a $278.98 CY2025 "
        "conversion factor, ~$8/loaded-mile Medicare vs ~$17 commercial, "
        "commercial ~2.0x Medicare overall, and 19.7% of transports "
        "collecting nothing — mix, not the base rate, is the margin.",
        "The cost side is labor and geometry: 70.7% labor share, unpaid "
        "deadhead and wait, MedPAC's inverse volume-cost curve making "
        "density the cost lever, and a +22.6% super-rural add-on that "
        "exists because rural geometry breaks the base rate."),
    why_matters=(
        "Every lever this section asks about — modality, distance, "
        "density, dedication, payer mix, denials, ramp, scale thresholds "
        "— has a cited industry direction and no public MMT value; the "
        "diligence pack is therefore a request list against company "
        "data, with the industry benchmarks as the scoring key."),
    evidence=(
        _E("Revenue estimates: $296.4M/784 employees (Growjo) vs $293.6M "
           "(ZoomInfo) vs $100-250M/~700 (LeadIQ) — ~3x disagreement, "
           "all conflicting with the company's 2,800+ headcount claim",
           "SOURCED", "Growjo / ZoomInfo / LeadIQ, 2026 (unaudited "
           "third-party estimates; re-verify)", ""),
        _E("Mean reimbursement $1,147/transport vs mean cost $2,673 "
           "all-agency / $1,778 private for-profit; labor 70.7%; 19.7% "
           "of transports unpaid",
           "SOURCED", "CMS/RAND GADCS Year 1-2 + Year 1-4 reports (via "
           "trade coverage; re-verify)",
           "https://emsmc.com/in-the-news/takeaways-from-the-first-cms-data-collection-report-on-ambulance-services-and-what-we-need-to-do-about-it/"),
        _E("CY2025 AFS conversion factor $278.98 × RVUs (BLS 1.00 / ALS1 "
           "1.20 / ALS2 2.75 / SCT 3.25); super-rural add-on +22.6% "
           "through 2027",
           "GOV", "CMS AFS / MedPAC Payment Basics 2025; CAA 2026 §6203 "
           "(re-verify)", ""),
        _E("Commercial ESI base rate 2.0x Medicare ($718 vs $365, 2022); "
           "mileage $17 vs $8",
           "SOURCED", "Health Care Cost Institute",
           "https://healthcostinstitute.org/all-hcci-reports/commercial-prices-for-ground-ambulance-are-double-medicare-rates/"),
        _E("Strong inverse relationship between response volume and cost "
           "per response — density is the profitability mechanism",
           "SOURCED", "MedPAC assessment of GADCS data, Dec 2025",
           "https://www.medpac.gov/wp-content/uploads/2025/01/Tab-M-Ambulance-Dec-2025.pdf"),
    ),
    subqs=(
        _S("What drives revenue per trip?",
           "HCPCS level (BLS 1.00 → SCT 3.25 RVU), loaded miles, payer "
           "(commercial ~2.0x Medicare), and collection (19.7% collect "
           "nothing); MMT's realized $/trip is a diligence request."),
        _S("What drives cost per trip?",
           "Labor first (70.7% of cost), then deadhead and at-door wait "
           "— the unpaid hours; MMT's cost build is a diligence "
           "request."),
        _S("How do modality and distance affect margin?",
           "Higher tiers carry higher relative values but scarcer crews; "
           "distance pays only loaded miles (~$8/mi Medicare), so "
           "one-way legs tax margin; MMT actuals are company data."),
        _S("How does fleet density affect profitability?",
           "Via MedPAC's inverse volume-cost curve: density chains "
           "trips, cuts deadhead, and lifts unit-hour utilization — the "
           "strongest published cost lever."),
        _S("How does dedicated capacity affect utilization?",
           "Scheduled books target UHU above the 0.30-0.50 911 band "
           "(AIMHI survey mean 0.508) — dedication converts forecastable "
           "demand into utilization; MMT's UHU is a diligence request."),
        _S("How does payer mix affect economics?",
           "Decisively: Medicare ~40% of a typical agency mix, "
           "commercial ~2.0x, Medicaid ~0.59x (derived from MA HPC "
           "medians), unpaid 19.7% — the commercial/Medicaid split of "
           "the residual is the flagged ask."),
        _S("What role do direct health-system payments play?",
           "The channel unique to IFT (Question 1): non-covered trips, "
           "denied-trip contract terms, and any availability retainers; "
           "MMT's facility-contract revenue share is company data."),
        _S("How much risk does MMT bear for denials?", "",
           skip="Company data — diligence request: denial rate, "
           "clean-claim rate, and contract allocation of denied trips; "
           "industry exposure is 13.2% improper (63.5% documentation)."),
        _S("How long does a new market take to mature?", "",
           skip="Company data — diligence request: ramp curves by market "
           "cohort (the 2023-24 NPI vintage is the natural test set)."),
        _S("What scale is required for market-level profitability?", "",
           skip="Company data — diligence request: market-level P&L "
           "thresholds; the public prior is MedPAC's density curve — "
           "direction without a number."),
        _S("Which service lines are most attractive?",
           "Structurally: commercially insured ALS2/SCT and dense "
           "chained BLS with backhaul (Question 1); MMT's line-level "
           "margins are company data."),
        _S("Which are strategically important but less profitable?",
           "Structurally: long rural one-ways, Medicaid/unfunded "
           "discharges, and wheelchair/para-transit — the availability "
           "book that wins contracts; MMT's cross-subsidy design is a "
           "diligence request."),
    ),
)


Q8 = QuestionDef(
    num=8,
    slug="mmt-model",
    title="What is MMT's operating model?",
    storyline=(
        "The public record proves the shape — a 35-year, 13-state-claimed "
        "(11 NPI-verified) dedicated-IFT platform grown from one Columbus "
        "NE ambulance — but every metric that would prove the model works "
        "(mix, retention, utilization, turnover, margin) is company data, "
        "requested here and never invented."),
    visual_key="mmt-system",
    blocks=(_SCOPE, _CUSTOMERS, _CAPACITY, _DISPATCH, _GEOGRAPHY,
            _WORKFORCE, _TECH, _ECONOMICS),
)


QUESTIONS = (Q7, Q8)
