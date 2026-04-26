# Report 0077: SQLite Storage Layer — `analysis_runs` Table

## Scope

Documents `analysis_runs` (the canonical packet cache table) at `analysis/analysis_store.py:36-49`. Sister to Reports 0017 (deals) + 0047 (runs).

## Findings

### Schema

```sql
CREATE TABLE IF NOT EXISTS analysis_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT NOT NULL,
    scenario_id TEXT,
    as_of TEXT,
    model_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    packet_json BLOB NOT NULL,
    hash_inputs TEXT NOT NULL,
    run_id TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
        ON DELETE CASCADE
);
```

**10 columns + FK with ON DELETE CASCADE** — first table audited that uses CASCADE (cross-link Report 0017 MR123: dual-tracked deletion).

### Indexes

```sql
CREATE INDEX IF NOT EXISTS idx_analysis_runs_hash
    ON analysis_runs(deal_id, hash_inputs);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_deal
    ON analysis_runs(deal_id, created_at);
```

**2 indexes** — first audited table with explicit indexes (cross-link Report 0017 MR126 — `deals` had no indexes). Hash-index for cache lookup; deal+date for chronological listing.

### Compression

Lines 63-68: `_compress`/`_decompress` use `zlib.compress(level=6)`. **Packets are stored compressed** — `packet_json BLOB`, not TEXT. Reduces row size at the cost of CPU.

### Write site (1 — `save_packet` at line 71)

```sql
INSERT INTO analysis_runs (deal_id, scenario_id, as_of, model_version,
                           created_at, packet_json, hash_inputs, run_id, notes)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
```

Single-writer through `analysis_store.save_packet(store, packet, inputs_hash, notes)`.

### Read sites (8+ across multiple files)

| Site | Use |
|---|---|
| `analysis_store.py:120` | Cache lookup by hash |
| `analysis_store.py:163, 171` | `find_cached_packet`, `load_latest_packet` |
| `analysis_store.py:196` | `list_packets(deal_id)` |
| `analysis_store.py:204` | `list_packets()` (all) |
| `analysis_store.py:214` | `load_packet_by_id` |
| `analysis/playbook.py:173` | playbook reads cached packets |
| `analysis/refresh_scheduler.py:97` | refresh-scheduler queries |
| `pe/fund_attribution.py:80` | per-deal packet load |
| `ui/dashboard_page.py:341` | recent-runs dashboard query |
| `infra/consistency_check.py:82` | data-integrity check |

**At least 10 read sites across 6 modules.** Heavy read load.

### `_ensure_table` redundant?

`refresh_scheduler.py:45` ALSO has `CREATE TABLE IF NOT EXISTS analysis_runs (...)`. **Two CREATE statements for the same table** in different modules. SQLite's IF NOT EXISTS makes this safe but **schema-drift risk**: if one diverges, only the file imported FIRST wins (idempotent skip).

### `model_version` column

A schema-versioning column independent of `PACKET_SCHEMA_VERSION` (Report 0058) — used for ML model versioning. Adds a second versioning dimension.

### `hash_inputs` column

Indexed. Cache key: `(deal_id, hash_inputs)` lookup serves cached packet (Report 0008's `find_cached_packet`).

### FK CASCADE

Notable contrast with `deals`-table FK on `runs` (Report 0047) which lacks CASCADE. **`analysis_runs` has CASCADE** — when a deal is deleted, all its analysis_runs go with it. This means `delete_deal` (Report 0008/0017) doesn't strictly need to manually `DELETE FROM analysis_runs` — the FK CASCADE handles it. **But `delete_deal:174-183` cascade list (per Report 0008) DOES include `analysis_runs`** — redundant but safe.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR454** | **Two `CREATE TABLE` statements for analysis_runs** (`analysis_store.py:36` + `refresh_scheduler.py:45`) | Schema-drift risk if either is modified independently. **Pre-merge: any branch that adds a column must update both.** | **High** |
| **MR455** | **CASCADE on FK + manual cascade in delete_deal** | Redundant but safe. Cleaner: drop manual `analysis_runs` from `delete_deal:174-183` since CASCADE handles it. **But cross-link Report 0017 MR123: schema-wide deletion is dual-tracked already.** | Low |
| **MR456** | **`packet_json BLOB` is zlib-compressed** | Cache size manageable but CPU cost on every read. If compression level changes, old rows still decompress (zlib is forward-compatible). | Low |
| **MR457** | **`model_version` + `PACKET_SCHEMA_VERSION` are independent versioning** | Two dimensions; cache key includes hash but NOT version. **A version change must invalidate cache; honor-system depends on hash also changing.** | **High** |
| **MR458** | **`hash_inputs` index alone may not be selective enough** | Composite `(deal_id, hash_inputs)` index helps. Verified at line 53-54. | (verified safe) |

## Dependencies

- **Incoming:** 6 production files + tests; FK from `deals` table.
- **Outgoing:** `deals` table (FK), zlib (compression), JSON (serialization).

## Open questions / Unknowns

- **Q1.** What does `notes` column store? Free-form analyst comment, or system-generated metadata?
- **Q2.** When does `hash_inputs` change? If config/CSV changes, the hash differs; if a model_version bump occurs, hash may NOT change (depends on what hash_inputs covers).

## Suggested follow-ups

| Iteration | Area |
|---|---|
| **0078** | Entry points (already requested). |

---

Report/Report-0077.md written.

