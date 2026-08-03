# Report 0273: Exception-Swallow Reliability Sweep — clone_deal partial-clone bug + SQL vein clean (commit cdce76f)

## Scope

Fourth fresh post-TRIAGE sweep, shifting from security (XSS/traversal, now mined out) to **reliability**: the over-broad-exception-swallow class that has yielded the most real bugs this session (delete_deal wrong table names, canonical_facade manifest, seeder cleanup — all fixed). A 3-lens hunt (DB writes / filesystem+exports / silent coercion) surfaced 6 candidates; each was adversarially verified with the prompt tuned to **refute** legitimate best-effort catches (audit/telemetry/cache/optional-dep). **5 refuted, 1 confirmed.** The 5:1 refute ratio is the point — most swallows are intentional, and the verify pass filtered them.

## Confirmed + fixed (commit cdce76f)

**`clone_deal` commits a partial clone and returns True (store.py:313).** The exact sibling of the delete_deal bug fixed in Report-0263, in the same file. The child-table copy loop (`deal_tags`, `deal_sim_inputs`) wrapped `PRAGMA table_info` + `INSERT ... SELECT` in `except Exception: pass` — intended only to tolerate a lazily-absent table, but it also ate genuine failures (locked DB after busy_timeout, disk I/O error, a constraint violation from schema drift). Execution then fell through to `con.commit()` + `return True`.

Consequence: the clone commits the new `deals` row without the child rows whose copy raised, and reports full success. Concretely, if the `deal_sim_inputs` copy fails, the cloned deal has no actual/benchmark paths, so the partner's "rerun simulation" shortcut silently has nothing to run — no error ever surfaced. The `POST /api/deals/<id>/duplicate` handler only checks the True/False return, fires a `deal.created` webhook, and reports `{"cloned": true}`, so nothing downstream catches it.

**Fix:** mirror the delete_deal narrowing — skip a table up front when `PRAGMA table_info` returns no columns (the sole tolerated "not created yet" case); let any real error propagate to the outer `except` (which rolls back the whole clone and re-raises). An incomplete clone is now never committed or reported as success.

## Also recorded (no code change): SQL-injection vein clean

Before the swallow sweep, audited every f-string/`.format`/`%` interpolation into `execute()` package-wide (15 sites). All are safe: interpolated **identifiers** come from hardcoded constants or fixed lists —
- `deal_library.py` CREATE/ALTER: column names + type keywords from `_ALL_COLS` schema constants;
- `tuva_bridge.py` `raw_data."{name}"`: `name` from a fixed 3-key dict (`medical_claim`/`pharmacy_claim`/`eligibility`);
- `rxnorm/store.py` `FROM {t}`: `t` from a fixed 5-table list;
- `migrations.py` `{table}`/`{tmp}`: from the module's own rebuild specs;
- `seed.py`/`refdata_packs.py` `DELETE FROM {table}`: hardcoded tuples.

Every **value** is parameterized. The SQL-injection class is verified clean across the data layer and package-wide.

## Evidence

- `tests/test_deal_id_validation.py` +3: clone succeeds when the lazy child tables are absent; clone copies `deal_sim_inputs` paths; a genuine child-copy failure (forced with a `RAISE(ABORT)` trigger on `deal_tags` — a real, unmocked DB error) rolls back the whole clone, leaving no partial `deals` row and raising instead of returning True.
- Regression: `test_deal_id_validation`, `test_improvements_b88` (existing clone-via-store + clone-via-API tests) → 20 passed.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| next | The swallow class is now largely swept (5:1 refute ratio suggests diminishing returns). Consider an auth/session review, a concurrency/transaction-boundary pass, or the `pe_intelligence/` package map. |

---

Report/Report-0273.md written.
