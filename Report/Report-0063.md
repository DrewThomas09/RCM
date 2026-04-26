# Report 0063: Key File — `auth/audit_log.py` (192 lines)

## Scope

Reads `auth/audit_log.py` end-to-end. Resolves Report 0062 Q1 + Reports 0021 Q1 / 0024 Q1 / 0030 Q3.

## Findings

### Module shape

192 lines. 6 public/private functions:

| Line | Function |
|---|---|
| 30 | `_iso(dt)` — private |
| 34 | `_utcnow()` — private |
| 38 | `_ensure_table(store)` — private |
| 79 | **`log_event(store, *, actor, action, target, detail=None) -> int`** |
| 113 | **`list_events(store, *, since, actor, action, limit=200) -> pd.DataFrame`** |
| 166 | **`cleanup_old_events(...)`** |
| 187 | **`event_count(store) -> int`** |

**4 public functions + 3 private.**

### Schema (line 41-51)

```sql
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT NOT NULL DEFAULT '',
    detail_json TEXT NOT NULL DEFAULT '{}',
    request_id TEXT
);
```

7 columns. **`request_id` was added via migration `audit_events_request_id`** (per Report 0017 migrations registry).

### Append-only design

Module docstring (line 9-12): "Append-only by design: audit rows are never updated or deleted in normal operation. A bug in a handler should never silently mutate history."

But `cleanup_old_events` (line 166) DOES delete — limited to "old" rows. **Append-and-cleanup, not strict append-only.**

### Trust contract

This module records security events. Per the docstring (line 1-7): "answering 'show me everything AT did Monday' required querying each one. This module adds a single append-only `audit_events` table the server writes to from every sensitive handler."

**This is the security-event trail.** Cross-link Report 0021 MR163 (auth.py has 0 logger calls): the answer is **`audit_log.log_event` is the canonical audit-channel** — failed logins SHOULD be recorded here.

But Report 0021 didn't find any `log_event` call inside `auth.py`. **Need to verify whether the calling site is in `server.py`'s auth-gate handler instead.**

### Public-API completeness

| Function | Args | Returns |
|---|---|---|
| `log_event` | actor, action, target, detail | int (the event id) |
| `list_events` | since, actor, action, limit=200 | DataFrame |
| `cleanup_old_events` | (per signature line 166) | int (count removed) |
| `event_count` | store | int |

**Clean API.** All 4 functions documented per the module docstring.

### Cross-link to compliance

Per Report 0028 / 0030, `compliance/audit_chain.py` is described as "adds a SHA-256 chain to the existing `audit_events` table so any after-the-fact deletion or mutation is cryptographically detectable." So `audit_log.audit_events` is the foundation; `compliance/audit_chain` adds tamper-evidence.

### `cleanup_old_events` tension

Line 166 contradicts the "append-only" docstring. Acceptable for table-size management (limit retention), but **the existence of cleanup means audit-deletion is by-design**. A malicious actor who can call `cleanup_old_events` can erase audit history. **Pre-merge: confirm only admins reach this function.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR425** | **`cleanup_old_events` permits deletion despite "append-only" claim** | Cross-link `compliance/audit_chain.py` for tamper-evidence. Without the chain, an attacker who reaches this function erases history. | **High** |
| **MR426** | **`audit_log` referenced from `auth/auth.py` — but Report 0021 found 0 logger calls** | Need to verify failed-login audit-event recording. Likely lives in server.py auth-gate, NOT auth.py. | **High** |
| **MR427** | **`detail_json` is plaintext SQLite** | If detail contains sensitive context (e.g. failed-login attempted-username), it's leaked to anyone with DB read access. Cross-link Report 0021 MR165 + Report 0028. | Medium |
| **MR428** | **No `actor` validation** | Any caller can `log_event(..., actor="root", ...)` and forge a record. Combined with MR425 (cleanup), audit integrity is weak without `audit_chain`. | **High** |
| **MR429** | **List-events query lacks ACL** | `list_events(...)` — anyone who can call this reads all audit history. Sensitive PII / actor names exposed. **Should require admin role.** | Medium |

## Dependencies

- **Incoming:** server.py (every handler that records actions), auth.py (likely), `compliance/audit_chain.py` (extends).
- **Outgoing:** stdlib (`json`, `datetime`), `pandas`, `portfolio.store`.

## Open questions / Unknowns

- **Q1.** Where is `log_event` called from in production? Need cross-grep.
- **Q2.** Does `auth.py` (any of its functions) call `log_event`?
- **Q3.** Does `compliance/audit_chain.py:append_chained_event` wrap `log_event` or replace it?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0064** | Incoming dep graph (already requested) — pick `audit_log`. |
| **0065** | Outgoing dep graph (already requested). |
| **0066** | Branch audit (already requested). |
| **0067** | Merge risk scan (already requested). |

---

Report/Report-0063.md written.

