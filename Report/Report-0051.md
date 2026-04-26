# Report 0051: Security Spot-Check — `infra/notifications.py`

## Scope

`infra/notifications.py` security audit. Sister to Reports 0021 (auth/auth.py) and 0049/0050 (this module's env vars + error handling).

## Findings

### Hardcoded secrets

`grep -nE "password\s*=\s*['\"]|secret\s*=\s*['\"]|api_key\s*=\s*['\"]"` — **none found.** Clean.

### SQL injection

5 SQL `execute()` sites (lines 30, 51-57, 67, 71, 50). All parameterized:

```python
con.execute(
    "INSERT INTO notification_configs "
    "(user_id, channel, config_json, events) "
    "VALUES (?, ?, ?, ?)",
    (user_id, channel, json.dumps(config), ",".join(events)),
)
```

**No f-string SQL.** Clean.

### Unsafe deserialization

| Pattern | Result |
|---|---|
| `eval(` / `exec(` | None |
| `pickle.` | None |
| `subprocess.` | None |
| `os.system(` | None |
| `yaml.load` (unsafe) | None |
| `json.loads(...)` | Lines 159 — used with `try/except json.JSONDecodeError` (Report 0050). Safe. |

**Clean.**

### Shell injection

No subprocess calls. **Clean.**

### Crypto / TLS

| Field | Status |
|---|---|
| SMTP TLS | STARTTLS on port 587 only (line 99-100). **Hardcoded port-test** — Report 0049 MR382. |
| Slack webhook | HTTPS by webhook-URL convention (Slack always returns `https://hooks.slack.com/...`). **No URL scheme validation** in code — could accept `http://` URL silently. |
| Slack URL stored as TEXT | In `notification_configs.config_json` (line 31-39). **Plaintext SQLite.** Same threat model as Report 0021/0025. |
| SMTP password handled | Via `os.environ.get("SMTP_PASS")` (Report 0049). Not stored in DB; only in process memory. |

### Input validation

| Input | Validator |
|---|---|
| `user_id, channel, events` (save_config line 45-59) | No validation — accepts any strings. |
| `channel` (send_notification line 135-143) | Only `"EMAIL"` and `"SLACK"` reach senders; others return False. **Allowlist by default**. |
| `webhook_url` (line 112) | Only checks `if not webhook_url:`. **No URL scheme / host validation.** |
| `to` (email recipient) | No format check. SMTP server rejects bad addresses but error is logged at debug. |
| `body_html` | No XSS guard — but body is rendered by email clients, not browsers. Lower risk than web. |

### Trust boundaries

The Slack webhook URL is **operator-supplied** via `save_config(...)` and persisted in `notification_configs`. An operator with DB write access can set a malicious webhook URL — but they already have full access (acceptable per local-deploy threat model, Report 0021).

### Specific concerns

| Issue | Risk |
|---|---|
| `webhook_url` is unvalidated and POSTed to with `urllib.request` | A malicious webhook URL could exfiltrate event data. Pre-merge: validate scheme==https + host whitelist (e.g. `hooks.slack.com`). |
| `payload` passed to `_send_slack` includes `json.dumps(payload, default=str)[:500]` (line 134) | Truncates to 500 chars; minor info-disclosure cap. |
| Email body includes raw `json.dumps(payload, indent=2, default=str)` (line 139) | If `payload` contains PHI (Report 0028 / 0030 enforcement gap), it goes out via email. **No PHI redaction in notification path.** |

### `payload` PHI exposure path

`dispatch_to_configs(store, event_type, payload)` is called from various event-fire sites. If `payload` carries deal data including PHI-like fields, the email body includes them verbatim. Combined with Report 0028 MR250 (no enforcement), **a `disallowed`-mode instance could still email PHI** if a deal carries PHI in its profile_json.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR388** | **Slack webhook URL not host-validated** | A malicious webhook URL set in DB exfiltrates events. Recommend: host whitelist (`hooks.slack.com`). | **High** |
| **MR389** | **Email body includes payload JSON without PHI redaction** | If event payload carries PHI, emails leak it. Cross-link Report 0028 MR250 / Report 0025 MR213. | **Critical** |
| **MR390** | **`urllib.request.urlopen` accepts any URL** | Combined with MR388, this is the egress path. No SSRF guard. | Medium |
| **MR391** | **`save_config` accepts any string for `user_id, channel, events`** | A typo'd `channel="email"` (lowercase) would store config but `send_notification` only matches `"EMAIL"` (uppercase). **Silent misconfig.** | Low |
| **MR392** | **No rate-limit on `dispatch_to_configs`** | A bug or attack that triggers many events spams configured destinations. | Medium |
| **MR393** | **Slack URL stored plaintext in SQLite** | Operator-side risk; standard for local-deploy threat model. | Low |

## Dependencies

- **Incoming:** alert/event firing sites (not yet enumerated).
- **Outgoing:** SMTP server, Slack webhook host, stdlib.

## Open questions / Unknowns

- **Q1.** Are deal profile_json fields ever passed as `payload` to dispatch? If yes, MR389 is reachable.
- **Q2.** How many notification configs typically exist per deployment?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0052** | **Circular import audit** (already requested). | Pending. |
| **0053** | **Audit alert/event firing sites** | Resolves Q1 / MR389. |

---

Report/Report-0051.md written. Next iteration should: circular import audit on `infra/` subsystem (already queued) — sister to Report 0022's analysis/ audit.

