#!/usr/bin/env bash
# One-time bootstrap for an Azure Ubuntu VM.
#
# Run as:
#   sudo bash vm_setup.sh <admin_username> <admin_password> [domain]
#
# When `domain` is passed, the script brings up the Caddy TLS
# sidecar — Caddy provisions a Let's Encrypt cert on first boot.
# The domain MUST have an A record pointing at the VM's public IP
# before you run this, or the LE challenge will fail and the cert
# won't be issued (Caddy will retry in the background; check logs
# with `docker compose logs caddy`).
#
# Without a `domain` argument, the script brings up only the origin
# on port 8080 — fine for a VM-internal test, not for a partner demo.
#
# Prereqs: Ubuntu 22.04 LTS, outbound internet access.

set -euo pipefail

ADMIN_USER="${1:-admin}"
ADMIN_PASS="${2:?Usage: vm_setup.sh <admin_user> <admin_pass> [domain]}"
DOMAIN="${3:-}"
REPO="https://github.com/DrewThomas09/RCM.git"
APP_DIR="/opt/rcm-mc"
DATA_DIR="/data/rcm"

echo "=== [1/6] System packages ==="
apt-get update -qq
apt-get install -y --no-install-recommends \
    git curl ca-certificates gnupg lsb-release ufw

echo "=== [2/6] Docker ==="
if ! command -v docker &>/dev/null; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /usr/share/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) \
        signed-by=/usr/share/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -qq
    apt-get install -y docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin
    systemctl enable --now docker
fi

echo "=== [3/6] Clone repo ==="
mkdir -p "$APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" pull --ff-only
else
    git clone "$REPO" "$APP_DIR"
fi

echo "=== [4/6] Data directory ==="
mkdir -p "$DATA_DIR"

echo "=== [5/6] Install systemd service ==="
cp "$APP_DIR/deploy/rcm-mc.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable rcm-mc

echo "=== [6/6] First-time build + start ==="
cd "$APP_DIR/RCM_MC"
COMPOSE_FILE="../deploy/docker-compose.yml"

if [ -n "$DOMAIN" ]; then
    echo "    DOMAIN=$DOMAIN set — bringing up Caddy TLS sidecar"
    export DOMAIN
    docker compose -f "$COMPOSE_FILE" --profile tls up -d --build
else
    echo "    No domain — origin only (port 8080, no TLS)"
    docker compose -f "$COMPOSE_FILE" up -d --build
fi

# Wait for server to be ready (up to 60s)
echo "Waiting for /health..."
for i in $(seq 1 12); do
    if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
        echo "Server is up."
        break
    fi
    sleep 5
done

echo "=== Creating admin user ==="
docker compose -f "$COMPOSE_FILE" exec rcm-mc \
    python -m rcm_mc portfolio --db /data/rcm_mc.db \
    users create --username "$ADMIN_USER" --password "$ADMIN_PASS" --role admin \
    2>/dev/null || echo "(User may already exist — skipping)"

echo ""
PUBLIC_IP="$(curl -sf ifconfig.me || echo '<public-ip>')"
if [ -n "$DOMAIN" ]; then
    echo "Done. RCM-MC is live at https://$DOMAIN/"
    echo "  (Let's Encrypt cert is being provisioned on first boot —"
    echo "   check 'docker compose logs caddy' if HTTPS doesn't"
    echo "   respond within 60 seconds; DNS A-record for $DOMAIN"
    echo "   must point at $PUBLIC_IP for the challenge to succeed.)"
    echo ""
    echo "Firewall: run 'ufw allow 80/tcp && ufw allow 443/tcp && ufw enable'"
else
    echo "Done. RCM-MC is live at http://${PUBLIC_IP}:8080/"
    echo ""
    echo "Firewall: run 'ufw allow 8080/tcp && ufw enable' to open the port."
    echo "For HTTPS, re-run with a domain: sudo bash vm_setup.sh $ADMIN_USER <pw> your.domain.com"
fi
echo "Admin user: $ADMIN_USER"
