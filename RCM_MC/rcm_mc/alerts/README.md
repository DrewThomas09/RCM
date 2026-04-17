# Alerts

Portfolio-wide alert evaluation, acknowledgement, and history tracking. Answers the PE analyst's Monday-morning question: "what broke over the weekend?" Evaluators are stateless and idempotent -- they never mutate the store and are safe to call on every page view.

| File | Purpose |
|------|---------|
| `alerts.py` | Fixed set of alert evaluators that scan the portfolio for covenant trips, variance breaches, and concerning-signal clusters; returns severity-tagged `Alert` records |
| `alert_acks.py` | Per-trigger-instance acknowledgement and snooze system with append-only audit trail; acks auto-expire when the underlying state changes |
| `alert_history.py` | Upsert log tracking first-seen/last-seen timestamps and sighting counts per alert; powers escalation views for alerts live >30 days |

## Key Concepts

- **Severity levels**: `red` (immediate attention), `amber` (watch), `info` (notable but not action-required).
- **Trigger-key based acks**: Acks are keyed on `(kind, deal_id, trigger_key)` so they automatically unmute when the underlying data changes.
- **Append-only history**: Alert history and ack records are never deleted, providing a full audit trail.
