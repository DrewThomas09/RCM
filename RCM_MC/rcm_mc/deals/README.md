# Deals

Deal lifecycle management: creation, staging, ownership, tagging, notes, comments, health scoring, approvals, and watchlist tracking. Provides the per-deal metadata layer consumed by analysis, alerts, and all UI components.

---

## `deal.py` — Deal Creation Orchestrator

**What it does:** The `rcm-mc deal new` CLI command and the `/new-deal` wizard backend. Sequences intake → ingest → simulation run → portfolio registration into one command.

**How it works:** Calls `data/intake.py` (interactive wizard) or parses a pre-built YAML config (non-interactive mode). Invokes `data/ingest.py` to normalize data. Queues a simulation run via `infra/job_queue.py`. Registers the deal in the portfolio store with initial stage `pipeline`. Returns the new `deal_id`. In non-interactive mode, accepts `--config`, `--name`, `--stage` flags.

**Data in:** Analyst keyboard input (interactive) or YAML config file (non-interactive); seller data files processed by `data/ingest.py`.

**Data out:** New deal row in `deals` SQLite table; initial simulation queued; portfolio store registration.

---

## `deal_stages.py` — Deal Stage Lifecycle

**What it does:** Manages deal stage transitions (pipeline → diligence → ic → loi → spa → hold → exit) with validated transitions, timestamps, and automation-engine event triggers.

**How it works:** Defines an allowed-transitions matrix (dict of `{current_stage: [valid_next_stages]}`). `transition_stage(deal_id, new_stage)` validates the transition, writes the new stage and `stage_changed_at` timestamp to the `deals` table, and fires an `automation_engine.py` event. `get_stage_history(deal_id)` returns the full stage timeline from the `deal_stage_history` audit table (append-only, never updated).

**Data in:** Current deal stage from `deals` table; analyst-requested next stage from the UI or CLI.

**Data out:** Updated `deals.stage`; new row in `deal_stage_history`; automation event for rule-based workflow.

---

## `deal_owners.py` — Per-Deal Ownership Assignment

**What it does:** Assigns a primary analyst/associate owner to each deal. Provides per-owner deal lists for the `/my/<owner>` personal dashboard.

**How it works:** CRUD layer over `deal_owners` SQLite table. `assign_owner(deal_id, username)` writes a new ownership record with timestamp, creating an append-only history (ownership transfers are recorded, not overwritten). `deals_for_owner(username)` returns all active deals assigned to that user with health scores. `owner_for_deal(deal_id)` returns the current (latest) owner.

**Data in:** Analyst username from the logged-in session; deal_id from the deal page.

**Data out:** Ownership records for the `/my/<owner>` personal dashboard; ownership history for the deal audit trail.

---

## `deal_tags.py` — Freeform Deal Tagging

**What it does:** Lets analysts tag deals with freeform labels (thesis type, fund vintage, geography, lead analyst, watchlist signals) for cohort analytics and search.

**How it works:** Tags stored in `deal_tags` SQLite table with `(deal_id, tag)` unique pairs. Tags are case-insensitively normalized (stored lowercase). `add_tag()`, `remove_tag()`, `tags_for(deal_id)`, `all_tags()` (for autocomplete), `deals_with_tag(tag)`. Tags are indexed for the `/cohorts` page and `analysis/cohorts.py` group-by analytics.

**Data in:** Analyst-entered tag strings via the deal page or `POST /api/deals/<id>/tags`.

**Data out:** Tag assignments for `analysis/cohorts.py`, the deal page tag display, and full-text search indexing.

---

## `deal_notes.py` — Append-Only Per-Deal Notes

**What it does:** Records analyst notes on deals: IC rationale, site visit observations, management call summaries, diligence findings. Append-only — no edits or deletes.

**How it works:** Notes stored in `deal_notes` table with deal_id, author (username), body (text), timestamp (UTC ISO), and optional `note_type` tag. `record_note(deal_id, author, body)` inserts. `list_notes(deal_id)` returns chronologically. `search_notes(query)` does LIKE-based search across all deals (used by `analysis/cross_deal_search.py`). Notes feed the activity feed on the deal page.

**Data in:** Note body and author from the deal page or `POST /api/deals/<id>/notes`.

**Data out:** Note history for the deal page activity feed; searchable by `cross_deal_search.py`.

---

## `deal_deadlines.py` — Per-Deal Task and Deadline Tracking

**What it does:** Manages time-sensitive tasks and deadlines for a deal: "Get updated AR aging by Nov 15", "IC draft due Dec 1". Surfaces upcoming and overdue items on the portfolio dashboard.

**How it works:** `deal_deadlines` SQLite table with deal_id, title, due_date, status (open/completed/overdue), assigned_to, created_by, created_at. `add_deadline()` uses `BEGIN IMMEDIATE` to prevent concurrent-write races on deadline insertion. `complete_deadline(id)` marks done with timestamp. `upcoming_deadlines(days=7)` and `overdue_deadlines()` return cross-portfolio lists for the Monday morning view.

**Data in:** Analyst-entered deadline data via `POST /api/deals/<id>/deadlines`.

**Data out:** Deadline lists for the portfolio dashboard "upcoming deadlines" panel.

---

## `deal_sim_inputs.py` — Simulation Input Path Storage

**What it does:** Stores per-deal simulation input file paths (actual.yaml, benchmark.yaml) so "Rerun simulation" is a single-click operation — the analyst doesn't need to re-upload files.

**How it works:** `deal_sim_inputs` table with deal_id, actual_path, benchmark_path, last_updated. `set_paths(deal_id, actual, benchmark)` upserts the paths. `get_paths(deal_id)` retrieves them. The `packet_builder.py` step 9 (Monte Carlo) calls `get_paths()` to find the YAML files; if they exist, it runs MC; if not, the MC step is `SKIPPED`.

**Data in:** File paths from `data/ingest.py` after a successful ingest run; or analyst upload paths.

**Data out:** File paths consumed by `packet_builder.py` step 9 and the "Rerun simulation" job queue trigger.

---

## `comments.py` — Metric-Level and Deal-Level Threaded Comments

**What it does:** Metric-specific commenting: "Why is the denial rate at 14.5% when HCRIS shows 9%?" Supports @-mention parsing for notification dispatch.

**How it works:** `deal_comments` table with deal_id, metric_key (nullable — null means deal-level comment), body, author, parent_comment_id (for threading), created_at. `add_comment()` parses `@username` patterns and queues notifications via `infra/notifications.py`. `thread_for_metric(deal_id, metric_key)` returns the full thread. Threaded replies via parent_comment_id.

**Data in:** Comment body and author from the workbench metric popover or deal page.

**Data out:** Comment threads for the workbench metric popover; @-mention notifications via `infra/notifications.py`.

---

## `approvals.py` — Lightweight IC Approval Workflow

**What it does:** Manages the IC approval process: VP review → partner investment approval. Tracks pending/approved/rejected status and the rationale for each vote.

**How it works:** `deal_approvals` table with deal_id, approval_type (vp_review / partner_approval), approver_username, status (pending/approved/rejected), rationale, timestamp. `request_approval()` creates a pending row and sends a notification. `vote(approval_id, status, rationale)` records the decision. `approval_status(deal_id)` returns the current approval state for the IC checklist. Uses `BEGIN IMMEDIATE` to prevent race conditions on simultaneous approval submissions.

**Data in:** Approval requests from the IC prep workflow; votes from VP and partner users.

**Data out:** Approval status for the IC checklist (`GET /api/deals/<id>/checklist`) and deal stage gating.

---

## `health_score.py` — Deal Health Score (0–100)

**What it does:** Computes a composite 0–100 health score per deal with green/amber/red band classification. The score rolls up covenant status, variance from plan, alert severity, and data completeness into a single monitoring signal.

**How it works:** Starts at 100. Deducts: up to 30 points for covenant risk (based on leverage ratio distance from covenant threshold via `pe/debt_model.py`), up to 25 points for cumulative variance from the value creation plan (via `pe/hold_tracking.py`), up to 25 points for active critical/high alerts (via `alerts/alerts.py`), up to 20 points for data quality (from `analysis/completeness.py` grade). Each deduction is named and traceable in the `components` list. Returns `HealthScore` with `score`, `band` (green/amber/red), `components` list, and a trend sparkline from the last 6 score snapshots.

**Data in:** Active alerts from `alerts/alerts.py`; variance data from `pe/hold_tracking.py`; covenant status from `pe/debt_model.py`; completeness grade from `analysis/completeness.py`.

**Data out:** `HealthScore` for the deal page, portfolio dashboard cards, and alert severity amplification.

---

## `note_tags.py` — Per-Note Tagging

**What it does:** Applies tags to individual notes for context slicing beyond full-text search (e.g., tag a note as `board_meeting` or `blocker`).

**How it works:** `note_tags` table with note_id and tag. `tag_note()`, `tags_for_note()`, `notes_with_tag(deal_id, tag)`. Tags are freeform but the UI suggests standard tags: `board_meeting`, `site_visit`, `management_call`, `blocker`, `ic_question`. Used to filter the deal activity feed.

**Data in:** Analyst-entered tag via note creation UI.

**Data out:** Tag-filtered note lists for the deal activity feed.

---

## `watchlist.py` — Deal Starring and Watchlist

**What it does:** Idempotent deal starring for quick `/watchlist` filtering. A partner can star deals they want to track closely without assigning formal ownership.

**How it works:** `watchlist` table with (username, deal_id) unique pairs. `toggle_star(username, deal_id)` inserts if not present, deletes if present — idempotent, uses `BEGIN IMMEDIATE` to prevent concurrent-toggle races. `starred_deals(username)` returns starred deal_ids. The `/watchlist` UI page filters to starred deals. The `deals_for_owner()` query includes a `is_starred` join so the personal dashboard shows stars inline.

**Data in:** Username from the session; deal_id from the star button click.

**Data out:** Starred deal list for the `/watchlist` page and personal dashboard.

---

## Key Concepts

- **Append-only audit trails**: Notes, ownership history, and approval records are never deleted or edited — corrections are new records.
- **Stage-gated transitions**: Only allowed transitions are permitted. Attempting to move directly from `pipeline` to `hold` raises an error.
- **Health score transparency**: Every deduction from the starting 100 is named and traceable in the `components` list.
