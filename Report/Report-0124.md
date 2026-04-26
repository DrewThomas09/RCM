# Report 0124: Incoming Dep Graph — `portfolio/store.py` (`PortfolioStore`)

## Scope

Maps every importer of `RCM_MC/rcm_mc/portfolio/store.py`'s `PortfolioStore` class. The most-cited module in the audit (Report 0017 schema, Report 0027 store coverage, Report 0090 + 0118 PRAGMA, Report 0111 MR626 architectural violations). Sister to Reports 0064 (audit_log incoming), 0094 (domain incoming), 0034 (infra/config incoming).

## Findings

### Headline coupling — extreme

**`PortfolioStore` is imported by 237 files** (43 production + 194 tests).

| Layer | Count |
|---|---|
| Production (`rcm_mc/`) | 43 |
| Tests (`tests/`) | 194 |
| **Total** | **237** |

**This is by far the most heavily-coupled module in the project.** Per Report 0094 heuristic of ">5 callers = tight," PortfolioStore is **47x the threshold** in production alone.

### Production importers by subpackage (43 total)

| Subpackage | Count | Files |
|---|---|---|
| `deals/` | 9 | deal, deal_notes, deal_tags, deal_owners, deal_deadlines, deal_sim_inputs, health_score, watchlist, note_tags |
| top-level entries | 4 | server.py, cli.py, portfolio_cmd.py, pe_cli.py |
| `ui/` | 4 | data_refresh_page, portfolio_risk_scan_page, global_search, dashboard_page |
| `portfolio/` | 5 | portfolio_digest, portfolio_dashboard, portfolio_synergy, portfolio_snapshots, portfolio_cli |
| `pe/` | 3 | hold_tracking, remark, fund_attribution |
| `alerts/` | 3 | alerts, alert_acks, alert_history |
| `compliance/` | 2 | __main__, audit_chain |
| `auth/` | 2 | auth, audit_log |
| `engagement/` | 2 | store, __init__ |
| `rcm/` | 2 | initiative_tracking, initiative_rollup |
| `data_public/` | 2 | deals_corpus, backtester |
| `reports/` | 2 | exit_memo, lp_update |
| `analysis/` | 1 | cohorts |
| `infra/` | 1 | morning_digest |
| `ml/` | 1 | contract_strength |

**15 subpackages depend on `portfolio/store.py`.** Every layer of the architecture diagram (per CLAUDE.md) touches it.

### Architectural status (cross-link CLAUDE.md + Report 0111 MR626)

CLAUDE.md (per Report 0011 + 0017): "**The store is the only module that talks to SQLite directly.**"

**Two interpretations to verify:**

#### Interpretation A — "PortfolioStore is the only `sqlite3.connect()` caller"

`grep "sqlite3.connect" RCM_MC/rcm_mc/`:

| File | Status |
|---|---|
| `portfolio/store.py:94` | ✓ legitimate — owner |
| **`server.py:3529-3530`** | **VIOLATION** — `_sqlite3.connect(self.config.db_path)` for `/api/backup` |
| **`server.py:5189`** | **VIOLATION** — direct connect |
| **`ui/command_center.py:14, 49, 77`** | **VIOLATION** — direct sqlite3 in UI page |
| **`ui/portfolio_bridge_page.py:13, 54`** | **VIOLATION** |
| **`ui/pipeline_page.py:10, 53`** | **VIOLATION** |
| ...more | likely 5+ more |

**At least 5 modules bypass PortfolioStore and call `sqlite3.connect()` directly.** The `PRAGMA busy_timeout`, `PRAGMA foreign_keys = ON` (per Report 0118), and `row_factory = sqlite3.Row` are NOT applied on these connections.

**MR708 critical**: 5+ modules bypass the store layer, missing the FK enforcement and busy-timeout guarantees.

#### Interpretation B — "Modules that import PortfolioStore use it (rather than instantiating their own DB connections)"

The 43 production importers all use `with store.connect() as con:` — legitimate per the architecture. 

So:
- **43 modules use PortfolioStore correctly.** ✓
- **5+ modules bypass it.** ✗ (per Interpretation A) — **architectural violation.**

### Tight-coupling pressure

A signature change to `PortfolioStore.__init__(db_path: str)` or `connect()` would ripple through 237 importers. **Maximum blast radius.**

| Risk | Affected |
|---|---|
| Renaming `connect` → `acquire` | 237 files (each `.connect()` call) |
| Adding required `__init__` arg | 237 files |
| Removing `init_db` | unknown count of callers |
| PRAGMA change in `connect` | implicit, all 237 |

### Cross-link to Report 0118 PRAGMA discovery

Per Report 0118: `connect()` sets:
- `PRAGMA busy_timeout = 5000`
- `PRAGMA foreign_keys = ON`

**Every one of the 43 production importers gets these PRAGMAs FOR FREE.** The bypassers (Interpretation A violations) **do NOT** — silent loss of FK enforcement and busy-timeout retries.

**Specifically**: `server.py:5189 sqlite3.connect(...)` direct call — that connection has FKs OFF and no busy_timeout. Any DELETE/INSERT through it could create dangling rows that the FK-enforced connections would reject.

### Cross-link to Reports 0027 (ServerConfig) + 0090 (db_path)

`ServerConfig.db_path` (Report 0027 + 0090) is the canonical source of `PortfolioStore(db_path=...)` instances. Tests typically use `PortfolioStore(temp_path)` directly.

The 4 different RCM_MC_DB defaults (Report 0118 MR679) all flow into `PortfolioStore(...)` — the store doesn't care what default the caller used.

### `init_db` method (line 109-... per Report 0118 read)

Creates the `deals` table at minimum. Other tables created by their feature modules' `_ensure_table` helpers. Cross-link Report 0017.

### Test importers (194 — 82% of total)

194 test files use PortfolioStore, mostly via `PortfolioStore(temp_db_path)` for unit-test isolation. **Test-tight coupling**: a refactor of PortfolioStore breaks ~80% of the test suite.

Cross-link Report 0091: ~280 unmapped test files. PortfolioStore is in 194 of them — confirms the store is the primary test fixture.

### Why the coupling is acceptable

Per CLAUDE.md architecture invariant, all SQLite I/O flows through PortfolioStore. Tight coupling is **by design** — the store is meant to be the single SQLite seam.

The risk is **violation of the seam** (per Interpretation A above), not the coupling itself.

### Cross-link to Report 0111 MR626 (8+ modules talk to SQLite directly)

Per Report 0111: 8+ modules call `store.connect()` and execute SQL. **That's the legitimate path** — 8 of the 43 importers happen to be ones that do schema-creation work. Not a violation.

The actual violation is the 5+ modules calling `sqlite3.connect()` (this report's Interpretation A finding).

**MR626 in Report 0111 should be REVISED** — it conflated "modules calling SQLite via store" (legitimate, 8+) with "modules bypassing the store" (violation, 5+ per this report). MR626 was over-broad.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR708** | **5+ modules bypass `PortfolioStore` and call `sqlite3.connect()` directly** | server.py × 2 sites, ui/command_center, ui/portfolio_bridge_page, ui/pipeline_page (+ more). These connections have FKs OFF, no busy_timeout, no row_factory. Could create dangling rows that go unrejected. **HIGH-PRIORITY architectural violation.** | **Critical** |
| **MR626-REVISE** | **Report 0111 MR626 conflates legitimate `store.connect()` users with `sqlite3.connect` bypassers** | The 8+ modules using `store.connect()` are correct per architecture. The actual violators are 5+ modules calling `sqlite3.connect` directly. Cross-correction. | (correction) |
| **MR709** | **237 importers — extreme blast radius for any signature change** | Any rename/add-required-arg ripples through 237 files. Architectural decision: PortfolioStore must remain stable. Adding kwargs (Optional, default-None) is the only safe-ish modification. | (advisory) |
| **MR710** | **No interface-vs-implementation split** | `PortfolioStore` is a concrete class, not an ABC + impl. Tests can't easily swap a fake; they instantiate against a real temp SQLite. Acceptable per CLAUDE.md "no mocks for our own code" — but if a Postgres backend is ever added, an ABC would help. | Low |
| **MR711** | **Bypass routes (server.py:5189) likely lack PRAGMA foreign_keys = ON** | Cross-link Report 0118: PRAGMA is per-connection. If `server.py:5189` is a high-volume route, FKs are unenforced in that path. | **High** |

## Dependencies

- **Incoming:** 237 files (43 production + 194 tests). 15 subpackages.
- **Outgoing:** stdlib `sqlite3`, `contextlib`, `pathlib`, `typing` (per Report 0017).

## Open questions / Unknowns

- **Q1.** What are the OTHER `sqlite3.connect` direct callers (only top 10 shown in this iteration)?
- **Q2.** What does `server.py:5189` do — read-only? if so, less harmful than write-path bypasses.
- **Q3.** Why does `/api/backup` (server.py:3529-3530) bypass PortfolioStore? **Plausible reason**: SQLite backup API requires source AND destination connections, neither of which can use a context manager that closes-on-exit.
- **Q4.** Are tests for the 5+ bypass routes asserting that FK violations are caught? (Probably no — they wouldn't be, given the bypass.)

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0125** | Schema-walk `deal_overrides` (Report 0118 MR677, still owed). |
| **0126** | Read `ui/command_center.py` to assess severity of MR708. |
| **0127** | Comprehensive `sqlite3.connect` bypass enumeration (closes Q1). |
| **0128** | Read `cli.py` head (1,252 lines, 14+ iterations owed). |

---

Report/Report-0124.md written.
Next iteration should: schema-walk `deal_overrides` (Report 0118 MR677 high, carried 6+ iterations) — the most-deferred concrete task.
