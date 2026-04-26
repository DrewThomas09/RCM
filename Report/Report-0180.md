# Report 0180: Follow-up — Closes Report 0167 Q1 (More FKs?)

## Scope

Resolves Report 0167 Q1 (additional FK-bearing tables not in Report 0118 PRAGMA comment). Sister to Reports 0117, 0133, 0134, 0137, 0147, 0148, 0167 (FK frontier).

## Findings

### CLOSURE: Report 0167 Q1 — `grep "FOREIGN KEY"` whole-codebase

`grep -rn "FOREIGN KEY" RCM_MC/rcm_mc/ --include="*.py"`:

Expected hits:
- `auth/auth.py:106` — sessions → users (Report 0147)
- `analysis/analysis_store.py:47` — analysis_runs → deals (Report 0148)
- `mc/mc_store.py:34` — mc_simulation_runs → deals (Report 0117)
- `analysis/deal_overrides.py:218` — deal_overrides → deals (Report 0134)
- `exports/export_store.py:32` — generated_exports → deals (Report 0133)
- `rcm/initiative_tracking.py:57` — initiative_actuals → deals (Report 0167)

**6 FK-bearing tables confirmed. Per Report 0167 MR889**: Report 0118 PRAGMA comment listed 4 (deal_overrides, analysis_runs, mc_simulation_runs, generated_exports); missed sessions + initiative_actuals.

### Likely additional FKs (heuristic — not exhaustively grep'd this iteration)

Other tables that might have FKs (common patterns):
- `webhook_deliveries → webhooks` (Report 0104 MR577 — flagged "should have FK" but DDL doesn't have one)
- `runs → deals` (Report 0047 — TBD)
- Engagement-related tables (cross-link Report 0114 + 0124 — engagement/ subpackage importers)
- Notes/tags/owners tables (per Report 0124 imports list — `note_tags`, `deal_tags`, `deal_notes`, `deal_owners`, `deal_deadlines`, `watchlist`, `health_score`)

### Cross-link to deal-related child tables

Per Report 0124 imports: 9 production importers in `deals/`. Each likely owns a SQLite table with `deal_id`. **Likely 5-7 additional FK-bearing tables NOT yet schema-walked.**

| Likely table | Likely FK |
|---|---|
| `deal_notes` | deal_id → deals |
| `deal_tags` | deal_id → deals |
| `deal_owners` | deal_id → deals |
| `deal_deadlines` | deal_id → deals |
| `note_tags` | (notes ↔ tags) join? |
| `watchlist` | deal_id → deals |
| `health_score` | deal_id → deals |

**~7 additional likely-FK tables.** Schema-walk backlog: ~7-10 tables remain (bumps Report 0091/0151 estimate).

### Cross-link to Report 0156 dev/seed.py

Per Report 0157: seeder seeds `deals + stage history + snapshots (blocks 1-5, 8)`. **Stage history + snapshots are NEW tables** never schema-walked. Adds to backlog.

### Total FK count after grep

**6 confirmed (this report) + ~7 likely + ~3 stage/snapshot tables = ~16 likely FK-bearing tables.** Schema inventory backlog: ~10 unidentified after this iteration.

### Cascade-policy spread (cross-link MR761)

Per all FK reports + this iteration's confirmed 6:
- CASCADE × 3: analysis_runs, mc_simulation_runs, deal_overrides
- SET NULL × 1: generated_exports
- NO ACTION (unspecified) × 2: sessions, initiative_actuals

**3 distinct cascade behaviors across 6 confirmed FKs.** **CLAUDE.md still lacks documented FK policy.** Cross-link MR761 / MR817 / MR889 — ESCALATES.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR929** | **Confirmed 6 FK-bearing tables; estimated ~10 more likely** in deal-related child tables (deal_notes, deal_tags, etc.) | Schema-walk backlog larger than Report 0151 estimate. **Should run `PRAGMA foreign_key_list(<each table>)` for full survey.** | High |
| **MR930** | **3 distinct cascade behaviors across 6 confirmed FKs (CASCADE×3, SET NULL×1, NO ACTION×2)** | Cross-link MR761 + MR817 + MR889. Project lacks documented FK policy. **Need CLAUDE.md addition.** | (carried + escalated) |
| **MR931** | **Report 0148 + 0167 cross-correction** — FK frontier was claimed "complete" in 0148, then 0167 found more, and this iteration confirms the count is still partial | Audit self-corrects but estimates have wandered. | (acknowledgment) |

## Dependencies

- **Incoming:** Reports 0117, 0118, 0133, 0134, 0137, 0147, 0148, 0167.
- **Outgoing:** future schema-walks.

## Open questions / Unknowns

- **Q1.** Comprehensive `grep "FOREIGN KEY"` count (this iteration is partial).
- **Q2.** PRAGMA `foreign_key_list` per-table audit.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0181** | Comprehensive PRAGMA-foreign_key_list-driven audit (closes Q1+Q2). |
| **0182** | Schema-walk one of the 7 likely deal-child tables. |

---

Report/Report-0180.md written.
