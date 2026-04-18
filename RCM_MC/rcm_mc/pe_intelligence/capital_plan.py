"""Capital plan — post-close capex + working-capital cash requirement.

Partners need a dollars-and-timing plan for capital post-close. A
deal thesis that requires $50M of capex in year 1 has a materially
different cash profile than one that needs $10M spread across 5
years. This module structures that plan + checks it against revenue
(capex as % of revenue by subsector).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Partner-prudent capex intensity by subsector (% of revenue).
_CAPEX_INTENSITY: Dict[str, Dict[str, float]] = {
    "acute_care": {"maintenance": 0.03, "growth": 0.02, "max_total": 0.07},
    "asc": {"maintenance": 0.02, "growth": 0.03, "max_total": 0.07},
    "behavioral": {"maintenance": 0.02, "growth": 0.02, "max_total": 0.05},
    "post_acute": {"maintenance": 0.025, "growth": 0.015, "max_total": 0.05},
    "specialty": {"maintenance": 0.03, "growth": 0.025, "max_total": 0.07},
    "outpatient": {"maintenance": 0.015, "growth": 0.02, "max_total": 0.05},
    "critical_access": {"maintenance": 0.04, "growth": 0.01, "max_total": 0.06},
}


@dataclass
class CapexLine:
    purpose: str              # "maintenance" | "growth" | "it" | "regulatory"
    year: int                 # 1-indexed
    amount: float             # $
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "purpose": self.purpose,
            "year": self.year,
            "amount": self.amount,
            "note": self.note,
        }


@dataclass
class CapitalPlan:
    deal_id: str
    subsector: Optional[str] = None
    annual_revenue: Optional[float] = None
    horizon_years: int = 5
    lines: List[CapexLine] = field(default_factory=list)

    def total_by_year(self) -> Dict[int, float]:
        out: Dict[int, float] = {}
        for line in self.lines:
            out[line.year] = out.get(line.year, 0.0) + line.amount
        return out

    def total_by_purpose(self) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for line in self.lines:
            out[line.purpose] = out.get(line.purpose, 0.0) + line.amount
        return out

    def total_capex(self) -> float:
        return sum(line.amount for line in self.lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "subsector": self.subsector,
            "annual_revenue": self.annual_revenue,
            "horizon_years": self.horizon_years,
            "lines": [l.to_dict() for l in self.lines],
            "total_capex": self.total_capex(),
            "total_by_year": self.total_by_year(),
            "total_by_purpose": self.total_by_purpose(),
        }


# ── Validation ──────────────────────────────────────────────────────

@dataclass
class CapitalPlanFinding:
    check: str
    passed: bool
    detail: str
    severity: str = "info"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check": self.check,
            "passed": self.passed,
            "detail": self.detail,
            "severity": self.severity,
        }


def validate_capital_plan(plan: CapitalPlan) -> List[CapitalPlanFinding]:
    """Validate a capital plan against partner-prudent intensity bands."""
    findings: List[CapitalPlanFinding] = []
    if plan.annual_revenue is None or plan.annual_revenue <= 0:
        findings.append(CapitalPlanFinding(
            check="revenue_populated", passed=False, severity="warning",
            detail="Annual revenue not populated — cannot size intensity.",
        ))
        return findings

    total_capex = plan.total_capex()
    avg_annual = total_capex / max(plan.horizon_years, 1)
    intensity = avg_annual / plan.annual_revenue

    sub = (plan.subsector or "").lower().strip()
    band = _CAPEX_INTENSITY.get(sub)
    if band is None:
        findings.append(CapitalPlanFinding(
            check="intensity_band", passed=False, severity="warning",
            detail=f"No capex-intensity band for subsector '{sub}'.",
        ))
    else:
        if intensity > band["max_total"]:
            findings.append(CapitalPlanFinding(
                check="intensity_band", passed=False, severity="mismatch",
                detail=(f"Avg capex intensity {intensity*100:.1f}% exceeds "
                        f"partner-prudent ceiling {band['max_total']*100:.1f}% "
                        f"for {sub}."),
            ))
        else:
            findings.append(CapitalPlanFinding(
                check="intensity_band", passed=True,
                detail=(f"Capex intensity {intensity*100:.1f}% within "
                        f"{sub} band (max {band['max_total']*100:.1f}%)."),
            ))

    # Year-1 concentration check
    y1 = plan.total_by_year().get(1, 0.0)
    if plan.annual_revenue > 0 and y1 / plan.annual_revenue > 0.12:
        findings.append(CapitalPlanFinding(
            check="year1_concentration", passed=False, severity="mismatch",
            detail=(f"Year 1 capex {y1/plan.annual_revenue*100:.1f}% of "
                    "revenue — front-loaded. Challenges cash profile."),
        ))
    else:
        findings.append(CapitalPlanFinding(
            check="year1_concentration", passed=True,
            detail="Year-1 capex within reasonable concentration.",
        ))

    # Purpose-mix sanity
    by_purpose = plan.total_by_purpose()
    if total_capex > 0:
        maint_pct = by_purpose.get("maintenance", 0.0) / total_capex
        if maint_pct < 0.30:
            findings.append(CapitalPlanFinding(
                check="maintenance_mix", passed=False, severity="warning",
                detail=(f"Only {maint_pct*100:.0f}% of capex is maintenance — "
                        "growth-heavy plans defer asset reinvestment risk."),
            ))
        else:
            findings.append(CapitalPlanFinding(
                check="maintenance_mix", passed=True,
                detail=f"Maintenance is {maint_pct*100:.0f}% of capex.",
            ))

    return findings


def has_plan_mismatch(findings: List[CapitalPlanFinding]) -> bool:
    return any(f.severity == "mismatch" for f in findings)
