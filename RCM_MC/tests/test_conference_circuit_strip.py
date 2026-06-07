"""Conference 'circuit read' strip: the at-a-glance sentiment graph.

Conference Intelligence was a wall of text; the ask was a graph to bring the
year's events to life. The recap layer now opens with a circuit-read strip:
a sentiment distribution bar plus one cell per event, each toned by that
recap's real sentiment, derived straight from the curated data (no fabricated
numbers). The existing conference tests cover the recaps, calendar, and macro
threads but not this strip, so pin it: it must render, be data-driven (one cell
per recap, real sentiment colours), and stay out of the category-filtered view
(which focuses the forward calendar).
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.conference_page import render_conference_roadmap
from rcm_mc.ui.conference_recaps import CONFERENCE_RECAPS


class CircuitStrip(unittest.TestCase):
    def setUp(self):
        self.html = render_conference_roadmap("all")

    def test_distribution_bar_and_summary_present(self):
        self.assertIn("cr-circ-bar2", self.html)  # the proportion bar
        self.assertIn("read across the circuit", self.html.lower())

    def test_one_cell_per_recap(self):
        # Data-driven: exactly one circuit cell per curated recap.
        self.assertEqual(
            self.html.count('<div class="cr-circ-cell"'),
            len(CONFERENCE_RECAPS),
        )

    def test_cells_are_sentiment_toned(self):
        # The cells carry the real sentiment palette (green optimistic / amber
        # mixed-or-cautious), so the bars actually encode the mood.
        self.assertIn("#0a8a5f", self.html)  # positive tone
        self.assertIn("#b8732a", self.html)  # warning tone

    def test_circuit_focuses_out_on_category_filter(self):
        # A category-filtered roadmap drops the recap/circuit layer to focus
        # the forward calendar (matches the recaps' own behaviour).
        filtered = render_conference_roadmap("PE/M&A")
        self.assertNotIn('<div class="cr-circ-cell"', filtered)


if __name__ == "__main__":
    unittest.main()
