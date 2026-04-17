# Layer: Provenance (`rcm_mc/provenance/`)

## TL;DR

Every scalar the platform shows a partner is backed by a provenance
node. Two complementary representations: (1) `DataPoint` /
`ProvenanceRegistry` — a flat per-metric audit log that persists to
SQLite, and (2) rich `ProvenanceGraph` — an explorable DAG with
typed edges rebuilt on demand for the UI. Plus a plain-English
explainer. The product's partner claim — "every number has a story"
— lives here.

## What this layer owns

- `DataPoint` — the atomic unit: value, metric_name, source,
  source_detail, confidence, as_of_date, upstream.
- `ProvenanceRegistry` — per-deal collection of DataPoints with
  convenience recorders (`record_user_input`, `record_hcris`,
  `record_regression`, ...) + SQLite persistence.
- `ProvenanceGraph` + `ProvenanceNode` + `ProvenanceEdge` — the rich
  explorable DAG built from a `DealAnalysisPacket`. (The packet's
  flat-snapshot analog is now named `ProvenanceSnapshot` to avoid
  the name collision — `ProvenanceGraph` on the packet side remains
  as a back-compat alias.)
- `build_rich_graph(packet)` — deterministic construction from
  packet → DAG.
- `explain_metric(graph, metric_key)` — plain-English narrative.
- `explain_for_ui(graph, metric_key)` — structured payload for the
  workbench tooltip.

## Files

### `tracker.py` (~170 lines)

**Purpose.** Define the atomic `DataPoint`. Every number surfaced
by the platform is wrapped in one of these.

**Key exports.**
- `Source` enum — `USER_INPUT`, `HCRIS`, `IRS990`,
  `REGRESSION_PREDICTED`, `BENCHMARK_MEDIAN`, `MONTE_CARLO_P50`,
  `CALCULATED`.
- `DataPoint` (frozen dataclass) — `value`, `metric_name`,
  `source`, `source_detail`, `confidence` ∈ [0, 1], `as_of_date`,
  `upstream: list[DataPoint]`.

**Design notes.**
- Frozen. Refining a prediction creates a new DataPoint — old one
  stays in the audit trail.
- `upstream` is the dependency tree.
- `value` is always float. Categorical metrics don't belong here.
- `as_of_date` separates "when the fact was true" from "when we
  ran the calculation." HCRIS 2022 has `as_of_date=2022-12-31`.

**Serialization.** `to_dict()` emits upstream as a list of
metric_name strings (the full DataPoints live in the Registry).
`from_dict(data, lookup)` rehydrates upstream via the lookup dict.

### `registry.py` (~555 lines)

**Purpose.** Per-deal collection of `DataPoint`s + SQLite persistence.

**Table.**
```sql
CREATE TABLE metric_provenance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    value REAL NOT NULL,
    source TEXT NOT NULL,
    source_detail TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL DEFAULT 1.0,
    as_of_date TEXT NOT NULL,
    upstream_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);
```

**Public class.** `ProvenanceRegistry(deal_id, run_id)`.

**Core API.**
- `record(dp: DataPoint) -> DataPoint`.
- `get(metric_name) -> Optional[DataPoint]`.
- `all_metrics() -> List[str]`.

**Convenience recorders** — one per `Source` enum:
- `record_user_input(value, metric_name, *, source_detail, as_of_date)`.
- `record_hcris(value, metric_name, *, ccn, fiscal_year,
  source_detail, as_of_date, confidence=0.95)`.
- `record_irs990(value, metric_name, *, ein, tax_year, ...)`.
- `record_regression(value, metric_name, *, upstream, r_squared,
  n_samples, predictor_summary)` — confidence = clamped R².
- `record_benchmark_median(value, metric_name, *, cohort_description,
  n_peers, confidence=0.8)`.
- `record_mc(value, metric_name, *, n_sims, percentile=50, stddev,
  upstream)` — confidence = `1 − CV` when stddev provided.
- `record_calc(value, metric_name, *, formula, upstream, confidence)`
  — confidence defaults to `min(upstream.confidence)` — a calculation
  is never more trustworthy than its weakest input.

**Traversal.**
- `trace(metric_name, *, max_depth=64) -> List[DataPoint]` —
  recursive upstream chain, topologically ordered, cycle-safe.
- `dependency_graph() -> dict` — flat JSON graph for the legacy API.

**Human explanation.** `human_explain(metric_name) -> str` — one-or-
two paragraph explanation using source-specific templates.

**Persistence.** `save(store, deal_id, run_id) -> int` (rows
inserted) + `classmethod load(store, deal_id, run_id=None)`.

### `graph.py` (~490 lines)

**Purpose.** Rich explorable DAG — built on demand from a
`DealAnalysisPacket`.

**Key enums.**
- `NodeType` — `SOURCE` (raw external), `OBSERVED` (user/analyst
  entered), `PREDICTED` (ridge/regression output), `CALCULATED`
  (deterministic arithmetic), `AGGREGATED` (cohort medians / target
  values), `BENCHMARK` (registry anchors).
- `EdgeRelationship` — `INPUT_TO` (default), `DERIVED_FROM`,
  `WEIGHTED_BY`, `CALIBRATED_AGAINST`. Used for UI styling (dotted
  lines for `weighted_by`, etc.).

**Key dataclasses.**
- `ProvenanceNode` — `id, label, node_type, value, unit, source,
  source_detail, confidence, timestamp, metadata`.
- `ProvenanceEdge` — `from_node, to_node, relationship`.
- `ProvenanceGraph` class — `nodes: dict`, `edges: list`. Methods:
  - `add_node(node)`, `add_edge(from, to, relationship)`.
  - `get_upstream(node_id) -> List[ProvenanceNode]` — cycle-safe
    recursive walk.
  - `get_downstream(node_id) -> List[ProvenanceNode]`.
  - `direct_parents(node_id) -> List[(Node, EdgeRelationship)]`.
  - `has_cycle() -> bool` — DFS tri-color cycle detection.
  - `topological_order() -> list[str]` — Kahn's algorithm; returns
    `[]` on cycle.
  - `to_dict()` / `to_json()`.
  - `to_packet_graph()` — flatten into
    `packet.ProvenanceGraph` + `DataNode` for persistence.

**The builder.** `build_rich_graph(packet) -> ProvenanceGraph`.
Walks observed → comparables → predicted → profile → bridge → MC
and wires up the full DAG.

**Node ID scheme** (critical for UI + API):
- `observed:<metric>` — user/analyst/CMS input.
- `source:<metric>` — raw external source node.
- `comparables:selection` — the cohort aggregate.
- `comparables:feature:<key>` — each feature fed to comparable
  selection.
- `predicted:<metric>` — ridge / median output.
- `target:<metric>` — target metric on the bridge.
- `bridge:<metric>` — per-lever EBITDA impact.
- `bridge:total` — rolled-up total.
- `mc:ebitda_p10 / p50 / p90` — MC summary bands.
- `profile:payer_mix:<payer>` — profile fields used by the bridge.
- `benchmark:<metric>:<percentile>` — registry anchors.

**Edge semantics** (abridged):
- `observed:denial_rate → bridge:denial_rate` (INPUT_TO) — lever
  reads observed value.
- `target:denial_rate → bridge:denial_rate` (INPUT_TO) — lever reads
  target.
- `observed:net_revenue → bridge:denial_rate` (WEIGHTED_BY) —
  financial input scales the lever.
- `comparables:selection → predicted:denial_rate` (DERIVED_FROM) —
  prediction came from cohort.
- `bridge:<metric> → bridge:total` (INPUT_TO) — lever impacts roll up.
- `bridge:total → mc:ebitda_pX` (DERIVED_FROM) — MC samples from
  bridge output.

### `explain.py` (~270 lines)

**Purpose.** Plain-English explainer for a metric.

**Public.**
- `explain_metric(graph, metric_key) -> str` — one-to-three sentences
  using node-type-specific templates.
- `explain_for_ui(graph, metric_key) -> dict` — structured payload:
  ```
  {
    "metric": <key>,
    "node_id": <resolved_id>,
    "value": <float>,
    "unit": <str>,
    "explanation_short": <one-line>,
    "explanation_full": <prose from explain_metric>,
    "upstream": [ {id, label, value, unit, source, relationship}, ... ],
    "method": <source>,
    "confidence": <0..1>,
    "node_type": <NodeType.value>,
    "metadata": {...}
  }
  ```

**Template dispatch.**
- `SOURCE` / `OBSERVED` — "<name> of <value> was pulled from
  <source>" or "provided directly as observed input."
- `PREDICTED` — "<name> of <value> was predicted using <method>
  (R²=<r2>) trained on <n> comparable hospitals. The prediction used
  <k> input features: <feature list>. The 90% confidence interval
  is [<low>, <high>], computed via split conformal prediction on the
  calibration set."
- `CALCULATED` — bridge-lever-specific: quotes revenue + cost split,
  margin bps, working-capital released. `bridge:total` summarizes
  EV at multiples. `mc:ebitda_*` cites n_sims.
- `AGGREGATED` / `BENCHMARK` — source-detail pass-through.

**Resolution.** `_resolve_metric_id(graph, metric_key)` tries
preference order: `observed:`, `predicted:`, `bridge:`, `target:`,
`mc:`, `comparables:`, exact match.

### `__init__.py`

Re-exports `DataPoint`, `Source`, `ProvenanceRegistry`,
`ProvenanceGraph`, `ProvenanceNode`, `ProvenanceEdge`, `NodeType`,
`EdgeRelationship`, `build_rich_graph`, `explain_metric`,
`explain_for_ui`.

## Flat vs. rich — why both?

```
┌─────────────────────────────────────┐
│  rcm_mc.provenance.graph             │
│  ProvenanceGraph (rich, typed edges) │
│                                      │
│  - Built fresh from packet every     │
│    time /api/analysis/<id>/provenance│
│    is requested.                     │
│  - Not persisted — lives in memory.  │
│  - Supports UI features (typed       │
│    relationships, cycle check,       │
│    plain-English explainer).         │
└──────────────┬──────────────────────┘
               │ .to_packet_graph() — flatten
               ▼
┌─────────────────────────────────────┐
│  rcm_mc.analysis.packet              │
│  ProvenanceSnapshot (flat, DataNode  │
│  with upstream: list[str])           │
│                                      │
│  - Stored in packet JSON.             │
│  - Survives cache reload.            │
│  - Drops typed edges but keeps       │
│    parent/child DAG.                 │
│                                      │
│  Back-compat alias:                  │
│    ProvenanceGraph = ProvenanceSnapshot│
└─────────────────────────────────────┘
```

Two classes at different granularity. The packet-side one was
renamed from `ProvenanceGraph` to `ProvenanceSnapshot` so the
distinction is crisp at the type level; the old name remains as
a back-compat alias.

Plus a third representation — `rcm_mc.provenance.registry` — which
persists per-metric DataPoints to the `metric_provenance` SQLite
table. Used by the Phase-2 simulator pipeline for its legacy
provenance trail.

## API

- `GET /api/analysis/<deal_id>/provenance` — full rich graph +
  `has_cycle` + `topological_order`.
- `GET /api/analysis/<deal_id>/provenance/<metric_key>` — subgraph
  for one metric (direct parents + full upstream chain).
- `GET /api/analysis/<deal_id>/explain/<metric_key>` — narrative +
  structured payload.
- Legacy: `GET /api/deals/<id>/provenance` + `.../<metric>` on the
  `ProvenanceRegistry` / `metric_provenance` table.

## How to add provenance for a new node type

1. Extend the node-ID prefix list in `graph.py::build_rich_graph()`.
2. Wire a dedicated `_add_*_nodes(g, packet)` helper that creates
   the nodes and edges.
3. Add a template branch in `explain.py::explain_metric` if the
   narrative needs custom wording.
4. Update tests in `tests/test_provenance_graph.py`.

## Current state

### Strong points
- **Every packet section already represented.** 26+ ontology metrics
  + observed + predicted + bridge levers + MC bands + comparables —
  all have explicit ID prefixes and edge rules.
- **Cycle detection + topological order verified by tests.** Self-
  loops, simple cycles, DAGs all tested.
- **Narrative templates quote exact numbers.** "92→97%", "$9.8M",
  "R² 0.81" — partners see the math in the explanation, not
  separate cells.
- **Two persistence paths** — flat snapshot survives packet JSON
  cache; rich graph rebuilt on demand.

### Weak points
- **No write-side UI.** Partners can't override a provenance tag
  from the workbench ("no, this came from the seller data, not from
  HCRIS"). Only the analyst-override path on reimbursement profile
  supports manual correction today.
- **`ProvenanceRegistry` (Phase-2) and `build_rich_graph` (Prompt 7)
  are parallel systems.** Phase-2 simulator uses the registry; the
  packet builder uses the rich graph. Long-term consolidation would
  pick one.
- **Narrative is template-based, not LLM-generated.** Good enough
  for tooltips; misses nuance.
