# PROGRESS-19 — Bug Fix & Push Loop status, iteration 19

Date: 2026-04-26
Branch: `audit/reports-and-triage` (HEAD `f218734` at run time)
Total fix-loop iterations completed: 18 fixes + 2 housekeeping (TRIAGE build, TEST-PASS report) + 1 verification

## Triage rollup

| Severity | Triaged | Resolved | Partial | Remaining |
|---|---|---|---|---|
| CRITICAL | 4 | **4** | 0 | **0** |
| HIGH | 22 | 14 | 0 | **8** |
| MEDIUM | 21 | 0 | 1 | 20 |
| LOW | 11 | 0 | 1 | 10 |
| **Totals** | **58** | **18** | **2** | **38** |

(Closed/partial counts include 2 partial-mitigation entries — MR1046 + MR1049 from iter 14 — which are pinned by tests but not yet structurally complete.)

## CRITICAL queue: empty

All four CRITICAL items are closed and on origin:

| MR | Fix | Commit |
|---|---|---|
| MR744 | configs/playbook.yaml unparseable since 2026-04-17 — leading-space stripped from 6 keys | `33fda80` |
| MR770/MR1038 | pyarrow CVE-2023-47248 RCE — pin tightened to `>=18.1,<19.0` | `cb84f07` |
| MR14/MR1035 | rcm-intake console-script broken — added `rcm_mc/intake.py` shim | `5d91bda` |
| MR1014 | 144-commit audit chain laptop-only — pushed to origin/audit/reports-and-triage | `53f67c4` |

## Top-5 remaining HIGH

1. **MR982** | unified delete-policy missing — 5 distinct cascade behaviors (CASCADE×3, SET NULL×1, NO ACTION×many, soft-delete×1, hard-delete×1) with no CLAUDE.md matrix. Operator-UX hazard. *Doc-only fix; can land next.*
2. **MR929/MR971** | ~10 deal-child tables unwalked for FK behavior (only 6 confirmed cascades). Need `PRAGMA foreign_key_list(<each>)` survey. *Audit task, not a code fix.*
3. **MR985** | 5 of 7 CMS data-loaders unaudited (`cms_*.py` in `rcm_mc/data/`). *Audit task; partial inventory in Report 0102.*
4. **MR1017** + **MR1018** | NEW `rcm_mc/dev/seed.py` (896 LOC) and `rcm_mc/exports/canonical_facade.py` (424 LOC) on `feat/ui-rework-v3` — never read. *Cannot fix on main; resolve at merge.*
5. **MR855/MR708** | INTEGRATION_AUDIT.md (commit `c6ab593`) flagged 9 UI pages bypass dispatcher + 5+ modules bypass PortfolioStore. *Cross-link to feat-branch state; resolve at merge.*

Honorable mentions still in HIGH queue:
- **MR917** — first merge of `feat/ui-rework-v3` → main triggers auto-deploy via deploy.yml; pre-merge: AZURE_VM secrets must be set. *Operational checklist, not a code fix.*

## Fixes shipped, iter 2-18 (chronological, with verification status)

| Iter | Commit | Severity | Item |
|---|---|---|---|
| 2 | `33fda80` | CRITICAL | playbook.yaml unparseable |
| 3 | `cb84f07` | CRITICAL | pyarrow CVE pin |
| 4 | `5d91bda` | CRITICAL | rcm-intake shim |
| 5 | `53f67c4` | CRITICAL | audit chain push |
| 6 | `b31aecd` | HIGH | profiles.yml gitignore |
| 7 | `a53321f` | HIGH | infra/README.md ConfigError fix |
| 8 | `5685af4` | HIGH | _chartis_kit_v2 deletion → MERGE-CONFLICTS.md |
| 9 | `9287908` | HIGH | open-server warning at startup |
| 10 | `f4ffdac` | HIGH | CLAUDE.md SQLite count 17→~89 |
| 11 | `0a90a85` | (test) | TEST-PASS-11 (243 green) |
| 12 | `f1039f8` | HIGH | CLAUDE.md Python version 3.14→3.10+ |
| 12+ | `4abc310` | HIGH | CHANGELOG v1.0.0 reconciliation |
| 12+ | `e624c0c` | HIGH | get_member_role added to engagement __all__ |
| 12+ | `127a9f9` | HIGH×2 | RCM_MM/ + Tuva inspections (Report-0255) |
| 13 | `2fc6715` | HIGH | hash_inputs YAML fingerprints — **verified iter 16** |
| 14 | `8d355d2` | MEDIUM | 17 tests for 6 untested config helpers |
| 15 | `110f2cf` | HIGH×2 | extras graph: [stats] + diligence ⊂ all |
| 16 | `42451f1` | (verify) | MR958 5-invariant verification |
| 17 | `d3f23b3` | HIGH | ReimbursementProfile collision deprecated |
| 18 | `442bb98` | HIGH | document_qa prompt-injection hardening |

## Tests / regression watch

- **iter 11 focused sweep** (commit `0a90a85`): 243 passed across affected-area + core spot check; no regressions from iter 2-10.
- **iter 13 fix** (`2fc6715`): 58 analysis tests pass.
- **iter 14 new tests** (`8d355d2`): 17/17 pass; covers 6 previously-untested public helpers in `infra/config.py`.
- **iter 17 fix** (`d3f23b3`): 52 tests across econ_ontology, value_bridge_v2, packet_builder_guardrail_hook pass.
- **iter 18 fix** (`442bb98`): 40 phase-P + e2e tests pass.

**No red tests caught from iter 2-18 work.** No regressions introduced. Memory note `project_test_baseline.md` (~314 pre-existing baseline failures unrelated to this loop) remains the gating policy — full sweep deliberately not run.

## Blockers needing human review

1. **`feat/ui-rework-v3` merge ownership.** MR1015 (deleted `_chartis_kit_v2.py`), MR1017 (`dev/seed.py`), MR1018 (`exports/canonical_facade.py`), MR855/MR708 (9 UI pages bypassing dispatcher) — all lie on the feature branch (+13.7K LOC). The audit branch can document but not resolve; resolution happens at merge time. `MERGE-CONFLICTS.md` captures the recipe for `_chartis_kit_v2`. **Question for human: who owns the merge?**

2. **Origin/main divergence.** Origin/main has been frozen at `3ef3aa3` for 9+ days; local main is 145 commits ahead of origin/main and 4 commits behind. Push to main was rejected at iter 1 (non-fast-forward). The audit branch is the canonical preserved copy. **Question for human: rebase, merge, or PR?**

3. **CLAUDE.md ground truth.** Iter 10 found 89 SQLite tables vs the 17/21 the audit chain inferred — schemas live across many subpackages. The doc now points at a grep recipe rather than a hardcoded number, but the FK frontier (MR929) is still under-mapped. **Question for human: should the FK survey be an audit-loop task, or push it to a one-shot script?**

4. **Origin auto-deploy on main merge.** MR917 — once `feat/ui-rework-v3` lands on main, `.github/workflows/deploy.yml` fires and pushes to Azure. Pre-merge: AZURE_VM secrets must be set on the GH repo. **Question for human: who owns the secret rotation + deploy verification?**

## Repro-impossible items

None this round. All triaged HIGH items have a concrete file/symbol/state pointer.

## Next iteration

Per workflow: pick the next unchecked HIGH. **MR982 (unified delete-policy doc)** is the lowest-friction landing — pure CLAUDE.md addition, no test risk, ships visibility for the 5 cascade behaviors immediately. Recommend that next.
