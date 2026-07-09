"""Midwest Medical Transport (MMT) — the county-resolved footprint model.

The IFT study frames MMT (the deep-dive subject, Omaha HQ) at the metro level
(``ift_geo``). This module resolves MMT's footprint down to the **county** grain
and wires every county-level public-data connector to it, so the analysis a
diligence team actually wants — "what does MMT's served territory look like,
county by county, by MSA, across every dataset we can reach" — is real.

MMT's served metros (``ift_geo`` registry read) map to seven OMB Core-Based
Statistical Areas across Nebraska + western Iowa:

  * **Omaha–Council Bluffs, NE-IA MSA** (HQ metro) — 8 counties
  * **Lincoln, NE MSA** — 2 counties
  * **Grand Island, NE MSA** — 3 counties      ┐ the ift_geo "Grand Island /
  * **Kearney, NE μSA** — 2 counties           ├ Kearney" cluster metro
  * **Hastings, NE μSA** — 3 counties          ┘
  * **North Platte, NE μSA** — 2 counties
  * **Columbus, NE μSA** — 2 counties

= 22 counties, ~1.56M people. County → CBSA delineations are OMB 2023
(GOV, cited); county populations are the 2020 Census (GOV); the senior share,
per-capita IFT rates, and the mission model are ILLUSTRATIVE with named bases;
the county-grain connector reads (Census / CDC / CMS / NPPES) degrade-safe —
network-gated offline with an honest fallback, SOURCED once the estate is
ingested (every ``dataset_id`` is registered, and every filter uses the estate's
``__in`` grammar + a real county/FIPS column, verified against the schema).

Design contract mirrors the rest of the IFT spine: frozen dataclasses, pure
functions that DEGRADE and never raise, honesty labels throughout.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# County reference — OMB 2023 CBSA delineations × 2020 Census population.
# `role`: core (principal-city county) / suburban / rural-feeder.
# `senior_share` is ILLUSTRATIVE (tier-based, Census-magnitude) — the SOURCED
# 65+ comes from census_acs_county_profile once ingested.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class MmtCounty:
    name: str
    state: str
    fips: str                # 5-digit county FIPS
    cbsa_code: str
    cbsa_name: str
    metro: str               # the ift_geo MARKETS metro this county rolls to
    role: str                # core | suburban | rural-feeder
    pop_2020: int            # GOV — 2020 Census
    senior_share: float      # ILLUSTRATIVE — 65+ share (tier-based)
    seat: str = ""
    note: str = ""

    @property
    def pop_65_plus(self) -> int:
        return int(round(self.pop_2020 * self.senior_share))


# tier senior-share assumptions (ILLUSTRATIVE, 2020-Census-magnitude): rural
# Nebraska counties skew markedly older than the metro cores.
_S_CORE = 0.145
_S_SUBURB = 0.155
_S_RURAL = 0.205

_C = lambda name, st, fips, code, cbsa, metro, role, pop, seat="", note="": MmtCounty(
    name, st, fips, code, cbsa, metro, role, pop,
    {"core": _S_CORE, "suburban": _S_SUBURB, "rural-feeder": _S_RURAL}[role],
    seat, note)

MMT_COUNTIES: Tuple[MmtCounty, ...] = (
    # ── Omaha–Council Bluffs, NE-IA MSA (36540) — MMT HQ metro ──
    _C("Douglas", "NE", "31055", "36540", "Omaha–Council Bluffs, NE-IA", "Omaha",
       "core", 584526, "Omaha",
       "MMT HQ county; Nebraska Medicine/UNMC + CHI + Methodist + Children's hubs."),
    _C("Sarpy", "NE", "31153", "36540", "Omaha–Council Bluffs, NE-IA", "Omaha",
       "suburban", 190604, "Papillion", "Fastest-growing NE county; CHI Midlands."),
    _C("Pottawattamie", "IA", "19155", "36540", "Omaha–Council Bluffs, NE-IA",
       "Omaha", "suburban", 93206, "Council Bluffs",
       "Iowa side; IA licensure — Methodist Jennie Edmundson, CHI Mercy CB."),
    _C("Cass", "NE", "31025", "36540", "Omaha–Council Bluffs, NE-IA", "Omaha",
       "rural-feeder", 26248, "Plattsmouth"),
    _C("Saunders", "NE", "31155", "36540", "Omaha–Council Bluffs, NE-IA", "Omaha",
       "rural-feeder", 21578, "Wahoo"),
    _C("Washington", "NE", "31177", "36540", "Omaha–Council Bluffs, NE-IA", "Omaha",
       "rural-feeder", 20729, "Blair"),
    _C("Mills", "IA", "19129", "36540", "Omaha–Council Bluffs, NE-IA", "Omaha",
       "rural-feeder", 15109, "Glenwood"),
    _C("Harrison", "IA", "19085", "36540", "Omaha–Council Bluffs, NE-IA", "Omaha",
       "rural-feeder", 14049, "Logan"),
    # ── Lincoln, NE MSA (30700) ──
    _C("Lancaster", "NE", "31109", "30700", "Lincoln, NE", "Lincoln", "core",
       322608, "Lincoln",
       "Bryan Health + CHI St. Elizabeth + Madonna Rehab (IRF/LTCH magnet)."),
    _C("Seward", "NE", "31159", "30700", "Lincoln, NE", "Lincoln", "rural-feeder",
       17609, "Seward"),
    # ── Grand Island, NE MSA (24260) ──
    _C("Hall", "NE", "31079", "24260", "Grand Island, NE", "Grand Island / Kearney",
       "core", 62895, "Grand Island", "CHI St. Francis regional hub."),
    _C("Howard", "NE", "31093", "24260", "Grand Island, NE",
       "Grand Island / Kearney", "rural-feeder", 6417, "St. Paul"),
    _C("Merrick", "NE", "31121", "24260", "Grand Island, NE",
       "Grand Island / Kearney", "rural-feeder", 7547, "Central City"),
    # ── Kearney, NE μSA (28260) ──
    _C("Buffalo", "NE", "31019", "28260", "Kearney, NE", "Grand Island / Kearney",
       "core", 50084, "Kearney", "CHI Good Samaritan + Kearney Regional."),
    _C("Kearney", "NE", "31099", "28260", "Kearney, NE", "Grand Island / Kearney",
       "rural-feeder", 6495, "Minden"),
    # ── Hastings, NE μSA (25580) ──
    _C("Adams", "NE", "31001", "25580", "Hastings, NE", "Grand Island / Kearney",
       "core", 31205, "Hastings", "Mary Lanning Healthcare (independent)."),
    _C("Clay", "NE", "31035", "25580", "Hastings, NE", "Grand Island / Kearney",
       "rural-feeder", 6102, "Clay Center"),
    _C("Webster", "NE", "31181", "25580", "Hastings, NE", "Grand Island / Kearney",
       "rural-feeder", 3462, "Red Cloud"),
    # ── North Platte, NE μSA (35820) ──
    _C("Lincoln", "NE", "31111", "35820", "North Platte, NE", "North Platte",
       "core", 34914, "North Platte", "Great Plains Health (sole regional hub)."),
    _C("Logan", "NE", "31113", "35820", "North Platte, NE", "North Platte",
       "rural-feeder", 763, "Stapleton", "Frontier county — long-leg IFT."),
    # ── Columbus, NE μSA (18100) ──
    _C("Platte", "NE", "31141", "18100", "Columbus, NE", "Columbus (NE)", "core",
       33470, "Columbus", "Columbus Community Hospital (single acute node)."),
    _C("Colfax", "NE", "31037", "18100", "Columbus, NE", "Columbus (NE)",
       "rural-feeder", 10679, "Schuyler", "CHI Schuyler CAH pulls toward CHI."),
)

_CBSA_KIND = {
    "36540": "MSA", "30700": "MSA", "24260": "MSA",
    "28260": "μSA", "25580": "μSA", "35820": "μSA", "18100": "μSA",
}
# CBSA → the ift_geo metro it belongs to (the Grand Island/Kearney cluster spans
# three CBSAs).
_CBSA_METRO = {
    "36540": "Omaha", "30700": "Lincoln", "24260": "Grand Island / Kearney",
    "28260": "Grand Island / Kearney", "25580": "Grand Island / Kearney",
    "35820": "North Platte", "18100": "Columbus (NE)",
}

_POP_SOURCE = "GOV · U.S. Census 2020 Decennial (county population)"
_CBSA_SOURCE = ("GOV · OMB 2023 CBSA delineations (eff. 2023-07-21); "
                "county↔MSA/μSA composition")


# ─────────────────────────────────────────────────────────────────────────────
# National-anchored IFT per-capita rates (ILLUSTRATIVE). US ground IFT ~4.5M
# legs/yr; the 65+ cohort generates the large majority of interfacility volume
# (aging + acuity + post-acute recurrence), so the model splits the rate by age.
# ─────────────────────────────────────────────────────────────────────────────
_RATE_65 = 0.054       # ground-IFT legs / 65+ person / yr (ILLUSTRATIVE)
_RATE_U65 = 0.0049     # ground-IFT legs / under-65 person / yr (ILLUSTRATIVE)
_REV_PER_LEG = 1300.0  # blended all-payer net revenue / IFT leg ($, ILLUSTRATIVE)


@dataclass(frozen=True)
class CountyDemand:
    county: MmtCounty
    pop_65_plus: int
    demand_missions: int          # modeled ground-IFT legs/yr
    demand_dollars: float         # demand_missions × rev/leg
    basis: str = "ILLUSTRATIVE (national-anchored per-capita rates × 2020 pop)"


def county_demand(c: MmtCounty) -> CountyDemand:
    """Modeled ground-IFT demand for one county — an age-split per-capita build
    off the 2020 population. Every rate is ILLUSTRATIVE (named, national-anchored),
    never a filed figure."""
    p65 = c.pop_65_plus
    pu = max(0, c.pop_2020 - p65)
    missions = int(round(p65 * _RATE_65 + pu * _RATE_U65))
    return CountyDemand(county=c, pop_65_plus=p65, demand_missions=missions,
                        demand_dollars=missions * _REV_PER_LEG)


# ─────────────────────────────────────────────────────────────────────────────
# CBSA + footprint roll-ups
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class MmtCbsa:
    code: str
    name: str
    kind: str                # MSA | μSA
    metro: str               # ift_geo metro
    counties: Tuple[MmtCounty, ...]
    pop_2020: int
    pop_65_plus: int
    demand_missions: int
    demand_dollars: float


def footprint_cbsas() -> List[MmtCbsa]:
    """MMT's footprint grouped into its seven CBSAs, biggest first. Never raises."""
    by_code: Dict[str, List[MmtCounty]] = {}
    order: List[str] = []
    for c in MMT_COUNTIES:
        by_code.setdefault(c.cbsa_code, [])
        if c.cbsa_code not in order:
            order.append(c.cbsa_code)
        by_code[c.cbsa_code].append(c)
    out: List[MmtCbsa] = []
    for code in order:
        cs = tuple(by_code[code])
        dems = [county_demand(c) for c in cs]
        out.append(MmtCbsa(
            code=code, name=cs[0].cbsa_name, kind=_CBSA_KIND.get(code, "μSA"),
            metro=_CBSA_METRO.get(code, cs[0].metro), counties=cs,
            pop_2020=sum(c.pop_2020 for c in cs),
            pop_65_plus=sum(c.pop_65_plus for c in cs),
            demand_missions=sum(d.demand_missions for d in dems),
            demand_dollars=sum(d.demand_dollars for d in dems)))
    out.sort(key=lambda b: b.pop_2020, reverse=True)
    return out


@dataclass(frozen=True)
class FootprintSummary:
    n_cbsa: int
    n_msa: int
    n_micro: int
    n_county: int
    n_states: int
    n_metros: int
    pop_2020: int
    pop_65_plus: int
    senior_share: float
    demand_missions: int
    demand_dollars: float
    pop_source: str = _POP_SOURCE
    cbsa_source: str = _CBSA_SOURCE


def footprint_summary() -> FootprintSummary:
    """Footprint totals for a KPI strip / headline. Never raises."""
    cbsas = footprint_cbsas()
    pop = sum(c.pop_2020 for c in MMT_COUNTIES)
    p65 = sum(c.pop_65_plus for c in MMT_COUNTIES)
    dems = [county_demand(c) for c in MMT_COUNTIES]
    return FootprintSummary(
        n_cbsa=len(cbsas),
        n_msa=sum(1 for b in cbsas if b.kind == "MSA"),
        n_micro=sum(1 for b in cbsas if b.kind != "MSA"),
        n_county=len(MMT_COUNTIES),
        n_states=len({c.state for c in MMT_COUNTIES}),
        n_metros=len({c.metro for c in MMT_COUNTIES}),
        pop_2020=pop, pop_65_plus=p65,
        senior_share=(p65 / pop if pop else 0.0),
        demand_missions=sum(d.demand_missions for d in dems),
        demand_dollars=sum(d.demand_dollars for d in dems))


# ─────────────────────────────────────────────────────────────────────────────
# County-grain connector coverage — every public-data hook resolvable to MMT's
# counties, probed degrade-safe. Reuses the estate grammar (aggregate + __in).
# ─────────────────────────────────────────────────────────────────────────────
def _fips_list() -> List[str]:
    return [c.fips for c in MMT_COUNTIES]


def _ne_ia_states() -> List[str]:
    return sorted({c.state for c in MMT_COUNTIES})


def _estate_probe(dataset_id: str, group_by: Any,
                  filters: Optional[Dict[str, Any]] = None,
                  metrics: Optional[List[str]] = None) -> Dict[str, Any]:
    """Degrade-safe estate aggregate (offline → count 0). Never raises."""
    try:
        from ..data_public import connector_estate as ce
        kwargs: Dict[str, Any] = {}
        if metrics:
            kwargs["metrics"] = list(metrics)
        return ce.aggregate(dataset_id, group_by=group_by,
                            filters=filters or None, **kwargs)
    except Exception:  # noqa: BLE001
        return {"count": 0, "rows": []}


@dataclass(frozen=True)
class CountyConnector:
    key: str
    title: str
    connector: str
    dataset_id: str
    grain: str               # what geography it resolves to for MMT
    yields: str              # what it gives per county
    available: bool
    n_rows: int
    status: str
    basis: str               # SOURCED | CONNECTOR
    source_label: str
    fallback_citation: str


# Declarative county-grain probes. Each filter uses a REAL county/FIPS/state
# column (verified against the estate schema) + the `__in` grammar for lists.
_COUNTY_PROBES: Tuple[Dict[str, Any], ...] = (
    dict(key="census_county", title="Census ACS county profile (65+ demand)",
         connector="census_acs", dataset_id="census_acs_county_profile",
         grain="all 22 counties (by fips5)",
         yields="65+ population, total population, median age, uninsured — the "
                "per-county demand base.",
         group_by="fips5", filter_col="fips5",
         metrics=("sum:pop_65_plus", "sum:total_pop"),
         fallback="GOV · U.S. Census ACS 5-year table S0101 (age 65+) by county"),
    dict(key="market_saturation_county",
         title="CMS ambulance market saturation (by county)",
         connector="cms_open_data",
         dataset_id="cms_open_data_market_saturation_state_county",
         grain="all 22 counties (by county_fips)",
         yields="ambulance provider count, FFS user count, penetration %, payment "
                "per county — MMT's competitive supply + fraud-moratorium lens.",
         group_by="county_fips", filter_col="county_fips",
         metrics=("sum:number_of_providers", "sum:number_of_users"),
         fallback="GOV · CMS Market Saturation & Utilization, Ambulance (by county)"),
    dict(key="geo_variation_county",
         title="CMS geographic variation (county utilization)",
         connector="cms_open_data",
         dataset_id="cms_open_data_geo_variation_state_county",
         grain="all 22 counties (by bene_geo_cd = FIPS)",
         yields="per-county Medicare cost/utilization — the spend intensity under "
                "the demand.",
         group_by="bene_geo_cd", filter_col="bene_geo_cd",
         metrics=None,
         fallback="GOV · CMS Geographic Variation Public Use File (state/county)"),
    dict(key="ckd_county",
         title="CDC PLACES CKD prevalence (dialysis-demand)",
         connector="cdc_data", dataset_id="cdc_data_places_county_ckd",
         grain="Nebraska + Iowa counties (by stateabbr)",
         yields="county chronic-kidney-disease prevalence — the recurring "
                "dialysis-transport demand pool.",
         group_by="stateabbr", filter_col="stateabbr",
         filter_vals_states=True, metrics=None,
         fallback="GOV · CDC PLACES county CKD (KIDNEY measure), age-adjusted"),
    dict(key="heart_mortality_county",
         title="CDC heart-disease mortality (county)",
         connector="cdc_data",
         dataset_id="cdc_data_heart_disease_mortality_county",
         grain="county rows (geographiclevel=County)",
         yields="county cardiac mortality — the acute cardiac-transfer severity "
                "layer.",
         group_by="geographiclevel", filter_col=None, metrics=None,
         fallback="GOV · CDC Interactive Atlas of Heart Disease & Stroke (county)"),
    dict(key="hospital_universe_county",
         title="CMS hospital universe (by county)",
         connector="provider_data", dataset_id="provider_data_hospital_general",
         grain="hospitals by state + countyparish",
         yields="the IFT ORIGIN universe per county — hospitals + which have EDs.",
         group_by="state", filter_col="state", filter_vals_states=True,
         metrics=None,
         fallback="GOV · CMS Care Compare Hospital General Information (county)"),
    dict(key="ambulance_suppliers_state",
         title="NPPES ambulance suppliers (MMT states)",
         connector="npi_registry", dataset_id="npi_provider_taxonomy",
         grain="NE + IA (address is state-grain in NPPES)",
         yields="the ambulance-supplier universe MMT competes in — the "
                "fragmentation denominator (NPPES has address at state grain).",
         group_by="state", filter_col=None, metrics=None,
         taxonomy=True,
         fallback="GOV · CMS NPPES provider taxonomy (NUCC §341600000X Ambulance)"),
    dict(key="snf_universe_state",
         title="CMS nursing-home / SNF universe (MMT states)",
         connector="provider_data",
         dataset_id="provider_data_nursing_home_provider_info",
         grain="SNFs by state (NE + IA)",
         yields="the post-acute DESTINATION universe — SNF↔hospital back-transfer "
                "is the recurring routine-IFT book MMT wins.",
         group_by="state", filter_col="state", filter_vals_states=True,
         metrics=None,
         fallback="GOV · CMS Care Compare Nursing Home provider info (by state)"),
    dict(key="dialysis_universe_state",
         title="CMS dialysis-facility universe (MMT states)",
         connector="provider_data",
         dataset_id="provider_data_dialysis_facilities",
         grain="dialysis centers by state (NE + IA)",
         yields="the recurring non-emergent-transport destination pool — "
                "thrice-weekly dialysis runs.",
         group_by="state", filter_col="state", filter_vals_states=True,
         metrics=None,
         fallback="GOV · CMS Care Compare Dialysis Facility file (by state)"),
    dict(key="rural_access_state",
         title="HRSA rural / HPSA designations (MMT states)",
         connector="hrsa_data", dataset_id="hrsa_data_hpsa_primary_care",
         grain="HPSA by state (NE + IA)",
         yields="rural-designation density — the super-rural mileage add-on "
                "economics behind the long-leg corridor.",
         group_by="common_state_abbreviation",
         filter_col="common_state_abbreviation", filter_vals_states=True,
         metrics=None,
         fallback="GOV · HRSA Data Warehouse HPSA/MUA designations (by state); "
                  "Medicare super-rural mileage add-on 42 CFR 414.610(c)(5)"),
)

# NUCC land+air+water ambulance taxonomy family (shared with ift_connectors).
_AMBULANCE_TAXONOMIES = ("341600000X", "3416L0300X", "3416A0800X", "3416S0300X")


def county_connector_coverage() -> List[CountyConnector]:
    """Every county-grain public-data hook for MMT's footprint, probed
    degrade-safe. Offline each is network-gated with an honest fallback; the
    wiring is real (registered dataset, real column, `__in` grammar) and lights
    up on ingest. Never raises."""
    out: List[CountyConnector] = []
    for p in _COUNTY_PROBES:
        filters: Optional[Dict[str, Any]] = None
        col = p.get("filter_col")
        if p.get("taxonomy"):
            filters = {"code__in": list(_AMBULANCE_TAXONOMIES)}
        elif col and p.get("filter_vals_states"):
            filters = {f"{col}__in": _ne_ia_states()}
        elif col:
            filters = {f"{col}__in": _fips_list()}
        payload = _estate_probe(p["dataset_id"], p["group_by"], filters,
                                list(p["metrics"]) if p.get("metrics") else None)
        rows = payload.get("rows") or []
        avail = bool(rows)
        out.append(CountyConnector(
            key=p["key"], title=p["title"], connector=p["connector"],
            dataset_id=p["dataset_id"], grain=p["grain"], yields=p["yields"],
            available=avail, n_rows=len(rows),
            status=("available (SOURCED)" if avail else "network-gated offline"),
            basis=("SOURCED" if avail else "CONNECTOR"),
            source_label=(("SOURCED · " + p["title"]) if avail
                          else p["fallback"]),
            fallback_citation=p["fallback"]))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Clinical demand link — the acute conditions (ICD-10 validated) that drive the
# interfacility volume in MMT's rural-hub-and-spoke geography.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ClinicalDriver:
    condition: str
    family: str
    icd10: str
    transfer_type: str
    codes_valid: int
    codes_total: int


def clinical_drivers(top_n: int = 12) -> List[ClinicalDriver]:
    """The top acute-transfer conditions (by demographic CAGR) with their
    ICD-10-CM validation — the demand engine beneath MMT's missions. Degrades to
    [] if the clinical spine is unavailable. Never raises."""
    try:
        from . import ift_clinical_demand as _cd
        ranked = _cd.growth_ranked() or []
        vc = _cd.validate_codes() or {}
    except Exception:  # noqa: BLE001
        return []
    out: List[ClinicalDriver] = []
    for c in ranked[:top_n]:
        name = getattr(c, "name", "")
        v = vc.get(name, {}) if isinstance(vc, dict) else {}
        ok = v.get("icd10_ok", []) or []
        miss = v.get("icd10_miss", []) or []
        icd = getattr(c, "icd10", None)
        icd_s = ", ".join(icd) if isinstance(icd, (list, tuple)) else str(icd or "")
        out.append(ClinicalDriver(
            condition=name, family=getattr(c, "family", ""),
            icd10=icd_s, transfer_type=getattr(c, "transfer_type", ""),
            codes_valid=len(ok), codes_total=len(ok) + len(miss)))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# MMT positioning per served metro (ties the county model back to ift_geo)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class MmtMetroRead:
    metro: str
    cbsas: Tuple[str, ...]
    n_counties: int
    pop_2020: int
    demand_missions: int
    insource_read: str
    moat_note: str
    competitors: Tuple[str, ...]


def mmt_metro_reads() -> List[MmtMetroRead]:
    """MMT's served metros with the county roll-up + the ift_geo qualitative read
    (insource/moat/competitors), so the county model and the market read agree.
    Never raises."""
    try:
        from . import ift_geo
        geo = {md.name: md for md in ift_geo.MARKETS}
    except Exception:  # noqa: BLE001
        geo = {}
    by_metro: Dict[str, List[MmtCounty]] = {}
    order: List[str] = []
    for c in MMT_COUNTIES:
        if c.metro not in by_metro:
            by_metro[c.metro] = []
            order.append(c.metro)
        by_metro[c.metro].append(c)
    out: List[MmtMetroRead] = []
    for m in order:
        cs = by_metro[m]
        md = geo.get(m)
        ops = tuple(getattr(md, "named_operators", ()) or ()) if md else ()
        # non-MMT operators are the competitive field in that metro
        comp = tuple(o for o in ops if "MMT" not in o and "Midwest Medical" not in o)
        out.append(MmtMetroRead(
            metro=m, cbsas=tuple(sorted({c.cbsa_code for c in cs})),
            n_counties=len(cs), pop_2020=sum(c.pop_2020 for c in cs),
            demand_missions=sum(county_demand(c).demand_missions for c in cs),
            insource_read=getattr(md, "insource_read", "") if md else "",
            moat_note=getattr(md, "moat_note", "") if md else "",
            competitors=comp))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Serviceable market (SOM) — county demand → serviceable share s(m) by the
# metro's insource archetype (reused from ift_analytics, so this model agrees
# with the funnel) → MMT's estimated share of the winnable book → MMT revenue.
# ─────────────────────────────────────────────────────────────────────────────
# MMT's estimated share of the SERVICEABLE (outsourced/contestable) book per
# metro (ILLUSTRATIVE, from the ift_geo competitive reads): MMT-led in Omaha, a
# two-horse race in Lincoln, incumbency contested by AmeriPro/Priority in the
# rural corridor.
_MMT_METRO_SHARE = {
    "Omaha": 0.45,                    # MMT-led adult IFT, shares w/ GMR/AMR
    "Lincoln": 0.40,                  # two-horse (AmeriPro vs MMT)
    "North Platte": 0.30,             # AmeriPro's Priority acquisition captures incumbency
    "Columbus (NE)": 0.35,            # single-hospital, per-contract
    "Grand Island / Kearney": 0.35,   # CHI-steered + AmeriPro corridor roll-up
}
_MMT_SHARE_DEFAULT = 0.35


@dataclass(frozen=True)
class MmtServiceableRow:
    metro: str
    insource_class: str
    demand_missions: int
    serviceable_share: float          # s(m)
    serviceable_missions: int
    mmt_share: float                  # MMT share of the serviceable book
    mmt_missions: int
    mmt_revenue: float


@dataclass(frozen=True)
class MmtServiceable:
    rows: Tuple[MmtServiceableRow, ...]
    total_demand: int
    total_serviceable: int
    mmt_som_missions: int
    mmt_som_dollars: float
    footprint_serviceable_share: float
    note: str = ("SOM = county demand × s(m) [insource archetype, reused from "
                 "ift_analytics] × MMT share of the serviceable book. Demand & "
                 "shares are ILLUSTRATIVE (named); s(m) matches the funnel.")


def mmt_serviceable_model() -> MmtServiceable:
    """MMT's serviceable-obtainable market by metro. Reuses the funnel's s(m) by
    insource archetype so this SOM is consistent with ift_analytics. Never
    raises (degrades to the default shares if ift_geo/analytics are dark)."""
    try:
        from . import ift_analytics as _an, ift_geo as _geo
        s_by_class = getattr(_an, "_SERVICEABLE_SHARE", {})
        s_default = getattr(_an, "_SERVICEABLE_DEFAULT", 0.20)
        cls_by_metro = {md.name: md.insource_class for md in _geo.MARKETS}
    except Exception:  # noqa: BLE001
        s_by_class, s_default, cls_by_metro = {}, 0.20, {}
    rows: List[MmtServiceableRow] = []
    by_metro: Dict[str, int] = {}
    order: List[str] = []
    for c in MMT_COUNTIES:
        if c.metro not in by_metro:
            by_metro[c.metro] = 0
            order.append(c.metro)
        by_metro[c.metro] += county_demand(c).demand_missions
    for m in order:
        demand = by_metro[m]
        cls = cls_by_metro.get(m, "rural-contract-gated")
        s = s_by_class.get(cls, s_default)
        serviceable = int(round(demand * s))
        share = _MMT_METRO_SHARE.get(m, _MMT_SHARE_DEFAULT)
        mmt_miss = int(round(serviceable * share))
        rows.append(MmtServiceableRow(
            metro=m, insource_class=cls, demand_missions=demand,
            serviceable_share=s, serviceable_missions=serviceable,
            mmt_share=share, mmt_missions=mmt_miss,
            mmt_revenue=mmt_miss * _REV_PER_LEG))
    rows.sort(key=lambda r: r.mmt_revenue, reverse=True)
    tot_d = sum(r.demand_missions for r in rows)
    tot_s = sum(r.serviceable_missions for r in rows)
    som_m = sum(r.mmt_missions for r in rows)
    return MmtServiceable(
        rows=tuple(rows), total_demand=tot_d, total_serviceable=tot_s,
        mmt_som_missions=som_m, mmt_som_dollars=som_m * _REV_PER_LEG,
        footprint_serviceable_share=(tot_s / tot_d if tot_d else 0.0))


# ─────────────────────────────────────────────────────────────────────────────
# Operating model — footprint unit economics (ILLUSTRATIVE, GADCS-anchored).
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class OpMetric:
    name: str
    value: str
    basis: str
    detail: str


@dataclass(frozen=True)
class MmtOperatingModel:
    headline: str
    revenue_per_leg: float
    cost_per_leg: float
    contribution_margin_pct: float
    est_units: int
    metrics: Tuple[OpMetric, ...]


def mmt_operating_model() -> MmtOperatingModel:
    """MMT footprint unit economics — the cost structure and the operating levers
    (UHU, deadhead) that separate a dense-metro book from a rural long-leg book.
    Every figure is ILLUSTRATIVE with a named basis (labor share is the GADCS
    anchor). Never raises."""
    rev = _REV_PER_LEG
    # cost structure (ILLUSTRATIVE): labor ~69% of ground cost (GADCS), the rest
    # vehicle/fuel/maintenance + overhead; footprint contribution margin ~20%.
    cost = 1040.0
    labor = round(cost * 0.69, 0)
    vehicle = round(cost * 0.16, 0)
    overhead = round(cost * 0.15, 0)
    cm = (rev - cost) / rev
    som = mmt_serviceable_model()
    # units estimate: mmt legs × ~1.6 crew-hours/leg / (UHU × ~4,380 staffed
    # unit-hours/yr). Rural drags the blended UHU down.
    uhu = 0.38
    est_units = int(round(som.mmt_som_missions * 1.6 / (uhu * 4380))) or 1
    metrics = (
        OpMetric("Net revenue / transport", f"${rev:,.0f}", "ILLUSTRATIVE",
                 "Blended all-payer net revenue per IFT leg."),
        OpMetric("Total cost / transport", f"${cost:,.0f}", "ILLUSTRATIVE",
                 "Fully-loaded; footprint blend of dense-metro + rural long-leg."),
        OpMetric("→ Labor / transport", f"${labor:,.0f}",
                 "ILLUSTRATIVE (GADCS ~69% of ground cost)",
                 "The binding constraint — crew wages + benefits."),
        OpMetric("→ Vehicle / fuel / maint.", f"${vehicle:,.0f}", "ILLUSTRATIVE",
                 "Higher per-leg in the rural corridor (miles)."),
        OpMetric("→ Overhead / dispatch / admin", f"${overhead:,.0f}",
                 "ILLUSTRATIVE", "CAD/AVL, billing, management."),
        OpMetric("Contribution margin", f"{cm*100:.1f}%", "ILLUSTRATIVE",
                 "Thin — the scale + density lever is the value-creation thesis."),
        OpMetric("Unit-hour utilization (UHU)", f"{uhu:.2f}",
                 "ILLUSTRATIVE", "Rural markets drag the blend; the #1 margin lever."),
        OpMetric("Deadhead share", "~32%", "ILLUSTRATIVE",
                 "Long empty return legs on the I-80 corridor — backhaul is the "
                 "prize."),
        OpMetric("Est. staffed units (footprint)", f"~{est_units}",
                 "ILLUSTRATIVE",
                 "MMT SOM legs × ~1.6 crew-hrs / (UHU × ~4,380 staffed unit-hrs)."),
    )
    return MmtOperatingModel(
        headline=(f"~{som.mmt_som_missions:,} MMT SOM legs/yr ≈ "
                  f"${som.mmt_som_dollars/1e6:,.1f}M revenue at a ~{cm*100:.0f}% "
                  "contribution margin — a density/backhaul scale game."),
        revenue_per_leg=rev, cost_per_leg=cost, contribution_margin_pct=cm,
        est_units=est_units, metrics=metrics)


# ─────────────────────────────────────────────────────────────────────────────
# Diligence pack — value-creation levers, risks, and the question list.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class DiligenceItem:
    title: str
    detail: str
    tag: str = ""          # lever category / risk severity


@dataclass(frozen=True)
class MmtDiligence:
    value_levers: Tuple[DiligenceItem, ...]
    risks: Tuple[DiligenceItem, ...]
    questions: Tuple[str, ...]


def mmt_diligence() -> MmtDiligence:
    """MMT-specific value-creation levers, risks, and diligence questions — the
    thesis a buyer underwrites. Analyst framework (FRAMEWORK basis). Never raises."""
    levers = (
        DiligenceItem(
            "I-80 corridor backhaul optimization",
            "The Omaha↔Lincoln↔Grand Island↔Kearney↔North Platte metros sit on a "
            "single interstate spine ~40-90 mi apart; pairing outbound + return "
            "legs cuts the ~32% deadhead and lifts UHU — the single biggest "
            "margin lever.", "Density / routing"),
        DiligenceItem(
            "CHI intra-system transfer-lane lock-in",
            "CHI Health runs a captive statewide network (Omaha ↔ Grand Island ↔ "
            "Kearney ↔ Lincoln); holding first-call on those intra-system lanes is "
            "recurring, high-switching-cost volume.", "Contract / moat"),
        DiligenceItem(
            "Defend vs AmeriPro's roll-up",
            "AmeriPro's acquisition of Priority (North Platte) is a direct "
            "incumbency-capture play; matching local posts + the anchor-hospital "
            "relationship is required to hold the rural corridor.", "Competitive"),
        DiligenceItem(
            "Rate + payer-mix optimization",
            "Commercial pays ~2-4× Medicare; the AIF floors reimbursement growth. "
            "OON leverage + escalators on the routine discharge book are "
            "underpriced levers.", "Reimbursement"),
        DiligenceItem(
            "Dispatch / CAD-AVL technology",
            "Reliable scheduled-transport execution (visibility, ETA, "
            "transfer-center integration) is what separates a first-call partner "
            "from a spot vendor.", "Operations / tech"),
    )
    risks = (
        DiligenceItem(
            "Rural long-leg deadhead economics",
            "Half the footprint is frontier/rural (Logan, Webster, Clay) — long "
            "empty legs + thin volume make UHU structurally low; backhaul is "
            "essential, not optional.", "HIGH"),
        DiligenceItem(
            "Anchor-system vendor steering / insource",
            "CHI steers CHI-preferred vendors and could insource high-acuity CCT; "
            "the winnable book is the routine discharge/SNF/dialysis residual, not "
            "the captive tertiary stream.", "HIGH"),
        DiligenceItem(
            "AmeriPro incumbency capture",
            "A well-capitalized consolidator locking anchor-hospital first-call "
            "(Lincoln, Platte, Buffalo/Dawson/Adams) directly compresses MMT's "
            "serviceable share.", "MEDIUM"),
        DiligenceItem(
            "Single-hospital market fragility (Columbus)",
            "Columbus (NE) is one independent hospital, outbound-dominant — highly "
            "exposed to whichever consolidator locks that single contract.",
            "MEDIUM"),
        DiligenceItem(
            "Reimbursement / AIF + labor inflation",
            "Ground-ambulance rates track the AIF (CPI-U − productivity); labor "
            "(~69% of cost) inflation can outrun it, compressing an already-thin "
            "margin.", "MEDIUM"),
    )
    questions = (
        "What are the contract terms + first-call status with CHI, Bryan Health, "
        "and Great Plains Health transfer centers (exclusivity, term, escalators)?",
        "Actual UHU and deadhead % by metro — how much backhaul headroom exists on "
        "the I-80 corridor?",
        "Payer mix by segment (commercial / Medicare / Medicaid / self-pay) and net "
        "revenue per leg by acuity (BLS / ALS / SCT)?",
        "Post-level economics — how many staffed units per metro, and driver/EMT "
        "retention + wage trajectory vs the AIF?",
        "Competitive share vs AmeriPro/Priority by anchor hospital, and any at-risk "
        "contracts up for renewal?",
        "High-acuity (CCT/SCT) capability + credentialing — can MMT capture the "
        "specialty-transport premium the field under-serves?",
        "IT stack — CAD/AVL, transfer-center integration, billing clean-claim rate "
        "and days-in-AR?",
    )
    return MmtDiligence(value_levers=levers, risks=risks, questions=questions)


# ─────────────────────────────────────────────────────────────────────────────
# Positioning scorecard — MMT vs the competitive field across factors.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ScorecardRow:
    factor: str
    mmt: str
    ameripro: str
    national_ems: str
    municipal: str


def mmt_positioning_scorecard() -> Tuple[ScorecardRow, ...]:
    """MMT vs AmeriPro (scaled regional), a national EMS platform (GMR/AMR), and
    municipal/fire 911 across the factors that decide IFT first-call. Reads are
    analyst knowledge (FRAMEWORK), operator names PUBLIC-WEB. Never raises."""
    return (
        ScorecardRow("Dedicated IFT capacity",
                     "High — dedicated scheduled fleet",
                     "High — dedicated regional",
                     "Low — IFT shares trucks with 911",
                     "Low — 911 mandate first"),
        ScorecardRow("Local density / UHU (footprint)",
                     "High in NE metros (HQ)",
                     "Rising — corridor roll-up",
                     "Thin local dedication",
                     "Jurisdiction-bound"),
        ScorecardRow("Anchor-system first-call",
                     "Strong CHI/Bryan relationships",
                     "Capturing via acquisition",
                     "National contracts (HCA-style)",
                     "Ceded / secondary"),
        ScorecardRow("High-acuity CCT/SCT",
                     "Contestable — a growth lever",
                     "Regional CCT",
                     "Air+ground CCT scale",
                     "Limited"),
        ScorecardRow("Rural long-leg reach",
                     "Local posts + GPH relationship",
                     "Priority acquisition footprint",
                     "Sparse rural dedication",
                     "In-jurisdiction only"),
        ScorecardRow("Capital / scale to consolidate",
                     "Regional — the roll-up prize",
                     "Well-capitalized consolidator",
                     "National capital",
                     "Public budget"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Growth projection — apply the study's three-lever growth bridge (price × volume
# + consolidation) to MMT's SOM to project the revenue trajectory.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ProjectionYear:
    year_offset: int          # 0 = today
    base_revenue: float       # organic market growth (price × volume)
    platform_revenue: float   # market × consolidation (a well-run platform)


@dataclass(frozen=True)
class MmtGrowthProjection:
    available: bool
    base_cagr: float          # market growth (organic)
    platform_cagr: float      # platform growth (market × consolidation)
    years: Tuple[ProjectionYear, ...]
    start_revenue: float
    base_5yr: float
    platform_5yr: float
    headline: str = ""
    basis: str = ""


def mmt_growth_projection(horizon: int = 5) -> MmtGrowthProjection:
    """Project MMT's SOM revenue over ``horizon`` years using the study's growth
    bridge — a base case at organic market growth (price × volume) and a platform
    case at market × consolidation. Growth rates are ILLUSTRATIVE (GOV-AIF-anchored
    price + demographic volume); the start is the modeled SOM. Never raises."""
    som = mmt_serviceable_model()
    start = som.mmt_som_dollars
    base_cagr = platform_cagr = 0.0
    try:
        from . import ift_tracking as _t
        gb = _t.growth_bridge()
        if gb and getattr(gb, "available", False):
            base_cagr = (gb.market_growth_central_pct or 0.0) / 100.0
            platform_cagr = (gb.platform_growth_central_pct or 0.0) / 100.0
    except Exception:  # noqa: BLE001
        pass
    if base_cagr <= 0:                     # degrade to a labelled default
        base_cagr, platform_cagr = 0.062, 0.072
    years = tuple(
        ProjectionYear(
            year_offset=y,
            base_revenue=start * ((1 + base_cagr) ** y),
            platform_revenue=start * ((1 + platform_cagr) ** y))
        for y in range(0, horizon + 1))
    base_5 = years[-1].base_revenue
    plat_5 = years[-1].platform_revenue
    return MmtGrowthProjection(
        available=bool(start > 0), base_cagr=base_cagr,
        platform_cagr=platform_cagr, years=years, start_revenue=start,
        base_5yr=base_5, platform_5yr=plat_5,
        headline=(f"MMT SOM ${start/1e6:,.1f}M → ${base_5/1e6:,.1f}M base "
                  f"({base_cagr*100:.1f}%/yr) / ${plat_5/1e6:,.1f}M platform "
                  f"({platform_cagr*100:.1f}%/yr) over {horizon} yrs"),
        basis=("ILLUSTRATIVE — the study's three-lever bridge: price (GOV AIF-"
               "anchored) × volume (demographic CAGR) = market growth; × "
               "consolidation = platform growth. Applied to the modeled SOM."))


# ─────────────────────────────────────────────────────────────────────────────
# SWOT — MMT's structured strategic read, tied to the county footprint.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class MmtSwot:
    strengths: Tuple[str, ...]
    weaknesses: Tuple[str, ...]
    opportunities: Tuple[str, ...]
    threats: Tuple[str, ...]


def mmt_swot() -> MmtSwot:
    """MMT's SWOT — analyst framework tied to the footprint model. Never raises."""
    return MmtSwot(
        strengths=(
            "Omaha-HQ home density — the highest-UHU metro in-state (best deadhead "
            "economics) and the CHI / Methodist / Nebraska Medicine transfer-center "
            "relationships.",
            "Dedicated scheduled-IFT posture (not 911-shared trucks), so reliability "
            "on the routine discharge book is a genuine differentiator.",
            "Statewide corridor presence across all five NE metros on the I-80 spine "
            "— a backhaul-friendly, hard-to-replicate network.",
            "CHI intra-system lanes (Omaha↔Grand Island↔Kearney↔Lincoln) are "
            "recurring, high-switching-cost captive-adjacent volume.",
        ),
        weaknesses=(
            "Thin contribution margin (~20%) — the model only works with high UHU + "
            "backhaul discipline.",
            "Half the footprint is rural/frontier (Logan, Webster, Clay) with "
            "structurally low utilization and long empty legs.",
            "Contested first-call vs AmeriPro in Lincoln and the western corridor — "
            "no single-vendor lock in most metros.",
            "High-acuity CCT/SCT capability is a growth area, not yet a moat — the "
            "specialty-transport premium is under-captured.",
        ),
        opportunities=(
            "Backhaul / corridor routing optimization to lift UHU and cut the ~32% "
            "deadhead — the biggest margin lever.",
            "Roll up the fragmented rural corridor before AmeriPro does — Priority "
            "(North Platte) shows the consolidation is live.",
            "Add CCT/SCT capability to capture the high-acuity, higher-$ transports "
            "the demographic wave is growing fastest.",
            "Aging demand tailwind — the 65+ cohort (the IFT over-indexer) grows "
            "through 2035 across the footprint.",
        ),
        threats=(
            "AmeriPro's incumbency-capture roll-up compressing MMT's serviceable "
            "share metro by metro.",
            "Anchor-system vendor steering or insourcing (CHI could take high-acuity "
            "CCT in-house).",
            "Reimbursement risk — AIF-capped rate growth vs labor inflation (~69% of "
            "cost) squeezing an already-thin margin.",
            "Single-hospital market fragility (Columbus) and any anchor-hospital "
            "ownership change (e.g. a system M&A) redirecting transfer volume.",
        ))


# ─────────────────────────────────────────────────────────────────────────────
# County opportunity ranking — where MMT should focus. Each county's contestable
# IFT book (demand × s(m) by its metro archetype), split into MMT's current book
# vs the headroom winnable from competitors.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class CountyOpportunity:
    rank: int
    name: str
    state: str
    fips: str
    metro: str
    role: str
    demand_missions: int
    serviceable_share: float          # s(m) of the metro
    serviceable_missions: int         # the contestable book in this county
    mmt_share: float
    mmt_current_revenue: float        # serviceable × mmt_share × $/leg
    headroom_revenue: float           # serviceable × (1-mmt_share) × $/leg
    opportunity_revenue: float        # total contestable $ (the focus size)


def mmt_county_opportunity() -> List[CountyOpportunity]:
    """Rank MMT's 22 counties by contestable IFT opportunity — the size of the
    outsourced book (county demand × the metro's s(m)) split into MMT's current
    revenue and the headroom still winnable from competitors. Reuses the metro
    s(m) / MMT-share from the serviceable model so the two agree. Never raises."""
    sm = mmt_serviceable_model()
    by_metro = {r.metro: (r.serviceable_share, r.mmt_share) for r in sm.rows}
    out: List[CountyOpportunity] = []
    tmp: List[CountyOpportunity] = []
    for c in MMT_COUNTIES:
        s, share = by_metro.get(c.metro, (0.20, _MMT_SHARE_DEFAULT))
        demand = county_demand(c).demand_missions
        serviceable = int(round(demand * s))
        opp = serviceable * _REV_PER_LEG
        tmp.append(CountyOpportunity(
            rank=0, name=c.name, state=c.state, fips=c.fips, metro=c.metro,
            role=c.role, demand_missions=demand, serviceable_share=s,
            serviceable_missions=serviceable, mmt_share=share,
            mmt_current_revenue=serviceable * share * _REV_PER_LEG,
            headroom_revenue=serviceable * (1 - share) * _REV_PER_LEG,
            opportunity_revenue=opp))
    tmp.sort(key=lambda o: o.opportunity_revenue, reverse=True)
    for i, o in enumerate(tmp, start=1):
        out.append(CountyOpportunity(
            rank=i, name=o.name, state=o.state, fips=o.fips, metro=o.metro,
            role=o.role, demand_missions=o.demand_missions,
            serviceable_share=o.serviceable_share,
            serviceable_missions=o.serviceable_missions, mmt_share=o.mmt_share,
            mmt_current_revenue=o.mmt_current_revenue,
            headroom_revenue=o.headroom_revenue,
            opportunity_revenue=o.opportunity_revenue))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Anchor-system account map — the transfer-center "accounts" that generate MMT's
# volume, and the go-to-market play for each. Systems/facilities are PUBLIC-WEB.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class AnchorAccount:
    system: str
    tier: str                         # captive-network | regional-hub | independent
    metros: Tuple[str, ...]
    insource_posture: str
    mmt_strategy: str
    risk: str


def mmt_anchor_accounts() -> Tuple[AnchorAccount, ...]:
    """MMT's key health-system transfer-center accounts + the account strategy.
    Systems/facilities are PUBLIC-WEB knowledge; the strategy/risk reads are
    analyst framework. Never raises."""
    return (
        AnchorAccount(
            system="CHI Health (CommonSpirit)",
            tier="captive-network",
            metros=("Omaha", "Grand Island / Kearney", "Lincoln",
                    "Columbus (NE)"),
            insource_posture="Runs a captive STATEWIDE intra-system network "
                "(Bergan/CUMC ↔ St. Francis GI ↔ Good Samaritan Kearney ↔ "
                "St. Elizabeth Lincoln); steers CHI-preferred vendors.",
            mmt_strategy="The #1 account — win first-call on the CHI "
                "intra-system lanes (recurring, high-switching-cost). "
                "Land-and-expand from Omaha across the corridor.",
            risk="CHI could insource high-acuity CCT or standardize on a single "
                "national vendor — the biggest single-account concentration risk."),
        AnchorAccount(
            system="Bryan Health",
            tier="regional-hub",
            metros=("Lincoln",),
            insource_posture="Bryan Medical Center + a ~30-CAH referral network "
                "funnels transfers INBOUND; hospital IFT outsourced.",
            mmt_strategy="Hold Bryan's transfer-center first-call to capture BOTH "
                "the inbound CAH funnel AND the Madonna acute→rehab lane — "
                "compounding volume.",
            risk="A two-horse race with AmeriPro in Lincoln — the contract is "
                "contestable at renewal."),
        AnchorAccount(
            system="Nebraska Medicine / UNMC",
            tier="regional-hub",
            metros=("Omaha",),
            insource_posture="Academic Level I / transplant quaternary hub; "
                "peds/neonatal CCT insourced at Children's next door.",
            mmt_strategy="Win the adult quaternary UP-transfer and routine "
                "discharge book; the high-acuity/peds stream is walled off.",
            risk="Academic centers may build captive CCT; volume is "
                "high-acuity-skewed (capability bar)."),
        AnchorAccount(
            system="Nebraska Methodist Health System",
            tier="regional-hub",
            metros=("Omaha",),
            insource_posture="Independent Omaha system; hospital IFT outsourced "
                "to privates.",
            mmt_strategy="Second Omaha anchor — diversify beyond CHI; win the "
                "discharge/SNF back-transfer book.",
            risk="Contested with GMR/AMR in metro Omaha."),
        AnchorAccount(
            system="Great Plains Health",
            tier="regional-hub",
            metros=("North Platte",),
            insource_posture="Sole west-central NE regional hub; brands the air "
                "program ('LifeNet'), outsources ground IFT.",
            mmt_strategy="Own the GPH ground relationship + local posts — geography "
                "is the moat (long legs, thin volume).",
            risk="AmeriPro's Priority acquisition is a direct incumbency-capture "
                "play on this exact account."),
        AnchorAccount(
            system="Mary Lanning Healthcare",
            tier="independent",
            metros=("Grand Island / Kearney",),
            insource_posture="Independent Hastings hospital; contracts IFT "
                "per-relationship.",
            mmt_strategy="Win the independent (non-CHI) discharge book in the "
                "Hastings cluster — per-contract, relationship-driven.",
            risk="Small standalone account; fragmented contracting vs for-profit "
                "entrants."),
        AnchorAccount(
            system="Columbus Community Hospital",
            tier="independent",
            metros=("Columbus (NE)",),
            insource_posture="Single independent acute node; outbound-dominant "
                "(tertiary cases sent to Omaha/Lincoln).",
            mmt_strategy="Win first-call + backhaul the Columbus→Omaha/Lincoln "
                "corridor lane against interstate volume.",
            risk="LOW structural moat — one hospital; whoever locks the single "
                "contract holds the market."),
    )
