"""In-Depth content — Questions 4-6: how the IFT ecosystem works, the
operating models health systems use, and how they procure and manage IFT.

Authored 2026-07-10 from the suite's cited corpus (ift_health_systems,
ift_insourcing, ift_geo, ift_npi_landscape, ift_study, ift_unit_economics,
ift_demand_evidence, ift_growth_evidence, ift_company, ift_mmt) plus the
payment-rules and operational-failure dossiers. Every evidence line carries
its basis + source; excerpt-grade captures carry "(re-verify)"; contract and
company facts that are not public are marked as diligence requests, never
invented. Analytic scaffolds carry the FRAMEWORK basis.
"""
from __future__ import annotations

from .ift_indepth import Block, Evidence, QuestionDef, SubQ

_E = Evidence
_S = SubQ


# ═════════════════════════════════════════════════════════════════════════════
# Question 4 — How does the IFT ecosystem actually work?
# ═════════════════════════════════════════════════════════════════════════════

_PARTICIPANTS = Block(
    "q4-participants", "Decision participants",
    conclusion=(
        "One IFT trip requires roughly eleven distinct decisions — initiate, "
        "certify necessity, pick modality, select provider, approve "
        "destination, confirm the bed, authorize payment, dispatch, monitor, "
        "escalate, confirm completion — made by six-plus different parties "
        "across four organizations; no single participant owns the trip end "
        "to end, and that map is the diagnosis."),
    why_true=(
        "Initiation and necessity sit at the bedside: a nurse, case manager "
        "or ED physician starts the trip, the attending certifies necessity "
        "(clinically, and for Medicare via 42 CFR 410.40 plus the PCS), and "
        "the same clinician picks the modality — usually without written "
        "criteria and with nobody auditing the choice.",
        "Destination approval is a two-key decision at the RECEIVER: the "
        "accepting physician agrees and bed management confirms a staffed "
        "bed — EMTALA's appropriate-transfer rule requires the sender to "
        "secure receiver acceptance (space + qualified personnel) before "
        "the patient moves.",
        "Payment authorization belongs to whoever the coverage says — "
        "Medicare has no IFT prior authorization outside RSNAT repetitive "
        "trips, MA plans and Medicaid MCOs add their own — while dispatch, "
        "monitoring and escalation all live inside the provider, invisible "
        "to the buyer in real time.",
        "Completion is split: the crew's ePCR closes the provider's record "
        "and the receiving unit signs the handoff — nobody reconciles the "
        "two for the sending hospital, which typically learns the trip "
        "finished only if someone asks."),
    why_matters=(
        "A process with this many hand-offs fails at the seams, and the "
        "seams are where the measured failures live — stroke-transfer "
        "door-in-door-out time is dominated by the disposition/transport "
        "interval, not imaging. A dedicated partner is selling the collapse "
        "of these decisions into one accountable counterparty."),
    evidence=(
        _E("EMTALA appropriate transfer: the receiving facility must have "
           "available space and qualified personnel and agree to accept; "
           "the transfer runs through qualified personnel and "
           "transportation equipment",
           "GOV", "42 CFR 489.24",
           "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-489/subpart-B/section-489.24"),
        _E("Medicare non-emergency ambulance requires medical necessity "
           "plus a physician certification statement; repetitive trips "
           "need the PCS in advance, dated within 60 days",
           "GOV", "42 CFR 410.40 / CMS Benefit Policy Manual ch.10", ""),
        _E("Mean stroke-transfer DIDO 171.4 min: door-to-imaging 18.3 min, "
           "imaging-to-door 153.1 min — the disposition/transport interval "
           "dominates the decision chain's cost",
           "ACADEMIC", "JAMA Network Open 2024 (n=28,887)",
           "https://doi.org/10.1001/jamanetworkopen.2024.31183"),
        _E("CHI Health's system transfer center RNs can accept STEMI, "
           "trauma and stroke transfers directly 'to expedite "
           "transportation arrangements' — a system consolidating the "
           "accept + book decisions",
           "SOURCED", "CHI Health transfer-center page, 2026-07-10 pull "
           "(re-verify)",
           "https://www.chihealth.com/services/transfer-center"),
    ),
    subqs=(
        _S("Who initiates the trip?",
           "The bedside team — nurse/case manager for discharge legs, the "
           "ED or attending physician for up-transfers; at spoke hospitals "
           "usually the ED physician calling the hub."),
        _S("Who determines that transport is medically necessary?",
           "Clinically the attending; for payment, 42 CFR 410.40(e) plus "
           "the PCS — and a signed PCS alone does not make the trip "
           "payable (the MAC position)."),
        _S("Who determines the modality?",
           "The ordering clinician (wheelchair/BLS/ALS/CCT), usually "
           "without written criteria — brokers script this decision in "
           "NEMT; nobody audits it in IFT."),
        _S("Who selects the provider?",
           "The transfer center where one exists (CHI's 24/7 center books "
           "transport); otherwise unit staff working a call list."),
        _S("Who approves the destination?",
           "The receiving physician (acceptance, an EMTALA precondition); "
           "payer rules constrain which destination is COVERED — Medicare "
           "pays only to the nearest appropriate facility."),
        _S("Who confirms bed or appointment availability?",
           "Receiving bed management / the house supervisor; transfer "
           "centers exist largely to make that one confirmation reliable."),
        _S("Who authorizes payment?",
           "The payer, mostly after the fact — Medicare prior-authorizes "
           "only RSNAT repetitive trips; MA/MCO plans vary — and the "
           "hospital itself on facility-responsible trips."),
        _S("Who dispatches the vehicle?",
           "The provider's dispatcher — the first participant in the chain "
           "employed by neither hospital."),
        _S("Who monitors performance?",
           "Usually nobody on the buyer side: the provider sees its own "
           "times, the hospital sees anecdotes — the governance gap "
           "Question 6 documents."),
        _S("Who owns escalation?",
           "Undefined in most markets — nurses re-dial the list; dedicated "
           "contracts name a ladder (dispatch supervisor → ops leader → "
           "executive sponsor)."),
        _S("Who confirms trip completion?",
           "The crew's ePCR plus the receiving unit's handoff signature; "
           "the sending hospital typically has no completion feed at all."),
    ),
)


_HEALTH_SYSTEM = Block(
    "q4-healthsystem", "Health-system responsibilities",
    conclusion=(
        "Inside the hospital, ten roles each control one sliver of the "
        "trip — the nurse controls readiness, the physician the order, case "
        "management the plan, the transfer center the booking, supply chain "
        "the paper, finance a spend it cannot see — and the two structural "
        "defects are duplication at booking and absence at ownership: no "
        "role owns transport as a program."),
    why_true=(
        "Clinical roles: the bedside nurse controls whether the patient is "
        "actually ready at pickup (lines, meds, paperwork — the "
        "patient-not-ready wait is hers); the physician controls the order, "
        "the necessity documentation and the PCS; case management and "
        "discharge planning control destination choice and timing — and "
        "transport-related tasks are a measured drag on discharge (one "
        "site's most frequent uncompleted discharge task).",
        "Operational roles: the transfer center controls acceptance and "
        "booking where it exists — CHI runs a 24/7 center for its "
        "14-hospital system, Nebraska Medicine runs one inside a 'Capacity "
        "Optimization Hub', Methodist publishes a transfer line — while "
        "bed management controls the staffed-bed ledger every trip frees "
        "or fills.",
        "Business roles hold fragments: supply chain holds whatever "
        "contract exists (often a letter, sometimes nothing), revenue "
        "cycle touches only facility-billed trips and bounced denials, "
        "finance sees transport scattered across unit cost centers, and "
        "executives meet it only when boarding becomes a board topic.",
        "The defect map: booking and status-chasing are DUPLICATED across "
        "unit, case management and transfer center; program ownership, "
        "performance data, demand forecasting and vendor governance are "
        "ABSENT — they belong to nobody."),
    why_matters=(
        "Selling transport to a hospital means finding the buyer inside "
        "this map. Systems that appoint one accountable owner — usually "
        "under capacity/throughput leadership — are the only ones "
        "structurally able to execute a dedicated partnership."),
    evidence=(
        _E("Delayed discharges: weighted mean 22.8% of discharges delayed "
           "(range 1.6-91.3% across 64 studies); delay costs $142-31,935 "
           "USD PPP per case",
           "ACADEMIC", "Landeiro et al., The Gerontologist 2019 "
           "(systematic review)",
           "https://doi.org/10.1093/geront/gnx028"),
        _E("3.5% of hospitalizations consumed 27.2% of inpatient days at "
           "a US academic hospital; facility placement was the most "
           "common non-medical discharge barrier at every timepoint",
           "ACADEMIC", "Gao & Berland, Brown J Hosp Med 2022",
           "https://doi.org/10.56305/001c.36593"),
        _E("Pending care-management/transportation needs were the most "
           "frequent uncompleted discharge task (47%) in a single-site "
           "improvement study",
           "ACADEMIC", "Single-site discharge-task QI study, PMC11023539 "
           "(re-verify)", ""),
        _E("CHI launched its 24/7 system transfer center in 2018 for a "
           "14-hospital network; at DHHS request it expanded to "
           "coordinate ALL Nebraska hospitals' COVID transfers (Apr 2020)",
           "SOURCED", "CHI Health system pages + press, 2026-07-10 pull "
           "(re-verify)",
           "https://www.chihealth.com/services/transfer-center"),
    ),
    subqs=(
        _S("What does the bedside nurse control?",
           "Patient readiness at pickup — lines, meds, paperwork, family — "
           "the largest controllable component of provider door time."),
        _S("What does the case manager control?",
           "The discharge plan: destination type, payer legwork, and when "
           "the patient becomes transport-eligible."),
        _S("What does the discharge planner control?",
           "Destination selection and acceptance among SNF/IRF/LTACH "
           "options, plus the discharge packet the receiver requires."),
        _S("What does the transfer center control?",
           "Acceptance, physician matching, bed assignment and transport "
           "booking for transfers — CHI's accepts STEMI/trauma/stroke "
           "directly on behalf of its service lines."),
        _S("What does bed management control?",
           "The staffed-bed ledger — which bed the outbound trip frees and "
           "when the inbound patient can land."),
        _S("What does the physician control?",
           "The transfer decision, the physician-to-physician acceptance "
           "conversation, medical-necessity documentation and the PCS."),
        _S("What does supply chain control?",
           "The contract and rates, where any exist — often a preferred-"
           "provider letter with no committed capacity (the contract-form "
           "gap Question 6 documents)."),
        _S("What does revenue cycle control?",
           "Little on most trips (the provider bills the payer); it pays "
           "invoices on facility-responsible trips and fields the disputes "
           "when denials bounce back."),
        _S("What does hospital finance control?",
           "A spend it cannot see — transport fragments across unit cost "
           "centers, invoices and provider write-offs; few systems can "
           "state an all-in figure (a standing diligence request)."),
        _S("What does executive leadership control?",
           "Nothing day-to-day — transport reaches the C-suite as a "
           "boarding/throughput crisis, not as a managed program."),
        _S("Where are responsibilities duplicated?",
           "Booking and status-chasing (unit, case management and transfer "
           "center all re-call the provider) and necessity documentation "
           "(nurse, physician and provider re-collect the same facts)."),
        _S("Where are responsibilities absent?",
           "Program ownership, performance measurement, demand forecasting "
           "and vendor governance — the four maturity gaps Question 6 "
           "grades."),
    ),
)


_PROVIDER = Block(
    "q4-provider", "Provider responsibilities",
    conclusion=(
        "The provider owns everything between 'trip requested' and 'cash "
        "collected' — validation, assignment, crew match, ETA, escalation, "
        "the trip record, billing, denials — and performs all of it with "
        "information the hospital only half-supplies, which is why "
        "documentation, not driving, is where IFT trips financially fail."),
    why_true=(
        "Intake must capture three payloads — clinical (acuity, equipment, "
        "isolation), logistical (origin/destination/time) and financial "
        "(payer, PCS) — before the dispatcher validates and the scheduler "
        "matches vehicle and crew to the tier's credential requirements "
        "(EMT/paramedic/nurse).",
        "During the trip the provider owns the promises: ETA and updates "
        "to the unit, clinical escalation en route under standing "
        "protocols and online medical direction, and re-triage of failed "
        "trips (patient not ready, bed gone, vehicle down) — with no "
        "contractual standard for any of it in the modal IFT relationship.",
        "After the trip the ePCR is simultaneously the clinical record and "
        "the claim evidence; the provider bills payer or hospital and "
        "manages denials in a market where the ambulance improper-payment "
        "rate is 13.2% and 63.5% of it is insufficient documentation — "
        "the documentation chain IS the revenue chain.",
        "Account-level performance review is the step most providers skip: "
        "mature operators run joint reviews per account; call-list vendors "
        "run none, which is why buyers cannot distinguish them on paper."),
    why_matters=(
        "Every step in this chain is a place a dedicated, instrumented "
        "operator can be measurably better than a call-list vendor — and "
        "the billing/denial layer is where revenue-cycle scale becomes a "
        "genuine moat rather than a back office."),
    evidence=(
        _E("Ambulance improper-payment rate 13.2%, projected $595.1M; "
           "insufficient documentation 63.5% of the error, medical "
           "necessity 27.5%",
           "GOV", "CMS CERT 2024 supplemental improper-payment data "
           "(re-verify)", ""),
        _E("19.7% of ambulance transports collect nothing (up from 18.8% "
           "in the first cohort) — the denial/no-pay tail the provider "
           "absorbs by default",
           "SOURCED", "CMS/RAND GADCS Year 1-4 appendix (Dec 2025), via "
           "AAA coverage",
           "https://ambulance.org/2025/12/09/cms-releases-new-gadcs-report/"),
        _E("Three-fourths of California hospitals detained EMS crews more "
           "than one hour; one-third delayed return to service by more "
           "than three hours (830,637 transports, 2017)",
           "ACADEMIC", "Backer et al., Prehospital Emergency Care 2018",
           "https://doi.org/10.1080/10903127.2018.1525456"),
        _E("Non-emergency claims require 410.40(e) necessity (bed-confined "
           "all-three test or contraindication) plus the PCS; repetitive "
           "trips require RSNAT prior authorization",
           "GOV", "42 CFR 410.40 / CMS RSNAT model", ""),
    ),
    subqs=(
        _S("What information must the provider receive?",
           "The booking triad: clinical (tier, equipment — vent, drips, "
           "isolation, weight), logistical (origin unit, destination, time "
           "window), financial (payer, PCS/necessity documentation)."),
        _S("Who validates the request?",
           "The provider's dispatcher/intake — checking tier against crew "
           "capability and payability; a broker script does this in NEMT, "
           "provider habit does it in IFT."),
        _S("Who assigns the vehicle?",
           "The scheduler/dispatcher, balancing the posting plan, trip "
           "chaining and acuity match."),
        _S("Who confirms crew capability?",
           "The provider, against state licensure plus its own "
           "credentialing (EMT/paramedic/RN by tier) — CCT requests fail "
           "this check most often."),
        _S("Who communicates the ETA?",
           "Provider dispatch to the requesting unit — and unreliable ETAs "
           "are the study's #1 recorded hospital complaint."),
        _S("Who updates the health system?",
           "The provider, if anyone; live status portals are the "
           "exception, phone-chasing the norm."),
        _S("Who manages clinical escalation?",
           "The crew, under standing protocols and online medical control; "
           "deterioration can divert the trip to the nearest ED."),
        _S("Who handles a failed trip?",
           "Provider dispatch re-queues it; the crew-hour cost is the "
           "provider's and the delay is the hospital's — a mutual loss "
           "with no contractual owner."),
        _S("Who captures the trip record?",
           "The crew's ePCR — times, mileage, care en route — which is "
           "both the clinical record and the claim evidence."),
        _S("Who submits the bill?",
           "The provider (or its RCM vendor) to Medicare/Medicaid/"
           "commercial, or an invoice to the hospital on facility-"
           "responsible trips."),
        _S("Who manages denials?",
           "The provider's revenue cycle; with necessity and documentation "
           "the dominant error causes, denial management is a core "
           "competency, not overhead."),
        _S("Who reviews account-level performance?",
           "In mature relationships a joint quarterly review; in most IFT "
           "accounts nobody — the same governance gap, seen from the "
           "provider side."),
    ),
)


_RECEIVING = Block(
    "q4-receiving", "Receiving-party responsibilities",
    conclusion=(
        "The receiving facility controls acceptance, bed truth and handoff "
        "speed — and its wall time is where system capacity quietly "
        "drains: crews were detained past an hour at three-quarters of "
        "California hospitals, and every wall-hour is a unit-hour "
        "subtracted from the next sender's trip."),
    why_true=(
        "Acceptance is formal — under EMTALA the receiver must have space "
        "and qualified personnel and agree — but bed truth is operational: "
        "a bed 'available' at booking can be gone at arrival, and "
        "re-confirmation is nobody's named job.",
        "The receiver needs the packet in advance (clinical summary, med "
        "list, necessity data, payer face sheet); missing information "
        "stalls the handoff at the door, and stroke data shows information "
        "arriving AHEAD of the patient (EMS prenotification) cuts "
        "door-in-door-out time by ~20 minutes.",
        "Clinical responsibility transfers at the documented bedside "
        "handoff, not at the door — until then the crew holds the patient, "
        "which is the mechanism of wall time.",
        "Offload delay is measured and fat-tailed: median ambulance "
        "patient-offload time is ~11 minutes, but 3.3% of agencies had a "
        "quarter or more of transports waiting over 30 minutes — enough "
        "that California legislated a 30-minute/90% standard with monthly "
        "per-hospital monitoring."),
    why_matters=(
        "Receivers are unpaid gatekeepers of provider economics. A partner "
        "that instruments arrival-to-handoff by facility hands systems the "
        "data to manage their own front door — a service no call-list "
        "vendor offers, and a governance artifact no hospital builds "
        "alone."),
    evidence=(
        _E("Three-fourths of hospitals detained EMS crews >1 hour, 40% "
           ">2 hours, one-third >3 hours (California, 830,637 transports, "
           "2017)",
           "ACADEMIC", "Backer et al., Prehospital Emergency Care 2018",
           "https://doi.org/10.1080/10903127.2018.1525456"),
        _E("Median ambulance patient-offload time 10.9 min (IQR 6.6-17.5) "
           "across 7,237,606 records (2024); 3.3% of agencies had >=25% "
           "of transports offloading >30 min",
           "ACADEMIC", "Shaw et al., Prehospital Emergency Care 2025",
           "https://doi.org/10.1080/10903127.2025.2535576"),
        _E("California AB 40 (2023): ambulance patient offload standard "
           "not to exceed 30 minutes, 90% of the time, with monthly "
           "per-hospital EMSA monitoring",
           "GOV", "CA AB 40 / EMSA APOT program (re-verify)",
           "https://emsa.ca.gov/apot/"),
        _E("EMTALA conditions an appropriate transfer on the receiving "
           "facility's available space, qualified personnel and agreement "
           "to accept",
           "GOV", "42 CFR 489.24",
           "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-489/subpart-B/section-489.24"),
    ),
    subqs=(
        _S("Who confirms acceptance?",
           "The receiving physician plus the facility (space and "
           "personnel) — an EMTALA precondition to the transfer."),
        _S("Who confirms the destination is still available?",
           "Formally bed management at booking; at arrival, often no one — "
           "the bed-gone-at-arrival failure is recurring and unowned."),
        _S("What information must be received in advance?",
           "Clinical summary and med list, reason-for-transfer/necessity "
           "data, equipment needs, and the payer face sheet — the same "
           "triad the provider needed at booking."),
        _S("What delays handoff at the destination?",
           "No assigned bed or staff, a missing packet, shift change, and "
           "ED saturation — offload delay is the measured symptom of all "
           "four."),
        _S("Who accepts clinical responsibility?",
           "The receiving clinical team at bedside handoff; the crew "
           "documents the transfer of care in the ePCR."),
        _S("When does responsibility formally transfer?",
           "At the documented handoff — report given, patient moved to the "
           "receiving bed/monitor — not at the door."),
        _S("What causes the vehicle and crew to remain waiting?",
           "Everything that delays handoff: the crew cannot leave until "
           "care transfers, so wall time is a receiver-controlled cost the "
           "provider bears."),
        _S("How does destination wait time affect future capacity?",
           "Directly — each wall-hour deletes a unit-hour (a third of CA "
           "hospitals held crews >3 hours); this trip's wall time is the "
           "next trip's 'no capacity'."),
    ),
)


_INFORMATION = Block(
    "q4-information", "Information flow",
    conclusion=(
        "A bookable IFT trip is three data payloads — clinical, logistical, "
        "financial — entered into four to six disconnected systems (EHR, "
        "transfer-center log, phone, provider CAD, ePCR, billing) and "
        "re-keyed at nearly every hop; the payload that most often fails a "
        "trip financially is the financial one, and the one that most "
        "often delays it is the clinical one."),
    why_true=(
        "Booking requires acuity/equipment (clinical), origin/destination/"
        "time (logistical) and payer/PCS (financial), assembled by phone "
        "in most markets — no interoperability standard connects hospital "
        "EHRs to ambulance CAD/ePCR systems.",
        "Content is re-keyed unit → transfer center → dispatch → crew "
        "ePCR → billing, losing fidelity at each hop; no missing-data rate "
        "is published, but the downstream consequence is measured — "
        "insufficient documentation drives 63.5% of ambulance improper "
        "payments.",
        "Visibility runs one-way and badly: providers rarely see the chart "
        "(no standard EHR access for transport crews), hospitals rarely "
        "see live trip status, and changes travel by phone call with no "
        "closed loop.",
        "The costliest failures pair a payload with a symptom: necessity/"
        "PCS gaps produce deniable claims, mis-declared acuity sends the "
        "wrong crew, stale bed status produces wall time — three systems, "
        "three owners, one broken trip."),
    why_matters=(
        "This is why 'technology' in IFT means workflow integration, not "
        "an app: the operator that ingests bookings electronically, writes "
        "status back, and closes the documentation loop removes the exact "
        "failure modes that produce both denials and delays — stroke "
        "prenotification's minus-20-minutes shows information moving early "
        "is clinically real."),
    evidence=(
        _E("Insufficient documentation accounts for 63.5% of the 13.2% "
           "ambulance improper-payment rate — the measured cost of the "
           "broken financial payload",
           "GOV", "CMS CERT 2024 supplemental improper-payment data "
           "(re-verify)", ""),
        _E("EMS prenotification cut stroke-transfer door-in-door-out time "
           "by 20.1 minutes (median DIDO 174 min; only 27.3% within 120 "
           "min; n=108,913 transfers)",
           "ACADEMIC", "GWTG-Stroke analysis, JAMA 2023",
           "https://doi.org/10.1001/jama.2023.12739"),
        _E("'A signed physician certification statement (PCS) does not "
           "alone demonstrate that transportation by ground ambulance was "
           "medically necessary' — the MAC position on the financial "
           "payload",
           "GOV", "First Coast Service Options MAC guidance (re-verify)",
           ""),
        _E("'Lack of transparency: no real-time status, no ETA, no "
           "reporting' is a named pain point in the study's health-system "
           "framework",
           "FRAMEWORK", "ift_study health-system pain-point registry", ""),
    ),
    subqs=(
        _S("What information is required to book a trip?",
           "Patient identity plus acuity/tier, equipment needs, origin/"
           "destination and times, payer and necessity documentation — "
           "clinical, logistical and financial in one call."),
        _S("Which information is clinical?",
           "Diagnosis/reason for transfer, acuity tier, monitoring and "
           "equipment (vent, drips, isolation), weight/bariatric needs, "
           "infection status."),
        _S("Which information is logistical?",
           "Origin unit/room, destination facility and bed, requested "
           "time, contacts at both ends, access constraints."),
        _S("Which information is financial?",
           "Payer and plan, the Medicare necessity basis (bed-confined or "
           "contraindication), PCS status, prior authorization "
           "(RSNAT/MA), and the facility-pay flag."),
        _S("Where is information entered?",
           "The EHR (clinical), the transfer-center log or a phone call "
           "(booking), the provider CAD (dispatch), the ePCR (trip), the "
           "billing system (claim) — mostly by re-typing."),
        _S("How many systems are involved?",
           "Typically four to six across two organizations, none natively "
           "connected — the phone is the integration layer."),
        _S("How often is information re-entered?",
           "At nearly every hop — a booking's content is commonly keyed "
           "three to five times end to end."),
        _S("How often is key information missing?",
           skip="Not published — no booking-completeness rate exists for "
                "IFT; the nearest measured proxy is the documentation "
                "share of ambulance improper payments (63.5% of the CERT "
                "error), plus per-account intake logs (diligence "
                "request)."),
        _S("Can providers access relevant patient information "
           "electronically?",
           "Rarely — no standard EHR-to-EMS interface exists in IFT; some "
           "systems grant CCT crews read access; the norm is paper "
           "packets and verbal report."),
        _S("Can hospitals view real-time trip status?",
           "Usually not — status portals and ETA feeds are a "
           "differentiator a few dedicated operators offer; the norm is "
           "calling dispatch."),
        _S("How are changes communicated?",
           "By phone, unit-to-dispatch, with no closed loop — the "
           "mechanism behind stale bed status and crews arriving to "
           "not-ready patients."),
        _S("Which information failures cause the largest delays?",
           "Bed-status staleness (wall time), acuity mis-specification "
           "(wrong crew, re-run trip), and packet gaps at handoff — while "
           "prenotification shows early information saves ~20 minutes per "
           "stroke transfer."),
    ),
)


_PAYMENT = Block(
    "q4-payment", "Payment flow",
    conclusion=(
        "The payer of first resort is the patient's coverage under strict "
        "Medicare rules — 410.40(e) necessity, the PCS, the nearest-"
        "appropriate-facility limit, RSNAT prior authorization for "
        "repetitive trips — and the payer of last resort is the provider "
        "itself (19.7% of transports collect nothing), with the hospital "
        "in between wherever contracts, non-covered destinations or "
        "ordered convenience put it; the gray zone between the three is "
        "the least-governed money in the ecosystem."),
    why_true=(
        "Medicare pays non-emergency ambulance only if the patient is "
        "bed-confined (unable to get up AND unable to ambulate AND unable "
        "to sit in a chair or wheelchair — all three) or other transport "
        "is contraindicated, with a signed PCS; coverage runs only to the "
        "nearest appropriate facility — 'only mileage to the nearest "
        "appropriate facility equipped to treat the patient is covered'.",
        "Repetitive non-emergency trips (3+ round trips in 10 days, or "
        "1+/week for 3+ weeks) require RSNAT prior authorization, and "
        "enforcement bites: the model produced 'a 61% reduction in the "
        "probability of RSNAT use' and 'a 77% reduction in RSNAT "
        "expenditures for a total of $1136 per beneficiary-year' — with "
        "'a 19% annual increase in the probability of emergency dialysis "
        "use' among ESRD beneficiaries.",
        "Error and audit exposure concentrate exactly here: CERT puts "
        "ambulance improper payments at 13.2% / $595.1M (63.5% "
        "insufficient documentation), and OIG found $30.2M paid where the "
        "beneficiary received no Medicare service at origin or "
        "destination in one half-year.",
        "Denied and uncovered trips flow by contract or default: the "
        "provider eats most, hospitals pay for what they order outside "
        "coverage (repatriations, capacity moves), and the patient can "
        "still be balance-billed out-of-network because ground ambulance "
        "is EXCLUDED from the No Surprises Act — the GAPB committee "
        "recommends ending that with cost-sharing capped at the lesser of "
        "$100 or 10%."),
    why_matters=(
        "Contract design is the answer to the gray zone: dedicated "
        "agreements that name who pays for denied, uncovered and wait-time "
        "items convert the least-governed money into priced risk — an "
        "advantage that belongs to whoever brings the paper."),
    evidence=(
        _E("Non-emergency coverage requires bed-confinement (all three "
           "tests) or contraindication plus a PCS; 'only mileage to the "
           "nearest appropriate facility equipped to treat the patient is "
           "covered'",
           "GOV", "42 CFR 410.40(e)/(f); CMS Benefit Policy Manual ch.10 "
           "§10.3", ""),
        _E("RSNAT prior authorization: '61% reduction in the probability "
           "of RSNAT use', '77% reduction in RSNAT expenditures ($1136 "
           "per beneficiary-year)', '19% annual increase in the "
           "probability of emergency dialysis use' (ESRD cohort)",
           "ACADEMIC", "Contreary et al., JAMA Health Forum 2022",
           "https://doi.org/10.1001/jamahealthforum.2022.2093"),
        _E("Ambulance improper payments 13.2% / $595.1M projected; "
           "insufficient documentation 63.5%, medical necessity 27.5%",
           "GOV", "CMS CERT 2024 supplemental improper-payment data "
           "(re-verify)", ""),
        _E("19.7% of transports collect nothing; Medicare + Medicare "
           "Advantage supply 42% of transport revenue",
           "SOURCED", "CMS/RAND GADCS reports via AAA / EMS|MC coverage "
           "(re-verify)",
           "https://ambulance.org/2025/12/09/cms-releases-new-gadcs-report/"),
        _E("Ground ambulance is excluded from the No Surprises Act; the "
           "GAPB advisory committee recommends banning OON balance "
           "billing with patient cost-share capped at the lesser of $100 "
           "or 10%",
           "GOV", "CMS GAPB Advisory Committee report, 2024",
           "https://www.cms.gov/files/document/report-advisory-committee-ground-ambulance-and-patient-billing.pdf"),
    ),
    subqs=(
        _S("Who is initially expected to pay?",
           "The patient's coverage — Medicare AFS, Medicaid, MA, "
           "commercial; Medicare plus MA alone are 42% of transport "
           "revenue."),
        _S("Who is ultimately responsible if the claim is denied?",
           "The provider by default (19.7% of transports collect "
           "nothing), the hospital by contract on facility-responsible "
           "trips, the patient where balance billing survives."),
        _S("When is prior authorization required?",
           "Medicare: only RSNAT repetitive non-emergency trips (3+ round "
           "trips/10 days or weekly for 3+ weeks; an affirmation covers "
           "120 round trips/180 days); MA and Medicaid MCO rules are "
           "plan-specific and common on non-emergency legs."),
        _S("When is medical-necessity documentation required?",
           "Every non-emergency claim: 410.40(e) necessity plus a signed/"
           "dated PCS — obtained in advance and dated within 60 days for "
           "repetitive trips; RN/PA/NP or discharge-planner certification "
           "can substitute on non-repetitive trips."),
        _S("When is the hospital financially responsible?",
           "Trips it orders outside coverage — repatriation, capacity/"
           "decompression moves, convenience, many behavioral and "
           "midnight discharge legs — plus whatever denial risk and "
           "retainer its contract accepts."),
        _S("When can the patient be billed?",
           "Cost-sharing always; out-of-network balance bills remain "
           "lawful for GROUND ambulance (the No Surprises Act excludes "
           "it) except where states ban them — the GAPB committee "
           "recommends a federal ban with a $100-or-10% cap."),
        _S("How does the provider determine the correct payer?",
           "Intake eligibility checks and coordination of benefits at "
           "booking, re-verified at billing — by phone and portal, "
           "because no hospital feed carries coverage data."),
        _S("How are uncovered trips handled?",
           "Quoted to the hospital or patient in advance where the "
           "provider is disciplined (an ABN for Medicare); otherwise run, "
           "denied and written off — a line item inside the 19.7%."),
        _S("How are contractual rates reconciled with payer "
           "reimbursement?",
           "On facility-billed trips the contract rate stands alone; on "
           "payer-billed trips hospital contracts typically never touch "
           "reimbursement — the two ledgers meet only in dedicated deals "
           "with retainers or denial-allocation clauses."),
        _S("Where does financial responsibility remain unclear?",
           "Denied-for-documentation trips, wait time and extra "
           "attendants (not separately payable by Medicare), discharge "
           "legs no payer covers, and any trip a hospital ordered but "
           "never agreed in writing to fund."),
    ),
)


_INCENTIVES = Block(
    "q4-incentives", "Incentive alignment",
    conclusion=(
        "The selector does not pay, the payer gains little from speed, the "
        "hospital gains bed-days it cannot bill the transport against, and "
        "the provider gains nothing from throughput it is not paid for — "
        "every optimization benefit lands one organization away from the "
        "party that must invest, which is why the predictable failures "
        "(slow discharge legs, refused thin-mix trips, shed scheduled "
        "work) persist."),
    why_true=(
        "The party selecting the provider (nurse or transfer center) "
        "neither pays the trip nor holds the contract; the payer captures "
        "little from faster discharge under episode-style payment (the "
        "hospital keeps the length-of-stay saving); the hospital captures "
        "the throughput value but pays directly for only a fraction of "
        "trips.",
        "The trip's price and its throughput value differ by an order of "
        "magnitude — hospital expense per inpatient day runs ~$3,132 "
        "against a $469 Medicare average payment per transport — and "
        "nobody trades between the two ledgers except through the "
        "hospital's direct-pay channel.",
        "Facilities face no cost signal on modality (an over-specified ALS "
        "trip costs the payer, not the requester; no IFT-specific "
        "over-triage rate is published), and providers rationally "
        "deprioritize low-reimbursement trips — RSNAT's squeeze on "
        "dialysis transport was followed by a measured 19% annual rise in "
        "emergency dialysis use among ESRD beneficiaries.",
        "The broker markets show alignment must be engineered: capitated "
        "NEMT brokers are paid to complete trips cheaply, and quality "
        "holds only where states audit and fine — New Jersey fined "
        "Modivcare ~$1.7M, and a Mississippi audit found ~3,000 of "
        ">52,000 monthly trips late or missed, roughly 3x the contractual "
        "limit."),
    why_matters=(
        "Whoever prices throughput into the transport contract — "
        "retainers, dedicated units, bed-day-linked service levels — "
        "captures the order-of-magnitude gap between what trips cost and "
        "what delays cost. That arbitrage is the economic core of the "
        "dedicated model."),
    evidence=(
        _E("Hospital adjusted expense per inpatient day ~$3,132 (2023; "
           "nonprofit $3,288, for-profit $2,529) — an expense proxy, not "
           "marginal cost",
           "SOURCED", "KFF State Health Facts, expenses per inpatient day "
           "(re-verify)", ""),
        _E("Medicare FFS average payment ~$469 per ground transport "
           "($5.3B / 11.3M, 2024) — the trip-price side of the mismatch",
           "DERIVED", "MedPAC Ambulance Payment Basics, Oct 2024",
           "https://www.medpac.gov/wp-content/uploads/2024/10/MedPAC_Payment_Basics_24_ambulance_FINAL_SEC.pdf"),
        _E("'A 19% annual increase in the probability of emergency "
           "dialysis use' among ESRD beneficiaries after RSNAT squeezed "
           "repetitive transport — cost shifts when incentives clash",
           "ACADEMIC", "Contreary et al., JAMA Health Forum 2022",
           "https://doi.org/10.1001/jamahealthforum.2022.2093"),
        _E("NEMT broker enforcement record: NJ fined Modivcare ~$1.7M "
           "(2017-22); GA fined brokers >$1M (2018-20); a Mississippi "
           "audit found ~5.8% of monthly trips late/missed, ~3x the "
           "contractual limit",
           "SOURCED", "State enforcement actions via Mississippi Today / "
           "state records, Sep 2024 (re-verify)", ""),
    ),
    subqs=(
        _S("Does the party selecting the provider pay for the trip?",
           "Almost never — nurses and transfer centers select; payers or "
           "the provider's write-off line pay. The defining misalignment."),
        _S("Does the payer benefit from a faster discharge?",
           "Modestly — under episode-style payment the HOSPITAL keeps the "
           "length-of-stay saving; payers neither see nor manage transport "
           "service levels."),
        _S("Does the hospital benefit financially from reliable "
           "transportation?",
           "Enormously — freed bed-days at ~$3,132/day expense and reduced "
           "boarding — but the benefit sits in throughput accounts no "
           "transport budget ever sees."),
        _S("Does the provider receive any benefit from improving hospital "
           "throughput?",
           "Not under per-trip pricing; only retainers, dedicated-unit "
           "fees or share-of-volume growth translate throughput into "
           "provider revenue."),
        _S("Does the facility have an incentive to request the "
           "lowest-cost modality?",
           "No — the requester bears no modality cost, so conservative "
           "over-specification is rational; no IFT-specific over-triage "
           "rate is published (flagged as a diligence pull)."),
        _S("Does the provider have an incentive to accept "
           "lower-reimbursement trips?",
           "Only relationship preservation — economically no; slow ETAs "
           "and quiet refusals on thin-mix legs are the observable "
           "result."),
        _S("Do brokers have incentives aligned with service quality?",
           "Capitation aligns them with cost, not quality; state OTP "
           "audits and fines (NJ ~$1.7M against Modivcare) are the "
           "counterweight — alignment is enforced, not emergent."),
        _S("Which participant benefits from optimization?",
           "The hospital first (bed-days, boarding relief), the patient "
           "clinically, the payer marginally — the provider only if the "
           "contract shares the gain."),
        _S("Which participant bears the cost of failure?",
           "The reverse order: nursing and flow feel the delays, the "
           "provider eats unpaid trips and wall time, the patient bears "
           "clinical risk — the contract-holder feels nothing directly."),
        _S("Where do misaligned incentives produce predictable service "
           "problems?",
           "Day-end discharge legs (no payer urgency), thin-payer trips "
           "(refusals), shared 911/IFT fleets (scheduled work shed in "
           "surges), and receiver door time (costs the crew, not the "
           "receiver)."),
    ),
)


Q4 = QuestionDef(
    num=4,
    slug="ecosystem",
    title="How does the IFT ecosystem actually work?",
    storyline=(
        "Eleven decisions by six-plus parties across four organizations "
        "move one patient — and the party that feels each failure is never "
        "the party holding contract leverage, so the ecosystem "
        "under-performs by construction, not by accident."),
    visual_key="ecosystem",
    blocks=(_PARTICIPANTS, _HEALTH_SYSTEM, _PROVIDER, _RECEIVING,
            _INFORMATION, _PAYMENT, _INCENTIVES),
)


# ═════════════════════════════════════════════════════════════════════════════
# Question 5 — What operating models do health systems use?
# ═════════════════════════════════════════════════════════════════════════════

_ASSETS = Block(
    "q5-assets", "Asset ownership",
    conclusion=(
        "Vehicle title is the least informative fact about an operating "
        "model: hospitals in the reference footprint own almost no ground "
        "fleet (5 hospital-owned ambulance organization NPIs in all of "
        "Nebraska), and where they do own, they own the narrow high-acuity "
        "slice — so asset maps must never be read as insourcing maps."),
    why_true=(
        "The footprint ownership census is countable: Children's Nebraska "
        "owns a CAMTS-accredited peds/neonatal program ('a fleet of ground "
        "ambulances, a EC 145-C2 helicopter and a PC 12 fixed-wing "
        "aircraft'); CHI Good Samaritan owns Kearney's 911 ground service "
        "plus the AirCare helicopter; Nebraska Medicine, Methodist, "
        "Madonna and Great Plains own nothing a records sweep can find, "
        "and Bryan's StarCare air rides on Air Methods equipment and "
        "pilots.",
        "Ownership varies by modality: systems own the high-acuity/"
        "specialty edge (peds CCT, branded air) and essentially never the "
        "BLS/wheelchair fleet that carries the volume; in outsourced "
        "models the provider owns and finances vehicles, posts and "
        "standard equipment, with hospital-owned specialty kit (isolettes, "
        "balloon pumps) riding along on contracted trucks.",
        "Ownership varies by geography: Iowa's rural default is "
        "hospital-owned (40+ hospital ambulance NPIs) while Nebraska's is "
        "municipal/volunteer plus private (~5 hospital-owned) — two "
        "adjacent states, two different default owners of the same asset.",
        "The classification trap follows: a system holding a few marked "
        "trucks reads 'insourced' on an asset count while outsourcing most "
        "of its mission volume — which is exactly why the framework "
        "classifies on delivered volume."),
    why_matters=(
        "Asset ownership tells a buyer who carries capital risk and what a "
        "displacement would cost; for classification it is a cross-check, "
        "never the axis. Reading trucks as models is the single most "
        "common operating-model error in this market."),
    evidence=(
        _E("NE/IA NPPES sweep: Nebraska 5 hospital-owned ambulance org "
           "NPIs (of 400 captured) vs Iowa 40+ (of 351) — the ownership "
           "default flips at the state line",
           "SOURCED", "CMS NPPES registry sweep, vendored 2026-07-10", ""),
        _E("Children's Nebraska owns a CAMTS-accredited neonatal/"
           "pediatric transport program: ground fleet + EC 145-C2 "
           "helicopter + PC 12 fixed-wing (own transport NPI 1831044759)",
           "SOURCED", "Children's Nebraska transport page, 2026-07-10 "
           "pull (re-verify)",
           "https://www.childrensnebraska.org/providers/specialties/transport-critical-care"),
        _E("CHI Good Samaritan directly operates Kearney's 911 ground "
           "service (city + Buffalo County FD#1 since 1988) and the "
           "AirCare helicopter (Bell 429, flown by Apollo MedFlight)",
           "SOURCED", "CHI Health system pages, 2026-07-10 pull "
           "(re-verify)",
           "https://www.chihealth.com/services/emergency-medicine/good-samaritan-emergency-department/aircare-ambulance-service"),
        _E("Nebraska Medicine, Methodist, Madonna and Great Plains: no "
           "owned ground transport found (recorded as not-found); Bryan's "
           "StarCare air is operated by Air Methods",
           "SOURCED", "System-page research pull 2026-07-10 "
           "(ift_health_systems; re-verify)", ""),
        _E("Classification axis: insourced transport-VOLUME share, not "
           "ambulance-asset ownership — a system can own a few units and "
           "still outsource most IFT",
           "FRAMEWORK", "ift_insourcing four-band classification model",
           ""),
    ),
    subqs=(
        _S("Who owns the vehicles?",
           "The provider, in outsourced models; hospital ownership is rare "
           "and acuity-targeted (Children's peds fleet, CHI's Kearney "
           "units) — 5 hospital-owned ambulance org NPIs in all of NE."),
        _S("Who finances vehicle purchases?",
           "The owner: provider balance sheets (and their sponsors) in "
           "outsourced models, hospital capital budgets in the few "
           "captive programs, municipal budgets for 911 fleets."),
        _S("Who pays for maintenance?",
           "Follows title — the operator; crews-on-hospital-assets "
           "hybrids split it contractually (no ground example found in "
           "the footprint — recorded as not-found)."),
        _S("Who owns stations or deployment locations?",
           "Providers lease their own posts; captive programs garage on "
           "campus; dedicated deals sometimes stage contractor crews "
           "inside hospital facilities."),
        _S("Who owns clinical equipment?",
           "The truck's owner for standard kit; specialty equipment "
           "(isolettes, balloon pumps, ECMO rigs) often belongs to the "
           "hospital team even on a contractor's vehicle."),
        _S("Does vehicle ownership vary by modality?",
           "Sharply — when systems own anything it is the high-acuity/"
           "specialty units; the BLS/wheelchair volume fleet is "
           "essentially always vendor-owned."),
        _S("Does ownership vary by geography?",
           "Yes — Iowa's hospital-owned rural default (40+ NPIs) against "
           "Nebraska's municipal-plus-private default (~5) is the "
           "cleanest adjacent-state contrast in the data."),
    ),
)


_WORKFORCE = Block(
    "q5-workforce", "Workforce ownership",
    conclusion=(
        "Labor is 70.7% of ambulance cost, so whoever employs the crews "
        "owns the operating model in the way that matters — recruiting, "
        "scheduling, credentialing, overtime and vacancy risk — and the "
        "notable hybrid forms (contractor pilots on a system-branded "
        "aircraft; vendor-supplied crews under a system brand) exist "
        "precisely to place that risk deliberately."),
    why_true=(
        "In outsourced models the provider employs drivers, EMTs, "
        "paramedics and dispatchers and absorbs vacancy and overtime "
        "risk; in captive programs the system employs them (CHI Good "
        "Samaritan staffs Kearney's 911; Children's staffs its transport "
        "team); specialty CCT nurses are commonly hospital employees even "
        "when everything else is contracted.",
        "Recruiting and scheduling sit with the employer, but clinical "
        "credentialing is layered — state licensure plus the operator's "
        "medical direction plus hospital-imposed specialty standards by "
        "contract — so a hospital can control clinical standards it does "
        "not employ.",
        "Both cross-ownership hybrids are observable at the specialty "
        "edge: CHI's AirCare is a system helicopter flown by a contractor "
        "(Apollo MedFlight), while Bryan's StarCare brand rides on Air "
        "Methods equipment, pilots and now medical staffing — each is a "
        "deliberate labor-risk allocation, not a taxonomy curiosity.",
        "Workforce is the market's binding constraint: 80%+ of Nebraska "
        "EMS agencies are all-volunteer, only 31% of volunteer agencies "
        "report enough staff, and 28% expect to be unable to operate "
        "within five years — whoever must employ the next decade's crews "
        "carries the sector's hardest risk."),
    why_matters=(
        "In diligence, crew employment tells you where wage inflation, "
        "FLSA exposure (multi-district wage-and-hour suits are the "
        "EMS-rollup signature) and service continuity actually sit — read "
        "the W-2s, not the paint jobs."),
    evidence=(
        _E("Labor (wages + benefits) is 70.7% of ambulance service cost "
           "(up from 69% in the first GADCS cohort)",
           "SOURCED", "CMS/RAND GADCS Year 1-4 appendix (Dec 2025) via "
           "AAA coverage (re-verify)",
           "https://ambulance.org/2025/12/09/cms-releases-new-gadcs-report/"),
        _E("80%+ of Nebraska EMS agencies rely entirely on volunteers; "
           "31% of volunteer agencies report sufficient staff; 28% expect "
           "to be unable to operate within 5 years",
           "GOV", "NE DHHS Statewide EMS Assessment 2023-24 (re-verify)",
           "https://dhhs.ne.gov/OEHS%20Program%20Documents/NE%20Statewide%20EMS%20Assessment%20v2024.pdf"),
        _E("Bryan's StarCare air program is operated by Air Methods — "
           "equipment, pilots, and now medical staffing — under the "
           "system's brand",
           "SOURCED", "Bryan Health system pages / research pull "
           "2026-07-10 (re-verify)", ""),
        _E("Three FLSA wage-and-hour suits across three districts (OH "
           "2020, WI 2023, NE 2024) against one multi-state IFT platform "
           "— the crew-compensation risk pattern of scaling EMS rollups",
           "SOURCED", "Federal dockets (Justia/CourtListener), pulled "
           "2026-07-10", ""),
    ),
    subqs=(
        _S("Who employs drivers, EMTs, paramedics, nurses, and "
           "dispatchers?",
           "The operator of record — the provider in outsourced models, "
           "the system in captive ones; CCT nurses are often hospital "
           "employees riding contracted logistics."),
        _S("Who recruits them?",
           "The employer — and in a shrinking-volunteer state, recruiting "
           "reach is a competitive weapon, not an HR function."),
        _S("Who schedules them?",
           "The employer's dispatch/scheduling; in dedicated contracts "
           "the schedule is built around the hospital's discharge curve — "
           "the visible difference between a partner and a vendor."),
        _S("Who determines compensation?",
           "The employer, in a business where labor is 70.7% of cost — "
           "wage decisions ARE margin decisions."),
        _S("Who manages clinical credentials?",
           "Layered: state licensure, the operator's medical direction, "
           "and hospital-imposed standards by contract for specialty "
           "work."),
        _S("Who absorbs overtime and vacancy risk?",
           "The employer — the core risk transfer in outsourcing; systems "
           "that insource buy exactly this risk back."),
        _S("Does the health system employ management while outsourcing "
           "crews?",
           "The rarer direction — no footprint example was found "
           "(recorded as not-found); the observed hybrids run the other "
           "way."),
        _S("Does the provider employ crews operating "
           "health-system-owned vehicles?",
           "Yes at the specialty edge — CHI's AirCare (system aircraft, "
           "Apollo MedFlight pilots); ground analogs are contract-"
           "staffing deals whose terms are a per-account diligence "
           "request."),
    ),
)


_CONTROL = Block(
    "q5-control", "Operational control",
    conclusion=(
        "Control is a third axis, separable from assets and payroll: "
        "dispatch, prioritization, positioning, staffing depth, protocols "
        "and escalation can each sit with either party — and the observed "
        "spread runs from Mayo (the system controls everything, including "
        "the 911 designation) through CHI (a system transfer center "
        "directs, vendors execute) to open call lists, where nobody "
        "controls anything beyond the next phone call."),
    why_true=(
        "Dispatch and prioritization belong to the provider's dispatcher "
        "in every non-captive model, disciplined only by contract; "
        "transfer centers reclaim the request side (CHI's RNs accept "
        "STEMI/trauma/stroke and expedite transport), and fully insourced "
        "systems fuse the two — Mayo Clinic Ambulance runs ~70 units as "
        "Rochester's sole 911 ALS and Mayo's IFT in one enterprise.",
        "Positioning, staffing levels and surge response are provider "
        "decisions wherever capacity is uncommitted — which is why 'who "
        "adds capacity?' answers 'no one' under trip-by-trip buying, and "
        "why the commitment clause is the contract's core term.",
        "Clinical protocols are the exception to vendor control: medical "
        "direction is the operator's licensure duty, but hospitals impose "
        "specialty protocols contractually (peds, vent, behavioral) — "
        "control without employment.",
        "The immediate-change test separates models cleanly: who can move "
        "a unit NOW — the captive system, a dedicated partner's on-site "
        "leadership, or nobody (the call-list answer)."),
    why_matters=(
        "Control determines whether performance is manageable or merely "
        "observable. Procurement that buys trips gets observation; "
        "procurement that buys control — dedicated units, embedded "
        "dispatch, named escalation — gets management."),
    evidence=(
        _E("Mayo Clinic Ambulance (ex-Gold Cross): ~70 units, sole 911 "
           "ALS plus Mayo IFT in Rochester — fleet, transfer center and "
           "911 designation as one enterprise",
           "SOURCED", "Footprint operator registry (public/company web), "
           "2026-07-10 (re-verify)", ""),
        _E("Allina Health EMS handled ~34,000 interfacility requests in "
           "2024 and sells CCT to non-system facilities — hospital-owned "
           "control at scale",
           "SOURCED", "Footprint operator registry (public/company web), "
           "2026-07-10 (re-verify)", ""),
        _E("CHI's transfer-center RNs accept STEMI/trauma/stroke "
           "transfers directly 'to expedite transportation arrangements' "
           "— system control of the request side without owning trucks",
           "SOURCED", "CHI Health transfer-center page, 2026-07-10 pull "
           "(re-verify)",
           "https://www.chihealth.com/services/transfer-center"),
        _E("Embedded-coordinator outsourcing (Superior at Mount Carmel's "
           "'Home Network') puts the vendor's scheduling staff inside "
           "the hospital workflow — control shared by design",
           "SOURCED", "Footprint operator registry (public/company web), "
           "2026-07-10", ""),
    ),
    subqs=(
        _S("Who controls dispatch?",
           "The provider's dispatcher in every non-captive model; hybrids "
           "embed vendor coordinators at the transfer center (the "
           "Superior/Mount Carmel form); captives fuse dispatch and "
           "transfer center."),
        _S("Who controls trip prioritization?",
           "Whoever dispatches — which is why hospitals on shared 911/IFT "
           "fleets experience surge-day deprioritization they cannot "
           "countermand."),
        _S("Who determines vehicle positioning?",
           "The provider, on its own economics; dedicated contracts buy "
           "positioning (posts at named campuses)."),
        _S("Who determines staffing levels?",
           "The employer/provider against demand it forecasts; a "
           "hospital's only lever is contractual minimums."),
        _S("Who adds capacity?",
           "Under trip-by-trip buying: no one — the market's core "
           "failure. Under dedicated contracts: the provider, against "
           "committed volume that makes the unit financeable."),
        _S("Who manages overflow?",
           "Informal cascades (the second and third names on the list) in "
           "open markets; named backup vendors or mutual aid in mature "
           "ones."),
        _S("Who owns escalation?",
           "Undefined absent a contract; dedicated deals name the ladder "
           "— dispatch supervisor, ops leader, executive sponsor."),
        _S("Who defines clinical protocols?",
           "The operator's medical director as the floor; hospital-"
           "imposed specialty protocols sit above it by contract."),
        _S("Who monitors performance?",
           "The party with the data — the provider; hospitals see "
           "performance only where contracts compel reporting (the "
           "Question 6 governance agenda)."),
        _S("Who can make immediate operational changes?",
           "The captive system, or a dedicated partner's on-site "
           "leadership; a call-list buyer can only redial."),
    ),
)


_CAPACITY = Block(
    "q5-capacity", "Capacity commitment",
    conclusion=(
        "Capacity commitment is the sharpest single discriminator between "
        "models because it is binary in the contract: 911 franchises and "
        "NEMT capitation guarantee coverage as their core term, while most "
        "hospital IFT runs on zero committed units — and everything "
        "hospitals dislike about IFT (unreliable ETAs, surge abandonment, "
        "no recourse) follows from that zero."),
    why_true=(
        "The comparator markets commit: 911 exclusive-operating-area "
        "contracts guarantee jurisdiction coverage against response-time "
        "fractiles (the 8:59-at-90% urban template, with penalty examples "
        "like $5,000 per response beyond 24 minutes), and NEMT brokers "
        "must field adequate networks against on-time standards (Texas's "
        "85% benchmark with capped penalties).",
        "IFT commitments, where they exist, take four known forms — "
        "dedicated units by facility, modality-specific commitments (a "
        "CCT truck), time-boxed dedication (discharge-window coverage), "
        "and guaranteed minimum units with substitution rules — and none "
        "of them appears in the modal call-list relationship; no public "
        "registry documents any hospital IFT commitment in the footprint.",
        "The failure mode differs by commitment: when demand exceeds "
        "COMMITTED capacity the queue is legible (overflow protocol, "
        "credits); when it exceeds UNCOMMITTED capacity the failure is "
        "silent — ETAs stretch, trips are declined, and the queue "
        "re-forms inside the hospital as boarding (Nebraska's statewide "
        "COVID transfer center could confirm only 146 of 234 requested "
        "transfers in Sep 2021 — the same arithmetic at state scale)."),
    why_matters=(
        "The commitment clause is where the buyer's throughput value and "
        "the provider's unit economics meet: a committed unit is "
        "financeable, a call list is not. This is the specific contract "
        "technology the dedicated model imports from 911 and NEMT into "
        "the one market that never adopted it."),
    evidence=(
        _E("Urban 911 contract norm: 8:59 response at the 90% fractile, "
           "with penalty examples — Pasadena TX 8:59/90% (cap 14:59); "
           "Multnomah County penalties below 90%; San Diego/Falck $5,000 "
           "per response beyond 24 minutes",
           "SOURCED", "Municipal EMS contracts + NFPA 1710 norms "
           "(re-verify)", ""),
        _E("Texas Medicaid medical transportation: 85% on-time-pickup "
           "benchmark with a $15,000 penalty cap — committed performance "
           "as a contract term",
           "GOV", "TX HHSC medical transportation program contract terms "
           "(re-verify)", ""),
        _E("No public hospital-by-hospital IFT capacity commitment is "
           "documentable for the footprint systems — the contract-form "
           "gap, recorded as not-found",
           "FRAMEWORK", "2026-07-10 research sweep (dead-end log)", ""),
        _E("Nebraska's statewide COVID-era transfer center confirmed 146 "
           "of 234 requested transfers (Sep 2021) and 113 of 168 (Oct "
           "2021) — demand exceeding placement + transport capacity, "
           "measured once",
           "SOURCED", "Omaha World-Herald / Journal Star, Nov 2021 "
           "(re-verify)", ""),
    ),
    subqs=(
        _S("Is any capacity contractually dedicated?",
           "In most IFT relationships, none — the defining gap against "
           "911 (jurisdiction coverage) and NEMT (network adequacy); "
           "dedicated deals are the exception being sold."),
        _S("Are specific vehicles assigned?",
           "In dedicated contracts yes — named or branded units per "
           "campus; call lists assign nothing."),
        _S("Are specific crews assigned?",
           "Sometimes at the specialty tier (a hospital CCT team pairs "
           "with named crews); the routine book gets whoever the board "
           "shows."),
        _S("Is capacity dedicated by facility, region, modality, or time "
           "period?",
           "All four forms exist — per-campus units, market-level fleets, "
           "a dedicated CCT truck, discharge-window coverage — chosen to "
           "match the demand curve being bought."),
        _S("Is there a guaranteed minimum number of units?",
           skip="Contract/company data — diligence request: minimum-unit "
                "guarantees live in unpublished dedicated contracts; no "
                "public IFT example exists in the footprint record."),
        _S("Is overflow capacity guaranteed?",
           "Almost never in writing — mature deals name a backup cascade "
           "rather than guaranteeing surge units."),
        _S("Can dedicated vehicles be reassigned?",
           "Governed by the contract (dedication windows, substitution "
           "rules) where one exists; on shared 911/IFT fleets, "
           "reassignment to emergencies is unilateral — the surge-"
           "abandonment mechanism."),
        _S("What happens when demand exceeds contracted capacity?",
           "With commitments: a visible queue, an overflow protocol, "
           "credits. Without: silent failure — stretched ETAs, declined "
           "trips, and boarding as the hospital-side queue."),
    ),
)


_FINANCIAL = Block(
    "q5-financial", "Financial structure",
    conclusion=(
        "Follow five risks — vehicle capital, labor, fuel/maintenance, "
        "demand variability, and reimbursement/denial — and the operating "
        "model names itself: trip-priced outsourcing piles all five on "
        "the provider (which prices them back as unreliability), captives "
        "pile all five on the hospital, and the engineered middle — "
        "retainers, dedicated-unit fees, hour-based pricing — allocates "
        "each risk to whoever can carry it cheapest."),
    why_true=(
        "Under per-trip pricing the provider carries everything, "
        "including demand variability it cannot see and denial risk on "
        "documentation half-created by the hospital (19.7% of transports "
        "collect nothing; 63.5% of improper payments are documentation) — "
        "so it defends itself the only ways it can: thin capacity, payer "
        "selection, and slow ETAs on unprofitable legs.",
        "Retainers and dedicated-unit fees swap money for risk: the "
        "hospital pays for readiness — the 911 lesson, since readiness is "
        "why the GADCS all-agency mean cost is $2,673 against $1,147 mean "
        "reimbursement — and the provider commits capacity; observed "
        "pricing bases are per-trip, per-unit-hour, per-dedicated-unit, "
        "and blended trip-plus-retainer.",
        "Reimbursement stays with the biller — the provider in nearly all "
        "models; hospital billing appears only in captive programs — and "
        "denial absorption is contractual: silent in call lists (the "
        "provider eats it), explicit in dedicated paper (named "
        "payer-denial and uncovered-trip clauses).",
        "The financial model drives behavior mechanically: trip-priced "
        "vendors chase dense corridors and commercial mix; retainer-"
        "holding partners staff the discharge curve — you get what the "
        "structure pays for."),
    why_matters=(
        "Diligence should price the risk allocation, not the rate card: "
        "two contracts at identical per-trip rates are different "
        "businesses if one carries a retainer and a denial backstop and "
        "the other carries neither."),
    evidence=(
        _E("GADCS means: cost per transport $2,673 all-agency ($3,127 "
           "governmental / $1,778 private for-profit) vs mean "
           "reimbursement $1,147 — readiness costs dominate the mean",
           "SOURCED", "CMS/RAND GADCS Year 1-2 report via trade coverage "
           "(re-verify)",
           "https://emsmc.com/in-the-news/takeaways-from-the-first-cms-data-collection-report-on-ambulance-services-and-what-we-need-to-do-about-it/"),
        _E("19.7% of transports collect nothing; insufficient "
           "documentation is 63.5% of the ambulance improper-payment "
           "error — the denial risk being allocated",
           "SOURCED", "GADCS Y1-4 appendix + CMS CERT 2024 (re-verify)",
           "https://ambulance.org/2025/12/09/cms-releases-new-gadcs-report/"),
        _E("The study's contracting frame: per-transport rates + "
           "availability/subsidy retainer + exclusivity/first-call + CPI "
           "escalators — 'the contract IS the deal, not the HCPCS code'",
           "FRAMEWORK", "ift_study health-system procurement registry",
           ""),
        _E("Medicare pays base by HCPCS tier plus loaded mileage (A0425); "
           "waiting time and extra attendants are not separately payable "
           "— contract-only revenue",
           "GOV", "CMS Ambulance Fee Schedule / Claims Processing Manual "
           "ch.15", ""),
    ),
    subqs=(
        _S("Who bears vehicle-capital risk?",
           "The fleet owner — providers (and their sponsors) in "
           "outsourced models, the hospital in captives."),
        _S("Who bears labor risk?",
           "The employer — the big one at 70.7% of cost; outsourcing "
           "exists substantially to shed it."),
        _S("Who bears fuel and maintenance risk?",
           "The operator; occasionally indexed back via fuel surcharges "
           "or CPI escalators in contracts."),
        _S("Who bears demand variability?",
           "Unpriced, the provider — which buffers with thin capacity; "
           "retainers move it to the hospital, the party that actually "
           "controls discharge timing."),
        _S("Who receives payer reimbursement?",
           "The billing provider in essentially every model; hospitals "
           "receive it only where they run the captive program under "
           "their own billing."),
        _S("Who absorbs denials?",
           "Default: the provider (inside the 19.7% collect-nothing "
           "share); dedicated contracts increasingly assign "
           "documentation-caused denials to the party that controls the "
           "documentation."),
        _S("Does the health system provide a minimum payment?",
           skip="Contract/company data — diligence request: retainer and "
                "minimum-payment terms are unpublished; the FORM "
                "(availability fee / dedicated-unit fee) is known from "
                "the study's contracting framework."),
        _S("Is payment based on trips, hours, vehicles, or overall "
           "service?",
           "All four exist — per-trip (dominant), per-unit-hour, "
           "per-dedicated-unit, and program/managed-service pricing; "
           "maturity generally moves down that list."),
        _S("How does the financial model influence service behavior?",
           "Directly — per-trip pays for chasing good trips; retainer "
           "plus service levels pays for being there. The difference is "
           "what the hospital experiences as reliability."),
    ),
)


_VARIANTS = Block(
    "q5-variants", "Major operating-model variants",
    conclusion=(
        "Twelve nameable variants reduce to one four-band spectrum — "
        "fully outsourced (0-5% of volume self-run), hybrid mostly-"
        "outsourced (5-50%), hybrid mostly-insourced (50-95%), fully "
        "insourced (95-100%) — with the named variants describing HOW a "
        "system occupies its band; the classification is always made on "
        "delivered transport volume, never on billing or trucks."),
    why_true=(
        "Every band has live footprint exemplars: fully outsourced — "
        "Nebraska Medicine, Methodist, Madonna, Great Plains (no owned "
        "transport found); hybrid mostly-outsourced — CHI (owns Kearney's "
        "911 and AirCare while its Omaha/Lincoln metro book is "
        "outsourced) and the insourced-top metros where systems own CCT "
        "above an outsourced routine book; hybrid mostly-insourced — "
        "Allina-class owned fleets with outsourced residuals; fully "
        "insourced — Mayo, where fleet, transfer center and the 911 "
        "designation are one enterprise.",
        "Dedicated versus non-dedicated outsourcing is a CONTRACT fact "
        "inside the same band — committed units and service levels versus "
        "a shared pool worked trip by trip — and multi-vendor networks "
        "and broker-managed models are procurement overlays on the fully "
        "outsourced band (the broker form lives mostly in Medicaid NEMT, "
        "under statutory brokerage authority).",
        "The mixed-asset variants are real but acuity-targeted: hospital-"
        "owned assets with outsourced operations (CHI's AirCare flown by "
        "Apollo MedFlight) and vendor assets under system brand (Bryan's "
        "StarCare on Air Methods equipment, pilots and staffing); hybrids "
        "by modality are the NORM (keep peds/CCT, outsource BLS volume — "
        "the Children's carve-out), while by-geography (CHI: own Kearney, "
        "outsource Omaha) and by-time-of-day (discharge-window "
        "dedication) hybrids are engineered variants."),
    why_matters=(
        "Precise naming prevents the classic mis-read — calling a "
        "CCT-owning system 'insourced' — and tells an entrant what it is "
        "actually competing against in each account: a contract, a "
        "fleet, or a habit."),
    evidence=(
        _E("The four-band spectrum: fully outsourced 0-5%, hybrid mostly-"
           "outsourced 5-50%, hybrid mostly-insourced 50-95%, fully "
           "insourced 95-100% of delivered transport volume self-run",
           "FRAMEWORK", "ift_insourcing classification model (volume-"
           "share bands)", ""),
        _E("Footprint EMS posture map: Children's owns a CAMTS peds "
           "fleet; CHI Good Samaritan owns Kearney 911 + AirCare; Bryan "
           "outsources air to Air Methods; Nebraska Medicine, Methodist, "
           "Madonna and Great Plains own nothing found",
           "SOURCED", "System-page research pull 2026-07-10 "
           "(ift_health_systems; re-verify)", ""),
        _E("Insourced-heavy reads: Mayo Clinic Ambulance (~70 units, "
           "sole 911 ALS + Mayo IFT); Allina Health EMS (~34,000 "
           "interfacility requests/2024, sells CCT outward)",
           "SOURCED", "Footprint operator registry (public/company web), "
           "2026-07-10 (re-verify)", ""),
        _E("Medicaid NEMT brokerage: states may contract capitated "
           "brokers who authorize, assign and subcontract provider "
           "networks (SSA 1902(a)(70); consolidated guidance SMD 23-006)",
           "GOV", "42 CFR 440.170 / CMS SMD 23-006", ""),
    ),
    subqs=(
        _S("What defines a fully insourced model?",
           "The system self-runs >~95% of IFT volume with its own units, "
           "crews and dispatch — transport is a department (Mayo the "
           "archetype)."),
        _S("What defines a fully outsourced model?",
           "<~5% self-run — every leg contracted out (Nebraska Medicine, "
           "Methodist, Madonna, Great Plains in the footprint record)."),
        _S("What defines dedicated outsourcing?",
           "Outsourced volume served by contractually committed units/"
           "crews with service levels — capacity reserved, not "
           "requested."),
        _S("What defines non-dedicated outsourcing?",
           "Outsourced volume served from the vendor's shared pool, trip "
           "by trip — first-call habit with no commitments; the modal "
           "form."),
        _S("What defines a multi-vendor network?",
           "A managed panel — primary plus backups, or per-modality/"
           "per-facility assignments — with allocation rules; procurement "
           "discipline layered over shared pools."),
        _S("What defines a broker-managed model?",
           "An intermediary authorizes, assigns and pays subcontracted "
           "providers under capitation or per-trip — the NEMT statutory "
           "form; rare for acute IFT."),
        _S("What defines a joint venture?",
           "Shared ownership of the operator between system and provider "
           "— no footprint example found (recorded as not-found; the "
           "adjacent observed form is the public-utility model)."),
        _S("What defines hospital-owned assets with outsourced "
           "operations?",
           "System holds title/brand, a contractor operates — CHI's "
           "AirCare: a system helicopter flown by Apollo MedFlight."),
        _S("What defines outsourced assets with hospital-controlled "
           "dispatch?",
           "A vendor fleet steered by the system's transfer center or "
           "dispatch — the control-without-capital form dedicated deals "
           "approximate."),
        _S("What defines a hybrid model by modality?",
           "Keep peds/neonatal/CCT, outsource the BLS/ALS volume — the "
           "single most common hybrid (the Children's carve-out; the "
           "insourced-top metros)."),
        _S("What defines a hybrid model by geography?",
           "Own where you are the anchor, outsource elsewhere — CHI "
           "operates in Kearney and outsources in Omaha/Lincoln."),
        _S("What defines a hybrid model by time of day?",
           "Dedicated discharge-window coverage with call-list nights "
           "and weekends — engineered where demand is curve-shaped."),
    ),
)


_PREVALENCE = Block(
    "q5-prevalence", "Penetration and prevalence",
    conclusion=(
        "No national census of hospital transport operating models "
        "exists. The honest prevalence evidence is (a) a 20-metro "
        "footprint classification — 11 metros read fully outsourced, 7 "
        "hybrid mostly-outsourced, 2 hybrid mostly-insourced, 0 fully "
        "insourced by delivered volume; (b) the NPPES ownership contrast "
        "(Iowa 40+ hospital-owned ambulance NPIs vs Nebraska ~5); and "
        "(c) directional correlates — insourcing concentrates where "
        "systems are large, academic and dense, and outsourcing is the "
        "default everywhere else."),
    why_true=(
        "The computable read: mapping each footprint metro's structural "
        "archetype onto the volume bands yields 11 / 7 / 2 / 0 across 20 "
        "metros — outsourced-leaning in 18 of 20 — a stated-scaffold "
        "classification over public/company-web operator facts, not a "
        "survey.",
        "Size, academic status and transfer volume correlate in the "
        "expected direction inside the same data: the mostly-insourced "
        "metros are exactly the large-academic referral magnets (Twin "
        "Cities, Rochester), while rural and community markets read "
        "outsourced or municipal — but n=20 metros is a footprint, not "
        "the nation.",
        "Local supply matters as much as system traits: Iowa hospitals "
        "own ambulances (40+ NPIs) largely because rural private and "
        "municipal supply is absent; Nebraska hospitals don't (~5) "
        "because volunteer squads and privates exist — availability, not "
        "philosophy, sets the default.",
        "Trend is uninstrumented; the observable signals are single "
        "events pointing both ways — Wesley/HCA flipped ~77% of county "
        "interfacility volume (~4,873 trips/2020) to a private in 2022, "
        "while volunteer collapse pushes some rural hospitals toward "
        "reluctant self-operation."),
    why_matters=(
        "Any national percentage anyone quotes for 'hospitals that "
        "insource transport' is invented. Underwriting should classify "
        "account by account on delivered volume and treat market-level "
        "prevalence as a mapping exercise per geography — the way the "
        "footprint read was actually built."),
    evidence=(
        _E("Footprint band counts across 20 metros: fully outsourced 11, "
           "hybrid mostly-outsourced 7, hybrid mostly-insourced 2, fully "
           "insourced 0 — computed from the archetype-to-band mapping",
           "FRAMEWORK", "ift_insourcing.market_insourcing() over the "
           "ift_geo registry, 2026-07-10", ""),
        _E("Iowa: 40+ hospital-owned ambulance org NPIs (dominant rural "
           "model) vs ~5 in Nebraska — the regional prevalence signal "
           "that IS measured",
           "SOURCED", "CMS NPPES registry sweep, vendored 2026-07-10", ""),
        _E("Wesley/HCA moved ~77% of Sedgwick County interfacility "
           "volume (~4,873 transports/2020) to AMR in 2022 — an "
           "outsourcing flip, measured once",
           "SOURCED", "Footprint registry (public/company web + local "
           "records), 2026-07-10 (re-verify)", ""),
        _E("No national operating-model census exists for hospital "
           "transport — recorded as not-found; a survey or AHA-annual-"
           "survey supplement pull is the only route to one",
           "FRAMEWORK", "2026-07-10 research sweep (dead-end log)", ""),
    ),
    subqs=(
        _S("How frequently does each model appear?",
           "No national census exists; in the 20-metro footprint "
           "classification: fully outsourced 11, hybrid mostly-outsourced "
           "7, hybrid mostly-insourced 2, fully insourced 0 — "
           "outsourced-leaning in 18 of 20."),
        _S("How does model choice vary by health-system size?",
           "Directionally, insourcing rises with size (fleet fixed costs "
           "need volume) — the insourced-heavy metros are all "
           "large-system markets; no national size-stratified data "
           "exists."),
        _S("How does it vary by hospital count?",
           "Multi-hospital systems gain the most from captive intra-"
           "system lanes, and the big captive programs (Allina, Mayo) "
           "sit atop exactly such networks — directional, not "
           "quantified."),
        _S("How does it vary by transfer volume?",
           "Volume is the economic gate — fixed dispatch and fleet costs "
           "amortize only over a dense book; high-transfer referral "
           "magnets are the insourcers."),
        _S("How does it vary by urban versus rural location?",
           "Two rural defaults, not one: hospital-owned where no supply "
           "exists (rural Iowa), municipal/volunteer where it does "
           "(rural Nebraska); urban systems default outsourced with "
           "acuity carve-outs."),
        _S("How does it vary by academic versus community status?",
           "The insourced examples skew academic/referral (Mayo, the "
           "academic Twin Cities systems, CCT-owning quaternaries); "
           "community systems mostly outsource — directional, not "
           "surveyed."),
        _S("How does it vary by nonprofit versus for-profit ownership?",
           "The visible signal runs through national vendor "
           "relationships — HCA pre-commits volume to GMR (the Wesley "
           "flip) — for-profits buy scale contracts; no ownership-"
           "stratified census exists."),
        _S("How does it vary based on local provider availability?",
           "Decisively — the Iowa-vs-Nebraska NPI contrast (40+ vs ~5 "
           "hospital-owned) is availability-driven; where a credible "
           "private exists, hospitals outsource."),
        _S("Which models are growing?",
           skip="Not published — requires a survey/AHA-supplement pull; "
                "single events point both ways (the Wesley/HCA "
                "outsourcing flip vs volunteer collapse pushing rural "
                "self-operation)."),
        _S("Which models appear to be declining?",
           "Not published as a trend — the one measured contraction is "
           "the volunteer-dependent municipal supply layer (80%+ of NE "
           "agencies all-volunteer and waning), which forces its "
           "hospital customers toward contracted or owned capacity."),
        _S("How should incomplete or uncertain classifications be "
           "handled?",
           "Band on delivered volume with an explicit range; treat "
           "billing-based reads as ceilings (a system NPI on the claim "
           "proves who billed, not who ran the truck); record not-found "
           "as not-found."),
    ),
)


_SELECTION = Block(
    "q5-selection", "Model-selection logic",
    conclusion=(
        "Model choice is arithmetic plus trauma: insourcing clears only "
        "at referral-magnet volume (fleet, 24/7 crews, dispatch and an "
        "ambulance revenue cycle are step costs), density and management "
        "capability gate it, and systems actually change models on "
        "triggering events — a failure spike, an acquisition, a vendor "
        "exit — not on spreadsheets."),
    why_true=(
        "The arithmetic: mean cost per transport is $2,673 all-agency — "
        "$3,127 governmental versus $1,778 private for-profit — with "
        "labor at 70.7%; a sub-scale hospital fleet buys the governmental "
        "cost curve, and MedPAC's strong inverse volume-cost relationship "
        "is the whole insourcing argument in one line: without referral-"
        "magnet density, self-operation is the expensive way to get "
        "worse service.",
        "The capability list stops more systems than the capital: EMS "
        "dispatch and posting, medical direction, credentialing, fleet "
        "operations, crew recruiting in the sector's scarcest labor "
        "market, and an ambulance revenue cycle — a parallel operating "
        "company, not a department.",
        "Rational large-scale outsourcing exists: transport is non-core, "
        "capital is contested (CommonSpirit posted a $225M FY2025 "
        "operating loss — asset-light beats fleet ownership under margin "
        "pressure), and partial retention persists only where acuity "
        "control is non-negotiable (peds/CCT) or a unit is a community "
        "911 obligation (CHI Kearney).",
        "Change arrives by event, and different facilities rationally run "
        "different models: CHI owns in Kearney and outsources in Omaha; "
        "the observed triggers are system M&A (HCA-Wesley to AMR), REH "
        "conversions — which keep no inpatient beds, so every admission "
        "becomes a transfer — affiliation waves converting independent "
        "vendor decisions into system ones, and vendor failures."),
    why_matters=(
        "Selection logic is a targeting model for an operator: sell "
        "dedicated capacity to high-volume outsourcers with no captive "
        "fleet and a recent failure memory; do not try to displace "
        "captives; watch trigger events (M&A, REH conversions, vendor "
        "exits) as the moments models actually change."),
    evidence=(
        _E("GADCS mean cost per transport: $2,673 all agencies, $3,127 "
           "governmental, $1,778 private for-profit; labor 70.7% of cost",
           "SOURCED", "CMS/RAND GADCS reports via trade coverage "
           "(re-verify)",
           "https://ambulance.org/2025/12/09/cms-releases-new-gadcs-report/"),
        _E("Strong inverse relationship between ambulance response volume "
           "and cost per response — the scale gate on insourcing",
           "SOURCED", "MedPAC assessment of GADCS data, Dec 2025",
           "https://www.medpac.gov/wp-content/uploads/2025/01/Tab-M-Ambulance-Dec-2025.pdf"),
        _E("CommonSpirit FY2025 operating loss $225M (improved from $875M "
           "FY2024) — the capital-allocation pressure that favors "
           "asset-light transport",
           "SOURCED", "CommonSpirit FY2025 results release (re-verify)",
           "https://www.commonspirit.org/news-articles/commonspirit-health-releases-fy2025-year-end-results"),
        _E("REH conversions: 40-50 since Jan 2023, nearly half in "
           "KS/TX/NE/OK; REHs keep no inpatient beds and 'must establish "
           "transfer agreements' — every admission becomes an IFT",
           "ACADEMIC", "J Rural Health 2026 (REH adaptation study)",
           "https://doi.org/10.1111/jrh.70112"),
    ),
    subqs=(
        _S("At what volume does insourcing become economically viable?",
           "No published threshold — the observable bar is referral-"
           "magnet density (Mayo ~70 units; Allina ~34,000 interfacility "
           "requests/yr); sub-scale fleets buy the governmental cost "
           "curve ($3,127 vs $1,778 per transport)."),
        _S("What level of local density is required?",
           "Enough to chain trips and hold unit-hour utilization above "
           "the 911 band — MedPAC's inverse volume-cost curve is the "
           "constraint stated in one sentence."),
        _S("What management capabilities are needed?",
           "EMS dispatch/posting, medical direction, credentialing, "
           "fleet operations, and an ambulance revenue cycle — a "
           "parallel operating company, not a hospital department."),
        _S("What capital is required?",
           "Vehicles, equipment, stations/posts, a CAD + ePCR stack, and "
           "working capital for a payer-billing cycle — bid against a "
           "contested hospital capital budget."),
        _S("What labor challenges arise?",
           "Recruiting EMTs/paramedics from a shrinking pool (80%+ of NE "
           "agencies all-volunteer and waning), 24/7 scheduling, and "
           "wage competition where labor is 70.7% of cost."),
        _S("Why might a health system outsource even at large scale?",
           "Non-core focus, capital allocation under margin pressure "
           "(CommonSpirit's FY2025 loss), risk transfer, and the "
           "existence of a credible dedicated partner — HCA outsources "
           "system-wide by design."),
        _S("Why might a health system retain part of the operation "
           "internally?",
           "Acuity control (peds/neonatal/CCT — the Children's "
           "carve-out), community 911 obligations (CHI Kearney), brand, "
           "or a sunk program that works."),
        _S("Why might different facilities use different models?",
           "Local supply and history differ by market — CHI owns in "
           "Kearney and outsources in Omaha; the model is a market "
           "decision wearing a system badge."),
        _S("What events trigger a change in model?",
           "Ownership and vendor events: system M&A (HCA-Wesley → AMR), "
           "vendor failure/exit, REH conversion (admissions become "
           "transfers), affiliation waves, contract expiries — rarely a "
           "standalone study."),
        _S("What failures cause health systems to reconsider their "
           "current structure?",
           "Boarding and discharge-delay escalation to the C-suite, a "
           "sentinel event on a delayed transfer, surge abandonment by a "
           "shared-fleet vendor, and denial disputes — pain first, "
           "process second."),
        _S("What conditions favor dedicated outsourcing?",
           "Forecastable curve-shaped demand, no captive fleet, a "
           "fragmented-vendor history, and board-visible throughput cost "
           "— the profile of the footprint's fully outsourced anchor "
           "systems."),
    ),
)


Q5 = QuestionDef(
    num=5,
    slug="models",
    title="What operating models do health systems use?",
    storyline=(
        "Operating models are a spectrum measured by how the service is "
        "actually delivered and controlled — delivered transport volume, "
        "never billing or trucks: most systems own at most a high-acuity "
        "sliver and outsource the routine book, which is exactly the "
        "addressable market."),
    visual_key="spectrum",
    blocks=(_ASSETS, _WORKFORCE, _CONTROL, _CAPACITY, _FINANCIAL,
            _VARIANTS, _PREVALENCE, _SELECTION),
)


# ═════════════════════════════════════════════════════════════════════════════
# Question 6 — How do health systems procure and manage IFT?
# ═════════════════════════════════════════════════════════════════════════════

_PROC_OWNERSHIP = Block(
    "q6-ownership", "Procurement ownership",
    conclusion=(
        "The formal owner is supply chain, the requirements owner is "
        "nursing and case management, the budget is nobody's — spend "
        "hides in unit cost centers and provider write-offs — and a "
        "single accountable executive for the transport program is the "
        "exception: the ownership diffusion Question 1 diagnosed is the "
        "root cause of the contract-form gap this question documents."),
    why_true=(
        "In centralized systems, purchased services run through system "
        "supply chain, yet transport routinely slips through as a "
        "facility-level purchase — too small for sourcing attention, too "
        "clinical for commodity treatment; 70% of US hospitals now sit "
        "inside systems, so the centralization MACHINERY exists even "
        "where transport never enters it.",
        "Requirements are written, when written at all, by non-buyers: "
        "transfer-center leaders and case management know the service "
        "levels that matter, but RFPs issue from sourcing staff a step "
        "removed — clinical users enter as evaluators at best.",
        "Individual hospitals contract independently even inside systems "
        "— the footprint shows CHI facilities steering CHI-preferred "
        "vendors while for-profit entrants and independents in the same "
        "cities contract per-relationship — and no documented footprint "
        "system names one executive who owns transport end to end "
        "(recorded as not-found).",
        "Classification predicts the failure mode: managed as a clinical "
        "service, transport gets protocols without contracts; as a "
        "logistics service, contracts without clinical voice; as a "
        "generic purchased service, neither — mature systems build a "
        "hybrid owner under capacity/throughput leadership because it is "
        "genuinely all three."),
    why_matters=(
        "'Who owns this decision?' is the first qualification question in "
        "any transport sale: a system that cannot name an owner cannot "
        "execute a dedicated deal — and creating that owner (an executive "
        "sponsor plus a governance table) is part of what the partner "
        "sells."),
    evidence=(
        _E("70% of non-federal general acute hospitals are system-"
           "affiliated (FY2024: 3,567 of 5,121) — the centralization "
           "machinery exists; transport rarely enters it",
           "SOURCED", "AHA Fast Facts 2026 / MedPAC ch.15 series "
           "(re-verify)",
           "https://www.aha.org/system/files/media/file/2026/02/Fast-Facts-on-US-Hospitals-2026.pdf"),
        _E("Fragmented contracting inside one market: CHI facilities "
           "steer CHI-preferred vendors while for-profits and "
           "independents contract per-relationship (Grand Island / "
           "Kearney / Hastings)",
           "SOURCED", "Footprint registry (public/company web), "
           "2026-07-10", ""),
        _E("No footprint system names a single accountable transport "
           "executive in any public document — recorded as not-found, "
           "itself evidence of absent ownership",
           "FRAMEWORK", "2026-07-10 research sweep (dead-end log)", ""),
        _E("The study's procurement frame: vendor structure, partnership "
           "model, contractual relationship and operational workflow are "
           "the four axes a system must staff to buy transport well",
           "FRAMEWORK", "ift_study health-system procurement registry",
           ""),
    ),
    subqs=(
        _S("Who formally owns the procurement decision?",
           "Supply chain / purchased services on paper; in practice, "
           "facility operations for the many accounts below sourcing's "
           "radar."),
        _S("Who defines operational requirements?",
           "The users — transfer center, case management, nursing — "
           "usually informally; requirement quality depends on whether "
           "they ever reach the RFP."),
        _S("Who controls the budget?",
           "Typically no one: spend fragments across unit cost centers, "
           "facility invoices and provider write-offs — few systems can "
           "state an all-in number (a standing diligence request)."),
        _S("Who approves the final vendor?",
           "Supply chain with facility and clinical sign-off above "
           "contract-size thresholds; small accounts are approved by "
           "whoever signs the letter."),
        _S("Is procurement centralized?",
           "Increasingly possible — 70% of hospitals sit in systems — "
           "but transport lags: system transfer centers coexist with "
           "facility-level vendor habits."),
        _S("Can individual hospitals contract independently?",
           "Routinely — the footprint's per-relationship contracting "
           "(CHI-steered and independent vendors in the same cities) is "
           "the observed norm."),
        _S("Are clinical users included in the decision?",
           "At evaluation, sometimes; at requirement-writing, rarely — "
           "the gap that produces price-weighted RFPs for a reliability "
           "product."),
        _S("Is transportation managed as a clinical service, logistical "
           "service, or purchased service?",
           "Whichever department inherited it; it is genuinely all "
           "three, and the misclassification predicts the failure mode "
           "(protocols without contracts, or contracts without clinical "
           "voice)."),
        _S("Is there one executive accountable for the full program?",
           "Almost never — no documented footprint system names one "
           "(not-found); appointing one is the first observable marker "
           "of procurement maturity."),
    ),
)


_VENDOR_CONFIG = Block(
    "q6-vendors", "Current vendor configuration",
    conclusion=(
        "The modal configuration is an unranked call list with a habitual "
        "first call; the engineered configurations — an embedded exclusive "
        "partner, primary-plus-backups, per-modality or per-geography "
        "assignment, broker management — all exist but are the minority; "
        "volume is allocated by habit and answer speed, poor performance "
        "is handled by silent list demotion, and facilities bypass "
        "'preferred' structures the moment a patient waits."),
    why_true=(
        "The full configuration spectrum is observable in one operator "
        "footprint: a single embedded partner (Superior inside Mount "
        "Carmel's workflow with embedded scheduling coordinators; AMR "
        "co-branded with UofL across 8 units and 9 facilities), contested "
        "two-horse lists (Lincoln: AmeriPro vs MMT), fragmented pools "
        "(Milwaukee's Bell/Curtis/Paratech), modality splits (peds "
        "insourced, adult outsourced), and county-exclusive rural "
        "contracts (AmeriPro's seven named Nebraska counties; Frontier's "
        "five-year Fremont County 911+IFT award).",
        "Brokers manage the Medicaid benefit layer — capitated statewide "
        "intermediaries subcontracting networks — but rarely acute IFT; "
        "the broker sits beside hospital transport, not inside it.",
        "Allocation and discipline are informal: no documented IFT "
        "account publishes volume-allocation rules or a termination-for-"
        "performance event; the observable discipline mechanism is the "
        "quiet re-ordering of the call list, invisible to procurement.",
        "Bypass is structural: any nurse can dial the second name; "
        "preferred-provider letters govern nothing until booking is "
        "centralized in a transfer center or the preferred partner is "
        "reliably better."),
    why_matters=(
        "The configuration audit is cheap diligence gold: pull one "
        "quarter of invoices and count the vendors actually used against "
        "the stated structure — the gap measures both the governance "
        "vacuum and the consolidation opportunity."),
    evidence=(
        _E("Embedded configurations: Superior at Mount Carmel ('Home "
           "Network', embedded scheduling coordinators); AMR co-branded "
           "preferred provider with UofL — 8 units, 9 facilities, "
           "embedded coordinators",
           "SOURCED", "Footprint registry (public/company web), "
           "2026-07-10", ""),
        _E("AmeriPro's stated Nebraska counties after acquiring Priority "
           "Medical Transport: Lincoln, Red Willow, Buffalo, Dawson, "
           "Adams, Dodge and Platte",
           "SOURCED", "AmeriPro press release, Feb 2025",
           "https://www.prnewswire.com/news-releases/ameripro-health-acquires-priority-medical-transport-and-expands-midwest-presence-302372373.html"),
        _E("County-contract template: Frontier Ambulance (Priority "
           "brand) holds Fremont County's five-year combined 911+IFT "
           "contract — the exclusive-award form IFT could copy",
           "SOURCED", "Footprint registry (public/company web), "
           "2026-07-10 (re-verify)", ""),
        _E("Medicaid NEMT runs through state brokerage authority — "
           "brokers authorize, run call centers, assign trips and "
           "subcontract networks, commonly capitated",
           "GOV", "SSA 1902(a)(70) / CMS SMD 23-006", ""),
    ),
    subqs=(
        _S("How many providers does the health system use?",
           "Stated: one or two preferred. Actual: whatever the call list "
           "reached — an invoice pull routinely finds more vendors than "
           "procurement can name."),
        _S("Is there one exclusive provider?",
           "Rarely in writing — IFT exclusivity is usually de facto "
           "(embedded workflow, the Mount Carmel/Superior form) rather "
           "than contractual."),
        _S("Is there a primary provider and backups?",
           "The commonest engineered form: first-call plus a cascade — "
           "whose order is folklore unless documented."),
        _S("Are providers assigned by facility?",
           "Often — different campuses inside one system keep different "
           "habits (the footprint's per-relationship contracting)."),
        _S("Are providers assigned by modality?",
           "Yes where acuity splits: peds/CCT to one operator or kept "
           "in-house, routine BLS/ALS to others — the most defensible "
           "assignment logic."),
        _S("Are providers assigned by geography?",
           "In multi-market systems yes — county-exclusive rural "
           "contracts and metro pools; CHI effectively runs different "
           "answers in Kearney and Omaha."),
        _S("Is there an open call list?",
           "The modal configuration — unranked names on a unit "
           "clipboard; the call list IS the incumbent competitor in most "
           "sales."),
        _S("Is a broker involved?",
           "For Medicaid NEMT legs, usually (statewide capitated "
           "brokers); for acute IFT, rarely — some discharge rides route "
           "through the patient's plan broker while ambulance IFT is "
           "bought directly."),
        _S("How is volume allocated?",
           "By habit, answer speed and ETA — not by rule; embedded "
           "coordinators and transfer-center booking are how allocation "
           "becomes governable."),
        _S("How is poor performance handled?",
           "Silent list demotion, unit-level grumbling, occasional "
           "escalation emails — contractual remedies are rare because "
           "contracts are."),
        _S("Can facilities bypass the preferred structure?",
           "Yes, by dialing — bypass ends only when booking centralizes "
           "(a transfer center that owns transport) or the preferred "
           "partner is reliably better."),
    ),
)


_TRIGGER = Block(
    "q6-trigger", "Sourcing trigger",
    conclusion=(
        "IFT sourcing is event-driven, not calendar-driven: the RFP — "
        "when one happens at all — follows a service crisis, a cost or "
        "denial dispute, system growth or M&A, a standardization push, or "
        "an insource/outsource study; contract expiration is a weak "
        "trigger because so much volume runs without a contract to "
        "expire."),
    why_true=(
        "The strongest trigger is escalated service failure — boarding "
        "and discharge delays reaching the C-suite — followed by M&A and "
        "affiliation events that force vendor rationalization: the "
        "footprint's live wave (Methodist-Fremont 2018, Bryan-Kearney "
        "Regional 2022, Bryan-Pender 2025, UnityPoint-MercyOne Siouxland "
        "2025) converts independent transfer and vendor decisions into "
        "system-directed ones.",
        "Growth and service-line events create new lanes needing "
        "coverage: CHI's Council Bluffs L&D closure (announced "
        "2026-07-10) re-routes obstetric volume across the river — new "
        "recurring maternal transfer legs bought by somebody.",
        "Standardization sweeps arrive with margin pressure (system "
        "purchased-services reviews), and insource/outsource analyses "
        "run at the extremes — the Wesley/HCA decision that moved ~77% "
        "of county interfacility volume to AMR is the executed example.",
        "There is no observed formal reassessment cadence for IFT "
        "anywhere in the public record — against 911's statutory rebids "
        "and NEMT's 3-5-year state contract cycles — reassessment "
        "happens when pain does."),
    why_matters=(
        "Sellers should map trigger events, not RFP calendars: "
        "affiliation announcements, REH conversions, service-line "
        "closures and vendor exits are the lead indicators that a "
        "sourcing window is opening."),
    evidence=(
        _E("Footprint consolidation events 2018-2025: Methodist-Fremont "
           "(50-yr lease), Bryan-Kearney Regional (Jan 2022), "
           "Bryan-Pender affiliation (Jun 2025), UnityPoint-MercyOne "
           "Siouxland (Sep 2025)",
           "SOURCED", "System press releases + trade coverage "
           "(re-verify)",
           "https://www.unitypoint.org/news-and-articles/press-releases/unitypoint-health-acquires-mercyone-siouxland-medical-center"),
        _E("CHI Mercy Council Bluffs L&D closure announced 2026-07-10 "
           "(deliveries end ~Sep 2026) — OB volume re-routes to Omaha, "
           "creating recurring maternal transfer lanes",
           "SOURCED", "Local press coverage, 2026-07-10 (re-verify)",
           "https://www.wowt.com/2026/07/10/chi-health-ending-labor-delivery-care-council-bluffs-hospital/"),
        _E("Wesley/HCA moved ~77% of Sedgwick County interfacility "
           "transports (~4,873/2020) to AMR in March 2022 — an executed "
           "outsourcing analysis",
           "SOURCED", "Footprint registry (public/company web + local "
           "records), 2026-07-10 (re-verify)", ""),
        _E("The comparator cadences: California EOAs are awarded through "
           "a competitive process (H&S 1797.224); state NEMT broker "
           "contracts run 3-5-year cycles",
           "GOV", "CA Health & Safety Code 1797.224; state Medicaid "
           "contract records (re-verify)", ""),
    ),
    subqs=(
        _S("What causes the health system to run an RFP?",
           "An event — escalated service failure, M&A or "
           "standardization, a new campus, a vendor exit — rarely a "
           "scheduled cycle."),
        _S("Is the process triggered by contract expiration?",
           "Weakly — much volume has no contract to expire; where "
           "contracts exist they quietly renew unless something else "
           "hurts."),
        _S("Is it triggered by poor service?",
           "The #1 trigger — transport reaches sourcing when boarding "
           "and discharge delays reach the C-suite."),
        _S("Is it triggered by rising cost?",
           "Secondarily — visible invoice growth or denial disputes on "
           "facility-billed trips; the larger costs (bed-days) are "
           "invisible to the transport budget."),
        _S("Is it triggered by system growth?",
           "Yes — new facilities, service-line consolidation (an L&D "
           "closure creating recurring maternal lanes), and referral-"
           "network expansion all create coverage gaps."),
        _S("Is it triggered by standardization efforts?",
           "Periodically — purchased-services rationalization under "
           "margin pressure sweeps transport into system RFPs."),
        _S("Is it triggered by an acquisition?",
           "Reliably — affiliation and M&A events force vendor "
           "rationalization across the combined footprint (the observed "
           "NE/IA wave)."),
        _S("Is it triggered by insourcing or outsourcing analysis?",
           "At the extremes — a build-a-fleet study or a divest "
           "decision; the Wesley/HCA flip is the executed example."),
        _S("How frequently is the model formally reassessed?",
           "No published cadence exists for IFT — against 911's "
           "statutory rebids and NEMT's 3-5-year state cycles, IFT is "
           "reassessed when it hurts."),
    ),
)


_EVALUATION = Block(
    "q6-evaluation", "Evaluation criteria",
    conclusion=(
        "A competent IFT evaluation tests seven capabilities — fleet "
        "capacity, local density, workforce, clinical tiers, technology, "
        "track record, financial stability — plus two meta-tests naive "
        "RFPs skip: normalizing price across non-equivalent service "
        "models (a per-trip rate against a retainer-plus-rate bid is not "
        "a comparison) and verifying capacity claims as staffed "
        "unit-hours rather than vehicle counts."),
    why_true=(
        "Capacity must be tested as staffed unit-hours by tier and post — "
        "a vehicle without a credentialed crew is scrap on the lot in a "
        "market where labor is 70.7% of cost and the volunteer pipeline "
        "is collapsing; workforce evaluation means retention, wage "
        "posture and recruiting pipeline, not headcount claims.",
        "Density and track record are checkable from outside: post "
        "locations and NPI estates, reference calls to transfer-center "
        "leaders (not procurement contacts), and any measurable on-time "
        "data from existing accounts; implementation risk scales with "
        "market entry — licensure (dual-state in bi-state metros like "
        "Kansas City and Cincinnati), Medicaid enrollment, stations and "
        "hiring are months of runway, not weeks.",
        "Financial stability moved from checkbox to core after the "
        "sector's leverage record — Modivcare filed Chapter 11 in Aug "
        "2025 and emerged in Dec 2025 cutting over $1.1B of ~$1.4B of "
        "funded debt; GMR carried a $5.4B refinancing into a reduced IPO "
        "— a failed vendor is a service crisis delivered by other means.",
        "Price comparison requires a total-cost model: rate cards plus "
        "retainers plus expected denial allocation plus the bed-day cost "
        "of each bidder's reliability gap — the study's phrase: mature "
        "buyers price the bed-day, not the trip."),
    why_matters=(
        "The evaluation design is itself the maturity test: systems that "
        "cannot normalize non-equivalent bids default to price-only "
        "RFPs — which structurally select the least reliable bidder and "
        "regenerate the failure that triggered the RFP."),
    evidence=(
        _E("Labor is 70.7% of ambulance cost; 80%+ of NE EMS agencies "
           "are all-volunteer with the base contracting — crews, not "
           "trucks, are the scarce input a bid must prove",
           "SOURCED", "GADCS Y1-4 appendix + NE DHHS EMS Assessment "
           "(re-verify)",
           "https://ambulance.org/2025/12/09/cms-releases-new-gadcs-report/"),
        _E("Modivcare Chapter 11: filed Aug 20 2025 (S.D. Tex.), emerged "
           "Dec 29 2025 cutting >$1.1B of ~$1.4B funded debt — vendor "
           "financial stability is a service-continuity criterion",
           "SOURCED", "Bankruptcy docket + coverage (re-verify)", ""),
        _E("Bi-state licensure is a real entry barrier: the KC metro's "
           "adult IFT leader is dual KS+MO licensed; Cincinnati's OH-KY "
           "dual licensure protects incumbents",
           "SOURCED", "Footprint registry (public/company web), "
           "2026-07-10", ""),
        _E("Density is the cost lever a bid should evidence: strong "
           "inverse relationship between response volume and cost per "
           "response",
           "SOURCED", "MedPAC assessment of GADCS data, Dec 2025",
           "https://www.medpac.gov/wp-content/uploads/2025/01/Tab-M-Ambulance-Dec-2025.pdf"),
    ),
    subqs=(
        _S("How is fleet capacity evaluated?",
           "As staffed unit-hours by tier and post, with substitution "
           "and surge rules — never as a vehicle count."),
        _S("How is local density evaluated?",
           "Posts, existing volume and chaining potential in the actual "
           "market — density drives both cost and ETA credibility "
           "(MedPAC's volume-cost curve applied to a bid)."),
        _S("How is workforce availability evaluated?",
           "Credentialed-crew counts, retention and turnover, wage "
           "posture and recruiting pipeline — the binding constraint in "
           "a 70.7%-labor business."),
        _S("How are clinical capabilities evaluated?",
           "Tier coverage (BLS through CCT) with credentialing evidence, "
           "medical direction, and specialty protocols — peds, vent, "
           "behavioral."),
        _S("How is technology evaluated?",
           "Booking intake, CAD/AVL, live status and ETA feeds, ePCR and "
           "reporting — demonstrated live, not by screenshot."),
        _S("How is prior performance evaluated?",
           "Reference checks with transfer-center and nursing leaders at "
           "comparable accounts plus any measurable on-time data — "
           "anecdote-proofed."),
        _S("How is financial stability evaluated?",
           "Leverage, sponsor posture and cash runway — the sector's "
           "record (a broker's Chapter 11, leveraged national platforms) "
           "makes this a continuity test, not a formality."),
        _S("How is implementation risk evaluated?",
           "Time-to-service from signature — hiring, stations, "
           "licensure, payer enrollment — with milestones and remedies "
           "written into the contract."),
        _S("How is market-entry capability evaluated?",
           "For non-incumbents: dual-state licensure where relevant, "
           "Medicaid/MCO enrollment lead times, and local wage-market "
           "entry — months of runway, priced honestly."),
        _S("How is price compared across non-equivalent service models?",
           "Total-cost normalization: rates plus retainers plus denial "
           "allocation plus the reliability-adjusted bed-day cost — "
           "comparing rate cards alone is a category error."),
        _S("Are bidders required to commit to measurable capacity?",
           "In mature RFPs yes — dedicated units, staffed hours, "
           "fractile service levels; requiring it is the single question "
           "that separates real bids from brochures."),
        _S("How are optimistic provider claims tested?",
           "Staffing rosters and credential files, site visits, "
           "reference on-time data, pilot/ramp phases with exit rights, "
           "and penalty-backed service levels from day one."),
    ),
)


_CONTRACT = Block(
    "q6-contract", "Contract structure",
    conclusion=(
        "The IFT contract, where one exists, is assembled from known "
        "clauses — exclusivity or first-call, dedicated capacity, minimum "
        "volume or payment, a pricing basis, tiered rates by modality, "
        "separate mileage and wait billing, service levels with credits, "
        "denial and uncovered-trip allocation, escalators, expansion and "
        "termination rights — and against 911 and NEMT paper the striking "
        "fact is how few IFT relationships have any of it: the "
        "contract-form gap is the market's central artifact."),
    why_true=(
        "The comparator paper is rich and enforceable: 911 franchises "
        "write exclusivity plus response fractiles plus penalties (the "
        "8:59-at-90% urban template; $5,000-per-late-response examples), "
        "and NEMT broker contracts write on-time standards with penalty "
        "regimes (Texas's 85% benchmark, $15,000 penalty cap) and state "
        "audits — transport SLAs are normal one market over.",
        "Pricing structure mirrors reimbursement mechanics: base rates "
        "tiered by modality (even municipal 911 publishes tiered "
        "schedules — Lincoln Fire & Rescue runs city EMS under a "
        "published rate schedule with an EMS Oversight Authority), "
        "mileage billed separately as Medicare does, and wait time "
        "billable only by contract precisely because Medicare pays no "
        "wait; escalators can index to CPI or the Ambulance Inflation "
        "Factor (CY2026: +2.0%).",
        "The risk-allocation clauses are the differentiators: who pays "
        "payer-denied trips (documentation-caused versus coverage-"
        "caused), who pays uncovered legs (repatriations, midnight "
        "discharges), retainer versus minimum-volume forms, and "
        "excusable-delay definitions — the gray-zone money Question 4 "
        "mapped, converted into paper.",
        "No footprint hospital IFT contract is publicly readable — every "
        "term above is documentable only by diligence request; the "
        "closest public template is the county 911+IFT hybrid (Frontier's "
        "five-year Fremont County award)."),
    why_matters=(
        "The clause list IS the product: a dedicated operator's real "
        "offer is this contract — the transplant of 911/NEMT contract "
        "technology into the one transport market that never adopted "
        "it."),
    evidence=(
        _E("911 contract technology: 8:59 at the 90% fractile as the "
           "urban norm; penalties — Pasadena TX caps at 14:59, Multnomah "
           "penalizes below 90%, San Diego/Falck pays $5,000 per "
           "response beyond 24 minutes",
           "SOURCED", "Municipal EMS contract records (re-verify)", ""),
        _E("NEMT contract technology: Texas 85% on-time-pickup benchmark "
           "with a $15,000 penalty cap; broker contract standards "
           "commonly reach >=95% on-time",
           "GOV", "TX HHSC MTP contract terms + state broker contracts "
           "(re-verify)", ""),
        _E("Lincoln Fire & Rescue operates city EMS under a published "
           "rate schedule with an EMS Oversight Authority — tiered "
           "public transport pricing in the footprint",
           "SOURCED", "City of Lincoln EMS program records (re-verify)",
           ""),
        _E("Ambulance Inflation Factor CY2026: +2.0% (CY2025: +2.4%) — "
           "the published escalator index IFT contracts can write "
           "against",
           "GOV", "CMS Ambulance Fee Schedule PUF / industry summaries "
           "(re-verify)",
           "https://www.cms.gov/medicare/payment/fee-schedules/ambulance/ambulance-fee-schedule-public-use-files"),
        _E("No public hospital-by-hospital IFT contract exists for the "
           "footprint systems — the honest not-found that defines the "
           "contract-form gap",
           "FRAMEWORK", "2026-07-10 research sweep (dead-end log)", ""),
    ),
    subqs=(
        _S("Is the agreement exclusive?",
           "Rarely in IFT (de facto first-call instead); standard in 911 "
           "(EOA/franchise) and NEMT (regional broker) — the paper gap "
           "in one clause."),
        _S("Is capacity dedicated?",
           "Only in dedicated deals — named units, posts or windows; "
           "absent from the modal relationship."),
        _S("Is there a minimum-volume commitment?",
           "Occasionally in dedicated deals (the demand-side mirror of "
           "dedicated units); no public IFT example — a per-account "
           "diligence request."),
        _S("Is there a minimum-payment commitment?",
           "The retainer / availability-fee form — readiness bought "
           "explicitly, the 911 lesson imported into IFT paper."),
        _S("Is pricing based on trips, vehicles, hours, or service "
           "availability?",
           "Per-trip is the default; unit-hour, per-dedicated-unit and "
           "availability pricing appear as maturity rises."),
        _S("Are rates differentiated by modality?",
           "Yes wherever rates exist — tiered wheelchair/BLS/ALS/CCT; "
           "even municipal schedules (Lincoln Fire's) publish the same "
           "tiering logic."),
        _S("Are mileage and wait time separately billed?",
           "Mileage yes — Medicare's own shape (A0425 loaded miles); "
           "wait time only by contract, because Medicare pays no wait — "
           "uncontracted wait is pure provider loss."),
        _S("Are service levels clearly defined?",
           "In IFT, usually not — ETAs are best-efforts; the definable "
           "set (pickup-window fractiles by priority tier) is proven "
           "daily in 911 and NEMT paper."),
        _S("How are exceptions treated?",
           "Mature contracts define excusable delay (weather, receiver "
           "wall time, mass-casualty diversion) and measure it out of "
           "the service level; call lists define nothing."),
        _S("Are service credits or penalties included?",
           "Standard in 911 ($5,000-per-response examples) and NEMT "
           "(capped penalty regimes); exceptional in IFT — importing "
           "them is the ask."),
        _S("Who pays for trips denied by insurers?",
           "Default the provider (inside the 19.7% collect-nothing "
           "share); negotiable by denial cause — documentation versus "
           "coverage — in dedicated paper."),
        _S("Who pays for uncovered or non-billable trips?",
           "The hospital, where it ordered outside coverage "
           "(repatriation, capacity moves) — if the contract says so; "
           "otherwise the provider's write-off line."),
        _S("How are annual rate increases handled?",
           "CPI- or AIF-indexed escalators (AIF CY2026: +2.0%) — a "
           "published index exists; using it is a choice."),
        _S("How are new facilities or markets added?",
           "Expansion/affiliate clauses in system deals (rate parity "
           "plus ramp terms); ad hoc otherwise — M&A-heavy systems "
           "should pre-wire this clause."),
        _S("What termination rights exist?",
           "For-cause on service-level breach (meaningful only if "
           "service levels exist), convenience with notice, and "
           "transition-assistance duties — the clause that makes every "
           "other clause enforceable."),
    ),
)


_GOVERNANCE = Block(
    "q6-governance", "Governance",
    conclusion=(
        "Transport governance — a data-bearing review cadence, "
        "cross-facility KPI tables, documented action plans, an "
        "escalation ladder, executive sponsors on both sides — is "
        "standard machinery in 911 oversight and NEMT state audit, and "
        "essentially undocumented in hospital IFT; where it exists it is "
        "the vendor's gift, because only the vendor has the data."),
    why_true=(
        "The comparators govern with teeth: 911 systems answer to "
        "oversight bodies with published response reporting (Lincoln's "
        "EMS Oversight Authority; California's monthly per-hospital "
        "offload monitoring under AB 40), and NEMT brokers file audited "
        "on-time and complaint reporting with fines attached (New "
        "Jersey's ~$1.7M against Modivcare; Georgia's >$1M).",
        "In IFT the buyer typically holds no data at all — no trip log, "
        "no on-time rate, no denial view — so any review that exists is "
        "built on provider reporting; that inverts leverage but defines "
        "the dedicated partner's opening: bring the KPI table (on-time "
        "by priority tier, wall time by facility, denial causes, "
        "modality mix) to a buyer who has never seen one.",
        "The functioning forms are known from adjacent practice and are "
        "not exotic: monthly facility ops reviews plus quarterly system "
        "reviews, an action-item log, a named escalation ladder, "
        "prospective capacity review against the discharge curve, and "
        "contract amendments linked to measured performance — all absent "
        "by default in IFT."),
    why_matters=(
        "Governance is the retention moat: the vendor that runs the "
        "buyer's only performance table is structurally hard to displace "
        "— and the buyer that builds its own table is the only one able "
        "to hold any vendor accountable."),
    evidence=(
        _E("Lincoln Fire & Rescue's city EMS runs under an EMS Oversight "
           "Authority with a published rate schedule — municipal "
           "transport governance in the footprint",
           "SOURCED", "City of Lincoln EMS program records (re-verify)",
           ""),
        _E("California AB 40 requires monthly per-hospital ambulance "
           "patient-offload monitoring against a 30-minute/90% standard "
           "— measured transport governance imposed by statute",
           "GOV", "CA AB 40 / EMSA APOT program (re-verify)",
           "https://emsa.ca.gov/apot/"),
        _E("NEMT audit regimes with fines: NJ ~$1.7M against Modivcare "
           "(2017-22); GA >$1M against brokers (2018-20); Mississippi "
           "audit found ~5.8% late/missed vs contract",
           "SOURCED", "State enforcement records via press (re-verify)",
           ""),
        _E("'Lack of transparency — no real-time status, no ETA, no "
           "reporting' is a named IFT pain point: the buyer-side data "
           "vacuum governance must fill",
           "FRAMEWORK", "ift_study health-system pain-point registry",
           ""),
    ),
    subqs=(
        _S("How frequently is performance reviewed?",
           "In the modal account: never formally; functioning dedicated "
           "accounts run monthly ops plus quarterly business reviews."),
        _S("Who attends governance meetings?",
           "When real: transfer-center/capacity leadership, case "
           "management, nursing, supply chain, and the provider's ops "
           "and account executives — not procurement alone."),
        _S("Are reviews conducted by facility or across the system?",
           "Both, ideally — facility ops detail plus a system pattern "
           "view; data fragmentation usually forces facility-only."),
        _S("Which KPIs are reviewed?",
           "The buildable table: on-time pickup by priority tier, ETA "
           "accuracy, wall/offload time by facility, completion rate, "
           "denial rate and causes, modality mix, complaint log."),
        _S("Are action plans documented?",
           "Rarely — the observable norm is escalation emails; a "
           "documented action log is a maturity marker."),
        _S("Is there a clear escalation ladder?",
           "Only where contracts name one; otherwise escalation means "
           "the nurse redials and the manager complains."),
        _S("Who resolves recurring disputes?",
           "Absent governance: nobody — disputes become silent list "
           "demotion; with it: the named executive sponsors."),
        _S("Are capacity needs reviewed prospectively?",
           "Almost never — demand forecasting against discharge curves "
           "is the analysis neither side runs today, and the "
           "highest-value agenda item a review can add."),
        _S("Are contract changes linked to performance?",
           "Only if service levels and credits exist to link to — "
           "governance without contract teeth is a book club."),
        _S("Is there executive sponsorship on both sides?",
           "The make-or-break: sponsorship is what keeps transport from "
           "surfacing at the C-suite only as a boarding crisis."),
    ),
)


_WORKFLOW = Block(
    "q6-workflow", "Operating workflow",
    conclusion=(
        "The daily workflow — request, acuity documentation, assignment, "
        "timing, acceptance, ETA, delay updates, readiness, arrival, "
        "handoff, completion, reconciliation — is thirteen steps run by "
        "phone across two organizations, and each step has a measured or "
        "measurable failure mode; the workflow map is therefore also the "
        "product-requirements document for anyone claiming to fix IFT."),
    why_true=(
        "Request and entry: phoned to dispatch or booked via transfer "
        "center; acuity lives in the EHR but is re-declared verbally to "
        "the provider (the wrong-crew failure), and the requested time "
        "is negotiated against vendor availability rather than chosen "
        "from committed capacity.",
        "Assignment, acceptance and ETA are provider-side and verbal in "
        "the modal account — an ETA is a promise without instrumentation, "
        "and delay updates flow only when someone calls.",
        "Readiness, arrival and handoff carry the measured losses: "
        "patient-not-ready is the largest controllable door-time loss "
        "(and nursing's hidden workload), while arrival and handoff are "
        "timestamped only in the provider's ePCR — hospitals have no "
        "clock on their own front door, which is why California had to "
        "legislate offload measurement.",
        "Completion and reconciliation: the ePCR closes the trip and "
        "feeds the claim; hospitals reconcile only facility-billed "
        "invoices, usually without trip-level detail to audit against — "
        "two ledgers that meet only in mature accounts."),
    why_matters=(
        "Every step that runs on the phone is a step a workflow-"
        "integrated operator can instrument. This checklist is the "
        "operational content behind 'technology' claims — and the demo "
        "script a buyer should demand before believing any of them."),
    evidence=(
        _E("The disposition/transport interval dominates transfer time: "
           "mean DIDO 171.4 min with imaging-to-door 153.1 min — the "
           "workflow, not the imaging, is the delay",
           "ACADEMIC", "JAMA Network Open 2024 (n=28,887)",
           "https://doi.org/10.1001/jamanetworkopen.2024.31183"),
        _E("Crew detention at hospital doors: three-fourths of CA "
           "hospitals >1 hour, one-third >3 hours — the readiness/"
           "handoff failure measured at scale",
           "ACADEMIC", "Backer et al., Prehospital Emergency Care 2018",
           "https://doi.org/10.1080/10903127.2018.1525456"),
        _E("California had to legislate arrival-clock measurement: AB 40 "
           "APOT standards with monthly per-hospital monitoring — "
           "hospitals did not instrument their own door",
           "GOV", "CA AB 40 / EMSA APOT program (re-verify)",
           "https://emsa.ca.gov/apot/"),
        _E("The study's workflow frame: embedded scheduling "
           "coordinators, transfer-center EHR integration and ETA/"
           "reporting visibility are the integration depth that makes an "
           "incumbent the default first-call",
           "FRAMEWORK", "ift_study health-system procurement registry",
           ""),
    ),
    subqs=(
        _S("How is a trip requested?",
           "A phone call to the provider — or a transfer-center booking; "
           "electronic intake is the exception a few operators offer."),
        _S("Where is the request entered?",
           "The provider's CAD, re-keyed from the call; hospital-side "
           "there is often no system of record at all."),
        _S("How is clinical acuity documented?",
           "In the chart for care, verbally for transport — the tier the "
           "dispatcher hears sends the crew; mis-declared acuity means "
           "the wrong crew and a re-run trip."),
        _S("How is the provider assigned?",
           "By the caller's habit or the transfer center's rule — the "
           "allocation moment the vendor-configuration block governs."),
        _S("How is the requested time established?",
           "Negotiated against provider availability; under committed "
           "capacity it would be chosen from a schedule — that "
           "difference IS the operating model."),
        _S("How is acceptance confirmed?",
           "Verbally — 'we'll take it' plus an ETA; nothing signed, "
           "little logged on the buyer side."),
        _S("How is ETA communicated?",
           "By phone at booking, updated on request — push status/ETA "
           "feeds are the visible differentiator of integrated "
           "operators."),
        _S("How are delays updated?",
           "Mostly when the unit calls to ask — the transparency pain "
           "point in its purest form."),
        _S("How is the patient's readiness confirmed?",
           "Often not until the crew stands at bedside — patient-not-"
           "ready is the largest controllable door-time loss and "
           "nursing's hidden workload."),
        _S("How is arrival recorded?",
           "Crew timestamps in the ePCR; hospitals rarely capture it "
           "independently — CA legislated APOT measurement to see its "
           "own door."),
        _S("How is handoff completed?",
           "Bedside report plus signature to the receiving clinician; "
           "responsibility transfers at that documented moment."),
        _S("How is trip completion documented?",
           "The finished ePCR — times, mileage, care, signatures — "
           "simultaneously the operational record and the claim file."),
        _S("How are billing records reconciled?",
           "Provider-side against the ePCR; hospital-side only for "
           "facility-billed invoices, usually without trip-level detail "
           "— cross-ledger reconciliation exists only in mature "
           "accounts."),
    ),
)


_MATURITY = Block(
    "q6-maturity", "Procurement maturity",
    conclusion=(
        "Maturity runs a five-step ladder — ad hoc call lists, preferred "
        "letters, real contracts with service levels, managed programs "
        "with governance and data, strategic capacity partnership — and "
        "the tests are objective: demand visibility, vendor control, "
        "network-versus-facility management, prospective capacity "
        "planning, enforcement, and whether data ever redesigns the "
        "model; a dedicated partnership requires roughly step-four "
        "discipline from the buyer, which is why the partner usually has "
        "to build it for them."),
    why_true=(
        "The ladder's bottom is documented (call lists, no contracts, no "
        "data — Question 1's purchasing finding plus the not-found "
        "contract registry) and its top is documented one market over "
        "(911 oversight authorities, NEMT audit regimes) — maturing IFT "
        "procurement means walking known ground, not inventing it.",
        "Demand visibility is the cheapest test: most systems cannot "
        "state monthly trip counts by modality — spend fragments across "
        "cost centers and most trips ride payer claims the hospital "
        "never sees; a system that can produce its own demand curve is "
        "already top-quartile.",
        "Enforcement and redesign separate the top steps: service levels "
        "that exist but never bind are step-three theater, while "
        "evidence-priced redesign — the Wesley/HCA flip that moved ~77% "
        "of county interfacility volume, modality re-tiering, "
        "discharge-window re-timing — is the observable behavior of "
        "step-five buyers.",
        "The dedicated-partnership threshold is specific: centralized "
        "booking (or adoption of the partner's), a named owner, seats at "
        "a governance table, and committed volume — absent those, "
        "dedication economics do not close for either side."),
    why_matters=(
        "Maturity grading converts the study's softest topic into a "
        "scoreable diagnostic per account — and tells an operator which "
        "accounts are sellable now versus which must first be taught to "
        "buy. The partner can bring the data and the paper; only the "
        "buyer can bring the owner."),
    evidence=(
        _E("The IFT purchasing baseline: call lists and unenforced "
           "preferred letters dominate; no public contract registry "
           "documents system-wide IFT terms — the ladder's measured "
           "bottom",
           "FRAMEWORK", "Question 1 purchasing synthesis + 2026-07-10 "
           "dead-end log", ""),
        _E("The ladder's top exists next door: 911 oversight authorities "
           "with published reporting and NEMT state audit regimes with "
           "fines — governance forms IFT can copy verbatim",
           "SOURCED", "Municipal EMS oversight + state NEMT enforcement "
           "records (re-verify)", ""),
        _E("Step-five behavior, observed once: Wesley/HCA's evidence-"
           "priced redesign moved ~77% of county interfacility volume "
           "(~4,873 transports/2020) to a contracted private",
           "SOURCED", "Footprint registry (public/company web + local "
           "records), 2026-07-10 (re-verify)", ""),
        _E("The five named pain points of immature buying — late "
           "transports/poor ETAs, blocked beds, fragmented vendors, no "
           "transparency, staff strain — are the ladder's bottom rungs "
           "experienced clinically",
           "FRAMEWORK", "ift_study health-system pain-point registry",
           ""),
    ),
    subqs=(
        _S("What distinguishes ad hoc buying from strategic management?",
           "Ownership, paper and data: a named owner, a contract with "
           "service levels, and a demand/performance table — ad hoc has "
           "none of the three."),
        _S("How much visibility exists into demand?",
           "Usually near-zero — no trip log, fragmented spend; the "
           "diagnostic question is 'how many trips last month, by "
           "modality?' and most systems cannot answer it."),
        _S("How much control exists over vendor behavior?",
           "Proportional to paper: no contract, no control; service "
           "levels plus credits plus governance reach the 911/NEMT level "
           "of control IFT rarely attempts."),
        _S("Is transportation managed facility by facility or as a "
           "network?",
           "Facility-by-facility by default, even inside systems; "
           "network management follows booking centralization — the "
           "transfer center is the pivot."),
        _S("Are capacity requirements planned or merely requested?",
           "Requested, trip by trip — prospective planning against the "
           "discharge curve is the step-four behavior that makes "
           "dedication possible."),
        _S("Is performance retrospective or actively managed?",
           "Retrospective at best — complaints after failures; active "
           "management needs live status and a KPI table, data the buyer "
           "must contract for."),
        _S("Are service levels consistently enforced?",
           "Almost never — enforcement requires service levels, "
           "measurement, and credits, in that order; most accounts lack "
           "the first."),
        _S("Are data used to redesign the operating model?",
           "Only at the ladder's top — evidence-priced insource/"
           "outsource moves (the Wesley/HCA flip) and modality "
           "re-tiering are the observable behaviors."),
        _S("What level of maturity is required to support a dedicated "
           "partnership?",
           "Roughly step four of five: centralized booking, a named "
           "owner, governance participation, and volume commitment — "
           "the partner can supply the data and the paper, but not the "
           "owner."),
    ),
)


Q6 = QuestionDef(
    num=6,
    slug="procurement",
    title="How do health systems procure and manage IFT?",
    storyline=(
        "IFT is the only transport market still bought without real "
        "contracts — 911 and NEMT write enforceable SLAs with penalties "
        "while most hospitals work call lists — so procurement maturity, "
        "not price, is what separates systems that get reliable capacity "
        "from systems that get excuses."),
    visual_key="maturity",
    blocks=(_PROC_OWNERSHIP, _VENDOR_CONFIG, _TRIGGER, _EVALUATION,
            _CONTRACT, _GOVERNANCE, _WORKFLOW, _MATURITY),
)


QUESTIONS = (Q4, Q5, Q6)
