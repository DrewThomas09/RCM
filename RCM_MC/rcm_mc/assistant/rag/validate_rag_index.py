"""Validate the local PEdesk Guide RAG index.

    python -m rcm_mc.assistant.rag.validate_rag_index [--index PATH]

Confirms the DB exists, has chunks + embeddings, and runs a few test
searches, printing the top sources. Exits non-zero on a hard failure
(missing DB / no chunks). Search requires a reachable local embedding
model; if it isn't, that's reported (not a hard schema failure).
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

from .. import ollama_client
from . import retrieval, vector_store
from .types import rag_index_path

_TEST_QUERIES = [
    "Where does HCRIS data come from?",
    "What does denial rate mean?",
    "Can PEdesk Guide change assumptions?",
]


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="rcm_mc.assistant.rag.validate_rag_index")
    ap.add_argument("--index", default=None)
    args = ap.parse_args(argv)
    path = args.index or rag_index_path()

    print("PEdesk Guide RAG index validation")
    print(f"  index path: {path}")
    if not os.path.exists(path):
        print("  FAIL: index file does not exist. Build it with "
              "`python -m rcm_mc.assistant.rag.index_builder`.")
        return 1

    con = vector_store.connect(path)
    try:
        chunks = vector_store.count_chunks(con)
        embedded = vector_store.count_embedded(con)
    finally:
        con.close()
    print(f"  chunks    : {chunks}")
    print(f"  embedded  : {embedded}")
    if chunks <= 0:
        print("  FAIL: index has no chunks.")
        return 1
    if embedded <= 0:
        print("  FAIL: index has no embeddings.")
        return 1

    print("  test searches:")
    try:
        for q in _TEST_QUERIES:
            results = retrieval.search(q, top_k=3, index_path=path)
            tops = ", ".join(r.source_label() for r in results) or "(none)"
            print(f"    - {q!r}")
            print(f"        top: {tops}")
    except ollama_client.OllamaError as exc:
        print(f"  WARN: could not run live searches — {exc}")
        print("  (schema/chunks/embeddings are valid; start Ollama with the "
              "embedding model to test retrieval.)")
        return 0

    print("  PASS — index exists, has embedded chunks, and search works.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
