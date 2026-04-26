# Report 0157: Merge Risk Scan — `feat/ui-rework-v3` Refresh

## Scope

Re-scans `feat/ui-rework-v3` after +20 commits (Report 0126: 35 ahead → Report 0156: 55 ahead). Sister to Report 0127 (initial scan at 35-commit state).

## Findings

### Diff stats — refresh

| Aspect | Report 0127 (35-commit) | Report 0157 (55-commit) | Δ |
|---|---|---|---|
| Files changed | 38 | **50** | +12 |
| Insertions | +12,043 | **+14,322** | +2,279 |
| Deletions | -706 | -753 | +47 |
| Added (A) | 28 | **39** | +11 |
| Modified (M) | 9 | **10** | +1 |
| Deleted (D) | 1 | 1 | 0 |

**Branch grew by 11 new files + 1 modification + ~2,300 added lines.**

### NEW files since Report 0127

Per `git diff --name-status`:

| New file | Purpose |
|---|---|
| `RCM_MC/rcm_mc/dev/__init__.py` | NEW subpackage `dev/` |
| **`RCM_MC/rcm_mc/dev/seed.py`** | demo-DB seeder |
| `RCM_MC/tests/test_dev_seed.py` (+209 LOC) | seeder unit tests |
| `RCM_MC/tests/test_dev_seed_integration.py` (+180 LOC) | seeder integration tests |
| `RCM_MC/docs/design-handoff/INTEGRATION_AUDIT.md` | NEW design-handoff doc |
| `RCM_MC/docs/design-handoff/SEEDER_PROPOSAL.md` | seeder design doc |

**HIGH-PRIORITY DISCOVERY**: `rcm_mc/dev/` is a brand-new SUBPACKAGE on the branch (NEVER existed on origin/main). Cross-link Report 0091/0121 backlog: a NEW package landing in this branch.

### Recent 20 commits on feat/ui-rework-v3

| Hash | Time | Subject |
|---|---|---|
| 118d8c5 | (last) | fix: covenant_status NaN crash on /dashboard against seeded DB |
| 4f0e511 | | docs(ui-rework): close out seeder — C1-C6 resolved, gaps updated |
| b2a2bf0 | | test(dev/seed): integration test + fix NaN-to-int crash on seeded DB |
| 03babe9 | | test(dev/seed): unit tests for seeder + verify path (16 tests) |
| 24b88c7 | | feat(dev/seed): --verify flag re-runs DEMO_CHECKLIST checks |
| b0b542e | | feat(dev/seed): seed generated_exports + placeholder files (block 9) |
| 26c94f0 | | feat(dev/seed): seed analysis_runs via real packet builder (block 6) |
| 6725a3e | | feat(dev/seed): seed initiative_actuals — playbook-gap signal fires |
| e49b5d4 | | feat(dev/seed): seed deals + stage history + snapshots (blocks 1-5, 8) |
| 0db3e13 | | feat(dev/seed): seeder skeleton + production-target guard + SeedResult |
| 48fabf1 | | fix(exports_index): two-color token swap to editorial palette |
| a8f8a91 | | fix(home_page): mechanical color-token swap to editorial palette |
| aacff1b | | feat(editorial-chrome): topnav sections become navigable anchors |
| c6ab593 | | docs: INTEGRATION_AUDIT Tier-3.5 finding — 9 pages bypass dispatcher |
| 85289ce | | fix: superset of legacy keys + conferences URL encoding |
| 6d985398 | | docs: INTEGRATION_AUDIT addendum — CSS-token consistency check |
| cddde6a | | feat(editorial-chrome): editorial_link() — sticky ?ui=v3 |
| 434693e | | docs: INTEGRATION_AUDIT — page inventory + tier breakdown |
| e27c5de | | docs: SEEDER_PROPOSAL — pre-Phase-2b demo DB seed script |
| 007835a | | docs: capture 4 gaps surfaced during /app?ui=v3 load |

**20 new commits split**: ~11 dev/seeder + ~5 editorial-palette/chrome + ~4 docs/audit. Disciplined: feat → test → fix → docs cycle.

### NEW dev/seed.py module — implications

The seeder writes to **`generated_exports`** (per commit `b0b542e`) AND **`analysis_runs`** (per commit `26c94f0`) AND **`initiative_actuals`** (per commit `6725a3e`).

**Cross-link**:
- Report 0133: `generated_exports` schema. Confirmed seeder writes here.
- Report 0148: `analysis_runs` schema. Confirmed.
- **`initiative_actuals` is a NEW table** never schema-walked. Cross-link Report 0151 ~7 unidentified tables. **MR853 below.**

### Schema risks (NEW since Report 0127)

| Table | Status |
|---|---|
| `generated_exports` | seeded on dev path (not new schema) |
| `analysis_runs` | seeded via real packet builder (not new schema) |
| **`initiative_actuals`** | **NEW table referenced — schema?** |
| `deals` | seeded (existing schema) |

### Production-target guard

Commit `0db3e13` "seeder skeleton + production-target guard" — implies the seeder REFUSES to run against production DB. Defensive design. **Q1**: confirm by reading guard logic.

### `--verify` flag

Commit `24b88c7`: `--verify` flag re-runs DEMO_CHECKLIST checks. Cross-link Report 0130 (DEMO_CHECKLIST.md added since Report 0127).

### Cross-link to Report 0127 risks

| Risk | Status |
|---|---|
| MR720 high (PHI mode write site) | (carried — still in branch) |
| MR722 high (NEW /forgot, /app routes) | (carried) |
| MR724 high (generated_exports writes) | **CLOSED** — Report 0133 schema-walked |
| MR725 medium (initiative_tracking +154 LOC) | (carried) |
| MR728 medium (login flow refactor stales Report 0108) | (carried) |

### NEW risks since Report 0127

- New subpackage `rcm_mc/dev/` (untracked by audit until now)
- New table `initiative_actuals` referenced in seeder
- Seeder generates fixture files on disk (Report 0136 path-traversal class concerns?)
- INTEGRATION_AUDIT.md identifies "9 pages bypass dispatcher" (per commit `c6ab593`) — significant production-side observation

### File-rename and dependency risks

Per `name-status`: 1 deletion (`_chartis_kit_v2.py`), 39 additions. **Same clean rename pattern as Report 0127.** No surprises.

### `pyproject.toml`, Dockerfile, workflow files

`grep` since Report 0127: no changes to these files. **No dep version bumps. No CI workflow changes. No Dockerfile changes.** Branch remains forward-mergeable.

### Routing surface refresh

Per Report 0127: 2 NEW routes (`/forgot`, `/app`). This iteration's commits don't add more routes (verified via diff overview). **Stable at 2 new routes.**

### Test additions — significant

| Test file | LOC |
|---|---|
| `test_ui_rework_contract.py` | +797 (was +675 per Report 0127 — grew +122) |
| `test_dev_seed.py` | +209 (NEW) |
| `test_dev_seed_integration.py` | +180 (NEW) |

**+1,186 test LOC across 3 files.** Per Report 0126 commit `0a747f1` "TODO discipline gate (18→25)" — expanded further.

### `/dashboard` NaN bug fix

Commit `118d8c5` "fix: covenant_status NaN crash on /dashboard against seeded DB" — **a real bug surfaced by the seeder**, fixed in same branch. **Good — found-and-fixed.** Cross-link Report 0140 broad-except discipline (likely the bug was hidden by some `except` block that the seeded DB hit).

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR853** | **NEW `rcm_mc/dev/` subpackage on branch** + **NEW `initiative_actuals` table reference** | Subpackage adds to ~30+ unmapped backlog. Table is the **8th unidentified table** per Report 0151. | **High** |
| **MR854** | **`fix: covenant_status NaN crash`** suggests prior production code didn't handle empty/seeded DB cleanly | Cross-link Report 0140 broad-except. The seeder exposed a defect by populating DB with realistic-but-edge values. | (closure on bug fix) |
| **MR855** | **INTEGRATION_AUDIT.md commit (`c6ab593`) finds "9 pages bypass dispatcher"** — significant pre-merge finding | The branch self-audits its own routing surface. **Cross-link Report 0124 MR708** (5+ modules bypass PortfolioStore). 9 UI pages may be a different bypass class. | High |
| **MR856** | **Branch self-discipline is high** — feat → test → fix → docs cycle, +1186 test LOC, production-target guard | Strong signals branch is mergeable. Cross-link Report 0127 conclusion: still mergeable. | (positive) |
| **MR857** | **`feat/ui-rework-v3` velocity continues** — +20 commits/day | Cross-link Report 0156 MR851. The longer it advances, the larger the merge later. | (carried) |

## Dependencies

- **Incoming:** Report 0127 baseline + Report 0156 branch state.
- **Outgoing:** unchanged from Report 0127 — pyproject/Dockerfile/workflows untouched.

## Open questions / Unknowns

- **Q1.** What is the `production-target guard` in `dev/seed.py`? (Likely an env-var or DB-path check.)
- **Q2.** What's the schema of `initiative_actuals` — never reported.
- **Q3.** Where are the "9 pages bypass dispatcher" listed in INTEGRATION_AUDIT.md?
- **Q4.** Does the seeder cover ALL the ~22+ tables, or just a subset?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0158** | Test coverage (in flight). |
| **0159** | Schema-walk `initiative_actuals` (newly discovered table per MR853). |
| **0160** | Read `INTEGRATION_AUDIT.md` (closes Q3). |
| **0161** | Read `dev/seed.py` (closes Q1+Q4). |

---

Report/Report-0157.md written.
