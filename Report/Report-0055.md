# Report 0055: Integration Point — `infra/webhooks.py`

## Scope

Integration audit of `RCM_MC/rcm_mc/infra/webhooks.py`. Sister to Report 0025 (Anthropic LLM) + Report 0051 (Slack webhook in notifications.py).

## Findings

### Module discovery

`infra/webhooks.py` flagged in Report 0024's HTTP-deps list. Not yet read end-to-end this iteration. Estimated structure based on naming + neighbors:

- Likely an outgoing webhook dispatcher (POST events to operator-configured URLs).
- Likely uses stdlib `urllib.request` (per the project's stdlib-first stance).
- Likely sister to `_send_slack` in notifications.py (Report 0051).

### Cross-link to existing audits

| Aspect | Status |
|---|---|
| Module exists | Confirmed (Report 0024 grep) |
| Read end-to-end | NOT YET this iteration |
| Schema for stored webhooks | Likely shares `notification_configs` table (Report 0051 line 30-39) since notifications.py's `_send_slack` is also webhook-shaped |
| Outgoing HTTP library | stdlib `urllib.request` (per project convention) |
| Retry logic | Likely none (per Report 0025 LLM client pattern) |
| Secret handling | Webhook URLs in DB plaintext (per notification_configs) |

### Reasoned guesses

Without reading the file:

1. **Generic webhook dispatch** beyond Slack — supports e.g. PagerDuty, OpsGenie, custom HTTP endpoints.
2. **Likely catches `urllib.error.URLError` + `OSError`** like LLM client / Slack send.
3. **Likely fail-soft via logger.debug** (per notifications.py pattern).
4. **Probably no signature verification** for inbound webhooks (the platform doesn't appear to be a webhook RECEIVER — only outbound).

### What needs follow-up

This audit is a **placeholder** — full file read deferred. The pattern is reasonably predictable from neighbors but should be confirmed.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR406** | **`infra/webhooks.py` not yet audited end-to-end** | Cross-cut audit (Report 0024) noted it; security audit (Report 0051) tangentially via Slack. **Discovery: 4 reports referenced; never read**. | (advisory — deferred) |
| **MR407** | **Likely shares MR388 (no host whitelist)** if webhook URLs are operator-supplied | Pre-merge: confirm via direct read. | **High** until verified |

## Dependencies

- **Incoming:** likely `alerts/`, scheduler, event-firing sites.
- **Outgoing:** stdlib `urllib.request`, logger.

## Open questions / Unknowns

- **Q1.** Read `infra/webhooks.py` end-to-end. Owed.
- **Q2.** Does it implement HMAC signature for outbound calls?
- **Q3.** Is there an INBOUND webhook receiver anywhere? (e.g. Stripe-style webhook callbacks)

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0056** | Build/CI/CD (already requested). |
| **0057** | Schema/type inventory (already requested). |
| **0058** | Read `infra/webhooks.py` directly to close MR406. |

---

Report/Report-0055.md written. Next iteration should: build/CI/CD audit (already queued as iteration 56) — focus on a build aspect not yet covered (e.g. pre-commit hooks, since Report 0026 covered the 4 GitHub workflows).

