"""Tax Structure Analyzer — F-reorg, 338(h)(10), step-up, PTE, carried interest tax.

Models deal tax economics:
- Stock vs. Asset deal: 338(h)(10) election evaluation
- F-reorganization for MSO/PC structures
- Goodwill step-up value (15-year amortization)
- Rollover equity taxation (partial deferral)
- PTE / SALT cap workarounds
- Carried interest / K-1 tax flow to LPs
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Tax constants
# ---------------------------------------------------------------------------

_FEDERAL_C_CORP = 0.21
_FEDERAL_INDIVIDUAL_MAX = 0.37
_FEDERAL_LTCG_MAX = 0.20
_FEDERAL_QBI_DEDUCTION = 0.20
_NIIT = 0.038
_AMORT_PERIOD_YEARS = 15


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class StructureOption:
    structure: str
    buyer_preferred: str
    seller_preferred: str
    goodwill_stepup_mm: float
    annual_tax_shield_mm: float
    pv_tax_shield_mm: float
    seller_tax_cost_mm: float
    net_benefit_mm: float
    complexity_score: int     # 1-10
    notes: str


@dataclass
class RolloverTax:
    rollover_value_mm: float
    deferred_gain_mm: float
    recognized_gain_mm: float
    immediate_tax_mm: float
    effective_tax_rate: float


@dataclass
class PTEBenefit:
    state: str
    pte_active: bool
    state_rate: float
    entity_deduction_mm: float
    federal_savings_mm: float
    net_benefit_mm: float


@dataclass
class TaxFlowRow:
    year: int
    ebitda_mm: float
    tax_shield_from_stepup_mm: float
    taxable_income_mm: float
    federal_tax_mm: float
    state_tax_mm: float
    after_tax_cash_mm: float


@dataclass
class TaxStructureResult:
    ev_mm: float
    ebitda_mm: float
    purchase_allocation: Dict[str, float]
    structure_options: List[StructureOption]
    recommended_structure: str
    rollover_tax: RolloverTax
    pte_benefits: List[PTEBenefit]
    tax_flow: List[TaxFlowRow]
    total_tax_optimization_mm: float
    seller_net_proceeds_mm: float
    effective_tax_rate: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 63):
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


def _pv(amount: float, rate: float, year: int) -> float:
    return amount / ((1 + rate) ** year)


def _purchase_allocation(ev_mm: float, ebitda_mm: float) -> Dict[str, float]:
    """Approximate purchase price allocation typical for healthcare services."""
    return {
        "tangible_assets": round(ev_mm * 0.08, 2),     # PP&E, receivables net
        "workforce_intangible": round(ev_mm * 0.05, 2),
        "customer_relationships": round(ev_mm * 0.12, 2),
        "trade_name": round(ev_mm * 0.03, 2),
        "non_compete": round(ev_mm * 0.02, 2),
        "goodwill": round(ev_mm * 0.70, 2),
    }


def _build_structures(ev_mm: float, ebitda_mm: float, hold_years: int) -> List[StructureOption]:
    options = []
    discount_rate = 0.10

    # 1. Stock deal (default — no step-up)
    options.append(StructureOption(
        structure="Stock Deal (no 338)",
        buyer_preferred="no",
        seller_preferred="yes",
        goodwill_stepup_mm=0,
        annual_tax_shield_mm=0,
        pv_tax_shield_mm=0,
        seller_tax_cost_mm=round(ev_mm * 0.20, 2),     # LTCG only
        net_benefit_mm=0,
        complexity_score=3,
        notes="Seller LTCG treatment; no buyer step-up",
    ))

    # 2. Asset deal / 338(h)(10)
    alloc = _purchase_allocation(ev_mm, ebitda_mm)
    stepup = alloc["goodwill"] + alloc["customer_relationships"] + alloc["trade_name"] + alloc["workforce_intangible"]
    annual_shield = stepup / _AMORT_PERIOD_YEARS * _FEDERAL_C_CORP
    pv_shield = sum(_pv(annual_shield, discount_rate, y) for y in range(1, _AMORT_PERIOD_YEARS + 1))
    seller_tax = ev_mm * 0.30     # Ordinary rate on goodwill treats
    options.append(StructureOption(
        structure="Asset Deal / 338(h)(10) Election",
        buyer_preferred="yes",
        seller_preferred="gross-up required",
        goodwill_stepup_mm=round(stepup, 2),
        annual_tax_shield_mm=round(annual_shield, 2),
        pv_tax_shield_mm=round(pv_shield, 2),
        seller_tax_cost_mm=round(seller_tax, 2),
        net_benefit_mm=round(pv_shield - (seller_tax - ev_mm * 0.20), 2),
        complexity_score=6,
        notes="Buyer gets step-up; seller typically requires gross-up for double-tax",
    ))

    # 3. F-reorganization (MSO/PC common)
    options.append(StructureOption(
        structure="F-Reorganization (MSO/PC)",
        buyer_preferred="yes",
        seller_preferred="yes",
        goodwill_stepup_mm=round(stepup * 0.95, 2),
        annual_tax_shield_mm=round(annual_shield * 0.95, 2),
        pv_tax_shield_mm=round(pv_shield * 0.95, 2),
        seller_tax_cost_mm=round(ev_mm * 0.20, 2),
        net_benefit_mm=round(pv_shield * 0.95, 2),
        complexity_score=9,
        notes="Best of both worlds for healthcare PE; requires careful structuring",
    ))

    # 4. Partial Rollover + Asset
    rollover_pct = 0.10
    rollover = ev_mm * rollover_pct
    cash_out = ev_mm - rollover
    cash_stepup = stepup * (1 - rollover_pct)
    shield_roll = cash_stepup / _AMORT_PERIOD_YEARS * _FEDERAL_C_CORP
    pv_shield_roll = sum(_pv(shield_roll, discount_rate, y) for y in range(1, _AMORT_PERIOD_YEARS + 1))
    seller_tax_roll = cash_out * 0.20
    options.append(StructureOption(
        structure="Rollover + Asset Deal",
        buyer_preferred="yes",
        seller_preferred="yes",
        goodwill_stepup_mm=round(cash_stepup, 2),
        annual_tax_shield_mm=round(shield_roll, 2),
        pv_tax_shield_mm=round(pv_shield_roll, 2),
        seller_tax_cost_mm=round(seller_tax_roll, 2),
        net_benefit_mm=round(pv_shield_roll - seller_tax_roll + cash_out * 0.20, 2),
        complexity_score=7,
        notes=f"{rollover_pct * 100:.0f}% rollover defers gain on that portion",
    ))

    return options


def _rollover_tax(equity_mm: float, rollover_pct: float) -> RolloverTax:
    rollover_value = equity_mm * rollover_pct
    cash_portion = equity_mm * (1 - rollover_pct)
    # Deferred gain (on rollover portion)
    deferred = rollover_value * 0.85    # Assume 85% gain (high basis = 15%)
    recognized = cash_portion * 0.85
    immediate_tax = recognized * (_FEDERAL_LTCG_MAX + _NIIT)
    eff_rate = immediate_tax / (cash_portion + rollover_value) if (cash_portion + rollover_value) else 0
    return RolloverTax(
        rollover_value_mm=round(rollover_value, 2),
        deferred_gain_mm=round(deferred, 2),
        recognized_gain_mm=round(recognized, 2),
        immediate_tax_mm=round(immediate_tax, 2),
        effective_tax_rate=round(eff_rate, 4),
    )


def _pte_benefits(ebitda_mm: float) -> List[PTEBenefit]:
    states = [
        ("New York", True, 0.109),
        ("California", True, 0.133),
        ("New Jersey", True, 0.1075),
        ("Illinois", True, 0.0495),
        ("Massachusetts", True, 0.09),
        ("Texas", False, 0.0),
        ("Florida", False, 0.0),
    ]
    rows = []
    for state, active, rate in states:
        entity_ded = ebitda_mm * 0.10 * rate if active else 0    # PTE applies to pass-through income
        fed_savings = entity_ded * _FEDERAL_INDIVIDUAL_MAX if active else 0
        net = fed_savings * 0.92    # minus state PTE tax
        rows.append(PTEBenefit(
            state=state,
            pte_active=active,
            state_rate=round(rate, 4),
            entity_deduction_mm=round(entity_ded, 3),
            federal_savings_mm=round(fed_savings, 3),
            net_benefit_mm=round(net, 3),
        ))
    return rows


def _build_tax_flow(
    ebitda_mm: float, growth_pct: float, hold_years: int,
    annual_shield: float, fed_rate: float, state_rate: float,
) -> List[TaxFlowRow]:
    rows = []
    for yr in range(0, hold_years + 1):
        eb = ebitda_mm * ((1 + growth_pct) ** yr)
        shield = annual_shield if yr >= 1 else 0
        taxable = max(0, eb - shield - eb * 0.02)    # D&A proxy
        fed_tax = taxable * fed_rate
        state_tax = taxable * state_rate
        after_tax = eb - fed_tax - state_tax
        rows.append(TaxFlowRow(
            year=yr,
            ebitda_mm=round(eb, 2),
            tax_shield_from_stepup_mm=round(shield, 2),
            taxable_income_mm=round(taxable, 2),
            federal_tax_mm=round(fed_tax, 2),
            state_tax_mm=round(state_tax, 2),
            after_tax_cash_mm=round(after_tax, 2),
        ))
    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_tax_structure(
    ev_mm: float = 300.0,
    ebitda_mm: float = 25.0,
    hold_years: int = 5,
    revenue_growth_pct: float = 0.05,
    rollover_pct: float = 0.10,
    equity_pct: float = 0.45,
    state: str = "New York",
) -> TaxStructureResult:
    corpus = _load_corpus()

    allocation = _purchase_allocation(ev_mm, ebitda_mm)
    structures = _build_structures(ev_mm, ebitda_mm, hold_years)
    # Recommend best net benefit
    best = max(structures, key=lambda s: s.net_benefit_mm)

    equity_mm = ev_mm * equity_pct
    rollover = _rollover_tax(equity_mm, rollover_pct)
    pte = _pte_benefits(ebitda_mm)

    state_rate = next((p.state_rate for p in pte if p.state == state), 0.06)
    tax_flow = _build_tax_flow(
        ebitda_mm, revenue_growth_pct, hold_years,
        best.annual_tax_shield_mm, _FEDERAL_C_CORP, state_rate,
    )

    total_optim = best.pv_tax_shield_mm + sum(p.net_benefit_mm for p in pte if p.pte_active) + rollover.deferred_gain_mm * 0.20
    seller_net = ev_mm - best.seller_tax_cost_mm
    eff_rate = best.seller_tax_cost_mm / ev_mm if ev_mm else 0

    return TaxStructureResult(
        ev_mm=round(ev_mm, 1),
        ebitda_mm=round(ebitda_mm, 2),
        purchase_allocation=allocation,
        structure_options=structures,
        recommended_structure=best.structure,
        rollover_tax=rollover,
        pte_benefits=pte,
        tax_flow=tax_flow,
        total_tax_optimization_mm=round(total_optim, 2),
        seller_net_proceeds_mm=round(seller_net, 2),
        effective_tax_rate=round(eff_rate, 4),
        corpus_deal_count=len(corpus),
    )
