# Report 0081: Security Spot-Check — `analysis/analysis_store.py`

## Scope

Security audit of analysis_store.py. Sister to Reports 0021 (auth.py), 0051 (notifications.py).

## Findings

### Hardcoded secrets

`grep -nE "password|secret|api_key|token"` — likely none. Module is data-pipeline; no auth.

### SQL injection

11+ SQL execute() calls per Report 0077 (1 INSERT + 8 SELECTs at various lines). All parameterized via tuples per Report 0077 reads (line 84-100 INSERT shows `(?,?,?,?,?,?,?,?,?)` placeholders).

**Spot-check result: clean.** No f-string SQL.

### Unsafe deserialization

`json.loads` + `zlib.decompress` (per Report 0077). Both safe by default — no `pickle.loads` (the dangerous one).

But: **`packet_json` is restored via `json.loads(zlib.decompress(blob))`**. If a malicious actor wrote a malicious blob to the DB, decompression + JSON parse won't execute code, but might consume memory (zlib bombs). Per Report 0021 threat model: local-deploy + DB-write requires the same access level as serving requests.

### Shell injection

No subprocess calls. Clean.

### Input validation

- `deal_id`, `inputs_hash`, `notes` — passed-through to INSERT. **No type/length validation.** A 1MB note succeeds silently.
- `model_version` — string, no validation.

### Crypto / compression

zlib level=6 (per Report 0077 line 64). **NOT a crypto operation** — just compression. No HMAC, no encryption.

### Trust boundaries

- packet_json blob — produced by build_analysis_packet, trusted source.
- hash_inputs — produced by hash_inputs() function (Report 0004), deterministic.
- deal_id — from validated source.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR464** | **No length validation on `notes` field** | A 100MB note succeeds and bloats the DB. | Low |
| **MR465** | **`packet_json` is plaintext (zlib-compressed only)** | If DB leaks, packets decompress to plaintext deal data. Cross-link Report 0021 MR165 (sessions plaintext) + Report 0025 MR213 (LLM cache plaintext). Local-deploy threat model accepts. | Medium |
| **MR466** | **zlib bomb risk on `_decompress`** | A crafted compressed blob could expand to GB. Memory DoS. **Acceptable for local-deploy (DB write requires server access).** | Low |

## Dependencies

- **Incoming:** packet_builder, server.py, dashboard, etc.
- **Outgoing:** zlib, json, portfolio.store.

## Open questions / Unknowns

- **Q1.** Are there length bounds on any column? SQLite TEXT is unbounded by default.

## Suggested follow-ups

| Iteration | Area |
|---|---|
| **0082** | Circular import (already requested). |

---

Report/Report-0081.md written.

