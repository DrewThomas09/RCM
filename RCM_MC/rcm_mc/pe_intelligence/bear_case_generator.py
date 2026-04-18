"""Bear case generator — the bear case a partner can actually defend.

Partner reflex: "if I can't write the bear case, I haven't done the
work." Generic "recession hits everyone" bear cases are useless.
A partner writes the bear case that is *specific to this deal*:
the subsector shock, the contract, the management gap, the
historical pattern.

This module takes a packet-like signal set and generates:

- **The bear case story** — a partner-voice paragraph specific to
  the deal, not generic.
- **Bear-case EBITDA** — base × (1 - cumulative shock factor).
- **Bear-case MOIC / IRR** — what the deal looks like under bear.
- **Named drivers** — which specific bear-case elements apply.
- **"Do we still win at X% probability?"** — expected MOIC across
  base-probability + bear-probability.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BearCaseInputs:
    deal_name: str = "Deal"
    subsector: str = ""
    base_ebitda_m: float = 0.0
    entry_multiple: float = 11.0
    base_exit_multiple: float = 11.0
    base_moic: float = 2.5
    hold_years: int = 5
    leverage_multiple: float = 5.5
    # Signals that shape the bear case:
    medicare_ffs_pct: float = 0.0
    oon_revenue_share: float = 0.0
    top_payer_share: float = 0.0
    denial_rate: float = 0.05
    historical_failure_matches: List[str] = field(default_factory=list)
    management_score_0_100: int = 70
    sale_leaseback_in_thesis: bool = False
    has_covenant_lite: bool = False
    labor_cost_pct_revenue: float = 0.40
    claimed_rate_growth_pct: float = 0.03
    pro_forma_addbacks_pct: float = 0.0
    base_probability: float = 0.60       # P(base), bear P is 1 - base


@dataclass
class BearDriver:
    name: str
    description: str
    ebitda_haircut_pct: float            # cumulative shock applied


@dataclass
class BearCaseReport:
    deal_name: str
    bear_ebitda_m: float
    bear_exit_multiple: float
    bear_moic: float
    bear_irr: Optional[float]
    cumulative_ebitda_shock_pct: float
    probability_weighted_moic: float
    drivers: List[BearDriver] = field(default_factory=list)
    bear_story: str = ""
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_name": self.deal_name,
            "bear_ebitda_m": self.bear_ebitda_m,
            "bear_exit_multiple": self.bear_exit_multiple,
            "bear_moic": self.bear_moic,
            "bear_irr": self.bear_irr,
            "cumulative_ebitda_shock_pct": self.cumulative_ebitda_shock_pct,
            "probability_weighted_moic": self.probability_weighted_moic,
            "drivers": [
                {"name": d.name, "description": d.description,
                 "ebitda_haircut_pct": d.ebitda_haircut_pct}
                for d in self.drivers
            ],
            "bear_story": self.bear_story,
            "partner_note": self.partner_note,
        }


def _driver_medicare_heavy(
    i: BearCaseInputs,
) -> Optional[BearDriver]:
    if i.medicare_ffs_pct >= 0.30:
        haircut = 0.03 + (i.medicare_ffs_pct - 0.30) * 0.10
        return BearDriver(
            "medicare_rate_shock",
            (f"Medicare FFS {i.medicare_ffs_pct*100:.0f}% of book. "
             "OBBBA / sequestration-style cut of 3-5% realizes "
             "mid-hold; no commercial leg to cross-subsidize."),
            haircut,
        )
    return None


def _driver_oon(i: BearCaseInputs) -> Optional[BearDriver]:
    if i.oon_revenue_share >= 0.20:
        haircut = i.oon_revenue_share * 0.40
        return BearDriver(
            "nsa_oon_compression",
            (f"OON {i.oon_revenue_share*100:.0f}% of revenue. "
             "No Surprises Act framework drives 40% realized "
             "compression on OON billing."),
            haircut,
        )
    return None


def _driver_top_payer(i: BearCaseInputs) -> Optional[BearDriver]:
    if i.top_payer_share >= 0.40:
        haircut = i.top_payer_share * 0.25
        return BearDriver(
            "top_payer_walk",
            (f"Top payer is {i.top_payer_share*100:.0f}% of revenue. "
             "Bear case assumes contract terms deteriorate 25% of "
             "that book at next renewal."),
            haircut,
        )
    return None


def _driver_denials_compound(i: BearCaseInputs) -> Optional[BearDriver]:
    if i.denial_rate >= 0.10:
        haircut = (i.denial_rate - 0.08) * 1.5
        return BearDriver(
            "denial_compounding",
            (f"Denial rate {i.denial_rate*100:.1f}% trends up 150 bps "
             "per year under bear; write-off losses compound over hold."),
            max(0.0, haircut),
        )
    return None


def _driver_historical_pattern(
    i: BearCaseInputs,
) -> Optional[BearDriver]:
    if i.historical_failure_matches:
        pattern = i.historical_failure_matches[0]
        haircut = 0.20
        return BearDriver(
            f"historical:{pattern}",
            (f"Deal pattern-matches {pattern}. If the same outcome "
             "materializes at 50% severity, EBITDA drops 20%."),
            haircut,
        )
    return None


def _driver_sale_leaseback(
    i: BearCaseInputs,
) -> Optional[BearDriver]:
    if i.sale_leaseback_in_thesis:
        return BearDriver(
            "steward_sale_leaseback",
            ("Sale-leaseback rent is a senior claim. A 10% EBITDA "
             "miss drives rent-to-EBITDA past 0.60; Steward showed "
             "what happens next."),
            0.15,
        )
    return None


def _driver_weak_management(
    i: BearCaseInputs,
) -> Optional[BearDriver]:
    if i.management_score_0_100 < 60:
        return BearDriver(
            "weak_management",
            (f"Management score {i.management_score_0_100}/100. Bear "
             "case: key departures by year 2 trigger 6-12 months of "
             "operating disruption."),
            0.08,
        )
    return None


def _driver_aggressive_rate(
    i: BearCaseInputs,
) -> Optional[BearDriver]:
    if i.claimed_rate_growth_pct > 0.05:
        return BearDriver(
            "rate_growth_miss",
            (f"Claimed {i.claimed_rate_growth_pct*100:.1f}% rate "
             "growth; bear assumes 1.5% rate growth (market average). "
             "Compounded miss over 5 years is material."),
            0.05,
        )
    return None


def _driver_pro_forma(i: BearCaseInputs) -> Optional[BearDriver]:
    if i.pro_forma_addbacks_pct > 0.15:
        return BearDriver(
            "pro_forma_fiction",
            (f"Pro-forma add-backs {i.pro_forma_addbacks_pct*100:.0f}%. "
             "Bear assumes 50% of the pro-forma never materializes; "
             "exit buyer underwrites GAAP."),
            i.pro_forma_addbacks_pct * 0.5,
        )
    return None


def _driver_labor_shock(
    i: BearCaseInputs,
) -> Optional[BearDriver]:
    if i.labor_cost_pct_revenue >= 0.50:
        return BearDriver(
            "labor_inflation",
            (f"Labor is {i.labor_cost_pct_revenue*100:.0f}% of revenue. "
             "Bear assumes 4-5% wage inflation + travel-nurse premium "
             "for 18 months."),
            0.06,
        )
    return None


DRIVERS = (
    _driver_medicare_heavy,
    _driver_oon,
    _driver_top_payer,
    _driver_denials_compound,
    _driver_historical_pattern,
    _driver_sale_leaseback,
    _driver_weak_management,
    _driver_aggressive_rate,
    _driver_pro_forma,
    _driver_labor_shock,
)


def _combine_haircuts(drivers: List[BearDriver]) -> float:
    """Combine multiple independent shocks multiplicatively."""
    retain = 1.0
    for d in drivers:
        retain *= (1 - max(0.0, min(0.4, d.ebitda_haircut_pct)))
    return 1.0 - retain


def _irr(moic: float, years: int) -> Optional[float]:
    if moic <= 0 or years <= 0:
        return None
    return moic ** (1.0 / years) - 1.0


def _compose_story(i: BearCaseInputs,
                    drivers: List[BearDriver],
                    bear_moic: float) -> str:
    if not drivers:
        return (f"Bear case for {i.deal_name}: "
                "no deal-specific shocks surface from the packet; "
                "the generic recession bear case (−10% EBITDA, "
                "−1x multiple) is all that applies.")

    lead = drivers[0]
    parts = [
        f"Bear case for {i.deal_name}: {lead.description}"
    ]
    if len(drivers) >= 2:
        parts.append(
            f"Compounded by {drivers[1].name}: {drivers[1].description}"
        )
    if len(drivers) >= 3:
        parts.append(
            f"Plus {drivers[2].name} in the background."
        )
    parts.append(
        f"Net effect: exit EBITDA compresses to bear "
        f"${(1 - _combine_haircuts(drivers))*i.base_ebitda_m:,.1f}M; "
        f"combined with multiple compression to "
        f"{max(i.base_exit_multiple - 1.5, 5.0):.1f}x, MOIC lands at "
        f"{bear_moic:.2f}x. "
    )
    if bear_moic < 1.0:
        parts.append("Bear case is a loss, not a soft landing.")
    elif bear_moic < 1.5:
        parts.append("Bear case clears principal but not hurdle.")
    else:
        parts.append("Bear case is survivable but dilutive to IRR.")
    return " ".join(parts)


def generate_bear_case(inputs: BearCaseInputs) -> BearCaseReport:
    drivers = [d for d in (fn(inputs) for fn in DRIVERS) if d is not None]
    drivers.sort(key=lambda d: d.ebitda_haircut_pct, reverse=True)

    shock = _combine_haircuts(drivers)
    bear_ebitda = inputs.base_ebitda_m * (1 - shock)
    bear_exit_mult = max(inputs.base_exit_multiple - 1.5, 5.0)

    # Bear MOIC: scale from base MOIC by EBITDA and multiple haircut.
    ratio = ((bear_ebitda / max(0.01, inputs.base_ebitda_m))
              * (bear_exit_mult / max(0.01, inputs.base_exit_multiple)))
    bear_moic = max(0.0, inputs.base_moic * ratio)
    bear_irr = _irr(bear_moic, inputs.hold_years)

    p_base = max(0.0, min(1.0, inputs.base_probability))
    p_bear = 1.0 - p_base
    pw_moic = p_base * inputs.base_moic + p_bear * bear_moic

    if bear_moic < 1.0:
        note = (f"Bear case loses money. Probability-weighted MOIC "
                f"{pw_moic:.2f}x at {p_base*100:.0f}% base probability. "
                "If you're not confident the base case clears 70%+ "
                "probability, pass.")
    elif bear_moic < 1.5:
        note = (f"Bear clears principal ({bear_moic:.2f}x) but not "
                "hurdle. Probability-weighted "
                f"{pw_moic:.2f}x. Deal is a bet on base-case "
                "realization.")
    else:
        note = (f"Bear case is survivable ({bear_moic:.2f}x). "
                f"Probability-weighted MOIC {pw_moic:.2f}x. "
                "Deal has real downside protection.")

    story = _compose_story(inputs, drivers, bear_moic)

    return BearCaseReport(
        deal_name=inputs.deal_name,
        bear_ebitda_m=round(bear_ebitda, 2),
        bear_exit_multiple=round(bear_exit_mult, 2),
        bear_moic=round(bear_moic, 4),
        bear_irr=round(bear_irr, 6) if bear_irr is not None else None,
        cumulative_ebitda_shock_pct=round(shock, 4),
        probability_weighted_moic=round(pw_moic, 4),
        drivers=drivers,
        bear_story=story,
        partner_note=note,
    )


def render_bear_case_markdown(r: BearCaseReport) -> str:
    lines = [
        f"# {r.deal_name} — Bear case",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Cumulative EBITDA shock: "
        f"{r.cumulative_ebitda_shock_pct*100:.0f}%",
        f"- Bear EBITDA: ${r.bear_ebitda_m:,.1f}M",
        f"- Bear exit multiple: {r.bear_exit_multiple:.1f}x",
        f"- Bear MOIC: {r.bear_moic:.2f}x",
    ]
    if r.bear_irr is not None:
        lines.append(f"- Bear IRR: {r.bear_irr*100:.1f}%")
    lines.extend([
        f"- Probability-weighted MOIC: "
        f"{r.probability_weighted_moic:.2f}x",
        "",
        "## Drivers",
        "",
    ])
    for d in r.drivers:
        lines.append(f"- **{d.name}** "
                     f"({d.ebitda_haircut_pct*100:.0f}% haircut): "
                     f"{d.description}")
    lines.extend(["", "## Story", "", r.bear_story])
    return "\n".join(lines)
