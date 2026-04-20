#!/usr/bin/env bash
# One-time bootstrap for an Azure Ubuntu VM.
# Run as: sudo bash vm_setup.sh <admin_username> <admin_password>
# Prereqs: Ubuntu 22.04 LTS, outbound internet access.

set -euo pipefail

ADMIN_USER="${1:-admin}"
ADMIN_PASS="${2:?Usage: vm_setup.sh <admin_user> <admin_pass>}"
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
docker compose -f ../deploy/docker-compose.yml up -d --build

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
docker compose -f ../deploy/docker-compose.yml exec rcm-mc \
    python -m rcm_mc portfolio --db /data/rcm_mc.db \
    users create --username "$ADMIN_USER" --password "$ADMIN_PASS" --role admin \
    2>/dev/null || echo "(User may already exist — skipping)"

echo ""
echo "Done. RCM-MC is live at http://$(curl -sf ifconfig.me):8080/"
echo "Admin user: $ADMIN_USER"
echo ""
echo "Firewall: run 'ufw allow 8080/tcp && ufw enable' to open the port."
