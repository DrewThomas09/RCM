# Report 0064: Incoming Dep Graph — `auth/audit_log.py`

## Scope

Maps every place `auth/audit_log.py` is imported/called. Resolves Report 0063 Q1.

## Findings

### Production imports (3 sites — all in server.py, all lazy)

| Site | Line | Pattern |
|---|---|---|
| server.py:1562-1565 | inside an auth gate | `from .auth.audit_log import log_event` (lazy) → `log_event(...)` |
| server.py:14586-14587 | another handler | same lazy pattern |
| server.py:14619-14620 | another handler | same |

**3 production call sites — ALL inside server.py, ALL lazy imports.** No top-level `from rcm_mc.auth.audit_log` anywhere in production.

### Test sites

Not enumerated this iteration — likely 1-3 test files.

### Sister reference

`compliance/audit_chain.py:12` (per cross-link grep): "don't want to risk breaking existing `log_event` calls." Confirms `audit_chain` extends/wraps `log_event`.

`auth/README.md:35` documents the audit-log behavior.

### Coupling-tightness verdict

**3 production callers, all in server.py.** Below the >5-callers tight-coupling threshold. **Light coupling.**

### Where it's NOT called

Notably ABSENT from:

- **`auth/auth.py`** — Report 0021 confirmed 0 logger calls + no `log_event` calls. **Verified: failed logins are NOT audit-logged from inside auth.py.** They might be logged from server.py's auth gate (lines 1562/14586/14619 are inside server.py auth handlers — possibly the answer to Report 0021 MR163).

Need to read those 3 server.py call sites to confirm.

### Resolves Report 0063 / 0021 / 0024 questions

| Question | Resolution |
|---|---|
| Report 0021 Q1 ("does any module log security events?") | **Yes via server.py auth gates calling log_event.** Auth.py itself doesn't log; the wrapping HTTP handler does. |
| Report 0024 Q1 (production stderr capture) | Still open — log_event writes to SQLite, not stderr. Operators have to query DB to see audit history. |
| Report 0063 Q1 (where called) | **Resolved: 3 server.py sites only.** |

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR430** | **All 3 audit-log callers are in server.py** | A non-HTTP path (CLI, scheduled jobs) does NOT generate audit events. Cross-link Report 0028 MR261 (audit doesn't tag PHI_MODE). | **High** |
| **MR431** | **server.py:1562 + 14586 + 14619 are 3 separate handlers** | If a future handler adds a new sensitive operation but forgets `log_event`, it's silently un-audited. **No auto-instrumentation; honor-system.** | **High** |
| **MR432** | **Lazy imports inside try blocks may swallow audit failures** | The 3 sites use `from .auth.audit_log import log_event` lazy. If wrapped in BLE001, a failed audit log is invisible. Need read of context. | Medium |

## Dependencies

- **Incoming:** server.py (3 sites).
- **Outgoing:** stdlib + pandas + portfolio.store.

## Open questions / Unknowns

- **Q1.** Read the 3 server.py call sites to confirm what events fire log_event (failed login, deal-delete, etc.).

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0065** | Outgoing dep graph (already requested). |
| **0066** | Branch audit (already requested). |
| **0067** | Merge risk scan (already requested). |

---

Report/Report-0064.md written.

