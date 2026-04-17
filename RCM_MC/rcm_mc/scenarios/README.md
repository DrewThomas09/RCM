# Scenarios

What-if scenario modeling: programmatic scenario construction, parameter overlays, and preset payer-policy shock scenarios. Pure config manipulation -- does not modify the Monte Carlo kernel math.

| File | Purpose |
|------|---------|
| `scenario_builder.py` | Fluent API for programmatically adjusting config parameters and running simulated what-if scenarios |
| `scenario_overlay.py` | Pure-function scenario overlay: applies multiplicative and additive shocks to distribution parameters in a config |
| `scenario_shocks.py` | Preset payer-policy shock scenarios for the Scenario Explorer; runs MC under shocked configs and returns EBITDA drag stats |
