"""IFT player tiers — the public-data guidance layer for sizing operators.

The question this module answers: given a ground-medical-transport operator,
*which* public data asset actually sees it, and how do you size it? The answer
is **tier-dependent**, and getting the tier wrong is how a naive analysis
misprices the market. This module encodes the four commercial tiers
(National / Scaled-regional / Subscaled-regional / Local mom-and-pop; hospital
captive carried as context) with, for each tier, its **public-data
fingerprint** (how it shows up in NPPES / CMS / PECOS / QCEW), the asset to
size it with, and the *systematic bias* the public record introduces.

It refines the ``ift_competitive`` archetypes (which split National / Scaled-
regional / mom-and-pop) by adding the **subscaled-regional** tier between them,
and it operationalises Run 8 (DELTA_NOTE_v4_4: fleet beats licensed-EMTs; the
national brands are invisible in NPPES) and Finding #46 (the supplier universes
must never be mixed) into an explicit sizing recipe per tier.

Provenance discipline matches the rest of the workstream: every value carries a
basis chip — OBSERVED (a primary pull we ran: the NPPES brand probes,
2026-07-20), CLAIMED (company self-report), or DERIVED/MODELED (a band we
reasoned, quarantined until a measured panel replaces it). ``source_label``
names the basis; the accessor **degrades, never raises**.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

# ── OBSERVED: live NPPES NPI Registry API (v2.1) organization-name probes,
# run 2026-07-20, enumeration_type=NPI-2. These are the tier fingerprints.
# (value = NPIs returned for the name query; note = what they actually are.)
NPPES_PROBE: Dict[str, Dict[str, object]] = {
    "Global Medical Response*": {"npis": 0, "tier": "national",
        "note": "parent holding co — no operating NPI at all"},
    "Rural/Metro / Rural Metro": {"npis": 0, "tier": "national",
        "note": "major GMR ground brand — nothing under its own name"},
    "American Medical Response": {"npis": 65, "tier": "national",
        "note": "~15 legal names + local DBAs (Randle Eastern, LifeFleet SE, "
                "Mercy, Metro, ParaMed, Hank's) matched only as former/other name"},
    "Priority Ambulance*": {"npis": 8, "tier": "national",
        "note": "only 3 (Shoals Ambulance LLC) are the real Knoxville roll-up; "
                "the other 5 are unrelated 'Priority Ambulance' name-collisions"},
    "Acadian Ambulance*": {"npis": 12, "tier": "scaled_regional",
        "note": "clean, findable — parent + state-suffixed LLCs (LA/TX/MS/TN/AL)"},
    "Falck*": {"npis": 17, "tier": "scaled_regional",
        "note": "~10 regional ambulance corps (Falck [region] Corp) + same-name "
                "non-ambulance noise (Falck Eye Center, Falck Therapy)"},
}


@dataclass(frozen=True)
class Tier:
    """One commercial IFT operator tier + its public-data guidance.

    ``fingerprint``/``examples`` carry OBSERVED + CLAIMED facts; the bands are
    DERIVED (indicative, not shipped measurements).
    """
    key: str
    rank: int                 # 1 = national … 4 = mom-and-pop
    name: str
    examples: str             # named operators (CLAIMED scale where quoted)
    transports_band: str      # DERIVED band, annual transports
    fleet_band: str           # DERIVED band, vehicles
    revenue_band: str         # DERIVED band
    entities_band: str        # NPIs per operator (OBSERVED where probed)
    npi_fingerprint: str      # how it appears in NPPES (OBSERVED)
    best_asset: str           # the public data asset that actually sees it
    sizing_method: str        # how to size an operator in this tier
    systematic_bias: str      # what the public record gets wrong


@dataclass
class PlayerTierSet:
    available: bool
    source_label: str
    tiers: List[Tier] = field(default_factory=list)
    nppes_probe: Dict[str, Dict[str, object]] = field(default_factory=dict)


# ── The tiers (rank order). Bands are DERIVED and deliberately wide; the
# named-operator anchors are CLAIMED (company self-reports) or OBSERVED
# (NPPES probe counts). Nothing here is quoted as a market measurement.
_TIERS: List[Tier] = [
    Tier(
        key="national", rank=1, name="National platform",
        examples="GMR/AMR (CLAIMED: 7,000+ vehicles · ~6.0M transports · 40 "
                 "states) · Priority Ambulance (CLAIMED: ~400 vehicles · 610K "
                 "transports · 22 brands / 15 states). Multi-region roll-up + "
                 "national-account contracting — not necessarily largest volume.",
        transports_band="~0.6M–6M+ (DERIVED)",
        fleet_band="~400–7,000+ vehicles (CLAIMED)",
        revenue_band="~$0.3B–multi-$B (DERIVED)",
        entities_band="tens–hundreds of NPIs, scattered across brands",
        npi_fingerprint="INVISIBLE by parent name — GMR* → 0, Rural/Metro → 0, "
                        "Priority Ambulance* → 8 of which only 3 real (OBSERVED). "
                        "Grows by acquiring and keeping local brands.",
        best_asset="Fleet disclosures + SEC/PE filings + CMS Medicare MUP "
                   "(A0425–A0434) aggregated through an OWNERSHIP CROSSWALK.",
        sizing_method="Σ permitted vehicles × transports-per-vehicle band, "
                      "rolled to the parent via an ownership map (NPPES has no "
                      "owner field). Never name-match in NPPES.",
        systematic_bias="Name-keyed counting undercounts consolidated scale "
                        "~10–50× and misses the parent entirely (Run 8).",
    ),
    Tier(
        key="scaled_regional", rank=2, name="Scaled regional private",
        examples="Acadian (CLAIMED: 750 ambulances · ~800K transports · 4 "
                 "states) · Falck US (regional corps) · DocGo/DCGO (SEC: ~$190M "
                 "transport segment) · Superior Air-Ground · AmeriPro.",
        transports_band="~300K–1M (DERIVED)",
        fleet_band="~200–800 vehicles (CLAIMED)",
        revenue_band="~$150M–$750M (DERIVED)",
        entities_band="~10–20 NPIs under one parent name",
        npi_fingerprint="FINDABLE — Acadian* → 12 clean state-suffixed LLCs; "
                        "Falck* → ~10 regional corps (OBSERVED). Requires a "
                        "wildcard, and you must strip same-name-different-company "
                        "noise (Falck Eye Center).",
        best_asset="NPPES (parent + regional-suffix entities) + CMS Medicare "
                   "MUP per NPI + company disclosures.",
        sizing_method="Sum the parent's regional-entity NPIs' CMS transport "
                      "volume; cross-check against disclosed fleet × ratio.",
        systematic_bias="Footprint fragmented across state LLCs; name collisions "
                        "inject false positives — filter by taxonomy 3416* and "
                        "address, not name alone.",
    ),
    Tier(
        key="subscaled_regional", rank=3, name="Subscaled regional private",
        examples="MMT/Midwest Medical Transport (CLAIMED: 500+ vehicles · 200K+ "
                 "missions; 3rd-party revenue $100M–$296M — disagrees ~3×) · "
                 "Ryan Brothers · Bell Ambulance · Physicians Ambulance.",
        transports_band="~50K–250K (DERIVED)",
        fleet_band="~30–200 vehicles (DERIVED)",
        revenue_band="~$25M–$150M (DERIVED)",
        entities_band="~10–30 NPIs, single corridor",
        npi_fingerprint="PARTIALLY findable — the corridor NPIs surface by name "
                        "(MMT ~24 org NPIs across 11 states) but the NPI count "
                        "undercounts vehicles ~20× (repo exhibit).",
        best_asset="State EMS licensing (permitted vehicles) + CMS Medicare MUP "
                   "+ IRS 990s. NOT third-party revenue estimators.",
        sizing_method="State-permitted vehicles × transports-per-vehicle band; "
                      "corroborate with CMS volume. Treat every third-party "
                      "revenue figure as unusable (they disagree ~3×).",
        systematic_bias="Third-party revenue/employee estimates diverge wildly "
                        "(Growjo vs ZoomInfo vs LeadIQ ~3×); NPIs undercount "
                        "vehicles ~20×.",
    ),
    Tier(
        key="mom_and_pop", rank=4, name="Local mom-and-pop private",
        examples="Single-market family-owned squads (Curtis, Paratech, Ultra "
                 "EMS, Front Line EMS, Midwest Ambulance of Iowa, …) — the "
                 "fragmented consolidation base.",
        transports_band="<~20K (DERIVED)",
        fleet_band="~1–10 vehicles (DERIVED)",
        revenue_band="<~$10M (DERIVED)",
        entities_band="1–3 NPIs",
        npi_fingerprint="Individually findable but not worth per-firm work — "
                        "the LONG TAIL. Collectively they are most of the "
                        "universe (Finding #46: ~10,465 PECOS suppliers / 8,721 "
                        "billing NPIs / 5,820 QCEW establishments — three "
                        "different objects that must never be mixed).",
        best_asset="Aggregate/statistical: PECOS enrollment + QCEW establishment "
                   "counts + state rosters — sized as a pool, not per firm.",
        sizing_method="Size the pool statistically (universe counts × average "
                      "small-operator volume); do not attempt per-firm sizing.",
        systematic_bias="Universe mismatch — enrollment ≠ billing identity ≠ "
                        "worksite; picking any one as 'the number of ambulance "
                        "companies' over/under-counts the tail.",
    ),
]

_SRC = ("FRAMEWORK · IFT player tiers + public-data guidance. NPPES brand "
        "probes OBSERVED (NPI Registry API v2.1, 2026-07-20); operator scale "
        "anchors CLAIMED (company self-reports/SEC); tier bands DERIVED "
        "(indicative, quarantined until a measured panel replaces them). "
        "Refines ift_competitive archetypes; operationalises DELTA_NOTE_v4_4 "
        "(Run 8) + Finding #46.")


def player_tiers() -> PlayerTierSet:
    """The four commercial IFT tiers with their public-data guidance.

    Degrades to ``available=False`` with a ``source_label`` rather than raising,
    per the workstream contract.
    """
    try:
        return PlayerTierSet(
            available=True, source_label=_SRC,
            tiers=list(_TIERS), nppes_probe=dict(NPPES_PROBE),
        )
    except Exception as exc:  # noqa: BLE001 — never take the report down
        return PlayerTierSet(
            available=False,
            source_label=f"player_tiers unavailable: {type(exc).__name__}",
        )
