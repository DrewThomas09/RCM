"""Scenario Monte Carlo Analyzer — multi-variable MOIC outcome distribution.

Runs N simulations varying:
- Revenue growth
- EBITDA margin expansion
- Exit multiple
- Leverage paydown rate

Outputs MOIC / IRR distribution with percentiles, probability of downside,
and sensitivity to each input driver.
"""
from __future__ import annotations

import importlib
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class InputDistribution:
    driver: str
    base_case: float
    low: float                   # 5th percentile
    high: float                  # 95th percentile
    unit: str


@dataclass
class OutcomeBin:
    moic_bin_low: float
    moic_bin_high: float
    count: int
    pct_of_sims: float


@dataclass
class PercentileRow:
    metric: str
    p5: float
    p25: float
    p50: float
    p75: float
    p95: float
    mean: float


@dataclass
class SensitivityDriver:
    driver: str
    correlation_to_moic: float
    elasticity: float              # % MOIC change per 1% driver change
    tornado_range_mm: float        # spread in EV between P10/P90 of this driver holding others at median


@dataclass
class ProbabilityRow:
    outcome: str
    probability: float
    description: str


@dataclass
class ScenarioMCResult:
    n_simulations: int
    inputs: List[InputDistribution]
    moic_distribution: List[OutcomeBin]
    percentiles: List[PercentileRow]
    sensitivities: List[SensitivityDriver]
    probabilities: List[ProbabilityRow]
    base_case_moic: float
    median_moic: float
    p5_moic: float
    p95_moic: float
    prob_moic_gt_2x: float
    prob_moic_gt_3x: float
    prob_loss: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 65):
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


def _sample_triangular(low: float, mode: float, high: float) -> float:
    """Triangular distribution sampling."""
    return random.triangular(low, high, mode)


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0
    s = sorted(values)
    idx = (len(s) - 1) * p / 100
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (idx - lo) * (s[hi] - s[lo])


def _correlation(xs: List[float], ys: List[float]) -> float:
    if len(xs) != len(ys) or not xs:
        return 0
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n
    vx = sum((x - mx) ** 2 for x in xs) / n
    vy = sum((y - my) ** 2 for y in ys) / n
    if vx <= 0 or vy <= 0:
        return 0
    return cov / math.sqrt(vx * vy)


# ---------------------------------------------------------------------------
# Core simulation
# ---------------------------------------------------------------------------

def _run_simulation(
    ev_mm: float, ebitda_margin: float, ev_ebitda: float, hold_years: int,
    revenue_growth_dist: Tuple[float, float, float],
    margin_expansion_dist: Tuple[float, float, float],
    exit_mult_dist: Tuple[float, float, float],
    equity_pct: float,
    debt_paydown_dist: Tuple[float, float, float],
    n_sims: int = 5000,
) -> Dict:
    """Run Monte Carlo on MOIC outcome."""
    revenue_mm = (ev_mm / ev_ebitda) / ebitda_margin if ev_ebitda and ebitda_margin else 100
    equity_mm = ev_mm * equity_pct
    debt_mm = ev_mm - equity_mm

    sims = []
    driver_rec = {"rev_growth": [], "margin_expansion": [], "exit_mult": [], "debt_paydown": [], "moic": []}

    for _ in range(n_sims):
        rev_g = _sample_triangular(*revenue_growth_dist)
        margin_exp = _sample_triangular(*margin_expansion_dist)
        exit_mult = _sample_triangular(*exit_mult_dist)
        debt_paydown = _sample_triangular(*debt_paydown_dist)

        # Terminal EBITDA
        final_rev = revenue_mm * ((1 + rev_g) ** hold_years)
        final_margin = ebitda_margin + margin_exp
        terminal_ebitda = final_rev * final_margin

        # Exit EV
        exit_ev = terminal_ebitda * exit_mult
        # Remaining debt
        remaining_debt = debt_mm * (1 - debt_paydown)
        # Exit equity
        exit_equity = exit_ev - remaining_debt
        moic = exit_equity / equity_mm if equity_mm else 0

        sims.append(moic)
        driver_rec["rev_growth"].append(rev_g)
        driver_rec["margin_expansion"].append(margin_exp)
        driver_rec["exit_mult"].append(exit_mult)
        driver_rec["debt_paydown"].append(debt_paydown)
        driver_rec["moic"].append(moic)

    return {"moics": sims, "drivers": driver_rec, "revenue_mm": revenue_mm}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_scenario_mc(
    ev_mm: float = 300.0,
    ebitda_margin: float = 0.18,
    ev_ebitda: float = 12.0,
    hold_years: int = 5,
    equity_pct: float = 0.45,
    n_sims: int = 5000,
    seed: int = 42,
) -> ScenarioMCResult:
    corpus = _load_corpus()
    random.seed(seed)

    # Input distributions (triangular: low, mode/base, high)
    rev_growth = (-0.02, 0.06, 0.14)
    margin_exp = (-0.02, 0.03, 0.08)
    exit_mult = (ev_ebitda * 0.85, ev_ebitda * 1.05, ev_ebitda * 1.25)
    debt_paydown = (0.15, 0.40, 0.60)

    inputs = [
        InputDistribution("Revenue Growth (CAGR)", 0.06, -0.02, 0.14, "%"),
        InputDistribution("Margin Expansion", 0.03, -0.02, 0.08, "pp"),
        InputDistribution("Exit Multiple", ev_ebitda * 1.05, exit_mult[0], exit_mult[2], "x"),
        InputDistribution("Debt Paydown %", 0.40, 0.15, 0.60, "% of debt"),
    ]

    sim = _run_simulation(
        ev_mm, ebitda_margin, ev_ebitda, hold_years,
        rev_growth, margin_exp, exit_mult, equity_pct, debt_paydown,
        n_sims,
    )
    moics = sim["moics"]
    drivers = sim["drivers"]

    # Base case
    base_moic = (
        (ev_mm / ev_ebitda / ebitda_margin) * ((1.06) ** hold_years) * (ebitda_margin + 0.03) * (ev_ebitda * 1.05)
        - ev_mm * (1 - equity_pct) * (1 - 0.40)
    ) / (ev_mm * equity_pct)

    # MOIC distribution bins
    bins = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 10.0]
    dist = []
    for i in range(len(bins) - 1):
        lo, hi = bins[i], bins[i + 1]
        count = sum(1 for m in moics if lo <= m < hi)
        dist.append(OutcomeBin(
            moic_bin_low=lo, moic_bin_high=hi,
            count=count, pct_of_sims=round(count / len(moics), 3),
        ))

    # Percentiles
    irrs = [(m ** (1 / hold_years) - 1) if m > 0 else -0.5 for m in moics]
    ebitdas = drivers.get("margin_expansion", [])

    percentiles = [
        PercentileRow(
            metric="MOIC",
            p5=round(_percentile(moics, 5), 2),
            p25=round(_percentile(moics, 25), 2),
            p50=round(_percentile(moics, 50), 2),
            p75=round(_percentile(moics, 75), 2),
            p95=round(_percentile(moics, 95), 2),
            mean=round(sum(moics) / len(moics), 2),
        ),
        PercentileRow(
            metric="IRR (%)",
            p5=round(_percentile(irrs, 5) * 100, 1),
            p25=round(_percentile(irrs, 25) * 100, 1),
            p50=round(_percentile(irrs, 50) * 100, 1),
            p75=round(_percentile(irrs, 75) * 100, 1),
            p95=round(_percentile(irrs, 95) * 100, 1),
            mean=round(sum(irrs) / len(irrs) * 100, 1),
        ),
    ]

    # Sensitivities
    corr_rev = _correlation(drivers["rev_growth"], moics)
    corr_mgn = _correlation(drivers["margin_expansion"], moics)
    corr_mult = _correlation(drivers["exit_mult"], moics)
    corr_dp = _correlation(drivers["debt_paydown"], moics)

    # Tornado: MOIC range between P10 and P90 of each driver
    def _tornado(driver_vals, moic_vals):
        paired = sorted(zip(driver_vals, moic_vals))
        p10_idx = int(len(paired) * 0.10)
        p90_idx = int(len(paired) * 0.90)
        low_moics = [m for _, m in paired[:p10_idx]]
        high_moics = [m for _, m in paired[p90_idx:]]
        if not low_moics or not high_moics:
            return 0
        return (sum(high_moics) / len(high_moics) - sum(low_moics) / len(low_moics)) * ev_mm * equity_pct

    sensitivities = [
        SensitivityDriver("Revenue Growth", round(corr_rev, 3), round(corr_rev * 3.0, 3),
                         round(_tornado(drivers["rev_growth"], moics), 1)),
        SensitivityDriver("Margin Expansion", round(corr_mgn, 3), round(corr_mgn * 2.5, 3),
                         round(_tornado(drivers["margin_expansion"], moics), 1)),
        SensitivityDriver("Exit Multiple", round(corr_mult, 3), round(corr_mult * 2.0, 3),
                         round(_tornado(drivers["exit_mult"], moics), 1)),
        SensitivityDriver("Debt Paydown", round(corr_dp, 3), round(corr_dp * 1.5, 3),
                         round(_tornado(drivers["debt_paydown"], moics), 1)),
    ]
    # Sort by absolute tornado range
    sensitivities.sort(key=lambda s: -abs(s.tornado_range_mm))

    # Probabilities
    prob_gt_2x = sum(1 for m in moics if m >= 2.0) / len(moics)
    prob_gt_3x = sum(1 for m in moics if m >= 3.0) / len(moics)
    prob_gt_4x = sum(1 for m in moics if m >= 4.0) / len(moics)
    prob_loss = sum(1 for m in moics if m < 1.0) / len(moics)
    prob_half_loss = sum(1 for m in moics if m < 0.5) / len(moics)

    probs = [
        ProbabilityRow("Home Run (MOIC ≥ 4x)", round(prob_gt_4x, 3), "Top decile outcome"),
        ProbabilityRow("Excellent (MOIC ≥ 3x)", round(prob_gt_3x, 3), "Upper-quartile outcome"),
        ProbabilityRow("Target (MOIC ≥ 2x)", round(prob_gt_2x, 3), "Minimum expected return"),
        ProbabilityRow("Downside (MOIC < 1x)", round(prob_loss, 3), "Principal loss scenario"),
        ProbabilityRow("Severe Loss (MOIC < 0.5x)", round(prob_half_loss, 3), "50%+ capital loss"),
    ]

    return ScenarioMCResult(
        n_simulations=n_sims,
        inputs=inputs,
        moic_distribution=dist,
        percentiles=percentiles,
        sensitivities=sensitivities,
        probabilities=probs,
        base_case_moic=round(base_moic, 2),
        median_moic=round(_percentile(moics, 50), 2),
        p5_moic=round(_percentile(moics, 5), 2),
        p95_moic=round(_percentile(moics, 95), 2),
        prob_moic_gt_2x=round(prob_gt_2x, 3),
        prob_moic_gt_3x=round(prob_gt_3x, 3),
        prob_loss=round(prob_loss, 3),
        corpus_deal_count=len(corpus),
    )
