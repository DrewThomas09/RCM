# OMB CBSA delineation × county ACS — source profile & geo use plan

**Requested:** real metro/micro-area (CBSA) demographics to give the
Geographic Intelligence suite a metro level and to de-synthesize the
illustrative `/geo-market` analyzer.

**Source/license finding (the "verify public source/license" step):** the
Core-Based Statistical Area definitions are published by the U.S. Census
Bureau on behalf of OMB as a **keyless, public-domain spreadsheet** (the
"delineation files"). We use the **July-2023** vintage (OMB Bulletin 23-01):

`https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xlsx`

It is a U.S. government work (public domain), freely redistributable. No API
key, no licensing constraint. `scripts/ingest_cbsa_crosswalk.py` curl-fetches
it (system trust store), reads the header on row index 2, and commits a
compact PII-free crosswalk.

## What we commit

`rcm_mc/data/vendor/cbsa_crosswalk/cbsa_county_crosswalk.csv` — one row per
county, mapping it to its CBSA:

| column | meaning |
|---|---|
| `county_fips` | 5-digit county FIPS (zero-padded) |
| `cbsa_code` | 5-digit CBSA code |
| `cbsa_title` | CBSA name (e.g. "New York-Newark-Jersey City, NY-NJ") |
| `area_type` | `Metropolitan` or `Micropolitan` |
| `central_outlying` | the county's role in the CBSA |

**1,915 counties → 935 CBSAs** (1,252 metro + 663 micro county rows). Plus
`cbsa_crosswalk_meta.json` (vintage, source URL, counts, ingest date).

## How CBSA demographics are derived

`rcm_mc/data/cbsa_demographics.py` joins this crosswalk to the committed
county demographics (`county_demographics`, sourced from Census ACS via
County Health Rankings — see `CENSUS_ACS_DEMOGRAPHICS_SOURCE_PROFILE.md`) and
rolls counties up to CBSAs. **918 CBSAs** carry demographics (covering
~311.8M people):

| metric | aggregation | honesty |
|---|---|---|
| `population` | **sum** of member-county populations | real |
| `pct_age_65_plus`, `uninsured_rate`, `pct_rural` | **population-weighted mean** of county values | real |
| `median_household_income` | **population-weighted mean** of county medians | **ESTIMATE** — a true CBSA median needs microdata; labelled wherever shown |

The join normalizes `county_fips` to 5 digits on **both** sides (the
demographics file drops the leading zero). Counties with no demographic row
are **excluded** from a CBSA's roll-up — never fabricated to fill gaps.

## Powers

- `/metro-markets` — the real-data CBSA analyzer (metro/micro filter,
  sortable, CSV) and the real counterpart to the illustrative `/geo-market`.

## What it indicates / does NOT prove

Real metro-level demographic scale and mix — the demand backdrop of a market
at the unit healthcare deals are usually scoped to. It is **area-level**, not
a deal's catchment or patient panel, and the income figure is a
population-weighted **estimate**, not a surveyed CBSA median. The competitive
inputs on `/geo-market` (HHI, 5-yr growth, payer mix) remain illustrative —
they have no public source and are clearly labelled as such.
