"""Recurring vs one-time EBITDA — line-by-line scrub.

Partner statement: "The exit multiple only applies to
recurring EBITDA. I can sell the platform at 12× TTM
— on the recurring base. One-time items are cash; they
get 1×, not 12×. Sellers know this and they bury one-
time items inside trailing twelve because they know
the buyer will cap-rate the whole thing. Scrub the
line items. Anything that doesn't happen again next
year is 1×. The recurring base is what the exit buyer
underwrites."

Distinct from:
- `ebitda_normalization` / `ebitda_quality` — broad
  quality assessments.
- `ebitda_quality_bridge_reconstructor` — stated-to-
  run-rate bridge.
- `qofe_prescreen` — 12 standard add-back categories
  with survival rates.

This module operates at the **individual line item**
level. Seller passes a list of adjustments /
add-backs / one-time items; module classifies each
and produces:

- recurring EBITDA (exit-multiple applies)
- one-time cash (1× multiple — dollar-for-dollar)
- questionable (partner-review required)
- exit-multiple-applicable EBITDA vs. stated EBITDA

### Pattern catalog: 20 common line-item patterns

Partners have a reflex vocabulary for these. The
catalog matches keyword patterns in the line-item
description to classification.

**One-time cash only (1× multiple):**
- `legal_settlement_receivable`
- `insurance_proceeds`
- `gain_on_sale_asset`
- `cares_act_provider_relief`
- `erc_employee_retention_credit`
- `one_time_rac_settlement_refund`
- `litigation_recovery`
- `pandemic_related_payroll_support`

**Questionable (requires QofE):**
- `restructuring_charge`
- `management_fee_addback`
- `owner_comp_normalization`
- `synergy_run_rate_addback`
- `new_contract_annualized`

**Recurring (exit-multiple applies):**
- `operating_lease_normalization`
- `stock_comp_addback`
- `recurring_professional_fees`
- `recurring_ebitda`

Anything not matched: **questionable** by default.

### Partner verdict on exit-multiple gap

`recurring_ebitda_m × exit_multiple + one_time_cash_m × 1 =
implied_equity_value`. If seller's pitch is
`stated_ebitda × exit_multiple`, the gap between that
and the partner's read is the "exit multiple bleed."
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


CATEGORY_RECURRING = "recurring"
CATEGORY_ONE_TIME = "one_time_cash"
CATEGORY_QUESTIONABLE = "questionable"


# (keyword_substrings_any, category, reason)
LINE_ITEM_PATTERNS: List[tuple] = [
    # One-time cash only
    (("legal settlement", "settlement receiv", "lawsuit recovery"),
     CATEGORY_ONE_TIME,
     "Legal settlement receivable — one-time cash, 1× multiple."),
    (("insurance proceed", "insurance payout"),
     CATEGORY_ONE_TIME,
     "Insurance proceeds — one-time; does not recur."),
    (("gain on sale", "asset sale gain", "property gain"),
     CATEGORY_ONE_TIME,
     "Gain on sale of asset — capital event, not operating EBITDA."),
    (("cares act", "provider relief"),
     CATEGORY_ONE_TIME,
     "CARES Act / provider relief funding — one-time, does not recur."),
    (("erc", "employee retention credit", "employee retention tax"),
     CATEGORY_ONE_TIME,
     "ERC credit — one-time tax-policy windfall."),
    (("rac settlement", "rac refund"),
     CATEGORY_ONE_TIME,
     "One-time RAC settlement recovery — not recurring."),
    (("pandemic support", "covid relief", "ppp forgiveness"),
     CATEGORY_ONE_TIME,
     "Pandemic-era support — one-time by definition."),
    (("litigation recovery", "litigation refund"),
     CATEGORY_ONE_TIME,
     "Litigation recovery — one-time cash."),

    # Questionable
    (("restructuring", "severance", "rif charge"),
     CATEGORY_QUESTIONABLE,
     "Restructuring charge — defensible as one-time if named; questionable if ongoing."),
    (("management fee", "sponsor fee", "monitoring fee"),
     CATEGORY_QUESTIONABLE,
     "Management fee add-back — will survive QofE if fee ends at close; questionable if persists."),
    (("owner comp", "physician owner comp", "owner normalization"),
     CATEGORY_QUESTIONABLE,
     "Owner / physician comp normalization — QofE typically haircuts 30-50%."),
    (("synerg", "run-rate addback", "run rate savings"),
     CATEGORY_QUESTIONABLE,
     "Synergy / run-rate add-back — unearned credit; QofE survival < 50%."),
    (("new contract annualiz", "annualized new", "new client annualized"),
     CATEGORY_QUESTIONABLE,
     "Annualized new-contract EBITDA — only survives if contract is signed AND implementation complete."),
    (("proforma for bolt-on", "pro-forma bolt-on", "annualized bolt-on"),
     CATEGORY_QUESTIONABLE,
     "Pro-forma bolt-on EBITDA — QofE will require full run-rate with integration costs."),

    # Recurring
    (("stock comp", "equity comp"),
     CATEGORY_RECURRING,
     "Stock comp add-back — standard PE treatment, add-back typically survives."),
    (("operating lease normaliz", "lease accounting"),
     CATEGORY_RECURRING,
     "Operating lease / ASC 842 normalization — typically add-back survives."),
    (("recurring professional fee",),
     CATEGORY_RECURRING,
     "Recurring professional fees — part of normalized run-rate."),
    (("recurring", "run-rate recurring"),
     CATEGORY_RECURRING,
     "Flagged as recurring; partner can confirm on QofE."),
]


@dataclass
class EBITDALineItem:
    description: str
    amount_m: float
    # Optional explicit category if partner already
    # knows; otherwise the scrubber classifies.
    explicit_category: Optional[str] = None


@dataclass
class ScrubbedLine:
    description: str
    amount_m: float
    category: str
    reason: str


@dataclass
class RecurringEBITDAInputs:
    stated_ebitda_m: float = 50.0
    line_items: List[EBITDALineItem] = field(
        default_factory=list)
    exit_multiple: float = 11.0


@dataclass
class RecurringEBITDAReport:
    lines: List[ScrubbedLine] = field(default_factory=list)
    stated_ebitda_m: float = 0.0
    recurring_ebitda_m: float = 0.0
    one_time_cash_m: float = 0.0
    questionable_m: float = 0.0
    exit_multiple_applicable_ebitda_m: float = 0.0
    implied_equity_seller_view_m: float = 0.0
    implied_equity_partner_view_m: float = 0.0
    exit_multiple_bleed_m: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lines": [
                {"description": l.description,
                 "amount_m": l.amount_m,
                 "category": l.category,
                 "reason": l.reason}
                for l in self.lines
            ],
            "stated_ebitda_m": self.stated_ebitda_m,
            "recurring_ebitda_m":
                self.recurring_ebitda_m,
            "one_time_cash_m": self.one_time_cash_m,
            "questionable_m": self.questionable_m,
            "exit_multiple_applicable_ebitda_m":
                self.exit_multiple_applicable_ebitda_m,
            "implied_equity_seller_view_m":
                self.implied_equity_seller_view_m,
            "implied_equity_partner_view_m":
                self.implied_equity_partner_view_m,
            "exit_multiple_bleed_m":
                self.exit_multiple_bleed_m,
            "partner_note": self.partner_note,
        }


def _classify_line(
    item: EBITDALineItem,
) -> tuple:
    """Returns (category, reason)."""
    if item.explicit_category:
        return (
            item.explicit_category,
            "Explicitly categorized by partner / deal team.",
        )
    desc = item.description.lower()
    for keywords, category, reason in LINE_ITEM_PATTERNS:
        if any(kw in desc for kw in keywords):
            return category, reason
    return (
        CATEGORY_QUESTIONABLE,
        "No matching pattern — partner review required.",
    )


def scrub_recurring_ebitda(
    inputs: RecurringEBITDAInputs,
) -> RecurringEBITDAReport:
    lines: List[ScrubbedLine] = []
    recurring = 0.0
    one_time = 0.0
    questionable = 0.0

    for item in inputs.line_items:
        category, reason = _classify_line(item)
        lines.append(ScrubbedLine(
            description=item.description,
            amount_m=item.amount_m,
            category=category,
            reason=reason,
        ))
        if category == CATEGORY_RECURRING:
            recurring += item.amount_m
        elif category == CATEGORY_ONE_TIME:
            one_time += item.amount_m
        else:
            questionable += item.amount_m

    # Baseline recurring EBITDA before line-item overlay
    # = stated EBITDA − sum of all adjustments (so the
    # items represent seller add-backs; partner subtracts
    # non-recurring ones from stated).
    # If line items sum to zero, assume stated_ebitda_m
    # is the recurring base already.
    total_adjustments = recurring + one_time + questionable
    if total_adjustments == 0:
        recurring_ebitda_m = inputs.stated_ebitda_m
    else:
        # Stated EBITDA includes all line items; partner
        # keeps only the RECURRING category.
        base_ebitda = inputs.stated_ebitda_m - total_adjustments
        # partner gives half-credit to questionable items
        # as a working assumption; full-credit to recurring.
        recurring_ebitda_m = (
            base_ebitda + recurring + questionable * 0.5
        )

    exit_applicable = max(0.0, recurring_ebitda_m)
    seller_view = (
        inputs.stated_ebitda_m * inputs.exit_multiple +
        0.0  # seller implicitly multiplies everything
    )
    partner_view = (
        exit_applicable * inputs.exit_multiple +
        one_time * 1.0
    )
    bleed = seller_view - partner_view

    # Partner note
    if bleed > 0.10 * seller_view and seller_view > 0:
        note = (
            f"Exit-multiple bleed: seller pitches "
            f"${seller_view:.1f}M equity; partner read "
            f"${partner_view:.1f}M "
            f"(${bleed:.1f}M gap). "
            "Anchor the next counter on recurring-only "
            "EBITDA × multiple + one-time × 1."
        )
    elif questionable > 0.5 * recurring:
        note = (
            f"Questionable items "
            f"${questionable:.1f}M are a large share of "
            "the bridge — prioritize QofE survival on "
            "owner comp, synergies, and annualized "
            "contract items. Re-run with QofE numbers."
        )
    else:
        note = (
            f"Line-item scrub confirms "
            f"${exit_applicable:.1f}M recurring EBITDA. "
            "One-time items properly segregated; "
            "exit-multiple-applicable bridge clean."
        )

    return RecurringEBITDAReport(
        lines=lines,
        stated_ebitda_m=inputs.stated_ebitda_m,
        recurring_ebitda_m=round(recurring_ebitda_m, 2),
        one_time_cash_m=round(one_time, 2),
        questionable_m=round(questionable, 2),
        exit_multiple_applicable_ebitda_m=round(
            exit_applicable, 2),
        implied_equity_seller_view_m=round(
            seller_view, 2),
        implied_equity_partner_view_m=round(
            partner_view, 2),
        exit_multiple_bleed_m=round(bleed, 2),
        partner_note=note,
    )


def render_recurring_ebitda_markdown(
    r: RecurringEBITDAReport,
) -> str:
    lines = [
        "# Recurring-vs-one-time EBITDA scrub",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Stated EBITDA: ${r.stated_ebitda_m:.1f}M",
        f"- Recurring EBITDA: ${r.recurring_ebitda_m:.1f}M",
        f"- One-time cash: ${r.one_time_cash_m:.1f}M (1× multiple)",
        f"- Questionable: ${r.questionable_m:.1f}M",
        f"- Exit-multiple-applicable: "
        f"${r.exit_multiple_applicable_ebitda_m:.1f}M",
        f"- Exit-multiple bleed: "
        f"${r.exit_multiple_bleed_m:+.1f}M",
        "",
        "| Line item | $M | Category | Reason |",
        "|---|---|---|---|",
    ]
    for l in r.lines:
        lines.append(
            f"| {l.description} | "
            f"${l.amount_m:+.2f} | "
            f"{l.category} | {l.reason} |"
        )
    return "\n".join(lines)
