"""Reverse challenge solver — "what assumptions would hit $X EBITDA drag?"

IC partner pushback pattern: "I don't believe the $17M drag. Show me why it
isn't $5M." Or: "What if management hits the plan? Where does the number
land?" The analyst needs to rapidly reverse-engineer what single or joint
change in target assumptions would move the modeled drag to a given value.

This module performs a **bisection** on the actual→benchmark progress factor
that the pressure-test module already uses. Given a target drag, we binary
search for the achievement (0 = status quo, 1 = full benchmark performance)
that lands the Monte Carlo mean drag within tolerance of the target.

Three kinds of answers:

- **Global:** fraction of the gap to benchmark that all three KPIs (IDR /
  FWR / A/R days) would have to close *simultaneously*.
- **Per-lever:** if *only* IDR changes (FWR/DAR held at current), how far
  must it move? Same for FWR alone, DAR alone. Surfaces which lever matters
  most — if IDR alone reaching benchmark wouldn't get there, the target is
  more ambitious than a pure denials story.
- **Target values:** translates each lever's progress fraction back into an
  absolute blended KPI value ("IDR would need to be 8.5% vs current 13.5%").
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from ..data.intake import _blended_mean
from .pressure_test import _TARGET_METRICS, _build_scenario_cfg
from ..core.simulator import simulate_compare


# ── Data classes ────────────────────────────────────────────────────────────

@dataclass
class ChallengeResult:
    target_drag: float
    current_drag: float
    # Progress fraction for the joint move (all three KPIs). None if the
    # target is already satisfied at status quo; 1.0 if it's unreachable even
    # with all three at benchmark.
    global_progress_needed: Optional[float]
    # Per-lever progress fraction with the same None/1.0 semantics.
    per_kpi_progress: Dict[str, Optional[float]]
    # For each KPI: {"current": blended_actual, "benchmark": blended_bench,
    # "target_required": blended_value_implied_by_progress_fraction}
    blended_values: Dict[str, Dict[str, Optional[float]]]


# ── Inner simulation helper ────────────────────────────────────────────────

def _require_finite_number(value: Any, *, label: str) -> float:
    """Reject NaN / inf challenge inputs before they trigger fake solves."""
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric, got bool")
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be numeric, got {value!r}") from None
    if not math.isfinite(out):
        raise ValueError(f"{label} must be finite, got {value!r}")
    return out


def _validate_solver_params(*, n_sims: int, tol_pct: float = 0.02,
                            max_iter: int = 10) -> None:
    """Keep the reverse-solver contract explicit and fail-fast."""
    if int(n_sims) <= 0:
        raise ValueError(f"n_sims must be > 0, got {n_sims!r}")
    tol = _require_finite_number(tol_pct, label="tol_pct")
    if tol <= 0.0 or tol >= 1.0:
        raise ValueError(f"tol_pct must be between 0 and 1, got {tol_pct!r}")
    if int(max_iter) <= 0:
        raise ValueError(f"max_iter must be > 0, got {max_iter!r}")

def _drag_at_achievement(
    actual_cfg: Dict[str, Any],
    bench_cfg: Dict[str, Any],
    achievement: float,
    kpi_keys: List[str],
    n_sims: int,
    seed: int,
) -> float:
    """Simulate with ``kpi_keys`` advanced by ``achievement`` toward benchmark.

    ``achievement=0.0`` → actual config unchanged; ``1.0`` → those KPIs at
    benchmark blended value. Other KPIs stay at their actual values.
    """
    plan_targets: Dict[str, float] = {}
    for k in kpi_keys:
        path = _TARGET_METRICS[k]
        bench_blended = _blended_mean(bench_cfg, path)
        if bench_blended is None:
            continue
        plan_targets[k] = float(bench_blended)
    cfg = _build_scenario_cfg(actual_cfg, plan_targets, achievement=float(achievement))
    df = simulate_compare(cfg, bench_cfg, n_sims=n_sims, seed=seed, align_profile=True)
    return float(df["ebitda_drag"].mean())


# ── Binary search ──────────────────────────────────────────────────────────

def _binary_search_progress(
    target: float,
    evaluate_fn: Callable[[float], float],
    tol_pct: float = 0.02,
    max_iter: int = 10,
) -> Optional[float]:
    """Find ``a ∈ [0, 1]`` s.t. ``evaluate_fn(a) ≈ target``.

    ``evaluate_fn`` is monotone-decreasing (more progress → less drag).
    Returns ``None`` if target ≥ status-quo drag (no progress needed), or
    ``1.0`` if even full benchmark progress can't reach the target.
    """
    target = _require_finite_number(target, label="target")
    _validate_solver_params(n_sims=1, tol_pct=tol_pct, max_iter=max_iter)
    low, high = 0.0, 1.0
    drag_low = evaluate_fn(low)    # worst case (status quo)
    drag_high = evaluate_fn(high)  # best case (full benchmark)

    # Target already at or above status-quo drag → no progress needed
    if target >= drag_low * (1 - tol_pct):
        return None
    # Target below even full-benchmark drag → unreachable with this lever set
    if target <= drag_high * (1 + tol_pct):
        return 1.0

    tol = abs(target) * tol_pct
    for _ in range(max_iter):
        mid = (low + high) / 2
        drag_mid = evaluate_fn(mid)
        if abs(drag_mid - target) <= tol:
            return mid
        if drag_mid > target:
            low = mid
        else:
            high = mid
    return (low + high) / 2


# ── Public solvers ─────────────────────────────────────────────────────────

def solve_global_progress(
    actual_cfg: Dict[str, Any],
    bench_cfg: Dict[str, Any],
    target_drag: float,
    n_sims: int = 1000,
    seed: int = 42,
) -> Optional[float]:
    """Joint-lever bisection: IDR + FWR + DAR all move together."""
    _require_finite_number(target_drag, label="target_drag")
    _validate_solver_params(n_sims=n_sims)
    keys = ["idr_blended", "fwr_blended", "dar_blended"]

    def eval_at(a: float) -> float:
        return _drag_at_achievement(actual_cfg, bench_cfg, a, keys, n_sims, seed)

    return _binary_search_progress(target_drag, eval_at)


def solve_per_kpi_progress(
    actual_cfg: Dict[str, Any],
    bench_cfg: Dict[str, Any],
    target_drag: float,
    n_sims: int = 1000,
    seed: int = 42,
) -> Dict[str, Optional[float]]:
    """Per-lever bisection: each KPI solved independently with others held at actual."""
    _require_finite_number(target_drag, label="target_drag")
    _validate_solver_params(n_sims=n_sims)
    out: Dict[str, Optional[float]] = {}
    for kpi in ("idr_blended", "fwr_blended", "dar_blended"):
        def eval_at(a: float, _k: str = kpi) -> float:
            return _drag_at_achievement(actual_cfg, bench_cfg, a, [_k], n_sims, seed)
        out[kpi] = _binary_search_progress(target_drag, eval_at)
    return out


def run_challenge(
    actual_cfg: Dict[str, Any],
    bench_cfg: Dict[str, Any],
    target_drag: float,
    n_sims: int = 1000,
    seed: int = 42,
) -> ChallengeResult:
    """Full challenge: global + per-lever + blended-value translation."""
    target_drag = _require_finite_number(target_drag, label="target_drag")
    _validate_solver_params(n_sims=n_sims)
    current = _drag_at_achievement(
        actual_cfg, bench_cfg, 0.0, ["idr_blended"], n_sims, seed,
    )
    global_pct = solve_global_progress(actual_cfg, bench_cfg, target_drag, n_sims, seed)
    per_kpi = solve_per_kpi_progress(actual_cfg, bench_cfg, target_drag, n_sims, seed)

    blended: Dict[str, Dict[str, Optional[float]]] = {}
    for kpi in ("idr_blended", "fwr_blended", "dar_blended"):
        path = _TARGET_METRICS[kpi]
        cur_b = _blended_mean(actual_cfg, path)
        bench_b = _blended_mean(bench_cfg, path)
        progress = per_kpi.get(kpi)
        target_b: Optional[float]
        if progress is None or cur_b is None or bench_b is None:
            target_b = None
        elif progress >= 1.0:
            target_b = bench_b  # at full-benchmark (even if that still misses the target)
        else:
            target_b = cur_b - float(progress) * (cur_b - bench_b)
        blended[kpi] = {"current": cur_b, "benchmark": bench_b, "target_required": target_b}

    return ChallengeResult(
        target_drag=float(target_drag),
        current_drag=current,
        global_progress_needed=global_pct,
        per_kpi_progress=per_kpi,
        blended_values=blended,
    )


# ── Output formatting ──────────────────────────────────────────────────────

def challenge_to_dataframe(result: ChallengeResult) -> pd.DataFrame:
    """One row per lever — joint move first, then per-lever alone."""
    def _fmt_progress(p: Optional[float]) -> str:
        if p is None:
            return "not needed (target ≥ current drag)"
        if p >= 0.999:
            return "≥100% — unreachable with this lever alone"
        return f"{p * 100:.0f}% of gap to benchmark"

    rows: List[Dict[str, Any]] = []
    rows.append({
        "lever":                 "joint (IDR + FWR + DAR)",
        "current_value":         "—",
        "target_value_required": "—",
        "benchmark_value":       "—",
        "progress_needed":       _fmt_progress(result.global_progress_needed),
    })
    labels = {
        "idr_blended": "IDR alone",
        "fwr_blended": "FWR alone",
        "dar_blended": "A/R days alone",
    }
    for kpi, label in labels.items():
        bd = result.blended_values.get(kpi, {})
        progress = result.per_kpi_progress.get(kpi)

        def _fmt_val(v: Any) -> str:
            if v is None:
                return "—"
            try:
                f = float(v)
            except (TypeError, ValueError):
                return "—"
            return f"{f:.3f}" if f < 1.0 else f"{f:.1f}"

        rows.append({
            "lever":                 label,
            "current_value":         _fmt_val(bd.get("current")),
            "target_value_required": _fmt_val(bd.get("target_required")),
            "benchmark_value":       _fmt_val(bd.get("benchmark")),
            "progress_needed":       _fmt_progress(progress),
        })
    return pd.DataFrame(rows)


# ── CLI ─────────────────────────────────────────────────────────────────────

def main(argv: Optional[List[str]] = None, prog: str = "rcm-mc challenge") -> int:
    ap = argparse.ArgumentParser(
        prog=prog,
        description=(
            "Reverse challenge solver: given a target EBITDA drag, solve for the "
            "assumption changes that would get there — both joint (all three KPIs "
            "together) and per-lever (each KPI alone)."
        ),
        epilog=(
            "Example:\n"
            "  rcm-mc challenge --actual actual.yaml --benchmark configs/benchmark.yaml \\\n"
            "                   --target-drag 10000000 --outdir outputs\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--actual", required=True, help="Actual config YAML")
    ap.add_argument("--benchmark", required=True, help="Benchmark config YAML")
    ap.add_argument(
        "--target-drag", type=float, required=True,
        help="Target EBITDA drag (dollars, e.g. 10000000)",
    )
    ap.add_argument("--outdir", default=None, help="Write challenge_analysis.csv here")
    ap.add_argument("--n-sims", type=int, default=1000, help="Sims per bisection step (default 1000)")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed (default 42)")
    args = ap.parse_args(argv)

    from ..infra.config import load_and_validate
    from ..infra._terminal import banner, info, success, warn

    try:
        actual = load_and_validate(args.actual)
        bench = load_and_validate(args.benchmark)
    except (FileNotFoundError, ValueError) as exc:
        sys.stderr.write(f"challenge failed: {exc}\n")
        return 1

    print(banner(f"Challenge solver — target ${args.target_drag:,.0f} EBITDA drag"))

    try:
        result = run_challenge(
            actual, bench, args.target_drag, n_sims=args.n_sims, seed=args.seed,
        )
    except ValueError as exc:
        sys.stderr.write(f"challenge failed: {exc}\n")
        return 1
    df = challenge_to_dataframe(result)

    print(info(f"Current drag (status quo):  ${result.current_drag:,.0f}"))
    print(info(f"Target drag:                ${result.target_drag:,.0f}"))
    if result.current_drag > 0:
        gap_pct = (result.current_drag - result.target_drag) / result.current_drag * 100
        print(info(f"Gap to close:               {gap_pct:.0f}% reduction in modeled drag"))
    print()
    # Pretty-print the dataframe aligned
    for _, row in df.iterrows():
        lever = str(row["lever"]).ljust(25)
        prog = str(row["progress_needed"])
        if "unreachable" in prog:
            print(warn(f"{lever}  {prog}"))
        elif "not needed" in prog:
            print(info(f"{lever}  {prog}"))
        else:
            print(info(f"{lever}  {prog}"))
            if row["current_value"] != "—":
                print(info(
                    f"{' ' * 25}  current {row['current_value']}  "
                    f"→  target {row['target_value_required']}  "
                    f"(benchmark {row['benchmark_value']})"
                ))

    if args.outdir:
        os.makedirs(args.outdir, exist_ok=True)
        out_path = os.path.join(args.outdir, "challenge_analysis.csv")
        df.to_csv(out_path, index=False)
        print()
        print(success(f"wrote {out_path}"))

    return 0


if __name__ == "__main__":
    sys.exit(main())
