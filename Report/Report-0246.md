# Report 0246: Branch Audit — Refresh #8

## Scope

Refresh #8 (cadence: every ~30 iterations). Sister to Reports 0006/0036/0066/0096/0126/0156/0186/0206/0216.

## Findings

### Triangulation snapshot

| Branch | HEAD | Notes |
|---|---|---|
| local `main` | `6d28dd3` | 144 ahead of origin/main, 4 behind (audit chain) |
| `origin/main` | `3ef3aa3` | **STILL frozen since Report 0096** (~9+ days) — last commit "ci: fix SSH quoting" |
| `origin/feat/ui-rework-v3` | (TBD) | 59 commits ahead of origin/main — unchanged from Reports 0186/0206/0216 |
| `feature/deals-corpus` (current local) | matches `main` | active branch this session |

### 16 remote branches enumerated

Same 13-branch set + 3 already enumerated (chore/proprietary-no-contributing, chore/public-readme, chore/ui-polish-and-sanity-guards, docs/per-file-readmes, feat/ui-rework-v3, feature/analyst-override-ui, feature/chartis-integration, feature/connect-partner-brain-phase0/1, feature/deals-corpus, feature/demo-real, feature/pe-intelligence, feature/workbench-corpus-polish, fix/revert-ui-reskin). **No new branches** since Refresh #7 (Report 0216).

### 4-way divergence now

Per Report 0216 + this refresh:
- `origin/main`: 3ef3aa3 (frozen)
- local `main`: 6d28dd3 (144 ahead — all audit reports)
- `origin/feat/ui-rework-v3`: 59 ahead of origin/main (unchanged)
- `feature/deals-corpus` (current local active): tracks main

**Local main has accumulated 144 audit-only commits without push.** Cross-link Report 0216 MR1005 — origin/main remains frozen.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR1014** | **Local `main` 144 commits ahead — never pushed** | All Report-NNNN.md commits stranded locally. If laptop loss → audit chain unrecoverable. **Push to a backup remote branch recommended.** | Medium |
| **MR1005** | **Origin frozen 9+ days** + 59-commit divergence on feat/ui-rework-v3 | (carried from Report 0216) | (carried) |

## Dependencies

- **Incoming:** Reports 0006–0216 lineage.

## Open questions / Unknowns

- **Q1.** Is local main 144-commit lag intentional (audit chain stays local until landing) or oversight?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0247** | Merge risk scan (in flight). |

---

Report/Report-0246.md written.
