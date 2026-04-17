# Build Status + Roadmap

The working document for "what's production-grade today, what's
weakly calibrated, and what to build next." Updated at the end of
each major build prompt; paired with the per-layer "Weak points"
sections which go deeper on each subsystem.

## Headline state

- **Test suite**: 1,776 passing (the pre-existing lookup filesystem
  artifact was resolved; its 9 tests are now green).
- **Resolved flags**: (1) lookup filesystem artifact fixed via `mv`;
  (2) `ReimbursementProfile` name collision resolved by renaming
  the `domain` version to `MetricReimbursementSensitivity` with
  back-compat alias; (3) `ProvenanceGraph` name collision resolved
  by renaming the `packet` version to `ProvenanceSnapshot` with
  back-compat alias; (4) v1 EBITDA bridge explicitly marked
  deprecated in-module.
- **Production-grade core**: packet construction, caching, JSON
  roundtrip, CMS data ingestion, ridge + conformal prediction,
  two-source Monte Carlo, Bloomberg workbench, packet-driven
  exports.
- **Active build area**: economic realism — Prompt 1 added the
  ontology, Prompt 2 added the reimbursement engine, Prompt 3 added
  the v2 value bridge. Prompt 4 should add Monte Carlo over the v2
  bridge + cross-lever dependency modeling.

## Layer-by-layer scorecard

| Layer | State | Confidence | Next action |
|---|---|---|---|
| Data ingestion (CMS + IRS) | Ships | High | Automate HCRIS refresh end-to-end |
| Domain / ontology | Ships | High | Add metric versioning |
| Reimbursement engine | Ships | Medium | Analyst-override UI for method distributions |
| Analysis spine (packet + builder) | Ships | High | Cached-packet invalidation on ontology change |
| Completeness + registry | Ships | High | — |
| Risk flags + diligence questions | Ships | High | Expand regulatory taxonomy beyond OBBBA |
| Ridge + conformal predictor | Ships | High | Cross-validated cohort sizing |
| v1 EBITDA bridge (research-band) | Ships | Medium | Deprecate after v2 validated |
| v2 value bridge (unit economics) | Ships | Medium | Cross-lever dependency DAG |
| pe_math (MOIC / IRR / grids) | Ships | High | — |
| Monte Carlo (two-source) | Ships | Medium | Vectorize inner loop; add exit-multiple distribution |
| Scenario comparison | Ships | High | UI surface |
| Provenance (flat + rich + explain) | Ships | High | Write-side UI for analyst override |
| UI — Bloomberg workbench | Ships | High | Scenario overlay tab |
| Exports — packet renderer | Ships | High | Real python-docx / python-pptx in pyproject |
| Server / routes | Ships | High | Structured per-request logging |
| CLI dispatcher | Ships | High | — |
| Auth + audit | Ships | High | Session persistence across restart |
| Alerts + deals workflow | Ships | High | — |
| Portfolio snapshots + LP update | Ships | High | Scheduled email delivery |
| Infra (rate limit, consistency) | Ships | High | Foreign-key enforcement |

## What's been built — chronological

### Phase 1–3 (pre-packet-centric)
- Monte Carlo simulator (`core/simulator.py`) for denial/claim-level
  modeling.
- Phase-2 PE math (`pe_math.py` original) for MOIC / IRR / hold grids.
- Portfolio ops (alerts / cohorts / owners / deadlines / notes /
  variance / LP update).
- HTML reports + narrative generation.

### Phase 4 — packet-centric refactor (this session's work)

| # | Prompt summary | Delivered |
|---|---|---|
| 1 | Deal Analysis Packet spine | `analysis/packet.py`, `analysis/packet_builder.py`, `analysis/analysis_store.py` cache, `/api/analysis/<id>` endpoints |
| 2 | Completeness assessment | 38-metric `RCM_METRIC_REGISTRY`, 6 quality-flag rules, A/B/C/D grade |
| 3 | CMS data sources | `cms_hcris`, `cms_care_compare`, `cms_utilization`, `irs990_loader`, `data_refresh` orchestrator, `hospital_benchmarks` table |
| 4 | Ridge + conformal predictor | `ml/ridge_predictor.py`, `ml/conformal.py`, `ml/backtester.py` with coverage verification |
| 5 | RCM EBITDA bridge (v1) | `pe/rcm_ebitda_bridge.py` with 7 levers calibrated to research band |
| 6 | Two-source Monte Carlo | `mc/ebitda_mc.py`, scenario comparison, convergence check, `mc_simulation_runs` table |
| 7 | Risk flags + diligence questions | `analysis/risk_flags.py` with 6 categories incl. OBBBA, `analysis/diligence_questions.py` with trigger-quoting questions |
| 8 | Provenance graph + explain | `provenance/graph.py` rich DAG, `provenance/explain.py`, rebuilt-on-demand API endpoints |
| 9 | Bloomberg workbench | `ui/analysis_workbench.py` single-file renderer with 6 tabs + interactive sliders |
| 10 | Packet-driven exports | `exports/packet_renderer.py` with HTML/PPTX/JSON/CSV/DOCX + `generated_exports` audit |
| 11 | Hardening pass | Consistency check, refresh rate limiter, 29 end-to-end tests, this doc tree |
| 12 | Economic ontology | `domain/econ_ontology.py` 26-metric registry + causal graph |
| 13 | Reimbursement engine | `finance/reimbursement_engine.py` 8-archetype + 6-payer-class + realization path |
| 14 | Value bridge v2 | `pe/value_bridge_v2.py` unit-economics bridge with reimbursement-aware lever math |
| 15 | Cross-lever dependency DAG | `pe/lever_dependency.py` — topological walk, magnitude-hint overlap, audit rows |
| 16 | Monte Carlo over v2 bridge | `mc/v2_monte_carlo.py` — collection / overturn / payer-leverage / exit-multiple sampling |
| 17 | Per-lever ramp curves | `pe/ramp_curves.py` — S-curve by family, `evaluation_month` on `BridgeAssumptions` |
| 18 | Analyst override surface | `analysis/deal_overrides.py` — SQLite-backed, CLI + PUT/DELETE API, provenance tagged |
| 19 | Vectorized MC inner loop | `compute_bridge_vectorized`, `compute_value_bridge_vectorized`, 100K sims in <1s |
| 20 | Scenarios tab in workbench | 7th tab — side-by-side cards, pairwise win matrix, overlay SVG, add-scenario form |
| 21 | Infra hardening pass | FK enforcement, schema-version cache gate, session cleanup, structured JSON access log |

## Strong points (what's genuinely production-grade)

### 1. The packet invariant holds
Every UI / API / export renders from the same packet. Tests assert
this (e.g., memo and workbench share dollar figures on the same
fixture). Partners who cite a number in IC can rebuild the packet
next quarter and get the same number — reproducibility is enforced
by the deterministic `hash_inputs` cache.

### 2. Dependency surface stays tight
Zero runtime deps beyond numpy + pandas + matplotlib + yaml. No
sklearn (Ridge + conformal implemented in numpy closed-form). No
Flask / FastAPI (stdlib HTTP server). Optional: python-pptx,
python-docx (graceful fallback when absent). This matters for
deploy footprint and audit-surface simplicity.

### 3. Provenance is everywhere
Every metric has a source and a confidence. Every bridge dollar
amount has upstream refs. Every export footer prints the packet
hash + run_id. Partners can answer "where did this number come
from?" by clicking, or by tracing through `generated_exports` ×
`analysis_runs`.

### 4. Graceful failure semantics
The builder wraps each step — a failure in one section doesn't kill
the packet, it marks that section `FAILED` with a reason. Optional
deps fall back to partner-usable alternatives (e.g., `.md` instead
of `.docx`). Startup consistency check reports orphans without
raising.

### 5. Two-source Monte Carlo with verified calibration
Prediction uncertainty (conformal CIs) × execution uncertainty
(beta per lever family). On 1,000 simulated held-out samples the
90% interval covers 85-96% of truth — empirically tight. Variance
decomposition sums to 1.0 by construction.

### 6. Economic structure is explicit
Every reimbursement-method sensitivity is hand-written in
`METHOD_SENSITIVITY_TABLE`. Every payer class has a default method
distribution tagged `inferred_from_profile`. Per-payer revenue
leverage table is auditable. No black-box coefficients.

## Weak points (per-layer, roll-up)

### Economic realism
- **Per-payer revenue leverage** (`_PAYER_REVENUE_LEVERAGE`) is
  industry-folklore; real commercial contracts vary ±30% by market.
- **Appeal-recovery rate** is a single scalar (0.39). Real rates
  vary by payer × denial category.
- **Rework cost / FTE cost** single scalars across all hospital types.
- **No cross-lever dependency modeling.** `clean_claim_rate` and
  `initial_denial_rate` run independently despite being causally
  linked — potential revenue-recovery double count.
- **Implementation ramp is single scalar.** Real ramps differ per
  lever family.
- **Medicaid MCO detail** collapses into `MANAGED_GOVERNMENT`.
- **No HCC risk-adjustment path** under capitation.

### ML
- **Feature importances** are |z-scored coefficients|, not SHAP.
- **Cohort size is static**, not cross-validated against prediction
  quality.
- **No temporal structure** — cross-sectional only.
- **Conformal assumes exchangeability** — no detection when the
  target hospital is fundamentally different from cohort.

### Monte Carlo
- **Python inner loop.** 10K sims × 7 levers × bridge call is
  CPU-bound (~10 sec).
- **Independent execution draws.** No "CDI failure correlates with
  denial failure" structure.
- **No assumption uncertainty.** `collection_realization`,
  `denial_overturn_rate`, exit multiple are point estimates.

### Infra
- **In-memory job queue.** Lost on restart.
- ~~Sessions don't survive server restart.~~ **Resolved (Prompt 21).**
  Sessions already lived in SQLite; hygiene helper now runs on boot
  + every 100 requests.
- ~~No foreign-key enforcement.~~ **Resolved (Prompt 21).**
  `PRAGMA foreign_keys=ON` on every connection; FK constraints on
  `deal_overrides` / `analysis_runs` / `mc_simulation_runs` /
  `generated_exports`.
- ~~Lookup filesystem artifact.~~ **Resolved (Prompt 14 flag fix).**
- ~~Per-process CSRF secret invalidates tokens on restart.~~ Still
  true — sessions survive but form tokens don't; partners have to
  refresh the tab after a server bounce.

### Exports / UI
- **No .xlsx export.** CSV covers the data case but partners
  sometimes want Excel formatting.
- **PPTX fallback is a flat outline**, not slide-shaped.
- **python-docx / python-pptx are optional**, not in pyproject.
- **Workbench is single-file HTML.** Complex interactions (live
  data, scenarios) would need a framework.

## Next-up priorities (tiered)

### Tier 1 — economic realism
1. **Cross-lever dependency DAG in v2 bridge.** Use
   `domain.econ_ontology.causal_graph()` as the topology; walk
   levers in topological order; each lever adjusts the "remaining
   leakage" the next lever operates on. Eliminates double counting.
2. **Monte Carlo over v2 bridge.** Parallel path to the existing
   `mc.ebitda_mc`. New dimensions: collection_realization,
   denial_overturn_rate, per-payer revenue leverage, exit multiple.
   `V2MonteCarloResult` with separate recurring-EBITDA vs. one-time-
   cash distributions; EV percentiles never leak WC release.
3. **Per-lever implementation ramp curves.** Move
   `BridgeAssumptions.implementation_ramp` from a scalar to a
   `dict[lever_family, ramp_curve]` so denial mgmt ramps in 3-6 mo
   and payer renegotiation in 6-18 mo.
4. **Analyst override surface** (CLI + API) for method distributions
   + contractual discounts + per-payer leverage. The engine already
   accepts overrides via `optional_contract_inputs`; need to
   expose + persist per deal.

### Tier 2 — product polish
5. **Scenario overlay tab in the workbench.** UI surface for
   `mc.scenario_comparison.compare_scenarios()`. Uses existing API.
6. **Scheduled LP update delivery.** Wire
   `PacketRenderer.render_lp_update_html` to an opt-in cron +
   email.
7. **Structured per-request logging in `server.py`.** request_id
   threading, response-time histogram, correlation with
   audit_events.
8. **Retire back-compat aliases** for `ReimbursementProfile` (in
   `domain`) and `ProvenanceGraph` (in `analysis.packet`) once all
   internal callers migrate to the new names.

### Tier 3 — deep infrastructure
9. **Vectorize the MC inner loop.** Rewrite
   `RCMMonteCarloSimulator.run()` to build an `(n_sims, n_levers)`
   ndarray of sampled final_values and call a vectorized bridge
   function once. Target: 100K sims in <5s.
10. **Cached-packet invalidation on ontology change.** When
    `PACKET_SCHEMA_VERSION` bumps or `METRIC_ONTOLOGY` drops a
    metric, invalidate `analysis_runs` rows that reference the
    changed schema.
11. **Foreign-key enforcement.** `PRAGMA foreign_keys=ON` on the
    store connection + CASCADE rules per table.
12. **xlsx export.** Optional openpyxl dep; same fallback pattern
    as docx/pptx.

## How to contribute

The codebase discipline (summarized in `CLAUDE.md`):

1. **No new runtime dependencies** without discussion.
2. **Parameterized SQL only** — never f-string values into SQL.
3. **`BEGIN IMMEDIATE`** around check-then-write sequences.
4. **`html.escape()` every user string** before rendering.
5. **`_clamp_int` every integer query param** — never unchecked
   `int(qs[...])`.
6. **Tests before ship.** Each new feature gets a `test_<feature>.py`
   file; bug fixes get `test_bug_fixes_b<N>.py` with a regression
   assertion.
7. **No mocks of our own code** — exercise the real path.
   `unittest.mock` acceptable only for external stubs.
8. **Order-independent tests.** Class-level state reset in
   `setUp`/`tearDown`.
9. **Docstrings explain *why*, not *what*.** The code says what; the
   docstring explains the constraint or the prior incident that
   drove the decision.
10. **Additive dataclass changes only.** Every new field gets a
    sensible default so old packets still round-trip.

## Where to start reading (for a new contributor)

1. [README_INDEX.md](README_INDEX.md) — this tree.
2. [README_GLOSSARY.md](README_GLOSSARY.md) — terms first.
3. [README_ARCHITECTURE.md](README_ARCHITECTURE.md) — mental model.
4. [README_DATA_FLOW.md](README_DATA_FLOW.md) — end-to-end trace.
5. [ANALYSIS_PACKET.md](ANALYSIS_PACKET.md) — the schema.
6. Pick a layer: [analysis](README_LAYER_ANALYSIS.md) if you're
   touching the builder, [PE](README_LAYER_PE.md) if you're touching
   bridges, [ML](README_LAYER_ML.md) if you're touching prediction,
   [MC](README_LAYER_MC.md) if you're touching simulation.
7. Run the adjacent test file to see the contract. Add / modify a
   test before changing code.
