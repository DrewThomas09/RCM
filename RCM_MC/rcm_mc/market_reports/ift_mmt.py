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
