"""LOI drafter — generate a partner-voice term sheet from a review.

Partners kick off negotiations with a short LOI that hits 8-10 key
terms. This module composes an LOI draft from a PartnerReview +
negotiation position:

- Purchase price / structure.
- Exclusivity period.
- Diligence scope.
- Financing contingency.
- Management terms.
- Closing conditions.
- Non-binding vs binding components.

Output: a text LOI draft the partner edits to final.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .negotiation_position import NegotiationPosition
from .partner_review import PartnerReview


@dataclass
class LOIDraft:
    headline: str
    purchase_price_summary: str
    exclusivity_days: int
    diligence_scope: List[str]
    financing_terms: str
    management_terms: List[str]
    closing_conditions: List[str]
    binding_sections: List[str]
    non_binding_sections: List[str]
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "headline": self.headline,
            "purchase_price_summary": self.purchase_price_summary,
            "exclusivity_days": self.exclusivity_days,
            "diligence_scope": list(self.diligence_scope),
            "financing_terms": self.financing_terms,
            "management_terms": list(self.management_terms),
            "closing_conditions": list(self.closing_conditions),
            "binding_sections": list(self.binding_sections),
            "non_binding_sections": list(self.non_binding_sections),
            "partner_note": self.partner_note,
        }


# ── Helpers ────────────────────────────────────────────────────────

def _diligence_scope_from_review(review: PartnerReview) -> List[str]:
    scope = [
        "Financial — 3yr audited + quality of earnings",
        "Payer — top-10 contracts + denial history",
        "Operational — KPI trends + service-line P&L",
        "Regulatory — licensure + CMS history",
    ]
    # Add scope items based on flagged heuristics.
    ids = {h.id for h in review.heuristic_hits}
    if "payer_concentration_risk" in ids:
        scope.append("Payer concentration — specific contract deep-dive")
    if "ehr_migration_planned" in ids:
        scope.append("IT — EHR migration plan and vendor references")
    if "regulatory_inspection_open" in ids:
        scope.append("Regulatory — open inspection resolution plan")
    return scope


def _management_terms(review: PartnerReview) -> List[str]:
    return [
        "Retention agreements for top-5 executives; equity rollover 5-15%",
        "Non-compete + non-solicit 2 years post-close",
        "Long-term equity grant aligned to hold period",
        "Transition services — CEO retained ≥ 90 days post-close",
    ]


def _closing_conditions(review: PartnerReview) -> List[str]:
    conds = [
        "Satisfactory completion of diligence",
        "Customary third-party consents (landlords, payers, regulators)",
        "No material adverse change",
        "Accurate representations and warranties at close",
    ]
    ids = {h.id for h in review.heuristic_hits}
    if "covenant_headroom_tight" in ids:
        conds.append("Amended debt documents providing ≥ 25% covenant headroom")
    if "340b_margin_dependency" in ids:
        conds.append("Clear 340B program status with CMS")
    return conds


def _exclusivity_days(review: PartnerReview) -> int:
    rec = review.narrative.recommendation
    if rec == "STRONG_PROCEED":
        return 30
    if rec == "PROCEED":
        return 45
    if rec == "PROCEED_WITH_CAVEATS":
        return 60
    return 0  # no exclusivity on PASS


def compose_loi(
    review: PartnerReview,
    negotiation: NegotiationPosition,
    *,
    exclusivity_days: Optional[int] = None,
) -> LOIDraft:
    """Compose an LOI draft from a review + negotiation position."""
    name = review.deal_name or review.deal_id or "target"
    headline = f"Letter of Intent — {name}"
    if negotiation.anchor_price_m is not None:
        price_summary = (
            f"Purchase price: ${negotiation.anchor_price_m:,.1f}M "
            f"({negotiation.anchor_multiple:.2f}x EBITDA), "
            f"subject to customary adjustments."
        )
    else:
        price_summary = (
            "Purchase price: to be determined; will reflect partner-"
            "prudent multiple against diligenced EBITDA."
        )
    excl = exclusivity_days or _exclusivity_days(review)
    diligence = _diligence_scope_from_review(review)
    mgmt_terms = _management_terms(review)
    close_conds = _closing_conditions(review)

    binding = [
        "Exclusivity",
        "Confidentiality",
        "Expense-reimbursement",
        "Governing law",
    ]
    non_binding = [
        "Purchase price and structure",
        "Diligence scope",
        "Financing terms",
        "Management terms",
        "Closing conditions",
    ]

    if review.narrative.recommendation == "PASS":
        note = "LOI draft is placeholder only — review recommends PASS."
    else:
        note = "LOI draft ready for partner edit before delivery."

    return LOIDraft(
        headline=headline,
        purchase_price_summary=price_summary,
        exclusivity_days=excl,
        diligence_scope=diligence,
        financing_terms=("Debt financing commitment (5.5x EBITDA) + sponsor "
                         "equity. Financing condition included unless "
                         "pre-committed."),
        management_terms=mgmt_terms,
        closing_conditions=close_conds,
        binding_sections=binding,
        non_binding_sections=non_binding,
        partner_note=note,
    )


def render_loi_markdown(draft: LOIDraft) -> str:
    lines = [
        f"# {draft.headline}",
        "",
        "## Purchase price and structure",
        draft.purchase_price_summary,
        "",
        f"## Exclusivity",
        f"{draft.exclusivity_days} days from LOI execution.",
        "",
        "## Diligence scope",
        "",
    ]
    for item in draft.diligence_scope:
        lines.append(f"- {item}")
    lines.extend(["", "## Financing terms", draft.financing_terms])
    lines.extend(["", "## Management terms", ""])
    for item in draft.management_terms:
        lines.append(f"- {item}")
    lines.extend(["", "## Closing conditions", ""])
    for item in draft.closing_conditions:
        lines.append(f"- {item}")
    lines.extend(["", "## Binding vs non-binding", ""])
    lines.append(f"**Binding:** {', '.join(draft.binding_sections)}")
    lines.append("")
    lines.append(f"**Non-binding:** {', '.join(draft.non_binding_sections)}")
    lines.extend(["", "---", "", f"_{draft.partner_note}_"])
    return "\n".join(lines)
