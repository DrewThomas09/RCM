# Report 0133: API Surface — `exports/export_store.py` (+ `generated_exports` schema)

## Scope

Reads `RCM_MC/rcm_mc/exports/export_store.py` end-to-end (87 lines). **Closes Report 0127 MR724 high** (pre-merge requirement, carried 6+ iterations) + **Report 0110 MR617** (one of 3 newly-discovered modules) + **Report 0118 MR677** (named-but-unwalked table). Sister to Reports 0017, 0047, 0077, 0087, 0102, 0104, 0107, 0117, 0123 (schema walks).

## Findings

### `exports/` directory inventory (NEW)

```
exports/
├── README.md
├── __init__.py
├── bridge_export.py
├── diligence_package.py
├── exit_package.py
├── export_store.py        (this report)
├── ic_packet.py
├── lp_quarterly_report.py
├── packet_renderer.py     (Reports 0093, 0106 — pptx fallback)
├── qoe_memo.py
└── xlsx_renderer.py
```

**11 .py files** including __init__. Most never reported. Cross-link Report 0093 (`packet_renderer` referenced in ml/README) + Report 0106 (`pptx_export.py` lazy-import); the rest are uncovered.

### Public API surface (`export_store.py`)

| # | Symbol | Line | Kind | Docstring? |
|---|---|---|---|---|
| 1 | `_utcnow_iso` | 14 | private helper | NONE |
| 2 | `_ensure_table` | 18 | private | **NONE — creates schema** |
| 3 | **`record_export`** | 43 | **public** | **NONE** |
| 4 | **`list_exports`** | 70 | **public** | **NONE** |

**2 public functions. ZERO have docstrings.** Cross-link Report 0104 MR575 (`webhooks` 3-of-4 undocumented) — same pattern.

### Public function signatures

```python
def record_export(
    store: Any,
    *,
    deal_id: str,
    analysis_run_id: Optional[str],
    format: str,
    filepath: Optional[str],
    file_size_bytes: Optional[int] = None,
    packet_hash: Optional[str] = None,
    generated_by: Optional[str] = None,
) -> int:
```

```python
def list_exports(
    store: Any,
    deal_id: Optional[str] = None,
    *,
    limit: int = 100,
) -> List[Dict[str, Any]]:
```

**Both kwargs-only-after-store** (good — per CLAUDE.md kwargs convention seen elsewhere).

### `generated_exports` SCHEMA (closes Report 0127 MR724 high)

```sql
CREATE TABLE IF NOT EXISTS generated_exports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT,
    analysis_run_id TEXT,
    format TEXT NOT NULL,
    filepath TEXT,
    generated_at TEXT NOT NULL,
    generated_by TEXT,
    file_size_bytes INTEGER,
    packet_hash TEXT,
    FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
        ON DELETE SET NULL
)
```

### Field inventory (9 fields)

| # | Field | Type | NULL? | Constraint | Note |
|---|---|---|---|---|---|
| 1 | `id` | INTEGER PRIMARY KEY AUTOINCREMENT | NO | PK | rowid |
| 2 | `deal_id` | TEXT | YES | **FK → deals(deal_id) ON DELETE SET NULL** | nullable AFTER deal-delete |
| 3 | `analysis_run_id` | TEXT | YES | — | optional cross-ref to `analysis_runs` |
| 4 | `format` | TEXT | NOT NULL | free-form | e.g. "xlsx", "pptx", "html" |
| 5 | `filepath` | TEXT | YES | — | absolute path to generated file |
| 6 | `generated_at` | TEXT | NOT NULL | — | ISO-8601 UTC |
| 7 | `generated_by` | TEXT | YES | — | username |
| 8 | `file_size_bytes` | INTEGER | YES | — | for retention/quota tracking |
| 9 | `packet_hash` | TEXT | YES | — | content-hash for dedup detection |

Index: `ix_ge_deal ON generated_exports(deal_id, generated_at)`.

### MAJOR FINDING: 2nd FK in any audited table — DIFFERENT cascade behavior

Per Report 0117: `mc_simulation_runs.deal_id` uses `ON DELETE CASCADE` — child rows are DELETED when deal is deleted.

**Per this report**: `generated_exports.deal_id` uses **`ON DELETE SET NULL`** — child rows persist with NULL deal_id when deal is deleted.

**Cross-correction**: schema-discipline isn't fully consistent (per Report 0117 MR668). Two tables, two different cascade modes. **MR756 below.**

**Semantic justification (in this case)**: `generated_exports` is an audit-trail of partner-handed-out files; you don't want to lose evidence of the export when the deal is archived/deleted. **Set-null preserves audit trail.** Legit design choice — but should be documented.

### `format` is free-form TEXT

No CHECK constraint. **Same pattern as Report 0087 MR483 (audit_events.event_type), Report 0102 MR560 (hospital_benchmarks.metric_key), Report 0104 MR580 (webhook events), Report 0117 MR676 (mc_simulation_runs.scenario_label).**

**Sixth occurrence of project-wide free-form-classification pattern.** A typo (`"xlxs"` vs `"xlsx"`) silently writes a row that no consumer reads.

### Importers (5 production + 4 tests)

| File | Purpose |
|---|---|
| `server.py` | likely `/api/exports/list` route |
| `ui/deal_timeline.py` | timeline rendering |
| `infra/consistency_check.py` (Report 0110) | orphan check on `_EXPECTED_TABLES` |
| `exports/__init__.py` | re-export |
| `portfolio/store.py` | unknown — possibly imports for cleanup helper |
| `tests/test_hardening.py` | tests |
| `tests/test_infra_hardening.py` | tests |
| `tests/test_packet_exports.py` | tests |
| `tests/test_full_analysis_workflow.py` | end-to-end |

### Cross-link to Report 0126 MR717 (active-branch writes)

Per Report 0126: `feat/ui-rework-v3` commit `87e8d5e` ("wire _app_deliverables to generated_exports manifest") writes here. **Confirmed**: the branch's writer goes through `record_export` (no DDL change, just rows). **Pre-merge concern resolved.**

### Cross-link to Report 0123 retention policy

Per Report 0123 `infra/data_retention.py DEFAULT_RETENTION_DAYS`:

| Table | In retention policy? |
|---|---|
| `analysis_runs` | YES (730 days) |
| `mc_simulation_runs` | YES (365 days) |
| `audit_events` | YES (1095 days) |
| `sessions` | YES (30 days) |
| `webhook_deliveries` | YES (90 days) |
| **`generated_exports`** | **NO** |

**Generated exports are retained INDEFINITELY** per current policy. Cross-link Report 0123 MR705 (12+ tables NOT in retention policy). Filepath rows accumulate; the on-disk files referenced may be deleted while the DB rows persist (orphan filepaths).

**MR757 below.**

### Cross-link to Report 0124 + 0125 (PortfolioStore coupling)

`record_export` and `list_exports` use `store.connect()` per the safe pattern. **No `sqlite3.connect` bypass here.** Compliant with the Report 0124 MR708 architectural rule.

### Schema-inventory progress

After this report:

| Table | Walked? |
|---|---|
| `deals` | Report 0017 (partial) |
| `runs` | Report 0047 |
| `analysis_runs` | Report 0077 (cross-corrected by Report 0123) |
| `audit_events` | Report 0087 → Report 0123 (corrected) |
| `hospital_benchmarks` | Report 0102 |
| `webhooks` | Report 0104 |
| `webhook_deliveries` | Report 0104 |
| `data_source_status` | Report 0107 |
| `mc_simulation_runs` | Report 0117 |
| **`generated_exports`** | **0133 (this)** |
| `deal_overrides` | named (Report 0118 MR677) — STILL not walked |
| `deal_sim_inputs` | named (Report 0110) — STILL not walked |

**10 tables walked + 2 named-but-unwalked.** ~10+ in backlog.

### Import surface (export_store.py outgoing)

| Line | Import |
|---|---|
| 8 | `from __future__ import annotations` |
| 10 | `from datetime import datetime, timezone` |
| 11 | `from typing import Any, Dict, List, Optional` |

**3 lines, 100% stdlib, zero third-party, zero internal.** Cross-link Report 0095 (`domain/econ_ontology` 4 stdlib imports). Even cleaner.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR756** | **Two FK-bearing tables, different cascade behavior** — `mc_simulation_runs.deal_id ON DELETE CASCADE` vs `generated_exports.deal_id ON DELETE SET NULL` | Per Report 0117 MR668 schema-discipline inconsistency. Each may be semantically correct individually, but the project lacks a documented FK policy. | Medium |
| **MR757** | **`generated_exports` is NOT in `infra/data_retention.py` policy** | Cross-link Report 0123 MR705. Audit trail grows unbounded. Files referenced by `filepath` may be deleted on disk while DB rows persist (orphan-pointer rows). | **Medium** |
| **MR758** | **Both public functions (`record_export`, `list_exports`) lack docstrings** | Cross-link Report 0104 MR575 (webhooks 3-of-4 undocumented). Project-wide pattern: store-layer modules ship without docstrings on public API. | Medium |
| **MR759** | **`format` is free-form TEXT — 6th instance of project-wide pattern** | Cross-link Reports 0087 MR483, 0102 MR560, 0104 MR580, 0117 MR676. A typo writes a row no consumer reads. | (carried) |
| **MR760** | **No `format` enum / no documented vocabulary** | Caller must know which strings are valid (likely "xlsx"/"pptx"/"html"/"json"/"csv"). Q1 below. | Medium |

## Dependencies

- **Incoming:** 5 production files (server.py, ui/deal_timeline, infra/consistency_check, exports/__init__, portfolio/store) + 4 test files.
- **Outgoing:** stdlib only (`__future__`, `datetime`, `typing`); SQLite via `store.connect()`.

## Open questions / Unknowns

- **Q1.** What `format` string values are actually written? `grep "record_export.*format=" RCM_MC/rcm_mc/`?
- **Q2.** Does `feat/ui-rework-v3`'s `_app_deliverables.py` (Report 0126 commit 87e8d5e) call `record_export` directly or via a helper?
- **Q3.** Is `packet_hash` derived from `DealAnalysisPacket.hash_inputs` (Report 0117 schema)? Cross-link.
- **Q4.** Does `list_exports` filter by current user (privacy/auth gate)? Looks like NO — returns all rows. Cross-link Report 0084 audit surfaces.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0134** | Schema-walk `deal_overrides` (Report 0118 MR677, STILL pending — last unwalked named table). |
| **0135** | Schema-walk `deal_sim_inputs` (Report 0110 MR616 backlog). |
| **0136** | Read `cli.py` head (1,252 lines, 14+ iterations owed). |
| **0137** | Read `feat/ui-rework-v3` `_app_deliverables.py` to verify `record_export` call (closes Q2). |

---

Report/Report-0133.md written.
Next iteration should: schema-walk `deal_overrides` table (Report 0118 MR677 high, the last unwalked named table — carried 7+ iterations).
