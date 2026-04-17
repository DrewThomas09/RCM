"""CMS payment trend forecaster — extrapolates historical rate trends for underwriting.

Uses CMS payment time-series data to project future reimbursement rates
for a given provider type and state. Integrates with deal underwriting to
stress-test EBITDA under adverse reimbursement scenarios.

Logic ported and cleaned from DrewThomas09/cms_medicare:
  - yearly_trends() aggregation approach
  - provider_volatility() standard deviation method
  - Extended with: CAGR extrapolation, deal-level stress application,
    and text forecasting reports

Public API:
    RateForecast                        dataclass
    compute_rate_forecast(trends_df, provider_type, state, years)  -> RateForecast
    apply_forecast_to_deal(deal, forecast)                         -> dict
    build_rate_forecast_table(trends_df, years, top_n)             -> str
    forecast_summary(forecasts)                                    -> dict
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RateForecast:
    """Forward rate projection for a provider type / state combination."""
    provider_type: str
    state: Optional[str]
    historical_cagr: Optional[float]       # observed payment CAGR over data window
    volatility: Optional[float]            # std dev of YoY changes
    years_of_data: int
    base_payment: Optional[float]          # most recent year payment per bene
    # Projections
    forecast_years: int = 3
    projected_cagr: Optional[float] = None      # blended: historical × regime adjustment
    base_case_payment: Optional[float] = None   # base payment * (1+cagr)^years
    bear_case_payment: Optional[float] = None   # apply -1.5 std dev shock
    bull_case_payment: Optional[float] = None   # apply +1.0 std dev uplift
    # Meta
    regime: str = "unknown"
    confidence: str = "low"    # low / medium / high (based on data window)
    warnings: List[str] = field(default_factory=list)


def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _cagr(start: float, end: float, years: float) -> Optional[float]:
    if years <= 0 or start <= 0:
        return None
    try:
        return (end / start) ** (1 / years) - 1.0
    except (ZeroDivisionError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Core forecast computation (works on pandas DataFrames from CMS API)
# ---------------------------------------------------------------------------

def compute_rate_forecast(
    trends_df: Any,    # pandas DataFrame — optional import
    provider_type: str,
    state: Optional[str] = None,
    forecast_years: int = 3,
) -> RateForecast:
    """Compute a forward rate forecast for a provider type.

    Args:
        trends_df:     DataFrame with columns: year, provider_type, [state],
                       total_medicare_payment_amt, total_unique_benes
        provider_type: Provider type to forecast (e.g., "Cardiology")
        state:         Optional two-letter state filter
        forecast_years: How many years forward to project

    Returns:
        RateForecast with base/bear/bull projections
    """
    warnings_list: List[str] = []

    try:
        import pandas as pd
        import numpy as np
    except ImportError:
        return RateForecast(
            provider_type=provider_type,
            state=state,
            historical_cagr=None,
            volatility=None,
            years_of_data=0,
            base_payment=None,
            forecast_years=forecast_years,
            warnings=["pandas/numpy not available"],
        )

    if trends_df is None or (hasattr(trends_df, 'empty') and trends_df.empty):
        return RateForecast(
            provider_type=provider_type,
            state=state,
            historical_cagr=None,
            volatility=None,
            years_of_data=0,
            base_payment=None,
            forecast_years=forecast_years,
            warnings=["No trend data provided"],
        )

    df = trends_df.copy()

    # Filter by provider type
    if "provider_type" in df.columns:
        df = df[df["provider_type"].str.lower() == provider_type.lower()]

    # Filter by state if provided
    if state and "state" in df.columns:
        df = df[df["state"].str.upper() == state.upper()]

    # Find payment and bene columns
    pay_col = None
    for c in ["total_medicare_payment_amt", "tot_mdcr_pymt_amt", "_cms_total_payment_mm"]:
        if c in df.columns:
            pay_col = c
            break

    bene_col = None
    for c in ["total_unique_benes", "tot_benes", "bene_cnt"]:
        if c in df.columns:
            bene_col = c
            break

    year_col = "year" if "year" in df.columns else None

    if pay_col is None or year_col is None or df.empty:
        return RateForecast(
            provider_type=provider_type,
            state=state,
            historical_cagr=None,
            volatility=None,
            years_of_data=0,
            base_payment=None,
            forecast_years=forecast_years,
            warnings=["Required columns missing in trends data"],
        )

    # Convert to numeric
    df[pay_col] = pd.to_numeric(df[pay_col], errors="coerce")
    df[year_col] = pd.to_numeric(df[year_col], errors="coerce")
    if bene_col:
        df[bene_col] = pd.to_numeric(df[bene_col], errors="coerce")

    df = df.dropna(subset=[year_col, pay_col]).sort_values(year_col)

    if len(df) < 2:
        return RateForecast(
            provider_type=provider_type,
            state=state,
            historical_cagr=None,
            volatility=None,
            years_of_data=len(df),
            base_payment=None,
            forecast_years=forecast_years,
            warnings=["Insufficient data (< 2 years)"],
        )

    # Aggregate by year (sum)
    if state and "state" in df.columns:
        group_cols = [year_col]
    else:
        group_cols = [year_col]

    agg_cols = [pay_col]
    if bene_col and bene_col in df.columns:
        agg_cols.append(bene_col)

    annual = df.groupby(group_cols)[agg_cols].sum().reset_index().sort_values(year_col)

    # Payment per bene if available
    if bene_col and bene_col in annual.columns:
        annual["payment_per_bene"] = annual[pay_col] / annual[bene_col].replace(0, np.nan)
        metric_col = "payment_per_bene"
    else:
        metric_col = pay_col

    vals = annual[metric_col].dropna().values
    years_arr = annual[year_col].dropna().values
    n = len(vals)

    if n < 2:
        return RateForecast(
            provider_type=provider_type,
            state=state,
            historical_cagr=None,
            volatility=None,
            years_of_data=n,
            base_payment=None,
            forecast_years=forecast_years,
            warnings=["Insufficient usable data points"],
        )

    # CAGR over full window
    year_span = float(years_arr[-1] - years_arr[0]) or 1.0
    hist_cagr = _cagr(float(vals[0]), float(vals[-1]), year_span)

    # YoY changes for volatility
    yoy = [((vals[i] / vals[i-1]) - 1.0) for i in range(1, n) if vals[i-1] > 0]
    volatility = float(np.std(yoy)) if len(yoy) >= 2 else None

    base_payment = float(vals[-1])

    # Confidence
    if n >= 5:
        confidence = "high"
    elif n >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    # Regime from CAGR + volatility
    if hist_cagr is not None and volatility is not None:
        if hist_cagr >= 0.05 and volatility < 0.10:
            regime = "durable_growth"
        elif hist_cagr >= 0.05 and volatility >= 0.10:
            regime = "emerging_volatile"
        elif hist_cagr < 0.0 and volatility > 0.10:
            regime = "declining_risk"
        elif hist_cagr < 0.01:
            regime = "stagnant"
        else:
            regime = "steady_compounders"
    else:
        regime = "unknown"

    # Projected CAGR: blend historical with mild mean reversion toward 2%
    mean_reversion_target = 0.02
    blend_weight = 0.7  # 70% historical, 30% mean reversion
    if hist_cagr is not None:
        projected_cagr = blend_weight * hist_cagr + (1 - blend_weight) * mean_reversion_target
    else:
        projected_cagr = mean_reversion_target
        warnings_list.append("Using default 2% CAGR (no historical data)")

    # Projections
    base_case = base_payment * ((1 + projected_cagr) ** forecast_years)
    vol_shock = volatility or 0.05
    bear_case = base_payment * ((1 + projected_cagr - 1.5 * vol_shock) ** forecast_years)
    bull_case = base_payment * ((1 + projected_cagr + 1.0 * vol_shock) ** forecast_years)

    if bear_case < 0:
        bear_case = base_payment * 0.7
        warnings_list.append("Bear case floored at 30% haircut from current payment")

    return RateForecast(
        provider_type=provider_type,
        state=state,
        historical_cagr=round(hist_cagr, 4) if hist_cagr is not None else None,
        volatility=round(volatility, 4) if volatility is not None else None,
        years_of_data=n,
        base_payment=round(base_payment, 2),
        forecast_years=forecast_years,
        projected_cagr=round(projected_cagr, 4),
        base_case_payment=round(base_case, 2),
        bear_case_payment=round(bear_case, 2),
        bull_case_payment=round(bull_case, 2),
        regime=regime,
        confidence=confidence,
        warnings=warnings_list,
    )


def apply_forecast_to_deal(deal: Dict[str, Any], forecast: RateForecast) -> Dict[str, Any]:
    """Stress-test a deal's EBITDA under bear/base/bull rate scenarios.

    Applies the payment rate delta as a proportional EBITDA haircut,
    weighted by Medicare/Medicaid exposure in the payer mix.

    Returns a dict with base/bear/bull EBITDA and implied MOIC adjustments.
    """
    import json

    ebitda = _safe_float(deal.get("ebitda_mm") or deal.get("ebitda_at_entry_mm"))
    moic = _safe_float(deal.get("realized_moic"))
    ev = _safe_float(deal.get("ev_mm"))
    ev_ebitda = _safe_float(deal.get("ev_ebitda"))

    # Get government payer exposure
    pm = deal.get("payer_mix")
    if isinstance(pm, str):
        try:
            pm = json.loads(pm)
        except Exception:
            pm = {}
    if not isinstance(pm, dict):
        pm = {}
    medicare = float(pm.get("medicare", 0) or 0)
    medicaid = float(pm.get("medicaid", 0) or 0)
    govt_exposure = medicare + medicaid

    result: Dict[str, Any] = {
        "source_id": deal.get("source_id"),
        "deal_name": deal.get("deal_name"),
        "provider_type": forecast.provider_type,
        "govt_exposure": govt_exposure,
        "forecast_regime": forecast.regime,
        "forecast_confidence": forecast.confidence,
    }

    if ebitda is None or forecast.base_payment is None or forecast.base_payment == 0:
        result["note"] = "Insufficient data for EBITDA stress"
        return result

    # Rate delta as fraction of current payment
    base_delta = (forecast.base_case_payment / forecast.base_payment - 1.0) if forecast.base_case_payment else 0.0
    bear_delta = (forecast.bear_case_payment / forecast.base_payment - 1.0) if forecast.bear_case_payment else -0.15
    bull_delta = (forecast.bull_case_payment / forecast.base_payment - 1.0) if forecast.bull_case_payment else 0.10

    # Apply to EBITDA proportionally by govt exposure
    def apply_delta(delta: float) -> Optional[float]:
        ebitda_impact = ebitda * govt_exposure * delta
        return round(ebitda + ebitda_impact, 1)

    ebitda_base = apply_delta(base_delta)
    ebitda_bear = apply_delta(bear_delta)
    ebitda_bull = apply_delta(bull_delta)

    result.update({
        "ebitda_entry_mm": ebitda,
        "ebitda_base_case_mm": ebitda_base,
        "ebitda_bear_case_mm": ebitda_bear,
        "ebitda_bull_case_mm": ebitda_bull,
        "implied_ev_ebitda_base": round(ev / ebitda_base, 1) if ev and ebitda_base and ebitda_base > 0 else None,
        "implied_ev_ebitda_bear": round(ev / ebitda_bear, 1) if ev and ebitda_bear and ebitda_bear > 0 else None,
        "rate_bear_impact_pct": round(bear_delta * govt_exposure * 100, 1),
    })

    return result


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def build_rate_forecast_table(
    trends_df: Any,
    forecast_years: int = 3,
    top_n: int = 15,
    state: Optional[str] = None,
) -> str:
    """Build a table of rate forecasts across top provider types."""
    try:
        import pandas as pd
    except ImportError:
        return "pandas required for rate forecast table"

    if trends_df is None or (hasattr(trends_df, 'empty') and trends_df.empty):
        return "No trend data provided"

    # Get unique provider types
    if "provider_type" not in trends_df.columns:
        return "provider_type column not found"

    provider_types = trends_df["provider_type"].dropna().unique().tolist()[:top_n]

    lines = [
        f"{'Provider Type':<35} {'Hist CAGR':>10} {'Vol':>6} {'Base':>10} {'Bear':>10} {'Regime':<20} Conf",
        "-" * 100,
    ]

    for pt in provider_types:
        fc = compute_rate_forecast(trends_df, pt, state=state, forecast_years=forecast_years)
        cagr_s = f"{fc.historical_cagr:.1%}" if fc.historical_cagr is not None else "  —  "
        vol_s = f"{fc.volatility:.1%}" if fc.volatility is not None else "  —"
        base_s = f"${fc.base_case_payment:,.0f}" if fc.base_case_payment is not None else "   —  "
        bear_s = f"${fc.bear_case_payment:,.0f}" if fc.bear_case_payment is not None else "   —  "
        lines.append(
            f"{pt[:34]:<35} {cagr_s:>10} {vol_s:>6} {base_s:>10} {bear_s:>10} {fc.regime:<20} {fc.confidence}"
        )

    return "\n".join(lines) + "\n"


def forecast_summary(forecasts: List[RateForecast]) -> Dict[str, Any]:
    """Aggregate summary across multiple rate forecasts."""
    if not forecasts:
        return {"count": 0}

    cagrs = [f.historical_cagr for f in forecasts if f.historical_cagr is not None]
    vols = [f.volatility for f in forecasts if f.volatility is not None]
    regimes = {}
    for f in forecasts:
        regimes[f.regime] = regimes.get(f.regime, 0) + 1

    def _median(vals):
        if not vals:
            return None
        s = sorted(vals)
        return round(s[len(s) // 2], 4)

    return {
        "count": len(forecasts),
        "median_historical_cagr": _median(cagrs),
        "median_volatility": _median(vols),
        "regime_distribution": regimes,
        "high_confidence_count": sum(1 for f in forecasts if f.confidence == "high"),
        "adverse_trend_count": sum(1 for f in forecasts
                                   if f.historical_cagr is not None and f.historical_cagr < -0.02),
    }
