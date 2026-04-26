# Report 0061: Kickoff/Resume — 60-Report Status

## Scope

Meta-survey after 60 reports. Sister to Report 0031.

## Findings

### Reports inventory

60 reports. Roughly:

- 0001-0010: Foundation (repo root, RCM_MC/, pyproject, packet.py, server.py outgoing, branches, workbench-corpus-polish merge risk, store coverage, lookup dead code, orphan files)
- 0011-0020: Config + data flow + dist API + docs gap + tech debt + pyyaml + deals table + serve trace + env vars + packet_builder errors
- 0021-0030: auth security + circular imports analysis + version drift + logging cross-cut + Anthropic API + CI/CD + ServerConfig schema + PHI mode + commits digest + PHI docs follow-up
- 0031-0040: meta-resume + deploy/ dir + Dockerfile + infra/config in/out + branch refresh + deals-corpus merge risk + simulator coverage + simulator dead code + diligence orphans
- 0041-0050: docker-compose config + DOMAIN flow + phi_scanner API + breakdowns docs + pe/ tech debt + numpy + runs table + python -m entry + notifications env + notifications errors
- 0051-0060: notifications security + infra/ cycles + pandas drift + caching cross-cut + webhooks placeholder + pre-commit + DealAnalysisPacket schema + PACKET_SCHEMA_VERSION trace + commits digest refresh + Q1 partial resolve

### Coverage by domain (updated)

| Domain | Reports |
|---|---|
| Repo structure | 0001, 0002, 0010, 0040, 0032 |
| Branches | 0006, 0007, 0036, 0037 |
| Build/CI/CD | 0003, 0023, 0026, 0033, 0041, 0046, 0053, 0056 |
| Tests | 0008, 0026, 0038 |
| Logging/errors | 0020, 0024, 0050 |
| Security | 0021, 0028, 0030, 0043, 0051 |
| Database/SQLite | 0008, 0017, 0047 |
| Configuration | 0011, 0012, 0019, 0027, 0028, 0041, 0042, 0049, 0058 |
| Server/HTTP | 0005, 0018, 0019, 0048 |
| External integrations | 0025, 0042, 0049, 0050, 0051, 0055 |
| Dependencies | 0003, 0016, 0023, 0046, 0053 |
| Documentation | 0014, 0029, 0030, 0044, 0059 |
| Cross-cuts | 0024, 0054 |
| Schema | 0027, 0057 |
| Compliance/PHI | 0028, 0030, 0043, 0056 |

### Still unmapped (highest-priority)

- `cli.py` (1252 lines) — owed since Report 0003
- `rcm_mc/diligence/` interior (40 subdirs)
- `rcm_mc/data_public/` interior (313 files)
- 7 of 8 ahead-of-main branches (only feature/deals-corpus + workbench-corpus-polish deeply audited)
- 22 sister SQLite tables beyond `deals` and `runs`
- `auth/audit_log.py` + `auth/external_users.py` + `auth/rbac.py`
- `core/simulator.py` interior (only coverage + dead code audited)
- `ml/` subpackage
- `infra/webhooks.py` (placeholder report only)

### Merge-risk count

**~421 merge risks** flagged (MR1..MR421). Estimated breakdown unchanged from Report 0031.

## Merge risks flagged

No new findings.

## Dependencies

- **Incoming:** all future iterations.
- **Outgoing:** Reports 0001-0060.

## Open questions / Unknowns

Repository's "is the audit useful?" check: ~421 risks, but only ~10 implemented or addressed in any commit. The audit is information-rich; remediation rate is 0.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0062** | Map next directory (already requested). |
| **0063** | Map next key file (already requested). |
| **0064** | Incoming dep graph (already requested). |
| **0065** | Outgoing dep graph (already requested). |

---

Report/Report-0061.md written.

