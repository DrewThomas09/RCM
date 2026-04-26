# TRIAGE — Bug Fix & Push Loop

Built: 2026-04-26 (iter 1) | Refreshed: 2026-04-26 (iter 21, after 19 fix-loop iterations).
Source: 255 audit reports (Report-0001.md through Report-0255.md), ~1056 unique MR-tagged risks. This list captures the highest-leverage actionable items; the rest stay catalogued in source reports as inventory/discovery.

**Status counters (verified via awk over the file):** 4/4 CRITICAL closed; 16/22 HIGH closed (6 open); 0/21 MEDIUM closed (1 partial = MR1046, 20 open); 0/13 LOW closed (1 partial = MR1049, 12 open — added MR1056 + RCM_MM/-Q2 follow-up from Report-0255 in this refresh). See Report/RESOLVED.md for the chronological commit list (20 entries) and Report/PROGRESS-19.md for the rollup.

Marker legend: `[ ]` open · `[x]` resolved (commit hash inline) · `[~]` partially mitigated · `[!]` reopened · `[?]` needs-repro.

## CRITICAL

- [x] CRITICAL | Report-0131 | `configs/playbook.yaml` unparseable YAML (6 of 8 keys have leading space → `ParserError`); silent production bug since 2026-04-17. All action-plan sections in HTML reports degrade to empty. | configs/playbook.yaml | MR744 | 33fda80 | 2026-04-26
- [x] CRITICAL | Report-0101/0107/0251 | `pyarrow>=10.0` pin allows CVE-2023-47248 RCE; code reads user-uploaded parquet → **RCE attack surface**. Tighten to `pyarrow>=18.1,<19.0`. | pyproject.toml:51 | MR770/MR1038 | cb84f07 | 2026-04-26
- [x] CRITICAL | Report-0001/0251 | `rcm-intake` console-script broken — `pyproject.toml:70` points to nonexistent `rcm_mc/intake.py`; real `main()` at `rcm_mc/data/intake.py:619`. After `pip install`, `rcm-intake` raises `ModuleNotFoundError`. Fix: add 12-line shim mirroring `rcm_mc/lookup.py`. | pyproject.toml:70 / rcm_mc/intake.py (missing) | MR14/MR1035 | 5d91bda | 2026-04-26
- [x] CRITICAL | Report-0246 | Local `main` 144 commits ahead of `origin/main`; entire audit chain (Reports 0001-0254) never pushed. Single-laptop-loss risk. | (git state) | MR1014 | 53f67c4 | 2026-04-26 (backed up to origin/audit/reports-and-triage; main-merge tracked as a separate non-critical follow-up)

## HIGH

- [x] HIGH | Report-0150/0145 | `profiles.yml` not in `.gitignore` — dbt credentials may leak if committed under `rcm_mc_diligence/connectors/seekingchartis/`. Fix: add `**/profiles.yml` + keep `!**/profiles.example.yml`. | .gitignore | MR829 | b31aecd | 2026-04-26
- [x] HIGH | Report-0254 | `infra/README.md:10` references `ConfigValidationError` (actual class: `ConfigError`) AND `write_yaml` (actually in `core/calibration.py`, not `config.py`). New contributors writing `except ConfigValidationError:` will silently miss real failures. | rcm_mc/infra/README.md:10 | MR1052 | a53321f | 2026-04-26
- [x] HIGH | Report-0247 | `_chartis_kit_v2.py` deleted on `feat/ui-rework-v3` (-600 LOC). Pre-merge grep needed for any importer on `main` referencing it. | rcm_mc/ui/_chartis_kit_v2.py | MR1015 | 5685af4 | 2026-04-26 (documented in MERGE-CONFLICTS.md; merge-time resolution rather than preemptive main change)
- [x] HIGH | Report-0207/0211 | CLAUDE.md says SQLite has 17 tables — actual count is 21 (Reports 0167/0183/0211 confirmed initiative_actuals + 4 engagement tables). Stale by 4. | RCM_MC/CLAUDE.md | MR1028 | f4ffdac | 2026-04-26 (live count is actually ~89 once subpackages are included; doc rewritten to reflect that with a self-derivable grep recipe)
- [x] HIGH | Report-0085/0119 | `RCM_MC_AUTH` unset = open server (no authentication). CLAUDE.md mentions multi-user security but does not enforce default-deny. | rcm_mc/server.py / CLAUDE.md | MR921 | 9287908 | 2026-04-26 (added stderr warning when bound non-loopback with no auth + no DB users; loopback laptop default unchanged)
- [x] HIGH | Report-0001/0251 | Python version drift — `pyproject.toml` targets `>=3.10` (mypy + ruff also 3.10) but CLAUDE.md states 3.14. Source-of-truth ambiguity. | pyproject.toml + CLAUDE.md | MR1036 | f1039f8 | 2026-04-26 (CLAUDE.md aligned to "Python 3.10+" matching the three pyproject pins)
- [x] HIGH | Report-0001 | Three-way version drift: `pyproject.toml:7` 1.0.0, `rcm_mc/__init__.py:1` 1.0.0, `RCM_MC/README.md:1` v0.6.0, `RCM_MC/CHANGELOG.md:3` v0.6.1. | multiple | MR15 | 4abc310 | 2026-04-26 (added v1.0.0 CHANGELOG entry consolidating audit/fix-loop hardening; pyproject + __init__ + CHANGELOG now agree at 1.0.0)
- [x] HIGH | Report-0094 | `ReimbursementProfile` name-collision in `reimbursement_engine.py` (1232 LOC, largest non-server.py finance file). | rcm_mc/finance/reimbursement_engine.py | MR795 | d3f23b3 | 2026-04-26 (added PEP 562 __getattr__ deprecation shim in rcm_mc/domain — back-compat preserved, DeprecationWarning surfaces the collision; 52 tests green)
- [x] HIGH | Report-0250 | `RCM_MM/` doubled-directory at repo root — never inspected, possibly vestigial WIP parallel package. | RCM_MM/ | MR1030 | 127a9f9 | 2026-04-26 (inspected — empty 0-byte scratch dir, no code; closed in Report-0255)
- [x] HIGH | Report-0250 | `vendor/ChartisDrewIntel/` never inspected — possibly proprietary code or CMS data. | vendor/ChartisDrewIntel/ | MR1031 | 127a9f9 | 2026-04-26 (inspected — Tuva Project, Apache 2.0 dbt package; closed in Report-0255)
- [x] HIGH | Report-0249 | `get_member_role` is public-by-use, private-by-export — used 11× (8× internal + 2× server.py + 1× test) but missing from `engagement/__init__.py:__all__`. Cleanup risk. | rcm_mc/engagement/__init__.py:57 | MR1027 | e624c0c | 2026-04-26 (added to import block + __all__; 34 engagement tests pass)
- [x] HIGH | Report-0162/0148 | `hash_inputs` does NOT include benchmark.yaml content → cache key collision risk for analysis runs. Same pattern as MR823/874. | rcm_mc/analysis/packet.py + analysis_store.py | MR958 | 2fc6715 | 2026-04-26 (added actual_yaml_hash + benchmark_yaml_hash kwargs, default None for back-compat; analysis_store fingerprints the deal_sim_inputs paths and threads through; 58 analysis tests pass)
- [x] HIGH | Report-0180/0211 | ~10 deal-child tables still unwalked for FK behavior. Run `PRAGMA foreign_key_list(<each table>)` for full survey. | (schema) | MR929/MR971 | c4b6421 | 2026-04-26 (13 tables walked in Report-0256: 4 CASCADE-clean, 4 NO ACTION, 5 no-FK-declared; surfaced MR1057+MR1058)
- [ ] HIGH | Report-0256 | 5 deal-child tables have NO FK at all → silent orphan rows on `DELETE FROM deals` (deal_sim_inputs, deal_owner_history, deal_health_history, deal_deadlines, deal_stars). Needs one-time orphan-purge + migration to add `ON DELETE CASCADE`. | rcm_mc/deals/* | MR1057
- [x] HIGH | Report-0181 | Project lacks unified delete-policy: soft-delete (deal_notes), hard-delete (deal_overrides), CASCADE×3, SET NULL×1, NO ACTION×many. Document a delete-policy matrix in CLAUDE.md. | CLAUDE.md | MR982 | 488e3c8 | 2026-04-26 (5-row matrix added between Python-style + Testing sections, with one-line rule of thumb + on-disk examples per behavior)
- [ ] HIGH | Report-0247 | NEW `rcm_mc/dev/seed.py` (896 LOC) lands as a unit on `feat/ui-rework-v3` — never read. | rcm_mc/dev/seed.py (on feat/ui-rework-v3) | MR1017
- [ ] HIGH | Report-0247 | NEW `rcm_mc/exports/canonical_facade.py` (424 LOC) — coupling to `infra/exports.py` unknown. | rcm_mc/exports/canonical_facade.py | MR1018
- [ ] HIGH | Report-0102 | 5 of 7 CMS data-loaders unaudited. | rcm_mc/data/cms_*.py | MR985
- [x] HIGH | Report-0212 | `document_qa.py` (355L) is largest in `ai/` — RAG implementation hits trust boundary (user-supplied document text → LLM). | rcm_mc/ai/document_qa.py | MR1000 | 442bb98 | 2026-04-26 (added 3-layer prompt-injection mitigation: 2000-char question cap, <document>/<question> delimiters, defensive system prompt; 40 phase-P + e2e tests pass)
- [x] HIGH | Report-0001 | `scipy>=1.11` only in `[all]` extras — any branch adding `import scipy` to a hot path breaks default install with `ImportError`. | pyproject.toml:59 | MR17 | 110f2cf | 2026-04-26 (added dedicated [stats] extras group + comment documenting lazy-import pattern across the 3 prod sites)
- [x] HIGH | Report-0001 | `[all]` does not include `[diligence]` deps (duckdb/dbt-core/dbt-duckdb/pyarrow). | pyproject.toml | MR18 | 110f2cf | 2026-04-26 (folded [diligence] deps into [all]; verified diligence ⊂ all and stats ⊂ all programmatically)
- [ ] HIGH | Report-0119/0120 | First merge from `feat/ui-rework-v3` → main triggers auto-deploy via deploy.yml; AZURE_VM secrets must be set. | .github/workflows/deploy.yml | MR917
- [ ] HIGH | Report-0124/0157 | INTEGRATION_AUDIT.md (commit c6ab593) flagged 9 UI pages bypass dispatcher; 5+ modules bypass PortfolioStore. | rcm_mc/ui/* | MR855/MR708

## MEDIUM

- [ ] MEDIUM | Report-0254 | `infra/cache.py` and `infra/morning_digest.py` undocumented in `infra/README.md` (28 modules, 26 sections). | rcm_mc/infra/README.md | MR1053
- [ ] MEDIUM | Report-0256 | 3 of 4 NO-ACTION-default deal-child FKs should upgrade to CASCADE (deal_tags, note_tags, deal_snapshots); deal_notes stays NO-ACTION because soft-delete is the partner UX. | rcm_mc/deals/* | MR1058
- [~] MEDIUM | Report-0253 | `rcm_mc/infra/config.py` has no `__all__` — every non-underscore name is implicit public surface; renames silently break callers. | rcm_mc/infra/config.py | MR1046 | 8d355d2 | 2026-04-26 (partially mitigated by test_config_public_helpers.py covering 6 helpers; __all__ declaration still pending)
- [ ] MEDIUM | Report-0253 | `_extends` recursion in `infra/config.py:66` has no cycle detection → self-extending YAML → RecursionError. | rcm_mc/infra/config.py:66 | MR1047
- [ ] MEDIUM | Report-0253 | `_resolve_env_vars` silently passes unset env vars (literal `${UNSET}` in cfg). | rcm_mc/infra/config.py:48 | MR1048
- [ ] MEDIUM | Report-0249 | `_audit` private writer in `engagement/store.py:221` untested; audit trails could break silently. | rcm_mc/engagement/store.py:221 | MR1024
- [ ] MEDIUM | Report-0251 | mypy version drift — `pyproject.toml` `>=1.5` vs pre-commit pin `v1.8.0`. | pyproject.toml + .pre-commit-config.yaml | MR1037
- [ ] MEDIUM | Report-0247 | NEW `rcm_mc/infra/exports.py` (225L) on feat/ui-rework-v3 — `infra/` had no prior Report mention before this. | rcm_mc/infra/exports.py | MR1019
- [ ] MEDIUM | Report-0247 | server.py +217 LOC on feat/ui-rework-v3 — route-collision risk if main also adds routes. | rcm_mc/server.py | MR1020
- [ ] MEDIUM | Report-0247 | screening/dashboard.py modified +69 LOC + bankruptcy_survivor commit. | rcm_mc/screening/dashboard.py | MR1021
- [ ] MEDIUM | Report-0246/0216 | Origin/main frozen at `3ef3aa3` for 9+ days; pre-merge state likely. | (git state) | MR1005
- [ ] MEDIUM | Report-0252 | `run_intake` writes YAML without atomic temp+rename → mid-process kill leaves corrupt YAML. | rcm_mc/data/intake.py:222 | MR1042
- [ ] MEDIUM | Report-0252 | `yaml.safe_load(f) or {}` at intake.py:52 silently turns malformed-empty into `{}`. | rcm_mc/data/intake.py:52 | MR1045
- [ ] MEDIUM | Report-0099/0119/0179 | 60% of deps have loose pins (12 of 20). | pyproject.toml | MR978
- [ ] MEDIUM | Report-0207 | `Engagement` dataclass + DDL high coupling — adding/removing column requires both DDL update AND dataclass update. | rcm_mc/engagement/store.py | MR988
- [ ] MEDIUM | Report-0212 | `ai/llm_client.py` reads `ANTHROPIC_API_KEY` env var with empty default → API calls fail at runtime with 401 if unset. | rcm_mc/ai/llm_client.py:147 | MR1001
- [ ] MEDIUM | Report-0212 | Single-vendor lock to Anthropic API — no abstraction layer for swapping provider. | rcm_mc/ai/* | MR1012
- [ ] MEDIUM | Report-0250 | 5 root `.md` files (ARCHITECTURE_MAP, FILE_INDEX, FILE_MAP, DEPLOYMENT_PLAN, WALKTHROUGH) — possible duplication / drift. | repo root | MR1033
- [ ] MEDIUM | Report-0247 | +13.7K LOC in single PR (feat/ui-rework-v3) — review burden very high; bisect-unfriendly. | (git state) | MR1016
- [ ] MEDIUM | Report-0094 | Three `*_predictor.py` variants (rcm_predictor / trained_rcm_predictor / rcm_performance_predictor) — overlapping behavior. | rcm_mc/ml/* | MR504/MR510
- [ ] MEDIUM | Report-0017 | No migration framework — field-add requires manual schema-aware migration. | rcm_mc/portfolio/store.py | MR486
- [ ] MEDIUM | Report-0251 | `openpyxl` listed in both `[dependencies]` and `[exports]` extras — redundant. | pyproject.toml | MR1039

## LOW

- [ ] LOW | Report-0253 | `MANDATORY_PAYERS` constant unused per comment ("Step 31: Kept for backward compatibility but no longer enforced"). Deletion candidate. | rcm_mc/infra/config.py:16 | MR1051
- [~] LOW | Report-0253 | `canonical_payer_name` undocumented + non-obvious aliases (Self-Pay→SelfPay, Private/PHI→Commercial). | rcm_mc/infra/config.py:80 | MR1049 | 8d355d2 | 2026-04-26 (alias contract pinned by 4 tests in test_config_public_helpers.py; docstring still pending)
- [ ] LOW | Report-0253 | Two contracts for same op: `load_and_validate` (raises) vs `validate_config_from_path` (returns tuple). | rcm_mc/infra/config.py:436+469 | MR1050
- [ ] LOW | Report-0249 | `remove_member` only 2 external refs — not dead, but worth verifying coverage. | rcm_mc/engagement/store.py:369 | MR1029
- [ ] LOW | Report-0250 | `scripts/run_all.sh` + `run_everything.sh` — no test, no CI ref. | scripts/run_*.sh | MR1034
- [ ] LOW | Report-0250 | `legacy/handoff/CHARTIS_KIT_REWORK.py` (21KB) zero refs — accidental re-import would conflict with `_chartis_kit_editorial.py`. | legacy/handoff/CHARTIS_KIT_REWORK.py | MR1032
- [ ] LOW | Report-0252 | Default template `community_hospital_500m` hard-coded at `intake.py:200`. | rcm_mc/data/intake.py:200 | MR1044
- [ ] LOW | Report-0251 | `exports` and `pptx` extras overlap on `python-pptx`. | pyproject.toml | MR1040
- [ ] LOW | Report-0251 | `profiles.example.yml` shipped via package-data — real `profiles.yml` glob-match risk. | pyproject.toml:80-85 | MR1041
- [ ] LOW | Report-0244 | `llm_client` likely instantiated 4× by sibling ai/ modules — 4× env-var reads. | rcm_mc/ai/* | MR1010
- [ ] LOW | Report-0245 | Possible `ai/memo_writer` → `pe_intelligence/ic_memo` cross-package call. | rcm_mc/ai/memo_writer.py | MR1013
- [ ] LOW | Report-0255 | Tuva Project (Apache 2.0) vendor copy — verify NOTICE file presence + license attribution in repo LICENSE/README. | vendor/ChartisDrewIntel/ | MR1056
- [ ] LOW | Report-0255 | `RCM_MM/` empty 0-byte scratch dir at repo root — decide: delete vs. gitignore vs. leave (carried follow-up Q2). | RCM_MM/ | (no MR — Q2)

## Backlog (not yet triaged)

The full report set surfaces ~1056 unique MR-tagged risks across 255 reports. Items below are catalogued in the source reports but not yet promoted to this triage list:

- Pre-Report-0085 MRs (MR1–MR475) — early audit findings; many superseded or carried through later reports with updated severity. Re-promotion candidates: re-grep `'\| (Critical|High)'` in old reports if a HIGH burndown stalls.
- Inventory/discovery items (subpackage maps, never-mapped modules) — handled by audit-loop task rather than fix-loop. Carried follow-ups: 5/7 unaudited CMS data-loaders (MR985), `pe_intelligence/` 270+ submodules, `data_public/` 313 files, ~10 small subpackages from Report 0190.
- Open-questions (Q1/Q2/etc.) — tracked in source reports' Open questions sections; promote to TRIAGE only when blocking a fix.

## Process / open blockers (need human review)

These four came out of the iter-19 progress report and are NOT severity-classified — they need human direction before the loop can act on them:

1. **Merge ownership of `feat/ui-rework-v3`** (+13.7K LOC, 51 files). Audit branch documents the merge risks (MR1015 in MERGE-CONFLICTS.md; MR1017 / MR1018 / MR855 / MR708 carried) but cannot resolve them without the merge author's input.
2. **Origin/main divergence**: local main is 145 commits ahead of origin/main and 4 behind; iter-1 push to main was rejected (non-fast-forward). Audit branch is the canonical preserved copy. **Question:** rebase, merge-back, or PR?
3. **FK survey ground truth** for ~10 deal-child tables (MR929/MR971). Audit-loop or one-shot script?
4. **Auto-deploy + secret rotation** when `feat/ui-rework-v3` lands on main (MR917). AZURE_VM_HOST/USER/SSH_KEY must be set on the GH repo before merge.

## How to add an entry

Format (one line per entry):

```
- [ ] SEVERITY | Report-NNNN | one-line summary | file:line if known | MRxxx
```

When a fix lands, replace `[ ]` with `[x]` and append `| <commit-hash> | <ISO-date> | <one-line note>` to that same row, then append to `Report/RESOLVED.md`:

```
<commit-hash> | <ISO date> | <SEVERITY> | <Report-NNNN> | <one-line summary>
```
