"""NEW-19 Epidemiology patient-flow funnel with monthly cohort mechanics.

The patient-flow archetype sizes a disease market from the population down:

    population
      x prevalence            -> prevalent pool
      x diagnosis rate        -> diagnosed
      x treatment rate        -> treated / on therapy
      x price per patient-month

The defensible difference from a flat "pool times price" estimate is the
persistence layer. Real adherence decays, so the number of patients actually on
therapy at month t is the sum over every initiation cohort of the survivors:

    N(t) = sum over c<=t of Init(c) * S(t - c)

where ``S(tau)`` is the persistence (survival) function tau months after
initiation. A constant monthly discontinuation hazard gives the exponential
form ``S(tau) = exp(-lambda*tau)``; a non-constant hazard (early drop-off then
stabilization) gives the Weibull form ``S(tau) = exp(-(tau/eta)^beta)``.

Incidence and prevalence tie together at steady state through the mean
treatment duration D-bar = sum of S(tau): ``prevalence ~= incidence * D-bar``.
This module exposes both the raw cohort mechanics and the funnel that uses them,
and it reconciles the funnel's steady-state treated pool against a simulated
cohort build so the two views are proven consistent.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional, Sequence

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-19"

# A persistence (survival) function maps a month-offset tau (>=0) to a survival
# fraction in [0, 1]. S(0) == 1 by construction.
SurvivalFn = Callable[[int], float]


def persistence_to_hazard(persistence_12: float) -> float:
    """Convert a 12-month persistence fraction to a monthly discontinuation hazard.

    From ``S(12) = exp(-lambda*12)`` we get ``lambda = -ln(persistence_12)/12``.
    A 78.28 percent 12-month persistence implies lambda ~= 0.0204 per month.
    """
    if not (0.0 < persistence_12 <= 1.0):
        raise ValueError("persistence_12 must be in (0, 1]")
    return -math.log(persistence_12) / 12.0


def exponential_survival(lam: float) -> SurvivalFn:
    """Constant-hazard persistence: ``S(tau) = exp(-lambda*tau)``."""
    if lam < 0:
        raise ValueError("hazard lambda must be non-negative")
    return lambda tau: math.exp(-lam * max(0, tau))


def weibull_survival(eta: float, beta: float) -> SurvivalFn:
    """Weibull persistence: ``S(tau) = exp(-(tau/eta)^beta)``.

    ``beta < 1`` gives a decreasing hazard (early drop-off then stabilization),
    the usual shape of real adherence curves. ``beta == 1`` reduces to the
    exponential with ``lambda = 1/eta``.
    """
    if eta <= 0 or beta <= 0:
        raise ValueError("Weibull eta and beta must be positive")
    return lambda tau: math.exp(-((max(0, tau) / eta) ** beta))


def mean_persistence_months(survival: SurvivalFn, horizon: int = 600) -> float:
    """Mean months on therapy, ``D-bar = sum over tau>=0 of S(tau)``.

    This is the discrete mean treatment duration that links incidence and
    prevalence (``prevalence ~= incidence * D-bar``). The horizon defaults to
    50 years of months, long enough for any clinical decay to converge.
    """
    return float(sum(survival(tau) for tau in range(horizon)))


def simulate_cohorts(
    initiations: Sequence[float],
    survival: SurvivalFn,
) -> List[float]:
    """On-therapy patients per month, ``N(t) = sum over c<=t of Init(c)*S(t-c)``.

    ``initiations[c]`` is the number of patients starting therapy in month c.
    Returns the on-therapy count for each month over the same horizon.
    """
    n = len(initiations)
    out: List[float] = []
    for t in range(n):
        total = 0.0
        for c in range(t + 1):
            total += float(initiations[c]) * survival(t - c)
        out.append(total)
    return out


def line_of_therapy_occupancy(
    lines: Sequence[Dict[str, float]],
    *,
    line1_initiations_per_month: float,
    horizon_months: int,
) -> List[float]:
    """Steady-state occupancy per line of therapy via a monthly Markov chain.

    Each line carries ``progress`` (monthly probability of advancing to the next
    line) and ``discontinue`` (monthly probability of leaving therapy). Patients
    enter line 1 at ``line1_initiations_per_month``; the remainder per line per
    month stay. Returns the occupancy of each line at the final month.
    """
    k = len(lines)
    if k == 0:
        raise ValueError("at least one line of therapy is required")
    occ = [0.0] * k
    for _ in range(horizon_months):
        nxt = [0.0] * k
        # New starts enter line 1.
        nxt[0] += line1_initiations_per_month
        for i, line in enumerate(lines):
            g = float(line.get("progress", 0.0))
            d = float(line.get("discontinue", 0.0))
            if g + d > 1.0 + 1e-9:
                raise ValueError(f"line {i}: progress + discontinue exceeds 1")
            stay = occ[i] * (1.0 - g - d)
            nxt[i] += stay
            if i + 1 < k:
                nxt[i + 1] += occ[i] * g
            # progression out of the last line is treated as discontinuation
        occ = nxt
    return occ


def patient_flow_funnel(
    *,
    population: float,
    prevalence_rate: float,
    diagnosis_rate: float,
    treatment_rate: float,
    price_per_patient_month: float,
    persistence_12: Optional[float] = None,
    survival: Optional[SurvivalFn] = None,
    line_of_therapy_share: float = 1.0,
    source: str = "Disease epidemiology build",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Size a disease market from population through persistence to revenue.

    The treated pool is the steady-state prevalent count on therapy. Persistence
    enters through the mean treatment duration: holding that pool steady requires
    a monthly initiation of ``treated_pool / D-bar`` (the incidence-prevalence
    identity). A cohort simulation at that initiation rate reconciles back to the
    treated pool, proving the funnel and the cohort mechanics agree.

    Provide persistence either as ``persistence_12`` (converted to an
    exponential hazard) or directly as a ``survival`` function (e.g. Weibull).
    """
    for name, val in (
        ("prevalence_rate", prevalence_rate),
        ("diagnosis_rate", diagnosis_rate),
        ("treatment_rate", treatment_rate),
        ("line_of_therapy_share", line_of_therapy_share),
    ):
        if not (0.0 <= val <= 1.0):
            raise ValueError(f"{name} must be in [0, 1], got {val}")
    if population < 0 or price_per_patient_month < 0:
        raise ValueError("population and price must be non-negative")
    if survival is None:
        if persistence_12 is None:
            raise ValueError("provide persistence_12 or a survival function")
        survival = exponential_survival(persistence_to_hazard(persistence_12))

    prevalent_pool = population * prevalence_rate
    diagnosed = prevalent_pool * diagnosis_rate
    treated_pool = diagnosed * treatment_rate * line_of_therapy_share

    d_bar = mean_persistence_months(survival)
    monthly_initiation = safe_div(treated_pool, d_bar, default=0.0)

    # Annual revenue from the steady-state prevalent treated pool.
    annual_patient_months = treated_pool * 12.0
    annual_revenue = annual_patient_months * price_per_patient_month

    # Reconciliation: a long cohort build at the implied initiation converges to
    # the treated pool. Run a horizon several times the mean duration.
    horizon = max(60, int(d_bar * 6) + 1)
    converged = simulate_cohorts([monthly_initiation] * horizon, survival)[-1]

    flags: List[Flag] = []
    if treatment_rate * diagnosis_rate < 0.10:
        flags.append(
            Flag(
                code="thin_funnel",
                severity="warn",
                message=(
                    "The diagnosis-times-treatment conversion is below 10 percent, "
                    "so most of the prevalent pool never reaches therapy. Confirm "
                    "the access and initiation rates before sizing on this funnel."
                ),
                source=source,
            )
        )

    reconciliations = [
        Reconciliation(
            identity="steady-state cohort build converges to the treated pool",
            lhs=converged,
            rhs=treated_pool,
            tolerance=max(1.0, treated_pool * 0.01),
        )
    ]

    funnel_points = [
        {"label": "Population", "value": population},
        {"label": "Prevalent pool", "value": prevalent_pool},
        {"label": "Diagnosed", "value": diagnosed},
        {"label": "Treated / on therapy", "value": treated_pool},
    ]
    series = [
        Series(name="Patient-flow funnel", kind="bar", points=funnel_points),
        Series(
            name="Persistence and initiation",
            kind="bar",
            internal_only=True,
            points=[
                {"label": "Mean months on therapy", "value": d_bar},
                {"label": "Monthly initiation to hold pool", "value": monthly_initiation},
            ],
        ),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "Treated pool is the steady-state prevalent count on therapy.",
            "Persistence decays per the survival function; mean duration links incidence and prevalence.",
            "Revenue is annual patient-months times price per patient-month.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Epidemiology patient-flow funnel",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"Treated pool {treated_pool:,.0f} patients, mean {d_bar:,.1f} months "
            f"on therapy, annual revenue {annual_revenue:,.0f}."
        ),
        meta={
            "prevalent_pool": prevalent_pool,
            "diagnosed": diagnosed,
            "treated_pool": treated_pool,
            "mean_persistence_months": d_bar,
            "monthly_initiation": monthly_initiation,
            "annual_patient_months": annual_patient_months,
            "annual_revenue": annual_revenue,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    # Illustrative chronic-therapy market on the diabetes funnel scale.
    return patient_flow_funnel(
        population=258_000_000,
        prevalence_rate=0.147,
        diagnosis_rate=0.772,
        treatment_rate=0.60,
        price_per_patient_month=45.0,
        persistence_12=0.7828,
        source="Demo epidemiology build",
        vintage="2026",
    )


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Epidemiology patient-flow funnel",
        audience="both",
        demo=_demo,
    )
)
