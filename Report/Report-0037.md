# Report 0037: Merge-Risk Scan — `feature/deals-corpus`

## Scope

Merge-risk scan of `origin/feature/deals-corpus` against `origin/main` on `f3f7e7f`. Branch HEAD: `9281474` ("docs: cross-link J2 ship from README + CHANGELOG"). 33 commits ahead of main, 822 behind. The branch carries the J2 Regulatory-Arbitrage Collapse Detector + corpus + diligence platform shipment.

Owed since Report 0006 MR40, MR43; sister to Report 0007 (workbench-corpus-polish).

Prior reports reviewed: 0033-0036.

## Findings

### Total diff scale

| Metric | Value |
|---|---:|
| Files changed | **3,730** |
| Insertions | +44,665 |
| Deletions | **−517,128** |
| Files added (A) | **167** |
| Files modified (M) | 184 |
| Files deleted (D) | **3,376** |
| Files renamed (R) | 3 |

**Same catastrophically-stale pattern as `feature/workbench-corpus-polish` (Report 0007)** — branched from older state of main; main has moved forward past it. Most "deletions" are files main *added* that the branch is unaware of.

### `pyproject.toml` changes

The branch **DELETES the entire `rcm_mc_diligence` second package**:
- Removes `[diligence]` extras (4 deps: duckdb, dbt-core, dbt-duckdb, pyarrow)
- Removes `rcm-mc-diligence` console script
- Narrows `packages.find` to `["rcm_mc*"]` (drops `rcm_mc_diligence*`)
- Removes `rcm_mc_diligence` package-data globs

**Identical to `workbench-corpus-polish` per Report 0007 MR45.** Both branches converge on dropping the second package.

### Branch's unique additions (167 A)

Sample additions:
- `RCM_MC/.github/workflows/ci.yml` (relocates workflow inside RCM_MC/)
- `RCM_MC/DEMO.md`, `RCM_MC/Dockerfile`, `RCM_MC/docker-compose.yml`
- `RCM_MC/docs/CHANGES_2026-04-25.md` (the J2 ship doc per Report 0009 — this is MY recent work)
- `RCM_MC/docs/CODING_PROMPTS.md`, `FULL_SUMMARY.md`, `GETTING_STARTED.md`, `PARTNER_WORKFLOW.md`, `README_API.md`
- 22 UI route files in `rcm_mc/ui/data_public/` (per the J2 build session)
- Corpus seeds: ~120 `extended_seed_*.py` files in `rcm_mc/data_public/`
- `rcm_mc/data_public/regulatory_arbitrage_collapse.py` (the J2 module)
- `tests/test_regulatory_arbitrage_collapse.py`

These are **the work I shipped during the iteration-1 build session** (per the conversation history). The 167 added files are the J2 platform + corpus + UI pages.

### Same root-doc deletions as workbench-corpus-polish

Per the diff `--stat`: `ARCHITECTURE_MAP.md`, `AZURE_DEPLOY.md`, `CONTRIBUTING.md`, `DEPLOYMENT_PLAN.md`, `FILE_INDEX.md`, `FILE_MAP.md`, `LICENSE`, root `.gitignore`, root `.dockerignore`, 3 root workflows — all DELETED by this branch (because they didn't exist when the branch was created).

This is the **stale-branch pattern**: main added these files in the 822 commits since branch-point; the branch has no record of them, so the diff shows them as deletions.

### Branch-point comparison

Per Report 0006: branch-point `389b95a` at 2026-04-18 07:46:40. Branched ~1 day before `workbench-corpus-polish` (which branched at `8c39d2c` 15:17:41).

`feature/deals-corpus` and `workbench-corpus-polish` are **both stale** at roughly the same vintage (within hours of each other). Neither has been rebased on top of main's subsequent 800+ commits.

### Critical asymmetry vs workbench-corpus-polish

| Aspect | feature/deals-corpus | workbench-corpus-polish |
|---|---|---|
| Files changed | 3,730 | 3,336 |
| Net deletions | -517K | -376K |
| **Unique value** | **The J2 platform — 167 A files including the regulatory-arbitrage detector + 313+ data_public corpus modules** | UI editorial reskin + 14 test fixes + AI settings page |
| **Carries my commits** | **Yes** — Reports 0001-0035 are NOT here (I committed those to main) but the J2 module IS | No |
| Cherry-pick targets | The 167 A files (esp. data_public/, ui/data_public/, tests/test_regulatory_arbitrage_collapse.py) | The "editorial reskin" + AI settings + 14 fixes |

**Key insight:** `feature/deals-corpus` carries massive **net-positive value** (the J2 platform + 313 data_public modules — confirmed in Report 0004 Discovery B that data_public has 313 files on this branch). Cherry-pick is highly selective compared to `workbench-corpus-polish`.

### Cherry-pick recommendation

Per Report 0007, both branches are too stale to merge naively. Approach:

1. Rebase `feature/deals-corpus` interactively onto current `origin/main`.
2. **Auto-resolve in main's favor** for:
   - Root-doc deletions (let main's docs stand)
   - Workflow files (let main's `.github/` stand)
   - `pyproject.toml`'s `[diligence]` removal — **but verify no path requires pyarrow** post-merge (cross-link Report 0023 MR183 — `rcm_mc/diligence/ingest/` requires pyarrow on main, so removing the [diligence] extras would worsen the production install).
3. **Preserve from this branch** the 167 added files in `rcm_mc/data_public/`, `rcm_mc/ui/data_public/`, `RCM_MC/docs/CHANGES_2026-04-25.md`, `tests/test_regulatory_arbitrage_collapse.py`.
4. Cherry-pick the 33 unique commits in topological order.

### Schema / API changes

- **No `pyproject.toml` numpy/pandas pin changes** — core deps unchanged.
- **CHANGELOG.md / README.md modifications** — minor cosmetic adds (the J2 ship cross-links).
- **`rcm_mc_diligence/` package deletion** — same as workbench-corpus-polish; structural change.
- **`rcm_mc/data_public/` heavy ADDITIONS** — corpus seeds + the J2 module. **Schema is additive** (new files, not modifications to existing).

### Conflict prediction

Server.py: per Report 0005, server.py has 526 imports. The J2 build session added a route `/reg-arbitrage` (per Report 0009). This route block is on `feature/deals-corpus` but main has its own server.py. **Three-way conflict guaranteed** — main has been edited; the branch has been edited; merge-base is the older state.

`_chartis_kit.py` nav: same situation. Branch added `★ Reg Arbitrage` nav entry; main may have added other entries.

`tests/test_data_public_smoke.py`: branch added 2 entries; main's version may have changed.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR309** | **HIGH-PRIORITY: feature/deals-corpus carries 167 net-positive additions worth preserving** | Unlike workbench-corpus-polish (mostly deletions of main's recent work), this branch has substantive new content: the J2 module, 313 data_public modules, 22 UI routes, corpus seeds. **A naive merge in main's favor would lose all of this.** Pre-merge: cherry-pick the additions selectively. | **Critical** |
| **MR310** | **Branch removes [diligence] extras + `rcm_mc_diligence` package** | (Cross-link MR45.) Both stale branches converge on this removal. **Pre-merge: confirm whether main's `rcm_mc_diligence/` is intentional (Report 0003) or vestigial (both feature branches think it's vestigial).** | **High** |
| **MR311** | **Server.py route conflicts** | The branch adds `/reg-arbitrage` (per Report 0009 — my J2 ship). Main's server.py is the merge supersink (Report 0005, 526 imports). Three-way merge of route blocks. | **High** |
| **MR312** | **`_chartis_kit.py` nav-entry conflicts** | Branch adds `★ Reg Arbitrage` entry. Main may have added other entries. Three-way conflict on the nav list. | **High** |
| **MR313** | **`tests/test_data_public_smoke.py` parametrize-list conflicts** | Branch added 2 entries (BACKEND_MODULES + UI_PAGES). Main version may have new entries from other work. | **High** |
| **MR314** | **Branch is structurally older than main by 822 commits** | Per Report 0006 MR40. Same hazard as workbench-corpus-polish (Report 0007 MR44). | **Critical** |
| **MR315** | **Some "deletions" in the diff are actually main-side adds the branch never saw** | 3,376 files marked as D — but most are NOT branch-side deletions; they're files main *added* that the branch is missing. **A merge tool must be told to keep main's adds.** | Medium (mechanical) |

## Dependencies

- **Incoming:** any merge plan; my own J2 ship.
- **Outgoing:** branch-point at `389b95a` (the older main state).

## Open questions / Unknowns

- **Q1.** Does main's `rcm_mc/diligence/` subsystem (40 subdirs per Report 0004) overlap with this branch's `rcm_mc/data_public/` (313 files)? The two are different conceptual layers — but a per-file diff would surface duplicates.
- **Q2.** Has the J2 ship been re-implemented on main since? If yes, the branch's J2 work is redundant.
- **Q3.** Of the 167 net-positive additions, which are unique value vs which are leftover from main (the branch may carry an older copy of files main now has differently).

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0038** | **Test-coverage spot check** (already requested as Iteration 38). | Pending. |
| **0039** | **Per-commit walk of feature/deals-corpus's 33 commits** (cf Report 0007 owed task) | Cherry-pick plan. |
| **0040** | **Diff `rcm_mc/data_public/` between main and feature/deals-corpus** | Resolves Q1, Report 0004 MR23. |
| **0041** | **Search main for J2 module re-implementation** | Resolves Q2. |

---

Report/Report-0037.md written. Next iteration should: do a test-coverage spot check on a fresh module (since Reports 0008 covered store.py and 0020 packet_builder.py error handling) — pick `core/simulator.py`, the long-deferred Monte Carlo core that's been mentioned in Reports 0011/0012/0013/0021/0027 but never read.

