# HIPAA Readiness Inventory

Inventory of how the RCM-MC / SeekingChartis platform maps to the
three HIPAA Safeguard categories (45 CFR 164.308/.310/.312) when
handling PHI during a diligence engagement.

This document is a **readiness inventory**, not a compliance
certification. A covered entity (CE) or their counsel must conduct
their own risk assessment before signing a Business Associate
Agreement (BAA).

Last reviewed: 2026-04

---

## Scope

RCM-MC is a local-deploy analytics tool for healthcare private-
equity diligence. When used with real claims data it processes PHI
(45 CFR 160.103). Engagement modes:

- **Sandbox** — synthetic fixtures only (`tests/fixtures/kpi_truth/`).
  No PHI in scope. This is the default for demos and development.
- **Engaged** — a specific deal uses live claims data under a signed
  BAA with the covered entity. All safeguards in this document
  apply in this mode.

---

## § 164.308 — Administrative Safeguards

| Control | Implementation | Status |
|---|---|---|
| Security Management Process (a)(1) | Engagement playbook (this doc + `templates/baa_template.md`); annual risk analysis refresh. | Documented |
| Assigned Security Responsibility (a)(2) | Named Security Officer on the engagement; initial = partner of record. | Documented |
| Workforce Security (a)(3) | RBAC via `rcm_mc.auth.rbac`; session scrypt + CSRF; rate-limited login. | Implemented |
| Information Access Management (a)(4) | Role-scoped access; deal-level owner assignment + audit trail. | Implemented |
| Security Awareness & Training (a)(5) | Onboarding checklist item; annual refresher. | Documented |
| Security Incident Procedures (a)(6) | Incident response in `HIPAA_READINESS.md` Appendix A (below). | Documented |
| Contingency Plan (a)(7) | `/api/backup` export; local-deploy model means no shared-infra blast radius; data-at-rest lives on one VM. | Implemented |
| Evaluation (a)(8) | Quarterly review of RBAC assignments + audit chain integrity. | Documented |
| BA Contracts (b) | `templates/baa_template.md` — fill-in-the-blank BAA. | Template |

---

## § 164.310 — Physical Safeguards

RCM-MC is a local-deploy tool. Physical safeguards are primarily
the deploying organisation's responsibility — this section inherits
from the host environment (firm office, cloud VM, partner laptop).

| Control | Implementation | Status |
|---|---|---|
| Facility Access Controls (a)(1) | Inherited from host (firm office / cloud provider). | Inherited |
| Workstation Use (b) | Laptop full-disk encryption; auto-lock after 5 min idle. Documented in engagement playbook. | Documented |
| Workstation Security (c) | Same as (b). | Documented |
| Device & Media Controls (d) | `rm -rfP` of the SQLite DB file at engagement close; firm-issued devices only. Export archive stored in firm DMS with retention policy. | Documented |

---

## § 164.312 — Technical Safeguards

| Control | Implementation | Status |
|---|---|---|
| Access Control (a)(1) — Unique User ID | `rcm_mc.auth.auth` enforces unique usernames, scrypt hashing. | Implemented |
| Access Control — Emergency Access | Admin-role break-glass documented; audited via chain. | Documented |
| Access Control — Automatic Logoff | Session TTL; meta-refresh logs out after 30 min idle. | Implemented |
| Access Control — Encryption/Decryption | At-rest: TLS-terminated reverse proxy; SQLite on encrypted volume. In-transit: HTTPS required when deployed outside `localhost`. | Documented |
| Audit Controls (b) | `rcm_mc.auth.audit_log` captures every sensitive action; `rcm_mc.compliance.audit_chain` adds SHA-256 hash chain. | Implemented |
| Integrity (c) | Hash chain over audit_events; CCD ingest logs SHA-256 content hash per source file. | Implemented |
| Person/Entity Authentication (d) | scrypt + session cookies + CSRF tokens. | Implemented |
| Transmission Security (e)(1) | TLS 1.2+ via reverse proxy when `--bind` is non-localhost. | Documented |

---

## Detective Controls in This Package

Two capabilities in `rcm_mc.compliance/`:

### `phi_scanner.py`
Regex-based detector for the common PHI patterns (SSN, phone, DOB,
MRN, NPI, email, street address). Run before:

- Committing test fixtures
- Exporting analyst working files out of the engagement sandbox
- Shipping logs to off-host systems

Example pre-commit usage:

```bash
python -c "from rcm_mc.compliance import scan_file, PHIScanReport
import sys; from pathlib import Path
for p in sys.argv[1:]:
    r = scan_file(p)
    if r.highest_severity:
        print(f'{p}: {r.highest_severity} — {r.count_by_pattern}')
        sys.exit(1)
" $(git diff --cached --name-only)
```

### `audit_chain.py`
SHA-256 chain over the `audit_events` table. Each event links to
its predecessor; any deletion, reordering, or mutation is detectable
via `verify_audit_chain(store)`. Run at engagement close to produce
a signed integrity attestation alongside the QoE memo.

**Trust model**: the chain is a detective control. An attacker with
write access to the SQLite file can still rewrite history *if* they
also regenerate every downstream hash. Mitigations:

- Periodic chain checkpoints exported to WORM storage (firm DMS,
  client S3 Object Lock).
- Off-host hash anchoring (daily email of the latest `row_hash` to a
  dedicated mailbox).
- Deploy the SQLite file on a volume that supports snapshotting
  with retention.

---

## Appendix A — Incident Response Runbook

1. **Detect**: analyst or reviewer notices anomaly (verify_audit_chain fails, unexpected record, unauthorised login in audit log).
2. **Triage** (within 1 business hour): Security Officer confirms incident, preserves the SQLite file via cold copy.
3. **Contain** (within 4 business hours): Revoke the compromised session; rotate admin credential.
4. **Assess** (within 24 hours): Determine whether PHI was disclosed. Counsel consulted for breach-notification clock.
5. **Notify** (per 45 CFR 164.410): BA notifies CE within 60 days; CE's obligations to individuals / HHS / media depend on scope.
6. **Remediate**: root-cause fix + chain-integrity re-attestation.
7. **Post-mortem**: blameless review within 5 business days; control gaps logged for the next quarterly evaluation.

---

## Appendix B — What This Package Is Not

- Not a formal SOC 2 Type II audit package. `SOC2_CONTROL_MAPPING.md`
  tracks the Trust Services Criteria pre-audit; a Type II report
  requires an independent auditor.
- Not a DLP product. `phi_scanner.py` catches pattern-matchable PHI
  in text — it won't catch PHI embedded in images, PDFs, or
  proprietary binary formats.
- Not a WAF. Rate-limited login + CSRF + session TLS are the baseline
  only; deploying to a hostile network requires a reverse proxy with
  its own WAF / fail2ban layer.
