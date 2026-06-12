"""Texas infusion market — Continued (part 2): the granular layer.

The first Texas-infusion page answers "how big, how fragmented, where"
at the state / metro / county grain. This module fills the gaps a deal
team hits NEXT — the per-claim and per-payer grain:

  1. Channel sizing that reconciles — the AIC and home channels sized
     bottom-up (patients × visits × per-channel revenue/infusion) and
     tied back to the part-1 TAM exactly, so the two pages can never
     disagree.
  2. CPT-level reimbursement per OFFICE/AIC visit — the Medicare PFS
     drug-administration codes (96360–96417) with national non-facility
     amounts and the typical visit coding stacks per therapy.
  3. CPT-level reimbursement per HOME visit — the Medicare HIT G-codes
     (G0068–G0070) + the commercial per-diem S-codes that actually fund
     the channel.
  4. The same visit priced across sites (HOPD APC vs office/AIC PFS vs
     home HIT) — the steerage arbitrage in dollars.
  5. Reimbursement by STATE — the CMS Geographic Adjustment Factor
     (GAF), Texas highlighted.
  6. Reimbursement by CITY — the eight Texas PFS payment localities
     (Houston, Dallas, Fort Worth, Austin, Galveston, Brazoria,
     Beaumont, Rest of Texas) with GPCIs → locality-adjusted rates.
  7. Drug mix → the overall reimbursement rate — marquee J-code
     economics per dose and the payer-weighted net yield per infusion
     that reconciles the part-1 $650 anchor.
  8. Payer structure by metro — PPO vs HMO concentration, insurer
     shares (AMA study), MA penetration — and what each mix means for
     buy-and-bill.
  9. The in-network matrix — which operators are in network with which
     plans, per metro.
 10. Proximity & population density — average distance to the nearest
     infusion option per county (a documented spatial model on real
     Census land areas).
 11. HealthQuest Infusion & Specialty spotlight — the Houston regional
     operator whose thesis IS referral-for-convenience: real site
     coordinates, drive-proximity to the population centers, payers,
     and the patient-experience positioning.
 12. Patient experience — the drivers that move infusion volume and a
     scored comparison of the operator models.

Every magnitude is a named-source constant (CMS PFS/OPPS files, NHIA,
AMA insurer-competition study, KFF, Census) or pure arithmetic on the
part-1 model — illustrative starting points for an engagement, labeled
as such, never fabricated precision.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

from .tam_sam import compute
from .texas_infusion import (
    INFUSIONS_PER_PATIENT_YR,
    REVENUE_PER_INFUSION,
    US_POPULATION_2024,
    _payer_mix,
    _site_of_care,
    texas_infusion_model,
)

# ════════════════════════════════════════════════════════════════════
# Sourced reimbursement constants (CMS published figures; year labeled)
# ════════════════════════════════════════════════════════════════════

#: Medicare PFS conversion factors ($ per RVU) — CMS final rules.
#: CY2026 split the CF: qualifying-APM participants get $33.5675; all
#: other clinicians $33.4009 (+3.26% on 2025 after the 2.83% 2025 cut).
PFS_CONVERSION_FACTOR_2025 = 32.3465
PFS_CONVERSION_FACTOR_2026 = 33.4009

#: Medicare PFS drug-administration CPT codes — the OFFICE / freestanding
#: AIC fee schedule. ``nonfac`` is the CY2025 NATIONAL non-facility
#: payment amount and ``nonfac_2026`` the CY2026 (non-QP CF) amount —
#: both verified against the CMS National PFS Relative Value files
#: (RVU25A/RVU25D and RVU26A; national amount = total non-facility RVU
#: × CF). Descriptors are public CPT facts.
PFS_ADMIN_CODES: List[Dict[str, Any]] = [
    {"code": "96360", "family": "Hydration",
     "descriptor": "Hydration IV infusion, initial, 31 min–1 hr",
     "nonfac": 30.08, "nonfac_2026": 33.40, "role": "initial"},
    {"code": "96361", "family": "Hydration",
     "descriptor": "Hydration, each additional hour",
     "nonfac": 11.64, "nonfac_2026": 13.03, "role": "add-on"},
    {"code": "96365", "family": "Therapeutic infusion",
     "descriptor": "IV infusion therapeutic/prophylactic, initial hr",
     "nonfac": 57.90, "nonfac_2026": 67.14, "role": "initial"},
    {"code": "96366", "family": "Therapeutic infusion",
     "descriptor": "Therapeutic IV infusion, each additional hour",
     "nonfac": 19.41, "nonfac_2026": 21.38, "role": "add-on"},
    {"code": "96367", "family": "Therapeutic infusion",
     "descriptor": "Additional sequential infusion, new drug, up to 1 hr",
     "nonfac": 26.52, "nonfac_2026": 29.73, "role": "add-on"},
    {"code": "96368", "family": "Therapeutic infusion",
     "descriptor": "Concurrent infusion (second drug at same time)",
     "nonfac": 18.44, "nonfac_2026": 20.71, "role": "add-on"},
    {"code": "96372", "family": "Injection",
     "descriptor": "Therapeutic injection, SC / IM",
     "nonfac": 13.91, "nonfac_2026": 15.36, "role": "initial"},
    {"code": "96374", "family": "Injection",
     "descriptor": "IV push, single or initial drug",
     "nonfac": 33.96, "nonfac_2026": 37.74, "role": "initial"},
    {"code": "96375", "family": "Injection",
     "descriptor": "IV push, each additional sequential drug",
     "nonfac": 14.23, "nonfac_2026": 15.70, "role": "add-on"},
    {"code": "96413", "family": "Chemo / complex biologic",
     "descriptor": "Chemo/complex-biologic IV infusion, up to 1 hr",
     "nonfac": 119.36, "nonfac_2026": 133.27, "role": "initial"},
    {"code": "96415", "family": "Chemo / complex biologic",
     "descriptor": "Chemo/complex-biologic infusion, each addl hr",
     "nonfac": 25.55, "nonfac_2026": 28.39, "role": "add-on"},
    {"code": "96416", "family": "Chemo / complex biologic",
     "descriptor": "Chemo prolonged infusion, pump initiation",
     "nonfac": 117.42, "nonfac_2026": 133.27, "role": "initial"},
    {"code": "96417", "family": "Chemo / complex biologic",
     "descriptor": "Chemo additional sequential infusion, up to 1 hr",
     "nonfac": 58.87, "nonfac_2026": 66.47, "role": "add-on"},
]

PFS_SOURCE_NOTE = (
    "Medicare Physician Fee Schedule NATIONAL non-facility amounts, "
    "verified against the CMS National PFS Relative Value files: "
    "CY2025 (CF $32.3465 — a real 2.83% cut vs 2024) and CY2026 "
    "(non-QP CF $33.4009; the 2026 office-PE methodology change ALSO "
    "raised admin RVUs, so 96413 moves $119.36 → $133.27, +11.7%). "
    "The non-facility rate is what a physician office or freestanding "
    "AIC collects per code; commercial contracts benchmark off it "
    "(professional services ≈122–148% of Medicare: HCCI 122%, CBO "
    "129%, KFF 143%, MedPAC PPO 134–140%, Milliman 148%).")

#: Typical visit-level CPT coding stacks per therapy — how an AIC visit
#: actually codes out (CPT hierarchy: one initial code per encounter,
#: add-ons stack). Built from the codes above so dollars recompute.
VISIT_CODING_STACKS: List[Dict[str, Any]] = [
    {"visit": "Biologic infusion, 1 hr (infliximab / vedolizumab)",
     "stack": ["96413", "96375"],
     "note": "complex-biologic initial hour + pre-med IV push"},
    {"visit": "Biologic infusion, 2 hr (rituximab / ocrelizumab)",
     "stack": ["96413", "96415", "96375"],
     "note": "initial + additional hour + pre-med push"},
    {"visit": "IVIG, 4 hr",
     "stack": ["96365", "96366", "96366", "96366"],
     "note": "therapeutic initial hour + 3 additional hours"},
    {"visit": "OPAT antibiotic, 1 hr (office-based)",
     "stack": ["96365"],
     "note": "single therapeutic infusion"},
    {"visit": "IV iron, 30–60 min",
     "stack": ["96365"],
     "note": "ferric carboxymaltose / iron sucrose"},
    {"visit": "Chemo, multi-agent + hydration",
     "stack": ["96413", "96417", "96361", "96375"],
     "note": "chemo initial + sequential agent + hydration add-on + push"},
]


def visit_stack_economics() -> List[Dict[str, Any]]:
    """Price each typical visit stack at the CY2025 national
    non-facility amounts — the ADMIN revenue per chair visit (drug is
    billed separately at ASP+6). Pure recompute from the code table."""
    by_code = {c["code"]: c for c in PFS_ADMIN_CODES}
    out = []
    for v in VISIT_CODING_STACKS:
        lines = [{"code": c, "amount": by_code[c]["nonfac"],
                  "descriptor": by_code[c]["descriptor"]}
                 for c in v["stack"]]
        out.append({
            "visit": v["visit"], "note": v["note"], "lines": lines,
            "codes": " + ".join(v["stack"]),
            "admin_total": round(sum(x["amount"] for x in lines), 2),
        })
    out.sort(key=lambda r: -r["admin_total"])
    return out


# ── Texas PFS payment localities — reimbursement by CITY ────────────
#
# Medicare divides Texas into eight PFS payment localities, each with
# its own work / practice-expense / malpractice GPCIs. The GPCIs come
# from the vendored official CMS CY2025 GPCI file (Addendum E, RVU25A
# package — see rcm_mc/data/cms_gpci.py); the composite GAF is
# computed at the published cost-share weights.

#: City labels + county color for the eight TX localities (the CMS
#: file carries only the locality name).
_TX_LOCALITY_COLOR = {
    "18": "Harris + metro core",
    "20": "Jefferson / Orange / Hardin",
    "09": "Brazoria (Pearland / Lake Jackson)",
    "11": "Dallas + metro core",
    "28": "Tarrant (Fort Worth / Arlington)",
    "15": "Galveston (League City / Texas City)",
    "31": "Travis / Williamson / Hays core",
    "99": "San Antonio, El Paso, RGV + all non-metro",
}

TX_LOCALITY_NOTE = (
    "CY2025 PFS GPCIs by Texas payment locality, from the vendored "
    "official CMS GPCI2025 file (Addendum E; work GPCI carries the "
    "statutory 1.0 floor; Houston's 1.409 malpractice GPCI is real — "
    "corroborated by the CY2026 file). GAF is COMPUTED at the "
    "published cost-share weights (work 50.9% / PE 44.8% / MP 4.3%), "
    "not read from Addendum D. San Antonio has NO metro locality of "
    "its own — it pays Rest-of-Texas, the lowest rate in the state, a "
    "real margin fact for site selection. Per-code locality amounts "
    "apply the GAF to the national amount; engagement-grade pricing "
    "should use the per-code locality file (RVU-mix weighting varies "
    "slightly).")


def texas_locality_rates(
    codes: Tuple[str, ...] = ("96413", "96365", "96360"),
) -> List[Dict[str, Any]]:
    """Locality-adjusted payment for the marquee admin codes in each of
    the eight Texas PFS localities — reimbursement by city, recomputed
    as national non-facility × the locality GAF from the vendored CMS
    GPCI file."""
    from ..data.cms_gpci import texas_localities
    by_code = {c["code"]: c for c in PFS_ADMIN_CODES}
    out = []
    for loc in texas_localities():
        row = {
            "locality": loc["locality"],
            "city": loc["name"].title().replace("Of", "of"),
            "counties": _TX_LOCALITY_COLOR.get(loc["locality"], ""),
            "work": loc["work"], "pe": loc["pe"], "mp": loc["mp"],
            "gaf": loc["gaf"],
            "rates": {c: round(by_code[c]["nonfac"] * loc["gaf"], 2)
                      for c in codes},
        }
        out.append(row)
    return out


def state_reimbursement_index(
    anchor_code: str = "96413",
) -> Dict[str, Any]:
    """The by-state reimbursement read: each state's composite GAF
    (from the vendored CMS GPCI file — unweighted mean across the
    state's localities) and what the anchor admin code pays there
    (national non-facility × GAF). Ranked; Texas flagged."""
    from ..data.cms_gpci import GPCI_SOURCE_NOTE, state_gaf
    nonfac = next(c["nonfac"] for c in PFS_ADMIN_CODES
                  if c["code"] == anchor_code)
    rows = [{"state": s, "gaf": v["gaf"],
             "localities": v["localities"],
             "rate": round(nonfac * v["gaf"], 2),
             "is_tx": s == "TX"} for s, v in state_gaf().items()]
    rows.sort(key=lambda r: -r["gaf"])
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    tx = next(r for r in rows if r["is_tx"])
    return {
        "anchor_code": anchor_code,
        "anchor_nonfac": nonfac,
        "states": rows,
        "texas": tx,
        "spread_pct": round(
            (rows[0]["gaf"] / rows[-1]["gaf"] - 1) * 100, 1),
        "note": (
            "Composite GAF by state computed from the vendored CMS "
            "CY2025 GPCI file — unweighted mean across each state's "
            "PFS localities (count shown; single-locality states are "
            "exact). Texas averages ≈0.997 across its eight "
            "localities — the metros pay at or just above national "
            "while Rest-of-Texas (incl. San Antonio) pays ≈0.973. "
            "Alaska's 1.27 reflects its statutory 1.5 work floor. "
            + GPCI_SOURCE_NOTE),
    }


# ── Home infusion CPT/HCPCS — the HIT G-codes + per-diem S-codes ─────

#: Medicare Home Infusion Therapy (HIT) professional-services payment,
#: CY2025 national amounts — verified against the CMS CY2025 national
#: HIT rates file (Jan-2025 revision, Transmittal R13512CP). Paid PER
#: VISIT DAY only (the calendar-day gap). First visits bill the
#: dedicated initial-visit codes G0088–G0090; G0068–G0070 are the
#: subsequent-visit codes. GAF-adjusted in practice.
HIT_G_CODES: List[Dict[str, Any]] = [
    {"code": "G0068", "first_code": "G0088", "category": 1,
     "drugs": "IV anti-infectives, pain management, chelation, "
              "pulmonary hypertension, inotropes (pump drugs)",
     "first_visit": 226.42, "subsequent": 186.16},
    {"code": "G0069", "first_code": "G0089", "category": 2,
     "drugs": "Subcutaneous immunotherapy / SC infusion (incl. SCIG)",
     "first_visit": 305.92, "subsequent": 251.55},
    {"code": "G0070", "first_code": "G0090", "category": 3,
     "drugs": "IV chemotherapy / highly complex biologics",
     "first_visit": 380.58, "subsequent": 312.93},
]

HIT_SOURCE_NOTE = (
    "CY2025 Medicare HIT services payment amounts, national "
    "unadjusted, per infusion-drug-administration CALENDAR DAY (a "
    "5-hour base unit; CMS CY2025 national HIT rates file as revised "
    "Jan 2025, Transmittal R13512CP; +2.4% CPI-U-less-productivity "
    "update on CY2024). First visits bill G0088–G0090 at the higher "
    "amount; G0068–G0070 are subsequent visits. The structural flaw: "
    "a 28-day OPAT course with one weekly nurse visit collects ~4 "
    "payments — the other 24 therapy days carry zero professional "
    "payment. The drug pays separately (Part B ASP+6 / DME LCD) and "
    "the pump + supplies under DME.")

#: Commercial / managed-care home-infusion PER-DIEM S-codes — what
#: actually funds the home channel. Descriptors are official HCPCS
#: Level II facts. ``published_rate`` is the ONLY public fee schedule
#: that prices these codes — Montana Medicaid's Home Infusion Services
#: fee schedule (eff. 2025-07-01) — shown as the verifiable floor;
#: commercial contracts are confidential and negotiate above Medicaid
#: (NHIA model-contract structure). ``None`` = no public rate exists.
HOME_PERDIEM_CODES: List[Dict[str, Any]] = [
    {"code": "S9500", "therapy": "Antibiotic (OPAT)",
     "descriptor": "Antibiotic / antiviral / antifungal, q24h, per diem",
     "published_rate": None},
    {"code": "S9501", "therapy": "Antibiotic (OPAT)",
     "descriptor": "Antibiotic q12h, per diem",
     "published_rate": None},
    {"code": "S9326", "therapy": "Pain management",
     "descriptor": "Continuous (≥24 hr) pain-management infusion, "
                   "per diem",
     "published_rate": 125.64},
    {"code": "S9338", "therapy": "IVIG / immunotherapy",
     "descriptor": "Home immunotherapy infusion, per diem (drug + "
                   "nursing coded separately)",
     "published_rate": 99.66},
    {"code": "S9365", "therapy": "TPN",
     "descriptor": "Home TPN, 1 liter/day, per diem",
     "published_rate": 302.47},
    {"code": "S9366", "therapy": "TPN",
     "descriptor": "Home TPN, 1–2 liters/day, per diem",
     "published_rate": 322.79},
    {"code": "S9368", "therapy": "TPN",
     "descriptor": "Home TPN, >3 liters/day, per diem",
     "published_rate": 381.38},
    {"code": "S9374", "therapy": "Hydration",
     "descriptor": "Home hydration, 1 liter/day, per diem",
     "published_rate": 72.10},
    {"code": "S9363", "therapy": "Anti-spasmodic",
     "descriptor": "Home anti-spasmodic infusion, per diem",
     "published_rate": 149.59},
]

HOME_PERDIEM_NOTE = (
    "S-codes are the commercial / managed-care home-infusion billing "
    "currency — Medicare NEVER pays them (it pays the HIT G-codes + "
    "Part B/DME drug instead), and state Medicaid recognition is "
    "inconsistent. The per-diem bundles pharmacy services, supplies, "
    "care coordination and equipment; the DRUG and NURSING VISITS bill "
    "separately on top. Published rates shown are Montana Medicaid's "
    "Home Infusion Services fee schedule (eff. 2025-07-01) — the only "
    "public S-code price list found; commercial contracts are "
    "confidential and run above the Medicaid floor (the NHIA model "
    "contract orders TPN > antibiotics, matching the Montana "
    "structure). Codes shown with no rate have NO public price — "
    "pull the target's actual contracted per-diems in diligence.")


# ── HOPD comparison — the same visit across the three sites ─────────

#: CY2025 OPPS drug-administration APC payment rates (CMS OPPS pricer /
#: Addendum A, national unadjusted; OPPS CF $89.169). Mapping facts
#: from the CMS IOCE v25.1: 96413/96416 → 5694; 96365/96360/96374 →
#: 5693; 96372/96367/96415/96417 → 5692; 96361/96366/96375 → 5691.
OPPS_DRUG_ADMIN_APCS: List[Dict[str, Any]] = [
    {"apc": "5691", "level": "Level 1 drug administration", "rate": 46.14,
     "maps": "96361, 96366, 96375"},
    {"apc": "5692", "level": "Level 2 drug administration", "rate": 71.17,
     "maps": "96372, 96367, 96415, 96417"},
    {"apc": "5693", "level": "Level 3 drug administration", "rate": 210.69,
     "maps": "96365, 96360, 96374"},
    {"apc": "5694", "level": "Level 4 drug administration", "rate": 331.69,
     "maps": "96413, 96416"},
]


def cross_site_visit_comparison() -> Dict[str, Any]:
    """The SAME drug administration priced at the three sites a payer
    can send it to — HOPD (OPPS APC), office/AIC (PFS non-facility),
    and home (Medicare HIT) — for both Medicare and the published
    commercial benchmarks. Pure recompute from the verified CY2025
    rate tables; the steerage arbitrage in one exhibit."""
    aic = next(c["nonfac"] for c in PFS_ADMIN_CODES
               if c["code"] == "96413")
    hopd = next(a["rate"] for a in OPPS_DRUG_ADMIN_APCS
                if a["apc"] == "5694")
    home = next(g["subsequent"] for g in HIT_G_CODES
                if g["code"] == "G0070")
    # Published commercial anchors: office ≈129% of Medicare (CBO
    # physician-services mean); HOPD = the national MEDIAN negotiated
    # price for 96413 from 1,458 hospitals' transparency files (JCO).
    commercial_office = round(aic * 1.29, 2)
    commercial_hopd = 536.00
    rows = [
        {"site": "Hospital outpatient (HOPD)", "code": "APC 5694",
         "amount": hopd, "vs_aic": round(hopd / aic, 2),
         "commercial": commercial_hopd,
         "commercial_basis": "median negotiated 96413 price across "
                             "1,458 hospitals (JCO 2022)",
         "note": "OPPS Level 4 drug administration (96413 maps here) — "
                 "the rate payers are steering away from"},
        {"site": "Physician office / AIC", "code": "CPT 96413",
         "amount": aic, "vs_aic": 1.0,
         "commercial": commercial_office,
         "commercial_basis": "≈129% of Medicare (CBO physician-"
                             "services benchmark)",
         "note": "PFS non-facility — the AIC admin fee; the steerage "
                 "destination"},
        {"site": "Home (Medicare HIT)", "code": "G0070 (subsequent)",
         "amount": home, "vs_aic": round(home / aic, 2),
         "commercial": None,
         "commercial_basis": "commercial pays per-diem S-codes + "
                             "nursing instead",
         "note": "per nurse-visit DAY only — higher per visit but most "
                 "therapy days pay $0 (the calendar-day gap)"},
    ]
    return {
        "rows": rows,
        "hopd_premium": round(hopd / aic, 2),
        "commercial_hopd_premium": round(commercial_hopd
                                         / commercial_office, 2),
        "note": (
            "Administration fee only — the drug itself pays ASP+6% in "
            "all three sites under Medicare, while commercial HOPD "
            "drug reimbursement averages ≈281% of ASP vs 106% for "
            "Medicare (RAND round 5.1) and HOPD prices run ~2× office "
            "for infused drugs (Health Affairs 2021). Medicare HOPD "
            "pays ≈{:.1f}× the office/AIC admin rate; commercially the "
            "same-visit gap is ≈{:.1f}×. NOTE: from Jan 1 2026, CMS "
            "pays drug-administration APCs at PFS-equivalent rates in "
            "excepted OFF-campus hospital departments (site-neutral "
            "expansion) — the HOPD premium survives on-campus only."
        ).format(hopd / aic, commercial_hopd / commercial_office),
    }


# ── Drug mix → the overall reimbursement rate ────────────────────────

#: Marquee infused drugs with the Medicare ASP payment limit per
#: typical maintenance dose — verified against the CMS quarterly ASP
#: pricing file (Q2 2026 = April 2026, effective 4/1–6/30/2026, via
#: the state-Medicaid verbatim mirror; J1745/Q5121 from Q4 2025).
#: ``asp_unit`` is the published per-unit payment limit (ASP+6%,
#: pre-sequester); ``asp_dose`` = unit × units per dose at an 80-kg
#: adult. The live quarterly ASP pull refreshes per-unit pricing where
#: egress permits (see cms_asp_pricing).
DRUG_DOSE_ECONOMICS: List[Dict[str, Any]] = [
    {"hcpcs": "J1745", "drug": "Infliximab (Remicade, originator)",
     "klass": "Immunology (anti-TNF)", "unit": "per 10 mg",
     "asp_unit": 31.09, "units_dose": 40, "dose": "400 mg q8w (IBD)",
     "asp_dose": 1_243.60, "doses_yr": 6.5,
     "note": "biosimilar competition has collapsed the reference ASP "
             "(Q4 2025 cell)"},
    {"hcpcs": "Q5103", "drug": "Infliximab-dyyb (Inflectra, biosimilar)",
     "klass": "Immunology (anti-TNF)", "unit": "per 10 mg",
     "asp_unit": 26.035, "units_dose": 40, "dose": "400 mg q8w",
     "asp_dose": 1_041.40, "doses_yr": 6.5,
     "note": "the biosimilar price floor — margin moves to the admin fee"},
    {"hcpcs": "J3380", "drug": "Vedolizumab (Entyvio)",
     "klass": "Immunology (IBD)", "unit": "per 1 mg",
     "asp_unit": 20.98, "units_dose": 300, "dose": "300 mg q8w",
     "asp_dose": 6_294.00, "doses_yr": 6.5,
     "note": "no IV biosimilar yet — a durable spread line"},
    {"hcpcs": "J2350", "drug": "Ocrelizumab (Ocrevus)",
     "klass": "Neurology (MS)", "unit": "per 1 mg",
     "asp_unit": 59.596, "units_dose": 600, "dose": "600 mg q6mo",
     "asp_dose": 35_757.60, "doses_yr": 2.0,
     "note": "the highest per-dose revenue in the chair — two visits/yr "
             "≈ $71.5K of drug"},
    {"hcpcs": "J2323", "drug": "Natalizumab (Tysabri)",
     "klass": "Neurology (MS)", "unit": "per 1 mg",
     "asp_unit": 24.321, "units_dose": 300, "dose": "300 mg q4w",
     "asp_dose": 7_296.30, "doses_yr": 13.0,
     "note": "monthly — the chair-utilization annuity"},
    {"hcpcs": "J9312", "drug": "Rituximab (Rituxan, reference)",
     "klass": "Immunology / heme-onc", "unit": "per 10 mg",
     "asp_unit": 74.765, "units_dose": 100,
     "dose": "1,000 mg ×2-dose course q24wk (RA)",
     "asp_dose": 7_476.50, "doses_yr": 4.0,
     "note": "biosimilars undercut hard: Truxima (Q5115) $30.15 and "
             "Ruxience (Q5119) $13.27 per 10 mg vs $74.77 reference"},
    {"hcpcs": "J1569", "drug": "IVIG (Gammagard liquid)",
     "klass": "Immune globulin", "unit": "per 500 mg",
     "asp_unit": 47.288, "units_dose": 80, "dose": "40 g q3–4w",
     "asp_dose": 3_783.04, "doses_yr": 13.0,
     "note": "the home/AIC margin engine — chronic, supply-constrained "
             "(Gamunex-C $98.15/g, Privigen $100.56/g price nearby)"},
    {"hcpcs": "J1439", "drug": "Ferric carboxymaltose (Injectafer)",
     "klass": "IV iron", "unit": "per 1 mg",
     "asp_unit": 1.103, "units_dose": 750, "dose": "750 mg ×2 per course",
     "asp_dose": 827.25, "doses_yr": 2.6,
     "note": "short chair time — high admin-fee yield per chair-hour"},
    {"hcpcs": "J0897", "drug": "Denosumab (Prolia)",
     "klass": "Bone / oncology support", "unit": "per 1 mg",
     "asp_unit": 29.507, "units_dose": 60, "dose": "60 mg SC q6mo",
     "asp_dose": 1_770.42, "doses_yr": 2.0,
     "note": "SC injection (96372) — low admin fee, high throughput"},
    {"hcpcs": "J9332", "drug": "Efgartigimod (Vyvgart)",
     "klass": "Neurology (gMG)", "unit": "per 2 mg",
     "asp_unit": 32.608, "units_dose": 400,
     "dose": "10 mg/kg weekly ×4 per cycle",
     "asp_dose": 13_043.20, "doses_yr": 16.0,
     "note": "the fast-growing neuro line — cycle-based, very high "
             "annual revenue per patient"},
    {"hcpcs": "J1299", "drug": "Eculizumab (Soliris)",
     "klass": "Rare / complement", "unit": "per 2 mg",
     "asp_unit": 45.028, "units_dose": 450, "dose": "900 mg q2w (PNH)",
     "asp_dose": 20_262.60, "doses_yr": 26.0,
     "note": "ultra-high-cost rare disease — AR / stop-loss intensive. "
             "NOTE: J1300 was deactivated 3/31/2025; eculizumab now "
             "bills J1299 (per 2 mg) — a stale-code denial trap. "
             "Ravulizumab (J1303) successor: $224.80/10 mg, 3,300 mg "
             "q8w ≈ $74.2K/dose"},
]

DRUG_DOSE_NOTE = (
    "Medicare ASP payment limits per unit from the CMS quarterly ASP "
    "pricing file — Q2 2026 (April 2026) for most codes, Q4 2025 where "
    "noted — at the published payment limit (ASP+6%, pre-sequester; "
    "net remitted ≈ ASP+4.3% after the 2% sequester on the 80% federal "
    "share). Doses assume an 80-kg adult on the FDA-label maintenance "
    "regimen. The buy-and-bill spread is the payment limit minus GPO "
    "acquisition. Commercial pays the same drugs at contract rates "
    "(AWP-minus or ASP-plus contracts; RAND round 5.1: hospitals "
    "collect ≈281% of ASP commercially vs Medicare's 106%) — a far "
    "wider spread, which is why payer mix decides the drug margin.")

#: AIC revenue mix by therapy class (share of AIC DRUG revenue) — NHIA /
#: operator-disclosure structure (Option Care chronic≈75/acute≈25 split,
#: IVX immunology/neurology focus), restated for a TX AIC book.
AIC_DRUG_MIX: List[Dict[str, Any]] = [
    {"klass": "Immunology (anti-TNF / IBD / rheum)", "share": 0.34},
    {"klass": "Neurology (MS / CIDP / migraine)", "share": 0.22},
    {"klass": "Immune globulin (IVIG/SCIG)", "share": 0.20},
    {"klass": "Oncology support (iron / bone / GCSF)", "share": 0.12},
    {"klass": "Rare disease / complement", "share": 0.07},
    {"klass": "Anti-infectives / hydration / other", "share": 0.05},
]


def drug_mix_economics() -> Dict[str, Any]:
    """Per-drug dose economics + the class mix, with the buy-and-bill
    spread per dose at sequestered ASP+4.3% vs a commercial contract.
    Pure arithmetic on the labeled constants."""
    from ..data.cms_asp_pricing import ASP_ADDON_SEQUESTERED
    rows = []
    for d in DRUG_DOSE_ECONOMICS:
        asp_dose = d["asp_dose"]
        annual = asp_dose * d["doses_yr"]
        # Spread per dose: Medicare = the sequestered add-on portion of
        # the ASP+6 payment; commercial modeled at a 14% contract spread
        # (the AIC payer-anchor used in part 1).
        medicare_spread = asp_dose * (ASP_ADDON_SEQUESTERED / 1.06)
        commercial_spread = asp_dose * 0.14
        rows.append({
            **d,
            "annual_drug_rev": round(annual),
            "medicare_spread_dose": round(medicare_spread),
            "commercial_spread_dose": round(commercial_spread),
        })
    rows.sort(key=lambda r: -r["annual_drug_rev"])
    return {
        "drugs": rows,
        "mix": AIC_DRUG_MIX,
        "note": DRUG_DOSE_NOTE,
        "read": (
            "The mix decides the margin: a commercial infliximab-"
            "biosimilar visit earns a thin drug spread + admin fee, an "
            "IVIG or Ocrevus visit earns 5–20× the dollars in the same "
            "chair hour. Drug mix × payer mix IS the AIC P&L."),
    }


# ── Payer yield — the overall reimbursement rate per infusion ────────

#: Per-payer realization vs the Medicare benchmark for the SAME
#: office/AIC infusion: index = net collected revenue per infusion
#: relative to Medicare FFS = 1.00. The commercial index follows the
#: published professional-services benchmarks (HCCI 122% / CBO 129% /
#: KFF 143% / MedPAC PPO 134–140% / Milliman 148% of Medicare) plus a
#: wider contracted drug spread; MA ≈ Medicare rates minus prior-auth/
#: denial drag; Medicaid below Medicare (TMHP); self-pay mostly
#: charity. Labeled analyst anchors on published ranges.
PAYER_YIELD: List[Dict[str, Any]] = [
    {"payer": "Commercial / employer", "index": 1.35,
     "note": "admin codes ≈122–148% of Medicare (HCCI/CBO/KFF/MedPAC/"
             "Milliman) + a wider contracted drug spread; the margin "
             "pool"},
    {"payer": "Medicare FFS (Part B)", "index": 1.00,
     "note": "PFS admin + ASP+6 drug (sequestered ≈+4.3) — the "
             "benchmark"},
    {"payer": "Medicare Advantage", "index": 0.95,
     "note": "≈Medicare rates minus prior-auth friction, steerage and "
             "denial drag"},
    {"payer": "Medicaid (TX STAR/managed)", "index": 0.72,
     "note": "TMHP fee schedule pays below Medicare; MCO contracts "
             "vary"},
    {"payer": "Self-pay / uninsured", "index": 0.18,
     "note": "charity / sliding scale — mostly uncollected"},
]


def overall_reimbursement_rate() -> Dict[str, Any]:
    """The blended net reimbursement per infusion: part-1 payer mix ×
    the per-payer yield index, anchored so the blend reproduces the
    part-1 $650 revenue-per-infusion exactly. Splitting Medicare into
    FFS vs MA uses the verified TX MA penetration (54% of TX Medicare
    beneficiaries, Sept 2024). Shows WHERE the blended dollar comes
    from."""
    mix = _payer_mix()
    # Split the part-1 Medicare bucket FFS vs MA at TX MA penetration.
    rows: List[Dict[str, Any]] = []
    for p in mix:
        if p["payer"].startswith("Medicare"):
            rows.append({"payer": "Medicare Advantage",
                         "share": round(p["share"] * 0.54, 3)})
            rows.append({"payer": "Medicare FFS (Part B)",
                         "share": round(p["share"] * 0.46, 3)})
        elif p["payer"].startswith("Medicaid"):
            rows.append({"payer": "Medicaid (TX STAR/managed)",
                         "share": p["share"]})
        elif p["payer"].startswith("Self-pay"):
            rows.append({"payer": "Self-pay / uninsured",
                         "share": p["share"]})
        else:
            rows.append({"payer": "Commercial / employer",
                         "share": p["share"]})
    idx = {y["payer"]: y for y in PAYER_YIELD}
    weighted_index = sum(r["share"] * idx[r["payer"]]["index"]
                         for r in rows)
    # Anchor: blended revenue per infusion = part-1 $650. Solve the
    # Medicare-equivalent unit so mix × index × unit = 650.
    medicare_unit = REVENUE_PER_INFUSION / weighted_index
    for r in rows:
        y = idx[r["payer"]]
        r["index"] = y["index"]
        r["note"] = y["note"]
        r["revenue_per_infusion"] = round(medicare_unit * y["index"])
        r["contribution"] = round(
            r["share"] * medicare_unit * y["index"], 2)
    blended = sum(r["contribution"] for r in rows)
    return {
        "rows": rows,
        "medicare_equivalent_unit": round(medicare_unit),
        "weighted_index": round(weighted_index, 3),
        "blended_revenue_per_infusion": round(blended),
        "anchor": REVENUE_PER_INFUSION,
        "note": (
            "Per-payer yield indices (Medicare FFS = 1.00) from "
            "published commercial-vs-Medicare admin-code benchmarks, "
            "MedPAC and TMHP structure — illustrative. The blend is "
            "anchored to the part-1 $650/infusion so the two pages "
            "reconcile; the table shows what that average HIDES: a "
            "commercial infusion collects ≈2.5× a Medicaid one."),
    }


# ── Channel sizing — AIC and home, bottom-up, reconciled to part 1 ───

#: Relative revenue-per-infusion index by site (office/AIC = 1.00).
#: HOPD bills the same service at a multiple (OPPS + chargemaster drug
#: markup); home blends lower-cost OPAT + per-diem service revenue.
#: Magnitudes follow the published rate tables above.
SITE_PRICE_INDEX = {
    "Home infusion": 0.72,
    "Ambulatory infusion suite (AIS)": 1.00,
    "Hospital outpatient (HOPD)": 2.10,
    "Physician office (buy-and-bill)": 1.00,
}


def channel_sizing(tx_patients: int) -> Dict[str, Any]:
    """Bottom-up AIC + home channel sizing that reconciles EXACTLY to
    the part-1 TAM: patients × 18 infusions/yr split by the part-1
    site-of-care shares, each site priced at its relative index, with
    the index scale solved so the blended revenue/infusion equals the
    part-1 $650 anchor. The granular layer the top-down number hides."""
    sites = _site_of_care()
    total_infusions = tx_patients * INFUSIONS_PER_PATIENT_YR
    # Solve the AIC-equivalent unit price U: Σ share×idx×U = $650.
    wsum = sum(s["share"] * SITE_PRICE_INDEX[s["site"]] for s in sites)
    unit = REVENUE_PER_INFUSION / wsum
    rows = []
    for s in sites:
        idx = SITE_PRICE_INDEX[s["site"]]
        infusions = total_infusions * s["share"]
        rev_per = unit * idx
        rows.append({
            "site": s["site"], "share": s["share"],
            "price_index": idx,
            "infusions": round(infusions),
            "revenue_per_infusion": round(rev_per),
            "revenue": round(infusions * rev_per),
            "growth_pct": s["growth_pct"],
        })
    tam_check = sum(r["revenue"] for r in rows)
    aic = next(r for r in rows if "AIS" in r["site"])
    home = next(r for r in rows if r["site"] == "Home infusion")
    return {
        "rows": rows,
        "unit_aic_revenue_per_infusion": round(unit),
        "tam_check": tam_check,
        "aic": aic,
        "home": home,
        "note": (
            "Bottom-up: TX patients × 18 infusions/yr × site share × "
            "per-site revenue/infusion. The per-site prices are solved "
            "against the part-1 $650 blended anchor with the relative "
            "price structure from the published rate tables (HOPD "
            "≈2.1× the AIC rate; home ≈0.7×), so the channel build "
            "sums EXACTLY to the part-1 TAM — same model, finer grain."),
    }


# ════════════════════════════════════════════════════════════════════
# Payer structure by metro — PPO/HMO concentration + insurer shares
# ════════════════════════════════════════════════════════════════════

#: Commercial product mix (covered workers) — KFF Employer Health
#: Benefits Survey 2025: PPO 46%, HDHP/SO 33%, HMO 12%, POS 9%.
#: HDHP/SO + POS are predominantly open-access (PPO-style) networks,
#: and 67% of covered workers are in self-funded ERISA plans (almost
#: all open-access). The structural read: TX commercial is ~88%
#: open-access / ~12% gatekeeper-HMO.
COMMERCIAL_PRODUCT_MIX = {"ppo": 0.46, "hdhp": 0.33, "hmo": 0.12,
                          "pos": 0.09}

#: Texas MA product split — HMO ≈59% / local PPO ≈40% of TX plan
#: offerings (KFF/state aggregators, directional); national MA
#: enrollment runs HMO 54–56% / local PPO 43–45% (KFF 2024–25).
TX_MA_HMO_SHARE = 0.59

#: Texas Medicaid runs through STAR managed care — gatekeeper MCO
#: (HMO-style) by construction.
MEDICAID_HMO_SHARE = 1.0

#: Per-metro payer structure. MA penetration is the VERIFIED core-
#: county rate (% of Medicare beneficiaries in MA, CMS data via county
#: enrollment pages, 2025). Insurer facts from the AMA Competition in
#: Health Insurance study (2025 edition, 2024 data) via TMA: HCSC
#: (BCBSTX) holds the largest commercial share in ALL 26 Texas metros,
#: from 37% (Austin) to 74% (Abilene); Aetna is #2 in 13 of 26 (TX
#: share ≈19%); Cigna #2 in 10 (DFW #2 at 23%). Exact HCSC shares for
#: Houston/DFW/San Antonio sit in the member-gated AMA tables — shown
#: as the published band, flagged est, never invented.
METRO_PAYER_LANDSCAPE: List[Dict[str, Any]] = [
    {"metro": "Houston", "core_county": "Harris",
     "ma_penetration": 0.613,
     "hcsc_share": None, "hcsc_band": "37–74% (AMA TX-metro band)",
     "number_two": "Aetna/CVS (TX #2 overall, ≈19% statewide)",
     "ring_ma": "Fort Bend / Montgomery run below Harris",
     "note": "BCBSTX #1; the HIGHEST big-metro MA penetration (61.3% "
             "of Harris Medicare) — the steered book is the majority "
             "of seniors here"},
    {"metro": "Dallas-Fort Worth", "core_county": "Dallas / Tarrant",
     "ma_penetration": 0.553,
     "hcsc_share": None, "hcsc_band": "37–74% (AMA TX-metro band)",
     "number_two": "Cigna #2 at 23% (its highest TX share)",
     "ring_ma": "Collin 42.1% — the affluent ring stays FFS/commercial",
     "note": "BCBSTX #1, Cigna's TX stronghold; Dallas 54.8% / Tarrant "
             "55.8% MA; KFF flags Dallas MA as highly concentrated"},
    {"metro": "Austin", "core_county": "Travis",
     "ma_penetration": 0.475,
     "hcsc_share": 0.37, "hcsc_band": "37% — published (the TX floor)",
     "number_two": "UHC / Aetna contest #2",
     "ring_ma": "Williamson 47.9% / Hays 49.9%",
     "note": "the ONLY big TX metro with a published HCSC share (37%) "
             "— least HCSC-concentrated AND lowest MA penetration: "
             "the most commercial-friendly payer map in Texas"},
    {"metro": "San Antonio", "core_county": "Bexar",
     "ma_penetration": 0.585,
     "hcsc_share": None, "hcsc_band": "37–74% (AMA TX-metro band)",
     "number_two": "Humana / UHC (military-retiree MA legacy)",
     "ring_ma": "Comal / Guadalupe lower",
     "note": "58.5% MA in Bexar, HMO-led — heavy steerage + prior-auth "
             "exposure, AND it pays Rest-of-Texas PFS rates: the "
             "thinnest payer map of the four"},
]

METRO_PAYER_NOTE = (
    "Insurer concentration: AMA Competition in Health Insurance, 2025 "
    "edition (2024 data) via TMA — HCSC/BCBSTX is #1 in every one of "
    "the 26 TX metros (37% Austin … 74% Abilene; exact Houston/DFW/San "
    "Antonio shares are member-gated, shown as the published band). "
    "97% of US MSA commercial markets are highly concentrated (avg "
    "HHI 3,486). MA penetration: CMS county enrollment (2025) — % of "
    "Medicare beneficiaries in MA. Product mix: KFF EHBS 2025 "
    "national covered-worker splits (PPO 46 / HDHP 33 / HMO 12 / POS "
    "9; 67% self-funded). Replace with license-grade pulls (AIS / "
    "Interstudy) before IC.")


def metro_payer_analysis() -> Dict[str, Any]:
    """Per-metro payer structure + the PPO/HMO concentration read.

    The HMO-EXPOSURE index = share of the metro's PAID infusion volume
    sitting behind a gatekeeper/steered product, computed from the
    part-1 payer revenue mix re-weighted with the metro's VERIFIED MA
    penetration: commercial × 12% HMO + Medicare × (MA pen × 59% TX
    MA-HMO) + Medicaid × 100% (STAR MCO). Self-pay carries none.
    Buy-and-bill friendliness inverts it and credits the FFS+PPO pool.
    Pure recompute from labeled anchors."""
    mix = {p["payer"].split(" ")[0]: p["share"] for p in _payer_mix()}
    commercial = mix.get("Commercial", 0.45)
    medicare = mix.get("Medicare", 0.35)
    medicaid = mix.get("Medicaid", 0.12)
    out = []
    for m in METRO_PAYER_LANDSCAPE:
        ma_pen = m["ma_penetration"]
        hmo_exposure = (
            commercial * COMMERCIAL_PRODUCT_MIX["hmo"]
            + medicare * ma_pen * TX_MA_HMO_SHARE
            + medicaid * MEDICAID_HMO_SHARE)
        ppo_open = (commercial * (1 - COMMERCIAL_PRODUCT_MIX["hmo"])
                    + medicare * (1 - ma_pen)
                    + medicare * ma_pen * (1 - TX_MA_HMO_SHARE))
        friendly = round(100 * (0.60 * ppo_open
                                + 0.40 * (1 - hmo_exposure)), 1)
        out.append({
            **m,
            "hmo_exposure": round(hmo_exposure, 3),
            "open_access_share": round(ppo_open, 3),
            "buyandbill_friendliness": friendly,
        })
    out.sort(key=lambda m: -m["buyandbill_friendliness"])
    for i, m in enumerate(out, 1):
        m["rank"] = i
    return {
        "metros": out,
        "product_mix": COMMERCIAL_PRODUCT_MIX,
        "tx_ma_hmo_share": TX_MA_HMO_SHARE,
        "note": METRO_PAYER_NOTE,
        "hcsc_facts": (
            "HCSC / BCBSTX: ~10.4M Texas members across all 254 "
            "counties; ≈70% of the TX RISK-BASED (fully-insured) "
            "commercial market by premium (S&P on HCSC, YE2022); #1 "
            "commercial share in all 26 TX metros (AMA 2025). It owns "
            "NO infusion asset — which makes the BCBSTX contract the "
            "single most valuable independent-provider agreement in "
            "the state."),
        "read": (
            "Texas commercial is an open-access market (≈88% PPO/HDHP/"
            "POS, only ≈12% gatekeeper HMO) dominated by one Blue — "
            "so buy-and-bill lives or dies on the HCSC relationship. "
            "The HMO concentration sits in MEDICARE (54% of TX "
            "beneficiaries in MA, ≈59% of it HMO) and Medicaid STAR — "
            "which is why San Antonio (58.5% MA, Rest-of-TX rates) "
            "screens hardest and Austin (47.5% MA, HCSC at just 37%) "
            "screens friendliest for an independent platform."),
    }


# ── In-network matrix — operators × plans ────────────────────────────

_PLANS = ["BCBS TX", "UnitedHealthcare", "Aetna/CVS", "Cigna", "Humana",
          "TX Medicaid (STAR MCOs)"]

#: In-network status per operator per plan, from each operator's OWN
#: public payer disclosures + directories (researched June 2026):
#: "in" = named/stated in-network; "owned" = the payer owns the
#: operator (steered volume); "rpt" = operator states "most insurances
#: accepted" but the named plan was NOT publicly confirmed — verify;
#: "ltd" = selective / certain plans only. Networks are contract-by-
#: contract (often therapy-by-therapy); verify per NPI in diligence.
NETWORK_MATRIX: List[Dict[str, Any]] = [
    {"operator": "Option Care Health",
     "status": {"BCBS TX": "in", "UnitedHealthcare": "in",
                "Aetna/CVS": "in", "Cigna": "in", "Humana": "in",
                "TX Medicaid (STAR MCOs)": "ltd"},
     "note": "discloses in-network with 96% of US insured lives, "
             "800+ plans incl. CMS — the broadest network in the "
             "channel; scale = leverage"},
    {"operator": "IVX Health (AIC)",
     "status": {"BCBS TX": "rpt", "UnitedHealthcare": "in",
                "Aetna/CVS": "in", "Cigna": "in", "Humana": "in",
                "TX Medicaid (STAR MCOs)": "ltd"},
     "note": "names Aetna/Anthem-BCBS/Cigna/Humana/UHC/Medicare + "
             "Medicaid in certain states; BCBSTX (HCSC) specifically "
             "not in the published payor list — confirm"},
    {"operator": "Paragon Healthcare",
     "status": {"BCBS TX": "in", "UnitedHealthcare": "in",
                "Aetna/CVS": "in", "Cigna": "in", "Humana": "in",
                "TX Medicaid (STAR MCOs)": "in"},
     "note": "Elevance-owned (closed 2024-03-11, ~$1B; CarelonRx) — "
             "directory lists BCBSTX/Aetna/Cigna/Humana/UHC/Amerigroup/"
             "Molina/Wellcare. NOTE: BCBSTX is HCSC, not Elevance — no "
             "captive TX Blue book"},
    {"operator": "Optum Infusion",
     "status": {"BCBS TX": "rpt", "UnitedHealthcare": "owned",
                "Aetna/CVS": "rpt", "Cigna": "rpt", "Humana": "rpt",
                "TX Medicaid (STAR MCOs)": "ltd"},
     "note": "UnitedHealth-owned — UHC's site-of-care policy caps HOPD "
             "infusion at ~6 months and relocates members to "
             "participating home/AIC sites, with Optum running the "
             "prior-auth reviews"},
    {"operator": "Coram (CVS Health)",
     "status": {"BCBS TX": "in", "UnitedHealthcare": "in",
                "Aetna/CVS": "owned", "Cigna": "in", "Humana": "in",
                "TX Medicaid (STAR MCOs)": "ltd"},
     "note": "CVS/Aetna-owned — 'in-network with most national and "
             "local private plans' (medical benefit; may be OON on "
             "pharmacy benefit). Closed 36 of 71 branches in 2023 — "
             "confirm surviving TX suites"},
    {"operator": "Soleo Health",
     "status": {"BCBS TX": "in", "UnitedHealthcare": "in",
                "Aetna/CVS": "in", "Cigna": "in", "Humana": "in",
                "TX Medicaid (STAR MCOs)": "in"},
     "note": "Frisco-TX-HQ'd; states participation in 'all major "
             "national, regional and local plans, PBMs, Medicare and "
             "Medicaid'; Austin AIC opened Apr 2026"},
    {"operator": "KabaFusion",
     "status": {"BCBS TX": "in", "UnitedHealthcare": "in",
                "Aetna/CVS": "in", "Cigna": "rpt", "Humana": "rpt",
                "TX Medicaid (STAR MCOs)": "ltd"},
     "note": "payors page names Medicare, Medicaid, BCBS, Aetna, "
             "United; Memorial Hermann (Houston) is an investor — a "
             "health-system referral channel"},
    {"operator": "Vital Care (franchise)",
     "status": {"BCBS TX": "rpt", "UnitedHealthcare": "in",
                "Aetna/CVS": "in", "Cigna": "in", "Humana": "in",
                "TX Medicaid (STAR MCOs)": "ltd"},
     "note": "national contracts with Aetna, Cigna, Humana, UHC; 6–8 "
             "TX franchises skewed to secondary markets (Lubbock, El "
             "Paso, Richmond)"},
    {"operator": "HealthQuest Infusion & Specialty",
     "status": {"BCBS TX": "rpt", "UnitedHealthcare": "in",
                "Aetna/CVS": "rpt", "Cigna": "rpt", "Humana": "rpt",
                "TX Medicaid (STAR MCOs)": "in"},
     "note": "states 'accepts most insurances'; NAMED: Preferred "
             "Infusion Provider for Community Health Choice (Houston "
             "Medicaid/CHIP/marketplace MCO) + UHC-KelseyCare/PGT "
             "contract — the payer-relationship wedge of a regional"},
]

NETWORK_NOTE = (
    "From operators' own public payer pages, directories and press "
    "(June 2026) — 'rpt' marks operators stating broad acceptance "
    "without the named plan publicly confirmed. 'Owned' marks vertical "
    "integration: that payer's volume routes to its own asset FIRST "
    "(UHC→Optum, Aetna→Coram, Elevance→Paragon), which is exactly why "
    "independents compete on convenience + experience. The decisive "
    "TX fact: HCSC/BCBSTX — ~70% of the fully-insured commercial "
    "market — owns NO infusion asset, so its network is open to "
    "independents and is the single most valuable contract in the "
    "state. Verify all of this per-NPI in diligence.")


def network_access_by_metro() -> Dict[str, Any]:
    """Cross the network matrix with each metro's operator presence
    (part 1): for each metro × plan, how many in-network infusion
    options a member actually has — the access map that decides where
    referral convenience wins."""
    from .texas_infusion import _METRO_OPERATORS
    # Map matrix operator names onto the part-1 metro presence lists.
    alias = {
        "Option Care Health": "Option Care Health",
        "Coram (CVS Health)": "CVS Health / Coram",
        "Optum Infusion": "Optum Infusion",
        "Soleo Health": "Soleo Health",
        "KabaFusion": "KabaFusion",
        "Paragon Healthcare": "Paragon Healthcare (Elevance)",
    }
    # IVX / Vital Care / HealthQuest metro presence from their public
    # site lists (they are not in the part-1 operator map).
    extra_presence = {
        "IVX Health (AIC)": {"Houston", "Dallas-Fort Worth-Arlington",
                             "San Antonio-New Braunfels",
                             "Austin-Round Rock-San Marcos"},
        "Vital Care (franchise)": {"Houston",
                                   "Dallas-Fort Worth-Arlington",
                                   "San Antonio-New Braunfels",
                                   "Austin-Round Rock-San Marcos"},
        "HealthQuest Infusion & Specialty": {"Houston"},
    }
    metros = list(_METRO_OPERATORS)
    rows = []
    for metro in metros:
        present = set(_METRO_OPERATORS[metro])
        cell: Dict[str, int] = {}
        for plan in _PLANS:
            n = 0
            for op in NETWORK_MATRIX:
                here = (alias.get(op["operator"], "") in present
                        or metro in extra_presence.get(op["operator"],
                                                       set()))
                if here and op["status"][plan] in ("in", "owned"):
                    n += 1
            cell[plan] = n
        rows.append({"metro": metro.split("-")[0], "options": cell})
    return {
        "plans": _PLANS,
        "rows": rows,
        "matrix": NETWORK_MATRIX,
        "note": NETWORK_NOTE,
    }


# ════════════════════════════════════════════════════════════════════
# Proximity — population density, distance to infusion, drive time
# ════════════════════════════════════════════════════════════════════

#: Census 2020 land area (sq mi) for the core metro counties —
#: verified against the official cb_2020_us_county_500k boundary file
#: (ALAND ÷ 2.59e6; matches QuickFacts' "Land area, 2020" exactly).
#: Population comes live from the vendored ACS county data.
COUNTY_LAND_SQMI: Dict[str, Tuple[str, float]] = {
    # fips: (county, land area sq mi, Census 2020)
    "48201": ("Harris", 1_706.96),
    "48157": ("Fort Bend", 861.72),
    "48339": ("Montgomery", 1_042.18),
    "48167": ("Galveston", 379.29),
    "48039": ("Brazoria", 1_363.33),
    "48113": ("Dallas", 873.05),
    "48439": ("Tarrant", 865.28),
    "48085": ("Collin", 841.25),
    "48121": ("Denton", 878.50),
    "48453": ("Travis", 994.05),
    "48491": ("Williamson", 1_115.83),
    "48209": ("Hays", 676.85),
    "48029": ("Bexar", 1_240.32),
    "48091": ("Comal", 559.53),
    "48187": ("Guadalupe", 711.25),
    "48245": ("Jefferson", 876.76),
}

#: Average metro driving speed for the drive-time proxy (urban arterial +
#: highway blend) and the detour factor that turns straight-line into road miles.
DRIVE_MPH = 35.0
ROAD_DETOUR_FACTOR = 1.30


def county_proximity_model() -> Dict[str, Any]:
    """Distance-to-infusion per core metro county.

    Real inputs: ACS county population (vendored) + Census land area.
    Centers per county re-use the part-1 estimate (national AIS count
    scaled by population). Expected distance to the NEAREST center uses
    the standard spatial-statistics result for points in an area —
    E[d] ≈ 0.5 / sqrt(centers per sq mi) — converted to road miles and
    minutes. A documented geometric model, not a geocoded roster: it
    shows the ORDER of access differences between counties honestly."""
    from ..data.county_demographics import demographics_county
    from .texas_infusion import US_AIS_CENTERS
    rows = []
    for fips, (name, area) in COUNTY_LAND_SQMI.items():
        d = demographics_county(fips) or {}
        pop = float(d.get("population") or 0)
        if not pop:
            continue
        centers = max(1, round(US_AIS_CENTERS * pop / US_POPULATION_2024))
        density = pop / area
        center_density = centers / area
        straight = 0.5 / math.sqrt(center_density)
        road = straight * ROAD_DETOUR_FACTOR
        minutes = road / DRIVE_MPH * 60
        rows.append({
            "county": name, "fips": fips,
            "population": round(pop),
            "land_sqmi": area,
            "pop_density": round(density, 1),
            "est_centers": centers,
            "avg_miles_to_nearest": round(road, 1),
            "avg_minutes": round(minutes),
            "band": ("convenient" if minutes <= 15 else
                     "acceptable" if minutes <= 30 else "burdened"),
        })
    rows.sort(key=lambda r: r["avg_minutes"])
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return {
        "counties": rows,
        "drive_mph": DRIVE_MPH,
        "detour_factor": ROAD_DETOUR_FACTOR,
        "note": (
            "Expected distance to the nearest infusion option per "
            "county: E[d] ≈ 0.5/√(centers per sq mi) (nearest-neighbor "
            "distance for dispersed points), ×1.30 road-detour factor, "
            "at a 35-mph metro highway blend. Centers are the part-1 "
            "population-scaled estimates; land areas are Census. A "
            "labeled spatial model — replace with geocoded NPPES sites "
            "+ real drive-time isochrones in diligence."),
        "read": (
            "Density is destiny for infusion access: the urban-core "
            "counties (Dallas, Harris, Tarrant, Bexar) put the average "
            "patient within a ~15-minute drive of a chair, while the "
            "growth-ring counties (Montgomery, Williamson, Comal, "
            "Brazoria) run 2–3× that — the same counties part 1 flags "
            "as undersupplied. Convenience white-space and demand "
            "white-space are the SAME counties."),
    }


# ════════════════════════════════════════════════════════════════════
# HealthQuest Infusion & Specialty — the convenience-thesis operator
# ════════════════════════════════════════════════════════════════════

#: HealthQuest site list — public company locations (hqrx.com,
#: corroborated by the NPI registry + directories, June 2026), with
#: approximate coordinates for the proximity math (public map facts).
#: ``status``: open = confirmed facility; service = stated home-
#: infusion service area (no confirmed street address); announced =
#: "coming soon" per the company site.
HEALTHQUEST_SITES: List[Dict[str, Any]] = [
    {"city": "Houston (HQ — Beltway 8 W / Spring Branch)",
     "address": "1311 W Sam Houston Pkwy N, Suite 100, Houston, TX 77043",
     "lat": 29.802, "lon": -95.558,
     "kind": "Ambulatory infusion center + home-infusion & specialty "
             "pharmacy (NPI 1831561091)",
     "status": "open"},
    {"city": "Beaumont",
     "address": "2955 Harrison Ave, Suite 204, Beaumont, TX 77702",
     "lat": 30.086, "lon": -94.126, "kind": "Infusion center",
     "status": "open"},
    {"city": "The Woodlands (north Houston)",
     "address": "Stated home-infusion service area — no street "
                "address published",
     "lat": 30.166, "lon": -95.461, "kind": "Home-infusion service area",
     "status": "service"},
    {"city": "Austin",
     "address": "'Coming soon' per hqrx.com — no opening confirmed",
     "lat": 30.267, "lon": -97.743, "kind": "Infusion center",
     "status": "announced"},
]

#: Houston-metro population centers (city, lat, lon, ~population) —
#: public map/Census facts for the drive-proximity read.
HOUSTON_POP_CENTERS: List[Dict[str, Any]] = [
    {"place": "Downtown Houston", "lat": 29.760, "lon": -95.370,
     "pop": 2_314_000},
    {"place": "Katy", "lat": 29.786, "lon": -95.825, "pop": 370_000},
    {"place": "Sugar Land", "lat": 29.620, "lon": -95.635, "pop": 111_000},
    {"place": "Cypress", "lat": 29.969, "lon": -95.697, "pop": 200_000},
    {"place": "The Woodlands", "lat": 30.166, "lon": -95.461,
     "pop": 120_000},
    {"place": "Spring", "lat": 30.080, "lon": -95.417, "pop": 62_000},
    {"place": "Pearland", "lat": 29.564, "lon": -95.286, "pop": 131_000},
    {"place": "Pasadena", "lat": 29.691, "lon": -95.209, "pop": 148_000},
    {"place": "Baytown", "lat": 29.736, "lon": -94.977, "pop": 84_000},
    {"place": "League City", "lat": 29.508, "lon": -95.095, "pop": 118_000},
    {"place": "Conroe", "lat": 30.312, "lon": -95.456, "pop": 106_000},
]

HEALTHQUEST_PROFILE = {
    "name": "HealthQuest Infusion & Specialty (HQRx)",
    "hq": "Houston, TX (1311 W Sam Houston Pkwy N, Suite 100)",
    "founded": "2008 (parent, founded by two generations of "
               "pharmacists; the infusion/specialty entity's NPI "
               "enumerated 2015)",
    "ownership": "Independent, founder/pharmacist-owned (CEO Shaukat "
                 "Zakaria); no PE backing found",
    "channels": "Ambulatory infusion center + home infusion + "
                "specialty pharmacy (hospital-to-home transition; "
                "24/7 pharmacists; overnight medication shipping)",
    "accreditation": "ACHC + URAC dual accreditation; PCAB "
                     "(compounding); NHIA member; USP <800> compliant "
                     "(self-reported — confirm in directories)",
    "therapies": "Biologics (Remicade, Entyvio — IBD/rheum/neuro), "
                 "IVIG/SCIG, anti-infectives (OPAT), TPN + enteral, "
                 "factor replacement, hydration & IV iron",
    "payers": "States 'accepts most insurances'; NAMED: Preferred "
              "Infusion Provider for Community Health Choice "
              "(Houston-area Medicaid/CHIP/marketplace MCO) and a "
              "UHC-KelseyCare/PGT contract; self-pay programs",
    "experience": "Private AIC rooms with massage chairs, desk space, "
                  "music, games, snack bar; same-day home-infusion "
                  "starts 'often'; same-day home-health coordination; "
                  "Google rating >4.5 (Trustindex badge)",
    "scale": "Regional — ~20–50 employees, single-digit-$M revenue "
             "per third-party estimates (low confidence; wide spread)",
    "positioning": (
        "Referral-for-convenience: the pitch to the prescriber is "
        "speed and proximity, not brand — fast benefit investigation, "
        "same-day/same-week starts, a Beltway-8-west chair site plus "
        "home-infusion coverage across greater Houston / The "
        "Woodlands / Beaumont, and white-glove physician service. A "
        "payer wedge built on the plans the nationals serve least "
        "(Community Health Choice preferred status, KelseyCare)."),
    "web": "https://hqrx.com",
}

#: Named competitor infusion sites in the Houston metro — public
#: locator facts (company location pages, June 2026). The proximity
#: read: who else is within the same drive-sheds HealthQuest serves.
HOUSTON_COMPETITOR_SITES: List[Dict[str, Any]] = [
    {"operator": "IVX Health", "sites": [
        "Bellaire", "Cinco Ranch (Katy)", "Clear Lake", "Cypress",
        "Katy", "Spring", "Sugar Land", "The Woodlands",
        "Medical Center"],
     "model": "private-suite AIC chain (20+ TX centers)"},
    {"operator": "Option Care Health", "sites": [
        "Houston (Kirby Dr)", "Clear Lake (Mercury Dr)", "Sugar Land",
        "Katy", "The Woodlands"],
     "model": "national home + infusion-suite platform"},
    {"operator": "Paragon Healthcare (Elevance)", "sites": [
        "Bellaire", "West Houston", "Clear Lake (Webster)", "Katy"],
     "model": "payer-owned AIC"},
    {"operator": "KabaFusion", "sites": [
        "Houston (10920 W Sam Houston Pkwy N — same parkway as "
        "HealthQuest, ~6 road-miles north)"],
     "model": "IG-led home infusion (Memorial Hermann investor)"},
    {"operator": "Optum Infusion", "sites": [
        "Houston (4620 S Sam Houston Pkwy W)"],
     "model": "UnitedHealth-owned home/suite pharmacy"},
    {"operator": "Soleo Health", "sites": ["Houston (pharmacy + AIC)"],
     "model": "specialty/complex home + suite"},
    {"operator": "Vital Care (franchise)", "sites": [
        "Richmond", "Greater Heights"],
     "model": "franchise home-infusion pharmacies"},
]


def _haversine_miles(lat1: float, lon1: float,
                     lat2: float, lon2: float) -> float:
    """Great-circle distance in statute miles (standard haversine)."""
    r = 3_958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = (math.sin(dp / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


def healthquest_proximity() -> Dict[str, Any]:
    """The HealthQuest convenience read: road miles + drive minutes
    from each Houston-metro population center to the NEAREST open
    HealthQuest site, population-weighted. Real geometry on public
    coordinates (haversine × road-detour ÷ metro speed)."""
    open_sites = [s for s in HEALTHQUEST_SITES if s["status"] == "open"]
    rows = []
    for c in HOUSTON_POP_CENTERS:
        best = min(open_sites, key=lambda s: _haversine_miles(
            c["lat"], c["lon"], s["lat"], s["lon"]))
        straight = _haversine_miles(c["lat"], c["lon"],
                                    best["lat"], best["lon"])
        road = straight * ROAD_DETOUR_FACTOR
        minutes = road / DRIVE_MPH * 60
        rows.append({
            "place": c["place"], "pop": c["pop"],
            "nearest_site": best["city"].split(" (")[0],
            "road_miles": round(road, 1),
            "drive_minutes": round(minutes),
            "within_30": minutes <= 30,
        })
    rows.sort(key=lambda r: r["drive_minutes"])
    total_pop = sum(r["pop"] for r in rows)
    within = sum(r["pop"] for r in rows if r["within_30"])
    wavg = (sum(r["pop"] * r["drive_minutes"] for r in rows) / total_pop
            if total_pop else 0.0)
    return {
        "profile": HEALTHQUEST_PROFILE,
        "sites": HEALTHQUEST_SITES,
        "centers": rows,
        "competitors": HOUSTON_COMPETITOR_SITES,
        "pop_within_30min": within,
        "pop_total": total_pop,
        "pct_within_30min": round(within / total_pop, 3) if total_pop else 0,
        "weighted_avg_minutes": round(wavg),
        "note": (
            "Drive proximity from the Houston-metro population centers "
            "to the nearest OPEN HealthQuest chair site (Houston "
            "Beltway-8 W + Beaumont) — haversine miles × 1.30 road "
            "detour at a 35-mph metro highway blend on public coordinates. "
            "The two-part read: the CHAIR footprint is convenient for "
            "the west-side population mass, and the HOME-infusion "
            "service area (greater Houston, The Woodlands, Beaumont) "
            "covers everyone the drive doesn't — convenience by chair "
            "where dense, by nurse where not. That hybrid IS the "
            "referral pitch."),
        "read": (
            "Why it matters for the thesis: referral-for-convenience "
            "is how a regional independent holds share against scale "
            "— and the competition is genuinely close: IVX runs ~9 "
            "private-suite centers across the same metro, and "
            "KabaFusion sits on the SAME parkway ~6 road-miles north. "
            "What the prescriber decides on is 'where will my patient "
            "actually GO, reliably, this week?' — drive time, fast "
            "benefit investigation, and same-day/same-week starts "
            "answer it, and the published evidence backs the lever "
            "(80% of patients say they'd switch providers on "
            "convenience alone — NRC Health). HealthQuest is the live "
            "Texas proof of the convenience wedge — which is exactly "
            "the playbook (and the tuck-in shortlist) for a platform "
            "build."),
    }


# ════════════════════════════════════════════════════════════════════
# Patient experience — the demand-side moat
# ════════════════════════════════════════════════════════════════════

#: Experience drivers with PUBLISHED evidence anchors (peer-reviewed
#: + industry studies, researched June 2026). Weights are the analyst
#: framework (sum to 1.00) — the evidence is sourced, the weighting is
#: a documented judgment.
EXPERIENCE_DRIVERS: List[Dict[str, Any]] = [
    {"driver": "Time to first infusion",
     "metric": "referral → first dose (days)",
     "benchmark": "home/specialty industry mean 14.6 days referral→"
                  "dispense (NHIF 2024); PA adds the delay — 71% of "
                  "infusible orders need PA, denials add ~1 month "
                  "(Arthritis Care & Res 2020); Medicaid/Medicare PA "
                  "49–53 days vs 19 commercial (JNMA 2024)",
     "why": "the single biggest referral-source satisfier — benefit-"
            "investigation + prior-auth speed is a process asset; 82% "
            "of physicians say PA delays sometimes cause treatment "
            "abandonment (AMA 2024)",
     "weight": 0.25},
    {"driver": "Drive time / location",
     "metric": "minutes door-to-chair",
     "benchmark": "median one-way cancer-care travel 30 min (JCO OP "
                  "2022); >50 mi cuts chemo receipt (OR 0.87→0.36, "
                  "JCO 2015); 80% of patients would switch providers "
                  "on convenience alone (NRC Health)",
     "why": "chronic therapy = 6–26 visits/yr; the drive compounds "
            "into adherence and site choice",
     "weight": 0.20},
    {"driver": "Wait + chair time",
     "metric": "on-time start %, appointment-to-first-drug minutes",
     "benchmark": "hospital infusion centers average 58-min waits "
                  "(range 25–102; NCCN 2019); cutting 58→40 min "
                  "raised wait-satisfaction 76→85 (JCO OP 2021); "
                  "<15-min waits ≈3.8× satisfaction odds (Press "
                  "Ganey-based)",
     "why": "infusion is hours long already — variance is the "
            "experience killer, and the hospital baseline is bad",
     "weight": 0.15},
    {"driver": "Environment (private suite vs bay)",
     "metric": "private rooms, recliners, wifi/TV, guest seating",
     "benchmark": "preferences split (29% private / 28% semi / 27% "
                  "open) BUT women + longer infusions prefer private "
                  "(HERD 2018) — i.e., exactly the biologic/IVIG book",
     "why": "the visible differentiator vs a hospital bay — drives "
            "word-of-mouth and Google ratings",
     "weight": 0.12},
    {"driver": "Scheduling flexibility",
     "metric": "evening/weekend slots, self-rescheduling",
     "benchmark": "37% of working-age chemo patients want evening/"
                  "weekend slots; UAB added Saturdays off a 44% "
                  "volume rise; no industry benchmark exists — "
                  "proprietary-data opportunity",
     "why": "working-age biologic patients (IBD/RA/MS) can't burn a "
            "workday every month",
     "weight": 0.12},
    {"driver": "Nurse continuity & clinical trust",
     "metric": "same-nurse rate, first-stick success, reaction handling",
     "benchmark": "nurse-navigator contact measurably lifts Press "
                  "Ganey percentiles (CJON 2019); Uptiv runs 1:3 "
                  "nurse-to-patient as a selling point",
     "why": "ports, hard sticks, infusion reactions — competence is "
            "remembered and referred",
     "weight": 0.10},
    {"driver": "Financial transparency",
     "metric": "pre-visit out-of-pocket quote, copay-assist enrollment",
     "benchmark": "60% of patients hit unexpected cost; 1 in 4 then "
                  "abandon therapy (CoverMyMeds)",
     "why": "surprise five-figure bills end relationships (and end "
            "collections)",
     "weight": 0.06},
]

#: Operator-model experience scorecard (1–5 per driver) — a documented
#: analyst framework anchored to DISCLOSED metrics (all self-reported,
#: unaudited: IVX NPS 90→97; Option Care NPS mid-70s / satisfaction
#: low-90s on earnings calls; NHIF home-infusion 98% highly satisfied,
#: 95% prefer home; hospital NPS benchmarks ~58) — not a patient
#: survey. Edit to the engagement's own survey data.
EXPERIENCE_MODELS: List[Dict[str, Any]] = [
    {"model": "Hospital HOPD infusion suite",
     "example": "health-system outpatient",
     "scores": {"Time to first infusion": 2, "Drive time / location": 2,
                "Wait + chair time": 2,
                "Environment (private suite vs bay)": 2,
                "Scheduling flexibility": 2,
                "Nurse continuity & clinical trust": 4,
                "Financial transparency": 1},
     "nps_anchor": "hospital-sector NPS benchmarks ≈58; 58-min mean "
                   "waits (NCCN); facility-fee billing"},
    {"model": "National home infusion",
     "example": "Option Care / Coram",
     "scores": {"Time to first infusion": 3, "Drive time / location": 5,
                "Wait + chair time": 4,
                "Environment (private suite vs bay)": 4,
                "Scheduling flexibility": 3,
                "Nurse continuity & clinical trust": 3,
                "Financial transparency": 3},
     "nps_anchor": "Option Care discloses NPS mid-70s, satisfaction "
                   "low-90s; NHIF: 95% of home patients prefer home"},
    {"model": "AIC chain (private-suite)",
     "example": "IVX Health",
     "scores": {"Time to first infusion": 4, "Drive time / location": 4,
                "Wait + chair time": 5,
                "Environment (private suite vs bay)": 5,
                "Scheduling flexibility": 5,
                "Nurse continuity & clinical trust": 4,
                "Financial transparency": 4},
     "nps_anchor": "IVX discloses NPS 90 (2020) → 97 (2021+), "
                   "self-reported — the consumer bar"},
    {"model": "Regional independent (white-glove)",
     "example": "HealthQuest",
     "scores": {"Time to first infusion": 5, "Drive time / location": 4,
                "Wait + chair time": 4,
                "Environment (private suite vs bay)": 4,
                "Scheduling flexibility": 4,
                "Nurse continuity & clinical trust": 5,
                "Financial transparency": 4},
     "nps_anchor": "same-day starts 'often' + >4.5 Google rating; "
                   "speed-to-start + physician service is the moat"},
]


def patient_experience_analysis() -> Dict[str, Any]:
    """Weighted experience scores per operator model — the demand-side
    read. Pure recompute of the framework scores × driver weights."""
    out = []
    for m in EXPERIENCE_MODELS:
        total = sum(m["scores"][d["driver"]] * d["weight"]
                    for d in EXPERIENCE_DRIVERS)
        out.append({**m, "weighted_score": round(total, 2),
                    "score_pct": round(total / 5 * 100)})
    out.sort(key=lambda m: -m["weighted_score"])
    for i, m in enumerate(out, 1):
        m["rank"] = i
    return {
        "drivers": EXPERIENCE_DRIVERS,
        "models": out,
        "note": (
            "Driver benchmarks are published evidence (NCCN, JCO/JCO "
            "OP, Arthritis Care & Research, HERD, NHIF, AMA, NRC "
            "Health — sources on the page); the 1–5 scores × weights "
            "are a documented analyst framework, and every operator "
            "NPS is self-reported and unaudited. The structural point "
            "survives any reasonable weighting: purpose-built AIC + "
            "fast-start regional models out-experience the hospital "
            "bay, and experience converts to referrals in a market "
            "where the prescriber chooses the site."),
        "read": (
            "Patient experience is not soft — in TX infusion it is "
            "the mechanism that captures the HOPD-steered volume: the "
            "payer steers on price, but the PATIENT and the "
            "PRESCRIBER pick which non-hospital site gets the steer. "
            "The two highest-weight drivers — time-to-first-infusion "
            "(industry mean 14.6 days; best operators same-week) and "
            "drive time (80% would switch on convenience) — are both "
            "operational choices: benefit-investigation staffing and "
            "site placement. They are buyable and buildable, which is "
            "the point of the platform thesis."),
    }


# ════════════════════════════════════════════════════════════════════
# Assembly
# ════════════════════════════════════════════════════════════════════

def build_texas_infusion_continued_analysis(
    fetch_live: bool = False,
) -> Dict[str, Any]:
    """Assemble the part-2 (continued) Texas infusion analysis.

    Light by design: re-runs the verified part-1 sizing chain for the
    patient base, then layers the per-claim / per-payer / per-place
    grain from the labeled constant tables. ``fetch_live`` threads the
    live CMS ASP pull into the drug table where egress permits."""
    from ..data.county_demographics import demographics_state
    demo = demographics_state("TX") or {}
    tx_pop = int(demo.get("population") or 30_029_572)
    model = texas_infusion_model(tx_pop)
    sizing = compute(model)
    tx_patients = int(model.chain[0].value)

    drug = drug_mix_economics()
    if fetch_live:
        from ..data.cms_asp_pricing import fetch_asp_pricing
        live = fetch_asp_pricing([d["hcpcs"] for d in DRUG_DOSE_ECONOMICS])
        for d in drug["drugs"]:
            if d["hcpcs"] in live:
                d["asp_per_unit_live"] = live[d["hcpcs"]]
                d["live"] = True

    out = {
        "state": "TX",
        "tx_population": tx_pop,
        "tx_patients": tx_patients,
        "sizing": sizing,
        "channel_sizing": channel_sizing(tx_patients),
        "pfs_admin_codes": PFS_ADMIN_CODES,
        "pfs_source_note": PFS_SOURCE_NOTE,
        "visit_stacks": visit_stack_economics(),
        "hit_g_codes": HIT_G_CODES,
        "hit_note": HIT_SOURCE_NOTE,
        "home_perdiem_codes": HOME_PERDIEM_CODES,
        "home_perdiem_note": HOME_PERDIEM_NOTE,
        "cross_site": cross_site_visit_comparison(),
        "state_reimbursement": state_reimbursement_index(),
        "tx_localities": texas_locality_rates(),
        "tx_locality_note": TX_LOCALITY_NOTE,
        "drug_mix": drug,
        "overall_reimbursement": overall_reimbursement_rate(),
        "metro_payers": metro_payer_analysis(),
        "network": network_access_by_metro(),
        "proximity": county_proximity_model(),
        "healthquest": healthquest_proximity(),
        "experience": patient_experience_analysis(),
        "sources": [
            "CMS National PFS Relative Value files (RVU25A/RVU25D + "
            "RVU26A) — CY2025/CY2026 non-facility amounts and "
            "conversion factors for the drug-administration CPTs",
            "CMS CY2025 GPCI file (Addendum E, vendored verbatim) — "
            "Texas locality GPCIs + the computed state GAF table",
            "CMS CY2025 OPPS pricer / Addendum A + IOCE v25.1 — "
            "drug-administration APC rates 5691–5694 and CPT→APC "
            "mappings; CY2026 off-campus site-neutral expansion",
            "CMS CY2025/CY2026 national Home Infusion Therapy rates "
            "files (Transmittal R13512CP) — G0068–G0070 / G0088–G0090",
            "Montana Medicaid Home Infusion Services fee schedule "
            "(eff. 2025-07-01) — the only public S-code per-diem "
            "prices; NHIA model-contract structure",
            "CMS quarterly ASP pricing files (Q1/Q2 2026 via state-"
            "Medicaid verbatim mirrors; live pull where egress "
            "permits) — per-unit drug payment limits",
            "Commercial-vs-Medicare benchmarks: HCCI (122%), CBO "
            "(129%), KFF (143%), MedPAC PPO (134–140%), Milliman "
            "(148%); RAND 5.1 (hospital drugs 281% of ASP vs 106% "
            "Medicare); JCO 2022 (96413 hospital median $536); "
            "Health Affairs 2021 (HOPD ≈2× office)",
            "AMA Competition in Health Insurance, 2025 edition (2024 "
            "data) via TMA — HCSC #1 in all 26 TX metros (37–74%); "
            "Aetna ~19% TX #2; Cigna 23% in DFW",
            "KFF Employer Health Benefits Survey 2025 — PPO 46 / "
            "HDHP 33 / HMO 12 / POS 9; 67% self-funded",
            "CMS/KFF MA enrollment — TX 54% MA (Sept 2024); county "
            "penetration: Harris 61.3 / Dallas 54.8 / Tarrant 55.8 / "
            "Bexar 58.5 / Travis 47.5 (county aggregators of the CMS "
            "penetration file)",
            "Census Vintage-2024 county estimates + 2020 "
            "cb_2020_us_county land areas — population density; ACS "
            "(vendored) county population",
            "hqrx.com (indexed) + NPI registry + directories — "
            "HealthQuest sites, services, accreditations, payers; "
            "operator location pages — Houston competitor sites",
            "Experience evidence: NCCN JOP 2019 (58-min waits); JCO "
            "OP 2021/2022; Arthritis Care & Research 2020 (PA "
            "delays); JNMA 2024; NHIF 2024 (14.6-day onboarding; "
            "satisfaction); HERD 2018 (suite preference); AMA 2024 "
            "PA survey; NRC Health (80% switch on convenience); "
            "operator NPS disclosures (self-reported)",
        ],
        "basis_note": (
            "Published CMS rate tables (verified against the official "
            "files), the vendored CMS GPCI file, and labeled industry "
            "anchors on top of the part-1 demand model — researched "
            "June 2026; rate files refresh quarterly/annually. "
            "Directional items (network status, insurer shares inside "
            "the AMA member-gated tables, county MA aggregators) are "
            "flagged in place — replace with license-grade pulls "
            "before IC."),
    }
    return out
