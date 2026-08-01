# Report 0263: Deals FK Correctness Pass — MR1068 + MR1058 + MR1059 (commit 0ab26f6)

## Scope

One coherent pass over deal-child FK behavior, closing the three items the Report-0262 verification tied together: the delete_deal wrong-table-name bug (MR1068, HIGH), the three missing CASCADE clauses (MR1058), and the live-DB rebuild migration the April fix left pending (MR1059).

Sister reports: 0256 (FK survey origin), 0262 (verification sweep that surfaced MR1068), 0181 (delete-policy matrix).

## What was actually wrong (worse than triaged)

Re-deriving the delete list against the live `CREATE TABLE` registry found **9 of the 27 listed names were wrong** — not 3:

| Listed in delete_deal | Reality |
|---|---|
| `deal_owners` | real table is `deal_owner_history` |
| `deal_stages` | real table is `deal_stage_history` (not caught by the 0262 verifier) |
| `health_scores` | real table is `deal_health_history` |
| `watchlist` | real table is `deal_stars` |
| `hold_period_tracking` | phantom — hold_tracking.py creates `quarterly_actuals` (already listed) |
| `initiative_tracking` | phantom — module creates `initiative_actuals` (already listed) |
| `provenance_registry` | phantom — no such table anywhere (real: `metric_provenance`, not a deal child) |
| `refresh_schedule` | phantom — no such table anywhere |
| `portfolio_snapshots` | phantom — module creates `deal_snapshots` (already listed) |

Every failed DELETE was swallowed by `except Exception: pass`, so none of this ever surfaced. Additionally `note_tags` (keyed on `note_id`, not `deal_id`) was never cleared, making any deal with a tagged note undeletable on DBs whose note_tags FK predates CASCADE — the IntegrityError from the `deal_notes` delete was also swallowed, then the final `DELETE FROM deals` failed the whole transaction.

## Fixes (commit 0ab26f6)

**MR1068 — delete_deal (portfolio/store.py):**
- Corrected the four wrong names; dropped the five phantoms; added `covenant_metrics` (ordered before `deal_snapshots` so its SET-NULL snapshot FK doesn't null rows about to die).
- `note_tags` cleared via `note_id IN (SELECT note_id FROM deal_notes WHERE deal_id = ?)` before `deal_notes`.
- Exception tolerance narrowed to `sqlite3.OperationalError` containing "no such table" (lazily-created tables may be absent); anything else — IntegrityError above all — now propagates and rolls back loudly.
- Final list: 23 deal-keyed tables + note_tags = 24 children. CLAUDE.md count corrected (23 → 24).

**MR1058 — CASCADE DDL:** `deal_tags`, `note_tags`, `deal_snapshots` now carry `ON DELETE CASCADE` in fresh-DB DDL. `deal_notes` deliberately stays NO ACTION (soft-delete UX per the delete-policy matrix).

**MR1059 — live-DB rebuild migration:** `deal_children_fk_cascade_rebuild` registered in infra/migrations.py (registry now accepts callable actions alongside SQL strings). For each of the 8 tables (5 from the April fresh-DB fix + the 3 above) it:
1. skips if the table is missing (lazily created correctly later) or `PRAGMA foreign_key_list` already shows CASCADE;
2. purges orphans (`deal_id NOT IN (SELECT deal_id FROM deals)`; note_id variant for note_tags);
3. rebuilds via the documented SQLite 12-step pattern — create corrected table under `_mr1059_new_*`, copy the column intersection, drop old, rename, recreate indexes — under `PRAGMA foreign_keys = OFF` so sibling FK clauses are untouched;
4. per-table transaction with rollback + warning on failure (other tables still converge).

Runs at server startup and dev/seed via the existing `run_pending` wiring; ordered after the ADD COLUMN migrations so the copy sees the full column set.

## Evidence

- `tests/test_deal_children_fk_migration.py` (9 new tests): legacy-DB convergence to CASCADE on all 8 tables; orphan purge with real-row preservation (values checked); all 9 indexes recreated; `PRAGMA foreign_key_check` clean; re-run no-op; **DDL-drift guard** (normalized sqlite_master schema of migrated-legacy DB == module-created fresh DB for all 8 tables); delete_deal end-to-end incl. the tagged-note regression; minimal-DB tolerance test.
- Raw `DELETE FROM deals` post-migration: blocked while a note exists (NO ACTION by design), cascades everything after the note is cleared — note_tags cascading through deal_notes proves the MR1058 clause.
- Affected suites green: deletion/notes/note_tags/deal_tags/watchlist/owners/deadlines/sim_inputs/portfolio_snapshots/migration_idempotency/dev_seed/deal = **192 passed**.
- Two migration-convention tests updated for the callable shape (documented in the registry docstring + the test comment).

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| (closure) | MR1068, MR1058, MR1059, and MR1057's pending half all closed by this pass | — |
| **Q1** | delete_deal explicitly deletes `generated_exports` rows although the FK is SET NULL and the delete-policy matrix says exports should outlive the deal for audit. Pre-existing behavior, untouched here — needs a product decision, not a bug fix. | LOW |

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| next | seed/exports cluster (MR1061/1062/1063/1065/1066) |
| later | Q1 above — decide keep-artifacts vs delete on deal removal |

---

Report/Report-0263.md written.
