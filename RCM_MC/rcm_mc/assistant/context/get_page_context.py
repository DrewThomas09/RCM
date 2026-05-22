"""Resolve a (possibly messy or dynamic) route to a PageContext.

Read-only lookup. Handles query strings, hash fragments, trailing
slashes, palette aliases, and parameterized dynamic routes
(/deal/<id>, /analysis/<id>, /portal/<id>, and deal sub-pages).
"""
from __future__ import annotations

import re
from typing import Callable, Dict, List, Optional, Tuple

from .discovered_tool_routes import DISCOVERED_TOOL_ROUTES
from .page_context_registry import PAGE_CONTEXT_REGISTRY
from .types import (
    DataConfidence,
    PageContext,
    PageContextCategory,
    PageContextLookupResult,
    SourceConfidence,
)

_FALLBACK = "No PEdesk Guide context has been documented for this page yet."

_DYNAMIC_NOTES = [
    "PEdesk Guide is read-only and explanatory — it never runs models, "
    "changes assumptions, or makes investment recommendations.",
    "This is a generic per-entity context; the specific entity id in the "
    "URL identifies the deal/engagement, not a different page type.",
    "Do not invent formulas, data lineage, or model mechanics; defer to "
    "source documentation for specifics.",
]


def normalize_route(route: str) -> str:
    """Strip query string + hash fragment and normalize trailing slash."""
    r = (route or "").strip()
    r = r.split("?", 1)[0].split("#", 1)[0]
    if len(r) > 1 and r.endswith("/"):
        r = r.rstrip("/")
    return r or "/"


# alias (normalized) -> canonical discovered route
def _build_alias_index() -> Dict[str, str]:
    idx: Dict[str, str] = {}
    for d in DISCOVERED_TOOL_ROUTES:
        for alias in d.aliases or []:
            idx[normalize_route(alias)] = d.route
    return idx


_ALIAS_INDEX = _build_alias_index()


def _dyn(route: str, title: str, category: PageContextCategory,
         short: str, purpose: str, related: List[str],
         users: Optional[List[str]] = None) -> PageContext:
    return PageContext(
        route=route,
        normalized_route=route,
        title=title,
        category=category,
        short_description=short,
        primary_purpose=purpose,
        intended_users=users or ["PE deal team reviewing this entity."],
        common_questions=[f"What does {title} show?",
                          "Where does its data come from?"],
        inputs=["The entity id in the route (deal / engagement)."],
        outputs=["Needs source documentation."],
        key_metrics=["Needs source documentation."],
        data_sources=["Needs source documentation."],
        model_logic_summary="Needs source documentation.",
        why_it_matters=purpose,
        diligence_use_cases=["Needs source documentation."],
        interpretation_guidance=[
            "This is a per-entity view; figures refer to the specific "
            "deal/engagement in the URL.",
        ],
        limitations=["Generic context — page specifics need source "
                     "documentation."],
        related_routes=related,
        source_confidence=SourceConfidence.INFERRED_FROM_ROUTE,
        data_confidence=DataConfidence.UNKNOWN,
        notes_for_assistant=list(_DYNAMIC_NOTES),
        last_reviewed_at="2026-05-22",
        owner="pedesk-guide",
    )


# (compiled pattern, builder(normalized_route) -> PageContext)
# Most specific patterns FIRST.
_DYNAMIC_ROUTES: List[Tuple[re.Pattern, Callable[[str], PageContext]]] = [
    (re.compile(r"^/deal/[^/]+/partner-review$"),
     lambda r: _dyn(r, "Partner Review", PageContextCategory.DILIGENCE_WORKSPACE,
                    "Partner-level review view for a single deal.",
                    "Give a partner the consolidated review of one deal's "
                    "diligence.",
                    ["/diligence/deal", "/diligence/ic-packet"])),
    (re.compile(r"^/deal/[^/]+/ic-packet$"),
     lambda r: _dyn(r, "Deal IC Packet", PageContextCategory.DILIGENCE_WORKSPACE,
                    "The investment-committee packet for a single deal.",
                    "Present the IC-ready deliverable for this deal.",
                    ["/diligence/ic-packet", "/diligence/deal"])),
    (re.compile(r"^/deal/[^/]+/red-flags$"),
     lambda r: _dyn(r, "Deal Red Flags", PageContextCategory.DILIGENCE_WORKSPACE,
                    "Red-flag summary for a single deal.",
                    "Surface the deal's flagged risks in one place.",
                    ["/bear-cases", "/diligence/risk-workbench"])),
    (re.compile(r"^/deal/[^/]+$"),
     lambda r: _dyn(r, "Deal Dashboard", PageContextCategory.DILIGENCE_WORKSPACE,
                    "The hub for a single deal — every analysis on it in "
                    "one place.",
                    "Orient on one deal and launch into its analyses.",
                    ["/diligence/deal", "/analysis/<dealId>", "/pipeline"])),
    (re.compile(r"^/analysis/[^/]+$"),
     lambda r: _dyn(r, "Analysis Workbench", PageContextCategory.DILIGENCE_WORKSPACE,
                    "The Bloomberg-style analysis workbench for a single "
                    "deal.",
                    "Work through a deal's full analytical packet.",
                    ["/diligence/deal", "/diligence/ic-packet"])),
    (re.compile(r"^/portal/[^/]+$"),
     lambda r: _dyn(r, "Engagement Portal", PageContextCategory.UNKNOWN,
                    "Client-facing portal for a single engagement.",
                    "Provide an engagement-scoped portal view.",
                    ["/engagements"],
                    users=["Engagement stakeholders / client-facing users."])),
]


def get_page_context(route: str) -> PageContextLookupResult:
    """Resolve ``route`` to a PageContextLookupResult (read-only)."""
    normalized = normalize_route(route)

    # 1. exact match
    ctx = PAGE_CONTEXT_REGISTRY.get(normalized)
    if ctx is not None:
        return PageContextLookupResult(True, route, normalized, ctx, None)

    # 2. alias -> canonical
    canonical = _ALIAS_INDEX.get(normalized)
    if canonical and canonical in PAGE_CONTEXT_REGISTRY:
        return PageContextLookupResult(
            True, route, normalized, PAGE_CONTEXT_REGISTRY[canonical], None
        )

    # 3. dynamic parameterized routes (most-specific first)
    for pattern, builder in _DYNAMIC_ROUTES:
        if pattern.match(normalized):
            return PageContextLookupResult(
                True, route, normalized, builder(normalized), None
            )

    # 4. clean fallback
    return PageContextLookupResult(
        False, route, normalized, None, _FALLBACK
    )
