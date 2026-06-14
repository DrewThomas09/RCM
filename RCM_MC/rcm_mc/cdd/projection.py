"""NEW-24 Forward-projection engines: cohort-component and Fisher-Pry.

The forecasting layer (Ridge, conformal intervals, Monte Carlo, changepoint,
isolation forest) already lives in this package. Two engines from the projection
spec were missing and this module adds them:

1. Cohort-component demographic projection. The accounting identity advances
   each age cohort by its survival rate, adds births from age-specific fertility,
   and applies net migration:

       P0(t)  = births * birth survival            (youngest band)
       Pi(t)  = P(i-1, t-1) * survival(i-1)         (middle bands)
       Plast += P(last, t-1) * survival(last)       (oldest band accumulates)

   Applying age-specific utilization rates to the projected population isolates
   the pure aging-and-growth tailwind that drives most healthcare demand.

2. Fisher-Pry logistic substitution for site-of-care migration. The single-
   parameter form linearizes to a regression on the log-odds:

       ln( f / (1 - f) ) = a + b*t   <=>   f(t) = 1 / (1 + exp(-(a + b*t)))

   Fit a and b from observed share history, then project the new-setting share
   forward (inpatient to outpatient to ASC to home).

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series
from .registry import CddFeature, register

FEATURE_ID = "NEW-24"


def cohort_component_step(
    population: Sequence[float],
    survival: Sequence[float],
    fertility: Sequence[float],
    *,
    net_migration: Optional[Sequence[float]] = None,
    birth_survival: float = 1.0,
) -> List[float]:
    """Advance an age-banded population one year (Leslie-matrix recurrence).

    ``survival[i]`` for i below the last band is the fraction of band i that
    advances into band i+1; ``survival[last]`` is the fraction of the oldest band
    that remains alive in it. ``fertility[i]`` is births per member of band i.
    """
    n = len(population)
    if not (len(survival) == len(fertility) == n):
        raise ValueError("population, survival, and fertility must be the same length")
    if net_migration is not None and len(net_migration) != n:
        raise ValueError("net_migration must match the number of bands")
    for i, s in enumerate(survival):
        if not (0.0 <= s <= 1.0):
            raise ValueError(f"survival[{i}] must be in [0, 1]")

    births = sum(population[i] * fertility[i] for i in range(n))
    nxt = [0.0] * n
    nxt[0] = births * birth_survival
    for i in range(1, n):
        nxt[i] = population[i - 1] * survival[i - 1]
    # The oldest band accumulates its own survivors on top of the inflow.
    nxt[n - 1] += population[n - 1] * survival[n - 1]
    if net_migration is not None:
        nxt = [max(0.0, nxt[i] + net_migration[i]) for i in range(n)]
    return nxt


def cohort_component_projection(
    population: Sequence[float],
    survival: Sequence[float],
    fertility: Sequence[float],
    years: int,
    *,
    net_migration: Optional[Sequence[float]] = None,
    birth_survival: float = 1.0,
) -> List[List[float]]:
    """Project an age-banded population forward ``years`` years.

    Returns a list of yearly population vectors, including year 0 (the input).
    """
    if years < 0:
        raise ValueError("years must be non-negative")
    out = [list(population)]
    cur = list(population)
    for _ in range(years):
        cur = cohort_component_step(
            cur, survival, fertility,
            net_migration=net_migration, birth_survival=birth_survival,
        )
        out.append(cur)
    return out


def project_demand(
    population_by_year: Sequence[Sequence[float]],
    rate_per_capita: Sequence[float],
) -> List[float]:
    """Apply age-specific per-capita rates to each projected population vector."""
    return [
        float(sum(pop[i] * rate_per_capita[i] for i in range(len(rate_per_capita))))
        for pop in population_by_year
    ]


def _logit(f: float) -> float:
    if not (0.0 < f < 1.0):
        raise ValueError("share must be strictly between 0 and 1 to take the log-odds")
    return math.log(f / (1.0 - f))


def fisher_pry_share(a: float, b: float, t: float) -> float:
    """Logistic substitution share ``f(t) = 1/(1 + exp(-(a + b*t)))``."""
    return 1.0 / (1.0 + math.exp(-(a + b * t)))


def fit_fisher_pry(times: Sequence[float], shares: Sequence[float]) -> Tuple[float, float]:
    """Fit ``a`` and ``b`` by ordinary least squares on the log-odds.

    Requires at least two distinct time points with shares strictly in (0, 1).
    """
    if len(times) != len(shares):
        raise ValueError("times and shares must be the same length")
    if len(times) < 2:
        raise ValueError("need at least two points to fit a line")
    ys = [_logit(s) for s in shares]
    n = len(times)
    tbar = sum(times) / n
    ybar = sum(ys) / n
    denom = sum((t - tbar) ** 2 for t in times)
    if denom == 0:
        raise ValueError("time points must vary to fit a slope")
    b = sum((times[i] - tbar) * (ys[i] - ybar) for i in range(n)) / denom
    a = ybar - b * tbar
    return a, b


def fisher_pry_projection(
    times: Sequence[float],
    shares: Sequence[float],
    future_times: Sequence[float],
    *,
    source: str = "Observed site-of-care share history",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Fit and project a logistic site-of-care substitution curve.

    The exhibit reconciles the fitted curve against the observed history (the
    fit should reproduce the in-sample shares closely) and projects the new-
    setting share at each future time.
    """
    a, b = fit_fisher_pry(times, shares)

    fitted = [fisher_pry_share(a, b, t) for t in times]
    max_resid = max(abs(fitted[i] - shares[i]) for i in range(len(times)))
    projected = [(t, fisher_pry_share(a, b, t)) for t in future_times]

    flags: List[Flag] = []
    if b <= 0:
        flags.append(
            Flag(
                code="no_substitution",
                severity="info",
                message=(
                    "The fitted substitution rate is not positive, so the new "
                    "setting is not gaining share over the observed window."
                ),
            )
        )

    reconciliations = [
        Reconciliation(
            identity="fitted logistic reproduces the observed shares",
            lhs=max_resid,
            rhs=0.0,
            tolerance=0.05,
        )
    ]

    series = [
        Series(
            name="Observed share",
            kind="line",
            points=[{"label": f"t{times[i]:g}", "value": shares[i]} for i in range(len(times))],
        ),
        Series(
            name="Projected share",
            kind="line",
            points=[{"label": f"t{t:g}", "value": v} for t, v in projected],
        ),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "Substitution follows the single-parameter Fisher-Pry logistic.",
            "Parameters a and b are fit by least squares on the log-odds of share.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Site-of-care substitution projection",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"Fitted Fisher-Pry a={a:.3f}, b={b:.3f}. Projected share reaches "
            f"{projected[-1][1]*100:.1f} percent by t{projected[-1][0]:g}."
        ),
        meta={
            "a": a,
            "b": b,
            "fitted": fitted,
            "projected": projected,
            "max_residual": max_resid,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    # Outpatient-share migration over five observed years, projected three out.
    return fisher_pry_projection(
        times=[0, 1, 2, 3, 4],
        shares=[0.20, 0.28, 0.38, 0.49, 0.60],
        future_times=[5, 6, 7],
        source="Demo site-shift history",
        vintage="2026",
    )


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Forward-projection engines (cohort-component, Fisher-Pry)",
        audience="both",
        demo=_demo,
    )
)
