"""Recurring vs one-time EBITDA splitter.

Partners reflex: the exit multiple ONLY applies to recurring
EBITDA. One-time cash — from working-capital release, covenant-free
dividend recaps, sale-leaseback proceeds, contract break-fees — is
dollar-for-dollar, not multiple-of-dollar.

This module takes a list of EBITDA contributions tagged recurring
or one-time and returns:

- **Recurring EBITDA** (base for exit multiple math).
- **One-time cash** (treated at 1x, not multiple).
- **Exit valuation split** — multiple × recurring + 1x × one_time.
- **Recurring-ratio** — red flag if < 80%.
- **Partner note** — direct guidance on whether the exit story
  assumes the multiple applies to the full reported EBITDA (bad)
  or only to the recurring piece (good).

Worked example the doc references: a $50M reported EBITDA that is
$40M recurring + $10M from a one-time contract termination
payment. At 12x exit multiple:

- Wrong: $50M × 12 = $600M exit EV.
- Right: $40M × 12 + $10M × 1 = $490M exit EV.

$110M error — the difference between a strong MOIC and a weak
one. Partners catch this; models often do not.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


RECURRING_CATEGORIES = (
    "ongoing_operations",
    "contracted_revenue",
    "recurring_fees",
    "subscription",
    "run_rate_operating",
)

ONE_TIME_CATEGORIES = (
    "working_capital_release",
    "sale_leaseback_proceeds",
    "contract_termination_payment",
    "legal_settlement_recovery",
    "insurance_recovery",
    "gain_on_asset_sale",
    "one_time_cost_takeout",
    "grant_or_subsidy_one_time",
    "covid_relief",
)


@dataclass
class EBITDAContribution:
    label: str
    amount_m: float
    category: str                         # one of RECURRING / ONE_TIME
    rationale: str = ""


@dataclass
class RecurringSplit:
    recurring_ebitda_m: float
    one_time_ebitda_m: float
    recurring_ratio: float                # 0-1
    exit_multiple: float
    exit_ev_correct_m: float              # mult × recurring + 1x × one-time
    exit_ev_naive_m: float                # mult × (recurring + one-time)
    ev_overstatement_m: float             # naive - correct
    partner_note: str
    components: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recurring_ebitda_m": self.recurring_ebitda_m,
            "one_time_ebitda_m": self.one_time_ebitda_m,
            "recurring_ratio": self.recurring_ratio,
            "exit_multiple": self.exit_multiple,
            "exit_ev_correct_m": self.exit_ev_correct_m,
            "exit_ev_naive_m": self.exit_ev_naive_m,
            "ev_overstatement_m": self.ev_overstatement_m,
            "partner_note": self.partner_note,
            "components": list(self.components),
        }


def _is_recurring(category: str) -> bool:
    # Unknown categories default to one-time (partner-prudent).
    return category in RECURRING_CATEGORIES


def split_ebitda(
    contributions: List[EBITDAContribution],
    exit_multiple: float = 11.0,
) -> RecurringSplit:
    recurring = sum(c.amount_m for c in contributions
                     if _is_recurring(c.category))
    one_time = sum(c.amount_m for c in contributions
                    if not _is_recurring(c.category))
    total = recurring + one_time
    ratio = (recurring / total) if total > 0 else 0.0

    ev_correct = exit_multiple * recurring + 1.0 * one_time
    ev_naive = exit_multiple * (recurring + one_time)
    overstatement = ev_naive - ev_correct

    components = [
        {
            "label": c.label,
            "amount_m": round(c.amount_m, 2),
            "category": c.category,
            "is_recurring": _is_recurring(c.category),
            "rationale": c.rationale,
        }
        for c in contributions
    ]

    if ratio >= 0.95:
        note = (f"Clean recurring profile ({ratio*100:.0f}% recurring). "
                f"Exit math applies multiple to almost the full book — "
                f"EV ${ev_correct:,.0f}M.")
    elif ratio >= 0.80:
        note = (f"Recurring profile OK ({ratio*100:.0f}% recurring). "
                f"Apply multiple to recurring ${recurring:,.0f}M only; "
                f"one-time ${one_time:,.0f}M at 1x.")
    elif ratio >= 0.60:
        note = (f"**Material one-time component** "
                f"({100-ratio*100:.0f}% is one-time). Seller's quoted "
                f"${total:,.0f}M × {exit_multiple:.1f}x exit is "
                f"${overstatement:,.0f}M too high. Correct exit EV: "
                f"${ev_correct:,.0f}M.")
    else:
        note = (f"**Majority one-time** — recurring only "
                f"{ratio*100:.0f}%. The exit thesis is fragile. "
                f"Underwrite to ${recurring:,.0f}M recurring at full "
                f"multiple; rest at 1x if at all. Overstatement in "
                f"the simple math: ${overstatement:,.0f}M.")

    return RecurringSplit(
        recurring_ebitda_m=round(recurring, 2),
        one_time_ebitda_m=round(one_time, 2),
        recurring_ratio=round(ratio, 4),
        exit_multiple=exit_multiple,
        exit_ev_correct_m=round(ev_correct, 2),
        exit_ev_naive_m=round(ev_naive, 2),
        ev_overstatement_m=round(overstatement, 2),
        partner_note=note,
        components=components,
    )


def render_recurring_split_markdown(s: RecurringSplit) -> str:
    lines = [
        "# Recurring vs one-time EBITDA split",
        "",
        f"_{s.partner_note}_",
        "",
        f"- Recurring EBITDA: ${s.recurring_ebitda_m:,.1f}M "
        f"({s.recurring_ratio*100:.0f}%)",
        f"- One-time EBITDA: ${s.one_time_ebitda_m:,.1f}M",
        f"- Exit multiple: {s.exit_multiple:.1f}x",
        f"- Correct exit EV: ${s.exit_ev_correct_m:,.1f}M",
        f"- Naive exit EV: ${s.exit_ev_naive_m:,.1f}M",
        f"- Overstatement if naive: ${s.ev_overstatement_m:,.1f}M",
        "",
        "## Components",
        "",
        "| Label | Amount | Category | Recurring? | Rationale |",
        "|---|---:|---|:-:|---|",
    ]
    for c in s.components:
        rec = "yes" if c["is_recurring"] else "no"
        lines.append(
            f"| {c['label']} | ${c['amount_m']:,.2f}M | "
            f"{c['category']} | {rec} | {c['rationale']} |"
        )
    return "\n".join(lines)
