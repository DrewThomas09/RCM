# Scenarios

What-if scenario modeling: programmatic scenario construction, parameter overlays, and preset payer-policy shock scenarios. Pure config manipulation — does not modify the Monte Carlo kernel math.

---

## `scenario_builder.py` — Fluent Scenario Builder

**What it does:** Provides a fluent API for programmatically adjusting deal config parameters and running what-if scenarios. Used by the Scenario Explorer UI and the `rcm-mc scenario` CLI.

**How it works:** `ScenarioBuilder(base_cfg)` — deep-copies the base config on init. Fluent methods: `adjust_idr(payer, delta)` adjusts initial denial rate by delta (clipped to [0.01, 0.50]), `adjust_fwr(payer, delta)` adjusts final write-off rate, `set_revenue(annual_revenue)` updates hospital revenue, `add_initiative(initiative_id)` applies an initiative's parameter deltas from the library. `build()` returns the modified config dict. All adjustments are recorded in `self._adjustments` for a human-readable diff summary. The builder never mutates the original config — always works on a deep copy.

**Data in:** Base config dict from `infra/config.py`; adjustment calls from the scenario UI or CLI.

**Data out:** Modified config dict passed to `core/kernel.py` for simulation; adjustment log for the scenario label.

---

## `scenario_overlay.py` — Pure-Function Scenario Overlay

**What it does:** Applies multiplicative and additive shocks to distribution parameters in a config. Used to create named scenarios (base / upside / downside) from a single base config.

**How it works:** `apply_overlay(config, overlay_dict)` — deep-copies the config and applies the overlay: multiplicative shocks (e.g., `{"payers.commercial.denials.idr.mean": 0.85}` multiplies the IDR mean by 0.85) and additive shocks (e.g., `{"payers.commercial.dar_clean_days.mean": +5}` adds 5 days). Uses dot-notation path parsing to navigate nested dicts. Returns the overlaid config. Pure function — no side effects, no SQLite writes.

**Data in:** Base config dict; overlay dict with dot-notation paths and shock values.

**Data out:** Overlaid config dict for the scenario simulation.

---

## `scenario_shocks.py` — Preset Payer-Policy Shock Scenarios

**What it does:** Defines preset payer-policy shock scenarios for the Scenario Explorer: Medicare sequestration extension, MA rate cut, Medicaid work-requirement implementation, site-neutral payment cuts, NSA rate reductions.

**How it works:** `_PRESET_SHOCKS` dict maps scenario names to `overlay_dict` structures (for `scenario_overlay.py`). `run_shock_scenario(config, shock_name, n_sims, seed)` — applies the shock overlay, runs MC, returns `ShockResult` with base vs. shocked P10/P50/P90 MOIC distributions and a one-sentence description of the shock assumption. Used by the `/scenarios` UI page to populate the preset scenario comparison panel.

**Data in:** Base deal config; preset shock parameters (hardcoded in the module, updated when new CMS rules take effect).

**Data out:** `ShockResult` for the scenario comparison chart.

---

## Key Concepts

- **Pure config manipulation**: Scenario modules never touch the MC math — they produce modified configs that the standard simulation engine consumes.
- **Fluent builder vs. pure overlay**: `scenario_builder.py` is a stateful fluent API for programmatic construction; `scenario_overlay.py` is a pure function for applying named shocks — both are composable.
- **Preset shocks reflect real policy risk**: The preset shock parameters are calibrated to actual CMS rulemaking impacts, not hypothetical.
