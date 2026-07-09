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
    }
