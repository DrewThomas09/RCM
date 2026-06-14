# openFDA connector — DECISIONS

_When uncertain (schema ambiguity, missing field, paging edge case, mapping
choice), we record the call and its rationale here and keep going. The
pipeline appends to this file at runtime; the entries below are the standing
design decisions made while building the slice._

## Runtime / dependency decisions

- **Stdlib only, no pandas/pyarrow/duckdb.** This repo's runtime is
  stdlib-heavy and adds no new dependencies. The connector uses
  `urllib` + `json` + `sqlite3` + `time` only. Verified live: `pandas`,
  `pyarrow`, and `duckdb` are not importable in the target environment.

- **Raw landing: parquet when available, else JSONL.** The contract says
  "land raw to parquet". Parquet needs `pyarrow`, which is absent here, so
  `raw_store` degrades to newline-delimited JSON and transparently writes
  parquet if `pyarrow` is ever installed. Either way raw bytes are kept
  verbatim and the write is atomic (temp file + replace) so a hard kill
  never leaves a half-written window.

- **Normalized store is SQLite**, matching the rest of RCM-MC. One store
  object owns the connection. Every column is TEXT so the uniform
  `/v1/query` layer has a single type model; numeric comparisons cast.

## Paging / backfill decisions

- **Deep paging via adaptive date windows.** openFDA caps `limit` at 1000
  and refuses `skip` past ~25,000. For dated endpoints we chunk history
  into date windows, page `skip` inside a window, then advance. Windows are
  adaptive: a window whose total exceeds the safe cap (25000 − 1000) is
  halved and retried; a comfortably-drained window grows back toward the
  30-day default. The cursor is JSON and persisted every step, so a kill
  resumes exactly.

- **Non-dated endpoints (`drug_ndc`, `drugsfda`, `device_classification`)**
  have no usable event date. They page by `skip`; if they ever exceed the
  skip cap they fall back to partitioning by a categorical field
  (`partition_field`) discovered via `count=`, draining each partition
  value separately. Documented because it is the one place we depart from
  pure date-window chunking.

- **`search_after` not used.** openFDA does not offer a stable
  `search_after`/cursor; the documented workaround is `skip` within bounded
  windows, which is what we implement. `supports_search_after` stays False.

- **Single-slice truncation is surfaced, not hidden.** If a single day (or
  single partition value) still exceeds the skip cap, the connector pulls
  what it can, sets `truncated=True`, and the pipeline logs the gap here.
  The DQ count-reconciliation check will flag the shortfall.

- **Live paging not verified in this build.** The brief asks to verify
  current paging behavior live before a bulk run. The build environment has
  no egress to `api.fda.gov` (HTTP 403 from the network policy), so the
  state machine is verified instead against an in-memory fake server that
  models `limit`/`skip`/`total`/`count=`/date-range search. **Before the
  first production bulk run, re-confirm the live skip ceiling and rate
  limits at https://open.fda.gov/apis/ and adjust `SKIP_CAP` /
  `min_interval_s` if they have changed.**

## Rate-limit decisions

- **Limits are not hard-coded as policy.** The transport uses a
  conservative default inter-request floor (~0.30 s ≈ 200 req/min, under
  the ~240 ceiling) and reads the key from `$OPENFDA_API_KEY`, degrading
  gracefully when absent (just a lower cap, never an error). HTTP 429 and
  5xx use exponential backoff + full jitter and honour `Retry-After`.

## Schema / mapping decisions

- **`dim_device` is keyed by native id, not by `product_code`.** The
  target schema lists "applicant, decision date and type", i.e. per-
  submission rows. So each 510(k) (`K:<k_number>`), PMA
  (`PMA:<pma>-<supplement>`), and classification (`CLASS:<product_code>`)
  is its own row, with `product_code` as the rollup dimension. This
  preserves the **clearance timeline by product_code** (filter
  `product_code`, order `decision_date`) the diligence value depends on.
  The `xwalk_device_product_code` table rolls these up to one row per
  product_code with a clearance count + earliest decision date.

- **`fact_device_recall` keys are prefixed by source** (`RES:` for
  `device/recall`, `ENF:` for `device/enforcement`) because the two
  endpoints use different native id schemes; prefixing prevents an
  accidental key collision while both feed one canonical table.

- **`drug_label` enriches `dim_drug_product`** by fanning out over
  `openfda.product_ndc`; `drug_ndc` is the primary source. Upsert merges
  the two per NDC.

- **NDC carried as the native `product_ndc` string.** An 11-digit form
  (`ndc11`) is exposed for RxNorm; with only a product NDC (labeler-product,
  no package segment) we pad to 5-4 (9 digits) and note the package gap —
  full NDC11 needs the package segment, available on `packaging[]` if a
  later pass needs exact RxNorm NDC matching.

- **Company rollup is a deterministic normalization**, not a probabilistic
  matcher: lower-case, strip corporate suffixes (Inc/LLC/Corp/Pharma/…) and
  punctuation, collapse whitespace → `company_key`. This is the testable,
  reproducible form of the "fuzzy match so records roll up to a company"
  requirement; variants like "Acme Pharma, Inc." and "ACME PHARMACEUTICALS
  LLC" land on `co_acme`. A fuzzier matcher can layer on later without
  changing the key contract.

## Crosswalk decisions

- **NDC→RxCUI is deferred when no RxNorm session has run.** The default
  resolver returns nothing; `xwalk_ndc_rxcui` rows are written with
  `resolution_status='deferred_no_rxnorm'` and `dim_drug_product.rxcui`
  stays NULL. The join is fully wireable — a later RxNorm session passes a
  real `ndc → rxcui` resolver and back-fills without re-ingesting. We never
  block drug ingestion on RxNorm. The DQ layer reports coverage %.

- **We append, never rewrite, the crosswalk contract.** This workstream
  adds the device `product_code` dimension (`xwalk_device_product_code`)
  and the NDC→RxCUI table. NPI, NUCC, FIPS, CPT/HCPCS, MS-DRG, and NDC
  themselves are untouched.

## Router decisions

- **`/v1/query/{dataset}` is registry-driven**; adding a dataset is a
  registry row derived from an `EndpointSpec`, not new routing code.
- **The two `/v1/lookup` handlers are provided as plain callables + a
  router-agnostic `v1_handlers()` map** so a router that supports plugin
  registration can mount them without core edits — the only condition under
  which the brief permits adding them. No router core was modified; if no
  pluggable router exists yet, the handlers remain usable directly and via
  the CLI.

## Unmapped fields

The normalizer records first-level fields present on raw records that it
does not place, and the pipeline appends them here at runtime (with counts)
so schema drift surfaces instead of silently dropping. Raw is retained in
the lake, so any unmapped field can be mapped later without re-fetching.

## Incremental watermark (operational)

- **Nightly incrementals resume from a per-endpoint high-watermark**, not a
  fixed lookback. After each run the pipeline records the max value of the
  endpoint's `date_field` seen (`EndpointState.high_watermark`); the next
  incremental seeds the connector start at `watermark - incremental_overlap_days`
  (default 2). The overlap re-pulls a small tail to catch late-arriving
  records; idempotent upsert absorbs the duplicates. A missed night
  therefore self-heals — the window simply stretches back to the last
  watermark. First incremental (no watermark yet) falls back to
  `incremental_lookback_days`. Both openFDA date encodings (`YYYYMMDD` and
  zero-padded `YYYY-MM-DD`) sort lexicographically and an endpoint uses
  exactly one, so a string `max` is a correct watermark.
