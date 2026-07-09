"""IFT demand — the health-system buyer model (hospital-discharge driven).

The buyer of interfacility transport is the HEALTH SYSTEM, and the demand it
generates is a derived demand off its hospitals' throughput — NOT off the
destination facilities. This module sizes demand the right way:

  * driver = **acute hospital discharges + up-transfers**, from HCRIS (the
    Medicare Hospital Cost Reports) — ``discharges ≈ patient_days ÷ ALOS`` when
    the HCRIS panel is present, else a labelled ``hospital_count × national
    discharges/hospital`` fallback so the build is non-zero in any environment;
  * the **SNF post-acute term is DROPPED** — a SNF is where a leg goes, not who
    orders or pays it, so SNF bed counts are not a demand node here;
  * demand is attributed to the **larger multi-hospital health systems** (the
    real buyers) and broken down **county by county** across the footprint; and
  * a **demand-data inventory** enumerates every driver we can source, its basis,
    and what it yields — because sizing this well is a data problem.

Reuses the sized estate (``ift_geo`` SOURCED facility structure, ``ift_analytics``
levers, ``ift_mmt`` counties + anchor accounts) so nothing drifts. Frozen
dataclasses, pure functions that DEGRADE and never raise, honesty labels on every
figure.

Public API:
    hospital_demand() -> Tuple[MetroHsDemand, ...]
    health_system_rollup() -> Tuple[SystemDemand, ...]
    county_demand() -> Tuple[CountyHsDemand, ...]
    demand_data_inventory() -> DemandInventory
    hs_demand_summary() -> Dict[str, Any]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# National discharge anchor (ILLUSTRATIVE): US short-term acute inpatient
# discharges ~34M / ~4,630 short-term hospitals ≈ ~7,300 discharges/hospital/yr
# (AHRQ HCUP NIS + AHA). Used as the fallback when HCRIS patient-days are absent.
_DISCHARGES_PER_HOSPITAL_YR = 7300.0
_ALOS_DAYS = 4.5                      # ILLUSTRATIVE — mean acute LOS (HCUP)
# Fraction of acute discharges that need a ground IFT leg (stretcher-eligible
# discharge + the up-transfer add). Reused from ift_analytics._F_IFT; the
# up-transfer add is small and folded in via the high end.
_F_IFT = (0.07, 0.10, 0.12)          # (low, central, high) — reused magnitude


def _levers() -> Tuple[Tuple[float, float, float], Tuple[float, float, float],
                       Dict[str, float], float]:
    """(f_IFT, r_IFT, serviceable-share-by-archetype, default-share) from
    ift_analytics so the buyer model shares the corrected levers. Degrades to
    local defaults."""
    f_ift = _F_IFT
    r_ift = (500.0, 600.0, 700.0)
    share: Dict[str, float] = {}
    default = 0.20
    try:
        from . import ift_analytics as _an
        f_ift = getattr(_an, "_F_IFT", f_ift)
        r_ift = getattr(_an, "_R_IFT", r_ift)
        share = dict(getattr(_an, "_SERVICEABLE_SHARE", {}) or {})
        default = float(getattr(_an, "_SERVICEABLE_DEFAULT", default))
    except Exception:  # noqa: BLE001
        pass
    return f_ift, r_ift, share, default


# ─────────────────────────────────────────────────────────────────────────────
# Per-metro hospital-discharge demand (the buyer base)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class MetroHsDemand:
    metro: str
    region_label: str
    rural: bool
    n_hospitals: int
    hcris_beds: float
    discharges: int                  # acute discharges/yr (the driver)
    discharge_basis: str             # SOURCED (HCRIS) | ILLUSTRATIVE (fallback)
    ift_legs: int                    # discharges × f_IFT (central) — SNF dropped
    serviceable_legs: int            # × s(m)
    demand_dollars: float            # serviceable_legs × r_IFT (central)
    anchor_systems: Tuple[str, ...]


def _discharges_for(s) -> Tuple[int, str]:
    """HCRIS-driven discharges (patient_days ÷ ALOS) when the panel is present,
    else the labelled hospital-count fallback. Returns (discharges, basis)."""
    pdays = float(getattr(s, "hcris_patient_days", 0.0) or 0.0)
    if pdays > 0:
        return int(round(pdays / _ALOS_DAYS)), "SOURCED"
    n_h = int(getattr(s, "n_hospitals", 0) or 0)
    return int(round(n_h * _DISCHARGES_PER_HOSPITAL_YR)), "ILLUSTRATIVE"


def hospital_demand() -> Tuple[MetroHsDemand, ...]:
    """Per-metro demand sized off hospital discharges (HCRIS-driven, SNF dropped),
    with the metro's anchor health systems attached. Never raises."""
    try:
        from . import ift_geo as _geo
        metros = _geo.all_metros()
    except Exception:  # noqa: BLE001
        return ()
    f_ift, r_ift, share_map, default_share = _levers()
    out: List[MetroHsDemand] = []
    for s in metros:
        if not getattr(s, "available", True):
            continue
        disch, basis = _discharges_for(s)
        legs = int(round(disch * f_ift[1]))
        s_m = share_map.get(getattr(s, "insource_class", ""), default_share)
        serv = int(round(legs * s_m))
        out.append(MetroHsDemand(
            metro=s.name, region_label=getattr(s, "region_label", ""),
            rural=bool(getattr(s, "rural", False)),
            n_hospitals=int(getattr(s, "n_hospitals", 0) or 0),
            hcris_beds=float(getattr(s, "hcris_beds", 0.0) or 0.0),
            discharges=disch, discharge_basis=basis, ift_legs=legs,
            serviceable_legs=serv, demand_dollars=serv * r_ift[1],
            anchor_systems=tuple(getattr(s, "anchor_systems", []) or [])))
    out.sort(key=lambda m: m.demand_dollars, reverse=True)
    return tuple(out)


# ─────────────────────────────────────────────────────────────────────────────
# Health-system roll-up (the buyer) — reach across the metros a system anchors
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class SystemDemand:
    system: str
    tier: str
    metros: Tuple[str, ...]
    n_metros: int
    ift_legs: int                    # gross IFT legs in the metros it anchors
    serviceable_legs: int
    demand_dollars: float
    strategy: str = ""
    note: str = ""


def health_system_rollup() -> Tuple[SystemDemand, ...]:
    """Attribute demand to the LARGER health systems — each system's reach is the
    demand in the metros it anchors (from the MMT anchor-account registry). Reach
    overlaps where two systems share a metro (contested), so this is system REACH,
    not an exclusive split — labelled as such. Never raises."""
    demand = {m.metro: m for m in hospital_demand()}
    try:
        from . import ift_mmt as _mmt
        accounts = _mmt.mmt_anchor_accounts()
    except Exception:  # noqa: BLE001
        return ()
    out: List[SystemDemand] = []
    for a in accounts:
        metros = tuple(getattr(a, "metros", ()) or ())
        legs = serv = 0
        dollars = 0.0
        hit: List[str] = []
        for mt in metros:
            m = demand.get(mt)
            if m is None:
                continue
            hit.append(mt)
            legs += m.ift_legs
            serv += m.serviceable_legs
            dollars += m.demand_dollars
        out.append(SystemDemand(
            system=getattr(a, "system", ""), tier=getattr(a, "tier", ""),
            metros=tuple(hit), n_metros=len(hit), ift_legs=legs,
            serviceable_legs=serv, demand_dollars=dollars,
            strategy=getattr(a, "mmt_strategy", ""),
            note=getattr(a, "insource_posture", "")))
    out.sort(key=lambda s: s.demand_dollars, reverse=True)
    return tuple(out)


# ─────────────────────────────────────────────────────────────────────────────
# County breakdown — allocate metro demand to the served counties by pop share
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class CountyHsDemand:
    county: str
    state: str
    fips: str
    cbsa_name: str
    metro: str
    role: str
    pop_2020: int
    pop_65_plus: int
    pop_share_of_metro: float        # allocation weight
    ift_legs: int                    # metro legs × pop share (SNF dropped)
    demand_dollars: float
    anchor_systems: Tuple[str, ...]  # the systems serving this county's metro


def county_demand() -> Tuple[CountyHsDemand, ...]:
    """Allocate each metro's hospital-driven demand to its served counties by 2020
    population share, tagging each county with the health systems that serve its
    metro. County population is GOV (2020 Census); the metro→county allocation is
    a labelled ILLUSTRATIVE weight. Never raises."""
    metro_by_name = {m.metro: m for m in hospital_demand()}
    try:
        from . import ift_mmt as _mmt
        counties = _mmt.MMT_COUNTIES
    except Exception:  # noqa: BLE001
        return ()
    # metro → total footprint population (for the allocation denominator)
    metro_pop: Dict[str, int] = {}
    for c in counties:
        metro_pop[c.metro] = metro_pop.get(c.metro, 0) + int(c.pop_2020 or 0)
    _, r_ift, _, _ = _levers()
    out: List[CountyHsDemand] = []
    for c in counties:
        md = metro_by_name.get(c.metro)
        denom = metro_pop.get(c.metro, 0)
        share = (c.pop_2020 / denom) if denom else 0.0
        legs = int(round((md.ift_legs if md else 0) * share))
        # dollars off the serviceable legs share (keep the metro s(m) implicitly)
        serv_share = (md.serviceable_legs / md.ift_legs) if (md and md.ift_legs) else 0.0
        dollars = int(round(legs * serv_share)) * r_ift[1]
        out.append(CountyHsDemand(
            county=c.name, state=c.state, fips=c.fips, cbsa_name=c.cbsa_name,
            metro=c.metro, role=c.role, pop_2020=int(c.pop_2020 or 0),
            pop_65_plus=c.pop_65_plus, pop_share_of_metro=round(share, 4),
            ift_legs=legs, demand_dollars=dollars,
            anchor_systems=(md.anchor_systems if md else ())))
    out.sort(key=lambda c: c.ift_legs, reverse=True)
    return tuple(out)


# ─────────────────────────────────────────────────────────────────────────────
# Demand-data inventory — every driver we can source, its basis + what it yields
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class DemandSignal:
    driver: str
    what_it_yields: str
    source: str
    basis: str                       # SOURCED | CONNECTOR | GOV | ACADEMIC
    status: str                      # live | ingest-ready | to-source
    dataset_id: str = ""


@dataclass(frozen=True)
class DemandInventory:
    available: bool
    signals: Tuple[DemandSignal, ...] = ()
    n_live: int = 0
    n_ingest_ready: int = 0
    n_to_source: int = 0
    source_label: str = ""


_SIGNALS: Tuple[DemandSignal, ...] = (
    DemandSignal(
        "Hospital discharges (throughput)",
        "The volume base — discharges ≈ patient_days ÷ ALOS per hospital.",
        "HCRIS Worksheet S-3 Pt I (vendored)", "SOURCED", "live",
        "hcris_s3_part_i"),
    DemandSignal(
        "Hospital universe (origins)",
        "The origin count + type per county/metro — who orders transport.",
        "CMS Provider-of-Services / Care Compare", "SOURCED", "live",
        "provider_data_hospital_general"),
    DemandSignal(
        "Payer mix per hospital",
        "Medicare/Medicaid day-share → the reimbursement blend per system.",
        "HCRIS S-3 (medicare_days / medicaid_days)", "SOURCED", "live",
        "hcris_s3_part_i"),
    DemandSignal(
        "Discharge disposition split",
        "The f_IFT fraction — ~35M inpatient discharges/yr, ~20-25% to a facility "
        "(SNF/IRF/LTCH/transfer); the scheduled discharge-book share.",
        "AHRQ HCUP NIS (2022) — loader in rcm_mc/data/ahrq_hcup.py (source_db=NIS)",
        "ACADEMIC", "ingest-ready", "ahrq_hcup_nis"),
    DemandSignal(
        "Hospital-to-hospital up-transfer rate",
        "The high-$ escalation legs — ~2.0M ED-to-ED transfers/yr (NEDS 2018-2022), "
        "by condition (STEMI/stroke/sepsis/trauma).",
        "AHRQ HCUP NEDS (2022) transfer disposition — loader source_db=NEDS",
        "ACADEMIC", "ingest-ready", "ahrq_hcup_neds"),
    DemandSignal(
        "ED-origin transfers (refreshed)",
        "ED→acute transfer volume — now ~2.0M/yr (NEDS 2018-2022), superseding the "
        "stale 1.9M/2009 read; NHAMCS ~1.1-1.3M/yr corroborates.",
        "AHRQ HCUP NEDS (2022) + CDC NHAMCS", "ACADEMIC", "ingest-ready",
        "ahrq_hcup_neds"),
    DemandSignal(
        "EMS interfacility activations",
        "The direct EMS-activation denominator — 54.2M activations/yr (2023), of "
        "which 'Hospital-to-Hospital Transfer' is a tracked service type.",
        "NEMSIS national EMS dataset (NHTSA, 2023 v3.5 public-release)", "ACADEMIC",
        "to-source", "nemsis_public_release"),
    DemandSignal(
        "Hospital catchment / served population",
        "Hospital→patient-ZIP flows — the counties a system actually serves.",
        "CMS Hospital Service Area file", "CONNECTOR", "ingest-ready",
        "cms_open_data_hospital_service_area"),
    DemandSignal(
        "Part-B ambulance utilization",
        "Line-level A0426-A0434 volume & spend — the definitive claims count.",
        "CMS Physician/Supplier Procedure Summary", "CONNECTOR", "ingest-ready",
        "cms_open_data_physician_supplier_procedure_summary"),
    DemandSignal(
        "Aging catchment (65+)",
        "65+ population by county — the per-capita demand multiplier.",
        "US Census ACS county profile", "CONNECTOR", "ingest-ready",
        "census_acs_county_profile"),
    DemandSignal(
        "Inpatient occupancy trend",
        "Throughput pressure over time (the transfer-demand proxy).",
        "CMS HCRIS (patient-days / bed-days)", "SOURCED", "live",
        "hcris_s3_part_i"),
    DemandSignal(
        "Case-mix / acuity",
        "The BLS↔ALS↔SCT mix and $/leg — higher CMI → more CCT/SCT.",
        "CMS IPPS case-mix index", "GOV", "to-source"),
    DemandSignal(
        "Chronic-disease prevalence",
        "The conditions that generate transfers, by county.",
        "CDC Chronic Disease Indicators", "CONNECTOR", "ingest-ready",
        "cdc_data_chronic_disease_indicators"),
)


def demand_data_inventory() -> DemandInventory:
    """Every demand driver we can source, its basis, status, and what it yields —
    the answer to 'what more demand data do we need.' Never raises."""
    live = sum(1 for s in _SIGNALS if s.status == "live")
    ready = sum(1 for s in _SIGNALS if s.status == "ingest-ready")
    tosrc = sum(1 for s in _SIGNALS if s.status == "to-source")
    return DemandInventory(
        available=True, signals=_SIGNALS, n_live=live, n_ingest_ready=ready,
        n_to_source=tosrc,
        source_label=("Demand-driver inventory — SOURCED (vendored HCRIS/provider "
                      "rolls), CONNECTOR (ingest-ready estate datasets), and the "
                      "GOV/ACADEMIC series still to source"))


# ─────────────────────────────────────────────────────────────────────────────
def hs_demand_summary() -> Dict[str, Any]:
    """Counts for the page header / meta line. Never raises."""
    hd = hospital_demand()
    sr = health_system_rollup()
    cd = county_demand()
    inv = demand_data_inventory()
    total_disch = sum(m.discharges for m in hd)
    total_legs = sum(m.ift_legs for m in hd)
    sourced = any(m.discharge_basis == "SOURCED" for m in hd)
    return {
        "n_metros": len(hd),
        "n_systems": len(sr),
        "n_counties": len(cd),
        "total_discharges": total_disch,
        "total_ift_legs": total_legs,
        "discharge_sourced": sourced,
        "n_signals": len(inv.signals),
        "n_live": inv.n_live,
        "n_ingest_ready": inv.n_ingest_ready,
        "n_to_source": inv.n_to_source,
    }
