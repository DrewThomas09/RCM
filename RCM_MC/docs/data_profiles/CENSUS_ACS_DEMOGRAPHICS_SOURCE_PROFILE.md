# Census ACS county demographics — source profile & market-intel use plan

**Requested:** U.S. Census ACS demographic variables for healthcare market
intelligence.

**Source/license finding (the "verify public source/license" step):** the
direct Census ACS API (`api.census.gov/data/.../acs/acs5[/profile]`) now
**requires an API key** for every request (returns a "Missing Key"
redirect). An API key is a secret we will not sign up for or commit. The
same ACS-derived demographics are published **keyless and redistributable**
by **County Health Rankings & Roadmaps (CHR)** (UW Population Health
Institute), which sources them from the Census Bureau (ACS / Population
Estimates / SAHIE / SAIPE). We therefore deliver the requested variables via
the CHR analytic file. If a Census API key is later provided, the loader
contract is unchanged — only `scripts/ingest_county_demographics.py` would
swap its fetch.

## Variable set (compact, market-relevant)

| key | meaning | CHR column |
|---|---|---|
| `population` | total population | Population raw value |
| `pct_age_65_plus` | share 65+ | % 65 and Older raw value |
| `median_household_income` | $ | Median Household Income raw value |
| `child_poverty_rate` | children in poverty | Children in Poverty raw value |
| `uninsured_rate` | uninsured | Uninsured raw value |
| `pct_white_nh` / `pct_black_nh` / `pct_hispanic` | race/ethnicity | % Non-Hispanic White/Black, % Hispanic |
| `pct_rural` | rural share | % Rural raw value |

Percent measures are stored as **fractions (0–1)**. County `5-digit FIPS`
is preserved; state aggregates are population-weighted.

## Ingest → committed aggregate

`scripts/ingest_county_demographics.py` → `rcm_mc/data/vendor/county_demographics/`:
`county_demographics.csv` (3,143 counties, FIPS preserved), `demographics_state.csv`
(51 states, pop-weighted), `demographics_summary.json` (national + metadata).
Loader: `rcm_mc/data/county_demographics.py` (`lru_cache`, no runtime network).
Registered `chr_county_demographics`. Tests: `tests/test_county_demographics.py`.

## Caveats

- ACS values are **survey estimates** (pooled, with margins of error); year
  and estimate limitations matter.
- Area-level market context — **not** provider-specific and **not** this
  deal's patient population.
- Missingness preserved (sparse small counties blank, not zero-filled).

## Refresh

Bump `CHR_YEAR` in the ingest script when a new CHR analytic file ships.
