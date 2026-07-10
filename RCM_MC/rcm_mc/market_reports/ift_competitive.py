"""IFT competitive landscape — the archetypes MMT actually competes against, the
per-metro competitive structure, and MMT's relative positioning as the dedicated
outsourced interfacility-transport (IFT) partner.

The SOW's competitive question is deliberately framed around a *whitespace*
thesis: MMT is NOT up against a thick field of pure-play IFT platforms. The
ground-IFT alternatives are almost all one of four things — a national EMS
platform that is 911-heavy and treats IFT as one line, a scaled regional private
that is geographically boxed and often 911-mixed, a subscale mom-and-pop local,
or a hospital-owned captive program. This module names those archetypes, sorts
every operator our ift_geo registry already knows into them, and reads each
metro's contestability — so the report can show that the dedicated-outsourced-IFT
lane MMT occupies is thinly contested.

What is PUBLIC-WEB knowledge (named honestly, never fabricated): every operator
and health-system NAME. They are REUSED verbatim from ``ift_geo.MARKETS`` —
``named_operators`` and ``anchor_systems`` — which the brief already curated from
public/company web. No operator is invented here and no contract exclusivity or
per-transport rate is asserted. Names carry a "public/company web, named
honestly" note, never a data chip.

What is SOURCED (computed from our vendored estate via ift_geo): the per-archetype
COUNT of footprint metros an archetype appears in, and every per-metro density
figure (nodes / density tier), which come straight from ``ift_geo.metro_structure``
(CMS hospital_coords + HCRIS + post-acute rolls).

What is ILLUSTRATIVE (modeled, basis named): the archetype scale magnitudes and
the per-metro contestability read. The contestability score reuses the
ILLUSTRATIVE realistically-serviceable share s(m) that ``ift_analytics.sam_formula``
already keys to each metro's insource-vs-outsource archetype — a higher s(m) IS a
more contestable book — so the competitive read and the sizing model agree rather
than diverging.

Honesty rule (the load-bearing invariant): a mixed result LEADS with its dominant
honest basis (ILLUSTRATIVE for the analytic reads) and names the SOURCED / PUBLIC-WEB
anchors inside; ``source_label`` uses " · " to separate the basis chip from the
descriptive remainder. Every figure-bearing record also carries a ``basis`` in
{GOV, SOURCED, ACADEMIC, ILLUSTRATIVE}.

Design contract (mirrors ``ift_analytics`` / ``ift_geo``): pure, no runtime
network, cached, frozen result records, and every function **degrades — never
raises** — returning ``available=False`` with a ``source_label`` so the report /
page renders an honest label instead of crashing.
"""
from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ── Honesty-basis vocabulary (mirrors the market_reports contract) ───────────
LABEL_GOV = "GOV"
LABEL_SOURCED = "SOURCED"
LABEL_ACADEMIC = "ACADEMIC"
LABEL_ILLUSTRATIVE = "FRAMEWORK"   # renamed 2026-07-10: a stated analytical scaffold, not "illustrative"
_BASES = (LABEL_GOV, LABEL_SOURCED, LABEL_ACADEMIC, LABEL_ILLUSTRATIVE)

# Operator / health-system NAMES are public-web knowledge, not a data figure —
# they carry this note, never a SOURCED/GOV data chip.
PUBLIC_WEB_NOTE = "PUBLIC-WEB · public/company web, named honestly"

# ── Archetype keys + the two context tags (municipal / air are not addressable
# ground-IFT competitors, but they show up in the registry and must classify
# honestly rather than be forced into a competitor bucket). ──────────────────
ARCH_NATIONAL = "national_ems"
ARCH_REGIONAL = "scaled_regional"
ARCH_MOMPOP = "mom_and_pop"
ARCH_HOSPITAL = "hospital_owned"
ARCH_DEDICATED = "dedicated_ift_specialist"     # MMT's own category
TAG_MUNICIPAL = "municipal_911"                 # public 911 / fire (context)
TAG_AIR = "air_excluded"                         # air medical (out of ground TAM)

# Ordered display of the primary competitive archetypes (MMT's own lane last).
_ARCHETYPE_ORDER: Tuple[str, ...] = (
    ARCH_NATIONAL, ARCH_REGIONAL, ARCH_MOMPOP, ARCH_HOSPITAL, ARCH_DEDICATED)

_ARCHETYPE_LABEL: Dict[str, str] = {
    ARCH_NATIONAL: "National EMS platform",
    ARCH_REGIONAL: "Scaled regional private",
    ARCH_MOMPOP: "Mom-and-pop local private",
    ARCH_HOSPITAL: "Hospital-owned program",
    ARCH_DEDICATED: "Dedicated outsourced IFT specialist",
    TAG_MUNICIPAL: "Municipal 911 / public (context)",
    TAG_AIR: "Air medical (excluded from ground TAM)",
}


def archetype_label(tag: str) -> str:
    """Human label for a classification tag (or the raw tag if unknown)."""
    return _ARCHETYPE_LABEL.get(tag, tag)


# ── Operator classifier ──────────────────────────────────────────────────────
# First matching rule wins. ORDER IS LOAD-BEARING: MMT is matched before
# anything else (it is the reference subject); air/municipal public providers are
# pulled out before the private buckets; and "AmeriPro" is matched before the
# national "Priority" patterns because ift_geo's "Priority Medical Transport
# (…acquired by AmeriPro)" is an AmeriPro tuck-in, not the national Priority
# Ambulance platform. Matching is case-insensitive substring on the raw ift_geo
# operator string (which carries the disambiguating parenthetical).
_CLASSIFY_RULES: Tuple[Tuple[Tuple[str, ...], str], ...] = (
    (("midwest medical transport", "(mmt", " mmt)"), ARCH_DEDICATED),
    (("excluded from tam", "lifeline", "medtrans"), TAG_AIR),
    (("fire department", "fire & rescue", "fire dept", "fire-based",
      "fire (911", "municipal city ems", "metro ems", "med-act", "county ems",
      "des moines fire", "lincoln fire", "omaha fire", "madison fire"),
     TAG_MUNICIPAL),
    (("allina", "fairview", "north memorial", "mayo clinic ambulance",
      "mercyone", "hospital-owned", "hospital-based", "owned fleet"),
     ARCH_HOSPITAL),
    # AmeriPro (scaled regional roll-up) BEFORE the national Priority patterns.
    (("ameripro",), ARCH_REGIONAL),
    (("amr", "gmr", "global medical", "acadian", "priority ambulance",
      "priority brand", "priority medical transport", "procarent",
      "yellow ambulance"), ARCH_NATIONAL),
    (("superior air", "ryan brothers", "physicians ambulance", "bell ambulance"),
     ARCH_REGIONAL),
)


def classify_operator(raw: str) -> str:
    """Classify one ift_geo operator string into an archetype / context tag.

    Falls back to ``ARCH_MOMPOP`` for an unrecognised named local private — the
    honest default for a single-market private that isn't a known national,
    regional, hospital-owned, municipal, or air provider. Never raises."""
    s = (raw or "").strip().lower()
    if not s:
        return ARCH_MOMPOP
    for patterns, tag in _CLASSIFY_RULES:
        if any(p in s for p in patterns):
            return tag
    return ARCH_MOMPOP


def _clean_name(raw: str) -> str:
    """The display operator name: the ift_geo string up to its descriptive
    parenthetical (e.g. 'AmeriPro Health (Lancaster County)' → 'AmeriPro
    Health'). Keeps the real ift_geo name — never invents one."""
    name = (raw or "").split(" (")[0].strip()
    return name or (raw or "").strip()


@functools.lru_cache(maxsize=1)
def _markets():
    """The ift_geo MARKETS tuple, or () if ift_geo is unreadable offline."""
    try:
        from . import ift_geo
        return ift_geo.MARKETS
    except Exception:  # noqa: BLE001 — degrade, never raise
        return tuple()


@functools.lru_cache(maxsize=1)
def _serviceable_share_by_metro() -> Dict[str, float]:
    """``{metro_name: s(m)}`` — the ILLUSTRATIVE realistically-serviceable share
    that ``ift_analytics.sam_formula`` keys to each metro's insource archetype.

    Reused as the contestability score (higher s(m) ⇒ more of the book is
    winnable by an outsourced operator) so the competitive read and the sizing
    model stay consistent. Returns ``{}`` on any failure so callers degrade to
    the insource-class-only tier."""
    try:
        from . import ift_analytics
        sam = ift_analytics.sam_formula()
        if not sam.available:
            return {}
        return {r.name: float(r.serviceable_share) for r in sam.rows}
    except Exception:  # noqa: BLE001
        return {}


# ── (1) Competitive archetypes ───────────────────────────────────────────────
@dataclass(frozen=True)
class Archetype:
    """One competitive archetype MMT faces (or, for the last, MMT's own lane).

    ``example_operators`` are REUSED from ift_geo's ``named_operators`` (real
    footprint presences, PUBLIC-WEB); ``n_footprint_metros`` is a SOURCED count
    of metros the archetype appears in; ``scale_magnitude`` is ILLUSTRATIVE."""
    key: str
    name: str
    description: str
    ift_posture: str
    scale_magnitude: str
    pros: Tuple[str, ...]
    cons: Tuple[str, ...]
    example_operators: Tuple[str, ...]      # PUBLIC-WEB, from ift_geo
    n_footprint_metros: int                 # SOURCED (ift_geo appearance count)
    mmt_advantage: str
    scale_basis: str = LABEL_ILLUSTRATIVE
    appearances_basis: str = LABEL_SOURCED
    names_basis: str = PUBLIC_WEB_NOTE
    basis: str = LABEL_ILLUSTRATIVE          # dominant honest basis for the record
    source_label: str = ""


@dataclass
class ArchetypeSet:
    available: bool
    archetypes: List[Archetype] = field(default_factory=list)
    source_label: str = ""
    note: str = ""


# Authored archetype content (pros/cons/posture/advantage) — real ground-IFT
# domain knowledge. The example_operators + footprint counts are wired live from
# ift_geo so the names are never hand-typed here.
_ARCHETYPE_AUTHORED: Dict[str, Dict[str, object]] = {
    ARCH_NATIONAL: {
        "name": "National EMS platform",
        "description": (
            "The consolidated national ambulance platforms — Global Medical "
            "Response / AMR / GMR (the largest US ambulance operator), Acadian, "
            "and Priority Ambulance — that hold 911 franchises across many states "
            "and cover interfacility transport as ONE line of a mixed book. In our "
            "footprint they appear as the AMR/GMR metro operations (Kansas City, "
            "Wichita, Louisville, Northern Virginia) and the Priority-family "
            "brands (Lifecare in NoVA, Frontier in Wyoming)."),
        "ift_posture": (
            "911-heavy / mixed — the network is built around emergency 911 "
            "response; scheduled IFT competes for the same trucks and is rarely "
            "the dedicated priority."),
        "scale_magnitude": (
            "Multi-billion-dollar revenue, thousands of vehicles across 40+ "
            "states (GMR/AMR alone) — the deepest balance sheets and the only "
            "operators that contract at national-account / MSA scale."),
        "pros": (
            "National contracting + MSA / GPO leverage with multi-state IDNs "
            "(e.g. the AMR–UofL co-branded, embedded-coordinator deal)",
            "Capital + fleet depth; can absorb dual-state licensure and surge",
            "Full acuity ladder incl. CCT/SCT and neonatal/PICU contract teams",
            "Brand + payer-contracting scale on the revenue cycle"),
        "cons": (
            "911 obligations bump scheduled IFT — a discharge waits behind an "
            "emergency call, the #1 hospital complaint about mixed operators",
            "Centralized national ops are less responsive to a local transfer "
            "center than an owner-operator down the street",
            "IFT is a secondary priority, so service levels drift; crew turnover",
            "Post-roll-up integration + private-equity churn create instability"),
        "mmt_advantage": (
            "MMT reserves units for IFT, so a scheduled discharge is never bumped "
            "by a 911 call; local ownership of the transfer-center relationship "
            "beats a national account manager on reliability and responsiveness."),
    },
    ARCH_REGIONAL: {
        "name": "Scaled regional private",
        "description": (
            "Multi-market regional privates with real IFT/CCT depth — Superior "
            "Air-Ground (Ohio + Indiana, embedded at Mount Carmel), Ryan Brothers "
            "(Madison, 60-year first-call tenure), AmeriPro (the Nebraska corridor "
            "roll-up), Physicians Ambulance (NE Ohio), and Bell Ambulance "
            "(Milwaukee, IFT-specialized). These are MMT's most direct comparables."),
        "ift_posture": (
            "Mixed, IFT-leaning — many run some 911 but carry a strong, often "
            "dominant, interfacility and CCT book; the closest thing to a "
            "dedicated model besides MMT."),
        "scale_magnitude": (
            "Tens to a few hundred units, single-region density; large enough to "
            "hold first-call and run CCT, small enough to be locally owned — and "
            "the pool the national platforms and roll-ups (AmeriPro) acquire."),
        "pros": (
            "Local density + long first-call tenure (Ryan Brothers ~60 yr) → high "
            "unit-hour utilization and switching-cost lock-in",
            "Genuine CCT/SCT capability and embedded coordinators (Superior at "
            "Mount Carmel's 'Home Network')",
            "Corridor roll-up economics (AmeriPro tucking in Priority Medical "
            "Transport across greater Nebraska)"),
        "cons": (
            "Geographically boxed — cannot follow a multi-state system",
            "Capital-constrained vs the nationals; acquisition-hungry (integration "
            "risk after a tuck-in)",
            "Where they still run 911, the same bump-risk as the nationals"),
        "mmt_advantage": (
            "In its home corridor MMT matches regional density and first-call "
            "tenure while staying purpose-built for IFT; against a 911-mixed "
            "regional, the dedicated-resource model wins on scheduled-transport "
            "reliability."),
    },
    ARCH_MOMPOP: {
        "name": "Mom-and-pop local private",
        "description": (
            "Single-market, often family-owned local privates — the fragmented "
            "pool (Curtis Ambulance, Paratech, Cincinnati Medical Transport, Ultra "
            "EMS, Ohio Ambulance Solutions, Front Line EMS, Elite / Preferred One, "
            "Midwest Ambulance of Iowa, plus the 'regional privates' our registry "
            "notes but does not individually name). This is the consolidation "
            "whitespace."),
        "ift_posture": (
            "Mixed and subscale — whatever the local hospitals will hand them; no "
            "dedicated-IFT discipline, limited high-acuity capability."),
        "scale_magnitude": (
            "A handful of units per operator; the long tail of the market by "
            "count, individually small, collectively the fragmented base a "
            "consolidator rolls up."),
        "pros": (
            "Cheap, flexible, deep personal local relationships",
            "Low overhead; can undercut on price for simple BLS discharge work"),
        "cons": (
            "No scale, thin capital, limited/absent CCT-SCT capability",
            "Weak revenue cycle + little dispatch technology → under-billing and "
            "poor on-time performance",
            "Succession / key-person risk; cannot staff surge or long rural legs",
            "Cannot guarantee capacity to a health-system transfer center"),
        "mmt_advantage": (
            "MMT brings CCT capability, dispatch technology, and a professional "
            "ambulance revenue cycle a mom-and-pop cannot fund — and is the "
            "natural consolidator of this pool rather than a peer in it."),
    },
    ARCH_HOSPITAL: {
        "name": "Hospital-owned program",
        "description": (
            "The health system owns the fleet and insources its own transport — "
            "Allina Health EMS and M Health Fairview EMS and North Memorial (Twin "
            "Cities), Mayo Clinic Ambulance (Rochester), MercyOne (Des Moines), "
            "plus the captive critical-care programs at Cleveland Clinic, "
            "University Hospitals, and the children's-hospital peds/neonatal CCT "
            "teams. This is the insource ceiling, not an outsourced competitor."),
        "ift_posture": (
            "Insourced / captive — units are an extension of the enterprise, "
            "deeply integrated into the transfer center and CAD; some (Allina) "
            "even sell CCT to non-system facilities."),
        "scale_magnitude": (
            "Large where it exists (Allina Health EMS fields ~34,000 interfacility "
            "requests/yr; Mayo runs ~70 units) but confined to the owning system's "
            "captive stream — a hard ceiling on the addressable market, not a "
            "contestable book. LIVE PROOF POINT: Allina signed a definitive "
            "agreement to combine with Sutter Health (May 21, 2026) into a "
            "~39-hospital, ~$26B nonprofit expected to close by end-2026 pending "
            "regulatory approval — exactly the 'strategic review flips a captive "
            "fleet' dynamic, putting Allina's ~34,000 captive IFT requests into "
            "play in a market otherwise scored insourced-hard."),
        "pros": (
            "Deepest transfer-center / CAD / ePCR integration — the default "
            "first-call inside the system",
            "Controls its own high-acuity, neonatal, and peds legs",
            "Captive volume with no contracting friction"),
        "cons": (
            "Capital-intensive and non-core — a fixed-cost fleet the system funds "
            "instead of clinical capacity",
            "Utilization / fixed-cost risk; only economic at real scale",
            "Strategic reviews and changes of control can flip it to outsource "
            "(the reported Allina→Sutter transaction is the watch item)"),
        "mmt_advantage": (
            "MMT's pitch IS the outsource case: convert a fixed-cost captive fleet "
            "to a variable-cost dedicated partner, freeing system capital while "
            "holding SLA-grade reliability — the winnable moment is a system's "
            "strategic review, not a day-to-day contest."),
    },
    ARCH_DEDICATED: {
        "name": "Dedicated outsourced IFT specialist",
        "description": (
            "MMT's own category: a partner whose units are purpose-built and "
            "reserved for interfacility transport with NO 911 obligation. The "
            "competitive thesis is that this lane is thinly populated — in our "
            "footprint MMT is the reference dedicated pure-play; nearly every "
            "alternative is instead 911-heavy, mixed, subscale, or captive."),
        "ift_posture": (
            "Dedicated — 100% interfacility, so a scheduled or urgent transfer is "
            "never de-prioritised behind an emergency call."),
        "scale_magnitude": (
            "The white space itself: few true pure-play dedicated-IFT platforms "
            "exist at regional scale, which is the structural reason the "
            "dedicated-outsource lane is under-contested."),
        "pros": (
            "Reliability — units never bumped by 911",
            "Workflow alignment with hospital transfer centers + discharge "
            "planning; embedded-coordinator model",
            "Professional ambulance revenue cycle and dispatch technology",
            "Long-term partnership / capacity-guarantee posture"),
        "cons": (
            "Needs local density to hit unit-hour utilization",
            "Must win AND hold first-call to defend the book",
            "Smaller balance sheet than the national platforms"),
        "mmt_advantage": (
            "This is MMT's whitespace, not a rival — the report's point is that "
            "the dedicated-outsourced-IFT lane has few credible pure-play "
            "contestants, so MMT competes mostly against mixed / captive models "
            "rather than a crowded field of peers."),
    },
}


@functools.lru_cache(maxsize=1)
def competitive_archetypes() -> ArchetypeSet:
    """The 5 competitive archetypes MMT faces, with real footprint operators.

    Names are PUBLIC-WEB (reused from ift_geo ``named_operators`` — never
    invented); per-archetype footprint-metro counts are SOURCED from ift_geo;
    scale magnitudes and the competitive read are ILLUSTRATIVE. Degrades to
    ``available=False`` if ift_geo is unreadable — never raises."""
    markets = _markets()
    src = (
        "FRAMEWORK · competitive archetypes, scale magnitudes and MMT-advantage "
        "reads are analytic/modeled; operator & health-system NAMES are PUBLIC-WEB "
        "(reused verbatim from ift_geo.named_operators, named honestly); the "
        "per-archetype footprint-metro appearance counts are SOURCED from ift_geo")
    if not markets:
        return ArchetypeSet(
            available=False, source_label=src,
            note="ift_geo MARKETS unavailable offline — archetypes cannot be "
                 "wired to real footprint operators.")

    # Wire real example operators + SOURCED appearance counts from ift_geo.
    examples: Dict[str, List[str]] = {k: [] for k in _ARCHETYPE_ORDER}
    metros_seen: Dict[str, set] = {k: set() for k in _ARCHETYPE_ORDER}
    for md in markets:
        for raw in md.named_operators:
            tag = classify_operator(raw)
            if tag not in examples:      # municipal / air are context, not archetypes
                continue
            nm = _clean_name(raw)
            if nm and nm not in examples[tag]:
                examples[tag].append(nm)
            metros_seen[tag].add(md.name)

    archetypes: List[Archetype] = []
    for key in _ARCHETYPE_ORDER:
        a = _ARCHETYPE_AUTHORED[key]
        n_metros = len(metros_seen[key])
        archetypes.append(Archetype(
            key=key, name=str(a["name"]), description=str(a["description"]),
            ift_posture=str(a["ift_posture"]),
            scale_magnitude=str(a["scale_magnitude"]),
            pros=tuple(a["pros"]), cons=tuple(a["cons"]),
            example_operators=tuple(examples[key]),
            n_footprint_metros=n_metros,
            mmt_advantage=str(a["mmt_advantage"]),
            source_label=(
                f"ILLUSTRATIVE archetype · operators PUBLIC-WEB (ift_geo) · "
                f"appears in {n_metros} of {len(markets)} footprint metros "
                "(SOURCED)")))

    return ArchetypeSet(
        available=True, archetypes=archetypes, source_label=src,
        note=("MMT competes mainly against MIXED / 911-heavy / captive models, "
              "not a crowded field of dedicated pure-play IFT platforms — the "
              "dedicated-outsourced-IFT lane (the last archetype) is the "
              "whitespace. Boundary held: IFT is facility-to-facility ground "
              "transport, distinct from 911 scene response, NEMT/wheelchair-van, "
              "and air. Every name is PUBLIC-WEB; the appearance counts are "
              "SOURCED; the scale + advantage reads are ILLUSTRATIVE."))


# ── (2) Per-metro competitive structure ──────────────────────────────────────
@dataclass(frozen=True)
class OperatorPresence:
    """One operator present in a metro, classified. ``operator`` is the cleaned
    PUBLIC-WEB name; ``raw`` keeps the full ift_geo string."""
    operator: str
    raw: str
    archetype: str
    archetype_label: str


@dataclass(frozen=True)
class MarketCompetitionRow:
    name: str
    region_label: str
    insource_class: str
    operators: Tuple[OperatorPresence, ...]
    archetype_mix: Tuple[Tuple[str, int], ...]     # (archetype_label, count)
    mmt_present: bool
    first_call_today: str                          # PUBLIC-WEB (ift_geo insource_read)
    contestability_tier: str                       # derived read
    contestability: str                            # prose
    serviceable_share: Optional[float]             # ILLUSTRATIVE s(m) (ift_analytics)
    moat_note: str                                 # PUBLIC-WEB (ift_geo)
    n_nodes: int                                   # SOURCED density (ift_geo)
    density_tier: str                              # SOURCED
    density_basis: str                             # SOURCED label
    names_basis: str                               # PUBLIC-WEB
    contestability_basis: str                      # ILLUSTRATIVE
    basis: str                                     # dominant honest basis
    source_label: str


@dataclass
class MarketCompetition:
    available: bool
    rows: List[MarketCompetitionRow] = field(default_factory=list)
    source_label: str = ""
    note: str = ""


# Contestability tier keyed to the ift_geo insource archetype — the structural
# read of how much of a metro's IFT book an outsourced operator can actually win.
_CONTESTABILITY: Dict[str, Tuple[str, str]] = {
    "insourced-heavy": (
        "Low — insourced-hard",
        "Captive system fleets (Allina / North Memorial / M Health / Mayo) own "
        "the transfer stream; only the SNF/post-acute discharge residual is "
        "winnable, and only if a system chooses to outsource what it built."),
    "mixed-insource-residual": (
        "Moderate — residual only",
        "The anchors insource their own critical-care legs; the contestable "
        "layer is the non-emergent SNF-discharge / repatriation residual and the "
        "central-mileage legs."),
    "insourced-top-outsourced-bottom": (
        "Split — routine book contestable",
        "Quaternary systems own high-acuity CCT + air (a hard ceiling); the "
        "winnable SAM is routine BLS/ALS discharge + SNF/dialysis back-transfer, "
        "held by contract + transfer-center workflow, not clinical capability."),
    "public-utility-mixed": (
        "Split — public base, system-directed flip",
        "A public-utility county base carries residual IFT while system-directed "
        "volume moves to privates (the Wesley/HCA→AMR flip is the proof point) — "
        "contestable but only as durable as the system's ownership intent."),
    "mixed-confirmed-outsource": (
        "High — confirmed outsource, unclaimed prize",
        "At least one anchor confirmed outsourced (Superior embedded at Mount "
        "Carmel) with the largest systems' sourcing still unclaimed — the biggest "
        "open prize, gated by workflow-integration switching costs."),
    "two-anchor-contestable": (
        "High — win one anchor",
        "Two-anchor concentration: winning EITHER system's BLS/ALS discharge book "
        "captures a large metro share; first-call status is decisive."),
    "outsourced-two-horse": (
        "High — two-horse race",
        "Hospital IFT outsourced to a two-operator field; the prize is the "
        "transfer-center first-call and the compounding inbound-funnel + "
        "acute→rehab lanes."),
    "outsourced-fragmented": (
        "High — fragmented roll-up target",
        "Private-dominant, no single first-call system-wide; the prime roll-up "
        "target — win on local density + first-call with the transfer centers, "
        "but the most contested field."),
    "bi-state-outsourced": (
        "High — but dual-licensure gated",
        "Predominantly outsourced for adult IFT, but bi-state dual-licensure is a "
        "structural barrier to entry that protects the incumbent (AMR/GMR)."),
    "outsourced-incumbent": (
        "Contested — fortress incumbent",
        "Outsourced, but a workflow-integrated incumbent (co-branding + embedded "
        "coordinators) makes displacement hard; the realistic play is "
        "share-of-wallet at a not-yet-locked anchor system."),
    "rural-contract-gated": (
        "Gated — the exclusive contract is the moat",
        "Long legs + thin volume mean the exclusive county/hospital contract is "
        "the entire moat; density is inverted (geography is both the barrier and "
        "the moat) and only an operator with local posts runs it economically."),
}
_CONTESTABILITY_DEFAULT = (
    "Contested",
    "Outsourced book contestable on local density and transfer-center first-call.")


@functools.lru_cache(maxsize=1)
def market_competition() -> MarketCompetition:
    """Per-metro competitive structure: who is present (classified), who is
    first-call today (from ift_geo's PUBLIC-WEB insource_read), the contestability
    read, and the SOURCED node density.

    Reuses ``ift_geo.MARKETS`` + ``ift_geo.metro_structure`` (SOURCED density) +
    the ILLUSTRATIVE s(m) from ``ift_analytics.sam_formula``. Degrades to
    ``available=False`` if ift_geo is unreadable — never raises."""
    markets = _markets()
    src = (
        "FRAMEWORK · the contestability read is analytic (reusing the s(m) "
        "serviceable share ift_analytics keys to each insource archetype); "
        "operators present + first-call read are PUBLIC-WEB (ift_geo); node "
        "density is SOURCED (ift_geo/CMS)")
    if not markets:
        return MarketCompetition(
            available=False, source_label=src,
            note="ift_geo MARKETS unavailable offline.")

    s_by_metro = _serviceable_share_by_metro()
    rows: List[MarketCompetitionRow] = []
    for md in markets:
        presences: List[OperatorPresence] = []
        mix: Dict[str, int] = {}
        mmt_present = False
        for raw in md.named_operators:
            tag = classify_operator(raw)
            if tag == ARCH_DEDICATED:
                mmt_present = True
            lbl = archetype_label(tag)
            presences.append(OperatorPresence(
                operator=_clean_name(raw), raw=raw,
                archetype=tag, archetype_label=lbl))
            mix[lbl] = mix.get(lbl, 0) + 1

        tier, prose = _CONTESTABILITY.get(md.insource_class, _CONTESTABILITY_DEFAULT)

        # SOURCED density from the metro structure (degrade-safe per metro).
        n_nodes = 0
        density_tier = ""
        try:
            from . import ift_geo
            st = ift_geo.metro_structure(md.name)
            if st.available:
                n_nodes = st.n_nodes
                density_tier = st.density_tier
        except Exception:  # noqa: BLE001
            pass

        rows.append(MarketCompetitionRow(
            name=md.name, region_label=md.region_label,
            insource_class=md.insource_class,
            operators=tuple(presences),
            archetype_mix=tuple(sorted(mix.items(), key=lambda kv: -kv[1])),
            mmt_present=mmt_present,
            first_call_today=md.insource_read,
            contestability_tier=tier, contestability=prose,
            serviceable_share=s_by_metro.get(md.name),
            moat_note=md.moat_note,
            n_nodes=n_nodes, density_tier=density_tier,
            density_basis="SOURCED · ift_geo metro_structure (CMS hospital_coords "
                          "+ HCRIS + post-acute rolls)",
            names_basis=PUBLIC_WEB_NOTE,
            contestability_basis=(
                "FRAMEWORK · contestability tier keyed to the insource "
                "archetype; score = s(m) serviceable share (ift_analytics)"),
            basis=LABEL_ILLUSTRATIVE,
            source_label=(
                f"ILLUSTRATIVE contestability · {len(presences)} operators "
                "PUBLIC-WEB (ift_geo) · density SOURCED")))

    return MarketCompetition(
        available=True, rows=rows, source_label=src,
        note=("Per-metro competitive structure across all "
              f"{len(markets)} footprint metros. First-call and operator names "
              "are PUBLIC-WEB (ift_geo); the contestability tier + s(m) score are "
              "ILLUSTRATIVE; node density is SOURCED. MMT (dedicated specialist) "
              "is present in the Nebraska corridor; elsewhere the field is "
              "national / regional / captive."))


# ── (3) MMT positioning ──────────────────────────────────────────────────────
@dataclass(frozen=True)
class PositioningPillar:
    """One dimension of MMT's dedicated-outsourced-IFT positioning."""
    pillar: str
    mmt_stance: str
    vs_alternatives: str
    basis: str = LABEL_ILLUSTRATIVE


@dataclass
class MmtPositioning:
    available: bool
    reference_market: str = "Omaha"
    reference_note: str = ""
    pillars: List[PositioningPillar] = field(default_factory=list)
    vs_archetype: List[Tuple[str, str]] = field(default_factory=list)
    # SOURCED home-market density snapshot (the Omaha reference incumbent)
    home_n_hospitals: int = 0
    home_n_nodes: int = 0
    home_snf_beds: int = 0
    home_density_tier: str = ""
    home_structure_basis: str = ""
    names_basis: str = PUBLIC_WEB_NOTE
    basis: str = LABEL_ILLUSTRATIVE
    source_label: str = ""
    headline: str = ""
    note: str = ""


_PILLARS: Tuple[Tuple[str, str, str], ...] = (
    ("Dedicated resources",
     "Units purpose-built and reserved for interfacility transport — a scheduled "
     "discharge or urgent up-transfer is never bumped by a 911 call, and posts "
     "are co-located near the anchor hubs to lift unit-hour utilization and cut "
     "deadhead.",
     "National platforms and 911-mixed regionals divert trucks to emergencies; "
     "hospital-owned programs tie up system capital in a fixed-cost fleet. MMT's "
     "capacity is variable-cost and always IFT-first."),
    ("Dispatch + technology",
     "CAD integration with hospital transfer centers, ePCR, real-time ETA/status "
     "visibility, and load-chaining / backhaul optimisation so the corridor lanes "
     "(e.g. Columbus→Omaha) run economically.",
     "Mom-and-pop locals lack the dispatch stack; national operators run "
     "centralized queues tuned to 911 SLAs, not to a specific hospital's "
     "discharge workflow."),
    ("Revenue cycle",
     "A professional ambulance revenue cycle — correct HCPCS level-of-service "
     "(A0426-A0434) + mileage (A0425), origin/destination modifiers, prior "
     "authorisation for repetitive non-emergent transport, and disciplined denial "
     "management that avoids the systematic under-billing claims data hide.",
     "Subscale privates under-bill and lack denial-management muscle; hospital "
     "programs treat transport as a cost center rather than a revenue-cycle "
     "discipline."),
    ("Workflow alignment",
     "Embedded scheduling coordinators, SLA-grade response, and first-call "
     "integration into discharge planning — the Superior/Mount Carmel "
     "embedded-coordinator model, run as a dedicated partner rather than a "
     "system-owned fleet.",
     "The embedded model is exactly what wins IFT and creates high switching "
     "costs; national account management operates at a distance and cannot match "
     "the local integration."),
    ("Long-term partnerships",
     "Multi-year preferred/exclusive relationships with capacity guarantees and "
     "shared quality data, so the health system offloads a non-core, "
     "capital-intensive function to a reliable partner and the relationship "
     "compounds in switching cost.",
     "Mom-and-pops cannot guarantee capacity; a system weighing insource capital "
     "against a dependable dedicated partner is MMT's core conversion pitch."),
)


@functools.lru_cache(maxsize=1)
def mmt_positioning() -> MmtPositioning:
    """MMT as the dedicated outsourced IFT partner vs the alternatives — a
    structured positioning across five pillars, anchored to MMT's SOURCED Omaha
    home-market density (the reference incumbent in ift_geo).

    Positioning reads are ILLUSTRATIVE; the Omaha density snapshot is SOURCED;
    the operator/system names are PUBLIC-WEB. Degrades gracefully (the Omaha
    snapshot drops to zeros with an honest basis note if ift_geo is unreadable) —
    never raises."""
    pillars = [PositioningPillar(p, s, v) for (p, s, v) in _PILLARS]

    # MMT's edge vs each competitor archetype — reuse the authored advantages.
    vs_arch: List[Tuple[str, str]] = []
    for key in (ARCH_NATIONAL, ARCH_REGIONAL, ARCH_MOMPOP, ARCH_HOSPITAL):
        a = _ARCHETYPE_AUTHORED[key]
        vs_arch.append((str(a["name"]), str(a["mmt_advantage"])))

    # SOURCED Omaha home-market snapshot (MMT's reference incumbent market).
    home_h = home_nodes = home_snf = 0
    home_tier = ""
    home_basis = ("SOURCED · ift_geo.metro_structure('Omaha') — CMS "
                  "hospital_coords + HCRIS + post-acute rolls")
    try:
        from . import ift_geo
        st = ift_geo.metro_structure("Omaha")
        if st.available:
            home_h = st.n_hospitals
            home_nodes = st.n_nodes
            home_snf = st.snf_beds
            home_tier = st.density_tier
        else:
            home_basis += " (unavailable offline)"
    except Exception:  # noqa: BLE001
        home_basis += " (unavailable offline)"

    ref_note = (
        "MMT is headquartered in Omaha and is the reference IFT incumbent there "
        "(ift_geo Omaha named_operators). Omaha is the densest in-state metro — "
        f"{home_h} hospitals across {home_nodes} origin+destination nodes "
        f"({home_tier or 'n/a'} density), {home_snf:,} SNF beds — giving the best "
        "unit-hour utilisation and lowest deadhead in the Nebraska corridor.")

    headline = (
        "MMT is positioned as the DEDICATED OUTSOURCED IFT PARTNER: units reserved "
        "for interfacility transport (never bumped by 911), transfer-center "
        "workflow integration, a professional ambulance revenue cycle, and "
        "long-term system partnerships — a lane few pure-plays contest, versus "
        "national platforms (911-heavy), scaled regionals (boxed / mixed), "
        "mom-and-pops (subscale), and hospital-owned programs (captive, "
        "capital-intensive).")

    return MmtPositioning(
        available=True, reference_market="Omaha", reference_note=ref_note,
        pillars=pillars, vs_archetype=vs_arch,
        home_n_hospitals=home_h, home_n_nodes=home_nodes, home_snf_beds=home_snf,
        home_density_tier=home_tier, home_structure_basis=home_basis,
        source_label=(
            "FRAMEWORK · the five-pillar positioning and MMT-advantage reads "
            "are analytic; operator & system NAMES are PUBLIC-WEB (ift_geo); the "
            "Omaha home-market density snapshot is SOURCED (ift_geo/CMS)"),
        headline=headline,
        note=("Positioning is an analytic (ILLUSTRATIVE) read of how MMT's "
              "dedicated-outsourced model differs from the four competitor "
              "archetypes; it asserts no contract exclusivity or rate. The Omaha "
              "reference-incumbent framing and density are SOURCED; the names are "
              "PUBLIC-WEB. Boundary held: dedicated GROUND interfacility "
              "transport, distinct from 911, NEMT, and air."))
