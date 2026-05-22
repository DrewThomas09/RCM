"""Local SQLite vector store for RAG (stdlib sqlite3, no extra deps).

Embeddings are stored as JSON text; v1 search is brute-force cosine in
Python over the stored vectors — fine for the small Guide index (a few
hundred chunks). Read-only with respect to PEdesk's data: this is a
separate, disposable index file.
"""
from __future__ import annotations

import json
import sqlite3
import time
from typing import List, Optional, Tuple

from .embeddings import cosine_similarity
from .types import RagChunk, RagSearchResult, rag_index_path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS guide_rag_chunks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    content_hash    TEXT UNIQUE NOT NULL,
    source_id       TEXT NOT NULL,
    source_type     TEXT NOT NULL,
    title           TEXT NOT NULL,
    route           TEXT,
    metric_id       TEXT,
    data_source_id  TEXT,
    file_path       TEXT,
    section         TEXT,
    text            TEXT NOT NULL,
    embedding_json  TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_guide_rag_source ON guide_rag_chunks(source_id);
"""


def connect(path: Optional[str] = None) -> sqlite3.Connection:
    con = sqlite3.connect(path or rag_index_path())
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=5000")
    con.executescript(_SCHEMA)
    return con


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def upsert_chunk(con: sqlite3.Connection, chunk: RagChunk,
                 embedding: List[float], model: str) -> bool:
    """Insert or refresh a chunk by content_hash. Returns True if it was
    newly inserted/updated (i.e. embedding written)."""
    emb = json.dumps([float(x) for x in embedding])
    now = _now()
    con.execute(
        """
        INSERT INTO guide_rag_chunks
            (content_hash, source_id, source_type, title, route, metric_id,
             data_source_id, file_path, section, text, embedding_json,
             embedding_model, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(content_hash) DO UPDATE SET
            text=excluded.text, embedding_json=excluded.embedding_json,
            embedding_model=excluded.embedding_model, updated_at=excluded.updated_at
        """,
        (chunk.content_hash, chunk.source_id, chunk.source_type, chunk.title,
         chunk.route, chunk.metric_id, chunk.data_source_id, chunk.file_path,
         chunk.section, chunk.text, emb, model, now, now),
    )
    return True


def existing_hashes(con: sqlite3.Connection, model: str) -> set:
    cur = con.execute(
        "SELECT content_hash FROM guide_rag_chunks WHERE embedding_model=?",
        (model,),
    )
    return {r[0] for r in cur.fetchall()}


def delete_stale_chunks(con: sqlite3.Connection, keep_hashes: set) -> int:
    """Remove chunks whose content_hash is no longer produced by the
    current sources (sources removed/changed). Returns rows deleted."""
    rows = con.execute("SELECT content_hash FROM guide_rag_chunks").fetchall()
    stale = [r[0] for r in rows if r[0] not in keep_hashes]
    for h in stale:
        con.execute("DELETE FROM guide_rag_chunks WHERE content_hash=?", (h,))
    return len(stale)


def count_chunks(con: sqlite3.Connection) -> int:
    return con.execute("SELECT COUNT(*) FROM guide_rag_chunks").fetchone()[0]


def count_embedded(con: sqlite3.Connection) -> int:
    return con.execute(
        "SELECT COUNT(*) FROM guide_rag_chunks "
        "WHERE embedding_json IS NOT NULL AND embedding_json != ''"
    ).fetchone()[0]


def search_similar(con: sqlite3.Connection, query_embedding: List[float],
                   top_k: int = 5) -> List[RagSearchResult]:
    rows = con.execute(
        "SELECT title, source_type, route, metric_id, data_source_id, "
        "source_id, section, text, embedding_json FROM guide_rag_chunks"
    ).fetchall()
    scored: List[Tuple[float, sqlite3.Row]] = []
    for r in rows:
        try:
            emb = json.loads(r["embedding_json"])
        except (ValueError, TypeError):
            continue
        scored.append((cosine_similarity(query_embedding, emb), r))
    scored.sort(key=lambda t: t[0], reverse=True)
    out: List[RagSearchResult] = []
    for score, r in scored[: max(1, top_k)]:
        out.append(RagSearchResult(
            title=r["title"], source_type=r["source_type"], text=r["text"],
            score=round(float(score), 4), route=r["route"],
            metric_id=r["metric_id"], data_source_id=r["data_source_id"],
            source_id=r["source_id"], section=r["section"],
        ))
    return out
