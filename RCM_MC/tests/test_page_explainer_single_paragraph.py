"""render_page_explainer must be ONE small paragraph — no sub-blocks.

Partners pushed back that the synthesis + RCM pages led with a wall of
explanation: an italic lede stacked on a "Scale." block, a "How to use."
block, and a mono "Source:" footer. The explainer is now a single
italic-led paragraph identical in weight to ck_page_explainer. This pins
that the heavy sub-blocks never come back, even though callers still
pass scale/use/source for signature compatibility.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.chartis._helpers import render_page_explainer


class PageExplainerSingleParagraphTests(unittest.TestCase):
    def _full(self):
        return render_page_explainer(
            "What this page does. Some supporting detail follows here.",
            scale="A = good, F = bad",
            use="Read the verdict first.",
            source="pe_intelligence/partner_review.py",
        )

    def test_no_scale_or_how_to_use_subblocks(self):
        out = self._full()
        self.assertNotIn("explainer-sub", out)
        self.assertNotIn("How to use", out)
        self.assertNotIn("Scale.", out)

    def test_no_source_footer(self):
        # Dev-facing code paths ("pe_intelligence/...py") must not render.
        out = self._full()
        self.assertNotIn("Source:", out)
        self.assertNotIn("partner_review.py", out)

    def test_exactly_one_explainer_paragraph(self):
        out = self._full()
        self.assertEqual(out.count('<p class="ck-page-explainer"'), 1)

    def test_lead_and_body_render_in_one_paragraph(self):
        out = self._full()
        self.assertIn("<em>What this page does.</em>", out)
        self.assertIn("Some supporting detail follows here.", out)

    def test_single_sentence_what_has_no_trailing_body(self):
        out = render_page_explainer("Just one sentence and done.")
        self.assertIn("<em>Just one sentence and done.</em>", out)
        self.assertEqual(out.count('<p class="ck-page-explainer"'), 1)


if __name__ == "__main__":
    unittest.main()
