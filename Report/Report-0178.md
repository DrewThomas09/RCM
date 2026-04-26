# Report 0178: Config Trace — `RCM_MC_AUTH` env var (HTTP Basic creds)

## Scope

Traces `RCM_MC_AUTH` env var. Per Reports 0090, 0118, 0151: cited but never deeply traced. Sister to Reports 0019, 0028, 0042, 0049, 0079, 0090, 0109, 0115, 0118, 0139, 0169.

## Findings

### Read sites

Per `server.py:101-102` (per Report 0090):
```python
# When the env-var ``RCM_MC_AUTH`` is set as ``user:pass``, build_server
# copies it here and every request must carry matching Basic auth.
auth_user: Optional[str] = None
auth_pass: Optional[str] = None
```

Cross-link Report 0084 MR471: HTTP Basic auth + session cookies coexist. **`RCM_MC_AUTH` activates the Basic-auth path.**

### Format

Per docstring: `RCM_MC_AUTH=user:pass`. Single env var; colon-separated. **No multi-user support via this var.**

### Default fallback

If unset → `auth_user = None` and `auth_pass = None` (per ServerConfig defaults Report 0027 + 0090). **Auth is DISABLED.** Anyone can hit the server.

**MR921 below**: in production deployments with `RCM_MC_AUTH` unset, server is fully open.

### Write sites

Per `build_server` in `server.py` (cited in docstring): set on ServerConfig class-attr. **Class-attribute mutation pattern** — cross-link Report 0090 MR499 medium (ServerConfig class-attribute-mutable global).

### Cross-link to Report 0084 + Report 0108

Per Report 0084: HTTP Basic auth is the legacy path; session cookies are primary. **Both supported simultaneously** (MR471 medium).

Per Report 0108: login flow → session cookies → user_for_session.
**Per RCM_MC_AUTH path**: HTTP Basic header → matched against config — no session, no audit log entry per Report 0084 MR430.

### Audit-log gap (cross-link Report 0084 MR430)

Per Report 0084 MR430: audit-event recording happens only on HTTP path. **Basic-auth requests bypass audit?** Unclear. **Q1 below.**

### What fails if missing

Nothing fails — auth is disabled, server runs open.

**Per CLAUDE.md "Multi-user security" Phase 3**: production WOULD set `RCM_MC_AUTH` (or use session-cookie path). Fresh-install default is OPEN.

### Cross-link to Report 0114 CSRF

Per Report 0114 MR643 medium: `_csrf_ok` returns True when no session token (HTTP-Basic auth path). **Two attack-class concerns combine: open + Basic + no CSRF gate.** Production deployments must override RCM_MC_AUTH OR rely on session-cookie path.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR921** | **Default behavior with RCM_MC_AUTH unset = NO authentication** | Server runs open. Per CLAUDE.md "Multi-user security" — production must set this OR rely on session-cookie path (Report 0090 MR497 conflict). | **High** |
| **MR922** | **`RCM_MC_AUTH=user:pass` is single-user-pair format** | No multi-user via env. For multi-user, must use session-cookie path (Report 0108). | (advisory) |
| **MR923** | **Basic-auth path may bypass audit logging** | Cross-link Report 0084 MR430. Q1 below. | Medium |
| **MR924** | **Combination of Basic auth + bypass-CSRF (Report 0114 MR643)** | Open mode AND no CSRF gate. Defense-in-depth gap if both apply. | High |

## Dependencies

- **Incoming:** every HTTP request via `RCMHandler._auth_ok` gate.
- **Outgoing:** ServerConfig class-attr; `secrets.compare_digest` likely.

## Open questions / Unknowns

- **Q1.** Does Basic-auth request hit audit_log.log_event? Per Report 0084 MR430: probably not.
- **Q2.** Does CLAUDE.md document the open-by-default behavior?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0179** | (next iteration TBD). |

---

Report/Report-0178.md written.
