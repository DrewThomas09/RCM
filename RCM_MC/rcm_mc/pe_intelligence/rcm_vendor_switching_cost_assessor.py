"""RCM vendor switching-cost assessor — transition drag + recovery.

Partner statement: "Every RCM conversion looks
reasonable on the day-one plan. Then month 3 hits,
denial rates spike, DSO blows out 12-18 days, and
cash chokes. Conversion hurts for 6-9 months even
when it goes well. If the deal's thesis requires a
platform cut-over, I want the drag modeled — how
much cash do we lose in transition, how long until
it's better than pre-conversion, and what's the "it
goes badly" scenario."

Distinct from:
- `cash_conversion` — static FCF / EBITDA math.
- `working_capital_seasonality_detector` — YoY trend.
- `back_office_consolidation` archetype narrative.

This module is **transition-specific**:
- monthly DSO trajectory during conversion
- denial-rate spike and recovery
- one-time implementation cost
- partner note on whether the thesis underwrites
  the transition or pretends it isn't there

### Typical conversion DSO pattern (best-case)

- Months 1-2: +5-8 days (training + go-live disruption)
- Months 3-4: +10-15 days (peak disruption)
- Months 5-8: gradual recovery to pre-conversion
- Months 9-12: 3-5 days below pre-conversion
  (platform is better)

"Bad" scenario adds 50-80% magnitude and extends
recovery by 6 months.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RCMSwitchingInputs:
    npr_m: float = 300.0
    pre_conversion_dso_days: float = 45.0
    annual_cash_cost_pre_m: float = 15.0
    """Annual RCM vendor cost pre-conversion (licensing,
    outsourced ops, etc.)."""
    annual_cash_cost_post_m: float = 10.0
    """Annual RCM vendor cost post-conversion."""
    implementation_cost_m: float = 4.0
    """One-time implementation cost (config, training,
    parallel runs)."""
    scenario: str = "best_case"
    """best_case / realistic / bad_case"""


# DSO delta patterns (days) across 12 months
DSO_PATTERNS: Dict[str, List[float]] = {
    "best_case": [
        5, 7, 10, 13, 11, 8, 4, 1, -2, -3, -4, -5,
    ],
    "realistic": [
        7, 10, 14, 18, 16, 12, 8, 4, 0, -2, -3, -3,
    ],
    "bad_case": [
        9, 14, 20, 26, 25, 22, 18, 14, 10, 6, 3, 0,
    ],
}


@dataclass
class MonthlyConversion:
    month: int
    dso_days: float
    dso_delta_days: float
    wc_change_m: float
    cumulative_wc_drag_m: float


@dataclass
class RCMSwitchingReport:
    months: List[MonthlyConversion] = field(
        default_factory=list)
    peak_dso_days: float = 0.0
    peak_dso_month: int = 0
    months_to_recover: Optional[int] = None
    max_cumulative_wc_drag_m: float = 0.0
    implementation_cost_m: float = 0.0
    annual_savings_post_m: float = 0.0
    payback_months: Optional[int] = None
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "months": [
                {"month": m.month,
                 "dso_days": m.dso_days,
                 "dso_delta_days": m.dso_delta_days,
                 "wc_change_m": m.wc_change_m,
                 "cumulative_wc_drag_m":
                     m.cumulative_wc_drag_m}
                for m in self.months
            ],
            "peak_dso_days": self.peak_dso_days,
            "peak_dso_month": self.peak_dso_month,
            "months_to_recover": self.months_to_recover,
            "max_cumulative_wc_drag_m":
                self.max_cumulative_wc_drag_m,
            "implementation_cost_m":
                self.implementation_cost_m,
            "annual_savings_post_m":
                self.annual_savings_post_m,
            "payback_months": self.payback_months,
            "partner_note": self.partner_note,
        }


def assess_rcm_switching(
    inputs: RCMSwitchingInputs,
) -> RCMSwitchingReport:
    pattern = DSO_PATTERNS.get(
        inputs.scenario, DSO_PATTERNS["realistic"])

    months: List[MonthlyConversion] = []
    cumulative_wc = 0.0
    peak_dso = inputs.pre_conversion_dso_days
    peak_month = 0
    recovery_month: Optional[int] = None
    max_drag = 0.0

    monthly_npr = inputs.npr_m / 12.0
    for i, delta in enumerate(pattern, start=1):
        dso = inputs.pre_conversion_dso_days + delta
        # WC change in $M approx: delta_days × monthly NPR / 30
        wc_change = delta * (monthly_npr / 30.0)
        cumulative_wc += wc_change
        if dso > peak_dso:
            peak_dso = dso
            peak_month = i
        if (recovery_month is None and i > 1 and
                delta <= 0):
            recovery_month = i
        if cumulative_wc > max_drag:
            max_drag = cumulative_wc
        months.append(MonthlyConversion(
            month=i,
            dso_days=round(dso, 2),
            dso_delta_days=round(delta, 2),
            wc_change_m=round(wc_change, 3),
            cumulative_wc_drag_m=round(cumulative_wc, 3),
        ))

    annual_savings = (
        inputs.annual_cash_cost_pre_m -
        inputs.annual_cash_cost_post_m
    )
    # Payback: implementation + max WC drag / monthly savings
    if annual_savings > 0:
        monthly_savings = annual_savings / 12.0
        total_cost = (
            inputs.implementation_cost_m + max_drag
        )
        payback = int(
            total_cost / monthly_savings) if monthly_savings > 0 else None
    else:
        payback = None

    # Partner note
    if inputs.scenario == "bad_case":
        note = (
            f"Bad-case conversion: DSO peaks at "
            f"{peak_dso:.0f} days in month "
            f"{peak_month}, cumulative WC drag "
            f"${max_drag:.1f}M. Recovery only by "
            f"month "
            f"{recovery_month if recovery_month else '>12'}. "
            "Factor the drag into cash-flow covenants."
        )
    elif inputs.scenario == "realistic":
        note = (
            f"Realistic conversion: peak DSO "
            f"{peak_dso:.0f} days at month "
            f"{peak_month}, WC drag "
            f"${max_drag:.1f}M. Recovery by month "
            f"{recovery_month if recovery_month else '?'}. "
            f"Implementation ${inputs.implementation_cost_m:.1f}M + "
            f"max WC drag ${max_drag:.1f}M → "
            f"{payback} month payback if annual savings "
            f"${annual_savings:.1f}M."
        )
    else:
        note = (
            f"Best-case conversion: manageable DSO "
            f"spike ({peak_dso:.0f} days), WC drag "
            f"${max_drag:.1f}M. Recovery by month "
            f"{recovery_month}. Base-case should "
            "assume realistic, not best-case."
        )

    if payback is not None and payback > 24:
        note += (
            f" Payback {payback} months exceeds "
            "two years — verify savings assumption "
            "or expand scope."
        )

    return RCMSwitchingReport(
        months=months,
        peak_dso_days=round(peak_dso, 2),
        peak_dso_month=peak_month,
        months_to_recover=recovery_month,
        max_cumulative_wc_drag_m=round(max_drag, 3),
        implementation_cost_m=round(
            inputs.implementation_cost_m, 3),
        annual_savings_post_m=round(annual_savings, 3),
        payback_months=payback,
        partner_note=note,
    )


def render_rcm_switching_markdown(
    r: RCMSwitchingReport,
) -> str:
    lines = [
        "# RCM vendor switching cost",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Peak DSO: {r.peak_dso_days:.0f} days "
        f"(month {r.peak_dso_month})",
        f"- Recovery month: "
        f"{r.months_to_recover if r.months_to_recover else 'none in 12'}",
        f"- Max cumulative WC drag: "
        f"${r.max_cumulative_wc_drag_m:.1f}M",
        f"- Implementation: "
        f"${r.implementation_cost_m:.1f}M",
        f"- Annual savings post: "
        f"${r.annual_savings_post_m:.1f}M",
        f"- Payback: "
        f"{r.payback_months if r.payback_months else 'n/a'} months",
        "",
        "| Month | DSO | Δ days | WC Δ $M | Cum WC drag $M |",
        "|---|---|---|---|---|",
    ]
    for m in r.months:
        lines.append(
            f"| {m.month} | {m.dso_days:.0f} | "
            f"{m.dso_delta_days:+.0f} | "
            f"${m.wc_change_m:+.2f} | "
            f"${m.cumulative_wc_drag_m:+.2f} |"
        )
    return "\n".join(lines)
