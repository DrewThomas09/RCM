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


class HospitalProfileMigrated(unittest.TestCase):
    """Both KPI grids on the hospital profile (fundamentals + quality
    metrics) migrated to kpi_strip. The quality strip is conditional
    — items appear only for metrics that are populated."""

    def _render(self, hospital_extra: dict | None = None) -> str:
        from types import SimpleNamespace
        from rcm_mc.ui.hospital_profile import render_hospital_profile

        hospital = {
            "ccn": "010001",
            "name": "Aurora Hospital",
            "state": "CA",
            "city": "San Francisco",
            "ownership": "Voluntary",
            "hospital_type": "Acute Care",
            "beds": 320,
            "net_patient_revenue": 450_000_000,
            "operating_margin": 0.08,
            "net_income": 32_000_000,
            "operating_expenses": 410_000_000,
            "medicare_share": 0.42,
            "medicaid_share": 0.18,
            "commercial_share": 0.32,
        }
        if hospital_extra:
            hospital.update(hospital_extra)
        score = SimpleNamespace(
            total=72.5,
            band="Good",
            components={
                "market_position": 25,
                "financial_health": 18,
                "operational_quality": 15,
                "competitive_moat": 14,
            },
            warnings=[],
        )
        return render_hospital_profile(hospital, score)

    def test_fundamentals_uses_kpi_strip(self) -> None:
        html = self._render()
        self.assertIn("kpi-strip", html)
        self.assertIn("kpi-strip-dense", html)
        for label in (
            "NET PATIENT REVENUE", "OPERATING MARGIN",
            "NET INCOME", "LICENSED BEDS",
            "REVENUE PER BED", "OPERATING EXPENSES",
        ):
            with self.subTest(label=label):
                self.assertIn(label, html)

    def test_no_legacy_cad_kpi_grid(self) -> None:
        html = self._render()
        self.assertNotIn('class="cad-kpi-grid"', html)

    def test_quality_strip_conditional_inclusion(self) -> None:
        html = self._render({
            "star_rating": 4,
            "readmission_rate": 13.2,
        })
        self.assertIn("CMS STAR RATING", html)
        self.assertIn("READMISSION RATE", html)
        self.assertNotIn("MORTALITY RATE", html)
        self.assertNotIn("PATIENT EXPERIENCE", html)


class ModelsDCFPageMigrated(unittest.TestCase):

    def test_dcf_kpis_use_kpi_strip(self) -> None:
        from rcm_mc.ui.models_page import render_dcf_page

        dcf = {
            "enterprise_value": 600_000_000,
            "pv_cash_flows": 220_000_000,
            "pv_terminal_value": 380_000_000,
            "terminal_value": 800_000_000,
            "assumptions": {"wacc": 0.10, "terminal_growth": 0.03},
            "projections": [],
        }
        html = render_dcf_page("aurora", "Project Aurora", dcf)
        self.assertIn("kpi-strip", html)
        self.assertIn("kpi-strip-dense", html)
        for label in (
            "ENTERPRISE VALUE", "PV OF CASH FLOWS",
            "PV OF TERMINAL VALUE", "TERMINAL VALUE",
            "WACC", "TERMINAL GROWTH",
        ):
            with self.subTest(label=label):
                self.assertIn(label, html)
        self.assertNotIn('class="cad-kpi-grid"', html)


class ModelsLBOPageMigrated(unittest.TestCase):

    def test_lbo_kpis_use_kpi_strip_with_irr_tone(self) -> None:
        from rcm_mc.ui.models_page import render_lbo_page

        lbo = {
            "returns": {
                "irr": 0.25, "moic": 3.0,
                "equity_invested": 250_000_000,
            },
            "summary": {
                "entry_ev": 600_000_000, "exit_ev": 900_000_000,
            },
            "sources": {"equity": 250_000_000, "debt": 350_000_000},
            "uses": {"purchase_price": 600_000_000},
            "tornado": [],
        }
        html = render_lbo_page("aurora", "Project Aurora", lbo)
        self.assertIn("kpi-strip", html)
        self.assertIn("tone-positive", html)
        self.assertNotIn('class="cad-kpi-grid"', html)


if __name__ == "__main__":
    unittest.main()
