# Report 0111: Security Spot-Check — `analysis/refresh_scheduler.py`

## Scope

`RCM_MC/rcm_mc/analysis/refresh_scheduler.py` (172 lines) — closes Report 0107 Q2 + the other half of MR597 high. Sister to Reports 0021 (auth security), 0051 (notifications security), 0072 (audit-event security), 0081 (analysis_store security), 0104 (webhooks security).

## Findings

### Module purpose

Stale-analysis detector + auto-refresh scheduler. Detects when a deal's latest `DealAnalysisPacket` was built BEFORE a data source's `last_refresh_at` (per Report 0107 `data_source_status`). Optionally rebuilds the top-N stalest packets via `analysis_store.get_or_build_packet(force_rebuild=True)`.

### Security checklist (clean across the board)

| Vector | Status |
|---|---|
| Hardcoded secrets | **NONE** — no tokens, no keys, no passwords |
| SQL injection | **NONE** — 2 SELECT queries (lines 95-103) use no parameters and no f-string interpolation |
| Unsafe deserialization (pickle/eval/exec) | **NONE** — uses `datetime.fromisoformat` only |
| `yaml.load` (unsafe) | **NONE** — no YAML parsing |
| Shell injection (subprocess/os.system) | **NONE** — no shell calls |
| Path traversal | **NONE** — no path manipulation |
| Weak crypto | **NONE** — no crypto used |
| Dangerous regex / ReDoS | **NONE** — no regex |
| Untrusted input deserialization | **NONE** — input is SQLite rows under our control |

### SQL discipline (per CLAUDE.md "Parameterised SQL only")

Lines 95-103, the only SQL surface:

```python
con.execute(
    """SELECT deal_id, MAX(created_at) AS latest_at
       FROM analysis_runs
       GROUP BY deal_id"""
)
con.execute(
    "SELECT source_name, last_refresh_at FROM data_source_status"
)
```

**Both queries take zero parameters.** No user input concatenation. Compliant.

### Input validation

- `_parse_iso(s)` (lines 72-81) — wraps `datetime.fromisoformat(cleaned)` in `try/except (ValueError, TypeError)` returning `None` on failure. Defensive.
- `s.replace("Z", "+00:00")` (line 78) — normalizes the ISO-8601 `Z` suffix that `fromisoformat` doesn't accept on Python <3.11. Safe.
- All input is **internal** (SQLite columns) — no HTTP / form / CLI input.

### Error handling

`auto_refresh_stale` (lines 162-170):

```python
for sa in to_refresh:
    try:
        get_or_build_packet(store, sa.deal_id, force_rebuild=True)
        refreshed.append(sa.deal_id)
    except Exception:
        logger.warning(
            "auto_refresh failed for deal %s", sa.deal_id,
            exc_info=True,
        )
```

| Aspect | Status |
|---|---|
| Bare except | NO — `except Exception` |
| `noqa: BLE001` annotation | **MISSING** — Report 0020 pattern partly violated |
| Logger present | YES — WARNING level with exc_info=True (full traceback) |
| Re-raise | NO — partial-failure tolerated by design (per docstring line 154) |

**Pattern A (full-traceback) logger discipline** — better than Report 0050 `infra/notifications.py` and Report 0104 `infra/webhooks.py` (silently swallowed). **Strong error handling here.**

### CRITICAL FINDING: schema definition duplicated

**`_ensure_tables_exist` (lines 39-69) re-declares `analysis_runs` AND `data_source_status` schemas** — both already defined elsewhere:
- `analysis_runs` defined in `analysis/analysis_store._ensure_table` (per Report 0077)
- `data_source_status` defined in `data/data_refresh._ensure_tables` (per Report 0107)

`CREATE TABLE IF NOT EXISTS` makes this a no-op when a peer module ran first. **But:** if a future commit adds a column to the canonical schema, **this module still creates the OLD shape**. A user on a fresh DB whose first interaction is `refresh_scheduler` would get a stale schema, and the canonical-schema-owning module would later fail to ALTER (per Report 0017: no ALTER TABLE migration framework).

**MR621 below.** Cross-link CLAUDE.md "The store is the only module that talks to SQLite directly" — clearly violated project-wide; this is the 5th+ instance.

### Architecture observation: CLAUDE.md claim vs reality

CLAUDE.md (per Report 0011 + 0017) says: "The store is the only module that talks to SQLite directly."

**Confirmed violations** (modules that call `store.connect()` directly):
| Module | Audited |
|---|---|
| `auth/audit_log.py` | Report 0063 |
| `auth/auth.py` | Report 0021 |
| `data/data_refresh.py` | Report 0102, 0107 |
| `infra/webhooks.py` | Report 0104 |
| `infra/consistency_check.py` | Report 0110 |
| **`analysis/refresh_scheduler.py`** | **this report** |
| `analysis/analysis_store.py` | Report 0008, 0080, 0081 |
| `domain/custom_metrics.py` | Report 0099 |

**8+ modules talk to SQLite directly.** CLAUDE.md architecture principle is **aspirational, not enforced.** Adds to Report 0093 MR503 + Report 0103 MR574 doc-rot inventory.

### Timezone-aware comparison defense

Lines 128-129, 134:

```python
pdt = packet_dt if packet_dt.tzinfo else packet_dt.replace(tzinfo=timezone.utc)
rdt = refresh_dt if refresh_dt.tzinfo else refresh_dt.replace(tzinfo=timezone.utc)
```

**Defensive**: if either timestamp parses without timezone (legacy data), assume UTC. **Per CLAUDE.md "Datetimes must be timezone-aware"** — confirmed compliance.

### Importers

| File | Use |
|---|---|
| `server.py` | likely a `/api/admin/refresh-stale` endpoint |
| `tests/test_phase_mn.py` | tests |

**2 importers — tight surface.**

### Cross-link to Report 0107 state machine

This module READS `data_source_status.last_refresh_at` to decide which packets are stale. It does NOT touch the `status`/`error_detail` columns. So the ERROR-terminal state machine (Report 0107 MR599) is bypassed here — even an ERROR-state source's `last_refresh_at` is read as canonical. **Subtle**: stale-detection works against the LAST KNOWN refresh time even if the source is broken now.

### Cross-link to Report 0093 / 0102 (free-form classifications)

No new free-form-text fields here. `StaleAnalysis.stale_sources` is `List[str]` of source names — sourced from `KNOWN_SOURCES` (per Report 0102) so the project-wide pattern doesn't bite here.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR621** | **Schema duplication: `analysis_runs` AND `data_source_status` re-declared in `_ensure_tables_exist` (lines 39-69)** | Both already declared in their canonical modules. CREATE IF NOT EXISTS makes this a no-op when canonical ran first, but future column-add to canonical leaves `refresh_scheduler` creating stale shape. | **High** |
| **MR622** | **`except Exception` lacks `noqa: BLE001`** (line 166) — Report 0020 pattern divergence | Minor lint hygiene; ruff will flag. | Low |
| **MR623** | **`auto_refresh_stale` triggers `get_or_build_packet` synchronously in a loop** | If 10 deals are stale and `get_or_build_packet` takes 30s each, caller blocks 5 minutes. Cross-link Report 0103 MR569 (single-worker FIFO). Should use `infra/job_queue.submit_callable` instead. | **Medium** |
| **MR624** | **No explicit auth gate on the function — it's library-level** | Caller (server.py) must enforce. If a future endpoint exposes `auto_refresh_stale` without auth, anyone can trigger 10+ packet rebuilds. DoS surface. | Medium |
| **MR625** | **`max_refreshes: int = 10`** is a hardcoded default, not env/config-tunable | Operators with 50+ stale packets need to either edit code or call repeatedly. Cross-link Report 0090 (env-var pattern for tunables). | Low |
| **MR626** | **CLAUDE.md "store is the only module that talks to SQLite" is violated by 8+ modules** | Cross-link MR503, MR574. Project-wide; remediation requires architectural choice. | (advisory) |

## Dependencies

- **Incoming:** server.py (probable `/api/admin/refresh-stale` route), tests/test_phase_mn.py.
- **Outgoing:** stdlib (`logging`, `dataclasses`, `datetime`, `typing`); `analysis.analysis_store.get_or_build_packet` (lazy import, line 156); `store.connect()` (SQLite).

## Open questions / Unknowns

- **Q1.** Where is `auto_refresh_stale` called from in server.py? Direct route or scheduled job?
- **Q2.** How does `get_or_build_packet` failure cascade? Is the SQLite connection released, or does a partial-write leave a half-built `analysis_runs` row?
- **Q3.** Does `tests/test_phase_mn.py` exercise the failure path (mocked failing `get_or_build_packet`)?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0112** | Schema-walk `mc_simulation_runs` (Report 0110 MR616 backlog). |
| **0113** | Read `mc/mc_store.py` (Report 0110 MR617 backlog). |
| **0114** | Map `rcm_mc_diligence/` separate package (carried 10+ iterations). |
| **0115** | Map `pe_intelligence/` (carried since Report 0093). |

---

Report/Report-0111.md written.
Next iteration should: schema-walk `mc_simulation_runs` table — closes Report 0110 MR616 backlog item.
