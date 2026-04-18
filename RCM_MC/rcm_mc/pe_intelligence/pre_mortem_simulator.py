"""Pre-mortem simulator — imagine the failure before you close.

Partner statement: "Before I commit, I write the post-
mortem. If I can picture the write-up, the deal has a
named failure mode. That's when I either fix it or walk."

`post_mortem.py` is a **look-back** template for exited
deals. This module is the **look-forward** mirror: given
a deal's signals today, simulate the post-mortem that
would be written in Year 5 if the deal fails.

### Why partners do this

Decision literature calls it "prospective hindsight":
imagining a failure forces concrete attribution instead
of hand-wavy risk language. A partner saying "the team
failed" doesn't prevent anything. A partner saying "in
Year 2, the CFO missed three forecasts and we entered
covenant cure; by Year 3, the lender pushed a sale" is
testable — and avoidable.

### How this module simulates

Given inputs:

- **Thesis** — the headline claim.
- **Pattern matches** — failure patterns that fire.
- **Thesis-chain status** — which downstream links are
  unresolved or contradicted.
- **Regulatory exposure** — hold-period shock schedule
  worst year.
- **Subsector** — for subsector-specific failure modes.
- **Management posture** — whether team is retained /
  rolled / aligned.

It composes a **dated attribution chain**:

- Y1: where the first crack appears (small miss, early
  warning signal).
- Y2: where the crack widens (covenant, retention,
  regulatory).
- Y3: where the thesis breaks (named lever fails).
- Y4: where ops / structure / lender forces action.
- Exit: the sale process, the write-off, or the
  continuation vehicle.

Each year carries:
- **What happened** — specific event.
- **Root-cause signal** — what we should have seen
  earlier.
- **Fix we didn't make** — the missed mitigation.

### Partner commentary

The module emits a partner note: "pre-mortem reads
plausibly on X, Y, Z axes. Mitigation required before
IC." If the pre-mortem reads thinly (no strong failure
signals), the partner proceeds.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PreMortemInputs:
    thesis: str = ""                       # e.g., "denial_reduction"
    thesis_contradicted_links: List[str] = field(
        default_factory=list
    )
    thesis_unresolved_links: List[str] = field(
        default_factory=list
    )
    pattern_matches: List[str] = field(default_factory=list)
    failure_archetype_matches: List[str] = field(
        default_factory=list
    )
    worst_year_leverage: Optional[float] = None
    covenant_max_leverage: Optional[float] = None
    worst_shock_year: Optional[int] = None
    worst_shock_cumulative_m: Optional[float] = None
    subsector: str = ""
    management_retained: bool = True
    management_rolled_equity: bool = False
    key_retention_signed: bool = True
    base_ebitda_m: Optional[float] = None
    debt_outstanding_m: Optional[float] = None
    hold_start_year: int = 2026


@dataclass
class PreMortemYear:
    year: int
    event: str
    root_cause_signal: str
    fix_missed: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year,
            "event": self.event,
            "root_cause_signal": self.root_cause_signal,
            "fix_missed": self.fix_missed,
        }


@dataclass
class PreMortemReport:
    thesis: str
    years: List[PreMortemYear] = field(default_factory=list)
    strength: str = "thin"       # "thin" / "moderate" / "strong"
    partner_note: str = ""
    exit_outcome: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "thesis": self.thesis,
            "years": [y.to_dict() for y in self.years],
            "strength": self.strength,
            "partner_note": self.partner_note,
            "exit_outcome": self.exit_outcome,
        }


# ── Year-by-year event builders ────────────────────────

def _y1_event(inputs: PreMortemInputs) -> Optional[PreMortemYear]:
    """Y1: first crack appears."""
    if (inputs.thesis == "denial_reduction" and
            "year1_cash_release_share" in
            " ".join(inputs.thesis_contradicted_links).lower()):
        return PreMortemYear(
            year=inputs.hold_start_year + 1,
            event=("Year-1 EBITDA beat on paper — 80% from A/R "
                   "catch-up release, not run-rate. Forward "
                   "guidance reset in Q4."),
            root_cause_signal=(
                "Y1 cash-release share > 40% flagged at "
                "diligence; we accepted management's framing."
            ),
            fix_missed=(
                "Required pro-forma run-rate reconciliation "
                "before IC vote."
            ),
        )
    if "fix_denials_in_12_months" in inputs.pattern_matches:
        return PreMortemYear(
            year=inputs.hold_start_year + 1,
            event=(
                "Denial-rate program delivered 150 bps vs. "
                "seller's 700 bps target. EBITDA plan missed "
                "by 15%."
            ),
            root_cause_signal=(
                "Historical denial programs cap at 200-300 "
                "bps/yr; seller promised 700 in 12 months."
            ),
            fix_missed=(
                "Should have modeled 200 bps/yr with 50% "
                "realization, not trust seller forecast."
            ),
        )
    if not inputs.key_retention_signed:
        return PreMortemYear(
            year=inputs.hold_start_year + 1,
            event=(
                "Key-15 retention unraveled — three principal "
                "clinicians / operators left in Y1 post-close."
            ),
            root_cause_signal=(
                "Retention agreements were not signed at close."
            ),
            fix_missed=(
                "Should have made key-15 signed retention a "
                "closing condition, not a best-efforts item."
            ),
        )
    return None


def _y2_event(inputs: PreMortemInputs) -> Optional[PreMortemYear]:
    """Y2: crack widens."""
    # Covenant trip signal.
    if (inputs.worst_year_leverage is not None
            and inputs.covenant_max_leverage is not None
            and inputs.worst_year_leverage >
                inputs.covenant_max_leverage):
        return PreMortemYear(
            year=inputs.hold_start_year + 2,
            event=(
                f"Leverage hit "
                f"{inputs.worst_year_leverage:.2f}x vs. "
                f"{inputs.covenant_max_leverage:.2f}x covenant. "
                "Cure required. Sponsor injected equity; base "
                "MOIC reset from 2.5x target to 1.8x."
            ),
            root_cause_signal=(
                "Hold-period shock schedule projected worst-"
                "year leverage above cov package. We accepted "
                "seller's covenant ask."
            ),
            fix_missed=(
                "Should have demanded max leverage ≥ worst-"
                "year projection + 0.5x cushion."
            ),
        )
    if "back_office_integration_optimism" in \
            inputs.failure_archetype_matches:
        return PreMortemYear(
            year=inputs.hold_start_year + 2,
            event=(
                "EHR consolidation project ran 18 months "
                "long. Integration cost 2x plan; Y2 synergies "
                "never materialized."
            ),
            root_cause_signal=(
                "Multi-EHR platform with Y1 synergy assumption "
                "in base case."
            ),
            fix_missed=(
                "Should have modeled synergy ramp Y2-Y4 with "
                "40%+ integration cost load."
            ),
        )
    return None


def _y3_event(inputs: PreMortemInputs) -> Optional[PreMortemYear]:
    """Y3: thesis breaks."""
    if (inputs.worst_shock_year is not None
            and inputs.worst_shock_cumulative_m is not None
            and inputs.worst_shock_cumulative_m >
                0.10 * (inputs.base_ebitda_m or 1.0)):
        return PreMortemYear(
            year=inputs.worst_shock_year,
            event=(
                f"Regulatory shocks cumulative $"
                f"{inputs.worst_shock_cumulative_m:,.1f}M hit "
                f"in {inputs.worst_shock_year}. EBITDA vs. "
                "entry plan down "
                f"{inputs.worst_shock_cumulative_m / max(0.01, inputs.base_ebitda_m or 1.0) * 100:.0f}%."
            ),
            root_cause_signal=(
                "Shock schedule baseline projected "
                f"${inputs.worst_shock_cumulative_m:,.1f}M "
                "cumulative, already known at diligence."
            ),
            fix_missed=(
                "Entry price should have been discounted "
                "for regulatory-run-rate EBITDA, not stated."
            ),
        )
    if inputs.thesis == "rollup_consolidation" and \
            "signed_lois_count" in \
            " ".join(inputs.thesis_unresolved_links).lower():
        return PreMortemYear(
            year=inputs.hold_start_year + 3,
            event=(
                "Platform did only 2 add-on acquisitions vs. "
                "plan of 8. Cap rate moved against us; "
                "pipeline claims didn't convert."
            ),
            root_cause_signal=(
                "LOI pipeline was 'universe' not 'signed' at "
                "intake. We took management's word."
            ),
            fix_missed=(
                "Should have required ≥ 3 signed LOIs before "
                "closing, not 'active pipeline'."
            ),
        )
    if "ma_pass_through_over_reliance" in \
            inputs.failure_archetype_matches:
        return PreMortemYear(
            year=inputs.hold_start_year + 3,
            event=(
                "MA benchmark cuts followed FFS cuts with 18-"
                "month lag. Operator had no risk-contracting "
                "chassis; margin compressed 400 bps."
            ),
            root_cause_signal=(
                "MA exposure > 20% with no risk-contract track "
                "record flagged at intake."
            ),
            fix_missed=(
                "Should have priced as FFS-correlated; no MA "
                "credit without ops team ready."
            ),
        )
    return None


def _y4_event(inputs: PreMortemInputs) -> Optional[PreMortemYear]:
    """Y4: ops / lender / structure forces action."""
    if "turnaround_without_operator" in \
            inputs.failure_archetype_matches:
        return PreMortemYear(
            year=inputs.hold_start_year + 4,
            event=(
                "CEO transition triggered in Q3. Search took "
                "9 months; Y5 stabilization cost $8M in "
                "severance + recruiter + interim."
            ),
            root_cause_signal=(
                "Thesis required ops turnaround but team on "
                "site was team that created the problem."
            ),
            fix_missed=(
                "Should have shipped with a CEO search; "
                "budgeted $5M operator-placement at close."
            ),
        )
    if not inputs.management_rolled_equity:
        return PreMortemYear(
            year=inputs.hold_start_year + 4,
            event=(
                "Management incentive misalignment — no "
                "rollover equity meant team saw payoff at "
                "close, not at exit. Operator pace dropped."
            ),
            root_cause_signal=(
                "No meaningful rollover at close. Incentives "
                "were retention bonuses only."
            ),
            fix_missed=(
                "Should have required 15-25% rollover for "
                "founder / 10% for senior team."
            ),
        )
    return None


def _exit_event(inputs: PreMortemInputs) -> Optional[PreMortemYear]:
    """The exit: sale, write-off, continuation vehicle."""
    # Decide by severity:
    failure_count = (
        len(inputs.thesis_contradicted_links)
        + len(inputs.failure_archetype_matches)
        + (1 if inputs.worst_year_leverage and
           inputs.covenant_max_leverage and
           inputs.worst_year_leverage >
           inputs.covenant_max_leverage else 0)
    )
    exit_year = inputs.hold_start_year + 5
    if failure_count >= 3:
        return PreMortemYear(
            year=exit_year,
            event=(
                "Exit: sponsor process launched and broke "
                "after one round. Wrote down to 0.8x MOIC; "
                "sold to a distressed buyer at 5.5x EBITDA "
                "(vs. 11x entry)."
            ),
            root_cause_signal=(
                "Multiple failure modes (thesis break + "
                "covenant cure + operator gap) stacked over "
                "the hold."
            ),
            fix_missed=(
                "Should have walked at LOI when failure-"
                "archetype matches ≥ 3."
            ),
        )
    if failure_count >= 1:
        return PreMortemYear(
            year=exit_year,
            event=(
                "Exit: secondary sale to a continuation "
                "vehicle at 1.6x MOIC (vs. 2.5x plan). "
                "Hold extended 18 months to achieve."
            ),
            root_cause_signal=(
                "Named failure mode unmitigated at close."
            ),
            fix_missed=(
                "Targeted mitigation required at IC "
                "was best-efforts, not closing condition."
            ),
        )
    return None


def simulate_pre_mortem(
    inputs: PreMortemInputs,
) -> PreMortemReport:
    years: List[PreMortemYear] = []
    for builder in (_y1_event, _y2_event, _y3_event,
                    _y4_event, _exit_event):
        y = builder(inputs)
        if y is not None:
            years.append(y)

    # Strength of the pre-mortem.
    if len(years) >= 4:
        strength = "strong"
    elif len(years) >= 2:
        strength = "moderate"
    else:
        strength = "thin"

    # Derive exit outcome narrative.
    exit_ev = years[-1] if years else None
    exit_outcome = (
        exit_ev.event if exit_ev else
        "No strong failure narrative constructed."
    )

    if strength == "strong":
        note = (
            f"Pre-mortem reads strongly — {len(years)} dated "
            "failure events line up against the current "
            "diligence posture. Partner: do not close "
            "without explicit mitigation on each."
        )
    elif strength == "moderate":
        note = (
            f"Pre-mortem reads moderately — {len(years)} "
            "events constructable. Partner: document "
            "mitigation for each in the IC memo or don't "
            "proceed."
        )
    else:
        note = (
            "Pre-mortem reads thin — no strong failure "
            "signals constructable. Partner: proceed on "
            "current thesis."
        )

    return PreMortemReport(
        thesis=inputs.thesis,
        years=years,
        strength=strength,
        partner_note=note,
        exit_outcome=exit_outcome,
    )


def render_pre_mortem_markdown(
    r: PreMortemReport,
) -> str:
    lines = [
        f"# Pre-mortem — `{r.thesis or 'thesis'}`",
        "",
        f"**Strength:** `{r.strength}`",
        "",
        f"_{r.partner_note}_",
        "",
    ]
    for y in r.years:
        lines.append(f"## {y.year}")
        lines.append(f"- **What happens:** {y.event}")
        lines.append(f"- **Root-cause signal:** "
                     f"{y.root_cause_signal}")
        lines.append(f"- **Fix we missed:** {y.fix_missed}")
        lines.append("")
    return "\n".join(lines)
