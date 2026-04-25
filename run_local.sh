#!/usr/bin/env bash
# run_local.sh — one-command local dev launcher.
#
# Sets up a venv (if missing), installs deps, exports Heroku-parity env
# vars, runs the release-phase bootstrap, then starts the web adapter.
# Equivalent to `heroku local` but without the Heroku toolbelt dependency.
#
# Usage:
#     ./run_local.sh              # start server on localhost:8080
#     ./run_local.sh smoke         # start server in background, run smoke tests, stop
#     ./run_local.sh clean        # blow away venv + db for a fresh start
#
# Env overrides (any can be pre-set in shell):
#     PORT, ADMIN_USERNAME, ADMIN_PASSWORD, RCM_MC_DB, RCM_MC_PHI_MODE
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

VENV="${ROOT}/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

# ── Defaults (Heroku-parity) ───────────────────────────────────────
export PORT="${PORT:-8080}"
export ADMIN_USERNAME="${ADMIN_USERNAME:-demo}"
export ADMIN_PASSWORD="${ADMIN_PASSWORD:-DemoPass!12}"
export RCM_MC_DB="${RCM_MC_DB:-/tmp/rcm_mc_local.db}"
export RCM_MC_PHI_MODE="${RCM_MC_PHI_MODE:-disallowed}"
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Make `rcm_mc` and `web` importable directly from source. This sidesteps
# Python 3.14's "hidden .pth file" rule which silently skips the dunder-
# named .pth that setuptools writes for editable installs (the `pip
# install -e ./RCM_MC` path produces __editable__.seekingchartis-*.pth,
# which 3.14's site.py treats as hidden). Putting the source dirs on
# PYTHONPATH gets us the same source-edits-take-effect behavior without
# relying on pip's editable mechanism.
export PYTHONPATH="${ROOT}/RCM_MC:${ROOT}:${PYTHONPATH:-}"

# ── Subcommands ────────────────────────────────────────────────────

cmd_clean() {
    echo "==> Cleaning venv + local DB"
    rm -rf "${VENV}"
    rm -f "${RCM_MC_DB}"
    echo "    done"
}

ensure_venv() {
    if [ ! -d "${VENV}" ]; then
        echo "==> Creating venv at ${VENV}"
        "${PYTHON_BIN}" -m venv "${VENV}"
    fi
    # shellcheck disable=SC1091
    source "${VENV}/bin/activate"

    if [ ! -f "${VENV}/.deps-installed" ]; then
        echo "==> Installing dependencies (pip install -r requirements.txt)"
        pip install --quiet --upgrade pip
        # Install all third-party deps from requirements.txt EXCEPT the
        # local ./RCM_MC path. The local package is on PYTHONPATH (set
        # at the top of this script) so source edits take effect with
        # zero reinstall. Avoids Python 3.14's silent skipping of
        # dunder-named .pth files written by setuptools' editable mode.
        grep -vE "^\./RCM_MC$|^\s*#|^\s*$" requirements.txt \
            | pip install --quiet -r /dev/stdin
        touch "${VENV}/.deps-installed"
    fi
}

run_bootstrap() {
    echo "==> Running bootstrap (migrations + admin user)"
    "${VENV}/bin/python" -m web.bootstrap
}

run_server() {
    echo ""
    echo "==> Starting server"
    echo "    URL:   http://localhost:${PORT}"
    echo "    Login: ${ADMIN_USERNAME} / ${ADMIN_PASSWORD}"
    echo "    DB:    ${RCM_MC_DB}"
    echo "    PHI:   ${RCM_MC_PHI_MODE}"
    echo "    (Ctrl-C to stop)"
    echo ""
    exec "${VENV}/bin/python" -m web.heroku_adapter
}

cmd_smoke() {
    ensure_venv
    run_bootstrap
    echo "==> Starting server in background"
    "${VENV}/bin/python" -m web.heroku_adapter >"${ROOT}/.server.log" 2>&1 &
    SERVER_PID=$!
    # Ensure we kill the server on exit regardless of smoke-test result
    trap "kill ${SERVER_PID} 2>/dev/null || true; rm -f ${ROOT}/.server.log" EXIT

    # Wait for /healthz to start responding (bounded 15s)
    echo "==> Waiting for server to accept connections"
    for i in $(seq 1 30); do
        if curl -sf "http://localhost:${PORT}/healthz" >/dev/null 2>&1; then
            echo "    ready after ${i} polls"
            break
        fi
        sleep 0.5
        if [ "$i" = "30" ]; then
            echo "    FAILED — server did not respond within 15s"
            tail -40 "${ROOT}/.server.log" || true
            exit 1
        fi
    done

    echo "==> Running smoke test"
    "${VENV}/bin/python" -m web.smoke_test "http://localhost:${PORT}"
    RC=$?

    echo "==> Stopping server"
    kill "${SERVER_PID}" 2>/dev/null || true
    wait "${SERVER_PID}" 2>/dev/null || true

    exit "${RC}"
}

# ── Dispatch ───────────────────────────────────────────────────────
case "${1:-run}" in
    clean)
        cmd_clean
        ;;
    smoke)
        cmd_smoke
        ;;
    run|"")
        ensure_venv
        run_bootstrap
        run_server
        ;;
    *)
        echo "usage: $0 [run|smoke|clean]" >&2
        echo "" >&2
        echo "  run   — (default) start the server on localhost:\$PORT" >&2
        echo "  smoke — start server, run smoke test, stop (CI-friendly)" >&2
        echo "  clean — remove venv + local DB" >&2
        exit 2
        ;;
esac
