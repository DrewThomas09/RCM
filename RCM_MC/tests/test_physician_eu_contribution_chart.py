"""Wave-32 visual: physician EU signed contribution chart.

The roster table ranked providers by contribution, but "three
providers fund the practice and two drain it" lived in a color-coded
dollars column. Pins the signed-bar chart: loss tones (FMV red /
observed amber), rank order, loss-maker caption counts, and the
empty state.
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence.physician_eu import analyze_roster_eu
from rcm_mc.ui.physician_eu_page import _contribution_svg, _demo_roster


class ContributionChartTests(unittest.TestCase):
    def setUp(self):
        self.report = analyze_roster_eu(_demo_roster())

    def test_renders_signed_bars_for_all_providers(self):
        svg = _contribution_svg(self.report)
        self.assertIn("<svg", svg)
        self.assertIn("ck-eu-contribution", svg)
        for u in self.report.units:
            self.assertIn(u.provider_id, svg)
        self.assertIn("LOSS-MAKER", svg)

    def test_rank_order_preserved(self):
        svg = _contribution_svg(self.report)
        ranked = sorted(self.report.units, key=lambda u: u.contribution_rank)
        idx = [svg.index(u.provider_id) for u in ranked]
        self.assertEqual(idx, sorted(idx))

    def test_loss_makers_get_negative_tones(self):
        svg = _contribution_svg(self.report)
        # The demo roster includes loss-makers at FMV (P007 class) —
        # the negative tone must appear.
        from rcm_mc.ui._chartis_kit import P
        n_fmv = sum(1 for u in self.report.units if u.is_loss_maker_at_fmv)
        if n_fmv:
            self.assertIn(P["negative"], svg)
        self.assertIn(f"{n_fmv} LOSS-MAKER", svg)

    def test_empty_renders_nothing(self):
        from types import SimpleNamespace
        self.assertEqual(
            _contribution_svg(SimpleNamespace(units=[])), "")


if __name__ == "__main__":
    unittest.main()
