"""CMS-driven geographic white-space market mapping.

Identifies the highest-opportunity state × provider-type combinations
for platform expansion by combining:
  - Market concentration (HHI) — fragmented markets = more white space
  - State fit score — top-quartile growth + stability
  - Opportunity score (scale × margin × acuity)
  - Regime classification — durable_growth markets preferred

Extends the white_space_opportunities() function in cms_market_analysis
with richer scoring and visualization support.

Public API:
    WhiteSpaceOpportunity                 dataclass
    compute_white_space_map(report, ...)  -> list[WhiteSpaceOpportunity]
    top_white_space(report, n)           -> list[WhiteSpaceOpportunity]
    white_space_table(opportunities)     -> str
    white_space_summary(opportunities)   -> dict
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class WhiteSpaceOpportunity:
    """One state × provider-type white-space entry."""

    state: str
    provider_type: str

    # Component signals
    hhi: Optional[float] = None
    state_fit_score: Optional[float] = None
    opportunity_score: Optional[float] = None
    regime: Optional[str] = None

    # Derived
    white_space_score: float = 0.0
    fragmentation_signal: str = "neutral"     # fragmented / neutral / concentrated
    fit_signal: str = "neutral"               # top / mid / low
    regime_signal: str = "unknown"


# ---------------------------------------------------------------------------
# Score computation
# ---------------------------------------------------------------------------

_W_FRAGMENTATION = 0.30   # HHI-based (lower HHI = more white space)
_W_FIT = 0.35             # state fit score
_W_OPPORTUNITY = 0.25     # opportunity score
_W_REGIME = 0.10          # regime classification bonus


def _fragmentation_score(hhi: Optional[float]) -> tuple[float, str]:
    """Convert HHI to a 0-1 fragmentation score (1 = most fragmented)."""
    if hhi is None:
        return 0.5, "neutral"
    if hhi < 1500:
        return 1.0, "fragmented"
    if hhi < 2500:
        return 0.6, "neutral"
    return 0.2, "concentrated"


def _fit_signal(fit_score: Optional[float], all_scores: List[float]) -> tuple[float, str]:
    if fit_score is None or not all_scores:
        return 0.5, "neutral"
    # Normalize to 0-1 within the distribution
    min_s = min(all_scores)
    max_s = max(all_scores)
    if max_s == min_s:
        return 0.5, "neutral"
    normalized = (fit_score - min_s) / (max_s - min_s)
    label = "top" if normalized >= 0.67 else ("low" if normalized < 0.33 else "mid")
    return normalized, label


def _regime_bonus(regime: Optional[str]) -> float:
    return {
        "durable_growth": 0.20,
        "steady_compounders": 0.10,
        "emerging_volatile": 0.05,
        "stagnant": -0.05,
        "declining_risk": -0.15,
    }.get(regime or "", 0.0)


def compute_white_space_map(
    report: Any,   # MarketAnalysisReport
    min_fit_percentile: float = 0.33,
    provider_types: Optional[List[str]] = None,
) -> List["WhiteSpaceOpportunity"]:
    """Compute white-space scores for all state × provider-type pairs.

    Parameters
    ----------
    report :
        MarketAnalysisReport from run_market_analysis().
    min_fit_percentile :
        Minimum state_fit_score percentile to include (0–1).
    provider_types :
        If given, restrict to these provider types.
    """
    import pandas as pd

    results: List[WhiteSpaceOpportunity] = []

    # Build lookups
    conc = report.concentration if hasattr(report, "concentration") else pd.DataFrame()
    fit = report.portfolio_fit if hasattr(report, "portfolio_fit") else pd.DataFrame()
    regimes = report.regimes if hasattr(report, "regimes") else pd.DataFrame()

    # HHI lookup: (state, provider_type) → hhi
    hhi_lookup: Dict[tuple, float] = {}
    if not conc.empty and "state" in conc.columns and "hhi" in conc.columns:
        for _, row in conc.iterrows():
            key = (str(row.get("state", "")), str(row.get("provider_type", "")))
            try:
                hhi_lookup[key] = float(row["hhi"])
            except (TypeError, ValueError):
                pass

    # Fit lookup: state → fit_score
    fit_scores: Dict[str, float] = {}
    all_fit_vals: List[float] = []
    if not fit.empty and "state" in fit.columns and "state_fit_score" in fit.columns:
        for _, row in fit.iterrows():
            try:
                s = float(row["state_fit_score"])
                fit_scores[str(row["state"])] = s
                all_fit_vals.append(s)
            except (TypeError, ValueError):
                pass

    # Regime lookup: provider_type → regime
    regime_lookup: Dict[str, str] = {}
    if not regimes.empty and "provider_type" in regimes.columns and "regime" in regimes.columns:
        for _, row in regimes.iterrows():
            regime_lookup[str(row["provider_type"])] = str(row["regime"])

    # Opportunity lookup: (state, provider_type) → opp_score (from state_growth as proxy)
    opp_lookup: Dict[tuple, float] = {}
    state_growth = report.state_growth if hasattr(report, "state_growth") else pd.DataFrame()
    if not state_growth.empty and "state" in state_growth.columns:
        for col in ["regional_opportunity_score", "growth_rate", "cagr"]:
            if col in state_growth.columns:
                for _, row in state_growth.iterrows():
                    pt = str(row.get("provider_type", "*"))
                    key = (str(row.get("state", "")), pt)
                    try:
                        opp_lookup[key] = float(row[col])
                    except (TypeError, ValueError):
                        pass
                break

    # Determine states + provider_types to evaluate
    states = list(fit_scores.keys()) or list({k[0] for k in hhi_lookup})
    pts = provider_types or list({k[1] for k in hhi_lookup}) or list(regime_lookup.keys())
    if not states or not pts:
        return []

    # Apply fit percentile filter
    if all_fit_vals:
        import statistics
        fit_cutoff = sorted(all_fit_vals)[max(0, int(min_fit_percentile * len(all_fit_vals)) - 1)]
    else:
        fit_cutoff = float("-inf")

    for state in states:
        f_score = fit_scores.get(state)
        if f_score is not None and f_score < fit_cutoff:
            continue

        for pt in pts:
            hhi = hhi_lookup.get((state, pt)) or hhi_lookup.get((state, "*"))
            opp = opp_lookup.get((state, pt)) or opp_lookup.get((state, "*"))
            regime = regime_lookup.get(pt)
            fit_val = f_score

            frag_s, frag_label = _fragmentation_score(hhi)
            fit_normalized, fit_label = _fit_signal(fit_val, all_fit_vals)

            # Normalize opportunity to 0-1
            all_opps = list(opp_lookup.values())
            if opp is not None and all_opps:
                min_o, max_o = min(all_opps), max(all_opps)
                opp_norm = (opp - min_o) / (max_o - min_o) if max_o != min_o else 0.5
            else:
                opp_norm = 0.5

            regime_b = _regime_bonus(regime)

            score = (
                _W_FRAGMENTATION * frag_s
                + _W_FIT * fit_normalized
                + _W_OPPORTUNITY * opp_norm
                + _W_REGIME * (regime_b + 0.75)  # shift to 0-1 range
            )

            results.append(WhiteSpaceOpportunity(
                state=state,
                provider_type=pt,
                hhi=hhi,
                state_fit_score=fit_val,
                opportunity_score=opp,
                regime=regime,
                white_space_score=round(score, 4),
                fragmentation_signal=frag_label,
                fit_signal=fit_label,
                regime_signal=regime or "unknown",
            ))

    results.sort(key=lambda r: r.white_space_score, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def top_white_space(
    report: Any,
    n: int = 10,
    **kwargs: Any,
) -> List[WhiteSpaceOpportunity]:
    """Return the top n white-space opportunities from a MarketAnalysisReport."""
    return compute_white_space_map(report, **kwargs)[:n]


def white_space_table(opportunities: List[WhiteSpaceOpportunity]) -> str:
    """Formatted text table of white-space opportunities."""
    if not opportunities:
        return "No white-space opportunities identified.\n"

    lines = [
        "Geographic White-Space Map",
        "=" * 80,
        f"{'State':<8} {'Provider Type':<28} {'WS Score':>8} {'HHI':>8} {'Fit':>8} {'Regime':<22}",
        "-" * 80,
    ]
    for opp in opportunities:
        hhi_s = f"{opp.hhi:,.0f}" if opp.hhi is not None else "N/A"
        fit_s = f"{opp.state_fit_score:.3f}" if opp.state_fit_score is not None else "N/A"
        lines.append(
            f"{opp.state:<8} {opp.provider_type:<28} {opp.white_space_score:>8.3f} "
            f"{hhi_s:>8} {fit_s:>8} {opp.regime_signal:<22}"
        )
    lines.append("=" * 80)
    return "\n".join(lines) + "\n"


def white_space_summary(opportunities: List[WhiteSpaceOpportunity]) -> Dict[str, Any]:
    """Machine-readable summary of the white-space map."""
    if not opportunities:
        return {"total": 0, "top_state": None, "top_provider_type": None}

    top = opportunities[0]
    fragmented = [o for o in opportunities if o.fragmentation_signal == "fragmented"]
    durable = [o for o in opportunities if o.regime_signal == "durable_growth"]

    return {
        "total": len(opportunities),
        "top_state": top.state,
        "top_provider_type": top.provider_type,
        "top_score": top.white_space_score,
        "top_regime": top.regime_signal,
        "fragmented_count": len(fragmented),
        "durable_growth_count": len(durable),
        "states_covered": len({o.state for o in opportunities}),
        "provider_types_covered": len({o.provider_type for o in opportunities}),
    }
