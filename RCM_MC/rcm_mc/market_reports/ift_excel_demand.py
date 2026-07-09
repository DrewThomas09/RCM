"""IFT DEMAND workbook — the whole demand side, volume-first, in one download.

A SEPARATE, demand-only companion to the market-study pack (``ift_excel``). Where
the market pack answers "how big is the dollar market and who competes," this
workbook answers the one question a diligence team keeps coming back to on the
demand side: **how many transports are there a year, and where do they come
from?** Volume is the spine — every sheet ladders off a transports/year figure,
and every figure carries a source.

Contents (demand only):
  * National transport VOLUME — the transports/year funnel, national → IFT slice,
    the centerpiece (from ``ift_demand.national_transport_volume``).
  * Volume sources — every citation behind the funnel, clickable.
  * CMS code analysis — the ground-ambulance HCPCS mapped to the three IFT acuity
    types (BLS/ALS/SCT) × emergency/non-emergency.
  * Emergency vs non-emergency prevalence — the split, from the transfer registry.
  * Demand by condition — YEAR OVER YEAR, with the case growth each year.
  * Aggregate demand trajectory — the blended YoY case curve.
  * Clinical demand engine — the condition registry (cases → codes → volume).
  * Health-system demand — HCRIS-discharge-driven, the health-system BUYER view
    (SNF is not the buyer, so it is not sized here).
  * Regional demand — subcounty/region facility base + demographic growth.
  * County demand — the operator footprint counties.
  * Demand-data inventory — what demand data we hold, its source, and what to pull.
  * Provenance & methodology — the honesty-basis contract for this workbook.

Built on the stdlib-only :mod:`rcm_mc.exports.xlsx_writer` — NO runtime
dependency added. Every builder DEGRADES: a missing analytic drops its sheet
rather than raising, so the download always succeeds even offline where a
network-gated / pandas-gated read is dark. Honesty travels into every
value-bearing cell via a ``Basis`` column (GOV / SOURCED / ACADEMIC /
ILLUSTRATIVE / DERIVED / FRAMEWORK). No trade / market-research-firm figures are
used anywhere — the all-payer volume line is DERIVED from the GOV anchor.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..exports.xlsx_writer import Sheet, write_xlsx, Link, basis_style, F  # noqa: F401
from . import ift_demand as _dd
from . import ift_clinical_demand as _cd

_H = "header"
_L = "label"


def _safe(fn, default=None):
    """Call an analytic, swallow any failure (degrade-never-raise)."""
    try:
        return fn()
    except Exception:  # noqa: BLE001
        return default


def _bn_to_dollars(bn: Optional[float]) -> Optional[float]:
    """A $B figure -> raw dollars for the ``money`` number format. None-safe."""
    try:
        return float(bn) * 1e9
    except (TypeError, ValueError):
        return None


def _pctf(x: Optional[float]) -> Optional[float]:
    """A percent expressed as 0-100 -> a 0-1 fraction for the ``pct`` cell format."""
    try:
        return float(x) / 100.0
    except (TypeError, ValueError):
        return None


# ═════════════════════════════════════════════════════════════════════════════
# 1 — National transport VOLUME (the centerpiece)
# ═════════════════════════════════════════════════════════════════════════════
def _volume_sheet() -> Optional[Sheet]:
    vol = _safe(_dd.national_transport_volume)
    if not (vol and getattr(vol, "available", False)):
        return None
    rows: List[List[Any]] = [
        [("National transport volume — how many transports a year?", _H)],
        [("The demand spine. A top-down transports/year funnel from the hardest "
          "GOV anchor (Medicare fee-for-service ground) out to an all-payer band "
          "and down to the interfacility slice. Every tier is sourced; the "
          "all-payer line is DERIVED from the GOV figure — no trade estimate.")],
        [],
        [("The GOV anchor", _H), ("Value", _H), ("Basis", _H)],
        ["Medicare FFS ground transports (CY%d)" % vol.ffs_year,
         (vol.ffs_transports_m * 1e6, "num"), "GOV"],
        ["Medicare FFS ground spend (CY%d)" % vol.ffs_year,
         (_bn_to_dollars(vol.ffs_spend_bn), "money"), "GOV"],
        ["Ground ambulance organizations paid", (vol.ffs_orgs, "num"), "GOV"],
        [],
        [("Transports/year funnel", _H), ("Transports / yr", _H), ("Basis", _H),
         ("Source", _H), ("What it counts", _H)],
    ]
    for t in vol.tiers:
        rows.append([t.tier, t.value, t.basis, t.source, t.note])
    # Acuity split (BLS / ALS / SCT) on the Medicare FFS base.
    rows += [
        [],
        [("By acuity type (on the %.1fM Medicare FFS base)"
          % vol.ffs_transports_m, _H)],
        [("Acuity type", _H), ("Share", _H), ("Transports (M)", _H),
         ("Basis", _H), ("Read", _H)],
    ]
    for a in vol.acuity_split:
        rows.append([a.label, (_pctf(a.share_pct), "pct"),
                     (a.transports_m, "num2"), a.basis, a.note])
    # Emergency vs non-emergency split.
    rows += [
        [],
        [("Emergency vs non-emergency (on the %.1fM Medicare FFS base)"
          % vol.ffs_transports_m, _H)],
        [("Split", _H), ("Share", _H), ("Transports (M)", _H), ("Basis", _H),
         ("Read", _H)],
    ]
    for e in vol.emergency_split:
        rows.append([e.label, (_pctf(e.share_pct), "pct"),
                     (e.transports_m, "num2"), e.basis, e.note])
    rows += [
        [],
        [("Source", _H), vol.source_label],
        [("Note", _H), vol.note],
    ]
    return Sheet("National volume", rows,
                 col_widths=[40, 18, 14, 60, 60])


# ═════════════════════════════════════════════════════════════════════════════
# 2 — Volume sources (every citation, clickable)
# ═════════════════════════════════════════════════════════════════════════════
# The user's ask is explicit: "provide all the sources." This sheet is the
# audit trail for every number on the National-volume sheet — GOV first, then
# the claims analyses, then the peer-reviewed interfacility studies.
_VOLUME_SOURCES: List[List[Any]] = [
    ["Medicare FFS ground: 11.3M transports, $5.3B, ~10,600 orgs (CY2024)", "GOV",
     Link("MedPAC — Ambulance Services Payment System (Payment Basics, Oct 2024)",
          "https://www.medpac.gov/wp-content/uploads/2024/10/"
          "MedPAC_Payment_Basics_24_ambulance_FINAL_SEC.pdf")],
    ["Ground ambulance payment adequacy + volume context (mandated report)", "GOV",
     Link("MedPAC — Mandated report: Payment for ground ambulance services",
          "https://www.medpac.gov/document/"
          "mandated-report-payment-for-ground-ambulance-services/")],
    ["Service-level & emergency/non-emergency mix (FFS claims, 2017-2020)", "GOV",
     Link("CMS — Ground Ambulance Industry Trends 2017-2020 (FFS claims analysis)",
          "https://www.cms.gov/files/document/"
          "ground-ambulance-industry-trends-2017-2020-report-analysis-"
          "medicare-fee-service-claims.pdf")],
    ["Agency cost/utilization + BLS emergency drift 2018->2022", "GOV",
     Link("CMS — Ground Ambulance Data Collection System (GADCS) Yr1/2 (RAND)",
          "https://www.cms.gov/files/document/"
          "medicare-ground-ambulance-data-collection-system-gadcs-report-"
          "year-1-and-year-2-cohort-analysis.pdf")],
    ["Ambulance Fee Schedule rates / HCPCS RVUs (the price side of volume)", "GOV",
     Link("CMS — Ambulance Fee Schedule Public Use Files",
          "https://www.cms.gov/medicare/payment/fee-schedules/ambulance/"
          "ambulance-fee-schedule-public-use-files")],
    ["Coverage / medical-necessity definitions by transport level", "GOV",
     Link("CMS — Medicare Benefit Policy Manual, Ch. 10 (Ambulance)",
          "https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/"
          "Downloads/bp102c10.pdf")],
    ["Interfacility transports to the ED ~1.1M/yr (2014-17, NHAMCS)", "ACADEMIC",
     Link("Am J Emerg Med 2020 — IFT by EMS in the US (NHAMCS estimates)",
          "https://www.sciencedirect.com/science/article/abs/pii/"
          "S0735675720303946")],
    ["IFT-to-ED ~1.3M/yr mean, rising (nationwide trend analysis)", "ACADEMIC",
     Link("Am J Emerg Med 2026 — IFT to the ED via EMS: nationwide trend",
          "https://www.sciencedirect.com/science/article/abs/pii/"
          "S0735675726001907")],
    ["All-payer utilization & cost of ground ambulance (claims database)", "SOURCED",
     Link("FAIR Health — A Window into Utilization and Cost of Ground Ambulance",
          "https://s3.amazonaws.com/media2.fairhealth.org/brief/asset/"
          "A%20Window%20into%20Utilization%20and%20Cost%20of%20Ground%20"
          "Ambulance%20Services%20-%20A%20FAIR%20Health%20Brief.pdf")],
]


def _volume_sources_sheet() -> Sheet:
    rows: List[List[Any]] = [
        [("Volume sources — every citation behind the funnel", _H)],
        [("The audit trail for the National-volume sheet. GOV government sources "
          "first, then the peer-reviewed interfacility studies. The all-payer "
          "band is DERIVED from the GOV Medicare figure — it has no source row "
          "because no trade/market-research-firm estimate is used.")],
        [],
        [("What it establishes", _H), ("Basis", _H), ("Source (click)", _H)],
    ]
    rows.extend(_VOLUME_SOURCES)
    rows += [
        [],
        [("Method note on the all-payer line", _L)],
        [("All-payer ground volume is computed as the GOV Medicare-FFS figure "
          "(11.3M) divided by Medicare FFS's ~25-32% share of all-payer ground "
          "volume — a DERIVED assumption band, shown so the GOV slice has "
          "context, NOT a published number.")],
    ]
    return Sheet("Volume sources", rows, col_widths=[48, 12, 70])


# ═════════════════════════════════════════════════════════════════════════════
# 2b — Demand databases (the multi-source triangulation: NEDS / NIS / NEMSIS / …)
# ═════════════════════════════════════════════════════════════════════════════
def _sources_matrix_sheet() -> Optional[Sheet]:
    m = _safe(_dd.demand_source_matrix)
    if not (m and getattr(m, "available", False)):
        return None
    rows: List[List[Any]] = [
        [("Demand databases — the multiple ways to measure IFT volume", _H)],
        [("Are we using NEDS, or other databases? Yes — this is the triangulation. "
          "Each independent database that measures IFT demand volume, its most-"
          "current published figure, the data year, the honesty basis, and a "
          "source URL. %d GOV, %d SOURCED, %d ACADEMIC — no trade / market-"
          "research firm." % (m.n_gov, m.n_sourced, m.n_academic))],
        [],
        [("Database", _H), ("Steward", _H), ("What it measures for IFT", _H),
         ("Most-current read", _H), ("Data year", _H), ("Basis", _H),
         ("Source (click)", _H), ("Note", _H)],
    ]
    for s in m.sources:
        link = Link(s.name, s.url) if getattr(s, "url", "") else s.name
        rows.append([s.name, s.steward, s.measures, s.current_read, s.data_year,
                     s.basis, link, s.note])
    rows += [
        [],
        [("Source", _H), m.source_label],
        [("Note", _H), m.note],
    ]
    return Sheet("Demand databases", rows,
                 col_widths=[30, 22, 44, 34, 16, 12, 40, 44])


# ═════════════════════════════════════════════════════════════════════════════
# 3 — CMS code analysis (HCPCS × acuity × emergency)
# ═════════════════════════════════════════════════════════════════════════════
def _code_analysis_sheet() -> Optional[Sheet]:
    hc = _safe(_dd.hcpcs_acuity_analysis)
    if not (hc and getattr(hc, "available", False)):
        return None
    rows: List[List[Any]] = [
        [("CMS code analysis — ground HCPCS by the three IFT acuity types", _H)],
        [("The ground-ambulance base codes mapped to BLS / ALS / SCT and the "
          "emergency/non-emergency dimension, with the interfacility relevance of "
          "each. RVUs are GOV (42 CFR 414.610); the classification is authored "
          "over the code descriptors (SCT is interfacility by definition).")],
        [],
        [("HCPCS", _H), ("Descriptor", _H), ("Acuity", _H), ("Emergency?", _H),
         ("RVU", _H), ("Interfacility relevance", _H)],
    ]
    for r in hc.rows:
        rows.append([r.hcpcs, r.descriptor, r.acuity_group, r.emergency,
                     (r.rvu, "num2"), r.ift_relevance])
    if hc.types:
        rows += [
            [],
            [("Acuity-type rollup", _H)],
            [("Acuity type", _H), ("Codes", _H), ("RVU low", _H), ("RVU high", _H),
             ("Read", _H)],
        ]
        for t in hc.types:
            rows.append([t.acuity_type, ", ".join(t.codes),
                         (t.rvu_low, "num2"), (t.rvu_high, "num2"), t.read])
    rows += [[], [("Source", _H), hc.source_label]]
    if getattr(hc, "note", ""):
        rows.append([("Note", _H), hc.note])
    return Sheet("CMS code analysis", rows,
                 col_widths=[10, 26, 10, 16, 8, 60])


# ═════════════════════════════════════════════════════════════════════════════
# 4 — Emergency vs non-emergency prevalence
# ═════════════════════════════════════════════════════════════════════════════
def _emergency_sheet() -> Optional[Sheet]:
    ep = _safe(_dd.emergency_prevalence)
    if not (ep and getattr(ep, "available", False)):
        return None
    rows: List[List[Any]] = [
        [("Emergency vs non-emergency prevalence", _H)],
        [("How the interfacility book splits between emergent up-transfers and "
          "scheduled step-down / discharge legs, read from the clinical transfer "
          "registry (escalation vs step-down vs direct-admit).")],
        [],
        [("Headline", _H), ("Value", _H), ("Basis", _H)],
        ["Emergent transfer scenarios", (ep.n_emergent_scenarios, "num"), "ACADEMIC"],
        ["Non-emergent transfer scenarios",
         (ep.n_nonemergent_scenarios, "num"), "ACADEMIC"],
        ["High-acuity (ALS+) share of transfers",
         (_frac_or_none(ep.high_acuity_share), "pct"), "ILLUSTRATIVE"],
        ["Critical-care (SCT/CCT) share of transfers",
         (_frac_or_none(ep.cct_sct_share), "pct"), "ILLUSTRATIVE"],
    ]
    if isinstance(ep.by_transfer_type, dict) and ep.by_transfer_type:
        rows += [[], [("By transfer type", _H), ("Scenarios", _H)]]
        for k, v in ep.by_transfer_type.items():
            rows.append([str(k), (v, "num")])
    if isinstance(ep.by_family, dict) and ep.by_family:
        rows += [[], [("By clinical family", _H), ("Scenarios", _H)]]
        for k, v in ep.by_family.items():
            rows.append([str(k), (v, "num")])
    rows += [[], [("Source", _H), ep.source_label]]
    if getattr(ep, "note", ""):
        rows.append([("Note", _H), ep.note])
    return Sheet("Emergency mix", rows, col_widths=[42, 16, 16])


def _frac_or_none(x: Any) -> Optional[float]:
    """Shares from the registry are already 0-1 fractions; pass through, None-safe."""
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return f if 0.0 <= f <= 1.5 else f / 100.0


# ═════════════════════════════════════════════════════════════════════════════
# 5 — Demand by condition (YEAR OVER YEAR)
# ═════════════════════════════════════════════════════════════════════════════
def _condition_yoy_sheet() -> Optional[Sheet]:
    proj = _safe(lambda: _cd.condition_yoy_projection(horizon=5), default=())
    if not proj:
        return None
    # Column headers: one per projected year (base -> base+horizon).
    years = [p.year for p in proj[0].points]
    year_hdrs = [(str(y), _H) for y in years]
    rows: List[List[Any]] = [
        [("Demand by condition — year over year", _H)],
        [("Each acute condition's transferable case volume, projected forward on "
          "its demographic growth (incidence held constant). The per-year cells "
          "show the case COUNT; the CAGR and total added cases show how fast the "
          "book is growing. Volumes are GOV/ACADEMIC; growth is ILLUSTRATIVE "
          "(Census age-band CAGRs).")],
        [],
        [("Condition", _H), ("Family", _H), ("Acuity", _H)]
        + year_hdrs + [("CAGR", _H), ("Added cases", _H), ("Basis", _H)],
    ]
    for c in proj:
        vol_cells = [(p.volume, "num") for p in c.points]
        rows.append(
            [c.name, c.family, c.transport_acuity] + vol_cells
            + [(c.cagr, "pct"), (c.added_cases, "num"),
               (c.basis.split()[0] if c.basis else "")])
    src = ""
    try:
        src = proj[0].basis
    except Exception:  # noqa: BLE001
        pass
    rows += [
        [],
        [("Read", _L)],
        [("Growth is demographic: each condition's age skew is weighted by the "
          "Census age-band population CAGRs, incidence held constant — so the "
          "case curve is the aging wave working through the transfer book.")],
        [], [("Basis", _H), src or "ILLUSTRATIVE (demographic CAGRs)"],
    ]
    widths = [26, 16, 14] + [12] * len(years) + [10, 14, 12]
    return Sheet("Demand by condition YoY", rows, col_widths=widths)


# ═════════════════════════════════════════════════════════════════════════════
# 6 — Aggregate demand trajectory (blended YoY)
# ═════════════════════════════════════════════════════════════════════════════
def _aggregate_yoy_sheet() -> Optional[Sheet]:
    ag = _safe(lambda: _cd.aggregate_demand_yoy(horizon=5))
    if not (ag and getattr(ag, "available", False)):
        return None
    # Map year-offsets (0..horizon) to calendar years off the condition base year.
    base_year = 0
    proj = _safe(lambda: _cd.condition_yoy_projection(horizon=5), default=())
    if proj:
        base_year = getattr(proj[0], "base_year", 0) or 0
    rows: List[List[Any]] = [
        [("Aggregate demand trajectory — blended year over year", _H)],
        [("The whole transferable case book summed and rolled forward. The "
          "blended CAGR is ~%.1f%%/yr across %d conditions — the demographic pull "
          "on IFT demand, before any share gains."
          % ((ag.blended_cagr or 0) * 100, ag.n_conditions))],
        [],
        [("Year", _H), ("Transferable cases", _H), ("YoY growth", _H),
         ("Added cases", _H)],
    ]
    for p in ag.points:
        yr = (base_year + p.year) if base_year else p.year
        yr_label = str(yr) if base_year else f"Y+{p.year}"
        rows.append([yr_label, (p.volume, "num"),
                     (_pctf(p.yoy_growth_pct), "pct"), (p.added_cases, "num")])
    rows += [
        [],
        [("Base volume", _L), (ag.base_volume, "num")],
        [("End volume", _L), (ag.end_volume, "num")],
        [("Blended CAGR", _L), (ag.blended_cagr, "pct")],
        [],
        [("Source", _H), ag.source_label],
    ]
    if getattr(ag, "note", ""):
        rows.append([("Note", _H), ag.note])
    return Sheet("Aggregate demand YoY", rows, col_widths=[14, 20, 14, 16])


# ═════════════════════════════════════════════════════════════════════════════
# 7 — Clinical demand engine (the condition registry)
# ═════════════════════════════════════════════════════════════════════════════
def _clinical_sheet() -> Optional[Sheet]:
    conds = _safe(_cd.all_conditions, default=[])
    if not conds:
        return None
    rows: List[List[Any]] = [
        [("Clinical demand engine — cases -> codes -> volume -> growth", _H)],
        [("A ground-IFT operator's volume equals the acute patients who must move "
          "between facilities. Volumes are published (GOV/ACADEMIC); growth is the "
          "demographic CAGR (ILLUSTRATIVE, named basis).")],
        [],
        [("Condition", _H), ("Family", _H), ("Transfer type", _H),
         ("ICD-10-CM", _H), ("MS-DRG", _H), ("Destination capability", _H),
         ("National volume/yr", _H), ("Measure", _H), ("Volume basis", _H),
         ("Growth CAGR", _H), ("Growth drivers", _H)],
    ]
    for c in conds:
        icd = ", ".join(c.icd10) if c.icd10 else ""
        drg = ", ".join(c.ms_drg) if c.ms_drg else ""
        nv = c.national_volume
        vbasis = (nv.source_label.split()[0] if nv and nv.source_label else "")
        vol = (nv.value if nv and nv.value else 0)
        rows.append([
            c.name, c.family, c.transfer_type, icd, drg,
            c.destination_capability,
            (vol, "num") if vol else "not separately enumerated",
            (nv.measure if nv else ""), vbasis,
            (c.growth.cagr, "pct") if c.growth else "—",
            (c.growth.drivers if c.growth else "")])
    return Sheet("Clinical demand engine", rows,
                 col_widths=[28, 14, 20, 22, 16, 26, 16, 22, 12, 11, 40])


# ═════════════════════════════════════════════════════════════════════════════
# 8 — Health-system demand (HCRIS-discharge-driven; the BUYER view)
# ═════════════════════════════════════════════════════════════════════════════
def _hs_demand_sheet() -> Optional[Sheet]:
    try:
        from . import ift_hs_demand as _hs
    except Exception:  # noqa: BLE001
        return None
    metros = _safe(_hs.hospital_demand, default=())
    systems = _safe(_hs.health_system_rollup, default=())
    if not metros and not systems:
        return None
    rows: List[List[Any]] = [
        [("Health-system demand — the BUYER view (HCRIS discharge-driven)", _H)],
        [("The health systems order and pay for IFT, so demand is sized off THEIR "
          "throughput: discharges ≈ patient_days ÷ ALOS per hospital (HCRIS "
          "Worksheet S-3). SNF is NOT the buyer, so it is not sized here. Legs "
          "are ILLUSTRATIVE from the discharge base; beds/discharges are SOURCED "
          "(pandas-gated — 0 when the HCRIS panel is offline).")],
        [],
        [("Metro", _H), ("Region", _H), ("Hospitals", _H), ("HCRIS beds", _H),
         ("Discharges", _H), ("IFT legs/yr", _H), ("Serviceable legs", _H),
         ("Demand $", _H), ("Anchor systems", _H)],
    ]
    for m in metros:
        rows.append([
            m.metro, m.region_label, (m.n_hospitals, "num"),
            (m.hcris_beds, "num"), (m.discharges, "num"),
            (m.ift_legs, "num"), (m.serviceable_legs, "num"),
            (m.demand_dollars, "money"),
            ", ".join(m.anchor_systems) if m.anchor_systems else ""])
    if systems:
        rows += [
            [],
            [("Health-system rollup (the account view)", _H)],
            [("System", _H), ("Tier", _H), ("Metros", _H), ("IFT legs/yr", _H),
             ("Serviceable legs", _H), ("Demand $", _H), ("Strategy", _H)],
        ]
        for s in systems:
            rows.append([
                s.system, s.tier, (s.n_metros, "num"), (s.ift_legs, "num"),
                (s.serviceable_legs, "num"), (s.demand_dollars, "money"),
                s.strategy])
    return Sheet("Health-system demand", rows,
                 col_widths=[24, 14, 10, 11, 12, 12, 14, 16, 30])


# ═════════════════════════════════════════════════════════════════════════════
# 9 — Regional demand (subcounty / region facility base + demographics)
# ═════════════════════════════════════════════════════════════════════════════
def _regional_sheet() -> Optional[Sheet]:
    reg = _safe(_dd.regional_demand, default=())
    if not reg:
        return None
    rows: List[List[Any]] = [
        [("Regional demand — facility base by region", _H)],
        [("The SOURCED facility base grouped by region: hospitals, HCRIS beds, "
          "post-acute destinations, and the demand dollars that structure "
          "supports. The demographic growth read sits on the demographic engine "
          "sheet. Counts are SOURCED; SAM dollars are ILLUSTRATIVE.")],
        [],
        [("Region", _H), ("Metros", _H), ("Hospitals", _H), ("HCRIS beds", _H),
         ("SNF", _H), ("Dialysis", _H), ("Post-acute dest.", _H),
         ("Demand $", _H)],
    ]
    for r in reg:
        rows.append([
            r.region_label, (r.n_metros, "num"), (r.n_hospitals, "num"),
            (r.hcris_beds, "num"), (r.n_snf, "num"), (r.n_dialysis, "num"),
            (r.n_postacute_destinations, "num"), (r.sam_dollars, "money")])
    return Sheet("Regional demand", rows,
                 col_widths=[22, 10, 11, 11, 8, 10, 16, 16])


# ═════════════════════════════════════════════════════════════════════════════
# 10 — County demand (the operator footprint)
# ═════════════════════════════════════════════════════════════════════════════
def _county_sheet() -> Optional[Sheet]:
    try:
        from . import ift_hs_demand as _hs
    except Exception:  # noqa: BLE001
        return None
    counties = _safe(_hs.county_demand, default=())
    if not counties:
        return None
    rows: List[List[Any]] = [
        [("County demand — the operator footprint, resolved to counties", _H)],
        [("The footprint counties with population, 65+ population, the county's "
          "share of its metro, and the IFT demand each supports. Population is "
          "GOV (Census); demand legs/$ are ILLUSTRATIVE from the health-system "
          "discharge base.")],
        [],
        [("County", _H), ("State", _H), ("CBSA", _H), ("Role", _H),
         ("Pop 2020", _H), ("Pop 65+", _H), ("Share of metro", _H),
         ("IFT legs/yr", _H), ("Demand $", _H), ("Anchor systems", _H)],
    ]
    for c in counties:
        rows.append([
            c.county, c.state, c.cbsa_name, c.role,
            (c.pop_2020, "num"), (c.pop_65_plus, "num"),
            (_frac_or_none(c.pop_share_of_metro), "pct"),
            (c.ift_legs, "num"), (c.demand_dollars, "money"),
            ", ".join(c.anchor_systems) if c.anchor_systems else ""])
    return Sheet("County demand", rows,
                 col_widths=[22, 8, 26, 16, 12, 12, 14, 12, 16, 28])


# ═════════════════════════════════════════════════════════════════════════════
# 11 — Demographic engine (the growth that drives demand)
# ═════════════════════════════════════════════════════════════════════════════
def _demographic_sheet() -> Optional[Sheet]:
    nf = _safe(_dd.national_frame)
    if not (nf and getattr(nf, "available", False)):
        return None
    rows: List[List[Any]] = [
        [("Demographic engine — the aging wave that drives IFT demand", _H)],
        [("IFT volume growth is demographic: the 75+ bands use post-acute "
          "transfer at the highest per-capita rate, and they are the fastest "
          "growing this decade. This is the engine behind every YoY case curve "
          "on the condition sheets.")],
        [],
        [("Age band", _H), ("Growth read", _H)],
    ]
    for band, read in (nf.age_bands or ()):
        rows.append([band, read])
    # The per-band CAGRs actually used by the projection (from the fallback table).
    cagrs = _safe(_pop_growth_table, default={})
    if cagrs:
        rows += [
            [],
            [("Per-band population CAGR (used by the YoY projection)", _H)],
            [("Age band", _H), ("5-yr CAGR", _H), ("Basis", _H)],
        ]
        for band, cagr in cagrs.items():
            rows.append([band, (cagr, "pct"), "ILLUSTRATIVE"])
    rows += [
        [],
        [("National price/volume/market growth", _H), ("Value", _H)],
        ["Price growth (AIF lever)",
         (_frac_or_none(nf.price_growth_pct), "pct") if nf.price_growth_pct
         is not None else "—"],
        ["Volume growth (demographic)",
         (_frac_or_none(nf.volume_growth_pct), "pct") if nf.volume_growth_pct
         is not None else "—"],
        ["Blended market growth",
         (_frac_or_none(nf.market_growth_pct), "pct") if nf.market_growth_pct
         is not None else "—"],
        [],
        [("Source", _H), nf.source_label],
    ]
    return Sheet("Demographic engine", rows, col_widths=[22, 72, 14])


def _pop_growth_table() -> Dict[str, float]:
    """The per-age-band 5-yr population CAGRs the YoY projection runs on. Reads the
    demand-forecast table when ingested; falls back to the module constant offline
    (so the sheet never blanks)."""
    fb = getattr(_cd, "_POP_GROWTH_FALLBACK", {}) or {}
    out: Dict[str, float] = {}
    for band, d in fb.items():
        try:
            out[band] = float(d.get("cagr_5yr", 0.0))
        except Exception:  # noqa: BLE001
            continue
    return out


# ═════════════════════════════════════════════════════════════════════════════
# 12 — Demand-data inventory (what we hold + its source + what to pull)
# ═════════════════════════════════════════════════════════════════════════════
def _inventory_sheet() -> Optional[Sheet]:
    try:
        from . import ift_hs_demand as _hs
    except Exception:  # noqa: BLE001
        return None
    inv = _safe(_hs.demand_data_inventory)
    if not (inv and getattr(inv, "available", False)):
        return None
    rows: List[List[Any]] = [
        [("Demand-data inventory — what we hold, where it comes from, what's next",
          _H)],
        [("Every demand signal this workbook draws on, its dataset, source, and "
          "whether it is live, ingest-ready, or still to source. The honesty "
          "contract in one place: %d live, %d ingest-ready, %d to source."
          % (inv.n_live, inv.n_ingest_ready, inv.n_to_source))],
        [],
        [("Driver", _H), ("What it yields", _H), ("Source", _H), ("Basis", _H),
         ("Status", _H), ("Dataset ID", _H)],
    ]
    for s in inv.signals:
        rows.append([s.driver, s.what_it_yields, s.source, s.basis, s.status,
                     s.dataset_id])
    rows += [[], [("Source", _H), inv.source_label]]
    return Sheet("Demand-data inventory", rows,
                 col_widths=[26, 40, 30, 14, 14, 22])


# ═════════════════════════════════════════════════════════════════════════════
# 13 — Provenance & methodology
# ═════════════════════════════════════════════════════════════════════════════
def _provenance_sheet() -> Sheet:
    rows: List[List[Any]] = [
        [("Provenance & methodology — the demand workbook's honesty contract", _H)],
        [("Every value-bearing cell carries a Basis. This sheet says what each "
          "label means and what is real vs modeled, so nothing is taken on faith.")],
        [],
        [("Basis", _H), ("What it means on the demand side", _H)],
        [("GOV", "basis_gov"),
         "Published government figure — MedPAC ambulance Payment Basics, CMS FFS "
         "claims analyses, CMS GADCS (RAND), Census population. The volume anchor."],
        [("SOURCED", "basis_sourced"),
         "Read from a real dataset we hold or a named claims database (HCRIS "
         "discharge base, FAIR Health utilization). 0 when a pandas-gated read is "
         "offline — the sheet degrades, it does not invent."],
        [("ACADEMIC", "basis_academic"),
         "Peer-reviewed / survey estimate — the NHAMCS interfacility studies. A "
         "FLOOR on IFT volume (ED arrivals only)."],
        [("ILLUSTRATIVE", "basis_illustrative"),
         "Modeled on a NAMED basis — the demographic CAGRs (Census age-band "
         "growth, incidence held constant) behind every YoY case curve, and the "
         "leg/$ conversions off the discharge base."],
        ["DERIVED",
         "Computed from a GOV figure with an explicit, stated assumption — the "
         "all-payer volume band (Medicare FFS ÷ its share of all-payer volume). "
         "NOT a trade/market-research-firm number."],
        [],
        [("What this workbook deliberately does NOT do", _L)],
        [("• It does not size SNF as a buyer — the health systems order and pay "
          "for IFT, so demand is sized off health-system throughput.")],
        [("• It does not use any trade / market-research-firm volume estimate — "
          "the all-payer line is DERIVED from the GOV Medicare anchor.")],
        [("• It does not present the NHAMCS interfacility figure as the whole IFT "
          "market — it is a FLOOR (ED arrivals only); the scheduled discharge "
          "book is additive and sized from HCRIS.")],
        [],
        [("Where this lives online (click to open)", _H)],
        ["", Link("Demand deep-dive", "https://pedesk.app/ift-demand"),
         "National → subcounty demand, the CMS code analysis, YoY condition curves."],
        ["", Link("Health-system demand", "https://pedesk.app/ift-hs-demand"),
         "The HCRIS discharge-driven, health-system-buyer demand view."],
        ["", Link("Download this workbook", "https://pedesk.app/api/ift/demand.xlsx"),
         "This Excel — always the latest build."],
    ]
    return Sheet("Provenance", rows, col_widths=[16, 92, 40])


# ═════════════════════════════════════════════════════════════════════════════
# Contents + assembly
# ═════════════════════════════════════════════════════════════════════════════
_SHEET_DESCRIPTIONS: Dict[str, str] = {
    "National volume": "THE centerpiece — how many transports a year, national -> "
                       "IFT slice, by acuity and emergency/non-emergency. Sourced.",
    "Volume sources": "Every citation behind the funnel, clickable (GOV first).",
    "Demand databases": "The multi-source triangulation — NEDS / NIS / NEMSIS / "
                        "MedPAC / HCRIS / NHAMCS / FAIR Health, each with its "
                        "current figure, data year, and URL.",
    "CMS code analysis": "Ground HCPCS mapped to BLS/ALS/SCT x emergency, with RVUs.",
    "Emergency mix": "Emergent up-transfer vs scheduled step-down / discharge split.",
    "Demand by condition YoY": "Each condition's case volume year over year + CAGR.",
    "Aggregate demand YoY": "The whole transferable case book, blended YoY curve.",
    "Clinical demand engine": "The condition registry: cases -> codes -> volume -> "
                              "growth.",
    "Health-system demand": "HCRIS discharge-driven demand — the health-system "
                            "BUYER view (SNF is not the buyer).",
    "Regional demand": "Facility base by region — hospitals, beds, post-acute.",
    "County demand": "The operator footprint counties with population + demand.",
    "Demographic engine": "The aging wave (age-band CAGRs) that drives IFT demand.",
    "Demand-data inventory": "What demand data we hold, its source, and what's next.",
    "Provenance": "The honesty-basis contract for this demand workbook.",
}


def _contents_sheet(sheets: List[Sheet]) -> Sheet:
    rows: List[List[Any]] = [
        [("Interfacility Transport (IFT) — DEMAND workbook", _H)],
        [("The whole demand side in one download, volume-first. How many "
          "transports a year, by acuity, emergency vs non-emergency, by condition "
          "year over year, by health system, region, and county — every figure "
          "sourced, the honesty basis on every value-bearing cell.")],
        [],
        [("#", _H), ("Sheet", _H), ("What's on it", _H)],
    ]
    for i, s in enumerate(sheets, start=1):
        rows.append([(i, "num"), (s.name, _H),
                     _SHEET_DESCRIPTIONS.get(s.name, "")])
    rows += [
        [],
        [("Where this lives online (click to open)", _H)],
        [("", _H), ("Page", _H), ("What it is", _H)],
        ["", Link("Demand deep-dive", "https://pedesk.app/ift-demand"),
         "National -> subcounty demand, CMS code analysis, YoY condition curves."],
        ["", Link("Health-system demand", "https://pedesk.app/ift-hs-demand"),
         "The HCRIS discharge-driven, health-system-buyer demand view."],
        ["", Link("IFT market study (full pack)", "https://pedesk.app/ift-markets"),
         "The sized TAM/SAM/SOM funnel + the 20-metro deep dive."],
        ["", Link("Download this workbook", "https://pedesk.app/api/ift/demand.xlsx"),
         "This Excel — always the latest build."],
    ]
    return Sheet("Contents", rows, col_widths=[5, 30, 78])


def demand_workbook_xlsx(qs: Optional[Dict[str, List[str]]] = None) -> bytes:
    """Build the separate IFT DEMAND workbook and return .xlsx bytes.

    Volume-first: the National-volume sheet leads, then its sources, the CMS code
    analysis, the emergency mix, the YoY condition curves, and the health-system /
    regional / county demand views, closed by the demand-data inventory and the
    provenance contract. Every sheet degrades to skipped rather than raising, so
    the download always succeeds even offline where a pandas-gated read is dark."""
    builders = [
        _volume_sheet, _volume_sources_sheet, _sources_matrix_sheet,
        _code_analysis_sheet, _emergency_sheet, _condition_yoy_sheet,
        _aggregate_yoy_sheet, _clinical_sheet, _hs_demand_sheet, _regional_sheet,
        _county_sheet, _demographic_sheet, _inventory_sheet, _provenance_sheet,
    ]
    sheets: List[Sheet] = []
    for b in builders:
        s = _safe(b)
        if s is not None:
            sheets.append(s)
    if not sheets:  # never emit an empty workbook
        sheets = [_provenance_sheet()]
    final = [_contents_sheet(sheets)] + sheets
    # Centralized presentation polish (title/banner hierarchy, basis chips, frozen
    # headers) — reuse the market pack's polisher; degrade to as-built if it can't
    # be imported (it lives in the numpy-gated exports neighborhood).
    _polish = None
    try:
        from .ift_excel import _polish_sheet as _polish
    except Exception:  # noqa: BLE001
        _polish = None
    out: List[Sheet] = []
    for s in final:
        if _polish is not None:
            out.append(_safe(lambda s=s: _polish(s), default=s) or s)
        else:
            out.append(s)
    return write_xlsx(out)
