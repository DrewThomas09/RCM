"""Top-level entry: valuate_contract + choose_optimal_track."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from ..vbc.cohort import Cohort
from .programs import VBCProgram, PROGRAMS
from .stochastic import StochasticInputs, run_monte_carlo_npv


@dataclass
class ContractValuationResult:
    """Per-program valuation summary."""
    program_id: str
    label: str
    distribution: Dict[str, float] = field(default_factory=dict)
    on_ramp_difficulty: float = 0.5
    risk_adjusted_score: float = 0.0   # used for Track-choice ranking


def valuate_contract(
    cohort: Cohort,
    program_id: str,
    *,
    inputs: Optional[StochasticInputs] = None,
    starting_year: int = 2026,
) -> ContractValuationResult:
    """Run Monte Carlo on one program × cohort combination.

    Returns the distribution + an on-ramp-discounted risk-adjusted
    score the Track optimizer ranks against:

        score = mean_npv − 0.5 × downside_risk(p25 − p50)
                         − 0.3 × on_ramp_difficulty × |mean_npv|
    """
    program = PROGRAMS.get(program_id)
    if not program:
        raise ValueError(f"Unknown program_id: {program_id}")

    distribution = run_monte_carlo_npv(
        cohort, program.contract_template,
        inputs=inputs, starting_year=starting_year,
    )

    mean = distribution["mean_npv_mm"]
    p25 = distribution["p25_mm"]
    p50 = distribution["p50_mm"]
    downside = max(0.0, p50 - p25)

    risk_adjusted = (mean
                     - 0.5 * downside
                     - 0.3 * program.on_ramp_difficulty * abs(mean))

    return ContractValuationResult(
        program_id=program_id,
        label=program.label,
        distribution=distribution,
        on_ramp_difficulty=program.on_ramp_difficulty,
        risk_adjusted_score=round(risk_adjusted, 2),
    )


def choose_optimal_track(
    cohort: Cohort,
    program_ids: Optional[Iterable[str]] = None,
    *,
    inputs: Optional[StochasticInputs] = None,
    starting_year: int = 2026,
) -> Dict[str, object]:
    """Run the valuator across every program and return the
    ranked recommendation.

    Returns a dict with:
      recommended: program_id
      reasoning: short-form rationale
      results: list of ContractValuationResult, sorted by
               risk-adjusted score descending.
    """
    program_ids = list(program_ids or PROGRAMS.keys())
    results: List[ContractValuationResult] = []
    for pid in program_ids:
        try:
            results.append(valuate_contract(
                cohort, pid, inputs=inputs,
                starting_year=starting_year,
            ))
        except Exception:  # noqa: BLE001
            continue

    results.sort(key=lambda r: r.risk_adjusted_score, reverse=True)

    if not results:
        return {
            "recommended": None,
            "reasoning": "No programs valuated successfully.",
            "results": [],
        }

    top = results[0]
    reasoning = (
        f"{top.label}: NPV mean ${top.distribution['mean_npv_mm']/1e6:.2f}M, "
        f"p5 ${top.distribution['p5_mm']/1e6:.2f}M, "
        f"prob_loss {top.distribution['prob_loss']*100:.0f}%, "
        f"on-ramp {top.on_ramp_difficulty:.2f}. "
        f"Risk-adjusted score ${top.risk_adjusted_score/1e6:.2f}M."
    )
    return {
        "recommended": top.program_id,
        "reasoning": reasoning,
        "results": results,
    }
