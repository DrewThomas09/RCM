# PEdesk prediction / modeling data-readiness audit

_Phase 5 of the Guide-coverage loop. The question is narrow and disciplined:
**before building any predictive model, do the labels actually exist?** If
they don't, we document the gap and how to source it — we do **not** train a
model on a label we don't have._

## Headline finding

**PEdesk is not yet ready to train supervised predictive models on the CMS
vertical data, because there are no labels.** Every vertical is vendored as a
**single dated cross-sectional snapshot**:

| Vertical | Snapshot date | Capacity fields | Concurrent event fields |
|---|---|---|---|
| Home Health | 2026-05-23 | — | — |
| Hospice | 2026-05-23 | — | — |
| SNF / Nursing Home | 2026-04-01 | certified_beds, avg_residents_per_day | sff_status, abuse_icon, changed_ownership_12mo |
| Dialysis | 2026-03-25 | dialysis_stations | — |
| IRF | 2026-02-13 | — | — |
| LTCH | 2026-02-13 | total_beds | — |

A supervised model needs an **outcome label** — usually a *future* event or a
*change over time*. With one snapshot per provider we can observe **levels**,
never **transitions**. So the change/decline/closure/growth labels below
cannot be constructed today, and the few event-like fields (SNF SFF / abuse /
penalties / ownership-change) are **concurrent states, not forward outcomes** —
using them as labels and as features would leak.

## Label matrix

`available` = a true label exists now · `partial` = a concurrent proxy exists
but is not a forward outcome (leak risk) · `absent` = needs data we don't have.

| Label | HH | Hospice | SNF | Dialysis | IRF | LTCH | Why |
|---|---|---|---|---|---|---|---|
| **Distress** (financial) | absent | absent | partial¹ | absent | absent | absent | No financials in CMS public quality data |
| **Closure** | absent | absent | absent | absent | absent | absent | Needs multi-snapshot diff to see a provider disappear |
| **Enforcement event** | absent | absent | partial² | absent | absent | absent | SNF has concurrent SFF/abuse/penalty *state*, not a dated future event |
| **Quality deterioration** | absent | absent | absent | absent | absent | absent | Needs ≥2 snapshots to measure a drop |
| **Staffing decline** | absent | absent | absent³ | absent | absent | absent | SNF has staffing *level* at one date; decline needs history |
| **Ownership change** | absent | absent | partial⁴ | absent | absent | absent | SNF has a backward-looking "changed in last 12mo" flag, not a forward label |
| **Utilization decline** | absent | absent | absent⁵ | absent⁵ | absent | absent⁵ | Census/beds/stations are point-in-time; decline needs history |
| **Reimbursement / payment proxy** | absent | absent | partial⁶ | absent | absent | absent | SNF payment-denial *count* exists; no $ reimbursement anywhere |
| **Growth** | absent | absent | absent | absent | absent | absent | Needs history (bed/census/volume over time) |

¹ SNF SFF status is a *regulatory*-distress proxy, not financial distress.
² Concurrent enforcement state — would leak if used as both label and feature.
³ `staffing_rating` / `total_nurse_hprd` / `turnover_pct` are one-date levels.
⁴ `changed_ownership_12mo` looks backward; a forward "will change" label needs longitudinal data.
⁵ `avg_residents_per_day`, `certified_beds`, `dialysis_stations`, `total_beds` are point-in-time capacity/census.
⁶ `num_payment_denials` is a count, not a reimbursement amount or trend.

## What this means for modeling

- **Do not train** distress / closure / deterioration / decline / growth
  models now — there is no label to learn.
- The **investable-evidence layer** (Phase 4) is the correct ceiling for
  today's data: *descriptive, peer-relative quality evidence*, explicitly not
  a forecast.
- Any model trained on concurrent SNF event flags as labels would **leak**
  (the flag is also a feature) — out of scope.

## How to source the missing labels (recommended, in priority order)

1. **Build a longitudinal snapshot spine (the single highest-value step).**
   Retain each dated CMS snapshot we already download instead of overwriting
   it, keyed by `(ccn, source_date)`. Two+ snapshots immediately unlock
   *quality deterioration*, *staffing decline*, *utilization decline*,
   *growth*, and *forward ownership-change* labels — with no new data source,
   just retention discipline. **No model until ≥2 clean snapshots exist per
   vertical.**
2. **Closure detection** — derive from the spine: a CCN present in snapshot
   *t* and absent (or decertified) in *t+1*. Confirm against CMS provider
   enrollment / decertification files before trusting it.
3. **Dated enforcement events** — source CMS penalty/inspection histories
   (e.g. SNF Health Deficiencies + Penalties datasets) which carry event
   *dates*, enabling a true forward enforcement label without leakage.
4. **Financial distress / reimbursement** — bring in cost-report data (HCRIS
   for facilities that file) and, where licensed, claims-based utilization;
   only then are *distress* and *reimbursement-trend* labels real.
5. **Validation discipline (when labels exist):** temporal split (train on
   early snapshots, test on later), report calibration + uncertainty, check
   subgroup bias, and keep the prediction ≠ causation boundary — per
   `PEDESK_PREDICTIVE_MODELING_ROADMAP.md`.

## Bottom line

The honest readiness verdict is **panel-data-blocked**: the modeling roadmap
is sound, but the data is single-snapshot, so the gating next step is
**snapshot retention**, not model code.
