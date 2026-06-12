"""Texas infusion geography — county-level patient-to-clinic proximity.

The referral question an AIC (ambulatory infusion center) platform turns
on: infusion referrals convert on CONVENIENCE — a patient offered q2-week
biologic maintenance picks the chair they can reach. So the diligence
read is "how far is the average target patient from the nearest infusion
access point, county by county", and where that distance is long despite
real demand, that's AIC whitespace.

There is no public AIC census (freestanding suites bill as physician
offices, POS 11 — invisible in facility files). Geography is therefore
built the honest way, from what IS verifiable, and every number carries
its evidence class:

REAL (exact, vendored public data):
  * 254 Texas county demographic rows — population, 65+ share, rural
    share, uninsured — ACS-derived via County Health Rankings
    (``data/vendor/county_demographics``).
  * 376 geocoded Texas hospitals — CMS Hospital General Information
    addresses geocoded via the US Census Geocoder
    (``data/hospital_coords.csv``). Filtered by CCN convention to the
    307 general-acute access points (STAC suffix 0001-0899 + CAH
    1300-1399): every short-term acute / critical-access hospital
    operates outpatient infusion or chemo chairs — the HOPD incumbent an
    AIC pulls referrals from, and the only site-of-care whose locations
    are public. Psych/rehab/LTCH CCNs are excluded (no infusion).
  * County → CBSA metro/micro membership
    (``data/vendor/cbsa_crosswalk``).
  * Real great-circle (haversine) nearest-neighbor spacing between
    in-county facilities — exact arithmetic on the geocoded points.

MODELED (documented formula on real inputs — labeled on every row):
  * Expected patient → nearest-access-point distance per county. Two
    modes:
      - **gazetteer mode** — when ``data/vendor/county_gazetteer/``
        exists (built by ``scripts/ingest_county_gazetteer.py`` from the
        Census Gazetteer: county internal-point lat/lon + land area),
        the cross-county term is the EXACT haversine from the county's
        population point to the nearest geocoded facility.
      - **model mode** (no gazetteer vendored; the offline default) —
        the standard spatial-access approximation. For patients uniform
        over land area A (sq mi) with n facilities, the expected
        distance to the nearest facility is ~0.5*sqrt(A/n) [E[d] =
        1/(2*sqrt(density)) for random facility placement]. The urban
        share of the county (1 - pct_rural, real ACS) is instead
        assigned half the county's REAL nearest-neighbor facility
        spacing — urban patients and facilities co-locate. Counties with
        no in-county facility get the own-county traverse plus one
        median-county hop: 0.5*sqrt(A_own) + 0.5*sqrt(A_median).
  * County land areas: explicit Census TIGER values for the counties
    that dominate the weighted result (the major-metro counties and the
    outsized West Texas counties), 909 sq mi — the Texas median, a
    legacy of ~30-mile county platting — for the remainder. The
    gazetteer ingest replaces ALL of these with exact values.

The headline statistic — the demand-weighted mean distance — is then
sum(county patients x county E[d]) / sum(patients): an auditable chain
where every multiplicand is either public data or a stated formula.

Sub-county granularity, honestly: the within-county urban/rural split
(real ACS) is what drives the distance model below county level; the
four-metro member-county ("suburb") drilldowns live in
``texas_infusion.build_texas_metro_deepdive``. Census-tract prevalence
(CDC PLACES) is NOT vendored at county/tract level — run
``scripts/ingest_cdc_places.py`` on a network-enabled machine to add it;
the page marks that column DATA REQUIRED until then.

Known coverage limit (stated on the page): the vendored geocode file
carries 376 of roughly 640 CMS-listed Texas hospitals (rows whose
geocode failed were dropped at ingest — e.g. Midland Memorial is
absent). Supply is therefore UNDERCOUNTED and modeled distances are
conservative (overstated); re-running
``scripts/ingest_hospital_coords`` style geocoding tightens them.
"""
from __future__ import annotations

import functools
import math
from pathlib import Path
from typing import Any

_DATA = Path(__file__).resolve().parent.parent / "data"
_GAZETTEER = _DATA / "vendor" / "county_gazetteer" / "county_gazetteer.csv"

# ── Sourced constants ───────────────────────────────────────────────

#: Census TIGER land area (sq mi) for the Texas counties that dominate
#: the demand-weighted distance (major-metro counties) or deviate far
#: from the platting norm (the big West Texas counties). Everything not
#: listed uses TX_MEDIAN_LAND_SQMI. ``scripts/ingest_county_gazetteer.py``
#: replaces this whole table with the exact Census Gazetteer file.
TX_COUNTY_LAND_SQMI: dict[str, float] = {
    # Major metro counties (top of the demand weighting)
    "HARRIS": 1_703, "DALLAS": 871, "TARRANT": 864, "BEXAR": 1_240,
    "TRAVIS": 990, "COLLIN": 841, "DENTON": 878, "HIDALGO": 1_571,
    "EL PASO": 1_013, "FORT BEND": 861, "MONTGOMERY": 1_042,
    "WILLIAMSON": 1_118, "CAMERON": 891, "NUECES": 838, "BELL": 1_051,
    "GALVESTON": 378, "LUBBOCK": 895, "WEBB": 3_361, "MCLENNAN": 1_037,
    "SMITH": 921, "BRAZORIA": 1_358, "JEFFERSON": 876, "BRAZOS": 585,
    "ELLIS": 935, "JOHNSON": 724, "GUADALUPE": 711, "COMAL": 559,
    "PARKER": 902, "RANDALL": 914, "POTTER": 902, "GRAYSON": 933,
    "HAYS": 678, "MIDLAND": 900, "ECTOR": 901, "TAYLOR": 916,
    "WICHITA": 628, "GREGG": 274, "TOM GREEN": 1_522, "BOWIE": 885,
    "HUNT": 841, "KAUFMAN": 781, "ROCKWALL": 127, "VICTORIA": 882,
    # Outsized West Texas counties (the long-distance tail)
    "BREWSTER": 6_184, "PECOS": 4_764, "HUDSPETH": 4_571,
    "PRESIDIO": 3_855, "CULBERSON": 3_813, "VAL VERDE": 3_134,
    "CROCKETT": 2_807, "TERRELL": 2_358, "REEVES": 2_635,
    "EDWARDS": 2_120, "JEFF DAVIS": 2_265, "KENEDY": 1_458,
    "SUTTON": 1_454, "UPTON": 1_242, "IRION": 1_052,
}

#: Median Texas county land area (sq mi), Census TIGER — most Texas
#: counties were platted roughly 30 miles square so a resident could
#: reach the county seat in a day's ride; the distribution is tight
#: around this median outside West Texas.
TX_MEDIAN_LAND_SQMI = 909.0

#: Random-placement nearest-facility coefficient: for facilities placed
#: independently of patients at density λ per sq mi, E[nearest distance]
#: = 1/(2·sqrt(λ)) — the standard spatial-access result. Conservative
#: (urban co-location shortens it; the urban term below handles that).
_RANDOM_PLACEMENT_K = 0.5

_EARTH_R_MI = 3_958.8


def _haversine_mi(lat1: float, lon1: float,
                  lat2: float, lon2: float) -> float:
    """Great-circle distance in miles — exact arithmetic, no model."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = (math.sin(dp / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return 2 * _EARTH_R_MI * math.asin(math.sqrt(a))


# ── Real inputs ─────────────────────────────────────────────────────

@functools.lru_cache(maxsize=1)
def tx_access_points() -> list[dict[str, Any]]:
    """The 307 geocoded Texas general-acute access points (STAC + CAH by
    CCN convention) — name, county, real lat/lon. REAL."""
    import pandas as pd
    df = pd.read_csv(_DATA / "hospital_coords.csv",
                     dtype={"ccn": str, "zip": str})
    tx = df[(df["state"] == "TX") & df["lat"].notna()].copy()
    suffix = pd.to_numeric(tx["ccn"].str[-4:], errors="coerce")
    acute = tx[((suffix >= 1) & (suffix <= 899))
               | ((suffix >= 1300) & (suffix <= 1399))]
    return [
        {"ccn": r.ccn, "name": r.facility_name,
         "county": _norm_county(str(r.county or "")),
         "city": r.city, "zip": r.zip,
         "lat": float(r.lat), "lon": float(r.lon),
         "kind": "CAH" if 1300 <= int(r.ccn[-4:]) <= 1399 else "STAC"}
        for r in acute.itertuples(index=False)
    ]


@functools.lru_cache(maxsize=1)
def _gazetteer() -> dict[str, dict[str, float]]:
    """county_fips → {lat, lon, land_sqmi} from the vendored Census
    Gazetteer aggregate, when present. Empty offline (model mode)."""
    if not _GAZETTEER.exists():
        return {}
    import pandas as pd
    df = pd.read_csv(_GAZETTEER, dtype={"county_fips": str})
    return {
        r.county_fips: {"lat": float(r.lat), "lon": float(r.lon),
                        "land_sqmi": float(r.land_sqmi)}
        for r in df.itertuples(index=False)
    }


def geo_mode() -> str:
    """'gazetteer' when the exact Census county points are vendored,
    else 'model'. The page states which mode produced the numbers."""
    return "gazetteer" if _gazetteer() else "model"


def _county_land_sqmi(name_upper: str, fips: str) -> tuple[float, str]:
    """(land area sq mi, evidence class). Gazetteer exact > explicit
    TIGER constant > state-median default."""
    g = _gazetteer().get(fips)
    if g:
        return g["land_sqmi"], "REAL"
    table = {k.replace(" ", ""): v for k, v in TX_COUNTY_LAND_SQMI.items()}
    if name_upper in table:
        return float(table[name_upper]), "REAL"
    return TX_MEDIAN_LAND_SQMI, "DEFAULT"


def _nearest_nn_mi(points: list[dict[str, Any]]) -> float | None:
    """Mean nearest-neighbor distance among a county's facilities —
    exact haversine; None below 2 points."""
    if len(points) < 2:
        return None
    total = 0.0
    for i, p in enumerate(points):
        best = min(_haversine_mi(p["lat"], p["lon"], q["lat"], q["lon"])
                   for j, q in enumerate(points) if j != i)
        total += best
    return total / len(points)


def _nearest_facility_mi(lat: float, lon: float,
                         points: list[dict[str, Any]]) -> float:
    return min(_haversine_mi(lat, lon, p["lat"], p["lon"])
               for p in points)


# ── The county universe ─────────────────────────────────────────────

def _norm_county(name: str) -> str:
    """Match key for county names across files: the CMS coords carry
    legacy spaced spellings ('MC LENNAN', 'DE WITT') where the ACS file
    has 'McLennan County' — uppercase and strip ALL whitespace so both
    sides meet."""
    return (name or "").upper().replace(" COUNTY", "").replace(" ", "")


@functools.lru_cache(maxsize=1)
def tx_county_universe() -> list[dict[str, Any]]:
    """All 254 Texas counties: real demographics + CBSA membership +
    real facility counts + the distance model. One row per county;
    every modeled field names its evidence class."""
    import pandas as pd

    from ..data.county_demographics import _county as _county_df
    from .texas_infusion import (
        US_INFUSION_PATIENTS,
        US_POPULATION_2024,
    )

    demo = _county_df()
    tx = demo[demo["state"] == "TX"].copy()

    cw = pd.read_csv(
        _DATA / "vendor" / "cbsa_crosswalk" / "cbsa_county_crosswalk.csv",
        dtype=str)
    cw = cw[cw["county_fips"].str.startswith("48")]
    cbsa_by_fips = {r.county_fips: r for r in cw.itertuples(index=False)}

    pts = tx_access_points()
    pts_by_county: dict[str, list[dict[str, Any]]] = {}
    for p in pts:
        pts_by_county.setdefault(p["county"], []).append(p)

    # CBSAs that contain at least one access point — a member county
    # with no in-county site still has metro spillover access (Randall
    # County patients use Potter County's Amarillo hospitals).
    fips_by_norm = {
        _norm_county(r.county_name): str(r.county_fips)
        for r in tx.itertuples(index=False)}
    cbsas_with_sites = set()
    for cname in pts_by_county:
        cb = cbsa_by_fips.get(fips_by_norm.get(cname, ""))
        if cb is not None:
            cbsas_with_sites.add(cb.cbsa_code)

    tx_pop = float(tx["population"].sum())
    tx_patients = US_INFUSION_PATIENTS * tx_pop / US_POPULATION_2024
    tx_seniors = float(
        (tx["population"] * tx["pct_age_65_plus"]).sum())

    # Computed urban fallback for single-facility counties: half the
    # median REAL nearest-neighbor spacing across multi-facility metro
    # counties — derived from the geocoded points, not invented.
    metro_nns = [
        nn for c, ps in pts_by_county.items()
        if (nn := _nearest_nn_mi(ps)) is not None
    ]
    metro_nns.sort()
    urban_fallback_mi = (
        metro_nns[len(metro_nns) // 2] / 2.0 if metro_nns else 3.0)

    rows: list[dict[str, Any]] = []
    for r in tx.itertuples(index=False):
        fips = str(r.county_fips)
        name_u = _norm_county(r.county_name)
        pop = float(r.population or 0)
        s65 = float(r.pct_age_65_plus or 0)
        rural = min(1.0, max(0.0, float(r.pct_rural or 0)))
        urban = 1.0 - rural
        seniors = pop * s65

        # Demand — same 60/40 senior/population apportionment the
        # verified metro breakdown uses (texas_metro_breakdown).
        senior_share = seniors / tx_seniors if tx_seniors else 0.0
        pop_share = pop / tx_pop if tx_pop else 0.0
        patients = tx_patients * (0.60 * senior_share + 0.40 * pop_share)

        cps = pts_by_county.get(name_u, [])
        n = len(cps)
        area, area_class = _county_land_sqmi(name_u, fips)
        nn_real = _nearest_nn_mi(cps)

        cb = cbsa_by_fips.get(fips)
        spillover = (n == 0 and cb is not None
                     and cb.cbsa_code in cbsas_with_sites)
        gaz = _gazetteer().get(fips)
        if gaz and n == 0:
            # Exact: county population point → nearest facility anywhere.
            dist = _nearest_facility_mi(gaz["lat"], gaz["lon"], pts)
            dist_class, tier = "REAL", "NO_IN_COUNTY"
        elif n == 0 and spillover:
            # Same-CBSA spillover: patients cross one county line into
            # the metro's facility cluster — own-county traverse plus
            # the computed urban spacing, not a median-county hop.
            dist = (_RANDOM_PLACEMENT_K * math.sqrt(area)
                    + urban_fallback_mi)
            dist_class, tier = "MODELED", "NO_IN_COUNTY"
        elif n == 0:
            # Own-county traverse + one median-county hop. MODELED.
            dist = (_RANDOM_PLACEMENT_K * math.sqrt(area)
                    + _RANDOM_PLACEMENT_K * math.sqrt(TX_MEDIAN_LAND_SQMI))
            dist_class, tier = "MODELED", "NO_IN_COUNTY"
        else:
            rural_term = _RANDOM_PLACEMENT_K * math.sqrt(area / n)
            urban_term = (nn_real / 2.0 if nn_real is not None
                          else urban_fallback_mi)
            dist = urban * urban_term + rural * rural_term
            dist_class = "MODELED"
            tier = "MULTI_SITE" if n >= 2 else "SINGLE_SITE"

        rows.append({
            "county_fips": fips,
            "county": str(r.county_name).replace(" County", ""),
            "population": round(pop),
            "seniors_65_plus": round(seniors),
            "pct_age_65_plus": s65,
            "pct_rural": rural,
            "uninsured_rate": float(r.uninsured_rate or 0),
            "median_household_income": float(
                r.median_household_income or 0),
            "cbsa_title": (cb.cbsa_title if cb else None),
            "metro_class": (
                "Metro" if cb and cb.area_type == "Metropolitan"
                else "Micropolitan" if cb else "Non-core (rural)"),
            "infusion_patients": round(patients),
            "patients_per_100k": round(patients / pop * 100_000, 1)
            if pop else 0.0,
            "access_points": n,
            "access_tier": tier,
            "metro_spillover": spillover,
            "facility_nn_mi": round(nn_real, 1)
            if nn_real is not None else None,
            "land_sqmi": round(area),
            "land_evidence": area_class,
            "expected_distance_mi": round(dist, 1),
            "distance_evidence": dist_class,
        })
    rows.sort(key=lambda x: -x["infusion_patients"])
    return rows


# ── Rollups ─────────────────────────────────────────────────────────

def _weighted_distance(rows: list[dict[str, Any]]) -> float:
    demand = sum(r["infusion_patients"] for r in rows)
    if not demand:
        return 0.0
    return round(sum(r["infusion_patients"] * r["expected_distance_mi"]
                     for r in rows) / demand, 1)


def proximity_summary() -> dict[str, Any]:
    """The headline read: statewide demand-weighted patient → nearest-
    access-point distance, the within-10-miles share, and the
    access-tier split. Sums recompute from the county rows."""
    rows = tx_county_universe()
    demand = sum(r["infusion_patients"] for r in rows)
    within10 = sum(r["infusion_patients"] for r in rows
                   if r["expected_distance_mi"] <= 10.0)
    no_access = [r for r in rows if r["access_tier"] == "NO_IN_COUNTY"]
    tiers = {}
    for tier in ("MULTI_SITE", "SINGLE_SITE", "NO_IN_COUNTY"):
        sub = [r for r in rows if r["access_tier"] == tier]
        tiers[tier] = {
            "counties": len(sub),
            "population": sum(r["population"] for r in sub),
            "infusion_patients": sum(r["infusion_patients"] for r in sub),
            "weighted_distance_mi": _weighted_distance(sub),
        }
    return {
        "counties": len(rows),
        "population": sum(r["population"] for r in rows),
        "infusion_patients": demand,
        "access_points": sum(r["access_points"] for r in rows),
        "weighted_distance_mi": _weighted_distance(rows),
        "pct_patients_within_10mi": round(
            within10 / demand * 100, 1) if demand else 0.0,
        "no_access_counties": len(no_access),
        "no_access_population": sum(r["population"] for r in no_access),
        "geo_mode": geo_mode(),
        "tiers": tiers,
    }


def proximity_by_group(key: str) -> list[dict[str, Any]]:
    """Demand-weighted distance rolled up by a grouping column —
    'metro_class', 'cbsa_title', or 'access_tier'. Each group recomputes
    from its member counties (auditable against the full table)."""
    rows = tx_county_universe()
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        g = r.get(key) or ("No CBSA" if key == "cbsa_title" else "—")
        groups.setdefault(str(g), []).append(r)
    out = []
    for g, sub in groups.items():
        out.append({
            "group": g,
            "counties": len(sub),
            "population": sum(r["population"] for r in sub),
            "seniors_65_plus": sum(r["seniors_65_plus"] for r in sub),
            "infusion_patients": sum(
                r["infusion_patients"] for r in sub),
            "access_points": sum(r["access_points"] for r in sub),
            "weighted_distance_mi": _weighted_distance(sub),
        })
    out.sort(key=lambda x: -x["infusion_patients"])
    return out


def aic_whitespace(top: int = 25) -> list[dict[str, Any]]:
    """Where referral convenience is the AIC entry wedge: counties
    ranked by demand x distance (patient-miles) — real patient pools
    sitting far from the nearest access point. A high score with
    in-county HOPD-only access is a de-novo AIC site read; NO_IN_COUNTY
    counties indicate where an adjacent-county site pulls referrals."""
    rows = tx_county_universe()
    scored = []
    for r in rows:
        scored.append(dict(
            r, patient_miles=round(
                r["infusion_patients"] * r["expected_distance_mi"])))
    scored.sort(key=lambda x: -x["patient_miles"])
    return scored[:top]


# ── Four-metro member-county deep-dive ──────────────────────────────

#: The four target metros (CBSA-title prefixes). Together they hold
#: ~65% of Texas infusion demand; the deep-dive goes county-by-county
#: inside each.
TX_TARGET_METRO_PREFIXES = (
    "Dallas-Fort Worth", "Houston", "San Antonio", "Austin",
)

#: Effective door-to-door travel speeds for the drive-time proxy —
#: MODELED constants (metro arterial vs rural highway averages). The
#: convenience threshold AIC operators quote is ~20-30 minutes; the
#: proxy turns modeled miles into that operational unit. Replace with
#: a drive-time API in engagement.
URBAN_MPH = 25.0
RURAL_MPH = 45.0


def _drive_minutes(dist_mi: float, urban_share: float) -> float:
    mph = urban_share * URBAN_MPH + (1.0 - urban_share) * RURAL_MPH
    return dist_mi / mph * 60.0 if mph else 0.0


def _siting_verdict(r: dict[str, Any]) -> str:
    """Deterministic per-county siting read from the computed fields —
    a rule, not a judgment call, so it audits."""
    pts, tier = r["infusion_patients"], r["access_tier"]
    if tier == "NO_IN_COUNTY" and pts >= 500:
        return ("Spillover catchment — first-mover AIC wedge: real "
                "demand, zero in-county incumbents")
    if tier == "MULTI_SITE" and pts >= 5_000:
        return ("Core volume — convenience share-shift vs the HOPD "
                "incumbents")
    if tier == "SINGLE_SITE" and pts >= 1_000:
        return ("Single incumbent — co-locate at the hospital's "
                "referral edge")
    if tier == "NO_IN_COUNTY":
        return "Thin demand — serve from the adjacent-county site"
    return "Hold — demand too thin for a dedicated site"


def metro_state_context() -> dict[str, Any]:
    """Texas state-level context for the metro deep-dives, read from
    the vendored aggregates (all REAL; each names its source). State
    granularity — county-level PLACES needs the ingest script."""
    import csv as _csv
    out: dict[str, Any] = {}
    eq = _DATA / "vendor" / "cdc_places" / "places_equity_state.csv"
    if eq.exists():
        with eq.open() as fh:
            for row in _csv.DictReader(fh):
                if row.get("state") == "TX":
                    out["places"] = {
                        "uninsured_18_64_pct": float(
                            row["uninsured_18_64"]),
                        "fair_poor_health_pct": float(
                            row["fair_poor_health"]),
                        "diabetes_pct": float(row["diabetes"]),
                        "obesity_pct": float(row["obesity"]),
                        "depression_pct": float(row["depression"]),
                        "source": "CDC PLACES state equity aggregate",
                    }
    ma = _DATA / "vendor" / "ma_geo" / "ma_geo_state.csv"
    if ma.exists():
        with ma.open() as fh:
            rows = [r for r in _csv.DictReader(fh)
                    if r.get("state") == "TX"]
        if rows:
            r = max(rows, key=lambda x: x.get("year") or "")
            out["ma"] = {
                "year": r["year"],
                "ma_enrollment": int(float(r["ma_enrollment"])),
                "avg_age": float(r["avg_age"]),
                "female_pct": float(r["female_pct"]),
                "dual_eligible_pct": float(r["dual_eligible_pct"]),
                "source": "CMS MA geographic-variation state file",
            }
    hp = _DATA / "vendor" / "hrsa" / "hrsa_hpsa_pc_by_state.csv"
    if hp.exists():
        with hp.open() as fh:
            for row in _csv.DictReader(fh):
                if row.get("state") == "TX":
                    out["hpsa"] = {
                        "designated_pc_hpsas": int(
                            float(row["designated_pc_hpsas"])),
                        "median_hpsa_score": float(
                            row["median_hpsa_score"]),
                        "source": "HRSA primary-care HPSA file",
                    }
    return out


@functools.lru_cache(maxsize=1)
def metro_county_deepdive() -> list[dict[str, Any]]:
    """The four target metros, county by county: every member county's
    real demographics + demand, its REAL facility roster (names from
    the geocoded CMS file), real intra-county facility spacing, the
    distance + drive-time proxy, age-band demand split, and a
    deterministic siting verdict. Ordered by metro demand."""
    from .texas_infusion import metro_age_breakdown

    universe = tx_county_universe()
    pts_by_county: dict[str, list[dict[str, Any]]] = {}
    for p in tx_access_points():
        pts_by_county.setdefault(p["county"], []).append(p)

    metros: list[dict[str, Any]] = []
    for prefix in TX_TARGET_METRO_PREFIXES:
        members = [r for r in universe
                   if (r["cbsa_title"] or "").startswith(prefix)]
        if not members:
            continue
        metro_pts: list[dict[str, Any]] = []
        counties: list[dict[str, Any]] = []
        for r in sorted(members, key=lambda x: -x["infusion_patients"]):
            cname = _norm_county(r["county"])
            roster = sorted(
                pts_by_county.get(cname, []),
                key=lambda p: (p["kind"] != "STAC", p["name"]))
            metro_pts.extend(roster)
            bands = metro_age_breakdown(
                float(r["population"]), float(r["pct_age_65_plus"]))
            # Senior bands match on prefix — the _AGE_BANDS labels
            # use an en-dash ("65-74") that must not be retyped here.
            senior_share = sum(
                b["demand_share"] for b in bands
                if b["band"].startswith(("65", "75")))
            mins = _drive_minutes(
                r["expected_distance_mi"], 1.0 - r["pct_rural"])
            counties.append({
                **r,
                "facility_roster": [
                    {"name": p["name"], "city": p["city"],
                     "kind": p["kind"]} for p in roster],
                "drive_minutes": round(mins, 1),
                "senior_demand_share": round(senior_share, 3),
                "patients_65_plus": round(
                    r["infusion_patients"] * senior_share),
                "patients_under_65": round(
                    r["infusion_patients"] * (1.0 - senior_share)),
                "patient_miles": round(r["infusion_patients"]
                                       * r["expected_distance_mi"]),
                "siting_verdict": _siting_verdict(r),
            })
        metro_nn = _nearest_nn_mi(metro_pts)
        demand = sum(c["infusion_patients"] for c in counties)
        metros.append({
            "metro": prefix,
            "cbsa_title": counties[0]["cbsa_title"],
            "counties": counties,
            "member_counties": len(counties),
            "population": sum(c["population"] for c in counties),
            "seniors_65_plus": sum(
                c["seniors_65_plus"] for c in counties),
            "infusion_patients": demand,
            "access_points": sum(c["access_points"] for c in counties),
            "facility_nn_mi": round(metro_nn, 1)
            if metro_nn is not None else None,
            "weighted_distance_mi": _weighted_distance(counties),
            "weighted_drive_minutes": round(
                sum(c["infusion_patients"] * c["drive_minutes"]
                    for c in counties) / demand, 1) if demand else 0.0,
            "no_access_counties": sum(
                1 for c in counties
                if c["access_tier"] == "NO_IN_COUNTY"),
        })
    metros.sort(key=lambda m: -m["infusion_patients"])
    return metros
