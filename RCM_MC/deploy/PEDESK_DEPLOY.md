# Deploying to `pedesk.app`

Step-by-step walkthrough for a clean `hotfix-security-on-v5` deploy to
the `pedesk.app` domain. Targets a fresh Azure Ubuntu 22.04 LTS VM
(public IP, ports 80/443/8080 open). One-shot: ~10 minutes from
`ssh` to live HTTPS.

The deploy stack is already in this directory:

| File | Role |
|---|---|
| `Dockerfile` | Python 3.14 + stdlib + `numpy/pandas/matplotlib/pyyaml/openpyxl` only |
| `docker-compose.yml` | Two services — `rcm-mc` origin + optional `caddy` TLS sidecar |
| `Caddyfile` | Reverse proxy with auto Let's Encrypt + HSTS + hardened headers |
| `rcm-mc.service` | systemd unit so the stack survives reboot |
| `vm_setup.sh` | One-shot bootstrap (Docker install + clone + compose up) |

## Prerequisites

1. **DNS A record** on `pedesk.app` (and any subdomains) pointing at
   the VM's public IPv4. Without this, Caddy's Let's Encrypt
   challenge fails and HTTPS won't come up.
2. **Ports open** on the VM's NSG / `ufw`:
   - `80/tcp` — Let's Encrypt HTTP-01 challenge
   - `443/tcp` + `443/udp` — HTTPS (TCP) + HTTP/3 (QUIC)
3. **SSH access** with sudo.

## One-shot bootstrap

```bash
# On the VM
sudo bash -c 'curl -fsSL \
  https://raw.githubusercontent.com/DrewThomas09/RCM/hotfix-security-on-v5/RCM_MC/deploy/vm_setup.sh \
  -o /tmp/vm_setup.sh'

# Args: <admin-user> <admin-password> [domain]
sudo bash /tmp/vm_setup.sh admin 'StrongAdminPass!12' pedesk.app
```

The bootstrap script:
1. Installs Docker Engine + Compose plugin
2. Clones the repo into `/opt/rcm-mc`
3. Installs the systemd unit (`rcm-mc.service` enabled + started)
4. Brings up `docker compose --profile tls up -d --build` (origin + Caddy)
5. Waits for `/health` to respond
6. Creates the admin user in SQLite (`/data/rcm/rcm_mc.db`)

When it returns, hit `https://pedesk.app/` and log in.

## What's new in this deploy (vs. last main)

This branch is **156 commits ahead** of `origin/main` with four
orthogonal compounding threads, all editorial-style consistent:

| Thread | Surfaces | Real bugs fixed |
|---|---|---|
| Up-next continuation cues | 96 daily-use surfaces | 4 broken routes, 6 italic-word mismatches |
| Print-preview mode | 8 IC-deliverable pages | — |
| Help-tooltip glosses | ~37 partner surfaces, ~110 popovers | — |
| Math + defensiveness audit | 6 segments | 3 real bugs fixed |
| **NPPES provider directory** (new) | `/hospital/<ccn>/providers` | — |

**Zero new runtime dependencies.** NPPES live-API client is
stdlib-only (urllib + json + sqlite3). The cache table
(`nppes_live_cache`) is created idempotently by
`rcm_mc.data_public.nppes_cache.ensure_table` on first navigation —
no migration step required.

## NPPES freshness operations

The provider directory page (`/hospital/<ccn>/providers`) reads from
a 30-day SQLite cache. **It does not hit the NPPES API on every page
load** — that would be rate-limited and slow. To populate or refresh
a CCN's roster:

```bash
# From inside the rcm-mc container
docker compose exec rcm-mc \
  python -m rcm_mc data refresh-nppes \
  --ccn 123456 \
  --name "Demo Health System" \
  --state GA

# Or from outside:
docker compose exec rcm-mc \
  /usr/local/bin/rcm-mc data refresh-nppes --ccn 123456 --name "Demo" --state GA
```

The page surfaces freshness via a chip — green <30d, amber 30-90d,
red >90d. Empty state shows the CLI command pre-filled with the
hospital's HCRIS-resolved name + state, so partners running it for
the first time copy-paste rather than type.

## Smoke test after deploy

```bash
# Health endpoint (no auth, no UI chrome)
curl -sf https://pedesk.app/health && echo OK

# Editorial-shell render (no auth — login page)
curl -sf https://pedesk.app/login | grep -q "Source+Serif+4" && echo "fonts loaded"

# Authenticated routes (via Caddy + session cookie):
#   /app                          — command center
#   /day-one                      — morning brief
#   /diligence/deal/<slug>        — deal profile
#   /diligence/risk-workbench     — 9-panel risk panorama
#   /diligence/hcris-xray         — HCRIS X-Ray
#   /hospital/<ccn>/providers     — NPPES provider directory (NEW)
#   /diligence/comparable-outcomes — corpus comparables
#   /ic-memo/<ccn>?print=1        — print-preview IC memo
#   /diligence/questions?print=1   — questions ledger print
```

If any route 500s, check `docker compose logs rcm-mc | grep ERROR`.

## Rollback

The systemd unit holds the compose state. To roll back to a previous
commit:

```bash
cd /opt/rcm-mc/RCM_MC
sudo git checkout <prev-sha>
sudo systemctl restart rcm-mc
# docker compose rebuilds on restart via ExecStart
```

SQLite at `/data/rcm/rcm_mc.db` is unchanged across deploys —
schemas are forward-compatible (new tables are additive; legacy
readers ignore new columns).

## Required env (host shell before `docker compose up`)

| Var | Value for pedesk.app | Notes |
|---|---|---|
| `DOMAIN` | `pedesk.app` | gates Caddy TLS sidecar |
| `ADMIN_USERNAME` | (your choice) | passed to bootstrap |
| `ADMIN_PASSWORD` | strong | scrypt-hashed in SQLite |
| `ANTHROPIC_API_KEY` | optional | only for `/settings/ai` |
| `RCM_MC_PHI_MODE` | `disallowed` | shows banner; recommended |
| `RCM_MC_HOMEPAGE` | `app` | `/` → `/app` editorial command center |
| `CHARTIS_UI_V2` | `1` | pin editorial UI on |
| `RCM_MC_SESSION_IDLE_MINUTES` | `30` | session idle timeout |

The bootstrap script reads `DOMAIN` from positional arg 3; the rest
default sensibly if unset.

## Editorial style — verified at build

The Dockerfile copy-step pulls the full `rcm_mc/` package including
`ui/_chartis_kit.py`, the editorial CSS tokens, and font preconnect
markers (Source Serif 4, Inter Tight, JetBrains Mono). No CDN-side
asset hosting needed — the shell embeds everything inline at render
time.

A `/health` smoke test confirms the server is up. To verify
editorial style after deploy:

```bash
curl -sf https://pedesk.app/login | python3 -c "
import sys
body = sys.stdin.read()
for f in ('Source+Serif+4', 'Inter+Tight', 'JetBrains+Mono'):
    print(('✓' if f in body else '✗'), f)
"
```

All three should print `✓`.
