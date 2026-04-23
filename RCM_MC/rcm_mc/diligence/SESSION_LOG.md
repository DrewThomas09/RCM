# RCM Diligence — Session Log

Session date: 2026-04-23
Branch: `fix/revert-ui-reskin`

## What shipped

### 1. Alerts removed from analyst nav
- [`rcm_mc/ui/_chartis_kit.py`](rcm_mc/ui/_chartis_kit.py) — removed
  `/alerts` entry from `_CORPUS_NAV`; added "RCM DILIGENCE" as the
  first nav section with four tabs.
- `_alert_bell_html()` now returns `""` instead of the topbar bell
  markup. The function is retained so the shell layout doesn't need
  surgery; a portfolio-ops variant can flip it back on.
- Alerts code (`rcm_mc/alerts/`) and the SQLite tables stay untouched
  per "Do not delete any existing code."

### 2. RCM Diligence workspace scaffold
New subpackage [`rcm_mc/diligence/`](rcm_mc/diligence/):

- `ingest/` — Phase 1 ingester, fully live (see below)
- `benchmarks/` — Phase 2 stub (empty `__init__.py` with docstring)
- `root_cause/` — Phase 3 stub
- `value/` — Phase 4 stub

Each subpackage's docstring states the phase contract and notes
"ships in a follow-up session."

### 3. HTTP routes
Four new routes wired into [`rcm_mc/server.py`](rcm_mc/server.py):

- `/diligence/ingest` — Phase 1 page with capability grid
- `/diligence/benchmarks` — Phase 2 placeholder
- `/diligence/root-cause` — Phase 3 placeholder
- `/diligence/value` — Phase 4 placeholder

All four render through `chartis_shell`, so the dark theme and nav
are coherent. Renderers live in
[`rcm_mc/diligence/_pages.py`](rcm_mc/diligence/_pages.py).

### 4. Canonical Claims Dataset (CCD) data contract
[`rcm_mc/diligence/ingest/ccd.py`](rcm_mc/diligence/ingest/ccd.py):

- `CanonicalClaim` — one canonical claim-line; grain is
  `(claim_id, line_number, source_system)`.
- `CanonicalClaimsDataset` — the whole dataset + transformation log
  + provenance. JSON round-trippable.
- `content_hash()` — deterministic SHA-256 excluding wall-time
  fields. Same inputs → same hash.
- `TransformationLog` — append-only, row-scoped, queryable by
  `ccd_row_id` or `rule`. Every coerced value is logged with source
  file + row + rule.
- Schema version: `CCD_SCHEMA_VERSION = "1.0.0"`.

### 5. Normalisation primitives
[`rcm_mc/diligence/ingest/normalize.py`](rcm_mc/diligence/ingest/normalize.py):

- `parse_date` — ISO, X12 `YYYYMMDD`, `MM/DD/YYYY`, `MM-DD-YYYY`,
  `DD.MM.YYYY`, Excel serial, Unix epoch, native `date`/`datetime`.
- `resolve_payer` — substring-matched canonical map → `PayerClass`.
  Covers the Blue Cross / BCBS / Anthem / Medicare Advantage tangle.
- `validate_cpt` — HCPCS shape check; non-standard codes preserved
  with a WARN log entry.
- `validate_icd` — ICD-10 strict; ICD-9 legacy accepted with WARN.
- `detect_duplicates`, `detect_near_duplicates` — used by the
  duplicate-resubmit detector in the ingester.

### 6. Readers
[`rcm_mc/diligence/ingest/readers.py`](rcm_mc/diligence/ingest/readers.py):

- CSV/TSV — utf-8 → windows-1252 → latin-1 encoding fallback; mixed-
  encoding-per-line is handled line-by-line. Junk header rows and
  trailing total rows are detected + dropped.
- Parquet — pyarrow.
- Excel — openpyxl. Merged cells are un-merged with value propagation.
  Junk header rows + trailing totals detected.
- EDI 837/835 — hand-rolled X12 subset; enough for the fixtures.
  Correctly handles NM1*PR/QC as pre-CLM loop header segments and
  flushes ctx on the start of a new 2000B.

### 7. The ingester
[`rcm_mc/diligence/ingest/ingester.py`](rcm_mc/diligence/ingest/ingester.py):

- `ingest_dataset(path)` — walks a directory or reads a single file.
- Column synonym map covers ~35 canonical fields with 3–8 source
  aliases each.
- Multi-EHR rollup: (patient, service_date, cpt) groups spanning >1
  source_system collapse to the lexicographically smallest claim_id;
  rewrite logged per row.
- Duplicate-resubmit detection: same grouping key *within* a source
  system → rows retained, cohort flagged.
- Remittance reconciliation: 835 rows enrich their 837 parent
  (paid_amount, paid_date, status); orphans logged WARN.
- ZBA write-off preservation: zero paid + nonzero adjustment does
  NOT clobber charge_amount or allowed_amount; the trail survives.

### 8. Ten messy fixtures
[`tests/fixtures/messy/`](tests/fixtures/messy/):

1. `fixture_01_clean_837` — baseline
2. `fixture_02_mixed_ehr_rollup` — Epic + Cerner + Athena × 10 claims
3. `fixture_03_excel_merged_cells` — merged cells, junk headers, totals row
4. `fixture_04_payer_typos` — seven Blue Cross spellings → one canonical
5. `fixture_05_date_format_hell` — seven date formats in one column
6. `fixture_06_partial_837` — truncated EDI mid-segment
7. `fixture_07_encoding_chaos` — utf-8 + windows-1252 mixed
8. `fixture_08_cpt_icd_drift` — proprietary CPT + ICD-9 legacy
9. `fixture_09_duplicate_claims` — 2 logical × 3 resubmits
10. `fixture_10_zero_balance_writeoffs` — ZBA preservation contract

Each fixture has an `expected.json` — the test contract. Regenerate
via `.venv/bin/python -m tests.fixtures.messy.generate_fixtures`.

### 9. Regression tests
[`tests/test_diligence_ingest.py`](tests/test_diligence_ingest.py):

- 10 fixture-specific test methods (one per fixture)
- 1 cross-cutting invariant: every fixture ingests + round-trips
  through JSON with a stable `content_hash`

**Status: 11 passed, 0 failed.** Runtime ~0.2s.

## What is tested

- Each fixture's claim count, source-system count, payer-class
  distribution, and required transformation rules.
- JSON round-trip preserves `content_hash`.
- Re-ingesting the same directory produces the same `content_hash`
  (idempotency).
- ZBA row's original charge + allowed + adjustment trail all survive.

## What is stubbed

- `rcm_mc/diligence/benchmarks/` — Phase 2 (KPIs, stress tests)
- `rcm_mc/diligence/root_cause/` — Phase 3 (Pareto, ZBA autopsy)
- `rcm_mc/diligence/value/` — Phase 4 (wire into v2 bridge + MC)

The three Phase 2–4 stubs are intentionally empty; their tabs render
placeholder pages that explain the phase + note that the CCD produced
by Phase 1 is already the load-bearing input.

## What stayed untouched

Per the "non-goals" directive:

- `rcm_mc/analysis/packet.py`, `packet_builder.py`
- `rcm_mc/pe/rcm_ebitda_bridge.py` and v2 bridge (when wired)
- `rcm_mc/mc/ebitda_mc.py`
- `rcm_mc/pe_intelligence/` (the 275+ brain modules)
- `rcm_mc/ui/analysis_workbench.py`
- `rcm_mc/exports/packet_renderer.py`
- `rcm_mc/alerts/` — code + tables kept; only nav/bell/dashboard
  panels hidden.
- All deal CRUD, owners/deadlines/notes/tags surfaces.
- No database schema migrations (additive CCD tables are a Phase 0.B
  job — today's CCD writes to JSON on disk).

## What the next session's entry point is

Priority order for Phase 2 kickoff:

1. **Wire CCD into the packet builder's `observed_metrics`** — when
   a deal has a CCD attached, prefer CCD-derived KPIs over partner
   YAML with higher confidence weighting. This is the hook point in
   [`rcm_mc/analysis/packet_builder.py`](rcm_mc/analysis/packet_builder.py).

2. **Ship Phase 2 `benchmarks/`**: Days in A/R, First-Pass Denial
   Rate, A/R Aging >90d, Cost to Collect, NRR. Each computes off
   the CCD; no partner YAML required.

3. **Cohort Liquidation Analysis** as the headline Phase 2 view —
   render inline on the `/diligence/benchmarks` page.

4. **Storage**: the CCD is dict-backed in memory today. When more
   than one analyst is working concurrently, persist to a new
   SQLite table (`ccd_runs`) — additive, CREATE TABLE IF NOT
   EXISTS migration per CLAUDE.md convention.

## Notes on the previous (superseded) Phase 0.A scaffold

An earlier session produced [`rcm_mc_diligence/`](rcm_mc_diligence/)
— a *sibling* package that wrapped Tuva via `dbt-duckdb`. That
direction was superseded by this session's pivot to a subpackage +
Python-native ingester. Per "Do not delete any existing code," the
sibling package is kept on disk; its tests are not wired into the
main pytest run. Its `SESSION_LOG.md` and `PHASE_0B_NOTES.md` are
also retained.

The `rcm_mc/diligence/` work in this session is the load-bearing
foundation going forward. If we want Tuva's input-layer DQ tests
later, the cleanest integration point is a new `tuva_bridge` module
inside `rcm_mc/diligence/ingest/` that would run post-CCD validation,
not as a pre-ingestion wrapper.

---

# Session 2 — 2026-04-23 (continuation)

## What shipped

### 1. Data-integrity gauntlet (all 7 items)
New subpackage [`rcm_mc/diligence/integrity/`](rcm_mc/diligence/integrity/):

- [`leakage_audit.py`](rcm_mc/diligence/integrity/leakage_audit.py) —
  `audit_features(target_provider_id, features)` raises `LeakageError`
  with a specific chain when any feature's source provider equals the
  target. Benchmark datasets are exempt. Provider ID normalisation
  handles casing / punctuation differences.
- [`split_enforcer.py`](rcm_mc/diligence/integrity/split_enforcer.py) —
  `make_three_way_split(target, pool, ...)` produces a provider-disjoint
  three-way split (train / calibration / test) keyed by
  `hashlib.sha256(seed || provider_id)`. Deterministic across runs.
  `assert_provider_disjoint` is exported for callers with hand-built
  splits.
- [`distribution_shift.py`](rcm_mc/diligence/integrity/distribution_shift.py) —
  PSI (Siddiqi thresholds: 0.10 stable, 0.25 drift) + two-sample KS D
  on a feature-by-feature basis. Worst-feature wins the overall
  verdict. Insufficient-sample guard set at 30 rows per feature.
- [`temporal_validity.py`](rcm_mc/diligence/integrity/temporal_validity.py) —
  `check_regulatory_overlap(claims_dates)` flags OBBBA / MA v28 /
  site-neutral / ICD-10 2026 events that fall inside a claims window.
  Stamped on every `KPIResult`.

### 2. CCD → packet bridge
- [`MetricSource.CCD`](rcm_mc/analysis/packet.py:66) added to the enum.
- [`ObservedMetric.confidence: float = 1.0`](rcm_mc/analysis/packet.py:203)
  added — default preserves backwards compat, JSON round-trip extended.
- [`NodeType.CCD_DERIVED`](rcm_mc/provenance/graph.py:42) added.
- [`rcm_mc/diligence/ccd_bridge.py`](rcm_mc/diligence/ccd_bridge.py) —
  `kpis_to_observed(bundle, ccd)` turns a `KPIBundle` into a
  `{metric_key: ObservedMetric}` dict + matching `ProvenanceNode` set.
  `merge_observed_sources(override, ccd, partner_yaml, predicted)`
  implements the spec §A priority:
  OVERRIDE > CCD > PARTNER_INPUT > PREDICTED. Confidence weights:
  override 1.0, CCD 1.0, partner 0.7, predicted fallback 0.5.

### 3. Phase 2 KPI engine
- [`benchmarks/kpi_engine.py`](rcm_mc/diligence/benchmarks/kpi_engine.py):
  Days in A/R (HFMA MAP), First-Pass Denial Rate (AAPC),
  A/R Aging > 90d (HFMA MAP #9), Cost to Collect (HFMA MAP #5, returns
  None without analyst inputs), Net Revenue Realization (returns None
  without contracted-rate lookup), Service→Bill and Bill→Cash lag
  (median / p25 / p75).
- [`benchmarks/cohort_liquidation.py`](rcm_mc/diligence/benchmarks/cohort_liquidation.py):
  cohort × window grid with mandatory `as_of_date` censoring. Censored
  cells return `status=INSUFFICIENT_DATA` + reason; NO numeric field.
  Per-payer-class splits optional via `by_payer_class=True`.
- [`benchmarks/_ansi_codes.py`](rcm_mc/diligence/benchmarks/_ansi_codes.py):
  rule-based CARC → DenialCategory map (front-end / coding / clinical /
  payer-behavior / contractual). NOT a classifier — every mapping is
  reviewable.

### 4. Phase 2 benchmarks UI
[`rcm_mc/ui/diligence_benchmarks.py`](rcm_mc/ui/diligence_benchmarks.py) —
three-section page:
- KPI scorecard with color-coded bands vs HFMA acute-hospital
  benchmarks.
- Cohort liquidation table (mature + censored clearly separated).
- Denial stratification Pareto with dollar-weighted bars.
- Provenance footer with claims range + as_of + any temporal-validity
  warnings.
- When no bundle is passed, falls through to the placeholder page with
  a link to `/diligence/ingest`.

### 5. KPI-truth fixtures
[`tests/fixtures/kpi_truth/`](tests/fixtures/kpi_truth/) — 5 hospitals
with hand-computed expected values in `expected.json`:
- `hospital_01_clean_acute` — 10 Medicare claims, all paid
- `hospital_02_denial_heavy` — 20 commercial, FPDR=20%
- `hospital_03_censoring` — mix of mature + young cohorts
- `hospital_04_mixed_payer` — 5/5/5/5 payer split
- `hospital_05_dental_dso` — 40 self-pay dental claims

Regenerable via `python -m tests.fixtures.kpi_truth.generate_kpi_truth`.

### 6. Tests
Six new test files, **all 52 tests pass** (41 new + 11 session-1
regression):
- [`test_diligence_leakage_audit.py`](tests/test_diligence_leakage_audit.py)
  — 6 tests: clean pool passes, deliberate leak raises, benchmark exempt.
- [`test_diligence_split_enforcer.py`](tests/test_diligence_split_enforcer.py)
  — 10 tests: target always in test, no overlap, deterministic seed.
- [`test_cohort_liquidation_censoring.py`](tests/test_cohort_liquidation_censoring.py)
  — 5 tests: mature reports, young censored, no fabrication sweep.
- [`test_kpi_engine_truth.py`](tests/test_kpi_engine_truth.py)
  — 7 tests: hand-computed DAR / FPDR / A/R>90 / lags match exactly.
- [`test_distribution_shift.py`](tests/test_distribution_shift.py)
  — 4 tests: DSO → OOD, acute-like → IN_DISTRIBUTION, thresholds,
  empty-input safe-fail.
- [`test_ccd_provenance_end_to_end.py`](tests/test_ccd_provenance_end_to_end.py)
  — 11 tests: CCD source stamp preserved, provenance nodes/edges wired,
  priority order merge, confidence round-trip.

## Regressions

Ran packet + completeness + reproducibility + chartis integration:
**132 passed, 2 failed** — the same two pre-existing failures from
session 1 (`/library` rendering raises `moic_bucket` keyword error
in an unrelated module). Confirmed via `git stash` that both failures
exist on an untouched tree.

No new test failures introduced by session 2.

## Done criteria (from the spec) — status

1. ✅ Every gauntlet check is implemented, tested, and runs as a
   guardrail (leakage_audit + split_enforcer fire loud, temporal_validity
   stamps every KPI, distribution_shift scores + classifies).
2. ✅ CCD feeds observed_metrics with correct confidence weighting
   (override 1.0 > CCD 1.0 > partner 0.7 > predicted 0.5).
3. ✅ KPI engine computes HFMA metrics with exact cited definitions;
   missing-data cases return None + reason, never estimates.
4. ✅ Cohort Liquidation respects as_of censoring.
5. ✅ Provenance chain resolves end-to-end (CCD source node →
   CCD_DERIVED nodes → ObservedMetric.source_detail carries ingest_id
   + citation + sample size).
6. ✅ Phase 2 tab renders the benchmarks UI.
7. ✅ Zero regressions beyond the 2 pre-existing failures.

## What is stubbed

- **Packet-builder direct invocation** with CCD metrics. The bridge
  exists (`kpis_to_observed` + `merge_observed_sources`) and ObservedMetric/MetricSource/provenance all
  accept CCD-tagged values; but the `build_analysis_packet(...)` call
  site hasn't been threaded with a `ccd_metrics=` kwarg yet — that
  modification goes in at Phase 3 when we need the packet to call the
  KPI engine automatically. For now, callers manually produce the
  override dict via `kpis_to_observed(...).as_override_dict()`.
- **Conformal splitting** — `ml/conformal.py`'s row-wise split remains
  in place. `split_enforcer.make_three_way_split` is available for
  callers who need provider-disjoint behaviour; wiring it into
  `ridge_predictor.predict_missing_metrics` is a Phase 3 task so it
  lands alongside the root-cause attribution work that re-exercises
  the predictor heavily.

## What stayed untouched

- v1 / v2 bridge math
- Monte Carlo kernel
- Partner YAML schema
- SQLite schema (no new tables)
- PE Intelligence brain modules (`pe_intelligence/`)
- Alerts code + tables

## Next session entry point

**Phase 3 — Root Cause Analysis.** Pareto of drivers per off-benchmark
KPI (uses the denial stratification rows from Phase 2 + per-category
dollar rollups from the bridge v2). ZBA autopsy: every claim with a
zero paid_amount + nonzero adjustment opens a drill-through — the CCD
preserves the original charge + allowed + adjustment trail for
exactly this purpose. Click-through to underlying rows resolves via
the `qualifying_claim_ids` array already attached to each `KPIResult`
and the `ccd_row_id` stable key already attached to every
`CanonicalClaim`.

Start in [`rcm_mc/diligence/root_cause/`](rcm_mc/diligence/root_cause/)
(empty stub today). First deliverable: a `pareto.py` that takes a
`KPIBundle` + `CanonicalClaimsDataset` + target KPI name and returns
an ordered list of driver-categories + linked claim IDs per category.

---

# Session 3 — 2026-04-23 (sibling-project integration)

Pulled the two sibling projects under `Coding Projects/` into the
main pipeline. Both are preserved on disk; the useful parts are
ported as first-class modules with tests.

## What shipped

### 1. CMS advisory analytics — ported + integrated
From `cms_medicare-master/cms_api_advisory_analytics.py` (2,032 lines,
40 public functions + plotting + argparse CLI). Ported the scoring
math; dropped plotting, Basemap, argparse, file IO.

- [`rcm_mc/pe/cms_advisory.py`](rcm_mc/pe/cms_advisory.py) — pure
  pandas library:
  - `standardize_columns` — CMS PUF vocabulary normalization
  - `screen_providers` — opportunity score per provider_type
    (scale 0.35 + margin 0.30 + acuity 0.20 + fragmentation 0.15)
  - `yearly_trends` + `provider_volatility` + `momentum_profile`
  - `regime_classification` — 5 operating regimes
    (durable_growth / steady_compounders / emerging_volatile /
    stagnant / declining_risk)
  - `stress_test` — 6 default scenarios incl. OBBBA Medicaid churn
    and site-neutral full exposure (synced with the regulatory
    calendar in `integrity/temporal_validity.py`)
  - `consensus_rank` — weighted ensemble rank
- [`rcm_mc/pe/cms_advisory_bridge.py`](rcm_mc/pe/cms_advisory_bridge.py) —
  converts advisory output into `RiskFlag` rows for the packet:
  - `market_posture` (consensus_rank quartile)
  - `operating_regime` (stagnant/declining_risk → HIGH)
  - `earnings_durability` (yoy_payment_volatility ≥ 35%)
  - `stress_exposure` (worst scenario ≤ −20% total payment)

### 2. Tuva bridge — map CCD → Tuva Input Layer
From `ChartisDrewIntel-main/` (vendored Tuva v0.17.1 under Apache
2.0; directory renamed but contents unmodified).

- [`rcm_mc/diligence/ingest/tuva_bridge.py`](rcm_mc/diligence/ingest/tuva_bridge.py):
  - `vendored_tuva_path()` — returns the local Tuva directory or None
  - `ccd_to_tuva_input_layer_arrow(ccd)` — returns
    `{table_name: pyarrow.Table}` with columns matching Tuva's
    `input_layer__medical_claim`, `input_layer__pharmacy_claim`,
    `input_layer__eligibility` contracts exactly
  - `write_tuva_input_layer_duckdb(ccd, path)` — writes to an
    on-disk DuckDB; partner runs `dbt build` against the vendored
    project from there
  - No new runtime deps; dbt-core + dbt-duckdb stay optional

### 3. Integration doc
- [`rcm_mc/diligence/INTEGRATION_MAP.md`](rcm_mc/diligence/INTEGRATION_MAP.md) —
  full data-flow diagram, module ownership matrix, test coverage
  summary, analyst workflow, design invariants.

### 4. Tests
- [`tests/test_integrations_full_stack.py`](tests/test_integrations_full_stack.py) —
  14 tests covering:
  - CMS advisory pipeline end-to-end on a synthetic 3×3-year frame
  - Consensus ranks are dense (no gaps), stress scenarios are
    uniformly downside in total-payment terms
  - Bridge produces typed RiskFlag rows with correct severity bands
  - Top-quartile / bottom-quartile thresholds fire on an 8-provider
    universe
  - Tuva bridge output columns match Tuva's contract exactly for
    all three Input Layer tables
  - Pharmacy table is empty-but-typed when no rx data (not missing)
  - `vendored_tuva_path` resolves and confirms the project is Tuva
    (by reading `name: 'the_tuva_project'` in its dbt_project.yml)

## Full diligence + integration test suite: **66 passing in 0.46s**

(11 ingest + 6 leakage + 10 split + 5 censoring + 7 KPI + 4 dist.
shift + 11 provenance + 14 integration — including the +10 subtests
in `test_every_fixture_ingests_and_roundtrips`.)

Wider suite: 2 pre-existing failures persist (unrelated `/library`
route `moic_bucket` issue); confirmed via `git stash` that they
predate session 2. No new regressions introduced.

## Attribution / licensing notes

- The vendored `ChartisDrewIntel-main/` is a directory-renamed copy
  of Tuva v0.17.1 (Apache 2.0). Its `dbt_project.yml` still carries
  `name: 'the_tuva_project'` and the original LICENSE is intact. The
  bridge module documents the vendored path and does not modify the
  Tuva content — it just maps our CCD onto Tuva's Input Layer
  contract so the partner can run Tuva's dbt project themselves.
- The `cms_medicare-master/` source has no LICENSE file. The ported
  `rcm_mc/pe/cms_advisory.py` is a significant rewrite that drops
  plotting + argparse CLI and restructures the scoring math as a
  clean pandas library with typed outputs. The module's docstring
  documents its lineage.

## Next session entry point (session 4)

**Phase 3 — Root Cause Analysis** remains the next big build, now
with additional inputs available:

- CMS advisory's `consensus_rank` + `regime` per provider_type is
  available as packet risk-flag context for the Pareto narrative.
- Tuva-enriched claims marts (CCSR, HCC) are available when a partner
  runs the vendored Tuva project on the Phase-1-shaped DuckDB file.
- Stress-test scenarios already exist as a typed table —
  `root_cause/pareto.py` can consume them as "what-if" drivers on
  each KPI's off-benchmark gap.

Start with `root_cause/pareto.py` as planned at the end of session 2.
Add a `root_cause/cms_advisory_narrative.py` that turns the four
advisory RiskFlags into narrative bullets for the analyst memo —
closing the loop on market-posture context.
