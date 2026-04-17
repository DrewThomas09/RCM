from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..core.simulator import simulate_compare


def _beta_from_mean_sd(mean: float, sd: float) -> Tuple[float, float]:
    m = float(np.clip(mean, 1e-6, 1 - 1e-6))
    sd = float(max(sd, 1e-8))
    var = sd * sd
    max_var = m * (1 - m) * 0.99
    if var >= max_var:
        var = max_var
    k = m * (1 - m) / var - 1.0
    a = m * k
    b = (1 - m) * k
    if not np.isfinite(a) or not np.isfinite(b) or a <= 0 or b <= 0:
        a = 10.0 * m
        b = 10.0 * (1 - m)
        a = max(a, 1.0)
        b = max(b, 1.0)
    return float(a), float(b)


def _shock_dist_mean(spec: Dict[str, Any], factor: float, lo: float, hi: float) -> Dict[str, Any]:
    """Return a *new* dist spec with mean multiplied by factor, and sd held roughly constant."""
    spec = copy.deepcopy(spec)
    dist = str(spec.get("dist", "")).strip().lower()
    factor = float(factor)

    if dist == "beta":
        m = float(spec.get("mean", 0.0))
        sd = float(spec.get("sd", 0.0))
        m2 = float(np.clip(m * factor, lo, hi))
        a, b = _beta_from_mean_sd(m2, sd if sd > 0 else max(0.05 * m2, 1e-3))
        spec["mean"] = m2
        spec["alpha"] = a
        spec["beta"] = b
        return spec

    if dist == "normal":
        m = float(spec.get("mean", 0.0))
        sd = float(spec.get("sd", 0.0))
        m2 = float(np.clip(m * factor, lo, hi))
        spec["mean"] = m2
        spec["sd"] = sd if sd > 0 else max(0.10 * abs(m2), 1e-6)
        return spec

    # fallback: only mean-like keys
    if "mean" in spec:
        spec["mean"] = float(np.clip(float(spec["mean"]) * factor, lo, hi))
    return spec


@dataclass(frozen=True)
class StressScenario:
    name: str
    description: str
    apply_fn: Any  # (cfg_actual, cfg_bench) -> (cfg_actual, cfg_bench)


def scenario_denial_rate_spike(payer: str = "Commercial", factor: float = 1.25) -> StressScenario:
    def _apply(a: Dict[str, Any], b: Dict[str, Any]):
        a2 = copy.deepcopy(a)
        b2 = copy.deepcopy(b)
        for cfg in (a2, b2):
            if payer in cfg["payers"] and cfg["payers"][payer].get("include_denials", False):
                spec = cfg["payers"][payer]["denials"]["idr"]
                cfg["payers"][payer]["denials"]["idr"] = _shock_dist_mean(spec, factor, 0.0, 0.50)
        return a2, b2
    return StressScenario(
        name=f"{payer}_IDR_x{factor:.2f}",
        description=f"Increase {payer} initial denial rate mean by {factor:.0%} (policy tightening / system issue).",
        apply_fn=_apply,
    )


def scenario_writeoff_worsens(payer: str = "Medicare", factor: float = 1.20) -> StressScenario:
    def _apply(a: Dict[str, Any], b: Dict[str, Any]):
        a2 = copy.deepcopy(a)
        b2 = copy.deepcopy(b)
        for cfg in (a2, b2):
            if payer in cfg["payers"] and cfg["payers"][payer].get("include_denials", False):
                spec = cfg["payers"][payer]["denials"]["fwr"]
                cfg["payers"][payer]["denials"]["fwr"] = _shock_dist_mean(spec, factor, 0.0, 0.95)
        return a2, b2
    return StressScenario(
        name=f"{payer}_FWR_x{factor:.2f}",
        description=f"Increase {payer} final write-off rate mean by {factor:.0%} (appeal effectiveness drops / timeliness).",
        apply_fn=_apply,
    )


def scenario_capacity_crunch(factor: float = 0.70) -> StressScenario:
    def _apply(a: Dict[str, Any], b: Dict[str, Any]):
        a2 = copy.deepcopy(a)
        b2 = copy.deepcopy(b)
        for cfg in (a2, b2):
            cap = cfg["operations"]["denial_capacity"]
            cap["enabled"] = True
            cap["mode"] = "queue"
            cap["fte"] = float(cap.get("fte", 12.0)) * float(factor)
        return a2, b2
    return StressScenario(
        name=f"Capacity_FTE_x{factor:.2f}",
        description=f"Reduce denial team capacity (FTE) by {(1-factor):.0%} (turnover / hiring freeze).",
        apply_fn=_apply,
    )


def scenario_payer_mix_shift(delta_to_medicaid: float = 0.05) -> StressScenario:
    def _apply(a: Dict[str, Any], b: Dict[str, Any]):
        a2 = copy.deepcopy(a)
        b2 = copy.deepcopy(b)
        for cfg in (a2, b2):
            # Move share from Commercial to Medicaid
            com = cfg["payers"].get("Commercial", {})
            med = cfg["payers"].get("Medicaid", {})
            if not com or not med:
                continue
            d = float(delta_to_medicaid)
            com["revenue_share"] = float(max(0.0, float(com["revenue_share"]) - d))
            med["revenue_share"] = float(min(1.0, float(med["revenue_share"]) + d))
        return a2, b2
    return StressScenario(
        name=f"PayerMix_Medicaid_+{delta_to_medicaid:.0%}",
        description=f"Shift {delta_to_medicaid:.0%} revenue from Commercial to Medicaid (mix deterioration).",
        apply_fn=_apply,
    )


def default_stress_suite() -> List[StressScenario]:
    return [
        scenario_denial_rate_spike("Commercial", 1.25),
        scenario_writeoff_worsens("Medicare", 1.20),
        scenario_capacity_crunch(0.70),
        scenario_payer_mix_shift(0.05),
    ]


def run_stress_suite(
    *,
    actual_cfg: Dict[str, Any],
    benchmark_cfg: Dict[str, Any],
    n_sims: int,
    seed: int,
    align_profile: bool = True,
    suite: Optional[List[StressScenario]] = None,
) -> pd.DataFrame:
    suite = suite or default_stress_suite()

    rows = []
    # Baseline
    base_df = simulate_compare(actual_cfg, benchmark_cfg, n_sims=n_sims, seed=seed, align_profile=align_profile)
    rows.append(
        {
            "scenario": "BASE",
            "description": "Baseline (no shock)",
            "mean_ebitda_drag": float(base_df["ebitda_drag"].mean()),
            "p50_ebitda_drag": float(base_df["ebitda_drag"].quantile(0.50)),
            "p90_ebitda_drag": float(base_df["ebitda_drag"].quantile(0.90)),
            "p95_ebitda_drag": float(base_df["ebitda_drag"].quantile(0.95)),
            "mean_economic_drag": float(base_df["economic_drag"].mean()),
        }
    )

    for sc in suite:
        a2, b2 = sc.apply_fn(actual_cfg, benchmark_cfg)
        df = simulate_compare(a2, b2, n_sims=n_sims, seed=seed + 13, align_profile=align_profile)
        rows.append(
            {
                "scenario": sc.name,
                "description": sc.description,
                "mean_ebitda_drag": float(df["ebitda_drag"].mean()),
                "p50_ebitda_drag": float(df["ebitda_drag"].quantile(0.50)),
                "p90_ebitda_drag": float(df["ebitda_drag"].quantile(0.90)),
                "p95_ebitda_drag": float(df["ebitda_drag"].quantile(0.95)),
                "mean_economic_drag": float(df["economic_drag"].mean()),
            }
        )

    return pd.DataFrame(rows)
