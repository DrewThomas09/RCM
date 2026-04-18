"""Management forecast reliability — track record of hitting numbers.

Partner reflex: "Before I believe this forecast, show me the last
four forecasts you made." The ratio of actual-to-forecast is
one of the most predictive partner signals.

A CEO who has delivered 95-105% of forecast for 4 consecutive
years has earned the base case. A CEO who has delivered 70-85%
has been sandbagging the board or over-promising sales; either
way, haircut the current forecast by the historical miss rate.

This module takes prior-year forecasts vs actuals and returns:

- Per-year variance + directional bias (beat / miss / at-plan).
- Reliability score 0-100.
- Recommended haircut to apply to the current forecast.
- Partner note naming the pattern.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class YearVariance:
    year: int
    forecast_ebitda_m: float
    actual_ebitda_m: float
    variance_pct: float                       # (actual - forecast) / forecast
    status: str                               # "beat" / "miss" / "at_plan"


@dataclass
class ReliabilityReport:
    years: List[YearVariance] = field(default_factory=list)
    avg_variance_pct: float = 0.0
    hit_rate_pct: float = 0.0                 # % of years within ±5%
    beat_rate_pct: float = 0.0                # % of years > +5%
    miss_rate_pct: float = 0.0                # % of years < -5%
    reliability_score_0_100: int = 50
    recommended_haircut_pct: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "years": [
                {"year": y.year,
                 "forecast_ebitda_m": y.forecast_ebitda_m,
                 "actual_ebitda_m": y.actual_ebitda_m,
                 "variance_pct": y.variance_pct,
                 "status": y.status}
                for y in self.years
            ],
            "avg_variance_pct": self.avg_variance_pct,
            "hit_rate_pct": self.hit_rate_pct,
            "beat_rate_pct": self.beat_rate_pct,
            "miss_rate_pct": self.miss_rate_pct,
            "reliability_score_0_100": self.reliability_score_0_100,
            "recommended_haircut_pct": self.recommended_haircut_pct,
            "partner_note": self.partner_note,
        }


def _status(variance: float) -> str:
    if variance > 0.05:
        return "beat"
    if variance < -0.05:
        return "miss"
    return "at_plan"


def analyze_forecasts(
    pairs: List[Tuple[int, float, float]],
) -> ReliabilityReport:
    """pairs = [(year, forecast_m, actual_m), ...]"""
    years: List[YearVariance] = []
    for yr, fc, act in sorted(pairs, key=lambda p: p[0]):
        variance = (act - fc) / max(0.01, fc)
        years.append(YearVariance(
            year=yr,
            forecast_ebitda_m=round(fc, 2),
            actual_ebitda_m=round(act, 2),
            variance_pct=round(variance, 4),
            status=_status(variance),
        ))

    if not years:
        return ReliabilityReport(partner_note=("No forecast history "
                                                 "provided."))
    avg_var = sum(y.variance_pct for y in years) / len(years)
    hit = sum(1 for y in years if y.status == "at_plan")
    beat = sum(1 for y in years if y.status == "beat")
    miss = sum(1 for y in years if y.status == "miss")
    hit_rate = hit / len(years)
    beat_rate = beat / len(years)
    miss_rate = miss / len(years)

    # Reliability scoring. Start at 50.
    # +15 per at-plan; +10 per beat (but decay if constant beats);
    # -20 per miss.
    score = 50
    score += 15 * hit
    score += 10 * beat
    score -= 20 * miss

    # Penalize high-variance patterns (unreliable both ways).
    variance_range = (max(y.variance_pct for y in years)
                       - min(y.variance_pct for y in years))
    if variance_range > 0.40:
        score -= 10

    # Constant-miss pattern.
    consecutive_misses = 0
    max_streak = 0
    for y in years:
        if y.status == "miss":
            consecutive_misses += 1
            max_streak = max(max_streak, consecutive_misses)
        else:
            consecutive_misses = 0
    if max_streak >= 3:
        score -= 15

    score = max(0, min(100, score))

    # Recommended haircut: miss-weighted average of misses only.
    miss_variances = [y.variance_pct for y in years
                       if y.status == "miss"]
    if miss_variances:
        avg_miss = sum(miss_variances) / len(miss_variances)
        haircut = min(0.25, abs(avg_miss) * miss_rate + 0.02)
    elif beat_rate >= 0.75:
        haircut = 0.0
    else:
        haircut = 0.05

    # Partner note.
    if miss_rate >= 0.50:
        note = (f"Management has missed {miss_rate*100:.0f}% of "
                f"forecasts — avg variance {avg_var*100:+.1f}%. "
                "Haircut current forecast by "
                f"{haircut*100:.0f}%; do NOT underwrite to their "
                "base case.")
    elif beat_rate >= 0.75 and miss == 0:
        note = (f"Management consistently beats forecast — avg "
                f"variance {avg_var*100:+.1f}%. Either sandbagging "
                "(good buyer signal) or genuinely under-promising. "
                "Underwrite at forecast; upside is real but don't "
                "pay for it.")
    elif hit_rate >= 0.60:
        note = (f"Reliable forecaster — {hit_rate*100:.0f}% at-"
                f"plan delivery. Base case is believable.")
    elif beat_rate >= 0.50 and miss_rate >= 0.25:
        note = (f"Inconsistent — beats ({beat_rate*100:.0f}%) and "
                f"misses ({miss_rate*100:.0f}%) mixed. Underwrite "
                "the median; don't chase the best year.")
    else:
        note = (f"Mixed track record. Reliability score {score}/100. "
                f"Apply {haircut*100:.0f}% haircut to current forecast.")

    return ReliabilityReport(
        years=years,
        avg_variance_pct=round(avg_var, 4),
        hit_rate_pct=round(hit_rate * 100, 2),
        beat_rate_pct=round(beat_rate * 100, 2),
        miss_rate_pct=round(miss_rate * 100, 2),
        reliability_score_0_100=int(score),
        recommended_haircut_pct=round(haircut, 4),
        partner_note=note,
    )


def render_reliability_markdown(r: ReliabilityReport) -> str:
    lines = [
        "# Management forecast reliability",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Reliability score: **{r.reliability_score_0_100}/100**",
        f"- Average variance: {r.avg_variance_pct*100:+.1f}%",
        f"- Hit rate (±5%): {r.hit_rate_pct:.0f}%",
        f"- Beat rate (>+5%): {r.beat_rate_pct:.0f}%",
        f"- Miss rate (<-5%): {r.miss_rate_pct:.0f}%",
        f"- Recommended haircut on current forecast: "
        f"{r.recommended_haircut_pct*100:.0f}%",
        "",
        "| Year | Forecast | Actual | Variance | Status |",
        "|---:|---:|---:|---:|---|",
    ]
    for y in r.years:
        lines.append(
            f"| {y.year} | ${y.forecast_ebitda_m:,.1f}M | "
            f"${y.actual_ebitda_m:,.1f}M | "
            f"{y.variance_pct*100:+.1f}% | {y.status} |"
        )
    return "\n".join(lines)
