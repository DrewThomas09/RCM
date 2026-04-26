# Report 0031: Kickoff / Resume — Audit-Loop Status After 30 Reports

## Scope

Meta-survey of what the audit loop has mapped and what is still unknown after 30 prior reports. `Report/` contains 30 entries (Reports 0001-0030) on `origin/main` at commit `f3f7e7f`. This report does not pick a new area — it inventories the corpus produced and the structural unknowns remaining.

Prior reports reviewed before writing: 0027-0030 (per the operating rules' "last 3-5 reports").

## Findings

### Reports produced (30)

| # | Title | Subject |
|---|---|---|
| 0001 | Repository Root Inventory | Top-level files + dirs |
| 0002 | RCM_MC/ Package Root | Depth-1 of the main package |
| 0003 | pyproject.toml | Dep + entry-point audit |
| 0004 | Incoming-dep graph for analysis/packet.py | + Discovery: rcm_mc/diligence/ + data_public/ on main |
| 0005 | Outgoing-dep graph for server.py | 526 internal modules imported |
| 0006 | Branch register (14 branches) | 1 trunk, 8 live, 5 dead |
| 0007 | Merge-risk scan: feature/workbench-corpus-polish | 3,336-file divergence, recommend cherry-pick |
| 0008 | Test-coverage on portfolio/store.py | Critical methods 1-test-only |
| 0009 | Dead code in data/lookup.py | 3 functions tested-but-unused |
| 0010 | Orphan files / subsystems | management/, portfolio_synergy/, site_neutral/, api.py, constants.py, lookup.py |
| 0011 | configs/actual.yaml — config map | 136 lines, schema, defaults, readers |
| 0012 | actual.yaml data-flow trace | CLI → loader → validator → simulator → disk |
| 0013 | Public API of core/distributions.py | 9 symbols, 8 dist shapes |
| 0014 | Documentation gap in management/ | thin docs but present |
| 0015 | Tech-debt marker sweep | 2 TODOs + 530 noqa suppressions (BLE001 dominant) |
| 0016 | pyyaml dependency audit | All safe_load, no security gaps |
| 0017 | deals SQLite table | 5 columns vs README's claim of 17, dual-tracked deletion |
| 0018 | rcm-mc serve entry-point trace | 5-layer trace |
| 0019 | server.py env vars + whole-repo inventory | 5 + 20 distinct vars |
| 0020 | Error handling in packet_builder.py | 100% logger.debug, silent failures |
| 0021 | Security spot-check on auth/auth.py | scrypt N below OWASP min, 0 logger calls |
| 0022 | Circular imports in analysis/ | Clean DAG, no cycles |
| 0023 | Version drift between pyproject + imports | pyarrow isolation violated, docx undeclared |
| 0024 | Logging cross-cut | 0 logger.exception, 63 silent debug calls |
| 0025 | Anthropic LLM API integration | Cache TTL claimed but not implemented |
| 0026 | Build/CI/CD audit | CI gates 4% of tests, deploy auto-trigger commented out |
| 0027 | ServerConfig schema | 5 fields, NOT @dataclass |
| 0028 | RCM_MC_PHI_MODE config-value trace | Banner is purely cosmetic, no enforcement |
| 0029 | Recent commits digest | Strong hygiene, doc-vs-code drift on PHI |
| 0030 | PHI docs follow-up | Refines MR250: gap is in banner text, not docs |

### Coverage by domain

| Domain | Reports covering | Coverage state |
|---|---|---|
| **Repo structure** | 0001, 0002 | depth ≤ 2 mapped; depth 3+ unknown for most subpackages |
| **Branches** | 0006, 0007 | 14 branches enumerated; 1 of 8 live branches deeply audited |
| **Build / packaging** | 0003, 0023, 0026 | pyproject + workflows + dep drift mapped |
| **Tests** | 0008 | One module's coverage audited; no full sweep; CI gate is 4% |
| **Logging / errors** | 0020, 0024 | Cross-cut + one module audited |
| **Security** | 0021, 0028, 0030 | Auth + PHI mapped; PHI banner gap surfaced |
| **Database / SQLite** | 0008, 0017 | One table fully audited; 22 sister tables not yet |
| **Configuration** | 0011, 0012, 0019, 0027, 0028 | actual.yaml + env vars + ServerConfig + PHI_MODE |
| **Server / HTTP** | 0005, 0018, 0019 | Outgoing imports + entry-point + env vars |
| **External integrations** | 0025 | Anthropic LLM mapped; SMTP / CMS data downloads owed |
| **Dependencies** | 0003, 0016, 0023 | pyproject + pyyaml audit + version drift |
| **Documentation** | 0014, 0029, 0030 | One module + commits + 2 PHI docs |

### What's NOT yet mapped (significant unknowns)

| Area | Why important |
|---|---|
| **`rcm_mc/diligence/` subsystem** (40 subdirs per Report 0004) | High-priority HIDDEN subsystem; only mentioned in 4 reports; never audited. INTEGRATION_MAP.md (17 KB) has been deferred 8+ times. |
| **`rcm_mc/data_public/` subsystem** (313 .py files per Report 0004) | Same — known to exist on main, never per-file mapped. Cross-link: parallel implementations vs feature/deals-corpus. |
| **`rcm_mc/cli.py` (1,252 lines)** | The user-facing CLI. Owed since Report 0003. |
| **`rcm_mc/server.py` per-route handlers** | 16,398 lines. Routes only sampled. |
| **`rcm_mc/ui/*` subsystem** | 351 lazy imports per Report 0005; only `_chartis_kit.py` partially read. |
| **`compliance/phi_scanner.py`** + `audit_chain.py` | Both repeatedly suggested as follow-ups (Reports 0021, 0028, 0030). |
| **`auth/audit_log.py`** | Sister to auth.py; promised since Report 0021 Q1. |
| **`auth/external_users.py`, `auth/rbac.py`** | Auth subsystem incomplete. |
| **`infra/` subsystem** (15+ files per Report 0019 inventory) | Only `logger.py`, `config.py`, `migrations.py` partially read. |
| **`pe/` subsystem** | 32 imports from server.py (Report 0005). Not audited. |
| **`ml/` subsystem** | 13 imports from server.py. Not audited. |
| **`core/simulator.py`** (entry at line 525, 601) | Mentioned 6+ times; never read. |
| **`core/calibration.py`** | YAML round-trip site (Report 0011); never audited. |
| **8 ahead-of-main branches** | 1 of 8 (workbench-corpus-polish) deeply audited; 7 untouched. |
| **CI tests in detail** | What does `test_full_pipeline_10_hospitals.py` actually verify? |
| **Deploy stack (`Dockerfile`, `docker-compose.yml`, `vm_setup.sh`, `Caddyfile`, `rcm-mc.service`)** | Owed 6+ times. |
| **22 sister SQLite tables** beyond `deals` (Report 0017) | runs, sessions, users, audit_events, etc. — schema unmapped. |
| **`vendor/ChartisDrewIntel/` DBT subproject** | 2,004 files in one commit (Report 0029). Treated as third-party. |
| **`legacy/heroku/` + `legacy/handoff/`** | Untouched. |
| **`tests/` directory at scale** (459 items per Report 0002) | Only `test_data_public_smoke.py` partially seen. |
| **External integrations beyond Anthropic** | SMTP (notifications.py), webhooks.py, CMS downloads (data/_cms_download.py, hcris.py, irs990.py, sec_edgar.py) — none audited. |

### Open-question count

Across 30 reports, the **Open Questions / Unknowns** sections enumerate ~205 questions. Many are still unresolved. Top recurring unresolved themes:

- Cross-branch sweeps (does branch X also do Y?) — every report needs this; never executed.
- Production runtime behavior (what does `infra/logger.py` actually emit at INFO?) — partially answered (Report 0024) but no production log sample inspected.
- HIPAA enforcement gap — surfaced (Report 0028) and refined (Report 0030); fix not yet implemented.
- 822-commit gap with `feature/deals-corpus` — Report 0006 flagged Critical (MR40); no merge prep in 50 commits since (Report 0029 MR273).

### Merge-risk count

The 30 reports collectively flag **279 merge risks** (MR1–MR279, with some sub-numbering — actual unique count is in this range). By severity (rough estimate):

- **Critical**: ~30
- **High**: ~110
- **Medium**: ~95
- **Low**: ~44

Top recurring critical risks:
- Branch-merge gap on `feature/deals-corpus` (MR40, MR43, MR273 — 3 reports)
- PHI banner enforcement (MR250, MR251, MR257, MR262, MR275)
- Hand-maintained schema lists (MR55, MR123, MR131)
- Workbench-corpus-polish destructive merge (MR44, MR45, MR47, MR225, MR237 — 5 reports)
- Pyarrow / docx dependency violations (MR183, MR184)

### Audit velocity

30 reports across iterations 1-30. Average iteration produces ~150-300 lines of report text + 8-15 new merge risks. **Sustainable cadence; no need to slow down.**

## Merge risks flagged

No new merge risks specific to this meta-report. All risks are inherited from the 30 covered reports. The advisory:

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR280** | **No master register of MR-IDs** | 279 merge risks scattered across 30 reports. **No single index.** Pre-merge planning requires walking every report. **Recommend: an `Report/INDEX_MERGE_RISKS.md` artifact**. | **High** |
| **MR281** | **No master register of resolved questions** | 205 Open Questions accumulated; some have been answered in subsequent reports (e.g. Report 0030 resolves Report 0028 Q3). **No "resolved" tracker.** | Medium |
| **MR282** | **Cross-branch sweeps repeatedly deferred** | Every merge-risk report assumes "ahead-of-main branches behave the same as main." This assumption has not been verified for any specific risk. **Risk amplification.** | **High** |

## Dependencies

- **Incoming:** every future audit iteration; any merge-planning effort.
- **Outgoing:** all 30 prior reports.

## Open questions / Unknowns

- **Q1 (this report).** Should the loop produce a master `INDEX.md` (cross-reference of all MR-IDs)? Decision needed.
- **Q2.** Of the ~205 open questions, how many have been silently resolved in later iterations vs are still genuinely open?
- **Q3.** What's the highest-priority unmapped area? Candidates: `rcm_mc/diligence/` (40-subdir subsystem), `rcm_mc/data_public/` (313 files), `cli.py` (1,252 lines, broken entry-point), or the deploy stack.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0032** | **Map `rcm_mc/deploy/` directory** (5 files: Caddyfile, Dockerfile, docker-compose.yml, rcm-mc.service, vm_setup.sh) | Owed since Reports 0023, 0026. Closes the deploy stack picture. |
| **0033** | **Read `RCM_MC/deploy/Dockerfile`** end-to-end | Sister to 0032. |
| **0034** | **Map `rcm_mc/diligence/INTEGRATION_MAP.md`** — owed 8 times since Report 0004. | The single most-deferred high-priority item. |
| **0035** | **Walk `rcm_mc/cli.py`** — owed since Report 0003. | The CLI surface; broken `rcm-intake` entry point unresolved. |
| **0036** | **Generate `Report/INDEX_MERGE_RISKS.md`** | Resolves Q1 / MR280. |

---

Report/Report-0031.md written. Next iteration should: map `RCM_MC/deploy/` (5 files: Caddyfile, Dockerfile, docker-compose.yml, rcm-mc.service, vm_setup.sh) — repeatedly deferred (Reports 0023, 0026, 0027, 0028) and is the missing piece of the deploy stack picture before any merge planning can land.

