"""Clinical outcome leading indicators — 18-month early warning.

Partner statement: "Quality metrics hit reimbursement
18-24 months after they deteriorate. Readmission rates
rising in 2026 means VBP cuts in 2028. I want the
trendline flagged now, not when the CMS penalty letter
arrives."

Distinct from:
- `quality_metrics` — point-in-time score → VBP dollar
  impact.
- `cash_conversion_drift_detector` — working-capital
  trends.

This module is trend-based: across 6 clinical-quality
metrics, flag direction-of-deterioration and quantify
the **forward reimbursement hit** in 18-24 months.

### 6 indicators tracked

1. **readmission_rate_30d** — HRRP penalty up to 3% of
   Medicare.
2. **hac_score_percentile** — HAC Reduction Program
   bottom quartile = 1% cut.
3. **hcahps_top_box_pct** — VBP patient-experience
   component.
4. **cms_star_rating** — 1-5; aggregate quality
   signal.
5. **sentinel_event_frequency** — Joint Commission
   reporting + CMS conditions-of-participation risk.
6. **physician_turnover_rate** — leading indicator of
   quality / retention fracture.

### Output

Per-metric trend direction, deterioration flag,
estimated forward-reimbursement-hit % of Medicare
revenue, partner note on aggregate exposure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ClinicalIndicator:
    name: str
    slope_per_quarter: float
    is_deteriorating: bool
    forward_reimbursement_hit_bps: float
    partner_comment: str


@dataclass
class ClinicalOutcomeInputs:
    readmission_rate_30d_series: List[float] = field(default_factory=list)
    hac_score_percentile_series: List[float] = field(default_factory=list)
    hcahps_top_box_pct_series: List[float] = field(default_factory=list)
    cms_star_rating_series: List[float] = field(default_factory=list)
    sentinel_event_frequency_series: List[float] = field(
        default_factory=list
    )
    physician_turnover_rate_series: List[float] = field(
        default_factory=list
    )
    medicare_revenue_m: float = 0.0


@dataclass
class ClinicalOutcomeReport:
    indicators: List[ClinicalIndicator] = field(default_factory=list)
    deteriorating_count: int = 0
    total_forward_reimbursement_hit_bps: float = 0.0
    forward_reimbursement_hit_m: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "indicators": [
                {"name": i.name,
                 "slope_per_quarter": i.slope_per_quarter,
                 "is_deteriorating": i.is_deteriorating,
                 "forward_reimbursement_hit_bps":
                     i.forward_reimbursement_hit_bps,
                 "partner_comment": i.partner_comment}
                for i in self.indicators
            ],
            "deteriorating_count": self.deteriorating_count,
            "total_forward_reimbursement_hit_bps":
                self.total_forward_reimbursement_hit_bps,
            "forward_reimbursement_hit_m":
                self.forward_reimbursement_hit_m,
            "partner_note": self.partner_note,
        }


# Deterioration direction and per-deterioration
# reimbursement hit (bps of Medicare revenue in 18-24mo).
INDICATOR_CONFIG: Dict[str, Dict[str, Any]] = {
    "readmission_rate_30d": {
        "direction": "rising",         # worse = rising
        "threshold": 0.002,            # 0.2% / qtr
        "hit_bps": 150,                # up to 3% cut but tiered
    },
    "hac_score_percentile": {
        "direction": "rising",         # worse = rising pctile (more HACs)
        "threshold": 2.0,
        "hit_bps": 100,
    },
    "hcahps_top_box_pct": {
        "direction": "falling",
        "threshold": 0.01,
        "hit_bps": 75,
    },
    "cms_star_rating": {
        "direction": "falling",
        "threshold": 0.10,
        "hit_bps": 200,
    },
    "sentinel_event_frequency": {
        "direction": "rising",
        "threshold": 0.05,
        "hit_bps": 60,
    },
    "physician_turnover_rate": {
        "direction": "rising",
        "threshold": 0.02,
        "hit_bps": 40,
    },
}


def _slope(series: List[float]) -> float:
    n = len(series)
    if n < 3:
        return 0.0
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(series) / n
    num = sum((xs[i] - mean_x) * (series[i] - mean_y)
              for i in range(n))
    den = sum((xs[i] - mean_x) ** 2 for i in range(n))
    return num / den if den != 0 else 0.0


def _is_deteriorating(direction: str, slope: float,
                       threshold: float) -> bool:
    if direction == "rising":
        return slope > threshold
    return slope < -threshold


def scan_clinical_outcomes(
    inputs: ClinicalOutcomeInputs,
) -> ClinicalOutcomeReport:
    series_by_name: Dict[str, List[float]] = {
        "readmission_rate_30d":
            inputs.readmission_rate_30d_series,
        "hac_score_percentile":
            inputs.hac_score_percentile_series,
        "hcahps_top_box_pct":
            inputs.hcahps_top_box_pct_series,
        "cms_star_rating": inputs.cms_star_rating_series,
        "sentinel_event_frequency":
            inputs.sentinel_event_frequency_series,
        "physician_turnover_rate":
            inputs.physician_turnover_rate_series,
    }

    indicators: List[ClinicalIndicator] = []
    total_bps = 0.0
    det_count = 0
    for name, series in series_by_name.items():
        cfg = INDICATOR_CONFIG[name]
        slope = _slope(series)
        det = False
        hit = 0.0
        if len(series) >= 3:
            det = _is_deteriorating(
                cfg["direction"], slope, cfg["threshold"]
            )
            if det:
                hit = cfg["hit_bps"]
                det_count += 1
                total_bps += hit
        comment = (
            f"Trend {slope:+.4f}/qtr; deteriorating → "
            f"~{hit:.0f} bps forward hit."
            if det else
            (f"Trend {slope:+.4f}/qtr; not deteriorating."
             if len(series) >= 3 else
             f"Series < 3 observations; cannot trend.")
        )
        indicators.append(ClinicalIndicator(
            name=name,
            slope_per_quarter=round(slope, 4),
            is_deteriorating=det,
            forward_reimbursement_hit_bps=hit,
            partner_comment=comment,
        ))

    # Cap aggregate at 500 bps — partners don't assume
    # stacked pain beyond that.
    total_bps = min(500.0, total_bps)
    dollar_hit = round(
        inputs.medicare_revenue_m * (total_bps / 10000.0), 2
    )

    if det_count >= 3:
        note = (
            f"{det_count} clinical indicators deteriorating; "
            f"forward reimbursement hit ~{total_bps:.0f} bps "
            f"= ${dollar_hit:,.1f}M on Medicare revenue. "
            "Partner: clinical-quality turnaround required "
            "before exit — 18-mo clock running."
        )
    elif det_count == 2:
        note = (
            f"{det_count} indicators deteriorating. "
            f"~${dollar_hit:,.1f}M forward hit. Partner: "
            "diligence the two trendlines specifically; "
            "quality-program spending may be required."
        )
    elif det_count == 1:
        note = (
            f"{det_count} deteriorating indicator. "
            "Partner: monitor; may be noise."
        )
    else:
        note = (
            "No clinical-quality leading indicator "
            "deteriorating. Partner: proceed on current "
            "quality assumptions."
        )

    return ClinicalOutcomeReport(
        indicators=indicators,
        deteriorating_count=det_count,
        total_forward_reimbursement_hit_bps=round(
            total_bps, 1
        ),
        forward_reimbursement_hit_m=dollar_hit,
        partner_note=note,
    )


def render_clinical_outcome_markdown(
    r: ClinicalOutcomeReport,
) -> str:
    lines = [
        "# Clinical outcome leading indicators",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Deteriorating: {r.deteriorating_count}",
        f"- Forward reimbursement hit: "
        f"{r.total_forward_reimbursement_hit_bps:.0f} bps "
        f"(${r.forward_reimbursement_hit_m:,.1f}M)",
        "",
        "| Indicator | Slope/qtr | Deteriorating | "
        "Fwd hit (bps) | Partner comment |",
        "|---|---|---|---|---|",
    ]
    for i in r.indicators:
        det = "✓" if i.is_deteriorating else "—"
        lines.append(
            f"| {i.name} | {i.slope_per_quarter:+.4f} | "
            f"{det} | {i.forward_reimbursement_hit_bps:.0f} | "
            f"{i.partner_comment} |"
        )
    return "\n".join(lines)
