# Source Profile — NPPES / NPI Registry (staged; full ingest deferred)

**Source:** CMS NPPES (National Plan & Provider Enumeration System) Data
Dissemination, public (`download.cms.gov/nppes/`). Every NPI (providers +
organizations) with taxonomy, practice address, enumeration date.

## Grain & size — why full ingest is deferred
- **Full monthly dissemination file: ~9 GB unzipped** (~8M NPIs, ~330 columns
  incl. up to 15 taxonomy slots + addresses). Downloading + parsing the whole
  file is not feasible in this build environment without a staged large-file
  job. **Deferred** pending a go-ahead for the large download.
- The per-NPI **API** (`npiregistry.cms.gov/api`) is lookup-only (not bulk
  aggregation), so it can't produce supply-by-geography aggregates.

## What already covers the immediate need
Provider **supply by state × type** is already live via
`rcm_mc/data/provider_supply.py` (CMS FFS Provider Enrollment — 2.98M enrolled
providers). NPPES would add: non-Medicare providers, full **taxonomy/specialty**
granularity, and **entity resolution** (NPI ↔ org ↔ CCN).

## Staged full-ingest plan (when approved)
1. `curl` the monthly NPPES file (`NPPES_Data_Dissemination_<MON>_<YYYY>.zip`,
   ~9 GB) to scratch.
2. Stream with `pandas` `chunksize`, read ONLY: NPI, entity type, primary
   taxonomy code, practice state. Drop names/addresses (PII).
3. Aggregate to **provider count by state × primary-taxonomy** (a few thousand
   rows) + a taxonomy reference.
4. Commit only the aggregate; loader + tests + Guide card; wire to market-intel
   provider supply (richer than the FFS proxy) and specialist industry pages.
5. Exact command + ~9 GB size + scratch-space requirement documented here for
   approval before running.

## Honesty
Until the staged ingest is approved/run, NPPES renders nowhere as data; the FFS
Provider Enrollment supply layer is the live proxy and is labeled as such.
