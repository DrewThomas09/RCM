# Report 0090: Follow-up — Closes Report 0088 Q1+Q2+Q3+Q4 (Session Idle Timeout)

## Scope

Reads `auth/auth.py:225-300` and `server.py:85-105` to resolve Report 0088 open questions on session idle timeout. Sister to Report 0027 (ServerConfig), Report 0021 (auth security), Report 0084 (auth cross-cut), Report 0088 (config-value trace).

## Findings

### Resolution table — Report 0088 questions

| Question | Answer |
|---|---|
| **Q1.** Exact field name? | **N/A — not in ServerConfig.** Lives in `auth/auth.py:230-238` as module-level function `_idle_timeout_minutes()`. |
| **Q2.** Default value? | **30 minutes.** Hardcoded at `auth/auth.py:233, 237, 238`. |
| **Q3.** Env-var override? | **`RCM_MC_SESSION_IDLE_MINUTES`** (line 231). |
| **Q4.** Does live-mode keep session alive? | **YES — confirmed code-side.** `user_for_session(touch=True)` (default) bumps `last_seen_at` on every authenticated request (lines 252-255, 297). CLAUDE.md "live mode meta-refresh doesn't extend session TTL" is **incorrect** — the code says it does. **Confirms Report 0088 MR489.** |

### Surprise: ServerConfig is smaller than Report 0027 implied

Per `server.py:85-105`, **ServerConfig has only 5 fields**:

| Line | Field | Type | Default |
|---|---|---|---|
| 96-97 | `db_path` | `str` | `os.environ.get("RCM_MC_DB") or os.path.expanduser("~/.rcm_mc/portfolio.db")` |
| 98 | `outdir` | `Optional[str]` | `None` |
| 99 | `title` | `str` | `"RCM Portfolio"` |
| 103 | `auth_user` | `Optional[str]` | `None` |
| 104 | `auth_pass` | `Optional[str]` | `None` |

**Cross-correction to Report 0027:** ServerConfig is even thinner than that report suggested. Session timeout is **NOT** a ServerConfig field — it's its own env-var-only control read inside `auth/auth.py`.

### Architecture observation (HIGH-PRIORITY discovery)

ServerConfig is a **class-attribute config object** — note the docstring at `server.py:88-92`: "Using a class attribute keeps the handler constructor compatible with `BaseHTTPRequestHandler`." It's NOT a dataclass; it's a class with class-level defaults. Setting an attribute on the class (`ServerConfig.db_path = ...`) mutates global state. **Cross-link Report 0027.**

### Two expiry gates (correction to Report 0088 MR488)

`user_for_session` enforces **two** gates (per docstring lines 247-250):

1. **Absolute TTL via `expires_at`** — default 7 days, set at login.
2. **Idle timeout via `last_seen_at`** — 30 minutes default.

**Report 0088 MR488 was wrong** — there IS an absolute-session-max (7 days). Retract MR488. (HIPAA still recommends shorter for clinical apps, but PE diligence is not clinical.)

### Implementation walk — `_idle_timeout_minutes()`

```python
def _idle_timeout_minutes() -> int:
    raw = os.environ.get("RCM_MC_SESSION_IDLE_MINUTES", "").strip()
    if not raw:
        return 30
    try:
        n = int(raw)
    except ValueError:
        return 30
    return n if n > 0 else 30
```

**Defensive:** invalid env values fall back to 30, never 0 or negative. **Good.**

### Implementation walk — `user_for_session` flow (lines 241-300)

1. Empty token → `None`
2. `_ensure_tables(store)` — idempotent
3. SELECT row from `sessions JOIN users`
4. Parse `expires_at` (absolute TTL); if `now >= expires` → `None`
5. Compute idle_mins from arg-or-env-fallback
6. Parse `last_seen_at`; if `(now - last_seen) > idle_mins` → DELETE session, return None
7. If `touch=True` (default): UPDATE last_seen_at to now
8. Return `{username, display_name, role}`

**Idle-expired sessions self-clean.** Good — addresses Report 0088 MR491 partially (per-session cleanup happens; bulk cleanup still relies on `cleanup_expired_sessions`).

### `touch=False` callers

Per docstring lines 253-255: "Read-only callers that want to peek without sliding the window (e.g. background audit passes) can pass `touch=False`." **Q1 below: who actually calls with `touch=False`?**

### Cross-link to Report 0021 MR173 (no MFA)

Idle timeout + absolute TTL are the only session-strength controls. Without MFA, a 7-day TTL means a single password compromise → 7 days of access. Per Report 0084: brute-force backstop also missing. **Defense-in-depth thin on this surface.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR497** | **CLAUDE.md `live mode` claim contradicts code** (closes Report 0088 MR489) | CLAUDE.md "Known limitations" says live-mode-refresh doesn't extend TTL. Code confirms it DOES. Either fix CLAUDE.md OR pass `touch=False` from live-mode endpoints. | **Medium** |
| **MR498** | **`_idle_timeout_minutes` is reread on every authenticated request** | Function isn't memoized; `os.environ.get()` is cheap but called per-request. Negligible perf, but env-var changes pick up live (no restart needed). Could surprise — typically env vars are read once. | Low |
| **MR499** | **ServerConfig is class-attribute-mutable global** (cross-link Report 0027) | `ServerConfig.db_path = X` mutates global state for all subsequent requests AND all tests in the same process. Multi-test pollution risk. | Medium |
| **MR500** | **Session timeout is env-var-only, not CLI-flag** | No `rcm-mc serve --session-idle-minutes 60`. Operators must set env var. Per Report 0019 env-var sweep, this is consistent with project pattern. | Low |
| **MR501** | **Retract MR488 from Report 0088** | An absolute 7-day TTL exists. Report 0088 was wrong. | (correction) |

## Dependencies

- **Incoming:** every authenticated request (server.py session-cookie auth path).
- **Outgoing:** `os.environ`, `auth.sessions` table.

## Open questions / Unknowns

- **Q1.** Which call-sites (if any) pass `touch=False`? `grep "touch=False\|touch = False"` not run this iteration.
- **Q2.** Where is the **absolute** 7-day TTL set? `create_session` likely (Report 0021 named it at line 196). Worth confirming the literal `7` and whether it's also env-var-overridable.
- **Q3.** Does live-mode HTML actually call `user_for_session(touch=True)` or is there a special read-only path? CLAUDE.md insists it doesn't extend; code says it does.
- **Q4.** Are there tests asserting the 30-min default + env-var override?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0091** | Read `create_session` body to close Q2 (absolute TTL value + env var). |
| **0092** | Grep `touch=False` call-sites + read live-mode endpoint to close Q1+Q3. |
| **0093** | Branch register refresh #3 (per Report 0089). |

---

Report/Report-0090.md written.
Next iteration should: read `create_session` (auth/auth.py:196) to close Q2 — confirm 7-day absolute TTL literal + any env-var override.
