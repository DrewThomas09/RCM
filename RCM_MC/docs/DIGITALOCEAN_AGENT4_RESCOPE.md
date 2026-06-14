# Agent 4 — Infrastructure / Platform / Operations re-scope (DigitalOcean)

> **Purpose.** The prior infra research was written against **Azure**
> assumptions (managed identity, Key Vault, Azure Monitor, Azure Bastion,
> Azure-style backup/HA). Azure-for-Students credit is exhausted and
> production has already moved to a **DigitalOcean Droplet**
> (`https://pedesk.app`). This document re-scopes Agent 4's mandate onto
> DigitalOcean **and** reconciles the generic cloud research against what
> PEdesk actually is — a deliberately minimalist, stdlib-heavy, **SQLite,
> single-machine** Python app. It separates three things that are easy to
> conflate: **what is already live**, **what is right-sized and worth doing
> next**, and **what is enterprise over-engineering we should consciously
> skip** for this workload.

Companion runbooks (the source of truth for current prod):
[`DIGITALOCEAN_DEPLOYMENT.md`](DIGITALOCEAN_DEPLOYMENT.md) (droplet build) ·
[`AUTODEPLOY.md`](AUTODEPLOY.md) (push-to-main pipeline) ·
[`../../AZURE_DEPLOY.md`](../../AZURE_DEPLOY.md) (retired tombstone).

---

## 0. The two corrections that reframe everything

The original research had two load-bearing assumptions that are **wrong for
this app**, and fixing them collapses most of the recommended stack:

1. **PEdesk is not containerized and does not use DOCR.** Production is a
   `git clone` at `/opt/RCM` running under `pedesk.service` (systemd) behind
   **Caddy** (not nginx), and deploy = `git reset --hard origin/main` +
   `pip install -e .` + `systemctl restart pedesk` over **SSH**
   ([`deploy.yml`](../../.github/workflows/deploy.yml)). There is **no
   container image, no registry, and no DigitalOcean API token in the deploy
   path** — CI authenticates with a dedicated **SSH deploy key**
   (`DO_SSH_KEY`), not a DO PAT. So the research's central "no OIDC → PATs
   everywhere / DOCR short-lived logins / image-digest deploys" narrative
   **does not apply to the current pipeline at all**. A DO PAT only enters
   the picture if/when we adopt Terraform or `doctl` (see §1).

2. **PEdesk is SQLite, single-machine, by design.** `CLAUDE.md` lists
   "Single-machine deployment. No clustering, no Postgres path" as a
   deliberate limitation, and the project rule is **zero new runtime
   dependencies**. The research's Managed PostgreSQL (+ standby), Managed
   Caching for Valkey, Load Balancer, and horizontal scaling assume a
   stateless tier over a managed datastore. Adopting them is an
   **application re-architecture**, not an infra task — and is out of scope
   until the product genuinely needs multi-node concurrency. They belong in
   a "if we outgrow SQLite" appendix, not the near-term plan.

Net effect: the honest DO target for PEdesk today is **a hardened single
Droplet with Caddy + systemd**, disciplined secrets, free built-in
monitoring, and a tested backup/restore path — not the full
Terraform/DOCR/Managed-DB/Prometheus enterprise build.

---

## 1. Azure → DigitalOcean fact corrections (authoritative)

These replace the invalid Azure assumptions. They are correct as of June
2026 regardless of whether we adopt them.

| Azure assumption (invalid) | DigitalOcean reality |
|---|---|
| Managed identity / workload identity vends credentials | **No managed identity.** API auth is a long-lived **Personal Access Token (PAT)** bearer. There is **no native GitHub OIDC federation** to the DO API (unlike AWS/Azure/GCP) — the only OIDC route is an experimental self-hosted proxy PoC (`digitalocean-labs/droplet-oidc-poc`), not a platform feature. |
| Key Vault for secrets | **No Key Vault.** Replace with a root-only `.env` (current prod), or SOPS+age / self-hosted Vault / Doppler / 1Password if we want managed rotation. App Platform has `SECRET`-typed env vars. |
| Azure Monitor (APM + logs + traces) | **No Azure Monitor.** DO's built-in **Monitoring** (`do-agent`) is **infra metrics only** (CPU/mem/disk/load/bandwidth, 1-min granularity, ~14-day retention) + free alert policies. Not APM/log/trace. |
| Azure Bastion (managed) | **No managed bastion.** Use a jump Droplet + `ProxyJump`, or — better for confidential data — **Tailscale/WireGuard** so the box has no public SSH. (PEdesk already runs Tailscale for the Mac→Ollama path.) |
| Disk encrypted at rest by default | **Droplet root disk is NOT encrypted at rest.** Block-storage **Volumes**, **Volume Snapshots**, and **Managed Databases** *are* (AES-256 LUKS + SSL in transit). Put confidential data on a Volume if at-rest encryption is required. |
| Azure backup/HA model | Managed PG = daily backups + **PITR to last 7 days** (WAL every 5 min ⇒ worst-case ~5-min RPO), automated failover, HA **only with a standby node**. Droplet **Backups** = weekly full images (20% of droplet cost, last 4 kept), **Snapshots** = on-demand ($0.06/GiB/mo). Neither captures Volumes or Managed-DB data. |
| Managed Redis | **Managed Caching for Valkey** (Redis-compatible) replaced Managed Redis (legacy EOL 30 Apr 2025). |

---

## 2. Re-scoped plan, mapped to PEdesk reality

For each of the original research areas: **what's already done**, **right-
sized next step**, and **what to skip** (and why).

### Area 1 — Hosting & Infrastructure-as-Code
- **Done:** Single Droplet (NYC, Ubuntu 24.04, 2 vCPU / 4 GB), DNS at
  Name.com, hand-provisioned via `scripts/do_bootstrap_server.sh`.
- **Right-sized next:** Capture the *existing* droplet as **Terraform**
  (`digitalocean/digitalocean`, pin `~> 2.x`, state in a **Spaces** S3
  backend with versioning) — `digitalocean_droplet`, `digitalocean_vpc`,
  `digitalocean_firewall`, `digitalocean_reserved_ip`,
  `digitalocean_volume`, `digitalocean_domain`/`_record`,
  `digitalocean_project`. The win is **reproducible rebuild for DR**, not
  multi-node scale. This is where the first **scoped, rotated DO PAT**
  (`DIGITALOCEAN_TOKEN`) actually gets introduced. Use a **reserved IP** so
  DNS survives a rebuild.
- **Skip:** App Platform migration, DOKS, Load Balancer + multiple
  Droplets. Over-built for a single SQLite app; revisit only on the scaling
  trigger in §4.

### Area 2 — Droplet hardening & network security
- **Done:** Tailscale mesh, `ufw` (22/80/443 only, **never 11434**),
  bootstrap script, Caddy TLS. SSH key in CI is a dedicated revocable
  deploy key.
- **Right-sized next:** Confirm `PasswordAuthentication no` +
  `PermitRootLogin` posture, add `fail2ban` (sshd jail) and
  `unattended-upgrades` to the bootstrap script (idempotent), and **move
  SSH fully behind Tailscale** (drop public 22 from the Cloud Firewall) so
  there is no public SSH surface. Add a **DigitalOcean Cloud Firewall**
  (edge-level, free, stateful) as the outer layer in front of `ufw` — keep
  the rules minimal and non-conflicting (DO warns against conflicting
  cloud+host rules). If the app DB/data ever needs at-rest encryption,
  relocate the data dir to an encrypted **Volume** (LUKS).
- **Skip:** Dedicated bastion Droplet (Tailscale already covers it);
  IPSec gateway module.

### Area 3 — CI/CD & release
- **Done:** Push-to-main → test gate → SSH deploy → public health check,
  serialized via `concurrency`, fork-PR-safe (`if: github.ref == main`).
  This is a clean, working pipeline.
- **Right-sized next:** Two small reliability upgrades, in priority order:
  1. **Graceful restart** instead of hard restart. The current
     `systemctl restart pedesk` drops in-flight requests for a beat. A
     gunicorn-style `SIGHUP` graceful reload (`ExecReload=/bin/kill -HUP
     $MAINPID`) — or a brief connection-drain — removes the blip with no
     new infra. *Note:* the app is a stdlib `ThreadingHTTPServer`, so
     graceful reload needs a tiny server-side change; treat as app+infra
     joint work.
  2. **Pin third-party actions by commit SHA** (`appleboy/ssh-action`,
     `actions/checkout`, `setup-python`) and add a **secret-scan**
     pre-commit/CI stage.
- **Skip:** DOCR build/push, image-digest deploys, App Platform
  `app_action`, full **blue-green** with two ports behind nginx. PEdesk
  isn't containerized and Caddy already fronts it — blue-green is a large
  build for a sub-second downtime problem. Reconsider only if zero-downtime
  becomes a hard SLO.

### Area 4 — Observability (replacing Azure Monitor)
- **Done:** App already emits **request observability** in-process
  (p50/p95/p99, `X-Request-Id`, `X-Response-Time`) and a `/healthz` probe
  the deploy gate checks.
- **Right-sized next:** Install **`do-agent`** (free) +
  **alert policies** at DO's recommended starting thresholds (70%
  CPU/mem/disk, load ≈ vCPU count) → email/Slack. Ship `pedesk.service`
  **structured logs** to `journald` (already there) and, if we want
  searchable history, forward to **Grafana Cloud free tier** rather than
  self-hosting. Add a simple external uptime check on `/healthz`.
- **Skip:** Self-hosted **Prometheus + Grafana + Loki + Tempo + OTel
  Collector** on a dedicated Droplet. That stack is appropriate for a
  multi-service fleet; for one single-machine app it is more operational
  surface than the app itself. The golden-signals / SLO / multi-burn-rate
  discipline is still worth *adopting as practice*, but on the free
  built-in + Grafana-Cloud substrate, not a self-run observability cluster.

### Area 5 — Reliability, backup & DR (highest-value area)
- **Gap today:** PEdesk's state is a **SQLite file on the Droplet**, plus
  the git-ignored `.pedesk_prod.env` and the prebuilt RAG index. Droplet
  Backups/Snapshots don't give point-in-time DB recovery, and a single
  Droplet is a single point of failure. This is the area where the research
  is most relevant and most under-served by the current setup.
- **Right-sized next (do this first of everything):**
  1. **Scheduled, encrypted, offsite backups to Spaces (3-2-1).** Cron a
     job that snapshots the SQLite DB (use the app's existing
     `/api/backup` or `sqlite3 .backup`), encrypts
     (`openssl enc -aes-256-cbc` or age), and `rclone`/`s3cmd`-uploads to
     **Spaces** (`nyc3.digitaloceanspaces.com`) with a lifecycle/retention
     policy. Include the RAG index and a *redacted* record of which env
     keys must be set (never the secret values).
  2. **Document + test restore.** A DR runbook for the two real scenarios:
     *(a)* Droplet destroyed → `terraform apply` rebuild (from §1) +
     re-clone + restore DB/env/RAG from Spaces + repoint reserved IP;
     *(b)* DB corruption → restore last-good encrypted snapshot. **Test the
     restore monthly** — an untested backup is not a backup. Define
     explicit **RTO/RPO** (a daily Spaces dump ⇒ RPO ≤ 24h today; tighten
     cadence if the data warrants).
- **Skip / defer:** Managed PostgreSQL with standby, cross-region read
  replicas, LB-fronted HA. These require the SQLite→Postgres app rewrite
  and only pay off at multi-node scale.

### Area 6 — Performance, scaling, supply chain
- **Right-sized next:** Add CI security stages that are cheap and
  host-agnostic — **Bandit/CodeQL** (SAST), dependency/SCA scan, secret
  scan, and **SBOM** (Syft/CycloneDX). Pin actions by SHA (also in §3).
- **Skip:** Valkey/Redis broker + Celery (app uses an in-memory job queue
  by design), PgBouncer pooling (no Postgres), CPU/RPS autoscaling
  (single Droplet), distroless container hardening (not containerized).

### Area 7 — Multi-agent coordination
- Agent 4 owns shared infra/config paths (`infra/**`,
  `.github/workflows/**`, deploy scripts, `Caddyfile.example`,
  `pedesk.service.example`, this doc). Merge **config/infra first**, then
  feature agents rebase. Keep parallel agents to burst, not default.

---

## 3. Secrets posture (replacing Key Vault) — current vs. options

- **Current (adequate for a small team):** `/opt/RCM/RCM_MC/.pedesk_prod.env`,
  `chmod 600`, git-ignored, read by `pedesk.service` via `EnvironmentFile`;
  CI's only secret is the SSH **deploy key** in GitHub Secrets. No DO PAT in
  the pipeline. This is a defensible posture and matches the runbooks.
- **Upgrade path (only if rotation/audit pressure rises):** **SOPS+age**
  (encrypted secrets committed to the repo, decrypted on the Droplet at
  deploy) or self-hosted **Vault**. The bootstrap secret (decrypt key) lives
  in GitHub Secrets + a root-only file on the box.
- **When Terraform lands (§1):** introduce a **scoped, scheduled-rotation DO
  PAT** as `DIGITALOCEAN_TOKEN`, plus `spaces_access_id`/`spaces_secret_key`
  for the Spaces state backend and backups. Use short-lived registry logins
  **only if** we ever introduce DOCR (we don't today).

---

## 4. Thresholds that change this plan

Stay on the single-Droplet/SQLite path until one of these trips:

- **Sustained CPU/mem > 70% or p99 latency breaches target** → first resize
  the Droplet (vertical); only then consider LB + second Droplet, which
  forces the SQLite→Managed-Postgres rewrite.
- **Concurrent-write contention on SQLite** (lock timeouts in logs) → that
  is the real signal to adopt **Managed PostgreSQL** (+ standby, PITR,
  PgBouncer) — an app-layer project, budgeted as such.
- **Regulatory pressure (HIPAA/audit) increases** → mandate encrypted
  **Volume** for data + Managed DB at rest, add cross-region read replica,
  shorten backup/restore-test cadence.
- **Zero-downtime becomes a hard SLO** → implement graceful reload (§3),
  then blue-green only if that's insufficient.
- **Team can't sustain OS-level ops** → move the web tier to **App
  Platform** (accept its networking constraints; note Tailscale→Ollama gets
  harder there).

---

## 5. Recommended sequence (right-sized)

1. **Backups + restore drill to Spaces** (Area 5) — closes the biggest real
   risk for a single-machine app holding confidential diligence data.
2. **Harden + Tailscale-only SSH + Cloud Firewall** (Area 2) and **pin
   actions by SHA + secret scan** (Area 3/6) — cheap, high-value.
3. **`do-agent` + alert policies** (Area 4) — free baseline observability.
4. **Terraform-capture the existing Droplet** with state in Spaces (Area 1)
   — makes the DR rebuild in step 1's runbook real, and is the point at
   which a scoped/rotated DO PAT is introduced.
5. **Graceful restart** (Area 3) — only if the deploy blip matters.

Everything beyond this (Managed PG/Valkey, LB/HA, self-hosted Prometheus
stack, DOCR/blue-green) is deferred behind the §4 triggers, not part of the
baseline DigitalOcean footprint for PEdesk.

---

## Caveats

- **No native DO OIDC** for the API as of June 2026 (one third-party vendor
  blog claims otherwise; uncorroborated by DO docs — don't rely on it).
- **PITR window is 7 days** for Managed PG; longer needs your own Spaces
  dumps — which is exactly the path §5 step 1 builds anyway.
- DO built-in Monitoring is **infra-only**, ~14-day retention — not APM or
  long-term log storage.
- Blue-green/backup scripts in the source research come from
  community/vendor tutorials; validate any borrowed script in staging.
- Several research recommendations (Managed PG/standby, Valkey, LB,
  Prometheus cluster, DOCR/blue-green) are **deliberately out of scope** for
  PEdesk's current single-machine/SQLite design — they are recorded here as
  the documented growth path, not the to-do list.
