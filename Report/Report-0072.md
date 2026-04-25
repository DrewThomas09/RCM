# Report 0072: Data Flow Trace — Audit Event (HTTP request → log_event → SQLite)

## Scope

Traces an audit event from HTTP request through `log_event` to SQLite. Sister to Reports 0042 (DOMAIN env), 0012 (actual.yaml).

## Findings

### Stage 0 — incoming HTTP request

User makes a privileged call: `POST /api/deals/<id>` (or similar sensitive route).

### Stage 1 — server.py route handler

server.py routes: per Report 0064 the 3 audit-recording sites are at lines 1562, 14586, 14619.

```python
# Lines 1562-1565 (paraphrased per Report 0064)
from .auth.audit_log import log_event   # lazy
log_event(
    store, actor=user, action="DEAL_DELETE",
    target=deal_id, detail={"reason": ..., ...},
)
```

### Stage 2 — `log_event` (audit_log.py:79)

```python
def log_event(store, *, actor, action, target, detail=None) -> int:
    _ensure_table(store)
    with store.connect() as con:
        cur = con.execute(
            "INSERT INTO audit_events (at, actor, action, target, detail_json, request_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (_iso(_utcnow()), actor, action, target, json.dumps(detail or {}), None),
        )
        con.commit()
        return int(cur.lastrowid)
```

### Stage 3 — `_ensure_table`

Creates `audit_events` table if not exists. Idempotent.

### Stage 4 — Connection + INSERT

`PortfolioStore.connect()` opens a connection (per Report 0017) — uses WAL mode + busy_timeout=5000. INSERT is parameterized.

### Stage 5 — Commit

`con.commit()` flushes to disk. **No retry on failure.** If the disk is full, INSERT raises and the audit event is lost.

### Stage 6 — Return event id

Caller may use the event_id for follow-up logging. Per the 3 server.py sites, the return value is typically discarded.

### Stage 7 — Compliance audit-chain (separate module)

Per Report 0028 / 0030 / 0064, `compliance/audit_chain.py:append_chained_event` is a parallel sister that adds SHA-256 chain integrity. **Not invoked by `log_event`** — independent module that reads `audit_events` post-hoc.

### Stage 8 — Reading back

`list_events(store, ...)` (audit_log.py:113) returns DataFrame for admin views. Likely called from server.py's `/admin/audit` route (not yet enumerated).

### Trace diagram

```
HTTP POST /api/deals/<id>
       │
   Stage 1   server.py:<route handler>
       │     from .auth.audit_log import log_event   (lazy)
       ▼
   Stage 2   audit_log.py:79  log_event(store, actor, action, target, detail)
       │
   Stage 3   _ensure_table(store)  → CREATE TABLE IF NOT EXISTS audit_events
       │
   Stage 4   con.execute("INSERT INTO audit_events ...")
       │
   Stage 5   con.commit()  → flushed to ~/.rcm_mc/portfolio.db (or RCM_MC_DB)
       │
   Stage 6   return cur.lastrowid
       │
   Stage 7   (separate)  compliance/audit_chain  reads + chains
       │
   Stage 8   admin route → list_events(...) → DataFrame → /admin/audit
```

### Failure modes

| Stage | Failure | Outcome |
|---|---|---|
| 1 | log_event call missing | event un-recorded; honor-system gap (MR431) |
| 2 | json.dumps of detail fails | exception bubbles up; HTTP request likely 500s |
| 4 | DB locked / disk full | exception bubbles; HTTP request 500s; event LOST |
| 5 | commit() interrupted | partial write; SQLite WAL recovers on next open |
| 7 | audit_chain runs separately | event recorded but un-chained until next audit_chain run |

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR445** | **No retry on `log_event` DB failure** | Audit event silently lost if INSERT fails | **High** |
| **MR446** | **`audit_chain` is post-hoc** | Tamper-evidence requires a separate process invocation; events are unchained until then | Medium |
| **MR447** | **CLI / scheduled paths don't `log_event`** (cross-link MR430) | Non-HTTP audit blind spot | **High** |

## Dependencies

- **Incoming:** server.py routes, admin UI, compliance audit_chain.
- **Outgoing:** PortfolioStore, SQLite.

## Open questions / Unknowns

- **Q1.** Is `request_id` ever populated, or always None at this site?

## Suggested follow-ups

| Iteration | Area |
|---|---|
| **0073** | API surface (already requested). |

---

Report/Report-0072.md written.

