"""TF-IDF — pure stdlib implementation.

We compute term frequency × inverse document frequency for the
document corpus, returning a sparse {token → score} dict per
document. Used by ``topics.classify_document_topics`` to find
topic-anchor overlap.

Why stdlib: this codebase ships zero new runtime deps, and a
50K-document corpus runs in ~1s with Counter + dict — no need
for sklearn here.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, Iterable, List, Tuple


# Lightweight English stopword list — a literal dataset we don't
# want to ship 8KB of. Hand-curated for healthcare-regulatory
# corpora (so terms like "rule" and "act" are kept since they
# carry legal meaning).
_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "at",
    "by", "for", "with", "as", "is", "are", "was", "were", "be",
    "been", "being", "this", "that", "these", "those", "it", "its",
    "from", "into", "but", "not", "no", "we", "our", "you", "your",
    "their", "they", "them", "him", "her", "his", "she", "he",
    "have", "has", "had", "will", "would", "should", "could", "may",
    "might", "can", "shall", "do", "does", "did", "if", "than",
    "then", "there", "which", "who", "what", "when", "where", "why",
    "how", "any", "all", "some", "such", "other", "more", "most",
    "very", "much", "many", "few", "each", "every", "also", "only",
    "just", "see", "page", "section", "subsection",
})

# Tokenizer — lowercase, alphanum + hyphens, drop short tokens.
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]{2,}")


def tokenize(text: str) -> List[str]:
    """Tokenize a string into lowercased terms; drop stopwords."""
    if not text:
        return []
    out: List[str] = []
    for m in _TOKEN_RE.finditer(text):
        t = m.group(0).lower()
        if t in _STOPWORDS:
            continue
        out.append(t)
    return out


def compute_tfidf(
    documents: Iterable[Tuple[str, str]],
) -> Dict[str, Dict[str, float]]:
    """Return a {doc_id → {term → tfidf}} mapping.

    Inputs:
      documents: iterable of (doc_id, text) tuples.

    The IDF uses the standard ``log(N / df)`` form with smoothing
    so terms in every doc still score above zero.
    """
    docs = list(documents)
    n_docs = len(docs)
    if n_docs == 0:
        return {}

    # 1) Count term frequency per document
    tf_per_doc: Dict[str, Counter] = {}
    df_counter: Counter = Counter()
    for doc_id, text in docs:
        tokens = tokenize(text)
        tf = Counter(tokens)
        tf_per_doc[doc_id] = tf
        for term in tf:
            df_counter[term] += 1

    # 2) Compute IDF per term
    idf: Dict[str, float] = {}
    for term, df in df_counter.items():
        # Smoothed: log((n_docs + 1) / (df + 1)) + 1
        idf[term] = math.log((n_docs + 1) / (df + 1)) + 1.0

    # 3) Compute TF-IDF per (doc, term)
    out: Dict[str, Dict[str, float]] = {}
    for doc_id, tf in tf_per_doc.items():
        doc_total = sum(tf.values()) or 1
        scores: Dict[str, float] = {}
        for term, count in tf.items():
            scores[term] = (count / doc_total) * idf[term]
        out[doc_id] = scores
    return out


def top_terms(
    tfidf_scores: Dict[str, float],
    *,
    n: int = 10,
) -> List[Tuple[str, float]]:
    """Top-N terms for a document by TF-IDF score."""
    return sorted(
        tfidf_scores.items(), key=lambda kv: kv[1], reverse=True,
    )[:n]
