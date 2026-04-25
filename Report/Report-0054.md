# Report 0054: Cross-Cutting — Caching

## Scope

Audits caching as a cross-cutting concern. Sister to Report 0024 (logging cross-cut).

## Findings

### Cache mechanisms in the codebase

| Site | Type | Notes |
|---|---|---|
| `infra/cache.py` | TTL/lru cache wrapper | Per Report 0015 has 2 `# type: ignore` — adds attributes to a wrapped function. Functools-based. |
| `analysis/analysis_store.py:find_cached_packet` | DB-backed packet cache | Per Report 0008 — keyed by deal_id + input hash. |
| `ai/llm_client.py:llm_response_cache` | DB-backed LLM cache | Per Report 0025 — keyed by sha256(system + "\x00" + user) + model. **No TTL** (Report 0025 MR207). |
| `core/calibration.py` | YAML deep-copy via `yaml.safe_load(yaml.safe_dump(...))` | Per Report 0011 — not really a cache, but pattern-relevant. |
| Implicit Python sys.modules | All `from .X import Y` | Standard import caching. |

### `infra/cache.py` (per Report 0015)

Functools-based wrapper that adds `cache_clear` and `cache_info` attributes (lines 119-120). Single canonical cache primitive. **Centralized.**

### Cache TTL inconsistency

| Cache | TTL |
|---|---|
| `infra/cache.py` (perf TTL cache for /models/quality + /models/importance per Report 0029 commit `29da226`) | TTL configurable per call |
| `analysis/analysis_store` packet cache | Keyed by input hash (no TTL — recomputes on input change) |
| `ai/llm_client.py` response cache | **No TTL** despite README claiming "24 hours" (Report 0025 MR207 — critical) |

**Inconsistent TTL semantics.** Three independent caching layers, three different invalidation strategies.

### Cache invalidation

- `infra/cache.py`: `cache_clear()` method.
- `analysis/analysis_store`: input-hash keyed; new input = new key.
- `ai/llm_client`: **never invalidated**. (MR207.)

### Cross-cuts

| Cache | Layer | Production impact |
|---|---|---|
| infra/cache | Performance | TTL cache prevents recomputation of expensive UI panels |
| analysis_store | Idempotency | Packet build is deterministic; cache keyed by input hash |
| llm_response | Cost + latency | Identical prompts return cached response |

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR401** | **3 different caching layers, 3 different invalidation strategies** | Pre-merge: any branch that adds a 4th cache should adopt one of the existing patterns. | Medium |
| **MR402** | **`llm_response_cache` has no TTL** (cross-link Report 0025 MR207) | Stale responses persist forever. | **Critical** |
| **MR403** | **`infra/cache.py` `# type: ignore[attr-defined]` (Report 0015)** | The `cache_clear`/`cache_info` attribute injection is mypy-bypassed. A future static-analyzer upgrade may flag. | Low |
| **MR404** | **No cache-coherency model documented** | If two paths cache the "same" thing under different keys, drift is possible. | Medium |
| **MR405** | **No cache-purge admin endpoint** | Operators can't force-invalidate without restart. | Medium |

## Dependencies

- **Incoming:** route handlers using `@cached`, packet builder, LLM client.
- **Outgoing:** stdlib `functools`, SQLite (for the DB-backed caches).

## Open questions / Unknowns

- **Q1.** What's the cumulative cache-table size in production? (Per Report 0025 MR214 unbounded growth.)
- **Q2.** Do tests exercise cache invalidation paths?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0055** | Integration point (already requested). |
| **0056** | Build/CI/CD (already requested). |

---

Report/Report-0054.md written. Next iteration should: integration point on `infra/webhooks.py` (per Report 0024 list — sister to notifications.py + Slack webhook from Report 0051).

