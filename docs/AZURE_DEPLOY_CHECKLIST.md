# Azure Deploy Checklist

Each row is a deploy-readiness criterion. Check off when the
codebase satisfies it. Failures get the smallest possible fix that
makes them pass — Azure-readiness work is forward-only on `design-v5`.

Initial audit: 2026-04-28 cycle 1 step 10. Subsequent rows checked
off with the iteration that closed them (e.g. `[x] (iter 27)`).

---

## ENVIRONMENT

- [x] `PORT` bound from environment variable, not hardcoded. (iter 20+34)
  - `demo.py` now reads `int(os.environ.get("PORT") or
    os.environ.get("WEBSITES_PORT") or 8765)`. Honours both Azure
    App Service env conventions (`PORT` and `WEBSITES_PORT`).
    Local dev still falls back to 8765.
- [ ] `CHARTIS_UI_V2=1` documented in deploy config.
  - Current: documented in `demo.py` docstring + CLAUDE.md.
  - Gap: needs to land in `deploy/` config (Bicep / app-service.json
    / equivalent) so Azure App Service Configuration sets it before
    the container starts.

## SECRETS

- [x] `secret_key` for session cookies sourced from env, never
      hardcoded. (iter cycle-11)
  - Two distinct secrets: (1) per-session token via
    `secrets.token_urlsafe(32)` stored in DB — no master key
    needed; (2) per-process CSRF HMAC secret. The CSRF secret
    now reads `RCM_MC_CSRF_SECRET` env (32+ chars required;
    shorter values trigger a stderr warning + ephemeral
    fallback). When env is set, partners stay logged in across
    container restarts. When unset, falls back to the
    documented Phase-3 ephemeral behavior. Pinned by 4 tests
    in `tests/test_azure_deploy_v2.py::CSRFSecretEnvTests`.
- [x] No DB credentials, API keys, or PII in repo or env defaults.
      (iter cycle-11)
  - Grep audit of `rcm_mc/` + `demo.py`: no hardcoded secrets.
    `demo.py` ships demo credentials (`DemoPass!1`,
    `ChartisDemo1`) intentionally — these are seeded admin
    accounts for the demo container, not production
    credentials. Production deploys should rotate them via
    `rcm-mc users password` after first boot. SMTP / external
    secrets read from env (`SMTP_PASS`, etc.). No PII in
    seed data — every name in the corpus is a public PE deal
    or sponsor.

## STATIC ASSETS

- [x] `chartis_tokens.css` served at `/static/chartis_tokens.css`.
  - Verified: `_CSS_LINK = '<link rel="stylesheet"
    href="/static/chartis_tokens.css">'` in `_chartis_kit.py`;
    server.py serves the static dir; smoke-tested via
    `test_alerts_page.py::test_alerts_renders_through_chartis_shell`
    which asserts the link is present in rendered HTML.
- [x] `/static/v3/chartis.css` served (marketing landing).
- [x] Static assets cached via `Cache-Control` headers (Azure CDN
      friendly). (iter cycle-10)
  - `_route_static` now sends
    `Cache-Control: public, max-age=3600` on every `/static/*`
    response. Pinned by
    `tests/test_azure_deploy_v2.py::StaticCacheControlTests::test_chartis_tokens_carries_cache_control`.
  - `_send_file` for partner-generated outputs in `outdir` still
    sends no caching directive (those change without a deploy).

## PORT BINDING

- [x] Bind to `0.0.0.0` not `127.0.0.1` so Azure can route traffic.
      (iter cycle-10)
  - `demo.py` now auto-detects the App Service environment via
    `WEBSITE_HOSTNAME` / `WEBSITES_PORT` (canonical Azure env
    vars) and defaults `HOST` to `0.0.0.0` in that case. Local
    runs (no Azure env) still bind `127.0.0.1`. `RCM_MC_HOST`
    explicit override wins over both. Pinned by 4 tests in
    `tests/test_azure_deploy_v2.py::AzureHostDetectionTests`.

## HEALTHCHECK

- [x] `/healthz` returns `200` with low duration.
  - Verified: `_HEALTH_PATHS = {"/health", "/healthz",
    "/api/health", "/api/health/deep"}` in
    `tools/v3_route_inventory.py`; the inventory classifier
    correctly excludes them from UI surface; `/healthz` is wired
    in server.py dispatcher.
- [ ] Confirmed end-to-end response time < 100ms on cold container.

## GUNICORN / HYPERCORN

- [ ] Production WSGI/ASGI server wired (not just `ThreadingHTTPServer`).
  - Current: `ThreadingHTTPServer` from `http.server` — fine for
    dev but not production. Azure expects gunicorn/hypercorn or
    Microsoft IIS / Kestrel.
  - Decision: defer until other rows are clean; the existing
    server is correct shape but not battle-tested under load.

## LOGGING

- [x] Structured JSON logs to stdout.
  - Verified: every server response logs a JSON line with `ts`,
    `request_id`, `method`, `path`, `status`, `duration_ms`,
    `user_id`, `client`. Captured during recent test runs.
- [x] Log level configurable via env (`LOG_LEVEL`). (iter cycle-10)
  - `rcm_mc/infra/logger.py` now resolves `LOG_LEVEL` from env,
    accepting both named levels (`DEBUG` / `INFO` / `WARNING` /
    `ERROR` / `CRITICAL`, case-insensitive) and numeric levels
    (`10` / `20` / `30`). Unknown values fall back to `INFO`
    rather than muting the logger or crashing boot. Pinned by 6
    tests in `tests/test_azure_deploy_v2.py::LogLevelEnvTests`.

## AUTH SESSION COOKIE

- [x] `SameSite=Lax` (or `Strict`) set on session cookie.
      (verified cycle-10)
- [x] `Secure` flag set when serving over HTTPS.
      (verified cycle-10)
- [x] `HttpOnly` set so JS can't read it.
      (verified cycle-10)
  - The `/api/login` and `/api/logout` paths in `server.py` set
    `rcm_session` with `HttpOnly; SameSite=Lax` and append
    `; Secure` via `_cookie_flags()` whenever `_is_https()`
    returns true (driven by `X-Forwarded-Proto: https` from
    Azure's reverse proxy). The `rcm_csrf` cookie is
    intentionally non-HttpOnly (the CSRF-patching JS reads it)
    but still carries `SameSite=Lax`. Pinned by 3 tests in
    `tests/test_azure_deploy_v2.py::SessionCookieFlagsTests`.

## CHARTIS_UI_V2 LOCK

- [x] CHARTIS_UI_V2=1 is documented as required at every entry
      point: `demo.py` startup banner, `CLAUDE.md`,
      `EDITORIAL_POLISH_LOG.md`. Without it the app falls back to
      the legacy dark Bloomberg shell — DO NOT ship like that.
- [x] Azure App Service Configuration JSON includes the
      `CHARTIS_UI_V2=1` setting (deploy manifest).
      (iter cycle-11)
  - `deploy/azure-app-service.json` ships with
    `CHARTIS_UI_V2=1` plus six other operational env vars
    (`RCM_MC_HOST`, `LOG_LEVEL`, `RCM_MC_CSRF_SECRET`,
    `RCM_MC_DB_PATH`, `WEBSITES_PORT`,
    `WEBSITES_ENABLE_APP_SERVICE_STORAGE`). Apply via
    `az webapp config appsettings set --resource-group <rg> \
    --name <app> --settings @deploy/azure-app-service.json`.
    Pinned by 5 tests in
    `tests/test_azure_deploy_v2.py::AzureManifestTests`.

## DATABASE PERSISTENCE

- [x] `portfolio.db` written to a path that survives container
      restarts on Azure. (iter cycle-11)
  - `demo.py` now reads `RCM_MC_DB_PATH` env when set and uses
    that path for the SQLite file (creating its parent dir if
    needed). Local dev (env unset) keeps the
    `tempfile.mkdtemp` fallback so `python demo.py` still gets
    a fresh DB. The deploy manifest sets
    `RCM_MC_DB_PATH=/home/data/portfolio.db` and
    `WEBSITES_ENABLE_APP_SERVICE_STORAGE=true` — `/home` is
    Azure App Service's persistent mount. `create_user` calls
    are now idempotent (catch ValueError on duplicate users)
    so a persistent DB across restarts doesn't crash boot.
- [ ] DB schema migrations idempotent on cold start.
  - `infra/migrations.run_pending()` is called by
    `build_server`; needs verification that all 89-table
    `CREATE TABLE IF NOT EXISTS` migrations are no-op when
    the table exists with the expected schema. Cycle 12
    target.

## SMOKE TEST (post-deploy)

- [x] `/login` → `/api/login` → `/app` round-trip succeeds with
      seeded credentials.
  - Verified locally during this session via curl + the server's
    own request log: GET `/login` 200 → POST `/api/login` 303 →
    GET `/` 303 → GET `/app` 200. End-to-end auth works.
- [ ] Same round-trip exercised post-Azure-deploy as a smoke gate.
- [ ] Editorial chrome present on `/app` (navy topbar + italic
      `Chartis` wordmark + teal accent rule visible in HTML).

---

## Audit summary

**Cycle 1 baseline (2026-04-28):** 6 of 22 passing.
**Cycle 4-5 update:** 7 of 22 passing (PORT-from-env shipped).
**Cycle 10 update (2026-04-28):** **13 of 22 passing.**
**Cycle 11 update (2026-04-28):** **18 of 22 passing.**

Cycle 11 closed 5 more rows in one batch:
1. SECRETS — `secret_key` from env via
   `RCM_MC_CSRF_SECRET`. Persists across container restarts
   so partners stay logged in across deploys.
2. SECRETS — no DB credentials / API keys / PII in repo
   audit.
3. CHARTIS_UI_V2 LOCK — `deploy/azure-app-service.json`
   manifest with `CHARTIS_UI_V2=1` + 6 other operational
   env vars.
4. DATABASE PERSISTENCE — `RCM_MC_DB_PATH` env points DB at
   Azure persistent `/home/data/` volume.
5. (`WEBSITES_ENABLE_APP_SERVICE_STORAGE=true` in manifest
   to mount `/home` — same row, different tooling.)

10 new tests in `tests/test_azure_deploy_v2.py` covering
CSRF-secret env semantics + manifest contents + DB-path env
clean import.

**Still pending (4 of 22):**
- DB schema migrations idempotent on cold start (cycle 12)
- `/healthz` cold-container response time <100ms confirmation
  (needs a real Azure ship)
- Production WSGI/ASGI server (gunicorn/hypercorn) — deferred
  by design until post-MVP load testing
- Same /login round-trip exercised post-Azure-deploy + chrome
  verification on `/app` post-deploy (needs a real Azure ship)

**Next-up rows for cycle 2 step 10:**
1. PORT from env (5-line change to the production entry point).
2. Bind 0.0.0.0 (one-line config).
3. Audit auth session cookie flags (likely already correct;
   verify and check off).
4. Add deploy/azure manifest under `deploy/` snapshotting the
   `CHARTIS_UI_V2=1` + `PORT` env.
