# Report 0003: `RCM_MC/pyproject.toml` — Dependency + Entry-Point Audit

## Scope

This report covers **`RCM_MC/pyproject.toml`** in full (126 lines, 3,842 B, last modified 2026-04-25 in commit `f3f7e7f` on `origin/main`). Read line-by-line; every declaration is documented below. The report also cross-validates each declared entry point against the source tree to confirm it resolves, and inspects the two declared packages (`rcm_mc`, `rcm_mc_diligence`) at their `__init__.py` level only — the rest of those trees is reserved for future iterations.

Prior reports reviewed before writing: 0001, 0002. Suggested follow-up from 0002 was: "read `RCM_MC/pyproject.toml` line-by-line and lock down the dependency surface." This report executes that.

## Findings

### Build system (lines 1-3)

- Backend: `setuptools.build_meta`. Requires `setuptools>=68.0` + `wheel`. Standard.

### Project metadata (lines 5-24)

- `name = "seekingchartis"` (line 6) — the **PyPI distribution name is `seekingchartis`**, even though the codebase, repo, and module names use `rcm_mc`. Distribution name vs import name divergence is normal but worth knowing for installs.
- `version = "1.0.0"` (line 7) — pyproject declares **1.0.0**, but `RCM_MC/rcm_mc/__init__.py:1` declares `__version__ = "1.0.0"` (matches), and `RCM_MC/README.md:1` says `# RCM-MC v0.6.0`, and `RCM_MC/CHANGELOG.md:3` says `## v0.6.1 (2026-04-25)`. **Three different version numbers in three places for the same package on the same branch.**
- `requires-python = ">=3.10"` (line 10).
- `license = {text = "Proprietary"}` (line 11) — answers part of Report 0001 Q1: **license declaration on origin/main is "Proprietary"**, despite the existence of `CONTRIBUTING.md` at repo root. Whether the LICENSE file body matches has not been verified.
- Classifiers (lines 13-24): "Development Status :: 4 - Beta" + Python versions 3.10 through 3.14 + financial / medical-science topic categories.

### Core runtime dependencies (lines 26-32)

| Dep | Constraint | Notes |
|---|---|---|
| `numpy` | `>=1.24,<3.0` | Core. The "Numpy-only ML" invariant in `CLAUDE.md` enforces this is the *only* numerical computation lib at module level. |
| `pandas` | `>=2.0,<4.0` | Core. Used widely in module data manipulation. |
| `pyyaml` | `>=6.0,<7.0` | Core. Config files are YAML. |
| `matplotlib` | `>=3.7,<4.0` | Core. Plotting. |
| `openpyxl` | `>=3.1,<4.0` | Core **and also** declared in `exports` extra (line 42 has a comment explaining the intentional duplication: xlsx export is a core partner workflow). |

**5 core deps.** No third-party HTTP framework (Flask, FastAPI), no third-party ORM (SQLAlchemy), no third-party auth (OAuth libs). Confirms the stdlib-heavy posture documented in `CLAUDE.md` on `feature/deals-corpus`.

### Optional dependency extras (lines 34-66)

| Extra | Deps | Purpose |
|---|---|---|
| `interactive` | `plotly>=5.0` | Interactive plot rendering (alternative to matplotlib). |
| `pptx` | `python-pptx>=0.6` | PowerPoint export. |
| `exports` | `python-pptx>=0.6`, `openpyxl>=3.1` | xlsx + pptx exports bundled. (`openpyxl` is dual-listed by design — see comment lines 37-41.) |
| `api` | `fastapi>=0.100`, `uvicorn>=0.23` | **Optional** FastAPI surface. Confirms the stdlib `http.server` is the default; FastAPI is an alternate path. |
| `diligence` | `duckdb>=1.0,<2.0`, `dbt-core>=1.10,<2.0`, `dbt-duckdb>=1.10,<2.0`, `pyarrow>=10.0` | **Phase 0.A diligence-ingestion layer**. Comment lines 44-46: "Isolated from core rcm_mc — the new code lives in `rcm_mc_diligence/` and wraps Tuva via `dbt-duckdb`. Core `rcm_mc` imports nothing from here." |
| `all` | `openpyxl`, `plotly`, `python-pptx`, `fastapi`, `uvicorn`, `scipy>=1.11` | Bundled "give me everything." **`scipy` only appears here — not in any other extra and not in core.** Implies scipy is optional everywhere except in code that runs under `[all]`. |
| `dev` | `pytest>=7.0`, `pytest-cov>=4.0`, `ruff>=0.1`, `mypy>=1.5` | Developer tools. |

**Important detail about `[all]`:** it does NOT include the `diligence` extras (no `duckdb`/`dbt-core`/`dbt-duckdb`/`pyarrow`). A user who runs `pip install -e ".[all]"` will get scipy + FastAPI + plotly + pptx but **not** the diligence stack. This is internally consistent with the "isolated subsystem" comment at lines 44-46 but easy to miss.

### Console scripts / entry points (lines 68-72)

| Console name | Declared module path | Resolves? |
|---|---|---|
| `rcm-mc` | `rcm_mc.cli:main` | ✅ `rcm_mc/cli.py:1252` defines `def main(argv: Optional[list[str]] = None) -> int`. |
| **`rcm-intake`** | **`rcm_mc.intake:main`** | ❌ **BROKEN.** No `rcm_mc/intake.py` and no `rcm_mc/intake/` package exists. The actual implementation lives at `rcm_mc/data/intake.py:619` (`def main(argv, prog="rcm-intake") -> int`). The entry point points one level up from where the code is. **HIGH-PRIORITY merge risk.** |
| `rcm-lookup` | `rcm_mc.lookup:main` | ✅ `rcm_mc/lookup.py:11` defines `def main() -> int`. |
| `rcm-mc-diligence` | `rcm_mc_diligence.cli:main` | ✅ `rcm_mc_diligence/cli.py:240` defines `def main(argv) -> int`. |

### Setuptools package configuration (lines 74-85)

- `[tool.setuptools.packages.find]` `include = ["rcm_mc*", "rcm_mc_diligence*"]` (line 75) — **two top-level packages get installed.** Confirms the discovery from Report 0002 MR10: `rcm_mc_diligence/` is a real, installable, declared package, not a stray directory.
- `[tool.setuptools.package-data]` `rcm_mc = ["data/*.csv.gz"]` (line 78) — verified: `RCM_MC/rcm_mc/data/hcris.csv.gz` exists (1,667,248 B, 1.59 MB). One gzipped CSV ships with the wheel.
- `rcm_mc_diligence` package-data (lines 79-85) — declares 5 globs covering the SeekingChartis DBT connector: `dbt_project.yml`, `packages.yml`, `profiles.example.yml`, plus all `.sql` and `.yml` files under `models/**/`. Verified: `RCM_MC/rcm_mc_diligence/connectors/seekingchartis/{dbt_project.yml,packages.yml,profiles.example.yml,models/,macros/}` all exist. The DBT connector is real.

### Pytest configuration (lines 87-110)

- `testpaths = ["tests"]` — pytest only descends into `RCM_MC/tests/` (459 items per Report 0002).
- `addopts = "-v --tb=short"` — verbose + short tracebacks by default.
- 6 markers declared (lines 91-97): `api`, `ui`, `store`, `security`, `integration`, `slow`. None are referenced in this report's scope; future test-suite reports must verify markers are actually used and surface unmarked tests.
- `filterwarnings` (lines 98-110) silences two ResourceWarnings tied to `ThreadingHTTPServer` socket-close timing (the comment is detailed: "this is a gc-timing artifact in multi-test-file runs, not a real leak"). Important context for any test-output regressions during merge.

### Ruff + mypy (lines 112-126)

- Ruff: `line-length = 120`, target `py310`, lint rules `E F W I UP B SIM RUF`, ignored `E501 RUF012`.
- Mypy: `python_version = "3.10"`, strict-optional on, all warn flags on, `ignore_missing_imports = true`. Strict but tolerant of unstubbed deps.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR14** | **HIGH-PRIORITY: Broken `rcm-intake` entry point** | `pyproject.toml:70` declares `rcm-intake = "rcm_mc.intake:main"`, but `rcm_mc/intake.py` does not exist on `origin/main`. The actual `main()` lives at `rcm_mc/data/intake.py:619`. Any user who runs `pip install -e .` and then `rcm-intake` will fail with `ModuleNotFoundError`. **Branches that touch intake (likely `feature/demo-real`, `feature/workbench-corpus-polish`) may have already fixed this — or made it worse**. Pre-merge: re-grep every branch for `rcm_mc.intake:main` and the actual location of `intake.py`. | Critical |
| **MR15** | **3-way version drift** | `pyproject.toml:7` says 1.0.0; `rcm_mc/__init__.py:1` says 1.0.0 (matches); `RCM_MC/README.md:1` says v0.6.0; `RCM_MC/CHANGELOG.md:3` says v0.6.1 (latest). Single source of truth violated. Any branch that bumps version in *one* of these files but not the others will silently desync. | High |
| **MR16** | License declaration mismatch | `pyproject.toml:11` is `"Proprietary"`. Repo-root `CONTRIBUTING.md` reads as semi-open. Repo-root `LICENSE` body has not been read yet (Q1 in Report 0001 — still open). If a branch updated `LICENSE` to MIT/Apache and bumped pyproject's license accordingly, that will conflict on merge with branches that left it Proprietary. | Medium |
| **MR17** | **scipy in `[all]` only** | `scipy>=1.11` (line 59) is reachable only via `pip install ".[all]"`. If any branch added a `scipy` import to a hot path (e.g. statistical helpers in `rcm_mc/ml/`), users on the default install will get `ImportError`. **Pre-merge audit must `grep -rn "import scipy" RCM_MC/rcm_mc` on every ahead-of-main branch** to find new scipy usages. | High |
| **MR18** | `[all]` does not include `[diligence]` | A user who installs `[all]` does not get `duckdb`/`dbt-core`/`dbt-duckdb`/`pyarrow`. If a branch wired `rcm_mc_diligence` into `rcm_mc` (against the stated isolation boundary), users on `[all]` will hit ImportError. Pre-merge audit must verify `rcm_mc_diligence` is *still* not imported from `rcm_mc/`. Maps directly to Report 0002 MR10. | High |
| **MR19** | Pytest `filterwarnings` masks real leaks | The two suppressed warnings are commented as gc-timing artifacts, but if a future commit introduces a real socket leak, the suppression will hide it. Worth knowing during test-suite audit (future iteration). | Low |
| **MR20** | Two-package wheel topology | `tool.setuptools.packages.find` returns both `rcm_mc*` and `rcm_mc_diligence*`. If a branch extended `rcm_mc_diligence/` to include sub-namespaces that *also* match `rcm_mc*` glob (e.g. `rcm_mc_diligence/rcm_mc_legacy/`), discovery could pick up duplicates. Unlikely but worth a grep. | Low |
| **MR21** | Pre-commit config on package, not repo-root | Report 0002 Q8 noted `RCM_MC/.pre-commit-config.yaml` exists but no repo-root one. Pyproject's ruff + mypy config lives here — if a branch adds repo-root pre-commit hooks for the same rules, they may double-run or conflict. | Low |

## Dependencies

- **Incoming (who depends on `pyproject.toml`):** every `pip install` (developer + CI + Azure VM deploy via `RCM_MC/deploy/Dockerfile`); GitHub workflows that pin Python versions; the `[project.scripts]` entry points are wired into shell `$PATH` post-install (`rcm-mc`, `rcm-intake`, `rcm-lookup`, `rcm-mc-diligence`).
- **Outgoing (what `pyproject.toml` depends on):**
  - **Code resolution:** `rcm_mc/cli.py::main`, `rcm_mc/lookup.py::main`, `rcm_mc_diligence/cli.py::main` — all confirmed to exist. `rcm_mc/intake.py::main` — **does not exist** (MR14).
  - **Package data presence:** `rcm_mc/data/hcris.csv.gz` (verified, 1.59 MB); `rcm_mc_diligence/connectors/seekingchartis/{dbt_project,packages,profiles.example}.yml` + nested `models/` (verified).
  - **External:** PyPI indexes, the 5 core deps, the conditional extras.

## Open questions / Unknowns

- **Q1 (this report).** When was `rcm-intake = "rcm_mc.intake:main"` last *correct*? Was the module moved into `rcm_mc/data/` and the entry point not updated? `git log -p -- pyproject.toml` for `RCM_MC/pyproject.toml` could answer this.
- **Q2.** Is the canonical version 1.0.0 (pyproject), 0.6.0 (README), or 0.6.1 (CHANGELOG)? Which is intended for the next release?
- **Q3.** Does the repo-root `LICENSE` body match the `"Proprietary"` declaration in `pyproject.toml:11`?
- **Q4.** Does `rcm_mc/` import anything from `scipy` today on origin/main? If yes, scipy belongs in core deps, not in `[all]`.
- **Q5.** Does any code in `rcm_mc/` currently import `rcm_mc_diligence` (violating the stated isolation)? The pyproject comment claims "Core `rcm_mc` imports nothing from here" — verify.
- **Q6.** Is `rcm_mc_diligence` covered by `RCM_MC/tests/` or by its own test suite? Pyproject's `testpaths = ["tests"]` is singular — there's no `rcm_mc_diligence/tests/` reference.
- **Q7.** Why does `[all]` exclude the `diligence` extras? Intentional ("you almost never want both" stance) or oversight?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0004** | Walk `RCM_MC/rcm_mc/cli.py` (1,252+ lines, has `main()` at 1252). The primary CLI surface. | This is the user-facing entry point. Mapping it locks down which subcommands are wired and which are stale. |
| **0005** | `RCM_MC/rcm_mc_diligence/` subsystem audit — full module list + verify the "isolated from `rcm_mc`" claim in pyproject's comment. | Critical for MR18, MR10, Q5. If isolation is broken, every merge that touches either package becomes risky. |
| **0006** | Resolve MR14: read `rcm_mc/data/intake.py` head + `git log` of `pyproject.toml` to find when the entry point broke. | The broken entry point is the single most actionable bug surfaced so far. |
| **0007** | Branch register (still owed) — every origin branch, ahead/behind main, last-touch date. | Required before any merge planning. Repeatedly suggested by 0001, 0002, deferred again here. |
| **0008** | `RCM_MC/.gitignore` + repo-root `.gitignore` diff (Q2 from 0002, Q1 from this report partial). | Two ignore files at different levels are a maintenance hazard. |
| **0009** | `.github/workflows/*.yml` audit (4 workflows). | Still open from Report 0001 Q3. Predicts CI gating on every merge. |

---

Report/Report-0003.md written. Next iteration should: walk `RCM_MC/rcm_mc/cli.py` end-to-end to map every subcommand and confirm the `rcm-mc` entry point's actual surface (the only console script verified to resolve so far).

