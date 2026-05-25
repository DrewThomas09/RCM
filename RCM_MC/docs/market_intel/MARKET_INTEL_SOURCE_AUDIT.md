# Market Intelligence Source Audit (I_Made_It)

Phase 0 inventory of the licensed SimplyAnalytics-derived market files in
`~/Desktop/I_Made_It/`. **Canonical data = the tabular exports.** Screenshots
are **design/variable references only** — never treated as data (no pixel OCR
when an export exists; values are not transcribed from map legends into the
product).

**Source system:** SimplyAnalytics (licensed business account). **Use:** internal
PEdesk market intelligence, diligence, screening, generated analysis. Label:
`LICENSED MARKET DATA DERIVED` / `SIMPLYANALYTICS DERIVED`. Raw screenshots and
raw third-party files are **not** committed or publicly served.

## Files

| File | Type | Variable shown | Geo | Year | Ingestible? |
|---|---|---|---|---|---|
| `New Project_Ranking_2026-05-25_09-59-04.xlsx` | **Ranking export (XLSX)** | **% Age 65 years and over [Estimated]** | **State** (FIPS 2-digit) | 2025 | **YES — canonical** |
| `New Project_Map_…09-58-54.png` | Screenshot | % Age 65+ | County (choropleth) | 2025 | No (design ref) |
| `New Project_Map 2_…10-14-38.png` | Screenshot | Median Household Income | County | 2025 | No (design ref) |
| `New Project_Map 4_…10-37/38.png` | Screenshot | % Private Health Insurance by Sex/Age (B27002, Under 6) | County | 2023 | No (design ref) |
| `New Project_Map 5_…(8 variants).png` | Screenshot | % No Health Insurance (by Sex/Males) **+ NAICS 621111 provider-count markers** | County | 2025 | No (design ref) |

## Canonical export — schema

`SimplyAnalytics Export` sheet, 52 rows (50 states + DC + US), columns:
`Name`, `FIPS` (2-digit, leading zeros preserved as strings), `% Age | 65 years
and over, 2025 [Estimated]` (fraction 0–1). Ingests directly; no OCR.

## What the screenshots tell us (design + export backlog)

The screenshots confirm the **intended variable set** and the **map UI direction**
(US choropleth, red intensity scale, legend, county boundaries, provider-count
markers for NAICS 621111). They are the spec for the finished UI — not the data.

**Export backlog** (need the underlying SimplyAnalytics XLSX/CSV before these
become real data; until then they render as `EXPORT REQUIRED`, never fabricated):
- Median Household Income, 2025 — county
- % Private Health Insurance by Sex/Age (B27002), 2023 — county
- % No Health Insurance by Sex/Age, 2025 — county
- NAICS 621111 provider counts (primary-care physician offices) — county/marker

The county-level age-65+ map exists as a screenshot but the export we have is
**state-level**; county age-65+ values are therefore also `EXPORT REQUIRED`.

## Recommended use

Build the Market Intelligence layer now on the **one real variable** (state
% age 65+), architected as a multi-variable model so each new export drops in
with provenance. Compute national percentiles/ranks from real values only.
Screenshots stay in the licensee's folder (`.gitignore`d), referenced here for
UI design and the export backlog.
