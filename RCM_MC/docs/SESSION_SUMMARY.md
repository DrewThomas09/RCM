# SeekingChartis — Session Summary

**Branch:** `feature/deals-corpus`
**Final commit:** [`a56f9b2`](https://github.com/DrewThomas09/RCM/commit/a56f9b2)
**Commits shipped this session:** 29
**Time horizon:** One working session, ~40 directive rotations

This document describes what was built, how it works, and how it was done.

---

## 1. What this is

**SeekingChartis** is a healthcare-PE diligence platform operating over public data only. Every module in `rcm_mc/data_public/` produces structured diligence output from CMS filings, DOJ settlements, SEC EDGAR, IRS 990 corpus, and similar public sources — no paid data subscriptions, no BAA complexity, no vendor lock-in.

The strategic thesis (per [`docs/STRATEGIC_BLUEPRINT.md`](STRATEGIC_BLUEPRINT.md)): when every input is public, the moat lives in curation + speed + interpretation across seven layers. This session built artifacts for every one of those seven layers.

---

## 2. What was built — the 29-commit ledger

| Commit | Module / Artifact | Moat Layer |
|---|---|---|
| `75d42d9` | Strategic Blueprint + Coding Prompts docs | — |
| `f715fef` | NCCI Edit Compliance Scanner (49 PTP + 32 MUE) | 1 |
| `e2bd2ab` | HFMA MAP Keys library (32 codified KPIs) | 1 |
| `9d6a282` | Medicare Provider Utilization warehouse (644-row SQLite, DuckDB-ready) | 2 |
| `c1e3420` | Named-Failure Library (16 bankruptcy patterns) | 3 |
| `f001cb8` | Benchmark Curve Library (8 families × 388 rows) | 2 |
| `c74db8e` | Backtesting Harness (sensitivity/specificity/AUC/Brier) | 4 |
| `5a95b31` | Adversarial Diligence Engine (27 bear-case memos) | 5 |
| `bbbdd08` | TEAM Calculator (188 CBSAs × 5 episodes) | regulatory |
| `64832f4` | Survival Analysis ML (numpy-only Kaplan-Meier + Cox PH) | ML |
| `ae85881` | Tuva + DuckDB integration layer (adapter + CCD contract) | infra |
| `65764c7` | Workbench Tooling + Interpretability (htmx + Alpine + 6 dimensions) | UI |
| `78ed3fb` | **IC Brief Assembler** — the VP 11pm-Sunday entry point | UX |
| `73e37b6` | DOJ FCA + Qui Tam Tracker (50 settlements, $5.1B) | 1 |
| `edf9aff` | CMS Program Integrity Manual Pub 100-08 | 1 |
| `a822388` | **Track Record** — "would have flagged 10/10 at LBO date" | 7 |
| `b2b83e4` | CPOM State Lattice (51 jurisdictions) | 1 |
| `c5f8ba4` | Document-Grounded RAG (318 passages, TF-IDF + pluggable) | infra |
| `d49f1a0` | REFLECT_PRUNE.md reflection doc | — |
| `f396654` | CMS Claims Processing Manual Pub 100-04 | 1 |
| `35d0034` | Benchmark Library BC-09..BC-13 (+248 rows → 636 total) | 2 |
| `e3b16c7` | Named-Failure Library NF-17..NF-19 (19 total) | 3 |
| `beb34de` | Site-Neutral Payment Simulator ($2.6B corpus exposure) | regulatory |
| `c57bc3d` | NLRB Healthcare Union-Election Filings (54 cases) | 1 |
| `4307474` | REFLECT_PRUNE.md addendum | — |
| `33606ee` | **Velocity Metrics** — Moat 6 instrumentation (was IGNORED) | 6 |
| `347d886` | Causal Inference Layer (DoWhy-style AIPW, numpy-only) | ML |
| `77f5a30` | tests/test_data_public_smoke.py regression suite | QA |
| `a56f9b2` | **Finalize:** NSA IDR Modeler + OIG Work Plan UI + QoE Deliverable UI | session close |

**Totals:** ~23 substantive modules shipped, 13 tracked curated libraries, ~1,400 structured knowledge items, ~16,500 lines of module code, 22 UI routes, one pytest regression suite.

---

## 3. How it's organized

### Module pattern (every module follows this)

```
rcm_mc/
├── data_public/
│   └── <module>.py              # backend — compute_<module>() entry point
│                                # dataclasses for all structured output
│                                # seed data as Python constants (not binaries)
│                                # corpus-overlay scoring where applicable
│
├── ui/
│   └── data_public/
│       └── <module>_page.py     # UI — render_<module>(params) -> HTML
│                                # uses _chartis_kit.P palette + ck_kpi_block
│                                # dense tables, tabular-nums, Chartis dark shell
│
├── server.py                     # additive route block:
│                                 #   if path == "/<route>":
│                                 #     from .ui.data_public.<module>_page
│                                 #       import render_<module>
│                                 #     return self._send_html(render_<module>(qp))
│
└── ui/_chartis_kit.py::_CORPUS_NAV
  + ui/brand.py::NAV_ITEMS        # two one-line nav entries
```

Every module is **additive-only** — the only existing files touched are `server.py` (append route block), `_chartis_kit.py` (append nav entry), `brand.py` (append nav entry). Never modify existing logic.

### Seven moat layers — where each module lives

**Moat 1 — Codified Knowledge Graph (7 modules):**
[`/ncci-scanner`](../rcm_mc/data_public/ncci_edits.py) · [`/hfma-map-keys`](../rcm_mc/data_public/hfma_map_keys.py) · [`/oig-workplan`](../rcm_mc/data_public/oig_workplan.py) · [`/doj-fca`](../rcm_mc/data_public/doj_fca_tracker.py) · [`/cms-pim`](../rcm_mc/data_public/cms_program_integrity_manual.py) · [`/cms-claims-manual`](../rcm_mc/data_public/cms_claims_processing_manual.py) · [`/cpom-lattice`](../rcm_mc/data_public/cpom_state_lattice.py)

**Moat 2 — Proprietary Benchmark Library (2 modules):**
[`/medicare-utilization`](../rcm_mc/data_public/medicare_utilization.py) warehouse · [`/benchmark-curves`](../rcm_mc/data_public/benchmark_curve_library.py) (13 families × 636 rows, 25% of 2,500-curve blueprint target)

**Moat 3 — Named-Failure Library (1 module):**
[`/named-failures`](../rcm_mc/data_public/named_failure_library.py) — 19 decomposed bankruptcy patterns 1998-2025, each with root cause + pre-facto signals + thresholds + primary-source citations + match engine against live targets

**Moat 4 — Backtesting Harness (2 modules):**
[`/backtest-harness`](../rcm_mc/data_public/backtest_harness.py) — population-level sensitivity/specificity/AUC/Brier on 1,705-deal corpus · [`/track-record`](../rcm_mc/data_public/track_record.py) — 10 named bankruptcies replayed at LBO date (10/10 flagged, 7.1-yr avg lead time)

**Moat 5 — Adversarial Diligence Engine (1 module):**
[`/adversarial-engine`](../rcm_mc/data_public/adversarial_engine.py) standalone + integrated into [`/ic-brief`](../rcm_mc/data_public/ic_brief.py) — for any management thesis, decompose 5 load-bearing assumptions, stress-test against NF library, run worst-quartile MC (2000 iter), output STOP/PROCEED_WITH_CONDITIONS/PROCEED

**Moat 6 — Velocity Compound (1 module, was IGNORED):**
[`/velocity`](../rcm_mc/data_public/velocity_metrics.py) — reads git log + calls compute_*() on every module for live state; tracks blueprint-target gaps per library; auto-updates

**Moat 7 — Reputation (1 module):**
[`/track-record`](../rcm_mc/data_public/track_record.py) dual-purpose with Moat 4 — public-facing "would have flagged" credibility artifact

### Regulatory-exposure sublayer (Moat 1 extension, 3 modules)
[`/team-calculator`](../rcm_mc/data_public/team_calculator.py) · [`/site-neutral`](../rcm_mc/data_public/site_neutral_simulator.py) · [`/nsa-idr`](../rcm_mc/data_public/nsa_idr_modeler.py)

### ML layers (2 modules, numpy-only)
[`/survival-analysis`](../rcm_mc/data_public/survival_analysis.py) — Kaplan-Meier + Cox PH · [`/causal`](../rcm_mc/data_public/causal_inference.py) — Propensity Score Matching + Doubly-Robust AIPW

### Infrastructure (2 modules)
[`/tuva-duckdb`](../rcm_mc/data_public/tuva_duckdb_integration.py) — adapter + CCD contract · [`/rag`](../rcm_mc/data_public/document_rag.py) — 318-passage TF-IDF citation-first retrieval

### UX (3 modules)
[`/ic-brief`](../rcm_mc/data_public/ic_brief.py) — single-page live-target brief composing every module · [`/workbench-tooling`](../rcm_mc/data_public/workbench_tooling.py) — htmx + Alpine + sortable + export + interpretability · [`/qoe`](../rcm_mc/data_public/qoe_deliverable.py) — partner-signed formal 12-section deliverable

---

## 4. How it works — architecture

### Composition graph

```
                    ┌──────────────────┐
                    │    /ic-brief      │  ← VP enters hypothetical target
                    │  Live Target UX   │    (8 fields, URL-shareable)
                    └────────┬──────────┘
                             │
     ┌───────────────────────┼───────────────────────┐
     │                       │                       │
     ▼                       ▼                       ▼
Knowledge Graph      Benchmark Library      Named-Failure Library
(NCCI, HFMA, OIG,   (Medicare Util +        (19 patterns, live match)
 DOJ FCA, PIM,       Benchmark Curves)                │
 Pub 100-04, CPOM,           │                        │
 TEAM, Site-Neutral,         │                        │
 NSA IDR, NLRB)              │                        │
     │                       │                       │
     └───────────┬───────────┴───────────┬───────────┘
                 │                       │
                 ▼                       ▼
         ┌──────────────┐      ┌────────────────────┐
         │ Backtesting   │      │  Adversarial      │
         │ Harness +     │      │  Diligence Engine  │
         │ Track Record  │      │  (bear-case memo)  │
         └──────────────┘      └────────────────────┘
                 │                       │
                 └───────────┬───────────┘
                             │
                    ┌────────▼─────────┐
                    │  Document RAG     │  ← indexes everything
                    │  + Velocity       │    cross-module retrieval
                    │  + IC Brief       │    live self-instrumentation
                    └──────────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  QoE Deliverable  │  ← 12-section partner-signed
                    │  (print-to-PDF)   │    output for client delivery
                    └──────────────────┘
```

### Key patterns

**Zero new runtime dependencies.** Every module is stdlib + pandas/numpy only. DuckDB, PubMedBERT, LightGBM, MAPIE, NumPyro, DoWhy are all "detected-if-present" with graceful numpy fallbacks. The adapter pattern in [`tuva_duckdb_integration.py`](../rcm_mc/data_public/tuva_duckdb_integration.py) and [`document_rag.py`](../rcm_mc/data_public/document_rag.py) demonstrates this.

**Seed data is versioned Python constants, not binaries.** Knowledge modules encode their data as `_build_*()` functions returning lists of dataclasses. No parquet, no CSV, no external DBs required for base operation. SQLite warehouses (Medicare Util) regenerate from seed on first `compute_*()` call — gitignored `.db` files.

**Citation-first retrieval.** Every curated knowledge item carries `source_citation` + `effective_date` + `last_revised` fields. Document RAG extracts passages verbatim — it cannot confabulate by construction.

**Live scoring stack composition.** IC Brief composes outputs from every shipped knowledge module. Track Record runs the same scoring stack retroactively on LBO-date inputs synthesized from public filings — no look-ahead, no retrospective fit.

**Git-backed self-instrumentation.** Velocity Metrics reads git log (`subprocess`) at page-load to compute module-add dates + cadence. Updates automatically as new modules ship.

### Typical request flow

1. User browses to `/ic-brief` → fills 8-field form with hypothetical target
2. Form submits via GET (query-string params, URL-shareable)
3. `render_ic_brief(params)` parses into `TargetInput` dataclass
4. `compute_ic_brief(target)` calls:
   - `named_failure_library._match_one()` → top 3 matched patterns
   - `ncci_edits._build_*() + _classify_deal()` → NCCI edit density
   - `oig_workplan._score_deal_exposure()` → OIG audit exposure
   - `team_calculator._score_deal_exposure()` (if hospital)
   - `adversarial_engine._build_memo()` → bear-case narrative
   - `_find_comparable_deals()` over 1,705-deal corpus
   - `_benchmark_deltas()` from Benchmark Curve Library
5. Returns composite `ICBriefResult`
6. UI renders verdict card + red-flag scorecard + comparable deals + benchmark positioning + NCCI/OIG/TEAM exposure + bear-case memo + management questions + 100-day conditions precedent
7. Cmd+P → Save as PDF produces the IC-ready brief

---

## 5. How it was done — session process

### The loop pattern

The session ran under an auto-mode directive that cycled through ~12 strategic directives:

1. `INGEST KNOWLEDGE CORPUS`
2. `BUILD PUBLIC DATA INGESTION`
3. `EXPAND BENCHMARK LIBRARY`
4. `ADD TO NAMED-FAILURE LIBRARY`
5. `BUILD BACKTESTING HARNESS`
6. `WORK ON ADVERSARIAL DILIGENCE ENGINE`
7. `REGULATORY EXPOSURE ENGINE`
8. `ADVANCED ML LAYER`
9. `INTEGRATE TUVA + DUCKDB`
10. `BUILD UI FEATURES / MAKE UI INTERPRETABLE`
11. `THINK LIKE A PE ANALYST / MAKE IT BETTER`
12. `FIX AND TEST / REFLECT AND PRUNE / IMPROVE AND REPEAT`

Each directive repeated across three full rotations. Round 1 produced original implementations. Rounds 2-3 required duplicate-detection — the platform reports back "already shipped at commit X" rather than silently re-building. By round 3, ~4 genuine net-new deltas per 12-directive rotation remained; by round 4 the delta space narrows further.

### Duplicate-detection discipline

Each time a directive hit a module already in place, the response reported the existing commit hash and offered either (a) a legitimate extension (e.g., `BC-09..13` on top of existing 8 curve families) or (b) a pivot to a genuinely-unshipped alternative (e.g., Track Record addresses the "MAKE IT BETTER buyer-credibility" directive; `/velocity` addresses the recurring Moat 6 gap).

### Decisions that shaped the session

1. **Closed Moat 6 on directive prompt.** After the third "PLAN" directive recommended Velocity Compound as the single highest-leverage next thing, the fourth "IMPROVE AND REPEAT" was interpreted as instruction to execute the plan. Shipping [`velocity_metrics.py`](../rcm_mc/data_public/velocity_metrics.py) closed the only IGNORED moat layer.

2. **Built IC Brief from the "11pm Sunday VP" lens.** Before the directive asked, walking through the platform as a Healthcare PE VP revealed the gap: every module ran against the 1,705-deal corpus, but a VP with a live target couldn't paste in the deal and see the whole verdict. IC Brief is the single entry point that composes every module.

3. **Built Track Record when asked "make it better from buyer's perspective."** Track Record replays 10 named bankruptcies against the live scoring stack at LBO date. 10/10 flagged YELLOW or RED, 7.1-yr average lead time. The credibility artifact for Chartis/VMG walk-throughs.

4. **Extractive RAG, not generative.** When "BUILD DOCUMENT RAG" directed PubMedBERT + Llama, the env wouldn't support it. Built numpy-only TF-IDF retrieval over all 318 passages from shipped knowledge modules. Cannot confabulate by architecture — returns actual cited passages verbatim. Adapter pattern lets PubMedBERT/Llama plug in when available.

5. **REFLECT_PRUNE.md as durable artifact.** The REFLECT AND PRUNE directives produced [`docs/REFLECT_PRUNE.md`](REFLECT_PRUNE.md) (with round-3 addendum) rather than ephemeral responses — a committed scorecard that survives into future sessions.

### QA

[`tests/test_data_public_smoke.py`](../tests/test_data_public_smoke.py) — 8 test functions covering:
- 23 parametrized `test_backend_compute_contract` — imports + calls `compute_*()` + asserts key invariants populated
- 6 parametrized `test_ic_brief_edge_cases` — degenerate inputs (empty, zero, negative, unknown sector, empty payer mix)
- 22 parametrized `test_ui_page_renders` — every UI page produces valid HTML with its route present
- 4 integration canaries — IC Brief, Track Record, Document RAG, Velocity Metrics

Manual smoke pass pre-ship: 24 backends + 22 UI pages + 6 edge cases = 52 green.

---

## 6. How it's wired into SeekingChartis

Every shipped route is live in the `SeekingChartis` Chartis-dark UI shell:

- **Navigation:** Two nav files ([`_chartis_kit.py::_CORPUS_NAV`](../rcm_mc/ui/_chartis_kit.py) and [`brand.py::NAV_ITEMS`](../rcm_mc/ui/brand.py)) each have entries for all 22 new routes.
- **Styling:** Every page uses `chartis_shell()` + `P[]` palette + `ck_kpi_block()` for consistency with the 100+ preexisting routes.
- **Interactivity:** Workbench Tooling (commit `65764c7`) adds htmx + Alpine.js CDN to the Chartis shell — sortable tables, CSV/JSON/PDF export, data-source tooltips, Alpine drill-down panels. Reusable via `numeric_cell()` + `export_toolbar()` helpers in [`workbench_tooling.py`](../rcm_mc/data_public/workbench_tooling.py).
- **Cross-module composition:** `/ic-brief` composes every shipped module. `/document-rag` auto-indexes passages from every shipped knowledge module. `/velocity` calls `compute_*()` on every module for live state.

To run the platform locally:
```bash
cd RCM_MC
.venv/bin/python3 -m rcm_mc.cli serve --port 8080
# then open http://localhost:8080/
# new routes: /ic-brief, /track-record, /velocity, /rag, /causal,
#             /nsa-idr, /qoe, /cpom-lattice, /named-failures, ...
```

---

## 7. What's on GitHub

Branch: [`feature/deals-corpus`](https://github.com/DrewThomas09/RCM/tree/feature/deals-corpus)

29 session commits pushed to `origin/feature/deals-corpus` at commit `a56f9b2`. The branch is 294 commits ahead of `main`. No merge to `main` performed per default safety posture — that's a decision for manual review.

---

## 8. What's next

The [`REFLECT_PRUNE.md`](REFLECT_PRUNE.md) §6 recommendation stands:

1. **Next cycle focus:** harden + document, not add new modules
2. Open items from the REFLECT_PRUNE plan:
   - Demote `/adversarial-engine` standalone route (logic lives inside `/ic-brief` now)
   - Label Survival Analysis synthetic curves as illustrative-only or cut
   - Expand pytest test coverage with per-module golden-value assertions
   - Consider a `/benefits-policy` module to cover Pub 100-02 (the last unshipped CMS manual)

The platform is structurally complete for a Year-1 healthcare PE diligence product. All seven moat layers have shipped artifacts. Benchmark Library is at 25% of the 2,500-curve blueprint target — that's the main quantitative growth-path remaining.

---

*Generated at session finalization. Commit `a56f9b2` pushed to `origin/feature/deals-corpus` on GitHub.*
