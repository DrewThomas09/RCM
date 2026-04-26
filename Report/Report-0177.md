# Report 0177: Schema Inventory — `Job` dataclass (Report 0103 expansion)

## Scope

Re-walks `Job` dataclass at `infra/job_queue.py:55-97` (per Report 0103 partial). Sister to Reports 0027 (ServerConfig), 0057 (DealAnalysisPacket), 0103 (job_queue API).

## Findings

### Re-walk per Report 0103 inventory

| Field | Type | Default | Serialized? |
|---|---|---|---|
| `job_id` | str | required | YES |
| `status` | str | required | YES |
| `created_at` | str | required | YES |
| `kind` | str | required | YES |
| `params` | Dict[str, Any] | `field(default_factory=dict)` | YES (deep-copied) |
| `started_at` | Optional[str] | None | YES |
| `finished_at` | Optional[str] | None | YES |
| `output_tail` | str | "" | YES |
| `error` | Optional[str] | None | YES |
| `result` | Dict[str, Any] | `field(default_factory=dict)` | YES |
| `runner` | Optional[Callable] | None | **NO** (not serializable) |
| `idempotency_key` | Optional[str] | None | **NO** (internal-only) |

**12 fields. 10 serialized + 2 internal-only.**

### Cross-correction Report 0117 MR670

Per Report 0117 MR670: `_mc_from_dict` whitelist drops new fields silently. **Job.to_dict has the SAME risk** — adding a 13th field to Job without updating to_dict produces stale-shape JSON.

### `JOB_STATUSES` discriminator (Report 0103 cross-link)

Per Report 0103: `JOB_STATUSES = ("queued", "running", "done", "failed")` — bare tuple. **`status: str` field stores one of these.** No CHECK at field level (per dataclass semantics).

Per Report 0103 MR566: should be Enum, not bare tuple. **Field-level**: `status: str` should be `status: JobStatus` (Enum).

### Cross-link to Report 0157 MR853 + Report 0167 schema-walk

Per Report 0167: `initiative_actuals` schema-walked. **Job dataclass is NOT a SQLite table** — it's in-memory (Report 0103 module-level `_DEFAULT_REGISTRY`). Different storage tier.

### `Job` instances flow

Per Report 0103 + 0128:
- Created in `submit_run` (line 248-264) and `submit_callable` (line 287-305)
- Mutated in `_run_one` (line 195-228) — status / started_at / finished_at / output_tail / error / result
- Read via `get` (line 307), `list_recent` (line 311), `wait` (line 317)

**Mutation pattern**: dataclass is intentionally mutable (no `frozen=True`). Cross-link Report 0095 (`MetricDefinition` is frozen vs Job mutable).

### Comparison to other audited dataclasses

| Dataclass | Lines | Fields | Serialized | Frozen? |
|---|---|---|---|---|
| `MetricDefinition` (Report 0098) | (TBD) | various | YES via to_dict | likely YES |
| `ScrubReport` (Report 0164) | 30L | 7 | YES | NO (default_factory used) |
| `DealAnalysisPacket` (Report 0057) | many | many | YES | TBD |
| `MonteCarloResult` (Report 0117) | (TBD) | 13 | YES (zlib-compressed) | TBD |
| **`Job` (Report 0103/0177)** | 30L | **12** | **10 of 12** | **NO** (mutable by design) |

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR919** | **`Job.to_dict` excludes `runner` + `idempotency_key`** — same risk class as Report 0117 MR670 (silent field-drop) | Adding a 13th field to `Job` without updating `to_dict` silently drops it. **Should add an `__all_fields__` introspection assertion test.** | Medium |
| **MR920** | **`Job.status: str` instead of `Job.status: JobStatus` (Enum)** | Cross-link Report 0103 MR566 + Report 0117 MR566 (bare tuple as enum surrogate). Type-checker can't validate values. | Medium |

## Dependencies

- **Incoming:** Report 0103, 0128.
- **Outgoing:** stdlib (dataclasses, datetime, typing).

## Open questions / Unknowns

None new — Report 0103 already covered.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0178** | Config trace (in flight). |

---

Report/Report-0177.md written.
