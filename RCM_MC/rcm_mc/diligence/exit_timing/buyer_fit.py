"""Per-buyer-type fit scorer.

Each buyer type has characteristic preferences. Given a target's
profile (category, EBITDA scale, payer mix, regulatory overhang,
management score, sector sentiment), return a 0–100 fit score
per buyer + the driver list behind the score.

Fit scores feed the final recommendation — the best buyer type
isn't always the one paying the highest headline multiple; it's
the one whose fit score × close certainty × expected multiple
maximises probability-weighted proceeds.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .playbook import BUYER_PLAYBOOKS, BuyerPlaybook, BuyerType


@dataclass
class BuyerFitScore:
    """Scored fit for one buyer type."""
    buyer_type: BuyerType
    label: str
    fit_score: int                      # 0–100
    expected_multiple_turns_delta: float  # premium / discount vs peer median
    close_certainty: float              # [0, 1]
    time_to_close_months: float
    favorable_hits: List[str] = field(default_factory=list)
    unfavorable_hits: List[str] = field(default_factory=list)
    narrative: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "buyer_type": self.buyer_type.value,
            "label": self.label,
            "fit_score": self.fit_score,
            "expected_multiple_turns_delta":
                self.expected_multiple_turns_delta,
            "close_certainty": self.close_certainty,
            "time_to_close_months": self.time_to_close_months,
            "favorable_hits": list(self.favorable_hits),
            "unfavorable_hits": list(self.unfavorable_hits),
            "narrative": self.narrative,
        }


# ────────────────────────────────────────────────────────────────────
# Heuristic checks — each returns a (hit, driver_label) tuple
# ────────────────────────────────────────────────────────────────────

def _check_scale_for_strategic(ebitda_usd: Optional[float]) -> Optional[Tuple[bool, str]]:
    if ebitda_usd is None:
        return None
    # Strategic buyers look for $10-100M EBITDA targets where they
    # can extract synergy; above $100M is platform-sized and sells
    # to PE/IPO instead.
    if 10_000_000 <= ebitda_usd <= 150_000_000:
        return (True, "EBITDA scale in strategic-buyer sweet spot ($10-150M)")
    if ebitda_usd > 200_000_000:
        return (False, "EBITDA exceeds strategic-buyer appetite — platform-sized")
    return (False, "EBITDA below strategic-buyer threshold")


def _check_scale_for_ipo(ebitda_usd: Optional[float]) -> Optional[Tuple[bool, str]]:
    if ebitda_usd is None:
        return None
    if ebitda_usd >= 100_000_000:
        return (True, "EBITDA $100M+ supports IPO scale requirement")
    return (False, "EBITDA below $100M — IPO unlikely to clear")


def _check_scale_for_pe(ebitda_usd: Optional[float]) -> Optional[Tuple[bool, str]]:
    if ebitda_usd is None:
        return None
    if 20_000_000 <= ebitda_usd <= 500_000_000:
        return (True, "EBITDA in PE-secondary clearing range ($20-500M)")
    if ebitda_usd < 15_000_000:
        return (False, "EBITDA below PE-secondary minimum — too small for fund thesis")
    return None


def _check_regulatory(verdict: Optional[str]) -> Optional[Tuple[bool, str]]:
    if verdict is None:
        return None
    v = str(verdict or "").upper()
    if v in ("GREEN",):
        return (True, "Regulatory composite GREEN — clean room for any buyer")
    if v in ("YELLOW",):
        return (True, "Regulatory composite YELLOW — manageable")
    if v in ("RED", "CRITICAL"):
        return (False, f"Regulatory composite {v} — HSR / DOJ overhang")
    return None


def _check_payer_mix(commercial_pct: Optional[float]) -> Optional[Tuple[bool, str]]:
    if commercial_pct is None:
        return None
    if commercial_pct >= 0.40:
        return (True, f"Commercial payer mix {commercial_pct*100:.0f}% — strong in-network revenue")
    if commercial_pct <= 0.15:
        return (False, f"Commercial mix only {commercial_pct*100:.0f}% — Medicare-dependent")
    return None


def _check_sector_sentiment(sentiment: Optional[str]) -> Optional[Tuple[bool, str]]:
    if sentiment is None:
        return None
    s = str(sentiment or "").lower()
    if s in ("positive",):
        return (True, "Sector sentiment positive — window is open")
    if s in ("negative",):
        return (False, "Sector sentiment negative — exit window shut")
    return None


def _check_management(mgmt_score: Optional[int]) -> Optional[Tuple[bool, str]]:
    if mgmt_score is None:
        return None
    if mgmt_score >= 75:
        return (True, f"Management scorecard {mgmt_score}/100 — team is a thesis asset")
    if mgmt_score < 50:
        return (False, f"Management scorecard {mgmt_score}/100 — team is a thesis risk")
    return None


def _check_concentration(top_1_payer_share: Optional[float]) -> Optional[Tuple[bool, str]]:
    if top_1_payer_share is None:
        return None
    if top_1_payer_share <= 0.25:
        return (True, f"Top-1 payer share {top_1_payer_share*100:.0f}% — diversified")
    if top_1_payer_share > 0.40:
        return (False, f"Top-1 payer share {top_1_payer_share*100:.0f}% — concentration risk")
    return None


# ────────────────────────────────────────────────────────────────────
# Buyer-specific scoring rubrics
# ────────────────────────────────────────────────────────────────────

def score_buyer_fit(
    buyer_type: BuyerType,
    *,
    ebitda_year_exit_usd: Optional[float] = None,
    regulatory_verdict: Optional[str] = None,
    commercial_payer_share: Optional[float] = None,
    sector_sentiment: Optional[str] = None,
    management_score: Optional[int] = None,
    top_1_payer_share: Optional[float] = None,
) -> BuyerFitScore:
    """Score one buyer type against the target's profile."""
    playbook = BUYER_PLAYBOOKS[buyer_type]
    score = 50  # neutral starting point
    favorable: List[str] = []
    unfavorable: List[str] = []

    # Common checks across all buyer types
    for check_fn, weight in (
        (lambda: _check_regulatory(regulatory_verdict), 15),
        (lambda: _check_concentration(top_1_payer_share), 10),
        (lambda: _check_sector_sentiment(sector_sentiment), 10),
    ):
        result = check_fn()
        if result is None:
            continue
        hit, label = result
        if hit:
            score += weight
            favorable.append(label)
        else:
            score -= weight
            unfavorable.append(label)

    # Buyer-specific checks
    if buyer_type == BuyerType.STRATEGIC:
        for check_fn, weight in (
            (lambda: _check_scale_for_strategic(ebitda_year_exit_usd), 12),
            (lambda: _check_payer_mix(commercial_payer_share), 8),
            (lambda: _check_management(management_score), 5),
        ):
            result = check_fn()
            if result is None:
                continue
            hit, label = result
            if hit:
                score += weight
                favorable.append(label)
            else:
                score -= weight
                unfavorable.append(label)
    elif buyer_type == BuyerType.PE_SECONDARY:
        for check_fn, weight in (
            (lambda: _check_scale_for_pe(ebitda_year_exit_usd), 12),
            (lambda: _check_management(management_score), 8),
        ):
            result = check_fn()
            if result is None:
                continue
            hit, label = result
            if hit:
                score += weight
                favorable.append(label)
            else:
                score -= weight
                unfavorable.append(label)
    elif buyer_type == BuyerType.IPO:
        for check_fn, weight in (
            (lambda: _check_scale_for_ipo(ebitda_year_exit_usd), 18),
            (lambda: _check_management(management_score), 8),
            (lambda: _check_payer_mix(commercial_payer_share), 5),
        ):
            result = check_fn()
            if result is None:
                continue
            hit, label = result
            if hit:
                score += weight
                favorable.append(label)
            else:
                score -= weight
                unfavorable.append(label)
    elif buyer_type == BuyerType.SPONSOR_HOLD:
        # Sponsor hold score is a residual — partners pick it when
        # other exits are unattractive.  Score 40 default.
        score = 40

    score = max(0, min(100, score))

    narrative = playbook.narrative
    if score >= 75 and favorable:
        narrative = (
            f"{playbook.label} is the highest-fit channel — "
            f"{favorable[0].lower()} and "
            f"{favorable[1].lower() if len(favorable) > 1 else 'other positive drivers'}."
        )
    elif score < 40 and unfavorable:
        narrative = (
            f"{playbook.label} is a poor fit — "
            f"{unfavorable[0].lower()}."
        )

    return BuyerFitScore(
        buyer_type=buyer_type,
        label=playbook.label,
        fit_score=score,
        expected_multiple_turns_delta=playbook.multiple_premium_turns_mean,
        close_certainty=playbook.close_certainty,
        time_to_close_months=playbook.time_to_close_months_mean,
        favorable_hits=favorable,
        unfavorable_hits=unfavorable,
        narrative=narrative,
    )


def score_all_buyers(**kwargs: Any) -> List[BuyerFitScore]:
    """Score every buyer type against the same target profile."""
    out: List[BuyerFitScore] = []
    for bt in BuyerType:
        out.append(score_buyer_fit(bt, **kwargs))
    return out
