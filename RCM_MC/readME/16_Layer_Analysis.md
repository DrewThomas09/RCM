# Layer: Analysis (`rcm_mc/analysis/`)

## TL;DR

This is the spine layer. Every UI/API/export consumes a
`DealAnalysisPacket`; this package owns the dataclass, the 12-step
builder, the SQLite cache, and all the analytical-intelligence
modules that the builder consumes (completeness grading, risk flags,
diligence questions).

## What this layer owns

- The `DealAnalysisPacket` dataclass (the canonical output).
- Every internal dataclass it contains (`HospitalProfile`,
  `ObservedMetric`, `CompletenessAssessment`, `ComparableSet`,
  `PredictedMetric`, `ProfileMetric`, `EBITDABridgeResult`,
  `SimulationSummary`, `RiskFlag`, `ProvenanceGraph`,
  `DiligenceQuestion`).
- The `analysis_runs` SQLite cache table.
- The builder + completeness + risk-flag + diligence-question logic.

## Files

### `packet.py` (~1,200 lines)

**Purpose.** The canonical dataclass and every nested type it
contains. Pure data + serialization; no business logic.

**Key exports.**
- `DealAnalysisPacket` — 19 top-level fields (identity, 12 spec
  sections, 4 Prompt 2/3 additive sections, exports dict).
- Nested dataclasses:
  - `HospitalProfile`, `ObservedMetric`, `CompletenessAssessment`
    (+ `MissingField`, `StaleField`, `ConflictField`, `QualityFlag`),
    `ComparableSet` + `ComparableHospital`, `PredictedMetric`,
    `ProfileMetric`, `MetricImpact`, `EBITDABridgeResult`,
    `PercentileSet`, `SimulationSummary`, `RiskFlag`, `DataNode`,
    `ProvenanceGraph`, `DiligenceQuestion`.
- Enums: `SectionStatus` (OK/INCOMPLETE/FAILED/SKIPPED),
  `MetricSource` (OBSERVED/PREDICTED/BENCHMARK/UNKNOWN),
  `RiskSeverity` (LOW/MEDIUM/HIGH/CRITICAL),
  `DiligencePriority` (P0/P1/P2).
- `PACKET_SCHEMA_VERSION = "1.0"`.
- `SECTION_NAMES` tuple.

**Key methods.**
- `to_dict()` / `from_dict()` round-trip contract.
- `to_json(indent=2)` — NaN/Inf coerced to null per JSON spec.
- `from_json(s)` — classmethod.
- `section(name)` — polymorphic accessor used by
  `/api/analysis/<id>/section/<name>`.
- `hash_inputs(...)` — deterministic SHA256 used by the cache.

**Back-compat rules.** Every new field is added **additively** with a
sensible default. `ProfileMetric`, `RiskFlag`, `DiligenceQuestion`,
`EBITDABridgeResult`, `MetricImpact`, `CompletenessAssessment`, and
`DealAnalysisPacket` have all been extended this way without breaking
roundtrip tests.

### `packet_builder.py` (~950 lines)

**Purpose.** The 12-step orchestrator. Reads inputs, runs every
upstream layer, produces a fully-populated packet.

**Public surface.** `build_analysis_packet(store, deal_id, *,
scenario_id, as_of, skip_simulation, observed_override,
profile_override, comparables_pool, target_metrics, financials,
historical_values, conflict_sources) -> DealAnalysisPacket`.

**Private helpers (one per step).**
- `_load_deal_row(store, deal_id)` — reads `deals.profile_json`.
- `_build_profile(deal_row, override)` — constructs `HospitalProfile`.
- `_build_observed(override, deal_row)` — coerces partner inputs into
  `ObservedMetric`.
- `_build_completeness(...)` — delegates to `assess_completeness()`.
- `_build_comparables(profile, pool)` — calls
  `ml.comparable_finder.find_comparables`.
- `_build_predictions(observed, profile, comparables)` — calls
  `ml.ridge_predictor.predict_missing_metrics`.
- `_merge_rcm_profile(observed, predicted, peers)` — combines +
  attaches ontology + percentile scoring.
- `_attach_ontology(merged)` — per-metric domain / pathway / tags /
  causal summary.
- `_build_reimbursement_views(profile, rcm_profile, financials)` —
  Prompt 2: profile + realization path + sensitivity map.
- `_build_bridge(...)` — v1 bridge via `RCMEBITDABridge`.
- `_build_value_bridge_v2(...)` — Prompt 3: unit-economics bridge.
- `_build_rcm_monte_carlo(...)` — two-source MC (optional).
- `_build_simulation(...)` — legacy YAML-based simulator (fallback).
- `_build_risk_flags(...)` — delegates to `risk_flags.assess_risks`.
- `_build_provenance(...)` — rich graph → flattened packet form.
- `_build_diligence_questions(...)` — delegates to
  `diligence_questions.generate_diligence_questions`.

**Error handling contract.** Every step is wrapped so a failure in
any single section does NOT kill the packet. That section gets
`status=FAILED` with a reason string; downstream steps continue. The
partner still sees everything that *did* succeed.

### `analysis_store.py` (~220 lines)

**Purpose.** SQLite cache for `DealAnalysisPacket`.

**Table.**
```sql
CREATE TABLE analysis_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT NOT NULL,
    scenario_id TEXT,
    as_of TEXT,
    model_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    packet_json BLOB NOT NULL,     -- zlib-compressed JSON
    hash_inputs TEXT NOT NULL,     -- SHA256 for dedup
    run_id TEXT NOT NULL,
    notes TEXT
);
CREATE INDEX idx_analysis_runs_hash ON analysis_runs(deal_id, hash_inputs);
```

**Public surface.**
- `get_or_build_packet(store, deal_id, *, scenario_id, as_of,
  force_rebuild, **builder_kwargs) -> DealAnalysisPacket` — cache
  lookup then build. The entry point every UI/API uses.
- `save_packet(store, packet, *, inputs_hash, notes=None)`.
- `load_latest_packet(store, deal_id, *, scenario_id, as_of)`.
- `load_packet_by_id(store, row_id)`.
- `find_cached_packet(store, deal_id, inputs_hash)`.
- `list_packets(store, deal_id=None)` — metadata only.

**Append-only semantics.** Reruns don't overwrite — partners need to
go back to a prior analysis ("what did we think on Feb 3?"). Cache
hits return the *latest* matching row by (deal_id, hash_inputs).

### `completeness.py` (~610 lines)

**Purpose.** First-question answerer: *what do we know, what's
missing, can we trust it?*

**Key export.**
- `RCM_METRIC_REGISTRY: dict` — 38 canonical RCM + PE-financial
  metrics with display_name, category, unit, hfma_map_key flag,
  required_for_bridge flag, EBITDA sensitivity rank (1-38), benchmark
  percentiles (P25/P50/P75/P90) from HFMA/Kodiak/Crowe consensus,
  valid_range, warn_threshold, stale_after_days, breakdown_of parent
  pointer for denial categorical splits.

**Public functions.**
- `assess_completeness(observed_metrics, profile, *, as_of,
  historical_values, conflict_sources) -> CompletenessAssessment`.
- `metric_keys()` — sorted by EBITDA sensitivity rank.
- `hfma_map_key_metrics()` — subset flagged as MAP Keys.
- `metric_display_name(key)`.

**Six detection rules.**
1. **OUT_OF_RANGE** — value outside `valid_range`. Always HIGH.
2. **STALE** — observed_date older than the metric's
   `stale_after_days` threshold (90-180 days typical).
3. **MISSING_BREAKDOWN** — parent metric present (e.g., `denial_rate`)
   but no children (`denial_rate_medicare_advantage`, etc.).
4. **BENCHMARK_OUTLIER** — value > 2σ from benchmark P50 using
   IQR ÷ 1.35 as σ proxy.
5. **SUSPICIOUS_CHANGE** — >20% MoM change in `historical_values`.
6. **PAYER_MIX_INCOMPLETE** — payer-mix shares don't sum to 95-105%.

**Grading.**
- A = ≥90% coverage AND no HIGH-severity flags.
- B = ≥75%.
- C = ≥50%.
- D = <50%.

### `risk_flags.py` (~430 lines)

**Purpose.** Automated risk detection.

**Six categories** (enum values — not lowercase strings):
`OPERATIONAL`, `REGULATORY`, `PAYER`, `CODING`, `DATA_QUALITY`,
`FINANCIAL`.

**Four severities.** `CRITICAL` > `HIGH` > `MEDIUM` > `LOW`.

**Public function.** `assess_risks(profile, rcm_profile, comparables,
ebitda_bridge, *, completeness) -> list[RiskFlag]` — sorted
severity-first.

**Detection rules (abridged).**
- `denial_rate > 10%` → OPERATIONAL / CRITICAL (or HIGH if <12%).
- `ar_over_90_pct > 20%` → OPERATIONAL / HIGH.
- `clean_claim_rate < 90%` → OPERATIONAL / HIGH.
- `dnfb_days > 7`, `charge_lag_days > 5` → OPERATIONAL / MEDIUM.
- `payer_mix_medicaid > 25%` → REGULATORY / HIGH (OBBBA). Amplified
  detail for states with active Medicaid work-requirement waivers
  (AR, GA, KY, NH, OH, UT, WI, IA, MT).
- `payer_mix_medicare > 55%` → REGULATORY / MEDIUM (sequestration).
- Any payer > 30% of revenue → PAYER / HIGH (concentration).
- `commercial_pct < 25%` → PAYER / MEDIUM.
- `denial_rate_medicare_advantage > 15%` → PAYER / HIGH.
- `case_mix_index < comparable P25` → CODING / HIGH (undercoding).
- `coding_accuracy_rate < 95%` → CODING / MEDIUM.
- Completeness grade D → DATA_QUALITY / CRITICAL.
- Stale metrics → DATA_QUALITY / MEDIUM.
- `ebitda_margin < 5%` → FINANCIAL / HIGH.
- `current_ebitda < 0` → FINANCIAL / CRITICAL.

**Output enrichment.** Each flag carries `ebitda_at_risk` pulled from
the bridge's matching lever impact when one exists — so the card in
the UI shows "$9.8M at risk" not just a qualitative flag.

### `diligence_questions.py` (~580 lines)

**Purpose.** Auto-generate the diligence questionnaire, sorted by
priority with trigger-quoting question bodies.

**Public function.** `generate_diligence_questions(profile,
rcm_profile, risk_flags, completeness, comparables) ->
list[DiligenceQuestion]`.

**Generation pipeline.**
1. **Per risk flag** (HIGH/CRITICAL) — call `_flag_question()` which
   emits a specific follow-up quoting the triggering number. Example:
   a 14.5% denial-rate flag produces "At 14.5% denial rate, please
   provide the root-cause breakdown (eligibility, authorization,
   coding, medical necessity, timely filing). What denial-management
   initiatives are currently in place? Has an external denial audit
   been conducted in the last 24 months?" Six category-specific
   templates; generic fallback for anything else.
2. **Top-5 missing metrics** by EBITDA sensitivity → P0 data
   request, e.g., "Please provide Cost to Collect data for the last
   36 months. This metric has the #5 highest impact on EBITDA
   valuation among RCM KPIs."
3. **Payer-breakdown gaps** — `denial_rate` observed without
   children → P0 request for payer-specific denial rates.
4. **Reason-code gaps** — `denial_rate` observed without any of the
   5 categorical denial_rate_* children → P0 CARC/RARC request.
5. **Benchmark outliers** (>2σ from cohort mean) → P1 explanation
   request citing the exact σ.
6. **Five always-ask P1/P2 questions** — payer contract
   renegotiations, EHR transition, CDI program, CDM review, IT
   contract portfolio.

**Dedup.** Keyed on `(trigger_metric, priority)` so a metric that's
both missing and flagged produces one question — the flag version
(which quotes the value) wins.

### `__init__.py`

Re-exports every dataclass + enum + builder function. Tests import
from here rather than the internal modules.

### Legacy sub-modules (existed before packet-centric refactor)

- `anomaly_detection.py` — config anomaly flagging (used by Phase 2
  simulator path).
- `challenge.py` — reverse EBITDA solver.
- `cohorts.py` — deal cohort grouping.
- `compare_runs.py` — side-by-side run compare.
- `pressure_test.py` — management-plan achievability.
- `stress.py` — parameter-shock stress suite.
- `surrogate.py` — stub for future ML surrogate.

## How it fits the system

```
                    ┌────────────────────────────────┐
                    │ rcm_mc.analysis.packet         │
                    │  DealAnalysisPacket dataclass  │
                    └──────────────┬─────────────────┘
                                   │
                    ┌──────────────▼─────────────────┐
                    │ rcm_mc.analysis.packet_builder │
                    │  12-step orchestrator          │
                    └──────────────┬─────────────────┘
        calls into                 │           writes to
        ┌─────────────────┬────────┴─────────┬─────────────────┐
        ▼                 ▼                   ▼                 ▼
┌────────────────┐  ┌──────────┐  ┌─────────────────┐  ┌──────────────┐
│ completeness   │  │ ml       │  │ pe              │  │ analysis_    │
│ risk_flags     │  │ ridge +  │  │ bridge v1 + v2  │  │ store        │
│ diligence_qs   │  │ comps    │  │ mc simulator    │  │ (cache)      │
└────────────────┘  └──────────┘  └─────────────────┘  └──────────────┘
        ▲
        │ consumed by
        │
   ┌────┴──────────────────────────┐
   │ ui.analysis_workbench          │
   │ exports.packet_renderer        │
   │ server.py  (API endpoints)     │
   └────────────────────────────────┘
```

## Current state

### Strong points
- Packet roundtrips (to_dict → from_dict → to_json → from_json)
  covered by a strict reproducibility test.
- Every section has independent status/reason so a failure in one
  doesn't kill the packet.
- SQLite cache keyed on deterministic SHA256 means same inputs →
  same run_id → same displayed numbers.
- 65 packet tests + 36 completeness tests + 31 risk/diligence tests.

### Weak points
- **No packet invalidation cascade.** If the `METRIC_ONTOLOGY` or
  `RCM_METRIC_REGISTRY` schema changes, old cached packets may still
  load even though their metadata shape is outdated. `model_version`
  bump is the manual workaround; no automated migration.
- **`packet.provenance` is a simplified snapshot.** The rich typed
  graph is rebuilt on demand at the API layer; callers who want
  typed edges from a cold-loaded packet need an explicit
  `build_rich_graph(packet)` call.
- **Legacy tests can still import the old names.** The
  `ReimbursementProfile` → `MetricReimbursementSensitivity` and
  `ProvenanceGraph` → `ProvenanceSnapshot` renames kept back-compat
  aliases; eventually those should be removed once every test +
  caller is migrated.
