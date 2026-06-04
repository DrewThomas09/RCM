"""Market-intel comps hub overhaul.

The /market-intel public-comps hub was reworked to be front-facing:

1. The EV/EBITDA × revenue scatter uses a LOG x-axis so a mega-cap payer
   (UNH ~$395B revenue) no longer compresses every hospital operator into an
   unreadable smear at the origin. The two genuine outliers — highest revenue
   (UNH) and highest multiple (a REIT) — are highlighted and always labelled.
   (Regression guard: an earlier rewrite left a stray ``x_min`` reference in
   the axis-tick loop that raised NameError at render time.)

2. A sub-vertical taxonomy rolls the granular category codes up into the
   six public-market buckets a PE desk screens by, with a per-vertical
   summary grid and a revenue-concentration HHI.

3. The comp table is dense + color-coded: EV/EBITDA shaded green ≥12x /
   red <8x, op-margin shaded, grouped by sub-vertical.
"""
from __future__ import annotations

import unittest


def _comps():
    """A spread spanning $0.9B → $395B so the log axis matters."""
    return [
        {"ticker": "UNH", "name": "UnitedHealth", "category": "MANAGED_CARE_PAYER",
         "revenue_ttm_usd_bn": 395.0, "ev_ebitda_multiple": 13.2,
         "ev_revenue_multiple": 1.42, "enterprise_value_usd_bn": 562.0,
         "operating_margin": 0.084, "debt_to_ebitda": 1.05,
         "analyst_coverage": {"consensus": "BUY", "price_target_usd": 630.0}},
        {"ticker": "HCA", "name": "HCA Healthcare", "category": "MULTI_SITE_ACUTE_HOSPITAL",
         "revenue_ttm_usd_bn": 71.2, "ev_ebitda_multiple": 8.9,
         "ev_revenue_multiple": 1.69, "enterprise_value_usd_bn": 120.1,
         "operating_margin": 0.169, "debt_to_ebitda": 3.09,
         "analyst_coverage": {"consensus": "BUY", "price_target_usd": 345.0}},
        {"ticker": "UHS", "name": "Universal Health", "category": "MULTI_SITE_ACUTE_AND_BEHAVIORAL",
         "revenue_ttm_usd_bn": 15.6, "ev_ebitda_multiple": 7.4,
         "ev_revenue_multiple": 1.12, "enterprise_value_usd_bn": 17.4,
         "operating_margin": 0.115, "debt_to_ebitda": 1.40,
         "analyst_coverage": {"consensus": "BUY", "price_target_usd": 235.0}},
        {"ticker": "WELL", "name": "Welltower", "category": "HEALTHCARE_REIT",
         "revenue_ttm_usd_bn": 8.2, "ev_ebitda_multiple": 52.1,
         "ev_revenue_multiple": 13.66, "enterprise_value_usd_bn": 112.0,
         "operating_margin": 0.205, "debt_to_ebitda": 10.93,
         "analyst_coverage": {"consensus": "BUY", "price_target_usd": 155.0}},
        {"ticker": "MPW", "name": "Medical Properties", "category": "HEALTHCARE_REIT",
         "revenue_ttm_usd_bn": 0.9, "ev_ebitda_multiple": 24.4,
         "ev_revenue_multiple": 14.57, "enterprise_value_usd_bn": 13.4,
         "operating_margin": 0.48, "debt_to_ebitda": 18.73,
         "analyst_coverage": {"consensus": "HOLD", "price_target_usd": 6.0}},
    ]


class TestLogScatter(unittest.TestCase):
    def setUp(self):
        from rcm_mc.ui.market_intel_page import _target_scatter_chart
        self.svg = _target_scatter_chart(_comps())

    def test_renders_without_stray_xmin(self):
        # The bug: a leftover ``x_min`` in the tick loop raised NameError.
        self.assertTrue(self.svg)
        self.assertNotIn("x_min", self.svg)

    def test_log_axis_titled(self):
        self.assertIn("LOG SCALE", self.svg)

    def test_proportional_not_distorted(self):
        self.assertIn('preserveAspectRatio="xMidYMid meet"', self.svg)
        self.assertNotIn('preserveAspectRatio="none"', self.svg)

    def test_outliers_labelled(self):
        # Highest revenue (UNH) and highest multiple (WELL) are the called-out
        # outliers and must both be labelled even though de-collision drops
        # some interior labels.
        self.assertIn(">UNH<", self.svg)
        self.assertIn(">WELL<", self.svg)

    def test_tooltip_carries_margin(self):
        # Hover tooltip is Ticker · Name · revenue · multiple · margin.
        self.assertIn("op margin", self.svg)


class TestHHI(unittest.TestCase):
    def test_monopoly_is_max(self):
        from rcm_mc.ui.market_intel_page import _hhi
        self.assertAlmostEqual(_hhi([100.0]), 10000.0, places=3)

    def test_two_equal_shares(self):
        from rcm_mc.ui.market_intel_page import _hhi
        # 50% + 50% → 2 × 50² = 5000.
        self.assertAlmostEqual(_hhi([40.0, 40.0]), 5000.0, places=3)

    def test_empty_is_zero(self):
        from rcm_mc.ui.market_intel_page import _hhi
        self.assertEqual(_hhi([]), 0.0)
        self.assertEqual(_hhi([0.0, 0.0]), 0.0)

    def test_labels(self):
        from rcm_mc.ui.market_intel_page import _hhi_label
        self.assertEqual(_hhi_label(9000), "highly concentrated")
        self.assertEqual(_hhi_label(2000), "moderately concentrated")
        self.assertEqual(_hhi_label(800), "competitive")


class TestSubvertical(unittest.TestCase):
    def test_known_rollups(self):
        from rcm_mc.ui.market_intel_page import _subvertical_of
        self.assertEqual(_subvertical_of("HEALTHCARE_REIT")[0], "Healthcare REITs")
        self.assertEqual(_subvertical_of("MANAGED_CARE_PAYER")[0], "Payors / Managed Care")
        # Acute codes all collapse to one bucket at the same rank.
        self.assertEqual(
            _subvertical_of("RURAL_ACUTE_HOSPITAL")[0],
            _subvertical_of("MULTI_SITE_ACUTE_HOSPITAL")[0],
        )

    def test_unknown_falls_through(self):
        from rcm_mc.ui.market_intel_page import _subvertical_of
        label, rank = _subvertical_of("SOMETHING_NEW")
        self.assertEqual(label, "Other operators")
        self.assertEqual(rank, 9)


class TestPageRender(unittest.TestCase):
    def setUp(self):
        from rcm_mc.ui.market_intel_page import render_market_intel_page
        self.h = render_market_intel_page()

    def test_no_traceback(self):
        self.assertNotIn("Traceback", self.h)

    def test_subvertical_grid_and_hhi(self):
        self.assertIn("mi-vert-grid", self.h)
        self.assertIn("Revenue HHI", self.h)

    def test_color_threshold_caption(self):
        # The table caption documents the green / red shading. (The "<8x"
        # comparison renders HTML-escaped, so assert on the plain words.)
        self.assertIn("premium multiple", self.h)
        self.assertIn("discount", self.h)
        self.assertIn("12x", self.h)

    def test_research_reference_box_gone(self):
        # The beige "research reference / mixed data" purpose box was removed
        # so the public-operator hub is the focal point under the hero.
        self.assertNotIn("Frame a target against", self.h)


if __name__ == "__main__":
    unittest.main()
