"""Earn-out design advisor — when and how to bridge the gap.

Partners use earn-outs when seller and buyer disagree on a
specific value driver. They're not for every gap — only for
gaps where a CLEAR MEASURABLE outcome resolves the disagreement
in 12-36 months.

Good earn-out drivers:

- Signed commercial payer contracts by year N.
- EBITDA milestones tied to specific run-rate numbers.
- Bolt-on close count (for roll-up platform deals).
- Regulatory milestones (e.g., specific state licensure).

Bad earn-out drivers:

- Generic "EBITDA over $X" (too easy to game).
- Quality metrics (subjective, dispute-prone).
- Management subjective targets.

This module takes the price gap + the disputed driver + deal
economics and returns a proposed earn-out structure, with
partner-voice commentary on whether to propose at all.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


GOOD_DRIVERS = {
    "signed_commercial_contract",
    "ebitda_run_rate_milestone",
    "bolton_close_count",
    "regulatory_licensure",
    "site_expansion_count",
}

BAD_DRIVERS = {
    "generic_ebitda_threshold",
    "quality_metric",
    "management_subjective",
    "market_share_claim",
}


@dataclass
class EarnoutInputs:
    price_gap_m: float = 0.0                  # asker - our bid
    total_transaction_value_m: float = 0.0
    disputed_driver: str = ""                 # one of the categories
    driver_description: str = ""
    driver_resolution_months: int = 18
    seller_conviction_high: bool = False      # seller stands by it
    buyer_skepticism_high: bool = False       # we think it's a stretch
    is_physician_owned: bool = False          # owner-operator dynamic


@dataclass
class EarnoutStructure:
    should_propose: bool
    earnout_size_m: float
    earnout_pct_of_gap: float
    trigger: str
    vesting_window_months: int
    pro_rata_achievability: bool
    partner_rationale: str


@dataclass
class EarnoutReport:
    structure: EarnoutStructure
    driver_quality: str                       # "good" / "bad" / "unknown"
    partner_note: str

    def to_dict(self) -> Dict[str, Any]:
        s = self.structure
        return {
            "structure": {
                "should_propose": s.should_propose,
                "earnout_size_m": s.earnout_size_m,
                "earnout_pct_of_gap": s.earnout_pct_of_gap,
                "trigger": s.trigger,
                "vesting_window_months": s.vesting_window_months,
                "pro_rata_achievability": s.pro_rata_achievability,
                "partner_rationale": s.partner_rationale,
            },
            "driver_quality": self.driver_quality,
            "partner_note": self.partner_note,
        }


def advise_earnout(inputs: EarnoutInputs) -> EarnoutReport:
    # Classify driver quality.
    if inputs.disputed_driver in GOOD_DRIVERS:
        quality = "good"
    elif inputs.disputed_driver in BAD_DRIVERS:
        quality = "bad"
    else:
        quality = "unknown"

    # Default recommendation.
    propose = True
    earnout_size = inputs.price_gap_m * 0.70   # cover 70% of gap
    earnout_pct = 0.70
    pro_rata = True
    window = inputs.driver_resolution_months

    trigger = (
        f"{inputs.driver_description or inputs.disputed_driver} "
        f"achieved by month {window}"
    )

    if quality == "bad":
        propose = False
        earnout_size = 0.0
        earnout_pct = 0.0
        rationale = (
            f"Disputed driver '{inputs.disputed_driver}' is not "
            "earn-out-able — too subjective or gameable. Instead, "
            "reduce headline price by 80% of the gap and share upside "
            "through MIP.")
    elif quality == "unknown":
        propose = True
        earnout_size = inputs.price_gap_m * 0.50
        earnout_pct = 0.50
        rationale = (
            "Driver is unspecified or non-standard. Size earn-out at "
            "50% of the gap to bound partner exposure; negotiate "
            "specific measurable language.")
    else:
        # Good driver — shape earn-out by buyer skepticism.
        if inputs.buyer_skepticism_high and not inputs.seller_conviction_high:
            earnout_size = inputs.price_gap_m * 0.90
            earnout_pct = 0.90
            rationale = (
                "Good driver with seller flinching — size earn-out "
                "deep (90% of gap). If they won't stand behind it, "
                "they don't really believe it.")
        elif inputs.seller_conviction_high and inputs.buyer_skepticism_high:
            earnout_size = inputs.price_gap_m * 0.60
            earnout_pct = 0.60
            rationale = (
                "Seller is confident and we're skeptical — classic "
                "earn-out zone. 60% of gap deferred to outcome.")
        else:
            earnout_size = inputs.price_gap_m * 0.70
            earnout_pct = 0.70
            rationale = (
                "Good driver, modest disagreement. Standard earn-out "
                "at 70% of gap.")

    if inputs.is_physician_owned and propose:
        rationale += (" Physician-owner dynamic: retention bonus "
                      "component is essential to align post-close.")

    # Pro-rata achievability — if the outcome is binary (licensure),
    # earn-out is cliff.
    if inputs.disputed_driver in ("regulatory_licensure",
                                    "signed_commercial_contract"):
        pro_rata = False
        rationale += (" Binary outcome — structure as cliff-vest, not "
                      "pro-rata.")

    # Partner note.
    if not propose:
        note = (f"Do NOT propose earn-out on this driver. "
                "Driver is not measurable enough. Cut headline price "
                "instead.")
    elif inputs.price_gap_m / max(1.0, inputs.total_transaction_value_m) >= 0.20:
        note = (f"Price gap is {inputs.price_gap_m:,.1f}M vs "
                f"${inputs.total_transaction_value_m:,.0f}M TV — "
                "meaningful. Earn-out is the bridge. Structure "
                "carefully.")
    else:
        note = (f"Earn-out bridges a modest "
                f"${inputs.price_gap_m:,.1f}M gap. Go straight to "
                "structure discussion.")

    structure = EarnoutStructure(
        should_propose=propose,
        earnout_size_m=round(earnout_size, 2),
        earnout_pct_of_gap=round(earnout_pct, 2),
        trigger=trigger,
        vesting_window_months=window,
        pro_rata_achievability=pro_rata,
        partner_rationale=rationale,
    )

    return EarnoutReport(
        structure=structure,
        driver_quality=quality,
        partner_note=note,
    )


def render_earnout_markdown(r: EarnoutReport) -> str:
    s = r.structure
    lines = [
        "# Earn-out design advisor",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Driver quality: **{r.driver_quality}**",
        f"- Should propose: **{'yes' if s.should_propose else 'no'}**",
        f"- Earn-out size: ${s.earnout_size_m:,.1f}M",
        f"- % of price gap covered: {s.earnout_pct_of_gap*100:.0f}%",
        f"- Trigger: {s.trigger}",
        f"- Vesting window: {s.vesting_window_months} months",
        f"- Pro-rata achievable: "
        f"{'yes' if s.pro_rata_achievability else 'no (cliff)'}",
        "",
        f"**Partner rationale:** {s.partner_rationale}",
    ]
    return "\n".join(lines)
