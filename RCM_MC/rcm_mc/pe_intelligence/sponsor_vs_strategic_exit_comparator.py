"""Sponsor-vs-strategic exit comparator — risk-adjusted per-day IRR.

Partner statement: "Strategic says 12x but the
process takes 12 months with FTC / AG review that
could block. Sponsor says 10x, closes in 4 months,
certainty is real. The question isn't headline
multiple — it's risk-adjusted net-per-day-of-hold.
Sometimes sponsor wins even at a turn lower because
the time value + certainty more than pays for it."

Distinct from:
- `buyer_type_fit_analyzer` — 8 buyer profiles.
- `exit_alternative_comparator` — 5 paths broadly.
- `exit_buyer_view_mirror` — first-person buyer IC.

This module compares **two specific exit paths**
head-to-head with:
- process duration (months to close)
- regulatory close-risk (probability-weighted)
- deal-term certainty (earn-out / reps / escrow)
- net-per-day-of-hold returns

### Output

- risk-adjusted exit EV for each path
- time-value-adjusted EV
- winner by expected-value
- partner verdict
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExitPathInputs:
    name: str = "Sponsor"
    ebitda_m: float = 50.0
    headline_multiple: float = 10.0
    months_to_close: float = 4.0
    probability_of_close_pct: float = 0.90
    seller_escrow_pct: float = 0.05
    """Escrow held back (reducing net-to-seller)."""
    earn_out_portion_of_price_pct: float = 0.0
    """Earn-out portion; discount at 50%."""
    annual_discount_rate_pct: float = 0.10


@dataclass
class SponsorVsStrategicInputs:
    sponsor: ExitPathInputs = field(
        default_factory=lambda: ExitPathInputs(
            name="Sponsor",
            headline_multiple=10.0,
            months_to_close=4.0,
            probability_of_close_pct=0.90,
            seller_escrow_pct=0.03,
            earn_out_portion_of_price_pct=0.0,
        )
    )
    strategic: ExitPathInputs = field(
        default_factory=lambda: ExitPathInputs(
            name="Strategic",
            headline_multiple=12.0,
            months_to_close=12.0,
            probability_of_close_pct=0.65,
            seller_escrow_pct=0.08,
            earn_out_portion_of_price_pct=0.10,
        )
    )


@dataclass
class PathResult:
    name: str
    headline_ev_m: float
    certain_portion_ev_m: float
    earn_out_discounted_ev_m: float
    escrow_haircut_ev_m: float
    expected_net_ev_m: float
    time_discounted_ev_m: float
    months_to_close: float


@dataclass
class SponsorVsStrategicReport:
    paths: List[PathResult] = field(default_factory=list)
    winner: str = ""
    delta_m: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "paths": [
                {"name": p.name,
                 "headline_ev_m": p.headline_ev_m,
                 "certain_portion_ev_m":
                     p.certain_portion_ev_m,
                 "earn_out_discounted_ev_m":
                     p.earn_out_discounted_ev_m,
                 "escrow_haircut_ev_m":
                     p.escrow_haircut_ev_m,
                 "expected_net_ev_m":
                     p.expected_net_ev_m,
                 "time_discounted_ev_m":
                     p.time_discounted_ev_m,
                 "months_to_close": p.months_to_close}
                for p in self.paths
            ],
            "winner": self.winner,
            "delta_m": self.delta_m,
            "partner_note": self.partner_note,
        }


def _evaluate_path(p: ExitPathInputs) -> PathResult:
    headline_ev = p.ebitda_m * p.headline_multiple
    certain_portion = (
        1.0 - p.seller_escrow_pct -
        p.earn_out_portion_of_price_pct
    )
    certain_ev = headline_ev * certain_portion
    earn_out_ev = (
        headline_ev * p.earn_out_portion_of_price_pct *
        0.50  # 50% risk-discount on earn-out
    )
    escrow_ev = (
        headline_ev * p.seller_escrow_pct * 0.80
    )  # 80% of escrow assumed recovered
    expected_net = (
        (certain_ev + earn_out_ev + escrow_ev) *
        p.probability_of_close_pct
    )
    # Time-discount to now
    years = p.months_to_close / 12.0
    discount = (1 + p.annual_discount_rate_pct) ** years
    time_disc = expected_net / max(0.01, discount)
    return PathResult(
        name=p.name,
        headline_ev_m=round(headline_ev, 2),
        certain_portion_ev_m=round(certain_ev, 2),
        earn_out_discounted_ev_m=round(earn_out_ev, 2),
        escrow_haircut_ev_m=round(escrow_ev, 2),
        expected_net_ev_m=round(expected_net, 2),
        time_discounted_ev_m=round(time_disc, 2),
        months_to_close=p.months_to_close,
    )


def compare_sponsor_vs_strategic(
    inputs: SponsorVsStrategicInputs,
) -> SponsorVsStrategicReport:
    sponsor_result = _evaluate_path(inputs.sponsor)
    strategic_result = _evaluate_path(inputs.strategic)
    delta = (
        strategic_result.time_discounted_ev_m -
        sponsor_result.time_discounted_ev_m
    )
    winner = (
        strategic_result.name if delta > 0
        else sponsor_result.name
    )

    abs_delta_pct = abs(delta) / max(
        0.01, sponsor_result.time_discounted_ev_m)

    if abs_delta_pct < 0.02:
        note = (
            f"Paths effectively tied "
            f"(${abs(delta):.1f}M delta). Pick "
            "certainty: sponsor closes faster, less "
            "regulatory exposure."
        )
    elif winner == inputs.sponsor.name:
        note = (
            f"Sponsor wins by ${abs(delta):.1f}M time-"
            "discounted. Certainty + faster close "
            "outweighs the strategic multiple premium."
        )
    else:
        note = (
            f"Strategic wins by ${abs(delta):.1f}M "
            "time-discounted even with regulatory risk "
            "and slower close. The premium is real — "
            "run the strategic process and keep "
            "sponsor as backup."
        )

    return SponsorVsStrategicReport(
        paths=[sponsor_result, strategic_result],
        winner=winner,
        delta_m=round(delta, 2),
        partner_note=note,
    )


def render_sponsor_vs_strategic_markdown(
    r: SponsorVsStrategicReport,
) -> str:
    lines = [
        "# Sponsor-vs-strategic exit",
        "",
        f"_Winner: **{r.winner}** "
        f"(Δ ${r.delta_m:+.1f}M)_",
        "",
        f"_{r.partner_note}_",
        "",
        "| Path | Headline EV | Certain $ | Earn-out disc | "
        "Escrow adj | Expected | Time-disc | Months |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for p in r.paths:
        lines.append(
            f"| {p.name} | ${p.headline_ev_m:.0f} | "
            f"${p.certain_portion_ev_m:.0f} | "
            f"${p.earn_out_discounted_ev_m:.0f} | "
            f"${p.escrow_haircut_ev_m:.0f} | "
            f"${p.expected_net_ev_m:.0f} | "
            f"${p.time_discounted_ev_m:.0f} | "
            f"{p.months_to_close:.0f} |"
        )
    return "\n".join(lines)
