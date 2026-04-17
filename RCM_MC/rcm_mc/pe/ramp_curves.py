"""Per-lever implementation ramp curves for the v2 bridge.

``BridgeAssumptions.implementation_ramp`` is a single scalar — 1.0
means "fully ramped; book the full run-rate". That overstates Year-1
for initiatives that actually take 6-12 months to land (CDI, payer
renegotiation) and understates Year-3 on the same bridge run.

This module ships a per-lever S-curve. Each lever family carries three
knobs — ``months_to_25_pct``, ``months_to_75_pct``, ``months_to_full``
— and a logistic interpolation between them. The ramp multiplier is
clamped to ``[0.0, 1.0]`` and forced to hit ``0.0`` at month 0 and
``1.0`` at ``months_to_full``.

Why logistic and not piecewise linear: operational ramps in healthcare
are S-shaped. The first month is mostly ground-work (little effect);
months 3-6 see rapid uptake; the tail is asymptotic diminishing
returns. A linear ramp over-credits Month 1 and under-credits Month 6.

Why keep ``implementation_ramp`` scalar around: partners still want
one place to haircut the whole plan (e.g., "run this at 80% credit
because management hasn't bought in yet"). The ramp curves handle
*timing*; ``implementation_ramp`` handles *confidence*.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Mapping, Optional

from .value_bridge_v2 import LeverImpact


# ── Dataclass ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class RampCurve:
    """One S-curve parameterization.

    ``lever_family`` is the name used by the ``METRIC_TO_FAMILY``
    lookup below. The three month fields drive the logistic midpoint
    and steepness; beyond ``months_to_full`` the curve sticks at 1.0.
    """
    lever_family: str
    months_to_25_pct: int
    months_to_75_pct: int
    months_to_full: int

    def __post_init__(self) -> None:
        if not (0 < self.months_to_25_pct
                < self.months_to_75_pct
                <= self.months_to_full):
            raise ValueError(
                f"RampCurve({self.lever_family!r}) requires "
                f"0 < months_to_25_pct < months_to_75_pct <= months_to_full, "
                f"got {self.months_to_25_pct}/"
                f"{self.months_to_75_pct}/{self.months_to_full}"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lever_family": self.lever_family,
            "months_to_25_pct": int(self.months_to_25_pct),
            "months_to_75_pct": int(self.months_to_75_pct),
            "months_to_full": int(self.months_to_full),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RampCurve":
        return cls(
            lever_family=str(d.get("lever_family") or "default"),
            months_to_25_pct=int(d.get("months_to_25_pct") or 3),
            months_to_75_pct=int(d.get("months_to_75_pct") or 6),
            months_to_full=int(d.get("months_to_full") or 12),
        )


# ── Defaults ──────────────────────────────────────────────────────
#
# Tunable but partner-defensible. Any edge in the mapping below can be
# overridden through ``BridgeAssumptions.ramp_curves`` for a specific
# deal (e.g., "this hospital already has a mature denial-management
# team — ramp faster"). The rationale for each family is partner-
# visible in the ``explanation`` the v2 bridge attaches to each lever.

DEFAULT_RAMP_CURVES: Dict[str, RampCurve] = {
    # Fast uptake: denial-management tooling + workflow is well-
    # understood; vendors ship configurations in weeks.
    "denial_management":   RampCurve("denial_management",   3, 6, 12),
    # Even faster: AR/collections is mostly automation — tuning
    # dialers and statement cadences.
    "ar_collections":      RampCurve("ar_collections",      2, 4, 9),
    # Slower: CDI/coding requires clinician behavior change, which
    # requires training, chart auditing, feedback loops.
    "cdi_coding":          RampCurve("cdi_coding",          6, 12, 18),
    # Slowest: payer renegotiation is counterparty-driven; contract
    # cycles are quarterly at best and amendments run a full cycle.
    "payer_renegotiation": RampCurve("payer_renegotiation", 6, 12, 24),
    # Moderate: cost / opex optimization happens at budget cycles.
    "cost_optimization":   RampCurve("cost_optimization",   3, 6, 12),
    # Catch-all for metrics not otherwise mapped.
    "default":             RampCurve("default",             3, 6, 12),
}


# Map each bridge lever metric to a ramp family. Mirrors the v1 MC
# family map (:data:`rcm_mc.mc.ebitda_mc._METRIC_TO_FAMILY`) but
# expanded for the richer v2 lever set.
METRIC_TO_FAMILY: Dict[str, str] = {
    # Denial-family metrics
    "denial_rate":                    "denial_management",
    "initial_denial_rate":            "denial_management",
    "final_denial_rate":              "denial_management",
    "auth_denial_rate":               "denial_management",
    "eligibility_denial_rate":        "denial_management",
    "medical_necessity_denial_rate":  "denial_management",
    "timely_filing_denial_rate":      "denial_management",
    "appeals_overturn_rate":          "denial_management",
    "avoidable_denial_pct":           "denial_management",

    # CDI / coding
    "coding_denial_rate":             "cdi_coding",
    "coding_accuracy_rate":           "cdi_coding",
    "case_mix_index":                 "cdi_coding",
    "cmi":                            "cdi_coding",

    # AR / collections
    "days_in_ar":                     "ar_collections",
    "ar_over_90_pct":                 "ar_collections",
    "clean_claim_rate":               "ar_collections",
    "first_pass_resolution_rate":     "ar_collections",
    "discharged_not_final_billed_days": "ar_collections",

    # Payer renegotiation (revenue-side contractual)
    "net_collection_rate":            "payer_renegotiation",

    # Cost optimization
    "cost_to_collect":                "cost_optimization",
    "bad_debt":                       "cost_optimization",
}


def family_for_metric(metric_key: str) -> str:
    """Return the ramp-curve family for a bridge lever. Unknown metrics
    fall into the ``default`` family so the caller can still look up a
    curve without special-casing."""
    return METRIC_TO_FAMILY.get(metric_key, "default")


def curve_for_metric(
    metric_key: str,
    curves: Optional[Mapping[str, RampCurve]] = None,
) -> RampCurve:
    """Resolve ``metric_key`` → family → curve, falling back to the
    ``default`` family when no explicit curve is registered for the
    resolved family (which can happen if a caller removes a family
    from the custom map)."""
    registry = dict(curves) if curves is not None else DEFAULT_RAMP_CURVES
    fam = family_for_metric(metric_key)
    if fam in registry:
        return registry[fam]
    return registry.get("default", DEFAULT_RAMP_CURVES["default"])


# ── Ramp math ──────────────────────────────────────────────────────

def ramp_factor(curve: RampCurve, month: int) -> float:
    """Return the achievement multiplier at ``month`` under ``curve``.

    ``month = 0`` → 0.0 (implementation hasn't started).
    ``month >= months_to_full`` → 1.0 (steady state).
    Between, an S-shaped logistic interpolates and is renormalized so
    the endpoints land exactly on 0 and 1.

    Partner intuition: a 3/6/12 curve hits ~25% at Month 3, ~50% just
    after Month 4, ~75% at Month 6, and asymptotically 100% at Month
    12. The midpoint between 25% and 75% ticks is the inflection point.
    """
    if month <= 0:
        return 0.0
    if month >= curve.months_to_full:
        return 1.0

    midpoint = (curve.months_to_25_pct + curve.months_to_75_pct) / 2.0
    # Logistic steepness chosen so f(m25) = 0.25 and f(m75) = 0.75.
    # σ(k*(m25 - mid)) = 0.25 → k*(m25 - mid) = -ln(3) ≈ -1.0986.
    # Symmetric: σ(k*(m75 - mid)) = 0.75.
    span = max(1e-9, curve.months_to_75_pct - curve.months_to_25_pct)
    k = 2.0 * math.log(3.0) / span

    def _sigmoid(m: float) -> float:
        return 1.0 / (1.0 + math.exp(-k * (m - midpoint)))

    raw0 = _sigmoid(0.0)
    rawT = _sigmoid(float(curve.months_to_full))
    span_raw = max(1e-9, rawT - raw0)
    normalized = (_sigmoid(float(month)) - raw0) / span_raw
    if normalized < 0.0:
        return 0.0
    if normalized > 1.0:
        return 1.0
    return float(normalized)


def annual_ramp_factors(
    curve: RampCurve, hold_years: int,
) -> List[float]:
    """Average the monthly ramp over each 12-month window.

    Year-1 = mean(ramp_factor(1..12)), Year-2 = mean(13..24), etc.
    Using month index starting at 1 (end-of-month) keeps the zero-
    month anchor out of the Year-1 average — otherwise a fast family
    looks artificially slow because Month 0 drags the mean down.

    Returns ``hold_years`` values; caller multiplies each by the
    lever's run-rate recurring flow to get per-year EBITDA.
    """
    years = max(1, int(hold_years))
    out: List[float] = []
    for y in range(years):
        start_month = 12 * y + 1
        end_month = 12 * (y + 1)  # inclusive
        total = 0.0
        for m in range(start_month, end_month + 1):
            total += ramp_factor(curve, m)
        out.append(total / 12.0)
    return out


def apply_ramp_to_lever(
    lever_impact: LeverImpact, factor: float,
) -> LeverImpact:
    """Return a copy of ``lever_impact`` with recurring flows scaled
    by ``factor``.

    Scaled: ``recurring_revenue_uplift``, ``recurring_cost_savings``,
    ``ongoing_financing_benefit`` (all recurring by definition).
    Untouched: ``one_time_working_capital_release`` — the WC release
    happens once at implementation and doesn't ramp with steady-state
    achievement. ``recurring_ebitda_delta`` is recomputed from the
    three recurring flows so the invariant
    ``ebitda_delta = revenue + cost + financing`` continues to hold.

    Factor is clamped to ``[0, 1]``. Callers should not pass >1.0 —
    the ramp curve enforces that upstream.
    """
    f = max(0.0, min(1.0, float(factor)))
    revenue = lever_impact.recurring_revenue_uplift * f
    cost = lever_impact.recurring_cost_savings * f
    financing = lever_impact.ongoing_financing_benefit * f
    ebitda = revenue + cost + financing

    # Preserve explanation + provenance by modifying shallow copies.
    new_provenance = dict(lever_impact.provenance or {})
    new_provenance["ramp_applied"] = f"{f:.3f}"

    return replace(
        lever_impact,
        recurring_revenue_uplift=revenue,
        recurring_cost_savings=cost,
        ongoing_financing_benefit=financing,
        recurring_ebitda_delta=ebitda,
        provenance=new_provenance,
    )


def resolve_ramp_curves(
    curves: Optional[Mapping[str, Any]],
) -> Dict[str, RampCurve]:
    """Normalize a user-supplied ramp-curves map.

    Accepts either a dict of :class:`RampCurve` instances or a dict of
    dicts (the JSON-serialized form). Empty / ``None`` inputs fall
    back to :data:`DEFAULT_RAMP_CURVES`.
    """
    if not curves:
        return dict(DEFAULT_RAMP_CURVES)
    out: Dict[str, RampCurve] = dict(DEFAULT_RAMP_CURVES)
    for k, v in curves.items():
        if isinstance(v, RampCurve):
            out[str(k)] = v
        elif isinstance(v, dict):
            out[str(k)] = RampCurve.from_dict(v)
    return out
