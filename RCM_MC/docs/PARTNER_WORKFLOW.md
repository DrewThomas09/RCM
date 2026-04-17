# Partner workflow guide

A single-page index of the capabilities that landed in bricks B101–B160.
Existing docs in this folder cover the simulator/bench layers; this
document covers the portfolio-operations layer a PE partner actually
touches day to day.

## Bootstrap

```bash
# First admin (switches the server into multi-user mode)
.venv/bin/python -m rcm_mc.portfolio_cmd --db portfolio.db \
    users create --username boss --password "StrongPass!1" --role admin

# Launch
rcm-mc serve --db portfolio.db --port 8080

# Open http://localhost:8080 → redirected to /login
```

Single-user mode (no users in DB) leaves the UI open — useful for a
laptop deploy. Creating the first user locks it down automatically.

## The Monday-morning partner routine

| Partner question | Where to look |
|---|---|
| "What broke over the weekend?" | `/alerts` |
| "What's been red for 30+ days?" | `/escalations` |
| "What's the portfolio mix today?" | `/` (pulse line + health distribution) |
| "What's on my plate?" | `/my/<username>` |
| "What's due this week?" | `/deadlines` |
| "How is the 'growth' cohort doing?" | `/cohorts` or `/cohort/growth` |
| "Who owns what?" | `/owners` or `/owner/<name>` |
| "What did we note about X?" | `/notes?q=X` |
| "Prepare LP update" | `/lp-update?days=30&download=1` |
| "Rerun simulation for ccf" | `/deal/ccf` → ▶ Rerun simulation button |
| "Who has admin rights?" | `/users` (admin-only) |
| "Audit trail of ack + ownership changes" | `/audit` (admin-only) |
| "Who acked what?" | `/api/audit/events?action=alert.ack` |

## HTML routes

**Portfolio-wide**
- `/` — dashboard (pulse line, health distribution, funnel, deal table)
- `/alerts` — evaluator-driven alerts with ack/snooze
- `/alerts?owner=AT` — scoped to one analyst's deals
- `/alerts?show=all` — include acked/snoozed
- `/escalations` — red alerts ≥30 days old (configurable)
- `/cohorts` — tag-grouped rollups with avg health
- `/cohort/<tag>` — deals in one cohort
- `/owners` — directory with per-analyst avg health
- `/owner/<name>` — deals owned by one analyst
- `/watchlist` — starred deals, per-row trend arrows
- `/deadlines` — inbox (overdue + upcoming, owner filter)
- `/variance` — portfolio-wide KPI variance drill-down
- `/notes` — full-text search + tag filter
- `/activity?owner=AT&kind=note` — timeline filterable by owner + event type
- `/lp-update?days=30` — partner-ready compile, `?download=1` for HTML file
- `/compare?deals=a,b,c` — side-by-side with EBITDA trajectory charts
- `/my/<owner>` — personalized pulse, health mix, alerts, deals, deadlines

**Deal-level**
- `/deal/<id>` — health score + trend + sparkline; alerts; tags; owner;
  deadlines; notes; rerun simulation; actuals entry; stage advance; ★ star
- `/deal/<id>?download=1` — printable HTML
- `/jobs` + `/jobs/<id>` — simulation queue + live status

**Admin**
- `/login`, `/logout`
- `/users` — create / rotate password / delete (admin-only)
- `/audit` — unified event log

## REST endpoints

**Authentication + identity**
- `POST /api/login` → sets `rcm_session` + `rcm_csrf` cookies
- `POST /api/logout`
- `GET /api/me` → `{username, display_name, role}` or `{}`
- `POST /api/users/{create,delete,password}` (admin-only, CSRF-gated)

**Alerts + acks + history**
- `GET /api/alerts/active` — non-acked
- `GET /api/alerts/all` — audit view including acked
- `GET /api/alerts/acks` — ack audit log
- `GET /api/alerts/history` — sighting log (first_seen / last_seen)
- `GET /api/alerts/days_red?min_days=30` — escalation query
- `POST /api/alerts/ack` — ack/snooze a specific alert instance

**Deals**
- `GET /api/deals` — latest-per-deal
- `GET /api/deals/<id>` — snapshot audit
- `GET /api/deals/<id>/health` — score + components + trend/delta
- `GET /api/deals/<id>/variance` — quarterly variance
- `GET /api/deals/<id>/initiatives` — initiative attribution
- `GET /api/deals/<id>/notes`, `/tags`, `/sim-inputs`, `/deadlines`
- `POST /api/deals/<id>/{actuals,snapshots,notes,remark,star,owner}`
- `POST /api/deals/<id>/{sim-inputs,rerun,deadlines,tags}`

**Portfolio rollups**
- `GET /api/rollup`
- `GET /api/cohorts`, `/api/cohort/<tag>`
- `GET /api/portfolio/variance?kpi=ebitda&quarter=2026Q1`
- `GET /api/owners`, `/api/owner/<name>`
- `GET /api/watchlist`
- `GET /api/my/<owner>` — one-call analyst bundle
- `GET /api/deadlines?days=14&owner=AT`

**Notes**
- `GET /api/notes/search?q=covenant&tags=board_meeting&limit=50&offset=0`
- `GET /api/notes/<id>/tags`
- `POST /api/notes/<id>/tags`, `POST /api/notes/<id>/tags/remove`
- `POST /api/upload-notes` — bulk CSV ingest

**Deadlines**
- `POST /api/deadlines/<id>/complete`
- `POST /api/deadlines/<id>/assign`

**Jobs (simulation queue)**
- `POST /api/jobs/run` — queue a new sim
- `GET /api/jobs`, `GET /api/jobs/<id>`

**Audit + observability**
- `GET /api/audit/events?actor=AT&action=alert.ack&limit=200&offset=0`
- `GET /health` — plain `ok`
- `GET /api/health` — includes `audit_failure_count` and `audit_last_failure`

**CSV export everywhere**
Add `?format=csv` to: `/variance`, `/escalations`, `/cohorts`, and
`/api/export` for the latest-per-deal view. All CSV cells starting
with `= + @ -` are prefixed with `'` to defang formula injection.

## CLI parity

Most common partner operations have CLI mirrors — script-friendly for
cron:

```bash
# Alerts
rcm-mc portfolio alerts active
rcm-mc portfolio alerts ack --kind covenant_tripped --deal-id ccf \
    --trigger-key "covenant_tripped|ccf|2026-04-15T10:00:00Z" --snooze-days 7

# Deadlines
rcm-mc portfolio deadlines upcoming --days 14 --owner AT
rcm-mc portfolio deadlines overdue --owner AT
rcm-mc portfolio deadlines add --deal-id ccf --label "covenant test" \
    --due-date 2026-05-31 --owner AT
rcm-mc portfolio deadlines complete --id 7

# Owners
rcm-mc portfolio owners list
rcm-mc portfolio owners deals --owner AT
rcm-mc portfolio owners assign --deal-id ccf --owner AT

# Users
rcm-mc portfolio users create --username AT --password "..." --role analyst
rcm-mc portfolio users list
rcm-mc portfolio users password --username AT --new-password "..."
rcm-mc portfolio users delete --username AT

# Simulation rerun
rcm-mc portfolio sim-inputs set --deal-id ccf \
    --actual /path/actual.yaml --benchmark /path/benchmark.yaml
rcm-mc portfolio rerun --deal-id ccf

# LP digest (cron-friendly)
rcm-mc portfolio lp-update --out /srv/out/lp_$(date +%Y%m%d).html --days 7
```

## Example cron

```cron
# Monday 6am: rerun the watchlist
0 6 * * 1 cd /srv/rcm && .venv/bin/python -m rcm_mc.portfolio_cmd \
    --db portfolio.db rerun --deal-id ccf >> logs/rerun.log 2>&1

# Daily 7am: regenerate LP update
0 7 * * * cd /srv/rcm && .venv/bin/python -m rcm_mc.portfolio_cmd \
    --db portfolio.db lp-update \
    --out /srv/rcm/out/lp_$(date +\%Y\%m\%d).html --days 7
```

## Security posture

- **Authn**: scrypt + per-user salt, 256-char password cap
- **Authz**: role-gated endpoints (admin vs analyst)
- **Sessions**: HttpOnly + SameSite=Lax cookies, 7-day TTL
- **CSRF**: HMAC double-submit cookie + `X-CSRF-Token` header; auto
  injected into forms via global JS
- **Rate limiting**: 5 failed logins per IP per 60s → 429
- **Audit**: unified event log; silent failures surfaced via
  `/api/health` + stderr
- **Inputs**: int bounds clamped, deal_id/note length capped, CSV
  encoding fallback (UTF-8 → latin-1), path traversal blocked in
  rerun outdir_base, CSV formula injection defanged on export
- **Concurrency**: SQLite `busy_timeout=5000`, `BEGIN IMMEDIATE` on
  multi-step writes (toggle_star, delete_user, add_deadline dedupe)

## Data model

14 tables, all `CREATE TABLE IF NOT EXISTS` with back-compat ALTER
migrations:

- `deals`, `runs`, `deal_snapshots` — core portfolio state
- `quarterly_actuals`, `initiative_actuals` — KPI tracking
- `deal_notes` (soft-delete) + `note_tags` — analyst context
- `deal_tags` — portfolio slicing
- `deal_stars` — watchlist
- `deal_owner_history` — ownership audit
- `deal_deadlines` (owner-aware) — task inbox
- `deal_sim_inputs` — stored rerun paths
- `alert_acks`, `alert_history`, `deal_health_history` — alerts lifecycle
- `users`, `sessions`, `audit_events` — access control

## Testing

```bash
.venv/bin/python -m pytest -q --ignore=tests/test_integration_e2e.py
# → 1421 passed
```

Test files for this session: `tests/test_*.py` covering B102–B160.
