# Report 0036: Branch-Register Refresh (vs Report 0006)

## Scope

Re-runs the branch audit from Report 0006 to detect drift since 2026-04-25. All 14 origin branches surveyed. Same data shape: last-commit hash, date/age, ahead/behind vs main.

Prior reports reviewed: 0032-0035.

## Findings

### Branch register — current state (2026-04-25 ~13:00 CDT, 4 hours after Report 0006)

| Branch | Last commit | SHA | Age (vs Report 0006) |
|---|---|---|---|
| `main` | 2026-04-25 (4 hr ago) | `f3f7e7f` | unchanged — same `f3f7e7f` |
| `feature/deals-corpus` | 2026-04-25 (5 hr ago) | `9281474` | unchanged |
| `docs/per-file-readmes` | 2026-04-24 (24 hr ago) | `52c0e22` | unchanged |
| `fix/revert-ui-reskin` | 2026-04-24 (29 hr ago) | `b900b43` | unchanged |
| `feature/analyst-override-ui` | 2026-04-19 (6 d ago) | `953e85b` | unchanged |
| `feature/workbench-corpus-polish` | 2026-04-19 (6 d ago) | `79c4887` | unchanged |
| `feature/demo-real` | 2026-04-18 (7 d ago) | `8b11b2d` | unchanged |
| `chore/proprietary-no-contributing` | 2026-04-18 (7 d ago) | `e2d92e5` | unchanged |
| `chore/ui-polish-and-sanity-guards` | 2026-04-18 (7 d ago) | `e8f89e1` | unchanged |
| `feature/chartis-integration` | 2026-04-18 (7 d ago) | `d8f5b74` | unchanged |
| `feature/connect-partner-brain-phase1` | 2026-04-18 (7 d ago) | `5715d53` | unchanged |
| `feature/connect-partner-brain-phase0` | 2026-04-18 (7 d ago) | `005fd03` | unchanged |
| `chore/public-readme` | 2026-04-18 (7 d ago) | `81fb1e4` | unchanged |
| `feature/pe-intelligence` | 2026-04-18 (7 d ago) | `f93b185` | unchanged |

**Zero drift since Report 0006.** All 14 SHAs identical. No new commits on any origin branch in the ~30 reports since the original audit. **The repo state is frozen for the duration of this audit loop.**

### Stale branches (>30 days)

**Zero.** Same as Report 0006 — newest is main (4 hr); oldest live work is 7 days. No branch crosses the 30-day staleness threshold.

But **commit-staleness** (gap to main) continues to widen since main accumulates audit commits + remains advanced. Per Report 0029 there's been NO merge prep for any of the 8 ahead-of-main branches in the last 50 commits.

### Mysterious / structurally-divergent

Same as Report 0006:

- **Mysterious names**: zero. All branch names descriptive.
- **Structurally divergent**:
  - `feature/workbench-corpus-polish` — 21 commits, 114 files (largest blast radius). Per Report 0007 the diff is 3,336 files / +19K / −376K — catastrophically stale.
  - `feature/deals-corpus` — 33 commits, 66 files. The J2 + diligence-platform + corpus shipment.
  - `docs/per-file-readmes` — 7 commits, 45 files.

### Single-author confirmation

All 14 branches authored by `DrewThomas09 <ast3801@gmail.com>` per Report 0006. Unchanged.

### Tags

**Still zero.** No release tags. `release.yml` workflow has never fired (Report 0026).

### Local main vs origin/main

Local `main` is now **35 commits ahead of origin/main** (Reports 0001-0035 are all unpushed). Per session policy, no auto-push to main.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR307** | **Repo state frozen during audit window** | Zero new commits to origin since 2026-04-25 ~10am. The audit captures a static state — but ALSO means no new merge-prep has happened. Per Report 0029 MR273, the merge gap with `feature/deals-corpus` is widening only via main's audit-report commits (not fixes). | Medium |
| **MR308** | **Local main is 35 commits ahead of origin/main** | All 35 are audit reports (Reports 0001-0035). Push pending user authorization. **If the user resumes the loop without pushing, eventually the local copy diverges far enough to risk loss.** Recommend: pushing batches periodically. | Medium |

## Dependencies

- **Incoming:** any merge-planning effort.
- **Outgoing:** the 14 branches.

## Open questions / Unknowns

- **Q1.** Why no merge prep in 30+ iterations? Is the audit running on a frozen snapshot intentionally (correct behavior) or has the user not had time to take merge actions?
- **Q2.** Does the user want the audit reports pushed to origin/main now, or kept local until a push-batch milestone?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0037** | **Merge-risk scan: feature/deals-corpus** (the largest live branch — 822 commits behind) | Owed since Report 0006. Different from workbench-corpus-polish (Report 0007). |
| **0038** | **Test-coverage spot check** (already requested as Iteration 38). | Pending. |
| **0039** | **Per-commit walk of feature/workbench-corpus-polish's 21 commits** | Owed since Report 0007. |
| **0040** | **Cross-branch sweep**: which ahead-of-main branches modify `infra/config.py`? | Resolves the cross-branch unknown across many reports. |

---

Report/Report-0036.md written. Next iteration should: do the merge-risk scan for `feature/deals-corpus` — the largest live branch with 822 commits behind main and 33 ahead, never deeply audited since Report 0006 flagged it as the critical merge target (MR40, MR43).

