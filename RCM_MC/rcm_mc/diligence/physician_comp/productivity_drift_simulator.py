"""Post-close "comp model reset" drift simulator — the novel analytic.

For each provider, simulate what happens when a buyer proposes a
new comp model that pays less (dollar-terms) than the seller's
current model:

    Scenario A (buyer holds firm):
        Providers renegotiate or attrite. Attrition ramps over
        12-24 months. Per-provider revenue loss if that provider's
        NPI carried X% of collections.

    Scenario B (buyer capitulates):
        The buyer concedes to maintain seller-era dollars. The
        comp-per-wRVU ratio drifts up by the buyer's proposed
        reduction — effectively nullifying the acquisition thesis.

CY 2021 anchor: the E/M fee schedule change inflated wRVUs ~10%
without revenue increase. Providers who were on wRVU-based
comp captured unearned increases unless contracts were re-
benchmarked.

Monte Carlo is intentionally lightweight — 200 runs sufficient
for a per-provider ramp-curve dispersion band. Uses Python's
stdlib ``random`` (no numpy dependency here).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .comp_ingester import Provider


@dataclass
class DriftScenarioResult:
    scenario: str                 # 'hold_firm' | 'capitulate'
    ebitda_at_risk_usd: float
    median_attrition_pct: float
    p90_attrition_pct: float
    ramp_months: int
    narrative: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class DriftResult:
    provider_count: int
    total_seller_era_comp_usd: float
    total_buyer_proposed_comp_usd: float
    buyer_proposed_reduction_pct: float
    scenarios: List[DriftScenarioResult] = field(default_factory=list)
    cy2021_echo_risk: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_count": self.provider_count,
            "total_seller_era_comp_usd": self.total_seller_era_comp_usd,
            "total_buyer_proposed_comp_usd":
                self.total_buyer_proposed_comp_usd,
            "buyer_proposed_reduction_pct":
                self.buyer_proposed_reduction_pct,
            "scenarios": [s.to_dict() for s in self.scenarios],
            "cy2021_echo_risk": self.cy2021_echo_risk,
        }


def _attrition_curve(
    reduction_pct: float,
    provider_attrition_propensity: float = 0.5,
    rng: Optional[random.Random] = None,
) -> float:
    """Probability a provider attrits given a dollar-comp reduction.

    Empirical heuristic:
        base = 0 at 0% cut, 0.2 at 10%, 0.45 at 20%, 0.7 at 30%+.
    Perturb by propensity (specialty / age / market factors) and
    a small random noise. Returns a fraction [0, 1]."""
    r = rng or random.Random(0)
    if reduction_pct <= 0:
        base = 0.02
    elif reduction_pct < 0.10:
        base = 0.20 * (reduction_pct / 0.10)
    elif reduction_pct < 0.20:
        base = 0.20 + 0.25 * ((reduction_pct - 0.10) / 0.10)
    elif reduction_pct < 0.30:
        base = 0.45 + 0.25 * ((reduction_pct - 0.20) / 0.10)
    else:
        base = min(0.90, 0.70 + 0.20 * ((reduction_pct - 0.30) / 0.10))
    perturbed = base * (0.8 + 0.4 * provider_attrition_propensity)
    perturbed += r.uniform(-0.05, 0.05)
    return max(0.0, min(0.95, perturbed))


def simulate_productivity_drift(
    providers: List[Provider],
    *,
    buyer_proposed_reduction_pct: float,
    wrvu_inflation_pct: float = 0.0,
    n_runs: int = 200,
    seed: int = 42,
    ramp_months: int = 18,
) -> DriftResult:
    """Run the two-scenario drift simulation.

    ``buyer_proposed_reduction_pct``: fraction by which the buyer's
        comp model reduces dollar comp vs. seller era (e.g. 0.10
        = 10% cut).
    ``wrvu_inflation_pct``: CY 2021-style wRVU inflation with no
        revenue change. When >0, capitulating providers capture
        unearned comp increases proportional to this.
    """
    rng = random.Random(seed)
    seller_total = sum(p.total_comp_usd for p in providers)
    buyer_total = seller_total * (1.0 - buyer_proposed_reduction_pct)

    # Scenario A: hold firm. Monte Carlo the per-provider attrition.
    attrition_samples: List[float] = []
    ebitda_loss_samples: List[float] = []
    for _ in range(n_runs):
        total_lost_collections = 0.0
        attrited = 0
        for p in providers:
            # Attrition propensity: high-comp-per-wRVU providers
            # attrit less easily (more to renegotiate); low-comp
            # providers attrit more readily.
            propensity = 0.5
            prob = _attrition_curve(
                buyer_proposed_reduction_pct,
                provider_attrition_propensity=propensity,
                rng=rng,
            )
            if rng.random() < prob:
                attrited += 1
                # Collections loss: conservatively 50% of that
                # provider's book (some volume follows the new
                # replacement hire).
                total_lost_collections += 0.5 * float(
                    p.collections_annual_usd or 0.0
                )
        attrition_samples.append(
            attrited / len(providers) if providers else 0.0
        )
        # Rough conversion: 25% of lost collections ≈ EBITDA impact
        # (gross-margin specialty dependent; 25% is a conservative
        # lower-bound for specialty practices).
        ebitda_loss_samples.append(total_lost_collections * 0.25)

    attrition_samples.sort()
    ebitda_loss_samples.sort()
    med_attrition = (
        attrition_samples[len(attrition_samples) // 2]
        if attrition_samples else 0.0
    )
    p90_attrition = (
        attrition_samples[int(0.9 * len(attrition_samples))]
        if attrition_samples else 0.0
    )
    med_ebitda_loss = (
        ebitda_loss_samples[len(ebitda_loss_samples) // 2]
        if ebitda_loss_samples else 0.0
    )

    hold_firm = DriftScenarioResult(
        scenario="hold_firm",
        ebitda_at_risk_usd=med_ebitda_loss,
        median_attrition_pct=med_attrition,
        p90_attrition_pct=p90_attrition,
        ramp_months=ramp_months,
        narrative=(
            f"Buyer holds firm on {buyer_proposed_reduction_pct*100:.0f}% "
            f"comp reduction. Median attrition {med_attrition*100:.0f}%; "
            f"p90 {p90_attrition*100:.0f}%. EBITDA at median: "
            f"${med_ebitda_loss:,.0f}."
        ),
    )

    # Scenario B: capitulate — seller-era dollars maintained; ratio
    # drifts up. Adds CY 2021 echo when wRVU_inflation > 0.
    capitulate_loss = seller_total - buyer_total   # buyer eats the gap
    if wrvu_inflation_pct > 0:
        # Providers capture the inflated wRVUs at the seller-era
        # comp-per-wRVU rate; additional cost is wrvu_inflation ×
        # seller_total.
        capitulate_loss += wrvu_inflation_pct * seller_total
    capitulate = DriftScenarioResult(
        scenario="capitulate",
        ebitda_at_risk_usd=capitulate_loss,
        median_attrition_pct=0.02,
        p90_attrition_pct=0.05,
        ramp_months=ramp_months,
        narrative=(
            f"Buyer capitulates — comp ratio drifts up by "
            f"{buyer_proposed_reduction_pct*100:.0f}%"
            + (f" + {wrvu_inflation_pct*100:.0f}% wRVU inflation "
               f"(CY 2021 echo)" if wrvu_inflation_pct > 0 else "")
            + f". Annual drag: ${capitulate_loss:,.0f}."
        ),
    )

    return DriftResult(
        provider_count=len(providers),
        total_seller_era_comp_usd=seller_total,
        total_buyer_proposed_comp_usd=buyer_total,
        buyer_proposed_reduction_pct=buyer_proposed_reduction_pct,
        scenarios=[hold_firm, capitulate],
        cy2021_echo_risk=wrvu_inflation_pct >= 0.05,
    )
