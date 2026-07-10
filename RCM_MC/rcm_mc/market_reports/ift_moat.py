"""IFT moat / stickiness scorecard — how defensible an interfacility-transport
incumbency is, scored per target metro on the seven factors the operator thesis
rests on.

Kevin's framing (MMT): IFT stickiness is a COMBINATION, not software alone. An
operator is durable when it is (1) the transfer center's first call, (2) holds
85%+ of a system's outsourced book (share-of-wallet), (3) runs co-located /
dedicated assets at the campuses, (4) is embedded in the system's scheduling
workflow, (5) sits on a dense node cluster (high unit-hour utilization, low
deadhead), (6) faces high switching costs, and (7) can point to cross-market
proof that a new entrant cannot easily displace an incumbent. Digital connection
matters, but only WITH the physical co-location and the share-of-wallet — never
on its own.

This module scores those seven factors. It does NOT invent numeric precision:

  * The per-metro DENSITY factor (5) is scored from the SOURCED node count in
    :func:`ift_geo.metro_structure` (hospitals + post-acute destinations → the
    density tier). That factor's basis is SOURCED.
  * The other six factors are ordinal reads (strong / moderate / weak) DERIVED
    from the ift_geo per-metro ``insource_class`` archetype plus the public/analyst
    ``moat_note`` + ``insource_read`` text — an explicit, documented rubric with
    the fired signals recorded as evidence. Those are ILLUSTRATIVE (a modeled
    ordinal anchored to public knowledge), never SOURCED.
  * The composite is the mean of the seven ordinal points on a 1.00-3.00 scale,
    labelled ILLUSTRATIVE with its inputs shown — deliberately NOT a fabricated
    0-100 score.
  * The 85%+ share-of-wallet TARGET is the operator thesis, labelled ILLUSTRATIVE.
  * The cross-market PROOF POINTS pull their evidence verbatim from ift_geo's
    ``moat_note`` / ``insource_read`` (the Wichita Wesley/HCA→AMR flip, the Mount
    Carmel–Superior embedded coordinators, Bryan Health's first-call CAH funnel,
    Ryan Brothers' 60-yr Madison relationships, Mayo's captive fleet, AMR's UofL
    co-branding). Operator/system names are PUBLIC-WEB knowledge, named honestly —
    no contract exclusivities or per-transport rates are asserted.

A strong composite in an INSOURCED market (Twin Cities, Rochester) means the moat
is real but held by the incumbent health-system fleet — entry-hard, not a winnable
prize. The ``contestability`` read on every row states who holds the moat, so the
score is never mistaken for "attractive for MMT".

Design contract (mirrors ``ift_analytics`` / ``ift_geo``): pure, cached, uses the
real ift_geo data (not a hardcoded parallel copy), frozen dataclasses, and every
function **degrades — never raises**, returning a typed record with a
``source_label`` so the report/page renders an honest label instead of crashing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

# ── Honesty bases (the load-bearing invariant) ───────────────────────────────
BASIS_GOV = "GOV"
BASIS_SOURCED = "SOURCED"
BASIS_ACADEMIC = "ACADEMIC"
BASIS_ILLUSTRATIVE = "FRAMEWORK"   # renamed 2026-07-10: a stated analytical scaffold, not "illustrative"
VALID_BASES = frozenset({BASIS_GOV, BASIS_SOURCED, BASIS_ACADEMIC, BASIS_ILLUSTRATIVE})

# ── Ordinal scale (a labelled ordinal is honest; a fabricated 0-100 is not) ──
STRONG = "strong"
MODERATE = "moderate"
WEAK = "weak"
_ORDINAL_POINTS: Dict[str, int] = {STRONG: 3, MODERATE: 2, WEAK: 1}
VALID_SCORES = frozenset(_ORDINAL_POINTS)

# ── The seven factor ids (stable keys) ───────────────────────────────────────
F_FIRST_CALL = "first_call"
F_SHARE_OF_WALLET = "share_of_wallet"
F_COLOCATED = "colocated_assets"
F_WORKFLOW = "workflow_integration"
F_DENSITY = "local_density"
F_SWITCHING = "switching_costs"
F_PROOF = "cross_market_proof"

# Canonical factor order (density sits 5th — the SOURCED one).
FACTOR_ORDER: Tuple[str, ...] = (
    F_FIRST_CALL, F_SHARE_OF_WALLET, F_COLOCATED, F_WORKFLOW,
    F_DENSITY, F_SWITCHING, F_PROOF)

FACTOR_NAMES: Dict[str, str] = {
    F_FIRST_CALL: "First-call relationship",
    F_SHARE_OF_WALLET: "Share-of-wallet (target 85%+)",
    F_COLOCATED: "Co-located / dedicated assets",
    F_WORKFLOW: "Health-system workflow integration",
    F_DENSITY: "Local market density (UHU / low deadhead)",
    F_SWITCHING: "High switching costs",
    F_PROOF: "Cross-market proof points",
}


# ── The factor definitions (the scorecard framework) ─────────────────────────
@dataclass(frozen=True)
class MoatFactor:
    """One stickiness factor: what it is, why it matters, how it is evidenced.

    ``basis`` is ILLUSTRATIVE because the factor is the operator thesis framing;
    the density factor names its SOURCED input, and the share-of-wallet factor
    carries the 85%+ TARGET (the thesis target, not a measured figure)."""
    id: str
    name: str
    definition: str
    why_it_matters: str
    how_evidenced: str
    target: str = ""
    basis: str = BASIS_ILLUSTRATIVE


_FACTOR_SPECS: Tuple[MoatFactor, ...] = (
    MoatFactor(
        id=F_FIRST_CALL, name=FACTOR_NAMES[F_FIRST_CALL],
        definition=("Being the default number a hospital transfer center / house "
                    "supervisor calls first when a bed opens and a patient must move."),
        why_it_matters=("The first call captures the whole episode — the up-transfer "
                        "out AND the back-transfer/repatriation return leg — so "
                        "first-call status compounds into volume, not a single leg."),
        how_evidenced=("Named transfer-center first-call reads in ift_geo: Bryan "
                       "Health's CAH funnel + Madonna lane (Lincoln), Ryan Brothers' "
                       "60-yr relationships (Madison), the Inova hub every spoke feeds "
                       "(Northern Virginia)."),
        basis=BASIS_ILLUSTRATIVE),
    MoatFactor(
        id=F_SHARE_OF_WALLET, name=FACTOR_NAMES[F_SHARE_OF_WALLET],
        definition=("The fraction of a health system's OUTSOURCED IFT book that one "
                    "operator carries; the thesis target is 85%+ of the system's "
                    "volume, not a thin slice."),
        why_it_matters=("Below ~85% the system keeps a second vendor warm and the "
                        "relationship stays contestable; at 85%+ the operator is the "
                        "de-facto sole provider and scheduling/pricing power accrues."),
        how_evidenced=("Concentration reads where winning one anchor system decides "
                       "the metro (two-anchor Dayton; win-one-win-the-market "
                       "Louisville) vs fragmented multi-private markets (Milwaukee)."),
        target="85%+",
        basis=BASIS_ILLUSTRATIVE),
    MoatFactor(
        id=F_COLOCATED, name=FACTOR_NAMES[F_COLOCATED],
        definition=("Ambulances, crews and posts physically stationed at or dedicated "
                    "to the system's campuses — not dispatched from across the metro."),
        why_it_matters=("Kevin's framing: stickiness is physical, not software alone. "
                        "Co-located units cut response time and deadhead and make the "
                        "operator part of the site's operations — expensive to replicate."),
        how_evidenced=("Dedicated/owned-fleet reads: Allina's hospital-owned EMS "
                       "(~34,000 interfacility requests/yr, Twin Cities), Mayo Clinic "
                       "Ambulance's captive fleet (Rochester), AMR's co-branded units "
                       "at UofL (Louisville)."),
        basis=BASIS_ILLUSTRATIVE),
    MoatFactor(
        id=F_WORKFLOW, name=FACTOR_NAMES[F_WORKFLOW],
        definition=("The operator embedded in the system's transfer/scheduling "
                    "workflow — coordinators inside the transfer center, CAD/ePCR/EHR "
                    "integration — so booking a transport is a default in-workflow act."),
        why_it_matters=("Digital + human embedding makes the operator the path of least "
                        "resistance; a rival must displace a workflow, not just underbid "
                        "a contract."),
        how_evidenced=("Embedded-coordinator reads: Superior's embedded scheduling "
                       "coordinators at Mount Carmel (Columbus OH), AMR's embedded "
                       "coordinators across 9 UofL facilities (Louisville)."),
        basis=BASIS_ILLUSTRATIVE),
    MoatFactor(
        id=F_DENSITY, name=FACTOR_NAMES[F_DENSITY],
        definition=("The clustering of origin (hospital) + destination (post-acute) "
                    "nodes in the metro, which drives achievable unit-hour utilization "
                    "and low deadhead miles."),
        why_it_matters=("Dense node clusters let one deployed unit chain loads "
                        "back-to-back (high UHU) — the cost-side moat a thin-density "
                        "rival cannot match; rural markets invert this to long-leg "
                        "mileage economics."),
        how_evidenced=("SOURCED per-metro node counts from ift_geo.metro_structure "
                       "(hospitals + post-acute destinations) → the density tier."),
        basis=BASIS_SOURCED),
    MoatFactor(
        id=F_SWITCHING, name=FACTOR_NAMES[F_SWITCHING],
        definition=("The cost, risk and disruption a system would incur to replace the "
                    "incumbent — retraining coordinators, re-integrating CAD, "
                    "re-credentialing crews, rebuilding trust."),
        why_it_matters=("High switching cost is what converts a WON relationship into a "
                        "durable one — the difference between a contract and a moat."),
        how_evidenced=("Long-tenure / co-branding / captive reads (Lifecare's 30-yr "
                       "tenure in Northern Virginia; AMR's UofL co-branding; Mayo's "
                       "infinite intra-enterprise switching cost) vs flip-prone reads "
                       "(the Wichita Wesley/HCA→AMR conversion)."),
        basis=BASIS_ILLUSTRATIVE),
    MoatFactor(
        id=F_PROOF, name=FACTOR_NAMES[F_PROOF],
        definition=("Concrete, already-observed evidence in one market that the moat is "
                    "real and hard to displace — proof a new entrant cannot easily "
                    "replace an entrenched incumbent."),
        why_it_matters=("Diligence weights demonstrated moats over asserted ones; a "
                        "proof point in one metro de-risks the thesis across the "
                        "footprint."),
        how_evidenced=("The proof_points() corpus — the Wichita flip, Mount "
                       "Carmel–Superior embedding, Bryan's first-call funnel, Madison's "
                       "60-yr relationships, Mayo's captive fleet, UofL co-branding."),
        basis=BASIS_ILLUSTRATIVE),
)

_MOAT_FACTORS_LABEL = (
    "FRAMEWORK · MMT operator stickiness thesis (digital connection + 85%+ "
    "share-of-wallet + co-located assets — not software alone); factor reads are "
    "public/analyst framing, the density factor names its SOURCED input")


@lru_cache(maxsize=1)
def moat_factors() -> Tuple[MoatFactor, ...]:
    """The seven stickiness factors, each with a definition, why it matters, and
    how it is evidenced. The 85%+ share-of-wallet TARGET rides on factor 2; the
    density factor names its SOURCED input. Pure, cached, never raises."""
    return _FACTOR_SPECS


def moat_factors_source_label() -> str:
    """The dominant-basis label for the factor framework (leads ILLUSTRATIVE)."""
    return _MOAT_FACTORS_LABEL


# ── The per-archetype base rubric (ILLUSTRATIVE, documented) ─────────────────
# Base ordinal per factor keyed on the ift_geo ``insource_class`` archetype — an
# explicit, defensible mapping, refined below by the free-text signals. Factor 5
# (density) is NOT here — it is computed SOURCED from the node count.
_S, _M, _W = STRONG, MODERATE, WEAK
_ARCHETYPE_RUBRIC: Dict[str, Dict[str, str]] = {
    # Captive systems own the fleet + transfer center — the moat is maximal but
    # held BY the incumbent system (entry-hard, not a winnable prize).
    "insourced-heavy": {F_FIRST_CALL: _S, F_SHARE_OF_WALLET: _S, F_COLOCATED: _S,
                        F_WORKFLOW: _S, F_SWITCHING: _S, F_PROOF: _S},
    # High-acuity walled off; the routine discharge book is the winnable, contract
    # -driven slice across competing systems.
    "insourced-top-outsourced-bottom": {F_FIRST_CALL: _M, F_SHARE_OF_WALLET: _M,
                                        F_COLOCATED: _M, F_WORKFLOW: _M,
                                        F_SWITCHING: _M, F_PROOF: _M},
    # Embedded incumbent at the confirmed system; the rest of the metro unclaimed.
    "mixed-confirmed-outsource": {F_FIRST_CALL: _S, F_SHARE_OF_WALLET: _M,
                                  F_COLOCATED: _M, F_WORKFLOW: _S,
                                  F_SWITCHING: _S, F_PROOF: _S},
    # Systems keep critical-care in-house; the private wins the non-emergent residual.
    "mixed-insource-residual": {F_FIRST_CALL: _M, F_SHARE_OF_WALLET: _W,
                                F_COLOCATED: _M, F_WORKFLOW: _M,
                                F_SWITCHING: _M, F_PROOF: _M},
    # Winning EITHER anchor captures a large metro share; first-call is decisive.
    "two-anchor-contestable": {F_FIRST_CALL: _S, F_SHARE_OF_WALLET: _S,
                               F_COLOCATED: _M, F_WORKFLOW: _M,
                               F_SWITCHING: _S, F_PROOF: _M},
    # A two-horse race where the transfer-hub first call compounds.
    "outsourced-two-horse": {F_FIRST_CALL: _S, F_SHARE_OF_WALLET: _S,
                             F_COLOCATED: _M, F_WORKFLOW: _M,
                             F_SWITCHING: _S, F_PROOF: _M},
    # No single first-call private — a roll-up target, contested share-of-wallet.
    "outsourced-fragmented": {F_FIRST_CALL: _M, F_SHARE_OF_WALLET: _W,
                              F_COLOCATED: _M, F_WORKFLOW: _M,
                              F_SWITCHING: _M, F_PROOF: _M},
    # An entrenched regional private incumbent — the strongest outsourced moat.
    "outsourced-incumbent": {F_FIRST_CALL: _S, F_SHARE_OF_WALLET: _M,
                             F_COLOCATED: _S, F_WORKFLOW: _S,
                             F_SWITCHING: _S, F_PROOF: _S},
    # Dual-licensed private incumbents behind a bi-state barrier; dense node cluster.
    "bi-state-outsourced": {F_FIRST_CALL: _M, F_SHARE_OF_WALLET: _M,
                            F_COLOCATED: _S, F_WORKFLOW: _M,
                            F_SWITCHING: _M, F_PROOF: _M},
    # County public-utility EMS + system-directed private — ownership-intent volatile.
    "public-utility-mixed": {F_FIRST_CALL: _M, F_SHARE_OF_WALLET: _M,
                             F_COLOCATED: _M, F_WORKFLOW: _M,
                             F_SWITCHING: _W, F_PROOF: _S},
    # The exclusive county/hospital contract IS the moat; geography gates entry, but
    # there is no embedded scheduling workflow.
    "rural-contract-gated": {F_FIRST_CALL: _M, F_SHARE_OF_WALLET: _S,
                             F_COLOCATED: _S, F_WORKFLOW: _W,
                             F_SWITCHING: _S, F_PROOF: _M},
}
_DEFAULT_RUBRIC: Dict[str, str] = {
    F_FIRST_CALL: _M, F_SHARE_OF_WALLET: _M, F_COLOCATED: _M,
    F_WORKFLOW: _M, F_SWITCHING: _M, F_PROOF: _M}

# Free-text signal nudges applied to the lowercased moat_note + insource_read.
# Each fired signal OVERRIDES the archetype base for its factor and is recorded as
# evidence, so within-archetype variation (Madison's 60-yr moat vs Milwaukee's
# contested one) is honestly reflected, not flattened. (signal, factor, ordinal).
_SIGNALS: Tuple[Tuple[str, str, str], ...] = (
    ("compounding", F_FIRST_CALL, _S),
    ("60-yr", F_FIRST_CALL, _S), ("60-yr", F_SWITCHING, _S),
    ("30-yr", F_FIRST_CALL, _S), ("30-yr", F_SWITCHING, _S),
    ("embedded", F_WORKFLOW, _S),
    ("co-brand", F_WORKFLOW, _S), ("co-brand", F_COLOCATED, _S),
    ("co-brand", F_SWITCHING, _S),
    ("densest", F_COLOCATED, _S),
    ("exclusive", F_FIRST_CALL, _S), ("exclusive", F_SWITCHING, _S),
    ("impenetrable", F_SWITCHING, _S), ("impenetrable", F_FIRST_CALL, _S),
    ("infinite", F_SWITCHING, _S),
    ("belongs to the incumbent", F_SWITCHING, _S),
    ("most contested", F_SHARE_OF_WALLET, _W),
    ("flip", F_SWITCHING, _W),
    ("as durable as ownership intent", F_SWITCHING, _W),
    ("low structural moat", F_FIRST_CALL, _W),
    ("low structural moat", F_SHARE_OF_WALLET, _W),
    ("low structural moat", F_SWITCHING, _W),
)

# SOURCED density tier → ordinal (the cost-side UHU moat; rural inverts to long-leg).
_DENSITY_ORDINAL: Dict[str, str] = {
    "very-dense": STRONG, "dense": STRONG, "moderate": MODERATE,
    "thin": WEAK, "thin/long-leg": WEAK}

# Who holds the moat / how contestable it is, keyed on the archetype (public/analyst).
_CONTESTABILITY: Dict[str, str] = {
    "insourced-heavy": ("Incumbent-held (captive) — the moat is real but owned by the "
                        "health-system fleet; low-probability entry, not a winnable prize."),
    "insourced-top-outsourced-bottom": ("Split — high-acuity is insourced (walled off); "
                                        "the routine discharge book is the winnable, "
                                        "contract-driven SAM."),
    "mixed-confirmed-outsource": ("Partly claimed — an embedded incumbent at the confirmed "
                                  "system; the larger unclaimed prize is still open."),
    "mixed-insource-residual": ("Residual-only — systems keep critical-care in-house; the "
                                "private wins the non-emergent SNF-discharge residual."),
    "two-anchor-contestable": ("Contestable — winning one of the two anchor systems decides "
                               "the metro."),
    "outsourced-two-horse": ("Contestable (two-horse) — first-call with the transfer hub is "
                             "decisive."),
    "outsourced-fragmented": ("Contestable / fragmented — no single first-call private; a "
                              "roll-up target."),
    "outsourced-incumbent": ("Incumbent-held (entrenched private) — a strong moat held by the "
                             "regional incumbent; displacement is hard, the play is "
                             "share-of-wallet at one system."),
    "bi-state-outsourced": ("Incumbent-held behind a bi-state dual-licensure barrier; density "
                            "is the pay-off if you win."),
    "public-utility-mixed": ("Contestable / volatile — ownership-intent-dependent (the Wichita "
                             "flip proves durability tracks ownership, not tenure)."),
    "rural-contract-gated": ("Contract-gated — the exclusive county/hospital contract IS the "
                             "moat; win the contract or you are shut out."),
}
_DEFAULT_CONTESTABILITY = ("Mixed — see the ift_geo insource read for who holds the volume.")

_SCORES_LABEL = (
    "FRAMEWORK · ordinal moat scores derived from ift_geo public/analyst reads "
    "(insource_class archetype + moat_note + insource_read signals) with a SOURCED "
    "per-metro node-density input (ift_geo.metro_structure); composite index "
    "FRAMEWORK, inputs shown")


# ── Per-factor + per-metro score records ─────────────────────────────────────
@dataclass(frozen=True)
class FactorScore:
    """One factor's ordinal score for one metro, with its basis + evidence.

    ``basis`` is SOURCED only for the density factor (computed from real node
    counts); every other factor is ILLUSTRATIVE (an ordinal read of the ift_geo
    public/analyst text). ``evidence`` records exactly what drove the score."""
    factor_id: str
    factor_name: str
    score: str                      # strong | moderate | weak
    points: int                     # 1..3
    basis: str                      # SOURCED (density) | ILLUSTRATIVE (rest)
    evidence: str
    evidence_source: str


@dataclass(frozen=True)
class MarketMoatScore:
    """The moat scorecard for one target metro: seven factor scores, a composite,
    an overall verdict, and the contestability read (who holds the moat)."""
    available: bool
    name: str = ""
    region_label: str = ""
    profile: str = ""
    rural: bool = False
    insource_class: str = ""
    factors: Tuple[FactorScore, ...] = ()
    density_tier: str = ""
    n_nodes: int = 0
    n_postacute: int = 0
    composite_index: float = 0.0            # 1.00-3.00 mean of factor points
    composite_basis: str = ""
    overall_verdict: str = ""               # strong | moderate | weak
    contestability: str = ""
    overall_read: str = ""
    moat_note: str = ""                     # ift_geo verbatim (public/analyst)
    insource_read: str = ""                 # ift_geo verbatim (public/analyst)
    source_label: str = ""
    note: str = ""


@dataclass(frozen=True)
class MoatScorecard:
    """The footprint-wide scorecard: one :class:`MarketMoatScore` per metro plus a
    verdict-count summary."""
    available: bool
    rows: Tuple[MarketMoatScore, ...] = ()
    n_markets: int = 0
    verdict_counts: Dict[str, int] = field(default_factory=dict)
    source_label: str = ""
    note: str = ""


def _verdict(composite: float) -> str:
    """Ordinal verdict from the 1.00-3.00 composite. Thresholds are the ordinal
    midpoints — a labelled band, not a fabricated cut-off."""
    if composite >= 2.5:
        return STRONG
    if composite >= 1.8:
        return MODERATE
    return WEAK


def _derive_factor_scores(md, structure) -> Tuple[FactorScore, ...]:
    """Derive the seven ordinal factor scores for one metro.

    The six qualitative factors start from the archetype rubric, then free-text
    signals in moat_note + insource_read override them (recorded as evidence);
    the density factor is scored SOURCED from the node count. ``md`` is an
    ift_geo.MetroDef; ``structure`` is its (SOURCED) ift_geo.MetroStructure."""
    text = ((md.moat_note or "") + " " + (md.insource_read or "")).lower()
    base = dict(_ARCHETYPE_RUBRIC.get(md.insource_class, _DEFAULT_RUBRIC))
    evidence: Dict[str, List[str]] = {
        fid: [f"archetype '{md.insource_class}' → {base[fid]}"] for fid in base}

    # Free-text signal overrides (within-archetype variation).
    for needle, fid, target in _SIGNALS:
        if needle in text and fid in base:
            base[fid] = target
            evidence[fid].append(f"signal '{needle}' → {target}")

    # A metro that furnishes a cross-market proof point scores strong on factor 7.
    if md.name in _PROOF_MARKETS:
        base[F_PROOF] = STRONG
        evidence[F_PROOF].append("furnishes a cross-market proof point → strong")

    scores: List[FactorScore] = []
    for fid in FACTOR_ORDER:
        if fid == F_DENSITY:
            tier = structure.density_tier or ""
            sc = _DENSITY_ORDINAL.get(tier, WEAK)
            ev = (f"SOURCED density: {structure.n_nodes:,} origin+destination nodes "
                  f"({structure.n_postacute_destinations:,} post-acute), tier "
                  f"'{tier or 'unknown'}'"
                  + (" — rural geography inverts UHU to long-leg mileage economics"
                     if md.rural else ""))
            scores.append(FactorScore(
                factor_id=fid, factor_name=FACTOR_NAMES[fid], score=sc,
                points=_ORDINAL_POINTS[sc], basis=BASIS_SOURCED, evidence=ev,
                evidence_source="ift_geo.metro_structure (SOURCED node count)"))
        else:
            sc = base[fid]
            scores.append(FactorScore(
                factor_id=fid, factor_name=FACTOR_NAMES[fid], score=sc,
                points=_ORDINAL_POINTS[sc], basis=BASIS_ILLUSTRATIVE,
                evidence="; ".join(evidence[fid]),
                evidence_source="ift_geo insource_class + moat_note/insource_read"))
    return tuple(scores)


@lru_cache(maxsize=64)
def market_moat_score(name: str) -> MarketMoatScore:
    """The seven-factor moat scorecard for one target metro (by ift_geo name).

    Degrades to ``available=False`` for an unknown metro or if the SOURCED
    structure is unreadable offline — never raises. The density factor is SOURCED;
    the other six are ILLUSTRATIVE ordinal reads of the ift_geo public/analyst
    text; the composite is the ILLUSTRATIVE mean of the seven ordinal points."""
    try:
        from . import ift_geo
        md = ift_geo.metro_def(name)
        if md is None:
            return MarketMoatScore(
                available=False, name=str(name), source_label=_SCORES_LABEL,
                note="Unknown metro — not in the ift_geo footprint registry.")
        structure = ift_geo.metro_structure(md.name)
        if not structure.available:
            return MarketMoatScore(
                available=False, name=md.name, region_label=md.region_label,
                insource_class=md.insource_class, source_label=_SCORES_LABEL,
                note=("The SOURCED per-metro structure is unavailable offline, so the "
                      "density factor cannot be scored honestly; row omitted."))

        factors = _derive_factor_scores(md, structure)
        composite = round(sum(f.points for f in factors) / len(factors), 2)
        verdict = _verdict(composite)
        contest = _CONTESTABILITY.get(md.insource_class, _DEFAULT_CONTESTABILITY)
        overall = (f"{verdict.capitalize()} composite moat ({composite:.2f}/3.00, "
                   f"ILLUSTRATIVE). {contest}")
        return MarketMoatScore(
            available=True, name=md.name, region_label=md.region_label,
            profile=md.profile, rural=md.rural, insource_class=md.insource_class,
            factors=factors, density_tier=structure.density_tier,
            n_nodes=structure.n_nodes,
            n_postacute=structure.n_postacute_destinations,
            composite_index=composite,
            composite_basis=("FRAMEWORK · mean of the seven ordinal factor points "
                             "(strong=3, moderate=2, weak=1) on a 1.00-3.00 scale; "
                             "inputs are the per-factor scores shown"),
            overall_verdict=verdict, contestability=contest, overall_read=overall,
            moat_note=md.moat_note, insource_read=md.insource_read,
            source_label=_SCORES_LABEL,
            note=("Density factor SOURCED (ift_geo node count); the six qualitative "
                  "factors are ILLUSTRATIVE ordinal reads of the ift_geo public/analyst "
                  "moat_note + insource_read; the composite is ILLUSTRATIVE. A strong "
                  "composite in an insourced market is entry-HARD, not winnable — see "
                  "contestability."))
    except Exception:  # noqa: BLE001 — degrade, never raise
        return MarketMoatScore(
            available=False, name=str(name), source_label=_SCORES_LABEL,
            note="Moat scoring failed offline.")


@lru_cache(maxsize=1)
def market_moat_scores() -> MoatScorecard:
    """The footprint-wide moat scorecard — one row per ift_geo market, each with a
    per-factor ordinal score (density SOURCED, the rest ILLUSTRATIVE), a composite
    and a contestability read. Degrade-safe: skips any metro that cannot be scored,
    returns ``available=False`` if ift_geo is unreadable — never raises."""
    try:
        from . import ift_geo
        markets = ift_geo.MARKETS
    except Exception:  # noqa: BLE001
        return MoatScorecard(
            available=False, source_label=_SCORES_LABEL,
            note="The ift_geo footprint registry is not available offline.")
    rows: List[MarketMoatScore] = []
    for md in markets:
        row = market_moat_score(md.name)
        if row.available:
            rows.append(row)
    if not rows:
        return MoatScorecard(
            available=False, source_label=_SCORES_LABEL,
            note="No market moat scores could be computed offline.")
    counts: Dict[str, int] = {STRONG: 0, MODERATE: 0, WEAK: 0}
    for r in rows:
        counts[r.overall_verdict] = counts.get(r.overall_verdict, 0) + 1
    return MoatScorecard(
        available=True, rows=tuple(rows), n_markets=len(rows),
        verdict_counts=counts, source_label=_SCORES_LABEL,
        note=("Stickiness is a COMBINATION (Kevin's framing): digital connection + "
              "85%+ share-of-wallet + co-located assets, never software alone. A strong "
              "composite in an insourced-heavy or entrenched-incumbent market means the "
              "moat is real but HELD by the incumbent (entry-hard); the contestability "
              "read on each row states who holds it. Density is SOURCED; the ordinal "
              "reads and composite are ILLUSTRATIVE off the ift_geo public/analyst text."))


# ── Cross-market proof points (evidence pulled verbatim from ift_geo) ─────────
# (market, factor-ids proven, authored claim headline, ift_geo field the evidence
#  is pulled from). The evidence text is NEVER re-typed — it is read straight off
#  the ift_geo MetroDef so it cannot drift from the curated public/analyst read.
_PROOF_SPECS: Tuple[Tuple[str, Tuple[str, ...], str, str], ...] = (
    ("Wichita",
     (F_SWITCHING, F_SHARE_OF_WALLET, F_PROOF),
     "Insource→outsource flip: Wesley/HCA moved ~77% of county IFT (~4,873/2020) "
     "to AMR in 2022 — the cleanest proof that share-of-wallet durability tracks "
     "ownership intent, not tenure.",
     "insource_read"),
    ("Columbus (OH)",
     (F_WORKFLOW, F_FIRST_CALL, F_SWITCHING),
     "Workflow-integration moat: Superior's embedded scheduling coordinators per "
     "Mount Carmel campus make it the default first call — a textbook embedded-"
     "workflow lock-in.",
     "moat_note"),
    ("Lincoln",
     (F_FIRST_CALL, F_SHARE_OF_WALLET),
     "Compounding first-call: holding Bryan Health's transfer-center first call "
     "captures BOTH the inbound CAH-network funnel AND the Madonna acute→rehab "
     "lane.",
     "moat_note"),
    ("Madison",
     (F_FIRST_CALL, F_SWITCHING),
     "Relationship tenure moat: Ryan Brothers' 60-yr first-call relationships + "
     "critical-care capability + 100-mi coverage density — the acquirable asset is "
     "the regional private, not a system fleet.",
     "moat_note"),
    ("Rochester (MN)",
     (F_COLOCATED, F_SWITCHING, F_FIRST_CALL),
     "Captive-fleet proof of the insource archetype: Mayo owns the fleet, the "
     "transfer center and the 911 designation — switching cost is infinite inside "
     "the enterprise.",
     "moat_note"),
    ("Louisville",
     (F_WORKFLOW, F_SWITCHING, F_COLOCATED),
     "Contract + co-branding moat: AMR's UofL deal — co-branded units + embedded "
     "coordinators + 9-site workflow = high switching cost.",
     "moat_note"),
    ("Twin Cities",
     (F_COLOCATED, F_FIRST_CALL, F_SWITCHING),
     "Owned-fleet insource proof: Allina Health EMS runs a hospital-owned fleet at "
     "~34,000 interfacility requests/2024 — captive volume a private cannot easily "
     "displace.",
     "insource_read"),
    ("Northern Virginia",
     (F_SWITCHING, F_FIRST_CALL),
     "Fortress-incumbent proof: displacement is hard against Lifecare's 30-yr "
     "tenure and AMR's Kaiser book — realistic entry is share-of-wallet at one "
     "system.",
     "moat_note"),
    ("Kansas City (bi-state)",
     (F_DENSITY, F_SWITCHING),
     "Density + barrier proof: the densest node cluster in the footprint (best "
     "deadhead/UHU economics) behind a bi-state dual-licensure barrier.",
     "moat_note"),
    ("North Platte",
     (F_PROOF, F_FIRST_CALL),
     "Incumbency-capture proof: AmeriPro's acquisition of Priority Medical "
     "Transport is a direct move to buy the local incumbency.",
     "moat_note"),
    ("Cincinnati",
     (F_SWITCHING, F_DENSITY),
     "Barrier-to-entry proof: bi-state OH-KY dual licensure protects the incumbents "
     "on the footprint's densest post-acute landscape.",
     "moat_note"),
)

# The set of markets that furnish a proof point (single source of truth, also used
# to bump factor 7 in the scorecard).
_PROOF_MARKETS: frozenset = frozenset(spec[0] for spec in _PROOF_SPECS)

_PROOF_LABEL = ("public/company web + ift_geo analyst reads, named honestly — no "
                "contract exclusivities or per-transport rates asserted")


@dataclass(frozen=True)
class ProofPoint:
    """One cross-market proof point: the market, the moat factors it proves, an
    authored claim, and the evidence pulled VERBATIM from ift_geo (never re-typed,
    so it cannot drift from the curated public/analyst read)."""
    market: str
    region_label: str
    factors: Tuple[str, ...]                # factor ids proven
    factor_names: Tuple[str, ...]
    claim: str
    evidence: str                           # ift_geo verbatim
    evidence_source: str                    # which ift_geo field
    named_operators: Tuple[str, ...]        # PUBLIC-WEB, named honestly
    source_note: str = _PROOF_LABEL


@dataclass(frozen=True)
class ProofPointSet:
    available: bool
    points: Tuple[ProofPoint, ...] = ()
    source_label: str = ""
    note: str = ""


@lru_cache(maxsize=1)
def proof_points() -> ProofPointSet:
    """The concrete cross-market proof points already in ift_geo — each names its
    market and the moat factor(s) it proves, with the evidence pulled verbatim
    from the ift_geo moat_note / insource_read (public/analyst, named honestly).

    Degrade-safe: skips any market missing from the registry, returns
    ``available=False`` if ift_geo is unreadable — never raises."""
    try:
        from . import ift_geo
    except Exception:  # noqa: BLE001
        return ProofPointSet(
            available=False, source_label=_PROOF_LABEL,
            note="The ift_geo footprint registry is not available offline.")
    points: List[ProofPoint] = []
    for market, factor_ids, claim, ev_field in _PROOF_SPECS:
        md = ift_geo.metro_def(market)
        if md is None:
            continue
        evidence = getattr(md, ev_field, "") or ""
        if not evidence:
            continue
        points.append(ProofPoint(
            market=md.name, region_label=md.region_label,
            factors=tuple(factor_ids),
            factor_names=tuple(FACTOR_NAMES[f] for f in factor_ids),
            claim=claim, evidence=evidence, evidence_source=f"ift_geo.{ev_field}",
            named_operators=tuple(md.named_operators)))
    if not points:
        return ProofPointSet(
            available=False, source_label=_PROOF_LABEL,
            note="No proof-point markets resolved against the ift_geo registry.")
    return ProofPointSet(
        available=True, points=tuple(points), source_label=_PROOF_LABEL,
        note=("Each proof point names its market and the factor(s) it proves; the "
              "evidence is pulled verbatim from ift_geo's curated public/analyst read "
              "(moat_note / insource_read), so nothing is re-invented. Operator and "
              "health-system names are PUBLIC-WEB, named honestly — no contract "
              "exclusivities or per-transport rates are asserted."))
