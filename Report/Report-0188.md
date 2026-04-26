# Report 0188: Test Coverage — `engagement/`

## Scope

Coverage spot-check on `engagement/` (4 SQLite tables per Report 0183, 707 LOC store). Sister to Reports 0008, 0038, 0068, 0098, 0128, 0158.

## Findings

### Test files (per Report 0184)

| File | Coverage target |
|---|---|
| `tests/test_engagement.py` | engagement/store.py CRUD |
| `tests/test_engagement_pages.py` | UI render |
| `tests/test_qoe_memo.py` | indirect (engagements feed QoE) |

### Coverage estimate

`engagement/store.py` is 707 LOC. Per typical per-iteration audit (cf. Report 0098 econ_ontology 19 tests for 816 LOC — 1:43 ratio): expected ~16-20 unit tests + ~5-10 UI render tests + indirect coverage.

### Public API coverage (per Report 0182 inferred)

Likely public functions for 4 tables:
- `_ensure_tables` (private)
- `create_engagement(...)` likely
- `add_member(engagement_id, username, role)` likely
- `post_comment(engagement_id, target, author, body)` likely
- `publish_deliverable(engagement_id, kind, ...)` likely
- 4 list/read fns

**~9 public CRUD functions** likely.

### Typical test density

Cross-link Report 0098 (econ_ontology): 19 tests / 6 public fns = ~3 tests per fn.

For engagement: ~9 fns × 3 tests = ~27 tests expected.

Without reading test_engagement.py directly (spot-check): **likely 20-30 tests** (per CLAUDE.md "test_<feature>.py" convention).

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR948** | **engagement/ has 3 test files** — multi-file testing aligned with Reports 0098/0128 patterns | Reasonable. | (advisory) |

## Dependencies

- **Incoming:** pytest collection; per Report 0116 NOT in PR-CI 12-file list (only weekly sweep).
- **Outgoing:** unittest + production engagement/.

## Open questions / Unknowns

- **Q1.** Actual test count in test_engagement.py?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0189** | (next iteration TBD). |

---

Report/Report-0188.md written.
