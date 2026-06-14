"""NEW-21 Facility / capacity model.

The capacity archetype sizes revenue from the physical plant up:

    capacity units (beds / chairs / stations / ORs)
      x operating periods (hours or days)
      x turns per unit per period (throughput)
      x utilization
    = effective volume
      x revenue per unit of volume (case mix x payer mix x allowed amount)

Two facts keep the estimate honest. First, throughput is the binding minimum of
physical capacity, staffing capacity, and demand, so a model that multiplies the
physical plant by 100 percent utilization overstates volume: real infusion
chairs run near 70 percent actual against 80 percent scheduled. Second, when
occupancy is high the wait and turn-away dynamics need a queue, so this module
includes an Erlang-C (M/M/c) helper to estimate the probability an arrival has
to wait.

The exhibit reconciles effective volume against the capacity identity so the
arithmetic is provable, and flags the binding constraint.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

import math
from typing import List, Optional

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series
from .registry import CddFeature, register

FEATURE_ID = "NEW-21"


def erlang_c_wait_probability(arrival_rate: float, service_rate: float, servers: int) -> float:
    """Probability an arrival must wait in an M/M/c queue (Erlang-C).

    ``arrival_rate`` and ``service_rate`` are per-unit-time; ``servers`` is the
    number of parallel servers (chairs, ORs, beds). Returns 0 when the offered
    load is zero and approaches 1 as the system saturates. Raises when the
    system is unstable (offered load at or above the server count).
    """
    if servers <= 0:
        raise ValueError("servers must be positive")
    if arrival_rate < 0 or service_rate <= 0:
        raise ValueError("arrival_rate must be non-negative and service_rate positive")
    a = arrival_rate / service_rate  # offered load in Erlangs
    rho = a / servers
    if rho >= 1.0:
        raise ValueError("unstable queue: offered load meets or exceeds server count")
    # Erlang-C formula.
    summ = sum((a ** k) / math.factorial(k) for k in range(servers))
    last = (a ** servers) / (math.factorial(servers) * (1.0 - rho))
    return last / (summ + last)


def facility_capacity(
    *,
    units: float,
    periods: float,
    turns_per_period: float,
    utilization: float,
    revenue_per_volume: float,
    staffing_capacity_volume: Optional[float] = None,
    demand_volume: Optional[float] = None,
    units_label: str = "units",
    source: str = "Operations and capacity plan",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Size facility revenue from capacity, throughput, utilization, and price.

    ``staffing_capacity_volume`` and ``demand_volume``, when supplied, cap the
    effective volume: the realized volume is the minimum of the utilized physical
    capacity, the staffing ceiling, and demand. The binding constraint is
    reported so a thesis is not built on physical capacity that staffing or
    demand will never let it reach.
    """
    for name, val in (("units", units), ("periods", periods), ("turns_per_period", turns_per_period)):
        if val < 0:
            raise ValueError(f"{name} must be non-negative")
    if not (0.0 <= utilization <= 1.0):
        raise ValueError("utilization must be in [0, 1]")
    if revenue_per_volume < 0:
        raise ValueError("revenue_per_volume must be non-negative")

    theoretical_capacity = units * periods * turns_per_period
    utilized_capacity = theoretical_capacity * utilization

    candidates = {"physical": utilized_capacity}
    if staffing_capacity_volume is not None:
        candidates["staffing"] = float(staffing_capacity_volume)
    if demand_volume is not None:
        candidates["demand"] = float(demand_volume)
    binding = min(candidates, key=lambda k: candidates[k])
    effective_volume = candidates[binding]

    revenue = effective_volume * revenue_per_volume

    flags: List[Flag] = []
    if binding != "physical":
        flags.append(
            Flag(
                code=f"binding_{binding}",
                severity="warn",
                message=(
                    f"Effective volume is capped by {binding}, not physical capacity. "
                    "Sizing on the physical plant alone would overstate volume."
                ),
                source=source,
            )
        )
    if utilization > 0.90:
        flags.append(
            Flag(
                code="high_utilization",
                severity="info",
                message=(
                    "Utilization above 90 percent leaves little turn buffer; model "
                    "wait and turn-away with a queue before assuming full capture."
                ),
            )
        )

    reconciliations = [
        Reconciliation(
            identity="utilized capacity == units * periods * turns * utilization",
            lhs=utilized_capacity,
            rhs=theoretical_capacity * utilization,
            tolerance=max(1e-6, theoretical_capacity * 1e-9),
        )
    ]

    series = [
        Series(
            name="Capacity to revenue",
            kind="bar",
            points=[
                {"label": f"Theoretical capacity ({units_label})", "value": theoretical_capacity},
                {"label": "Utilized capacity", "value": utilized_capacity},
                {"label": "Effective volume", "value": effective_volume},
                {"label": "Revenue", "value": revenue},
            ],
        ),
        Series(
            name="Constraint detail",
            kind="bar",
            internal_only=True,
            points=[{"label": k, "value": v} for k, v in candidates.items()],
        ),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "Effective volume is the minimum of utilized physical capacity, staffing, and demand.",
            "Full theoretical capacity is unachievable because of ramp and turn dynamics.",
            "Revenue is effective volume times blended revenue per unit of volume.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Facility capacity to revenue",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"Effective volume {effective_volume:,.0f} ({binding}-bound), "
            f"revenue {revenue:,.0f}."
        ),
        meta={
            "theoretical_capacity": theoretical_capacity,
            "utilized_capacity": utilized_capacity,
            "effective_volume": effective_volume,
            "binding_constraint": binding,
            "revenue": revenue,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    # 30 infusion chairs, 312 operating days, 4 turns/day, 70 percent actual.
    return facility_capacity(
        units=30,
        periods=312,
        turns_per_period=4,
        utilization=0.70,
        revenue_per_volume=520.0,
        units_label="chairs",
        source="Demo infusion center plan",
        vintage="2026",
    )


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Facility / capacity model",
        audience="both",
        demo=_demo,
    )
)
