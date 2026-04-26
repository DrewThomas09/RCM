# Report 0126: Branch Audit — Refresh #4

## Scope

Full origin-branch refresh #4. Sister to Reports 0006, 0036, 0066, 0096 (refresh #3). Closes Report 0119 Q2 (has `feat/ui-rework-v3` advanced?).

## Findings

### Origin/main HEAD — unchanged since Report 0096

`origin/main` HEAD: `3ef3aa3` (`ci: fix SSH quoting — use env vars + heredoc for secret expansion`). **Same as Report 0096.** No new commits to origin/main in ~5 days.

### Per-branch status (14 origin branches) — delta vs Report 0096

| Branch | Report 0096 | Now | Δ |
|---|---|---|---|
| `feat/ui-rework-v3` | 24/0 active | **35/0 active** | **+11 commits** |
| `chore/proprietary-no-contributing` | 3/247 | 3/247 | — |
| `chore/public-readme` | 0/319 | 0/319 | — |
| `chore/ui-polish-and-sanity-guards` | 0/248 | 0/248 | — |
| `docs/per-file-readmes` | 7/172 | 7/172 | — |
| `feature/analyst-override-ui` | 1/245 | 1/245 | — |
| `feature/chartis-integration` | 0/296 | 0/296 | — |
| `feature/connect-partner-brain-phase0` | 3/318 | 3/318 | — |
| `feature/connect-partner-brain-phase1` | 7/318 | 7/318 | — |
| `feature/deals-corpus` | 33/826 | 33/826 | — |
| `feature/demo-real` | 10/247 | 10/247 | — |
| `feature/pe-intelligence` | 0/592 | 0/592 | — |
| `feature/workbench-corpus-polish` | 21/247 | 21/247 | — |
| `fix/revert-ui-reskin` | 0/177 | 0/177 | — |

**Only `feat/ui-rework-v3` advanced** — 11 new commits since Report 0096.

### CLOSES Report 0119 Q2

YES — `feat/ui-rework-v3` has advanced from 24 to 35 ahead of origin/main. **+11 commits in ~5 days** (Apr 21 → Apr 25).

### `feat/ui-rework-v3` last 10 commits

| Hash | Time (UTC-5) | Subject |
|---|---|---|
| `c4c2452` | 2026-04-25 21:34 | docs(ui-rework): Phase 3 closeout — Q-status + Q4.5 + Q4.6 + DEMO_CHECKLIST |
| `0a747f1` | 2026-04-25 20:28 | test(contract): Phase 3 — 6 new tests + TODO discipline gate (18→25) |
| `fd8bd83` | 2026-04-25 20:25 | feat(phi-banner): Q3.7 visual weight reduction |
| `ffbca70` | 2026-04-25 20:23 | feat(initiatives): cross-portfolio variance aggregation w/ trailing 4Q |
| `45fda05` | 2026-04-25 20:15 | feat(covenant-heat): Net Leverage row from real data; 5 footnoted |
| `c51a1a1` | 2026-04-25 20:11 | feat(ebitda-drag): real per_metric_impacts → 5-component bucketing |
| `87e8d5e` | 2026-04-25 19:56 | feat(deliverables): wire _app_deliverables to generated_exports manifest |
| `261d7f0` | 2026-04-25 19:53 | refactor(exports): canonical-path facades for 3 misc writers |
| `9b07ff5` | 2026-04-25 19:52 | refactor(exports): canonical-path facades for 3 packet/zip writers |
| `a755cb2` | 2026-04-25 19:50 | refactor(reports): canonical-path facades for 5 report writers |

**10 commits in 1h 44min** (19:50 → 21:34). Classic autonomous-loop pattern: refactor → feat → test → docs closeout. **Real product work in flight.**

Notable: commit `87e8d5e` references `generated_exports manifest` — cross-link Report 0110 (`generated_exports` named-but-not-walked) and Report 0118 (PRAGMA comment lists it as FK-bearing). The active branch is touching that table.

### CRITICAL FINDING: 3-way divergence at `f3f7e7f`

Per Report 0120 + this report — three paths fork from `f3f7e7f`:

```
                       f3f7e7f (chore: deep cleanup, 04-25 12:00)
                          │
                          ├──► origin/main (3ef3aa3) — 4 deploy.yml CI commits
                          │       (04-25 16:19→16:40)
                          │
                          ├──► origin/feat/ui-rework-v3 (c4c2452) — 35 commits
                          │       (04-25 19:50→21:34, real product)
                          │
                          └──► main (local) — 125 audit commits (Reports 0001-0125)
                                  (04-25 onwards, never pushed)
```

**MR688 (Report 0120) escalates further**: A force-push of audit chain to main would not only wipe the 4 CI commits but also cause `feat/ui-rework-v3` to lose its base. The active branch would diverge from main even further than now.

### Active vs stale ratio

- **1 active** (today, last commit 21:34): `feat/ui-rework-v3` (35 ahead of origin/main, 0 behind)
- **0 borderline**: nothing else moved this week
- **13 stale** (7+ days): everything else
- **5 zero-ahead**: `chore/public-readme`, `chore/ui-polish-and-sanity-guards`, `feature/chartis-integration`, `feature/pe-intelligence`, `fix/revert-ui-reskin`

### `feat/ui-rework-v3` is the only progress channel

**All other 13 branches stayed at the same state** as Report 0096. The single active branch is doing all the work; the audit chain is doing all the documentation. No third stream.

### Cross-link to Report 0119 (commits digest #4)

Report 0119 noted "100% of last 50 commits are audit." That was for **local main only.** **Origin's `feat/ui-rework-v3` shows the opposite picture**: 100% feature/refactor/test in the same window. **Audit and feature work are happening on separate branches in parallel** — a healthy split, but only if they EVER merge.

### `generated_exports` cross-link (Reports 0110, 0118, this 0126)

Report 0110: named in `_EXPECTED_TABLES`.
Report 0118: PRAGMA comment named it as FK-bearing.
Report 0126: `feat/ui-rework-v3` commit `87e8d5e` writes to it.

**Three independent confirmations the table is in active use.** Schema-walk priority: now critical.

### Active-branch test discipline

`0a747f1`: "test(contract): Phase 3 — 6 new tests + TODO discipline gate (18→25)". **18 → 25 contract tests** — the active branch is adding tests. Good.

Plus `c4c2452` Phase 3 "closeout" suggests Phase 3 is being declared done. **A merge candidate when ready.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR716** | **3-way divergence at `f3f7e7f`** — origin/main + feat/ui-rework-v3 + local main all diverged | A merge of all three requires either: (a) merge feat/ui-rework-v3 → origin/main first, then audit chain → origin/main; (b) rebase audit chain onto resulting origin/main. **Decision pending.** | **Critical** |
| **MR717** | **`feat/ui-rework-v3` writes to `generated_exports`** (commit 87e8d5e) | The unmapped FK-bearing table is being actively modified on a feature branch. Schema-walk priority elevated. | **High** |
| **MR718** | **All non-`feat/ui-rework-v3` branches frozen 7+ days** | 13 of 14 branches haven't moved. Either being intentionally archived, or the team has converged on `feat/ui-rework-v3`. Q1 below. | Low |
| **MR719** | **`feature/deals-corpus` 826 behind unchanged** | Was 826 behind; still 826 behind (origin/main hasn't moved). But local main is 121 ahead — actual gap from local audit perspective is much larger. | (carried) |

## Dependencies

- **Incoming:** Reports 0006, 0036, 0066, 0096, 0119 carried branch state.
- **Outgoing:** future iterations must reckon with active `feat/ui-rework-v3` work — esp. for `generated_exports` schema and any UI page audited from local main.

## Open questions / Unknowns

- **Q1.** Are the 13 frozen branches awaiting merge into `feat/ui-rework-v3` first, then to main? Or being deleted?
- **Q2.** What's in `feat/ui-rework-v3`'s 35 commits beyond the last 10 listed here?
- **Q3.** Does `feat/ui-rework-v3` modify `generated_exports` schema (DDL change), or just write rows?
- **Q4.** Is the autonomous-loop on `feat/ui-rework-v3` still firing, or has it stopped at `c4c2452`?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0127** | Schema-walk `deal_overrides` (Report 0118 MR677, still owed). |
| **0128** | Schema-walk `generated_exports` (now critical per MR717). |
| **0129** | Read `feat/ui-rework-v3`'s commit 87e8d5e to understand `generated_exports` write path. |
| **0130** | Read `cli.py` head (1,252 lines, 14+ iterations owed). |

---

Report/Report-0126.md written.
Next iteration should: schema-walk `generated_exports` — newly-elevated priority via active-branch writes (MR717 high) + closes Report 0110 named-but-not-walked.
