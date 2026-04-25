# Report 0049: Env-Var Audit — `infra/notifications.py`

## Scope

`RCM_MC/rcm_mc/infra/notifications.py` (219 lines) on `origin/main` at commit `f3f7e7f`. 4 SMTP env vars per Report 0019 MR148. Email + Slack notification dispatch.

Prior reports reviewed: 0045-0048.

## Findings

### Env vars in module (4 SMTP)

```python
# Lines 84-90 inside _send_email():
host = os.environ.get("SMTP_HOST")
if not host:
    logger.debug("SMTP not configured; email skipped")
    return False
port = int(os.environ.get("SMTP_PORT") or 587)
user = os.environ.get("SMTP_USER") or ""
password = os.environ.get("SMTP_PASS") or ""
```

| Var | Default | Failure mode if missing |
|---|---|---|
| `SMTP_HOST` | None | Function returns False, logs `logger.debug("SMTP not configured; email skipped")`. **No error.** |
| `SMTP_PORT` | 587 (STARTTLS port) | Always-defined fallback. |
| `SMTP_USER` | "" empty string | If empty AND password empty, skips login (line 101). |
| `SMTP_PASS` | "" empty string | Same; combined with USER, skips login. |

**Per-call evaluation** — read every time `_send_email` is called. Live-config-friendly.

### Failure path

`_send_email` is wrapped in `try/except: # noqa: BLE001` at line 105-107:

```python
except Exception as exc:  # noqa: BLE001
    logger.debug("email send failed: %s", exc)
    return False
```

**Silent swallow + debug log** (per Report 0024 — debug suppressed in production at INFO level).

### Sister: Slack webhook

`_send_slack(webhook_url, text)` at line 110-124. Takes `webhook_url` as parameter (not env var). The webhook URL itself is stored in the `notification_configs` SQLite table per `_ensure_tables` line 27-39. **No SMTP-style env-var fallback.**

### Logging hygiene

| Failure | Logger call |
|---|---|
| SMTP not configured | `logger.debug("SMTP not configured; email skipped")` (line 86) |
| Email send raised | `logger.debug("email send failed: %s", exc)` (line 106) |
| Slack send raised | `logger.debug("slack send failed: %s", exc)` (line 123) |
| Digest build raised | `logger.debug("digest build failed: %s", exc)` (line 213) |

**All 4 failure paths log at DEBUG.** Per Report 0024 MR152, debug is silent in production. **Operators see nothing when emails fail.**

### Cross-codebase env-var sister: `RCM_MC_*`

Notifications uses unprefixed `SMTP_*` (industry-standard) — different from `RCM_MC_*` prefix used elsewhere (Report 0019). Inconsistency but standard names are usually preferable for SMTP.

### What's NOT here

- **No `SMTP_FROM` override** — defaults to `SMTP_USER or "rcm-mc@noreply.local"` (line 93).
- **No `SMTP_TLS_REQUIRED`** — STARTTLS only fires on port 587 (line 99-100).
- **No `SMTP_TIMEOUT` override** — hardcoded 10s (line 97).
- **No SLACK env vars** — webhook URLs are per-config in DB.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR380** | **SMTP failure logged at DEBUG only** | Operators don't see email-send failures unless they enable DEBUG logging. Cross-link Report 0024 MR152. **Recommend: `logger.warning` for send failures.** | **High** |
| **MR381** | **`SMTP_PASS` could be logged via `%s` exception** | Line 106 logs `exc` — usually safe (smtplib doesn't echo password) but a future smtplib upgrade could include the username in error messages. **Recommend: explicit redaction.** Cross-link Report 0019 MR148. | Medium |
| **MR382** | **STARTTLS only triggered on port 587** | Hardcoded check at line 99 `if port == 587: server.starttls()`. Some providers use port 465 (SMTPS implicit TLS) or 25 with STARTTLS. **Hardcoded port-test is fragile.** | Medium |
| **MR383** | **Email "From" defaults to `rcm-mc@noreply.local`** | If neither SMTP_USER nor SMTP_FROM set, email is from a non-routable domain. Some receivers reject; some quarantine. | Low |

## Dependencies

- **Incoming:** `auth.audit_log` (likely; alerts trigger notifications), `alerts/`, scheduler.
- **Outgoing:** stdlib `smtplib`, `urllib.request`, `email.mime.*`. SMTP env vars (4). PortfolioStore for notification_configs table.

## Open questions / Unknowns

- **Q1.** Does any caller of `dispatch_to_configs` log dispatch failures at higher than DEBUG?
- **Q2.** Are credentials redacted in any logger.exception path that touches notifications?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0050** | **Error handling audit** (already requested as iteration 50). | Pending. |
| **0051** | **Security spot-check** (already requested as iteration 51). | Pending. |

---

Report/Report-0049.md written. Next iteration should: error-handling audit on `infra/notifications.py` (4 try/except blocks, all logger.debug-only) — closes MR380 escalation question.

