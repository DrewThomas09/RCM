# DECISIONS — CDD Analytics Expansion (session claude/pedesk-cdd-analytics-cvzvgf)

Architectural and routing decisions for the CDD analytics build. Append-only.
The pre-existing app decision log lives at `RCM_MC/DECISIONS.md`; this file
tracks decisions made during this session only.

## [2026-06-14 01:25] SESSION — CDD package location and shared foundation
Context: New CDD analytics features need a home that does not entangle with the
large existing rcm_mc surface, while still being wired into the app.
Options: A) scatter modules across existing analytics/ml dirs; B) one cohesive
`rcm_mc/cdd/` subpackage with a shared Exhibit contract and a registry the
server and CLI consume.
Decision: B. New code lives in `rcm_mc/cdd/`. Each feature is a module exposing
a pure compute function returning an `Exhibit`. A `registry` maps feature ids to
builders so the CLI (`rcm-mc cdd ...`) and server can enumerate and run them.
Rationale: keeps golden tests hermetic, satisfies "no orphan modules" by routing
every feature through one registered surface, and isolates from the 2,878-test
existing suite.
Reconciliation/Validation: `tests/golden/test_registry.py` asserts every
feature id in feature_list.json resolves to a registered builder.

## [2026-06-14 01:25] SESSION — Exhibit metadata + audience separation in code
Context: Part 4 requires sourced footnotes, em-dash-free copy, and audience
separation enforced in code, not convention.
Options: A) rely on existing HTML chart_kit source strings; B) a typed Exhibit
dataclass carrying machine-readable footnotes (source, vintage, assumptions),
audience gating, and a copy linter.
Decision: B. `rcm_mc/cdd/exhibit.py` defines `Exhibit`, `Footnote`,
`AssumptionNode`. `Exhibit.render(internal_mode=False)` strips assumption nodes
and internal-only series for partner output. A `lint_copy` helper rejects
em-dashes and AI filler in any user-facing string.
Rationale: makes Part 4 constraints testable rather than aspirational.
Reconciliation/Validation: `test_two_audience.py` asserts partner render omits
assumption nodes; `test_chartpack_standards.py` asserts footnote metadata and
em-dash-free labels on every exhibit.

## [2026-06-14 01:25] SESSION — Statistical-only inference, seeds pinned
Context: Part 4 hard constraint: no LLM on any prediction path; determinism.
Decision: All CDD estimators use numpy / scipy / scikit-learn / lifelines /
ruptures only. Every stochastic path takes `seed` and uses
`np.random.default_rng(seed)`. No `np.random.*` global state.
Rationale: reproducibility to 1e-9 and auditability.
Reconciliation/Validation: reproducibility assertions in Monte Carlo and
conformal golden tests.

## [2026-06-14 04:30] NEW-01 SOM definition
Context: SOM can be a flat percentage of TAM or capacity-constrained.
Options: A) flat % of TAM; B) sales capacity times realistic win rate, capped at demand ceiling.
Decision: B.
Rationale: a flat TAM cut is not defensible in diligence; capacity times win rate ties SOM to the sales plan.
Reconciliation/Validation: test_tam_sam_som asserts SOM 4000 from 300 winnable units at the blended reachable price.

## [2026-06-14 04:30] NEW-02 PVM decomposition method
Context: many price-volume-mix decompositions exist; most are not exactly additive or reversal consistent.
Options: A) sequential first-difference; B) symmetric Bennet indicator.
Decision: B.
Rationale: Bennet is exactly additive and reversal consistent to machine precision.
Reconciliation/Validation: test_pvm_bridge asserts additivity 1e-6 and reversal negation.

## [2026-06-14 04:30] NEW-04 reimbursement basis handling
Context: percent-of-Medicare can be medical-services-repriced or facility-inclusive.
Options: A) blend to one number; B) label each basis and never blend.
Decision: B.
Rationale: blending bases produces a meaningless ratio; RAND and Milliman anchors sit on different bases.
Reconciliation/Validation: test_pct_medicare asserts basis label on every output and a basis_mismatch flag.

## [2026-06-14 04:30] NEW-05 small-cohort threshold
Context: small cohorts give unreliable Kaplan-Meier estimates.
Options: A) no flag; B) flag cohorts below 30 members.
Decision: B, threshold 30.
Rationale: 30 is the conventional small-sample boundary; below it KM curves are too noisy to defend.
Reconciliation/Validation: test_retention_survival asserts the small_cohort flag for a 10-member cohort.

## [2026-06-14 04:30] NEW-11 Monte Carlo default model
Context: drivers must combine into an outcome.
Options: A) additive on revenue; B) base times one plus the sum of fractional shocks.
Decision: B.
Rationale: fractional shocks compose naturally for rate cuts and attrition and keep the model unit-free.
Reconciliation/Validation: test_monte_carlo_overlay asserts P50 near theory and 1e-9 reproducibility.

## [2026-06-14 04:30] NEW-13 FFS correction weight
Context: grossing FFS-only activity to all-population needs a weight.
Options: A) add MA penetration; B) divide by FFS share, weight 1/(1-MA).
Decision: B.
Rationale: FFS counts cover only the FFS share of the population; dividing by that share recovers the whole.
Reconciliation/Validation: test_ffs_correction asserts MA 0.50 grosses 1000 to 2000.

## [2026-06-14 05:00] BOLSTER-01 conformal coverage design
Context: a pure time trend with Ridge shrinkage on an unscaled feature breaks conformal exchangeability on the holdout.
Options: A) raw feature + Ridge; B) StandardScaler pipeline + exchangeable design for the coverage test.
Decision: B.
Rationale: scaling removes shrinkage bias; exchangeable calibration and holdout are required for the split-conformal guarantee.
Reconciliation/Validation: test_ridge_conformal_bolster asserts empirical coverage >= nominal - 1% at 80 and 95.

## [2026-06-14 05:20] BOLSTER-03 changepoint default penalty
Context: PELT needs a penalty; too low over-segments, too high misses breaks.
Options: A) fixed constant; B) BIC-style sigma^2 log(n) with a robust sigma from the median absolute first difference.
Decision: B.
Rationale: scales with noise so a noisy series does not over-segment and a flat series yields none.
Reconciliation/Validation: test_changepoint asserts one break on a clear shift and zero on a flat series.

## [2026-06-14 19:30] NEW-19 marimekko width/height encoding
Context: a healthcare profit-pool marimekko can use the textbook revenue-width by
margin-height encoding or McKinsey's EBITDA-share by EBITDA-share variant.
Options: A) revenue width and margin height; B) width is sector share of total
industry EBITDA and height is sub-segment share of its sector's EBITDA.
Decision: B as the primary, with A offered as an alternate when revenue and
margin are supplied.
Rationale: faithful recreation of the McKinsey healthcare profit-pool map, where
rectangle area reads as a sub-segment's share of total industry EBITDA; the
classic encoding stays available for margin-pressure diligence.
Reconciliation/Validation: test_marimekko asserts widths sum to 1.0, areas sum
to 1.0, and the 10/50/5/35 sector widths of the published 2017/18 map.

## [2026-06-14 19:30] NEW-18 CAGR bracket coverage and undefined handling
Context: a profit-pool exhibit needs CAGR brackets, and CAGR is undefined when a
base or endpoint is non-positive or the span is zero.
Options: A) emit a single full-span CAGR; B) emit consecutive-pair brackets plus
the full span, and return None for an undefined CAGR rather than a number.
Decision: B.
Rationale: multi-column decks want both adjacent and end-to-end growth; a None
keeps a meaningless ratio out of a bracket instead of printing a misleading one.
Reconciliation/Validation: test_profit_pool asserts total CAGR 7.0% and HST 12%
hand-verified, plus a reconciliation that the full-span CAGR rebuilds the final
total from the first.

## [2026-06-14 19:30] NEW-20 growth quadrant threshold
Context: the historic-vs-projected growth map needs a quadrant line.
Options: A) median of each axis; B) a fixed 5 percent growth line on both axes.
Decision: B, default 5 percent (overridable).
Rationale: the McKinsey archetype map uses an absolute 5 percent growth line, not
a relative median, so high-growth pools are defined consistently across vintages.
Reconciliation/Validation: test_growth_archetype asserts the four quadrant
assignments and the high-growth EBITDA share 299/389 hand-verified.
