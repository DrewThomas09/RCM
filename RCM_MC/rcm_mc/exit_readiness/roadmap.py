"""Readiness-gap roadmap — quarterly-sequenced remediation plan.

The existing identify_readiness_gaps returns a FLAT list of
gaps. The user-facing artefact a partner actually needs is a
SEQUENCED roadmap: which gaps to start in Q1, which in Q2, etc.,
plus an overall readiness score that compresses "how prepared
is this asset for exit today" into one number.

This module also adds the two archetype-specific gap detectors
that the original readiness module didn't cover:

  • Sponsor-to-sponsor — process-readiness gaps (VDR maturity,
    audit cadence, recurring revenue mix).
  • Continuation vehicle — LP-side gaps (liquidity demand
    alignment, LP-base concentration).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .target import ExitArchetype, ExitTarget
from .readiness import ReadinessGap, identify_readiness_gaps


@dataclass
class RoadmapQuarter:
    """One quarter's worth of remediation work."""
    quarter_index: int           # 1, 2, 3, ...
    months_from_now: int         # quarter_index × 3 - 3 (start)
    gaps: List[ReadinessGap] = field(default_factory=list)


@dataclass
class ReadinessRoadmap:
    """Sequenced quarterly plan + overall readiness score."""
    target_name: str
    readiness_score: float       # 0-1; 1.0 = ready today
    quarters: List[RoadmapQuarter] = field(default_factory=list)
    total_gaps: int = 0
    high_severity_count: int = 0
    expected_ready_in_months: int = 0


def _sponsor_to_sponsor_gaps(target: ExitTarget) -> List[ReadinessGap]:
    """Process-readiness gaps for a sponsor-to-sponsor exit.

    Sponsor buyers price aggressively but expect a clean process —
    VDR up to date, recurring revenue clearly visible, audited
    financials. Gaps here cost weeks of process delay, not bid
    headlines.
    """
    out: List[ReadinessGap] = []
    # Recurring revenue check — higher cash-pay share signals less
    # recurring (membership/contract) revenue
    if target.cash_pay_share > 0.20:
        out.append(ReadinessGap(
            archetype=ExitArchetype.SPONSOR_TO_SPONSOR,
            title="Heavy cash-pay mix limits recurring-revenue claim",
            description=(
                f"Cash-pay {target.cash_pay_share*100:.0f}% of "
                f"revenue. Sponsor buyers underwrite recurring/"
                f"contract revenue first; cash-pay is treated as "
                f"churn-prone. Convert as much as possible to "
                f"membership / subscription contracts in the 6-12 "
                f"months before launch."),
            months_to_remediate=12, severity="medium"))
    # EBITDA scale — sponsor-to-sponsor below $10M EBITDA is a
    # narrow buyer universe
    if target.ttm_ebitda_mm < 10:
        out.append(ReadinessGap(
            archetype=ExitArchetype.SPONSOR_TO_SPONSOR,
            title="EBITDA below sponsor-to-sponsor scale floor",
            description=(
                f"TTM EBITDA ${target.ttm_ebitda_mm:.1f}M. Most "
                f"sponsor buyers gate at $10M+ for platform deals; "
                f"below that the universe narrows to add-on buyers "
                f"who pay 1-2 turns less."),
            months_to_remediate=18, severity="high"))
    return out


def _continuation_vehicle_gaps(target: ExitTarget,
                               ) -> List[ReadinessGap]:
    """LP-side gaps for a continuation-vehicle exit.

    The CV path needs three things in alignment: continued
    growth runway, LP appetite for the asset (the existing fund's
    LPs have to be willing to roll OR the CV needs new LPs lined
    up), and a defensible NAV.
    """
    out: List[ReadinessGap] = []
    if target.growth_rate < 0.07:
        out.append(ReadinessGap(
            archetype=ExitArchetype.CONTINUATION,
            title="Growth too low to justify CV roll",
            description=(
                f"Forward growth {target.growth_rate*100:.1f}%. "
                f"Continuation vehicles require a credible "
                f"forward-growth story (typically 8%+) so the "
                f"existing LPs see why a 5-year extension creates "
                f"more value than a clean exit today."),
            months_to_remediate=12, severity="high"))
    if target.growth_durability_score < 0.6:
        out.append(ReadinessGap(
            archetype=ExitArchetype.CONTINUATION,
            title="Growth durability score too low",
            description=(
                f"Durability score {target.growth_durability_score:.2f} "
                f"under the 0.60 floor. CV NAV models discount "
                f"heavily when forward growth isn't durable; LPs "
                f"underwrite to a haircut, narrowing the spread."),
            months_to_remediate=12, severity="medium"))
    return out


def _severity_to_quarter(severity: str,
                         months_to_remediate: int) -> int:
    """Quarter-index assignment policy. High severity starts in Q1
    regardless of how long it takes; medium starts in Q2; low in
    Q3+. Within each tier, longer-to-remediate items still start
    early (so they finish in time)."""
    if severity == "high":
        return 1
    if severity == "medium":
        return 2
    return 3


def _readiness_score_from_gaps(gaps: List[ReadinessGap]) -> float:
    """Compress the gap list into a 0-1 readiness score.

    Each high gap costs 0.15, each medium 0.07, each low 0.03.
    Score floors at 0.0 and starts at 1.0.
    """
    score = 1.0
    for g in gaps:
        if g.severity == "high":
            score -= 0.15
        elif g.severity == "medium":
            score -= 0.07
        else:
            score -= 0.03
    return max(0.0, round(score, 3))


def build_readiness_roadmap(
    target: ExitTarget,
    *,
    extra_gaps: Optional[List[ReadinessGap]] = None,
) -> ReadinessRoadmap:
    """Build the quarterly-sequenced roadmap.

    Combines the existing identify_readiness_gaps output with
    the new sponsor-to-sponsor + continuation-vehicle gaps,
    assigns each to a quarter, and computes the overall
    readiness score + expected ready-by month.
    """
    gaps = list(identify_readiness_gaps(target))
    gaps.extend(_sponsor_to_sponsor_gaps(target))
    gaps.extend(_continuation_vehicle_gaps(target))
    if extra_gaps:
        gaps.extend(extra_gaps)

    # Bucket by quarter
    by_q: Dict[int, List[ReadinessGap]] = {}
    for g in gaps:
        q = _severity_to_quarter(g.severity, g.months_to_remediate)
        by_q.setdefault(q, []).append(g)

    quarters: List[RoadmapQuarter] = []
    for q_idx in sorted(by_q.keys()):
        # Within a quarter sort by remediation time descending —
        # start the long-running items first.
        bucket = sorted(by_q[q_idx],
                        key=lambda g: -g.months_to_remediate)
        quarters.append(RoadmapQuarter(
            quarter_index=q_idx,
            months_from_now=(q_idx - 1) * 3,
            gaps=bucket,
        ))

    high_count = sum(1 for g in gaps if g.severity == "high")
    expected_ready = (max((g.months_to_remediate for g in gaps),
                          default=0))

    return ReadinessRoadmap(
        target_name=target.target_name,
        readiness_score=_readiness_score_from_gaps(gaps),
        quarters=quarters,
        total_gaps=len(gaps),
        high_severity_count=high_count,
        expected_ready_in_months=expected_ready,
    )


def render_roadmap_markdown(roadmap: ReadinessRoadmap) -> str:
    """Render the roadmap as a markdown block ready to paste
    into the IC binder or a partner email."""
    lines: List[str] = []
    lines.append(f"## Readiness Roadmap — {roadmap.target_name}")
    lines.append("")
    lines.append(
        f"**Readiness score:** "
        f"{roadmap.readiness_score:.2f} / 1.00")
    lines.append(
        f"**Total gaps:** {roadmap.total_gaps} "
        f"({roadmap.high_severity_count} high-severity)")
    lines.append(
        f"**Expected ready-by:** "
        f"{roadmap.expected_ready_in_months} months from start")
    lines.append("")
    for q in roadmap.quarters:
        label = (f"Q{q.quarter_index} (months "
                 f"{q.months_from_now}-{q.months_from_now + 3})")
        lines.append(f"### {label}")
        for g in q.gaps:
            lines.append(
                f"- [{g.severity.upper()}] **{g.title}** "
                f"({g.archetype.value}): {g.description} "
                f"({g.months_to_remediate}mo to fix)")
        lines.append("")
    return "\n".join(lines)
