# docs/

Reference documents that don't belong in the numbered user guide (`readME/`) — canonical specs, the PE heuristics rulebook, and domain deep-dives.

**First time here?** Start with the repo-root **[README.md](../../README.md)** for a plain-English explanation of what the tool does, or **[WALKTHROUGH.md](../../WALKTHROUGH.md)** for a case study.

**Main documentation index**: [readME/README.md](../readME/README.md)

**New-module READMEs** (cycle-shipped diligence surfaces):
- [HCRIS X-Ray](../rcm_mc/diligence/hcris_xray/README.md)
- [Regulatory Calendar](../rcm_mc/diligence/regulatory_calendar/README.md)
- [Covenant Stress Lab](../rcm_mc/diligence/covenant_lab/README.md)
- [Bridge Auto-Auditor](../rcm_mc/diligence/bridge_audit/README.md)
- [Bear Case Auto-Generator](../rcm_mc/diligence/bear_case/README.md)
- [Payer Mix Stress](../rcm_mc/diligence/payer_stress/README.md)
- [Thesis Pipeline](../rcm_mc/diligence/thesis_pipeline/README.md)

---

| File | What it is |
|------|-----------|
| [ANALYSIS_PACKET.md](ANALYSIS_PACKET.md) | Canonical spec for the `DealAnalysisPacket` dataclass — every field, its type, and what builds it |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture deep-dive: layer diagram, dependency rules, design decisions |
| [BENCHMARK_SOURCES.md](BENCHMARK_SOURCES.md) | Data source reference — CMS HCRIS, Care Compare, Utilization, IRS 990, SEC EDGAR field-by-field |
| [METRIC_PROVENANCE.md](METRIC_PROVENANCE.md) | How each metric traces back to its source, with confidence tiers |
| [MODEL_IMPROVEMENT.md](MODEL_IMPROVEMENT.md) | Known model limitations and the improvement roadmap (Tier 1–3) |
| [PE_HEURISTICS.md](PE_HEURISTICS.md) | PE partner rule catalog: 275+ named heuristics, failure patterns, and thesis-trap detectors used by the `pe_intelligence/` brain |
