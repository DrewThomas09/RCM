# Report 0101: Config Map — `pyproject.toml` (Full)

## Scope

Full read of `RCM_MC/pyproject.toml` (127 lines). Closes Report 0086 Q1+Q2+Q3 + Report 0091 entry-point gap. Sister to Reports 0003 (initial dep audit), 0086 (entry-points partial).

## Findings

### Build system

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"
```

Setuptools >=68 (newer than Report 0003 said "61"). Standard build-meta backend.

### `[project]` core fields

| Key | Value |
|---|---|
| `name` | `seekingchartis` (NOT `rcm_mc` — package name vs distribution name distinction) |
| `version` | `1.0.0` (no `dynamic` — static versioning) |
| `description` | "SeekingChartis — Healthcare PE Diligence Platform" |
| `readme` | `README.md` |
| `requires-python` | `>=3.10` ← **closes Report 0086 Q2** |
| `license` | `Proprietary` |
| `classifiers` | Python 3.10–3.14 supported per classifier rows 17-21 |

**Cross-correction to CLAUDE.md**: CLAUDE.md says "Python 3.14"; pyproject says `>=3.10` (floor) AND lists 3.10–3.14 in classifiers. Both are correct: 3.14 is the latest supported, but 3.10 is the **minimum**. CLAUDE.md is misleading — should say "≥3.10, tested 3.10-3.14."

### `[project.dependencies]` (5 core runtime deps)

```toml
"numpy>=1.24,<3.0",
"pandas>=2.0,<4.0",
"pyyaml>=6.0,<7.0",
"matplotlib>=3.7,<4.0",
"openpyxl>=3.1,<4.0",
```

5 packages. Cross-references:
- numpy: Report 0046
- pandas: Report 0053
- pyyaml: Report 0016
- matplotlib: Report 0076
- openpyxl: Report 0083

**All 5 already audited.** No new direct runtime deps.

### `[project.optional-dependencies]` — 7 extras groups

| Extra | Packages | Status |
|---|---|---|
| `interactive` | `plotly>=5.0` | unmapped — likely used in some UI page |
| `pptx` | `python-pptx>=0.6` | per CLAUDE.md (`pptx_export` module) |
| `exports` | `python-pptx>=0.6`, `openpyxl>=3.1` | duplicates base + pptx (per Report 0083) |
| `api` | `fastapi>=0.100`, `uvicorn>=0.23` | **NEVER USED** — CLAUDE.md says "no Flask/FastAPI" |
| `diligence` | `duckdb>=1.0`, `dbt-core>=1.10`, `dbt-duckdb>=1.10`, `pyarrow>=10.0` | for `rcm_mc_diligence/` package (separate root) |
| `all` | unique union + `scipy>=1.11` | scipy is here only — **no production scipy** |
| `dev` | `pytest>=7.0`, `pytest-cov>=4.0`, `ruff>=0.1`, `mypy>=1.5` | dev tooling |

### HIGH-PRIORITY DISCOVERY: `[api]` extras define unused deps

Lines 43: `api = ["fastapi>=0.100", "uvicorn>=0.23"]`. Per CLAUDE.md: "HTTP via `http.server.ThreadingHTTPServer` — no Flask/FastAPI." **Either CLAUDE.md is wrong OR `[api]` extras are dead.** No prior report mapped fastapi/uvicorn imports. Likely dead extras.

### HIGH-PRIORITY DISCOVERY: scipy is in `[all]` but never imported

Per Reports 0046, 0093, 0095: project is "numpy-only" (per ml/README). But pyproject `[all]` includes `scipy>=1.11`. **Either:**
- scipy is intended for a future module that doesn't yet exist, OR
- some module imports scipy that wasn't caught in audit, OR
- it's vestigial from an earlier era.

`grep -rn "import scipy\|from scipy" RCM_MC/rcm_mc/` — not run this iteration. Q1.

### `[project.scripts]` — closes Report 0086 Q1

**4 console scripts** (not 1, not 3):

| Script | Module:function | Status |
|---|---|---|
| `rcm-mc` | `rcm_mc.cli:main` | ← Reports 0018, 0048 |
| `rcm-intake` | `rcm_mc.intake:main` | **NEVER REPORTED** — implies `rcm_mc/intake.py` exists |
| `rcm-lookup` | `rcm_mc.lookup:main` | **NEVER REPORTED** — Report 0009 covered `data/lookup.py` dead code; this is `rcm_mc/lookup.py` (different file?) |
| `rcm-mc-diligence` | `rcm_mc_diligence.cli:main` | ← Report 0078 |

**`rcm-intake` and `rcm-lookup` are CLI entry-points never seen.** Cross-link Report 0091 unmapped #1 (cli.py 1252 lines).

### HIGH-PRIORITY DISCOVERY: separate `rcm_mc_diligence/` package

```toml
[tool.setuptools.packages.find]
include = ["rcm_mc*", "rcm_mc_diligence*"]
```

**`rcm_mc_diligence` is a SECOND top-level package**, not a subpackage of `rcm_mc/`. All prior reports referred to `rcm_mc/diligence/` (subpackage of rcm_mc). Per Report 0078 entry-point trace: `rcm-mc-diligence` was identified. Now confirmed: separate package at repo root. Q2 below.

### `[tool.setuptools.package-data]`

```toml
rcm_mc = ["data/*.csv.gz"]
rcm_mc_diligence = [
    "connectors/seekingchartis/dbt_project.yml",
    "connectors/seekingchartis/packages.yml",
    "connectors/seekingchartis/profiles.example.yml",
    "connectors/seekingchartis/models/**/*.sql",
    "connectors/seekingchartis/models/**/*.yml",
]
```

`rcm_mc/data/` ships `.csv.gz` files in the wheel. `rcm_mc_diligence/connectors/seekingchartis/` ships dbt SQL/YAML — **dbt model bundling**. Confirms `rcm_mc_diligence` is a dbt+duckdb-based separate package.

### `[tool.pytest.ini_options]`

| Key | Value |
|---|---|
| `testpaths` | `["tests"]` |
| `addopts` | `-v --tb=short` |
| `markers` | api, ui, store, security, integration, slow (6 markers) |
| `filterwarnings` | 2 ResourceWarning ignores for ThreadingHTTPServer FD reaping |

**6 pytest markers** — Reports 0008 + 0026 + 0038 + 0068 didn't enumerate them. The `slow` marker means "5+ seconds" tests can be skipped via `-m "not slow"`.

### `[tool.ruff]`

```toml
line-length = 120
target-version = "py310"
```

```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]
ignore = ["E501", "RUF012"]
```

**`F` is in the select list.** F401 (unused-imports) is part of `F`. So ruff DOES check unused imports.

**Cross-correction to Report 0099 MR543**: I claimed pre-commit "likely doesn't have F401." Wrong — it does. The 5 unused imports in `domain/custom_metrics.py` (Report 0099) **should have been caught**. Either:
- pre-commit hooks aren't running on commit (per Report 0056), OR
- ruff isn't actually invoked by pre-commit, OR
- file is excluded.

Q3 below.

### `[tool.mypy]`

```toml
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
warn_unused_ignores = true
strict_optional = true
ignore_missing_imports = true
```

`strict_optional = true` is the **most consequential** setting. `Optional[T]` ≠ `T`; can't pass `None` where `T` is expected. Per Report 0021 (`auth.py` Optional[User] return) this is enforced.

`ignore_missing_imports = true` weakens it — third-party packages without stubs (e.g. dbt-core?) won't fail mypy.

### Cross-correction to Report 0086

| Report 0086 claim | Actual |
|---|---|
| "1 binary or 3?" (Q1) | **4 binaries** |
| "`>=3.10` or `>=3.14`?" (Q2) | **`>=3.10`** with classifiers up to 3.14 |
| "editable / wheel / sdist?" (Q3) | unanswered — pyproject doesn't pin |
| MR479 medium | downgraded — both CLAUDE.md and pyproject correct, just inconsistent in framing |

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR549** | **`[api]` extras (fastapi+uvicorn) likely DEAD** — never imported per CLAUDE.md "no Flask/FastAPI." | Should be removed or repurposed. If a future PR uses [api] extras thinking they're wired, breaks. | Medium |
| **MR550** | **`scipy>=1.11` in `[all]` but never imported in production** | Either intended-for-future or vestigial. Provides false signal that scipy is "available". | Medium |
| **MR551** | **`rcm-intake` + `rcm-lookup` entry-points never audited** | 2 console scripts never traced; `rcm_mc/intake.py` + `rcm_mc/lookup.py` body unknown. **HIGH-PRIORITY**. | **High** |
| **MR552** | **`rcm_mc_diligence/` separate package never end-to-end mapped** | Per Report 0078: entry-point traced; per this iteration: ships dbt SQL+YAML data files. Body of the package unknown. | **High** |
| **MR553-correction** | **Report 0099 MR543 was wrong about ruff F401** — ruff DOES select F. The dead imports SHOULD be caught. Real Q: why aren't they? | Pre-commit may not be wired into git hooks; or ruff fails silently in CI. Cross-link Report 0056. | **High** |
| **MR554** | **`mypy ignore_missing_imports=true` weakens strict_optional for any 3rd-party not stubbed** | Important runtime types (e.g. duckdb, dbt-core, openpyxl) not type-checked. | Medium |
| **MR555** | **`pytest markers` exist but Reports 0008/0026/0038/0068 never enumerated them** | Useful test-organization metadata never surfaced. | Low |
| **MR556** | **`name = "seekingchartis"` vs package `rcm_mc`** | Distribution name ≠ import name. `pip show seekingchartis` works; `pip show rcm_mc` does not. Onboarding ambiguity. | Low |
| **MR557** | **Filterwarnings hide ThreadingHTTPServer FD-reap timing warnings** | Per pyproject lines 99-109: "this is a gc-timing artifact, not a real leak." Comment is candid but the suppression hides any future actual leak too. | Low |

## Dependencies

- **Incoming:** every install (`pip install -e .[dev]`), every CI job (Reports 0026 + 0086), every release wheel.
- **Outgoing:** PyPI (numpy, pandas, pyyaml, matplotlib, openpyxl), setuptools.

## Open questions / Unknowns

- **Q1.** Does any production module actually import `scipy`? (`grep "scipy" RCM_MC/rcm_mc/`)
- **Q2.** What is the `rcm_mc_diligence/` package — file count, public surface, line count?
- **Q3.** Is pre-commit (Report 0056) actually running ruff F401 in practice? Why didn't it catch Report 0099's 5 unused imports?
- **Q4.** What's in `rcm_mc/intake.py` and `rcm_mc/lookup.py` (the entry-point modules)?
- **Q5.** Are the `[api]` extras truly dead or is there an opt-in fastapi mode somewhere?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0102** | Map `rcm_mc_diligence/` separate package (closes Q2 + MR552). |
| **0103** | Read `rcm_mc/intake.py` head (closes Q4 partial + MR551). |
| **0104** | Grep `import scipy` (closes Q1 + MR550). |
| **0105** | Map `rcm_mc/pe_intelligence/` (deferred 5+ iterations). |

---

Report/Report-0101.md written.
Next iteration should: map `rcm_mc_diligence/` separate package — closes MR552 high + uncovers a 4th-extras hidden subsystem.
