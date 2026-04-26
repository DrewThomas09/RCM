# Report 0108: Entry Point — `POST /api/login`

## Scope

Traces a browser-or-API login POST through every layer of the call stack until session cookie is set. Closes Report 0085 MR475 critical (incorrectly claimed login was unprotected). Sister to Reports 0018 (rcm-mc serve), 0048 (python -m), 0102 (data-refresh POST), 0021 (auth security), 0090 (session timeout).

## Findings

### MAJOR FINDING — closes Report 0085 MR475 (was Critical)

**`/api/login` IS rate-limited** — but by a custom per-IP fail-tracker on `RCMHandler`, NOT by `infra.rate_limit.RateLimiter`.

**The codebase has 2 distinct rate-limiting implementations:**

| Implementation | Location | Surface | Tunables |
|---|---|---|---|
| `infra.rate_limit.RateLimiter` | server.py:48, 49 | `/api/data/refresh/*` (1/hr), delete (10/hr) | `max_hits`, `window_secs` |
| Hand-rolled per-IP fail log | server.py:1537-1540, 14564-14577 | `/api/login` only | `_LOGIN_FAIL_MAX=5`, `_LOGIN_FAIL_WINDOW_SECS=60` |

**Report 0085 MR475 is RETRACTED.** Login path is protected: 5 fail attempts per minute per IP → 429.

### Layer-by-layer trace

#### Layer 1 — `ThreadingHTTPServer` request dispatch

Per Report 0018: `server.py` constructs `ThreadingHTTPServer((host, port), RCMHandler)`. Each incoming POST instantiates a fresh `RCMHandler` and calls `do_POST()`.

#### Layer 2 — `RCMHandler.do_POST()` (server.py:10195)

1. Read body (REQUEST_ENTITY_TOO_LARGE check at line 10247-10252).
2. Idempotency-Key cache check (line 10253-10257).
3. Path dispatch — `path == "/api/login"` → `_route_login_post()` (line 10258-10259).

**Auth bypass paths** (line 1704): `/health`, `/healthz`, `/login` (and per line 1706: `/api/login`) bypass the `_auth_ok` gate. Login MUST be reachable without auth.

#### Layer 3 — `_route_login_post` (server.py:14542-14687)

Inline imports at line 14550:
```python
from .auth.auth import create_session, verify_password
```

**Step-by-step:**

| Step | Line | Action |
|---|---|---|
| 3.1 | 14552 | `form = self._read_form_body()` — parse `application/x-www-form-urlencoded` |
| 3.2 | 14553-14554 | Extract `username`, `password` |
| 3.3 | 14555-14562 | **Open-redirect protection**: validate `next` is a local path (must start with `/`, not `//`, not contain `://`) |
| 3.4 | 14564-14577 | **Rate-limit check** under `_login_fail_lock` |
| 3.5 | 14579 | `verify_password(store, username, password)` |
| 3.6 | 14580-14594 | On fail: log timestamp + `log_event("login.failure")` + return 401 / 303 |
| 3.7 | 14613-14615 | On success: clear fail log for IP |
| 3.8 | 14618-14626 | `log_event("login.success")` |
| 3.9 | 14627 | `token = create_session(store, username)` |
| 3.10 | 14628 | `csrf = self._csrf_value(token)` |
| 3.11 | 14631-14638 | Set `rcm_session` cookie (HttpOnly, SameSite=Lax, Max-Age=7d) + `rcm_csrf` cookie (non-HttpOnly so JS can read for form-injection) |
| 3.12 | (later) | Redirect 303 → `nxt` OR JSON 200 if Accept: application/json |

#### Layer 3.5 — Rate-limit (per-IP fail log)

```python
_LOGIN_FAIL_WINDOW_SECS: int = 60                    # server.py:1537
_LOGIN_FAIL_MAX: int = 5                              # server.py:1538
_login_fail_log: Dict[str, list] = {}                 # server.py:1539 — CLASS-LEVEL
_login_fail_lock: threading.Lock = ...                # server.py:1540 — CLASS-LEVEL
```

**Class-level attributes** — shared across all handler instances (since `BaseHTTPRequestHandler` constructs a new instance per request).

Algorithm (lines 14564-14577):
1. `cutoff = now - 60`
2. Drop log entries older than cutoff
3. If `len(log) >= 5` → 429 RATE_LIMITED
4. Otherwise proceed to verify

Failed attempts append to log (line 14581). Successful login clears IP's log (line 14615).

**Fails open on restart** — same trade-off as `infra.rate_limit.RateLimiter`. After server restart, fail count resets.

#### Layer 4 — `auth.auth.verify_password` (per Report 0021)

Per Report 0021: scrypt-based constant-time comparison. Returns bool.

#### Layer 4 — `auth.auth.create_session` (per Reports 0021, 0090)

Generates `secrets.token_urlsafe(32)`, INSERTs into `sessions` table with `expires_at = now + 7days` (per Report 0090: 7-day absolute TTL) + `last_seen_at = now`. Returns token string.

#### Layer 4 — `auth.audit_log.log_event` (per Reports 0063, 0064)

INSERTs into `audit_events` table. Per Report 0087 schema: `(actor, action, target, detail_json, event_at)`.

**Action strings used by login:**
- `"login.failure"` (line 14589)
- `"login.success"` (line 14621)

**Cross-link Report 0087 MR483**: free-form action TEXT — typo here would silently lose audit trail. Confirmed pattern site.

#### Layer 5 — SQLite via `PortfolioStore.connect()`

`store = PortfolioStore(self.config.db_path)` line 14551. Connection per request — Reports 0017 + 0008 noted busy_timeout=5000.

### Tables touched per login attempt

| Table | Operation |
|---|---|
| `users` | SELECT (via verify_password) |
| `audit_events` | INSERT × 1 (success or failure) |
| `sessions` | INSERT × 1 (success only) |

### Response shape

| Outcome | Status | Body / Header |
|---|---|---|
| Rate-limited | 429 | JSON: `{"error": "too many...", "code": "RATE_LIMITED"}` |
| Bad credentials (Accept: application/json) | 401 | JSON: `{"error": "invalid credentials", "code": "INVALID_CREDENTIALS"}` |
| Bad credentials (browser) | 303 | redirect to `/login?err=...&next=...` |
| Success (Accept: application/json) | 200 | (TBD — body shape past line 14638 not extracted) |
| Success (browser) | 303 | redirect to validated `nxt` + Set-Cookie ×2 |

### Audit-event trace (cross-link Report 0072)

Failed and successful logins both invoke `log_event` wrapped in `try/except Exception: pass` (lines 14585-14594, 14618-14626). **Audit-write failures are silently swallowed.**

Per Report 0072: this is a documented Pattern A (audit-event recording is best-effort, not load-bearing). Cross-link Report 0024 logging.

### Security observations

| Point | Status |
|---|---|
| Open-redirect on `next=` | **Mitigated** — line 14555-14562 validates local path only |
| CSRF on `/api/login` | **Bypassed by design** — `_CSRF_EXEMPT_POSTS` includes `/api/login` (line 1546) |
| Brute force | **Mitigated** — 5/min per IP |
| Session-fixation | session token regenerated on login (Report 0021) |
| Constant-time pw compare | per Report 0021 (`secrets.compare_digest`) |
| HttpOnly session cookie | **YES** — line 14632 |
| Secure cookie flag | conditional on `_cookie_flags()` (line 14630) — TLS-only |
| SameSite=Lax | **YES** — line 14632 |
| Cookie Max-Age | 7 days (`7*24*3600`) — matches absolute session TTL per Report 0090 |

### Cross-link to Report 0085 + 0084

- Report 0084 MR470 (rate_limit.py never audited) — cross-correct: rate_limit.py was correctly audited as data-refresh-only; the login limiter is **separate**.
- Report 0085 MR475 (login unprotected, Critical) — **RETRACTED**. Login is protected via the class-level fail-log.
- The CRITICAL in MR475 was based on missing the second rate-limiting implementation. Project-side, this report restores confidence.

### Cross-link to Report 0103 (job_queue idempotency)

`Idempotency-Key` header is honored at the do_POST layer (line 10253) BEFORE login path-dispatch. **A login POST with `Idempotency-Key` could replay a cached response** without re-checking credentials. Likely never used by browsers but a thin attack surface. **Q1 below.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR604-correction** | **Report 0085 MR475 (login unprotected) was WRONG — RETRACTED** | 5/min per-IP fail log exists at server.py:1537-1540 + 14564-14577. | (correction) |
| **MR605** | **Two rate-limiting implementations coexist** (`RateLimiter` class vs class-level `_login_fail_log`) | Diverging behavior: failure modes, restart semantics, accuracy. Cross-cuts a known patch. | Medium |
| **MR606** | **5 attempts per minute per IP is permissive** | Behind a CDN/proxy with shared egress IP, multiple legitimate users hit the limit. Low-budget brute force still gets ~7,200 attempts/day per IP. | Medium |
| **MR607** | **Idempotency-Key cached BEFORE auth check** (line 10253-10257 vs 10258 dispatch) | If a login response is cached under an Idempotency-Key, replays return the cached response (incl. cookies) without re-verifying. | **High** |
| **MR608** | **`audit_events` write failure is silently swallowed** (lines 14585-14594, 14618-14626) | Per Report 0072 documented Pattern A. But: a determined attacker can DoS the audit table; logins still succeed and audit is gone. | Medium |
| **MR609** | **`_login_fail_log` is unbounded** | Same pattern as Report 0085 MR474 (RateLimiter._log unbounded). High-cardinality client IP set + long uptime → memory leak. | Low |
| **MR610** | **Login bypass paths hardcoded in 2 places** (server.py:1704 + 1706) | `/login` and `/api/login`. If a third-party adds `/login.json`, auth gate may fire incorrectly. Cross-link Report 0084 MR472. | Low |

## Dependencies

- **Incoming:** browser POST `<form action="/api/login">` (per server.py:14235), API client POST with `Accept: application/json`, `python -m rcm_mc serve` after login form rendered.
- **Outgoing:** `auth.auth.verify_password`, `auth.auth.create_session`, `auth.audit_log.log_event`, `PortfolioStore`, `_csrf_value`. Tables: `users` (R), `sessions` (W), `audit_events` (W).

## Open questions / Unknowns

- **Q1.** Does `_idempotency_cache` cache failed-credential responses? (If yes, replay attack: re-use the same Idempotency-Key for the same denied login.)
- **Q2.** What is the EXACT successful-login JSON body shape (past line 14638)?
- **Q3.** Why is `_login_fail_log` class-level rather than instance-level OR module-level? Class-level works because Python instantiates the class once per process (handler class is shared). But this is non-obvious.
- **Q4.** Is the CDN/proxy IP-extraction issue (X-Forwarded-For) handled? `self.client_address[0]` is the **TCP peer**, not the user's real IP. **HIGH-PRIORITY behind any reverse proxy.**

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0109** | Read `infra/consistency_check.py` (carried from Report 0107). |
| **0110** | Verify Q4 — does `_route_login_post` honor `X-Forwarded-For` for IP-based rate limit? |
| **0111** | Map `rcm_mc_diligence/` separate package (carried 8+ iterations). |

---

Report/Report-0108.md written.
Next iteration should: read `infra/consistency_check.py` to close Report 0107 Q1 + half of MR597.
