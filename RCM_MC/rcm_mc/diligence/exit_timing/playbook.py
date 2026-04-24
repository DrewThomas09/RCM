"""Buyer-type playbooks — expected behaviour of each exit channel.

Each playbook captures the partner-facing economics of selling to
that buyer type: multiple premium/discount vs the public comp
median, expected time-to-close, and close-certainty. Values are
calibrated against public PE-healthcare exit data (SEC 8-Ks on
take-privates + IPO S-1s + secondary announcements).

Partners read these as the "typical deal shape if we go this way."
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Tuple


class BuyerType(str, Enum):
    STRATEGIC = "STRATEGIC"              # Operating acquirer (HCA buys ARDT, UHG buys LHC)
    PE_SECONDARY = "PE_SECONDARY"        # Another PE fund
    IPO = "IPO"                          # Take-public
    SPONSOR_HOLD = "SPONSOR_HOLD"        # Extend hold (no exit)


@dataclass(frozen=True)
class BuyerPlaybook:
    """Partner-readable economics of selling to one buyer type."""
    buyer_type: BuyerType
    label: str
    # Multiple adjustment vs peer public median EV/EBITDA.
    # Strategic pays ~1-2 turn premium; PE secondary pays ~0.5 turn
    # discount; IPO trades at peer median +/- volatility.
    multiple_premium_turns_mean: float
    multiple_premium_turns_sd: float
    # Time from decision to close, months.
    time_to_close_months_mean: float
    time_to_close_months_sd: float
    # Probability the bid actually clears (seller accepts + deal
    # doesn't break).  Strategic has re-trade risk; PE has
    # financing risk; IPO has market-window risk.
    close_certainty: float
    # Narrative shown on the UI + IC packet.
    narrative: str
    # What moves the premium up or down — captured as named drivers.
    favorable_drivers: Tuple[str, ...]
    unfavorable_drivers: Tuple[str, ...]


BUYER_PLAYBOOKS: Dict[BuyerType, BuyerPlaybook] = {
    BuyerType.STRATEGIC: BuyerPlaybook(
        buyer_type=BuyerType.STRATEGIC,
        label="Strategic acquirer",
        multiple_premium_turns_mean=1.2,
        multiple_premium_turns_sd=0.8,
        time_to_close_months_mean=7.0,
        time_to_close_months_sd=2.0,
        close_certainty=0.75,
        narrative=(
            "Operating healthcare companies (HCA, UHS, Tenet, UHG, "
            "Humana-CenterWell, Optum) pay a 1-2 turn premium over "
            "public-peer EV/EBITDA when the acquisition fills a "
            "geographic or capability gap. Synergy math + regulatory "
            "cover support the premium. Biggest risk: HSR review + "
            "re-trade after diligence."
        ),
        favorable_drivers=(
            "Geographic fit with buyer's existing footprint",
            "Capability gap (e.g., ASC for a hospital system)",
            "Strong in-network commercial contracts",
            "Low OON exposure",
            "Clean regulatory record (no DOJ/OIG overhang)",
        ),
        unfavorable_drivers=(
            "Market overlap that triggers HSR concerns",
            "Declining organic growth",
            "Material open DOJ/OIG matters",
            "Pending labor action or union organizing",
        ),
    ),
    BuyerType.PE_SECONDARY: BuyerPlaybook(
        buyer_type=BuyerType.PE_SECONDARY,
        label="PE secondary",
        multiple_premium_turns_mean=-0.5,
        multiple_premium_turns_sd=0.7,
        time_to_close_months_mean=5.0,
        time_to_close_months_sd=1.5,
        close_certainty=0.85,
        narrative=(
            "Fund-to-fund sales clear at 0-0.5 turns below peer public "
            "median — the buying fund needs its own MOIC path, so "
            "pays at or below strip valuation. Faster close than "
            "strategic (no HSR most cases) but less upside."
        ),
        favorable_drivers=(
            "Proven platform for tuck-in M&A",
            "Clean data room + benchmarking-ready",
            "Low customer/payer concentration",
            "Management team willing to roll equity",
        ),
        unfavorable_drivers=(
            "Credit market tightening (limits buyer leverage)",
            "Sector out of favor",
            "Unresolved diligence items from prior hold",
            "Fund vintage timing mismatch",
        ),
    ),
    BuyerType.IPO: BuyerPlaybook(
        buyer_type=BuyerType.IPO,
        label="IPO / public-market exit",
        multiple_premium_turns_mean=0.0,
        multiple_premium_turns_sd=1.5,
        time_to_close_months_mean=9.0,
        time_to_close_months_sd=3.0,
        close_certainty=0.55,
        narrative=(
            "IPO clears at peer public median with material range — "
            "±1.5 turns on any given window. Requires $150M+ equity "
            "raise + $1B+ implied EV + 3 years of clean audited "
            "financials. Window-dependent: 55% close certainty "
            "reflects windows that shut mid-process."
        ),
        favorable_drivers=(
            "Scale (EBITDA > $100M)",
            "Three clean years of audited financials",
            "Investor story with defensible growth driver",
            "Favorable sector-rotation window",
        ),
        unfavorable_drivers=(
            "Customer concentration > 20% top-1",
            "Material regulatory overhang",
            "Management team shorter than 3 years",
            "Sector out of favor (analyst coverage negative)",
        ),
    ),
    BuyerType.SPONSOR_HOLD: BuyerPlaybook(
        buyer_type=BuyerType.SPONSOR_HOLD,
        label="Extend hold (sponsor retains)",
        multiple_premium_turns_mean=0.0,
        multiple_premium_turns_sd=0.3,
        time_to_close_months_mean=0.0,
        time_to_close_months_sd=0.0,
        close_certainty=1.0,
        narrative=(
            "No exit — sponsor extends hold another 1-2 years. IRR "
            "decay kicks in (~2-4 pp per year). Use when no buyer "
            "clears the reserve or when a material sector-rotation "
            "window is expected."
        ),
        favorable_drivers=(
            "Sector expected to rotate in favor in 12-18 months",
            "Near-term regulatory tailwind (CMS rate increase, etc.)",
            "Operational initiative with >12 months runway",
        ),
        unfavorable_drivers=(
            "Fund approaching end-of-life",
            "Sector expected to stay out of favor",
            "Management fatigue / turnover risk",
        ),
    ),
}
