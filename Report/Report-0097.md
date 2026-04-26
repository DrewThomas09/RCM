# Report 0097: Merge Risk Scan — `feature/pe-intelligence`

## Scope

Investigates `origin/feature/pe-intelligence` (last commit f93b185, 0-ahead/592-behind per Report 0096). Closes Report 0093 MR513 + Report 0096 Q1.

## Findings

### MAJOR FINDING: branch is a stale snapshot, NOT a merge candidate

`git diff main..origin/feature/pe-intelligence --shortstat`:

> **3,956 files changed, 16,691 insertions(+), 569,606 deletions(-)**

**Direction read:** the diff reports what changes if you walked from `main` to the branch tip. Negative numbers = main has content the branch doesn't. The branch is therefore **569,606 lines BEHIND main**, not ahead.

Per Report 0096: 0 commits ahead, 592 behind. Per this report's diff: branch represents an earlier snapshot of the codebase, missing the 592 commits' worth of additions main has accumulated since.

**The branch CANNOT be merged forward** — all its content is already on main (since 0-ahead). A reverse merge (main → branch) is structurally a no-op only commit-wise, but content-wise would attempt to wipe 569K lines.

### Per-area diff breakdown

| Area | Files changed | Insertions | Deletions |
|---|---|---|---|
| `RCM_MC/` | 1,551 | 16,719 | 357,409 |
| `vendor/` | 2,276 | 0 | 191,954 |
| `tests/` (top-level) | ~273 | (subset of above) | (subset of above) |
| Other | 129 | (small) | (small) |

`vendor/` (2,276 files, all deletions) is the biggest single chunk. This is the `vendor/cms_medicare/` tree that main has but branch doesn't — likely a subsystem added to main AFTER the branch was last updated.

### `rcm_mc/` subdirectory hit-list (top 20 by file count)

| Subdir | Files in branch diff | Per Report 0091 status |
|---|---|---|
| `data_public/` | **319** | unmapped (313 files; +6 = consistent) |
| `ui/` | **317** | partially mapped |
| `diligence/` | **185** | unmapped (40 subdirs) |
| `data/` | 22 | partial |
| `ml/` | 18 | mapped (Reports 0092-0093) |
| `pricing/` | 14 | **NEW SUBPACKAGE** — never reported |
| `market_intel/` | 12 | **NEW SUBPACKAGE** — never reported |
| `montecarlo_v3/` | 10 | **NEW SUBPACKAGE** — never reported |
| `management/` | 9 | per Report 0014 doc-gap only |
| `vbc/` | 8 | **NEW SUBPACKAGE** — never reported |
| `sector_themes/` | 8 | **NEW SUBPACKAGE** — never reported |
| `referral/` | 8 | **NEW SUBPACKAGE** — never reported |
| `exit_readiness/` | 8 | **NEW SUBPACKAGE** — never reported |
| `esg/` | 8 | **NEW SUBPACKAGE** — never reported |
| `compliance/` | 8 | partial (Reports 0043, 0072) |
| `comparables/` | 8 | **NEW SUBPACKAGE** — never reported |
| `buyandbuild/` | 8 | **NEW SUBPACKAGE** — never reported |
| `vbc_contracts/` | 7 | **NEW SUBPACKAGE** — never reported |
| `regulatory/` | 7 | **NEW SUBPACKAGE** — never reported |
| `qoe/` | 7 | **NEW SUBPACKAGE** — never reported |

### HIGH-PRIORITY DISCOVERY: 13 unmapped sibling subpackages

The branch diff reveals **13 subpackages that exist on main and have never been reported** in 96 prior reports:

`pricing/`, `market_intel/`, `montecarlo_v3/`, `vbc/`, `sector_themes/`, `referral/`, `exit_readiness/`, `esg/`, `comparables/`, `buyandbuild/`, `vbc_contracts/`, `regulatory/`, `qoe/`.

Plus partial-mappings already known: `pe_intelligence/` (Report 0093), `compliance/` (Reports 0043, 0072), `management/` (Report 0014).

### `pe_intelligence/` confirmation on main

`ls RCM_MC/rcm_mc/pe_intelligence/ | wc` reports **276 .py files** on main. The branch's last-commit-message claim of "275 modules" is **substantially correct** — the subpackage is indeed on main. `feature/pe-intelligence` was the original development branch; main has caught up and surpassed it.

### Schema / API / dependency changes

Per the diff samples viewed:
- A `claim_review` dict in `analysis/` lost `healthcare_checks` and `claude_review` keys when traversing main → branch (i.e., main ADDED those keys after the branch was last updated). **Schema additions on main, not on branch.**
- A `print_dep_graph` CLI tool (mermaid renderer) deleted on branch, present on main.
- `vbc_contracts/` (7 modules with bayesian/posterior/programs/stochastic/valuator) — entirely missing from branch — main-only.
- `vbc/shrinkage.py` and friends — main-only.

**No schema deletions in branch direction that would harm a forward merge** — the branch isn't ahead. The risk is ONLY if someone tries to ff-merge it backwards or "reset main to branch" by accident.

### Why "275 modules · 2970 tests · 278 doc sections" claim is misleading

The branch's last-commit message claimed authorship of `pe_intelligence/`. Main absorbed those changes already; main now has 276 modules in `pe_intelligence/`. The branch's claim is **stale provenance** — accurate at time of commit but no longer informative about what's NEW vs main.

### Cross-link to Reports 0061, 0091 (audit "still unmapped" lists)

Reports 0061 + 0091 listed `data_public/` (313 files) and `diligence/` (40 subdirs) as top-priority unmapped. **This branch diff confirms 13 ADDITIONAL unmapped subpackages.** Total unmapped subpackages now ≥ 16.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR529** | **Discovery: 13 unmapped sibling subpackages on main** never previously reported — `pricing`, `market_intel`, `montecarlo_v3`, `vbc`, `sector_themes`, `referral`, `exit_readiness`, `esg`, `comparables`, `buyandbuild`, `vbc_contracts`, `regulatory`, `qoe`. **HIGH-PRIORITY**. | **Critical** |
| **MR530** | **`feature/pe-intelligence` is functionally dead** — 0-ahead, 569K-line content gap behind. Should be deleted from origin to avoid future confusion. | **High** |
| **MR531** | **Anyone attempting to "restore main to feature/pe-intelligence" or to reset onto it would catastrophically drop 569K lines** — including all of `vendor/`, all of `vbc_contracts/`, and parts of every active subpackage. | **Critical** |
| **MR532** | **`vbc_contracts/` has bayesian + stochastic + valuator modules but NO TESTS in this report's sample** | Per Report 0091 the test-coverage spot is thin in general; this subpackage may have zero coverage. | (advisory) |
| **MR533** | **CLAUDE.md package-layout diagram doesn't list `pricing`, `market_intel`, `montecarlo_v3`, `vbc`, `sector_themes`, `referral`, `exit_readiness`, `esg`, `comparables`, `buyandbuild`, `vbc_contracts`, `regulatory`, `qoe`** | 13 subpackages in the codebase that the architecture doc doesn't acknowledge. **CLAUDE.md doc rot deepens.** | **Critical** |
| **MR534** | **The branch's commit message claim of "275 modules · 2970 tests · 278 doc sections" applies to MAIN, not the branch** | Anyone reading the branch's commit log might assume those 275 modules came from this branch — they're already on main; the claim represents the moment-of-merge, not the branch's unique content. | Low |

## Dependencies

- **Incoming:** Reports 0091, 0093, 0096 carried unmapped-subsystem lists. This report makes them dramatically larger.
- **Outgoing:** every future iteration must reckon with 13 newly-discovered subpackages.

## Open questions / Unknowns

- **Q1.** Is `feature/pe-intelligence` safe to delete from origin? (No commits unique → yes, but verify nothing tracks the ref.)
- **Q2.** What do each of the 13 newly-discovered subpackages contain? (One iteration each = 13 future reports.)
- **Q3.** Are any of the 13 subpackages tested? Per Report 0091: ~280 unmapped test files.
- **Q4.** Was `vendor/` added to main intentionally, or is it crufty? 2,276 vendor files is a lot for a single repo.
- **Q5.** Cross-link: do any of the 13 subpackages appear in CLAUDE.md package-layout diagram?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0098** | Map `rcm_mc/pe_intelligence/` subpackage end-to-end (closes Report 0093 MR513). |
| **0099** | Map one of: `pricing/` / `market_intel/` / `montecarlo_v3/` (HIGH-PRIORITY unmapped per MR529). |
| **0100** | 100-report meta-survey + complete unmapped-subpackage inventory. |

---

Report/Report-0097.md written.
Next iteration should: map `rcm_mc/pe_intelligence/` end-to-end (closes Report 0093 MR513).
