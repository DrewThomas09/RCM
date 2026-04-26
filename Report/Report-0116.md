# Report 0116: Build / CI / CD — Full Workflow Inventory

## Scope

Reads all 4 GitHub Actions workflows at `.github/workflows/`. Sister to Reports 0026 (initial CI/CD), 0033 (Dockerfile), 0041 (docker-compose), 0056 (pre-commit), 0086 (entry-points), 0101 (full pyproject).

## Findings

### 4 workflows total

| File | Size | Trigger | Purpose |
|---|---|---|---|
| `ci.yml` | 76 lines | push to main/develop + PR to main + manual | per-PR test + smoke |
| `deploy.yml` | 77 lines | manual only (`workflow_dispatch`) | SSH deploy to Azure VM |
| `regression-sweep.yml` | 184 lines | cron `Mon 08:17 UTC` + manual | weekly full-suite + drift detection |
| `release.yml` | 39 lines | `v*` tags + manual | wheel/sdist build → GitHub Release |

### Workflow 1 — `ci.yml`

**Trigger**: `push: branches: [main, develop]`, `pull_request: branches: [main]`, `workflow_dispatch`.

**Matrix**: Python `["3.11", "3.12", "3.14"]` — **3.10 and 3.13 NOT TESTED** (per Report 0101: pyproject `requires-python = ">=3.10"`, classifiers list 3.10–3.14). **Matrix-vs-pin gap.**

**Jobs**:
1. `actions/checkout@v4` + `actions/setup-python@v5`
2. `pip install -e ".[dev]"` (Report 0101 [dev] extras)
3. **Targeted test subset**: 12 named test files (~160 tests, ~20s per docstring)
4. **Server-boot smoke test**: starts `build_server`, fetches `/health` via urllib

**The 12 test files** (lines 43-56):
- `test_healthz.py`, `test_api_endpoints_smoke.py`, `test_full_pipeline_10_hospitals.py`, `test_readme_links.py`, `test_data_pipeline_resilience.py`, `test_empty_data_resilience.py`, `test_extreme_values_resilience.py`, `test_exports_end_to_end.py`, `test_auth.py`, `test_csrf.py`, `test_portfolio.py`, `test_alerts.py`, `test_health_score.py`

**12 of ~280+ test files** (per Report 0091) — **96% of tests NOT run in PR CI.** Only the weekly regression-sweep.yml runs the full suite.

### Workflow 2 — `deploy.yml`

**Trigger**: `workflow_dispatch` ONLY. Lines 15-16 have the auto-trigger commented out:

```yaml
on:
  # push:
  #   branches: [main]
  workflow_dispatch:
```

**Cross-link Report 0096 commit `3ef3aa3`**: `"ci: fix SSH quoting — use env vars + heredoc for secret expansion"`. That commit fixed something in this file. Auto-deploy still gated off.

**Required secrets** (per docstring lines 5-8): `AZURE_VM_HOST`, `AZURE_VM_USER`, `AZURE_VM_SSH_KEY`. **Not validated**; if missing, run fails late.

**Steps**:
1. `appleboy/ssh-action@v1.0.3` runs script on VM:
   - `git fetch origin main && git reset --hard origin/main`
   - `cd RCM_MC && docker compose -f deploy/docker-compose.yml up -d --build`
   - **Health-check loop**: 12 retries × 5s = up to 60s waiting for `:8080/health`
2. 2nd SSH step — smoke test 3 endpoints: `/health`, `/healthz`, `/api/migrations` (asserts `all_applied: True`).

**`environment: production`** (line 22) — uses GitHub environment-protection rules (manual approval, etc.).

**`git reset --hard origin/main`** is destructive — overwrites any in-flight work on the VM. Per the deploy contract this is intentional.

### Workflow 3 — `regression-sweep.yml`

**Trigger**: cron `17 8 * * 1` (Mon 08:17 UTC, off-the-hour) + manual.

**Permissions**: `contents: read`, `issues: write` (for auto-issue on drift).

**Steps**:
1. **Six-session must-pass**: 8 test files (test_cash_waterfall, test_qoe_memo, test_phi_scanner, test_audit_chain, test_integration_sockets, test_engagement, test_engagement_pages, test_compliance_cli)
2. **Full suite** (continue-on-error): all tests EXCEPT `test_integration_e2e.py` (always ignored)
3. **Extract totals**: parses pytest summary line for fail/pass counts
4. **Compare against baseline**: `BASELINE_FAIL=133` (line 92)
5. **Job summary** to `$GITHUB_STEP_SUMMARY`
6. **Auto-open/update tracking issue** (label `regression-sweep`) on:
   - Six-session module failure, OR
   - `delta > 0` (more failures than baseline)
7. **Upload logs** as artifact (30-day retention)

**Cross-link memory**: `project_test_baseline.md` says "pre-existing 314 failures." This workflow uses `BASELINE_FAIL=133`. **Numbers don't match** — either memory is stale or baseline was reset. Q1 below.

**Cross-link Report 0091 (~280 unmapped tests)**: regression-sweep DOES run them all. ci.yml does not.

### Workflow 4 — `release.yml`

**Trigger**: tag `v*` push + manual.

**Single job**:
1. checkout + Python 3.14 only
2. `pip install build`
3. `python -m build` → wheel + sdist
4. `softprops/action-gh-release@v1` → uploads `RCM_MC/dist/*` to a new GitHub Release with auto-generated notes

**NO PyPI publish.** Only GitHub Release attachment. Cross-link Report 0101 `name = "seekingchartis"` — package not published to PyPI.

**Python 3.14 build only**: wheel may have been built with newer-Python source-only quirks. Pure-Python packages should be fine; if any C/Cython compilation is added later, this becomes problematic. Per Report 0046: numpy is the only native-code dep, and it's runtime not build-time, so safe.

### Cross-cutting findings

#### Python version drift (CI matrix vs pyproject)

| Source | Python versions |
|---|---|
| `pyproject.toml requires-python` | `>=3.10` |
| `pyproject.toml classifiers` | 3.10, 3.11, 3.12, 3.13, 3.14 |
| **`ci.yml` matrix** | **3.11, 3.12, 3.14** (NO 3.10, NO 3.13) |
| `release.yml` | 3.14 only |
| `regression-sweep.yml` | 3.14 only |

**3.10 and 3.13 are claimed-supported but NEVER tested.** **MR656 high.**

#### Coverage / lint absent from CI

Per Report 0101 `[dev]` extras: pytest, pytest-cov, ruff, mypy.

| Tool | In dev extras | Run in CI? |
|---|---|---|
| `pytest` | YES | YES (subset + sweep) |
| `pytest-cov` | YES | **NO** |
| `ruff` | YES | **NO** (only pre-commit per Report 0056) |
| `mypy` | YES | **NO** |

**Coverage and static-analysis are dev-only.** A PR that fails ruff or mypy locally → developer can `--no-verify` and push (cross-link Report 0099 MR543 + Report 0101 MR553). CI does NOT enforce.

#### Secret management

Only `deploy.yml` uses secrets (3: AZURE_VM_HOST/USER/SSH_KEY). No PyPI tokens, no SSH keys for any other service. Compliant with the project's "minimal external integrations" posture.

#### Tests skipped

`test_integration_e2e.py` is ALWAYS ignored:
- `regression-sweep.yml:76`: `--ignore=tests/test_integration_e2e.py`
- Per CLAUDE.md "Running" section: same flag is recommended for local runs (`pytest -q --ignore=tests/test_integration_e2e.py`)

**Q2**: why? The file exists but is never run. Slow / flaky / requires external infra?

#### Deploy contract

Per `deploy.yml`:
- Single Azure VM
- Docker compose is the unit of deploy
- `git reset --hard origin/main` — **state-of-main IS the deploy state**
- No staging environment, no rollback step
- Health-check after deploy; failure leaves the previous container running (compose up -d only replaces on success)

**Single-machine deployment** per CLAUDE.md "Single-machine deployment. No clustering." Confirmed.

### Comparison to Report 0026

Report 0026 noted: ci.yml + workflow setup. This report adds:
- 3 more workflows (deploy, regression-sweep, release)
- The 12-test subset breakdown
- The 133-baseline finding
- The Python-version drift finding
- The auto-deploy disabled finding

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR656** | **Python 3.10 + 3.13 claimed-supported but NEVER TESTED in any workflow** | pyproject classifiers list them; users on those versions may hit untested code paths. | **High** |
| **MR657** | **PR CI runs only 12 of ~280 test files** | 96% of tests are not gated by PR. A breaking change in the un-tested 268 files merges with green CI. Weekly regression-sweep is the only safety net. | **High** |
| **MR658** | **No ruff / mypy in any CI job** | Pre-commit catches locally but `--no-verify` bypasses. CI does NOT enforce static-analysis. Cross-link Reports 0099, 0101. | **Medium** |
| **MR659** | **No `pytest-cov` invocation in any workflow** | `pytest-cov` is in `[dev]` extras but never run. Coverage measurement is local-only. | Medium |
| **MR660** | **`deploy.yml` auto-trigger commented out** (lines 15-16) | Per the docstring, this is intentional — manual-only until verified. But "intentional" without a reminder TODO drifts to "permanently manual." Cross-link Report 0105 (TODO discipline). | Low |
| **MR661** | **`regression-sweep.yml BASELINE_FAIL=133` vs memory `project_test_baseline.md` "314 failures"** | Numbers conflict. Either baseline drifted, memory stale, or two distinct counts (one with `--ignore=test_integration_e2e`). | Medium |
| **MR662** | **`test_integration_e2e.py` always ignored — never run anywhere** | Test file exists but is structurally orphan. Per Report 0010 orphan-file pattern. Either delete or revive. | **Medium** |
| **MR663** | **`release.yml` builds wheel with 3.14 only** | If a new C-extension dep is added, wheel may not work on 3.10/3.11/3.12. Pure-Python works today. Future-risk. | Low |
| **MR664** | **`release.yml` does NOT publish to PyPI** | Per Report 0101: `name = "seekingchartis"` is the distribution name. Releases are GitHub-attachments only. Limits sharing. | Low |
| **MR665** | **`appleboy/ssh-action@v1.0.3` is third-party action** | Pinned to specific version (good). Supply-chain risk: action could be hijacked. Worth periodic verification. | Low |
| **MR666** | **`deploy.yml` `git reset --hard origin/main`** | Destructive — wipes any in-flight VM-side work. Per deploy contract this is intentional, but a reminder comment in the file would help. | Low |
| **MR667** | **No CI test for `[api]` install path** (Report 0113 follow-up Q3) | The fastapi/uvicorn alternative entry-point is never tested in CI. Could be silently broken. | Medium |

## Dependencies

- **Incoming:** every PR/push, Monday cron, every `v*` tag.
- **Outgoing:** GitHub Actions runners, Azure VM (deploy), GitHub Issues API (regression-sweep), `softprops/action-gh-release`, `appleboy/ssh-action`.

## Open questions / Unknowns

- **Q1.** Why does `regression-sweep.yml` have `BASELINE_FAIL=133` but memory says "314"? Were 181 tests fixed without baseline update?
- **Q2.** What's in `test_integration_e2e.py` and why is it always-ignored? Slow / flaky / external-dep?
- **Q3.** Has the deploy.yml workflow successfully run since the SSH-quoting fix (`3ef3aa3`)?
- **Q4.** Is the release.yml wheel pure-Python (no compiled extensions)? If so, 3.14-built wheel works for 3.10+.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0117** | Read `tests/test_integration_e2e.py` head — closes Q2 + MR662. |
| **0118** | Schema-walk `mc_simulation_runs` (Report 0110 backlog). |
| **0119** | Read `_route_quick_import_post` (Report 0114 MR639 confirmation). |
| **0120** | Audit `vendor/ChartisDrewIntel/.github/workflows/` (a SECOND workflows directory found this iteration). |

---

Report/Report-0116.md written.
Next iteration should: read `tests/test_integration_e2e.py` head — closes Q2 (why always-ignored) + MR662 medium.
