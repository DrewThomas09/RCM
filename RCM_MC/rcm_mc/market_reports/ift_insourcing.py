"""IFT insource-vs-outsource framework — the SOW's trickiest topic, sized honestly.

The investment question is *how much of the ground interfacility-transport (IFT)
book a health system runs with its OWN units versus contracts out*, because the
outsourced slice is the addressable market. The transcripts pin three rules this
module encodes so the read is defensible rather than hand-waved:

  (a) **Classify by transport VOLUME, not asset ownership.** A health system may
      own a handful of marked ambulances (usually the high-acuity neonatal/peds
      CCT slice it must control) and still OUTSOURCE the high-volume routine
      book — that is a *hybrid*, not an insourced system. An asset count
      over-states insourcing; only self-run mission VOLUME classifies a system.
  (b) **Claims are the upper bound on insourcing.** Claims data can show WHO
      billed a mission, including whether a health-system-affiliated NPI billed
      it. "If the system is billing the transport it must be insourced" makes the
      health-system-biller share the *ceiling* on insourcing — the true value is
      at or below it (a system NPI can bill for a subcontracted/JV operator).
  (c) **Claims under-count the market, so it must be grossed UP.** Fragmented
      mom-and-pop vendors often bill the *hospital* directly (never the payer),
      and some hospitals simply eat the cost — neither reaches a payer claim, so
      a claims-observed market must be grossed up for direct-bill + unbilled
      activity to reach the true market.

What is ILLUSTRATIVE (modeled, basis named on every figure): the four insourcing
bands and their volume-share cut-points, the per-metro insourced-volume-share
read, the direct-bill / unbilled gross-up fractions, and the multiplier they
imply. The health-system-biller insource CEILING is REUSED verbatim from
``ift_analytics.health_system_sam().insource_ceiling`` (not reinvented here) — it
is the network-gated claims proxy, labelled ILLUSTRATIVE, anchored to how little
ground fleet hospitals own. The gross-up fractions are the IFT-market analog of
the documented causes in ``rcm_mc/npi_cleaner/understatement.py`` (the 20-cause
claims-understatement taxonomy), which this module IMPORTS and cites so the two
stay consistent rather than being parallel reinventions.

What is PUBLIC-WEB knowledge (named honestly, never fabricated): every health-
system and operator NAME. They are REUSED from ``ift_geo`` (``anchor_systems`` /
``named_operators``, which the brief curated from public/company web); no system
or operator is invented and no contract exclusivity or per-transport rate is
asserted. Names carry a "public/company web, named honestly" note, not a data
chip. The per-metro insource_read / moat prose is likewise PUBLIC-WEB (ift_geo).

Honesty rule (load-bearing): a mixed result LEADS with its dominant honest basis
(ILLUSTRATIVE for every read here) and names the SOURCED / GOV / PUBLIC-WEB
anchors inside; ``source_label`` uses " · " to split the basis chip from the
descriptive remainder. Every figure-bearing record also carries a ``basis`` in
{GOV, SOURCED, ACADEMIC, ILLUSTRATIVE}.

Design contract (mirrors ``ift_analytics`` / ``ift_geo`` / ``ift_competitive``):
pure, no runtime network, cached, frozen leaf records, and every function
**degrades — never raises** — returning an honest ``available`` + ``source_label``
so the report / page renders a label instead of crashing.
"""
from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ── Honesty-basis vocabulary (mirrors the market_reports contract) ───────────
LABEL_GOV = "GOV"
LABEL_SOURCED = "SOURCED"
LABEL_ACADEMIC = "ACADEMIC"
LABEL_ILLUSTRATIVE = "ILLUSTRATIVE"
_BASES = (LABEL_GOV, LABEL_SOURCED, LABEL_ACADEMIC, LABEL_ILLUSTRATIVE)

# System / operator NAMES are public-web knowledge, not a data figure — they
# carry this note, never a SOURCED/GOV data chip.
PUBLIC_WEB_NOTE = "PUBLIC-WEB · public/company web, named honestly"

# ── The four insourcing bands (keys + ordered display) ───────────────────────
# The classification AXIS is transport-VOLUME share insourced, NOT asset
# ownership. Bands are contiguous over [0, 1] so the spectrum reads cleanly.
BAND_FULLY_OUTSOURCED = "fully_outsourced"
BAND_MOSTLY_OUTSOURCED = "hybrid_mostly_outsourced"
BAND_MOSTLY_INSOURCED = "hybrid_mostly_insourced"
BAND_FULLY_INSOURCED = "fully_insourced"

_BAND_ORDER: Tuple[str, ...] = (
    BAND_FULLY_OUTSOURCED, BAND_MOSTLY_OUTSOURCED,
    BAND_MOSTLY_INSOURCED, BAND_FULLY_INSOURCED)

_BAND_LABEL: Dict[str, str] = {
    BAND_FULLY_OUTSOURCED: "Fully outsourced",
    BAND_MOSTLY_OUTSOURCED: "Hybrid — mostly outsourced",
    BAND_MOSTLY_INSOURCED: "Hybrid — mostly insourced",
    BAND_FULLY_INSOURCED: "Fully insourced",
}

# Contiguous volume-share cut-points (insourced transport-VOLUME share).
_BAND_RANGE: Dict[str, Tuple[float, float]] = {
    BAND_FULLY_OUTSOURCED: (0.00, 0.05),
    BAND_MOSTLY_OUTSOURCED: (0.05, 0.50),
    BAND_MOSTLY_INSOURCED: (0.50, 0.95),
    BAND_FULLY_INSOURCED: (0.95, 1.00),
}


def band_label(key: str) -> str:
    """Human label for a band key (or the raw key if unknown)."""
    return _BAND_LABEL.get(key, key)


# ── ift_geo accessors (degrade-safe, cached) ─────────────────────────────────
@functools.lru_cache(maxsize=1)
def _markets():
    """The ift_geo MARKETS tuple, or () if ift_geo is unreadable offline."""
    try:
        from . import ift_geo
        return ift_geo.MARKETS
    except Exception:  # noqa: BLE001 — degrade, never raise
        return tuple()


def _clean_name(raw: str) -> str:
    """Display name = the ift_geo string up to its descriptive parenthetical
    ('Allina Health EMS (hospital-owned; …)' → 'Allina Health EMS'). Keeps the
    real ift_geo name — never invents one."""
    name = (raw or "").split(" (")[0].strip()
    return name or (raw or "").strip()


@functools.lru_cache(maxsize=1)
def _all_geo_names() -> Tuple[str, ...]:
    """Every PUBLIC-WEB operator + anchor-system display name in ift_geo, in
    registry order, de-duped. () if ift_geo is unreadable offline — so callers
    degrade to empty example lists rather than raising."""
    seen: List[str] = []
    for md in _markets():
        for raw in tuple(md.named_operators) + tuple(md.anchor_systems):
            nm = _clean_name(raw)
            if nm and nm not in seen:
                seen.append(nm)
    return tuple(seen)


def _resolve_geo_names(substrs: Tuple[str, ...]) -> Tuple[str, ...]:
    """Resolve each substring to the FIRST matching ift_geo display name
    (case-insensitive), preserving order and de-duping.

    Guarantees every returned name is REUSED from ift_geo (never invented);
    silently drops a substring with no match so a registry edit can't crash the
    framework."""
    names = _all_geo_names()
    out: List[str] = []
    for sub in substrs:
        s = sub.lower()
        for nm in names:
            if s in nm.lower():
                if nm not in out:
                    out.append(nm)
                break
    return tuple(out)


@functools.lru_cache(maxsize=1)
def _serviceable_share_by_metro() -> Dict[str, float]:
    """``{metro_name: s(m)}`` — the ILLUSTRATIVE realistically-serviceable share
    ``ift_analytics.sam_formula`` keys to each metro's insource archetype.

    Reused as the *contestable-residual* score (a higher serviceable share IS a
    larger winnable book for an outsourced operator) so the insourcing read and
    the sizing model agree. ``{}`` on any failure."""
    try:
        from . import ift_analytics
        sam = ift_analytics.sam_formula()
        if not sam.available:
            return {}
        return {r.name: float(r.serviceable_share) for r in sam.rows}
    except Exception:  # noqa: BLE001
        return {}


def _health_system_sam():
    """``ift_analytics.health_system_sam()`` or None — the source of the reused
    insource ceiling. Wrapped so a degrade test can null it out."""
    try:
        from . import ift_analytics
        return ift_analytics.health_system_sam()
    except Exception:  # noqa: BLE001
        return None


def _ground_tam():
    """``ift_analytics.ground_tam()`` or None — the GOV-anchored true-market
    reference the claims gross-up is applied against."""
    try:
        from . import ift_analytics
        return ift_analytics.ground_tam()
    except Exception:  # noqa: BLE001
        return None


def _understatement():
    """The claims-understatement cleaner module or None. IMPORTED (not copied)
    so the gross-up cites the SAME 20-cause taxonomy the cleaner documents."""
    try:
        from ..npi_cleaner import understatement as u
        return u
    except Exception:  # noqa: BLE001
        return None


# ═════════════════════════════════════════════════════════════════════════════
# (1) The classification model — insourcing_framework()
# ═════════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class InsourceBand:
    """One band of the insource-vs-outsource spectrum, defined by the insourced
    transport-VOLUME share (NOT asset ownership).

    ``example_systems`` are REUSED from ift_geo (PUBLIC-WEB); the definition,
    operating-requirement rationale and addressable read are ILLUSTRATIVE."""
    key: str
    name: str
    volume_share_low: float          # insourced transport-VOLUME share, low edge
    volume_share_high: float         # high edge (contiguous with the next band)
    definition: str
    operating_requirement: str       # WHAT it takes to sit here — the rationale
    asset_vs_volume_note: str        # the "owns a few trucks ≠ insourced" trap
    addressable_read: str            # what an outsourced operator can win here
    example_systems: Tuple[str, ...]  # PUBLIC-WEB (ift_geo), possibly empty
    names_basis: str = PUBLIC_WEB_NOTE
    basis: str = LABEL_ILLUSTRATIVE
    source_label: str = ""


@dataclass
class InsourceFramework:
    available: bool
    bands: List[InsourceBand] = field(default_factory=list)
    classification_axis: str = ""
    source_label: str = ""
    headline: str = ""
    note: str = ""


# Authored band content. ``example_substrs`` are resolved against ift_geo at
# build time so the names are guaranteed REUSED, never hand-typed magnitudes.
_BAND_AUTHORED: Dict[str, Dict[str, object]] = {
    BAND_FULLY_OUTSOURCED: {
        "definition": (
            "The health system self-runs essentially NO interfacility transport "
            "(under ~5% of missions by volume); every IFT leg is handed to a "
            "contracted operator — a dedicated IFT specialist, a national EMS "
            "platform, a regional private, or a public-utility/municipal service."),
        "operating_requirement": (
            "None beyond a contract and a transfer-center workflow — outsourcing "
            "is the default because running ambulances is capital-intensive, "
            "non-core, and needs 24/7 crews the system would rather not carry."),
        "asset_vs_volume_note": (
            "A system here may still hold a decommissioned or grant-funded unit on "
            "the books; asset ownership does not move it out of fully-outsourced — "
            "only self-run mission VOLUME would, and there is none of consequence."),
        "addressable_read": (
            "The entire book is contestable; winning is about first-call status "
            "and transfer-center / CAD integration, not displacing a captive fleet."),
        "example_substrs": ("Norton Healthcare", "Inova", "UW Health", "Bryan Health"),
    },
    BAND_MOSTLY_OUTSOURCED: {
        "definition": (
            "The system self-runs a MINORITY of IFT volume (~5-50%) — typically "
            "only the narrow high-acuity slice it must control (neonatal/peds CCT, "
            "ECMO, its own critical-care up-transfers) — and outsources the "
            "high-VOLUME routine BLS/ALS discharge + SNF/dialysis back-transfer."),
        "operating_requirement": (
            "A small captive critical-care program: a few specialty units, "
            "specialty crews, and medical direction — affordable because ACUITY "
            "(not volume) justifies it, while the routine book stays outsourced."),
        "asset_vs_volume_note": (
            "THE CLASSIC TRAP: the system owns a few marked ambulances, so an "
            "asset count reads 'insourced' — but by mission VOLUME it is mostly "
            "OUTSOURCED. This is why the classification tracks volume, not assets."),
        "addressable_read": (
            "The routine-volume residual — the bulk of missions — is the "
            "addressable market; the high-acuity slice the system keeps is a "
            "hard, small ceiling."),
        "example_substrs": ("Cleveland Clinic", "Cincinnati Children's",
                            "Children's Mercy", "MercyOne"),
    },
    BAND_MOSTLY_INSOURCED: {
        "definition": (
            "The system self-runs the MAJORITY of IFT volume (~50-95%) on a real "
            "fleet with its own dispatch and crews, outsourcing only overflow, "
            "surge, or the low-margin long-leg / SNF residual."),
        "operating_requirement": (
            "A genuine fleet operation — 24/7 crews, CAD/dispatch, medical "
            "direction, an ambulance revenue cycle, and enough transfer VOLUME to "
            "amortize the fixed cost; only large integrated systems clear this bar."),
        "asset_vs_volume_note": (
            "Here asset ownership and volume finally agree — but the read is still "
            "made on volume; a large owned fleet that sat idle would not count."),
        "addressable_read": (
            "Only overflow + the residual are winnable, and mainly at a strategic-"
            "review moment when the system reconsiders a fixed-cost captive fleet."),
        "example_substrs": ("Allina Health EMS", "North Memorial",
                            "M Health Fairview EMS"),
    },
    BAND_FULLY_INSOURCED: {
        "definition": (
            "The system self-runs essentially ALL IFT (over ~95% of volume), "
            "often also holding the 911 designation and the transfer center as one "
            "enterprise — transport is not a vendor relationship, it is a "
            "department."),
        "operating_requirement": (
            "Full vertical integration at referral-magnet scale: a captive fleet, "
            "the transfer center, and sometimes 911 authority run as a single "
            "enterprise — the economics only work at very high transfer volume."),
        "asset_vs_volume_note": (
            "Ownership and volume are the same thing here; the switching cost is "
            "effectively infinite because the transport IS the enterprise."),
        "addressable_read": (
            "Effectively nil except subcontracted overflow — a proof point of the "
            "insource archetype, not an acquisition or displacement target."),
        "example_substrs": ("Mayo Clinic Ambulance",),
    },
}


@functools.lru_cache(maxsize=1)
def insourcing_framework() -> InsourceFramework:
    """The insource-vs-outsource classification model.

    Four bands — fully-outsourced → hybrid-mostly-outsourced → hybrid-mostly-
    insourced → fully-insourced — defined by insourced transport-VOLUME share
    (NOT asset ownership), each with its operating-requirement rationale and the
    "owns a few trucks ≠ insourced" trap spelled out. Example systems are REUSED
    from ift_geo (PUBLIC-WEB). The model is authored (ILLUSTRATIVE) so it stays
    ``available`` even if ift_geo is unreadable — the example lists just degrade
    to empty. Never raises."""
    axis = ("insourced transport-VOLUME share (missions self-run with the "
            "system's own units + crews), NOT ambulance-asset ownership — a "
            "system can own a few units and still outsource most IFT (a hybrid)")
    bands: List[InsourceBand] = []
    for key in _BAND_ORDER:
        a = _BAND_AUTHORED[key]
        lo, hi = _BAND_RANGE[key]
        examples = _resolve_geo_names(tuple(a["example_substrs"]))  # type: ignore[arg-type]
        bands.append(InsourceBand(
            key=key, name=_BAND_LABEL[key],
            volume_share_low=lo, volume_share_high=hi,
            definition=str(a["definition"]),
            operating_requirement=str(a["operating_requirement"]),
            asset_vs_volume_note=str(a["asset_vs_volume_note"]),
            addressable_read=str(a["addressable_read"]),
            example_systems=examples,
            source_label=(
                f"ILLUSTRATIVE band ({lo * 100:.0f}-{hi * 100:.0f}% insourced by "
                "volume) · example systems PUBLIC-WEB (ift_geo)"
                if examples else
                f"ILLUSTRATIVE band ({lo * 100:.0f}-{hi * 100:.0f}% insourced by "
                "volume) · example systems unavailable offline")))
    return InsourceFramework(
        available=True, bands=bands, classification_axis=axis,
        source_label=(
            "ILLUSTRATIVE · insource-vs-outsource classification model "
            "(volume-share bands + operating-requirement rationale); example "
            "systems PUBLIC-WEB (reused from ift_geo, named honestly)"),
        headline=(
            "Insourcing is a spectrum measured by transport VOLUME, not assets: "
            "fully-outsourced → hybrid-mostly-outsourced → hybrid-mostly-insourced "
            "→ fully-insourced. Most multi-hospital systems sit in the two hybrid "
            "bands — self-running only the high-acuity slice they must control and "
            "outsourcing the high-volume routine book, which is exactly the "
            "addressable market."),
        note=("Do NOT classify a system as insourced just because it owns a few "
              "ambulances; classify on the share of mission VOLUME it self-runs. "
              "The bands are ILLUSTRATIVE with named volume-share cut-points; the "
              "example systems are PUBLIC-WEB, reused verbatim from ift_geo. "
              "Boundary held: GROUND interfacility transport, distinct from 911 "
              "scene response, NEMT/wheelchair-van, and air."))


# ═════════════════════════════════════════════════════════════════════════════
# (2) The health-system-biller proxy — biller_proxy()  [insource UPPER BOUND]
# ═════════════════════════════════════════════════════════════════════════════
@dataclass
class BillerProxy:
    """The health-system-biller claims proxy = the UPPER BOUND on insourcing.

    Ceiling + addressable are REUSED verbatim from
    ``ift_analytics.health_system_sam()`` (not reinvented); every figure is
    ILLUSTRATIVE (the precise value is a network-gated claims build)."""
    available: bool
    ceiling_low: float = 0.0
    ceiling_central: float = 0.0
    ceiling_high: float = 0.0
    addressable_low: float = 0.0
    addressable_central: float = 0.0
    addressable_high: float = 0.0
    proxy_rule: str = ""
    upper_bound_rationale: str = ""
    limitations: List[str] = field(default_factory=list)
    source_label: str = ""
    headline: str = ""
    note: str = ""


@functools.lru_cache(maxsize=1)
def biller_proxy() -> BillerProxy:
    """The health-system-biller claims proxy — the insource UPPER BOUND.

    The transcript proxy: "if the health system is billing the transport it must
    be insourced." So the share of ground-IFT dollars billed by a health-system-
    affiliated NPI is the CEILING on insourcing — true insourcing is at or below
    it, and the addressable (outsourceable) market is at or above (1 − ceiling).
    The ceiling is REUSED verbatim from ``ift_analytics.health_system_sam()``
    ``.insource_ceiling`` (the network-gated claims proxy, ILLUSTRATIVE, anchored
    to how little ground fleet hospitals own) — NOT a different number. Degrades
    to ``available=False`` if that spine is unavailable — never raises."""
    src = ("ILLUSTRATIVE · health-system-biller insource ceiling reused from "
           "ift_analytics.health_system_sam().insource_ceiling (network-gated "
           "claims proxy; anchored to how little ground fleet hospitals own) — "
           "GROUND IFT $ only, ex-air ex-NEMT ex-911")
    hs = _health_system_sam()
    if hs is None or not getattr(hs, "available", False):
        return BillerProxy(
            available=False, source_label=src,
            note=("The health_system_sam spine is unavailable offline, so the "
                  "biller-proxy insource ceiling cannot be read. Fallback: the "
                  "ceiling is low — hospitals rarely own ground fleets; the big-"
                  "IDN captive exceptions (Cleveland Clinic, Mayo, Allina) set it."))
    cl, cc, ch = hs.insource_ceiling
    al, ac, ah = hs.addressable_share
    return BillerProxy(
        available=True,
        ceiling_low=float(cl), ceiling_central=float(cc), ceiling_high=float(ch),
        addressable_low=float(al), addressable_central=float(ac),
        addressable_high=float(ah),
        proxy_rule=("Claims can show WHO billed each mission; '$ billed by a "
                    "health-system-affiliated NPI ⇒ that mission is insourced' is "
                    "the proxy the transcripts prescribe."),
        upper_bound_rationale=(
            "It is an UPPER BOUND, not a point estimate: a system that outsources "
            "does not bill, so the biller share caps insourcing — but a system NPI "
            "on the claim proves the system BILLED, not that its own crew ran the "
            "truck (a subcontracted or JV operator can bill under the system's "
            "arrangement), so true insourced volume is at or BELOW the ceiling."),
        limitations=[
            "Ceiling, not a point estimate — real insourcing ≤ the biller share; "
            "the addressable (outsourceable) market is correspondingly ≥ "
            "(1 − ceiling).",
            "A system-NPI biller can be a subcontracted / joint-venture operator "
            "billing under the system's arrangement — that inflates the biller "
            "share above the truly self-run volume.",
            "Network-gated offline: the precise biller share needs line-level "
            "claims with billing-NPI ownership (Komodo / CMS), which we do not "
            "have offline; the band here is the ILLUSTRATIVE ceiling from "
            "health_system_sam.",
            "Boundary: counts GROUND IFT dollars only (ex-air, ex-NEMT, ex-911), "
            "consistent with the ground-IFT TAM.",
        ],
        source_label=src,
        headline=(
            f"Health-system-biller insource CEILING ≈ {cc * 100:.1f}% (range "
            f"{cl * 100:.1f}-{ch * 100:.1f}%) of ground-IFT $ — the UPPER BOUND on "
            f"insourcing; the addressable outsourceable market is ≥ "
            f"{ac * 100:.1f}% (1 − ceiling)."),
        note=("The biller proxy is the insource UPPER BOUND, reused from "
              "health_system_sam so the sizing model and this framework cite ONE "
              "ceiling, not two. Read it as a ceiling: hospitals rarely own ground "
              "fleets, so most of the multi-system book is addressable. Every "
              "figure is ILLUSTRATIVE — the precise biller share is a network-"
              "gated claims build."))


# ═════════════════════════════════════════════════════════════════════════════
# (3) The claims gross-up — claims_grossup()  [undercount → true market]
# ═════════════════════════════════════════════════════════════════════════════
# The ILLUSTRATIVE fractions of the TRUE ground-IFT market that a claims-only
# extract MISSES, each tied to the documented understatement causes so the two
# modules stay consistent. Additive (never compounded), mirroring the cleaner's
# convention; the multiplier grosses a claims-observed figure back up to true.
_DIRECT_BILL_FRAC = (0.08, 0.12, 0.18)   # mom-and-pop invoices the hospital direct
_UNBILLED_FRAC = (0.03, 0.05, 0.08)      # hospital eats the cost / bundled, unbilled


@dataclass(frozen=True)
class GrossupComponent:
    """One documented reason claims under-count the IFT market, with an
    ILLUSTRATIVE missing-fraction band and the ``understatement`` cause IDs it is
    the IFT analog of (so this is a reference, not a reinvention)."""
    key: str                          # direct_bill | unbilled
    label: str
    frac_low: float
    frac_central: float
    frac_high: float
    mechanism: str
    named_basis: str
    understatement_cause_ids: Tuple[str, ...]
    understatement_causes: Tuple[str, ...]   # the cause NAMES from the taxonomy
    basis: str = LABEL_ILLUSTRATIVE


@dataclass
class ClaimsGrossup:
    available: bool
    components: List[GrossupComponent] = field(default_factory=list)
    total_missing_low: float = 0.0
    total_missing_central: float = 0.0
    total_missing_high: float = 0.0
    multiplier_low: float = 0.0       # 1 / (1 − missing); low missing ⇒ low mult
    multiplier_central: float = 0.0
    multiplier_high: float = 0.0
    # reference application against the GOV-anchored true-market TAM
    true_market_bn: Optional[float] = None       # ground_tam central
    claims_observed_bn: Optional[float] = None    # true × (1 − missing_central)
    missing_bn: Optional[float] = None
    taxonomy_source: str = ""
    taxonomy_available: bool = False
    source_label: str = ""
    headline: str = ""
    note: str = ""


# Authored gross-up components. Each names its mechanism + basis and links to the
# understatement taxonomy cause IDs it is the IFT-market analog of.
_GROSSUP_AUTHORED: Tuple[Dict[str, object], ...] = (
    {
        "key": "direct_bill",
        "label": "Direct-bill (mom-and-pop → hospital)",
        "frac": _DIRECT_BILL_FRAC,
        "mechanism": (
            "Fragmented mom-and-pop transport vendors often invoice the HOSPITAL "
            "under a facility contract instead of billing the payer, so the "
            "mission never reaches a payer claim and is invisible to a claims-only "
            "market build."),
        "named_basis": (
            "ILLUSTRATIVE — direct-to-hospital vendor billing share; the IFT "
            "analog of the cleaner's 'interfacility/transport legs billed "
            "separately and dropped' + NPI/TIN-fragmentation causes."),
        "cause_ids": ("ancillary_transport_dropped", "chain_parent_attribution_absent",
                     "npi_tin_fragmentation"),
    },
    {
        "key": "unbilled",
        "label": "Unbilled / eaten cost",
        "frac": _UNBILLED_FRAC,
        "mechanism": (
            "Some hospitals absorb the transport as an internal cost — bundled "
            "into the case rate or simply written off — and never bill any payer, "
            "so that volume never appears in claims at all."),
        "named_basis": (
            "ILLUSTRATIVE — hospital-absorbed / unbilled share; the IFT analog of "
            "the cleaner's 'self-pay / never billed' + 'capitated / bundled — no "
            "FFS claim' causes."),
        "cause_ids": ("self_pay_never_billed", "capitated_bundled_no_ffs"),
    },
)


@functools.lru_cache(maxsize=1)
def claims_grossup() -> ClaimsGrossup:
    """The claims-undercount gross-up — direct-bill + unbilled fractions that
    gross a claims-observed IFT market UP to the true market.

    Claims under-count because fragmented mom-and-pop vendors bill the hospital
    directly (never the payer) and some hospitals eat the cost — so
    ``true = claims_observed / (1 − direct_bill − unbilled)``. Each fraction is
    ILLUSTRATIVE with a named basis and is the IFT-market analog of a documented
    cause in ``rcm_mc/npi_cleaner/understatement.py`` (IMPORTED here, its cause
    NAMES pulled live, so this is a reference — not a parallel reinvention). The
    multiplier is applied against the GOV-anchored ground-IFT TAM as the true-
    market reference. Never raises; the core fractions render even if the cleaner
    import or the TAM is unavailable."""
    us = _understatement()
    by_id = getattr(us, "TAXONOMY_BY_ID", {}) if us is not None else {}
    tax_ok = bool(by_id)

    components: List[GrossupComponent] = []
    for a in _GROSSUP_AUTHORED:
        fl, fc, fh = a["frac"]  # type: ignore[misc]
        ids = tuple(a["cause_ids"])  # type: ignore[arg-type]
        # Pull the REAL cause names from the taxonomy so the wording stays
        # consistent with the cleaner; fall back to the id if it isn't present.
        names = tuple(getattr(by_id.get(cid), "name", cid) for cid in ids)
        components.append(GrossupComponent(
            key=str(a["key"]), label=str(a["label"]),
            frac_low=float(fl), frac_central=float(fc), frac_high=float(fh),
            mechanism=str(a["mechanism"]), named_basis=str(a["named_basis"]),
            understatement_cause_ids=ids, understatement_causes=names))

    miss_lo = sum(c.frac_low for c in components)
    miss_c = sum(c.frac_central for c in components)
    miss_hi = min(0.95, sum(c.frac_high for c in components))
    # multiplier = 1 / (1 − missing): more missing ⇒ larger gross-up.
    mult_lo = round(1.0 / (1.0 - miss_lo), 4)
    mult_c = round(1.0 / (1.0 - miss_c), 4)
    mult_hi = round(1.0 / (1.0 - miss_hi), 4)

    # Reference application: take the GOV-anchored ground-IFT TAM central as the
    # TRUE all-payer market; a claims-only build would observe only (1 − missing)
    # of it, and the gross-up recovers the rest.
    tam = _ground_tam()
    true_bn = claims_bn = missing_bn = None
    if tam is not None and getattr(tam, "available", False):
        true_bn = round(float(tam.allpayer_tam_bn_central), 2)
        claims_bn = round(true_bn * (1.0 - miss_c), 2)
        missing_bn = round(true_bn - claims_bn, 2)

    tax_src = ("cross-referenced to rcm_mc/npi_cleaner/understatement.py TAXONOMY "
               "(the 20-cause claims-understatement taxonomy) — these gross-up "
               "fractions are the IFT-market analog of its documented undercount "
               "causes, not a parallel reinvention"
               + ("" if tax_ok else " [taxonomy not loadable offline; cause names "
                  "fell back to their ids]"))

    ref = (f" A claims-only build off a true ${true_bn:.2f}B would capture only "
           f"~${claims_bn:.2f}B, missing ~${missing_bn:.2f}B."
           if true_bn is not None else "")
    headline = (
        f"Claims under-count the ground-IFT market by ~{miss_c * 100:.1f}% "
        f"(range {miss_lo * 100:.1f}-{miss_hi * 100:.1f}%): direct-bill "
        f"{_DIRECT_BILL_FRAC[1] * 100:.1f}% + unbilled {_UNBILLED_FRAC[1] * 100:.1f}%. "
        f"Gross-up ≈ {mult_c:.2f}x (range {mult_lo:.2f}-{mult_hi:.2f}x)." + ref)

    return ClaimsGrossup(
        available=True, components=components,
        total_missing_low=round(miss_lo, 4), total_missing_central=round(miss_c, 4),
        total_missing_high=round(miss_hi, 4),
        multiplier_low=mult_lo, multiplier_central=mult_c, multiplier_high=mult_hi,
        true_market_bn=true_bn, claims_observed_bn=claims_bn, missing_bn=missing_bn,
        taxonomy_source=tax_src, taxonomy_available=tax_ok,
        source_label=(
            "ILLUSTRATIVE · direct-bill + unbilled gross-up fractions (named "
            "basis each), cross-referenced to the npi_cleaner/understatement.py "
            "20-cause taxonomy; reference market = the GOV-anchored ground-IFT TAM "
            "(ift_analytics.ground_tam)"),
        headline=headline,
        note=("Because claims can only see WHAT was billed to a payer, they "
              "systematically UNDER-count IFT: mom-and-pop vendors direct-bill the "
              "hospital and some hospitals eat the cost. The claims-observed "
              "market — and therefore the biller-proxy insource ceiling read off "
              "it — must be grossed UP by this multiplier to reach the true "
              "market. Fractions are ILLUSTRATIVE with a named basis and mirror "
              "the documented cleaner causes; the true-market reference is the "
              "GOV-anchored TAM. Additive (not compounded), the conservative "
              "convention the cleaner uses."))


# ═════════════════════════════════════════════════════════════════════════════
# (4) Per-metro insourcing read — market_insourcing()
# ═════════════════════════════════════════════════════════════════════════════
# Map each ift_geo insource archetype to a framework band + an ILLUSTRATIVE
# insourced-volume-share band + the volume-based (not asset-based) read. The
# insourced shares stay inside the mapped band's global range for coherence.
_CLASS_TO_BAND: Dict[str, Tuple[str, float, float, str]] = {
    "insourced-heavy": (
        BAND_MOSTLY_INSOURCED, 0.65, 0.90,
        "By transport VOLUME this is a mostly-/fully-insourced market: the anchor "
        "systems run large captive fleets (some even sell CCT outward), so the "
        "winnable book is the SNF/post-acute discharge RESIDUAL — not the captive "
        "tertiary transfer stream. Displacing captive volume needs a system to "
        "strategically outsource what it built to own."),
    "mixed-insource-residual": (
        BAND_MOSTLY_OUTSOURCED, 0.25, 0.45,
        "Asset ownership over-states insourcing here: the anchors OWN critical-"
        "care units and self-run their high-acuity legs, but by mission VOLUME the "
        "majority — non-emergent SNF-discharge / repatriation — is outsourced to "
        "the private pool. A hybrid that reads mostly-OUTSOURCED on volume despite "
        "the visible system-owned trucks."),
    "insourced-top-outsourced-bottom": (
        BAND_MOSTLY_OUTSOURCED, 0.15, 0.35,
        "The textbook volume-vs-asset split: the quaternary systems OWN high-acuity "
        "CCT + air (a hard insource ceiling), but that is a small slice of missions; "
        "the high-VOLUME routine BLS/ALS discharge + SNF/dialysis back-transfer is "
        "outsourced. By volume the market is mostly-OUTSOURCED even though every "
        "anchor owns ambulances."),
    "mixed-confirmed-outsource": (
        BAND_MOSTLY_OUTSOURCED, 0.05, 0.20,
        "Confirmed outsourced at the volume level: at least one anchor runs an "
        "embedded outsourced partner for the routine book and the largest systems' "
        "routine IFT is contracted out; system-OWNED volume is minimal."),
    "two-anchor-contestable": (
        BAND_MOSTLY_OUTSOURCED, 0.05, 0.20,
        "Outsourced by volume: neither anchor runs a material captive IFT fleet, so "
        "winning either system's routine BLS/ALS discharge book captures a large "
        "share. Asset ownership is negligible; the classification is a volume read."),
    "outsourced-two-horse": (
        BAND_FULLY_OUTSOURCED, 0.00, 0.05,
        "Fully outsourced by volume: hospital IFT is contracted to a two-operator "
        "private field; the systems own no material transport fleet, so essentially "
        "all mission volume is addressable."),
    "outsourced-fragmented": (
        BAND_FULLY_OUTSOURCED, 0.00, 0.05,
        "Fully outsourced by volume: private-dominant with no system-owned fleet of "
        "consequence; the whole routine book is contestable and the fragmented "
        "private pool is the roll-up target."),
    "outsourced-incumbent": (
        BAND_FULLY_OUTSOURCED, 0.02, 0.05,
        "Fully outsourced by volume, but a workflow-integrated PRIVATE incumbent "
        "(co-branding + embedded coordinators) holds the book; the system insources "
        "~nothing, so the contest is operator-vs-operator, not insource-vs-outsource."),
    "bi-state-outsourced": (
        BAND_FULLY_OUTSOURCED, 0.02, 0.05,
        "Outsourced by volume for adult IFT (dual-licensure-gated to the incumbent), "
        "with ONE walled-off system-insourced niche (peds/neonatal CCT). The niche "
        "is low-volume, so the market reads fully-OUTSOURCED on total mission volume."),
    "public-utility-mixed": (
        BAND_MOSTLY_OUTSOURCED, 0.05, 0.20,
        "Mixed by volume: a public-utility county service carries part of the book "
        "(a form of outsourcing to the public entity) while system-directed volume "
        "moves to privates; system-OWNED insourced volume is low — the Wesley/HCA→"
        "AMR flip proves the moat tracks ownership INTENT, not assets."),
    "rural-contract-gated": (
        BAND_FULLY_OUTSOURCED, 0.00, 0.05,
        "Fully outsourced by volume under an exclusive county/hospital contract to a "
        "private or municipal service; the hospital owns no fleet, so the entire "
        "(thin, long-leg) book is addressable but gated behind the exclusive "
        "contract."),
}
_CLASS_TO_BAND_DEFAULT: Tuple[str, float, float, str] = (
    BAND_MOSTLY_OUTSOURCED, 0.10, 0.30,
    "Outsourced-leaning by volume; the addressable book is the routine discharge + "
    "back-transfer residual.")


@dataclass(frozen=True)
class MarketInsourceRow:
    """One footprint metro's insourcing read.

    ``insource_class`` is the ift_geo insource-vs-outsource archetype — PUBLIC-WEB
    per ift_geo's own header (the per-metro insource read is drawn from public/
    company sources, NOT a CMS-computed figure); the framework band + insourced-
    volume-share + volume_read are ILLUSTRATIVE; the contestable residual reuses
    ``sam_formula``'s s(m); ``insource_read`` / ``moat_note`` are PUBLIC-WEB (ift_geo)."""
    name: str
    region_label: str
    insource_class: str
    framework_band: str
    framework_band_label: str
    insourced_volume_share_low: float
    insourced_volume_share_high: float
    contestable_residual_share: Optional[float]   # s(m) (ILLUSTRATIVE, ift_analytics)
    volume_read: str
    insource_read: str                            # PUBLIC-WEB (ift_geo)
    moat_note: str                                # PUBLIC-WEB (ift_geo)
    names_basis: str = PUBLIC_WEB_NOTE
    basis: str = LABEL_ILLUSTRATIVE
    source_label: str = ""


@dataclass
class MarketInsourcing:
    available: bool
    rows: List[MarketInsourceRow] = field(default_factory=list)
    band_counts: Dict[str, int] = field(default_factory=dict)
    source_label: str = ""
    note: str = ""


@functools.lru_cache(maxsize=1)
def market_insourcing() -> MarketInsourcing:
    """Per-metro insource-vs-outsource read across the footprint.

    For each ift_geo metro: the structural archetype (insource_class), the
    framework band it maps to, the ILLUSTRATIVE insourced-VOLUME-share band, the
    volume-based (not asset-based) read, and the contestable residual (the s(m)
    serviceable share reused from ``ift_analytics.sam_formula``). The
    ``insource_read`` / moat prose are PUBLIC-WEB (ift_geo). Degrades to
    ``available=False`` if ift_geo is unreadable — never raises."""
    src = ("ILLUSTRATIVE · per-metro insourced-VOLUME-share read keyed to the "
           "ift_geo insource archetype; contestable residual = s(m) serviceable "
           "share (ift_analytics.sam_formula); insource_class, insource_read & moat "
           "PUBLIC-WEB (ift_geo, named honestly)")
    markets = _markets()
    if not markets:
        return MarketInsourcing(
            available=False, source_label=src,
            note="ift_geo MARKETS unavailable offline — per-metro insourcing "
                 "cannot be read.")

    s_by_metro = _serviceable_share_by_metro()
    rows: List[MarketInsourceRow] = []
    band_counts: Dict[str, int] = {k: 0 for k in _BAND_ORDER}
    for md in markets:
        band, lo, hi, read = _CLASS_TO_BAND.get(md.insource_class,
                                                _CLASS_TO_BAND_DEFAULT)
        band_counts[band] = band_counts.get(band, 0) + 1
        rows.append(MarketInsourceRow(
            name=md.name, region_label=md.region_label,
            insource_class=md.insource_class,
            framework_band=band, framework_band_label=_BAND_LABEL[band],
            insourced_volume_share_low=lo, insourced_volume_share_high=hi,
            contestable_residual_share=s_by_metro.get(md.name),
            volume_read=read, insource_read=md.insource_read,
            moat_note=md.moat_note,
            source_label=(
                f"ILLUSTRATIVE · {_BAND_LABEL[band]} "
                f"({lo * 100:.0f}-{hi * 100:.0f}% insourced by volume) · "
                "insource_read PUBLIC-WEB (ift_geo)")))

    return MarketInsourcing(
        available=True, rows=rows, band_counts=band_counts, source_label=src,
        note=(f"Per-metro insourcing across all {len(markets)} footprint metros, "
              "classified by transport VOLUME (not asset ownership). The band + "
              "insourced-share are ILLUSTRATIVE; the contestable residual reuses "
              "the sizing model's s(m); the insource_read / moat are PUBLIC-WEB "
              "(ift_geo). Most metros read outsourced or mostly-outsourced by "
              "volume — the routine book is the addressable market — with the "
              "Twin Cities / Rochester captive systems the insourced exceptions."))
