"""Physician comp normalization check — partner's EBITDA filter.

Partner statement: "Every physician-practice deal has
comp-normalization uplift in the pro-forma. Half of it is
real; half is seller optimism. I want to see the specific
adjustments and decide which survive."

Physician-practice PE deals book EBITDA uplift from
*comp normalization*: the assumption that post-close,
physician compensation resets to market, and the "savings"
flows to the bottom line. Sellers stretch this number.

This module scrutinizes five specific categories of
physician-comp adjustment and classifies each by whether it
**survives** partner diligence:

1. **Base comp normalization to MGMA median** — the
   headline adjustment.
2. **Ancillary ownership distributions elimination** — DI,
   radiology, pathology ownership rolled up.
3. **Related-party rent step-down** — physician-owned real
   estate.
4. **Pre-close retention / signing bonuses add-back** —
   one-time items.
5. **Management fee elimination** — practice-level MSO /
   admin fee.

### Partner survival rates

Partner-judgment fraction of each adjustment that
survives QofE + operator reality:

- `base_comp_normalization` — 60% survives (MGMA
  benchmarks have wide bands; operator churn if cut too
  aggressively).
- `ancillary_ownership` — 80% survives (clear structural
  change).
- `related_party_rent` — 70% survives if at market;
  30% if below market (cap adjustment at market rate).
- `retention_bonuses` — 50% survives (some are
  disguised run-rate).
- `management_fee_elim` — 90% survives.

### The operator-churn constraint

If base-comp cut > 20% from current, partner applies a
**churn haircut** — 15-30% of physicians leave within 24
months. Every departing physician takes 40-60% of their
revenue with them. The savings disappears.

### Output

- **Adjusted EBITDA** = stated EBITDA - adjustments not
  surviving.
- **Churn-risk flag** if base-comp cut > 20%.
- **Partner note** with accept / reprice / walk.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Partner-judgment survival rates by adjustment category.
SURVIVAL_RATES: Dict[str, float] = {
    "base_comp_normalization": 0.60,
    "ancillary_ownership": 0.80,
    "related_party_rent_at_market": 0.70,
    "related_party_rent_below_market": 0.30,
    "retention_bonuses": 0.50,
    "management_fee_elim": 0.90,
    "other": 0.50,
}


@dataclass
class CompAdjustment:
    category: str
    amount_m: float
    description: str = ""


@dataclass
class PhysicianCompNormInputs:
    stated_ebitda_m: float
    proposed_adjustments: List[CompAdjustment] = field(
        default_factory=list
    )
    physician_count: int = 10
    current_avg_comp_usd: float = 500_000.0
    proposed_avg_comp_usd: float = 450_000.0
    rent_cut_is_below_market: bool = False


@dataclass
class AdjustmentAssessment:
    category: str
    amount_m: float
    expected_survival_pct: float
    expected_surviving_m: float
    expected_haircut_m: float
    partner_commentary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "amount_m": self.amount_m,
            "expected_survival_pct": self.expected_survival_pct,
            "expected_surviving_m": self.expected_surviving_m,
            "expected_haircut_m": self.expected_haircut_m,
            "partner_commentary": self.partner_commentary,
        }


@dataclass
class PhysicianCompNormReport:
    stated_ebitda_m: float
    total_adjustments_m: float
    total_surviving_m: float
    total_haircut_m: float
    adjusted_ebitda_m: float
    base_comp_cut_pct: float
    churn_risk_flag: bool
    churn_ebitda_hit_m: float
    adjustments: List[AdjustmentAssessment] = field(default_factory=list)
    verdict: str = ""
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stated_ebitda_m": self.stated_ebitda_m,
            "total_adjustments_m": self.total_adjustments_m,
            "total_surviving_m": self.total_surviving_m,
            "total_haircut_m": self.total_haircut_m,
            "adjusted_ebitda_m": self.adjusted_ebitda_m,
            "base_comp_cut_pct": self.base_comp_cut_pct,
            "churn_risk_flag": self.churn_risk_flag,
            "churn_ebitda_hit_m": self.churn_ebitda_hit_m,
            "adjustments": [a.to_dict() for a in self.adjustments],
            "verdict": self.verdict,
            "partner_note": self.partner_note,
        }


def _commentary(category: str, survives: float) -> str:
    templates = {
        "base_comp_normalization": (
            "Base-comp normalization survives on MGMA "
            "anchor but carries churn risk if cut > 20%."
        ),
        "ancillary_ownership": (
            "Ancillary-ownership roll-up is a structural "
            "change; mostly survives QofE."
        ),
        "related_party_rent_at_market": (
            "Rent normalization at market rate is standard."
        ),
        "related_party_rent_below_market": (
            "Cutting below-market rent to even lower is "
            "partner-rejected; cap at market."
        ),
        "retention_bonuses": (
            "Retention bonuses blur with run-rate comp. "
            "Only 50% survives as true one-time."
        ),
        "management_fee_elim": (
            "Sponsor-level management fee standard; "
            "survives."
        ),
        "other": (
            "Uncategorized adjustment. Default 50% survival; "
            "demand seller justification."
        ),
    }
    return templates.get(category, templates["other"])


def check_physician_comp_normalization(
    inputs: PhysicianCompNormInputs,
) -> PhysicianCompNormReport:
    adjustments: List[AdjustmentAssessment] = []
    total_adj = 0.0
    total_surv = 0.0
    total_hair = 0.0

    for adj in inputs.proposed_adjustments:
        cat = adj.category
        # Special-case related-party rent based on input flag.
        if cat == "related_party_rent":
            cat = ("related_party_rent_below_market"
                   if inputs.rent_cut_is_below_market
                   else "related_party_rent_at_market")
        survival = SURVIVAL_RATES.get(
            cat, SURVIVAL_RATES["other"]
        )
        surviving = round(adj.amount_m * survival, 2)
        haircut = round(adj.amount_m - surviving, 2)
        adjustments.append(AdjustmentAssessment(
            category=cat,
            amount_m=adj.amount_m,
            expected_survival_pct=survival,
            expected_surviving_m=surviving,
            expected_haircut_m=haircut,
            partner_commentary=_commentary(cat, survival),
        ))
        total_adj += adj.amount_m
        total_surv += surviving
        total_hair += haircut

    # Base-comp cut magnitude.
    if inputs.current_avg_comp_usd > 0:
        base_cut_pct = (
            (inputs.current_avg_comp_usd
             - inputs.proposed_avg_comp_usd)
            / inputs.current_avg_comp_usd
        )
    else:
        base_cut_pct = 0.0
    churn_flag = base_cut_pct > 0.20

    # Churn EBITDA hit: 15% of physicians churn, each taking
    # 50% of revenue contribution. Approximate contribution
    # = stated EBITDA × (phys / total).
    churn_hit = 0.0
    if churn_flag:
        # Rough: assume 15% of the avg-comp delta turns into
        # lost margin. Partner shortcut.
        n_churning = max(1, int(inputs.physician_count * 0.15))
        # Lost EBITDA ≈ n_churning × (stated EBITDA /
        # physician_count) × 0.50 (we lose half their margin
        # contribution to competitors).
        if inputs.physician_count > 0:
            churn_hit = round(
                n_churning *
                (inputs.stated_ebitda_m /
                 max(1, inputs.physician_count)) * 0.50,
                2,
            )

    # Adjusted EBITDA = stated + surviving adjustments -
    # churn hit. But "stated" may already include optimistic
    # adjustments; partner wants stated_ebitda - haircut.
    # Interpret stated_ebitda as the seller's pro-forma
    # already including proposed adjustments. Haircut reduces
    # to partner-realistic; churn further reduces.
    adjusted_ebitda = round(
        inputs.stated_ebitda_m - total_hair - churn_hit,
        2,
    )

    haircut_pct = (
        (total_hair + churn_hit)
        / max(0.01, inputs.stated_ebitda_m)
    )

    # Verdict ladder.
    if haircut_pct >= 0.20 or (churn_flag and haircut_pct >= 0.10):
        verdict = "walk"
        note = (
            f"Pro-forma overstates EBITDA by "
            f"${total_hair + churn_hit:,.1f}M "
            f"({haircut_pct*100:.0f}%). "
            "Partner: walk or demand seller recut."
        )
    elif haircut_pct >= 0.10:
        verdict = "reprice"
        note = (
            f"Expected normalization haircut $"
            f"{total_hair + churn_hit:,.1f}M "
            f"({haircut_pct*100:.0f}%). Partner: model off "
            f"${adjusted_ebitda:,.1f}M; apply exit multiple "
            "accordingly."
        )
    elif total_hair + churn_hit > 0:
        verdict = "proceed_with_adjustments"
        note = (
            f"Modest haircut ${total_hair + churn_hit:,.1f}M. "
            f"Partner: model off ${adjusted_ebitda:,.1f}M; "
            "proceed."
        )
    else:
        verdict = "accept"
        note = (
            "No material adjustments flagged. Partner: "
            "accept seller normalization."
        )

    if churn_flag:
        note += (
            f" Churn risk: base comp cut "
            f"{base_cut_pct*100:.0f}% triggers 15% physician "
            "churn assumption — priced into adjusted EBITDA."
        )

    return PhysicianCompNormReport(
        stated_ebitda_m=inputs.stated_ebitda_m,
        total_adjustments_m=round(total_adj, 2),
        total_surviving_m=round(total_surv, 2),
        total_haircut_m=round(total_hair, 2),
        adjusted_ebitda_m=adjusted_ebitda,
        base_comp_cut_pct=round(base_cut_pct, 4),
        churn_risk_flag=churn_flag,
        churn_ebitda_hit_m=churn_hit,
        adjustments=adjustments,
        verdict=verdict,
        partner_note=note,
    )


def render_physician_comp_norm_markdown(
    r: PhysicianCompNormReport,
) -> str:
    lines = [
        "# Physician comp normalization check",
        "",
        f"**Verdict:** `{r.verdict}`",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Stated EBITDA: ${r.stated_ebitda_m:,.1f}M",
        f"- Normalization adjustments: "
        f"${r.total_adjustments_m:,.1f}M",
        f"- Surviving at QofE: ${r.total_surviving_m:,.1f}M",
        f"- Haircut: ${r.total_haircut_m:,.1f}M",
        f"- Churn EBITDA hit: ${r.churn_ebitda_hit_m:,.1f}M "
        f"(cut {r.base_comp_cut_pct*100:.0f}%, "
        f"flag {'YES' if r.churn_risk_flag else 'no'})",
        f"- **Adjusted EBITDA: ${r.adjusted_ebitda_m:,.1f}M**",
        "",
        "| Category | Amount | Survival | Surviving | Haircut "
        "| Partner read |",
        "|---|---|---|---|---|---|",
    ]
    for a in r.adjustments:
        lines.append(
            f"| {a.category} | ${a.amount_m:,.1f}M | "
            f"{a.expected_survival_pct*100:.0f}% | "
            f"${a.expected_surviving_m:,.1f}M | "
            f"${a.expected_haircut_m:,.1f}M | "
            f"{a.partner_commentary} |"
        )
    return "\n".join(lines)
