"""Pin for the Risk-vs-Return scatter on /deal-risk-scores.

The page's subtitle promises scores "validated against realized MOIC"
but only tabled them. The scatter makes the validation visual: composite
risk score (x) vs realized MOIC (y), one dot per deal, colored by tier,
dashed vertical at corpus-average risk, break-even at 1.0x, dots
clickable to /library.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace as NS


def _d(**kw):
    return NS(
        company_name=kw.get("company_name", "X"),
        composite_score=kw.get("composite_score"),
        moic=kw.get("moic"),
        tier=kw.get("tier", "Medium"),
        source_id=kw.get("source_id", "seed_1"),
    )


class RiskReturnScatterTests(unittest.TestCase):
    def _scatter(self, deals, avg=48.0):
        from rcm_mc.ui.data_public.deal_risk_scores_page import _risk_return_scatter
        return _risk_return_scatter(deals, avg)

    def test_dots_axes_and_section_header(self):
        html = self._scatter([
            _d(composite_score=72, moic=0.8, tier="Critical", source_id="s1"),
            _d(composite_score=20, moic=3.2, tier="Low", source_id="s2"),
        ])
        self.assertIn("Risk vs Realized Return", html)
        self.assertIn("Composite risk score", html)
        self.assertIn("Realized MOIC", html)
        self.assertEqual(html.count("<circle"), 2)

    def test_dots_link_to_library(self):
        html = self._scatter([
            _d(composite_score=72, moic=0.8, source_id="seed_42"),
            _d(composite_score=30, moic=2.0, source_id="seed_43"),
        ])
        self.assertEqual(html.count("<a href"), 2)
        self.assertIn("/library/seed_42", html)

    def test_tier_tone_mapping(self):
        html = self._scatter([
            _d(composite_score=75, moic=0.7, tier="Critical"),
            _d(composite_score=18, moic=3.4, tier="Low"),
        ])
        self.assertIn("--sc-negative", html)  # Critical
        self.assertIn("--sc-positive", html)  # Low

    def test_corpus_avg_reference_line(self):
        html = self._scatter(
            [_d(composite_score=72, moic=0.8), _d(composite_score=20, moic=3.0)],
            avg=46.0)
        self.assertIn("stroke-dasharray", html)
        self.assertIn("corpus average risk (46)", html)

    def test_skips_deals_without_moic_or_score(self):
        html = self._scatter([
            _d(composite_score=50, moic=2.0, source_id="a"),
            _d(composite_score=None, moic=2.0, source_id="b"),
            _d(composite_score=40, moic=None, source_id="c"),
            _d(composite_score=30, moic=1.5, source_id="d"),
        ])
        self.assertEqual(html.count("<circle"), 2)


if __name__ == "__main__":
    unittest.main()
