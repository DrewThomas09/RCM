# CDC PLACES — Health Equity / SDOH source profile

**Source:** CDC PLACES — *County Data (GIS Friendly Format)*, 2025 release
(`data.cdc.gov` dataset `i46a-9kgh`). Public, redistributable.

**What it is:** model-based, **full-population** county estimates of chronic
disease, risk behaviors, and (2025 release) social-determinants-of-health
measures, derived from BRFSS + ACS. 3,143 counties × ~120 measure columns
(crude + age-adjusted prevalence with 95% CIs).

**Why it's the right anchor for `/health-equity`:** the page's HEI / Star-bonus
scorecard is illustrative; PLACES supplies the real, observed SDOH burden the
equity thesis sits on — uninsured 18–64, food insecurity, lack of
transportation, utility-shutoff threat, frequent mental distress, etc. Unlike
`disease_density.py` (Medicare-beneficiary prevalence) PLACES is the full
population — the right denominator for an MSO/ASC's commercial flow.

## Ingest → committed aggregate

`scripts/ingest_cdc_places.py` downloads the release, then writes only a
compact, PII-free aggregate (no raw county file committed):

- `rcm_mc/data/vendor/cdc_places/places_equity_state.csv` — 51 rows
  (50 states + DC), population-weighted crude prevalence for the curated
  equity measure set.
- `rcm_mc/data/vendor/cdc_places/places_equity_summary.json` — national
  population-weighted prevalence + extract metadata.

Loader: `rcm_mc/data/cdc_places_agg.py` (`functools.lru_cache`, no runtime
network). Registered as `cdc_places_equity` in `source_registry.csv`.
Tests: `tests/test_cdc_places_equity.py`.

## Honesty caveats

- Model-based estimates (small-area), **not** a direct count and **not** this
  deal's patient population.
- Crude prevalence, population-weighted county→state (some sparse-county
  measures blank for small states).
- Not a payer-mix figure and not a provider-specific clinical outcome.

## Refresh

Re-run `python scripts/ingest_cdc_places.py` and bump `RELEASE`/`DATASET_ID`
when CDC publishes a new annual release.
