# diligence/ingest/

**Phase 1 — Ingestion & Normalization.** Turns messy seller data (CSV / Excel / scanned / EDI 837 / 835) into the **Canonical Claims Dataset (CCD)** that every downstream diligence phase reads from.

## The data contract

The **CCD is the single artefact** every downstream phase reads. Partners and CFOs can defend a number to a skeptical auditor by walking:

```
KPI  →  CCD rows that feed it  →  TransformationLog entries  →  source file + source row + rule
```

Row-level auditability is the load-bearing property. No interpolated numbers; every normalization logged.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Public surface — `CanonicalClaim`, `CanonicalClaimsDataset`, `TransformationLog`, `ingest_dataset`. |
| `ccd.py` | **The data contract.** `CanonicalClaim` dataclass + `CanonicalClaimsDataset` + `TransformationLog` primitives. |
| `ingester.py` | **The driver.** `ingest_dataset(path)` walks a dataset dir, dispatches to readers, feeds rows through normalisers, emits `CanonicalClaimsDataset` with row-logged `TransformationLog`. |
| `readers.py` | Source-format readers — CSV (stdlib `csv`, no pandas), Excel (openpyxl), fixed-width, JSON. Each returns row dicts + per-row source metadata. Format-agnostic downstream. |
| `normalize.py` | Normalization primitives — each takes raw value + TransformationLog + row context, returns coerced value + logs decision. Row-scoped logs so "why is this field what it is?" is one filter away. |
| `tuva_bridge.py` | Maps `CanonicalClaimsDataset` → Tuva Input Layer schema so partners who want the richer Tuva marts (CCSR, HCC, financial_pmpm, chronic conditions, readmissions) can run vendored Tuva dbt on top of our CCD. |

## Invariants (enforced by fixture tests)

Tests against `tests/fixtures/messy/`:
- Every claim row that makes it into the CCD has a corresponding `TransformationLog` entry for every normalized field
- Every field in the CCD was either sourced or logged-as-missing; no silent defaults
- Re-running the ingester on the same input produces byte-identical output (determinism)
- Timezone-naive datetimes convert to UTC with logged assumption
- Payer name variants collapse to canonical names via `infra.config.canonical_payer_name`

## The relationship to `rcm_mc_diligence/`

**Two parallel ingestion paths**:
- **This package** (`rcm_mc/diligence/ingest/`) — lightweight Python-only, stdlib + pandas. Runs anywhere.
- **`rcm_mc_diligence/`** — heavyweight dbt + DuckDB + vendored Tuva. Requires a working dbt install.

Both terminate in packet-shaped artifacts (`DealAnalysisPacket` vs `DQReport`). The choice is a deployment fit — firms with a data engineer prefer the dbt path; firms without prefer this one.

## Bridge to Phase 4 packet

`diligence/ccd_bridge.py` is the single choke point between Phase 1 output (CCD + TransformationLog + Phase 2 KPIs) and the Phase 4 `analysis.packet_builder`. It converts CCD-derived KPIs into the `observed_metrics` dict the builder expects + produces matching provenance nodes.

## Tests

`tests/test_ingest*.py` — deterministic fixtures under `tests/fixtures/messy/`. Each scenario exercises a specific pathology pattern.
