"""Thesis internal-consistency validator.

A deal thesis is a bundle of claims: entry price, operating plan,
exit assumption. The partner's check is whether those claims *hang
together*. An aggressive lever plan that relies on a long hold is
inconsistent with a 3-year exit. A VBC growth thesis paired with
FFS-style margin assumptions is inconsistent on its face.

This module takes a :class:`ThesisStatement` and returns a list of
:class:`ConsistencyFinding` items flagging internal contradictions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Inputs ──────────────────────────────────────────────────────────

@dataclass
class ThesisStatement:
    """Structured thesis — what the team says the deal will do."""
    entry_multiple: Optional[float] = None
    exit_multiple: Optional[float] = None
    hold_years: Optional[float] = None
    revenue_cagr: Optional[float] = None        # fraction
    margin_expansion_bps_per_yr: Optional[float] = None
    denial_improvement_bps_per_yr: Optional[float] = None
    ar_reduction_days_per_yr: Optional[float] = None
    leverage_multiple: Optional[float] = None
    deal_structure: Optional[str] = None        # "FFS" | "capitation" | "VBC" | "hybrid"
    payer_mix: Dict[str, float] = field(default_factory=dict)
    target_irr: Optional[float] = None
    target_moic: Optional[float] = None
    has_rollup_thesis: Optional[bool] = None
    has_rcm_thesis: Optional[bool] = None
    has_turnaround_thesis: Optional[bool] = None


@dataclass
class ConsistencyFinding:
    rule: str
    severity: str                   # "low" | "medium" | "high"
    summary: str
    partner_note: str = ""
    fields_implicated: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "summary": self.summary,
            "partner_note": self.partner_note,
            "fields_implicated": list(self.fields_implicated),
        }


# ── Rules ───────────────────────────────────────────────────────────

def _r_rcm_with_short_hold(t: ThesisStatement) -> Optional[ConsistencyFinding]:
    if not t.has_rcm_thesis:
        return None
    if t.hold_years is None or t.hold_years >= 4:
        return None
    return ConsistencyFinding(
        rule="rcm_thesis_needs_4yr_hold",
        severity="medium",
        summary="RCM thesis with a sub-4-year hold",
        partner_note=("RCM programs mature in 18-24 months; a sub-4-year "
                      "hold leaves the second-stage cash for the buyer."),
        fields_implicated=["has_rcm_thesis", "hold_years"],
    )


def _r_vbc_with_ffs_growth(t: ThesisStatement) -> Optional[ConsistencyFinding]:
    structure = (t.deal_structure or "").lower()
    if structure not in ("capitation", "cap", "vbc", "value-based",
                         "value_based_care"):
        return None
    if t.revenue_cagr is None or t.revenue_cagr <= 0.04:
        return None
    return ConsistencyFinding(
        rule="vbc_with_ffs_growth",
        severity="high",
        summary="VBC / capitation structure with FFS-style revenue growth",
        partner_note=("Capitated revenue grows via lives × PMPM. "
                      "Volume × rate math doesn't apply."),
        fields_implicated=["deal_structure", "revenue_cagr"],
    )


def _r_entry_equals_exit(t: ThesisStatement) -> Optional[ConsistencyFinding]:
    if t.entry_multiple is None or t.exit_multiple is None:
        return None
    if t.exit_multiple >= t.entry_multiple + 0.25:
        return None
    if t.target_irr is None:
        return None
    # If IRR expectation is aggressive without multiple expansion, flag.
    if t.target_irr >= 0.20:
        return ConsistencyFinding(
            rule="irr_ambition_without_multiple_expansion",
            severity="medium",
            summary="Aggressive IRR with no multiple expansion assumption",
            partner_note=("Going-in and going-out multiples are ~flat. "
                          "Achieving 20%+ IRR relies entirely on EBITDA "
                          "growth — validate the operating plan."),
            fields_implicated=["entry_multiple", "exit_multiple", "target_irr"],
        )
    return None


def _r_margin_faster_than_rev(t: ThesisStatement) -> Optional[ConsistencyFinding]:
    if t.margin_expansion_bps_per_yr is None or t.revenue_cagr is None:
        return None
    if t.margin_expansion_bps_per_yr < 300:
        return None
    if t.revenue_cagr >= 0.08:
        return None
    return ConsistencyFinding(
        rule="margin_leapfrogs_revenue",
        severity="medium",
        summary="Margin expansion runs faster than revenue growth",
        partner_note=("Large margin lift with flat revenue implies either "
                      "cost takeout (limited runway) or repricing (not "
                      "durable). Distinguish between the two."),
        fields_implicated=["margin_expansion_bps_per_yr", "revenue_cagr"],
    )


def _r_leverage_vs_govt_mix(t: ThesisStatement) -> Optional[ConsistencyFinding]:
    if t.leverage_multiple is None or t.leverage_multiple <= 5.5:
        return None
    mix = t.payer_mix or {}
    norm = {k: float(v) for k, v in mix.items()}
    total = sum(norm.values())
    if total > 1.5:
        norm = {k: v / 100.0 for k, v in norm.items()}
    govt = norm.get("medicare", 0.0) + norm.get("medicaid", 0.0)
    if govt < 0.60:
        return None
    return ConsistencyFinding(
        rule="leverage_exceeds_govt_stability",
        severity="high",
        summary="Leverage is high for a government-heavy payer mix",
        partner_note=("Government-heavy reimbursement cannot sustain >5.5x "
                      "leverage through a bad rate cycle."),
        fields_implicated=["leverage_multiple", "payer_mix"],
    )


def _r_turnaround_with_rollup(t: ThesisStatement) -> Optional[ConsistencyFinding]:
    if not t.has_turnaround_thesis or not t.has_rollup_thesis:
        return None
    return ConsistencyFinding(
        rule="turnaround_plus_rollup_too_ambitious",
        severity="high",
        summary="Turnaround + roll-up thesis simultaneously",
        partner_note=("Turnarounds need CEO focus; roll-ups need integration "
                      "bandwidth. Pursuing both in one hold is a classic "
                      "dual-thesis failure pattern."),
        fields_implicated=["has_turnaround_thesis", "has_rollup_thesis"],
    )


def _r_moic_vs_irr(t: ThesisStatement) -> Optional[ConsistencyFinding]:
    if (t.target_moic is None or t.target_irr is None
            or t.hold_years is None or t.hold_years <= 0):
        return None
    implied_cagr = t.target_moic ** (1.0 / t.hold_years) - 1.0
    delta = abs(implied_cagr - t.target_irr)
    if delta <= 0.02:
        return None
    return ConsistencyFinding(
        rule="moic_irr_disagree",
        severity="low",
        summary="MOIC and IRR targets are internally inconsistent",
        partner_note=(f"{t.target_moic:.2f}x MOIC over {t.hold_years:.1f} "
                      f"years implies a {implied_cagr*100:.1f}% CAGR, vs. "
                      f"stated IRR target of {t.target_irr*100:.1f}%."),
        fields_implicated=["target_moic", "target_irr", "hold_years"],
    )


def _r_denial_improvement_without_rcm(t: ThesisStatement) -> Optional[ConsistencyFinding]:
    if t.denial_improvement_bps_per_yr is None:
        return None
    if t.denial_improvement_bps_per_yr < 200:
        return None
    if t.has_rcm_thesis:
        return None
    return ConsistencyFinding(
        rule="denial_improvement_without_rcm_thesis",
        severity="medium",
        summary="Aggressive denial improvement without an RCM thesis tag",
        partner_note=("Claiming > 200 bps/yr denial-rate improvement "
                      "without an RCM program named as a core thesis is "
                      "inconsistent — name the program or remove the lift."),
        fields_implicated=["denial_improvement_bps_per_yr", "has_rcm_thesis"],
    )


RULES = [
    _r_rcm_with_short_hold,
    _r_vbc_with_ffs_growth,
    _r_entry_equals_exit,
    _r_margin_faster_than_rev,
    _r_leverage_vs_govt_mix,
    _r_turnaround_with_rollup,
    _r_moic_vs_irr,
    _r_denial_improvement_without_rcm,
]


def validate_thesis(thesis: ThesisStatement) -> List[ConsistencyFinding]:
    """Run every consistency rule; return findings sorted by severity."""
    findings: List[ConsistencyFinding] = []
    for rule in RULES:
        try:
            hit = rule(thesis)
        except Exception:
            hit = None
        if hit is not None:
            findings.append(hit)
    order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: order.get(f.severity, 3))
    return findings
