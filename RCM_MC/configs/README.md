# configs/

Configuration templates and seed YAML files. Loaded via `rcm_mc.core.config.load_and_validate(path)`.

| File | What it is |
|------|------------|
| `actual.yaml` | The "actual" deal calibration — partner-entered or analyst-entered values for the deal under review |
| `benchmark.yaml` | The peer-benchmark calibration — bands derived from HCRIS / HFMA / MGMA |
| `initiatives_library.yaml` | The 7 RCM-bridge levers + their priors (median realization, target-conditional adjustments) |
| `playbook.yaml` | Fund-specific playbook — which initiatives this fund tends to run, with realization history |
| `value_plan.yaml` | Value-creation plan template for the workbench's Plan tab |

| Subdirectory | Purpose |
|--------------|---------|
| `scenario_presets/` | Pre-built scenario shocks (rate compression, MA shift, V28 acceleration, recession) |
| `templates/` | Per-archetype hospital templates (community 500M, academic 1.5B, safety-net, etc.) |

## Usage

```python
from rcm_mc.core.config import load_and_validate
cfg = load_and_validate("configs/actual.yaml")
```

Schema validation runs on load — bad YAML fails fast with a clear error.
