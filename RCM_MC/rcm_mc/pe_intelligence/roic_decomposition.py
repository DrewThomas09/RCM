"""ROIC decomposition — return on invested capital, DuPont-style.

Partners decompose ROIC to spot weak links:

- ROIC = NOPAT / Invested Capital.
- NOPAT = EBIT × (1 - tax rate).
- Invested Capital = Net PP&E + NWC + Intangibles.

Decomposed further:

- **Margin** = EBIT / Revenue (ops efficiency).
- **Turnover** = Revenue / Invested Capital (asset efficiency).
- ROIC = Margin × Turnover × (1 - tax rate).

Healthcare-PE peers:

- Specialty practices: margin 18-25%, turnover 1.5-2.5x, ROIC
  20-35%.
- Hospitals: margin 10-15%, turnover 0.6-0.8x, ROIC 7-12%.
- Outpatient / ASC: margin 25-35%, turnover 1.2-1.8x, ROIC 25-40%.

This module takes a subsector, computes ROIC, flags weak links,
and produces a partner note.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


SUBSECTOR_BANDS: Dict[str, Dict[str, tuple]] = {
    "specialty_practice": {
        "ebit_margin": (0.18, 0.25),
        "capital_turnover": (1.5, 2.5),
        "roic": (0.20, 0.35),
    },
    "hospital": {
        "ebit_margin": (0.10, 0.15),
        "capital_turnover": (0.6, 0.8),
        "roic": (0.07, 0.12),
    },
    "outpatient_asc": {
        "ebit_margin": (0.25, 0.35),
        "capital_turnover": (1.2, 1.8),
        "roic": (0.25, 0.40),
    },
    "dme_supplier": {
        "ebit_margin": (0.08, 0.12),
        "capital_turnover": (2.0, 3.5),
        "roic": (0.15, 0.25),
    },
    "home_health": {
        "ebit_margin": (0.10, 0.15),
        "capital_turnover": (3.0, 5.0),
        "roic": (0.25, 0.40),
    },
}


@dataclass
class ROICInputs:
    subsector: str
    revenue_m: float
    ebit_m: float
    invested_capital_m: float
    tax_rate: float = 0.25


@dataclass
class ROICFinding:
    component: str
    verdict: str                          # "above_band" / "in_band" / "below_band"
    actual: float
    band_low: float
    band_high: float


@dataclass
class ROICResult:
    subsector: str
    ebit_margin: float
    capital_turnover: float
    tax_rate: float
    nopat_m: float
    roic: float
    findings: List[ROICFinding] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsector": self.subsector,
            "ebit_margin": self.ebit_margin,
            "capital_turnover": self.capital_turnover,
            "tax_rate": self.tax_rate,
            "nopat_m": self.nopat_m,
            "roic": self.roic,
            "findings": [
                {
                    "component": f.component, "verdict": f.verdict,
                    "actual": f.actual, "band_low": f.band_low,
                    "band_high": f.band_high,
                } for f in self.findings
            ],
            "partner_note": self.partner_note,
        }


def _verdict(actual: float, band: tuple) -> str:
    lo, hi = band
    if actual < lo:
        return "below_band"
    if actual > hi:
        return "above_band"
    return "in_band"


def decompose_roic(inputs: ROICInputs) -> ROICResult:
    revenue = max(0.01, inputs.revenue_m)
    ic = max(0.01, inputs.invested_capital_m)
    margin = inputs.ebit_m / revenue
    turnover = revenue / ic
    nopat = inputs.ebit_m * (1 - inputs.tax_rate)
    roic = nopat / ic

    bands = SUBSECTOR_BANDS.get(inputs.subsector)
    findings: List[ROICFinding] = []
    if bands:
        for comp, actual in [
            ("ebit_margin", margin),
            ("capital_turnover", turnover),
            ("roic", roic),
        ]:
            lo, hi = bands[comp]
            findings.append(ROICFinding(
                component=comp,
                verdict=_verdict(actual, (lo, hi)),
                actual=round(actual, 4),
                band_low=lo, band_high=hi,
            ))

    weak = [f for f in findings if f.verdict == "below_band"]
    strong = [f for f in findings if f.verdict == "above_band"]

    if not bands:
        note = f"Subsector {inputs.subsector!r} not in ROIC library."
    elif len(weak) >= 2:
        weak_names = ", ".join(w.component for w in weak)
        note = (f"ROIC below peer band ({roic*100:.1f}%) with weakness "
                f"in: {weak_names}. Operating posture needs "
                "intervention.")
    elif weak:
        note = (f"ROIC weak link: {weak[0].component} "
                f"({weak[0].actual:.2f}) below peer band.")
    elif len(strong) >= 2:
        note = (f"ROIC {roic*100:.1f}% — top of peer range; confirm "
                "sustainability vs one-time tailwinds.")
    else:
        note = f"ROIC {roic*100:.1f}% — in line with peer band."

    return ROICResult(
        subsector=inputs.subsector,
        ebit_margin=round(margin, 4),
        capital_turnover=round(turnover, 4),
        tax_rate=inputs.tax_rate,
        nopat_m=round(nopat, 2),
        roic=round(roic, 4),
        findings=findings,
        partner_note=note,
    )


def render_roic_markdown(r: ROICResult) -> str:
    lines = [
        f"# ROIC decomposition — {r.subsector}",
        "",
        f"_{r.partner_note}_",
        "",
        f"- EBIT margin: {r.ebit_margin*100:.1f}%",
        f"- Capital turnover: {r.capital_turnover:.2f}x",
        f"- NOPAT: ${r.nopat_m:,.2f}M",
        f"- ROIC: {r.roic*100:.1f}%",
    ]
    if r.findings:
        lines.extend(["", "## Peer-band check", "",
                       "| Component | Verdict | Actual | Low | High |",
                       "|---|---|---:|---:|---:|"])
        for f in r.findings:
            lines.append(
                f"| {f.component} | {f.verdict} | "
                f"{f.actual:.3f} | {f.band_low:.3f} | {f.band_high:.3f} |"
            )
    return "\n".join(lines)
