# Report 0152: Map Next Directory — `rcm_mc/pe_intelligence/` Top-Level

## Scope

`RCM_MC/rcm_mc/pe_intelligence/` — top-level inventory only. **276 Python modules** (per Report 0097). Per Report 0151 backlog #2; carried since Report 0093 + 0097 + 0100. Sister to Reports 0092 (ml/ inventory), 0122 (rcm_mc_diligence/).

## Findings

### Headline

**`pe_intelligence/` is the largest unmapped subpackage in the project.**

- **276 .py files at top level** (no subdirectories per `find -type d` returning only the root)
- **3.2 MB total source size**
- **README.md: 20,192 bytes (~457 lines)** — extensive, this report reads only the header
- **`__init__.py`: 87,597 bytes (3,490 lines)** — **MASSIVE** — by far the largest `__init__.py` in the repo

### Top 20 largest .py files (by bytes)

| File | Bytes | Approx LOC |
|---|---|---|
| `__init__.py` | 87,597 | 3,490 |
| `partner_review.py` | 38,711 | ~1,500 |
| `heuristics.py` | 37,799 | ~1,500 |
| `reasonableness.py` | 33,803 | ~1,300 |
| `subsector_partner_lens.py` | 22,721 | ~900 |
| `deal_to_historical_failure_matcher.py` | 21,270 | ~850 |
| `named_failure_library_v2.py` | 20,394 | ~810 |
| `historical_failure_library.py` | 20,303 | ~810 |
| `narrative.py` | 19,246 | ~770 |
| `connect_the_dots_packet_reader.py` | 19,149 | ~760 |
| `management_meeting_questions.py` | 18,867 | ~750 |
| `healthcare_thesis_archetype_recognizer.py` | 18,458 | ~735 |
| `thesis_implications_chain.py` | 18,069 | ~720 |
| `cross_pattern_digest.py` | 17,759 | ~705 |
| `red_flags.py` | 17,531 | ~700 |
| `physician_specialty_economic_profiler.py` | 16,962 | ~675 |
| `deal_archetype.py` | 16,386 | ~650 |
| `failure_archetype_library.py` | 16,080 | ~640 |
| `regulatory_watch.py` | 16,032 | ~640 |

### Estimated total LOC

Average file size ~12 KB → ~480 LOC per file. **276 × 480 ≈ 132,000 lines.** ~3× the size of `rcm_mc/server.py` (which is ~11K lines per Report 0091).

**Per Report 0097**: The branch claimed "275 modules · 2,970 tests · 278 doc sections." Confirmed — 276 modules now (1 added since branch).

### Module-class observations from filenames

Per filename clusters, 276 modules organize into **7 partner reflexes** (per README lines 17-41):

| Reflex | Sample filenames |
|---|---|
| 1. Sniff test | `reasonableness.py`, `heuristics.py`, `red_flags.py`, `auditor_view.py` |
| 2. Archetype on sight | `archetype_canonical_bear_writer`, `archetype_heuristic_router`, `archetype_outcome_distribution_predictor`, `archetype_subrunners`, `bear_book`, `bear_case_generator`, `deal_archetype`, `healthcare_thesis_archetype_recognizer` |
| 3. Named-failure pattern match | `named_failure_library_v2`, `historical_failure_library`, `failure_archetype_library`, `deal_to_historical_failure_matcher` |
| 4. Dot-connect packet signals | `connect_the_dots_packet_reader`, `cross_pattern_digest`, `thesis_implications_chain` |
| 5. Recurring vs one-time | (likely in heuristics, reasonableness) |
| 6. Specific regulatory $ | `regulatory_watch.py`, `regulatory_*` family (TBD count) |
| 7. Partner voice | `partner_review` (orchestrator), `narrative.py`, `management_meeting_questions.py`, `analyst_cheatsheet.py` |

**Plus support clusters**: `bank_syndicate_*`, `bidder_landscape_reader`, `board_*`, `buyer_type_fit_analyzer`, `c_suite_team_grader`, `capex_*`, `capital_*`, `carve_out_risks`, `cash_conversion`...

### Primary entry point

Per README lines 45-50:
```python
from rcm_mc.pe_intelligence import partner_review
review = partner_review(packet)
```

**`partner_review.py` (38,711 bytes, ~1,500 LOC)** is the main orchestrator. It takes a `DealAnalysisPacket` (per Report 0057) and returns a partner-voice review.

### Suspicious findings

| Item | Note |
|---|---|
| `__init__.py` 87,597 bytes (3,490 lines) | **Dramatically larger than typical** — Reports 0093 (ml/__init__) was 30L; 0094 (domain/__init__) was 58L; 0122 (rcm_mc_diligence/__init__) was 46L. **This `__init__` is 50-100× larger.** Likely re-exports + heavy logic? |
| 0 subdirectories | All 276 modules at flat top level. **No grouping.** Per Report 0093 `ml/` 41 modules were also flat; this is 6.7× larger flat. Navigation friction. |
| Mtime: all files Apr 25 12:01 | **Bulk-touched** — same mtime as the f3f7e7f cleanup commit. Per Report 0097: branch was merged to main; mtimes reset on merge. |
| `__pycache__/` (per Report 0097) | exists; gitignored per Report 0001 + 0150. |

### Cross-link to Report 0093 ml/

Per Report 0093: `ml/` has 41 modules with a 29 KB README documenting 38 of them (2 undocumented). **`pe_intelligence/` has 276 modules with 20 KB README** — proportionally far less documentation density. **Doc gap likely.** Q1 below.

### Cross-link to Report 0097 (feature/pe-intelligence stale-snapshot)

Per Report 0097: `feature/pe-intelligence` branch is 0-ahead-of-main (merged). The 276 modules ARE on main. This iteration confirms.

### CLAUDE.md mentions (per Report 0093)

CLAUDE.md does NOT list `pe_intelligence/` in its Phase 4 module list. **MR503 critical doc rot.**

### Public surface — TBD

`__init__.py` is 3,490 lines. Would need a separate iteration to enumerate the public API surface. Per pattern (Report 0094 domain/__init__ re-exports 14 names), this likely re-exports a much larger surface.

**Q2**: How many names does `__init__.py` re-export?

### Cross-link to Report 0151 backlog

This iteration partially addresses Report 0151 backlog #2 (`pe_intelligence/`). 276 modules are now **inventoried at the top level**. Per-module audit would require ~276 iterations at 1 module per report.

**Realistic strategy**: spot-check the orchestrator (`partner_review.py`) + the 7 reflex anchors + the `__init__.py` public surface. ~10 iterations to cover the operational surface.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR836** | **`pe_intelligence/__init__.py` is 3,490 lines** — dramatically larger than typical `__init__.py` patterns (30-58L per prior subpackage audits) | Per Report 0093 + 0094 + 0122: `__init__.py` should be a thin re-export. **3,490 lines suggests substantive logic in the `__init__`** — refactor target if confirmed. | **High** |
| **MR837** | **276 modules at flat top level — no subdirectory grouping** | Navigation friction. ml/ (Report 0093) is 41 flat — already painful at that scale. 6.7× larger here. **A `partner_reflexes/` / `failure_libraries/` / `archetype_*/` reorganization would help.** | Medium |
| **MR838** | **Module count claimed in README (275) vs actual (276) drift by 1** | Per README line 4: "275 Python modules". Actual: 276. Minor doc-staleness. Cross-link Report 0093 ml/README claims 38 modules; reality is 40 (which were also off by 2). | Low |
| **MR839** | **CLAUDE.md does NOT mention `pe_intelligence/`** | Cross-link Report 0093 MR503 critical doc rot. The largest subpackage in the project is invisible to architectural docs. | **High** |
| **MR840** | **20 KB README for 132,000 lines — doc-density 6 chars/LOC** | vs ml/ (29 KB / 13K lines = 2.3 chars/LOC). pe_intelligence has 3× lower per-line documentation. **Strict per-module docstring discipline likely the saving grace** (Q3). | Medium |

## Dependencies

- **Incoming:** server.py (likely `/api/partner-review` route), `analysis/packet_builder.py` (per Report 0020 12-step builder), CLI.
- **Outgoing:** `DealAnalysisPacket` (per `partner_review(packet)` signature), stdlib (per README "stdlib-only").

## Open questions / Unknowns

- **Q1.** Does pe_intelligence/README.md document all 276 modules (like ml/README documented 38 of 40)?
- **Q2.** What does `__init__.py` (3,490 lines) actually contain — re-exports, registries, dispatch logic, or something else?
- **Q3.** Per-module docstring density — likely strict per "self-contained ... dataclass-based ... pairs a partner-voice `partner_note`" claim, but unverified.
- **Q4.** Does `partner_review(packet)` invoke ALL 276 modules per call, or selectively?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0153** | Read `pe_intelligence/__init__.py` (3,490 lines) — closes Q2 + reveals the registry pattern. |
| **0154** | Read `pe_intelligence/partner_review.py` head (38KB) — closes Q4 + identifies which sub-modules it dispatches to. |
| **0155** | Read `cli.py` head (1,252 lines, 19+ iter carry from Report 0003). |

---

Report/Report-0152.md written.
Next iteration should: read `pe_intelligence/__init__.py` (3,490 lines — anomalously large) to understand the registry/dispatch pattern.
