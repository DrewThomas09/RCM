"""IC packet review-glance strips — the diligence upgrade wave.

Two stacked strips under the verdict hero: reasonableness bands
(in-band → implausible) and heuristic severities (critical → low).
"""
from __future__ import annotations

import unittest


class ReviewGlanceTests(unittest.TestCase):
    def test_glance_renders_for_a_review(self):
        from rcm_mc.pe_intelligence.partner_review import PartnerReview
        from rcm_mc.ui.chartis.ic_packet_page import _review_glance_svg
        r = PartnerReview(deal_id="d1", deal_name="Test")
        svg = _review_glance_svg(r)
        self.assertIn("Review at a glance", svg)
        self.assertIn("BAND CHECKS", svg)
        self.assertIn("HEURISTICS", svg)

    def test_none_review_renders_nothing(self):
        from rcm_mc.ui.chartis.ic_packet_page import _review_glance_svg
        self.assertEqual(_review_glance_svg(None), "")


if __name__ == "__main__":
    unittest.main()
