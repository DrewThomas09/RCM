# Provenance & Data Quality

How PEdesk tracks where every number came from and flags weak data. Explains
the backend so the Guide can answer "where did this number come from / how
complete is the data / what do the honesty dots mean".

## Provenance graph (`rcm_mc/provenance/graph.py`, `explain.py`)
- Computed figures carry a lineage: which inputs and data sources fed them.
  `explain.py` turns that graph into a plain-English "why this number" trace,
  so an analyst can audit any figure back to its source.

## Data-completeness grading (`rcm_mc/analysis/completeness.py`)
- Scores how complete the inputs are for an analysis, flags missing/imputed
  fields with severity, and surfaces benchmark outliers. A figure leaning
  heavily on imputed inputs is marked as such (see the imputation_share and
  data_coverage_score metrics).

## Surface honesty tiers (`rcm_mc/diligence/surface_status.py`)
- Every page is classified into an honesty tier — green (live/observed),
  navy (computed from public data), data-required, yellow (illustrative),
  red (placeholder) — so a partner can tell at a glance whether a surface is
  real data, a benchmark, a model estimate, or a scaffold awaiting their upload.

## How to read it
- Confidence labels (data_confidence on each page; formula_confidence on each
  metric) are deliberate honesty signals, not decoration. "Illustrative" /
  "model estimate" means do not treat the figure as the deal's realized value.

## Caveats
- Provenance shows how a number was computed, not that the underlying source is
  correct or current — HCRIS and other public data lag.
