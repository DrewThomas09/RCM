"""Debt Covenant Headroom Monitor.

Tracks covenant compliance for PE portfolio companies with credit-facility
debt. Real-time view of maintenance covenant cushion, springing triggers,
and cure-right availability.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class CovenantMetric:
    name: str
    actual: float
    limit: float
    direction: str   # "max" or "min"
    headroom_pct: float
    breach_risk: str


@dataclass
class FacilityTranche:
    tranche: str
    balance_mm: float
    rate_type: str
    spread_bps: int
    all_in_rate_pct: float
    maturity_year: int
    covenant_type: str


@dataclass
class ScenarioStress:
    scenario: str
    ebitda_delta_pct: float
    projected_ebitda_mm: float
    projected_leverage: float
    covenant_status: str
    headroom_pct: float


@dataclass
class CureRight:
    covenant: str
    cure_equity_needed_mm: float
    cure_mechanism: str
    time_to_cure_days: int
    penalty_interest_bps: int


@dataclass
class AmortizationSchedule:
    year: int
    opening_balance_mm: float
    mandatory_amort_mm: float
    excess_cash_sweep_mm: float
    voluntary_prepay_mm: float
    closing_balance_mm: float
    interest_expense_mm: float


@dataclass
class CovenantResult:
    platform_ebitda_ttm_mm: float
    total_debt_mm: float
    total_leverage: float
    blended_rate_pct: float
    next_test_date: str
    overall_status: str
    covenants: List[CovenantMetric]
    tranches: List[FacilityTranche]
    stress_scenarios: List[ScenarioStress]
    cure_rights: List[CureRight]
    amort_schedule: List[AmortizationSchedule]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 92):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    try:
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS
        deals = _SEED_DEALS + deals
    except Exception:
        pass
    return deals


def _build_covenants(ebitda: float, debt: float) -> List[CovenantMetric]:
    leverage = debt / ebitda if ebitda else 0
    int_coverage = ebitda / (debt * 0.085) if debt else 0
    fixed_coverage = ebitda / (debt * 0.085 + ebitda * 0.04) if ebitda else 0
    return [
        CovenantMetric("Total Leverage (Debt/EBITDA)", round(leverage, 2), 6.25, "max",
                       round((6.25 - leverage) / 6.25, 4) if leverage < 6.25 else round((leverage - 6.25) / 6.25, 4),
                       "low" if leverage < 5.0 else ("medium" if leverage < 5.75 else "high")),
        CovenantMetric("First-Lien Leverage", round(leverage * 0.70, 2), 4.5, "max",
                       round((4.5 - leverage * 0.70) / 4.5, 4), "low"),
        CovenantMetric("Net Leverage (Debt - Cash)/EBITDA", round(leverage - 0.3, 2), 6.0, "max",
                       round((6.0 - (leverage - 0.3)) / 6.0, 4), "low"),
        CovenantMetric("Interest Coverage (EBITDA/Interest)", round(int_coverage, 2), 2.25, "min",
                       round((int_coverage - 2.25) / 2.25, 4), "low" if int_coverage > 3.0 else "medium"),
        CovenantMetric("Fixed Charge Coverage", round(fixed_coverage, 2), 1.25, "min",
                       round((fixed_coverage - 1.25) / 1.25, 4), "low" if fixed_coverage > 1.5 else "medium"),
        CovenantMetric("Min Liquidity ($M)", round(ebitda * 0.18, 2), ebitda * 0.10, "min",
                       0.80, "low"),
        CovenantMetric("Max Capex ($M)", round(ebitda * 0.12, 2), ebitda * 0.20, "max",
                       round((ebitda * 0.20 - ebitda * 0.12) / (ebitda * 0.20), 4) if ebitda else 0, "low"),
    ]


def _build_tranches(debt: float) -> List[FacilityTranche]:
    return [
        FacilityTranche("Revolver ($75M commit, $12M drawn)",
                        round(debt * 0.04, 2), "SOFR+400", 400, 8.45, 2030, "maintenance"),
        FacilityTranche("First-Lien Term Loan",
                        round(debt * 0.62, 2), "SOFR+475", 475, 9.20, 2031, "maintenance"),
        FacilityTranche("Second-Lien Term Loan",
                        round(debt * 0.22, 2), "SOFR+825", 825, 12.70, 2032, "incurrence"),
        FacilityTranche("Mezzanine (PIK toggle)",
                        round(debt * 0.08, 2), "Fixed 12% cash + 3% PIK", 0, 15.00, 2033, "incurrence"),
        FacilityTranche("Seller Note",
                        round(debt * 0.04, 2), "Fixed 8%", 0, 8.00, 2030, "incurrence"),
    ]


def _build_stress(ebitda: float, debt: float) -> List[ScenarioStress]:
    scenarios = []
    deltas = [
        ("Base Case (no shock)", 0.0),
        ("Mild Miss (-5% EBITDA)", -0.05),
        ("Moderate Miss (-12% EBITDA)", -0.12),
        ("Severe Miss (-20% EBITDA)", -0.20),
        ("Downside (-30% EBITDA)", -0.30),
    ]
    for label, delta in deltas:
        proj_ebitda = ebitda * (1 + delta)
        proj_lev = debt / proj_ebitda if proj_ebitda > 0 else 99
        if proj_lev <= 6.0:
            status = "in compliance"
        elif proj_lev <= 6.25:
            status = "tight / monitoring"
        elif proj_lev <= 6.5:
            status = "technical breach"
        else:
            status = "material breach"
        headroom = (6.25 - proj_lev) / 6.25 if proj_ebitda > 0 else -1
        scenarios.append(ScenarioStress(
            scenario=label,
            ebitda_delta_pct=round(delta, 3),
            projected_ebitda_mm=round(proj_ebitda, 2),
            projected_leverage=round(proj_lev, 2),
            covenant_status=status,
            headroom_pct=round(headroom, 4),
        ))
    return scenarios


def _build_cure_rights(ebitda: float) -> List[CureRight]:
    return [
        CureRight("Leverage Cure (equity contribution)",
                  round(ebitda * 0.25, 2), "LP pro-rata equity injection",
                  30, 0),
        CureRight("EBITDA Cure (retroactive add-back)",
                  round(ebitda * 0.08, 2), "Sponsor equity added to EBITDA",
                  45, 0),
        CureRight("Liquidity Cure",
                  round(ebitda * 0.12, 2), "Cash equity to bolster balance sheet",
                  20, 0),
        CureRight("Rate Reset (if breach)",
                  0, "Spread increases +200bps until compliance",
                  0, 200),
        CureRight("Amend & Extend (negotiated)",
                  round(ebitda * 0.05, 2), "Amendment fee + equity as needed",
                  60, 100),
    ]


def _build_amort(initial_balance: float) -> List[AmortizationSchedule]:
    rows = []
    balance = initial_balance
    current_year = 2026
    for i in range(8):
        year = current_year + i
        mandatory = balance * 0.01  # 1% annual mandatory
        sweep = balance * 0.03 if i >= 2 else balance * 0.015  # excess cash flow sweep
        voluntary = balance * 0.02 if i >= 3 else 0
        new_bal = balance - mandatory - sweep - voluntary
        interest = balance * 0.092  # blended rate
        rows.append(AmortizationSchedule(
            year=year,
            opening_balance_mm=round(balance, 2),
            mandatory_amort_mm=round(mandatory, 2),
            excess_cash_sweep_mm=round(sweep, 2),
            voluntary_prepay_mm=round(voluntary, 2),
            closing_balance_mm=round(max(0, new_bal), 2),
            interest_expense_mm=round(interest, 2),
        ))
        balance = max(0, new_bal)
        if balance < initial_balance * 0.05:
            break
    return rows


def compute_covenant_headroom(
    ebitda_ttm_mm: float = 55.0,
    total_debt_mm: float = 275.0,
) -> CovenantResult:
    corpus = _load_corpus()

    covenants = _build_covenants(ebitda_ttm_mm, total_debt_mm)
    tranches = _build_tranches(total_debt_mm)
    stress = _build_stress(ebitda_ttm_mm, total_debt_mm)
    cure_rights = _build_cure_rights(ebitda_ttm_mm)
    amort = _build_amort(total_debt_mm)

    leverage = total_debt_mm / ebitda_ttm_mm if ebitda_ttm_mm else 0
    blended_rate = sum(t.balance_mm * t.all_in_rate_pct for t in tranches) / total_debt_mm if total_debt_mm else 0

    # Overall status: worst covenant
    breach_counts = {"low": 0, "medium": 0, "high": 0}
    for c in covenants:
        breach_counts[c.breach_risk] = breach_counts.get(c.breach_risk, 0) + 1
    if breach_counts.get("high", 0) > 0:
        overall = "tight"
    elif breach_counts.get("medium", 0) >= 2:
        overall = "monitoring"
    else:
        overall = "healthy"

    return CovenantResult(
        platform_ebitda_ttm_mm=round(ebitda_ttm_mm, 2),
        total_debt_mm=round(total_debt_mm, 2),
        total_leverage=round(leverage, 2),
        blended_rate_pct=round(blended_rate, 3),
        next_test_date="2026-06-30",
        overall_status=overall,
        covenants=covenants,
        tranches=tranches,
        stress_scenarios=stress,
        cure_rights=cure_rights,
        amort_schedule=amort,
        corpus_deal_count=len(corpus),
    )
