"""Payer Mix Shift Simulator — models P&L impact of payer re-mix.

Healthcare PE deals face payer mix shifts over hold period from:
- Medicare Advantage penetration
- Commercial-to-Medicaid migration
- State Medicaid expansion
- Self-pay erosion in urgent care / HC Marketplace

Simulates starting mix → target mix across hold, projects revenue/EBITDA impact.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Payer reimbursement benchmarks (relative to commercial = 1.00)
# ---------------------------------------------------------------------------

_PAYER_RATE_INDEX = {
    "commercial": 1.00,
    "medicare_fee_for_service": 0.72,
    "medicare_advantage": 0.68,
    "medicaid": 0.48,
    "medicaid_managed": 0.52,
    "self_pay": 0.38,       # after bad debt
    "workers_comp": 1.15,
    "auto_liability": 1.35,
    "tricare": 0.78,
    "marketplace_exchange": 0.82,
}

_PAYER_COLLECTION_RATE = {
    "commercial": 0.96,
    "medicare_fee_for_service": 0.99,
    "medicare_advantage": 0.94,
    "medicaid": 0.92,
    "medicaid_managed": 0.90,
    "self_pay": 0.28,
    "workers_comp": 0.88,
    "auto_liability": 0.82,
    "tricare": 0.97,
    "marketplace_exchange": 0.91,
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PayerMix:
    payer: str
    pct: float
    rate_index: float
    collection_rate: float
    weighted_yield: float       # pct × rate × collection


@dataclass
class MixShiftScenario:
    label: str
    description: str
    start_commercial_pct: float
    end_commercial_pct: float
    start_medicaid_pct: float
    end_medicaid_pct: float
    start_weighted_yield: float
    end_weighted_yield: float
    yield_change_pct: float
    revenue_impact_mm: float
    ebitda_impact_mm: float
    ev_impact_mm: float


@dataclass
class YearlyProjection:
    year: int
    commercial_pct: float
    medicare_pct: float
    medicaid_pct: float
    self_pay_pct: float
    weighted_yield: float
    revenue_mm: float
    ebitda_mm: float


@dataclass
class PayerShiftResult:
    sector: str
    starting_mix: List[PayerMix]
    target_mix: List[PayerMix]
    scenarios: List[MixShiftScenario]
    yearly_projection: List[YearlyProjection]
    base_revenue_mm: float
    terminal_revenue_mm: float
    total_ebitda_impact_mm: float
    total_ev_impact_mm: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 64):
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


def _build_mix(mix_dict: Dict[str, float]) -> List[PayerMix]:
    rows = []
    for payer, pct in mix_dict.items():
        if pct <= 0:
            continue
        rate = _PAYER_RATE_INDEX.get(payer, 0.7)
        coll = _PAYER_COLLECTION_RATE.get(payer, 0.9)
        yield_ = pct * rate * coll
        rows.append(PayerMix(
            payer=payer.replace("_", " ").title(),
            pct=round(pct, 4),
            rate_index=round(rate, 3),
            collection_rate=round(coll, 3),
            weighted_yield=round(yield_, 4),
        ))
    return rows


def _weighted_yield(mix: Dict[str, float]) -> float:
    return sum(pct * _PAYER_RATE_INDEX.get(p, 0.7) * _PAYER_COLLECTION_RATE.get(p, 0.9)
               for p, pct in mix.items())


def _build_scenarios(
    base_mix: Dict[str, float], revenue_mm: float, ebitda_margin: float,
    exit_multiple: float,
) -> List[MixShiftScenario]:
    base_yield = _weighted_yield(base_mix)

    scenarios_def = [
        # (label, description, mix_delta_dict)
        (
            "Medicare Advantage Penetration",
            "Traditional FFS → MA shift (2% per year × 5 yrs)",
            {"medicare_fee_for_service": -0.10, "medicare_advantage": 0.10},
        ),
        (
            "Commercial Erosion (MA-ACA)",
            "Commercial shifts to Medicare Advantage and Marketplace",
            {"commercial": -0.08, "medicare_advantage": 0.05, "marketplace_exchange": 0.03},
        ),
        (
            "Medicaid Expansion Impact",
            "Self-pay and commercial shift to Medicaid Managed",
            {"self_pay": -0.04, "commercial": -0.03, "medicaid_managed": 0.07},
        ),
        (
            "Self-Pay Growth (HDHP)",
            "High-deductible plans push more to self-pay",
            {"commercial": -0.05, "self_pay": 0.05},
        ),
        (
            "Payer Contract Renegotiation (+5%)",
            "Commercial rate uplift via sponsor-led renegotiation",
            {},    # No mix change, but 5% rate uplift
        ),
    ]

    rows = []
    for label, desc, delta in scenarios_def:
        new_mix = dict(base_mix)
        for p, d in delta.items():
            new_mix[p] = max(0, new_mix.get(p, 0) + d)
        # Renormalize
        total = sum(new_mix.values())
        if total > 0:
            new_mix = {p: v / total for p, v in new_mix.items()}

        new_yield = _weighted_yield(new_mix)

        # Special case for contract renegotiation
        if "Contract" in label:
            new_yield = base_yield * 1.05

        yield_change_pct = (new_yield / base_yield - 1) if base_yield else 0
        revenue_impact = revenue_mm * yield_change_pct
        ebitda_impact = revenue_impact * (ebitda_margin + 0.02)   # High fall-through on rate changes
        ev_impact = ebitda_impact * exit_multiple

        start_comm = base_mix.get("commercial", 0.5)
        end_comm = new_mix.get("commercial", 0.5) if "Contract" not in label else start_comm
        start_med = base_mix.get("medicaid", 0) + base_mix.get("medicaid_managed", 0)
        end_med = new_mix.get("medicaid", 0) + new_mix.get("medicaid_managed", 0) if "Contract" not in label else start_med

        rows.append(MixShiftScenario(
            label=label,
            description=desc,
            start_commercial_pct=round(start_comm, 3),
            end_commercial_pct=round(end_comm, 3),
            start_medicaid_pct=round(start_med, 3),
            end_medicaid_pct=round(end_med, 3),
            start_weighted_yield=round(base_yield, 4),
            end_weighted_yield=round(new_yield, 4),
            yield_change_pct=round(yield_change_pct, 4),
            revenue_impact_mm=round(revenue_impact, 2),
            ebitda_impact_mm=round(ebitda_impact, 2),
            ev_impact_mm=round(ev_impact, 1),
        ))
    return rows


def _build_yearly(
    base_mix: Dict[str, float], target_mix: Dict[str, float],
    hold_years: int, revenue_mm: float, ebitda_margin: float, growth_pct: float,
) -> List[YearlyProjection]:
    rows = []
    for yr in range(0, hold_years + 1):
        progress = yr / hold_years if hold_years else 0
        current_mix = {}
        for p in set(list(base_mix.keys()) + list(target_mix.keys())):
            b = base_mix.get(p, 0)
            t = target_mix.get(p, 0)
            current_mix[p] = b + (t - b) * progress

        cur_yield = _weighted_yield(current_mix)
        base_yield = _weighted_yield(base_mix)
        yield_mult = cur_yield / base_yield if base_yield else 1

        rev = revenue_mm * ((1 + growth_pct) ** yr) * yield_mult
        ebitda = rev * ebitda_margin

        rows.append(YearlyProjection(
            year=yr,
            commercial_pct=round(current_mix.get("commercial", 0), 3),
            medicare_pct=round(current_mix.get("medicare_fee_for_service", 0)
                               + current_mix.get("medicare_advantage", 0), 3),
            medicaid_pct=round(current_mix.get("medicaid", 0)
                               + current_mix.get("medicaid_managed", 0), 3),
            self_pay_pct=round(current_mix.get("self_pay", 0), 3),
            weighted_yield=round(cur_yield, 4),
            revenue_mm=round(rev, 2),
            ebitda_mm=round(ebitda, 2),
        ))
    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_payer_shift(
    sector: str = "Physician Services",
    revenue_mm: float = 80.0,
    ebitda_margin: float = 0.18,
    exit_multiple: float = 11.0,
    hold_years: int = 5,
    growth_pct: float = 0.04,
    starting_mix: Optional[Dict[str, float]] = None,
    target_mix: Optional[Dict[str, float]] = None,
) -> PayerShiftResult:
    corpus = _load_corpus()

    if starting_mix is None:
        starting_mix = {
            "commercial": 0.50,
            "medicare_fee_for_service": 0.18,
            "medicare_advantage": 0.08,
            "medicaid": 0.08,
            "medicaid_managed": 0.08,
            "self_pay": 0.08,
        }
    if target_mix is None:
        target_mix = {
            "commercial": 0.44,
            "medicare_fee_for_service": 0.10,
            "medicare_advantage": 0.18,
            "medicaid": 0.05,
            "medicaid_managed": 0.13,
            "self_pay": 0.10,
        }

    start_mix_rows = _build_mix(starting_mix)
    target_mix_rows = _build_mix(target_mix)
    scenarios = _build_scenarios(starting_mix, revenue_mm, ebitda_margin, exit_multiple)
    yearly = _build_yearly(starting_mix, target_mix, hold_years, revenue_mm, ebitda_margin, growth_pct)

    terminal_rev = yearly[-1].revenue_mm if yearly else revenue_mm
    total_ebitda_impact = sum(y.ebitda_mm for y in yearly) - (revenue_mm * ebitda_margin) * len(yearly)
    total_ev_impact = (yearly[-1].ebitda_mm - revenue_mm * ebitda_margin) * exit_multiple if yearly else 0

    return PayerShiftResult(
        sector=sector,
        starting_mix=start_mix_rows,
        target_mix=target_mix_rows,
        scenarios=scenarios,
        yearly_projection=yearly,
        base_revenue_mm=round(revenue_mm, 1),
        terminal_revenue_mm=round(terminal_rev, 1),
        total_ebitda_impact_mm=round(total_ebitda_impact, 2),
        total_ev_impact_mm=round(total_ev_impact, 1),
        corpus_deal_count=len(corpus),
    )
