"""tests for the broader Phase-3 kpi_strip sweep.

PROMPTS.md Phase 3 / Prompt 26 follow-up. The original canary
landed on Portfolio overview; this file pins the migration of two
more pages that previously used the bespoke ``cad-kpi-grid``
markup:

  * waterfall_page (LP/GP cashflow waterfall)
  * pe_returns_page (deal-level return summary)

Both pages preserve their legacy ``irr_color`` variable for
downstream callouts that read it; the kpi-strip's tone field
takes over the visible coloring on the strip itself.
"""
from __future__ import annotations

import unittest


class WaterfallPageMigrated(unittest.TestCase):

    def test_uses_kpi_strip_not_cad_kpi_grid(self) -> None:
        from rcm_mc.ui.waterfall_page import render_waterfall_page

        result = {
            "gross_irr": 0.223,
            "gross_moic": 2.80,
            "lp_total": 80_000_000,
            "gp_total": 20_000_000,
            "lp_moic": 2.5,
            "lp_irr": 0.20,
            "gp_moic": 4.0,
            "invested": 100_000_000,
            "exit_proceeds": 280_000_000,
            "hold_years": 5.0,
            "tiers": [],
        }
        html = render_waterfall_page(
            deal_id="aurora", deal_name="Project Aurora",
            result=result,
        )
        self.assertIn("kpi-strip", html)
        # Five KPIs.
        self.assertIn("repeat(5,1fr)", html)
        # All five labels visible.
        for label in (
            "GROSS IRR", "GROSS MOIC", "INVESTED",
            "EXIT PROCEEDS", "HOLD PERIOD",
        ):
            with self.subTest(label=label):
                self.assertIn(label, html)

    def test_irr_tone_drives_kpi_color(self) -> None:
        from rcm_mc.ui.waterfall_page import render_waterfall_page

        # IRR > 0.20 → tone-positive on the IRR tile.
        result = {
            "gross_irr": 0.25, "gross_moic": 3.0,
            "lp_total": 1, "gp_total": 1,
            "lp_moic": 1, "lp_irr": 0, "gp_moic": 1,
            "invested": 1, "exit_proceeds": 1, "hold_years": 1,
            "tiers": [],
        }
        html = render_waterfall_page(
            deal_id="x", deal_name="X", result=result,
        )
        self.assertIn("tone-positive", html)


class PEReturnsPageMigrated(unittest.TestCase):

    def test_uses_kpi_strip_not_cad_kpi_grid(self) -> None:
        from rcm_mc.ui.pe_returns_page import render_returns_page

        returns = {
            "irr": 0.223, "moic": 2.80,
            "entry_equity": 250_000_000,
            "exit_proceeds": 700_000_000,
            "total_distributions": 700_000_000,
            "hold_years": 5.0,
        }
        html = render_returns_page(
            "aurora", "Project Aurora", returns, covenant={},
        )
        self.assertIn("kpi-strip", html)
        # Six KPIs.
        self.assertIn("repeat(6,1fr)", html)
        for label in (
            "IRR", "MOIC", "ENTRY EQUITY", "EXIT PROCEEDS",
            "TOTAL DISTRIBUTIONS", "HOLD PERIOD",
        ):
            with self.subTest(label=label):
                self.assertIn(label, html)


if __name__ == "__main__":
    unittest.main()
