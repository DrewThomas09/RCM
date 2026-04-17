"""Operational KPI cascade — lever-to-EBITDA attribution.

Partners want to know: which operating KPI moves EBITDA most?
This module takes current/target KPI values and computes the $
EBITDA impact of each, then ranks them by dollar impact.

Used post-close in monthly ops reviews to keep the team focused on
the highest-leverage KPIs, and pre-close to prioritize the thesis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class KPIMovement:
    kpi: str
    unit: str                       # "bps" | "days" | "pct"
    current: float
    target: float
    delta: float
    ebitda_impact: float            # $ impact (positive = beneficial)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kpi": self.kpi,
            "unit": self.unit,
            "current": self.current,
            "target": self.target,
            "delta": self.delta,
            "ebitda_impact": self.ebitda_impact,
            "partner_note": self.partner_note,
        }


@dataclass
class KPICascadeInputs:
    annual_revenue: float
    # Current / target values (fractions unless noted otherwise).
    current_denial_rate: Optional[float] = None
    target_denial_rate: Optional[float] = None
    current_final_writeoff: Optional[float] = None
    target_final_writeoff: Optional[float] = None
    current_days_in_ar: Optional[float] = None
    target_days_in_ar: Optional[float] = None
    current_clean_claim_rate: Optional[float] = None
    target_clean_claim_rate: Optional[float] = None
    current_labor_pct_of_rev: Optional[float] = None
    target_labor_pct_of_rev: Optional[float] = None

    # Conversion factors — fraction of denial reduction that flows to
    # EBITDA (rest is recovered via appeals but with cost offset).
    denial_to_ebitda_flow: float = 0.50
    clean_claim_to_ebitda_flow: float = 0.30


def _impact_denial(inputs: KPICascadeInputs) -> Optional[KPIMovement]:
    if (inputs.current_denial_rate is None
            or inputs.target_denial_rate is None):
        return None
    delta = inputs.current_denial_rate - inputs.target_denial_rate
    # Reduced denial rate × revenue × flow factor.
    impact = inputs.annual_revenue * delta * inputs.denial_to_ebitda_flow
    note = ("Denial-rate improvement is lever #1 for most RCM theses."
            if impact > 0 else "No change modeled.")
    return KPIMovement(
        kpi="initial_denial_rate", unit="bps",
        current=inputs.current_denial_rate * 10_000,
        target=inputs.target_denial_rate * 10_000,
        delta=delta * 10_000,
        ebitda_impact=impact,
        partner_note=note,
    )


def _impact_writeoff(inputs: KPICascadeInputs) -> Optional[KPIMovement]:
    if (inputs.current_final_writeoff is None
            or inputs.target_final_writeoff is None):
        return None
    delta = inputs.current_final_writeoff - inputs.target_final_writeoff
    impact = inputs.annual_revenue * delta  # Write-off reduction flows 100% to EBITDA.
    note = ("Write-off reduction is pure margin — every bp is $ at risk today."
            if impact > 0 else "No change modeled.")
    return KPIMovement(
        kpi="final_writeoff_rate", unit="bps",
        current=inputs.current_final_writeoff * 10_000,
        target=inputs.target_final_writeoff * 10_000,
        delta=delta * 10_000,
        ebitda_impact=impact,
        partner_note=note,
    )


def _impact_ar_days(inputs: KPICascadeInputs) -> Optional[KPIMovement]:
    if (inputs.current_days_in_ar is None
            or inputs.target_days_in_ar is None):
        return None
    delta = inputs.current_days_in_ar - inputs.target_days_in_ar
    # AR days reduction = one-time cash, NOT EBITDA.
    cash_impact = inputs.annual_revenue * delta / 365.0
    note = ("AR reduction is one-time cash — flagged separately from EBITDA. "
            "Don't apply exit multiple.")
    return KPIMovement(
        kpi="days_in_ar", unit="days",
        current=inputs.current_days_in_ar,
        target=inputs.target_days_in_ar,
        delta=delta,
        ebitda_impact=cash_impact,   # reported as cash; caller treats differently
        partner_note=note,
    )


def _impact_clean_claim(inputs: KPICascadeInputs) -> Optional[KPIMovement]:
    if (inputs.current_clean_claim_rate is None
            or inputs.target_clean_claim_rate is None):
        return None
    delta = inputs.target_clean_claim_rate - inputs.current_clean_claim_rate
    # Higher clean claim rate = faster DSO + fewer reworks.
    impact = inputs.annual_revenue * delta * inputs.clean_claim_to_ebitda_flow
    note = "Clean claim rate drives rework cost reduction + faster cash."
    return KPIMovement(
        kpi="clean_claim_rate", unit="bps",
        current=inputs.current_clean_claim_rate * 10_000,
        target=inputs.target_clean_claim_rate * 10_000,
        delta=delta * 10_000,
        ebitda_impact=impact,
        partner_note=note,
    )


def _impact_labor(inputs: KPICascadeInputs) -> Optional[KPIMovement]:
    if (inputs.current_labor_pct_of_rev is None
            or inputs.target_labor_pct_of_rev is None):
        return None
    delta = inputs.current_labor_pct_of_rev - inputs.target_labor_pct_of_rev
    # Labor ratio reduction flows 100% to EBITDA.
    impact = inputs.annual_revenue * delta
    note = ("Labor-ratio reduction is a durable margin lever, "
            "but watch retention if aggressive.")
    return KPIMovement(
        kpi="labor_pct_of_revenue", unit="pct",
        current=inputs.current_labor_pct_of_rev * 100,
        target=inputs.target_labor_pct_of_rev * 100,
        delta=delta * 100,
        ebitda_impact=impact,
        partner_note=note,
    )


# ── Orchestrator ────────────────────────────────────────────────────

def build_cascade(inputs: KPICascadeInputs) -> List[KPIMovement]:
    """Build the full KPI-to-EBITDA cascade, sorted by $ impact desc."""
    movements: List[KPIMovement] = []
    for fn in (_impact_denial, _impact_writeoff, _impact_ar_days,
               _impact_clean_claim, _impact_labor):
        m = fn(inputs)
        if m is not None:
            movements.append(m)
    movements.sort(key=lambda m: -abs(m.ebitda_impact))
    return movements


def top_levers(
    cascade: List[KPIMovement],
    *,
    n: int = 3,
) -> List[KPIMovement]:
    """Return the top-N levers by $ impact."""
    return cascade[:n]


def total_ebitda_impact(cascade: List[KPIMovement]) -> float:
    """Sum EBITDA impact across the cascade (excluding AR one-time cash).

    AR days is reported in the cascade but excluded from the EBITDA
    total because it is one-time working-capital release, not
    recurring EBITDA.
    """
    return sum(m.ebitda_impact for m in cascade
               if m.kpi != "days_in_ar")
