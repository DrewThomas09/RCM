"""IFT Market Study — the investor market-study synthesis (SOW Dimension 1).

This is the "answer the study questions" layer: it stitches the offline IFT
spine (ift_geo / ift_analytics / ift_clinical_demand / ift_competitive /
ift_insourcing / ift_tracking / ift_moat) into the four SOW dimensions —

  1. Market context   — a taxonomy matrix distinguishing IFT from 911 / CCT /
     air / NEMT, and why dedicated IFT competes on different dimensions.
  2. IFT ecosystem    — the patient journey across sites of care and the
     participants that transport connects.
  3. Health-system POV — insourced / outsourced / hybrid operating models
     (classified by delivered VOLUME, not billing), procurement, and pain points.
  4. Company positioning — MMT (the deep-dive subject) and each competitor in
     the space, against the archetypes.

Design contract mirrors the rest of the IFT modules: frozen dataclasses, pure
functions that DEGRADE (return ``available=False``) and never raise, honesty
labels on every figure (GOV / SOURCED / ACADEMIC / ILLUSTRATIVE), and named
operators/systems carried as PUBLIC-WEB knowledge (labelled), not data figures.
The taxonomy/ecosystem/operating-model narrative content is authored market
knowledge (ACADEMIC/ILLUSTRATIVE); the quantitative anchors are reused verbatim
from the sized modules so nothing drifts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# Dimension 1 — Market context: the taxonomy matrix
# ─────────────────────────────────────────────────────────────────────────────
# The five ground-and-air transport modalities investors conflate, contrasted on
# the seven dimensions that actually differentiate them. Authored market
# knowledge (ACADEMIC/ILLUSTRATIVE) — the single most important market-education
# artifact, because indexing IFT to 911 or NEMT is the biggest sizing error.
_TAXONOMY_COLUMNS: Tuple[str, ...] = (
    "911 Emergency",
    "Interfacility (IFT)",
    "Critical Care Transport (CCT)",
    "Air Transport",
    "Wheelchair / Van / NEMT",
)
_IFT_COL = 1

_TAXONOMY_ROWS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Key use cases", (
        "Unscheduled response to a 911 call — scene-of-emergency pickup and "
        "transport to the nearest appropriate ED.",
        "Scheduled/urgent movement BETWEEN facilities — hospital→hospital "
        "up-transfers to higher acuity, and hospital→post-acute discharge legs.",
        "High-acuity interfacility transport with critical-care crew "
        "(ventilator, drips, balloon pump) — a specialty tier WITHIN IFT.",
        "Rotor/fixed-wing for time-critical or long-distance transfers where "
        "ground time is prohibitive.",
        "Non-emergency, no medical monitoring — wheelchair van / livery for "
        "ambulatory patients (dialysis runs, clinic visits).",
    )),
    ("Primary customers", (
        "The general public / bystanders (via the municipal 911 PSAP).",
        "Community hospitals, tertiary/quaternary systems, EDs, and "
        "post-acute facilities — the hospital orders and often pays.",
        "Tertiary transfer centers and referring hospitals needing "
        "ICU-level transport.",
        "Trauma/STEMI/stroke networks and rural referring hospitals.",
        "Medicaid programs, MA plans, and patients — a benefit, not a "
        "hospital operating function.",
    )),
    ("Acuity level", (
        "Full range, unknown at dispatch — triaged on scene.",
        "Stable-to-critical, KNOWN before dispatch — BLS/ALS/ALS2/SCT tiers.",
        "Critical only — the top of the IFT acuity ladder.",
        "Critical / time-critical.",
        "Ambulatory / stable — no monitoring or intervention en route.",
    )),
    ("Payer", (
        "Medicare/Medicaid/commercial + heavy municipal subsidy; high "
        "uncompensated care.",
        "Medicare AFS + commercial (OON leverage, ground is EXCLUDED from the "
        "No Surprises Act) + hospital facility contracts / subsidies.",
        "Same as IFT but the highest-RVU line (A0434 SCT ≈ 3.25× BLS).",
        "Medicare/commercial; AIR is the one modality COVERED by the No "
        "Surprises Act (balance-billing curbed).",
        "Medicaid NEMT benefit (42 CFR 431.53) — a separate federally-mandated "
        "program (~$3-5B/yr estimated).",
    )),
    ("Dispatch workflow", (
        "911 PSAP → nearest available unit → scene → nearest ED. Speed is "
        "everything.",
        "Hospital transfer center / case management → scheduled or ASAP → "
        "dedicated crew → destination bed. ETA reliability & bed-readiness win.",
        "Transfer center → specialty CCT crew staged for the mission.",
        "Transfer center / medical control → flight crew → landing zone.",
        "Broker / plan portal → van → residence↔clinic. Booked in advance.",
    )),
    ("Operating requirements", (
        "Coverage of a jurisdiction, sub-9-minute response, posted units, "
        "public-utility or fire-based model.",
        "DEDICATED capacity, transfer-center integration, tech/ETA visibility, "
        "revenue-cycle scale, chained loads for unit-hour utilization.",
        "Critical-care-credentialed crews, advanced equipment, 24/7 readiness.",
        "Aircraft, pilots, aviation regulatory overhead, weather ops.",
        "Wheelchair-accessible vehicles, low clinical requirement.",
    )),
    ("Contracting model", (
        "Municipal franchise / 911 zone contract (exclusive, low margin, "
        "subsidized).",
        "Health-system service contract — per-transport rates + availability "
        "retainer + exclusivity / first-call at the transfer center.",
        "Layered into the IFT contract or a specialty add-on.",
        "Hospital/network contract or independent membership model.",
        "State Medicaid / MA broker contract (capitated or per-trip).",
    )),
)

_WHY_DIFFERENT: Tuple[Tuple[str, str], ...] = (
    ("Customer is the hospital, not the patient",
     "IFT is ORDERED and often paid by the health system — it is a B2B "
     "operating service bought by transfer centers and case management, not a "
     "consumer 911 utility. The buyer, the sale cycle, and the KPI (bed "
     "throughput) are entirely different."),
    ("Reliability beats raw speed",
     "911 competes on response time to an unknown scene; IFT competes on ETA "
     "reliability, bed-readiness, and transfer-center workflow — the things "
     "that unblock a staffed bed and protect ED throughput."),
    ("Dedicated capacity vs shared 911 trucks",
     "A 911-heavy provider sheds scheduled IFT to protect emergency unit-hours; "
     "a dedicated IFT operator commits capacity to the system, so it is the "
     "reliable first-call — a structural, not a pricing, advantage."),
    ("Acuity + payer mix over volume",
     "IFT over-indexes on the high-RVU ALS2/SCT lines and commercial OON "
     "pricing; an interfacility book is worth a multiple of a 911-scene BLS "
     "book of the same trip count."),
    ("Density + revenue-cycle scale are the moat",
     "Profit is made by chaining loads (unit-hour utilization) and billing at "
     "scale — a purpose-built IFT platform with local density and RCM "
     "infrastructure structurally out-executes a subscale or 911-first vendor."),
)


@dataclass(frozen=True)
class TaxonomyMatrix:
    available: bool
    columns: Tuple[str, ...] = ()
    rows: Tuple[Tuple[str, Tuple[str, ...]], ...] = ()
    ift_col_index: int = _IFT_COL
    why_dedicated_different: Tuple[Tuple[str, str], ...] = ()
    source_label: str = ""
    note: str = ""


def taxonomy_matrix() -> TaxonomyMatrix:
    """The IFT-vs-911-vs-CCT-vs-air-vs-NEMT taxonomy matrix. Authored market
    knowledge; the payer/reimbursement rows name the real GOV anchors (AFS, No
    Surprises Act ground exclusion, Medicaid NEMT mandate) inside otherwise
    ACADEMIC/ILLUSTRATIVE narrative."""
    return TaxonomyMatrix(
        available=True,
        columns=_TAXONOMY_COLUMNS,
        rows=_TAXONOMY_ROWS,
        ift_col_index=_IFT_COL,
        why_dedicated_different=_WHY_DIFFERENT,
        source_label=("ACADEMIC / FRAMEWORK market taxonomy; GOV anchors named "
                      "inside (Medicare Ambulance Fee Schedule tiers, No Surprises "
                      "Act ground exclusion, Medicaid NEMT mandate 42 CFR 431.53)"),
        note=("The market definition IS the thesis: IFT is a hospital-ordered B2B "
              "operating service, distinct from consumer 911, specialty CCT (a tier "
              "within IFT), air, and the Medicaid NEMT benefit. Reading IFT against "
              "the whole-ambulance or NEMT market is the biggest sizing error."))


# ─────────────────────────────────────────────────────────────────────────────
# Dimension 2 — IFT ecosystem: the patient journey + participants
# ─────────────────────────────────────────────────────────────────────────────
_JOURNEY: Tuple[Tuple[str, str, str], ...] = (
    ("Community / referring hospital", "Origin",
     "A patient presents or deteriorates at a community or rural hospital or a "
     "freestanding ED that lacks the service line (PCI, stroke thrombectomy, "
     "trauma, NICU). IFT moves them UP to a capable center."),
    ("Emergency department", "Origin / throughput",
     "ED boarding is the pressure valve — every admitted patient waiting on a "
     "bed blocks a new arrival. Timely IFT (in and out) is what unblocks ED "
     "throughput and capacity."),
    ("Tertiary / quaternary hub", "Destination (up) / origin (down)",
     "The system-owned hub receives acute up-transfers, then REPATRIATES the "
     "recovered patient back down — each escalation implies a paired return leg."),
    ("Post-acute: IRF / LTACH", "Destination (step-down)",
     "Rehabilitation and long-term acute care take the recovering patient by "
     "stretcher — a scheduled, high-reliability discharge lane."),
    ("Skilled nursing facility (SNF)", "Destination + recurring",
     "The largest post-acute destination pool, plus recurring SNF→hospital and "
     "SNF→dialysis round-trips — the countable BLS/ALS discharge engine."),
    ("Home / hospice", "Discharge",
     "The end of the journey — comfort transitions and home discharge, the "
     "aging-driven tail that grows fastest."),
)

_PARTICIPANTS: Tuple[Tuple[str, str], ...] = (
    ("Health systems / hospitals",
     "The buyer and the demand generator — transfer centers order the mission "
     "and the system's referral network shapes the lanes. The core IFT customer."),
    ("Ambulance / IFT providers",
     "National EMS platforms, scaled regional privates, mom-and-pops, and "
     "hospital-owned programs — who actually runs the transport (see Dimension 4)."),
    ("Payers",
     "Medicare AFS (GOV) sets the floor; commercial pays a multiple (ground is "
     "OON-exposed, No Surprises Act does NOT cover ground); MA/Medicaid fill "
     "the rest — the payer mix drives revenue-per-transport."),
    ("Patients",
     "Move through the continuum; experience and safety are the human stakes, "
     "but the patient rarely chooses or pays for IFT."),
    ("Downstream / post-acute providers",
     "IRF, LTACH, SNF, HHA, hospice, dialysis — the destinations that make "
     "discharge transport a countable, recurring volume pool."),
)


@dataclass(frozen=True)
class Ecosystem:
    available: bool
    journey: Tuple[Tuple[str, str, str], ...] = ()
    participants: Tuple[Tuple[str, str], ...] = ()
    n_acute_scenarios: int = 0
    postacute_destinations: int = 0
    transfer_matrix: List[Dict[str, Any]] = field(default_factory=list)
    source_label: str = ""
    note: str = ""


def ecosystem() -> Ecosystem:
    """The IFT ecosystem — the patient journey across sites of care and the
    participants transport connects. Reuses the SOURCED clinical spine (the
    acute-transfer matrix + real post-acute destination counts) for the
    quantitative anchors; degrades to the authored journey/participants if the
    clinical module is unavailable."""
    n_scen = 0
    n_dest = 0
    matrix: List[Dict[str, Any]] = []
    try:
        from . import ift_clinical_demand as _cd
        summ = _cd.registry_summary()
        n_scen = int(summ.get("n_conditions", 0) or 0)
        supply = _cd.destination_supply()
        n_dest = int(supply.get("national", 0) or 0) if isinstance(supply, dict) else 0
        matrix = _cd.transfer_matrix() or []
    except Exception:  # noqa: BLE001
        pass
    return Ecosystem(
        available=True, journey=_JOURNEY, participants=_PARTICIPANTS,
        n_acute_scenarios=n_scen, postacute_destinations=n_dest,
        transfer_matrix=matrix,
        source_label=("Authored care-continuum map; SOURCED anchors = "
                      "ift_clinical_demand acute-scenario registry + real CMS "
                      "post-acute destination counts"),
        note=("IFT is the connective tissue of the acute→post-acute continuum: "
              "every escalation up-transfer and every discharge step-down is a "
              "mission, and the aging-driven post-acute tail is the volume story."))


# ─────────────────────────────────────────────────────────────────────────────
# Dimension 3 — Health-system POV: operating models, procurement, pain points
# ─────────────────────────────────────────────────────────────────────────────
_PROCUREMENT: Tuple[Tuple[str, str], ...] = (
    ("Vendor structure",
     "Single dedicated partner vs a fragmented pool of privates vs an owned "
     "fleet — the structure determines reliability and switching cost."),
    ("Partnership model",
     "Transactional per-trip vendor vs a dedicated, workflow-integrated partner "
     "with an availability retainer and shared throughput KPIs."),
    ("Contractual relationship",
     "Per-transport rates + availability/subsidy retainer + exclusivity / "
     "first-call at the transfer center + CPI escalators — the contract IS the "
     "deal, not the HCPCS code."),
    ("Operational workflow",
     "Embedded scheduling coordinators, transfer-center EHR integration, and "
     "ETA/reporting visibility — the integration depth that makes the incumbent "
     "the default first-call."),
)

_PAIN_POINTS: Tuple[Tuple[str, str], ...] = (
    ("Late transports & poor ETAs",
     "Unreliable pickup windows leave admitted patients waiting — the #1 "
     "throughput complaint."),
    ("Blocked beds & ED boarding",
     "A patient who can't move OUT blocks the bed a new admission needs; "
     "transport delay is capacity loss."),
    ("Fragmented vendors",
     "Juggling multiple mom-and-pop privates with no single accountable partner "
     "and inconsistent quality."),
    ("Lack of transparency",
     "No real-time status, no ETA, no reporting — the system flies blind on its "
     "own patient movement."),
    ("Staff & capacity strain",
     "Nurses and case managers spend time chasing rides; 911-first vendors shed "
     "scheduled IFT when emergencies spike."),
)


@dataclass(frozen=True)
class OperatingModels:
    available: bool
    bands: List[Any] = field(default_factory=list)           # from ift_insourcing
    biller_ceiling_pct: Optional[Tuple[float, float, float]] = None
    procurement: Tuple[Tuple[str, str], ...] = ()
    pain_points: Tuple[Tuple[str, str], ...] = ()
    classification_note: str = ""
    source_label: str = ""
    note: str = ""


def operating_models() -> OperatingModels:
    """The health-system POV — insourced / outsourced / hybrid operating models
    (classified by delivered transport VOLUME, not billing/asset ownership),
    how systems procure, and the pain points under current models. Reuses the
    ift_insourcing framework + biller ceiling verbatim; degrades gracefully."""
    bands: List[Any] = []
    ceiling: Optional[Tuple[float, float, float]] = None
    try:
        from . import ift_insourcing as _ins
        fr = _ins.insourcing_framework()
        if fr.available:
            bands = list(fr.bands)
        bp = _ins.biller_proxy()
        if getattr(bp, "available", False):
            # BillerProxy exposes ceiling_low/central/high (there is no single
            # ``insource_ceiling`` attribute) — assemble the (low, central, high)
            # tuple the operating-model view wants.
            ceiling = (bp.ceiling_low, bp.ceiling_central, bp.ceiling_high)
    except Exception:  # noqa: BLE001
        pass
    return OperatingModels(
        available=True, bands=bands, biller_ceiling_pct=ceiling,
        procurement=_PROCUREMENT, pain_points=_PAIN_POINTS,
        classification_note=(
            "CLASSIFY BY VOLUME, NOT ASSETS: a system that owns a few ambulances "
            "but outsources most of its interfacility volume is HYBRID / mostly "
            "outsourced, not insourced. Prior studies overstated insourcing by "
            "reading asset ownership; the honest read is the share of delivered "
            "TRANSPORT VOLUME, upper-bounded by the health-system-biller proxy."),
        source_label=("Authored operating-model + procurement framework; "
                      "quantitative bands + biller ceiling reused from "
                      "ift_insourcing (FRAMEWORK, GOV/SOURCED anchored)"),
        note=("The delivered-vs-reimbursed distinction is the crux: insourcing is "
              "measured by who actually runs the volume, not who bills or owns a "
              "truck. Most hospital IFT is contestable because hospitals rarely "
              "run enough owned capacity to cover their real transfer demand."))


# ─────────────────────────────────────────────────────────────────────────────
# Dimension 4 — Company positioning: MMT (subject) + the competitive field
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class CompanyProfile:
    slug: str
    name: str
    archetype: str                       # matches ift_competitive archetype names
    is_subject: bool                     # True only for MMT (the deep-dive)
    hq: str
    footprint: str
    operating_model: str
    services: Tuple[str, ...]
    customer_relationships: str
    dedicated_vs_ems: str
    strategic_role: str
    mmt_contrast: str                    # how MMT stacks vs this player
    footprint_markets: Tuple[str, ...] = ()   # our metros where the operator appears
    names_basis: str = ("Company facts are PUBLIC-WEB / company-web knowledge, "
                        "named honestly — not a data-derived figure.")


# Operator name tokens → the study company slug, so we can attach the footprint
# (which of our 20 metros each operator appears in) as a registry read over the
# PUBLIC-WEB operator/anchor names in ift_geo — a public-web fact, not a data figure.
_OPERATOR_TOKENS: Dict[str, Tuple[str, ...]] = {
    "mmt": ("midwest medical transport", "mmt"),
    "amr_gmr": ("amr", "gmr", "global medical response", "rural/metro"),
    "superior": ("superior air-ground", "superior air", "superior ambulance"),
    "ameripro": ("ameripro", "priority medical transport"),
    "ryan_brothers": ("ryan brothers",),
    "acadian": ("acadian",),
    "priority": ("priority ambulance",),
    "physicians": ("physicians ambulance",),
    "bell": ("bell ambulance",),
    # Ground hospital-owned programs only — air brands ('*med flight', 'airmed')
    # are OUT of the ground-IFT TAM, and 'mayo' alone would false-match a mere
    # branding affiliation, so match the actual 'Mayo Clinic Ambulance' operator.
    "hospital_owned": ("allina", "cleveland clinic", "north memorial",
                       "children's", "mayo clinic ambulance"),
}

_COMPANIES: Tuple[CompanyProfile, ...] = (
    CompanyProfile(
        slug="mmt", name="Midwest Medical Transport (MMT)",
        archetype="Dedicated outsourced IFT specialist", is_subject=True,
        hq="Omaha, Nebraska",
        footprint="Nebraska core (Omaha, Lincoln, North Platte, Columbus, "
                  "Grand Island / Kearney) with a dedicated-IFT operating model.",
        operating_model="Dedicated interfacility partner — committed ambulance "
                        "capacity, its own dispatch/technology and revenue cycle, "
                        "aligned to health-system transfer-center workflow under "
                        "long-term partnerships (the reference for the archetype).",
        services=("Dedicated BLS / ALS / CCT interfacility capacity",
                  "Transfer-center-integrated dispatch + ETA visibility",
                  "In-house revenue cycle / billing at scale",
                  "Availability retainer / first-call reliability"),
        customer_relationships="First-call / share-of-wallet partnerships with "
                               "the anchor systems' transfer centers across its "
                               "Nebraska footprint.",
        dedicated_vs_ems="Purpose-built for IFT — capacity is committed to the "
                         "system, NOT shed to protect 911 unit-hours like a "
                         "911-heavy provider.",
        strategic_role="Advances the 'transportation as a strategic operating "
                       "capability' thesis — the outsourced patient-movement "
                       "partner, not a transactional ride vendor.",
        mmt_contrast="This is the subject — the dedicated model every other "
                     "archetype is contrasted against.",
    ),
    CompanyProfile(
        slug="amr_gmr", name="AMR / Global Medical Response (GMR)",
        archetype="National EMS platform", is_subject=False,
        hq="National (Colorado)",
        footprint="Nationwide 911 + IFT; in-footprint at Kansas City and Wichita "
                  "(won Wesley/HCA interfacility).",
        operating_model="National 911-anchored platform; IFT competes for the "
                        "same trucks and is rarely the dedicated priority.",
        services=("911 emergency response", "Interfacility + CCT",
                  "National contracting scale"),
        customer_relationships="National MSAs and system relationships (e.g. HCA "
                               "pre-commits volume to GMR); breadth over "
                               "market-level dedication.",
        dedicated_vs_ems="911-heavy — scheduled IFT is deprioritized when "
                         "emergency demand spikes.",
        strategic_role="Scale incumbent; the default when a system wants one "
                       "national vendor, not a dedicated local partner.",
        mmt_contrast="MMT wins on dedicated capacity + local density + "
                     "transfer-center integration where GMR's 911-first model "
                     "cedes reliability on scheduled IFT.",
    ),
    CompanyProfile(
        slug="superior", name="Superior Air-Ground Ambulance",
        archetype="Scaled regional private", is_subject=False,
        hq="Elmhurst, Illinois (Midwest regional)",
        footprint="Midwest regional; in-footprint at Columbus OH (Mount Carmel "
                  "'Home Network', embedded coordinators) and Dayton.",
        operating_model="Scaled regional private with deep single-system "
                        "workflow integration (embedded scheduling coordinators).",
        services=("Regional BLS / ALS / CCT IFT", "Embedded transfer coordination"),
        customer_relationships="Textbook workflow-integration moat at Mount "
                               "Carmel — embedded coordinators = default first-call.",
        dedicated_vs_ems="Dedicated IFT-capable within its region; the closest "
                         "archetype to MMT's model.",
        strategic_role="Proof that workflow integration + embeddedness is the "
                       "durable moat — the model MMT extends into its markets.",
        mmt_contrast="Same dedicated-integration playbook; the contest is which "
                     "operator holds first-call and local density per metro.",
    ),
    CompanyProfile(
        slug="ameripro", name="AmeriPro Health",
        archetype="Scaled regional private", is_subject=False,
        hq="Regional (multi-state roll-up)",
        footprint="Nebraska/Midwest roll-up; in-footprint at Lincoln, North "
                  "Platte (acquired Priority Medical Transport), Columbus NE, "
                  "Grand Island / Kearney.",
        operating_model="Regional roll-up acquiring incumbency market by market "
                        "— a direct consolidation competitor to MMT in Nebraska.",
        services=("Regional IFT + 911 in some markets", "Roll-up of local privates"),
        customer_relationships="Building first-call via acquisition of the "
                               "incumbent (e.g. Priority in North Platte).",
        dedicated_vs_ems="Mixed — dedicated IFT plus some 911; consolidation-led.",
        strategic_role="The consolidation threat — buys incumbency rather than "
                       "building it.",
        mmt_contrast="Head-to-head roll-up rivalry in Nebraska; the battleground "
                     "is who locks the system transfer-center first-call.",
    ),
    CompanyProfile(
        slug="ryan_brothers", name="Ryan Brothers Ambulance",
        archetype="Scaled regional private", is_subject=False,
        hq="Madison, Wisconsin",
        footprint="Dominant Madison-area private; IFT to a 100-mile radius.",
        operating_model="60-year first-call incumbency + critical-care capability "
                        "+ wide coverage density.",
        services=("Regional BLS / ALS / CCT IFT", "Critical-care transport"),
        customer_relationships="Multi-decade system relationships — a deep "
                               "incumbency moat.",
        dedicated_vs_ems="Dedicated regional IFT provider.",
        strategic_role="The acquirable regional-private archetype — the asset a "
                       "platform buys, not a system fleet.",
        mmt_contrast="Illustrates the durability of 60-year first-call — the same "
                     "relationship depth MMT builds in Nebraska.",
    ),
    CompanyProfile(
        slug="physicians", name="Physicians Ambulance",
        archetype="Scaled regional private", is_subject=False,
        hq="Northeast Ohio",
        footprint="NE-Ohio hospital-partnered discharge/skilled; in-footprint at "
                  "Cleveland.",
        operating_model="Hospital-partnered regional private focused on the "
                        "routine BLS/ALS discharge + SNF back-transfer book.",
        services=("Discharge + skilled-nursing IFT", "Hospital-partnered model"),
        customer_relationships="Partnered with NE-Ohio systems for the "
                               "outsourced routine book beneath the insourced CCT.",
        dedicated_vs_ems="Dedicated to the routine interfacility/discharge slice.",
        strategic_role="Shows the winnable SAM beneath insourced-top systems "
                       "(Cleveland Clinic / UH own the high-acuity CCT).",
        mmt_contrast="Same 'win the routine discharge book' strategy MMT runs "
                     "where systems insource only the top tier.",
    ),
    CompanyProfile(
        slug="bell", name="Bell Ambulance",
        archetype="Scaled regional private", is_subject=False,
        hq="Milwaukee, Wisconsin",
        footprint="IFT-specialized Milwaukee private (with Curtis, Paratech in a "
                  "fragmented pool).",
        operating_model="IFT-specialized private in a fragmented, outsourced "
                        "market with no single system-wide first-call.",
        services=("IFT-specialized BLS / ALS", "Milwaukee metro density"),
        customer_relationships="One of several privates the systems contract; the "
                               "market is contested, not locked.",
        dedicated_vs_ems="Dedicated IFT specialist.",
        strategic_role="The prime roll-up target in a fragmented dense-urban "
                       "market — density without an entrenched first-call.",
        mmt_contrast="The type of dense-urban, un-consolidated market a dedicated "
                     "platform like MMT targets for entry.",
    ),
    CompanyProfile(
        slug="acadian", name="Acadian Ambulance",
        archetype="National EMS platform", is_subject=False,
        hq="Lafayette, Louisiana (employee-owned)",
        footprint="Large multi-state ESOP; 911 + IFT + air.",
        operating_model="Scaled employee-owned platform spanning 911, IFT, and "
                        "air — breadth model.",
        services=("911", "Interfacility + CCT", "Air medical"),
        customer_relationships="Regional scale relationships across its "
                               "multi-state footprint.",
        dedicated_vs_ems="Mixed 911 / IFT / air.",
        strategic_role="A scaled comparable illustrating the breadth (vs "
                       "dedicated-IFT-depth) strategic choice.",
        mmt_contrast="Breadth-across-modalities vs MMT's dedicated-IFT depth in "
                     "a concentrated footprint.",
    ),
    CompanyProfile(
        slug="hospital_owned", name="Hospital-owned programs (insourced)",
        archetype="Hospital-owned program", is_subject=False,
        hq="Various health systems",
        footprint="Allina EMS (Twin Cities, ~34k interfacility requests/yr), "
                  "Cleveland Clinic CCT, North Memorial, Children's peds CCT.",
        operating_model="System-owned fleets that run their own (usually "
                        "high-acuity) interfacility transport — the insource "
                        "ceiling.",
        services=("Owned CCT / interfacility fleets", "Sometimes sold to "
                  "non-system facilities (Allina)"),
        customer_relationships="Captive intra-system volume; a closed door to "
                               "outsourced operators for the insourced slice.",
        dedicated_vs_ems="Insourced — not for sale; the residual (routine "
                         "discharge / SNF back-transfer) is the contestable SAM.",
        strategic_role="Defines the insource ceiling — but even here most systems "
                       "own only the top tier and outsource the routine volume.",
        mmt_contrast="The 'closed door' archetype; MMT competes for the "
                     "outsourced residual these systems do NOT run themselves.",
    ),
)

_BY_SLUG: Dict[str, CompanyProfile] = {c.slug: c for c in _COMPANIES}
_DEFAULT_COMPANY = "mmt"


def _footprint_for(slug: str) -> Tuple[str, ...]:
    """Which of our 20 metros this operator appears in — a registry read over the
    PUBLIC-WEB operator/anchor names in ift_geo (NOT vendored CMS data, so NOT a
    SOURCED figure). Degrades to () if geo is unavailable."""
    tokens = _OPERATOR_TOKENS.get(slug, ())
    if not tokens:
        return ()
    hits: List[str] = []
    try:
        from . import ift_geo as _geo
        for md in _geo.MARKETS:
            blob = " ".join(md.named_operators).lower() + " " \
                + " ".join(md.anchor_systems).lower() + " " \
                + md.insource_read.lower()
            if any(tok in blob for tok in tokens):
                hits.append(md.name)
    except Exception:  # noqa: BLE001
        return ()
    return tuple(hits)


def all_companies() -> List[CompanyProfile]:
    """Every company in the study, MMT first (the subject), each with its
    SOURCED in-footprint metros attached."""
    out: List[CompanyProfile] = []
    for c in _COMPANIES:
        fp = _footprint_for(c.slug)
        out.append(CompanyProfile(**{**c.__dict__, "footprint_markets": fp}))
    return out


def company_profile(slug: Optional[str]) -> CompanyProfile:
    """One company's profile (default MMT). Unknown slug → MMT, so the page never
    404s on a bad ``?company=`` value."""
    key = (slug or _DEFAULT_COMPANY).strip().lower()
    base = _BY_SLUG.get(key, _BY_SLUG[_DEFAULT_COMPANY])
    return CompanyProfile(**{**base.__dict__,
                             "footprint_markets": _footprint_for(base.slug)})


@dataclass(frozen=True)
class CompanyPositioning:
    available: bool
    subject: CompanyProfile
    is_subject_mmt: bool
    field_: List[CompanyProfile] = field(default_factory=list)
    mmt_positioning: Any = None          # ift_competitive.mmt_positioning()
    archetypes: Any = None               # ift_competitive.competitive_archetypes()
    source_label: str = ""
    note: str = ""


def company_positioning(slug: Optional[str] = None) -> CompanyPositioning:
    """Dimension 4 for a chosen company (default MMT — the deep-dive). Carries the
    full competitive field, and MMT's structured positioning pillars +
    archetype-contrast from ift_competitive. Degrades but never raises."""
    subj = company_profile(slug)
    mp = None
    arch = None
    try:
        from . import ift_competitive as _c
        mp = _c.mmt_positioning()
        arch = _c.competitive_archetypes()
    except Exception:  # noqa: BLE001
        pass
    return CompanyPositioning(
        available=True, subject=subj, is_subject_mmt=(subj.slug == "mmt"),
        field_=all_companies(), mmt_positioning=mp, archetypes=arch,
        source_label=("Authored company positioning; MMT pillars + archetype "
                      "contrast reused from ift_competitive; footprints are a "
                      "registry read over ift_geo's PUBLIC-WEB operator names; all "
                      "company facts PUBLIC-WEB, labelled"),
        note=("MMT is the deep-dive subject — the dedicated outsourced IFT "
              "partner. Every other player is positioned against that model: "
              "national 911-first platforms, scaled regional privates, and "
              "insourced hospital programs."))


def study_summary() -> Dict[str, Any]:
    """A tiny roll-up for the page KPI strip / meta line — how much of the study
    is wired. Never raises."""
    n_companies = len(_COMPANIES)
    tm = taxonomy_matrix()
    return {
        "n_taxonomy_modalities": len(tm.columns) if tm.available else 0,
        "n_taxonomy_dimensions": len(tm.rows) if tm.available else 0,
        "n_companies": n_companies,
        "subject": "Midwest Medical Transport (MMT)",
    }
