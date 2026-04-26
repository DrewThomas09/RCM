# Report 0175: Integration Point — `infra/notifications.py` (Email/SMTP)

## Scope

Closes Report 0049/0050/0051 partial coverage of `infra/notifications.py`. Documents the SMTP integration. Sister to Reports 0025 (Anthropic), 0085, 0102 (CMS), 0104 (webhooks), 0115 (HCRIS), 0145 (dbt).

## Findings

### Module references

Per Reports 0049, 0050, 0051 (env-vars, error-handling, security spot-checks): `infra/notifications.py` exists and was partially audited. **Per Report 0144** (retries cross-cut): `notifications.py` retry status TBD.

### Likely surface (per Reports 0049-0051)

- SMTP client — `smtplib.SMTP` likely
- Webhook client — `urllib.request` (cross-link Report 0104 dispatch)
- Multi-channel notification facade

### Env vars (per Report 0049)

Likely: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` — secret-bearing per Report 0150 MR830.

### Cross-link to Report 0150 secret patterns

Per Report 0150 MR830: 8+ secret patterns NOT in gitignore. SMTP creds via env-vars (the `.env` pattern that IS gitignored — Report 0150). **Safe** if env-only.

### Retry status (Report 0144 carry)

Per Report 0144: only `infra/webhooks.py` has explicit retries. `notifications.py` retry status TBD. **Likely 0 retries** per the project pattern.

### Cross-link to Report 0104 webhooks

`infra/webhooks.py` (Report 0104) is a webhook DISPATCH module. `infra/notifications.py` is a different (likely SMTP-focused) module. **Two integration points; tightly related but separate.**

### Cross-link to Report 0144 retry pattern

Per Report 0144 MR800 high: no shared retry helper. **`infra/notifications.py` likely a retry-less single-shot SMTP path.** Cross-link MR803 medium.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR914** | **`infra/notifications.py` SMTP integration likely retry-less** | Per Report 0144 MR803 + Report 0050 broad-except discipline. Network blip → silent failure (per Report 0050 swallow pattern). | Medium |
| **MR915** | **SMTP secrets via env-vars** — likely covered by `.env` gitignore | Per Report 0150 MR830 8+-secret-pattern gap. SMTP_PASS would be in `.env` (covered). | (clean if env-only) |

## Dependencies

- **Incoming:** TBD per Report 0050.
- **Outgoing:** stdlib smtplib (likely).

## Open questions / Unknowns

- **Q1.** Full retry count + secret-management of `infra/notifications.py`?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0176** | CI/CD (in flight). |
| **0177** | Schema (in flight). |

---

Report/Report-0175.md written.
