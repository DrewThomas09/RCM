"""Concentration risk — the 6-dimension partner scan.

A partner's reflexive concentration scan. Single-dimension
concentration checks exist elsewhere (customer, payer). This
module does the ONE partner question: "show me the six
concentration numbers, side by side, and flag which ones are a
problem."

Dimensions:

1. **Customer** — top-1 / top-5 customer revenue share.
2. **Site / location** — top-1 / top-5 site share of revenue.
3. **Payer** — top-1 payer share of revenue.
4. **Provider** — top-1 / top-5 provider (physician / clinician)
   productivity share.
5. **Service line / product** — top service line share of EBITDA.
6. **Geography** — top state / MSA share of revenue.

Every concentration dimension has the same rule: any ONE dim
> 30% is a diligence flag; > 50% is an underwriting constraint.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ConcentrationInputs:
    top_customer_share: float = 0.0
    top_5_customer_share: float = 0.0
    top_site_share: float = 0.0
    top_5_site_share: float = 0.0
    top_payer_share: float = 0.0
    top_provider_share: float = 0.0
    top_5_provider_share: float = 0.0
    top_service_line_share: float = 0.0
    top_state_share: float = 0.0
    top_msa_share: float = 0.0


@dataclass
class ConcentrationFinding:
    dimension: str
    value: float
    severity: str                           # "low" / "medium" / "high"
    partner_commentary: str


@dataclass
class ConcentrationReport:
    findings: List[ConcentrationFinding] = field(default_factory=list)
    high_count: int = 0
    worst_dimension: str = ""
    worst_value: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "findings": [
                {"dimension": f.dimension, "value": f.value,
                 "severity": f.severity,
                 "partner_commentary": f.partner_commentary}
                for f in self.findings
            ],
            "high_count": self.high_count,
            "worst_dimension": self.worst_dimension,
            "worst_value": self.worst_value,
            "partner_note": self.partner_note,
        }


def _severity(value: float) -> str:
    if value >= 0.50:
        return "high"
    if value >= 0.30:
        return "medium"
    if value >= 0.15:
        return "low"
    return "low"


def _commentary(dim: str, value: float) -> str:
    s = _severity(value)
    if s == "high":
        return (f"{dim.title()} concentration "
                f"{value*100:.0f}% is an underwriting constraint — "
                "re-underwrite assuming 20% of that revenue walks.")
    if s == "medium":
        return (f"{dim.title()} concentration "
                f"{value*100:.0f}% is a diligence flag — get specifics "
                "on contract term, escalator, and renewal date.")
    if s == "low":
        return (f"{dim.title()} concentration "
                f"{value*100:.0f}% is noted but manageable.")
    return ""


def scan_concentration(
    inputs: ConcentrationInputs,
) -> ConcentrationReport:
    findings: List[ConcentrationFinding] = []
    for dim_name, value in [
        ("customer_top_1", inputs.top_customer_share),
        ("customer_top_5", inputs.top_5_customer_share),
        ("site_top_1", inputs.top_site_share),
        ("site_top_5", inputs.top_5_site_share),
        ("payer_top_1", inputs.top_payer_share),
        ("provider_top_1", inputs.top_provider_share),
        ("provider_top_5", inputs.top_5_provider_share),
        ("service_line_top_1", inputs.top_service_line_share),
        ("geography_top_state", inputs.top_state_share),
        ("geography_top_msa", inputs.top_msa_share),
    ]:
        if value <= 0:
            continue
        sev = _severity(value)
        findings.append(ConcentrationFinding(
            dimension=dim_name,
            value=round(value, 4),
            severity=sev,
            partner_commentary=_commentary(dim_name, value),
        ))

    high = sum(1 for f in findings if f.severity == "high")
    if findings:
        worst = max(findings, key=lambda f: f.value)
    else:
        worst = ConcentrationFinding(
            dimension="", value=0.0, severity="low",
            partner_commentary="")

    if high >= 2:
        note = (f"{high} dimensions with > 50% concentration. Not a "
                "flag, a structural issue. Re-underwrite with each "
                "concentrated dimension stressed.")
    elif high == 1:
        note = (f"Single-dim concentration on {worst.dimension} at "
                f"{worst.value*100:.0f}%. Specific mitigation plan "
                "required before IC.")
    elif any(f.severity == "medium" for f in findings):
        med_count = sum(1 for f in findings if f.severity == "medium")
        note = (f"{med_count} medium concentration(s) — "
                f"worst is {worst.dimension} at "
                f"{worst.value*100:.0f}%. Standard diligence "
                "questions apply.")
    else:
        note = ("Concentration profile is reasonably diversified "
                "across all six dimensions.")

    return ConcentrationReport(
        findings=findings,
        high_count=high,
        worst_dimension=worst.dimension,
        worst_value=round(worst.value, 4),
        partner_note=note,
    )


def render_concentration_markdown(
    r: ConcentrationReport,
) -> str:
    lines = [
        "# Concentration risk — 6-dimension scan",
        "",
        f"_{r.partner_note}_",
        "",
        "| Dimension | Value | Severity | Commentary |",
        "|---|---:|---|---|",
    ]
    for f in r.findings:
        lines.append(
            f"| {f.dimension} | {f.value*100:.1f}% | {f.severity} | "
            f"{f.partner_commentary} |"
        )
    return "\n".join(lines)
