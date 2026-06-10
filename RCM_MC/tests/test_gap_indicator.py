"""Regression: the subtle red-dot data-gap indicator + per-section count.

Accuracy work needs a quiet, consistent way to mark cells we DON'T have a
real value for (not reported, or gated as a filing artifact) so a partner can
scan a dense page and see exactly where the gaps are — and so the gaps can be
counted to size sourcing work. See _chartis_kit.ck_gap_dot / ck_gap_count and
the HCRIS X-Ray metric rows.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_gap_dot, ck_gap_count


class GapDotTests(unittest.TestCase):
    def test_dot_renders_red_with_reason(self):
        h = ck_gap_dot("Not in the HCRIS filing")
        self.assertIn("ck-gap-dot", h)
        self.assertIn("sc-negative", h)               # red
        self.assertIn("Not in the HCRIS filing", h)   # reason in tooltip

    def test_reason_is_escaped(self):
        self.assertNotIn("<script>", ck_gap_dot("<script>x</script>"))


class GapCountTests(unittest.TestCase):
    def test_count_renders_when_gaps_present(self):
        h = ck_gap_count(3, 12)
        self.assertIn("3 of 12 not reported", h)

    def test_count_is_empty_when_complete(self):
        # A fully-populated section stays clean — no count chip at all.
        self.assertEqual(ck_gap_count(0, 12), "")
        self.assertEqual(ck_gap_count(-1, 12), "")


class XrayGapMarkingTests(unittest.TestCase):
    def test_xray_marks_gaps_on_missing_metrics(self):
        from rcm_mc.diligence.hcris_xray import find_hospital
        from rcm_mc.ui.hcris_xray_page import render_hcris_xray_page
        # Find a hospital whose page-selected metrics include a None (gap).
        ccn = None
        from rcm_mc.data.hcris import load_hcris
        for c in load_hcris()["ccn"].astype(str).unique().tolist()[:3000]:
            h = find_hospital(c)
            if h and h.net_to_gross_ratio is None:
                ccn = c
                break
        self.assertIsNotNone(ccn, "expected a hospital with a gated metric")
        html = render_hcris_xray_page({"ccn": [ccn]})
        self.assertIn("ck-gap-dot", html)            # at least one red dot
        self.assertIn("not reported", html)          # the section tally


if __name__ == "__main__":
    unittest.main()
