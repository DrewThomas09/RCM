# Report 0169: Env-Var Sweep — `ui/_chartis_kit.py`

## Scope

Env-var grep on `RCM_MC/rcm_mc/ui/_chartis_kit.py`. Sister to Reports 0019, 0028, 0042, 0049, 0079, 0090, 0109, 0115, 0118, 0138, 0139.

## Findings

### Env-var inventory (2 reads)

Per `grep -n "os\.environ\|os\.getenv"`:

| Line | Pattern | Env var |
|---|---|---|
| 48 | `_os.environ.get("CHARTIS_UI_V2", "0") != "0"` | `CHARTIS_UI_V2` |
| 63 | `_os.environ.get("RCM_MC_PHI_MODE", "").strip().lower()` | `RCM_MC_PHI_MODE` |

### `CHARTIS_UI_V2` semantics (line 48)

Per Report 0127 baseline: feature-flag for v2 vs v3 UI. Default `"0"` = legacy. Truthy = enable editorial/v2.

**Per Report 0127 + this iteration**: branch `feat/ui-rework-v3` adds `RCM_MC_UI_VERSION` env-var as a sibling. Both coexist on branch.

### `RCM_MC_PHI_MODE` semantics (line 63)

Per Report 0028: PHI redaction mode. `.strip().lower()` ensures defensive parsing.

### What fails if missing

Both env vars have safe defaults (empty string → falsy). **Nothing fails.**

### Cross-link to env-var registry

Per Report 0118 + 0139 + 0151 (~14 env vars): `CHARTIS_UI_V2` was first cited in Report 0127. **Now mapped at source.** **No new env vars discovered this iteration.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR897** | **Two parallel UI-version env vars** (`CHARTIS_UI_V2` legacy + `RCM_MC_UI_VERSION` per feat/ui-rework-v3) | Per Report 0127. Branch coexists with legacy. Onboarding ambiguity post-merge. | Low |

## Dependencies

- **Incoming:** every UI page that imports `_chartis_kit`.
- **Outgoing:** os.environ.

## Open questions / Unknowns

None new.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0170** | Error-handling (in flight). |

---

Report/Report-0169.md written.
