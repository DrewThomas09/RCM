"""Payer mix risk — deeper analysis of payer-mix concentration.

`reasonableness.py` categorizes payer mixes into regimes. This
module is a finer-grained risk analysis:

- Calculates payer-mix HHI specifically.
- Flags pools where Medicare-Advantage is a large share (as it
  behaves differently from FFS Medicare).
- Flags Medicaid-Managed-Care vs fee-for-service Medicaid share.
- Evaluates payer-mix stability by looking at recent trend.
- Surfaces specific exposures (e.g., >20% exchange / ACA-plan share).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PayerMixRiskInputs:
    payer_mix: Dict[str, float] = field(default_factory=dict)
    medicare_advantage_share: Optional[float] = None     # fraction of total
    medicaid_managed_care_share: Optional[float] = None
    aca_exchange_share: Optional[float] = None
    mix_trend_3yr: Optional[Dict[str, float]] = None     # per-payer yoy


@dataclass
class PayerRisk:
    category: str
    severity: str                   # "low" | "medium" | "high"
    detail: str
    remediation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "detail": self.detail,
            "remediation": self.remediation,
        }


@dataclass
class PayerMixRiskReport:
    payer_hhi: float
    risks: List[PayerRisk] = field(default_factory=list)
    top_payer: str = ""
    top_payer_share: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "payer_hhi": self.payer_hhi,
            "risks": [r.to_dict() for r in self.risks],
            "top_payer": self.top_payer,
            "top_payer_share": self.top_payer_share,
            "partner_note": self.partner_note,
        }


def _normalize_mix(mix: Dict[str, float]) -> Dict[str, float]:
    if not mix:
        return {}
    norm = {str(k).lower(): float(v) for k, v in mix.items()
            if v is not None}
    total = sum(norm.values())
    if total <= 0:
        return norm
    if total > 1.5:
        norm = {k: v / 100.0 for k, v in norm.items()}
    return norm


def _payer_hhi(norm: Dict[str, float]) -> float:
    # 0..10000 scale.
    return sum((s * 100.0) ** 2 for s in norm.values())


def analyze_payer_mix_risk(
    inputs: PayerMixRiskInputs,
) -> PayerMixRiskReport:
    norm = _normalize_mix(inputs.payer_mix)
    hhi = _payer_hhi(norm)
    risks: List[PayerRisk] = []

    top = ("", 0.0)
    if norm:
        top = max(norm.items(), key=lambda kv: kv[1])

    # HHI flag
    if hhi >= 4500:
        risks.append(PayerRisk(
            category="payer_hhi",
            severity="high",
            detail=f"Payer HHI {hhi:.0f} — very concentrated.",
            remediation="Diversify payer book; price in concentration risk.",
        ))
    elif hhi >= 3000:
        risks.append(PayerRisk(
            category="payer_hhi",
            severity="medium",
            detail=f"Payer HHI {hhi:.0f} — moderately concentrated.",
            remediation="Monitor top-payer contracts closely.",
        ))

    # Dominant-single payer flag (beyond the `reasonableness.py` 60% cutoff)
    if top[1] >= 0.50:
        risks.append(PayerRisk(
            category="dominant_payer",
            severity="high" if top[1] >= 0.60 else "medium",
            detail=(f"{top[0]} is {top[1]*100:.0f}% of revenue — "
                    "single-payer dependency."),
            remediation="Contract longevity analysis + down-rate scenario.",
        ))

    # Medicare Advantage
    if inputs.medicare_advantage_share is not None:
        ma = float(inputs.medicare_advantage_share)
        if ma > 1.5:
            ma /= 100.0
        if ma >= 0.30:
            risks.append(PayerRisk(
                category="medicare_advantage_heavy",
                severity="medium" if ma < 0.50 else "high",
                detail=(f"Medicare Advantage is {ma*100:.0f}% of revenue. "
                        "MA behaves differently from FFS Medicare — denial "
                        "patterns, rate negotiations, and network rules all "
                        "diverge."),
                remediation="Break out MA payer separately; model MA rate "
                            "actions distinct from FFS Medicare.",
            ))

    # Medicaid Managed Care
    if inputs.medicaid_managed_care_share is not None:
        mmc = float(inputs.medicaid_managed_care_share)
        if mmc > 1.5:
            mmc /= 100.0
        if mmc >= 0.30:
            risks.append(PayerRisk(
                category="medicaid_managed_care_heavy",
                severity="medium",
                detail=(f"Medicaid Managed Care is {mmc*100:.0f}% of "
                        "revenue. MCO rate negotiations differ from FFS."),
                remediation="Per-MCO rate review + contract expiration mapping.",
            ))

    # ACA exchange
    if inputs.aca_exchange_share is not None:
        aca = float(inputs.aca_exchange_share)
        if aca > 1.5:
            aca /= 100.0
        if aca >= 0.20:
            risks.append(PayerRisk(
                category="aca_exchange_heavy",
                severity="medium",
                detail=(f"ACA exchange is {aca*100:.0f}% of revenue. "
                        "Enrollee turnover is high and subsidy policy "
                        "affects member count."),
                remediation="Model subsidy-expiration scenario.",
            ))

    # Mix trend — flag large YoY shifts.
    if inputs.mix_trend_3yr:
        for payer, delta in inputs.mix_trend_3yr.items():
            try:
                d = float(delta)
            except (TypeError, ValueError):
                continue
            if abs(d) >= 0.05:
                sev = "medium" if abs(d) < 0.10 else "high"
                risks.append(PayerRisk(
                    category="mix_shift",
                    severity=sev,
                    detail=(f"{payer} share has shifted {d*100:+.1f} pp "
                            "YoY. Mix instability affects revenue forecast."),
                    remediation="Understand driver — enrollment change, "
                                "rate shock, or selection bias.",
                ))

    if any(r.severity == "high" for r in risks):
        note = "High-severity payer-mix risk — re-price or structure around."
    elif any(r.severity == "medium" for r in risks):
        note = "Medium payer-mix risks — incorporate into diligence."
    else:
        note = "Payer mix is balanced — no material risks surfaced."

    return PayerMixRiskReport(
        payer_hhi=round(hhi, 2),
        risks=risks,
        top_payer=top[0],
        top_payer_share=round(top[1], 4),
        partner_note=note,
    )


def render_payer_mix_risk_markdown(
    report: PayerMixRiskReport,
) -> str:
    lines = [
        "# Payer-mix risk analysis",
        "",
        f"**Payer HHI:** {report.payer_hhi:.0f}  ",
        f"**Top payer:** {report.top_payer or 'n/a'} "
        f"({report.top_payer_share*100:.0f}%)",
        "",
        f"_{report.partner_note}_",
    ]
    if report.risks:
        lines.extend(["", "## Risks", "",
                      "| Category | Severity | Detail | Remediation |",
                      "|---|---|---|---|"])
        for r in report.risks:
            lines.append(
                f"| {r.category} | {r.severity} | {r.detail} | {r.remediation} |"
            )
    return "\n".join(lines)
