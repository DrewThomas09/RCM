"""The merged PageContext registry.

Generated placeholder stubs (one per discovered route) overlaid with
hand-written manual contexts (manual wins). Guarantees every discovered
route has an entry.
"""
from __future__ import annotations

from typing import Dict, List

from .discovered_tool_routes import DISCOVERED_TOOL_ROUTES
from .generated_page_context_stubs import GENERATED_PAGE_CONTEXT_STUBS
from .manual_page_contexts import MANUAL_PAGE_CONTEXTS
from .types import PageContext, SourceConfidence


def _build_registry() -> Dict[str, PageContext]:
    registry: Dict[str, PageContext] = {}
    # 0. honest placeholder for every SERVED route absent from the palette
    #    (so the Guide is never empty for a served page; tells the assistant
    #    not to invent specifics). Overridden by palette stubs + manual below.
    try:
        from .served_route_stubs import SERVED_ROUTE_STUBS
        registry.update(SERVED_ROUTE_STUBS)
    except Exception:
        pass
    # 1. stub for every discovered (palette) route
    registry.update(GENERATED_PAGE_CONTEXT_STUBS)
    # 2. manual contexts override stubs
    registry.update(MANUAL_PAGE_CONTEXTS)
    return registry


PAGE_CONTEXT_REGISTRY: Dict[str, PageContext] = _build_registry()


def _is_placeholder(ctx: PageContext) -> bool:
    return ctx.source_confidence == SourceConfidence.NEEDS_VALIDATION


ALL_PAGE_CONTEXTS: List[PageContext] = list(PAGE_CONTEXT_REGISTRY.values())
PLACEHOLDER_PAGE_CONTEXTS: List[PageContext] = [
    c for c in ALL_PAGE_CONTEXTS if _is_placeholder(c)
]
DOCUMENTED_PAGE_CONTEXTS: List[PageContext] = [
    c for c in ALL_PAGE_CONTEXTS if not _is_placeholder(c)
]
