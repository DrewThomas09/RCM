"""Thesis-break price — partner's max justifiable bid.

Partner statement: "Every deal has a walk number.
Below it the math works; above it doesn't. I want that
number on the page before the first bid goes out."

Distinct from:
- `seller_math_reverse` — what seller must believe.
- `exit_multiple_compression_scenarios` — stresses exit.
- `pricing_concession_ladder` — negotiation sequence.

This module computes the **partner's maximum justifiable
price** given the deal's thesis + pattern risk +
pre-mortem strength + archetype shape. Each risk layer
translates to a price haircut from the seller's ask.

### Haircut layers

1. **Pre-mortem strength** — strong pre-mortem → 10%
   haircut; moderate → 5%; thin → 0%.
2. **Thesis chain contradicted links** — each contradicted
   link → 4%.
3. **Compound pattern risks** — each theme firing across
   ≥ 2 libraries → 3%.
4. **Failure archetype matches** — each shape archetype →
   2%.
5. **Cycle multiple dependence** — if multiple-expansion
   share > 30% → 5% haircut.
6. **Referral single-point-of-failure** → 4%.
7. **Turnaround thesis without operator** → 6%.

### Output

- Base price (seller's ask or modeled base).
- Cumulative haircut % and $.
- Partner walk-away price.
- Named haircut items (partner reads these in the memo).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BreakPriceInputs:
    base_price_m: float
    pre_mortem_strength: str = "thin"       # thin/moderate/strong
    thesis_contradicted_links_count: int = 0
    compound_pattern_risks_count: int = 0
    failure_archetype_matches_count: int = 0
    multiple_expansion_share_pct: float = 0.0   # 0.0-1.0
    referral_single_point_of_failure: bool = False
    turnaround_without_operator: bool = False


@dataclass
class HaircutLine:
    source: str
    pct: float
    dollars_m: float
    partner_rationale: str


@dataclass
class BreakPriceReport:
    base_price_m: float
    walk_away_price_m: float
    total_haircut_pct: float
    total_haircut_m: float
    lines: List[HaircutLine] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_price_m": self.base_price_m,
            "walk_away_price_m": self.walk_away_price_m,
            "total_haircut_pct": self.total_haircut_pct,
            "total_haircut_m": self.total_haircut_m,
            "lines": [
                {"source": l.source, "pct": l.pct,
                 "dollars_m": l.dollars_m,
                 "partner_rationale": l.partner_rationale}
                for l in self.lines
            ],
            "partner_note": self.partner_note,
        }


def compute_thesis_break_price(
    inputs: BreakPriceInputs,
) -> BreakPriceReport:
    base = max(0.01, inputs.base_price_m)
    lines: List[HaircutLine] = []

    pm = {"strong": 0.10, "moderate": 0.05,
          "thin": 0.0}.get(inputs.pre_mortem_strength, 0.0)
    if pm > 0:
        lines.append(HaircutLine(
            source="pre_mortem",
            pct=pm,
            dollars_m=round(base * pm, 2),
            partner_rationale=(
                f"Pre-mortem reads {inputs.pre_mortem_strength}; "
                "price in the named failure narrative."
            ),
        ))

    chain_haircut = 0.04 * inputs.thesis_contradicted_links_count
    if chain_haircut > 0:
        lines.append(HaircutLine(
            source="thesis_chain_contradictions",
            pct=chain_haircut,
            dollars_m=round(base * chain_haircut, 2),
            partner_rationale=(
                f"{inputs.thesis_contradicted_links_count} "
                "contradicted thesis link(s); the chain "
                "breaks here."
            ),
        ))

    compound_haircut = 0.03 * inputs.compound_pattern_risks_count
    if compound_haircut > 0:
        lines.append(HaircutLine(
            source="compound_pattern_risks",
            pct=compound_haircut,
            dollars_m=round(base * compound_haircut, 2),
            partner_rationale=(
                f"{inputs.compound_pattern_risks_count} "
                "compound risk theme(s) firing across "
                "≥ 2 libraries."
            ),
        ))

    archetype_haircut = (
        0.02 * inputs.failure_archetype_matches_count
    )
    if archetype_haircut > 0:
        lines.append(HaircutLine(
            source="failure_archetypes",
            pct=archetype_haircut,
            dollars_m=round(base * archetype_haircut, 2),
            partner_rationale=(
                f"{inputs.failure_archetype_matches_count} "
                "shape-level failure archetype(s)."
            ),
        ))

    if inputs.multiple_expansion_share_pct > 0.30:
        pct = 0.05
        lines.append(HaircutLine(
            source="cycle_multiple_dependence",
            pct=pct,
            dollars_m=round(base * pct, 2),
            partner_rationale=(
                f"{inputs.multiple_expansion_share_pct*100:.0f}% "
                "of MOIC from multiple expansion — cycle-"
                "dependent; partner haircuts."
            ),
        ))

    if inputs.referral_single_point_of_failure:
        pct = 0.04
        lines.append(HaircutLine(
            source="referral_single_point_of_failure",
            pct=pct,
            dollars_m=round(base * pct, 2),
            partner_rationale=(
                "Single-referrer concentration without "
                "contract mitigation."
            ),
        ))

    if inputs.turnaround_without_operator:
        pct = 0.06
        lines.append(HaircutLine(
            source="turnaround_without_operator",
            pct=pct,
            dollars_m=round(base * pct, 2),
            partner_rationale=(
                "Turnaround thesis without identified "
                "operator; partner-reject at base price."
            ),
        ))

    total_pct = sum(l.pct for l in lines)
    # Cap at 40% — beyond that partner walks entirely.
    total_pct = min(0.40, total_pct)
    total_dollars = round(base * total_pct, 2)
    walk_away = round(base - total_dollars, 2)

    if total_pct >= 0.25:
        note = (
            f"Cumulative haircut {total_pct*100:.0f}% "
            f"(${total_dollars:,.0f}M off base "
            f"${base:,.0f}M). Partner: walk-away "
            f"${walk_away:,.0f}M. If seller won't accept, "
            "pass."
        )
    elif total_pct >= 0.10:
        note = (
            f"Haircut {total_pct*100:.0f}% "
            f"(${total_dollars:,.0f}M). Walk-away "
            f"${walk_away:,.0f}M — use as LOI target, "
            "not ask-match."
        )
    elif total_pct > 0:
        note = (
            f"Light haircut {total_pct*100:.1f}%. Walk-"
            f"away ${walk_away:,.0f}M. Modest "
            "negotiation room."
        )
    else:
        note = (
            f"No thesis-break haircuts. Walk-away = base "
            f"${base:,.0f}M."
        )

    return BreakPriceReport(
        base_price_m=round(base, 2),
        walk_away_price_m=walk_away,
        total_haircut_pct=round(total_pct, 4),
        total_haircut_m=total_dollars,
        lines=lines,
        partner_note=note,
    )


def render_break_price_markdown(
    r: BreakPriceReport,
) -> str:
    lines = [
        "# Thesis-break price",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Base: ${r.base_price_m:,.1f}M",
        f"- Walk-away: ${r.walk_away_price_m:,.1f}M",
        f"- Total haircut: "
        f"{r.total_haircut_pct*100:.1f}% "
        f"(${r.total_haircut_m:,.1f}M)",
        "",
        "| Source | Haircut % | $M | Partner rationale |",
        "|---|---|---|---|",
    ]
    for l in r.lines:
        lines.append(
            f"| {l.source} | {l.pct*100:.1f}% | "
            f"${l.dollars_m:,.1f}M | "
            f"{l.partner_rationale} |"
        )
    return "\n".join(lines)
