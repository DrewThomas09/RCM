from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from ..reports.reporting import summary_table
from ..core.simulator import simulate_compare
from .value_plan import build_target_config


def _year_avg_effect_linear_ramp(ramp_months: float, year_index_1based: int) -> float:
    """
    Average "effect" in a given year assuming a linear ramp from 0% to 100% over ramp_months.

    effect(t) = min(1, t / ramp_months)

    Returns average effect over the year window [(y-1)*12, y*12].
    """
    y = int(year_index_1based)
    if y <= 0:
        return 0.0

    M = float(ramp_months)
    if M <= 0:
        return 1.0

    a = float((y - 1) * 12)  # start month
    b = float(y * 12)        # end month

    # Entire year after ramp completion
    if a >= M:
        return 1.0

    # Entire year within ramp
    if b <= M:
        # average of t/M on [a,b]
        return float(((b * b - a * a) / (2.0 * M)) / (b - a))

    # Straddle: part ramp, part steady
    # ∫_a^M t/M dt + ∫_M^b 1 dt
    ramp_area = (M * M - a * a) / (2.0 * M)
    steady_area = (b - M)
    return float((ramp_area + steady_area) / (b - a))


def _plan_numbers(plan: Dict[str, Any]) -> Dict[str, float]:
    """Extract plan economics with safe defaults."""
    tl = plan.get("timeline", {}) if isinstance(plan.get("timeline"), dict) else {}
    costs = plan.get("costs", {}) if isinstance(plan.get("costs"), dict) else {}

    ramp_months = float(tl.get("ramp_months", 12.0))
    horizon_years = int(tl.get("horizon_years", 3))
    discount_rate = float(tl.get("discount_rate", 0.12))

    one_time = float(costs.get("one_time", 0.0))
    annual_run_rate = float(costs.get("annual_run_rate", 0.0))

    # Escrow sizing percentile (optional)
    deal = plan.get("deal", {}) if isinstance(plan.get("deal"), dict) else {}
    escrow_q = float(deal.get("escrow_percentile", 0.90))
    escrow_q = float(np.clip(escrow_q, 0.50, 0.99))

    return {
        "ramp_months": ramp_months,
        "horizon_years": horizon_years,
        "discount_rate": discount_rate,
        "one_time": one_time,
        "annual_run_rate": annual_run_rate,
        "escrow_percentile": escrow_q,
    }


def run_value_creation(
    *,
    actual_cfg: Dict[str, Any],
    benchmark_cfg: Dict[str, Any],
    plan: Dict[str, Any],
    n_sims: int,
    seed: int,
    align_profile: bool = True,
    ev_multiple: float = 8.0,
) -> Dict[str, Any]:
    """
    Run a simple PE-grade value-creation analysis:

    1) Baseline: Actual vs Benchmark (drag)
    2) Target: (Actual improved per plan) vs Benchmark (residual drag)
    3) Uplift = Baseline drag - Residual drag

    Returns a dict of outputs suitable for saving to CSV.
    """
    plan = plan or {}
    pnums = _plan_numbers(plan)

    target_cfg = build_target_config(actual_cfg, benchmark_cfg, plan)

    # Use the same seed for baseline and target compares so the Benchmark draw is identical
    # and the scenario draws share common random numbers (more stable uplift estimates).
    baseline = simulate_compare(actual_cfg, benchmark_cfg, n_sims=n_sims, seed=seed, align_profile=align_profile)
    residual = simulate_compare(target_cfg, benchmark_cfg, n_sims=n_sims, seed=seed, align_profile=align_profile)

    # Uplift distributions
    vc_sims = pd.DataFrame({
        "sim": baseline["sim"].values,
        "baseline_ebitda_drag": baseline["ebitda_drag"].values,
        "residual_ebitda_drag": residual["ebitda_drag"].values,
        "baseline_economic_drag": baseline["economic_drag"].values,
        "residual_economic_drag": residual["economic_drag"].values,
    })
    vc_sims["ebitda_uplift_gross"] = vc_sims["baseline_ebitda_drag"] - vc_sims["residual_ebitda_drag"]
    vc_sims["economic_uplift"] = vc_sims["baseline_economic_drag"] - vc_sims["residual_economic_drag"]

    # Translate economic drag into incremental A/R dollars (working capital tied up)
    wacc = float(actual_cfg.get("economics", {}).get("wacc_annual", 0.12))
    if wacc > 0:
        vc_sims["wc_release_dollars"] = vc_sims["economic_uplift"] / wacc
    else:
        vc_sims["wc_release_dollars"] = np.nan

    one_time = float(pnums["one_time"])
    annual_run_rate = float(pnums["annual_run_rate"])

    # Year-by-year ramped uplift and NPV
    horizon = int(pnums["horizon_years"])
    ramp_months = float(pnums["ramp_months"])
    discount = float(pnums["discount_rate"])

    # Steady state net uplift (run-rate)
    vc_sims["ebitda_uplift_net_steady"] = vc_sims["ebitda_uplift_gross"] - annual_run_rate
    vc_sims["ev_uplift_net_steady"] = vc_sims["ebitda_uplift_net_steady"] * float(ev_multiple)

    # Payback (years) based on steady-state net uplift
    denom = vc_sims["ebitda_uplift_net_steady"].clip(lower=1e-9)
    vc_sims["payback_years"] = one_time / denom
    vc_sims.loc[vc_sims["ebitda_uplift_net_steady"] <= 0, "payback_years"] = np.inf

    # NPV over horizon
    npv = -one_time
    for y in range(1, horizon + 1):
        eff = _year_avg_effect_linear_ramp(ramp_months, y)
        vc_sims[f"gross_uplift_y{y}"] = vc_sims["ebitda_uplift_gross"] * eff
        vc_sims[f"net_uplift_y{y}"] = vc_sims[f"gross_uplift_y{y}"] - annual_run_rate
        npv = npv + vc_sims[f"net_uplift_y{y}"] / ((1.0 + discount) ** y)
    vc_sims["npv_value_creation"] = npv

    # Summary tables
    vc_summary = summary_table(
        vc_sims,
        cols=[
            "baseline_ebitda_drag",
            "residual_ebitda_drag",
            "ebitda_uplift_gross",
            "ebitda_uplift_net_steady",
            "ev_uplift_net_steady",
            "wc_release_dollars",
            "npv_value_creation",
            "payback_years",
        ],
    )

    # Deal pack (simple, IC-friendly rows)
    escrow_q = float(pnums["escrow_percentile"])
    deal_pack = _build_deal_pack(
        baseline=baseline,
        residual=residual,
        vc_sims=vc_sims,
        ev_multiple=float(ev_multiple),
        escrow_q=escrow_q,
        wacc=wacc,
    )

    return {
        "target_cfg": target_cfg,
        "baseline": baseline,
        "residual": residual,
        "vc_sims": vc_sims,
        "vc_summary": vc_summary,
        "deal_pack": deal_pack,
    }


def _quantiles(x: np.ndarray, qs: List[float]) -> List[float]:
    x = np.asarray(x, dtype=float)
    return [float(np.quantile(x, q)) for q in qs]


def _build_deal_pack(
    *,
    baseline: pd.DataFrame,
    residual: pd.DataFrame,
    vc_sims: pd.DataFrame,
    ev_multiple: float,
    escrow_q: float,
    wacc: float,
) -> pd.DataFrame:
    """Produce a small CSV that a PE team can paste into an IC memo."""

    drag = baseline["ebitda_drag"].to_numpy(dtype=float)
    resid = residual["ebitda_drag"].to_numpy(dtype=float)
    uplift = vc_sims["ebitda_uplift_gross"].to_numpy(dtype=float)
    net_uplift = vc_sims["ebitda_uplift_net_steady"].to_numpy(dtype=float)

    qs = [0.10, 0.50, 0.90, 0.95]
    drag_q = _quantiles(drag, qs)
    resid_q = _quantiles(resid, qs)
    uplift_q = _quantiles(uplift, qs)
    net_uplift_q = _quantiles(net_uplift, qs)

    ev_drag_q = [v * ev_multiple for v in drag_q]
    ev_net_uplift_q = [v * ev_multiple for v in net_uplift_q]

    # Working capital tied up (A/R dollars) implied by economic drag
    econ_drag = baseline["economic_drag"].to_numpy(dtype=float)
    wc_drag = econ_drag / wacc if wacc > 0 else np.full_like(econ_drag, np.nan)
    wc_drag_q = _quantiles(wc_drag, qs)

    # Simple escrow sizing proxy: size to a high percentile of drag translated into EV
    escrow_ev = float(np.quantile(drag, escrow_q) * ev_multiple)

    # Probabilities (IC-friendly)
    prob_net_positive = float(np.mean(net_uplift > 0))

    # Payback probabilities (requires payback_years to be computed upstream)
    if "payback_years" in vc_sims.columns:
        payback_years = vc_sims["payback_years"].to_numpy(dtype=float)
    else:
        payback_years = np.full_like(net_uplift, np.inf, dtype=float)
    prob_payback_lt_1 = float(np.mean(np.isfinite(payback_years) & (payback_years <= 1.0)))
    prob_payback_lt_2 = float(np.mean(np.isfinite(payback_years) & (payback_years <= 2.0)))

    rows = []
    for label, vals in [
        ("EBITDA drag (Actual - Benchmark)", drag_q),
        ("Residual drag after plan (Target - Benchmark)", resid_q),
        ("Gross EBITDA uplift (Baseline - Residual)", uplift_q),
        ("Net EBITDA uplift (steady-state, after run-rate cost)", net_uplift_q),
        (f"EV at risk from drag (@{ev_multiple:.1f}x)", ev_drag_q),
        (f"EV uplift from net run-rate (@{ev_multiple:.1f}x)", ev_net_uplift_q),
        ("Working capital tied up (A/R dollars, implied)", wc_drag_q),
    ]:
        rows.append(
            {
                "metric": label,
                "p10": vals[0],
                "p50": vals[1],
                "p90": vals[2],
                "p95": vals[3],
            }
        )

    rows.append(
        {
            "metric": f"Escrow/holdback sizing proxy (P{int(escrow_q*100)} EV impact)",
            "p10": escrow_ev,
            "p50": escrow_ev,
            "p90": escrow_ev,
            "p95": escrow_ev,
        }
    )

    rows.append(
        {
            "metric": "Probability net uplift > 0 (steady-state)",
            "p10": prob_net_positive,
            "p50": prob_net_positive,
            "p90": prob_net_positive,
            "p95": prob_net_positive,
        }
    )
    rows.append(
        {
            "metric": "Probability payback <= 1 year",
            "p10": prob_payback_lt_1,
            "p50": prob_payback_lt_1,
            "p90": prob_payback_lt_1,
            "p95": prob_payback_lt_1,
        }
    )
    rows.append(
        {
            "metric": "Probability payback <= 2 years",
            "p10": prob_payback_lt_2,
            "p50": prob_payback_lt_2,
            "p90": prob_payback_lt_2,
            "p95": prob_payback_lt_2,
        }
    )

    return pd.DataFrame(rows)
