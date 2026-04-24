# Provenance

Full dependency tracking and audit trail for every number the platform produces. Each scalar is backed by a `DataPoint` that answers: what is it, where did it come from, how much do we trust it, and what fed into it?

---

## `tracker.py` — DataPoint Atomic Provenance Unit

**What it does:** Defines the `DataPoint` dataclass — the atomic unit of provenance. Every scalar value in the platform is (or can be) backed by a DataPoint that carries its full context.

**How it works:** `DataPoint` fields: `metric_key`, `value`, `source` (`MetricSource` enum), `confidence` (0.0–1.0), `upstream_keys` (list of metric keys that fed into this value), `method` (how it was computed), `timestamp`, `note` (optional human-readable context). `ProvenanceTracker` accumulates DataPoints for a single analysis run and provides `explain(metric_key)` → plain English. DataPoints are immutable once created — refinements create new DataPoints with the old ones in `upstream_keys`.

**Data in:** Created by `packet_builder.py` at each computation step; written into the `DealAnalysisPacket.provenance_snapshot`.

**Data out:** DataPoint objects consumed by `registry.py` and `explain.py`.

---

## `registry.py` — Per-Deal Provenance Collection

**What it does:** `ProvenanceRegistry` — per-deal collection of DataPoints. Persists to SQLite, exports as a JSON dependency graph, and generates plain-English explanations for any metric.

**How it works:** Stores DataPoints in the `provenance_points` SQLite table with deal_id and run_id. `register(data_point)` inserts. `get_point(metric_key)` retrieves. `export_graph()` serializes the full dependency graph as a JSON dict of nodes and edges for the `/api/analysis/<id>/provenance` endpoint. `explain(metric_key)` traverses upstream DataPoints and assembles a chain-of-custody explanation ("This value was predicted by Ridge regression from 23 comparable hospitals. The 6 most similar hospitals had a denial rate of 8.2–11.4%. Conformal interval: 7.9–13.7%.").

**Data in:** DataPoints from `tracker.py` during the packet build; deal_id and run_id for scoping.

**Data out:** JSON provenance graph for the provenance viewer; plain-English explanations for the metric popover.

---

## `graph.py` — Rich Explorable Provenance DAG

**What it does:** Rich graph type with typed edges, node categories (SOURCE / OBSERVED / PREDICTED / CALCULATED / AGGREGATED / BENCHMARK), and traversal APIs. Built on demand from a packet for UI rendering.

**How it works:** `ProvenanceGraph` class built from a `DealAnalysisPacket.provenance_snapshot` (the simplified wire format). Each node has a `NodeType` enum value and metadata. Typed edges: `INPUT_TO`, `DERIVED_FROM`, `WEIGHTED_BY`, `CALIBRATED_FROM`, `VALIDATED_AGAINST`. `upstream(metric_key)` — BFS traversal returning all ancestor nodes. `downstream(metric_key)` — BFS traversal for dependents. `has_cycle()` — DFS cycle detection (should always be False — the provenance graph is a DAG). Used by `GET /api/analysis/<id>/provenance` to serve the interactive graph viewer.

**Data in:** `DealAnalysisPacket.provenance_snapshot` (simplified wire format from `packet.py`).

**Data out:** Rich graph object for the provenance API and the interactive graph visualization.

---

## `explain.py` — Plain-English Metric Explanation Generator

**What it does:** Generates partner-readable prose and structured UI popover data for any metric in the packet. "Why is the denial rate 10.8%?" → a paragraph explaining the Ridge prediction, the comparables used, and the CI.

**How it works:** Template-driven explanation generator: each `MetricSource` type has a template (`PREDICTED` → "This {metric} was predicted by {method} using {n_comps} comparable hospitals..."; `OBSERVED` → "This {metric} was entered by {analyst} on {date}..."; `AUTO_POPULATED` → "This {metric} was sourced from CMS HCRIS data for CCN {ccn}..."). `explain_metric(metric_key, packet)` returns a plain-English string. `explain_for_ui(metric_key, packet)` returns a structured dict with `{text, source_label, confidence_label, data_points: [...]}` for the workbench metric popover.

**Data in:** `DealAnalysisPacket` metric and provenance data; `registry.py` for DataPoint context.

**Data out:** Explanation string for `GET /api/analysis/<id>/explain/<metric_key>`; structured popover dict for the workbench.

---

## Key Concepts

- **Immutable DataPoints**: Once created, a DataPoint is never modified. Refinements create new DataPoints with the old ones referenced in `upstream_keys`.
- **Two graph types**: The packet carries a simplified wire-format graph for JSON round-tripping; the rich graph is built on demand for UI traversal.
- **Partner-facing explanations**: `explain_metric` produces prose a partner can read without context; `explain_for_ui` returns structured data for popovers.
