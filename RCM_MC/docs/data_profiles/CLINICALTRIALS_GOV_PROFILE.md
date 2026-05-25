# ClinicalTrials.gov trial landscape — source profile

**Source:** ClinicalTrials.gov v2 API (U.S. National Library of Medicine), public/keyless.
**Coverage:** registry-wide counts — total studies (~586K), currently recruiting (~65K),
interventional (~447K), and counts by phase (1–4). Build-time queries; runtime reads the
committed JSON summary (no live API).

**Why it anchors `/trial-site-econ`:** clinical-research-site economics are driven by trial
volume, recruiting demand, and phase mix (later phases = larger, higher-revenue site work).
The registry gives the real landscape; the page's per-site P&L/enrollment model is illustrative.

## Ingest → committed aggregate
`scripts/ingest_clinical_trials.py` → `rcm_mc/data/vendor/clinical_trials/clinical_trials_summary.json`.
Loader `rcm_mc/data/clinical_trials.py`. Registered `clinicaltrials_gov`. Tests `tests/test_clinical_trials.py`.

## Honesty caveats
- Registry counts, **not** this deal's sites or revenue, and not a financial figure.
- Registry coverage is not 100% of all trials worldwide.

## Refresh
Re-run `python scripts/ingest_clinical_trials.py` (counts update continuously).
