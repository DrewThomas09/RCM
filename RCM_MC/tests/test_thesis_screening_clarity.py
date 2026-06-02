"""Thesis Screening clarity + bigger controls.

You said the page is good but its purpose should be clearer — the mental
model is "I ran a deal, got these metrics, now show the historical pass /
success rate of those metrics" — and the screening controls were too small.

This covers the render layer:
  - titled "Thesis Screening" (matching the nav label; was "Deal Screening");
  - a "how it works" 3-step + an explainer that frames the thresholds as YOUR
    thesis and the pass rate as its historical base rate;
  - larger, labelled controls (ds-controls / ds-input, not 10px / 100px);
  - the empty-state orientation copy is preserved.
"""
from __future__ import annotations

import unittest

import rcm_mc.ui.chartis.deal_screening_page as dsp


class TitleAndFramingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.html = dsp.render_deal_screening(query="")

    def test_titled_thesis_screening(self) -> None:
        self.assertIn("Thesis Screening", self.html)
        self.assertIn("THESIS SCREENING", self.html)

    def test_purpose_framing_is_explicit(self) -> None:
        self.assertIn("How would your thesis", self.html)
        self.assertIn("pass rate", self.html)
        # thesis = thresholds, pass rate = base rate
        self.assertIn("base rate", self.html)

    def test_how_it_works_three_steps(self) -> None:
        self.assertIn("ds-howto", self.html)
        self.assertIn("STEP 1", self.html)
        self.assertIn("STEP 2", self.html)
        self.assertIn("STEP 3", self.html)


class BiggerControlsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.html = dsp.render_deal_screening(query="")

    def test_controls_use_larger_grid_classes(self) -> None:
        self.assertIn("ds-controls", self.html)
        self.assertIn("ds-input", self.html)
        self.assertIn("Your thesis — set the thresholds", self.html)
        # the old cramped 100px inline inputs are gone
        self.assertNotIn("width:100px", self.html)

    def test_controls_have_plain_english_glosses(self) -> None:
        # each lever explains what it does
        self.assertIn("valuation ceiling", self.html)
        self.assertIn("return floor", self.html)


class EmptyStatePreservedTests(unittest.TestCase):
    def test_empty_state_orientation_intact(self) -> None:
        import unittest.mock as mock
        with mock.patch.object(dsp, "load_corpus_deals", return_value=[]):
            html = dsp.render_deal_screening()
        self.assertIn("No deal corpus is loaded yet.", html)
        self.assertIn("ranks the corpus deal library", html)


if __name__ == "__main__":
    unittest.main()
