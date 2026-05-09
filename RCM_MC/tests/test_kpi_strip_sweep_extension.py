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


class FivePageBatchMigrated(unittest.TestCase):
    """One-line check that the five-page batch now uses kpi_strip
    rather than the bespoke cad-kpi-grid markup. Each renderer
    produces a self-contained KPI block; the test exercises the
    cleanest reachable path per page."""

    def test_command_center_kpi_strip(self) -> None:
        # command_center is hard to call directly without a portfolio
        # store + corpus fixture; check the source instead.
        import inspect
        from rcm_mc.ui import command_center
        src = inspect.getsource(command_center)
        self.assertIn("kpi_strip([", src)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_market_analysis_kpi_strip(self) -> None:
        import inspect
        from rcm_mc.ui import market_analysis_page
        src = inspect.getsource(market_analysis_page)
        self.assertIn("kpi_strip([", src)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_demand_kpi_strip(self) -> None:
        import inspect
        from rcm_mc.ui import demand_page
        src = inspect.getsource(demand_page)
        self.assertIn("kpi_strip([", src)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_market_data_kpi_strip(self) -> None:
        import inspect
        from rcm_mc.ui import market_data_page
        src = inspect.getsource(market_data_page)
        # Two KPI blocks migrated; both use kpi_strip.
        self.assertGreaterEqual(src.count("kpi_strip("), 2)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_analytics_pages_kpi_strip(self) -> None:
        import inspect
        from rcm_mc.ui import analytics_pages
        src = inspect.getsource(analytics_pages)
        # Four KPI blocks migrated; all use kpi_strip.
        self.assertGreaterEqual(src.count("kpi_strip("), 4)
        self.assertNotIn('class="cad-kpi-grid"', src)


class SixPageBatchTwoMigrated(unittest.TestCase):
    """Batch 2: pe_returns covenant block, pipeline_page,
    portfolio_bridge, conference, ebitda_bridge (×2 blocks),
    deal_dashboard. Source-only checks because some pages need
    heavy fixture setup to render end-to-end."""

    def _src(self, module_name: str) -> str:
        import importlib
        import inspect
        return inspect.getsource(importlib.import_module(module_name))

    def test_pe_returns_fully_migrated(self) -> None:
        src = self._src("rcm_mc.ui.pe_returns_page")
        self.assertGreaterEqual(src.count("kpi_strip("), 2)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_pipeline_page_migrated(self) -> None:
        src = self._src("rcm_mc.ui.pipeline_page")
        self.assertIn("kpi_strip(", src)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_portfolio_bridge_migrated(self) -> None:
        src = self._src("rcm_mc.ui.portfolio_bridge_page")
        self.assertIn("kpi_strip(", src)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_conference_page_migrated(self) -> None:
        src = self._src("rcm_mc.ui.conference_page")
        self.assertIn("kpi_strip(", src)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_ebitda_bridge_migrated_two_blocks(self) -> None:
        src = self._src("rcm_mc.ui.ebitda_bridge_page")
        self.assertGreaterEqual(src.count("kpi_strip("), 2)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_deal_dashboard_migrated(self) -> None:
        src = self._src("rcm_mc.ui.deal_dashboard")
        self.assertIn("kpi_strip(", src)
        self.assertNotIn('class="cad-kpi-grid"', src)


class SixPageBatchThreeMigrated(unittest.TestCase):
    """Batch 3: hospital_stats, hospital_history, deal_quick_view,
    predictive_screener, denial_page, regression_page."""

    def _src(self, module_name: str) -> str:
        import importlib
        import inspect
        return inspect.getsource(importlib.import_module(module_name))

    def test_hospital_stats_migrated(self) -> None:
        src = self._src("rcm_mc.ui.hospital_stats_page")
        self.assertIn("kpi_strip(", src)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_hospital_history_migrated(self) -> None:
        src = self._src("rcm_mc.ui.hospital_history")
        self.assertIn("kpi_strip(", src)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_deal_quick_view_migrated(self) -> None:
        src = self._src("rcm_mc.ui.deal_quick_view")
        self.assertIn("kpi_strip(", src)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_predictive_screener_migrated(self) -> None:
        src = self._src("rcm_mc.ui.predictive_screener")
        self.assertIn("kpi_strip(", src)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_denial_page_migrated(self) -> None:
        src = self._src("rcm_mc.ui.denial_page")
        self.assertIn("kpi_strip(", src)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_regression_page_migrated(self) -> None:
        src = self._src("rcm_mc.ui.regression_page")
        self.assertIn("kpi_strip(", src)
        self.assertNotIn('class="cad-kpi-grid"', src)


class SixPageBatchFourMigrated(unittest.TestCase):
    """Batch 4: competitive_intel, model_validation, ml_insights,
    memo_page, fund_learning, home_v2."""

    def _src(self, module_name: str) -> str:
        import importlib
        import inspect
        return inspect.getsource(importlib.import_module(module_name))

    def test_competitive_intel_migrated(self) -> None:
        src = self._src("rcm_mc.ui.competitive_intel_page")
        self.assertIn("kpi_strip(", src)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_model_validation_migrated(self) -> None:
        src = self._src("rcm_mc.ui.model_validation_page")
        self.assertIn("kpi_strip(", src)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_ml_insights_migrated(self) -> None:
        src = self._src("rcm_mc.ui.ml_insights_page")
        # Two KPI blocks migrated; both use kpi_strip.
        self.assertGreaterEqual(src.count("kpi_strip("), 2)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_memo_page_migrated(self) -> None:
        src = self._src("rcm_mc.ui.memo_page")
        # Three KPI blocks migrated.
        self.assertGreaterEqual(src.count("kpi_strip("), 3)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_fund_learning_migrated(self) -> None:
        src = self._src("rcm_mc.ui.fund_learning_page")
        self.assertIn("kpi_strip(", src)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_home_v2_migrated_two_blocks(self) -> None:
        src = self._src("rcm_mc.ui.home_v2")
        # Pulse + Portfolio Summary blocks both migrated.
        self.assertGreaterEqual(src.count("kpi_strip("), 2)
        self.assertNotIn('class="cad-kpi-grid"', src)
        # Local _kpi_card helper retired now that the only consumer
        # is gone — guards against accidental re-introduction.
        self.assertNotIn("def _kpi_card(", src)


class SixPageBatchFiveMigrated(unittest.TestCase):
    """Batch 5: data_dashboard, portfolio_monitor, value_tracking,
    scenario_modeler, pe_tools, advanced_tools."""

    def _src(self, module_name: str) -> str:
        import importlib
        import inspect
        return inspect.getsource(importlib.import_module(module_name))

    def test_data_dashboard_migrated(self) -> None:
        src = self._src("rcm_mc.ui.data_dashboard")
        self.assertIn("kpi_strip(", src)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_portfolio_monitor_migrated(self) -> None:
        src = self._src("rcm_mc.ui.portfolio_monitor_page")
        self.assertIn("kpi_strip(", src)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_value_tracking_migrated(self) -> None:
        src = self._src("rcm_mc.ui.value_tracking_page")
        self.assertIn("kpi_strip(", src)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_scenario_modeler_migrated(self) -> None:
        src = self._src("rcm_mc.ui.scenario_modeler_page")
        self.assertIn("kpi_strip(", src)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_pe_tools_migrated_three_blocks(self) -> None:
        src = self._src("rcm_mc.ui.pe_tools_page")
        # Three KPI blocks across value bridge, anomalies, service lines.
        self.assertGreaterEqual(src.count("kpi_strip("), 3)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_advanced_tools_migrated_four_blocks(self) -> None:
        src = self._src("rcm_mc.ui.advanced_tools_page")
        # Four KPI blocks across debt, challenge solver, 990, trends.
        self.assertGreaterEqual(src.count("kpi_strip("), 4)
        self.assertNotIn('class="cad-kpi-grid"', src)


class FivePageBatchSixMigrated(unittest.TestCase):
    """Batch 6 — final sweep batch: pressure, diligence, data_room,
    team, bayesian. After this batch, no production page in
    ``rcm_mc/ui/`` emits the legacy ``class=\"cad-kpi-grid\"`` markup."""

    def _src(self, module_name: str) -> str:
        import importlib
        import inspect
        return inspect.getsource(importlib.import_module(module_name))

    def test_pressure_migrated(self) -> None:
        src = self._src("rcm_mc.ui.pressure_page")
        self.assertIn("kpi_strip(", src)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_diligence_migrated_two_blocks(self) -> None:
        src = self._src("rcm_mc.ui.diligence_page")
        # Questions + playbook blocks both migrated.
        self.assertGreaterEqual(src.count("kpi_strip("), 2)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_data_room_migrated_two_blocks(self) -> None:
        src = self._src("rcm_mc.ui.data_room_page")
        # Top KPIs + EBITDA bridge impact blocks both migrated.
        self.assertGreaterEqual(src.count("kpi_strip("), 2)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_team_migrated(self) -> None:
        src = self._src("rcm_mc.ui.team_page")
        self.assertIn("kpi_strip(", src)
        self.assertNotIn('class="cad-kpi-grid"', src)

    def test_bayesian_migrated(self) -> None:
        src = self._src("rcm_mc.ui.bayesian_page")
        self.assertIn("kpi_strip(", src)
        self.assertNotIn('class="cad-kpi-grid"', src)


class CadKpiGridFullyEliminated(unittest.TestCase):
    """Cross-cutting guard: after all six sweep batches, no module
    under ``rcm_mc/ui/`` emits the legacy ``class=\"cad-kpi-grid\"``
    pattern. Catches any future page that re-introduces it."""

    def test_no_module_emits_legacy_grid_markup(self) -> None:
        import pathlib
        ui_dir = pathlib.Path(__file__).resolve().parent.parent / "rcm_mc" / "ui"
        offenders: list[str] = []
        for py in ui_dir.rglob("*.py"):
            try:
                src = py.read_text(encoding="utf-8")
            except OSError:
                continue
            if 'class="cad-kpi-grid"' in src:
                offenders.append(str(py.relative_to(ui_dir)))
        self.assertEqual(
            offenders, [],
            f"Legacy cad-kpi-grid markup found in: {offenders}",
        )


class CadKpiTilesFullyEliminated(unittest.TestCase):
    """Stronger guard: also catches bare ``class=\"cad-kpi\"`` /
    ``cad-kpi-value`` / ``cad-kpi-label`` tile usages that the
    original sweep grep missed (they appeared inside hand-rolled
    flex/grid wrappers without the ``cad-kpi-grid`` class). Server
    routes are included in scope since some pages emit HTML
    directly from ``server.py``."""

    LEGACY_CLASS_ATTRS = (
        'class="cad-kpi"',
        'class="cad-kpi-value"',
        'class="cad-kpi-label"',
    )

    def test_no_module_emits_legacy_tile_markup(self) -> None:
        import pathlib
        repo_root = pathlib.Path(__file__).resolve().parent.parent
        scan_roots = [repo_root / "rcm_mc" / "ui", repo_root / "rcm_mc" / "server.py"]
        offenders: list[str] = []
        for root in scan_roots:
            paths = root.rglob("*.py") if root.is_dir() else [root]
            for py in paths:
                try:
                    src = py.read_text(encoding="utf-8")
                except OSError:
                    continue
                for attr in self.LEGACY_CLASS_ATTRS:
                    if attr in src:
                        offenders.append(f"{py.relative_to(repo_root)} :: {attr}")
                        break
        self.assertEqual(
            offenders, [],
            f"Legacy cad-kpi tile markup found in: {offenders}",
        )


if __name__ == "__main__":
    unittest.main()
