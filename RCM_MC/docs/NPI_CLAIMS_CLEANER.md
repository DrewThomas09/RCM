# NPI Claims Cleaner — enterprise claims data-quality platform

`/npi-cleaner` is a self-contained claims data-quality tool inside RCM-MC:
drop a claims extract (CSV / TSV / XLSX), **a raw X12 837 or 835 EDI
file**, or **a .zip batch of files** and get back a cleaned file, a 0–100
quality grade, actionable per-rule and per-payer worklists, a printable
executive report, and a full cell-level audit trail. Everything runs
locally — no claim data ever leaves the server, and nothing is written to
the app database.

The design borrows deliberately from three product families:

- **Great Expectations / Informatica** — a declarative rule registry
  where every check is a first-class object with severity, remediation
  guidance, and a data-quality dimension; named profiles ("expectation
  suites") tune the rules per feed.
- **Clearinghouses (Availity, Waystar)** — claims reference catalogs
  (POS, TOB, CARC/RARC, revenue codes, modifiers, UB-04 code sets, MBI
  format), scrubber-style front-door edits, and per-rule worklists.
- **Data observability (Monte Carlo, Bigeye)** — run history that trends
  quality across uploads, per-rule and per-dimension, so a team can see
  whether a feed is getting better after a source fix.

## What a run produces

| Artifact | Where |
|---|---|
| Cleaned file (all deterministic repairs applied) | `⤓ Download cleaned CSV` |
| Report workbook — opens on an **executive Summary tab** (grade, top findings + remediation, credential/specialty mix), plus Scorecard, Quality, NPI health, per-rule **WL worklist tabs**, cleaned data | `?fmt=xlsx` |
| Cell-level change log (every original → cleaned value; recorded before de-identification so PHI never leaks into it) | `?fmt=changelog` |
| Per-rule worklist CSVs (just the flagged rows, with row numbers) | `?fmt=worklist&rule=<id>` |
| Per-payer worklist CSVs (one payer family's flagged rows) | `?fmt=worklist&payer=<FAMILY>` |
| Data dictionary (per-column role, fill %, distinct, PHI-safe samples) | `?fmt=dictionary` |
| Printable executive one-pager | `?fmt=exec` |
| **Everything at once** — one zip with all of the above + `scorecard.json` | `?fmt=bundle` |

## The quality grade

Five classic DQ dimensions, each a recomputable ratio, blended
0.25/0.25/0.20/0.15/0.15 into a 0–100 score with a letter grade:

- **Completeness** — filled cells / total cells
- **Validity** — rows without impossible values (bad codes, unparseable
  amounts, malformed NPIs/MBIs/DRGs …)
- **Consistency** — rows without contradictions (paid > billed,
  discharge before admit, ZIP↔state disagreement, room & board on an
  outpatient bill …)
- **Uniqueness** — duplicates removed + near-duplicates + suspected
  duplicate claims
- **Conformity** — how much deterministic repair the file needed

## Rules

68 registered rules (`rcm_mc/npi_cleaner/rules.py`), two kinds:

- **Repairs** — deterministic, safe-by-construction normalizations the
  cleaner applies (NPI Excel-float damage, date → ISO, money
  normalization, ZIP/revenue/DRG/POS zero-pads, ICD-10 decimal insertion,
  provider-name re-casing …). Fully audited in the change log; can never
  be disabled by a profile.
- **Flags** — report-only findings (never auto-fixed): code-shape and
  domain screens, cross-field contradictions, charge outliers (3×IQR per
  HCPCS), timely-filing risk with **per-payer limits**, MUE-style unit
  screens, duplicate-claim detection …

`GET /npi-cleaner/api/rules` returns the whole catalog with severity,
description, remediation, and dimension.

## Profiles and mapping templates

- **Profiles** (`X-Profile` header, `--profile` on the CLI): named rule
  suites — each flag **on / accepted / off**, plus thresholds
  (timely-filing days, stale-date horizon, outlier fence). *Accepted*
  means "known issue, stop grading us on it": still reported, greyed,
  excluded from the score.
- **Mapping templates** (`X-Mapping` header, `--mapping` on the CLI):
  map a source system's column vocabulary once ("Epic extract") and
  reuse it on every upload. Saved from the confirm-columns step; an
  explicit hand-edited mapping always wins over the template.

Both persist in dedicated SQLite files under the cleaner's WORKDIR —
configuration only, never claim rows.

## X12 837 + 835 ingestion

`rcm_mc/npi_cleaner/x12.py` reads native EDI directly:

- **837P/837I claims** flatten to one row per service line (ClaimID,
  payer, billing/rendering/attending NPI, patient, DOS, POS / TOB,
  revenue code, HCPCS + modifiers, diagnosis, units, charge).
- **835 remittances (ERA)** flatten to one row per paid service line
  (claim status, billed/paid/patient-responsibility, CARC denial codes
  from CAS adjustments with group codes and amounts) — the CARCs feed
  the existing denial analytics and catalog, and the paid-vs-billed
  screens run automatically.

Separators come from the ISA envelope per spec and the normal pipeline
runs unchanged. Any other transaction set (999/270/276) produces a
precise warning instead of an empty result.

## Zip batches, payer split, portable suites

- **Zip batch**: a `.zip` of claim files cleans every member through the
  full pipeline — per-file grades on the Quality tab, one blended report
  card, and a zip of cleaned files as the download. An `.xlsx` (also a
  zip) is distinguished by `[Content_Types].xml`; junk entries are
  skipped; total **uncompressed** size is capped so a zip bomb can't
  defeat the upload limit.
- **Quality by payer**: findings split by payer family (spelling
  variants fold together) — rows, flagged share, clean %, top rules per
  payer, each with its own worklist download.
- **Portable suites**: profiles and mapping templates export/import as
  JSON (`/api/profiles/export|import`, `/api/mappings/export|import`);
  every import re-passes the save-time sanitizer.

## 837↔835 reconciliation

`POST /npi-cleaner/api/reconcile` with `{"a": <claims job id>, "b":
<remittance job id>}` matches two completed runs on claim id and
reports: claims with **no remittance at all**, paid-vs-billed variance
per matched claim (with each claim's CARCs), orphan remits, and the
playbook-enriched denial mix. The results panel offers the same match
against any recent run cleaned in the same browser.

## Run history

`/npi-cleaner/history` — every run records **aggregate counts only**
(score, dimensions, per-rule counts; no claim rows, no PHI) to a
dedicated SQLite file. The page trends the overall score, each quality
dimension, and any single rule across runs, and diffs two runs
rule-by-rule.

## PHI

- De-identification is **opt-in** (`deid=1`): patient identifiers are
  masked (names/SSN/MRN tokenized stably, DOB → year, ZIP → ZIP3);
  provider NPIs and names are never touched.
- The change log records values **before** de-identification runs, so
  masked PHI never appears in it.
- History and profiles store aggregates/configuration only.

## Programmatic surface

Documented in `/api/openapi.json` under the **Claims Cleaner** tag:

```
POST /npi-cleaner/api/clean?profile=<name>     raw CSV body → scorecard JSON
GET  /npi-cleaner/api/rules                    rule catalog
GET/POST /npi-cleaner/api/profiles [+/delete]  rule suites
GET/POST /npi-cleaner/api/mappings [+/delete]  mapping templates
GET  /npi-cleaner/api/history[/compare?a=&b=]  run history
```

CLI (cron/CI door — same engine, same artifacts):

```
rcm-mc npi-clean claims.csv [--profile P] [--mapping M] [--deid]
                            [--no-dedupe] [--json] [--outdir DIR]
                            [--bundle]          # <stem>_bundle.zip of all artifacts
                            [--min-score N]     # exit 1 below N → CI gate
rcm-mc npi-clean claims.837 --min-score 80
rcm-mc npi-clean sites.zip  --bundle            # batch a zip of extracts
```

## Module map

```
rcm_mc/npi_cleaner/
├── engine.py       cleaning engine: repairs, flags, scorecard, jobs
├── rules.py        declarative registry (68 rules)
├── refdata.py      claims reference catalogs (POS/TOB/CARC/RARC/…)
├── x12.py          837P/837I EDI → service-line table
├── profiles.py     named rule suites (SQLite, config only)
├── mappings.py     named column-mapping templates (SQLite, config only)
├── history.py      run-history observability (SQLite, aggregates only)
├── exec_report.py  printable executive one-pager
├── report.py       .xlsx workbook (Summary/Scorecard/Quality/WL tabs)
└── cli.py          `rcm-mc npi-clean`
rcm_mc/ui/npi_cleaner_page.py    the /npi-cleaner page
rcm_mc/ui/npi_history_page.py    the /npi-cleaner/history page
```

Tests: `tests/test_npi_cleaner.py` (130+ tests — every repair and flag
exercised with valid/invalid/skip cases, HTTP end-to-end through a real
server, PHI-absence assertions, CLI gate, X12 round-trips).
