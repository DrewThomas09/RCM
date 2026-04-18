"""Local market intensity — how crowded is the block?

Partner statement: "HHI at the national level is noise.
What matters is the MSA. If we're the 6th urgent-care
operator in Phoenix, pricing is a race to the bottom.
If we're the only GI practice in a 50-mile radius, I
can underwrite growth."

Distinct from `market_structure` (national HHI / CR3 /
CR5 for sector). This module measures **local market
intensity** — the partner's actual competitive read of
the MSA / radius / specialty combination the target
operates in.

### 6 intensity signals

1. **direct_competitors_local** — count of head-to-head
   competitors in target's market radius.
2. **new_entrant_announced_12mo** — any announced new
   entry in past year.
3. **dominant_payer_share_local** — share of the single
   largest local payer (high = price-taker risk).
4. **physician_labor_pool_depth** — local supply of
   needed physician specialty (thin = wage inflation
   risk).
5. **consumer_retail_encroachment** — CVS, Amazon,
   Walmart, Optum moving in.
6. **state_con_regulatory_friction** — CON / certificate-
   of-need + licensure complexity blocks new entry
   (protective) vs. open-market (more competition).

### Tier ladder

- **protected_local** (≤ 1 flag + CON state) — pricing
  power; partner can underwrite growth.
- **balanced** (2 flags) — normal competition; model at
  peer peer-average.
- **crowded** (3 flags) — price pressure; haircut
  projected growth.
- **hypercompetitive** (4+ flags) — price-taker,
  commoditization risk; reprice or walk.

### Why local matters more than national

Healthcare services are local-delivered. A "national
rollup" is actually a collection of MSA duopolies or
monopolies. Partners make the MSA-level call at
underwrite, then aggregate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LocalMarketFlag:
    name: str
    triggered: bool
    partner_comment: str


@dataclass
class LocalMarketInputs:
    direct_competitors_local: int = 0
    new_entrant_announced_12mo: bool = False
    dominant_payer_share_local: float = 0.0
    physician_labor_pool_shallow: bool = False
    consumer_retail_encroachment: bool = False
    state_con_protected: bool = False


@dataclass
class LocalMarketReport:
    tier: str                              # protected/balanced/crowded/hyper
    triggered_count: int
    flags: List[LocalMarketFlag] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier,
            "triggered_count": self.triggered_count,
            "flags": [
                {"name": f.name,
                 "triggered": f.triggered,
                 "partner_comment": f.partner_comment}
                for f in self.flags
            ],
            "partner_note": self.partner_note,
        }


def score_local_market_intensity(
    inputs: LocalMarketInputs,
) -> LocalMarketReport:
    flags: List[LocalMarketFlag] = []

    # Flag 1: >= 3 direct local competitors.
    crowded_comp = inputs.direct_competitors_local >= 3
    flags.append(LocalMarketFlag(
        name="direct_competitors_local_gte_3",
        triggered=crowded_comp,
        partner_comment=(
            f"{inputs.direct_competitors_local} direct local "
            "competitors — head-to-head pricing."
            if crowded_comp else
            f"{inputs.direct_competitors_local} direct local "
            "competitors — manageable intensity."
        ),
    ))

    # Flag 2: new entrant in past 12 months.
    new_entrant = inputs.new_entrant_announced_12mo
    flags.append(LocalMarketFlag(
        name="new_entrant_announced_12mo",
        triggered=new_entrant,
        partner_comment=(
            "New entrant announced in past 12 months — "
            "pricing pressure imminent."
            if new_entrant else
            "No recently announced new entrant."
        ),
    ))

    # Flag 3: dominant local payer > 45%.
    dominant = inputs.dominant_payer_share_local >= 0.45
    flags.append(LocalMarketFlag(
        name="dominant_local_payer_gte_45pct",
        triggered=dominant,
        partner_comment=(
            f"Dominant local payer "
            f"{inputs.dominant_payer_share_local*100:.0f}% "
            "share — provider is a price-taker."
            if dominant else
            "Local payer mix diversified; provider has "
            "some leverage."
        ),
    ))

    # Flag 4: shallow physician labor pool.
    shallow_pool = inputs.physician_labor_pool_shallow
    flags.append(LocalMarketFlag(
        name="physician_labor_pool_shallow",
        triggered=shallow_pool,
        partner_comment=(
            "Physician labor pool shallow — wage "
            "inflation risk above national peer."
            if shallow_pool else
            "Adequate physician labor pool locally."
        ),
    ))

    # Flag 5: consumer retail encroachment.
    retail = inputs.consumer_retail_encroachment
    flags.append(LocalMarketFlag(
        name="consumer_retail_encroachment",
        triggered=retail,
        partner_comment=(
            "CVS / Walmart / Amazon / Optum moving into "
            "market — commoditization risk."
            if retail else
            "No consumer / retail encroachment flagged."
        ),
    ))

    triggered = sum(1 for f in flags if f.triggered)

    # Tier ladder — CON protection pulls back 1 flag.
    effective_flags = triggered
    if inputs.state_con_protected and effective_flags > 0:
        effective_flags -= 1   # CON protects against competition

    if effective_flags >= 4:
        tier = "hypercompetitive"
        note = (
            f"{triggered} local-intensity flag(s); "
            "hypercompetitive market. Partner: price-"
            "taker dynamic — reprice or walk."
        )
    elif effective_flags == 3:
        tier = "crowded"
        note = (
            f"{triggered} flag(s); crowded market. "
            "Partner: haircut projected growth; commercial "
            "pricing power limited."
        )
    elif effective_flags == 2:
        tier = "balanced"
        note = (
            f"{triggered} flag(s); balanced competition. "
            "Model at peer-average growth; no structural "
            "gating."
        )
    else:
        tier = "protected_local"
        if inputs.state_con_protected:
            note = (
                "Protected local market (CON + low "
                "intensity). Partner: pricing power; "
                "can underwrite growth."
            )
        else:
            note = (
                "Low local intensity. Partner: proceed "
                "on growth thesis; monitor for entrants."
            )

    return LocalMarketReport(
        tier=tier,
        triggered_count=triggered,
        flags=flags,
        partner_note=note,
    )


def render_local_market_markdown(
    r: LocalMarketReport,
) -> str:
    lines = [
        "# Local market intensity",
        "",
        f"**Tier:** `{r.tier}`",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Flags triggered: {r.triggered_count} / "
        f"{len(r.flags)}",
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
