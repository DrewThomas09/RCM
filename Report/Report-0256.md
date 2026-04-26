# Report 0256: FK Frontier — Deal-Child Tables Walked

## Scope

Closes Reports 0148 / 0167 / 0180 / 0211 carry-forward (MR929 / MR971): the deal-child FK survey. This iteration reads the `CREATE TABLE` body of every table whose primary axis is `deal_id` (or transitive via `deal_notes`) and tabulates the actual FK + `ON DELETE` clause.

Sister reports: 0091 / 0118 / 0148 / 0167 / 0180 / 0207 / 0211 (FK frontier lineage), 0181 (delete-policy matrix — closed in iter-20 commit `488e3c8`).

## Findings

### 13 deal-child tables walked

| Table | DDL site | FK to deals/funds/notes | `ON DELETE` |
|---|---|---|---|
| `deal_fund_assignments` | `infra/multi_fund.py:57` | `fund_id → funds(fund_id)` | **CASCADE** |
| `deal_overrides` | `analysis/deal_overrides.py:209` | `deal_id → deals(deal_id)` | **CASCADE** |
| `deal_stage_history` | `deals/deal_stages.py:48` | `deal_id → deals(deal_id)` | **CASCADE** |
| `comments` | `deals/comments.py:18` | `deal_id → deals(deal_id)` | **CASCADE** |
| `deal_tags` | `deals/deal_tags.py:70` | `deal_id → deals(deal_id)` | (default = **NO ACTION**) |
| `deal_notes` | `deals/deal_notes.py:53` | `deal_id → deals(deal_id)` | (default = **NO ACTION**) — also has `deleted_at` soft-delete |
| `note_tags` | `deals/note_tags.py:40` | `note_id → deal_notes(note_id)` | (default = **NO ACTION**) |
| `deal_snapshots` | `portfolio/portfolio_snapshots.py:94` | `deal_id → deals(deal_id)` | (default = **NO ACTION**) |
| `deal_sim_inputs` | `deals/deal_sim_inputs.py:43` | **none declared** | (orphan-on-delete risk) |
| `deal_owner_history` | `deals/deal_owners.py:57` | **none declared** | (orphan-on-delete risk) |
| `deal_health_history` | `deals/health_score.py:48` | **none declared** | (orphan-on-delete risk) |
| `deal_deadlines` | `deals/deal_deadlines.py:59` | **none declared** | (orphan-on-delete risk) |
| `deal_stars` | `deals/watchlist.py:40` | **none declared** | (orphan-on-delete risk) |

### Distribution

- **CASCADE**: 4 tables — deal_fund_assignments → funds, deal_overrides / deal_stage_history / comments → deals.
- **NO ACTION (default)**: 4 tables with FK declared but no ON DELETE — deal_tags, deal_notes, note_tags, deal_snapshots.
- **No FK declared at all**: 5 tables — deal_sim_inputs, deal_owner_history, deal_health_history, deal_deadlines, deal_stars. These produce orphan rows when their parent deal is deleted; nothing in SQLite blocks the deletion or cleans up.

### Cross-link to delete-policy matrix (iter-20 `488e3c8`)

The matrix CLAUDE.md just received says: *"Reach for NO ACTION only when the operator-visible cleanup step is intentional, and document the cleanup order in the same migration that introduces the FK."* None of the 4 NO-ACTION tables have a documented cleanup order. None of the 5 no-FK tables are even visible to a parent-delete check.

### Severity assessment

Per the matrix and the 5 cascade behaviors documented in iteration 20:

| Risk class | Tables | Recommended action |
|---|---|---|
| **Silent orphans on deal delete** | deal_sim_inputs, deal_owner_history, deal_health_history, deal_deadlines, deal_stars | Add `FOREIGN KEY(deal_id) REFERENCES deals(deal_id) ON DELETE CASCADE` (these are derivative analytics — partner-visible but not audit-canonical). |
| **NO ACTION blocks delete with no doc** | deal_tags, deal_notes, note_tags, deal_snapshots | For deal_notes: keep NO ACTION since soft-delete already handles "go away" UX. For deal_tags + note_tags + deal_snapshots: upgrade to CASCADE. |
| **Cleanly handled** | deal_fund_assignments, deal_overrides, deal_stage_history, comments | Leave alone. |

**MR929/MR971 closure state:** survey complete. The audit chain previously inferred ~10 unwalked tables; this report walks 13 and finds 9 of them in either an orphan-allowing or a cleanup-blocking state.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR1057** | **5 deal-child tables have no FK at all** — silent orphan rows after `DELETE FROM deals` | deal_sim_inputs, deal_owner_history, deal_health_history, deal_deadlines, deal_stars. Adding the FK in a migration is a breaking schema change for live DBs (existing orphan rows may already exist) — needs a one-time cleanup pass before the FK can be added. | High |
| **MR1058** | **4 deal-child tables have FK but default NO ACTION** with no documented cleanup order | deal_tags, deal_notes, note_tags, deal_snapshots. Deleting a deal raises `IntegrityError` until children are cleared. deal_notes is intentional (soft-delete is the partner UX); the other three are accidental. | Medium |
| **MR929/MR971** | (RETRACTED — closed) deal-child FK frontier walked | (closure) | (closed) |

## Dependencies

- **Incoming:** anyone calling `DELETE FROM deals WHERE deal_id = ?` — server.py, CLI cleanup paths, test fixtures.
- **Outgoing:** SQLite + `PortfolioStore.PRAGMA foreign_keys=ON` (Report 0118).

## Open questions / Unknowns

- **Q1.** How many existing live DBs already have orphan rows in the 5 no-FK tables? Migration to add the FK must clean those first.
- **Q2.** Should `deal_notes` keep NO ACTION + soft-delete forever, or migrate to CASCADE (and rely on `archived` semantics elsewhere)?
- **Q3.** `note_tags → deal_notes` is two-hop from deals; if deal_notes ever moves to CASCADE, note_tags inherits the cascade automatically.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| (next-actionable) | Migrate the 5 no-FK tables to add `FOREIGN KEY(deal_id) REFERENCES deals(deal_id) ON DELETE CASCADE` — but only after a one-time orphan-row purge migration. (MR1057.) |
| (low) | Upgrade deal_tags / note_tags / deal_snapshots from NO ACTION to CASCADE. (MR1058 — bulk of the four NO ACTION tables.) |
| (audit) | Re-run this survey across non-deal-child tables (sessions, initiative_actuals, engagement_*) to confirm the 89-table full picture matches the cascade matrix. |

---

Report/Report-0256.md written.
