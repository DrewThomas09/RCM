# scenarios/

Scenario YAML files — pre-built shocks the analyst can apply on top of the base case from the workbench Scenario tab.

| File | Shock |
|------|-------|
| `commercial_tightening.yaml` | Commercial-payer rate compression of -2% / -3% / -4% over 36 months |
| `management_plan_example.yaml` | Example of an analyst-built management plan stress-test |

## How they're consumed

The `scenarios_page.py` UI reads every YAML in this directory and lets the analyst toggle scenarios on/off. Each toggle re-runs Deal MC with the scenario's modifications layered into the driver distributions. See [`rcm_mc/scenarios/`](../rcm_mc/scenarios/) for the engine that applies these.

To add a new scenario: drop a YAML file here that conforms to the `ScenarioBuilder` schema, then refresh the page.
