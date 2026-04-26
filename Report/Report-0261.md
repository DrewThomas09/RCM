# Report 0261: PortfolioStore-Bypass Audit (MR708) + Surgical Fix at server.py:5189

## Scope

Closes Report 0124 / MR708: "5+ modules bypass PortfolioStore and call sqlite3.connect() directly". A re-grep of `rcm_mc/` finds **33 direct sqlite3.connect() sites** — far more than the original 5+ estimate. This iteration classifies them by risk (read-only vs write-path; portfolio DB vs standalone DB) and applies one surgical fix at the single high-impact write site.

Sister reports: 0124 (MR708 origin), 0118 (PRAGMA foreign_keys), 0157 (MR855 sibling), 0181 (delete-policy matrix).

## Findings

### Full bypass landscape — 33 sites

| Category | Count | Examples | Risk |
|---|---|---|---|
| **Write to portfolio DB, no PortfolioStore** | **1** | `server.py:5189` (save_entry in /data-room/) | **High — MR708 hits here** |
| Write to *standalone* DB (not portfolio) | 4 | `infra/backup.py:108,161` (decompressed-restore integrity check) · `infra/run_history.py:69` (separate runs.sqlite file) | Out of scope — not the portfolio DB |
| Read-only on portfolio DB | ~28 | `ui/command_center.py:49,77` · `ui/pipeline_page.py:53` · `ui/portfolio_bridge_page.py:54` · `ui/model_validation_page.py:43` · `ui/ebitda_bridge_page.py:358` · `ui/value_tracking_page.py:44` · `ui/data_room_page.py:58` · `ui/team_page.py:23` · `ui/chartis/home_page.py:104,152,227,473` · `ui/provenance.py:202` · `server.py:3529-3530` (backup API — read source / write empty backup) · ... | Bounded — read-only paths don't violate FK, no dangling-row risk |
| Test fixtures | 0 | (already use PortfolioStore) | — |

### Re-classification of the original MR708 list

Report 0124 identified `server.py × 2`, `ui/command_center`, `ui/portfolio_bridge_page`, `ui/pipeline_page` as the worst offenders. Re-reading each:

| Site | Operation | Verdict |
|---|---|---|
| `server.py:3529-3530` | SQLite backup API (source + dest connections) | **Acceptable** — Q3 in Report 0124 already noted: backup API requires both connections without a context manager |
| `server.py:5189` | `save_entry(con, ...)` — INSERT into data_room_entries | **Real MR708 hit — fixed in this iteration** |
| `ui/command_center.py:49,77` | SELECT-only renderers | Bounded read-only |
| `ui/portfolio_bridge_page.py:54` | SELECT-only renderer | Bounded read-only |
| `ui/pipeline_page.py:53` | SELECT-only renderer | Bounded read-only |

So the actual unbounded MR708 hit reduces to **1 site**, not 5+. The original audit conflated read-only renderers (low risk) with the one real write-path bypass.

### Surgical fix at `server.py:5189`

Before:
```python
from .data.data_room import save_entry
con = sqlite3.connect(self.config.db_path)
save_entry(con, ccn, metric, value, sample_size, source, analyst)
con.commit()
con.close()
```

After:
```python
from .data.data_room import save_entry
# Report 0124 MR708: route through PortfolioStore so this
# write inherits PRAGMA foreign_keys = ON + busy_timeout =
# 5000 + row_factory rather than running on a bare
# sqlite3.connect that misses all three.
with PortfolioStore(self.config.db_path).connect() as con:
    save_entry(con, ccn, metric, value, sample_size, source, analyst)
    con.commit()
```

The replacement:
- Uses `PortfolioStore(...).connect()` which applies `PRAGMA busy_timeout = 5000` + `PRAGMA foreign_keys = ON` + `row_factory = sqlite3.Row` (per Report 0118).
- Wraps in `with ... as con:` so the connection is closed even on exception (the original explicit `con.close()` was outside any try-finally).
- Preserves `con.commit()` since `save_entry` doesn't auto-commit.

`PortfolioStore` import is already present at module top of server.py — no new import needed.

### MR708 closure justification

After this iteration:
- The single real write-path bypass on the portfolio DB is fixed.
- The 4 standalone-DB sites (backup, run_history) are intentional and out of scope.
- The ~28 read-only renderer sites have bounded risk; tracked as a low-priority refactor (replace `db_path: str` → `store: PortfolioStore` in UI page contracts).
- 8 data_room tests pass post-fix.

**MR708 closure justified.** The remaining read-only bypass sites stay as a tracked refactor — see MR1067 below.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR1067** | **~28 UI-renderer sites still call `sqlite3.connect()` directly** for read-only queries on the portfolio DB. Bounded risk (no FK enforcement needed for SELECT), but they do miss `busy_timeout = 5000` so a heavy concurrent writer could SQLITE_BUSY them. | Refactor: change UI page contracts from `db_path: str` to `store: PortfolioStore`. ~28 files; should be a one-shot mechanical PR. | Low |
| **MR708** | (RETRACTED — closed) the single high-impact write-path bypass at server.py:5189 fixed; remaining sites re-classified as read-only or out-of-scope | (closure) | (closed) |

## Dependencies

- **Incoming:** `/data-room/` POST handler in server.py.
- **Outgoing:** `data.data_room.save_entry`, `PortfolioStore.connect`, `sqlite3.Row` (via PRAGMA + row_factory).

## Open questions / Unknowns

- **Q1.** Is there a JOIN-driven hot path in any of the ~28 read-only UI renderers that depends on `row_factory = sqlite3.Row` (column-name access)? If yes, those sites have ALREADY been mass-migrated to `dict()`-style row consumption. Worth a follow-up grep.
- **Q2.** Should `infra/run_history.py` move from a separate `runs.sqlite` file into the main portfolio DB? Cross-link CLAUDE.md "single SQLite file" stance.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| (low) | MR1067 — refactor ~28 UI renderers to take `store: PortfolioStore` instead of `db_path: str`. |
| (low) | Q2 — consolidation of run_history into portfolio.db, or document why separation is intentional. |

---

Report/Report-0261.md written.
