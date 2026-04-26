# Report 0104: Documentation Gap — `infra/webhooks.py` Full Read

## Scope

Reads `RCM_MC/rcm_mc/infra/webhooks.py` (179 lines) end-to-end. Closes Report 0055 placeholder. Cross-link Reports 0024 (logging), 0093 MR503 (CLAUDE.md doc rot), 0091 (22+ unmapped tables).

## Findings

### Module docstring is good (7 lines, lines 1-8)

> "Webhooks: HMAC-signed event dispatch (Prompt 39). Events (`deal.created`, `analysis.completed`, `risk.critical`) fire from the server via `dispatch_event`. Each configured webhook URL receives a POST with a JSON body + an `X-RCM-Signature` header (HMAC-SHA256 of the body keyed on the webhook's secret). Three retries with exponential backoff on failure."

Includes 3 example event types + signing-mechanism + retry-policy. **Adequate module-level overview.**

### Function-level docstring inventory

| Line | Function | Docstring? |
|---|---|---|
| 25 | `_ensure_tables` | NONE |
| 54 | `_utcnow` | NONE |
| 60 | **`register_webhook`** | **NONE — public, undocumented** |
| 75 | **`list_webhooks`** | **NONE — public, undocumented** |
| 85 | **`delete_webhook`** | **NONE — public, undocumented** |
| 95 | `_sign` | NONE (private; acceptable) |
| 101 | `_deliver` | 1-line: returns `(status_code, error)` |
| 126 | `dispatch_event` | 4-line — adequate |

**3 of 4 public CRUD functions have ZERO docstrings.** Per CLAUDE.md "Docstrings explain *why*, not *what*" — the why is missing for register/list/delete. **Major documentation gap.**

### Schema discovery (closes Report 0091 #11 partially)

`_ensure_tables` (lines 25-51) creates **2 SQLite tables**, never previously schema-walked.

#### `webhooks` table (7 fields)

| Field | Type | Constraint | Note |
|---|---|---|---|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | NOT NULL | rowid |
| `url` | TEXT | NOT NULL | destination URL |
| `secret` | TEXT | NOT NULL | **HMAC secret — stored plaintext** |
| `events` | TEXT | NOT NULL | comma-separated event types |
| `active` | INTEGER | DEFAULT 1 | enable/disable |
| `created_at` | TEXT | NOT NULL | ISO-8601 |
| `description` | TEXT | (nullable) | optional |

#### `webhook_deliveries` table (8 fields)

| Field | Type | Constraint | Note |
|---|---|---|---|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | NOT NULL | rowid |
| `webhook_id` | INTEGER | NOT NULL | **NO FK — orphan-delivery risk** |
| `event_type` | TEXT | NOT NULL | e.g. `deal.created` |
| `payload_json` | TEXT | NOT NULL | full payload (could be large) |
| `status_code` | INTEGER | (nullable) | 0 = network failure; HTTP code otherwise |
| `attempts` | INTEGER | DEFAULT 0 | tracks retries |
| `delivered_at` | TEXT | (nullable) | ISO-8601 of last attempt |
| `error` | TEXT | (nullable) | exception message |

**No indexes on either table.** Same pattern as Report 0087 audit_events MR484.

### What's missing — concrete documentation needs

| Gap | What to add |
|---|---|
| **`register_webhook` docstring** | Args (url, secret, events list, description); validation: events must be lowercase dotted (e.g. `deal.created`); idempotency: no — duplicates allowed |
| **`list_webhooks` docstring** | Returns list-of-dicts with `id, url, events, active, created_at, description` (NOT secret — sensible omission, but document it) |
| **`delete_webhook` docstring** | Returns True if a row was deleted; orphans `webhook_deliveries` rows (Q1 below) |
| **Event-type registry** | No central list of valid event_type strings. Per docstring 3 examples, but full surface unknown. Cross-link Report 0087 MR483 (audit_events same issue). |
| **Consumer signature-verification doc** | The receiver needs to verify `X-RCM-Signature: sha256=<hex>`. **No external doc** explains this. Without it, integrators cannot validate. |
| **Retry-policy doc** | Module docstring says "exponential backoff" — `_deliver` uses `2 ** attempt` (1s, 2s, 4s waits). Total worst case ~7s per webhook. Not in docstring. |
| **Async-delivery thread-fanout doc** | `dispatch_event(async_delivery=True)` (default) fires one daemon thread per webhook. **No semaphore.** Could spawn 100+ threads if 100 webhooks registered. |
| **CLAUDE.md cross-reference** | Per Report 0093 MR503: webhooks not mentioned in architecture diagram. |

### Code-quality observations beyond docstrings

| Line | Issue | Severity |
|---|---|---|
| 32 | `secret TEXT NOT NULL` — stored plaintext | **High security** |
| 42 | `webhook_id INTEGER NOT NULL` — no FK to `webhooks(id)` | Medium |
| 118 | `except Exception` with `noqa: BLE001` — swallows network errors | acceptable per pattern |
| 172-173 | `except Exception: pass` swallows delivery-record write failures | **High** — bug hidden |
| 175-176 | `threading.Thread(...).start()` — no thread limit | Medium |
| 159-176 | `_do_deliver` defined inside loop with default-arg captures | acceptable Python idiom |

### Closure default-arg pattern (line 159)

```python
def _do_deliver(wh_id=wh_id, url=url, sig=sig):
```

This is the **standard Python workaround** for late-binding closures inside `for` loops. Necessary; not a bug. But a comment explaining why would help.

### Test coverage

`grep "test.*webhook" RCM_MC/tests/`: not run this iteration. Q2.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR575** | **3 of 4 public CRUD functions undocumented** (`register_webhook`, `list_webhooks`, `delete_webhook`) | Onboarding friction; signature validation, idempotency, etc. all unstated. | Medium |
| **MR576** | **Webhook secrets stored plaintext in SQLite** | Cross-link Report 0030 PHI security. If portfolio.db is exfiltrated, attacker can sign forged webhook payloads. Should use `auth.scrypt`-style hashing or symmetric encrypt-at-rest. | **Critical** |
| **MR577** | **`webhook_deliveries.webhook_id` has NO FK to `webhooks.id`** | Orphan deliveries persist when a webhook is deleted. Eventually deliveries stop being join-able to source URL. | Medium |
| **MR578** | **`_do_deliver` line 172-173 silently swallows ALL exceptions writing to `webhook_deliveries`** | Lost-write bug hidden. Per Report 0024 cross-cut: `logger.warning(...)` should at minimum log. | **High** |
| **MR579** | **Unbounded thread fanout in `dispatch_event(async_delivery=True)`** | One daemon thread per matching webhook. 100 webhooks → 100 threads. No semaphore. | Medium |
| **MR580** | **No event-type registry** | Same pattern as Report 0087 MR483 (audit_events.event_type) and Report 0102 MR560 (hospital_benchmarks.metric_key). Three free-form text fields where a typo silently breaks routing. **Project-wide pattern.** | **High** |
| **MR581** | **`webhook_deliveries.payload_json` has no size cap** | A large analysis-complete payload could persist megabytes. No truncation, no compression. | Low |
| **MR582** | **`attempts INTEGER DEFAULT 0` but `_deliver` always inserts `1`** | Per line 169: `attempts, delivered_at, error VALUES (..., 1, ...)`. Even after 3 retries, `attempts=1` is recorded. **Bug — undercount.** | **Medium** |
| **MR583** | **No webhook-level rate limit** | Cross-link Report 0085: data-refresh has limit, auth doesn't, webhooks don't. A misbehaving consumer could be hammered without circuit-breaker. | Medium |
| **MR584** | **CLAUDE.md doesn't mention `infra/webhooks.py`** | Cross-link Report 0093 MR503 + Report 0103 MR574. Doc rot deepens. | Medium |

## Dependencies

- **Incoming:** server.py (probable — fires events on deal/analysis state changes), tests (TBD).
- **Outgoing:** stdlib only (`hashlib`, `hmac`, `json`, `logging`, `threading`, `urllib.request`, `datetime`, `typing`). Per Report 0024 + Report 0095 stdlib-only invariant: confirmed for this module.

## Open questions / Unknowns

- **Q1.** Does `delete_webhook` cascade to `webhook_deliveries`? Per code: no — orphan deliveries persist.
- **Q2.** Are there tests in `tests/test_webhooks.py` or similar?
- **Q3.** What is the **complete event-type registry** that's actually fired? `grep "dispatch_event(" RCM_MC/rcm_mc/`?
- **Q4.** Is the `secret`-plaintext-storage decision documented anywhere? (CLAUDE.md says scrypt for passwords; nothing about webhook secrets.)
- **Q5.** Is MR582 (attempts always 1) a real bug or is the schema field unused / misnamed?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0105** | Schema-walk `data_source_status` (carried from Report 0102 Q2). |
| **0106** | Grep `dispatch_event` call-sites (closes Q3 + bounds the event-type registry). |
| **0107** | Read `tests/test_webhooks.py` if exists (closes Q2). |
| **0108** | Bug-fix PR for MR582 + MR578 (concrete remediation work). |

---

Report/Report-0104.md written.
Next iteration should: schema-walk `data_source_status` table (sibling to `hospital_benchmarks` per Report 0102, still owed).
