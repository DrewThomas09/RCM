"""EBITDA normalization — reported to partner-prudent Adjusted EBITDA.

Sellers market "Adjusted EBITDA" aggressively. Partners normalize
back to something defensible. This module takes the reported
bridge and classifies each adjustment by partner-prudence:

- **Defensible** — one-time legal settlement, one-time cyber
  remediation cost, founder-family non-economic salary add-back,
  public-company prep costs, CEO severance.
- **Defensible-with-support** — synergy run-rate (proven via LOI),
  acquired revenue annualization (contract signed), cost takeout
  already executed (signed severance).
- **Aggressive** — projected synergies (not realized), run-rate
  revenue from pipeline, normalization for "non-recurring" items
  that recur every year.
- **Reject** — sponsor fees (pays itself), pre-opening losses
  (shouldn't add back losses), stock-based comp add-back for
  sponsor-portfolio co (this is real cost).

Output: a **partner-prudent Adjusted EBITDA** + line-by-line
haircut and partner note.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


CATEGORY_ORDER = ["defensible", "defensible_with_support",
                  "aggressive", "reject"]

# Partner haircut by category (fraction accepted).
HAIRCUTS = {
    "defensible": 1.00,
    "defensible_with_support": 0.70,  # 70% credit pending support
    "aggressive": 0.30,               # 30% credit (sandbag)
    "reject": 0.00,                   # full haircut
}


@dataclass
class EBITDAItem:
    label: str
    amount_m: float                       # positive adds back, negative subtracts
    category: str                         # one of CATEGORY_ORDER
    rationale: str = ""


@dataclass
class NormalizationResult:
    reported_ebitda_m: float
    seller_adjusted_ebitda_m: float
    partner_adjusted_ebitda_m: float      # after haircuts
    total_seller_adjustments_m: float
    total_partner_adjustments_m: float
    rejected_m: float
    items: List[Dict[str, Any]] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reported_ebitda_m": self.reported_ebitda_m,
            "seller_adjusted_ebitda_m": self.seller_adjusted_ebitda_m,
            "partner_adjusted_ebitda_m": self.partner_adjusted_ebitda_m,
            "total_seller_adjustments_m": self.total_seller_adjustments_m,
            "total_partner_adjustments_m": self.total_partner_adjustments_m,
            "rejected_m": self.rejected_m,
            "items": list(self.items),
            "partner_note": self.partner_note,
        }


def normalize_ebitda(reported_ebitda_m: float,
                     items: List[EBITDAItem]) -> NormalizationResult:
    """Apply partner haircuts to seller's EBITDA bridge."""
    seller_total = sum(i.amount_m for i in items)
    seller_adj = reported_ebitda_m + seller_total

    partner_accepted = 0.0
    rejected_amount = 0.0
    line_items: List[Dict[str, Any]] = []
    for it in items:
        cat = it.category if it.category in HAIRCUTS else "aggressive"
        haircut = HAIRCUTS[cat]
        partner_credit = it.amount_m * haircut
        rejected = it.amount_m - partner_credit
        partner_accepted += partner_credit
        rejected_amount += rejected
        line_items.append({
            "label": it.label,
            "amount_m": round(it.amount_m, 2),
            "category": cat,
            "partner_credit_m": round(partner_credit, 2),
            "haircut_applied_m": round(rejected, 2),
            "rationale": it.rationale,
        })

    partner_adj = reported_ebitda_m + partner_accepted

    # Gap between seller's claim and partner's number.
    gap = seller_adj - partner_adj
    gap_pct = (gap / seller_adj * 100) if seller_adj > 0 else 0.0

    if gap_pct >= 20:
        note = (f"Seller's Adjusted EBITDA (${seller_adj:,.1f}M) is "
                f"{gap_pct:.0f}% above partner's number "
                f"(${partner_adj:,.1f}M). Significant bridge — "
                "renegotiate purchase price off partner view.")
    elif gap_pct >= 10:
        note = (f"Seller's bridge carries {gap_pct:.0f}% haircut vs "
                "partner — modest renegotiation leverage.")
    else:
        note = (f"Seller's bridge largely supportable "
                f"(~{gap_pct:.0f}% haircut).")

    return NormalizationResult(
        reported_ebitda_m=round(reported_ebitda_m, 2),
        seller_adjusted_ebitda_m=round(seller_adj, 2),
        partner_adjusted_ebitda_m=round(partner_adj, 2),
        total_seller_adjustments_m=round(seller_total, 2),
        total_partner_adjustments_m=round(partner_accepted, 2),
        rejected_m=round(rejected_amount, 2),
        items=line_items,
        partner_note=note,
    )


def render_normalization_markdown(r: NormalizationResult) -> str:
    lines = [
        "# EBITDA normalization",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Reported EBITDA: ${r.reported_ebitda_m:,.1f}M",
        f"- Seller's Adjusted: ${r.seller_adjusted_ebitda_m:,.1f}M",
        f"- Partner's Adjusted: ${r.partner_adjusted_ebitda_m:,.1f}M",
        f"- Total haircut: ${r.rejected_m:,.1f}M",
        "",
        "## Line items",
        "",
        "| Label | Amount | Category | Partner credit | Haircut |",
        "|---|---:|---|---:|---:|",
    ]
    for i in r.items:
        lines.append(
            f"| {i['label']} | ${i['amount_m']:,.2f}M | "
            f"{i['category']} | ${i['partner_credit_m']:,.2f}M | "
            f"${i['haircut_applied_m']:,.2f}M |"
        )
    return "\n".join(lines)
