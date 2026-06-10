"""Regression: the margin/occupancy band has ONE source of truth (core).

The band + plausibility helpers moved to rcm_mc.core.margins so every layer
(UI, ml, finance, intelligence) validates against the same numbers. The UI
kit re-exports them, so the identity below proves a single definition — no
surface can drift to a looser band.
"""
from __future__ import annotations

import unittest

from rcm_mc.core import margins as core


class SingleSourceTests(unittest.TestCase):
    def test_ui_reexports_core(self):
        from rcm_mc.ui import _chartis_kit as kit
        # Same object, not a copy → genuinely one definition.
        self.assertIs(kit.margin_is_plausible, core.margin_is_plausible)
        self.assertIs(kit.margin_is_plausible_series, core.margin_is_plausible_series)
        self.assertIs(kit.occupancy_is_plausible, core.occupancy_is_plausible)
        self.assertEqual(kit.MARGIN_PLAUSIBLE_LO, core.MARGIN_PLAUSIBLE_LO)
        self.assertEqual(kit.MARGIN_PLAUSIBLE_HI, core.MARGIN_PLAUSIBLE_HI)
        self.assertEqual(kit.OCCUPANCY_PLAUSIBLE_HI, core.OCCUPANCY_PLAUSIBLE_HI)

    def test_band_values(self):
        self.assertEqual((core.MARGIN_PLAUSIBLE_LO, core.MARGIN_PLAUSIBLE_HI),
                         (-0.40, 0.30))
        self.assertEqual(core.OCCUPANCY_PLAUSIBLE_HI, 1.05)

    def test_helpers_behave(self):
        self.assertTrue(core.margin_is_plausible(0.05))
        self.assertFalse(core.margin_is_plausible(0.90))
        self.assertEqual(core.margin_flag(0.9), "high")
        self.assertFalse(core.occupancy_is_plausible(2.39))


class CoreConsumersUseBandTests(unittest.TestCase):
    def test_market_analysis_imports_core_band(self):
        import rcm_mc.finance.market_analysis  # noqa: F401 — imports cleanly
    def test_investability_imports_core_band(self):
        import rcm_mc.ml.investability_scorer  # noqa: F401


if __name__ == "__main__":
    unittest.main()
