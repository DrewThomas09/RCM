# Report 0264: Seeder + Canonical-Export Hardening — MR1061/1062/1063/1065/1066 (commit 186b06a)

## Scope

The five open items on the two files that landed on main from feat/ui-rework-v3: dev/seed.py (the demo seeder) and exports/canonical_facade.py (the 11-facade canonical export layer). All five verified still-open in Report-0262's sweep; all five closed here.

Sister reports: 0258 (seed.py audit origin), 0259 (canonical_facade audit origin), 0262 (re-verification), 0263 (FK pass this builds on).

## Fixes (commit 186b06a)

**MR1061 — overwrite provenance guard (seed.py).** The production guard was a two-string path heuristic (`/data/`, `seekingchartis.db`); a partner's `~/portfolio.db` sailed through and `--overwrite` then blanket-deleted six tables. `--overwrite` is now provenance-gated: every existing deal must trace to a seed-stamped `deal_stage_history` row (`changed_by='seed'`), else `SeederRefuseError` — refusal leaves the DB untouched (tested). `force=True` still overrides for operators who mean it. The path heuristic stays as the first line.

**MR1063 — transactional, complete overwrite cleanup (seed.py).** The cleanup loop ran one autocommit DELETE per table with `except Exception: pass`. Three defects: (a) `covenant_metrics` was missing although the seeder inserts covenant rows with plain INSERTs — every re-seed doubled them (regression test pins equal counts across two overwrite runs); (b) `quarterly_actuals` was missing — its NO-ACTION FK blocked `DELETE FROM deals` on any held-deal DB, and the swallow left the DB half-cleared (children wiped, deals intact); (c) nothing was transactional. Now: one `BEGIN IMMEDIATE` covering `note_tags, deal_notes, deal_snapshots, deal_stage_history, initiative_actuals, generated_exports, analysis_runs, covenant_metrics, quarterly_actuals, deals`; only "no such table" tolerated; anything else rolls the whole cleanup back and raises.

**MR1062 — seed_random consumed (seed.py).** The parameter was accepted, CLI-exposed (`--seed`), and documented as "byte-for-byte identical" — and never touched any RNG. `seed_demo_db` now seeds both `random` and `numpy.random` before the pipeline runs. Test proves the post-run RNG stream is identical across two runs regardless of prior RNG state.

**MR1065 — unlink-before-move removed (canonical_facade.py).** `_move_to_canonical` unlinked the existing canonical file before `shutil.move`. Every caller holds the source inside a `TemporaryDirectory`, so a crash between unlink and move destroyed **both** copies. rename/copy2 both overwrite the destination; the unlink was pure risk. Docstring records the reasoning; test proves overwrite-without-pre-unlink and that a failed move preserves both the source and the old canonical content.

**MR1066 — manifest failures logged (canonical_facade.py).** `_record`'s `except Exception: pass` becomes a `logger.warning` naming the artifact and deal (still swallowed — the artifact on disk is load-bearing; the audit row is best-effort by design). Module gains its `logging` setup. Test drives the real `record_export` path against a failing store and asserts the warning.

## Evidence

- New: `tests/test_dev_seed_hardening.py` (5 tests: refusal + untouched-DB, force override, pure-seed overwrite, covenant no-duplication, RNG determinism) and `tests/test_canonical_facade.py` (4 tests: overwrite semantics, parent-dir creation, failed-move preservation [skips as root], manifest-failure logging).
- Full seed + export surface green: `test_dev_seed.py`, `test_dev_seed_integration.py`, all 9 `test_*export*.py` files → **119 passed** (2 pre-existing skips).

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| (closure) | MR1061, MR1062, MR1063, MR1065, MR1066 all closed | — |
| **Q1** | Seeder `--overwrite` wipes user-authored notes on seed deals (deliberate: the deal itself is being replaced; provenance guard ensures only demo DBs get here). Documented, not fixed. | LOW |

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| next | pins + misc cluster (MR1037/978/1039/1040, MR1067 residual, MR1032, MR1034, MR1056) |

---

Report/Report-0264.md written.
