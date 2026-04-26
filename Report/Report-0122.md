# Report 0122: Map Next Directory — `rcm_mc_diligence/` (separate top-level package)

## Scope

Maps `RCM_MC/rcm_mc_diligence/` — the second top-level Python package per Report 0101 MR552. Carried 13+ iterations (since Report 0078 entry-point trace, restated Reports 0093, 0101, 0113, 0117, 0118, 0120, 0121).

## Findings

### Top-level inventory

```
rcm_mc_diligence/
├── README.md              (1.0 KB)
├── __init__.py            (46 lines)
├── cli.py                 (252 lines)
├── connectors/
│   └── seekingchartis/    (dbt project)
├── dq/                    (data quality)
├── fixtures/              (test scenarios)
└── ingest/                (pipeline)
```

**4 subdirectories, 18 `.py` files, 3,859 lines of code.**

### Per-file inventory (sorted by lines)

| Path | Lines | Purpose |
|---|---|---|
| `dq/report.py` | 584 | `DQReport` dataclass + serialization (canonical result object) |
| `ingest/pipeline.py` | 397 | `run_ingest` — top-level pipeline orchestrator |
| `ingest/warehouse.py` | 396 | `DuckDBAdapter` + `Snowflake`/`Postgres` stubs |
| `ingest/file_loader.py` | 347 | Excel / CSV / Parquet loaders (uses pyarrow per Report 0113) |
| `dq/rules.py` | 346 | Data-quality validators — schema, completeness, plausibility |
| `ingest/connector.py` | 314 | Connector base class + dbt invocation |
| `dq/tuva_bridge.py` | 310 | Tuva-Health.org integration |
| `cli.py` | 252 | `rcm-mc-diligence` entry — `validate` / `ingest` / `run` subcommands |
| `fixtures/synthetic.py` | 209 | Synthetic data generator |
| `fixtures/mess_scenario_1_multi_ehr.py` | 166 | "Multi-EHR" mess scenario |
| `fixtures/mess_scenario_3_duplicate_adjudication.py` | 91 | "Duplicate adjudication" |
| `fixtures/mess_scenario_5_partial_payer_mix.py` | 89 | "Partial payer mix" |
| `fixtures/mess_scenario_2_orphaned_835s.py` | 88 | "Orphaned 835s" |
| `fixtures/mess_scenario_4_unmapped_codes.py` | 71 | "Unmapped codes" |
| `fixtures/__init__.py` | 61 | `FIXTURES` registry |
| `ingest/__init__.py` | 50 | re-exports |
| `__init__.py` | 46 | top-level re-exports |
| `dq/__init__.py` | 42 | re-exports |

### `connectors/seekingchartis/` (dbt project, NOT Python)

Per `find`: 8 files — dbt project + SQL models + sources YAML.

| File | Purpose |
|---|---|
| `dbt_project.yml` | dbt root config |
| `packages.yml` | dbt package deps (likely Tuva packages) |
| `profiles.example.yml` | sample dbt profile (DB credentials template) |
| `macros/safe_source_column.sql` | dbt macro |
| `models/input_layer/eligibility.sql` | eligibility input transform |
| `models/input_layer/medical_claim.sql` | medical claims transform |
| `models/input_layer/pharmacy_claim.sql` | Rx claims transform |
| `models/sources/_sources.yml` | dbt source declarations |

**8 files, all SQL/YAML.** No Python in this subdir. Per Report 0101 `[tool.setuptools.package-data]` these ship in the wheel.

### Public surface (per `__init__.py:33-46`)

```python
__all__ = [
    "DQReport", "DQSectionStatus", "DQSeverity",
    "DuckDBAdapter", "PostgresAdapter", "SnowflakeAdapter", "WarehouseAdapter",
    "run_ingest",
]
__version__ = "0.1.0"
```

**8 names exported.** Independent versioning (`0.1.0` vs main package `1.0.0` per Report 0101).

### Architectural promise (per `__init__.py` docstring lines 1-13)

> "This package is strictly additive to `rcm_mc`: it imports nothing from it and vice versa. Shared state (config, DB files, CLI entry points) is deliberately separate."

**One-way decoupling**: `rcm_mc/diligence/` (subpackage of `rcm_mc/`) ≠ `rcm_mc_diligence/` (top-level sibling). The two share names but **must not import each other**. Cross-link Report 0101 (separate-package design).

### Phase status (per `__init__.py`)

> "Phase 0.A substrate for the SeekingChartis diligence layer."

**Phase 0.A**. References `SESSION_LOG.md` and `PHASE_0B_NOTES.md` for next-phase work.

### Doc-rot finding: referenced files DON'T EXIST

Per `find RCM_MC/rcm_mc_diligence -name "*.md"`:

```
RCM_MC/rcm_mc_diligence/README.md
```

**Only README.md exists.** The `__init__.py` references:
- `rcm_mc_diligence/SESSION_LOG.md` — **NOT FOUND**
- `rcm_mc_diligence/PHASE_0B_NOTES.md` — **NOT FOUND**

**MR693 below.** Cross-link Report 0093 MR503 critical CLAUDE.md doc rot — same pattern, smaller scope.

### Doc-rot finding: README mentions `tests/` subdir that DOESN'T exist

`README.md` line 6: `| `tests/` | Test suite for this package only (separate from the main `RCM_MC/tests/`) |`

`find RCM_MC -name "tests" -path "*rcm_mc_diligence*"` returns **nothing**. **MR694 below.**

Per Report 0117: `tests/test_diligence_synthesis.py` exists in `RCM_MC/tests/` (the main package's tests, not this package's). Tests for this package live in the main `tests/` dir, not `rcm_mc_diligence/tests/`. README is wrong.

### `[diligence]` extras dependencies (per Report 0101)

```toml
diligence = [
    "duckdb>=1.0,<2.0",
    "dbt-core>=1.10,<2.0",
    "dbt-duckdb>=1.10,<2.0",
    "pyarrow>=10.0",
]
```

Per Report 0113: all 4 are lazy-imported inside this package's modules.

### "Mess scenario" fixtures (5 named test cases)

| # | File | Scenario name |
|---|---|---|
| 1 | `mess_scenario_1_multi_ehr.py` (166L) | Multi-EHR data feed |
| 2 | `mess_scenario_2_orphaned_835s.py` (88L) | Orphaned 835 ERA records |
| 3 | `mess_scenario_3_duplicate_adjudication.py` (91L) | Duplicate adjudication entries |
| 4 | `mess_scenario_4_unmapped_codes.py` (71L) | Unmapped codes |
| 5 | `mess_scenario_5_partial_payer_mix.py` (89L) | Partial payer mix |

**5 hand-built realistic-ugly-data scenarios** for testing the DQ layer. CLAUDE.md "Tests" pattern: "no mocks for our own code" — these are fixtures, not mocks. **Discipline aligned.**

### Subpackage import architecture

| Module | Imports |
|---|---|
| `__init__.py` | `.dq.report`, `.ingest.pipeline`, `.ingest.warehouse` |
| `cli.py` | `.dq.report.DQReport`, `.fixtures.FIXTURES`, `.ingest.pipeline.run_ingest`, `.ingest.warehouse.warehouse_from_name` |
| `ingest/connector.py` | `dbt.cli.main.dbtRunner` (lazy, per Report 0113) |
| `ingest/warehouse.py` | `duckdb` (lazy) |
| `ingest/file_loader.py` | `pyarrow` (lazy, 9+ sites per Report 0113) |
| `fixtures/synthetic.py` | `pyarrow` (lazy) |

**All third-party deps lazy-imported.** Confirms the optional-dep discipline.

### Cross-link to Report 0078 entry-point trace

`rcm-mc-diligence` console script (per pyproject `[project.scripts]`) → `rcm_mc_diligence.cli:main` → 252-line cli.py with 3 subcommands (`validate`, `ingest`, `run`).

### Comparison vs `rcm_mc/` (main package)

| Metric | `rcm_mc/` | `rcm_mc_diligence/` |
|---|---|---|
| Top-level .py | 5+ | 3 |
| Total .py files | hundreds | 18 |
| Total lines | ~50K+ | 3,859 |
| Subdirs | 54 (per Report 0101) | 4 |
| Public surface | huge | 8 names |
| Version | 1.0.0 | 0.1.0 |

**`rcm_mc_diligence/` is ~1% the size** of the main package. Tight, focused.

### NEW finding: `dq/tuva_bridge.py` integration with Tuva-Health.org

310 lines bridging to Tuva (open-source healthcare DQ project). Cross-link Report 0115 (CMS HCRIS integration); both are external-data-source bridges.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR693** | **`__init__.py` docstring references `SESSION_LOG.md` + `PHASE_0B_NOTES.md` — neither file exists** | Doc rot. Either files were deleted, never written, or live in a different location. New developer reading docstring fails to find them. | Low |
| **MR694** | **README.md table claims `tests/` subdir exists; it doesn't** | Tests for this package live in `RCM_MC/tests/test_diligence_synthesis.py` (main package tests). Misleading. | Low |
| **MR695** | **`SnowflakeAdapter` + `PostgresAdapter` are stubs** (per __init__ docstring "scaffolded stubs for Phase 0.B") | Public-API exports that raise NotImplementedError on use. Per Report 0105 NotImplementedError-stub pattern: documented + intentional. Acceptable. | (advisory) |
| **MR696** | **Architectural promise: "imports nothing from rcm_mc and vice versa"** | Promise needs verification. Q1 below. If broken, the separate-package independence is gone. | **High** |
| **MR697** | **`__version__ = "0.1.0"`** vs main package `1.0.0` (per Report 0101) | Independent versioning. Wheel bumps are decoupled. Need a release-coordination policy. | Low |
| **MR698** | **5 mess-scenario fixtures (~500 lines combined) ship in the wheel** | Per Report 0101 package-data: tested. But: synthetic-PHI fixtures may carry inadvertent realistic-looking patient data. Cross-link Report 0028 PHI mode. | Medium |
| **MR699** | **Connectors include real dbt project files** (`dbt_project.yml`, models, profiles example) | Ships in wheel via Report 0101 package-data. Has `profiles.example.yml` — but if a real `profiles.yml` is ever committed accidentally, secrets leak. **Should be `.gitignore`d.** | **Medium** |
| **MR700** | **Phase 0.A label**: implies phases 0.B / 0.C / 1.0+ planned; no roadmap visibility | Cross-link Report 0072 retention question, Report 0058 packet-version question. | Low |

## Dependencies

- **Incoming:** `pyproject.toml [project.scripts]` (rcm-mc-diligence binary), `pyproject.toml [tool.setuptools.packages.find]` (`rcm_mc_diligence*` glob), tests in `RCM_MC/tests/test_diligence_synthesis.py` and `RCM_MC/tests/test_*` plus the `Report 0100`-discovered `rcm_mc/diligence_synthesis/runner.py` (different package — DOES import from `rcm_mc/vbc_contracts` and `rcm_mc/montecarlo_v3`).
- **Outgoing:** stdlib + lazy `duckdb`, `dbt-core`, `dbt-duckdb`, `pyarrow`. Per architectural promise: NO `rcm_mc.*` imports.

## Open questions / Unknowns

- **Q1.** Verify the architectural promise: `grep "from rcm_mc\b\|import rcm_mc\b" rcm_mc_diligence/`. If clean, MR696 closed.
- **Q2.** Where do `SESSION_LOG.md` and `PHASE_0B_NOTES.md` live (if anywhere)? Or were they deleted in the cleanup commit `f3f7e7f` (Report 0089)?
- **Q3.** Do the 5 mess-scenario fixtures contain any real-looking PHI that would trip `phi_scanner.py` (Report 0043)?
- **Q4.** Does `rcm_mc/diligence_synthesis/runner.py` (Report 0100 — DIFFERENT package) duplicate any logic in this package's `ingest/pipeline.py`?
- **Q5.** Where is `profiles.example.yml`'s real-credentials version? Is it `.gitignore`d?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0123** | Verify MR696 — grep for cross-package imports between `rcm_mc/` and `rcm_mc_diligence/`. |
| **0124** | Schema-walk `deal_overrides` (Report 0118 MR677 — still owed). |
| **0125** | Read `infra/data_retention.py` (Report 0117 MR672 — still owed). |
| **0126** | Read `cli.py` head (1,252 lines, 14+ iterations owed). |

---

Report/Report-0122.md written.
Next iteration should: verify MR696 — the architectural promise that `rcm_mc_diligence/` and `rcm_mc/` don't import each other.
