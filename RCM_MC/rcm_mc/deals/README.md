# Deals

Deal lifecycle management: creation, staging, ownership, tagging, notes, comments, health scoring, and watchlist tracking. Provides the per-deal metadata layer that all analysis, alerts, and UI components consume.

| File | Purpose |
|------|---------|
| `deal.py` | `rcm-mc deal new` CLI orchestrator: sequences intake, ingest, simulation run, and deal state in one command |
| `deal_stages.py` | Deal stage tracking (pipeline > diligence > ic > hold > exit) with validated transitions and automation-engine events |
| `deal_owners.py` | Per-deal ownership assignment with append-only reassignment history and "my deals" views |
| `deal_tags.py` | Freeform deal tagging (thesis, fund, watchlist, geography, lead analyst) with case-insensitive dedup |
| `deal_notes.py` | Append-only per-deal notes with author attribution and UTC timestamps |
| `deal_deadlines.py` | Per-deal deadline/task tracking with open/completed status and cross-portfolio upcoming/overdue queries |
| `deal_sim_inputs.py` | Stores per-deal simulation input paths so "Rerun simulation" is a single-click operation |
| `comments.py` | Metric-level and deal-level threaded comments with @-mention parsing for notification dispatch |
| `approvals.py` | Lightweight IC approval workflow: VP review and partner investment approval with pending/approved/rejected status |
| `health_score.py` | Composite 0-100 health score (green/amber/red bands) rolled up from covenant status, variance, and alert counts |
| `note_tags.py` | Per-note tags for slicing analyst context (e.g., `board_meeting`, `blocker`) beyond full-text search |
| `watchlist.py` | Deal starring/watchlist with idempotent toggle for quick `/watchlist` filtering |

## Key Concepts

- **Append-only audit trails**: Notes, ownership history, and comments are never deleted or edited -- corrections are new records.
- **Stage-gated transitions**: Only allowed transitions are permitted (e.g., `pipeline` can move to `diligence` or `closed`, not directly to `hold`).
- **Health score transparency**: Every deduction from the starting score of 100 is named and traceable in the `components` list.
