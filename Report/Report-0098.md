# Report 0098: Test Coverage — `domain/econ_ontology.py`

## Scope

`RCM_MC/rcm_mc/domain/econ_ontology.py` (816 lines, audited Reports 0094 + 0095) vs `RCM_MC/tests/test_econ_ontology.py` (297 lines). Closes Report 0094 follow-up "0098".

## Findings

### Public surface inventory (per `grep -n "^def \|^class "`)

| # | Symbol | Line | Kind |
|---|---|---|---|
| 1 | `Domain` | 35 | Enum (public) |
| 2 | `Directionality` | 48 | Enum (public) |
| 3 | `FinancialPathway` | 54 | Enum (public) |
| 4 | `ConfidenceClass` | 63 | Enum (public) |
| 5 | `ReimbursementType` | 76 | Enum (public) |
| 6 | `MechanismEdge` | 87 | Dataclass (public) |
| 7 | `MetricReimbursementSensitivity` | 108 | Dataclass (public) |
| 8 | `MetricDefinition` | 138 | Dataclass (public) |
| 9 | `CausalGraph` | 168 | Dataclass (public) |
| 10 | `_r` | 192 | Helper (private) |
| 11 | `_m` | 199 | Helper (private) |
| 12 | `causal_graph()` | 680 | **Public function** |
| 13 | `_infer_effect_direction` | 707 | Helper (private) |
| 14 | `classify_metric()` | 725 | **Public function** |
| 15 | `_reimb_summary` | 742 | Helper (private) |
| 16 | `explain_causal_path()` | 762 | **Public function** |
| — | `METRIC_ONTOLOGY` | (constant) | Public constant (~480 lines, lines 200-679) |

**Public surface: 3 functions + 5 enums + 4 dataclasses + 1 large constant = 13 named exports.** Matches `domain/__init__.py:51-58` `__all__` of 14 (the 14th is `ReimbursementProfile` back-compat alias per Report 0094 MR516).

### Test-file inventory (`tests/test_econ_ontology.py`)

5 test classes, 19 test methods, 297 lines:

| Class | Lines | Tests | Target |
|---|---|---|---|
| `TestOntologyCoverage` | 79-110 | 4 | METRIC_ONTOLOGY completeness + `classify_metric()` |
| `TestReimbursementSensitivity` | 112-131 | 4 | reimbursement scoring matrix |
| `TestCausalGraph` | 134-175 | 5 | `causal_graph()` + invariants |
| `TestCausalPathExplanations` | 177-230 | 5 | `explain_causal_path()` |
| `TestPacketIntegration` | 232-end | 3 | end-to-end via packet_builder |

### Coverage of public symbols

| Public symbol | Tested? | Mode |
|---|---|---|
| `Domain` | indirect (every metric definition uses it; verified via test_every_definition_is_well_formed) | data validation |
| `Directionality` | indirect | data validation |
| `FinancialPathway` | indirect | data validation |
| `ConfidenceClass` | indirect | data validation |
| `ReimbursementType` | **direct** | TestReimbursementSensitivity (4 tests across DRG/FFS/capitated cases) |
| `MechanismEdge` | indirect via causal_graph() | structural |
| `MetricReimbursementSensitivity` | **direct** | TestReimbursementSensitivity (4 tests) |
| `MetricDefinition` | **direct** | test_every_definition_is_well_formed |
| `CausalGraph` | **direct** | TestCausalGraph (5 tests) |
| `causal_graph()` | **direct** | TestCausalGraph.test_graph_has_nodes_and_edges |
| `classify_metric()` | **direct** | TestOntologyCoverage.test_classify_metric_returns_the_entry + test_classify_unknown_raises |
| `explain_causal_path()` | **direct** | TestCausalPathExplanations (5 tests) |
| `METRIC_ONTOLOGY` | **direct** | TestOntologyCoverage.test_every_required_metric_has_a_definition + test_every_definition_is_well_formed |

**Every public function has at least one direct test.** Every enum used at least transitively. Every dataclass exercised.

### Tested invariants (notable)

1. `test_no_self_loops` (TestCausalGraph:157) — DAG invariant: no metric is its own parent.
2. `test_financial_metrics_end_in_ebitda` (line 165) — every financial-pathway metric reaches EBITDA in the graph. **Strong invariant.**
3. `test_classify_unknown_raises` (line 105) — error-path explicitly tested.
4. `test_unknown_metric_returns_safe_fallback` (line 213) — graceful-fallback path explicitly tested.
5. `test_attach_helper_is_idempotent` (line 264) — idempotency invariant verified.
6. `test_profile_metric_roundtrip_preserves_ontology_fields` (line 279) — JSON round-trip invariant.

### Gaps in coverage

| Gap | Risk |
|---|---|
| `_r`, `_m`, `_infer_effect_direction`, `_reimb_summary` private helpers | acceptable — private, exercised via public callers |
| No test of `MechanismEdge` constructed directly (only via `causal_graph()`) | low — dataclass; would catch field-rename only if direct |
| No test that every `Domain` enum value is referenced by ≥1 metric | medium — orphan enum values would slip through |
| No test of `Directionality` HIGHER_IS_BETTER vs LOWER_IS_BETTER classification correctness for every metric | medium — a wrong directionality silently flips a UI badge |
| No test of `FinancialPathway` correctness per metric | medium — same as above |
| `TestPacketIntegration` depends on `packet_builder.py` (Report 0020 + 0093) — heavyweight; if it breaks, the integration tests fail for unrelated reasons | low — coupling risk |

### Test patterns observed

- Pure stdlib unittest (no pytest fixtures, no mocks). Per CLAUDE.md "no mocks for our own code" — confirmed.
- TestPacketIntegration uses real `packet_builder` — exercises real path. Per CLAUDE.md.
- Test data is the literal `METRIC_ONTOLOGY` from production — no fixtures, no synthetic mocks. **Strong.**

### Cross-link to Report 0091 test coverage

Report 0091 listed "tests directory: ~280+ unmapped test files" as Q. This iteration covers 1 (`test_econ_ontology.py`). 279 still unmapped.

### Per-line ratio

- Module: 816 production lines.
- Tests: 297 test lines, 19 tests.
- **Ratio**: 1 test per 43 lines of production. Healthy by industry norms (typical 1:50-100).
- Tests/public-symbol: 19 tests / 13 public symbols = ~1.5 tests per symbol. Above average.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR535** | **No coverage check that every `Domain` enum value is non-orphan** | Adding a new `Domain.X` without a metric using it slips through tests, then a UI tab renders empty. | Low |
| **MR536** | **No per-metric Directionality / FinancialPathway correctness tests** | A metric mis-classified as HIGHER_IS_BETTER when it should be LOWER_IS_BETTER silently flips a UI green→red signal. Tests verify shape, not semantic correctness. | **Medium** |
| **MR537** | **TestPacketIntegration imports `packet_builder` (heavyweight)** | If packet_builder breaks for an unrelated reason, 3 ontology tests fail spuriously. Cross-link Report 0020 (packet_builder error handling) + Report 0093 (packet_builder ml-coupling). | Low |
| **MR538** | **No coverage for the back-compat alias `ReimbursementProfile`** | Per Report 0094 MR516: a name collision exists with `finance/reimbursement_engine.ReimbursementProfile`. Tests don't verify the alias still resolves correctly. | Medium |

## Dependencies

- **Incoming:** test_econ_ontology.py is invoked by pytest collection. Per Report 0026 GitHub Actions runs `pytest`.
- **Outgoing:** unittest stdlib + production `domain.econ_ontology` + `analysis.packet_builder` (TestPacketIntegration only).

## Open questions / Unknowns

- **Q1.** Does `tests/test_lever_dependency.py` (per Report 0094 incoming-dep finding) cover `domain.econ_ontology` indirectly? Adds to coverage if so.
- **Q2.** Does CI fail on a new metric being added to METRIC_ONTOLOGY without a corresponding `Domain` enum value? (Schema-evolution invariant.)
- **Q3.** Are the 5 `TestCausalPathExplanations` test cases (denial_rate, days_in_ar, clean_claim_rate, net_collection_rate, unknown) representative, or is a sweep of all metrics needed?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0099** | Map `rcm_mc/pe_intelligence/` (HIGH-PRIORITY — Report 0093 MR513 + 0096 + 0097). |
| **0100** | 100-report meta-survey + complete unmapped-subpackage inventory (per Report 0097). |
| **0101** | Test coverage spot-check on `tests/test_lever_dependency.py` (Q1). |

---

Report/Report-0098.md written.
Next iteration should: map `rcm_mc/pe_intelligence/` end-to-end (HIGH-PRIORITY discovery from Reports 0093, 0096, 0097).
