"""IFT diligence question architecture — the study's question tree (SOW spine).

This is the "how the study is interrogated" layer that sits behind the answered
pages. Where :mod:`ift_study` answers the four SOW dimensions and :mod:`ift_geo`
/ :mod:`ift_analytics` size the market, THIS module encodes the *diligence
question architecture*: for every slide in the market study it carries the
underlying main question, the sub-question tree beneath it, the data/evidence
that would prove the point, the visuals that make it persuasive, and — the value
add over a static outline — a live cross-link to WHERE ON THIS PLATFORM the
answer already lives, plus the real connector datasets that feed the evidence.

It is deliberately not a sizing module: it holds no dollar figures of its own.
Every quantitative claim stays on the sized pages this module points at, so
nothing here can drift from the numbers. The content is authored diligence
knowledge (FRAMEWORK); the connector references are resolved at read time from
the real :mod:`ift_connectors` estate so a renamed dataset degrades to nothing
rather than to a dead reference.

Design contract mirrors the rest of the IFT modules: frozen dataclasses, pure
functions that DEGRADE (return ``available=False`` / empty) and never raise, and
an honesty ``source_label`` on every result.

Public API:
    master_tree() -> MasterTree
    slide_architecture() -> SlideArchitecture
    evidence_plan() -> EvidencePlan
    visual_package() -> VisualPackage
    nuances() -> Tuple[Nuance, ...]
    connector_evidence() -> ConnectorEvidence
    diligence_summary() -> Dict[str, Any]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# The live answer surfaces this study is decomposed against. Kept as one table so
# every cross-link on the page resolves to a route that actually serves (the
# palette test pins that these serve HTTP 200).
LINK = {
    "study": ("/ift-study", "Investor market study — 4 dimensions"),
    "study_mmt": ("/ift-study?company=mmt", "Company positioning — MMT"),
    "markets": ("/ift-markets", "Geographic markets — TAM/SAM/SOM"),
    "research": ("/ift-research", "Market research brief — 20 topics"),
    "research_def": ("/ift-research#rs-definition", "Definition & taxonomy"),
    "research_eco": ("/ift-research#rs-ecosystem", "Patient journey & ecosystem"),
    "research_ops": ("/ift-research#rs-operating",
                     "Operating models, procurement & pain"),
    "research_comp": ("/ift-research#rs-competitive",
                      "Competitive landscape by type"),
    "clinical": ("/ift-clinical", "Clinical acute-transfer demand engine"),
    "mmt": ("/ift-mmt", "MMT county deep-dive (by MSA)"),
    "estate": ("/connector-estate", "Live data-connector estate"),
    "report": ("/market/interfacility_transport", "Full IFT market report"),
    "xlsx": ("/api/ift/markets.xlsx", "Investor data pack (Excel)"),
}


def _links(*keys: str) -> Tuple[Tuple[str, str], ...]:
    """Resolve link keys to (label, href) pairs, dropping unknown keys."""
    out: List[Tuple[str, str]] = []
    for k in keys:
        href_label = LINK.get(k)
        if href_label:
            out.append((href_label[1], href_label[0]))
    return tuple(out)


# ─────────────────────────────────────────────────────────────────────────────
# 0 — The master question tree (SOW Section 0: A / B / C)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class QGroup:
    """A cluster of sub-questions under one heading."""
    heading: str
    questions: Tuple[str, ...]


@dataclass(frozen=True)
class TreeBranch:
    key: str
    title: str
    main_question: str
    intro: str
    groups: Tuple[QGroup, ...]


@dataclass(frozen=True)
class MasterTree:
    available: bool
    branches: Tuple[TreeBranch, ...] = ()
    source_label: str = ""
    note: str = ""


_BRANCH_A = TreeBranch(
    key="what",
    title="A. What exactly is the IFT market?",
    main_question=("What patient-transportation use cases should be included in "
                   "'IFT,' and what should be excluded?"),
    intro=("The market boundary IS the thesis. Draw it by dispatch source, buyer, "
           "and care setting — not by acuity alone — or the asset gets mis-priced "
           "against the whole-ambulance or NEMT market."),
    groups=(
        QGroup("What is the unit of demand?", (
            "Is the market measured by trips, transports, patient encounters, "
            "revenue, loaded miles, facility contracts, or covered lives?",
            "Are scheduled AND unscheduled transfers the same market?",
            "Are discharge transports included? ED-to-hospital? "
            "Hospital-to-hospital?",
            "Are hospital-to-SNF / IRF / LTACH / home transports included?",
            "Are recurring transports (dialysis, oncology) in or out?",
            "Are behavioral-health, neonatal / pediatric / bariatric, and "
            "critical-care transports included?",
            "Ground only, or air medical too?",
        )),
        QGroup("What distinguishes IFT from 911 EMS?", (
            "Who initiates — facility-directed or patient/public-directed?",
            "Emergent, urgent, scheduled, or discharge-related?",
            "Who chooses the provider — a public dispatch system, a hospital "
            "transfer center, a case manager, or a contract?",
            "Is response time measured in minutes, SLA windows, discharge-cycle "
            "impact, or bed throughput?",
            "Is the buyer the municipality, patient, hospital, payer, or system?",
            "Is revenue fee-for-service, municipal contract, hospital contract, "
            "or mixed?",
        )),
        QGroup("What distinguishes IFT from NEMT?", (
            "Is medical monitoring, a stretcher, or ambulance-level staffing "
            "required?",
            "Is the patient under active clinical care, mid acute-care "
            "transition?",
            "Is the origin/destination a hospital, ED, SNF, home, clinic, or "
            "dialysis center?",
            "Who decides transport is medically necessary?",
            "Who pays when medical necessity is not met?",
        )),
        QGroup("What is the market's center of gravity?", (
            "Is IFT mostly acute-care transfer, discharge management, post-acute "
            "placement enablement, or critical-care transfer?",
            "Is it a hospital-logistics function more than a pure ambulance "
            "service?",
            "Which use cases drive volume? Which drive profitability? Which drive "
            "strategic importance for health systems?",
        )),
        QGroup("What are the natural segmentations inside IFT?", (
            "By acuity: BLS, ALS, CCT, SCT, neonatal, pediatric, bariatric, "
            "behavioral.",
            "By urgency: emergent, urgent, scheduled, routine, discharge.",
            "By origin/destination lane: ED-to-ED, ED-to-inpatient, "
            "hospital-to-hospital, hospital-to-post-acute, and the return legs.",
            "By contracting model: exclusive partner, preferred vendor, roster, "
            "spot market, insourced fleet, hybrid.",
            "By payer: Medicare, Medicaid, commercial, facility-paid, self-pay, "
            "capitated / value-based.",
            "By geography and customer type: IDN, community hospital, academic "
            "medical center, freestanding ED, LTACH, SNF, rehab, behavioral.",
        )),
    ),
)

_BRANCH_B = TreeBranch(
    key="why",
    title="B. Why does the market matter to health systems?",
    main_question=("Why should a health system care about IFT beyond 'getting a "
                   "patient from point A to point B'?"),
    intro=("The strongest version of the thesis is operational, not "
           "market-size-based: transportation failures create measurable, "
           "expensive health-system pain."),
    groups=(
        QGroup("How does IFT affect hospital throughput?", (
            "Does delayed transport increase ED boarding and delay admissions?",
            "Does it delay discharges and prevent bed turnover?",
            "Does it reduce effective capacity and create avoidable "
            "length-of-stay?",
            "Does it disrupt transfer-center operations and waste nursing time?",
        )),
        QGroup("How does IFT affect financial performance?", (
            "Do delayed discharges create avoidable bed days?",
            "Does delayed transfer reduce the ability to accept higher-acuity "
            "patients?",
            "Does delayed repatriation keep patients in expensive settings?",
            "Does poor documentation create reimbursement leakage, or force the "
            "hospital to subsidize un-billable trips?",
            "Does transport availability gate service-line growth?",
        )),
        QGroup("How does IFT affect care quality & patient experience?", (
            "Do delays break continuity of care and leave patients waiting in "
            "hallways or ED bays?",
            "Are patients moved to the right level of care quickly?",
            "Are high-risk patients transported by appropriately trained crews?",
            "Are handoffs reliable and families kept informed?",
        )),
        QGroup("How does IFT affect system strategy?", (
            "Does transport enable hub-and-spoke models and centralized specialty "
            "services?",
            "Does it support post-acute network management and reduce leakage?",
            "Does it support payer value-based-care initiatives and ED "
            "decompression?",
            "Does it underpin regional transfer strategy?",
        )),
    ),
)

_BRANCH_C = TreeBranch(
    key="advantage",
    title="C. Why might dedicated IFT providers be advantaged?",
    main_question=("What capabilities does a dedicated IFT provider build that a "
                   "911 EMS provider or fragmented local vendor may not "
                   "prioritize?"),
    intro=("Test the thesis, do not assume it — dedicated capacity is both an "
           "advantage and a cost; prove when health systems value reliability "
           "enough to pay for it."),
    groups=(
        QGroup("Operational specialization", (
            "Is the fleet designed around facility-based demand, not municipal "
            "emergency coverage?",
            "Are dispatch workflows built around hospital transfer centers?",
            "Is it optimized for scheduled + urgent reliability, not only "
            "emergency response?",
            "Are vehicles stationed around hospital nodes with dedicated units "
            "for specific customers?",
        )),
        QGroup("Customer integration", (
            "Does it integrate with hospital transfer centers and give ETA / unit "
            "/ cancellation / status visibility?",
            "Does it attend operating reviews with health-system leadership and "
            "report SLA performance?",
            "Does it help solve root-cause delays and become embedded in daily "
            "patient-flow operations?",
        )),
        QGroup("Contracting & economics", (
            "Does dedicated capacity reduce uncertainty, and does an "
            "exclusive/semi-exclusive model improve planning?",
            "Does fixed-base + variable pricing improve reliability?",
            "Does the provider accept SLA commitments and trade utilization risk "
            "for deeper partnership?",
            "Does it generate stickier relationships than spot-market vendors?",
        )),
        QGroup("Competitive defensibility", (
            "Does density create better unit availability and lower deadhead?",
            "Does customer-specific workflow knowledge create switching costs?",
            "Does dispatch data improve future staffing and deployment?",
            "Does trust with case-management / transfer-center teams, plus "
            "compliance and reporting, make the incumbent hard to displace?",
        )),
    ),
)


def master_tree() -> MasterTree:
    """The three top-level diligence branches (what the market is, why it matters,
    why dedicated may win). Authored FRAMEWORK — never raises."""
    return MasterTree(
        available=True,
        branches=(_BRANCH_A, _BRANCH_B, _BRANCH_C),
        source_label=("Authored diligence question architecture (FRAMEWORK); the "
                      "answers live on the sized IFT pages this tree points at"),
        note=("The core storyline: IFT is a distinct operational layer inside the "
              "hospital care-continuum — different from 911 EMS and NEMT across "
              "use case, buyer, acuity, economics, workflow, and competitive "
              "basis — and a dedicated partnership model may be structurally "
              "advantaged."))


# ─────────────────────────────────────────────────────────────────────────────
# 1 — The per-slide question architecture (SOW slides 1..15)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Slide:
    num: int
    slug: str
    title: str
    kind: str                              # cover | divider | content
    prompt: str
    main_question: str
    groups: Tuple[QGroup, ...]
    data_needed: Tuple[str, ...]
    visuals: Tuple[str, ...]
    answered_by: Tuple[Tuple[str, str], ...]   # (label, href)
    connector_keys: Tuple[str, ...]            # ift_connectors keys feeding evidence


@dataclass(frozen=True)
class SlideArchitecture:
    available: bool
    slides: Tuple[Slide, ...] = ()
    source_label: str = ""
    note: str = ""


_SLIDES: Tuple[Slide, ...] = (
    Slide(
        num=1, slug="cover", title="Cover — frame the study", kind="cover",
        prompt="Frame what the study is actually about.",
        main_question=("Is this a market-definition study, a commercial-diligence "
                       "proof, a growth-strategy study, or an investment thesis — "
                       "and who is the audience?"),
        groups=(
            QGroup("Framing decisions", (
                "Market-first, company-first, or thesis-first title?",
                "Audience: internal deal team, lenders, management, board, buyer, "
                "or client health-system executives?",
                "Tone: neutral market study, diligence-style proof, or strategic "
                "narrative?",
            )),
        ),
        data_needed=(
            "The deal team's intended use of the study (education vs proof vs IC "
            "support).",
        ),
        visuals=("Clean title page with the subtitle 'Market Framework, Health "
                 "System Use Cases, and Dedicated Provider Positioning.'",),
        answered_by=_links("study", "markets"),
        connector_keys=(),
    ),
    Slide(
        num=2, slug="vocabulary", title="Dimension intro — vocabulary & boundaries",
        kind="content",
        prompt=("Establish a common vocabulary and market framework that will "
                "serve as the foundation for the remainder of the study."),
        main_question=("What vocabulary, classifications, and market boundaries "
                       "must be fixed before the rest of the study can be "
                       "interpreted consistently?"),
        groups=(
            QGroup("Terms to define precisely", (
                "IFT — all interfacility ambulance transport, and does it include "
                "discharge, post-acute, non-ambulance medical van, or air?",
                "EMS vs '911 / emergency' — is the defining feature the dispatch "
                "source or the clinical acuity?",
                "NEMT — Medicaid wheelchair/van benefit; when does it become "
                "ambulance-level?",
                "Critical-care transport — a sub-tier WITHIN IFT or a separate "
                "category?",
                "'Dedicated IFT partnership' — dedicated fleet, crews, dispatch, "
                "exclusivity, SLAs, embedded onsite team?",
                "Insourced / outsourced / hybrid — classified by operational "
                "delivery, NOT reimbursement or branding.",
            )),
            QGroup("Dimensions of the market framework", (
                "Clinical acuity, urgency, origin/destination, buyer / "
                "decision-maker, payer / revenue source, procurement model, "
                "operating model, competitive basis.",
                "For each term: definition (inclusion / exclusion), operational "
                "reality, economic reality, and strategic importance.",
            )),
        ),
        data_needed=(
            "A glossary reconciled to how the target actually classifies its own "
            "trips.",
            "Ambulance vs NEMT-van supplier universes (to bound the categories).",
            "The coverage rules that decide when a mode is medically necessary.",
        ),
        visuals=(
            "Market-definition decision tree (branches by acuity, "
            "origin/destination, monitoring, dispatcher, payer).",
            "Service-category continuum (acuity × urgency).",
            "Vocabulary glossary page (term, plain-English definition, included / "
            "excluded, why it matters).",
            "Market-boundary map (core IFT vs adjacent NEMT / 911 / air).",
        ),
        answered_by=_links("research_def", "study", "markets"),
        connector_keys=("ambulance_suppliers", "nemt_van_suppliers",
                        "ambulance_coverage", "icd10_validation"),
    ),
    Slide(
        num=3, slug="divider", title="Section divider — Dimension 1: IFT Market",
        kind="divider",
        prompt="Orient the reader into the first dimension.",
        main_question=("Signal that Dimension 1 is market definition, ecosystem, "
                       "health-system purchasing, and MMT positioning — not "
                       "operational pain points yet."),
        groups=(
            QGroup("Dimension roadmap", (
                "Market context → IFT ecosystem → Health-system POV → MMT "
                "positioning.",
            )),
        ),
        data_needed=(),
        visuals=("A small dimension-roadmap strip so the reader sees why the "
                 "slides move from broad definition into company positioning.",),
        answered_by=_links("study", "markets"),
        connector_keys=(),
    ),
    Slide(
        num=4, slug="definition", title="Market context — clear market definition",
        kind="content",
        prompt=("Develop a clear market definition that distinguishes IFT from "
                "traditional EMS and non-emergency medical transportation."),
        main_question=("What is IFT, and why is it meaningfully different from 911 "
                       "EMS and NEMT?"),
        groups=(
            QGroup("What is the cleanest definition of IFT?", (
                "By origin/destination — movement between care sites (hospital to "
                "hospital, hospital to post-acute, ED to another facility).",
                "By who initiates — health-system staff, transfer center, case "
                "manager, ED nurse, discharge planner, physician.",
                "By clinical context — patient already inside the system, under "
                "active care, mid care-transition.",
                "By economic buyer — the health system controls vendor choice even "
                "when the payer reimburses.",
                "By operational role — enables patient flow, right-level-of-care "
                "movement, and bed management.",
            )),
            QGroup("What belongs in CORE IFT?", (
                "ED-to-hospital and hospital-to-hospital (incl. tertiary / "
                "specialty) transfers.",
                "Hospital-to-SNF / IRF / LTACH / behavioral discharge legs.",
                "Post-acute-to-hospital readmission and repatriation legs.",
                "Critical-care ground transport and medically necessary "
                "long-distance transfers.",
            )),
            QGroup("What is excluded or adjacent?", (
                "911 scene response, fire / municipal emergency response, air "
                "medical evacuation.",
                "Routine wheelchair van, ambulatory rideshare-style and Medicaid "
                "brokered NEMT, recurring dialysis van.",
                "Courier / lab / organ transport unless tied to patient movement.",
            )),
            QGroup("The hardest boundaries to draw", (
                "Emergency IFT vs 911 — a hospital-to-hospital transfer can be "
                "emergent yet is NOT a 911 patient (dispatch source, not acuity).",
                "Ambulance IFT vs NEMT — some discharge legs look like NEMT but "
                "consume ambulance resources.",
                "Critical-care transport — premium IFT sub-segment vs separate "
                "specialty market.",
                "Air — clinically adjacent but a different fleet, economics, and "
                "competitive set (show as adjacent).",
            )),
        ),
        data_needed=(
            "For each use case: who requests, who chooses the vendor, who pays, "
            "who bears the cost of failure, response-time expectation, crew / "
            "vehicle required, documentation, and whether it is profitable.",
            "Medicare Part-B ambulance utilization by HCPCS tier (to weight the "
            "BLS / ALS / CCT mix).",
            "The ambulance and NEMT-van supplier universes (to separate the "
            "categories).",
        ),
        visuals=(
            "IFT definition box ('medically appropriate patient movement between "
            "sites of care, initiated by facilities…').",
            "Three-circle Venn: 911 EMS / IFT / NEMT with the overlap zones.",
            "Boundary decision tree (dispatch source → care-setting → acuity → "
            "vendor-selection).",
            "Use-case segmentation table (lane × dispatcher × acuity × buyer × "
            "payer × KPI × in-IFT?).",
        ),
        answered_by=_links("study", "markets", "research_def"),
        connector_keys=("ambulance_suppliers", "nemt_van_suppliers",
                        "part_b_ambulance", "ambulance_coverage",
                        "hospital_universe"),
    ),
    Slide(
        num=5, slug="taxonomy", title="Market context — taxonomy matrix",
        kind="content",
        prompt=("Build a market-taxonomy matrix comparing IFT, 911, critical-care "
                "transport, wheelchair / van / NEMT, air, etc. across customers, "
                "use cases, acuity, payer, dispatch workflow, contracting model, "
                "and operating requirements."),
        main_question=("How do the major patient-transport categories differ "
                       "across the dimensions that actually matter commercially "
                       "and operationally?"),
        groups=(
            QGroup("Rows — the service categories", (
                "911 ground EMS; private / backup emergency ambulance; core BLS / "
                "ALS IFT; critical-care transport; specialty (neonatal / peds / "
                "bariatric / behavioral); discharge ambulance; wheelchair / "
                "stretcher / medical van; Medicaid / brokered NEMT; air medical; "
                "health-system-owned fleet.",
            )),
            QGroup("Columns — the comparison dimensions", (
                "Primary use case; customer / buyer; patient acuity; "
                "origin/destination; dispatcher / workflow; payer / "
                "reimbursement; contracting model; operating requirements; "
                "competitive basis; strategic importance to the health system.",
            )),
            QGroup("The nuance the matrix must expose", (
                "In 911 the municipality is the buyer; in IFT the health system "
                "is the buyer even when insurance pays the claim; in NEMT the "
                "payer / broker controls routing.",
                "Acuity alone does not separate the categories — dispatch source, "
                "buyer, and workflow do.",
            )),
        ),
        data_needed=(
            "Ambulance-fee-schedule tiers and the commercial multiple (payer "
            "column).",
            "Part-B ambulance utilization + market-saturation supplier counts "
            "(competitive-basis column).",
            "Coverage / medical-necessity policy (the reimbursement column).",
        ),
        visuals=(
            "The full taxonomy matrix, color-coded (green = core / strong, yellow "
            "= partial, red = not typical, gray = n/a).",
            "Heat map of strategic relevance to health systems (categories × "
            "throughput / discharge / ED decompression / specialty access / "
            "revenue / experience / cost).",
            "Acuity-vs-urgency scatterplot (911 / NEMT / IFT / CCT / air / "
            "discharge).",
            "Buyer-vs-payer map (who selects the vendor × who pays the claim).",
            "Dispatch-workflow swimlanes (911 vs IFT vs NEMT).",
        ),
        answered_by=_links("study", "research_def", "markets"),
        connector_keys=("part_b_ambulance", "ambulance_market_saturation",
                        "ambulance_coverage", "nemt_managed_care",
                        "ambulance_suppliers"),
    ),
    Slide(
        num=6, slug="markets-contrast",
        title="Market context — customers, models, purchasing, reimbursement, "
              "competition",
        kind="content",
        prompt=("Detail and contrast the customers, operating models, purchasing "
                "decisions, reimbursement dynamics, and competitive "
                "characteristics unique to 911 / emergency, IFT, and NEMT."),
        main_question="How do 911, IFT, and NEMT differ as commercial markets?",
        groups=(
            QGroup("Customer differences", (
                "911: municipality / county / fire district values coverage and "
                "response time; measures response time and unit-hour utilization.",
                "IFT: the health system / transfer center / case management values "
                "ETA reliability and discharge throughput; measures on-time "
                "pickup, request-to-arrival, cancellations, SLA.",
                "NEMT: Medicaid MCO / broker values low cost-per-ride and "
                "appointment adherence; measures completed rides and no-shows.",
            )),
            QGroup("Operating-model differences", (
                "Capacity deployment: 911 geographically distributed; IFT "
                "facility-clustered and semi-scheduled; NEMT route-optimized.",
                "Demand predictability: 911 stochastic; IFT partly forecastable "
                "from discharge / transfer patterns; NEMT scheduled recurring.",
                "Labor & tech: CAD / PSAP for 911; hospital-facing portal + SLA "
                "reporting for IFT; broker platform + eligibility for NEMT.",
            )),
            QGroup("Purchasing & reimbursement differences", (
                "911 purchasing is political / municipal; NEMT is payer / broker / "
                "cost-driven; IFT is embedded in hospital throughput.",
                "Does reimbursement align with the buyer's incentives? Who "
                "absorbs unreimbursed but operationally necessary trips?",
            )),
            QGroup("Competitive-characteristic differences", (
                "Who competes, what differentiates, what creates switching costs, "
                "and what creates scale advantage in each of the three markets.",
            )),
        ),
        data_needed=(
            "Part-B ambulance utilization + Medicaid managed-care penetration (the "
            "NEMT proxy).",
            "Market-saturation and enrollment supplier counts (the competitive "
            "set).",
            "'What failure looks like' by segment (911 = late emergency; IFT = "
            "blocked bed / ED boarding; NEMT = missed appointment).",
        ),
        visuals=(
            "Side-by-side market-archetype table (911 / IFT / NEMT × customer / "
            "buyer / payer / dispatcher / KPI / failure consequence).",
            "Three commercial-model diagrams (buyer / user / payer / vendor / "
            "dispatch / economic flow).",
            "'What failure looks like' comparison.",
            "KPI-comparison dashboard by segment.",
        ),
        answered_by=_links("research_ops", "research_comp", "study", "markets"),
        connector_keys=("part_b_ambulance", "nemt_managed_care",
                        "ambulance_market_saturation", "ambulance_enrollment",
                        "ambulance_coverage"),
    ),
    Slide(
        num=7, slug="why-dedicated",
        title="Market context — why dedicated IFT competes differently",
        kind="content",
        prompt=("Demonstrate why dedicated IFT providers compete on fundamentally "
                "different dimensions than traditional EMS, and why these "
                "structural differences create a sustainable advantage for "
                "purpose-built operators."),
        main_question=("Why is a purpose-built IFT provider not just another "
                       "ambulance company?"),
        groups=(
            QGroup("The competitive dimensions in IFT", (
                "Scheduled-pickup and response-time reliability; capacity during "
                "discharge peaks; multi-acuity coverage; transfer-center "
                "integration; transparent ETAs; documentation / billing accuracy; "
                "reduced call-around; performance reporting.",
            )),
            QGroup("How they differ from 911 EMS and regional vendors", (
                "911 optimizes immediate emergency response and public coverage "
                "obligations, not hospital discharge timing or transfer-delay "
                "metrics.",
                "Regional vendors may lack density, technology integration, real "
                "SLAs, acuity breadth, and account-management sophistication.",
            )),
            QGroup("What makes the advantage sustainable", (
                "Density (positioning, deadhead, spike absorption); workflow "
                "integration (embeddedness, retraining cost to switch); data "
                "(staffing, delay root-cause, renewals); contractual stickiness; "
                "clinical breadth (one throat to choke); relationship depth; "
                "reliability reputation.",
            )),
            QGroup("Counterarguments to test", (
                "Does dedicated capacity become under-utilized / more expensive?",
                "Are SLAs actually enforced, and do local vendors sometimes "
                "outperform?",
                "Is the advantage stronger in dense regions than rural markets?",
                "Can labor shortages erase the provider advantage?",
            )),
        ),
        data_needed=(
            "Ambulance market-saturation and supplier density per market (the "
            "density moat).",
            "Hospital-origin density to anchor 'built around facility demand.'",
        ),
        visuals=(
            "Competitive-basis shift chart (traditional EMS vs dedicated IFT).",
            "Capability-maturity curve (ad-hoc call-around → dedicated capacity → "
            "integrated transport command center).",
            "Dedicated-IFT flywheel (contract → density → reliability → data → "
            "renewal → more density).",
            "Switching-cost stack; 'cost of failure' bridge.",
        ),
        answered_by=_links("study", "markets", "research_comp"),
        connector_keys=("ambulance_market_saturation", "ambulance_suppliers",
                        "hospital_universe"),
    ),
    Slide(
        num=8, slug="patient-journey", title="IFT ecosystem — the patient journey",
        kind="content",
        prompt=("Map the patient journey and the role IFT plays across acute "
                "hospitals, EDs, freestanding EDs, post-acute providers, IRF, "
                "LTACH, SNF, and other sites of care."),
        main_question=("Where does IFT appear in the patient journey, and what "
                       "operational problem does it solve at each transition "
                       "point?"),
        groups=(
            QGroup("The journey stages", (
                "Entry into acute care (ED / freestanding ED / direct admit / "
                "post-acute origin).",
                "ED stabilization and the transfer decision (specialty need, "
                "capacity, accepting physician, authorization, when transport is "
                "requested).",
                "Hospital-to-hospital transfer (lateral vs up-transfer vs "
                "repatriation; BLS / ALS / CCT / air).",
                "Inpatient stay and discharge planning (medically-ready timing, "
                "destination confirmed, SNF admission windows, avoidable LOS).",
                "Post-acute transition (SNF / IRF / LTACH / behavioral / home / "
                "hospice) and readmission / return-to-hospital.",
            )),
            QGroup("The transition problems IFT solves", (
                "Freestanding EDs are structurally transport-dependent (no "
                "inpatient beds → more transfer demand).",
                "Late-day discharge misses SNF admission windows → an avoidable "
                "bed day.",
                "When IFT is unavailable, post-acute facilities call 911 — "
                "inappropriate emergency utilization a dedicated partner can "
                "reduce.",
            )),
        ),
        data_needed=(
            "The mapped acute-transfer scenario registry (condition → code → "
            "destination → volume).",
            "Hospital + post-acute (SNF / IRF / LTACH / hospice / HHA) node "
            "universe — the origins and destinations.",
            "Hospital catchment / patient-flow matrix and inpatient occupancy "
            "(where boarding builds).",
            "Aging-catchment and chronic-disease prevalence (the demand growth "
            "tail).",
        ),
        visuals=(
            "Patient-journey map with per-stage initiator / transport need / "
            "failure mode / KPI / MMT role.",
            "Site-of-care network map (nodes = care sites, arrows = flows).",
            "Sankey of transport volume (source sites → destination sites, sized "
            "by volume, colored by acuity).",
            "Bottleneck map; an 'IFT touchpoint' care-continuum overlay.",
        ),
        answered_by=_links("clinical", "research_eco", "study"),
        connector_keys=("hospital_universe", "postacute_universe",
                        "hospital_service_area", "dialysis_facilities",
                        "hospital_capacity", "chronic_disease", "aging_demand"),
    ),
    Slide(
        num=9, slug="participants", title="IFT ecosystem — major participants",
        kind="content",
        prompt=("Identify the major participants — health systems, ambulance "
                "providers, payers, patients, and downstream care providers — and "
                "how transportation enables care transitions across the "
                "continuum."),
        main_question=("Who participates in the IFT ecosystem, what does each "
                       "party want, and how do incentives align or conflict?"),
        groups=(
            QGroup("The participant categories", (
                "Health systems (C-suite, COO, CFO, CNO, ED, transfer center, "
                "case / bed management, discharge planning, procurement, revenue "
                "cycle, service lines) — who owns the problem vs who controls the "
                "budget.",
                "Transport providers (dedicated IFT, traditional EMS, regional "
                "private, fire-based, hospital-owned, CCT, air, NEMT / broker) — "
                "acuity coverage, density, dedicated capacity, billing capability.",
                "Payers (Medicare, Medicaid, commercial, MA, MCO, workers' comp, "
                "self-pay, risk-bearing) — coverage rules, medical necessity, "
                "denials, and the reimbursement they drive.",
                "Patients & families — rarely choose or pay, but bear the "
                "experience and safety stakes.",
                "Downstream / post-acute providers — admission cutoffs, handoff "
                "needs, census exposure, network leakage.",
                "Regulators / municipalities — licensing, CON, rate regulation, "
                "local EMS authority, 911 market structure.",
            )),
            QGroup("Incentive alignment / conflict", (
                "The system wants faster transport than payers will reimburse; the "
                "provider wants to avoid low-margin trips the hospital still needs.",
                "Case management prioritizes discharge completion while "
                "procurement prioritizes rate.",
                "Payer policy can unintentionally create hospital bottlenecks.",
            )),
        ),
        data_needed=(
            "Hospital + post-acute node universe (who the participants are, by "
            "geography).",
            "Part-B ambulance reimbursement and Medicaid managed-care penetration "
            "(the payer layer).",
            "Ambulance supplier universe (who actually runs transport).",
        ),
        visuals=(
            "Ecosystem map (patient flow = solid, money = dashed, dispatch / info "
            "= dotted).",
            "Incentive map (participants × goals / pain / decision rights / KPIs / "
            "economic exposure).",
            "RACI chart across the transport steps.",
            "Money-flow vs decision-flow diagram (payer of record ≠ the actor who "
            "most cares about performance).",
        ),
        answered_by=_links("study", "research_eco", "clinical"),
        connector_keys=("hospital_universe", "postacute_universe",
                        "part_b_ambulance", "nemt_managed_care",
                        "ambulance_suppliers"),
    ),
    Slide(
        num=10, slug="operating-models",
        title="Health-system POV — operating models", kind="content",
        prompt=("Characterize the range and penetration of insourced, outsourced, "
                "and hybrid transportation programs, and classify by how IFT is "
                "actually DELIVERED vs. how it is reimbursed."),
        main_question=("How do health systems actually deliver IFT, and how should "
                       "we classify their operating models?"),
        groups=(
            QGroup("The operating models", (
                "Fully insourced (owns fleet, employs crews, runs dispatch, bills "
                "payers).",
                "Fully outsourced (a third party supplies operations, staff, "
                "fleet, dispatch, possibly billing).",
                "Hybrid (internal fleet for priority / scheduled, vendors for "
                "overflow / nights / CCT / discharge).",
                "Preferred-vendor roster; spot-market / call-around; managed / "
                "brokered; dedicated partnership (dedicated units + SLAs + "
                "integration).",
            )),
            QGroup("Classification criteria — by delivery, not billing", (
                "Who owns the fleet, employs crews, dispatches, manages daily "
                "operations, is contractually responsible for performance, and "
                "bills payers?",
                "Are assets dedicated or shared? Is there a single accountable "
                "partner and enforceable SLAs?",
                "A system that owns a few trucks but outsources most volume is "
                "HYBRID / mostly outsourced — not insourced.",
            )),
            QGroup("Penetration questions", (
                "What share of hospitals use outsourced vs insourced vs hybrid?",
                "Does penetration vary by system size, region, urban/rural, "
                "academic/community, bed count, and transfer volume?",
                "Are larger systems more likely to prefer dedicated partnerships, "
                "and rural hospitals more dependent on local EMS?",
            )),
        ),
        data_needed=(
            "Ambulance supplier enrollment + market saturation (the supply-side "
            "structure by market).",
            "The health-system-biller insource-ceiling proxy (why claims "
            "undercount outsourced volume).",
            "Hospital universe by system size / geography (to read penetration).",
        ),
        visuals=(
            "Operating-model archetype matrix (model × fleet / staffing / dispatch "
            "/ billing / accountability / SLA / control).",
            "Operating-model maturity continuum (spot-market → roster → outsourced "
            "→ dedicated → insourced command center).",
            "Classification decision tree; penetration bar chart; model-fit heat "
            "map by health-system type.",
        ),
        answered_by=_links("markets", "study", "research_ops"),
        connector_keys=("ambulance_enrollment", "part_b_ambulance",
                        "ambulance_market_saturation", "hospital_universe"),
    ),
    Slide(
        num=11, slug="procurement",
        title="Health-system POV — procurement & vendor structures", kind="content",
        prompt=("Evaluate how health systems procure transportation — vendor "
                "structures, partnership models, contractual relationships, and "
                "operational workflows."),
        main_question=("How do health systems decide who provides IFT, and what "
                       "contract / workflow structures emerge from that decision?"),
        groups=(
            QGroup("What triggers procurement, and who is involved", (
                "Contract expiration, poor performance, ED-boarding / discharge "
                "crisis, consolidation, new freestanding EDs or service lines, "
                "cost pressure, labor shortage in an insourced fleet.",
                "Procurement, operations, ED, transfer center, case management, "
                "finance, revenue cycle, compliance, legal, and a C-suite sponsor "
                "— where does final authority sit vs where does the pain land?",
            )),
            QGroup("Vendor structures & partnership models", (
                "Single exclusive; primary + overflow; multi-vendor roster; vendor "
                "by geography / facility / acuity; internal + external; dedicated "
                "units for high-volume facilities.",
                "Transactional per-trip → preferred → exclusive → dedicated-unit "
                "→ system-wide strategic partnership → risk / performance-based.",
            )),
            QGroup("Contract terms & operational workflows that matter", (
                "Term, exclusivity, volume commitment, dedicated-fleet / minimum "
                "staffing, response-time SLAs, penalties / bonuses, escalators, "
                "reporting & data-sharing, surge coverage, facility-paid-trip "
                "rules.",
                "How staff request a trip, how dispatch confirms, ETA "
                "communication, escalation, cancellation handling, handoff "
                "documentation, and performance reporting.",
            )),
        ),
        data_needed=(
            "Target-contract review (exclusivity, SLAs, dedicated units, rate "
            "structure, escalators, facility-paid terms).",
            "Supplier market-saturation and enrollment (who is available to bid "
            "per market).",
        ),
        visuals=(
            "Procurement-journey swimlane (needs → RFP → evaluation → contracting "
            "→ implementation → operating review → renewal).",
            "Vendor-structure archetype chart (pros / cons / best-fit customer).",
            "Contract-model continuum overlaid with price risk / accountability / "
            "integration / switching cost.",
            "Example SLA dashboard; decision-maker influence map (influence × "
            "pain × budget control).",
        ),
        answered_by=_links("research_ops", "study", "markets"),
        connector_keys=("ambulance_market_saturation", "ambulance_enrollment",
                        "ambulance_suppliers"),
    ),
    Slide(
        num=12, slug="challenges",
        title="Health-system POV — operational challenges", kind="content",
        prompt=("Describe the operational challenges under current transportation "
                "models and the implications for health-system performance."),
        main_question=("What pain points do current transportation models create, "
                       "and why do they matter operationally and financially?"),
        groups=(
            QGroup("The pain-point categories", (
                "Availability / response delays (worst at discharge peaks, nights "
                "/ weekends, rural, behavioral).",
                "Fragmented vendor management (many vendors, no standard workflow, "
                "no comparable metrics, no accountability).",
                "Lack of visibility (no vehicle location, no ETA, no dashboard, no "
                "delay root-cause).",
                "Poor workflow integration (late / misclassified requests, "
                "duplicate documentation, claims issues).",
                "Capacity mismatch (predictable spikes un-staffed; scarce CCT; "
                "rural deadhead pulling local supply).",
                "Cost / reimbursement friction, labor / fleet constraints, and "
                "quality / compliance risk.",
            )),
            QGroup("Why it matters — the implications", (
                "Increases length-of-stay and avoidable bed days; reduces ED "
                "capacity and transfer acceptance; consumes staff time.",
                "Raises cost, weakens post-acute relationships, and reduces "
                "strategic flexibility.",
                "Creates avoidable clinical risk and payer friction.",
            )),
        ),
        data_needed=(
            "Inpatient occupancy time-series and hospital catchment (where "
            "boarding and blocked beds build).",
            "Aging-catchment and post-acute node density (the demand pressure and "
            "the destinations that fail late).",
            "Target delay / cancellation / SLA logs and incident reports (from the "
            "data room).",
        ),
        visuals=(
            "Pain-point heat map (operating model × availability / visibility / "
            "cost / accountability / CCT access / integration).",
            "Delay waterfall (request → vendor contacted → unit assigned → arrival "
            "→ loaded → handoff).",
            "Root-cause Pareto of delay reasons.",
            "Operational-impact chain (delayed transport → delayed discharge → "
            "occupied bed → ED boarding → lost capacity).",
            "Before / after dashboard (fragmented vs dedicated model).",
        ),
        answered_by=_links("study", "research_ops", "markets"),
        connector_keys=("hospital_capacity", "hospital_service_area",
                        "aging_demand", "postacute_universe"),
    ),
    Slide(
        num=13, slug="mmt-positioning",
        title="MMT positioning — model, services, footprint, customers",
        kind="content",
        prompt=("Detail MMT's operating model, service offerings, geographic "
                "footprint, and customer relationships relative to the broader IFT "
                "landscape."),
        main_question=("Where does MMT sit in the IFT market, and what makes its "
                       "model different from other provider types?"),
        groups=(
            QGroup("MMT operating model & services", (
                "Which services are actually provided (BLS / ALS / CCT / specialty "
                "/ behavioral / bariatric / discharge / dedicated units / "
                "long-distance)?",
                "What capacity is dedicated vs shared; what is the dispatch, "
                "labor, fleet, and billing model?",
                "Which offerings are core, differentiating, high-margin, and "
                "stickiness-driving?",
            )),
            QGroup("Geographic footprint & customer relationships", (
                "Which markets are dense, emerging, or single-customer dependent; "
                "how does the footprint align with health-system clusters and "
                "white space?",
                "Who are the largest customers (IDN / hospital / post-acute); are "
                "contracts system-wide, exclusive, long-term, with dedicated "
                "units?",
                "Retention, share-of-wallet, expansion within accounts, "
                "referenceability, and why customers chose MMT.",
            )),
            QGroup("MMT vs the broader landscape", (
                "Where is MMT more specialized / broader / denser / lacking vs "
                "traditional EMS, national players, regional privates, "
                "hospital-owned fleets, NEMT, CCT specialists, air?",
                "Is the advantage local, regional, or model-based; is it "
                "defensible on contracts, density, reputation, technology, or "
                "labor?",
            )),
        ),
        data_needed=(
            "MMT company data: trip / revenue by service, customer, facility; "
            "dedicated vs non-dedicated; payer mix; SLA / response / cancellation; "
            "fleet & crew by region; retention; win/loss.",
            "The county-by-MSA footprint model and its connector coverage.",
            "Hospital + post-acute density and aging catchment in the footprint "
            "(the demand it sits on).",
            "Rural mileage-add-on basis (the super-rural economics on long legs).",
        ),
        visuals=(
            "MMT capability map (MMT vs traditional EMS / regional / "
            "hospital-fleet / NEMT).",
            "Geographic footprint map (markets, customers, fleet hubs, white "
            "space, health-system density).",
            "Revenue / trip-mix stacked bars; customer-concentration bubble "
            "chart.",
            "MMT positioning matrix (dedicated-partnership depth × clinical "
            "acuity breadth).",
        ),
        answered_by=_links("mmt", "markets", "study_mmt"),
        connector_keys=("ambulance_suppliers", "hospital_universe",
                        "postacute_universe", "aging_demand", "rural_access",
                        "part_b_ambulance"),
    ),
    Slide(
        num=14, slug="dedicated-model",
        title="MMT positioning — dedicated partnership vs alternatives",
        kind="content",
        prompt=("Describe MMT's dedicated partnership model, contrasted with "
                "traditional EMS providers, regional transportation vendors, and "
                "insourced health-system programs."),
        main_question=("What exactly is MMT's dedicated partnership model, and why "
                       "is it different from the alternatives?"),
        groups=(
            QGroup("What 'dedicated partnership' means for MMT", (
                "Dedicated fleet / crews / dispatch line / account manager; "
                "contracted SLAs; transfer-center integration; joint operating "
                "reviews; custom per-facility workflows; fixed + variable "
                "pricing; multi-year, system-wide scope.",
            )),
            QGroup("How it differs from the alternatives", (
                "Traditional EMS: 911-first, units pulled for emergencies, public "
                "dispatch, little hospital-specific reporting.",
                "Regional vendors: sub-scale, thin acuity breadth, no formal SLAs "
                "or account management, owner-operator dependent.",
                "Insourced programs: fixed cost, labor / fleet / dispatch burden, "
                "no external billing scale, distraction from core hospital "
                "operations.",
            )),
            QGroup("Weaknesses to test, and the proof points that validate", (
                "Is dedicated capacity expensive / volume-dependent / weaker in "
                "rural markets / concentrated in a few customers?",
                "Proof: higher SLA compliance, lower delays / cancellations, "
                "reduced call-around, improved discharge timing, high renewal and "
                "account-expansion rates, wins after competitor underperformance.",
            )),
        ),
        data_needed=(
            "MMT SLA / response / cancellation / retention / expansion metrics vs "
            "market benchmarks.",
            "Competitor market-saturation and supplier density (who else could "
            "hold first-call).",
            "Hospital-origin density (the dedicated-capacity utilization base).",
        ),
        visuals=(
            "Four-model comparison table (MMT dedicated / traditional EMS / "
            "regional / insourced).",
            "Dedicated-model operating diagram (request → integrated dispatch → "
            "dedicated / shared allocation → handoff → reporting loop).",
            "Partnership-depth ladder (ad-hoc → preferred → primary → dedicated + "
            "SLAs → strategic patient-flow partner).",
            "Trade-off matrix (control × complexity transferred away); proof-point "
            "dashboard.",
        ),
        answered_by=_links("study_mmt", "markets", "research_comp"),
        connector_keys=("ambulance_market_saturation", "ambulance_suppliers",
                        "hospital_universe"),
    ),
    Slide(
        num=15, slug="strategic-capability",
        title="MMT positioning — transportation as a strategic capability",
        kind="content",
        prompt=("Illustrate MMT's role in advancing dedicated IFT partnerships and "
                "helping health systems recognize transportation as a strategic "
                "operational capability rather than a transactional vendor "
                "service."),
        main_question=("How does MMT help reframe IFT from a commodity vendor "
                       "service into a strategic health-system capability?"),
        groups=(
            QGroup("The shift to prove", (
                "Old view: transportation is a necessary cost and a vendor task, "
                "noticed only when it fails.",
                "New view: transportation is a patient-flow, capacity-management, "
                "and care-continuum capability that affects beds, ED throughput, "
                "discharge, specialty access, post-acute transitions, experience, "
                "and value-based performance.",
            )),
            QGroup("MMT's role in the shift", (
                "Dedicated / prioritized capacity, standardized workflows, reduced "
                "call-around, ETA transparency, system-level reporting, clinical "
                "acuity breadth, participation in operating reviews, and "
                "root-cause delay work.",
            )),
            QGroup("Evidence for and against", (
                "For: customers moved from multi-vendor to MMT partnership, "
                "expanded to system-wide, added dedicated units, and describe MMT "
                "as a strategic partner whose data leadership uses.",
                "Against: are contracts still per-trip, SLAs weak, technology "
                "adoption limited, or results non-repeatable across geographies?",
            )),
        ),
        data_needed=(
            "MMT before/after operating metrics at reference accounts (the proof "
            "the reframe is real).",
            "Inpatient occupancy and Part-B utilization (the throughput and "
            "reimbursement value at stake).",
            "Aging-catchment growth (the reason the capability matters more over "
            "time).",
        ),
        visuals=(
            "Transactional-to-strategic transformation visual (call-around / "
            "unknown ETA / no accountability → dedicated capacity / integrated "
            "dispatch / SLA visibility / system reporting).",
            "Strategic-capability pyramid (reliable execution → visibility / "
            "integration → patient-flow & system-strategy enablement).",
            "Health-system value bridge; MMT partnership flywheel; before-vs-after "
            "operating model.",
        ),
        answered_by=_links("study_mmt", "markets", "study"),
        connector_keys=("hospital_capacity", "part_b_ambulance", "aging_demand"),
    ),
)


def slide_architecture() -> SlideArchitecture:
    """The slide-by-slide diligence question architecture (SOW slides 1-15).
    Authored FRAMEWORK; the ``answered_by`` links and ``connector_keys`` resolve
    to live surfaces at read time. Never raises."""
    return SlideArchitecture(
        available=True, slides=_SLIDES,
        source_label=("Authored slide-by-slide diligence architecture (FRAMEWORK); "
                      "cross-links resolve to the sized IFT pages, connectors to "
                      "the real ift_connectors estate"),
        note=("Each slide is broken into its main diligence question, the "
              "sub-question tree beneath it, the data / evidence that would prove "
              "the point, the persuasive visuals, and WHERE the answer already "
              "lives on this platform."))


# ─────────────────────────────────────────────────────────────────────────────
# 2 — Cross-slide evidence plan (SOW "Data and Evidence Needed")
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class EvidenceSource:
    name: str
    intro: str
    items: Tuple[str, ...]
    our_surface: Tuple[Tuple[str, str], ...]     # (label, href)
    connector_keys: Tuple[str, ...]


@dataclass(frozen=True)
class EvidencePlan:
    available: bool
    sources: Tuple[EvidenceSource, ...] = ()
    source_label: str = ""


_EVIDENCE = (
    EvidenceSource(
        name="1. Company data from MMT",
        intro=("The spine of the company-specific proof — every quantitative claim "
               "on the MMT slides should trace here."),
        items=(
            "Trip volume and revenue by service type, customer, and facility.",
            "Dedicated vs non-dedicated volume; payer mix; facility-paid vs "
            "payer-paid.",
            "Average response time, SLA compliance, cancellation rate, delay "
            "reason codes, on-time pickup.",
            "Fleet and crew count by region; dedicated-unit utilization.",
            "Customer retention, contract renewal rate, average term, "
            "concentration, and account expansion.",
            "Win/loss reasons, pipeline by customer type, margin by service and "
            "geography.",
        ),
        our_surface=_links("mmt", "study_mmt"),
        connector_keys=("ambulance_suppliers", "rural_access"),
    ),
    EvidenceSource(
        name="2. Customer interviews",
        intro=("Primary research with the buyers and users — the ecosystem "
               "participant map frames who to interview and what to ask."),
        items=(
            "Targets: health-system COO, ED director, transfer-center and "
            "case-management leaders, procurement, CFO, post-acute network, plus "
            "existing / lost / competitor customers.",
            "How IFT is arranged today and the biggest pain points.",
            "Delay frequency and what happens when transport is late — who feels "
            "the impact.",
            "How vendors are evaluated, what would make them switch, and whether "
            "they'd pay more for reliability.",
            "What reporting they receive; whether transportation is strategic or "
            "transactional today.",
        ),
        our_surface=_links("study", "research_eco"),
        connector_keys=(),
    ),
    EvidenceSource(
        name="3. Contract review",
        intro=("The contract IS the deal, not the HCPCS code — the operating-model "
               "bands read the delivered-volume structure these contracts "
               "encode."),
        items=(
            "Exclusivity, SLAs, penalties, and dedicated-unit specifications.",
            "Rate structure (per-trip vs fixed + variable), volume commitments, "
            "escalators, and renewal options.",
            "Reporting / data-sharing requirements and termination clauses.",
            "Facility-paid-trip rules and service levels defined by acuity.",
        ),
        our_surface=_links("markets", "research_ops"),
        connector_keys=("ambulance_enrollment",),
    ),
    EvidenceSource(
        name="4. Market & competitor research",
        intro=("The competitive set by archetype and market — most alternatives "
               "are 911-heavy, mixed, or sub-scale."),
        items=(
            "Major competitors by region and archetype (EMS / IFT specialist / "
            "NEMT / hospital fleet).",
            "Services offered, customers served, and whether they offer dedicated "
            "IFT partnerships.",
            "CCT capability, multi-region reach, and consolidation posture.",
        ),
        our_surface=_links("markets", "study", "research_comp"),
        connector_keys=("ambulance_suppliers", "ambulance_market_saturation",
                        "ambulance_enrollment"),
    ),
    EvidenceSource(
        name="5. Health-system operating data",
        intro=("The operational proof that transportation failure is expensive — "
               "the demand and throughput data behind the pain."),
        items=(
            "Transfer volume and discharge volume requiring transport.",
            "ED-boarding time, bed-turnover time, and avoidable days.",
            "Discharge-before-noon, transfer-acceptance time, and post-acute "
            "placement timing.",
            "Staff time spent coordinating transport, transport-delay incident "
            "reports, and vendor performance logs.",
        ),
        our_surface=_links("clinical", "markets"),
        connector_keys=("hospital_capacity", "hospital_service_area",
                        "aging_demand", "postacute_universe"),
    ),
)


def evidence_plan() -> EvidencePlan:
    """The five cross-slide evidence sources, each mapped to the live surface and
    the connectors that supply the analog. Never raises."""
    return EvidencePlan(
        available=True, sources=_EVIDENCE,
        source_label=("Authored evidence plan (FRAMEWORK); each source mapped to "
                      "the live platform surface and the real connector datasets "
                      "that feed it"))


# ─────────────────────────────────────────────────────────────────────────────
# 3 — The best-overall visual package + the nuances not to miss
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class VisualRec:
    name: str
    purpose: str
    where: Tuple[Tuple[str, str], ...]     # (label, href) — where we render it


@dataclass(frozen=True)
class VisualPackage:
    available: bool
    visuals: Tuple[VisualRec, ...] = ()
    source_label: str = ""


_VISUALS = (
    VisualRec("IFT market-boundary decision tree",
              "Defines what is in / out of the market.",
              _links("study", "research_def")),
    VisualRec("Transport-category taxonomy matrix",
              "Compares IFT vs 911 / CCT / NEMT / air.",
              _links("study", "research_def")),
    VisualRec("Acuity-vs-urgency scatterplot",
              "Shows why IFT is distinct from the adjacent modes.",
              _links("study",)),
    VisualRec("Buyer-vs-payer map",
              "Explains the purchasing / reimbursement confusion (buyer ≠ payer).",
              _links("study", "research_ops")),
    VisualRec("Patient-journey / care-continuum map",
              "Shows where IFT appears across sites of care.",
              _links("clinical", "research_eco")),
    VisualRec("Ecosystem map (patient / money / decision flow)",
              "Explains participants and incentive conflict.",
              _links("study", "research_eco")),
    VisualRec("Health-system operating-model continuum",
              "Insourced vs outsourced vs hybrid vs dedicated.",
              _links("markets", "research_ops")),
    VisualRec("Procurement swimlane",
              "Shows how vendor selection actually happens.",
              _links("research_ops",)),
    VisualRec("Operational pain-point heat map",
              "Connects current models to health-system problems.",
              _links("study", "research_ops")),
    VisualRec("Dedicated-IFT flywheel",
              "Makes the sustainable-advantage case.",
              _links("markets", "study")),
    VisualRec("MMT capability / competitor comparison matrix",
              "Positions the company vs the field.",
              _links("study_mmt", "markets")),
    VisualRec("MMT footprint map",
              "Geographic positioning and white space.",
              _links("mmt", "markets")),
    VisualRec("Customer-concentration / relationship-depth bubble chart",
              "Reads customer quality and stickiness.",
              _links("mmt",)),
    VisualRec("Transactional-to-strategic transformation visual",
              "Carries the final narrative.",
              _links("study_mmt", "markets")),
    VisualRec("Proof-point dashboard",
              "Backs the MMT model with actual metrics.",
              _links("mmt", "markets")),
)


def visual_package() -> VisualPackage:
    """The 15 highest-leverage visuals, each mapped to where we already render (or
    would render) it. Never raises."""
    return VisualPackage(
        available=True, visuals=_VISUALS,
        source_label=("Authored visual-priority package (FRAMEWORK); 'where' links "
                      "resolve to the live pages that carry each visual"))


@dataclass(frozen=True)
class Nuance:
    title: str
    body: str


_NUANCES = (
    Nuance("Acuity alone does not define the market",
           "A hospital-to-hospital transfer can be clinically urgent yet still "
           "structurally different from 911 — the workflow, buyer, dispatcher, and "
           "economics differ."),
    Nuance("Buyer and payer are often different",
           "The health system cares most about vendor performance even when "
           "Medicare, Medicaid, or a commercial payer reimburses the trip."),
    Nuance("IFT is part logistics market, part healthcare-operations market",
           "The value is not just safe transport — it is throughput, transfer "
           "completion, discharge execution, and site-of-care movement."),
    Nuance("Dedicated capacity is both an advantage and a cost",
           "Prove WHEN health systems value reliability enough to pay for it."),
    Nuance("NEMT is adjacent but not the same",
           "NEMT is payer / broker-driven and lower acuity; IFT is facility-driven "
           "and care-transition embedded."),
    Nuance("Traditional EMS has ambulance capability but different priorities",
           "The question is not whether they CAN transport patients — it is whether "
           "they are built around health-system IFT workflows."),
    Nuance("Insourcing gives control but creates management burden",
           "Systems may own the problem without wanting to own fleet, labor, "
           "dispatch, compliance, and billing."),
    Nuance("The MMT story must be proven with metrics",
           "Don't just say 'dedicated partnership' — show dedicated units, SLAs, "
           "performance data, retention, expansion, and references."),
    Nuance("The strongest argument is operational, not size-based",
           "IFT matters because transportation failures create measurable "
           "health-system pain."),
    Nuance("The final positioning is 'infrastructure for care transitions'",
           "Not a commodity ambulance vendor, not a generic EMS provider — a "
           "specialized operating partner for patient movement across the "
           "continuum."),
)


def nuances() -> Tuple[Nuance, ...]:
    """The most important nuances the study must not miss. Never raises."""
    return _NUANCES


# ─────────────────────────────────────────────────────────────────────────────
# 4 — The connector evidence estate (reused from ift_connectors, keyed for the
#     per-slide chips + a grouped evidence table)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ConnectorEvidence:
    available: bool
    probes_by_key: Dict[str, Any] = field(default_factory=dict)
    probes: List[Any] = field(default_factory=list)
    summary: Optional[Any] = None
    source_label: str = ""


def connector_evidence() -> ConnectorEvidence:
    """Resolve the live connector estate once, keyed by probe ``key`` so the
    per-slide ``connector_keys`` render as real, linkable evidence chips. Degrades
    to ``available=False`` (empty) if the estate module is unavailable — never
    raises."""
    try:
        from . import ift_connectors as _ic
        probes = _ic.connector_estate_map()
        summ = _ic.estate_summary(probes)
    except Exception:  # noqa: BLE001
        return ConnectorEvidence(available=False)
    if not probes:
        return ConnectorEvidence(available=False)
    by_key = {p.key: p for p in probes}
    return ConnectorEvidence(
        available=True, probes_by_key=by_key, probes=list(probes), summary=summ,
        source_label=("Live ift_connectors estate — each dataset registered; the "
                      "hook flips to SOURCED once the estate is ingested, honest "
                      "GOV/ACADEMIC fallback offline"))


# ─────────────────────────────────────────────────────────────────────────────
# Rollup summary (for the page meta line)
# ─────────────────────────────────────────────────────────────────────────────
def diligence_summary() -> Dict[str, Any]:
    """Small counts for the page header / meta line. Never raises."""
    mt = master_tree()
    sa = slide_architecture()
    n_questions = 0
    for br in mt.branches:
        for g in br.groups:
            n_questions += len(g.questions)
    for sl in sa.slides:
        for g in sl.groups:
            n_questions += len(g.questions)
    ce = connector_evidence()
    return {
        "n_branches": len(mt.branches),
        "n_slides": len(sa.slides),
        "n_content_slides": sum(1 for s in sa.slides if s.kind == "content"),
        "n_questions": n_questions,
        "n_evidence_sources": len(evidence_plan().sources),
        "n_visuals": len(visual_package().visuals),
        "n_nuances": len(nuances()),
        "n_connectors": (ce.summary.n_connectors if ce.available and ce.summary
                         else 0),
        "n_connector_hooks": (ce.summary.total if ce.available and ce.summary
                              else 0),
    }
