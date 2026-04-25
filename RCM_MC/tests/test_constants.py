"""Tests for the central constants registry."""
from __future__ import annotations

import unittest


class TestSanityRanges(unittest.TestCase):
    def test_denial_rate_range(self):
        from rcm_mc.constants import DENIAL_RATE_RANGE
        lo, hi = DENIAL_RATE_RANGE
        self.assertEqual(lo, 0.0)
        self.assertGreater(hi, 0.20)
        self.assertLess(hi, 1.0)

    def test_days_in_ar_range(self):
        from rcm_mc.constants import DAYS_IN_AR_RANGE
        lo, hi = DAYS_IN_AR_RANGE
        self.assertGreater(lo, 0)
        self.assertLess(lo, 30)
        self.assertGreater(hi, 80)

    def test_collection_rate_range(self):
        from rcm_mc.constants import (
            COLLECTION_RATE_RANGE,
        )
        lo, hi = COLLECTION_RATE_RANGE
        self.assertGreater(lo, 0.5)
        self.assertEqual(hi, 1.00)

    def test_operating_margin_range(self):
        from rcm_mc.constants import (
            OPERATING_MARGIN_RANGE,
        )
        lo, hi = OPERATING_MARGIN_RANGE
        self.assertLess(lo, 0)
        self.assertGreater(hi, 0)


class TestDistressThresholds(unittest.TestCase):
    def test_margin_threshold_negative(self):
        from rcm_mc.constants import (
            DISTRESS_MARGIN_THRESHOLD,
        )
        self.assertLess(DISTRESS_MARGIN_THRESHOLD, 0)

    def test_days_cash_ordering(self):
        from rcm_mc.constants import (
            DAYS_CASH_DISTRESS,
            DAYS_CASH_WARNING,
            DAYS_CASH_HEALTHY,
        )
        self.assertLess(
            DAYS_CASH_DISTRESS, DAYS_CASH_WARNING)
        self.assertLess(
            DAYS_CASH_WARNING, DAYS_CASH_HEALTHY)


class TestFreshnessBands(unittest.TestCase):
    def test_band_ordering(self):
        from rcm_mc.constants import (
            FRESHNESS_FRESH_DAYS,
            FRESHNESS_STALE_DAYS,
            FRESHNESS_FULL_DECAY_DAYS,
        )
        self.assertLess(
            FRESHNESS_FRESH_DAYS,
            FRESHNESS_STALE_DAYS)
        self.assertLess(
            FRESHNESS_STALE_DAYS,
            FRESHNESS_FULL_DECAY_DAYS)


class TestCacheTTLs(unittest.TestCase):
    def test_panel_ttl_reasonable(self):
        from rcm_mc.constants import (
            DEFAULT_PANEL_TTL_SECONDS,
        )
        # 5 minutes
        self.assertEqual(
            DEFAULT_PANEL_TTL_SECONDS, 300)

    def test_catalog_ttl_shorter(self):
        from rcm_mc.constants import (
            DATA_CATALOG_TTL_SECONDS,
            DEFAULT_PANEL_TTL_SECONDS,
        )
        # Catalog reflects live SQL; should refresh more
        # often than synthesized panels
        self.assertLess(
            DATA_CATALOG_TTL_SECONDS,
            DEFAULT_PANEL_TTL_SECONDS)


class TestUIBreakpoints(unittest.TestCase):
    def test_ordering(self):
        from rcm_mc.constants import (
            BREAKPOINT_TABLET_PX,
            BREAKPOINT_LAPTOP_PX,
            BREAKPOINT_DESKTOP_PX,
        )
        self.assertLess(
            BREAKPOINT_TABLET_PX, BREAKPOINT_LAPTOP_PX)
        self.assertLess(
            BREAKPOINT_LAPTOP_PX, BREAKPOINT_DESKTOP_PX)

    def test_matches_responsive_module(self):
        """Constants must agree with the live values used in
        responsive.py — divergence breaks visual consistency."""
        from rcm_mc.constants import (
            BREAKPOINT_TABLET_PX,
            BREAKPOINT_LAPTOP_PX,
        )
        from rcm_mc.ui.responsive import BREAKPOINTS
        self.assertEqual(
            f"{BREAKPOINT_TABLET_PX}px",
            BREAKPOINTS["tablet_min"])
        self.assertEqual(
            f"{BREAKPOINT_LAPTOP_PX}px",
            BREAKPOINTS["laptop_min"])


class TestMLDefaults(unittest.TestCase):
    def test_alpha_positive(self):
        from rcm_mc.constants import DEFAULT_RIDGE_ALPHA
        self.assertGreater(DEFAULT_RIDGE_ALPHA, 0)

    def test_kfolds_reasonable(self):
        from rcm_mc.constants import DEFAULT_K_FOLDS
        self.assertGreaterEqual(DEFAULT_K_FOLDS, 3)
        self.assertLessEqual(DEFAULT_K_FOLDS, 10)

    def test_nominal_coverage_in_unit_interval(self):
        from rcm_mc.constants import (
            DEFAULT_NOMINAL_COVERAGE,
        )
        self.assertGreater(
            DEFAULT_NOMINAL_COVERAGE, 0)
        self.assertLess(DEFAULT_NOMINAL_COVERAGE, 1)


class TestPeerComparison(unittest.TestCase):
    def test_significance_band(self):
        from rcm_mc.constants import (
            PEER_SIGNIFICANCE_BAND,
        )
        self.assertGreater(PEER_SIGNIFICANCE_BAND, 0)
        self.assertLess(PEER_SIGNIFICANCE_BAND, 1)

    def test_target_percentile(self):
        from rcm_mc.constants import (
            PEER_TARGET_PERCENTILE,
        )
        self.assertGreater(PEER_TARGET_PERCENTILE, 50)
        self.assertLess(PEER_TARGET_PERCENTILE, 100)


class TestHealthScoreBands(unittest.TestCase):
    def test_band_ordering(self):
        from rcm_mc.constants import (
            HEALTH_SCORE_HIGH,
            HEALTH_SCORE_MID,
        )
        self.assertGreater(
            HEALTH_SCORE_HIGH, HEALTH_SCORE_MID)


if __name__ == "__main__":
    unittest.main()
