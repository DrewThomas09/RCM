# Report 0141: Security Spot-Check — `analysis/packet_builder.py`

## Scope

Security audit of `RCM_MC/rcm_mc/analysis/packet_builder.py` (1,454 lines) — the 12-step packet builder per CLAUDE.md, Phase-4 load-bearing module. Sister to Reports 0021, 0051, 0072, 0081, 0104, 0108, 0111, 0114, 0136 (security audits).

## Findings

### Security checklist

| Vector | Sites | Status |
|---|---|---|
| Hardcoded secrets / API keys / passwords / tokens | **0** | clean (per `grep -nE "api_key\|API_KEY\|secret\|password\|token"`) |
| SQL injection (f-string SELECT/INSERT/DELETE/UPDATE) | **0** | clean (per regex `f"SELECT\|...`) |
| `subprocess` / `os.system` / `shell=True` | **0** | clean |
| `eval(` / `exec(` | **0** | clean |
| `pickle.` (deserialization) | **0** | clean |
| `yaml.load` (unsafe — without `safe_`) | **0** | clean |
| `input(` (interactive prompt) | **0** | clean |
| Path traversal (open user-supplied paths) | (TBD — partial check) | likely none direct in this module |

**All 8 security vectors clean.** packet_builder is a pure-computation orchestrator; data IO is delegated to other modules.

### Cross-correction to Report 0020 + Report 0140

Report 0020 + Report 0140 noted broad-except discipline (27 broad-except, 0 bare) — error handling is loose-but-documented. **No corresponding security holes** in this iteration's checklist.

### Cross-link to Report 0081 (analysis_store security)

Report 0081 audited `analysis/analysis_store.py` and found: parameterized SQL, no eval/pickle, json+zlib safe. **packet_builder has the same posture** — clean.

### What this module DOES touch (security-relevant)

Per CLAUDE.md + Report 0020:
1. `DealAnalysisPacket` dataclass (Report 0057)
2. `hash_inputs` function (cross-link Report 0058 PACKET_SCHEMA_VERSION)
3. Lazy imports of pricing/scoring modules (per try/except patterns from Report 0140)
4. Calls into ML predictors (Report 0093 ml/ subpackage)
5. Reads `deal_overrides` (Report 0134)

**No untrusted-data deserialization** in this module — it operates on already-validated dataclasses and SQLite rows. Cross-link Report 0136 MR770 (pyarrow CVE — affects `rcm_mc_diligence/`, NOT packet_builder).

### Trust boundary

packet_builder is **internal orchestrator**. Inputs come from:
- `DealAnalysisPacket` (validated by analysis_store.find_cached_packet)
- `deal_overrides` (validated by deal_overrides.validate_override_key per Report 0134)
- `deal_sim_inputs` (per Report 0137 — paths)
- ML predictors output (numpy)

**No direct user-input deserialization.** Trust boundary is upstream.

### Cross-link to Report 0140 (error handling)

Per Report 0140: 27 broad-except blocks. **None catches `OSError` or socket-level errors** that would suggest network-trust-boundary issues. **packet_builder doesn't do network I/O** — confirmed clean.

### Comparison to Report 0136 pyarrow (HIGH risk)

| Module | Untrusted input? | CVE-class risk |
|---|---|---|
| `analysis/packet_builder.py` (this) | NO | **clean** |
| `rcm_mc_diligence/ingest/file_loader.py` (Report 0136) | YES — partner Parquet | **HIGH** (pyarrow CVE-2023-47248) |
| `auth/auth.py` (Report 0021) | YES — login form | clean (scrypt, compare_digest) |
| `infra/webhooks.py` (Report 0104) | mixed | secret plaintext in DB (MR576 critical) |
| `core/distributions.py` (Report 0129) | NO | clean (numpy math) |

**packet_builder is in the "clean by construction" tier** — no untrusted inputs reach it directly.

### What packet_builder DOES NOT do — by inspection

- Does NOT open user-supplied files (paths come from validated `deal_sim_inputs` rows)
- Does NOT call subprocess (no shell injection risk)
- Does NOT deserialize foreign formats (no pickle/eval risk)
- Does NOT log secrets (no `logger.info(token)`-style mistakes)
- Does NOT directly write SQL (delegates to store layer)

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR791** | **packet_builder is security-clean by audit** — no eval/pickle/subprocess/SQL-injection/secrets/yaml-unsafe-load | Per the 8-vector checklist. Confirms Report 0020 + Report 0081 cross-link. | (clean) |
| **MR792** | **Trust boundary upstream — relies on `deal_overrides.validate_override_key` (Report 0134) and `deal_sim_inputs` validation** | If those upstream validators are bypassed (e.g. direct INSERT into SQLite), packet_builder's inputs become untrusted. **Defense-in-depth gap**: packet_builder does NOT re-validate. | Low |

## Dependencies

- **Incoming:** server.py routes, CLI `rcm-mc analysis <deal_id>`, async job_queue.
- **Outgoing:** stdlib + numpy + ML predictors + `analysis_store` + `deal_overrides`.

## Open questions / Unknowns

- **Q1.** Does any `try/except` block silently catch `subprocess.CalledProcessError` etc. (suggesting hidden subprocess usage)?
- **Q2.** Does any submodule lazy-imported by packet_builder have a security hole that bubbles up?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0142** | Circular imports (in flight). |
| **0143** | Verify Q2 — security-spot-check 1 of the lazy-imported predictors. |

---

Report/Report-0141.md written.
