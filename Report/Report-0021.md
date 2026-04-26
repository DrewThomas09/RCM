# Report 0021: Security Spot-Check — `rcm_mc/auth/auth.py`

## Scope

This report covers a **security audit of `RCM_MC/rcm_mc/auth/auth.py`** (467 lines, 16,483 B) on `origin/main` at commit `f3f7e7f`. Module owns multi-user authentication: scrypt password hashing, session tokens, role-based access (admin / analyst), and user lifecycle (create/verify/delete + idle-timeout).

The audit checks for:
- Hardcoded secrets
- SQL injection vectors
- Unsafe deserialization (`eval` / `exec` / `pickle`)
- Shell injection (`subprocess`, `os.system`)
- Missing input validation
- Weak crypto choices (algorithm, parameters, randomness, constant-time compare)
- Logging/audit gaps

The full 467 lines were read line-by-line. CLAUDE.md (Report 0002) names this subsystem as "scrypt passwords, sessions, CSRF, rate-limited login" — the rate-limiter and CSRF protection live in `infra/rate_limit.py` and elsewhere; this report covers the password + session core.

Prior reports reviewed before writing: 0017-0020.

## Findings

### Hardcoded secrets — CLEAN

`grep -nE "password\s*=\s*['\"]|secret\s*=\s*['\"]|api_key\s*=\s*['\"]|token\s*=\s*['\"]"` returns empty. **No hardcoded credentials.**

### SQL injection — CLEAN

All 21 SQL `execute()` call sites use **parameterized queries with `?` placeholders**. No f-strings, no `%`-formatting, no string concatenation into SQL. Sites verified:

| Lines | Operation | Pattern |
|---|---|---|
| 90-99 | `CREATE TABLE IF NOT EXISTS users (...)` + `sessions` | DDL — no user input |
| 116-119 | `ALTER TABLE sessions ADD COLUMN last_seen_at` | DDL |
| 120-122 | `CREATE INDEX IF NOT EXISTS idx_sessions_username` | DDL |
| 151-158 | `INSERT INTO users (...)` | Tuple-bound parameters |
| 181-185 | `SELECT password_hash, password_salt FROM users WHERE username = ?` | `(u,)` |
| 216-221 | `INSERT INTO sessions (...)` | Tuple-bound |
| 261-267 | `SELECT s.username, ... FROM sessions s JOIN users u ... WHERE s.token = ?` | `(token,)` |
| 289-291 | `DELETE FROM sessions WHERE token = ?` | `(token,)` |
| 300-303 | `UPDATE sessions SET last_seen_at = ? WHERE token = ?` | `(_iso(now), token)` |
| 324-326 | `DELETE FROM sessions WHERE token = ?` | `(token,)` |
| 343-346 | `DELETE FROM sessions WHERE expires_at < ?` | `(now,)` |
| 354-357 | `SELECT username, display_name, role, created_at FROM users ORDER BY username` | No user input |
| 381-384 | `UPDATE users SET password_hash = ?, password_salt = ? WHERE username = ?` | Tuple-bound |
| 389 | `DELETE FROM sessions WHERE username = ?` | `(u,)` |
| 427-435 | `SELECT COUNT(DISTINCT deal_id) FROM deal_owner_history ... WHERE owner = ?` | `(u,)` |
| 444-447 | `SELECT COUNT(*) FROM deal_deadlines WHERE owner = ? AND status = 'open'` | `(u,)` (status is a literal, not user input) |
| 456 | `DELETE FROM sessions WHERE username = ?` | `(u,)` |
| 457-459 | `DELETE FROM users WHERE username = ?` | `(u,)` |
| 113-114 | `PRAGMA table_info(sessions)` | DDL/introspection |

**Every dynamic input flows through `?`-placeholders.** No SQL injection vectors detected.

### Unsafe deserialization / shell injection — CLEAN

`grep -nE "\beval\(|\bexec\(|pickle\.|subprocess\.|os\.system\("` returns empty. **No code-execution attack surface.**

### Input validation

| Field | Validator | Line | Effect |
|---|---|---|---|
| `username` | `_USERNAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@-]{0,39}$")` | 46 | Strict whitelist: alnum + `. _ - @`, must start alnum, max 40 chars, no spaces. Validated by `_validate_username` (line 73). |
| `password` (length, lower bound) | `len(password) < 8 → ValueError` | 138, 373 | Enforces minimum 8 chars on `create_user` and `change_password`. |
| `password` (length, upper bound) | `len(password) > 256 → ValueError` | 143, 375 | **B150 fix**: cap at 256 chars to prevent scrypt DoS. |
| `password` on verify | `len(password) > 256 → return False` | 173-174 | Same cap, but returns False instead of raising (denial-of-service-resistant login). |
| `role` | `role in ("admin", "analyst")` | 136 | Whitelist. Two values only. |
| `ttl_hours` | `int(ttl_hours) <= 0 → ValueError` | 208 | **B147 fix**: prevent immediate-expiry tokens. |
| `token` | `if not token: return None / False` | 257, 320 | Empty-string sentinel rejected. |
| `display_name` | `str(display_name or "").strip()` | 156 | Best-effort coercion — accepts any string but normalizes to empty. |

**Input validation is consistent and bounded.** Note: every public function calls `_validate_username` first, except `cleanup_expired_sessions` and `list_users` which take no user input.

### Crypto primitives — STRONG with one weakness

| Primitive | Site | Verdict |
|---|---|---|
| **scrypt** for password hashing | `_hash_password(password, salt)` at line 65-70 | **Modern, recommended algorithm.** PBKDF2 / bcrypt would be acceptable; scrypt is better. Implementation uses stdlib `hashlib.scrypt`, no third-party dep. |
| Per-user salt | `salt = os.urandom(16)` at lines 147, 378 | 128-bit random salt. **Standard.** |
| Constant-time password compare | `hmac.compare_digest(bytes(row["password_hash"]), candidate)` at line 193 | **Correct.** Prevents timing leaks on hash comparison. |
| Session tokens | `secrets.token_urlsafe(32)` at line 212 | 32 bytes ≈ 256 bits of entropy via `secrets` (cryptographically secure RNG). **Best practice.** |
| Username-enumeration timing protection | `_hash_password(password or "", os.urandom(16))` on unknown user (line 190) | **Partial protection** — burns roughly the same scrypt cost. But the prior `SELECT password_hash, password_salt FROM users WHERE username = ?` (line 181) takes a different time when the row is absent (very fast) vs present (cache hit/miss, btree). **Timing-perfect this is not** — but per the comment ("threat model = local deploy"), the gap is acceptable. |

#### `scrypt` parameter choice — SUB-OPTIMAL

```python
_SCRYPT_N = 2 ** 14  # cost  → N = 16,384
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32
```

(lines 51-54)

**Comment rationale (line 48-50):** "Values chosen for ~100ms verify on commodity hardware — fast enough that a real login isn't noticeable, slow enough that offline brute force on a leaked DB costs real money."

**Issue:** OWASP's password-storage cheat sheet recommends scrypt with **N ≥ 2^15 (= 32,768) minimum**, ideally N=2^17 (=131,072) on modern hardware. **`N = 2^14` is below the minimum recommendation.** RFC 7914 (the scrypt RFC) does NOT mandate a minimum; it says "the parameters … should be carefully chosen". Modern guidance (2024) considers `N=2^14` light.

The "100ms target" is reasonable for UX but trades attacker work-factor for it. On a deploy where:
- The DB might leak (e.g. backup leaked, host compromised)
- Attackers run dedicated GPU/ASIC rigs

…N=16384 with r=8, p=1 takes ~tens of GPU-seconds per password to brute-force at the high end. With N=131072 it would be ~hundreds.

**Recommendation:** raise N to at least 2^15 (32768). Re-time on production hardware before bumping further.

### Failed-login logging — GAP

`grep -nE "logger\.(error|warning|exception|info|debug)"` on `auth/auth.py` returns **0 calls**. The module has no `logger` import.

**No logging of failed login attempts.** A user typing the wrong password 100 times in a row produces no log line. Combined with the `RateLimiter` (per Report 0018 line 42 imports `RateLimiter` in server.py), throttling is enforced but **forensic visibility into brute-force attempts depends entirely on the rate-limit subsystem**. If a feature branch disables or weakens rate-limit, there's no fallback signal.

**Recommendation:** add `logger.warning("auth fail: user=%s", u)` at `verify_password` line 191 (post-burn-cost). And `logger.info("auth ok: user=%s", u)` at successful return.

### Audit-event hooks — N/A in this module

This module focuses on auth primitives; the higher-level audit-log emission (`audit_log.record(...)`) lives in `auth/audit_log.py` (per server.py imports). Future iteration should verify that login/logout events feed into the audit log.

### Session-touch silent swallow

Line 305: `except Exception: # noqa: BLE001 ... pass` — session-touch DB write failure is silently ignored. Comment (line 306-309): "Touching the session must never break auth — a DB write failure here should still let the authenticated request proceed. Next request will try again."

**Defensible** — session-touch is a hygiene operation, not a correctness requirement. But combined with the lack of any logger call here, **a DB outage on session-touch is invisible.**

### Concurrency-safety strength

`delete_user` (line 423) opens a `BEGIN IMMEDIATE` transaction (line 424) before checking for current-owner deals or open deadlines. **Prevents TOCTOU races.** This is solid.

Comment (line 405-409) explicitly explains the rationale: "hold a single IMMEDIATE-write transaction across the check + delete so a concurrent assign_owner/add_deadline can't sneak in between us verifying 'no current references' and deleting the user row."

### Idle-timeout

Lines 230-238: `_idle_timeout_minutes()` reads `RCM_MC_SESSION_IDLE_MINUTES` env var (per Report 0019 inventory), default 30 minutes. Negative or zero values fall back to 30. **Sensible defaults; well-validated.**

### Session-on-password-rotation revocation

Line 389: `con.execute("DELETE FROM sessions WHERE username = ?", (u,))` — when a user changes their password, every existing session for that user is invalidated. **Standard best practice; explicit comment (line 366-370) documents the "rotated because of compromise" scenario.**

### Username regex weakness

`^[A-Za-z0-9][A-Za-z0-9_.@-]{0,39}$` (line 46) is strict. But it allows characters that may cause issues in downstream contexts:

- `@` allows `analyst@firm.com` — useful for emails as usernames; but if the system also has an "analyst" user, both can legitimately exist. Probably fine.
- `.` allows `john.doe` — fine.
- No length minimum (just `>= 1` via the leading-char rule). A 1-char username (`a`) is valid.

**Not a vulnerability — just a footgun if a UI somewhere assumes minimum length 3.**

### Tokens stored in plaintext in DB

Session token at line 217-220 is stored as the literal token string, not a hash. This is the SQLite-backed equivalent of a Bearer token — anyone with read access to the SQLite file can read all active session tokens and impersonate any logged-in user.

**Threat model context:** the SQLite DB is on the same host as the server. Anyone with file-read access already has full access. The sessions-table-plaintext design is **acceptable for this threat model** (single-host deploy, file-system-trust boundary). Comment in CLAUDE.md states "Single-machine deployment. No clustering, no Postgres path."

But: backup files, dev replicas, accidental SCP, etc. could expose the DB. Even hashed-token storage (with constant-time lookup via reverse index) would protect against a leaked-DB-but-not-host-compromised threat.

**Recommendation (low priority for current threat model):** consider HMAC'd tokens with a server-side secret.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR162** | **scrypt N=2^14 is below OWASP minimum** | `_SCRYPT_N = 2 ** 14 = 16,384`. OWASP recommends ≥ 2^15. A leaked DB takes O(2x) less attacker work than current best practice. **Pre-merge: any branch that touches `_SCRYPT_*` constants must re-time on production hardware.** Recommend bumping to 2^15 (= 32768) before any prod deploy. | **High** |
| **MR163** | **Zero logger calls in auth/auth.py** | No `logger.warning` on failed login. Forensic visibility depends entirely on `RateLimiter` (separate module). If the rate-limiter is disabled/misconfigured, brute-force attempts produce no log line. **Pre-merge: any branch that disables RateLimiter must add logging here first.** | **High** |
| **MR164** | **Username-enumeration timing — partial protection** | The "burn ~equal scrypt cost on unknown user" pattern (line 190) is good but not perfect — the SELECT before line 190 differs in cost between found/not-found rows. Tightening would require constant-time DB access (impractical). For local-deploy threat model this is fine; for any future remote/multi-tenant deploy it becomes more relevant. | Medium |
| **MR165** | **Session tokens stored in plaintext in SQLite** | If `portfolio.db` leaks (backup, dev copy), every active session token is exposed. Local-deploy threat model accepts this; any remote-deploy branch should HMAC the tokens with a server-side secret. | Medium |
| **MR166** | **`change_password` rotates sessions, but `delete_user` does not first force-logout other sessions before the deal-ownership check** | `delete_user` (line 394-467) holds an IMMEDIATE txn but the existence-checks happen before `DELETE FROM sessions`. Someone with an active session could be in mid-flight while the user row is deleted. **Per Report 0017 MR123, deletion semantics across the schema are dual-tracked**; this auth-side deletion is one slice. Edge case, low impact. | Low |
| **MR167** | **`_idle_timeout_minutes()` re-reads env var per call** | Line 230-238. Each `user_for_session()` invocation reads `RCM_MC_SESSION_IDLE_MINUTES`. Cheap but means changing the env var midflight applies on the next request. **Consistent with Report 0019 patterns** (per-request env reads); flagged for awareness only. | Low |
| **MR168** | **`role` whitelist is hardcoded — no future-proofing** | Line 136: `role in ("admin", "analyst")`. A branch that adds a third role (e.g. "viewer", "auditor") needs to update this single check, plus every consumer that branches on role. **Pre-merge sweep for any new role values.** | Medium |
| **MR169** | **Password length cap at 256 — bypass on the UPDATE branch** | `change_password` (line 375) and `create_user` (line 143) both enforce `<= 256`. `verify_password` returns False at >256 (line 173-174). **Consistent.** No bypass. (False alarm — listed for completeness.) | (verified safe) |
| **MR170** | **`_ensure_tables` runs ALTER TABLE on every call** | Lines 113-119 check pragma → conditional ALTER. The pragma check is cheap but means every auth call has at least one extra read. Combined with `_ensure_tables` being called from every public function, this is N extra DB hits per request. **Performance only; not security.** | Low |
| **MR171** | **`hmac.compare_digest` operates on bytes — `bytes(row["password_hash"])` cast assumes the BLOB column actually contains bytes** | Line 193: `bytes(row["password_hash"])`. If a future migration accidentally stores the hash as a hex string (e.g. for debug), `bytes("hex_string")` would not be the same byte values as the original hash. Compare would fail silently → all logins return False. | Medium |
| **MR172** | **No CAPTCHA / bot-deterrent signal — relies entirely on RateLimiter** | A scripted attacker can brute-force usernames + passwords subject only to the rate-limit window. This is fine for a known-user-list attack at the rate-limit ceiling but means **the system has no second-factor defense if rate-limiting fails open**. | Medium |
| **MR173** | **No 2FA / multi-factor primitive** | The module has no TOTP / WebAuthn / hardware-key support. **For a local single-tenant tool this is appropriate; for any "remote-access portfolio for partners" scenario, this is a feature-level gap.** | (advisory) |

## Dependencies

- **Incoming:** `server.py:16277-16280` (`cleanup_expired_sessions` at boot per Report 0018); per-request session validation (likely `user_for_session` called from every route's auth gate); `cli.py` (likely calls `create_user` for the bootstrap admin per CLAUDE.md "rcm-mc portfolio users create"); `auth/audit_log.py` (sister module, audit log); `infra/rate_limit.py` (the RateLimiter; protects against brute force).
- **Outgoing:** stdlib only (`hashlib`, `hmac`, `os`, `re`, `secrets`, `datetime`, `typing`); `pandas` for `list_users()`; `portfolio.store:PortfolioStore`. **No third-party security libs** — confirms the no-new-runtime-deps stance.

## Open questions / Unknowns

- **Q1 (this report).** Are failed login attempts logged anywhere? `auth/audit_log.py` (sister module) likely captures them — need to verify.
- **Q2.** Is the `RateLimiter` configured with an aggressive enough window for password brute-force resistance? `infra/rate_limit.py` not yet read.
- **Q3.** Does the `delete_user` flow actually invalidate the deleted user's active session BEFORE the user row is removed? Reading the txn ordering: line 456 deletes sessions, line 457 deletes users — sessions are killed first, but inside the same txn. A concurrent request held by the active session might still complete with stale auth context. Edge case worth a test.
- **Q4.** Is `RCM_MC_SESSION_IDLE_MINUTES` documented for operators? Per Report 0019 MR146, env vars are not in any README.
- **Q5.** Does any branch on origin add a third role (e.g. "viewer")? Cross-branch sweep needed.
- **Q6.** Is `change_password` rate-limited the same way `verify_password` is? A logged-in user could brute-force their own password (low value) but more importantly an attacker who steals a session could change the password without knowing the old one — that's a session-hijack-amplification attack.
- **Q7.** Are there any `auth/auth.py` consumers that call `_hash_password` directly (bypassing `create_user`)? Module-private convention says no, but verify.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0022** | **Read `auth/audit_log.py`** — sister module for audit events. | Resolves Q1 — does the platform log failed logins? |
| **0023** | **Read `infra/rate_limit.py`** — the brute-force-resistance backstop. | Resolves Q2 / MR163 / MR172. |
| **0024** | **Read `auth/external_users.py`** (per Report 0005 lazy imports) and `auth/rbac.py` — sister auth modules. | Closes the auth-subsystem map. |
| **0025** | **`auth/audit_log.py` security spot-check** — same audit pattern. | Companion. |
| **0026** | **Audit `change_password` for old-password-required workflow.** | Resolves Q6 — current API takes only `new_password`, no old-password verification. |
| **0027** | **Read `infra/logger.py`** — owed since Report 0020. | Closes the logger-level question for the whole codebase. |

---

Report/Report-0021.md written. Next iteration should: read `auth/audit_log.py` end-to-end and verify whether failed login attempts produce audit events — closes Q1 here, MR163 (no logger calls in auth.py), and finally answers whether brute-force attempts have any forensic visibility beyond the rate-limit module.

