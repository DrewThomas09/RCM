"""Marketing hero coverage card (fills the empty right column).

The hero's right column carries a compact card: a bar per CMS provider
class plus three figures and a source line. Two things matter and are
easy to regress:

  1. the card must actually render (otherwise the column is blank);
  2. it must stay HONEST — and the definition of honest changed here.

Until 2026-08-18 the card was an ILLUSTRATIVE deal-activity chart with a
"Sample workspace" marker, and the marker was the load-bearing part: it
kept a decorative shape from reading as a live dashboard. The card now
carries no invented shape at all. Bar heights are proportional to real
certified-facility counts read from the shipped provider crosswalk, and
the three figures under it are read from the data at import. So the test
that used to pin the honesty LABEL now pins the honesty ITSELF: the
numbers must match what the loaders return.

Renderer-level, no server needed.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.chartis.marketing_page import (
    _CCNS_BY_CLASS,
    _N_CCNS,
    _N_HOSPITALS,
    _N_SYSTEMS,
    _N_VERIFIED_DEALS,
    render_marketing_page,
)


class HeroArtCard(unittest.TestCase):
    def setUp(self):
        self.html = render_marketing_page(basic_auth=False)

    def test_hero_art_card_renders(self):
        self.assertIn('class="hero-art"', self.html)
        self.assertIn("ha-card", self.html)
        # the visual itself (the SVG bar chart)
        self.assertIn('class="ha-chart"', self.html)
        self.assertIn("<svg", self.html)

    def test_hero_art_bars_are_one_per_provider_class(self):
        # One bar per class in the coverage map, so the picture cannot
        # drift from the counts printed beside it.
        self.assertGreaterEqual(len(_CCNS_BY_CLASS), 5)
        self.assertEqual(self.html.count('<rect x='),
                         len(_CCNS_BY_CLASS))

    def test_hero_art_figures_come_from_the_data(self):
        # Was three hand-typed constants ("1,936", "30+", "100%"). Each
        # of these is now whatever the loaders return, so a data refresh
        # moves the page and this test together.
        for figure in (f"{_N_CCNS:,}", f"{_N_HOSPITALS:,}",
                       str(_N_VERIFIED_DEALS)):
            self.assertIn(figure, self.html, figure)

    def test_the_counts_are_plausible_not_placeholders(self):
        # Guards the fallback path silently shipping zeros if a data
        # file goes missing in a slim deployment.
        self.assertGreater(_N_CCNS, 10_000)
        self.assertGreater(_N_HOSPITALS, 1_000)
        self.assertGreater(_N_VERIFIED_DEALS, 100)
        self.assertGreater(_N_SYSTEMS, 50)
        self.assertEqual(_N_HOSPITALS, _CCNS_BY_CLASS["Hospital"])
        self.assertGreaterEqual(_N_CCNS, sum(_CCNS_BY_CLASS.values()))

    def test_hero_art_names_its_sources(self):
        self.assertIn("HCRIS", self.html)
        self.assertIn("Source:", self.html)

    def test_no_sample_marker_because_nothing_is_a_sample(self):
        # The old card needed "Sample workspace" because its chart shape
        # was made up. Nothing on this card is, so the marker would now
        # be misleading in the other direction.
        self.assertNotIn("Sample workspace", self.html)

    def test_hero_art_present_with_basic_auth_too(self):
        # The art is decorative chrome, not auth-gated; both variants show it.
        self.assertIn('class="hero-art"', render_marketing_page(basic_auth=True))
