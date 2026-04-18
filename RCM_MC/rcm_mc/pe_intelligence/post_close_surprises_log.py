"""Post-close surprises log — diligence miss-rate feedback loop.

A senior partner keeps a mental "diligence miss rate." If we
regularly miss 15%+ of post-close surprises, our process has a
systematic gap — and the fix is in the diligence template, not
the individual deals.

This module logs:

- **Known at close** — items the packet / QoL / QofE flagged.
- **Surprises** — items that emerged post-close that were NOT
  in the packet.
- **Miss category** — operational / clinical / legal / financial /
  regulatory / cultural / market.
- **Financial impact** — $ effect on EBITDA or cash.

And produces a rolling portfolio-level diligence miss-rate
analysis: which categories miss the most often, which categories
underestimate dollars most, and partner-voice recommendations
for tightening the template.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Surprise:
    deal_name: str
    category: str                           # operational/clinical/legal/
                                            # financial/regulatory/
                                            # cultural/market
    description: str
    impact_ebitda_m: float                  # negative = hit
    was_known_at_close: bool = False
    flagged_severity_at_close: str = "none"  # none/low/medium/high
    actual_severity_post_close: str = "medium"
    months_post_close: int = 0


@dataclass
class CategoryStats:
    category: str
    total_items: int
    missed_items: int
    miss_rate: float
    avg_impact_missed_m: float
    partner_commentary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "total_items": self.total_items,
            "missed_items": self.missed_items,
            "miss_rate": self.miss_rate,
            "avg_impact_missed_m": self.avg_impact_missed_m,
            "partner_commentary": self.partner_commentary,
        }


@dataclass
class MissRateReport:
    total_items: int
    missed_items: int
    overall_miss_rate: float
    overall_missed_impact_m: float
    category_stats: List[CategoryStats] = field(default_factory=list)
    worst_category: str = ""
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_items": self.total_items,
            "missed_items": self.missed_items,
            "overall_miss_rate": self.overall_miss_rate,
            "overall_missed_impact_m": self.overall_missed_impact_m,
            "category_stats": [c.to_dict() for c in self.category_stats],
            "worst_category": self.worst_category,
            "partner_note": self.partner_note,
        }


def _category_commentary(cat: str, miss_rate: float,
                          avg_impact: float) -> str:
    # Severity reads.
    if miss_rate >= 0.30:
        rate_part = (f"{miss_rate*100:.0f}% miss rate is a systematic "
                     f"{cat} gap in the diligence template — fix "
                     "before the next deal in this subsector.")
    elif miss_rate >= 0.15:
        rate_part = (f"{miss_rate*100:.0f}% miss rate on {cat} is "
                     "above tolerance; review template.")
    else:
        rate_part = f"{miss_rate*100:.0f}% miss rate is within norms."

    if avg_impact < -2.0:
        dollar_part = (f" When missed, {cat} items average "
                       f"${abs(avg_impact):,.1f}M of EBITDA hit — "
                       "this is where portfolio dollars bleed.")
    elif avg_impact < 0:
        dollar_part = (f" Average missed impact is modest "
                       f"(${abs(avg_impact):,.1f}M).")
    else:
        dollar_part = ""

    return rate_part + dollar_part


def compute_miss_rate(surprises: List[Surprise]) -> MissRateReport:
    total = len(surprises)
    missed = [s for s in surprises if not s.was_known_at_close]
    overall_miss = len(missed) / total if total > 0 else 0.0
    overall_impact = sum(s.impact_ebitda_m for s in missed)

    # Per-category stats.
    by_cat: Dict[str, List[Surprise]] = {}
    for s in surprises:
        by_cat.setdefault(s.category, []).append(s)

    cats: List[CategoryStats] = []
    for cat, items in by_cat.items():
        item_count = len(items)
        cat_missed = [i for i in items if not i.was_known_at_close]
        miss_rate = len(cat_missed) / max(1, item_count)
        avg_imp = (sum(i.impact_ebitda_m for i in cat_missed)
                    / max(1, len(cat_missed))
                    if cat_missed else 0.0)
        cats.append(CategoryStats(
            category=cat,
            total_items=item_count,
            missed_items=len(cat_missed),
            miss_rate=round(miss_rate, 4),
            avg_impact_missed_m=round(avg_imp, 2),
            partner_commentary=_category_commentary(cat, miss_rate,
                                                       avg_imp),
        ))

    cats.sort(key=lambda c: c.miss_rate, reverse=True)
    worst = cats[0].category if cats else ""

    if total == 0:
        note = "No surprise log entries yet."
    elif overall_miss >= 0.25:
        note = (f"Overall miss rate {overall_miss*100:.0f}% across "
                f"{total} items — the diligence template is "
                f"systematically weak in {worst}. ${-overall_impact:,.1f}M "
                "of bled EBITDA across the missed items.")
    elif overall_miss >= 0.15:
        note = (f"Miss rate {overall_miss*100:.0f}% is above "
                f"tolerance; worst category is {worst}. Review "
                "template after next close.")
    else:
        note = (f"Miss rate {overall_miss*100:.0f}% is within partner "
                f"tolerance across {total} items.")

    return MissRateReport(
        total_items=total,
        missed_items=len(missed),
        overall_miss_rate=round(overall_miss, 4),
        overall_missed_impact_m=round(overall_impact, 2),
        category_stats=cats,
        worst_category=worst,
        partner_note=note,
    )


def render_miss_rate_markdown(r: MissRateReport) -> str:
    lines = [
        "# Post-close surprises log",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Total items: {r.total_items}",
        f"- Missed (not known at close): {r.missed_items}",
        f"- Overall miss rate: {r.overall_miss_rate*100:.0f}%",
        f"- Missed EBITDA impact: "
        f"${r.overall_missed_impact_m:,.1f}M",
        f"- Worst category: {r.worst_category}",
        "",
        "| Category | Items | Missed | Miss % | Avg missed $M | Commentary |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for c in r.category_stats:
        lines.append(
            f"| {c.category} | {c.total_items} | {c.missed_items} | "
            f"{c.miss_rate*100:.0f}% | "
            f"${c.avg_impact_missed_m:,.2f}M | "
            f"{c.partner_commentary} |"
        )
    return "\n".join(lines)
