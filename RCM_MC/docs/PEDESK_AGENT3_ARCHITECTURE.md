# PEDesk Agent 3 — Cross-Cutting Platform Architecture

**Status:** Architecture / design contract. Not yet implemented end-to-end.
**Owner:** The third PEDesk (RCM-MC) Claude Code agent.
**Audience:** All three PEDesk agents + a human reviewer with compliance sign-off authority.

This document defines the scope, design, and coordination model for the
**third** PEDesk agent. Agent 1 owns the analytics/prediction engine; Agent 2
owns ingestion, deliverables, and the app shell; **Agent 3 owns the
cross-cutting platform layers that the other two consume but neither should
build**: security & access control, compliance & audit governance, commercial
data-vendor connectors, the primary-research (expert-network) workflow with its
qualitative-synthesis tracker, and the data-room / deal-pipeline / engagement
spine.

It is grounded in the research report *"Filling the Gaps for the Third PEDesk
Agent"* and, more importantly, in **what already exists in this repository**.
Several of Agent 3's domains are already partially built (RBAC, a hash-chained
audit log, HIPAA/SOC 2 readiness artifacts, an expert-call program, an
engagement state machine, an integrations hub). Agent 3's job is therefore
mostly **extension and consolidation**, not greenfield construction.

---

## 0. The load-bearing constraint: this is a stdlib / SQLite / single-machine app

The research report recommends a cloud-native stack — PostgreSQL Row-Level
Security, FastAPI + OAuth2/JWT, Azure Key Vault, Snowflake/Databricks Delta
Sharing, OPA/Cedar policy engines. **None of that matches the platform as
built**, and the [`CLAUDE.md`](../CLAUDE.md) rules forbid drifting there
casually:

- **Tech stack today:** Python 3.10+, stdlib-heavy. Runtime deps are only
  `numpy`, `pandas`, `pyyaml`, `matplotlib`, `openpyxl`. HTTP is
  `http.server.ThreadingHTTPServer` — **no Flask/FastAPI**. Auth is stdlib
  `hashlib.scrypt` + session cookies — **no third-party IdP**. Storage is a
  single **SQLite** file (~89 tables) — **no Postgres path** ("Single-machine
  deployment. No clustering, no Postgres path." — `CLAUDE.md` Known limitations).
- **Hard rule:** *"No new runtime dependencies without explicit discussion."*
- **Existing posture:** [`docs/PHI_SECURITY_ARCHITECTURE.md`](PHI_SECURITY_ARCHITECTURE.md)
  already states the platform is **public-data-only today** and explicitly
  **will not accept PHI in the multi-tenant SaaS shape**.

This forces a **translation discipline**: every cloud-native recommendation in
the research must be either (a) implemented with stdlib/SQLite primitives, or
(b) recorded as a *future-stack* decision gated behind an explicit dependency
discussion and an ADR — never silently pulled in. The translation table:

| Research recommends | PEDesk translation (build now) | Future-stack (gated, ADR required) |
|---|---|---|
| PostgreSQL Row-Level Security | Request-scoped tenant middleware in `server.py` + a mandatory `tenant_id` column convention + a `WHERE tenant_id = ?` enforcement helper that **every** store query routes through, plus a CI lint that fails when a tenant-scoped table is queried without it | True DB-enforced RLS — only if/when a Postgres path is adopted |
| FastAPI + OAuth2/JWT + scopes | Existing stdlib session/CSRF + a scoped **capability-token** layer (`auth/audit_token.py` pattern) for API/service auth | FastAPI `SecurityScopes` — only under the existing `[api]` optional extra |
| Azure Key Vault + managed identity | Secrets from environment variables only, never committed; a thin `infra/secrets.py` indirection so the backend can be swapped | Key Vault / managed identity adapter behind `infra/secrets.py` |
| OPA / Cedar / Oso policy engine | A stdlib ABAC evaluator: pure-Python predicate functions over a `SubjectAttributes`/`ResourceAttributes`/`Context` triple | Externalized policy engine — only if policy volume justifies it |
| Snowflake / Databricks Delta Sharing | One **adapter** per delivery modality behind the anti-corruption layer; ship the SFTP/bulk + REST modalities first (stdlib `urllib`/`ftplib`) | Native Snowflake/Databricks connectors behind their own optional extras |
| SOC 2 immutable blob anchoring (S3 Object Lock) | Hash-chain (already built in `compliance/audit_chain.py`) + periodic chain-head export to an append-only file the app process cannot rewrite | Cloud object-lock anchoring adapter |

**Rule of thumb:** Agent 3 builds the *seam* (the interface) now, with a
stdlib implementation behind it, so the cloud-native backend can be dropped in
later without touching callers. The seam is the deliverable; the cloud backend
is a future decision.

---

## 1. Scope: the five layers Agent 3 owns

| # | Layer | Owns | Does **not** own |
|---|---|---|---|
| 1 | **Security & access control** | Multi-tenancy seam, RBAC+ABAC, ethical walls/information barriers, SSO/SCIM seam, session & capability-token auth, secrets indirection | The HTTP server loop itself (Agent 2's `server.py`); business features behind the gates |
| 2 | **Compliance, governance & audit** | Data-classification taxonomy, immutable audit log + hash chain, HIPAA/SOC 2/MNPI control mapping, PHI scanner, retention policy | Generating the analytics that get audited (Agent 1); the export artifacts being retained (Agent 2) |
| 3 | **Commercial data-vendor connectors** | Anti-corruption layer (adapter/translator/facade per vendor), resilience (retry/circuit-breaker/cache), per-tenant entitlement enforcement, vendor credential handling | Public-data ingestion (Agent 2's `data/`, `data_public/`); the canonical analytics that consume normalized vendor data (Agent 1) |
| 4 | **Primary research & qualitative synthesis** | Expert-call lifecycle + MNPI guardrails, interview-guide management, the structured (non-generative) thematic-analysis tracker | The statistical prediction engine (Agent 1 — stays ML-only); deliverable rendering (Agent 2) |
| 5 | **Data-room, deal-pipeline & engagement** | VDR (DRL-mirrored, permissioned, watermarked, audited), deal-stage state machine, engagement/workstream management | Portfolio-monitoring analytics (Agent 2); the IC-memo/exit-memo rendering (Agent 2) |

**Cross-cutting invariant Agent 3 enforces:** *all prediction/forecasting stays
statistical/ML* (Agent 1's Ridge + conformal intervals, isolation forest,
changepoint). The qualitative-synthesis layer is a **structured human-coding
workflow** — a codebook, code-to-quote links, prevalence counts — and must
**never** become an LLM auto-summarizer, and must **never** feed the prediction
engine.

---

## 2. What already exists vs. the gap (per layer)

This is the honest starting line. Agent 3 should **extend the bolded existing
modules**, not re-create them.

### Layer 1 — Security & access control

| Capability | Status | Where |
|---|---|---|
| scrypt passwords, sessions, CSRF, login rate-limit | ✅ exists | `auth/auth.py`, `server.py` |
| Flat 6-tier RBAC + `check_permission` | ✅ exists | `auth/rbac.py` |
| External/LP per-deal access grants | ✅ exists | `auth/external_users.py` |
| Scoped capability tokens | ✅ exists (pattern) | `auth/audit_token.py` |
| **Multi-tenancy / tenant isolation** | ❌ **gap** — `tenant` in code means only real-estate tenants; the app is single-tenant | — |
| **ABAC (attribute conditions: classification, deal-team, MFA, location)** | ❌ **gap** | — |
| **Ethical walls / information barriers** | ❌ **gap** — no `barrier`/`wall`/`restricted-list` code | — |
| **SSO (SAML/OIDC) + SCIM deprovisioning + MFA** | ❌ **gap** | — |
| **Secrets indirection** | ⚠️ partial — env vars used ad hoc; no `infra/secrets.py` seam | — |

### Layer 2 — Compliance, governance & audit

| Capability | Status | Where |
|---|---|---|
| Append-only audit log of state-changing actions | ✅ exists | `auth/audit_log.py` |
| **Hash-chained tamper-evident audit** (SHA-256 links) | ✅ exists | `compliance/audit_chain.py` (`verify_chain`) |
| Pattern-based PHI scanner (CI-friendly) | ✅ exists | `compliance/phi_scanner.py` |
| HIPAA readiness + SOC 2 control mapping docs | ✅ exists | `compliance/HIPAA_READINESS.md`, `compliance/SOC2_CONTROL_MAPPING.md`, `docs/PHI_SECURITY_ARCHITECTURE.md` |
| **Four-tier data-classification attribute** (public/internal/confidential/restricted) wired into access + retention | ❌ **gap** | — |
| **DB-level UPDATE/DELETE revocation on audit table** | ⚠️ N/A on SQLite — replace with trigger + chain-head export | — |
| **MNPI restricted/watch-list + wall-crossing registers** | ❌ **gap** | — |
| **Retention schedule engine** | ❌ **gap** | — |

### Layer 3 — Commercial data-vendor connectors

| Capability | Status | Where |
|---|---|---|
| CRM/PMS sync (DealCloud/Salesforce/Sheets; Allvue/Cobalt/Investran iface) | ✅ exists | `integrations/integration_hub.py`, `integrations/pms/` |
| Tuva / dbt-duckdb diligence ingestion bridge | ✅ exists (isolated, optional extra) | `rcm_mc_diligence/`, `diligence/ingest/tuva_bridge.py` |
| **Anti-corruption layer for commercial health-data vendors** (Definitive, IQVIA, Komodo, Trilliant, Clarivate, Symphony) | ❌ **gap** | — |
| **Resilience primitives** (retry+jitter, circuit breaker, response cache, token-bucket rate limit) | ❌ **gap** | — |
| **Per-tenant entitlement enforcement** | ❌ **gap** | — |

### Layer 4 — Primary research & qualitative synthesis

| Capability | Status | Where |
|---|---|---|
| Expert-call program core (stakeholder lenses, question bank, call guide, coverage read) | ✅ exists | `diligence/expert_calls.py` |
| Cross-module diligence synthesis (narrative through-line) | ✅ exists | `diligence_synthesis/runner.py`, `dossier.py` |
| **Expert-call compliance lifecycle** (attestations, restricted-topic checks, conflict screening, call logging w/ retention, MNPI flags) | ❌ **gap** | — |
| **Structured thematic-analysis tracker** (codebook, code→quote linkage, prevalence counts, multi-coder/IRR, triangulation) | ❌ **gap** — existing synthesis is narrative, not coded | — |

### Layer 5 — Data-room, deal-pipeline & engagement

| Capability | Status | Where |
|---|---|---|
| Per-engagement RBAC + draft/publish/archive state machine + comments + deliverables | ✅ exists | `engagement/store.py` |
| Deal lifecycle (create/archive/clone/delete-cascade/pin/validate/IC checklist) | ✅ exists | `deals/`, `portfolio/` |
| VDR tracker page (DRL status surface) | ⚠️ partial — a tracker UI, not a permissioned/watermarked/audited room | `ui/data_public/vdr_tracker_page.py` |
| **Full VDR** (folder tree mirroring the DRL, granular folder/file perms, watermarks, view/download audit trail, staged disclosure, per-bidder isolation, Q&A workflow) | ❌ **gap** | — |
| **Explicit deal-pipeline state machine** (origination → screening → diligence → IC → close → monitoring with stage-gated permissions) | ⚠️ partial — stages exist as data; no enforced gate machine | — |

---

## 3. Layer designs (stdlib-grounded)

### 3.1 Security & access control

**Multi-tenancy (pool model + defense in depth).** Adopt the shared-schema
"pool" model: every tenant-scoped table carries a `tenant_id` column. Enforce
at **two** layers so an application bug cannot leak across tenants:

1. **Application layer (primary):** a request-scoped `TenantContext` resolved
   from the session/token in `server.py` and threaded through. A
   `get_tenant_id()` accessor **raises** if called outside a request context —
   this catches background jobs and cron paths that would otherwise run
   unscoped. All `portfolio/store.py` reads/writes on tenant-scoped tables go
   through a `scoped(con, sql, params)` helper that injects the
   `tenant_id` predicate.
2. **Storage layer (backstop):** since SQLite has no RLS, add (a) a CI lint
   that fails when a tenant-scoped table is referenced without the scoping
   helper, and (b) a per-tenant integrity test in `tests/` that seeds two
   tenants and asserts zero cross-read. Escalate a marquee/regulated tenant to
   a **separate SQLite file** (silo) only when a contract demands physical
   separation — the `store` connection manager already abstracts the DB path,
   so silo = "this tenant gets its own `.db`".

**RBAC + ABAC hybrid.** Keep `auth/rbac.py` as the coarse role gate. Add
`auth/abac.py`: a pure-Python evaluator over three attribute bags —
`SubjectAttributes` (tenant_id, role, deal-team membership, clearance,
mfa_satisfied, account_locked), `ResourceAttributes` (tenant_id,
classification, deal_id/deal-team), and `Context` (request time, ip/location).
A decision is `permit` only when role grants the action **and** every ABAC
predicate passes (e.g., `subject.tenant_id == resource.tenant_id`,
`classification_rank(resource) <= clearance_rank(subject)`,
`not subject.account_locked`, `subject.mfa_satisfied`). This is the seam the
research's "RBAC+ABAC keyed on tenant attributes" calls for, with the *option*
to swap in OPA/Cedar later. (Do **not** cite the unsourced "RBAC covers ~90%"
folklore; NIST SP 800-162 is the ABAC reference for the *definition* only.)

**Ethical walls / information barriers.** Model walls as ABAC, not a separate
system: (a) deal-team membership is a subject attribute and a resource
attribute; (b) a `barriers` table records pairs of deals flagged
adverse/competing and a separate internal-Chartis-vs-external-PE-client wall;
(c) the ABAC evaluator denies any cross-wall access and (d) writes a
`wall_event` to the audit log on every block and every wall-crossing grant; (e)
a conflict-check runs at user/deal assignment time.

**Identity / SSO / SCIM.** FastAPI/Authlib is future-stack. The seam to build
now: an `auth/identity.py` provider interface with a default
`LocalPasswordProvider` (today's scrypt flow) and a documented `SsoProvider`
contract (OIDC/SAML → normalized profile) plus a `ScimProvisioner` contract
whose `deprovision(user)` flips `is_active=False` so `get_current_user` returns
401 on the next request. MFA = a TOTP attribute on the subject feeding ABAC.

**Secrets.** Add `infra/secrets.py` with a single `get_secret(name)` that reads
from environment variables today and can be backed by Key Vault later. No
vendor key or connection string is ever committed; all credential access is
logged through the audit layer.

### 3.2 Compliance, governance & audit

**Data classification** is a first-class attribute (`public` < `internal` <
`confidential` < `restricted`) attached to datasets *and* documents. It drives
ABAC clearance checks, VDR permissions, retention, and audit verbosity.
**Target-provided diligence data defaults to `restricted`/potential-PHI** — the
danger zone per `PHI_SECURITY_ARCHITECTURE.md` — and gets minimum-necessary
access and fullest logging.

**Immutable audit log.** Build on the existing chain:
`auth/audit_log.py` (writer) + `compliance/audit_chain.py` (SHA-256 links,
`verify_chain`). Add: (1) a canonical event schema (actor, action, resource,
tenant, deal, classification, timestamp); (2) a SQLite `BEFORE UPDATE/DELETE`
trigger on the audit table that raises (the SQLite analogue of `REVOKE
UPDATE/DELETE`); (3) periodic export of the latest chain head to an append-only
file/object the app process cannot rewrite (tamper anchor); (4) a CI/cron
verification job that re-walks the chain. This satisfies SOC 2, HIPAA, and SEC
§204A evidence demands with stdlib only.

**MNPI controls.** A `restricted_list` / `watch_list` table with reason notes
on add/remove (kept separate from NDA lists), `wall_crossing` records, and
expert-call logs (≥3-year retention) — all flowing to the immutable audit log.
This realizes §204A's "written policies reasonably designed to prevent misuse
of MNPI."

**Retention engine.** A per-classification retention schedule that the audit
log records but does not silently enforce destructive deletes — destructive
actions remain operator-driven and logged.

### 3.3 Commercial data-vendor connectors

**Anti-corruption layer (DDD).** One package, `connectors/`, structured as
Facade → Adapter → Translator → canonical model:

```
connectors/
  canonical.py        # Provider, Facility, Claim, Prescriber, Market dataclasses
  base.py             # VendorAdapter + Translator + Facade protocols; resilience mixins
  resilience.py       # retry(+jitter, honor Retry-After), CircuitBreaker, TTL cache, token-bucket
  entitlements.py     # per-tenant entitlement records + check at the boundary
  definitive/  iqvia/  komodo/  trilliant/  clarivate/  symphony/
                      #   adapter.py (protocol: REST | SFTP | cloud-share | platform-export)
                      #   translator.py (vendor schema -> canonical.py)
```

- **Adapter** handles protocol (HTTP via stdlib/`urllib` or `httpx` if already
  present; SFTP via `ftplib`/`paramiko` only under an optional extra; cloud
  share + platform export are future-stack adapters), auth, retries,
  pagination.
- **Translator** maps each vendor's schema to `canonical.py`. Swapping a vendor
  that changes delivery (e.g., Trilliant retired its REST APIs 2025-07-24 and
  moved to Databricks Marketplace) means swapping the **adapter** without
  touching the canonical model — that decoupling is the whole point.
- **Four delivery modalities** must be supported because the vendor mix spans
  all of them: cloud data share, REST API, SFTP/bulk, proprietary-platform
  export.

**Resilience.** Retry with exponential backoff + jitter (honor `Retry-After`
before backoff math; retry 429/5xx, fail fast on 4xx); a three-state circuit
breaker (CLOSED→OPEN→HALF-OPEN) so a down vendor fails fast; idempotency keys
on writes; TTL response cache that also serves as the graceful-degradation
fallback when a vendor is unavailable; client-side token-bucket rate limiting;
per-vendor cost/spend tracking with budget alerts (IQVIA pay-per-use, Komodo
per-use-case priced).

**Entitlements.** Per-tenant entitlement records (sourced from the
contract/billing source of truth) gate which vendor datasets a tenant/user may
access. Enforce at the connector boundary **and** the API layer — a contractual
requirement with the data vendors.

### 3.4 Primary research & qualitative synthesis

**Expert-call lifecycle** extends `diligence/expert_calls.py` (which already has
the lens taxonomy, question bank, guide builder, coverage read) with the
compliance wrapper the SEC expects for expert networks (tailored, not generic):

- pre-call **attestation** capture (expert confirms no MNPI/confidentiality
  breach);
- **restricted-topic** checks (forward-looking financials, unannounced
  transactions, pending regulatory decisions);
- **conflict screening** against the client's competitive landscape / supply
  chain / current transactions / litigation (the record goes into the client
  diligence file);
- **employer-permission / employment-history** verification;
- recording prohibitions, bidirectional NDA, **call logging** (expert, client,
  topic, date, duration, fees, notes) retained ≥3 years;
- chaperoning capability and **per-expert call-count limits** (repeat-call MNPI
  risk);
- every event → the immutable audit log + MNPI/wall-crossing flags.

**Structured qualitative synthesis (NOT an LLM summarizer).** A new
`primary_research/synthesis/` tracker implementing Braun & Clarke's six-phase
thematic analysis as a *workflow*, distinct from the existing narrative
`diligence_synthesis/`:

1. familiarization (verbatim transcript storage);
2. initial codes (line-by-line; a code may apply to many statements);
3. searching for themes; 4. reviewing themes; 5. defining/naming themes
   (a managed **codebook**); 6. writing up.

It tracks a **codebook**, **code→quote linkage**, **prevalence counts**
("X of Y experts indicated…", reported with sample composition rather than
cherry-picked quotes), **multiple coders + inter-rater reliability**, and
**triangulation** across sources — preserving full traceability from raw
transcript → coded text → theme → finding. This is structured tracking, not
generation, and it is **firewalled from the prediction engine**.

### 3.5 Data-room, deal-pipeline & engagement

**VDR.** Upgrade the `vdr_tracker_page` into a real room: a folder tree
mirroring the document-request-list (DRL) with status indicators
(incomplete/received/reviewed); granular folder- and file-level permissions
(driven by ABAC + classification); view-only/no-download modes; watermarks; an
NDA/terms gate before entry; a full **audit trail of every login/view/download**
(legal evidence of what was disclosed when); **staged disclosure** (teaser room
vs. confidential diligence room) and per-bidder isolation; a Q&A workflow
linking buyer questions to specific documents.

**Deal-pipeline state machine.** Formalize the stages
origination → screening → diligence → IC → close → monitoring as an enforced
gate machine with per-stage permissions. The **monitoring** stage hands off to
Agent 2's portfolio-monitoring analytics: Agent 3 owns the stage state +
access; Agent 2 owns the monitoring analytics/alerting.

**Engagement management** extends `engagement/store.py`: workstream tracking,
staffing/resourcing, timeline/milestones, document versioning + access control.
Deliverables hand off to Agent 2's deliverable-production layer.

---

## 4. Frozen interface contracts (land these FIRST)

Per the research's strongest coordination finding, Agent 3 publishes a small,
**frozen** contract surface that Agent 1 and Agent 2 import but never modify
mid-sprint. Freezing prevents the most common multi-agent failure (diverging
shared types). Proposed location: `rcm_mc/contracts/` (a thin, dependency-free
package — protocols + dataclasses + raising stubs only).

| Contract | Shape | Consumed by |
|---|---|---|
| `TenantContext` / `get_tenant_id()` | request-scoped accessor; raises outside a request | everyone touching tenant-scoped data |
| `AuthorizationDecision` / `authorize(subject, resource, action, ctx)` | RBAC+ABAC entry point returning permit/deny + reason | every gated route/feature |
| `AuditLogger.emit(event)` | canonical event schema writer | every state-changing action |
| `EntitlementChecker.check(tenant, dataset)` | boolean gate at the connector boundary | connectors + analytics that read vendor data |
| `CanonicalRecord` family (`Provider`, `Facility`, `Claim`, `Prescriber`, `Market`) | the connector→analytics handoff schema | Agent 1 analytics |
| `Classification` enum + `classify(resource)` | public/internal/confidential/restricted | VDR, retention, ABAC |

**Change protocol:** a frozen contract is changed only by re-cutting it through
an explicit, logged change in `TASKS.md` (see §5) — never a silent edit.

---

## 5. Three-agent coordination model

### 5.1 Directory / file ownership map

Each agent owns non-overlapping packages. Mapped to **actual** repo packages
(not the research's generic names):

| Agent | Owns (edit freely) | Off-limits |
|---|---|---|
| **Agent 1 — analytics/prediction** | `core/`, `mc/`, `pe/`, `rcm/`, `finance/`, `scenarios/`, `analysis/`, `ml/`, `causal/`, and the *analytic* diligence modules | everything below |
| **Agent 2 — ingestion/deliverables/app-shell** | `data/`, `data_public/`, `rcm_mc_diligence/` ingestion, `reports/`, `exports/`, `ic_memo/`, `ic_binder/`, `portfolio_monitor/`, `ui/`, `server.py`, **`tests/` + CI** | Agent 3's security/compliance/connector internals |
| **Agent 3 — cross-cutting platform** | `auth/`, `compliance/`, `engagement/`, `integrations/` + new `connectors/`, `primary_research/` (expert-call compliance + synthesis tracker), VDR/data-room modules, deal-pipeline state machine, new `contracts/`, `infra/secrets.py` | `core/`/`ml/` math, `ui/` rendering, `data*/` ingestion |

`diligence/expert_calls.py` and `diligence_synthesis/` straddle the line: Agent 3
owns the **compliance + thematic-coding** additions; their analytic outputs stay
readable by Agent 1.

### 5.2 The other coordination rails

- **Frozen `contracts/` module** (§4) — landed first, imported by all, modified
  by none mid-sprint.
- **`TASKS.md` ledger** at repo root — each agent marks tasks
  in-progress/done so work isn't duplicated, and files cross-agent requests
  (dependency needs, contract-change requests) here. Filesystem isolation
  (worktrees) + work-allocation coordination (the ledger) are *both* required.
- **Single config owner.** Package manifests (`pyproject.toml`), CI
  (`.github/workflows/`), and root `CLAUDE.md` are the classic three-way
  collision points. **Agent 2 is the config owner** (it already owns tests/CI).
  Agents 1 and 3 request dependency/CI changes via `TASKS.md` rather than
  editing those files directly. A single **migration owner** serializes
  schema-migration edits. (Note: per `CLAUDE.md`, *no new runtime dependency*
  lands without explicit discussion — so connector deps like a cloud-share SDK
  go through an ADR + the config owner, never a silent add.)
- **Merge sequencing.** Because Agent 3 provides the cross-cutting seams
  (tenant context, authorize, audit emit, entitlements) that 1 and 2 consume,
  land in order: **contracts → security/governance → connectors → consumers.**
  PR-per-agent with CI + review; always branch worktrees from the stable base
  (`main`), never from each other; commit incrementally for a clean audit trail.
- **Worktrees.** Each agent runs in its own git worktree; three is well within
  the practical 2–4 sweet spot.

---

## 6. Staged roadmap

| Stage | Deliverable | Gate to advance |
|---|---|---|
| **0** | This doc + `TASKS.md` ledger + ownership map agreed | Reviewer sign-off on scope/boundaries |
| **1** | Freeze `contracts/` (TenantContext, authorize, audit emit, entitlement, canonical records, classification) | All three agents import the frozen surface |
| **2** | Security spine: pool-model tenant scoping + CI lint + ABAC evaluator + ethical-wall ABAC + secrets seam; SSO/SCIM seams stubbed | Cross-tenant integrity test passes; ABAC denies cross-wall |
| **3** | Governance: 4-tier classification wired into ABAC/retention; audit trigger + chain-head anchor + verification job; MNPI registers; SOC 2 control map updated | `verify_chain` green in CI; classification on every dataset/doc |
| **4** | Connectors: ACL (adapter/translator/facade) for the vendor set; resilience primitives; entitlement enforcement at the boundary | One vendor end-to-end through canonical model behind entitlements |
| **5** | Primary research: expert-call compliance lifecycle + thematic-analysis tracker (non-generative, firewalled from predictor); then VDR + deal-stage machine + engagement extensions | Attestation/restricted-topic/conflict checks logged; VDR audit trail complete |

**Escalation thresholds** (when to deviate from the stdlib path): a client
contract requiring physical separation → silo that tenant to its own SQLite
file (or open the Postgres ADR); a vendor changing delivery mechanism → swap the
adapter only; policy volume outgrowing pure-Python ABAC → open the OPA/Cedar
ADR. Each deviation is an ADR under `docs/adr/`, routed through the config owner.

---

## 7. Caveats (carried from the research)

- **Vendor specifics shift.** Trilliant retired its public REST APIs
  (2025-07-24); Clarivate was reportedly exploring a sale of its Life Sciences &
  Healthcare segment (early 2026). Verify current delivery mechanisms at
  integration time. A public REST API / cloud-share for Symphony Health, and a
  Snowflake/Databricks share for Clarivate, could not be confirmed — absence of
  evidence, not evidence of absence.
- **Compliance guidance here is implementation-oriented, not legal advice.** The
  HIPAA de-identification (Safe Harbor §164.514(b)(2) / Expert Determination
  §164.514(b)(1)), SEC §204A, and SOC 2 specifics are accurate to authoritative
  sources, but a regulated PE/consulting deployment needs compliance-counsel
  sign-off — especially on Expert Determination and ethical-wall design.
- **The "~90% RBAC" figure is unsourced folklore** — not in NIST SP 800-162.
  Don't cite it.
- **Marketing vs. architecture.** Isolation-model, identity-provider, and VDR
  vendor write-ups are well-corroborated as *patterns*; specific product claims
  (pricing, "first partner," AI features) are marketing — verify independently.
