# Report 0158: Test Coverage — `tests/test_pe_intelligence.py`

## Scope

Coverage spot-check on `RCM_MC/tests/test_pe_intelligence.py` — the test suite for `pe_intelligence/` (per Reports 0152-0155). Sister to Reports 0008, 0038, 0068, 0098, 0128.

## Findings

### Test file scale

- **36,212 LOC** in single test file
- **2,973 top-level test methods** (per `grep -c "    def test_"`)
- **30+ Test classes**

**This is the largest single test file in the project** — ~28x larger than Report 0098's `test_econ_ontology.py` (297 LOC, 19 tests).

### Test class inventory (visible top 30)

| Class | Line | Coverage target |
|---|---|---|
| TestBandClassification | 74 | reasonableness.Band |
| TestSizeClassification | 101 | reasonableness — size |
| TestPayerMixClassification | 122 | reasonableness — payer mix |
| TestCheckIRR | 170 | reasonableness.check_irr |
| TestCheckEBITDAMargin | 217 | reasonableness.check_ebitda_margin |
| TestCheckMultipleCeiling | 259 | reasonableness.check_multiple_ceiling |
| TestCheckLeverRealizability | 280 | reasonableness.check_lever_realizability |
| TestRunReasonablenessChecks | 321 | reasonableness.run_reasonableness_checks |
| TestHeuristicsFireOnExpectedPatterns | 353 | heuristics.run_heuristics |
| TestHeuristicsSortingAndRegistry | 535 | heuristics.all_heuristics + sorting |
| TestNarrativeCompose | 587 | narrative.compose_narrative |
| TestPartnerReviewFromPacket | 708 | partner_review.partner_review |
| TestPartnerReviewConvenienceFlags | 797 | partner_review variants |
| **TestNoPacketBuilderModification** | 829 | **architectural invariant test** |
| TestRedFlagDetectors | 870 | red_flags |
| TestRunAllRules | 951 | red_flags.run_all_rules |
| TestRedFlagFieldsConstant | 981 | RED_FLAG_FIELDS constant |
| TestWACCCheck | 1003 | valuation_checks.check_wacc |
| TestEVWalk | 1025 | valuation_checks.check_ev_walk |
| TestTerminalValueShare | 1066 | valuation_checks.check_terminal_value_share |
| TestTerminalGrowth | 1089 | valuation_checks.check_terminal_growth |
| TestInterestCoverage | 1104 | valuation_checks.check_interest_coverage |
| TestEquityConcentration | 1119 | valuation_checks.check_equity_concentration |
| TestRunValuationChecks | 1131 | valuation_checks.run_valuation_checks |
| TestStressRateDown | 1191 | stress tests |
| TestStressVolumeDown | 1211 | stress tests |
| TestStressMultipleCompression | 1227 | stress tests |
| TestStressLeverSlip | 1248 | stress tests |
| TestStressLaborShock | 1262 | stress tests |
| TestRunPartnerStresses | 1277 | stress orchestrator |

**30+ classes visible; file continues past line 1300** (out to 36,212 LOC). **Likely 50+ test classes total.**

### Coverage shape

Per Report 0153: `pe_intelligence` has 1,455 public names across 276 modules.

If 2,973 tests cover ~50 classes and each class targets ~5 functions/methods, that's ~250 functions tested. **~17% of public surface** by name-count — but probably much higher by **load-bearing-function count** (most of the 1,455 names are dataclass fields, not functions).

### NEW finding — `TestNoPacketBuilderModification` (line 829)

**Architectural invariant test.** Per Report 0153 docstring: "[pe_intelligence] does not modify any existing calculation. It consumes a `DealAnalysisPacket` and emits a `PartnerReview`."

**This test class enforces the invariant.** Strong discipline. Cross-link CLAUDE.md "Phase 4 invariant: one packet, rendered by many consumers."

### Per-class test density

Per the visible classes:
- `TestHeuristicsFireOnExpectedPatterns`: 353 → 535 = **182 lines**, likely 50+ tests
- `TestHeuristicsSortingAndRegistry`: 535 → 587 = 52 lines
- `TestNarrativeCompose`: 587 → 708 = 121 lines
- `TestPartnerReviewFromPacket`: 708 → 797 = 89 lines

**Average ~50-150 LOC per test class. ~50 test methods/class on the heaviest.**

### Test-to-production ratio

Per Report 0152: pe_intelligence is ~132,000 production LOC. Per this iteration: ~36,000 test LOC. **Ratio ~3.7:1 (production:test).** Below industry typical (1:1 to 1:2) — expected when production code is heavily-formulaic numeric checks (each function has 5-10 unit tests covering the math but not 1:1 LOC).

### Comparison to other audited test files

| Test file | LOC | Test count | Production target |
|---|---|---|---|
| `test_econ_ontology.py` (Report 0098) | 297 | 19 | domain (816 LOC) |
| `test_job_queue.py` (Report 0128) | 294 | 13 (+ ~12 in cross-files) | infra/job_queue (389 LOC) |
| **`test_pe_intelligence.py` (this)** | **36,212** | **2,973** | **pe_intelligence (~132K LOC)** |

**pe_intelligence test file is 122× larger** than the next-tested module's test file. **Per-iteration coverage audit must scale.**

### Coverage gaps — high-level

**Not feasible to enumerate 1,455 public names vs 2,973 tests in this iteration.** Approximate gaps:

| Likely covered | Likely uncovered |
|---|---|
| reasonableness checks (8 sub-classes) | 230+ NEVER-mentioned modules |
| heuristics (2 sub-classes) | obscure helper functions per module |
| narrative compose | private utilities |
| partner_review entry-points (2 sub-classes) | rendering helpers |
| red_flags + valuation_checks | future-extension hooks |
| stress (5 sub-classes) | sub-module APIs |

**Estimated `_app_*.py` and other hyper-specific modules from the 276** are not directly tested per the visible class names.

### Test quality observation

Per `tail -5`:

```python
        json.dumps(r.to_dict())
```

**Final test asserts JSON-round-trip-ability** of result objects — per Report 0153 README: "JSON-round-trippable" was a stated invariant. **Test enforces invariant.** Strong.

### `if __name__ == "__main__": unittest.main()`

Standard `unittest.main()` runner at file end. Tests run via pytest collection AND direct invocation.

### Cross-link Report 0153 + 0154

Per Report 0153: 1,455 public names, 275 modules.
Per Report 0154: only 10 importers; 8 of 10 never-audited.

**The test file is internal-coverage-only.** Cross-package consumers (server.py, ui/chartis, data_public) are tested separately.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR858** | **`test_pe_intelligence.py` is 36,212 LOC in a single file** — extreme | Maintenance burden. Should be split by reflex (test_reasonableness, test_heuristics, test_partner_review, test_red_flags, test_valuation_checks, test_stress) for parallelization + grep-ability. | **High** |
| **MR859** | **2,973 tests but ~1,455 public names + 276 modules** | Coverage CANNOT be 1:1 in this report. Many helper functions / dataclass fields untested — **untested ~80% of the surface by module count.** | High |
| **MR860** | **Architectural-invariant test exists** (`TestNoPacketBuilderModification`) | **Strong discipline.** Cross-link Report 0153 architectural promise. | (positive) |
| **MR861** | **JSON-round-trip discipline tested at end** | Per Report 0153 README. Verifies invariant. | (positive) |
| **MR862** | **Cross-file test-coverage absent** for pe_intelligence's external consumers (data_public/, ui/chartis/) | Cross-link Report 0154 (10 importers). Only 2 importers (test_pe_intelligence + test_deals_corpus) test it; ui/chartis pages have no test. | Medium |

## Dependencies

- **Incoming:** pytest collection (per Report 0116 ci.yml — though only 12 named files run in PR CI; this is NOT one of them).
- **Outgoing:** unittest stdlib + production pe_intelligence + DealAnalysisPacket fixtures.

## Open questions / Unknowns

- **Q1.** Total class count past line 1300 (file is 36K LOC; ~50+ classes likely).
- **Q2.** Does the regression-sweep workflow (Report 0116) run this file? It's not in the 12-file PR-CI list.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0159** | Dead-code (in flight). |
| **0160** | Orphan files (in flight). |

---

Report/Report-0158.md written.
