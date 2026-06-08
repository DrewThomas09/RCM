"""Regression: IC-packet TOC linked to sections that weren't rendered.

scenario_narrative / board_memo / lp_pitch arrive as truthy dicts whose
inner text can be empty; the section renderer then returns a no-anchor
placeholder, but the TOC keyed off bundle.get(key) and emitted dead
#scenario / #board-memo jump links. _toc now filters on the set of
anchors actually rendered.
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.ui.chartis.ic_packet_page import _toc


class TocAnchorTests(unittest.TestCase):
    def test_toc_only_links_rendered_anchors(self):
        bundle = {
            "ic_memo": "x", "scenario_narrative": {"summary": ""},
            "board_memo": {"markdown": ""}, "lp_pitch": {"markdown": ""},
        }
        # Body actually rendered only the ic-memo anchor.
        html = _toc(bundle, rendered_anchors={"ic-memo"})
        refs = set(re.findall(r'href="#([\w-]+)"', html))
        self.assertEqual(refs, {"ic-memo"})
        self.assertNotIn("#scenario", html)
        self.assertNotIn("#board-memo", html)

    def test_toc_includes_rendered_scenario(self):
        bundle = {"scenario_narrative": {"summary": "real"}}
        html = _toc(bundle, rendered_anchors={"scenario"})
        self.assertIn('href="#scenario"', html)

    def test_toc_empty_when_nothing_rendered(self):
        self.assertEqual(_toc({"ic_memo": "x"}, rendered_anchors=set()), "")


if __name__ == "__main__":
    unittest.main()
