#!/usr/bin/env bash
# run_mac_hosted_guide_ai.sh — run PEdesk in FULL local AI mode on this
# Mac (PEdesk + local Ollama + RAG, single-user). Thin wrapper that pins
# the Mac-local env and delegates to run_with_guide_ai.sh.
#
#   ./scripts/run_mac_hosted_guide_ai.sh                # serve, port 8080
#   ./scripts/run_mac_hosted_guide_ai.sh --port 9000    # extra serve args
#
# Prereqs (one-time):
#   ollama pull gemma4:e4b
#   ollama pull nomic-embed-text
#   PEDESK_GUIDE_RAG_ENABLED=true ./scripts/build_guide_rag_index.sh
#
# Keep the Mac awake while serving:  caffeinate -dimsu &
# SECURITY: do NOT expose Ollama's port (11434) publicly. Users connect to
# PEdesk only; PEdesk talks to Ollama over localhost.
set -euo pipefail

ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$ROOT"

# Mac-local full-AI defaults (override by exporting before calling).
export PEDESK_GUIDE_OLLAMA_ENABLED=true
export PEDESK_GUIDE_RAG_ENABLED=true
export PEDESK_GUIDE_OLLAMA_MODEL="${PEDESK_GUIDE_OLLAMA_MODEL:-gemma4:e4b}"
export PEDESK_GUIDE_RAG_EMBED_MODEL="${PEDESK_GUIDE_RAG_EMBED_MODEL:-nomic-embed-text}"
export PEDESK_GUIDE_OLLAMA_BASE_URL="${PEDESK_GUIDE_OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
export PEDESK_GUIDE_OLLAMA_TIMEOUT_SECONDS="${PEDESK_GUIDE_OLLAMA_TIMEOUT_SECONDS:-45}"

exec ./scripts/run_with_guide_ai.sh "$@"
