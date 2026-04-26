# TEST-PASS-11 — focused regression sweep, all green

Date: 2026-04-26
Branch: `audit/reports-and-triage` (HEAD `6522848` at run time)
Runner: pytest 9.0.3 on Python 3.14.2

## Why focused, not full

Per the project memory note `project_test_baseline.md`, the full sweep has ~314 pre-existing failures unrelated to the audit/fix-loop work; running it from cold is several minutes of red noise that drowns out signal. The trusted regression gate is the per-module suite + smoke harness for the modules a change touches.

## What ran

Two batches, both green.

### Batch 1 — affected-area suite (iterations 2-10 changes)

- `tests/test_api_endpoints_smoke.py` — server boot smoke
- `tests/test_cli_dispatcher.py` — CLI dispatcher (covers `rcm-intake` shim)
- `tests/test_intake.py` — intake wizard (data/intake.py)
- `tests/test_auth.py` — auth module
- `tests/test_server.py` — server module (covers the new open-mode warning path)
- `tests/test_security_hardening.py` — security headers, CSRF, rate-limit
- `tests/test_config.py` — config loading
- `tests/test_config_validation.py` — config validation
- `tests/test_engagement.py` — engagement store
- `tests/test_engagement_pages.py` — engagement UI pages

**Result: 212 passed in 57.78s.**

### Batch 2 — core math + portfolio spot check

- `tests/test_simulator.py`
- `tests/test_calibration.py`
- `tests/test_value_plan.py`
- `tests/test_provenance.py`
- `tests/test_portfolio.py`
- `tests/test_pe_integration.py`

**Result: 31 passed in 0.83s.**

## Coverage of recent fixes

| Iter | Fix | Test coverage |
|---|---|---|
| 2 | configs/playbook.yaml parse | (no direct test; consumer is html_report — covered transitively if `test_full_report` runs, which it did not in this sweep) |
| 3 | pyarrow pin tighten | metadata-only; no runtime test needed |
| 4 | rcm_mc/intake.py shim | test_cli_dispatcher (12) + test_intake (27) — green |
| 7 | infra/README.md text | docs-only, no test coverage |
| 8 | MERGE-CONFLICTS.md | docs-only, no test coverage |
| 9 | server.py open-mode warning | test_auth + test_server + test_security_hardening (106) — green |
| 10 | CLAUDE.md table count | docs-only, no test coverage |

**No regressions introduced. No red tests in the focused sweep.**

## Known blind spots (not failures, but uncovered by this sweep)

- `tests/test_full_report.py` (or equivalent) was not run, so the playbook.yaml fix from iter 2 is structurally verified (yaml.safe_load returns 8 buckets) but not exercised end-to-end through the HTML report pipeline.
- The full ~3000-test suite was not run per the baseline-failures memory note; future iterations may want to run it once the baseline is curated.
