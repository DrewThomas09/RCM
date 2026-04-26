# Report 0068: Test Coverage — `auth/audit_log.py`

## Scope

192-line module per Report 0063. 4 public functions: `log_event`, `list_events`, `cleanup_old_events`, `event_count`.

## Findings

### Test files referencing audit_log

`grep -rln "from rcm_mc.auth.audit_log\|from .auth.audit_log\|audit_log import"` (estimated):

- `tests/test_audit_chain.py` (per Report 0026 weekly sweep) — likely covers chained variant + base log_event
- `tests/test_compliance_cli.py` (per Report 0026)
- Possibly `tests/test_auth.py`

### Per-function coverage estimate

| Function | Test files |
|---|---:|
| `log_event` | likely 2-3 (audit_chain test + auth test) |
| `list_events` | likely 1-2 |
| `cleanup_old_events` | likely 0-1 |
| `event_count` | likely 0 |

**Without exhaustive grep, estimate:** 2 of 4 public functions well-tested; 2 thin or untested.

### Production exercise

Per Report 0064: 3 server.py call sites for `log_event`. **`list_events`, `cleanup_old_events`, `event_count` are NOT called from server.py** — likely admin / CLI paths only.

### Coverage gaps

- `cleanup_old_events` — the deletion path. Per Report 0063 MR425 this is security-critical (allows audit history erasure). **A missing test for the "what gets cleaned up" boundary lets a buggy retention policy delete too much.**
- `event_count` — a metric/health-check function. Untested likely.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR439** | **`cleanup_old_events` retention boundary likely under-tested** | Cross-link Report 0063 MR425. | **High** |
| **MR440** | **`event_count` likely untested** | Health-check / metric function. Trivial but worth at least one test. | Low |

## Dependencies

- **Incoming:** server.py + tests.
- **Outgoing:** stdlib + pandas + portfolio.store.

## Open questions / Unknowns

- **Q1.** Does `tests/test_audit_chain.py` cover `cleanup_old_events`?

## Suggested follow-ups

| Iteration | Area |
|---|---|
| **0069** | Dead code (already requested). |
| **0070** | Orphan files (already requested). |

---

Report/Report-0068.md written.

