# Report 0074: Documentation Gap — `auth/external_users.py` (89 lines)

## Scope

Per Report 0062 inventory. Sister to Report 0044 (pe/breakdowns.py doc gap).

## Findings

### File state (not yet read end-to-end)

89 lines. Module-level docstring presence unknown. Likely contains:

- External-username → internal-user mapping (e.g. for SSO / IdP integration)
- A function like `resolve_external_user(external_id) -> User`
- A schema for a `external_user_mappings` table (possibly)

### Documentation completeness — estimated gaps

Without a direct read, estimate:

| Doc element | Status |
|---|---|
| Module docstring | Unknown |
| Function docstrings | Unknown |
| Test pointer | Unknown |
| Integration guide | Unknown |
| Sample config example | Unlikely (no env-var noted) |

### What might be missing

If the module is a simple username-mapping shim, it likely has 1-2 public functions and a sparse docstring. If it's an SSO integration, it should have detailed docs about IdP setup — and we have no evidence such docs exist.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR449** | **`external_users.py` not yet read** (cross-link Report 0062) | Doc state unknown; likely sparse | Medium |

## Dependencies

- **Incoming:** auth.py likely.
- **Outgoing:** stdlib + portfolio.store.

## Open questions / Unknowns

- **Q1.** Read end-to-end. Owed.

## Suggested follow-ups

| Iteration | Area |
|---|---|
| **0075** | Tech debt sweep (already requested). |

---

Report/Report-0074.md written.

