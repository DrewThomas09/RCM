# Industry Report Source Audit

Phase 0 inventory of the licensed IBISWorld industry reports that feed the
PEdesk **Industry Intelligence** layer. Raw PDFs live **only** on the licensee's
machine (`~/Desktop/Industry Information Pages/`) and are **not** committed —
PEdesk commits only derived, structured, attributed facts (see
[INDUSTRY_REPORT_LICENSE_POLICY.md](INDUSTRY_REPORT_LICENSE_POLICY.md)).

**Publisher:** IBISWorld (US industry research). **License:** purchased private
business license; PEdesk authorized for internal BI, diligence, benchmarking,
and generated industry briefs. Attribution required on every derived surface.

## Inventory

| IBIS code | NAICS | Report title | Published | Pages | PEdesk slug |
|---|---|---|---|---|---|
| 62 | 62 (sector) | Healthcare and Social Assistance in the US | Aug 2025 | 47 | `healthcare-social-assistance` |
| 62111a | 621111 | Primary Care Doctors in the US | Feb 2026 | 46 | `primary-care-doctors` |
| 62111b | 621112 | Specialist Doctors in the US | Mar 2026 | 46 | `specialist-doctors` |
| 62149 | 621491 / 6214 | Emergency & Other Outpatient Care Centers in the US | Jan 2026 | 46 | `outpatient-care-centers` |
| 62211 | 622110 | Hospitals in the US | Dec 2025 | 48 | `hospitals` |

## Standardized structure (extraction target)

All five reports share the IBISWorld standard layout. Confirmed sections:

- **About This Industry** — Definition, Codes (NAICS), What's Included,
  Companies, Related Industries, Related Terms
- **At a Glance** — Revenue, Employees, Businesses, Profit, Profit Margin,
  Wages (each with '21–'26 historic + '26–'31 forecast CAGR); Major Players;
  Products & Services mix (item · revenue · market share); Key External Drivers
  (driver · impact direction); Key Takeaways
- **Performance / Outlook / Life Cycle / Volatility**
- **Products & Markets** — segments, major markets, international trade
- **Geographic Breakdown** — business locations
- **Competitive Forces** — concentration, barriers, basis of competition
- **External Environment** — regulation, technology, external drivers
- **Financial Benchmarks** — Profit Margin, Average Wage, Largest Cost; Cost
  Structure (% of revenue, industry vs sector: Wages/Purchases/Profit/
  Depreciation/Rent/Marketing/Utilities/Other)
- **Key Statistics** — historical time series 2006→forecast (Revenue, IVA,
  Establishments, Enterprises, Employment, Wages)
- **Key Success Factors**

## Extraction quality

- **Text + tables**: machine-extractable via `pdfplumber` (no OCR needed for
  the numeric tables; At-a-Glance and Key Statistics extract cleanly).
- **Charts/figures**: some cost-structure bars render as graphics, but the same
  numbers appear in the adjacent "Cost Structure Benchmarks" table — extract the
  table, ignore the chart.
- **Confidence**: At-a-Glance metrics, Products/Services mix, Cost Structure,
  Key Statistics time series → high. Narrative drivers/SWOT → paraphrase only.

## Detected per-report data (validation examples)

- **Primary Care (621111)**: revenue $370.8bn, employees ~1m, businesses ~133k,
  profit $42.6bn, margin 11.5%, wages $142.0bn; segments Internal medicine 38.5%,
  Family/general 36.6%, Pediatric 23%, Geriatric 1.9%; drivers private insurance
  (+), Medicare/Medicaid funding (+), disposable income.
- **Specialist Doctors (621112)**: OB/GYN, anesthesiology, psychiatry,
  ophthalmology, cardiology segments; drivers private insurance, adults 65+,
  total health expenditure, Medicare/Medicaid funding.
- **Outpatient (62149)**: freestanding ambulatory surgical & emergency centers,
  HMO medical centers, kidney dialysis centers, other outpatient care.
- **Hospitals (622110)**: general medical & surgical hospitals; inpatient,
  outpatient, other.
- **Healthcare & Social Assistance (62)**: broad sector roll-up.

## Recommended normalized output

`data/industry_intel/` — `industry_reports.json` + per-fact CSVs
(`industry_metrics`, `industry_segments`, `industry_drivers`,
`industry_benchmarks`, `industry_risks`, `industry_questions`,
`industry_related`, `industry_terms`). Every row carries provenance
(source_file, report_title, publisher, publication_date, industry_code, section,
page, value_type, confidence, license_note). Loaders read the committed derived
files only — no runtime PDF parsing, no raw PDF in the repo.
