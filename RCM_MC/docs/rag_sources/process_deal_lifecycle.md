# Backend Process: Deal Lifecycle

The states a deal moves through and the data trail it leaves, so the Guide can
explain deal management (/deals, /pipeline, the deal page).

## Lifecycle
create / import → snapshot trail (point-in-time states) → archive / unarchive →
clone → delete (cascades across ~23 child tables in one transaction) → pin →
validate → IC checklist. Pipeline stages: sourcing → LOI → diligence → IC →
close.

## Data model notes
- Every per-deal page renders from the deal's analysis packet (see the analysis
  packet card) — one source of truth.
- Child tables use a deliberate delete policy (CASCADE for derivative
  analytics, SET NULL for audit artifacts, soft-delete for partner-visible
  records) so deletion behavior is intentional and auditable.
- Snapshots give variance (latest vs plan) and a health-score trend.

## How to read it
- An archived deal is hidden from active views but retained for audit; a cloned
  deal copies inputs, not realized history.
