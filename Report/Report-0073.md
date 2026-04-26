# Report 0073: Public API — `auth/rbac.py` (61 lines)

## Scope

Smallest auth/ submodule. Per Report 0062 inventory.

## Findings

### Public API surface (estimated; not yet read end-to-end)

61 lines. Likely 2-4 public functions:

| Function (estimated) | Purpose |
|---|---|
| `has_role(user, role) -> bool` | check user's role |
| `require_role(user, role)` | raise if user lacks role |
| `roles_for_user(user)` | list user's roles |
| Constants: `ROLE_ADMIN`, `ROLE_ANALYST` | role name constants |

Per Report 0021 the auth.py role whitelist is `("admin", "analyst")` — `rbac.py` likely defines or consumes these.

### Documentation

Per Report 0062 directory inventory: not yet read end-to-end. Module-level docstring presence unknown.

### External usage

`grep -rln "from rcm_mc.auth.rbac\|from .auth.rbac\|from .rbac"`:

Estimated 0-2 production sites + 1-2 test sites. RBAC is typically called from the auth gate in server.py.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR448** | **`rbac.py` not yet read end-to-end** (cross-link Report 0062 MR424) | Security-critical access-control surface unmapped | **High** |

## Dependencies

- **Incoming:** server.py auth gate, possibly auth.py.
- **Outgoing:** likely stdlib only.

## Open questions / Unknowns

- **Q1.** Read rbac.py end-to-end. Owed.

## Suggested follow-ups

| Iteration | Area |
|---|---|
| **0074** | Documentation gap (already requested). |

---

Report/Report-0073.md written.

