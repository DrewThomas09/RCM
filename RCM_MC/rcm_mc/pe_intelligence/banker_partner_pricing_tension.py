"""Banker-vs-partner pricing tension — quantify the gap and categorize.

Partner statement: "Every process has a pricing
tension. The banker says 12x is where it clears.
Your math says 10.5x is where your IRR still clears.
That 1.5-turn gap is the tension. If I can bridge
it with operational upside, I'm in. If the bridge
requires top-quartile execution to close, I'm out.
The gap IS the partner conversation."

Distinct from:
- `banker_narrative_decoder` — pitch language tactics.
- `cycle_timing_pricing_check` — market-cycle sanity.
- `pricing_concession_ladder` — concession moves.
- `pricing_power_diagnostic` — company-side pricing
  power.

This module **quantifies the banker-vs-partner
tension**:
- banker-suggested price (or multiple)
- partner walk-away price
- gap in turns and $M
- bridge feasibility given upside levers
- verdict: accept_pitch / bridgeable / walk
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BankerPricingTensionInputs:
    ebitda_base_m: float = 50.0
    banker_suggested_multiple: float = 12.0
    partner_walkaway_multiple: float = 10.5
    operational_upside_turns: float = 0.0
    """Turns of upside sourced from operational levers
    that would justify closing above walk-away."""
    top_quartile_execution_required: bool = False
    competing_bidders_count: int = 3


@dataclass
class BankerPricingTensionReport:
    banker_implied_ev_m: float = 0.0
    partner_implied_ev_m: float = 0.0
    gap_turns: float = 0.0
    gap_dollars_m: float = 0.0
    bridge_turns_available: float = 0.0
    residual_gap_turns: float = 0.0
    verdict: str = "bridgeable"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "banker_implied_ev_m": self.banker_implied_ev_m,
            "partner_implied_ev_m":
                self.partner_implied_ev_m,
            "gap_turns": self.gap_turns,
            "gap_dollars_m": self.gap_dollars_m,
            "bridge_turns_available":
                self.bridge_turns_available,
            "residual_gap_turns": self.residual_gap_turns,
            "verdict": self.verdict,
            "partner_note": self.partner_note,
        }


def read_banker_pricing_tension(
    inputs: BankerPricingTensionInputs,
) -> BankerPricingTensionReport:
    banker_ev = (
        inputs.ebitda_base_m *
        inputs.banker_suggested_multiple
    )
    partner_ev = (
        inputs.ebitda_base_m *
        inputs.partner_walkaway_multiple
    )
    gap_turns = (
        inputs.banker_suggested_multiple -
        inputs.partner_walkaway_multiple
    )
    gap_dollars = banker_ev - partner_ev

    bridge = inputs.operational_upside_turns
    residual = gap_turns - bridge

    if gap_turns <= 0:
        verdict = "accept_pitch"
        note = (
            f"Banker's {inputs.banker_suggested_multiple:.1f}× "
            f"is at or below partner walk-away "
            f"{inputs.partner_walkaway_multiple:.1f}×. "
            "Price at the pitch; no tension."
        )
    elif residual <= 0:
        verdict = "bridgeable"
        note = (
            f"Gap {gap_turns:.1f}× "
            f"(${gap_dollars:.0f}M) is fully "
            f"bridged by "
            f"{inputs.operational_upside_turns:.1f}× "
            "operational upside. Move to confirmatory "
            "on the specific levers that justify the "
            "bridge."
        )
    elif residual <= 0.5:
        verdict = "thin_bridge"
        note = (
            f"Residual gap {residual:.1f}× after "
            f"operational upside. Acceptable only if "
            "competing-bidder pressure is real and "
            "banker pitch holds up."
        )
        if inputs.top_quartile_execution_required:
            note += (
                " Also flagged: closing this gap "
                "requires top-quartile execution — "
                "not base case."
            )
    else:
        verdict = "walk"
        note = (
            f"Residual gap {residual:.1f}× after all "
            "operational upside. No bridge the IC can "
            "defend. Walk, or let the seller find a "
            "sponsor with a looser IRR standard."
        )
        if inputs.competing_bidders_count <= 1:
            note += (
                " Low competitive pressure "
                f"({inputs.competing_bidders_count} "
                "bidder(s)) means seller will come "
                "back after failed round."
            )

    return BankerPricingTensionReport(
        banker_implied_ev_m=round(banker_ev, 2),
        partner_implied_ev_m=round(partner_ev, 2),
        gap_turns=round(gap_turns, 3),
        gap_dollars_m=round(gap_dollars, 2),
        bridge_turns_available=round(bridge, 3),
        residual_gap_turns=round(residual, 3),
        verdict=verdict,
        partner_note=note,
    )


def render_banker_pricing_tension_markdown(
    r: BankerPricingTensionReport,
) -> str:
    lines = [
        "# Banker-vs-partner pricing tension",
        "",
        f"_Verdict: **{r.verdict}**_ — {r.partner_note}",
        "",
        f"- Banker EV: ${r.banker_implied_ev_m:.0f}M",
        f"- Partner walk-away EV: "
        f"${r.partner_implied_ev_m:.0f}M",
        f"- Gap: {r.gap_turns:+.1f}× "
        f"(${r.gap_dollars_m:+.0f}M)",
        f"- Bridge available: "
        f"{r.bridge_turns_available:.1f}×",
        f"- Residual after bridge: "
        f"{r.residual_gap_turns:+.1f}×",
    ]
    return "\n".join(lines)
