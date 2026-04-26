# Report 0091: Kickoff/Resume — 90-Report Status

## Scope

Meta-survey after 90 reports. Sister to Reports 0001 (kickoff), 0031 (30-report), 0061 (60-report).

## Findings

### Reports inventory

90 reports written. Window-by-window:

- 0001-0030: foundation + repo + core deps + first cross-cuts
- 0031-0060: depth into infra/, analysis/, packet, calibration cross-link
- 0061-0090: deep into auth/, audit_log, session timeout, rate_limit, schema/type traces

### Coverage by domain (refresh)

| Domain | Recent reports |
|---|---|
| Repo structure | 0001, 0002, 0010, 0032, 0040 |
| Branches | 0006, 0007, 0036, 0037, 0066, 0067 |
| Build/CI/CD | 0003, 0023, 0026, 0033, 0041, 0046, 0053, 0056, 0071, 0083, 0086 |
| Tests | 0008, 0026, 0038, 0068 |
| Logging/errors | 0020, 0024, 0050, 0080 |
| Security | 0021, 0028, 0030, 0043, 0051, 0072, 0081 |
| Database/SQLite | 0008, 0017, 0047, 0077, 0087 |
| Configuration | 0011, 0019, 0027, 0028, 0042, 0049, 0058, 0079, 0088, 0090 |
| Server/HTTP | 0005, 0018, 0019, 0048, 0078 |
| External integrations | 0025, 0042, 0049, 0050, 0051, 0055, 0085 |
| Dependencies | 0003, 0016, 0023, 0046, 0053, 0076, 0083 |
| Documentation | 0014, 0029, 0030, 0044, 0059, 0074, 0089 |
| Cross-cuts | 0024, 0054, 0084 |
| Schema | 0027, 0057, 0077, 0087 |
| Compliance/PHI | 0028, 0030, 0043, 0056, 0072 |
| Auth subsystem | 0021, 0062, 0063, 0064, 0065, 0068, 0069, 0072, 0073, 0074, 0075, 0084, 0090 |
| Dead code / orphans | 0009, 0010, 0039, 0040, 0069, 0070 |
| Circular imports | 0022, 0052, 0082 |

### Most-covered subsystem: `auth/`

13 reports touch auth/. Per Reports 0062, 0063, 0064, 0065, 0090: `auth/audit_log.py` and `auth/auth.py` deeply mapped. **Still unmapped:** `auth/rbac.py` and `auth/external_users.py` end-to-end (placeholders only — Reports 0073, 0074).

### Still unmapped — highest-priority

Cross-referenced against prior meta-surveys (Report 0061 list) plus new debt:

1. **`cli.py` (1,252 lines)** — owed since Report 0003. Never read.
2. **`rcm_mc/diligence/` interior** — only orphan-list-level (Report 0040). 40 subdirs unmapped.
3. **`rcm_mc/data_public/` interior** — 313 files. Only J2 module mapped.
4. **`rcm_mc/ml/` subpackage** — never touched.
5. **`core/simulator.py` interior** — only test-coverage + dead-code at edges.
6. **`pe/breakdowns.py`** — Report 0044 doc-gap only; never read line-by-line.
7. **`compliance/audit_chain.py`** — Report 0082 noted clean DAG; never read body.
8. **`infra/webhooks.py`** — placeholder report only (Report 0055).
9. **`auth/rbac.py` (61 lines)** + **`auth/external_users.py` (89 lines)** — placeholders.
10. **`server.py` ≈ 11K lines** — only routes, env-vars, and entry points covered. Most handlers unread.
11. **22+ SQLite tables** beyond `deals`, `runs`, `analysis_runs`, `audit_events` — never schema-walked.
12. **7 of 14 origin branches** — Reports 0006/0007/0037/0066 mapped only `feature/deals-corpus` + `feature/workbench-corpus-polish` deeply. Others only listed.
13. **Tests directory** — Report 0008 + Report 0038 + Report 0068 sampled three modules. ~280+ test files unmapped.
14. **`pyproject.toml` exact `[project.scripts]` block** — Report 0086 inferred but did not extract.

### Merge-risk count

**~501 merge risks** flagged (MR1..MR501). Per Reports 0090 + 0089:
- 0001-0421: per Report 0061 estimate
- 0421-0501: 80 new risks across Reports 0061-0090

### Cross-corrections (since Report 0061)

- **Report 0090 retracted Report 0088 MR488** — absolute 7-day session TTL DOES exist.
- **Report 0090 cross-corrected Report 0027** — ServerConfig has 5 fields, not the implied larger set.
- **Report 0089 confirmed origin frozen** since `f3f7e7f` (2026-04-25).

### Audit-vs-remediation gap (still open from Report 0061 Q1)

Per Report 0089: 100% of last 50 commits are audit. Zero risks fixed. **The audit is producing risks faster than the project is closing them — same observation as Report 0061, now stronger.**

## Merge risks flagged

No new risks in this meta-survey.

## Dependencies

- **Incoming:** all future iterations.
- **Outgoing:** Reports 0001-0090.

## Open questions / Unknowns

Carried forward from Report 0061 Q1 + new this round:

- **Q1.** When (if ever) will any of the 501 flagged risks be remediated? (Carried from 0061.)
- **Q2.** Is `Report/` going to remain local-only, or be pushed to origin? (Carried from Report 0089.)
- **Q3.** When the 1,500-iteration audit completes (~iteration 1,500), what artifact is produced? Single PDF? GitBook? Index file?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0092** | Map next directory (the queue per task-rotation). |
| **0093** | Map next key file — pick `cli.py` head (close 14-iteration debt from Report 0003). |
| **0094** | Branch register refresh #3 (per Report 0089 + Report 0066). |
| **0095** | Read `create_session` body (per Report 0090 Q2). |

---

Report/Report-0091.md written.
Next iteration should: MAP NEXT DIRECTORY — pick `rcm_mc/ml/` (entirely unmapped subpackage).
