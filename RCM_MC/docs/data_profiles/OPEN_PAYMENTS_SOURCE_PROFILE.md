# Source Profile — CMS Open Payments (staged)

**Source:** CMS Open Payments (`openpaymentsdata.cms.gov`, `download.cms.gov/
openpayments/`). Public, no license restriction. Annual program years.
**What it is:** industry (drug/device manufacturer & GPO) payments and
transfers of value to physicians/teaching hospitals — the canonical
financial-relationship / conflict-of-interest dataset.

## Grain & size
- **Detail "General Payments"**: one row per payment — **multi-GB per year**
  (millions of rows, PII-bearing recipient identifiers). NOT ingested whole.
- **Pre-aggregated summary files** (`SMRY_RPTS_…`): small, public, no PII.
  - *By reporting entity × nature-of-payment* (`…BY_AMGPO_BY_NTR_OF_PYMT…`):
    **6,484 rows** for PGYR2023; columns `AMGPO_ID, Nature_Of_Payment_Type_Code,
    Number_of_Transaction, Total_Amount, AMGPO_Name`. ~$3.31bn total 2023.
  - Also: by covered-recipient×nature, by reporting-entity, etc.

## Staged ingest (this PR)
Ingest the small **by-entity×nature summary** and commit two PII-free aggregates:
- **National total** (sum $ + transactions across all entities/natures).
- **Top reporting entities (manufacturers/GPOs) by total payments** — name +
  total $ + transaction count. Public-company names; no recipient PII.
Nature-of-payment dimension is captured by **code** only in the source summary;
the authoritative **code→label map is a documented follow-up** (the grouped
summary ships codes; labels live in the detail file's text column). We do NOT
guess labels for a conflict-of-interest dataset.

## Use cases
- Specialist/physician industry pages: scale of industry financial ties.
- Partner economics / provider-profile context: manufacturer-relationship scale.
- Guide: "how large are industry→physician financial relationships?"

## Full-ingest plan (deferred; needs go-ahead for size)
To get recipient-level / specialty-level / nature-labeled detail, stage the
detail "General Payments" file per year (multi-GB): stream + aggregate to
state×specialty×nature totals, drop recipient PII, commit only aggregates.
Command pattern: `curl <detail year zip>` → chunked pandas aggregate. Deferred
until approved due to size; the summary aggregate above is live now.

## Provenance / honesty
Public CMS data; manufacturer names are public entities (no recipient PII in
the committed aggregate). National/industry context — NOT provider-specific and
NOT a wrongdoing flag (disclosure is lawful and routine).
