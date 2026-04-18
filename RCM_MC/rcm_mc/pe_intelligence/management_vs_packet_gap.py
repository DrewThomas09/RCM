"""Management-vs-packet gap — where the story and the numbers diverge.

Partners test management claims against what the packet shows.
Small gaps are fine — management has forward-looking info. Large
gaps are a credibility issue and must be resolved before IC.

This module takes pairs of (management_claim, packet_reality) on
key metrics and returns the delta, the partner interpretation, and
whether the gap is flat-out contradicted by data.

Each comparison ships with partner-voice guidance: "minor timing
difference" vs "management is rounding up" vs "management is
saying one thing while the data says another."
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Claim:
    metric: str
    mgmt_value: float
    packet_value: float
    unit: str = ""                         # "pct" / "x" / "days" / "$M"
    higher_is_better: bool = True


@dataclass
class GapFinding:
    metric: str
    mgmt_value: float
    packet_value: float
    gap_pct: float                         # (mgmt - packet) / |packet|
    severity: str                          # "minor" / "material" / "contradicted"
    partner_interpretation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "mgmt_value": self.mgmt_value,
            "packet_value": self.packet_value,
            "gap_pct": self.gap_pct,
            "severity": self.severity,
            "partner_interpretation": self.partner_interpretation,
        }


@dataclass
class GapReport:
    findings: List[GapFinding] = field(default_factory=list)
    contradicted_count: int = 0
    material_count: int = 0
    minor_count: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "contradicted_count": self.contradicted_count,
            "material_count": self.material_count,
            "minor_count": self.minor_count,
            "partner_note": self.partner_note,
        }


def _classify_gap(
    gap_pct: float, higher_is_better: bool,
) -> tuple:
    """Return (severity, interpretation)."""
    # Mgmt-favorable gap is "mgmt_value is better than packet."
    favorable = (gap_pct > 0 and higher_is_better) or (
        gap_pct < 0 and not higher_is_better)
    abs_pct = abs(gap_pct)
    if abs_pct < 0.05:
        return ("minor",
                "Minor difference — within rounding or timing noise.")
    if abs_pct < 0.15:
        if favorable:
            return ("material",
                    "Management is rounding up — push for the "
                    "packet number in underwriting.")
        return ("material",
                "Management is below where data shows them — "
                "conservative framing or missed metric.")
    if favorable:
        return ("contradicted",
                "Management claim contradicted by data. Credibility "
                "hit — they are selling what the numbers do not show.")
    return ("contradicted",
             "Large gap in the other direction — something changed "
             "recently or management is sandbagging.")


def compare_claims(claims: List[Claim]) -> GapReport:
    findings: List[GapFinding] = []
    for c in claims:
        base = abs(c.packet_value) if c.packet_value != 0 else 1.0
        gap = (c.mgmt_value - c.packet_value) / base
        sev, interp = _classify_gap(gap, c.higher_is_better)
        findings.append(GapFinding(
            metric=c.metric,
            mgmt_value=round(c.mgmt_value, 4),
            packet_value=round(c.packet_value, 4),
            gap_pct=round(gap, 4),
            severity=sev,
            partner_interpretation=interp,
        ))

    contradicted = sum(1 for f in findings if f.severity == "contradicted")
    material = sum(1 for f in findings if f.severity == "material")
    minor = sum(1 for f in findings if f.severity == "minor")

    if contradicted >= 2:
        note = (f"{contradicted} management claims contradicted by "
                "packet data. This is a credibility problem, not a "
                "metrics problem. Pause diligence until reconciled.")
    elif contradicted == 1:
        worst = next(f for f in findings
                      if f.severity == "contradicted")
        note = (f"Management claim on {worst.metric} contradicted by "
                "data. Force explicit reconciliation before IC.")
    elif material >= 3:
        note = (f"{material} claims where management is rounding in "
                "their favor. Underwrite to the packet numbers, not "
                "the deck.")
    elif material > 0:
        note = (f"{material} material gap(s); mostly rounding. Fold "
                "into diligence questions.")
    else:
        note = ("Management and packet align. No gaps worth "
                "flagging.")

    return GapReport(
        findings=findings,
        contradicted_count=contradicted,
        material_count=material,
        minor_count=minor,
        partner_note=note,
    )


def render_gap_markdown(r: GapReport) -> str:
    lines = [
        "# Management vs packet gap",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Contradicted: {r.contradicted_count}",
        f"- Material: {r.material_count}",
        f"- Minor: {r.minor_count}",
        "",
        "| Metric | Mgmt | Packet | Gap % | Severity | Interpretation |",
        "|---|---:|---:|---:|---|---|",
    ]
    for f in r.findings:
        lines.append(
            f"| {f.metric} | {f.mgmt_value:.3f} | "
            f"{f.packet_value:.3f} | {f.gap_pct*100:+.1f}% | "
            f"{f.severity} | {f.partner_interpretation} |"
        )
    return "\n".join(lines)
