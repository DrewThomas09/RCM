# Report 0004: Incoming Dependency Graph for `rcm_mc/analysis/packet.py`

## Scope

This report covers the **incoming-dependency graph for `RCM_MC/rcm_mc/analysis/packet.py`** on `origin/main` at commit `f3f7e7f`. That is: every file that imports this module (or its symbols), with exact paths and line numbers, plus a coupling-tightness verdict. The module was selected because `CLAUDE.md` (on `feature/deals-corpus`) names `DealAnalysisPacket` as the load-bearing invariant — every UI page, API endpoint, and export renders from a single instance — so the audit needs to know its actual reach.

Two HIGH-PRIORITY discoveries were made in passing while tracing imports; they are documented under Findings rather than deferred.

Prior reports reviewed before writing: 0001, 0002, 0003.

## Findings

### The module under audit

- `RCM_MC/rcm_mc/analysis/packet.py` — **1,283 lines**, last touched 2026-04-25 (commit `f3f7e7f`).
- Outgoing imports (what packet.py itself depends on) — **stdlib only**: `hashlib`, `json`, `math`, `dataclasses`, `datetime`, `enum`, `typing`. **Zero `rcm_mc` imports.** It is a pure dataclass module with no internal coupling — that is structurally good and a key reason it can serve as the canonical packet.

### Sibling packet modules — disambiguation required

Three different `packet.py` files exist on origin/main. Naive `grep "from .packet"` over-counts because relative imports resolve to a sibling, not to `analysis/packet.py`.

| Path | Lines | Role |
|---|---:|---|
| `rcm_mc/analysis/packet.py` | 1,283 | Canonical `DealAnalysisPacket`. Subject of this report. |
| `rcm_mc/diligence/regulatory/packet.py` | ~344 (11.4 KB) | `RegulatoryRiskPacket` — sub-packet attached to `DealAnalysisPacket` at "step 5.5 (after comparables, before reimbursement)" (per its module docstring). |
| `rcm_mc/exit_readiness/packet.py` | (n/a) | Owns `run_exit_readiness_packet`, `ExitReadinessResult`. Imported only by `rcm_mc/exit_readiness/__init__.py:54`. |

This is a **deliberate sibling pattern**: each subsystem owns its own `packet.py` that composes into the overall packet. Therefore:

- `from .packet import …` inside `rcm_mc/diligence/regulatory/*.py` resolves to `rcm_mc/diligence/regulatory/packet.py` — **not** to `rcm_mc/analysis/packet.py`.
- `from .packet import …` inside `rcm_mc/exit_readiness/__init__.py` resolves to `rcm_mc/exit_readiness/packet.py` — same story.

After disambiguating, the true incoming graph for `rcm_mc/analysis/packet.py` is below.

### True incoming importers — production code (7 files, 11 import sites)

| File | Line | Import statement |
|---|---:|---|
| [`rcm_mc/server.py`](../RCM_MC/rcm_mc/server.py) | 3713 | `from .analysis.packet import PACKET_SCHEMA_VERSION` |
| [`rcm_mc/server.py`](../RCM_MC/rcm_mc/server.py) | 8736 | `from .analysis.packet import hash_inputs` |
| [`rcm_mc/server.py`](../RCM_MC/rcm_mc/server.py) | 8957 | `from .analysis.packet_builder import _new_run_id as _pb_rid` (sibling builder, not packet.py itself, but tightly related) |
| [`rcm_mc/server.py`](../RCM_MC/rcm_mc/server.py) | 10852 | `from .analysis.packet import PACKET_SCHEMA_VERSION` (duplicate of L3713) |
| [`rcm_mc/analysis/__init__.py`](../RCM_MC/rcm_mc/analysis/__init__.py) | 3-32 | Re-exports **30 symbols** from `.packet`: `DealAnalysisPacket`, `HospitalProfile`, `ObservedMetric`, `CompletenessAssessment`, `MissingField`, `StaleField`, `ConflictField`, `QualityFlag`, `ComparableSet`, `ComparableHospital`, `PredictedMetric`, `ProfileMetric`, `MetricImpact`, `EBITDABridgeResult`, `PercentileSet`, `SimulationSummary`, `RiskFlag`, `RiskSeverity`, `DataNode`, `ProvenanceGraph`, `ProvenanceSnapshot`, `DiligenceQuestion`, `DiligencePriority`, `SectionStatus`, `MetricSource`, `PACKET_SCHEMA_VERSION`, `SECTION_NAMES`, `hash_inputs`. **This is the canonical re-export point** — the entire packet type system is exposed at `rcm_mc.analysis.<symbol>`. |
| [`rcm_mc/analysis/risk_flags.py`](../RCM_MC/rcm_mc/analysis/risk_flags.py) | 38 | `from .packet import (` — sibling import. |
| [`rcm_mc/analysis/diligence_questions.py`](../RCM_MC/rcm_mc/analysis/diligence_questions.py) | 30 | `from .packet import (` — sibling. |
| [`rcm_mc/analysis/packet_builder.py`](../RCM_MC/rcm_mc/analysis/packet_builder.py) | 27 | `from .packet import (` — sibling. The builder. |
| [`rcm_mc/analysis/analysis_store.py`](../RCM_MC/rcm_mc/analysis/analysis_store.py) | 23 | `from .packet import DealAnalysisPacket, PACKET_SCHEMA_VERSION, hash_inputs` |
| [`rcm_mc/analysis/analysis_store.py`](../RCM_MC/rcm_mc/analysis/analysis_store.py) | 241 | `from .packet_builder import build_analysis_packet` (lazy, inside function) |
| [`rcm_mc/analysis/completeness.py`](../RCM_MC/rcm_mc/analysis/completeness.py) | 36 | `from .packet import (` — sibling. |
| [`rcm_mc/diligence/integrity/preflight.py`](../RCM_MC/rcm_mc/diligence/integrity/preflight.py) | 201 | Only a docstring reference (`Lazy import of rcm_mc.analysis.packet.IntegrityCheck`). No actual import statement. **Not a real importer.** |

**Production-coupling tightness verdict:** **MODERATE.** Only **7 files** in `rcm_mc/` import this module directly. Six are within `analysis/` itself (the package owns its own state). The seventh is `server.py`, which uses only two symbols — `PACKET_SCHEMA_VERSION` (twice, as a guard against schema drift) and `hash_inputs` (once, for input fingerprinting).

That is a much cleaner production graph than the raw 102-grep-hits suggested. The "load-bearing invariant" claim is enforced through the **30-symbol re-export at `rcm_mc/analysis/__init__.py:3-32`**, not through wide direct imports of `packet.py`.

### True incoming importers — tests

- **80 test files** under `RCM_MC/tests/` import `from rcm_mc.analysis.packet …` (qualified path).
- This is the **dominant coupling site**. The test surface treats `analysis.packet` as a public, stable contract. Any breaking change to `DealAnalysisPacket`'s shape or a re-exported symbol's signature will cascade into ~80 test files.
- Sample (one match per common test): `tests/test_concurrent_analysis.py:26`, `tests/test_phase_j.py:76`, `tests/test_ccd_provenance_end_to_end.py:25`, `tests/test_auto_populate.py:56`, `tests/test_ridge_predictor.py:353`, `tests/test_integrations_full_stack.py:21`, `tests/test_state_regulatory.py:36`, `tests/test_temporal_forecaster.py:34`, `tests/test_ui_pages.py:34`, `tests/test_provenance_graph.py:16`, `tests/test_packet_sparse_data.py:18`. (Full list available via `grep -rn "from rcm_mc.analysis.packet" RCM_MC/tests`.)

### Symbol-level reach

- `grep -rln "DealAnalysisPacket"` returns **48 files** in `rcm_mc/` referencing the symbol. That's the actual production reach when you count files that handle a packet object without re-importing the type. **48 production files touch DealAnalysisPacket** — call this the "packet-aware surface."

### Orphan test? No, this module is hot

- 0 production files unimport this module — so **no orphan modules in this scope**.
- Tight-coupling threshold per iteration spec: ">5 callers". Production callers = 7 (just over). Test callers = 80 (massive over). Symbol-aware callers = 48. By any of those counts, **this module is tightly coupled**, but in the controlled way that a canonical dataclass should be.

### HIGH-PRIORITY discoveries made in passing

#### Discovery A — `rcm_mc/diligence/` is a 40+ subdirectory subsystem on origin/main

Listing `RCM_MC/rcm_mc/diligence/` reveals **40 subdirectories** plus 2 README/log files plus 4 top-level Python files. Subdirs include: `bear_case`, `benchmarks`, `bridge_audit`, `checklist`, `comparable_outcomes`, `counterfactual`, `covenant_lab`, `cyber`, `deal_autopsy`, `deal_mc`, `denial_prediction`, `exit_timing`, `hcris_xray`, `ingest`, `integrity`, `labor`, `ma_dynamics`, `management_scorecard`, `patient_pay`, `payer_stress`, `physician_attrition`, `physician_comp`, `physician_eu`, `quality`, `real_estate`, `referral`, `regulatory`, `regulatory_calendar`, `reputational`, `root_cause`, `screening`, `synergy`, `thesis_pipeline`, `value`, `working_capital`. Plus a 17 KB `INTEGRATION_MAP.md` and a 45.7 KB `SESSION_LOG.md`.

This subsystem is **not mentioned in any prior report**. It is a peer to `data_public/` (which also exists on main with 313 Python files — see Discovery B). Mapping it is multi-iteration work.

#### Discovery B — `rcm_mc/data_public/` exists on origin/main with **313 Python files**

In Reports 0001/0002 I assumed `data_public/` was unique to `feature/deals-corpus`. **That was wrong.** `RCM_MC/rcm_mc/data_public/` exists on `origin/main` with at least 313 `.py` files including `aco_economics.py`, `__init__.py`, etc. The earlier "untracked" status I observed when standing on `main` was because I had checked out the OLD `f9477f1` main; since pulling to current `f3f7e7f`, `data_public/` is fully tracked here too.

This means there are now **(at least) two competing implementations of similar concepts** — main has `diligence/regulatory/nsa_idr_modeler.py` *and* `data_public/` modules; `feature/deals-corpus` has `data_public/nsa_idr_modeler.py`. Without a careful per-file diff, the merge of `feature/deals-corpus → main` will produce silent shadowing or drop work.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR22** | **HIGH-PRIORITY: Parallel NSA IDR implementations across branches** | Origin/main has `rcm_mc/diligence/regulatory/nsa_idr_modeler.py` + `rcm_mc/data_public/nsa_idr_modeler.py` (existence on main of the data_public version not yet verified — see Q1 below). Feature/deals-corpus has `rcm_mc/data_public/nsa_idr_modeler.py` with my J2-related work. A naive merge can leave 3 implementations co-existing, or silently drop work, or shadow imports depending on Python's resolution order. | **Critical** |
| **MR23** | **HIGH-PRIORITY: Parallel `data_public/` trees** | Both main (313 .py files) and feature/deals-corpus have `data_public/`. The two trees may overlap, may diverge, may have files with same name and different content. Pre-merge: full per-file `git diff origin/main..origin/feature/deals-corpus -- RCM_MC/rcm_mc/data_public/` to enumerate exact overlaps. | **Critical** |
| **MR24** | 30-symbol re-export at `analysis/__init__.py` is the load-bearing API surface | Any branch that adds, removes, or renames a symbol in `packet.py` must also update `analysis/__init__.py:3-32`. Easy to miss. Tests will catch some breakage (80 test importers); the risk is silent attribute drops that tests don't exercise. Pre-merge audit: diff `analysis/__init__.py` across all 8 ahead-of-main branches and reconcile the re-export list. | **High** |
| **MR25** | `server.py` lazy / late imports of `analysis.packet` (4 sites at lines 3713, 8736, 8957, 10852) | These are inside-function imports, not top-of-file. Easy to miss in a search-and-replace. Branches that update `analysis.packet` symbol names must hand-edit these too. | **Medium** |
| **MR26** | `analysis_store.py:241` lazy import of `packet_builder` | Same pattern — late import inside a function. Branch merges that move `build_analysis_packet` to a different module will silently break this. | **Medium** |
| **MR27** | Three sibling `packet.py` files easy to confuse | `analysis/packet.py`, `diligence/regulatory/packet.py`, `exit_readiness/packet.py`. A grep over `from .packet import` is ambiguous. Branches that introduce a fourth subsystem `packet.py` increase the confusion surface. Recommendation: rename the sub-packets (`regulatory_packet.py`, `exit_readiness_packet.py`) to disambiguate, or accept the pattern and document it. | Low |
| **MR28** | `diligence/integrity/preflight.py:201` references `IntegrityCheck` only in a docstring | If `IntegrityCheck` was removed or renamed in a feature branch, the docstring will be a stale lie that humans (and grep-based tooling) will trust. Low-impact alone but symptomatic. | Low |

## Dependencies

- **Incoming (production):** 7 files (server.py + 6 within analysis/). 80 test files. Zero non-test, non-analysis production importers outside server.py — meaning `analysis/packet.py`'s reach into the rest of the package is via the `analysis/__init__.py` re-export point and via objects passed by reference.
- **Incoming (tests):** 80 files. Tests are the most coupled consumers and serve as the de facto contract.
- **Outgoing:** stdlib only. No internal coupling. Clean.

## Open questions / Unknowns

- **Q1 (this report).** Does `data_public/nsa_idr_modeler.py` exist on origin/main, and if so does it differ from `diligence/regulatory/nsa_idr_modeler.py`? Without this answer, MR22 cannot be sized.
- **Q2.** What is the line-by-line diff of `data_public/` between origin/main and origin/feature/deals-corpus? The two trees both exist; their delta is the actual integration unknown.
- **Q3.** Has any branch added a new top-level dataclass to `analysis/packet.py` and forgotten to update the `analysis/__init__.py` re-export list? Mechanical check: grep for `@dataclass` in packet.py vs the symbol list in `__init__.py`.
- **Q4.** Are the two test files I sampled at `tests/test_packet_sparse_data.py:18` and `tests/test_provenance_graph.py:16` representative of the test-side packet contract, or do other tests probe deeper internals (e.g. private fields, schema-version constants)?
- **Q5.** What does `rcm_mc/diligence/SESSION_LOG.md` (45.7 KB) contain? It is the largest single doc inside diligence/. May contain build history that informs merge planning.
- **Q6.** What does `rcm_mc/diligence/INTEGRATION_MAP.md` (17 KB) say about how the diligence subsystem expects to plug into `analysis/packet.py`? This document might pre-answer many merge questions.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0005** | **Read `rcm_mc/diligence/INTEGRATION_MAP.md`** in full and document its claims. | Likely pre-answers Q5/Q6 and many of the upcoming merge questions for free. HIGH-priority — built into the codebase as a roadmap, but not yet read. |
| **0006** | Diff `data_public/` between `origin/main` and `origin/feature/deals-corpus` — file-by-file existence + size delta. | Resolves Q1, Q2, MR22, MR23. Cannot plan any merge before this is done. |
| **0007** | Walk `rcm_mc/cli.py` (1,252+ lines, `main()` at L1252). Still owed since Report 0003. | Maps the user-facing CLI surface; required by MR14 follow-through. |
| **0008** | Branch register (still owed since 0001/0002/0003). Every branch ahead/behind main with author + last-touch date. | Required before any merge planning. |
| **0009** | Read `analysis/__init__.py` end-to-end and produce the canonical re-export list as a checked artifact. | MR24 mitigation. |
| **0010** | Map `rcm_mc/diligence/` at depth = 1 — list every subdir + count modules. | Discovery A is large enough that one report can't cover it; this is the "directory of directories" layer. |

---

Report/Report-0004.md written. Next iteration should: read `rcm_mc/diligence/INTEGRATION_MAP.md` (17 KB) in full and document what it claims about how the 40-subdirectory diligence subsystem connects to `analysis/packet.py` — likely pre-resolves several of the open questions above.

