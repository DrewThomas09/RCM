"""Reference Pricing / Payer Contract Analyzer.

Benchmarks current payer rates vs market comparables:
- Medicare rate (fee schedule baseline)
- Commercial average (market comps)
- Top-quartile commercial (negotiation target)
- Rate gap analysis → renegotiation uplift
- Contract renewal calendar
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# CPT fee schedule baselines (indexed to Medicare = 1.00)
# ---------------------------------------------------------------------------

_CPT_BENCHMARKS = {
    "99213": {"name": "Office Visit Est. Pt Level 3", "medicare": 89.0,
              "comm_median_index": 1.85, "comm_p75_index": 2.10, "comm_p25_index": 1.55},
    "99214": {"name": "Office Visit Est. Pt Level 4", "medicare": 130.5,
              "comm_median_index": 1.82, "comm_p75_index": 2.05, "comm_p25_index": 1.52},
    "99203": {"name": "Office Visit New Pt Level 3", "medicare": 115.0,
              "comm_median_index": 1.78, "comm_p75_index": 2.02, "comm_p25_index": 1.48},
    "99204": {"name": "Office Visit New Pt Level 4", "medicare": 175.0,
              "comm_median_index": 1.75, "comm_p75_index": 1.98, "comm_p25_index": 1.45},
    "45378": {"name": "Colonoscopy Diagnostic", "medicare": 420.0,
              "comm_median_index": 2.10, "comm_p75_index": 2.55, "comm_p25_index": 1.70},
    "45385": {"name": "Colonoscopy w/ Polypectomy", "medicare": 520.0,
              "comm_median_index": 2.15, "comm_p75_index": 2.60, "comm_p25_index": 1.72},
    "43239": {"name": "EGD w/ Biopsy", "medicare": 485.0,
              "comm_median_index": 2.00, "comm_p75_index": 2.45, "comm_p25_index": 1.68},
    "11102": {"name": "Skin Biopsy (single)", "medicare": 85.0,
              "comm_median_index": 1.92, "comm_p75_index": 2.22, "comm_p25_index": 1.60},
    "11104": {"name": "Punch Biopsy (single)", "medicare": 98.0,
              "comm_median_index": 1.88, "comm_p75_index": 2.18, "comm_p25_index": 1.58},
    "88305": {"name": "Path Exam Tissue", "medicare": 68.0,
              "comm_median_index": 2.20, "comm_p75_index": 2.60, "comm_p25_index": 1.80},
    "66984": {"name": "Cataract Surgery", "medicare": 1580.0,
              "comm_median_index": 1.55, "comm_p75_index": 1.78, "comm_p25_index": 1.32},
    "27447": {"name": "Total Knee Arthroplasty", "medicare": 1450.0,
              "comm_median_index": 1.68, "comm_p75_index": 1.95, "comm_p25_index": 1.42},
    "27130": {"name": "Total Hip Arthroplasty", "medicare": 1530.0,
              "comm_median_index": 1.65, "comm_p75_index": 1.90, "comm_p25_index": 1.40},
    "99285": {"name": "ER Visit Level 5", "medicare": 295.0,
              "comm_median_index": 2.45, "comm_p75_index": 2.95, "comm_p25_index": 1.95},
    "90837": {"name": "Psychotherapy 60 min", "medicare": 160.0,
              "comm_median_index": 1.42, "comm_p75_index": 1.68, "comm_p25_index": 1.18},
    "97110": {"name": "Therapeutic Exercises 15min", "medicare": 32.0,
              "comm_median_index": 1.55, "comm_p75_index": 1.85, "comm_p25_index": 1.28},
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CPTRow:
    cpt_code: str
    description: str
    volume_annual: int
    medicare_rate: float
    current_avg_rate: float       # weighted across payers
    comm_median: float
    comm_p75: float
    current_index_to_mcr: float
    gap_to_median_pct: float
    gap_to_p75_pct: float
    uplift_to_median_mm: float
    uplift_to_p75_mm: float


@dataclass
class PayerContract:
    payer: str
    contract_type: str            # "Evergreen", "3-year", "1-year", "Letter Agreement"
    renewal_date: str
    annual_volume_mm: float
    blended_index_to_mcr: float
    status: str                   # "current", "expiring", "open"
    leverage: str                 # "high", "medium", "low"


@dataclass
class UpliftScenario:
    scenario: str
    target_index_to_mcr: float
    annual_revenue_uplift_mm: float
    ebitda_uplift_mm: float
    ev_impact_mm: float
    execution_complexity: str
    probability: float


@dataclass
class RefPricingResult:
    sector: str
    cpt_rows: List[CPTRow]
    payer_contracts: List[PayerContract]
    uplift_scenarios: List[UpliftScenario]
    current_weighted_index: float
    market_median_index: float
    market_p75_index: float
    total_uplift_to_median_mm: float
    total_uplift_to_p75_mm: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 66):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    try:
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS, EXTENDED_SEED_DEALS
        deals = _SEED_DEALS + EXTENDED_SEED_DEALS + deals
    except Exception:
        pass
    return deals


def _sector_cpts(sector: str) -> List[str]:
    """Return relevant CPT codes for sector."""
    mapping = {
        "Physician Services": ["99213", "99214", "99203", "99204"],
        "Primary Care":       ["99213", "99214", "99203", "99204"],
        "Dermatology":        ["99213", "99214", "11102", "11104", "88305"],
        "Gastroenterology":   ["99213", "99214", "45378", "45385", "43239"],
        "Ophthalmology":      ["99213", "99214", "66984"],
        "Orthopedics":        ["99213", "99214", "27447", "27130"],
        "Urgent Care":        ["99213", "99214", "99203", "99285"],
        "Behavioral Health":  ["90837"],
        "ABA Therapy":        ["97110"],
    }
    return mapping.get(sector, ["99213", "99214", "99203", "99204"])


def _build_cpt_rows(sector: str, revenue_mm: float, current_index: float) -> List[CPTRow]:
    codes = _sector_cpts(sector)
    rows = []
    total_rev_target = revenue_mm * 1_000_000    # in dollars

    # Estimate volume per CPT to hit target revenue
    remaining_rev = total_rev_target
    for i, code in enumerate(codes):
        b = _CPT_BENCHMARKS[code]
        weight = 1.0 / len(codes) if i < len(codes) - 1 else 1.0   # even split
        cpt_rev = total_rev_target / len(codes)
        current_rate = b["medicare"] * current_index
        volume = int(cpt_rev / current_rate) if current_rate else 0

        comm_median_rate = b["medicare"] * b["comm_median_index"]
        comm_p75_rate = b["medicare"] * b["comm_p75_index"]

        gap_median = (comm_median_rate - current_rate) / current_rate if current_rate else 0
        gap_p75 = (comm_p75_rate - current_rate) / current_rate if current_rate else 0

        uplift_median = volume * (comm_median_rate - current_rate) / 1_000_000
        uplift_p75 = volume * (comm_p75_rate - current_rate) / 1_000_000

        rows.append(CPTRow(
            cpt_code=code,
            description=b["name"],
            volume_annual=volume,
            medicare_rate=b["medicare"],
            current_avg_rate=round(current_rate, 2),
            comm_median=round(comm_median_rate, 2),
            comm_p75=round(comm_p75_rate, 2),
            current_index_to_mcr=round(current_index, 3),
            gap_to_median_pct=round(gap_median, 4),
            gap_to_p75_pct=round(gap_p75, 4),
            uplift_to_median_mm=round(uplift_median, 2),
            uplift_to_p75_mm=round(uplift_p75, 2),
        ))
    return rows


def _build_payer_contracts(revenue_mm: float, current_index: float) -> List[PayerContract]:
    payers = [
        ("UnitedHealthcare Commercial", "3-year", "2026-12-31", revenue_mm * 0.22, current_index * 1.05, "current", "high"),
        ("Anthem / Elevance", "3-year", "2026-08-15", revenue_mm * 0.18, current_index * 0.98, "expiring", "high"),
        ("Aetna / CVS", "Evergreen", "rolling 90-day", revenue_mm * 0.14, current_index * 1.02, "current", "medium"),
        ("Cigna", "3-year", "2027-03-31", revenue_mm * 0.10, current_index * 1.08, "current", "medium"),
        ("BCBS Local", "3-year", "2025-12-31", revenue_mm * 0.12, current_index * 0.95, "expiring", "high"),
        ("Humana", "1-year", "2026-06-30", revenue_mm * 0.08, current_index * 0.92, "open", "medium"),
        ("Medicare Advantage (UHC)", "3-year", "2026-12-31", revenue_mm * 0.08, 0.75, "current", "low"),
        ("Medicaid FFS", "Evergreen", "statutory", revenue_mm * 0.05, 0.62, "current", "low"),
        ("Workers Comp (state fee schedule)", "Letter Agreement", "annual", revenue_mm * 0.03, 1.20, "current", "low"),
    ]
    return [PayerContract(
        payer=p, contract_type=ct, renewal_date=rd, annual_volume_mm=round(vol, 2),
        blended_index_to_mcr=round(idx, 3), status=st, leverage=lev,
    ) for p, ct, rd, vol, idx, st, lev in payers]


def _build_scenarios(
    cpt_rows: List[CPTRow], revenue_mm: float, ebitda_margin: float,
    exit_multiple: float, current_index: float,
) -> List[UpliftScenario]:
    total_median_uplift = sum(c.uplift_to_median_mm for c in cpt_rows)
    total_p75_uplift = sum(c.uplift_to_p75_mm for c in cpt_rows)

    scenarios = [
        ("Close gap to market median", 1.80, total_median_uplift * 0.60, "medium", 0.60),
        ("Close gap to P75 (aggressive)", 2.10, total_p75_uplift * 0.35, "high", 0.28),
        ("Close gap to P75 (selected 2 payers)", 1.95, total_p75_uplift * 0.22, "medium", 0.48),
        ("Hold-flat (negotiate CPI only)", current_index * 1.03, revenue_mm * 0.03, "low", 0.88),
        ("Downside: Payer cuts 3% on renewal", current_index * 0.97, -revenue_mm * 0.03, "low", 0.25),
    ]
    rows = []
    for label, target_idx, rev_uplift, complex_, prob in scenarios:
        ebitda_up = rev_uplift * (ebitda_margin + 0.04)    # Rate changes fall through almost fully
        ev_impact = ebitda_up * exit_multiple
        rows.append(UpliftScenario(
            scenario=label,
            target_index_to_mcr=round(target_idx, 3),
            annual_revenue_uplift_mm=round(rev_uplift, 2),
            ebitda_uplift_mm=round(ebitda_up, 2),
            ev_impact_mm=round(ev_impact, 1),
            execution_complexity=complex_,
            probability=round(prob, 3),
        ))
    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_ref_pricing(
    sector: str = "Physician Services",
    revenue_mm: float = 80.0,
    current_index_to_mcr: float = 1.55,    # current rate / Medicare
    ebitda_margin: float = 0.18,
    exit_multiple: float = 11.0,
) -> RefPricingResult:
    corpus = _load_corpus()

    cpt_rows = _build_cpt_rows(sector, revenue_mm, current_index_to_mcr)
    contracts = _build_payer_contracts(revenue_mm, current_index_to_mcr)
    scenarios = _build_scenarios(cpt_rows, revenue_mm, ebitda_margin, exit_multiple, current_index_to_mcr)

    total_median = sum(c.uplift_to_median_mm for c in cpt_rows)
    total_p75 = sum(c.uplift_to_p75_mm for c in cpt_rows)

    # Market average indices
    market_median = sum(_CPT_BENCHMARKS[c.cpt_code]["comm_median_index"] for c in cpt_rows) / len(cpt_rows) if cpt_rows else 1.8
    market_p75 = sum(_CPT_BENCHMARKS[c.cpt_code]["comm_p75_index"] for c in cpt_rows) / len(cpt_rows) if cpt_rows else 2.1

    return RefPricingResult(
        sector=sector,
        cpt_rows=cpt_rows,
        payer_contracts=contracts,
        uplift_scenarios=scenarios,
        current_weighted_index=round(current_index_to_mcr, 3),
        market_median_index=round(market_median, 3),
        market_p75_index=round(market_p75, 3),
        total_uplift_to_median_mm=round(total_median, 2),
        total_uplift_to_p75_mm=round(total_p75, 2),
        corpus_deal_count=len(corpus),
    )
