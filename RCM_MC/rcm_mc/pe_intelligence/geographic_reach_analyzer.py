"""Geographic reach analyzer — state/market footprint analysis.

Multi-state healthcare businesses carry compounding complexity:

- Each state has its own Medicaid fee schedule, certificate-of-need
  rules, licensure regime, AG scrutiny, anti-corporate-practice
  statutes.
- Density matters: 30 sites in 1 state >> 30 sites across 30 states
  (for operations / management).
- Regulatory diversity is a double-edged sword: a bad ruling in one
  state doesn't kill the book, but 50 state legal teams cost.

This module takes site-level or revenue-by-state input and returns:

- **State HHI** (revenue concentration across states).
- **Top-state share** (one-state-risk).
- **Anti-corporate-practice-of-medicine (CPOM) exposure** — how
  much revenue is in restrictive states.
- **Expansion white-space suggestions** — adjacent markets by
  demographics + regulatory fit.
- **Density efficiency** — sites per state (rough ops leverage).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


# Partner-approximated anti-CPOM and restrictive states.
# In reality, state-by-state CPOM rules are complex; this is a
# generalized codification used for ranking.
CPOM_RESTRICTIVE_STATES: Set[str] = {
    "CA", "NY", "TX", "IL", "NJ", "OH", "MI", "WA",
    "CO", "IA", "OR",
}

# Favorable expansion states for healthcare services — lower
# regulatory burden, friendly demographics.
EXPANSION_FAVORABLE_STATES: List[str] = [
    "FL", "TX", "AZ", "NC", "TN", "GA", "SC",
    "NV", "UT", "ID",
]


@dataclass
class StateFootprint:
    state: str                            # "CA", "NY", etc.
    revenue_m: float
    site_count: int = 1


@dataclass
class GeoFinding:
    level: str                            # "info" / "medium" / "high"
    message: str


@dataclass
class GeoReachReport:
    state_count: int
    top_state: str
    top_state_share_pct: float
    state_hhi: int
    cpom_exposure_pct: float
    density_avg_sites_per_state: float
    favorable_expansion_states: List[str] = field(default_factory=list)
    findings: List[GeoFinding] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_count": self.state_count,
            "top_state": self.top_state,
            "top_state_share_pct": self.top_state_share_pct,
            "state_hhi": self.state_hhi,
            "cpom_exposure_pct": self.cpom_exposure_pct,
            "density_avg_sites_per_state": self.density_avg_sites_per_state,
            "favorable_expansion_states": list(self.favorable_expansion_states),
            "findings": [{"level": f.level, "message": f.message}
                          for f in self.findings],
            "partner_note": self.partner_note,
        }


def analyze_geography(footprints: List[StateFootprint]) -> GeoReachReport:
    if not footprints:
        return GeoReachReport(
            state_count=0, top_state="", top_state_share_pct=0.0,
            state_hhi=0, cpom_exposure_pct=0.0,
            density_avg_sites_per_state=0.0,
            partner_note="No geographic footprint provided.",
        )

    # Aggregate by state (dedupe).
    by_state: Dict[str, Dict[str, float]] = {}
    for f in footprints:
        state = f.state.upper()
        agg = by_state.setdefault(state, {"revenue_m": 0.0, "sites": 0})
        agg["revenue_m"] += f.revenue_m
        agg["sites"] += f.site_count

    total_rev = sum(v["revenue_m"] for v in by_state.values())
    total_sites = sum(v["sites"] for v in by_state.values())
    if total_rev <= 0:
        total_rev = 0.01

    # Top state.
    top_state, top = max(
        by_state.items(), key=lambda kv: kv[1]["revenue_m"]
    )
    top_share = top["revenue_m"] / total_rev

    # State HHI ×10000.
    hhi = int(sum(((v["revenue_m"] / total_rev) * 100) ** 2
                   for v in by_state.values()))

    # CPOM exposure.
    cpom_rev = sum(v["revenue_m"] for s, v in by_state.items()
                    if s in CPOM_RESTRICTIVE_STATES)
    cpom_pct = cpom_rev / total_rev

    # Density.
    density = total_sites / len(by_state)

    # Expansion suggestions: favorable states not yet entered.
    present = set(by_state.keys())
    expansion = [s for s in EXPANSION_FAVORABLE_STATES if s not in present][:5]

    findings: List[GeoFinding] = []
    if top_share >= 0.60:
        findings.append(GeoFinding(
            level="high",
            message=(f"Top state ({top_state}) = {top_share*100:.0f}% of "
                     "revenue — single-state risk is material."),
        ))
    elif top_share >= 0.40:
        findings.append(GeoFinding(
            level="medium",
            message=(f"Top state ({top_state}) = {top_share*100:.0f}% of "
                     "revenue — watch regulatory risk."),
        ))

    if cpom_pct >= 0.50:
        findings.append(GeoFinding(
            level="high",
            message=(f"{cpom_pct*100:.0f}% of revenue is in CPOM-restrictive "
                     "states — structural complexity for ownership model."),
        ))

    if density < 2.0 and len(by_state) >= 5:
        findings.append(GeoFinding(
            level="medium",
            message=(f"Density {density:.1f} sites/state across "
                     f"{len(by_state)} states — thin operations leverage."),
        ))

    if len(by_state) >= 20:
        findings.append(GeoFinding(
            level="medium",
            message=(f"{len(by_state)} states — state-by-state compliance "
                     "overhead is material."),
        ))

    if top_share < 0.30 and len(by_state) >= 10:
        findings.append(GeoFinding(
            level="info",
            message=("Well-diversified footprint — resilient to any one "
                     "state's policy shock."),
        ))

    if density >= 5.0:
        findings.append(GeoFinding(
            level="info",
            message=(f"Strong density {density:.1f} sites/state — "
                     "operations leverage is good."),
        ))

    high_count = sum(1 for f in findings if f.level == "high")
    if high_count >= 2:
        note = (f"Geographic profile carries material risk: {high_count} "
                "high-severity findings. Reprice or scope diligence.")
    elif high_count == 1:
        note = "One high-severity geographic finding — stress test its impact."
    elif top_share < 0.30 and density >= 3.0:
        note = "Geographic profile is healthy — diversified and dense enough."
    else:
        note = "Geographic profile is standard — no red flags."

    return GeoReachReport(
        state_count=len(by_state),
        top_state=top_state,
        top_state_share_pct=round(top_share * 100, 2),
        state_hhi=hhi,
        cpom_exposure_pct=round(cpom_pct * 100, 2),
        density_avg_sites_per_state=round(density, 2),
        favorable_expansion_states=expansion,
        findings=findings,
        partner_note=note,
    )


def render_geo_markdown(report: GeoReachReport) -> str:
    lines = [
        "# Geographic reach analysis",
        "",
        f"_{report.partner_note}_",
        "",
        f"- State count: {report.state_count}",
        f"- Top state: {report.top_state} "
        f"({report.top_state_share_pct:.1f}%)",
        f"- State HHI: {report.state_hhi}",
        f"- CPOM-restrictive state exposure: "
        f"{report.cpom_exposure_pct:.1f}%",
        f"- Density: {report.density_avg_sites_per_state:.1f} sites/state",
        f"- Suggested expansion: {', '.join(report.favorable_expansion_states) or '—'}",
    ]
    if report.findings:
        lines.extend(["", "## Findings", ""])
        for f in report.findings:
            lines.append(f"- **{f.level.upper()}**: {f.message}")
    return "\n".join(lines)
