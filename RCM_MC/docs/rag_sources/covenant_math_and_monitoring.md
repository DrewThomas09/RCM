# Covenant Math & Monitoring

How PEdesk computes covenant ratios, headroom, and the early-warning bands so
the Guide can answer "what does covenant cushion mean", "how is it
calculated", and "what's the difference between trip and tight".

## Covenant types PEdesk handles

- **Leverage covenants** — Total debt / TTM EBITDA, Senior debt / EBITDA,
  Net debt / EBITDA. Set as a **maximum** (ratio must stay below the
  threshold).
- **Coverage covenants** — Fixed-charge coverage (FCCR), Interest coverage
  (ICR). Set as a **minimum** (ratio must stay above the threshold).
- **Capex / cash limits** — Maintenance capex cap, minimum liquidity. Per
  the deal's credit agreement.

Each tracked deal stores its covenant schedule in the deal store; the
covenant module reads the latest snapshot's financials, computes each
ratio, compares to the threshold, and reports headroom.

## Headroom formula

For a max-ratio covenant (e.g. leverage):
```
headroom_pct = (threshold - current_ratio) / threshold
```
Positive = below the cap; negative = breach.

For a min-ratio covenant (e.g. ICR):
```
headroom_pct = (current_ratio - threshold) / threshold
```
Positive = above the floor; negative = breach.

For multi-covenant deals, the **lowest-headroom** covenant is reported as
the binding constraint. Computed in `rcm_mc.deals.covenants`. Stored as
the `covenant_cushion` metric.

## The early-warning bands

- **Headroom > 25%** = green. Comfortable.
- **Headroom 15-25%** = early-warning band. Worth a monthly review and
  often the trigger for tightening working-capital monitoring.
- **Headroom 0-15%** = tight. Partners typically open conversations with
  the lender about waivers or amendments here.
- **Headroom < 0** = trip. Breach has technically occurred; depending on
  the credit agreement, the lender can call default or grant a waiver.

These bands drive the alert evaluators in `rcm_mc.alerts`:
- Tight (0-15%) → amber alert.
- Trip (<0) → red alert. Persists until cured (headroom back > 15%) or
  waived (audit-logged).

## How tight is "tight"?

PE shops vary, but the conventions PEdesk follows:

- 15% is the standard amber band because EBITDA can swing 5-10% in a
  quarter from working-capital effects alone; that swing eats half the
  cushion.
- The recommended action at < 15% is to start the conversation with the
  lender BEFORE a breach forces it.
- A waiver after-the-fact is more expensive (and looks worse to LPs)
  than a proactive amendment.

## Monthly cadence

- Covenant ratios are recomputed whenever monthly actuals upload via
  `/import`.
- Headroom values are cached in `portfolio_snapshot` so the page is fast.
- If actuals haven't uploaded in >60 days, the page flags the values as
  stale; treat them as last-known-state, not current.

## What PEdesk does NOT do

- Does not auto-amend covenants — partner judgment + lender conversation.
- Does not predict future headroom from operating projections; that lives
  on `/scenarios/design` and `/diligence/covenant-stress`.
- Does not handle covenants outside the credit agreement (e.g. sponsor-
  level NAV covenants).

## Related surfaces

- `/portfolio/monitor` — daily dashboard surfacing the binding-covenant
  headroom per deal.
- `/covenant-headroom` — per-deal drill-in showing every covenant + its
  cushion.
- `/covenant-monitor` — sector-level monitoring view.
- `/diligence/covenant-stress` — pre-IC sensitivity on what shocks
  break the structure.
- `/methodology` — formal documentation including the recommended-action
  matrix and the calibration log.
