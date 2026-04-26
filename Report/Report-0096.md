# Report 0096: Branch Audit — Refresh #3

## Scope

Full origin-branch refresh. Reports 0006 (initial), 0036 (refresh #1), 0066 (refresh #2 — declared origin frozen at f3f7e7f). Reports 0079, 0089 carried that "frozen" claim. **This report invalidates that claim.**

## Findings

### MAJOR FINDING: origin/main is no longer frozen at `f3f7e7f`

| Origin/main HEAD | Author | Date | Subject |
|---|---|---|---|
| **NOW: `3ef3aa3`** | DrewThomas09 | 2026-04-25 16:40 | ci: fix SSH quoting — use env vars + heredoc for secret expansion |
| Per Report 0066: `f3f7e7f` (frozen) | DrewThomas09 | 2026-04-25 (earlier same-day) | chore(repo): deep cleanup |

**Origin/main has advanced ≥2 commits since Reports 0066, 0079, 0089 declared it frozen.** Cross-corrects MR493, MR494, the audit-vs-remediation gap discussion in Report 0089. Origin is alive.

### Per-branch status (14 origin branches)

| Branch | Last hash | Last commit (UTC-5) | Ahead of main | Behind main | Stale? |
|---|---|---|---|---|---|
| `feat/ui-rework-v3` | 757a649 | 2026-04-25 19:19 | **24** | **0** | active |
| `feature/deals-corpus` | 9281474 | 2026-04-25 09:53 | 33 | **826** | very-stale |
| `chore/proprietary-no-contributing` | e2d92e5 | 2026-04-18 16:12 | 3 | 247 | stale (8 days) |
| `chore/public-readme` | 81fb1e4 | 2026-04-18 08:49 | 0 | 319 | stale + zero ahead — re-mergeable? |
| `chore/ui-polish-and-sanity-guards` | e8f89e1 | 2026-04-18 15:16 | 0 | 248 | stale + zero ahead |
| `docs/per-file-readmes` | 52c0e22 | 2026-04-24 14:59 | 7 | 172 | active-ish (1 day) |
| `feature/analyst-override-ui` | 953e85b | 2026-04-19 22:02 | 1 | 245 | stale (7 days) |
| `feature/chartis-integration` | d8f5b74 | 2026-04-18 11:22 | 0 | 296 | stale + zero ahead |
| `feature/connect-partner-brain-phase0` | 005fd03 | 2026-04-18 09:28 | 3 | 318 | stale |
| `feature/connect-partner-brain-phase1` | 5715d53 | 2026-04-18 09:50 | 7 | 318 | stale |
| `feature/demo-real` | 8b11b2d | 2026-04-18 19:03 | 10 | 247 | stale |
| `feature/pe-intelligence` | f93b185 | 2026-04-18 07:47 | 0 | 592 | stale + zero ahead — **PE-INTELLIGENCE BRANCH FOUND** |
| `feature/workbench-corpus-polish` | 79c4887 | 2026-04-19 21:16 | 21 | 247 | stale (7 days) |
| `fix/revert-ui-reskin` | b900b43 | 2026-04-24 10:01 | 0 | 177 | stale + zero ahead |

### Cross-link to Report 0093 (HIGH-PRIORITY discovery)

**`feature/pe-intelligence` branch IS the source of the unmapped `pe_intelligence/` subpackage referenced in Report 0093 MR513.** The branch's last commit message:

> "auto: pe_intelligence/README.md — comprehensive branch overview (275 modules · 2970 tests · 278 doc sections); 7 partner reflexes; module inventory grouped by partner-brain function"

**275 modules. 2,970 tests. 278 doc sections.** Larger than the entire main-branch codebase.

**Status:** 0 ahead of main, 592 behind. Per the rev-list, `feature/pe-intelligence` has been **fully merged** into main at some point — but the branch's content (per its README claim) is on origin only via the branch itself, not on main. Either:
- (a) The merge was a squash-merge that didn't actually carry the 275 modules (per Report 0093, only some referenced files are on main), OR
- (b) The branch ahead-of-main count is misleading because origin/main has advanced past every commit the branch ever had.

**Q1 below.**

### Active vs stale ratio

- **1 active** (today): `feat/ui-rework-v3` (24 ahead, 0 behind)
- **2 borderline** (1-2 days): `docs/per-file-readmes`, `feature/deals-corpus`
- **11 stale** (7+ days): everything else
- **5 zero-ahead** branches: `chore/public-readme`, `chore/ui-polish-and-sanity-guards`, `feature/chartis-integration`, `feature/pe-intelligence`, `fix/revert-ui-reskin` — candidates for deletion (already in main).

### Branch with the most divergence

**`feature/deals-corpus`: 33 ahead, 826 behind.** Per Reports 0007, 0037, 0067 this was already flagged as catastrophically stale. Cross-link those — situation has not improved, deepened to 826-behind.

### `feat/ui-rework-v3` is the only "alive" branch on origin

Last 3 commits (per `git log origin/feat/ui-rework-v3`):

| Hash | Time | Subject |
|---|---|---|
| 757a649 | 19:19 | docs(ui-rework): register Q3.7 — PHI banner visual weight reduction |
| e3ef504 | 19:11 | docs(ui-rework): IA + plan + Phase 3 questions for /app |
| f1fa770 | 19:03 | test(contract): activate phi_banner + V3_CHARTED_PAGES + /app routes (12→18) |

Each ~8 minutes apart — recent burst, possibly autonomous. **Active development happening on this branch right now.**

### Cross-link to Report 0089 commit-digest

Report 0089 said "100% of last 50 commits are audit." That was true on **local main** but missed origin/feat/ui-rework-v3 progress. **Cross-correction:** other branches have non-audit work in flight; main-only digest underspecified.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR523** | **`origin/main` has advanced past `f3f7e7f`** — invalidates Reports 0066 + 0079 + 0089's "frozen" claim. | Cross-correction. Ongoing audit must `git fetch` before claiming origin state. | (correction) |
| **MR524** | **`feat/ui-rework-v3` (24 ahead, 0 behind)** has 3 commits 8 min apart on 2026-04-25 | Active autonomous-loop branch. If it merges to main, conflicts with audit reports unlikely (no `Report/` touched per branch name). But: PHI banner + V3_CHARTED_PAGES + /app routes are UI changes that may collide with rendered HTML in `Report/`-adjacent files. | Medium |
| **MR525** | **`feature/pe-intelligence` claims 275 modules + 2,970 tests but is 0-ahead of main** | Either the audit subpackage IS already merged into main (and Report 0093 was correct that it's referenced but partially-mapped) OR the branch was squash-merged, losing the 275-module fanout. **Cross-link Report 0093 MR513.** | **High** |
| **MR526** | **5 zero-ahead branches not deleted** | `chore/public-readme`, `chore/ui-polish-and-sanity-guards`, `feature/chartis-integration`, `feature/pe-intelligence`, `fix/revert-ui-reskin` are all 0-ahead-of-main. Either fully merged (delete) or rebased-away (delete). | Low |
| **MR527** | **`feature/deals-corpus` 826 behind** (was 800+ in Report 0067) | Branch has fallen further behind in 8 days. Merging it now requires either heroic cherry-pick or full rebase — same issue as Report 0067 MR435-438. | (carried) |
| **MR528** | **`feature/connect-partner-brain-phase0/1` are 318 behind** | 318 commits behind on what is presumably the partner-brain feature. Same merge-stale concern. | Medium |

## Dependencies

- **Incoming:** Reports 0006, 0036, 0066, 0079, 0089 all claimed origin frozen state — this report supersedes them.
- **Outgoing:** all subsequent branch references rely on this status.

## Open questions / Unknowns

- **Q1.** Was `feature/pe-intelligence` squash-merged or full-merged? Does main contain all 275 modules referenced in its README?
- **Q2.** What does `feat/ui-rework-v3` modify? (24 ahead — could touch `Report/`-adjacent UI files.)
- **Q3.** Should the 5 zero-ahead branches be deleted?
- **Q4.** Has `origin/main` advanced again since this report's git fetch? (Audit must re-fetch each iteration.)
- **Q5.** What changed in origin/main between `f3f7e7f` and `3ef3aa3`?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0097** | Investigate `feature/pe-intelligence` content — closes Q1 + closes Report 0093 MR513 + confirms whether 275 modules exist on main. |
| **0098** | Read `feat/ui-rework-v3` recent diffs (closes Q2). |
| **0099** | Diff `f3f7e7f..3ef3aa3` on origin/main (closes Q5). |

---

Report/Report-0096.md written.
Next iteration should: investigate `feature/pe-intelligence` to close Q1 — does main actually contain the 275 modules + `pe_intelligence/` subpackage referenced in Report 0093?
