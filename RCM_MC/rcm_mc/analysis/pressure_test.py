"""Management plan pressure-test.

Buy-side diligence always asks: "management claims X — is it realistic?"
This module answers that structurally:

1. **Achievability** — for each target, classify as ``conservative``,
   ``stretch``, ``aggressive``, or ``aspirational`` based on where it sits
   between the target's actual and the published top-decile benchmark.
2. **Sensitivity to miss** — run Monte Carlo at 100% / 75% / 50% / 0% of the
   claimed improvement and report mean EBITDA drag at each level. Makes the
   cost of missing the plan concrete in dollars.
3. **Timeline cross-check** — for each target metric, look up matching
   initiatives in :file:`configs/initiatives_library.yaml` and surface the
   median ``ramp_months``. If management says "12 months" and the library
   says typical ramp is 18, that's a red flag.

The management plan YAML is intentionally small — just the targets a partner
would actually defend:

.. code-block:: yaml

    horizon_months: 12
    targets:
      idr_blended: 0.10
      fwr_blended: 0.25
      dar_blended: 45
    notes: "New denial prevention program + Epic upgrade"
"""
from __future__ import annotations

import copy
import math
import os
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml

from ..data.intake import _blended_mean, scale_blended_to_per_payer
from ..core.simulator import simulate_compare


# Maps the three supported management-plan target keys to their config path
# (so we can both read current values and scale the config for scenarios).
_TARGET_METRICS = {
    "idr_blended": ("denials", "idr"),
    "fwr_blended": ("denials", "fwr"),
    "dar_blended": ("dar_clean_days",),
}

# Which initiative-library ``param`` strings map to each plan target. Used only
# for ramp-month cross-referencing; misses degrade to "no matching initiatives".
_INITIATIVE_PARAM_MAP = {
    "idr_blended": {"idr"},
    "fwr_blended": {"fwr"},
    "dar_blended": {"dar_clean_days", "dar"},
}

# Ratio of progress toward benchmark that separates classification buckets.
# Tuned so "conservative" = easily-proven gains, "aspirational" = beating the
# top-decile reference (rare outside best-in-class operators).
_CONSERVATIVE_UPPER = 0.25
_STRETCH_UPPER = 0.75
_AGGRESSIVE_UPPER = 1.10


@dataclass
class TargetAssessment:
    target_key: str
    actual_blended: float
    benchmark_blended: float
    target_value: float
    progress_ratio: float
    classification: str
    matching_initiatives: List[str] = field(default_factory=list)
    median_ramp_months: Optional[float] = None


# ── Loaders ─────────────────────────────────────────────────────────────────

def _coerce_finite_number(value: Any, *, label: str) -> float:
    """Reject non-numeric / non-finite plan inputs before simulation.

    Pressure-test outputs are only defensible when the input plan is
    explicit and machine-valid. Coercing here prevents a quoted YAML
    scalar like ``"0.11"`` from leaking through as a string, while
    still rejecting ``nan`` / ``inf`` / booleans that would make the
    later scenario math misleading.
    """
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric, got bool")
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be numeric, got {value!r}") from None
    if not math.isfinite(out):
        raise ValueError(f"{label} must be finite, got {value!r}")
    return out


def _normalize_plan(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize the public management-plan shape.

    This module is imported both from the CLI (which loads YAML from
    disk) and directly in tests / packet plumbing. Centralizing the
    validation keeps every entry point on the same contract.
    """
    if not isinstance(raw, dict):
        raise ValueError(
            f"Management plan must be a YAML mapping, got {type(raw).__name__}",
        )
    targets = raw.get("targets") or {}
    if not isinstance(targets, dict) or not targets:
        raise ValueError("Management plan needs a non-empty 'targets' block")

    normalized = dict(raw)
    normalized_targets: Dict[str, float] = {}
    for key, raw_target in targets.items():
        if key not in _TARGET_METRICS:
            raise ValueError(
                f"Unknown target '{key}'; supported: {sorted(_TARGET_METRICS)}"
            )
        target = _coerce_finite_number(raw_target, label=f"Target '{key}'")
        if key in ("idr_blended", "fwr_blended"):
            if not (0.0 < target < 1.0):
                raise ValueError(
                    f"Target '{key}' must be between 0 and 1 as a blended rate, got {target!r}",
                )
        elif key == "dar_blended" and target <= 0.0:
            raise ValueError(
                f"Target '{key}' must be > 0 clean A/R days, got {target!r}",
            )
        normalized_targets[key] = target
    normalized["targets"] = normalized_targets

    horizon = raw.get("horizon_months")
    if horizon is not None:
        horizon_num = _coerce_finite_number(
            horizon, label="horizon_months",
        )
        if horizon_num <= 0 or not float(horizon_num).is_integer():
            raise ValueError(
                f"horizon_months must be a positive whole number of months, got {horizon!r}",
            )
        normalized["horizon_months"] = int(horizon_num)
    return normalized


def _normalize_run_inputs(
    *,
    n_sims: int,
    achievement_levels: Optional[List[float]] = None,
) -> List[float]:
    """Validate simulation-run knobs before burning Monte Carlo cycles."""
    if int(n_sims) <= 0:
        raise ValueError(f"n_sims must be > 0, got {n_sims!r}")
    levels = [0.0, 0.5, 0.75, 1.0] if achievement_levels is None else list(achievement_levels)
    if not levels:
        raise ValueError("achievement_levels must be a non-empty list of fractions")
    normalized: List[float] = []
    for raw_level in levels:
        level = _coerce_finite_number(raw_level, label="achievement level")
        if level < 0.0 or level > 1.0:
            raise ValueError(
                f"achievement level must be between 0 and 1, got {raw_level!r}",
            )
        normalized.append(level)
    return sorted(normalized)

def load_management_plan(path: str) -> Dict[str, Any]:
    """Load a management plan YAML. Accepts only the documented subset of keys."""
    with open(path) as f:
        raw = yaml.safe_load(f) or {}
    return _normalize_plan(raw)


def load_initiative_library(path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load the stock initiatives library. Returns [] on missing / malformed."""
    if path is None:
        path = str(Path(__file__).resolve().parent.parent.parent / "configs" / "initiatives_library.yaml")
    if not os.path.isfile(path):
        return []
    try:
        with open(path) as f:
            doc = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        return []
    return list(doc.get("initiatives") or [])


# ── Classification ──────────────────────────────────────────────────────────

def classify_target(
    actual_value: float,
    benchmark_value: float,
    target_value: float,
) -> str:
    """Classify ambition of a management target.

    The convention here assumes the metric is a 'lower-is-better' driver (IDR,
    FWR, DAR days). The benchmark represents the top-decile (best-practice)
    value. Progress ratio measures how far toward the benchmark the target
    goes:

    - ``progress ≤ 25%`` → ``conservative`` (small step toward best practice)
    - ``25% < progress ≤ 75%`` → ``stretch`` (meaningful but proven gains)
    - ``75% < progress ≤ 110%`` → ``aggressive`` (close to or at top-decile)
    - ``progress > 110%`` → ``aspirational`` (beyond published top-decile)
    """
    gap = actual_value - benchmark_value
    # If actual is already at or better than benchmark, any further reduction is aspirational.
    if gap <= 1e-9:
        return "aspirational" if target_value < actual_value else "conservative"
    progress = (actual_value - target_value) / gap
    if progress <= _CONSERVATIVE_UPPER:
        return "conservative"
    if progress <= _STRETCH_UPPER:
        return "stretch"
    if progress <= _AGGRESSIVE_UPPER:
        return "aggressive"
    return "aspirational"


def match_initiatives_for_target(
    target_key: str,
    initiatives: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Return initiatives whose ``affected_parameters`` include this target's param."""
    wanted = _INITIATIVE_PARAM_MAP.get(target_key, set())
    if not wanted:
        return []
    out = []
    for init in initiatives:
        affected = init.get("affected_parameters") or []
        if any((p or {}).get("param") in wanted for p in affected):
            out.append(init)
    return out


def _median_ramp_months(initiatives: List[Dict[str, Any]]) -> Optional[float]:
    ramps = [float(i.get("ramp_months")) for i in initiatives if i.get("ramp_months") is not None]
    if not ramps:
        return None
    return float(statistics.median(ramps))


def assess_targets(
    actual_cfg: Dict[str, Any],
    benchmark_cfg: Dict[str, Any],
    plan: Dict[str, Any],
    initiatives: Optional[List[Dict[str, Any]]] = None,
) -> List[TargetAssessment]:
    """Build per-target assessments (no simulation — pure classification + lookup)."""
    plan = _normalize_plan(plan)
    if initiatives is None:
        initiatives = load_initiative_library()
    assessments: List[TargetAssessment] = []
    for key, tgt in (plan.get("targets") or {}).items():
        path = _TARGET_METRICS[key]
        actual_blended = _blended_mean(actual_cfg, path) or 0.0
        bench_blended = _blended_mean(benchmark_cfg, path) or 0.0
        classification = classify_target(actual_blended, bench_blended, float(tgt))
        matched = match_initiatives_for_target(key, initiatives)
        assessments.append(TargetAssessment(
            target_key=key,
            actual_blended=actual_blended,
            benchmark_blended=bench_blended,
            target_value=float(tgt),
            progress_ratio=(
                (actual_blended - float(tgt)) / (actual_blended - bench_blended)
                if (actual_blended - bench_blended) > 1e-9 else float("inf")
            ),
            classification=classification,
            matching_initiatives=[i.get("id") or i.get("name", "?") for i in matched],
            median_ramp_months=_median_ramp_months(matched),
        ))
    return assessments


# ── Miss-sensitivity scenarios ──────────────────────────────────────────────

def _build_scenario_cfg(
    actual_cfg: Dict[str, Any],
    plan_targets: Dict[str, float],
    achievement: float,
) -> Dict[str, Any]:
    """Return a deep-copied actual_cfg with each target moved ``achievement`` of
    the way from the actual value toward the plan target.

    ``achievement=1.0`` means plan fully delivered; ``0.0`` means status quo.
    """
    cfg = copy.deepcopy(actual_cfg)
    for key, target in plan_targets.items():
        path = _TARGET_METRICS.get(key)
        if path is None:
            continue
        current = _blended_mean(cfg, path)
        if current is None:
            continue
        scenario_blended = current - float(achievement) * (current - float(target))
        # Reuse the intake wizard's scaling — same contract, same clamps.
        clamp_max = 0.95 if key in ("idr_blended", "fwr_blended") else 200.0
        clamp_min = 0.001 if key in ("idr_blended", "fwr_blended") else 5.0
        scale_blended_to_per_payer(
            cfg, path, scenario_blended,
            min_clamp=clamp_min, max_clamp=clamp_max,
        )
    return cfg


def run_miss_scenarios(
    actual_cfg: Dict[str, Any],
    benchmark_cfg: Dict[str, Any],
    plan: Dict[str, Any],
    n_sims: int = 2000,
    seed: int = 42,
    achievement_levels: Optional[List[float]] = None,
    align_profile: bool = True,
) -> pd.DataFrame:
    """Run the core Monte Carlo at each achievement level of the plan.

    Returns a dataframe with columns: ``achievement``, ``ebitda_drag_mean``,
    ``ebitda_drag_p10``, ``ebitda_drag_p90``. Rows ordered from 0% (status quo)
    up to 100% (plan fully hit).
    """
    plan = _normalize_plan(plan)
    achievement_levels = _normalize_run_inputs(
        n_sims=n_sims, achievement_levels=achievement_levels,
    )
    targets = plan.get("targets") or {}
    rows: List[Dict[str, Any]] = []
    for idx, lvl in enumerate(achievement_levels):
        scenario_cfg = _build_scenario_cfg(actual_cfg, targets, achievement=lvl)
        df = simulate_compare(
            scenario_cfg, benchmark_cfg,
            n_sims=n_sims,
            seed=seed + idx,
            align_profile=align_profile,
        )
        rows.append({
            "achievement": lvl,
            "ebitda_drag_mean": float(df["ebitda_drag"].mean()),
            "ebitda_drag_p10": float(df["ebitda_drag"].quantile(0.10)),
            "ebitda_drag_p90": float(df["ebitda_drag"].quantile(0.90)),
        })
    return pd.DataFrame(rows)


# ── Top-level orchestrator ──────────────────────────────────────────────────

def assessments_to_dataframe(assessments: List[TargetAssessment]) -> pd.DataFrame:
    rows = []
    for a in assessments:
        rows.append({
            "target": a.target_key,
            "actual_blended": a.actual_blended,
            "benchmark_blended": a.benchmark_blended,
            "target_value": a.target_value,
            "progress_ratio": a.progress_ratio,
            "classification": a.classification,
            "matching_initiatives": ", ".join(a.matching_initiatives) or "—",
            "median_ramp_months": a.median_ramp_months,
        })
    return pd.DataFrame(rows)


def run_pressure_test(
    actual_cfg: Dict[str, Any],
    benchmark_cfg: Dict[str, Any],
    plan: Dict[str, Any],
    n_sims: int = 2000,
    seed: int = 42,
    align_profile: bool = True,
) -> Dict[str, Any]:
    """Full pressure test: assessments + miss scenarios + summary flags.

    Returns a dict with:

    - ``assessments`` — ``List[TargetAssessment]``
    - ``assessments_df`` — dataframe
    - ``miss_scenarios_df`` — achievement level → EBITDA drag
    - ``horizon_months`` — from the plan
    - ``risk_flags`` — list of human-readable warnings
    """
    plan = _normalize_plan(plan)
    assessments = assess_targets(actual_cfg, benchmark_cfg, plan)
    miss_df = run_miss_scenarios(
        actual_cfg, benchmark_cfg, plan,
        n_sims=n_sims, seed=seed, align_profile=align_profile,
    )
    horizon = plan.get("horizon_months")
    flags: List[str] = []
    for a in assessments:
        if a.classification == "aspirational":
            flags.append(
                f"{a.target_key}: target {a.target_value:g} is beyond published top-decile "
                f"({a.benchmark_blended:g}) — requires best-in-class execution."
            )
        if a.median_ramp_months is not None and horizon is not None:
            if a.median_ramp_months > float(horizon):
                flags.append(
                    f"{a.target_key}: library median ramp is {a.median_ramp_months:.0f}mo but "
                    f"management plan claims {horizon}mo horizon — timeline risk."
                )
    aggressive_count = sum(1 for a in assessments if a.classification in ("aggressive", "aspirational"))
    if aggressive_count >= 2:
        flags.append(
            f"Plan asks for {aggressive_count} aggressive-or-aspirational improvements "
            f"simultaneously — execution risk compounds across concurrent initiatives."
        )
    return {
        "assessments": assessments,
        "assessments_df": assessments_to_dataframe(assessments),
        "miss_scenarios_df": miss_df,
        "horizon_months": horizon,
        "risk_flags": flags,
    }
