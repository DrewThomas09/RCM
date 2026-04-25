# Azure VM Deploy — Quickstart

**One page. Five commands. Working server in ~10 minutes.**

The full design rationale, threat-model, and verified-against-source assessment lives in [`DEPLOYMENT_PLAN.md`](DEPLOYMENT_PLAN.md). This page is the runbook.

---

## What you get

A single Azure Ubuntu VM running:

- The RCM-MC stdlib HTTP server on port 8080 (15,327 LOC, 88+ routes, scrypt+session auth, CSRF, rate limit, audit log)
- SQLite on a persistent volume mount (`/data/rcm` → `/data` inside the container)
- Optional Caddy TLS sidecar (Let's Encrypt) — opt-in via `--profile tls`
- systemd unit so the stack comes up on reboot
- 50 MB × 5 file log rotation

No Postgres, no Redis, no Kubernetes. Single-process job queue is intentional — Deal MC at 3,000 trials needs a long-running thread, not a worker pool.

---

## Prerequisites

| Requirement | Detail |
|---|---|
| Azure VM | Ubuntu 22.04 LTS, B2s (~2 vCPU / 4GB) for testing, B4ms (4 vCPU / 16GB) for production |
| Inbound rules | Port 22 (SSH), 80 + 443 (if using Caddy/TLS), 8080 (if testing without Caddy) |
| Outbound | Internet access (to clone repo, pull Docker images, fetch CMS data on first refresh) |
| Domain (optional) | A-record pointing at VM public IP. Required only if you want Caddy + Let's Encrypt TLS |
| BAA | If handling PHI, sign the Azure BAA before pointing real data at this VM |

---

## Deploy in 5 commands

SSH into the VM and run:

```bash
# 1. Pull the bootstrap script from the repo (no clone needed yet — vm_setup.sh does the clone itself)
curl -fsSL https://raw.githubusercontent.com/DrewThomas09/RCM/main/RCM_MC/deploy/vm_setup.sh -o /tmp/vm_setup.sh

# 2. Without TLS (VM-internal testing — server reachable on http://<public-ip>:8080)
sudo bash /tmp/vm_setup.sh <admin_username> <admin_password>

# 2-alt. With TLS (Caddy + Let's Encrypt; requires the A-record pointing at this VM beforehand)
sudo bash /tmp/vm_setup.sh <admin_username> <admin_password> diligence.example.com

# 3. Verify
curl -fsS http://localhost:8080/health   # local check
curl -fsS https://diligence.example.com/health   # public check, if TLS enabled

# 4. Open in browser
# http://<public-ip>:8080  (no TLS) — login with the admin user from step 2
# https://diligence.example.com  (TLS) — same login

# 5. (optional) Tail logs
docker compose -f /opt/rcm-mc/RCM_MC/deploy/docker-compose.yml logs -f
```

The script handles: apt update, Docker install, repo clone to `/opt/rcm-mc`, image build, volume creation, admin-user create, healthcheck wait, firewall hint.

---

## What lives where after install

| Path | What |
|---|---|
| `/opt/rcm-mc/` | Cloned repo |
| `/opt/rcm-mc/RCM_MC/deploy/docker-compose.yml` | Compose stack (origin + optional Caddy) |
| `/data/rcm/rcm_mc.db` | SQLite database (persistent across container restarts) |
| `/etc/systemd/system/rcm-mc.service` | systemd unit that brings up `docker compose` on boot |
| Docker volume `caddy_data` | Let's Encrypt cert state (only with TLS profile) |

---

## Common operations

| Task | Command |
|------|---------|
| Restart the stack | `sudo systemctl restart rcm-mc` |
| Pull latest code + rebuild | `cd /opt/rcm-mc && sudo git pull && sudo docker compose -f RCM_MC/deploy/docker-compose.yml up -d --build` |
| Backup the DB | `sudo cp /data/rcm/rcm_mc.db /data/rcm/backup-$(date +%F).db` |
| Add a user | `sudo docker compose -f /opt/rcm-mc/RCM_MC/deploy/docker-compose.yml exec rcm-mc python -m rcm_mc.portfolio_cmd users create --username NAME --password PASS --role analyst` |
| Tail logs | `sudo docker compose -f /opt/rcm-mc/RCM_MC/deploy/docker-compose.yml logs -f rcm-mc` |
| Shell into the container | `sudo docker compose -f /opt/rcm-mc/RCM_MC/deploy/docker-compose.yml exec rcm-mc bash` |

---

## Configuration via env vars (set in `/opt/rcm-mc/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `ADMIN_USERNAME` | (required at install) | First admin user, created at release-phase |
| `ADMIN_PASSWORD` | (required at install) | Password for that admin |
| `RCM_MC_PHI_MODE` | `disallowed` | Set to `allowed` only if VM is BAA-covered. Controls the PHI banner |
| `RCM_MC_HOMEPAGE` | `dashboard` | Where `/` redirects (`dashboard` or `home`) |
| `RCM_MC_SESSION_IDLE_MINUTES` | `30` | Session idle timeout |
| `ANTHROPIC_API_KEY` | unset | Enables `/settings/ai` features (optional) |
| `DOMAIN` | unset | Required if using Caddy / `--profile tls` |

After editing `.env`: `sudo systemctl restart rcm-mc`.

---

## TLS / Caddy

If you set `DOMAIN` and run `docker compose --profile tls up`, Caddy will:

1. Listen on 80 / 443 / 443-UDP (HTTP/3)
2. Auto-provision a Let's Encrypt cert on first boot (rate-limited to 5/week per domain — don't burn it)
3. Proxy → `rcm-mc:8080` with `X-Forwarded-Proto: https`
4. Persist cert state in the `caddy_data` Docker volume so reboots don't trigger re-issuance

If LE issuance fails, check: A-record points at this VM's public IP, port 80 is open inbound, `docker compose logs caddy`.

---

## Health check

```bash
curl -fsS http://localhost:8080/health
# → {"status":"ok","version":"...","uptime_seconds":...}
```

The same endpoint backs the Docker `HEALTHCHECK` directive (30s interval, 5s timeout, 3 retries) so a stuck process triggers an automatic container restart.

---

## Rolling back

The service is a single Docker container. To roll back:

```bash
cd /opt/rcm-mc && sudo git checkout <prev-commit-sha>
sudo docker compose -f RCM_MC/deploy/docker-compose.yml up -d --build
```

The DB schema uses idempotent `CREATE TABLE IF NOT EXISTS` migrations, so rolling back code never breaks the DB. Roll back the DB separately if needed: replace `/data/rcm/rcm_mc.db` from a backup, then restart.

---

## Pre-go-live checklist

- [ ] VM sized (B4ms+ for production)
- [ ] Inbound firewall: 22 / 80 / 443 only (close 8080 once Caddy is in front)
- [ ] BAA signed with Azure if PHI is in scope
- [ ] `RCM_MC_PHI_MODE=allowed` set only if BAA is in place; default `disallowed` shows the banner
- [ ] `.env` has unique `ADMIN_USERNAME` / `ADMIN_PASSWORD` (don't ship the install defaults)
- [ ] Domain A-record points at VM, TLS provisioned, `https://...` resolves
- [ ] First DB backup taken (`/data/rcm/backup-<date>.db`) and confirmed restoreable on a second VM
- [ ] `docker compose logs` clean for 5 minutes under light load
- [ ] One end-to-end deal walkthrough in production matches the test environment

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `curl localhost:8080/health` hangs | Server didn't bind 0.0.0.0 | Check `Dockerfile` CMD has `--host 0.0.0.0` (it does on `main`) |
| 502 Bad Gateway from Caddy | `rcm-mc` container not running | `docker compose ps`, check `logs rcm-mc` |
| Login works on host but fails through Caddy | Cookie marked Secure but request is HTTP | Caddy is misrouting; verify the proxy block in `Caddyfile` |
| Cert not provisioning | A-record wrong or port 80 closed | Check `dig <domain>` returns the VM IP, open inbound port 80 |
| DB file zero bytes after restart | Volume mount missing | `docker compose config` should show `/data/rcm:/data`; the systemd unit should specify `volumes:` in the compose file |
| `lsof: command not found` in container | Slim base image | use `ss -tlnp` instead, or `apt-get install -y lsof` if shelling in |

---

## Going further

- Detailed assessment + threat model: [`DEPLOYMENT_PLAN.md`](DEPLOYMENT_PLAN.md)
- PHI handling architecture: [`RCM_MC/docs/PHI_SECURITY_ARCHITECTURE.md`](RCM_MC/docs/PHI_SECURITY_ARCHITECTURE.md)
- 6-month roadmap (incl. Tier-1 PHI controls): [`RCM_MC/docs/PRODUCT_ROADMAP_6MO.md`](RCM_MC/docs/PRODUCT_ROADMAP_6MO.md)
- Beta program ops (provisioning per design partner): [`RCM_MC/docs/BETA_PROGRAM_PLAN.md`](RCM_MC/docs/BETA_PROGRAM_PLAN.md)
