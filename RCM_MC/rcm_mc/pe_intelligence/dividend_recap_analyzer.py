"""Dividend recap analyzer — can we re-leverage to return capital?

A dividend recap re-levers the balance sheet and returns cash to
the sponsor/LPs. It's a DPI lever without an exit. Partners ask:

- Is the company's EBITDA growth enough to support higher debt?
- Is there coverage headroom for the incremental interest?
- Does the after-recap leverage still make the exit refinance-able?
- What's the IRR / DPI impact for LPs?

This module evaluates those questions and returns a partner-ready
go/no-go + sized recommendation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RecapInputs:
    current_ebitda_m: float
    current_debt_m: float
    fund_equity_invested_m: float         # cumulative called into this deal
    current_enterprise_value_m: float     # mark-to-model EV
    max_leverage_tolerance: float = 6.5   # post-recap leverage cap
    target_interest_coverage: float = 2.5  # post-recap EBITDA/interest floor
    market_debt_rate: float = 0.095
    years_into_hold: int = 3              # info only for partner note


@dataclass
class RecapAssessment:
    feasible: bool
    max_incremental_debt_m: float
    proposed_dividend_m: float
    post_recap_leverage: float
    post_recap_coverage: float
    dpi_uplift: float                     # dividend / fund_equity_invested
    partner_note: str
    blockers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feasible": self.feasible,
            "max_incremental_debt_m": self.max_incremental_debt_m,
            "proposed_dividend_m": self.proposed_dividend_m,
            "post_recap_leverage": self.post_recap_leverage,
            "post_recap_coverage": self.post_recap_coverage,
            "dpi_uplift": self.dpi_uplift,
            "partner_note": self.partner_note,
            "blockers": list(self.blockers),
        }


def analyze_recap(inputs: RecapInputs) -> RecapAssessment:
    """Assess a dividend recap against partner-prudent gates."""
    ebitda = max(0.01, inputs.current_ebitda_m)
    current_leverage = inputs.current_debt_m / ebitda
    blockers: List[str] = []

    # Max debt under leverage cap.
    max_debt_from_leverage = ebitda * inputs.max_leverage_tolerance

    # Max debt under coverage floor.
    # Coverage = EBITDA / (debt × rate). Solve for debt.
    if inputs.market_debt_rate > 0 and inputs.target_interest_coverage > 0:
        max_debt_from_coverage = ebitda / (
            inputs.target_interest_coverage * inputs.market_debt_rate
        )
    else:
        max_debt_from_coverage = max_debt_from_leverage

    max_debt = min(max_debt_from_leverage, max_debt_from_coverage)
    incremental_debt = max(0.0, max_debt - inputs.current_debt_m)

    # Dividend = incremental debt (minus a 2% transaction-cost haircut).
    dividend = incremental_debt * 0.98

    # Post-recap metrics assume full incremental debt taken.
    post_leverage = max_debt / ebitda if ebitda > 0 else 0.0
    post_interest = max_debt * inputs.market_debt_rate
    post_coverage = (ebitda / post_interest) if post_interest > 0 else 99.0

    if current_leverage >= inputs.max_leverage_tolerance:
        blockers.append(
            f"Current leverage {current_leverage:.1f}x already at/above "
            f"tolerance {inputs.max_leverage_tolerance:.1f}x."
        )
    if dividend <= 0:
        blockers.append(
            "No incremental debt capacity — leverage or coverage already maxed."
        )
    if post_coverage < inputs.target_interest_coverage:
        blockers.append(
            f"Post-recap coverage {post_coverage:.1f}x below target "
            f"{inputs.target_interest_coverage:.1f}x."
        )

    feasible = not blockers

    dpi_uplift = (dividend / inputs.fund_equity_invested_m
                   if inputs.fund_equity_invested_m > 0 else 0.0)

    if feasible:
        note = (
            f"Recap feasible: size up to ${dividend:,.1f}M dividend "
            f"(DPI uplift {dpi_uplift:.2f}x). Post-recap leverage "
            f"{post_leverage:.1f}x, coverage {post_coverage:.1f}x."
        )
    else:
        note = "Recap NOT feasible under current gates. " + " | ".join(blockers)

    return RecapAssessment(
        feasible=feasible,
        max_incremental_debt_m=round(incremental_debt, 2),
        proposed_dividend_m=round(dividend, 2),
        post_recap_leverage=round(post_leverage, 2),
        post_recap_coverage=round(post_coverage, 2),
        dpi_uplift=round(dpi_uplift, 4),
        partner_note=note,
        blockers=blockers,
    )


def render_recap_markdown(a: RecapAssessment) -> str:
    lines = [
        "# Dividend recap assessment",
        "",
        f"_{a.partner_note}_",
        "",
        f"- Feasible: **{'yes' if a.feasible else 'no'}**",
        f"- Max incremental debt: ${a.max_incremental_debt_m:,.1f}M",
        f"- Proposed dividend: ${a.proposed_dividend_m:,.1f}M",
        f"- Post-recap leverage: {a.post_recap_leverage:.2f}x",
        f"- Post-recap coverage: {a.post_recap_coverage:.2f}x",
        f"- DPI uplift: {a.dpi_uplift:.2f}x",
    ]
    if a.blockers:
        lines.extend(["", "## Blockers", ""])
        for b in a.blockers:
            lines.append(f"- {b}")
    return "\n".join(lines)
