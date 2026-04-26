# Report 0258: `dev/seed.py` Audit (MR1017 closure)

## Scope

Closes Report 0247 / MR1017: never-read 896-LOC seeder that lands as part of `feat/ui-rework-v3`. This iteration reads the file via `git show origin/feat/ui-rework-v3:RCM_MC/rcm_mc/dev/seed.py` and audits the API + side-effects + production-safety guards. Does not modify code on either branch — purely an audit/inventory closure so the merge author has the risk picture.

Sister reports: 0247 (feat-branch diff stat), 0250 (orphan-files cross-link), 0181 (delete-policy matrix), 0256 (deal-child FK frontier).

## Findings

### Inventory

- File: `RCM_MC/rcm_mc/dev/seed.py` on `origin/feat/ui-rework-v3` (does not exist on `origin/main`).
- Size: **896 LOC**, ~30KB.
- Branch source: introduced via commits `a7c0a22` / `b0b542e` / `24b88c7` / `03babe9` / `b2a2bf0` per Report 0247 commit log.

### Public API

| Name | Line | Role |
|---|---|---|
| `SeederRefuseError(RuntimeError)` | 121 | exception when the seeder declines to run |
| `SeedResult` (dataclass) | 155 | row counts for the verify path |
| `VerifyResult` | 619 | counts for `--verify` flag |
| **`seed_demo_db(db_path, *, deal_count=7, snapshot_quarters=8, seed_random=20260425, overwrite=False, write_export_files=True, base_dir=None, force=False) -> SeedResult`** | 736 | the orchestrator |
| `verify_seeded_db(db_path) -> VerifyResult` | 637 | re-runs DEMO_CHECKLIST checks |
| `main(argv=None) -> int` | 865 | CLI: `python -m rcm_mc.dev.seed --db ...` |

### Side-effects

1. **SQLite writes**: deals, deal_snapshots, deal_stage_history, initiative_actuals, analysis_runs (via `get_or_build_packet`), generated_exports.
2. **Filesystem writes**: placeholder export files under `tempfile.gettempdir() / "rcm_mc_demo_exports"` by default (overridable via `--base-dir`).
3. **Calls into production code**: per docstring, "the seeder runs the real `get_or_build_packet()` pipeline" — coupling dev seeder to the canonical analysis seam (Report 0162 hash_inputs cache lives there).

### Production-target guard

```python
_PROD_HINTS = ("/data/", "seekingchartis.db")

def _guard_against_production(db_path, *, force):
    if force: return
    resolved = str(db_path.resolve())
    if any(hint in resolved for hint in _PROD_HINTS):
        raise SeederRefuseError(...)
```

**Heuristic — string-match on path.** Recognizes:
- absolute paths under `/data/`
- any path whose resolved form contains `seekingchartis.db`

Operator can override with `force=True` (or `--force-prod-path` CLI flag).

### Determinism

Default `seed_random=20260425` (the date the seeder was authored). Same seed → byte-for-byte identical output (deals, EBITDA values, covenant trajectories). This is the right shape for a CI dependency.

### Cross-link to iter-23 fix (commit `91097a1`)

The seeder uses `--overwrite` to drop+recreate seeded tables. With the iter-23 FK CASCADE fix, deleting a deal now cleanly removes all 5 previously-orphaning child rows (deal_sim_inputs, deal_owner_history, deal_health_history, deal_deadlines, deal_stars). Without the iter-23 fix, `--overwrite` would have left orphan rows in those 5 tables on every reseed.

**The seeder's `--overwrite` path is materially safer post-iter-23.** Worth flagging in the merge handoff.

### Cross-link to iter-13 fix (commit `2fc6715`)

`seed_demo_db` calls `get_or_build_packet()` which now folds actual.yaml + benchmark.yaml SHA-256 into the cache key. The seeder writes its own actual/benchmark fixtures (per `write_export_files=True`); the cache key correctly covers them.

### CLI surface

```
python -m rcm_mc.dev.seed --db /tmp/demo.db
python -m rcm_mc.dev.seed --db /tmp/demo.db --overwrite --deal-count 10
python -m rcm_mc.dev.seed --db /tmp/demo.db --no-export-files
python -m rcm_mc.dev.seed --db /tmp/demo.db --verify
```

`--verify` re-runs the DEMO_CHECKLIST checks (per commit `24b88c7`) without re-seeding.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR1061** | **Heuristic production guard** at `seed.py:134` matches only `/data/` and `seekingchartis.db`. A partner running their DB at `~/portfolio.db` would NOT trigger the guard; `--overwrite` against that path silently truncates real data. | Tighten the heuristic at merge: also reject filenames matching `*.db` outside `/tmp/`, `/var/folders/`, or an explicit dev-mode env var. | Medium |
| **MR1062** | **Seeder couples to production analysis pipeline** via `get_or_build_packet()`. Changes to packet_builder semantics will change seeder output non-determinism unless the seed_random is re-pinned. | Document the contract; consider a frozen-output golden file under `tests/`. | Low |
| **MR1063** | **`--overwrite` is partially safe post-iter-23** but only for the 5 newly-cascading tables on FRESH DBs. Live DBs missing the FK still leak orphans on `--overwrite` until MR1059 ALTER migration lands. | Document; do not `--overwrite` against an old live DB before MR1059 is shipped. | Medium |
| **MR1017** | (RETRACTED — closed) `dev/seed.py` was never read | (closure) | (closed) |

## Dependencies

- **Incoming on feat/ui-rework-v3:** demo flow + `--verify` flag wired in `tests/test_dev_seed.py` (209 LOC) + `tests/test_dev_seed_integration.py` (180 LOC) per Report 0247.
- **Outgoing:** PortfolioStore, deals/ + analysis/ + exports/ subpackages, `get_or_build_packet`.

## Open questions / Unknowns

- **Q1.** Does the heuristic guard (MR1061) need expansion before merge? The two `_PROD_HINTS` cover `/data/` deploy paths and the canonical filename, but miss the partner's own `~/portfolio.db`.
- **Q2.** Does the seeder respect or bypass `RCM_MC_PHI_MODE` (per Report 0119 / CLAUDE.md PHI banner)? Likely irrelevant since seed data is fictional, but worth confirming for compliance audit trails.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| (post-merge) | Tighten the production guard in MR1061 — minimum: also reject any path under `$HOME` unless `force=True`. |
| (post-merge) | Verify the dev/seed.py + iter-23 FK CASCADE interaction with a real `--overwrite` integration test. |
| (post-merge) | Read `dev/seed.py` body (lines 198-633) for the per-block seed logic — this audit covered head + key functions only. |

---

Report/Report-0258.md written.
