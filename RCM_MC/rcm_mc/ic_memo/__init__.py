"""IC Memo Generator — partner-facing investment-committee memo.

The existing ``ic_binder`` renders a SynthesisResult organised by
packet. An IC memo is organised by the section headings a partner
expects to see in the IC pre-read:

  1. Executive Summary
  2. Target Overview
  3. Investment Thesis
  4. Comparable Transactions
  5. Predictions & EBITDA Bridge
  6. Scenarios (Bull / Base / Bear)
  7. Key Risks
  8. Methodology Appendix

This module wires the existing synthesis output into that
structure, augments with bull/base/bear scenario construction
(off the comparable-deal MOIC distribution + the QoE-adjusted
EBITDA), and renders both markdown and HTML.

Public API::

    from rcm_mc.ic_memo import (
        build_ic_memo, ICMemo,
        render_memo_markdown, render_memo_html,
        build_scenarios, ScenarioSet,
    )
"""
from .scenarios import build_scenarios, ScenarioSet, Scenario
from .memo import build_ic_memo, ICMemo
from .render import render_memo_markdown, render_memo_html

__all__ = [
    "build_ic_memo", "ICMemo",
    "render_memo_markdown", "render_memo_html",
    "build_scenarios", "ScenarioSet", "Scenario",
]
