# Report 0182: Map Next Directory — `rcm_mc/engagement/`

## Scope

Maps `RCM_MC/rcm_mc/engagement/` — one of Report 0121's 17+ never-mentioned subpackages. Sister to Reports 0092 (ml/), 0122 (rcm_mc_diligence/), 0142 (finance/), 0152 (pe_intelligence/).

## Findings

### Inventory

```
engagement/
├── README.md         (2.1 KB)
├── __init__.py       (76 lines, 2.1 KB)
└── store.py          (707 lines, 24.3 KB)
```

**3 files. 783 total .py LOC.** Tight subpackage.

### Per-file purpose

- `README.md` (2.1 KB) — subpackage README.
- `__init__.py` (76L) — re-export.
- `store.py` (707L) — engagement-table CRUD operations (cross-link Report 0124 PortfolioStore importer).

### Cross-link to Report 0124

Per Report 0124: `engagement/store.py` and `engagement/__init__.py` are both PortfolioStore importers. **Confirmed: this subpackage has SQLite tables.**

### Likely tables (per Report 0127 commit 87e8d5e references)

Per Report 0127 (feat/ui-rework-v3): server.py routes `/engagements/...` for engagement CRUD:
- `_route_engagement_create` → likely INSERT
- `_route_engagement_add_member` → likely INSERT into a members table
- `_route_engagement_post_comment` → likely INSERT into a comments table
- `_route_engagement_publish_deliverable` → likely UPDATE

**Likely 3-5 SQLite tables in engagement/store.py**: `engagements`, `engagement_members`, `engagement_comments`, `engagement_deliverables`. **All NEW unmapped tables.**

### Suspicious findings

| Item | Note |
|---|---|
| store.py 707L | substantial; large for a single store module |
| `__pycache__/` | (not extracted; per Report 0001 + 0150 gitignored) |
| Mtime: Apr 25 12:01 | bulk-touched — same as `f3f7e7f` cleanup |

### NEW unmapped subsystem detected

**Engagement** = workflow tracking (PE deal team coordination per CLAUDE.md "Phase 3" portfolio operations). Per CLAUDE.md "Cohorts, watchlists, owners, deadlines, notes, tags." **Engagement is a parallel coordination layer.**

### Cross-link to Report 0181 backlog

Engagement is **1 of ~17 never-mentioned subpackages** per Report 0121. Now mapped at directory level.

### Comparison to other small subpackages

| Subpackage | Files | Lines | Status |
|---|---|---|---|
| `domain/` (Report 0094-0099) | 3 | 1,059 | mapped |
| `infra/data_retention/` (Report 0123) | 1 | 79 | mapped |
| **`engagement/` (this)** | **3 (2 .py)** | **783** | **inventoried** |

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR934** | **`engagement/store.py` is 707 LOC** — likely 3-5 unwalked SQLite tables | Per Report 0181 backlog: ~10-15 unidentified tables. This subpackage adds ~3-5 to that. | **High** |
| **MR935** | **NEW unmapped subsystem** confirmed: workflow/coordination layer | Cross-link Report 0121 + 0181 — 17+ never-mentioned. This is one. | (advisory) |

## Dependencies

- **Incoming:** server.py routes (`/engagements/*` per Report 0127), tests TBD.
- **Outgoing:** PortfolioStore (per Report 0124).

## Open questions / Unknowns

- **Q1.** What tables does `engagement/store.py` create?
- **Q2.** Per `__init__.py` (76L) re-exports — public API count?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0183** | Read `engagement/store.py` head + schema (closes Q1, in flight). |
| **0184** | Read `__init__.py` re-exports (closes Q2). |

---

Report/Report-0182.md written.
