"""Equity-story scoring per archetype.

Every buyer archetype pays for a different *story*. A strategic
pays for cross-sell; a public-market IPO pays for growth durability;
a take-private pays for predictable margin. This module scores how
well an asset's actual profile maps to what each archetype values,
returning a 0-1 fit score the optimizer uses to weight valuations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .target import ExitTarget, ExitArchetype


@dataclass
class EquityStoryScore:
    archetype: ExitArchetype
    fit_score: float       # 0-1
    matched_themes: List[str]
    missing_themes: List[str]


# Map of archetype → (theme_name → weight, asset_check_fn)
def _strategic_themes(target: ExitTarget) -> Dict[str, bool]:
    return {
        "diversified_payer_mix": target.payer_concentration < 0.5,
        "cross_sell_optionality": target.cash_pay_share > 0.10,
        "growth_above_market": target.growth_rate > 0.10,
    }


def _secondary_pe_themes(target: ExitTarget) -> Dict[str, bool]:
    return {
        "stable_ebitda_margin": target.ebitda_margin > 0.15,
        "solid_growth_curve": target.growth_rate > 0.05,
        "manageable_concentration": target.physician_concentration < 0.4,
    }


def _take_private_themes(target: ExitTarget) -> Dict[str, bool]:
    return {
        "public_market_comp_strong": target.public_comp_multiple >= 12,
        "predictable_margin": target.ebitda_margin > 0.18,
        "low_payer_concentration": target.payer_concentration < 0.5,
    }


def _ipo_themes(target: ExitTarget) -> Dict[str, bool]:
    return {
        "scale_above_floor": target.ttm_revenue_mm >= 200,
        "durable_growth": target.growth_durability_score >= 0.6,
        "non_concentrated_revenue": target.payer_concentration < 0.4,
    }


def _continuation_themes(target: ExitTarget) -> Dict[str, bool]:
    return {
        "growing_asset": target.growth_rate > 0.07,
        "stable_margin": target.ebitda_margin > 0.15,
    }


def _div_recap_themes(target: ExitTarget) -> Dict[str, bool]:
    return {
        "high_recurring_ebitda": target.ttm_ebitda_mm > 25,
        "low_existing_leverage": (target.net_debt_mm
                                  / max(0.1, target.ttm_ebitda_mm)
                                  ) < 4.0,
    }


_THEME_FNS = {
    ExitArchetype.STRATEGIC: _strategic_themes,
    ExitArchetype.SECONDARY_PE: _secondary_pe_themes,
    ExitArchetype.SPONSOR_TO_SPONSOR: _secondary_pe_themes,
    ExitArchetype.TAKE_PRIVATE: _take_private_themes,
    ExitArchetype.CONTINUATION: _continuation_themes,
    ExitArchetype.IPO: _ipo_themes,
    ExitArchetype.DIVIDEND_RECAP: _div_recap_themes,
}


def score_equity_story(
    target: ExitTarget,
    archetype: ExitArchetype,
) -> EquityStoryScore:
    """Score the asset's fit to a specific archetype's story."""
    fn = _THEME_FNS.get(archetype)
    if not fn:
        return EquityStoryScore(
            archetype=archetype, fit_score=0.0,
            matched_themes=[], missing_themes=[])
    themes = fn(target)
    matched = [k for k, v in themes.items() if v]
    missing = [k for k, v in themes.items() if not v]
    fit = len(matched) / max(1, len(themes))
    return EquityStoryScore(
        archetype=archetype,
        fit_score=round(fit, 3),
        matched_themes=matched,
        missing_themes=missing,
    )
