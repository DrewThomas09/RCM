"""X-Ray section jump-nav — the page grew to ~7,000px / 8 panels, so a
compact 'On this page' nav anchors each rendered section. Only rendered
panels get a chip + anchor (conditional ones that didn't resolve are
skipped), and the IC anchor (#hx-ic, linked from the source-purpose strip)
must stay unique.
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.ui.hcris_xray_page import _section_nav, render_hcris_xray_page


class SectionNavHelperTests(unittest.TestCase):
    def test_skips_empty_blocks(self):
        nav, body = _section_nav([
            ("a", "Alpha", "<p>A</p>"),
            ("b", "Bravo", ""),            # didn't render → no chip/anchor
            ("c", "Charlie", "<p>C</p>"),
        ])
        self.assertIn('href="#a"', nav)
        self.assertNotIn('href="#b"', nav)
        self.assertIn('href="#c"', nav)
        self.assertIn('id="a"', body)
        self.assertNotIn('id="b"', body)

    def test_no_nav_for_single_section(self):
        nav, body = _section_nav([("a", "Alpha", "<p>A</p>")])
        self.assertEqual(nav, "")
        self.assertIn("<p>A</p>", body)   # body still returned


class XrayNavRenderTests(unittest.TestCase):
    def setUp(self):
        self.h = render_hcris_xray_page({"ccn": ["450358"]})

    def test_nav_and_anchors_render(self):
        self.assertIn("On this page", self.h)
        for sid in ("hx-peers", "hx-local", "hx-demo", "hx-roster", "hx-ic"):
            self.assertIn(f'href="#{sid}"', self.h)
            self.assertIn(f'id="{sid}"', self.h)

    def test_ic_anchor_is_unique(self):
        # source-purpose links to #hx-ic; a duplicate id is invalid HTML.
        self.assertEqual(len(re.findall(r'id="hx-ic"', self.h)), 1)
        self.assertIn('href="#hx-ic"', self.h)


if __name__ == "__main__":
    unittest.main()
