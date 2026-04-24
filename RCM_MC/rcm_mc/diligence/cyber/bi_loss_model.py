"""Business-interruption loss Monte Carlo.

For a target with:
    - revenue_per_day_baseline_usd
    - probability_of_incident_per_year
    - downtime distribution (log-normal parameters from historical
      breach data; Change Healthcare was ~21 days for claims
      reconciliation)
    - direct_plus_indirect_cost_multiplier (legal, OCR settlement,
      credit monitoring, reputation — typically 2-4x the direct
      revenue loss)

Simulate expected-loss-per-year + P90/P95 tail. Uses Python
stdlib random — no numpy dependency.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BILossResult:
    expected_loss_usd: float
    p90_loss_usd: float
    p95_loss_usd: float
    incident_probability_per_year: float
    n_runs: int
    mean_downtime_days: float
    runs_sample: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expected_loss_usd": self.expected_loss_usd,
            "p90_loss_usd": self.p90_loss_usd,
            "p95_loss_usd": self.p95_loss_usd,
            "incident_probability_per_year":
                self.incident_probability_per_year,
            "n_runs": self.n_runs,
            "mean_downtime_days": self.mean_downtime_days,
        }


def simulate_bi_loss(
    *,
    revenue_per_day_baseline_usd: float,
    incident_probability_per_year: float = 0.05,
    downtime_mean_days: float = 14.0,
    downtime_sigma_days: float = 0.7,
    direct_plus_indirect_multiplier: float = 2.5,
    n_runs: int = 2000,
    seed: int = 42,
    cascade_risk_multiplier: float = 1.0,
) -> BILossResult:
    """Run the BI-loss Monte Carlo.

    Model:
        For each trial:
            occurs = Bernoulli(incident_probability_per_year)
            if occurs:
                downtime_days = LogNormal(mean_log, sigma_log)
                direct_loss = revenue_per_day * downtime_days
                total_loss = direct_loss * multiplier * cascade_mult
            else:
                total_loss = 0
        Returns mean + P90 + P95 across trials.

    ``cascade_risk_multiplier`` captures BA-cascade risk — set to
    2.5 when Change Healthcare is in the BA graph.
    """
    rng = random.Random(seed)
    # Convert mean_days to LogNormal parameters. We treat
    # downtime_mean_days as the median of the log-normal for
    # tractability; real-world breach data fits this reasonably.
    mu = math.log(max(downtime_mean_days, 1.0))
    sigma = max(downtime_sigma_days, 0.01)

    losses: List[float] = []
    downtimes: List[float] = []
    for _ in range(n_runs):
        if rng.random() > incident_probability_per_year:
            losses.append(0.0)
            continue
        downtime = math.exp(rng.gauss(mu, sigma))
        downtimes.append(downtime)
        direct = revenue_per_day_baseline_usd * downtime
        total = (
            direct
            * direct_plus_indirect_multiplier
            * cascade_risk_multiplier
        )
        losses.append(total)

    losses_sorted = sorted(losses)
    n = len(losses_sorted)
    mean_loss = sum(losses_sorted) / n if n else 0.0
    p90 = losses_sorted[int(0.90 * n)] if n else 0.0
    p95 = losses_sorted[int(0.95 * n)] if n else 0.0
    mean_downtime = (
        sum(downtimes) / len(downtimes) if downtimes else 0.0
    )
    return BILossResult(
        expected_loss_usd=mean_loss,
        p90_loss_usd=p90,
        p95_loss_usd=p95,
        incident_probability_per_year=incident_probability_per_year,
        n_runs=n_runs,
        mean_downtime_days=mean_downtime,
        runs_sample=losses_sorted[:5] + losses_sorted[-5:],
    )
