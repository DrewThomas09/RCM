# Report 0025: Integration Point — Anthropic LLM API

## Scope

This report covers the **Anthropic API integration** in `RCM_MC/rcm_mc/ai/llm_client.py` (241 lines) on `origin/main` at commit `f3f7e7f`. The audit includes:

- The HTTP client construction.
- Authentication / secret management.
- Error handling and retry posture.
- Caching layer (`llm_response_cache` SQLite table).
- Cost-tracking layer (`llm_calls` SQLite table).
- Adjacent callers and UI surfaces.

This is the project's **only external HTTP integration to a third-party API** (per `RCM_MC/pyproject.toml`'s no-fastapi-on-the-default-install posture and the stdlib-only HTTP convention). The SMTP integration in `infra/notifications.py` (Report 0019 MR148) is sister territory.

Prior reports reviewed before writing: 0021-0024.

## Findings

### Module shape

- `RCM_MC/rcm_mc/ai/llm_client.py` — **241 lines**.
- Outgoing imports: stdlib only (`hashlib`, `json`, `logging`, `os`, `time`, `urllib.request`, `urllib.error`, `dataclasses`, `datetime`, `typing`). **Zero third-party HTTP libs**.
- Logger: `logger = logging.getLogger(__name__)` (line 25 — Pattern B per Report 0024).
- Public API: `LLMResponse` dataclass + `LLMClient` class with `is_configured` property and `complete(system_prompt, user_prompt, *, model, max_tokens, temperature)` method.

### Endpoint configuration

| Field | Value | Site |
|---|---|---|
| API endpoint | `https://api.anthropic.com/v1/messages` | line 41 (`_API_URL`) |
| HTTP method | `POST` | line 200 |
| Library | stdlib `urllib.request` | line 192-201 |
| Timeout | **60 seconds** | line 205 (`urlopen(req, timeout=60)`) |
| Auth header | `x-api-key: <key>` | line 196 |
| Anthropic-version header | **`"2023-06-01"`** | line 197 |
| Content-type | `application/json` | line 198 |
| Request body | JSON-encoded Messages API request | line 184-190 |

### Anthropic-version pin — old

`anthropic-version: 2023-06-01` (line 197) is the **earliest stable Messages-API version**. Newer features (extended thinking, computer-use, fine-grained tool use, prompt caching headers, etc.) require newer date-stamped versions (e.g. `2024-...`). Pinning to the original 2023 version means **the client cannot use any post-2023 capability** — even though the underlying models (`claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5`) post-date that header.

The pin is defensible (avoids accidental breaking changes) but **forecloses optimization**. For example, `prompt-caching` would reduce cost on repeated `system_prompt` calls — unavailable with this header version.

### Authentication / secret management

**API-key source:** `os.environ.get("ANTHROPIC_API_KEY", "")` (line 147).

| Aspect | Status |
|---|---|
| Storage | env var only — no file-based config, no keyring, no HashiCorp Vault, no AWS Secrets Manager |
| In-memory persistence | `self._api_key = ...` instance attribute (line 147). **Readable via debugger / repr / any reference to the `LLMClient` instance.** |
| Logging | API key never logged inside `llm_client.py`. ✓ |
| Empty-key fallback | If env var missing → `is_configured = False` → `complete()` returns `LLMResponse(text="[LLM not configured]", model="fallback")` (lines 170-174). **No exception raised; caller must check return value.** |
| Refresh / rotation | API key captured at `__init__` only. **If `ANTHROPIC_API_KEY` is rotated mid-process, the existing `LLMClient` keeps using the old key.** Caller must construct a new instance. |
| Display in UI | Per Report 0024 sweep: `ui/settings_ai_page.py:42` reads the env var (`key = os.environ.get("ANTHROPIC_API_KEY") or ""`) — possibly displayed on a settings page. **Not yet verified for redaction.** |
| Validation of key format | None. Truthy check only (line 152). `ANTHROPIC_API_KEY=placeholder` reads as `is_configured = True`; the actual API call then 401s and the client returns `[LLM call failed]`. (Cross-link Report 0019 MR143.) |

**Real Anthropic keys begin with `sk-ant-`. The codebase does NOT enforce this format anywhere — making misconfiguration silent.**

### Error handling — single try, no retries

Lines 203-212:

```python
t0 = time.monotonic()
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
    logger.warning("LLM call failed: %s", exc)
    return LLMResponse(
        text="[LLM call failed]",
        model=model,
    )
latency = (time.monotonic() - t0) * 1000
```

| Aspect | Status |
|---|---|
| Catch list | `urllib.error.URLError`, `urllib.error.HTTPError`, `OSError` — covers network errors, HTTP non-200s, socket timeouts. **`HTTPError` is a subclass of `URLError`, listing both is redundant but harmless.** |
| **JSON parse errors NOT caught** | Line 206 `json.loads(...)` is INSIDE the try block — protected. ✓ |
| **Other exceptions NOT caught** | A response with unexpected shape (e.g. `data.get("content", [])` returning non-list) would raise `TypeError` outside the try — propagates up to caller. |
| Retry policy | **None.** Single attempt. No exponential backoff, no rate-limit handling, no 429 detection. |
| Fallback response | `LLMResponse(text="[LLM call failed]", model=model)` — magic-string sentinel. Caller pattern: check `text == "[LLM call failed]"` or `model == "fallback"`. |
| Logging level | `logger.warning("LLM call failed: %s", exc)` — visible at default INFO level (Report 0024). ✓ |
| **Tracebacks logged?** | **No.** Only `str(exc)` via `%s`. Per Report 0024 MR197, no `logger.exception` calls anywhere — including here. Post-mortem of an intermittent 503 cannot recover the traceback. |
| Token usage on failure | Not logged. Failed calls produce no `llm_calls` row. **A failure storm wouldn't show in cost-tracking dashboards.** |
| Idempotency on retry | Not relevant — no retries. But cache-on-success means a retry from the caller would hit the cache if the prompt hash matches. |

### Caching layer

**Tables:** `llm_calls` (line 62) and `llm_response_cache` (line 71).

`llm_calls` schema:

```sql
CREATE TABLE IF NOT EXISTS llm_calls (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    model         TEXT NOT NULL,
    input_tokens  INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd      REAL NOT NULL,
    called_at     TEXT NOT NULL
);
```

`llm_response_cache` schema:

```sql
CREATE TABLE IF NOT EXISTS llm_response_cache (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_hash   TEXT NOT NULL,
    model         TEXT NOT NULL,
    response_text TEXT NOT NULL,
    input_tokens  INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    created_at    TEXT NOT NULL,
    UNIQUE(prompt_hash, model)
);
```

Cache key: `prompt_hash = sha256(system_prompt + "\x00" + user_prompt)` per `_prompt_hash` at line 86-88.

**Lookup logic** (`_lookup_cache` at line 91-108):

```sql
SELECT response_text, input_tokens, output_tokens
FROM llm_response_cache
WHERE prompt_hash = ? AND model = ?;
```

**No `created_at` filter.** Cache entries are returned regardless of age.

But the README (Report 0024 grep) says: *"if an identical prompt hash has been called within the last 24 hours, returns the cached response"*. **The code contradicts the README.** Cache entries persist until the table is manually cleared; the 24-hour TTL is **not implemented**.

**Save logic** (`_save_cache` at line 111-121):

```python
"INSERT OR REPLACE INTO llm_response_cache "
"(prompt_hash, model, response_text, ...) "
"VALUES (?, ?, ?, ...)"
```

`INSERT OR REPLACE` overwrites existing rows on conflict (the `UNIQUE(prompt_hash, model)` constraint). So a re-run with the same prompt updates the timestamp — but again, no TTL is enforced.

### Cost tracking

`_estimate_cost` (line 136-138):

```python
def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = _COST_PER_1K.get(model, (0.001, 0.005))
    return (input_tokens / 1000) * rates[0] + (output_tokens / 1000) * rates[1]
```

**Rate table at lines 30-38** (per-1K tokens, in USD):

| Model | Input rate | Output rate |
|---|---:|---:|
| `claude-opus-4-7` | $0.015 | $0.075 |
| `claude-sonnet-4-6` | $0.003 | $0.015 |
| `claude-haiku-4-5-20251001` | $0.0008 | $0.004 |
| `claude-haiku-4-5` (alias) | $0.0008 | $0.004 |
| `claude-sonnet-4-20250514` (legacy alias) | $0.003 | $0.015 |
| `claude-opus-4-20250514` (legacy alias) | $0.015 | $0.075 |
| **Unknown model fallback** | **$0.001** | **$0.005** |

**Issue:** the unknown-model fallback (line 137) is a **dramatic underestimate** for any high-tier model. If a future caller passes `model="claude-opus-5-..."` (hypothetical), the rate table doesn't recognize it and returns ~5x lower than actual costs. **No warning is emitted; cost dashboards silently understate.**

**Per-call logging** (`_log_call` at line 124-133): every successful call writes one row to `llm_calls`. **Failures don't log.**

### Default model + invocation

```python
def complete(
    self,
    system_prompt: str,
    user_prompt: str,
    *,
    model: str = "claude-haiku-4-5-20251001",  # line 159
    max_tokens: int = 2000,
    temperature: float = 0.0,
) -> LLMResponse:
```

**Default model: Claude Haiku 4.5** — cheap + fast. Callers can opt up to Sonnet 4.6 or Opus 4.7.

**Default temperature: 0.0** — deterministic. Good for fact-checking.

**Default max_tokens: 2000** — modest. Fine for memo sections.

### Adjacent UI surfaces

`grep -rn "claude\.get" RCM_MC/rcm_mc/`:

| File:line | Use |
|---|---|
| `ui/chartis/partner_review_page.py:384-392` | Pulls `status, summary, model, latency_ms, cost_usd_estimate, confirmed_points, concerns` from a `claude` dict |
| `ui/chartis/red_flags_page.py:197-200` | Same pattern for "Claude review" |
| `ui/chartis/ic_packet_page.py:150-155` | Same pattern for IC packet |
| `ui/settings_ai_page.py:42, 209` | Reads `ANTHROPIC_API_KEY` env var directly + at line 193 displays `export ANTHROPIC_API_KEY="sk-ant-…"` instructional text |

**Pattern:** UI pages render a `claude` dict produced by some upstream call to `LLMClient`. Default `status` is `"not_configured"` and `model` is `"fallback"` — matches `LLMResponse` model "fallback" sentinel.

### Adjacent caller modules in `ai/`

`ls RCM_MC/rcm_mc/ai/` returns:

- `claude_reviewer.py`
- `conversation.py`
- `document_qa.py`
- `llm_client.py` (this module)
- `memo_writer.py`
- `__init__.py`
- `README.md`

`claude_reviewer.py`, `conversation.py`, `document_qa.py`, `memo_writer.py` are likely the 4 callers that use `LLMClient.complete(...)`. Not yet read in this iteration.

### What's missing

| Capability | Status |
|---|---|
| Streaming responses | **Not implemented.** Uses non-streaming Messages API. UI can't show progressive output. |
| Multi-turn conversation | **Not implemented.** `messages` list contains one entry only (line 189). Caller must concatenate history into the user prompt. |
| Tool use / function calling | **Not implemented.** Body has no `tools` field. |
| Prompt caching (Anthropic-side) | **Not implemented.** Would require `anthropic-version: 2024-...` and a `cache_control` block in messages. (Cross-link Q on `anthropic-version` pin.) |
| Vision / multimodal | **Not implemented.** Body has no image blocks. |
| Extended thinking | **Not implemented.** Would require post-2024 anthropic-version. |
| Request-ID propagation | **Not implemented.** No correlation between Anthropic's server-side logs and the local `llm_calls` table. |
| Rate-limit handling | **Not implemented.** No 429 detection, no `Retry-After` header parsing. |
| Token-budget enforcement | **Not implemented.** Caller can pass `max_tokens=...` but the client doesn't enforce a daily cost ceiling. |

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR207** | **Cache TTL claimed in README but NOT implemented** | README says "within the last 24 hours" but `_lookup_cache` (line 94-98) has no `created_at` filter. Cache entries are returned regardless of age. **Stale responses can persist indefinitely.** Pre-merge: any branch that adds time-sensitive prompts (e.g. "summarize this week's deals") will silently reuse months-old responses. | **Critical** |
| **MR208** | **`anthropic-version: 2023-06-01` forecloses Anthropic's modern features** | Prompt caching, extended thinking, computer-use, fine-grained tool use all require newer headers. **Recommend bumping to `2024-...` after testing — but coordinate with the call sites that depend on the response shape (which has stayed compatible).** | Medium |
| **MR209** | **No retry / no backoff / no rate-limit awareness** | A 429 response → `urllib.error.HTTPError` → caught → `[LLM call failed]` returned. **A burst of failed calls under rate-limiting silently degrades the entire AI layer.** Recommend: implement exponential backoff with jitter on 429 + 5xx, with a max-retry-count. | **High** |
| **MR210** | **API key captured at `__init__` only — rotation requires reconstruction** | `self._api_key` is set once. If the operator rotates `ANTHROPIC_API_KEY` mid-process, the existing client uses the old key. **Pre-merge: any branch that adds an "AI Settings" UI page that mutates env vars must construct a new LLMClient.** | Medium |
| **MR211** | **No format validation for `ANTHROPIC_API_KEY`** | Real keys start with `sk-ant-`. Empty string or random text passes the truthy check at line 152, then 401s at the API. **Misconfiguration is silent until first call.** Recommend: validate prefix at construction; log warning on mismatch. | Medium |
| **MR212** | **Unknown-model cost-rate fallback dramatically underestimates** | Line 137 `(0.001, 0.005)` is roughly Haiku-tier. A future model (Opus 5, Claude Plus) would log at 1/15th the actual cost. **Cost dashboards lie.** Recommend: emit a logger.warning when the model is missing from `_COST_PER_1K`. | **High** |
| **MR213** | **`response_text` cached verbatim in plaintext SQLite** | Includes potentially sensitive deal-derived prompt content. Anyone with read access to `portfolio.db` can read every cached LLM response. **Consistent with the local-deploy threat model** (Report 0021 MR165) but a remote-deploy branch needs encryption. | Medium |
| **MR214** | **Cache table grows unbounded** | No TTL, no maintenance pass deletes old rows. After 6 months of use, `llm_response_cache` could be 100s of MB. **No vacuum / prune / max-size logic.** | Medium |
| **MR215** | **Magic-string sentinel for failure** | Caller checks `text == "[LLM call failed]"` or `model == "fallback"`. A future change to either string silently breaks every caller's "did the LLM work?" branch. **Recommend: an `is_fallback: bool` field on `LLMResponse`.** | Medium |
| **MR216** | **No traceback logged on failure** (cross-link Report 0024 MR197) | `logger.warning("LLM call failed: %s", exc)` drops the traceback. Diagnosing a chronic 503 is harder than necessary. | Medium |
| **MR217** | **`_lookup_cache` ignores `created_at`** | Combined with the unbounded cache (MR214), a prompt rewrite that produces the same hash returns a stale response. The hash is `sha256(system + "\x00" + user)` — semantically-identical prompts with whitespace differences hash differently. Acceptable in practice. | Low |
| **MR218** | **Settings page may display the API key** | `ui/settings_ai_page.py:42` reads it; line 193 has placeholder text `sk-ant-…`. Pre-merge: read this file end-to-end to confirm the actual rendered key is redacted (e.g. `sk-ant-***...***last4`) and never echoed in full. | **High** until verified |
| **MR219** | **No streaming = UI can't show progressive output** | For the IC-memo generation path, a 60-second wait for the full response feels slow. Recommend implementing streaming when bumping `anthropic-version`. | Low |
| **MR220** | **No request-ID propagation** | The `anthropic-request-id` response header (which Anthropic returns) is not captured. Forensic correlation with Anthropic's server logs (e.g. for a billing dispute) is impossible. | Low |
| **MR221** | **No daily-cost ceiling** | A bug or accidental loop could call `LLMClient.complete()` repeatedly. **No budget control.** Recommend: query `llm_calls` for today's `cost_usd` sum at construction and refuse if over a configurable ceiling. | Medium |

## Dependencies

- **Incoming (callers of `LLMClient.complete`):** `ai/claude_reviewer.py`, `ai/conversation.py`, `ai/document_qa.py`, `ai/memo_writer.py` (plus their consumers — likely server.py routes that render the chartis IC packet, partner-review page, red-flags page).
- **Outgoing:** stdlib only (`urllib.request`, `urllib.error`, `json`, `hashlib`, `logging`, `os`, `time`, `dataclasses`, `datetime`, `typing`); `PortfolioStore` from `..portfolio.store` (passed as `store=` kwarg); the **public Anthropic Messages API** at `https://api.anthropic.com/v1/messages`.

## Open questions / Unknowns

- **Q1 (this report).** Does `ui/settings_ai_page.py` redact the API key before display, or is it shown in full? (MR218.)
- **Q2.** Where do the 4 sister modules in `ai/` (`claude_reviewer.py`, `conversation.py`, `document_qa.py`, `memo_writer.py`) call `LLMClient.complete`? With what default model? With what user-data — could it leak PHI / deal-secret content?
- **Q3.** Is the `anthropic-version: 2023-06-01` header pinned for a deliberate reason, or is it just historical? Bumping to `2024-...` may be safe.
- **Q4.** What's the actual production size of the `llm_response_cache` table? `SELECT COUNT(*), SUM(LENGTH(response_text)) FROM llm_response_cache` would tell.
- **Q5.** Are there tests for the no-key fallback path (`[LLM not configured]`)? For the failure path (`[LLM call failed]`)? `pytest -k "llm"` would surface.
- **Q6.** Has any feature branch added prompt-caching, streaming, or tool-use to this client?
- **Q7.** Is `RCM_MC_PHI_MODE` (Report 0019 MR147) consulted before sending prompt content to the LLM? If `PHI_MODE=on`, the LLM call should be gated.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0026** | **Read `ui/settings_ai_page.py`** end-to-end — verify API key redaction. | Resolves Q1 / MR218. |
| **0027** | **Audit the 4 caller modules in `ai/`** — what prompts do they construct? With what user data? | Resolves Q2; potential PHI leak audit. |
| **0028** | **Audit `RCM_MC_PHI_MODE`** — owed since Report 0019. | Resolves Q7. |
| **0029** | **Audit `infra/notifications.py`** SMTP integration — sister external integration. | Companion. |
| **0030** | **Audit `infra/webhooks.py`** — also surfaced in Report 0024's HTTP-deps list. | Sister integration. |
| **0031** | **Trace `data/_cms_download.py`** — CMS public-data downloader, sister HTTP integration. | Companion. |
| **0032** | **Implement TTL or max-rows for `llm_response_cache`** | Mitigates MR207 + MR214. |

---

Report/Report-0025.md written. Next iteration should: read `ui/settings_ai_page.py` end-to-end and verify the `ANTHROPIC_API_KEY` is redacted before display — closes MR218 (potential secret-display risk) here and is the simplest remaining security-spot-check from the AI layer.

