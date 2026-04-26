# Report 0050: Error-Handling Audit — `infra/notifications.py`

## Scope

`infra/notifications.py` (219 lines) try/except sweep. Sister to Report 0049's env-var audit + Report 0020's packet_builder.py audit.

## Findings

### try/except sites (4 total)

| Line | Catch | Action |
|---|---|---|
| 96-107 | `try: ... except Exception as exc: # noqa: BLE001` | `_send_email`. Logger.debug + return False. |
| 119-124 | `try: ... except Exception as exc: # noqa: BLE001` | `_send_slack`. Logger.debug + return False. |
| 158-161 | `try: ... except json.JSONDecodeError: continue` | Inside `dispatch_to_configs` — typed-narrow on bad config JSON. Skips that config row. |
| 193-213 | `try: ... except Exception as exc: # noqa: BLE001` | `build_weekly_digest`. Logger.debug + falls through to summary line. |

**3 BLE001 + 1 typed-narrow.** All BLE001 sites log at debug only (cross-link Report 0024 MR152).

### Bare except check

`grep -nE "^[[:space:]]*except[[:space:]]*:"` returns empty. **No bare except.** Clean.

### Logger calls

Module uses Pattern B per Report 0024: `logger = logging.getLogger(__name__)` (line 22).

| Logger call | Level | Site |
|---|---|---|
| `logger.debug("SMTP not configured ...")` | debug | line 86 |
| `logger.debug("email send failed: %s", exc)` | debug | line 106 |
| `logger.debug("slack send failed: %s", exc)` | debug | line 123 |
| `logger.debug("digest build failed: %s", exc)` | debug | line 213 |

**4 logger calls — all DEBUG.** Production-silent. **Operators see nothing when notifications fail.** Same anti-pattern as Report 0020.

### `dispatch_to_configs` thread-fire-and-forget

Line 167: `threading.Thread(target=_do, daemon=True).start()`. **No exception capture from the thread.** If `send_notification` raises inside the thread, the exception is lost. **Daemon thread exits silently.**

### Per-pattern verdict

| Pattern | Count | Notes |
|---|---|---|
| Typed-narrow + recover | 1 | json.JSONDecodeError — correct |
| BLE001 + logger.debug + recover | 3 | All silent in production |
| BLE001 + silent (no logger) | 0 | None |
| Re-raise after logging | 0 | None |
| Daemon thread + no capture | 1 (line 167) | Silent failure mode |

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR384** | All 4 logger calls at DEBUG — failures invisible in production (cross-link MR152) | **High** |
| **MR385** | Daemon thread at line 167 has no exception capture — `send_notification` failures silently lost | **High** |
| **MR386** | `build_weekly_digest`'s outer try (line 193-213) wraps lazy import + entire packet-walk loop; failure midway loses partial state | Medium |
| **MR387** | No retry on email/Slack send. A 5xx response = single-shot failure | Medium |

## Dependencies

- **Incoming:** likely `alerts/`, scheduler, `tests/test_engagement.py`.
- **Outgoing:** stdlib smtplib + urllib.request; logger.

## Open questions / Unknowns

- **Q1.** Where does `dispatch_to_configs` get called from? Need cross-grep.
- **Q2.** Is the daemon-thread-no-capture pattern intentional (notifications must not block requests) or oversight?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0051** | **Security spot-check** (already requested). | Pending. |
| **0052** | **Cross-grep `dispatch_to_configs` callers** | Resolves Q1. |

---

Report/Report-0050.md written. Next iteration should: security spot-check on `infra/notifications.py` (already queued as iteration 51) — focus on credential handling in SMTP login + Slack URL persistence.

