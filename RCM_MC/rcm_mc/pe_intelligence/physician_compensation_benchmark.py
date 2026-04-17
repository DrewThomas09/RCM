"""Physician compensation benchmark — comp vs MGMA percentiles.

Physician-practice PE deals (PPM roll-ups, specialty consolidators)
have compensation as their largest cost. Partners benchmark:

- **Total comp / provider** vs MGMA percentiles.
- **Comp / wRVU** (comp divided by work RVU).
- **Base:productivity mix** — too much guaranteed base caps
  productivity; too little creates flight risk.
- **Post-close physician alignment** — MIP equity, retention
  bonuses, non-compete strength.

MGMA median references are partner-approximated — not from a live
feed. A real deployment would ingest the actual MGMA dataset, but
for this codified logic we use representative bands.

Representative medians (2024 data, partner-approximation):

- Primary care: $280K total comp, $55/wRVU.
- Cardiology (invasive): $650K, $75/wRVU.
- Orthopedics: $720K, $85/wRVU.
- Dermatology: $500K, $70/wRVU.
- Gastroenterology: $590K, $73/wRVU.
- Ophthalmology: $480K, $68/wRVU.
- Anesthesiology: $450K, $60/wRVU.
- Emergency medicine: $380K, $55/wRVU.
- Radiology: $530K, $65/wRVU.

Anything ≥ 1.2× median = "above median" (high); ≤ 0.85× = "below
median" (potential productivity cap or flight risk).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Partner-approximated MGMA median references.
MGMA_BENCHMARKS: Dict[str, Dict[str, float]] = {
    "primary_care": {"total_comp_k": 280.0, "comp_per_wrvu": 55.0},
    "cardiology": {"total_comp_k": 650.0, "comp_per_wrvu": 75.0},
    "orthopedics": {"total_comp_k": 720.0, "comp_per_wrvu": 85.0},
    "dermatology": {"total_comp_k": 500.0, "comp_per_wrvu": 70.0},
    "gastroenterology": {"total_comp_k": 590.0, "comp_per_wrvu": 73.0},
    "ophthalmology": {"total_comp_k": 480.0, "comp_per_wrvu": 68.0},
    "anesthesiology": {"total_comp_k": 450.0, "comp_per_wrvu": 60.0},
    "emergency_medicine": {"total_comp_k": 380.0, "comp_per_wrvu": 55.0},
    "radiology": {"total_comp_k": 530.0, "comp_per_wrvu": 65.0},
}


@dataclass
class PhysicianCompInputs:
    specialty: str                        # key from MGMA_BENCHMARKS
    avg_total_comp_k: float               # annualized total comp per provider
    avg_comp_per_wrvu: float              # comp / work RVU
    base_pct: float = 0.60                # guaranteed base as % of total
    provider_count: int = 1
    state: str = "US"                     # optional geo adjust
    coastal_adjust: bool = False           # bump 5% for NYC/SF/LA markets


@dataclass
class PhysicianCompFinding:
    level: str                            # "ok" / "low" / "high"
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {"level": self.level, "description": self.description}


@dataclass
class PhysicianCompReport:
    specialty: str
    comp_pct_of_median: float             # actual / median
    wrvu_pct_of_median: float
    findings: List[PhysicianCompFinding] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "specialty": self.specialty,
            "comp_pct_of_median": self.comp_pct_of_median,
            "wrvu_pct_of_median": self.wrvu_pct_of_median,
            "findings": [f.to_dict() for f in self.findings],
            "partner_note": self.partner_note,
        }


def benchmark_physician_comp(inputs: PhysicianCompInputs) -> PhysicianCompReport:
    """Compare actual physician comp to MGMA median references."""
    bench = MGMA_BENCHMARKS.get(inputs.specialty)
    if bench is None:
        return PhysicianCompReport(
            specialty=inputs.specialty,
            comp_pct_of_median=0.0,
            wrvu_pct_of_median=0.0,
            partner_note=(
                f"Specialty {inputs.specialty!r} not in MGMA library. "
                "Add to MGMA_BENCHMARKS or pick from the supported list."
            ),
        )
    median_comp = bench["total_comp_k"]
    median_wrvu = bench["comp_per_wrvu"]
    if inputs.coastal_adjust:
        median_comp *= 1.05
        median_wrvu *= 1.05
    comp_ratio = inputs.avg_total_comp_k / median_comp
    wrvu_ratio = inputs.avg_comp_per_wrvu / median_wrvu

    findings: List[PhysicianCompFinding] = []

    if comp_ratio >= 1.20:
        findings.append(PhysicianCompFinding(
            level="high",
            description=(f"Total comp {comp_ratio*100:.0f}% of MGMA median — "
                         "above market. Expect margin pressure; look for "
                         "productivity justification in wRVU data."),
        ))
    elif comp_ratio <= 0.85:
        findings.append(PhysicianCompFinding(
            level="low",
            description=(f"Total comp {comp_ratio*100:.0f}% of median — "
                         "below market. Flight risk to competing practices; "
                         "stress test retention."),
        ))
    else:
        findings.append(PhysicianCompFinding(
            level="ok",
            description=(f"Total comp {comp_ratio*100:.0f}% of median — "
                         "within normal band."),
        ))

    if wrvu_ratio >= 1.20:
        findings.append(PhysicianCompFinding(
            level="high",
            description=(f"Comp per wRVU {wrvu_ratio*100:.0f}% of median — "
                         "inefficient; providers paid for less work."),
        ))
    elif wrvu_ratio <= 0.85:
        findings.append(PhysicianCompFinding(
            level="low",
            description=(f"Comp per wRVU {wrvu_ratio*100:.0f}% of median — "
                         "efficient or under-compensated relative to output."),
        ))

    if inputs.base_pct >= 0.80:
        findings.append(PhysicianCompFinding(
            level="high",
            description=(f"Base comp {inputs.base_pct*100:.0f}% of total — "
                         "productivity incentive is weak; expect flat "
                         "volume growth."),
        ))
    elif inputs.base_pct <= 0.30:
        findings.append(PhysicianCompFinding(
            level="low",
            description=(f"Base comp {inputs.base_pct*100:.0f}% of total — "
                         "heavily productivity-weighted; upside for top "
                         "performers but retention risk for average producers."),
        ))

    high_count = sum(1 for f in findings if f.level == "high")
    low_count = sum(1 for f in findings if f.level == "low")

    if high_count >= 2:
        note = ("Comp structure is above market on multiple dimensions — "
                "EBITDA optimization opportunity post-close, but expect "
                "physician pushback.")
    elif low_count >= 2:
        note = ("Comp structure is below market — flight risk; budget for "
                "retention bonuses and potential comp normalization.")
    elif high_count == 1:
        note = ("One comp dimension above market — watch but not urgent.")
    else:
        note = "Comp structure is within MGMA normal bands."

    return PhysicianCompReport(
        specialty=inputs.specialty,
        comp_pct_of_median=round(comp_ratio, 3),
        wrvu_pct_of_median=round(wrvu_ratio, 3),
        findings=findings,
        partner_note=note,
    )


def render_physician_comp_markdown(report: PhysicianCompReport) -> str:
    lines = [
        f"# Physician compensation benchmark — {report.specialty}",
        "",
        f"_{report.partner_note}_",
        "",
        f"- Total comp vs median: {report.comp_pct_of_median*100:.0f}%",
        f"- Comp / wRVU vs median: {report.wrvu_pct_of_median*100:.0f}%",
        "",
        "## Findings",
        "",
    ]
    for f in report.findings:
        lines.append(f"- **{f.level.upper()}**: {f.description}")
    return "\n".join(lines)
