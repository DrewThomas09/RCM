# Report 0047: SQLite Storage Layer — `runs` Table (canonical)

## Scope

Documents the canonical `runs` SQLite table created at `portfolio/store.py:125` on `origin/main` at commit `f3f7e7f`. Sister to Report 0017 (`deals` table). Resolves Report 0008's noted gap that `list_runs` and `get_run` have ZERO direct test references.

**HIGH-PRIORITY DISCOVERY:** A second, independent `runs` table also exists at `infra/run_history.py` — same name, different schema, different DB file. Documented below.

Prior reports reviewed: 0043-0046.

## Findings

### Schema (canonical `runs` in `portfolio/store.py:125-137`)

```sql
CREATE TABLE IF NOT EXISTS runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT,
    scenario TEXT,
    created_at TEXT,
    notes TEXT,
    config_yaml TEXT,
    summary_json TEXT,
    primitives_json TEXT,
    FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
);
```

**8 columns + FK.** No `ON DELETE CASCADE` on the FK (Report 0017 noted this — `runs` is one of the 19 child tables that relies on `delete_deal`'s manual loop, not SQL CASCADE).

| Column | Type | Notes |
|---|---|---|
| `run_id` | INTEGER PK AUTOINCREMENT | The single canonical run ID |
| `deal_id` | TEXT (nullable) | FK → `deals.deal_id`. Nullable per the schema; should always be set. |
| `scenario` | TEXT | Free-form scenario tag (e.g. "stress_test_v2") |
| `created_at` | TEXT (ISO-8601) | Set by `_utcnow()` in store.py |
| `notes` | TEXT | Free-form analyst comment |
| `config_yaml` | TEXT | The YAML config blob — full simulator input |
| `summary_json` | TEXT | The summary stats output JSON |
| `primitives_json` | TEXT | Output of `extract_primitives_from_config` (Report 0008) — derived priors per payer |

**Three free-form text blobs (yaml + 2 JSON) — schema-on-read pattern.** Cross-link Report 0017 MR128: `profile_json` on `deals`. Same anti-pattern.

### Write sites (1 in store.py)

| Line | Method | SQL |
|---|---|---|
| `portfolio/store.py:318` | `add_run(self, deal_id, scenario, ...)` | `INSERT INTO runs (deal_id, scenario, created_at, notes, config_yaml, summary_json, primitives_json) VALUES (?,?,?,?,?,?,?)` |

**1 write site.** Accessible via `PortfolioStore.add_run(...)` per Report 0008.

### Read sites (4 in store.py + 1 in data_public/)

| Line | Method | SQL |
|---|---|---|
| `portfolio/store.py:329` | `list_runs(deal_id=...)` | `SELECT run_id, deal_id, scenario, created_at, notes FROM runs WHERE deal_id=? ORDER BY created_at DESC` |
| `portfolio/store.py:334` | `list_runs(deal_id=None)` (all-runs branch) | `SELECT run_id, deal_id, scenario, created_at, notes FROM runs ORDER BY created_at DESC` |
| `portfolio/store.py:340` | `get_run(run_id)` | `SELECT * FROM runs WHERE run_id=?` |
| `portfolio/store.py:349` | `export_priors(...)` | `SELECT primitives_json FROM runs` (full table scan, no filter) |
| `data_public/backtester.py:146` | (backtest tooling) | `SELECT * FROM runs WHERE deal_id = ? ORDER BY created_at DESC LIMIT 1` |

**5 reads total.** All via `portfolio/store.py` methods plus 1 external `data_public/backtester.py` reader.

### Test coverage (per Report 0008)

- `add_run` — 1 test reference
- `list_runs` — **0 tests**
- `get_run` — **0 tests**
- `export_priors` — 1 test reference

**The most heavily-used run-table reader (`list_runs` from cli.py + server.py + portfolio_cli.py) has ZERO direct tests.** Report 0008 MR58 already flagged this; this report confirms the schema picture.

### `RunRecord` dataclass

`portfolio/store.py:65-74` defines:

```python
@dataclass
class RunRecord:
    run_id: int
    deal_id: str
    scenario: str
    created_at: str
    notes: str
    config_yaml: str
    summary_json: str
    primitives_json: str
```

**Field-for-field map of the schema** (8 fields). Returned by `get_run(run_id)` (line 338-344 per Report 0008).

Per Report 0008 MR59: **`RunRecord` has 0 external consumers** — exposed via `get_run()` but no caller destructures it. Production callers may rely on raw column tuples instead.

### HIGH-PRIORITY DISCOVERY: Second `runs` table

`infra/run_history.py:18-33` defines a **completely different** schema for a table also named `runs`:

```sql
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    actual_config_hash TEXT,
    benchmark_config_hash TEXT,
    n_sims INTEGER,
    seed INTEGER,
    ebitda_drag_mean REAL,
    ebitda_drag_p10 REAL,
    ebitda_drag_p90 REAL,
    ev_impact REAL,
    output_dir TEXT,
    hospital_name TEXT,
    notes TEXT
);
```

13 columns. **Different from the portfolio/store.py runs schema.**

- Different DB file: `infra/run_history.py:47` `_get_db_path(outdir) -> os.path.join(outdir, "runs.sqlite")`. **Per-outdir DB**, separate from the canonical `~/.rcm_mc/portfolio.db`.
- Different write site: `infra/run_history.py:73` `INSERT INTO runs (timestamp, actual_config_hash, ...)`.
- Different read site: `infra/run_history.py:102` `SELECT * FROM runs ORDER BY id DESC LIMIT ?`.
- Different function name: `infra/run_history.py:92 list_runs(outdir, limit=20)` — same name as `portfolio/store.py:list_runs`, different signature.

**No actual data collision** because the two tables live in different DB files. But:

- **Conceptual collision.** A grep for `INSERT INTO runs` returns two unrelated sites.
- **Function-name collision.** `list_runs(deal_id=None)` vs `list_runs(outdir, limit=20)` — different modules, different DBs.
- **Schema-name collision.** Future migrations referencing "the runs table" must specify which one.

This is a **maintenance hazard** but not a runtime bug today. Pre-merge: any branch consolidating run-tracking must understand which `runs` is the canonical one (likely `portfolio/store.py`).

### Indexes

- **No indexes on `portfolio/store.py:runs`** beyond the PRIMARY KEY. `list_runs(deal_id=?)` does a seq-scan filtered by `deal_id`. Acceptable at low volume; degrades at thousands of runs per deal.
- `infra/run_history.py:runs` similarly no indexes.

### FK enforcement

`portfolio/store.py:runs.FOREIGN KEY(deal_id) REFERENCES deals(deal_id)` — declared, but **no `ON DELETE CASCADE`**. Per Report 0017, this places `runs` in the manual-cascade list at `delete_deal:174-183`. Verified: line 175 of the cascade list includes `"runs"`.

If `PRAGMA foreign_keys=ON` is set (per Report 0017 portfolio/README.md claim), then **inserting a `runs` row with a non-existent `deal_id` fails**. If `PRAGMA foreign_keys=OFF`, orphans are accepted silently.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR369** | **HIGH-PRIORITY: Two different `runs` tables in two different DBs** | `portfolio/store.py:125` (canonical) vs `infra/run_history.py:18-33` (per-outdir). Same table name, different schemas, different DB files. **Confusing for any maintenance pass.** Recommend rename: `runs` (canonical) + `cli_run_history` (the infra one). | **High** |
| **MR370** | **`infra/run_history.py:list_runs(outdir, limit)` shadows `PortfolioStore.list_runs(deal_id)`** | A `from rcm_mc.infra.run_history import list_runs` in some module would call the wrong function vs `from rcm_mc.portfolio.store import PortfolioStore; store.list_runs(deal_id)`. **Function-name collision** even though the modules are different. | **High** |
| **MR371** | **`primitives_json` blob is opaque** | Schema-on-read; producers + consumers must agree on JSON shape. A future change to `extract_primitives_from_config` (Report 0008) writes a different shape; readers don't know. | Medium |
| **MR372** | **No indexes on `runs` table** | At thousands of runs per deal, `list_runs(deal_id=?)` becomes slow. Recommend `CREATE INDEX idx_runs_deal_id ON runs(deal_id)`. | Medium |
| **MR373** | **`list_runs` + `get_run` have 0 direct tests** | (Cross-link Report 0008 MR58.) The two read paths into the canonical run history are untested. | **High** |
| **MR374** | **`export_priors` does a full-table scan** | `SELECT primitives_json FROM runs` (line 349) — no filter. At scale this is wasteful. Report 0008 noted export_priors is the longest method (50 lines) with 1 test. | Medium |
| **MR375** | **`config_yaml` and `summary_json` are blob-typed but stored as TEXT** | A truly large config (e.g. multi-MB scenarios) inflates the DB. SQLite can store TEXT blobs but rows over ~1 MB hit a `SQLITE_LIMIT_LENGTH` (default 1 GB but default page size is 4 KB so over-page reads are slow). | Low |

## Dependencies

- **Incoming:** `cli.py` (per Report 0008's `list_runs` + `get_run` referenced in production callers — mostly via PortfolioStore methods), `server.py` (per Report 0008), `portfolio_cli.py`, `data_public/backtester.py:146` (1 direct read site).
- **Outgoing:** `deals` table (FK), `extract_primitives_from_config` (the producer of `primitives_json`).

## Open questions / Unknowns

- **Q1.** Is the `infra/run_history.py:runs` table actually used in production? Per the file docstring it's "Step 83: SQLite-based run history. Auto-appends a row after each CLI run." So it logs CLI runs to a per-outdir DB. **Likely live but separate from the partner-portfolio path.**
- **Q2.** Why two different schemas for "runs"? Was one a refactor that left the other in place?
- **Q3.** Are there ahead-of-main branches that consolidate the two `runs` schemas?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0048** | **Read `infra/run_history.py`** end-to-end (~107 lines per the read above) | Resolves Q1 / Q2 / MR369. |
| **0049** | **Audit `data_public/backtester.py:146`** — the only external `runs` read site | Cross-link with the canonical schema. |
| **0050** | **Audit `analysis_runs` table** — third canonical persistence layer | Sister to deals + runs. |

---

Report/Report-0047.md written. Next iteration should: read `infra/run_history.py` end-to-end (~107 lines) to fully document the second `runs` table, resolve Q1 (is it used in production), and propose a rename to disambiguate from the canonical `portfolio/store.py:runs` table — closes MR369/MR370 here.

