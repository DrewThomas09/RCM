# Report 0204: Cross-Cutting — Soft-Delete Pattern

## Scope

Documents soft-delete pattern usage across the project. **Discovered in Report 0197 (`deal_notes.deleted_at`)** as the FIRST instance. Sister to Reports 0024, 0054, 0084, 0114, 0144, 0174 (cross-cuts).

## Findings

### Confirmed soft-delete sites

| Table | Field | Source |
|---|---|---|
| `deal_notes` | `deleted_at TEXT` (nullable, lazy-ALTERed) | Report 0197 |

**Only 1 confirmed instance across 21 walked tables.**

### Likely additional sites (heuristic)

Tables that COULD have soft-delete but DON'T (per Reports 0017, 0047, 0077, 0087, 0102, 0104, 0107, 0117, 0123, 0133, 0134, 0137, 0147, 0148, 0167, 0183, 0197):

| Table | Has soft-delete? |
|---|---|
| `deals` | NO (hard-delete via cascade) |
| `runs` | NO |
| `analysis_runs` | NO |
| `audit_events` | NO (immutable audit trail) |
| `hospital_benchmarks` | NO |
| `webhooks`, `webhook_deliveries` | NO |
| `data_source_status` | NO (single-row-per-source) |
| `mc_simulation_runs` | NO |
| `generated_exports` | NO |
| `deal_overrides` | NO |
| `deal_sim_inputs` | NO |
| `users`, `sessions` | NO |
| `initiative_actuals` | NO |
| `engagements` (engagement_id-based; `closed_at` field) | **closed_at is similar pattern!** |
| `engagement_members` | NO |
| `engagement_comments` | NO |
| `engagement_deliverables` | NO (`status: DRAFT|PUBLISHED` is similar) |
| **`deal_notes`** | **YES — `deleted_at`** |

**Inconsistency**: 1 explicit `deleted_at` + 2 conceptually-similar (`engagements.closed_at`, `engagement_deliverables.status`).

### Why deal_notes specifically

Per Report 0197 line 63: "Back-compat migration for DBs created before soft-delete" — soft-delete was added LATER. Pre-migration deal_notes had no soft-delete; lazy ALTER added the column.

**Inference**: deal_notes had a use-case where partners said "I deleted that note by accident — can you recover it?" → soft-delete added. **Pattern is reactive, not architectural.**

### Cross-link to Report 0123 retention

Per Report 0123 `enforce_retention`: hard-DELETE based on age. **Conflicts with soft-delete?** If `deal_notes` rows are soft-deleted (deleted_at set) but never actually removed, retention should EVENTUALLY hard-delete them. Report 0123 policy: deal_notes is NOT in DEFAULT_RETENTION_DAYS. **Soft-deleted notes persist indefinitely.**

**MR981 below.**

### Cross-link Report 0134 deal_overrides

Per Report 0134: `clear_override(store, deal_id, key)` performs HARD DELETE. **Override delete is hard.** Different policy from notes.

**Project lacks unified delete-policy**. Per Report 0167 + 0183 + 0189 cascade-policy gap (MR761/MR817/MR889/MR938) — same theme: project lacks documented policy on lifecycle.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR981** | **`deal_notes` soft-delete + NOT in retention policy → notes persist forever after delete** | Cross-link Report 0123 MR705 / MR778 retention-coverage gaps. **Soft-deleted notes accumulate unbounded.** | Medium |
| **MR982** | **Project lacks unified delete-policy** — soft-delete (deal_notes), hard-delete (deal_overrides), cascade (mc_simulation_runs), set-null (generated_exports), no-action (sessions, initiative_actuals, engagement-children) | Cross-link MR761/MR817/MR889/MR938. **Document a delete-policy matrix** in CLAUDE.md. | High |
| **MR983** | **`engagements.closed_at` and `engagement_deliverables.status` are conceptual soft-deletes** | Not "deleted_at" but functionally similar. Inconsistent vocabulary across project. | Medium |

## Dependencies

- **Incoming:** Report 0197 (deal_notes).
- **Outgoing:** future iterations should track soft-delete patterns as they're discovered.

## Open questions / Unknowns

- **Q1.** Does any code actually call something like `deal_notes WHERE deleted_at IS NULL` in reads (filtering soft-deleted)?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0205** | Integration point (in flight). |

---

Report/Report-0204.md written.
