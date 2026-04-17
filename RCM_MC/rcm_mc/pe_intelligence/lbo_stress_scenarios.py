"""LBO stress scenarios — covenant-breach oriented downside tests.

This module runs named, partner-recognizable downside scenarios
against a deal's capital structure and base-case EBITDA. Each
scenario quantifies:

- **EBITDA hit** — dollar and percentage.
- **Post-shock leverage** — debt / stressed EBITDA.
- **Post-shock coverage** — stressed EBITDA / interest.
- **Covenant breach** — boolean vs headroom.
- **Months-to-default** — crude estimate assuming EBITDA
  doesn't recover.

Scenarios included (healthcare-PE focused):

- `recession_soft` — -10% EBITDA, rates +100 bps.
- `recession_hard` — -25% EBITDA, rates +200 bps.
- `denial_rate_spike` — -15% EBITDA from working-capital hit.
- `medicare_cut` — -8% EBITDA from IPPS / physician fee-schedule cut.
- `labor_shock` — -18% EBITDA from wage inflation.
- `cyber_attack` — -20% EBITDA (one-time) + $5M cash outflow.
- `lost_contract` — -12% EBITDA from single large payer loss.

All scenarios are composable: run them individually or together
via ``run_all_lbo_stresses``. Output is a ``LBOStressReport``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class LBOStressInputs:
    base_ebitda_m: float
    debt_m: float
    interest_rate: float
    covenant_leverage_max: float = 7.0    # triggered if post-shock > this
    covenant_coverage_min: float = 2.0    # triggered if post-shock < this
    cash_on_hand_m: float = 20.0


@dataclass
class LBOStressScenario:
    name: str
    ebitda_hit_pct: float
    rate_shift_bps: int = 0
    one_time_cash_m: float = 0.0          # cash outflow at shock
    description: str = ""


LBO_STRESS_LIBRARY: List[LBOStressScenario] = [
    LBOStressScenario(
        name="recession_soft",
        ebitda_hit_pct=-0.10, rate_shift_bps=100,
        description="Mild recession: -10% EBITDA, rates +100 bps.",
    ),
    LBOStressScenario(
        name="recession_hard",
        ebitda_hit_pct=-0.25, rate_shift_bps=200,
        description="Severe recession: -25% EBITDA, rates +200 bps.",
    ),
    LBOStressScenario(
        name="denial_rate_spike",
        ebitda_hit_pct=-0.15,
        description="Payer denial spike: -15% EBITDA from working-cap hit.",
    ),
    LBOStressScenario(
        name="medicare_cut",
        ebitda_hit_pct=-0.08,
        description="CMS IPPS / fee-schedule cut: -8% EBITDA.",
    ),
    LBOStressScenario(
        name="labor_shock",
        ebitda_hit_pct=-0.18,
        description="Wage inflation shock: -18% EBITDA.",
    ),
    LBOStressScenario(
        name="cyber_attack",
        ebitda_hit_pct=-0.20, one_time_cash_m=5.0,
        description="Cyber incident: -20% EBITDA + $5M cash outflow.",
    ),
    LBOStressScenario(
        name="lost_contract",
        ebitda_hit_pct=-0.12,
        description="Single large payer contract lost: -12% EBITDA.",
    ),
]


@dataclass
class LBOStressResult:
    scenario: str
    stressed_ebitda_m: float
    stressed_leverage: float
    stressed_coverage: float
    leverage_breach: bool
    coverage_breach: bool
    breach: bool                          # either breach
    months_to_default: Optional[int]
    cash_after_shock_m: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario": self.scenario,
            "stressed_ebitda_m": self.stressed_ebitda_m,
            "stressed_leverage": self.stressed_leverage,
            "stressed_coverage": self.stressed_coverage,
            "leverage_breach": self.leverage_breach,
            "coverage_breach": self.coverage_breach,
            "breach": self.breach,
            "months_to_default": self.months_to_default,
            "cash_after_shock_m": self.cash_after_shock_m,
        }


@dataclass
class LBOStressReport:
    results: List[LBOStressResult] = field(default_factory=list)
    worst_scenario: str = ""
    worst_stressed_leverage: float = 0.0
    worst_stressed_coverage: float = 99.0
    breach_count: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "results": [r.to_dict() for r in self.results],
            "worst_scenario": self.worst_scenario,
            "worst_stressed_leverage": self.worst_stressed_leverage,
            "worst_stressed_coverage": self.worst_stressed_coverage,
            "breach_count": self.breach_count,
            "partner_note": self.partner_note,
        }


def _months_to_default(stressed_ebitda: float, interest: float,
                        cash: float) -> Optional[int]:
    """Rough estimate: if EBITDA < interest, how long does cash last?"""
    annual_burn = interest - max(0.0, stressed_ebitda)
    if annual_burn <= 0:
        return None
    months = max(0.0, cash / annual_burn * 12.0)
    return int(months) if months < 240 else None


def run_scenario(inputs: LBOStressInputs,
                 scenario: LBOStressScenario) -> LBOStressResult:
    stressed_ebitda = inputs.base_ebitda_m * (1 + scenario.ebitda_hit_pct)
    stressed_rate = inputs.interest_rate + scenario.rate_shift_bps / 10000.0
    interest = inputs.debt_m * stressed_rate
    leverage = inputs.debt_m / max(0.01, stressed_ebitda)
    coverage = (stressed_ebitda / interest) if interest > 0 else 99.0
    lev_breach = leverage > inputs.covenant_leverage_max
    cov_breach = coverage < inputs.covenant_coverage_min
    breach = lev_breach or cov_breach
    cash_after = inputs.cash_on_hand_m - scenario.one_time_cash_m
    mtd = _months_to_default(stressed_ebitda, interest, cash_after)
    return LBOStressResult(
        scenario=scenario.name,
        stressed_ebitda_m=round(stressed_ebitda, 2),
        stressed_leverage=round(leverage, 2),
        stressed_coverage=round(coverage, 2),
        leverage_breach=lev_breach,
        coverage_breach=cov_breach,
        breach=breach,
        months_to_default=mtd,
        cash_after_shock_m=round(cash_after, 2),
    )


def run_all_lbo_stresses(inputs: LBOStressInputs,
                         scenarios: Optional[List[LBOStressScenario]] = None
                         ) -> LBOStressReport:
    """Run all stress scenarios; return sorted report."""
    scen = scenarios if scenarios is not None else LBO_STRESS_LIBRARY
    results = [run_scenario(inputs, s) for s in scen]

    worst_by_coverage = min(results,
                             key=lambda r: r.stressed_coverage,
                             default=None)
    breach_count = sum(1 for r in results if r.breach)

    if worst_by_coverage is None:
        return LBOStressReport(partner_note="No scenarios run.")

    if breach_count == 0:
        note = (f"Covenants hold across {len(results)} scenarios. "
                f"Worst case: {worst_by_coverage.scenario} — coverage "
                f"{worst_by_coverage.stressed_coverage:.2f}x.")
    elif breach_count <= 2:
        note = (f"{breach_count} scenario(s) breach covenants — manageable. "
                f"Focus monitoring on: "
                f"{', '.join(r.scenario for r in results if r.breach)}.")
    else:
        note = (f"Breaches in {breach_count}/{len(results)} scenarios — "
                "capital structure is fragile. Consider lower leverage "
                "at entry or covenant-lite terms.")

    return LBOStressReport(
        results=results,
        worst_scenario=worst_by_coverage.scenario,
        worst_stressed_leverage=worst_by_coverage.stressed_leverage,
        worst_stressed_coverage=worst_by_coverage.stressed_coverage,
        breach_count=breach_count,
        partner_note=note,
    )


def render_lbo_stress_markdown(report: LBOStressReport) -> str:
    lines = [
        "# LBO stress scenarios",
        "",
        f"_{report.partner_note}_",
        "",
        "| Scenario | EBITDA | Lev | Cov | Breach | MtD (mo) |",
        "|---|---:|---:|---:|:-:|---:|",
    ]
    for r in report.results:
        breach = "**yes**" if r.breach else "no"
        mtd = str(r.months_to_default) if r.months_to_default is not None else "—"
        lines.append(
            f"| {r.scenario} | ${r.stressed_ebitda_m:,.1f}M | "
            f"{r.stressed_leverage:.1f}x | {r.stressed_coverage:.1f}x | "
            f"{breach} | {mtd} |"
        )
    return "\n".join(lines)
