"""Generated placeholder PageContext stubs — one per discovered route.

Every discovered route gets a context entry so nothing is ever missing.
Where a page is not yet documented, the stub is an explicit placeholder
(``needs_validation`` / ``unknown``) that tells the assistant NOT to
invent formulas, data lineage, or model mechanics. Manual high-quality
contexts (manual_page_contexts.py) override these in the registry.
"""
from __future__ import annotations

from typing import Dict

from .discovered_tool_routes import DISCOVERED_TOOL_ROUTES
from .types import (
    DataConfidence,
    PageContext,
    SourceConfidence,
)

_PLACEHOLDER = "Needs source documentation."

_STUB_NOTES = [
    "This page has a placeholder context entry.",
    "Do not invent formulas, data lineage, or model mechanics.",
    "Tell the user this page needs source documentation if asked for specifics.",
]


def _stub_for(route: str, title: str, category) -> PageContext:
    return PageContext(
        route=route,
        normalized_route=route,
        title=title,
        category=category,
        short_description=_PLACEHOLDER,
        primary_purpose=_PLACEHOLDER,
        intended_users=["Needs source documentation."],
        common_questions=["What does this page do?"],
        inputs=[_PLACEHOLDER],
        outputs=[_PLACEHOLDER],
        key_metrics=[_PLACEHOLDER],
        data_sources=[_PLACEHOLDER],
        model_logic_summary=_PLACEHOLDER,
        why_it_matters=_PLACEHOLDER,
        diligence_use_cases=[_PLACEHOLDER],
        interpretation_guidance=[_PLACEHOLDER],
        limitations=[_PLACEHOLDER],
        related_routes=[],
        source_confidence=SourceConfidence.NEEDS_VALIDATION,
        data_confidence=DataConfidence.UNKNOWN,
        notes_for_assistant=list(_STUB_NOTES),
        last_reviewed_at=None,
        owner=None,
    )


def build_generated_stubs() -> Dict[str, PageContext]:
    """One placeholder PageContext per discovered route, keyed by route."""
    out: Dict[str, PageContext] = {}
    for d in DISCOVERED_TOOL_ROUTES:
        out[d.route] = _stub_for(d.route, d.title, d.category)
    return out


GENERATED_PAGE_CONTEXT_STUBS: Dict[str, PageContext] = build_generated_stubs()
