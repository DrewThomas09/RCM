# Report 0107: Database Layer — `data_source_status` SQLite Table

## Scope

Schema-walks `data_source_status` (sister table to `hospital_benchmarks` per Report 0102). Closes Report 0102 Q2 + MR564, deferred over Reports 0103, 0104, 0105, 0106. Sister to Reports 0017 (deals), 0047 (runs), 0077 (analysis_runs), 0087 (audit_events), 0102 (hospital_benchmarks), 0104 (webhooks + webhook_deliveries).

## Findings

### Definition

`data/data_refresh.py:97-107` (`_ensure_tables`):

```sql
CREATE TABLE IF NOT EXISTS data_source_status (
    source_name TEXT PRIMARY KEY,
    last_refresh_at TEXT,
    record_count INTEGER DEFAULT 0,
    next_refresh_at TEXT,
    status TEXT,
    error_detail TEXT,
    interval_days INTEGER DEFAULT 30
)
```

**7 fields.** No secondary indexes (PRIMARY KEY on source_name covers lookups).

### Field-by-field inventory

| Field | Type | Constraint | Note |
|---|---|---|---|
| `source_name` | TEXT | **PRIMARY KEY** | one of `KNOWN_SOURCES` (per Report 0102: 7 sources) |
| `last_refresh_at` | TEXT | (nullable) | ISO-8601 UTC; NULL until first refresh |
| `record_count` | INTEGER | DEFAULT 0 | rows ingested in last successful refresh |
| `next_refresh_at` | TEXT | (nullable) | NULL when status=ERROR (no auto-reschedule on error) |
| `status` | TEXT | (free-form) | "OK" / "STALE" / "ERROR" per `_STATUS_*` constants (lines 47-49) |
| `error_detail` | TEXT | (nullable) | exception message; only populated on ERROR |
| `interval_days` | INTEGER | DEFAULT 30 | refresh cadence; configurable per source |

### Status state machine

Per `set_status` (line 242) + `mark_stale_sources` (line 453):

```
        ┌──────────┐  refresh OK     ┌──────────┐
   →    │  STALE   │ ──────────────► │    OK    │
        └──────────┘                 └──────────┘
              ▲                             │
              │                             │ next_refresh_at < now
              │                             ▼
              │                       ┌──────────┐
              │   refresh fails       │  STALE   │
              ◄────────────────────── └──────────┘
                                            │
                                            ▼
                                      ┌──────────┐
                                      │  ERROR   │ (terminal until manual fix)
                                      └──────────┘
```

ERROR is **terminal in the auto path** — `set_status` line 253: `nxt = _next_refresh(...) if status != _STATUS_ERROR else None`. ERROR rows have NULL `next_refresh_at`, so `mark_stale_sources` skips them (line 463-464). **Manual operator intervention required to recover.**

### Code sites — WRITE (3)

| Site | Operation | Trigger |
|---|---|---|
| `data/data_refresh.py:255-269 set_status` | UPSERT via `ON CONFLICT(source_name)` | Per-source refresh result (called from `refresh_all_sources` lines 422, 434, 445) |
| `data/data_refresh.py:303-310 schedule_refresh` | INSERT (only if absent) | Seed function — one row per `KNOWN_SOURCES` member |
| `data/data_refresh.py:476-479 mark_stale_sources` | UPDATE status='STALE' | Cron-style sweep when `next_refresh_at < now` |

**3 writers, all in `data/data_refresh.py`.** Single-source-of-truth pattern.

### Code sites — READ (10+)

| Site | Use |
|---|---|
| `data/data_refresh.py:273-285 get_status` | Primary read API; by name or all |
| `data/data_refresh.py:462 mark_stale_sources` | Iterates via `get_status(store)` |
| `data/data_refresh.py:300-302 schedule_refresh` | Existence check before INSERT (idempotency) |
| `tests/test_data_refresh_workflow.py` | Workflow assertions |
| `tests/test_data_refresh.py` | Unit tests |
| `tests/test_hardening.py` | Failure-mode tests |
| `tests/test_dashboard_since_yesterday.py` | UI rendering test |
| `tests/test_phase_mn.py` | Phase M/N integration tests |
| `cli.py` | `rcm-mc data status` CLI |
| `server.py` | `/api/data/status` API + `/data/refresh` UI |
| `ui/data_refresh_page.py` | Dashboard page render |
| `ui/dashboard_page.py` | Dashboard summary widget |
| `infra/consistency_check.py` | **NEW UNMAPPED MODULE** |
| `analysis/refresh_scheduler.py` | **NEW UNMAPPED MODULE** |

### HIGH-PRIORITY DISCOVERIES

| Module | Status |
|---|---|
| `RCM_MC/rcm_mc/infra/consistency_check.py` | **never reported** in 106 prior iterations |
| `RCM_MC/rcm_mc/analysis/refresh_scheduler.py` | **never reported** in 106 prior iterations |

Both modules **read** `data_source_status` — likely orchestrate the refresh cadence (refresh_scheduler) and validate cross-table consistency (consistency_check).

### UPSERT pattern

`set_status` uses SQLite's native UPSERT (`ON CONFLICT(source_name) DO UPDATE`) — Reports 0017 + 0027 mention `BEGIN IMMEDIATE` for check-then-write but `set_status` skips that since UPSERT is atomic. **Cleaner pattern than transactional check-then-write.**

### Idempotency

`schedule_refresh` (line 288-311) is documented as "Safe to call repeatedly. Does NOT trigger a refresh — just records the schedule." Existing rows preserved. **Strong idempotency.**

### Cross-link to Report 0091 (schema gap)

Per Report 0091: 22+ tables unmapped. Schema-walk count after this report:

| Table | Source report |
|---|---|
| `deals` | 0017 |
| `runs` | 0047 |
| `analysis_runs` | 0077 |
| `audit_events` | 0087 |
| `hospital_benchmarks` | 0102 |
| `webhooks` | 0104 |
| `webhook_deliveries` | 0104 |
| `data_source_status` | **0107 (this)** |

**8 tables mapped. ~14+ remain.**

### Cross-link to project-wide event-string pattern

`status` field is free-form TEXT with 3 known values (`OK`/`STALE`/`ERROR`). No CHECK constraint. Same pattern as:
- `audit_events.event_type` (Report 0087 MR483)
- `hospital_benchmarks.metric_key` (Report 0102 MR560)
- `webhooks.events` (Report 0104 MR580)
- `Job.kind` (per Report 0103: `"sim_run"`, `"data_refresh"`, etc.)

**Project-wide convention: free-form text classifications, no enum enforcement.** MR580 (Report 0104) escalates further.

### Schema-evolution risk

A new `KNOWN_SOURCES` entry → `schedule_refresh` will seed it on next call. **No ALTER TABLE needed.** Per Report 0017: idempotent CREATE pattern is the codebase's migration story.

But: a new STATUS value (e.g. `"PARTIAL"`) → readers in `ui/data_refresh_page.py` likely have a fixed-set rendering switch. Adding without updating consumers leads to silent misrendering.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR597** | **`infra/consistency_check.py` and `analysis/refresh_scheduler.py` never reported** | 2 NEW unmapped modules touching the data refresh state machine. **HIGH-PRIORITY**. | **High** |
| **MR598** | **`status TEXT` is free-form, no CHECK constraint** | Cross-link Report 0104 MR580 project-wide pattern. A typo writes a row that auto-recovery rules silently skip. | Medium |
| **MR599** | **ERROR is terminal — no auto-recovery** | Per `set_status` line 253. A transient failure (CMS down for 30 min) puts the source in ERROR until an operator manually re-runs. No retry-after-N-hours. | **High** |
| **MR600** | **No retention/cleanup for `data_source_status`** | Table is small (≤7 rows = `len(KNOWN_SOURCES)`), so growth-unbounded isn't an issue. But `error_detail` accumulates the last-error text indefinitely; a multi-day outage's traceback persists until next success. | Low |
| **MR601** | **PRIMARY KEY on `source_name` means one row per source** | Schema cannot represent "this source had 3 partial-success refreshes today" — only the latest. Audit trail lost. **Cross-link Report 0102 MR558** (7 unaudited CMS modules each return only the latest count). | Medium |
| **MR602** | **`mark_stale_sources` cron is operator-invoked**, no auto-timer (cross-link Report 0103 MR572 mark_stale pattern) | If operator forgets, sources stay "OK" past their `next_refresh_at` date. Silently stale. | Medium |
| **MR603** | **3 unique-but-undocumented column semantics**: `last_refresh_at`, `next_refresh_at`, `interval_days` | None has docstring on `_ensure_tables` (per Report 0104 doc-gap pattern). New developers must read `set_status`/`mark_stale_sources` to understand semantics. | Low |

## Dependencies

- **Incoming:** see READ + WRITE sections above. Total ~13 production sites + tests.
- **Outgoing:** SQLite via `PortfolioStore.connect()`.

## Open questions / Unknowns

- **Q1.** What does `infra/consistency_check.py` do, and how does it use `data_source_status`?
- **Q2.** What does `analysis/refresh_scheduler.py` do — is it a cron-style scheduler or just a query helper?
- **Q3.** Does `mark_stale_sources` ever run automatically (cron / startup hook), or only when an operator hits a specific UI button?
- **Q4.** Is there a `/api/data/status` endpoint? Per the read sites above, server.py touches `data_source_status` — confirm route.
- **Q5.** What's the recovery path for a source stuck in ERROR? Manual `rcm-mc data refresh <source>` retry? Auto-retry after N hours?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0108** | Read `infra/consistency_check.py` (closes Q1, MR597 partial). |
| **0109** | Read `analysis/refresh_scheduler.py` (closes Q2, MR597 partial). |
| **0110** | Map `rcm_mc_diligence/` separate package (carried 7+ iterations). |
| **0111** | Audit `plotly` (`[interactive]` extra, per Report 0106 follow-up). |

---

Report/Report-0107.md written.
Next iteration should: read `infra/consistency_check.py` to close Q1 + half of MR597 high.
