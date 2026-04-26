# Report 0151: Kickoff/Resume — 150-Report Status

## Scope

Meta-survey after 150 reports (151st report). Sister to Reports 0001 (kickoff), 0031, 0061, 0091, 0121. Window: Reports 0122-0150 (29 audit reports).

## Findings

### Headline numbers

- **Reports written**: 150 (`ls Report/ | wc -l = 151`)
- **Local main**: 1,234 commits, 137 ahead of origin/main
- **Origin/main**: `3ef3aa3` — unchanged since Report 0096
- **Net unique merge risks**: ~830 (~820 after retractions)
- **Tables schema-walked**: 15 of ~22+ in DB
- **Subpackages mapped**: ~20 of 54 (per Report 0101 inventory)
- **Backlog**: ~7 unidentified tables, ~30+ unmapped subpackages

### Major windowed findings (Reports 0122-0150)

| Report | Finding | Severity |
|---|---|---|
| 0122 | `rcm_mc_diligence/` separate package fully mapped (closes 13+ iter carry) | (closure) |
| 0123 | `infra/data_retention.py` mapped + Report 0087 audit_events cross-correction | (closure + correction) |
| 0124 | PortfolioStore: 237 importers; 5+ bypass via `sqlite3.connect` | **MR708 critical** |
| 0126 | `feat/ui-rework-v3` advanced 24→35 ahead, writes `generated_exports` | MR717 high |
| 0127 | feat/ui-rework-v3 merge risk scan: clean to merge, +2 routes, NEW PHI write site | MR720 high |
| 0130 | 6+ unmapped top-level entries (seekingchartis.py, demo.py, scripts/, tools/, scenarios/, readME/) | MR738 high |
| 0131 | **`configs/playbook.yaml` is unparseable YAML — 8+ days silent** | **MR744 critical** |
| 0132 | Idempotency-Key trace; downgrades Report 0108 MR607 | (correction) |
| 0133 | `generated_exports` schema-walk; SET NULL FK | (closure) |
| 0134 | `deal_overrides` schema-walk; **doc-discipline foil** | (closure + observation) |
| 0136 | **pyarrow CVE-2023-47248 RCE risk on user-uploaded Parquet** | **MR770 critical** |
| 0137 | `deal_sim_inputs` (last named-but-unwalked) + path-traversal risk | MR777 high |
| 0144 | No shared retry helper — 4 inconsistent strategies | MR800 high |
| 0145 | dbt-core integration: partner can write arbitrary SQL into models/ | MR805 high |
| 0146 | All 8 quality gates pre-commit-only; NONE in CI | **MR813 high** |
| 0147 | `users` + `sessions` schema-walk; **5th FK discovered** | MR817 high |
| 0148 | `analysis_runs` FK confirmed (CASCADE); FK frontier complete | (closure) |
| 0150 | `profiles.yml` NOT in gitignore; 8+ secret patterns missing | MR829-831 high |

**~14 high/critical findings in 30-iteration window.** Productivity sustained.

### Coverage by domain (refresh)

| Domain | Latest reports |
|---|---|
| Repo structure | 0001, 0091, 0101, 0121, 0130, 0151 |
| Branches | 0006, 0036, 0066, 0096, 0119, 0120, 0126, 0149 |
| Build/CI/CD | 0026, 0033, 0041, 0056, 0086, 0101, 0116, 0120, 0143, 0146 |
| Tests | 0008, 0026, 0038, 0068, 0098, 0128 |
| Logging/errors | 0020, 0024, 0050, 0080, 0110, 0111, 0140 |
| Security | 0021, 0028, 0030, 0043, 0051, 0072, 0081, 0104, 0108, 0111, 0114, 0136, 0141, 0145, 0150 |
| Database/SQLite | 0017, 0047, 0077, 0087, 0102, 0104, 0107, 0117, 0118, 0123, 0133, 0134, 0137, 0147, 0148 |
| Configuration | 0011, 0019, 0027, 0028, 0042, 0049, 0058, 0079, 0088, 0090, 0101, 0109, 0115, 0118, 0131, 0139, 0148 |
| Server/HTTP | 0005, 0018, 0019, 0048, 0078, 0102, 0108, 0114, 0132, 0138 |
| External integrations | 0025, 0042, 0049, 0050, 0051, 0055, 0085, 0102, 0104, 0115, 0136, 0145 |
| Dependencies | 0003, 0016, 0023, 0046, 0053, 0076, 0083, 0086, 0101, 0106, 0113, 0136, 0143 |
| Documentation | 0014, 0029, 0044, 0089, 0104, 0119, 0134, 0149 |
| Cross-cuts | 0024, 0054, 0084, 0114, 0144 |
| Schema | 0027, 0057, 0077, 0087, 0102, 0104, 0107, 0117, 0123, 0133, 0134, 0137, 0147, 0148 |
| Compliance/PHI | 0028, 0030, 0043, 0056, 0072 |
| Auth subsystem | 0021, 0062-0065, 0068, 0069, 0072-0075, 0084, 0090, 0108, 0114, 0147 |
| ML | 0092, 0093, 0094, 0095, 0098, 0099, 0112, 0129 |
| Dead code / orphans | 0009, 0010, 0039, 0040, 0069, 0070, 0099, 0100, 0105, 0129, 0130 |
| Circular imports | 0022, 0052, 0082, 0095, 0112, 0142 |
| Idempotency / Job queue | 0103, 0108, 0128, 0132 |
| CSRF | 0114 |
| Retries (cross-cut) | 0144 |
| FK frontier | 0117, 0133, 0134, 0137, 0147, 0148 (COMPLETE) |

### Net risk count

| Source | Risks |
|---|---|
| Reports 0001-0090 | ~501 (per Report 0091) |
| Reports 0091-0120 | +182 (per Report 0121) |
| Reports 0121-0150 | ~+150 estimated |
| **Total claimed** | **~833** |
| Retractions | 7 (MR475, 488, 543, 549, 550, 660, 673) + cross-corrections (487, 484, 678, 707) |
| **Net unique** | **~822** |

### Audit-vs-remediation

Per Report 0061 Q1, 0091, 0119, 0121, 0149: **~1.5% remediation rate stable.** Audit accumulates ~5 risks/report; closures ~0.4/report. Gap continues to widen.

### Schema inventory (15 of ~22+ tables)

| Table | Walked? |
|---|---|
| 1-12. (per Report 0137) | ✓ |
| 13. `users` | Report 0147 |
| 14. `sessions` | Report 0147 |
| 15. `analysis_runs` (re-walked) | Report 0148 |

**~7 unidentified.** Likely candidates: `csrf_log`, `idempotency_log`, `notification_configs`, `tags`, `notes`, `owners`, `deadlines`, `escalations`, `task_audit`, `prediction_events`/`outcome_events` (Report 0093 referenced).

### FK frontier (CLOSED per Report 0148)

5 FK constraints across 5 tables:
- CASCADE × 3: `analysis_runs`, `mc_simulation_runs`, `deal_overrides` (deal_id → deals)
- SET NULL × 1: `generated_exports` (deal_id → deals)
- NO ACTION × 1: `sessions` (username → users)

Cascade-policy heterogeneity per MR761/MR817: 3 distinct behaviors. **Project lacks documented FK policy.**

### Top-priority unmapped subpackages

Per Report 0121 + Report 0130:

1. **`cli.py` (1,252 lines)** — owed since Report 0003 (14+ iterations, NOW 19+)
2. **`pe_intelligence/`** — 276 modules per Report 0097
3. **`data_public/`** — 313 files per Report 0091
4. **`diligence/`** interior — 40 subdirs
5. **6-7 CMS data-loaders** — only `cms_hcris.py` audited (Report 0115)
6. **13 sibling subpackages from Report 0097**
7. **2 more from Report 0100**
8. **6 mostly-unmapped finance/ modules** (Report 0142 — only `reimbursement_engine.py` named, not deeply read)
9. **demo.py + tools/build_dep_graph.py + scripts/** (Report 0130)
10. **17-20 NEVER-mentioned subpackages** (per Report 0121 — `ai/`, `analytics/`, `causal/`, `engagement/`, `finance/` partial, `ic_memo/`, `intelligence/`, `irr_attribution/`, `negotiation/`, `portfolio_monitor/`, `portfolio_synergy/`, `screening/`, `site_neutral/`, `verticals/`)

**Backlog: ~30+ unmapped subpackages.**

### Cross-reference health

Closures via cross-iteration links:
- Carry-forwards in window: ~14 prior open Qs closed
- Cross-corrections in window: 7+ (MR475, 488, 543, 549, 550, 660, 673, 487, 484, 678, 707)

**Strong inter-report correctness pattern.** Audit self-corrects.

### Project state observations

- **Origin/main frozen at `3ef3aa3` for 6+ days** (since Apr 25 16:40)
- **`feat/ui-rework-v3` actively advancing** with 35+ commits per Report 0126
- **Local main 137 commits ahead** of origin/main
- **3-way divergence** at `f3f7e7f` (Report 0120 MR688 critical)
- **No remediation of any high/critical MR** observed in window — Reports 0144 MR800, 0146 MR813, 0150 MR829-831 all open

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR833** | **Audit chain has accumulated 137 unpushed commits** (was 115 at Report 0119, +22 in window) | Cross-link MR684 / MR493. Local-disk-only home for Report/. **No git remote backup.** | **High** (carried + escalated) |
| **MR834** | **Schema inventory: 15 walked + ~7 unidentified** | Per Report 0091 22+ tables. ~7 still in backlog. Suggests notification_configs, csrf_log, idempotency_log, prediction_events, outcome_events, etc. | Medium |
| **MR835** | **~30+ unmapped subpackages remain** in backlog | At ~1 per iteration (per Report 0121 estimate), 30+ iterations needed to drain. Backlog stable. | (advisory) |

## Dependencies

- **Incoming:** all future iterations.
- **Outgoing:** Reports 0001-0150.

## Open questions / Unknowns

Carried from prior meta-surveys:
- **Q1.** Audit-vs-remediation rate: ~1.5% stable. (Reports 0061, 0091, 0121.) When (if ever) will remediation start?
- **Q2.** Branch disposition (merge / rebase / separate-branch). (Report 0089.)
- **Q3.** Final artifact form when audit completes (PDF? GitBook? Index?). (Report 0091.)

New since Report 0121:
- **Q4.** Are the high/critical findings (MR744, MR770, MR813, MR829, MR831) being actively triaged?
- **Q5.** Does the audit-chain decision require coordination with `feat/ui-rework-v3` merge timing?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0152** | Read `cli.py` head (1,252 lines, owed since Report 0003 — NOW 19 iterations carry). |
| **0153** | Identify the remaining ~7 unmapped tables via repo-wide `grep "CREATE TABLE"`. |
| **0154** | Map `pe_intelligence/` head (276 modules — Report 0097 carried). |
| **0155** | Map next sibling subpackage from Report 0097's 13. |

---

Report/Report-0151.md written.
Next iteration should: read `cli.py` head — 1,252 lines, owed since Report 0003 (NOW 19 iterations of carry-forward).
