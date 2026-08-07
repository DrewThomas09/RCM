"""Provider identifier crosswalk — one row per facility, every ID attached.

Why this module exists
----------------------
``health_systems.py`` answers ownership: which system runs a CCN. But a
CCN on its own doesn't join to anything else a deal team uses. Market
sizing is done by MSA, network adequacy by county, specialty screens by
taxonomy, and claims work by NPI — and each of those lives behind a
different identifier, in a different file, keyed differently.

This is the spine that ties them together: **one row per CCN carrying
every identifier we can resolve**, each with the source that produced
it. A row is only as good as its provenance, so every derived column
has a ``*_source`` sibling; a partner can always see whether a county
came from the geocode file or from the cost report, and whether a CBSA
is real or absent because the county genuinely sits outside one.

The chain, and what each link is worth on the bundled data:

    CCN  ──►  health system        1,987 of 6,001 operating (33%)
     │        (health_systems.py registry)
     │
     ├──►  county FIPS             5,831 of 6,123 (95.2%)
     │        geocode file first (4,325), cost-report county
     │        second (1,506) — two independent sources of the same
     │        fact, and the second is what lifts this from 71% to 95%
     │
     ├──►  CBSA / MSA              4,720 of 6,123 (77.1%)
     │        county FIPS -> OMB 2023 delineation. The 1,111
     │        facilities with a FIPS but no CBSA are NOT a gap: rural
     │        counties sit outside every metro and micro area by
     │        definition, and calling that "missing" would invent a
     │        data-quality problem where there is geography.
     │
     ├──►  NUCC taxonomy           every facility
     │        CCN-range facility type -> the standard code a claim
     │        actually carries (282N00000X and friends)
     │
     └──►  NPI                     0 until an NPPES file is present
              see nppes_ingest.py — the linkage is built, the bulk
              source is a 9GB monthly file this environment cannot
              currently reach.

Public API::

    build_crosswalk(df=None)  -> DataFrame, one row per CCN
    crosswalk_coverage(df=None) -> {identifier: CoverageStat}
    facility_taxonomy(facility_type) -> (code, description)
    cbsa_for_county(county_fips) -> dict | None
    county_fips_for(ccn, state, county_name) -> (fips, source)
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .cms_facility_names import cms_facility, load_cms_facilities
from .health_systems import assign_systems

_CBSA_CSV = (Path(__file__).resolve().parent / "vendor" / "cbsa_crosswalk"
             / "cbsa_county_crosswalk.csv")


# ── Facility type → NUCC taxonomy ──────────────────────────────────
#
# The CCN range tells us what kind of facility this is; NUCC codes are
# what a claim, an NPPES record and a payer contract actually carry.
# Mapping between them is the difference between "we know it's a psych
# hospital" and "we can join it to anything else in the industry".
#
# Codes are the NUCC Health Care Provider Taxonomy hospital branch
# (level 282/283). Where CMS's bed-class notion is coarser than NUCC's,
# the mapping picks the parent code rather than guessing a child.

NUCC_BY_FACILITY_TYPE: Dict[str, Tuple[str, str]] = {
    "general": ("282N00000X", "General Acute Care Hospital"),
    "critical_access": ("282NC0060X", "Critical Access Hospital"),
    "psychiatric": ("283Q00000X", "Psychiatric Hospital"),
    "rehab": ("283X00000X", "Rehabilitation Hospital"),
    "ltach": ("282E00000X", "Long Term Care Hospital"),
    "children": ("282NC2000X", "Children's Hospital"),
    "other": ("281P00000X", "Chronic Disease Hospital"),
}


def facility_taxonomy(facility_type: Any) -> Tuple[str, str]:
    """NUCC code + description for a CCN-range facility type."""
    return NUCC_BY_FACILITY_TYPE.get(
        str(facility_type or ""), ("", ""))


# ── County FIPS + CBSA ─────────────────────────────────────────────


@lru_cache(maxsize=1)
def _cbsa_by_county() -> Dict[str, Dict[str, str]]:
    """county FIPS -> CBSA record, from the OMB 2023 delineation file."""
    out: Dict[str, Dict[str, str]] = {}
    if not _CBSA_CSV.exists():
        return out
    with _CBSA_CSV.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            fips = str(row.get("county_fips") or "").strip().zfill(5)
            if not fips:
                continue
            out[fips] = {
                "cbsa_code": str(row.get("cbsa_code") or "").strip(),
                "cbsa_title": str(row.get("cbsa_title") or "").strip(),
                "cbsa_type": str(row.get("area_type") or "").strip(),
                "cbsa_central_outlying": str(row.get("central_outlying") or "").strip(),
            }
    return out


def cbsa_for_county(county_fips: Any) -> Optional[Dict[str, str]]:
    """CBSA record for a county, or ``None`` when the county sits outside
    every metro and micro area — which is a real answer, not a miss."""
    fips = str(county_fips or "").strip().zfill(5)
    return _cbsa_by_county().get(fips) if fips and fips != "00000" else None


def county_fips_for(
    ccn: Any,
    state: Any = "",
    county_name: Any = "",
) -> Tuple[str, str]:
    """Resolve a facility to a county FIPS. Returns ``(fips, source)``.

    Two independent sources for the same fact, tried in confidence
    order. The geocode file is preferred — its county came from the
    Census geocoder against a street address. The cost report's own
    county field is the fallback, and it is not a rounding error: it
    carries 1,506 facilities the geocode file never had, lifting county
    coverage from 71% to 95%. ``("", "")`` when neither resolves, which
    is mostly Puerto Rico municipios, Alaska's renamed boroughs, and
    cost reports that left the county blank.
    """
    from .county_demographics import _county_by_name, _norm_county
    from .hospital_coords import load_hospital_coords

    index = _county_by_name()

    coord = load_hospital_coords().get(str(ccn or ""))
    if coord is not None and coord.county and coord.state:
        row = index.get((str(coord.state).upper(), _norm_county(coord.county)))
        if row:
            return str(row.get("county_fips", "")).zfill(5), "geocode"

    st = str(state or "").upper().strip()
    name = str(county_name or "").strip()
    if st and name and name.lower() != "nan":
        row = index.get((st, _norm_county(name)))
        if row:
            return str(row.get("county_fips", "")).zfill(5), "cost report"

    # Third source: Care Compare's own county, which fills rows where the
    # cost report left the field blank entirely.
    cms = cms_facility(ccn)
    if cms is not None and cms.county and cms.state:
        row = index.get((cms.state, _norm_county(cms.county)))
        if row:
            return str(row.get("county_fips", "")).zfill(5), "care compare"

    return "", ""


# ── The crosswalk ──────────────────────────────────────────────────

#: Columns the crosswalk guarantees, in display order. Every derived
#: identifier is followed by the source that produced it — a row whose
#: provenance is invisible is a row nobody can check.
CROSSWALK_COLUMNS: Tuple[str, ...] = (
    "ccn", "name", "street", "city", "state", "zip",
    "system_id", "system_name", "system_kind", "system_focus", "system_match",
    "facility_status", "is_operating", "reports_no_activity",
    "facility_type", "facility_type_label", "taxonomy_code", "taxonomy_desc",
    "is_behavioral",
    "cms_name", "cms_ownership", "cms_hospital_type", "emergency_services",
    "county", "county_fips", "county_fips_source",
    "cbsa_code", "cbsa_title", "cbsa_type", "cbsa_central_outlying",
    "lat", "lon", "geo_match_quality",
    "npi", "npi_source",
    "beds", "net_patient_revenue",
)


def build_crosswalk(df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """One row per CCN with every identifier we can resolve attached."""
    from .hospital_coords import load_hospital_coords

    assigned = assign_systems(df)
    if assigned.empty:
        return pd.DataFrame(columns=list(CROSSWALK_COLUMNS))

    coords = load_hospital_coords()
    care_compare = load_cms_facilities()
    rows: List[Dict[str, Any]] = []
    for rec in assigned.to_dict("records"):
        ccn = str(rec.get("ccn", ""))
        coord = coords.get(ccn)
        cms = care_compare.get(ccn)
        fips, fips_source = county_fips_for(ccn, rec.get("state"), rec.get("county"))
        cbsa = cbsa_for_county(fips) or {}
        code, desc = facility_taxonomy(rec.get("facility_type"))
        rows.append({
            "ccn": ccn,
            "name": rec.get("name", ""),
            "street": rec.get("street", "") or (coord.address if coord else ""),
            "city": rec.get("city", ""),
            "state": rec.get("state", ""),
            "zip": (rec.get("zip", "") or "").strip().rstrip("-"),
            "system_id": rec.get("system_id", ""),
            "system_name": rec.get("system_name", ""),
            "system_kind": rec.get("system_kind", ""),
            "system_focus": rec.get("system_focus", ""),
            "system_match": rec.get("system_match", ""),
            "facility_status": rec.get("facility_status", ""),
            "is_operating": bool(rec.get("is_operating")),
            "reports_no_activity": bool(rec.get("reports_no_activity")),
            "facility_type": rec.get("facility_type", ""),
            "facility_type_label": rec.get("facility_type_label", ""),
            "taxonomy_code": code,
            "taxonomy_desc": desc,
            "is_behavioral": bool(rec.get("is_behavioral")),
            # Care Compare's own view of the same facility: the
            # untruncated name, and the ownership class CMS observes
            # rather than the one the registry infers.
            "cms_name": cms.name if cms else "",
            "cms_ownership": cms.ownership if cms else "",
            "cms_hospital_type": cms.hospital_type if cms else "",
            "emergency_services": cms.emergency_services if cms else "",
            "county": rec.get("county", "") if isinstance(rec.get("county"), str) else "",
            "county_fips": fips,
            "county_fips_source": fips_source,
            "cbsa_code": cbsa.get("cbsa_code", ""),
            "cbsa_title": cbsa.get("cbsa_title", ""),
            "cbsa_type": cbsa.get("cbsa_type", ""),
            "cbsa_central_outlying": cbsa.get("cbsa_central_outlying", ""),
            "lat": coord.lat if coord else None,
            "lon": coord.lon if coord else None,
            "geo_match_quality": coord.match_quality if coord else "",
            # Populated by nppes_ingest when an NPPES extract is present.
            "npi": "",
            "npi_source": "",
            "beds": rec.get("beds"),
            "net_patient_revenue": rec.get("net_patient_revenue"),
        })
    return pd.DataFrame(rows, columns=list(CROSSWALK_COLUMNS))


@lru_cache(maxsize=1)
def _cached_crosswalk() -> pd.DataFrame:
    return build_crosswalk(None)


def get_crosswalk(df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Crosswalk over the bundled universe, memoized; a copy every time."""
    if df is None:
        return _cached_crosswalk().copy()
    return build_crosswalk(df)


# ── Coverage ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class CoverageStat:
    """How much of the universe carries one identifier."""

    identifier: str
    resolved: int
    total: int
    note: str = ""

    @property
    def pct(self) -> float:
        return (self.resolved / self.total * 100.0) if self.total else 0.0


def crosswalk_coverage(df: Optional[pd.DataFrame] = None) -> List[CoverageStat]:
    """Fill rate per identifier — the honest scoreboard for this build.

    Ordered worst-covered first, because the point of the scoreboard is
    to show where the crosswalk still can't answer, not to flatter the
    columns that are already complete.
    """
    xw = get_crosswalk(df)
    total = len(xw)
    if not total:
        return []

    def filled(col: str) -> int:
        if col not in xw.columns:
            return 0
        series = xw[col]
        return int(series.astype(str).str.strip().ne("").sum())

    stats = [
        CoverageStat("CCN", total, total, "the key — every row has one"),
        CoverageStat("Health system", int((xw["system_id"] != "_unmapped").sum()),
                     total, "name-matched against the curated registry"),
        CoverageStat("County FIPS", filled("county_fips"), total,
                     "geocode file, then the cost report's own county"),
        CoverageStat("CBSA / MSA", filled("cbsa_code"), total,
                     "counties outside every metro and micro area have none "
                     "by definition — not a gap"),
        CoverageStat("NUCC taxonomy", filled("taxonomy_code"), total,
                     "derived from the CCN range"),
        CoverageStat("Lat / lon", int(xw["lat"].notna().sum()), total,
                     "Census geocoder against CMS addresses"),
        CoverageStat("ZIP", filled("zip"), total, "from the cost report"),
        CoverageStat("CMS ownership", filled("cms_ownership"), total,
                     "observed ownership class from Care Compare — the only "
                     "ownership signal an unmapped facility has"),
        CoverageStat("NPI", filled("npi"), total,
                     "requires an NPPES extract — see nppes_ingest"),
    ]
    stats.sort(key=lambda s: s.pct)
    return stats


def crosswalk_by_cbsa(df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Facilities and beds rolled up to CBSA — the market view.

    A deal team sizes a market by MSA, not by state: "Dallas-Fort
    Worth" is the unit an operator competes in, and a state total
    smears four unrelated markets together.
    """
    xw = get_crosswalk(df)
    live = xw[xw["is_operating"] & xw["cbsa_code"].astype(str).str.strip().ne("")]
    if live.empty:
        return pd.DataFrame(columns=["cbsa_code", "cbsa_title", "cbsa_type",
                                     "facilities", "beds", "systems", "states"])
    beds = pd.to_numeric(live["beds"], errors="coerce").fillna(0)
    grouped = live.assign(_beds=beds).groupby(
        ["cbsa_code", "cbsa_title", "cbsa_type"], sort=False)
    out = grouped.agg(
        facilities=("ccn", "count"),
        beds=("_beds", "sum"),
        systems=("system_id", lambda s: int(pd.Series(
            [x for x in s if x and x != "_unmapped"]).nunique())),
        states=("state", lambda s: int(pd.Series(list(s)).nunique())),
    ).reset_index()
    return out.sort_values(["beds", "facilities"], ascending=False)


def _clear_cache() -> None:
    """Test hook — drop the memoized crosswalk."""
    _cached_crosswalk.cache_clear()
    _cbsa_by_county.cache_clear()
