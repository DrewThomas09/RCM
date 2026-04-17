from __future__ import annotations

import copy
from typing import Any, Dict, Optional

import numpy as np
import yaml

from ..infra.config import validate_config
from ..core.distributions import dist_moments


class ValuePlanError(ValueError):
    pass


# Metrics we support in the gap-closure plan, and the direction that represents improvement.
# - "lower": lower is better (e.g., denial rates)
# - "higher": higher is better (e.g., recovery rate)
METRIC_DIRECTIONS: Dict[str, str] = {
    "idr": "lower",
    "fwr": "lower",
    "dar_clean_days": "lower",
    "upr": "lower",
    "underpay_severity": "lower",
    "underpay_recovery": "higher",
    "stage_mix": "toward_benchmark",
}


def load_value_plan(path: str) -> Dict[str, Any]:
    """Load a YAML value-creation plan."""
    try:
        with open(path, "r") as f:
            plan = yaml.safe_load(f)
    except Exception as e:
        raise ValuePlanError(f"Failed to read value plan YAML: {path}") from e
    if not isinstance(plan, dict):
        raise ValuePlanError("Value plan YAML must be a dict")
    return plan


def _clip01(x: Any) -> float:
    try:
        v = float(x)
    except Exception:
        v = 0.0
    return float(np.clip(v, 0.0, 1.0))


def get_gap_closure(plan: Dict[str, Any], payer: str, metric: str, default: float = 0.0) -> float:
    """
    Resolve a gap-closure fraction k in [0,1].

    Supported structures (both optional):
      - plan.gap_closure[metric]
      - plan.gap_closure_by_payer[payer][metric]

    payer-specific overrides win.
    """
    k = float(default)
    if isinstance(plan.get("gap_closure"), dict) and metric in plan["gap_closure"]:
        k = float(plan["gap_closure"][metric])
    if isinstance(plan.get("gap_closure_by_payer"), dict):
        po = plan["gap_closure_by_payer"].get(payer)
        if isinstance(po, dict) and metric in po:
            k = float(po[metric])
    return _clip01(k)


def _blend_scalar(actual: float, benchmark: float, k: float, direction: str) -> float:
    """Blend actual toward benchmark by k, only in the improving direction."""
    a = float(actual)
    b = float(benchmark)
    k = _clip01(k)

    if direction == "lower":
        # Only move down if benchmark is lower.
        diff = min(b - a, 0.0)
        return a + k * diff
    if direction == "higher":
        # Only move up if benchmark is higher.
        diff = max(b - a, 0.0)
        return a + k * diff
    # Default: move toward benchmark.
    return a + k * (b - a)


def _safe_sd_from_spec(spec: Dict[str, Any]) -> float:
    _, var = dist_moments(spec)
    return float(np.sqrt(max(var, 0.0)))


def blend_dist_spec(
    actual_spec: Dict[str, Any],
    benchmark_spec: Dict[str, Any],
    k: float,
    direction: str,
    *,
    clamp_min: Optional[float] = None,
    clamp_max: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Create a new distribution spec by shifting the *mean* of actual_spec toward benchmark_spec.

    This keeps the model explainable:
      - we keep the distribution family (beta vs normal vs triangular),
      - we move the center toward best-practice, and
      - we optionally blend the spread (sd) toward the benchmark's spread.
    """

    actual_spec = actual_spec or {"dist": "fixed", "value": 0.0}
    benchmark_spec = benchmark_spec or actual_spec
    k = _clip01(k)
    direction = str(direction or "toward").lower()

    dist = str(actual_spec.get("dist", "fixed")).lower()
    a_mean, _ = dist_moments(actual_spec)
    b_mean, _ = dist_moments(benchmark_spec)
    a_sd = _safe_sd_from_spec(actual_spec)
    b_sd = _safe_sd_from_spec(benchmark_spec)

    t_mean = _blend_scalar(a_mean, b_mean, k, direction)
    t_sd = (1.0 - k) * a_sd + k * b_sd

    if clamp_min is not None:
        t_mean = max(float(clamp_min), float(t_mean))
    if clamp_max is not None:
        t_mean = min(float(clamp_max), float(t_mean))

    # Preserve distribution family where possible.
    if dist == "fixed":
        return {"dist": "fixed", "value": float(t_mean)}

    if dist == "beta":
        out = copy.deepcopy(actual_spec)
        out["mean"] = float(np.clip(t_mean, 1e-6, 1 - 1e-6))
        out["sd"] = float(max(t_sd, 1e-6))
        # Respect optional min/max keys from the original spec.
        if "min" in out:
            out["min"] = float(out["min"])
        if "max" in out:
            out["max"] = float(out["max"])
        return out

    if dist in ("normal_trunc", "normal", "gaussian"):
        out = copy.deepcopy(actual_spec)
        out["mean"] = float(t_mean)
        out["sd"] = float(max(t_sd, 1e-6))
        return out

    if dist == "triangular":
        # Shift + (optionally) scale the triangle around the mode.
        out = copy.deepcopy(actual_spec)
        low = float(out.get("low", 0.0))
        mode = float(out.get("mode", low))
        high = float(out.get("high", mode))

        # Shift so the mean moves by delta.
        delta = float(t_mean) - float(a_mean)
        mode2 = mode + delta

        # Scale the spread (roughly) if we have a non-zero sd.
        scale = 1.0
        if a_sd > 1e-9:
            scale = float(np.clip(t_sd / a_sd, 0.25, 4.0))

        left = max(mode - low, 0.0) * scale
        right = max(high - mode, 0.0) * scale
        low2 = mode2 - left
        high2 = mode2 + right
        if low2 > mode2:
            low2 = mode2
        if high2 < mode2:
            high2 = mode2

        out["low"] = float(low2)
        out["mode"] = float(mode2)
        out["high"] = float(high2)
        return out

    if dist in ("gamma", "lognormal"):
        out = copy.deepcopy(actual_spec)
        out["mean"] = float(max(t_mean, 1e-9))
        out["sd"] = float(max(t_sd, 1e-9))
        return out

    # Fallback to fixed.
    return {"dist": "fixed", "value": float(t_mean)}


def blend_stage_mix(actual_mix: Dict[str, float], benchmark_mix: Dict[str, float], k: float) -> Dict[str, float]:
    """Blend denial stage mix shares toward benchmark and normalize."""
    k = _clip01(k)
    a = {str(s): float(v) for s, v in (actual_mix or {}).items()}
    b = {str(s): float(v) for s, v in (benchmark_mix or {}).items()}
    keys = sorted(set(a.keys()) | set(b.keys()))
    raw = {}
    for kk in keys:
        raw[kk] = float(a.get(kk, 0.0) + k * (b.get(kk, 0.0) - a.get(kk, 0.0)))
    # Clamp and normalize.
    vals = np.array([max(raw[kk], 0.0) for kk in keys], dtype=float)
    s = float(vals.sum())
    if s <= 0:
        vals = np.ones(len(keys), dtype=float) / len(keys)
    else:
        vals = vals / s
    return {kk: float(vals[i]) for i, kk in enumerate(keys)}


def build_target_config(actual_cfg: Dict[str, Any], benchmark_cfg: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a Target scenario by closing a fraction of the Actual-to-Benchmark gap.

    This is the core PE "value creation" abstraction:
      - Actual is where the target is today.
      - Benchmark is best-practice.
      - Target is "Actual improved", e.g. 30–60% of the gap closed over 12 months.
    """
    a = copy.deepcopy(actual_cfg)
    b = benchmark_cfg  # read-only
    plan = plan or {}

    payers_a = a.get("payers", {}) or {}
    payers_b = b.get("payers", {}) or {}

    for payer, pconf_a in payers_a.items():
        if payer not in payers_b:
            continue
        pconf_b = payers_b[payer]

        # Clean-claim days in A/R
        k = get_gap_closure(plan, payer, "dar_clean_days", default=0.0)
        if "dar_clean_days" in pconf_a and "dar_clean_days" in pconf_b:
            pconf_a["dar_clean_days"] = blend_dist_spec(
                pconf_a["dar_clean_days"],
                pconf_b["dar_clean_days"],
                k,
                METRIC_DIRECTIONS["dar_clean_days"],
                clamp_min=1.0,
            )

        # Denials
        if bool(pconf_a.get("include_denials", False)) and isinstance(pconf_a.get("denials"), dict) and isinstance(pconf_b.get("denials"), dict):
            da = pconf_a["denials"]
            db = pconf_b["denials"]

            k_idr = get_gap_closure(plan, payer, "idr", default=0.0)
            k_fwr = get_gap_closure(plan, payer, "fwr", default=0.0)
            k_mix = get_gap_closure(plan, payer, "stage_mix", default=0.0)

            if "idr" in da and "idr" in db:
                da["idr"] = blend_dist_spec(
                    da["idr"],
                    db["idr"],
                    k_idr,
                    METRIC_DIRECTIONS["idr"],
                    clamp_min=0.0,
                    clamp_max=1.0,
                )

            if "fwr" in da and "fwr" in db:
                da["fwr"] = blend_dist_spec(
                    da["fwr"],
                    db["fwr"],
                    k_fwr,
                    METRIC_DIRECTIONS["fwr"],
                    clamp_min=0.0,
                    clamp_max=1.0,
                )

            if isinstance(da.get("stage_mix"), dict) and isinstance(db.get("stage_mix"), dict) and k_mix > 0:
                da["stage_mix"] = blend_stage_mix(da["stage_mix"], db["stage_mix"], k_mix)

        # Underpayments
        if bool(pconf_a.get("include_underpayments", False)) and isinstance(pconf_a.get("underpayments"), dict) and isinstance(pconf_b.get("underpayments"), dict):
            ua = pconf_a["underpayments"]
            ub = pconf_b["underpayments"]

            k_upr = get_gap_closure(plan, payer, "upr", default=0.0)
            k_sev = get_gap_closure(plan, payer, "underpay_severity", default=0.0)
            k_rec = get_gap_closure(plan, payer, "underpay_recovery", default=0.0)

            if "upr" in ua and "upr" in ub:
                ua["upr"] = blend_dist_spec(
                    ua["upr"],
                    ub["upr"],
                    k_upr,
                    METRIC_DIRECTIONS["upr"],
                    clamp_min=0.0,
                    clamp_max=1.0,
                )

            if "severity" in ua and "severity" in ub and k_sev > 0:
                ua["severity"] = blend_dist_spec(
                    ua["severity"],
                    ub["severity"],
                    k_sev,
                    METRIC_DIRECTIONS["underpay_severity"],
                    clamp_min=0.0,
                    clamp_max=1.0,
                )

            if "recovery" in ua and "recovery" in ub and k_rec > 0:
                ua["recovery"] = blend_dist_spec(
                    ua["recovery"],
                    ub["recovery"],
                    k_rec,
                    METRIC_DIRECTIONS["underpay_recovery"],
                    clamp_min=0.0,
                    clamp_max=1.0,
                )

    # Operational levers (optional)
    ops = plan.get("operations", {}) if isinstance(plan.get("operations"), dict) else {}
    if isinstance(ops.get("denial_capacity"), dict):
        den_cap = a.setdefault("operations", {}).setdefault("denial_capacity", {})
        cap_plan = ops["denial_capacity"]
        if "fte" in cap_plan:
            den_cap["fte"] = float(cap_plan["fte"])
        if "fte_delta" in cap_plan:
            den_cap["fte"] = float(den_cap.get("fte", 0.0)) + float(cap_plan["fte_delta"])
        if "denials_per_fte_per_day" in cap_plan:
            den_cap["denials_per_fte_per_day"] = float(cap_plan["denials_per_fte_per_day"])

    # Add optional metadata to make outputs easier to interpret
    meta = a.setdefault("meta", {})
    meta["scenario"] = "Target"
    meta["value_plan"] = plan.get("name", "value_plan")

    # Ensure we didn't break the schema
    return validate_config(a)
