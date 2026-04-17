"""Side-by-side Monte Carlo scenario comparison.

Partners usually underwrite three or four scenarios: "base case",
"management plan", "downside", "upside". This module runs each with
the same simulator + bridge, then surfaces two diligence artifacts:

1. Pairwise win-probability — ``P(scenario_A > scenario_B)`` on EBITDA
   impact, computed from the MC samples directly (no distributional
   assumption).
2. A single ``recommended_scenario`` that optimizes expected EBITDA
   impact penalized by downside risk (P(negative)). Partners want a
   default to anchor the conversation on, while being able to see the
   math behind the pick.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .ebitda_mc import (
    MetricAssumption,
    MonteCarloResult,
    RCMMonteCarloSimulator,
)


@dataclass
class ScenarioComparison:
    per_scenario: Dict[str, MonteCarloResult] = field(default_factory=dict)
    pairwise_overlap: Dict[str, float] = field(default_factory=dict)
    recommended_scenario: str = ""
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "per_scenario": {k: v.to_dict() for k, v in self.per_scenario.items()},
            "pairwise_overlap": dict(self.pairwise_overlap),
            "recommended_scenario": self.recommended_scenario,
            "rationale": self.rationale,
        }


def _pairwise_key(a: str, b: str) -> str:
    """Flat string key for the JSON map. Tuples aren't JSON-native.

    Partners read this as "P(A > B)", so we keep A's name first.
    """
    return f"{a}__vs__{b}"


def _raw_ebitda_samples(
    simulator: RCMMonteCarloSimulator,
    assumptions: Dict[str, MetricAssumption],
    *,
    scenario_label: str,
) -> Tuple[MonteCarloResult, np.ndarray]:
    """Re-run the simulator and return the per-sim EBITDA impact
    vector along with the canonical :class:`MonteCarloResult`.

    We rerun from a deterministic seed per scenario so the numbers are
    reproducible — partners bring the same run back up next week and
    get identical bars.
    """
    simulator.configure(
        simulator._current_metrics,
        assumptions,
        correlation_matrix=simulator._corr_matrix,
        metric_order=simulator._metric_order or list(assumptions.keys()),
        entry_multiple=simulator.entry_multiple,
        exit_multiple=simulator.exit_multiple,
        hold_years=simulator.hold_years,
        organic_growth_pct=simulator.organic_growth_pct,
        moic_targets=simulator.moic_targets,
        covenant_leverage_threshold=simulator.covenant_leverage_threshold,
    )
    result = simulator.run(scenario_label=scenario_label)

    # Re-sample to get the raw ebitda_impact vector for win-probability
    # math. Cheap — we're reusing the bridge + same seed.
    rng = np.random.default_rng(simulator.seed)
    n = simulator.n_simulations
    vec = np.zeros(n)
    order = simulator._metric_order
    uniforms = simulator._make_uniforms(rng, n)
    for i in range(n):
        sampled_targets: Dict[str, float] = {}
        final_values: Dict[str, float] = {}
        for col, metric in enumerate(order):
            a = assumptions[metric]
            u = uniforms[i, col] if uniforms is not None else None
            sampled_target = RCMMonteCarloSimulator._sample_prediction(a, rng, u)
            exec_frac = RCMMonteCarloSimulator._sample_execution(a, rng)
            final = a.current_value + (sampled_target - a.current_value) * exec_frac
            final_values[metric] = final
        try:
            br = simulator.bridge.compute_bridge(
                {k: assumptions[k].current_value for k in order}, final_values,
            )
            vec[i] = br.total_ebitda_impact
        except Exception:  # noqa: BLE001
            vec[i] = 0.0
    return result, vec


def compare_scenarios(
    simulator: RCMMonteCarloSimulator,
    scenarios: Dict[str, Dict[str, MetricAssumption]],
    *,
    risk_aversion: float = 0.5,
) -> ScenarioComparison:
    """Run one MC per scenario and compute pairwise win-probabilities.

    ``risk_aversion`` blends "mean EBITDA impact" against "P(negative)"
    in the recommendation score:
        score = mean - risk_aversion × downside_std
    Pick the scenario with the highest score.
    """
    if not scenarios:
        return ScenarioComparison()

    per_scenario: Dict[str, MonteCarloResult] = {}
    raw_samples: Dict[str, np.ndarray] = {}
    for name, assumptions in scenarios.items():
        result, vec = _raw_ebitda_samples(
            simulator, assumptions, scenario_label=name,
        )
        per_scenario[name] = result
        raw_samples[name] = vec

    pairwise: Dict[str, float] = {}
    names = list(per_scenario.keys())
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            va = raw_samples[a]
            vb = raw_samples[b]
            # Pairwise: randomly pair simulation indices — treat the two
            # scenarios as independent draws of "what happens next".
            m = min(len(va), len(vb))
            pairwise[_pairwise_key(a, b)] = float(np.mean(va[:m] > vb[:m]))
            pairwise[_pairwise_key(b, a)] = float(np.mean(vb[:m] > va[:m]))

    # Risk-adjusted score
    best_name = names[0]
    best_score = -float("inf")
    rationale_lines: List[str] = []
    for name in names:
        vec = raw_samples[name]
        mean = float(np.mean(vec))
        downside = float(np.std(vec[vec < mean])) if np.any(vec < mean) else 0.0
        score = mean - risk_aversion * downside
        rationale_lines.append(
            f"{name}: mean={mean:,.0f}, downside_σ={downside:,.0f}, "
            f"score={score:,.0f}"
        )
        if score > best_score:
            best_score = score
            best_name = name
    rationale = (
        f"Recommended '{best_name}' by mean − {risk_aversion:g}×downside_σ. "
        + "; ".join(rationale_lines)
    )
    return ScenarioComparison(
        per_scenario=per_scenario,
        pairwise_overlap=pairwise,
        recommended_scenario=best_name,
        rationale=rationale,
    )
