# NPI Claims Cleaner — enterprise claims data-quality platform

`/npi-cleaner` is a self-contained claims data-quality tool inside RCM-MC:
drop a claims extract (CSV / TSV / XLSX), **a raw X12 837 or 835 EDI
file**, or **a .zip batch of files** and get back a cleaned file, a 0–100
quality grade, actionable per-rule and per-payer worklists, a printable
executive report, and a full cell-level audit trail. Everything runs
locally — no claim data ever leaves the server, and nothing is written to
the app database.

The design borrows deliberately from four product families:

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
- **Claims analytics frameworks (The Tuva Project)** — the layer beyond
  validation: service-category grouping, encounter construction,
  chronic-condition prevalence, data-loss-over-time detection,
  readmissions, coding-intensity screens.

**How this compares to Tuva.** Tuva is a dbt package: to use it you need
a warehouse (Snowflake/BigQuery/Databricks/…), a dbt project, an
input-layer mapping exercise, and an orchestrated pipeline. This tool
computes the same *class* of output — groupers, condition prevalence,
volume integrity, readmissions — in the **same pass as cleaning**, on a
drag-and-drop file, with zero infrastructure, plus everything Tuva
doesn't do at all: deterministic cell repairs with a full audit trail,
NPI Luhn verification and NPPES recovery, X12 837/835 native intake,
837↔835 reconciliation, PHI de-identification, a CI-gateable CLI, and a
10 GB streaming mode. Tuva's terminology depth (full code sets, CMS-HCC
risk, quality measures) is deeper; this tool's *time-to-first-answer* —
minutes from file to grade, worklists and population profile — is what a
diligence or RCM ops team actually needs first.

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

## Population analytics (the Tuva-class layer)

Report-only marts computed offline from the cleaned table in the same
run — rendered on the **Population** tab and carried in the scorecard
under `population`:

- **Service-category mix** — every line classified by the
  institutional-first ladder (Type of Bill → revenue code → place of
  service → HCPCS range) into Inpatient / Outpatient (ED, dialysis,
  ambulatory surgery, therapies…) / Office / Ancillary (lab, imaging,
  DME, ambulance) / Pharmacy / Behavioral health / Home health /
  Hospice, with an explicit Unclassified rate.
- **Encounters** — lines grouped into visits: same patient, same
  setting, service dates chaining with gaps ≤ 1 day (inpatient spans
  widen to admit→discharge). Per-setting counts, lines-per-visit,
  charges, and a one-row-per-encounter CSV (`?fmt=encounters`).
- **30-day readmissions** — an inpatient encounter starting 1–30 days
  after the patient's previous inpatient discharge.
- **Chronic-condition prevalence** — CCW-style ICD-10 prefix groups
  (25 conditions: diabetes, CKD, CHF, COPD, depression, cancer…) with
  per-patient multimorbidity (0/1/2/3+). Reporting only — membership is
  never a validity flag.
- **Volume integrity ("data loss over time")** — rows/charges/patients
  by service month with cliff detection: an interior month under 40% of
  its trailing median is almost always a missing extract, and says so.
  Each month also carries **observed PMPM** (charges per patient with
  claims that month — labeled "observed" because there is no
  eligibility denominator), plus the median across months.
- **E&M coding intensity** — each provider's established-visit mix
  (99211–99215) vs the file's own mix (national Medicare mix shown for
  context); providers coding materially hotter surface as a
  documentation-review starting point.

Everything is guarded (a mart failure never blocks cleaning), computed
post-de-identification (stable tokens keep grouping intact), and skipped
in 10 GB streaming mode (whole-table by nature — the warning says so).

## Huge files (up to 10 GB, streamed)

CSV/TSV uploads are accepted up to **10 GB**. Bodies above ~32 MB never
pass through memory — the server spools them to disk and the job cleans
the file with `npi_cleaner/bigfile.py`:

- The file is read as complete records (quote-aware, so embedded
  newlines never split a row) and grouped into ~48 MB chunks; every
  chunk runs the **exact same deterministic pipeline** as a normal
  upload, and chunk results merge the way zip-batch results do (summed
  counters, one blended grade). Cleaned rows append to one master
  output CSV as they are produced, so memory stays bounded by the chunk
  size no matter the input — a 10 GB file is simply many hours of
  chunks, and the job's progress reports per-chunk (% of file).
- Change-log rows stream to the master audit CSV with **global** row
  indices; worklist row indices are offset to the merged output, so
  per-rule and per-payer downloads slice the right rows.
- **Exact duplicates die across the whole file**, not just within a
  chunk: chunks share one bounded digest set (96-bit row digests,
  capped at 2M distinct rows ≈ 100 MB peak). If a file has more
  distinct rows than the cap, tracking stops there and the run says so
  in a warning — bounded memory stays honest.
- Scope (surfaced as warnings on the run): online modes, the
  suggestions companion, the xlsx workbook and whole-table analytics
  (payer clusters, outliers, claim rollup, dictionary, population
  marts) are skipped. The grade itself is exact — all five score
  dimensions come from summed counters. One history record for the
  whole run.
- Non-splittable formats (xlsx / zip / X12) keep the 200 MB in-memory
  ceiling; past it the run returns instructions to export CSV instead
  of an OOM. The `rcm-mc npi-clean` CLI routes through the same
  `clean_path`, so cron gets the 10 GB door too.
- **Long-run ergonomics**: job status carries `elapsed_secs`/`eta_secs`
  (linear projection once real work is under way) and the page shows
  "about Nh remaining"; `POST /npi-cleaner/cancel/<job_id>` cancels a
  running job cooperatively — the worker stops at its next progress
  tick (between chunks on a streaming run), no thread kill.

## Wishlist ("missing something?")

The page carries a request card: category (rule / field / payer /
format / integration / other), one-line title, optional details.
Requests persist to a dedicated WORKDIR SQLite file (config text only,
never claim data, length-capped) and move through a backlog
(open → planned → shipped/declined) — `GET/POST
/npi-cleaner/api/wishlist`, `POST …/wishlist/status`, `POST
…/wishlist/delete`. The run-history page carries the triage table
(change status, delete). This is the front door for feeding the
cleaner's improvement loop with what real feeds actually need.

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
├── rules.py        declarative registry (69 rules)
├── refdata.py      claims reference catalogs (POS/TOB/CARC/RARC/
│                   chronic-condition groups/…)
├── analytics.py    population marts: service mix, encounters,
│                   conditions, volume integrity, coding intensity
├── bigfile.py      10 GB streamed cleaning (chunk + merge)
├── wishlist.py     "missing something?" request backlog (SQLite)
├── x12.py          837P/837I/835 EDI → service-line table
├── profiles.py     named rule suites (SQLite, config only)
├── mappings.py     named column-mapping templates (SQLite, config only)
├── history.py      run-history observability (SQLite, aggregates only)
├── exec_report.py  printable executive one-pager
├── report.py       .xlsx workbook (Summary/Scorecard/Quality/WL tabs)
└── cli.py          `rcm-mc npi-clean`
rcm_mc/ui/npi_cleaner_page.py    the /npi-cleaner page
rcm_mc/ui/npi_history_page.py    the /npi-cleaner/history page
```

Tests: `tests/test_npi_cleaner.py` (175+ tests — every repair and flag
exercised with valid/invalid/skip cases, HTTP end-to-end through a real
server, PHI-absence assertions, CLI gate, X12 round-trips, streaming
equality, population-mart matrices).
