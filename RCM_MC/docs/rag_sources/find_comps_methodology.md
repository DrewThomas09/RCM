# Find Comps — Comparable Transaction Search

How `/find-comps` and the underlying `rcm_mc.analysis.find_comps` module
identify the realized-deal corpus's closest peers to a query target, so the
Guide can answer "find me comps for this deal", "what's the peer MOIC", and
"why is this deal NOT a comp".

## What it does

Given a query deal's characteristics, finds the **N most similar realized
deals** from the corpus and reports peer benchmarks: MOIC, IRR, hold-period,
exit multiple, sponsor type, exit path. Used early in diligence to anchor
the underwriting case against precedent.

The corpus is a curated set of historical PE healthcare transactions with
sourced realized outcomes (no fabrication; entries with unknown outcomes
are tagged as such).

## How "similar" is measured

Multi-feature distance with weighted features. The match score is a
weighted sum of the feature-by-feature similarity:

- **Sector** (35 weight) — exact-match or aligned-sector (e.g. dermatology
  → multi-specialty derm).
- **Size** (20 weight) — entry EV bucket (within ±50% gets full credit;
  the closer the better).
- **Year** (20 weight) — closer cohorts score higher; an entry within
  the same 3-year window earns full credit.
- **Payer mix** (15 weight) — Medicaid-heavy vs commercial-heavy vs
  balanced. Hospitals with a 60% Medicaid mix do not comp to
  commercial-heavy ASCs.
- **Sponsor** (10 weight) — exact sponsor match adds points (a sponsor's
  prior playbook is the closest precedent).

Maximum possible match score = 100. Anything below 50 is "weak comp";
50-70 is "fair"; 70+ is "strong".

The exact scoring lives in `rcm_mc.analysis.find_comps`.

## Outputs

- Ranked peer table: deal name (or anonymized), match score, sector,
  entry year, entry EV, exit EV / MOIC / IRR / hold, exit path
  (strategic / sponsor-to-sponsor / IPO / write-down).
- Distribution stats across the peer set: median MOIC, MOIC IQR, median
  hold-years, exit-path frequency.
- Per-feature breakdown of the match score so partners can see WHY a
  particular comp scored high (sector match + sponsor match) vs low
  (different cohort, different size band).

## Common partner questions the Guide should answer

- *"What's the peer MOIC for this deal?"* — Look at median MOIC across
  the top-5 strong-match comps; mention sample size and IQR.
- *"Who are the closest comps?"* — Top-3 by match score with a one-line
  reason.
- *"Why is X NOT a comp?"* — Pull the per-feature breakdown; the most
  common reason is sector misalignment or sponsor mismatch.
- *"What exit path is most common for deals like this?"* — Frequency
  across the peer set.
- *"How long do comps hold?"* — Median + IQR of hold-years.

## Interpretation guidance

- A small peer set (n < 5 strong-match comps) reflects a thinner cohort;
  treat distributions as illustrative not authoritative.
- Sponsor match is a strong signal but it doesn't mean replicable — the
  same sponsor's later vintages may have different playbooks.
- Payer-mix match is the single most-skippable feature for general
  consolidation plays; weight it lower for non-rate-exposure deals.
- The corpus has a survivorship-bias risk: failed deals are
  under-represented because they generate fewer public press releases.
- Year-bucket gets less weight at long lookbacks because exit-multiple
  norms shift across cycles.

## What it is NOT

- Not a price-target generator. It anchors the range; partner judgment
  picks the case.
- Not the same as `/comparables` (which is a peer-PEER metric benchmark
  on **public hospital financials**, not deal outcomes).
- Not a substitute for cohort-correct base rates (see
  `predictive_modeling_boundaries.md`).
- Not an exit-path predictor. Frequency of strategic exits in the
  corpus is descriptive, not predictive.

## Related surfaces

- `/find-comps` — the comparable-transaction search.
- `/comparables` — public-data peer benchmark (different signal).
- `/diligence/comparable-outcomes` — distribution view of comp outcomes.
- `/deal-screening` — apply screen criteria against the corpus.
- `/comp-set` — saved peer sets per deal.
- `/methodology` — full documentation of the scoring weights and the
  corpus criteria.
