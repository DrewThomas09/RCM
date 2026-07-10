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


# __PART5__
