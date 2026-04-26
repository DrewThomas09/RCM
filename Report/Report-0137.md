# Report 0137: Database Layer — `deal_sim_inputs` SQLite Table

## Scope

Schema-walks `deal_sim_inputs` — **the LAST named-but-unwalked SQLite table** per Reports 0110, 0118, 0134. Closes Report 0110 MR616 backlog. Sister to Reports 0017, 0047, 0077, 0087, 0102, 0104, 0107, 0117, 0123, 0133, 0134.

## Findings

### Schema (deals/deal_sim_inputs.py:43-49)

```sql
CREATE TABLE IF NOT EXISTS deal_sim_inputs (
    deal_id TEXT PRIMARY KEY,
    actual_path TEXT NOT NULL,
    benchmark_path TEXT NOT NULL,
    outdir_base TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
)
```

### Field inventory (5 fields)

| # | Field | Type | NULL? | Default | Note |
|---|---|---|---|---|---|
| 1 | `deal_id` | TEXT PRIMARY KEY | NO | — | unique per deal (ONE inputs row per deal) |
| 2 | `actual_path` | TEXT | NOT NULL | — | path to `actual.yaml` (per Report 0011) |
| 3 | `benchmark_path` | TEXT | NOT NULL | — | path to `benchmark.yaml` |
| 4 | `outdir_base` | TEXT | NOT NULL | `''` | output dir base; empty = caller picks |
| 5 | `updated_at` | TEXT | NOT NULL | — | ISO-8601 UTC |

**5 fields. PRIMARY KEY on deal_id (UPSERT-friendly). NO foreign key. No secondary index** (PK lookup covers all queries).

### Module structure (130 lines)

| Line | Symbol | Public? |
|---|---|---|
| 35 | `_utcnow_iso` | private |
| 39 | `_ensure_table` | private |
| 54 | `set_inputs(store, *, deal_id, actual_path, benchmark_path, outdir_base="")` | **public** |
| 96 | `get_inputs(store, deal_id) -> Optional[Dict[str, str]]` | **public** |
| 115 | `next_outdir(deal_id, outdir_base="") -> str` | **public** (path helper, no DB) |

**3 public functions, 1 path helper.** `set_inputs` and `get_inputs` have docstrings.

### Foreign-key absence (cross-correction to Report 0118 PRAGMA comment)

Per Report 0118 the PRAGMA comment in `portfolio/store.py:99-101` lists:
> "deal_overrides / analysis_runs / mc_simulation_runs / generated_exports raise IntegrityError"

**`deal_sim_inputs` is NOT in that list.** This iteration confirms: NO FK on `deal_sim_inputs.deal_id`.

**But**: `set_inputs:76` calls `store.upsert_deal(deal_id)` BEFORE the INSERT — ensures the parent deals row exists. **Application-level enforcement** of referential integrity, not DDL-level. **MR776 below.**

### Cross-link to Report 0017 deals table

`deals.deal_id` is the join target. Per Report 0017: `deals(deal_id TEXT PRIMARY KEY, ...)` — same key shape. `deal_sim_inputs.deal_id` mirrors that.

**One-to-one** (PRIMARY KEY → only one row per deal_id). Each deal has at most one set of sim inputs.

### `set_inputs` — UPSERT pattern

Lines 78-93: `INSERT ... ON CONFLICT(deal_id) DO UPDATE SET ...`. Same pattern as Report 0107 `set_status` and Report 0134 `set_override`. Atomicity good.

### `get_inputs` — simple SELECT

Returns `Optional[Dict[str, str]]`. **No type cross-validation** — paths could exist or not (per docstring "We do NOT require the files to exist at call time").

### Trust boundary

`actual_path`, `benchmark_path` are **filesystem paths supplied by partners**. Stored verbatim in SQLite. **Path traversal risk**: if a partner sets `actual_path = "../../../etc/passwd"`, then a downstream `open(actual_path)` reads that.

Cross-link Report 0136 MR772 (pyarrow file_loader has no pre-flight validation). Same risk class. **MR777 below.**

### `next_outdir` (line 115) — path helper

Returns auto-incrementing output directory name based on deal_id + base. Pure path logic — no DB.

### Importers (10 production + 3 test)

| File | Use |
|---|---|
| `server.py` | likely `/api/deals/<id>/sim-inputs` route (set/get) |
| `cli.py` | `rcm-mc analysis <deal_id>` reads stored paths |
| `portfolio_cmd.py` | CLI for setting inputs |
| `infra/consistency_check.py` (Report 0110) | orphan check |
| `analysis/packet_builder.py` | reads paths at packet-build time |
| `analysis/analysis_store.py` | possibly cache key derivation |
| `portfolio/store.py` | possibly via init_db helpers |
| `demo.py` (Report 0130) | seeds demo deals |
| `tests/test_rerun_cli_and_alerts_owner.py` | tests |
| `tests/test_bug_fixes_b149.py` | tests |
| `tests/test_deal_sim_inputs.py` | unit tests |

**13 callers total.** Tighter than `PortfolioStore` (237 callers per Report 0124) but heavily used in the deal-rerun flow.

### Cross-link to Report 0103 (job_queue)

`submit_run(*, actual, benchmark, outdir, ...)` uses **the SAME field names** — `actual_path` and `benchmark_path` map directly to `submit_run`'s `actual` and `benchmark` parameters. Likely flow:
1. UI: partner sets paths via `set_inputs(store, deal_id, actual_path, benchmark_path)`
2. UI: partner clicks "rerun" → `JobRegistry.submit_run(actual=stored_actual_path, benchmark=stored_benchmark_path)`
3. Worker: `cli.run_main` reads files

**`deal_sim_inputs` is the storage layer for "remembered rerun parameters."** Cross-link CLAUDE.md "rerun simulation" feature.

### Schema-inventory — COMPLETE for named tables

After this report:

| Table | Walked? | FK? |
|---|---|---|
| `deals` | Report 0017 | (parent) |
| `runs` | Report 0047 | none |
| `analysis_runs` | Report 0077 | (Report 0118 MR678 — claimed FK; not yet verified) |
| `audit_events` | Report 0123 | none |
| `hospital_benchmarks` | Report 0102 | none |
| `webhooks` | Report 0104 | none |
| `webhook_deliveries` | Report 0104 | none |
| `data_source_status` | Report 0107 | none |
| `mc_simulation_runs` | Report 0117 | CASCADE |
| `generated_exports` | Report 0133 | SET NULL |
| `deal_overrides` | Report 0134 | CASCADE |
| **`deal_sim_inputs`** | **0137 (this)** | **none — application-level only** |

**12 tables walked + 0 named-but-unwalked.** Per Report 0091: 22+ tables in DB. **~10 tables remain unidentified** (per `_EXPECTED_TABLES` cross-reference, all 8 tables there are now mapped; the rest are non-expected — possibly `users`, `sessions`, `csrf_log`, `idempotency_log`, `notification_configs`, `task_audit`, `escalations`, `tags`, `notes`, `owners`, `deadlines`, etc.).

### Cross-link to Report 0091 22+ unmapped tables

Per Report 0091 #11: "22 sister SQLite tables beyond `deals` and `runs`." This iteration: **12 walked + ~10+ remaining**. Backlog still substantial.

### Cross-correction summary

Per Report 0118 PRAGMA comment: 4 tables have FKs (`deal_overrides`, `analysis_runs`, `mc_simulation_runs`, `generated_exports`).
- `deal_overrides` → CASCADE ✓ (Report 0134)
- `mc_simulation_runs` → CASCADE ✓ (Report 0117)
- `generated_exports` → SET NULL ✓ (Report 0133)
- `analysis_runs` → **STILL UNVERIFIED** (Report 0118 MR678)

3 of 4 PRAGMA-comment-claimed FKs verified. **`analysis_runs` FK status is the last open question on the FK frontier.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR776** | **`deal_sim_inputs.deal_id` has NO foreign key — application-level enforcement only via `store.upsert_deal()`** | If a future caller skips `upsert_deal` and directly INSERTs into deal_sim_inputs, a non-existent deal_id can be inserted (no DDL constraint). | **Medium** |
| **MR777** | **`actual_path`, `benchmark_path` are user-supplied filesystem paths stored verbatim** | Path traversal risk: `actual_path = "../../etc/passwd"` would store. Downstream `open(actual_path)` would read. **No validation in `set_inputs`.** Cross-link Report 0136 MR772 (similar pattern in pyarrow file_loader). | **High** |
| **MR778** | **`deal_sim_inputs` not in `infra/data_retention.py` policy** | Cross-link Reports 0123 MR705, 0133 MR757. Stale stored paths persist forever (paths to deleted YAML files). | Medium |
| **MR779** | **PRIMARY KEY = deal_id forces ONE inputs row per deal** | A user couldn't have two competing input scenarios per deal. Architectural choice — UPSERT semantics confirm. | (advisory) |
| **MR780** | **`outdir_base TEXT NOT NULL DEFAULT ''`** — empty string default | A blank string is "valid" but useless. `next_outdir(deal_id, outdir_base='')` line 115 likely falls back. The DEFAULT '' chooses-to-allow vs forcing required. | Low |
| **MR616-CLOSED** | **All named SQLite tables are now schema-walked.** 12 tables + 0 named-but-unwalked. ~10 unidentified tables remain (Report 0091 #11). | (closure) |
| **MR678-CARRIED** | **`analysis_runs` FK status is the last open question on the FK frontier** | Report 0118 PRAGMA comment claims it has an FK. Report 0077 didn't see one. Re-verify. | Medium |

## Dependencies

- **Incoming:** 7 production files + 3 tests (per importer count).
- **Outgoing:** stdlib (`datetime`, `typing`, `pathlib` likely); `PortfolioStore.connect()` and `upsert_deal`.

## Open questions / Unknowns

- **Q1.** Why does `deal_sim_inputs` not have a FK while `deal_overrides` (also keyed by deal_id) does? Cross-link Report 0134 MR761 (no documented FK policy).
- **Q2.** Does `set_inputs` validate path safety (no traversal)? Per code: NO — only emptiness check.
- **Q3.** What does the body of `next_outdir` (lines 115-130) compute? Auto-increment, hash-based, or timestamp?
- **Q4.** Is there a test for path-traversal in `actual_path`?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0138** | Re-verify `analysis_runs` FK status (Report 0118 MR678) — last open FK question. |
| **0139** | Read `cli.py` head (1,252 lines, 14+ iterations owed). |
| **0140** | Identify remaining ~10 SQLite tables (per Report 0091 #11 backlog). |
| **0141** | Bug-fix PR for MR770 critical (pyarrow CVE) + MR777 high (path traversal in set_inputs). |

---

Report/Report-0137.md written.
Next iteration should: re-verify `analysis_runs` FK status (Report 0118 MR678) — last open question on the FK frontier.
