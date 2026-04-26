# Report 0132: Data Flow Trace — `Idempotency-Key` HTTP Header

## Scope

Traces the `Idempotency-Key` HTTP header from request entry through cache lookup, response storage, and eviction. Sister to Reports 0102 (data refresh POST), 0108 (login POST), 0114 (CSRF). Closes Report 0108 MR607 high — Idempotency-Key cache check before auth.

**Bonus closure**: parses other 4 `configs/*.yaml` files (Report 0131 Q1 + MR748).

## Findings

### CLOSURE: Other configs all parse cleanly

Per `python3 -c "import yaml; yaml.safe_load(open(<f>))"`:

| File | Status |
|---|---|
| `actual.yaml` | OK |
| `benchmark.yaml` | OK |
| `initiatives_library.yaml` | OK |
| `value_plan.yaml` | OK |
| `playbook.yaml` | **BROKEN** (Report 0131 MR744 critical) |

**Closes Report 0131 Q1 + MR748 medium.** Only playbook.yaml is broken — bug is isolated, not project-wide.

### Hop-by-hop trace of `Idempotency-Key`

#### Hop 1 — Request enters

Client sends:
```http
POST /api/<route> HTTP/1.1
Idempotency-Key: <uuid>
Content-Type: application/json
...
```

#### Hop 2 — `do_POST` reads header (server.py:10253)

```python
self._idempotency_key = self.headers.get("Idempotency-Key")
if self._idempotency_key:
    cached = _IDEMPOTENCY_CACHE.get(self._idempotency_key)
    if cached is not None:
        return self._send_json(cached)
```

**Cache check happens BEFORE the `path == "/api/login"` dispatch (line 10258).** Per Report 0108 MR607.

#### Hop 3 — `_IdempotencyCache` (server.py:54-71)

```python
class _IdempotencyCache:
    """Thread-safe LRU cache for idempotency keys. Prevents duplicate POSTs."""
    def __init__(self, max_keys: int = 1000) -> None:
        self._cache: Dict[str, Any] = {}
        self._lock = _threading.Lock()
        self._max = max_keys

    def get(self, key: str):
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, response: Any) -> None:
        with self._lock:
            if len(self._cache) >= self._max:
                oldest = next(iter(self._cache))
                del self._cache[oldest]
            self._cache[key] = response
```

**Module-level singleton** at line 72:
```python
_IDEMPOTENCY_CACHE = _IdempotencyCache()
```

#### Hop 4 — Cache write on successful response

`_send_json` (line 10189-10191):
```python
ikey = getattr(self, "_idempotency_key", None)
if ikey:
    _IDEMPOTENCY_CACHE.set(ikey, payload)
```

**Cache writes the JSON `payload`** (the dict body of the response). Headers (e.g., `Set-Cookie`) are NOT stored — they're sent separately via `self.send_header()`.

#### Hop 5 — Eviction (LRU)

When cache hits `max_keys=1000`:
```python
oldest = next(iter(self._cache))
del self._cache[oldest]
```

**Python 3.7+ dict preserves insertion order**, so `next(iter(...))` returns oldest insertion. Effectively FIFO eviction (not strict LRU — entries don't move on access). **Misnamed**: it's FIFO, not LRU.

#### Hop 6 — CORS preflight advertise

`server.py:10170`:
```python
self.send_header("Access-Control-Allow-Headers", "Content-Type, X-CSRF-Token, Idempotency-Key")
```

Browsers see `Idempotency-Key` in the allow-list and can include it in CORS-preflight POSTs. Cross-link Report 0114 MR641 (only 1 of 3 CORS sites includes Idempotency-Key — inconsistency).

### Cache properties

| Property | Value |
|---|---|
| Capacity | 1000 keys (hardcoded default, not configurable) |
| Persistence | NONE — process restart wipes |
| Expiration | NONE by time; only FIFO eviction at capacity |
| Thread-safety | YES via `threading.Lock()` |
| Eviction policy | FIFO (misnamed as LRU in docstring) |

### Cross-link to Report 0108 MR607 (CRITICAL)

Per Report 0108: "Idempotency-Key cached BEFORE auth check (line 10253-10257 vs 10258 dispatch)."

**Confirmed.** The flow:
1. `if self._idempotency_key:` (line 10254)
2. `cached = _IDEMPOTENCY_CACHE.get(...)` (line 10255)
3. `if cached is not None: return self._send_json(cached)` (line 10256-10257) — **EARLY RETURN**
4. Auth dispatch starts (line 10258)

**An UNAUTHENTICATED request with a known Idempotency-Key gets the cached response** — bypassing all auth, CSRF, rate-limit, route-handler logic.

### What an attacker gets

The cached payload is the JSON body. **Cookies (`Set-Cookie`) are NOT replayed** — those are set in `_route_login_post:14631+` after explicit auth, not via `_send_json`. So:

- ✓ JSON-payload replay: attacker gets the cached body verbatim (including any user IDs, deal IDs, success messages embedded in payload)
- ✗ Cookie replay: NO — cookies aren't in the cache; `_send_json` doesn't write Set-Cookie
- ✗ Side-effect replay: NO — the actual handler isn't invoked; just the cached payload returned

**Information leakage** but not session hijack. Severity downgrade vs Report 0108 MR607.

### MR607 RE-EVALUATION (this report's contribution)

Report 0108 MR607 was rated **High** based on assumed Set-Cookie replay risk. **This report downgrades to Medium**:
- Information leak: yes (cached JSON body returned to anyone with key)
- Session/cookie replay: no
- Side-effect replay: no

Still a real bug but less critical than the High classification.

### Cache-key collision risk

A `max_keys=1000` cache is **shared across all routes**. Idempotency-Key for `POST /api/users/create` and `POST /api/data/refresh/<source>` (Report 0102 hop 10) live in the same cache. An accidentally-reused UUID across routes silently returns the wrong response.

### Cross-link Report 0103 (job_queue idempotency)

Per Report 0103: `JobRegistry.submit_callable(*, idempotency_key=...)` — a SEPARATE idempotency mechanism for async jobs. **Two distinct idempotency systems**:
1. `_IDEMPOTENCY_CACHE` — in-memory FIFO at HTTP-handler level (this report)
2. `JobRegistry._jobs[].idempotency_key` — in-memory at job-queue level (Report 0103)

**Different scopes, different lifetimes, no shared logic.** Cross-link Report 0102 hop 10: data-refresh POST goes through both.

### Test coverage

`grep "Idempotency-Key\|_IDEMPOTENCY_CACHE" RCM_MC/tests/`: not run this iteration. **Q1 below.**

### Failure modes

| Mode | Behavior |
|---|---|
| Process restart | cache cleared, all keys reset |
| Capacity overflow (1001st key) | oldest entry evicted (FIFO) |
| Concurrent same-key writes | both cache writes succeed under lock; last-writer wins |
| Concurrent same-key reads | both reads return cached value (lock allows reader concurrency? — actually it serializes) |
| Bad payload type | `_send_json(cached)` may fail if payload is unexpected type |

### Cross-link to silent-failure pattern (Report 0131 MR747)

`_IdempotencyCache` does NOT log eviction. A high-traffic system at 1000+ keys per second would silently drop the oldest entries with no operator visibility. **Not strictly silent-failure** (the data isn't a failure), but the LRU/FIFO semantics are invisible.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR607-DOWNGRADE** | Report 0108 MR607 (Idempotency-Key before auth) downgraded from High to **Medium** | Information leak (cached JSON body returned to anyone with key); NO cookie or side-effect replay. | (correction) |
| **MR750** | **`_IdempotencyCache` named LRU but is actually FIFO** (no access-bumps insertion order) | Misleading. Either rename or fix the semantics. | Low |
| **MR751** | **`max_keys=1000` is hardcoded** | Not env-var-configurable. High-traffic deploys silently drop entries. | Medium |
| **MR752** | **Cache-key collision across all routes** | Single shared dict; accidentally-reused UUID returns wrong response. Should namespace by `(method, path)` or use a dedicated key derivation. | Medium |
| **MR753** | **No expiration by time** — only FIFO eviction at 1000-cap | An idle key sits forever (until process restart or 1000 newer keys arrive). | Low |
| **MR754** | **No logging on eviction or cache-hit** | Operators have no visibility into idempotency-cache effectiveness. | Low |
| **MR755** | **Cache check is BEFORE `_auth_ok` AND `_csrf_ok`** | Reports 0108 + 0114 both touched this. **Sequencing should be: auth → CSRF → idempotency check → handler.** | **Medium** |
| **MR748-CLOSED** | Other 4 configs/*.yaml parse cleanly | Closes Report 0131 Q1 + MR748. | (closure) |

## Dependencies

- **Incoming:** every authenticated POST/PUT/DELETE/PATCH request (with optional `Idempotency-Key` header).
- **Outgoing:** `_IDEMPOTENCY_CACHE` module singleton; stdlib `threading.Lock`.

## Open questions / Unknowns

- **Q1.** Are there tests asserting `Idempotency-Key` correctly returns cached response, AND tests verifying it doesn't bypass auth?
- **Q2.** Does any HTTP route explicitly OPT-OUT of idempotency caching? (E.g., `/api/login` shouldn't be cached.)
- **Q3.** What's the production traffic volume vs `max_keys=1000`? At 10 req/s, cache fills in 100s of activity.
- **Q4.** Is the cached payload byte-for-byte the response body, or a Python dict? (Per `_send_json` it's a dict; downstream `json.dumps` serializes per-call.)

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0133** | Schema-walk `generated_exports` (Report 0127 MR724 high — STILL pre-merge requirement, 6+ iterations carried). |
| **0134** | Read `cli.py` head (1,252 lines, 14+ iterations owed). |
| **0135** | Test coverage of `_IdempotencyCache` (closes Q1, Q2). |

---

Report/Report-0132.md written.
Next iteration should: schema-walk `generated_exports` table — pre-merge requirement (carried 6+ iterations now, blocking `feat/ui-rework-v3` merge per Report 0127 MR724).
