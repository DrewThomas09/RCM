"""Referral flow dependency — who sends the volume?

Partner statement: "A physician practice isn't really
selling patients — it's selling the referral network.
If one referring doctor generates 12% of visits, that's
a single-point-of-failure. Buy the practice, lose the
doctor, lose the patients."

Distinct from:
- `customer_concentration_drilldown` — direct customer
  concentration (usually payer- or employer-facing).
- `concentration_risk_multidim` — multi-dimensional
  concentration summary.

This module focuses on **referral flow** specifically —
the upstream sources that send patients, samples, or
cases to the target. It matters most in:
- Specialty practices (GI, cardiology, orthopedics).
- Ambulatory surgery centers (surgeon ownership).
- Clinical labs (ordering physicians).
- Hospice (hospital discharge planners + physicians).
- Home health (hospital discharge + SNF referrals).

### 5 dimensions scored

1. **top_1_referrer_pct** — fraction from the single
   largest referrer.
2. **top_5_referrer_pct** — fraction from top-5.
3. **top_referrer_age_60_plus** — flight-risk.
4. **no_referring_network_contract** — can they just
   walk?
5. **diversification_across_specialties** — different
   specialties reduce correlated departure.

### Dependency tier

- `highly_diversified` (0 flags) — proceed; no ref-flow
  gate.
- `moderately_concentrated` (1-2 flags) — retention
  and relationship mgmt in 100-day plan.
- `heavily_concentrated` (3+ flags) — specific retention
  conditions at close; haircut EBITDA for flight risk.
- `single_point_of_failure` (top-1 ≥ 20% AND flight
  risk) — partner walks or specific mitigation.

### Expected EBITDA loss if top referrer departs

= top_1_pct × probability_of_departure × margin_elasticity.

Partner heuristic:
- top_1 ≥ 15% + age 60+: 60% probability over 3-yr hold.
- With no network contract: 40%.
- Diversified + younger: 15%.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ReferralFlowInputs:
    top_1_referrer_pct: float = 0.0        # fraction of revenue / volume
    top_5_referrer_pct: float = 0.0
    top_referrer_age_60_plus: bool = False
    no_referring_network_contract: bool = False
    diversification_across_specialties: bool = False
    ebitda_m: float = 0.0
    margin_elasticity: float = 0.9       # % EBITDA loss per % revenue loss


@dataclass
class ReferralFlag:
    name: str
    triggered: bool
    partner_comment: str


@dataclass
class ReferralFlowReport:
    tier: str                              # highly_diversified / moderately_concentrated
                                            # / heavily_concentrated /
                                            # single_point_of_failure
    flags: List[ReferralFlag] = field(default_factory=list)
    triggered_count: int = 0
    departure_probability_pct: float = 0.0
    expected_ebitda_loss_m: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier,
            "flags": [
                {"name": f.name, "triggered": f.triggered,
                 "partner_comment": f.partner_comment}
                for f in self.flags
            ],
            "triggered_count": self.triggered_count,
            "departure_probability_pct":
                self.departure_probability_pct,
            "expected_ebitda_loss_m":
                self.expected_ebitda_loss_m,
            "partner_note": self.partner_note,
        }


def score_referral_flow_dependency(
    inputs: ReferralFlowInputs,
) -> ReferralFlowReport:
    flags: List[ReferralFlag] = []

    # Flag 1: top-1 ≥ 15% revenue.
    top1_flag = inputs.top_1_referrer_pct >= 0.15
    flags.append(ReferralFlag(
        name="top_1_concentration_gt_15pct",
        triggered=top1_flag,
        partner_comment=(
            f"Top-1 referrer "
            f"{inputs.top_1_referrer_pct*100:.1f}% — "
            "single-point-of-failure exposure."
            if top1_flag else
            f"Top-1 referrer "
            f"{inputs.top_1_referrer_pct*100:.1f}% — "
            "manageable."
        ),
    ))

    # Flag 2: top-5 ≥ 50% revenue.
    top5_flag = inputs.top_5_referrer_pct >= 0.50
    flags.append(ReferralFlag(
        name="top_5_concentration_gt_50pct",
        triggered=top5_flag,
        partner_comment=(
            f"Top-5 referrers "
            f"{inputs.top_5_referrer_pct*100:.0f}% — "
            "concentrated base; small group sets "
            "volume."
            if top5_flag else
            "Top-5 referrer concentration within "
            "typical band."
        ),
    ))

    # Flag 3: top referrer age 60+ (retirement flight risk).
    flags.append(ReferralFlag(
        name="top_referrer_age_60_plus",
        triggered=inputs.top_referrer_age_60_plus,
        partner_comment=(
            "Top referrer age 60+ — retirement flight "
            "risk within 5 years."
            if inputs.top_referrer_age_60_plus else
            "Top referrer age profile not flight-risk."
        ),
    ))

    # Flag 4: no referring network contract.
    flags.append(ReferralFlag(
        name="no_referring_network_contract",
        triggered=inputs.no_referring_network_contract,
        partner_comment=(
            "No contractual referring-physician "
            "commitment — can walk any day."
            if inputs.no_referring_network_contract else
            "Referring-network contracts in place."
        ),
    ))

    # Flag 5: no diversification across specialties.
    flags.append(ReferralFlag(
        name="no_specialty_diversification",
        triggered=not inputs.diversification_across_specialties,
        partner_comment=(
            "Referral flow concentrated in one "
            "specialty — correlated departure risk."
            if not inputs.diversification_across_specialties
            else
            "Multi-specialty referral flow — reduces "
            "correlated risk."
        ),
    ))

    triggered = sum(1 for f in flags if f.triggered)

    # Departure probability heuristic.
    base_prob = 0.15
    if top1_flag and inputs.top_referrer_age_60_plus:
        base_prob = 0.60
    elif top1_flag and inputs.no_referring_network_contract:
        base_prob = 0.40
    elif top1_flag:
        base_prob = 0.30
    elif inputs.no_referring_network_contract:
        base_prob = 0.25
    if not inputs.diversification_across_specialties:
        base_prob += 0.05
    base_prob = min(0.80, base_prob)

    expected_revenue_loss_fraction = (
        inputs.top_1_referrer_pct * base_prob
    )
    expected_ebitda_loss = (
        inputs.ebitda_m
        * expected_revenue_loss_fraction
        * inputs.margin_elasticity
    )

    # Tier determination.
    spof = (
        inputs.top_1_referrer_pct >= 0.20
        and (inputs.top_referrer_age_60_plus or
              inputs.no_referring_network_contract)
    )
    if spof:
        tier = "single_point_of_failure"
        note = (
            f"Top-1 referrer "
            f"{inputs.top_1_referrer_pct*100:.0f}% + "
            "flight-risk factor → single point of "
            "failure. Partner: walk or require signed "
            "referring-physician contract as closing "
            "condition."
        )
    elif triggered >= 3:
        tier = "heavily_concentrated"
        note = (
            f"{triggered} referral flags firing. "
            f"Expected EBITDA loss on top-1 departure "
            f"${expected_ebitda_loss:,.1f}M at "
            f"{base_prob*100:.0f}% probability. Haircut "
            "underwrite by this amount."
        )
    elif triggered >= 1:
        tier = "moderately_concentrated"
        note = (
            f"{triggered} referral flags firing. "
            "Partner: retention and relationship "
            "management in the 100-day plan."
        )
    else:
        tier = "highly_diversified"
        note = (
            "Referral flow diversified. No concentration "
            "gating."
        )

    return ReferralFlowReport(
        tier=tier,
        flags=flags,
        triggered_count=triggered,
        departure_probability_pct=round(base_prob * 100, 1),
        expected_ebitda_loss_m=round(expected_ebitda_loss, 2),
        partner_note=note,
    )


def render_referral_flow_markdown(
    r: ReferralFlowReport,
) -> str:
    lines = [
        "# Referral flow dependency",
        "",
        f"**Tier:** `{r.tier}`",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Triggered flags: {r.triggered_count} / "
        f"{len(r.flags)}",
        f"- Departure probability: "
        f"{r.departure_probability_pct:.1f}%",
        f"- Expected EBITDA loss: "
        f"${r.expected_ebitda_loss_m:,.1f}M",
        "",
        "| Flag | Triggered | Partner comment |",
        "|---|---|---|",
    ]
    for f in r.flags:
        check = "✓" if f.triggered else "—"
        lines.append(
            f"| {f.name} | {check} | {f.partner_comment} |"
        )
    return "\n".join(lines)
