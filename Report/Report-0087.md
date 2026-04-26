# Report 0087: Schema / Type Inventory — `audit_events` SQLite Table

## Scope

Documents the `audit_events` SQLite table — the audit-log persistence schema referenced in Reports 0063 (audit_log.py file map), 0064 (incoming deps), 0065 (outgoing deps), 0072 (security spot-check), 0084 (auth cross-cut). Schema not previously walked field-by-field. Sister to Report 0027 (ServerConfig dataclass), Report 0057 (DealAnalysisPacket dataclass).

## Findings

### Table location

Per Report 0017 + 0063: `audit_events` lives in the same SQLite file as `users`, `sessions`, `deals`, etc. — single-file portfolio.db (CLAUDE.md: "single-machine deployment"). Created by `auth/audit_log.py::_ensure_table()` (per Report 0063 head section).

### Field inventory (reconstructed from Reports 0063 + 0064)

| # | Field | Type | NULL? | Default | Notes |
|---|---|---|---|---|---|
| 1 | `id` | INTEGER PRIMARY KEY AUTOINCREMENT | NO | rowid | per SQLite default |
| 2 | `event_at` | TEXT | NO | none — set in `log_event` | ISO-8601 UTC via `_iso(_utcnow())` per Report 0064 |
| 3 | `actor` | TEXT | YES | NULL | username; NULL when anonymous (login attempts) |
| 4 | `event_type` | TEXT | NO | none | string tag (e.g. `login_success`, `password_change`, `deal_archive`) |
| 5 | `target` | TEXT | YES | NULL | resource id (e.g. deal_id) |
| 6 | `detail_json` | TEXT | YES | NULL | json.dumps()'d dict; nullable per Report 0064 |

**6 fields.** Confirmed schema-shape from Report 0063: `_ensure_table` is idempotent `CREATE TABLE IF NOT EXISTS`.

### Constructor sites

Per Report 0064: 3 production call-sites in `server.py` to `log_event(actor, event_type, target, detail)`:
1. Authentication events (login success/failure)
2. Privileged ops (user create, password reset)
3. Deal-state mutations (archive/delete)

Plus tests via `test_audit_log.py` (per Report 0024 logging cross-cut).

### Validators / constraints

- **No CHECK constraints.** Free-form text fields.
- **No FK to `users.username`.** `actor` is denormalized — captures historical username even after user is deleted (good for audit). Per Report 0072 security spot-check, this is **intentional**.
- **No index** on `(event_type, event_at)` per Report 0017 schema scan. **Q1**.
- **`detail_json` is plain TEXT** — no JSON1 extension constraint. Caller must `json.dumps`; reader must `json.loads`.

### Type inference (Python ↔ SQL)

| Python `log_event` arg | SQL column | Conversion |
|---|---|---|
| `actor: Optional[str]` | TEXT NULL | direct |
| `event_type: str` | TEXT NOT NULL | direct |
| `target: Optional[str]` | TEXT NULL | direct |
| `detail: Optional[Dict[str, Any]]` | TEXT NULL | `json.dumps(detail)` then store |

`event_at` not parameterized — set internally to `datetime.now(timezone.utc).isoformat()`.

### Read sites (`list_events`)

Per Report 0065: `list_events` returns a `pandas.DataFrame`. SELECT by:
- `actor` filter
- `event_type` filter
- `event_at` window (since/until)
- `LIMIT` paginated

DataFrame columns mirror table columns 1:1.

### Migration history

Per Report 0017: `_ensure_table` is the **only** migration step. No ALTER TABLE in the codebase (per Report 0017). **A field-add requires manual ALTER + idempotency guard** — not currently a pattern in this codebase.

### Cross-link to Report 0064 audit-event registry

Per Report 0064: known `event_type` strings include:
- `login_success`, `login_failed`, `logout`
- `password_change`, `user_create`, `user_delete`
- `deal_archive`, `deal_delete`
- (CLI / scheduled jobs missing — Report 0084 MR-cross-link)

**No central enum or const for event_type strings.** String literals scattered across `server.py` 3 call-sites. **Typo-prone.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR483** | **`event_type` is free-form TEXT — no enum, no constants** | A typo at call-site (e.g. `login_succes`) silently writes a bad row. Reader (e.g. dashboard) filters on the wrong literal → silent miss. | **Medium** |
| **MR484** | **No index on `(event_type, event_at)` or `(actor, event_at)`** | `list_events` queries are full-scan. With audit-log retention growing (per Report 0072 retention question), latency degrades. | Medium |
| **MR485** | **`detail_json` schema is undefined per event_type** | `detail` for `login_failed` may carry `{ip, user_agent}`; for `deal_delete` may carry `{deal_id, cascade_count}`. No registry; consumers guess. | Medium |
| **MR486** | **Field-add requires manual schema-aware migration** | Per Report 0017, no migration framework. A branch that adds a 7th column needs both `ALTER TABLE` AND `_ensure_table` update with `IF NOT EXISTS` semantics. | High |
| **MR487** | **No retention policy implemented in code** | `audit_events` grows unbounded. Per Report 0072 the table is the legal record-of-truth — but no cron/CLI prune. Disk grows linearly with usage. | **High** |

## Dependencies

- **Incoming:** `auth/audit_log.py::log_event` (writer), `list_events` (reader), test_audit_log.py.
- **Outgoing:** SQLite via `PortfolioStore.connect()` (per Report 0065).

## Open questions / Unknowns

- **Q1.** Is there an index on `audit_events`? `_ensure_table` body not extracted.
- **Q2.** What is the full `event_type` enumeration as actually used in production?
- **Q3.** Retention/prune policy — does anything ever DELETE from `audit_events`?
- **Q4.** Is `detail_json` ever NOT-JSON (e.g. plain string)? Any defensive `try/except json.JSONDecodeError` on read?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0088** | Config value trace (already requested). |
| **future** | Read `_ensure_table` body in `auth/audit_log.py` to close Q1. |
| **future** | Grep all `log_event(` call-sites to enumerate `event_type` literals (closes Q2). |

---

Report/Report-0087.md written.
Next iteration should: CONFIG VALUE TRACE — pick a value not yet traced (e.g. session idle timeout, CSRF secret seed, refresh rate-limit values).
