"""Marketing hero 'sample workspace' art (fills the empty right column).

The hero's right column went blank when the old meta block was removed; it now
carries a compact 'Sample workspace' card: an illustrative deal-activity chart
plus three TRUE, durable figures (1,936 comparable deals, 30+ open-data
sources, 100% link-to-source) and a source line. Two things matter and are
easy to regress:

  1. the card must actually render (otherwise the column is blank again);
  2. it must stay HONEST: the 'Sample workspace' marker is what keeps the
     decorative chart from reading as a live dashboard, in line with the rest
     of the platform's modeled-vs-live discipline.

Renderer-level, no server needed.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.chartis.marketing_page import render_marketing_page


class HeroArtCard(unittest.TestCase):
    def setUp(self):
        self.html = render_marketing_page(basic_auth=False)

    def test_hero_art_card_renders(self):
        self.assertIn('class="hero-art"', self.html)
        self.assertIn("ha-card", self.html)
        # the visual itself (the SVG bar chart)
        self.assertIn('class="ha-chart"', self.html)
        self.assertIn("<svg", self.html)

    def test_hero_art_is_marked_sample_not_live(self):
        # The honesty marker: a decorative shape must never read as a live
        # dashboard. This is the load-bearing label.
        self.assertIn("Sample workspace", self.html)

    def test_hero_art_shows_the_true_figures(self):
        # These three are true/durable (not illustrative), so they are pinned.
        for figure in ("1,936", "30+", "100%"):
            self.assertIn(figure, self.html)

    def test_hero_art_names_its_sources(self):
        self.assertIn("HCRIS", self.html)
        self.assertIn("Source:", self.html)

    def test_hero_art_present_with_basic_auth_too(self):
        # The art is decorative chrome, not auth-gated; both variants show it.
        self.assertIn('class="hero-art"', render_marketing_page(basic_auth=True))


if __name__ == "__main__":
    unittest.main()
