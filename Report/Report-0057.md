# Report 0057: Schema Inventory — `DealAnalysisPacket` (analysis/packet.py)

## Scope

The load-bearing dataclass per CLAUDE.md. 1,283 lines per Report 0004. 30+ symbols re-exported via `analysis/__init__.py:3-32` (Report 0004).

## Findings

### Top-level dataclass: `DealAnalysisPacket`

Per Report 0004 the `__init__.py` re-exports the following 30 symbols (via `from .packet import (...)` at lines 3-32):

```
DealAnalysisPacket           ← top-level packet
HospitalProfile              ← target hospital data
ObservedMetric               ← observed values
CompletenessAssessment       ← completeness
MissingField, StaleField, ConflictField, QualityFlag  ← data-quality flags
ComparableSet, ComparableHospital ← comparable peers
PredictedMetric, ProfileMetric, MetricImpact ← predictions
EBITDABridgeResult           ← EBITDA bridge
PercentileSet, SimulationSummary ← MC results
RiskFlag, RiskSeverity (Enum)  ← risk register
DataNode, ProvenanceGraph (alias), ProvenanceSnapshot ← provenance
DiligenceQuestion, DiligencePriority ← diligence questions
SectionStatus                ← section status enum
MetricSource (Enum)          ← provenance source
PACKET_SCHEMA_VERSION        ← const
SECTION_NAMES                ← const tuple
hash_inputs                  ← function
```

**~24 dataclasses + 5 enums + 1 type alias + 2 constants + 1 function.** The DealAnalysisPacket itself is the top container holding all the other dataclasses as fields.

### Field-by-field for `DealAnalysisPacket`

Not yet enumerated end-to-end (would require reading 1,283 lines). Per Report 0020 + 0008, the packet contains at minimum:

| Field | Type | Purpose |
|---|---|---|
| `deal_id` | str | The canonical deal identifier |
| `hospital` | HospitalProfile | Target hospital |
| `rcm_profile` | Dict[str, ProfileMetric] | RCM metric values |
| `comparables` | ComparableSet | Peer hospitals |
| `predicted_metrics` | List[PredictedMetric] | ML-predicted values |
| `ebitda_bridge` | EBITDABridgeResult | EBITDA decomposition |
| `simulation_summary` | SimulationSummary | MC outputs |
| `risk_flags` | List[RiskFlag] | Risk register |
| `diligence_questions` | List[DiligenceQuestion] | Question list |
| `provenance` | ProvenanceSnapshot | Source attribution |
| `completeness` | CompletenessAssessment | Data-quality summary |
| `audit_trail` | Optional[Dict] | Per-section status + reason |
| `schema_version` | str | `PACKET_SCHEMA_VERSION` |
| `created_at` | str (ISO) | timestamp |

**~14+ top-level fields.** Many sub-fields per dataclass; full enumeration is a multi-iteration task.

### Where instances are constructed

Per Report 0004:

| Constructor / Builder | Site |
|---|---|
| `analysis.packet_builder:build_analysis_packet(...)` | `analysis_store.py:241` (lazy), `cli.py` (analysis subcmd), `server.py` (route handlers) |
| Direct `DealAnalysisPacket(...)` | tests (80+ files per Report 0004) |
| Loaded from cache | `analysis_store:load_packet_by_id`, `find_cached_packet` |

**`build_analysis_packet` is the canonical constructor**; tests instantiate directly.

### Validators

The 30 dataclasses are stdlib `@dataclass` — **no Pydantic, no runtime validation**. Per Report 0027 same pattern as ServerConfig.

### Hashing / equality

`hash_inputs(...)` (re-exported) computes a stable input hash; `analysis_store` uses it as cache key.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR413** | **30+ re-exported symbols** — any signature change ripples to 80+ test files (cross-link Report 0004 MR24) | **High** |
| **MR414** | **No runtime validation on dataclass fields** | If a field type changes (e.g. str → Optional[str]), no error at construction; downstream consumers may NoneType-attribute-error. | Medium |
| **MR415** | **Field-by-field schema not enumerated this iteration** | A future deep audit must walk all 1,283 lines. Owed. | Medium |
| **MR416** | **`PACKET_SCHEMA_VERSION` constant** — increment policy unclear | Branches that change packet shape must bump it; no enforcement. | Medium |

## Dependencies

- **Incoming:** server.py (4 lazy imports per Report 0004), analysis/* (6 sibling files), 80+ test files.
- **Outgoing:** stdlib only (`dataclasses`, `datetime`, `enum`, `hashlib`, `json`, `math`, `typing`).

## Open questions / Unknowns

- **Q1.** What's the current `PACKET_SCHEMA_VERSION` value?
- **Q2.** Field-by-field types of every dataclass — owed.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0058** | Config value trace (already requested). |
| **0059** | Recent commits digest (already requested). |
| **0060** | Resolve a prior open question (already requested). |

---

Report/Report-0057.md written. Next iteration should: config value trace on a fresh value (not yet picked) — `PACKET_SCHEMA_VERSION` resolves Q1 here while exercising the trace pattern.

