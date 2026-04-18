"""Exit alternative comparator — sell now vs. hold vs. recap.

Partner statement: "Every board meeting I ask the same
question: if we had to decide today, sell / hold /
recap / continuation vehicle — which one wins on risk-
adjusted MOIC? The answer changes every year. I want it
on one page."

Mid-hold, partners compare five alternatives explicitly.
The right answer depends on current EV, remaining hold
runway, debt paydown capacity, thesis maturity, and the
LP clock.

### 5 alternatives modeled

1. **sell_strategic_now** — current EV × strategic
   premium, net of advisory fees.
2. **sell_sponsor_secondary** — current EV at PE-to-PE
   multiple, net of fees.
3. **continuation_vehicle** — current sponsor recaps
   own portco; GP-led secondary at fairness-opinion
   mark.
4. **dividend_recap_and_hold** — lever up 3-4x to pay
   dividend + continue underwriting thesis to planned
   exit.
5. **hold_and_build** — do nothing; ride planned thesis
   to exit year.

### Output

MOIC + time-to-exit per alternative + partner-voice
commentary on the trade-off. Named "winning"
alternative given the inputs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExitAlternativesInputs:
    entry_equity_m: float
    entry_ebitda_m: float
    entry_multiple: float
    current_ebitda_m: float
    current_multiple: float
    current_debt_m: float
    years_into_hold: float
    planned_exit_year: float
    planned_exit_ebitda_m: float
    planned_exit_multiple: float
    planned_exit_debt_m: float = 0.0
    strategic_premium_pct: float = 0.10        # typical +10% over PE
    secondary_mark_discount_pct: float = 0.05  # PE-to-PE usually below strategic
    continuation_fairness_opinion_pct: float = 0.03  # CV premium over PE secondary
    advisory_fees_pct_of_ev: float = 0.015
    dividend_recap_leverage_multiple: float = 6.0
    dividend_recap_dividend_pct_of_equity: float = 0.40


@dataclass
class Alternative:
    name: str
    equity_proceeds_m: float
    moic: float
    time_to_exit_yrs: float
    partner_commentary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "equity_proceeds_m": self.equity_proceeds_m,
            "moic": self.moic,
            "time_to_exit_yrs": self.time_to_exit_yrs,
            "partner_commentary": self.partner_commentary,
        }


@dataclass
class ExitAlternativesReport:
    alternatives: List[Alternative] = field(default_factory=list)
    winning_alternative_name: str = ""
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alternatives": [a.to_dict()
                             for a in self.alternatives],
            "winning_alternative_name":
                self.winning_alternative_name,
            "partner_note": self.partner_note,
        }


def compare_exit_alternatives(
    inputs: ExitAlternativesInputs,
) -> ExitAlternativesReport:
    entry_eq = max(0.01, inputs.entry_equity_m)
    current_ev = (
        inputs.current_ebitda_m * inputs.current_multiple
    )
    current_equity_gross = (
        current_ev - inputs.current_debt_m
    )
    advisory_drag_pct = inputs.advisory_fees_pct_of_ev

    alternatives: List[Alternative] = []

    # 1. Strategic sale now.
    strategic_ev = current_ev * (
        1.0 + inputs.strategic_premium_pct
    )
    strategic_equity = max(
        0.0,
        strategic_ev * (1.0 - advisory_drag_pct)
        - inputs.current_debt_m,
    )
    strategic_moic = strategic_equity / entry_eq
    alternatives.append(Alternative(
        name="sell_strategic_now",
        equity_proceeds_m=round(strategic_equity, 2),
        moic=round(strategic_moic, 3),
        time_to_exit_yrs=0.25,
        partner_commentary=(
            f"Strategic premium +{inputs.strategic_premium_pct*100:.0f}%; "
            "fast close; no further execution risk."
        ),
    ))

    # 2. Sponsor secondary.
    secondary_ev = current_ev * (
        1.0 - inputs.secondary_mark_discount_pct
    )
    secondary_equity = max(
        0.0,
        secondary_ev * (1.0 - advisory_drag_pct)
        - inputs.current_debt_m,
    )
    secondary_moic = secondary_equity / entry_eq
    alternatives.append(Alternative(
        name="sell_sponsor_secondary",
        equity_proceeds_m=round(secondary_equity, 2),
        moic=round(secondary_moic, 3),
        time_to_exit_yrs=0.5,
        partner_commentary=(
            "PE-to-PE sale; no strategic premium but "
            "faster than continuation."
        ),
    ))

    # 3. Continuation vehicle.
    cv_ev = current_ev * (
        1.0 + inputs.continuation_fairness_opinion_pct
    )
    cv_equity = max(
        0.0,
        cv_ev * (1.0 - advisory_drag_pct)
        - inputs.current_debt_m,
    )
    cv_moic = cv_equity / entry_eq
    alternatives.append(Alternative(
        name="continuation_vehicle",
        equity_proceeds_m=round(cv_equity, 2),
        moic=round(cv_moic, 3),
        time_to_exit_yrs=1.0,
        partner_commentary=(
            "GP-led secondary at fairness opinion; LP "
            "liquidity option; sponsor extends hold."
        ),
    ))

    # 4. Dividend recap + hold.
    target_debt_post = (
        inputs.current_ebitda_m
        * inputs.dividend_recap_leverage_multiple
    )
    recap_dividend = max(
        0.0,
        target_debt_post - inputs.current_debt_m,
    )
    recap_dividend *= inputs.dividend_recap_dividend_pct_of_equity
    # Hold to planned exit, then sell.
    planned_exit_ev = (
        inputs.planned_exit_ebitda_m
        * inputs.planned_exit_multiple
    )
    planned_exit_equity = max(
        0.0,
        planned_exit_ev - inputs.planned_exit_debt_m
        - target_debt_post,
    )
    recap_total = recap_dividend + planned_exit_equity
    recap_moic = recap_total / entry_eq
    recap_time = max(0.5,
                      inputs.planned_exit_year -
                      inputs.years_into_hold)
    alternatives.append(Alternative(
        name="dividend_recap_and_hold",
        equity_proceeds_m=round(recap_total, 2),
        moic=round(recap_moic, 3),
        time_to_exit_yrs=round(recap_time, 2),
        partner_commentary=(
            f"Lever to "
            f"{inputs.dividend_recap_leverage_multiple:.1f}x; "
            f"dividend ${recap_dividend:,.1f}M + hold to "
            "planned exit."
        ),
    ))

    # 5. Hold and build.
    hold_equity = max(
        0.0,
        planned_exit_ev - inputs.planned_exit_debt_m,
    )
    hold_moic = hold_equity / entry_eq
    hold_time = max(0.5,
                     inputs.planned_exit_year -
                     inputs.years_into_hold)
    alternatives.append(Alternative(
        name="hold_and_build",
        equity_proceeds_m=round(hold_equity, 2),
        moic=round(hold_moic, 3),
        time_to_exit_yrs=round(hold_time, 2),
        partner_commentary=(
            f"Ride thesis to Y{inputs.planned_exit_year:.0f}; "
            "no structural change."
        ),
    ))

    # "Winning" alternative = highest MOIC per year
    # (IRR-adjusted).
    def per_year(a: Alternative) -> float:
        t = max(0.25, a.time_to_exit_yrs)
        if a.moic <= 0:
            return 0.0
        return a.moic ** (1.0 / t) - 1.0
    winner = max(alternatives, key=per_year)

    note = (
        f"Winning alternative (MOIC / yr): {winner.name} "
        f"at {winner.moic:.2f}x MOIC / "
        f"{winner.time_to_exit_yrs:.1f}yr. Partner: "
        "compare at each board meeting; the right answer "
        "changes every year."
    )

    return ExitAlternativesReport(
        alternatives=alternatives,
        winning_alternative_name=winner.name,
        partner_note=note,
    )


def render_exit_alternatives_markdown(
    r: ExitAlternativesReport,
) -> str:
    lines = [
        "# Exit alternative comparison",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Winning alternative: "
        f"**{r.winning_alternative_name}**",
        "",
        "| Alternative | Proceeds | MOIC | Time to "
        "exit | Partner commentary |",
        "|---|---|---|---|---|",
    ]
    for a in r.alternatives:
        lines.append(
            f"| {a.name} | ${a.equity_proceeds_m:,.1f}M | "
            f"{a.moic:.2f}x | "
            f"{a.time_to_exit_yrs:.2f}yr | "
            f"{a.partner_commentary} |"
        )
    return "\n".join(lines)
