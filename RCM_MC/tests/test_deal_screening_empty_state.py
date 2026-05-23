"""The /deal-screening no-corpus state should orient the user.

A flow-junction page (screen -> diligence -> IC) shouldn't dead-end on a
one-line "No corpus available" — it should say what the page does, why
it's empty, and where to load data.
"""
from __future__ import annotations

import unittest

import rcm_mc.ui.chartis.deal_screening_page as dsp


class DealScreeningEmptyStateTests(unittest.TestCase):
    def test_no_corpus_state_is_actionable(self):
        orig = dsp.load_corpus_deals
        dsp.load_corpus_deals = lambda *a, **k: []
        try:
            html = dsp.render_deal_screening()
        finally:
            dsp.load_corpus_deals = orig
        self.assertIn("No deal corpus is loaded yet.", html)       # clear state
        self.assertIn("ranks the corpus deal library", html)        # what it does
        self.assertIn("Data Catalog", html)                         # next step
        self.assertNotIn("No corpus available for screening.", html)  # old copy

    def test_normal_render_unaffected(self):
        # With the real (non-empty) corpus the page still renders fully.
        html = dsp.render_deal_screening()
        self.assertGreater(len(html), 1000)
        self.assertNotIn("No deal corpus is loaded yet.", html)


if __name__ == "__main__":
    unittest.main()
