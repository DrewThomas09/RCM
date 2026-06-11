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
    metro: Dict[str, Any], tx_patients: int, tx_pop: int) -> Dict[str, Any]:
    """Assemble the in-depth per-city analysis: age-band demand ranking,
    member-county ('suburb') breakdown with white-space, known operators
    (linked), and the specialty tilt. Real ACS population per county +
    the documented age/utilization model."""
    import pandas as pd
    from pathlib import Path
    from ..data.county_demographics import demographics_county

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
            suburbs.append({
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
                "median_household_income":
                    float(d.get("median_household_income") or 0),
                "infusion_patients": patients,
                "est_ais_centers": est_ais,
                # White-space: patients per AIS chair-cluster. High =
                # underserved (demand with thin local capacity).
                "patients_per_ais": (round(patients / est_ais)
                                     if est_ais else None),
                "illness_burden": illness,
            })
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
    }


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


def build_texas_infusion_analysis(
    aic_overrides: Optional[Dict[str, Any]] = None,
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
    # In-depth per-city deep dives — age-band ranking, suburb/county
    # breakdown with white-space, linked operators, specialty tilt.
    metro_deepdives = [
        build_texas_metro_deepdive(m, tx_patients, tx_pop) for m in metros
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

    return {
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
        "payer_mix": payer,
        "chains": chains,
        "hhi": hhi,
        "hhi_band": hhi_band,
        "provider_landscape": provider_landscape,
        "channel_economics": channel_economics(),
        "players": infusion_players(),
        "risk_register": infusion_risk_register(),
        "rcm_playbook": rcm_playbook(),
        "aic_economics": aic_chair_economics(**aic_overrides),
        "aic_sensitivity": aic_sensitivity(**aic_overrides),
        "aic_utilization_curve": aic_utilization_curve(**aic_overrides),
        "aic_overrides_active": bool(aic_overrides),
        "drug_supply": infusion_drug_supply(),
        "provider_segments": _PROVIDER_SEGMENTS,
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
        ],
        "basis_note": model.basis_note,
    }
