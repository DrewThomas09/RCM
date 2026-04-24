# docs/

Reference documents that don't belong in the numbered user guide (`readME/`) — canonical specs, the PE heuristics rulebook, and domain deep-dives.

**For the main documentation index, start here: [readME/README.md](../readME/README.md)**

---

| File | What it is |
|------|-----------|
| [ANALYSIS_PACKET.md](ANALYSIS_PACKET.md) | Canonical spec for the `DealAnalysisPacket` dataclass — every field, its type, and what builds it |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture deep-dive: layer diagram, dependency rules, design decisions |
| [BENCHMARK_SOURCES.md](BENCHMARK_SOURCES.md) | Data source reference — CMS HCRIS, Care Compare, Utilization, IRS 990, SEC EDGAR field-by-field |
| [METRIC_PROVENANCE.md](METRIC_PROVENANCE.md) | How each metric traces back to its source, with confidence tiers |
| [MODEL_IMPROVEMENT.md](MODEL_IMPROVEMENT.md) | Known model limitations and the improvement roadmap (Tier 1–3) |
| [PE_HEURISTICS.md](PE_HEURISTICS.md) | PE partner rule catalog: 275+ named heuristics, failure patterns, and thesis-trap detectors used by the `pe_intelligence/` brain |
