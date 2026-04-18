"""Seller math reverse-engineer — what must the seller believe?

Partner statement: "The seller isn't stupid. If they ask
16x, they believe something specific about margin, growth,
and exit. I want to know what that is before I counter."

Deal pricing is the intersection of two private views:

- **Buyer's math**: stated EBITDA × realistic exit multiple
  ÷ target MOIC, solved for entry price.
- **Seller's math**: stated EBITDA × seller's implied exit
  multiple × their assumed growth, solved for entry price.

When asks diverge from our base case, the partner's job is
to reverse-engineer **what the seller must be assuming** to
justify their ask. Three variables can close the gap:

1. **Implied exit multiple** — seller thinks the market
   will pay more at exit than we do.
2. **Implied EBITDA growth** — seller thinks base EBITDA
   compounds faster than we believe.
3. **Implied margin expansion** — seller thinks operating
   leverage will expand margins beyond peer band.

This module takes buyer base assumptions + seller ask and
solves for the implicit seller assumption on each of those
three variables **holding the other two constant**. Partner
then reads each implied assumption against peer benchmarks
to decide:

- If the implied **exit multiple** is already at cycle
  peak, seller is betting on cycle extension → partner
  counter: price off cycle-average exit.
- If the implied **EBITDA growth** assumes 8%/yr organic,
  seller's forecasting a market we don't see → partner
  counter: price off mid-single-digit growth.
- If the implied **margin expansion** is 400+ bps beyond
  peer ceiling, seller believes in operator synergies we
  don't → partner counter: discount to peer-ceiling case.

### Partner's real-world use

In negotiation, the partner doesn't argue "your price is
too high." They argue "your price implies an exit multiple
of 14x or growth of 9%/yr — which of those are you willing
to guarantee?"
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SellerMathInputs:
    buyer_base_ebitda_m: float
    buyer_base_exit_multiple: float          # what we believe
    buyer_base_ebitda_growth_pct: float      # annual
    buyer_base_margin_expansion_bps: float   # total over hold
    hold_years: float
    seller_ask_price_m: float                # headline enterprise value
    target_moic: float = 2.5


@dataclass
class ImpliedAssumption:
    variable: str
    buyer_base: float
    implied_seller: float
    delta: float
    partner_interpretation: str


@dataclass
class SellerMathReport:
    buyer_implied_price_m: float
    seller_ask_price_m: float
    ask_premium_pct: float
    assumptions: List[ImpliedAssumption] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "buyer_implied_price_m": self.buyer_implied_price_m,
            "seller_ask_price_m": self.seller_ask_price_m,
            "ask_premium_pct": self.ask_premium_pct,
            "assumptions": [
                {"variable": a.variable,
                 "buyer_base": a.buyer_base,
                 "implied_seller": a.implied_seller,
                 "delta": a.delta,
                 "partner_interpretation": a.partner_interpretation}
                for a in self.assumptions
            ],
            "partner_note": self.partner_note,
        }


def _forward_ebitda(
    base: float, growth_pct: float, margin_bps: float,
    hold_years: float,
) -> float:
    """Project EBITDA at exit under buyer/seller assumptions."""
    grown = base * (1.0 + growth_pct) ** hold_years
    # Margin expansion is applied as an additive % uplift on EBITDA
    # margin. For simplicity, treat as a scalar uplift on EBITDA.
    margin_uplift_factor = 1.0 + (margin_bps / 10000.0)
    return grown * margin_uplift_factor


def reverse_engineer_seller_math(
    inputs: SellerMathInputs,
) -> SellerMathReport:
    # Buyer's implied entry price: what we'd pay to hit target MOIC.
    buyer_exit_ebitda = _forward_ebitda(
        inputs.buyer_base_ebitda_m,
        inputs.buyer_base_ebitda_growth_pct,
        inputs.buyer_base_margin_expansion_bps,
        inputs.hold_years,
    )
    buyer_exit_ev = buyer_exit_ebitda * inputs.buyer_base_exit_multiple
    buyer_implied_price = buyer_exit_ev / max(1.01, inputs.target_moic)

    premium = (inputs.seller_ask_price_m - buyer_implied_price) \
        / max(0.01, buyer_implied_price)

    # Scenario 1: implied exit multiple given buyer's growth + margin.
    # seller_ask = (base_exit_ebitda × implied_multiple) / MOIC
    # implied_multiple = ask × MOIC / base_exit_ebitda
    implied_exit_mult = (inputs.seller_ask_price_m * inputs.target_moic) \
        / max(0.01, buyer_exit_ebitda)

    # Scenario 2: implied growth given buyer's multiple + margin.
    # ask = base × (1+g)^hold × (1 + margin_bps/10000) × buyer_mult / MOIC
    # Solve for g.
    if buyer_exit_ebitda > 0 and inputs.hold_years > 0:
        target_ebitda = (inputs.seller_ask_price_m * inputs.target_moic) \
            / max(0.01, inputs.buyer_base_exit_multiple)
        margin_factor = 1.0 + (inputs.buyer_base_margin_expansion_bps / 10000.0)
        growth_factor_needed = (target_ebitda /
            max(0.01, inputs.buyer_base_ebitda_m * margin_factor))
        implied_growth = growth_factor_needed ** (1.0 / inputs.hold_years) - 1.0
    else:
        implied_growth = inputs.buyer_base_ebitda_growth_pct

    # Scenario 3: implied margin expansion given buyer's growth + multiple.
    # ask = base × (1+g)^hold × (1 + implied_margin_bps/10000) × buyer_mult / MOIC
    # Solve for margin_bps.
    if buyer_exit_ebitda > 0:
        target_ebitda = (inputs.seller_ask_price_m * inputs.target_moic) \
            / max(0.01, inputs.buyer_base_exit_multiple)
        grown_ebitda = inputs.buyer_base_ebitda_m * \
            (1.0 + inputs.buyer_base_ebitda_growth_pct) ** inputs.hold_years
        margin_factor_needed = target_ebitda / max(0.01, grown_ebitda)
        implied_margin_bps = (margin_factor_needed - 1.0) * 10000.0
    else:
        implied_margin_bps = inputs.buyer_base_margin_expansion_bps

    assumptions: List[ImpliedAssumption] = [
        ImpliedAssumption(
            variable="implied_exit_multiple",
            buyer_base=round(inputs.buyer_base_exit_multiple, 2),
            implied_seller=round(implied_exit_mult, 2),
            delta=round(implied_exit_mult - inputs.buyer_base_exit_multiple, 2),
            partner_interpretation=_interp_multiple(
                implied_exit_mult, inputs.buyer_base_exit_multiple,
            ),
        ),
        ImpliedAssumption(
            variable="implied_annual_ebitda_growth",
            buyer_base=round(inputs.buyer_base_ebitda_growth_pct, 4),
            implied_seller=round(implied_growth, 4),
            delta=round(implied_growth -
                inputs.buyer_base_ebitda_growth_pct, 4),
            partner_interpretation=_interp_growth(
                implied_growth, inputs.buyer_base_ebitda_growth_pct,
            ),
        ),
        ImpliedAssumption(
            variable="implied_margin_expansion_bps",
            buyer_base=round(inputs.buyer_base_margin_expansion_bps, 0),
            implied_seller=round(implied_margin_bps, 0),
            delta=round(implied_margin_bps -
                inputs.buyer_base_margin_expansion_bps, 0),
            partner_interpretation=_interp_margin(
                implied_margin_bps, inputs.buyer_base_margin_expansion_bps,
            ),
        ),
    ]

    if premium > 0.15:
        note = (f"Seller ask ${inputs.seller_ask_price_m:,.0f}M is "
                f"{premium*100:.0f}% above buyer's implied price "
                f"${buyer_implied_price:,.0f}M. To justify, seller "
                f"must assume ONE of: "
                f"{implied_exit_mult:.1f}x exit multiple, "
                f"{implied_growth*100:.1f}%/yr EBITDA growth, or "
                f"{implied_margin_bps:,.0f} bps margin expansion. "
                "Partner: pick the weakest assumption and force "
                "seller to defend it.")
    elif premium > 0.05:
        note = (f"Seller ask {premium*100:.0f}% above buyer base. "
                "Standard negotiation range; pick one variable to "
                "close.")
    elif premium >= 0:
        note = (f"Seller ask {premium*100:.0f}% above buyer base. "
                "Within noise; proceed.")
    else:
        note = (f"Seller ask is BELOW buyer's implied price by "
                f"{-premium*100:.0f}%. Either seller is motivated "
                "by non-price factors or we're missing downside the "
                "seller sees. Diligence the gap.")

    return SellerMathReport(
        buyer_implied_price_m=round(buyer_implied_price, 2),
        seller_ask_price_m=round(inputs.seller_ask_price_m, 2),
        ask_premium_pct=round(premium, 4),
        assumptions=assumptions,
        partner_note=note,
    )


def _interp_multiple(implied: float, base: float) -> str:
    if implied > 16:
        return ("Cycle-peak exit multiple. Seller betting on "
                "continued multiple expansion.")
    if implied > base + 1.5:
        return ("Well above buyer's base. Partner: price off "
                "cycle-average exit, not cycle-peak.")
    if implied > base:
        return "Modest implied lift on exit multiple."
    return "Seller comfortable with buyer's exit assumption."


def _interp_growth(implied: float, base: float) -> str:
    if implied > 0.10:
        return ("Double-digit implied EBITDA growth. Rare in "
                "healthcare services; seller betting on market "
                "we don't see.")
    if implied > base + 0.03:
        return ("Meaningfully above buyer's base growth. Push "
                "seller to guarantee first 2 years.")
    if implied > base:
        return "Modest growth delta."
    return "Seller comfortable with buyer's growth assumption."


def _interp_margin(implied_bps: float, base_bps: float) -> str:
    if implied_bps > 400:
        return ("400+ bps margin expansion is partner-reject: "
                "requires operator heroics we'd need to own.")
    if implied_bps > base_bps + 100:
        return ("Meaningful margin stretch. Ask seller to name "
                "the specific bps per initiative.")
    if implied_bps > base_bps:
        return "Modest margin delta."
    return "Seller comfortable with buyer's margin assumption."


def render_seller_math_markdown(r: SellerMathReport) -> str:
    lines = [
        "# Seller math reverse-engineer",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Buyer's implied price: ${r.buyer_implied_price_m:,.1f}M",
        f"- Seller's ask: ${r.seller_ask_price_m:,.1f}M",
        f"- Ask premium: {r.ask_premium_pct*100:.1f}%",
        "",
        "| Variable | Buyer base | Implied seller | Delta | "
        "Partner interpretation |",
        "|---|---|---|---|---|",
    ]
    for a in r.assumptions:
        lines.append(
            f"| {a.variable} | {a.buyer_base} | "
            f"{a.implied_seller} | {a.delta} | "
            f"{a.partner_interpretation} |"
        )
    return "\n".join(lines)
