"""ExitTimingReport orchestrator — composes the curve, buyer fit,
and a recommendation.

Recommendation algorithm:
    1. Build the MOIC/IRR curve for candidate years 2–7
    2. Score each buyer type against the target profile
    3. For each (year, buyer_type) combo, compute
       probability-weighted proceeds =
           equity_proceeds_at_year × (close_certainty)
       Apply multiple adjustment: a strategic buyer expects a
       ~1.2-turn premium over peer public median; PE secondary
       ~0.5 turn below; IPO at median.
    4. Rank combos by probability-weighted IRR
    5. Tie-break: shorter time-to-close; higher fit_score

The partner-facing recommendation names the year, buyer type, and
the "what this tradeoff costs" sentence: "Year 4 to strategic
clears 28% IRR vs year 5 at 22% — the extra year costs 6 pp, fund
math should prefer year 4."
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from .buyer_fit import BuyerFitScore, score_all_buyers
from .curves import (
    DEFAULT_CANDIDATE_HOLDS, ExitCurvePoint, build_exit_curve,
    peak_irr_year,
)
from .playbook import BUYER_PLAYBOOKS, BuyerType


@dataclass
class ExitRecommendation:
    """Partner-facing exit-path recommendation."""
    exit_year: int
    buyer_type: BuyerType
    buyer_label: str
    # Expected outcome
    expected_moic: float
    expected_irr: float
    expected_proceeds_usd: float
    probability_weighted_proceeds_usd: float
    # Narrative
    summary: str
    rationale: str                    # "Year 4 to strategic vs year 5 costs 6 pp IRR"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exit_year": self.exit_year,
            "buyer_type": self.buyer_type.value,
            "buyer_label": self.buyer_label,
            "expected_moic": self.expected_moic,
            "expected_irr": self.expected_irr,
            "expected_proceeds_usd": self.expected_proceeds_usd,
            "probability_weighted_proceeds_usd":
                self.probability_weighted_proceeds_usd,
            "summary": self.summary,
            "rationale": self.rationale,
        }


@dataclass
class ExitTimingReport:
    """Top-level output surface."""
    curve: List[ExitCurvePoint] = field(default_factory=list)
    buyer_fit: List[BuyerFitScore] = field(default_factory=list)
    recommendation: Optional[ExitRecommendation] = None
    # Additional context
    peer_median_multiple: Optional[float] = None
    sector_sentiment: Optional[str] = None

    @property
    def peak_irr_point(self) -> Optional[ExitCurvePoint]:
        return peak_irr_year(self.curve)

    @property
    def sorted_fit(self) -> List[BuyerFitScore]:
        return sorted(
            self.buyer_fit,
            key=lambda b: b.fit_score, reverse=True,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "curve": [p.to_dict() for p in self.curve],
            "buyer_fit": [b.to_dict() for b in self.buyer_fit],
            "recommendation": (
                self.recommendation.to_dict()
                if self.recommendation else None
            ),
            "peer_median_multiple": self.peer_median_multiple,
            "sector_sentiment": self.sector_sentiment,
        }


# ────────────────────────────────────────────────────────────────────
# Recommendation math
# ────────────────────────────────────────────────────────────────────

def _recommend(
    curve: Sequence[ExitCurvePoint],
    buyers: Sequence[BuyerFitScore],
    peer_median_multiple: Optional[float] = None,
    equity_check_usd: float = 0.0,
) -> Optional[ExitRecommendation]:
    """Score every (year, buyer) combination on probability-weighted
    proceeds; pick the top."""
    if not curve or not buyers:
        return None

    # For each buyer, adjust the exit curve's multiple by the
    # playbook's expected premium/discount. This produces an
    # expected-value-adjusted proceeds per (year, buyer) combo.
    candidates: List[dict] = []
    for point in curve:
        for buyer in buyers:
            playbook = BUYER_PLAYBOOKS[buyer.buyer_type]
            mult_delta = playbook.multiple_premium_turns_mean
            adj_multiple = point.exit_multiple_assumed + mult_delta
            adj_terminal = point.ebitda_median_usd * adj_multiple
            adj_equity = max(
                0.0, adj_terminal - point.remaining_debt_usd,
            )
            adj_moic = (
                adj_equity / equity_check_usd
                if equity_check_usd > 0 else 0.0
            )
            if point.year <= 0 or adj_moic <= 0:
                adj_irr = 0.0
            else:
                adj_irr = adj_moic ** (1.0 / point.year) - 1.0
            prob_weighted_proceeds = (
                adj_equity * buyer.close_certainty
            )
            # Probability-weighted IRR is the right fund-level metric:
            # partners optimize IRR (not absolute $), and
            # close-certainty is the real-world probability of
            # actually getting it.
            weighted_irr = adj_irr * buyer.close_certainty
            # Fit-score gates the recommendation — buyers scoring
            # below 30 are treated as non-candidates.
            if buyer.fit_score < 30:
                continue
            candidates.append({
                "year": point.year,
                "buyer": buyer,
                "adj_moic": adj_moic,
                "adj_irr": adj_irr,
                "weighted_irr": weighted_irr,
                "adj_equity_proceeds": adj_equity,
                "prob_weighted_proceeds": prob_weighted_proceeds,
                "time_to_close": buyer.time_to_close_months,
            })

    if not candidates:
        return None

    # Rank primarily by probability-weighted IRR (partners optimize
    # for IRR, not absolute proceeds).  Tie-breaks: MOIC first,
    # then shorter time-to-close.
    # If no candidate clears MOIC ≥ 1.5x the scenario is marginal —
    # we still produce a recommendation but flag it below-hurdle so
    # partners see the real read rather than a silent None.
    above_hurdle = [c for c in candidates if c["adj_moic"] >= 1.5]
    below_hurdle_flag = not above_hurdle
    pool = above_hurdle if above_hurdle else candidates
    if not pool:
        return None
    pool.sort(key=lambda c: (
        -c["weighted_irr"], -c["adj_moic"], c["time_to_close"],
    ))
    candidates = pool
    top = candidates[0]
    buyer: BuyerFitScore = top["buyer"]

    # Compare to the year-5 strategic baseline — this is the default
    # PE assumption.  Rationale sentence quotes the delta.
    baseline_candidate = next(
        (c for c in candidates
         if c["year"] == 5 and c["buyer"].buyer_type == BuyerType.STRATEGIC),
        None,
    )
    rationale: str
    if baseline_candidate and (
        top["year"] != baseline_candidate["year"]
        or top["buyer"].buyer_type != baseline_candidate["buyer"].buyer_type
    ):
        delta_irr = top["adj_irr"] - baseline_candidate["adj_irr"]
        delta_proceeds = (
            top["prob_weighted_proceeds"]
            - baseline_candidate["prob_weighted_proceeds"]
        )
        if top["year"] < baseline_candidate["year"]:
            rationale = (
                f"Year {top['year']} to {buyer.label.lower()} clears "
                f"{top['adj_irr']*100:.1f}% IRR vs year "
                f"{baseline_candidate['year']} strategic at "
                f"{baseline_candidate['adj_irr']*100:.1f}% — the extra "
                f"{baseline_candidate['year'] - top['year']}-year hold "
                f"costs {abs(delta_irr)*100:.1f} pp of IRR."
            )
        else:
            rationale = (
                f"Year {top['year']} to {buyer.label.lower()} at "
                f"{top['adj_irr']*100:.1f}% IRR beats year "
                f"{baseline_candidate['year']} strategic at "
                f"{baseline_candidate['adj_irr']*100:.1f}% by "
                f"{delta_irr*100:+.1f} pp, "
                f"${delta_proceeds:,.0f} probability-weighted."
            )
    else:
        rationale = (
            f"Default base case: year {top['year']} exit to "
            f"{buyer.label.lower()} at {top['adj_irr']*100:.1f}% IRR."
        )

    summary = (
        f"Recommended exit: year {top['year']} to "
        f"{buyer.label.lower()}. Expected MOIC "
        f"{top['adj_moic']:.2f}x, IRR {top['adj_irr']*100:.1f}%, "
        f"probability-weighted proceeds "
        f"${top['prob_weighted_proceeds']:,.0f} "
        f"(close certainty {buyer.close_certainty*100:.0f}%, "
        f"time-to-close {buyer.time_to_close_months:.0f} months)."
    )
    if below_hurdle_flag:
        summary = (
            "⚠ No exit candidate clears the 1.5x MOIC hurdle. "
            + summary
            + " This scenario is structurally marginal — partner should "
            "consider offer-shape modifications or walkaway."
        )
        rationale = (
            "Best-of-bad options: " + rationale
            + " All candidate exit years produce MOIC below 1.5x. "
            "The thesis needs material improvement (revenue uplift, "
            "debt restructure, or entry-multiple reduction) before "
            "the curve clears."
        )

    return ExitRecommendation(
        exit_year=top["year"],
        buyer_type=buyer.buyer_type,
        buyer_label=buyer.label,
        expected_moic=top["adj_moic"],
        expected_irr=top["adj_irr"],
        expected_proceeds_usd=top["adj_equity_proceeds"],
        probability_weighted_proceeds_usd=top["prob_weighted_proceeds"],
        summary=summary,
        rationale=rationale,
    )


# ────────────────────────────────────────────────────────────────────
# Public entry
# ────────────────────────────────────────────────────────────────────

def analyze_exit_timing(
    *,
    equity_check_usd: float,
    debt_year0_usd: float,
    ebitda_median_by_year: Sequence[float],
    exit_multiple_by_year: Optional[Sequence[float]] = None,
    peer_median_multiple: Optional[float] = None,
    # Target profile for buyer-fit scoring
    regulatory_verdict: Optional[str] = None,
    commercial_payer_share: Optional[float] = None,
    sector_sentiment: Optional[str] = None,
    management_score: Optional[int] = None,
    top_1_payer_share: Optional[float] = None,
    candidate_holds: Sequence[int] = DEFAULT_CANDIDATE_HOLDS,
) -> ExitTimingReport:
    """Compose the full exit-timing analysis.

    ``exit_multiple_by_year`` is optional — when not supplied we use
    a flat projection anchored on ``peer_median_multiple`` or a
    9.0x hospital-system default.
    """
    if exit_multiple_by_year is None:
        anchor = peer_median_multiple or 9.0
        exit_multiple_by_year = [anchor] * (
            max(candidate_holds) + 1
            if candidate_holds else 8
        )

    curve = build_exit_curve(
        equity_check_usd=equity_check_usd,
        debt_year0_usd=debt_year0_usd,
        ebitda_median_by_year=ebitda_median_by_year,
        exit_multiple_by_year=exit_multiple_by_year,
        candidate_holds=candidate_holds,
    )

    # Use the exit-year EBITDA for buyer fit — specifically the
    # candidate with the peak IRR, or fall back to the last year.
    reference_year = 5 if 5 in candidate_holds else (
        candidate_holds[-1] if candidate_holds else 5
    )
    ref_ebitda: Optional[float] = None
    for p in curve:
        if p.year == reference_year:
            ref_ebitda = p.ebitda_median_usd
            break
    if ref_ebitda is None and curve:
        ref_ebitda = curve[-1].ebitda_median_usd

    buyers = score_all_buyers(
        ebitda_year_exit_usd=ref_ebitda,
        regulatory_verdict=regulatory_verdict,
        commercial_payer_share=commercial_payer_share,
        sector_sentiment=sector_sentiment,
        management_score=management_score,
        top_1_payer_share=top_1_payer_share,
    )

    recommendation = _recommend(
        curve=curve, buyers=buyers,
        peer_median_multiple=peer_median_multiple,
        equity_check_usd=equity_check_usd,
    )

    return ExitTimingReport(
        curve=curve,
        buyer_fit=buyers,
        recommendation=recommendation,
        peer_median_multiple=peer_median_multiple,
        sector_sentiment=sector_sentiment,
    )
