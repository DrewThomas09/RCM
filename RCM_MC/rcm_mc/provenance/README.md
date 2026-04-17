# Provenance

Full dependency tracking and audit trail for every number the platform produces. Each scalar is backed by a `DataPoint` that answers: what is it, where did it come from, how much do we trust it, and what fed into it.

| File | Purpose |
|------|---------|
| `tracker.py` | `DataPoint` dataclass: the atomic unit of provenance carrying metric name, value, source, confidence, and upstream dependencies |
| `registry.py` | `ProvenanceRegistry`: per-deal collection of DataPoints; persists to SQLite, exports as JSON dependency graph, and generates plain-English explanations |
| `graph.py` | Rich explorable provenance DAG with typed edges, node categories (SOURCE/OBSERVED/PREDICTED/CALCULATED/AGGREGATED/BENCHMARK), and traversal APIs |
| `explain.py` | Plain-English explanation generator: templates node metadata into partner-readable paragraphs and structured UI popovers |

## Key Concepts

- **Immutable DataPoints**: Once created, a DataPoint is never modified. Refinements create new DataPoints; the old ones stay in the audit trail.
- **Two graph types**: The packet carries a simplified wire-format graph for JSON round-tripping; the rich graph is built on demand for UI traversal.
- **Partner-facing explanations**: `explain_metric` produces prose a partner can read without context; `explain_for_ui` returns structured data for popovers.
