"""Earnout & Contingent Consideration Analyzer.

Common structure for physician-led healthcare deals. Models:
- Earnout milestones (EBITDA / revenue / clinical KPIs)
- Probability-weighted payout
- GAAP fair-value accounting
- Seller vs buyer risk allocation
- IRR impact with/without earnout
"""
from __future__ import annotations

import importlib
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class EarnoutMilestone:
    milestone: str
    metric: str
    target: str
    measurement_period: str
    max_payout_mm: float
    probability_of_achievement: float
    expected_payout_mm: float
    risk_allocation: str           # "seller", "buyer", "shared"


@dataclass
class PayoutScenario:
    scenario: str
    probability: float
    base_purchase_price_mm: float
    earnout_payout_mm: float
    total_consideration_mm: float
    implied_multiple_x: float


@dataclass
class FairValueRow:
    period: str
    discount_rate: float
    expected_payout_mm: float
    present_value_mm: float
    accounting_classification: str


@dataclass
class IRRImpact:
    scenario: str
    seller_gross_ev_mm: float
    seller_net_proceeds_mm: float
    buyer_effective_mult: float
    buyer_irr_if_exit_at_12x: float
    seller_pref_vs_buyer: str


@dataclass
class RiskAllocationFactor:
    factor: str
    seller_burden: float
    buyer_burden: float
    guidance: str


@dataclass
class EarnoutResult:
    base_purchase_price_mm: float
    max_earnout_mm: float
    expected_earnout_mm: float
    effective_headline_multiple: float
    effective_paid_multiple: float
    milestones: List[EarnoutMilestone]
    scenarios: List[PayoutScenario]
    fair_value_timeline: List[FairValueRow]
    irr_impacts: List[IRRImpact]
    risk_allocation: List[RiskAllocationFactor]
    total_expected_payout_pv_mm: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 72):
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


def _build_milestones(base_price: float, ebitda_mm: float) -> List[EarnoutMilestone]:
    max_total = base_price * 0.18    # 18% typical earnout

    items = [
        ("Year 1 EBITDA ≥ 110%",
         "EBITDA vs base", f"${ebitda_mm * 1.10:,.1f}M",
         "TTM Year 1", max_total * 0.25, 0.75, "seller"),
        ("Year 2 EBITDA ≥ 125%",
         "EBITDA vs base", f"${ebitda_mm * 1.25:,.1f}M",
         "TTM Year 2", max_total * 0.30, 0.58, "seller"),
        ("Revenue Retention ≥ 92%",
         "Payer revenue retention", "≥ 92%",
         "Year 1", max_total * 0.12, 0.82, "seller"),
        ("Top 3 Provider Retention",
         "Top producers remain employed", "100% of 3",
         "Year 2", max_total * 0.15, 0.65, "seller"),
        ("Bolt-on Integration Complete",
         "IT, EHR, HR integration", "Substantially complete",
         "Year 1.5", max_total * 0.10, 0.72, "shared"),
        ("Clinical Quality Score ≥ 85",
         "Composite quality metric", "≥ 85/100",
         "Year 2", max_total * 0.08, 0.68, "shared"),
    ]
    rows = []
    for m, metric, target, period, max_p, prob, risk in items:
        expected = max_p * prob
        rows.append(EarnoutMilestone(
            milestone=m, metric=metric, target=target,
            measurement_period=period,
            max_payout_mm=round(max_p, 2),
            probability_of_achievement=round(prob, 3),
            expected_payout_mm=round(expected, 2),
            risk_allocation=risk,
        ))
    return rows


def _build_scenarios(base_price: float, milestones: List[EarnoutMilestone]) -> List[PayoutScenario]:
    max_earnout = sum(m.max_payout_mm for m in milestones)
    # Scenarios based on achievement rate
    scenarios_def = [
        ("Full Achievement (100%)", 0.15, 1.0),
        ("Strong Achievement (80%)", 0.25, 0.80),
        ("Expected Achievement (66%)", 0.35, 0.66),
        ("Partial Achievement (40%)", 0.18, 0.40),
        ("Minimal Achievement (15%)", 0.07, 0.15),
    ]
    rows = []
    for label, prob, achievement in scenarios_def:
        payout = max_earnout * achievement
        total = base_price + payout
        implied_mult = total / base_price
        rows.append(PayoutScenario(
            scenario=label,
            probability=round(prob, 3),
            base_purchase_price_mm=round(base_price, 1),
            earnout_payout_mm=round(payout, 1),
            total_consideration_mm=round(total, 1),
            implied_multiple_x=round(implied_mult, 2),
        ))
    return rows


def _build_fair_value(expected_total: float, n_periods: int = 8) -> List[FairValueRow]:
    rows = []
    discount_rate = 0.11
    # Split expected payout across periods
    per_period = expected_total / n_periods

    for q in range(1, n_periods + 1):
        time_yrs = q * 0.5
        pv = per_period / ((1 + discount_rate) ** time_yrs)
        cls = "Level 3 — unobservable inputs" if q <= 3 else "Level 3 — mark to model"
        rows.append(FairValueRow(
            period=f"Year {q / 2:.1f}",
            discount_rate=round(discount_rate, 3),
            expected_payout_mm=round(per_period, 2),
            present_value_mm=round(pv, 2),
            accounting_classification=cls,
        ))
    return rows


def _build_irr_impact(base_price: float, max_earnout: float) -> List[IRRImpact]:
    rows = []

    # Zero earnout
    rows.append(IRRImpact(
        scenario="Zero earnout achieved",
        seller_gross_ev_mm=round(base_price, 1),
        seller_net_proceeds_mm=round(base_price * 0.80, 1),    # after tax
        buyer_effective_mult=round(base_price / (base_price / 12.0), 2),   # 12.0x
        buyer_irr_if_exit_at_12x=0.28,
        seller_pref_vs_buyer="Buyer preferred (better IRR)",
    ))

    # 50% earnout
    half_payout = max_earnout * 0.50
    total_half = base_price + half_payout
    rows.append(IRRImpact(
        scenario="50% earnout achieved",
        seller_gross_ev_mm=round(total_half, 1),
        seller_net_proceeds_mm=round(total_half * 0.80, 1),
        buyer_effective_mult=round(total_half / (base_price / 12.0), 2),
        buyer_irr_if_exit_at_12x=round((12 * (base_price / 12) / total_half) ** (1 / 5) - 1, 3),
        seller_pref_vs_buyer="Neutral",
    ))

    # Full earnout
    total_full = base_price + max_earnout
    rows.append(IRRImpact(
        scenario="Full earnout achieved",
        seller_gross_ev_mm=round(total_full, 1),
        seller_net_proceeds_mm=round(total_full * 0.80, 1),
        buyer_effective_mult=round(total_full / (base_price / 12.0), 2),
        buyer_irr_if_exit_at_12x=round((12 * (base_price / 12) / total_full) ** (1 / 5) - 1, 3),
        seller_pref_vs_buyer="Seller preferred (full payout)",
    ))

    return rows


def _build_risk_allocation() -> List[RiskAllocationFactor]:
    return [
        RiskAllocationFactor(
            factor="EBITDA Target Achievement",
            seller_burden=0.85, buyer_burden=0.15,
            guidance="Seller retains most execution risk",
        ),
        RiskAllocationFactor(
            factor="Provider Retention",
            seller_burden=0.70, buyer_burden=0.30,
            guidance="Joint responsibility — buyer controls comp/culture",
        ),
        RiskAllocationFactor(
            factor="Payer Contract Retention",
            seller_burden=0.60, buyer_burden=0.40,
            guidance="Buyer contracts post-close complicate attribution",
        ),
        RiskAllocationFactor(
            factor="Macroeconomic Downside",
            seller_burden=0.45, buyer_burden=0.55,
            guidance="Contract may include MAC (material adverse change) carveout",
        ),
        RiskAllocationFactor(
            factor="Regulatory / Reimbursement Changes",
            seller_burden=0.35, buyer_burden=0.65,
            guidance="Typically buyer absorbs policy risk",
        ),
        RiskAllocationFactor(
            factor="Integration Execution",
            seller_burden=0.30, buyer_burden=0.70,
            guidance="Buyer-led process; seller advisory",
        ),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_earnout(
    base_purchase_price_mm: float = 250.0,
    current_ebitda_mm: float = 20.0,
) -> EarnoutResult:
    corpus = _load_corpus()

    milestones = _build_milestones(base_purchase_price_mm, current_ebitda_mm)
    scenarios = _build_scenarios(base_purchase_price_mm, milestones)
    max_earnout = sum(m.max_payout_mm for m in milestones)
    expected_earnout = sum(m.expected_payout_mm for m in milestones)

    fair_value = _build_fair_value(expected_earnout)
    irr_impact = _build_irr_impact(base_purchase_price_mm, max_earnout)
    risk = _build_risk_allocation()

    total_pv = sum(fv.present_value_mm for fv in fair_value)

    # Effective multiples (assuming 12x entry on base)
    base_ebitda = base_purchase_price_mm / 12.0
    headline_mult = (base_purchase_price_mm + max_earnout) / base_ebitda
    paid_mult = (base_purchase_price_mm + expected_earnout) / base_ebitda

    return EarnoutResult(
        base_purchase_price_mm=round(base_purchase_price_mm, 1),
        max_earnout_mm=round(max_earnout, 2),
        expected_earnout_mm=round(expected_earnout, 2),
        effective_headline_multiple=round(headline_mult, 2),
        effective_paid_multiple=round(paid_mult, 2),
        milestones=milestones,
        scenarios=scenarios,
        fair_value_timeline=fair_value,
        irr_impacts=irr_impact,
        risk_allocation=risk,
        total_expected_payout_pv_mm=round(total_pv, 2),
        corpus_deal_count=len(corpus),
    )
