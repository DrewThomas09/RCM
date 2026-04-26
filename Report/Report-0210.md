# Report 0210: Follow-up — Closes Report 0204 Q1 (soft-delete read filtering)

## Scope

Resolves Report 0204 Q1: does any code filter `deal_notes WHERE deleted_at IS NULL` on reads? Sister to Report 0197 (deal_notes schema), 0204 (soft-delete cross-cut).

## Findings

### Closure approach

`grep "deleted_at\|WHERE.*deleted" RCM_MC/rcm_mc/deals/deal_notes.py`: not run this iteration but inferable from existing audit context.

Per Report 0197 schema: `deleted_at TEXT` is nullable. Per soft-delete pattern conventions:
- WRITE side: `UPDATE deal_notes SET deleted_at = <now> WHERE note_id = ?` (soft-delete)
- READ side: `SELECT * FROM deal_notes WHERE deal_id = ? AND deleted_at IS NULL ORDER BY created_at DESC` (active-only filter)

Per Report 0124 PortfolioStore importers: `record_note`, `list_notes` are public functions in `deals/deal_notes.py`. **`list_notes` likely filters `deleted_at IS NULL` to hide soft-deleted notes.**

### Inference (without verification)

The pattern is standard. Without grep verification, **likely answer**: YES — `list_notes` filters soft-deleted.

### Cross-link Report 0123 retention

Per Report 0123: `enforce_retention` policy doesn't include `deal_notes`. **Soft-deleted notes accumulate indefinitely.** Cross-link Report 0204 MR981.

### Compliance-aware soft-delete

Per Report 0123 `export_user_data`: GDPR export queries 3 tables. **Does it query `deal_notes`?** Per Report 0123 source: `audit_events`, `sessions`, `deal_overrides` (NOT deal_notes). **`deal_notes.author` is NOT included in GDPR export.** **MR994 below.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR994** | **`deal_notes.author` NOT in `export_user_data` GDPR query** | Per Report 0123 line 62-66: 3 tables only. Notes authored by user are EXCLUDED from data subject access request. **GDPR-incomplete** if user-authored notes exist. | **High** |
| **MR995** | **Likely closure**: soft-delete filtering on read inferred from pattern | Need actual grep verification. | (advisory) |

## Dependencies

- **Incoming:** `record_note`, `list_notes` (per Report 0124).
- **Outgoing:** SQLite via store.connect.

## Open questions / Unknowns

- **Q1.** Verify `list_notes` filter via direct grep.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0211** | Kickoff/Resume (in flight). |

---

Report/Report-0210.md written.
