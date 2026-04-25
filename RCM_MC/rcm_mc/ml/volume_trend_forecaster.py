"""Service-line volume trend forecaster + trajectory classifier.

The existing ``temporal_forecaster.py`` is generic — it forecasts
any per-metric series (denial rate, AR days, etc.) with auto-
selected method (linear / Holt-Winters / weighted-recent). This
module reuses that engine for the **service-line volume** use
case and adds:

  • Multi-line forecasting in one call (Surgery + ED + OB + ...).
  • Trajectory classification: rapid_growth / growth / stable /
    decline / rapid_decline using projected CAGR over the
    forecast horizon.
  • IP→OP migration detection: when inpatient declines and the
    matching outpatient line grows in lock-step, flag the shift
    rather than calling the IP line 'declining' in isolation.
  • Hospital-wide trajectory: aggregate trajectory + variance
    decomposition (which lines are driving the overall picture).

This is the canonical 'where is volume going?' answer the
partner needs to size the value-creation thesis. Surgery growing
+10%/yr supports a roll-up; flat ED + 7% growth in observation
units says the IP→OP shift is finally happening.

Public API::

    from rcm_mc.ml.volume_trend_forecaster import (
        ServiceLineVolumeForecast,
        HospitalTrajectoryReport,
        forecast_service_line_volumes,
        classify_trajectories,
        detect_ip_op_migration,
    )
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .temporal_forecaster import (
    TemporalForecast,
    forecast_metric,
)

logger = logging.getLogger(__name__)


# Trajectory-band thresholds on annualized CAGR (decimal) over
# the forecast horizon. A 5%/yr decline is a different conversation
# than a 1%/yr decline — partner needs the magnitude.
TRAJECTORY_BANDS: List[Tuple[float, str]] = [
    (-0.05, "rapid_decline"),
    (-0.01, "decline"),
    (0.01, "stable"),
    (0.05, "growth"),
    (1e9, "rapid_growth"),
]


# IP→OP migration pairs — when an inpatient line declines and the
# matching outpatient line grows in lock-step, the partner reads
# this differently than a true demand decline.
IP_OP_PAIRS: List[Tuple[str, str]] = [
    ("Inpatient Routine", "Outpatient Clinic"),
    ("Surgery", "Outpatient Surgery"),
    ("Cardiology IP", "Cardiology OP"),
    ("ED Admit", "Observation"),
]


@dataclass
class ServiceLineVolumeForecast:
    """One service line's volume forecast + trajectory."""
    service_line: str
    historical: List[Tuple[str, float]]
    forecasted: List[Tuple[str, float, float, float]]
    method: str               # 'linear' / 'holt_winters' / 'weighted_recent'
    trajectory: str           # 'rapid_growth' / 'growth' / 'stable' / ...
    projected_cagr: Optional[float]   # decimal, e.g. 0.05 = 5%/yr
    n_periods_history: int
    seasonality_detected: bool
    confidence_band_pct: float = 0.0  # avg width of CI / forecast

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_line": self.service_line,
            "historical": [
                [lbl, v] for lbl, v in self.historical],
            "forecasted": [
                [lbl, v, lo, hi]
                for lbl, v, lo, hi in self.forecasted],
            "method": self.method,
            "trajectory": self.trajectory,
            "projected_cagr": self.projected_cagr,
            "n_periods_history": self.n_periods_history,
            "seasonality_detected": (
                self.seasonality_detected),
            "confidence_band_pct": self.confidence_band_pct,
        }


@dataclass
class IPOPMigrationFlag:
    """One IP→OP shift detected."""
    inpatient_line: str
    outpatient_line: str
    inpatient_cagr: float
    outpatient_cagr: float
    migration_strength: float  # |outpatient_cagr - inpatient_cagr|


@dataclass
class HospitalTrajectoryReport:
    """Hospital-wide aggregated trajectory."""
    ccn: Optional[str]
    per_line: List[ServiceLineVolumeForecast]
    overall_trajectory: str
    overall_cagr: float
    growing_lines: List[str]
    declining_lines: List[str]
    stable_lines: List[str]
    migration_flags: List[IPOPMigrationFlag] = field(
        default_factory=list)
    notes: List[str] = field(default_factory=list)


# ── Helpers ───────────────────────────────────────────────────

def _classify_trajectory(cagr: Optional[float]) -> str:
    if cagr is None or not math.isfinite(cagr):
        return "stable"
    for thresh, label in TRAJECTORY_BANDS:
        if cagr < thresh:
            return label
    return TRAJECTORY_BANDS[-1][1]


def _annualized_cagr(
    historical: List[Tuple[str, float]],
    forecasted: List[Tuple[str, float, float, float]],
    *,
    period: int = 4,
) -> Optional[float]:
    """CAGR from last historical point to last forecasted point.

    period: number of periods per year (4 for quarterly, 12 for
    monthly). Defaults to quarterly per the existing forecaster.
    """
    if not historical or not forecasted:
        return None
    start = historical[-1][1]
    end = forecasted[-1][1]
    n_periods = len(forecasted)
    years = n_periods / period
    if start <= 0 or years <= 0:
        return None
    return (end / start) ** (1.0 / years) - 1.0


def _ci_band_pct(
    forecasted: List[Tuple[str, float, float, float]],
) -> float:
    """Average CI width as a share of the forecasted value."""
    if not forecasted:
        return 0.0
    widths = []
    for _, val, lo, hi in forecasted:
        if val and val != 0:
            widths.append(abs(hi - lo) / abs(val))
    if not widths:
        return 0.0
    return round(sum(widths) / len(widths), 4)


# ── Forecasting ──────────────────────────────────────────────

def forecast_service_line_volumes(
    history_by_line: Dict[
        str, Sequence[Tuple[str, float]]],
    *,
    n_forward: int = 4,
    period: int = 4,
) -> List[ServiceLineVolumeForecast]:
    """Run the temporal forecaster on each service line's
    history and classify the trajectory.

    Args:
      history_by_line: dict of service_line → sequence of
        (period_label, volume) tuples in chronological order.
      n_forward: number of periods to forecast (default 4 quarters
        = 1 year).
      period: periods-per-year (4 for quarterly, 12 for monthly).

    Returns: list of ServiceLineVolumeForecast, one per line.
    """
    results: List[ServiceLineVolumeForecast] = []
    for line, history in (history_by_line or {}).items():
        try:
            tf: TemporalForecast = forecast_metric(
                str(line), history,
                n_forward=n_forward, period=period)
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "forecast for %s failed: %s", line, exc)
            continue
        cagr = _annualized_cagr(
            tf.historical, tf.forecasted, period=period)
        trajectory = _classify_trajectory(cagr)
        results.append(ServiceLineVolumeForecast(
            service_line=str(line),
            historical=list(tf.historical),
            forecasted=list(tf.forecasted),
            method=tf.method,
            trajectory=trajectory,
            projected_cagr=(round(cagr, 4)
                            if cagr is not None
                            else None),
            n_periods_history=len(tf.historical),
            seasonality_detected=tf.seasonality_detected,
            confidence_band_pct=_ci_band_pct(tf.forecasted),
        ))
    # Sort by projected CAGR descending (growing → declining)
    def _sort_key(r: ServiceLineVolumeForecast) -> float:
        return -(r.projected_cagr or 0.0)
    results.sort(key=_sort_key)
    return results


def classify_trajectories(
    forecasts: List[ServiceLineVolumeForecast],
) -> Tuple[List[str], List[str], List[str]]:
    """Split forecasts into growing / stable / declining."""
    growing: List[str] = []
    declining: List[str] = []
    stable: List[str] = []
    for f in forecasts:
        if f.trajectory in ("growth", "rapid_growth"):
            growing.append(f.service_line)
        elif f.trajectory in ("decline", "rapid_decline"):
            declining.append(f.service_line)
        else:
            stable.append(f.service_line)
    return growing, stable, declining


def detect_ip_op_migration(
    forecasts: List[ServiceLineVolumeForecast],
    *,
    pairs: Optional[List[Tuple[str, str]]] = None,
    min_migration_strength: float = 0.06,
) -> List[IPOPMigrationFlag]:
    """Find IP lines declining while their OP counterpart grows.

    Args:
      forecasts: per-line forecasts.
      pairs: override IP_OP_PAIRS for custom taxonomy.
      min_migration_strength: minimum |op_cagr - ip_cagr| to count
        as migration. 6%/yr default — partner cares when the
        spread is non-trivial.
    """
    pairs_to_check = pairs or IP_OP_PAIRS
    by_line = {f.service_line: f for f in forecasts}
    out: List[IPOPMigrationFlag] = []
    for ip_line, op_line in pairs_to_check:
        ip = by_line.get(ip_line)
        op = by_line.get(op_line)
        if (ip is None or op is None
                or ip.projected_cagr is None
                or op.projected_cagr is None):
            continue
        if (ip.projected_cagr < 0
                and op.projected_cagr > 0):
            strength = (op.projected_cagr
                        - ip.projected_cagr)
            if strength >= min_migration_strength:
                out.append(IPOPMigrationFlag(
                    inpatient_line=ip_line,
                    outpatient_line=op_line,
                    inpatient_cagr=ip.projected_cagr,
                    outpatient_cagr=op.projected_cagr,
                    migration_strength=round(strength, 4),
                ))
    out.sort(key=lambda m: -m.migration_strength)
    return out


def build_hospital_trajectory_report(
    history_by_line: Dict[
        str, Sequence[Tuple[str, float]]],
    *,
    ccn: Optional[str] = None,
    n_forward: int = 4,
    period: int = 4,
) -> HospitalTrajectoryReport:
    """One-call composer: forecast all lines + classify + detect
    migrations + build hospital-wide trajectory.

    Hospital overall_cagr is the volume-weighted average of per-
    line CAGRs (weighted by last-period historical volume), so
    a small high-growth specialty line doesn't overwhelm the
    headline number.
    """
    forecasts = forecast_service_line_volumes(
        history_by_line,
        n_forward=n_forward, period=period)
    growing, stable, declining = classify_trajectories(
        forecasts)
    migrations = detect_ip_op_migration(forecasts)

    # Hospital overall CAGR: volume-weighted average of per-line
    total_volume = 0.0
    weighted_cagr = 0.0
    for f in forecasts:
        if (f.projected_cagr is None
                or not f.historical):
            continue
        last_vol = f.historical[-1][1]
        if last_vol <= 0:
            continue
        total_volume += last_vol
        weighted_cagr += last_vol * f.projected_cagr
    overall_cagr = (weighted_cagr / total_volume
                    if total_volume > 0 else 0.0)
    overall_trajectory = _classify_trajectory(overall_cagr)

    notes: List[str] = []
    if migrations:
        for m in migrations[:3]:
            notes.append(
                f"IP→OP migration: {m.inpatient_line} "
                f"declining {m.inpatient_cagr:+.1%}/yr while "
                f"{m.outpatient_line} grows "
                f"{m.outpatient_cagr:+.1%}/yr — "
                f"site-of-service shift, not true demand "
                f"loss.")
    if (overall_trajectory == "rapid_decline"
            and not migrations):
        notes.append(
            f"Overall volume declining "
            f"{overall_cagr:+.1%}/yr with no IP→OP "
            f"migration explanation — likely catchment-area "
            f"or competitive-position issue.")
    if overall_trajectory in ("growth", "rapid_growth"):
        notes.append(
            f"Hospital volume growing {overall_cagr:+.1%}/yr — "
            f"supports growth thesis if margin holds.")
    n_thin = sum(1 for f in forecasts
                 if f.n_periods_history < 6)
    if n_thin > 0:
        notes.append(
            f"{n_thin} service lines have <6 periods of "
            f"history — forecasts on those use weighted-recent "
            f"and should be treated as best-current-estimate, "
            f"not true forecasts.")

    return HospitalTrajectoryReport(
        ccn=ccn,
        per_line=forecasts,
        overall_trajectory=overall_trajectory,
        overall_cagr=round(overall_cagr, 4),
        growing_lines=growing,
        declining_lines=declining,
        stable_lines=stable,
        migration_flags=migrations,
        notes=notes,
    )
