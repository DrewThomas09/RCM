"""CMS-driven benchmark calibration for the public deals corpus.

Bridges the CMS analytics pipeline (market concentration, regime
classification, opportunity scoring) into the base-rate benchmarks
so deal-level MOIC/IRR estimates reflect real CMS market conditions.

Calibration logic:
  1. Pull CMS state/provider-type data for a given year.
  2. Compute concentration (HHI), regime, and opportunity scores.
  3. Map those signals to MOIC adjustment factors.
  4. Return a CalibrationResult that can update Benchmarks objects.

Public API:
    CalibrationResult                     dataclass
    calibrate_from_cms(year, state, ...)  -> CalibrationResult
    apply_calibration(benchmarks, cal)    -> dict   (adjusted P25/P50/P75)
    calibration_text(cal)                 -> str
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# CalibrationResult
# ---------------------------------------------------------------------------

@dataclass
class CalibrationResult:
    """Output of a CMS-driven calibration run."""

    year: int
    state_filter: Optional[str]
    provider_type_filter: Optional[str]

    # HHI signals
    median_hhi: Optional[float] = None
    high_concentration_pct: float = 0.0   # fraction of markets with HHI > 2500

    # Regime signals
    durable_growth_count: int = 0
    declining_risk_count: int = 0
    regime_ratio: Optional[float] = None  # durable / (durable + declining)

    # Opportunity signals
    median_opportunity_score: Optional[float] = None
    top_provider_type: Optional[str] = None

    # Derived MOIC adjustment
    moic_uplift_factor: float = 1.0
    confidence: str = "low"          # low / medium / high

    errors: List[str] = field(default_factory=list)
    source_row_count: int = 0


# ---------------------------------------------------------------------------
# Calibration logic
# ---------------------------------------------------------------------------

_HHI_THRESHOLDS = {
    "competitive": 1500,
    "moderate": 2500,
    "concentrated": float("inf"),
}

_REGIME_UPLIFT = {
    # regime_ratio → moic_uplift
    "strong": 1.15,    # >= 0.70 durable ratio
    "neutral": 1.00,   # 0.40–0.70
    "weak": 0.88,      # < 0.40
}


def _hhi_adjustment(median_hhi: Optional[float], high_pct: float) -> float:
    """Return a concentration-based moic adjustment factor.

    High concentration (fewer competitors) is modestly positive for
    platform operators but negative for new entrants paying entry premiums.
    We apply a slight penalty for extreme concentration (HHI > 4000).
    """
    if median_hhi is None:
        return 1.0
    if median_hhi > 4000:
        return 0.95  # very concentrated — entry premium risk
    if median_hhi > 2500:
        return 1.00  # moderate concentration — neutral
    return 1.05      # competitive market — more upside from consolidation


def _regime_adjustment(durable: int, declining: int) -> tuple[float, Optional[float]]:
    """Return (uplift_factor, regime_ratio) from regime counts."""
    total = durable + declining
    if total == 0:
        return 1.0, None
    ratio = durable / total
    if ratio >= 0.70:
        return _REGIME_UPLIFT["strong"], ratio
    if ratio >= 0.40:
        return _REGIME_UPLIFT["neutral"], ratio
    return _REGIME_UPLIFT["weak"], ratio


def _opportunity_adjustment(opp_score: Optional[float]) -> float:
    """Return uplift based on opportunity score (0–1 scale)."""
    if opp_score is None:
        return 1.0
    # Linear interpolation: 0.5 → 1.0x, 1.0 → 1.10x, 0.0 → 0.92x
    return round(0.92 + opp_score * 0.18, 4)


def _confidence_level(row_count: int, errors: List[str]) -> str:
    if errors or row_count < 50:
        return "low"
    if row_count < 300:
        return "medium"
    return "high"


def calibrate_from_cms(
    year: int = 2021,
    state: Optional[str] = None,
    provider_type: Optional[str] = None,
    max_pages: int = 5,
    limit: int = 500,
    df=None,  # Optional pre-loaded DataFrame to skip HTTP
) -> CalibrationResult:
    """Run a CMS-driven calibration for the given year/filters.

    If df is provided, uses it directly (useful for testing without HTTP).
    Falls back gracefully on any API errors.
    """
    result = CalibrationResult(
        year=year,
        state_filter=state,
        provider_type_filter=provider_type,
    )

    try:
        from .cms_market_analysis import run_market_analysis
        from .cms_opportunity_scoring import provider_screen, enrich_features

        report = run_market_analysis(
            year=year,
            state=state,
            provider_type=provider_type,
            max_pages=max_pages,
            limit=limit,
            df=df,
        )
        result.source_row_count = report.row_count
        result.errors = list(report.errors)

        # HHI signals
        if not report.concentration.empty and "hhi" in report.concentration.columns:
            import pandas as pd
            hhis = pd.to_numeric(report.concentration["hhi"], errors="coerce").dropna()
            if not hhis.empty:
                result.median_hhi = float(hhis.median())
                result.high_concentration_pct = float((hhis > 2500).sum() / len(hhis))

        # Regime signals
        if not report.regimes.empty and "regime" in report.regimes.columns:
            reg = report.regimes["regime"].astype(str)
            result.durable_growth_count = int((reg == "durable_growth").sum())
            result.declining_risk_count = int((reg == "declining_risk").sum())

        # Opportunity signals
        if not report.regimes.empty:
            try:
                raw_df = df
                if raw_df is None:
                    raw_df = report.regimes  # fallback: use regime df shape
                enriched = enrich_features(raw_df) if raw_df is not None else report.regimes
                screen = provider_screen(enriched)
                if not screen.empty and "opportunity_score" in screen.columns:
                    import pandas as pd
                    scores = pd.to_numeric(screen["opportunity_score"], errors="coerce").dropna()
                    if not scores.empty:
                        result.median_opportunity_score = float(scores.median())
                        top_row = screen.iloc[0]
                        result.top_provider_type = str(top_row.get("provider_type", ""))
            except Exception as e:
                result.errors.append(f"opportunity_scoring: {e}")

    except Exception as e:
        result.errors.append(f"calibration_error: {e}")

    # Derive combined MOIC uplift
    hhi_adj = _hhi_adjustment(result.median_hhi, result.high_concentration_pct)
    regime_adj, regime_ratio = _regime_adjustment(
        result.durable_growth_count, result.declining_risk_count
    )
    opp_adj = _opportunity_adjustment(result.median_opportunity_score)

    result.regime_ratio = regime_ratio
    result.moic_uplift_factor = round(hhi_adj * regime_adj * opp_adj, 4)
    result.confidence = _confidence_level(result.source_row_count, result.errors)

    return result


# ---------------------------------------------------------------------------
# Apply calibration to benchmarks
# ---------------------------------------------------------------------------

def apply_calibration(
    benchmarks: Dict[str, Any],
    cal: CalibrationResult,
) -> Dict[str, Any]:
    """Apply the calibration uplift factor to a benchmarks dict.

    Scales moic_p25 / moic_p50 / moic_p75 by cal.moic_uplift_factor.
    Returns a new dict (does not modify input).

    The benchmarks dict may come from base_rates.get_benchmarks() or
    any dict with moic_p25/p50/p75 keys.
    """
    out = dict(benchmarks)
    factor = cal.moic_uplift_factor
    for key in ("moic_p25", "moic_p50", "moic_p75", "moic_mean"):
        if key in out and out[key] is not None:
            try:
                out[key] = round(float(out[key]) * factor, 3)
            except (TypeError, ValueError):
                pass
    out["calibration_year"] = cal.year
    out["calibration_factor"] = factor
    out["calibration_confidence"] = cal.confidence
    return out


# ---------------------------------------------------------------------------
# Text output
# ---------------------------------------------------------------------------

def calibration_text(cal: CalibrationResult) -> str:
    """Human-readable calibration summary."""
    def _fmt(v: Any, fmt: str = ".3f") -> str:
        if v is None:
            return "N/A"
        try:
            return format(float(v), fmt)
        except (TypeError, ValueError):
            return str(v)

    lines = [
        f"CMS Benchmark Calibration — {cal.year}"
        + (f" [{cal.state_filter}]" if cal.state_filter else ""),
        "=" * 60,
        f"  Source rows          : {cal.source_row_count}",
        f"  Confidence           : {cal.confidence}",
        "-" * 60,
        f"  Median HHI           : {_fmt(cal.median_hhi, ',.0f')}",
        f"  High-conc markets    : {_fmt(cal.high_concentration_pct, '.1%')}",
        f"  Durable-growth count : {cal.durable_growth_count}",
        f"  Declining-risk count : {cal.declining_risk_count}",
        f"  Regime ratio         : {_fmt(cal.regime_ratio, '.2f')}",
        f"  Median opp score     : {_fmt(cal.median_opportunity_score, '.3f')}",
        f"  Top provider type    : {cal.top_provider_type or 'N/A'}",
        "-" * 60,
        f"  MOIC uplift factor   : {_fmt(cal.moic_uplift_factor, '.4f')}",
        "=" * 60,
    ]
    if cal.errors:
        lines.append(f"  Errors ({len(cal.errors)}): " + "; ".join(cal.errors[:3]))
    return "\n".join(lines) + "\n"
