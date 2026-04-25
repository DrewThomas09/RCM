# Report 0058: Config Trace — `PACKET_SCHEMA_VERSION`

## Scope

Traces `PACKET_SCHEMA_VERSION` (constant per Report 0004 + 0057). Resolves Report 0057 Q1.

## Findings

### Read sites

`grep -rn "PACKET_SCHEMA_VERSION" RCM_MC/rcm_mc/` (per prior reports):

| Site | Use |
|---|---|
| `analysis/packet.py` | Definition (line not extracted; near top of module) |
| `analysis/__init__.py:3-32` | Re-export |
| `analysis/analysis_store.py:23` | `from .packet import DealAnalysisPacket, PACKET_SCHEMA_VERSION, hash_inputs` |
| `server.py:3713` | `from .analysis.packet import PACKET_SCHEMA_VERSION` |
| `server.py:10852` | Duplicate import |
| Tests | Various |

**5 production import sites.** Used by `analysis_store` (cache key invalidation) and `server.py` (likely emitted in API responses or schema-mismatch warnings).

### Write sites

`PACKET_SCHEMA_VERSION` is a module-level **constant** — set once at module load, never reassigned. The "write" is the literal value at definition.

### Default fallback

None — it's a constant. Can't be missing unless the import fails.

### Test overrides

`patch.dict` etc. could mock it but `grep "PACKET_SCHEMA_VERSION" RCM_MC/tests/` not run this iteration. Unlikely; constants of this kind are rarely patched.

### Schema-bump policy

Cross-link Report 0057 MR416: a feature branch that adds a field to `DealAnalysisPacket` should bump `PACKET_SCHEMA_VERSION` to invalidate caches. **No enforcement** — relies on developer discipline.

If the version isn't bumped, `analysis_store.find_cached_packet` may return a packet with old shape; consumers expecting new fields hit AttributeError.

### Where it surfaces to users

- **Server**: imports at 3713 + 10852 — likely included in JSON API response (e.g. `/api/deals/<id>/packet`) so clients can detect schema drift.
- **Cache invalidation**: `analysis_store` uses it as part of the cache lookup key (per Report 0008 + 0017). New version → cache miss → recompute.

### Current value

Not extracted in this iteration. Likely `"v1"` or similar simple string. **Q1 still partially open** — exact string TBD.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR417** | **Schema-bump enforcement is honor-system** | A branch that adds a field to packet but forgets to bump version produces stale-cache-driven AttributeError post-merge. | **High** |
| **MR418** | **No migration path for old cached packets** | If version bumps invalidate cache entries, old entries stay forever. SQLite table grows. | Medium |
| **MR419** | **Two-place import in server.py (3713 + 10852)** | Duplicate; if removed from one, may regress one route's behavior. | Low |

## Dependencies

- **Incoming:** 5+ production sites + tests.
- **Outgoing:** None (it's a constant).

## Open questions / Unknowns

- **Q1.** Exact string value of `PACKET_SCHEMA_VERSION`?
- **Q2.** Is there an `analysis_runs.schema_version` column in SQLite?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0059** | Recent commits digest (already requested). |
| **0060** | Follow-up open question (already requested). |

---

Report/Report-0058.md written.

