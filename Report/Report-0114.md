# Report 0114: Cross-Cutting — CSRF Protection

## Scope

Full audit of CSRF mechanism in `server.py`. Sister to Reports 0024 (logging), 0054 (caching), 0084 (auth). Closes a ~106-iteration gap on a security-critical surface.

## Findings

### Mechanism overview

| Component | Location | Function |
|---|---|---|
| Per-process HMAC secret | server.py:1529 | `_SERVER_SECRET = secrets.token_bytes(32)` — ephemeral, rotates on restart |
| CSRF value generator | server.py:1612-1620 | `_csrf_value(token)` — `HMAC-SHA256(server_secret, session_token)` |
| CSRF gate | server.py:1622-1643 | `_csrf_ok(form)` — header XOR form supply + `compare_digest` |
| Exempt-paths list | server.py:1546-1547 | `_CSRF_EXEMPT_POSTS` — 6 entries |

### Algorithm

CSRF token = HMAC-SHA256(server_secret, session_token).hexdigest()

- Generated at login success (`_route_login_post` server.py:14627-14628)
- Set as a **non-HttpOnly** `rcm_csrf` cookie (line 14637-14638) so JS can read it for form-injection
- Verified on every authenticated POST/PUT/DELETE/PATCH

### Verification gate (`_csrf_ok`, line 1622-1643)

3-tier:
1. **No session token** → return `True` (skip — legacy/Basic-auth path)
2. **Path in `_CSRF_EXEMPT_POSTS`** → return `True` (skip)
3. Else: header `X-CSRF-Token` (preferred for AJAX) **OR** form `csrf_token` field, compared via `hmac.compare_digest`

Both inputs use `compare_digest` (constant-time). Per Report 0021 auth audit: standard discipline.

### Call sites — `_csrf_ok` (4 invocations)

| Line | Method | Note |
|---|---|---|
| 10240 | `do_POST` | main POST gate |
| 10345 | `do_PUT` | analyst-override API |
| 10369 | `do_DELETE` | (inferred from line proximity) |
| 10440 | `do_PATCH` | (inferred — TBD) |

**4 entry points all call `_csrf_ok`.** Consistent surface coverage.

### Exempt-paths list (CRITICAL FINDING)

Per server.py:1546-1547:

```python
_CSRF_EXEMPT_POSTS: tuple = ("/api/login", "/api/logout", "/health",
                             "/quick-import", "/quick-import-json", "/screen")
```

**6 entries.** Per docstring (line 1544-1545):
> "Login must be exempt (no session yet); logout and health are idempotent / non-sensitive."

This justifies `/api/login`, `/api/logout`, `/health`. **The other 3 are suspicious:**

| Path | Likely behavior | CSRF concern |
|---|---|---|
| `/quick-import` | bulk-import POST (per server.py:10316 dispatch) | **HIGH** — state-changing; third-party form-submit could insert fake deals |
| `/quick-import-json` | JSON variant of quick-import | **HIGH** — same |
| `/screen` | batch hospital screening (per server.py:10320) | **MEDIUM** — read-mostly but expensive |

**MR639 below.** Cross-link to OWASP CSRF guidance: state-changing endpoints SHOULD have CSRF protection. Exempting `/quick-import` is a classic vulnerability pattern.

### Token-binding (cross-link Report 0090)

Server-secret (`_SERVER_SECRET`) is **per-process ephemeral** — line 1526-1528 docstring:
> "B128: per-process HMAC secret for CSRF tokens. Ephemeral — rotates each server restart, which also invalidates old form tokens."

So a server restart **invalidates all existing CSRF tokens.** Browsers with stale `rcm_csrf` cookie hit CSRF-failed on next POST → user must reload (which re-mints). **Acceptable** for a single-machine deployment per CLAUDE.md.

### Cookie discipline (cross-link Report 0108 login flow)

Per `_route_login_post` line 14637-14638:

```python
csrf_cookie = (
    f"rcm_csrf={csrf}; Path=/; SameSite=Lax; "
    f"Max-Age={7*24*3600}{secure}"
)
```

**Note: `rcm_csrf` is NOT HttpOnly** — JS-readable so the CSRF-patching shim can read it (per server.py:14156 docstring "the same one shell_v2 injects"). **This is the standard double-submit-cookie pattern** — accepted CSRF design.

| Cookie | HttpOnly | Reason |
|---|---|---|
| `rcm_session` | YES | session token (must not be JS-readable) |
| `rcm_csrf` | NO | must be JS-readable so form-injection works |

**Discipline correct.** Pattern: double-submit cookie + HMAC-bound to session.

### CORS allow-headers

| Line | Method handler | Allow-Headers |
|---|---|---|
| 10018 | (preflight or main) | `Content-Type, X-CSRF-Token` |
| 10170 | (preflight) | `Content-Type, X-CSRF-Token, Idempotency-Key` |
| 10428 | (per-method) | `Content-Type, X-CSRF-Token` |

**Inconsistency**: 10170 includes `Idempotency-Key`; 10018 + 10428 don't. **MR641 below.** Cross-link Report 0108 MR607 (idempotency-key cache before login dispatch).

### Form-vs-header preference (`_csrf_ok` line 1638-1643)

```python
header = self.headers.get("X-CSRF-Token", "")
if header and _h.compare_digest(header, expected):
    return True
supplied = (form or {}).get("csrf_token", "")
return bool(supplied) and _h.compare_digest(supplied, expected)
```

**Header takes precedence.** AJAX → header; HTML form → field. Both fall through to `False` on mismatch.

### `_csrf_value` symmetry

`_csrf_value(token)` is invoked at:
- **Mint**: `_route_login_post` line 14628 (creates the cookie)
- **Verify**: `_csrf_ok` line 1637 (recomputes for compare)

**Same input (session_token), same secret (server-process-scoped), same algorithm.** Symmetric — verifiable.

### Not-yet-exempt-list edge

`/api/upload-actuals`, `/api/upload-initiatives`, `/api/upload-notes` (server.py:10262-10267) ARE NOT in `_CSRF_EXEMPT_POSTS`. They go through the normal CSRF gate. **Good** — uploads need CSRF.

### Summary table — CSRF posture per route group

| Group | Auth required | CSRF required | Notes |
|---|---|---|---|
| `/api/login` | NO | NO | bootstrap |
| `/api/logout` | YES | NO (exempt) | idempotent per docstring |
| `/health`, `/healthz` | NO | NO | monitoring |
| `/quick-import*`, `/screen` | YES (per Report 0084) | **NO (exempt)** | **vulnerability per MR639** |
| All other `/api/*` POST/PUT/PATCH/DELETE | YES | YES | gated by 4 call-sites |

### Cross-link to Report 0084 (auth surfaces)

Report 0084 enumerated 13 auth surfaces but didn't catalog CSRF call-sites. This report adds:
- 1 secret (`_SERVER_SECRET`)
- 2 helpers (`_csrf_value`, `_csrf_ok`)
- 6 exempt paths
- 4 call-sites (do_POST/PUT/DELETE/PATCH)

**Total auth-related surfaces: now 26** (Report 0084's 13 + 13 from this iteration).

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR639** | **`/quick-import`, `/quick-import-json`, `/screen` exempted from CSRF** despite being state-changing | Classic CSRF vulnerability — third-party form-submission triggers imports in authenticated user's session. **OWASP-class issue.** | **High** |
| **MR640** | **CSRF-exempt list is hardcoded at server.py:1546** without enforcement that exempt paths must be idempotent | Adding a new state-changing route to exempt list won't trip any CI check. | Medium |
| **MR641** | **CORS Allow-Headers inconsistent** between server.py:10018 / 10170 / 10428 — sometimes includes `Idempotency-Key`, sometimes doesn't | Browsers may reject preflight if a new client sets Idempotency-Key on a route that doesn't advertise it. | Medium |
| **MR642** | **`_SERVER_SECRET` rotates on every restart** — invalidates all in-flight CSRF tokens | Per docstring intentional. But: a partner with a long-running form session loses their work on a deploy. UX issue. | Low |
| **MR643** | **`_csrf_ok` returns True when `_session_token() is None`** | "Open mode or HTTP-Basic script" path. Means an unauthenticated POST passes CSRF. Per CLAUDE.md HTTP Basic auth is supported (Report 0084 MR471). Combination with broken auth could elevate privileges. | Medium |
| **MR644** | **`/api/logout` is CSRF-exempt** | Docstring says "idempotent" — but a third-party site can force-logout an authenticated user (DoS). Mild but valid CSRF concern. | Low |
| **MR645** | **`X-CSRF-Token` header preferred over form field** — order matters | If a request includes BOTH a wrong header AND a correct form field, the wrong header wins → reject. Subtle. | Low |
| **MR646** | **`_audit_failure_count` counter never surfaced via UI/metric** | Per server.py:1551-1552: counter exists but no `/admin/audit-failures` route or metric — silent breadcrumb only on stderr. | Medium |

## Dependencies

- **Incoming:** every state-changing HTTP request, login-success cookie set, logout cookie clear.
- **Outgoing:** stdlib (`hmac`, `hashlib`, `secrets`), `auth.audit_log` (cross-cut for CSRF-failure events — TBD if logged).

## Open questions / Unknowns

- **Q1.** Is a CSRF-failed POST audit-logged anywhere?
- **Q2.** What does `/quick-import` actually do? — confirm it IS state-changing (CSV insert into `deals` table likely).
- **Q3.** Is the CSRF cookie's `Max-Age=7*24*3600` (7 days) consistent with session TTL (Report 0090: 7-day absolute)? **Yes — they match.** Closes Q3.
- **Q4.** Are there tests that verify `/quick-import` accepts cross-origin POSTs? (Should be a security regression test.)

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0115** | Read `_route_quick_import_post` body — confirms MR639 severity. |
| **0116** | Read `rcm_mc/api.py` (per Report 0113 follow-up). |
| **0117** | Schema-walk `mc_simulation_runs` (Report 0110 backlog). |

---

Report/Report-0114.md written.
Next iteration should: read `_route_quick_import_post` body to confirm whether MR639 is the OWASP-class CSRF vulnerability it appears to be.
