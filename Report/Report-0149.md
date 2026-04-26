# Report 0149: Recent Commits Digest — Reports 0119-0148 Window

## Scope

`git log --oneline -50` from HEAD `288ab26` (Report 0147 commit). Refresh of Reports 0029, 0059, 0089, 0119. Window: ~30 audit commits since Report 0119.

## Findings

### Headline numbers

- **Local main**: 1,234 commits, HEAD `288ab26`
- **Origin/main**: 1,093 commits at `3ef3aa3` (unchanged since Report 0096 — divergence persists)
- **`origin/main..HEAD`**: **137 unpushed commits** (was 115 per Report 0119; +22)
- **Window covered**: Reports 0119-0148 (~30 audit commits)

### Group breakdown (last 50 commits)

100% `audit:` — same pattern as Reports 0029/0059/0089/0119.

| Type | Count |
|---|---|
| `audit:` | 50 |
| `feature` | 0 |
| `fix` | 0 |
| `refactor` | 0 |
| `chore` | 0 |
| `docs` | 0 |
| `test` | 0 |

### Commit-volume discipline

| Commit | Reports bundled | Pattern |
|---|---|---|
| `288ab26` | 1 (0147) | one-per-commit |
| `d86b0d6` | 4 (0143-0146) | **batch flush** |
| `7428e48` | 5 (0138-0142) | **batch flush** |
| `da8c2fd` | 1 (0137) | one-per-commit |
| (rest, 0136-0119) | 1 each | one-per-commit |

**Two batch-flush commits** (`d86b0d6` 4-bundle, `7428e48` 5-bundle) — different from Reports 0089-0119 era which was strictly 1-per-commit.

**Why batch?** Per Report 0143 + 0144 + 0145 + 0146 ordering: 4 task-types arrived simultaneously (iteration prompts queued during one work session). Batched for atomic commit hygiene.

### Origin frozen at `3ef3aa3` since Report 0096

**No origin advance in 5+ days.** Per Reports 0096, 0119, 0126, 0146: origin/main HEAD is `3ef3aa3` (the SSH-quoting fix). Cross-link Report 0120 (4-commit deploy.yml debugging session 2026-04-25 16:19→16:40).

**Per Report 0126**: `feat/ui-rework-v3` advanced from 24 → 35 commits (+11 since Report 0119). Active branch is **separate** from origin/main.

### Mysterious / suspect commits

**None.** Zero reverts. Zero hot-fixes. All commit messages in window follow `audit: Report NNNN — <topic>` pattern.

### Multi-touch / wide-blast commits

**None.** Each audit commit touches exactly 1 file (or 4-5 in batch-flush case, all `Report/Report-NNNN.md`).

### Audit-vs-remediation rate (refresh)

Per Report 0091: ~501 risks. Per Report 0119: ~683. Per Report 0121: ~676 net (after 7 retractions).

**This iteration window (~30 reports)**: estimated ~150 new risks per the 5-per-report average. **Total now: ~830 risks claimed (~820 net after retractions).**

**Remediation rate**: still ~1.5%. **Gap continues to widen.**

### Cross-reference resolution rate

Iterations close prior open questions at a healthy clip:
- Report 0120 closed Report 0089 Q5 + 0119 Q1
- Report 0121 closed Report 0120 Q1
- Report 0122 closed Report 0101 MR552
- Report 0123 closed Report 0117 MR672 + 0087 MR487
- Report 0127 closed Report 0124 question
- Report 0132 closed Report 0131 Q1 + MR748
- Report 0133 closed Report 0127 MR724 + 0118 MR677
- Report 0134 closed Report 0118 MR677
- Report 0137 closed Report 0110 MR616 (last named-but-unwalked)
- Report 0143 closed Report 0116 Q4
- Report 0146 closed Report 0143 Q1 + 0116 Q4
- Report 0147 cross-corrected Report 0118 PRAGMA comment
- **Report 0148 closed Report 0118 MR678 (FK frontier complete)**

**~13 prior open questions / risks closed in this 30-iteration window.** Net new risks ~150, closures ~13. **Net outpaces by 11×.** Audit accumulation continues.

### MAJOR FINDINGS in window (chronological)

| Report | Finding |
|---|---|
| 0120 | Branch divergence at `f3f7e7f` (3-way) — MR688 critical |
| 0124 | PortfolioStore: 237 importers; **5+ modules bypass via sqlite3.connect** — MR708 critical |
| 0126 | `feat/ui-rework-v3` adds `generated_exports` writes — MR717 high |
| 0127 | feat/ui-rework-v3 merge risk scan — clean to merge but adds 2 routes; MR720 high (PHI write site) |
| 0130 | 6+ unmapped top-level entries (seekingchartis.py, demo.py, scripts/, tools/, scenarios/, readME/) — MR738 high |
| 0131 | **`configs/playbook.yaml` is unparseable YAML** — MR744 critical |
| 0136 | **pyarrow CVE-2023-47248 RCE risk on user-uploaded Parquet** — MR770 critical |
| 0144 | No shared retry helper — 4 inconsistent strategies — MR800 high |
| 0145 | dbt-core: partner can write arbitrary SQL into models/ — MR805 high |
| 0146 | All 8 quality gates pre-commit-only; none in CI — MR813 high |
| 0147 | 5th FK discovered (`sessions.username → users`) + new cascade behavior NO ACTION — MR817 high |
| 0148 | **FK frontier complete**: 5 FKs, 3 cascade behaviors. analysis_runs CASCADE confirmed (closes MR678) |

**12 high/critical findings in 30 iterations.** Audit is producing high-leverage findings.

### Branch state observation

| Branch | Status |
|---|---|
| `main` (local) | 137 ahead of origin/main, 0 behind — diverged since `f3f7e7f` |
| `origin/main` | unchanged at `3ef3aa3` for 5+ days |
| `feat/ui-rework-v3` | actively advancing per Report 0126 |
| 13 other branches | frozen 7+ days |

**Same divergence pattern continues.** No merge initiated.

### Audit chain push status (carried)

**137 unpushed commits.** MR684 (Report 0119) high — single-point-of-failure scope grows. Was 115; now 137.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR684-CARRIED** | **137 unpushed audit commits — backup risk continues** | Was 115 at Report 0119. +22 in 30 iterations. Local-disk-only home for `Report/`. | **High** |
| **MR827** | **Audit accumulation rate is ~5 risks/report; remediation rate still ~1.5%** | Net ~150 new risks per 30-report window. ~13 closures. **Audit grows faster than the remediation team can close.** Cross-link Report 0089 MR495 advisory. | (advisory) |
| **MR828** | **Two batch-flush commits in window** (`d86b0d6` 4-bundle, `7428e48` 5-bundle) | Different from prior 1-per-commit discipline. Likely a workflow shift (queued iterations). Slightly harder to bisect. | Low |

## Dependencies

- **Incoming:** all future iterations.
- **Outgoing:** git history.

## Open questions / Unknowns

- **Q1.** When will the 137-commit audit chain be pushed to origin? Disposition (merge / rebase / separate-branch) still pending.
- **Q2.** Has any high/critical MR (MR744, MR770, MR813) actually been remediated yet?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0150** | 150-report meta-survey (round number due). |
| **0151** | Comprehensive PRAGMA cross-check for all FK constraints (carry from Report 0148 follow-up). |
| **0152** | Read `cli.py` head (1,252 lines, 14+ iterations owed). |

---

Report/Report-0149.md written.
Next iteration should: 150-report meta-survey (multiple-of-30 rhythm — Reports 0001/0031/0061/0091/0121).
