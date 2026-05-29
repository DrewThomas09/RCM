# Health Score Methodology

How PEdesk's composite per-deal health score is computed and what it means,
so the Guide can explain it when a partner asks "what does 72/100 mean for
this deal?".

## What it is

Health score is a 0-100 composite that summarises a portfolio company's
current monitoring state in a single number. It rolls up four sub-signals
into one read partners reach for during the morning portfolio scan
(instead of opening 8 separate dials).

Lives in `rcm_mc.deals.health_score` and is surfaced on
`/portfolio/monitor`, `/my/<owner>`, `/dashboard`, and the deal-card row
on `/watchlist`.

## The four sub-signals

1. **Plan realization** — EBITDA % of the value-creation plan over the
   last 4 quarters. A deal hitting 100% of plan gets a perfect sub-score
   here; one running at 75% gets a partial credit.
2. **Covenant cushion** — current covenant headroom % (see the
   `covenant_cushion` metric entry). Headroom < 15% triggers an
   early-warning sub-score; headroom < 0 (a covenant trip) zeros it.
3. **Alert posture** — count of active red + amber alerts. More active
   alerts = lower sub-score. An alert at amber for >30 days counts
   double.
4. **Trend slope** — direction of EBITDA over the last 4 quarters
   (positive slope = healthy, negative slope = degrading). Detects
   deals quietly drifting before they trip a band.

## The blend

Weighted blend of the four sub-signals; weights documented in
`rcm_mc.deals.health_score` and reviewed each quarter via the
`/methodology` calibration log. The blended score is clamped to
[0, 100] then bucketed into reading bands:

- **80+** = green (healthy, no immediate concern)
- **60-79** = amber (worth a partner check-in this week)
- **<60** = red (should have an active alert; due for an escalation)

## How to read it

- Score is a **heuristic** not a prediction. Pair it with the active-alert
  detail before acting.
- A score of 90 doesn't mean the deal is risk-free — it means none of
  the four monitored signals is flashing.
- A score that's stable but the trend slope sub-signal is negative is
  the early-warning case: surface-clean but quietly worsening.
- Score recomputes whenever any source signal updates: monthly actuals
  upload, covenant ratio recalculation, alert fire/snooze/ack, snapshot
  refresh.

## What it is NOT

- Not a forecast or a price target.
- Not a substitute for partner judgment.
- Not comparable across funds with different covenant structures
  (cushion sub-signal depends on the actual covenant terms).
- Not a credit-rating equivalent — it tracks monitoring state, not
  default probability.

## Related surfaces

- `/portfolio/monitor` — the daily dashboard scoring all tracked deals.
- `/escalations` — red-zone deals that have stayed red past N days.
- `/watchlist` — pinned subset for focused monitoring.
- `/audit` — every recompute is audit-logged; reviewable if a partner
  asks why a score moved.
- `/metric-glossary#health_score` — canonical reference.
