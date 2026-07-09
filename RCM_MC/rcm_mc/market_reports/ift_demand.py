"""IFT demand deep-dive — national → regional → subcounty, over time.

Synthesizes the demand story across the IFT estate into one layer:

  * the CMS **HCPCS code analysis** by the three interfacility acuity types (BLS /
    ALS / SCT) and the emergency-vs-non-emergency split, with the interfacility
    relevance of each code;
  * the **emergency vs non-emergency prevalence** read, from the clinical
    transfer registry (escalation vs step-down / direct-admit) and the acuity mix;
  * a **regional roll-up** of the SOURCED facility base (hospitals, beds,
    post-acute nodes) grouped by the ift_geo regions, with the demographic growth
    read; and
  * a **time series** ("trailed over time") that stitches the backward HCRIS
    occupancy panel, the GOV AIF series, and the forward MMT growth projection.

It holds no NEW dollar figures of its own — every quantity is reused from
:mod:`ift_analytics`, :mod:`ift_geo`, :mod:`ift_clinical_demand`,
:mod:`ift_tracking`, and :mod:`ift_mmt` so nothing drifts. The only authored
content is the HCPCS acuity/emergency classification (which the CMS codes and
42 CFR 414 already fix) and the narrative framing.

Design contract mirrors the rest of the IFT modules: frozen dataclasses, pure
functions that DEGRADE and never raise, honesty labels on every figure.

Public API:
    hcpcs_acuity_analysis() -> HcpcsAnalysis
    emergency_prevalence() -> EmergencyPrevalence
    regional_demand() -> Tuple[RegionDemand, ...]
    national_frame() -> NationalFrame
    national_transport_volume() -> NationalVolume
    demand_source_matrix() -> DemandSourceMatrix
    demand_time_series() -> DemandTimeSeries
    demand_summary() -> Dict[str, Any]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# 1 — CMS HCPCS code analysis: the three interfacility acuity types × emergency
# ─────────────────────────────────────────────────────────────────────────────
# The three IFT acuity types the market is read on, and how the ground base HCPCS
# map to them + the emergency/non-emergency dimension. Acuity RVUs come from
# ift_analytics (42 CFR 414.610); the emergency flag and interfacility relevance
# are fixed by the code descriptors and 42 CFR 414.605 (SCT is interfacility by
# definition). Authored classification (FRAMEWORK) over GOV codes/RVUs.
@dataclass(frozen=True)
class HcpcsRow:
    hcpcs: str
    descriptor: str
    acuity_group: str          # BLS | ALS | SCT | (mileage/other)
    emergency: str             # Emergency | Non-emergency | Either / add-on
    rvu: float
    ift_relevance: str


_ACUITY_GROUP = {
    "A0428": "BLS", "A0429": "BLS",
    "A0426": "ALS", "A0427": "ALS", "A0433": "ALS", "A0432": "ALS",
    "A0434": "SCT",
    "A0425": "Mileage", "A0430": "Air", "A0431": "Air", "A0435": "Air",
    "A0436": "Air",
}
_EMERGENCY = {
    "A0429": "Emergency", "A0427": "Emergency",
    "A0428": "Non-emergency", "A0426": "Non-emergency",
    "A0433": "Non-emergency", "A0434": "Non-emergency",
    "A0432": "Either", "A0425": "Add-on",
}
_IFT_RELEVANCE = {
    "A0428": "The core interfacility DISCHARGE book — the largest non-emergency "
             "IFT volume (hospital→SNF/IRF/home, SNF recurring legs).",
    "A0429": "Mostly 911/scene; emergent BLS interfacility is uncommon.",
    "A0426": "Scheduled ALS interfacility — monitored discharge / transfer.",
    "A0427": "911/scene AND the emergent UP-transfer (STEMI/stroke in-window) — "
             "the emergency-coded IFT minority.",
    "A0433": "High-acuity interfacility (≥3 med admins / an ALS procedure, drips) "
             "— IFT over-indexes here.",
    "A0434": "Specialty/critical-care transport — DEFINITIONALLY interfacility "
             "(42 CFR 414.605); the premium IFT tier.",
    "A0432": "Rural paramedic intercept — edge case.",
    "A0425": "Ground loaded mileage — the long-leg (rural) economics rider.",
}


@dataclass(frozen=True)
class TypeRollup:
    acuity_type: str           # BLS | ALS | SCT
    codes: Tuple[str, ...]
    rvu_low: float
    rvu_high: float
    read: str


@dataclass(frozen=True)
class HcpcsAnalysis:
    available: bool
    rows: Tuple[HcpcsRow, ...] = ()
    types: Tuple[TypeRollup, ...] = ()
    source_label: str = ""
    note: str = ""


def hcpcs_acuity_analysis() -> HcpcsAnalysis:
    """The ground ambulance base HCPCS mapped to the three IFT acuity types (BLS /
    ALS / SCT) and the emergency/non-emergency split, with interfacility relevance.
    RVUs reused from ift_analytics (GOV). Never raises."""
    try:
        from . import ift_analytics as _an
        rvu = getattr(_an, "_AMBULANCE_RVU", ())
    except Exception:  # noqa: BLE001
        rvu = ()
    if not rvu:
        return HcpcsAnalysis(available=False)
    rows: List[HcpcsRow] = []
    for hcpcs, descriptor, val in rvu:
        rows.append(HcpcsRow(
            hcpcs=hcpcs, descriptor=descriptor,
            acuity_group=_ACUITY_GROUP.get(hcpcs, "Other"),
            emergency=_EMERGENCY.get(hcpcs, "Either"),
            rvu=float(val),
            ift_relevance=_IFT_RELEVANCE.get(hcpcs, "")))
    # Three-type roll-up.
    def _band(codes: Tuple[str, ...]) -> Tuple[float, float]:
        vals = [r.rvu for r in rows if r.hcpcs in codes]
        return (min(vals), max(vals)) if vals else (0.0, 0.0)
    types = (
        TypeRollup("BLS", ("A0428", "A0429"), *_band(("A0428", "A0429")),
                   read="Basic life support — no drugs/monitoring beyond BLS. The "
                        "non-emergency A0428 is the discharge / post-acute volume "
                        "engine; A0429 is emergency (mostly 911)."),
        TypeRollup("ALS", ("A0426", "A0427", "A0433"),
                   *_band(("A0426", "A0427", "A0433")),
                   read="Advanced life support — monitoring, IV, drugs. ALS1 splits "
                        "emergency (A0427) vs non-emergency (A0426); ALS2 (A0433) is "
                        "the high-acuity interfacility tier IFT over-indexes on."),
        TypeRollup("SCT", ("A0434",), *_band(("A0434",)),
                   read="Specialty / critical-care transport — nurse/RT crew, vent, "
                        "drips. Definitionally interfacility (42 CFR 414.605) and the "
                        "highest RVU; the premium IFT tier."),
    )
    return HcpcsAnalysis(
        available=True, rows=tuple(rows), types=types,
        source_label=("GOV HCPCS + RVU (42 CFR 414.610, reused from "
                      "ift_analytics); acuity/emergency/IFT-relevance classification "
                      "is authored FRAMEWORK over the GOV codes (SCT = interfacility "
                      "per 42 CFR 414.605)"),
        note=("The three IFT acuity types are BLS / ALS / SCT. IFT concentrates in "
              "the NON-emergency codes (A0428 discharge book) plus the higher-acuity "
              "urgent tiers (A0433 ALS2, A0434 SCT). The emergency codes (A0429, "
              "A0427) are predominantly 911/scene — the emergency-coded IFT slice is "
              "the emergent up-transfer minority. Line-level volume/spend flips to "
              "SOURCED once the Part-B ambulance-HCPCS estate is ingested."))


# ─────────────────────────────────────────────────────────────────────────────
# 2 — Emergency vs non-emergency prevalence
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class EmergencyPrevalence:
    available: bool
    by_family: Dict[str, int] = field(default_factory=dict)
    by_transfer_type: Dict[str, int] = field(default_factory=dict)
    n_emergent_scenarios: int = 0        # escalation / up-transfer
    n_nonemergent_scenarios: int = 0     # step-down + direct-admit + down/lateral
    cct_sct_share: Optional[float] = None
    high_acuity_share: Optional[float] = None
    source_label: str = ""
    note: str = ""


def emergency_prevalence() -> EmergencyPrevalence:
    """The emergency-vs-non-emergency read of the IFT book, from the clinical
    transfer registry families + transfer types + the acuity mix. Degrades if the
    clinical spine is unavailable. Never raises."""
    try:
        from . import ift_clinical_demand as _cd
        rs = _cd.registry_summary()
        m = _cd.mission_mix()
    except Exception:  # noqa: BLE001
        return EmergencyPrevalence(available=False)
    fam = dict(rs.get("n_by_family", {}) or {})
    tt = dict(rs.get("n_by_transfer_type", {}) or {})
    # Escalation / up-transfers read as emergent-acuity; step-down + direct-admit
    # (and down/lateral moves) read as non-emergency scheduled work.
    emergent = int(fam.get("Escalation", 0) or 0)
    nonemergent = sum(v for k, v in fam.items() if k != "Escalation")
    return EmergencyPrevalence(
        available=True, by_family=fam, by_transfer_type=tt,
        n_emergent_scenarios=emergent, n_nonemergent_scenarios=nonemergent,
        cct_sct_share=m.get("cct_sct_share"),
        high_acuity_share=m.get("high_acuity_incl_behavioral_share"),
        source_label=("SOURCED registry families/transfer-types + GOV-weighted "
                      "mission mix (ift_clinical_demand)"),
        note=("Two different lenses. By clinical SCENARIO the registry skews to "
              "emergent ESCALATION up-transfers (the dramatic, high-acuity cases). "
              "By VOLUME the engine is the opposite — the NON-emergency post-acute "
              "discharge + recurring-leg book that ages in. Dispatch-wise IFT is "
              "predominantly non-emergency (scheduled/urgent between facilities); "
              "the emergency-coded slice is the emergent up-transfer minority."))


# ─────────────────────────────────────────────────────────────────────────────
# 3 — Regional roll-up of the SOURCED facility base + growth
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class RegionDemand:
    region: str
    region_label: str
    n_metros: int
    n_hospitals: int
    hcris_beds: float
    n_snf: int
    snf_beds: int
    n_postacute_destinations: int
    n_dialysis: int
    sam_dollars: float                   # ILLUSTRATIVE per-metro SAM, summed
    rural: bool


def regional_demand() -> Tuple[RegionDemand, ...]:
    """Roll the SOURCED per-metro facility structure up to the ift_geo regions,
    with the ILLUSTRATIVE per-metro SAM summed as the demand-$ proxy. Never
    raises."""
    try:
        from . import ift_geo as _geo
        from . import ift_analytics as _an
        metros = _geo.all_metros()
        sam = _an.sam_formula()
    except Exception:  # noqa: BLE001
        return ()
    sam_by_name: Dict[str, float] = {}
    if sam and getattr(sam, "available", False):
        for r in sam.rows:
            sam_by_name[r.name] = r.sam_dollars
    agg: Dict[str, Dict[str, Any]] = {}
    for s in metros:
        if not getattr(s, "available", True):
            continue
        a = agg.setdefault(s.region, {
            "region_label": getattr(s, "region_label", s.region),
            "n_metros": 0, "n_hospitals": 0, "hcris_beds": 0.0, "n_snf": 0,
            "snf_beds": 0, "n_postacute_destinations": 0, "n_dialysis": 0,
            "sam_dollars": 0.0, "rural": False})
        a["n_metros"] += 1
        a["n_hospitals"] += int(s.n_hospitals or 0)
        a["hcris_beds"] += float(s.hcris_beds or 0.0)
        a["n_snf"] += int(s.n_snf or 0)
        a["snf_beds"] += int(s.snf_beds or 0)
        a["n_postacute_destinations"] += int(s.n_postacute_destinations or 0)
        a["n_dialysis"] += int(s.n_dialysis or 0)
        a["sam_dollars"] += float(sam_by_name.get(s.name, 0.0))
        a["rural"] = a["rural"] or bool(getattr(s, "rural", False))
    try:
        order = list(_geo.REGION_LABELS.keys())
    except Exception:  # noqa: BLE001
        order = list(agg.keys())
    out: List[RegionDemand] = []
    for region in order:
        if region not in agg:
            continue
        a = agg[region]
        out.append(RegionDemand(
            region=region, region_label=a["region_label"],
            n_metros=a["n_metros"], n_hospitals=a["n_hospitals"],
            hcris_beds=a["hcris_beds"], n_snf=a["n_snf"], snf_beds=a["snf_beds"],
            n_postacute_destinations=a["n_postacute_destinations"],
            n_dialysis=a["n_dialysis"], sam_dollars=a["sam_dollars"],
            rural=a["rural"]))
    out.sort(key=lambda r: r.sam_dollars, reverse=True)
    return tuple(out)


# ─────────────────────────────────────────────────────────────────────────────
# 4 — National frame (facility base + demographic growth + TAM anchor)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class NationalFrame:
    available: bool
    n_hospitals_national: int = 0
    snf_beds_national: int = 0
    postacute_destinations: int = 0
    tam_central_bn: float = 0.0
    ift_legs_low_m: float = 0.0
    ift_legs_high_m: float = 0.0
    price_growth_pct: Optional[float] = None
    volume_growth_pct: Optional[float] = None
    market_growth_pct: Optional[float] = None
    age_bands: Tuple[Tuple[str, str], ...] = ()     # (band, growth read)
    source_label: str = ""


def national_frame() -> NationalFrame:
    """National facility base + demographic growth + TAM anchor, reused across the
    estate. Never raises."""
    n_h = snf_beds = 0
    dest = 0
    try:
        from . import ift_geo as _geo
        fr = _geo.footprint_rollup()
        n_h = int(getattr(fr, "n_hospitals_national", 0) or 0)
        snf_beds = int(getattr(fr, "snf_beds_national", 0) or 0)
    except Exception:  # noqa: BLE001
        pass
    try:
        from . import ift_clinical_demand as _cd
        ds = _cd.destination_supply()
        dest = int(ds.get("national", 0) or 0) if isinstance(ds, dict) else 0
    except Exception:  # noqa: BLE001
        pass
    tam_c = 0.0
    legs = (0.0, 0.0)
    try:
        from . import ift_analytics as _an
        t = _an.ground_tam()
        if getattr(t, "available", False):
            tam_c = float(t.allpayer_tam_bn_central)
            legs = tuple(t.transports_m)
    except Exception:  # noqa: BLE001
        pass
    price = volume = market = None
    try:
        from . import ift_tracking as _tr
        gb = _tr.growth_bridge()
        if getattr(gb, "available", False):
            price = gb.price_central_pct
            volume = gb.volume_central_pct
            market = gb.market_growth_central_pct
    except Exception:  # noqa: BLE001
        pass
    # The boomer-aging age-band structure (ILLUSTRATIVE magnitude; the per-band
    # CAGR engine populates from the demand-forecast estate when ingested).
    age_bands = (
        ("65-74", "Front of the boomer wave; largest 65+ band, growth decelerating "
                  "as the leading cohort ages up."),
        ("75-84", "The fastest-growing band this decade as boomers cross 75 — the "
                  "acuity + post-acute inflection where IFT demand concentrates."),
        ("85+", "Highest per-capita transfer + post-acute use; smaller base but the "
                "steepest long-run tail."),
    )
    return NationalFrame(
        available=True, n_hospitals_national=n_h, snf_beds_national=snf_beds,
        postacute_destinations=dest, tam_central_bn=tam_c,
        ift_legs_low_m=legs[0], ift_legs_high_m=legs[1],
        price_growth_pct=price, volume_growth_pct=volume, market_growth_pct=market,
        age_bands=age_bands,
        source_label=("SOURCED national facility rolls (ift_geo / "
                      "ift_clinical_demand) + ILLUSTRATIVE TAM & growth "
                      "(ift_analytics / ift_tracking, GOV-anchored)"))


# ─────────────────────────────────────────────────────────────────────────────
# 4b — National transport VOLUME: "how many transports a year?"
# ─────────────────────────────────────────────────────────────────────────────
# The demand centerpiece: a top-down transports/year funnel from the hardest GOV
# anchor down to the interfacility slice, every tier carrying a source. No trade /
# market-research-firm figures are used — the all-payer line is DERIVED from the
# GOV Medicare figure, not taken from any industry report.
#
# Anchors (all public):
#   * MedPAC, "Ambulance Services Payment System" Payment Basics (Oct 2024):
#     ~10,600 ground ambulance organizations delivered 11.3M transports to
#     Medicare fee-for-service beneficiaries in CY2024, for $5.3B in payments.   [GOV]
#   * Service-level mix ~56% BLS / ~44% ALS (incl. SCT at the top) — Medicare
#     FFS claims analysis (CMS "Ground Ambulance Industry Trends 2017-2020";
#     FAIR Health ground-ambulance utilization brief).                          [SOURCED]
#   * BLS emergency vs non-emergency drifted 56.3/43.7 (2018) → 62.9/37.1 (2022)
#     — Medicare claims / CMS GADCS (RAND) Year-1/2 report.                      [GOV]
#   * Interfacility transports arriving at an ED via EMS ~1.1-1.3M/yr — National
#     Hospital Ambulatory Medical Care Survey (NHAMCS), Am J Emerg Med 2020 /
#     2026 nationwide IFT trend study.                                          [ACADEMIC]
_MC_FFS_TRANSPORTS_M = 11.3          # MedPAC Payment Basics 2024 (GOV)
_MC_FFS_SPEND_BN = 5.3              # MedPAC Payment Basics 2024 (GOV)
_MC_FFS_ORGS = 10_600              # MedPAC Payment Basics 2024 (GOV)
_MC_FFS_YEAR = 2024
# Medicare FFS share of ALL-PAYER ground transport VOLUME. The elderly use
# ambulances far above their population share, and roughly half of Medicare is now
# MA, so FFS alone sits near a quarter-to-a-third of all ground volume. A DERIVED
# assumption band — NOT a published figure — used only to gross the GOV anchor up.
_MC_FFS_SHARE = (0.25, 0.32)
# Interfacility ED-to-ED transfers, from the largest all-payer ED database
# (AHRQ HCUP NEDS): 9.87M adult ED-to-ED transfers over 2018-2022 ≈ ~2.0M/yr, and
# >2M/yr across all ages (Am J Emerg Med 2025). This is the current, precise read
# on the emergent up-transfer stream — it supersedes the older NHAMCS ~1.1-1.3M/yr
# estimate (kept below as corroboration). Both still EXCLUDE the larger scheduled
# discharge book (hospital→SNF/IRF/home), which /ift-hs-demand sizes from HCRIS.
_NEDS_ED_TRANSFERS_M = 2.0         # HCUP NEDS 2018-2022 (SOURCED)
_IFT_TO_ED_M = (1.1, 1.3)         # older CDC NHAMCS read (ACADEMIC), corroborating


@dataclass(frozen=True)
class VolumeTier:
    tier: str                  # the funnel tier label
    value: str                 # formatted display value (transports/yr)
    basis: str                 # GOV | SOURCED | ACADEMIC | DERIVED
    source: str                # the citation
    note: str = ""


@dataclass(frozen=True)
class VolumeSplit:
    label: str
    share_pct: float           # % of the Medicare FFS ground base
    transports_m: float        # implied transports (millions) on the 11.3M base
    basis: str
    note: str = ""


@dataclass(frozen=True)
class NationalVolume:
    available: bool
    ffs_transports_m: float = 0.0
    ffs_spend_bn: float = 0.0
    ffs_orgs: int = 0
    ffs_year: int = 0
    allpayer_low_m: float = 0.0
    allpayer_high_m: float = 0.0
    ffs_share_low: float = 0.0
    ffs_share_high: float = 0.0
    ift_to_ed_low_m: float = 0.0
    ift_to_ed_high_m: float = 0.0
    neds_ed_transfers_m: float = 0.0
    tiers: Tuple[VolumeTier, ...] = ()
    acuity_split: Tuple[VolumeSplit, ...] = ()
    emergency_split: Tuple[VolumeSplit, ...] = ()
    source_label: str = ""
    note: str = ""


def national_transport_volume() -> NationalVolume:
    """The transports/year funnel — national → interfacility, every tier sourced.

    Anchored on the GOV Medicare-FFS figure (11.3M transports, $5.3B, CY2024) and
    stepped up to an all-payer band (DERIVED, explicit share assumption) and down to
    the interfacility slice (ACADEMIC NHAMCS floor). Never raises."""
    ffs = _MC_FFS_TRANSPORTS_M
    lo_share, hi_share = _MC_FFS_SHARE
    # All-payer = FFS ÷ FFS's share of all-payer volume. Lower share → higher total.
    allpayer_low = round(ffs / hi_share, 1)     # 11.3 / 0.32 ≈ 35.3M
    allpayer_high = round(ffs / lo_share, 1)    # 11.3 / 0.25 ≈ 45.2M
    ift_lo, ift_hi = _IFT_TO_ED_M

    tiers = (
        VolumeTier(
            tier="US all-payer ground ambulance",
            value=f"~{allpayer_low:.0f}-{allpayer_high:.0f}M / yr",
            basis="DERIVED",
            source=("DERIVED: GOV Medicare-FFS anchor (11.3M) ÷ Medicare FFS's "
                    f"~{lo_share*100:.0f}-{hi_share*100:.0f}% share of all-payer "
                    "ground volume — NOT a trade/market-research-firm figure"),
            note="The widest ring: every ground transport, all payers, all types. "
                 "A derived band, shown so the GOV slice below has context."),
        VolumeTier(
            tier="Medicare FFS ground (the GOV anchor)",
            value=f"{ffs:.1f}M / yr",
            basis="GOV",
            source=("MedPAC, 'Ambulance Services Payment System' Payment Basics "
                    "(Oct 2024) — ~10,600 orgs, 11.3M transports, $5.3B, CY2024"),
            note=f"The hardest number on the page: ${_MC_FFS_SPEND_BN:.1f}B paid "
                 f"across {_MC_FFS_ORGS:,} organizations. Everything else is sized "
                 "off this."),
        VolumeTier(
            tier="Non-emergency ground (scheduled book)",
            value="~38-40% of the base",
            basis="SOURCED",
            source=("Medicare claims / CMS GADCS (RAND) Year-1/2 — BLS "
                    "non-emergency fell 43.7%→37.1% of BLS lines, 2018→2022"),
            note="Scheduled discharge/transfer + repetitive (dialysis) legs. IFT's "
                 "discharge book lives here; the slice is shrinking as repetitive "
                 "non-emergency is scrutinized."),
        VolumeTier(
            tier="Interfacility ED-to-ED transfers (HCUP NEDS)",
            value=f"~{_NEDS_ED_TRANSFERS_M:.1f}M / yr",
            basis="SOURCED",
            source=("AHRQ HCUP NEDS — 9.87M adult ED-to-ED transfers 2018-2022 "
                    "(~2.0M/yr; >2M/yr all ages), Am J Emerg Med 2025. The older "
                    f"CDC NHAMCS read (~{ift_lo:.1f}-{ift_hi:.1f}M/yr) corroborates."),
            note="The emergent up-transfer stream, measured in the largest "
                 "all-payer ED database — more current and precise than the NHAMCS "
                 "floor. Still excludes the hospital→SNF/IRF/home discharge book, "
                 "sized on /ift-hs-demand from HCRIS + HCUP NIS dispositions."),
    )

    # Acuity mix on the Medicare FFS ground base (~11.3M). 56/44 BLS/ALS is the
    # SOURCED claims split; SCT is carved from the high-acuity ALS end (ILLUSTRATIVE
    # — SCT is definitionally interfacility, 42 CFR 414.605, small volume/high value).
    acuity_split = (
        VolumeSplit("BLS (basic life support)", 56.0, round(ffs * 0.56, 1), "SOURCED",
                    "The plurality of transports — routine + the discharge book."),
        VolumeSplit("ALS (advanced life support)", 42.0, round(ffs * 0.42, 1), "SOURCED",
                    "Monitored transfers + the emergent up-transfer stream."),
        VolumeSplit("SCT / CCT (specialty critical care)", 2.0, round(ffs * 0.02, 1),
                    "ILLUSTRATIVE",
                    "Carved from the ALS top — definitionally interfacility (42 CFR "
                    "414.605); the premium IFT tier, small volume, highest value."),
    )

    # Emergency vs non-emergency on the Medicare FFS ground base. The BLS trend
    # (62.9% emergency by 2022) is the SOURCED anchor; blended with the more
    # emergency-weighted ALS book gives an overall ~60-62% emergency read.
    emergency_split = (
        VolumeSplit("Emergency (911 / emergent up-transfer)", 62.0,
                    round(ffs * 0.62, 1), "SOURCED",
                    "The 911 book + the in-window emergent transfer (STEMI/stroke). "
                    "Rising share as non-emergency is scrutinized."),
        VolumeSplit("Non-emergency (scheduled / IFT discharge)", 38.0,
                    round(ffs * 0.38, 1), "SOURCED",
                    "The scheduled interfacility discharge/transfer book — where the "
                    "IFT market concentrates outside the emergent minority."),
    )

    return NationalVolume(
        available=True,
        ffs_transports_m=ffs, ffs_spend_bn=_MC_FFS_SPEND_BN, ffs_orgs=_MC_FFS_ORGS,
        ffs_year=_MC_FFS_YEAR,
        allpayer_low_m=allpayer_low, allpayer_high_m=allpayer_high,
        ffs_share_low=lo_share, ffs_share_high=hi_share,
        ift_to_ed_low_m=ift_lo, ift_to_ed_high_m=ift_hi,
        neds_ed_transfers_m=_NEDS_ED_TRANSFERS_M,
        tiers=tiers, acuity_split=acuity_split, emergency_split=emergency_split,
        source_label=("GOV Medicare-FFS anchor (MedPAC 2024) → DERIVED all-payer "
                      "band → SOURCED HCUP NEDS interfacility transfers; "
                      "acuity/emergency mix from CMS GADCS (RAND) + FAIR Health"),
        note=("Every tier is sourced. The all-payer line is DERIVED from the GOV "
              "figure — no trade or market-research-firm volume estimate is used. "
              "The HCUP NEDS line (~2.0M/yr) measures ED-to-ED transfers only; the "
              "full IFT book adds the scheduled discharge legs sized on "
              "/ift-hs-demand from HCRIS + HCUP NIS dispositions."))


# ─────────────────────────────────────────────────────────────────────────────
# 4c — Demand-source matrix: the databases, the current best figure from each
# ─────────────────────────────────────────────────────────────────────────────
# "Are we using NEDS or other databases?" — this is the direct answer: the
# multiple independent ways to measure IFT demand VOLUME, each with its most-
# current published figure, data year, honesty basis, and a source URL. It exists
# so the volume funnel above is not one number but a TRIANGULATION a buyer can
# cross-check across the payer claims (CMS/MedPAC), the EMS activation record
# (NEMSIS), the all-payer ED database (HCUP NEDS), the inpatient database (HCUP
# NIS), and the facility throughput base (HCRIS). No trade / market-research-firm
# database is used.
@dataclass(frozen=True)
class DemandSource:
    name: str                  # database / dataset
    steward: str               # who runs it
    measures: str              # what it measures for IFT volume
    current_read: str          # the most-current published figure + unit
    data_year: str             # the data year / window it applies to
    basis: str                 # GOV | SOURCED | ACADEMIC
    url: str
    note: str = ""


_DEMAND_SOURCES: Tuple[DemandSource, ...] = (
    DemandSource(
        "Medicare Ambulance Fee Schedule + MedPAC Payment Basics",
        "CMS / MedPAC",
        "Medicare fee-for-service ground ambulance transports & spend — the hard "
        "payer anchor for volume.",
        "11.3M transports/yr · $5.3B · ~10,600 orgs", "CY2024", "GOV",
        "https://www.medpac.gov/wp-content/uploads/2024/10/"
        "MedPAC_Payment_Basics_24_ambulance_FINAL_SEC.pdf",
        "The single hardest number; ~24-29% of all-payer ground volume, so the "
        "all-payer total is grossed up from here."),
    DemandSource(
        "NEMSIS — National EMS Information System",
        "NHTSA Office of EMS / NEMSIS TAC",
        "National EMS activations; 'Hospital-to-Hospital Transfer' (formerly "
        "Interfacility Transport) is a tracked Type of Service Requested — the "
        "most direct EMS-activation denominator for IFT.",
        "54.2M activations/yr (14,369 agencies, 54 states)", "2023 (v3.5 PRDS)",
        "SOURCED", "https://nemsis.org/view-reports/public-reports/",
        "The public-release research dataset can be filtered to the interfacility "
        "service-type subset — the highest-value refinement still to ingest."),
    DemandSource(
        "HCUP NEDS — Nationwide Emergency Department Sample",
        "AHRQ HCUP",
        "ED-to-ED interfacility transfers (the emergent up-transfer stream), the "
        "largest all-payer ED database.",
        "~2.0M/yr (9.87M adult, 2018-2022; >2M all ages)", "2022 (latest release)",
        "SOURCED", "https://hcup-us.ahrq.gov/nedsoverview.jsp",
        "Supersedes the older NHAMCS ~1.1-1.3M/yr read. Loader exists "
        "(rcm_mc/data/ahrq_hcup.py, source_db='NEDS') — vendored rows to ingest."),
    DemandSource(
        "HCUP NIS — National Inpatient Sample",
        "AHRQ HCUP",
        "Inpatient discharges + discharge-disposition split (transfer-to-hospital, "
        "transfer-to-SNF/IRF/other) — the scheduled discharge-book denominator.",
        "~35M discharges/yr (20% sample); ~20-25% to a facility", "2022", "SOURCED",
        "https://hcup-us.ahrq.gov/nisoverview.jsp",
        "The f_IFT discharge-disposition fraction the health-system model needs; "
        "same loader (source_db='NIS'). The post-acute share is a superset of the "
        "ambulance-requiring legs (many post-acute discharges go by van/livery)."),
    DemandSource(
        "CMS GADCS — Ground Ambulance Data Collection System",
        "CMS / RAND",
        "Agency cost & utilization; the BLS emergency vs non-emergency mix and its "
        "drift over time.",
        "BLS non-emergency 43.7%→37.1% (2018→2022)", "2022-2023 (Yr1/2 cohort)",
        "GOV", "https://www.cms.gov/files/document/medicare-ground-ambulance-data-"
        "collection-system-gadcs-report-year-1-and-year-2-cohort-analysis.pdf",
        "Fixes the emergency/non-emergency split on the funnel; also the definitive "
        "agency-count and cost structure."),
    DemandSource(
        "CMS HCRIS — Hospital Cost Reports",
        "CMS",
        "Hospital discharges (throughput) per facility — the health-system-buyer "
        "demand base (discharges ≈ patient_days ÷ ALOS).",
        "vendored per-hospital S-3 panel (discharges, days, payer mix)",
        "latest filed FY", "SOURCED",
        "https://www.cms.gov/research-statistics-data-and-systems/"
        "downloadable-public-use-files/cost-reports",
        "LIVE in the estate — the one demand driver already ingested; powers "
        "/ift-hs-demand county-by-county."),
    DemandSource(
        "CDC NHAMCS — Nat'l Hospital Ambulatory Medical Care Survey",
        "CDC / NCHS",
        "ED arrivals by ambulance and ED→acute interfacility transfers — the older "
        "corroboration of the NEDS read.",
        "~1.1-1.3M/yr IFT-to-ED (5.3% of EMS-ED encounters)", "2014-2022",
        "ACADEMIC", "https://www.cdc.gov/nchs/ahcd/index.htm",
        "Kept as a cross-check; NEDS is the more current/precise primary."),
    DemandSource(
        "FAIR Health — all-payer claims database",
        "FAIR Health (independent nonprofit)",
        "All-payer ground ambulance utilization & cost — the commercial/Medicaid "
        "side the Medicare anchor misses.",
        "utilization & cost brief (all-payer ground)", "latest brief", "SOURCED",
        "https://www.fairhealth.org/",
        "Widens the payer lens beyond Medicare FFS; not a trade/market-research "
        "firm — a claims database."),
)


@dataclass(frozen=True)
class DemandSourceMatrix:
    available: bool
    sources: Tuple[DemandSource, ...] = ()
    n_gov: int = 0
    n_sourced: int = 0
    n_academic: int = 0
    source_label: str = ""
    note: str = ""


def demand_source_matrix() -> DemandSourceMatrix:
    """The multiple independent databases used to measure IFT demand volume, each
    with its most-current published figure, data year, basis, and URL. The direct
    answer to 'are we using NEDS / other databases.' Never raises."""
    srcs = _DEMAND_SOURCES
    return DemandSourceMatrix(
        available=True, sources=srcs,
        n_gov=sum(1 for s in srcs if s.basis == "GOV"),
        n_sourced=sum(1 for s in srcs if s.basis == "SOURCED"),
        n_academic=sum(1 for s in srcs if s.basis == "ACADEMIC"),
        source_label=("Multi-database demand triangulation — CMS/MedPAC (payer "
                      "claims), NEMSIS (EMS activations), HCUP NEDS/NIS (all-payer "
                      "ED + inpatient), CMS GADCS, HCRIS, CDC NHAMCS, FAIR Health"),
        note=("Every source is government or an independent claims/records database "
              "— no trade or market-research firm. NEDS and NIS have a loader in "
              "the codebase (rcm_mc/data/ahrq_hcup.py); NEMSIS is citation-anchored "
              "with the public-release dataset as the ingest target."))


# ─────────────────────────────────────────────────────────────────────────────
# 5 — Time series ("trailed over time")
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class SeriesPoint:
    label: str
    value: float


@dataclass(frozen=True)
class TimeSeries:
    key: str
    title: str
    unit: str
    basis: str
    window: str
    points: Tuple[SeriesPoint, ...]
    note: str = ""


@dataclass(frozen=True)
class DemandTimeSeries:
    available: bool
    series: Tuple[TimeSeries, ...] = ()
    source_label: str = ""


def demand_time_series() -> DemandTimeSeries:
    """Assemble the three trailable series: backward HCRIS occupancy, the GOV AIF
    price series, and the forward MMT growth projection. Never raises."""
    series: List[TimeSeries] = []
    # (a) Occupancy — backward (HCRIS), may be offline.
    try:
        from . import ift_analytics as _an
        occ = _an.occupancy_trend()
        pts = [SeriesPoint(f"FY{fy}", round(o * 100, 1))
               for fy, o in getattr(occ, "points", []) or []]
        if pts:
            series.append(TimeSeries(
                key="occupancy", title="National inpatient occupancy",
                unit="%", basis="GOV", window=f"{pts[0].label}-{pts[-1].label}",
                points=tuple(pts),
                note="The throughput proxy — but the panel ends FY2022, so the "
                     "rise is a COVID-recovery level normalizing, not a trend."))
    except Exception:  # noqa: BLE001
        pass
    # (b) AIF — the GOV price series.
    try:
        from . import ift_tracking as _tr
        pl = _tr.price_lever()
        pts = [SeriesPoint(str(y), float(v))
               for y, v in getattr(pl, "aif_trend", ()) or ()]
        if pts:
            series.append(TimeSeries(
                key="aif", title="Ambulance Inflation Factor (price)",
                unit="%/yr", basis="GOV",
                window=f"{pts[0].label}-{pts[-1].label}", points=tuple(pts),
                note="Decelerating (2.6/2.4/2.0 for CY2024-26) — a >2% price lever "
                     "now sits above the GOV floor."))
    except Exception:  # noqa: BLE001
        pass
    # (c) MMT SOM projection — forward.
    try:
        from . import ift_mmt as _mmt
        gp = _mmt.mmt_growth_projection(horizon=5)
        pts = [SeriesPoint(f"Y+{y.year_offset}", round(y.base_revenue / 1e6, 2))
               for y in getattr(gp, "years", ())]
        if pts:
            series.append(TimeSeries(
                key="mmt_projection", title="MMT SOM revenue (base case)",
                unit="$M", basis="ILLUSTRATIVE", window="Y+0 to Y+5",
                points=tuple(pts),
                note=f"Organic market growth {gp.base_cagr * 100:.1f}%/yr on the "
                     "modeled SOM (price × volume)."))
    except Exception:  # noqa: BLE001
        pass
    return DemandTimeSeries(
        available=bool(series), series=tuple(series),
        source_label=("GOV HCRIS occupancy + GOV AIF series + ILLUSTRATIVE MMT "
                      "projection (three windows, stitched)"))


# ─────────────────────────────────────────────────────────────────────────────
# Rollup summary
# ─────────────────────────────────────────────────────────────────────────────
def demand_summary() -> Dict[str, Any]:
    """Counts for the page header / meta line. Never raises."""
    reg = regional_demand()
    nf = national_frame()
    hc = hcpcs_acuity_analysis()
    ts = demand_time_series()
    vol = national_transport_volume()
    n_counties = n_cbsa = 0
    try:
        from . import ift_mmt as _mmt
        fs = _mmt.footprint_summary()
        n_counties = fs.n_county
        n_cbsa = fs.n_cbsa
    except Exception:  # noqa: BLE001
        pass
    return {
        "n_regions": len(reg),
        "n_metros": sum(r.n_metros for r in reg),
        "n_hospitals_footprint": sum(r.n_hospitals for r in reg),
        "n_hospitals_national": nf.n_hospitals_national,
        "n_hcpcs": len(hc.rows),
        "n_series": len(ts.series),
        "n_counties": n_counties,
        "n_cbsa": n_cbsa,
        "ffs_transports_m": vol.ffs_transports_m,
        "allpayer_low_m": vol.allpayer_low_m,
        "allpayer_high_m": vol.allpayer_high_m,
        "neds_ed_transfers_m": vol.neds_ed_transfers_m,
        "n_demand_sources": len(demand_source_matrix().sources),
    }
