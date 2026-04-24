# SOC 2 Trust Services Criteria — Control Mapping

Pre-audit mapping of the AICPA 2017 Trust Services Criteria (TSC)
to controls implemented in the RCM-MC platform. Intended for
readiness, not certification — a SOC 2 report is issued only by an
independent CPA firm after a formal audit.

Scope selected: **Security (common criteria) + Confidentiality**.
Availability, Processing Integrity, and Privacy are candidates for a
future engagement but are not claimed here.

Last reviewed: 2026-04

---

## Common Criteria (CC) — Security

| TSC | Description | Implementation |
|---|---|---|
| CC1.1–CC1.5 | Control environment, governance | Partner-of-record accountability; documented engagement playbook; annual review cycle. |
| CC2.1 | Communication of information | Engagement kickoff memo; BAA signed; runbooks distributed. |
| CC2.2 | Communication with external parties | Incident response plan (HIPAA_READINESS.md Appendix A) includes BA → CE notification path. |
| CC2.3 | Internal communication | RBAC assignments reviewed quarterly; audit log reviewed before IC. |
| CC3.1–CC3.4 | Risk assessment | Annual risk analysis refresh per `HIPAA_READINESS.md §164.308(a)(1)`. |
| CC4.1–CC4.2 | Monitoring activities | `verify_audit_chain()` run at engagement close; `chain_status()` surfaced to admin UI. |
| CC5.1–CC5.3 | Control activities | RBAC (`rcm_mc.auth.rbac`), CSRF patching, rate-limited login, parameterised SQL. |
| CC6.1 | Logical access — new | scrypt password hashing + session cookies; unique user IDs. |
| CC6.2 | Logical access — modification | Admin-only user management; audit-logged. |
| CC6.3 | Logical access — removal | Admin delete-user cascades + audit row. |
| CC6.6 | Logical access — authentication | 2FA is on the roadmap (Session 5 RBAC work); currently scrypt + session TLS. |
| CC6.7 | Restricted access to sensitive data | Engagement sandboxing; separate DB files per engagement. |
| CC6.8 | Data protection controls | At-rest encryption at host layer; TLS in-transit. |
| CC7.1 | System monitoring | Unified audit log; p50/p95/p99 request observability; request-id trace. |
| CC7.2 | Anomaly detection | PHI scanner on pre-commit; audit-chain verification. |
| CC7.3 | Evaluation of security events | Incident response plan. |
| CC7.4 | Incident response | HIPAA_READINESS.md Appendix A. |
| CC7.5 | Recovery | `/api/backup` export; local-deploy isolation. |
| CC8.1 | Change management | Git-based change history; Co-Authored-By traceable to tooling. |
| CC9.1 | Risk mitigation | Documented in engagement playbook; BAA covers legal mitigation. |
| CC9.2 | Vendor risk | Zero third-party runtime dependencies for core functionality; all analytics stay on-host. |

---

## Confidentiality (C)

| TSC | Description | Implementation |
|---|---|---|
| C1.1 | Confidential information identified | CCD schema marks PHI fields; PHI scanner flags leakage. |
| C1.2 | Confidential information protected | Local-deploy sandbox; RBAC + audit log + chain; engagement teardown procedure. |

---

## Gaps Explicitly Acknowledged (Not Certified)

- **CC6.6 — MFA**: single-factor password + session. 2FA / WebAuthn is on the Session 5 roadmap.
- **Availability TSC**: no HA posture claimed. Single-VM deployment.
- **Processing Integrity TSC**: no claim. The CCD ingest reports a
  provenance chain per source file (SHA-256 + row counts), but full
  ETL-level PI is not audited here.
- **Privacy TSC**: no claim. This is an analytics platform for
  enterprise diligence — individuals are not direct users of the
  system.

---

## Evidence Artifacts for an External Auditor

When engaging an external SOC 2 auditor, the following artifacts
are collected from a representative engagement:

1. `audit_events` table export (chain-verified)
2. `rcm_mc.compliance.verify_audit_chain()` attestation output
3. RBAC role matrix (screenshot + export)
4. BAA countersigned with the covered entity
5. Incident response drill log (annual tabletop)
6. PHI scanner run logs from the engagement period
7. Pre- and post-engagement risk assessment memos
8. Change history (git log) for the engagement's snapshot of the
   code
