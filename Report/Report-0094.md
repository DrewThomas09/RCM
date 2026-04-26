# Report 0094: Incoming Dep Graph — `domain/econ_ontology.py`

## Scope

Maps every importer of `rcm_mc/domain/econ_ontology.py`. New subpackage discovered in Report 0093 MR513 (HIGH-PRIORITY). Sister to Report 0064 (audit_log incoming).

## Findings

### Module size and shape

`RCM_MC/rcm_mc/domain/econ_ontology.py` — **816 lines, 33,615 bytes**. Largest single non-server.py file mapped so far in any audit (closest is server.py partials). Per Report 0093 README cross-reference: causal-edges DAG used by ML anomaly detection + ridge predictor.

### Public surface (per `domain/__init__.py:33-50`)

`__init__.py` re-exports **14 names**:

| Type | Name |
|---|---|
| Constants | `METRIC_ONTOLOGY` |
| Enums | `Domain`, `Directionality`, `FinancialPathway`, `ConfidenceClass`, `ReimbursementType` |
| Dataclasses | `MetricDefinition`, `MechanismEdge`, `CausalGraph`, `MetricReimbursementSensitivity` |
| Back-compat alias | `ReimbursementProfile` (= `MetricReimbursementSensitivity`) |
| Helper functions | `classify_metric`, `explain_causal_path`, `causal_graph` |

### Production import sites (5 distinct files)

| # | File | Line | Symbols imported |
|---|---|---|---|
| 1 | `analysis/packet_builder.py` | 372 | (multi-symbol — full set not extracted) |
| 2 | `analysis/packet_builder.py` | 1245 | `causal_graph` |
| 3 | `pe/lever_dependency.py` | 40 | `CausalGraph, causal_graph` |
| 4 | `data/auto_populate.py` | 484 | `causal_graph` |
| 5 | `ui/methodology_page.py` | 285 | `classify_metric, explain_causal_path` |
| 6 | `domain/__init__.py` | 33 | re-export of 14 names |

**5 production sites + 1 re-export = 6 imports.** Per >5-couplers heuristic, this is **tight but not extreme** — at the boundary.

### Non-import references (string-literal / docstring)

Two files mention `econ_ontology` without importing:

- `ui/data_explorer.py:196` — string literal: `("Economic Ontology", "rcm_mc.domain.econ_ontology", "/methodology")` — appears to be a navigation-link entry pointing to a `/methodology` route.
- `analysis/packet.py:569` — Sphinx `:mod:` cross-reference docstring.
- `finance/reimbursement_engine.py:135` — docstring discriminating `MetricReimbursementSensitivity` vs `finance.reimbursement_engine.ReimbursementProfile` (cross-link to `__init__.py:31-34` back-compat note).

### Test importers (2)

- `RCM_MC/tests/test_econ_ontology.py` — direct module test.
- `RCM_MC/tests/test_lever_dependency.py` — indirect (via `pe.lever_dependency`).

### Dominant call sites

`causal_graph` (the function) is the most-imported single symbol — 3 distinct call sites (`packet_builder.py`, `auto_populate.py`, `lever_dependency.py`). Suggests this is the workhorse public API; rest of the surface less-loaded.

### Related sibling discovery

`domain/custom_metrics.py` (185 lines) is also imported by:

- `server.py:3582` — `list_custom_metrics`
- `server.py:10475` — `delete_custom_metric`
- `server.py:14784` — `register_custom_metric, CustomMetric`
- `ui/settings_pages.py:20` — `list_custom_metrics`

**4 import sites for custom_metrics.py** — separate file, separate audit needed.

### Naming-collision risk (already handled)

`__init__.py:25-28` explicitly notes:

> "MetricReimbursementSensitivity was previously named ReimbursementProfile. The old name is still exported as a back-compat alias, but new code should use the explicit one — `rcm_mc.finance.reimbursement_engine` also defines a `ReimbursementProfile` with different semantics."

**Two `ReimbursementProfile` exist with different semantics in different subpackages.** The codebase carries this disambiguation in two docstrings (`__init__.py` + `finance/reimbursement_engine.py:135`). **Easy footgun.**

### Coupling shape

| Layer | Importers |
|---|---|
| `analysis/` | 1 file (packet_builder.py — 2 lines) |
| `data/` | 1 file (auto_populate.py) |
| `pe/` | 1 file (lever_dependency.py) |
| `ui/` | 1 file (methodology_page.py) |
| Tests | 2 files |

**4 distinct subpackages depend on `domain.econ_ontology`** — fan-in is wide but shallow (1 file per subpackage, mostly 1-2 lines each). DAG is clean (no cycle observed; `domain/` is leaf).

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR516** | **`ReimbursementProfile` collision across two subpackages with different semantics** | Per `domain/__init__.py:31-34` AND `finance/reimbursement_engine.py:135`. Discriminated by docstring only — no type-system enforcement. Branch that imports the wrong one gets wrong semantics silently. | **High** |
| **MR517** | **`packet_builder.py` imports `causal_graph` at TWO sites (lines 372 + 1245)** | Code-smell: same symbol imported twice in one file means lazy-import duplication. If one is removed during refactor, the OTHER may regress. | Low |
| **MR518** | **`back-compat alias` lives in `__all__` AND comments call it deprecated** | `ReimbursementProfile` is exported in `__all__` (line 51) AND tagged "deprecated alias" (line 31). Linters won't deprecate-warn on an alias inside `__all__`. | Medium |
| **MR519** | **`ui/data_explorer.py:196` references the module by string** | A string-literal import is invisible to grep-renames. If `domain/econ_ontology.py` is moved/renamed, that string silently 404s the `/methodology` link. | Medium |
| **MR520** | **`auto_populate.py` (data/) takes a domain dependency** | Per CLAUDE.md architecture diagram: `data/` should be foundation. `data/` importing `domain/` reverses expected flow. Possibly intentional (causal_graph is leaf-ish) but worth flagging. | Medium |

## Dependencies

- **Incoming:** 5 production files (`analysis/packet_builder`, `pe/lever_dependency`, `data/auto_populate`, `ui/methodology_page`, `domain/__init__`) + 2 test files.
- **Outgoing:** Not extracted in this iteration. 816 lines, ~most likely numpy + stdlib + `domain/custom_metrics.py` cross-dep TBD.

## Open questions / Unknowns

- **Q1.** What does `packet_builder.py:372` import? (Full multi-symbol import block.)
- **Q2.** What is the structure of `METRIC_ONTOLOGY` (the 816-line file's central data structure)?
- **Q3.** Does `econ_ontology.py` itself import anything from sibling subpackages (cycle risk)?
- **Q4.** Why does `data/auto_populate.py` need `causal_graph`? (Cross-layer dependency direction.)
- **Q5.** What is the `/methodology` HTTP route — when was it added, what does it render? (Cross-link Report 0093 Q4 on `/models/quality` route registration.)
- **Q6.** Where are the two `ReimbursementProfile` semantics actually used differently? Any tests guarding the disambiguation?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0095** | Outgoing-dep graph for `domain/econ_ontology.py` (closes Q3). |
| **0096** | Read `METRIC_ONTOLOGY` body in econ_ontology.py (closes Q2). |
| **0097** | Map `rcm_mc/pe_intelligence/` (still HIGH-PRIORITY unmapped per Report 0093 MR513). |
| **0098** | Test coverage spot-check for `tests/test_econ_ontology.py` (closes part of Q6). |

---

Report/Report-0094.md written.
Next iteration should: outgoing-dep graph for `domain/econ_ontology.py` to close Q3 (cycle risk) and Q1 (full packet_builder import).
