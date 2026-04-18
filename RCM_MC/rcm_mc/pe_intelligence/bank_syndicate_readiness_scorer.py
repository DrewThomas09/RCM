"""Bank syndicate readiness — can we actually close the debt?

Partner statement: "Equity thesis can work and the deal
still dies because the debt package doesn't come
together. I want the syndication risk on the page
before LOI, not the week before close."

Distinct from:
- `bank_syndicate_picker` — picks lenders for a deal.
- `debt_capacity_sizer` — how much debt an asset supports.
- `refinancing_window` — post-close refinance timing.

This module is the **pre-LOI readiness gate**: given the
proposed debt package + market + lender context, what's
the probability the debt package actually closes?

### 8 readiness dimensions

1. **commitment_letter_signed** — hard vs soft circle.
2. **lead_lender_has_sector_dry_powder** — lender's
   book capacity in this subsector.
3. **leverage_at_or_below_peer_average** — above peer
   = harder to syndicate.
4. **covenant_package_lender_friendly** — too seller-
   friendly gets rejected.
5. **repeat_lender_relationship** — relationship =
   faster close.
6. **rate_lock_or_hedged** — rate-move protection.
7. **private_credit_or_bank_match** — right capital
   type for the deal.
8. **market_rate_stable_at_signing** — macro rate
   volatility in last 60 days.

### Readiness tiers

- **6-8/8** = `ready` — close on timeline.
- **4-5/8** = `conditional` — close with remediation.
- **2-3/8** = `at_risk` — 30-60 day delay probable.
- **0-1/8** = `unreadied` — re-pitch lenders or
  restructure deal.

### Partner-note

Partners use this to decide whether to push close date
or extend LOI exclusivity. A single missing dimension
is usually fixable; three or more = re-think.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SyndicateReadinessInputs:
    commitment_letter_signed: bool = False
    lead_lender_has_sector_dry_powder: bool = False
    proposed_leverage: float = 5.5
    peer_average_leverage: float = 5.5
    covenant_package_lender_friendly: bool = False
    repeat_lender_relationship: bool = False
    rate_lock_or_hedged: bool = False
    private_credit_or_bank_match: bool = False
    market_rate_volatility_bps_60d: float = 0.0   # basis points


@dataclass
class ReadinessDimension:
    name: str
    passed: bool
    partner_comment: str


@dataclass
class SyndicateReadinessReport:
    score: int                             # 0-8
    tier: str                              # ready / conditional / at_risk / unreadied
    dimensions: List[ReadinessDimension] = field(default_factory=list)
    named_remediations: List[str] = field(default_factory=list)
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
            "named_remediations":
                list(self.named_remediations),
            "partner_note": self.partner_note,
        }


def score_syndicate_readiness(
    inputs: SyndicateReadinessInputs,
) -> SyndicateReadinessReport:
    dims: List[ReadinessDimension] = []
    remediations: List[str] = []

    # 1. Commitment letter signed.
    dims.append(ReadinessDimension(
        name="commitment_letter_signed",
        passed=inputs.commitment_letter_signed,
        partner_comment=(
            "Commitment letter signed."
            if inputs.commitment_letter_signed else
            "No signed commitment — soft circle only."
        ),
    ))
    if not inputs.commitment_letter_signed:
        remediations.append(
            "Obtain signed commitment letter before IC."
        )

    # 2. Lead lender dry powder.
    dims.append(ReadinessDimension(
        name="lead_lender_has_sector_dry_powder",
        passed=inputs.lead_lender_has_sector_dry_powder,
        partner_comment=(
            "Lead lender has capacity in subsector."
            if inputs.lead_lender_has_sector_dry_powder else
            "Lead lender at or near subsector cap — "
            "syndication risk."
        ),
    ))
    if not inputs.lead_lender_has_sector_dry_powder:
        remediations.append(
            "Either replace lead or widen syndicate to "
            "reduce hold-by-lender concentration."
        )

    # 3. Leverage at or below peer average.
    leverage_ok = (
        inputs.proposed_leverage
        <= inputs.peer_average_leverage + 0.25
    )
    dims.append(ReadinessDimension(
        name="leverage_at_or_below_peer_average",
        passed=leverage_ok,
        partner_comment=(
            f"Proposed leverage {inputs.proposed_leverage:.2f}x "
            f"within peer band ({inputs.peer_average_leverage:.2f}x)."
            if leverage_ok else
            f"Proposed {inputs.proposed_leverage:.2f}x above "
            f"peer {inputs.peer_average_leverage:.2f}x — "
            "lenders will push back."
        ),
    ))
    if not leverage_ok:
        remediations.append(
            "Reduce proposed leverage or add more equity "
            "to match peer-band leverage."
        )

    # 4. Covenant package.
    dims.append(ReadinessDimension(
        name="covenant_package_lender_friendly",
        passed=inputs.covenant_package_lender_friendly,
        partner_comment=(
            "Covenant package meets lender-standard terms."
            if inputs.covenant_package_lender_friendly else
            "Covenant package leans seller-friendly — "
            "expect lender redlines."
        ),
    ))
    if not inputs.covenant_package_lender_friendly:
        remediations.append(
            "Tighten cure rights / leverage steps / "
            "material MAC definitions to match lender "
            "market."
        )

    # 5. Repeat lender.
    dims.append(ReadinessDimension(
        name="repeat_lender_relationship",
        passed=inputs.repeat_lender_relationship,
        partner_comment=(
            "Repeat lender relationship — faster "
            "documentation."
            if inputs.repeat_lender_relationship else
            "New lender — longer credit committee cycle."
        ),
    ))

    # 6. Rate lock / hedged.
    dims.append(ReadinessDimension(
        name="rate_lock_or_hedged",
        passed=inputs.rate_lock_or_hedged,
        partner_comment=(
            "Rate protection in place."
            if inputs.rate_lock_or_hedged else
            "No rate lock / hedge — exposure to macro "
            "moves between commitment and funding."
        ),
    ))
    if not inputs.rate_lock_or_hedged:
        remediations.append(
            "Negotiate rate lock as part of commitment "
            "or purchase SOFR cap."
        )

    # 7. Private credit vs bank match.
    dims.append(ReadinessDimension(
        name="private_credit_or_bank_match",
        passed=inputs.private_credit_or_bank_match,
        partner_comment=(
            "Capital-type matches deal shape."
            if inputs.private_credit_or_bank_match else
            "Capital-type mismatch (e.g., bank-only on "
            "covenant-lite unitranche deal)."
        ),
    ))

    # 8. Market volatility.
    vol_ok = inputs.market_rate_volatility_bps_60d <= 50
    dims.append(ReadinessDimension(
        name="market_rate_stable_at_signing",
        passed=vol_ok,
        partner_comment=(
            f"Market rates stable "
            f"({inputs.market_rate_volatility_bps_60d:.0f} "
            "bps vol in past 60 days)."
            if vol_ok else
            f"Rate volatility {inputs.market_rate_volatility_bps_60d:.0f} "
            "bps in past 60 days — widening spreads likely."
        ),
    ))
    if not vol_ok:
        remediations.append(
            "Pre-sign market flex language; factor "
            "widening spread into underwrite."
        )

    score = sum(1 for d in dims if d.passed)
    if score >= 6:
        tier = "ready"
        note = (
            f"Syndicate ready ({score}/8). Close on "
            "timeline; monitor market vol."
        )
    elif score >= 4:
        tier = "conditional"
        note = (
            f"Syndicate conditional ({score}/8). Close "
            "with remediation on "
            f"{len(remediations)} items."
        )
    elif score >= 2:
        tier = "at_risk"
        note = (
            f"Syndicate at-risk ({score}/8). 30-60 day "
            "delay probable. Partner: extend LOI "
            "exclusivity or re-pitch lead."
        )
    else:
        tier = "unreadied"
        note = (
            f"Syndicate unreadied ({score}/8). Re-pitch "
            "entire lender group or restructure deal "
            "to match lender appetite."
        )

    return SyndicateReadinessReport(
        score=score,
        tier=tier,
        dimensions=dims,
        named_remediations=remediations,
        partner_note=note,
    )


def render_syndicate_readiness_markdown(
    r: SyndicateReadinessReport,
) -> str:
    lines = [
        "# Bank syndicate readiness",
        "",
        f"**Tier:** `{r.tier}` ({r.score}/8)",
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
    if r.named_remediations:
        lines.append("")
        lines.append("## Remediations")
        lines.append("")
        for rem in r.named_remediations:
            lines.append(f"- {rem}")
    return "\n".join(lines)
