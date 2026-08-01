# Report 0262: Post-Merge Re-Verification Sweep + infra/config & intake Hardening

## Scope

First fix-loop iteration since the April triage freeze. The tree moved from the April audit baseline to HEAD `a46a928` (July 2026: `feat/ui-rework-v3` landed, 75 commits on origin/main, Reports/PRs #1859-#1956). Every open TRIAGE item was re-verified against current code by an 8-cluster parallel sweep before any fix was applied. This report records (a) the verification verdicts, (b) 10 items closed with no code change, (c) 9 items fixed in commit `0e93f13`, and (d) one NEW high-severity finding surfaced during verification.

Sister reports: 0253 (config audit origin), 0252 (intake), 0261 (previous iteration).

## Part 1 — Verification verdicts (all open items, 8 clusters)

| Cluster | Still open | Already fixed / moot | Notes |
|---|---|---|---|
| infra-config | MR1046, MR1047, MR1049, MR1050 | MR1048 (warning landed upstream `2e3548e`), MR1051 (functionally dead) | all fixed this iteration |
| intake | MR1042, MR1045, MR1044 | — | all fixed this iteration |
| deals-FK | MR1059, MR1058 | — | **surfaced MR1068 (new, HIGH)** — see Part 4 |
| seed/exports | MR1061, MR1062, MR1063, MR1065, MR1066 | — | files now on main; next iteration |
| engagement | MR1024, MR988 | MR1029 (remove_member covered at test_engagement.py:135-140) | |
| pyproject | MR1037, MR978 (12 uncapped, all optional/dev), MR1039/MR1040 (documented-intentional, pin sync pending) | MR1041 (explicit file list at pyproject.toml:113-121 + gitignore defense) | |
| ai | MR1010 (4 lazy sites; real issue is store-less defaults skipping cache) | MR1001 (no-key guard + tests by design), MR1012 (Ollama backend landed — two backends now), MR1013 (no cross-package import exists) | |
| misc-root | MR1033, MR1034, MR1056 (worse: license file is 1 byte), MR1060, MR1067 (residual = 1 site: ml/fund_learning.py:46) | Q2 (RCM_MM/ gone), MR1005+MR1016 (git state moved on), MR486 (infra/migrations.py registry exists, startup-wired, tested), MR504/510 (three predictors have documented distinct roles + own tests — closed as accepted) | MR1032 changed: now 2 identical copies |

## Part 2 — Closed with no code change (verification-only)

| MR | Verdict | Evidence |
|---|---|---|
| MR1041 | already-fixed | package-data is an explicit file list (`profiles.example.yml` by exact name); `**/profiles.yml` gitignored with example whitelisted |
| MR1001 | already-fixed | `complete()` guards no-key at llm_client.py:232-236 → `[LLM not configured]` fallback; `is_configured` checked by all 4 callers; tested (test_phase_p.py:118-141); graceful degradation is the documented design |
| MR1012 | resolved-by-design | LLMClient now dispatches Ollama (primary) vs Anthropic (legacy fallback); LLM surface confined to ai/ + assistant/ |
| MR1013 | stale-moot | no ai/memo_writer → pe_intelligence/ic_memo import in either direction; the two memo systems are deliberately separate |
| MR486 | already-fixed | infra/migrations.py registry (6 entries, `_migrations` table, parameterised SQL) wired at server startup + dev/seed.py; tested (test_migration_idempotency.py) |
| MR1029 | already-fixed | remove_member exercised by MemberManagementTests.test_add_list_remove |
| MR1005 | stale-moot | origin/main current at a46a928 (2026-07-27); 75 commits landed since April |
| MR1016 | stale-moot | feat/ui-rework-v3 landed via normal PR flow months ago |
| Q2 (RCM_MM/) | stale-moot | directory no longer exists; never tracked by git |
| MR504/MR510 | closed-as-accepted | three predictors serve documented distinct roles (comparables filler / trained Ridge+CV engine / public-data screener), each with own tests + README coverage; consolidation would be a large behavior-changing refactor with no defect driving it |

## Part 3 — Fixed in commit `0e93f13`

| MR | Fix |
|---|---|
| MR1046 | explicit `__all__` (14 names) on infra/config.py + resolvability/no-private-names tests |
| MR1047 | `_extends` cycle guard: realpath visited-set threaded through recursion; circular chains raise `ConfigError("Circular _extends chain detected at ...")`; self-cycle, mutual-cycle, and legit-chain tests |
| MR1048 | contract locked by tests (set → substitute; unset+default → default; unset no-default → literal + warning). The "silent" half was already fixed upstream (`2e3548e` added the warning); closure = tests |
| MR1049 | why-focused docstring on canonical_payer_name (aliases + rationale) |
| MR1050 | load_and_validate documented as the canonical hard-fail entry; validate_config_from_path as the Step-37 soft wrapper; tie test asserts raise ↔ (False, [msg]) equivalence |
| MR1051 | MANDATORY_PAYERS deleted; server.py:8850 coverage import swapped to CURRENT_SCHEMA_VERSION; absence pinned by test |
| MR1042 | run_intake writes temp + `os.replace` (atomic on POSIX, same dir); try/finally unlinks temp on failure; test proves pre-existing actual.yaml survives a failed dump byte-for-byte |
| MR1045 | load_template raises `ValueError` naming the file for empty/null/non-mapping templates (was: silent `{}` → misleading "Missing 'hospital' section" much later) |
| MR1044 | `DEFAULT_TEMPLATE` constant; run_intake signature + interactive chooser both reference it; signature-default test |

Evidence: `python -m pytest tests/test_config_hardening.py tests/test_intake_hardening.py tests/test_config*.py tests/test_intake.py -q` => 89 passed; `tests/test_pressure_test.py tests/test_deal.py` (load_yaml consumers) => 41 passed. server.py imports clean after the swap.

## Part 4 — NEW finding: MR1068 (HIGH)

**`PortfolioStore.delete_deal` references three child tables by wrong names.** At store.py:174-189 the delete list says `deal_owners`, `health_scores`, `watchlist` — the actual tables are `deal_owner_history`, `deal_health_history`, `deal_stars`. Each per-table DELETE is wrapped in `except Exception: pass`, so the "no such table" errors are swallowed silently:

- On fresh DBs (post-91097a1 FK CASCADE) the final `DELETE FROM deals` cascades correctly, masking the bug.
- On live pre-April DBs (no FK), deleting a deal silently orphans rows in all three tables today.
- Compounding: `note_tags` has a bare NO-ACTION FK (MR1058), so `DELETE FROM deal_notes` inside delete_deal raises IntegrityError on any deal with tagged notes → swallowed → final `DELETE FROM deals` fails → **a deal with tagged notes cannot be deleted at all**.

Fix scheduled for the next iteration together with MR1058/MR1059 (single FK-correctness pass over the deals subpackage).

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR1068** | delete_deal wrong child-table names + swallowed errors → silent orphans (live DBs) and undeletable deals (tagged notes) | HIGH |

## Open questions / Unknowns

- **Q1.** CLAUDE.md claims delete cascade "across 23 child tables" — recount against delete_deal's actual list during the MR1068 fix.
- **Q2.** MR1048 kept warn-and-passthrough (back-compat) rather than fail-fast ConfigError for unset env vars without defaults. Revisit only if a partner hits a literal `${VAR}` in production config.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| next | MR1068 + MR1058 + MR1059 — one FK-correctness pass over deals/: fix delete_deal names, add 3 CASCADE clauses, ship the live-DB rebuild migration |
| after | seed/exports cluster (MR1061/1062/1063/1065/1066) |

---

Report/Report-0262.md written.
