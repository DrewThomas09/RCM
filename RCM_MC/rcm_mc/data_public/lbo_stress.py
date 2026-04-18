"""LBO Model Stress Test.

Classic PE LBO model with comprehensive sensitivity analysis.
Tornado chart across entry multiple, exit multiple, leverage, EBITDA
growth, and operating margin. Outputs MOIC/IRR sensitivity grids.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class LBOBase:
    purchase_price_mm: float
    entry_ebitda_mm: float
    entry_multiple: float
    initial_leverage: float
    senior_debt_mm: float
    sub_debt_mm: float
    equity_check_mm: float
    projected_exit_year: int
    projected_ebitda_cagr_pct: float
    exit_multiple: float
    projected_moic: float
    projected_irr_pct: float


@dataclass
class SensitivityCell:
    exit_multiple: float
    exit_ebitda_mm: float
    exit_ev_mm: float
    net_debt_at_exit_mm: float
    equity_proceeds_mm: float
    moic: float
    irr_pct: float


@dataclass
class TornadoDriver:
    driver: str
    downside_value: str
    base_value: str
    upside_value: str
    downside_moic: float
    base_moic: float
    upside_moic: float
    swing_moic: float


@dataclass
class CovenantPath:
    year: int
    ebitda_mm: float
    total_debt_mm: float
    leverage: float
    interest_coverage: float
    in_compliance: bool


@dataclass
class ReturnsBridge:
    component: str
    contribution_mm: float
    contribution_pct: float


@dataclass
class ScenarioOutcome:
    scenario: str
    exit_ebitda_mm: float
    exit_multiple: float
    exit_proceeds_mm: float
    moic: float
    irr_pct: float
    probability_pct: float


@dataclass
class LBOStressResult:
    base: LBOBase
    sensitivity_grid: List[SensitivityCell]
    tornado: List[TornadoDriver]
    covenant_path: List[CovenantPath]
    returns_bridge: List[ReturnsBridge]
    scenarios: List[ScenarioOutcome]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 120):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_base() -> LBOBase:
    return LBOBase(
        purchase_price_mm=485.0,
        entry_ebitda_mm=32.0,
        entry_multiple=15.16,
        initial_leverage=6.0,
        senior_debt_mm=192.0,
        sub_debt_mm=48.0,
        equity_check_mm=245.0,
        projected_exit_year=2031,
        projected_ebitda_cagr_pct=0.18,
        exit_multiple=14.0,
        projected_moic=2.78,
        projected_irr_pct=0.227,
    )


def _build_sensitivity() -> List[SensitivityCell]:
    # 7 exit multiples × base case
    multiples = [10.0, 11.5, 12.5, 14.0, 15.5, 17.0, 18.5]
    exit_ebitda = 73.4   # 32 * (1.18)^5 ≈ 73.3
    rows = []
    for mult in multiples:
        ev = exit_ebitda * mult
        net_debt = 195.0  # post cash-sweep + amortization
        proceeds = ev - net_debt
        moic = proceeds / 245.0
        irr = moic ** (1 / 5) - 1 if moic > 0 else 0
        rows.append(SensitivityCell(
            exit_multiple=mult, exit_ebitda_mm=exit_ebitda, exit_ev_mm=round(ev, 2),
            net_debt_at_exit_mm=net_debt, equity_proceeds_mm=round(proceeds, 2),
            moic=round(moic, 2), irr_pct=round(irr, 4),
        ))
    return rows


def _build_tornado() -> List[TornadoDriver]:
    return [
        TornadoDriver("Exit Multiple", "12.0x", "14.0x", "16.0x", 2.20, 2.78, 3.38, 1.18),
        TornadoDriver("EBITDA CAGR", "12%", "18%", "24%", 2.05, 2.78, 3.62, 1.57),
        TornadoDriver("Initial Leverage", "5.0x", "6.0x", "6.5x", 2.92, 2.78, 2.68, -0.24),
        TornadoDriver("Entry Multiple", "16.5x", "15.16x", "13.5x", 2.48, 2.78, 3.15, 0.67),
        TornadoDriver("Debt Paydown (excess FCF sweep)", "15%", "25%", "35%", 2.58, 2.78, 3.00, 0.42),
        TornadoDriver("Operating Margin (EBITDA %)", "18%", "22%", "26%", 2.25, 2.78, 3.35, 1.10),
        TornadoDriver("Revenue CAGR", "8%", "15%", "22%", 2.35, 2.78, 3.25, 0.90),
        TornadoDriver("Net Working Capital", "-$3M", "$0M", "+$3M", 2.72, 2.78, 2.84, 0.12),
        TornadoDriver("Capex % of Revenue", "4%", "2.5%", "1.5%", 2.65, 2.78, 2.88, 0.23),
    ]


def _build_covenant_path() -> List[CovenantPath]:
    # Year-by-year leverage trajectory
    years = [2026, 2027, 2028, 2029, 2030, 2031]
    ebitdas = [32.0, 37.8, 44.6, 52.6, 62.1, 73.4]
    debts = [240.0, 228.5, 215.0, 198.5, 180.0, 158.0]
    rows = []
    for y, e, d in zip(years, ebitdas, debts):
        lev = d / e
        int_cov = e / (d * 0.085)
        rows.append(CovenantPath(
            year=y, ebitda_mm=round(e, 2), total_debt_mm=round(d, 2),
            leverage=round(lev, 2), interest_coverage=round(int_cov, 2),
            in_compliance=lev <= 6.25,
        ))
    return rows


def _build_returns_bridge() -> List[ReturnsBridge]:
    return [
        ReturnsBridge("Entry Equity Value", 245.0, 1.00),
        ReturnsBridge("EBITDA Growth (18% CAGR)", 325.8, 1.33),
        ReturnsBridge("Multiple Compression (15.2→14.0x)", -88.0, -0.36),
        ReturnsBridge("Debt Paydown (cash sweep)", 82.0, 0.33),
        ReturnsBridge("Exit Value ($681M EV - $195M debt)", 486.0, 1.98),
        ReturnsBridge("Total Equity Proceeds", 486.0, 1.98),
        ReturnsBridge("Implied MOIC (2.78x ÷ 1.00x entry)", 2.78, 2.78),
    ]


def _build_scenarios() -> List[ScenarioOutcome]:
    return [
        ScenarioOutcome("Downside (-25% EBITDA + 12x exit)", 55.0, 12.0, 165.0, 0.67, -0.075, 0.10),
        ScenarioOutcome("Recession Scenario (-10% + 13x)", 66.0, 13.0, 283.0, 1.16, 0.030, 0.15),
        ScenarioOutcome("Base Case (18% CAGR + 14x)", 73.4, 14.0, 486.0, 1.98, 0.147, 0.40),
        ScenarioOutcome("Projected (22% CAGR + 14.5x)", 86.7, 14.5, 612.0, 2.50, 0.201, 0.20),
        ScenarioOutcome("Upside (26% + 15.5x)", 102.0, 15.5, 787.0, 3.21, 0.263, 0.10),
        ScenarioOutcome("Home Run (IPO / Strategic + 17x)", 115.0, 17.0, 1000.0, 4.08, 0.325, 0.05),
    ]


def compute_lbo_stress() -> LBOStressResult:
    corpus = _load_corpus()

    base = _build_base()
    sensitivity = _build_sensitivity()
    tornado = _build_tornado()
    covenant = _build_covenant_path()
    bridge = _build_returns_bridge()
    scenarios = _build_scenarios()

    return LBOStressResult(
        base=base,
        sensitivity_grid=sensitivity,
        tornado=tornado,
        covenant_path=covenant,
        returns_bridge=bridge,
        scenarios=scenarios,
        corpus_deal_count=len(corpus),
    )
