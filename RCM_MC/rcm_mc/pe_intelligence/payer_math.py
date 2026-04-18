"""Payer-mix-aware projection math helpers.

Healthcare reimbursement is not a single rate — it's a blend of
payer-level rates that each grow (or shrink) on their own schedule.
Partners often ask, "what does EBITDA look like if Medicare grows at
0%, commercial at 3%, and Medicaid is frozen?" This module provides
the math for that question without re-running the Monte Carlo.

Core primitives:

- :func:`blended_rate_growth` — weighted rate growth given a payer
  mix and a per-payer rate-growth vector.
- :func:`project_revenue` — deterministic per-year revenue walk.
- :func:`project_ebitda_from_revenue` — apply a contribution margin
  to revenue deltas.
- :func:`compare_payer_scenarios` — roll multiple scenarios and
  produce a side-by-side.
- :func:`vbc_revenue_projection` — value-based math: lives × PMPM ×
  (1 - MLR) + shared savings.

These helpers are deliberately stateless. They don't touch the
packet or the simulator — callers stitch results into whatever view
they want.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ── Payer-mix blending ───────────────────────────────────────────────

def _normalize_mix(mix: Dict[str, float]) -> Dict[str, float]:
    if not mix:
        return {}
    low = {str(k).lower().strip(): float(v) for k, v in mix.items()
           if v is not None}
    total = sum(low.values())
    if total <= 0:
        return low
    if total > 1.5:
        return {k: v / 100.0 for k, v in low.items()}
    return low


def blended_rate_growth(
    mix: Dict[str, float],
    rate_growth_by_payer: Dict[str, float],
) -> float:
    """Return the blended annual rate growth for a payer mix.

    Payers present in ``mix`` but absent from ``rate_growth_by_payer``
    contribute a 0% rate growth. Unknown payers in
    ``rate_growth_by_payer`` are ignored.
    """
    nmix = _normalize_mix(mix)
    if not nmix:
        return 0.0
    total_share = sum(nmix.values()) or 1.0
    blend = 0.0
    for payer, share in nmix.items():
        r = float(rate_growth_by_payer.get(payer, 0.0))
        blend += (share / total_share) * r
    return blend


# ── Revenue projection ───────────────────────────────────────────────

@dataclass
class ProjectionInputs:
    base_revenue: float
    base_ebitda: float
    payer_mix: Dict[str, float] = field(default_factory=dict)
    rate_growth_by_payer: Dict[str, float] = field(default_factory=dict)
    volume_growth_pct: float = 0.0        # annual, fraction
    contribution_margin: float = 0.40     # fraction of revenue delta flowing to EBITDA
    years: int = 5


@dataclass
class YearProjection:
    year: int
    revenue: float
    rate_growth: float
    volume_growth: float
    blended_growth: float
    ebitda: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year,
            "revenue": self.revenue,
            "rate_growth": self.rate_growth,
            "volume_growth": self.volume_growth,
            "blended_growth": self.blended_growth,
            "ebitda": self.ebitda,
        }


def project_revenue(inputs: ProjectionInputs) -> List[YearProjection]:
    """Year-by-year revenue + EBITDA walk under payer-mix blending.

    Revenue grows at ``(1 + blended_rate_growth) * (1 + volume_growth)``
    each year. EBITDA deltas flow at the ``contribution_margin`` fraction.

    Mix is held constant across years. If you need mix evolution,
    call this function in a loop with updated inputs per year.
    """
    rate = blended_rate_growth(inputs.payer_mix, inputs.rate_growth_by_payer)
    blended = (1 + rate) * (1 + inputs.volume_growth_pct) - 1.0
    out: List[YearProjection] = []
    rev = inputs.base_revenue
    ebitda = inputs.base_ebitda
    for y in range(1, inputs.years + 1):
        new_rev = rev * (1 + blended)
        delta_rev = new_rev - rev
        ebitda = ebitda + inputs.contribution_margin * delta_rev
        out.append(YearProjection(
            year=y, revenue=new_rev, rate_growth=rate,
            volume_growth=inputs.volume_growth_pct,
            blended_growth=blended, ebitda=ebitda,
        ))
        rev = new_rev
    return out


def project_ebitda_from_revenue(
    base_ebitda: float,
    revenue_series: List[float],
    base_revenue: float,
    contribution_margin: float = 0.40,
) -> List[float]:
    """Project EBITDA forward from a revenue series + contribution margin.

    Useful when a caller has an external revenue projection and
    wants the flow-through to EBITDA with a simple contribution assumption.
    """
    out: List[float] = []
    rev = base_revenue
    ebitda = base_ebitda
    for new_rev in revenue_series:
        delta = new_rev - rev
        ebitda = ebitda + contribution_margin * delta
        out.append(ebitda)
        rev = new_rev
    return out


# ── Scenario comparison ──────────────────────────────────────────────

@dataclass
class PayerScenario:
    name: str
    rate_growth_by_payer: Dict[str, float]
    volume_growth_pct: float = 0.0


@dataclass
class ScenarioResult:
    name: str
    year5_revenue: float
    year5_ebitda: float
    blended_growth: float
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "year5_revenue": self.year5_revenue,
            "year5_ebitda": self.year5_ebitda,
            "blended_growth": self.blended_growth,
            "partner_note": self.partner_note,
        }


def compare_payer_scenarios(
    base_inputs: ProjectionInputs,
    scenarios: List[PayerScenario],
) -> List[ScenarioResult]:
    """Run each scenario against the same base inputs. Returns a
    per-scenario summary.
    """
    results: List[ScenarioResult] = []
    for sc in scenarios:
        inputs = ProjectionInputs(
            base_revenue=base_inputs.base_revenue,
            base_ebitda=base_inputs.base_ebitda,
            payer_mix=dict(base_inputs.payer_mix),
            rate_growth_by_payer=dict(sc.rate_growth_by_payer),
            volume_growth_pct=sc.volume_growth_pct,
            contribution_margin=base_inputs.contribution_margin,
            years=max(base_inputs.years, 5),
        )
        series = project_revenue(inputs)
        # Year 5 (or last available).
        last = series[-1]
        note = _scenario_note(sc.name, last.blended_growth)
        results.append(ScenarioResult(
            name=sc.name,
            year5_revenue=last.revenue,
            year5_ebitda=last.ebitda,
            blended_growth=last.blended_growth,
            partner_note=note,
        ))
    return results


def _scenario_note(name: str, blended: float) -> str:
    if blended < 0:
        return f"{name}: blended growth negative — deal burns EBITDA year over year."
    if blended < 0.02:
        return f"{name}: blended growth <2% — lever program has to carry everything."
    if blended < 0.04:
        return f"{name}: modest top-line growth — plan survives if levers land."
    if blended < 0.07:
        return f"{name}: healthy top-line — leverage supports equity case."
    return f"{name}: aggressive top-line assumption — question the rate inputs."


# ── Value-based (VBC) revenue math ───────────────────────────────────

@dataclass
class VBCInputs:
    lives: int
    pmpm: float                      # per member per month premium, $
    mlr: float = 0.85                # medical loss ratio
    shared_savings_rate: float = 0.0  # fraction of savings accruing to us
    savings_pool: float = 0.0        # $ shared-savings pool generated
    admin_cost_rate: float = 0.08    # admin cost as fraction of premium


@dataclass
class VBCProjection:
    premium_revenue: float
    claims_cost: float
    admin_cost: float
    underwriting_margin: float
    shared_savings_share: float
    total_vbc_ebitda: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "premium_revenue": self.premium_revenue,
            "claims_cost": self.claims_cost,
            "admin_cost": self.admin_cost,
            "underwriting_margin": self.underwriting_margin,
            "shared_savings_share": self.shared_savings_share,
            "total_vbc_ebitda": self.total_vbc_ebitda,
        }


def vbc_revenue_projection(inputs: VBCInputs) -> VBCProjection:
    """Compute VBC economics: premium, claims, admin, shared savings.

    This is lives × PMPM × 12 = premium revenue. Claims run at MLR
    of premium. Admin cost is a fraction of premium. Underwriting
    margin is premium − claims − admin. Shared savings add a separate
    accrual on top.
    """
    premium = inputs.lives * inputs.pmpm * 12
    claims = premium * inputs.mlr
    admin = premium * inputs.admin_cost_rate
    underwriting = premium - claims - admin
    savings_share = inputs.savings_pool * inputs.shared_savings_rate
    total = underwriting + savings_share
    return VBCProjection(
        premium_revenue=premium,
        claims_cost=claims,
        admin_cost=admin,
        underwriting_margin=underwriting,
        shared_savings_share=savings_share,
        total_vbc_ebitda=total,
    )


# ── Convenience: common payer-scenario library ───────────────────────

def standard_scenarios() -> List[PayerScenario]:
    """Three common partner scenarios: base, CMS cut, commercial rate
    boom. Meant as a starting point; callers should tailor per deal.
    """
    return [
        PayerScenario(
            name="Base",
            rate_growth_by_payer={"medicare": 0.02, "medicaid": 0.00, "commercial": 0.03},
            volume_growth_pct=0.015,
        ),
        PayerScenario(
            name="CMS cut",
            rate_growth_by_payer={"medicare": -0.015, "medicaid": -0.005, "commercial": 0.03},
            volume_growth_pct=0.015,
        ),
        PayerScenario(
            name="Commercial rate boom",
            rate_growth_by_payer={"medicare": 0.02, "medicaid": 0.00, "commercial": 0.055},
            volume_growth_pct=0.015,
        ),
        PayerScenario(
            name="Frozen rates (recession)",
            rate_growth_by_payer={"medicare": 0.00, "medicaid": -0.02, "commercial": 0.00},
            volume_growth_pct=-0.02,
        ),
    ]
