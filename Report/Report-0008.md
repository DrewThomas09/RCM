# Report 0008: Test Coverage Spot-Check — `rcm_mc/portfolio/store.py`

## Scope

This report covers a **structural test-coverage audit of `RCM_MC/rcm_mc/portfolio/store.py`** on `origin/main` at commit `f3f7e7f`. The module was selected because `RCM_MC/CLAUDE.md` (per Report 0002) names `portfolio/store.py` as the **only module that talks to SQLite directly** — every alert, deal, portfolio operation, and simulation run goes through it. A coverage gap here = silent data-corruption risk during merge of any branch that schema-shifts the DB.

The audit lists every public function/method, counts test-file references for each, classifies tested vs untested, and flags complex untested paths. No tests are run; this is structural inspection only.

Prior reports reviewed before writing: 0001-0007.

## Findings

### Module shape (394 lines, last touched 2026-04-17 at commit before `f3f7e7f`)

- 1 module-level helper: `_utcnow` (private, line 18).
- 1 module-level helper: `_beta_params_from_mean_sd` (private, line 22).
- 1 module-level public function: `extract_primitives_from_config` (line 42).
- 1 dataclass: `RunRecord` (line 65, 8 fields).
- 1 main class: `PortfolioStore` (line 77) with **12 methods** + 1 nested helper.

The module imports `from ..core.distributions import sample_dist` (line 15) — its only `rcm_mc.*` outgoing dependency.

### Per-method coverage table

Coverage signal = number of test files that mention the method by name (`grep -rl "\.method(" RCM_MC/tests/`). This is a **structural floor**, not a logical floor — a test may reference a method without actually exercising every branch.

| Method (line) | Lines | Test files referencing | Verdict |
|---|---:|---:|---|
| `extract_primitives_from_config` (42) | 21 | **0** | **UNTESTED directly.** Exercised transitively via `add_run` (line 314 — `primitives_json = json.dumps(extract_primitives_from_config(cfg))`). |
| `RunRecord` (dataclass, 65) | 8 fields | 0 in tests; 0 in `rcm_mc/` outside store.py | **Output type returned by `get_run()` has no consumer outside store.py itself.** Exposed but never destructured. |
| `__init__` (80) | 4 | (covered transitively by 188 instantiations) | OK |
| `connect` (84) | 25 | 57 | OK (context manager, used everywhere) |
| `init_db` (109) | 30 | 61 | OK |
| `upsert_deal` (139) | 29 | **76** (the workhorse) | **Best-tested method in the module.** |
| **`delete_deal`** (168) | **43** | **1** (`tests/test_deal_deletion.py` only) | **CRITICAL GAP.** 23-table cascade-DELETE + per-table silent exception-swallow. Most-destructive method, least-tested. |
| **`clone_deal`** (211) | **44** | **1** (`tests/test_improvements_b88.py` only) | **CRITICAL GAP.** Uses `PRAGMA table_info` + dynamic column-list SQL. Schema-shift breaks it silently. |
| `archive_deal` (255) | 11 | 3 | Adequate (simple status flip). |
| `unarchive_deal` (266) | 11 | 1 | Light (simple status flip). |
| `list_deals` (277) | 23 | 10 | Adequate. |
| `add_run` (300) | 24 | **1** (`tests/test_portfolio.py` only) | **HIGH GAP.** Persists run records — 1 of the 2 paths into the `runs` table. Most run records in production come from `cli.py` / `portfolio_cli.py`. Test surface barely exercises the run-write path. |
| `list_runs` (324) | 14 | **0** (zero!) | **UNTESTED.** Production callers: `cli.py`, `server.py`, `portfolio_cli.py`, `infra/run_history.py`. |
| `get_run` (338) | 7 | **0** (zero!) | **UNTESTED.** Returns `RunRecord` (which has no other consumer). Production callers: same as `list_runs`. |
| `export_priors` (345) | **50** | 1 | **HIGH GAP.** Longest method in the module. Exports calibration priors to YAML — silent regressions = wrong MC simulations. |

### Coverage summary

- **13 callable surfaces** in the module.
- **3 with zero direct test references**: `extract_primitives_from_config`, `list_runs`, `get_run`.
- **6 with only 1 test reference**: `delete_deal`, `clone_deal`, `unarchive_deal`, `add_run`, `export_priors`, plus `extract_primitives_from_config` (via add_run only).
- **4 well-tested**: `connect`, `init_db`, `upsert_deal`, `list_deals`.

**Median coverage per method = 3 test references. The riskiest methods (delete_deal, clone_deal, export_priors) are at the floor.**

### Why no `tests/test_store.py` exists

There is **no dedicated unit-test file** for `portfolio/store.py`. Confirmed: `ls RCM_MC/tests/*store*.py` returns empty. The store is only tested transitively: 188 test files instantiate `PortfolioStore` as fixture setup and exercise the methods they happen to need. There is no file whose explicit job is "verify the store contract."

This is a structural gap, not a coverage gap — coverage is moderate via integration tests, but no single file enumerates every method's contract.

### Complex untested branches

| Branch | Complexity | Test floor |
|---|---|---|
| `delete_deal` line 174-183: 23-table cascade list | If a feature branch adds a child table referencing `deal_id` and forgets to extend this list, **deletes will leave orphan rows** (i.e. the deal "reappears" on cascade-recompute). | 1 test |
| `delete_deal` line 195-201: per-table `try/except: pass` | **Per-child-table silent exception-swallow.** If schema drifts and a column is renamed, `DELETE FROM tbl WHERE deal_id = ?` will fail and the failure is silent. | 1 test |
| `delete_deal` line 184-208: `BEGIN IMMEDIATE` lock + commit + raise | Concurrency-correctness contract. If a concurrent reader holds a lock, this method should retry under `busy_timeout=5000`. Untested concurrency. | 1 test |
| `clone_deal` line 232-237: `PRAGMA table_info` + dynamic column list | If a feature branch adds a column to `deal_tags` or `deal_sim_inputs` that should NOT be cloned (e.g. a UUID, a timestamp), it gets cloned anyway. | 1 test |
| `add_run` line 314: `primitives_json = json.dumps(extract_primitives_from_config(cfg))` | If `extract_primitives_from_config` raises (bad config), `add_run` raises — but no test exercises a bad-config path. | 1 test (for add_run); 0 for extract_primitives. |
| `export_priors` line 345-394: 50-line aggregation + Beta-distribution fit | The most numerically-complex path. `_mean_sd` nested helper. Silent fitting failures (e.g. `_beta_params_from_mean_sd` falling back to "conservative prior" path lines 33-38) won't appear in 1-test coverage. | 1 test |

### Untested-but-callable inventory

The following are **publicly callable** and have **zero direct test reference**:

1. `store.list_runs(deal_id=None)` — used by `cli.py` `rcm-mc list-runs` (probably) and the `/runs` route in `server.py`. Untested.
2. `store.get_run(run_id)` — used to render `RunRecord` for export. Untested.
3. `RunRecord` dataclass — exposed shape that 0 consumer destructures (no `.run_id`, `.deal_id`, etc. attribute access in tests or production outside store.py).
4. `extract_primitives_from_config(cfg)` — top-level public function, exercised only inside `add_run`.

Each of these is a path where a feature branch could change the contract (rename a field on `RunRecord`, change `list_runs` columns, add a kwarg to `extract_primitives_from_config`) and **no test would fail**.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR55** | **HIGH-PRIORITY: 23-table delete-cascade list is hand-maintained, single test covers it** | If any branch adds a new child table with a `deal_id` column (`feature/connect-partner-brain-phase1` adds new tables for partner brain — likely candidate), `delete_deal`'s cascade list must be extended. **Test will pass even if you forget**, because the only test (`test_deal_deletion.py`) only checks the tables that existed when the test was written. Pre-merge: enumerate every `CREATE TABLE` across all branches and cross-check against `child_tables` at line 174-183. | **Critical** |
| **MR56** | **`clone_deal`'s PRAGMA-driven column list silently clones new columns** | If a branch adds a `cloned_from_deal_id` audit column to `deal_tags`, the column gets cloned — leaking provenance from the source deal into the clone. Test (`test_improvements_b88.py`) likely doesn't check this. | **High** |
| **MR57** | **`extract_primitives_from_config` is exercised only via `add_run`** | Both functions have 1 test (`test_portfolio.py`). If a branch changes the config schema (likely on `feature/workbench-corpus-polish`'s "editorial reskin" or any branch that touches configs/), the resulting MC priors will be silently wrong. | **High** |
| **MR58** | **`list_runs` / `get_run` have ZERO direct tests** | Production callers in `cli.py`, `server.py`, `portfolio_cli.py`, `infra/run_history.py`. If a branch renames a column in the `runs` table (or removes one), tests pass; production fails on first call to one of these methods. | **High** |
| **MR59** | **`RunRecord` dataclass has 0 external consumers** | The dataclass is returned by `get_run()` but nothing destructures it. If a branch removes the dataclass entirely, `get_run` would still need to return *something* — refactor risk that tests can't catch. | Medium |
| **MR60** | **`export_priors` is the longest method (50 lines) with 1 test reference** | Aggregates summary statistics + fits Beta priors. The fitting path has a "conservative fallback" branch (`_beta_params_from_mean_sd` lines 33-38) that no test surfaces. Pre-merge: any branch that changes the runs-table schema or adds new prior types breaks this silently. | **High** |
| **MR61** | **No dedicated `test_store.py` file** | 188 test files reference `PortfolioStore` but there is no single file whose job is to enumerate the store's contract. Hard to bisect a regression to "the store layer broke." | Medium |
| **MR62** | **`delete_deal` swallows per-table DELETE exceptions silently** | Lines 195-201: `except Exception: pass`. A schema rename (column dropped, table renamed) will silently no-op the cascade. Combined with MR55, this is a multiplier on the cascade-list risk. | **High** |
| **MR63** | **`store.py` is 188-test-file-coupled** | Any signature change to `init_db`, `upsert_deal`, `connect` will cascade across 188 test files. **Pre-merge audit must verify no ahead-of-main branch changes these signatures**, otherwise the test sweep will explode. | **High** |

## Dependencies

- **Incoming (who depends on `store.py`):** 188 test files. Production consumers (per Report 0005 server.py grep + this iteration's check): `cli.py`, `server.py`, `portfolio_cli.py`, `infra/run_history.py`, `analysis/__init__.py` (via re-exports), `portfolio/__init__.py`. The store is the singular SQLite gate — every persisted operation flows through it.
- **Outgoing (what `store.py` depends on):** stdlib (`json`, `sqlite3`, `contextlib`, `dataclasses`, `datetime`, `pathlib`, `typing`); third-party (`numpy`, `pandas`, `pyyaml`); internal (`from ..core.distributions import sample_dist` — line 15, **only one internal import**).

## Open questions / Unknowns

- **Q1 (this report).** Do any of the 188 test files that instantiate `PortfolioStore` exercise `list_runs` or `get_run` indirectly through a wrapper (e.g. via `infra/run_history.py`)? Need to trace these wrappers to see if there's transitive coverage.
- **Q2.** Are the 23 child tables in `delete_deal`'s cascade list complete? Need to enumerate every table on origin/main with a `deal_id` column and diff against the list.
- **Q3.** Does any feature branch add a new `deal_id`-bearing table that's missing from `delete_deal`? Pre-merge sweep needed.
- **Q4.** What does `_beta_params_from_mean_sd`'s "conservative fallback" path (lines 33-38) actually produce? Is the fallback empirically reasonable, or does it inflate uncertainty in production runs?
- **Q5.** Is there a reason there's no dedicated `tests/test_store.py`? Was one removed at some point? `git log --diff-filter=D --name-only -- 'RCM_MC/tests/test_store*.py'` would reveal.
- **Q6.** Does `extract_primitives_from_config` handle missing payer config blocks gracefully? Line 46 `for payer, pconf in cfg.get("payers", {}).items():` is fine, but line 48 `dar = sample_dist(rng, pconf["dar_clean_days"], size=int(n_draws))` will KeyError on missing field. No test covers this.
- **Q7.** What's the actual production volume of `add_run` calls per session? If it's high, the lack of integration testing for the run-write path is more risky than the test count suggests.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0009** | **Enumerate every SQLite table created across `rcm_mc/`** by grepping `CREATE TABLE IF NOT EXISTS` in all `.py` files. Build the canonical schema map. Cross-check the 23 entries in `delete_deal`'s `child_tables` list. | Resolves Q2, MR55, MR62. The single most actionable schema-correctness check. |
| **0010** | **Per-commit walk of `feature/workbench-corpus-polish`** — owed since Report 0007. The 21 commits to triage. | Cherry-pick plan. |
| **0011** | **Branch-by-branch grep of `delete_deal` / `clone_deal` / signatures** — does any ahead-of-main branch touch these? | If yes, merge-risk amplification (MR63). |
| **0012** | **Read `rcm_mc/diligence/INTEGRATION_MAP.md`** — owed since 0004, 0005, 0006, 0007. | Repeatedly deferred; likely answers many merge questions. |
| **0013** | **Map `infra/run_history.py`** — Q1 / probable wrapper around `list_runs`/`get_run`. | If `run_history.py` is the de-facto run-table reader, store.py's `list_runs`/`get_run` may be vestigial; coverage gap is then less severe. |
| **0014** | **`feature/demo-real` per-commit walk** — confirm vs polish (Report 0006 Q1 still open). | Drops dead branch if confirmed-subset. |
| **0015** | **Walk `rcm_mc/cli.py`** (1,252 lines) — owed since 0003. Closes MR14. | The broken `rcm-intake` entry point still unresolved. |

---

Report/Report-0008.md written. Next iteration should: enumerate every `CREATE TABLE IF NOT EXISTS` across `rcm_mc/` and cross-check against the 23-entry cascade list at `portfolio/store.py:174-183` — directly resolves MR55 and produces the canonical schema map for all future merge-risk reasoning.

