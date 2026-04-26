# Report 0102: Data Flow Trace — `POST /api/data/refresh/<source>`

## Scope

Traces a single HTTP POST through every hop until SQLite is written. Closes Report 0085 Q1 (which routes call RateLimiter) + Report 0093 MR512 (`hospital_benchmarks` schema). Sister to Report 0072 (audit-event flow), Report 0012 (actual.yaml flow).

## Findings

### Hop-by-hop trace

#### Hop 1 — HTTP entry

**`server.py:16056-16091`**: sync handler matches `len(parts) == 4 and parts[0] == "api" and parts[1] == "data" and parts[2] == "refresh"`. Source name extracted: `urllib.parse.unquote(parts[3])`.

**`server.py:16093-16147`**: async variant matches `len(parts) == 5 ... parts[4] == "async"`. Same path prefix; appends `/async` for background-job mode.

#### Hop 2 — Validate source

**`server.py:16066-16072`**: `source not in dr.KNOWN_SOURCES` → 400 `UNKNOWN_SOURCE`.

**`data/data_refresh.py:36-44`** declares `KNOWN_SOURCES`:

```python
KNOWN_SOURCES: Tuple[str, ...] = (
    "hcris", "care_compare", "utilization",
    "irs990", "cms_pos", "cms_general", "cms_hrrp",
)
```

**7 sources** — never enumerated in any prior report.

#### Hop 3 — Rate-limit check

**`server.py:42`**: `from .infra.rate_limit import RateLimiter` — closes Report 0085 Q1 source-import.

**`server.py:48`**: `_REFRESH_RATE_LIMITER = RateLimiter(max_hits=1, window_secs=3600)` — module-level singleton. **1 hit per hour per source.**

**`server.py:16074`**: `ok, wait = _REFRESH_RATE_LIMITER.check(f"refresh:{source}")`.

**`server.py:16075-16082`**: on rate-limit failure → 429 `RATE_LIMITED` + `retry_after_seconds`.

**Async variant `server.py:16115`**: keys with `f"refresh:{source}:async"` (note: different key from sync — sync and async run in parallel).

#### Hop 4 — Orchestrator

**`server.py:16084`**: `report = dr.refresh_all_sources(store, sources=sources)`.

**`data/data_refresh.py:397-450 refresh_all_sources`**:

1. `_ensure_tables(store)` → idempotent CREATE.
2. `refreshers = _default_refreshers()` → 7 lazy refreshers.
3. `selected = list(sources) if sources else list(KNOWN_SOURCES)`.
4. For each source: `count = int(fn(store) or 0)`; capture elapsed; record.
5. Catch `Exception` (with `noqa: BLE001` — partial failures tolerated).
6. Log warning + debug-level traceback.
7. `set_status(store, name, status=_STATUS_OK | _STATUS_ERROR, ...)`.
8. Return `RefreshReport`.

#### Hop 5 — Schema (CLOSES Report 0093 MR512)

**`data/data_refresh.py:62-90 _ensure_tables`** creates `hospital_benchmarks`:

| Field | Type | NULL? | Purpose |
|---|---|---|---|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | NO | rowid |
| `provider_id` | TEXT | NOT NULL | hospital identifier (CCN) |
| `source` | TEXT | NOT NULL | one of KNOWN_SOURCES |
| `metric_key` | TEXT | NOT NULL | per `domain/econ_ontology.METRIC_ONTOLOGY` |
| `value` | REAL | YES | numeric reading |
| `text_value` | TEXT | YES | non-numeric reading |
| `period` | TEXT | YES | e.g. `2024Q3` |
| `loaded_at` | TEXT | NOT NULL | ISO-8601 UTC |
| `quality_flags` | TEXT | YES | freeform |

Plus index `ix_hb_provider` (line 84-85).

**Closes Report 0093 MR512.** Schema is well-formed but free-form `metric_key` (no FK to `METRIC_ONTOLOGY` as enum) — typo-prone (cf. Report 0087 MR483 audit_events same issue).

#### Hop 6 — Per-source refreshers

**`data/data_refresh.py:352-394 _default_refreshers`** — lazy imports for 7 source modules:

| Source | Module | Function |
|---|---|---|
| hcris | `data/cms_hcris.py` | `refresh_hcris_source` |
| care_compare | `data/cms_care_compare.py` | `refresh_care_compare_source` |
| utilization | `data/cms_utilization.py` | `refresh_utilization_source` |
| irs990 | `data/irs990_loader.py` | `refresh_irs990_source` |
| cms_pos | `data/cms_pos.py` | `refresh_pos_source` |
| cms_general | `data/cms_hospital_general.py` | `refresh_general_source` |
| cms_hrrp | `data/cms_hrrp.py` | `refresh_hrrp_source` |

**7 NEW UNREPORTED MODULES.** Never seen in any prior audit. Each likely 100s-1000s of lines of CMS parsing logic.

#### Hop 7 — Each refresher writes to `hospital_benchmarks` + sets status

Per pattern: each refresher returns an `int` record count. Caller wraps it into `RefreshSourceResult`.

#### Hop 8 — Status table

**`set_status` at `data/data_refresh.py:242`** — referenced by `refresh_all_sources` lines 422, 434, 445. Writes to `data_source_status` table — **also created by `_ensure_tables`**. Schema not fully extracted this iteration (Q3 below).

#### Hop 9 — Response

**Sync**: `self._send_json(report.to_dict())` returns `{started_at, finished_at, per_source[], total_records, any_errors}`.

**Async**: `self._send_json({"job_id": job_id, "status_url": f"/api/jobs/{job_id}", ...}, status=202)`.

#### Hop 10 (async only) — Job queue

**`server.py:16101`**: `from .infra.job_queue import get_default_registry`.

**`server.py:16136-16141`**:

```python
job_id = get_default_registry().submit_callable(
    kind="data_refresh",
    runner=_refresh_runner,
    params={"source": source, "sources": sources},
    idempotency_key=f"data_refresh:{source}",
)
```

**`infra/job_queue.py`** — NEVER REPORTED. New module discovery.

`_refresh_runner` closure (line 16128-16134) re-opens the store inside a worker thread (since the `store` from request thread isn't shared safely). Cross-link Report 0008 store thread-safety.

### Cross-link to second rate-limiter discovered

**`server.py:49`**: `_DELETE_RATE_LIMITER = RateLimiter(max_hits=10, window_secs=3600)`. **10 hits/hr** — different threshold. Used for some delete path (TBD; not in this report's scope).

**Closes Report 0085 partial: 2 RateLimiter instances exist, not 1.**

### CMS download — fail-open posture

Per `infra/rate_limit.py` docstring (Report 0085): "Fails open on process restart." So if the server restarts, the 1-hit-per-hour budget resets. Combined with rate-limit applied AFTER source-validation, an attacker could iterate on misspelled sources without ever consuming budget. **Cross-link Report 0085 MR475 — this surface is rate-limited; auth IS NOT.**

### Number of error paths

In the sync flow alone:
1. Path-mismatch (no match) — falls through to next handler
2. Unknown source → 400
3. Rate-limited → 429
4. Refresher exception → 500
5. Per-source partial failure → captured in report (200 + any_errors=true)

**5 distinct response shapes.** Only #4 is "hard failure"; #5 is "soft failure" (200 OK with errors flagged in payload). Cross-link Report 0020 (packet_builder error handling).

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR558** | **7 NEW unreported CMS data-loader modules** (`cms_hcris`, `cms_care_compare`, `cms_utilization`, `irs990_loader`, `cms_pos`, `cms_hospital_general`, `cms_hrrp`) | Foundational data path; never audited. Likely thousands of lines combined. | **Critical** |
| **MR559** | **`infra/job_queue.py` never reported** | Powers async refresh + presumably analysis-build async. New unmapped module. | **High** |
| **MR560** | **`hospital_benchmarks.metric_key` is free-form TEXT, no FK to METRIC_ONTOLOGY** | Same pattern as Report 0087 MR483 (audit_events.event_type). A typo silently writes a row that no consumer will read. | Medium |
| **MR561** | **Sync + async share refresh budget on different KEY** (`refresh:{source}` vs `refresh:{source}:async`) | An attacker could alternate sync/async to double the budget. Likely intentional but not documented. | Low |
| **MR562** | **Validation-before-rate-limit** (line 16066 vs 16074) | Spamming unknown source names doesn't burn rate-limit budget. Per-IP rate limit absent — repeated 400s could DoS via parsing. | Medium |
| **MR563** | **`infra/rate_limit.py` failure mode (in-memory + restart-clears)** allows refresh-storm-on-restart | If server restarts during high traffic, budget resets — could trigger CMS downloads concurrently. | Low |
| **MR564** | **`set_status` and `data_source_status` table never schema-walked** | A 2nd unmapped foundation table (alongside `hospital_benchmarks` until this report). | Medium |
| **MR565** | **Per-source refreshers raise broad Exception, caught with noqa BLE001** | Per Report 0020 broad-except discipline: `except Exception` is intentional for partial-failure tolerance, but masks programmer errors (TypeError, AttributeError). | Low |

## Dependencies

- **Incoming:** Browser POST, scheduled cron (per CLAUDE.md "data refresh"), CLI command (per Report 0048 `python -m rcm_mc data refresh`).
- **Outgoing:** `infra/rate_limit.RateLimiter`, `data/data_refresh.refresh_all_sources`, `_default_refreshers()` → 7 CMS modules → SQLite `hospital_benchmarks` table.

## Open questions / Unknowns

- **Q1.** What does each of the 7 CMS refresher modules actually do? (HTTP fetch vs cached file vs parquet vs FTP?)
- **Q2.** What is the schema of `data_source_status` (the second table created by `_ensure_tables`)?
- **Q3.** What is `infra/job_queue.py`'s public surface? Idempotency-key semantics, persistence, retry policy?
- **Q4.** Is `_DELETE_RATE_LIMITER` (10 hits/hr) hooked to any specific delete route, and which?
- **Q5.** Does the CLI path `rcm-mc data refresh` (per CLAUDE.md) bypass HTTP / rate-limit entirely?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0103** | Map `infra/job_queue.py` end-to-end (closes Q3, MR559). |
| **0104** | Schema-walk `data_source_status` (closes Q2, MR564). |
| **0105** | Sample-audit `cms_hcris.py` (closes Q1 partial; closes MR558 partial). |
| **0106** | Map `rcm_mc_diligence/` separate package (still pending). |

---

Report/Report-0102.md written.
Next iteration should: map `infra/job_queue.py` — closes Q3 + MR559 high (powers all async refresh paths).
