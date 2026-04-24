"""HIPAA / SOC 2 compliance readiness package.

Three distinct capabilities live under this package:

- **PHI scanner** (``phi_scanner``) — pattern-based detector that
  flags PHI leaking into logs, test fixtures, or exports. Catches the
  common patterns (SSN, phone, DOB, NPI, MRN, ICD codes with name
  proximity). Designed for the pre-commit + CI path, not as a
  production DLP.

- **Audit-log hash chain** (``audit_chain``) — adds a SHA-256 chain
  to the existing ``audit_events`` table so any after-the-fact
  deletion or mutation is cryptographically detectable. Extends the
  existing auth.audit_log module without breaking its API.

- **Readiness documents** (``HIPAA_READINESS.md``,
  ``SOC2_CONTROL_MAPPING.md``, ``templates/baa_template.md``) — the
  paperwork a covered entity reviews before signing a BAA.

Zero new runtime dependencies. Everything is stdlib + the existing
``pandas``/``sqlite3`` path the rest of the platform uses.
"""
from __future__ import annotations

from .audit_chain import (  # noqa: F401
    AuditChainReport,
    append_chained_event,
    chain_status,
    verify_audit_chain,
)
from .phi_scanner import (  # noqa: F401
    PHIFinding,
    PHIScanReport,
    redact_phi,
    scan_text,
    scan_file,
)

__all__ = [
    "AuditChainReport",
    "PHIFinding",
    "PHIScanReport",
    "append_chained_event",
    "chain_status",
    "redact_phi",
    "scan_file",
    "scan_text",
    "verify_audit_chain",
]
