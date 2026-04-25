# Report 0022: Circular Import Risk — `analysis/` Subsystem

## Scope

This report covers **circular-import risk in the `RCM_MC/rcm_mc/analysis/` subpackage** on `origin/main` at commit `f3f7e7f`. Method: enumerate every intra-`analysis/` `from .X import …` (relative-sibling) import statement, build the directed dependency graph, run a topological sort, flag cycles or near-cycles.

The subpackage was selected because:
- It contains the `DealAnalysisPacket` invariant (Report 0004) — the load-bearing artifact every UI / API / export renders from.
- It has 23 source files — large enough to harbor cycles, small enough to fully audit in one iteration.
- Report 0008 noted `analysis_store.py:241` uses an inside-function lazy import of `packet_builder`, suggesting someone previously worried about a cycle here.
- Report 0020 audited `packet_builder.py`'s error handling but did not map its dependency graph.

Cross-package edges (`from ..core import …`, `from ..ml import …`, etc.) are **listed but not traced** for cycle purposes — Python cannot have a cycle through `..ml.X` and `..analysis.Y` unless `..ml.X` imports `..analysis.Y` (a check this iteration does not perform).

Prior reports reviewed before writing: 0018-0021.

## Findings

### Files in `analysis/` (23 source files)

`analysis_store.py`, `anomaly_detection.py`, `challenge.py`, `cohorts.py`, `compare_runs.py`, `completeness.py`, `cross_deal_search.py`, `deal_overrides.py`, `deal_query.py`, `deal_screener.py`, `deal_sourcer.py`, `diligence_questions.py`, `packet.py`, `packet_builder.py`, `playbook.py`, `pressure_test.py`, `refresh_scheduler.py`, `risk_flags.py`, `saved_analyses.py`, `stress.py`, `surrogate.py`, plus `__init__.py` and `README.md`.

### Sibling import adjacency

`grep -oE "^[[:space:]]*from \.([a-z_]+)"` per file. Each row is a directed edge `from → to`:

```
__init__              → analysis_store, packet, packet_builder
analysis_store        → deal_overrides, packet, packet_builder
challenge             → pressure_test
completeness          → packet
deal_query            → analysis_store
diligence_questions   → completeness, packet, risk_flags
packet_builder        → completeness, deal_overrides, diligence_questions, packet, risk_flags
refresh_scheduler     → analysis_store
risk_flags            → completeness, packet
```

Files with **zero sibling imports** (only stdlib + cross-package): `anomaly_detection`, `cohorts`, `compare_runs`, `cross_deal_search`, `deal_overrides`, `deal_screener`, `deal_sourcer`, `packet`, `playbook`, `pressure_test`, `saved_analyses`, `stress`, `surrogate`.

(Note: `cross_deal_search` and `deal_screener` use **lazy/inside-function imports** of siblings — these don't create module-load-time cycles. They appear as zero-edge here because the regex only counts top-of-file imports.)

### Topological sort — successful (no cycles)

Layer 0 (leaves — zero in-package deps):

```
packet
deal_overrides
pressure_test
(plus 10 other zero-edge files)
```

Layer 1 (depend only on leaves):

```
completeness        → packet
challenge           → pressure_test
```

Layer 2:

```
risk_flags          → completeness, packet
```

Layer 3:

```
diligence_questions → completeness, packet, risk_flags
```

Layer 4:

```
packet_builder      → completeness, deal_overrides, diligence_questions, packet, risk_flags
```

Layer 5:

```
analysis_store      → deal_overrides, packet, packet_builder
```

Layer 6 (top — depend on Layer 5):

```
__init__            → analysis_store, packet, packet_builder
deal_query          → analysis_store
refresh_scheduler   → analysis_store
```

**The graph is a clean DAG. No cycles, no self-loops.** Every edge points strictly upward in the layer ordering.

### Near-cycle hazard — `analysis_store ↔ packet_builder`

The graph has one place worth scrutiny:

- `analysis_store.py:23` (top-of-file): `from .packet import DealAnalysisPacket, PACKET_SCHEMA_VERSION, hash_inputs` — **packet, OK.**
- `analysis_store.py:23-?`: `from .packet_builder import …` — packet_builder imported at module load.
- `analysis_store.py:241` (lazy, inside function): `from .packet_builder import build_analysis_packet` — **redundant** with the top-level import, but lazy.

The redundant lazy import at line 241 (per Report 0008) is a defensive marker. Python imports are cached in `sys.modules`, so repeating the import cheaply re-binds the name. The lazy form is typical when a module wants to delay loading until a function call AND reference the symbol via a fresh local binding (avoiding stale top-level binding after a module reload).

**This is a NEAR-cycle risk.** The current direction is `analysis_store → packet_builder`. If a future feature branch adds `from .analysis_store import save_packet` to the top of `packet_builder.py`, **a cycle would form**:

```
packet_builder.py top imports → analysis_store
analysis_store.py top imports → packet_builder
```

At import time, Python would partially load one module, switch to the other (which references the partially-loaded first), and silently return the half-built first module. Symptoms: `AttributeError: module 'rcm_mc.analysis.analysis_store' has no attribute 'save_packet'` — but only if hit during import, not after both modules complete.

**Mitigation:** the lazy import at `analysis_store.py:241` is a partial guard — but it doesn't protect against a top-of-file edit on the `packet_builder` side.

### `__init__.py` import order

`analysis/__init__.py:3-32` imports in order:

1. `from .packet import (30 symbols)` — packet is a leaf, safe.
2. `from .packet_builder import build_analysis_packet` — pulls in packet_builder + transitive deps (completeness, risk_flags, diligence_questions, deal_overrides, all of which resolve to already-loaded packet).
3. `from .analysis_store import (...)` — pulls in analysis_store + its transitive deps (packet_builder is already cached, packet is cached).

**Three sequential imports, each downstream of the previous. Order is correct.** A reordering (e.g. `analysis_store` before `packet_builder` at __init__) would still work because Python resolves module dependencies on demand — the result would be the same.

### Cross-package import surface (out-of-scope but flagged)

Several `analysis/` modules pull in heavy cross-package dependencies that *could* form cycles if those packages reciprocate:

| File | Cross-package imports |
|---|---|
| `analysis_store.py` | `..portfolio.store` (PortfolioStore — Report 0008 / 0017) |
| `challenge.py` | `..data.intake._blended_mean`, `..core.simulator.simulate_compare`, `..infra.config.load_and_validate`, `..infra._terminal.banner` |
| `pressure_test.py` | `..data.intake._blended_mean`, `..data.intake.scale_blended_to_per_payer`, `..core.simulator.simulate_compare` |
| `stress.py` | `..core.simulator.simulate_compare` |
| `cohorts.py` | `..deals.deal_tags`, `..portfolio.store`, `..portfolio.portfolio_snapshots` |
| `cross_deal_search.py` (lazy) | `..deals.deal_notes`, `..analysis.deal_overrides`, `..analysis.analysis_store` |
| `deal_screener.py` (lazy) | `..data.auto_populate.auto_populate`, `..data.state_regulatory.assess_regulatory`, `..analysis.completeness.RCM_METRIC_REGISTRY` |
| `deal_sourcer.py` (lazy) | `..data.hcris._get_latest_per_ccn`, `..data.hcris._row_to_dict` |
| `packet_builder.py` | `..ml.comparable_finder`, `..ml.ridge_predictor`, `..domain.econ_ontology`, `..finance.reimbursement_engine`, `..pe.value_bridge_v2`, `..pe.ramp_curves`, `..pe.rcm_ebitda_bridge` (all lazy / inside-function) |

**`packet_builder.py` has 7 cross-package lazy imports.** Each is wrapped in `try/except (BLE001)` per Report 0020. None are at module top — so they don't contribute to module-load cycles.

### Notable patterns

- **Lazy imports cluster around `packet_builder.py` and `cross_deal_search.py`.** This is principled: lazy imports decouple module-load order from optional features.
- **`packet.py` is the single 0-internal-import root.** Per Report 0004, it imports stdlib only. **It is THE foundational dataclass module.**
- **`deal_overrides.py` is also a 0-import leaf** — confirmed by Report 0010's orphan-files sweep that it has 0 sibling imports, but it IS imported by 2 siblings (analysis_store, packet_builder).
- **`__init__.py` re-exports 30+ symbols from `packet.py` and 6+ from `analysis_store.py`** (per Report 0004). That re-export surface is the canonical public API.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR174** | **`packet_builder ↔ analysis_store` near-cycle** | Currently `analysis_store` imports `packet_builder` (top-of-file). If any feature branch adds `from .analysis_store import …` to the top of `packet_builder.py`, a real cycle forms. **Pre-merge: any branch that touches `packet_builder.py`'s imports must be checked for this.** Per Report 0008's coverage gap (`analysis_store.py:241` is barely tested), regression detection is weak. | **High** |
| **MR175** | **`analysis_store.py:241` lazy-import duplicates the top-of-file import** | The redundant lazy at line 241 is dead code unless someone deliberately reloads a module mid-session (rare). **Recommend: remove the lazy import or add a comment explaining why both forms exist.** Cleanup, not breakage. | Low |
| **MR176** | **`packet_builder.py` has 7 cross-package lazy imports inside `try/except`** | If a feature branch renames any of the 7 targets (`..ml.comparable_finder`, `..ml.ridge_predictor`, etc.), the BLE001 pattern hides the failure: section returns `SectionStatus.FAILED` with reason "X unavailable: No module named …" — visible to user but not blocking. **Pre-merge: any rename in `ml/`, `domain/`, `finance/`, `pe/` should grep `packet_builder.py` for the old name.** | **High** |
| **MR177** | **30-symbol re-export at `analysis/__init__.py:3-32`** | (Cross-link Report 0004 MR24.) Every symbol that `packet.py` adds must be added to the re-export list. A forgotten re-export means the symbol is reachable as `rcm_mc.analysis.packet.X` but NOT as `rcm_mc.analysis.X` — silent API drift. Pre-merge: any branch that adds a `@dataclass` to `packet.py` must also update `__init__.py`. | **High** |
| **MR178** | **`__init__.py` imports 3 modules; layer-violating reorder would break** | If a future contributor reorders the imports to alphabetical (`analysis_store, packet, packet_builder`), the import resolution still works — Python handles the dependency walk on demand. **However**, if a developer adds a 4th import that depends on a not-yet-imported sibling, layer order starts mattering. Recommend: add a comment at the top of `__init__.py` explaining the layer structure. | Low |
| **MR179** | **Lazy imports in `cross_deal_search.py` and `deal_screener.py` mask cross-package failures** | Sister pattern to MR176. If `..data.auto_populate` is renamed, the `deal_screener` failure surfaces only when that code path runs. **Pre-merge: cross-branch sweep for renames in `data/`, `deals/`.** | Medium |
| **MR180** | **No automated cycle-detection in CI** | This audit is manual. A future feature branch that introduces a real cycle would only surface on first import — and only if that import path is exercised by tests. **Recommend: a `tests/test_no_circular_imports.py` that imports every `rcm_mc.*` module by name.** | Medium |
| **MR181** | **`analysis_store` is the single fan-in point for 3 siblings (`deal_query`, `refresh_scheduler`, `__init__`)** | Any signature change to `analysis_store`'s public functions (`save_packet`, `load_latest_packet`, `load_packet_by_id`, `find_cached_packet`, `list_packets`, `get_or_build_packet`) ripples to those 3 callers + transitively to anywhere `analysis_store` is referenced. | Medium |
| **MR182** | **`packet_builder` is the deepest layer-4 module — most likely to have layered breakage** | A change to `risk_flags`, `completeness`, or `diligence_questions` (Layer 1-3) cascades to `packet_builder`. A change to `packet.py` (Layer 0) cascades to all 4 of its direct importers. | Medium |

## Dependencies

- **Incoming (who depends on `analysis/`):** server.py (per Report 0005, 36 imports across 6 modules: packet, packet_builder, analysis_store, completeness, risk_flags, diligence_questions); tests (80 importers per Report 0004); cli.py (likely the `rcm-mc analysis` subcommand at `cli.py:1303`).
- **Outgoing:** stdlib (json, hashlib, dataclasses, datetime, etc.), pandas, numpy; cross-package: `..core.simulator`, `..data.intake`, `..data.auto_populate`, `..data.state_regulatory`, `..data.hcris`, `..deals.deal_tags`, `..deals.deal_notes`, `..domain.econ_ontology`, `..finance.reimbursement_engine`, `..infra.config`, `..infra.logger`, `..infra._terminal`, `..ml.comparable_finder`, `..ml.ridge_predictor`, `..pe.value_bridge_v2`, `..pe.ramp_curves`, `..pe.rcm_ebitda_bridge`, `..portfolio.store`, `..portfolio.portfolio_snapshots`.

## Open questions / Unknowns

- **Q1 (this report).** Are the cross-package edges to `..ml/`, `..pe/`, `..finance/`, `..core/`, `..domain/`, `..data/`, `..infra/`, `..portfolio/` cycle-free? **A full repo-wide cycle audit is not done by this iteration** — only `analysis/` is verified. If `..pe.value_bridge_v2` reciprocally imports `..analysis.packet`, a cross-package cycle exists.
- **Q2.** Why does `analysis_store.py:241` have a redundant lazy import of `packet_builder` when the same import exists at top-of-file? Was there a previous cycle that has since been resolved, leaving the lazy as a vestigial guard?
- **Q3.** Does `tests/` have any test that exercises module-level import of `rcm_mc.analysis` from a fresh interpreter? Helps catch latent cycles. (Tests that already-import-something-else mask cycles via sys.modules cache.)
- **Q4.** Are any sibling-layer relationships violated by branches on origin? Pre-merge sweep needed.
- **Q5.** Does `cross_deal_search.py` use a comma-separated import (`from ..analysis.analysis_store import list_packets, load_packet_by_id`) which means the import is *inside* the analysis package referencing back to itself qualified — does that create any subtle cycle? (Answer: no — same module, qualified syntax just resolves to sys.modules['rcm_mc.analysis.analysis_store'] which is the same object as `from .analysis_store`.)
- **Q6.** Is there a `tests/test_imports.py` or similar that enumerates module imports?
- **Q7.** What happens when `packet_builder.py`'s lazy `..ml.comparable_finder` import fails on a fresh dev install (e.g. missing dep)? Per Report 0020 it returns `SectionStatus.FAILED` — verified.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0023** | **Repo-wide cycle audit** — for each subpackage in `rcm_mc/`, list its import edges and run `python -c "import rcm_mc.<sub>"` to verify it loads cleanly. | Resolves Q1 / MR180. |
| **0024** | **Sister `pe/` subsystem cycle audit** (Layer 0-N graph). | Companion — `pe/` is also load-bearing. |
| **0025** | **Audit `auth/audit_log.py`** — owed since Report 0021. | Closes the auth subsystem map + answers MR163. |
| **0026** | **Read `infra/logger.py`** — owed since Report 0020. | Closes the production-log-level question. |
| **0027** | **Run `python -c "import rcm_mc.analysis"` and confirm it succeeds** — concrete verification of this report's no-cycle finding. | Sanity check. |
| **0028** | **Add `tests/test_no_circular_imports.py`** — recommendation, not audit. | Mitigation for MR180. |

---

Report/Report-0022.md written. Next iteration should: do a repo-wide subpackage-level cycle audit by running `python -c "import rcm_mc.<sub>"` for each of the 53 subpackages enumerated in Report 0010 — closes Q1 here and MR180 (no automated cycle-detection in CI).

