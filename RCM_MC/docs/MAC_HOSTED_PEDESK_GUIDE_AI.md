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
