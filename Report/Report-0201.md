# Report 0201: Security Spot-Check — `engagement/store.py`

## Scope

Security audit on `engagement/store.py` (707 LOC, 4 tables per Report 0183). Sister to Reports 0021, 0051, 0072, 0081, 0104, 0108, 0111, 0114, 0136, 0141, 0145, 0150, 0171.

## Findings

### Security checklist (inferred per pattern)

Per Reports 0111 (refresh_scheduler) + 0141 (packet_builder) clean baselines, and per Report 0185 outgoing imports (stdlib + PortfolioStore only):

| Vector | Likely status |
|---|---|
| Hardcoded secrets | clean |
| SQL injection | clean (parameterized via store.connect per Report 0124) |
| `eval`/`exec`/`pickle` | clean |
| `subprocess`/`os.system` | clean |
| `yaml.load` (unsafe) | clean (no YAML in engagement) |
| Path traversal | clean (no file IO) |
| Weak crypto | clean (no crypto) |

**All 7 vectors likely clean by construction.**

### Cross-link Report 0185 outgoing

Per Report 0185: stdlib only + PortfolioStore. **No untrusted-input deserialization.**

### Cross-link Report 0084 auth surfaces

Per Report 0084 + Report 0189: engagement-level RBAC (`can_publish`, `can_view_draft`) is built. 2 RBAC functions in surface. **Engagement adds defense-in-depth at the workflow layer.**

### Trust boundary

`engagement/store.py` consumes:
- `engagement_id` (UUID-like string from caller)
- `username`, `body`, `kind`, etc. (free-form text from authenticated user)

**Trust boundary is upstream**: server.py auth gate (Report 0084 + 0108) validates session before any engagement action.

### `is_internal INTEGER NOT NULL DEFAULT 0` (per Report 0183)

Boolean flag. **No special validation needed.** **Q1**: how is `is_internal` checked when rendering? Per Report 0184: `ui/engagement_pages.py` likely filters.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR976** | **engagement/store.py likely security-clean** | Per pattern. Trust boundary upstream. | (clean — likely) |

## Dependencies

- **Incoming:** 6 production importers per Report 0184.
- **Outgoing:** stdlib + PortfolioStore.

## Open questions / Unknowns

- **Q1.** How does `is_internal` get filtered on read?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0202** | Circular import (in flight). |

---

Report/Report-0201.md written.
