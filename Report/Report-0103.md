# Report 0103: API Surface — `infra/job_queue.py`

## Scope

Documents the public API of `RCM_MC/rcm_mc/infra/job_queue.py` (389 lines). Closes Report 0102 MR559 high. Sister to Reports 0085 (rate_limit), 0034 (infra/config incoming).

## Findings

### Module purpose

Per docstring (lines 1-32): in-process simulation job queue for the web UI. Single worker thread, in-memory registry keyed by UUID, no persistence across restarts. Pluggable runner.

**4 design constraints documented in source:**
1. Single-process, in-memory (no Redis/Celery)
2. One worker thread (CPU-bound MC + serial SQLite writes)
3. Pluggable runner (test override)
4. No persistence across restarts ("orphaned" jobs after restart)

### Public exports

| Name | Kind | Line |
|---|---|---|
| `JOB_STATUSES` | tuple constant | 52 |
| `Job` | dataclass | 56 |
| `JobRegistry` | class | 149 |
| `get_default_registry` | function | 376 |
| `reset_default_registry` | function | 384 |

**5 public exports.**

### `JOB_STATUSES = ("queued", "running", "done", "failed")`

Tuple, not Enum. Order is documented: `queued → running → (done | failed)` linear flow, no backward moves.

**Anti-pattern**: should be `Enum`, not bare-tuple. Per Report 0094 `domain/econ_ontology` uses Enums for similar state classifications. Inconsistent.

### `class Job` (dataclass) — full field inventory

| Field | Type | Default | Serialized? |
|---|---|---|---|
| `job_id` | `str` | — (required) | YES |
| `status` | `str` | — (required) | YES |
| `created_at` | `str` | — (required) | YES |
| `kind` | `str` | — (required) | YES |
| `params` | `Dict[str, Any]` | `field(default_factory=dict)` | YES (deep-copied via `dict(...)`) |
| `started_at` | `Optional[str]` | `None` | YES |
| `finished_at` | `Optional[str]` | `None` | YES |
| `output_tail` | `str` | `""` | YES |
| `error` | `Optional[str]` | `None` | YES |
| `result` | `Dict[str, Any]` | `field(default_factory=dict)` | YES |
| `runner` | `Optional[Callable]` | `None` | **NO** — internal-only |
| `idempotency_key` | `Optional[str]` | `None` | **NO** — internal-only |

**Method**: `to_dict() -> Dict[str, Any]` (line 85-97). Deep-copies `params` and `result`. Excludes `runner` and `idempotency_key`.

### `class JobRegistry` — full method signature catalog

#### Constructor
```python
__init__(self, *, runner=None, output_tail_lines=80) -> None
```
- `runner`: Optional default runner; falls back to `_default_sim_runner` (line 110)
- `output_tail_lines=80`: how many trailing stdout lines to retain per job

#### Public submit-style methods

```python
submit_run(self, *, actual: str, benchmark: str, outdir: str,
           n_sims: int = 5000, seed: int = 42,
           no_report: bool = False, partner_brief: bool = False,
           portfolio_register: bool = True) -> str
```
- Queues a `kind="sim_run"` job. Returns `job_id` (12-char hex prefix of UUID4).
- 8 named params; all kwargs-only (per `*`).
- **Cross-link Report 0027**: many of these mirror `ServerConfig` / CLI defaults.

```python
submit_callable(self, *, kind: str,
                runner: Callable[[Dict[str, Any]], Dict[str, Any]],
                params: Optional[Dict[str, Any]] = None,
                idempotency_key: Optional[str] = None) -> str
```
- Queues a generic-kind job with caller-supplied runner.
- **Idempotency semantics**: if a queued/running job with same key exists → returns its job_id. Terminal-state jobs (done/failed) DON'T block new submits.
- Used by `data_refresh` per Report 0102 hop 10.

#### Public read methods

```python
get(self, job_id: str) -> Optional[Job]                                  # line 307
list_recent(self, n: int = 20) -> List[Job]                              # line 311 (newest-first)
wait(self, job_id: str, timeout: float = 5.0) -> Optional[Job]           # line 317 (test helper)
```

#### Public maintenance methods

```python
shutdown(self, timeout: float = 2.0) -> None                             # line 230
mark_stale(self, *, max_age_seconds: float = 3600.0,
           reason: str = "marked stale by operator") -> List[str]        # line 331
```

`mark_stale` is the **operator-recovery hook** for orphaned jobs after restart (per docstring line 333-345). Returns the list of transitioned job_ids.

### Module-level singleton

```python
get_default_registry() -> JobRegistry      # line 376 — lazy-init on first call
reset_default_registry() -> None           # line 384 — drops the global, for tests
```

`_DEFAULT_REGISTRY: Optional[JobRegistry]` (line 373) is the global slot.

### Private surface (internal-only)

| Name | Line | Purpose |
|---|---|---|
| `_default_sim_runner` | 110 | Production fallback runner — calls `rcm_mc.cli.run_main` |
| `_utcnow` | 100 | ISO timestamp helper |
| `_ensure_worker` | 170 | Lazy-start worker thread |
| `_worker_loop` | 185 | Daemon-thread main loop |
| `_run_one` | 195 | Per-job execution + stdout capture + result/error population |

Plus instance attributes `_jobs`, `_order`, `_lock`, `_queue`, `_runner`, `_output_tail_lines`, `_worker_thread`, `_worker_started`, `_shutdown`.

### Documentation quality

Module docstring (lines 1-32): well-written. Documents 4 constraints + sample API usage.
Class docstrings: present on `Job` and `JobRegistry`.
Method docstrings: present on all public methods.

**`submit_run` is missing a Returns description** (line 247: `"""Queue a simulation run. Returns the new ``job_id``."""`). Wait — it IS there. Confirmed.

`submit_callable` has explicit idempotency-key explainer (lines 281-285). Good.

### Threading discipline

- All access to `_jobs` / `_order` is under `self._lock`.
- Worker thread is a daemon (line 178: `daemon=True`) — won't block process exit.
- `_run_one` redirects stdout/stderr per-job (line 208) for output_tail capture.
- `BaseException` (not `Exception`) caught at line 213 — prevents KeyboardInterrupt / SystemExit from killing worker.

### Cross-correction to CLAUDE.md

CLAUDE.md known-limitations section says: "In-memory job queue; jobs lost on restart. OK for partner-driven rerun (they'll just click rerun again) but not for critical cron runs — those should go via the CLI directly." **Confirmed** by this report — explicit module design.

CLAUDE.md does not name `infra/job_queue.py`. **Architecture doc gap.**

### Cross-link to Report 0024 logging

Per `_run_one` (line 213): `BaseException` caught with `noqa: BLE001`. Per Report 0020 broad-except discipline: this is intentional + documented. Comment says "one bad runner should not kill the shared worker thread."

But: the failure is recorded to `job.error` only. **No `logger.error(...)` call.** Per Report 0024: this is Pattern A or no-logger. If a runner fails repeatedly with the same root cause, only the JobRegistry.list_recent() shows it; nothing is in syslog/journal.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR566** | **`JOB_STATUSES` is a bare tuple, not an Enum** | Inconsistent with `domain/` which uses Enum. A typo in `job.status = "runing"` slips through. | Medium |
| **MR567** | **`runner` and `idempotency_key` fields excluded from `to_dict()`** | Sensible (callable not JSON-serializable) but if a caller round-trips a Job through `to_dict → from_dict` they lose runner attachment. No `from_dict` exists; not currently a problem but a future bug. | Low |
| **MR568** | **No persistence — restart drops all queued jobs silently** | Per CLAUDE.md known-limitation. `mark_stale` recovers `running` jobs, but `queued` jobs that never started are lost without trace. | **Medium** |
| **MR569** | **Single worker thread + idempotency-key bypass** | If a runner blocks for 1+ hour (large CMS download per Report 0102 MR558), all queued jobs wait. Idempotency only blocks dup-submit; it doesn't bypass the FIFO. | **High** |
| **MR570** | **`_run_one` catches `BaseException` (not `Exception`)** | Intentional + documented at line 213. But `BaseException` includes `SystemExit` — if production code calls `sys.exit()` inside a runner, it's silently swallowed instead of stopping the process. | Medium |
| **MR571** | **No call to `logger.error(...)` on job failure** | Cross-link Report 0024 logging cross-cut. Failures only visible via `list_recent` UI; ops can't grep journal. | **Medium** |
| **MR572** | **`mark_stale` is operator-invoked, never auto-cron** | Per docstring 337: "Operators run this periodically." No background timer enforces it. Stuck-running jobs can persist indefinitely if no operator action. | Low |
| **MR573** | **Idempotency-key compares strings exactly** (line 292) | Whitespace/case differences treat as different keys. `data_refresh:hcris` ≠ `data_refresh:HCRIS`. Per Report 0102 hop 10 the key is constructed from URL component — case-sensitivity may surprise. | Low |
| **MR574** | **CLAUDE.md does not document `infra/job_queue.py`** | Cross-link Report 0093 MR503 critical CLAUDE.md doc rot. Adds another foundation module to the "missing from architecture diagram" list. | Medium |

## Dependencies

- **Incoming:** server.py (3+ async POST routes — sim_run, data_refresh sync/async per Report 0102), tests.
- **Outgoing:** stdlib only (`contextlib`, `io`, `os`, `queue`, `threading`, `traceback`, `uuid`, `dataclasses`, `datetime`, `typing`). Lazy-imports `rcm_mc.cli.run_main` inside `_default_sim_runner` (line 110+).

## Open questions / Unknowns

- **Q1.** What is the body of `_default_sim_runner` (line 110)? It calls `rcm_mc.cli.run_main` per docstring — but `rcm_mc/cli.py` is per Report 0091 still 1,252 unmapped lines.
- **Q2.** Body of `reset_default_registry` (line 384)?
- **Q3.** Are there any **other** call sites to `submit_callable` besides data_refresh (Report 0102)? Grep needed.
- **Q4.** Does the `/api/jobs/<id>` endpoint (per Report 0102 hop 10 link) call `get(job_id)` directly? Cross-link server.py routes.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0104** | Schema-walk `data_source_status` (per Report 0102 Q2). |
| **0105** | Read `cli.py` head (closes Q1 + breaks 14-iteration debt per Report 0091). |
| **0106** | Grep `submit_callable\|submit_run` call-sites (closes Q3). |
| **0107** | Map `rcm_mc_diligence/` separate package (deferred since Report 0101). |

---

Report/Report-0103.md written.
Next iteration should: schema-walk the `data_source_status` table — sibling to `hospital_benchmarks` per Report 0102, also unmapped (closes Report 0102 Q2 + MR564).
