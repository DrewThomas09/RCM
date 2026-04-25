"""Regulatory risk scoring — NLP over public regulatory corpora.

Ingests documents from:
  • Federal Register (proposed + final rules)
  • OIG enforcement actions
  • FTC notices (including healthcare-noncompete enforcement)
  • State CON/CPOM legislation
  • CMS rules + sub-regulatory guidance (Calendar Year payment rules)

Scores per-target regulatory exposure as the sum of:
  topic_relevance (TF-IDF document similarity)
  × jurisdictional_match (states the target operates in)
  × ebitda_sensitivity (predefined per topic)

Output: a heatmap dict of (topic × jurisdiction) → $-EBITDA-at-risk
plus a bullet list of the top-N citations per topic, ready to drop
into a partner brief.

The pipeline is intentionally deterministic — no MCMC LDA or
black-box embeddings. Topic anchors are hand-curated keyword
sets that map to specific regulatory threats; exposure scores
are auditable line-items the partner can cross-check against the
underlying citations.

Public API::

    from rcm_mc.regulatory import (
        RegulatoryDocument, RegulatoryCorpus,
        compute_tfidf,                  # stdlib TF-IDF
        TOPIC_ANCHORS,                  # predefined topic taxonomy
        score_target_exposure,          # main scoring entry point
        jurisdictional_heatmap,         # state × topic × $
    )
"""
from .corpus import RegulatoryDocument, RegulatoryCorpus
from .tfidf import compute_tfidf, top_terms
from .topics import (
    TOPIC_ANCHORS,
    classify_document_topics,
    TopicMatch,
)
from .score import (
    score_target_exposure,
    jurisdictional_heatmap,
    TargetProfile,
    TargetExposureResult,
)

__all__ = [
    "RegulatoryDocument",
    "RegulatoryCorpus",
    "compute_tfidf",
    "top_terms",
    "TOPIC_ANCHORS",
    "classify_document_topics",
    "TopicMatch",
    "score_target_exposure",
    "jurisdictional_heatmap",
    "TargetProfile",
    "TargetExposureResult",
]
