# Scenario & Stress Engine

How PEdesk applies downside/macro scenarios to a deal. Explains the backend so
the Guide can answer "how do scenarios work / what does a preset shock change".

## What it does
A library of named preset shocks (e.g. payer rate cuts, volume shocks) is
defined as structured, reusable adjustments. A preset is layered onto a deal's
simulation/model so the same downside case can be applied consistently across
deals.
- Modules: `rcm_mc/scenarios/scenario_shocks.py` (the PRESET_SHOCKS library),
  `rcm_mc/scenarios/scenario_overlay.py` (applies a shock to a deal's inputs),
  `rcm_mc/scenarios/scenario_builder.py`.
- The /scenarios page is the catalog/explainer; the dollar impact materializes
  only when a preset is applied to a specific deal's simulation.

## How to read it
- A preset is a TEMPLATE of assumptions — the impact depends entirely on the
  deal it's applied to. The catalog page shows definitions, not a deal's result.
- Use scenarios to make IC downside cases comparable across deals, and to find
  where a thesis breaks.

## Caveats
- Deterministic preset shocks are assumptions, not predictions; for a full
  outcome distribution use the Monte Carlo engine.
