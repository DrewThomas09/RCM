# tests/

Test suite for the RCM-MC / SeekingChartis platform. **339 files** — mostly 1:1 test-per-feature with the rest being numbered regression tests + end-to-end integration tests.

## Running

```bash
# Full suite
.venv/bin/python -m pytest -q --ignore=tests/test_integration_e2e.py

# Single feature
.venv/bin/python -m pytest tests/test_hcris_xray.py -q

# The 7 new-cycle diligence modules
.venv/bin/python -m pytest tests/test_hcris_xray.py tests/test_bear_case.py \
    tests/test_payer_stress.py tests/test_bridge_audit.py \
    tests/test_covenant_lab.py tests/test_regulatory_calendar.py \
    tests/test_thesis_pipeline.py -q
```

Expected: ~2,970+ passing.

## File naming patterns

| Pattern | Count | Description |
|---------|-------|-------------|
| `test_<feature>.py` | 310 | One file per backend feature/module |
| `test_bug_fixes_b<N>.py` | 15 | **Numbered regression tests** — B146 through B162. Filename doubles as bug ticket reference. |
| `test_integration_*.py` | 1 | **End-to-end** via real HTTP server on a free port |
| `test_ui_*.py` | 2 | UI-specific integration |
| `test_api_*.py` | 1 | API contract |
| `test_pe_intelligence_*.py` | 1 | Partner-brain integration |
| `test_cms_*.py` | 1 | CMS pipeline integration |
| `conftest.py` | 1 | Shared pytest fixtures |

## Conventions (enforced)

- **Stdlib `unittest` classes, driven by pytest runner.** No third-party assertion libraries.
- **No mocks for our own code.** Always exercise the real path. `unittest.mock` only acceptable for external stubs (e.g., simulating a failing `log_event` to test silent-failure paths).
- **Multi-step workflows hit a real HTTP server** on a free port via `urllib.request`. No mocked HTTP clients.
- **Order-independent** — class-level state (e.g., login-fail log on `RCMHandler`) is reset in `setUp` / `tearDown`.
- **Bug fixes get their own file** — `test_bug_fixes_bN.py` with a one-line bug description docstring + minimal reproducer + assertion.

## Shared fixtures (`conftest.py`)

- `portfolio_store_tmp` — `PortfolioStore` backed by a temp DB path. Auto-cleaned.
- `free_port` — finds an unused port for integration tests via stdlib `socket`.
- Threading helpers — start server in a thread, join on teardown.

## Fixture hospitals (`tests/fixtures/kpi_truth/`)

Deterministic synthetic CCD fixtures representing named pathology scenarios. Referenced across the codebase (e.g., `thesis_pipeline` README defaults to `hospital_04_mixed_payer`).

| Fixture | Pathology |
|---------|-----------|
| `hospital_02_denial_heavy` | High denial rate; stresses denial-prediction model |
| `hospital_04_mixed_payer` | Balanced payer mix; default for thesis pipeline demo |
| `hospital_05_dental_dso` | DSO pattern; stresses distribution-shift integrity guardrail |
| `hospital_06_waterfall_truth` | Known-good waterfall output for regression testing |
| `hospital_07_waterfall_concordant` | Multiple-method concordance scenario |
| `hospital_08_waterfall_critical` | Edge-case waterfall with known-failure patterns |

Generated via `tests/fixtures/kpi_truth/generate_kpi_truth.py` — deterministic given a seed.

## Messy-data fixtures (`tests/fixtures/messy/`)

Parallel to `rcm_mc_diligence/fixtures/mess_scenario_*` but for the lightweight Python-only ingest path. `generate_fixtures.py` produces raw-data directories that exercise normalization invariants (column alias, date-format drift, payer-spelling variants).

## Regression test catalog

Bug fix filenames double as tickets. Skim the filenames for a compressed history of what broke:

- `b146` through `b162` (skipping b153 and b161) — chronological since numbering began
- Examples:
  - `b146` — (see file docstring)
  - `b160` — `trigger_key strips whitespace` in alerts
  - ...

Each file's module docstring starts with `Regression test for B<N>: <one-line description>.`

## CI expectations

- All test files in `tests/` root run in the default pytest invocation
- Integration tests under `test_integration_*` are gated by `--ignore=tests/test_integration_e2e.py` by default — they require a bound port and take longer
- Fixtures are regenerated deterministically on import; no network calls in any test
