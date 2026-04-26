# Report 0199: Env-Var Sweep — `rcm_mc_diligence/cli.py`

## Scope

`RCM_MC/rcm_mc_diligence/cli.py` (252 LOC per Report 0122) — env-var sweep on the separate-package CLI. Sister to Reports 0019, 0028, 0042, 0049, 0079, 0090, 0109, 0115, 0118, 0138, 0139, 0169.

## Findings

### Env-var inventory — ZERO

`grep -n "os\.environ|os\.getenv"`: **0 hits.**

**`rcm_mc_diligence/cli.py` is env-var-FREE.** 252 LOC of CLI without any environment variable read.

### Cross-link to Report 0122

Per Report 0122: rcm_mc_diligence is "strictly additive to rcm_mc; imports nothing from it and vice versa." Independent versioning + design.

### Cross-link to Report 0145 dbt invocation

Per Report 0145: dbt-core programmatic API is invoked. Profiles file (`profiles.yml`) carries credentials. **No env-var injection at the `cli.py` level.**

### Comparison to `rcm_mc/cli.py` (Report 0139)

| Module | Lines | Env vars |
|---|---|---|
| `rcm_mc/cli.py` (Report 0139) | 1252 | 1 (`RCM_MC_NO_PORTFOLIO`) |
| **`rcm_mc_diligence/cli.py` (this)** | **252** | **0** |

**Both CLIs are nearly env-var-free.** Args-only configuration. **Strong CLI hygiene.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR974** | **`rcm_mc_diligence/cli.py` is env-var-FREE** | Clean — argparse-only. | (clean) |

## Dependencies

- **Incoming:** `rcm-mc-diligence` console script per Report 0086.
- **Outgoing:** stdlib argparse + sibling diligence modules.

## Open questions / Unknowns

None new.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0200** | Error handling (in flight). |

---

Report/Report-0199.md written.
