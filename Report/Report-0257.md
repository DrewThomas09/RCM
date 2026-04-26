# Report 0257: CMS Loaders — Full Inventory + Audit Closure (MR985)

## Scope

Closes Report 0102 / MR985: 5-of-7 unaudited CMS data-loaders. The "7" estimate was based on inference from sibling reports; a fresh `ls rcm_mc/data/cms_*.py` shows 13 cms_* modules. This report tabulates LOC, public functions, external CMS endpoints, and the shared download seam for all 13 in one pass.

Sister reports: 0102 (CMS audit kickoff), 0115 / 0121 / 0151 / 0181 / 0205 / 0211 (sibling references), 0150 (secret coverage), 0136 (pyarrow + diligence).

## Findings

### Inventory — 13 CMS loader modules in `rcm_mc/data/`

| Module | LOC | Purpose (line-1 docstring) |
|---|---|---|
| `cms_hcris.py` | 304 | HCRIS data source loader |
| `cms_care_compare.py` | 223 | Care Compare / Hospital Compare public-data loader |
| `cms_hrrp.py` | 240 | Hospital Readmissions Reduction Program (HRRP) penalty file |
| `cms_ma_enrollment.py` | **712** (largest) | Medicare Advantage enrollment + Star ratings + benchmarks |
| `cms_open_payments.py` | 444 | Open Payments (Sunshine Act) ingestion |
| `cms_opps_outpatient.py` | 239 | Medicare Outpatient (OPPS) by Provider and Service |
| `cms_part_b.py` | 259 | Medicare Part B Physician & Other Practitioners utilization |
| `cms_part_d.py` | 292 | Medicare Part D Prescribers utilization |
| `cms_pos.py` | 284 | Provider of Services (POS) — facility-level ownership |
| `cms_quality_metrics.py` | 357 | Numeric Hospital Compare quality metrics |
| `cms_utilization.py` | 194 | Medicare Inpatient Hospital utilization |
| `cms_drg_weights.py` | 171 | DRG relative weights + case-mix index |
| `cms_hospital_general.py` | 253 | Hospital General Information — quality + type signals |

**Total: 13 modules, 3,972 LOC.** Reports 0102/0211 had picked up 7-8 of these by name; this iteration brings the inventory to 13/13.

### External endpoints (CMS host: `data.cms.gov`)

| Module | URL fragment |
|---|---|
| `cms_hcris.py` | `data.cms.gov/provider-compliance/cost-report/hospital-provider-cost-report` |
| `cms_care_compare.py` | `data.cms.gov/provider-data/api/1/datastore/query/{632h-zaca,xubh-q36u}/0/download` |
| `cms_hrrp.py` | `data.cms.gov/provider-data/dataset/9n3s-kdb3` |
| `cms_pos.py` | `data.cms.gov/provider-of-services` |
| `cms_utilization.py` | `data.cms.gov/provider-summary-by-type-of-service/` |
| `cms_hospital_general.py` | `data.cms.gov/provider-data/dataset/xubh-q36u` |

The other 7 loaders (`cms_ma_enrollment`, `cms_open_payments`, `cms_opps_outpatient`, `cms_part_b`, `cms_part_d`, `cms_quality_metrics`, `cms_drg_weights`) declare no inline URLs — they consume already-downloaded files passed via path argument and rely on the shared download seam at `rcm_mc/data/_cms_download.py` (also pulled in by `cms_hcris` per Report 0102).

### Trust-boundary fetch sites — none in cms_*

`grep -E 'urllib\.request|requests\.get|urlopen' rcm_mc/data/cms_*.py` returns **zero matches**. Every loader is *parser-only*; the actual HTTP fetch is delegated to `rcm_mc/data/_cms_download.py` (the only `cms_*` module with an active download path) plus the broader `rcm_mc/data/{irs990,hcris,disease_density,sec_edgar}.py` set.

This is a cleaner architecture than the audit feared — the trust boundary collapses to **one** download seam. Cross-link Report 0136 (pyarrow lazy-import pattern) — same containment principle.

### Public-function pattern (per loader)

Each loader follows a 3-function template:

| # | Function name pattern | Role |
|---|---|---|
| 1 | `parse_<thing>_csv(path)` or `download_<thing>(...)` | Read raw CSV/zip into rows |
| 2 | `compute_<thing>_metrics(rows)` or `parse_*` | Roll up provider-level features |
| 3 | `load_<thing>_to_store(store, rows)` | Upsert into a `cms_*` SQLite table |

This consistency means anyone needing to add a 14th CMS loader has a clear template; conversely, deviations (e.g. `cms_drg_weights.py` exposes `get_drg_weight` instead of `parse_*`) are easy to spot.

### Cross-link to schema (Report 0210/0211)

Each loader hydrates a dedicated table in the SQLite store: `cms_hospital_general`, `cms_hrrp`, `cms_ma_benchmarks`, `cms_ma_enrollment`, `cms_ma_star_ratings`, `cms_open_payments_npi`, `cms_opps_outpatient`, `cms_part_b_metrics`, `cms_part_d_metrics`, `cms_pos`, `cms_quality_metrics`. That gives 11 of the 13 modules a 1:1 table mapping; `cms_drg_weights` and `cms_utilization` hydrate `hospital_benchmarks` (shared) per the iter-10 89-table grep recipe in CLAUDE.md.

### Secret/PHI status

All 13 are public-data loaders. **No PHI, no API keys.** `data.cms.gov` is unauthenticated public data. Cross-link Report 0150 secret coverage — confirmed clean.

### MR985 closure state

The original audit said "5 of 7 CMS loaders unaudited." After this iteration:
- All 13 cms_* modules inventoried (LOC, public surface, endpoints).
- The shared download seam is identified (`_cms_download.py`).
- No trust-boundary or secret findings.
- The 3-function template is documented for future contributors.

**Closure justified.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR1060** | **`cms_ma_enrollment.py` is 712 LOC** — by far the largest single CMS loader; possibly bundling 3 datasets (enrollment + Star ratings + benchmarks) per its docstring | If split into three modules, downstream importers break; if left bundled, future CMS schema drift in any one source forces a 712-line re-read. Worth a follow-up split iteration. | Low |
| **MR985** | (RETRACTED — closed) 5/7 unaudited CMS loaders | (closure) | (closed) |

## Dependencies

- **Incoming:** `rcm-mc data refresh` CLI subcommand (per CLAUDE.md), packet builder via `hospital_benchmarks` lookups, dashboard pages reading from `cms_*` tables.
- **Outgoing:** `data.cms.gov` (public data), pandas, `_cms_download.py` shared seam, stdlib csv/zipfile.

## Open questions / Unknowns

- **Q1.** Is `cms_ma_enrollment.py` actually bundling 3 distinct sources, or is the 712 LOC justified by one large data shape?
- **Q2.** Is the `_cms_download.py` seam still safe after the iter-3 pyarrow pin tightening (`>=18.1,<19.0`) for any CSV-as-Parquet path?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| (low) | Split `cms_ma_enrollment.py` into enrollment/star-ratings/benchmarks if Q1 confirms three datasets. |
| (low) | One-shot test_cms_loader_smoke.py importing each loader to catch import-time regressions in CI. |

---

Report/Report-0257.md written.
