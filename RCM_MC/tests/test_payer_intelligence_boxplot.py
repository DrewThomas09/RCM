"""Pin for the MOIC box-plot on /payer-intelligence.

Replaces the bland regime-stats table with a glanceable box-and-
whisker view of MOIC distribution per payer-mix regime — partner
sees at a glance which regime has the widest spread and which
band the median lands in.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace


def _reg(**kwargs):
    return SimpleNamespace(
        regime=kwargs.get("regime", "X"),
        commercial_range=kwargs.get("commercial_range", (0.0, 1.0)),
        n_deals=kwargs.get("n_deals", 1),
        moic_p25=kwargs.get("moic_p25", 1.0),
        moic_p50=kwargs.get("moic_p50", 1.5),
        moic_p75=kwargs.get("moic_p75", 2.0),
        irr_p50=kwargs.get("irr_p50", 0.12),
        avg_commercial_pct=kwargs.get("avg_commercial_pct", 0.4),
        avg_medicare_pct=kwargs.get("avg_medicare_pct", 0.4),
        avg_medicaid_pct=kwargs.get("avg_medicaid_pct", 0.2),
        loss_rate=kwargs.get("loss_rate", 0.2),
    )


class RegimeMoicBoxplotTests(unittest.TestCase):
    def test_renders_one_box_per_regime(self):
        from rcm_mc.ui.chartis.payer_intelligence_page import (
            _regime_moic_boxplot,
        )
        svg = _regime_moic_boxplot([
            _reg(regime="Gov-heavy", moic_p25=1.1, moic_p50=1.5, moic_p75=2.0),
            _reg(regime="Balanced",  moic_p25=1.6, moic_p50=2.2, moic_p75=2.9),
            _reg(regime="Commercial",moic_p25=2.0, moic_p50=2.8, moic_p75=3.6),
        ])
        self.assertTrue(svg.startswith("<svg"))
        # 3 boxes (one per regime)
        self.assertEqual(svg.count("<rect"), 3)
        # Regime names render
        self.assertIn("Gov-heavy", svg)
        self.assertIn("Balanced", svg)
        self.assertIn("Commercial", svg)
        # Y-axis label
        self.assertIn("MOIC distribution", svg)

    def test_box_color_keys_off_p50_band(self):
        from rcm_mc.ui.chartis.payer_intelligence_page import (
            _regime_moic_boxplot,
        )
        svg = _regime_moic_boxplot([
            _reg(regime="green", moic_p50=2.8),
            _reg(regime="amber", moic_p50=2.0),
            _reg(regime="red",   moic_p50=1.0),
        ])
        self.assertIn("#0a8a5f", svg)  # green band
        self.assertIn("#b8732a", svg)  # amber band
        self.assertIn("#b5321e", svg)  # red band

    def test_returns_empty_for_no_data(self):
        from rcm_mc.ui.chartis.payer_intelligence_page import (
            _regime_moic_boxplot,
        )
        self.assertEqual(_regime_moic_boxplot([]), "")

    def test_p50_label_above_each_box(self):
        from rcm_mc.ui.chartis.payer_intelligence_page import (
            _regime_moic_boxplot,
        )
        svg = _regime_moic_boxplot([
            _reg(regime="A", moic_p50=2.2),
            _reg(regime="B", moic_p50=1.7),
        ])
        # Median values labelled
        self.assertIn("2.2x", svg)
        self.assertIn("1.7x", svg)


if __name__ == "__main__":
    unittest.main()
