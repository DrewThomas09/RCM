#!/usr/bin/env bash
# run_with_guide_ollama.sh — start PEdesk locally with the PEdesk Guide
# Q&A (local Ollama) enabled. LOCAL / DEV USE ONLY — it sets the enable
# env vars in front of the normal start command; it does not change any
# production default.
#
#   ./scripts/run_with_guide_ollama.sh                 # serve, port 8080
#   ./scripts/run_with_guide_ollama.sh --port 9000     # extra serve args
#   PEDESK_GUIDE_RAG_ENABLED=true ./scripts/run_with_guide_ollama.sh
#
# Prereqs (one-time):
#   ollama pull gemma4:e4b
#   ollama pull nomic-embed-text     # only needed if RAG is enabled
#   ollama list                      # confirm the models are present
#
# To also use RAG, build the local index first (Ollama must be running):
#   PEDESK_GUIDE_OLLAMA_ENABLED=true PEDESK_GUIDE_RAG_ENABLED=true \
#     .venv/bin/python -m rcm_mc.assistant.rag.index_builder
set -euo pipefail

ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$ROOT"

# Activate the venv if present and not already active.
if [ -z "${VIRTUAL_ENV:-}" ] && [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# Guide-Ollama env (override by exporting before calling this script).
export PEDESK_GUIDE_OLLAMA_ENABLED="${PEDESK_GUIDE_OLLAMA_ENABLED:-true}"
export PEDESK_GUIDE_OLLAMA_MODEL="${PEDESK_GUIDE_OLLAMA_MODEL:-gemma4:e4b}"
export PEDESK_GUIDE_OLLAMA_BASE_URL="${PEDESK_GUIDE_OLLAMA_BASE_URL:-http://localhost:11434}"
export PEDESK_GUIDE_OLLAMA_TIMEOUT_SECONDS="${PEDESK_GUIDE_OLLAMA_TIMEOUT_SECONDS:-45}"
# RAG is opt-in (and needs a built index); leave default off here.
export PEDESK_GUIDE_RAG_ENABLED="${PEDESK_GUIDE_RAG_ENABLED:-false}"
export PEDESK_GUIDE_RAG_EMBED_MODEL="${PEDESK_GUIDE_RAG_EMBED_MODEL:-nomic-embed-text}"

echo "[run_with_guide_ollama] Guide Q&A enabled · model=$PEDESK_GUIDE_OLLAMA_MODEL"
echo "[run_with_guide_ollama] base_url=$PEDESK_GUIDE_OLLAMA_BASE_URL · RAG=$PEDESK_GUIDE_RAG_ENABLED"
if ! curl -sf -m 3 "$PEDESK_GUIDE_OLLAMA_BASE_URL/api/tags" >/dev/null 2>&1; then
  echo "[run_with_guide_ollama] WARNING: Ollama not reachable at $PEDESK_GUIDE_OLLAMA_BASE_URL"
  echo "[run_with_guide_ollama]          Start it (ollama serve) and 'ollama pull $PEDESK_GUIDE_OLLAMA_MODEL'."
fi

# Default to 'serve' if the caller passed no rcm-mc subcommand args.
if [ "$#" -eq 0 ]; then
  set -- serve --port 8080
fi
exec rcm-mc "$@"
