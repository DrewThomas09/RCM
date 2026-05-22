"""Preflight check for full PEdesk Guide AI mode (Ollama + RAG).

    python -m rcm_mc.assistant.rag.preflight_guide_ai

One human-readable PASS / WARN / FAIL report covering: Ollama reachable,
chat model installed, embed model installed, RAG index exists / has
chunks / has embeddings, and a live retrieval test. Read-only; never
mutates anything. Exit 0 when the full AI path is ready, 1 otherwise.
"""
from __future__ import annotations

import sys
from typing import List, Optional, Tuple

from .. import ollama_client
from . import retrieval
from .types import is_rag_enabled, rag_embed_model, rag_index_path

_TEST_QUERY = "What does denial rate mean?"


def _model_installed(name: str, installed: List[str]) -> bool:
    base = name.split(":")[0]
    return any(m == name or m.split(":")[0] == base for m in installed)


def run() -> Tuple[bool, List[str]]:
    """Return (ai_ready, lines)."""
    lines: List[str] = []
    ok = True

    def emit(level: str, msg: str, fix: str = "") -> None:
        nonlocal ok
        lines.append(f"  [{level}] {msg}" + (f"\n         fix: {fix}" if fix else ""))
        if level == "FAIL":
            ok = False

    enabled = ollama_client.is_ollama_enabled()
    if enabled:
        emit("PASS", "Ollama enabled (PEDESK_GUIDE_OLLAMA_ENABLED=true)")
    else:
        emit("FAIL", "Ollama disabled",
             "PEDESK_GUIDE_OLLAMA_ENABLED=true ./scripts/run_with_guide_ai.sh")

    reachable = ollama_client.check_ollama_health() if enabled else False
    base = ollama_client.ollama_base_url()
    if reachable:
        emit("PASS", f"Ollama reachable at {base}")
    elif enabled:
        emit("FAIL", f"Ollama not reachable at {base}",
             "start Ollama (ollama serve) and check PEDESK_GUIDE_OLLAMA_BASE_URL")

    installed = ollama_client.list_models() if reachable else []
    chat = ollama_client.ollama_default_model()
    embed = rag_embed_model()
    if reachable:
        if _model_installed(chat, installed):
            emit("PASS", f"chat model installed: {chat}")
        else:
            emit("FAIL", f"chat model missing: {chat}", f"ollama pull {chat}")
        if _model_installed(embed, installed):
            emit("PASS", f"embed model installed: {embed}")
        else:
            emit("FAIL", f"embed model missing: {embed}", f"ollama pull {embed}")

    if not is_rag_enabled():
        emit("WARN", "RAG disabled (PEDESK_GUIDE_RAG_ENABLED not set) — Q&A "
             "would be packet-only",
             "PEDESK_GUIDE_RAG_ENABLED=true ./scripts/run_with_guide_ai.sh")

    st = retrieval.index_status()
    path = rag_index_path()
    if st.get("exists"):
        emit("PASS", f"RAG index exists: {path}")
        if st.get("chunk_count", 0) > 0:
            emit("PASS", f"RAG index has {st['chunk_count']} chunks")
        else:
            emit("FAIL", "RAG index has no chunks",
                 "PEDESK_GUIDE_RAG_ENABLED=true ./scripts/build_guide_rag_index.sh")
        if st.get("embedded_count", 0) > 0:
            emit("PASS", f"RAG index has {st['embedded_count']} embeddings")
        else:
            emit("FAIL", "RAG index has no embeddings",
                 "PEDESK_GUIDE_RAG_ENABLED=true ./scripts/build_guide_rag_index.sh")
    else:
        emit("FAIL", f"RAG index missing: {path}",
             "PEDESK_GUIDE_RAG_ENABLED=true ./scripts/build_guide_rag_index.sh")

    # Live retrieval test (only if the pieces above are in place).
    if reachable and st.get("embedded_count", 0) > 0 and is_rag_enabled():
        try:
            results = retrieval.search(_TEST_QUERY, top_k=3)
            if results:
                top = results[0].source_label()
                emit("PASS", f"RAG search ok — {_TEST_QUERY!r} → {top}")
            else:
                emit("WARN", f"RAG search returned no results for {_TEST_QUERY!r}")
        except ollama_client.OllamaError as exc:
            emit("FAIL", f"RAG search failed: {exc}",
                 f"ollama pull {embed}")

    return ok, lines


def main(argv: Optional[List[str]] = None) -> int:
    ok, lines = run()
    print("PEdesk Guide — full AI mode preflight")
    for ln in lines:
        print(ln)
    print(f"\n  RESULT: {'READY' if ok else 'NOT READY'}")
    if not ok:
        print("  Setup: ollama pull gemma4:e4b && ollama pull nomic-embed-text")
        print("         PEDESK_GUIDE_RAG_ENABLED=true ./scripts/build_guide_rag_index.sh")
        print("         PEDESK_GUIDE_RAG_ENABLED=true ./scripts/run_with_guide_ai.sh")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
