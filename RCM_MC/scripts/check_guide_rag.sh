#!/usr/bin/env bash
# check_guide_rag.sh — validate the local PEdesk Guide RAG index
# (existence, chunk/embedding counts, embedding-model consistency, and a
# few live test searches if Ollama is reachable). Read-only.
#
#   ./scripts/check_guide_rag.sh
set -euo pipefail
ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$ROOT"
if [ -z "${VIRTUAL_ENV:-}" ] && [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
export PEDESK_GUIDE_RAG_EMBED_MODEL="${PEDESK_GUIDE_RAG_EMBED_MODEL:-nomic-embed-text}"
exec python -m rcm_mc.assistant.rag.validate_rag_index "$@"
