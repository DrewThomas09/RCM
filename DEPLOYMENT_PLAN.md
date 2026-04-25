# DEPLOYMENT_PLAN.md

Private, password-gated web-app deployment of SeekingChartis / RCM-MC on **Azure VM**. Assessment + plan — no code written yet.

---

## Executive summary

**Use the Azure VM deployment infrastructure that already exists in `RCM_MC/deploy/`.** Don't write a Flask app, don't move to Heroku, don't build a `web/` adapter directory. The repo shipped Azure VM deploy infrastructure at commit `0b5c07c feat(deploy): Azure VM deployment infrastructure` and it's on `main` today.

**What actually needs doing is small**: one real bug to fix in the Dockerfile, four small enhancements (PHI banner, `/healthz` alias, `PYTHONUNBUFFERED`, stdout logging), one startup gate (release-phase check), and one post-deploy smoke test. Plus HTTPS via Caddy if the app will have a real domain.

Prior draft of this plan assumed Heroku and proposed a 110-LOC `web/` adapter to work around Heroku's ephemeral filesystem + 30-sec request timeout + lack of BAA. All three problems go away on Azure VM. The Azure path saves roughly a week of adapter code and gives you a deployment that actually fits the app's design (single-process job queue, SQLite with volume mount, no timeout on Deal MC at 3,000 trials).

---

## Step 1 — What exists (verified against source)

### Existing deployment infrastructure (`RCM_MC/deploy/`)

Four files, shipped and on `main`:

| File | LOC | What it does |
|------|-----|--------------|
| `Dockerfile` | 24 | `python:3.14-slim`; installs gcc/g++; `pip install .` from `pyproject.toml`; creates `/data` for SQLite; exposes 8080; healthcheck hits `http://localhost:8080/health`; `ENTRYPOINT python -m rcm_mc serve` |
| `docker-compose.yml` | 20 | Port forward `8080:8080`; volume mount `/data/rcm:/data` for SQLite persistence across restarts; env passthrough (`RCM_MC_DB`, `RCM_MC_AUTH`, `ANTHROPIC_API_KEY`); `restart: unless-stopped`; 50 MB × 5 file log rotation |
| `rcm-mc.service` | 18 | systemd unit (`oneshot + RemainAfterExit`); runs `docker compose up -d --build` on boot; `Restart=on-failure`; `Wants=network-online.target` |
| `vm_setup.sh` | 60 | 1-command VM bootstrap. Installs Docker, clones the repo, builds + starts the compose stack, waits for `/health` (60 s), creates the admin user via `python -m rcm_mc portfolio users create`, prints the public IP + firewall hint |

### Inside the app (verified)

- **`rcm_mc/server.py`** — 15,327 LOC HTTP app, 88+ routes, stdlib-based auth (`hashlib.scrypt` + session cookies + CSRF), rate limiting, unified audit log
- **`/health` route** exists at `server.py:3564` ✓
- **`rcm-mc serve` CLI entry** at `cli.py:1301` → `server.serve_main` ✓
- **`RCM_MC_AUTH` env-var fallback** at `server.py:15196` — single-user or `user:pass` credentials via env ✓
- **`chartis_shell()` render wrapper** — single function every page passes through; ideal insertion point for the PHI banner ✓
- **`rcm_mc.infra.migrations`** — idempotent schema migration registry, auto-runs on startup ✓
- **`rcm_mc.infra.job_queue`** — single-process in-memory job registry for long-running analyses (no timeout issues on Azure; no Redis needed)

### Bug found during verification

**Container binds to 127.0.0.1 by default.** `server.py` CLI parser sets `--host 127.0.0.1` as default. The Dockerfile's `CMD` line is `["--db", "/data/rcm_mc.db", "--port", "8080"]` — no `--host` override. Inside the container this listens on loopback only. Docker's `-p 8080:8080` port forward requires the container process to bind `0.0.0.0`. Result: the Docker healthcheck works (internal `curl localhost:8080/health` from inside the container succeeds), but **external access from the Azure VM to port 8080 silently fails.** One-line fix in the Dockerfile CMD.

---

## Step 2 — Browser-viewable outputs (same as before)

Already all routed through `server.py`. Five categories:

| Output | Served by | Example routes |
|--------|-----------|-----|
| Partner memos (IC packet, IC memo, partner review) | `ui/ic_memo_page.py`, `ui/ic_packet_page.py`, `ui/chartis/ic_packet_page.py`, `ui/chartis/partner_review_page.py` | `/diligence/ic-packet`, `/deal/<id>/ic-packet`, `/deal/<id>/partner-review` |
| Metric dashboards (workbench, home, command center, portfolio overview) | `ui/analysis_workbench.py`, `ui/home_v2.py`, `ui/command_center.py`, `ui/portfolio_overview.py` | `/analysis/<deal_id>`, `/home`, `/portfolio` |
| Charts | Zero-dep SVG via `diligence/deal_mc/charts.py`; matplotlib inline in `reports/html_report.py` | Inline in above pages |
| Module documentation | 34 diligence sub-module READMEs + 29 backend sub-package READMEs (shipped in PR #12) + FILE_MAP.md + ARCHITECTURE_MAP.md | Currently not routed; see §9 |
| Corpus browser | `ui/data_public/*_page.py` — 173 pages | `/<topic>` per topic (e.g. `/aco-economics`, `/sponsor-league`) |

**Nothing new needs to be built for rendering.** Every page is already a handler in `server.py`.

---

## Step 3 — Analysis entry points to trigger from the browser

All already exposed as routes. In order of likely user-trigger frequency:

| Entry point | Purpose | Existing route |
|-------------|---------|----------------|
| `analysis.packet_builder.build_analysis_packet(deal_id, ...)` | 12-step master orchestrator producing the canonical `DealAnalysisPacket` | `POST /api/analysis/<deal_id>/rebuild` |
| `diligence.thesis_pipeline.run_thesis_pipeline(input)` | 19-step diligence chain | `POST /diligence/thesis-pipeline` |
| `diligence.deal_mc.engine.run_deal_mc(scenario, n_runs=3000)` | Headline MC — MOIC/IRR cones | `POST /api/analysis/<deal_id>/simulate` |
| `diligence.covenant_lab.simulator.run_covenant_stress(...)` | 500 lognormal paths × 20 quarters × 4 covenants | `POST /diligence/covenant-stress` |
| `diligence.payer_stress.contract_simulator.run_payer_stress(...)` | 500 paths × horizon × 19 payers | `POST /diligence/payer-stress` |
| `diligence.bear_case.generator.generate_bear_case_from_pipeline(report)` | IC memo bear-case synthesizer | `POST /diligence/bear-case` |
| `data.data_refresh.refresh_source(source_name)` | CMS / IRS 990 / Care Compare refresh | `POST /api/data/refresh/<source>` (rate-limited) |

---

## Step 4 — Timing analysis on Azure VM

**Azure VM has no platform-imposed request timeout.** Docker / nginx / Caddy will happily hold a request open for the 2–5 minutes a long analysis takes. The 30-sec budget discussion from the Heroku draft of this plan is **moot on Azure**.

However, user experience still matters. A 3-minute synchronous request blocks the browser tab. Two patterns available:

### Pattern A — synchronous (default)

For analyses under ~10 s, return the rendered page directly. Browser waits, user sees result immediately. Works for:
- HCRIS X-Ray (7 ms – 250 ms)
- Bear Case generator (~100 ms)
- Payer Stress (~2–5 s on fixture)
- Bridge Auto-Auditor (~4 s)
- Covenant Lab (~3–7 s)

### Pattern B — async via existing `infra/job_queue`

For longer analyses, use the in-process job queue already in the codebase:
1. Browser POSTs parameters → handler enqueues a job, returns 202 + job_id
2. Browser polls `GET /api/jobs/<id>` every 2 s
3. On completion, handler returns the result URL

Good candidates:
- Deal MC at 3,000 trials (often >30 s on real CCD)
- CMS data refresh (30 s to 10 minutes per source)
- `packet_builder` full run on real CCD

**No refactor needed.** The existing job queue already does this. Single-process (web + worker in same dyno / container) is the design.

---

## Step 5 — What to add / fix

Seven items. Total new code: **~40 LOC of app changes + ~80 LOC of deploy-side config**. No framework migration, no new package structure.

### 5.1 — Fix the `--host 0.0.0.0` bind bug (**MUST**)

In `RCM_MC/deploy/Dockerfile`:
```diff
-CMD ["--db", "/data/rcm_mc.db", "--port", "8080"]
+CMD ["--db", "/data/rcm_mc.db", "--host", "0.0.0.0", "--port", "8080"]
```
Without this, external access to the VM's port 8080 never succeeds even though the container looks healthy. Current state: shipped but not externally reachable; healthcheck green because it's container-internal.

### 5.2 — Add `PYTHONUNBUFFERED=1` (stdout logging)

In `RCM_MC/deploy/Dockerfile`, before `ENTRYPOINT`:
```diff
+ENV PYTHONUNBUFFERED=1
+ENV PYTHONDONTWRITEBYTECODE=1
```
Makes Python flush stdout/stderr to Docker's log driver in real time. Without it, `docker logs` can lag minutes behind reality; startup errors may never appear until buffer fills. `PYTHONDONTWRITEBYTECODE` is a bonus — keeps the container image clean (no `.pyc` write churn under read-only mounts).

### 5.3 — Add `/healthz` alias for `/health`

In `rcm_mc/server.py` near the existing `/health` handler (line 3564):
```python
if path in ("/health", "/healthz"):
    self._send_plain(200, "ok")
```

`/healthz` is the widely-used convention (Kubernetes, GCP load balancers, etc.). `/health` was first, don't break it. Both pointing at the same handler = zero risk, catches either probe pattern.

### 5.4 — PHI banner (visible commitment if no-PHI deployment)

In `rcm_mc/ui/_chartis_kit.py::chartis_shell()`, inject a banner above the page body when env var is set:
```python
def chartis_shell(..., body, ...):
    phi_mode = os.environ.get("RCM_MC_PHI_MODE", "").lower()
    banner = ""
    if phi_mode == "disallowed":
        banner = '<div class="phi-banner">No PHI permitted on this instance — public data + corpus analytics only.</div>'
    elif phi_mode == "restricted":
        banner = '<div class="phi-banner warning">PHI-eligible deployment — audit-logged; do not export outside BAA scope.</div>'
    return f"<html>...{banner}{body}...</html>"
```

`docker-compose.yml` sets `RCM_MC_PHI_MODE=disallowed` by default. The banner is on every page rendered through `chartis_shell` — auditable, screenshot-able, visible to colleagues when you share access.

### 5.5 — Release-phase startup check (fail-fast)

Add a pre-startup step to `RCM_MC/deploy/docker-compose.yml` via `depends_on` + a small one-shot service that runs migrations + integrity checks, exiting non-zero on failure:

```yaml
services:
  migrate:
    build: ...
    command: ["python", "-c", "from rcm_mc.infra.migrations import run_all; from rcm_mc.infra.consistency_check import verify_schema; run_all('/data/rcm_mc.db'); verify_schema('/data/rcm_mc.db')"]
    volumes: [/data/rcm:/data]

  rcm-mc:
    depends_on:
      migrate:
        condition: service_completed_successfully
    # ...
```

On boot, `migrate` runs first. If schema is broken or corrupt, the main service never starts — Docker logs show the failure clearly. Uses the existing `rcm_mc.infra.migrations` + `rcm_mc.infra.consistency_check` modules, which are designed for this.

### 5.6 — Smoke test (`RCM_MC/deploy/smoke_test.sh`)

30 lines, runs after `docker compose up`:
```bash
#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-http://localhost:8080}"

# 1. Healthcheck
curl -sf "$BASE/healthz" || { echo "FAIL: /healthz"; exit 1; }

# 2. Login flow (check auth returns 302 to /home)
CSRF=$(curl -sc /tmp/cookies "$BASE/login" | grep -oE 'name="csrf"[^>]*value="[^"]+"' | cut -d'"' -f4)
curl -sb /tmp/cookies -sc /tmp/cookies -o /dev/null -w "%{http_code}" \
    -d "username=${ADMIN_USER}&password=${ADMIN_PASS}&csrf=${CSRF}" \
    "$BASE/login" | grep -q "302" || { echo "FAIL: login"; exit 1; }

# 3. Home page returns 200
curl -sb /tmp/cookies -o /dev/null -w "%{http_code}" "$BASE/home" \
    | grep -q "200" || { echo "FAIL: /home"; exit 1; }

# 4. Thesis pipeline fixture run returns 200 (smoke-check the analysis surface)
curl -sb /tmp/cookies -o /dev/null -w "%{http_code}" \
    "$BASE/diligence/thesis-pipeline?dataset=hospital_04_mixed_payer" \
    | grep -q "200" || { echo "FAIL: thesis pipeline"; exit 1; }

echo "OK: all smoke tests passed"
```

Runs inside `vm_setup.sh` after the stack comes up. Also callable from CI / cron / post-deploy.

### 5.7 — HTTPS via Caddy (optional, recommended for real domain)

Add a `caddy` service to `docker-compose.yml`:
```yaml
  caddy:
    image: caddy:2-alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on: [rcm-mc]
    restart: unless-stopped

volumes:
  caddy_data:
  caddy_config:
```

With a 6-line `Caddyfile`:
```
your.domain.com {
    reverse_proxy rcm-mc:8080
}
```

Caddy auto-provisions + renews Let's Encrypt certs on the first request. The VM's firewall opens 80+443 instead of 8080. Zero manual cert handling.

If no custom domain is needed (IP-only access for solo use), skip this — the plain 8080 path works for private internal access.

---

## Step 6 — Azure-specific guidance

### VM sizing

| Plan | Size | vCPU | RAM | Cost (pay-as-you-go) | Fit |
|------|------|------|-----|----------------------|-----|
| **B1s** | Burstable | 1 | 1 GB | ~$8/mo (stoppable) | Minimal — works for corpus browsing, struggles on Deal MC at 3,000 trials |
| **B2s** | Burstable | 2 | 4 GB | ~$30/mo | **Recommended.** Comfortable for all analyses; can run Deal MC synchronously. |
| **B2ms** | Burstable | 2 | 8 GB | ~$60/mo | Overkill unless you grow the corpus meaningfully. |

Use **B2s** unless cost-sensitive. B1s will OOM-kill Python on a 3,000-trial Deal MC with large fixtures.

### Storage

SQLite file lives at `/data/rcm/rcm_mc.db` on the Azure managed disk (standard SSD is fine). Daily Azure VM snapshots via Azure Backup give you point-in-time recovery. Or run the existing `rcm_mc.infra.backup.create_backup()` on a cron to a separate Azure Blob Storage container.

### Firewall / NSG

Azure Network Security Group rules:
- **Inbound**: 22 (SSH, your IP only) + 443 (HTTPS, 0.0.0.0/0) + 80 (HTTP, 0.0.0.0/0, Caddy needs it for cert renewal)
- **Inbound deny**: 8080 (keep Docker port internal; only Caddy reaches it)
- **Outbound**: anywhere (for CMS data refresh + Let's Encrypt)

### Stop when idle

Azure VMs can be deallocated when not in use → you stop paying for compute (disk still costs ~$5/mo). Use Azure Automation's auto-shutdown feature to stop nightly + start on schedule. Solo users: stop manually when not needed.

### BAA (HIPAA)

If you need BAA coverage: Azure has a BAA template, VMs deployed under a compliant subscription are BAA-eligible. This is out of scope for this plan to configure — but the Azure path doesn't foreclose it, the way Heroku Standard does.

---

## Step 7 — Auth + user management

**Already solved.** `rcm_mc/auth/` has scrypt password hashing, session cookies, CSRF, and RBAC (6 role tiers: `ADMIN > PARTNER > VP > ASSOCIATE > ANALYST > VIEWER`).

The existing `vm_setup.sh` creates the admin user via:
```bash
docker compose exec rcm-mc \
    python -m rcm_mc portfolio users create \
    --username "$ADMIN_USER" --password "$ADMIN_PASS" --role admin
```

Additional users created via the admin UI after first login, or by adding more lines to `vm_setup.sh`.

Session TTL defaults to 24 h; configurable via existing auth module.

---

## Step 8 — Risks + mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| **127.0.0.1 bind bug** (already in main) | Certain — will fail on first deploy | Fix per §5.1 before first deploy. |
| VM patched out-of-band + reboots mid-analysis | Low | Unattended-upgrades off by default on Ubuntu Azure; schedule maintenance windows manually. |
| SQLite file corrupted by abrupt container kill | Low with `busy_timeout=5000` + Docker's SIGTERM→SIGKILL 10 s grace | Nightly Azure Backup snapshot or cron-driven `infra.backup.create_backup()`. |
| Deal MC OOMs on B1s | High at 3,000 trials | Use B2s, or lower `n_runs` default for web-triggered runs. |
| Let's Encrypt rate limit on repeated deploys | Low but real (5 certs/week per domain) | Caddy uses `/data` volume for persistent cert storage → survives container rebuilds. |
| Someone uploads PHI despite banner | Operational, not technical | §5.4 banner is the visible commitment; existing `rcm_mc/compliance/phi_scanner.py` can run in CI against committed artifacts; audit log via `rcm_mc/compliance/audit_chain.py` gives cryptographic proof of access. |
| Public GitHub repo exposes corpus data | Depends on repo visibility | Repo is `DrewThomas09/RCM` (already public per `README.md` and PR links); no seller PHI in corpus; all seed deals sourced from public filings. Re-audit `data_public/extended_seed_*.py` annually if policy changes. |
| SSH key lost / rotated staff | Low | Azure Bastion or manual key rotation via VM settings. |

---

## Step 9 — Recommended follow-up: serve the documentation

Not strictly required for MVP, but high-value:
- FILE_MAP.md, ARCHITECTURE_MAP.md, and every per-package README currently live on disk only
- Adding a `/docs/<path>` static-markdown route would let users browse them in the deployed app
- ~30 LOC in `server.py`, rendered via existing `ui/text_to_html.py`

Skip for MVP; add in v1.1 if anyone asks.

---

## Step 10 — Proposed Prompt 2

After you approve this revised plan, Prompt 2 should be:

> Apply the seven changes from §5 of `DEPLOYMENT_PLAN.md` to the existing Azure deploy infrastructure:
> 1. Fix the `--host 0.0.0.0` bind bug in `RCM_MC/deploy/Dockerfile`
> 2. Add `PYTHONUNBUFFERED=1` + `PYTHONDONTWRITEBYTECODE=1` to the Dockerfile
> 3. Add a `/healthz` alias to `rcm_mc/server.py` routing to the same handler as `/health`
> 4. Add a PHI-banner hook in `rcm_mc/ui/_chartis_kit.py::chartis_shell()` driven by the `RCM_MC_PHI_MODE` env var (default `disallowed`)
> 5. Split `docker-compose.yml` into a `migrate` one-shot service + the main `rcm-mc` service, with `depends_on: service_completed_successfully`
> 6. Write `RCM_MC/deploy/smoke_test.sh` per the sketch in §5.6 and wire it into the tail of `vm_setup.sh`
> 7. Add the optional Caddy service + `Caddyfile` to `docker-compose.yml` (only wire in if a domain is configured; otherwise leave commented-out)
>
> Don't write new routes, don't refactor `server.py`, don't add new runtime deps. Include tests for the `/healthz` alias and the `chartis_shell` banner behavior.

Prompt 3 would be the deploy runbook: `az vm create ...`, SSH in, `sudo bash deploy/vm_setup.sh`, verify `/healthz` via public IP, set DNS, trigger the smoke test.

---

## Summary table

| Question | Answer |
|---------|--------|
| Do I need Flask or FastAPI? | **No.** `rcm_mc/server.py` is a 15K-LOC HTTP app. Use it. |
| Do I need a `web/` adapter directory? | **No.** Heroku-only concept; Azure VM deploys via the existing Docker stack. |
| Do I need background workers / Redis? | **No.** In-process job queue in `infra/job_queue.py` works on a single VM. |
| What's actually broken? | One line in Dockerfile `CMD` — missing `--host 0.0.0.0`. |
| What needs adding? | 6 small items: `PYTHONUNBUFFERED`, `/healthz` alias, PHI banner, release-phase gate, smoke test, optional Caddy. |
| How much new code? | ~40 LOC app changes + ~80 LOC deploy config = **~120 LOC total, zero new runtime deps**. |
| VM size? | **B2s** ($30/mo) for comfort on Deal MC; B1s ($8) if cost-sensitive. |
| HIPAA/BAA path? | Azure supports BAA on VMs in compliant subscriptions. This plan doesn't configure that; flag if you need it. |
| PHI posture for this deployment? | Set `RCM_MC_PHI_MODE=disallowed` + banner on every page (§5.4). If PHI will ever flow, switch to `restricted` + apply BAA procedures separately. |

**Ready for Prompt 2?**
