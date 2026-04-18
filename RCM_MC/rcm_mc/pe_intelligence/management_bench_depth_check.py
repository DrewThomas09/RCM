"""Management bench depth check — key-person risk beyond CEO.

Partner statement: "The CEO is always named. But what
happens if the CFO walks at 6 months? If the COO is new?
If no direct reports own a P&L? That's where the real
key-person risk lives — not in the CEO slot."

Distinct from `management_assessment` (overall quality),
`management_forecast_reliability` (forecast track record),
`management_rollover_equity_designer` (rollover size).
This module checks **bench depth** — if a named seat
empties post-close, is there someone behind them?

### 7 dimensions scored

1. **ceo_rollover_pct** — skin-in-the-game signal.
2. **cfo_successor_identified** — CFO has named #2?
3. **coo_in_role_gt_12mo** — COO past honeymoon?
4. **pnl_owning_direct_reports_count** — distributed
   accountability.
5. **key_person_dependency_count** — named flight-risk
   executives.
6. **board_operating_experience_count** — independent
   directors with relevant ops experience.
7. **exec_retention_signed_at_close** — contracts vs
   handshake.

### Bench depth tiers

- **deep** (score ≥ 6) — post-close can absorb 1-2
  departures without thesis reset.
- **adequate** (4-5) — 1 departure manageable; 2 in
  same year is trouble.
- **thin** (2-3) — single departure resets plan; ship
  with a search plan.
- **critical** (0-1) — no bench; every seat is single-
  threaded. Partner: restructure or walk.

### Key-person risk list

For each dimension that fails, emit a named risk with a
partner counter. These feed the 100-day-plan and the
LOI-level retention-condition language.

### Why this matters

Partners' scar tissue: most deal-level blow-ups trace to
a named seat failing in year 1-2. A "strong CEO" with a
thin bench is a one-shot roll. Bench depth turns the team
into a system.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BenchDepthInputs:
    ceo_name: str = ""
    ceo_rollover_pct: float = 0.0          # 0-1
    cfo_successor_identified: bool = False
    coo_name: str = ""
    coo_months_in_role: int = 0
    pnl_owning_direct_reports_count: int = 0
    total_direct_reports: int = 0
    key_person_dependencies: List[str] = field(default_factory=list)
    board_operating_director_count: int = 0
    exec_retention_signed_at_close: bool = False


@dataclass
class BenchDimension:
    name: str
    passed: bool
    partner_comment: str


@dataclass
class KeyPersonRisk:
    seat: str
    description: str
    partner_counter: str


@dataclass
class BenchDepthReport:
    score: int                             # 0-7
    tier: str                              # deep/adequate/thin/critical
    dimensions: List[BenchDimension] = field(default_factory=list)
    key_person_risks: List[KeyPersonRisk] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "tier": self.tier,
            "dimensions": [
                {"name": d.name, "passed": d.passed,
                 "partner_comment": d.partner_comment}
                for d in self.dimensions
            ],
            "key_person_risks": [
                {"seat": k.seat,
                 "description": k.description,
                 "partner_counter": k.partner_counter}
                for k in self.key_person_risks
            ],
            "partner_note": self.partner_note,
        }


def check_bench_depth(inputs: BenchDepthInputs) -> BenchDepthReport:
    dims: List[BenchDimension] = []
    risks: List[KeyPersonRisk] = []

    # 1. CEO rollover ≥ 15%.
    ceo_ok = inputs.ceo_rollover_pct >= 0.15
    dims.append(BenchDimension(
        name="ceo_rollover_pct",
        passed=ceo_ok,
        partner_comment=(
            f"CEO rollover {inputs.ceo_rollover_pct*100:.0f}% "
            "is meaningful skin-in-the-game."
            if ceo_ok else
            f"CEO rollover only "
            f"{inputs.ceo_rollover_pct*100:.0f}% — partner "
            "wants ≥ 15% for alignment."
        ),
    ))
    if not ceo_ok:
        risks.append(KeyPersonRisk(
            seat="ceo",
            description=(
                f"CEO rollover is "
                f"{inputs.ceo_rollover_pct*100:.0f}%, "
                "below the 15% alignment threshold."
            ),
            partner_counter=(
                "Negotiate rollover ≥ 15% or structure "
                "performance-based equity vesting."
            ),
        ))

    # 2. CFO successor identified.
    dims.append(BenchDimension(
        name="cfo_successor_identified",
        passed=inputs.cfo_successor_identified,
        partner_comment=(
            "CFO successor named — bench visible."
            if inputs.cfo_successor_identified else
            "No CFO successor — partner: if CFO walks, "
            "we're external-search from day 1."
        ),
    ))
    if not inputs.cfo_successor_identified:
        risks.append(KeyPersonRisk(
            seat="cfo",
            description=(
                "No identified CFO successor. If CFO "
                "departs within 24 months, plan slips."
            ),
            partner_counter=(
                "Require retention package for current "
                "CFO + name a controller-level successor "
                "in the 100-day plan."
            ),
        ))

    # 3. COO > 12 months in role.
    coo_ok = inputs.coo_months_in_role >= 12
    dims.append(BenchDimension(
        name="coo_in_role_gt_12mo",
        passed=coo_ok,
        partner_comment=(
            f"COO {inputs.coo_months_in_role} months in "
            "role; past honeymoon."
            if coo_ok else
            f"COO only {inputs.coo_months_in_role} months "
            "in role — operating cadence not yet proven."
        ),
    ))
    if not coo_ok and inputs.coo_name:
        risks.append(KeyPersonRisk(
            seat="coo",
            description=(
                f"COO {inputs.coo_name} in role < 12 months."
            ),
            partner_counter=(
                "Interview direct reports independently; "
                "assess whether COO has real operating "
                "cadence or is still in listening mode."
            ),
        ))

    # 4. ≥ 3 direct reports own a P&L (distributed accountability).
    pnl_ok = inputs.pnl_owning_direct_reports_count >= 3
    dims.append(BenchDimension(
        name="pnl_owning_direct_reports_count",
        passed=pnl_ok,
        partner_comment=(
            f"{inputs.pnl_owning_direct_reports_count} "
            "direct reports own a P&L — distributed "
            "accountability."
            if pnl_ok else
            f"Only {inputs.pnl_owning_direct_reports_count} "
            "P&L-owning direct reports — plan lives in "
            "CEO's head."
        ),
    ))
    if not pnl_ok:
        risks.append(KeyPersonRisk(
            seat="operating_team",
            description=(
                "Fewer than 3 direct reports own a P&L line."
            ),
            partner_counter=(
                "Day-1 action: redesign org around P&L "
                "owners; CEO shouldn't be the only person "
                "with the plan."
            ),
        ))

    # 5. Key-person dependencies ≤ 2.
    key_deps_ok = len(inputs.key_person_dependencies) <= 2
    dims.append(BenchDimension(
        name="key_person_dependency_count",
        passed=key_deps_ok,
        partner_comment=(
            f"{len(inputs.key_person_dependencies)} key-"
            "person dependencies — manageable."
            if key_deps_ok else
            f"{len(inputs.key_person_dependencies)} key-"
            "person dependencies — concentration risk."
        ),
    ))
    if not key_deps_ok:
        risks.append(KeyPersonRisk(
            seat="key_persons",
            description=(
                f"Named key-person dependencies: "
                f"{', '.join(inputs.key_person_dependencies[:3])}."
            ),
            partner_counter=(
                "Sign retention + non-compete for each at "
                "close. Do not accept 'best efforts' on "
                "retention for critical seats."
            ),
        ))

    # 6. Board operating directors ≥ 1.
    board_ok = inputs.board_operating_director_count >= 1
    dims.append(BenchDimension(
        name="board_operating_experience_count",
        passed=board_ok,
        partner_comment=(
            f"{inputs.board_operating_director_count} "
            "operating director(s) on board."
            if board_ok else
            "No independent operating directors — partner: "
            "plan to recruit one in first 6 months."
        ),
    ))

    # 7. Exec retention signed at close.
    dims.append(BenchDimension(
        name="exec_retention_signed_at_close",
        passed=inputs.exec_retention_signed_at_close,
        partner_comment=(
            "Exec retention contracts signed at close."
            if inputs.exec_retention_signed_at_close else
            "Handshake retention only — partner: walk-"
            "right if key-15 departs."
        ),
    ))
    if not inputs.exec_retention_signed_at_close:
        risks.append(KeyPersonRisk(
            seat="retention_contracts",
            description=(
                "No signed retention contracts for key-"
                "15 executives."
            ),
            partner_counter=(
                "Make signed retention a closing "
                "condition, not a best-effort obligation."
            ),
        ))

    score = sum(1 for d in dims if d.passed)
    if score >= 6:
        tier = "deep"
        note = (
            "Bench is deep. Post-close can absorb 1-2 "
            "departures without thesis reset. Partner: "
            "proceed; retention budget can focus on "
            "growth hires."
        )
    elif score >= 4:
        tier = "adequate"
        note = (
            f"Bench adequate ({score}/7). One departure "
            "manageable; two in same year is trouble. "
            "Partner: price in a $3-5M retention budget."
        )
    elif score >= 2:
        tier = "thin"
        note = (
            f"Bench thin ({score}/7). Single departure "
            "resets plan. Partner: ship with an "
            "operator-placement plan and reserve $5M+."
        )
    else:
        tier = "critical"
        note = (
            f"Bench critical ({score}/7). Every seat "
            "single-threaded. Partner: restructure team "
            "in diligence or walk."
        )

    return BenchDepthReport(
        score=score,
        tier=tier,
        dimensions=dims,
        key_person_risks=risks,
        partner_note=note,
    )


def render_bench_depth_markdown(
    r: BenchDepthReport,
) -> str:
    lines = [
        "# Management bench depth check",
        "",
        f"**Tier:** `{r.tier}` ({r.score}/7)",
        "",
        f"_{r.partner_note}_",
        "",
        "| Dimension | Passed | Partner comment |",
        "|---|---|---|",
    ]
    for d in r.dimensions:
        check = "✓" if d.passed else "✗"
        lines.append(
            f"| {d.name} | {check} | {d.partner_comment} |"
        )
    if r.key_person_risks:
        lines.append("")
        lines.append("## Key-person risks")
        lines.append("")
        for k in r.key_person_risks:
            lines.append(f"### {k.seat}")
            lines.append(f"- **Risk:** {k.description}")
            lines.append(f"- **Partner counter:** "
                         f"{k.partner_counter}")
            lines.append("")
    return "\n".join(lines)
