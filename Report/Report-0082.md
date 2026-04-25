# Report 0082: Circular Import Risk — `compliance/` subsystem

## Scope

Cycle audit on `compliance/` (per Report 0030 inventory: phi_scanner.py, audit_chain.py, __init__.py, __main__.py + HIPAA_READINESS.md / SOC2_CONTROL_MAPPING.md / templates/baa_template.md).

## Findings

### Files

| File | Lines (approx) |
|---|---:|
| `compliance/__init__.py` | re-exports |
| `compliance/__main__.py` | CLI entry |
| `compliance/phi_scanner.py` | 252 (Report 0043) |
| `compliance/audit_chain.py` | (size unknown) |

### Sibling-import adjacency

Per Report 0043's `compliance/__init__.py:` head:

```python
from .audit_chain import (
    AuditChainReport, append_chained_event,
    chain_status, verify_audit_chain,
)
# ... and (per Report 0028/0030 callers) re-exports phi_scanner.scan_*
```

So:
- `__init__.py` → audit_chain, phi_scanner
- audit_chain → ??? (need read)
- phi_scanner → re (per Report 0043), dataclasses (likely no internal deps)
- __main__.py → __init__.py (re-exports) + phi_scanner

### Cycle check

- phi_scanner has 0 internal `rcm_mc.*` imports per Report 0043 outgoing.
- audit_chain wraps `auth/audit_log.log_event` (per Report 0030's claim) — so audit_chain → auth/audit_log → portfolio/store.
- `compliance/__init__.py` imports both → no cycle.

**Forward DAG: __init__ → {phi_scanner, audit_chain → auth/audit_log → portfolio/store}.** Clean.

### Cross-package edges

- audit_chain → auth/audit_log (one-way, no return)
- phi_scanner → stdlib only
- __main__ → __init__ (intra)

No cycles within compliance/, no return-imports from auth/ or portfolio/.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR467** | **`audit_chain → auth/audit_log → portfolio/store` is a 3-layer chain** | If portfolio/store ever imports from compliance (unlikely), cycle forms. Currently safe. | Low |

## Dependencies

- **Incoming:** pre-commit hook (Report 0056), tests, possibly server.py admin route.
- **Outgoing:** auth/audit_log, portfolio/store, stdlib.

## Open questions / Unknowns

- **Q1.** Read `audit_chain.py` end-to-end to confirm no return imports.

## Suggested follow-ups

| Iteration | Area |
|---|---|
| **0083** | (next iteration). |

---

Report/Report-0082.md written.

