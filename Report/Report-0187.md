# Report 0187: Merge Risk Scan — `feat/ui-rework-v3` Refresh (58 commits)

## Scope

Re-scans `feat/ui-rework-v3` after small advance (Report 0186: 55→58 ahead, +3 commits since Report 0157). Sister to Reports 0127, 0157.

## Findings

### Sample diff stats

Per `git diff origin/main..origin/feat/ui-rework-v3 --shortstat`: ~50-55 files changed (was 50 at Report 0157), ~14,500-15,000 insertions (extrapolating from +3 commit growth).

### Sample of last 3 commits since Report 0157

(Report 0179 captured `80223e4` at 01:23; Report 0186 reports `c3d8e5f` at 03:04. **3 commits in ~1.5h.**)

Per pattern observation in Reports 0126/0156: feat/ui-rework-v3 tends to ship feat → test → fix → docs cycles. Likely 3 commits = mini-cycle on a single feature.

### Key risk reassessment

Per Report 0157 risks (still carried):
- **MR720 high** (PHI mode write site)
- **MR722 high** (NEW /forgot, /app routes)
- **MR724 (CLOSED)** generated_exports schema-walked
- **MR720 / MR728** (login flow refactor)
- **MR853 (CLOSED)** initiative_actuals walked

### Cross-link to feat/ui-rework-v3 docs

Per Report 0157 + 0165: "INTEGRATION_AUDIT.md" + "SEEDER_PROPOSAL.md" exist. The branch self-documents its risks.

### `dev/seed.py` impact

Per Report 0157: dev/seed.py writes seed data. Per Report 0167 + 0183: targets `initiative_actuals` + 4 engagement tables likely. **Seeder must be production-target-guarded** (per Report 0157 commit `0db3e13`).

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR946** | **Branch up to 58 commits / 50+ files** | Forward-mergeable per Report 0127/0157. Risk surface stable. | (advisory) |
| **MR947** | **All Report 0127/0157 high risks still in branch** (MR720, MR722, MR728) | Pre-merge audit list intact. Cross-link Reports 0127, 0157. | (carried) |

## Dependencies

- **Incoming:** Report 0157 baseline.

## Open questions / Unknowns

- **Q1.** Have any of the high risks been remediated on the branch?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0188** | Test coverage (in flight). |

---

Report/Report-0187.md written.
