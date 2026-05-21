# 10 · Portfolio workflow & operations

> The daily-driver workflow a partner/associate uses to *run* the book (as opposed to analyze a deal): alerts, cohorts, owners, deadlines, notes, tags, the LP digest, audit. These are **workflow state in SQLite**, not modeled numbers — so "where does it come from" here means which table and which lifecycle, not a formula.

---

## Alerts — the lifecycle
`rcm_mc/alerts/` (+ `alert_history`, `alert_acks` tables). An alert moves through a defined lifecycle:
**fire → ack / snooze → history (ages) → escalate → returning-badge when a snooze expires.**
- **Fire:** `evaluate_active(store)` derives live alerts from deal state — each `Alert{kind, severity (red/amber/info), deal_id, title, detail}`. Kinds include covenant_tripped, plan_drift, lagging_initiative, deadline_overdue, source_stale, concerning_cluster, stage_regress.
- **Ack / snooze:** an alert can be acknowledged or snoozed (recorded in `alert_acks` with a trigger key so the same condition doesn't re-fire spuriously).
- **History + age:** `alert_history` keeps the trail; alerts show age.
- **Escalate:** unresolved alerts escalate (surfaced on `/escalations`).
- **Returning badge:** when a snooze expires and the condition still holds, the alert returns with a "returning" badge.
- **Surfaces:** `/alerts` (list, `?show=`/`?owner=`), `/escalations`, and the `/app` alerts block (§02). The CTA per alert routes by kind (covenant→Variance, drift→Playbook, stale→Source).

## Cohorts, owners, watchlist, deadlines, notes, tags
All in `rcm_mc/deals/` with their own tables:
- **Cohorts** (`/cohorts`, `/cohort/<tag>`) — slice the book by tag.
- **Owners** (`/owners`, `/owner/<o>`, `assign_owner`) — who leads each deal; `/my/<owner>` is the personal dashboard (pulse + health mix for that owner's deals).
- **Watchlist** (`/watchlist`, `star_deal`) — starred deals.
- **Deadlines** (`/deadlines`, `deal_deadlines.add_deadline`) — per-deal dated tasks; overdue ones fire alerts and show on the risk scan.
- **Notes** (`/notes`, `deal_notes`, `note_tags`) — searchable notes, tag-filterable; soft-deleted (`deal_notes` uses the soft-delete policy).
- **Tags** (`deal_tags`) — labels for slicing.
- **Activity** (`/activity`) — the event/audit feed (`?limit`/`?owner`/`?kind`).

## Health score
Documented in §03 — the 0–100 deduction model per deal, with a 90-day sparkline. It's the headline of the deal dashboard and the `/portfolio/monitor` health bar; persisted to `deal_health_history`.

## LP digest
`/lp-update` (+ `reports/lp_update`, `/exports/lp-update`) — a partner-ready LP digest assembled from portfolio state (deals, snapshots, value-creation), exportable as HTML/download. This is reporting output, not a new computation — it formats existing portfolio numbers.

## Deal lifecycle operations
Create / archive / unarchive / clone / delete (cascade across ~23 child tables) / pin / validate / IC checklist — all via the `deals/` modules through `PortfolioStore` (with `BEGIN IMMEDIATE` on check-then-write paths). The delete-policy matrix (§`PEDESK_DATA`) governs what cascades vs sets-null vs soft-deletes.

## Simulation queue
An in-memory single-worker queue (`infra/job_queue`) for per-deal rerun (uses the stored `actual.yaml`/`benchmark.yaml` paths). **Jobs are lost on restart** — fine for partner-driven reruns (just click rerun again), not for cron (use the CLI). `/jobs`, `/jobs/<id>`.

## Audit & security
- **Audit log** — every state-changing action is appended (with the request ID); sensitive views (`/admin`, `/users`, `/audit`, `/settings`) are specifically audited. `/audit`, `/admin/audit-chain` (integrity).
- **Multi-user** — scrypt passwords + session cookies + CSRF + rate-limited login + idempotency keys (§`PEDESK_OVERVIEW` §9).

---

## Where these numbers come from — summary
Everything in this file is **live portfolio workflow state** read from SQLite tables (`alerts`/`alert_history`/`alert_acks`, `deal_notes`/`deal_tags`/`deal_owner_history`/`deal_deadlines`/`deal_stars`, `deal_health_history`, `audit_events`), not the corpus and not a packet. The only "computation" is the health-score deduction model (§03) and the alert-firing rules (`evaluate_active`).

---
*Next: `11_METRIC_GLOSSARY.md` — the canonical definitions behind the metric names used everywhere.*
