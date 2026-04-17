# End-to-End Data Flow

A step-by-step trace of one deal: "partner registers Acme Regional" →
"partner downloads the diligence memo PPTX". Shows exactly which file,
function, and SQLite table each action touches.

## Scenario

A PE associate is looking at **Acme Regional Health** — 420 beds,
midwest, 40% Medicare / 45% commercial / 15% Medicaid. They have
three metrics from the seller: denial rate 11%, days in AR 55,
cost-to-collect 4.0%. Net revenue ~$400M.

## Step 0 — Register the deal

**Action:** `rcm-mc portfolio register --deal-id acme --name "Acme Regional" ...`
or HTTP `POST /api/deals/<id>/snapshots`

**What happens:**
- `rcm_mc.portfolio.store.PortfolioStore.upsert_deal()` inserts a row
  in the `deals` table with the hospital profile JSON.
- `rcm_mc.deals.deal_sim_inputs.set_inputs()` optionally stores paths
  to YAML config files for the Phase-2 simulator (not used by the
  packet-builder path).

**Tables touched:** `deals`, optionally `deal_sim_inputs`.

## Step 1 — Trigger the analysis build

**Action:** `rcm-mc analysis acme --skip-sim` or HTTP
`GET /api/analysis/acme` or navigate to `/analysis/acme` in a browser.

**Entry point:** `rcm_mc.analysis.analysis_store.get_or_build_packet()`
- Computes `hash_inputs(deal_id, observed_metrics, scenario_id,
  as_of, profile)` with `sort_keys=True` for determinism.
- Looks in `analysis_runs` table for a row matching that hash. If
  hit, decompress and return the cached packet (same `run_id`).
- If miss, call `build_analysis_packet()` and save.

**Tables touched:** `analysis_runs`.

## Step 2 — `build_analysis_packet()` runs the 12-step pipeline

Orchestrator file: **`rcm_mc/analysis/packet_builder.py`**.

### Step 1 (load deal)
- `_load_deal_row(store, "acme")` → reads `deals.profile_json`.
- Parses to `HospitalProfile` dataclass with `bed_count=420`,
  `payer_mix={"medicare": 0.40, ...}`.

### Step 2 (observed metrics)
- Caller supplied: `{"denial_rate": 11.0, "days_in_ar": 55.0,
  "cost_to_collect": 4.0}`.
- Wrapped as `ObservedMetric(value=X, source="USER_INPUT")`.

### Step 3 (completeness)
- `rcm_mc/analysis/completeness.py::assess_completeness()` walks the
  38-metric `RCM_METRIC_REGISTRY`.
- Returns `CompletenessAssessment(coverage_pct=0.079, grade="D",
  missing_fields=[...35 entries sorted by EBITDA sensitivity...],
  quality_flags=[...])`.
- Runs six detection rules: OUT_OF_RANGE, STALE, MISSING_BREAKDOWN
  (e.g., denial_rate present but no payer-breakdown), BENCHMARK_OUTLIER,
  SUSPICIOUS_CHANGE, PAYER_MIX_INCOMPLETE.

### Step 4 (comparables)
- Partner passes `comparables_pool=[<50 peer dicts>]` or pulls from
  `hospital_benchmarks` via `rcm_mc/data/data_refresh.query_hospitals`.
- `rcm_mc/ml/comparable_finder.py::find_comparables()` scores each
  peer on 6 weighted dimensions (bed_count / region / payer_mix /
  system_affiliation / teaching / urban_rural) and returns the top
  50 with similarity scores in [0, 1].

### Step 5 (predict missing metrics)
- `rcm_mc/ml/ridge_predictor.py::predict_missing_metrics()`.
- For each missing registry metric: gate by cohort size.
  - ≥15 peers with the metric → Ridge regression + split conformal
    prediction (70/30 train-cal split). 90% CI.
  - 5-14 peers → similarity-weighted median + bootstrap CI.
  - <5 peers → benchmark P50 with P25-P75 as the band,
    `reliability_grade="D"`.
- Each prediction wrapped in a `PredictedMetric` with
  `ci_low/ci_high/method/r_squared/n_comparables_used/provenance_chain`.

### Step 6 (merge rcm_profile)
- `_merge_rcm_profile()` combines observed + predicted into one
  `dict[str, ProfileMetric]`, preferring observed.
- `_attach_ontology()` annotates each `ProfileMetric` with domain,
  financial_pathway, mechanism_tags, causal_path_summary from
  `rcm_mc/domain/econ_ontology.METRIC_ONTOLOGY`.

### Step 6b (reimbursement + realization — Prompt 2)
- `_build_reimbursement_views()` in `packet_builder.py`:
  - `rcm_mc/finance/reimbursement_engine.build_reimbursement_profile()`
    infers the hospital's method exposure from payer mix + profile
    heuristics (e.g., bed_count<25 → critical-access → COST_BASED).
  - `compute_revenue_realization_path()` decomposes `net_revenue`
    into 9 stages: gross → contractual → front-end leakage → coding
    leakage → initial denial leakage → final denial → collectible →
    timing drag → bad debt → realized cash.
  - `estimate_metric_revenue_sensitivity()` per metric, producing
    revenue / cost / working-capital split.

### Step 7 (v1 EBITDA bridge)
- `rcm_mc/pe/rcm_ebitda_bridge.py::RCMEBITDABridge.compute_bridge()`.
- Research-band-calibrated coefficients (denial_avoidable_share=0.35,
  NCR coefficient=0.60, etc.) applied uniformly across hospitals.
- Returns `EBITDABridgeResult` with per-lever `MetricImpact` rows,
  waterfall data, EV at 10x/12x/15x multiples.

### Step 7b (v2 value bridge — Prompt 3)
- `rcm_mc/pe/value_bridge_v2.py::compute_value_bridge()`.
- Reads reimbursement profile + realization path; routes each lever
  through four separate flavors: recurring revenue / recurring cost /
  one-time WC release / ongoing financing benefit.
- Key differentiator: same lever produces **different value** under
  commercial-heavy vs Medicare-heavy mixes because per-payer
  revenue-leverage table multiplies the recovery math.
- EV only applied to recurring EBITDA; one-time cash reported separately.

### Step 8 (Monte Carlo)
- `rcm_mc/mc/ebitda_mc.py::RCMMonteCarloSimulator`.
- Composes two uncertainty sources:
  1. Prediction uncertainty — conformal CI from the ridge predictor.
  2. Execution uncertainty — per-lever-family beta distribution
     (denial management beta(7,3) → 70% expected achievement,
     capitation renegotiation beta(5,5) → 50/50, etc.).
- 2,000 draws by default; returns P10/P25/P50/P75/P90 on EBITDA,
  MOIC, IRR; variance-contribution decomposition; convergence check.

### Step 9 (risk flags)
- `rcm_mc/analysis/risk_flags.py::assess_risks()`.
- Six categories: OPERATIONAL, REGULATORY, PAYER, CODING,
  DATA_QUALITY, FINANCIAL. Each flag carries title, detail,
  trigger_metrics, ebitda_at_risk (when the bridge sized it).
- OBBBA / Medicaid work-requirement logic: Medicaid > 25% fires
  HIGH with state-specific amplification for AR/GA/KY/NH/OH/UT/WI/IA/MT.

### Step 10 (provenance graph)
- `_build_provenance()` delegates to
  `rcm_mc/provenance/graph.py::build_rich_graph(packet)`.
- Rich graph has typed edges (`input_to`, `derived_from`,
  `weighted_by`, `calibrated_against`) and node categories (SOURCE,
  OBSERVED, PREDICTED, CALCULATED, AGGREGATED, BENCHMARK).
- Flattened to `packet.provenance: ProvenanceSnapshot` for JSON
  round-trip; rich graph rebuilt on demand at
  `GET /api/analysis/<id>/provenance`. (Old name `ProvenanceGraph`
  still works via back-compat alias.)

### Step 11 (diligence questions)
- `rcm_mc/analysis/diligence_questions.py::generate_diligence_questions()`.
- For each HIGH/CRITICAL risk flag: specific follow-up P0 question
  quoting the triggering number ("At 14.5% denial rate, please
  provide the root-cause breakdown...").
- Plus P0 requests for every missing metric ranked by EBITDA
  sensitivity, P0 for missing payer-specific denial rates / reason
  codes, P1 outlier drills (metrics > 2σ from cohort), and five
  always-ask standard questions.
- Dedup by (trigger_metric, priority) so one metric doesn't produce
  two questions.

### Step 12 (assemble packet)
- Final `DealAnalysisPacket(...)` construction with all 19 sections.
- `get_or_build_packet()` compresses the JSON (zlib) and writes to
  `analysis_runs.packet_json`.

## Step 3 — Render in the workbench

**Action:** Browser navigates to `/analysis/acme`.

**Entry point:** `rcm_mc.server.RCMHandler._route_analysis_workbench()`.
- Calls `get_or_build_packet(store, deal_id)` — cache hit, same
  packet loaded back.
- Calls `rcm_mc.ui.analysis_workbench.render_workbench(packet)`.

**Renderer file:** `rcm_mc/ui/analysis_workbench.py`.

Produces one full HTML document with:
- Sticky header (deal name, completeness badge, freshness indicator,
  Rebuild button, JSON/Provenance links).
- 6 tabs: Overview / RCM Profile / EBITDA Bridge / Monte Carlo /
  Risk & Diligence / Provenance.
- Bloomberg-style dark theme (`#0a0e17` bg, JetBrains Mono numbers,
  no border-radius > 4px).
- Interactive sliders on the Bridge tab that debounce 300ms and
  POST to `/api/analysis/acme/bridge` with custom targets; the
  response re-renders the waterfall client-side.

## Step 4 — Export the diligence memo

**Action:** Click "Export → PPTX" on the workbench, or CLI
`curl http://localhost/api/analysis/acme/export?format=pptx`.

**Entry point:** `server.py::_route_analysis_export()`.
- Calls `rcm_mc.exports.PacketRenderer.render_diligence_memo_pptx(packet)`.
- python-pptx if installed produces a real .pptx; otherwise a
  `.pptx.txt` fallback with the same 8-slide outline.
- Writes an audit row to `generated_exports` with `deal_id`,
  `analysis_run_id`, `format="pptx"`, `file_size_bytes`,
  `packet_hash`.
- Streams the file bytes back with `Content-Disposition: attachment`.

**Tables touched:** `generated_exports`.

## Step 5 — Portfolio LP update

**Action:** `GET /exports/lp-update?days=30`.

**What happens:**
- `server.py::_route_exports_lp_update()` lists all cached packets
  (newest first, one per deal) via
  `rcm_mc.analysis.analysis_store.list_packets()`.
- Hydrates each packet from its compressed JSON blob.
- Calls `PacketRenderer.render_lp_update_html(packets)` — one card
  per deal with name, total EBITDA opportunity, top risk flag, top
  diligence question, audit trail.
- Headline stats: deal_count, total_opportunity (sum of
  `ebitda_bridge.total_ebitda_impact`), critical_risks (sum of
  CRITICAL-severity flags).

## The full sequence at a glance

```
┌───────────────────┐  POST deals/snapshots  ┌─────────────────┐
│ partner registers │─────────────────────▶ │   deals table   │
│   Acme Regional    │                        └─────────────────┘
└───────────────────┘
        │
        │ GET /analysis/acme
        ▼
┌─────────────────────────┐   cache miss   ┌─────────────────────┐
│  get_or_build_packet()   │──────────────▶│ build_analysis_     │
│   (analysis_runs cache)  │                │ packet()            │
└──────────┬──────────────┘                │ (12-step pipeline)  │
           │ cache hit                      └──────┬──────────────┘
           │                                       │
           └────────────────────────────────┬─────┘
                                            ▼
                                 ┌────────────────────┐
                                 │  DealAnalysisPacket │
                                 │  (fully populated)  │
                                 └─┬────┬────┬────┬────┘
                                   │    │    │    │
                   ┌───────────────┘    │    │    └──────────────┐
                   │                    │    │                    │
                   ▼                    ▼    ▼                    ▼
       ┌──────────────────┐  ┌─────────────┐  ┌───────────────────┐
       │ render_workbench │  │ render_memo │  │ render_lp_update  │
       │ (Bloomberg HTML) │  │ (HTML/PPTX/ │  │ (portfolio card   │
       │                  │  │  JSON/CSV)  │  │  grid)            │
       └──────────────────┘  └─────────────┘  └───────────────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │ generated_exports    │ ← audit row
                        └──────────────────────┘
```
