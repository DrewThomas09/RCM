"""Secondary sale valuation — GP-led secondary / LP interest pricing.

Secondary sales price an LP's fund interest (LP-led) or a specific
deal (GP-led continuation vehicle) mid-hold. Pricing conventions:

- LP-led: usually priced at discount to NAV. Typical
  healthcare-fund discount is 5-20% depending on fund age and
  remaining undeployed capital.
- GP-led (single-asset continuation): typically priced at mark
  or a modest premium (0-10%) with new LPs coming in to back a
  longer hold.

Discount drivers:

- Fund age (older fund = larger discount, 10+ year fund ~ 20%+).
- DPI to date (low DPI = higher discount, buyer pays for uncertainty).
- Concentration (single-asset fund > 40% of NAV = wider discount).
- Sector (healthcare typically less discounted than VC/growth).

This module computes indicative discount/premium, implied price,
and a partner note explaining the drivers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SecondarySaleInputs:
    nav_m: float
    transaction_type: str = "lp_led"      # "lp_led" or "gp_led"
    fund_age_years: int = 5
    dpi_to_date: float = 0.3              # DPI before secondary
    concentration_in_top_asset_pct: float = 0.25
    buyer_required_irr: float = 0.15      # hurdle used to back into price
    remaining_hold_years: int = 4
    remaining_projected_moic_on_unrealized: float = 1.7
    is_healthcare_fund: bool = True


@dataclass
class SecondarySaleAssessment:
    transaction_type: str
    indicative_discount_bps: int          # positive = discount, negative = premium
    implied_price_m: float
    discount_drivers: List[str] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_type": self.transaction_type,
            "indicative_discount_bps": self.indicative_discount_bps,
            "implied_price_m": self.implied_price_m,
            "discount_drivers": list(self.discount_drivers),
            "partner_note": self.partner_note,
        }


def _lp_led_discount_bps(inputs: SecondarySaleInputs) -> tuple:
    """Return (bps, drivers)."""
    # Base: 5% for healthcare, 8% for non-healthcare.
    base_bps = 500 if inputs.is_healthcare_fund else 800
    drivers: List[str] = [
        f"Base secondary discount {base_bps} bps "
        f"({'healthcare' if inputs.is_healthcare_fund else 'non-healthcare'} fund)."
    ]

    # Fund age.
    if inputs.fund_age_years >= 10:
        add = 700
        base_bps += add
        drivers.append(f"Fund age {inputs.fund_age_years}y → +{add} bps "
                       "(tail-end fund).")
    elif inputs.fund_age_years >= 7:
        add = 300
        base_bps += add
        drivers.append(f"Fund age {inputs.fund_age_years}y → +{add} bps "
                       "(mature fund).")
    elif inputs.fund_age_years <= 3:
        sub = 200
        base_bps -= sub
        drivers.append(f"Fund age {inputs.fund_age_years}y → -{sub} bps "
                       "(young fund, more optionality).")

    # Low DPI.
    if inputs.dpi_to_date < 0.10:
        add = 500
        base_bps += add
        drivers.append(f"DPI {inputs.dpi_to_date:.2f}x → +{add} bps "
                       "(low distributions so far).")
    elif inputs.dpi_to_date >= 0.80:
        sub = 200
        base_bps -= sub
        drivers.append(f"DPI {inputs.dpi_to_date:.2f}x → -{sub} bps "
                       "(strong distributions).")

    # Concentration.
    if inputs.concentration_in_top_asset_pct >= 0.40:
        add = 400
        base_bps += add
        drivers.append(
            f"Top-asset concentration "
            f"{inputs.concentration_in_top_asset_pct*100:.0f}% → "
            f"+{add} bps (concentrated book).")

    return base_bps, drivers


def _gp_led_discount_bps(inputs: SecondarySaleInputs) -> tuple:
    """GP-led continuation vehicles — typically at or above mark."""
    # Base: par for healthcare, 200 bps discount for non.
    base_bps = 0 if inputs.is_healthcare_fund else 200
    drivers: List[str] = [
        f"Base GP-led pricing "
        f"{'par to NAV' if inputs.is_healthcare_fund else '-200 bps'}."
    ]

    # High-confidence asset → potential premium.
    implied_irr = (inputs.remaining_projected_moic_on_unrealized **
                   (1.0 / max(1, inputs.remaining_hold_years)) - 1.0)
    if implied_irr > inputs.buyer_required_irr + 0.05:
        sub = 500
        base_bps -= sub
        drivers.append(
            f"Projected IRR {implied_irr*100:.1f}% > buyer hurdle "
            f"{inputs.buyer_required_irr*100:.1f}% → "
            f"premium of {sub} bps possible.")
    elif implied_irr < inputs.buyer_required_irr:
        add = 600
        base_bps += add
        drivers.append(
            f"Projected IRR {implied_irr*100:.1f}% < hurdle → "
            f"+{add} bps discount required.")

    return base_bps, drivers


def value_secondary_sale(inputs: SecondarySaleInputs) -> SecondarySaleAssessment:
    if inputs.transaction_type == "lp_led":
        bps, drivers = _lp_led_discount_bps(inputs)
    elif inputs.transaction_type == "gp_led":
        bps, drivers = _gp_led_discount_bps(inputs)
    else:
        raise ValueError(
            f"Unsupported transaction_type: {inputs.transaction_type!r}. "
            "Use 'lp_led' or 'gp_led'."
        )
    implied_price = inputs.nav_m * (1 - bps / 10000.0)

    if bps >= 2000:
        tone = "Deep discount — buyer's market or late-tail fund."
    elif bps >= 1000:
        tone = "Material discount — typical for mature funds."
    elif bps >= 500:
        tone = "Modest discount — standard market pricing."
    elif bps > 0:
        tone = "Near-NAV pricing."
    elif bps == 0:
        tone = "Par pricing."
    else:
        tone = f"Premium pricing ({abs(bps)} bps above NAV)."

    note = (f"{inputs.transaction_type} secondary: indicative "
            f"{bps:+d} bps vs NAV → ${implied_price:,.1f}M. {tone}")

    return SecondarySaleAssessment(
        transaction_type=inputs.transaction_type,
        indicative_discount_bps=bps,
        implied_price_m=round(implied_price, 2),
        discount_drivers=drivers,
        partner_note=note,
    )


def render_secondary_markdown(a: SecondarySaleAssessment) -> str:
    lines = [
        f"# Secondary sale valuation — {a.transaction_type}",
        "",
        f"_{a.partner_note}_",
        "",
        f"- Indicative vs NAV: {a.indicative_discount_bps:+d} bps",
        f"- Implied price: ${a.implied_price_m:,.1f}M",
        "",
        "## Discount / premium drivers",
        "",
    ]
    for d in a.discount_drivers:
        lines.append(f"- {d}")
    return "\n".join(lines)
