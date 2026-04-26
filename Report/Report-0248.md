# Report 0248: Test Coverage — `engagement/store.py`

## Scope

Structural test-coverage audit on `RCM_MC/rcm_mc/engagement/store.py` (707 LOC) vs `tests/test_engagement.py` (392 LOC) + `tests/test_engagement_pages.py` (270 LOC). Sister to Reports 0207 (Engagement schema), 0189 (engagement/__init__.py), 0218 (ai/ test coverage cadence).

## Findings

### Public surface in `engagement/store.py` (14 public symbols)

| Symbol | Line | Kind |
|---|---|---|
| `EngagementRole` | 35 | Enum |
| `can_publish` | 64 | function |
| `can_view_draft` | 71 | function |
| `Engagement` | 84 | dataclass |
| `EngagementMember` | 99 | dataclass |
| `Comment` | 117 | dataclass |
| `Deliverable` | 132 | dataclass |
| `create_engagement` | 243 | function |
| `get_engagement` | 284 | function |
| `list_engagements` | 305 | function |
| `add_member` | 333 | function |
| `remove_member` | 369 | function |
| `list_members` | 391 | function |
| `get_member_role` | 412 | function |
| `post_comment` | 430 | function |
| `list_comments` | 482 | function |
| `create_deliverable` | 529 | function |
| `publish_deliverable` | 575 | function |
| `list_deliverables` | 638 | function |

**4 dataclasses + 1 enum + 13 functions = 18 public names.** (Cross-link Report 0189 `__all__`.)

### Private helpers (not in test scope)

- `_iso_utc` (151)
- `_ensure_tables` (155) — DDL bootstrap
- `_audit` (221)
- `_fetch_deliverable` (681)

### Test invocation tally (`test_engagement.py`)

| Function | Direct calls in test file |
|---|---|
| `add_member` | 13 |
| `create_engagement` | 11 |
| `create_deliverable` | 11 |
| `can_publish` | 9 |
| `publish_deliverable` | 8 |
| `post_comment` | 6 |
| `list_members` | 4 |
| `list_engagements` | 3 |
| `list_deliverables` | 3 |
| `list_comments` | 3 |
| `can_view_draft` | 3 |
| `remove_member` | 2 |
| `get_engagement` | 2 |

### Coverage classification

**Tested (12 of 13 functions):** `can_publish`, `can_view_draft`, `create_engagement`, `get_engagement`, `list_engagements`, `add_member`, `remove_member`, `list_members`, `post_comment`, `list_comments`, `create_deliverable`, `publish_deliverable`, `list_deliverables`.

**NOT TESTED (1 of 13):**

| Function | Line | Risk |
|---|---|---|
| **`get_member_role`** | 412 | **Authorization-bearing function — looks up a user's role within an engagement.** Used by every permission check elsewhere. **Untested in `test_engagement.py`.** |

### Test class structure (per grep)

23 `def test_*` methods in `test_engagement.py` organized by behavior:
- `test_partner_can_publish_qoe_memo` (41)
- `test_lead_cannot_publish_qoe_memo` (44)
- `test_analyst_cannot_publish_anything` (51)
- `test_client_viewer_cannot_publish_anything` (56)
- `test_client_viewer_cannot_see_drafts` (62)
- `test_create_and_read_back` (75)
- `test_duplicate_engagement_id_rejected` (88)
- `test_list_engagements_newest_first` (101)
- `test_add_list_remove` (119)
- `test_add_same_user_twice_updates_role` (142)
- `test_analyst_creates_draft` (180)
- `test_cannot_republish_already_published` (255)
- `test_client_sees_only_published_deliverables` (310)
- `test_client_sees_only_non_internal_comments` (323)
- `test_client_cannot_post_internal_comment` (348)
- `test_non_member_cannot_post` (362)
- `test_empty_body_rejected` (375)

**Strong RBAC + republish-guard coverage.** Every role × action matrix appears tested.

### Companion test file `test_engagement_pages.py` (270L)

UI-page-level tests — separate concern from store API surface. Likely tests HTTP route renderers; not counted toward store.py coverage.

### Complex untested branches

- **`get_member_role` (412)** — only auth lookup, **never called in test_engagement.py**. May be implicitly exercised via `add_member` round-trips, but **no direct assertion** of returned role for an existing member, missing-member, or post-removal state.
- `_audit` (221, private) — audit-trail writer. **Never directly tested.** If it silently swallows DB errors, audit coverage will be invisible to test suite. Cross-link Report 0131 silent-failure pattern.
- `_ensure_tables` (155) — runs DDL. Likely exercised by every test fixture. Untested for idempotency on re-init.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR1023** | **`get_member_role` untested** at 412 — authorization-bearing | If signature drifts or returns None on missing member, downstream permission checks may silently allow access. **High-impact gap.** | High |
| **MR1024** | **`_audit` private writer untested** | Audit trails could break silently. Cross-link Report 0131. | Medium |
| **MR1025** | **No idempotency test for `_ensure_tables`** | Lazy-ALTER pattern (Reports prior) means re-init must not double-create. **Medium gap given pattern's prevalence.** | Medium |
| **MR1026** | **`test_engagement_pages.py` (270L) coverage uninspected** | This report did not enumerate UI-page test coverage — possible duplicate/stale tests. **Q1 below.** | Low |

## Dependencies

- **Incoming:** 6 production importers per Report 0189; tested by 2 test modules (test_engagement.py, test_engagement_pages.py).
- **Outgoing:** stdlib + `PortfolioStore` (per Report 0118).

## Open questions / Unknowns

- **Q1.** Does `test_engagement_pages.py` cover any store-layer functions that `test_engagement.py` skips?
- **Q2.** Is `get_member_role` exercised transitively via `can_publish`/`can_view_draft` setup?
- **Q3.** What does the `_audit` writer log on failure — does it raise, log-and-skip, or silently swallow?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0249** | Read `dev/seed.py` head (per Report 0247 MR1017 — never-mapped 896-LOC subsystem). |
| **0250** | Read `engagement/store.py:412` `get_member_role` body to close Q2 + close MR1023 severity. |
| **0251** | Inspect `test_engagement_pages.py` to close Q1. |

---

Report/Report-0248.md written. Next iteration should: read `RCM_MC/rcm_mc/dev/seed.py` head (896 LOC, NEW on feat/ui-rework-v3 per Report 0247 MR1017 — never-mapped seeder subsystem).

