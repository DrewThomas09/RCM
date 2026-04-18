"""CMS payment rate trend monitoring.

Tracks year-over-year payment rate changes for state × provider-type
combinations, computes trend signals, and flags adverse rate environments
that should inform deal stress testing and watchlist logic.

All analytics operate on DataFrames from the CMS analytics pipeline
(fetch_provider_utilization / run_market_analysis).

Public API:
    RateTrendSignal                       dataclass
    compute_rate_trends(dfs_by_year)      -> list[RateTrendSignal]
    adverse_rate_flag(signals)            -> list[dict]
    rate_trend_table(signals)             -> str
    rate_monitor_summary(signals)         -> dict
    apply_rate_stress(benchmarks, signals) -> dict
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RateTrendSignal:
    """Payment rate trend for a provider_type (optionally by state)."""

    provider_type: str
    state: Optional[str] = None

    years: List[int] = field(default_factory=list)
    payment_values: List[float] = field(default_factory=list)

    yoy_changes: List[float] = field(default_factory=list)   # % changes
    cagr: Optional[float] = None
    trend_direction: str = "flat"          # rising / declining / volatile / flat
    adverse_flag: bool = False
    severity: str = "none"                 # none / low / medium / high / critical


# ---------------------------------------------------------------------------
# Trend computation
# ---------------------------------------------------------------------------

def _compute_cagr(values: List[float], years: List[int]) -> Optional[float]:
    if len(values) < 2 or len(years) < 2:
        return None
    n = years[-1] - years[0]
    if n <= 0 or values[0] <= 0:
        return None
    return (values[-1] / values[0]) ** (1.0 / n) - 1.0


def _yoy(values: List[float]) -> List[float]:
    changes = []
    for i in range(1, len(values)):
        if values[i - 1] > 0:
            changes.append((values[i] - values[i - 1]) / values[i - 1])
        else:
            changes.append(0.0)
    return changes


def _classify_trend(yoy: List[float], cagr: Optional[float]) -> tuple[str, bool, str]:
    """Returns (direction, adverse_flag, severity)."""
    if not yoy:
        return "flat", False, "none"

    avg_yoy = sum(yoy) / len(yoy)
    neg_count = sum(1 for y in yoy if y < -0.01)

    if cagr is not None and cagr < -0.05:
        direction = "declining"
        if cagr < -0.15:
            return direction, True, "critical"
        if cagr < -0.08:
            return direction, True, "high"
        return direction, True, "medium"

    if neg_count >= len(yoy) - 1 and len(yoy) >= 2:
        direction = "declining"
        return direction, True, "medium"

    if avg_yoy < -0.01:
        direction = "declining"
        return direction, True, "low"

    if avg_yoy > 0.03:
        return "rising", False, "none"

    # Check volatility
    if len(yoy) >= 2:
        try:
            import statistics
            sd = statistics.stdev(yoy)
            if sd > 0.05:
                return "volatile", False, "low"
        except Exception:
            pass

    return "flat", False, "none"


def compute_rate_trends(
    dfs_by_year: Dict[int, Any],   # year → pd.DataFrame
    state: Optional[str] = None,
    payment_col: str = "_cms_total_payment_mm",
    bene_col: str = "bene_cnt",
) -> List[RateTrendSignal]:
    """Compute rate trend signals for each provider_type across years.

    Parameters
    ----------
    dfs_by_year :
        Dict of {year: DataFrame} from fetch_provider_utilization or run_market_analysis.
    state :
        If given, restrict to this state.
    payment_col, bene_col :
        Column names for payment and beneficiary count.
    """
    import pandas as pd

    # Aggregate: per (year, provider_type) → payment_per_bene
    records: Dict[str, Dict[int, float]] = {}

    for yr, df in sorted(dfs_by_year.items()):
        if df is None or df.empty:
            continue
        if state and "state" in df.columns:
            df = df[df["state"] == state]

        if "provider_type" not in df.columns:
            continue

        pt_col = "provider_type"
        grp = df.groupby(pt_col)

        for pt, sub in grp:
            pt_str = str(pt)
            # Compute payment per bene as proxy for rate
            pmt = pd.to_numeric(sub.get(payment_col, pd.Series(dtype=float)), errors="coerce")
            bene = pd.to_numeric(sub.get(bene_col, pd.Series(dtype=float)), errors="coerce")
            tot_pmt = float(pmt.sum(skipna=True))
            tot_bene = float(bene.sum(skipna=True))

            if tot_bene > 0:
                ppb = tot_pmt / tot_bene * 1_000_000  # convert mm → per bene
            elif tot_pmt > 0:
                ppb = tot_pmt
            else:
                continue

            records.setdefault(pt_str, {})[int(yr)] = ppb

    signals = []
    for pt, yr_vals in records.items():
        if len(yr_vals) < 2:
            continue
        years_sorted = sorted(yr_vals.keys())
        vals = [yr_vals[y] for y in years_sorted]

        yoy = _yoy(vals)
        cagr = _compute_cagr(vals, years_sorted)
        direction, adverse, severity = _classify_trend(yoy, cagr)

        signals.append(RateTrendSignal(
            provider_type=pt,
            state=state,
            years=years_sorted,
            payment_values=[round(v, 2) for v in vals],
            yoy_changes=[round(y, 4) for y in yoy],
            cagr=round(cagr, 4) if cagr is not None else None,
            trend_direction=direction,
            adverse_flag=adverse,
            severity=severity,
        ))

    signals.sort(key=lambda s: s.cagr or 0)
    return signals


# ---------------------------------------------------------------------------
# Adverse rate flags
# ---------------------------------------------------------------------------

def adverse_rate_flag(signals: List[RateTrendSignal]) -> List[Dict[str, Any]]:
    """Return list of dicts for signals with adverse_flag=True."""
    result = []
    for sig in signals:
        if sig.adverse_flag:
            result.append({
                "provider_type": sig.provider_type,
                "state": sig.state,
                "cagr": sig.cagr,
                "trend_direction": sig.trend_direction,
                "severity": sig.severity,
                "detail": (
                    f"Payment rate declining {sig.cagr:.1%} CAGR"
                    if sig.cagr else f"Adverse trend: {sig.trend_direction}"
                ),
            })
    return result


# ---------------------------------------------------------------------------
# Apply rate stress to benchmarks
# ---------------------------------------------------------------------------

def apply_rate_stress(
    benchmarks: Dict[str, Any],
    signals: List[RateTrendSignal],
    provider_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Adjust benchmark MOICs downward for adverse rate environments.

    If provider_type given, uses that signal; otherwise uses worst signal.
    Stress applied to moic_p25/p50/p75.
    """
    relevant = [s for s in signals if s.adverse_flag]
    if provider_type:
        relevant = [s for s in relevant if s.provider_type == provider_type] or relevant

    if not relevant:
        return dict(benchmarks)

    worst = sorted(relevant, key=lambda s: (s.cagr or 0))[0]
    cagr = worst.cagr or -0.05

    _SEVERITY_HAIRCUT = {
        "critical": 0.25,
        "high": 0.15,
        "medium": 0.08,
        "low": 0.04,
        "none": 0.0,
    }
    haircut = _SEVERITY_HAIRCUT.get(worst.severity, 0.0)

    out = dict(benchmarks)
    for key in ("moic_p25", "moic_p50", "moic_p75", "moic_mean"):
        if key in out and out[key] is not None:
            try:
                out[key] = round(float(out[key]) * (1 - haircut), 3)
            except (TypeError, ValueError):
                pass
    out["rate_stress_applied"] = True
    out["rate_stress_severity"] = worst.severity
    out["rate_stress_haircut"] = haircut
    out["rate_stress_provider_type"] = worst.provider_type
    return out


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def rate_trend_table(signals: List[RateTrendSignal]) -> str:
    """Formatted rate trend table."""
    if not signals:
        return "No rate trend data available.\n"

    lines = [
        "CMS Payment Rate Trends",
        "=" * 72,
        f"{'Provider Type':<28} {'CAGR':>8} {'Direction':<14} {'Severity':<10} {'Adverse':<8}",
        "-" * 72,
    ]
    for sig in signals:
        cagr_s = f"{sig.cagr:.1%}" if sig.cagr is not None else "N/A"
        adv_s = "YES" if sig.adverse_flag else "—"
        lines.append(
            f"{sig.provider_type:<28} {cagr_s:>8} {sig.trend_direction:<14} "
            f"{sig.severity:<10} {adv_s:<8}"
        )
    lines.append("=" * 72)
    return "\n".join(lines) + "\n"


def rate_monitor_summary(signals: List[RateTrendSignal]) -> Dict[str, Any]:
    """Machine-readable summary of rate trends."""
    adverse = [s for s in signals if s.adverse_flag]
    critical = [s for s in signals if s.severity == "critical"]
    cagrs = [s.cagr for s in signals if s.cagr is not None]

    return {
        "total_provider_types": len(signals),
        "adverse_count": len(adverse),
        "critical_count": len(critical),
        "rising_count": sum(1 for s in signals if s.trend_direction == "rising"),
        "declining_count": sum(1 for s in signals if s.trend_direction == "declining"),
        "median_cagr": sorted(cagrs)[len(cagrs) // 2] if cagrs else None,
        "worst_provider": signals[0].provider_type if signals else None,
        "worst_cagr": signals[0].cagr if signals else None,
    }
