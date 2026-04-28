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

- [ ] `secret_key` for session cookies sourced from env, never
      hardcoded.
  - Current: `rcm_mc/auth/session.py` (or equivalent) — needs
    audit.
- [ ] No DB credentials, API keys, or PII in repo or env defaults.

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
- [ ] Azure App Service Configuration JSON includes the
      `CHARTIS_UI_V2=1` setting (deploy manifest).

## DATABASE PERSISTENCE

- [ ] `portfolio.db` written to a path that survives container
      restarts on Azure.
  - Current: `demo.py` uses `tempfile.mkdtemp(prefix="rcm_demo_")`
    — wiped on restart. Production needs a mounted volume
    (Azure Files share / managed disk) at e.g. `/data`.
- [ ] DB schema migrations idempotent on cold start.

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

Cycle 10 closed 6 rows in one batch:
1. PORT BINDING — auto-bind `0.0.0.0` on Azure (env-detected).
2. STATIC ASSETS — `Cache-Control: public, max-age=3600` on
   `/static/*`.
3. LOGGING — `LOG_LEVEL` env configurable (named or numeric).
4. AUTH SESSION COOKIE — `HttpOnly` + `SameSite=Lax` verified.
5. AUTH SESSION COOKIE — `Secure` on HTTPS verified
   (`X-Forwarded-Proto: https` driven).
6. AUTH SESSION COOKIE — `HttpOnly` regression-pinned.

All six are pinned by 14 new tests in
`tests/test_azure_deploy_v2.py`.

**Still pending (9 of 22):**
- CHARTIS_UI_V2=1 in deploy/ manifest
- `secret_key` for sessions sourced from env (audit)
- No DB credentials / API keys / PII in repo or env defaults
- `/healthz` cold-container response time <100ms confirmation
- Production WSGI/ASGI server (gunicorn/hypercorn) — deferred
- Azure App Service Configuration JSON snapshot
- `portfolio.db` on a mounted volume that survives restarts
- DB schema migrations idempotent on cold start
- Same /login round-trip exercised post-Azure-deploy
- Editorial chrome verification on `/app` post-deploy

**Next-up rows for cycle 2 step 10:**
1. PORT from env (5-line change to the production entry point).
2. Bind 0.0.0.0 (one-line config).
3. Audit auth session cookie flags (likely already correct;
   verify and check off).
4. Add deploy/azure manifest under `deploy/` snapshotting the
   `CHARTIS_UI_V2=1` + `PORT` env.
