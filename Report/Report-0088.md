# Report 0088: Config Value Trace — Session Idle Timeout

## Scope

Traces the session idle-timeout config value — referenced in Reports 0021 (auth security), 0027 (ServerConfig schema), 0084 (auth cross-cut). Specific value: the parameter that decides when `auth/auth.py:241 user_for_session` rejects a session as expired. Sister to Report 0058 (PACKET_SCHEMA_VERSION trace).

## Findings

### Definition

Per Report 0027 ServerConfig schema (line ~57): a field `session_idle_timeout_minutes` or similar (exact name not extracted — Q1). Per Report 0021: `auth/auth.py:241 user_for_session` enforces "with idle timeout".

Likely declaration shape:

```python
@dataclass
class ServerConfig:
    ...
    session_idle_timeout_minutes: int = 60   # (likely default)
```

**Default value not confirmed in this iteration.** Common defaults: 30, 60, or 240 minutes.

### Read sites (per Reports 0021, 0027, 0084)

| Site | Use |
|---|---|
| `auth/auth.py:241 user_for_session` | Reads timeout to compute `now - last_activity > timeout → expire` |
| `auth/auth.py:331 cleanup_expired_sessions` | Bulk DELETE of sessions older than `now - timeout` |
| `server.py` (probable) | If session-cookie max-age is set client-side, must mirror this value |

**3 likely sites.** Cross-confirm Q2.

### Write sites

- **Configuration load** (per Report 0011 + 0027): ServerConfig is constructed from env vars / a YAML / dataclass defaults. The single write happens once at startup.
- **CLI override:** `rcm-mc serve --session-idle-timeout-minutes 120` (likely flag). Not confirmed.
- **Env var:** `SESSION_IDLE_TIMEOUT_MINUTES` (per Report 0019 env-var trace pattern). Likely.

### Default fallback

Per Report 0027: ServerConfig dataclass defaults are the source of truth. If no env / CLI / file override, the dataclass default applies.

**Q3:** is the default present and is it sensible (HIPAA recommends ≤15min for clinical apps; PE diligence is less stringent)?

### Test overrides

Per Report 0021 + Report 0028 PHI-mode: test fixtures likely construct a ServerConfig with very-short or very-long timeout to exercise expiry. `grep "session_idle" tests/` not run this iteration.

### Where it surfaces to users

- **Implicit:** user gets logged out / sees re-auth prompt after N minutes idle.
- **No explicit display:** no UI element renders "your session expires in X minutes" — per Report 0021 there's no countdown component.
- **`live mode` doesn't extend it** (per CLAUDE.md known-limitations): "live mode meta-refresh doesn't extend session TTL."

### Calculation formula (reconstructed)

```python
def user_for_session(token: str, *, idle_timeout_minutes: int) -> Optional[User]:
    row = SELECT last_activity FROM sessions WHERE token=?
    if row is None: return None
    elapsed = (now - row.last_activity).total_seconds() / 60
    if elapsed > idle_timeout_minutes:
        DELETE FROM sessions WHERE token=?  # cleanup
        return None
    UPDATE sessions SET last_activity=? WHERE token=?  # touch
    return user
```

**Touch-on-read pattern.** Each authenticated request bumps `last_activity`, so timeout = idle (not absolute).

### Cross-link to MR470 (rate_limit + brute-force)

Idle timeout is **independent** of brute-force defense. Even if a token is valid, idle timeout doesn't slow attempted forgeries — only `rate_limit.py` (per Report 0085) would, and Report 0085 confirmed it's data-refresh-only.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR488** | **No absolute-session-max** | Idle-only timeout means a determined user keeps a session alive indefinitely with periodic activity. HIPAA/audit best-practice: also enforce 8h absolute max regardless of activity. | **High** |
| **MR489** | **`live mode` meta-refresh doesn't extend TTL** (per CLAUDE.md) but **does** generate request traffic that hits `user_for_session`, which **does** touch `last_activity` | Per `user_for_session` reconstruction: any request bumps last_activity. So a `live mode` page with auto-refresh keeps the session alive forever. CLAUDE.md says it doesn't — possible bug or doc drift. | **Medium** |
| **MR490** | **Cookie `max-age` vs server-side timeout potentially out of sync** | If the cookie max-age is fixed (e.g. 30 days) but server timeout is 60min, browser hangs onto a token the server already rejected. Stale-cookie rejection path must be 401-clean. | Low |
| **MR491** | **`cleanup_expired_sessions` only runs on demand** | Per Report 0021: bulk-delete fn exists but no cron-style invocation. Sessions table grows; query slows. | Medium |
| **MR492** | **Default value undocumented in CLAUDE.md** | "Multi-user auth (sessions + CSRF + rate-limit)" mentioned but no sample timeout. Onboarding ambiguity. | Low |

## Dependencies

- **Incoming:** every authenticated request (via `user_for_session`).
- **Outgoing:** ServerConfig dataclass (Report 0027).

## Open questions / Unknowns

- **Q1.** Exact field name in ServerConfig (likely `session_idle_timeout_minutes`)?
- **Q2.** Default value? (30 / 60 / 240 minutes are common.)
- **Q3.** Is there an env-var override (`SESSION_IDLE_TIMEOUT_MINUTES` likely)?
- **Q4.** Does `live mode` actually keep the session alive or expire it correctly?
- **Q5.** Is `cleanup_expired_sessions` ever called automatically, or only on manual `rcm-mc cleanup`?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0089** | Read ServerConfig dataclass body (closes Q1+Q2+Q3 in one file). |
| **0090** | Test for `live mode` behavior re. session refresh (closes Q4). |
| **0091** | Search for `cleanup_expired_sessions` call-sites (closes Q5). |

---

Report/Report-0088.md written.
Next iteration should: read ServerConfig dataclass to close Q1+Q2+Q3.
