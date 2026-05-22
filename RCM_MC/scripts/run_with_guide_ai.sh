#!/usr/bin/env bash
# run_with_guide_ai.sh — start PEdesk in FULL local AI mode:
# Ollama Q&A + local RAG both enabled. This is the preferred local /
# operator command for the integrated Guide AI path.
#
# LOCAL / DEV USE ONLY — it sets the enable env vars in front of the
# normal start command; it does not change any production default.
#
#   ./scripts/run_with_guide_ai.sh                 # serve, port 8080
#   ./scripts/run_with_guide_ai.sh --port 9000     # extra serve args
#
# Prereqs (one-time):
#   ollama pull gemma4:e4b
#   ollama pull nomic-embed-text
#   PEDESK_GUIDE_RAG_ENABLED=true ./scripts/build_guide_rag_index.sh
#   PEDESK_GUIDE_RAG_ENABLED=true ./scripts/check_guide_rag.sh
#
# After it starts, confirm: GET /api/guide/ollama-health -> "ai_ready": true
set -euo pipefail

ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$ROOT"

if [ -z "${VIRTUAL_ENV:-}" ] && [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# Full-AI env (override by exporting before calling).
export PEDESK_GUIDE_OLLAMA_ENABLED="${PEDESK_GUIDE_OLLAMA_ENABLED:-true}"
export PEDESK_GUIDE_RAG_ENABLED="${PEDESK_GUIDE_RAG_ENABLED:-true}"
export PEDESK_GUIDE_OLLAMA_MODEL="${PEDESK_GUIDE_OLLAMA_MODEL:-gemma4:e4b}"
export PEDESK_GUIDE_RAG_EMBED_MODEL="${PEDESK_GUIDE_RAG_EMBED_MODEL:-nomic-embed-text}"
export PEDESK_GUIDE_OLLAMA_BASE_URL="${PEDESK_GUIDE_OLLAMA_BASE_URL:-http://localhost:11434}"
export PEDESK_GUIDE_OLLAMA_TIMEOUT_SECONDS="${PEDESK_GUIDE_OLLAMA_TIMEOUT_SECONDS:-45}"

echo "[run_with_guide_ai] FULL AI mode · chat=$PEDESK_GUIDE_OLLAMA_MODEL · embed=$PEDESK_GUIDE_RAG_EMBED_MODEL"
echo "[run_with_guide_ai] base_url=$PEDESK_GUIDE_OLLAMA_BASE_URL · RAG=$PEDESK_GUIDE_RAG_ENABLED"

# Preflight (advisory — never blocks startup).
if python -m rcm_mc.assistant.rag.preflight_guide_ai; then
  :
else
  echo "[run_with_guide_ai] Preflight found issues (see above). Starting anyway;"
  echo "[run_with_guide_ai] the sidebar will explain what's missing."
fi

if [ "$#" -eq 0 ]; then
  set -- serve --port 8080
fi
exec rcm-mc "$@"
