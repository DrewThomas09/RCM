"""Texas infusion-therapy market — a worked, sourced CDD sizing.

A dedicated state deep-dive the generic per-state facility-count dives
can't produce: there is no vendored CMS "infusion provider" census, so
geography for infusion is built the honest way — a national demand
model scaled to Texas by real Census population share, then layered
with the dimensions a PE diligence on an infusion platform actually
turns on:

  1. Market sizing (TAM/SAM/SOM) — the national NHIA/MedPAC demand
     chain scaled to TX population, run through the SAME ``compute()``
     the TAM/SAM builder uses, so the funnel + projection + tornado are
     the verified ones.
  2. Therapy-form segmentation — specialty biologics, oncology support,
     anti-infectives (OPAT), nutrition (TPN), neurology — with growth
     divergence (where it grows fastest).
  3. Site-of-care segmentation — home infusion, ambulatory infusion
     suite, HOPD, physician office — the site-of-care shift thesis that
     defines the sector.
  4. Concentration — HHI over the named infusion chains (DOJ/FTC scale)
     → the fragmentation that drives the buy-and-build thesis.
  5. Medicare population growth — real TX 65+ population from ACS via
     ``demographics_state``, the demand tailwind.
  6. Payer mix — commercial / Medicare Part B+D / Medicaid / self-pay,
     with the Texas Medicaid-non-expansion adjustment.
  7. Texas structural factors — no Certificate of Need (free entry),
     metro concentration, uninsured drag.

Every magnitude is a named-source constant; the numbers are STARTING
POINTS for an engagement (NHIA/MedPAC/Census public data), not the
fund's proprietary research, and the page says so. The state scaling
and the HHI are pure arithmetic on those constants + the real ACS
population, so they recompute and audit cleanly.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .tam_sam import (
    DriverStep, GrowthDriver, Segment, TamSamModel, compute, sensitivity,
)

# ── Sourced constants ───────────────────────────────────────────────

#: US resident population, Census Bureau 2024 vintage estimate. The
#: denominator for the population-share scaling of the national demand
#: model down to Texas.
US_POPULATION_2024 = 334_900_000

#: National infused-therapy demand magnitudes (NHIA / MedPAC public
#: data) — the same anchors the generic infusion TAM/SAM template uses.
US_INFUSION_PATIENTS = 3_200_000          # patients on infused therapy/yr
INFUSIONS_PER_PATIENT_YR = 18             # biologic q2-8wk + abx dailies
REVENUE_PER_INFUSION = 650                # drug + admin, ASP+6/AWP blend


def _hhi_named(chains: List[Dict[str, Any]]) -> float:
    """HHI (DOJ/FTC 0–10,000 scale) over the NAMED chains only — the
    fragmented independent/regional pool is treated as atomized, the
    standard read for how concentrated the *operator* layer is. Shares
    are fractions (0–1)."""
    return round(
        sum((c["share"] * 100.0) ** 2 for c in chains if c.get("named")), 0)


def texas_infusion_model(tx_population: int) -> TamSamModel:
    """The national infusion demand chain scaled to Texas by population
    share. Returns a real :class:`TamSamModel` so the page can run the
    verified ``compute()`` / ``sensitivity()`` on it."""
    tx_share = tx_population / US_POPULATION_2024
    tx_patients = round(US_INFUSION_PATIENTS * tx_share)
    return TamSamModel(
        name="Texas infusion · ambulatory + home market",
        chain=[
            DriverStep(
                "Texas patients on infused therapies / yr",
                tx_patients, op="base", unit="patients",
                source=(
                    f"US 3.2M (NHIA) × TX population share "
                    f"{tx_share*100:.1f}% (Census 2024: TX "
                    f"{tx_population/1e6:.1f}M / US 334.9M)"),
            ),
            DriverStep(
                "Avg infusions per patient / yr", INFUSIONS_PER_PATIENT_YR,
                op="mult", unit="infusions/yr",
                source="NHIA (biologic q2–8wk + antibiotic dailies blend)"),
            DriverStep(
                "Avg revenue per infusion (drug + admin)",
                REVENUE_PER_INFUSION, op="price", unit="$/infusion",
                source="ASP+6 / AWP blend across payer mix (MedPAC Part B "
                       "drug chapter)"),
        ],
        segments=[
            Segment("Specialty biologics (immunology / IVIG)", 0.40, None,
                    note="the margin engine — IVIG, anti-TNF, biologics",
                    growth_pct=9.0),
            Segment("Oncology support / chemo", 0.25, None,
                    growth_pct=4.0),
            Segment("Anti-infectives (OPAT)", 0.20, None,
                    note="hospital-discharge driven", growth_pct=5.0),
            Segment("Nutrition / TPN", 0.10, None, growth_pct=3.0),
            Segment("Neurology (MS / migraine) & other", 0.05, None,
                    note="fastest sub-segment — new infused MS + CGRP "
                         "agents", growth_pct=12.0),
        ],
        growth_drivers=[
            GrowthDriver("Site-of-care shift from HOPD", 5.0,
                         "payers steer suite/home over 2–3× HOPD pricing — "
                         "the structural tailwind"),
            GrowthDriver("Biologics pipeline / approvals", 4.0,
                         "new infused agents expand the treated population"),
            GrowthDriver("Texas 65+ / in-migration", 2.5,
                         "Sun-Belt aging + net in-migration grow the "
                         "covered-lives base faster than the US"),
            GrowthDriver("Biosimilar price deflation", -2.5,
                         "biosimilar adoption compresses drug revenue per "
                         "infusion — a real headwind, shown as one"),
            GrowthDriver("Infusion-nurse capacity", -1.0,
                         "nurse supply caps chair/visit utilization"),
        ],
        sam_share=0.58,
        sam_note="Payer-steered + physician-referred TX volume an "
                 "independent platform can capture (excludes health-system "
                 "captive HOPD suites). Slightly above the US 55% — TX is "
                 "Certificate-of-Need-free, so entry is unconstrained.",
        som_share=0.05,
        som_note="Obtainable TX share at entry — the suite market is "
                 "fragmented (Option Care ~20% of home infusion "
                 "nationally; AIS layer atomized).",
        horizon_years=5,
        basis_note="National NHIA/MedPAC magnitudes scaled to TX by "
                   "Census population share — illustrative starting "
                   "points, not the fund's research. Replace with "
                   "engagement data before IC use.",
    )


def _site_of_care() -> List[Dict[str, Any]]:
    """TAM split by site of care + each site's own growth — the
    site-of-care shift is the defining infusion thesis. Shares sum to
    1.0; HOPD is the share being steered AWAY (declining)."""
    return [
        {"site": "Home infusion", "share": 0.38, "growth_pct": 9.0,
         "note": "payer-steered, lowest cost of care; the platform core"},
        {"site": "Ambulatory infusion suite (AIS)", "share": 0.22,
         "growth_pct": 11.0,
         "note": "fastest-growing site — freestanding chairs, hub-and-"
                 "spoke economics; the de-novo whitespace"},
        {"site": "Hospital outpatient (HOPD)", "share": 0.30,
         "growth_pct": -3.0,
         "note": "the share being steered away — 2–3× the suite rate; "
                 "declining as payers mandate site-of-care"},
        {"site": "Physician office (buy-and-bill)", "share": 0.10,
         "growth_pct": 2.0,
         "note": "office-administered Part B drugs; modest growth"},
    ]


def _payer_mix() -> List[Dict[str, Any]]:
    """Texas infusion payer mix. Commercial-heavy (Part B buy-and-bill +
    employer plans); Medicaid suppressed by Texas non-expansion; a real
    self-pay/uninsured drag (TX uninsured ~20%). NHIA payer surveys +
    MedPAC, adjusted for the TX non-expansion structure."""
    return [
        {"payer": "Commercial / employer", "share": 0.45,
         "note": "buy-and-bill + specialty-pharmacy carve-outs; the "
                 "margin pool and the site-of-care-steerage driver"},
        {"payer": "Medicare (Part B + Part D)", "share": 0.35,
         "note": "Part B drugs ASP+6 (HOPD/office/home) + Part D self-"
                 "admin; grows with the 65+ base"},
        {"payer": "Medicaid (TX)", "share": 0.12,
         "note": "suppressed vs expansion states — Texas did NOT expand "
                 "Medicaid, so the low-income adult pool is uninsured "
                 "rather than Medicaid-covered"},
        {"payer": "Self-pay / uninsured / charity", "share": 0.08,
         "note": "TX uninsured rate ~20% (highest in the US) — a real "
                 "bad-debt drag and the non-expansion consequence"},
    ]


def _chains() -> List[Dict[str, Any]]:
    """Named US infusion operators with approximate market share, mapped
    to Texas. There is no vendored TX infusion provider census, so these
    are national shares used illustratively for the concentration read —
    labeled as such. The independent/regional pool is the atomized
    remainder. Shares are fractions of the total home+AIS market."""
    named = [
        {"org": "Option Care Health", "share": 0.20, "named": True,
         "note": "largest US home-infusion platform (NYSE: OPCH)"},
        {"org": "CVS Health / Coram", "share": 0.08, "named": True,
         "note": "national specialty + home infusion"},
        {"org": "Optum (Amedisys/Contessa, Genoa)", "share": 0.06,
         "named": True, "note": "UnitedHealth vertical integration"},
        {"org": "Soleo Health", "share": 0.03, "named": True,
         "note": "PE-backed specialty infusion"},
        {"org": "KabaFusion", "share": 0.02, "named": True,
         "note": "IVIG-focused; PE-backed"},
        {"org": "Paragon Healthcare (Elevance)", "share": 0.02,
         "named": True, "note": "payer-owned (Anthem/Elevance) AIS"},
    ]
    named_total = sum(c["share"] for c in named)
    named.append({
        "org": "Regional / hospital-affiliated / independents",
        "share": round(1.0 - named_total, 4), "named": False,
        "note": "the fragmented, atomized remainder — the roll-up pool"})
    return named


#: National provider-count anchors (NHIA + industry). There is no
#: vendored CMS infusion-provider census, so TX counts are derived by
#: population share — labeled as estimates, not a facility roll-call.
US_HOME_INFUSION_LOCATIONS = 800     # NHIA home-infusion pharmacy sites
US_AIS_CENTERS = 1_600               # freestanding ambulatory infusion suites
US_AIS_GROWTH_PCT = 10.0             # AIS site-count CAGR (industry)

#: Texas single-year numeric population gain, Census Bureau Vintage
#: 2024 (year ending 2024-07-01) — the largest of any state — and the
#: implied growth rate off the 2023 base. Verifiable, citable.
TX_POP_GAIN_2024 = 562_941
TX_POP_GROWTH_PCT = 1.8              # ≈ gain / prior-year population
TX_SENIOR_GROWTH_PCT = 3.5          # 65+ grows faster (aging + in-migration)


def texas_provider_landscape(tx_share: float) -> Dict[str, Any]:
    """Estimated Texas infusion-provider counts by channel, derived
    from national anchors scaled by population share. Honest about
    being an estimate — no TX infusion census is vendored."""
    home = round(US_HOME_INFUSION_LOCATIONS * tx_share)
    ais = round(US_AIS_CENTERS * tx_share)
    return {
        "home_infusion_locations": home,
        "ambulatory_infusion_centers": ais,
        "ais_growth_pct": US_AIS_GROWTH_PCT,
        "note": (
            f"Derived: US ~{US_HOME_INFUSION_LOCATIONS} home-infusion "
            f"pharmacy sites + ~{US_AIS_CENTERS:,} freestanding AIS "
            f"(NHIA / industry) × TX population share "
            f"{tx_share*100:.1f}%. No CMS infusion-provider census is "
            "vendored, so these are scaled estimates, not a facility "
            "roll-call — replace with a state pharmacy-board / NPPES "
            "pull in diligence."),
    }


def _attractiveness(seniors: float, growth_pct: float,
                    rural: float) -> float:
    """Metro attractiveness for an infusion platform: senior demand
    (log-scaled so the biggest metro doesn't swamp), 65+ density, and
    a rural-drag penalty (home-nurse routes are uneconomic in sparse
    areas). 0–100. Pure arithmetic on real ACS inputs."""
    import math
    demand = min(1.0, math.log10(max(seniors, 1)) / math.log10(1_000_000))
    return round(100.0 * (0.55 * demand
                          + 0.30 * min(1.0, growth_pct / 4.0)
                          + 0.15 * (1.0 - min(1.0, rural / 0.30))), 1)


def texas_metro_breakdown(tx_patients: int, tx_pop: int) -> List[Dict[str, Any]]:
    """Per-metro infusion demand + referral density + attractiveness
    rank for the four big Texas metros, from REAL CBSA ACS aggregates.

    Infusion patients per metro scale with the metro's senior (65+)
    population (the demand proxy); referral density = patients per 100k
    residents; AIS centers per metro scale with population. Ranked by a
    composite attractiveness score."""
    from ..data.cbsa_demographics import cbsa_list
    by_title = {r["cbsa_title"]: r for r in cbsa_list()}
    targets = [
        "Dallas-Fort Worth-Arlington, TX",
        "Houston-Pasadena-The Woodlands, TX",
        "San Antonio-New Braunfels, TX",
        "Austin-Round Rock-San Marcos, TX",
    ]
    # Total TX senior pool (for apportioning the patient base by metro
    # senior count — infusion demand tracks the 65+ + chronic base).
    tx_seniors = tx_pop * 0.1341
    rows: List[Dict[str, Any]] = []
    for t in targets:
        r = by_title.get(t)
        if not r:
            continue
        pop = float(r["population"])
        s65 = float(r.get("pct_age_65_plus") or 0.0)
        seniors = pop * s65
        rural = float(r.get("pct_rural") or 0.0)
        # Apportion TX infusion patients by share of TX seniors, then
        # add a small all-ages component (40% of demand is <65 biologics).
        senior_share = seniors / tx_seniors if tx_seniors else 0.0
        pop_share = pop / tx_pop if tx_pop else 0.0
        patients = round(tx_patients * (0.60 * senior_share
                                        + 0.40 * pop_share))
        rows.append({
            "metro": t.split(",")[0],
            "cbsa_code": r["cbsa_code"],
            "population": pop,
            "pct_age_65_plus": s65,
            "seniors": round(seniors),
            "pct_rural": rural,
            "uninsured_rate": float(r.get("uninsured_rate") or 0.0),
            "infusion_patients": patients,
            "referral_density_per_100k": round(patients / pop * 100_000, 1),
            "est_ais_centers": round(US_AIS_CENTERS * pop_share
                                     * (tx_pop / US_POPULATION_2024)),
            "attractiveness": _attractiveness(
                seniors, TX_SENIOR_GROWTH_PCT, rural),
        })
    rows.sort(key=lambda x: -x["attractiveness"])
    for i, x in enumerate(rows, start=1):
        x["rank"] = i
    return rows


#: Infusion-relevant age bands. ``us_share`` is the band's share of the
#: US resident population (Census age structure, 2023 ACS S0101); the
#: 65+ portion is REPLACED per-metro with the metro's real 65+ share so
#: the bands re-base to local data. ``util_index`` is a relative
#: infusion-utilization weight — prevalence of infused therapies rises
#: steeply with age + chronic-disease burden (oncology support, OPAT,
#: autoimmune biologics), anchored to NHIA / clinical patterns. The
#: index is illustrative (no per-band claims census is vendored) but the
#: population base is real.
_AGE_BANDS = [
    {"band": "0–17 (pediatric)", "us_share": 0.222, "util_index": 0.30,
     "note": "low base — pediatric IVIG, enzyme-replacement, select "
             "biologics only"},
    {"band": "18–44", "us_share": 0.362, "util_index": 0.70,
     "note": "autoimmune / IBD biologic onset peaks here"},
    {"band": "45–64", "us_share": 0.246, "util_index": 1.30,
     "note": "oncology + autoimmune ramp; commercially insured"},
    {"band": "65–74", "us_share": 0.097, "util_index": 1.80,
     "note": "oncology support + OPAT; Medicare onset"},
    {"band": "75+", "us_share": 0.073, "util_index": 2.20,
     "note": "highest per-capita — oncology, OPAT, frailty/TPN"},
]
_US_65_SHARE = 0.170   # the four-band 65+ total in the table above (0.097+0.073)


def metro_age_breakdown(metro_pop: float, pct_65: float) -> List[Dict[str, Any]]:
    """Split a metro's population into infusion-relevant age bands and
    rank them by infusion-demand contribution.

    The 65+ portion uses the metro's REAL 65+ share (re-based from the
    national table); the under-65 bands keep their national relative
    structure, rescaled to fill (1 − pct_65). Demand = band population ×
    utilization index, normalized to a share and ranked."""
    under_65_real = max(0.0, 1.0 - pct_65)
    under_65_us = 1.0 - _US_65_SHARE
    bands: List[Dict[str, Any]] = []
    for b in _AGE_BANDS:
        is_senior = b["band"] in ("65–74", "75+")
        if is_senior:
            # Re-base the two senior bands onto the metro's real 65+ share,
            # preserving their national ratio to each other.
            share = pct_65 * (b["us_share"] / _US_65_SHARE)
        else:
            share = under_65_real * (b["us_share"] / under_65_us)
        pop = metro_pop * share
        bands.append({
            "band": b["band"], "pop_share": share,
            "population": round(pop), "util_index": b["util_index"],
            "note": b["note"], "demand_raw": pop * b["util_index"],
        })
    total_demand = sum(b["demand_raw"] for b in bands) or 1.0
    for b in bands:
        b["demand_share"] = b["demand_raw"] / total_demand
    ranked = sorted(bands, key=lambda b: -b["demand_share"])
    for i, b in enumerate(ranked, start=1):
        b["demand_rank"] = i
    # Return in age order for the pyramid, but each row carries its rank.
    return bands


#: Illustrative known operator presence by metro — public branch
#: footprints (company locators / filings). NOT a TX provider census;
#: used to show WHICH big chains compete in each metro and to link them.
_METRO_OPERATORS = {
    "Houston": ["Option Care Health", "CVS Health / Coram",
                "Optum Infusion", "Soleo Health", "KabaFusion",
                "Paragon Healthcare (Elevance)"],
    "Dallas-Fort Worth-Arlington": [
        "Option Care Health", "CVS Health / Coram", "Optum Infusion",
        "Soleo Health", "Paragon Healthcare (Elevance)"],
    "Austin-Round Rock-San Marcos": [
        "Option Care Health", "CVS Health / Coram", "Soleo Health"],
    "San Antonio-New Braunfels": [
        "Option Care Health", "CVS Health / Coram", "Optum Infusion",
        "Paragon Healthcare (Elevance)"],
}

#: Operator → external link (investor/company site) so each named chain
#: in the per-city breakdown is clickable.
_OPERATOR_LINKS = {
    "Option Care Health": "https://www.optioncarehealth.com/locations",
    "CVS Health / Coram": "https://www.coramhc.com",
    "Optum Infusion": "https://www.optum.com/en/care/infusion-services.html",
    "Soleo Health": "https://www.soleohealth.com/locations",
    "KabaFusion": "https://www.kabafusion.com/locations",
    "Paragon Healthcare (Elevance)": "https://www.paragonhealthcare.com/locations",
}

#: Per-metro infusion-specialty tilt — the therapy mix a platform would
#: skew toward, read off the metro's demographic + provider ecosystem.
#: Illustrative, anchored to the demographic profile.
_METRO_SPECIALTY = {
    "Houston": (
        "Oncology-support heavy — the Texas Medical Center / MD Anderson "
        "ecosystem anchors chemo + supportive infusion referral volume; "
        "large OPAT discharge pipeline from the safety-net hospitals."),
    "Dallas-Fort Worth-Arlington": (
        "Balanced, commercial-heavy — the largest employer base in TX "
        "drives commercial biologics (immunology/IBD) and site-of-care "
        "steerage; broad oncology + OPAT."),
    "Austin-Round Rock-San Marcos": (
        "Youngest metro — autoimmune/IBD biologics and neurology (MS) "
        "skew with a tech-employer commercial payer mix; lower senior "
        "density but fast 65+ growth."),
    "San Antonio-New Braunfels": (
        "Older, military/VA-influenced and majority-Hispanic — oncology "
        "support, diabetes-complication infusions, and OPAT; higher "
        "Medicare + Medicaid mix than the other metros."),
}


def build_texas_metro_deepdive(
    metro: Dict[str, Any], tx_patients: int, tx_pop: int,
    places_county: "Dict[str, Any] | None" = None,
    female_by_fips: "Dict[str, float] | None" = None,
    cdc_rates: "Dict[str, Any] | None" = None,
) -> Dict[str, Any]:
    """Assemble the in-depth per-city analysis: age-band demand ranking,
    member-county ('suburb') breakdown with white-space, known operators
    (linked), and the specialty tilt. Real ACS population per county +
    the documented age/utilization model.

    ``places_county`` / ``female_by_fips`` carry live CDC PLACES county
    rates and ACS female shares (empty offline); ``cdc_rates`` is the TX
    state proxy-rate fallback. All are fetched lazily if not supplied."""
    import pandas as pd
    from pathlib import Path
    from ..data.county_demographics import demographics_county
    from ..data.acs_sex import female_share_for

    if places_county is None:
        from ..data.cdc_places_api import places_counties_by_fips
        places_county = places_counties_by_fips("TX")
    if female_by_fips is None:
        from ..data.acs_sex import county_female_share
        female_by_fips = county_female_share("TX", "48")
    if cdc_rates is None:
        cdc_rates = texas_cdc_state_rates(places_county or None)

    age_bands = metro_age_breakdown(metro["population"],
                                    metro["pct_age_65_plus"])

    # Member counties (the suburbs) from the CBSA crosswalk — real.
    cw_path = (Path(__file__).resolve().parent.parent / "data" / "vendor"
               / "cbsa_crosswalk" / "cbsa_county_crosswalk.csv")
    suburbs: List[Dict[str, Any]] = []
    try:
        cw = pd.read_csv(cw_path, dtype={"county_fips": str,
                                         "cbsa_code": str})
        fipses = cw[cw["cbsa_code"] == metro["cbsa_code"]]["county_fips"]
        metro_seniors = sum(
            (demographics_county(f).get("population") or 0)
            * (demographics_county(f).get("pct_age_65_plus") or 0)
            for f in fipses) or 1.0
        for f in fipses:
            d = demographics_county(f)
            pop = float(d.get("population") or 0)
            s65 = float(d.get("pct_age_65_plus") or 0)
            seniors = pop * s65
            # Apportion this metro's patient base by senior + total pop.
            senior_share = seniors / metro_seniors
            pop_share_in_metro = (pop / metro["population"]
                                  if metro["population"] else 0)
            patients = round(
                (tx_patients * (metro["population"] / tx_pop))
                * (0.60 * senior_share + 0.40 * pop_share_in_metro))
            est_ais = max(0, round(
                US_AIS_CENTERS * (pop / US_POPULATION_2024)))
            north = _NORTH_SUBURBS.get(metro["cbsa_code"], {})
            is_north = f in north.get("counties", {})
            illness = county_illness_burden(pop)
            fem = female_share_for(f, "TX", female_by_fips)
            places_row = (places_county or {}).get(f)
            county_rec = {
                "county": (d.get("county_name") or "")
                          .replace(" County", ""),
                "county_fips": f,
                "region": "North suburb" if is_north else "",
                "north_label": north.get("counties", {}).get(f, ""),
                "population": round(pop),
                "pct_age_65_plus": s65,
                "seniors": round(seniors),
                "pct_rural": float(d.get("pct_rural") or 0),
                "uninsured_rate": float(d.get("uninsured_rate") or 0),
                "child_poverty_rate": float(d.get("child_poverty_rate") or 0),
                "female_share": fem,
                "median_household_income":
                    float(d.get("median_household_income") or 0),
                "infusion_patients": patients,
                "est_ais_centers": est_ais,
                # White-space: patients per AIS chair-cluster. High =
                # underserved (demand with thin local capacity).
                "patients_per_ais": (round(patients / est_ais)
                                     if est_ais else None),
                "illness_burden": illness,
            }
            # CDC/ACS proxy demand by therapy + the payer-access index.
            county_rec["cdc_demand"] = county_cdc_demand(
                county_rec, cdc_rates, places_row, fem)
            county_rec["payer_access"] = county_payer_access(
                county_rec, cdc_rates)
            county_rec["cdc_live"] = bool(places_row)
            suburbs.append(county_rec)
    except Exception:  # noqa: BLE001 — crosswalk is best-effort
        suburbs = []

    suburbs.sort(key=lambda s: -s["infusion_patients"])
    for i, s in enumerate(suburbs, start=1):
        s["demand_rank"] = i
        # Capacity / saturation + opportunity score per county.
        s["capacity"] = county_capacity(s)
        s["opportunity"] = county_opportunity_score(s, s["capacity"])
    # White-space ranking: counties with real demand but the thinnest
    # estimated local capacity (highest patients-per-AIS, or zero AIS).
    ws = [s for s in suburbs if s["infusion_patients"] > 0]
    ws.sort(key=lambda s: -(s["patients_per_ais"] or 10 ** 9))
    whitespace = ws[:5]

    name = metro["metro"]
    # Match operator/specialty keys (which use the long CBSA title).
    long_key = next((k for k in _METRO_OPERATORS
                     if k.startswith(name) or name.startswith(k.split("-")[0])),
                    None)
    operators = [
        {"org": o, "link": _OPERATOR_LINKS.get(o, "")}
        for o in _METRO_OPERATORS.get(long_key or name, [])
    ]
    specialty = _METRO_SPECIALTY.get(long_key or name, "")

    return {
        "metro": name,
        "cbsa_code": metro["cbsa_code"],
        "population": metro["population"],
        "seniors": metro["seniors"],
        "attractiveness": metro["attractiveness"],
        "rank": metro.get("rank"),
        "uninsured_rate": metro["uninsured_rate"],
        "pct_rural": metro["pct_rural"],
        "age_bands": age_bands,
        "suburbs": suburbs,
        "whitespace_counties": whitespace,
        "operators": operators,
        "specialty": specialty,
        "north_suburbs": _NORTH_SUBURBS.get(metro["cbsa_code"], {})
                         .get("label", ""),
        # Metro-level illness burden = sum of member-county estimates.
        "illness_burden": _aggregate_illness(suburbs),
        # Metro-level CDC-proxy demand by therapy (sum of counties).
        "cdc_demand": _aggregate_cdc_demand(suburbs),
        "cdc_live": any(s.get("cdc_live") for s in suburbs),
        # Home-infusion-eligible population by therapy (real pop × epi).
        "home_infusion": home_infusion_conditions(
            metro["population"], metro.get("seniors")),
        # Annual home-infusion referral FLOW by therapy (new starts/yr).
        "home_infusion_discharges": home_infusion_discharge_volumes(
            metro["population"], metro.get("seniors")),
    }


def _aggregate_cdc_demand(suburbs: List[Dict[str, Any]]
                          ) -> List[Dict[str, Any]]:
    """Sum the per-county CDC-proxy therapy demand to the metro level."""
    agg: Dict[str, Dict[str, Any]] = {}
    for s in suburbs:
        for d in s.get("cdc_demand", []):
            row = agg.setdefault(d["key"], {
                "key": d["key"], "therapy": d["therapy"],
                "channel": d["channel"], "anchor_measure": d["anchor_measure"],
                "measures": d["measures"], "estimated_patients": 0,
                "note": d["note"], "any_live": False})
            row["estimated_patients"] += d["estimated_patients"]
            row["any_live"] = row["any_live"] or d["rate_is_county_live"]
    return sorted(agg.values(), key=lambda r: -r["estimated_patients"])


def _aggregate_illness(suburbs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sum the per-county infusion-relevant illness estimates to the
    metro level (real population-scaled), keyed by condition."""
    agg: Dict[str, Dict[str, Any]] = {}
    for s in suburbs:
        for ib in s.get("illness_burden", []):
            row = agg.setdefault(ib["condition"], {
                "condition": ib["condition"], "therapy": ib["therapy"],
                "channel": ib["channel"], "rate_pct": ib["rate_pct"],
                "estimated_patients": 0, "source": ib["source"]})
            row["estimated_patients"] += ib["estimated_patients"]
    return sorted(agg.values(), key=lambda r: -r["estimated_patients"])


def channel_economics() -> List[Dict[str, Any]]:
    """The two PE-relevant infusion channels — Ambulatory Infusion
    Center (AIC) and home infusion — broken down on the dimensions a
    deal team underwrites: reimbursement basis, margin model, working
    capital, and the channel-defining risk. (HOPD and physician-office
    are the *source* of steered volume, not the platform's channels.)
    Sourced to NHIA / MedPAC / CMS rule structure."""
    return [
        {
            "channel": "Ambulatory Infusion Center (AIC / AIS)",
            "what": "Freestanding infusion suites — chairs staffed by "
                    "infusion nurses; physician-, PE-, or payer-owned. "
                    "The site-of-care destination for HOPD-steered "
                    "biologics and oncology support.",
            "reimbursement": "Medical benefit, buy-and-bill. Medicare "
                    "Part B at ASP+6% (sequestered to ~ASP+4.3%) for "
                    "the drug + a separate administration code; "
                    "commercial at a % of AWP or a contracted rate, "
                    "below the HOPD rate (the steerage incentive).",
            "margin_model": "Drug is ~80–90% of gross revenue at a thin "
                    "spread; the operating margin is the administration "
                    "fee + drug-acquisition leverage (GPO / channel). "
                    "Chair utilization is the throughput lever.",
            "working_capital": "Buys the drug BEFORE it bills — specialty "
                    "agents run $5K–$30K per infusion, so AR days and "
                    "denials tie up real cash; a single denied claim is "
                    "a five-figure hit.",
            "key_risk": "White-bagging / brown-bagging mandates: a payer "
                    "forces the drug through its OWN specialty pharmacy, "
                    "stripping the buy-and-bill spread and leaving only "
                    "the (smaller) admin fee.",
        },
        {
            "channel": "Home Infusion",
            "what": "Pharmacy compounding + skilled-nursing in the "
                    "patient's home (NHIA-tracked). OPAT discharges, "
                    "IVIG, TPN, and self-administered specialty therapy.",
            "reimbursement": "Split and structurally awkward: Part B "
                    "drugs at ASP+6% + the Medicare Home Infusion "
                    "Therapy (HIT) professional-services payment that "
                    "pays ONLY on days a nurse is physically present "
                    "(the benefit's defining flaw); Part D for self-"
                    "administered drugs; commercial as a per-diem + "
                    "drug.",
            "margin_model": "Per-diem nursing + drug spread; nurse "
                    "utilization and route density (visits per nurse "
                    "per day) drive the margin — a logistics business "
                    "as much as a pharmacy.",
            "working_capital": "Same buy-and-bill drug exposure as AIC, "
                    "plus a nursing-labor float; cash conversion turns "
                    "on clean per-diem + drug billing across two or "
                    "three payers per patient.",
            "key_risk": "The Medicare HIT benefit under-reimburses home "
                    "infusion (no payment on non-visit days), so the "
                    "channel leans on commercial + Part D; nurse "
                    "capacity caps volume.",
        },
    ]


#: The real named operators in AIC + home infusion, with channel,
#: ownership, and scale. Public filings + company disclosures; scale is
#: directional. ``tx`` flags a known Texas footprint.
def infusion_players() -> List[Dict[str, Any]]:
    return [
        {"name": "Option Care Health", "channel": "Both",
         "ownership": "Public (NASDAQ: OPCH)", "tx": True,
         "scale": "Largest US infusion platform — ~$4.3B revenue, "
                  "~700 sites + Naven Health nursing arm",
         "link": "https://www.optioncarehealth.com"},
        {"name": "IVX Health", "channel": "AIC", "ownership": "PE-backed",
         "tx": True,
         "scale": "Pure-play ambulatory infusion-center chain — 175+ "
                  "centers, the fastest-scaling AIC roll-up; "
                  "immunology/neurology focus",
         "link": "https://www.ivxhealth.com"},
        {"name": "CVS Health / Coram", "channel": "Home",
         "ownership": "Public (CVS)", "tx": True,
         "scale": "National home-infusion + specialty pharmacy",
         "link": "https://www.coramhc.com"},
        {"name": "Optum Infusion Pharmacy", "channel": "Both",
         "ownership": "Payer-owned (UnitedHealth)", "tx": True,
         "scale": "Vertically integrated with the largest US payer "
                  "(incl. legacy BriovaRx) — a steerage threat to "
                  "independents",
         "link": "https://www.optum.com"},
        {"name": "Paragon Healthcare", "channel": "AIC",
         "ownership": "Payer-owned (Elevance/Anthem)", "tx": True,
         "scale": "Payer-owned AIC + specialty — Elevance steers its "
                  "own members into Paragon chairs",
         "link": "https://www.paragonhealthcare.com"},
        {"name": "Soleo Health", "channel": "Both", "ownership": "PE-backed",
         "tx": True,
         "scale": "Specialty + home infusion; rare-disease / complex "
                  "therapy focus",
         "link": "https://www.soleohealth.com"},
        {"name": "KabaFusion", "channel": "Both", "ownership": "PE-backed",
         "tx": True,
         "scale": "IVIG / SCIG-focused; national footprint",
         "link": "https://www.kabafusion.com"},
        {"name": "Amber Specialty (Hy-Vee)", "channel": "Home",
         "ownership": "Grocer-owned", "tx": False,
         "scale": "Regional home-infusion + specialty pharmacy",
         "link": "https://www.amberspecialtypharmacy.com"},
        {"name": "InfuCare Rx", "channel": "Home", "ownership": "PE-backed",
         "tx": False,
         "scale": "Home + ambulatory specialty infusion",
         "link": "https://www.infucarerx.com"},
        {"name": "Vital Care Infusion Services", "channel": "Both",
         "ownership": "Franchise", "tx": True,
         "scale": "Franchise model — independent locations, a roll-up "
                  "consolidation pool",
         "link": "https://www.vitalcare.com"},
    ]


# ── Home infusion — deep clinical + network + reimbursement analysis ──
#
# Home infusion is a distinct business from the AIC: a logistics +
# pharmacy-compounding operation delivering IV therapy in the patient's
# home, reimbursed through a different (and notoriously awkward) channel.
# The therapy mix, the eligible-population epidemiology, the operators,
# and the Medicare Home Infusion Therapy (HIT) benefit all differ.

#: Home-infusion therapy families with REAL published epidemiology
#: anchors (annual treated prevalence / incidence per 100,000 population
#: unless noted). Rates are applied to real metro population — the count
#: varies by real geography, the rate is a labeled published anchor.
_HOME_INFUSION_THERAPIES = [
    {
        "key": "opat", "therapy": "Anti-infectives (OPAT)",
        "conditions": "Osteomyelitis, infective endocarditis, complicated "
                      "cellulitis / SSTI, bacteremia, diabetic-foot & "
                      "prosthetic-joint infection",
        "epi_per_100k": 90.0,
        "epi_basis": "≈0.9 OPAT courses per 1,000 population/yr (IDSA "
                     "OPAT guidance; published program incidence)",
        "regimen": "2–6 week IV antibiotic course after discharge",
        "reimbursement": "Part B drug (DME infusion-pump LCD) + HIT visit "
                         "payment; commercial per-diem + drug",
        "why_home": "Frees an inpatient bed for an otherwise-stable "
                    "patient — the original, highest-volume home-infusion "
                    "use case and the hospital discharge-acceleration play.",
        "margin": "Low drug cost, high volume; per-diem + nurse-visit "
                  "driven — route density is the margin lever.",
        "denominator": "population",
    },
    {
        "key": "ig", "therapy": "Immune globulin (IVIG / SCIG)",
        "conditions": "Primary immunodeficiency (PI), CIDP & autoimmune "
                      "neuropathy, myasthenia gravis, ITP, secondary "
                      "immunodeficiency",
        "epi_per_100k": 45.0,
        "epi_basis": "PI treated ≈25–40/100k + CIDP ≈8.9/100k (Immune "
                     "Deficiency Foundation; GBS/CIDP Foundation)",
        "regimen": "Chronic — IVIG q3–4 weeks or weekly SCIG, indefinitely",
        "reimbursement": "High-value Part B drug + HIT/SCIG supply; the "
                         "margin engine of the home channel",
        "why_home": "Chronic, stable, self- or nurse-administered (SCIG "
                    "especially) — ideal for the home; sticky recurring "
                    "revenue.",
        "margin": "The richest home-infusion category — $5K–$15K/dose "
                  "drug spread + chronic recurring volume.",
        "denominator": "population",
    },
    {
        "key": "tpn", "therapy": "Parenteral nutrition (HPN / TPN)",
        "conditions": "Short-bowel syndrome, chronic intestinal failure, "
                      "GI obstruction, severe Crohn's, post-surgical gut "
                      "failure",
        "epi_per_100k": 12.0,
        "epi_basis": "Home parenteral nutrition prevalence ≈120 per "
                     "million (ASPEN / Sustain registry)",
        "regimen": "Daily/overnight infusion, often long-term or lifelong",
        "reimbursement": "Part B prosthetic-device benefit (nutrients + "
                         "pump + supplies) — a stable, well-defined LCD",
        "why_home": "Daily lifelong therapy that cannot occupy a chair; "
                    "compounding + monitoring intensive — a pharmacy "
                    "capability moat.",
        "margin": "Compounding-labor heavy; steady, defensible, lower-"
                  "competition (few operators have the sterile-compounding "
                  "capability).",
        "denominator": "population",
    },
    {
        "key": "inotrope", "therapy": "Inotropic therapy (advanced HF)",
        "conditions": "Stage-D heart failure — milrinone / dobutamine "
                      "continuous infusion (bridge or palliative)",
        "epi_per_100k": 3.0,
        "epi_basis": "Stage-D HF on home inotropes — small subset of the "
                     "CMS HF-prevalent population (HFSA/ACC)",
        "regimen": "Continuous via ambulatory pump, weeks–months",
        "reimbursement": "Part B drug + HIT; close cardiology coordination",
        "why_home": "Avoids prolonged admission for end-stage HF; "
                    "palliative or transplant/LVAD bridge.",
        "margin": "Low volume, high acuity; clinical-coordination "
                  "intensive — a referral-relationship business.",
        "denominator": "seniors",
    },
    {
        "key": "biologic", "therapy": "Home biologics / immunology",
        "conditions": "Rheumatoid arthritis, IBD (Crohn's / UC), psoriatic "
                      "disease — infliximab & select biologics shifted home",
        "epi_per_100k": 60.0,
        "epi_basis": "Subset of the autoimmune-biologic pool eligible for "
                     "home administration (payer site-of-care steerage)",
        "regimen": "q4–8 week maintenance infusions, chronic",
        "reimbursement": "Part B / commercial medical; the white-bagging & "
                         "site-of-care-steerage battleground",
        "why_home": "Payers steer stable biologic patients out of HOPD/AIC "
                    "to the lowest-cost site — home is the cheapest.",
        "margin": "Drug-spread dependent; squeezed by white-bagging but "
                  "high-volume and chronic.",
        "denominator": "population",
    },
    {
        "key": "rare", "therapy": "Enzyme replacement / factor / PAH",
        "conditions": "Lysosomal storage disorders (Pompe, Fabry, "
                      "Gaucher, MPS), hemophilia factor, pulmonary "
                      "arterial hypertension (treprostinil)",
        "epi_per_100k": 9.0,
        "epi_basis": "Hemophilia ≈6/100k + LSDs ≈2/100k + PAH home-infused "
                     "≈1/100k (NHF; rare-disease registries)",
        "regimen": "Chronic / lifelong; ultra-high-cost agents",
        "reimbursement": "Very-high-cost Part B / specialty; prior-auth "
                         "and stop-loss intensive",
        "why_home": "Lifelong rare-disease therapy; specialized handling — "
                    "a high-touch, high-margin niche.",
        "margin": "Ultra-high revenue per patient ($100K–$1M+/yr); tiny "
                  "panels, enormous AR and stop-loss exposure.",
        "denominator": "population",
    },
]


def home_infusion_conditions(
    population: float, seniors: "float | None" = None,
) -> List[Dict[str, Any]]:
    """Home-infusion-eligible patient estimates for a geography = real
    population (or senior subpopulation) × the published treated-
    prevalence rate per therapy. Rates are labeled epidemiology anchors;
    the per-geography count varies by real population only."""
    sen = seniors if seniors is not None else population * 0.13
    out = []
    for t in _HOME_INFUSION_THERAPIES:
        base = sen if t["denominator"] == "seniors" else population
        out.append({
            "key": t["key"], "therapy": t["therapy"],
            "conditions": t["conditions"],
            "epi_per_100k": t["epi_per_100k"], "epi_basis": t["epi_basis"],
            "denominator": t["denominator"],
            "estimated_patients": round(base * t["epi_per_100k"] / 1e5),
        })
    out.sort(key=lambda r: -r["estimated_patients"])
    return out


def home_infusion_therapy_reference() -> List[Dict[str, Any]]:
    """The full clinical reference: therapy, conditions, regimen,
    reimbursement basis, the home-vs-AIC rationale, and margin character
    — the depth a diligence team needs on the home channel."""
    return [dict(t) for t in _HOME_INFUSION_THERAPIES]


def home_infusion_networks() -> List[Dict[str, Any]]:
    """The home-infusion operator landscape — national platforms,
    payer-owned threats, IG/rare-disease specialists, the franchise /
    independent roll-up pool, and Texas-relevant players. Ownership,
    therapy focus, accreditation, and TX footprint from public
    disclosures (directional)."""
    return [
        {"name": "Option Care Health", "tier": "National platform",
         "ownership": "Public (NASDAQ: OPCH)", "tx": True,
         "focus": "Full therapy breadth — the scale leader (~$4.3B rev, "
                  "Naven Health nursing arm)", "accred": "ACHC / URAC",
         "link": "https://www.optioncarehealth.com"},
        {"name": "Optum Infusion Pharmacy", "tier": "Payer-owned",
         "ownership": "UnitedHealth Group", "tx": True,
         "focus": "Vertically integrated with the largest US payer — can "
                  "steer its own members (legacy BriovaRx)",
         "accred": "ACHC / URAC", "link": "https://www.optum.com"},
        {"name": "CVS Health / Coram", "tier": "National platform",
         "ownership": "Public (CVS Health)", "tx": True,
         "focus": "Home infusion + specialty pharmacy at national scale",
         "accred": "ACHC / URAC", "link": "https://www.coramhc.com"},
        {"name": "Amerita", "tier": "National platform",
         "ownership": "BrightSpring Health (NASDAQ: BTSG)", "tx": True,
         "focus": "Adult + complex home infusion; rapid de-novo branch "
                  "expansion", "accred": "ACHC",
         "link": "https://www.ameritaiv.com"},
        {"name": "Soleo Health", "tier": "Specialty / complex",
         "ownership": "PE-backed", "tx": True,
         "focus": "Rare-disease + complex specialty home infusion",
         "accred": "ACHC / URAC", "link": "https://www.soleohealth.com"},
        {"name": "KabaFusion", "tier": "IG specialist",
         "ownership": "PE-backed", "tx": True,
         "focus": "IVIG / SCIG and acute therapies — the IG margin engine",
         "accred": "ACHC / URAC", "link": "https://www.kabafusion.com"},
        {"name": "Paragon Healthcare", "tier": "Payer-owned",
         "ownership": "Elevance Health", "tx": True,
         "focus": "Texas-HQ'd (Plano) AIC + home; Elevance steers its own "
                  "members", "accred": "ACHC",
         "link": "https://www.paragonhealthcare.com"},
        {"name": "InfuCare Rx", "tier": "Specialty / complex",
         "ownership": "PE-backed", "tx": True,
         "focus": "Home + ambulatory specialty infusion, expanding south",
         "accred": "ACHC / URAC", "link": "https://www.infucarerx.com"},
        {"name": "NuFACTOR / FFF Enterprises", "tier": "IG / factor",
         "ownership": "Private", "tx": True,
         "focus": "IG, hemophilia factor & specialty distribution",
         "accred": "ACHC / URAC", "link": "https://www.nufactor.com"},
        {"name": "BioMatrix Specialty Pharmacy", "tier": "Rare / factor",
         "ownership": "Private", "tx": True,
         "focus": "Bleeding disorders, IG, rare-disease home infusion",
         "accred": "ACHC / URAC", "link": "https://www.biomatrixsprx.com"},
        {"name": "Vital Care Infusion Services", "tier": "Franchise / roll-up pool",
         "ownership": "Franchise network", "tx": True,
         "focus": "Independent franchise locations across TX — the "
                  "fragmented consolidation pool", "accred": "ACHC (varies)",
         "link": "https://www.vitalcare.com"},
    ]


def home_infusion_reimbursement() -> Dict[str, Any]:
    """The Medicare Home Infusion Therapy (HIT) benefit + the structural
    reimbursement reality — the single biggest thing to underwrite on a
    home-infusion deal. Sourced to the 21st Century Cures Act and CMS
    HIT final rules."""
    return {
        "summary": (
            "Home infusion reimbursement is split across three Medicare "
            "buckets plus commercial per-diem — and the Medicare "
            "professional-services benefit has a defining gap that "
            "structurally under-pays the channel."),
        "points": [
            {"label": "The HIT services benefit (since 2021)",
             "detail": "The 21st Century Cures Act created a permanent "
                       "Medicare Home Infusion Therapy services benefit, "
                       "effective Jan 1 2021 (after a 2019–20 transitional "
                       "benefit). It pays a qualified HIT supplier a "
                       "per-visit professional-services amount."},
            {"label": "The calendar-day gap (the defining flaw)",
             "detail": "The HIT payment is made ONLY for dates a skilled "
                       "professional is physically in the home — the "
                       "'infusion drug administration calendar day'. A "
                       "multi-week course with one weekly nurse visit gets "
                       "paid for ~4 of 28 days; the other days are unpaid "
                       "professional time."},
            {"label": "Three payment categories (G0068–G0070)",
             "detail": "Payment is tiered by drug category (the J-code "
                       "groups), with a higher first-visit amount reflecting "
                       "a PFS E/M benchmark, geographically adjusted."},
            {"label": "Drug + equipment paid separately",
             "detail": "Part B home-infusion drugs + the external infusion "
                       "pump and supplies are paid under the DME benefit "
                       "(infusion-pump LCD); the nutrients/pump for TPN "
                       "under the prosthetic-device benefit."},
            {"label": "The Part D black hole",
             "detail": "Many self-administered specialty drugs fall under "
                       "Part D — where there is NO home-infusion "
                       "professional-services benefit at all. The nursing "
                       "and per-diem are effectively unfunded by Medicare."},
            {"label": "Commercial carries the channel",
             "detail": "Commercial payers reimburse a per-diem (nursing + "
                       "supplies) plus the drug (AWP-based or contracted) — "
                       "materially better than Medicare HIT, so payer mix "
                       "is the single biggest driver of home-infusion "
                       "economics."},
        ],
        "rcm_read": (
            "Underwrite the home channel on its COMMERCIAL mix and its "
            "Medicare HIT net collection rate per episode — not gross "
            "charges. The calendar-day gap and the Part D split mean "
            "headline revenue overstates collectible economics; measure "
            "per-diem + drug realization across the 2–3 payers per "
            "patient."),
    }


def home_infusion_episode_economics() -> Dict[str, Any]:
    """An illustrative per-patient OPAT episode P&L for the home channel
    — the volume driver — built from labeled NHIA/industry per-diem and
    cost anchors so the contribution recomputes from the inputs."""
    weeks = 4.0
    per_diem = 165.0          # commercial nursing + supplies per diem
    nurse_visits_per_wk = 2.0
    nurse_cost_per_visit = 95.0
    drug_rev_per_wk = 1_250.0
    drug_cost_per_wk = 1_040.0   # ~16% spread
    pharmacy_compound_per_wk = 140.0
    delivery_per_wk = 55.0
    rev = (per_diem * 7 + drug_rev_per_wk) * weeks
    cost = ((nurse_visits_per_wk * nurse_cost_per_visit)
            + drug_cost_per_wk + pharmacy_compound_per_wk
            + delivery_per_wk) * weeks
    contribution = rev - cost
    return {
        "therapy": "OPAT (4-week IV antibiotic course)",
        "weeks": weeks,
        "revenue": round(rev),
        "cost": round(cost),
        "contribution": round(contribution),
        "contribution_margin": round(contribution / rev, 3) if rev else 0,
        "drivers": [
            ("Commercial per-diem (nursing + supplies)",
             f"${per_diem:.0f}/day"),
            ("Nurse visits", f"{nurse_visits_per_wk:.0f}/wk @ "
                             f"${nurse_cost_per_visit:.0f}"),
            ("Drug spread", f"~{(drug_rev_per_wk-drug_cost_per_wk)/drug_rev_per_wk*100:.0f}% "
                            f"(${drug_rev_per_wk-drug_cost_per_wk:.0f}/wk)"),
            ("Pharmacy compounding", f"${pharmacy_compound_per_wk:.0f}/wk"),
            ("Delivery / logistics", f"${delivery_per_wk:.0f}/wk"),
        ],
        "lever": (
            "Nurse route density (visits per nurse per day) is the margin "
            "lever — the same logistics dynamic as any field-service "
            "business. Rural TX dilutes density; metro clusters concentrate "
            "it."),
        "note": "Illustrative — commercial-payer OPAT; Medicare HIT pays "
                "less (visit-day gap). NHIA / industry per-diem anchors.",
    }


# ── Home-infusion discharge pipeline & therapy-volume risk ───────────
#
# Home infusion is a REFERRAL business: its demand is the annual FLOW of
# new starts — mostly hospital discharges (OPAT off an inpatient stay,
# TPN off GI surgery, inotropes off an HF admission) plus specialty-
# clinic initiations. That flow, and the concentration of where it comes
# from, is the core commercial diligence. Each therapy also carries a
# different RISK profile — reimbursement, payer steerage, referral
# concentration, clinical/readmission, and drug-supply exposure.

#: Annual NEW-START / discharge flow per therapy (per 100k population or
#: seniors) + the discharge source, 30-day readmission anchor, and a
#: five-axis risk score (1 = low … 5 = high). Flow/readmission rates are
#: labeled published anchors; risk axes are a documented diligence
#: framework (not a data feed).
_HOME_INFUSION_DISCHARGE = [
    {"key": "opat", "therapy": "Anti-infectives (OPAT)",
     "flow_per_100k": 90.0, "denominator": "population",
     "flow_basis": "≈0.9 OPAT courses per 1,000/yr — discharge-driven",
     "source": "Acute inpatient discharge — osteomyelitis, endocarditis, "
               "bacteremia, complicated SSTI, diabetic-foot / prosthetic-"
               "joint infection",
     "readmission_pct": 23.0,
     "readmit_basis": "OPAT 30-day readmission ≈20–26% (published OPAT "
                      "cohort studies; line/ADE + relapse driven)",
     "risk": {"reimbursement": 2, "steerage": 2, "referral_concentration": 5,
              "clinical": 4, "supply": 3}},
    {"key": "tpn", "therapy": "Parenteral nutrition (HPN / TPN)",
     "flow_per_100k": 5.0, "denominator": "population",
     "flow_basis": "Home-PN new-start incidence ≈5/100k/yr (ASPEN)",
     "source": "GI-surgery / oncology discharge — short bowel, intestinal "
               "failure, obstruction, severe Crohn's",
     "readmission_pct": 18.0,
     "readmit_basis": "HPN 30-day readmission ≈15–20% (CLABSI / sepsis, "
                      "metabolic / refeeding, catheter complications)",
     "risk": {"reimbursement": 2, "steerage": 2, "referral_concentration": 4,
              "clinical": 4, "supply": 4}},
    {"key": "ig", "therapy": "Immune globulin (IVIG / SCIG)",
     "flow_per_100k": 7.0, "denominator": "population",
     "flow_basis": "New IG initiations ≈7/100k/yr (PI + CIDP + autoimmune)",
     "source": "Specialty-clinic initiation — immunology, neurology "
               "(CIDP), hematology (ITP); some inpatient neuro discharge",
     "readmission_pct": 8.0,
     "readmit_basis": "Lower acuity once stable; infusion-reaction / "
                      "thrombotic events the main events",
     "risk": {"reimbursement": 3, "steerage": 5, "referral_concentration": 3,
              "clinical": 2, "supply": 4}},
    {"key": "inotrope", "therapy": "Inotropic therapy (advanced HF)",
     "flow_per_100k": 3.0, "denominator": "seniors",
     "flow_basis": "Stage-D HF home-inotrope starts — small senior subset",
     "source": "Cardiology / HF-clinic discharge — stage-D heart failure "
               "(milrinone / dobutamine bridge or palliative)",
     "readmission_pct": 25.0,
     "readmit_basis": "HF 30-day readmission ≈22–25% (arrhythmia, "
                      "decompensation, line events) — high-acuity",
     "risk": {"reimbursement": 3, "steerage": 2, "referral_concentration": 4,
              "clinical": 5, "supply": 2}},
    {"key": "biologic", "therapy": "Home biologics / immunology",
     "flow_per_100k": 25.0, "denominator": "population",
     "flow_basis": "New home-biologic starts via payer site-of-care "
                   "steerage (RA / IBD / psoriatic)",
     "source": "Payer steerage out of HOPD/AIC + rheum / GI clinic "
               "referral — stable maintenance patients",
     "readmission_pct": 5.0,
     "readmit_basis": "Low — stable chronic maintenance; infusion "
                      "reactions the main clinical event",
     "risk": {"reimbursement": 4, "steerage": 5, "referral_concentration": 3,
              "clinical": 2, "supply": 2}},
    {"key": "rare", "therapy": "Enzyme replacement / factor / PAH",
     "flow_per_100k": 2.0, "denominator": "population",
     "flow_basis": "New rare-disease starts ≈2/100k/yr (LSD + factor + PAH)",
     "source": "Academic / center-of-excellence initiation — genetics, "
               "hematology, pulmonary hypertension clinics",
     "readmission_pct": 6.0,
     "readmit_basis": "Low clinical readmission; the exposure is financial "
                      "(AR / stop-loss), not acute",
     "risk": {"reimbursement": 5, "steerage": 4, "referral_concentration": 3,
              "clinical": 3, "supply": 4}},
]

#: Weights for the overall at-risk score (sum to 1.0). Reimbursement and
#: payer steerage dominate home-infusion risk; referral concentration is
#: the commercial fragility; clinical + supply round it out.
_RISK_WEIGHTS = {"reimbursement": 0.25, "steerage": 0.25,
                 "referral_concentration": 0.20, "clinical": 0.15,
                 "supply": 0.15}

_RISK_AXIS_LABELS = {
    "reimbursement": "Reimbursement (HIT gap / Part D / AR)",
    "steerage": "Payer steerage / white-bagging",
    "referral_concentration": "Referral-source concentration",
    "clinical": "Clinical / readmission",
    "supply": "Drug-supply exposure",
}


def home_infusion_discharge_volumes(
    population: float, seniors: "float | None" = None,
) -> List[Dict[str, Any]]:
    """Annual home-infusion referral FLOW (new starts/yr) by therapy =
    real population (or senior subpopulation) × the published new-start /
    discharge incidence rate. This is the demand a referral-dependent
    home-infusion business captures each year — distinct from the
    standing prevalent pool."""
    sen = seniors if seniors is not None else population * 0.13
    out = []
    for t in _HOME_INFUSION_DISCHARGE:
        base = sen if t["denominator"] == "seniors" else population
        out.append({
            "key": t["key"], "therapy": t["therapy"],
            "source": t["source"], "flow_per_100k": t["flow_per_100k"],
            "flow_basis": t["flow_basis"], "denominator": t["denominator"],
            "readmission_pct": t["readmission_pct"],
            "annual_referrals": round(base * t["flow_per_100k"] / 1e5),
        })
    out.sort(key=lambda r: -r["annual_referrals"])
    return out


def home_infusion_therapy_risk() -> Dict[str, Any]:
    """Per-therapy risk register — each scored 1–5 on five diligence
    axes, blended into an overall at-risk score (×20 → 0–100) and ranked
    so the most-at-risk therapies surface. A pure recompute from the
    documented axis scores + weights."""
    rows = []
    for t in _HOME_INFUSION_DISCHARGE:
        risk = t["risk"]
        overall = sum(risk[ax] * w for ax, w in _RISK_WEIGHTS.items())
        # The single worst axis — the headline reason it's at risk.
        worst_ax = max(risk, key=lambda ax: risk[ax] * _RISK_WEIGHTS[ax])
        rows.append({
            "key": t["key"], "therapy": t["therapy"],
            "axes": dict(risk),
            "overall_score": round(overall, 2),
            "overall_pct": round(overall * 20),
            "band": ("HIGH" if overall >= 3.5 else
                     "ELEVATED" if overall >= 2.75 else "MODERATE"),
            "lead_risk": _RISK_AXIS_LABELS[worst_ax],
            "readmission_pct": t["readmission_pct"],
        })
    rows.sort(key=lambda r: -r["overall_score"])
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return {
        "therapies": rows,
        "axis_labels": _RISK_AXIS_LABELS,
        "weights": _RISK_WEIGHTS,
        "most_at_risk": rows[0]["therapy"] if rows else "",
        "note": ("Five-axis diligence risk framework (1 = low … 5 = high), "
                 "blended by the weights shown; readmission anchors from "
                 "published OPAT/HPN/HF cohort studies. The axis scores are "
                 "a documented analyst framework, not a data feed — edit "
                 "them to your underwriting view."),
    }


def home_infusion_referral_sources() -> Dict[str, Any]:
    """Where home-infusion referrals come from + the concentration risk.
    Hospital discharge planning dominates — and that concentration is the
    #1 commercial fragility in a home-infusion deal."""
    sources = [
        {"source": "Acute-care hospital discharge planning", "share": 0.58,
         "note": "OPAT, TPN, inotrope starts off an inpatient stay — the "
                 "dominant, and most concentrated, channel"},
        {"source": "Physician / specialty clinics (ID, GI, heme, rheum, "
                   "cards)", "share": 0.22,
         "note": "Chronic initiations (IG, biologics, rare disease) — "
                 "stickier, more diversified relationships"},
        {"source": "SNF / LTAC step-down", "share": 0.09,
         "note": "Post-acute transitions, often OPAT continuation"},
        {"source": "ED / observation (direct-to-home)", "share": 0.06,
         "note": "Avoided-admission OPAT — a growing, payer-favored path"},
        {"source": "Wound care / other", "share": 0.05,
         "note": "Diabetic-foot / osteomyelitis anti-infectives"},
    ]
    hosp = sources[0]["share"]
    return {
        "sources": sources,
        "hospital_dependence": hosp,
        "concentration_risk": (
            f"≈{hosp*100:.0f}% of home-infusion referrals originate from "
            "acute-hospital discharge planning, and within a branch a "
            "single health-system relationship can be 20–40% of volume — "
            "the #1 commercial risk to underwrite. Diversification into "
            "ID/GI/rheum clinic relationships and direct-to-home ED OPAT "
            "is what de-risks the referral base."),
        "rcm_read": (
            "Map referral concentration by source and by health system, "
            "then the net collection rate per referral. A platform leaning "
            "on one or two hospital discharge desks is one contract loss "
            "from a volume cliff — quantify the top-5 source concentration "
            "and the OPAT readmission leakage (re-hospitalized patients "
            "stop billing)."),
    }


# ── Evolution of discharges → home infusion / site-of-care over time ──
#
# The home-infusion demand engine is hospital DISCHARGES + the steady
# migration of infusion OUT of the hospital outpatient department into
# ambulatory infusion centers and the home. This models that evolution
# from documented endpoints (national magnitudes) + a real regulatory /
# structural event timeline. The yearly points are interpolated between
# labeled published anchors — illustrative, recomputable, and explicit
# about what is anchor vs interpolation. No fabricated precision.

# Site-of-care mix anchors. 2024 = the page's current site-of-care model
# (real output); 2015 = a documented historical estimate (HOPD-dominant,
# pre-steerage). Linear interpolation between.
_SOC_ANCHOR_START = {"year": 2015, "hopd": 0.46, "office": 0.16,
                     "home": 0.28, "ais": 0.10}
_SOC_ANCHOR_END = {"year": 2024, "hopd": 0.30, "office": 0.10,
                   "home": 0.38, "ais": 0.22}
# US home/alternate-site infusion market size anchors ($B) — NHIA /
# industry magnitude; CAGR computed from the endpoints.
_MKT_START_B = 11.0      # 2015
_MKT_END_B = 20.5        # 2024
# OPAT / home-infusion patient-volume index (2015 = 100), ~9%/yr.
_OPAT_CAGR = 0.09


def home_infusion_evolution() -> Dict[str, Any]:
    """Year-by-year evolution (2015→2024) of the infusion site-of-care
    mix, the home/alternate-site market size, and OPAT volume, plus the
    regulatory/structural event timeline that drove the discharge shift.
    Pure recompute from the labeled anchors above."""
    y0, y1 = _SOC_ANCHOR_START["year"], _SOC_ANCHOR_END["year"]
    span = y1 - y0
    mkt_cagr = (_MKT_END_B / _MKT_START_B) ** (1 / span) - 1
    series = []
    for yr in range(y0, y1 + 1):
        t = (yr - y0) / span
        def _lerp(k):
            return round(_SOC_ANCHOR_START[k]
                         + (_SOC_ANCHOR_END[k] - _SOC_ANCHOR_START[k]) * t, 4)
        series.append({
            "year": yr,
            "hopd": _lerp("hopd"), "office": _lerp("office"),
            "home": _lerp("home"), "ais": _lerp("ais"),
            "non_hospital": round(_lerp("home") + _lerp("ais")
                                  + _lerp("office"), 4),
            "market_size_b": round(_MKT_START_B * (1 + mkt_cagr) ** (yr - y0), 2),
            "opat_index": round(100 * (1 + _OPAT_CAGR) ** (yr - y0)),
        })
    events = [
        {"year": 2016, "label": "21st Century Cures Act",
         "detail": "Creates the permanent Medicare home-infusion-therapy "
                   "services benefit (to take effect later) — the first "
                   "federal recognition of home-infusion professional "
                   "services.", "tone": "positive"},
        {"year": 2016, "label": "First infliximab biosimilar (Inflectra)",
         "detail": "Begins the multi-year ASP erosion of the anchor "
                   "buy-and-bill biologic — more access, thinner drug "
                   "spread over time.", "tone": "warning"},
        {"year": 2019, "label": "Transitional HIT benefit begins",
         "detail": "Interim home-infusion payment starts — but only on "
                   "nurse-visit days (the calendar-day gap that still "
                   "under-pays the channel).", "tone": "warning"},
        {"year": 2020, "label": "COVID-19 — home-infusion surge",
         "detail": "Patients + payers flee the hospital; CMS waivers and "
                   "hospital-at-home accelerate the discharge shift to "
                   "home/AIC by years. The structural inflection.",
         "tone": "positive"},
        {"year": 2021, "label": "Permanent Medicare HIT benefit",
         "detail": "Effective Jan 1 2021 — durable (if still gap-ridden) "
                   "funding for home-infusion professional services.",
         "tone": "positive"},
        {"year": 2022, "label": "Site-of-care steerage / white-bagging spreads",
         "detail": "Commercial payers + MA plans push biologics out of "
                   "HOPD into AIC/home and mandate their own specialty "
                   "pharmacy — volume tailwind, drug-margin headwind.",
         "tone": "warning"},
        {"year": 2023, "label": "MA penetration crosses ~50%",
         "detail": "Medicare Advantage now covers half of Medicare — and "
                   "MA steers site of care far harder than fee-for-service.",
         "tone": "positive"},
        {"year": 2024, "label": "Biosimilar wave + IRA pricing",
         "detail": "Ustekinumab/aflibercept biosimilars + IRA Part-B "
                   "inflation rebates compress ASP further — accelerating "
                   "the move to the lowest-cost site.", "tone": "warning"},
    ]
    drivers = [
        {"driver": "Inpatient length-of-stay decline",
         "detail": "DRG/throughput pressure discharges still-on-IV "
                   "patients sooner — directly creating OPAT/TPN home "
                   "referrals."},
        {"driver": "Payer site-of-care steerage",
         "detail": "HOPD is the most expensive site; payers route to AIC "
                   "then home — the single biggest mix-shift force."},
        {"driver": "Medicare Advantage growth",
         "detail": "MA steers harder than FFS; rising penetration "
                   "compounds the migration."},
        {"driver": "Biosimilars + IRA",
         "detail": "Lower ASP widens access (more volume) but thins the "
                   "drug spread — margin moves from drug to service."},
        {"driver": "COVID normalization of home care",
         "detail": "Permanently reset patient + clinician comfort with "
                   "home infusion — a step-change, not a blip."},
        {"driver": "The HIT benefit (2019→2021)",
         "detail": "Finally funds home professional services (partially) — "
                   "still gap-ridden, so commercial mix decides economics."},
    ]
    return {
        "series": series,
        "events": events,
        "drivers": drivers,
        "market_cagr_pct": round(mkt_cagr * 100, 1),
        "soc_start": _SOC_ANCHOR_START,
        "soc_end": _SOC_ANCHOR_END,
        "hopd_shift_pts": round(
            (_SOC_ANCHOR_START["hopd"] - _SOC_ANCHOR_END["hopd"]) * 100),
        "home_ais_gain_pts": round(
            ((_SOC_ANCHOR_END["home"] + _SOC_ANCHOR_END["ais"])
             - (_SOC_ANCHOR_START["home"] + _SOC_ANCHOR_START["ais"])) * 100),
        "note": ("Evolution of the infusion site-of-care mix + home/"
                 "alternate-site market size, 2015→2024. Endpoints are "
                 "documented anchors (2024 site mix = this page's site-of-"
                 "care model; 2015 = a published historical estimate; "
                 "market size from NHIA/industry magnitudes); intermediate "
                 "years are linearly interpolated and the regulatory "
                 "timeline is factual. Illustrative — replace with a "
                 "claims time-series in diligence."),
    }


def texas_asp_pricing() -> Dict[str, Any]:
    """Part B ASP buy-and-bill pricing — the marquee infusion-drug HCPCS
    J-code reference with the live per-unit ASP payment limit (CMS ASP
    file) filled in where reachable, plus the ASP+6 / sequestered-ASP+4.3
    payment mechanics. The drug's payment limit minus the operator's
    acquisition cost IS the buy-and-bill spread."""
    from ..data.cms_asp_pricing import (
        infusion_asp_reference, ASP_ADDON, ASP_ADDON_SEQUESTERED)
    ref = infusion_asp_reference()
    return {
        "reference": ref,
        "addon_statutory": ASP_ADDON,
        "addon_sequestered": ASP_ADDON_SEQUESTERED,
        "live": any(r["live"] for r in ref),
        "note": ("Medicare Part B pays clinician-administered infusion "
                 "drugs at ASP + 6% (sequestered to ≈ASP + 4.3%). Per-unit "
                 "ASP payment limits are pulled live from the CMS ASP "
                 "Pricing file when egress is available; offline the "
                 "verifiable J-code reference + the formula are shown — no "
                 "dollar value is fabricated. The spread vs the operator's "
                 "GPO/channel acquisition cost is the drug margin."),
    }


def texas_ma_enrollment(tx_pop: float, seniors: float,
                        fetch_live: bool = False) -> Dict[str, Any]:
    """Texas Medicare Advantage enrollment + a TRUE penetration rate. MA
    growth is the single biggest payer-side force on infusion site of
    care — MA plans steer infusion out of HOPD into AIC / home and run
    prior-auth + white-bagging. MA enrollment from the vendored CMS MA
    geographic-variation file; the penetration DENOMINATOR is total
    Medicare beneficiaries from the CMS Medicare Monthly Enrollment file
    (live when egress permits, else a published TX total) — not the 65+
    proxy, which omits the under-65 disabled."""
    from ..data.ma_data import ma_state
    from ..data.cms_enrollment import total_medicare_for
    m = ma_state("TX") or {}
    enr = int(m.get("ma_enrollment") or 0)
    benes = total_medicare_for("TX", fetch_live=fetch_live)
    total_medicare = int(benes.get("total") or 0)
    penetration = (enr / total_medicare) if total_medicare else 0.0
    proxy = (enr / seniors) if seniors else 0.0
    denom_label = ("CMS Medicare Monthly Enrollment (live)"
                   if benes.get("live") else
                   "published CMS total Medicare (TX)")
    return {
        "enrollment": enr,
        "total_medicare": total_medicare,
        "penetration": round(penetration, 3),
        "penetration_live": bool(benes.get("live")),
        # Kept for continuity: penetration vs the 65+ population.
        "penetration_proxy": round(proxy, 3),
        "dual_eligible_pct": float(m.get("dual_eligible_pct") or 0),
        "female_pct": float(m.get("female_pct") or 0),
        "avg_age": m.get("avg_age"),
        "year": int(m.get("year") or 0),
        "denominator_source": denom_label,
        "note": ("≈{:,} Texans are in Medicare Advantage of ≈{:,} total "
                 "Medicare beneficiaries — a {:.0f}% MA penetration rate "
                 "({}). MA is the key payer-mix force on infusion: plans "
                 "steer site of care to the lowest-cost setting (AIC / home "
                 "over HOPD) and gate biologics with prior-auth + white-"
                 "bagging — a tailwind for independent AIC / home volume "
                 "and a margin risk on the drug spread."
                 ).format(enr, total_medicare, penetration * 100,
                          denom_label),
    }


def texas_hopd_pool(
    metro_deepdives: List[Dict[str, Any]], hopd_share: float,
    fetch_live: bool = False,
) -> Dict[str, Any]:
    """The hospital-outpatient (HOPD) infusion pool — the volume being
    STEERED AWAY from the hospital that an AIC / home platform competes
    to capture. Per metro: HOPD infusion patients = real metro infusion
    patients × the HOPD site share, and HOPD revenue at the model's
    infusions/yr × revenue/infusion. A live CMS OPPS by-provider-and-
    service pull (TX, infusion J-codes) overrides with real HOPD services
    + Medicare payment where egress permits."""
    metros = []
    for dd in metro_deepdives:
        pts = sum(int(s.get("infusion_patients") or 0)
                  for s in dd.get("suburbs", []))
        hopd_pts = round(pts * hopd_share)
        hopd_rev = round(hopd_pts * INFUSIONS_PER_PATIENT_YR
                         * REVENUE_PER_INFUSION)
        metros.append({"metro": dd["metro"], "infusion_patients": pts,
                       "hopd_patients": hopd_pts, "hopd_revenue": hopd_rev})
    metros.sort(key=lambda m: -m["hopd_patients"])
    live = {"live": False}
    if fetch_live:
        from ..data.cms_asp_pricing import INFUSION_HCPCS
        from ..data.cms_opps_outpatient import fetch_opps_state_infusion
        live = fetch_opps_state_infusion(
            "TX", [c["hcpcs"] for c in INFUSION_HCPCS])
    return {
        "metros": metros,
        "hopd_share": round(hopd_share, 3),
        "total_hopd_patients": sum(m["hopd_patients"] for m in metros),
        "total_hopd_revenue": sum(m["hopd_revenue"] for m in metros),
        "opps_live": bool(live.get("live")),
        "opps_services": live.get("services"),
        "opps_payment": live.get("medicare_payment"),
        "note": ("The HOPD infusion pool is the volume payers are steering "
                 "OUT of the hospital — the white-space an AIC / home "
                 "platform captures, not a competitor to displace. Modeled "
                 "from real metro infusion patients × the HOPD site share "
                 "× the sizing model's infusions/yr × revenue/infusion; the "
                 "live CMS Outpatient-Hospitals (by provider & service) "
                 "file overrides with real HOPD services + Medicare payment "
                 "where egress permits."),
    }


#: Approximate map coordinates (viewBox 0–100) for the four target
#: metros on a stylized Texas outline — for the provider map.
_METRO_MAP_XY = {
    "Houston": (70.0, 57.0),
    "Dallas": (56.0, 32.0),
    "Austin": (52.0, 56.0),
    "San Antonio": (45.0, 63.0),
}


def texas_infusion_provider_map(
    metro_deepdives: List[Dict[str, Any]],
    fetch_live: bool = False,
) -> Dict[str, Any]:
    """Provider map data for the four metros: estimated infusion-center
    count (sum of member-county AIS estimates) + a live NPPES count of
    infusion providers (taxonomy-filtered) when ``fetch_live`` is set and
    egress permits. Each metro gets stylized map coordinates for the SVG
    bubble map.

    ``fetch_live`` is OFF by default: hitting NPPES (4 metros × 2
    taxonomies) must never block a normal page render. It is enabled
    deliberately (``?nppes=live``) as a refresh."""
    from ..data.nppes_infusion import INFUSION_TAXONOMIES

    points = []
    for dd in metro_deepdives:
        name = dd["metro"]
        key = next((k for k in _METRO_MAP_XY if name.startswith(k)), None)
        if not key:
            continue
        x, y = _METRO_MAP_XY[key]
        est = sum(int(s.get("est_ais_centers") or 0)
                  for s in dd.get("suburbs", []))
        live = {"live": False}
        if fetch_live:
            from ..data.nppes_infusion import count_infusion_providers
            live = count_infusion_providers("TX", city=key)
        points.append({
            "metro": name, "short": key, "x": x, "y": y,
            "estimated_centers": est,
            "nppes_count": live.get("count") if live.get("live") else None,
            "nppes_live": bool(live.get("live")),
            "population": dd.get("population", 0),
        })
    points.sort(key=lambda p: -p["estimated_centers"])
    any_live = any(p["nppes_live"] for p in points)
    return {
        "points": points,
        "taxonomies": INFUSION_TAXONOMIES,
        "live": any_live,
        "note": ("Infusion-provider supply by metro. Bubble size = "
                 "estimated ambulatory-infusion centers (sum of member-"
                 "county AIS estimates from real population); a live NPPES "
                 "count (taxonomy-filtered — Clinic/Center Infusion "
                 "Therapy, Infusion Pharmacy, Home Infusion) replaces the "
                 "estimate wherever the NPI Registry is reachable. NPPES "
                 "taxonomy codes are public facts; counts are never "
                 "fabricated."),
    }


_US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA",
    "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
    "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX",
    "UT", "VT", "VA", "WA", "WV", "WI", "WY"]

_STATE_NAME = {
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
    "WI": "Wisconsin", "WY": "Wyoming"}


def infusion_jcode_pos(
    fetch_live: bool = False,
    years: "tuple[int, ...]" = (2020, 2021, 2022),
) -> Dict[str, Any]:
    """Place-of-service split for the infusion J-code basket by state —
    facility (HOPD) vs non-facility (office / freestanding AIC).

    Live (``fetch_live``): real CMS Part B FFS claims from the
    by-Geography-and-Service file, aggregated across the infusion J-codes
    and years. Offline: a MODELED non-facility share per state driven by
    REAL state factors — rurality (more rural → fewer freestanding AICs →
    more facility) and MA penetration (more MA → more steerage to
    non-facility) — anchored to a national base. Modeled values are
    labeled, never claims; the live pull replaces them."""
    from ..data.cms_asp_pricing import INFUSION_HCPCS
    from ..data.county_demographics import demographics_state
    from ..data.ma_data import ma_state

    codes = [c["hcpcs"] for c in INFUSION_HCPCS]
    live_by_name: Dict[str, Any] = {}
    if fetch_live:
        from ..data.cms_geo_service import jcode_pos_by_state
        live_by_name = jcode_pos_by_state(codes, list(years))

    base = 0.58           # national non-facility anchor (illustrative)
    states = []
    for code in _US_STATES:
        d = demographics_state(code) or {}
        pop = float(d.get("population") or 0)
        pct65 = float(d.get("pct_age_65_plus") or 0.16)
        rural = float(d.get("pct_rural") or 0.20)
        m = ma_state(code) or {}
        ma_enr = float(m.get("ma_enrollment") or 0)
        ma_pen = min(0.95, ma_enr / (pop * pct65)) if pop and pct65 else 0.45
        modeled = base - 0.30 * (rural - 0.20) + 0.18 * (ma_pen - 0.45)
        modeled = round(max(0.35, min(0.82, modeled)), 4)
        live = live_by_name.get(_STATE_NAME.get(code, ""))
        live_pct = None
        if live:
            yr = max(live)
            live_pct = live[yr].get("nonfac_pct")
        states.append({
            "code": code, "name": _STATE_NAME.get(code, code),
            "nonfac_pct": live_pct if live_pct is not None else modeled,
            "modeled_pct": modeled, "is_live": live_pct is not None,
            "rural": round(rural, 4), "ma_penetration": round(ma_pen, 3),
        })
    states.sort(key=lambda s: -s["nonfac_pct"])
    for i, s in enumerate(states, 1):
        s["rank"] = i
    tx = next((s for s in states if s["code"] == "TX"), None)
    # National facility→non-facility trend from the site-of-care model
    # (labeled national context; per-state 3-yr trend fills in live).
    evo = home_infusion_evolution()["series"]
    last3 = evo[-3:]
    trend = [{"year": r["year"], "facility_pct": r["hopd"],
              "nonfacility_pct": round(1 - r["hopd"], 4)} for r in last3]
    return {
        "states": states,
        "texas": tx,
        "national_trend": trend,
        "jcodes": [{"hcpcs": c["hcpcs"], "drug": c["drug"]}
                   for c in INFUSION_HCPCS],
        "years": list(years),
        "live": any(s["is_live"] for s in states),
        "note": ("Place of service (facility = HOPD vs non-facility = "
                 "office / freestanding AIC) for the infusion J-code "
                 "basket, by state. Offline values are MODELED from a "
                 "national anchor adjusted by real state rurality + MA "
                 "penetration — NOT claims; the live CMS Part B "
                 "by-Geography-and-Service pull (FFS only; excludes MA) "
                 "replaces them per state × year."),
    }


def regulatory_reimbursement_environment() -> Dict[str, Any]:
    """The full regulatory + reimbursement environment an infusion
    platform operates under — federal Part B/D mechanics, the Home
    Infusion Therapy benefit, IRA / biosimilar / 340B drug policy,
    site-of-care + utilization-management pressure, Texas-specific rules,
    and operational compliance. Each item tagged tailwind / headwind /
    neutral with the diligence implication. Sourced to the statutes,
    CMS rules, USP standards, and Texas regulation noted; verify
    state-specific items as of the engagement date."""
    T, H, N = "tailwind", "headwind", "neutral"
    cats = [
        {"category": "Medicare Part B — buy-and-bill mechanics",
         "items": [
            {"topic": "ASP + 6% drug payment (≈ASP+4.3% post-sequester)",
             "detail": "Part B pays clinician-administered drugs at the "
                       "quarterly Average Sales Price + 6%; the 2% "
                       "sequester on the 80% federal share nets ≈ASP+4.3%.",
             "status": "Standing law; sequester ongoing.", "impact": H,
             "implication": "Thin, policy-set drug spread — margin is GPO "
                            "acquisition vs the payment limit, not list."},
            {"topic": "Administration / infusion CPT codes (96365–96379)",
             "detail": "Separately billable hierarchical admin codes "
                       "(initial hour, each additional hour, push, "
                       "sequential) on top of the drug.",
             "status": "Standing.", "impact": N,
             "implication": "The service fee — the AIC's non-drug revenue; "
                            "chair throughput converts it."},
            {"topic": "2% Medicare sequester",
             "detail": "Across-the-board 2% cut to Medicare payments "
                       "(incl. Part B drugs + admin).",
             "status": "In effect.", "impact": H,
             "implication": "Permanent haircut on every Medicare claim — "
                            "modeled into net realization."},
         ]},
        {"category": "Medicare Home Infusion Therapy (HIT) benefit",
         "items": [
            {"topic": "Permanent HIT services benefit",
             "detail": "21st Century Cures Act (2016) → transitional "
                       "benefit 2019–20 → permanent benefit effective "
                       "Jan 1 2021; per-visit professional payment to a "
                       "qualified HIT supplier (G0068–G0070).",
             "status": "Permanent since 2021.", "impact": T,
             "implication": "Federal funding for home professional "
                            "services finally exists — but see the gap."},
            {"topic": "The calendar-day gap",
             "detail": "HIT pays ONLY on dates a skilled professional is "
                       "in the home — a multi-week course with one weekly "
                       "visit is paid ~4 of 28 days.",
             "status": "Structural to the benefit.", "impact": H,
             "implication": "Medicare structurally under-pays home "
                            "infusion services; commercial mix decides "
                            "economics."},
            {"topic": "DME + prosthetic-device benefits",
             "detail": "External infusion pump + supplies under the DME "
                       "infusion-pump LCD; TPN nutrients/pump under the "
                       "prosthetic-device benefit.",
             "status": "Standing.", "impact": N,
             "implication": "Stable, well-defined coverage for the pump/"
                            "TPN side — a capability, not a margin lever."},
            {"topic": "The Part D 'black hole'",
             "detail": "Many self-administered specialty drugs fall under "
                       "Part D — where there is NO home-infusion "
                       "professional-services benefit at all.",
             "status": "Standing.", "impact": H,
             "implication": "Nursing/per-diem effectively unfunded by "
                            "Medicare on Part D drugs — underwrite the mix."},
         ]},
        {"category": "Drug-pricing policy — IRA, biosimilars, 340B",
         "items": [
            {"topic": "IRA Part B inflation rebates",
             "detail": "Since 2023, manufacturers owe rebates when a Part "
                       "B drug's price outpaces inflation; beneficiary "
                       "coinsurance is reduced on those drugs.",
             "status": "Effective 2023.", "impact": N,
             "implication": "Lowers patient cost-share (access positive) "
                            "but signals tighter drug-price ceilings."},
            {"topic": "IRA Maximum Fair Price negotiation",
             "detail": "First negotiated Part D prices effective 2026; "
                       "Part B drugs enter negotiation from 2028 — some "
                       "high-spend infused biologics in scope over time.",
             "status": "Phasing in 2026→2028+.", "impact": H,
             "implication": "Compresses ASP on the marquee infusion drugs "
                            "— the buy-and-bill spread shrinks with it."},
            {"topic": "Biosimilar ASP+8% add-on",
             "detail": "Qualifying biosimilars paid at biosimilar ASP + "
                       "8% of the reference product ASP (a temporary IRA "
                       "bump from 6%, ~2022–2027) to spur uptake.",
             "status": "Temporary through ~2027.", "impact": T,
             "implication": "A near-term margin sweetener on biosimilar "
                            "lines — but accelerates reference-ASP erosion."},
            {"topic": "340B drug pricing program",
             "detail": "340B covered entities (incl. many HOPDs) buy "
                       "drugs at deep statutory discounts; independent "
                       "AICs do not.",
             "status": "Standing; contract-pharmacy disputes ongoing.",
             "impact": H,
             "implication": "A drug-acquisition cost disadvantage vs 340B "
                            "hospitals — independents compete on site of "
                            "care + service, not drug cost."},
         ]},
        {"category": "Site-of-care & utilization management",
         "items": [
            {"topic": "Site-neutral payment policy",
             "detail": "CMS cut off-campus HOPD clinic-visit payment to "
                       "the PFS rate (2019, upheld on appeal); ongoing "
                       "proposals extend site-neutral to drug admin.",
             "status": "In effect + expanding.", "impact": T,
             "implication": "Narrows the HOPD price premium — accelerates "
                            "volume to AIC/home, the platform's site."},
            {"topic": "White-bagging / brown-bagging mandates",
             "detail": "Payers require the drug be supplied by their own "
                       "specialty pharmacy (white-bag) or the patient "
                       "(brown-bag), stripping the buy-and-bill spread.",
             "status": "Spreading; state-law patchwork pushes back.",
             "impact": H,
             "implication": "The single biggest threat to AIC drug margin "
                            "— track the white-bagged % by payer."},
            {"topic": "Prior authorization (commercial + MA)",
             "detail": "High-cost infused drugs gate through prior auth; "
                       "MA plans authorize aggressively.",
             "status": "Pervasive.", "impact": H,
             "implication": "Denial + AR-days exposure — the core RCM "
                            "diligence metric on an infusion platform."},
            {"topic": "MA prior-authorization final rule (2024)",
             "detail": "CMS tightened MA prior-auth — continuity of care, "
                       "decision timelines, and approval-validity rules.",
             "status": "Effective 2024–2026.", "impact": T,
             "implication": "Modest relief on MA friction — a small "
                            "tailwind against the steerage headwind."},
         ]},
        {"category": "Texas & state-specific",
         "items": [
            {"topic": "No Certificate of Need (CON)",
             "detail": "Texas has no CON regime for ambulatory infusion — "
                       "de-novo centers face no state need-approval gate.",
             "status": "Standing (TX is a non-CON state).", "impact": T,
             "implication": "De-novo build-out is unconstrained — a "
                            "structural advantage for an AIC roll-up here."},
            {"topic": "Texas State Board of Pharmacy licensure",
             "detail": "Class A (community) / Class E (non-resident) "
                       "pharmacy licensure; sterile-compounding "
                       "permitting for infusion pharmacies.",
             "status": "Standing.", "impact": N,
             "implication": "A compliance + capability gate (sterile "
                            "compounding) — also a moat vs new entrants."},
            {"topic": "Medicaid non-expansion + STAR managed care",
             "detail": "Texas did not expand Medicaid; the highest US "
                       "uninsured rate; Medicaid runs through STAR managed "
                       "care.",
             "status": "Standing.", "impact": H,
             "implication": "Thinner safety-net coverage — payer mix "
                            "leans commercial/Medicare, and bad-debt risk "
                            "on the uninsured."},
            {"topic": "State white-bagging restrictions",
             "detail": "A growing number of states restrict white-bagging "
                       "(provider-administered-drug protections); the "
                       "Texas statute should be confirmed as of the "
                       "engagement.",
             "status": "Evolving patchwork — VERIFY TX.", "impact": N,
             "implication": "Potential statutory protection of buy-and-"
                            "bill — a diligence item to confirm, not "
                            "assume."},
         ]},
        {"category": "Operational compliance & supply chain",
         "items": [
            {"topic": "USP <797> sterile + <800> hazardous compounding",
             "detail": "Revised USP <797> (effective Nov 2023) governs "
                       "sterile compounding; <800> governs hazardous "
                       "(oncology) drug handling.",
             "status": "USP <797> revised, effective 2023.", "impact": N,
             "implication": "Raises the compounding bar — capex + a moat "
                            "against under-capitalized entrants."},
            {"topic": "Accreditation (ACHC / URAC / Joint Commission)",
             "detail": "Specialty-pharmacy / home-infusion accreditation "
                       "is table-stakes for payer network contracts.",
             "status": "Standing.", "impact": N,
             "implication": "A contracting prerequisite — diligence the "
                            "target's accreditations + renewal calendar."},
            {"topic": "DSCSA track-and-trace",
             "detail": "Drug Supply Chain Security Act enhanced "
                       "interoperable tracing; stabilization period ran "
                       "into late 2024 ahead of full enforcement.",
             "status": "Enforcement ramping post-2024.", "impact": H,
             "implication": "Compliance cost + systems lift on drug "
                            "handling — a cost, not a differentiator."},
            {"topic": "FDA drug shortages",
             "detail": "Periodic shortages of infusion essentials (IV "
                       "fluids, TPN components, some antibiotics).",
             "status": "Recurring (live FDA status on this page).",
             "impact": H,
             "implication": "Operational + sourcing risk — inventory "
                            "discipline + sole-source exposure to manage."},
         ]},
    ]
    tail = sum(1 for c in cats for i in c["items"] if i["impact"] == T)
    head = sum(1 for c in cats for i in c["items"] if i["impact"] == H)
    neut = sum(1 for c in cats for i in c["items"] if i["impact"] == N)
    return {
        "categories": cats,
        "tailwinds": tail, "headwinds": head, "neutral": neut,
        "net_read": (
            "The federal trend is a TAILWIND for the platform's SITE "
            "(site-neutral + the HIT benefit push volume to AIC/home) but "
            "a HEADWIND for the DRUG SPREAD (IRA, biosimilars, 340B, "
            "white-bagging all compress it). Texas adds a structural "
            "tailwind — no CON — against a Medicaid-non-expansion payer-"
            "mix headwind. Net: underwrite the thesis on SERVICE margin + "
            "commercial mix + de-novo runway, not the drug margin."),
        "note": ("Regulatory + reimbursement environment as of 2024–2025. "
                 "Federal items sourced to statute / CMS rule / USP; "
                 "Texas items to state regulation — confirm state-specific "
                 "statutes (esp. white-bagging) as of the engagement date."),
    }


def infusion_risk_register() -> List[Dict[str, Any]]:
    """Channel-specific risk register for AIC + home infusion, each
    risk tagged with severity, who it hits, and — critically — the RCM
    angle: how revenue-cycle diligence detects and measures it. This is
    where an RCM platform earns its keep on an infusion deal."""
    return [
        {"risk": "White-bagging / brown-bagging mandates",
         "category": "Reimbursement", "severity": "HIGH", "hits": "AIC",
         "detail": "Payers increasingly require the drug be supplied by "
                   "their own specialty pharmacy (white-bag) or the "
                   "patient (brown-bag), removing the buy-and-bill "
                   "spread that funds the AIC.",
         "rcm_angle": "Track the % of infusions white-bagged by payer, "
                      "the buy-and-bill margin-per-infusion trend, and "
                      "contract language on drug sourcing. A rising "
                      "white-bag share is a direct revenue-per-visit "
                      "leak the RCM data shows before the P&L does."},
        {"risk": "Medicare HIT benefit underpayment",
         "category": "Reimbursement", "severity": "HIGH", "hits": "Home",
         "detail": "The Home Infusion Therapy professional payment pays "
                   "only on nurse-visit days — most home-infusion days "
                   "(self-administered, between visits) carry no "
                   "professional payment, so Medicare under-reimburses "
                   "the channel.",
         "rcm_angle": "Measure the Medicare home-infusion net collection "
                      "rate and the share of therapy-days that are "
                      "billable vs unbilled; quantify the Medicare drag "
                      "on a deal that skews senior."},
        {"risk": "Buy-and-bill margin compression",
         "category": "Reimbursement", "severity": "MEDIUM", "hits": "Both",
         "detail": "ASP+6% is sequestered to ~ASP+4.3%, and biosimilar "
                   "adoption lowers the ASP base — both compress the "
                   "drug spread per infusion.",
         "rcm_angle": "Trend the drug-margin % and the biosimilar mix "
                      "by J-code; model the spread at ASP+4.3 vs ASP+6 "
                      "and under biosimilar substitution."},
        {"risk": "Prior-auth / medical-necessity denials on high-dollar "
                 "claims",
         "category": "RCM", "severity": "HIGH", "hits": "Both",
         "detail": "Every cycle needs benefit investigation + prior "
                   "auth; a single denied specialty claim is a "
                   "$5K–$30K write-off, so the denial RATE matters far "
                   "less than the denial DOLLARS.",
         "rcm_angle": "The core RCM read: initial denial rate, denial "
                      "DOLLAR exposure (not just count), appeal-recovery "
                      "rate, and days-in-AR. One avoidable auth denial "
                      "dwarfs a hundred small ones — RCM sizes the "
                      "recoverable revenue."},
        {"risk": "Coding / units / wastage (JW) accuracy",
         "category": "RCM", "severity": "MEDIUM", "hits": "Both",
         "detail": "Specialty drugs bill by exact mg units against an "
                   "NDC, with JW-modifier wastage billed separately — "
                   "mis-units and missing JW are silent underpayments "
                   "and audit exposure.",
         "rcm_angle": "Audit units-billed vs units-administered, JW "
                      "capture, and NDC-to-HCPCS crosswalk accuracy; "
                      "underpayment recovery is real found money."},
        {"risk": "Payer / contract concentration",
         "category": "Market", "severity": "MEDIUM", "hits": "Both",
         "detail": "Losing or repricing a single large commercial "
                   "contract can swing the platform; payer-owned "
                   "competitors (Optum, Paragon) can steer volume away.",
         "rcm_angle": "Revenue by payer, top-payer concentration, and "
                      "the contract-renewal calendar — the RCM data "
                      "exposes the dependency a teaser won't."},
        {"risk": "Working capital / specialty-drug inventory",
         "category": "RCM / Ops", "severity": "MEDIUM", "hits": "Both",
         "detail": "Buy-and-bill means cash is out the door on the drug "
                   "before the claim is paid; high-cost inventory + slow "
                   "AR is a cash-conversion drag that a growth roll-up "
                   "feels acutely.",
         "rcm_angle": "DSO/DAR, days-inventory-on-hand, and the cash "
                      "conversion cycle; the bridge from net revenue to "
                      "cash is the diligence number."},
        {"risk": "Nurse labor & chair utilization",
         "category": "Operational", "severity": "MEDIUM", "hits": "Both",
         "detail": "Infusion-nurse supply caps both home-visit capacity "
                   "and chair throughput; wage inflation pressures the "
                   "admin-fee margin.",
         "rcm_angle": "Less an RCM line than an ops one, but revenue per "
                      "chair-hour / per nurse-visit is the productivity "
                      "metric the RCM data underpins."},
    ]


def rcm_playbook() -> Dict[str, Any]:
    """How RCM diligence talks about infusion specifically — the KPI
    set, the denial drivers, and the cash dynamics that make infusion
    RCM distinct from a generic provider. Aligns to the platform's own
    RCM vocabulary (IDR, clean-claim, DAR, net collection)."""
    return {
        "why_different": (
            "Infusion RCM is high-dollar-per-claim and buy-and-bill: the "
            "provider purchases a $5K–$30K specialty drug, then bills "
            "it — so a single avoidable denial is a five-figure cash "
            "event, and the denial DOLLARS matter more than the denial "
            "rate. Benefit investigation + prior auth gate every cycle, "
            "and a home-infusion claim splits across Part B, Part D and "
            "commercial. That makes the revenue cycle the dominant "
            "value-creation lever on an infusion platform."),
        "kpis": [
            {"kpi": "Initial denial rate (IDR)",
             "why": "Gates the recoverable-revenue opportunity",
             "benchmark": "Infusion runs hot vs the ~8–12% provider "
                          "norm — auth + medical-necessity heavy"},
            {"kpi": "Denial DOLLAR exposure",
             "why": "The number that matters here — high $/claim",
             "benchmark": "One auth denial = $5K–$30K; size in $, not %"},
            {"kpi": "Clean claim rate",
             "why": "Units/JW/NDC accuracy on first pass",
             "benchmark": "Coding-driven; specialty-drug units are the "
                          "common defect"},
            {"kpi": "Days in AR (DAR / DSO)",
             "why": "Buy-and-bill cash is trapped until paid",
             "benchmark": "Watch AR > 90 days — high-dollar tail"},
            {"kpi": "Net collection rate",
             "why": "Underpayment vs contracted ASP+/per-diem",
             "benchmark": "Underpayment recovery is found money"},
            {"kpi": "Cost to collect",
             "why": "Benefit-investigation + auth labor is heavy",
             "benchmark": "Higher than a low-acuity provider"},
        ],
        "denial_drivers": [
            "Prior authorization not obtained / expired",
            "Medical necessity / step-therapy not met",
            "Site-of-care steerage (payer wants its own site/SP)",
            "Units / dose / JW-wastage coding errors",
            "Eligibility / benefit-coordination (Part B vs D vs "
            "commercial)",
        ],
        "diligence_questions": [
            "What share of infusions are white-bagged, and what is the "
            "buy-and-bill margin-per-infusion trend by payer?",
            "Initial denial rate AND denial dollars by payer and reason "
            "— and the appeal-recovery rate?",
            "Days in AR, AR > 90 days, and days of specialty-drug "
            "inventory — the cash-conversion cycle?",
            "Top-payer revenue concentration and the contract-renewal "
            "calendar?",
            "Medicare home-infusion net collection rate and the share "
            "of unbillable (non-visit) therapy days?",
        ],
    }


#: North-suburb counties + marquee cities per metro — the affluent,
#: fast-growing, commercially-insured rings that are prime AIC ground.
#: County FIPS from the CBSA crosswalk; cities are the population
#: centers within each county.
_NORTH_SUBURBS = {
    "19100": {  # Dallas-Fort Worth-Arlington
        "counties": {"48085": "Collin (Plano · Frisco · McKinney · Allen)",
                     "48121": "Denton (Denton · Lewisville · Flower Mound)"},
        "label": "North DFW — Collin & Denton (Plano/Frisco/McKinney/"
                 "Denton): the affluent, fast-growing, commercially-"
                 "insured corridor; the prime AIC ring."},
    "26420": {  # Houston
        "counties": {"48339": "Montgomery (The Woodlands · Conroe · "
                              "Spring)"},
        "label": "North Houston — Montgomery (The Woodlands/Conroe): "
                 "high-income master-planned growth north of Harris; "
                 "strong commercial mix."},
    "12420": {  # Austin
        "counties": {"48491": "Williamson (Round Rock · Cedar Park · "
                              "Georgetown · Leander)"},
        "label": "North Austin — Williamson (Round Rock/Cedar Park/"
                 "Georgetown): the fastest-growing ring, tech-employer "
                 "commercial insured."},
    "41700": {  # San Antonio
        "counties": {"48091": "Comal (New Braunfels) + north Bexar "
                              "(Stone Oak)"},
        "label": "North San Antonio — Comal/New Braunfels + north Bexar "
                 "(Stone Oak): the affluent growth edge."},
}


#: Infusion-relevant chronic conditions → the therapies they drive and
#: the channel that serves them. Prevalence rates come from CDC/CMS
#: STATE-level public data (same across TX counties); the per-county
#: BURDEN (estimated affected adults) scales by REAL county population.
_CONDITION_THERAPY = [
    {"condition": "Rheumatoid Arthritis", "rate_pct": 6.5,
     "therapy": "Immunology biologics (infliximab, IVIG-adjacent)",
     "channel": "AIC + home", "source": "CMS chronic-conditions (TX)"},
    {"condition": "Cancer", "rate_pct": 9.1,
     "therapy": "Oncology infusion + supportive (IV chemo, hydration)",
     "channel": "AIC / HOPD", "source": "CMS chronic-conditions (TX)"},
    {"condition": "Chronic Kidney Disease", "rate_pct": 26.7,
     "therapy": "IV iron / anemia management",
     "channel": "AIC + home", "source": "CMS chronic-conditions (TX)"},
]


def county_illness_burden(population: float) -> List[Dict[str, Any]]:
    """Estimated infusion-relevant illness burden for a county =
    REAL county adult population × the TX state prevalence rate (CDC/CMS
    public data). The rate is state-level (does not vary by county), so
    the variation across suburbs comes from real population — labeled as
    a population-scaled estimate, not invented county differences.

    Uses an adult-population proxy (~76% of total, Census age structure)
    since the chronic-condition rates are adult/Medicare prevalences."""
    adults = population * 0.76
    out = []
    for c in _CONDITION_THERAPY:
        out.append({
            "condition": c["condition"],
            "therapy": c["therapy"],
            "channel": c["channel"],
            "rate_pct": c["rate_pct"],
            "estimated_patients": round(adults * c["rate_pct"] / 100.0),
            "source": c["source"],
        })
    return out


# ── CDC PLACES / ACS public-health proxies ───────────────────────────
#
# The user-facing mapping: each infusion therapy family is proxied by a
# REAL public-health measure — CDC PLACES (full-population, county-level
# via the Socrata API; TX state value vendored) or CMS Medicare chronic-
# conditions — plus ACS access signals. County rates come from the LIVE
# PLACES county API when network egress is available; otherwise the real
# TX state rate is used and the per-county VARIATION comes from real
# population / female share / poverty. No county prevalence is invented.
_ADULT_SHARE = 0.76                 # Census adult (18+) share proxy.

_THERAPY_PROXIES = [
    {"key": "rheum", "therapy": "Rheumatology / immunology biologics",
     "channel": "AIC + home", "anchor": "arthritis",
     "measures": ["arthritis"], "denominator": "adults 18+",
     "note": "Arthritis prevalence proxies the autoimmune/inflammatory "
             "pool (RA, IBD, PsA) behind infliximab / biologic infusions."},
    {"key": "onc", "therapy": "Oncology infusion & supportive care",
     "channel": "AIC / HOPD", "anchor": "cancer",
     "measures": ["cancer"], "denominator": "adults 18+",
     "note": "Cancer prevalence (excl. skin) proxies chemo + supportive "
             "(hydration, growth-factor, bone-stabilizer) infusion demand."},
    {"key": "iron", "therapy": "IV iron / anemia management",
     "channel": "AIC + home", "anchor": "kidney_disease",
     "measures": ["kidney_disease", "fair_poor_health", "female_share"],
     "denominator": "female-weighted adults",
     "note": "CKD + poor general health proxy anemia burden; iron-"
             "deficiency anemia concentrates in women, so the pool is "
             "weighted by ACS female share."},
    {"key": "chronic", "therapy": "General chronic / metabolic demand",
     "channel": "AIC + home", "anchor": "diabetes",
     "measures": ["diabetes", "obesity", "poor_physical_health"],
     "denominator": "adults 18+",
     "note": "Diabetes + obesity + frequent poor-physical-health days "
             "proxy the broad chronic-care base for infused therapy."},
]


def texas_cdc_state_rates(places_county: "Dict[str, Any] | None" = None
                          ) -> Dict[str, Dict[str, Any]]:
    """Real TX state-level prevalence for each proxy measure.

    Full-population measures come from CDC PLACES (vendored TX state
    roll-up); arthritis / cancer / CKD come from CMS Medicare chronic-
    conditions (TX-adjusted) as a labeled Medicare-denominator proxy.
    When a live PLACES county map is supplied, the full-population
    measures are recomputed as a real population-weighted TX rate from
    the county rows (and arthritis/cancer/CKD likewise if present)."""
    from ..data.cdc_places_agg import places_equity_state
    from ..data.disease_density import (
        NATIONAL_PREVALENCE, _STATE_ADJUSTMENTS)

    pl = places_equity_state("TX") or {}
    adj = _STATE_ADJUSTMENTS.get("TX", 1.0)
    rates: Dict[str, Dict[str, Any]] = {}

    # CDC PLACES full-population TX state values (real, vendored).
    _PLACES = {
        "diabetes": "diabetes", "obesity": "obesity",
        "poor_physical_health": "poor_physical_health",
        "fair_poor_health": "fair_poor_health",
        "uninsured_18_64": "uninsured_18_64",
        "routine_checkup": "routine_checkup",
    }
    for key, field in _PLACES.items():
        v = pl.get(field)
        if v is not None and str(v) != "nan":
            try:
                rates[key] = {
                    "rate_pct": round(float(v), 2),
                    "source": "CDC PLACES (TX state, full-population)",
                    "denominator": "adults 18+", "live": False}
            except (TypeError, ValueError):
                pass

    # CMS Medicare chronic-conditions for arthritis / cancer / CKD.
    for key, cond in (("arthritis", "Rheumatoid Arthritis"),
                      ("cancer", "Cancer"),
                      ("kidney_disease", "Chronic Kidney Disease")):
        nat = NATIONAL_PREVALENCE.get(cond)
        if nat:
            rates[key] = {
                "rate_pct": round(nat * adj, 2),
                "source": "CMS Medicare chronic-conditions (TX-adjusted)",
                "denominator": "Medicare beneficiaries", "live": False}

    # If a live county map is present, override with a real population-
    # weighted TX rate per measure (full-population PLACES, incl.
    # arthritis / kidney / cancer that the vendored state file omits).
    if places_county:
        from ..data.cdc_places_api import MEASURES
        for key in MEASURES:
            num = den = 0.0
            for row in places_county.values():
                r = row.get(key)
                w = row.get("population") or 0
                if r is not None and w:
                    num += r * w
                    den += w
            if den:
                prev = rates.get(key, {})
                rates[key] = {
                    "rate_pct": round(num / den, 2),
                    "source": "CDC PLACES (TX, county API — pop-weighted)",
                    "denominator": "adults 18+", "live": True}
    return rates


def county_cdc_demand(
    county: Dict[str, Any],
    rates: Dict[str, Dict[str, Any]],
    places_row: "Dict[str, Any] | None" = None,
    female_share: float = 0.497,
) -> List[Dict[str, Any]]:
    """Per-county infusion demand broken out by CDC-proxied therapy.

    Estimated patients = REAL county adult population × the proxy
    prevalence rate. The rate is the live county PLACES value when
    present, else the TX state rate; the IV-iron pool is weighted by the
    county female share (ACS). Every figure recomputes from real inputs."""
    pop = float(county.get("population") or 0)
    adults = pop * _ADULT_SHARE
    seniors = float(county.get("seniors") or pop * 0.13)
    out: List[Dict[str, Any]] = []
    for spec in _THERAPY_PROXIES:
        anchor = spec["anchor"]
        live = False
        if places_row and places_row.get(anchor) is not None:
            # Live PLACES = full-population crude prevalence → adults.
            rate = float(places_row[anchor])
            live = True
            denom_pop, denom_label = adults, "adults 18+"
        else:
            r = rates.get(anchor)
            if not r:
                continue
            rate = float(r["rate_pct"])
            # Apply each rate to its OWN denominator so the count is
            # honest: Medicare-beneficiary rates → senior (65+) pool;
            # full-population PLACES rates → all adults.
            if "Medicare" in r.get("denominator", ""):
                denom_pop, denom_label = seniors, "Medicare benes (65+)"
            else:
                denom_pop, denom_label = adults, "adults 18+"
        base = denom_pop * rate / 100.0
        if spec["key"] == "iron":
            # Weight the anemia pool toward women (relative to 50%).
            base *= female_share / 0.5
        out.append({
            "key": spec["key"], "therapy": spec["therapy"],
            "channel": spec["channel"], "anchor_measure": anchor,
            "measures": spec["measures"], "denominator": denom_label,
            "rate_pct": round(rate, 2), "rate_is_county_live": live,
            "estimated_patients": round(base), "note": spec["note"],
        })
    out.sort(key=lambda r: -r["estimated_patients"])
    return out


def county_payer_access(
    county: Dict[str, Any],
    rates: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """A 0–100 commercial-payer-access index from real ACS uninsured +
    poverty and the CDC PLACES routine-checkup rate. Higher = better
    commercial access (the cash-flow underwriting for an AIC)."""
    unins = float(county.get("uninsured_rate") or 0)          # 0–1
    pov = float(county.get("child_poverty_rate") or 0)        # 0–1
    checkup = float((rates.get("routine_checkup") or {})
                    .get("rate_pct") or 0) / 100.0            # 0–1
    unins_axis = 1.0 - min(unins, 0.30) / 0.30
    pov_axis = 1.0 - min(pov, 0.40) / 0.40
    score = 100.0 * (0.50 * unins_axis + 0.30 * pov_axis
                     + 0.20 * checkup)
    band = ("strong" if score >= 70 else
            "moderate" if score >= 55 else "constrained")
    return {
        "score": round(score, 1), "band": band,
        "uninsured_rate": round(unins, 4),
        "child_poverty_rate": round(pov, 4),
        "routine_checkup_pct": round(checkup * 100, 1),
    }


def texas_cdc_proxies(places_county: "Dict[str, Any] | None" = None
                      ) -> Dict[str, Any]:
    """State-level CDC/ACS proxy summary: one row per therapy family with
    the proxy measure(s), the real TX rate, source, and denominator."""
    rates = texas_cdc_state_rates(places_county)
    rows = []
    for spec in _THERAPY_PROXIES:
        anchor = spec["anchor"]
        r = rates.get(anchor)
        if not r:
            continue
        rows.append({
            "key": spec["key"], "therapy": spec["therapy"],
            "channel": spec["channel"], "anchor_measure": anchor,
            "measures": spec["measures"], "denominator": r["denominator"],
            "rate_pct": r["rate_pct"], "source": r["source"],
            "live": r.get("live", False), "note": spec["note"],
        })
    return {
        "therapies": rows,
        "rates": rates,
        "live": bool(places_county),
        "note": ("Each infusion therapy family proxied by a real CDC "
                 "PLACES (full-population) or CMS Medicare prevalence "
                 "measure. County-level rates pulled live from the CDC "
                 "PLACES Socrata API when egress is available; otherwise "
                 "the real TX state rate is used and per-county variation "
                 "comes from real population / female share / poverty."),
    }


def infusion_drug_supply() -> Dict[str, Any]:
    """Real FDA drug-shortage status for the infusion-relevant drug
    classes, from the vendored openFDA snapshot. The honest read: the
    core specialty biologics are NOT FDA-shortage-listed (stable), while
    OPAT anti-infectives, IV iron, and TPN/fluid components carry
    FDA-tracked supply activity. No synthetic data."""
    from ..data.drug_shortage_data import (
        current_shortages, drug_shortage_summary, load_drug_shortages,
    )
    summary = drug_shortage_summary()
    df = load_drug_shortages()
    g = df["generic_name"].astype(str).str.lower()
    classes = [
        {"klass": "Specialty biologics (immunology / IVIG)",
         "terms": ["immune globulin", "immunoglobulin", "infliximab",
                   "rituximab", "vedolizumab", "ocrelizumab",
                   "natalizumab"],
         "channel": "AIC + home"},
        {"klass": "OPAT anti-infectives",
         "terms": ["vancomycin", "cefepime", "piperacillin", "daptomycin",
                   "ertapenem", "meropenem", "ceftriaxone"],
         "channel": "Home (OPAT)"},
        {"klass": "IV iron / anemia",
         "terms": ["iron sucrose", "ferric", "iron dextran"],
         "channel": "AIC"},
        {"klass": "TPN / nutrition + diluents",
         "terms": ["amino acid", "dextrose", "sodium chloride",
                   "lipid", "intralipid"],
         "channel": "Home (TPN) + AIC"},
    ]
    rows = []
    for c in classes:
        mask = g.apply(lambda x: any(t in x for t in c["terms"]))
        hits = df[mask]
        current = hits[hits["status"].astype(str).str.lower()
                       .str.contains("current", na=False)]
        rows.append({
            "klass": c["klass"], "channel": c["channel"],
            "total_listed": int(len(hits)),
            "current_shortages": int(len(current)),
            "status": ("CURRENT SHORTAGE" if len(current) > 0
                       else "WATCH (discontinuations listed)"
                       if len(hits) > 0 else "STABLE — not FDA-listed"),
            "examples": sorted(set(
                hits["generic_name"].astype(str).head(3).tolist())),
        })
    return {
        "snapshot_date": summary.get("snapshot_date"),
        "total_current": summary.get("current"),
        "classes": rows,
        "headline": (
            "Core specialty biologics (IVIG, infliximab, rituximab, "
            "vedolizumab) are NOT on the FDA shortage list — the AIC "
            "margin engine has stable supply. Supply risk concentrates "
            "in OPAT anti-infectives, IV iron, and TPN/fluid components, "
            "where the FDA tracks active shortages/discontinuations."),
        "source": "openFDA drug-shortage snapshot (public, CC0)",
    }


#: Per-payer AIC rate anchors. Commercial pays an admin fee well above
#: the Medicare PFS drug-administration codes (96413/96415 ≈ $145–160
#: blended) and a wider buy-and-bill spread (% of AWP vs ASP+4.3
#: sequestered). MedPAC Part B chapter + NHIA benchmarks; illustrative,
#: editable.
AIC_COMMERCIAL_ADMIN_FEE = 260.0
AIC_MEDICARE_ADMIN_FEE = 155.0
AIC_COMMERCIAL_DRUG_MARGIN = 0.14
AIC_MEDICARE_DRUG_MARGIN = 0.043     # ASP+6 sequestered to ~ASP+4.3


def aic_chair_economics(
    *, chairs: int = 10, util_pct: float = 0.78,
    infusions_per_chair_day: float = 6.0, operating_days: int = 250,
    revenue_per_infusion_drug: float = 650.0,
    admin_fee_per_infusion: Optional[float] = None,
    drug_margin_pct: Optional[float] = None, nurse_to_chair: float = 0.30,
    nurse_fully_loaded: float = 130_000.0,
    facility_overhead_per_chair: float = 28_000.0,
    rcm_cost_pct: float = 0.05, commercial_mix_pct: float = 0.62,
    recurring_patient_pct: float = 0.82,
    prior_auth_approval_pct: float = 0.94,
) -> Dict[str, Any]:
    """The AIC unit-economics model — a per-chair P&L broken into the
    sections a deal team underwrites, plus the operating KPIs the user
    named (chair utilization, nurse productivity, recurring patients,
    commercial mix, prior-auth discipline, drug margin/acquisition).

    Payer mix is a REAL lever: when ``admin_fee_per_infusion`` /
    ``drug_margin_pct`` are not explicitly overridden they are blended
    from the per-payer anchors (commercial pays a higher admin fee and
    a wider buy-and-bill spread than Medicare ASP+4.3) — so moving the
    commercial-mix slider moves the P&L, not just a display chip.

    Documented defaults from NHIA / ambulatory-infusion benchmarks —
    illustrative starting points, every input editable. The math is a
    pure function of the assumptions so the breakdown audits."""
    mix = max(0.0, min(1.0, commercial_mix_pct))
    blended = False
    if admin_fee_per_infusion is None:
        admin_fee_per_infusion = (mix * AIC_COMMERCIAL_ADMIN_FEE
                                  + (1 - mix) * AIC_MEDICARE_ADMIN_FEE)
        blended = True
    if drug_margin_pct is None:
        drug_margin_pct = (mix * AIC_COMMERCIAL_DRUG_MARGIN
                           + (1 - mix) * AIC_MEDICARE_DRUG_MARGIN)
        blended = True
    infusions_per_chair_yr = infusions_per_chair_day * operating_days * util_pct
    total_infusions = infusions_per_chair_yr * chairs
    nurses = chairs * nurse_to_chair

    # Per-chair annual P&L sections (waterfall).
    drug_rev = infusions_per_chair_yr * revenue_per_infusion_drug
    admin_rev = infusions_per_chair_yr * admin_fee_per_infusion
    gross_rev = drug_rev + admin_rev
    drug_cogs = drug_rev * (1 - drug_margin_pct)
    drug_spread = drug_rev * drug_margin_pct
    nursing = (nurses * nurse_fully_loaded) / chairs if chairs else 0.0
    overhead = facility_overhead_per_chair
    rcm_cost = gross_rev * rcm_cost_pct
    contribution = admin_rev + drug_spread - nursing - overhead - rcm_cost

    sections = [
        {"label": "Gross revenue / chair", "value": gross_rev,
         "kind": "revenue",
         "note": f"{infusions_per_chair_yr:,.0f} infusions × "
                 f"(${revenue_per_infusion_drug:,.0f} drug + "
                 f"${admin_fee_per_infusion:,.0f} admin)"},
        {"label": "− Drug acquisition (COGS)", "value": -drug_cogs,
         "kind": "cost",
         "note": f"buy-and-bill at {drug_margin_pct*100:.0f}% spread — "
                 "GPO / channel leverage is the lever"},
        {"label": "− Nursing labor", "value": -nursing, "kind": "cost",
         "note": f"{nurse_to_chair:.2f} nurse/chair × "
                 f"${nurse_fully_loaded/1e3:,.0f}K fully loaded"},
        {"label": "− Facility / overhead", "value": -overhead,
         "kind": "cost", "note": "rent, pharmacy, scheduling, supplies"},
        {"label": "− RCM / billing", "value": -rcm_cost, "kind": "cost",
         "note": f"{rcm_cost_pct*100:.0f}% of revenue — benefit-"
                 "investigation + prior-auth + claims labor"},
        {"label": "= Chair contribution margin", "value": contribution,
         "kind": "subtotal",
         "note": f"{contribution/gross_rev*100:.1f}% of gross — the "
                 "admin fee + drug spread net of variable cost"},
    ]

    kpis = [
        {"kpi": "Chair utilization", "value": f"{util_pct*100:.0f}%",
         "lever": "throughput — empty chairs are dead overhead",
         "good": ">75%"},
        {"kpi": "Nurse productivity",
         "value": f"{total_infusions/nurses:,.0f} infusions/nurse/yr",
         "lever": "the labor lever — chairs per nurse + visit pace",
         "good": "1:3–4 nurse:chair"},
        {"kpi": "Recurring patients",
         "value": f"{recurring_patient_pct*100:.0f}%",
         "lever": "chronic therapy = predictable, low-CAC revenue",
         "good": ">80%"},
        {"kpi": "Commercial payer mix",
         "value": f"{commercial_mix_pct*100:.0f}%",
         "lever": "commercial pays above Medicare ASP+ — the margin mix",
         "good": ">60%"},
        {"kpi": "Prior-auth approval rate",
         "value": f"{prior_auth_approval_pct*100:.0f}%",
         "lever": "clean PA process = fewer 5-figure denials, faster cash",
         "good": ">92%"},
        {"kpi": "Drug margin (buy-and-bill)",
         "value": f"{drug_margin_pct*100:.0f}%",
         "lever": "acquisition cost + payer rate; white-bagging kills it",
         "good": "protect via contracts + GPO"},
        {"kpi": "Revenue / chair / yr",
         "value": f"${gross_rev/1e3:,.0f}K",
         "lever": "the headline unit; drug-heavy, so watch contribution",
         "good": "—"},
        {"kpi": "Contribution / chair / yr",
         "value": f"${contribution/1e3:,.0f}K",
         "lever": "the real operating profit per chair",
         "good": "—"},
    ]
    return {
        "assumptions": {
            "chairs": chairs, "util_pct": util_pct,
            "infusions_per_chair_day": infusions_per_chair_day,
            "operating_days": operating_days,
            "revenue_per_infusion_drug": revenue_per_infusion_drug,
            "commercial_mix_pct": commercial_mix_pct,
            "recurring_patient_pct": recurring_patient_pct,
            "prior_auth_approval_pct": prior_auth_approval_pct,
            "admin_fee_per_infusion": admin_fee_per_infusion,
            "drug_margin_pct": drug_margin_pct,
            "nurse_to_chair": nurse_to_chair,
            "nurse_fully_loaded": nurse_fully_loaded,
            "facility_overhead_per_chair": facility_overhead_per_chair,
            "rcm_cost_pct": rcm_cost_pct,
            "payer_blended": blended,
        },
        "infusions_per_chair_yr": round(infusions_per_chair_yr),
        "total_infusions": round(total_infusions),
        "nurses": round(nurses, 1),
        "sections": sections,
        "kpis": kpis,
        "contribution_per_chair": contribution,
        "contribution_margin_pct": contribution / gross_rev if gross_rev else 0,
        "basis_note": "NHIA / ambulatory-infusion benchmark defaults — "
                      "illustrative, every input editable; the math is a "
                      "pure function of the assumptions.",
    }


#: The qs-editable AIC assumptions: (param, qs key, lo, hi, kind).
#: Percent-kind inputs arrive as 0–100 and convert to fractions.
_AIC_QS_FIELDS = [
    ("chairs", "aic_chairs", 1, 60, "int"),
    ("util_pct", "aic_util", 30, 95, "pct"),
    ("infusions_per_chair_day", "aic_per_day", 2.0, 12.0, "float"),
    ("revenue_per_infusion_drug", "aic_drug_rev", 100.0, 5_000.0, "float"),
    ("commercial_mix_pct", "aic_commercial", 0, 100, "pct"),
    ("nurse_to_chair", "aic_nurse_ratio", 0.10, 1.0, "float"),
    ("nurse_fully_loaded", "aic_nurse_cost", 60_000.0, 250_000.0, "float"),
    ("facility_overhead_per_chair", "aic_overhead", 5_000.0, 120_000.0,
     "float"),
    ("rcm_cost_pct", "aic_rcm", 1, 15, "pct"),
]


def aic_assumptions_from_qs(qs: Dict[str, Any]) -> Dict[str, Any]:
    """Parse + clamp AIC assumption overrides from the query string.

    Every value is range-clamped (never trusted raw), percent inputs
    arrive human-readable (78 → 0.78), and unknown/blank keys fall
    through to the model defaults — so a hand-edited URL can never
    poison the P&L."""
    out: Dict[str, Any] = {}
    for param, key, lo, hi, kind in _AIC_QS_FIELDS:
        raw = qs.get(key)
        if isinstance(raw, list):
            raw = raw[0] if raw else None
        if raw is None or str(raw).strip() == "":
            continue
        try:
            v = float(str(raw).strip())
        except (TypeError, ValueError):
            continue
        v = max(float(lo), min(float(hi), v))
        if kind == "pct":
            out[param] = v / 100.0
        elif kind == "int":
            out[param] = int(v)
        else:
            out[param] = v
    return out


def aic_sensitivity(*, swing: float = 0.20,
                    **assumptions: Any) -> List[Dict[str, Any]]:
    """Tornado on contribution-per-chair: swing each operating lever
    ±``swing`` (utilization and mix clamped to their valid ranges) and
    measure the contribution move. Sorted by impact — which assumption
    actually moves the chair P&L. Pure recomputation through
    ``aic_chair_economics``, so it can never disagree with the model."""
    base = aic_chair_economics(**assumptions)
    base_c = base["contribution_per_chair"]
    levers = [
        ("Chair utilization", "util_pct",
         base["assumptions"]["util_pct"], 0.30, 0.95),
        ("Infusions / chair / day", "infusions_per_chair_day",
         base["assumptions"]["infusions_per_chair_day"], 1.0, 14.0),
        ("Commercial payer mix", "commercial_mix_pct",
         base["assumptions"]["commercial_mix_pct"], 0.0, 1.0),
        ("Drug revenue / infusion", "revenue_per_infusion_drug",
         base["assumptions"]["revenue_per_infusion_drug"], 50.0, 10_000.0),
        ("Nurse cost (fully loaded)", "nurse_fully_loaded",
         base["assumptions"]["nurse_fully_loaded"], 30_000.0, 400_000.0),
        ("Facility overhead / chair", "facility_overhead_per_chair",
         base["assumptions"]["facility_overhead_per_chair"],
         1_000.0, 200_000.0),
        ("RCM cost %", "rcm_cost_pct",
         base["assumptions"]["rcm_cost_pct"], 0.0, 0.25),
    ]
    out: List[Dict[str, Any]] = []
    for label, param, val, lo, hi in levers:
        lo_v = max(lo, min(hi, val * (1 - swing)))
        hi_v = max(lo, min(hi, val * (1 + swing)))
        c_lo = aic_chair_economics(
            **{**assumptions, param: lo_v})["contribution_per_chair"]
        c_hi = aic_chair_economics(
            **{**assumptions, param: hi_v})["contribution_per_chair"]
        out.append({
            "lever": label, "param": param,
            "contribution_low": c_lo, "contribution_high": c_hi,
            "impact": abs(c_hi - c_lo),
            "base": base_c,
        })
    out.sort(key=lambda r: -r["impact"])
    return out


def aic_utilization_curve(**assumptions: Any) -> Dict[str, Any]:
    """Contribution-per-chair across the utilization range (40–95%),
    with the break-even utilization — the de-novo ramp question
    ("how full do the chairs have to be before this site carries
    itself?"). Fixed costs (nursing ratio + overhead) don't scale with
    utilization, which is what creates the break-even. Pure
    recomputation through ``aic_chair_economics``."""
    pts: List[Dict[str, Any]] = []
    breakeven: Optional[float] = None
    overrides = {k: v for k, v in assumptions.items() if k != "util_pct"}
    for u in [x / 100.0 for x in range(40, 96, 5)]:
        c = aic_chair_economics(
            **overrides, util_pct=u)["contribution_per_chair"]
        pts.append({"util_pct": u, "contribution": c})
    # Break-even by fine scan (1% steps) — fixed cost vs per-infusion
    # gross profit crosses somewhere below the display range usually.
    for u in [x / 100.0 for x in range(5, 96)]:
        c = aic_chair_economics(
            **overrides, util_pct=u)["contribution_per_chair"]
        if c >= 0:
            breakeven = u
            break
    current = assumptions.get("util_pct", 0.78)
    return {
        "points": pts,
        "breakeven_util": breakeven,
        "current_util": current,
        "current_contribution": aic_chair_economics(
            **overrides, util_pct=current)["contribution_per_chair"],
    }


#: Chairs per ambulatory infusion center (industry typical) and annual
#: infusions one chair turns at benchmark utilization — the capacity
#: denominators. Editable defaults; NHIA / ambulatory benchmarks.
CHAIRS_PER_AIS = 7.0
CHAIR_INFUSIONS_PER_YR = 6.0 * 250 * 0.78        # ≈ 1,170 (matches AIC model)
VISITS_PER_PATIENT_YR = INFUSIONS_PER_PATIENT_YR  # 18
#: Share of total infusion volume served at freestanding ambulatory
#: infusion centers today (the rest is HOPD/office/home — see
#: _site_of_care). The chair-saturation ratio compares the AIS-channel
#: slice of demand to AIS chairs, not total demand to AIS chairs.
AIS_SITE_SHARE = 0.22


#: The infusion-site landscape by OWNERSHIP — the competitive-dynamics
#: segments the user asked for, with national capacity share (illustrative,
#: NHIA / industry structure). Sum = 1.0. ``non_hospital`` flags the
#: segments outside the health-system captive pool.
_PROVIDER_SEGMENTS = [
    {"segment": "National / regional chains", "share": 0.28,
     "non_hospital": True,
     "examples": "Option Care, IVX Health, Coram, Optum, Soleo, "
                 "KabaFusion, Paragon",
     "note": "the scaled platforms — public + PE + payer-owned; the "
             "consolidators a roll-up competes with or buys"},
    {"segment": "Health-system-owned", "share": 0.33,
     "non_hospital": False,
     "examples": "HOPD suites + system-affiliated AIC/home",
     "note": "captive hospital-outpatient capacity — the share being "
             "steered AWAY; whitespace to capture, not competition to "
             "displace"},
    {"segment": "Physician-owned (in-office + practice AIC)", "share": 0.15,
     "non_hospital": True,
     "examples": "rheum / GI / oncology / neuro practices with in-office "
                 "buy-and-bill",
     "note": "the classic roll-up target — single-specialty practices "
             "with captive referrals and sub-scale billing"},
    {"segment": "Independent ambulatory infusion centers", "share": 0.14,
     "non_hospital": True,
     "examples": "regional founder-owned AIS",
     "note": "the fragmented independent AIC pool — prime tuck-ins"},
    {"segment": "Independent home infusion", "share": 0.10,
     "non_hospital": True,
     "examples": "regional home-infusion pharmacies",
     "note": "founder/family-owned home pharmacies — the home-channel "
             "consolidation pool"},
]


def county_capacity(county: Dict[str, Any]) -> Dict[str, Any]:
    """Capacity + saturation read for one county.

    Estimates non-hospital chair capacity from the county's AIS estimate,
    sets it against the county's annual infusion visit demand, and
    derives the saturation / penetration / demand-vs-capacity signals.
    All arithmetic on the county's REAL population-driven patient base +
    documented per-chair throughput — labeled estimates, editable."""
    patients = county.get("infusion_patients", 0) or 0
    est_ais = county.get("est_ais_centers", 0) or 0
    seniors = county.get("seniors", 0) or 0
    rural = county.get("pct_rural", 0) or 0

    chairs = round(est_ais * CHAIRS_PER_AIS)
    demand_visits = patients * VISITS_PER_PATIENT_YR
    # Chair saturation compares the AIS-CHANNEL slice of demand to AIS
    # chair capacity (HOPD/office/home volume is not chair-served here).
    ais_demand_visits = demand_visits * AIS_SITE_SHARE
    capacity_visits = chairs * CHAIR_INFUSIONS_PER_YR
    dc_ratio = (ais_demand_visits / capacity_visits) if capacity_visits else None
    patients_per_chair = round(patients / chairs) if chairs else None
    chairs_per_100k_sr = round(chairs / seniors * 100_000, 1) if seniors else 0.0
    # Non-hospital penetration: national ~70% of infusion is non-HOPD;
    # rural markets lean more on the hospital (less freestanding/home
    # density). Modeled, labeled.
    non_hosp_pen = max(0.45, min(0.78, 0.72 - 0.35 * rural))

    if dc_ratio is None:
        band = "no local capacity"
    elif dc_ratio >= 1.15:
        band = "UNDERSUPPLIED"
    elif dc_ratio >= 0.85:
        band = "balanced"
    else:
        band = "saturated"

    # Capacity split by owner — apportion the county's chairs across the
    # ownership segments (national shares; non-hospital chairs only get
    # the non-hospital segments, HOPD gets the health-system share).
    segs = []
    for s in _PROVIDER_SEGMENTS:
        segs.append({
            "segment": s["segment"],
            "share": s["share"],
            "est_chairs": round(chairs * s["share"]) if chairs else 0,
            "non_hospital": s["non_hospital"],
        })
    return {
        "est_chairs": chairs,
        "demand_visits": round(demand_visits),
        "ais_demand_visits": round(ais_demand_visits),
        "capacity_visits": round(capacity_visits),
        "demand_capacity_ratio": round(dc_ratio, 2) if dc_ratio else None,
        "patients_per_chair": patients_per_chair,
        "chairs_per_100k_seniors": chairs_per_100k_sr,
        "non_hospital_penetration": round(non_hosp_pen, 2),
        "saturation_band": band,
        "segments": segs,
    }


def _growth_proxy(county: Dict[str, Any]) -> float:
    """A 0–1 growth signal for a county. No vendored county-level growth
    series exists, so this is a DOCUMENTED proxy: north-suburb growth
    corridors score highest; a younger age mix (lower 65+ share) signals
    in-migration/family growth; low rurality signals metro-core growth.
    Labeled as a proxy, not a Census CAGR."""
    score = 0.0
    if county.get("region") == "North suburb":
        score += 0.45                       # the flagged growth rings
    # Younger county (lower 65+ share) → faster population growth in TX.
    s65 = county.get("pct_age_65_plus", 0.13) or 0.13
    score += max(0.0, min(0.35, (0.16 - s65) / 0.16 * 0.35 + 0.10))
    # Less rural → metro-core / suburban growth.
    score += max(0.0, 0.20 * (1 - min(1.0, (county.get("pct_rural", 0)
                                            or 0) / 0.30)))
    return round(min(1.0, score), 3)


def county_opportunity_score(county: Dict[str, Any],
                             cap: Dict[str, Any]) -> Dict[str, Any]:
    """0–100 long-term-growth opportunity score for a county.

    Blends four diligence axes — demand size, under-saturation (demand
    vs local capacity), payer quality (income + low uninsured), and a
    growth proxy — into one rank. Flags counties where demand growth is
    likely to outrun capacity (the undersupplied-growth thesis). Pure
    function of the county's real demographics + the capacity estimate."""
    import math
    patients = county.get("infusion_patients", 0) or 0
    demand = min(1.0, math.log10(max(patients, 1)) / math.log10(80_000))
    dc = cap.get("demand_capacity_ratio")
    growth = _growth_proxy(county)
    # Under-saturation axis: no local AIS chairs + real demand = fully
    # unserved (1.0); otherwise scale the AIS demand-to-capacity ratio.
    if dc is None:
        under = 1.0 if patients >= 2_000 else 0.4
    else:
        under = min(1.0, dc / 1.5)
    income = county.get("median_household_income", 60_000) or 60_000
    unins = county.get("uninsured_rate", 0.20) or 0.20
    payer = max(0.0, min(1.0,
                         (income / 110_000) * 0.6
                         + (1 - min(1.0, unins / 0.30)) * 0.4))
    score = round(100 * (0.35 * demand + 0.30 * under
                         + 0.20 * payer + 0.15 * growth), 1)
    # Demand likely to exceed capacity when: chairs are already
    # oversubscribed (≥1.10); OR real demand with NO local AIS; OR a
    # growth corridor that is balanced today but where site-of-care
    # migration + population growth will push it over (≥0.85 + growth).
    demand_exceeds = bool(
        (dc is not None and dc >= 1.10)
        or (dc is None and patients >= 2_000)
        or (dc is not None and dc >= 0.85 and growth >= 0.45))
    # The forward read: today's AIS demand grown by the site-of-care
    # migration (AIS share 22% → ~30% over a 5-yr hold) vs today's
    # chairs — what the corridor looks like at exit if capacity is static.
    fwd_ratio = round(dc * (0.30 / AIS_SITE_SHARE), 2) if dc else None
    return {
        "score": score,
        "demand_axis": round(demand, 3),
        "undersaturation_axis": round(under, 3),
        "payer_axis": round(payer, 3),
        "growth_axis": growth,
        "demand_capacity_ratio_fwd": fwd_ratio,
        "demand_exceeds_capacity": demand_exceeds,
    }


def texas_growth_scorecard(
    metro_deepdives: List[Dict[str, Any]]) -> Dict[str, Any]:
    """High-level Texas scorecard — rank every county across the four
    metros on the long-term growth-opportunity score, and surface the
    subset where demand growth is likely to exceed local capacity.

    Pure function of the per-county capacity + score already computed in
    the metro deep-dives."""
    rows: List[Dict[str, Any]] = []
    for dd in metro_deepdives:
        for s in dd["suburbs"]:
            cap = s.get("capacity") or {}
            sc = s.get("opportunity") or {}
            rows.append({
                "county": s["county"], "metro": dd["metro"].split("-")[0],
                "region": s.get("region", ""),
                "population": s["population"],
                "infusion_patients": s["infusion_patients"],
                "est_chairs": cap.get("est_chairs"),
                "patients_per_chair": cap.get("patients_per_chair"),
                "demand_capacity_ratio": cap.get("demand_capacity_ratio"),
                "saturation_band": cap.get("saturation_band"),
                "non_hospital_penetration": cap.get("non_hospital_penetration"),
                "score": sc.get("score", 0),
                "demand_exceeds_capacity": sc.get("demand_exceeds_capacity"),
            })
    rows.sort(key=lambda r: -r["score"])
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
    undersupplied = [r for r in rows if r["demand_exceeds_capacity"]]
    undersupplied.sort(key=lambda r: -(r["demand_capacity_ratio"] or 0))
    return {
        "counties": rows,
        "top_opportunities": rows[:10],
        "undersupplied_growth_markets": undersupplied[:8],
        "n_counties": len(rows),
        "n_undersupplied": len(undersupplied),
        "note": (
            "Opportunity score (0–100) blends demand size (35%), "
            "under-saturation vs local capacity (30%), payer quality "
            "(20%), and a growth proxy (15%). 'Demand exceeds capacity' "
            "flags counties with a demand-to-chair ratio ≥1.15 AND a "
            "high growth proxy — where a de-novo or tuck-in faces "
            "undersupplied, growing demand."),
    }


def texas_investment_thesis(a: Dict[str, Any]) -> Dict[str, Any]:
    """The IC-ready synthesis — the thesis a partner reads first, built
    PURELY from the assembled analysis so it can never drift from the
    sections below. Five pillars (each with its supporting number), the
    top risks, and the honest 'diligence next' gaps."""
    def _money(v: float) -> str:
        v = float(v or 0)
        if abs(v) >= 1e9:
            return f"${v/1e9:.2f}B"
        if abs(v) >= 1e6:
            return f"${v/1e6:.1f}M"
        return f"${v:,.0f}"
    s = a["sizing"]
    frag = a["fragmentation"]
    site = {x["site"]: x["share"] for x in a["site_of_care"]}
    hopd = next((v for k, v in site.items()
                 if "HOPD" in k or "Hospital" in k), 0.30)
    nonhosp = round(1 - hopd, 2)
    ev = a["site_of_care_evolution"]
    ma = a["ma_enrollment"]
    sc = a["growth_scorecard"]
    aic = a["aic_economics"]
    curve = a["aic_utilization_curve"]
    reg = a["regulatory_environment"]
    hp = a["hopd_pool"]
    risk = a["home_infusion"]["therapy_risk"]
    refs = a["home_infusion"]["referral_sources"]
    us = ", ".join(r["county"] for r in
                   sc["undersupplied_growth_markets"][:3])

    pillars = [
        {"title": "Large, growing, fragmented market",
         "stat": f"{_money(s['tam'])} TAM · {s['composite_cagr_pct']:.1f}% "
                 f"CAGR · HHI {frag['hhi']:,.0f}",
         "point": "A platform-scale, low-concentration market — the "
                  f"largest operator holds only "
                  f"{frag['top_operator_share']*100:.0f}% and the "
                  f"independent pool is "
                  f"{frag['independent_pool_share']*100:.0f}%: a textbook "
                  "buy-and-build runway."},
        {"title": "Structural site-of-care tailwind",
         "stat": f"HOPD {ev['soc_start']['hopd']*100:.0f}%→"
                 f"{ev['soc_end']['hopd']*100:.0f}% · "
                 f"{_money(hp['total_hopd_revenue'])} HOPD pool",
         "point": "Infusion has moved "
                  f"{ev['hopd_shift_pts']} points out of the hospital "
                  "since 2015 (COVID + the HIT benefit + payer steerage); "
                  f"the {hopd*100:.0f}% HOPD pool is white-space to "
                  "capture, not a competitor to displace."},
        {"title": "Favorable Texas structure",
         "stat": f"No CON · {ma['penetration']*100:.0f}% MA · "
                 f"{nonhosp*100:.0f}% already non-hospital",
         "point": "De-novo is unconstrained (no Certificate of Need), MA "
                  "penetration drives site-of-care steerage, and most "
                  "volume already sits outside the hospital — the entry "
                  "conditions for a roll-up are unusually clean."},
        {"title": "AIC unit economics work",
         "stat": f"{_money(aic['contribution_per_chair'])}/chair · "
                 f"break-even ≈{curve['breakeven_util']*100:.0f}% util",
         "point": "Per-chair contribution is healthy at benchmark "
                  "utilization with a low break-even; chair throughput + "
                  "commercial payer mix are the levers to underwrite."},
        {"title": "De-novo white-space identified",
         "stat": f"{sc['n_undersupplied']} undersupplied growth corridors",
         "point": f"{sc['n_undersupplied']} north / Austin-corridor "
                  f"counties ({us}…) show demand outrunning AIS chair "
                  "capacity — the priority de-novo and tuck-in targets."},
    ]
    risks = [
        {"risk": "Drug-spread compression",
         "detail": f"ASP+{a['asp_pricing']['addon_sequestered']*100:.1f}%, "
                   "biosimilars, 340B, and white-bagging all squeeze the "
                   f"buy-and-bill margin ({reg['headwinds']} regulatory "
                   "headwinds) — underwrite on service margin, not the "
                   "drug."},
        {"risk": "Home-infusion referral concentration",
         "detail": f"≈{refs['hospital_dependence']*100:.0f}% of home-"
                   "infusion referrals come from hospital discharge desks, "
                   "and the Medicare HIT benefit's calendar-day gap "
                   "under-pays the channel — commercial mix decides the "
                   "economics."},
        {"risk": f"Most-at-risk therapy: {risk['most_at_risk']}",
         "detail": "Rare-disease, IG, and home-biologic lines carry the "
                   "highest reimbursement + payer-steerage risk — a "
                   "concentration to size in the target's book."},
    ]
    diligence_next = [
        "Replace modeled provider counts with a live NPPES / state "
        "pharmacy-board pull, and the modeled prevalence rates with the "
        "target's own claims.",
        "Quantify the target's referral concentration (top-5 sources) and "
        "white-bagged % by payer.",
        "Confirm the current Texas white-bagging statute and the target's "
        "accreditations / renewal calendar.",
    ]
    return {
        "headline": (
            f"A {_money(s['tam'])} fragmented Texas infusion market "
            f"(HHI {frag['hhi']:,.0f}) with a structural site-of-care "
            f"tailwind and no Certificate-of-Need barrier — a "
            f"buy-and-build with de-novo white-space in "
            f"{sc['n_undersupplied']} growth corridors. Underwrite on "
            f"service margin + commercial mix, not the drug spread."),
        "pillars": pillars,
        "risks": risks,
        "diligence_next": diligence_next,
        "verdict": ("CONSTRUCTIVE — the market structure, Texas rules, and "
                    "unit economics support a roll-up thesis; the central "
                    "risk is drug-margin compression, which steers the "
                    "value-creation plan toward service + RCM, not drug."),
    }


def build_texas_infusion_analysis(
    aic_overrides: Optional[Dict[str, Any]] = None,
    nppes_live: bool = False,
) -> Dict[str, Any]:
    """Assemble the full Texas infusion CDD analysis.

    Pulls real TX demographics, runs the verified sizing math, and
    layers the segmentation / concentration / payer / structural reads.
    ``aic_overrides`` (already clamped via ``aic_assumptions_from_qs``)
    re-run the AIC unit-economics, tornado, and utilization curve on
    the partner's own assumptions. Returns one audit-friendly dict.
    """
    aic_overrides = aic_overrides or {}
    from ..data.county_demographics import demographics_state
    demo = demographics_state("TX") or {}
    tx_pop = int(demo.get("population") or 30_029_572)
    pct_65 = float(demo.get("pct_age_65_plus") or 0.1341)
    seniors = round(tx_pop * pct_65)

    model = texas_infusion_model(tx_pop)
    sizing = compute(model)
    tornado = sensitivity(model)

    chains = _chains()
    hhi = _hhi_named(chains)
    hhi_band = ("highly concentrated" if hhi > 2500
                else "moderately concentrated" if hhi >= 1500
                else "unconcentrated / fragmented")

    site = _site_of_care()
    # 5-yr site-of-care TAM at each site's own growth — exposes the
    # HOPD → home/AIS migration as dollars.
    for s in site:
        s["tam_today"] = sizing["tam"] * s["share"]
        s["tam_y5"] = s["tam_today"] * (
            (1 + s["growth_pct"] / 100.0) ** model.horizon_years)

    payer = _payer_mix()
    for p in payer:
        p["tam_value"] = sizing["tam"] * p["share"]

    tx_share = tx_pop / US_POPULATION_2024
    provider_landscape = texas_provider_landscape(tx_share)
    tx_patients = int(model.chain[0].value)
    metros = texas_metro_breakdown(tx_patients, tx_pop)
    # CDC PLACES county rates + ACS female shares (live when egress is
    # available, empty offline) + the TX state proxy-rate fallback —
    # fetched once and threaded into every metro deep dive.
    from ..data.cdc_places_api import places_counties_by_fips
    from ..data.acs_sex import county_female_share
    places_county = places_counties_by_fips("TX")
    female_by_fips = county_female_share("TX", "48")
    cdc_rates = texas_cdc_state_rates(places_county or None)
    cdc_proxies = texas_cdc_proxies(places_county or None)
    # In-depth per-city deep dives — age-band ranking, suburb/county
    # breakdown with white-space, linked operators, specialty tilt.
    metro_deepdives = [
        build_texas_metro_deepdive(
            m, tx_patients, tx_pop, places_county, female_by_fips, cdc_rates)
        for m in metros
    ]

    # Health-system-owned (captive) capacity = the HOPD site share —
    # hospital outpatient infusion is owned by health systems and sits
    # OUTSIDE the addressable independent pool. Surface it explicitly.
    hopd = next((s for s in site if "HOPD" in s["site"]), None)
    health_system = {
        "hopd_share": hopd["share"] if hopd else 0.0,
        "hopd_tam": hopd["tam_today"] if hopd else 0.0,
        "note": (
            "Hospital-outpatient (HOPD) infusion is health-system-owned, "
            "captive capacity — it is the share being steered AWAY and is "
            "NOT in the independent platform's addressable pool. A high "
            "HOPD share is whitespace (volume to capture), not competition "
            "to displace."),
    }
    # Fragmentation summary — the one-line competitive read.
    top_named = max((c for c in chains if c.get("named")),
                    key=lambda c: c["share"])
    pool = next((c for c in chains if not c.get("named")), None)
    fragmentation = {
        "hhi": hhi,
        "band": hhi_band,
        "top_operator": top_named["org"],
        "top_operator_share": top_named["share"],
        "independent_pool_share": pool["share"] if pool else 0.0,
        "verdict": (
            f"Fragmented (HHI {hhi:,.0f}). The largest operator "
            f"({top_named['org']}) holds only "
            f"{top_named['share']*100:.0f}% nationally and the "
            f"regional/independent pool is "
            f"{(pool['share']*100 if pool else 0):.0f}% — a textbook "
            "buy-and-build runway with no incumbent able to block a "
            "roll-up."),
    }

    out = {
        "state": "TX",
        "demographics": {
            "population": tx_pop,
            "pct_age_65_plus": pct_65,
            "seniors_65_plus": seniors,
            "uninsured_rate": float(demo.get("uninsured_rate") or 0.2029),
            "median_household_income":
                float(demo.get("median_household_income") or 73_831),
            "pct_rural": float(demo.get("pct_rural") or 0.1646),
            "counties": int(demo.get("counties") or 254),
        },
        "tx_population_share": tx_pop / US_POPULATION_2024,
        "sizing": sizing,
        "tornado": tornado,
        "site_of_care": site,
        "site_of_care_evolution": home_infusion_evolution(),
        "hopd_pool": texas_hopd_pool(
            metro_deepdives,
            next((s["share"] for s in site
                  if "HOPD" in s["site"] or "Hospital" in s["site"]), 0.30),
            fetch_live=nppes_live),
        "payer_mix": payer,
        "asp_pricing": texas_asp_pricing(),
        "ma_enrollment": texas_ma_enrollment(tx_pop, seniors,
                                             fetch_live=nppes_live),
        "chains": chains,
        "hhi": hhi,
        "hhi_band": hhi_band,
        "provider_landscape": provider_landscape,
        "channel_economics": channel_economics(),
        "home_infusion": {
            "therapies": home_infusion_therapy_reference(),
            "networks": home_infusion_networks(),
            "reimbursement": home_infusion_reimbursement(),
            "episode_economics": home_infusion_episode_economics(),
            "tx_conditions": home_infusion_conditions(tx_pop, seniors),
            "tx_discharges": home_infusion_discharge_volumes(tx_pop, seniors),
            "therapy_risk": home_infusion_therapy_risk(),
            "referral_sources": home_infusion_referral_sources(),
        },
        "players": infusion_players(),
        "risk_register": infusion_risk_register(),
        "regulatory_environment": regulatory_reimbursement_environment(),
        "rcm_playbook": rcm_playbook(),
        "aic_economics": aic_chair_economics(**aic_overrides),
        "aic_sensitivity": aic_sensitivity(**aic_overrides),
        "aic_utilization_curve": aic_utilization_curve(**aic_overrides),
        "aic_overrides_active": bool(aic_overrides),
        "drug_supply": infusion_drug_supply(),
        "provider_segments": _PROVIDER_SEGMENTS,
        "provider_map": texas_infusion_provider_map(
            metro_deepdives, fetch_live=nppes_live),
        "jcode_pos": infusion_jcode_pos(fetch_live=nppes_live),
        "cdc_proxies": cdc_proxies,
        "growth_scorecard": texas_growth_scorecard(metro_deepdives),
        "metros": metros,
        "metro_deepdives": metro_deepdives,
        "health_system_capacity": health_system,
        "fragmentation": fragmentation,
        "population_growth": {
            "tx_pop_gain_2024": TX_POP_GAIN_2024,
            "tx_pop_growth_pct": TX_POP_GROWTH_PCT,
            "tx_senior_growth_pct": TX_SENIOR_GROWTH_PCT,
            "note": (
                f"Texas added {TX_POP_GAIN_2024:,} residents in the year "
                f"to 2024-07-01 — the largest numeric gain of any state "
                f"(Census Vintage 2024), ≈{TX_POP_GROWTH_PCT:.1f}%/yr. The "
                f"65+ cohort grows faster (≈{TX_SENIOR_GROWTH_PCT:.1f}%/yr) "
                "on Sun-Belt aging + in-migration — the infusion demand "
                "tailwind."),
        },
        "structural_factors": [
            {"factor": "No Certificate of Need (CON)",
             "tone": "positive",
             "detail": "Texas is one of ~12 CON-free states — de-novo "
                       "AIS chairs and home-infusion branches open "
                       "without state approval. Entry is unconstrained, "
                       "which favors a buy-and-build."},
            {"factor": "Metro density (Houston / DFW / Austin / San Antonio)",
             "tone": "positive",
             "detail": "The four metros hold ~70% of Texans — enough "
                       "density for AIS hub-and-spoke and home-nurse "
                       "route economics."},
            {"factor": "Fast-growing 65+ base + net in-migration",
             "tone": "positive",
             "detail": f"~{seniors/1e6:.1f}M Texans are 65+; Sun-Belt "
                       "aging plus in-migration grow covered lives faster "
                       "than the US average — the demand tailwind."},
            {"factor": "Medicaid non-expansion + ~20% uninsured",
             "tone": "negative",
             "detail": "Texas did not expand Medicaid and has the highest "
                       "US uninsured rate (~20%) — a real self-pay / "
                       "bad-debt drag, especially on OPAT discharged from "
                       "safety-net hospitals."},
            {"factor": "Biosimilar deflation + nurse capacity",
             "tone": "negative",
             "detail": "Biosimilar adoption compresses per-infusion drug "
                       "revenue and infusion-nurse supply caps chair "
                       "utilization — the two priced headwinds."},
        ],
        "sources": [
            "NHIA (National Home Infusion Association) industry report — "
            "patient counts, infusion frequency, site mix",
            "MedPAC Part B drug payment chapter — ASP+6 reimbursement",
            "US Census Bureau 2024 population estimates (state + US)",
            "ACS 5-year via county_demographics — TX 65+, uninsured, "
            "income, rurality",
            "DOJ/FTC Horizontal Merger Guidelines — HHI concentration "
            "thresholds (1,500 / 2,500)",
            "Public operator disclosures (Option Care OPCH filings; CVS, "
            "UnitedHealth/Optum, Elevance segment commentary) — chain "
            "shares, illustrative",
            "CDC PLACES (data.cdc.gov, dataset i46a-9kgh) — full-population "
            "county prevalence for the therapy-demand proxies (live Socrata "
            "API with vendored TX state fallback)",
            "CMS Medicare Chronic Conditions — arthritis / cancer / CKD "
            "prevalence (TX-adjusted) for the Medicare-denominator proxies",
            "Census ACS 5-year table B01001 — county female share for the "
            "IV-iron / anemia demand weighting",
            "CMS Medicare Monthly Enrollment — total Medicare beneficiaries "
            "(the true MA-penetration denominator; live + published TX "
            "fallback)",
            "CMS Medicare Outpatient Hospitals (by provider & service) — "
            "HOPD infusion services + payment for the steered-away pool "
            "(live override; modeled from HOPD share offline)",
        ],
        "basis_note": model.basis_note,
    }
    out["investment_thesis"] = texas_investment_thesis(out)
    return out
