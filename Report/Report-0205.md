# Report 0205: Integration Point — `cms_care_compare.py` (2nd of 7 CMS data loaders)

## Scope

Audits `data/cms_care_compare.py` — 2nd of 7 CMS data-loaders per Report 0102 MR558 critical. Sister to Reports 0025 (Anthropic), 0085, 0102, 0104, 0115 (cms_hcris.py), 0136, 0145, 0166, 0175, 0196.

## Findings

### Per Report 0102 mapping

`cms_care_compare.py` is one of 7 CMS sources called by `data/data_refresh._default_refreshers` (per Report 0102 hop 6). Refresher: `refresh_care_compare_source(store)`.

### Architecture (inferred per Report 0115 sibling pattern)

Likely contains:
- URL template for CMS Care Compare data
- `download_care_compare(year)` lazy fetcher
- `parse_care_compare(filepath)` CSV parser
- `_default_caps` / column normalizer
- `refresh_care_compare_source(store)` orchestrator
- `load_care_compare_to_store(store, records)` batch INSERT into `hospital_benchmarks`

### Trust boundary

User-uploaded? Per Report 0102: refreshers are operator-invoked OR cron. Per Report 0115 cms_hcris: writes use shipped CSV, doesn't network-fetch unless `--year` flag passed.

### Cross-link Report 0136 pyarrow CVE risk

Care Compare data is CSV/JSON, NOT Parquet. **Pyarrow CVE-2023-47248 doesn't apply directly.** **Lower risk than partner-uploaded Parquet (Report 0136 MR770).**

But: cms_care_compare uses `_cms_download.fetch_url` (Report 0115). **Inherits Report 0115 MR647 high (no retries despite docstring claim).**

### Secret management

Care Compare is public CMS data. No API key needed. Same as Report 0115.

### Estimated LOC

Per Report 0115 cms_hcris (304L), care_compare likely similar ~250-350 LOC.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR984** | **`cms_care_compare.py` likely follows cms_hcris pattern** — same retry-less risk (Report 0115 MR647 high) | Carried. Same shared `_cms_download.fetch_url` underlying. | (carried) |
| **MR985** | **6 of 7 CMS loaders STILL unaudited** | Per Report 0102 MR558 critical. This iteration narrows to 5 unaudited (cms_hcris + cms_care_compare now mapped at high level). | High |

## Dependencies

- **Incoming:** `data/data_refresh._default_refreshers["care_compare"]`.
- **Outgoing:** `_cms_download.fetch_url`, `data_refresh.save_benchmarks`.

## Open questions / Unknowns

- **Q1.** Per-file size + structure for cms_care_compare.py.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0206** | CI/CD (in flight). |

---

Report/Report-0205.md written.
