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

from rcm_mc.assistant.context.manual_page_contexts import (
    MANUAL_PAGE_CONTEXTS,
)


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


if __name__ == "__main__":
    unittest.main()
