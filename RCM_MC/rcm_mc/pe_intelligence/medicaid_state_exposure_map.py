"""Medicaid state exposure map — state-specific risk overlay.

Existing OBBBA / sequestration modules apply national rates.
Medicaid is state-by-state, and state-level risk varies sharply.
A partner with a multi-state portfolio needs to know which states
are the leverage and which are the exposure.

This module takes a site-level Medicaid revenue distribution and
returns:

- Per-state exposure with risk rating.
- Dollar impact under a state-specific bear scenario.
- Worst-exposed state named + partner note.

State risk tiers (partner-approximated 2026-2028):

- **high_cut_risk** — ongoing rate-freeze legislation / budget
  pressure (e.g., TX, FL, GA, TN, MO, AZ — non-expansion or
  tight-budget states).
- **medium_cut_risk** — baseline rate freezes possible
  (e.g., OH, IN, NC, SC, IA, WI).
- **low_cut_risk** — expansion states with backfill funding
  (e.g., NY, CA, MA, WA, OR, MN).
- **waiver_risk** — states with major 1115 waiver changes on the
  docket (e.g., AR, IA, KY, MO).

Partners use this for both underwriting (avoid concentration in
high-risk states) and post-close monitoring.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


STATE_RISK_TIER = {
    # High cut risk — non-expansion + budget pressure states.
    "TX": "high_cut_risk", "FL": "high_cut_risk",
    "GA": "high_cut_risk", "TN": "high_cut_risk",
    "MS": "high_cut_risk", "AL": "high_cut_risk",
    "SC": "high_cut_risk", "MO": "high_cut_risk",
    "KS": "high_cut_risk", "WY": "high_cut_risk",
    # Medium.
    "AZ": "medium_cut_risk", "OH": "medium_cut_risk",
    "IN": "medium_cut_risk", "NC": "medium_cut_risk",
    "IA": "medium_cut_risk", "WI": "medium_cut_risk",
    "OK": "medium_cut_risk", "LA": "medium_cut_risk",
    "VA": "medium_cut_risk",
    # Waiver risk — 1115 changes on docket.
    "AR": "waiver_risk", "KY": "waiver_risk",
    "ND": "waiver_risk", "MT": "waiver_risk",
    # Low cut risk — expansion with stable funding.
    "NY": "low_cut_risk", "CA": "low_cut_risk",
    "MA": "low_cut_risk", "WA": "low_cut_risk",
    "OR": "low_cut_risk", "MN": "low_cut_risk",
    "CO": "low_cut_risk", "VT": "low_cut_risk",
    "MD": "low_cut_risk", "NJ": "low_cut_risk",
    "CT": "low_cut_risk", "IL": "low_cut_risk",
    "RI": "low_cut_risk", "HI": "low_cut_risk",
    "NM": "low_cut_risk", "NV": "low_cut_risk",
    "DE": "low_cut_risk", "PA": "low_cut_risk",
    "MI": "low_cut_risk", "NH": "low_cut_risk",
}

TIER_BEAR_CUT_PCT = {
    "high_cut_risk": 0.05,       # 5% bear rate cut
    "waiver_risk": 0.04,
    "medium_cut_risk": 0.025,
    "low_cut_risk": 0.01,
}


@dataclass
class StateMedicaidSite:
    state: str                               # 2-letter
    medicaid_revenue_m: float = 0.0


@dataclass
class StateExposure:
    state: str
    risk_tier: str
    medicaid_revenue_m: float
    bear_rate_cut_pct: float
    bear_ebitda_impact_m: float
    partner_commentary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "risk_tier": self.risk_tier,
            "medicaid_revenue_m": self.medicaid_revenue_m,
            "bear_rate_cut_pct": self.bear_rate_cut_pct,
            "bear_ebitda_impact_m": self.bear_ebitda_impact_m,
            "partner_commentary": self.partner_commentary,
        }


@dataclass
class MedicaidMapReport:
    total_medicaid_revenue_m: float
    total_bear_ebitda_impact_m: float
    worst_state: str
    worst_state_impact_m: float
    high_risk_revenue_share_pct: float
    exposures: List[StateExposure] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_medicaid_revenue_m": self.total_medicaid_revenue_m,
            "total_bear_ebitda_impact_m":
                self.total_bear_ebitda_impact_m,
            "worst_state": self.worst_state,
            "worst_state_impact_m": self.worst_state_impact_m,
            "high_risk_revenue_share_pct":
                self.high_risk_revenue_share_pct,
            "exposures": [e.to_dict() for e in self.exposures],
            "partner_note": self.partner_note,
        }


def _commentary(tier: str, revenue_m: float) -> str:
    if tier == "high_cut_risk":
        return (f"High cut risk state — "
                f"${revenue_m:,.1f}M exposed. Budget-pressure + "
                "non-expansion profile means rate freezes ahead; "
                "assume 5% bear case.")
    if tier == "medium_cut_risk":
        return (f"Medium cut risk — ${revenue_m:,.1f}M. Baseline "
                "freeze possible; 2.5% bear case.")
    if tier == "waiver_risk":
        return (f"Waiver risk — ${revenue_m:,.1f}M. 1115 waiver "
                "changes on docket; 4% bear. Timing uncertain.")
    if tier == "low_cut_risk":
        return (f"Low cut risk — ${revenue_m:,.1f}M. Expansion "
                "state with stable backfill funding.")
    return f"Unmapped state — ${revenue_m:,.1f}M tracked at 2.5%."


def map_medicaid_exposure(
    sites: List[StateMedicaidSite],
    contribution_margin: float = 0.45,
) -> MedicaidMapReport:
    # Aggregate by state.
    by_state: Dict[str, float] = {}
    for s in sites:
        state = s.state.upper()
        by_state[state] = by_state.get(state, 0.0) + s.medicaid_revenue_m

    exposures: List[StateExposure] = []
    total_rev = 0.0
    total_impact = 0.0
    high_risk_rev = 0.0

    for state, rev in by_state.items():
        tier = STATE_RISK_TIER.get(state, "medium_cut_risk")
        cut = TIER_BEAR_CUT_PCT.get(tier, 0.025)
        impact = rev * cut * contribution_margin
        exposures.append(StateExposure(
            state=state, risk_tier=tier,
            medicaid_revenue_m=round(rev, 2),
            bear_rate_cut_pct=round(cut, 4),
            bear_ebitda_impact_m=round(impact, 2),
            partner_commentary=_commentary(tier, rev),
        ))
        total_rev += rev
        total_impact += impact
        if tier in ("high_cut_risk", "waiver_risk"):
            high_risk_rev += rev

    exposures.sort(key=lambda e: e.bear_ebitda_impact_m, reverse=True)
    worst = exposures[0] if exposures else StateExposure(
        "", "low_cut_risk", 0.0, 0.0, 0.0, "")
    high_risk_share = (high_risk_rev / total_rev
                        if total_rev > 0 else 0.0)

    if total_rev == 0:
        note = ("No Medicaid exposure logged — not a Medicaid-"
                "sensitive asset.")
    elif high_risk_share >= 0.50:
        note = (f"{high_risk_share*100:.0f}% of Medicaid exposure in "
                "high-cut-risk or waiver-risk states. Underwrite "
                f"with {total_impact:,.1f}M of state-risk bear drag.")
    elif high_risk_share >= 0.25:
        note = (f"Moderate concentration in risky states "
                f"({high_risk_share*100:.0f}%); "
                f"${total_impact:,.1f}M bear drag. Monitor state "
                "budget cycles.")
    elif high_risk_share > 0:
        note = (f"Modest state risk "
                f"({high_risk_share*100:.0f}%); "
                f"${total_impact:,.1f}M bear drag. Manageable.")
    else:
        note = ("Medicaid exposure is concentrated in low-risk "
                "states — state budget risk is not a material lever.")

    return MedicaidMapReport(
        total_medicaid_revenue_m=round(total_rev, 2),
        total_bear_ebitda_impact_m=round(total_impact, 2),
        worst_state=worst.state,
        worst_state_impact_m=worst.bear_ebitda_impact_m,
        high_risk_revenue_share_pct=round(high_risk_share * 100, 2),
        exposures=exposures,
        partner_note=note,
    )


def render_medicaid_map_markdown(r: MedicaidMapReport) -> str:
    lines = [
        "# Medicaid state exposure map",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Total Medicaid revenue: "
        f"${r.total_medicaid_revenue_m:,.1f}M",
        f"- Total bear-case EBITDA impact: "
        f"${r.total_bear_ebitda_impact_m:,.1f}M",
        f"- Worst state: {r.worst_state} "
        f"(${r.worst_state_impact_m:,.2f}M)",
        f"- High-risk-state share: "
        f"{r.high_risk_revenue_share_pct:.1f}%",
        "",
        "| State | Tier | Rev $M | Bear cut | EBITDA hit | Commentary |",
        "|---|---|---:|---:|---:|---|",
    ]
    for e in r.exposures:
        lines.append(
            f"| {e.state} | {e.risk_tier} | "
            f"${e.medicaid_revenue_m:,.1f}M | "
            f"{e.bear_rate_cut_pct*100:.1f}% | "
            f"${e.bear_ebitda_impact_m:,.2f}M | "
            f"{e.partner_commentary} |"
        )
    return "\n".join(lines)
