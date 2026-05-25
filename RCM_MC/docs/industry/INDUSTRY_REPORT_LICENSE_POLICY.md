# Industry Report License Policy

How PEdesk may use the licensed IBISWorld industry reports that feed the
**Industry Intelligence** layer. This policy is binding on the extraction
script, the committed data, and every rendered surface.

## License basis

The reports were purchased under a **private business/license account**.
PEdesk is authorized to use them **internally** for business intelligence,
diligence, benchmarking, training, and PEdesk-generated industry briefs. This
is **licensed business source material**, not a public scrape.

## Allowed (use the licensed data fully)

- Extract structured **metrics, tables, ratios, benchmarks, cost structures**.
- Extract **industry definitions, NAICS/IBIS codes, included services,
  products/services mix, segment shares**.
- Extract **major-player presence, market-share signals, drivers, risks,
  SWOT signals, key success factors**.
- Build **normalized derived datasets** (JSON/CSV) with provenance.
- Build PEdesk **industry pages, Guide/RAG answers, and generated briefs** that
  add analysis on top of the reports.
- **Connect** report-derived context to CMS/HCRIS/CIVHC/provider/deal data.

> Do not underuse the reports out of over-cautious copyright assumptions. The
> guardrail is against **republishing verbatim**, not against using the data.

## Not allowed

- Committing or publicly serving the **raw PDFs**.
- Dumping **long verbatim narrative passages** into pages or committed JSON.
- Making PEdesk look like an **IBISWorld clone / static mirror**.
- Presenting report-derived facts **as CMS/provider facts**, or mixing report
  **forecasts** with provider-specific evidence without clear labels.
- Using report-derived facts **without attribution/provenance**.

## Required posture

**LICENSED REPORT DERIVED**, not public scrape · **STRUCTURED EXTRACTION**, not
plagiarism · **PEdesk VALUE-ADD**, not a copied mirror.

- Raw PDFs stay private/internal (on the licensee machine; `.gitignore`d if ever
  staged).
- Numeric metrics, tables, labels, codes, segments, and benchmarks may be
  extracted with provenance.
- Longer narrative is **paraphrased** into PEdesk-native analysis; verbatim
  passages above a short length fail the extraction guardrail and are not
  rendered.
- Every derived record carries: `source_file, report_title, publisher,
  publication_date, industry_code, section, page, value_type, confidence,
  license_note`.

## Attribution string

> "Derived from licensed IBISWorld industry report, *<report title>*,
> <publication date>."

## Data-source boundary labels (rendered on every surface)

`LICENSED REPORT DERIVED` · `CMS PUBLIC DATA` · `HCRIS PUBLIC DATA` ·
`STATE APCD / CIVHC DATA` · `USER DEAL DATA` · `DATA REQUIRED`

Report-derived context is **industry-level, not provider-specific** unless
joined to CMS/HCRIS/user data, and **forecasts are report-derived, not PEdesk
predictions**. Industry context is not a final investment conclusion.
