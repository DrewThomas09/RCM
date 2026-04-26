# Report 0062: `RCM_MC/rcm_mc/auth/` Directory Inventory

## Scope

Maps `RCM_MC/rcm_mc/auth/` (auth subsystem). Sister to Report 0021 (auth/auth.py security audit).

## Findings

### Inventory

| Path | Size | Lines | Purpose |
|---|---:|---:|---|
| `auth/README.md` | (small) | — | Subsystem README |
| `auth/__init__.py` | 1 line | 1 | Empty namespace marker |
| `auth/audit_log.py` | (size) | **192 lines** | Audit-log table + record_event(). Repeatedly deferred from Reports 0021 Q1, 0024 Q1, 0030 Q3. |
| `auth/auth.py` | 16 KB | 467 | Multi-user auth — Report 0021 covered this. scrypt + sessions + rbac. |
| `auth/external_users.py` | (size) | 89 | External-user mapping (likely SSO / IdP integration). Not yet read. |
| `auth/rbac.py` | (size) | 61 | Role-based access control. Not yet read. |

### File-count + line-count summary

5 Python files, **810 lines total**. Smallest substantive subsystem audited.

### Suspicious items

- **No `.DS_Store`, no tmp/bak files, no untracked binaries.** Clean.
- `auth/__init__.py` at 1 line — empty namespace. **No re-exports.** Consumers must `from rcm_mc.auth.auth import ...` explicitly. Different from `analysis/__init__.py` (re-exports 30 symbols per Report 0004).

### High-priority subsystem state (Report 0021 cross-link)

- `auth.py:467 lines` — security audit complete (Report 0021).
- `audit_log.py:192 lines` — **NEVER mapped end-to-end despite 4+ deferral references.**
- `external_users.py:89` — never mapped.
- `rbac.py:61` — never mapped.

### What this directory NOT contains

- No CSRF module — Report 0002 / 0021 noted CSRF lives elsewhere (likely `infra/`).
- No rate-limiter — `infra/rate_limit.py` per Report 0018.
- No 2FA — Report 0021 MR173.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR422** | **`auth/__init__.py` is empty namespace** | Different convention from `analysis/__init__.py`. **No central public API.** Adding new auth functions requires every caller to use the full path. | Low |
| **MR423** | **`audit_log.py` (192 lines) is the unmapped audit-trail core** | Repeatedly deferred. Pre-merge any branch that touches audit-event recording must understand this module. | **High** |
| **MR424** | **`rbac.py` (61 lines) is the access-control surface** | Tiny but security-critical. Untouched by audit. | **High** |

## Dependencies

- **Incoming:** server.py (auth gate), cli.py (`rcm-mc portfolio users create`), tests.
- **Outgoing:** stdlib (hashlib, hmac, secrets), `portfolio.store`, `infra.logger`.

## Open questions / Unknowns

- **Q1.** What does `audit_log.py:record_event` log + does it satisfy Report 0021 MR163 (no logger calls in auth.py)?
- **Q2.** Does `external_users.py` integrate with an external IdP (LDAP / SAML / OIDC)? Or is it a simpler external-username-mapping?
- **Q3.** What are the actual roles in `rbac.py`? Per Report 0021 only "admin" and "analyst" are exposed.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0063** | Map next key file (already requested) — pick `audit_log.py`. |
| **0064** | Incoming dep graph (already requested). |
| **0065** | Outgoing dep graph (already requested). |
| **0066** | Branch audit (already requested). |

---

Report/Report-0062.md written.

