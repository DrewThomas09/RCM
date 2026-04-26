# Report 0148: Config Trace — `analysis_runs.hash_inputs` (+ closes Report 0118 MR678 medium)

## Scope

Traces `hash_inputs` — the cache-invalidation key for `analysis_runs` table. **Closes Report 0118 MR678 medium** (analysis_runs FK status). Sister to Reports 0057 (DealAnalysisPacket schema), 0058 (PACKET_SCHEMA_VERSION), 0077 (analysis_runs initial), 0123 (audit_events cross-correction), 0134 (deal_overrides), 0147 (users + sessions).

## Findings

### CLOSES Report 0118 MR678 + carries from Reports 0137, 0147

**`analysis_runs.deal_id` HAS an FK with `ON DELETE CASCADE`** (per `analysis_store.py:47-48`).

```sql
CREATE TABLE IF NOT EXISTS analysis_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT NOT NULL,
    scenario_id TEXT,
    as_of TEXT,
    model_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    packet_json BLOB NOT NULL,
    hash_inputs TEXT NOT NULL,
    run_id TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
        ON DELETE CASCADE
)
```

Plus 2 indexes:
- `idx_analysis_runs_hash ON (deal_id, hash_inputs)` — cache lookup
- `idx_analysis_runs_deal ON (deal_id, created_at)` — listing

**Report 0077 MISSED**: the FK + both indexes + the full 10-field schema. **Cross-correction.**

### Updated FK frontier — COMPLETE

| Table | FK target | ON DELETE |
|---|---|---|
| `analysis_runs.deal_id` | deals(deal_id) | **CASCADE** |
| `mc_simulation_runs.deal_id` | deals(deal_id) | **CASCADE** |
| `deal_overrides.deal_id` | deals(deal_id) | **CASCADE** |
| `generated_exports.deal_id` | deals(deal_id) | **SET NULL** |
| `sessions.username` | users(username) | **(unspecified — NO ACTION default)** |

**5 FK-bearing tables, 3 distinct cascade behaviors.** Cross-correction to Report 0118 PRAGMA comment (which listed 4 tables; missed sessions). All FK frontier questions now closed.

### `hash_inputs` config trace

#### Definition site

`analysis/packet.py:1243-1280+ hash_inputs(...)`:

```python
def hash_inputs(
    *,
    deal_id: str,
    observed_metrics: Dict[str, Any],
    scenario_id: Optional[str] = None,
    as_of: Optional[date] = None,
    profile: Optional[Dict[str, Any]] = None,
    analyst_overrides: Optional[Dict[str, Any]] = None,
) -> str:
    """Deterministic SHA256 over canonical input JSON."""
    payload = {
        "deal_id": str(deal_id),
        "scenario_id": scenario_id,
        "as_of": as_of.isoformat() if as_of else None,
        "observed_metrics": {...},
        "profile": _clean(profile or {}),
        "analyst_overrides": {...},
    }
```

**Inputs (6 components)**:
1. `deal_id` (per Report 0017)
2. `observed_metrics` dict
3. `scenario_id` optional
4. `as_of` date optional
5. `profile` dict optional (hospital profile per Report 0093 ml/comparable_finder)
6. `analyst_overrides` dict optional (per Report 0134 deal_overrides)

**Output**: hex SHA-256 string.

**`sort_keys=True`** ensures determinism (per docstring lines 1261-1262).

#### 5+ readers (importers)

Per `grep "hash_inputs"` (excluding packet.py):

| File | Use |
|---|---|
| `analysis/__init__.py` | re-export |
| `analysis/analysis_store.py` | line 23 import; idx_analysis_runs_hash uses it as cache key |
| `analysis/packet_builder.py` | computes via `hash_inputs(...)` at packet-build time |
| `analysis/refresh_scheduler.py` (Report 0111) | likely re-hashes for staleness detection |
| `analysis/deal_overrides.py` (Report 0134) | overrides feed into hash → cache miss on change |
| `server.py` | likely API exposure |
| `diligence/ingest/ccd.py` | possibly different hash for ingest? Q3 |

**Cache write site**: `analysis_store.py` (per Report 0008 + 0080) — INSERT row with `hash_inputs` column.

**Cache read site**: `find_cached_packet` (Report 0080 + 0081 partial) — `SELECT * FROM analysis_runs WHERE deal_id = ? AND hash_inputs = ?`.

#### Default fallback

`hash_inputs` requires kwargs. **No defaults at config-level.** Default behavior: missing `analyst_overrides` → empty dict → hash includes `{}` rather than `{...overrides...}`. **Different hash for empty overrides vs unsupplied overrides.** Q1 below.

#### Test overrides

Tests likely call `hash_inputs(...)` with synthetic dicts. `grep "hash_inputs(" tests/`: not run this iteration.

#### What forces cache invalidation

| Change | Cache invalidates? |
|---|---|
| `observed_metrics[denial_rate] = 0.07 → 0.08` | YES |
| `analyst_overrides["bridge.exit_multiple"] = 11.0` | YES (per Report 0134 docstring) |
| `profile.bed_count = 100 → 200` | YES |
| `as_of = 2025-01-01 → 2025-02-01` | YES |
| **`PACKET_SCHEMA_VERSION` bump** (Report 0058) | NO — different field; bumps via separate honor-system mechanism |

**Cache-miss does NOT happen on schema bump.** Cross-link Report 0058 MR417 (high — "honor-system schema bump"). **Hash includes inputs but NOT the version of the packet shape.**

**MR823 below.**

#### `model_version` field (cross-link Report 0058)

`analysis_runs.model_version TEXT NOT NULL` is a SEPARATE field from `hash_inputs`. **Likely stores `PACKET_SCHEMA_VERSION` value at row-write time.** Cross-link Report 0058: a future cache lookup that filters by `model_version = current_version` would force schema-driven invalidation. **Not currently done** (per Report 0080 lookup uses only `hash_inputs`).

### `_clean(...)` helper (lines 1264-1269)

Reaches into `ObservedMetric` and `HospitalProfile` dataclasses, calls `.to_dict()` for canonical form. For other types, falls back to `_json_safe(x)`. **Defensive type narrowing** — same pattern as Report 0134 `_coerce_for_json`.

### Cache-key collision risk

If `_clean` produces the same JSON for two distinct objects (hash collision in shape), two distinct runs share a cache row. **MR824 below.**

### Cross-link to schema-versioning gap

Report 0058 MR417: `PACKET_SCHEMA_VERSION` is honor-system. Adding a field to `DealAnalysisPacket` should bump the version, but if the developer forgets:
1. Old cached packet returned for new code path
2. New code accesses missing attribute → AttributeError

**`hash_inputs` does NOT detect this.** Schema-bump invalidation is a separate concern.

### Schema-inventory progress (CLOSURE)

After this report: **15 tables walked.**

| Table | Walked? | FK? |
|---|---|---|
| (12 prior) | ✓ | various |
| 13. `users` | Report 0147 | (parent for sessions) |
| 14. `sessions` | Report 0147 | NO ACTION → users |
| 15. `analysis_runs` | **0148 (this — RE-WALK)** | **CASCADE → deals** |

**Per Report 0091 #11**: 22+ tables in DB. ~7 unidentified remain.

### CLAUDE.md cross-link

CLAUDE.md says: "Phase 4 ... `rcm_mc/analysis/analysis_store.py` ... cached in the `analysis_runs` table." **Doesn't mention** `hash_inputs` discriminator or FK behavior. **Cross-link Report 0093 MR503 critical doc rot.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR678-CLOSED** | **`analysis_runs.deal_id` has FK with ON DELETE CASCADE** + 2 indexes (idx_analysis_runs_hash, idx_analysis_runs_deal). Closes Report 0118 MR678 + Report 0077 cross-correction. | (closure) |
| **MR823** | **`hash_inputs` does NOT include `PACKET_SCHEMA_VERSION` in its payload** | A schema bump without code-side version-check fetches the OLD-shape cached packet for NEW callers. Cross-link Report 0058 MR417 high. **Should add `"_schema_version": PACKET_SCHEMA_VERSION` to the hash payload.** | **High** |
| **MR824** | **`_clean(...)` may produce identical JSON for distinct objects** if `to_dict` is lossy | Cache-key collision: two genuinely-different runs share a cache row. Acceptable if `to_dict` is canonical, fragile otherwise. | Medium |
| **MR825** | **`hash_inputs` differs for `analyst_overrides=None` vs `analyst_overrides={}`** | `{}` hashes to `{}` payload entry; `None` becomes `{}` after `or {}`. **Same.** OK actually. **No risk.** | (clean — false alarm) |
| **MR826** | **Report 0077 missed: FK + 2 indexes + correct field count for `analysis_runs`** | Audit cross-correction. Report 0077 must be marked superseded for the schema-walk portion. | (correction) |

## Dependencies

- **Incoming:** 7 production files (analysis chain + server + diligence).
- **Outgoing:** stdlib `hashlib.sha256`, `json.dumps(sort_keys=True)`; `_clean` calls `to_dict` on dataclasses.

## Open questions / Unknowns

- **Q1.** Should `hash_inputs` be enhanced with `PACKET_SCHEMA_VERSION` for stronger cache invalidation? (MR823 escalation.)
- **Q2.** What does `diligence/ingest/ccd.py` use `hash_inputs` for — is it the same function, or a name collision?
- **Q3.** Does any test verify cache invalidation on `analyst_overrides` change?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0149** | Comprehensive PRAGMA cross-check for ALL tables (final FK-frontier sweep). |
| **0150** | Fix MR823 — enhance `hash_inputs` to include `_schema_version`. |
| **0151** | Read `cli.py` head (1,252 lines, 14+ iterations owed). |

---

Report/Report-0148.md written.
Next iteration should: comprehensive PRAGMA cross-check for ALL tables to enumerate every FK constraint definitively (close FK frontier).
