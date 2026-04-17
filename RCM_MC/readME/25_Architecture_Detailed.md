# Architecture — Packet-Centric Design

## The one invariant

> Every UI page, every API endpoint, and every export renders from a
> single `DealAnalysisPacket` instance. Nothing renders independently.

If the workbench and the diligence memo disagree on a number, that's a
renderer bug — not a data bug. This is the load-bearing design
commitment that makes RCM-MC's outputs audit-defensible.

## The packet

A `DealAnalysisPacket` is a large dataclass (~15 sections) containing
everything known about one deal:

```
DealAnalysisPacket
├── profile                       — hospital identity (beds, region, payer mix)
├── observed_metrics              — partner-supplied actuals
├── completeness                  — grade + missing-fields + quality flags
├── comparables                   — peer cohort + similarity scores
├── predicted_metrics             — ridge/conformal predictions for gaps
├── rcm_profile                   — observed + predicted merged per metric
├── ebitda_bridge                 — v1 bridge result (research-band coefficients)
├── simulation                    — Monte Carlo summary (P10/P50/P90)
├── risk_flags                    — 6-category CRITICAL/HIGH/MEDIUM/LOW flags
├── provenance                    — flat DAG of every metric's origin
├── diligence_questions           — auto-generated P0/P1/P2 questions
├── reimbursement_profile         — Prompt 2: payer-method exposure
├── revenue_realization           — Prompt 2: leakage waterfall
├── metric_sensitivity_map        — Prompt 2: per-metric revenue/cost/WC split
├── value_bridge_result           — Prompt 3: unit-economics bridge (v2)
├── leverage_table                — Prompt 3: per-lever four-flavor rows
├── recurring_vs_one_time_summary — Prompt 3: aggregate split
├── enterprise_value_summary      — Prompt 3: EV delta + multiple
└── exports                       — rendered-artifact pointers
```

Full schema: [ANALYSIS_PACKET.md](ANALYSIS_PACKET.md).

## The 12-step build pipeline

`rcm_mc.analysis.packet_builder.build_analysis_packet()` walks through
12 sequential steps. Each step is wrapped so a failure in one section
does not kill the packet — that section gets `status=FAILED` with a
reason, and downstream steps continue.

```
 ┌─── 1. Load deal profile from PortfolioStore
 ├─── 2. Load observed metrics (partner input or override)
 ├─── 3. Compute completeness grade (Prompt: completeness.py)
 ├─── 4. Find comparable hospitals (ml/comparable_finder.py)
 ├─── 5. Predict missing metrics via ridge + conformal (ml/ridge_predictor.py)
 ├─── 6. Merge observed + predicted → rcm_profile
 │       └── attach economic ontology metadata per metric
 │   6b. Build reimbursement profile + realization path
 │       + metric sensitivity map (Prompt 2)
 ├─── 7. Compute EBITDA bridge v1 (pe/rcm_ebitda_bridge.py)
 │   7b. Compute value bridge v2 (pe/value_bridge_v2.py)
 ├─── 8. Run two-source Monte Carlo (mc/ebitda_mc.py) — optional
 ├─── 9. Generate risk flags (analysis/risk_flags.py)
 ├── 10. Build provenance graph (provenance/graph.py → flatten to packet)
 ├── 11. Generate diligence questions (analysis/diligence_questions.py)
 └── 12. Assemble the final packet dataclass
```

## Cross-layer dependency diagram

```
                       ┌───────────────────────────┐
                       │  rcm_mc.analysis.packet    │ ← the canonical object
                       └────────────┬──────────────┘
                                    │
                       ┌────────────▼──────────────┐
                       │  analysis.packet_builder   │ ← orchestrator
                       └────────────┬──────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
  ┌───────▼───────┐        ┌───────▼──────┐         ┌───────▼──────┐
  │   domain       │        │     ml        │         │   finance     │
  │ econ_ontology  │───▶──  │ ridge +       │──▶──    │ reimbursement │
  │ metric         │        │ conformal +   │         │ realization   │
  │ definitions    │        │ comparables   │         │ per-method    │
  └───────┬───────┘        └───────┬──────┘         └───────┬──────┘
          │                         │                         │
          └─────────────────────────┼─────────────────────────┘
                                    │
                       ┌────────────▼──────────────┐
                       │    pe.rcm_ebitda_bridge    │ ← v1 (research coefficients)
                       │    pe.value_bridge_v2      │ ← v2 (unit economics)
                       │    pe.pe_math              │ ← MOIC / IRR / EV
                       └────────────┬──────────────┘
                                    │
                       ┌────────────▼──────────────┐
                       │    mc.ebitda_mc            │ ← Monte Carlo
                       │    mc.scenario_comparison  │
                       │    mc.convergence          │
                       └────────────┬──────────────┘
                                    │
                       ┌────────────▼──────────────┐
                       │  analysis.risk_flags       │
                       │  analysis.diligence_qs     │
                       │  provenance.graph          │
                       └────────────┬──────────────┘
                                    │
             ┌──────────────────────┼──────────────────────┐
             │                      │                      │
   ┌─────────▼─────────┐  ┌────────▼────────┐  ┌──────────▼──────────┐
   │ ui.analysis_      │  │ exports.packet_ │  │  api endpoints       │
   │ workbench         │  │ renderer         │  │  (server.py)         │
   │ Bloomberg HTML    │  │ HTML / PPTX /   │  │  GET /api/analysis/  │
   │                   │  │ JSON / CSV /    │  │    <id>/...          │
   │                   │  │ DOCX            │  │                       │
   └───────────────────┘  └─────────────────┘  └──────────────────────┘
```

**Rule:** every arrow goes **down**. A layer may never import from a
layer below it circles back. This is how the whole system stays
intelligible as it grows — each layer has a single-direction contract.

## Supporting infrastructure (orthogonal to the pipeline)

```
┌─────────────────────────────┐     ┌─────────────────────────────┐
│  data/ (CMS + IRS loaders)   │     │  portfolio.store (SQLite)    │
│                              │ ──▶ │  - deals                     │
│  hospital_benchmarks feeds   │     │  - analysis_runs (cache)     │
│  the comparable pool         │     │  - mc_simulation_runs        │
└─────────────────────────────┘     │  - generated_exports         │
                                    │  - hospital_benchmarks       │
┌─────────────────────────────┐     │  - data_source_status        │
│  auth/, alerts/, deals/      │ ──▶ │  - deal_snapshots            │
│  (portfolio operations)       │     │  - ...                        │
└─────────────────────────────┘     └─────────────────────────────┘
```

## Tech stack invariants

- **Python 3.14** stdlib-heavy. Runtime deps limited to `numpy`,
  `pandas`, `matplotlib`, `yaml` — nothing else. `sklearn` is
  explicitly **not** used (we implement Ridge + conformal in numpy
  closed-form).
- **SQLite** via stdlib `sqlite3`. No Postgres path. Every table uses
  `CREATE TABLE IF NOT EXISTS` so schema migrations are idempotent.
- **HTTP** via stdlib `http.server.ThreadingHTTPServer`. No Flask /
  FastAPI.
- **Auth** via stdlib `hashlib.scrypt` + session cookies. No
  third-party identity provider.
- **Tests** via stdlib `unittest`, driven by `pytest`. 1,767+ passing.

## The 12 packet sections vs. the `section()` accessor

The packet exposes `section(name) -> Any` so API endpoints don't grow
a dispatch switch for every field:

```python
packet.section("completeness")   # returns CompletenessAssessment
packet.section("ebitda_bridge")  # returns EBITDABridgeResult
packet.section("risk_flags")     # returns list[RiskFlag]
```

Used by `GET /api/analysis/<deal_id>/section/<name>`.

## Caching strategy

Every build writes one row to `analysis_runs` with:

- `deal_id`
- `hash_inputs` — SHA256 of `(deal_id, observed_metrics, scenario_id,
  as_of, profile)` with `sort_keys=True` for determinism
- compressed JSON blob of the full packet

`get_or_build_packet()` checks the cache by `(deal_id, hash_inputs)`
before building — same inputs return the exact cached packet (same
run_id). `force_rebuild=True` bypasses the cache.

This is why the reproducibility contract works: identical inputs →
identical packet content (see `tests/test_packet_reproducibility.py`).

## Where to go next

- **To ship a new lever**: update the ontology
  ([README_LAYER_DOMAIN.md](README_LAYER_DOMAIN.md)), add the
  sensitivity coefficient table entry
  ([README_LAYER_PE.md](README_LAYER_PE.md)), add a packet-builder
  step that surfaces it.
- **To trace a specific number**: use the provenance graph
  ([README_LAYER_PROVENANCE.md](README_LAYER_PROVENANCE.md)).
  `GET /api/analysis/<deal_id>/explain/<metric_key>` gives
  plain-English.
- **To add a new export format**: extend `PacketRenderer`
  ([README_LAYER_UI_EXPORTS.md](README_LAYER_UI_EXPORTS.md)).
- **To understand what's currently weak**:
  [README_BUILD_STATUS.md](README_BUILD_STATUS.md).
