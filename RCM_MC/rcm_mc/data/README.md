# Data

Data ingestion, public-data loaders, and hospital profile assembly. Connects to CMS (HCRIS, Care Compare, Utilization), IRS Form 990, SEC EDGAR, and seller-provided files. All external fetches use stdlib `urllib` — no third-party HTTP libraries.

---

## `cms_hcris.py` — HCRIS Benchmark Database Loader

**What it does:** Loads CMS Hospital Cost Report (HCRIS) data into the `hospital_benchmarks` SQLite table. Provides the primary public financial benchmark for every US hospital — ~6,000 records with bed counts, payer mix, revenue, margins, and operating metrics.

**How it works:** Downloads the annual HCRIS zip (`HOSP10FY{year}.zip`) from `downloads.cms.gov/hcris/...` via `_cms_download.py`. Parses the fixed-width HCRIS bundle (three sub-files: numeric, alphanumeric, reports) using a coordinate table (worksheet/line/column) to extract 15 fields per hospital: provider_id (CCN), fiscal year, bed count, total discharges, CMI, gross and net patient revenue, operating expenses, operating margin, payer mix fractions, bad debt, charity care. Normalizes into `HCRISRecord` objects. Upserts into `hospital_benchmarks` with `source='hcris'` using `UNIQUE(provider_id, source, metric_key, period)` conflict resolution.

**Data in:** Annual CMS HCRIS zip file from `https://downloads.cms.gov/hcris/`. Uses pre-parsed `hcris.csv.gz` shipped with the package for the current year (no network call required for core use).

**Data out:** `HCRISRecord` objects → `hospital_benchmarks` SQLite table rows (`metric_key` / `value` / `period` per hospital per field).

---

## `hcris.py` — HCRIS Public Data Layer

**What it does:** Parses the raw CMS HCRIS bundle (the pre-shipped `hcris.csv.gz`) for one-off CCN lookups and powers the `rcm-lookup` CLI. Also defines `HCRIS_URL_TEMPLATE` used by `cms_hcris.py` for annual refreshes.

**How it works:** Reads the bundled `hcris.csv.gz` (gzip-compressed CSV shipped in the package at `data/hcris.csv.gz`) directly into pandas for fast CCN lookups. Provides `lookup_ccn(ccn)`, `search_by_name(name)`, `list_by_state(state)`, and `filter_by_beds(min_beds, max_beds)` functions. Also exposes `refresh_hcris(year)` which downloads a fresh annual bundle and re-parses it.

**Data in:** Bundled `hcris.csv.gz` file (shipped with the package, ~6,000 hospitals); or freshly downloaded zip for refresh.

**Data out:** Pandas DataFrame rows for CCN lookups; feeds `rcm-lookup` CLI and `auto_populate.py`.

---

## `cms_care_compare.py` — CMS Care Compare Loader

**What it does:** Downloads and normalizes CMS Care Compare quality data: hospital star ratings, HCAHPS patient satisfaction scores, complication rates, and readmission rates.

**How it works:** Fetches three CSV endpoints from the CMS Provider Data Catalog API: (1) General: `https://data.cms.gov/provider-data/api/1/datastore/query/xubh-q36u/0/download?format=csv` (star ratings); (2) HCAHPS: `https://data.cms.gov/provider-data/api/1/datastore/query/632h-zaca/0/download?format=csv`; (3) Complications: `https://data.cms.gov/provider-data/api/1/datastore/query/ynj2-r877/0/download?format=csv`. Uses `_cms_download.py` for atomic fetch with retry. One failing URL does not kill the batch — partial results are stored. Normalizes into `CareCompareRecord` objects and upserts into `hospital_benchmarks` with `source='care_compare'`.

**Data in:** CMS Provider Data Catalog API — public, no authentication required. Schema drifts annually; `_cms_download.py` handles graceful column-name fallbacks.

**Data out:** `CareCompareRecord` objects → `hospital_benchmarks` table with quality metrics per CCN.

---

## `cms_utilization.py` — Medicare Inpatient Utilization Loader

**What it does:** Downloads CMS Medicare inpatient utilization data: DRG volumes per provider, charge-to-payment ratios, and service-line concentration.

**How it works:** Fetches the IPPS DRG discharge data from `https://data.cms.gov/provider-summary-by-type-of-service/...` via `_cms_download.py`. For each provider: aggregates total discharges by DRG, computes HHI service-line concentration score (measures how concentrated a hospital's volume is in a few DRGs — high HHI = specialty-focused, low HHI = general acute). Computes charge-to-payment ratio per DRG as a proxy for commercial leverage. Upserts into `hospital_benchmarks` with `source='utilization'`.

**Data in:** CMS IPPS DRG-level provider utilization data — public annual file.

**Data out:** HHI concentration score and charge-to-payment ratios per provider → `hospital_benchmarks` table.

---

## `data_refresh.py` — Data Source Orchestrator

**What it does:** Sequences and orchestrates refreshes of the four core CMS data sources (HCRIS, Care Compare, Utilization, IRS 990). Records provenance and handles partial failures so one broken source doesn't block the others.

**How it works:** Accepts `source` parameter: `'all'` / `'hcris'` / `'care_compare'` / `'utilization'` / `'irs990'`. For each source: calls the relevant loader, catches exceptions, logs success/failure with timestamps into the `data_source_log` table. Returns a `RefreshReport` with per-source status. Exposes the `rcm-mc data refresh` CLI command and the `GET /api/data/sources` HTTP endpoint. Respects the rate limiter (one refresh per source per hour) enforced by `infra/rate_limit.py`.

**Data in:** Network: CMS HCRIS, Care Compare, Utilization URLs; ProPublica IRS 990 API.

**Data out:** Updated `hospital_benchmarks` rows; `RefreshReport` for the CLI and API; `data_source_log` audit rows.

---

## `auto_populate.py` — One-Name-to-Full-Profile Assembly

**What it does:** Given a hospital name (or CCN), assembles a complete hospital profile by merging HCRIS, Care Compare, IRS 990, and utilization data with per-field source attribution. Used by the "Auto-populate from HCRIS" button in the new-deal wizard.

**How it works:** (1) Looks up the CCN via `hcris.py` name search or exact CCN match; (2) pulls all `hospital_benchmarks` rows for that CCN across all sources; (3) merges fields in priority order: analyst-entered > IRS 990 > Care Compare > HCRIS, with provenance tagging at each field; (4) infers missing fields using `data_scrub.py` winsorization and peer-median fallbacks; (5) returns a `HospitalProfile` dict with every field tagged `{value, source, confidence}`.

**Data in:** `hospital_benchmarks` SQLite table (all four sources); analyst-entered overrides from `deals/deal_overrides.py`.

**Data out:** `HospitalProfile` dict fed into `packet_builder.py` step 1.

---

## `benchmark_evolution.py` — Year-Over-Year Benchmark Drift Tracker

**What it does:** Tracks year-over-year shifts in benchmark medians (e.g., "denial rate P50 has moved from 9.2% to 8.1% since last year"). Flags when a benchmark has shifted enough to warrant re-marking open deals.

**How it works:** Queries `hospital_benchmarks` for the same metric across two consecutive `period` values. Computes the absolute and percentage shift in P25/P50/P75. Flags metrics where P50 shifted >1pp (for rate metrics) or >5% (for dollar metrics). Returns a `BenchmarkDriftReport` used by `analysis/refresh_scheduler.py` to identify stale analyses.

**Data in:** `hospital_benchmarks` table across multiple `period` values (annual snapshots).

**Data out:** `BenchmarkDriftReport` for the data status page and stale analysis detection.

---

## `claim_analytics.py` — Claim-Level Denial and Aging Analytics

**What it does:** Computes denial rates by payer and root cause, top denial reason distributions, and A/R aging bucket analysis from the deal's uploaded claim records.

**How it works:** Queries the `claim_records` table (populated by `ingest.py` when a seller provides claim data). Groups by payer class and denial reason code. Computes initial denial rate (IDR), final write-off rate (FWR), and overturn rate per payer. Builds A/R aging buckets (0–30, 31–60, 61–90, 90+ days). Returns a `ClaimAnalytics` dict with per-payer breakdowns for the RCM Profile tab.

**Data in:** `claim_records` SQLite table populated by `data/ingest.py` from seller-provided claim data.

**Data out:** Per-payer denial and aging analytics for the RCM Profile tab.

---

## `document_reader.py` — Seller File Metric Extractor

**What it does:** Extracts RCM metrics from seller-provided Excel, CSV, and TSV files using alias-aware column matching. Handles the hundreds of different column names sellers use for the same metrics.

**How it works:** Opens the file (Excel via `openpyxl`, CSV/TSV via stdlib `csv`). Applies the alias table from `core/_calib_schema.py` to map raw column headers to canonical metric keys. Extracts values, validates numeric formats, and applies range checks. Returns an `ExtractionResult` with the extracted metrics tagged `MetricSource.EXTRACTED` and a confidence score based on the alias match quality. Column matches are logged so the analyst can verify the mapping.

**Data in:** Seller-uploaded Excel/CSV/TSV files from the deal's data room; alias table from `core/_calib_schema.py`.

**Data out:** `ExtractionResult` with canonical metric values → fed into `packet_builder.py` step 2 as `MetricSource.EXTRACTED` values.

---

## `edi_parser.py` — EDI 837/835 Claim Data Parser

**What it does:** Parses EDI 837 (claim submission) and 835 (remittance/EOB) files to extract denial reasons, payment amounts, and adjustment codes for analytics.

**How it works:** Reads the EDI file in line-by-line segment mode (ISA/GS/ST loop structure). Extracts CLP/SVC/CAS segments from 835 files for denial reason codes (CARC codes) and adjustment amounts. Extracts CLM/SV1 segments from 837 files for claim amounts and service codes. Maps CARC codes to the platform's canonical denial reason taxonomy. Returns a `ClaimBatch` suitable for insertion into `claim_records`.

**Data in:** EDI 835/837 files uploaded by the seller or extracted from a clearinghouse export.

**Data out:** `ClaimBatch` objects → `claim_records` table via `ingest.py`.

---

## `geo_lookup.py` — City/State to Lat/Lon

**What it does:** Resolves city/state strings to approximate latitude/longitude coordinates for portfolio map plotting.

**How it works:** Uses a lookup table of US state capital centroids (50 entries) as fallbacks for city-level resolution. For non-capital cities, applies a city→centroid dict built from HCRIS provider address data. Returns `(lat, lon)` tuples for the `/portfolio/map` visualization. Does not make any external geocoding API calls.

**Data in:** Hospital address strings from `hospital_benchmarks` HCRIS records.

**Data out:** `(lat, lon)` tuples for the portfolio map SVG renderer.

---

## `ingest.py` — Seller Data Pack Ingestion CLI

**What it does:** The `rcm-mc ingest` command. Turns messy seller data packs (Excel, zip archives, folders of CSVs) into three canonical calibration YAML files (`actual.yaml`, `benchmark.yaml`, `calibration.yaml`) that the MC simulator can consume.

**How it works:** Accepts a path to a zip, Excel, or folder. Discovers files using extension matching. Routes Excel files through `document_reader.py`, CSV/EDI files through `edi_parser.py` or `claim_analytics.py`. Assembles the extracted metrics into the canonical YAML structure. Applies `data_scrub.py` to winsorize outliers. Writes three YAML files to a timestamped output directory. Logs every source field and extraction step for audit.

**Data in:** Seller-provided data pack (zip/Excel/CSV/EDI) from the file path argument.

**Data out:** `actual.yaml`, `benchmark.yaml`, `calibration.yaml` in the output directory.

---

## `intake.py` — Interactive 11-Prompt Intake Wizard

**What it does:** An interactive terminal wizard that collapses a 131-field YAML configuration surface into an 11-question analyst session (5 minutes). Used when a seller file isn't available and the analyst is entering parameters manually.

**How it works:** Presents 11 prompts covering: hospital name/CCN, revenue, bed count, payer mix (commercial/Medicare/Medicaid), key RCM metrics (denial rate, AR days, collection rate, CMI), and investment thesis. Auto-populates remaining fields from HCRIS benchmarks using `auto_populate.py`. Validates each input and offers retry on invalid entries. Writes a complete YAML config file at the end.

**Data in:** Analyst keyboard input; HCRIS auto-populate data from `auto_populate.py`.

**Data out:** Complete YAML config file for the MC simulator.

---

## `irs990.py` — IRS Form 990 Cross-Check (Non-Profit Hospitals)

**What it does:** Fetches IRS Form 990 data for non-profit hospitals via the ProPublica Nonprofit Explorer API and cross-checks charity care and bad debt figures against HCRIS.

**How it works:** Calls `https://projects.propublica.org/nonprofits/api/v2/search.json` with NTEE codes E20/E21/E22 (general, specialty, rehab/psych hospitals). Extracts charity care dollars, Medicare/Medicaid surplus/loss, and executive compensation. Flags cases where the 990's charity care differs from HCRIS by >15% (common when hospitals use different accounting bases). Returns a `IRS990Report` with the cross-check flags.

**Data in:** ProPublica Nonprofit Explorer API — public, no authentication for most queries. Requires a seeded `ein_list.json` for the hospital universe.

**Data out:** `IRS990Report` with charity care cross-check flags; feeds `auto_populate.py` for non-profit hospital profiles.

---

## `irs990_loader.py` — IRS 990 Benchmark Database Loader

**What it does:** Normalizes IRS 990 data into `hospital_benchmarks` rows. Complements HCRIS with charity-care and bad-debt figures that HCRIS doesn't carry cleanly.

**How it works:** Wraps `irs990.py` API calls. Extracts the 990's Schedule H (hospital community benefit) fields: charity care cost, unreimbursed Medicaid, Medicare surplus/loss, bad debt expense. Normalizes to `hospital_benchmarks` rows with `source='irs990'` and the fiscal year end as `period`. Uses `UNIQUE` upsert to avoid duplicates on re-runs.

**Data in:** ProPublica API responses from `irs990.py`; EIN-to-CCN mapping from `ein_list.json`.

**Data out:** `hospital_benchmarks` rows with charity care and bad-debt metrics per hospital per year.

---

## `lookup.py` — rcm-lookup CLI

**What it does:** The `rcm-lookup` command — a fast terminal browser for CMS HCRIS data. Lets analysts find hospitals by CCN, name fragment, state, or bed-count range.

**How it works:** Wraps `hcris.py` search functions with a formatted terminal output table using `infra/_terminal.py` ANSI helpers. Supports `--ccn`, `--name`, `--state`, `--min-beds`, `--max-beds` flags. Outputs a terminal table with CCN, name, state, beds, NPR, and key metrics. Used during the intake process to find the right CCN before running intake.

**Data in:** Bundled `hcris.csv.gz`; CLI flag arguments.

**Data out:** Formatted terminal table of matching hospitals.

---

## `market_intelligence.py` — Competitor and Market Concentration Analysis

**What it does:** Finds competitor hospitals within a configurable radius and computes HHI market concentration for a target hospital's service area.

**How it works:** Uses Haversine distance formula on state-centroid coordinates from `geo_lookup.py`. Finds all HCRIS hospitals within the specified radius. Computes HHI as `Σ(market_share²)` where market share is based on discharge volume. Returns a `MarketProfile` with competitor names, distances, HHI score, and market structure classification (monopoly / oligopoly / competitive).

**Data in:** Target hospital coordinates from `geo_lookup.py`; competitor hospitals from `hospital_benchmarks` HCRIS data; discharge volumes from `cms_utilization.py`.

**Data out:** `MarketProfile` for the deal workbench Market tab.

---

## `sec_edgar.py` — SEC EDGAR Public Company Loader

**What it does:** Fetches revenue, EBITDA margin, and leverage data from SEC EDGAR XBRL filings for ~25 public hospital systems. Used for peer valuation analysis against publicly traded operators.

**How it works:** Constructs the EDGAR XBRL API URL for each covered ticker (HCA, Tenet, CYH, UHS, etc.). Parses the JSON XBRL response for `us-gaap:Revenues`, `us-gaap:OperatingIncomeLoss`, and `us-gaap:LongTermDebt` tags across the last 8 quarters. Normalizes to annual EBITDA margin and net leverage. Caches results for 24 hours to avoid repeated API calls.

**Data in:** SEC EDGAR XBRL API — public, no authentication required.

**Data out:** Public operator financial benchmarks for `data_public/peer_valuation.py`.

---

## `sources.py` — Config Parameter Provenance Tagger

**What it does:** Tags each parameter in a simulation config as `observed`, `prior`, or `assumed`, making it clear to the analyst which inputs came from real data and which are defaults.

**How it works:** Iterates the config dict and cross-references each field against: the analyst's intake answers (observed), the HCRIS auto-populate results (prior from public data), and the default YAML values (assumed). Returns an annotated config dict with a `_provenance` sub-dict matching the config structure. Used by `infra/provenance.py` for the run provenance manifest.

**Data in:** Simulation config dict; intake answers; auto-populate results.

**Data out:** Annotated config dict with per-field provenance tags.

---

## `state_regulatory.py` — State Regulatory Registry

**What it does:** Provides state-level regulatory context: Certificate of Need (CON) laws, Medicaid expansion status, rate-setting regulations, and commercial market concentration for each state.

**How it works:** Static lookup table (a Python dict) with entries for all 50 states. Each entry has: `con_law` (True/False), `medicaid_expanded` (True/False), `rate_setting` (all-payer / selective / none), `medicaid_managed_care_penetration` (%), `commercial_hhi` (market concentration score). Used by `risk_flags.py` for regulatory risk assessment and by `pe_intelligence/` modules for state-level regulatory exposure analysis.

**Data in:** Static data compiled from CMS and KFF state policy databases (updated manually with each CMS rule change).

**Data out:** State regulatory context dict for `risk_flags.py` and `pe_intelligence/` modules.

---

## `system_network.py` — Hospital System Network Graph

**What it does:** Builds a hospital system network graph and finds standalone hospitals near a target system's existing footprint — identifying potential add-on acquisition targets.

**How it works:** Loads system affiliation data from HCRIS (`system_id` field). Groups hospitals by system. For a target system, identifies all member hospitals and computes Haversine distances to all non-member hospitals. Applies filters for bed count and payer mix fit. Returns a `NetworkAnalysis` with the system's current footprint map and top candidate add-on targets.

**Data in:** `hospital_benchmarks` HCRIS system affiliation and location data.

**Data out:** `NetworkAnalysis` for the portfolio strategy panel.

---

## `team.py` — Management Team Data

**What it does:** Stores and retrieves management team profiles for portfolio companies, including tenure, prior experience, and analyst notes.

**How it works:** CRUD layer over the `management_team` SQLite table. Fields: name, title, deal_id, tenure_months, prior_experience (JSON), analyst_notes, flag_for_review. Used by `pe_intelligence/management_assessment.py` for management quality scoring.

**Data in:** Analyst-entered management team data via the deal page.

**Data out:** Management team profiles for `pe_intelligence/management_assessment.py` and the deal overview page.

---

## `data_scrub.py` — Board-Ready Data Scrubbing

**What it does:** Winsorizes outliers, standardizes naming conventions, and caps EBITDA drag artifacts before they enter the simulation engine or reports.

**How it works:** Applies metric-specific winsorization bounds (e.g., denial rate capped at 35%, AR days capped at 120). Standardizes payer names using the alias table. Caps implausibly large EBITDA impacts (>50% of NPR gets flagged and capped at 40%). Logs every scrubbing action for audit. Returns the scrubbed config dict with a `ScrubLog` listing all modifications.

**Data in:** Raw metric dict from `ingest.py` or `auto_populate.py`.

**Data out:** Scrubbed metric dict; `ScrubLog` for the analyst review UI.

---

## `disease_density.py` — Disease Prevalence and Service Density

**What it does:** Estimates disease prevalence and healthcare service density for a hospital's service area, providing context for revenue growth projections.

**How it works:** Maps the hospital's county/MSA to CDC chronic disease prevalence data (diabetes, heart disease, COPD rates). Estimates the addressable patient population for the hospital's service lines using population and market share data. Returns a `DiseaseDensityProfile` used by `pe_intelligence/` for market growth thesis assessment.

**Data in:** County-level CDC disease prevalence data (static table updated annually); HCRIS service area estimates.

**Data out:** `DiseaseDensityProfile` for pe_intelligence market analysis modules.

---

## `drg_weights.py` — CMS DRG Relative Weights

**What it does:** Provides CMS DRG relative weight lookup (the weight that determines Medicare payment for each diagnosis-related group) for CMI and revenue modeling.

**How it works:** Loads the CMS annual IPPS DRG weight table (static CSV bundled with the package, updated annually). Provides `get_weight(drg_code)`, `get_geometric_mean_los(drg_code)`, and `compute_case_mix_index(drg_volume_dict)` functions. Used by `cms_utilization.py` for CMI computation and by `pe_intelligence/CMI_uplift.py` for CDI impact modeling.

**Data in:** Bundled CMS IPPS DRG weight table CSV (updated manually each fiscal year).

**Data out:** DRG weights and CMI calculations for analytics and pe_intelligence modules.

---

## `data_room.py` — Deal Data Room Document Index

**What it does:** Indexes and tracks documents uploaded to a deal's virtual data room: management presentations, financial statements, billing system reports, payer contracts.

**How it works:** CRUD layer over the `data_room_documents` SQLite table. Tracks: document name, type (CIM / financials / billing_report / payer_contract / etc.), upload timestamp, analyst, and extraction status (pending / extracted / failed). Integrates with `document_reader.py` to trigger metric extraction on upload. Used by the `/data-room/<deal_id>` UI page.

**Data in:** Analyst-uploaded documents via the deal page data room tab; extraction results from `document_reader.py`.

**Data out:** Document index for the data room UI; triggers `document_reader.py` extraction pipeline.

---

## `pipeline.py` — Data Ingestion Pipeline Orchestrator

**What it does:** Orchestrates the full data ingestion pipeline for a new deal: from uploaded files through to a complete, calibrated `DealAnalysisPacket` build.

**How it works:** Sequences: (1) file detection and routing (Excel → `document_reader`, EDI → `edi_parser`, YAML → direct load); (2) metric extraction and scrubbing; (3) HCRIS auto-populate for missing fields; (4) calibration (if claim data present); (5) packet build trigger. Returns a `PipelineResult` with step-by-step status and a pointer to the built packet.

**Data in:** Uploaded file paths; deal_id for the portfolio store.

**Data out:** Calibrated config files → triggers `packet_builder.py` for a full analysis run.

---

## `_cms_download.py` — Shared CMS Download Helper

**What it does:** Shared download utility for all CMS data loaders. Handles atomic fetch, respectful retry (3 attempts with exponential backoff), cache directory management, and gzip decompression.

**How it works:** `download_file(url, dest_path)` — downloads to a `.tmp` file, verifies by size, then renames atomically. `download_if_stale(url, dest_path, max_age_days=7)` — skips download if cached copy is fresh. Respects `NO_CMS_DOWNLOAD=1` environment variable for CI/test isolation. User-agent string identifies the tool to CMS.

**Data in:** CMS download URLs from the loader modules; local cache directory.

**Data out:** Downloaded and decompressed file at the destination path.

---

---

## Public-data expansion cycle (Apr 2026)

Four new public-data ingestion surfaces shipped in the most recent autonomous-loop cycle, plus a unified data-catalog UI surface that surfaces every data source the platform understands.

### `cdc_places.py` — CDC PLACES + NVSS county-level health

**What it does:** Loads CDC PLACES county-level chronic disease prevalence (diabetes, COPD, heart disease, etc.) plus NVSS mortality and natality summaries. Used as a market-context overlay on `portfolio_map` and as a covariate in `geographic_clustering`.

**How it works:** Streams PLACES annual CSV (~500MB) by chunk; normalizes 28 health indicators into the `county_health` SQLite table keyed by FIPS. Uses `_cms_download.py` retry logic. Schema-drift tolerant.

### `state_apcd.py` — State All-Payer Claims Database loaders

**What it does:** Ingests publicly-released State APCD aggregates from the ~12 states that publish them (CO, MA, NH, OR, RI, UT, VT, etc.). Each state's schema differs; this module normalizes to a common `apcd_aggregate` row schema.

**How it works:** Per-state adapters with a registry (`APCD_STATES`). Each adapter handles its state's quirks (CO uses provider TIN, MA uses license number, OR uses internal IDs) and emits normalized rows. Schema-drift defended by alias tables and graceful column-name fallbacks.

### `ahrq_hcup.py` — AHRQ HCUP NIS / NEDS

**What it does:** Loads the AHRQ HCUP National Inpatient Sample (NIS) and National Emergency Department Sample (NEDS) public-use files. Drives the service-line volume forecaster and cross-subsidy analysis.

**How it works:** HCUP files are large fixed-width SAS exports; this module uses a coordinate table to extract the columns we actually use (DRG, age, payer, charges, LOS, mortality flag) and writes to `hcup_discharge` partitioned by year + state.

### `cms_ma_enrollment.py` — CMS Medicare Advantage enrollment + Star ratings

**What it does:** Loads CMS Medicare Advantage county-level enrollment penetration (the share of Medicare beneficiaries enrolled in MA plans), plan Star ratings, and benchmark payments. Critical for the V28 coding-compression risk model and the regulatory calendar's MA exposure overlay.

**How it works:** Three CMS endpoints — Monthly Enrollment, Plan Ratings, MA Benchmark Payments — with `_cms_download.py`. Star ratings dimensionalized by contract × plan × year. Benchmark payments normalized to per-bene per-month for cross-county comparison.

### `catalog.py` + `/data/catalog` — Data catalog page

**What it does:** Surfaces the **full data estate** of the platform on a single page: every source, the modules it powers, last-refresh timestamp, row count, schema-drift status. Eliminates the "what data does this tool know about?" question.

**How it works:** Reads from `data_source_log` plus a static registry of source metadata (`CATALOG_SOURCES`). Renders a `power_table` with sortable columns + status badges (fresh / stale / missing). UI lives in `ui/data_catalog_page.py`.

---

## Key Concepts

- **No runtime network calls for core analysis**: Public data ships pre-parsed in `hcris.csv.gz`; external refreshes are explicit analyst actions via `rcm-mc data refresh`.
- **Alias-aware column matching**: Seller files use hundreds of different column names for the same metrics — the alias table in `core/_calib_schema.py` handles the mapping.
- **Per-field provenance**: Every auto-populated value is tagged with its source (`HCRIS / care_compare / irs990 / analyst`) so the analyst can defend each number in IC.
- **Partial failure tolerance**: One broken CMS source never blocks the others — `data_refresh.py` runs each loader independently.
- **Schema drift defense**: Every loader carries an alias table and graceful column-name fallbacks so a CMS or state APCD schema change doesn't break the loader silently.
