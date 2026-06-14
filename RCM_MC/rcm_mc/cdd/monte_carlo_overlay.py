"""NEW-11 Monte Carlo / scenario simulation overlay.

Propagates named risk-driver distributions through a revenue or EBITDA model on
top of a base forecast (the Ridge plus conformal engine supplies the base).
Outputs downside, base, and upside as P5, P50, P95 plus a tornado chart that
ranks drivers by sensitivity. A deterministic downside scenario stress-tests a
CMS rate cut.

This is simulation over a statistical model. numpy.random.default_rng(seed)
drives every draw, so two runs on the same seed are identical to 1e-9. No LLM is
ever on the path.

Supported driver distributions: normal(mean, sd), triangular(left, mode, right),
beta(a, b, scale, loc), lognormal(mean, sigma). Driver values are fractional
shocks; the default model is output = base * (1 + sum of shocks).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

import numpy as np

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series
from .registry import CddFeature, register

FEATURE_ID = "NEW-11"
DEFAULT_N_SIMS = 10000


def _draw(rng: np.random.Generator, dist: str, params: Mapping[str, float], n: int) -> np.ndarray:
    if dist == "normal":
        return rng.normal(params["mean"], params["sd"], n)
    if dist == "triangular":
        return rng.triangular(params["left"], params["mode"], params["right"], n)
    if dist == "beta":
        base = rng.beta(params["a"], params["b"], n)
        return base * params.get("scale", 1.0) + params.get("loc", 0.0)
    if dist == "lognormal":
        return rng.lognormal(params["mean"], params["sigma"], n)
    raise ValueError(f"unsupported distribution {dist!r}")


def _default_model(base: float, shocks: Mapping[str, np.ndarray]) -> np.ndarray:
    total = np.zeros_like(next(iter(shocks.values())))
    for arr in shocks.values():
        total = total + arr
    return base * (1.0 + total)


def monte_carlo_overlay(
    base: float,
    drivers: Sequence[Mapping[str, Any]],
    *,
    model_fn: Optional[Callable[[float, Mapping[str, np.ndarray]], np.ndarray]] = None,
    n_sims: int = DEFAULT_N_SIMS,
    seed: int = 42,
    stress_scenarios: Optional[Mapping[str, Mapping[str, float]]] = None,
    source: str = "Ridge plus conformal base forecast",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Run the overlay simulation and return P5/P50/P95 plus a tornado.

    ``drivers``: records of {name, dist, params}. ``stress_scenarios``: optional
    map of scenario name to {driver_name: additive shift to that driver's draws}.
    """
    if not drivers:
        raise ValueError("monte_carlo_overlay requires at least one driver")
    if n_sims < 10000:
        raise ValueError("n_sims must be at least 10000 for the overlay")

    model = model_fn or _default_model
    rng = np.random.default_rng(seed)

    # Draw drivers in a fixed order so the seed fully determines the result.
    names = [str(d["name"]) for d in drivers]
    shocks: Dict[str, np.ndarray] = {}
    for d in drivers:
        shocks[str(d["name"])] = _draw(rng, str(d["dist"]), d["params"], n_sims)

    output = np.asarray(model(base, shocks), dtype=float)
    p5, p50, p95 = (float(x) for x in np.percentile(output, [5, 50, 95]))

    # Tornado: vary each driver across its own P5..P95 with others at their mean.
    means = {k: float(np.mean(v)) for k, v in shocks.items()}
    tornado: List[Dict[str, Any]] = []
    for name in names:
        lo_shock = float(np.percentile(shocks[name], 5))
        hi_shock = float(np.percentile(shocks[name], 95))
        scen_lo = dict(means)
        scen_hi = dict(means)
        scen_lo[name] = lo_shock
        scen_hi[name] = hi_shock
        out_lo = float(model(base, {k: np.array([v]) for k, v in scen_lo.items()})[0])
        out_hi = float(model(base, {k: np.array([v]) for k, v in scen_hi.items()})[0])
        tornado.append({
            "driver": name,
            "low": out_lo,
            "high": out_hi,
            "sensitivity": abs(out_hi - out_lo),
        })
    tornado.sort(key=lambda t: t["sensitivity"], reverse=True)

    # Deterministic stress scenarios (for example a CMS rate cut).
    stresses: Dict[str, Any] = {}
    if stress_scenarios:
        for scen_name, shifts in stress_scenarios.items():
            stressed = {k: v.copy() for k, v in shocks.items()}
            for dn, shift in shifts.items():
                if dn in stressed:
                    stressed[dn] = stressed[dn] + float(shift)
            s_out = np.asarray(model(base, stressed), dtype=float)
            sp5, sp50, sp95 = (float(x) for x in np.percentile(s_out, [5, 50, 95]))
            stresses[scen_name] = {"p5": sp5, "p50": sp50, "p95": sp95}

    flags: List[Flag] = []
    if stresses:
        worst = min(stresses.items(), key=lambda kv: kv[1]["p50"])
        flags.append(Flag(
            code="downside_stress",
            severity="warn",
            message=(
                f"Under the {worst[0]} stress, median falls to {worst[1]['p50']:,.0f} "
                f"from the base median {p50:,.0f}."
            ),
            source=source,
        ))

    reconciliations = [
        Reconciliation(identity="P5 <= P50 <= P95", lhs=1.0 if p5 <= p50 <= p95 else 0.0,
                       rhs=1.0, tolerance=1e-9),
    ]

    series = [
        Series(name="Outcome distribution (P5/P50/P95)", kind="bar", points=[
            {"label": "P5 downside", "value": p5},
            {"label": "P50 base", "value": p50},
            {"label": "P95 upside", "value": p95},
        ]),
        Series(name="Driver sensitivity tornado", kind="bar", points=[
            {"label": t["driver"], "value": t["sensitivity"], "low": t["low"], "high": t["high"]}
            for t in tornado
        ]),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            f"{n_sims} simulations, numpy default_rng seed {seed}, reproducible to 1e-9.",
            "Drivers are fractional shocks; default model is base times one plus the sum of shocks.",
            "Simulation over a statistical model. No LLM is on the path.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Monte Carlo scenario overlay",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=f"P5 {p5:,.0f}, P50 {p50:,.0f}, P95 {p95:,.0f} over {n_sims} sims.",
        meta={
            "base": base,
            "n_sims": n_sims,
            "seed": seed,
            "p5": p5, "p50": p50, "p95": p95,
            "tornado": tornado,
            "stresses": stresses,
            "driver_means": means,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    drivers = [
        {"name": "cms_rate_cut", "dist": "normal", "params": {"mean": -0.05, "sd": 0.02}},
        {"name": "medicaid_attrition", "dist": "beta", "params": {"a": 2, "b": 8, "scale": -0.05, "loc": 0.0}},
        {"name": "staffing_cost", "dist": "lognormal", "params": {"mean": -3.0, "sigma": 0.4}},
    ]
    return monte_carlo_overlay(
        1000.0, drivers, seed=42,
        stress_scenarios={"CMS rate cut": {"cms_rate_cut": -0.10}},
        source="Demo base forecast", vintage="2026",
    )


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Monte Carlo / scenario simulation overlay",
        audience="both",
        demo=_demo,
    )
)
