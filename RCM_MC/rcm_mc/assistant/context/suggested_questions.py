"""Deterministic suggested-question generator for the PEdesk Guide.

No AI, no generation — pure Python. Given a PageContext, return 5-8
useful starter questions: five sensible defaults plus page-specific
additions keyed off the page's category and whether it carries data
sources. The future Guide assistant uses these as clickable prompts;
they are NOT answers and carry no behavior.
"""
from __future__ import annotations

from typing import List, Optional

from .types import PageContext, PageContextCategory

_NEEDS = "Needs source documentation."

_MAX_QUESTIONS = 8

# Always-present defaults (5).
_DEFAULTS: List[str] = [
    "What does this page do?",
    "Where does this data come from?",
    "Which numbers matter most?",
    "How should I interpret this?",
    "What are the limitations?",
]

_CATEGORY_QUESTIONS = {
    PageContextCategory.DILIGENCE_WORKSPACE: [
        "What should I be careful about before using this in IC?",
        "Which diligence questions does this page raise?",
    ],
    PageContextCategory.PORTFOLIO_LP: [
        "What does this say about portfolio risk?",
        "What would a partner want to know from this page?",
    ],
    PageContextCategory.LIBRARY_REFERENCE: [
        "How does this methodology support diligence?",
        "Which pages use this definition?",
    ],
}

_DATA_SOURCE_QUESTIONS = [
    "Which data sources feed this page?",
    "Is this observed, estimated, benchmarked, or unknown?",
]


def _has_data_sources(page_context: PageContext) -> bool:
    if getattr(page_context, "data_source_ids", None):
        return True
    return any(
        ds and ds != _NEEDS for ds in (page_context.data_sources or [])
    )


def get_suggested_questions_for_page(
    page_context: Optional[PageContext],
) -> List[str]:
    """Return 5-8 starter questions for ``page_context`` (deterministic).

    Defaults always appear first; page-specific questions are appended
    based on category and whether the page carries data sources, capped
    at eight and de-duplicated in priority order.
    """
    questions: List[str] = list(_DEFAULTS)
    if page_context is None:
        return questions

    extras: List[str] = list(
        _CATEGORY_QUESTIONS.get(page_context.category, [])
    )
    if _has_data_sources(page_context):
        extras += _DATA_SOURCE_QUESTIONS

    for q in extras:
        if len(questions) >= _MAX_QUESTIONS:
            break
        if q not in questions:
            questions.append(q)

    return questions
