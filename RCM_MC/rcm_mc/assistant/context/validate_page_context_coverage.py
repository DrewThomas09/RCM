"""Validate PageContext coverage of the discovered route manifest.

Run:
    .venv/bin/python -m rcm_mc.assistant.context.validate_page_context_coverage

Reports coverage + structural integrity and exits non-zero on any HARD
failure. A page saying "Needs source documentation." (a placeholder) is
NOT a failure — that is allowed in the first complete coverage pass.
"""
from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass, field
from typing import List

from .discovered_tool_routes import DISCOVERED_TOOL_ROUTES
from .manual_page_contexts import MANUAL_PAGE_CONTEXTS
from .page_context_registry import (
    PAGE_CONTEXT_REGISTRY,
    PLACEHOLDER_PAGE_CONTEXTS,
)
from .types import (
    VALID_CATEGORIES,
    VALID_DATA_CONFIDENCE,
    VALID_SOURCE_CONFIDENCE,
)


@dataclass
class Report:
    total_discovered: int = 0
    total_registry: int = 0
    documented: int = 0
    placeholder: int = 0
    missing: List[str] = field(default_factory=list)
    duplicate_routes: List[str] = field(default_factory=list)
    invalid_categories: List[str] = field(default_factory=list)
    invalid_source_confidence: List[str] = field(default_factory=list)
    invalid_data_confidence: List[str] = field(default_factory=list)
    missing_titles: List[str] = field(default_factory=list)
    missing_normalized: List[str] = field(default_factory=list)
    manual_not_discovered: List[str] = field(default_factory=list)

    @property
    def hard_failures(self) -> List[str]:
        problems = []
        if self.missing:
            problems.append(f"{len(self.missing)} discovered route(s) missing from registry")
        if self.duplicate_routes:
            problems.append(f"{len(self.duplicate_routes)} duplicate route(s)")
        if self.invalid_categories:
            problems.append(f"{len(self.invalid_categories)} invalid category value(s)")
        if self.invalid_source_confidence:
            problems.append(f"{len(self.invalid_source_confidence)} invalid sourceConfidence value(s)")
        if self.invalid_data_confidence:
            problems.append(f"{len(self.invalid_data_confidence)} invalid dataConfidence value(s)")
        if self.missing_titles:
            problems.append(f"{len(self.missing_titles)} missing title(s)")
        if self.missing_normalized:
            problems.append(f"{len(self.missing_normalized)} missing normalizedRoute(s)")
        return problems


def build_report() -> Report:
    r = Report()
    discovered_routes = [d.route for d in DISCOVERED_TOOL_ROUTES]
    r.total_discovered = len(discovered_routes)
    r.total_registry = len(PAGE_CONTEXT_REGISTRY)

    # duplicate discovered routes (ambiguity)
    dup = [route for route, n in Counter(discovered_routes).items() if n > 1]
    r.duplicate_routes = sorted(dup)

    # every discovered route must be in the registry
    r.missing = sorted(rt for rt in discovered_routes
                       if rt not in PAGE_CONTEXT_REGISTRY)

    # structural integrity of every registry entry
    for route, ctx in PAGE_CONTEXT_REGISTRY.items():
        cat = getattr(ctx.category, "value", ctx.category)
        if cat not in VALID_CATEGORIES:
            r.invalid_categories.append(route)
        sc = getattr(ctx.source_confidence, "value", ctx.source_confidence)
        if sc not in VALID_SOURCE_CONFIDENCE:
            r.invalid_source_confidence.append(route)
        dc = getattr(ctx.data_confidence, "value", ctx.data_confidence)
        if dc not in VALID_DATA_CONFIDENCE:
            r.invalid_data_confidence.append(route)
        if not (ctx.title or "").strip():
            r.missing_titles.append(route)
        if not (ctx.normalized_route or "").strip():
            r.missing_normalized.append(route)

    r.placeholder = len(PLACEHOLDER_PAGE_CONTEXTS)
    r.documented = r.total_registry - r.placeholder

    # manual contexts pointing at a route that was never discovered
    discovered_set = set(discovered_routes)
    r.manual_not_discovered = sorted(
        rt for rt in MANUAL_PAGE_CONTEXTS if rt not in discovered_set
    )
    return r


def print_report(r: Report) -> None:
    print("PEdesk Guide — PageContext coverage report")
    print("=" * 56)
    print(f"  discovered routes ............ {r.total_discovered}")
    print(f"  registry entries ............. {r.total_registry}")
    print(f"  documented contexts .......... {r.documented}")
    print(f"  placeholder contexts ......... {r.placeholder}")
    print(f"  missing contexts ............. {len(r.missing)}")
    print(f"  duplicate routes ............. {len(r.duplicate_routes)}")
    print(f"  invalid categories ........... {len(r.invalid_categories)}")
    print(f"  invalid sourceConfidence ..... {len(r.invalid_source_confidence)}")
    print(f"  invalid dataConfidence ....... {len(r.invalid_data_confidence)}")
    print(f"  missing titles ............... {len(r.missing_titles)}")
    print(f"  missing normalizedRoutes ..... {len(r.missing_normalized)}")
    print(f"  manual route not discovered .. {len(r.manual_not_discovered)} "
          f"(advisory)")
    if r.missing:
        print("\n  MISSING:", ", ".join(r.missing[:20]))
    if r.duplicate_routes:
        print("\n  DUPLICATES:", ", ".join(r.duplicate_routes))
    if r.manual_not_discovered:
        print("\n  manual-but-not-discovered (advisory only):",
              ", ".join(r.manual_not_discovered))


def main() -> int:
    r = build_report()
    print_report(r)
    fails = r.hard_failures
    if fails:
        print("\nFAIL:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("\nPASS — every discovered route has a valid context entry.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
