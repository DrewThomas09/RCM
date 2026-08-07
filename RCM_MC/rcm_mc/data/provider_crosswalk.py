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

Two scopes
----------
``scope="hospital"`` is the 6,123-facility HCRIS universe — the only
one with beds, revenue and filing recency on it. ``scope="all"`` adds
the 42,387 nursing homes, home-health agencies, hospices, dialysis
facilities, IRFs and LTCHs from the CMS Compare files, for 48,510 CCNs.
The default stays hospital-only because a caller who did not ask for
eight times the rows should not silently get them.

The chain, and what each link is worth over the full universe:

    CCN  ──►  health system        14,261 of 48,510 (29.4%)
     │        (health_systems.py registry). The average hides an
     │        enormous spread — 89% of dialysis, 8.5% of nursing
     │        homes — so crosswalk_by_class() reports it per class.
     │
     ├──►  county FIPS             46,499 of 48,510 (95.9%)
     │        four independent sources of the same fact, tried in
     │        confidence order and named on the row: Census geocode
     │        (4,325), the county the facility filed (30,836), Care
     │        Compare's county (66), and an unambiguous ZIP (11,272).
     │        The last exists because home health is the one class
     │        CMS publishes with no county column at all.
     │
     ├──►  CBSA / MSA              42,225 of 48,510 (87.0%)
     │        county FIPS -> OMB 2023 delineation, plus a Connecticut
     │        layer: CT replaced counties with planning regions in 2022
     │        and the two bundled files disagree on the vintage, so all
     │        385 CT facilities used to read as rural. cbsa_source says
     │        which path produced the answer, or why there is none —
     │        "outside any cbsa" (real geography) and "no county" (a
     │        real gap) used to look identical.
     │
     ├──►  NUCC taxonomy           every facility
     │        provider class -> the standard code a claim actually
     │        carries (282N00000X and friends)
     │
     ├──►  CMS ownership           46,707 of 48,510 (96.3%)
     │        CMS's observed class, published for every provider
     │        class. Where a facility maps to no system, this is the
     │        only ownership signal there is.
     │
     └──►  NPI                     90 of 48,510 (0.2%)
              matched against the bundled NPPES roster on
              name+state+ZIP5, over both the legal name and every
              d/b/a. Small because that roster is a 20,401-NPI
              ambulance slice, not NPPES; nppes_ingest.py streams the
              full 9GB dissemination file, which this environment
              cannot reach. Two rules keep the 90 trustworthy: exactly
              one NPI may claim a key, and the NPI must describe the
              same kind of provider as the row — see _npi_for.

Public API::

    build_crosswalk(df=None, *, scope=...) -> DataFrame, one row per CCN
    crosswalk_coverage(df=None, *, scope=...) -> [CoverageStat]
    crosswalk_by_class(df=None) -> per-provider-class coverage
    crosswalk_by_cbsa(df=None, *, scope=...) -> the market rollup
    facility_taxonomy(facility_type) -> (code, description)
    cbsa_for_county(county_fips) -> dict | None
    cbsa_for_row(county_fips, state, city) -> (dict, source)
    county_fips_for(ccn, state, county_name, zip_code) -> (fips, source)
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .cms_facility_names import cms_facility, load_cms_facilities
from .health_systems import assign_systems, normalize_name
from .npi_registry import organization_index

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
    "rnhci": ("282J00000X", "Religious Nonmedical Health Care Institution"),
    # Unclassified means unclassified. This used to emit 281P00000X
    # ("Chronic Disease Hospital"), which is a clinical assertion about
    # a facility whose type we could not determine — and every row it
    # ever reached was in fact an acute hospital or an RNHCI, both of
    # which are now typed by their CCN range. Nothing lands here today,
    # and if something does, the honest answer is silence.
    "other": ("", ""),
    # Post-acute and outpatient classes. The key here is CMS's own
    # provider class rather than a CCN range, because the Compare files
    # state the class outright and re-deriving it would only add a way
    # to be wrong.
    "snf": ("314000000X", "Skilled Nursing Facility"),
    "hha": ("251E00000X", "Home Health Agency"),
    "hospice": ("251G00000X", "Hospice Care, Community Based"),
    "dialysis": ("261QE0700X", "Clinic/Center — End-Stage Renal Disease"),
    "irf": ("283X00000X", "Rehabilitation Hospital"),
    "ltch": ("282E00000X", "Long Term Care Hospital"),
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


# ── Connecticut: a county-vintage break, not rural geography ───────
#
# Connecticut replaced its eight counties with nine councils of
# governments as its statistical geography in 2022. The OMB-2023
# delineation bundled here keys exclusively on the planning regions
# (09110-09190); ``county_demographics.csv``, which is where every
# county FIPS on this crosswalk is minted, still carries the legacy
# counties (09001-09015). The two key sets share nothing at all, so
# every Connecticut facility failed the county -> CBSA join and was
# reported as sitting outside every metro area.
#
# That is 385 facilities, 276 of them with a resolved county, and it
# removed 7,554 operating hospital beds and $14.87B of net patient
# revenue from the market view — Yale New Haven (1,306 beds), Hartford
# Hospital (711), Saint Francis, Bridgeport, Danbury, Stamford. Every
# one of those metros is LISTED IN THE SAME FILE that failed to match
# them.
#
# The break is Connecticut's alone. Comparing the two files' FIPS key
# sets state by state, CT is the only state where the intersection is
# empty; every other state's unmatched county is genuinely absent from
# the delineation because it is in no CBSA. (Puerto Rico is a different
# gap: county_demographics carries no PR rows at all, and PR facilities
# therefore never resolve a county to begin with.)
#
# Two tiers resolve it, strongest first:
#
#   1. **Principal city.** The delineation file's own CBSA titles name
#      thirteen Connecticut towns. A facility in Waterbury or Shelton
#      is in Waterbury-Shelton by the file's own words — no judgement,
#      no external table. This tier is what puts Waterbury Hospital and
#      St. Mary's in 47930 rather than in New Haven.
#   2. **Legacy county, dominant region.** Five of the eight legacy
#      counties sit inside one planning region. Three genuinely span
#      two, and for those the dominant region is used and the exception
#      is written down below rather than left for a reader to discover.
#
# What this does NOT do is invent a town-level table. The obvious
# source — the county text the facilities themselves file — turns out
# to be provider-typed and unreliable: eleven towns' filed regions
# disagree with their actual one, and Meriden's own filings disagree
# with each other (six rows say Lower CT River Valley, one says
# Capitol; neither is right). Closing the last twelve rows needs a real
# CT council-of-governments town roster, which this repository does not
# have.

#: Towns the delineation file's own CBSA titles name.
_CT_PRINCIPAL_CITY_CBSA: Dict[str, str] = {
    "BRIDGEPORT": "14860", "STAMFORD": "14860", "DANBURY": "14860",
    "HARTFORD": "25540", "WEST HARTFORD": "25540", "EAST HARTFORD": "25540",
    "NEW HAVEN": "35300",
    "NORWICH": "35980", "NEW LONDON": "35980", "WILLIMANTIC": "35980",
    "PUTNAM": "39480",
    "TORRINGTON": "45860",
    "WATERBURY": "47930", "SHELTON": "47930",
}

#: Legacy county FIPS -> the CBSA covering most of it. The three that
#: span two planning regions carry the facilities the rule misfiles, so
#: the cost is stated rather than hidden:
#:   09001 Fairfield  -> 14860, except SHELTON (caught by tier 1)
#:   09003 Hartford   -> 25540, except BRISTOL (8 facilities, 47930)
#:   09009 New Haven  -> 35300, except WATERBURY (tier 1), MIDDLEBURY
#:                       (3) and DERBY (1), which are 47930
#: Twelve of 276 county-resolved Connecticut rows land in an adjacent
#: metro. The alternative was 385 rows reported as rural.
_CT_LEGACY_COUNTY_CBSA: Dict[str, str] = {
    "09001": "14860",   # Fairfield
    "09003": "25540",   # Hartford
    "09005": "45860",   # Litchfield
    "09007": "25540",   # Middlesex — Lower CT River Valley folds into Hartford
    "09009": "35300",   # New Haven
    "09011": "35980",   # New London
    "09013": "25540",   # Tolland
    "09015": "39480",   # Windham — no dominant region; Putnam by facility count
}

#: Where a CBSA came from, or why there isn't one. A blank cbsa_code
#: meant three different things and said none of them.
CBSA_SOURCE_OMB = "omb 2023"
CBSA_SOURCE_CT_CITY = "ct principal city"
CBSA_SOURCE_CT_COUNTY = "ct legacy county"
CBSA_SOURCE_OUTSIDE = "outside any cbsa"
CBSA_SOURCE_NO_COUNTY = "no county"


def _norm_city(value: Any) -> str:
    """City as the delineation titles spell it.

    HCRIS types a city three ways — "STAMFORD  CT 06904", "GREENWICH,
    CT", "STAMFORD". Strip the trailing state and ZIP so all three key
    the same.
    """
    text = re.sub(r"[^A-Z ]", " ", str(value or "").upper())
    text = re.sub(r"\s+", " ", text).strip()
    return re.sub(r"\s+CT$", "", text).strip()


def cbsa_for_row(county_fips: Any, state: Any = "",
                 city: Any = "") -> Tuple[Dict[str, str], str]:
    """CBSA record plus the source that produced it, or the reason there
    is none. Never returns a bare blank — see :data:`CBSA_SOURCE_OMB`."""
    fips = str(county_fips or "").strip().zfill(5)
    record = _cbsa_by_county().get(fips) if fips and fips != "00000" else None
    if record:
        return record, CBSA_SOURCE_OMB

    if str(state or "").upper().strip() == "CT":
        by_code = {r["cbsa_code"]: r for r in _cbsa_by_county().values()}
        code = _CT_PRINCIPAL_CITY_CBSA.get(_norm_city(city))
        if code and code in by_code:
            return by_code[code], CBSA_SOURCE_CT_CITY
        code = _CT_LEGACY_COUNTY_CBSA.get(fips)
        if code and code in by_code:
            return by_code[code], CBSA_SOURCE_CT_COUNTY

    if not fips or fips == "00000":
        return {}, CBSA_SOURCE_NO_COUNTY
    return {}, CBSA_SOURCE_OUTSIDE


@lru_cache(maxsize=None)
def _fips_lookup(state: str, county_name: str) -> str:
    from .county_demographics import _county_by_name, _norm_county_for

    row = _county_by_name().get((state, _norm_county_for(state, county_name)))
    return str(row.get("county_fips", "")).zfill(5) if row else ""


def _fips_from_county_name(state: Any, county_name: Any) -> str:
    """County FIPS for a (state, county name) pair, or empty.

    Memoized: the universe is 48,510 facilities across ~3,100 counties,
    so all but the first few thousand calls are repeats.
    """
    st = str(state or "").upper().strip()
    name = str(county_name or "").strip()
    if not st or not name or name.lower() == "nan":
        return ""
    return _fips_lookup(st, name)


@lru_cache(maxsize=1)
def _county_by_zip() -> Dict[str, str]:
    """ZIP5 -> county FIPS, learned from the rows that carry both.

    Home-health agencies are the one provider class CMS publishes with
    no county field at all — 12,392 facilities that would otherwise
    have no geography beyond a state. Every other class carries both a
    ZIP and a county, which is 36,000-odd observations of the same
    mapping.

    Only unambiguous ZIPs are kept. A ZIP that straddles a county line
    appears here with two different FIPS and is dropped outright: an
    inferred county that is right most of the time is worse than an
    absent one, because nothing downstream can tell which rows to
    distrust.
    """
    from .health_systems import assign_all

    seen: Dict[str, set] = {}
    frame = assign_all()
    for zip_code, state, county in zip(frame["zip"], frame["state"],
                                       frame["county"], strict=True):
        zip5 = str(zip_code or "").strip()[:5]
        if len(zip5) != 5 or not zip5.isdigit():
            continue
        fips = _fips_from_county_name(state, county)
        if fips:
            seen.setdefault(zip5, set()).add(fips)
    return {z: next(iter(f)) for z, f in seen.items() if len(f) == 1}


def county_fips_for(
    ccn: Any,
    state: Any = "",
    county_name: Any = "",
    zip_code: Any = "",
) -> Tuple[str, str]:
    """Resolve a facility to a county FIPS. Returns ``(fips, source)``.

    Four independent sources for the same fact, tried in confidence
    order, and the source is returned alongside the answer so a caller
    can weight it:

    1. **geocode** — the Census geocoder run against a street address.
       Strongest, but hospital-only.
    2. **cost report** / **provider file** — the county the facility
       itself filed. Not a rounding error: it carries 1,506 hospitals
       the geocode file never had, lifting hospital county coverage
       from 71% to 95%.
    3. **care compare** — CMS's county for the same CCN, which fills
       rows where the filed county was blank.
    4. **zip inferred** — only for the home-health file, which publishes
       no county at all. Learned from the 36,000 rows that carry both a
       ZIP and a county, and only where the ZIP is unambiguous.

    ``("", "")`` when none resolve — mostly Puerto Rico municipios and
    Alaska's renamed boroughs.
    """
    from .hospital_coords import load_hospital_coords

    coord = load_hospital_coords().get(str(ccn or ""))
    if coord is not None and coord.county and coord.state:
        fips = _fips_from_county_name(coord.state, coord.county)
        if fips:
            return fips, "geocode"

    fips = _fips_from_county_name(state, county_name)
    if fips:
        return fips, "cost report"

    cms = cms_facility(ccn)
    if cms is not None:
        fips = _fips_from_county_name(cms.state, cms.county)
        if fips:
            return fips, "care compare"

    zip5 = str(zip_code or "").strip()[:5]
    if len(zip5) == 5 and zip5.isdigit():
        fips = _county_by_zip().get(zip5, "")
        if fips:
            return fips, "zip inferred"

    return "", ""


# ── The crosswalk ──────────────────────────────────────────────────

#: Columns the crosswalk guarantees, in display order. Every derived
#: identifier is followed by the source that produced it — a row whose
#: provenance is invisible is a row nobody can check.
CROSSWALK_COLUMNS: Tuple[str, ...] = (
    "ccn", "name", "street", "city", "state", "zip",
    "provider_class", "provider_class_label",
    "system_id", "system_name", "system_kind", "system_focus", "system_match",
    "chain_name",
    "facility_status", "is_operating", "reports_no_activity",
    "facility_type", "facility_type_label", "taxonomy_code", "taxonomy_desc",
    "is_behavioral",
    "cms_name", "cms_ownership", "cms_hospital_type", "emergency_services",
    "certification_date",
    "npi_taxonomy",
    "county", "county_fips", "county_fips_source",
    "cbsa_code", "cbsa_title", "cbsa_type", "cbsa_central_outlying",
    "cbsa_source",
    "lat", "lon", "geo_match_quality",
    "npi", "npi_source",
    "beds", "net_patient_revenue",
)

#: ``scope="hospital"`` is the 6,123-facility HCRIS universe — the one
#: with beds, revenue and filing recency. ``scope="all"`` adds the
#: 42,387 post-acute and outpatient CCNs, which have none of those and
#: are most of what a health system actually holds.
SCOPE_HOSPITAL = "hospital"
SCOPE_ALL = "all"
CROSSWALK_SCOPES: Tuple[str, ...] = (SCOPE_HOSPITAL, SCOPE_ALL)


#: Columns ``_crosswalk_row`` reads off the assigned frame.
_SOURCE_COLUMNS: Tuple[str, ...] = (
    "ccn", "name", "street", "city", "state", "zip",
    "provider_class", "provider_class_label",
    "system_id", "system_name", "system_kind", "system_focus", "system_match",
    "chain_name", "facility_status", "is_operating", "reports_no_activity",
    "facility_type", "facility_type_label", "is_behavioral", "cms_ownership",
    "certification_date", "county", "beds", "net_patient_revenue",
)


def _records(assigned: pd.DataFrame) -> List[Dict[str, Any]]:
    """Plain dicts, one per facility, without pandas scalar boxing.

    ``DataFrame.to_dict("records")`` boxes every cell through
    ``maybe_box_native`` — tolerable at 6,123 rows, two seconds of pure
    overhead at 48,510. Pulling each column to a list once and zipping
    is the same result for a fraction of the work.
    """
    blank = [""] * len(assigned)
    columns = {c: (assigned[c].tolist() if c in assigned.columns else blank)
               for c in _SOURCE_COLUMNS}
    keys = list(columns)
    return [dict(zip(keys, values, strict=True))
            for values in zip(*columns.values(), strict=True)]


#: How much of a NUCC code identifies the kind of provider. Four
#: characters is the grouping plus the classification letter: every
#: hospital variant shares "282N" (general, critical access, rural,
#: children's), while a rehab hospital is "283X", a SNF "3140", a home
#: health agency "251E". Comparing at this depth keeps a refinement and
#: rejects a different provider.
_TAXONOMY_FAMILY_LEN = 4


def _same_taxonomy_family(left: Any, right: Any) -> bool:
    a, b = str(left or ""), str(right or "")
    if not a or not b:
        return False
    return a[:_TAXONOMY_FAMILY_LEN] == b[:_TAXONOMY_FAMILY_LEN]


def _npi_for(rec: Dict[str, Any], zip5: str, index,
             row_taxonomy: str) -> Tuple[str, str, str]:
    """(npi, source, taxonomy) from the bundled NPPES roster, or blanks.

    Matched on (normalized name, state, ZIP5) against both the legal
    name and every d/b/a. Two rules make the result trustworthy rather
    than merely large:

    1. **Exactly one NPI must claim the key.** Handled in
       :func:`npi_registry.organization_index`.
    2. **The NPI must describe the same kind of provider as the row.**
       277 crosswalk rows match the roster on name+state+ZIP5, and the
       match is real every time — but 187 of them attach the wrong
       NPI, because a hospital's ambulance service, its rehab unit and
       its nursing home all file under the hospital's name at the
       hospital's address. Comparing the NUCC classification family
       (the first four characters) rejects every one of those while
       keeping the refinements that matter: 282NR1301X (Rural Acute
       Care) on a row typed 282N00000X is the same hospital, not a
       different provider.

    ``npi_taxonomy`` rides along on the row so the claim stays
    checkable rather than having to be trusted.
    """
    name = str(rec.get("name", "") or "")
    state = str(rec.get("state", "") or "").upper().strip()
    # HCRIS spells ZIPs three ways — "35957", "35957-", "372051609". The
    # roster is ZIP5, so key on the first five digits rather than on
    # whatever the cost report happened to type.
    key_zip = zip5[:5]
    if not name or not state or len(key_zip) != 5 or not key_zip.isdigit():
        return "", "", ""
    hit = index.get((normalize_name(name), state, key_zip))
    if hit is None:
        return "", "", ""
    npi, taxonomy, basis = hit
    if not _same_taxonomy_family(taxonomy, row_taxonomy):
        return "", "", ""
    return npi, f"nppes {basis}+state+zip5", taxonomy


def _crosswalk_row(rec: Dict[str, Any], coords, care_compare,
                   npi_index) -> Dict[str, Any]:
    """Flatten one assigned facility onto the crosswalk shape."""
    ccn = str(rec.get("ccn", ""))
    coord = coords.get(ccn)
    cms = care_compare.get(ccn)
    zip5 = str(rec.get("zip", "") or "").strip().rstrip("-")
    fips, fips_source = county_fips_for(
        ccn, rec.get("state"), rec.get("county"), zip5)
    cbsa, cbsa_source = cbsa_for_row(fips, rec.get("state"), rec.get("city"))
    code, desc = facility_taxonomy(rec.get("facility_type"))
    npi, npi_source, npi_taxonomy = _npi_for(rec, zip5, npi_index, code)
    return {
        "ccn": ccn,
        "name": rec.get("name", ""),
        "street": rec.get("street", "") or (coord.address if coord else ""),
        "city": rec.get("city", ""),
        "state": rec.get("state", ""),
        "zip": zip5,
        "provider_class": rec.get("provider_class", "") or SCOPE_HOSPITAL,
        "provider_class_label": rec.get("provider_class_label", "") or "Hospital",
        "system_id": rec.get("system_id", ""),
        "system_name": rec.get("system_name", ""),
        "system_kind": rec.get("system_kind", ""),
        "system_focus": rec.get("system_focus", ""),
        "system_match": rec.get("system_match", ""),
        "chain_name": rec.get("chain_name", "") or "",
        "facility_status": rec.get("facility_status", ""),
        "is_operating": bool(rec.get("is_operating")),
        "reports_no_activity": bool(rec.get("reports_no_activity")),
        "facility_type": rec.get("facility_type", ""),
        "facility_type_label": rec.get("facility_type_label", ""),
        "taxonomy_code": code,
        "taxonomy_desc": desc,
        "is_behavioral": bool(rec.get("is_behavioral")),
        # Care Compare's own view of the same facility: the untruncated
        # name, and the ownership class CMS observes rather than the one
        # the registry infers.
        "cms_name": cms.name if cms else "",
        "cms_ownership": cms.ownership if cms else (rec.get("cms_ownership", "") or ""),
        "cms_hospital_type": cms.hospital_type if cms else "",
        "emergency_services": cms.emergency_services if cms else "",
        "certification_date": rec.get("certification_date", "") or "",
        "npi_taxonomy": npi_taxonomy,
        "county": rec.get("county", "") if isinstance(rec.get("county"), str) else "",
        "county_fips": fips,
        "county_fips_source": fips_source,
        "cbsa_code": cbsa.get("cbsa_code", ""),
        "cbsa_title": cbsa.get("cbsa_title", ""),
        "cbsa_type": cbsa.get("cbsa_type", ""),
        "cbsa_central_outlying": cbsa.get("cbsa_central_outlying", ""),
        "cbsa_source": cbsa_source,
        "lat": coord.lat if coord else None,
        "lon": coord.lon if coord else None,
        "geo_match_quality": coord.match_quality if coord else "",
        "npi": npi,
        "npi_source": npi_source,
        "beds": rec.get("beds"),
        "net_patient_revenue": rec.get("net_patient_revenue"),
    }


def build_crosswalk(df: Optional[pd.DataFrame] = None, *,
                    scope: str = SCOPE_HOSPITAL) -> pd.DataFrame:
    """One row per CCN with every identifier we can resolve attached.

    Passing ``df`` always builds over that frame as a hospital universe;
    ``scope`` only applies to the bundled build.
    """
    from .health_systems import assign_all
    from .hospital_coords import load_hospital_coords

    if df is None and scope == SCOPE_ALL:
        assigned = assign_all()
    else:
        assigned = assign_systems(df)
    if assigned.empty:
        return pd.DataFrame(columns=list(CROSSWALK_COLUMNS))

    coords = load_hospital_coords()
    care_compare = load_cms_facilities()
    npi_index = organization_index()
    rows: List[Dict[str, Any]] = [
        _crosswalk_row(rec, coords, care_compare, npi_index)
        for rec in _records(assigned)
    ]
    _resolve_npi_collisions(rows)
    return pd.DataFrame(rows, columns=list(CROSSWALK_COLUMNS))


def _resolve_npi_collisions(rows: List[Dict[str, Any]]) -> None:
    """Strip an NPI that more than one CCN claims, unless one row owns it.

    The name+state+ZIP5 key is unique on the NPPES side but not on ours:
    a hospital and its own hospital-based rehab unit file the SAME name
    at the SAME address under two CCNs, so both match the hospital's
    NPI. Riverside Medical Center IL is 140186 and 14T186; Poudre Valley
    is 060010 and 06T010.

    **On the bundled data this function removes nothing**, and that is
    worth stating rather than leaving a reader to assume it is load
    bearing. Those eight pairs never reach it: the rehab rows are typed
    283X and the NPI is 282N, so ``_same_taxonomy_family`` rejects them
    upstream. What is left here is the case the family check cannot
    see — two rows of the SAME type, at the same name and ZIP, under
    two CCNs. None exist today. The guard stays because an NPI on the
    wrong row is worse than an absent one: a claims join would silently
    attribute one facility's volume to another.

    Where exactly one claimant's own taxonomy matches the NPI's, that
    row keeps it; where the tie does not break, every claimant loses it.
    Exercised directly by its unit test rather than by the universe.
    """
    by_npi: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        if row.get("npi"):
            by_npi.setdefault(row["npi"], []).append(row)

    for claimants in by_npi.values():
        if len(claimants) < 2:
            continue
        owners = [r for r in claimants
                  if r.get("taxonomy_code") == r.get("npi_taxonomy")]
        keep = owners[0] if len(owners) == 1 else None
        for row in claimants:
            if row is keep:
                continue
            row["npi"] = ""
            row["npi_source"] = ""
            row["npi_taxonomy"] = ""


@lru_cache(maxsize=len(CROSSWALK_SCOPES))
def _cached_crosswalk(scope: str) -> pd.DataFrame:
    return build_crosswalk(None, scope=scope)


def get_crosswalk(df: Optional[pd.DataFrame] = None, *,
                  scope: str = SCOPE_HOSPITAL) -> pd.DataFrame:
    """Crosswalk over the bundled universe, memoized; a copy every time."""
    if scope not in CROSSWALK_SCOPES:
        raise ValueError(f"scope must be one of {CROSSWALK_SCOPES}, got {scope!r}")
    if df is None:
        return _cached_crosswalk(scope).copy()
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


def crosswalk_coverage(df: Optional[pd.DataFrame] = None, *,
                       scope: str = SCOPE_HOSPITAL) -> List[CoverageStat]:
    """Fill rate per identifier — the honest scoreboard for this build.

    Ordered worst-covered first, because the point of the scoreboard is
    to show where the crosswalk still can't answer, not to flatter the
    columns that are already complete.
    """
    xw = get_crosswalk(df, scope=scope)
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
                     "geocode file, then the filed county, then Care "
                     "Compare, then an unambiguous ZIP"),
        CoverageStat("CBSA / MSA", filled("cbsa_code"), total,
                     "read cbsa_source before calling a blank a gap: "
                     "'outside any cbsa' is real rural geography, "
                     "'no county' is a genuine miss"),
        CoverageStat("NUCC taxonomy", filled("taxonomy_code"), total,
                     "derived from the CCN range"),
        CoverageStat("Lat / lon", int(xw["lat"].notna().sum()), total,
                     "Census geocoder against CMS addresses"),
        CoverageStat("ZIP", filled("zip"), total, "from the cost report"),
        CoverageStat("CMS ownership", filled("cms_ownership"), total,
                     "observed ownership class, published by CMS for every "
                     "provider class — the only ownership signal an "
                     "unmapped facility has"),
        CoverageStat("NPI", filled("npi"), total,
                     "matched against the bundled NPPES roster on "
                     "name+state+ZIP5; a national fill needs the full "
                     "dissemination file — see nppes_ingest"),
    ]
    stats.sort(key=lambda s: s.pct)
    return stats


_CBSA_ROLLUP_COLUMNS = ["cbsa_code", "cbsa_title", "cbsa_type",
                        "facilities", "hospitals", "beds", "systems", "states"]


def crosswalk_by_cbsa(df: Optional[pd.DataFrame] = None, *,
                      scope: str = SCOPE_HOSPITAL) -> pd.DataFrame:
    """Facilities and beds rolled up to CBSA — the market view.

    A deal team sizes a market by MSA, not by state: "Dallas-Fort
    Worth" is the unit an operator competes in, and a state total
    smears four unrelated markets together.

    ``hospitals`` is counted separately from ``facilities`` because
    beds only exist on the hospital rows. A market's facility count and
    its bed count answer different questions once dialysis stations and
    home-health agencies are in the frame, and collapsing them would
    make bed-per-facility read as a tenth of its real value.
    """
    xw = get_crosswalk(df, scope=scope)
    live = xw[xw["is_operating"] & xw["cbsa_code"].astype(str).str.strip().ne("")]
    if live.empty:
        return pd.DataFrame(columns=_CBSA_ROLLUP_COLUMNS)
    beds = pd.to_numeric(live["beds"], errors="coerce").fillna(0)
    is_hospital = live["provider_class"].astype(str).eq(SCOPE_HOSPITAL)
    grouped = live.assign(_beds=beds.where(is_hospital, 0),
                          _hosp=is_hospital.astype(int)).groupby(
        ["cbsa_code", "cbsa_title", "cbsa_type"], sort=False)
    out = grouped.agg(
        facilities=("ccn", "count"),
        hospitals=("_hosp", "sum"),
        beds=("_beds", "sum"),
        systems=("system_id", lambda s: int(pd.Series(
            [x for x in s if x and x != "_unmapped"]).nunique())),
        states=("state", lambda s: int(pd.Series(list(s)).nunique())),
    ).reset_index()
    return out.sort_values(["beds", "facilities"], ascending=False)


def crosswalk_by_class(df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Coverage per provider class — where the mapping is strong and weak.

    The single "health system" coverage number hides an enormous
    spread: 89% of dialysis facilities resolve to a parent because CMS
    publishes one, against 9% of nursing homes, whose names are local
    and whose operators change hands constantly. One average across
    both would describe neither.
    """
    xw = get_crosswalk(df, scope=SCOPE_ALL)
    if xw.empty:
        return pd.DataFrame(columns=["provider_class", "provider_class_label",
                                     "facilities", "mapped", "mapped_pct",
                                     "with_cbsa", "with_county"])
    frame = xw.assign(
        _mapped=xw["system_id"].ne("_unmapped").astype(int),
        _cbsa=xw["cbsa_code"].astype(str).str.strip().ne("").astype(int),
        _county=xw["county_fips"].astype(str).str.strip().ne("").astype(int),
    )
    out = frame.groupby(["provider_class", "provider_class_label"],
                        as_index=False).agg(
        facilities=("ccn", "count"),
        mapped=("_mapped", "sum"),
        with_cbsa=("_cbsa", "sum"),
        with_county=("_county", "sum"),
    )
    out["mapped_pct"] = out["mapped"] / out["facilities"] * 100.0
    out = out[["provider_class", "provider_class_label", "facilities",
               "mapped", "mapped_pct", "with_cbsa", "with_county"]]
    return out.sort_values("facilities", ascending=False).reset_index(drop=True)


def _clear_cache() -> None:
    """Test hook — drop the memoized crosswalk."""
    _cached_crosswalk.cache_clear()
    _cbsa_by_county.cache_clear()
    _county_by_zip.cache_clear()
    _fips_lookup.cache_clear()
