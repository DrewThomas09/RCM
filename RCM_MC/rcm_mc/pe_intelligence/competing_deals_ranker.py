"""Competing deals ranker — which of these do I pick?

A partner frequently has 2-3 deals competing for attention. The
question is not "is each one a buy" — the question is "which one
wins the partnership's time and capital?"

The partner's mental ranking weighs:

- Expected return (MOIC + IRR) per deal.
- Quality of the thesis (coherence + pricing power + management).
- Downside protection (bear case, margin of safety).
- Fund-fit (does this move the fund's PME story?).
- Execution burden (competing ops partner / team bandwidth).
- Timing (which one is most time-sensitive).

Output: rank + head-to-head commentary + "if I can only do one"
recommendation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DealSnapshot:
    name: str
    base_moic: float = 2.5
    base_irr: float = 0.22
    bear_moic: float = 1.5
    thesis_coherence_0_100: int = 75
    pricing_power_0_100: int = 60
    management_score_0_100: int = 70
    ebitda_m: float = 50.0
    fund_pme_boost: bool = False             # materially moves PME
    execution_burden_0_100: int = 50         # higher = more burden
    time_sensitivity_weeks: int = 12         # how soon it needs decision
    scorecard_fails: int = 0


@dataclass
class DealRanking:
    name: str
    rank: int
    composite_score_0_100: int
    return_component: int
    quality_component: int
    downside_component: int
    fit_component: int
    timing_component: int
    partner_commentary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "rank": self.rank,
            "composite_score_0_100": self.composite_score_0_100,
            "return_component": self.return_component,
            "quality_component": self.quality_component,
            "downside_component": self.downside_component,
            "fit_component": self.fit_component,
            "timing_component": self.timing_component,
            "partner_commentary": self.partner_commentary,
        }


@dataclass
class RankingReport:
    rankings: List[DealRanking] = field(default_factory=list)
    if_one_pick: str = ""
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rankings": [r.to_dict() for r in self.rankings],
            "if_one_pick": self.if_one_pick,
            "partner_note": self.partner_note,
        }


def _score_return(d: DealSnapshot) -> int:
    # Scale base IRR 0-40% → 0-100 linearly.
    score = int(round(d.base_irr * 250))
    return max(0, min(100, score))


def _score_quality(d: DealSnapshot) -> int:
    # Weighted average of coherence / pricing / management.
    return int(round(
        0.40 * d.thesis_coherence_0_100
        + 0.30 * d.pricing_power_0_100
        + 0.30 * d.management_score_0_100
    ))


def _score_downside(d: DealSnapshot) -> int:
    # Bear MOIC 1.0x = 40; 2.0x = 100; 0.5x = 0.
    raw = (d.bear_moic - 0.5) * 60.0
    return max(0, min(100, int(round(raw))))


def _score_fit(d: DealSnapshot) -> int:
    score = 50
    if d.fund_pme_boost:
        score += 20
    if d.scorecard_fails >= 2:
        score -= 40
    elif d.scorecard_fails == 1:
        score -= 15
    return max(0, min(100, score))


def _score_timing(d: DealSnapshot) -> int:
    # Closer to decision = higher urgency score.
    if d.time_sensitivity_weeks <= 4:
        score = 90
    elif d.time_sensitivity_weeks <= 8:
        score = 70
    elif d.time_sensitivity_weeks <= 16:
        score = 55
    else:
        score = 40
    # Execution burden drags fit.
    score -= (d.execution_burden_0_100 - 50) // 3
    return max(0, min(100, score))


WEIGHTS = {
    "return": 0.30,
    "quality": 0.25,
    "downside": 0.20,
    "fit": 0.15,
    "timing": 0.10,
}


def rank_deals(deals: List[DealSnapshot]) -> RankingReport:
    rankings: List[DealRanking] = []
    for d in deals:
        rc = _score_return(d)
        qc = _score_quality(d)
        dc = _score_downside(d)
        fc = _score_fit(d)
        tc = _score_timing(d)
        composite = int(round(
            rc * WEIGHTS["return"]
            + qc * WEIGHTS["quality"]
            + dc * WEIGHTS["downside"]
            + fc * WEIGHTS["fit"]
            + tc * WEIGHTS["timing"]
        ))
        rankings.append(DealRanking(
            name=d.name, rank=0,
            composite_score_0_100=composite,
            return_component=rc, quality_component=qc,
            downside_component=dc, fit_component=fc,
            timing_component=tc,
            partner_commentary=_deal_commentary(d, rc, qc, dc, fc, tc),
        ))

    rankings.sort(key=lambda r: r.composite_score_0_100, reverse=True)
    for i, r in enumerate(rankings):
        r.rank = i + 1

    if not rankings:
        return RankingReport(if_one_pick="",
                              partner_note="No deals provided.")

    winner = rankings[0]
    if_one = winner.name

    if len(rankings) >= 2:
        runner_up = rankings[1]
        gap = winner.composite_score_0_100 - runner_up.composite_score_0_100
        if gap >= 15:
            note = (f"Clear winner: **{winner.name}** "
                    f"({winner.composite_score_0_100} vs "
                    f"{runner_up.composite_score_0_100}). The partner's "
                    "time goes here — others are deal-team-level.")
        elif gap >= 5:
            note = (f"{winner.name} edges {runner_up.name} "
                    f"({winner.composite_score_0_100} vs "
                    f"{runner_up.composite_score_0_100}). Close "
                    "enough that a flipped downside scenario or "
                    "timing pressure could shift the call.")
        else:
            note = (f"Effective tie between {winner.name} and "
                    f"{runner_up.name} "
                    f"({winner.composite_score_0_100} vs "
                    f"{runner_up.composite_score_0_100}). Use the "
                    "execution-burden tiebreaker: pick the one the "
                    "ops-partner bench is ready to own.")
    else:
        note = (f"Single deal — no ranking needed. Partner attention "
                "on {winner.name}.")

    return RankingReport(
        rankings=rankings,
        if_one_pick=if_one,
        partner_note=note,
    )


def _deal_commentary(d: DealSnapshot, rc: int, qc: int, dc: int,
                      fc: int, tc: int) -> str:
    bits: List[str] = []
    if rc >= 75:
        bits.append("return is compelling")
    elif rc < 50:
        bits.append("return is thin vs hurdle")
    if qc >= 75:
        bits.append("thesis quality is high")
    elif qc < 55:
        bits.append("quality concerns")
    if dc >= 70:
        bits.append("downside is protected")
    elif dc < 40:
        bits.append("bear case is painful")
    if fc < 40:
        bits.append("scorecard issues drag fit")
    if tc >= 80:
        bits.append("time-sensitive")
    if not bits:
        bits.append("mid-range deal")
    return "; ".join(bits).capitalize() + "."


def render_ranking_markdown(r: RankingReport) -> str:
    lines = [
        "# Competing deals ranking",
        "",
        f"_{r.partner_note}_",
        "",
        f"- **If I can only do one:** {r.if_one_pick}",
        "",
        "| Rank | Deal | Composite | Return | Quality | Downside | Fit | Timing |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for ranked in r.rankings:
        lines.append(
            f"| {ranked.rank} | {ranked.name} | "
            f"{ranked.composite_score_0_100} | "
            f"{ranked.return_component} | "
            f"{ranked.quality_component} | "
            f"{ranked.downside_component} | "
            f"{ranked.fit_component} | "
            f"{ranked.timing_component} |"
        )
    lines.extend(["", "## Commentary", ""])
    for ranked in r.rankings:
        lines.append(f"- **{ranked.name}**: {ranked.partner_commentary}")
    return "\n".join(lines)
