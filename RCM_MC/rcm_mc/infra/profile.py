
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Tuple
import copy


# These fields describe the hospital "volume / mix" profile.
# They should be identical between Actual and Benchmark scenarios.
DEFAULT_PROFILE_KEYS = ("revenue_share", "avg_claim_dollars")


@dataclass(frozen=True)
class HospitalProfile:
    annual_revenue: float
    payer_profile: Dict[str, Dict[str, float]]  # payer -> {key: value}


def extract_hospital_profile(cfg: Dict[str, Any], keys: Iterable[str] = DEFAULT_PROFILE_KEYS) -> HospitalProfile:
    """Extract structural hospital profile fields from a scenario config."""
    keys = tuple(keys)
    hospital = cfg.get("hospital", {})
    annual_revenue = float(hospital.get("annual_revenue", 0.0))
    payer_profile: Dict[str, Dict[str, float]] = {}
    for payer, pconf in cfg.get("payers", {}).items():
        payer_profile[payer] = {k: float(pconf.get(k)) for k in keys if k in pconf}
    return HospitalProfile(annual_revenue=annual_revenue, payer_profile=payer_profile)


def apply_hospital_profile(cfg: Dict[str, Any], profile: HospitalProfile, keys: Iterable[str] = DEFAULT_PROFILE_KEYS) -> Dict[str, Any]:
    """
    Apply a hospital profile to a scenario config.

    Mutates and returns cfg (caller can deepcopy first).
    """
    keys = tuple(keys)
    cfg.setdefault("hospital", {})
    cfg["hospital"]["annual_revenue"] = float(profile.annual_revenue)

    payers = cfg.get("payers", {}) or {}
    for payer, vals in profile.payer_profile.items():
        if payer not in payers:
            continue
        for k in keys:
            if k in vals:
                payers[payer][k] = float(vals[k])
    cfg["payers"] = payers
    return cfg


def align_benchmark_to_actual(
    actual_cfg: Dict[str, Any],
    benchmark_cfg: Dict[str, Any],
    keys: Iterable[str] = DEFAULT_PROFILE_KEYS,
    deepcopy_inputs: bool = True,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Ensure the Benchmark scenario uses the *same hospital profile* as Actual.

    This prevents accidental apples-to-oranges comparisons where calibration updates
    payer mix / avg claim on Actual but Benchmark keeps defaults, which can distort:
      - denial volumes (cases) and therefore
      - rework costs, backlog, and cycle time economics.

    Returns (actual_cfg, aligned_benchmark_cfg).
    """
    a = copy.deepcopy(actual_cfg) if deepcopy_inputs else actual_cfg
    b = copy.deepcopy(benchmark_cfg) if deepcopy_inputs else benchmark_cfg

    profile = extract_hospital_profile(a, keys=keys)
    b = apply_hospital_profile(b, profile, keys=keys)
    return a, b
