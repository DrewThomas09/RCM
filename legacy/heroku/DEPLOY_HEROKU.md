# DEPLOY.md — Heroku-style web deployment

Operational guide for the private, password-gated web deployment of
RCM-MC / SeekingChartis. The same pattern works on any platform that:

- Runs a single dyno/container with `$PORT` injected into the env
- Terminates TLS at an edge router and forwards `X-Forwarded-Proto`
- Provides ephemeral filesystem (writes go to `/tmp`)
- Sends `SIGTERM` on graceful shutdown
- Hits a configurable healthcheck URL on each dyno boot

Heroku is the canonical PaaS target; the same files (`Procfile`,
`runtime.txt`, `app.json`) ship on Render, Fly, Railway, and most
PaaS providers with no changes. For durability (SQLite on volume-
mounted disk instead of ephemeral `/tmp`), long-running compute
(>30 s), or a partner demo that survives a restart, use the **Azure
VM** path documented in §8. The Azure path also provides HTTPS via
a Caddy sidecar with automatic Let's Encrypt cert management.

---

## 1 — One-time setup

### Required Heroku config vars

Set with `heroku config:set KEY=value -a <app>` or via the dashboard.

| Var                       | Required | Default     | Notes |
|---------------------------|----------|-------------|-------|
| `ADMIN_USERNAME`          | yes      | —           | Created by release-phase if no users exist |
| `ADMIN_PASSWORD`          | yes      | —           | ≥ 8 chars, ≤ 256 chars (scrypt cost capped) |
| `RCM_MC_DB`               | no       | `/tmp/rcm_mc.db` | Ephemeral on Heroku — see §5 for durability |
| `RCM_MC_PHI_MODE`         | recommended | unset    | `disallowed` (public-data banner) or `restricted` (BAA-eligible banner) |
| `RCM_MC_SESSION_IDLE_MINUTES` | no   | `30`        | Inactive sessions auto-expire after N minutes |
| `RCM_MC_HOMEPAGE`         | recommended for web deploys | unset | Set to `dashboard` to make `/` 303-redirect to `/dashboard`. Without it, `/` serves the legacy portfolio dashboard, which works but isn't the experience built for web deployments. |
| `CHARTIS_UI_V2`           | no       | unset       | Reserved — opts into the editorial reskin shell once it's restored. Default keeps the legacy dark terminal shell currently shipping. |
| `ANTHROPIC_API_KEY`       | optional | —           | Enables AI-assist features in /settings/ai |
| `PYTHONUNBUFFERED`        | always   | `1`         | Sent automatically via app.json — do not unset |

### One-command deploy

```bash
heroku create <app-name> --buildpack heroku/python
heroku config:set ADMIN_USERNAME=admin ADMIN_PASSWORD='Strong#Pass1' \
                  RCM_MC_PHI_MODE=disallowed \
                  RCM_MC_HOMEPAGE=dashboard \
                  -a <app-name>
git push heroku main
heroku open -a <app-name>      # /login → enter creds → lands on /dashboard
```

`RCM_MC_HOMEPAGE=dashboard` is what makes a fresh login land on the
new web-deployment dashboard (curated analyses, daily-workflow badges,
system status, data freshness). Without it, `/` serves the legacy
portfolio view — fine, just not the morning-view we built for partners.

### First boot — what happens

1. **Build phase**: pip installs `requirements.txt` + the editable
   package from `./RCM_MC` (this repo's root).
2. **Release phase**: `python -m web.bootstrap` runs idempotent migrations
   and creates the admin user from `ADMIN_USERNAME` / `ADMIN_PASSWORD`.
3. **Web dyno boot**: `python -m web.heroku_adapter` binds the stdlib
   ThreadingHTTPServer to `$PORT`, registers a `SIGTERM` handler, and
   starts serving.
4. **Heroku healthcheck**: hits `/healthz` (auth-bypassed) and routes
   live traffic once it returns 200.

If `ADMIN_PASSWORD` is unset on first boot, the release phase logs
a warning and skips user creation; the app starts in single-user mode
(everything reachable without creds — DO NOT do this on a public URL).

---

## 2 — Verify the deploy

The smoke test in `web/smoke_test.py` is what you should run after
every deploy. It hits `/healthz`, logs in with creds you supply,
triggers a fast analysis, polls the job queue until it completes,
and exits 0 on success.

```bash
heroku run --app <app-name> -- python -m web.smoke_test \
    --base-url https://<app>.herokuapp.com \
    --username "$ADMIN_USERNAME" \
    --password "$ADMIN_PASSWORD"
```

Exit codes: 0 = green, 1 = healthcheck/login failure, 2 = analysis
failure (server up, app broken).

---

## 3 — Daily operations

### Tail logs
```bash
heroku logs --tail -a <app>
```
All logs go to stdout; structured JSON is not used (yet) so grep is
your friend. Look for `[rcm-mc audit] FAILED` for audit-write
breakages, and HTTP 5xx counts for handler regressions.

### Open a one-off shell
```bash
heroku run --app <app> bash
```
Useful for `python -m rcm_mc.portfolio_cmd users list`,
`python -m rcm_mc data status`, or ad-hoc DB inspection.

### Trigger a data refresh
- UI: open `/data/refresh`, click Refresh on a source.
- CLI inside one-off shell:
  `python -m rcm_mc data refresh --source hcris`
- API:
  `curl -X POST -b "rcm_session=$TOKEN" \
        https://<app>/api/data/refresh/hcris/async`

### Force a restart (drains in-flight jobs)
```bash
heroku ps:restart -a <app>
```
The SIGTERM handler has 10 s to flush the request log + finish the
current request; jobs in-flight on the in-process worker die. See §5
for what survives.

---

## 4 — Monitoring

### What to watch

| Signal | Where | Action |
|--------|-------|--------|
| Healthcheck failures | Heroku metrics → Throughput → 503s | Restart, then check logs for the cause |
| 500 spike | `heroku logs --tail \| grep " 500 "` | Page just regressed; the `request_id` header in the response correlates to the log line |
| Audit write failures | `heroku logs \| grep '\[rcm-mc audit\]'` | Indicates DB lock contention or schema corruption — investigate immediately |
| Memory hits cap | `heroku logs \| grep R14` | The pandas dataframe in some endpoint is too big; cap it via `?limit=` |
| Long jobs | `/dashboard` → Recent runs | Anything stuck in `running` for > 10 min has hung |

### Dashboards (built into the app)

- `/healthz` — JSON health summary, public (no auth)
- `/api/system/info` — version, request count, DB size, started_at
- `/dashboard` — system status cards (DB reachable, migrations applied,
  job worker running, PHI mode, uptime)
- `/data/refresh` — per-source freshness chips, last-refreshed timestamps
- `/api/openapi.json` — every route + method

---

## 5 — Resilience: what happens when things break

The app is designed to fail forward. This section documents the
recovery posture for each common failure mode — useful for both
debugging and confidence during stakeholder demos.

### Dyno restart mid-analysis

**What dies**: the in-process worker thread and any analysis it was
running. The SIGTERM handler does NOT wait for the worker to finish;
that would block restarts longer than Heroku's 30-s grace.

**What survives**: the request log, the audit table, all completed
analyses (every packet is checkpointed to the `analysis_runs` table
on completion, never just held in memory).

**Recovery**: jobs in `queued` or `running` status are picked up by
**no one** on the next boot — Heroku is single-dyno; there is no
redundancy. Operators see the stuck row in `/dashboard → Recent runs`
and either:

  1. Click rerun on the source feature page (idempotent — same params
     produce the same packet), OR
  2. Manually mark the row failed via
     `python -m rcm_mc job-queue mark-stale --max-age 1h`

The smoke test re-establishes a known-good baseline on every deploy.

### Data refresh fails halfway

**What's at risk**: `data_source_status` row left in `running` status,
partial rows in the source table.

**What protects you**:

  1. The refresher uses `INSERT OR REPLACE` so a re-run cleanly
     overwrites half-written rows.
  2. `data_source_status.status = 'running'` is the lock — concurrent
     refreshes coalesce via the rate limiter (1 / source / hour).
  3. The job-queue runner wraps the refresh in a try/except that always
     transitions the job to `failed` with the exception text in
     `error`, never leaves it stuck in `running`.

**Recovery**: from `/data/refresh`, click Refresh on the offending
source again. The next attempt rebuilds from scratch. If the source's
data file has a real schema problem, the failure surfaces in the
status chip with the exception type — not a stack trace dump.

### Database corruption / disk full

**What protects you**:

  - SQLite WAL mode + `PRAGMA busy_timeout = 5000ms` rules out the
    common "database is locked" race.
  - Every CREATE TABLE is `IF NOT EXISTS` — restart-safe.
  - Migrations are idempotent and content-keyed, not numeric — running
    the same migration twice is a no-op.

**What goes wrong on Heroku**: `/tmp` fills up if you cache analyses
without bound. The `/api/system/info` endpoint reports `db_size_mb`;
if it crosses ~400 MB, restart the dyno (which wipes `/tmp`) and
re-run any IC packets you still need.

**Recovery from corruption**:

  1. `heroku run python -m rcm_mc portfolio backup --output /tmp/backup.db`
     copies the SQLite file out so you can inspect locally.
  2. `heroku ps:restart` — `/tmp` resets to empty; the release-phase
     migrations recreate every schema; the admin user is recreated
     from `ADMIN_USERNAME` / `ADMIN_PASSWORD`.
  3. Any deal data not exported is lost. **Never run prod off Heroku
     ephemeral DB if you care about long-term durability.** Use the
     Azure VM path with a persistent disk volume for production.

### Heroku 30-s request timeout

**What hits the limit**: 500-path covenant Monte Carlo, payer-stress
500 paths, full IC packet build with all 12 modules.

**What protects you**: every long-running endpoint has an `/async`
sibling that enqueues the work onto the in-process job queue, returns
202 + `job_id`, and lets the UI poll `/api/jobs/<id>`. The pattern
is wired for `/api/data/refresh/*/async`,
`/api/analysis/<deal>/build-async`, and the IC packet route.

**What does NOT hit the limit**: the synchronous variants of the
above only block for ≤ a few seconds; their 95th percentile is well
under the 30-s cap. If you see Heroku H12s in logs, the route is
mis-categorized — open an issue.

### Audit table write failure

**What you see**: `[rcm-mc audit] FAILED to log event ...` on stderr
plus `_audit_failure_count` increments on the handler class.

**What protects you**: the failure is non-fatal — the user's request
still completes. `_audit_last_failure` ISO timestamp is stashed on the
class so `/api/system/info` (or a future Prometheus exporter) can
surface "audit gap detected at <ts>".

**Recovery**: usually a DB lock. If it persists, the audit_events
table itself may be corrupted — restart, and the table recreates on
first write.

### Session DB / migration drift

**What protects you**: `auth/auth.py::_ensure_tables()` is invoked
on every login attempt and on every `user_for_session` call. Missing
columns are added idempotently via `PRAGMA table_info` + `ALTER TABLE
ADD COLUMN`. Older deployments upgrading to the idle-timeout feature
get the new `last_seen_at` column on first login attempt — no
manual migration step.

---

## 6 — Troubleshooting

### "Login redirects to /login forever"

Most common cause: the `Secure` cookie flag is being set, but the
edge router isn't forwarding `X-Forwarded-Proto: https`. Verify with:

```bash
heroku run -- python -c "import os; \
  print(os.environ.get('FORWARDED', 'not-set'))"
```

If the cookie is rejected by the browser, no session can be
established. Heroku always sends `X-Forwarded-Proto`; if you're
behind an extra proxy, make sure it preserves the header.

### "Healthcheck timeout / boot loops"

The first boot runs migrations + admin-user creation + table
ensures. If it OOMs (rare, but the python-3.14 + pandas image is
~250 MB resident at boot), the dyno is killed and Heroku marks the
release failed. Confirm with `heroku releases:info <release>`.

Fix: `heroku ps:scale web=1:standard-1x` (512 MB → 1 GB) for the
release phase only, or trim `requirements.txt`.

### "I see a Python traceback in my browser"

You shouldn't — every handler has a global error boundary that
sends `{"error": "internal server error", "request_id": "..."}` and
logs the traceback to stdout (Heroku captures it in `heroku logs`).
If a traceback escapes to the user, file a bug with the URL + the
`X-Request-Id` header from the response — the test
`tests/test_web_e2e_audit.py` is supposed to catch this exact
regression.

### "Deal export downloads HTML when I asked for PDF"

PDF is rendered as HTML + auto-print JS — open in browser, hit
Cmd-P / Ctrl-P, save as PDF. Avoiding a native PDF engine kept us
off the 250-MB-larger Heroku slug. If you really want server-side
PDF, see the comment in `rcm_mc/exports/packet_renderer.py` for the
WeasyPrint path.

### "Async job stuck in 'running' forever on the dashboard"

The in-process job queue lost its worker thread (most often a dyno
restart mid-job). The on-disk `data_source_status` row is unaffected
— it only ever holds terminal states (OK / STALE / ERROR). The
"running" you see is purely an in-memory artifact.

Reset:

```bash
heroku run -- python -c "
from rcm_mc.infra.job_queue import get_default_registry
stale = get_default_registry().mark_stale(max_age_seconds=600)
print(f'marked {len(stale)} stale: {stale}')
"
```

Then click Refresh again from `/data/refresh` — the new attempt
takes a fresh job_id. The rate limiter is per-source and DB-backed,
so a previously stale job does not block subsequent attempts.

---

## 7 — Production readiness checklist

Before pointing real users at the deployment:

- [ ] `ADMIN_USERNAME` + `ADMIN_PASSWORD` set, password ≥ 12 chars
- [ ] `RCM_MC_PHI_MODE` set explicitly (`disallowed` for public-data
      deployments, `restricted` for BAA-eligible)
- [ ] HTTPS enforced — visit the URL over `http://` and confirm a
      302 redirect to HTTPS (Heroku does this automatically once you
      attach an SSL cert; verify the redirect chain)
- [ ] `/healthz` returns 200 from outside the dyno
- [ ] Smoke test green:
      `python -m web.smoke_test --base-url https://<app>`
- [ ] Logs show no `[rcm-mc audit] FAILED` lines in last hour
- [ ] You can log in, navigate to /dashboard, run a thesis pipeline,
      and see the result
- [ ] You know how to roll back: `heroku rollback <release>`

---

## 8 — Azure VM path (the durable one)

Heroku is fine for a sales POC but the ephemeral filesystem is a
real problem: a dyno cycle wipes every packet built since last
boot. For a partner demo or production use, deploy to an Azure VM
with a volume-mounted SQLite + a Caddy TLS sidecar.

### What ships in `RCM_MC/deploy/`

| File               | Purpose |
|--------------------|---------|
| `Dockerfile`       | Python 3.14-slim + the package. **CMD binds `--host 0.0.0.0`** — required for the sidecar to reach the origin |
| `docker-compose.yml` | Origin service + optional Caddy sidecar behind the `tls` profile |
| `Caddyfile`        | Reverse-proxy config; automatic Let's Encrypt; sets `X-Forwarded-Proto: https` so the origin emits HSTS + Secure cookies |
| `rcm-mc.service`   | systemd unit that starts the compose stack on boot + restarts on failure |
| `vm_setup.sh`      | One-command bootstrap: installs Docker, clones the repo, starts the stack, creates the admin user, prints the public URL |

### One-command deploy (domain + HTTPS)

```bash
# On a fresh Azure Ubuntu 22.04 VM:
sudo bash vm_setup.sh admin 'StrongPass!12' diligence.example.com
```

The domain must have an A record pointing at the VM's public IP
BEFORE you run this. Caddy's ACME challenge fails otherwise (it
retries in the background; check `docker compose logs caddy`).

### Without HTTPS (VM-internal test)

```bash
sudo bash vm_setup.sh admin 'StrongPass!12'
# Live at http://<vm-public-ip>:8080/
```

This brings up only the origin on port 8080. Useful for smoke
testing the stack without touching DNS or Let's Encrypt.

### What survives a restart on Azure (vs Heroku)

| Failure | Heroku | Azure VM |
|---------|--------|----------|
| Container/dyno restart | DB wiped (ephemeral `/tmp`) | DB persists (volume mount `/data/rcm`) |
| In-flight job at SIGTERM | lost | lost (same in-memory registry) |
| Let's Encrypt cert | N/A (platform handles) | persists (caddy_data volume) |
| Analysis packets | lost on restart | persist in SQLite |
| Audit log | lost on restart | persists in SQLite |
| Session tokens | lost on restart | persist; `last_seen_at` idle timeout enforced |

### Switching HTTPS on/off

- Bring HTTPS up: `DOMAIN=your.domain.com docker compose --profile tls up -d`
- Take HTTPS down (keep origin): `docker compose stop caddy`

The origin keeps running on port 8080 either way. Caddy is a
strictly optional ingress — the whole stack is designed so that
losing the TLS terminator doesn't lose the app.

### Why not Heroku + managed Postgres?

Both paths make data durable. Heroku + Postgres requires a
`PortfolioStore` adapter that chooses between SQLite and Postgres
based on `DATABASE_URL` — about two weeks of work because every
table definition is SQLite-dialect and the `_ensure_table()` path
assumes WAL + `busy_timeout`. The Azure VM path reuses the
existing SQLite design; the only add is the Caddyfile. See
`NEXT_CYCLE.md` Track A for the full comparison.
