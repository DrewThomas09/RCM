"""The RCM Benchmarks page should point to where benchmarks get applied.

Benchmark bands are only useful next to a target — the page should guide
the user onward to the RCM diligence pages that consume them.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.chartis.rcm_benchmarks_page import render_rcm_benchmarks


class RcmBenchmarksRelatedPagesTests(unittest.TestCase):
    def setUp(self):
        self.html = render_rcm_benchmarks()

    def test_has_related_pages_block(self):
        self.assertIn("RELATED PAGES", self.html)

    def test_links_to_consuming_diligence_pages(self):
        for route in (
            "/diligence/denial-prediction",
            "/diligence/payer-stress",
            "/diligence/hcris-xray",
        ):
            self.assertIn(route, self.html)


if __name__ == "__main__":
    unittest.main()
