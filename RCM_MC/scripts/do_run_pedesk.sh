#!/usr/bin/env bash
# do_run_pedesk.sh — run PEdesk on the Droplet, reading .pedesk_prod.env.
#
# Binds to 127.0.0.1:8080 by default (behind Caddy, which terminates HTTPS
# for pedesk.app). Set PEDESK_BIND_HOST=0.0.0.0 only if you are intentionally
# serving without Caddy. Reads the env file but prints NO secrets.
#
#   bash scripts/do_run_pedesk.sh                 # 127.0.0.1:8080 (behind Caddy)
#   PEDESK_BIND_HOST=0.0.0.0 bash scripts/do_run_pedesk.sh   # direct (needs auth!)
#
# Ollama stays on the Mac and is reached privately over Tailscale; this
# process never exposes 11434.
set -euo pipefail

ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$ROOT"
ENV_FILE="${PEDESK_PROD_ENV:-.pedesk_prod.env}"

if [ ! -f "$ENV_FILE" ]; then
  echo "[run] $ENV_FILE not found — create it first (see docs/DIGITALOCEAN_DEPLOYMENT.md)." >&2
  exit 1
fi

# Activate venv if present (created during setup).
if [ -z "${VIRTUAL_ENV:-}" ] && [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# Load env WITHOUT echoing it (contains RCM_MC_AUTH).
set -a; . "./$ENV_FILE"; set +a

BIND_HOST="${PEDESK_BIND_HOST:-127.0.0.1}"
BIND_PORT="${PEDESK_BIND_PORT:-8080}"

echo "[run] PEdesk · bind ${BIND_HOST}:${BIND_PORT} · Ollama=${PEDESK_GUIDE_OLLAMA_MODEL:-gemma4:e4b} (private via Tailscale)"
if [ "$BIND_HOST" = "0.0.0.0" ] && [ -z "${RCM_MC_AUTH:-}" ]; then
  echo "[run] REFUSING to bind 0.0.0.0 with no RCM_MC_AUTH — set Basic Auth or run behind Caddy on 127.0.0.1." >&2
  exit 1
fi

exec rcm-mc serve --host "$BIND_HOST" --port "$BIND_PORT"
