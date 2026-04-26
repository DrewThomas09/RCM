# Report 0147: Schema Inventory — `users` + `sessions` SQLite Tables

## Scope

Schema-walks `users` and `sessions` (defined together in `auth/auth.py:87-124`). Both referenced repeatedly (Reports 0021, 0090, 0108, 0123, 0134) but **never schema-walked**. Sister to all prior schema reports (0017, 0047, 0077, 0087, 0102, 0104, 0107, 0117, 0123, 0133, 0134, 0137).

## Findings

### `users` table (auth/auth.py:91-98)

```sql
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password_hash BLOB NOT NULL,
    password_salt BLOB NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL DEFAULT 'analyst',
    created_at TEXT NOT NULL
)
```

#### Field inventory (6 fields)

| # | Field | Type | NULL? | Default | Note |
|---|---|---|---|---|---|
| 1 | `username` | TEXT PRIMARY KEY | NOT NULL | — | unique identity |
| 2 | `password_hash` | BLOB | NOT NULL | — | scrypt hash (per Report 0021) |
| 3 | `password_salt` | BLOB | NOT NULL | — | per-user salt for scrypt |
| 4 | `display_name` | TEXT | NOT NULL | `''` | optional display |
| 5 | `role` | TEXT | NOT NULL | `'analyst'` | free-form (yet another instance) |
| 6 | `created_at` | TEXT | NOT NULL | — | ISO-8601 |

**6 fields. PRIMARY KEY on username.** No secondary indexes — single PK lookup pattern.

### `sessions` table (auth/auth.py:101-108 + lazy ALTER 115-119)

```sql
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(username) REFERENCES users(username)
)
-- Plus lazy ALTER:
ALTER TABLE sessions
    ADD COLUMN last_seen_at TEXT NOT NULL DEFAULT ''
```

#### Field inventory (5 fields)

| # | Field | Type | NULL? | Default | Note |
|---|---|---|---|---|---|
| 1 | `token` | TEXT PRIMARY KEY | NOT NULL | — | `secrets.token_urlsafe(32)` per Report 0021 |
| 2 | `username` | TEXT | NOT NULL | — | **FK → users(username)** (no cascade specified) |
| 3 | `expires_at` | TEXT | NOT NULL | — | absolute TTL, default 7 days per Report 0090 |
| 4 | `created_at` | TEXT | NOT NULL | — | ISO-8601 |
| 5 | `last_seen_at` | TEXT | NOT NULL | `''` | added via lazy ALTER; touched per request (Report 0090) |

Index: `idx_sessions_username ON sessions(username)` — supports per-user session listing.

### MAJOR FINDING — 4th FK behavior NEW

Per Report 0118 PRAGMA comment, 4 FK-bearing tables: `deal_overrides`, `analysis_runs`, `mc_simulation_runs`, `generated_exports`.

**This iteration discovers a 5th: `sessions.username → users(username)`.** **NOT listed in the PRAGMA comment.**

**MR817 below** — comment is incomplete.

### Cascade-behavior inconsistency intensifies

| Table | FK | ON DELETE behavior |
|---|---|---|
| `mc_simulation_runs.deal_id` | → deals | **CASCADE** |
| `deal_overrides.deal_id` | → deals | **CASCADE** |
| `generated_exports.deal_id` | → deals | **SET NULL** |
| `analysis_runs.deal_id` | → deals (TBD per MR678) | TBD |
| **`sessions.username`** | **→ users** | **(unspecified — defaults to NO ACTION)** |

**4 distinct cascade behaviors so far** (CASCADE, SET NULL, NO ACTION, TBD). Cross-link Reports 0117 MR668, 0133 MR756, 0134 MR761. **MR817 escalates.**

**Implication of `sessions` no-cascade**: deleting a user with active sessions FAILS with IntegrityError. **Operator must clear sessions first.** Cross-link Report 0123 `export_user_data` (which queries sessions) — GDPR delete-user request would fail unless sessions purged first.

### Lazy ALTER pattern (cross-link Report 0123 MR701)

`auth/auth.py:113-119`:

```python
cols = {r[1] for r in con.execute(
    "PRAGMA table_info(sessions)").fetchall()}
if "last_seen_at" not in cols:
    con.execute(
        "ALTER TABLE sessions "
        "ADD COLUMN last_seen_at TEXT NOT NULL DEFAULT ''"
    )
```

**Same idiom as audit_log.py:62-65 (Report 0123 cross-correction).** Per-module migration via PRAGMA-table-info → check column → ALTER.

This is the **2nd confirmed instance** of the de-facto migration pattern. **Cross-correction Report 0017 + 0027 + 0117**: codebase DOES have schema-evolution discipline; just per-module rather than centralized. Report 0123 MR701 was correct.

### `role` free-form TEXT — 7th instance of project-wide pattern

Per Reports 0087 MR483 (audit_events.event_type → action), 0102 MR560 (hospital_benchmarks.metric_key), 0104 MR580 (webhooks.events), 0107 (data_source_status.status), 0117 MR676 (mc_simulation_runs.scenario_label), 0133 (generated_exports.format).

**`users.role` default `'analyst'`** — typical values likely `'analyst'`, `'admin'` (per CLAUDE.md "users + roles" + per Report 0023 cli docs). No CHECK, no enum, no whitelist. **A typo `'analsyt'` silently denies admin access to its bearer until manually corrected.**

### Salt + hash discipline (cross-link Report 0021)

`password_hash` BLOB + `password_salt` BLOB stored separately. Per Report 0021: scrypt with N=2^14 (below OWASP minimum 2^15+, MR162 flagged in Report 0021).

**Per-user salt is correct** (vs single global salt). Compliant with auth best-practice.

### Cross-link to Report 0090 session timeout

`sessions.expires_at` = absolute 7-day TTL (Report 0090). `sessions.last_seen_at` = idle-timeout reference (touched per request).

**Two-gate expiry** confirmed by schema (both columns present).

### Cross-link to Report 0123 `enforce_retention`

Per Report 0123: `sessions` retention = 30 days based on `created_at`. **Report 0123 MR704 medium**: should use `last_seen_at` instead — confirmed concern, since active long sessions can be older than 30 days from `created_at` but freshly active.

### `users.created_at` index?

NO. The PK is on `username` (text-keyed), no time-based index. **`SELECT * FROM users ORDER BY created_at` would full-scan.** Acceptable for a small user base (per CLAUDE.md "single-machine deployment, 5-30 deals" — likely <100 users).

### Schema-inventory progress

After this report:

| Table | Walked? |
|---|---|
| 1. `deals` | Report 0017 |
| 2. `runs` | Report 0047 |
| 3. `analysis_runs` | Report 0077 (FK status pending re Report 0118 MR678) |
| 4. `audit_events` | Report 0123 (corrected 0087) |
| 5. `hospital_benchmarks` | Report 0102 |
| 6. `webhooks` | Report 0104 |
| 7. `webhook_deliveries` | Report 0104 |
| 8. `data_source_status` | Report 0107 |
| 9. `mc_simulation_runs` | Report 0117 |
| 10. `generated_exports` | Report 0133 |
| 11. `deal_overrides` | Report 0134 |
| 12. `deal_sim_inputs` | Report 0137 |
| 13. **`users`** | **0147 (this)** |
| 14. **`sessions`** | **0147 (this)** |

**14 tables walked.** Per Report 0091: 22+ in DB. ~8 unidentified remain.

### Importers / write sites

- `auth/auth.py` (creator + reader): `create_user`, `verify_password`, `create_session`, `user_for_session`, `revoke_session`, `cleanup_expired_sessions`
- `auth/audit_log.py` (Report 0063 audit-log writes capture `actor` from session)
- `infra/data_retention.py` (Report 0123): `enforce_retention` deletes old sessions; `export_user_data` queries sessions
- `analysis/refresh_scheduler.py` (Report 0111): not directly
- 8+ test files

### Cross-link to Report 0124 PortfolioStore

Both `users` and `sessions` are read/written via `store.connect()`. **Per Report 0124 MR708**: 5+ modules bypass the store with `sqlite3.connect()`. **None of those bypassers touch users/sessions** (auth is centralized). **Clean.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR817** | **Report 0118 PRAGMA comment lists 4 FK-bearing tables; this report finds a 5th (`sessions.username → users(username)`)** | Cross-correction. Possibly more undiscovered FKs. **MR761 cascade-policy gap escalates: 4 distinct behaviors (CASCADE × 2, SET NULL × 1, NO ACTION × 1, TBD × 1).** | **High** |
| **MR818** | **Deleting a user with active sessions FAILS with IntegrityError** (no cascade specified, defaults to NO ACTION) | Operator must `cleanup_expired_sessions` or DELETE sessions WHERE username=? first. GDPR delete-user (Report 0123) blocks. | **High** |
| **MR819** | **`role` is free-form TEXT — 7th instance of project-wide pattern** | A typo (`analsyt` vs `analyst`) silently denies role-gated access. No CHECK, no enum. | (carried) |
| **MR820** | **Lazy ALTER pattern for `last_seen_at`** is the 2nd confirmed instance (audit_log.py being the 1st per Report 0123) | Pattern is real and undocumented in CLAUDE.md. **Should be documented as the project's de-facto migration discipline.** | Medium |
| **MR821** | **`users.created_at` not indexed** — `ORDER BY created_at` full-scans | Acceptable for small user base. If user count grows >1000, becomes noticeable. | Low |
| **MR822** | **`sessions.last_seen_at TEXT NOT NULL DEFAULT ''`** — empty-string default | A migrated existing-session row gets `last_seen_at = ''`. `user_for_session` (Report 0090) parses this via `datetime.fromisoformat` — empty string raises ValueError, falls through. **Report 0090 MR497 silent edge case.** | Medium |

## Dependencies

- **Incoming:** auth/auth.py (creator, reader), audit_log (actor source), infra/data_retention (delete + export), tests.
- **Outgoing:** SQLite via store.connect(). hashlib.scrypt for password hashing.

## Open questions / Unknowns

- **Q1.** What other tables have FKs not listed in Report 0118 PRAGMA comment?
- **Q2.** What's the `analysis_runs` FK status (still open since Report 0118 MR678 + 0137)?
- **Q3.** Are there CHECK constraints on `role` somewhere (application-level vs DDL)?
- **Q4.** Does `cleanup_expired_sessions` clear sessions for a deleted user, or does an admin have to manually intervene?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0148** | Verify Report 0118 MR678 — does `analysis_runs` have an FK? (Last open FK frontier question.) |
| **0149** | Comprehensive PRAGMA cross-check: enumerate ALL FK constraints by querying `PRAGMA foreign_key_list(<table>)` for every table. |
| **0150** | Read `cli.py` head (1,252 lines, 14+ iterations owed). |

---

Report/Report-0147.md written.
Next iteration should: verify `analysis_runs` FK status — last open question on the FK frontier (Report 0118 MR678, carried 9+ iterations).
