# PEdesk dataset onboarding playbook

The repeatable engine for turning a new dataset into real, source-backed PEdesk
analytics. Every dataset follows the same path; the Colorado CIVHC payer files
(`rcm_mc/data/payer_data.py`) are the reference implementation.

## The loop, per dataset

1. **Profile** — sheets, rows, columns, sample rows, missingness, geography,
   identifiers, what it actually measures, what surfaces it can support. Do
   this before writing any code.
2. **Classify** — public/open vs licensed. Public/redistributable (CMS, CIVHC,
   state public-use) → normalized CSVs are committed under
   `rcm_mc/data/vendor/<group>/`. Licensed (Capital IQ) → git-ignored, loaded
   locally only (see `data/vendor/deal_library/.gitignore`).
3. **Register** — add a row to `rcm_mc/data/vendor/source_registry.csv`
   (source_id, publisher, geography, year, normalized_table, row_count,
   key_fields, product_surfaces_supported, missingness_notes, caveats,
   license_or_use_note). No dataset ships without a registry row.
4. **Normalize** — an offline `scripts/ingest_*.py` reads the source and writes
   tidy CSVs with canonical column names + a `source_id` column. Missing stays
   empty/NaN — never 0; nothing inferred from a blank.
5. **Load** — a `rcm_mc/data/<name>.py` module reads the vendored CSVs (no
   runtime network calls) and exposes summary/query helpers that report sample
   size and preserve missingness.
6. **Test** — datasets load, provenance present, missingness preserved, helpers
   work, no network.
7. **Connect** — wire the data into the diligence/vertical surfaces it supports,
   labeling each as LIVE / DERIVED / BENCHMARK / ESTIMATED / DATA-REQUIRED /
   ILLUSTRATIVE (see `PEDESK_DILIGENCE_ANALYTICS_ROADMAP.md`).
8. **Guide** — add a `docs/rag_sources/*.md` source card so the Guide can
   explain the source, its status, missingness, and what not to infer.

## Non-negotiables

- No fake/synthetic/invented values (rates, costs, APM %, provider matches,
  deal values, multiples, CMS IDs/NPIs). Missing stays missing.
- Estimates are labeled ESTIMATED with source inputs, method, peer group,
  sample size, and confidence — never written into observed/raw fields.
- No runtime network calls; ingestion is offline/build-time only.
- Don't force a dataset onto a vertical/page it doesn't actually cover.

## Reference implementation — Colorado CIVHC payer files

`scripts/ingest_payer_data.py` → `rcm_mc/data/vendor/payer_data/*.csv` →
`rcm_mc/data/payer_data.py`. Three public CIVHC (CO APCD) datasets: Cost of
Care (spend/PPPY by payer × region × claim type, 2017–21), APM adoption
(%FFS/%APM by payer × year, 2022–24), and Medicare Reference-Based Pricing
(provider-level % of Medicare, 2021–24). See `source_registry.csv` for
provenance and `docs/PEDESK_PUBLIC_DATA_SOURCE_REGISTRY.md` for the catalog.
