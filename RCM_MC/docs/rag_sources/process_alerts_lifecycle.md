# Backend Process: Alerts Lifecycle

How PEdesk turns portfolio signals into an actionable, auditable triage queue,
so the Guide can explain the /alerts and /escalations surfaces.

## The lifecycle
fire → acknowledge / snooze → history (with age) → escalate → returning-badge
(when a snooze expires the alert returns, flagged). Each alert carries a
severity (Critical / Warning / Info) and an age.

## How alerts are generated
Rule-based evaluators run over the LATEST per-deal snapshots in the portfolio
store — covenant trip/tight, EBITDA-variance misses (amber vs red bands),
concerning-signal clusters, stage regressions, snapshot-freshness. (Exact
thresholds live in `rcm_mc/alerts/`.)

## How to read it
- An empty alerts list is an affirmative "all clear", not missing data.
- Severity is rule-assigned from snapshot signals, not a partner judgment.
- Alerts reflect only what the latest snapshots contain — an alert NOT firing
  is not proof a risk is absent.
