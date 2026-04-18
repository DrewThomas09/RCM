"""Partner scorecard — the binary must-haves gate.

Every senior partner carries a short list of yes/no tests. These
are not weighted — any ONE failing is typically a pass. The
scorecard:

1. **Scale** — EBITDA ≥ minimum threshold for the fund.
2. **Team** — management assessment above the floor.
3. **Market position** — defensible share or differentiation.
4. **Unit economics** — margin and cash conversion at peer
   median or better.
5. **Balance sheet** — leverage sustainable at stress EBITDA.
6. **Exit path** — clearly articulable banker story.
7. **Thesis integrity** — recurring EBITDA share and thesis
   coherence above floors.

This module runs each check and returns a scorecard with pass/
fail per dimension and a strict all-must-pass gate. Partner note
names which dimensions fail.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ScorecardInputs:
    deal_name: str = "Deal"
    # Scale:
    ebitda_m: float = 0.0
    fund_min_ebitda_m: float = 15.0
    # Team:
    management_score_0_100: int = 70
    team_floor: int = 55
    # Market:
    local_market_share_pct: float = 0.15
    has_coe_or_exclusive: bool = False
    market_floor_share: float = 0.10
    # Unit economics:
    ebitda_margin: float = 0.20
    peer_median_margin: float = 0.18
    cash_conversion: float = 0.80          # FCF / EBITDA
    cash_conversion_floor: float = 0.65
    # Balance sheet:
    leverage: float = 5.5
    stress_coverage: float = 2.2
    coverage_floor: float = 1.5
    # Exit:
    has_articulable_exit_story: bool = True
    exit_story_credibility_0_100: int = 65
    exit_story_floor: int = 50
    # Thesis integrity:
    recurring_ebitda_pct: float = 0.90
    thesis_coherence_0_100: int = 80
    recurring_floor: float = 0.80
    coherence_floor: int = 60


@dataclass
class ScorecardCheck:
    dimension: str
    passed: bool
    actual: str
    floor: str
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "passed": self.passed,
            "actual": self.actual,
            "floor": self.floor,
            "rationale": self.rationale,
        }


@dataclass
class ScorecardReport:
    deal_name: str
    checks: List[ScorecardCheck] = field(default_factory=list)
    all_pass: bool = False
    failed_dimensions: List[str] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_name": self.deal_name,
            "checks": [c.to_dict() for c in self.checks],
            "all_pass": self.all_pass,
            "failed_dimensions": list(self.failed_dimensions),
            "partner_note": self.partner_note,
        }


def run_scorecard(inputs: ScorecardInputs) -> ScorecardReport:
    checks: List[ScorecardCheck] = []

    # 1. Scale.
    scale_ok = inputs.ebitda_m >= inputs.fund_min_ebitda_m
    checks.append(ScorecardCheck(
        dimension="scale",
        passed=scale_ok,
        actual=f"${inputs.ebitda_m:,.1f}M EBITDA",
        floor=f"${inputs.fund_min_ebitda_m:,.1f}M min",
        rationale=("Fund scale discipline — sub-threshold deals eat "
                   "team bandwidth without moving the fund "
                   "mathematically."),
    ))

    # 2. Team.
    team_ok = inputs.management_score_0_100 >= inputs.team_floor
    checks.append(ScorecardCheck(
        dimension="team",
        passed=team_ok,
        actual=f"{inputs.management_score_0_100}/100",
        floor=f"{inputs.team_floor}/100 min",
        rationale=("A good deal with a weak team becomes a bad deal "
                   "in 18 months."),
    ))

    # 3. Market.
    market_ok = (
        inputs.local_market_share_pct >= inputs.market_floor_share
        or inputs.has_coe_or_exclusive
    )
    checks.append(ScorecardCheck(
        dimension="market",
        passed=market_ok,
        actual=(f"{inputs.local_market_share_pct*100:.0f}% share"
                + (" + CoE/exclusive" if inputs.has_coe_or_exclusive
                   else "")),
        floor=(f"{inputs.market_floor_share*100:.0f}% or "
               "differentiation"),
        rationale=("Commodity positioning in healthcare is a race to "
                   "fee-schedule cost."),
    ))

    # 4. Unit economics.
    margin_ok = inputs.ebitda_margin >= inputs.peer_median_margin * 0.85
    cash_ok = inputs.cash_conversion >= inputs.cash_conversion_floor
    unit_econ_ok = margin_ok and cash_ok
    checks.append(ScorecardCheck(
        dimension="unit_economics",
        passed=unit_econ_ok,
        actual=(f"margin {inputs.ebitda_margin*100:.1f}%, "
                f"cash conv {inputs.cash_conversion*100:.0f}%"),
        floor=(f"margin ≥ "
                f"{inputs.peer_median_margin*100*0.85:.1f}% AND cash "
                f"≥ {inputs.cash_conversion_floor*100:.0f}%"),
        rationale=("A good story does not fix bad unit economics."),
    ))

    # 5. Balance sheet.
    bs_ok = (inputs.stress_coverage >= inputs.coverage_floor
             and inputs.leverage <= 7.0)
    checks.append(ScorecardCheck(
        dimension="balance_sheet",
        passed=bs_ok,
        actual=(f"leverage {inputs.leverage:.1f}x, stress coverage "
                f"{inputs.stress_coverage:.1f}x"),
        floor=(f"leverage ≤ 7.0x AND stress coverage ≥ "
                f"{inputs.coverage_floor:.1f}x"),
        rationale=("Capital structure must survive a 10-15% EBITDA "
                   "miss without covenant trip."),
    ))

    # 6. Exit path.
    exit_ok = (inputs.has_articulable_exit_story
               and inputs.exit_story_credibility_0_100
                   >= inputs.exit_story_floor)
    checks.append(ScorecardCheck(
        dimension="exit_path",
        passed=exit_ok,
        actual=(f"credibility {inputs.exit_story_credibility_0_100}/100"
                + (" (articulable)" if inputs.has_articulable_exit_story
                   else " (NOT articulable)")),
        floor=f"≥ {inputs.exit_story_floor}/100 + articulable",
        rationale=("If you can't write the banker's CIM now, you "
                   "don't know what you are buying."),
    ))

    # 7. Thesis integrity.
    thesis_ok = (
        inputs.recurring_ebitda_pct >= inputs.recurring_floor
        and inputs.thesis_coherence_0_100 >= inputs.coherence_floor
    )
    checks.append(ScorecardCheck(
        dimension="thesis_integrity",
        passed=thesis_ok,
        actual=(f"recurring {inputs.recurring_ebitda_pct*100:.0f}%, "
                f"coherence {inputs.thesis_coherence_0_100}/100"),
        floor=(f"recurring ≥ {inputs.recurring_floor*100:.0f}% AND "
                f"coherence ≥ {inputs.coherence_floor}/100"),
        rationale=("Exit multiple only applies to recurring; pillars "
                   "that contradict each other destroy exit multiple."),
    ))

    failed = [c.dimension for c in checks if not c.passed]
    all_pass = len(failed) == 0

    if all_pass:
        note = ("All must-haves pass. This is a buy the partner can "
                "defend on fundamentals alone.")
    elif len(failed) == 1:
        note = (f"One must-have fails: {failed[0]}. That alone is "
                "typically enough to pass. If sponsor conviction is "
                "exceptional, force a remediation plan before IC.")
    else:
        note = (f"{len(failed)} must-haves fail: "
                f"{', '.join(failed)}. Pass. Do not spend partner "
                "time on the remaining diligence.")

    return ScorecardReport(
        deal_name=inputs.deal_name,
        checks=checks,
        all_pass=all_pass,
        failed_dimensions=failed,
        partner_note=note,
    )


def render_scorecard_markdown(r: ScorecardReport) -> str:
    lines = [
        f"# {r.deal_name} — Partner scorecard",
        "",
        f"_{r.partner_note}_",
        "",
        f"- All-pass: **{'yes' if r.all_pass else 'no'}**",
        f"- Failed dimensions: "
        f"{', '.join(r.failed_dimensions) if r.failed_dimensions else '—'}",
        "",
        "| Dimension | Pass | Actual | Floor | Why it matters |",
        "|---|:-:|---|---|---|",
    ]
    for c in r.checks:
        mark = "✓" if c.passed else "✗"
        lines.append(
            f"| {c.dimension} | {mark} | {c.actual} | {c.floor} | "
            f"{c.rationale} |"
        )
    return "\n".join(lines)
