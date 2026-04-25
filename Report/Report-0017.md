# Report 0017: SQLite Storage Layer — `deals` Table

## Scope

This report covers the **`deals` SQLite table** — the foundational entity of the portfolio store — on `origin/main` at commit `f3f7e7f`. The audit documents:

- The actual current schema (every column, every type, every constraint).
- Every code site that creates / migrates / reads / writes the table.
- The migration trail from initial schema to today.
- Foreign-key landscape (which child tables reference `deals.deal_id`).

The `deals` table was selected because Reports 0008 + 0006 + 0004 keep referencing it as the cascade root and CLAUDE.md identifies `portfolio/store.py` as the single SQL gate. Sister tables (`runs`, `analysis_runs`, `audit_events`, `users`, etc.) get their own future iterations.

Prior reports reviewed before writing: 0013-0016.

## Findings

### Actual current schema (5 columns)

```sql
-- Created at portfolio/store.py:113-119, plus migration deals_archived_at
CREATE TABLE IF NOT EXISTS deals (
    deal_id      TEXT PRIMARY KEY,
    name         TEXT,
    created_at   TEXT,
    profile_json TEXT
);
ALTER TABLE deals ADD COLUMN archived_at TEXT;
```

Final shape: **5 columns**, all `TEXT`. No indexes, no UNIQUE constraints beyond `PRIMARY KEY`.

| Column | Type | Constraint | Purpose |
|---|---|---|---|
| `deal_id` | TEXT | PRIMARY KEY | The single canonical identifier. Free-form string (e.g. `"acme-2026"`). |
| `name` | TEXT | (nullable) | Display name. |
| `created_at` | TEXT | (nullable) | ISO-8601 string set by `_utcnow()` at insert. |
| `profile_json` | TEXT | (nullable) | JSON blob holding the full deal profile. **All structured deal data lives here**, not in dedicated columns. |
| `archived_at` | TEXT | (nullable, added via migration `deals_archived_at`) | ISO-8601 timestamp when archived. NULL = active. **Soft-delete flag.** |

### Schema-doc drift (HIGH-PRIORITY)

`RCM_MC/rcm_mc/portfolio/README.md:11` claims **"Core tables: deals (17 columns), …"**. The actual `deals` table has **5 columns**, not 17. **The README is wrong.**

The 17 may refer to fields *inside* the `profile_json` blob, or it may be a leftover from an older schema that has since been condensed. Either way, the public README is at variance with the live schema. **Pre-merge: any branch that adds a column will update store.py + migrations, but the README will silently stay wrong.**

### Migration history

`RCM_MC/rcm_mc/infra/migrations.py:18-25` is the migration registry. Migrations relevant to `deals`:

| Migration name | SQL | Status |
|---|---|---|
| `deals_archived_at` | `ALTER TABLE deals ADD COLUMN archived_at TEXT` | Currently the only `deals`-touching migration |

Two adjacent migrations affect tables FK-linked to `deals`:

- `deal_notes_deleted_at` — `ALTER TABLE deal_notes ADD COLUMN deleted_at TEXT`
- `deal_deadlines_owner` — `ALTER TABLE deal_deadlines ADD COLUMN owner TEXT NOT NULL DEFAULT ''`

Migration mechanism (`infra/migrations.py:30-66`):

- Idempotent — each migration's name is recorded in a `_migrations` tracking table; subsequent runs skip applied migrations.
- **Per-migration `try/except: pass` swallows errors silently** (line 48). If `ALTER TABLE` fails (e.g. column exists from earlier `init_db` ALTER), it's silently no-op. Combined with the redundant ALTER at `store.py:121` (also wrapped in `try/except: pass`), the `deals_archived_at` migration may execute the ALTER twice — once at init_db, once via run_pending. The second is silently no-op'd.

### Indexes

```bash
$ grep -rn "CREATE INDEX.*deals" RCM_MC/rcm_mc/ | grep -v __pycache__
RCM_MC/rcm_mc/data_public/deals_corpus.py:70-72  # all on public_deals (different table)
```

**No indexes on the `deals` table.** Reads use `WHERE deal_id = ?` (PRIMARY KEY → automatic index) and `WHERE archived_at IS NULL` (full-table scan, no index). For a single-tenant SQLite of moderate size, this is acceptable; at multi-thousand-deal scale, the `archived_at IS NULL` scan becomes O(N) per portfolio render.

### Write sites (6 total — all in `portfolio/store.py`)

The write surface is **strictly centralized** through 5 methods on the `PortfolioStore` class:

| Method | Line | SQL |
|---|---|---|
| `upsert_deal` (insert path) | 148 | `INSERT OR IGNORE INTO deals (deal_id, name, created_at, profile_json) VALUES (?, ?, ?, ?)` |
| `upsert_deal` (update path) | 160 | `UPDATE deals SET name=?, profile_json=? WHERE deal_id=?` |
| `delete_deal` | 203 | `DELETE FROM deals WHERE deal_id = ?` (after cascading 23 child tables — Report 0008) |
| `clone_deal` | 227 | `INSERT INTO deals (deal_id, name, created_at, profile_json) VALUES (?, ?, ?, ?)` |
| `archive_deal` | 260 | `UPDATE deals SET archived_at = ? WHERE deal_id = ? AND archived_at IS NULL` |
| `unarchive_deal` | 271 | `UPDATE deals SET archived_at = NULL WHERE deal_id = ? AND archived_at IS NOT NULL` |

**Single-writer pattern is preserved.** Every write goes through `PortfolioStore`; no other module performs a direct INSERT/UPDATE/DELETE on `deals`.

### Read sites (≥ 17 distinct call sites across 8 files)

`grep -n "FROM deals\b" RCM_MC/rcm_mc/`:

| File:line | SQL pattern | Filters by `archived_at`? |
|---|---|---|
| `server.py:3727` | `SELECT COUNT(*) FROM deals` | **No** (counts archived too) |
| `server.py:3799` | `… FROM deals WHERE archived_at IS NULL` | Yes |
| `server.py:3869` | `SELECT name, profile_json FROM deals …` | (continued line — full clause not shown) |
| `server.py:3927` | `… FROM deals WHERE archived_at IS NULL` | Yes |
| `server.py:4014` | `SELECT name, profile_json FROM deals …` | (clause continues) |
| `server.py:4061` | `SELECT name, profile_json FROM deals …` | (clause continues) |
| `server.py:5780` | `SELECT deal_id, name, profile_json FROM deals WHERE deal_id = ?` | **No** (single-deal lookup; intentional — needs to surface archived deals too) |
| `server.py:6311` | `SELECT * FROM deals WHERE deal_id = ?` | **No** (single-deal lookup) |
| `server.py:10866` | `SELECT COUNT(*) FROM deals` | **No** |
| `ui/command_center.py:53` | `… FROM deals WHERE archived_at IS NULL …` | Yes |
| `ui/portfolio_monitor_page.py:47` | `SELECT deal_id, name, profile_json FROM deals WHERE archived_at IS NULL` | Yes |
| `ui/dashboard_page.py:638` | `SELECT deal_id, profile_json FROM deals …` | (clause continues) |
| `ui/dashboard_page.py:802` | f-string SQL `… FROM deals …` | (f-string — verify safety) |
| `ui/dashboard_page.py:1837` | `SELECT deal_id, profile_json FROM deals …` | (clause continues) |
| `pe/fund_attribution.py:140` | `SELECT deal_id FROM deals` | **No** (full table including archived — likely a bug) |
| `analysis/playbook.py:158` | `SELECT profile_json FROM deals WHERE deal_id = ?` | **No** (single-deal) |
| `analysis/playbook.py:237` | `SELECT deal_id FROM deals` | **No** (full table — same risk as fund_attribution) |
| `analysis/packet_builder.py:74` | `SELECT deal_id, name, profile_json FROM deals WHERE deal_id = ?` | **No** (single-deal) |

(Plus internal store.py reads at lines 153, 188, 219.)

**~17 read sites across 8 files.** Most rendering paths correctly filter `WHERE archived_at IS NULL`. Two batch reads (`pe/fund_attribution.py:140`, `analysis/playbook.py:237`) fetch ALL deals including archived — could be a bug or intentional (audit roll-up across the full history).

### Foreign-key landscape — child tables that reference `deals.deal_id`

`grep -rn "REFERENCES deals" RCM_MC/rcm_mc/`:

| Child table | File:line | ON DELETE? |
|---|---|---|
| `runs` | `portfolio/store.py:133` | (no ON DELETE clause — orphans on parent delete) |
| `value_creation_plans` | `pe/value_creation_plan.py:135` | **CASCADE** |
| `initiative_tracking` | `rcm/initiative_tracking.py:57` | (none) |
| `hold_period_tracking` | `pe/hold_tracking.py:70` | (none) |
| `deal_overrides` | `analysis/deal_overrides.py:218` | (none) |
| `approval_requests` | `deals/approvals.py:29` | **CASCADE** |
| `comments` | `deals/comments.py:27` | **CASCADE** |
| `deal_tags` | `deals/deal_tags.py:75` | (none) |
| `deal_notes` | `deals/deal_notes.py:60` | (none) |
| `analysis_runs` | `analysis/analysis_store.py:47` | (none) |
| `deal_stages` | `deals/deal_stages.py:55` | **CASCADE** |
| (plus 12+ more per Report 0008's `delete_deal` cascade list) | various | inconsistent |

**Inconsistent ON DELETE behavior.** Four child tables declare `ON DELETE CASCADE`; the rest declare no clause (default = `NO ACTION` in SQLite, but only enforced if `PRAGMA foreign_keys = ON`). Combined with `delete_deal`'s manual cascade list at `store.py:174-183` (Report 0008 MR55), the deletion logic is **dual-tracked**: SQL cascades for some children, app-level loop for others.

This is a known anti-pattern — tests pass because `delete_deal` does the manual loop, but if any branch removes the manual loop trusting CASCADE, the non-CASCADE child tables (most of them) leak orphan rows.

### `PRAGMA foreign_keys` posture

`portfolio/README.md:11` says SQLite is opened with `PRAGMA foreign_keys=ON`. The code that sets this is in `store.py:84-108` (`connect()` context manager — not yet read in this iteration but referenced by README claim).

**If `foreign_keys=OFF`** (e.g. forgotten in a future code path), the four `ON DELETE CASCADE` declarations are dead letter and `delete_deal`'s manual cascade list is the *only* delete enforcement. Future iteration must verify the PRAGMA is consistently applied across all `connect()` calls.

### `f-string` SQL at `ui/dashboard_page.py:802`

```python
f"SELECT deal_id, profile_json FROM deals "
```

The f-string usage is suspicious because **CLAUDE.md (Report 0002) explicitly forbids f-string SQL** ("Parameterised SQL only — never f-string values into SQL"). Need to verify the f-string here only interpolates a non-user value (e.g. an ORDER BY column from a known whitelist) and not user input. **Pre-merge: read `dashboard_page.py:802` end-to-end to confirm safety.**

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR122** | **HIGH-PRIORITY: README claims "deals (17 columns)" but actual is 5** | `portfolio/README.md:11` is silently wrong. Onboarders read the README and form an incorrect mental model. **Update the README to say "deals (5 columns; all structured deal data is JSON-blobbed in `profile_json`)".** | **High** |
| **MR123** | **Dual-tracked deletion logic (manual loop + sparse CASCADE FKs)** | 4 child tables declare `ON DELETE CASCADE`; the rest rely on `delete_deal`'s manual 23-table loop (Report 0008 MR55). A branch that removes the manual loop trusting SQL CASCADE would orphan rows in 19 tables. **Recommend: standardize on either ALL-CASCADE (DDL change across 19 tables) or ALL-MANUAL (drop the 4 CASCADE clauses).** | **Critical** |
| **MR124** | **Two read sites fetch all deals including archived (`fund_attribution.py:140`, `playbook.py:237`)** | If these are intentional (full-history audit), document. If not, archived deals leak into computations. Pre-merge: verify intent. | Medium |
| **MR125** | **f-string SQL at `ui/dashboard_page.py:802` may violate CLAUDE.md "parameterised SQL only" policy** | Without reading the surrounding context, cannot rule out user-input interpolation. **Sample read needed.** | **High** until verified |
| **MR126** | **No indexes on the `deals` table** | At 5K+ deals, `WHERE archived_at IS NULL` and `created_at`-ordered queries become O(N) scans. Pre-launch on production dataset, add `CREATE INDEX idx_deals_archived ON deals(archived_at)` migration. | Medium |
| **MR127** | **Migration registry's per-migration `try/except: pass` swallows real errors** | `infra/migrations.py:48` swallows ALL exceptions during ALTER. If a migration genuinely fails (e.g. type incompatibility on a non-empty table), the `_migrations` tracking row gets inserted anyway (line 53-58 always runs), declaring the migration "applied" when it actually failed. **Recommend: distinguish "column already exists" (silent skip) from real errors (raise).** | **High** |
| **MR128** | **`profile_json` is a free-form JSON blob with no schema** | All structured deal data lives in this column with no validation. A branch that changes the JSON shape silently breaks every reader. The reads at server.py:5780, 6311, etc. just `json.loads(profile_json)` and call `.get()` — robust to missing keys but **no contract enforcement**. Pre-merge: any branch that touches profile shape needs to confirm consumers tolerate missing/added keys. | **High** |
| **MR129** | **`archived_at` filter is the soft-delete convention, applied inconsistently** | Some reads filter `WHERE archived_at IS NULL`; others don't. A branch that adds a new read without filtering will silently include archived deals. Recommend: a `list_active_deals(self)` method on the store that encodes the filter, replacing all ad-hoc reads. | Medium |
| **MR130** | **Tests for `delete_deal` cover only 1 site (Report 0008)** | This iteration confirms 4 of 23 child tables have `ON DELETE CASCADE`; the rest rely on the manual loop. The single test (`tests/test_deal_deletion.py`) presumably exercises a small subset of child tables. **Adding a new child table with no test means the cascade list silently goes stale.** | **Critical** (compounds Report 0008 MR55) |
| **MR131** | **Schema lives in two places: `store.py:113` `CREATE TABLE` + `infra/migrations.py:18-25` `ALTER TABLE`** | Adding a column requires editing both files (or only the migration; the CREATE TABLE only runs on fresh DBs). A branch that adds a column to one file but not the other will produce different schemas on fresh-install vs upgrade. | **High** |

## Dependencies

- **Incoming (who reads/writes `deals`):** `portfolio/store.py` (writes), `server.py` (9 reads), `ui/dashboard_page.py` (3 reads), `ui/command_center.py`, `ui/portfolio_monitor_page.py`, `pe/fund_attribution.py`, `analysis/playbook.py` (2 reads), `analysis/packet_builder.py` (1 read), and indirectly every test that goes through `PortfolioStore`. Plus 11+ child tables that hold FK references.
- **Outgoing (what `deals` depends on):** SQLite (`sqlite3` stdlib); `infra/migrations.py` (for ALTER TABLE registry). No external services.

## Open questions / Unknowns

- **Q1 (this report).** What does `PortfolioStore.connect()` (line 84) actually set? The README claims `WAL mode`, `busy_timeout=5000`, `PRAGMA foreign_keys=ON`. Need to verify all three are applied unconditionally on every connection.
- **Q2.** Is `ui/dashboard_page.py:802`'s f-string SQL safe (whitelist-bound) or a vulnerability? Sample-read needed.
- **Q3.** Are the two "fetch-all-deals" reads (`pe/fund_attribution.py:140`, `analysis/playbook.py:237`) intentional or bugs?
- **Q4.** How many deals fit in the typical production database? At what threshold does the lack of indexes become a performance issue?
- **Q5.** What's the JSON shape of `profile_json`? Is there a Pydantic model / dataclass anywhere documenting the keys readers depend on?
- **Q6.** Does any feature branch add a column to `deals` (via either `store.py:113` or `infra/migrations.py`)? Cross-branch sweep needed.
- **Q7.** Does the SQLite database file path differ between the CLI's local-laptop default (`~/.rcm_mc/portfolio.db`) and the Heroku/Docker path (`$RCM_MC_DB`)? Per Report 0007, `feature/workbench-corpus-polish` removes the env-var fallback.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0018** | **Read `portfolio/store.py:connect()` (lines 84-108)** end-to-end. | Resolves Q1 — verifies WAL / busy_timeout / foreign_keys=ON are unconditional. |
| **0019** | **Read `ui/dashboard_page.py:802`** end-to-end and verify f-string SQL safety. | Resolves Q2 / MR125. |
| **0020** | **Audit the JSON shape of `profile_json`** by sampling readers' `.get()` patterns. | Resolves Q5 / MR128. |
| **0021** | **Audit `runs` table** (the second table created in store.py:125). Same depth as this report. | Sister table; Report 0008 noted `list_runs`/`get_run` are 0-test-coverage. |
| **0022** | **Cross-branch sweep: which ahead-of-main branch adds columns to `deals`?** | Resolves Q6 / MR131. |
| **0023** | **Audit `analysis_runs` table** (the packet cache). | Closes the trio of canonical persistence tables. |

---

Report/Report-0017.md written. Next iteration should: read `portfolio/store.py:connect()` (lines 84-108) end-to-end and verify that WAL mode, `busy_timeout=5000`, and `PRAGMA foreign_keys=ON` are all set unconditionally on every connection — closes Q1 here, MR123 (FK enforcement underpinning), and MR128 (concurrency assumptions).

