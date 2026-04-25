# legacy/heroku/

**Status: archived. Not the current deploy path.**

These files supported a Heroku deploy that was abandoned in favor of Azure VM. See [`/DEPLOYMENT_PLAN.md`](../../DEPLOYMENT_PLAN.md) and [`/AZURE_DEPLOY.md`](../../AZURE_DEPLOY.md) for the active deployment.

Heroku was abandoned because:
- Ephemeral filesystem (SQLite would be wiped on every restart)
- 30-second request timeout (Deal MC at 3,000 trials needs longer)
- No BAA available on standard Heroku plans (PHI handling would require Heroku Shield)

The Azure VM path solves all three: persistent volume mount for SQLite, no per-request timeout, and Azure offers a BAA on standard VMs.

## What's here

| File | Purpose under Heroku |
|------|----------------------|
| `Procfile` | Dyno entry — `web: python -m web.heroku_adapter`, `release: python -m web.bootstrap` |
| `app.json` | Heroku app manifest with env-var schema for `ADMIN_USERNAME` / `ADMIN_PASSWORD` etc. |
| `runtime.txt` | Pinned `python-3.14` for the Heroku buildpack |
| `requirements.txt` | Pip deps mirror of `RCM_MC/pyproject.toml` for Heroku's pip-based install |
| `run_local.sh` | Local-dev launcher that mimicked `heroku local` (Heroku-parity env vars + bootstrap) |
| `web/` | Heroku adapter directory: `heroku_adapter.py`, `bootstrap.py`, `smoke_test.py`, `test_shim.py` |

## Why kept, not deleted

If a future migration to a managed-Python platform happens (Render, Fly, Railway, etc.) most of the same patterns apply with minor edits. The Heroku adapter shape — release-phase migration + admin-user bootstrap + adapter that wraps stdlib `ThreadingHTTPServer` — is reusable.

For local dev today: use `python demo.py` from `RCM_MC/` (documented in [`RCM_MC/README.md`](../../RCM_MC/README.md)). For production deploy: see [`AZURE_DEPLOY.md`](../../AZURE_DEPLOY.md).
