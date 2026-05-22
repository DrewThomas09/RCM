"""Build the local PEdesk Guide RAG index.

    python -m rcm_mc.assistant.rag.index_builder [--index PATH] [--model M]

Gathers read-only document sources, chunks them, embeds each new/changed
chunk via local Ollama, and upserts into the SQLite index. Idempotent:
chunks whose content_hash already exists (same model) are skipped, and
chunks no longer produced by the sources are pruned.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import List, Optional

from .. import ollama_client
from . import vector_store
from .chunking import chunk_documents
from .document_sources import iter_guide_documents
from .embeddings import embed_texts
from .types import rag_embed_model, rag_index_path

_EMBED_BATCH = 16


@dataclass
class BuildReport:
    sources: int = 0
    chunks: int = 0
    embedded: int = 0
    skipped: int = 0
    pruned: int = 0
    errors: int = 0
    error_detail: Optional[str] = None


def build_index(index_path: Optional[str] = None,
                model: Optional[str] = None) -> BuildReport:
    path = index_path or rag_index_path()
    model = model or rag_embed_model()
    rep = BuildReport()

    docs = iter_guide_documents()
    rep.sources = len(docs)
    chunks = chunk_documents(docs)
    rep.chunks = len(chunks)

    con = vector_store.connect(path)
    try:
        have = vector_store.existing_hashes(con, model)
        todo = [c for c in chunks if c.content_hash not in have]
        rep.skipped = len(chunks) - len(todo)

        for i in range(0, len(todo), _EMBED_BATCH):
            batch = todo[i:i + _EMBED_BATCH]
            try:
                vectors = embed_texts([c.text for c in batch], model=model)
            except ollama_client.OllamaError as exc:
                rep.errors += len(batch)
                rep.error_detail = str(exc)
                break
            for c, v in zip(batch, vectors):
                vector_store.upsert_chunk(con, c, v, model)
                rep.embedded += 1
            con.commit()

        # Prune chunks no longer produced by the current sources.
        keep = {c.content_hash for c in chunks}
        rep.pruned = vector_store.delete_stale_chunks(con, keep)
        con.commit()
    finally:
        con.close()
    return rep


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="rcm_mc.assistant.rag.index_builder")
    ap.add_argument("--index", default=None, help="index SQLite path")
    ap.add_argument("--model", default=None, help="embedding model")
    args = ap.parse_args(argv)

    rep = build_index(index_path=args.index, model=args.model)
    print("PEdesk Guide RAG index build")
    print(f"  index path : {args.index or rag_index_path()}")
    print(f"  embed model: {args.model or rag_embed_model()}")
    print(f"  sources    : {rep.sources}")
    print(f"  chunks     : {rep.chunks}")
    print(f"  embedded   : {rep.embedded}")
    print(f"  skipped    : {rep.skipped} (already indexed)")
    print(f"  pruned     : {rep.pruned} (stale removed)")
    print(f"  errors     : {rep.errors}")
    if rep.error_detail:
        print(f"  error      : {rep.error_detail}")
        print("  hint       : ensure Ollama is running and the embedding "
              "model is pulled (ollama pull " + (args.model or rag_embed_model()) + ").")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
