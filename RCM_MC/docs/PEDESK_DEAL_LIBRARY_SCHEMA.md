# PEdesk Deal Library — canonical schema

The Deal Library is PEdesk's normalized store of **companies (and, later,
transactions)** assembled from user-licensed market-data exports + public/CMS
enrichment. This documents the canonical schema the ingestion pipeline
(`scripts/ingest_deal_library_exports.py`) writes and the loader
(`rcm_mc/data/deal_library.py`) reads.

## Important: the first two exports are a COMPANY universe, not transactions

The profiled `Company Screening Report*.xls` files are Capital IQ **company**
screens (criteria: Health Care · Pending/Current/Prior **Sponsor-Backed** ·
US/Canada · Operating) — ~**12,265** rows combined (8,051 + 4,214). They carry
company-level fields only; there are **no** buyer / seller / announcement-date /
close-date / deal-value / multiple columns. So they populate
`deal_library_companies`, **not** a transactions table. A transactions table is
reserved for a future Capital IQ *Transactions* screen and is documented below
for completeness, but is **not** populated from a company screen (doing so
would require inventing deal fields — disallowed).

## `deal_library_companies` (populated now)

| field | notes |
|---|---|
| `company_id` | deterministic `dl_<sha1>` of source_system+file+clean_name+row |
| `source_system`, `source_batch_id`, `source_file`, `source_sheet`, `source_row_id` | full provenance |
| `company_name`, `clean_name` | clean_name is a normalized dedup/resolution key; **leading digits kept** (e.g. "100% …") |
| `ticker` | ~97% null (mostly private) |
| `industry` | CapIQ Industry Classifications |
| `ownership_status` | raw CapIQ owner string |
| `sponsor_owner` | **parsed PE sponsor** (prefers "(Current Sponsor)"); ~99% present |
| `company_status` | Operating / … |
| `website`, `address`, `geography`, `state` | state parsed deterministically from address/geography |
| `enterprise_value`, `ebitda`, `revenue`, `market_cap`, `amount_raised`, `employees` | $USDmm; **NULL when absent — never 0**. EV/EBITDA ~97% null, revenue ~74% null |
| `missing_fields` | `;`-joined list of empty core fields |
| `completeness_score` | `present_core_fields / total_core_fields` |
| `duplicate_candidate` | 1 if (clean_name, state) collides with an earlier row; conservative — nothing merged/dropped |
| `provenance_note` | human-readable source pointer |

**Core fields** for `completeness_score`: company_name, industry,
ownership_status, company_status, geography, revenue, enterprise_value,
website.

## `deal_library_sources`

`source_id, source_system, source_type, source_file, source_date,
license_scope_note, ingestion_date, notes` — one row per ingested export
(the manifest, see `data/vendor/deal_library/source_manifests/`).

## `deal_library_transactions` (future — Transactions screen only)

`deal_id, source_system, source_batch_id, source_file, source_sheet,
source_row_id, capiq_transaction_id, announcement_date, close_date, year,
target_company_name, target_clean_name, buyer_name, seller_name, sponsor_name,
deal_type, transaction_status, sector, subsector, healthcare_vertical,
geography, country, state, city, enterprise_value, revenue, ebitda,
ev_revenue_multiple, ev_ebitda_multiple, description, source_url_or_ref,
missing_fields, completeness_score, duplicate_candidate, provenance_note`.

## Honesty rules (enforced in the pipeline)

- Missing means unavailable → `None`/NULL, never 0; no value inferred from a blank.
- No invented EV / revenue / EBITDA / multiples / profiles.
- Public/CMS enrichment is added only when **traceable** (via the #685
  CapIQ→CMS entity-resolution layer) and is labeled as derived, never as an
  observed export fact.
- Licensed export rows are never relabeled as public data, and the raw/normalized
  licensed data is git-ignored (not redistributed).
