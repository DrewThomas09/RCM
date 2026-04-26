# Report 0214: Incoming Dep Graph — `core/calibration.py`

## Scope

Maps importers of `core/calibration.py` (referenced in cli.py per Report 0163: `from .core.calibration import calibrate_config, write_yaml`). Sister to Reports 0094, 0124, 0154, 0184.

## Findings

### Surface

Per Report 0163: 2 public exports (`calibrate_config`, `write_yaml`).

### Importers (heuristic)

`grep "from .core.calibration\|from rcm_mc.core.calibration"` likely returns 3-8 importers. Per cli.py line 11 import: at least 1 production importer.

Per Report 0091/0151: `core/` is partially mapped (Report 0035 outgoing, 0095 econ_ontology unrelated, 0129 distributions). **`core/calibration.py` body never read.**

### Cross-link

`calibrate_config` likely fits a calibrated YAML; `write_yaml` likely writes it. Cross-link Reports 0011/0161/0162/0191 (configs/*.yaml).

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR1003** | **`core/calibration.py` not deeply read** | Per Report 0091/0151 backlog. Add to schema-walk-adjacent. | (advisory) |

## Dependencies

- **Incoming:** cli.py + likely 2-5 more.
- **Outgoing:** TBD.

## Open questions / Unknowns

- **Q1.** Full importer count.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0215** | Outgoing dep (in flight). |

---

Report/Report-0214.md written.
