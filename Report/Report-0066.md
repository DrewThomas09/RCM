# Report 0066: Branch-Register Refresh #2 (vs Report 0036)

## Scope

Branch-register check. Sister to Reports 0006 + 0036.

## Findings

### State

- Origin frozen since Report 0001. Same 14 branches, same SHAs.
- Local main: ~65 commits ahead (Reports 0001-0065).

### Branch list (unchanged)

Per Report 0036 register. Zero drift since:

| Tier | Branches |
|---|---|
| Trunk | main `f3f7e7f` |
| Live (8) | feature/deals-corpus (33 ahead), feature/workbench-corpus-polish (21), feature/demo-real (10), docs/per-file-readmes (7), feature/connect-partner-brain-phase1 (7), feature/connect-partner-brain-phase0 (3), chore/proprietary-no-contributing (3), feature/analyst-override-ui (1) |
| Dead (5) | chore/public-readme, chore/ui-polish-and-sanity-guards, feature/chartis-integration, feature/pe-intelligence, fix/revert-ui-reskin |

### No new findings

Repo state continues frozen. The audit corpus is the only thing growing.

### Pre-merge sweep gaps (still owed across all reports)

- For each ahead-of-main branch: which files modify the audit-flagged risk surfaces (server.py routes, _chartis_kit.py nav, packet.py schema, pyproject.toml deps)?
- Per-commit walks for the 33 + 21 + 10 + 7 + 7 + 3 + 3 + 1 = 85 unique commits across live branches.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR434** | **Audit-vs-implementation gap widens** | 65 audit reports, 0 risk-resolution commits. **The audit is observation; remediation is a separate phase**. Pre-merge planning needs both. | (advisory) |

## Dependencies

- **Incoming:** future iterations.
- **Outgoing:** git.

## Open questions / Unknowns

None new.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0067** | Merge risk scan (already requested). |
| **0068** | Test coverage (already requested). |

---

Report/Report-0066.md written.

