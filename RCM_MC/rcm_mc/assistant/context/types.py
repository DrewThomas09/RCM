"""Type definitions for the PEdesk Guide page-context layer.

Python adaptation of the TypeScript spec (this codebase is pure Python —
stdlib HTTP server, no Node/TS toolchain). Enums replace the string
union types; frozen-ish dataclasses replace the TS interfaces.

This layer is READ-ONLY and explanatory. It carries no behavior — no
model execution, no data mutation, no actions. It only describes pages
so a future PEdesk Guide assistant can explain them conservatively.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class PageContextCategory(str, Enum):
    """The seven PEdesk tool groups (mirrors the Tools / Cmd+K palette
    section headers), plus an explicit ``unknown`` fallback."""

    HOME_OPERATIONS = "home_operations"
    PIPELINE_SOURCING = "pipeline_sourcing"
    DILIGENCE_WORKSPACE = "diligence_workspace"
    LIBRARY_REFERENCE = "library_reference"
    RESEARCH_BACKTESTING = "research_backtesting"
    PORTFOLIO_LP = "portfolio_lp"
    ADMIN_SYSTEM = "admin_system"
    UNKNOWN = "unknown"


class SourceConfidence(str, Enum):
    """How the page's *description* was established."""

    DOCUMENTED = "documented"
    INFERRED_FROM_ROUTE = "inferred_from_route"
    INFERRED_FROM_PAGE = "inferred_from_page"
    NEEDS_VALIDATION = "needs_validation"


class DataConfidence(str, Enum):
    """What kind of data the page actually shows (critical for honest
    explanation — e.g. live target data vs an illustrative template)."""

    OBSERVED_TARGET_DATA = "observed_target_data"
    PUBLIC_BENCHMARK_DATA = "public_benchmark_data"
    USER_ENTERED_DATA = "user_entered_data"
    MODEL_ESTIMATE = "model_estimate"
    DEMO_OR_FIXTURE = "demo_or_fixture"
    MIXED = "mixed"
    UNKNOWN = "unknown"


# Convenience sets for the validator (string values of each enum).
VALID_CATEGORIES = {c.value for c in PageContextCategory}
VALID_SOURCE_CONFIDENCE = {c.value for c in SourceConfidence}
VALID_DATA_CONFIDENCE = {c.value for c in DataConfidence}


@dataclass
class ToolRouteDefinition:
    """One discovered tool/page route (normalized, de-duplicated)."""

    title: str
    route: str
    category: PageContextCategory
    source_group: str
    is_auto_generated: bool = False
    aliases: List[str] = field(default_factory=list)
    source_file: Optional[str] = None


@dataclass
class PageContext:
    """Conservative, read-only explanation of a single PEdesk page."""

    route: str
    normalized_route: str
    title: str
    category: PageContextCategory
    short_description: str
    primary_purpose: str
    intended_users: List[str]
    common_questions: List[str]
    inputs: List[str]
    outputs: List[str]
    key_metrics: List[str]
    data_sources: List[str]
    model_logic_summary: str
    why_it_matters: str
    diligence_use_cases: List[str]
    interpretation_guidance: List[str]
    limitations: List[str]
    related_routes: List[str]
    source_confidence: SourceConfidence
    data_confidence: DataConfidence
    notes_for_assistant: List[str]
    last_reviewed_at: Optional[str] = None
    owner: Optional[str] = None


# A registry maps normalized_route -> PageContext.
PageContextRegistry = Dict[str, PageContext]


@dataclass
class PageContextLookupResult:
    """Result of resolving a (possibly messy / dynamic) route."""

    found: bool
    route: str
    normalized_route: str
    context: Optional[PageContext] = None
    fallback_message: Optional[str] = None
