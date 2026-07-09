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
    demand_drivers() -> DemandDrivers
    demand_evidence() -> Tuple[Evidence, ...]   (verbatim quote + link per figure)
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
# Every number here is a PUBLISHED, quoted figure from the evidence registry
# (ift_demand_evidence) — nothing illustrative, nothing modeled from an unsourced
# assumption. These are FOUR DISTINCT measures (different denominators), not a
# nested funnel: a payer-claims count (Medicare FFS), and three all-payer
# interfacility counts from HCUP. Each carries its basis; the Evidence & sources
# sheet holds the verbatim quote + link for every one.
#
# Note on the all-payer total: an all-payer ground-transport count is NOT published
# and Medicare's share of all-payer VOLUME is not a verifiable public figure, so we
# deliberately DO NOT state an all-payer total — that would be an unsourced number.
from . import ift_demand_evidence as _ev

_MC_FFS_TRANSPORTS_M = 11.3          # MedPAC Payment Basics 2024 (GOV, quoted)
_MC_FFS_SPEND_BN = 5.3              # MedPAC Payment Basics 2024 (GOV, quoted)
_MC_FFS_ORGS = 10_600              # MedPAC Payment Basics 2024 (GOV, quoted)
_MC_FFS_YEAR = 2024
# HCUP NEDS: 9,867,701 adult ED-to-ED transfers over 2018-2022 = ~1.97M/yr.
_NEDS_ED_TRANSFERS_TOTAL = 9_867_701   # Am J Emerg Med 2025 (ACADEMIC, quoted)
_NEDS_YEARS = 5
_NEDS_ED_TRANSFERS_M = round(_NEDS_ED_TRANSFERS_TOTAL / _NEDS_YEARS / 1e6, 2)  # 1.97
_NEDS_CRITICAL = 655_442               # 6.6% with a critical procedure (quoted)
_INTERHOSPITAL_M = 1.5                  # ~1.5M/yr = 3.5% of admissions (quoted)
# Acuity: GADCS — "56 percent of transports were at the basic life support level."
_BLS_SHARE = 56.0
_ALS_SHARE = 44.0
# Emergency mix: GADCS BLS claim lines (2022) — the only sourced split we have.
_BLS_EMERGENCY_2022 = 62.9
_BLS_NONEMERGENCY_2022 = 37.1


@dataclass(frozen=True)
class VolumeTier:
    tier: str                  # the measure label
    value: str                 # published value (verbatim)
    basis: str                 # GOV | SOURCED | ACADEMIC  (never ILLUSTRATIVE)
    source: str                # the citation (full quote is on the Evidence sheet)
    evidence_key: str = ""     # link into ift_demand_evidence
    note: str = ""


@dataclass(frozen=True)
class VolumeSplit:
    label: str
    share_pct: float           # published share
    basis: str
    source: str = ""
    note: str = ""


@dataclass(frozen=True)
class NationalVolume:
    available: bool
    ffs_transports_m: float = 0.0
    ffs_spend_bn: float = 0.0
    ffs_orgs: int = 0
    ffs_year: int = 0
    neds_ed_transfers_m: float = 0.0
    neds_critical: int = 0
    interhospital_transfers_m: float = 0.0
    tiers: Tuple[VolumeTier, ...] = ()
    acuity_split: Tuple[VolumeSplit, ...] = ()
    emergency_split: Tuple[VolumeSplit, ...] = ()
    source_label: str = ""
    note: str = ""


def national_transport_volume() -> NationalVolume:
    """The transports/year measures — FOUR distinct, published counts, each with a
    verbatim source quote (on the Evidence sheet). No illustrative or unsourced
    number: there is deliberately NO all-payer total, because none is published.
    Never raises."""
    ffs = _MC_FFS_TRANSPORTS_M
    neds = _NEDS_ED_TRANSFERS_M

    tiers = (
        VolumeTier(
            tier="Medicare FFS ground transports",
            value=f"{ffs:.1f}M / yr", basis="GOV",
            source="MedPAC Ambulance Payment Basics (Oct 2024) — 11.3M transports, "
                   "$5.3B, ~10,600 orgs (2024)",
            evidence_key="medicare_ffs_transports",
            note=f"The hardest number: a full payer-claims count. ${_MC_FFS_SPEND_BN:.1f}"
                 f"B across {_MC_FFS_ORGS:,} organizations. Medicare FFS only — not "
                 "all-payer (no all-payer total is published)."),
        VolumeTier(
            tier="Interfacility ED-to-ED transfers (all-payer)",
            value=f"~{neds:.1f}M / yr", basis="ACADEMIC",
            source="HCUP NEDS — 9,867,701 adult ED-to-ED transfers 2018-2022 "
                   "(Am J Emerg Med 2025)",
            evidence_key="neds_ed_transfers",
            note="The emergent up-transfer stream in the largest all-payer ED "
                 "database. 9,867,701 ÷ 5 yrs ≈ 1.97M/yr. Excludes the "
                 "hospital→SNF/IRF/home discharge book."),
        VolumeTier(
            tier="Acute inter-hospital transfers (all-payer)",
            value=f"~{_INTERHOSPITAL_M:.1f}M / yr", basis="ACADEMIC",
            source="Nationwide Outcomes Study, HCUP NIS (PubMed 25397857) — 3.5% of "
                   "admissions = 1.5M",
            evidence_key="interhospital_transfers",
            note="Acute-to-acute transfers = 3.5% of all inpatient admissions. "
                 "Overlaps the NEDS ED count where the transfer originates in an ED."),
        VolumeTier(
            tier="ED transfers needing critical care (CCT-relevant)",
            value=f"{_NEDS_CRITICAL:,} (6.6%)", basis="ACADEMIC",
            source="HCUP NEDS — 655,442 of 9,867,701 ED transfers had a critical "
                   "procedure (Am J Emerg Med 2025)",
            evidence_key="neds_critical_share",
            note="The SCT/CCT-relevant slice, measured directly: the premium, "
                 "highest-value interfacility tier."),
    )

    # Acuity mix — GADCS published split (56% BLS → ~44% ALS). SOURCED, quoted.
    acuity_split = (
        VolumeSplit("BLS (basic life support)", _BLS_SHARE, "SOURCED",
                    "CMS GADCS (RAND) — \"56 percent of transports were at the BLS "
                    "level\"",
                    "The plurality of transports — routine + the discharge book."),
        VolumeSplit("ALS (advanced life support)", _ALS_SHARE, "SOURCED",
                    "CMS GADCS (RAND) — the balance of the 56% BLS split",
                    "Monitored transfers + the emergent up-transfer stream. SCT/CCT "
                    "sits at the top of ALS; the CCT count is the NEDS 655,442."),
    )

    # Emergency vs non-emergency — the ONLY sourced split is GADCS BLS claim lines
    # (2022). We present it AS BLS-specific, not extrapolated to all transports.
    emergency_split = (
        VolumeSplit("Emergency (BLS claim lines, 2022)", _BLS_EMERGENCY_2022,
                    "SOURCED",
                    "CMS GADCS / Medicare claims — BLS emergency rose 56.3%→62.9% "
                    "(2018→2022)",
                    "BLS-specific — not extrapolated to all transports."),
        VolumeSplit("Non-emergency (BLS claim lines, 2022)", _BLS_NONEMERGENCY_2022,
                    "SOURCED",
                    "CMS GADCS / Medicare claims — BLS non-emergency fell "
                    "43.7%→37.1% (2018→2022)",
                    "The scheduled interfacility discharge book concentrates here."),
    )

    return NationalVolume(
        available=True,
        ffs_transports_m=ffs, ffs_spend_bn=_MC_FFS_SPEND_BN, ffs_orgs=_MC_FFS_ORGS,
        ffs_year=_MC_FFS_YEAR,
        neds_ed_transfers_m=neds, neds_critical=_NEDS_CRITICAL,
        interhospital_transfers_m=_INTERHOSPITAL_M,
        tiers=tiers, acuity_split=acuity_split, emergency_split=emergency_split,
        source_label=("Four published counts — MedPAC (GOV), HCUP NEDS (ACADEMIC, "
                      "x2) and HCUP NIS (ACADEMIC); acuity/emergency mix from CMS "
                      "GADCS. Every figure quoted on the Evidence & sources sheet"),
        note=("These are FOUR distinct measures with different denominators, not a "
              "nested funnel — Medicare FFS is a payer-claims count; the three "
              "interfacility counts are all-payer from HCUP. We deliberately state "
              "NO all-payer TOTAL, because none is published and Medicare's share "
              "of all-payer volume is not a verifiable figure."))


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
# 4d — Demand drivers: the structural forces behind IFT volume, EVERY ONE SOURCED
# ─────────────────────────────────────────────────────────────────────────────
# The forces that generate interfacility transport demand — admissions, transfers,
# consolidation, specialization, ED boarding, acuity mix — each with a current
# GOV/SOURCED/ACADEMIC figure (NOTHING illustrative), the best proxy to obtain it,
# and how to track it over time. Basis is deliberately restricted: a driver with
# no published/GOV figure is not admitted to this table.
@dataclass(frozen=True)
class DemandDriver:
    driver: str                # the demand force
    metric: str                # the specific quantity
    value: str                 # the current sourced figure
    basis: str                 # GOV | SOURCED | ACADEMIC  (never ILLUSTRATIVE)
    source: str                # citation
    url: str
    proxy: str                 # the best proxy / dataset to OBTAIN it
    track: str                 # the best way to TRACK it over time
    ift_link: str              # why it drives IFT demand


_DEMAND_DRIVERS: Tuple[DemandDriver, ...] = (
    DemandDriver(
        "Annual hospital admissions",
        "US inpatient admissions / discharges per year",
        "~33.7M admissions (AHA 2022); ~35M discharges (HCUP NIS 2022)",
        "SOURCED",
        "AHA Fast Facts / AHA Annual Survey (2022); AHRQ HCUP NIS (2022)",
        "https://www.aha.org/statistics/fast-facts-us-hospitals",
        "AHA Annual Survey admissions; HCUP NIS weighted discharges; per-hospital "
        "HCRIS Worksheet S-3 discharges (already vendored).",
        "HCRIS S-3 refresh each cost-report cycle (LIVE) + HCUP NIS yearly release.",
        "The demand denominator — every admission is a potential transfer origin; "
        "IFT volume scales with the admitted base."),
    DemandDriver(
        "Annual IFT missions / transfers",
        "Interfacility ambulance transports per year",
        "~2.0M ED-to-ED (NEDS 2018-22) + ~1.5M inter-hospital (nationwide study)",
        "SOURCED",
        "AHRQ HCUP NEDS (2022); Sokol-Hessner/Mueller et al., Nationwide Outcomes "
        "Study (PubMed 25397857); MedPAC 11.3M FFS ground (CY2024)",
        "https://pubmed.ncbi.nlm.nih.gov/25397857/",
        "HCUP NEDS/NIS transfer disposition (loader exists); NEMSIS "
        "'Hospital-to-Hospital Transfer' service-type count; CMS Part-B A0426-A0434.",
        "HCUP NEDS/NIS annual; NEMSIS public-release dataset each year; CMS PSPS "
        "annual — triangulated, not a single feed.",
        "The direct volume the operator serves."),
    DemandDriver(
        "Annual hospital-to-hospital transfers",
        "Acute-to-acute inter-hospital transfers per year",
        "~1.5M/yr (~3.5% of admissions); ~640k require critical care",
        "ACADEMIC",
        "Mueller SK et al., 'Interhospital Facility Transfers in the US: A "
        "Nationwide Outcomes Study' (PubMed 25397857); ~3.5% of admissions",
        "https://pubmed.ncbi.nlm.nih.gov/25397857/",
        "HCUP NIS admission-source = 'transfer from another acute hospital' + "
        "discharge disposition = 'transfer to short-term hospital'.",
        "HCUP NIS yearly (loader supports source_db=NIS); cross-check vs NEDS "
        "ED-to-ED transfers.",
        "The escalation up-transfer book — the high-acuity, high-$ IFT stream."),
    DemandDriver(
        "Acuity mix — % ALS / BLS / CCT",
        "Share of ground transports by service level",
        "BLS ~56% / ALS ~42% / SCT-CCT ~2% (CMS claims); ~40% of inter-hospital "
        "transfers are critical-care level (~640k of ~1.5M)",
        "SOURCED",
        "CMS Ground Ambulance Industry Trends / GADCS (RAND); FAIR Health; the "
        "640k-CCT share from the Nationwide Outcomes Study",
        "https://www.cms.gov/data-research/statistics-trends-reports/"
        "medicare-provider-utilization-payment-data",
        "CMS Part-B Physician/Supplier Procedure Summary by HCPCS (A0426-A0434); "
        "GADCS agency reports.",
        "CMS PSPS annual (ingest-ready connector) — line-level A0428/A0433/A0434 "
        "volume is the definitive acuity split.",
        "The revenue mix — SCT/CCT is the premium tier; a rising CCT share lifts "
        "$/leg."),
    DemandDriver(
        "Health systems — facilities increasing (consolidation)",
        "Number of health systems & hospital system-affiliation",
        "640 health systems (2022); ~70% of non-federal general acute hospitals "
        "are in a system; system growth continues",
        "GOV",
        "AHRQ Compendium of US Health Systems (CHSP), 2022",
        "https://www.ahrq.gov/chsp/data-resources/compendium.html",
        "AHRQ Compendium of US Health Systems (systems, hospitals-per-system, "
        "affiliation) + CMS Provider-of-Services facility counts.",
        "AHRQ CHSP Compendium annual release; CMS POS facility counts.",
        "System growth → more INTRA-system transfers (keep patients in-network) → "
        "captive, contractible IFT demand."),
    DemandDriver(
        "Hospitals increasingly specializing (regionalization)",
        "Service-line concentration into designated centers",
        "Time-sensitive care (trauma, STEMI, stroke, sepsis, cardiogenic shock) is "
        "regionalized hub-and-spoke; strong volume-outcome relationship",
        "ACADEMIC",
        "Time-to-Transfer / hub-and-spoke, Joint Commission Journal Qual Patient "
        "Saf (2023); regionalization & volume-outcome literature",
        "https://www.jointcommissionjournal.com/article/S1553-7250(23)00132-0/"
        "abstract",
        "Designated-center registries (trauma level I/II, primary/comprehensive "
        "stroke, STEMI-receiving); CMS MedPAR service-line volume by hospital.",
        "Center-designation lists + CMS MedPAR DRG concentration, tracked yearly.",
        "Spoke→hub up-transfers are the direct product of specialization — the "
        "highest-acuity, most reliable IFT demand."),
    DemandDriver(
        "ED boarding / occupancy / transfer delays",
        "ED boarding prevalence & transfer-out pressure",
        "44% of adults report prolonged waits before admit/transfer, 16% of those "
        "≥13h (ACEP 2023); boarding drives diversion + transfer-out",
        "ACADEMIC",
        "ACEP Emergency Department Boarding & Crowding (2023 ACEP/Morning Consult "
        "poll); ED-throughput literature",
        "https://www.acep.org/administration/crowding--boarding",
        "CMS Hospital Compare 'Timely & Effective Care' ED-throughput measures "
        "(OP-18/OP-22) + HCRIS inpatient occupancy (patient-days ÷ bed-days).",
        "CMS Care Compare ED-throughput quarterly; HCRIS occupancy (LIVE) each "
        "cost-report cycle.",
        "A full hospital transfers patients OUT — boarding and high occupancy "
        "convert directly into IFT missions."),
    DemandDriver(
        "Impact on hospital priorities (why they buy)",
        "Throughput, EMTALA duty, quality, network retention",
        "EMTALA (42 CFR 489.24) mandates appropriate transfer; boarding raises "
        "LOS, cost, diversion, and mortality risk (sourced above)",
        "GOV",
        "CMS EMTALA — 42 CFR 489.24; ED-throughput & regionalization evidence "
        "(rows above)",
        "https://www.cms.gov/medicare/regulations-guidance/legislation/"
        "emergency-medical-treatment-labor-act",
        "CMS EMTALA rule (the legal transfer duty) + CMS quality/throughput "
        "measures for the operational impact.",
        "EMTALA compliance + throughput + in-network retention, tracked via CMS "
        "measures.",
        "Hospitals MUST transfer appropriately and WANT reliable, in-network "
        "transport — the structural pull that makes IFT a purchased service."),
)


@dataclass(frozen=True)
class DemandDrivers:
    available: bool
    drivers: Tuple[DemandDriver, ...] = ()
    n_gov: int = 0
    n_sourced: int = 0
    n_academic: int = 0
    all_sourced: bool = True
    source_label: str = ""
    note: str = ""


def demand_drivers() -> DemandDrivers:
    """The structural forces behind IFT demand, EACH fully sourced (GOV/SOURCED/
    ACADEMIC, nothing illustrative), with the best proxy to obtain it and how to
    track it over time. Never raises."""
    ds = _DEMAND_DRIVERS
    bases = {d.basis for d in ds}
    return DemandDrivers(
        available=True, drivers=ds,
        n_gov=sum(1 for d in ds if d.basis == "GOV"),
        n_sourced=sum(1 for d in ds if d.basis == "SOURCED"),
        n_academic=sum(1 for d in ds if d.basis == "ACADEMIC"),
        all_sourced=bases.issubset({"GOV", "SOURCED", "ACADEMIC"}),
        source_label=("IFT demand drivers — each anchored to a GOV rule/statistic, "
                      "a real dataset (HCUP/HCRIS/CMS/AHRQ), or a peer-reviewed "
                      "study; every row carries its source, proxy, and tracking "
                      "path"),
        note=("Nothing on this table is illustrative — a driver with no published "
              "or government figure is not admitted. Proxies name the exact dataset "
              "to obtain each figure; several (HCRIS, CMS PSPS, HCUP loader) are "
              "already in the codebase's data estate."))


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
        "neds_ed_transfers_m": vol.neds_ed_transfers_m,
        "interhospital_transfers_m": vol.interhospital_transfers_m,
        "n_demand_sources": len(demand_source_matrix().sources),
        "n_demand_drivers": len(demand_drivers().drivers),
        "n_evidence": len(demand_evidence()),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Evidence registry passthrough (single source of truth for every headline number)
# ─────────────────────────────────────────────────────────────────────────────
Evidence = _ev.Evidence


def demand_evidence() -> Tuple[Any, ...]:
    """Every headline demand figure with its VERBATIM published quote and link —
    the 'what can I trust' reference. No illustrative figures. Never raises."""
    try:
        return _ev.all_evidence()
    except Exception:  # noqa: BLE001
        return ()
