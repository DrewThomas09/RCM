# Report 0032: `RCM_MC/deploy/` Directory Inventory

## Scope

Maps every file in `RCM_MC/deploy/` on `origin/main` at commit `f3f7e7f`. This dir was deferred 6+ times (Reports 0023, 0026, 0027, 0028, 0030, 0031). 5 files, 214 lines + 2,411 + 1,186 = ~5,800 B total.

Prior reports reviewed: 0028-0031.

## Findings

### Inventory (5 files, 214+ lines text + Dockerfile + Caddyfile)

| Path | Size | Lines | Purpose |
|---|---:|---:|---|
| [`RCM_MC/deploy/Caddyfile`](../RCM_MC/deploy/Caddyfile) | 2,411 B | (text) | Reverse-proxy config. Auto-provisions Let's Encrypt cert for `{$DOMAIN}`. Proxies to `rcm-mc:8080`. Sets `X-Forwarded-Proto: https`. |
| [`RCM_MC/deploy/Dockerfile`](../RCM_MC/deploy/Dockerfile) | 1,186 B | 35 | Build the rcm-mc container. `FROM python:3.14-slim`. Installs gcc/g++ for numpy/pandas. Runs `pip install --no-cache-dir .` (no extras). Sets `RCM_MC_DB=/data/rcm_mc.db`. EXPOSE 8080. HEALTHCHECK every 30s. ENTRYPOINT `python -m rcm_mc serve` + CMD `--host 0.0.0.0 --port 8080`. |
| [`RCM_MC/deploy/docker-compose.yml`](../RCM_MC/deploy/docker-compose.yml) | 2,947 B | 86 | Compose stack: rcm-mc service (build from `..`, port 8080→8080, mount `/data/rcm`, env vars per Report 0019). Also wires Caddy sidecar (per Caddyfile). |
| [`RCM_MC/deploy/rcm-mc.service`](../RCM_MC/deploy/rcm-mc.service) | 681 B | 19 | systemd unit. `Type=oneshot RemainAfterExit=yes`. WorkingDirectory `/opt/rcm-mc/RCM_MC`. ExecStart = `docker compose -f deploy/docker-compose.yml up -d --build`. Restart on failure. |
| [`RCM_MC/deploy/vm_setup.sh`](../RCM_MC/deploy/vm_setup.sh) | 3,792 B | 109 | One-time Azure VM bootstrap. Takes `<admin_user> <admin_pass> [domain]` args. Clones from `https://github.com/DrewThomas09/RCM.git` to `/opt/rcm-mc`. Sets up `/data/rcm`. |

### Suspicious / out-of-place items

- **No `.DS_Store`, no tmp files, no untracked binaries.** Clean.
- **No `.env.example`** or template — operators have no canonical env-var reference (cross-link Report 0019 MR146 — no env-var documentation).
- **No `docker-stack.yml` or k8s manifest** — single-VM deploy only.
- **No `nginx.conf` / `apache.conf`** — Caddy is the only reverse-proxy choice.
- **No `production.yaml` or environment-specific configs** — env vars carry all config differentiation.

### Key facts surfaced

| Fact | Site |
|---|---|
| Default install installs **only core deps**, no extras | `Dockerfile:16` `pip install --no-cache-dir .` (no `[exports]`, no `[diligence]`, no `[all]`) |
| Production overrides `127.0.0.1` default with `--host 0.0.0.0` | `Dockerfile:35` (with comment explaining the subtlety) |
| `RCM_MC_DB` env var is set to `/data/rcm_mc.db` in the container | `Dockerfile:20` AND `docker-compose.yml:38` (redundant — compose-yml wins) |
| Caddy sidecar handles HTTPS | `Caddyfile` — auto Let's Encrypt |
| systemd unit relies on Docker | `rcm-mc.service:5` `Requires=docker.service` |
| Repo source URL hard-coded | `vm_setup.sh:24` `REPO="https://github.com/DrewThomas09/RCM.git"` |
| Bootstrap creates `/data/rcm` data dir | `vm_setup.sh:25` |
| Container HEALTHCHECK uses urllib | `Dockerfile:24-25` — calls `http://localhost:8080/health` |

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR283** | **Dockerfile installs ONLY core deps** | `pip install --no-cache-dir .` — no `[exports]`, `[diligence]`, `[api]`, `[all]`. Per Report 0023 MR183, `rcm_mc/diligence/ingest/` requires `pyarrow` (in `[diligence]` extras). **Production runs without pyarrow** — any path through diligence/ingest hits ImportError at runtime. **Critical.** | **Critical** |
| **MR284** | **Dockerfile sets `RCM_MC_DB=/data/rcm_mc.db` (line 20)** but `docker-compose.yml:38` **also** sets it. Redundant. If they ever diverge, compose-yml wins (env vars set after Dockerfile ENV). | Low |
| **MR285** | **`vm_setup.sh:24` hard-codes the repo URL** `https://github.com/DrewThomas09/RCM.git` | A fork of the project would need to edit the script. Acceptable for single-owner repo; flagged for any future fork. | Low |
| **MR286** | **systemd unit's `WorkingDirectory=/opt/rcm-mc/RCM_MC` is location-locked** | Hard-coded; mismatched if `vm_setup.sh` ever changes its clone target. Cross-link: `vm_setup.sh:25` uses `APP_DIR="/opt/rcm-mc"`. Consistent today. | Low |
| **MR287** | **No `.env.example` for operators** | Operators must read `docker-compose.yml:14-23` comments + Report 0019's env-var inventory to know what's settable. **No copy-paste-ready env file.** | Medium |
| **MR288** | **`pyproject.toml`'s `requires-python = ">=3.10"` but Dockerfile pins `python:3.14-slim`** | The container runs the latest declared Python. Acceptable; Caddyfile/systemd don't constrain. | Low |
| **MR289** | **No layered Docker cache strategy** | Dockerfile copies `pyproject.toml` then `rcm_mc/` (line 13-14), then runs `pip install`. **Source-code change invalidates the deps layer**. Layer order should be: `COPY pyproject.toml`, `pip install`, `COPY rcm_mc/`. | Low |
| **MR290** | **No multi-stage build** | Dockerfile is single-stage. `gcc g++` apt packages stay in the final image (line 9-11). **Bloated final image** — these dev tools aren't needed at runtime. | Medium |
| **MR291** | **HEALTHCHECK passes silently if server binds wrong host** | Comment at line 32-34 acknowledges "in-container HEALTHCHECK silently passes either way". So it does NOT catch the 127.0.0.1-vs-0.0.0.0 misconfiguration. **Acceptable but worth noting** as documented limitation. | Low |
| **MR292** | **`feature/workbench-corpus-polish` deletes some deploy files + adds new docker-compose at RCM_MC/ root** (per Report 0007) | Cross-branch interaction. Pre-merge: confirm the path-resolution still works post-merge. | **High** |
| **MR293** | **No backup-restoration script** | `infra/backup.py` exists per Report 0024 but no shell wrapper to restore from backup on a fresh VM. | Medium |

## Dependencies

- **Incoming:** GitHub Actions `deploy.yml` (per Report 0026); operators running `bash vm_setup.sh`; the systemd unit; the deploy.yml SSH script.
- **Outgoing:** Docker, docker-compose, Caddy, systemd, apt, git, Ubuntu 22.04+ — entire host stack.

## Open questions / Unknowns

- **Q1.** Does the docker-compose `volumes: /data/rcm:/data` need ownership setup? `vm_setup.sh:25` creates the dir but doesn't show chown.
- **Q2.** Does the Caddyfile reach the rcm-mc service correctly when the latter doesn't expose `expose: 8080`?
- **Q3.** Is the Dockerfile aware of the broken `rcm-intake` entry point (Report 0003 MR14)?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0033** | **Read `Dockerfile` end-to-end** (already requested as Iteration 33). | Maps the runtime contract. |
| **0034** | **Read `docker-compose.yml` end-to-end** (86 lines). | Sister artifact. |
| **0035** | **Read `vm_setup.sh` end-to-end** (109 lines). | Bootstrap surface. |

---

Report/Report-0032.md written. Next iteration should: read `RCM_MC/deploy/Dockerfile` line-by-line and document the build contract — closes MR283 (no [diligence] extras in production install) and Report 0023 Q1 (which extras are actually present).

