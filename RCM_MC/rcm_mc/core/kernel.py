"""
Stable kernel entrypoint for RCM Monte Carlo.
No formula changes; clean API wrapping the simulator.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import pandas as pd

from ..infra.profile import align_benchmark_to_actual
from .simulator import simulate_compare


@dataclass
class SimulationResult:
    """Result of a single simulation run (actual vs benchmark)."""
    df: pd.DataFrame
    ebitda_drag_mean: float
    ebitda_drag_p10: float
    ebitda_drag_p90: float
    economic_drag_mean: float

    @property
    def summary(self) -> Dict[str, float]:
        return {
            "ebitda_drag_mean": self.ebitda_drag_mean,
            "ebitda_drag_p10": self.ebitda_drag_p10,
            "ebitda_drag_p90": self.ebitda_drag_p90,
            "economic_drag_mean": self.economic_drag_mean,
        }


def run_simulation(
    actual_cfg: Dict[str, Any],
    benchmark_cfg: Dict[str, Any],
    n_sims: int,
    seed: int,
    align_profile: bool = True,
) -> SimulationResult:
    """
    Run Monte Carlo simulation: actual vs benchmark.
    Returns structured result; no formula changes.
    """
    df = simulate_compare(
        actual_cfg,
        benchmark_cfg,
        n_sims=n_sims,
        seed=seed,
        align_profile=align_profile,
    )
    ebitda = df["ebitda_drag"]
    economic = df["economic_drag"] if "economic_drag" in df.columns else df.get("drag_economic_cost", pd.Series([0.0] * len(df)))
    return SimulationResult(
        df=df,
        ebitda_drag_mean=float(ebitda.mean()),
        ebitda_drag_p10=float(ebitda.quantile(0.1)),
        ebitda_drag_p90=float(ebitda.quantile(0.9)),
        economic_drag_mean=float(economic.mean()),
    )
