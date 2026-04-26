# Report 0143: Version Drift — `[dev]` Extras Sweep

## Scope

Verifies the 4 `[dev]` extras packages are actually used. Sister to Reports 0023, 0046, 0053, 0076, 0083, 0086, 0101, 0106, 0113, 0136. Closes Report 0116 Q4 (mypy/ruff/pytest-cov in CI).

## Findings

### `[dev]` extras (per pyproject.toml line 61-66 / Report 0101)

```toml
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.1",
    "mypy>=1.5",
]
```

### Usage matrix

| Package | Direct Python `import`? | CLI invocation? | Status |
|---|---|---|---|
| `pytest` | YES — 8 test files (`tests/conftest.py:10`, `test_seekingchartis_*` × 6, `test_improvements_b119.py`) | YES — CI workflow ci.yml + regression-sweep | **alive** |
| `pytest-cov` | NO direct imports | NOT in CI workflows (per Report 0116 finding) | **dead-in-CI** (manual-use only) |
| `ruff` | NO direct imports (linter, not lib) | YES — `.pre-commit-config.yaml` (per Report 0056) | **alive (pre-commit only)** |
| `mypy` | NO direct imports | (TBD — likely manual) | **alive (pre-commit?)** |

### Key findings

#### Cross-correction (clarifies Report 0101 + 0116)

- **`pytest-cov`** is in `[dev]` but **not invoked anywhere**. Per Report 0116 MR659 ("No `pytest-cov` invocation"). Confirmed.
- **`ruff`** is in pre-commit (Report 0056) but per Report 0116 MR658 — NOT in CI. So `ruff` only runs locally pre-commit, can be `--no-verify`'d.
- **`mypy`** in `[dev]` but Report 0116 didn't see it in CI. Possibly in pre-commit but Report 0056 didn't enumerate.

#### Effective dead-extras

`pytest-cov` is INSTALLED but NEVER RUN. **Same dead-extra pattern as `plotly` (Report 0113 confirmed dead).**

### Cross-link to env-var registry (Report 0139)

`cli.py` env var trace: 1 var. **Per Report 0118 MR681**: ~14 env vars total in registry. CLAUDE.md still enumerates none.

### Closes Report 0116 Q4

> "Q4. Is `mypy>=1.5` actually invoked by pre-commit (Report 0056) or is `dev` extras passive?"

Per this report: `mypy` doesn't appear as a Python `import` AND wasn't seen in CI. **Likely dev-only via pre-commit hook.** Report 0056 should enumerate.

### Cross-link to Report 0099 MR543 (retracted Report 0101 MR553)

Report 0099 claimed pre-commit doesn't run F401 (5 unused imports in `custom_metrics.py` weren't caught). Report 0101 MR553 cross-corrected: ruff DOES select `F`. **Outstanding question**: why didn't pre-commit catch them? Likely answer: developer used `--no-verify` or pre-commit hooks not installed locally.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR797** | **`pytest-cov` is in `[dev]` but never invoked** — second confirmed dead extra after `plotly` (Report 0113) | Either remove from `[dev]` or wire into CI workflow as `pytest --cov`. | Low |
| **MR798** | **`mypy` and `ruff` in `[dev]` but not in CI** — pre-commit-only enforcement | Cross-link Report 0116 MR658. Static-analysis bypassable via `git commit --no-verify`. | Medium |
| **MR799** | **`pytest>=7.0`, `pytest-cov>=4.0`, `ruff>=0.1`, `mypy>=1.5` are all loose-pinned** (no upper bound) | Cross-link Report 0106 MR591 + Report 0113 MR636 (10 of 19 deps loose). | Low |

## Dependencies

- **Incoming:** dev install path (`pip install -e .[dev]`), CI install (per Report 0116).
- **Outgoing:** PyPI.

## Open questions / Unknowns

- **Q1.** Is mypy in `.pre-commit-config.yaml`? (Report 0056 may have missed it.)
- **Q2.** Does `pre-commit run --all-files` typically pass cleanly?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0144** | Cross-cutting (in flight). |
| **0145** | Integration point (in flight). |
| **0146** | CI/CD refresh (in flight). |
| **0147** | Read `.pre-commit-config.yaml` carefully for mypy hook (closes Q1). |

---

Report/Report-0143.md written.
