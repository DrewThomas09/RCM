# Report 0041: Config Map — `RCM_MC/deploy/docker-compose.yml`

## Scope

Documents every key in `RCM_MC/deploy/docker-compose.yml` (86 lines) on `origin/main` at commit `f3f7e7f`. Owed since Reports 0026, 0028, 0032.

Prior reports reviewed: 0037-0040.

## Findings

### Top-level structure

```yaml
version: "3.9"

services:
  rcm-mc: ...
  caddy: ...

volumes:
  caddy_data:
  caddy_config:
```

Compose file format **3.9**. Two services + two volumes.

### Service `rcm-mc` (the application)

| Key | Value | Notes |
|---|---|---|
| `build.context` | `..` | Build context = repo root |
| `build.dockerfile` | `deploy/Dockerfile` | Per Report 0033 |
| `ports` | `"8080:8080"` | Direct host expose for testing; comment says "comment out in production where Caddy is the only ingress" |
| `expose` | `"8080"` | Internal Docker network |
| `volumes` | `/data/rcm:/data` | SQLite persistence at `/data/rcm` on host |
| `environment` | 6 env vars (see below) | |
| `restart` | `unless-stopped` | Auto-restart on crash |
| `logging.driver` | `json-file` | |
| `logging.options.max-size` | `50m` | Log rotation |
| `logging.options.max-file` | `5` | Keep 5 rotated files |

**Environment variables (rcm-mc service):**

| Key | Default | Source |
|---|---|---|
| `RCM_MC_DB` | `/data/rcm_mc.db` | Hardcoded; **redundant with `Dockerfile:20`** (Report 0033 MR284) |
| `RCM_MC_AUTH` | `${RCM_MC_AUTH:-}` (empty if unset) | Per Report 0019 — HTTP Basic creds |
| `ANTHROPIC_API_KEY` | `${ANTHROPIC_API_KEY:-}` (empty) | Per Report 0025 — LLM key |
| `RCM_MC_PHI_MODE` | `${RCM_MC_PHI_MODE:-disallowed}` (defaults to "disallowed") | Per Report 0028 — banner toggle |
| `RCM_MC_HOMEPAGE` | `${RCM_MC_HOMEPAGE:-dashboard}` (defaults to "dashboard") | Per Report 0019 — root redirect |
| `RCM_MC_SESSION_IDLE_MINUTES` | `${RCM_MC_SESSION_IDLE_MINUTES:-30}` | Per Report 0019 — auth idle timeout |

**6 vars set; 4 with defaults; 2 unset-pass-through (`RCM_MC_AUTH`, `ANTHROPIC_API_KEY`).**

### Service `caddy` (the TLS terminator)

| Key | Value | Notes |
|---|---|---|
| `image` | `caddy:2-alpine` | Pinned major version 2; alpine variant. Latest 2.x at deploy time. **No SHA pin.** |
| `ports` | `"80:80"`, `"443:443"`, `"443:443/udp"` (HTTP/3) | TLS termination ports |
| `volumes` | `./Caddyfile:/etc/caddy/Caddyfile:ro` + `caddy_data:/data` + `caddy_config:/config` | Caddyfile mounted read-only; LE certs persisted |
| `environment.DOMAIN` | `${DOMAIN:?set DOMAIN=your.domain.com in host env before compose up}` | **Fails fast** if not set |
| `depends_on` | `rcm-mc` | Caddy starts after origin |
| `restart` | `unless-stopped` | |
| `logging` | (same as rcm-mc) | |
| `profiles` | `[tls]` | **Opt-in service.** `docker compose up` does NOT start Caddy; `docker compose --profile tls up` does. |

**Profiles gate the TLS sidecar behind an explicit opt-in** (line 75-79 comment). This is unusual but principled — local-dev gets origin only.

### Volumes

| Volume | Purpose |
|---|---|
| `caddy_data` | Persists Let's Encrypt certs + session state. Critical: LE rate-limits to ~5 issuances/week/domain — without persistence, every restart re-issues and gets blocked. |
| `caddy_config` | Caddy admin config state. |

### Required host env vars (per comment block lines 14-22)

| Var | Required when | Purpose |
|---|---|---|
| `DOMAIN` | Caddy profile is enabled | Site name + LE cert |
| `ADMIN_USERNAME` | First boot bootstrap | Initial admin user |
| `ADMIN_PASSWORD` | First boot bootstrap | Initial admin password |
| `ANTHROPIC_API_KEY` | Optional | `/settings/ai` toggle |
| `RCM_MC_PHI_MODE` | Optional (defaults disallowed) | UI banner |
| `RCM_MC_HOMEPAGE` | Optional (defaults dashboard) | Root redirect |

**Note:** `ADMIN_USERNAME` + `ADMIN_PASSWORD` are mentioned in the comment but **not actually wired into the rcm-mc service's environment list**. They must be consumed by the `vm_setup.sh` bootstrap (per Report 0032), not by the running container. Subtle dependency.

### Each key's reader

| Key | Reader |
|---|---|
| `RCM_MC_DB` | `server.py:96` (Report 0019) |
| `RCM_MC_AUTH` | `server.py:16264` (Report 0018, 0019) |
| `ANTHROPIC_API_KEY` | `server.py:3622` + `ai/llm_client.py:147` (Report 0025) |
| `RCM_MC_PHI_MODE` | `_chartis_kit.py:63` + `dashboard_page.py:2424` (Report 0028) |
| `RCM_MC_HOMEPAGE` | `server.py:1953` (Report 0019) |
| `RCM_MC_SESSION_IDLE_MINUTES` | `auth/auth.py:230 _idle_timeout_minutes()` (Report 0021) |
| `DOMAIN` | Caddy reads from container env (templated into `{$DOMAIN}` in Caddyfile) |

**All 6 service env vars have known production readers.** No dead env vars.

### What's NOT documented

- **No `ADMIN_USERNAME` / `ADMIN_PASSWORD` reader** in the service env. The comment promises bootstrap-time use; needs `vm_setup.sh` audit (Report 0032 deferred).
- **No env-var override for log level** — combined with Report 0024 MR199.
- **No env-var for the `--port` override** — server runs on 8080 (Dockerfile CMD per Report 0033).
- **No healthcheck overrides** — relies on Dockerfile's HEALTHCHECK clause.
- **No resource limits** (`mem_limit`, `cpu_limit`) — container can consume unlimited resources.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR331** | **`RCM_MC_DB=/data/rcm_mc.db` set in BOTH Dockerfile and docker-compose.yml** (cross-link Report 0033 MR284) | Redundant; if they ever diverge, compose wins. **Recommend: pick one location.** | Low |
| **MR332** | **`ADMIN_USERNAME`/`ADMIN_PASSWORD` mentioned in comments but not in service env** | Operators following docker-compose comments may set them and find no effect. Bootstrap (vm_setup.sh) consumes them; service container doesn't. **Document the split.** | Medium |
| **MR333** | **`caddy:2-alpine` floats** (no digest pin) | Each `docker pull` may get a new patch. Recommend pinning to digest for reproducibility. | Medium |
| **MR334** | **`profiles: [tls]` opt-in TLS** | An operator who runs `docker compose up` (forgetting `--profile tls`) gets HTTP-only deploy. **Production-incident risk** if forgotten. | **High** |
| **MR335** | **No resource limits on `rcm-mc` container** | A runaway request could OOM the VM. | Medium |
| **MR336** | **`expose: 8080` is redundant** with `ports: "8080:8080"` | Both serve same purpose. Cosmetic. | Low |
| **MR337** | **No env-var override for `--port`** | Container always binds 8080. Multi-instance deploys impossible without compose-file edit. | Low |
| **MR338** | **`/data/rcm:/data` mount needs host-side dir creation** | `vm_setup.sh:25` creates it (per Report 0032), but compose doesn't. **Compose-only deploys fail without manual mkdir.** | Medium |
| **MR339** | **No `secrets:` block** | API keys + admin password live in plain env vars. Compose secrets feature unused. **OK for single-VM deploy; risk for multi-tenant.** | Medium |
| **MR340** | **No backup-volume mount** | `infra/backup.py` writes backups (Report 0024). Where? Default likely `/data` (same volume), so backups live alongside the DB they back up. **Single-volume backup is no backup.** | **High** |

## Dependencies

- **Incoming:** `vm_setup.sh` (Azure VM bootstrap — Report 0032), `rcm-mc.service` (systemd unit — Report 0032), GitHub Actions deploy.yml (Report 0026).
- **Outgoing:** Docker, docker-compose, host env vars, caddy:2-alpine image.

## Open questions / Unknowns

- **Q1.** Where are backups actually written? Same `/data/rcm` volume? Different mount?
- **Q2.** Is the `profiles: [tls]` gate consistent with the deploy.yml workflow's `docker compose -f deploy/docker-compose.yml up -d --build` command (Report 0026)? **No `--profile tls` in deploy.yml — Caddy may not start in production**.
- **Q3.** What does `vm_setup.sh` actually do with `ADMIN_USERNAME` / `ADMIN_PASSWORD`?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0042** | **Data flow trace** (already requested as iteration 42). | Pending. |
| **0043** | **Read `vm_setup.sh`** (109 lines) | Resolves Q3. |
| **0044** | **Verify deploy.yml uses `--profile tls`** | Resolves Q2; if not, MR334 escalates. |
| **0045** | **Read `infra/backup.py`** | Resolves Q1 / MR340. |

---

Report/Report-0041.md written. Next iteration should: trace the `DOMAIN` env var as a data-flow source — host shell → docker-compose interpolation → Caddyfile templating → Let's Encrypt cert provisioning → HTTPS termination — closes Report 0026 + 0032 + Q2 here in one trace.

