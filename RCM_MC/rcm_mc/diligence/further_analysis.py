"""Further Analysis — a Tableau-style query + chart engine over the
platform's vendored public datasets.

A partner picks a dataset (CMS / CDC / Census / Labor / Markets / derived),
a focus (e.g. a state for a county-grain set), one or more measures, a
dimension to plot against, a sort and a row cap — and gets a clean,
client-ready chart in any of the CDD chart kit's chart types, exportable to
PNG/SVG. Datasets × focuses × measures × dimensions × chart types × sorting
yields thousands of distinct, real-data views.

Hard rule (same as the rest of the platform): **no synthetic data**. Every
series here is real vendored public data loaded offline — CMS Part D / Open
Payments / ASP, CDC PLACES, Census/County demographics, BLS-based labor
economics, MA penetration, PE transaction multiples, FDA drug shortages, and
the platform's own derived infusion-market scores. Loaders that would need
the network fail closed and are simply not offered here; what is offered
renders without egress.

The engine is intentionally declarative: a ``Dataset`` is metadata + a
``loader`` returning a list of row dicts. ``shape_table`` turns a query into
the ``parse_table``-shaped ``{"headers", "rows"}`` that ``render_cdd_chart``
consumes, scaling each measure into display units and picking a unit suffix.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

# The 51 USPS codes the vendored state datasets cover (50 states + DC).
_STATES: List[str] = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI",
    "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN",
    "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH",
    "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA",
    "WV", "WI", "WY",
]

_STATE_NAMES: Dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut",
    "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida",
    "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky",
    "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}


# --------------------------------------------------------------------------
# Measure formatting. ``fmt`` controls how a raw value is scaled into display
# units and which unit suffix the chart shows. Keeping the scaling here (not
# in each loader) means a loader can return values in their natural units.
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Measure:
    key: str
    label: str
    fmt: str = "num"   # num | usd | usd_m | usd_b | pct | pct100 | x | weeks


_SUFFIX = {
    "num": "", "usd": "", "usd_m": "M", "usd_b": "B",
    "pct": "%", "pct100": "%", "x": "x", "weeks": "w",
}


def _scale(value: Any, fmt: str) -> Optional[float]:
    """Scale a raw value into the display unit for ``fmt`` (None-safe)."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if fmt == "usd_m":
        return v / 1_000_000.0
    if fmt == "usd_b":
        return v / 1_000_000_000.0
    if fmt == "pct":          # value is a 0-1 fraction → show as 0-100
        return v * 100.0
    return v                   # num / usd / pct100 / x / weeks pass through


def measure_suffix(fmt: str) -> str:
    return _SUFFIX.get(fmt, "")


@dataclass
class Dataset:
    id: str
    label: str
    category: str             # CMS | CDC | Census | Labor | Markets | Derived
    source: str               # citation shown on the page
    grain: str                # state | county | category
    dim_key: str              # row field used as the category/x label
    dim_label: str
    measures: List[Measure]
    loader: Callable[[Optional[str]], List[Dict[str, Any]]]
    focus_label: Optional[str] = None
    focus_options: Optional[List[Tuple[str, str]]] = None
    note: str = ""

    def measure(self, key: str) -> Optional[Measure]:
        for m in self.measures:
            if m.key == key:
                return m
        return None


# --------------------------------------------------------------------------
# Loaders — each returns a list of row dicts with ``dim_key`` + measure keys.
# Every loader is offline-safe; rows with missing values are tolerated and
# filtered at shape time. Imports are local so importing this module is cheap
# and a single broken loader never takes down the registry.
# --------------------------------------------------------------------------
def _safe(fn: Callable[[], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    try:
        return fn() or []
    except Exception:
        return []


def _load_state_demographics(_focus: Optional[str]) -> List[Dict[str, Any]]:
    from ..data import county_demographics as cd
    rows: List[Dict[str, Any]] = []
    for st in _STATES:
        try:
            d = cd.demographics_state(st)
        except Exception:
            continue
        if not d:
            continue
        d = dict(d)
        d["state"] = _STATE_NAMES.get(st, st)
        rows.append(d)
    return rows


def _load_county_demographics(focus: Optional[str]) -> List[Dict[str, Any]]:
    from ..data import county_demographics as cd
    st = (focus or "TX").upper()
    try:
        return cd.counties_for_state(st) or []
    except Exception:
        return []


def _load_ma_penetration(_focus: Optional[str]) -> List[Dict[str, Any]]:
    from ..market_intel import ma_penetration as mp
    out: List[Dict[str, Any]] = []
    for s in _safe(mp.list_state_penetration):
        st = getattr(s, "state", None)
        out.append({
            "state": _STATE_NAMES.get(st, st),
            "penetration_pct": getattr(s, "penetration_pct", None),
            "band": getattr(s, "band", ""),
        })
    return out


def _load_cdc_places(_focus: Optional[str]) -> List[Dict[str, Any]]:
    from ..data import cdc_places_agg as ca
    rows: List[Dict[str, Any]] = []
    for st in _STATES:
        try:
            d = ca.places_equity_state(st)
        except Exception:
            continue
        if not d:
            continue
        d = dict(d)
        d["state"] = _STATE_NAMES.get(st, st)
        rows.append(d)
    return rows


def _load_infusion_attractiveness(_focus: Optional[str]) -> List[Dict[str, Any]]:
    from ..diligence import infusion_market as im
    try:
        scan = im.infusion_state_attractiveness()
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for s in scan.get("states", []):
        axes = s.get("axes", {}) or {}
        out.append({
            "name": s.get("name") or s.get("code"),
            "score": s.get("score"),
            "senior_base": axes.get("senior_base"),
            "ma_steerage": axes.get("ma_steerage"),
            "no_con": axes.get("no_con"),
            "density": axes.get("density"),
            "commercial": axes.get("commercial"),
            "seniors": s.get("seniors"),
            "ma_penetration": s.get("ma_penetration"),
            "median_income": s.get("median_income"),
            "pct_rural": s.get("pct_rural"),
        })
    return out


def _load_hcris_state(_focus: Optional[str]) -> List[Dict[str, Any]]:
    from ..data import hcris
    try:
        df = hcris.load_hcris()
    except Exception:
        return []
    try:
        g = df.groupby("state").agg(
            n_hospitals=("ccn", "count"),
            total_beds=("beds", "sum"),
            total_npsr=("net_patient_revenue", "sum"),
            total_opex=("operating_expenses", "sum"),
            total_net_income=("net_income", "sum"),
        ).reset_index()
    except Exception:
        return []
    rows: List[Dict[str, Any]] = []
    for r in g.to_dict("records"):
        st = r.get("state")
        if not st or st not in _STATE_NAMES:
            continue
        npsr = r.get("total_npsr") or 0.0
        ni = r.get("total_net_income") or 0.0
        r["state"] = _STATE_NAMES.get(st, st)
        r["operating_margin"] = (ni / npsr) if npsr else None
        rows.append(r)
    return rows


def _load_partd(_focus: Optional[str]) -> List[Dict[str, Any]]:
    from ..data import partd_drug as pdd
    return _safe(lambda: pdd.top_drugs_by_spend(40))


def _load_open_payments(_focus: Optional[str]) -> List[Dict[str, Any]]:
    from ..data import open_payments as op
    rows = _safe(lambda: op.top_reporting_entities(25))
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append({
            "entity": r.get("AMGPO_Name") or r.get("entity")
            or r.get("name") or "—",
            "total_amount": r.get("total_amount"),
            "transactions": r.get("transactions"),
        })
    return out


def _load_labor(_focus: Optional[str]) -> List[Dict[str, Any]]:
    from ..market_intel import labor_market as lm
    out: List[Dict[str, Any]] = []
    for r in _safe(lm.list_roles):
        out.append({
            "label": getattr(r, "label", ""),
            "median_hourly_usd": getattr(r, "median_hourly_usd", None),
            "wage_yoy_pct": getattr(r, "wage_yoy_pct", None),
            "turnover_pct": getattr(r, "turnover_pct", None),
            "vacancy_pct": getattr(r, "vacancy_pct", None),
            "replacement_weeks": getattr(r, "replacement_weeks", None),
            "fragility_score": (r.fragility_score()
                                if hasattr(r, "fragility_score") else None),
        })
    return out


def _load_multiples(_focus: Optional[str]) -> List[Dict[str, Any]]:
    """All EV/EBITDA transaction-multiple bands, read straight from the
    vendored YAML so every specialty × deal-size band is available."""
    import pathlib
    import yaml  # type: ignore
    from ..market_intel import transaction_multiples as tm
    try:
        p = (pathlib.Path(tm.__file__).parent / "content"
             / "transaction_multiples.yaml")
        y = yaml.safe_load(p.read_text())
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for b in (y.get("bands", []) if isinstance(y, dict) else []):
        spec = str(b.get("specialty", "")).replace("_", " ").title()
        band = str(b.get("deal_size_band", "")).replace("_", " ").title()
        out.append({
            "band": f"{spec} · {band}",
            "p25_ev_ebitda": b.get("p25_ev_ebitda"),
            "p50_ev_ebitda": b.get("p50_ev_ebitda"),
            "p75_ev_ebitda": b.get("p75_ev_ebitda"),
            "sample_size": b.get("sample_size"),
        })
    return out


def _load_drug_shortages(_focus: Optional[str]) -> List[Dict[str, Any]]:
    from ..data import drug_shortage_data as ds
    return _safe(ds.shortages_by_category)


def _load_hcahps(_focus: Optional[str]) -> List[Dict[str, Any]]:
    """CMS HCAHPS patient-experience top-box percentages, one row per state.
    Values are already 0-100 top-box shares (pct100 — no rescale)."""
    from ..data import hcahps_data as hc
    out: List[Dict[str, Any]] = []
    for st in _STATES:
        try:
            d = hc.hcahps_state(st)
        except Exception:
            continue
        if not d:
            continue
        d = dict(d)
        d["state"] = _STATE_NAMES.get(st, st)
        out.append(d)
    return out


def _load_ma_geo(_focus: Optional[str]) -> List[Dict[str, Any]]:
    """CMS Medicare Advantage geographic variation, one row per state:
    enrollment, the demographic drivers of risk adjustment, and headline
    utilization. Percentage fields are 0-1 fractions (scaled at shape time)."""
    from ..data import ma_data as md
    out: List[Dict[str, Any]] = []
    for r in _safe(lambda: md.top_ma_states(60)):
        st = r.get("state")
        if st not in _STATE_NAMES:
            continue
        r = dict(r)
        r["state"] = _STATE_NAMES.get(st, st)
        out.append(r)
    return out


def _load_provider_supply(_focus: Optional[str]) -> List[Dict[str, Any]]:
    """CMS PECOS enrolled-provider counts by provider/supplier type
    (national). Title-cased so the all-caps source labels read cleanly."""
    from ..data import provider_supply as ps
    out: List[Dict[str, Any]] = []
    for r in _safe(lambda: ps.supply_national_by_type(30)):
        pt = r.get("provider_type")
        if not pt:
            continue
        out.append({
            "provider_type": str(pt).title(),
            "enrolled_count": r.get("enrolled_count"),
        })
    return out


def _load_mips(_focus: Optional[str]) -> List[Dict[str, Any]]:
    """CMS MIPS performance-category score distribution (0-100 points)."""
    from ..data import mips_data as mp
    return _safe(mp.mips_category_scores)


def _load_postacute_footprint(_focus: Optional[str]) -> List[Dict[str, Any]]:
    """CMS Care Compare provider counts across the five post-acute verticals,
    aligned to one row per state so a partner can compare facility density of
    SNF / home health / hospice / dialysis / IRF side by side. Counts are
    directly comparable (all integer facility counts); the SNF overall star
    average rides along as a quality reference."""
    from ..data import (snf, home_health as hh, hospice as ho,
                         dialysis as di, irf)

    def _by_state(fn: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
        try:
            return fn() or {}
        except Exception:
            return {}

    snf_s = _by_state(snf.load_snf_summary_by_state)
    hha_s = _by_state(hh.load_home_health_summary_by_state)
    hos_s = _by_state(ho.load_hospice_summary_by_state)
    dia_s = _by_state(di.load_dialysis_summary_by_state)
    irf_s = _by_state(irf.load_irf_summary_by_state)

    out: List[Dict[str, Any]] = []
    for st in _STATES:
        row = {
            "state": _STATE_NAMES.get(st, st),
            "snf_facilities": (snf_s.get(st) or {}).get("facilities"),
            "hha_agencies": (hha_s.get(st) or {}).get("agencies"),
            "hospice_count": (hos_s.get(st) or {}).get("hospices"),
            "dialysis_facilities": (dia_s.get(st) or {}).get("facilities"),
            "irf_facilities": (irf_s.get(st) or {}).get("facilities"),
            "snf_avg_rating": (snf_s.get(st) or {}).get("avg_overall_rating"),
        }
        if any(v is not None for k, v in row.items() if k != "state"):
            out.append(row)
    return out


def _load_mssp_aco_state(_focus: Optional[str]) -> List[Dict[str, Any]]:
    """CMS Medicare Shared Savings Program ACOs operating in each state — a
    read on value-based-care adoption (a multi-state ACO counts in every
    state it serves)."""
    from ..data import mssp_aco_data as m
    out: List[Dict[str, Any]] = []
    for st in _STATES:
        try:
            n = m.acos_for_state(st)
        except Exception:
            continue
        out.append({"state": _STATE_NAMES.get(st, st), "aco_count": n})
    return out


def _load_mssp_track(_focus: Optional[str]) -> List[Dict[str, Any]]:
    """CMS MSSP risk-track distribution — how many ACOs sit in each BASIC
    (upside-only → two-sided) and ENHANCED (full two-sided) track. A direct
    read on downside-risk appetite across the program."""
    from ..data import mssp_aco_data as m
    out: List[Dict[str, Any]] = []
    for r in _safe(m.mssp_track_breakdown):
        tr = r.get("track")
        if not tr:
            continue
        out.append({"track": str(tr).title(), "acos": r.get("acos")})
    return out


def _load_consolidation_state(_focus: Optional[str]) -> List[Dict[str, Any]]:
    """CMS change-of-ownership velocity by state — Medicare-enrolled SNF and
    hospital ownership changes summed across all vintage years. A real
    consolidation / transaction-velocity signal by market."""
    from ..data import snf_chow as sc
    out: List[Dict[str, Any]] = []
    for st in _STATES:
        try:
            snf_n = sc.total_chows_for_state(st)
            hosp_n = sc.total_hospital_chows_for_state(st)
        except Exception:
            continue
        out.append({
            "state": _STATE_NAMES.get(st, st),
            "snf_chows": snf_n,
            "hospital_chows": hosp_n,
            "total_chows": (snf_n or 0) + (hosp_n or 0),
        })
    return out


def _load_consolidation_trend(_focus: Optional[str]) -> List[Dict[str, Any]]:
    """CMS change-of-ownership national time series — SNF vs hospital ownership
    changes per year, the consolidation wave as a trend line."""
    from ..data import snf_chow as sc
    snf = {int(r["year"]): r.get("chow_count")
           for r in _safe(sc.chow_by_year) if r.get("year") is not None}
    hosp = {int(r["year"]): r.get("chow_count")
            for r in _safe(sc.hospital_chow_by_year)
            if r.get("year") is not None}
    out: List[Dict[str, Any]] = []
    for y in sorted(set(snf) | set(hosp)):
        out.append({
            "year": str(y),
            "snf_chows": snf.get(y),
            "hospital_chows": hosp.get(y),
        })
    return out


def _load_hrsa_shortage(_focus: Optional[str]) -> List[Dict[str, Any]]:
    """HRSA primary-care Health Professional Shortage Areas by state — designated
    HPSA count, shortage severity score, and population in shortage. An unmet
    primary-care-demand / market-opportunity signal."""
    from ..data import hrsa_data as h
    out: List[Dict[str, Any]] = []
    for st in _STATES:
        try:
            d = h.hpsa_state(st)
        except Exception:
            continue
        if not d:
            continue
        out.append({
            "state": _STATE_NAMES.get(st, st),
            "designated_pc_hpsas": d.get("designated_pc_hpsas"),
            "median_hpsa_score": d.get("median_hpsa_score"),
            "population_in_shortage": d.get("population_in_shortage"),
        })
    return out


def _load_snf_owners(_focus: Optional[str]) -> List[Dict[str, Any]]:
    """CMS SNF ownership — the largest owner organizations by facility count,
    a direct read on chain consolidation in skilled nursing."""
    from ..data import snf
    out: List[Dict[str, Any]] = []
    for r in _safe(lambda: snf.snf_top_owner_orgs(30)):
        org = r.get("owner_organization")
        if not org:
            continue
        out.append({
            "owner_organization": str(org).title(),
            "facilities_owned": r.get("facilities_owned"),
        })
    return out


# --------------------------------------------------------------------------
# The registry. Order here is the order shown in the dataset dropdown.
# --------------------------------------------------------------------------
_PCT = "pct"        # 0-1 fractions
_P100 = "pct100"    # already 0-100

_DATASETS_LIST: List[Dataset] = [
    Dataset(
        id="state_demographics", label="State demographics (Census/ACS)",
        category="Census",
        source="US Census ACS / County Health Rankings (vendored)",
        grain="state", dim_key="state", dim_label="State",
        measures=[
            Measure("population", "Population", "num"),
            Measure("pct_age_65_plus", "Age 65+", _PCT),
            Measure("median_household_income", "Median HH income", "usd"),
            Measure("child_poverty_rate", "Child poverty", _PCT),
            Measure("uninsured_rate", "Uninsured", _PCT),
            Measure("pct_white_nh", "White (NH)", _PCT),
            Measure("pct_black_nh", "Black (NH)", _PCT),
            Measure("pct_hispanic", "Hispanic", _PCT),
            Measure("pct_rural", "Rural", _PCT),
        ],
        loader=_load_state_demographics,
        note="One row per state (50 + DC).",
    ),
    Dataset(
        id="county_demographics", label="County demographics (by state)",
        category="Census",
        source="US Census ACS / County Health Rankings (vendored)",
        grain="county", dim_key="county_name", dim_label="County",
        measures=[
            Measure("population", "Population", "num"),
            Measure("pct_age_65_plus", "Age 65+", _PCT),
            Measure("median_household_income", "Median HH income", "usd"),
            Measure("child_poverty_rate", "Child poverty", _PCT),
            Measure("uninsured_rate", "Uninsured", _PCT),
            Measure("pct_white_nh", "White (NH)", _PCT),
            Measure("pct_black_nh", "Black (NH)", _PCT),
            Measure("pct_hispanic", "Hispanic", _PCT),
            Measure("pct_rural", "Rural", _PCT),
        ],
        loader=_load_county_demographics,
        focus_label="State",
        focus_options=[(s, _STATE_NAMES[s]) for s in _STATES],
        note="Every county in the chosen state.",
    ),
    Dataset(
        id="ma_penetration", label="Medicare Advantage penetration (state)",
        category="CMS",
        source="KFF / CMS MA enrollment (vendored)",
        grain="state", dim_key="state", dim_label="State",
        measures=[Measure("penetration_pct", "MA penetration", _P100)],
        loader=_load_ma_penetration,
        note="Share of Medicare eligibles in MA, by state.",
    ),
    Dataset(
        id="cdc_places", label="CDC PLACES health equity (state)",
        category="CDC",
        source="CDC PLACES county estimates, state-rolled (vendored)",
        grain="state", dim_key="state", dim_label="State",
        measures=[
            Measure("uninsured_18_64", "Uninsured 18-64", _P100),
            Measure("fair_poor_health", "Fair/poor health", _P100),
            Measure("poor_mental_health", "Poor mental-health days", _P100),
            Measure("poor_physical_health", "Poor physical-health days",
                    _P100),
            Measure("routine_checkup", "Routine checkup", _P100),
            Measure("food_insecurity", "Food insecurity", _P100),
            Measure("snap_participation", "SNAP participation", _P100),
            Measure("utility_shutoff_threat", "Utility-shutoff threat",
                    _P100),
        ],
        loader=_load_cdc_places,
        note="Social-determinant and health-status prevalence by state.",
    ),
    Dataset(
        id="infusion_attractiveness",
        label="Infusion market attractiveness (state)",
        category="Derived",
        source="Platform scan — demographics + MA + CON policy",
        grain="state", dim_key="name", dim_label="State",
        measures=[
            Measure("score", "Attractiveness score", "num"),
            Measure("senior_base", "Senior-base axis", _PCT),
            Measure("ma_steerage", "MA-steerage axis", _PCT),
            Measure("no_con", "No-CON axis", _PCT),
            Measure("density", "Metro-density axis", _PCT),
            Measure("commercial", "Commercial-payer axis", _PCT),
            Measure("seniors", "Seniors (count)", "num"),
            Measure("ma_penetration", "MA penetration", _PCT),
            Measure("median_income", "Median income", "usd"),
            Measure("pct_rural", "Rural", _PCT),
        ],
        loader=_load_infusion_attractiveness,
        note="0-100 composite ranking 51 states for home/AIC infusion.",
    ),
    Dataset(
        id="hcris_state", label="Hospital financials (HCRIS, state roll-up)",
        category="CMS",
        source="CMS HCRIS hospital cost reports (vendored)",
        grain="state", dim_key="state", dim_label="State",
        measures=[
            Measure("n_hospitals", "Hospitals", "num"),
            Measure("total_beds", "Staffed beds", "num"),
            Measure("total_npsr", "Net patient revenue", "usd_b"),
            Measure("total_opex", "Operating expense", "usd_b"),
            Measure("total_net_income", "Net income", "usd_b"),
            Measure("operating_margin", "Operating margin", _PCT),
        ],
        loader=_load_hcris_state,
        note="Cost-report financials aggregated to the state.",
    ),
    Dataset(
        id="partd", label="Part D top drugs (spend & price)",
        category="CMS",
        source="CMS Medicare Part D drug spending (vendored)",
        grain="category", dim_key="brand", dim_label="Drug",
        measures=[
            Measure("spend_2023", "2023 spend", "usd_b"),
            Measure("claims_2023", "2023 claims", "num"),
            Measure("price_per_unit_2023", "Price per unit", "usd"),
            Measure("price_cagr_19_23", "Price CAGR '19-'23", _PCT),
        ],
        loader=_load_partd,
        note="The 40 highest-spend Part D drugs.",
    ),
    Dataset(
        id="open_payments", label="Open Payments top entities",
        category="CMS",
        source="CMS Open Payments (vendored)",
        grain="category", dim_key="entity", dim_label="Manufacturer / GPO",
        measures=[
            Measure("total_amount", "Total payments", "usd_m"),
            Measure("transactions", "Transactions", "num"),
        ],
        loader=_load_open_payments,
        note="Largest industry payers to providers.",
    ),
    Dataset(
        id="labor", label="Healthcare labor economics (roles)",
        category="Labor",
        source="BLS OES / JOLTS-based labor model (vendored)",
        grain="category", dim_key="label", dim_label="Role",
        measures=[
            Measure("median_hourly_usd", "Median hourly", "usd"),
            Measure("wage_yoy_pct", "Wage growth YoY", _P100),
            Measure("turnover_pct", "Turnover", _P100),
            Measure("vacancy_pct", "Vacancy", _P100),
            Measure("replacement_weeks", "Replacement weeks", "weeks"),
            Measure("fragility_score", "Fragility score", "num"),
        ],
        loader=_load_labor,
        note="Wage, turnover and vacancy by clinical/admin role.",
    ),
    Dataset(
        id="multiples", label="PE transaction multiples (EV/EBITDA)",
        category="Markets",
        source="Healthcare M&A comps library (vendored)",
        grain="category", dim_key="band", dim_label="Specialty · size band",
        measures=[
            Measure("p25_ev_ebitda", "EV/EBITDA P25", "x"),
            Measure("p50_ev_ebitda", "EV/EBITDA P50", "x"),
            Measure("p75_ev_ebitda", "EV/EBITDA P75", "x"),
            Measure("sample_size", "Sample size", "num"),
        ],
        loader=_load_multiples,
        note="29 specialty × deal-size comp bands.",
    ),
    Dataset(
        id="drug_shortages", label="FDA drug shortages (by category)",
        category="CMS",
        source="FDA drug shortage database (vendored)",
        grain="category", dim_key="category", dim_label="Therapeutic area",
        measures=[Measure("n", "Active shortages", "num")],
        loader=_load_drug_shortages,
        note="Count of active national shortages per therapeutic area.",
    ),
    Dataset(
        id="hcahps", label="HCAHPS patient experience (state)",
        category="CMS",
        source="CMS Care Compare HCAHPS survey, state top-box (vendored)",
        grain="state", dim_key="state", dim_label="State",
        measures=[
            Measure("overall_rating_9_10", "Overall rating 9-10", _P100),
            Measure("would_definitely_recommend", "Would recommend", _P100),
            Measure("nurse_comm_always", "Nurse communication", _P100),
            Measure("doctor_comm_always", "Doctor communication", _P100),
            Measure("staff_explained_meds_always", "Meds explained", _P100),
            Measure("given_discharge_info", "Discharge info", _P100),
            Measure("room_always_clean", "Room always clean", _P100),
            Measure("always_quiet_night", "Quiet at night", _P100),
        ],
        loader=_load_hcahps,
        note="Official CMS patient-survey top-box shares by state.",
    ),
    Dataset(
        id="ma_geo", label="Medicare Advantage profile (state)",
        category="CMS",
        source="CMS MA geographic variation, 2022 (vendored)",
        grain="state", dim_key="state", dim_label="State",
        measures=[
            Measure("ma_enrollment", "MA enrollment", "num"),
            Measure("dual_eligible_pct", "Dual-eligible", _PCT),
            Measure("avg_age", "Average age", "num"),
            Measure("female_pct", "Female", _PCT),
            Measure("race_white_pct", "White", _PCT),
            Measure("race_black_pct", "Black", _PCT),
            Measure("race_hispanic_pct", "Hispanic", _PCT),
            Measure("ip_stays_per_1000", "Inpatient stays / 1,000", "num"),
            Measure("snf_days_per_1000", "SNF days / 1,000", "num"),
            Measure("er_visits_per_1000", "ER visits / 1,000", "num"),
        ],
        loader=_load_ma_geo,
        note="MA enrollment, risk-adjustment population mix and utilization.",
    ),
    Dataset(
        id="provider_supply", label="Provider supply by type (PECOS)",
        category="CMS",
        source="CMS PECOS enrolled providers, national (vendored)",
        grain="category", dim_key="provider_type", dim_label="Provider type",
        measures=[Measure("enrolled_count", "Enrolled providers", "num")],
        loader=_load_provider_supply,
        note="Medicare-enrolled provider/supplier counts by type.",
    ),
    Dataset(
        id="mips", label="MIPS score distribution (categories)",
        category="CMS",
        source="CMS Quality Payment Program MIPS scores (vendored)",
        grain="category", dim_key="category", dim_label="Performance category",
        measures=[
            Measure("mean", "Mean score", "num"),
            Measure("median", "Median score", "num"),
            Measure("p25", "25th percentile", "num"),
            Measure("p75", "75th percentile", "num"),
            Measure("n", "Clinicians scored", "num"),
        ],
        loader=_load_mips,
        note="MIPS performance-category points (0-100) across clinicians.",
    ),
    Dataset(
        id="postacute_footprint",
        label="Post-acute provider footprint (state)",
        category="CMS",
        source="CMS Care Compare — SNF/HHA/hospice/dialysis/IRF (vendored)",
        grain="state", dim_key="state", dim_label="State",
        measures=[
            Measure("snf_facilities", "Skilled nursing", "num"),
            Measure("hha_agencies", "Home health", "num"),
            Measure("hospice_count", "Hospice", "num"),
            Measure("dialysis_facilities", "Dialysis", "num"),
            Measure("irf_facilities", "Inpatient rehab", "num"),
            Measure("snf_avg_rating", "SNF avg star rating", "num"),
        ],
        loader=_load_postacute_footprint,
        note="Facility counts across the five post-acute verticals, by state.",
    ),
    Dataset(
        id="snf_owners", label="SNF ownership concentration (chains)",
        category="CMS",
        source="CMS SNF ownership data (vendored)",
        grain="category", dim_key="owner_organization",
        dim_label="Owner organization",
        measures=[Measure("facilities_owned", "Facilities owned", "num")],
        loader=_load_snf_owners,
        note="Largest skilled-nursing chains by facility count.",
    ),
    Dataset(
        id="mssp_aco_state", label="ACO footprint by state (MSSP)",
        category="CMS",
        source="CMS Medicare Shared Savings Program ACO directory (vendored)",
        grain="state", dim_key="state", dim_label="State",
        measures=[Measure("aco_count", "ACOs serving state", "num")],
        loader=_load_mssp_aco_state,
        note="Shared Savings ACOs operating in each state (value-based care).",
    ),
    Dataset(
        id="mssp_track", label="ACO risk-track mix (MSSP)",
        category="CMS",
        source="CMS Medicare Shared Savings Program ACO directory (vendored)",
        grain="category", dim_key="track", dim_label="Risk track",
        measures=[Measure("acos", "ACOs in track", "num")],
        loader=_load_mssp_track,
        note="ACO counts by BASIC/ENHANCED risk track — downside-risk appetite.",
    ),
    Dataset(
        id="consolidation_state",
        label="Provider consolidation by state (CHOW)",
        category="CMS",
        source="CMS SNF + hospital change-of-ownership records (vendored)",
        grain="state", dim_key="state", dim_label="State",
        measures=[
            Measure("total_chows", "All ownership changes", "num"),
            Measure("snf_chows", "SNF ownership changes", "num"),
            Measure("hospital_chows", "Hospital ownership changes", "num"),
        ],
        loader=_load_consolidation_state,
        note="Medicare-enrolled ownership changes by state (transaction velocity).",
    ),
    Dataset(
        id="consolidation_trend",
        label="Provider consolidation trend (national, by year)",
        category="CMS",
        source="CMS SNF + hospital change-of-ownership records (vendored)",
        grain="category", dim_key="year", dim_label="Year",
        measures=[
            Measure("snf_chows", "SNF ownership changes", "num"),
            Measure("hospital_chows", "Hospital ownership changes", "num"),
        ],
        loader=_load_consolidation_trend,
        note="National ownership-change counts per year — the consolidation wave.",
    ),
    Dataset(
        id="hrsa_shortage",
        label="Primary-care shortage by state (HRSA HPSA)",
        category="HRSA",
        source="HRSA Health Professional Shortage Areas — primary care (vendored)",
        grain="state", dim_key="state", dim_label="State",
        measures=[
            Measure("designated_pc_hpsas", "Designated HPSAs", "num"),
            Measure("population_in_shortage", "Population in shortage", "num"),
            Measure("median_hpsa_score", "Median HPSA severity score", "num"),
        ],
        loader=_load_hrsa_shortage,
        note="Primary-care shortage designations and underserved population.",
    ),
]

DATASETS: Dict[str, Dataset] = {d.id: d for d in _DATASETS_LIST}

# Chart types that take a single value column (the rest plot many series).
_SINGLE_SERIES_TYPES = {
    "pie", "donut", "funnel", "tornado", "dot", "gauge", "marimekko",
}


def list_datasets() -> List[Dataset]:
    return list(_DATASETS_LIST)


def categories() -> List[str]:
    seen: List[str] = []
    for d in _DATASETS_LIST:
        if d.category not in seen:
            seen.append(d.category)
    return seen


def _row_label(row: Dict[str, Any], dim_key: str) -> str:
    val = row.get(dim_key)
    return "—" if val is None else str(val)


def shape_table(
    dataset: Dataset,
    measure_keys: List[str],
    *,
    focus: Optional[str] = None,
    sort_key: Optional[str] = None,
    ascending: bool = False,
    top_n: int = 15,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Run a query and return ``(table, meta)``.

    ``table`` is ``{"headers", "rows"}`` shaped for ``render_cdd_chart``;
    values are scaled into the display unit for each measure. ``meta`` carries
    the suffix and the resolved measure list so the page can label things.
    """
    valid = [k for k in measure_keys if dataset.measure(k) is not None]
    if not valid:
        valid = [dataset.measures[0].key]
    measures = [dataset.measure(k) for k in valid]

    rows = dataset.loader(focus)
    # Keep rows that have a label and at least one of the selected measures.
    kept: List[Dict[str, Any]] = []
    for r in rows:
        if not any(r.get(k) is not None for k in valid):
            continue
        kept.append(r)

    # Sort. Default: by the first selected measure, descending.
    skey = sort_key if (sort_key in valid or sort_key == "_label") else valid[0]
    if skey == "_label":
        kept.sort(key=lambda r: _row_label(r, dataset.dim_key),
                  reverse=ascending)
    else:
        def _k(r: Dict[str, Any]) -> float:
            v = r.get(skey)
            try:
                return float(v)
            except (TypeError, ValueError):
                return float("-inf") if not ascending else float("inf")
        kept.sort(key=_k, reverse=not ascending)

    top_n = max(1, min(int(top_n), 60))
    kept = kept[:top_n]

    headers = [dataset.dim_label] + [m.label for m in measures]
    out_rows: List[Tuple[str, List[Optional[float]]]] = []
    for r in kept:
        vals = [_scale(r.get(m.key), m.fmt) for m in measures]
        out_rows.append((_row_label(r, dataset.dim_key), vals))

    # The chart shows one unit suffix; use the first measure's.
    suffix = measure_suffix(measures[0].fmt)
    meta = {
        "suffix": suffix,
        "measures": [{"key": m.key, "label": m.label, "fmt": m.fmt}
                     for m in measures],
        "n_rows": len(out_rows),
        "dim_label": dataset.dim_label,
    }
    return {"headers": headers, "rows": out_rows}, meta


def _qs1(qs: Optional[Dict[str, Any]], key: str, default: str = "") -> str:
    if not qs:
        return default
    v = qs.get(key)
    if isinstance(v, list):
        v = v[0] if v else None
    return str(v) if v not in (None, "") else default


def _qsmany(qs: Optional[Dict[str, Any]], key: str) -> List[str]:
    if not qs:
        return []
    v = qs.get(key)
    if v is None:
        return []
    if isinstance(v, list):
        out: List[str] = []
        for item in v:
            out.extend(str(item).split(","))
        return [x for x in (s.strip() for s in out) if x]
    return [x for x in (s.strip() for s in str(v).split(",")) if x]


def resolve_query(qs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Resolve query-string params into a normalized analysis spec, clamped
    to valid datasets/measures/focus. Shared by the page and the JSON API so
    both stay perfectly in sync."""
    ds_id = _qs1(qs, "dataset", _DATASETS_LIST[0].id)
    dataset = DATASETS.get(ds_id) or _DATASETS_LIST[0]

    focus = None
    if dataset.focus_options:
        valid_focus = {v for v, _ in dataset.focus_options}
        focus = _qs1(qs, "focus", dataset.focus_options[0][0])
        if focus not in valid_focus:
            focus = dataset.focus_options[0][0]

    chosen = [k for k in _qsmany(qs, "measures")
              if dataset.measure(k) is not None]
    if not chosen:
        chosen = [dataset.measures[0].key]

    chart_type = _qs1(qs, "type", "bar")
    if chart_type in _SINGLE_SERIES_TYPES:
        chosen = chosen[:1]

    sort_key = _qs1(qs, "sort", chosen[0])
    ascending = _qs1(qs, "asc", "0") in ("1", "true", "yes", "on")
    try:
        top_n = int(_qs1(qs, "top", "15"))
    except ValueError:
        top_n = 15

    table, meta = shape_table(
        dataset, chosen, focus=focus, sort_key=sort_key,
        ascending=ascending, top_n=top_n)

    return {
        "dataset": dataset, "dataset_id": dataset.id, "focus": focus,
        "measures": chosen, "chart_type": chart_type, "sort_key": sort_key,
        "ascending": ascending, "top_n": max(1, min(top_n, 60)),
        "table": table, "meta": meta,
    }


def build_further_analysis(qs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """JSON-API payload: the resolved query + shaped table + the catalog so a
    programmatic caller can discover every dataset/measure available."""
    spec = resolve_query(qs)
    ds = spec["dataset"]
    catalog = [{
        "id": d.id, "label": d.label, "category": d.category,
        "grain": d.grain, "source": d.source, "note": d.note,
        "dimension": d.dim_label,
        "focus_label": d.focus_label,
        "focus_options": d.focus_options,
        "measures": [{"key": m.key, "label": m.label, "fmt": m.fmt}
                     for m in d.measures],
    } for d in _DATASETS_LIST]
    return {
        "selected": {
            "dataset": ds.id, "dataset_label": ds.label,
            "category": ds.category, "source": ds.source,
            "focus": spec["focus"], "measures": spec["measures"],
            "chart_type": spec["chart_type"], "sort_key": spec["sort_key"],
            "ascending": spec["ascending"], "top_n": spec["top_n"],
        },
        "table": {
            "headers": spec["table"]["headers"],
            "rows": [{"label": lbl, "values": vals}
                     for lbl, vals in spec["table"]["rows"]],
        },
        "meta": spec["meta"],
        "catalog": catalog,
    }
