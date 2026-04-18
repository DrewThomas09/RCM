"""LOI term sheet review — the specific terms partners push back on.

After diligence, partners review the seller's LOI markup and
push back on specific items. Associates mark up everything;
partners know which 5 terms actually move outcomes.

Partner-priority LOI terms:

1. **Exclusivity window** — 45-60 days standard; anything less
   is a buyer squeeze, anything more is giving up optionality.
2. **Breakup fee** — partner asks "is this enforceable in this
   jurisdiction?" Reverse termination fees are a specific tool.
3. **No-shop / go-shop** — true no-shop is partner preference;
   go-shop is a seller carveout.
4. **Financing contingency** — hard money on signing vs.
   flexibility; we want flex.
5. **R&W insurance mechanics** — cap, deductible, exclusions,
   carve-outs (tax, FCA, fraud always survive).
6. **Working capital peg methodology** — reference the peg
   negotiation module.
7. **Material adverse change (MAC) definition** — narrow or
   broad; partners want breathing room.
8. **Interim covenants** — what seller can and can't do between
   sign and close.
9. **Employee / retention pools** — sized at close or post-
   close? Who controls?
10. **Regulatory approval commitments** — FTC / antitrust; who
    pays for divestitures?
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LOITermReview:
    term: str
    seller_proposal: str
    partner_counter: str
    priority: str                             # "must_push" / "should_push"
    rationale: str


@dataclass
class LOIReviewInputs:
    exclusivity_days: int = 60
    breakup_fee_pct: float = 0.0
    no_shop_present: bool = True
    financing_contingency_hard: bool = True
    rw_insurance_proposed: bool = True
    rw_cap_pct_ev: float = 0.10
    rw_deductible_pct_ev: float = 0.005
    mac_definition_broad: bool = True
    interim_covenants_tight: bool = True
    retention_pool_sized_at_close: bool = True
    regulatory_risk_material: bool = False


@dataclass
class LOIReviewReport:
    reviews: List[LOITermReview] = field(default_factory=list)
    must_push_count: int = 0
    should_push_count: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reviews": [
                {"term": r.term, "seller_proposal": r.seller_proposal,
                 "partner_counter": r.partner_counter,
                 "priority": r.priority, "rationale": r.rationale}
                for r in self.reviews
            ],
            "must_push_count": self.must_push_count,
            "should_push_count": self.should_push_count,
            "partner_note": self.partner_note,
        }


def review_loi(inputs: LOIReviewInputs) -> LOIReviewReport:
    reviews: List[LOITermReview] = []

    # Exclusivity.
    if inputs.exclusivity_days < 45:
        reviews.append(LOITermReview(
            term="exclusivity_window",
            seller_proposal=f"{inputs.exclusivity_days} days",
            partner_counter="45-60 days",
            priority="must_push",
            rationale=("Less than 45 days rushes diligence; partners "
                        "push back unless we know the asset cold."),
        ))
    elif inputs.exclusivity_days > 90:
        reviews.append(LOITermReview(
            term="exclusivity_window",
            seller_proposal=f"{inputs.exclusivity_days} days",
            partner_counter="60-75 days",
            priority="should_push",
            rationale=("Excess exclusivity signals seller has "
                        "nothing to go-shop; also ties up our team."),
        ))

    # Breakup fee.
    if inputs.breakup_fee_pct > 0.03:
        reviews.append(LOITermReview(
            term="breakup_fee",
            seller_proposal=(f"{inputs.breakup_fee_pct*100:.1f}% of "
                              "purchase price"),
            partner_counter="1-2% max",
            priority="must_push",
            rationale=("> 3% break fee is punitive; pushes us into "
                        "signing when diligence isn't clean."),
        ))

    # No-shop.
    if not inputs.no_shop_present:
        reviews.append(LOITermReview(
            term="no_shop_clause",
            seller_proposal="not included",
            partner_counter="strict no-shop with limited fiduciary out",
            priority="must_push",
            rationale=("Without no-shop, seller can shop our bid; "
                        "no partner will sign without this."),
        ))

    # Financing contingency.
    if inputs.financing_contingency_hard:
        reviews.append(LOITermReview(
            term="financing_contingency",
            seller_proposal="hard money / no financing contingency",
            partner_counter="customary financing contingency + "
                            "reverse termination fee",
            priority="should_push",
            rationale=("Hard-money signing assumes credit markets "
                        "cooperate; partners want a fallback."),
        ))

    # R&W insurance caps.
    if inputs.rw_insurance_proposed:
        if inputs.rw_cap_pct_ev > 0.15:
            reviews.append(LOITermReview(
                term="rw_insurance_cap",
                seller_proposal=(f"{inputs.rw_cap_pct_ev*100:.0f}% of EV"),
                partner_counter="10-15% of EV (market standard)",
                priority="should_push",
                rationale=("Higher caps cost more premium; middle of "
                            "market is the efficient point."),
            ))
        if inputs.rw_deductible_pct_ev < 0.004:
            reviews.append(LOITermReview(
                term="rw_deductible",
                seller_proposal=(f"{inputs.rw_deductible_pct_ev*100:.2f}%"),
                partner_counter="0.4-0.5% EV",
                priority="should_push",
                rationale=("Deductible below 0.4% is generous; we "
                            "don't need to cover every penny."),
            ))

    # MAC definition.
    if inputs.mac_definition_broad:
        reviews.append(LOITermReview(
            term="mac_definition",
            seller_proposal="broad MAC carve-outs",
            partner_counter=("narrow MAC — seller shouldn't be able "
                              "to force close through adverse events"),
            priority="must_push",
            rationale=("Narrow MAC gives the partner a walk-away "
                        "right if fundamentals deteriorate pre-close."),
        ))

    # Interim covenants.
    if not inputs.interim_covenants_tight:
        reviews.append(LOITermReview(
            term="interim_covenants",
            seller_proposal="loose interim operating covenants",
            partner_counter=("tight covenants: no new debt, material "
                              "contract changes, hiring > threshold, "
                              "capex > threshold"),
            priority="must_push",
            rationale=("Loose covenants let seller change the asset "
                        "between sign and close — we buy something "
                        "different from what we diligenced."),
        ))

    # Retention pool.
    if not inputs.retention_pool_sized_at_close:
        reviews.append(LOITermReview(
            term="retention_pool",
            seller_proposal="retention pool sized post-close",
            partner_counter=("retention pool sized at close with "
                              "buyer control over allocation"),
            priority="should_push",
            rationale=("Retention pool is a partner lever; seller "
                        "sizing it pre-close constrains allocation."),
        ))

    # Regulatory approval risk.
    if inputs.regulatory_risk_material:
        reviews.append(LOITermReview(
            term="regulatory_approval",
            seller_proposal="buyer pays for divestitures",
            partner_counter=("divestiture obligations capped; no "
                              "'hell-or-high-water' commitment"),
            priority="must_push",
            rationale=("Open-ended divestiture commitments can "
                        "destroy deal economics; cap or walk."),
        ))

    must = sum(1 for r in reviews if r.priority == "must_push")
    should = sum(1 for r in reviews if r.priority == "should_push")

    if must >= 4:
        note = (f"{must} must-push items — LOI is seller-friendly "
                "across the board. Partner should rebuild the term "
                "sheet rather than red-line.")
    elif must >= 2:
        note = (f"{must} must-push + {should} should-push items. "
                "Standard LOI negotiation; get partner on the "
                "phone with seller's sponsor counsel.")
    elif must == 0 and should == 0:
        note = ("LOI terms are within market bands; no partner-level "
                "escalation needed.")
    else:
        note = (f"{must} must-push + {should} should-push. Associate-"
                "level redline is fine; partner reviews on final.")

    return LOIReviewReport(
        reviews=reviews,
        must_push_count=must,
        should_push_count=should,
        partner_note=note,
    )


def render_loi_review_markdown(r: LOIReviewReport) -> str:
    lines = [
        "# LOI term sheet review",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Must-push: {r.must_push_count}",
        f"- Should-push: {r.should_push_count}",
        "",
        "| Term | Seller proposal | Partner counter | Priority | Rationale |",
        "|---|---|---|---|---|",
    ]
    for rv in r.reviews:
        lines.append(
            f"| {rv.term} | {rv.seller_proposal} | "
            f"{rv.partner_counter} | {rv.priority} | {rv.rationale} |"
        )
    return "\n".join(lines)
