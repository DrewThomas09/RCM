"""Working capital seasonality detector — is the WC drag real or seasonal?

Partner statement: "Healthcare WC has a Q1 deductible
reset spike — patients haven't met deductible yet so
the AR ages faster, DSO climbs, cash drags. By Q3 it
normalizes. If a seller flags 'WC drag' in Q1 and
your model carries that into trailing twelve, you're
double-counting a seasonal swing as structural.
Conversely, if DSO is growing year-over-year SAME-Q
— Q1 2026 vs Q1 2025 — that's not seasonal, that's
real."

Distinct from:
- `working_capital` — point-in-time WC math.
- `working_capital_peer_band` — peer comparison.
- `cash_conversion_drift_detector` — trend detector
  generally.

This module distinguishes **seasonal** WC swings
from **structural** WC drag using YoY same-quarter
comparison.

### Healthcare seasonal patterns

- Q1: deductible reset → DSO +5-15 days (peaks Feb-Mar)
- Q2: normalization
- Q3: low season + summer slowdown
- Q4: year-end Medicare claim push → DSO −3-5 days
  (cleaner)

### Output

- per-quarter `QuarterlyWC` (DSO, AR_days, structural_pct)
- average seasonal swing
- average structural drift YoY
- partner_verdict: seasonal / mixed / structural_drag
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


SEASONAL_BASELINE_DAYS_BY_QUARTER: Dict[int, float] = {
    1: 8.0,    # Q1 deductible-reset spike
    2: 0.0,
    3: -2.0,   # summer slowdown but cleaner cash
    4: -4.0,   # Q4 Medicare claim push
}


@dataclass
class QuarterlyWCObservation:
    year: int
    quarter: int
    dso_days: float


@dataclass
class WCSeasonalityInputs:
    observations: List[QuarterlyWCObservation] = field(
        default_factory=list)
    baseline_dso_days: float = 50.0


@dataclass
class QuarterlyWC:
    year: int
    quarter: int
    dso_days: float
    seasonal_baseline_days: float
    seasonally_adjusted_dso: float
    yoy_same_q_delta_days: Optional[float]


@dataclass
class WCSeasonalityReport:
    quarters: List[QuarterlyWC] = field(default_factory=list)
    avg_seasonal_swing_days: float = 0.0
    avg_yoy_drift_days: float = 0.0
    verdict: str = "seasonal"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quarters": [
                {"year": q.year,
                 "quarter": q.quarter,
                 "dso_days": q.dso_days,
                 "seasonal_baseline_days":
                     q.seasonal_baseline_days,
                 "seasonally_adjusted_dso":
                     q.seasonally_adjusted_dso,
                 "yoy_same_q_delta_days":
                     q.yoy_same_q_delta_days}
                for q in self.quarters
            ],
            "avg_seasonal_swing_days":
                self.avg_seasonal_swing_days,
            "avg_yoy_drift_days":
                self.avg_yoy_drift_days,
            "verdict": self.verdict,
            "partner_note": self.partner_note,
        }


def detect_wc_seasonality(
    inputs: WCSeasonalityInputs,
) -> WCSeasonalityReport:
    if not inputs.observations:
        return WCSeasonalityReport(
            partner_note=(
                "No observations — provide at least 4 "
                "quarters of DSO data."
            ),
        )

    sorted_obs = sorted(
        inputs.observations,
        key=lambda o: (o.year, o.quarter),
    )

    quarters: List[QuarterlyWC] = []
    yoy_lookup: Dict[tuple, float] = {}
    for o in sorted_obs:
        seasonal = SEASONAL_BASELINE_DAYS_BY_QUARTER.get(
            o.quarter, 0.0)
        adjusted = o.dso_days - seasonal
        prev_year_key = (o.year - 1, o.quarter)
        prev_dso = yoy_lookup.get(prev_year_key)
        yoy_delta = (
            o.dso_days - prev_dso
            if prev_dso is not None else None
        )
        quarters.append(QuarterlyWC(
            year=o.year,
            quarter=o.quarter,
            dso_days=round(o.dso_days, 2),
            seasonal_baseline_days=round(seasonal, 2),
            seasonally_adjusted_dso=round(adjusted, 2),
            yoy_same_q_delta_days=(
                round(yoy_delta, 2)
                if yoy_delta is not None else None
            ),
        ))
        yoy_lookup[(o.year, o.quarter)] = o.dso_days

    # Average seasonal swing = max-min of seasonally
    # unadjusted DSO across quarters within the same year
    swings_by_year: Dict[int, List[float]] = {}
    for q in quarters:
        swings_by_year.setdefault(q.year, []).append(
            q.dso_days)
    swings = []
    for yr_dsos in swings_by_year.values():
        if len(yr_dsos) >= 2:
            swings.append(max(yr_dsos) - min(yr_dsos))
    avg_seasonal_swing = (
        sum(swings) / len(swings) if swings else 0.0
    )

    # Average YoY drift = mean of yoy_same_q deltas
    yoy_deltas = [
        q.yoy_same_q_delta_days
        for q in quarters
        if q.yoy_same_q_delta_days is not None
    ]
    avg_yoy_drift = (
        sum(yoy_deltas) / len(yoy_deltas)
        if yoy_deltas else 0.0
    )

    # Verdict logic
    if abs(avg_yoy_drift) < 1.5:
        verdict = "seasonal"
        note = (
            f"WC variation is seasonal: YoY drift "
            f"{avg_yoy_drift:+.1f} days; seasonal "
            f"swing {avg_seasonal_swing:.1f} days. "
            "Don't model the Q1 spike as structural — "
            "it reverses by Q3."
        )
    elif abs(avg_yoy_drift) < 5.0:
        verdict = "mixed"
        note = (
            f"Mixed: YoY drift "
            f"{avg_yoy_drift:+.1f} days suggests some "
            "structural movement on top of the "
            f"{avg_seasonal_swing:.1f}-day seasonal "
            "swing. Diligence the trend on a same-Q "
            "basis."
        )
    elif avg_yoy_drift > 0:
        verdict = "structural_drag"
        note = (
            f"Structural drag: YoY same-Q DSO is "
            f"climbing {avg_yoy_drift:+.1f} days "
            "average. Not seasonal — collections are "
            "deteriorating. Investigate denials, payer "
            "mix shift, or coding issues."
        )
    else:
        verdict = "structural_improvement"
        note = (
            f"Structural improvement: YoY same-Q DSO "
            f"falling {avg_yoy_drift:+.1f} days — real "
            "RCM lift, not seasonal. Counter the "
            "seller's WC story with the trend."
        )

    return WCSeasonalityReport(
        quarters=quarters,
        avg_seasonal_swing_days=round(
            avg_seasonal_swing, 2),
        avg_yoy_drift_days=round(avg_yoy_drift, 2),
        verdict=verdict,
        partner_note=note,
    )


def render_wc_seasonality_markdown(
    r: WCSeasonalityReport,
) -> str:
    lines = [
        "# Working capital seasonality",
        "",
        f"_Verdict: **{r.verdict}**_ — {r.partner_note}",
        "",
        f"- Avg seasonal swing: "
        f"{r.avg_seasonal_swing_days:.1f} days",
        f"- Avg YoY same-Q drift: "
        f"{r.avg_yoy_drift_days:+.1f} days",
        "",
        "| Year/Q | DSO | Seasonal baseline | Adjusted | YoY Δ |",
        "|---|---|---|---|---|",
    ]
    for q in r.quarters:
        yoy = (
            f"{q.yoy_same_q_delta_days:+.1f}"
            if q.yoy_same_q_delta_days is not None
            else "—"
        )
        lines.append(
            f"| Y{q.year}Q{q.quarter} | "
            f"{q.dso_days:.1f} | "
            f"{q.seasonal_baseline_days:+.1f} | "
            f"{q.seasonally_adjusted_dso:.1f} | "
            f"{yoy} |"
        )
    return "\n".join(lines)
