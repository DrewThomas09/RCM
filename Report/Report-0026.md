# Report 0026: Build / CI / CD Audit — `.github/workflows/`

## Scope

This report covers **every GitHub Actions workflow** in `.github/workflows/` on `origin/main` at commit `f3f7e7f`. Audit lists each job, what it runs, what it gates, and flags failing / skipped / never-run steps.

The repo has **no Makefile** (`find . -maxdepth 3 -name "Makefile"` returns empty), no `Justfile`, no `tox.ini` — CI lives entirely in GitHub Actions YAML.

This audit was suggested as a follow-up in Reports 0001 (Q3), 0007 (MR51), and elsewhere; finally landing it.

Prior reports reviewed before writing: 0022-0025.

## Findings

### Workflow inventory (4 files, 372 lines total)

| File | Lines | Role |
|---|---:|---|
| `.github/workflows/ci.yml` | 75 | Per-push / per-PR test suite |
| `.github/workflows/deploy.yml` | 76 | Azure VM SSH-based deploy |
| `.github/workflows/regression-sweep.yml` | 183 | Weekly full-suite cron job |
| `.github/workflows/release.yml` | 38 | Tag-triggered wheel build + GitHub Release |

All workflows declare `defaults: run: working-directory: ./RCM_MC` (where pyproject.toml lives). Repo-root files (`README.md`, `AZURE_DEPLOY.md`, `FILE_INDEX.md`) hold no Python; the working-directory shift is correct.

### `ci.yml` — Continuous Integration (75 lines)

#### Triggers (lines 3-8)

```yaml
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  workflow_dispatch:
```

- `push` to `main` or `develop`. **Note:** `develop` is not in the branch register (Report 0006) — it doesn't exist on origin. So this trigger fires on push to main only.
- `pull_request` targeting `main`. Fires on every PR opened against main.
- `workflow_dispatch` — manual trigger.

#### Jobs

**Job 1: `test`** (line 18)

- `runs-on: ubuntu-latest`.
- **Matrix:** Python `3.11`, `3.12`, `3.14` (line 23). **Skips 3.10 and 3.13.**
  - 3.10 is the minimum per `pyproject.toml:10` `requires-python = ">=3.10"` — should be in the matrix.
  - 3.13 is a stable version the project claims to support (`classifiers` line 20 lists 3.13).
  - **Gap.** Tests on 3.11/3.12/3.14 alone may pass while 3.10/3.13 break. Cross-link Report 0003 (classifiers list 3.10 through 3.14).
- `fail-fast: false` (line 21) — all matrix entries run independently. Good.

**Steps (lines 25-75):**

| Step | Action |
|---|---|
| Checkout | `actions/checkout@v4` |
| Set up Python | `actions/setup-python@v5` |
| Install deps | `pip install -e ".[dev]"` — installs core + `[dev]` extras only. **Does NOT install `[all]`, `[exports]`, or `[diligence]` extras.** |
| Run go-live test subset | A hand-curated list of 13 test files (lines 43-56) — `test_healthz.py`, `test_api_endpoints_smoke.py`, `test_full_pipeline_10_hospitals.py`, `test_readme_links.py`, `test_data_pipeline_resilience.py`, `test_empty_data_resilience.py`, `test_extreme_values_resilience.py`, `test_exports_end_to_end.py`, `test_auth.py`, `test_csrf.py`, `test_portfolio.py`, `test_alerts.py`, `test_health_score.py`. |
| Smoke-test server boot + /health | An inline Python script (lines 58-75) that imports `rcm_mc.server`, calls `build_server`, hits `http://127.0.0.1:<port>/health`, asserts response is `200 OK` with body `"ok"`. |

**Test-coverage analysis:**

- **CI runs ~13 of the ~459 test files** (per Report 0002). The comment on line 39 says "~160 tests, ~20s". The full suite is per Reports 0006 + 0008 around 4,000+ tests. **CI gates on ~4% of the test surface.**
- Test selection is biased toward smoke + auth + exports + resilience. **Heavy modules like `test_packet_builder.py`, `test_simulator.py`, `test_distributions.py`, `test_lookup.py`, `test_intake.py`, `test_state_regulatory.py`, `test_provenance_graph.py`** — none in the CI gate.
- **The `test_data_public_smoke.py` regression harness** (Report 0008 / 0007 / 0014 / etc. — 2,883 tests at one point, 4,286 at another) is **NOT in the CI gate.**

**Smoke test (lines 58-75) — inline Python:**

- Hard-codes `host='127.0.0.1'`, `port=0` (random port).
- 0.5s sleep before probing — race-prone but typically OK.
- Asserts `body == 'ok'`. The /health route must return exactly `'ok'` — Report 0018 didn't enumerate the body, but this assertion pins it.
- No teardown of the threading thread after `server.shutdown()`. Test exits before thread joins. Acceptable for CI but leaks a daemon.
- **No `RCM_MC_AUTH` set** — confirms /health doesn't need auth (matches `server.py:1700` per Report 0018).

#### What ci.yml gates

- Pull requests against `main` cannot be merged unless this workflow passes (assuming branch-protection rules; not visible in YAML).
- Direct push to `main` triggers the workflow but doesn't *gate* the push (push already happened).

### `deploy.yml` — Azure VM Deploy (76 lines)

#### Triggers (lines 14-17)

```yaml
on:
  # push:
  #   branches: [main]
  workflow_dispatch:
```

**The `push` trigger is COMMENTED OUT.** Lines 14-17:

```yaml
on:
  # push:
  #   branches: [main]
  workflow_dispatch:
```

**This means deploy NEVER runs automatically.** Only manual triggers via the GitHub Actions UI. The comment at lines 1-12 explains:

> "This workflow is gated to manual-trigger-only (`workflow_dispatch`) until the following GitHub Secrets are configured: AZURE_VM_HOST, AZURE_VM_USER, AZURE_VM_SSH_KEY. Once secrets are set and you've verified one manual deploy succeeds, uncomment the `push: branches: [main]` block below to enable auto-deploy on every push to main."

**Status: PERMANENTLY MANUAL.** Cannot determine from the YAML alone whether the secrets have ever been set; only manual triggers ever run this workflow.

#### Jobs

**Job: `deploy`** (line 20)

- `runs-on: ubuntu-latest`
- `environment: production` — uses GitHub's environments feature (potentially with required reviewers, branch restrictions, etc. — not visible in YAML).
- 2 steps:
  1. **Deploy via SSH** (line 25-55): `appleboy/ssh-action@v1.0.3` runs SSH commands on the Azure VM. Pulls latest from origin/main, runs `docker compose -f deploy/docker-compose.yml up -d --build` from `/opt/rcm-mc/RCM_MC/`. Health-checks `http://localhost:8080/health` for up to 60s.
  2. **Smoke test** (line 57-76): another `appleboy/ssh-action` block. Calls `/health`, `/healthz`, `/api/migrations` on the VM. Asserts migrations are all applied via Python one-liner.

**Issues:**

- `git fetch origin main && git reset --hard origin/main` (lines 36-37) — **destructive**. Any local commits or uncommitted changes on the VM are wiped. Acceptable for a stateless deploy target; risky if anyone manually changes anything on the VM.
- Uses **THIRD-PARTY action** `appleboy/ssh-action@v1.0.3` (twice). Pinning at `@v1.0.3` is good. **Marketplace third-party action**; supply-chain risk unless the version is verified.
- Smoke test references both `/health` AND `/healthz` (line 68-69). Per Report 0019 MR142, `feature/workbench-corpus-polish` removes `/healthz` — would fail this smoke test if merged.
- Smoke test references `/api/migrations` (line 72) — an endpoint that returns JSON with `all_applied` field. Per Report 0017, the migration registry is at `infra/migrations.py`; the endpoint is presumably wired in `server.py` but not yet enumerated.

### `regression-sweep.yml` — Weekly Cron (183 lines)

#### Triggers (lines 21-25)

```yaml
on:
  schedule:
    - cron: "17 8 * * 1"     # Monday 08:17 UTC
  workflow_dispatch:
```

- `cron: "17 8 * * 1"` — every Monday at 08:17 UTC.
- Manual trigger.

#### Jobs

**Job: `sweep`** (line 37)

- `runs-on: ubuntu-latest`
- `timeout-minutes: 30` — cap on runtime.
- 7 steps:

| Step | Behavior |
|---|---|
| Checkout + Python 3.14 + install `[dev]` | Standard setup. **Same `[dev]`-only install as ci.yml**. |
| **Run six-session modules (must all pass)** | 8 specific test files: `test_cash_waterfall.py`, `test_qoe_memo.py`, `test_phi_scanner.py`, `test_audit_chain.py`, `test_integration_sockets.py`, `test_engagement.py`, `test_engagement_pages.py`, `test_compliance_cli.py`. Captures exit code. |
| **Run full suite** (`if: always()`, `continue-on-error: true`) | `pytest --ignore=tests/test_integration_e2e.py -q --tb=line` with `\| tee full_sweep.log \|\| true`. **Always succeeds** (the `\|\| true` swallows any failure). The actual fail/pass count is parsed from the log. |
| **Extract totals** | Parses `full_sweep.log` for the final `==== N passed, M failed ====` line. Computes `delta = FAIL_COUNT - 133` (the "baseline" set at ship time per line 18-19). |
| **Write job summary** | Writes a Markdown summary to `$GITHUB_STEP_SUMMARY`. |
| **Flag drift via tracking issue** | If six-session failed OR delta > 0, opens or updates an issue labeled `regression-sweep` via `actions/github-script@v7`. |
| **Upload logs as artifact** | 30-day retention for `six_session.log` + `full_sweep.log`. |

**Hardcoded baseline of 133 failures** (line 92, line 18-19 comment): "Known baseline at the time of shipping: 133 pre-existing failures across the pre-existing UI-v2 test files."

**This is a known-failing baseline.** The sweep flags drift only when failures exceed 133. Per Report 0008's broader sweep result of 314 fail / 4286 pass on `feature/deals-corpus`, the trunk's failure count may differ from 133. **The baseline is hand-coded and likely stale.**

**The eight "six-session" tests are the actual gate.** If any of those 8 fails, the issue auto-opens. The full-suite numbers are advisory.

### `release.yml` — Tag-Triggered Build (38 lines)

#### Triggers (lines 3-7)

```yaml
on:
  push:
    tags:
      - "v*"
  workflow_dispatch:
```

- Triggered when a tag matching `v*` is pushed.
- **Per Report 0006: NO tags exist on origin.** This workflow has never fired.

#### Job: `build-and-publish` (line 15)

- `runs-on: ubuntu-latest`
- `permissions: contents: write` — needs write access to create a release.
- Steps:
  1. Checkout
  2. Set up Python 3.14
  3. `pip install build`
  4. `python -m build` — produces wheel + sdist in `RCM_MC/dist/`
  5. `softprops/action-gh-release@v1` — creates a GitHub Release with `files: RCM_MC/dist/*` and `generate_release_notes: true`

**Issues:**

- **No PyPI publish step.** Only creates a GitHub Release with the wheel/sdist attached. To publish to PyPI, would need a `twine upload` step + `PYPI_API_TOKEN` secret. The package name `seekingchartis` (per Report 0003) is presumably reserved on PyPI but not auto-published.
- **Build runs from `RCM_MC/`** (defaults clause). `python -m build` writes to `RCM_MC/dist/`. The release-action then uploads `RCM_MC/dist/*`.
- **No version validation.** Tag `v0.6.1` doesn't have to match `pyproject.toml:7 version = "1.0.0"`. **3-way version drift per Report 0003 MR15** is unresolved here too — a tagged release ships whatever pyproject says, regardless of the tag value.

### Summary table

| Workflow | Trigger | Status | Gates |
|---|---|---|---|
| `ci.yml` | push main, PR to main, manual | **Active.** Runs ~13/459 test files + smoke. | PR merge to main (assuming branch protection). |
| `deploy.yml` | manual ONLY (push trigger commented out) | **Permanently manual.** Auto-deploy gated behind secret config. | Production deploys. |
| `regression-sweep.yml` | weekly cron Mon 08:17 UTC, manual | **Active.** Runs 8 six-session tests + full suite. | Auto-opens GitHub issue on drift. |
| `release.yml` | tag push (v*), manual | **Never fired** (zero tags per Report 0006). | GitHub release artifact. |

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR222** | **CI runs only ~13 of ~459 test files** (~4% of surface) | A regression in any non-go-live test file passes CI silently. The full sweep runs only weekly. **An entire week of broken commits can land on main before the sweep flags drift.** | **High** |
| **MR223** | **Python version matrix is 3.11 / 3.12 / 3.14 — skips 3.10 and 3.13** | `pyproject.toml:10` declares `requires-python = ">=3.10"` and classifiers list 3.10 through 3.14. Skipping 3.10 means a 3.10-incompatible feature (e.g. `match` statement, structural pattern matching nuances, `int.bit_count()`) ships. Skipping 3.13 misses a stable production target. | **High** |
| **MR224** | **`deploy.yml` push trigger is commented out** | Auto-deploy never fires. Every deploy requires a manual `workflow_dispatch`. **Effective deploy frequency depends on operator memory.** Operators may forget to deploy after merging a fix. | **High** |
| **MR225** | **`deploy.yml` references `/healthz` but `feature/workbench-corpus-polish` removes it** (cross-link Report 0019 MR142) | Pre-merge: if that branch lands, the deploy smoke test fails on the second curl. Either the workflow updates first or the route stays. | **Critical** |
| **MR226** | **`regression-sweep.yml` baseline of 133 is hand-coded and likely stale** | Line 92 hardcodes `BASELINE_FAIL=133`. Reports 0006/0008 measured 314 fail at one point. **The drift detector under-reports current failures or over-reports drift depending on which way the baseline is wrong.** Recommend: rebase the baseline with each merge, or store baseline in a versioned file. | **High** |
| **MR227** | **Six-session test list is also hand-curated and could go stale** | 8 specific tests (lines 59-66 of regression-sweep.yml) and 13 specific tests (lines 44-56 of ci.yml). When a new must-pass module ships, the lists need updating. **Pre-merge: any branch that adds critical tests must update both YAMLs.** | Medium |
| **MR228** | **`release.yml` has never fired — no tags on origin** (cross-link Report 0006 MR41) | The release pipeline is theoretical. First tag attempt may surface bugs (wheel build, dist path, action-gh-release version). | Medium |
| **MR229** | **`pip install -e ".[dev]"` skips other extras** | Both `ci.yml:36` and `regression-sweep.yml:52` install only `[dev]`. **Tests that exercise `[exports]` (xlsx export — covered by `test_exports_end_to_end.py`), `[diligence]` (rcm_mc_diligence package — likely tested separately), `[api]` (FastAPI — orphan per Report 0010) are not exercised.** | **High** |
| **MR230** | **`appleboy/ssh-action@v1.0.3` is a third-party Marketplace action** | Supply-chain risk. v1.0.3 is pinned (good); but the action source code could be replaced upstream. Recommend: pin to a specific commit SHA instead of a version tag. | Medium |
| **MR231** | **Deploy uses `git reset --hard origin/main`** | Wipes any local state on the VM. Acceptable for stateless deploy; if anyone manually edits files on the VM (config, certs), they're lost on next deploy. | Low |
| **MR232** | **No PyPI publish step in `release.yml`** | The package name `seekingchartis` exists in `pyproject.toml` but the release flow only attaches artifacts to a GitHub Release. **Users cannot `pip install seekingchartis` from PyPI** even after a tagged release. | Low |
| **MR233** | **`release.yml` doesn't validate that the tag matches `pyproject.toml`'s version** | A `v2.0.0` tag with `pyproject.toml version = "1.0.0"` produces a `seekingchartis-1.0.0.whl` named under a v2 release. **Confusing.** | Medium |
| **MR234** | **No `requirements-lock.txt` step in any workflow** (cross-link Reports 0016 / 0023) | CI installs whatever pip resolves at install time. Different runs may install slightly different versions of transitive deps. **Reproducibility weak.** | Medium |
| **MR235** | **No coverage thresholds** | `pytest-cov` is in `[dev]` extras (per Report 0023) but never invoked. CI doesn't measure or gate on coverage. | Medium |
| **MR236** | **No security scanning workflow** | No CodeQL, no `bandit`, no `pip-audit`, no `safety`. Per Report 0021's manual security audit, the auth surface looks clean — but that's by hand. | **High** |
| **MR237** | **`feature/workbench-corpus-polish` deletes 3 root workflows + adds 1 inside `RCM_MC/`** (Report 0007 MR51) | If that branch lands, `.github/workflows/` at root would be empty (or near-empty), breaking trigger paths. **GitHub Actions only triggers off the repo-root `.github/workflows/`** — `RCM_MC/.github/` would silently disable CI. | **Critical** |

## Dependencies

- **Incoming (who depends on the workflows):** branch-protection rules on `main` (gating PR merge); operators (manual deploys); the weekly cron and the issue-tracker; tag-pushers (theoretical).
- **Outgoing:** GitHub Actions runners (ubuntu-latest); third-party actions (`actions/checkout@v4`, `actions/setup-python@v5`, `actions/upload-artifact@v4`, `softprops/action-gh-release@v1`, `appleboy/ssh-action@v1.0.3`, `actions/github-script@v7`); the `RCM_MC/pyproject.toml` for dep resolution; the `RCM_MC/tests/` for test files.

## Open questions / Unknowns

- **Q1 (this report).** What branch-protection rules are configured on `main`? Without seeing the GitHub repo settings, we don't know whether ci.yml is *required* for PR merge or just *informational*.
- **Q2.** Have the deploy secrets (`AZURE_VM_HOST`, `AZURE_VM_USER`, `AZURE_VM_SSH_KEY`) been set? The deploy workflow can't determine this from YAML alone.
- **Q3.** Has the regression-sweep cron actually fired? If yes, are there issues labeled `regression-sweep` in the repo? If no (e.g. cron disabled at GitHub level), the weekly safety net doesn't exist.
- **Q4.** Is the Python 3.14 matrix actually executable on `ubuntu-latest`? GitHub's `setup-python` may default to the latest available — if 3.14 isn't yet in the cache, the workflow may fall back to 3.13 silently.
- **Q5.** Why is `develop` in `ci.yml`'s push triggers when no `develop` branch exists?
- **Q6.** What does `/api/migrations` return? It's tested in deploy.yml smoke but not yet enumerated in any report.
- **Q7.** Does any feature branch update the regression-sweep baseline (133 failures) or the six-session test list?
- **Q8.** How long does the full sweep actually take? Reports 0006/0008 had 10:46 (646s) for the broader sweep — under the 30-min timeout but close.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0027** | **Audit `tests/test_healthz.py`** — the most CI-gated test. | Single-file deep dive on the gate. |
| **0028** | **Audit `RCM_MC/deploy/Dockerfile` + `docker-compose.yml`** — used by deploy.yml step 1. (Owed since Report 0019 / 0023.) | Closes the deploy stack picture. |
| **0029** | **Cross-branch workflow diff** — does any ahead-of-main branch modify `.github/workflows/`? Resolves MR237 cross-link. | Catches the polish-branch's `.github/` move (Report 0007 MR51). |
| **0030** | **Add `pip-audit` / `bandit` / CodeQL workflow recommendation** | Mitigates MR236. |
| **0031** | **Update CI matrix to include 3.10 + 3.13** | Mitigates MR223. |
| **0032** | **Audit `tests/test_full_pipeline_10_hospitals.py`** — the largest item in CI go-live subset. | Tells us what the gate actually validates. |
| **0033** | **Audit `infra/notifications.py` SMTP integration** — sister external integration owed since Report 0019. | Companion. |

---

Report/Report-0026.md written. Next iteration should: read `RCM_MC/deploy/Dockerfile` + `RCM_MC/deploy/docker-compose.yml` to determine the production runtime container — closes Report 0023 Q1 and tells us whether `pip install -e ".[diligence]"` (or any specific extras) actually runs in production, completing the deploy/CI/build picture.

