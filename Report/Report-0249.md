# Report 0249: Dead Code — `engagement/` subpackage

## Scope

Dead-code audit on `RCM_MC/rcm_mc/engagement/` (store.py 707L, __init__.py 76L). Closes Report 0248 MR1023 with cross-correction. Sister to Reports 0099, 0129, 0159, 0189, 0219.

## Findings

### Cross-correction Report 0248 MR1023

**RETRACTED.** Report 0248 flagged `get_member_role` as untested/high-risk. Grep confirms:

| Site | Calls |
|---|---|
| `engagement/store.py` | 5 internal calls (lines 444, 508, 540, 585, 659) |
| `server.py` | 2 calls (6710 import + 6732 call; 6831 import + 6847 call) |
| `tests/test_engagement_pages.py` | 1 call (line 28 import + 113 call) |

**Total: 8 production references + 1 test.** Heavily used. Authorization function is exercised — tests reach it via UI page-test path. **MR1023 downgraded → CLOSED.**

### `get_member_role` IS NOT in `__all__`

`engagement/__init__.py:57-76` lists 17 public names. **`get_member_role` is absent.** Yet:

- `server.py:6710` uses `from .engagement.store import get_member_role` (deep-path import bypassing `__init__`).
- `tests/test_engagement_pages.py:28` does the same.

**This is "public-by-use, private-by-export"** — a name that is treated as public API but not declared in `__all__`. **Risk:** if a future cleanup deletes `get_member_role` thinking it's internal, server.py + test_engagement_pages.py break. Cross-link Report 0207 RBAC dataclass surface.

### External-reference tally for `__all__` (all 17 + EngagementRole)

| Symbol | External refs (excluding engagement/) |
|---|---|
| `Engagement` | 52 |
| `EngagementRole` | 46 |
| `list_comments` | 26 |
| `list_deliverables` | 23 |
| `add_member` | 21 |
| `create_engagement` | 17 |
| `get_engagement` | 15 |
| `create_deliverable` | 15 |
| `Comment` | 13 |
| `Deliverable` | 13 |
| `list_members` | 13 |
| `publish_deliverable` | 12 |
| `post_comment` | 11 |
| `list_engagements` | 8 |
| `can_publish` | 7 |
| `EngagementMember` | 3 |
| `can_view_draft` | 3 |
| `remove_member` | 2 |

**No symbol is dead.** Every `__all__` member has at least 2 external references (most have 7+).

### Lowest-use symbols (worth watching, not dead)

- `remove_member` — only 2 external refs. Both likely test + admin path. Cross-link Report 0207.
- `EngagementMember` — only 3 refs. Dataclass mostly travels under `add_member`/`list_members` return types.
- `can_view_draft` — 3 refs. Mirrored by `EngagementRole` enum-driven checks elsewhere.

### Private helpers (correctly internal)

| Symbol | Line | Usage in store.py |
|---|---|---|
| `_iso_utc` | 151 | likely 8+ (timestamp generator) |
| `_ensure_tables` | 155 | called once per init |
| `_audit` | 221 | called by every mutating function |
| `_fetch_deliverable` | 681 | called by `publish_deliverable` |

All correctly underscore-prefixed per CLAUDE.md convention. **No dead helpers.**

### Cross-correction CLAUDE.md table count

CLAUDE.md (top of file) says "**SQLite via `sqlite3` stdlib — 17 tables**". Report 0211 confirmed **21 tables** (including 4 engagement tables from Report 0183 + initiative_actuals from Report 0167). **CLAUDE.md is stale by 4 tables.** Cross-link Report 0211 schema inventory.

### CLAUDE.md test-count drift

CLAUDE.md says **"2,878 passing tests"**. Cross-link project memory `project_test_baseline.md` (314 pre-existing failures). Total test count likely shifted since CLAUDE.md was written. **Q3 below.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR1027** | **`get_member_role` is public-by-use, private-by-export** | Missing from `__all__` at engagement/__init__.py:57. A cleanup that trusts `__all__` as the public contract would silently break server.py + test_engagement_pages.py. **Add to `__all__`.** | Medium |
| **MR1028** | **CLAUDE.md table count stale (says 17, actually 21)** | Misleading for new contributors. Cross-link Report 0211. | Low |
| **MR1029** | **`remove_member` only 2 external refs** | Not dead, but suggests admin-only path. Worth verifying coverage in test_engagement_pages.py. | Low |
| **MR1023** | (RETRACTED) `get_member_role` is not untested — exercised via test_engagement_pages.py + 8 internal call sites | (closure) | (closed) |

## Dependencies

- **Incoming:** server.py, ui/engagement_pages.py, diligence/_pages.py, 3 test modules.
- **Outgoing:** stdlib + PortfolioStore.

## Open questions / Unknowns

- **Q1.** Does `test_engagement_pages.py` exercise `remove_member`?
- **Q2.** Should `get_member_role` be added to `__all__` or stay deep-import?
- **Q3.** What is the current test count vs CLAUDE.md's 2878?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0250** | Read `dev/seed.py` head (per Report 0247 MR1017). |
| **0251** | Inspect `test_engagement_pages.py` for Q1. |
| **0252** | Run pytest collection-only to answer Q3 (test-count drift). |

---

Report/Report-0249.md written. Next iteration should: read `RCM_MC/rcm_mc/dev/seed.py` head (896 LOC, NEW on feat/ui-rework-v3 — never-mapped seeder per Report 0247 MR1017).
