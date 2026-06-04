"""Corpus credibility: realized-outcome benchmarks must be disclosed as
largely illustrative.

The benchmark deal corpus is ~1,700 deals, but only a small verified-
historical core carries disclosed returns — ~96% of the rows with a
realized MOIC/IRR are illustrative/modeled. Provenance is honestly tagged in
corpus_provenance, but several partner-facing pages compute MOIC/IRR
benchmarks off the whole corpus and presented them under a plain "BENCHMARK
CORPUS" chip (which read as real historical data). These guard the
disclosure so a partner / LP never reads a synthetic-dominated median as a
real track record.
"""

import unittest

from rcm_mc.ui._chartis_kit import ck_data_universe
from rcm_mc.ui.chartis.deal_screening_page import render_deal_screening
from rcm_mc.ui.chartis.payer_intelligence_page import render_payer_intelligence
from rcm_mc.ui.chartis.portfolio_analytics_page import render_portfolio_analytics
from rcm_mc.ui.chartis.sponsor_track_record_page import render_sponsor_track_record


class TestCorpusIllustrativeDisclosure(unittest.TestCase):
    def test_corpus_universe_tooltip_is_honest(self):
        chip = ck_data_universe("corpus")
        # The tooltip must say the realized outcomes are mostly illustrative,
        # not present the corpus as fully real historical data.
        self.assertIn("illustrative", chip.lower())
        self.assertIn("not disclosed returns", chip.lower())

    def test_sponsor_track_record_discloses_illustrative(self):
        html = render_sponsor_track_record({})
        self.assertIn("illustrative", html.lower())
        # The corpus universe chip rides along too.
        self.assertIn("BENCHMARK CORPUS", html)
        # And the verified-only read is shown beside the illustrative median.
        self.assertIn("Verified Median MOIC", html)
        self.assertIn("verified-historical deals", html)

    def test_deal_screening_discloses_illustrative(self):
        html = render_deal_screening({})
        self.assertIn("illustrative", html.lower())
        self.assertIn("BENCHMARK CORPUS", html)

    def test_portfolio_analytics_discloses_illustrative(self):
        html = render_portfolio_analytics({})
        self.assertIn("illustrative", html.lower())

    def test_payer_intelligence_discloses_illustrative(self):
        """Per-payer-regime MOIC/IRR distributions are corpus-derived
        (synthetic-dominated), so they must be disclosed as illustrative."""
        html = render_payer_intelligence({})
        self.assertIn("illustrative", html.lower())
        self.assertIn("MOIC", html)  # it does show the corpus MOIC bands


if __name__ == "__main__":
    unittest.main()
