"""J-Code Atlas — scan every infusion J-code by site of care (home vs
office vs ambulatory-suite vs HOPD), measure THE CHANGE (the home /
out-of-hospital migration), and tie each code to its disease and the
size of the patient pool it serves.

This is the analysis layer over ``data.infusion_jcodes``. Three reads:

  1. **Site-of-care scan** — for each J-code, the current home / office /
     AIC / HOPD mix, the 2018→now *delta* per site, and a single
     "home-migration index" (how many points of share have left the
     hospital for home/office/AIC). This is the "by home vs in office
     and the change" the diligence asks for, code by code.
  2. **Disease tie** — group the codes by indication, then size each
     disease's infusion-eligible patient pool from real geography
     (population / senior base) × the labeled treated-prevalence anchor.
     A J-code is only demand once it's tied to a disease and its epi.
  3. **Portfolio summary** — how many codes are migrating home, the
     biggest movers, the ASP-erosion (biosimilar) exposure, and the
     home-vs-office split of the whole infusion drug book.

The site mix + its change come from the labeled archetype anchors in the
data layer (recomputable, honest about being anchors). The dollar
dimension (per-unit ASP payment limit) is overlaid LIVE from the CMS ASP
Pricing file where egress permits, and is ``None`` (shown as the
formula) offline — no fabricated dollar value. Patient pools scale with
REAL geography passed in.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from ..data.infusion_jcodes import (
    SOC_NOW_YEAR, SOC_THEN_YEAR, jcode_catalog, site_archetypes,
)

# The four sites of care, in out-of-hospital → hospital order. HOPD is
# the share being steered AWAY; home/office/AIC are the destinations.
SITES = ("home", "office", "aic", "hopd")
_NON_HOSPITAL = ("home", "office", "aic")

# Default US population denominators when a caller does not pass real
# geography (so the module is usable standalone). Census 2024 vintage.
_US_POPULATION = 334_900_000
_US_SENIOR_SHARE = 0.17


def _migration(then: Dict[str, float], now: Dict[str, float]
               ) -> Dict[str, Any]:
    """The site-of-care change for one archetype: per-site delta (pts),
    the home-migration index (non-hospital share gained = HOPD share
    lost), and the direction. Pts are percentage points (×100)."""
    deltas = {s: round((now[s] - then[s]) * 100, 1) for s in SITES}
    non_hosp_then = sum(then[s] for s in _NON_HOSPITAL)
    non_hosp_now = sum(now[s] for s in _NON_HOSPITAL)
    return {
        "delta_pts": deltas,
        "home_shift_pts": deltas["home"],
        "hopd_shift_pts": deltas["hopd"],
        # Out-of-hospital migration = non-hospital share gained.
        "out_of_hospital_pts": round((non_hosp_now - non_hosp_then) * 100, 1),
        "non_hospital_share_now": round(non_hosp_now, 4),
        "non_hospital_share_then": round(non_hosp_then, 4),
    }


# Home-shift-opportunity weights — a documented analyst framework, not a
# data feed. A code is an attractive home/AIC roll-up target when it has
# a large patient pool (demand), is actively migrating out of the
# hospital (momentum), AND still has hospital share left to capture
# (runway). Biosimilar codes carry a drug-margin penalty.
_OPP_WEIGHTS = {"demand": 0.45, "momentum": 0.35, "runway": 0.20}
_OPP_POOL_CAP = 200_000      # pool that maps to a full demand score
_OPP_MOMENTUM_CAP = 22.0     # out-of-hospital pts that maps to full momentum
_OPP_BIOSIM_PENALTY = 0.85   # ASP-erosion haircut on biosimilar codes


def _home_shift_opportunity(
    pool: float, out_of_hospital_pts: float, hopd_share: float,
    biosimilar: bool,
) -> Dict[str, Any]:
    """Score (0–100) how attractive a J-code is as a home/AIC roll-up
    target. Pure arithmetic on the scan row so it recomputes + audits.

    demand   = log-scaled patient pool (the addressable volume)
    momentum = out-of-hospital migration already underway (the trend)
    runway   = HOPD share still in the hospital (the capture headroom)
    A biosimilar haircut reflects the thinner drug spread."""
    demand = min(1.0, math.log10(max(pool, 1)) / math.log10(_OPP_POOL_CAP))
    momentum = min(1.0, max(0.0, out_of_hospital_pts) / _OPP_MOMENTUM_CAP)
    runway = max(0.0, min(1.0, hopd_share))
    penalty = _OPP_BIOSIM_PENALTY if biosimilar else 1.0
    axes = {"demand": demand, "momentum": momentum, "runway": runway}
    score = 100.0 * penalty * sum(axes[k] * w for k, w in _OPP_WEIGHTS.items())
    return {
        "score": round(score, 1),
        "axes": {k: round(v, 3) for k, v in axes.items()},
        "biosimilar_penalty": biosimilar,
    }


def jcode_site_of_care_scan(
    population: Optional[float] = None,
    seniors: Optional[float] = None,
    *,
    fetch_live: bool = False,
) -> List[Dict[str, Any]]:
    """Per-J-code site-of-care scan with the change + patient pool.

    Each row: the code/drug/class/diseases, the current home/office/AIC/
    HOPD mix, the 2018→now per-site delta + home-migration index, the
    estimated infusion-eligible patient pool (real geography × the
    labeled treated-prevalence anchor), and — when ``fetch_live`` and
    egress permit — the live per-unit ASP payment limit.
    """
    pop = float(population) if population else float(_US_POPULATION)
    sen = (float(seniors) if seniors
           else pop * _US_SENIOR_SHARE)
    arch = site_archetypes()

    # Live ASP overlay (best-effort; empty offline → formula shown).
    live_asp: Dict[str, float] = {}
    if fetch_live:
        try:
            from ..data.cms_asp_pricing import fetch_asp_pricing
            live_asp = fetch_asp_pricing(
                [c["hcpcs"] for c in jcode_catalog()])
        except Exception:  # noqa: BLE001 — live overlay is best-effort
            live_asp = {}

    rows: List[Dict[str, Any]] = []
    for c in jcode_catalog():
        a = arch.get(c["soc"]) or {}
        then = a.get("then", {s: 0.0 for s in SITES})
        now = a.get("now", {s: 0.0 for s in SITES})
        mig = _migration(then, now)
        base = sen if c.get("denominator") == "seniors" else pop
        patients = round(base * float(c["epi_per_100k"]) / 1e5)
        asp = live_asp.get(c["hcpcs"])
        opp = _home_shift_opportunity(
            patients, mig["out_of_hospital_pts"], now["hopd"], c["biosimilar"])
        rows.append({
            "hcpcs": c["hcpcs"], "drug": c["drug"], "unit": c["unit"],
            "drug_class": c["drug_class"], "diseases": c["diseases"],
            "icd10": c["icd10"], "biosimilar": c["biosimilar"],
            "soc_archetype": c["soc"], "soc_label": a.get("label", ""),
            "soc_thesis": a.get("thesis", ""),
            "site_mix_now": {s: round(now[s], 4) for s in SITES},
            "site_mix_then": {s: round(then[s], 4) for s in SITES},
            "change": mig,
            "home_shift_pts": mig["home_shift_pts"],
            "out_of_hospital_pts": mig["out_of_hospital_pts"],
            "denominator": c.get("denominator", "population"),
            "epi_per_100k": c["epi_per_100k"], "epi_basis": c["epi_basis"],
            "estimated_patients": patients,
            "asp_payment_limit_per_unit": asp,
            "asp_live": asp is not None,
            "home_shift_opportunity": opp["score"],
            "opportunity_axes": opp["axes"],
            "note": c.get("note", ""),
        })
    # Default sort: biggest home-migrators first (the thesis ranking).
    rows.sort(key=lambda r: -r["out_of_hospital_pts"])
    for i, r in enumerate(rows, start=1):
        r["migration_rank"] = i
    return rows


def jcode_disease_tie(
    population: Optional[float] = None,
    seniors: Optional[float] = None,
    scan: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Tie the J-codes to disease, then size each disease's infusion
    pool. Groups the scan by indication; per disease: the treating
    codes, the summed estimated patient pool, the dominant site of care,
    and how strongly that disease's drugs are migrating home.

    The per-disease patient pool is the MAX across its codes (codes for
    the same disease overlap — different brands of the same therapy — so
    summing would double-count; the max is the conservative pool size).
    """
    scan = scan or jcode_site_of_care_scan(population, seniors)
    by_code = {r["hcpcs"]: r for r in scan}
    grouped: Dict[str, List[str]] = {}
    for r in scan:
        for dz in r["diseases"]:
            grouped.setdefault(dz, []).append(r["hcpcs"])

    out: List[Dict[str, Any]] = []
    for dz, codes in grouped.items():
        recs = [by_code[c] for c in codes]
        # Conservative pool: the largest single-code estimate (brands of
        # the same therapy overlap; do not sum).
        pool = max((r["estimated_patients"] for r in recs), default=0)
        # Demand-weighted average home-migration across the disease's codes.
        wsum = sum(r["estimated_patients"] for r in recs) or 1
        home_mig = round(sum(r["out_of_hospital_pts"] * r["estimated_patients"]
                             for r in recs) / wsum, 1)
        # Dominant site = the site with the largest demand-weighted share.
        site_w = {s: sum(r["site_mix_now"][s] * r["estimated_patients"]
                         for r in recs) for s in SITES}
        dominant = max(site_w, key=site_w.get) if any(site_w.values()) else ""
        out.append({
            "disease": dz,
            "codes": codes,
            "n_codes": len(codes),
            "estimated_pool": pool,
            "dominant_site": dominant,
            "out_of_hospital_pts": home_mig,
            "drug_classes": sorted({r["drug_class"] for r in recs}),
            "any_biosimilar": any(r["biosimilar"] for r in recs),
        })
    out.sort(key=lambda d: -d["estimated_pool"])
    for i, d in enumerate(out, start=1):
        d["rank"] = i
    return out


def jcode_atlas(
    population: Optional[float] = None,
    seniors: Optional[float] = None,
    *,
    fetch_live: bool = False,
) -> Dict[str, Any]:
    """The full atlas: the per-code site-of-care scan, the disease tie,
    and a portfolio summary (home/office split, codes migrating home,
    biggest movers, ASP-erosion exposure). Real geography in →
    recomputable estimates out."""
    scan = jcode_site_of_care_scan(population, seniors, fetch_live=fetch_live)
    diseases = jcode_disease_tie(population, seniors, scan=scan)

    n = len(scan)
    migrating_home = [r for r in scan if r["out_of_hospital_pts"] > 0]
    biosimilars = [r for r in scan if r["biosimilar"]]
    # Demand-weighted current home/office/AIC/HOPD split of the whole
    # infusion drug book (weighted by estimated patient pool).
    wsum = sum(r["estimated_patients"] for r in scan) or 1
    book_mix_now = {s: round(sum(r["site_mix_now"][s] * r["estimated_patients"]
                                 for r in scan) / wsum, 4) for s in SITES}
    book_mix_then = {s: round(sum(r["site_mix_then"][s] * r["estimated_patients"]
                                  for r in scan) / wsum, 4) for s in SITES}
    book_change = {s: round((book_mix_now[s] - book_mix_then[s]) * 100, 1)
                   for s in SITES}
    movers = sorted(scan, key=lambda r: -r["out_of_hospital_pts"])[:6]
    opps = sorted(scan, key=lambda r: -r["home_shift_opportunity"])[:8]

    return {
        "scan": scan,
        "diseases": diseases,
        "summary": {
            "n_codes": n,
            "n_diseases": len(diseases),
            "n_migrating_home": len(migrating_home),
            "n_biosimilar": len(biosimilars),
            "book_mix_now": book_mix_now,
            "book_mix_then": book_mix_then,
            "book_change_pts": book_change,
            "home_office_now": round(book_mix_now["home"]
                                     + book_mix_now["office"], 4),
            "home_office_then": round(book_mix_then["home"]
                                      + book_mix_then["office"], 4),
            "out_of_hospital_gain_pts": round(
                sum(book_change[s] for s in _NON_HOSPITAL), 1),
            "biosimilar_codes": [r["hcpcs"] for r in biosimilars],
            "top_movers": [{"hcpcs": r["hcpcs"], "drug": r["drug"],
                            "out_of_hospital_pts": r["out_of_hospital_pts"],
                            "home_shift_pts": r["home_shift_pts"]}
                           for r in movers],
            "top_opportunities": [
                {"hcpcs": r["hcpcs"], "drug": r["drug"],
                 "drug_class": r["drug_class"],
                 "score": r["home_shift_opportunity"],
                 "estimated_patients": r["estimated_patients"],
                 "out_of_hospital_pts": r["out_of_hospital_pts"],
                 "hopd_share_now": r["site_mix_now"]["hopd"],
                 "biosimilar": r["biosimilar"]}
                for r in opps],
        },
        "opportunity_weights": _OPP_WEIGHTS,
        "then_year": SOC_THEN_YEAR,
        "now_year": SOC_NOW_YEAR,
        "asp_live": any(r["asp_live"] for r in scan),
        "geography": {
            "population": float(population) if population else _US_POPULATION,
            "seniors": (float(seniors) if seniors
                        else (float(population) * _US_SENIOR_SHARE
                              if population else _US_POPULATION
                              * _US_SENIOR_SHARE)),
            "is_default_us": not bool(population),
        },
        "note": (
            f"Every infusion J-code scanned by site of care (home / office "
            f"/ ambulatory suite / HOPD) with the {SOC_THEN_YEAR}→"
            f"{SOC_NOW_YEAR} change, tied to its disease + treated-prevalence "
            f"pool. Site-of-care mix + its change are labeled archetype "
            f"anchors (NHIA / MedPAC site-of-care literature); patient pools "
            f"scale with real geography × published epi anchors; ASP "
            f"payment limits are pulled live from the CMS ASP file where "
            f"egress permits (else the formula is shown). Illustrative "
            f"starting points — replace the site mix with a claims "
            f"place-of-service time-series in diligence."),
    }


def jcode_scan_dataframe(
    population: Optional[float] = None,
    seniors: Optional[float] = None,
    *,
    fetch_live: bool = False,
    scan: Optional[List[Dict[str, Any]]] = None,
):
    """Flatten the site-of-care scan into a pandas DataFrame for the CSV
    export — one row per J-code, with the now-mix, the change, the pool,
    the opportunity score, and (where reachable) the live ASP. Returns a
    DataFrame so the server's shared defanged CSV sender can stream it."""
    import pandas as pd
    scan = scan or jcode_site_of_care_scan(
        population, seniors, fetch_live=fetch_live)
    out = []
    for r in scan:
        now = r["site_mix_now"]
        d = r["change"]["delta_pts"]
        asp = r["asp_payment_limit_per_unit"]
        out.append({
            "hcpcs": r["hcpcs"],
            "drug": r["drug"],
            "drug_class": r["drug_class"],
            "primary_disease": r["diseases"][0] if r["diseases"] else "",
            "n_diseases": len(r["diseases"]),
            "icd10": r["icd10"][0] if r["icd10"] else "",
            "biosimilar": "Y" if r["biosimilar"] else "",
            "home_pct_now": round(now["home"] * 100, 1),
            "office_pct_now": round(now["office"] * 100, 1),
            "aic_pct_now": round(now["aic"] * 100, 1),
            "hopd_pct_now": round(now["hopd"] * 100, 1),
            "home_change_pts": d["home"],
            "out_of_hospital_pts": r["out_of_hospital_pts"],
            "estimated_patients": r["estimated_patients"],
            "asp_payment_limit_per_unit": (round(asp, 4)
                                           if asp is not None else ""),
            "home_shift_opportunity": r["home_shift_opportunity"],
            "migration_rank": r["migration_rank"],
        })
    return pd.DataFrame(out)
