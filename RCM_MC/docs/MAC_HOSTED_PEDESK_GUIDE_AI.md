# Mac-hosted PEdesk Guide AI (local Ollama + RAG)

Run PEdesk's Guide AI entirely on this Mac: PEdesk + local Ollama + local
RAG, no cloud, single-user. When configured, the Guide sidebar shows
**"AI Q&A ready · RAG enabled"** and the Ask box is active.

Everything is **local and read-only**: the Guide explains pages, metrics,
data sources, and limitations. No uploads, memory, actions, exports,
mutations, or external/cloud LLMs.

## 1. Install + pull models (one-time)

Install Ollama (https://ollama.com), then:

```bash
ollama pull gemma4:e4b          # chat model (answers)
ollama pull nomic-embed-text    # embedding model (RAG retrieval)
ollama list                     # confirm both are present
```

Ollama must be running (the Ollama.app menubar icon, or `ollama serve`).

## 2. Build the local RAG index (one-time, and after context edits)

```bash
PEDESK_GUIDE_RAG_ENABLED=true ./scripts/build_guide_rag_index.sh
```

The index is a local SQLite file (`.pedesk_guide_rag.sqlite3`, gitignored)
covering only in-repo Guide context — page contexts, the metric and
data-source registries, the read-only policy, and curated docs. **No user
documents are indexed.**

## 3. Preflight (verify readiness)

```bash
PEDESK_GUIDE_RAG_ENABLED=true ./scripts/check_guide_rag.sh
PEDESK_GUIDE_OLLAMA_ENABLED=true PEDESK_GUIDE_RAG_ENABLED=true \
  python -m rcm_mc.assistant.rag.preflight_guide_ai      # expect: RESULT: READY
```

## 4. Run PEdesk in full AI mode

```bash
./scripts/run_mac_hosted_guide_ai.sh            # serves on port 8080
# or choose a port:
./scripts/run_mac_hosted_guide_ai.sh --port 9000
```

This pins the Mac-local env (Ollama + RAG enabled, `gemma4:e4b`,
`nomic-embed-text`, base `http://127.0.0.1:11434`, 45s timeout), runs a
preflight, then starts the server.

## 5. Confirm + use

```bash
curl http://127.0.0.1:8080/api/guide/ollama-health
# expect: ai_ready:true, ollama_reachable:true, chat/embed model installed,
#         rag_enabled:true, rag_index_exists:true, rag_chunk_count > 0
```

Open `http://127.0.0.1:8080/` in a browser, sign in, open the **Guide**
sidebar — it should read **"AI Q&A ready · RAG enabled"** with an active
Ask box and source citations under answers.

## 6. Host for guests on your LAN (Basic auth)

Sections 1–5 host PEdesk for **you** on `127.0.0.1` (loopback only). To let
others on your Wi-Fi use the Guide — with no install and no Ollama on their
side — bind to all interfaces **and turn on a password**. Never bind to a
network interface without auth.

1. Create a local credential file (kept out of git, locked down):

   ```bash
   python -c "import secrets; print('RCM_MC_AUTH=pedesk:'+secrets.token_urlsafe(18))" \
     > .pedesk_host_auth.env
   chmod 600 .pedesk_host_auth.env
   ```

   `.pedesk_host_auth.env` is git-ignored — **never commit it**.

2. Start the durable host (LAN bind + Basic auth + keep-awake):

   ```bash
   export $(cat .pedesk_host_auth.env)
   caffeinate -dimsu ./scripts/run_with_guide_ai.sh \
     serve --host 0.0.0.0 --port 8080
   ```

   Leave that Terminal open — closing it stops the server.

3. Find your Mac's LAN address and share it with guests:

   ```bash
   ipconfig getifaddr en0      # e.g. 10.0.0.126
   ```

   Guests open `http://<mac-ip>:8080`, log in with the `user:pass` from your
   env file, and use the **Guide** sidebar. They install nothing.

**Expectations + safety for LAN hosting:**

- **One user at a time.** This is a single-process server with one local
  model; concurrent questions queue behind the local model. Fine for a small
  trusted group, not a multi-tenant service.
- **24 GB RAM** comfortably runs `gemma4:e4b`; use `gemma4:e2b`
  (`PEDESK_GUIDE_OLLAMA_MODEL=gemma4:e2b`) if you want faster/lighter.
- **Keep the Mac awake** (`caffeinate -dimsu`, already in the command above).
- **Do not port-forward 8080** on your router — that exposes it to the public
  internet. LAN (or Tailscale) only.
- **Rotate the password** if it is ever pasted/shared in the wrong place:
  rewrite `.pedesk_host_auth.env` (step 1) and restart the server.
- Anyone on your current Wi-Fi who has the password can reach it — only host
  on trusted networks.

## Keep it running

Keep Ollama running and the Mac awake while serving:

```bash
caffeinate -dimsu &
```

## Security notes

- **Do not expose Ollama's port (11434) publicly.** PEdesk talks to Ollama
  over `localhost` only; users connect to **PEdesk**, never to Ollama.
- This is a single-user local host (24GB RAM is plenty for `gemma4:e4b`);
  `gemma4:e2b` is a faster/smaller fallback if needed
  (`PEDESK_GUIDE_OLLAMA_MODEL=gemma4:e2b`).
- The page guide still works without AI; Q&A requires this AI mode.

## Troubleshooting

If the sidebar shows "Ask PEdesk Guide is not fully configured," its
Setup details name the cause, or run the preflight:

| Symptom | Fix |
|---------|-----|
| Ollama not running | start Ollama.app / `ollama serve` |
| chat model missing | `ollama pull gemma4:e4b` |
| embed model missing | `ollama pull nomic-embed-text` |
| index missing/empty | `PEDESK_GUIDE_RAG_ENABLED=true ./scripts/build_guide_rag_index.sh` |
| answers slow | this is expected (~20s on a laptop); raise `PEDESK_GUIDE_OLLAMA_TIMEOUT_SECONDS` |
