"""Validate PEdesk Guide context quality (pages + metrics + data sources).

Run:
    .venv/bin/python -m rcm_mc.assistant.context.validate_guide_context_quality

Reports coverage/quality signals and exits non-zero ONLY on hard
integrity failures:
  - a page references a metric id not in the metric registry
  - a page references a data-source id not in the data-source registry
  - duplicate metric ids
  - duplicate data-source ids
  - broken lookup aliases (an alias claimed by >1 entry, i.e. ambiguous)

It does NOT fail because a formula needs validation or a page still says
"Needs source documentation." — those are allowed.
"""
from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass, field
from typing import List

from .data_source_registry import DATA_SOURCE_REGISTRY, _SOURCES
from .get_data_source_context import _norm as _norm_src
from .get_metric_context import _norm as _norm_metric
from .metric_registry import METRIC_REGISTRY, _METRICS
from .page_context_registry import PAGE_CONTEXT_REGISTRY
from .manual_page_contexts import MANUAL_PAGE_CONTEXTS

_NEEDS = "Needs source documentation."


@dataclass
class QualityReport:
    total_pages: int = 0
    total_metrics: int = 0
    total_data_sources: int = 0
    pages_no_key_metrics: List[str] = field(default_factory=list)
    pages_no_data_sources: List[str] = field(default_factory=list)
    manual_still_placeholder: List[str] = field(default_factory=list)
    metrics_needs_validation: List[str] = field(default_factory=list)
    sources_needs_validation: List[str] = field(default_factory=list)
    invalid_metric_refs: List[str] = field(default_factory=list)
    invalid_source_refs: List[str] = field(default_factory=list)
    duplicate_metric_ids: List[str] = field(default_factory=list)
    duplicate_source_ids: List[str] = field(default_factory=list)
    broken_aliases: List[str] = field(default_factory=list)

    @property
    def hard_failures(self) -> List[str]:
        out = []
        if self.invalid_metric_refs:
            out.append(f"{len(self.invalid_metric_refs)} invalid metric id ref(s) on pages")
        if self.invalid_source_refs:
            out.append(f"{len(self.invalid_source_refs)} invalid data-source id ref(s) on pages")
        if self.duplicate_metric_ids:
            out.append(f"{len(self.duplicate_metric_ids)} duplicate metric id(s)")
        if self.duplicate_source_ids:
            out.append(f"{len(self.duplicate_source_ids)} duplicate data-source id(s)")
        if self.broken_aliases:
            out.append(f"{len(self.broken_aliases)} broken/ambiguous alias(es)")
        return out


def _all_placeholder(values: List[str]) -> bool:
    return (not values) or all((v or "").strip() == _NEEDS for v in values)


def _alias_collisions(entries, id_attr: str, norm) -> List[str]:
    """Aliases (or labels) normalized to the same key by two different
    entries — ambiguous, so the lookup index would silently drop one."""
    claims: dict = {}
    for e in entries:
        eid = getattr(e, id_attr)
        keys = {norm(eid), norm(e.label)} | {norm(a) for a in e.aliases}
        for k in keys:
            claims.setdefault(k, set()).add(eid)
    return sorted(k for k, ids in claims.items() if len(ids) > 1)


def build_report() -> QualityReport:
    r = QualityReport()
    r.total_pages = len(PAGE_CONTEXT_REGISTRY)
    r.total_metrics = len(METRIC_REGISTRY)
    r.total_data_sources = len(DATA_SOURCE_REGISTRY)

    for route, ctx in PAGE_CONTEXT_REGISTRY.items():
        if _all_placeholder(ctx.key_metrics):
            r.pages_no_key_metrics.append(route)
        if _all_placeholder(ctx.data_sources):
            r.pages_no_data_sources.append(route)
        for mid in ctx.metric_ids:
            if mid not in METRIC_REGISTRY:
                r.invalid_metric_refs.append(f"{route} -> {mid}")
        for sid in ctx.data_source_ids:
            if sid not in DATA_SOURCE_REGISTRY:
                r.invalid_source_refs.append(f"{route} -> {sid}")

    for route in MANUAL_PAGE_CONTEXTS:
        ctx = PAGE_CONTEXT_REGISTRY[route]
        if _NEEDS in (
            [ctx.short_description, ctx.primary_purpose, ctx.model_logic_summary,
             ctx.why_it_matters]
        ):
            r.manual_still_placeholder.append(route)

    r.metrics_needs_validation = sorted(
        mid for mid, m in METRIC_REGISTRY.items()
        if m.formula_confidence.value == "needs_validation"
    )
    r.sources_needs_validation = sorted(
        sid for sid, s in DATA_SOURCE_REGISTRY.items()
        if s.source_confidence.value == "needs_validation"
    )

    # duplicates (in the source-of-truth lists, before dict de-dup)
    r.duplicate_metric_ids = sorted(
        mid for mid, n in Counter(m.metric_id for m in _METRICS).items() if n > 1
    )
    r.duplicate_source_ids = sorted(
        sid for sid, n in Counter(s.source_id for s in _SOURCES).items() if n > 1
    )

    # ambiguous aliases in either registry
    r.broken_aliases = (
        [f"metric:{k}" for k in _alias_collisions(_METRICS, "metric_id", _norm_metric)]
        + [f"source:{k}" for k in _alias_collisions(_SOURCES, "source_id", _norm_src)]
    )
    return r


def print_report(r: QualityReport) -> None:
    print("PEdesk Guide — context quality report")
    print("=" * 56)
    print(f"  page contexts ................ {r.total_pages}")
    print(f"  metric contexts .............. {r.total_metrics}")
    print(f"  data source contexts ......... {r.total_data_sources}")
    print(f"  pages w/ no key metrics ...... {len(r.pages_no_key_metrics)} (advisory)")
    print(f"  pages w/ no data sources ..... {len(r.pages_no_data_sources)} (advisory)")
    print(f"  manual still placeholder ..... {len(r.manual_still_placeholder)} (advisory)")
    print(f"  metrics needs_validation ..... {len(r.metrics_needs_validation)} (allowed)")
    print(f"  sources needs_validation ..... {len(r.sources_needs_validation)} (allowed)")
    print(f"  invalid metric refs .......... {len(r.invalid_metric_refs)}")
    print(f"  invalid data-source refs ..... {len(r.invalid_source_refs)}")
    print(f"  duplicate metric ids ......... {len(r.duplicate_metric_ids)}")
    print(f"  duplicate data-source ids .... {len(r.duplicate_source_ids)}")
    print(f"  broken/ambiguous aliases ..... {len(r.broken_aliases)}")
    for label, items in [
        ("invalid metric refs", r.invalid_metric_refs),
        ("invalid data-source refs", r.invalid_source_refs),
        ("duplicate metric ids", r.duplicate_metric_ids),
        ("duplicate data-source ids", r.duplicate_source_ids),
        ("broken aliases", r.broken_aliases),
    ]:
        if items:
            print(f"\n  {label}: {', '.join(items[:20])}")


def main() -> int:
    r = build_report()
    print_report(r)
    fails = r.hard_failures
    if fails:
        print("\nFAIL:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("\nPASS — metric/data-source references and registries are consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
