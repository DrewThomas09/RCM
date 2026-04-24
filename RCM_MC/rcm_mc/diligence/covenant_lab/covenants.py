"""Financial-covenant definitions and per-period evaluator.

Four covenants dominate PE healthcare credit agreements:

    * **Net leverage**   Total funded debt ÷ LTM EBITDA ≤ ceiling
    * **DSCR**           LTM EBITDA ÷ Σ debt service (interest +
                         scheduled amort) ≥ floor
    * **Fixed-charge coverage**
                         (LTM EBITDA − maintenance capex) ÷
                         (Σ debt service + taxes) ≥ floor
    * **Minimum EBITDA**  LTM EBITDA ≥ floor

The evaluator consumes one quarter's LTM EBITDA + debt-service
row + ending balance and returns a ``CovenantTestResult`` per
covenant with a numeric headroom (negative = breach).

Why this module matters: Deal MC produces an EBITDA band; this
turns that band into the exact PE question — *how much headroom
do I have against the ceiling, and when does the step-down bite?*
Step-downs are modeled via ``step_down_schedule`` — a per-year
ceiling/floor path so partners can see "leverage is 6.5× with a
6.0× covenant in Y2 — no breach — but covenant steps to 5.25×
in Y3, and I'm at 5.8× → 55 bps breach".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


class CovenantKind(str, Enum):
    NET_LEVERAGE = "NET_LEVERAGE"            # ceiling
    DSCR = "DSCR"                            # floor
    FIXED_CHARGE_COVERAGE = "FIXED_CHARGE_COVERAGE"  # floor
    MIN_EBITDA = "MIN_EBITDA"                # floor
    INTEREST_COVERAGE = "INTEREST_COVERAGE"  # floor
    SENIOR_LEVERAGE = "SENIOR_LEVERAGE"      # ceiling


@dataclass(frozen=True)
class CovenantDefinition:
    """One covenant line in the credit agreement.

    ``step_down_schedule`` is a list of (year, new_threshold) pairs
    — e.g. [(1, 6.5), (2, 6.25), (3, 5.75), (4, 5.0)] on a
    NET_LEVERAGE covenant.  The active threshold at a given year is
    the step value <= year.  Missing → threshold stays at the
    opening value.

    ``cushion_pct`` is the PE-underwriter's self-imposed headroom
    target — e.g. a 15% cushion means ``true_breach`` fires only
    when the metric crosses the threshold + 15%.  The model always
    reports both actual-covenant breach and cushion-breach.
    """
    name: str
    kind: CovenantKind
    opening_threshold: float                 # 7.5 (leverage), 1.25 (DSCR)
    step_down_schedule: Tuple[Tuple[int, float], ...] = ()
    cushion_pct: float = 0.10
    test_frequency_months: int = 3           # quarterly by default
    first_test_quarter: int = 1               # Q1 Y1 tested on close
    description: str = ""

    @property
    def is_ceiling(self) -> bool:
        """Ceiling covenants breach when metric *exceeds* threshold
        (leverage); floor covenants breach when metric falls below."""
        return self.kind in (
            CovenantKind.NET_LEVERAGE,
            CovenantKind.SENIOR_LEVERAGE,
        )

    def threshold_at_year(self, year: int) -> float:
        """Step-down threshold active in ``year``."""
        active = self.opening_threshold
        for step_year, val in sorted(self.step_down_schedule):
            if year >= step_year:
                active = val
        return active

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "opening_threshold": self.opening_threshold,
            "step_down_schedule":
                [list(p) for p in self.step_down_schedule],
            "cushion_pct": self.cushion_pct,
            "test_frequency_months": self.test_frequency_months,
            "first_test_quarter": self.first_test_quarter,
            "description": self.description,
            "is_ceiling": self.is_ceiling,
        }


@dataclass
class CovenantTestResult:
    """One quarter's result of one covenant."""
    covenant_name: str
    covenant_kind: CovenantKind
    quarter_idx: int
    year: int
    metric_value: float
    threshold: float
    headroom: float                          # threshold - metric for
                                             # ceilings; metric - threshold
                                             # for floors
    headroom_pct: float
    breached: bool
    cushion_breached: bool                   # threshold × (1±cushion)
    narrative: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "covenant_name": self.covenant_name,
            "covenant_kind": self.covenant_kind.value,
            "quarter_idx": self.quarter_idx,
            "year": self.year,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "headroom": self.headroom,
            "headroom_pct": self.headroom_pct,
            "breached": self.breached,
            "cushion_breached": self.cushion_breached,
            "narrative": self.narrative,
        }


# ────────────────────────────────────────────────────────────────────
# Metric calculators
# ────────────────────────────────────────────────────────────────────

def _compute_metric(
    covenant: CovenantDefinition,
    *,
    ltm_ebitda: float,
    total_debt: float,
    senior_debt: float,
    ltm_interest: float,
    ltm_debt_service: float,
    ltm_taxes: float,
    ltm_maint_capex: float,
) -> float:
    """Route covenant kind to the right metric formula."""
    kind = covenant.kind
    if kind == CovenantKind.NET_LEVERAGE:
        return total_debt / max(ltm_ebitda, 1.0)
    if kind == CovenantKind.SENIOR_LEVERAGE:
        return senior_debt / max(ltm_ebitda, 1.0)
    if kind == CovenantKind.DSCR:
        return ltm_ebitda / max(ltm_debt_service, 1.0)
    if kind == CovenantKind.INTEREST_COVERAGE:
        return ltm_ebitda / max(ltm_interest, 1.0)
    if kind == CovenantKind.FIXED_CHARGE_COVERAGE:
        fcf = ltm_ebitda - ltm_maint_capex
        fixed = ltm_debt_service + ltm_taxes
        return fcf / max(fixed, 1.0)
    if kind == CovenantKind.MIN_EBITDA:
        return ltm_ebitda
    return 0.0


def evaluate_covenant(
    covenant: CovenantDefinition,
    quarter_idx: int,
    *,
    ltm_ebitda: float,
    total_debt: float,
    senior_debt: float,
    ltm_interest: float,
    ltm_debt_service: float,
    ltm_taxes: float = 0.0,
    ltm_maint_capex: float = 0.0,
) -> CovenantTestResult:
    """Evaluate one covenant in one quarter."""
    year = quarter_idx // 4 + 1
    threshold = covenant.threshold_at_year(year)
    metric = _compute_metric(
        covenant,
        ltm_ebitda=ltm_ebitda,
        total_debt=total_debt,
        senior_debt=senior_debt,
        ltm_interest=ltm_interest,
        ltm_debt_service=ltm_debt_service,
        ltm_taxes=ltm_taxes,
        ltm_maint_capex=ltm_maint_capex,
    )
    if covenant.is_ceiling:
        headroom = threshold - metric
        breached = metric > threshold
        cushion_threshold = threshold * (1.0 - covenant.cushion_pct)
        cushion_breached = metric > cushion_threshold
    else:
        headroom = metric - threshold
        breached = metric < threshold
        cushion_threshold = threshold * (1.0 + covenant.cushion_pct)
        cushion_breached = metric < cushion_threshold
    headroom_pct = (
        headroom / max(abs(threshold), 0.01)
        if threshold else 0.0
    )
    return CovenantTestResult(
        covenant_name=covenant.name,
        covenant_kind=covenant.kind,
        quarter_idx=quarter_idx,
        year=year,
        metric_value=metric,
        threshold=threshold,
        headroom=headroom,
        headroom_pct=headroom_pct,
        breached=breached,
        cushion_breached=cushion_breached,
    )


# ────────────────────────────────────────────────────────────────────
# Default covenant suite — the typical PE healthcare package
# ────────────────────────────────────────────────────────────────────

DEFAULT_COVENANTS: Tuple[CovenantDefinition, ...] = (
    CovenantDefinition(
        name="Net Leverage",
        kind=CovenantKind.NET_LEVERAGE,
        opening_threshold=7.5,
        step_down_schedule=(
            (2, 7.0), (3, 6.5), (4, 6.0), (5, 5.5),
        ),
        cushion_pct=0.15,
        description=(
            "Total funded debt ÷ LTM EBITDA ≤ 7.5× at close, steps "
            "down 50 bps/yr.  Primary covenant for PE healthcare "
            "LBOs — the 'running out of covenant' clock."
        ),
    ),
    CovenantDefinition(
        name="Interest Coverage",
        kind=CovenantKind.INTEREST_COVERAGE,
        opening_threshold=2.25,
        step_down_schedule=((3, 2.50), (4, 2.75)),
        cushion_pct=0.15,
        description=(
            "LTM EBITDA ÷ LTM interest expense ≥ 2.25× at close, "
            "floors tighten.  Tests ability to service floating rate "
            "in a rising-rate environment."
        ),
    ),
    CovenantDefinition(
        name="Fixed Charge Coverage",
        kind=CovenantKind.FIXED_CHARGE_COVERAGE,
        opening_threshold=1.10,
        cushion_pct=0.10,
        description=(
            "(LTM EBITDA − maintenance capex) ÷ (debt service + "
            "taxes) ≥ 1.10×.  Most aggressive — first covenant to "
            "trip in a margin compression."
        ),
    ),
)
