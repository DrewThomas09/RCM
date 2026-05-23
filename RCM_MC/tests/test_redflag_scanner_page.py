"""Trust framing for the rule-based Deal Red-Flag Scanner page.

A rule-based scanner is a *directional* diligence input, not a finished
IC deliverable — the page subtitle must not claim "IC-ready".
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.redflag_scanner_page import render_redflag_scanner


class RedflagScannerTrustFramingTests(unittest.TestCase):
    def setUp(self):
        self.html = render_redflag_scanner({})

    def test_renders_with_page_title(self):
        self.assertIn("ck-page-title", self.html)
        self.assertIn("Deal Red-Flag Scanner", self.html)

    def test_does_not_overclaim_ic_ready(self):
        # The rule-based scanner output is directional, not IC-ready.
        self.assertNotIn("IC-ready", self.html)
        self.assertIn("directional, verify before IC", self.html)


if __name__ == "__main__":
    unittest.main()
