"""De novo site ramp economics — month-by-month carrying cost to breakeven.

Partner statement: "De novo healthcare sites look
great on a 3-year pro-forma. Month by month, they
bleed. Year 1: rent + labor + credentialing with
10-30% of revenue. Year 2: 50-70% of revenue, still
sub-contribution-margin. Year 3-4: at run-rate. If
the model says breakeven at month 12, ask how. The
credentialing cycle alone is 6-9 months with
commercial payers."

Distinct from:
- `capex_intensity_stress` — capex drag.
- `capacity_expansion` archetype — narrative.
- `healthcare_thesis_archetype_recognizer` — class.

This module projects **month-by-month** economics
for a single de novo site from open → breakeven →
run-rate, and computes cumulative carrying cost.

### Ramp curve (default — specialty practice)

- Months 0-3: 15% of run-rate revenue (credentialing
  + ramp)
- Months 4-6: 30%
- Months 7-12: 50%
- Months 13-18: 70%
- Months 19-24: 85%
- Months 25+: 100%

### Output

- monthly P&L from open
- month-to-breakeven
- cumulative carrying cost (negative EBITDA) before
  breakeven
- partner note on reasonableness of model's
  assumption
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


DEFAULT_RAMP_CURVE: List[tuple] = [
    # (min_month, max_month, pct_of_run_rate_revenue)
    (0, 3, 0.15),
    (4, 6, 0.30),
    (7, 12, 0.50),
    (13, 18, 0.70),
    (19, 24, 0.85),
    (25, 120, 1.00),
]


def _ramp_pct(month: int) -> float:
    for lo, hi, pct in DEFAULT_RAMP_CURVE:
        if lo <= month <= hi:
            return pct
    return 1.0


@dataclass
class DeNovoRampInputs:
    run_rate_monthly_revenue_m: float = 0.30
    """Revenue at steady state (month 25+)."""
    monthly_fixed_cost_m: float = 0.12
    """Rent + base labor + overhead; constant."""
    variable_cost_pct_of_revenue: float = 0.55
    """Variable cost as % of each month's actual revenue."""
    startup_capex_m: float = 0.50
    """One-time capex charged at month 0."""
    analysis_months: int = 36
    assumed_breakeven_month_in_model: Optional[int] = None


@dataclass
class MonthlyDeNovo:
    month: int
    revenue_pct_of_run_rate: float
    revenue_m: float
    variable_cost_m: float
    fixed_cost_m: float
    contribution_m: float
    cumulative_ebitda_m: float


@dataclass
class DeNovoRampReport:
    months: List[MonthlyDeNovo] = field(default_factory=list)
    breakeven_month: Optional[int] = None
    cumulative_drag_to_breakeven_m: float = 0.0
    total_36mo_ebitda_m: float = 0.0
    model_assumption_delta_months: Optional[int] = None
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "months": [
                {"month": m.month,
                 "revenue_pct_of_run_rate":
                     m.revenue_pct_of_run_rate,
                 "revenue_m": m.revenue_m,
                 "variable_cost_m": m.variable_cost_m,
                 "fixed_cost_m": m.fixed_cost_m,
                 "contribution_m": m.contribution_m,
                 "cumulative_ebitda_m":
                     m.cumulative_ebitda_m}
                for m in self.months
            ],
            "breakeven_month": self.breakeven_month,
            "cumulative_drag_to_breakeven_m":
                self.cumulative_drag_to_breakeven_m,
            "total_36mo_ebitda_m":
                self.total_36mo_ebitda_m,
            "model_assumption_delta_months":
                self.model_assumption_delta_months,
            "partner_note": self.partner_note,
        }


def project_de_novo_ramp(
    inputs: DeNovoRampInputs,
) -> DeNovoRampReport:
    months: List[MonthlyDeNovo] = []
    cum_ebitda = -inputs.startup_capex_m
    breakeven = None
    drag_to_breakeven = 0.0
    prev_cum = cum_ebitda
    for m in range(1, inputs.analysis_months + 1):
        pct = _ramp_pct(m)
        revenue = inputs.run_rate_monthly_revenue_m * pct
        variable = (
            revenue * inputs.variable_cost_pct_of_revenue
        )
        fixed = inputs.monthly_fixed_cost_m
        contribution = revenue - variable - fixed
        cum_ebitda += contribution
        if breakeven is None and contribution > 0 and cum_ebitda >= 0:
            breakeven = m
            drag_to_breakeven = abs(
                min(cum_ebitda, prev_cum))
        elif breakeven is None and contribution > 0:
            # contribution positive but cumulative still negative
            pass
        months.append(MonthlyDeNovo(
            month=m,
            revenue_pct_of_run_rate=pct,
            revenue_m=round(revenue, 3),
            variable_cost_m=round(variable, 3),
            fixed_cost_m=round(fixed, 3),
            contribution_m=round(contribution, 3),
            cumulative_ebitda_m=round(cum_ebitda, 3),
        ))
        prev_cum = cum_ebitda

    total_36 = cum_ebitda
    # Compute actual drag = minimum cumulative ebitda
    min_cum = min(m.cumulative_ebitda_m for m in months)
    drag_to_be = abs(min_cum)

    delta_months: Optional[int] = None
    if (inputs.assumed_breakeven_month_in_model is not None
            and breakeven is not None):
        delta_months = (
            breakeven -
            inputs.assumed_breakeven_month_in_model
        )

    if breakeven is None:
        verdict_note = (
            f"Site does not break even in "
            f"{inputs.analysis_months}-month window. "
            "Extend analysis or rerun with higher "
            "run-rate revenue assumption."
        )
    elif breakeven <= 12:
        verdict_note = (
            f"Breakeven month {breakeven} — aggressive. "
            "Credentialing cycle alone is 6-9 months "
            "with commercial payers; verify plan "
            "includes payer credentialing pre-open."
        )
    elif breakeven <= 24:
        verdict_note = (
            f"Breakeven month {breakeven} — within "
            "typical healthcare de-novo range (18-24 "
            f"mo). Carrying cost "
            f"${drag_to_be:.2f}M to breakeven."
        )
    else:
        verdict_note = (
            f"Breakeven month {breakeven} — long "
            "ramp. Cumulative drag "
            f"${drag_to_be:.2f}M. Re-verify assumed "
            "run-rate revenue vs MSA peer sites."
        )

    if delta_months is not None:
        if delta_months > 6:
            verdict_note += (
                f" Model assumes breakeven "
                f"{delta_months} months earlier than "
                "empirical — optimistic."
            )
        elif delta_months < -3:
            verdict_note += (
                f" Model assumes breakeven "
                f"{-delta_months} months later than "
                "empirical — conservative; verify why."
            )

    return DeNovoRampReport(
        months=months,
        breakeven_month=breakeven,
        cumulative_drag_to_breakeven_m=round(
            drag_to_be, 3),
        total_36mo_ebitda_m=round(total_36, 3),
        model_assumption_delta_months=delta_months,
        partner_note=verdict_note,
    )


def render_de_novo_ramp_markdown(
    r: DeNovoRampReport,
) -> str:
    lines = [
        "# De novo site ramp economics",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Breakeven month: "
        f"{r.breakeven_month if r.breakeven_month else 'not in window'}",
        f"- Cumulative drag to breakeven: "
        f"${r.cumulative_drag_to_breakeven_m:.2f}M",
        f"- 36-month EBITDA: "
        f"${r.total_36mo_ebitda_m:+.2f}M",
        "",
        "| Month | Rev % | Rev $M | Var $M | Fixed $M | "
        "Contribution $M | Cum EBITDA $M |",
        "|---|---|---|---|---|---|---|",
    ]
    # Sample key months only to keep markdown readable
    key_months = {
        1, 3, 6, 9, 12, 15, 18, 21, 24, 30, 36,
    }
    for m in r.months:
        if m.month not in key_months:
            continue
        lines.append(
            f"| {m.month} | "
            f"{m.revenue_pct_of_run_rate:.0%} | "
            f"${m.revenue_m:.3f} | "
            f"${m.variable_cost_m:.3f} | "
            f"${m.fixed_cost_m:.3f} | "
            f"${m.contribution_m:+.3f} | "
            f"${m.cumulative_ebitda_m:+.3f} |"
        )
    return "\n".join(lines)
