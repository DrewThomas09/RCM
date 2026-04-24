# Auth

Multi-user authentication, role-based access control, audit logging, and external user management.

---

## `auth.py` — User Management and Session Authentication

**What it does:** Manages user accounts, password hashing, session tokens, and login rate limiting. Provides the authentication layer for the HTTP server.

**How it works:** Passwords hashed with `hashlib.scrypt` (N=65536, r=8, p=1) and a 32-byte random salt — no third-party dependencies. Session tokens are 32-byte URL-safe random strings generated via `secrets.token_urlsafe(32)`, stored in the `sessions` table with a `TTL` of 24 hours. `create_user(username, password, role)` validates the username (alphanumeric, 3–32 chars) and password strength (8+ chars, mixed case + digit), hashes the password, and inserts. `authenticate(username, password)` — verifies hash, creates a session token, returns it. Rate limiting: after 5 failed logins from an IP in 10 minutes, that IP is locked out for 30 minutes (tracked in a module-level dict, reset on server restart). `check_session(token)` validates the session and updates `last_seen`.

**Data in:** Username/password from the login form (`POST /login`); session cookie from the request.

**Data out:** Session token (set as `HttpOnly; SameSite=Strict` cookie); `username` and `role` for the request handler; audit log entry via `audit_log.py`.

---

## `rbac.py` — Role-Based Access Control

**What it does:** Six-tier role hierarchy (ADMIN > PARTNER > VP > ASSOCIATE > ANALYST > VIEWER) with flat permission sets. Single enforcement point for all route handlers.

**How it works:** `ROLE_PERMISSIONS` dict maps each role to a frozenset of permission strings (e.g., `'deal.delete'`, `'user.manage'`, `'export.lp_update'`, `'analysis.run'`). Permissions are cumulative upward — each role inherits all permissions of roles below it. `check_permission(username, permission, store)` looks up the user's role in the `users` table and checks the permission frozenset. `require_permission(permission)` is a decorator for route handlers that calls `check_permission` and returns 403 if unauthorized. External users (management team, LPs) are handled by `external_users.py` with read-only subsets.

**Data in:** Username from the session; user role from the `users` SQLite table.

**Data out:** `True / False` permission check; 403 response for unauthorized requests.

---

## `audit_log.py` — Unified Append-Only Audit Log

**What it does:** Single pane of glass across all sensitive operations. Every login, deal change, export generation, user management action, and override is logged here.

**How it works:** `audit_events` table with: `event_id` (UUID), `event_type` (login / deal_create / deal_delete / analysis_run / export_generate / user_create / override_set / etc.), `actor` (username), `target_id` (deal_id or user_id), `metadata` (JSON with relevant context), `ip_address`, `created_at`. `log_event(event_type, actor, target_id, metadata)` always inserts (never updates). `query_log(actor, event_type, since, limit)` for the admin audit view. `deal_audit_trail(deal_id)` for the per-deal audit panel. Rows are never deleted (use `data_retention.py` for GDPR purge).

**Data in:** Called by `server.py` route handlers and all modules that perform sensitive operations.

**Data out:** Audit event rows for the admin audit log page (`GET /admin/audit`) and per-deal audit trail panel.

---

## `external_users.py` — External Portal Users

**What it does:** Manages read-only external user accounts for two portal types: management team (per-deal read-only) and LP (fund-level read-only quarterly reporting).

**How it works:** `external_users` table with: `username`, `external_type` (management / lp), `deal_id` (nullable — set for management users scoped to a specific deal), `created_by`, `expires_at`. `create_external_user(type, deal_id, expires_days)` generates a temporary username+password and scoped token. `check_external_access(username, deal_id)` verifies the user can see that deal. Management users can only read their deal's overview, metrics, and LP update. LP users can only read the fund-level LP report. External accounts auto-expire (enforced on login, not by cron).

**Data in:** Admin-created external user invitations via `POST /admin/external-users`.

**Data out:** Scoped session tokens for the external portal; access control checks for management and LP routes.

---

## Key Concepts

- **No external identity providers**: All auth is stdlib `hashlib.scrypt` + `secrets`. The entire auth layer is auditable in one file.
- **Append-only audit**: Audit rows are never updated or deleted. Every sensitive handler writes to one table.
- **Role hierarchy with explicit permissions**: Roles are defined as cumulative permission sets — adding a new permission to one role does not silently affect others.
