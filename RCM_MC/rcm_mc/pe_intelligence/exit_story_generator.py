"""Exit story generator — the banker's pitch at exit, drafted at entry.

Partner reflex: "if I can't write the sell-side CIM headline at
entry, I don't know what I'm buying." The exit story is NOT the
same as the investment thesis. It's the two-sentence pitch a
sell-side banker will make to strategic buyers or the next sponsor.

This module composes the exit story from the packet's current
state + thesis pillars + target exit channel. Output is:

- **Exit headline** — the one-line banker-pitch opener.
- **Three bullets** — the "why buy this" moments.
- **Likely buyer types** — strategic, sponsor, IPO.
- **Exit risk** — the thing that could derail the story.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExitStoryInputs:
    deal_name: str = "Deal"
    subsector: str = ""
    entry_revenue_m: float = 0.0
    entry_ebitda_m: float = 0.0
    exit_revenue_m: float = 0.0
    exit_ebitda_m: float = 0.0
    hold_years: int = 5
    organic_growth_pct: float = 0.10
    acquisition_growth_pct: float = 0.0
    recurring_ebitda_pct: float = 1.0
    commercial_payer_pct: float = 0.50
    site_count_at_exit: int = 0
    site_count_at_entry: int = 0
    has_coe_designation: bool = False
    has_scale_advantage: bool = False
    is_category_leader: bool = False
    target_channel: str = "sponsor"        # "strategic"/"sponsor"/"ipo"


@dataclass
class ExitStory:
    deal_name: str
    headline: str
    bullets: List[str]
    likely_buyers: List[str]
    exit_risk: str
    banker_multiple_range: tuple            # (low, high)
    partner_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_name": self.deal_name,
            "headline": self.headline,
            "bullets": list(self.bullets),
            "likely_buyers": list(self.likely_buyers),
            "exit_risk": self.exit_risk,
            "banker_multiple_range": list(self.banker_multiple_range),
            "partner_note": self.partner_note,
        }


def _revenue_cagr(i: ExitStoryInputs) -> float:
    if i.entry_revenue_m <= 0 or i.hold_years <= 0:
        return 0.0
    return (i.exit_revenue_m / i.entry_revenue_m) ** (
        1.0 / i.hold_years) - 1.0


def _scale_multiplier(i: ExitStoryInputs) -> float:
    if i.entry_revenue_m <= 0:
        return 0.0
    return i.exit_revenue_m / i.entry_revenue_m


def _compose_bullets(i: ExitStoryInputs) -> List[str]:
    bullets: List[str] = []
    cagr = _revenue_cagr(i)
    if cagr >= 0.12:
        bullets.append(
            f"Organic revenue CAGR of {cagr*100:.1f}% over "
            f"{i.hold_years} years vs subsector growth of 3-5%.")
    elif cagr >= 0.08:
        bullets.append(
            f"Mid-teens topline growth with a "
            f"${i.exit_revenue_m:,.0f}M scaled platform.")
    else:
        bullets.append(
            f"${i.exit_revenue_m:,.0f}M scaled platform with proven "
            "operating discipline.")

    # Quality of earnings bullet.
    if i.recurring_ebitda_pct >= 0.95:
        bullets.append(
            f"~100% recurring EBITDA profile; exit multiple applies "
            "to the full book.")
    elif i.recurring_ebitda_pct >= 0.85:
        bullets.append(
            f"{i.recurring_ebitda_pct*100:.0f}% recurring EBITDA; "
            "high visibility into run-rate earnings.")
    # Payer / differentiation bullet.
    if i.commercial_payer_pct >= 0.60:
        bullets.append(
            f"{i.commercial_payer_pct*100:.0f}% commercial payer mix "
            "— premium rate capture and limited regulatory exposure.")
    elif i.has_coe_designation:
        bullets.append(
            "Center-of-Excellence designation in core service line — "
            "payer-leverage differentiation.")
    elif i.is_category_leader:
        bullets.append(
            f"Category leader in {i.subsector} by scale and "
            "outcomes.")

    # M&A / consolidation bullet.
    if i.acquisition_growth_pct >= 0.05:
        site_adds = max(0, i.site_count_at_exit - i.site_count_at_entry)
        bullets.append(
            f"Proven M&A engine: {site_adds} bolt-ons executed "
            "with documented integration playbook.")

    return bullets[:3]


def _banker_multiple_range(i: ExitStoryInputs) -> tuple:
    # Base range from subsector; nudge for scale + quality.
    base = {
        "hospital": (7.0, 10.0),
        "specialty_practice": (9.0, 13.0),
        "outpatient_asc": (11.0, 15.0),
        "home_health": (10.0, 13.0),
        "dme_supplier": (8.0, 11.0),
        "physician_staffing": (7.0, 10.0),
    }.get(i.subsector, (9.0, 12.0))
    lo, hi = base
    if i.has_coe_designation:
        lo += 0.5
        hi += 0.5
    if i.is_category_leader:
        lo += 1.0
        hi += 1.0
    if i.recurring_ebitda_pct >= 0.95:
        lo += 0.25
        hi += 0.25
    if i.commercial_payer_pct >= 0.60:
        lo += 0.5
        hi += 0.5
    return (round(lo, 2), round(hi, 2))


def _likely_buyers(i: ExitStoryInputs) -> List[str]:
    buyers: List[str] = []
    if i.target_channel == "strategic":
        buyers.append("strategic_healthcare_system")
        if i.subsector in ("specialty_practice", "outpatient_asc"):
            buyers.append("strategic_outpatient_platform")
    elif i.target_channel == "ipo":
        buyers.append("public_market")
    # Always add next-ring-up sponsor as an option.
    buyers.append("next_ring_up_sponsor")
    if i.acquisition_growth_pct >= 0.05:
        buyers.append("consolidator_roll_up")
    return buyers[:4]


def _exit_risk(i: ExitStoryInputs) -> str:
    if _revenue_cagr(i) < 0.05:
        return ("Low growth profile — buyers ask whether the business "
                "has further runway or is approaching peak.")
    if i.recurring_ebitda_pct < 0.80:
        return ("One-time / bridge adjustments ≥ 20% of EBITDA — "
                "exit buyer will haircut pro-forma aggressively.")
    if i.acquisition_growth_pct >= 0.10 and i.site_count_at_exit > 0:
        return ("Heavy M&A dependency — buyer must be comfortable "
                "with pro-forma ties to GAAP on acquired businesses.")
    if i.target_channel == "ipo":
        return ("IPO window sensitivity — a closed market at exit "
                "forces sponsor-to-sponsor or continuation.")
    return ("Cycle timing — buyer multiples at exit are a bet on "
            "credit + equity market conditions outside management's "
            "control.")


def generate_exit_story(inputs: ExitStoryInputs) -> ExitStory:
    cagr = _revenue_cagr(inputs)
    scale_mult = _scale_multiplier(inputs)
    bullets = _compose_bullets(inputs)
    buyers = _likely_buyers(inputs)
    risk = _exit_risk(inputs)
    mult_range = _banker_multiple_range(inputs)

    # Headline: lead with scale + growth + differentiator.
    lead = {
        "strategic": "Premium strategic asset",
        "sponsor": "Sponsor-ready platform",
        "ipo": "Public-ready company",
    }.get(inputs.target_channel, "Scaled platform")

    headline = (
        f"{lead} — {inputs.subsector or 'healthcare services'} "
        f"{inputs.exit_revenue_m:,.0f}M NPR / "
        f"${inputs.exit_ebitda_m:,.0f}M EBITDA after "
        f"{cagr*100:.0f}% annual growth over {inputs.hold_years} years; "
        f"{scale_mult:.1f}x scaled from entry."
    )

    if len(bullets) < 2 or cagr < 0.03:
        note = ("Exit story is weak — the banker will struggle to "
                "construct a premium pitch. Either the thesis needs "
                "to actually play out, or the exit channel needs "
                "to shift to a continuation vehicle.")
    elif inputs.is_category_leader or inputs.has_coe_designation:
        note = (f"Exit story is strong. Banker range "
                f"{mult_range[0]:.1f}-{mult_range[1]:.1f}x is "
                "defensible on the differentiation bullets.")
    else:
        note = (f"Exit story is workable. Banker range "
                f"{mult_range[0]:.1f}-{mult_range[1]:.1f}x. "
                "Main risk: {risk.split('.')[0]}.")

    return ExitStory(
        deal_name=inputs.deal_name,
        headline=headline,
        bullets=bullets,
        likely_buyers=buyers,
        exit_risk=risk,
        banker_multiple_range=mult_range,
        partner_note=note,
    )


def render_exit_story_markdown(s: ExitStory) -> str:
    lines = [
        f"# {s.deal_name} — Exit story (banker's pitch)",
        "",
        f"_{s.partner_note}_",
        "",
        "## Headline",
        "",
        s.headline,
        "",
        "## Why buy this",
        "",
    ]
    for b in s.bullets:
        lines.append(f"- {b}")
    lines.extend([
        "",
        f"## Likely buyers: {', '.join(s.likely_buyers)}",
        "",
        f"## Exit risk: {s.exit_risk}",
        "",
        f"## Banker multiple range: "
        f"{s.banker_multiple_range[0]:.1f}x – "
        f"{s.banker_multiple_range[1]:.1f}x",
    ])
    return "\n".join(lines)
