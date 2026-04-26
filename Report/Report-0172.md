# Report 0172: Circular Import Risk — `data_public/` Subpackage Survey

## Scope

Surveys `RCM_MC/rcm_mc/data_public/` (313 files at top level) — Report 0091/0121 backlog #3. Sister to Reports 0022, 0052, 0082, 0095, 0112, 0142.

## Findings

### Subpackage scale

- **313 .py files at top level** (per `find -maxdepth 1 -type f -name "*.py"`)
- **2 subdirectories**: `_warehouse/`, `scrapers/`
- **2nd-largest unmapped subpackage** after pe_intelligence/ (276 modules per Report 0152)

### Cross-package imports — sample

`grep "^from \.\." data_public/*.py` returned empty in head — head modules don't import cross-package at top level. **Likely lazy-import pattern** per Report 0113 + 0125.

### Cross-link to Report 0154 PE_intelligence importers

Per Report 0154: `data_public/` has 4 of 8 production importers of `pe_intelligence/`:
- `data_public/rcm_benchmarks.py`
- `data_public/__init__.py`
- `data_public/corpus_report.py`
- `data_public/corpus_cli.py`
- `data_public/ic_memo_synthesizer.py` (5th — overcounted in 0154 but cross-listed)

**`data_public/` is the heavy consumer of `pe_intelligence/`.** Tight coupling between two giants (Report 0154 MR846 high).

### Cycle check approach

Without reading 313 files, can't enumerate cycles directly. **Heuristic**: per Report 0124 `PortfolioStore` is imported by `data_public/deals_corpus.py + backtester.py` (per Report 0124). So `data_public/` → `portfolio/` (forward edge).

Per Report 0154: `data_public/` → `pe_intelligence/` (forward edge). Per Report 0153: `pe_intelligence/` → only siblings. **No back-edge from pe_intelligence/ to data_public/.**

**No cycle** between data_public/ and pe_intelligence/.

**Likely no cycle within data_public/** if architecture is consistent — flat 313 files at top suggests namespace pattern (per Report 0093 ml/, 0152 pe_intelligence/).

### Subdirectory observations

| Subdir | Likely purpose |
|---|---|
| `data_public/_warehouse/` | underscore-prefix → internal storage abstraction |
| `data_public/scrapers/` | per Report 0156 reference: `news_deals.py`, `sec_filings.py` |

**`_warehouse/`** is a NEW unmapped sub-subpackage. Cross-link Report 0145 dbt `warehouse.py` (different package — `rcm_mc_diligence/ingest/warehouse.py`). **Naming-collision risk.**

### Trust boundary

`data_public/` consumes scraper output (per `news_deals.py`, `sec_filings.py` per Report 0156). **Scrapers fetch external HTTP** — same trust class as Report 0115 (CMS HCRIS) and Report 0136 (pyarrow user-uploaded).

### Cross-link to Report 0154 + Report 0156

Per Report 0156: feat/ui-rework-v3 + data_public/ have unmapped UI consumers. Cross-link with this report — data_public/ is the upstream of those UI consumers.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR904** | **`data_public/` is 313 files top-level + 2 subdirs (`_warehouse/`, `scrapers/`)** — 2nd largest unmapped | Cross-link Report 0091/0121/0152. Add to backlog priority. | **High** |
| **MR905** | **`data_public/_warehouse/` name potentially collides with `rcm_mc_diligence/ingest/warehouse.py`** | Different packages, no Python collision. But: search confusion for "warehouse" finds both. Per Report 0094 MR516 ReimbursementProfile pattern. | Low |
| **MR906** | **No cycle observed between data_public/ and pe_intelligence/ at high level** (forward edges only) | Cross-link Report 0142 finance/ leaf-shape; Report 0153 pe_intelligence leaf. **data_public is downstream consumer of both.** | (clean) |
| **MR907** | **`data_public/scrapers/`** has external-HTTP fetchers (per Report 0156: news_deals, sec_filings) | Trust boundary class same as Report 0115 (CMS) + Report 0136 (pyarrow). Need security audit. | Medium |

## Dependencies

- **Incoming:** unknown — likely UI pages (Report 0154 cross-link).
- **Outgoing:** PortfolioStore (Report 0124), pe_intelligence (Report 0154).

## Open questions / Unknowns

- **Q1.** Does data_public/ have a README documenting its 313 modules?
- **Q2.** What's the public surface (`__init__.py` re-exports)?
- **Q3.** Per-file cycle structure within data_public/ — flat namespace or layered?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0173** | Version drift (in flight). |
| **0174** | Cross-cutting (in flight). |

---

Report/Report-0172.md written.
