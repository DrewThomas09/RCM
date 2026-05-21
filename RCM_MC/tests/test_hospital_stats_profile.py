"""Pin for the National Percentile Profile bar chart on /hospital-stats.

The statistical-profile table carries each metric's national percentile
in a single column, hiding the hospital's shape. The lead profile turns
those percentiles into one labelled bar per metric (bar length = rank)
so a partner reads the spiky profile — top-decile on size, bottom
quartile on margin — at a glance. Color marks RANK (top-quartile green,
bottom-quartile red), matching the table's percentile badges, not a
value judgment.
"""
from __future__ import annotations

import unittest


class PercentileProfileTests(unittest.TestCase):
    def _profile(self, data):
        from rcm_mc.ui.hospital_stats_page import _percentile_profile
        return _percentile_profile(data)

    def test_one_bar_row_per_metric(self):
        html = self._profile([
            ("Beds", "420", 88.0),
            ("Operating Margin", "-2.1%", 18.0),
            ("Occupancy", "61%", 55.0),
        ])
        self.assertIn("National Percentile Profile", html)
        self.assertEqual(html.count("ck-bar-row-fill"), 3)

    def test_tone_tracks_percentile_rank(self):
        html = self._profile([
            ("Beds", "420", 88.0),            # top quartile -> positive
            ("Operating Margin", "-2.1%", 18.0),  # bottom quartile -> negative
        ])
        self.assertIn("--sc-positive", html)
        self.assertIn("--sc-negative", html)

    def test_empty_below_two_metrics(self):
        self.assertEqual(self._profile([("Beds", "420", 88.0)]), "")

    def test_caption_clarifies_rank_not_judgment(self):
        html = self._profile([
            ("Beds", "420", 88.0), ("Occupancy", "61%", 55.0),
        ])
        self.assertIn("percentile rank", html)
        self.assertIn("not whether high is favorable", html)


if __name__ == "__main__":
    unittest.main()
