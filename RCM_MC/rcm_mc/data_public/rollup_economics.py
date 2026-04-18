"""Roll-Up / Platform Economics Analyzer.

Roll-up theses dominate healthcare PE: aggregate fragmented practices,
standardize operations, arbitrage multiple expansion (e.g., 8x EBITDA
for solo practice -> 14x at platform scale). This module models:

- Multiple arbitrage waterfall
- Add-on pacing / deployment capacity
- Integration cost curve
- Synergy capture (cost vs revenue)
- Debt capacity per add-on
- Platform EBITDA walk
- Market-share trajectory
- Exit multiple assumptions
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AddOnCohort:
    cohort_year: int
    targets_closed: int
    avg_entry_multiple: float
    avg_ev_mm: float
    total_deployed_mm: float
    synergy_capture_pct: float
    time_to_full_integration_months: int


@dataclass
class MultipleArbitrageStep:
    stage: str
    ebitda_mm: float
    implied_multiple: float
    implied_ev_mm: float
    incremental_value_mm: float


@dataclass
class SynergyItem:
    category: str
    annual_run_rate_mm: float
    capture_timing_months: int
    one_time_cost_mm: float
    execution_risk: str
    confidence: str


@dataclass
class IntegrationCost:
    workstream: str
    cost_per_addon_k: float
    total_cost_mm: float
    duration_months: int
    peak_fte: int


@dataclass
class DebtCapacity:
    stage: str
    ebitda_mm: float
    leverage_multiple: float
    max_debt_mm: float
    equity_check_mm: float
    dry_powder_mm: float


@dataclass
class PlatformEBITDAWalk:
    period: str
    standalone_ebitda_mm: float
    acquired_ebitda_mm: float
    synergies_mm: float
    total_ebitda_mm: float
    organic_growth_pct: float


@dataclass
class ExitScenario:
    scenario: str
    exit_ebitda_mm: float
    exit_multiple: float
    exit_ev_mm: float
    less_debt_mm: float
    equity_proceeds_mm: float
    moic: float
    irr: float


@dataclass
class RollupResult:
    platform_entry_ebitda_mm: float
    platform_exit_ebitda_mm: float
    total_addons_closed: int
    total_deployed_mm: float
    total_synergies_mm: float
    multiple_arbitrage_mm: float
    add_on_cohorts: List[AddOnCohort]
    multiple_arb: List[MultipleArbitrageStep]
    synergies: List[SynergyItem]
    integration_costs: List[IntegrationCost]
    debt_capacity: List[DebtCapacity]
    ebitda_walk: List[PlatformEBITDAWalk]
    exit_scenarios: List[ExitScenario]
    base_case_moic: float
    base_case_irr: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 87):
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


def _build_cohorts(hold_years: int, target_addons_per_year: int,
                   base_multiple: float, base_ev: float) -> List[AddOnCohort]:
    import hashlib
    rows = []
    base_year = 2024
    for i in range(hold_years):
        h = int(hashlib.md5(str(i).encode()).hexdigest()[:6], 16)
        # Typically more add-ons in middle years
        closed = target_addons_per_year
        if i == 0: closed = max(1, int(target_addons_per_year * 0.4))   # ramp
        if i >= hold_years - 1: closed = max(1, int(target_addons_per_year * 0.5))  # slow down
        # Bolt-ons are typically smaller at lower multiples
        multiple = base_multiple * (0.70 + (h % 12) / 100)
        # Bolt-on EV typically $5-20M each for mid-market healthcare roll-up
        ev = base_ev * (0.08 + (h % 10) / 100)
        total_dep = closed * ev
        syn_capture = 0.45 + (i * 0.05) + (h % 10) / 100
        int_time = 12 + (h % 6)
        rows.append(AddOnCohort(
            cohort_year=base_year + i,
            targets_closed=closed,
            avg_entry_multiple=round(multiple, 2),
            avg_ev_mm=round(ev, 2),
            total_deployed_mm=round(total_dep, 2),
            synergy_capture_pct=round(min(syn_capture, 0.85), 3),
            time_to_full_integration_months=int_time,
        ))
    return rows


def _build_multiple_arb(entry_ebitda: float, exit_ebitda: float,
                        entry_multiple: float, exit_multiple: float) -> List[MultipleArbitrageStep]:
    rows = []
    # Entry point
    rows.append(MultipleArbitrageStep(
        stage="Entry (Platform Acquisition)",
        ebitda_mm=round(entry_ebitda, 2),
        implied_multiple=round(entry_multiple, 2),
        implied_ev_mm=round(entry_ebitda * entry_multiple, 2),
        incremental_value_mm=0,
    ))
    # Post-bolt-on EBITDA growth (no multiple change yet)
    bolton_ebitda = exit_ebitda * 0.55
    rows.append(MultipleArbitrageStep(
        stage="Post Bolt-On Growth",
        ebitda_mm=round(bolton_ebitda, 2),
        implied_multiple=round(entry_multiple * 1.15, 2),
        implied_ev_mm=round(bolton_ebitda * entry_multiple * 1.15, 2),
        incremental_value_mm=round(bolton_ebitda * entry_multiple * 1.15 - entry_ebitda * entry_multiple, 2),
    ))
    # Organic + synergy
    mid_ebitda = exit_ebitda * 0.75
    rows.append(MultipleArbitrageStep(
        stage="Organic + Synergy Capture",
        ebitda_mm=round(mid_ebitda, 2),
        implied_multiple=round(entry_multiple * 1.3, 2),
        implied_ev_mm=round(mid_ebitda * entry_multiple * 1.3, 2),
        incremental_value_mm=round(mid_ebitda * entry_multiple * 1.3 - bolton_ebitda * entry_multiple * 1.15, 2),
    ))
    # Platform-scale re-rating
    rows.append(MultipleArbitrageStep(
        stage="Platform Re-Rating",
        ebitda_mm=round(exit_ebitda, 2),
        implied_multiple=round(exit_multiple, 2),
        implied_ev_mm=round(exit_ebitda * exit_multiple, 2),
        incremental_value_mm=round(exit_ebitda * exit_multiple - mid_ebitda * entry_multiple * 1.3, 2),
    ))
    return rows


def _build_synergies(platform_ebitda: float, target_platform_revenue: float) -> List[SynergyItem]:
    syn = target_platform_revenue
    return [
        SynergyItem("RCM / Billing Consolidation", round(syn * 0.018, 2), 12, round(syn * 0.005, 2), "low", "high"),
        SynergyItem("Payer Contract Renegotiation", round(syn * 0.032, 2), 18, round(syn * 0.003, 2), "medium", "medium"),
        SynergyItem("Supply Chain / GPO Arbitrage", round(syn * 0.012, 2), 9, round(syn * 0.002, 2), "low", "high"),
        SynergyItem("Back-Office Consolidation (HR, Finance)", round(syn * 0.008, 2), 15, round(syn * 0.004, 2), "low", "high"),
        SynergyItem("Technology Platform Unification", round(syn * 0.014, 2), 24, round(syn * 0.012, 2), "high", "medium"),
        SynergyItem("Malpractice / Insurance Pooling", round(syn * 0.006, 2), 8, round(syn * 0.001, 2), "low", "high"),
        SynergyItem("Clinical Ops Standardization", round(syn * 0.025, 2), 20, round(syn * 0.008, 2), "medium", "medium"),
        SynergyItem("Revenue Cycle Optimization", round(syn * 0.021, 2), 14, round(syn * 0.005, 2), "medium", "high"),
        SynergyItem("Cross-Sell / New Service Lines", round(syn * 0.018, 2), 30, round(syn * 0.004, 2), "high", "low"),
    ]


def _build_integration_costs(addon_count: int) -> List[IntegrationCost]:
    items = [
        ("Financial / Tax Diligence", 185, 6),
        ("Legal / Contract Review", 225, 8),
        ("IT Systems Migration", 340, 9),
        ("EHR/PM Unification", 485, 14),
        ("Billing System Consolidation", 220, 8),
        ("HR / Payroll Integration", 95, 5),
        ("Rebrand / Marketing", 145, 7),
        ("Compliance Program Alignment", 118, 4),
        ("Facilities / Lease Review", 78, 3),
    ]
    rows = []
    for ws, per_addon_k, duration in items:
        total = per_addon_k * addon_count / 1000
        peak_fte = max(2, int(addon_count * 0.8))
        rows.append(IntegrationCost(
            workstream=ws,
            cost_per_addon_k=per_addon_k,
            total_cost_mm=round(total, 2),
            duration_months=duration,
            peak_fte=peak_fte,
        ))
    return rows


def _build_debt_capacity(entry_ebitda: float, exit_ebitda: float) -> List[DebtCapacity]:
    rows = []
    stages = [
        ("Entry", entry_ebitda, 5.5),
        ("Post Year-1 Add-Ons", entry_ebitda * 1.6, 5.75),
        ("Post Year-2 Add-Ons", entry_ebitda * 2.2, 6.0),
        ("Post Year-3 Add-Ons", entry_ebitda * 2.8, 5.75),
        ("Exit Year", exit_ebitda, 5.5),
    ]
    for stage, ebit, lev in stages:
        max_debt = ebit * lev
        equity = max_debt * 0.45  # typical 55/45 ds/equity
        dry_powder = max_debt - (ebit * 4.8)  # 4.8x is current leverage
        rows.append(DebtCapacity(
            stage=stage,
            ebitda_mm=round(ebit, 2),
            leverage_multiple=round(lev, 2),
            max_debt_mm=round(max_debt, 2),
            equity_check_mm=round(equity, 2),
            dry_powder_mm=round(dry_powder, 2),
        ))
    return rows


def _build_ebitda_walk(entry_ebitda: float, exit_ebitda: float,
                       hold_years: int) -> List[PlatformEBITDAWalk]:
    rows = []
    base_year = 2024
    prev = entry_ebitda
    for i in range(hold_years + 1):
        if i == 0:
            rows.append(PlatformEBITDAWalk(
                period=f"{base_year} (Entry)",
                standalone_ebitda_mm=round(entry_ebitda, 2),
                acquired_ebitda_mm=0,
                synergies_mm=0,
                total_ebitda_mm=round(entry_ebitda, 2),
                organic_growth_pct=0,
            ))
            continue
        progress = i / max(hold_years, 1)
        standalone = prev * 1.04  # organic 4%
        acquired = (exit_ebitda - entry_ebitda) * progress * 0.65
        synergy = (exit_ebitda - entry_ebitda) * progress * 0.15
        total = standalone + acquired + synergy
        # Normalize to hit exit target
        if i == hold_years:
            total = exit_ebitda
        rows.append(PlatformEBITDAWalk(
            period=f"{base_year + i}",
            standalone_ebitda_mm=round(standalone, 2),
            acquired_ebitda_mm=round(acquired, 2),
            synergies_mm=round(synergy, 2),
            total_ebitda_mm=round(total, 2),
            organic_growth_pct=round((total / prev - 1), 4) if prev else 0,
        ))
        prev = total
    return rows


def _build_exit_scenarios(exit_ebitda: float, entry_ebitda: float,
                          entry_multiple: float, hold_years: int,
                          total_deployed: float) -> List[ExitScenario]:
    rows = []
    scenarios = [
        ("Downside (7x)", exit_ebitda * 0.85, 7.0),
        ("Base (10x)", exit_ebitda, 10.0),
        ("Upside Strategic (13x)", exit_ebitda * 1.08, 13.0),
        ("IPO / Public Comp (15x)", exit_ebitda * 1.12, 15.0),
    ]
    for name, ebit, mult in scenarios:
        ev = ebit * mult
        debt = ebit * 5.2  # assume 5.2x on exit
        proceeds = ev - debt
        equity_in = entry_ebitda * entry_multiple * 0.40 + total_deployed * 0.30
        moic = proceeds / equity_in if equity_in > 0 else 0
        irr = moic ** (1 / hold_years) - 1 if moic > 0 and hold_years > 0 else 0
        rows.append(ExitScenario(
            scenario=name,
            exit_ebitda_mm=round(ebit, 2),
            exit_multiple=round(mult, 2),
            exit_ev_mm=round(ev, 2),
            less_debt_mm=round(debt, 2),
            equity_proceeds_mm=round(proceeds, 2),
            moic=round(moic, 2),
            irr=round(irr, 4),
        ))
    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_rollup_economics(
    platform_entry_ebitda_mm: float = 12.0,
    platform_exit_ebitda_target_mm: float = 48.0,
    entry_multiple: float = 9.5,
    exit_multiple: float = 13.5,
    hold_years: int = 5,
    target_addons_per_year: int = 6,
) -> RollupResult:
    corpus = _load_corpus()

    entry_ev = platform_entry_ebitda_mm * entry_multiple
    exit_ev = platform_exit_ebitda_target_mm * exit_multiple

    cohorts = _build_cohorts(hold_years, target_addons_per_year,
                             entry_multiple, entry_ev)
    total_addons = sum(c.targets_closed for c in cohorts)
    total_deployed = sum(c.total_deployed_mm for c in cohorts)

    multiple_arb = _build_multiple_arb(
        platform_entry_ebitda_mm, platform_exit_ebitda_target_mm,
        entry_multiple, exit_multiple,
    )
    # Revenue proxy at exit (assume 22% margin)
    exit_revenue = platform_exit_ebitda_target_mm / 0.22
    synergies = _build_synergies(platform_exit_ebitda_target_mm, exit_revenue)
    integration_costs = _build_integration_costs(total_addons)
    debt_capacity = _build_debt_capacity(platform_entry_ebitda_mm,
                                         platform_exit_ebitda_target_mm)
    ebitda_walk = _build_ebitda_walk(platform_entry_ebitda_mm,
                                     platform_exit_ebitda_target_mm, hold_years)
    exit_scenarios = _build_exit_scenarios(
        platform_exit_ebitda_target_mm, platform_entry_ebitda_mm,
        entry_multiple, hold_years, total_deployed,
    )

    # Total synergies
    total_synergies_mm = sum(s.annual_run_rate_mm for s in synergies)
    multiple_arb_value = (
        platform_exit_ebitda_target_mm * exit_multiple
        - platform_entry_ebitda_mm * entry_multiple
    )

    # Base case = the "Base (10x)" scenario
    base = next((s for s in exit_scenarios if "Base" in s.scenario), exit_scenarios[1])

    return RollupResult(
        platform_entry_ebitda_mm=round(platform_entry_ebitda_mm, 2),
        platform_exit_ebitda_mm=round(platform_exit_ebitda_target_mm, 2),
        total_addons_closed=total_addons,
        total_deployed_mm=round(total_deployed, 2),
        total_synergies_mm=round(total_synergies_mm, 2),
        multiple_arbitrage_mm=round(multiple_arb_value, 2),
        add_on_cohorts=cohorts,
        multiple_arb=multiple_arb,
        synergies=synergies,
        integration_costs=integration_costs,
        debt_capacity=debt_capacity,
        ebitda_walk=ebitda_walk,
        exit_scenarios=exit_scenarios,
        base_case_moic=round(base.moic, 2),
        base_case_irr=round(base.irr, 4),
        corpus_deal_count=len(corpus),
    )
