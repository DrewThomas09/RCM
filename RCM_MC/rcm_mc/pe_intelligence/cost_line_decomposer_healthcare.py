"""Cost line decomposer — per-line $ and % vs. subsector peer band.

Partner statement: "Show me costs broken into 7
lines — labor, supply, professional fees, rent,
malpractice, utilities, admin. Each line has a peer
band by subsector. If labor is 52% of NPR on a
hospital, that's normal; on an ASC that's a
problem. The decomposition tells me where the lever
is before I underwrite the thesis."

Distinct from:
- `labor_cost_analytics` — labor-only deep dive.
- `labor_shortage_cascade` — labor-shortage
  cascade.

### Subsector peer bands (% of NPR)

Each line has a band (low-high) for each subsector.
If observed % is outside the band, flag direction.

### 7 cost lines

- `labor`
- `supply`
- `professional_fees`
- `rent_occupancy`
- `malpractice_insurance`
- `utilities`
- `admin_overhead`

### 4 subsectors covered

- `hospital` — acute inpatient
- `asc` — ambulatory surgery center
- `physician_practice` — office-based
- `post_acute` — SNF / home health
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


COST_BANDS: Dict[str, Dict[str, tuple]] = {
    "hospital": {
        "labor": (0.45, 0.55),
        "supply": (0.10, 0.18),
        "professional_fees": (0.03, 0.07),
        "rent_occupancy": (0.02, 0.05),
        "malpractice_insurance": (0.02, 0.04),
        "utilities": (0.015, 0.025),
        "admin_overhead": (0.05, 0.09),
    },
    "asc": {
        "labor": (0.30, 0.40),
        "supply": (0.18, 0.26),
        "professional_fees": (0.02, 0.05),
        "rent_occupancy": (0.04, 0.08),
        "malpractice_insurance": (0.01, 0.03),
        "utilities": (0.01, 0.02),
        "admin_overhead": (0.04, 0.07),
    },
    "physician_practice": {
        "labor": (0.45, 0.55),
        "supply": (0.05, 0.10),
        "professional_fees": (0.02, 0.04),
        "rent_occupancy": (0.05, 0.10),
        "malpractice_insurance": (0.02, 0.05),
        "utilities": (0.01, 0.02),
        "admin_overhead": (0.06, 0.10),
    },
    "post_acute": {
        "labor": (0.55, 0.70),
        "supply": (0.05, 0.10),
        "professional_fees": (0.02, 0.04),
        "rent_occupancy": (0.05, 0.10),
        "malpractice_insurance": (0.015, 0.03),
        "utilities": (0.02, 0.035),
        "admin_overhead": (0.05, 0.08),
    },
}

LEVER_HINTS: Dict[str, str] = {
    "labor": (
        "Labor overage: staffing model, productivity "
        "metrics (nurse/patient, FTE/bed), contract "
        "labor mix."
    ),
    "supply": (
        "Supply overage: GPO affiliation, SKU "
        "rationalization, physician preference card "
        "standardization."
    ),
    "professional_fees": (
        "Professional fees overage: outsourced services "
        "(anesthesia, radiology, ED); renegotiate or "
        "in-source."
    ),
    "rent_occupancy": (
        "Rent overage: lease renegotiation, subletting "
        "under-utilized space, related-party lease audit."
    ),
    "malpractice_insurance": (
        "Malpractice overage: broker shop; claims history "
        "drives underwriting."
    ),
    "utilities": (
        "Utilities overage: energy efficiency, vendor "
        "consolidation; typically small $."
    ),
    "admin_overhead": (
        "Admin overage: shared services, redundant "
        "roles, consultant spend review."
    ),
}


@dataclass
class CostLineInputs:
    subsector: str = "hospital"
    npr_m: float = 300.0
    observed_pct_by_line: Dict[str, float] = field(
        default_factory=dict)


@dataclass
class CostLineFinding:
    line: str
    observed_pct: float
    observed_m: float
    peer_band_low: float
    peer_band_high: float
    status: str  # "below_band" / "in_band" / "above_band"
    savings_opportunity_m: float
    lever_hint: str


@dataclass
class CostLineReport:
    subsector: str = ""
    in_catalog: bool = False
    findings: List[CostLineFinding] = field(default_factory=list)
    total_above_band_opportunity_m: float = 0.0
    total_below_band_risk_m: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsector": self.subsector,
            "in_catalog": self.in_catalog,
            "findings": [
                {"line": f.line,
                 "observed_pct": f.observed_pct,
                 "observed_m": f.observed_m,
                 "peer_band_low": f.peer_band_low,
                 "peer_band_high": f.peer_band_high,
                 "status": f.status,
                 "savings_opportunity_m":
                     f.savings_opportunity_m,
                 "lever_hint": f.lever_hint}
                for f in self.findings
            ],
            "total_above_band_opportunity_m":
                self.total_above_band_opportunity_m,
            "total_below_band_risk_m":
                self.total_below_band_risk_m,
            "partner_note": self.partner_note,
        }


def decompose_cost_lines(
    inputs: CostLineInputs,
) -> CostLineReport:
    bands = COST_BANDS.get(inputs.subsector)
    if bands is None:
        return CostLineReport(
            subsector=inputs.subsector,
            in_catalog=False,
            partner_note=(
                f"Subsector '{inputs.subsector}' not in "
                "cost-band catalog. Supported: hospital, "
                "asc, physician_practice, post_acute."
            ),
        )

    findings: List[CostLineFinding] = []
    total_above = 0.0
    total_below = 0.0
    for line, (lo, hi) in bands.items():
        obs_pct = inputs.observed_pct_by_line.get(
            line, (lo + hi) / 2.0)
        obs_m = obs_pct * inputs.npr_m
        if obs_pct > hi:
            status = "above_band"
            savings = (obs_pct - hi) * inputs.npr_m
            total_above += savings
        elif obs_pct < lo:
            status = "below_band"
            # "savings" in the opposite direction — likely
            # under-invested line that will cost later
            savings = -(lo - obs_pct) * inputs.npr_m
            total_below += -(savings)
        else:
            status = "in_band"
            savings = 0.0
        findings.append(CostLineFinding(
            line=line,
            observed_pct=round(obs_pct, 4),
            observed_m=round(obs_m, 2),
            peer_band_low=round(lo, 4),
            peer_band_high=round(hi, 4),
            status=status,
            savings_opportunity_m=round(savings, 2),
            lever_hint=LEVER_HINTS.get(line, ""),
        ))

    findings.sort(
        key=lambda f: f.savings_opportunity_m,
        reverse=True,
    )

    if total_above > 0.02 * inputs.npr_m:
        note = (
            f"Above-band opportunity "
            f"${total_above:.1f}M across "
            f"{sum(1 for f in findings if f.status == 'above_band')} "
            "cost lines. Biggest lever: "
            f"{findings[0].line} "
            f"(${findings[0].savings_opportunity_m:.1f}M). "
            "Build 100-day plan around the top-2 lines."
        )
    elif total_below > 0.02 * inputs.npr_m:
        below_lines = [
            f.line for f in findings
            if f.status == "below_band"
        ]
        note = (
            f"{len(below_lines)} cost line(s) below "
            "peer band — under-investment concern. "
            "Cost coming back in year 2-3 as mandatory "
            f"spend (lines: {', '.join(below_lines)})."
        )
    else:
        note = (
            "Cost structure within peer band — no "
            "material lever or under-investment concern."
        )

    return CostLineReport(
        subsector=inputs.subsector,
        in_catalog=True,
        findings=findings,
        total_above_band_opportunity_m=round(
            total_above, 2),
        total_below_band_risk_m=round(total_below, 2),
        partner_note=note,
    )


def render_cost_line_markdown(
    r: CostLineReport,
) -> str:
    if not r.in_catalog:
        return (
            "# Healthcare cost-line decomposition\n\n"
            f"_{r.partner_note}_\n"
        )
    lines = [
        "# Healthcare cost-line decomposition",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Subsector: {r.subsector}",
        f"- Above-band opportunity: "
        f"${r.total_above_band_opportunity_m:.1f}M",
        f"- Below-band risk: "
        f"${r.total_below_band_risk_m:.1f}M",
        "",
        "| Line | Observed | Peer band | Status | "
        "Opportunity | Lever |",
        "|---|---|---|---|---|---|",
    ]
    for f in r.findings:
        lines.append(
            f"| {f.line} | {f.observed_pct:.1%} | "
            f"{f.peer_band_low:.1%}-{f.peer_band_high:.1%} | "
            f"{f.status} | "
            f"${f.savings_opportunity_m:+.1f}M | "
            f"{f.lever_hint} |"
        )
    return "\n".join(lines)
