"""Command Center (/app) canvas + card-sizing guards.

Partner-flagged: the page used a yellowy `--cc-page-bg:#ebe5d3` that read as a
card tone rather than the app's page canvas, and fixed 140px grid rows with
`overflow:hidden` clipped cards whose content didn't fit. This pins the fixes:
the page background tracks the standard `--sc-parchment` canvas, rows grow to
fit content, and cards/bodies no longer clip.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.chartis._app_grid import APP_GRID_CSS as C


class CommandCenterCanvasTests(unittest.TestCase):
    def test_page_bg_matches_app_parchment_not_yellow(self):
        self.assertIn("--cc-page-bg:var(--sc-parchment", C)
        self.assertNotIn("#ebe5d3", C)   # the old yellowy outlier is gone

    def test_grid_rows_grow_to_fit_content(self):
        self.assertIn("grid-auto-rows:minmax(140px,auto)", C)
        self.assertNotIn("grid-auto-rows:140px;", C)   # no fixed-height clip

    def test_cards_and_bodies_do_not_clip(self):
        # Both the card and its body must not hide overflowing nested boxes.
        self.assertIn(".cc-card{position:relative;background:var(--cc-paper)"
                      ";border:1px solid var(--cc-rule);", C)
        self.assertIn("flex-direction:column;overflow:visible;min-height:0;}", C)
        self.assertIn(".cc-body{flex:1;padding:16px 20px;overflow:visible", C)


if __name__ == "__main__":
    unittest.main()
