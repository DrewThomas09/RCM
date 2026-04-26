# Report 0197: Database Layer — `deal_notes` SQLite Table

## Scope

Schema-walks `deal_notes` — one of 7+ deal-child tables predicted in Report 0180 MR929. Owner: `deals/deal_notes.py:53`. Sister to all prior schema reports.

## Findings

### Schema (deals/deal_notes.py:53-62)

```sql
CREATE TABLE IF NOT EXISTS deal_notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    author TEXT,
    body TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
)
```

### Field inventory (6 fields)

| # | Field | Type | NULL? | Note |
|---|---|---|---|---|
| 1 | `note_id` | INTEGER PK AUTOINCREMENT | NO | rowid |
| 2 | `deal_id` | TEXT | NOT NULL | **FK → deals(deal_id) (no cascade — NO ACTION default)** |
| 3 | `created_at` | TEXT | NOT NULL | ISO-8601 |
| 4 | `author` | TEXT | (nullable) | username |
| 5 | `body` | TEXT | NOT NULL | note content |
| 6 | `deleted_at` | TEXT | (nullable) | **soft-delete tombstone** |

Index: `idx_deal_notes_deal ON (deal_id, created_at DESC)`.

### Soft-delete pattern (NEW)

`deleted_at TEXT` column = soft-delete timestamp. **First soft-delete pattern observed across 21 walked tables.** Cross-link Report 0123 retention policy: hard-DELETE done via cron-style `enforce_retention`, but THIS table uses soft-delete first.

**MR969 below**: rest of schema-walked tables use hard-DELETE only. **Soft-delete is a deal_notes-specific feature.**

### Lazy ALTER for `deleted_at`

Lines 64-66:
```python
cols = {r[1] for r in con.execute("PRAGMA table_info(deal_notes)").fetchall()}
if "deleted_at" not in cols:
    con.execute("ALTER TABLE deal_notes ADD COLUMN deleted_at TEXT")
```

**3rd confirmed instance** of the per-module lazy-ALTER pattern (cross-link Reports 0123 audit_events MR701, 0147 sessions). Project-wide migration pattern.

### Cascade behavior — NO ACTION (carried)

7th confirmed FK with NO ACTION default. Cross-link Report 0167 + 0183 + 0189 — pattern is **dominant** for child tables.

### Schema inventory progress

After this report: **21 tables walked.** Per Report 0181: ~22+ in DB. ~1-2 unidentified remain.

| # | Table | Walked? |
|---|---|---|
| 1-20 | (per Report 0183) | ✓ |
| 21 | **`deal_notes`** | **0197 (this)** |

### NO third-party "Deal child" tables remaining likely

Per Report 0180 MR929 prediction: 7+ deal-child tables. Report 0124 imports list:
- `deal_notes` ✓ (this report)
- `deal_tags` (TBD)
- `deal_owners` (TBD)
- `deal_deadlines` (TBD)
- `deal_sim_inputs` ✓ (Report 0137)
- `note_tags` (TBD)
- `health_score` ✓ (per Report 0124 — hist `history_series`)
- `watchlist` (TBD)

**5+ deal-child tables still unwalked.** Backlog continues.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR969** | **`deal_notes.deleted_at` is the FIRST soft-delete column observed** | Cross-link Report 0123 retention. Most tables use hard-delete; deal_notes preserves history. **Should be documented as per-table policy.** | Medium |
| **MR970** | **3rd instance of lazy-ALTER pattern** | Cross-link Reports 0123 (audit_events MR701) + 0147 (sessions). Project has implicit migration discipline. | (carried) |
| **MR971** | **5+ deal-child tables still unwalked** | Per Report 0180 MR929. Add to backlog. | High |

## Dependencies

- **Incoming:** `record_note`, `list_notes` (Report 0124).
- **Outgoing:** SQLite via store.connect.

## Open questions / Unknowns

- **Q1.** What about `deal_tags`, `deal_owners`, `deal_deadlines` schema?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0198** | Entry point (in flight). |
| **0199** | Schema-walk deal_tags or deal_owners. |

---

Report/Report-0197.md written.
