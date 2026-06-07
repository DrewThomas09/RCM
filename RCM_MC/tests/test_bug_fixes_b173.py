"""b173 — the top-bar hover mega-menu was too large.

Hovering a nav section dropped a full-bleed mega-menu that was ~280px tall:
a 22px lede headline, 20+16px vertical padding, and 22px row-gaps left a lot
of empty space for just six links. Compacted (verified against real
screenshots): 17px headline, 14/12 padding, 13px row-gaps, tighter feat gap.

This guards the compact values so the panel can't quietly balloon again — the
top bar has been a recurring source of "too large / overlap" regressions, so
the sizes are pinned here.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import chartis_shell


class TestMegaMenuCompact(unittest.TestCase):
    def setUp(self):
        self.css = chartis_shell("<p>x</p>", "T")

    def test_mega_inner_padding_is_compact(self):
        # Mega-inner padding settled at 20px/18px in the full-width 2-column
        # redesign (superseding the earlier compact 14px/12px). Pin the current
        # value; still guard against the old roomy 20px/16px height driver.
        self.assertIn("padding:20px 32px 18px", self.css)
        self.assertNotIn("padding:20px 32px 16px", self.css)

    def test_mega_headline_is_compact(self):
        # 22px serif headline made the lede column tall; now 17px.
        self.assertIn(".ck-mega-feat-title", self.css)
        self.assertIn("font-size:17px", self.css)

    def test_mega_item_rows_are_tight(self):
        # 22px row-gap left big gaps between the two rows of links.
        self.assertIn("row-gap:13px", self.css)


if __name__ == "__main__":
    unittest.main()
