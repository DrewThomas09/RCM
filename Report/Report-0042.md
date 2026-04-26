# Report 0042: Data-Flow Trace — `DOMAIN` env var

## Scope

Traces the `DOMAIN` environment variable end-to-end on `origin/main` at commit `f3f7e7f`. Path: host shell → `vm_setup.sh` → docker-compose env interpolation → Caddy container → Caddyfile templating → Let's Encrypt cert provisioning → HTTPS request termination → reverse-proxy to origin.

Prior reports reviewed: 0038-0041.

## Findings

### Stage 0 — Host shell

Operator sets `DOMAIN=diligence.example.com` (or similar) in their shell. Per Report 0026 the GitHub Actions deploy.yml runs:

```bash
docker compose -f deploy/docker-compose.yml up -d --build
```

But this command does NOT pass `--profile tls`, so Caddy may not start in CI-driven deploys (Report 0041 MR334).

### Stage 1 — `vm_setup.sh:23` reads `DOMAIN`

```bash
DOMAIN="${3:-}"
```

(line 23 — third positional arg, defaults to empty)

### Stage 2 — `vm_setup.sh:68-70` exports DOMAIN if non-empty

```bash
if [ -n "$DOMAIN" ]; then
    echo "    DOMAIN=$DOMAIN set — bringing up Caddy TLS sidecar"
    export DOMAIN
fi
```

So `DOMAIN` enters the docker-compose process env only when the operator passes the third arg.

### Stage 3 — `docker-compose.yml:62` consumes DOMAIN with fail-fast

```yaml
environment:
  - DOMAIN=${DOMAIN:?set DOMAIN=your.domain.com in host env before compose up}
```

The `${VAR:?error}` syntax **fails compose-up if DOMAIN is unset**, with the embedded message. This is on the **caddy** service. Per Report 0041 the caddy service is gated behind `profiles: [tls]`.

### Stage 4 — Caddy container starts, reads DOMAIN as env var

Inside the running caddy container, `$DOMAIN` is now set to the host shell value.

### Stage 5 — Caddyfile templating

`RCM_MC/deploy/Caddyfile:25`:

```
{$DOMAIN} {
    ...
}
```

Caddy uses `{$DOMAIN}` as the **environment variable substitution** syntax (not `${DOMAIN}`). At Caddy's startup, this expands to the container's DOMAIN env value, producing a real Caddyfile site block keyed by the actual domain name.

### Stage 6 — Caddy provisions Let's Encrypt cert

Caddy 2.x auto-detects HTTPS-eligible site blocks (those with bare domains, not `:port`) and triggers ACME HTTP-01 or TLS-ALPN-01 challenge against the domain. **Requires:**

1. The DNS A-record for `$DOMAIN` points at the VM's public IP.
2. Port 80 reachable from the public internet (for HTTP-01 challenge).
3. Let's Encrypt rate limit (5 issuances/week/domain) not exceeded.

`caddy_data` volume (per Report 0041) persists the issued cert across restarts.

### Stage 7 — Cert installed; HTTPS termination

Caddy now serves HTTPS for `$DOMAIN` with the LE-issued cert. Listens on `:443` (and `:443/udp` for HTTP/3 per docker-compose port mapping).

### Stage 8 — Reverse proxy to origin

The Caddyfile (line 25 onwards, not fully read this iteration) likely contains a `reverse_proxy rcm-mc:8080` directive. Caddy resolves `rcm-mc` via Docker's internal network DNS; forwards request to the origin container on port 8080.

### Stage 9 — Origin sees `X-Forwarded-Proto: https`

Per Caddyfile's standard reverse_proxy behavior. Origin server (`server.py`) detects HTTPS and emits HSTS + Secure cookies.

### Stage 10 — Test verification

`tests/test_azure_deploy.py:97-98` asserts:

```python
self.assertIn("{$DOMAIN}", self.src,
              msg="Caddyfile must use {$DOMAIN} so compose ...")
```

**The test pins the templating syntax** — protects against accidental rewriting to `${DOMAIN}` (compose syntax) which would not work inside Caddy's runtime.

### Trace summary

```
host shell:    export DOMAIN=diligence.example.com
                      │
                      ▼
   Stage 1   vm_setup.sh:23  DOMAIN="${3:-}"
                      ▼
   Stage 2   vm_setup.sh:68-70  if [ -n "$DOMAIN" ]; then export DOMAIN
                      ▼
   Stage 3   docker-compose.yml:62  DOMAIN=${DOMAIN:?...}  (fail-fast)
                      ▼
   Stage 4   caddy container env: $DOMAIN
                      ▼
   Stage 5   Caddyfile:25  {$DOMAIN} {  (env-var substitution)
                      ▼
   Stage 6   Caddy startup → ACME challenge → LE-issued cert
                      ▼
   Stage 7   HTTPS bind on :443 (+:443/udp for HTTP/3)
                      ▼
   Stage 8   Caddy → reverse_proxy rcm-mc:8080
                      ▼
   Stage 9   Origin server.py reads X-Forwarded-Proto: https
                      ▼
   Stage 10  tests/test_azure_deploy.py:97-98  pins templating syntax
```

### Sister flows

- `vm_setup.sh` without DOMAIN arg: skips Stage 2-9; only origin starts on port 8080 with no TLS.
- `docker compose up rcm-mc` (no `--profile tls`): same — only origin runs.
- Local dev: developers can edit Caddyfile to use `:80 { reverse_proxy ... }` per the Caddyfile comment at lines 22-23.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR341** | **Caddy profiles + deploy.yml asymmetry** (cross-link Report 0041 MR334) | deploy.yml `docker compose up -d --build` does NOT pass `--profile tls`. **Production deploys via the workflow may run HTTP-only.** | **Critical** |
| **MR342** | **`{$DOMAIN}` vs `${DOMAIN}` syntax confusion** | Caddyfile uses `{$DOMAIN}` (Caddy native); compose uses `${DOMAIN}` (compose interpolation). A future contributor swapping syntaxes breaks one or the other. **`tests/test_azure_deploy.py:97-98` pins the Caddyfile syntax — preserves it.** | Medium |
| **MR343** | **DOMAIN must resolve via DNS BEFORE first compose-up** | Otherwise LE challenge fails; Caddy retries in background but the deploy is HTTP-only until DNS propagates. | Medium |
| **MR344** | **No `RCM_MC_AUTH` or `ANTHROPIC_API_KEY` test pinning** | `test_azure_deploy.py` tests the Caddyfile syntax. Need similar tests for env-var pass-through. | Medium |
| **MR345** | **Stage 3's fail-fast only fires if Caddy profile is enabled** | If operator omits `--profile tls`, the fail-fast is silenced. **Stack starts HTTP-only without surfacing the missing-DOMAIN.** | **High** |
| **MR346** | **Let's Encrypt rate limit (5 issuances/week/domain)** is real | If `caddy_data` volume is recreated (e.g. accidental `docker compose down -v`), every restart re-issues. **5 deploys in 7 days = locked out.** Volume persistence per Report 0041 prevents this. | Medium |
| **MR347** | **Caddy 2-alpine image floats** (Report 0041 MR333) | A future Caddy 2.x release could change `{$DOMAIN}` semantics. Pinning to digest mitigates. | Low |

## Dependencies

- **Incoming:** operator (host shell), `vm_setup.sh`, deploy.yml workflow, `caddy:2-alpine` image.
- **Outgoing:** DNS (A-record), Let's Encrypt service (ACME), Docker network DNS.

## Open questions / Unknowns

- **Q1.** Does deploy.yml actually pass `--profile tls`? Report 0026 read shows it does NOT (just `docker compose up -d --build`). **MR341 confirmed.**
- **Q2.** What's in the Caddyfile after line 25? The `reverse_proxy` block is referenced but not read this iteration.
- **Q3.** Does Caddy emit any logs that would alert an operator that LE challenge failed (e.g. DNS not propagated yet)?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0043** | **Read full Caddyfile** end-to-end (lines 25-end) | Resolves Q2. |
| **0044** | **Read deploy.yml's actual compose-up command** to confirm MR341 | Resolves Q1. |
| **0045** | **Cross-check `tests/test_azure_deploy.py`** end-to-end | Companion to MR342 + MR344. |

---

Report/Report-0042.md written. Next iteration should: read the full Caddyfile (lines 25 to end) and document the reverse-proxy block — closes Q2 and tells us what HTTP→HTTPS / HSTS / X-Forwarded-Proto headers are actually injected at the TLS edge.

