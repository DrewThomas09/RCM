"""
Preset payer policy shock scenarios for Scenario Explorer.
Runs Monte Carlo under shocked configs and returns ebitda_drag stats for client-side overlay.
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List

from ..infra.config import load_and_validate
from ..core.simulator import simulate_compare


def apply_shocks_to_config(cfg: Dict[str, Any], shocks: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply shocks to config. Shocks format:
    { "payers": { "Commercial": { "idr_mult": 1.20, "fwr_mult": 1.0, ... }, ... } }
    """
    out = copy.deepcopy(cfg)
    payers_shocks = shocks.get("payers", {})
    for payer, pshocks in payers_shocks.items():
        if payer not in out.get("payers", {}):
            continue
        p = out["payers"][payer]
        idr_mult = float(pshocks.get("idr_mult", 1.0))
        fwr_mult = float(pshocks.get("fwr_mult", 1.0))
        upr_mult = float(pshocks.get("upr_mult", 1.0))
        if "denials" in p and "idr" in p["denials"] and "mean" in p["denials"]["idr"]:
            m = p["denials"]["idr"]["mean"]
            p["denials"]["idr"]["mean"] = min(m * idr_mult, float(p["denials"]["idr"].get("max", 0.5)))
        if "denials" in p and "fwr" in p["denials"] and "mean" in p["denials"]["fwr"]:
            m = p["denials"]["fwr"]["mean"]
            p["denials"]["fwr"]["mean"] = min(m * fwr_mult, float(p["denials"]["fwr"].get("max", 0.8)))
        if "underpayments" in p and "upr" in p["underpayments"] and "mean" in p["underpayments"]["upr"]:
            m = p["underpayments"]["upr"]["mean"]
            p["underpayments"]["upr"]["mean"] = min(m * upr_mult, float(p["underpayments"]["upr"].get("max", 0.3)))
    return out


PRESET_SHOCKS: List[Dict[str, Any]] = [
    {
        "id": "commercial_idr_20",
        "name": "Commercial IDR +20% (Prior-Auth risk)",
        "shocks": {"payers": {"Commercial": {"idr_mult": 1.20}}},
    },
    {
        "id": "medicare_idr_15",
        "name": "Medicare IDR +15%",
        "shocks": {"payers": {"Medicare": {"idr_mult": 1.15}}},
    },
    {
        "id": "all_payers_idr_10",
        "name": "All payers IDR +10%",
        "shocks": {
            "payers": {
                "Commercial": {"idr_mult": 1.10},
                "Medicare": {"idr_mult": 1.10},
                "Medicaid": {"idr_mult": 1.10},
            }
        },
    },
]


def run_preset_shocks(
    actual_path: str,
    benchmark_path: str,
    n_sims: int = 3000,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """
    Run preset payer policy shock scenarios. Returns list of
    { id, name, ebitda_drag: { mean, p10, p90 } } for Scenario Explorer.
    """
    actual = load_and_validate(actual_path)
    benchmark = load_and_validate(benchmark_path)
    results: List[Dict[str, Any]] = []
    for i, preset in enumerate(PRESET_SHOCKS):
        shocked = apply_shocks_to_config(actual, preset["shocks"])
        df = simulate_compare(shocked, benchmark, n_sims=n_sims, seed=seed + 1000 + i, align_profile=True)
        results.append({
            "id": preset["id"],
            "name": preset["name"],
            "ebitda_drag": {
                "mean": float(df["ebitda_drag"].mean()),
                "p10": float(df["ebitda_drag"].quantile(0.1)),
                "p90": float(df["ebitda_drag"].quantile(0.9)),
            },
        })
    return results
