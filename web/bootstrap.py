"""First-boot: schema migrations + admin user creation. Idempotent.

Env vars:
    ADMIN_USERNAME, ADMIN_PASSWORD — required
    RCM_MC_DB                      — optional, default /tmp/rcm_mc.db
"""
from __future__ import annotations

import os
import sys

from rcm_mc.auth.auth import create_user
from rcm_mc.infra import migrations
from rcm_mc.portfolio.store import PortfolioStore


DEFAULT_DB_PATH = "/tmp/rcm_mc.db"


def ensure_ready() -> str:
    """Run migrations + create admin user from env. Returns the db path used."""
    db_path = os.environ.get("RCM_MC_DB", DEFAULT_DB_PATH)
    store = PortfolioStore(db_path)
    migrations.run_pending(store)

    username = os.environ.get("ADMIN_USERNAME")
    password = os.environ.get("ADMIN_PASSWORD")
    if not (username and password):
        print("bootstrap: ADMIN_USERNAME + ADMIN_PASSWORD required",
              file=sys.stderr)
        sys.exit(1)

    try:
        create_user(store, username, password, role="admin")
        print(f"bootstrap: admin '{username}' created", file=sys.stderr)
    except ValueError as exc:
        # Idempotent skip when the user already exists — every Heroku
        # redeploy fires the release phase, so first-deploy creates +
        # subsequent-deploys must no-op. Other ValueErrors (bad
        # username, short password) are real config errors and propagate.
        msg = str(exc).lower()
        if "already exists" in msg or "clash" in msg:
            print(f"bootstrap: admin '{username}' already exists, skipping",
                  file=sys.stderr)
        else:
            raise
    return db_path


if __name__ == "__main__":
    ensure_ready()
