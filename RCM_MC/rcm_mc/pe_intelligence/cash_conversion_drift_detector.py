"""Cash conversion drift — early-warning on working-capital stress.

Partner statement: "DSO rising three quarters in a row
is a tell. By the time it shows up in EBITDA, we've
missed the QofE window. I want the trendline flagged
before it becomes a number."

Distinct from `cash_conversion.py` (computes point-in-
time cash conversion cycle). This module is **trend-
based** — it catches the *direction* of working-capital
metrics over 4-8 quarters and flags deteriorating ones
before they hit the P&L.

### 6 drift signals

1. **dso_days_trend** — days sales outstanding rising.
2. **dpo_days_trend** — days payable outstanding falling
   (vendors tightening).
3. **inventory_days_trend** — inventory days rising on
   flat or falling revenue.
4. **initial_denial_rate_trend** — front-end or coding
   issues building.
5. **claim_appeal_age_trend** — stuck-in-appeals claims
   stretching.
6. **collections_velocity_trend** — % collected in 90
   days falling.

### Direction conventions

"deteriorating" for each:
- DSO rising
- DPO falling
- Inventory days rising
- Initial denial rate rising
- Appeal age rising
- Collections velocity falling

### Drift-tier ladder

- **clean** — 0 deteriorating signals.
- **noise** — 1 deteriorating signal.
- **early_warning** — 2 deteriorating signals.
- **working_capital_stress** — 3+ deteriorating.

Partner note escalates at 3+: "working-capital stress
building; bring-down QofE period-over-period comparison
at close."

### Trend detection

A series is "deteriorating" if the linear slope over the
last N quarters is in the wrong direction by more than
a configurable threshold (default 1% per quarter for
rates, 1 day/quarter for day metrics).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# Direction of deterioration per signal.
DETERIORATION_DIRECTION: Dict[str, str] = {
    "dso_days": "rising",
    "dpo_days": "falling",
    "inventory_days": "rising",
    "initial_denial_rate": "rising",
    "claim_appeal_age": "rising",
    "collections_velocity": "falling",
}

# Partner-judgment thresholds for "meaningful" trend.
DEFAULT_THRESHOLDS: Dict[str, float] = {
    "dso_days": 1.0,                    # days per quarter
    "dpo_days": 1.0,
    "inventory_days": 1.0,
    "initial_denial_rate": 0.010,       # 1% per quarter
    "claim_appeal_age": 2.0,            # days per quarter
    "collections_velocity": 0.010,
}


@dataclass
class DriftInputs:
    dso_days_series: List[float] = field(default_factory=list)
    dpo_days_series: List[float] = field(default_factory=list)
    inventory_days_series: List[float] = field(default_factory=list)
    initial_denial_rate_series: List[float] = field(default_factory=list)
    claim_appeal_age_series: List[float] = field(default_factory=list)
    collections_velocity_series: List[float] = field(
        default_factory=list
    )


@dataclass
class DriftSignal:
    name: str
    slope_per_quarter: float
    is_deteriorating: bool
    partner_comment: str


@dataclass
class DriftReport:
    tier: str                              # clean / noise / early_warning /
                                            # working_capital_stress
    deteriorating_count: int
    signals: List[DriftSignal] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier,
            "deteriorating_count": self.deteriorating_count,
            "signals": [
                {"name": s.name,
                 "slope_per_quarter": s.slope_per_quarter,
                 "is_deteriorating": s.is_deteriorating,
                 "partner_comment": s.partner_comment}
                for s in self.signals
            ],
            "partner_note": self.partner_note,
        }


def _linear_slope(series: List[float]) -> float:
    """Simple linear regression slope. Uses least squares."""
    n = len(series)
    if n < 2:
        return 0.0
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(series) / n
    num = sum((xs[i] - mean_x) * (series[i] - mean_y)
              for i in range(n))
    den = sum((xs[i] - mean_x) ** 2 for i in range(n))
    if den == 0.0:
        return 0.0
    return num / den


def _signal_direction(name: str, slope: float,
                       threshold: float) -> bool:
    """Return True if the slope indicates deterioration."""
    direction = DETERIORATION_DIRECTION.get(name, "rising")
    if direction == "rising":
        return slope > threshold
    return slope < -threshold


def _comment(name: str, slope: float,
              is_det: bool) -> str:
    dir_word = DETERIORATION_DIRECTION.get(name, "rising")
    if is_det:
        return (
            f"Trending {dir_word} at "
            f"{slope:+.2f}/quarter — deteriorating."
        )
    return (
        f"Trend {slope:+.2f}/quarter — not meaningfully "
        "deteriorating."
    )


def detect_cash_conversion_drift(
    inputs: DriftInputs,
) -> DriftReport:
    signal_series: Dict[str, List[float]] = {
        "dso_days": inputs.dso_days_series,
        "dpo_days": inputs.dpo_days_series,
        "inventory_days": inputs.inventory_days_series,
        "initial_denial_rate":
            inputs.initial_denial_rate_series,
        "claim_appeal_age": inputs.claim_appeal_age_series,
        "collections_velocity":
            inputs.collections_velocity_series,
    }

    signals: List[DriftSignal] = []
    det_count = 0
    for name, series in signal_series.items():
        if not series or len(series) < 3:
            signals.append(DriftSignal(
                name=name,
                slope_per_quarter=0.0,
                is_deteriorating=False,
                partner_comment=(
                    f"Series for {name} has < 3 "
                    "observations; cannot trend."
                ),
            ))
            continue
        slope = _linear_slope(series)
        threshold = DEFAULT_THRESHOLDS.get(name, 1.0)
        is_det = _signal_direction(name, slope, threshold)
        if is_det:
            det_count += 1
        signals.append(DriftSignal(
            name=name,
            slope_per_quarter=round(slope, 4),
            is_deteriorating=is_det,
            partner_comment=_comment(name, slope, is_det),
        ))

    if det_count >= 3:
        tier = "working_capital_stress"
        note = (
            f"{det_count} signals deteriorating — working "
            "capital stress building. Partner: demand "
            "bring-down QofE period-over-period comparison "
            "at close. Stress the covenant package against "
            "this trajectory."
        )
    elif det_count == 2:
        tier = "early_warning"
        note = (
            f"{det_count} signals deteriorating — early "
            "warning. Partner: diligence the two "
            "specifics; verify QofE catches them."
        )
    elif det_count == 1:
        tier = "noise"
        note = (
            "1 signal deteriorating — monitor; may be "
            "noise or early indicator."
        )
    else:
        tier = "clean"
        note = (
            "No deteriorating trends across cash-"
            "conversion signals. Partner: proceed on "
            "current WC assumption."
        )

    return DriftReport(
        tier=tier,
        deteriorating_count=det_count,
        signals=signals,
        partner_note=note,
    )


def render_drift_markdown(r: DriftReport) -> str:
    lines = [
        "# Cash conversion drift",
        "",
        f"**Tier:** `{r.tier}`",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Deteriorating signals: "
        f"{r.deteriorating_count}",
        "",
        "| Signal | Slope / qtr | Deteriorating | "
        "Partner comment |",
        "|---|---|---|---|",
    ]
    for s in r.signals:
        det = "✓" if s.is_deteriorating else "—"
        lines.append(
            f"| {s.name} | {s.slope_per_quarter:+.3f} | "
            f"{det} | {s.partner_comment} |"
        )
    return "\n".join(lines)
