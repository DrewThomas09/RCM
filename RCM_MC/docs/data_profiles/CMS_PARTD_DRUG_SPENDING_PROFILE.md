# CMS Medicare Part D Spending by Drug — source profile

**Source:** CMS "Medicare Part D Spending by Drug" (data.cms.gov), public.
**Geography:** United States, national, per drug (brand × generic).
**Coverage:** 3,598 drugs; total 2023 Part D spend ~$275.9B; per-drug total
spend, claims, beneficiaries, **average spend per dosage unit** (the price
metric) and its **2019–2023 CAGR** + 2022→2023 change. Build-time snapshot;
runtime reads the committed aggregate (no live API).

**Why it anchors `/drug-pricing-340b`:** the 340B Drug Pricing Program exists
because outpatient drug prices and their growth pressure safety-net provider
economics. The real per-unit price CAGR (median ~1.8%/yr; N drugs >10%/yr) and
the most-expensive drugs (Eliquis, etc.) are the real cost backdrop the 340B
savings thesis sits on.

## Ingest → committed aggregate

`scripts/ingest_partd_drug_spending.py` → `rcm_mc/data/vendor/partd_drug/`:
`partd_drug_summary.json` (national totals + top lists), `partd_drug_top_spend.csv`,
`partd_drug_top_inflation.csv`. Loader: `rcm_mc/data/partd_drug.py` (`lru_cache`,
no runtime network). Registered `cms_partd_drug_spending`. Tests:
`tests/test_partd_drug.py`.

## Honesty caveats

- Part D **retail** spend — **NOT** 340B ceiling/acquisition prices.
- National, per-drug — **not** this deal's formulary or contract.
- Manufacturer "Overall" roll-up rows only (avoids double-counting); outliers
  flagged in source.

## Refresh

Bump the DY/URL in the ingest script when CMS publishes a newer data year.
