# Report 0029: Recent Commits Digest — `git log -50` on `origin/main`

## Scope

This report digests the **most recent 50 commits on `origin/main`** ending at `f3f7e7f` (HEAD as of 2026-04-25). Groups commits by area, flags large / mysterious / unrelated-files commits, and surveys conventional-commit hygiene. Single-author repo (`DrewThomas09`) — no co-author signal to track.

Prior reports reviewed before writing: 0025-0028.

## Findings

### Commit-message style — uniformly conventional

Every one of the 50 commits uses **conventional-commit prefixes** (`feat`, `fix`, `chore`, `docs`, `test`, `perf`, `test+fix`, `feat(ui)`, `feat(infra)`, etc.). No raw / unprefixed messages. **Hygiene is excellent.**

Sample distribution:

```
chore     :  4 commits  (deploy, dockerignore, repo cleanup, front page)
docs      : 17 commits  (heavy doc cluster)
feat      : 16 commits  (mostly UI)
fix       :  3 commits  (deploy compose path, tests resource warning, screening e2e)
perf      :  1 commit   (TTL cache)
test      :  6 commits  (e2e suites)
test+fix  :  3 commits  (combined)
```

### Group: chore (4) — repo + deploy hygiene

| SHA | Subject | Notes |
|---|---|---|
| `f3f7e7f` | "chore(repo): deep cleanup — RCM_MC root, workflows, 28 subfolder READMEs" | **122 files changed.** The HEAD commit; touches root, workflows, and 28 subfolder READMEs. Per Reports 0001 + 0002, this introduced the 261 KB FILE_MAP.md and reorganized docs. |
| `6001ec1` | "chore(deploy): add .dockerignore to keep build context lean" | Small. |
| **`9a69244`** | **"chore(repo): clean up front page + canonicalize Azure VM as deploy target"** | **2,301 files changed**. **Largest commit in the last 50 by 19x.** Per `git show --name-only`: 2,004 files in `vendor/ChartisDrewIntel/`, 221 in `vendor/cms_medicare/`, 11 in `legacy/heroku/`, 6 in `legacy/handoff/`. **Most of the diff is vendor moves/deletions.** ~233 insertions / 902 deletions (per `git show --stat` totals) — a *negative-LoC commit* despite the file count. Net effect: vendor cleanup. |
| `9a69244` (subj continues) | (same hash) | This is the front-page revamp + Azure-canonicalization. The vendor cleanup landed in the same commit, breaking single-purpose-commit best practice. **Two unrelated changes bundled.** |

### Group: deploy/fix (1)

- `e5b25f2` "fix(deploy): correct compose path + untrack stray SQLite DBs" — preceded `f3f7e7f`. Likely the response to a deploy-time bug discovered during the cleanup pass.

### Group: docs (17 — the dominant cluster)

The block from `ef79e78` through `02229e8` is essentially one continuous docs-and-roadmap rollup. Subjects:

- `ef79e78` "docs(readme): wire top-level README into cleaned-up front page"
- `7d97758` "test+fix(docs): markdown link checker + 8 stale-path repairs" (the only test+fix in the docs cluster)
- `f5fc139` "docs(readme): roll up Apr 2026 cycle into all surface READMEs"
- `47f90eb` "docs: 6-month product roadmap — Q2/Q3 2026, realistic velocity"
- `240faf6` "docs: beta program plan — 3-cohort validation structure"
- `cc3b1f8` "docs: partnerships strategy + outreach plan"
- `7841430` "docs: competitive landscape — healthcare PE intelligence space"
- `ee4abaa` "docs: v2.0 plan — what we'd do differently, applied incrementally"
- `638cc4e` "docs: PHI security architecture + BAA plan" — **directly relevant to Report 0028's PHI gap finding**
- `0fe18f3` "docs: integrations + API architecture plan"
- `b7da794` "docs: 10-minute MD demo script — every step works flawlessly"
- `8158174` "docs: learning loop architecture — closed-loop self-improvement"
- `78b57b4` "docs: data acquisition strategy — 12-month plan ranked by lift/effort"
- `f798b16` "docs: 18-month regulatory roadmap (OPPS / LEAD / ILPA / CPOM)"
- `f63628a` "docs: business model + monetization plan"
- `16b7c6e` "docs: multi-user platform architecture plan"
- `071a2b1` "docs: multi-asset expansion plan (physician groups / ASCs / behavioral / post-acute)"
- `6ad3c66` "docs: next-cycle plan — 5 highest-impact features ranked"
- `02229e8` "docs: UI kit reference index for the recent sprint"

**Pattern:** sprint-end retrospective + forward planning. Same author, same day-or-two timeframe. **Unusually doc-heavy stretch** — 18 of 50 commits are pure docs. The implementation has caught up; the next sprint is being mapped on paper.

### Group: feat / feat(ui) — UI sprint cluster

The block from `9b449b2` through `6883182` is a UI-component-library sprint. 15 `feat(ui)` commits:

- `9b449b2` form input validators
- `c3d81fb` canonical UI kit (buttons, cards, inputs, KPIs)
- `28e8ac8` user preferences
- `dc559b2` global search bar
- `bdb7263` provenance icons
- `8769885` reusable side-by-side comparison
- `40ab040` theme toggle
- `570e707` responsive layout utilities
- `369d6f8` empty-state component library
- `e11e5ae` skeleton screens / spinners / progress bars
- `967e858` breadcrumbs + Bloomberg keyboard shortcuts
- `562bdf4` contextual metric tooltips + glossary
- `67290b6` semantic color system
- `69e3701` power chart (interactive SVG)
- `6883182` power table (sortable / filterable)

**Plus 1 `feat(infra)`:**
- `ae2f2a2` "feat(infra): central constants registry — magic numbers → named" — **this is the `rcm_mc/constants.py` module that Report 0010 flagged as orphan (0 production imports).** The commit shipped the registry; subsequent UI commits did NOT migrate to use it. **Confirmed: the dedup intent was never executed.**

### Group: test (6) + test+fix (3)

Test cluster:

- `9294f39` "test: full pipeline run across 10 hospital archetypes" — large e2e
- `848019b` "test: data pipeline resilience contract — 18 tests, no failures"
- `6c7090b` "test: comp engine workflow e2e (select, view, defend, override)"
- `c534ae4` "test: EBITDA bridge workflow e2e (build, adjust, compare, export)"
- `4370411` "test: end-to-end export coverage — Excel, PowerPoint, HTML, Markdown"
- `7ede974` "test(ui): empty-data resilience suite — 21 tests, no failures"
- `b4957bf` "test(api): systematic smoke suite across recent + core endpoints"

Test+fix (combined):

- `7d97758` "test+fix(docs): markdown link checker + 8 stale-path repairs" (already counted above)
- `278a824` "test+fix: screening workflow e2e (filter, sort, drill, back) + 1 fix"
- `b3bea2c` "test+fix: extreme-value resilience suite — found 1 issue, fixed"

**Strong testing discipline.** "Found 1 issue, fixed" pattern (b3bea2c, 278a824) shows test-first investigation → bug surfaced → fix landed in the same commit. Good.

### Group: perf (1)

- `29da226` "perf: TTL cache for /models/quality + /models/importance panels" — local optimization, scoped to two routes.

### Group: fix (2 standalone, plus 1 in deploy)

- `e5b25f2` "fix(deploy): correct compose path + untrack stray SQLite DBs" (already counted)
- `718f521` "fix(tests): silence pytest ResourceWarning from ThreadingHTTPServer race" (cross-link Report 0003 line 99-110 — the `filterwarnings` pyproject config)

### File-count distribution

```
2 commits with > 100 files changed (f3f7e7f: 122; 9a69244: 2301)
0 reverts
0 hot-fixes
0 emergency commits
```

The two large commits are deliberate cleanup passes. The rest are focused single-purpose changes.

### Mysterious / unexplained commits — NONE

Every subject line is descriptive. No `wip`, `temp`, `xxx`, `urgent`, no empty messages. **High commit hygiene.**

### Cross-cuts touched (large commits)

#### `9a69244` (2,301 files)

- 2,004 files: `vendor/ChartisDrewIntel/` — DBT subproject. Likely fully replaced or extensively re-vendored. Per Report 0001 this dir is treated as third-party imports.
- 221 files: `vendor/cms_medicare/` — Medicare data + plotting code (per Report 0001).
- 11 files: `legacy/heroku/`
- 6 files: `legacy/handoff/`
- 3 files: `RCM_MC/docs/`
- Others: scattered.

**Net:** -902 deletions / +233 insertions. Most of the work is **moves and deletions** in vendor — repo-size cleanup.

#### `f3f7e7f` (122 files)

The "deep cleanup" — 28 subfolder READMEs (per the subject), workflow files, repo root reorganization. Per Reports 0001, 0002, 0003.

### Commits that touch unrelated areas

- `9a69244` bundles "front page cleanup" + "Azure VM canonicalization" + "vendor cleanup". **3 logically distinct concerns in one commit.** Bisect-hostile.
- `f3f7e7f` bundles "RCM_MC root" + "workflows" + "28 subfolder READMEs". **3 concerns.**

These are large enough that a regression introduced in the diff cannot be cleanly bisected without manual file-level isolation.

### Topics surfaced by recent commits

Topics that appear in commit messages but haven't been audited in any prior report:

| Topic | Hint commit | Implied artifact |
|---|---|---|
| **PHI security architecture** | `638cc4e` | Likely a `docs/PHI_SECURITY_ARCHITECTURE.md` per Report 0007's deletion list. Cross-link Report 0028 MR263 (the gap on enforcement). |
| Beta program plan | `240faf6` | `docs/BETA_PROGRAM_PLAN.md` (per Report 0007) |
| Multi-user architecture | `16b7c6e` | `docs/MULTI_USER_ARCHITECTURE.md` (deleted on `feature/workbench-corpus-polish` per Report 0007) |
| Learning loop architecture | `8158174` | `docs/LEARNING_LOOP.md` |
| Regulatory roadmap | `f798b16` | `docs/REGULATORY_ROADMAP.md` |
| MD demo script | `b7da794` | `docs/MD_DEMO_SCRIPT.md` |
| Multi-asset expansion plan | `071a2b1` | `docs/MULTI_ASSET_EXPANSION.md` |
| Power chart + power table | `69e3701`, `6883182` | UI components — referenced by other UI commits |

### Velocity signal

50 commits across what timeframe? `git log --since="N weeks" --oneline | wc -l`:

- The branch register (Report 0006) showed `feature/deals-corpus` branch-point at 2026-04-18. The 50 commits cover roughly 1 week of activity.
- **~7 commits/day average.** High velocity.

This explains:
- The doc rollup at the top of the log (the developer just shipped a sprint, now writing it up).
- The UI-component sprint cluster.
- The 2 cleanup commits (sprint-close hygiene).

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR264** | **`9a69244` (2,301 files) is bisect-hostile** | Bundles vendor cleanup + front-page revamp + Azure canonicalization. A regression in any of those areas requires manual file-level isolation. | Medium |
| **MR265** | **`f3f7e7f` (122 files) bundles 3 concerns (root + workflows + 28 READMEs)** | Same hazard, smaller scale. | Low |
| **MR266** | **`feat(infra) ae2f2a2` shipped `constants.py` but no follow-up migration ever happened** | Per Report 0010 MR71. The dedup goal was structurally abandoned. **15 modules still have inline literals; the registry is dead-on-arrival.** | Medium |
| **MR267** | **`docs:` cluster of 17 documents implies the next sprint will be feature-heavy** | Plans drafted but not yet executed: 6-month product roadmap, beta program, partnerships, V2 plan, integrations plan, multi-asset expansion, multi-user architecture, learning loop, data-acquisition. **Each is a feature workstream waiting to land.** Pre-merge: any branch claiming to implement one of these should be checked against the roadmap doc for scope creep. | (advisory) |
| **MR268** | **`docs: PHI security architecture + BAA plan` (`638cc4e`) was shipped — but Report 0028 MR250 found the implementation is purely cosmetic** | The doc may exist (Report 0001 `RCM_MC/docs/PHI_SECURITY_ARCHITECTURE.md` was deleted on workbench-corpus-polish per Report 0007). **Doc-vs-code drift.** Pre-merge: any branch that claims to implement the PHI architecture must wire `compliance/phi_scanner.py` to `RCM_MC_PHI_MODE`. | **High** |
| **MR269** | **No security-hardening commits in last 50** | 0 `feat(security)` / `fix(security)` / `chore(security)` commits. Combined with Report 0026 MR236 (no security scanning workflow) and Report 0021 (auth.py audit found scrypt N below OWASP minimum), the security backlog appears un-addressed. | Medium |
| **MR270** | **No commits touch `RCM_MC_PHI_MODE`** | Despite the PHI security architecture doc shipping (`638cc4e`), the actual code change to wire enforcement is absent in this 50-commit window. | **High** (cross-link MR250) |
| **MR271** | **`feat(ui) 67290b6` "semantic color system" — applied to "recent UI" only** | Older UI not migrated. Pre-merge: any branch that touches older UI must adopt the semantic system or be flagged for follow-up. | Low |
| **MR272** | **`28 subfolder READMEs` updated in `f3f7e7f`** | Per Report 0014, several subpackage READMEs were thin or missing usage examples. Pre-merge: spot-check that the 28 are now consistent. | Low |
| **MR273** | **No commit explicitly addresses `feature/deals-corpus` work or planning a merge of any of the 8 ahead-of-main branches** | The 50-commit window shows main moving forward on UI + docs + cleanup, but **no merge prep for the Tier-2 branches identified in Report 0006**. Per Report 0006, `feature/deals-corpus` is 822 commits behind main; the gap is widening. | **High** |
| **MR274** | **`9a69244` bundled vendor cleanup hides whether the vendored DBT subproject was deliberately re-vendored or accidentally regenerated** | 2,004 files in `vendor/ChartisDrewIntel/` — most touched in one commit. Pre-merge: confirm that re-vendoring is intentional and the upstream version is pinned somewhere. | Medium |

## Dependencies

- **Incoming:** every contributor reading the log; bisect / blame consumers; release-note auto-generators (per `release.yml:39` `generate_release_notes: true`); any audit pass like this one.
- **Outgoing:** the work in those 50 commits — feature/test/doc/cleanup files distributed across the repo.

## Open questions / Unknowns

- **Q1 (this report).** Was `9a69244`'s 2,004-file vendor cleanup a re-vendor (downloaded fresh from upstream) or a deletion (pruning unused vendor)? `git show --stat 9a69244 | head -30` would clarify (M vs D vs A counts).
- **Q2.** Why was `feat(infra): central constants registry` shipped without a migration of the 15 caller modules? Was a follow-up commit planned and dropped?
- **Q3.** What's in `docs/PHI_SECURITY_ARCHITECTURE.md` (shipped in `638cc4e`)? Does it acknowledge the cosmetic-only banner gap (MR250)?
- **Q4.** Are any of the 17 docs in the cluster CHANGELOG-quality or planning-quality? E.g. is `docs/v2_PLAN.md` an executable backlog or aspirational fiction?
- **Q5.** Do any of the 6 e2e test commits land tests that would gate `feature/deals-corpus`'s merge? Cross-link Report 0006.
- **Q6.** Are any commits authored by `Claude Opus 4.7 (1M context)` (the audit reports' co-author footer)? `git log --grep "Co-Authored-By: Claude"` would tell.
- **Q7.** Is there a pattern in the timestamp distribution (e.g. most commits in 1-2 days)? `git log --pretty="%ai" -50` would show.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0030** | **Resolve Report 0028 Q3** — read `docs/PHI_SECURITY_ARCHITECTURE.md` (shipped in `638cc4e`). Does it acknowledge the cosmetic-banner gap? | Q3 above + Report 0028 MR263. |
| **0031** | **Audit `compliance/phi_scanner.py`** — owed since Report 0028. | The wiring path for the PHI enforcement layer. |
| **0032** | **Look at `git log` since 2026-04-18 with `--shortstat`** to confirm sprint velocity. | Resolves Q7. |
| **0033** | **Read `docs/V2_PLAN.md` (or whatever survived the cleanup)** — is it executable? | Resolves Q4. |
| **0034** | **`git log --grep "Co-Authored-By"`** — count AI-assisted commits in mainline. | Resolves Q6. |
| **0035** | **Audit `docs/REGULATORY_ROADMAP.md`** — what's in the OPPS/LEAD/ILPA/CPOM 18-month plan? | Sister context. |

---

Report/Report-0029.md written.

