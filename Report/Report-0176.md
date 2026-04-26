# Report 0176: Build / CI / CD — `feat/ui-rework-v3` Test Discipline

## Scope

Refresh of CI/CD audit (Reports 0026, 0033, 0041, 0056, 0086, 0101, 0116, 0120, 0143, 0146) — focuses on the `feat/ui-rework-v3` branch's added test discipline.

## Findings

### `feat/ui-rework-v3` test additions (per Report 0157)

| File | LOC |
|---|---|
| `tests/test_ui_rework_contract.py` | +797 (was +675 per Report 0127, grew +122) |
| `tests/test_dev_seed.py` | +209 (NEW per Report 0157) |
| `tests/test_dev_seed_integration.py` | +180 (NEW per Report 0157) |

**+1,186 test LOC across 3 files.**

### "TODO discipline gate"

Per Report 0126 commit `0a747f1`: "Phase 3 — 6 new tests + TODO discipline gate (18→25)." **Branch has explicit TODO-discipline test enforcement.**

Per Report 0165: 7 TODOs in UI_REWORK_PLAN.md (planning, not debt). Discipline gate ensures phase-tracked work has tests.

### CI workflow status (per Report 0116)

**Unchanged**: 4 workflows (ci.yml, deploy.yml, release.yml, regression-sweep.yml). No new workflows added in window.

### Cross-link to Report 0146 pre-commit

Per Report 0146: 8 pre-commit hooks; **all 8 are pre-commit-only**, none in CI (MR813 high). **Status unchanged.**

### Cross-link to Report 0120 deploy.yml

Per Report 0120: deploy.yml on origin/main has auto-deploy ENABLED (the cross-correction). **Deploy is firing on every origin/main push** — except origin/main hasn't moved since Apr 25 (per Reports 0096, 0119, 0126, 0149, 0156).

### `feat/ui-rework-v3` will trigger deploy on merge

When `feat/ui-rework-v3` merges to origin/main, it triggers deploy.yml's `push: branches: [main]`. **Per Report 0157**: branch is forward-mergeable. **Pre-merge check**: ensure secrets are configured.

### NEW finding — branch gate count

Branch contract tests: 25 → 31+ likely (per Report 0127 said 25; Report 0157 grew +122 LOC; estimate 6 new tests = 31).

### Cross-link Report 0143 + 0146 dev extras

Per Reports 0143 + 0146:
- pytest IS used + IS in CI
- pytest-cov IS in `[dev]` but NOT invoked
- ruff IS in pre-commit, NOT in CI
- mypy IS in pre-commit (v1.8.0), NOT in CI

**Status unchanged.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR916** | **`feat/ui-rework-v3` adds 1,186 test LOC across 3 files but tests still NOT in PR-CI 12-file list** | Per Report 0116: PR CI runs only 12 named test files. `test_ui_rework_contract.py` + `test_dev_seed.py` + `test_dev_seed_integration.py` are NOT in that list. **Will only run in weekly regression-sweep**, not on PR. | **Medium** |
| **MR917** | **Branch-merge will trigger auto-deploy** (per Report 0120) | First merge from feat/ui-rework-v3 → main → deploy.yml fires. **Pre-merge check**: AZURE_VM secrets must be set. | High |
| **MR918** | **No CI workflow added for branch's contract tests** | The "TODO discipline gate" runs only locally. CI doesn't enforce. | Medium |

## Dependencies

- **Incoming:** every PR/push, weekly cron.
- **Outgoing:** GitHub Actions runners, Azure VM.

## Open questions / Unknowns

- **Q1.** Are AZURE_VM secrets currently set in repo settings?
- **Q2.** Will feat/ui-rework-v3 merge wait for ci.yml's 12-file subset to pass?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0177** | Schema (in flight). |

---

Report/Report-0176.md written.
