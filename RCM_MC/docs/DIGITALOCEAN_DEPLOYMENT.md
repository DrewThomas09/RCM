# PEdesk on DigitalOcean — deployment guide

Host the PEdesk web app publicly on a DigitalOcean Droplet, with **Ollama
staying on the home Mac** and reached **privately over Tailscale**. Users
hit `https://pedesk.app`; they never touch Ollama, and port **11434 is never
exposed to the internet**.

## Architecture

```
   User browser
        │  https://pedesk.app
        ▼
   ┌──────────────────────────────────────────┐
   │  DigitalOcean Droplet (NYC2, Ubuntu 24.04)│
   │  Caddy :443  ──►  PEdesk :8080 (127.0.0.1)│
   └───────────────┬──────────────────────────┘
                   │  Tailscale (private mesh, encrypted)
                   ▼
   ┌──────────────────────────────────────────┐
   │  Home Mac  ──  Ollama :11434 (private)    │
   │  gemma4:e4b (chat) + nomic-embed-text     │
   └──────────────────────────────────────────┘
```

PEdesk runs only on the Droplet. Ollama runs only on the Mac. The Droplet
calls Ollama at the Mac's **Tailscale IP** — never a public address.

## Migration context

Moving off Azure-for-Students (credit exhausted, subscription disabled) to a
self-managed DigitalOcean Droplet. The home-Mac Ollama host (and its local
RAG workflow) is unchanged; only the *web app* moves to the cloud.

## Droplet details

- Public IPv4: **107.170.18.237**
- Name: `pedesk-prod` / `pedesk-web-01`
- Region: NYC2 · OS: Ubuntu 24.04 LTS x64
- Plan: Basic Premium Intel — 2 vCPU / 4 GB RAM / 120 GB disk

## DNS (Name.com, domain pedesk.app)

Point both names at the Droplet; remove the old Azure IP.

| Type | Host | Value |
|------|------|-------|
| A | `@` (pedesk.app) | `107.170.18.237` |
| A | `www` | `107.170.18.237` |

- **Delete** any A record still pointing at the old Azure IP `52.159.100.217`.
- Caddy needs these resolving before it can issue HTTPS certs. Check:
  `dig +short pedesk.app` → `107.170.18.237`.

## Step 1 — Mac: Ollama + Tailscale (no live-host restart needed)

On the home Mac (where Ollama already runs):

```bash
ollama list                      # confirm gemma4:e4b + nomic-embed-text
# Install Tailscale (https://tailscale.com/download) and sign in, then:
tailscale ip -4                  # note the Mac's Tailscale IP (100.x.y.z)
```

Make Ollama reachable on the Tailscale interface (not the public internet).
By default Ollama binds loopback; to accept LAN/Tailscale connections set
`OLLAMA_HOST=0.0.0.0` for the Ollama process **and rely on Tailscale + the
Mac firewall to keep it private** — do NOT port-forward 11434 on your router.
Keep the Mac awake while it serves (`caffeinate -dimsu`).

> Only the Tailscale network should be able to reach 11434. Never expose it
> publicly; never port-forward it.

## Step 2 — Droplet: bootstrap

SSH in as root. (During `apt upgrade`, keeping the currently-installed
`sshd_config` — as you did — is the safe choice; it avoids changing SSH and
locking yourself out.) Then:

```bash
git clone https://github.com/DrewThomas09/RCM.git /opt/RCM
cd /opt/RCM/RCM_MC
bash scripts/do_bootstrap_server.sh            # + --with-caddy to install Caddy too
tailscale up                                   # authenticate this node
```

`do_bootstrap_server.sh` installs git/python3/venv/pip/curl/ufw + Tailscale
(+ optional Caddy), and stages ufw rules for SSH/80/443 (it does **not**
auto-enable ufw, and never opens 11434).

Create the Python venv + install PEdesk:

```bash
cd /opt/RCM/RCM_MC
python3 -m venv .venv
. .venv/bin/activate
pip install -e .          # or: pip install -r requirements.txt (per repo)
```

## Step 3 — Env file (`.pedesk_prod.env`) — secret, never committed

Create it by hand on the Droplet (it is git-ignored):

```bash
cd /opt/RCM/RCM_MC
cat > .pedesk_prod.env <<'EOF'
PEDESK_GUIDE_OLLAMA_ENABLED=true
PEDESK_GUIDE_RAG_ENABLED=true
PEDESK_GUIDE_OLLAMA_BASE_URL=http://<MAC_TAILSCALE_IP>:11434
PEDESK_GUIDE_OLLAMA_MODEL=gemma4:e4b
PEDESK_GUIDE_RAG_EMBED_MODEL=nomic-embed-text
PEDESK_GUIDE_OLLAMA_TIMEOUT_SECONDS=60
# Basic Auth (HTTP Basic) — set a strong shared credential. Generate the
# password yourself; do not paste it into chat/logs:
#   python3 -c "import secrets; print('pedesk:'+secrets.token_urlsafe(18))"
RCM_MC_AUTH=<USER>:<STRONG_PASSWORD>
EOF
chmod 600 .pedesk_prod.env
```

Fill manually: `<MAC_TAILSCALE_IP>` (from `tailscale ip -4` on the Mac) and
`RCM_MC_AUTH`. **Never commit this file. Never print its contents.**

## Step 4 — Build the RAG index (one-time, + after context edits)

```bash
cd /opt/RCM/RCM_MC
. .venv/bin/activate
PEDESK_GUIDE_RAG_ENABLED=true ./scripts/build_guide_rag_index.sh
```

## Step 5 — Preflight

```bash
bash scripts/do_preflight.sh        # expect: RESULT: READY
```

Verifies the env file + permissions, Tailscale, the private Ollama path
(`/api/tags`), both models, the RAG index, and that `RCM_MC_AUTH` is set —
printing **no** secret values.

## Step 6 — Manual run (smoke test)

```bash
bash scripts/do_run_pedesk.sh       # binds 127.0.0.1:8080 (behind Caddy)
# direct/no-Caddy test (needs RCM_MC_AUTH):
#   PEDESK_BIND_HOST=0.0.0.0 bash scripts/do_run_pedesk.sh
curl -u "$USER:$PASS" http://127.0.0.1:8080/api/guide/ollama-health   # ai_ready:true
```

## Step 7 — Durable service (systemd)

```bash
sudo cp docs/pedesk.service.example /etc/systemd/system/pedesk.service
# edit User=/paths if needed
sudo systemctl daemon-reload
sudo systemctl enable --now pedesk
sudo systemctl status pedesk
journalctl -u pedesk -f
```

The unit reads `.pedesk_prod.env` via `EnvironmentFile`, binds 127.0.0.1:8080,
and restarts on failure.

## Step 8 — HTTPS (Caddy)

```bash
sudo cp docs/Caddyfile.example /etc/caddy/Caddyfile
sudo systemctl reload caddy
# Caddy auto-issues Let's Encrypt certs for pedesk.app + www.pedesk.app
```

Then enable the firewall deliberately (SSH must stay allowed):

```bash
sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status            # 22, 80, 443 only — NOT 11434
```

Visit `https://pedesk.app`, log in with the Basic Auth credential, open the
**Guide** sidebar → "AI Q&A ready · RAG enabled".

## Rollback plan

- **App regression:** `cd /opt/RCM && git fetch && git checkout <last-good-sha>`,
  rebuild RAG if context changed, `sudo systemctl restart pedesk`.
- **Bad deploy entirely:** `sudo systemctl stop pedesk` (site returns 502 via
  Caddy) until fixed. DNS can also be repointed at Name.com if you stand up a
  replacement.
- **HTTPS issues:** `sudo systemctl stop caddy` to drop back to the systemd
  app on 127.0.0.1; fix DNS/certs, then reload Caddy.
- The Mac/Ollama side is independent — rolling back the Droplet never touches it.

## Troubleshooting

| Symptom | Check |
|---|---|
| Guide shows "not fully configured" | `bash scripts/do_preflight.sh` — names the cause |
| Can't reach Ollama | `tailscale status` on both ends; `curl http://<MAC_TS_IP>:11434/api/tags` from the Droplet; Mac awake + Ollama running with `OLLAMA_HOST=0.0.0.0` |
| Model missing | pull on the **Mac**: `ollama pull gemma4:e4b` / `ollama pull nomic-embed-text` |
| HTTPS cert fails | DNS not resolving yet (`dig +short pedesk.app`), or 80/443 blocked by ufw |
| 502 from Caddy | PEdesk not running — `systemctl status pedesk` / `journalctl -u pedesk` |
| Slow answers | expected on a remote local model; raise `PEDESK_GUIDE_OLLAMA_TIMEOUT_SECONDS` |
| Old Azure IP still served | delete the `52.159.100.217` A records at Name.com; wait for TTL |

## Hard rules (do not violate)

- **Never expose Ollama / port 11434 publicly.** Droplet→Mac is Tailscale-only.
- **Never commit** `.pedesk_prod.env` (or `.pedesk_host_auth.env`); both are
  git-ignored. Never print their contents.
- DigitalOcean hosts the **PEdesk web app only**; the **Mac hosts Ollama**.
- No cloud/external LLMs; the Guide stays read-only (no uploads, memory,
  actions, exports, or mutations).
