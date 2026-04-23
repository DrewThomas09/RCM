# Alerts

Portfolio-wide alert evaluation, acknowledgement, and history tracking. Answers the PE analyst's Monday-morning question: "what broke over the weekend?" Evaluators are stateless and idempotent — safe to call on every page view.

---

## `alerts.py` — Alert Evaluators

**What it does:** A fixed set of stateless alert evaluators that scan the portfolio for covenant trips, variance breaches, concerning-signal clusters, and data-staleness flags. Returns severity-tagged `Alert` records for the alerts page and the deal health score.

**How it works:** Each evaluator is a function that takes a `deal_id` and the portfolio store handle, reads the relevant data, and returns a list of `Alert` objects. Evaluators defined: `covenant_trip` (leverage ratio crossed threshold), `variance_breach` (quarterly variance > 15% from plan), `denial_spike` (denial rate increased > 2pp from prior quarter), `ar_deterioration` (AR days increased > 10 days), `data_staleness` (analysis packet >30 days old), `critical_risk_flag` (new CRITICAL flag in latest packet). Alert severity levels: `red` (immediate action), `amber` (watch), `info` (notable). Each `Alert` carries: `kind`, `deal_id`, `trigger_key` (a deterministic string for ack keying), `message`, `severity`, `metric_value`, `threshold`.

**Data in:** `portfolio/store.py` deal data; `analysis/analysis_store.py` latest packets; `pe/debt_model.py` covenant status; `pe/hold_tracking.py` variance data.

**Data out:** `Alert` list for the `/alerts` page, deal health score deduction in `deals/health_score.py`, and alert history upsert in `alert_history.py`.

---

## `alert_acks.py` — Acknowledgement and Snooze System

**What it does:** Per-trigger-instance acknowledgement and snooze system. Analysts can ack an alert (mark it reviewed) or snooze it (suppress for N days). Acks auto-expire when the underlying data changes.

**How it works:** `alert_acks` table with `(kind, deal_id, trigger_key)` unique key, `ack_type` (acknowledged / snoozed), `snoozed_until` (nullable datetime), `acked_by`, `acked_at`, `rationale`. The `trigger_key` is deterministic from the alert's data — when the underlying metric changes, the trigger_key changes, automatically un-muting the alert. `is_muted(alert)` checks the ack table for a matching trigger_key that hasn't expired. `snooze(alert, days, username)` sets `snoozed_until = now + days`. The returning-badge logic: when a snoozed alert reappears after the snooze expires, it's shown with a "returned" badge.

**Data in:** Alert objects from `alerts.py`; analyst ack/snooze actions via `POST /api/alerts/<id>/ack` or `POST /api/alerts/<id>/snooze`.

**Data out:** `is_muted()` result filters which alerts are shown; ack history for the deal audit trail.

---

## `alert_history.py` — Alert Escalation and History Log

**What it does:** Append-only log of alert sightings that tracks first-seen and last-seen timestamps, sighting counts, and escalation state. Powers the "escalate to CRITICAL" logic for alerts live > 30 days.

**How it works:** `alert_history` table with `(kind, deal_id, trigger_key)` unique key, `first_seen`, `last_seen`, `sight_count`. `upsert_sighting(alert)` inserts on first sight, then updates `last_seen` and increments `sight_count` on each subsequent evaluation. Escalation: `sight_count > 30 AND severity == 'amber'` → escalate to `red` with a "stale alert" annotation. The `escalated_alerts()` query returns alerts that have been alive > 30 days without being resolved or acked.

**Data in:** `Alert` objects from `alerts.py` on each evaluation pass.

**Data out:** Escalated alert list for the escalation panel; sighting history for the deal audit trail.

---

## Key Concepts

- **Trigger-key based acks**: Acks are keyed on `(kind, deal_id, trigger_key)` where `trigger_key` is derived from the actual triggering data. When the data changes, the key changes — automatically unmuting without manual clear.
- **Idempotent evaluators**: Alert evaluators are pure functions with no side effects. Safe to call on every page view or API request.
- **Escalation by age**: Alerts that persist > 30 days without resolution automatically escalate from amber to red, preventing alert fatigue from hiding genuine persistent issues.
