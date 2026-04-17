# Auth

Multi-user authentication, role-based access control, audit logging, and external user management. Provides per-user identities with session cookies while preserving backward compatibility with legacy single-user HTTP Basic auth.

| File | Purpose |
|------|---------|
| `auth.py` | User management with scrypt password hashing, session tokens (32-byte URL-safe randoms), and admin/analyst role support |
| `rbac.py` | Role-based access control with a six-tier hierarchy (ADMIN > PARTNER > VP > ASSOCIATE > ANALYST > VIEWER) and flat permission sets |
| `audit_log.py` | Unified append-only `audit_events` table providing a single pane of glass across all sensitive operations |
| `external_users.py` | External user management for management team (read-only per-deal) and LP (read-only fund-level) portal access |

## Key Concepts

- **Role hierarchy**: Six roles with escalating permissions; `check_permission` is the single enforcement point for all route handlers.
- **Append-only audit**: Audit rows are never updated or deleted. Every sensitive handler writes to one table.
- **No external deps**: Password hashing uses stdlib `hashlib.scrypt`; sessions are stdlib `secrets` tokens.
