# HHS OIG LEIE (excluded providers) — source profile

**Source:** HHS Office of Inspector General — List of Excluded Individuals/Entities
(oig.hhs.gov/exclusions), public, updated monthly.
**Coverage:** 83K+ providers/entities excluded from federal health programs, by state,
exclusion-authority type (e.g. 1128b4 license revocation, 1128a1 program-related crime),
year, and specialty.

**Why it anchors `/fraud-detection`:** OIG exclusions are the *realized* Medicare/Medicaid
fraud-&-abuse / sanction record — the real base rate a fraud-risk thesis sits on. The page's
per-provider fraud-risk scores are illustrative; LEIE is the observed outcome record.

## PII handling (critical)
The raw LEIE file contains PII (names, NPI, DOB, address). `scripts/ingest_oig_leie.py`
**drops all PII at ingest** and commits only aggregate counts
(`rcm_mc/data/vendor/oig_leie/oig_leie_summary.json`). Loader `rcm_mc/data/oig_leie.py`.
Registered `oig_leie`. Tests `tests/test_oig_leie.py` (incl. a PII-absence assertion).

## Honesty caveats
- Realized exclusions, **not** a prediction and **not** this deal's providers.
- Counts only; no individual identification in the committed aggregate.

## Refresh
Re-run `python scripts/ingest_oig_leie.py` (OIG updates monthly).
