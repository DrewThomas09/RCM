# cdc_data — data.cdc.gov (Socrata SODA) connector

Self-contained, **stdlib-only** connector over the CDC's Socrata open-data
domain. It connects the **entire catalog** (~1,500 datasets), promotes
**twenty-seven** flagship datasets to first-class canonical tables, and
keeps every other 4x4 reachable through a generic on-demand rows table —
all behind the same `/v1` contract as the rest of the RCM connector
estate.

```
endpoints ─▶ transport ─▶ connector.discover()/fetch()/fetch_dataset() ─▶ raw rows
                                                              │
                                                        normalize ─▶ canonical SQLite tables
                                                              │              │
                                                          registry ─▶ /v1/query/{dataset} + /aggregate
                                                                        /v1/lookup/county-health/{fips}
                                                                        /v1/lookup/cdc-dataset/{4x4}
```

## API facts (verified live 2026-07-06)

- Base: `https://data.cdc.gov`
- **Catalog**: `GET /api/views/metadata/v1?limit=N&page=P` → JSON array of
  dataset metadata (4x4 `id`, `name`, `description`, `category`,
  camelCase timestamps, nested `customFields`). **Live quirk:** this
  endpoint pages by `limit` + **1-based `page`** — the documented
  `offset` param is silently *ignored* on this domain and would replay
  page 1 forever. Stop on a short/empty page (~1,508 datasets ≈ 4 pages
  at 500/page).
- **Rows**: `GET /resource/{4x4}.json?$limit=N&$offset=M&$where=…&col=value`
  (SoQL). Returns a bare JSON array; **null fields are omitted per row**,
  so the canonical column lists in `endpoints.py` were snapshotted from
  `/api/views/{4x4}.json` (the authoritative column metadata), not from
  row samples. Every paged request pins `$order=:id` (Socrata's stable
  system ordering) — pages without an explicit order are not
  deterministic.
- **Auth**: none required for modest volume (shared throttled pool). An
  application token from **`$CDC_APP_TOKEN`** is sent as `X-App-Token`
  when set and buys a dedicated rate allocation. A *wrong* token
  hard-403s (verified live), so the header is only attached when a token
  is genuinely configured.
- Unknown/retired 4x4 → HTTP 404 → treated as zero rows (estate
  convention), not an error.
- Rate posture: courtesy floor of 0.25 s between requests, 429/5xx retried
  with exponential backoff + full jitter, `Retry-After` honoured. These
  are conservative defaults, **not** a documented Socrata contract —
  verify at dev.socrata.com before a bulk run.

## Datasets (29 registry rows)

The first 14 are the original curation; the 15 below the divider are the
**2026-07 catalog curation sweep** (see the sweep note further down). Every
4x4 was verified live on 2026-07-06 and every natural key was confirmed
unique on a real ≥2,000-row pull (the biggest four also confirmed by a
full drain that ingested every row without key collapse).

| dataset_id | 4x4 | target table | grain / natural key |
|---|---|---|---|
| `cdc_data_catalog` | — | `cdc_data_catalog` | one row per dataset on data.cdc.gov (pk = 4x4 id) |
| `cdc_data_places_county` | `swc5-untb` | `cdc_places_county` | PLACES county measure: `state:fips:measure:valuetype` |
| `cdc_data_places_county_ckd` | `h3ej-a9ec` | `cdc_places_county_ckd` | PLACES 2023 county CKD prevalence (pinned `measureid=KIDNEY`): `state:fips:KIDNEY:valuetype` |
| `cdc_data_provisional_deaths_state` | `9bhg-hcku` | `cdc_provisional_deaths_state` | `group:year:month:state:sex:age_group` |
| `cdc_data_vsrr_drug_overdose` | `xkb8-kh2a` | `cdc_vsrr_drug_overdose` | `state:year:month:indicator` |
| `cdc_data_nchs_leading_causes` | `bi63-dtpu` | `cdc_nchs_leading_causes` | `year:state:cause` |
| `cdc_data_weekly_deaths_by_cause` | `u6jv-9ijr` | `cdc_weekly_deaths_by_cause` | `state:mmwr_year:week:cause:type` |
| `cdc_data_monthly_deaths_select_causes` | `9dzk-mvmi` | `cdc_monthly_deaths_select_causes` | national monthly deaths by select cause: `jurisdiction:year:month` |
| `cdc_data_brfss_prevalence` | `dttw-5yxu` | `cdc_brfss_prevalence` | `year:state:class:topic:question:response:breakout` |
| `cdc_data_chronic_disease_indicators` | `hksd-2xuw` | `cdc_chronic_disease_indicators` | `years:state:question:response:valuetype:strat` |
| `cdc_data_life_expectancy_tract` | `5h56-n989` | `cdc_life_expectancy_tract` | `state:county:census_tract` |
| `cdc_data_drug_poisoning_county` | `rpvx-m2md` | `cdc_drug_poisoning_county` | `fips:year` |
| `cdc_data_heart_disease_mortality_county` | `th8y-thx5` | `cdc_heart_disease_mortality` | `fips:year:sex:race` |
| `cdc_data_fetched_rows` | any | `cdc_data_rows` | generic pull: `{dataset_key}:{row_idx}` |
| — *2026-07 sweep* — | | | |
| `cdc_data_teen_birth_county` | `3h58-x6cd` | `cdc_teen_birth_county` | **natality** — teen (15-19) birth rate by county: `combined_fips(5-digit):year` (56,466 rows) |
| `cdc_data_vsrr_birth_indicators` | `76vv-a7x8` | `cdc_vsrr_birth_indicators` | **natality (provisional)** — national quarterly birth indicators: `year_quarter:topic_subgroup:indicator:race` (900) |
| `cdc_data_infant_mortality_state` | `pjb2-jvdr` | `cdc_infant_mortality_state` | **infant mortality** — by state/race (DQS): `state_fips:group:subgroup:subtopic:period:est_type` (1,710) |
| `cdc_data_vsrr_maternal_death` | `e2d5-ggg7` | `cdc_vsrr_maternal_death` | **maternal mortality** — provisional counts/rates: `jurisdiction:group:subgroup:year:month:period` (840) |
| `cdc_data_flu_vaccination_coverage` | `vh55-3he6` | `cdc_flu_vaccination_coverage` | **immunization (flu)** — coverage all ages: `fips:vaccine:season:month:dim_type:dim` (235,381) |
| `cdc_data_kindergarten_vaccination` | `ijqb-a7ye` | `cdc_kindergarten_vaccination` | **immunization (childhood)** — kindergarten coverage/exemptions: `state:season:vaccine:dose:survey` (8,166) |
| `cdc_data_smoking_attributable_mortality` | `4yyu-3s69` | `cdc_smoking_attributable_mortality` | **tobacco** — SAMMEC smoking-attributable deaths by state: `state:year:measure:submeasure:sex` (312) |
| `cdc_data_npao_brfss` | `hn4x-zwk7` | `cdc_npao_brfss` | **obesity/nutrition/PA** — NPAO's BRFSS cut: `state:yearstart:yearend:question:strat:valuetype` (110,880) |
| `cdc_data_injury_violence_county` | `psx4-wq38` | `cdc_injury_violence_county` | **suicide/violence** — injury/overdose/violence rates by county: `geoid(5-digit):intent:period` (132,000) |
| `cdc_data_disability_dhds` | `s2qv-b27b` | `cdc_disability_dhds` | **disability** — DHDS status/type prevalence by state: `state:indicator:response:strat:year` (3,592) |
| `cdc_data_pm25_county` | `53mz-4zqd` | `cdc_pm25_county` | **environmental (air)** — daily county PM2.5 2001-2022: `statefips:countyfips:date` (24.9M) |
| `cdc_data_stroke_mortality_county` | `cpdh-8cna` | `cdc_stroke_mortality_county` | **cardiovascular** — stroke mortality 35+ by county: `fips:year:strat1:strat2` (78,792) |
| `cdc_data_diabetes_state_burden` | `b559-sbez` | `cdc_diabetes_state_burden` | **diabetes** — USDSS state burden indicators: `state:year:topic:indicator:age:race:sex:education` (114,275) |
| `cdc_data_oral_health_adults` | `jz6n-v26y` | `cdc_oral_health_adults` | **oral health** — NOHSS adult indicators by state: `state:year:indicator:break_out:response` (31,542) |
| `cdc_data_alzheimers_aging` | `hfr9-rurv` | `cdc_alzheimers_aging` | **healthy aging/dementia** — Alzheimer's & Healthy Aging by state: `state:yearstart:yearend:question:strat1:strat2:valuetype` (284,142) |

The six datasets over ~100k rows (`flu_vaccination_coverage`, `npao_brfss`,
`injury_violence_county`, `pm25_county`, `diabetes_state_burden`,
`alzheimers_aging`) default to a smaller 500-row page like BRFSS, so an
accidental "fetch" under the default 5-page cap stays a modest pull. Two
sweep datasets carry a live `group` field (an SQL keyword) that the
documented normalizer renames to `group_field`
(`infant_mortality_state`, `vsrr_maternal_death`). Three sweep county
tables (`teen_birth_county`, `stroke_mortality_county`,
`injury_violence_county`) key on the same 5-digit FIPS as PLACES and are
folded into the `county-health` lookup.

Assignment-id corrections found during live verification: `pj7m-y5uh` is
*not* the Chronic Disease Indicators (it is "Provisional COVID-19 Deaths:
Distribution of Deaths by Race and Hispanic Origin") — the correct CDI id
is `hksd-2xuw`; `ikd3-hr7f` 404s — the live life-expectancy dataset is
`5h56-n989`.

## Kidney-disease surveillance coverage

CDC runs a Chronic Kidney Disease Surveillance System, but it is a **web
application** (ckd.cdc.gov), **not** a Socrata dataset — a full catalog
sweep (all 1,508 datasets, verified live 2026-07-06) finds no standalone
"CKD Surveillance" 4x4, and the one NCHS↔USRDS end-stage-renal-disease
linkage (`jmgj-74h4`) returns **HTTP 403** (restricted micro-data, not
queryable). CKD on data.cdc.gov is therefore spread across several
datasets; this connector curates the three grains that matter and
documents how to reach each:

- **State indicator over time — already curated.** The premier CKD
  surveillance indicator, *incidence of treated end-stage kidney disease*,
  lives inside the curated **`cdc_data_chronic_disease_indicators`**
  (`hksd-2xuw`), topic `Chronic Kidney Disease` (52 jurisdictions, years
  2019–2022, adjusted rate + number; 416 rows live). Slice it:
  ```bash
  python -m connectors.cdc_data.cli --db ./cdc.db query \
      cdc_data_chronic_disease_indicators \
      --filter topic="Chronic Kidney Disease" --filter locationabbr=US
  ```
- **County prevalence — new curated `cdc_data_places_county_ckd`.**
  PLACES county data carries CKD prevalence under **`measureid = KIDNEY`**
  (measure "Chronic kidney disease among adults aged >=18 years", both
  `CrdPrv` and `AgeAdjPrv` value types). **Live verification caveat:** the
  KIDNEY measure was **dropped from PLACES' 2024 and 2025 county
  releases** — the currently-curated `cdc_data_places_county`
  (`swc5-untb`, 2025 release) has **zero** KIDNEY rows
  (`$where=measureid='KIDNEY'` → empty). The most recent PLACES county
  vintage that still carries it is the **2023 release `h3ej-a9ec`**
  (6,154 KIDNEY rows live: ~3,077 counties × 2 value types, year 2021),
  so it is curated here as its own measure-pinned table
  (`default_params={"measureid":"KIDNEY"}`). This table also feeds the
  `chronic_kidney_disease` section of the `county-health` lookup.
- **National mortality over time — new curated
  `cdc_data_monthly_deaths_select_causes`.** `9dzk-mvmi` (Monthly
  Provisional Counts of Deaths by Select Causes, 2020–2023, national, 45
  rows) carries kidney-disease mortality as the first-class column
  **`nephritis_nephrotic_syndrome`** (Nephritis, nephrotic syndrome and
  nephrosis). Kidney disease *as a leading cause of death* is also already
  sliceable inside curated `cdc_data_nchs_leading_causes`
  (`--filter cause_name="Kidney disease"`).
- **Generic-fetch alternative — Diabetes State Burden Toolkit.**
  `ircd-wk4g` (Diabetes State Burden Toolkit – Health Burden) reports a
  state-level `Chronic Kidney Disease` indicator among Medicare
  beneficiaries with diabetes (1,742 rows). It is **not** promoted to a
  first-class table: the source has genuine duplicate composite keys
  (1,742 rows collapse to 1,404 distinct on every candidate natural key),
  so pull it through the generic escape hatch instead:
  ```bash
  python -m connectors.cdc_data.cli --db ./cdc.db fetch --dataset ircd-wk4g \
      --where "short_text_indicator='Chronic Kidney Disease'" --max-pages 1
  ```

Canonical column names are the live Socrata field names run through the
documented normalizer (`flatten.to_column`): lowercase snake_case, and a
field colliding with an SQL keyword gets a `_field` suffix (live `group`
→ column `group_field`) because the uniform query engine interpolates
whitelisted identifiers bare. Everything is stored TEXT (`geolocation`
and `tags` as JSON); only `row_idx` is INTEGER.

## 2026-07 catalog curation sweep

A category-by-category pass over the whole synced catalog (1,508 datasets,
verified live 2026-07-06) added the 15 datasets below the divider in the
table above — one clean state/county multi-year dataset per health-analysis
category the earlier curation lacked. Selection bar: the 4x4 must return
real rows via SODA (not an empty data-lens/map view), carry a natural key
proven unique on a live pull, and prefer a state/county grain with a
multi-year time series. Anything duplicating an already-curated grain was
skipped.

**Category coverage map** (category → curated dataset_id, or documented skip):

| category | outcome |
|---|---|
| natality / births | `cdc_data_teen_birth_county` (`3h58-x6cd`, county) + `cdc_data_vsrr_birth_indicators` (`76vv-a7x8`, national quarterly) |
| immunization — flu | `cdc_data_flu_vaccination_coverage` (`vh55-3he6`) |
| immunization — childhood | `cdc_data_kindergarten_vaccination` (`ijqb-a7ye`) |
| tobacco use | `cdc_data_smoking_attributable_mortality` (`4yyu-3s69`, SAMMEC) |
| obesity / nutrition / physical activity | `cdc_data_npao_brfss` (`hn4x-zwk7`) |
| maternal / infant health | `cdc_data_infant_mortality_state` (`pjb2-jvdr`) + `cdc_data_vsrr_maternal_death` (`e2d5-ggg7`) |
| suicide / violence | `cdc_data_injury_violence_county` (`psx4-wq38`, county; `intent` = suicide/homicide/…) |
| disability | `cdc_data_disability_dhds` (`s2qv-b27b`) |
| environmental health (air quality) | `cdc_data_pm25_county` (`53mz-4zqd`, daily county PM2.5) |
| cardiovascular (stroke) | `cdc_data_stroke_mortality_county` (`cpdh-8cna`) — distinct topic from the curated heart-disease table |
| diabetes | `cdc_data_diabetes_state_burden` (`b559-sbez`, USDSS) — distinct source from BRFSS/CDI |
| oral health | `cdc_data_oral_health_adults` (`jz6n-v26y`, NOHSS) |
| healthy aging / dementia | `cdc_data_alzheimers_aging` (`hfr9-rurv`) |
| **social vulnerability (CDC SVI)** | **SKIP — not queryable.** The only SVI 4x4 on the domain, `ypqf-r5qs` ("Social Vulnerability Index"), is a **data-lens/map view whose SODA endpoint returns empty `{}` rows** for every record despite a `count(*)` of 3,142 (verified live: `/api/views/ypqf-r5qs.json` exposes zero columns). The only other SVI hit, `9hdi-ekmb`, is *Provisional COVID-19 Deaths by County SVI* — COVID mortality bucketed by SVI quartile (780 rows), not a county SVI index. The authoritative CDC/ATSDR SVI is distributed off-Socrata (svi.cdc.gov CSV/shapefile); no clean county-SVI natural-key dataset exists on data.cdc.gov. |
| **STI / HIV surveillance** | **SKIP — no clean grain.** The only STI data on the domain is the **NNDSS notifiable-disease tables** (e.g. `5egk-p6rd` "Table II. Chlamydia to Coccidioidomycosis"): wide, one-4x4-per-year-vintage, multiple conditions per table, column names with the year baked in (`chlamydia_..._cum_2017`) — not a single clean multi-year STI series. HIV/STD surveillance proper (AtlasPlus) lives on gis.cdc.gov, off this domain. Any NNDSS table is still reachable via the generic escape hatch (`fetch --dataset 5egk-p6rd`). |
| **alcohol** | **SKIP — duplicate/absent.** No standalone clean alcohol dataset (CDC's ARDI is off-Socrata). Alcohol is already curated: `cdc_data_chronic_disease_indicators` carries the `Alcohol` topic, `cdc_data_brfss_prevalence` carries binge drinking, and alcohol-induced deaths sit in the mortality tables. Curating another would duplicate an existing grain. |
| **healthcare-associated infections** | **SKIP — no geographic key.** The domain's only HAI data is the **HAICViz dashboard-backing aggregates** (`abgz-qs4g` C. diff, `34p9-h4us` candidemia, …): columns `topic/series/viewby/value/yearname` — chart series with **no state/county FIPS grain**. There is **no** NHSN standardized-infection-ratio (CLABSI/CAUTI/MRSA/C.diff SIR) dataset on data.cdc.gov (searched `standardized infection ratio`/`clabsi`/`central line`/`bloodstream` → 0 hits); the NHSN datasets present are weekly *respiratory* hospital admissions, not HAI SIRs. Reachable via generic fetch if the aggregate is wanted. |

Other grains deliberately **not** promoted (would duplicate existing
curated tables or add no clean key): the DQS / GIS-friendly / ZCTA / place
/ census-tract PLACES re-cuts, the older BRFSS vintages and SMART
metro-area cuts, the per-year PRAMStat maternal files (2000-2011, one 4x4
each), and the county/tract *ozone* twin of PM2.5 (`3vxk-q2jk`, same schema
and grain as the curated PM2.5 table — one air-quality pollutant is
enough). All remain reachable through the generic `cdc_data_rows` table.

## Usage

```bash
# The registry
python -m connectors.cdc_data.cli datasets

# Sync the FULL catalog (~1.5k datasets, ~4 requests) into a db
python -m connectors.cdc_data.cli --db ./cdc.db discover

# Search the synced catalog locally
python -m connectors.cdc_data.cli --db ./cdc.db catalog-search --q "life expectancy"

# Ingest one page of PLACES county data (paging absorbed; polite default
# cap of 5 pages per call — pass --max-pages explicitly for a bulk run)
python -m connectors.cdc_data.cli --db ./cdc.db fetch --dataset places_county \
    --max-pages 1 --filter stateabbr=AL

# SoQL passthrough for anything fancier
python -m connectors.cdc_data.cli --db ./cdc.db fetch --dataset vsrr_drug_overdose \
    --where "state='CA' AND year='2023'" --max-pages 1

# ANY 4x4 on the domain lands in the generic cdc_data_rows table
python -m connectors.cdc_data.cli --db ./cdc.db fetch --dataset 9yie-6ukv --max-pages 1

# Query the canonical tables through the uniform engine
python -m connectors.cdc_data.cli --db ./cdc.db query cdc_data_places_county \
    --filter measureid=CSMOKING --sort=-data_value --limit 5

# Lookups
python -m connectors.cdc_data.cli --db ./cdc.db lookup-county-health 01073
python -m connectors.cdc_data.cli --db ./cdc.db lookup-cdc-dataset swc5-untb

# Standalone /v1 surface
python -m connectors.cdc_data.cli --db ./cdc.db serve --port 8099
```

`/v1` routes (same contract as every estate connector): `/health`,
`/v1/datasets`, `/v1/query/{dataset}` (filter grammar `field__op`, ops
`eq/ne/gt/gte/lt/lte/like/in/between/isnull/notnull`),
`/v1/query/{dataset}/aggregate?group_by=…`, plus the two lookups above.

## Politeness / paging model

`fetch()` absorbs SoQL `$limit`/`$offset` paging entirely; callers never
see it. Each call is bounded by `max_pages` (default **5**; hard cap
1000) so an accidental "fetch BRFSS" (~2M rows live) cannot hammer the
API — BRFSS additionally defaults to a smaller 500-row page. A result
reports `exhausted=False` when the cap cut the pull short.

## Tests

```bash
cd /home/user/RCM && python3 -m unittest discover -s connectors/cdc_data/tests -t . -v
```

Stdlib `unittest`, no network: an injectable fake opener
(`tests/fakes.py`) mirrors the live shapes — including the catalog's
`limit`+`page` quirk and Socrata's omitted-null rows — and scripted
429/5xx transients exercise the retry paths. The API-server suite runs a
real `ThreadingHTTPServer` on a free port.
