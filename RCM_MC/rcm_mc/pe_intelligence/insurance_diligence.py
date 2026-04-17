"""Insurance diligence — coverage review and claims-history risk.

Healthcare targets carry substantial insurance programs: general
liability, professional liability (malpractice), property, cyber,
D&O, and often self-insured retention for employee benefits. This
module screens:

- **Coverage adequacy** — limits relative to deal size and subsector.
- **Claims-frequency** — recent claims count and severity.
- **Retained risk** — SIR / deductible levels and funding adequacy.
- **Tail coverage** — need for a tail policy post-close for
  departing executives.

Partner-facing output: list of `InsuranceGap` items + a tail-policy
recommendation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class InsuranceInputs:
    subsector: Optional[str] = None
    ebitda_m: Optional[float] = None
    professional_liability_limit_m: Optional[float] = None
    general_liability_limit_m: Optional[float] = None
    property_limit_m: Optional[float] = None
    cyber_limit_m: Optional[float] = None
    d_and_o_limit_m: Optional[float] = None
    sir_m: Optional[float] = None                     # self-insured retention
    sir_funded_m: Optional[float] = None              # actuarial reserve
    claims_last_24mo: Optional[int] = None
    largest_open_claim_m: Optional[float] = None
    tail_policy_available: Optional[bool] = None


@dataclass
class InsuranceGap:
    area: str
    severity: str                        # "high" | "medium" | "low" | "info"
    detail: str
    remediation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "area": self.area,
            "severity": self.severity,
            "detail": self.detail,
            "remediation": self.remediation,
        }


@dataclass
class InsuranceReport:
    gaps: List[InsuranceGap] = field(default_factory=list)
    overall_score: float = 0.0                  # 0..1 (higher = more gaps)
    tail_policy_required: bool = False
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gaps": [g.to_dict() for g in self.gaps],
            "overall_score": self.overall_score,
            "tail_policy_required": self.tail_policy_required,
            "partner_note": self.partner_note,
        }


# ── Adequacy rules by subsector ────────────────────────────────────

# Minimum professional-liability limit as a multiple of EBITDA.
_PL_MIN_MULTIPLE = {
    "acute_care": 3.0,
    "asc": 1.5,
    "behavioral": 2.5,
    "post_acute": 2.5,
    "specialty": 3.0,
    "outpatient": 1.5,
    "critical_access": 2.0,
}


def _subsector_key(s: Optional[str]) -> str:
    if not s:
        return ""
    aliases = {
        "hospital": "acute_care", "acute": "acute_care",
        "snf": "post_acute", "ltach": "post_acute",
        "psych": "behavioral", "clinic": "outpatient",
        "cah": "critical_access",
    }
    return aliases.get(s.lower().strip(), s.lower().strip())


def _check_professional_liability(inputs: InsuranceInputs) -> Optional[InsuranceGap]:
    if (inputs.professional_liability_limit_m is None
            or inputs.ebitda_m is None
            or not inputs.subsector):
        return None
    key = _subsector_key(inputs.subsector)
    min_mult = _PL_MIN_MULTIPLE.get(key, 2.0)
    required = inputs.ebitda_m * min_mult
    if inputs.professional_liability_limit_m >= required:
        return InsuranceGap(
            area="professional_liability",
            severity="info",
            detail=(f"PL limit ${inputs.professional_liability_limit_m}M ≥ "
                    f"{min_mult}x EBITDA ≈ ${required}M. Adequate."),
        )
    return InsuranceGap(
        area="professional_liability",
        severity="high",
        detail=(f"PL limit ${inputs.professional_liability_limit_m}M < "
                f"required ~${required}M ({min_mult}x EBITDA) for {key}."),
        remediation="Raise PL limit before close; buyer typically pays excess premium.",
    )


def _check_cyber(inputs: InsuranceInputs) -> Optional[InsuranceGap]:
    if inputs.cyber_limit_m is None:
        return None
    # Healthcare cyber breach typical cost: ~$1-10M; limit below $5M is gap.
    if inputs.cyber_limit_m < 5:
        return InsuranceGap(
            area="cyber",
            severity="medium",
            detail=(f"Cyber limit ${inputs.cyber_limit_m}M is below the $5M "
                    "healthcare breach-event benchmark."),
            remediation="Raise to ≥$10M; add ransomware-specific coverage.",
        )
    return InsuranceGap(
        area="cyber",
        severity="info",
        detail=f"Cyber limit ${inputs.cyber_limit_m}M meets healthcare benchmark.",
    )


def _check_sir_funding(inputs: InsuranceInputs) -> Optional[InsuranceGap]:
    if inputs.sir_m is None:
        return None
    if inputs.sir_funded_m is None:
        return InsuranceGap(
            area="sir_funding",
            severity="medium",
            detail="SIR exposure declared but funded reserves not reported.",
            remediation="Require actuarial study; fund to independent estimate.",
        )
    gap = inputs.sir_m - inputs.sir_funded_m
    if gap > 0.5:
        return InsuranceGap(
            area="sir_funding",
            severity="high",
            detail=(f"SIR reserves under-funded by ~${gap:.1f}M — retained "
                    "risk not on the balance sheet at book value."),
            remediation="Fund SIR to actuarial level at close; adjust purchase price.",
        )
    return InsuranceGap(
        area="sir_funding",
        severity="info",
        detail="SIR reserves adequately funded.",
    )


def _check_claims_history(inputs: InsuranceInputs) -> Optional[InsuranceGap]:
    if inputs.claims_last_24mo is None:
        return None
    n = inputs.claims_last_24mo
    if n <= 5:
        return InsuranceGap(
            area="claims_frequency",
            severity="info",
            detail=f"{n} claim(s) in last 24 months — within peer range.",
        )
    if n <= 15:
        return InsuranceGap(
            area="claims_frequency",
            severity="medium",
            detail=(f"{n} claims in last 24 months — elevated. Review "
                    "reason-code concentration."),
            remediation="Request claim-by-claim register; identify repeat patterns.",
        )
    return InsuranceGap(
        area="claims_frequency",
        severity="high",
        detail=(f"{n} claims in last 24 months — systemic operating or "
                "quality problem."),
        remediation="Operating diagnostic required; may reflect clinical quality gap.",
    )


def _check_largest_open(inputs: InsuranceInputs) -> Optional[InsuranceGap]:
    if inputs.largest_open_claim_m is None:
        return None
    if inputs.ebitda_m is None:
        return None
    ratio = inputs.largest_open_claim_m / max(inputs.ebitda_m, 1e-9)
    if ratio < 0.10:
        return InsuranceGap(
            area="largest_open_claim",
            severity="info",
            detail=f"Largest open claim ${inputs.largest_open_claim_m}M — small vs EBITDA.",
        )
    if ratio < 0.40:
        return InsuranceGap(
            area="largest_open_claim",
            severity="medium",
            detail=(f"Largest open claim ${inputs.largest_open_claim_m}M "
                    f"({ratio*100:.0f}% of EBITDA). Watch the reserve level."),
        )
    return InsuranceGap(
        area="largest_open_claim",
        severity="high",
        detail=(f"Largest open claim ${inputs.largest_open_claim_m}M "
                f"({ratio*100:.0f}% of EBITDA). Escrow or indemnity "
                "required."),
        remediation="Hold escrow / indemnity equal to reserves + buffer.",
    )


def _tail_policy_required(inputs: InsuranceInputs) -> bool:
    # Simple heuristic: tail policy recommended on claims-made PL
    # programs whenever policy changes at close.
    return bool(inputs.tail_policy_available)


# ── Orchestrator ────────────────────────────────────────────────────

def screen_insurance(inputs: InsuranceInputs) -> InsuranceReport:
    gaps: List[InsuranceGap] = []
    for fn in (_check_professional_liability, _check_cyber,
               _check_sir_funding, _check_claims_history,
               _check_largest_open):
        g = fn(inputs)
        if g is not None:
            gaps.append(g)

    # Score: weight "high" heavily.
    weight = {"high": 1.0, "medium": 0.5, "low": 0.2, "info": 0.0}
    total_weight = sum(weight.get(g.severity, 0.0) for g in gaps)
    # Normalize to 0..1 using 4.0 as worst-realistic sum.
    score = min(1.0, total_weight / 4.0)

    tail_req = _tail_policy_required(inputs)

    high = sum(1 for g in gaps if g.severity == "high")
    medium = sum(1 for g in gaps if g.severity == "medium")
    if high == 0 and medium == 0:
        note = "Insurance program is adequate; no material gaps."
    elif high == 0:
        note = f"{medium} medium insurance gap(s) to close pre-close."
    else:
        note = (f"{high} high-severity insurance gap(s) — address with "
                "escrow / indemnity / policy purchase before close.")

    return InsuranceReport(
        gaps=gaps,
        overall_score=round(score, 4),
        tail_policy_required=tail_req,
        partner_note=note,
    )


def render_insurance_report_markdown(report: InsuranceReport) -> str:
    lines = [
        "# Insurance diligence",
        "",
        f"**Overall gap score:** {report.overall_score:.2f}  ",
        f"**Tail policy required:** "
        f"{'yes' if report.tail_policy_required else 'no'}",
        "",
        f"_{report.partner_note}_",
        "",
        "| Area | Severity | Detail | Remediation |",
        "|---|---|---|---|",
    ]
    for g in report.gaps:
        lines.append(
            f"| {g.area} | {g.severity} | {g.detail} | {g.remediation} |"
        )
    return "\n".join(lines)
