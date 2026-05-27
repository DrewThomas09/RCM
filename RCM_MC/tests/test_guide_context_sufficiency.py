"""Guide context-sufficiency regression guard.

The 2026-05-26 sprint mapped placeholder page-contexts 144 -> 1 and expanded
the metric registry so the Guide can answer hard, quantitative questions WITH
the right context (formula + provenance), not just prose. These tests pin that
outcome offline (no Ollama needed): they assert the assembled context packet
actually surfaces the metric/formula a hard question needs, so the coverage
can't silently regress. They test context ASSEMBLY, not model output.
"""
from __future__ import annotations

import unittest

from rcm_mc.assistant.context.guide_context_packet import (
    build_guide_context_packet,
)
from rcm_mc.assistant.context.metric_registry import METRIC_REGISTRY
from rcm_mc.assistant.context.page_context_registry import (
    PAGE_CONTEXT_REGISTRY,
    _is_placeholder,
)

_NEEDS = "Needs source documentation."


class CoverageStaysHigh(unittest.TestCase):
    def test_placeholders_stay_essentially_zero(self):
        # The sprint took placeholders to 1 (only /ebitda-bridge, an unwired
        # alias). Guard against silent regression of the whole migration.
        ph = [r for r, c in PAGE_CONTEXT_REGISTRY.items() if _is_placeholder(c)]
        self.assertLessEqual(len(ph), 3, f"placeholders crept back up: {ph}")

    def test_core_analytic_routes_grade_strong(self):
        # These are the pages partners hit with hard quantitative questions;
        # each must resolve linked metric/source context (STRONG), not prose
        # alone.
        for route in ("/quant-lab", "/portfolio/regression", "/benchmarks",
                      "/cost-structure", "/debt-service", "/lp-dashboard",
                      "/concentration-risk", "/sector-intel",
                      "/diligence/xray"):
            pkt = build_guide_context_packet(route)
            self.assertEqual(pkt.context_quality, "strong",
                             f"{route} is not STRONG: {pkt.context_quality}")


class HardQuestionContextIsPresent(unittest.TestCase):
    """For a hard question on a route, the packet must carry the metric the
    answer depends on — i.e. the Guide can actually answer it from context."""

    CASES = [
        ("/debt-service", "dscr"),
        ("/lp-dashboard", "tvpi"),
        ("/lp-dashboard", "dpi"),
        ("/concentration-risk", "hhi"),
        ("/benchmarks", "denial_rate"),
        ("/cost-structure", "operating_margin"),
        ("/quant-lab", "operating_margin"),
        ("/nursing-homes", "cms_star_rating"),
        ("/treasury", "days_cash_on_hand"),
    ]

    def test_packet_surfaces_the_needed_metric(self):
        for route, metric_id in self.CASES:
            pkt = build_guide_context_packet(route)
            ids = {m.metric_id for m in pkt.metric_contexts}
            self.assertIn(metric_id, ids,
                          f"{route} packet missing metric {metric_id} "
                          f"(has: {sorted(ids)})")


class NewMetricsAreUsable(unittest.TestCase):
    def test_added_metrics_have_real_formulas(self):
        # Standard metrics added this sprint must carry a real (non-placeholder)
        # formula so the Guide can explain "how is X computed".
        for mid in ("hhi", "concentration_ratio", "dscr", "tvpi", "dpi",
                    "rvpi", "days_cash_on_hand"):
            m = METRIC_REGISTRY.get(mid)
            self.assertIsNotNone(m, f"metric {mid} missing from registry")
            self.assertNotEqual(m.formula, _NEEDS,
                                f"{mid} has no real formula")
            self.assertTrue(m.definition and m.caveats,
                            f"{mid} lacks definition/caveats")

    def test_cms_star_rating_is_honest_about_being_external(self):
        # CMS stars are CMS's own composite — must NOT claim an invented
        # formula; formula_confidence must be NOT_APPLICABLE.
        m = METRIC_REGISTRY["cms_star_rating"]
        self.assertEqual(m.formula_confidence.name, "NOT_APPLICABLE")


if __name__ == "__main__":
    unittest.main()
