"""Corpus + vocabulary construction.

Inputs to LDA are just (doc_id, text, optional date). We tokenize
with the same lightweight regex used by the regulatory packet,
then build a vocabulary capped at the top-N most-frequent tokens
to keep matrix sizes bounded.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

# Reuse the tokenizer + stopword list from the regulatory package.
from ..regulatory.tfidf import tokenize


@dataclass
class Document:
    """One corpus document — a deal description, press release,
    industry note, etc."""
    doc_id: str
    text: str
    date: str = ""              # ISO YYYY-MM-DD when known
    sector: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class Corpus:
    """Holder for documents + the vocabulary derived from them."""
    documents: List[Document] = field(default_factory=list)
    vocab: List[str] = field(default_factory=list)
    word_to_idx: Dict[str, int] = field(default_factory=dict)
    doc_token_ids: List[List[int]] = field(default_factory=list)


def build_vocabulary(
    docs: Iterable[Document],
    *,
    max_vocab: int = 5000,
    min_count: int = 2,
) -> Corpus:
    """Tokenize every document and build a vocabulary capped at
    the top-``max_vocab`` most-frequent tokens.

    Returns a Corpus with documents + vocab + per-doc token-id
    lists. Tokens not in the vocab are dropped from doc_token_ids
    so the LDA matrix stays clean.
    """
    docs = list(docs)
    counter: Counter = Counter()
    per_doc_tokens: List[List[str]] = []
    for d in docs:
        toks = tokenize(d.text)
        per_doc_tokens.append(toks)
        counter.update(toks)
    # Filter by min_count, then pick top max_vocab
    surviving = [
        (w, c) for w, c in counter.items() if c >= min_count
    ]
    surviving.sort(key=lambda kv: kv[1], reverse=True)
    vocab = [w for w, _ in surviving[:max_vocab]]
    word_to_idx = {w: i for i, w in enumerate(vocab)}

    doc_token_ids: List[List[int]] = []
    for toks in per_doc_tokens:
        ids = [word_to_idx[t] for t in toks if t in word_to_idx]
        doc_token_ids.append(ids)

    return Corpus(
        documents=docs,
        vocab=vocab,
        word_to_idx=word_to_idx,
        doc_token_ids=doc_token_ids,
    )
