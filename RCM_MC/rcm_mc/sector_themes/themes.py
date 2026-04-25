"""Theme-anchored matching — fixed-taxonomy mode.

For partners who already know the four named themes (and don't
want to wait for LDA to discover them), this module ships
hand-curated keyword anchors and a deal-scoring function.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..regulatory.tfidf import tokenize


@dataclass
class ThemeAnchor:
    theme_id: str
    label: str
    keywords: List[str]
    sector_tags: List[str] = field(default_factory=list)


THEME_ANCHORS: Dict[str, ThemeAnchor] = {
    "glp1_specialty_pharmacy": ThemeAnchor(
        theme_id="glp1_specialty_pharmacy",
        label="GLP-1 specialty pharmacy",
        keywords=[
            "glp-1", "glp1", "ozempic", "wegovy", "mounjaro",
            "zepbound", "semaglutide", "tirzepatide",
            "specialty pharmacy", "compounding pharmacy",
            "weight loss", "obesity",
        ],
        sector_tags=["pharmacy", "specialty_pharmacy"],
    ),
    "hybrid_care_platforms": ThemeAnchor(
        theme_id="hybrid_care_platforms",
        label="Hybrid (in-person + virtual) care",
        keywords=[
            "hybrid care", "hybrid-care", "telehealth",
            "virtual visit", "virtual care", "remote monitoring",
            "asynchronous visit", "omnichannel care",
            "tele-mental health",
        ],
        sector_tags=["primary_care", "behavioral_health"],
    ),
    "ai_enabled_rcm": ThemeAnchor(
        theme_id="ai_enabled_rcm",
        label="AI-enabled RCM (revenue cycle)",
        keywords=[
            "revenue cycle", "rcm", "denial management",
            "ai-enabled", "ai-powered", "machine learning",
            "claim automation", "denials prevention",
            "computer-assisted coding", "cac",
        ],
        sector_tags=["healthcare_it"],
    ),
    "ma_star_arbitrage": ThemeAnchor(
        theme_id="ma_star_arbitrage",
        label="MA Star-rating arbitrage",
        keywords=[
            "medicare advantage", "star rating", "stars rating",
            "quality bonus", "qbp", "ma plan",
            "star measure", "cms quality",
        ],
        sector_tags=["managed_care"],
    ),
    "value_based_primary_care": ThemeAnchor(
        theme_id="value_based_primary_care",
        label="Value-based primary care",
        keywords=[
            "value-based", "value based", "capitated",
            "global capitation", "primary care", "aco reach",
            "msso", "direct contracting", "delegated risk",
        ],
        sector_tags=["primary_care", "managed_care"],
    ),
    "behavioral_health_consolidation": ThemeAnchor(
        theme_id="behavioral_health_consolidation",
        label="Behavioral health consolidation",
        keywords=[
            "behavioral health", "mental health", "addiction",
            "substance use", "psychiatric", "therapy network",
            "outpatient mental health",
        ],
        sector_tags=["behavioral_health"],
    ),
}


@dataclass
class ThemeMatch:
    theme_id: str
    label: str
    score: float                # 0-1 keyword density
    matched_keywords: List[str]


def score_deal_against_themes(
    text: str,
    *,
    custom_anchors: Optional[Dict[str, ThemeAnchor]] = None,
    min_score: float = 0.05,
) -> List[ThemeMatch]:
    """Score a single deal description against every theme.

    Returns only matches with score ≥ ``min_score``, sorted
    descending. Score = matched_anchor_count / total_anchor_count
    for the theme.
    """
    if not text:
        return []
    tokens = set(tokenize(text))
    text_lower = text.lower()

    anchors = dict(THEME_ANCHORS)
    if custom_anchors:
        anchors.update(custom_anchors)

    out: List[ThemeMatch] = []
    for theme in anchors.values():
        hits: List[str] = []
        for kw in theme.keywords:
            kw_low = kw.lower()
            if " " in kw_low or "-" in kw_low:
                if kw_low in text_lower:
                    hits.append(kw)
            else:
                if kw_low in tokens:
                    hits.append(kw)
        if not hits:
            continue
        score = len(hits) / len(theme.keywords)
        if score < min_score:
            continue
        out.append(ThemeMatch(
            theme_id=theme.theme_id,
            label=theme.label,
            score=round(score, 4),
            matched_keywords=hits,
        ))
    out.sort(key=lambda m: m.score, reverse=True)
    return out
