#!/usr/bin/env bash
# do_bootstrap_server.sh — one-time DigitalOcean Droplet bootstrap for PEdesk.
#
# Installs OS basics + Tailscale (+ optional Caddy). Idempotent: safe to
# re-run. Touches NO secrets and prints none. Run as root on the Droplet:
#
#   bash scripts/do_bootstrap_server.sh               # basics + Tailscale
#   bash scripts/do_bootstrap_server.sh --with-caddy  # also install Caddy
#
# After this: `tailscale up`, create .pedesk_prod.env, then do_preflight.sh.
# This script does NOT expose Ollama and does NOT open port 11434.
set -euo pipefail

WITH_CADDY=0
[ "${1:-}" = "--with-caddy" ] && WITH_CADDY=1

if [ "$(id -u)" -ne 0 ]; then
  echo "[bootstrap] please run as root (sudo)." >&2
  exit 1
fi

echo "[bootstrap] apt update + upgrade…"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y

echo "[bootstrap] installing basics (git python3 venv pip curl ufw)…"
apt-get install -y git python3 python3-venv python3-pip curl ufw ca-certificates

# Tailscale — private path from the Droplet to the home Mac running Ollama.
if command -v tailscale >/dev/null 2>&1; then
  echo "[bootstrap] Tailscale already installed."
else
  echo "[bootstrap] installing Tailscale…"
  curl -fsSL https://tailscale.com/install.sh | sh
fi
echo "[bootstrap] NOTE: run 'tailscale up' yourself to authenticate this node."

if [ "$WITH_CADDY" -eq 1 ]; then
  if command -v caddy >/dev/null 2>&1; then
    echo "[bootstrap] Caddy already installed."
  else
    echo "[bootstrap] installing Caddy (official apt repo)…"
    apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
      | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
      | tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
    apt-get update -y
    apt-get install -y caddy
  fi
fi

# Firewall: allow SSH + HTTP/HTTPS only. Ollama (11434) is NEVER opened — the
# Droplet reaches Ollama over the private Tailscale interface, not the public
# internet. (ufw is configured but NOT auto-enabled to avoid SSH lockout; the
# operator enables it deliberately — see docs/DIGITALOCEAN_DEPLOYMENT.md.)
echo "[bootstrap] preparing ufw rules (not auto-enabling)…"
ufw allow OpenSSH       || ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
echo "[bootstrap] ufw rules staged. Enable deliberately with: ufw enable"
echo "[bootstrap] do NOT 'ufw allow 11434' — Ollama stays private over Tailscale."

echo "[bootstrap] done. Next: tailscale up · create .pedesk_prod.env · do_preflight.sh"
