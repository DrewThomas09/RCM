# RAG source — HCRIS X-Ray: what it does and how to read it

**What HCRIS X-Ray is.** A CMS-HCRIS peer-benchmarking diligence tool. Enter a
hospital (name, CCN, or city); it pulls the target's Medicare cost-report
rollup, finds the 25–50 true peer hospitals (matched on size cohort, state,
payer mix, fiscal year), computes ~15 derived RCM / cost / margin metrics, and
flags where the target sits inside, above, or below the peer **P25–P75 band**.
Route: `/diligence/hcris-xray`.

**Input — the Workstation.** A two-up landing: left is the intake (identify
the hospital + the peer engine controls — peer-pool size, bed band, fiscal
year); right is a clearly-labelled **SAMPLE** preview (illustrative only —
never your target's data). Submitting runs the real engine.

**Results — Headline.** The report leads with a **top finding** — the single
most material *real* deviation (the biggest unfavorable peer gap, else the
strongest beat, else an honest "inside the band on every metric"). Below it:
the target identity, the full benchmark table (target vs P25 / median / P75
with a peer band per metric), the peer roster, and public-comp context.

**How to read it.**
- The **peer band** is the peer P25–P75 interquartile range; the diamond/marker
  is the target. Outside the box = an outlier worth diligence.
- **P25 / median / P75** describe the peer distribution, not a target.
- A red top finding is the *biggest gap to peers*, not a verdict — read it
  with the metric's direction (higher- vs lower-is-better) and the peer count.

**What to ask management.** What drives the flagged gap (case mix, payer mix,
one-time items)? Is it structural or fixable? How does it trend over the
3 available fiscal years?

**Observed vs derived.** Bed count, payer days, patient revenue, expenses, and
net income are *filed* (observed). Ratios (net-to-gross, opex/patient-day,
margins) are *derived* from those filings.

**What NOT to infer.** HCRIS is Medicare cost-report data — not commercial
contract rates, not a recoverable-EBITDA promise, not causation. The X-Ray
sizes the operational gap behind an EBITDA delta; it does not recommend.

**HCRIS X-Ray vs CMS Provider X-Ray.** HCRIS X-Ray is hospital-specific and
speaks to cost-report financials (beds/revenue/margin). The universal **CMS
Provider X-Ray** (`/diligence/xray`) generalizes the same design across
post-acute verticals (SNF, Home Health, Hospice, Dialysis, IRF, LTCH) using
CMS quality measures — no revenue/financials there, and only the sections each
vertical's real data supports.
