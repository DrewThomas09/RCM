"""LDA-based topic discovery on a regulatory corpus.

The hand-curated TOPIC_ANCHORS catch known threats (FTC
noncompete, state CON/CPOM, OPPS site-neutral, V28 cliff,
Stark/AKS, rate review). What they miss is the EMERGING ones —
the topic that's only just started showing up in Federal Register
notices, or the OIG-enforcement category that nobody on the
diligence team has named yet.

This module runs collapsed-Gibbs LDA over the regulatory corpus
to surface what's there empirically, then compares each
discovered topic against the existing anchor taxonomy:

  • If the topic's top words have ≥2 keyword hits against an
    anchor, label it as that anchor (validation: the data agrees
    with the taxonomy).
  • If no anchor matches, flag the topic as "novel" — these are
    the unknowns the partner should review by eye and consider
    adding to the taxonomy.

We reuse the pure-numpy LDA from rcm_mc.sector_themes.lda — same
collapsed-Gibbs sampler, source-agnostic. The regulatory wrapper
just builds the corpus shape from RegulatoryDocument lists and
applies a small regulatory-specific stopword extension.

Public API::

    from rcm_mc.regulatory import (
        discover_regulatory_topics,
        DiscoveredTopic, TopicDiscoveryResult,
    )
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from .corpus import RegulatoryCorpus, RegulatoryDocument
from .topics import TOPIC_ANCHORS


@dataclass
class DiscoveredTopic:
    """One LDA-discovered topic + classification against anchors."""
    topic_index: int
    top_words: List[Tuple[str, float]]      # (word, prob)
    anchor_id: Optional[str]                # anchor it matched, or None
    anchor_label: Optional[str]
    is_novel: bool
    n_anchor_keyword_hits: int
    document_share: float                   # fraction of corpus
                                            # whose top topic = this


@dataclass
class TopicDiscoveryResult:
    """Output of discover_regulatory_topics."""
    K: int
    topics: List[DiscoveredTopic] = field(default_factory=list)
    novel_topic_count: int = 0
    matched_topic_count: int = 0


def _classify_topic_against_anchors(
    top_words: List[Tuple[str, float]],
    *,
    min_hits: int = 2,
) -> Tuple[Optional[str], Optional[str], int]:
    """Find the best-matching anchor for a discovered topic by
    counting keyword hits in the top-N words.

    Returns (anchor_id, label, n_hits).
    """
    word_set = {w for w, _ in top_words}
    best_id: Optional[str] = None
    best_label: Optional[str] = None
    best_hits = 0
    for anchor in TOPIC_ANCHORS.values():
        n_hits = 0
        for kw in anchor.keywords:
            kw_low = kw.lower()
            # Multi-word phrases: check whether any top word is a
            # token from the phrase.
            if " " in kw_low or "-" in kw_low:
                tokens = (kw_low.replace("-", " ")
                          .split())
                if any(t in word_set for t in tokens):
                    n_hits += 1
            else:
                if kw_low in word_set:
                    n_hits += 1
        if n_hits > best_hits:
            best_hits = n_hits
            best_id = anchor.topic_id
            best_label = anchor.label
    if best_hits >= min_hits:
        return best_id, best_label, best_hits
    return None, None, best_hits


def discover_regulatory_topics(
    corpus: RegulatoryCorpus,
    *,
    K: int = 6,
    n_top_words: int = 12,
    n_iter: int = 80,
    seed: int = 7,
    min_anchor_hits: int = 2,
) -> TopicDiscoveryResult:
    """Run LDA on the regulatory corpus + classify each discovered
    topic against the hand-curated anchor taxonomy.

    Args:
      corpus: RegulatoryCorpus with N documents.
      K: number of latent topics to fit.
      n_top_words: top words per topic for the result + anchor match.
      n_iter: collapsed-Gibbs iterations.
      seed: RNG seed for reproducibility.
      min_anchor_hits: anchor-keyword hit threshold for an LDA
        topic to be classified as that anchor (else "novel").

    Returns a TopicDiscoveryResult with per-topic top words,
    anchor labels, and novel-topic flags.
    """
    if not corpus.documents:
        return TopicDiscoveryResult(K=K)

    # Build a sector_themes-compatible Document list from the
    # regulatory documents. Concatenate title + body to give the
    # LDA more signal per doc.
    from ..sector_themes.corpus import (
        Document as ThemeDocument, build_vocabulary,
    )
    from ..sector_themes.lda import fit_lda_collapsed_gibbs

    theme_docs = [
        ThemeDocument(
            doc_id=d.doc_id,
            text=f"{d.title}\n{d.body}",
            date=d.date,
        )
        for d in corpus.documents
    ]
    theme_corpus = build_vocabulary(theme_docs, min_count=2)
    if not theme_corpus.vocab:
        return TopicDiscoveryResult(K=K)

    model = fit_lda_collapsed_gibbs(
        theme_corpus, K=K, n_iter=n_iter, seed=seed)

    # Document-share per topic: each doc's top topic
    if model.theta.size > 0:
        top_topic_per_doc = model.theta.argmax(axis=1)
        share_counter = Counter(top_topic_per_doc.tolist())
        n_docs = len(theme_docs)
    else:
        share_counter = Counter()
        n_docs = max(1, len(theme_docs))

    topics: List[DiscoveredTopic] = []
    matched = 0
    novel = 0
    for k in range(K):
        words = model.top_words(k, n_top=n_top_words)
        anchor_id, anchor_label, hits = (
            _classify_topic_against_anchors(
                words, min_hits=min_anchor_hits))
        is_novel = anchor_id is None
        if is_novel:
            novel += 1
        else:
            matched += 1
        topics.append(DiscoveredTopic(
            topic_index=k,
            top_words=words,
            anchor_id=anchor_id,
            anchor_label=anchor_label,
            is_novel=is_novel,
            n_anchor_keyword_hits=hits,
            document_share=round(
                share_counter.get(k, 0) / n_docs, 4),
        ))

    return TopicDiscoveryResult(
        K=K,
        topics=topics,
        novel_topic_count=novel,
        matched_topic_count=matched,
    )
