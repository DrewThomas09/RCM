"""Service-line analysis — mix risk, margin contribution, exposure.

Given a target's service-line breakdown (revenue and margin by
line), this module surfaces:

- **Concentration** — top-line share, HHI across service lines.
- **Margin contribution** — which lines carry the EBITDA.
- **Single-point-of-failure risk** — top-line share > 30% on a
  reimbursement-exposed line.
- **Portfolio verdict** — balanced / anchor-line-dependent /
  specialty-concentration / well-diversified.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ServiceLine:
    name: str
    revenue_share: float              # fraction 0..1
    ebitda_margin: Optional[float] = None
    is_reimbursement_exposed: bool = False     # CMS rate-sensitive

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "revenue_share": self.revenue_share,
            "ebitda_margin": self.ebitda_margin,
            "is_reimbursement_exposed": self.is_reimbursement_exposed,
        }


@dataclass
class ServiceLineRisk:
    line: ServiceLine
    ebitda_contribution_share: Optional[float]    # fraction of total EBITDA
    risk_score: float                             # 0..1
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "line": self.line.to_dict(),
            "ebitda_contribution_share": self.ebitda_contribution_share,
            "risk_score": self.risk_score,
            "flags": list(self.flags),
        }


@dataclass
class ServiceLinePortfolio:
    per_line: List[ServiceLineRisk] = field(default_factory=list)
    concentration_top_line: float = 0.0
    concentration_top_3: float = 0.0
    service_line_hhi: float = 0.0                 # 0..10000
    top_ebitda_contributor_share: float = 0.0
    portfolio_verdict: str = ""                    # balanced / anchor_dependent / specialty_concentration / well_diversified
    partner_note: str = ""
    actions_needed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "per_line": [r.to_dict() for r in self.per_line],
            "concentration_top_line": self.concentration_top_line,
            "concentration_top_3": self.concentration_top_3,
            "service_line_hhi": self.service_line_hhi,
            "top_ebitda_contributor_share": self.top_ebitda_contributor_share,
            "portfolio_verdict": self.portfolio_verdict,
            "partner_note": self.partner_note,
            "actions_needed": list(self.actions_needed),
        }


# ── Helpers ─────────────────────────────────────────────────────────

def _service_line_hhi(shares: List[float]) -> float:
    return sum((s * 100.0) ** 2 for s in shares)


def _score_line(line: ServiceLine) -> ServiceLineRisk:
    score = 0.0
    flags: List[str] = []
    if line.revenue_share >= 0.30:
        score += 0.40
        flags.append(f"Single-line revenue share {line.revenue_share*100:.0f}%.")
    elif line.revenue_share >= 0.20:
        score += 0.20
        flags.append("Meaningful revenue contributor.")

    if line.is_reimbursement_exposed:
        score += 0.30
        flags.append("CMS rate-sensitive line.")

    if line.revenue_share >= 0.30 and line.is_reimbursement_exposed:
        score += 0.20
        flags.append("Concentration × reimbursement exposure compounds risk.")

    if (line.ebitda_margin is not None and line.ebitda_margin < 0.02
            and line.revenue_share >= 0.10):
        score += 0.10
        flags.append("Low-margin line with meaningful revenue share — dilutive.")

    return ServiceLineRisk(
        line=line,
        ebitda_contribution_share=None,          # filled at portfolio level
        risk_score=min(score, 1.0),
        flags=flags,
    )


def _ebitda_contributions(lines: List[ServiceLine]) -> Dict[str, float]:
    """Approximate EBITDA contribution per line as share × margin."""
    raw = {}
    for line in lines:
        m = line.ebitda_margin if line.ebitda_margin is not None else 0.0
        raw[line.name] = line.revenue_share * m
    total = sum(raw.values())
    if total <= 0:
        return {k: 0.0 for k in raw}
    return {k: v / total for k, v in raw.items()}


def _portfolio_verdict(
    top_line: float, top_3: float, hhi: float,
    top_ebitda: float,
) -> str:
    if top_line >= 0.40:
        return "anchor_dependent"
    if top_ebitda >= 0.60 and top_line < 0.30:
        return "specialty_concentration"
    if hhi < 1500 and top_line < 0.25:
        return "well_diversified"
    if hhi < 2500:
        return "balanced"
    return "anchor_dependent"


_PARTNER_NOTE = {
    "well_diversified": (
        "Well-diversified service-line portfolio — no single line moves "
        "the deal on its own."),
    "balanced": (
        "Balanced portfolio — modest concentration, no single-point-of-"
        "failure line."),
    "anchor_dependent": (
        "Anchor-dependent portfolio — one or more lines drive the deal. "
        "Re-verify the anchor's reimbursement and competitive position."),
    "specialty_concentration": (
        "Specialty-concentrated portfolio — high-margin lines drive "
        "EBITDA disproportionately. Stress the anchor line."),
}


# ── Orchestrator ────────────────────────────────────────────────────

def analyze_service_lines(
    lines: List[ServiceLine],
) -> ServiceLinePortfolio:
    """Compute concentration, contribution, and portfolio verdict."""
    if not lines:
        return ServiceLinePortfolio(
            portfolio_verdict="unknown",
            partner_note="No service-line data provided.",
        )

    # Per-line risk
    per_line = [_score_line(l) for l in lines]
    # EBITDA contribution shares
    contributions = _ebitda_contributions(lines)
    for r in per_line:
        r.ebitda_contribution_share = round(
            contributions.get(r.line.name, 0.0), 4
        )

    sorted_by_share = sorted(lines, key=lambda l: -l.revenue_share)
    concentration_top = sorted_by_share[0].revenue_share
    concentration_3 = sum(l.revenue_share for l in sorted_by_share[:3])
    hhi = _service_line_hhi([l.revenue_share for l in lines])
    top_ebitda = max(contributions.values()) if contributions else 0.0

    verdict = _portfolio_verdict(concentration_top, concentration_3,
                                 hhi, top_ebitda)

    actions: List[str] = []
    for r in per_line:
        if r.risk_score >= 0.50:
            actions.append(
                f"Diligence {r.line.name}: concentration + exposure profile."
            )
    if concentration_top >= 0.40:
        actions.append(
            f"Single-line share {concentration_top*100:.0f}% — model a "
            "reimbursement-shock scenario specifically for this line.")

    return ServiceLinePortfolio(
        per_line=per_line,
        concentration_top_line=round(concentration_top, 4),
        concentration_top_3=round(concentration_3, 4),
        service_line_hhi=round(hhi, 2),
        top_ebitda_contributor_share=round(top_ebitda, 4),
        portfolio_verdict=verdict,
        partner_note=_PARTNER_NOTE.get(verdict, ""),
        actions_needed=actions,
    )


def render_service_lines_markdown(portfolio: ServiceLinePortfolio) -> str:
    lines = [
        "# Service-line portfolio",
        "",
        f"**Verdict:** {portfolio.portfolio_verdict}  ",
        f"**Partner note:** {portfolio.partner_note}",
        "",
        f"- Top-line share: {portfolio.concentration_top_line*100:.0f}%",
        f"- Top-3 share: {portfolio.concentration_top_3*100:.0f}%",
        f"- Service-line HHI: {portfolio.service_line_hhi:.0f}",
        f"- Top EBITDA-contributor share: {portfolio.top_ebitda_contributor_share*100:.0f}%",
        "",
        "## Per-line",
        "",
        "| Line | Revenue share | Margin | EBITDA contrib | Risk | Flags |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for r in portfolio.per_line:
        m = (f"{r.line.ebitda_margin*100:.1f}%"
             if r.line.ebitda_margin is not None else "n/a")
        contrib = (f"{(r.ebitda_contribution_share or 0)*100:.0f}%"
                   if r.ebitda_contribution_share is not None else "—")
        lines.append(
            f"| {r.line.name} | {r.line.revenue_share*100:.0f}% | "
            f"{m} | {contrib} | {r.risk_score:.2f} | {'; '.join(r.flags)} |"
        )
    if portfolio.actions_needed:
        lines.extend(["", "## Actions needed", ""])
        for i, a in enumerate(portfolio.actions_needed, 1):
            lines.append(f"{i}. {a}")
    return "\n".join(lines)
