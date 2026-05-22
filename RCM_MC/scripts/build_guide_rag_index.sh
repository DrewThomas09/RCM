#!/usr/bin/env bash
# build_guide_rag_index.sh — build the local PEdesk Guide RAG index.
# LOCAL / DEV USE. Requires Ollama running with the embedding model pulled
# (ollama pull nomic-embed-text). Read-only over in-repo Guide context;
# no uploads, no cloud.
#
#   ./scripts/build_guide_rag_index.sh                 # default index path
#   ./scripts/build_guide_rag_index.sh --model nomic-embed-text
set -euo pipefail
ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$ROOT"
if [ -z "${VIRTUAL_ENV:-}" ] && [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
export PEDESK_GUIDE_OLLAMA_ENABLED="${PEDESK_GUIDE_OLLAMA_ENABLED:-true}"
export PEDESK_GUIDE_RAG_ENABLED="${PEDESK_GUIDE_RAG_ENABLED:-true}"
export PEDESK_GUIDE_RAG_EMBED_MODEL="${PEDESK_GUIDE_RAG_EMBED_MODEL:-nomic-embed-text}"
exec python -m rcm_mc.assistant.rag.index_builder "$@"
