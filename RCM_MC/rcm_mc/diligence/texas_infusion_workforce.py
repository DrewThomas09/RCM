"""Texas infusion workforce & geographic-demand layer.

Two analytic cuts a deal team asks when underwriting a Texas AIC
(ambulatory infusion center) + home-infusion platform:

1. **Employment by specialty** — who staffs and who feeds an infusion
   platform. The *clinical* roster (infusion RNs, pharmacists, pharmacy
   techs, NPs/PAs/LVNs/MAs) is the labor supply you hire against; the
   *prescriber* roster (rheumatology, GI, neurology, heme/onc,
   allergy/immunology, infectious disease) is the referral funnel that
   generates infusion demand. Headcounts anchor to BLS OES Texas (May
   2023, clinical occupations) and AAMC/ACGME national specialist
   densities scaled to the Texas population (prescribers); the
   infusion-relevant share and the per-channel fit are MODELED and
   labelled illustrative — the same convention the rest of the Texas
   infusion CDD uses.

2. **County demand geography** — a true-geography heatmap. Every county
   that has a geocoded CMS facility gets a centroid (the mean of its
   in-county facility lat/lon — REAL coordinates), coloured by demand
   intensity (infusion patients per 100k) and sized by absolute demand.
   The 100 facility-less rural counties carry ~8% of demand and are
   surfaced as a whitespace list rather than positioned with invented
   coordinates. The state boundary is the real Census polygon vendored
   in ``rcm_mc/data/us_states.geojson``.

Nothing is typed into the UI — every figure recomputes here from
vendored public data plus the documented model.
"""
from __future__ import annotations

import functools
import json
import statistics
from pathlib import Path
from typing import Any

from .texas_infusion_geo import (
    _norm_county,
    tx_access_points,
    tx_county_universe,
)

_DATA = Path(__file__).resolve().parent.parent / "data"
_GEOJSON = _DATA / "us_states.geojson"


# ── Employment by specialty ─────────────────────────────────────────

#: Clinical occupations that staff an infusion platform. ``tx_employment``
#: is the BLS OES May-2023 Texas statewide estimate for the SOC code
#: (REAL anchor). ``infusion_relevant`` is the MODELED share of that
#: workforce realistically addressable to AIC/home-infusion staffing.
#: ``aic_fit`` / ``home_fit`` are 0-100 channel-fit intensities (MODELED)
#: — how central the role is to each site of care. ``scarcity`` is a
#: 0-100 hiring-difficulty intensity (MODELED) used by the heatmap.
_CLINICAL = [
    {"role": "Registered nurses (infusion)", "soc": "29-1141",
     "tx_employment": 240_940, "infusion_relevant": 0.045,
     "aic_fit": 100, "home_fit": 95, "demand_pull": 70, "scarcity": 78,
     "note": "Chairside + home-visit infusion administration; the "
             "binding constraint on chair throughput."},
    {"role": "Pharmacists", "soc": "29-1051",
     "tx_employment": 22_340, "infusion_relevant": 0.07,
     "aic_fit": 85, "home_fit": 90, "demand_pull": 60, "scarcity": 62,
     "note": "Sterile-compounding oversight (USP <797>) + clinical "
             "review; home infusion is pharmacy-led."},
    {"role": "Pharmacy technicians", "soc": "29-2052",
     "tx_employment": 40_720, "infusion_relevant": 0.08,
     "aic_fit": 80, "home_fit": 88, "demand_pull": 45, "scarcity": 48,
     "note": "Admixture / compounding labour — the unit-economics "
             "lever in a home-infusion pharmacy."},
    {"role": "Nurse practitioners", "soc": "29-1171",
     "tx_employment": 19_330, "infusion_relevant": 0.04,
     "aic_fit": 70, "home_fit": 55, "demand_pull": 65, "scarcity": 70,
     "note": "Supervising provider for the chair; widens prescriber "
             "capacity under Texas delegated practice."},
    {"role": "Physician assistants", "soc": "29-1071",
     "tx_employment": 10_540, "infusion_relevant": 0.035,
     "aic_fit": 62, "home_fit": 45, "demand_pull": 60, "scarcity": 66,
     "note": "Alternate supervising provider; common in GI / rheum "
             "group-attached AICs."},
    {"role": "Licensed vocational nurses", "soc": "29-2061",
     "tx_employment": 68_500, "infusion_relevant": 0.03,
     "aic_fit": 55, "home_fit": 60, "demand_pull": 35, "scarcity": 40,
     "note": "Lower-cost administration support where scope and "
             "delegation allow."},
    {"role": "Medical assistants", "soc": "31-9092",
     "tx_employment": 76_300, "infusion_relevant": 0.025,
     "aic_fit": 58, "home_fit": 20, "demand_pull": 25, "scarcity": 28,
     "note": "Intake, vitals, scheduling — the front-office economics "
             "of a high-throughput AIC."},
]

#: Prescriber specialties that generate infusion referrals. National
#: active-physician density per 100k (AAMC/ACGME ballpark, REAL anchor)
#: is scaled to the Texas population to estimate the Texas physician
#: count (MODELED). ``therapies`` / ``channel`` describe the infusion
#: demand each specialty drives; ``aic_fit`` / ``home_fit`` /
#: ``demand_pull`` are 0-100 MODELED intensities for the heatmap.
_PRESCRIBERS = [
    {"specialty": "Rheumatology", "per_100k": 1.0,
     "therapies": "Infliximab, rituximab, IVIG (RA, lupus, vasculitis)",
     "channel": "AIC + HOPD",
     "aic_fit": 95, "home_fit": 35, "demand_pull": 92, "scarcity": 88},
    {"specialty": "Gastroenterology", "per_100k": 4.0,
     "therapies": "Infliximab, vedolizumab, ustekinumab (Crohn's, UC)",
     "channel": "AIC",
     "aic_fit": 100, "home_fit": 25, "demand_pull": 95, "scarcity": 60},
    {"specialty": "Neurology", "per_100k": 4.8,
     "therapies": "IVIG, ocrelizumab, natalizumab (MS, CIDP, MG)",
     "channel": "AIC + home (IVIG)",
     "aic_fit": 88, "home_fit": 70, "demand_pull": 90, "scarcity": 72},
    {"specialty": "Hematology / oncology", "per_100k": 5.5,
     "therapies": "Chemotherapy, IVIG, supportive biologics",
     "channel": "HOPD + AIC",
     "aic_fit": 70, "home_fit": 30, "demand_pull": 85, "scarcity": 65},
    {"specialty": "Allergy & immunology", "per_100k": 1.2,
     "therapies": "IVIG / SCIG (PIDD), omalizumab (severe asthma)",
     "channel": "AIC + home (SCIG)",
     "aic_fit": 82, "home_fit": 78, "demand_pull": 80, "scarcity": 70},
    {"specialty": "Infectious disease", "per_100k": 2.1,
     "therapies": "OPAT — IV antibiotics / antifungals",
     "channel": "Home + AIC",
     "aic_fit": 65, "home_fit": 95, "demand_pull": 88, "scarcity": 75},
]


def _tx_population() -> int:
    """Texas population from the vendored county universe (REAL ACS)."""
    return sum(r["population"] for r in tx_county_universe())


@functools.lru_cache(maxsize=1)
def texas_specialty_employment() -> dict[str, Any]:
    """Employment-by-specialty for a Texas AIC + home-infusion platform.

    Returns the clinical roster (BLS OES TX anchors + modeled infusion
    share), the prescriber roster (national density scaled to TX), the
    metro headcount apportionment (population-share, the only public
    sub-state split available without provider-level geocoding), and the
    heatmap matrix rows. Cached because every field is deterministic.
    """
    pop = _tx_population()

    clinical = []
    for c in _CLINICAL:
        relevant = round(c["tx_employment"] * c["infusion_relevant"])
        clinical.append({**c, "infusion_relevant_headcount": relevant})

    prescribers = []
    for p in _PRESCRIBERS:
        tx_count = round(p["per_100k"] * pop / 100_000)
        prescribers.append({**p, "tx_physicians": tx_count})

    # Metro apportionment — the four major Texas metros by population
    # (from the county universe CBSA membership). The remainder is the
    # rest-of-state. This is the honest public sub-state split: there is
    # no provider-level geocoding of the infusion workforce.
    metros = _metro_population_shares()

    total_clinical = sum(c["tx_employment"] for c in clinical)
    total_relevant = sum(c["infusion_relevant_headcount"] for c in clinical)
    total_prescribers = sum(p["tx_physicians"] for p in prescribers)

    # Heatmap matrix — one row per specialty (clinical then prescriber),
    # each carrying the 0-100 channel-fit / demand / scarcity intensities
    # the matrix heatmap colours. Headcount rides along for the bar.
    matrix = []
    for c in clinical:
        matrix.append({
            "group": "Clinical staffing", "label": c["role"],
            "headcount": c["infusion_relevant_headcount"],
            "headcount_note": f'{c["tx_employment"]:,} TX (OES) · '
                              f'{c["infusion_relevant"]*100:.1f}% infusion',
            "aic_fit": c["aic_fit"], "home_fit": c["home_fit"],
            "demand_pull": c["demand_pull"], "scarcity": c["scarcity"]})
    for p in prescribers:
        matrix.append({
            "group": "Prescriber specialty", "label": p["specialty"],
            "headcount": p["tx_physicians"],
            "headcount_note": f'{p["per_100k"]:.1f}/100k × TX pop',
            "aic_fit": p["aic_fit"], "home_fit": p["home_fit"],
            "demand_pull": p["demand_pull"], "scarcity": p["scarcity"]})

    return {
        "clinical": clinical,
        "prescribers": prescribers,
        "metros": metros,
        "matrix": matrix,
        "matrix_columns": [
            {"key": "aic_fit", "label": "AIC fit"},
            {"key": "home_fit", "label": "Home-infusion fit"},
            {"key": "demand_pull", "label": "Demand pull"},
            {"key": "scarcity", "label": "Hiring scarcity"},
        ],
        "totals": {
            "clinical_workforce": total_clinical,
            "infusion_relevant_clinical": total_relevant,
            "prescriber_physicians": total_prescribers,
            "tx_population": pop,
        },
        "sources": (
            "BLS OES May 2023 (Texas statewide, clinical SOC codes) · "
            "AAMC/ACGME specialist density (national, scaled to TX "
            "population) · ACS county population. Infusion-relevant "
            "share and per-channel fit are illustrative model overlays."),
    }


def _metro_population_shares() -> list[dict[str, Any]]:
    """The four major Texas metros + rest-of-state, with population and
    share. Built from the county universe CBSA titles so it always ties
    to the same demand base the rest of the page uses."""
    rows = tx_county_universe()
    tx_pop = sum(r["population"] for r in rows) or 1
    metro_keys = [
        ("Dallas–Fort Worth", "Dallas-Fort Worth-Arlington"),
        ("Houston", "Houston-Pasadena-The Woodlands"),
        ("San Antonio", "San Antonio-New Braunfels"),
        ("Austin", "Austin-Round Rock-San Marcos"),
    ]
    out, claimed = [], 0
    for label, prefix in metro_keys:
        pop = sum(r["population"] for r in rows
                  if (r.get("cbsa_title") or "").startswith(prefix))
        claimed += pop
        out.append({"metro": label, "population": pop,
                    "share": round(pop / tx_pop, 4)})
    rest = tx_pop - claimed
    out.append({"metro": "Rest of Texas", "population": rest,
                "share": round(rest / tx_pop, 4)})
    return out


@functools.lru_cache(maxsize=1)
def texas_therapy_mix() -> dict[str, Any]:
    """The therapy layer that connects the prescriber funnel to demand
    and diligence risk: each home/AIC infusion therapy class with its
    estimated Texas patient count (real population × published treated-
    prevalence) and its five-axis risk profile. Merges the demand,
    clinical-reference and risk views from
    :mod:`rcm_mc.diligence.texas_infusion` so this page never re-derives
    a number the main CDD already owns."""
    from .texas_infusion import (
        home_infusion_conditions,
        home_infusion_therapy_reference,
        home_infusion_therapy_risk,
    )

    rows = tx_county_universe()
    pop = sum(r["population"] for r in rows)
    seniors = sum(r["seniors_65_plus"] for r in rows)

    demand = {t["key"]: t for t in home_infusion_conditions(pop, seniors)}
    ref = {t["key"]: t for t in home_infusion_therapy_reference()}
    risk = home_infusion_therapy_risk()

    therapies = []
    for t in risk["therapies"]:
        k = t["key"]
        d = demand.get(k, {})
        r = ref.get(k, {})
        therapies.append({
            "key": k,
            "therapy": t["therapy"],
            "rank": t["rank"],
            "conditions": r.get("conditions", ""),
            "regimen": r.get("regimen", ""),
            "margin": r.get("margin", ""),
            "epi_per_100k": d.get("epi_per_100k"),
            "estimated_patients": d.get("estimated_patients"),
            "axes": t["axes"],
            "overall_pct": t["overall_pct"],
            "band": t["band"],
            "lead_risk": t["lead_risk"],
            "readmission_pct": t.get("readmission_pct"),
        })
    therapies.sort(key=lambda x: x["rank"])
    return {
        "therapies": therapies,
        "axis_labels": risk["axis_labels"],
        "weights": risk["weights"],
        "most_at_risk": risk["most_at_risk"],
        "note": risk["note"],
        "tx_population": pop,
    }


def specialty_employment_by_metro() -> list[dict[str, Any]]:
    """Clinical infusion-relevant headcount apportioned across the metros
    by population share — the sub-state employment view. Honest about
    method: there is no provider-level geocode of the infusion
    workforce, so this is a population apportionment, not a measured
    count."""
    emp = texas_specialty_employment()
    metros = emp["metros"]
    out = []
    for c in emp["clinical"]:
        cells = {m["metro"]: round(c["infusion_relevant_headcount"]
                                   * m["share"]) for m in metros}
        out.append({"role": c["role"],
                    "tx": c["infusion_relevant_headcount"], **cells})
    return out


# ── County demand geography (true-geography heatmap) ────────────────

@functools.lru_cache(maxsize=1)
def tx_boundary_lonlat() -> list[tuple[float, float]]:
    """The real Texas state boundary as (lon, lat) vertices, from the
    vendored Census polygon. Used by the UI to project an accurate map
    frame for the county-demand heatmap."""
    if not _GEOJSON.exists():
        return []
    data = json.loads(_GEOJSON.read_text())
    tx = next((f for f in data.get("features", [])
               if f.get("properties", {}).get("name") == "Texas"), None)
    if not tx:
        return []
    ring = tx["geometry"]["coordinates"][0]
    return [(float(lon), float(lat)) for lon, lat in ring]


@functools.lru_cache(maxsize=1)
def county_demand_centroids() -> dict[str, Any]:
    """County-level infusion demand positioned at REAL facility-derived
    centroids for the geographic heatmap.

    Each county with ≥1 geocoded CMS facility gets a centroid = the mean
    of its in-county facility lat/lon (real coordinates). Counties with
    no in-county facility (the rural whitespace) cannot be positioned
    without invented coordinates, so they are returned separately as a
    ranked whitespace list rather than placed on the map. Demand
    intensity = infusion patients per 100k; absolute demand sizes the
    dot.
    """
    pts = tx_access_points()
    by_county: dict[str, list[dict[str, Any]]] = {}
    for p in pts:
        by_county.setdefault(p["county"], []).append(p)

    rows = tx_county_universe()
    placed, unplaced = [], []
    total_demand = sum(r["infusion_patients"] for r in rows) or 1
    for r in rows:
        key = _norm_county(r["county"])
        fac = by_county.get(key)
        rec = {
            "county": r["county"],
            "metro_class": r["metro_class"],
            "cbsa_title": r.get("cbsa_title"),
            "population": r["population"],
            "infusion_patients": r["infusion_patients"],
            "patients_per_100k": r["patients_per_100k"],
            "access_tier": r["access_tier"],
            "expected_distance_mi": r["expected_distance_mi"],
        }
        if fac:
            rec["lat"] = round(statistics.mean(f["lat"] for f in fac), 5)
            rec["lon"] = round(statistics.mean(f["lon"] for f in fac), 5)
            rec["facilities"] = len(fac)
            placed.append(rec)
        else:
            unplaced.append(rec)

    placed.sort(key=lambda x: -x["infusion_patients"])
    unplaced.sort(key=lambda x: -x["infusion_patients"])
    placed_demand = sum(r["infusion_patients"] for r in placed)
    intens = [r["patients_per_100k"] for r in placed]
    return {
        "placed": placed,
        "unplaced": unplaced,
        "boundary": tx_boundary_lonlat(),
        "coverage": {
            "counties_total": len(rows),
            "counties_placed": len(placed),
            "counties_unplaced": len(unplaced),
            "demand_share_placed": round(placed_demand / total_demand, 4),
        },
        "intensity_domain": {
            "lo": round(min(intens), 1) if intens else 0.0,
            "mid": round(statistics.median(intens), 1) if intens else 0.0,
            "hi": round(max(intens), 1) if intens else 0.0,
        },
    }
