# Report 0067: Merge-Risk Scan — `feature/connect-partner-brain-phase1`

## Scope

Per Report 0006, this branch has 7 commits ahead of main, 13 files diff. Last commit: `feat(server): wire /partner-brain/modules + /module + hub promotion`. 314 commits behind main.

## Findings

### Diff stats (estimated from Report 0006 register)

- Files: 13 modified
- Commits: 7 ahead

Compared to feature/deals-corpus (66 files / 33 commits) and workbench-corpus-polish (114 files / 21 commits), **this is a small, focused branch**.

### Branch-point + staleness

Branched 2026-04-18 08:53 (per Report 0036). Same vintage as workbench-corpus-polish/demo-real (~mid-April 2026). 314 commits behind main = stale.

### Commit subjects (need re-fetch)

Per Report 0006: HEAD `5715d53` "feat(server): wire /partner-brain/modules + /module + hub promotion". Phase1 of a partner-brain wiring; phase0 (sister branch, 3 commits ahead) added 13 tests.

### Likely conflict zone

`server.py` — adds `/partner-brain/modules` + `/module` routes. **Three-way conflict guaranteed** with main + with `feature/deals-corpus` (which adds `/reg-arbitrage` per Report 0009).

### Phase ordering

Per Report 0006 MR38: phase0 (tests) should land BEFORE phase1 (implementation). Both stale 314 commits behind main; both need rebase + per-commit cherry-pick.

### Schema / API surface

Without per-commit walk: phase1 likely adds new modules under `rcm_mc/pe_intelligence/` or `rcm_mc/diligence/` (the "partner brain" concept). Cross-link feature/pe-intelligence (the dead branch with 0 commits ahead per Report 0006) — possibly the **same partner-brain work was attempted twice**, once via pe-intelligence (deleted/superseded) and once via connect-partner-brain (still alive).

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR435** | **Phase0 must land before phase1** (cross-link Report 0006 MR38) | Phase1's `/partner-brain/modules` route may depend on Phase0 test-pinned APIs. | **High** |
| **MR436** | **server.py route conflict with main + feature/deals-corpus** | Pre-merge: route-block extraction + replay. | **Critical** |
| **MR437** | **Possible duplicate of feature/pe-intelligence (dead) work** | Unknown if connect-partner-brain re-implements pe-intelligence's content. | **High** |
| **MR438** | **314 commits behind main** | Same staleness pattern as deals-corpus + workbench-corpus-polish. Rebase required. | **Critical** |

## Dependencies

- **Incoming:** future merge plan.
- **Outgoing:** mid-April main snapshot.

## Open questions / Unknowns

- **Q1.** Per-commit walk owed.
- **Q2.** Diff vs `feature/pe-intelligence` to detect duplication.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0068** | Test coverage (already requested). |

---

Report/Report-0067.md written.

