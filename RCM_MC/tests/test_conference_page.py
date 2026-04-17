"""Tests for conference roadmap page."""
from __future__ import annotations

import unittest


class TestConferenceRoadmap(unittest.TestCase):

    def test_renders_all_conferences(self):
        from rcm_mc.ui.conference_page import render_conference_roadmap, CONFERENCES
        html = render_conference_roadmap()
        self.assertIn("SeekingChartis", html)
        self.assertIn("Conference Roadmap", html)
        self.assertIn("J.P. Morgan", html)
        self.assertIn("HIMSS", html)

    def test_category_filter(self):
        from rcm_mc.ui.conference_page import render_conference_roadmap
        html = render_conference_roadmap("Investment")
        self.assertIn("J.P. Morgan", html)
        self.assertNotIn("AHA Annual", html)

    def test_all_categories_present(self):
        from rcm_mc.ui.conference_page import CONFERENCES
        categories = {e["category"] for e in CONFERENCES}
        self.assertTrue(len(categories) >= 4)

    def test_planning_tips(self):
        from rcm_mc.ui.conference_page import render_conference_roadmap
        html = render_conference_roadmap()
        self.assertIn("Planning Tips", html)
        self.assertIn("J.P. Morgan", html)

    def test_quarter_grouping(self):
        from rcm_mc.ui.conference_page import render_conference_roadmap
        html = render_conference_roadmap()
        self.assertIn("2027 Q1", html)

    def test_tier_badges(self):
        from rcm_mc.ui.conference_page import render_conference_roadmap
        html = render_conference_roadmap()
        self.assertIn("Flagship", html)
        self.assertIn("Major", html)


if __name__ == "__main__":
    unittest.main()
