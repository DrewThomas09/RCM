"""Reimbursement cliffs — model named rate cliffs in hold window.

Partners name specific reimbursement-rate events ahead of time:
IMD waiver expiry, 340B rule change, Medicare sequestration reset,
site-neutral rule expansion. When any of these fall inside the
hold window, they must be modeled explicitly.

This module takes a list of :class:`ReimbursementCliff` objects + a
hold window and produces:

- Cliffs inside the hold (severity-ranked).
- Dollar impact at each cliff given exposure base.
- Partner-voice cliff-by-cliff commentary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ReimbursementCliff:
    id: str
    name: str
    effective_year: int
    affected_payer: str              # "medicare" | "medicaid" | "commercial" | "340b"
    rate_change_bps: float            # negative for cuts
    state: Optional[str] = None
    source: str = ""                 # citation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "effective_year": self.effective_year,
            "affected_payer": self.affected_payer,
            "rate_change_bps": self.rate_change_bps,
            "state": self.state,
            "source": self.source,
        }


@dataclass
class CliffImpact:
    cliff: ReimbursementCliff
    year_in_hold: int
    dollar_impact: float             # negative = revenue hit
    severity: str                    # "high" | "medium" | "low"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cliff": self.cliff.to_dict(),
            "year_in_hold": self.year_in_hold,
            "dollar_impact": self.dollar_impact,
            "severity": self.severity,
            "partner_note": self.partner_note,
        }


@dataclass
class CliffReport:
    cliffs_in_hold: List[CliffImpact] = field(default_factory=list)
    total_dollar_impact: float = 0.0
    worst_cliff: Optional[str] = None
    partner_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cliffs_in_hold": [c.to_dict() for c in self.cliffs_in_hold],
            "total_dollar_impact": self.total_dollar_impact,
            "worst_cliff": self.worst_cliff,
            "partner_summary": self.partner_summary,
        }


_DEFAULT_CLIFF_LIBRARY: List[ReimbursementCliff] = [
    ReimbursementCliff(
        id="medicare_sequester_reset", name="Medicare sequestration reset",
        effective_year=2027, affected_payer="medicare",
        rate_change_bps=-200, source="OMB sequestration schedule",
    ),
    ReimbursementCliff(
        id="imd_waiver_expiry", name="Medicaid IMD waiver expiry",
        effective_year=2028, affected_payer="medicaid",
        rate_change_bps=-400,
        source="CMS waiver calendar (behavioral health)",
    ),
    ReimbursementCliff(
        id="site_neutral_phase2", name="Site-neutral payment expansion",
        effective_year=2026, affected_payer="medicare",
        rate_change_bps=-150,
        source="CMS OPPS site-neutral rulemaking",
    ),
    ReimbursementCliff(
        id="340b_rule_update", name="340B program rule update",
        effective_year=2027, affected_payer="340b",
        rate_change_bps=-2500,
        source="CMS 340B payment rule history",
    ),
]


def default_cliff_library() -> List[ReimbursementCliff]:
    """Return a starter catalog. Deal teams extend per-deal."""
    return list(_DEFAULT_CLIFF_LIBRARY)


def _severity_for(dollar_impact: float,
                  base_revenue: Optional[float]) -> str:
    if base_revenue is None or base_revenue == 0:
        return "medium"
    ratio = abs(dollar_impact) / abs(base_revenue)
    if ratio >= 0.03:
        return "high"
    if ratio >= 0.01:
        return "medium"
    return "low"


def evaluate_cliffs(
    cliffs: List[ReimbursementCliff],
    *,
    current_year: int,
    hold_years: int,
    state: Optional[str] = None,
    revenue_by_payer: Optional[Dict[str, float]] = None,
) -> CliffReport:
    """Identify cliffs in hold, size their impact, rank severity."""
    revenue_by_payer = revenue_by_payer or {}
    total_revenue = sum(revenue_by_payer.values()) or 0.0

    in_hold: List[CliffImpact] = []
    for cliff in cliffs:
        # Skip state-specific cliffs that don't match.
        if cliff.state and state and cliff.state.upper() != state.upper():
            continue
        yrs_until = cliff.effective_year - current_year
        if yrs_until < 0 or yrs_until > hold_years:
            continue
        base = revenue_by_payer.get(cliff.affected_payer.lower(), 0.0)
        # Rate change in bps → fraction.
        dollar = base * (cliff.rate_change_bps / 10_000.0)
        sev = _severity_for(dollar, total_revenue or None)
        note = (f"{cliff.name} hits in year {yrs_until} — "
                f"${dollar:,.0f} {'revenue hit' if dollar < 0 else 'revenue lift'}.")
        in_hold.append(CliffImpact(
            cliff=cliff, year_in_hold=yrs_until,
            dollar_impact=round(dollar, 2), severity=sev,
            partner_note=note,
        ))

    total = sum(c.dollar_impact for c in in_hold)
    worst = None
    if in_hold:
        worst_obj = min(in_hold, key=lambda c: c.dollar_impact)
        worst = worst_obj.cliff.id

    high = sum(1 for c in in_hold if c.severity == "high")
    if not in_hold:
        summary = "No named reimbursement cliffs inside hold window."
    elif high > 0:
        summary = (f"{high} high-severity cliff(s) in hold — model each "
                   "explicitly and stress the aggregate.")
    else:
        summary = (f"{len(in_hold)} cliff(s) in hold — aggregate impact "
                   f"${total:,.0f}.")

    return CliffReport(
        cliffs_in_hold=sorted(in_hold, key=lambda c: c.dollar_impact),
        total_dollar_impact=round(total, 2),
        worst_cliff=worst,
        partner_summary=summary,
    )


def render_cliff_report_markdown(report: CliffReport) -> str:
    lines = [
        "# Reimbursement cliffs",
        "",
        f"**Aggregate impact:** ${report.total_dollar_impact:,.0f}  ",
        f"**Worst cliff:** {report.worst_cliff or 'none'}",
        "",
        f"_{report.partner_summary}_",
    ]
    if report.cliffs_in_hold:
        lines.extend(["",
                      "| Cliff | Year | Severity | $ impact |",
                      "|---|---:|---|---:|"])
        for c in report.cliffs_in_hold:
            lines.append(
                f"| {c.cliff.name} | Y+{c.year_in_hold} | {c.severity} | "
                f"${c.dollar_impact:,.0f} |"
            )
    return "\n".join(lines)
