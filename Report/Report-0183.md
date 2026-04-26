# Report 0183: Map Next Key File — `engagement/store.py` (4 NEW tables)

## Scope

Reads `RCM_MC/rcm_mc/engagement/store.py` (707 lines per Report 0182). **Closes Report 0182 Q1: 4 NEW unmapped SQLite tables.** Sister to schema-walk reports.

## Findings

### 4 NEW SQLite tables (lines 159-209)

#### Table 1 — `engagements` (8 fields)

```sql
CREATE TABLE IF NOT EXISTS engagements (
    engagement_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    client_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    closed_at TEXT,
    notes TEXT NOT NULL DEFAULT ''
)
```

**8 fields. PRIMARY KEY on engagement_id (TEXT). No FK.**

#### Table 2 — `engagement_members` (5 fields, COMPOSITE PK + FK)

```sql
CREATE TABLE IF NOT EXISTS engagement_members (
    engagement_id TEXT NOT NULL,
    username TEXT NOT NULL,
    role TEXT NOT NULL,
    added_at TEXT NOT NULL,
    added_by TEXT NOT NULL,
    PRIMARY KEY (engagement_id, username),
    FOREIGN KEY (engagement_id) REFERENCES engagements(engagement_id)
)
```

**Composite PRIMARY KEY** (engagement_id, username) — first composite PK seen. **FK** to engagements (no cascade specified — NO ACTION default).

#### Table 3 — `engagement_comments` (8 fields, FK)

```sql
CREATE TABLE IF NOT EXISTS engagement_comments (
    comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    engagement_id TEXT NOT NULL,
    target TEXT NOT NULL,
    author TEXT NOT NULL,
    body TEXT NOT NULL,
    posted_at TEXT NOT NULL,
    is_internal INTEGER NOT NULL DEFAULT 0,
    parent_comment_id INTEGER,  -- threading; no FK to self
    FOREIGN KEY (engagement_id) REFERENCES engagements(engagement_id)
)
```

**8 fields. `parent_comment_id` is self-reference but NOT FK-declared.** `is_internal` is INTEGER (0/1) used as boolean.

Index: `idx_comments_engagement ON engagement_comments(engagement_id, posted_at DESC)`.

#### Table 4 — `engagement_deliverables` (11 fields, FK)

```sql
CREATE TABLE IF NOT EXISTS engagement_deliverables (
    deliverable_id INTEGER PRIMARY KEY AUTOINCREMENT,
    engagement_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    published_by TEXT,
    published_at TEXT,
    content_ref TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT ''
    FOREIGN KEY (engagement_id) REFERENCES engagements(engagement_id)
)
```

**11 fields, FK.** `kind` and `status` are free-form (8th instance of pattern).

### MAJOR FINDING — 3 more FKs (cross-link Report 0167 + 0180)

3 of the 4 new tables have FKs to `engagements`:
- engagement_members.engagement_id → engagements
- engagement_comments.engagement_id → engagements
- engagement_deliverables.engagement_id → engagements

**All 3 have NO cascade specified (NO ACTION).** Cross-link Report 0167 + 0147 (sessions, initiative_actuals — same NO ACTION default).

**FK-frontier count NOW: 9 confirmed FK-bearing tables.** Report 0180 estimate of "~16 likely" ramps further.

### Cascade behavior count update

| Behavior | Count |
|---|---|
| CASCADE | 3 (analysis_runs, mc_simulation_runs, deal_overrides) |
| SET NULL | 1 (generated_exports) |
| **NO ACTION (default)** | **5** (sessions + initiative_actuals + 3 engagement-children) |

**5 tables with NO ACTION cascade** = if parent deleted, IntegrityError. Cross-link Report 0147 MR818 / 0167 MR890.

### Schema inventory progress

After this report: **20 tables walked** (16 prior + 4 here). Per Report 0091/0181: 22+ in DB. **~2-7 unidentified remain.**

### Free-form-text classifications (8th + 9th instances)

- `engagements.status TEXT DEFAULT 'ACTIVE'` — free-form
- `engagement_members.role TEXT NOT NULL` — free-form (cross-link Report 0147 users.role)
- `engagement_comments.target TEXT NOT NULL` — free-form
- `engagement_deliverables.kind TEXT NOT NULL` — free-form
- `engagement_deliverables.status TEXT DEFAULT 'DRAFT'` — free-form

**5 more free-form-text fields in this single subpackage.** Project-wide pattern continues.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR936** | **4 NEW SQLite tables in engagement/store.py** with 3 FKs to engagements (composite PK, threaded comments, deliverables) | Closes Report 0182 Q1. Schema-walk count: 20. | (closure) |
| **MR937** | **5 free-form-TEXT fields in single subpackage** (status, role, target, kind, status) | 8th-12th instance project-wide. **Pattern is overwhelming evidence** for documented enum convention. | (carried) |
| **MR938** | **5 NO-ACTION cascade tables** (sessions + initiative_actuals + 3 engagement-children) | Cross-link MR818/MR890. Deleting parent fails with IntegrityError. **Most-common cascade behavior is the WORST UX** — operator must clear children manually. | **High** |
| **MR939** | **`parent_comment_id` is self-reference but NOT declared FK** | Threaded comments can have orphan parent references silently. Cross-link Report 0167 same pattern. | Medium |

## Dependencies

- **Incoming:** server.py engagement routes (Report 0127), tests.
- **Outgoing:** PortfolioStore.

## Open questions / Unknowns

- **Q1.** Public API surface (engagement/__init__.py 76L re-exports)?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0184** | Incoming dep graph (in flight). |

---

Report/Report-0183.md written.
