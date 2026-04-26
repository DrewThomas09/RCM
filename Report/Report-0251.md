# Report 0251: Config Map — `pyproject.toml`

## Scope

Full key-by-key audit of `RCM_MC/pyproject.toml` (126 lines). First report to enumerate the project's build/install/CLI/test/lint config in one place. Sister to Reports 0027 (ServerConfig), 0085 (broader env-var pass), 0184 (CI workflows).

## Findings

### `[build-system]` (lines 1-3)

- `requires = ["setuptools>=68.0", "wheel"]`
- `build-backend = "setuptools.build_meta"`

Standard setuptools. **No reads in code** — consumed by `pip` only.

### `[project]` (lines 5-24)

| Key | Value | Read by |
|---|---|---|
| `name` | `"seekingchartis"` | pip metadata (cross-link Report 0250 — top-level `seekingchartis.py` matches name) |
| `version` | `"1.0.0"` | pip metadata. **Note:** CLAUDE.md does not state a version; cross-link `rcm_mc.__version__` likely defined separately in `rcm_mc/__init__.py`. **Q1.** |
| `description` | "SeekingChartis — Healthcare PE Diligence Platform" | pip metadata |
| `readme` | `"README.md"` | pip |
| `requires-python` | `">=3.10"` | pip; **conflicts with CLAUDE.md "Python 3.14"** — pyproject says any 3.10+ but CLAUDE.md targets 3.14 |
| `license` | `{text = "Proprietary"}` | pip |

### `[project] dependencies` (lines 26-32) — runtime deps

| Pkg | Pin | Note |
|---|---|---|
| `numpy` | `>=1.24,<3.0` | pe_math, mc, ml |
| `pandas` | `>=2.0,<4.0` | data_public, ingest |
| `pyyaml` | `>=6.0,<7.0` | playbook.yaml, actual.yaml, benchmark.yaml |
| `matplotlib` | `>=3.7,<4.0` | charts |
| `openpyxl` | `>=3.1,<4.0` | xlsx export — **also listed in `[exports]` extras** (duplicate intent) |

### `[project.optional-dependencies]` (lines 34-66)

| Group | Pkgs | Note |
|---|---|---|
| `interactive` | plotly>=5.0 | optional charting |
| `pptx` | python-pptx>=0.6 | duplicates `exports` |
| `exports` | python-pptx + openpyxl | overlaps `pptx` and core dep |
| `api` | fastapi>=0.100, uvicorn>=0.23 | cross-link Report 0113 (api.py) |
| `diligence` | duckdb, dbt-core, dbt-duckdb, **pyarrow>=10.0** | cross-link Report 0101 / pyarrow CVE-2023-47248 (MR770) |
| `all` | openpyxl, plotly, python-pptx, fastapi, uvicorn, **scipy>=1.11** | cross-link Report 0113 retraction (scipy used) |
| `dev` | pytest>=7.0, pytest-cov, ruff>=0.1, mypy>=1.5 | **mypy>=1.5 conflicts with pre-commit pinning at v1.8.0** (Report 0184) |

### `[project.scripts]` (lines 68-72) — CLI entry-points

| Script | Module | Status |
|---|---|---|
| `rcm-mc` | `rcm_mc.cli:main` | OK — `rcm_mc/cli.py` exists (Report 0163) |
| `rcm-intake` | `rcm_mc.intake:main` | **BROKEN.** `rcm_mc/intake.py` does NOT exist. Module is at `rcm_mc/data/intake.py` (line 619 has `main()`). **No back-compat shim.** |
| `rcm-lookup` | `rcm_mc.lookup:main` | OK — `rcm_mc/lookup.py` exists as back-compat shim that delegates to `rcm_mc/data/lookup.py` |
| `rcm-mc-diligence` | `rcm_mc_diligence.cli:main` | OK — package exists |

### Critical finding — `rcm-intake` entry-point is broken

`pyproject.toml:70` references `rcm_mc.intake:main`. **No file at that path.** Confirmed by `ls`:

```
/Users/drewthomas/dev/RCM_MC/RCM_MC/rcm_mc/intake.py: No such file or directory
```

The actual `main()` function lives at `rcm_mc/data/intake.py:619`. `rcm_mc/lookup.py` is a back-compat shim that follows the **same pattern** that `intake.py` is missing. **Likely missed during the data/ refactor that moved `intake.py` → `data/intake.py`.**

After `pip install`, invoking `rcm-intake` would raise `ModuleNotFoundError: No module named 'rcm_mc.intake'`.

**Cross-link `tests/test_cli_dispatcher.py:141`** which says `rcm-intake and rcm-lookup remain functional as aliases (one-release deprecation window)` — but `rcm-intake` is **NOT functional** because the shim is missing. Test may fail in CI on a fresh install.

### `[tool.setuptools.packages.find]` (line 74-75)

`include = ["rcm_mc*", "rcm_mc_diligence*"]` — wheel will package both top-level packages. **`rcm_mc_diligence/` confirmed as separate co-resident package** per Report 0156-region knowledge.

### `[tool.setuptools.package-data]` (lines 77-85)

- `rcm_mc = ["data/*.csv.gz"]` — gzipped CSVs ship with the wheel.
- `rcm_mc_diligence` — 5 entries (dbt project, packages.yml, profiles.example.yml, models/**/*.sql, models/**/*.yml). Cross-link Report 0150 secret coverage MR829 ("`profiles.yml` not gitignored") — **here it's `profiles.example.yml` (clean) being shipped**, but real `profiles.yml` may exist alongside.

### `[tool.pytest.ini_options]` (lines 87-110)

- `testpaths = ["tests"]`
- `addopts = "-v --tb=short"` — verbose by default
- 6 markers: `api`, `ui`, `store`, `security`, `integration`, `slow`
- 2 `filterwarnings` ignores for `ResourceWarning` from ThreadingHTTPServer (documented)

### `[tool.ruff]` (lines 112-118)

- `line-length = 120`
- `target-version = "py310"` — **conflicts with project `requires-python = ">=3.10"` partially OK, but conflicts with CLAUDE.md's Python 3.14 target**
- `select = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]`
- `ignore = ["E501", "RUF012"]` — line-length + mutable-class-attrs

### `[tool.mypy]` (lines 120-126)

- `python_version = "3.10"` — same conflict
- `warn_return_any = true`
- `warn_unused_configs = true`
- `warn_unused_ignores = true`
- `strict_optional = true`
- `ignore_missing_imports = true`

### Cross-corrections

- **CLAUDE.md says Python 3.14 but pyproject targets 3.10.** Three internal stops at 3.10: `requires-python`, `tool.ruff.target-version`, `tool.mypy.python_version`. **Source of truth ambiguity.** Cross-link Report 0249 MR1028 (CLAUDE.md drift).
- **Test count drift Q (Report 0249 Q3)** — pyproject has no test-count assertion; CLAUDE.md "2,878 passing tests" may be stale.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR1035** | **`rcm-intake` console-script broken at pyproject.toml:70** — points to nonexistent `rcm_mc/intake.py` | After `pip install`, `rcm-intake` raises ModuleNotFoundError. Tests in `test_cli_dispatcher.py` may pass via direct module import but break for installed users. **Add `rcm_mc/intake.py` shim mirroring `rcm_mc/lookup.py` pattern.** | High |
| **MR1036** | **Python version drift: pyproject 3.10 vs CLAUDE.md 3.14** | mypy + ruff target 3.10 syntax/typing. If devs use 3.14-only features, ruff/mypy still gate at 3.10. Cross-link Report 0249. | Medium |
| **MR1037** | **mypy version drift: pyproject `>=1.5` vs pre-commit `v1.8.0`** | Two different version policies — pre-commit will run 1.8 strictly, but `pip install -e .[dev]` allows 1.5+. Type-check parity broken. | Medium |
| **MR1038** | **`pyarrow>=10.0` in `[diligence]`** — CVE-2023-47248 RCE risk | Cross-link Report 0101 MR770. **No upper bound on pyarrow.** | High |
| **MR1039** | **openpyxl listed in both `[dependencies]` and `[exports]` extras** | Redundant. Confusing for downstream extras computation. | Low |
| **MR1040** | **`exports` and `pptx` extras overlap on python-pptx** | Either consolidate or document the distinction. | Low |
| **MR1041** | **`profiles.example.yml` shipped via package-data — real `profiles.yml` near it** | Cross-link Report 0150 MR829. If real profiles.yml exists in same dir, glob-match risk. | Low |

## Dependencies

- **Incoming:** all `pip install` consumers; CI (Report 0184); pre-commit (Report 0184).
- **Outgoing:** PyPI (numpy, pandas, pyyaml, matplotlib, openpyxl, +optionals).

## Open questions / Unknowns

- **Q1.** What does `rcm_mc.__version__` resolve to vs pyproject `version = "1.0.0"`?
- **Q2.** Is `rcm-intake` covered by any installed-mode test (subprocess invoke), or only direct-import tests?
- **Q3.** Why is target Python 3.10 in pyproject but 3.14 in CLAUDE.md?
- **Q4.** Does `rcm_mc_diligence/` ship a real `profiles.yml` alongside `profiles.example.yml`?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0252** | Inspect `vendor/ChartisDrewIntel/` (carried from Report 0250). |
| **0253** | Add `rcm_mc/intake.py` shim **(actionable fix for MR1035)** — out of audit scope but flagged. |
| **0254** | Read `rcm_mc/__init__.py` for `__version__` (Q1). |

---

Report/Report-0251.md written. Next iteration should: data flow trace through `rcm_mc/data/intake.py` (only entry point currently broken-shimless) — closes MR1035 follow-up + Q2.
