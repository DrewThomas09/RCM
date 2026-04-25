"""Per-target regulatory exposure scoring + jurisdictional heatmap.

Inputs:
  • A target profile (sector + states of operation + EBITDA)
  • A regulatory corpus (RegulatoryCorpus) populated by the ingestor

Output:
  • A topic-level exposure list: each topic that's both relevant to
    the target's sector AND has supporting documents in the corpus,
    with the dollar EBITDA-at-risk and the top citations.
  • A jurisdictional heatmap: state × topic → $-EBITDA-at-risk
    (only states the target operates in are populated; others are
    omitted).

The dollar math is intentionally explicit:

    ebitda_at_risk = target_ebitda
                     × topic.ebitda_sensitivity
                     × topic_density_multiplier
                     × jurisdictional_match

  - topic_density_multiplier is min(1.0, n_docs/3) — three or
    more documents on a topic crystallizes the threat.
  - jurisdictional_match is 1.0 for the topic's anchored states,
    0.5 for any-state topics applied to a target's home state.

Every input is auditable. Partners can ask "why is FTC noncompete
costing me $4M?" and the topic citations back it up.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .corpus import RegulatoryCorpus, RegulatoryDocument
from .topics import (
    TOPIC_ANCHORS, classify_document_topics, TopicMatch,
)
from .tfidf import compute_tfidf


@dataclass
class TargetProfile:
    target_name: str
    sector: str
    states: List[str] = field(default_factory=list)
    ebitda_mm: float = 0.0


@dataclass
class TopicExposure:
    topic_id: str
    label: str
    n_documents: int
    relevance: float
    ebitda_at_risk_mm: float
    citations: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class TargetExposureResult:
    target_name: str
    sector: str
    ebitda_mm: float
    total_at_risk_mm: float
    topic_exposures: List[TopicExposure] = field(default_factory=list)


def _topic_applicable(topic_id: str, sector: str) -> bool:
    anchor = TOPIC_ANCHORS.get(topic_id)
    if not anchor:
        return False
    if not anchor.applicable_sectors:
        return True
    s = sector.lower().replace(" ", "_")
    return s in {x.lower() for x in anchor.applicable_sectors}


def score_target_exposure(
    target: TargetProfile,
    corpus: RegulatoryCorpus,
) -> TargetExposureResult:
    """Build the per-topic EBITDA-at-risk view for a target.

    Steps:
      1. Compute corpus-wide TF-IDF (so topic relevance benefits
         from term distinctiveness).
      2. For every document, classify topics with anchor matching.
      3. Aggregate: per topic, count documents + average relevance,
         keep top citations.
      4. Filter to topics applicable to the target sector.
      5. Compute ebitda_at_risk = ebitda × sensitivity × density
         × jurisdictional_match.
    """
    target_states = {s.upper() for s in (target.states or [])}

    tfidf = compute_tfidf(
        (d.doc_id, f"{d.title}\n{d.body}") for d in corpus.documents
    )

    per_topic_docs: Dict[str, List[
        tuple]] = defaultdict(list)  # topic_id → [(relevance, doc)]
    per_topic_state_hits: Dict[str, set] = defaultdict(set)

    for doc in corpus.documents:
        scores = tfidf.get(doc.doc_id, {})
        text = f"{doc.title}\n{doc.body}"
        matches = classify_document_topics(text, tfidf_scores=scores)
        for m in matches:
            per_topic_docs[m.topic_id].append((m.relevance, doc))
            for st in (doc.states or []):
                per_topic_state_hits[m.topic_id].add(st.upper())

    exposures: List[TopicExposure] = []
    for topic_id, anchor in TOPIC_ANCHORS.items():
        if not _topic_applicable(topic_id, target.sector):
            continue
        hits = per_topic_docs.get(topic_id, [])
        if not hits:
            continue

        # Density multiplier: three documents on a topic = 1.0,
        # one document = 0.33, etc.
        density = min(1.0, len(hits) / 3.0)
        avg_relevance = sum(h[0] for h in hits) / len(hits)

        # Jurisdictional match — if the topic's documents are
        # anchored to states the target operates in, full match.
        # Federal-level topics (no state on the docs) get 0.7.
        topic_states = per_topic_state_hits.get(topic_id, set())
        if not topic_states:
            jur = 0.7  # Federal docs apply nationally but at lower
                       # punch than state-targeted action
        elif target_states and (topic_states & target_states):
            jur = 1.0
        else:
            jur = 0.3  # documents exist but not where target operates

        at_risk = (target.ebitda_mm
                   * anchor.ebitda_sensitivity
                   * density
                   * jur)

        # Top 3 citations (highest TF-IDF relevance)
        top_hits = sorted(hits, key=lambda r: r[0], reverse=True)[:3]
        citations = [
            {
                "doc_id": d.doc_id,
                "title": d.title,
                "source": d.source,
                "date": d.date,
                "citation": d.citation,
                "relevance": round(rel, 3),
            }
            for rel, d in top_hits
        ]

        exposures.append(TopicExposure(
            topic_id=topic_id,
            label=anchor.label,
            n_documents=len(hits),
            relevance=round(avg_relevance, 3),
            ebitda_at_risk_mm=round(at_risk, 3),
            citations=citations,
        ))

    exposures.sort(key=lambda e: e.ebitda_at_risk_mm, reverse=True)
    total = sum(e.ebitda_at_risk_mm for e in exposures)
    return TargetExposureResult(
        target_name=target.target_name,
        sector=target.sector,
        ebitda_mm=target.ebitda_mm,
        total_at_risk_mm=round(total, 3),
        topic_exposures=exposures,
    )


def jurisdictional_heatmap(
    target: TargetProfile,
    corpus: RegulatoryCorpus,
) -> Dict[str, Dict[str, float]]:
    """Build a {state → {topic_id → $-at-risk}} dict ready for a
    grid-style UI render. Only includes the target's operating
    states; topics with zero exposure are omitted.

    Per-state EBITDA-at-risk is the topic-level at-risk divided
    evenly across the target's operating states (a rough but
    interpretable allocation; partners can override).
    """
    full = score_target_exposure(target, corpus)
    states = sorted({s.upper() for s in (target.states or [])})
    n_states = max(1, len(states))

    heatmap: Dict[str, Dict[str, float]] = {st: {} for st in states}
    for exposure in full.topic_exposures:
        per_state = round(exposure.ebitda_at_risk_mm / n_states, 3)
        # Per-topic per-state allocation. Topics with explicit
        # state matches in their corpus could be allocated
        # proportionally — a v2 enhancement.
        for st in states:
            heatmap[st][exposure.topic_id] = per_state
    return heatmap
