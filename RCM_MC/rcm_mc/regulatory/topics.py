"""Regulatory topic taxonomy + topic-keyword anchors.

The user's directive named four concrete current threats:

  1. FTC healthcare-noncompete enforcement (the 2024 final rule
     was vacated; FTC continues case-by-case enforcement)
  2. State legislative wave on CON/CPOM repeal/amendment
  3. CY2026 OPPS site-neutral payment expansion
  4. ACO REACH PY2026 V28 risk-coding cliff

Each topic carries:
  • a unique id used for joining against the heatmap output
  • a human-readable label
  • a keyword anchor list — the canonical strings the TF-IDF /
    overlap scoring uses to detect the topic in a document
  • an EBITDA sensitivity factor — how much of a typical target's
    EBITDA is at risk if the topic crystallizes
  • applicable sectors so a hospital diligence doesn't false-
    positive on a physician-noncompete case

A document gets a topic match if the topic's anchor keywords
appear with non-trivial TF-IDF scores. Multiple topics can match.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set

from .tfidf import tokenize


@dataclass
class TopicAnchor:
    topic_id: str
    label: str
    keywords: List[str]
    ebitda_sensitivity: float       # 0-1, applied to target EBITDA
    applicable_sectors: List[str] = field(default_factory=list)


# ── Predefined topic anchors ─────────────────────────────────────

TOPIC_ANCHORS: Dict[str, TopicAnchor] = {
    "ftc_noncompete": TopicAnchor(
        topic_id="ftc_noncompete",
        label="FTC healthcare-noncompete enforcement",
        keywords=[
            "noncompete", "non-compete", "restrictive covenant",
            "ftc", "federal trade commission",
            "physician mobility", "labor mobility",
        ],
        ebitda_sensitivity=0.06,    # ~6% EBITDA at risk
        applicable_sectors=[
            "physician_group", "mso", "dental", "dermatology",
            "ophthalmology", "behavioral_health", "managed_care",
        ],
    ),
    "state_con_cpom": TopicAnchor(
        topic_id="state_con_cpom",
        label="State CON/CPOM legislative wave",
        keywords=[
            "certificate of need", "con repeal", "corporate practice",
            "cpom", "private equity ownership", "transaction review",
            "material change", "transaction notification",
        ],
        ebitda_sensitivity=0.04,
        applicable_sectors=[
            "hospital", "physician_group", "mso", "asc",
            "behavioral_health",
        ],
    ),
    "site_neutral": TopicAnchor(
        topic_id="site_neutral",
        label="CY2026 OPPS site-neutral payment expansion",
        keywords=[
            "site-neutral", "site neutral", "opps", "outpatient prospective",
            "off-campus", "provider-based", "hospital outpatient",
        ],
        ebitda_sensitivity=0.08,
        applicable_sectors=["hospital", "asc", "imaging"],
    ),
    "v28_risk_cliff": TopicAnchor(
        topic_id="v28_risk_cliff",
        label="ACO REACH PY2026 V28 risk-coding cliff",
        keywords=[
            "v28", "risk adjustment", "hcc", "coding intensity",
            "aco reach", "direct contracting", "ma star",
            "medicare advantage", "risk score", "lead model",
        ],
        ebitda_sensitivity=0.10,
        applicable_sectors=["managed_care", "physician_group", "mso"],
    ),
    "stark_kickback": TopicAnchor(
        topic_id="stark_kickback",
        label="Stark/AKS enforcement",
        keywords=[
            "anti-kickback", "stark", "self-referral", "fmv",
            "fair market value", "physician compensation",
        ],
        ebitda_sensitivity=0.05,
        applicable_sectors=[
            "hospital", "physician_group", "mso", "dental",
            "radiology", "lab", "asc",
        ],
    ),
    "rate_review": TopicAnchor(
        topic_id="rate_review",
        label="State Medicaid rate review / cuts",
        keywords=[
            "medicaid rate", "rate cut", "fee schedule",
            "managed care organization", "mco directed payment",
            "supplemental payment",
        ],
        ebitda_sensitivity=0.07,
        applicable_sectors=[
            "hospital", "behavioral_health", "skilled_nursing",
            "home_health", "managed_care",
        ],
    ),
}


@dataclass
class TopicMatch:
    topic_id: str
    label: str
    relevance: float                # 0-1 overlap-weighted score
    matched_keywords: List[str] = field(default_factory=list)


def classify_document_topics(
    text: str,
    *,
    tfidf_scores: Optional[Dict[str, float]] = None,
    min_relevance: float = 0.05,
) -> List[TopicMatch]:
    """Run topic-anchor overlap scoring on a document.

    Each topic gets a relevance score = (matched anchor terms /
    total anchor terms), optionally weighted by TF-IDF if scores
    for the document are passed in.

    Returns matches above ``min_relevance`` ordered by relevance
    descending.
    """
    if not text:
        return []
    tokens = set(tokenize(text))
    text_lower = text.lower()
    matches: List[TopicMatch] = []

    for topic in TOPIC_ANCHORS.values():
        # Multi-word phrases are matched against the lowercased
        # text; single-word anchors against the token set.
        hit_keywords: List[str] = []
        for kw in topic.keywords:
            kw_low = kw.lower()
            if " " in kw_low or "-" in kw_low:
                if kw_low in text_lower:
                    hit_keywords.append(kw)
            else:
                if kw_low in tokens:
                    hit_keywords.append(kw)
        if not hit_keywords:
            continue

        base_relevance = len(hit_keywords) / len(topic.keywords)

        # If TF-IDF scores are available, scale the relevance by the
        # average TF-IDF of the matched single-word terms — captures
        # how DISTINCTIVE the topic is in the doc.
        if tfidf_scores:
            single_words = [
                k.lower() for k in hit_keywords
                if " " not in k and "-" not in k
            ]
            if single_words:
                tfidf_avg = sum(tfidf_scores.get(w, 0.0)
                                for w in single_words) / len(single_words)
                # Cap the boost so high TF-IDF doesn't dominate
                base_relevance = base_relevance * (1.0 + min(2.0, tfidf_avg * 10))

        if base_relevance < min_relevance:
            continue

        matches.append(TopicMatch(
            topic_id=topic.topic_id,
            label=topic.label,
            relevance=round(min(1.0, base_relevance), 4),
            matched_keywords=hit_keywords,
        ))

    matches.sort(key=lambda m: m.relevance, reverse=True)
    return matches
