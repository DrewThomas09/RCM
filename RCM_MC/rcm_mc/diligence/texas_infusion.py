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


def build_texas_infusion_analysis() -> Dict[str, Any]:
    """Assemble the full Texas infusion CDD analysis.

    Pulls real TX demographics, runs the verified sizing math, and
    layers the segmentation / concentration / payer / structural reads.
    Returns one audit-friendly dict the page renders.
    """
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
    metros = texas_metro_breakdown(model.chain[0].value, tx_pop)

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
        "metros": metros,
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
