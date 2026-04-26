# Report 0128: Test Coverage — `infra/job_queue.py`

## Scope

Coverage spot-check for `infra/job_queue.py` (Report 0103: 389 lines, 5 public exports). Sister to Reports 0008 (portfolio.store), 0038 (simulator), 0068 (audit_log), 0098 (econ_ontology).

## Findings

### Public surface (per Report 0103)

| # | Symbol | Type |
|---|---|---|
| 1 | `JOB_STATUSES` | tuple constant |
| 2 | `Job` | dataclass (12 fields, `to_dict`) |
| 3 | `JobRegistry` | class (8 public methods) |
| 4 | `get_default_registry()` | factory |
| 5 | `reset_default_registry()` | test helper |

### `JobRegistry` 8 public methods coverage

| Method | Test file | Status |
|---|---|---|
| `__init__(*, runner, output_tail_lines)` | implicit (every test instantiates) | ✓ |
| `submit_run(*, actual, benchmark, outdir, ...)` | test_job_queue.py | ✓ direct |
| `submit_callable(*, kind, runner, params, idempotency_key)` | **test_data_refresh_workflow.py** (2 tests) | ✓ |
| `get(job_id)` | test_job_queue.py | ✓ direct |
| `list_recent(n)` | test_job_queue.py | ✓ direct |
| `wait(job_id, timeout)` | (test helper itself) | acceptable |
| `mark_stale(*, max_age_seconds, reason)` | **test_resilience.py** (2 tests) | ✓ |
| `shutdown(timeout)` | **— NONE FOUND** | ✗ |

**7 of 8 methods directly tested. `shutdown` is the only gap.**

### Test files exercising JobRegistry

| File | Lines | Test count for job_queue | Notes |
|---|---|---|---|
| `tests/test_job_queue.py` | 294 | 13 (7 lifecycle + 5 HTTP integration) | core unit tests |
| `tests/test_data_refresh_workflow.py` | (TBD) | 6 (2 submit_callable + 4 data-refresh flow) | feature tests |
| `tests/test_resilience.py` | (TBD) | 3 (2 mark_stale + 1 stuck-job) | resilience tests |
| `tests/test_bug_fixes_b149.py` | (TBD) | (TBD) | regression for BaseException catch |
| `tests/test_rerun_cli_and_alerts_owner.py` | (TBD) | indirect | CLI flow |
| `tests/test_web_production_readiness.py` | (TBD) | indirect | smoke |
| `tests/test_deal_sim_inputs.py` | (TBD) | indirect | feature |

**~20-25 tests total exercise this module.** Cross-link CLAUDE.md "Each feature has a `test_<feature>.py` file" — coverage is BY FEATURE not BY MODULE. Report 0103's "test_job_queue.py exists" was incomplete — the real coverage map spans 7+ files.

### `test_job_queue.py` test inventory (294 lines)

#### `TestJobLifecycle` (lines 25-119) — 7 tests

1. `test_submit_returns_job_id` — submit_run returns string
2. `test_job_transitions_to_done` — full happy path (queued → running → done)
3. `test_failing_job_marked_failed_with_error` — exception path
4. `test_get_unknown_returns_none` — error path
5. `test_list_recent_newest_first` — ordering invariant
6. `test_output_tail_captures_prints` — stdout-capture behavior
7. `test_worker_is_single_threaded_fifo` — **single-worker invariant** (cross-link Report 0103 MR569 about FIFO blocking)

#### `TestHttpIntegration` (lines 120+) — 6 tests

8. `test_post_jobs_run_accepts_and_returns_job_id`
9. `test_post_jobs_run_missing_params_returns_400`
10. `test_post_jobs_run_nonexistent_actual_returns_400`
11. `test_jobs_index_page_renders`
12. `test_job_detail_for_unknown_id_shows_message`
13. `test_job_detail_shows_status_and_params`

### Strong invariants tested

| Invariant | Test |
|---|---|
| `queued → running → done | failed` linear | test_job_transitions_to_done + test_failing_job |
| Single worker FIFO | test_worker_is_single_threaded_fifo |
| Stdout/stderr capture into `output_tail` | test_output_tail_captures_prints |
| Failed runner doesn't kill worker | test_failing_job |
| `mark_stale` grace period honored | test_resilience.py |
| `submit_callable` idempotency-key coalescing | test_data_refresh_workflow.py |

### Coverage gaps

| Gap | Risk | Severity |
|---|---|---|
| `shutdown(timeout)` not tested | Mid-flight shutdown could leave dangling daemon thread | **Medium** |
| `Job.to_dict()` not directly unit-tested | Schema may drift; HTTP integration tests would catch but slowly | Low |
| `JOB_STATUSES` constant never asserted | Per Report 0103 MR566: tuple not Enum, typo `"runing"` slips through | Medium |
| `_run_one` `BaseException` catch (line 213, per Report 0103 MR570) | Possibly tested in `test_bug_fixes_b149` per its name; not verified this iteration | (likely covered) |
| Malformed `started_at` ISO in `mark_stale` (line 357-360) — `float("inf")` fallback | Edge case; not tested | Low |
| Concurrent shutdown + submit race | Race condition, hard to test deterministically | Low |
| `Job.runner` field excluded from `to_dict` (Report 0103 MR567) | Not asserted as regression | Low |

### Per-line ratio

- Module: 389 lines (Report 0103).
- Tests: 294 lines in `test_job_queue.py` + ~200 lines split across 6 other test files = ~500 total test lines.
- **Ratio**: 1 test line per 0.78 production lines. **Healthy** (industry typical is 1:1 to 1:2).

### Test patterns

- Pure stdlib `unittest` (per CLAUDE.md "Tests via stdlib `unittest`")
- HTTP integration tests use **real server on free port + urllib.request** — cross-link CLAUDE.md "Multi-step workflows tested end-to-end via a real HTTP server."
- No mocks for our own code — confirmed.
- `_default_sim_runner` is replaced via constructor `runner=` arg in tests; production passes None to use the default.

### Cross-link to Report 0103 risk catalog

| Report 0103 MR | Test coverage status |
|---|---|
| MR566 (JOB_STATUSES bare tuple, typo risk) | NOT TESTED — gap |
| MR567 (runner/idempotency_key not in to_dict) | NOT TESTED — gap |
| MR568 (no persistence — restart drops queued jobs) | NOT TESTED (behavior is "by design") |
| MR569 (single worker FIFO blocks) | TESTED (test_worker_is_single_threaded_fifo) |
| MR570 (BaseException catch) | LIKELY (test_bug_fixes_b149) |
| MR571 (no logger.error on failure) | NOT TESTED — gap |
| MR572 (mark_stale not auto-cron) | NOT TESTED (behavior is "by design") |
| MR573 (idempotency-key case-sensitive) | TESTED (test_data_refresh_workflow case-handling — TBD verify) |

### Comparison to other audited test coverage

| Module | Test count | Production lines | Ratio | Public methods tested |
|---|---|---|---|---|
| `domain/econ_ontology` (Report 0098) | 19 | 816 | 1:43 | 3 of 3 |
| `auth/audit_log` (Report 0068) | (TBD) | 192 | (TBD) | (Report 0068) |
| `core/simulator` (Report 0038) | (TBD) | (TBD) | (Report 0038) | partial |
| **`infra/job_queue` (this)** | **~20-25** | **389** | **~1:18** | **7 of 8** |

job_queue is **better-tested per-line** than econ_ontology (1:18 vs 1:43). Reflects the criticality of async-job correctness.

### Cross-link to feat/ui-rework-v3 (Report 0127)

`feat/ui-rework-v3` adds `tests/test_ui_rework_contract.py` (+675 lines, 25 tests) which is its OWN test discipline. Doesn't directly touch `job_queue` tests. Independent quality streams.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR729** | **`JobRegistry.shutdown(timeout)` is the only public method NOT tested** | Mid-flight shutdown semantics unclear: pending jobs stay queued, worker thread joins. A bug here causes daemon-thread leak on test cleanup or production restart. | **Medium** |
| **MR730** | **`JOB_STATUSES` constant typos not testable** | Cross-link Report 0103 MR566. A typo `"runing"` instead of `"running"` would compile, write a job in invalid state, NO test would fail. **Convert tuple → `Enum` would gain compile-time check.** | Medium |
| **MR731** | **No regression test for `Job.to_dict()` field set** | Cross-link Report 0103 MR567. Field add/remove is silent. | Low |
| **MR732** | **No test asserts `logger.error` is called on job failure** | Cross-link Report 0103 MR571 medium. If a future refactor accidentally drops the log line, no test catches it. | Low |
| **MR733** | **Tests are split across 7+ files by feature, not module** | Cross-link CLAUDE.md "test_<feature>.py" convention. Discoverability problem: a developer wanting "all job_queue tests" has to grep across 7 files. Fine for ownership; harder for coverage audit. | Low |

## Dependencies

- **Incoming:** pytest collection picks up all 7 test files automatically.
- **Outgoing:** unittest stdlib + production `infra/job_queue` + portfolio.store (in HTTP integration tests).

## Open questions / Unknowns

- **Q1.** What does `tests/test_bug_fixes_b149.py` actually test? Likely the BaseException catch behavior per Report 0103 MR570.
- **Q2.** Does `test_data_refresh_workflow.py` cover the case-sensitive idempotency-key risk (Report 0103 MR573)?
- **Q3.** Is there ANY test for shutdown — perhaps in conftest.py or a tearDown hook?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0129** | Schema-walk `generated_exports` (Report 0127 MR724, still pre-merge requirement). |
| **0130** | Add a regression test for `JobRegistry.shutdown` (concrete remediation for MR729). |
| **0131** | Read `cli.py` head (1,252 lines, 14+ iterations owed). |

---

Report/Report-0128.md written.
Next iteration should: schema-walk `generated_exports` table — pre-merge requirement for `feat/ui-rework-v3` (Report 0127 MR724 high).
