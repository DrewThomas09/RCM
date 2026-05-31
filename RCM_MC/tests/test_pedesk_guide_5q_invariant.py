"""Invariant — every partner-facing PageContext has 5+ common_questions.

The 2026-05-29/30 loop sprint (PRs #1197-#1216) bumped ~138 pages'
``common_questions`` from 3-4 entries to 5+, so the Ollama Guide
could answer the partner follow-up that usually comes after the
obvious one (method nuance + sibling-route distinction). This test
locks the floor in: any new ``_ctx(...)`` or ``_BATCH*``/``_PE_TOOLS*``
tuple that lands with fewer than 5 questions fails CI.

Explicitly allow-listed exceptions are leaf "data dump" endpoints
(``.csv`` exports and a licensed-asset leaf) where 5 partner-voice
questions add no value beyond their existing pair. The allowlist
should NOT grow casually — new entries need a justification
comment.

This test is a static-source / runtime check (no server, no DB).
"""
from __future__ import annotations

import unittest

from rcm_mc.assistant.context.data_source_registry import (
    DATA_SOURCE_REGISTRY,
)
from rcm_mc.assistant.context.manual_page_contexts import (
    MANUAL_PAGE_CONTEXTS,
)
from rcm_mc.assistant.context.metric_registry import METRIC_REGISTRY


# Leaf endpoints where the Guide-context is intentionally short
# because the surface is a download or single-purpose licensed
# asset, not a partner-facing analytic page. New entries here need
# a justification comment.
_SHORT_OK = {
    # .csv data dumps — answered by "what's in this file / what format"
    "/county-explorer.csv",
    "/metro-markets.csv",
    "/state-compare.csv",
    "/state-peers.csv",
    "/state-profile.csv",
    "/state-rankings.csv",
    "/target-screener.csv",
    # Licensed leaf-asset embed; the page itself is a thin viewer.
    "/market-intel/seeking-alpha",
}

_MIN_QUESTIONS = 5


class TestPartnerQuestionsFloor(unittest.TestCase):
    """Every partner-facing PageContext should ask at least 5 questions
    so the Guide can answer the follow-up that comes after the
    obvious one. Allowlist is leaf data-dump endpoints only."""

    def test_no_short_common_questions_outside_allowlist(self):
        short = sorted(
            (route, len(ctx.common_questions))
            for route, ctx in MANUAL_PAGE_CONTEXTS.items()
            if len(ctx.common_questions) < _MIN_QUESTIONS
            and route not in _SHORT_OK
        )
        self.assertFalse(
            short,
            "Pages below the 5-Q floor — bump common_questions or add "
            "to _SHORT_OK with a justification comment:\n  "
            + "\n  ".join(f"{r}: n={n}" for r, n in short),
        )

    def test_allowlist_entries_still_exist_and_are_short(self):
        """Sanity guard: every entry in _SHORT_OK must still exist
        in the registry AND must still be short (≤4 Qs). If a leaf
        endpoint gets renamed, removed, or richly enriched, the
        allowlist should be pruned, not silently kept."""
        stale = []
        for route in _SHORT_OK:
            ctx = MANUAL_PAGE_CONTEXTS.get(route)
            if ctx is None:
                stale.append((route, "missing-from-registry"))
                continue
            if len(ctx.common_questions) >= _MIN_QUESTIONS:
                stale.append((route, f"now has {len(ctx.common_questions)} "
                              "questions — drop from _SHORT_OK"))
        self.assertFalse(
            stale,
            "Stale allowlist entries — prune them:\n  "
            + "\n  ".join(f"{r}: {why}" for r, why in stale),
        )


class TestAnalyticPagesHaveRelatedRoutes(unittest.TestCase):
    """Every analytic page (something with metric_ids or key_metrics)
    should have ≥1 related_route so the Guide can suggest where to
    look next. The DATA_REQUIRED for-loop default (PR #1217) and the
    metric-related-routes series (#1192-#1196) together drove this to
    zero gaps; this guards against a regression that adds a new
    analytic surface with no sibling-route hint."""

    def test_no_analytic_page_has_empty_related_routes(self):
        empty = sorted(
            route
            for route, ctx in MANUAL_PAGE_CONTEXTS.items()
            if not (ctx.related_routes or [])
            and (ctx.metric_ids or ctx.key_metrics)
        )
        self.assertFalse(
            empty,
            "Analytic pages with no related_routes — add at least one "
            "sibling page so the Guide can recommend 'see also':\n  "
            + "\n  ".join(empty),
        )


class TestAllPagesHaveRelatedRoutes(unittest.TestCase):
    """Stricter than TestAnalyticPagesHaveRelatedRoutes: EVERY page —
    even admin / settings / status / utility surfaces — should carry at
    least one related_route so the Guide never dead-ends. PR #1259
    filled the last 22 system pages via _BATCH8_SIBLINGS; this guards
    against a new _ctx() or system-batch entry landing with no peer
    pointer."""

    def test_no_page_has_empty_related_routes(self):
        empty = sorted(
            route
            for route, ctx in MANUAL_PAGE_CONTEXTS.items()
            if not (ctx.related_routes or [])
        )
        self.assertFalse(
            empty,
            "Pages with no related_routes — add at least one sibling "
            "page (workflow / admin / settings family) so the Guide "
            "can recommend 'see also':\n  " + "\n  ".join(empty),
        )

    def test_related_routes_resolve(self):
        """Every related_routes entry must resolve to a real
        PageContext — a dangling reference sends the Guide to a 404."""
        known = set(MANUAL_PAGE_CONTEXTS.keys())
        broken: dict[str, list[str]] = {}
        for route, ctx in MANUAL_PAGE_CONTEXTS.items():
            bad = [r for r in (ctx.related_routes or []) if r not in known]
            if bad:
                broken[route] = bad
        self.assertFalse(
            broken,
            f"Pages referencing non-existent routes: {broken}",
        )


class TestNoNeedsPlaceholderInLimitations(unittest.TestCase):
    """Every PageContext should carry real, page-specific limitations,
    interpretation_guidance, and model_logic_summary rather than the
    "Needs source documentation." scaffold default. The placeholder
    cleanup series (#1225-#1244) drove all three fields to zero;
    this guards against a regression that lands a new _ctx() call
    without an explicit kwarg, which would inherit the _NEEDS default
    and surface placeholder text in the Guide."""

    _PLACEHOLDER = "needs source"

    def test_no_limitations_carries_needs_placeholder(self):
        offenders = sorted(
            route
            for route, ctx in MANUAL_PAGE_CONTEXTS.items()
            if any(self._PLACEHOLDER in (l or "").lower()
                   for l in (ctx.limitations or []))
        )
        self.assertFalse(
            offenders,
            "PageContexts with placeholder limitations — supply a "
            "real, page-specific limitations=[...] kwarg on the _ctx() "
            "call:\n  " + "\n  ".join(offenders),
        )

    def test_no_interpretation_guidance_carries_needs_placeholder(self):
        offenders = sorted(
            route
            for route, ctx in MANUAL_PAGE_CONTEXTS.items()
            if any(self._PLACEHOLDER in (l or "").lower()
                   for l in (ctx.interpretation_guidance or []))
        )
        self.assertFalse(
            offenders,
            "PageContexts with placeholder interpretation_guidance — "
            "supply a real, page-specific "
            "interpretation_guidance=[...] kwarg on the _ctx() "
            "call:\n  " + "\n  ".join(offenders),
        )

    def test_no_model_logic_summary_carries_needs_placeholder(self):
        offenders = sorted(
            route
            for route, ctx in MANUAL_PAGE_CONTEXTS.items()
            if self._PLACEHOLDER in (ctx.model_logic_summary or "").lower()
        )
        self.assertFalse(
            offenders,
            "PageContexts with placeholder model_logic_summary — "
            "supply a real, page-specific model_logic_summary="
            "kwarg on the _ctx() call describing what the page "
            "actually computes:\n  " + "\n  ".join(offenders),
        )


class TestNoNeedsPlaceholderInListFields(unittest.TestCase):
    """Every PageContext should carry real, page-specific entries in
    inputs / outputs / key_metrics / diligence_use_cases rather than the
    "Needs source documentation." scaffold default. The list-fields
    cleanup series (#1246-#1256) drove all four fields to zero; this
    guards against a regression that lands a new _ctx() call without
    one of these kwargs, which would inherit the _NEEDS default and
    surface placeholder text in the Guide."""

    _PLACEHOLDER = "needs source"
    _FIELDS = ("inputs", "outputs", "key_metrics", "diligence_use_cases")

    def test_no_list_field_carries_needs_placeholder(self):
        offenders = []
        for route, ctx in MANUAL_PAGE_CONTEXTS.items():
            for fname in self._FIELDS:
                values = getattr(ctx, fname) or []
                if any(self._PLACEHOLDER in (v or "").lower()
                       for v in values):
                    offenders.append(f"{route}: {fname}")
        offenders.sort()
        self.assertFalse(
            offenders,
            "PageContexts with placeholder inputs / outputs / "
            "key_metrics / diligence_use_cases — supply real, "
            "page-specific entries on the _ctx() call:\n  "
            + "\n  ".join(offenders),
        )


class TestMetricsHaveRealCommonMisread(unittest.TestCase):
    """Every MetricContext should carry a real common_misread sentence
    rather than the "Needs source documentation." placeholder default.
    `common_misread` IS sent to the Ollama Guide as part of the metric
    context block, so a placeholder degrades every answer about that
    metric. The misread-patches series (#1257-#1258) drove all 81
    metrics from placeholder to real; this guards against a regression
    that adds a new metric without supplying a real common_misread on
    the _m() call."""

    _PLACEHOLDER = "needs source"

    def test_no_metric_common_misread_is_placeholder(self):
        offenders = sorted(
            mid for mid, m in METRIC_REGISTRY.items()
            if self._PLACEHOLDER in (m.common_misread or "").lower()
        )
        self.assertFalse(
            offenders,
            "Metrics with placeholder common_misread — supply a real, "
            "metric-specific common_misread on the _m() call (or add "
            "an entry to _MISREAD_PATCHES):\n  " + "\n  ".join(offenders),
        )


class TestMetricsHaveRelatedMetrics(unittest.TestCase):
    """Every MetricContext should reference at least one related metric
    so the Guide can hop between connected concepts (e.g.
    timely_initiation_of_care → home_health_star_rating).
    PR #1258 closed the last 6 gaps; this guards against a regression
    that lands a new metric with no peer pointers."""

    _MIN_RELATED = 1

    def test_no_metric_has_empty_related_metrics(self):
        empty = sorted(
            mid for mid, m in METRIC_REGISTRY.items()
            if not (m.related_metrics or [])
        )
        self.assertFalse(
            empty,
            "Metrics with no related_metrics — add at least one peer "
            "concept so the Guide can hop:\n  " + "\n  ".join(empty),
        )

    def test_related_metrics_resolve(self):
        """Sanity guard: every related_metrics entry must resolve to a
        real metric_id — a dangling reference sends the Guide nowhere."""
        known = set(METRIC_REGISTRY.keys())
        broken = {}
        for mid, m in METRIC_REGISTRY.items():
            bad = [r for r in (m.related_metrics or []) if r not in known]
            if bad:
                broken[mid] = bad
        self.assertFalse(
            broken,
            f"Metrics referencing unknown peer metric_ids: {broken}",
        )


class TestDataSourcesHaveRealProvenance(unittest.TestCase):
    """Every DataSourceContext should carry real provenance_notes +
    strengths instead of the "Needs source documentation." placeholder
    default. Provenance is what makes a Guide answer about data
    lineage honest — placeholders short-circuit the trust chain.
    The drain landed in PR #1262 (23 provenance + 1 strengths cleared);
    this guards a new _s() call that lands without overriding the
    _NEEDS defaults."""

    _PLACEHOLDER = "needs source"

    def test_no_data_source_provenance_is_placeholder(self):
        offenders = sorted(
            sid for sid, s in DATA_SOURCE_REGISTRY.items()
            if self._PLACEHOLDER in (s.provenance_notes or "").lower()
        )
        self.assertFalse(
            offenders,
            "Data sources with placeholder provenance_notes — supply a "
            "real, source-specific provenance_notes kwarg on the _s() "
            "call (where it came from, how it's identified, what to "
            "cite):\n  " + "\n  ".join(offenders),
        )

    def test_no_data_source_strengths_carry_placeholder(self):
        offenders = sorted(
            sid for sid, s in DATA_SOURCE_REGISTRY.items()
            if any(self._PLACEHOLDER in (v or "").lower()
                   for v in (s.strengths or []))
        )
        self.assertFalse(
            offenders,
            "Data sources with placeholder strengths — supply real, "
            "source-specific strengths on the _s() call:\n  "
            + "\n  ".join(offenders),
        )

    def test_no_data_source_update_cadence_is_placeholder(self):
        offenders = sorted(
            sid for sid, s in DATA_SOURCE_REGISTRY.items()
            if self._PLACEHOLDER in (s.update_cadence or "").lower()
        )
        self.assertFalse(
            offenders,
            "Data sources with placeholder update_cadence — supply a "
            "real refresh cadence on the _s() call:\n  "
            + "\n  ".join(offenders),
        )

    def test_no_data_source_freshness_lag_is_placeholder(self):
        offenders = sorted(
            sid for sid, s in DATA_SOURCE_REGISTRY.items()
            if self._PLACEHOLDER in (s.freshness_lag or "").lower()
        )
        self.assertFalse(
            offenders,
            "Data sources with placeholder freshness_lag — supply a "
            "real lag on the _s() call:\n  " + "\n  ".join(offenders),
        )

    def test_every_data_source_has_explicit_ic_ready_flag(self):
        """Every DataSourceContext should declare ic_ready as True or
        False — never None — so the Guide can give an honest answer to
        'Is this IC-ready?' for any source. The 8 system-metadata /
        uploaded-target-data sources were filled in PR #1267; this
        guards a new _s() landing without the flag (which would
        default to None and leave the answer ambiguous)."""
        offenders = sorted(
            sid for sid, s in DATA_SOURCE_REGISTRY.items()
            if s.ic_ready is None
        )
        self.assertFalse(
            offenders,
            "Data sources with ic_ready=None — supply an explicit "
            "True / False on the _s() call:\n  " + "\n  ".join(offenders),
        )

    def test_data_source_related_metrics_resolve(self):
        """Every related_metrics entry on a data source must resolve to
        a real metric_id in METRIC_REGISTRY. A dangling reference sends
        the Guide nowhere when a partner asks 'what metrics does this
        source feed?'. Added in PR #1263 when public CMS sources were
        wired to their consuming metrics."""
        known = set(METRIC_REGISTRY.keys())
        broken: dict[str, list[str]] = {}
        for sid, s in DATA_SOURCE_REGISTRY.items():
            bad = [m for m in (s.related_metrics or []) if m not in known]
            if bad:
                broken[sid] = bad
        self.assertFalse(
            broken,
            f"Data sources referencing unknown metric_ids: {broken}",
        )

    def test_page_data_source_ids_resolve(self):
        """Every data_source_ids entry on a PageContext must resolve to
        a real source_id in DATA_SOURCE_REGISTRY. A dangling reference
        breaks the 'where does this come from' answer. PR #1264 wired
        24 illustrative-overlay pages to their canonical anchor source
        via _DATA_SOURCE_LINK_PATCHES; this guards future links."""
        known = set(DATA_SOURCE_REGISTRY.keys())
        broken: dict[str, list[str]] = {}
        for route, ctx in MANUAL_PAGE_CONTEXTS.items():
            bad = [s for s in (ctx.data_source_ids or []) if s not in known]
            if bad:
                broken[route] = bad
        self.assertFalse(
            broken,
            f"Pages referencing unknown data_source_ids: {broken}",
        )


class TestNoOrphanMetricsInRegistry(unittest.TestCase):
    """Every metric in METRIC_REGISTRY should be referenced by at
    least one PageContext.metric_ids. An orphan metric is dead
    weight in the prompt — the Guide can't surface it because no
    page resolves to it. PR #1279 wired the last 7 orphan metrics
    via _METRIC_LINK_EXTEND_2; this guards a new metric landing
    without being wired to its owning page."""

    def test_every_metric_is_referenced_by_some_page(self):
        all_used: set[str] = set()
        for ctx in MANUAL_PAGE_CONTEXTS.values():
            all_used.update(ctx.metric_ids or [])
        orphans = sorted(set(METRIC_REGISTRY.keys()) - all_used)
        self.assertFalse(
            orphans,
            "Orphan metrics in METRIC_REGISTRY — wire each to its "
            "owning page's metric_ids (or add an entry to "
            "_METRIC_LINK_EXTEND_2 at the bottom of "
            "manual_page_contexts.py):\n  " + "\n  ".join(orphans),
        )


class TestKeyMetricsResolveToWiredMetricIds(unittest.TestCase):
    """For every PageContext.key_metrics free-form string that resolves
    to a real METRIC_REGISTRY id via the lookup, the corresponding
    metric_id should be present in the page's metric_ids list — so the
    Guide's per-metric block (definition, formula, caveats,
    common_misread, etc.) actually surfaces in the prompt.

    PR #1277 wired the last 9 unwired pairs via _METRIC_LINK_EXTEND_2.
    This test guards against a new PageContext landing with a
    key_metrics string that mentions a registered metric (or a new
    registry entry being added without wiring it into the pages that
    already reference it by name)."""

    def test_no_unwired_key_metrics_resolve_to_registry(self):
        from rcm_mc.assistant.context.get_metric_context import (
            get_metric_context,
        )
        unwired: list[str] = []
        for route, ctx in MANUAL_PAGE_CONTEXTS.items():
            existing = set(ctx.metric_ids or [])
            for km in (ctx.key_metrics or []):
                km_text = (km or "").strip()
                if not km_text or "needs source" in km_text.lower():
                    continue
                result = get_metric_context(km_text)
                if result.found and result.metric_id not in existing:
                    unwired.append(
                        f"{route}: key_metrics {km_text!r} resolves to "
                        f"{result.metric_id!r} but it's not in metric_ids"
                    )
        unwired.sort()
        self.assertFalse(
            unwired,
            "Pages with key_metrics strings that resolve to METRIC_REGISTRY "
            "ids but aren't wired into metric_ids — add the id to the "
            "page's metric_ids (or to _METRIC_LINK_EXTEND_2 at the bottom "
            "of manual_page_contexts.py):\n  " + "\n  ".join(unwired),
        )


class TestMetricsHaveTwoOrMoreRelatedRoutes(unittest.TestCase):
    """Every MetricContext should have ≥2 related_routes so the Guide
    can always suggest at least one alternative page when a partner
    asks about a metric. The metric-related-routes series
    (#1192-#1196, #1219-#1223) drove sparse metrics from ~29 to zero;
    this guards against a regression that lands a new metric with
    only one (or zero) sibling-route pointers."""

    _MIN_ROUTES = 2

    def test_no_metric_has_fewer_than_two_related_routes(self):
        sparse = sorted(
            (mid, len(m.related_routes or []))
            for mid, m in METRIC_REGISTRY.items()
            if len(m.related_routes or []) < self._MIN_ROUTES
        )
        self.assertFalse(
            sparse,
            "Metrics with fewer than 2 related_routes — add canonical "
            "sibling pages so the Guide can always suggest 'see also':"
            "\n  " + "\n  ".join(f"{mid}: n={n}" for mid, n in sparse),
        )

    def test_metric_related_routes_resolve(self):
        """Sanity guard: every related_routes entry on a metric must
        resolve to a real PageContext — a metric pointing to a
        non-existent route sends the Guide to a 404."""
        known = set(MANUAL_PAGE_CONTEXTS.keys())
        broken = {}
        for mid, m in METRIC_REGISTRY.items():
            bad = [r for r in (m.related_routes or []) if r not in known]
            if bad:
                broken[mid] = bad
        self.assertFalse(
            broken,
            f"Metrics referencing non-existent routes: {broken}",
        )


if __name__ == "__main__":
    unittest.main()
