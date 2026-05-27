# Backend Process: Data Ingestion

How real data gets into PEdesk — both the public CMS loaders and a deal's own
uploaded snapshot — so the Guide can explain provenance and /diligence/snapshot.

## Public data loaders
CMS HCRIS, Care Compare, provider enrollment, and other public datasets are
loaded via `rcm-mc data refresh` / the Data Catalog into SQLite. These are the
benchmark/universe layer (lagged — cost reports file with a delay).

## Deal snapshot ingestion (835/837)
A deal's claims/financial snapshot is uploaded and run through:
parse (X12 835/837 adapters) → normalize (payer resolution, CPT/ICD
validation, canonical row mapping) → reconcile remittances → de-duplicate
(exact + near-duplicate / resubmit detection) → roll up multi-EHR →
data-quality summary (row-level errors/warnings). Modules:
`rcm_mc/diligence/ingest/` + `rcm_mc/diligence/parsers/`.

## How to read it
- Ingestion is snapshot-based and versioned, not a live feed. The data-quality
  summary surfaces problems rather than hiding them — a high invalid-row count
  means the downstream analysis is on shaky ground.
- Public benchmark data and a deal's own uploaded data are different
  confidence tiers; do not conflate them.
