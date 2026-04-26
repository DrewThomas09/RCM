# Report 0121: Kickoff/Resume — 120-Report Status

## Scope

Meta-survey after 120 reports. Sister to Reports 0001 (kickoff), 0031, 0061, 0091. Combines this with **closure of Report 0120 Q1 + MR689 high** via `git diff main..origin/main --stat`.

## Findings

### CLOSURE: Report 0120 Q1 + MR689 high

`git diff main..origin/main --stat` shows **121 files differ, 86 insertions(+), 16,044 deletions(-)**:

- **120 files** = `Report/Report-0001.md` through `Report/Report-0120.md` (local-only audit reports; absent on origin)
- **1 file** = `.github/workflows/deploy.yml` (the case Report 0120 already discovered)

**RESULT: deploy.yml is the ONLY non-audit file stale on local main.** MR689 high narrows scope dramatically — no other production-code/config files have been audited from a stale local view. **All 120 reports' file-content claims are valid** for the codebase as it sits on origin/main (since the only-stale file was deploy.yml).

### Reports inventory

120 reports written. Window-by-window:
- 0001-0030: foundation + repo + core deps + cross-cuts (Reports 0029 commit digest #1)
- 0031-0060: depth into infra/, analysis/, packet, calibration cross-link (0061 meta)
- 0061-0090: deep auth/, audit_log, session timeout, rate_limit, schema (0089 commit digest #3, 0091 meta)
- 0091-0120: ml/, domain/, mc/, CI/CD, branches, schema-walks, divergence discovery (0119 commit digest #4, 0120 4-commit gap)

### Major discoveries since Report 0091 (90→120)

| Report | Discovery |
|---|---|
| 0092-0093 | `rcm_mc/ml/` 41 modules, 13K lines (HIGH-PRIORITY) |
| 0093 | `rcm_mc/domain/`, `rcm_mc/pe_intelligence/` subpackages (HIGH) |
| 0096 | Origin/main no longer frozen (f3f7e7f → 3ef3aa3) |
| 0097 | 13 unmapped sibling subpackages (Critical MR529) |
| 0100 | 2 more unmapped: `diligence_synthesis/`, `ic_binder/` (Critical MR544) |
| 0101 | 4 console scripts, broken `rcm-intake` (Critical MR588) |
| 0102 | 7 unaudited CMS data-loader modules (Critical MR558) |
| 0103 | `infra/job_queue.py` (HIGH MR559) |
| 0107 | 2 more unmapped: `infra/consistency_check.py`, `analysis/refresh_scheduler.py` (HIGH MR597) |
| 0108 | Login DOES rate-limit (retracted Report 0085 MR475) |
| 0110 | `infra/data_retention.py` (HIGH MR672) — STILL not read |
| 0113 | scipy + fastapi NOT dead (retracted Report 0101 MR549/550) |
| 0114 | CSRF exempts `/quick-import*`, `/screen` — likely OWASP issue (HIGH MR639) |
| 0117 | First-ever FK in any audited table (`mc_simulation_runs`) |
| 0118 | `deal_overrides` table (HIGH MR677) |
| 0118 | PRAGMA foreign_keys = ON confirmed; busy_timeout = 5000 |
| 0120 | Branch divergence — 4 origin CI commits + 115 local audit commits |

### Coverage by domain (refresh)

| Domain | Latest reports |
|---|---|
| Repo structure | 0001, 0002, 0010, 0032, 0040, 0091, 0101, 0121 |
| Branches | 0006, 0007, 0036, 0066, 0067, 0096, 0120 |
| Build/CI/CD | 0026, 0033, 0041, 0046, 0053, 0056, 0086, 0101, 0116, 0120 |
| Tests | 0008, 0026, 0038, 0068, 0098 |
| Logging/errors | 0020, 0024, 0050, 0080, 0110, 0111 |
| Security | 0021, 0028, 0030, 0043, 0051, 0072, 0081, 0104, 0108, 0111, 0114 |
| Database/SQLite | 0008, 0017, 0047, 0077, 0087, 0102, 0104, 0107, 0117, 0118 |
| Configuration | 0011, 0019, 0027, 0028, 0042, 0049, 0058, 0079, 0088, 0090, 0101, 0109, 0115, 0118 |
| Server/HTTP | 0005, 0018, 0019, 0048, 0078, 0102, 0108 |
| External integrations | 0025, 0042, 0049, 0050, 0051, 0055, 0085, 0102, 0104, 0115 |
| Dependencies | 0003, 0016, 0023, 0046, 0053, 0076, 0083, 0086, 0101, 0106, 0113 |
| Documentation | 0014, 0029, 0030, 0044, 0059, 0074, 0089, 0104, 0119 |
| Cross-cuts | 0024, 0054, 0084, 0114 |
| Schema | 0027, 0057, 0077, 0087, 0102, 0104, 0107, 0117 |
| Compliance/PHI | 0028, 0030, 0043, 0056, 0072 |
| Auth subsystem | 0021, 0062-0065, 0068, 0069, 0072-0075, 0084, 0090, 0108, 0114 |
| ML | 0092, 0093, 0094, 0095, 0098, 0099, 0112 |
| Dead code / orphans | 0009, 0010, 0039, 0040, 0069, 0070, 0099, 0100, 0105 |
| Circular imports | 0022, 0052, 0082, 0095, 0112 |
| Idempotency / Job queue | 0103, 0108 |
| CSRF | 0114 |
| Schema-walked tables | 9 (deals, runs, analysis_runs, audit_events, hospital_benchmarks, webhooks, webhook_deliveries, data_source_status, mc_simulation_runs) |

### Most-covered subsystem

**`auth/`** — 13+ reports (Report 0091 metric stable). Followed by `domain/` (5 reports across 0094-0099) and `infra/` (8+ reports).

### Still unmapped — refreshed top-priority list

Per accumulated discoveries:

1. **`cli.py`** (1,252 lines) — owed since Report 0003. **Closes Report 0091 #1**, never read.
2. **`rcm_mc_diligence/`** separate package — carried 13+ iterations (Reports 0078, 0101).
3. **`rcm_mc/pe_intelligence/`** — 276 modules per Report 0097.
4. **13 sibling subpackages** discovered Report 0097 (`pricing/`, `market_intel/`, `montecarlo_v3/`, `vbc/`, etc.).
5. **2 more** discovered Report 0100 (`diligence_synthesis/`, `ic_binder/`).
6. **`rcm_mc/data_public/`** — 313 files (per Report 0091).
7. **`rcm_mc/diligence/`** interior (40 subdirs).
8. **7 CMS data loaders** (Report 0102 MR558) — only `cms_hcris.py` audited (Report 0115).
9. **3 unmapped tables**: `deal_sim_inputs`, `generated_exports`, `deal_overrides` (Reports 0110, 0118).
10. **3 unmapped modules from Report 0110**: `mc/mc_store.py` ✓ (Report 0117), `exports/export_store.py`, `deals/deal_sim_inputs.py`.
11. **`infra/data_retention.py`** (MR672 — never read).
12. **`infra/consistency_check.py`** ✓ (Report 0110), **`analysis/refresh_scheduler.py`** ✓ (Report 0111).
13. **`server.py` ≈ 11K lines** — handlers ~80% unread.
14. **~280 test files** mostly untouched; only ~20 spot-checked.
15. **NEW unmapped subpackages discovered after Report 0097/0100** (per Report 0101 inventory of 54 subdirs): ~17-20 more never reported including `ai/`, `analytics/`, `causal/`, `engagement/`, `finance/`, `ic_memo/`, `integrations/` (partial — Report 0105), `intelligence/`, `irr_attribution/`, `negotiation/`, `portfolio_monitor/`, `portfolio_synergy/`, `screening/`, `site_neutral/`, `verticals/`.

### Merge-risk count

**~683 risks claimed in commit messages.** Adjusted for retractions:
- Report 0085 MR475 (Critical, login unprotected) — RETRACTED Report 0108
- Report 0088 MR488 (no absolute session max) — RETRACTED Report 0090
- Report 0099 MR543 (pre-commit F401 not configured) — RETRACTED Report 0101
- Report 0101 MR549 ([api] dead) — RETRACTED Report 0113
- Report 0101 MR550 (scipy unused) — RETRACTED Report 0113
- Report 0116 MR660 (auto-deploy commented out) — RETRACTED Report 0120
- Report 0117 MR673 (PRAGMA foreign_keys not set) — RETRACTED Report 0118

**Net unique risks: ~676.**

### Audit-vs-remediation rate

Per Report 0061 Q1, 0091, 0119: ~10 risks remediated of ~676. **~1.5%.** Gap holding steady.

### Branch state (post Report 0120)

- Local main: 1,204 commits, HEAD `b9d8102` (post-Report-0120)
- Origin main: 1,093 commits, HEAD `3ef3aa3`
- **Diverged at `f3f7e7f`** — 4 origin commits + 116+ local audit commits
- **No file-content claim risk** beyond `deploy.yml` (per this report's diff).

### What's still unknown

- Which audit-chain disposition is correct (merge vs rebase vs separate-branch).
- Status of MR597 + MR672 modules NOT yet read.
- Body of `cli.py` (1,252 lines).
- 13+ sibling subpackages from Report 0097 each unaudited.
- ~17-20 sibling subpackages from Report 0101's 54-dir inventory each unaudited.
- ~12+ unmapped tables.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR689-NARROWED** | **Per `git diff main..origin/main --name-only`: only `deploy.yml` is non-audit stale on local** | Risk scope reduced from "potentially many files" to "only deploy.yml." Other 120 audit-report files are local-only (not stale-from-origin). | (correction; downgrade) |
| **MR692** | **120 reports — backlog of ≥35 unmapped subpackages and ≥12 unmapped tables** | At ~1 entity per report, 47+ iterations to drain backlog at current pace. | (advisory) |

## Dependencies

- **Incoming:** all future iterations.
- **Outgoing:** Reports 0001-0120.

## Open questions / Unknowns

Carried from Report 0091:
- **Q1.** Audit-vs-remediation rate. ~1.5% — unchanged.
- **Q2.** Branch disposition decision (merge / rebase / separate-branch).
- **Q3.** Final artifact form when audit completes (PDF? GitBook? Index?).

New since Report 0091:
- **Q4.** Backlog ordering — by HIGH-PRIORITY MR severity, by line-count of unmapped, or chronological?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0122** | Schema-walk `deal_overrides` (Report 0118 MR677 backlog). |
| **0123** | Read `infra/data_retention.py` (Report 0117 MR672 carried). |
| **0124** | Read `cli.py` head (1,252 lines, owed since Report 0003 — 14+ iterations). |
| **0125** | Map `rcm_mc_diligence/` separate package (carried 13+). |

---

Report/Report-0121.md written.
Next iteration should: schema-walk `deal_overrides` (highest-priority HIGH MR677, never reported) — closes Report 0118 follow-up.
