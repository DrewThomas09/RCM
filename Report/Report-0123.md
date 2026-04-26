# Report 0123: Map Next Key File — `infra/data_retention.py` (+ Report 0087 cross-correction)

## Scope

Reads `RCM_MC/rcm_mc/infra/data_retention.py` end-to-end (79 lines). **Closes Report 0117 MR672 high** + **Report 0087 MR487 high**. Sister to Report 0072 (audit-event retention concern).

**MAJOR cross-correction**: Report 0087 (`audit_events` schema) was substantially wrong — actual schema verified this iteration via `audit_log.py:42-50`.

## Findings

### Module structure

- **79 lines, 2 public functions, 1 constant.**
- **Public surface**:
  - `DEFAULT_RETENTION_DAYS: Dict[str, int]` — 5-table policy
  - `enforce_retention(store, policy=None) -> Dict[str, int]`
  - `export_user_data(store, user_id, out_dir) -> Path`
- **Per docstring (lines 1-5)**: "Configurable retention per table; `enforce_retention` deletes rows older than policy. `export_user_data` for GDPR-style data export."

### `DEFAULT_RETENTION_DAYS` (lines 16-22)

| Table | Days | Months | Cross-link |
|---|---|---|---|
| `analysis_runs` | 730 | 24 | Report 0077 |
| `mc_simulation_runs` | 365 | 12 | Report 0117 (closes the retention Q) |
| `audit_events` | 1,095 | 36 | Report 0087 MR487 (closes — high → resolved) |
| `sessions` | 30 | 1 | Report 0090 (new — sessions retention is 30d, not "indefinite") |
| `webhook_deliveries` | 90 | 3 | Report 0104 (new — webhook deliveries kept 3 months) |

**5 tables policed.** Notable absences: `deals`, `runs`, `hospital_benchmarks`, `data_source_status`, `webhooks`, `users`, `deal_overrides`. **Most tables retained indefinitely** (deliberate per their nature).

### `enforce_retention()` flow (lines 25-54)

1. `cutoff = (now - timedelta(days=days)).isoformat()` — UTC ISO-8601.
2. Per-table timestamp column lookup (line 36-42 dict):
   - `analysis_runs.created_at`
   - `mc_simulation_runs.created_at`
   - **`audit_events.at`** ← **NOT `event_at`!**
   - `sessions.created_at`
   - `webhook_deliveries.delivered_at`
3. `f"DELETE FROM {table} WHERE {ts_col} < ?"` with `noqa: S608` — table+column names are from internal constants, not user input. Safe.
4. `except Exception: logger.debug(...)` — silent failure; missing-table or missing-column → returns 0 deleted.

### MAJOR CROSS-CORRECTION TO REPORT 0087 (audit_events schema)

Per actual `auth/audit_log.py:42-50`:

```sql
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT NOT NULL DEFAULT '',
    detail_json TEXT NOT NULL DEFAULT '{}',
    request_id TEXT
)
```

**7 fields actual** (Report 0087 said 6).

| Field | Report 0087 claim | Actual | Status |
|---|---|---|---|
| `id` | INTEGER PK AUTOINC | INTEGER PK AUTOINC | ✓ |
| `at` | `event_at` | `at` | **WRONG name in 0087** |
| `actor` | TEXT NULL | TEXT NOT NULL | **WRONG nullability in 0087** |
| `action` | `event_type` | `action` | **WRONG name in 0087** |
| `target` | TEXT NULL | TEXT NOT NULL DEFAULT '' | **WRONG nullability + default missed** |
| `detail_json` | TEXT NULL | TEXT NOT NULL DEFAULT '{}' | **WRONG nullability + default missed** |
| `request_id` | (missing from 0087) | TEXT (added via lazy ALTER) | **MISSING from 0087** |

Plus `auth/audit_log.py:69-70` creates **`CREATE INDEX idx_audit_events_at`** — Report 0087 MR484 incorrectly claimed no index.

**Report 0087 retracted in major part:**
- MR484 (no index on audit_events) — **RETRACTED** (idx_audit_events_at exists)
- MR485 (detail_json schema undefined) — partially valid (still free-form JSON) but column NOT NULL DEFAULT '{}' (Report 0087 missed the default).
- MR483 (event_type free-form TEXT, no enum) — RENAME to `action` (still free-form, finding intact).

### NEW finding: lazy ALTER pattern (cross-link Report 0017)

`audit_log.py:62-65` adds `request_id` column on demand:

```python
if "request_id" not in cols:
    con.execute(
        "ALTER TABLE audit_events ADD COLUMN request_id TEXT"
    )
```

**Cross-correction Report 0017 MR (no ALTER migration framework)**: Reports 0017, 0027, 0117 all said the codebase has no ALTER TABLE pattern. **Wrong** — `audit_log.py:62-65` shows a "PRAGMA table_info → check column → ALTER if missing" pattern. This IS a migration step, just inline rather than centralized.

**Schema-evolution discipline IS present** but per-module rather than a framework. **MR701 below.**

### `export_user_data()` flow (lines 57-79)

GDPR export — query 3 tables for rows referencing `user_id`:
- `audit_events.actor = user_id`
- `sessions.username = user_id`
- `deal_overrides.set_by = user_id` ← **`deal_overrides` referenced again** (per Report 0118 MR677 — table never schema-walked but confirmed used).

**Outputs**: `<out_dir>/user_data_<user_id>.json` (UTF-8 with `default=str` for datetime serialization).

**Tables NOT in export**:
- `analysis_runs` (per-deal, not per-user) — fine
- `mc_simulation_runs` — fine
- `deals` (no user FK) — fine
- `users` (the user themselves) — **MISSING**: a GDPR export should include the user's own row from the `users` table. **MR702 below.**

### Importers (2 production)

| File | Use |
|---|---|
| `server.py` | likely `/api/admin/retention` or `/api/admin/export-user/<id>` admin route |
| `tests/test_phase_k.py` | tests |

**2 importers — tight surface.**

### Mtime + git history

Per `ls -la` (not run this iteration but available): file Apr 25 12:01 — same timestamp as the rest of the repo's last bulk update.

### Sessions table reference

`enforce_retention` retains `sessions` for 30 days based on `created_at`. **Cross-link Report 0090**: per `auth/auth.py`, sessions also have `expires_at` (7-day TTL) and `last_seen_at` (touched on each request).

**Inconsistency**: an idle-but-not-expired session (e.g., last touched 25 days ago, never logged out) sits in the table 30 days from creation. The 30-day retention here is the **bulk cleanup**, separate from the per-session idle/absolute expiry.

### Cross-link to Report 0072 audit-data-flow

Per Report 0072: audit_events grows unbounded. **CLOSED** by `enforce_retention` setting 1,095-day retention. Bulk DELETE happens when this function is called.

But: **`enforce_retention` is operator-invoked**, no auto-cron. Cross-link Reports 0103 MR572 (mark_stale operator-invoked), 0107 MR602 (mark_stale_sources operator-invoked). **Pattern: all retention/cleanup is manual.** **MR703 below.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR700** (carried) | **Phase 0.A → 0.B roadmap unclear** for `rcm_mc_diligence/` | (Report 0122 carried.) | Low |
| **MR701** | **Per-module ALTER pattern (`audit_log.py:62-65`) is the de-facto migration framework** — undocumented in CLAUDE.md | Cross-correction to Report 0017 MR. Each module owns its own schema evolution. New developer adding columns must replicate the pattern. | Medium |
| **MR702** | **`export_user_data` does NOT include the `users` table itself** | A GDPR data subject access request should return the user's own row (display_name, role, etc.). Currently omitted. | **Medium** |
| **MR703** | **`enforce_retention` is operator-invoked — no auto-cron** | Cross-link MR572, MR602. Project-wide pattern: retention requires human action. Tables grow until someone runs the function. | **High** |
| **MR704** | **`sessions` retention 30 days based on `created_at`** but Report 0090 noted `last_seen_at` is the touch column | Active long-running sessions that were created 31+ days ago could be deleted while still valid. Should retention use `last_seen_at` instead, OR rely solely on the per-request expiry check (which already does the right thing)? | Medium |
| **MR705** | **5 tables in retention policy; ~12+ tables in DB are NOT covered** (e.g., `deals`, `runs`, `hospital_benchmarks`, `webhooks`, `users`) | Some are correctly retained indefinitely (deals, users) but `hospital_benchmarks` could grow large over decades of HCRIS refreshes. Each table's policy should be explicit. | Medium |
| **MR706** | **Cross-correction: Report 0087 audit_events schema was substantially wrong** | Actual: 7 fields (not 6), `at` (not `event_at`), `action` (not `event_type`), all NOT NULL, `request_id` exists, `idx_audit_events_at` index exists. **MR484 RETRACTED.** | (correction) |
| **MR707** | **`f"DELETE FROM {table} WHERE {ts_col} < ?"` uses f-string interpolation** (line 46, 71) | Marked `noqa: S608`. Source of `table`/`ts_col` is internal-constant dict — safe. But: a future developer who refactors to "configurable retention from env var" reintroduces the SQL injection vector. Comment-as-warning would help. | Low |

## Dependencies

- **Incoming:** server.py, tests/test_phase_k.py.
- **Outgoing:** stdlib only (`json`, `logging`, `datetime`, `pathlib`, `typing`); SQLite via `store.connect()`.

## Open questions / Unknowns

- **Q1.** Where is `enforce_retention` called from in `server.py`? Likely `/api/admin/retention` route or similar.
- **Q2.** Is `enforce_retention` called by ANY scheduled job (cron, systemd timer, GitHub Actions)?
- **Q3.** What's the schema of `sessions` table fully? Report 0090 named some columns but never schema-walked.
- **Q4.** What's the schema of `deal_overrides` (Report 0118 MR677 backlog)?
- **Q5.** Should there be tests asserting Report 0123 cross-corrections to Report 0087 are now in test fixtures?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0124** | Schema-walk `deal_overrides` (Report 0118 MR677, still owed). |
| **0125** | Schema-walk `sessions` (closes Q3 — never fully walked despite 7+ reports touching it). |
| **0126** | Search server.py for `enforce_retention` call-site (closes Q1). |
| **0127** | Read `cli.py` head (1,252 lines, 14+ iterations owed). |

---

Report/Report-0123.md written.
Next iteration should: schema-walk `deal_overrides` table — finally close Report 0118 MR677 high (carried 5+ iterations now).
