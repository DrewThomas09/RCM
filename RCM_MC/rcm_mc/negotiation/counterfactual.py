"""Counterfactual market-structure simulation + antitrust risk.

Two operations:

  • simulate_post_merger_rate: re-runs the Nash bargaining with a
    counterfactual "merged" provider that combines the volumes of
    two providers. Reduces payer's outside options (one less
    alternative network), raising the equilibrium rate.

  • antitrust_risk_score: HHI-style Herfindahl on the post-merger
    market share by provider. Used to flag transactions likely to
    draw FTC/DOJ scrutiny.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

from .bargaining import nash_bargaining, repeated_game_rate
from .outside_options import compute_outside_options


def simulate_post_merger_rate(
    pricing_store: Any,
    npi_list: List[str],
    code: str,
    payer_name: str,
    *,
    payer_leverage_pre: float = 0.5,
    payer_leverage_post: float = 0.3,
) -> Dict[str, Any]:
    """Compare the negotiated rate before vs after a merger.

    Pre-merger: each NPI bargains independently → averaged.
    Post-merger: the merged entity has the combined outside-option
    distribution AND the payer's leverage drops (fewer alternatives).

    Returns a dict with both rates + the implied uplift in $/service
    and percent.
    """
    if not npi_list:
        raise ValueError("npi_list must contain at least one NPI")

    # Pre-merger: each NPI bargains alone using the FULL corpus
    # of outside options (including the other NPIs in the merger).
    pre_rates: List[float] = []
    for npi in npi_list:
        oo = compute_outside_options(
            pricing_store, npi, code,
            exclude_payer=payer_name,
        )
        if oo.rate_count == 0:
            continue
        state = repeated_game_rate(
            oo, payer_name=payer_name,
            payer_leverage=payer_leverage_pre,
        )
        pre_rates.append(state.negotiated_rate)

    pre_avg = (sum(pre_rates) / len(pre_rates)) if pre_rates else 0.0

    # Post-merger: combine the outside-options across all NPIs
    # in the merger AND drop the merger NPIs from each other's
    # outside options (they're no longer alternatives — same
    # entity).
    combined_rates: List[float] = []
    for npi in npi_list:
        oo = compute_outside_options(
            pricing_store, npi, code,
            exclude_payer=payer_name,
        )
        # Drop rates that came from any of the merging NPIs by
        # iterating the corpus directly. Since list_negotiated_rates
        # doesn't reveal the source NPI per-row easily here,
        # approximate by dropping a fraction proportional to the
        # number of merging NPIs in the dispersion.
        if oo.rate_count == 0:
            continue
        # Estimated reduction: each merging NPI removes a slice of
        # the dispersion equal to 1/payer_count from the lower tail
        # (since the payer can no longer steer to those NPIs).
        drop_frac = max(0.0,
                        min(0.5, (len(npi_list) - 1) / max(
                            2, oo.payer_count)))
        keep = sorted(oo.rates)
        cut = int(round(len(keep) * drop_frac))
        keep = keep[cut:]  # drop bottom rates → reduces payer's
                           # downside leverage in the bargaining
        # Re-summarize
        from .outside_options import _percentile, OutsideOptions
        oo_post = OutsideOptions(
            npi=npi, code=code,
            payer_count=max(0, oo.payer_count - 1),
            rate_count=len(keep), rates=keep,
            p25=_percentile(keep, 0.25),
            p50=_percentile(keep, 0.50),
            p75=_percentile(keep, 0.75),
            surplus=(_percentile(keep, 0.75) or 0.0)
                    - (_percentile(keep, 0.25) or 0.0),
        )
        state = repeated_game_rate(
            oo_post, payer_name=payer_name,
            payer_leverage=payer_leverage_post,
        )
        combined_rates.append(state.negotiated_rate)

    post_avg = ((sum(combined_rates) / len(combined_rates))
                if combined_rates else 0.0)
    uplift = post_avg - pre_avg
    uplift_pct = (uplift / pre_avg) if pre_avg > 0 else 0.0

    return {
        "code": code,
        "payer_name": payer_name,
        "merging_npi_count": len(npi_list),
        "pre_merger_rate": round(pre_avg, 2),
        "post_merger_rate": round(post_avg, 2),
        "uplift_dollars": round(uplift, 2),
        "uplift_pct": round(uplift_pct, 4),
    }


def antitrust_risk_score(
    market_shares: Iterable[float],
    *,
    pre_post_delta_threshold: int = 200,
) -> Dict[str, Any]:
    """HHI-based antitrust risk score.

    HHI = Σ (share × 100)² across competitors.
      <1500  → unconcentrated
      1500-2500 → moderately concentrated
      >2500   → highly concentrated; merger raising HHI by >200
               points typically draws DOJ/FTC scrutiny.

    ``market_shares`` is the POST-merger distribution. The function
    reports the post-merger HHI and a categorical risk band.
    """
    shares = [float(s) for s in market_shares
              if s is not None and float(s) > 0]
    total = sum(shares)
    if total <= 0:
        return {"hhi": 0.0, "band": "unconcentrated"}
    norm = [(s / total) * 100.0 for s in shares]
    hhi = sum(s * s for s in norm)

    if hhi < 1500:
        band = "unconcentrated"
    elif hhi < 2500:
        band = "moderately_concentrated"
    else:
        band = "highly_concentrated"

    return {
        "hhi": round(hhi, 1),
        "band": band,
        "n_competitors": len(shares),
        "max_share_pct": round(max(norm), 1),
    }
