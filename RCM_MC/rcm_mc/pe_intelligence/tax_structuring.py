"""Tax structuring — partner-prudent tax-structure checks.

PE tax structuring varies by seller / buyer / state / entity type.
This module codifies partner-level sanity checks:

- **Step-up eligibility** — partnership / S-corp sellers produce
  step-up; C-corp sellers do not (without 338(h)(10)).
- **State tax drag** — income-tax states (NY, CA, NJ) drag carry
  value; no-income-tax states (TX, FL) help.
- **F-reorg / up-C structure** — feasibility and complexity cost.
- **Section 1202 QSBS** — LP tax benefits if held > 5 yrs in a
  qualified entity.
- **Debt push-down** — typical for LBOs; limitations under 163(j).
- **GILTI / international** — cross-border exposure flags.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TaxStructureInputs:
    seller_entity_type: Optional[str] = None         # "partnership" | "s_corp" | "c_corp" | "llc"
    buyer_entity_type: Optional[str] = None          # "partnership" | "c_corp"
    state_of_primary_operation: Optional[str] = None
    ebitda_m: Optional[float] = None
    debt_at_close: Optional[float] = None
    interest_rate: Optional[float] = None            # fraction
    holding_period_years: Optional[float] = None
    is_qsbs_eligible: Optional[bool] = None
    international_exposure: Optional[bool] = None
    use_f_reorg: Optional[bool] = None


@dataclass
class TaxFinding:
    area: str
    status: str                     # "favorable" | "neutral" | "warning" | "blocker"
    detail: str
    estimated_impact: Optional[float] = None  # $ estimate

    def to_dict(self) -> Dict[str, Any]:
        return {
            "area": self.area,
            "status": self.status,
            "detail": self.detail,
            "estimated_impact": self.estimated_impact,
        }


@dataclass
class TaxStructureReport:
    findings: List[TaxFinding] = field(default_factory=list)
    step_up_available: Optional[bool] = None
    state_drag_score: float = 0.0       # 0..1 (higher = more drag)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "step_up_available": self.step_up_available,
            "state_drag_score": self.state_drag_score,
            "partner_note": self.partner_note,
        }


# ── State drag ──────────────────────────────────────────────────────

_INCOME_TAX_STATES_HIGH = {"CA", "NY", "NJ", "OR", "HI", "MN"}
_INCOME_TAX_STATES_LOW = {"TX", "FL", "TN", "NV", "WY", "SD", "AK", "WA", "NH"}


def _state_drag(state: Optional[str]) -> float:
    if not state:
        return 0.30
    s = state.upper()
    if s in _INCOME_TAX_STATES_HIGH:
        return 0.75
    if s in _INCOME_TAX_STATES_LOW:
        return 0.10
    return 0.40


# ── Findings ────────────────────────────────────────────────────────

def _step_up_finding(inputs: TaxStructureInputs) -> TaxFinding:
    seller = (inputs.seller_entity_type or "").lower()
    if seller in ("partnership", "llc", "s_corp"):
        return TaxFinding(
            area="step_up",
            status="favorable",
            detail="Pass-through seller → step-up in basis available; buyer gets amortization tax shield.",
        )
    if seller == "c_corp":
        return TaxFinding(
            area="step_up",
            status="warning",
            detail=("C-corp seller → no step-up without 338(h)(10) election. "
                    "Election requires seller cooperation and typically "
                    "triggers seller tax friction."),
        )
    return TaxFinding(
        area="step_up",
        status="neutral",
        detail="Seller entity type not specified.",
    )


def _state_drag_finding(inputs: TaxStructureInputs) -> TaxFinding:
    drag = _state_drag(inputs.state_of_primary_operation)
    if drag >= 0.70:
        return TaxFinding(
            area="state_tax",
            status="warning",
            detail=(f"{inputs.state_of_primary_operation} is a high-"
                    "income-tax state. Carry + distributions face "
                    "state tax drag of ~8-13%."),
        )
    if drag <= 0.20:
        return TaxFinding(
            area="state_tax",
            status="favorable",
            detail=(f"{inputs.state_of_primary_operation} is a no-"
                    "income-tax state. LP distributions don't face "
                    "state drag at the entity level."),
        )
    return TaxFinding(
        area="state_tax",
        status="neutral",
        detail="State has a moderate income-tax regime.",
    )


def _interest_cap_finding(inputs: TaxStructureInputs) -> Optional[TaxFinding]:
    if inputs.ebitda_m is None or inputs.debt_at_close is None:
        return None
    if inputs.interest_rate is None:
        return None
    # 163(j) limits interest deduction to 30% of adjusted taxable income.
    interest = inputs.debt_at_close * inputs.interest_rate
    ebitda_dollars = inputs.ebitda_m * 1_000_000.0
    cap = ebitda_dollars * 0.30
    if interest > cap:
        excess = interest - cap
        return TaxFinding(
            area="163j_interest_cap",
            status="warning",
            detail=(f"Interest expense ~${interest:,.0f} exceeds 30% "
                    f"163(j) cap of ${cap:,.0f}. Excess ~${excess:,.0f} "
                    "may be non-deductible in year 1."),
            estimated_impact=-excess * 0.25,  # rough 25% tax benefit lost
        )
    return TaxFinding(
        area="163j_interest_cap",
        status="favorable",
        detail=(f"Interest expense ~${interest:,.0f} within 30% 163(j) "
                f"cap of ${cap:,.0f}."),
    )


def _qsbs_finding(inputs: TaxStructureInputs) -> Optional[TaxFinding]:
    if inputs.is_qsbs_eligible is None:
        return None
    if not inputs.is_qsbs_eligible:
        return TaxFinding(
            area="qsbs",
            status="neutral",
            detail="QSBS eligibility not confirmed; rely on conventional tax planning.",
        )
    hold = inputs.holding_period_years
    if hold is not None and hold >= 5:
        return TaxFinding(
            area="qsbs",
            status="favorable",
            detail=("QSBS-eligible + 5+ year hold — LP gains up to "
                    "$10M / 10x may be federal-tax-free."),
        )
    return TaxFinding(
        area="qsbs",
        status="warning",
        detail=("QSBS-eligible but hold < 5 years expected. LPs cannot "
                "claim the exclusion without the 5-year floor."),
    )


def _international_finding(inputs: TaxStructureInputs) -> Optional[TaxFinding]:
    if inputs.international_exposure is None:
        return None
    if not inputs.international_exposure:
        return None
    return TaxFinding(
        area="international",
        status="warning",
        detail=("International exposure triggers GILTI / FDII / Subpart-F "
                "analysis. Tax counsel required before signing."),
    )


def _f_reorg_finding(inputs: TaxStructureInputs) -> Optional[TaxFinding]:
    if inputs.use_f_reorg is None:
        return None
    if not inputs.use_f_reorg:
        return None
    return TaxFinding(
        area="f_reorg",
        status="favorable",
        detail=("F-reorganization enables step-up on S-corp sellers. "
                "Adds closing complexity but captures tax value."),
    )


# ── Orchestrator ────────────────────────────────────────────────────

def analyze_tax_structure(inputs: TaxStructureInputs) -> TaxStructureReport:
    findings: List[TaxFinding] = []
    findings.append(_step_up_finding(inputs))
    findings.append(_state_drag_finding(inputs))
    for fn in (_interest_cap_finding, _qsbs_finding,
               _international_finding, _f_reorg_finding):
        f = fn(inputs)
        if f is not None:
            findings.append(f)

    # Step-up availability summary.
    seller = (inputs.seller_entity_type or "").lower()
    if seller in ("partnership", "llc", "s_corp"):
        step_up = True
    elif seller == "c_corp" and not inputs.use_f_reorg:
        step_up = False
    else:
        step_up = None

    state_drag = _state_drag(inputs.state_of_primary_operation)

    warnings = sum(1 for f in findings if f.status in ("warning", "blocker"))
    favorable = sum(1 for f in findings if f.status == "favorable")
    if warnings == 0:
        note = "Tax structure looks clean."
    elif warnings == 1:
        note = "One tax-structure item to resolve with tax counsel."
    else:
        note = (f"{warnings} tax-structure items to resolve. "
                "Engage tax counsel early.")

    return TaxStructureReport(
        findings=findings,
        step_up_available=step_up,
        state_drag_score=round(state_drag, 4),
        partner_note=note,
    )


def render_tax_structure_markdown(report: TaxStructureReport) -> str:
    lines = [
        "# Tax structure report",
        "",
        f"**Step-up available:** "
        f"{'yes' if report.step_up_available else 'no' if report.step_up_available is False else 'unknown'}  ",
        f"**State drag score:** {report.state_drag_score*100:.0f}/100",
        "",
        f"_{report.partner_note}_",
        "",
        "| Area | Status | Detail |",
        "|---|---|---|",
    ]
    for f in report.findings:
        lines.append(f"| {f.area} | {f.status} | {f.detail} |")
    return "\n".join(lines)
