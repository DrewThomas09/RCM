# Report 0006: Branch Register — All 14 Branches on `origin/`

## Scope

This report covers **every branch on `origin` and every local branch** as of 2026-04-25. It produces a canonical branch register: name, last-commit hash, last-commit author, last-commit date, behind/ahead counts vs `origin/main`, file-diff count, branch-point hash + date, and a verdict (live work / dead / stale). Tags are also listed (none).

This audit was suggested as a follow-up in Reports 0001, 0002, 0003, 0004, and 0005, and the Iteration 6 prompt explicitly demanded it.

Prior reports reviewed before writing: 0001-0005.

## Findings

### Branch counts

- **2 local branches:** `feature/deals-corpus`, `main`.
- **14 remote branches** on `origin` (13 + main). One is the special `HEAD` ref pointing at main.
- **0 tags** on origin. Confirmed via `git tag -l` (empty).

### Authorship

- **Single author across all 14 branches:** `DrewThomas09 <ast3801@gmail.com>`. No co-authors visible in the commit-author field on any branch (Co-Authored-By lines in commit-message bodies were not enumerated this iteration). Single-author repo.

### Local main vs origin/main

- Local `main` = `06e4c04` ("audit: Report 0005 — outgoing-dep graph for server.py"). Local is **5 commits ahead of origin/main** (`f3f7e7f`). All 5 commits are this audit loop's reports (Reports 0001-0005). Not pushed yet — pending user authorization (per session policy).

### Comprehensive register (sorted by recency)

| Branch | Last commit | Date / age | SHA | Behind main | Ahead main | Files diff vs main | Branch-point | Verdict |
|---|---|---|---|---:|---:|---:|---|---|
| **`main`** | "chore(repo): deep cleanup" | 2026-04-25 (85 min ago) | `f3f7e7f` | — | — | — | — | **trunk** |
| `feature/deals-corpus` | "docs: cross-link J2 ship from README + CHANGELOG" | 2026-04-25 (3 h) | `9281474` | **822** | **33** | 66 | `389b95a` 2026-04-18 07:46 | live work |
| `docs/per-file-readmes` | "docs(file_map): full cluster analysis" | 2026-04-24 (21 h) | `52c0e22` | 168 | 7 | 45 | (not computed) | live work |
| `fix/revert-ui-reskin` | "Overnight build checkpoint: ChartisDrewIntel..." | 2026-04-24 (26 h) | `b900b43` | 173 | **0** | 0 | (already on main) | **dead** |
| `feature/analyst-override-ui` | "feat(ui): Analyst Override / Assumptions tab" | 2026-04-19 (6 d) | `953e85b` | 241 | 1 | 2 | (not computed) | live work (tiny) |
| `feature/workbench-corpus-polish` | "feat(ui): editorial reskin + fix 14 pre-existing test failures" | 2026-04-19 (6 d) | `79c4887` | 243 | **21** | **114** | `8c39d2c` 2026-04-18 15:17 | **largest live branch** |
| `feature/demo-real` | "docs: log synthetic corpus integrity violations" | 2026-04-18 (7 d) | `8b11b2d` | 243 | 10 | 12 | `8c39d2c` 2026-04-18 15:17 | live work (overlaps polish) |
| `chore/proprietary-no-contributing` | "chore: refresh seekingchartis.db" | 2026-04-18 (7 d) | `e2d92e5` | 243 | 3 | 30 | (not computed) | live work |
| `chore/ui-polish-and-sanity-guards` | "chore: remove Phase 3 + Phase 5 scratch docs" | 2026-04-18 (7 d) | `e8f89e1` | 244 | **0** | 0 | (already on main) | **dead** |
| `feature/chartis-integration` | "test: smoke + integration tests for 6 portfolio-level routes" | 2026-04-18 (7 d) | `d8f5b74` | 292 | **0** | 0 | (already on main) | **dead** |
| `feature/connect-partner-brain-phase1` | "feat(server): wire /partner-brain/modules + /module + hub promotion" | 2026-04-18 (7 d) | `5715d53` | 314 | 7 | 13 | `c24404d` 2026-04-18 08:53 | live work |
| `feature/connect-partner-brain-phase0` | "test: 13 tests for Partner Brain routes (Phase 0)" | 2026-04-18 (7 d) | `005fd03` | 314 | 3 | 5 | (not computed) | live work |
| `chore/public-readme` | "docs: add root README" | 2026-04-18 (7 d) | `81fb1e4` | 315 | **0** | 0 | (already on main) | **dead** |
| `feature/pe-intelligence` | "auto: pe_intelligence/README.md — comprehensive..." | 2026-04-18 (7 d) | `f93b185` | **588** | **0** | 0 | `f93b185` (= HEAD itself) | **dead — HEAD is ancestor of main** |

### Tier classification

**Tier 1 — trunk (1):** `main`.

**Tier 2 — live branches with unique work (8):**

| Branch | Ahead | Files | Comment |
|---|---:|---:|---|
| `feature/deals-corpus` | 33 | 66 | The J2 + diligence-platform + corpus shipment. 822 commits behind main — the largest "real merge" required. |
| `feature/workbench-corpus-polish` | 21 | **114** | **Largest file footprint** of any branch. Touches `rcm_mc/` (68 files) + `tests/` (42 files) + docs (2) + `seekingchartis.db` + `run_everything.sh`. Editorial reskin + 14 test fixes + AI settings page. |
| `feature/demo-real` | 10 | 12 | Same branch-point as `workbench-corpus-polish` (`8c39d2c`). **Overlap suspected — likely a strict subset of polish.** Pre-merge: `git log origin/main..origin/feature/demo-real` and `... origin/feature/workbench-corpus-polish` to confirm. |
| `docs/per-file-readmes` | 7 | 45 | Per-file README scaffolding + a 7-payer + 7-deal-scoring cluster analysis. Mostly docs. |
| `feature/connect-partner-brain-phase1` | 7 | 13 | Wires `/partner-brain/modules` + `/module` + hub promotion. Server routes — direct conflict with any other branch that touches `server.py`. |
| `feature/connect-partner-brain-phase0` | 3 | 5 | 13 tests for Partner Brain routes. **Pre-requisite of phase1**: phase1 should sit on top of phase0. |
| `chore/proprietary-no-contributing` | 3 | 30 | Removes `CONTRIBUTING.md` (or similar) and refreshes `seekingchartis.db`. The 30-file footprint vs 3-commit count means individual commits touch broad swaths — likely sweeping renames. |
| `feature/analyst-override-ui` | 1 | 2 | Single commit, 2 files. Smallest live branch. Adds an Analyst Override / Assumptions tab to the Analysis Workbench. |

**Tier 3 — dead branches with 0 unique commits (5, all safe to delete):**

| Branch | Behind main | Comment |
|---|---:|---|
| `feature/pe-intelligence` | 588 | `merge-base = HEAD = f93b185`. Confirmed: branch HEAD is a strict ancestor of main. Has been fully merged or otherwise superseded. **Behind by 588** but contributed nothing unique. |
| `chore/public-readme` | 315 | Already merged. |
| `feature/chartis-integration` | 292 | Already merged. |
| `chore/ui-polish-and-sanity-guards` | 244 | Already merged. |
| `fix/revert-ui-reskin` | 173 | Already merged. |

### Stale check (>30 days)

**Zero branches are date-stale.** The oldest live-work branch (`feature/connect-partner-brain-phase0`) is 7 days old; the trunk and `feature/deals-corpus` are today. The 5 dead branches are 6-7 days old. The 30-day staleness threshold is not approached. (However, **commit-staleness** — branches falling behind main — is severe: the largest gap is 822 commits on `feature/deals-corpus`, then 588 on `feature/pe-intelligence`.)

### Mysterious names check

- All branch names are descriptive enough to infer purpose. **No mysterious names.** Notable:
  - `chore/proprietary-no-contributing` — interpretation: a chore that aligns the repo with a proprietary license posture by removing `CONTRIBUTING.md`. Not yet verified by reading the diff, but the name is unambiguous.
  - `feature/connect-partner-brain-phase{0,1}` — sequential phases of the same feature. Phase0 = tests; phase1 = implementation.
  - `fix/revert-ui-reskin` — a fix that reverts a previous UI reskin attempt. Now dead (already merged into main).

### Branch-point pattern

Three of the 8 live branches share branch-point dates around 2026-04-18:

- `feature/deals-corpus` branched at `389b95a` (2026-04-18 07:46:40)
- `feature/workbench-corpus-polish` and `feature/demo-real` branched at the SAME point: `8c39d2c` (2026-04-18 15:17:41)
- `feature/connect-partner-brain-phase1` branched at `c24404d` (2026-04-18 08:53:23)

`feature/workbench-corpus-polish` and `feature/demo-real` sharing a branch-point + similar commit messages around corpus provenance strongly suggest **demo-real ⊂ workbench-corpus-polish**. Pre-merge planning should treat them as one unit.

### Tags

**N/A** — `git tag -l` returns empty. No release tags, no audit tags, no version anchors. The codebase advances purely on branch-and-merge, with no immutable version markers.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR36** | **`workbench-corpus-polish` is the structural risk** | 114 files differ from main, including 68 in `rcm_mc/` and 42 in `tests/`. That is the largest "blast radius" of any live branch. Merging requires per-subsystem review, not a single PR-merge gesture. | **Critical** |
| **MR37** | **`demo-real` likely ⊂ `workbench-corpus-polish`** | Same branch-point (`8c39d2c`) + overlapping commit subjects (`feat(corpus): provenance`, `synthetic integrity`). Merging both naively could double-apply work. Pre-merge: drop `demo-real` if confirmed-subset. | **High** |
| **MR38** | **`connect-partner-brain-phase0` should land before phase1** | Phase0 = test scaffolding; phase1 = the wiring. Merging phase1 without phase0 means the test that proves phase1 works isn't in the test suite. Pre-merge order: phase0 → phase1. | **High** |
| **MR39** | **5 dead branches consume mental overhead** | `feature/pe-intelligence`, `chore/public-readme`, `feature/chartis-integration`, `chore/ui-polish-and-sanity-guards`, `fix/revert-ui-reskin` are all 0-ahead. They imply work that was already absorbed into main, but their continued presence on origin suggests no one closed the loop. **Recommendation: delete all 5 from origin** (after a sanity-check confirming each merge-base = HEAD or each commit is in main). Cleanup, not risk. | Medium |
| **MR40** | **`feature/deals-corpus` is 822 commits behind main** | The gap is so large that a `git merge` will produce a multi-thousand-line conflict surface. Recommended: `git rebase origin/main` on a copy of `feature/deals-corpus`, resolving subsystem-by-subsystem; then merge the rebased branch. **Or:** cherry-pick the 33 unique commits onto a fresh branch off main and PR that. The cherry-pick approach is safer if the 33 commits are independent. | **Critical** |
| **MR41** | **No tags exist** | The 822-commit gap on `feature/deals-corpus` has no version anchors to bisect against. If any of the 822 main commits introduce a regression, finding the offending commit means walking 588-822 commits manually. Recommend creating tags at known-good points (e.g. `v0.6.0` from README, `v0.6.1` from CHANGELOG) before any merge work. | **High** |
| **MR42** | **Single-author repo** | Every branch authored by `DrewThomas09 <ast3801@gmail.com>`. There is no second pair of eyes on any commit. Merge planning loses a normal safety net (the "did the second engineer notice this?" check). The audit reports are partial compensation. | Medium |
| **MR43** | **`server.py` is touched by multiple ahead-of-main branches** | `feature/connect-partner-brain-phase1` adds routes (`/partner-brain/modules`, `/module`); `feature/deals-corpus` adds routes (`/reg-arbitrage`, plus 22 others); `feature/workbench-corpus-polish` likely adds routes too (the editorial reskin). Per Report 0005, server.py has 526 internal imports and 974 lazy import sites — three branches each editing it will produce ugly three-way conflicts. **Pre-merge: extract route blocks per-branch, replay in order.** | **Critical** |

## Dependencies

- **Incoming (who depends on the branch register):** the upcoming merge plan; every reader of `Report/Report-NNNN.md`; CI-driven branch protection rules (none detected yet — see Report 0001 Q3 still open on workflows). The register answers "what branches are alive" for every future report.
- **Outgoing (what the register depends on):** `git for-each-ref`, `git rev-list --left-right --count`, `git diff --name-only`, `git merge-base`. All stdlib git. No external tooling.

## Open questions / Unknowns

- **Q1 (this report).** Are `feature/workbench-corpus-polish` and `feature/demo-real` strictly subset/superset, or do they each have unique commits? Pre-merge requires confirming — `git log --oneline origin/main..origin/feature/demo-real` vs `... origin/feature/workbench-corpus-polish`.
- **Q2.** Why do all 5 dead branches still exist on origin? Was a deletion attempted and reverted? Was each closed via PR-merge or via direct push to main? The git reflog on origin would clarify, but is not accessible from a clone.
- **Q3.** What does `RCM_MC/seekingchartis.db` (touched by `chore/proprietary-no-contributing` and `feature/workbench-corpus-polish`) contain? A SQLite db tracked in git is a known footgun — every change creates a binary diff. Should it be tracked? See Report 0002's MR4 (FILE_MAP.md as generator-produced); same family of risk.
- **Q4.** Is there a CI workflow that prevents push-to-main? `git branch -vv` shows my local main is "ahead 5" of origin — the user's permission denial confirms a manual gate. But is there a server-side branch-protection rule too? Will affect the merge plan.
- **Q5.** Are there per-branch CHANGELOG / release-note files that would summarize what each branch shipped? Future iterations should grep for `BRANCH_SUMMARY.md` or similar artifacts inside each branch's checkout.
- **Q6.** Does the 30-file diff on `chore/proprietary-no-contributing` touch the LICENSE file? That bears directly on Report 0001 Q1 (license posture) and Report 0003 MR16.
- **Q7.** Why is `feature/pe-intelligence`'s last commit message "auto: pe_intelligence/README.md — comprehensive branch overview (275 modules · 2970 tests · 278 doc sections); 7 partner reflexes" if 0 ahead of main? **Did its 275-module subsystem get absorbed into main under a different name?** This is HIGH-priority — the message implies massive content that may or may not be on main.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0007** | **Confirm `demo-real ⊂ workbench-corpus-polish`** by listing each branch's unique commits and diffing. Resolves Q1, MR37. | Single biggest pre-merge ambiguity. |
| **0008** | **Investigate `feature/pe-intelligence`** — what 275-module subsystem did it ship? Is it now in `main` under `rcm_mc/diligence/` or `rcm_mc/data_public/` (Discoveries A & B from Report 0004)? | HIGH-priority. The dead branch may have been the source of the subsystem main now contains. |
| **0009** | **Dead-branch deletion plan** — for each of the 5 0-ahead branches, confirm `git merge-base origin/main origin/<branch> = origin/<branch>` (i.e. branch HEAD is ancestor of main). Then propose deletion. | Resolves MR39. Cleanup before merging anything else. |
| **0010** | **Tag known-good points on main** — at minimum `v0.6.0`, `v0.6.1`, plus a `pre-merge-feature-deals-corpus` tag right before any merge. | Resolves MR41. |
| **0011** | **`feature/deals-corpus` cherry-pick plan** — list each of the 33 unique commits, classify (independent / dependent on prior commit), propose merge sequence. | Resolves MR40. Single biggest merge to plan. |
| **0012** | **Read `rcm_mc/diligence/INTEGRATION_MAP.md`** — owed since 0004. | Likely pre-answers Q7 + Discovery A questions. |
| **0013** | **Walk `rcm_mc/cli.py`** — owed since 0003. | Closes MR14 (broken `rcm-intake` entry point). |

---

Report/Report-0006.md written. Next iteration should: confirm whether `feature/demo-real` is a strict subset of `feature/workbench-corpus-polish` by enumerating each branch's unique commits — biggest pre-merge ambiguity blocking the merge plan.

