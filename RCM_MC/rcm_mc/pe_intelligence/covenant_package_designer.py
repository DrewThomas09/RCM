"""Covenant package designer — partner's basket recommendation.

Partner statement: "The covenant package is where the
equity gets wiped out. A bad covenant trips on noise; a
good one trips only when the thesis is actually broken."

`covenant_monitor.py` tracks covenant compliance post-
close. This module is the *pre*-close partner advisory:
given the deal's stress profile, what covenant package
should we negotiate for?

Partners think about covenants across four dimensions:

1. **Maximum leverage ratio** — how much headroom above
   base EBITDA? Partner rule of thumb: base leverage +
   0.5-1.0x cushion, OR worst-year bear leverage + 0.25x
   — whichever is higher.

2. **Step-downs** — quarterly glide path that tightens
   over the hold. Aggressive step-downs strangle growth
   capex; loose step-downs waste spread.

3. **Cure rights** — equity cure (sponsor injects equity
   to cure a trip) is standard for 4 of 8 quarters; more
   is seller-friendly, less is buyer-friendly.

4. **Fixed-charge coverage / interest coverage** — often
   a floor-level test (≥ 1.1x) vs. seller's desired ≥ 2x.
   Worst-year coverage under shock schedule tells us
   where to set it.

### Worked partner logic

Given:
- Base EBITDA $75M, base leverage 5.5x (debt $412.5M).
- Worst-year bear EBITDA (from hold_period_shock_schedule)
  $63M → worst leverage 6.54x.
- Base EBITDA volatility (std dev % of revenue): 8%.

Partner-recommended max leverage: **7.0x** (worst-year +
0.5x cushion). Anything tighter trips on volatility; looser
wastes spread.

### Output

- `recommended_max_leverage` with basis.
- Step-down schedule (quarterly).
- Cure rights sized.
- Interest coverage floor.
- Partner note: `accept`, `negotiate`, `walk`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CovenantDesignInputs:
    base_ebitda_m: float
    base_leverage: float               # x times base EBITDA
    worst_year_ebitda_m: float         # from shock schedule
    worst_year_leverage: float
    ebitda_volatility_pct: float = 0.08   # std dev / base
    hold_years: float = 5.0
    seller_proposed_max_leverage: float = 8.0
    seller_proposed_cure_quarters: int = 2
    base_interest_coverage: float = 3.0


@dataclass
class StepDown:
    quarter: int
    max_leverage: float


@dataclass
class CovenantPackage:
    recommended_max_leverage: float
    leverage_cushion: float
    step_downs: List[StepDown] = field(default_factory=list)
    recommended_cure_quarters: int = 4
    recommended_int_coverage_floor: float = 1.5
    partner_verdict: str = ""          # accept/negotiate/walk
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommended_max_leverage":
                self.recommended_max_leverage,
            "leverage_cushion": self.leverage_cushion,
            "step_downs": [
                {"quarter": s.quarter,
                 "max_leverage": s.max_leverage}
                for s in self.step_downs
            ],
            "recommended_cure_quarters":
                self.recommended_cure_quarters,
            "recommended_int_coverage_floor":
                self.recommended_int_coverage_floor,
            "partner_verdict": self.partner_verdict,
            "partner_note": self.partner_note,
        }


def design_covenant_package(
    inputs: CovenantDesignInputs,
) -> CovenantPackage:
    # Recommended max leverage = max of:
    # (a) base leverage + 1.0x cushion
    # (b) worst-year leverage + 0.5x cushion
    # (c) base leverage × (1 + 2 × volatility)   — volatility-based
    a = inputs.base_leverage + 1.0
    b = inputs.worst_year_leverage + 0.5
    c = inputs.base_leverage * (1.0 + 2.0 *
                                  inputs.ebitda_volatility_pct)
    recommended = round(max(a, b, c), 2)
    cushion = round(recommended - inputs.base_leverage, 2)

    # Step-downs: glide from (recommended) to (base + 0.5)
    # over the hold, quarterly.
    step_downs: List[StepDown] = []
    end_leverage = max(inputs.base_leverage + 0.5,
                        inputs.worst_year_leverage + 0.25)
    n_quarters = max(1, int(inputs.hold_years * 4))
    for q in range(1, n_quarters + 1):
        frac = q / n_quarters
        lev = recommended - (recommended - end_leverage) * frac
        step_downs.append(StepDown(
            quarter=q, max_leverage=round(lev, 2)
        ))

    # Cure quarters: 4 of 8 is buyer-standard. Seller proposing
    # 2 should be pushed to 4.
    recommended_cures = max(4, inputs.seller_proposed_cure_quarters)

    # Interest coverage floor: half of base, but floor at 1.25.
    int_coverage_floor = max(
        1.25, round(inputs.base_interest_coverage * 0.5, 2)
    )

    # Verdict:
    if inputs.seller_proposed_max_leverage >= recommended + 0.5:
        verdict = "accept"
        note = (f"Seller proposed {inputs.seller_proposed_max_leverage:.2f}x "
                f"vs. our recommended {recommended:.2f}x — "
                f"{inputs.seller_proposed_max_leverage - recommended:.2f}x "
                "of additional cushion. Accept as offered.")
    elif inputs.seller_proposed_max_leverage >= recommended:
        verdict = "accept"
        note = (f"Seller at {inputs.seller_proposed_max_leverage:.2f}x, "
                f"our target {recommended:.2f}x. Accept; focus "
                "negotiation on cure rights and step-down pace.")
    elif inputs.seller_proposed_max_leverage >= recommended - 0.3:
        verdict = "negotiate"
        note = (f"Seller at {inputs.seller_proposed_max_leverage:.2f}x "
                f"is ~0.3x tight vs our {recommended:.2f}x. "
                "Negotiate up to our target or add cure rights "
                "and step-down runway to compensate.")
    else:
        verdict = "walk"
        note = (f"Seller proposed {inputs.seller_proposed_max_leverage:.2f}x "
                f"is more than 0.3x below our {recommended:.2f}x "
                "target. Covenant trips on volatility alone — "
                "walk or fully rebuild the package.")

    # Add worst-year framing if material.
    if inputs.worst_year_leverage > inputs.base_leverage + 0.75:
        note += (f" Worst-year projected at "
                 f"{inputs.worst_year_leverage:.2f}x; covenant "
                 "package must price this, not base case.")

    return CovenantPackage(
        recommended_max_leverage=recommended,
        leverage_cushion=cushion,
        step_downs=step_downs,
        recommended_cure_quarters=recommended_cures,
        recommended_int_coverage_floor=int_coverage_floor,
        partner_verdict=verdict,
        partner_note=note,
    )


def render_covenant_package_markdown(
    p: CovenantPackage,
) -> str:
    lines = [
        "# Covenant package — partner recommendation",
        "",
        f"**Verdict:** `{p.partner_verdict}`",
        "",
        f"_{p.partner_note}_",
        "",
        f"- Recommended max leverage: "
        f"{p.recommended_max_leverage:.2f}x",
        f"- Cushion above base: {p.leverage_cushion:.2f}x",
        f"- Recommended cure quarters (of 8): "
        f"{p.recommended_cure_quarters}",
        f"- Interest coverage floor: "
        f"{p.recommended_int_coverage_floor:.2f}x",
        "",
        "## Step-down glide path",
        "",
        "| Quarter | Max leverage |",
        "|---|---|",
    ]
    for s in p.step_downs:
        lines.append(f"| Q{s.quarter} | {s.max_leverage:.2f}x |")
    return "\n".join(lines)
