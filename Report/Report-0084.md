# Report 0084: Cross-Cutting — Authentication

## Scope

Maps every authentication site. Sister to Reports 0024 (logging), 0054 (caching).

## Findings

### Auth surfaces

| Layer | Module | Function |
|---|---|---|
| Password storage | `auth/auth.py` (Report 0021) | scrypt hash via `_hash_password` |
| Password verify | `auth/auth.py:165 verify_password` | constant-time compare |
| Session create | `auth/auth.py:196 create_session` | secrets.token_urlsafe(32) |
| Session validate | `auth/auth.py:241 user_for_session` | with idle timeout |
| Session revoke | `auth/auth.py:318 revoke_session` | one-row DELETE |
| Session cleanup | `auth/auth.py:331 cleanup_expired_sessions` | bulk delete expired |
| HTTP Basic gate | `server.py:1668 onwards` (Report 0018) | reads RCMHandler.config.auth_user/pass |
| Session cookie auth | `server.py:1663` (Report 0018) | calls user_for_session |
| Auth-bypass paths | `server.py:1700` | `/health`, `/healthz`, `/login`, `/api/login` |
| Audit-event log | `server.py` 3 sites (Report 0064) | calls log_event for sensitive ops |
| RBAC | `auth/rbac.py` (Report 0073) | 61 lines — placeholder; not deeply read |
| External users | `auth/external_users.py` (Report 0074) | 89 lines — placeholder |
| Rate limit | `infra/rate_limit.py` (Report 0018 reference) | not yet audited |

### Inconsistencies

1. **Logger calls in auth/auth.py: 0** (Report 0021 MR163). Audit events recorded only via server.py wrappers (Report 0064).
2. **scrypt N=2^14 below OWASP minimum** (Report 0021 MR162). Pin to 2^15+ recommended.
3. **No 2FA / MFA / WebAuthn** (Report 0021 MR173). Single-factor.
4. **HTTP Basic auth + session cookies coexist** — two auth modes, both supported. Cross-link Report 0018 line 1668 (HTTP Basic) + 1663 (session cookie).
5. **`auth_user = ""` (empty string) bypass** — Report 0021 MR144, Report 0027 MR240. `is not None` passes; compare_digest fails. Unintended state.
6. **Audit-event recording only on HTTP path** (Report 0064 MR430) — CLI / scheduled jobs blind spot.
7. **Failed-login logging absent** from auth.py (recorded via server.py wrapper instead).

### Coverage by surface

| Surface | Report |
|---|---|
| auth.py | 0021 (security) |
| audit_log.py | 0063, 0064, 0072 |
| rbac.py | 0073 (placeholder) |
| external_users.py | 0074 (placeholder) |
| HTTP gate | 0018 |
| Session model | 0021 + 0017 (sessions table) |
| Rate limiter | NEVER directly audited |

**`infra/rate_limit.py` is the unaudited brute-force-resistance backstop.** Cross-link Report 0021 MR163.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR470** | **`infra/rate_limit.py` never audited** | The only counter-measure to brute-force without 2FA. If misconfigured = open door. | **Critical** |
| **MR471** | **Two auth modes (HTTP Basic + session cookies) cross-cuts** | A request can authenticate via either; both must be guarded uniformly. Pre-merge: confirm symmetric handling. | Medium |
| **MR472** | **`/health` + `/login` bypass paths hardcoded at server.py:1700** | Adding a new "always-public" route requires adding to this list. Honor-system. | Medium |

## Dependencies

- **Incoming:** every HTTP request, every CLI bootstrap.
- **Outgoing:** auth/, infra/rate_limit.py, portfolio/store.

## Open questions / Unknowns

- **Q1.** Rate-limiter window and threshold values?
- **Q2.** WebAuthn / TOTP roadmap?

## Suggested follow-ups

| Iteration | Area |
|---|---|
| **0085** | Integration point (already requested) — pick `infra/rate_limit.py`. |

---

Report/Report-0084.md written.

