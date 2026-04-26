# Report 0085: Integration Point — `infra/rate_limit.py`

## Scope

Audits the never-before-mapped brute-force backstop. Closes Report 0021 MR163 + Report 0084 MR470.

## Findings

### Module shape

- **Path:** `RCM_MC/rcm_mc/infra/rate_limit.py`
- **Lines:** 57 (whole file)
- **Imports:** stdlib only (`threading`, `time`, `typing.Dict/Tuple`)
- **Surface:** one class `RateLimiter`, three methods (`__init__`, `check`, `reset`)

### Module docstring (verbatim)

> "Used by endpoints we don't want partners hammering — principally `/api/data/refresh/<source>` where each call may spin up a real CMS download. Fails open on process restart (limits are in-memory) — we accept that because the worst case is one extra refresh, not a security breach."

**Self-disclosed scope:** data refresh, NOT auth login. Per Report 0084 the auth path needs brute-force defense; this module is **not** what guards it.

### `RateLimiter.__init__(*, max_hits, window_secs)`

Keyword-only (good). Casts to `int` — silent if a float passed.
State: `self._log: Dict[str, list]` (per-key timestamp list) + `threading.Lock`.

### `RateLimiter.check(key) -> Tuple[bool, float]`

Sliding-window algorithm:
1. `cutoff = now - window_secs`
2. Drop expired timestamps from per-key log (in-place via slice)
3. If `len(log) >= max_hits`: return `(False, oldest+window-now)` (seconds-until-allowed)
4. Else append `now`, return `(True, 0.0)`

Lock held during the entire critical section. Correct for `ThreadingHTTPServer` per CLAUDE.md.

### `RateLimiter.reset(key="")` — test-only

Empty key clears all keys. Used for test isolation.

### Usage sites (need server.py grep)

The module docstring claims `/api/data/refresh/<source>`. Per Reports 0018 + 0019 server.py is 11K+ lines. **No grep done in this iteration to confirm all consumer sites.** Q1 below.

### Failure modes

| Mode | Behavior |
|---|---|
| Process restart | `_log` cleared, all keys reset (fail-open by design) |
| Memory leak | Per-key keys never deleted (only their timestamps trimmed). High-cardinality key (e.g. per-IP) over months → unbounded `Dict` |
| Thundering herd | All-or-nothing window: at boundary, all callers in `(oldest+window)` window get unlocked simultaneously |
| Wall-clock skew | Uses `time.time()` (wall clock); a backwards jump could expire entries falsely or grant excess hits |

### Cross-module assumptions

- **Caller-supplied key** — module trusts caller to choose meaningful keys. Per-IP vs. per-user vs. per-(user,source) all valid; choice deferred to server.py.
- **No persistence** — accepted per docstring.
- **No HTTP semantics** — module returns `(bool, float)`; caller emits HTTP 429 / `{"error": "rate_limited"}`.
- **No logger** — silent. Per Report 0024 logging cross-cut, this means rate-limited refusals don't show up in server logs unless the caller logs them.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR473** | **Module is data-refresh-only by design — auth path is unprotected by it** | Closes Report 0084 MR470 partially: rate_limit.py exists and is fine; but it is NOT wired to `/login` / `/api/login`. The brute-force concern in Report 0021 MR163 is **not** addressed here. | **High** |
| **MR474** | **Unbounded `_log` key dict** | Long-lived process with high-cardinality keys (per-IP) leaks memory. No eviction. | Medium |
| **MR475** | **No login-path rate-limit anywhere** | Until verified by grep, assume `/login` accepts unlimited attempts up to whatever Report 0021 MR163 `secrets.compare_digest` overhead permits (~1ms/attempt). | **Critical** (if grep confirms) |
| **MR476** | **Wall-clock-time-based** | NTP step backwards could invalidate trimming. | Low |
| **MR477** | **Silent — no logger** | Rate-limit refusals invisible without caller-side logging. | Low |
| **MR478** | **No per-test reset wired into conftest.py** | If tests instantiate a singleton limiter, cross-test pollution. | Low |

## Dependencies

- **Incoming:** server.py (claimed by docstring; not verified site-by-site this iteration). Possibly `data/sources` cron paths.
- **Outgoing:** stdlib only.

## Open questions / Unknowns

- **Q1.** **Which exact server.py routes call RateLimiter?** `grep -n "RateLimiter\|rate_limit" RCM_MC/rcm_mc/server.py` not run this iteration.
- **Q2.** **Is `/login` rate-limited at all?** CLAUDE.md says "rate-limited login" but rate_limit.py says "data refresh only" — which is correct?
- **Q3.** **Limit values?** No defaults in the module — caller picks `max_hits` + `window_secs`.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0086** | Build / CI / CD (already requested). |
| **0087** | Schema / Type inventory (already requested). |
| **future** | Grep server.py for all RateLimiter call-sites + `/login` brute-force defense — closes Q1, Q2, MR475. |

---

Report/Report-0085.md written.
Next iteration should: BUILD / CI / CD — pick build aspect not in 0026/0033/0041/0046/0053/0056/0071/0083.
