# compliance/

**HIPAA / SOC 2 readiness layer** — PHI scanner, hash-chain audit integrity, CLI. Every HIPAA / SOC 2 auditor expects these artifacts.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — three capabilities: `phi_scanner`, `audit_chain`, CLI. |
| `__main__.py` | **CLI entry**: `python -m rcm_mc.compliance scan <path> [<path>...]`. Exit code 0 on no findings, 1 on any finding. CI-friendly. |
| `phi_scanner.py` | **Pattern-based PHI detector.** Catches common PHI patterns leaking into logs, test fixtures, exports, committed files — SSN, phone, DOB, NPI, MRN, ICD codes with name. SSN detector uses SSA guidance sanity band (excludes area codes 000 / 666 / 900-999). |
| `audit_chain.py` | **Hash-chain extension of `auth.audit_log`.** SHA-256 links each `audit_events` row to its predecessor so after-the-fact deletion, re-ordering, or mutation is detectable. Standard HIPAA / SOC 2 audit requirement. |

## How to use

### PHI scan before commit

```bash
# Scan test fixtures + logs for leaking PHI patterns
python -m rcm_mc.compliance scan tests/ RCM_MC/logs/ handoff/

# Exits non-zero if any pattern hits — wire into pre-commit or CI
```

### Verify audit log integrity

```python
from rcm_mc.compliance.audit_chain import verify_chain
result = verify_chain(db_path="seekingchartis.db")
# result.valid == False if any event was tampered with
# result.broken_at gives the first broken link
```

## Design notes

- **Stdlib-only** — `hashlib` for SHA-256, `re` for PHI patterns, no third-party deps
- **Pattern-based PHI** (not ML) — deterministic, auditable, false-positive-preferred over false-negative. Missing a SSN is worse than flagging a 9-digit phone number.
- **Hash chain runs on the same SQLite `audit_events` table** that `auth.audit_log` writes. Extension, not replacement.

## What it does NOT do

- Does not prevent PHI from being written — partners / integrations can still ingest PHI legitimately. The scanner flags **leaks** into non-PHI locations (logs, fixtures, exports).
- Does not replace a qualified HIPAA compliance officer review. Provides the machine-readable artifacts; humans still sign off.

## Tests

`tests/test_compliance_*.py` — PHI pattern coverage + hash-chain tamper-detection tests.
