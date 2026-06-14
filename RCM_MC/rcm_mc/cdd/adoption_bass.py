"""NEW-22 Installed-base / adoption model (Bass diffusion + ACV + NRR).

The adoption archetype sizes recurring revenue for a software or technology
product:

    addressable units (total entities x ICP-qualification rate)
      x Bass diffusion penetration over time
    = customers
      x seats per customer x price per seat   (the ACV build)
      x net revenue retention                 (expansion minus churn)
    = ARR trajectory

The Bass model splits adoption into innovation and imitation. In discrete form:

    n(t) = p*(M - N(t-1)) + q*(N(t-1)/M)*(M - N(t-1))
    N(t) = N(t-1) + n(t)

where M is the market potential, N cumulative adopters, p the coefficient of
innovation, and q the coefficient of imitation. For a novel product p and q are
borrowed from an analogue (the meta-analytic averages are p ~= 0.03, q ~= 0.38)
and refit once internal data accumulate, which is why this is the least
defensible archetype and should dominate the sensitivity analysis.

Net revenue retention compounds the installed base between new-logo additions:

    NRR = (starting ARR + expansion - contraction - churn) / starting ARR

The exhibit reconciles cumulative adopters against the market potential (the
diffusion can never exceed M) and emits the ARR path.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

import math
from typing import Dict, List

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-22"


def bass_adoption(market_potential: float, p: float, q: float, periods: int) -> Dict[str, List[float]]:
    """Discrete Bass diffusion: incremental and cumulative adopters per period.

    Returns ``{"incremental": [...], "cumulative": [...]}`` of length ``periods``.
    """
    if market_potential <= 0:
        raise ValueError("market_potential must be positive")
    if p < 0 or q < 0:
        raise ValueError("p and q must be non-negative")
    if periods < 1:
        raise ValueError("periods must be at least 1")

    incremental: List[float] = []
    cumulative: List[float] = []
    prev = 0.0
    for _ in range(periods):
        remaining = market_potential - prev
        n = p * remaining + q * (prev / market_potential) * remaining
        n = min(n, remaining)  # never overshoot the potential
        prev = prev + n
        incremental.append(n)
        cumulative.append(prev)
    return {"incremental": incremental, "cumulative": cumulative}


def bass_peak_period(p: float, q: float) -> float:
    """Continuous-time peak adoption period, ``t* = ln(q/p)/(p+q)``."""
    if p <= 0 or q <= 0:
        raise ValueError("p and q must be positive for a peak")
    return math.log(q / p) / (p + q)


def nrr(starting_arr: float, expansion: float, contraction: float, churn: float) -> float:
    """Net revenue retention from the four ARR movements."""
    return safe_div(
        starting_arr + expansion - contraction - churn, starting_arr, default=0.0
    )


def adoption_model(
    *,
    addressable_units: float,
    icp_qualification_rate: float,
    p: float,
    q: float,
    periods: int,
    seats_per_customer: float,
    price_per_seat: float,
    net_revenue_retention: float = 1.0,
    source: str = "Analogue diffusion and pricing plan",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Project an ARR trajectory from Bass adoption, the ACV build, and NRR.

    ARR compounds the existing base at NRR and adds the period's new-logo ACV:

        ARR(t) = ARR(t-1) * NRR + new_customers(t) * ACV

    The exhibit reconciles the final cumulative adopters against the market
    potential and flags the borrowed-analogue defensibility risk on p and q.
    """
    if not (0.0 <= icp_qualification_rate <= 1.0):
        raise ValueError("icp_qualification_rate must be in [0, 1]")
    if seats_per_customer < 0 or price_per_seat < 0:
        raise ValueError("seats and price must be non-negative")
    if net_revenue_retention < 0:
        raise ValueError("net_revenue_retention must be non-negative")

    market_potential = addressable_units * icp_qualification_rate
    diffusion = bass_adoption(market_potential, p, q, periods)
    acv = seats_per_customer * price_per_seat

    arr_path: List[float] = []
    arr = 0.0
    for t in range(periods):
        arr = arr * net_revenue_retention + diffusion["incremental"][t] * acv
        arr_path.append(arr)

    final_customers = diffusion["cumulative"][-1]

    flags: List[Flag] = [
        Flag(
            code="borrowed_diffusion_params",
            severity="warn",
            message=(
                "Bass p and q are borrowed from an analogue and are the least "
                "defensible inputs. Let them dominate the sensitivity analysis and "
                "refit once three or more internal data points exist."
            ),
            source=source,
        )
    ]

    # One-sided check that adopters never exceed the potential: the gap is zero
    # when final <= M and positive (failing) only on an overshoot.
    reconciliations = [
        Reconciliation(
            identity="cumulative adopters do not exceed the market potential",
            lhs=final_customers,
            rhs=min(final_customers, market_potential),
            tolerance=max(1e-6, market_potential * 1e-9),
        )
    ]

    series = [
        Series(
            name="ARR trajectory",
            kind="line",
            points=[{"label": f"t{t+1}", "value": v} for t, v in enumerate(arr_path)],
        ),
        Series(
            name="Cumulative adopters",
            kind="line",
            points=[
                {"label": f"t{t+1}", "value": v}
                for t, v in enumerate(diffusion["cumulative"])
            ],
        ),
        Series(
            name="ACV detail",
            kind="bar",
            internal_only=True,
            points=[
                {"label": "Market potential", "value": market_potential},
                {"label": "ACV per customer", "value": acv},
                {"label": "Net revenue retention", "value": net_revenue_retention},
            ],
        ),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "Market potential is addressable units times the ICP-qualification rate.",
            "Adoption follows the discrete Bass model with borrowed p and q.",
            "ARR compounds the base at NRR and adds each period's new-logo ACV.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Installed-base adoption and ARR",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"{final_customers:,.0f} of {market_potential:,.0f} potential customers "
            f"by period {periods}, ending ARR {arr_path[-1]:,.0f}."
        ),
        meta={
            "market_potential": market_potential,
            "acv": acv,
            "final_customers": final_customers,
            "arr_path": arr_path,
            "cumulative_adopters": diffusion["cumulative"],
            "ending_arr": arr_path[-1],
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    return adoption_model(
        addressable_units=5000,
        icp_qualification_rate=0.40,
        p=0.03,
        q=0.38,
        periods=10,
        seats_per_customer=8,
        price_per_seat=1200.0,
        net_revenue_retention=1.10,
        source="Demo adoption plan",
        vintage="2026",
    )


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Installed-base / adoption model (Bass diffusion)",
        audience="both",
        demo=_demo,
    )
)
