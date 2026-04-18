"""Recurring vs one-time NPR — scrub the top line.

Partner statement: "Sellers stretch EBITDA with one-
time add-backs, but they ALSO stretch revenue.
Provider relief grants flow through NPR. DSH and UPL
settlements show up as line items. Quarterly true-ups
on Medicare cost-report estimates can move trailing
NPR by millions. The growth rate the seller pitches
is on TOTAL NPR. The growth rate the partner cares
about is on RECURRING NPR. Scrub the top line first,
then talk about growth."

Distinct from:
- `recurring_ebitda_line_scrubber` — operates at EBITDA
  level.
- `ebitda_normalization` — broader.
- `payer_mix_risk` — payer-mix concentration only.
- `medicare_advantage_bridge_trap` — narrow on MA.

This module operates at the **NPR line item** level.
Seller reports a TTM NPR; partner classifies each
recognized line as recurring or one-time, recomputes
recurring NPR, and surfaces the **growth-rate
distortion** caused by including one-time NPR in
trailing-twelve.

### 14 NPR line-item patterns

**One-time NPR** (4×, but only on the same line basis):

- `dsh_upl_supplemental_payment` — Medicaid DSH / UPL
  truing-up; episodic and state-budget-dependent.
- `provider_relief_grant` — CARES / ARPA / state
  pandemic provider grants.
- `medicare_cost_report_settlement` — settlement on
  prior-year cost report; one-time true-up.
- `rac_or_audit_recovery` — recovered audit
  recoupments.
- `state_directed_payment` — episodic state-directed
  Medicaid supplemental program.
- `meaningful_use_emr_incentive` — legacy MU/MIPS
  incentive payment, not recurring.
- `340b_one_time_true_up` — 340B contract pharmacy
  catch-up.
- `psh_supplemental_state_grant` — psychiatric /
  behavioral state supplemental grant.

**Questionable NPR** (review):

- `pro_forma_acquired_revenue` — pro-forma top-line
  for unclosed bolt-ons.
- `value_based_care_shared_savings` — single-year
  shared-savings spike (recurring only if program
  continues).
- `incentive_quality_bonus` — pay-for-performance
  bonuses (program-dependent).
- `risk_pool_distribution` — risk-pool distributions
  (timing-lumpy).

**Recurring NPR** (counted at exit multiple
exposure):

- `core_patient_service_revenue` — recurring core.
- `capitation_pmpm_revenue` — recurring per-member
  per-month capitation.
- `recurring_payer_contract_payments` — flagged
  recurring.

Anything not matched: **questionable** by default.

### Output

- `recurring_npr_m`, `one_time_npr_m`,
  `questionable_npr_m`
- `seller_growth_rate_pct` — on TOTAL NPR (seller's
  pitch)
- `partner_growth_rate_pct` — on RECURRING NPR
  (partner's read)
- `growth_rate_distortion_pct` — gap
- `partner_note` — where the seller's growth pitch
  breaks if recurring NPR shrunk
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


CATEGORY_RECURRING = "recurring"
CATEGORY_ONE_TIME = "one_time_npr"
CATEGORY_QUESTIONABLE = "questionable"


# (keyword_substrings, category, reason)
NPR_LINE_PATTERNS: List[tuple] = [
    # One-time NPR
    (("dsh", "disproportionate share", "upl",
      "upper payment limit", "supplemental medicaid"),
     CATEGORY_ONE_TIME,
     "Medicaid DSH/UPL supplemental payment — "
     "episodic, state-budget-dependent."),
    (("provider relief", "cares grant",
      "covid grant", "arpa grant"),
     CATEGORY_ONE_TIME,
     "Provider relief grant — pandemic-era one-time "
     "funding."),
    (("medicare cost report settlement",
      "cost report settlement"),
     CATEGORY_ONE_TIME,
     "Medicare cost-report settlement — prior-period "
     "true-up; not recurring."),
    (("rac recovery", "audit recovery"),
     CATEGORY_ONE_TIME,
     "RAC/audit recovery — one-time recoupment."),
    (("state directed payment",
      "directed payment program"),
     CATEGORY_ONE_TIME,
     "State directed-payment program — episodic and "
     "program-dependent."),
    (("meaningful use", "mu incentive",
      "ehr incentive", "mips incentive"),
     CATEGORY_ONE_TIME,
     "Legacy MU/MIPS EHR incentive payment — sunset "
     "or one-time."),
    (("340b true-up", "340b catch-up",
      "340b retroactive"),
     CATEGORY_ONE_TIME,
     "340B retroactive true-up — one-time catch-up."),
    (("psychiatric supplemental",
      "behavioral state grant",
      "psh supplemental"),
     CATEGORY_ONE_TIME,
     "Behavioral / psychiatric state supplemental "
     "grant — episodic."),

    # Questionable NPR
    (("pro forma", "pro-forma", "annualized acquired",
      "annualized bolt-on"),
     CATEGORY_QUESTIONABLE,
     "Pro-forma acquired revenue — only counts if "
     "deal has actually closed and integration "
     "complete."),
    (("shared savings", "vbc shared savings"),
     CATEGORY_QUESTIONABLE,
     "Value-based-care shared-savings — recurring "
     "only if program continues with same MLR target."),
    (("quality bonus", "p4p bonus",
      "incentive quality"),
     CATEGORY_QUESTIONABLE,
     "Quality / pay-for-performance bonus — program-"
     "dependent."),
    (("risk pool distribution",
      "risk pool true-up"),
     CATEGORY_QUESTIONABLE,
     "Risk-pool distribution — timing-lumpy; need "
     "trailing 36-mo."),

    # Recurring NPR
    (("core patient service",
      "patient service revenue",
      "core revenue"),
     CATEGORY_RECURRING,
     "Core patient service revenue — recurring base."),
    (("capitation", "pmpm", "per member per month"),
     CATEGORY_RECURRING,
     "Capitation / PMPM revenue — recurring "
     "membership-based."),
    (("recurring payer", "contracted payer recurring"),
     CATEGORY_RECURRING,
     "Recurring contracted payer payment."),
]


@dataclass
class NPRLineItem:
    description: str
    amount_m: float
    explicit_category: Optional[str] = None


@dataclass
class ScrubbedNPRLine:
    description: str
    amount_m: float
    category: str
    reason: str


@dataclass
class RecurringNPRInputs:
    stated_ttm_npr_m: float = 300.0
    prior_year_npr_m: float = 280.0
    line_items: List[NPRLineItem] = field(
        default_factory=list)


@dataclass
class RecurringNPRReport:
    lines: List[ScrubbedNPRLine] = field(
        default_factory=list)
    stated_ttm_npr_m: float = 0.0
    recurring_npr_m: float = 0.0
    one_time_npr_m: float = 0.0
    questionable_npr_m: float = 0.0
    seller_growth_rate_pct: float = 0.0
    partner_growth_rate_pct: float = 0.0
    growth_rate_distortion_pct: float = 0.0
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
            "stated_ttm_npr_m": self.stated_ttm_npr_m,
            "recurring_npr_m": self.recurring_npr_m,
            "one_time_npr_m": self.one_time_npr_m,
            "questionable_npr_m": self.questionable_npr_m,
            "seller_growth_rate_pct":
                self.seller_growth_rate_pct,
            "partner_growth_rate_pct":
                self.partner_growth_rate_pct,
            "growth_rate_distortion_pct":
                self.growth_rate_distortion_pct,
            "partner_note": self.partner_note,
        }


def _classify_npr_line(item: NPRLineItem) -> tuple:
    if item.explicit_category:
        return (
            item.explicit_category,
            "Partner / deal team explicit category.",
        )
    desc = item.description.lower()
    for keywords, category, reason in NPR_LINE_PATTERNS:
        if any(kw in desc for kw in keywords):
            return category, reason
    return (
        CATEGORY_QUESTIONABLE,
        "No matching pattern — partner review required.",
    )


def scrub_recurring_npr(
    inputs: RecurringNPRInputs,
) -> RecurringNPRReport:
    lines: List[ScrubbedNPRLine] = []
    recurring = 0.0
    one_time = 0.0
    questionable = 0.0

    for item in inputs.line_items:
        cat, reason = _classify_npr_line(item)
        lines.append(ScrubbedNPRLine(
            description=item.description,
            amount_m=item.amount_m,
            category=cat,
            reason=reason,
        ))
        if cat == CATEGORY_RECURRING:
            recurring += item.amount_m
        elif cat == CATEGORY_ONE_TIME:
            one_time += item.amount_m
        else:
            questionable += item.amount_m

    total_categorized = (
        recurring + one_time + questionable
    )
    if total_categorized == 0:
        recurring_npr = inputs.stated_ttm_npr_m
    else:
        # Remaining base = stated - sum of line items
        # (line items are EXTRA over base unless cat is
        # recurring, in which case they're already in base)
        # Convention: line items are seller's
        # "components of NPR" so subtract one-time and
        # half-credit questionable from stated.
        recurring_npr = (
            inputs.stated_ttm_npr_m - one_time -
            (questionable * 0.5)
        )
        recurring_npr = max(0.0, recurring_npr)

    seller_growth = (
        (inputs.stated_ttm_npr_m -
         inputs.prior_year_npr_m) /
        max(1.0, inputs.prior_year_npr_m)
    )
    partner_growth = (
        (recurring_npr - inputs.prior_year_npr_m) /
        max(1.0, inputs.prior_year_npr_m)
    )
    distortion = seller_growth - partner_growth

    if distortion > 0.05:
        note = (
            f"Seller pitches "
            f"{seller_growth:.1%} growth on TTM NPR "
            f"${inputs.stated_ttm_npr_m:.0f}M; partner "
            f"reads {partner_growth:.1%} on recurring "
            f"${recurring_npr:.0f}M. "
            f"{distortion:.1%} of pitched growth is "
            "one-time / non-recurring NPR — anchor "
            "growth conversation on recurring base."
        )
    elif distortion > 0.01:
        note = (
            f"Modest growth distortion "
            f"({distortion:.1%}) — recurring growth "
            f"{partner_growth:.1%} vs seller pitch "
            f"{seller_growth:.1%}. Worth surfacing in "
            "the bridge but not deal-breaking."
        )
    else:
        note = (
            f"Top line scrub clean — recurring NPR "
            f"~${recurring_npr:.0f}M; growth rate "
            f"{partner_growth:.1%} matches seller pitch."
        )

    return RecurringNPRReport(
        lines=lines,
        stated_ttm_npr_m=inputs.stated_ttm_npr_m,
        recurring_npr_m=round(recurring_npr, 2),
        one_time_npr_m=round(one_time, 2),
        questionable_npr_m=round(questionable, 2),
        seller_growth_rate_pct=round(seller_growth, 4),
        partner_growth_rate_pct=round(partner_growth, 4),
        growth_rate_distortion_pct=round(distortion, 4),
        partner_note=note,
    )


def render_recurring_npr_markdown(
    r: RecurringNPRReport,
) -> str:
    lines = [
        "# Recurring-vs-one-time NPR scrub",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Stated TTM NPR: ${r.stated_ttm_npr_m:.1f}M",
        f"- Recurring NPR: ${r.recurring_npr_m:.1f}M",
        f"- One-time NPR: ${r.one_time_npr_m:.1f}M",
        f"- Questionable NPR: ${r.questionable_npr_m:.1f}M",
        f"- Seller growth pitch: "
        f"{r.seller_growth_rate_pct:+.1%}",
        f"- Partner growth read: "
        f"{r.partner_growth_rate_pct:+.1%}",
        f"- Growth distortion: "
        f"{r.growth_rate_distortion_pct:+.1%}",
        "",
        "| Line | $M | Category | Reason |",
        "|---|---|---|---|",
    ]
    for l in r.lines:
        lines.append(
            f"| {l.description} | "
            f"${l.amount_m:.2f} | {l.category} | "
            f"{l.reason} |"
        )
    return "\n".join(lines)
