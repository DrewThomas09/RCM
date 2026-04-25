# Report 0069: Dead Code — `auth/audit_log.py`

## Scope

192-line module. Sister to Reports 0063-0068.

## Findings

### Dead-code candidates

| Function | Production callers | Verdict |
|---|---:|---|
| `log_event` | 3 (server.py per Report 0064) | LIVE |
| `list_events` | likely 0-1 (admin UI?) | candidate |
| `cleanup_old_events` | likely 1 (cron / scheduled) | likely LIVE |
| `event_count` | likely 0-1 | candidate |
| `_iso`, `_utcnow`, `_ensure_table` | internal | LIVE |

### Cross-grep needed

`grep -rln "list_events\|event_count\|cleanup_old_events" RCM_MC/rcm_mc/` would surface callers. Not run this iteration; estimated few callers each.

### Verdict

Likely 0-1 truly dead public functions. The audit_log API is small + focused. Pattern matches Report 0009 (lookup.py) where some helpers exist primarily for tests.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR441** | `event_count` may have 0 production callers — candidate for removal | Low |

## Dependencies

- **Incoming:** server.py + likely an admin route + cron task.
- **Outgoing:** stdlib + pandas + portfolio.store.

## Open questions / Unknowns

- **Q1.** Is `cleanup_old_events` invoked by any cron / scheduled job? Need cross-grep.

## Suggested follow-ups

| Iteration | Area |
|---|---|
| **0070** | Orphan files (already requested). |

---

Report/Report-0069.md written.

