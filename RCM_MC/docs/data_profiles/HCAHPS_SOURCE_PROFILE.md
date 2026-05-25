# CMS HCAHPS — patient-experience source profile

**Source:** CMS Care Compare — *Patient survey (HCAHPS) - State*
(`data.cms.gov/provider-data` dataset `84jm-wiui`). Public, redistributable.

**What it is:** the official CMS patient-experience survey, published at the
**state** level as top-box percentages (already aggregated — no PII, no
facility-level handling needed). 51–52 states/territories × ~56 measures.

**Why it's the right anchor for `/patient-experience`:** the page's NPS /
complaint / service-recovery model is illustrative; HCAHPS is *the* real,
regulator-published patient-experience benchmark (it feeds Star Ratings and
VBP). Headline top-box measures wired:

- `H_HSP_RATING_9_10` overall rating 9–10
- `H_RECMND_DY` would definitely recommend
- nurse / doctor communication "always", staff explained meds, discharge
  info, room always clean, always quiet at night

## Ingest → committed aggregate

`scripts/ingest_hcahps.py` downloads the state file and pivots to one row per
state for the headline measures:

- `rcm_mc/data/vendor/hcahps/hcahps_state.csv`
- `rcm_mc/data/vendor/hcahps/hcahps_summary.json` (national = simple mean
  across states + survey period)

Loader: `rcm_mc/data/hcahps_data.py` (`functools.lru_cache`, no runtime
network). Registered `cms_hcahps_state`. Tests: `tests/test_hcahps_data.py`.

## Honesty caveats

- State-level published top-box %, **not** this deal's facilities.
- National figure is the **simple mean across states**, not patient-volume
  weighted.
- Not a payer-mix or financial figure.

## Note

The dataset id `632h-zaca` (labelled "hcahps" in `cms_care_compare.py`)
actually returns readmissions/complications measures — `84jm-wiui` is the
correct HCAHPS state file.

## Refresh

Re-run `python scripts/ingest_hcahps.py` when CMS publishes a new release.
