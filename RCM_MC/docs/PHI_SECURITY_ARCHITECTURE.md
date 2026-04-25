# PHI Security Architecture + BAA Plan

When a customer brings claims data, they're handing the platform
**Protected Health Information** under HIPAA's Privacy + Security
Rules. The platform becomes a **Business Associate** of the
covered entity. This document maps the path from the current
public-data-only architecture to a PHI-capable platform — what
must be built, what must be governed, and what we deliberately
won't accept.

## What's PHI and what's not

Per 45 CFR §160.103 PHI is **individually identifiable health
information** transmitted or maintained by a covered entity or
business associate. Practically:

  - **PHI**: claims (837/835), eligibility (270/271), encounter
    data, EHR extracts, ADT messages, individual patient records.
    Anything that links a patient identifier (name, MRN, DOB +
    ZIP) to a clinical/financial fact.
  - **Not PHI**: HCRIS aggregated cost reports, NPPES provider
    registry, Hospital Compare quality scores, Census demographics,
    CDC PLACES county-level data, AHRQ HCUP de-identified discharge
    samples. Everything the platform ingests today is non-PHI
    public data.

The platform's current data layer is fully public; there is **no
PHI on the platform today**. PHI enters only when a customer opts
to upload claims (e.g., for our trained predictors to retrain on
their realized RCM outcomes — per the learning-loop plan).

## Three deployment options

PE customers will ask for one of three deployment shapes when PHI
enters the picture. Each has different security boundary, BAA
posture, and engineering lift.

### Option 1 — Multi-tenant SaaS (current shape)

**Status**: Not BAA-eligible. We will not accept PHI in the
multi-tenant deployment.

**Why not**: Multi-tenant means one database hosts multiple
customers' data. Even with row-level security, a software bug in
the access layer is a HIPAA breach affecting every covered entity
on the system. The blast radius is unacceptable.

**Decision**: Multi-tenant stays public-data-only. PHI requires
single-tenant.

### Option 2 — Single-tenant SaaS (managed by us, isolated infrastructure)

**Status**: BAA-eligible. **Recommended primary path.**

**Architecture**:
- One **dedicated VPC per customer** in our cloud account (AWS
  GovCloud or Azure Commercial — both sign BAAs).
- One database, one app server, one Redis cache **per customer**.
  No shared compute, no shared storage.
- Customer data **never crosses the VPC boundary**. Network
  egress restricted to our own update/telemetry endpoints (which
  receive only metric counters, never customer data).
- Encryption at rest using AES-256 with **per-customer KMS keys**;
  customer can revoke our access by rotating the key.
- TLS 1.3 in transit; certificate pinning for our internal
  services.
- Access logged per request to an immutable audit log retained
  6 years (HITECH §13402(c) mandatory minimum).

**Operational model**: We deploy + monitor + update. Customer
sees a managed service. Engineering team's access to the customer
VPC requires (a) JIT access request, (b) MFA, (c) approval from
the customer's designated security contact, (d) all sessions
recorded.

**Cost**: ~$3-8K/month per customer in cloud infrastructure
(varies with usage). Built into the Enterprise pricing tier;
covered by the $150K base + per-seat fees.

### Option 3 — Customer-VPC deployment (BYO cloud)

**Status**: BAA-eligible. Required for some healthcare strategics
+ regulated mega-funds.

**Architecture**:
- Platform deployed inside the **customer's own VPC**. Their
  cloud account, their network controls, their KMS keys, their
  IAM. Data never leaves the customer's cloud.
- We provide the deployment via Terraform module + Helm chart.
  Customer's cloud team applies it; we never touch their account.
- Updates: customer pulls a versioned container image from our
  registry; their CI/CD applies it on their schedule.
- Telemetry: opt-in. By default, we get nothing back. Customer
  can opt into anonymous performance metrics (request counts,
  error rates, no customer data).

**Operational model**: Customer operates the platform; we
provide the software + monthly support. Engineering team has
**zero access** to customer data.

**Cost**: Customer pays cloud infrastructure directly (typically
$5-15K/month at their volume, billed by their cloud provider).
Platform license fee covers software + 24/7 support but not
infrastructure.

**Tradeoffs**: Customer owns the operational lift (deployment,
backups, scaling, incident response). Slower update cadence (we
ship every 2 weeks; customer might pull monthly). Higher all-in
cost than managed single-tenant but stronger compliance posture.

### When each option fits

| Customer profile | Right deployment |
|---|---|
| PE shop with no internal cloud team | Option 2 (managed single-tenant) |
| Mega-fund healthcare vertical with mature security org | Option 3 (customer VPC) |
| Healthcare strategic (UnitedHealth, HCA M&A) | Option 3 (customer VPC) — likely required |
| PE shop with strict data-residency requirements (EU, Australia) | Option 3 in their region's cloud |
| Pro-tier customer not bringing PHI | Option 1 (current multi-tenant) |

---

## BAA requirements

The Business Associate Agreement is contract terms required by
HIPAA. Every customer bringing PHI signs one before any PHI
flows. Our standard BAA terms:

### What we commit to

  - **Use limitation**: PHI used only to provide the platform's
    services to that specific customer.
  - **No marketing or research** use of PHI without explicit
    customer authorization.
  - **No data sale** under any circumstances.
  - **Subcontractor flow-down**: any subprocessor with PHI access
    (e.g., AWS, the database vendor) signs a BAA with us, and
    those terms flow down to the customer's BAA. Subprocessor
    list maintained at `/legal/subprocessors`.
  - **Breach notification within 72 hours** of discovery to the
    customer's designated security contact (HIPAA requires 60
    days; we commit to faster).
  - **Termination data return**: on contract end, all PHI
    returned (single-tenant: VPC snapshot delivered; customer
    VPC: nothing to return) or destroyed under documented
    process within 30 days.
  - **Audit cooperation**: customer or their auditor gets read
    access to audit logs for HIPAA compliance audits at no
    additional cost.

### What we require from the customer

  - **Designated security contact**: named individual at the
    customer who receives breach notifications and approves our
    JIT access requests.
  - **Identity attestation**: customer is a covered entity or
    business associate of one; we don't accept PHI from
    organizations without that posture.
  - **Data minimization**: customer agrees to upload only the
    PHI necessary for the use case. Bulk dumps without filtering
    are refused.
  - **Use case scoping**: each upload describes the analytical
    purpose. Out-of-scope use of uploaded PHI requires explicit
    authorization.
  - **Authorized user list**: customer maintains the list of
    their staff authorized to access PHI on the platform.

### Subprocessors (the BAA chain)

| Vendor | Service | BAA in place |
|---|---|---|
| AWS | Cloud infrastructure (Option 2) | Yes (AWS BAA) |
| Microsoft Azure | Alternative cloud | Yes (Azure BAA) |
| Datadog or equivalent | Observability (PHI-stripped only) | Required before launch |
| PagerDuty | Incident alerts (no PHI) | Required before launch |
| GitHub | Source control (no customer data) | N/A — no PHI exposure |

We do not use any vendor without a BAA where PHI could plausibly
flow. Vendor selection is gated by the security review.

---

## Security architecture (single-tenant SaaS — the primary path)

### Data isolation

- Per-customer **dedicated VPC** (AWS) or VNet (Azure).
- Per-customer database instance — no shared schema, no
  multi-tenant table.
- Per-customer S3 bucket / Azure Blob container with bucket
  policies blocking cross-account access.
- Cross-customer access is **architecturally impossible**, not
  just policy-blocked. A bug in our app code cannot leak
  customer A's data to customer B because they're not in the
  same database.

### Encryption

- **At rest**: AES-256 via cloud KMS. Each customer has their
  own KMS key alias; customer can rotate or revoke access
  unilaterally.
- **In transit**: TLS 1.3 only; certificate pinning on internal
  service-to-service calls.
- **Key separation**: KMS keys stored in customer-specific KMS
  with audit logs going to the customer's CloudTrail / Activity
  Log.

### Access controls

- **RBAC**: 6-tier hierarchy from `auth/rbac.py` already exists;
  unchanged for PHI.
- **MFA mandatory**: Enterprise customers' users must MFA. No
  password-only access to PHI-bearing tenants.
- **JIT engineering access**: Our team requesting access to a
  customer VPC requires (a) ticketed reason, (b) customer's
  security contact approval, (c) MFA, (d) session recording, (e)
  expires after 4 hours.
- **No standing access**: No engineer has persistent access to
  any customer's PHI environment. Every access is JIT.

### Audit logging

- Every state-changing action logged with `(timestamp, user,
  action, resource, deal_id, ip_address)`.
- Read access also logged for PHI-containing resources.
- Logs immutable (write-once via S3 Object Lock or Azure Blob
  immutability) and retained **6 years minimum** (HITECH).
- Customer gets read-only access to their own audit log via
  `/api/v1/audit-log` endpoint.
- Anomaly detection: bulk-export, off-hours access, cross-deal
  reads — all flagged via the existing `regime_detection`
  pattern adapted for security events.

### Network controls

- Inbound: only the customer's allowlisted IP ranges (or
  VPN-via-customer-cloud) can reach the platform.
- Outbound: deny-by-default; allowlist only the specific
  endpoints we need (KMS, S3, public-data refresh sources).
- Customer data **never** sent to our update / telemetry
  endpoints. Telemetry is metric counters only —
  request-count + error-rate + p50/p95 latency. No PHI fields,
  no deal_id, no user_id.

### Application-layer hardening

- All HTTP responses set `Strict-Transport-Security`,
  `X-Frame-Options: DENY`, `Content-Security-Policy`,
  `X-Content-Type-Options: nosniff`.
- All forms CSRF-protected (already shipped).
- Output encoding via the existing `html.escape` discipline (the
  recent UI sprint enforces this in tests).
- SQL injection: parameterized queries only (already enforced
  per CLAUDE.md).
- No reliance on userspace cryptography — KMS, AWS Secrets
  Manager, OS-level TLS termination handle all crypto.

### Backup + recovery

- Per-customer encrypted snapshots, retained 30 days hot + 1 year
  cold (cold = customer-controlled S3 Glacier).
- Recovery objective: RPO 24 hours, RTO 4 hours.
- Quarterly recovery drill: documented restoration of a test
  customer's snapshot to a separate VPC; integrity verified.

### Monitoring + alerting

- Cloud-native monitoring (CloudWatch / Azure Monitor) with
  PHI-stripped metric streams.
- Security events (failed logins, JIT-access requests, anomalous
  reads) → PagerDuty for our security team.
- Customer-facing status page at `status.example.com` showing
  uptime + active incidents per customer cluster.

---

## SOC 2 Type II commitment

Most Enterprise customers require SOC 2 Type II evidence before
signing a BAA. Path:

1. **Type I** (point-in-time control existence): 4 months from
   project start. Evidence we have controls; auditor inspects them
   at one moment.
2. **Type II** (operating effectiveness over time): additional
   6-12 months observation period. Evidence the controls actually
   ran. Required for most Enterprise procurement.

Total: 10-16 months from start to Type II issuance. We start the
clock immediately on Enterprise customer commitment; no PHI flows
until Type I is in hand.

Cost: $50-100K for Type I, $100-200K for Type II (audit firm fees
+ internal staff time). Build into Enterprise pricing.

---

## What we deliberately don't accept

These are partner-tempting offers we will refuse:

  - **Bulk PHI dumps without use-case scoping**: customer can't
    upload 'all our claims' for unspecified analysis. Every
    upload describes the analytical purpose.
  - **De-identified-but-not-anonymous data**: per HIPAA Safe Harbor
    + Expert Determination, true de-identification removes 18
    specific identifiers. We accept either truly de-identified
    data (no BAA needed) or full PHI (BAA required), but not the
    middle ground where the customer claims de-identification but
    hasn't done the full removal.
  - **Re-identification by us**: we never combine de-identified
    customer data with public data in a way that could re-identify
    individuals. Recital in BAA.
  - **PHI sold to or shared with third parties**: full ban.
    Subprocessors sign BAA flow-down terms; even our cloud vendors
    have no commercial use of customer PHI.
  - **PHI in observability / debugging**: when our team
    troubleshoots an issue, we cannot see PHI. Logs PHI-stripped
    at the source; debug environments use anonymized data only.
  - **Long-term PHI retention beyond contract**: 30-day return
    or destruction window post-termination. No 'archive in case
    customer comes back'.

The line: we provide analytical services on PHI within a documented
use case for the duration of the contract. Anything outside that
boundary is refused.

---

## Build sequence

### Phase 1 — Foundation (8 weeks)

1. **Weeks 1-3**: Per-customer VPC provisioning automation
   (Terraform modules); per-customer KMS keys; VPC peering for
   our control plane.
2. **Weeks 4-5**: Application-level customer isolation —
   ensuring no shared globals, per-customer SQLite path, no
   cross-customer queries possible.
3. **Weeks 6-8**: Audit log immutability (S3 Object Lock); 6-year
   retention configuration; customer-facing audit log API.

### Phase 2 — BAA-readiness (6 weeks)

1. **Weeks 1-2**: Subprocessor BAA chain (AWS, Datadog, PagerDuty
   each sign their BAA with us before launch).
2. **Weeks 3-4**: Standard customer BAA template + legal review.
3. **Weeks 5-6**: Internal access controls — JIT request system,
   session recording, customer-approval workflow.

### Phase 3 — SOC 2 prep (16 weeks rolling)

1. **Months 1-2**: Internal security review; gap assessment
   against SOC 2 Trust Services Criteria.
2. **Months 3-6**: Control implementation + documentation.
3. **Month 7**: Type I audit.
4. **Months 8-13**: Type II observation period.
5. **Month 14**: Type II audit + report issuance.

### Phase 4 — Customer-VPC deployment (8 weeks)

1. **Weeks 1-3**: Helm chart + container packaging.
2. **Weeks 4-5**: Customer-deploys-it documentation +
   troubleshooting runbook.
3. **Weeks 6-8**: First customer-VPC pilot deployment with a
   design-partner customer.

**Total: ~22 weeks of dedicated work + 16 months of SOC 2 calendar
time.** Phases 1-2 + 4 are the engineering lift; phase 3 is mostly
audit work that runs in parallel.

---

## Pricing implications

PHI handling lives at the **Enterprise tier only** (per the
business model plan). The reasons:

1. **SOC 2 + BAA** is non-trivial cost — $200-300K/year for
   audits + dedicated security headcount. Spread across small
   Pro accounts ($30K/seat) it doesn't math.
2. **Per-customer infrastructure** is $3-8K/month — Pro tier
   gross margin can't absorb it.
3. **Liability exposure**: HIPAA breach penalties scale to $1.5M
   per violation category per year. We need cyber-liability
   insurance + customer indemnification language that only
   Enterprise-tier contracts support.

Enterprise BAA + PHI handling adds ~$200-400K/yr to the customer's
fee on top of the base Enterprise pricing. Single-tenant
infrastructure ($60-100K/yr) + SOC 2 amortization ($30-50K/yr) +
incremental engineering operations ($100-200K/yr) + insurance
($30-50K/yr).

Enterprise customers can support these economics; the value of
analytical insight on their own claims data justifies the cost.

---

## Customer responsibilities (the shared-responsibility model)

Customers bringing PHI also have obligations. Spelling these out
in the BAA prevents the 'we thought you handled X' surprise:

  - **Data classification**: customer marks each upload as PHI vs
    de-identified vs aggregated. We treat each appropriately.
  - **User provisioning**: customer's admin creates / removes
    users; off-boarding is their job.
  - **Access reviews**: customer reviews their user list quarterly;
    we provide the access-log export to support that.
  - **Workforce training**: their staff using the platform must
    have HIPAA training (their training, not ours).
  - **Endpoint security**: laptops accessing our platform must
    have FDE + MFA + EDR per the customer's security policy. We
    don't provide endpoint controls.
  - **Network egress**: customer is responsible for their network
    paths to our service. We require TLS but can't enforce
    customer-side network controls.

The split: we secure the platform; the customer secures their
people, devices, and processes. HIPAA shared responsibility is
explicit in the BAA.

---

## Strategic takeaway

PHI capability is the price of admission to the **Enterprise
healthcare PE market**. Healthcare strategics, mega-funds with
captive providers, and any customer wanting to leverage their own
claims data for predictor retraining will require it.

The investment to enable PHI handling is real (~$300K + 16 months
to SOC 2 Type II) but unblocks ~$5-15M of Enterprise ARR over the
next 24 months that's currently unreachable.

The architecture above puts the platform in the strongest possible
posture: single-tenant by default, customer-VPC for the most
demanding shops, never multi-tenant for PHI, JIT-only engineering
access, every commitment paper-trailed in the BAA. That's the
posture LPs will require, that auditors will sign off on, and that
won't make the news for the wrong reasons.

The line we hold throughout: customer's PHI is on the platform to
serve a documented analytical purpose, for the duration of the
contract, with full audit trail, accessible only to authorized
users with MFA. Everything outside that line is refused.
