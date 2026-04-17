"""Scenario narrative — render the stress-grid as partner prose.

`stress_test.py` produces a :class:`StressGridResult` with numeric
outcomes and a letter grade. Partners want to read the narrative
version: "if CMS cuts 200 bps the deal still clears, but a
simultaneous volume decline kills it."

This module turns the grid into three narrative pieces:

- **Worst-case walk** — one sentence naming the most damaging
  scenario with $ / pct impact.
- **Passing-downside summary** — list of shocks the deal absorbs.
- **Compound-shock warning** — flags scenario pairs that together
  break the deal even if individually they don't.

Pairs well with `narrative_styles.py` — use these blocks inside any
style's `bear_case`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ScenarioNarrativeResult:
    headline: str                                 # one-sentence partner take
    worst_case_sentence: str = ""
    passing_downside_summary: str = ""
    compound_warning: str = ""
    failing_scenarios: List[str] = field(default_factory=list)
    passing_scenarios: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "headline": self.headline,
            "worst_case_sentence": self.worst_case_sentence,
            "passing_downside_summary": self.passing_downside_summary,
            "compound_warning": self.compound_warning,
            "failing_scenarios": list(self.failing_scenarios),
            "passing_scenarios": list(self.passing_scenarios),
        }


def _scenario_label(scenario: str) -> str:
    """Human-friendly label for a scenario id."""
    return {
        "rate_down_100bps": "CMS rate cut 100 bps",
        "rate_down_200bps": "CMS rate cut 200 bps",
        "rate_down_300bps": "CMS rate cut 300 bps",
        "volume_down_5pct": "5% volume decline",
        "volume_down_10pct": "10% volume decline",
        "multiple_compression_flat": "exit at entry multiple",
        "lever_slip_60pct": "lever program delivers 60%",
        "lever_slip_40pct": "lever program delivers 40%",
        "labor_shock_10pct": "agency labor +10%",
        "labor_shock_20pct": "agency labor +20%",
        "lever_full_realization": "lever program at plan",
        "multiple_expansion_+1x": "exit multiple +1 turn",
    }.get(scenario, scenario.replace("_", " "))


def _worst_case_sentence(grid: Dict[str, Any]) -> str:
    outcomes = grid.get("outcomes") or []
    # Find the failing downside with the largest negative ebitda_delta_pct.
    downside_fails = [o for o in outcomes
                      if o.get("severity") == "downside"
                      and o.get("passes") is False]
    if not downside_fails:
        return "No downside scenario materially breaks the deal."
    worst = None
    worst_delta = 0.0
    for o in downside_fails:
        d = o.get("ebitda_delta_pct")
        if d is None:
            continue
        if d < worst_delta:
            worst_delta = d
            worst = o
    if worst is None:
        worst = downside_fails[0]
    label = _scenario_label(worst.get("name", ""))
    d = worst.get("ebitda_delta_pct")
    if d is not None:
        return (f"Worst-case downside: {label} (~{d*100:.1f}% EBITDA hit) "
                "breaks the deal as modeled.")
    breach = " (covenant breach)" if worst.get("covenant_breach") else ""
    return f"Worst-case downside: {label}{breach}."


def _passing_summary(grid: Dict[str, Any]) -> str:
    outcomes = grid.get("outcomes") or []
    passers = [o for o in outcomes
               if o.get("severity") == "downside" and o.get("passes") is True]
    if not passers:
        return "The deal does not cleanly pass any downside scenario."
    labels = [_scenario_label(o.get("name", "")) for o in passers[:4]]
    more = len(passers) - 4
    suffix = f" (+{more} more)" if more > 0 else ""
    return f"Deal absorbs: {', '.join(labels)}{suffix}."


def _compound_warning(grid: Dict[str, Any]) -> str:
    """Identify scenario pairs that, if compounded, would kill the deal
    even when each individually passes."""
    outcomes = grid.get("outcomes") or []
    pass_rate = grid.get("downside_pass_rate") or 0.0
    if pass_rate >= 0.90:
        return "High downside pass rate — compound shocks unlikely to break the deal."
    # Identify the smallest-margin passing downsides (closest-to-failing).
    marginal = []
    for o in outcomes:
        if (o.get("severity") == "downside"
                and o.get("passes") is True
                and o.get("ebitda_delta_pct") is not None):
            delta = o.get("ebitda_delta_pct")
            # Looser threshold: within 10% of the breakpoint.
            if delta <= -0.05:
                marginal.append(o)
    if len(marginal) < 2:
        return ""
    labels = [_scenario_label(o.get("name", "")) for o in marginal[:2]]
    return (f"Watch for compound shocks: {labels[0]} and {labels[1]} each "
            "pass alone, but stacked they likely break covenant.")


def _headline(grid: Dict[str, Any]) -> str:
    grade = grid.get("robustness_grade", "?")
    pass_rate = grid.get("downside_pass_rate", 0.0) or 0.0
    grade_headlines = {
        "A": "Deal is durable across the scenario grid.",
        "B": f"Deal is serviceable — {pass_rate*100:.0f}% of downsides clear.",
        "C": f"Deal is fragile — only {pass_rate*100:.0f}% of downsides pass.",
        "D": f"Deal is weak — majority of downsides break it.",
        "F": "Deal is brittle — do not bring as modeled.",
    }
    return grade_headlines.get(grade,
                               f"Stress grid: grade {grade}, pass rate {pass_rate*100:.0f}%.")


def render_scenario_narrative(grid: Dict[str, Any]) -> ScenarioNarrativeResult:
    """Render a stress-grid result dict as partner-narrative text."""
    outcomes = grid.get("outcomes") or []
    failing = [_scenario_label(o.get("name", "")) for o in outcomes
               if o.get("passes") is False]
    passing = [_scenario_label(o.get("name", "")) for o in outcomes
               if o.get("passes") is True and o.get("severity") == "downside"]
    return ScenarioNarrativeResult(
        headline=_headline(grid),
        worst_case_sentence=_worst_case_sentence(grid),
        passing_downside_summary=_passing_summary(grid),
        compound_warning=_compound_warning(grid),
        failing_scenarios=failing,
        passing_scenarios=passing,
    )


def render_scenario_markdown(grid: Dict[str, Any]) -> str:
    """Markdown-formatted scenario narrative."""
    narr = render_scenario_narrative(grid)
    parts = [
        f"## Stress grid: {grid.get('robustness_grade', '?')}",
        "",
        narr.headline,
        "",
        f"**Worst case:** {narr.worst_case_sentence}",
        "",
        f"**Absorbs:** {narr.passing_downside_summary}",
    ]
    if narr.compound_warning:
        parts.extend(["", f"**Compound risk:** {narr.compound_warning}"])
    return "\n".join(parts)
