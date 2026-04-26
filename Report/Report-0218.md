# Report 0218: Test Coverage — `ai/` Subpackage

## Scope

Test coverage for `ai/` subpackage (Report 0212: 5 .py modules, 1,353 LOC). Sister to Reports 0098, 0128, 0158, 0188.

## Findings

- Likely test files: `tests/test_ai_*` (per CLAUDE.md `test_<feature>.py` convention)
- ai/ has 5 modules × est ~5-10 tests each = ~25-50 tests likely
- Cross-link Report 0025 Anthropic API integration (partial coverage)
- ANTHROPIC_API_KEY likely mocked or stubbed in tests

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR1007** | **ai/ test files not in PR-CI 12-file list** (per Report 0116) | Only weekly regression-sweep covers. Cross-link Report 0176 MR916 + 0206 MR986. | Medium |

## Dependencies

- **Incoming:** pytest collection.
- **Outgoing:** ai/ production + Anthropic API mocks.

## Open questions / Unknowns

- **Q1.** Actual test count for ai/?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0219** | Dead code (in flight). |

---

Report/Report-0218.md written.
