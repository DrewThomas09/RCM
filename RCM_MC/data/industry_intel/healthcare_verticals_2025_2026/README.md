# Healthcare Verticals 2025–2026 — Chart-Ready Reference Bundle

A public-source synthesis of **17 specialized, adjacent & emerging US healthcare
verticals** for the 2025–2026 cycle, plus the structured datasets needed to chart it.

## Why this lives in its own subdirectory

The parent `data/industry_intel/` holds **licensed IBISWorld-derived** facts, keyed by
NAICS code and loaded by `rcm_mc/data/industry_intel.py` (which reads files *directly*
in that directory, not recursively). This bundle is a **different provenance class** —
`source_kind: PUBLIC_SOURCE_SYNTHESIS`, drawn from CMS payment rules, MedPAC, NIC MAP,
USRDS, SAMHSA, HRSA, CDC/NCHS ART, PHI, and named market-research estimates. Keeping it
in a subdirectory means:

- it never mixes into the NAICS-keyed CSVs or `industry_reports.json`, so the existing
  loader and its tests are untouched;
- the licensing note is unambiguous — nothing here is IBISWorld-derived.

## Files

| File | What it is | Charts it feeds |
|---|---|---|
| `healthcare_verticals_2025_2026.md` | The full narrative report (the source deliverable). | — |
| `verticals.csv` | Index of the 17 verticals: group, payment system, market size, payer, consolidation. | Overview tables |
| `payment_updates_2026.csv` | FY/CY2026 headline net payment updates (SNF, hospice, home health, ESRD). | Payment-update bar |
| `payment_buildup_2026.csv` | Rate build-up components for waterfall charts (SNF, home health). | Rate-build-up waterfalls |
| `unit_economics.csv` | Cross-vertical per-unit economics (per day/treatment/cycle/trip/dose). | Unit-economics synthesis bar |
| `gene_therapy_prices.csv` | Cell & gene therapy WAC list prices (16 rows). | Price bar, platform pie |
| `market_structure.csv` | Concentration / leader share by vertical. | Concentration bars/lines |
| `workforce.csv` | Direct-care and behavioral-health workforce figures. | Workforce-shortage bars |
| `sources.csv` | Authoritative data source per vertical. | Provenance/source maps |
| `chart_specs.json` | Machine-readable chart suggestions mapping visuals → datasets. | Chart generation |

## Conventions

- **Provenance on every row.** Each CSV carries `source` and `confidence` columns.
- **`confidence` values:** `high` (federal/company-reported), `medium` (ranges or
  market-research estimates), `low` (figure flagged as unverifiable in research — the
  metric and its source are recorded rather than a number fabricated).
- **Ranges are kept as ranges** (`value_low` / `value_high`), per the report's caveats —
  notably NEMT, CRO, and CDMO market sizes, and gene-therapy WAC vs. net prices.
- **`vertical_id`** is the stable join key across all files (see `verticals.csv`).

## Caveats (carried from the report)

Market-size figures vary widely by source and scope; gene-therapy list prices differ
materially from net/paid prices; some figures are dated (e.g., the $2.6B drug-development
cost is a 2014 Tufts estimate); and policy is in flux (SNF staffing-mandate rescission,
ETC termination, hospital-at-home extension to 2030). See the report's **Caveats**
section for the full list.

## Source kind

`PUBLIC_SOURCE_SYNTHESIS` — no licensed-report content; no runtime network. All facts
trace to a named public dataset or filing in `sources.csv` / the report body.
