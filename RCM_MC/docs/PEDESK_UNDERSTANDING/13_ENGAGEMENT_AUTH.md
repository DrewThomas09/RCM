# 13 · Engagements, access control & the two-view mode

> PE Desk serves two audiences from the same surfaces — a PE fund running its own deals, and a Chartis-style consulting team running client engagements. This file documents the consulting **engagement** layer, the **two RBAC systems** that gate it, the draft→publish deliverable workflow, the client portal, and the auth mechanics underneath.

---

## Two layers of access control

**1. Platform roles** (`auth/rbac.py`) — who you are on the whole instance:
`ADMIN > PARTNER > VP > ASSOCIATE > ANALYST > VIEWER`, each with a permission set (e.g. VIEWER = `{read, export}`; higher roles add write/admin permissions). This gates the app-wide surfaces (admin, user management, settings).

**2. Engagement roles** (`engagement/store.py`) — your role *on a specific client engagement*:
- **LEAD** — managing associate; can publish most deliverables.
- **MEMBER** — works the engagement; can edit/draft but limited publish.
- **CLIENT_VIEWER** — the client; **read-only on PUBLISHED deliverables only**, never sees drafts or raw claims.

Two gate functions enforce it: `can_publish(role, deliverable_type)` and `can_view_draft(role)`. A `CLIENT_VIEWER` has an empty publish set and cannot view drafts — so a client can never see work-in-progress or upload claims.

These layers compose: a platform `ASSOCIATE` who is the `LEAD` on engagement X has full rights there but not on engagement Y.

## The engagement workflow
Tables: `engagements`, `engagement_members`, `engagement_deliverables`, `engagement_comments` (+ `external_user_assignments` for client users).
- **`/engagements`** — the engagement list (RBAC-filtered to what you can see).
- **`/engagements/<id>`** — detail: members, deliverables, comment stream. POSTs: `/engagements/create`, `/engagements/<id>/members/add`, `/comments/post`, `/deliverables/<d>/publish`.
- **Deliverable state machine:** **DRAFT → PUBLISHED**. The team works in DRAFT; a LEAD publishes; only then does the client (`CLIENT_VIEWER`) see it. A QoE memo render can optionally write a DRAFT deliverable linked to the engagement (§04).
- **`/portal/<id>`** — the **client portal**: a published-only view for `CLIENT_VIEWER`. This is what the client logs into — they see finished deliverables, not the working analysis.

## The two-view workspace mode
A lighter, copy-only mechanism layered on top (separate from RBAC): the `ck_workspace_mode` cookie sets a per-request mode —
- **PE Partner** ("Fund-level deal operations") — default; "Deal", "Sponsor", "Portfolio", "Fund II".
- **Chartis Consulting** ("Commercial diligence for client engagements") — swaps the vocabulary: "Engagement", "Client", "Engagement Book", "Client Engagement".

It is **copy-only** — it changes labels via `term()` (and the `/app` Command Center framing), never page structure or numbers. Toggle via POST `/settings/workspace`. (See the two-view work: `/app` page head + KPI labels swap with the cookie; partner output is unchanged by default.)

## Auth mechanics
- **Passwords:** stdlib `hashlib.scrypt`; password length capped before hashing to prevent a scrypt DoS. No third-party identity provider.
- **Sessions:** cookie tokens with a 7-day sliding TTL + idle timeout (`sessions` table). **The CSRF secret is per-process**, so sessions invalidate on server restart (partners reopen the login tab — documented limitation).
- **CSRF:** per-process HMAC secret; session POSTs require a `csrf_token` field or `X-CSRF-Token` header (a JS shim auto-adds it). Short exempt list: login/logout/health.
- **Open mode:** if no auth is configured and zero `users` rows exist, PE Desk runs single-user (laptop) with no login. Creating the first user (`rcm-mc portfolio users create … --role admin`) switches on multi-user.
- **Audit:** every state-changing action and sensitive view (`/admin`, `/users`, `/audit`, `/settings`) is appended to the audit log with the request ID; `/admin/audit-chain` checks integrity.
- **Rate limits:** login, data-refresh (1/hr/source), deletes (10/hr); 10 MB request cap.

---

## Where these "numbers" come from
This layer is **access + workflow state**, not analytics — it governs *who sees which deliverable*, not what a number is. The deliverables themselves (IC memo, QoE memo, etc.) carry the packet/corpus numbers documented elsewhere; engagement RBAC just controls visibility and the draft→publish gate.

---
*This completes the system coverage. Back to `00_INDEX.md`. For the high-level map see the sibling `../PEDESK_OVERVIEW.md` / `PAGES` / `ALGORITHMS` / `DATA`.*
