"""QofE pre-screen — partner's gut-read on add-back survival.

Partner statement: "Sellers normalize aggressively. Good
QofE strips back 20-30%. Know which add-backs will
survive before you engage the firm."

`qofe_tracker.py` handles status/progress on a QofE
engagement. This module is different: it is the *pre*-QofE
partner read on the seller's adjustments schedule. Given
the list of add-backs the seller is asserting, it:

1. Classifies each by how likely it is to survive QofE
   (high / medium / low / rejected).
2. Estimates the dollar haircut the partner should
   already price in (before QofE confirms).
3. Produces a re-priced EBITDA with partner-judgment
   adjustments.
4. Writes a partner-note: "stated $75M → QofE-adjusted
   $58M; model off $58M, not $75M."

### Add-back categories and rejection rates

Partner-judgment survival rates based on QofE patterns in
healthcare services PE:

- **owner_comp_excess** — 85% survive (normalize to market).
- **related_party_rent** — 70% survive at market rent;
  25% survive if seller-owned real estate.
- **nonrecurring_legal** — 60% survive; recurring legal
  is a red flag.
- **covid_windfall** — 20% survive (one-time but partners
  exclude aggressively).
- **systems_migration_onetime** — 50% survive; partners
  question whether truly one-time.
- **executive_severance** — 70% survive.
- **deferred_maintenance_capex_as_opex** — 10% survive;
  this is a reclassification.
- **pro_forma_acquisition** — 40% survive; partners
  demand TTM actuals.
- **management_fee_elim** — 90% survive.
- **startup_losses** — 50% survive with vintage cohort
  logic.
- **litigation_settlement** — 60% survive.
- **other** — 50% default.

The rejection rates are partner gut; QofE firms vary and
sector matters. Partners read the prescreen to decide
whether to spend QofE budget or walk before engaging.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


SURVIVAL_RATES: Dict[str, float] = {
    "owner_comp_excess": 0.85,
    "related_party_rent": 0.70,
    "nonrecurring_legal": 0.60,
    "covid_windfall": 0.20,
    "systems_migration_onetime": 0.50,
    "executive_severance": 0.70,
    "deferred_maintenance_capex_as_opex": 0.10,
    "pro_forma_acquisition": 0.40,
    "management_fee_elim": 0.90,
    "startup_losses": 0.50,
    "litigation_settlement": 0.60,
    "other": 0.50,
}

# Partner commentary per category.
PARTNER_COMMENTARY: Dict[str, str] = {
    "owner_comp_excess": (
        "Standard normalization. Survives QofE; model it."
    ),
    "related_party_rent": (
        "Survives if at market. If seller owns the "
        "real estate, ask whether the rent adjustment is "
        "really a sale-leaseback waiting to happen."
    ),
    "nonrecurring_legal": (
        "One-off legal survives. If legal repeats in prior "
        "year, it's not nonrecurring — it's run-rate."
    ),
    "covid_windfall": (
        "Aggressive QofE strips COVID tailwinds. Price off "
        "pre-COVID and post-COVID run-rates, not peak."
    ),
    "systems_migration_onetime": (
        "Partners question 'one-time' framing. If migration "
        "is ongoing or phased, 50% haircut at QofE."
    ),
    "executive_severance": (
        "Usually survives but ask whether severance is a "
        "signal of deeper team instability."
    ),
    "deferred_maintenance_capex_as_opex": (
        "Rejected. This is a reclassification, not an "
        "add-back. If seller is calling it add-back, "
        "walk."
    ),
    "pro_forma_acquisition": (
        "QofE usually demands TTM actuals for acquisitions "
        "— only 40% of pro-forma survives unadjusted."
    ),
    "management_fee_elim": (
        "Sponsor management fee normalization is standard. "
        "Nearly always survives."
    ),
    "startup_losses": (
        "Survives only with cohort-vintage support. If "
        "startup losses keep recurring, they're run-rate."
    ),
    "litigation_settlement": (
        "Settlement one-time; ongoing litigation cost is not."
    ),
    "other": (
        "Uncategorized add-back. Ask seller to justify; "
        "default 50% survival at QofE."
    ),
}


@dataclass
class SellerAddBack:
    category: str
    amount_m: float
    description: str = ""


@dataclass
class QofEPrescreenInputs:
    stated_ebitda_m: float
    seller_add_backs: List[SellerAddBack] = field(default_factory=list)


@dataclass
class AddBackAssessment:
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
class QofEPrescreenReport:
    stated_ebitda_m: float
    total_add_backs_m: float
    total_expected_surviving_m: float
    total_expected_haircut_m: float
    qofe_adjusted_ebitda_m: float
    adjustments: List[AddBackAssessment] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stated_ebitda_m": self.stated_ebitda_m,
            "total_add_backs_m": self.total_add_backs_m,
            "total_expected_surviving_m":
                self.total_expected_surviving_m,
            "total_expected_haircut_m":
                self.total_expected_haircut_m,
            "qofe_adjusted_ebitda_m":
                self.qofe_adjusted_ebitda_m,
            "adjustments": [a.to_dict() for a in self.adjustments],
            "partner_note": self.partner_note,
        }


def prescreen_qofe(
    inputs: QofEPrescreenInputs,
) -> QofEPrescreenReport:
    adjustments: List[AddBackAssessment] = []
    total_add_backs = 0.0
    total_surviving = 0.0
    total_haircut = 0.0

    for ab in inputs.seller_add_backs:
        cat = ab.category if ab.category in SURVIVAL_RATES else "other"
        survival = SURVIVAL_RATES[cat]
        surviving = round(ab.amount_m * survival, 2)
        haircut = round(ab.amount_m - surviving, 2)
        adjustments.append(AddBackAssessment(
            category=cat,
            amount_m=ab.amount_m,
            expected_survival_pct=survival,
            expected_surviving_m=surviving,
            expected_haircut_m=haircut,
            partner_commentary=PARTNER_COMMENTARY.get(
                cat, PARTNER_COMMENTARY["other"]
            ),
        ))
        total_add_backs += ab.amount_m
        total_surviving += surviving
        total_haircut += haircut

    # Seller's stated EBITDA already includes add-backs
    # asserted. QofE-adjusted EBITDA strips the haircut.
    qofe_adj_ebitda = round(inputs.stated_ebitda_m - total_haircut, 2)

    haircut_pct = (total_haircut / max(0.01, inputs.stated_ebitda_m))

    if haircut_pct >= 0.20:
        note = (f"Seller's ${inputs.stated_ebitda_m:,.1f}M EBITDA "
                f"loses ${total_haircut:,.1f}M at QofE "
                f"({haircut_pct*100:.0f}% of stated). Partner: "
                "re-price from adjusted EBITDA or pass. Do not "
                "underwrite off the headline.")
    elif haircut_pct >= 0.10:
        note = (f"Expected QofE haircut ${total_haircut:,.1f}M "
                f"({haircut_pct*100:.0f}%). Partner: model off "
                f"${qofe_adj_ebitda:,.1f}M, not stated. Exit "
                "multiple × adjusted EBITDA.")
    elif total_haircut > 0:
        note = (f"Small QofE haircut ${total_haircut:,.1f}M "
                f"({haircut_pct*100:.1f}%). Partner: model off "
                f"${qofe_adj_ebitda:,.1f}M; proceed on current "
                "thesis.")
    else:
        note = ("No add-backs asserted; stated EBITDA is QofE-"
                "ready on its face. Partner: verify at QofE but "
                "no pre-adjustment needed.")

    # Escalate further if any rejected category is material.
    rejected = [a for a in adjustments
                if a.category == "deferred_maintenance_capex_as_opex"]
    if rejected and sum(a.amount_m for a in rejected) > 0.02 * inputs.stated_ebitda_m:
        note += (" Additional red: deferred-maintenance capex "
                 "reclassified as opex is a walk signal; do not "
                 "proceed without seller recut.")

    return QofEPrescreenReport(
        stated_ebitda_m=inputs.stated_ebitda_m,
        total_add_backs_m=round(total_add_backs, 2),
        total_expected_surviving_m=round(total_surviving, 2),
        total_expected_haircut_m=round(total_haircut, 2),
        qofe_adjusted_ebitda_m=qofe_adj_ebitda,
        adjustments=adjustments,
        partner_note=note,
    )


def render_qofe_prescreen_markdown(
    r: QofEPrescreenReport,
) -> str:
    lines = [
        "# QofE pre-screen — partner read on add-back survival",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Stated EBITDA: ${r.stated_ebitda_m:,.1f}M",
        f"- Seller add-backs: ${r.total_add_backs_m:,.1f}M",
        f"- Expected surviving at QofE: ${r.total_expected_surviving_m:,.1f}M",
        f"- Expected haircut: ${r.total_expected_haircut_m:,.1f}M",
        f"- **QofE-adjusted EBITDA: ${r.qofe_adjusted_ebitda_m:,.1f}M**",
        "",
        "| Category | Amount | Survival % | Surviving | Haircut | "
        "Partner read |",
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
