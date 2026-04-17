"""Tests for portfolio HTML dashboard (Brick 50)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest

import pandas as pd

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.portfolio.portfolio_dashboard import build_portfolio_dashboard
from rcm_mc.portfolio.portfolio_snapshots import register_snapshot


def _seed_pe_run(dirpath: str, *,
                 moic: float = 2.5, irr: float = 0.20,
                 headroom: float = 1.1,
                 concerning: int = 0) -> None:
    os.makedirs(dirpath, exist_ok=True)
    with open(os.path.join(dirpath, "pe_bridge.json"), "w") as f:
        json.dump({"entry_ev": 450e6, "exit_ev": 659e6,
                   "entry_ebitda": 50e6, "entry_multiple": 9.0,
                   "exit_multiple": 10.0, "hold_years": 5.0}, f)
    with open(os.path.join(dirpath, "pe_returns.json"), "w") as f:
        json.dump({"moic": moic, "irr": irr}, f)
    with open(os.path.join(dirpath, "pe_covenant.json"), "w") as f:
        json.dump({"actual_leverage": 5.4,
                   "covenant_headroom_turns": headroom}, f)
    if concerning:
        pd.DataFrame({
            "severity": ["concerning"] * concerning + ["neutral"] * 3,
        }).to_csv(os.path.join(dirpath, "trend_signals.csv"), index=False)


def _read_text(path: str) -> str:
    with open(path) as f:
        return f.read()


class TestPortfolioDashboard(unittest.TestCase):
    def test_empty_portfolio_renders(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out)
            self.assertTrue(os.path.isfile(out))
            html = _read_text(out)
            self.assertIn("<html", html)
            self.assertIn("Portfolio Dashboard", html)
            # Headline shows 0 deals
            self.assertIn(">0<", html)

    def test_populated_dashboard_shows_kpis_and_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            run = os.path.join(tmp, "run1")
            _seed_pe_run(run, moic=2.55, irr=0.21)
            register_snapshot(store, "ccf_2026", "hold", run_dir=run)

            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out, title="Test Portfolio")
            html = _read_text(out)
            self.assertIn("Test Portfolio", html)
            self.assertIn("ccf_2026", html)
            self.assertIn("2.55x", html)
            # MOIC 2.55 ≥ 2.5 → green; green CSS class or color hex referenced
            self.assertIn("#10B981", html)

    def test_at_risk_block_highlights_tripped_deals(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            run_bad = os.path.join(tmp, "bad")
            run_good = os.path.join(tmp, "good")
            _seed_pe_run(run_bad, headroom=-0.5)
            _seed_pe_run(run_good, headroom=1.2)
            register_snapshot(store, "bad_deal", "hold", run_dir=run_bad)
            register_snapshot(store, "good_deal", "hold", run_dir=run_good)
            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out)
            html = _read_text(out)
            self.assertIn("At-risk deals", html)
            self.assertIn("bad_deal", html)
            self.assertIn("TRIPPED", html)

    def test_at_risk_clean_when_all_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            run = os.path.join(tmp, "good")
            _seed_pe_run(run, headroom=1.5)
            register_snapshot(store, "good", "hold", run_dir=run)
            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out)
            html = _read_text(out)
            self.assertIn("all covenants SAFE", html)

    def test_dashboard_includes_funnel_for_all_stages_with_deals(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            for stage in ("sourced", "ioi", "loi", "hold"):
                register_snapshot(store, f"deal_{stage}", stage)
            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out)
            html = _read_text(out)
            self.assertIn("Pipeline funnel", html)
            # Each populated stage label appears (title-cased)
            for label in ("Sourced", "Ioi", "Loi", "Hold"):
                self.assertIn(label, html)

    def test_signals_badges_rendered(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            run = os.path.join(tmp, "r")
            _seed_pe_run(run, concerning=3)
            register_snapshot(store, "x", "hold", run_dir=run)
            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out)
            html = _read_text(out)
            # Concerning count rendered as a red badge with "3c"
            self.assertIn(">3c<", html)


class TestHeldDealVariance(unittest.TestCase):
    """Brick 53: dashboard shows hold-period EBITDA variance per held deal."""

    def _held_deal_with_actuals(self, tmp: str, deal_id: str,
                                ebitda_series, plan: float = 50e6) -> PortfolioStore:
        """Helper: spin up a store with one held deal + N quarters of actuals."""
        from rcm_mc.pe.hold_tracking import record_quarterly_actuals
        store = PortfolioStore(os.path.join(tmp, "p.db"))
        run = os.path.join(tmp, deal_id + "_run")
        os.makedirs(run, exist_ok=True)
        with open(os.path.join(run, "pe_bridge.json"), "w") as f:
            json.dump({"entry_ebitda": plan, "entry_ev": plan * 9.0}, f)
        register_snapshot(store, deal_id, "hold", run_dir=run)
        # Quarters go 2025Q3 → 2026Q2
        quarters = ["2025Q3", "2025Q4", "2026Q1", "2026Q2"]
        for qtr, actual in zip(quarters, ebitda_series):
            record_quarterly_actuals(
                store, deal_id, qtr,
                actuals={"ebitda": actual}, plan={"ebitda": plan},
            )
        return store

    def test_block_rendered_for_held_deal_with_actuals(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._held_deal_with_actuals(
                tmp, "ccf", [49e6, 50e6, 51e6, 52e6],
            )
            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out)
            html = _read_text(out)
            self.assertIn("Hold-period variance", html)
            self.assertIn("ccf", html)
            # Last-4-quarters labels in the table
            for qtr in ("2025Q3", "2025Q4", "2026Q1", "2026Q2"):
                self.assertIn(qtr, html)
            self.assertIn("Cumulative drift", html)

    def test_improving_deal_shows_on_track_color(self):
        """EBITDA 49→52 against 50 plan → ~+2% cum → on-track green."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._held_deal_with_actuals(
                tmp, "ccf", [49e6, 50e6, 51e6, 52e6],
            )
            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out)
            html = _read_text(out)
            # Green color hex (#10B981) used for on-track severity
            self.assertIn("#10B981", html)

    def test_deteriorating_deal_shows_off_track_red(self):
        """EBITDA 14.5→11.5 against 15 plan → ~-18% drift → off_track."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._held_deal_with_actuals(
                tmp, "rural", [14.5e6, 14e6, 13e6, 11.5e6], plan=15e6,
            )
            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out)
            html = _read_text(out)
            # Red hex used for off-track
            self.assertIn("#EF4444", html)

    def test_block_omitted_when_no_held_deals_with_actuals(self):
        """Deals in sourced/ioi/loi must not appear (only hold/exit)."""
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            register_snapshot(store, "pipeline_only", "ioi")
            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out)
            html = _read_text(out)
            self.assertNotIn("Hold-period variance", html)

    def test_held_deal_without_actuals_is_skipped(self):
        """A held deal with no quarterly data shouldn't break the block."""
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            register_snapshot(store, "held_no_data", "hold")
            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out)
            html = _read_text(out)
            # Block not rendered because no rows qualify
            self.assertNotIn("Hold-period variance", html)

    def test_less_than_four_quarters_pads_leading_cells(self):
        """A deal with 2 quarters has its data on the right; left cells empty."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._held_deal_with_actuals(
                tmp, "two_qtr", [50e6, 51e6],
            )
            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out)
            html = _read_text(out)
            self.assertIn("Hold-period variance", html)
            # Newest quarter 2025Q4 appears; older padded with em-dash
            self.assertIn("2025Q4", html)


class TestLaggingInitiatives(unittest.TestCase):
    """Brick 59: dashboard surfaces lagging initiatives across held deals."""

    def test_lagging_section_renders_when_initiatives_off_track(self):
        from rcm_mc.rcm.initiative_tracking import record_initiative_actual
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            run = os.path.join(tmp, "r")
            _seed_pe_run(run)
            register_snapshot(store, "ccf", "hold", run_dir=run)
            # Under-deliver vs plan: prior_auth_improvement has 25k annual,
            # recording 1k over 2 quarters → -92% variance, off_track
            record_initiative_actual(store, deal_id="ccf",
                initiative_id="prior_auth_improvement",
                quarter="2026Q1", ebitda_impact=500)
            record_initiative_actual(store, deal_id="ccf",
                initiative_id="prior_auth_improvement",
                quarter="2026Q2", ebitda_impact=500)

            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out)
            text = _read_text(out)
            self.assertIn("Lagging initiatives", text)
            self.assertIn("prior_auth_improvement", text)

    def test_lagging_section_omitted_when_all_on_track(self):
        from rcm_mc.rcm.initiative_tracking import record_initiative_actual
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            run = os.path.join(tmp, "r")
            _seed_pe_run(run)
            register_snapshot(store, "ccf", "hold", run_dir=run)
            # coding_cdi_improvement: annual_run_rate 80000. 2-quarter plan =
            # 40000. Record 40000 total → on_track, must NOT surface here.
            record_initiative_actual(store, deal_id="ccf",
                initiative_id="coding_cdi_improvement",
                quarter="2026Q1", ebitda_impact=20000)
            record_initiative_actual(store, deal_id="ccf",
                initiative_id="coding_cdi_improvement",
                quarter="2026Q2", ebitda_impact=20000)

            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out)
            text = _read_text(out)
            self.assertNotIn("Lagging initiatives", text)

    def test_lagging_section_omitted_when_no_held_deals(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            register_snapshot(store, "pipeline", "ioi")
            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out)
            text = _read_text(out)
            self.assertNotIn("Lagging initiatives", text)


class TestMiniSparkline(unittest.TestCase):
    """B92: inline SVG sparkline column on each deal row."""

    def test_row_has_svg_when_deal_has_multi_quarter_data(self):
        from rcm_mc.pe.hold_tracking import record_quarterly_actuals
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            run = os.path.join(tmp, "r")
            _seed_pe_run(run)
            register_snapshot(store, "ccf", "hold", run_dir=run)
            for qtr, v in [("2025Q3", 11.5e6), ("2025Q4", 12e6),
                           ("2026Q1", 12.5e6)]:
                record_quarterly_actuals(store, "ccf", qtr,
                                         actuals={"ebitda": v},
                                         plan={"ebitda": 12e6})
            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out)
            text = _read_text(out)
            # Sparkline SVG present in row
            self.assertIn("<svg", text)
            self.assertIn("polyline", text)
            # "Recent" column header
            self.assertIn("<th>Recent</th>", text)

    def test_row_shows_dash_when_fewer_than_two_quarters(self):
        from rcm_mc.pe.hold_tracking import record_quarterly_actuals
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            run = os.path.join(tmp, "r")
            _seed_pe_run(run)
            register_snapshot(store, "ccf", "hold", run_dir=run)
            record_quarterly_actuals(store, "ccf", "2026Q1",
                                     actuals={"ebitda": 12e6},
                                     plan={"ebitda": 12e6})
            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out)
            text = _read_text(out)
            self.assertIn("<th>Recent</th>", text)
            # Exactly one deal → no sparkline polyline drawn
            self.assertNotIn("<polyline", text)


class TestRecentlyViewedCard(unittest.TestCase):
    """B98: dashboard has a recently-viewed card hydrated from localStorage."""

    def test_card_present_and_hidden_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            register_snapshot(store, "ccf", "hold")
            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out)
            text = _read_text(out)
            # Card skeleton exists
            self.assertIn('id="rcm-recent-deals-card"', text)
            self.assertIn('id="rcm-recent-deals-list"', text)
            # Hidden until JS finds localStorage entries
            self.assertIn('display: none', text)
            # Hydration script reads the well-known key
            self.assertIn("rcm-mc-recent-deals-v1", text)


class TestHeadlineKpiIds(unittest.TestCase):
    """B93: KPI cards carry stable IDs so filter JS can recompute them."""

    def test_kpi_cards_have_known_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            run = os.path.join(tmp, "r")
            _seed_pe_run(run)
            register_snapshot(store, "ccf", "hold", run_dir=run)
            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out)
            text = _read_text(out)
            for kpi_id in (
                "kpi-deal-count",
                "kpi-weighted-moic",
                "kpi-weighted-irr",
                "kpi-at-risk",
            ):
                self.assertIn(f'id="{kpi_id}"', text)

    def test_rows_carry_numeric_data_attrs_for_recompute(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            run = os.path.join(tmp, "r")
            _seed_pe_run(run, moic=2.55, irr=0.21)
            register_snapshot(store, "ccf", "hold", run_dir=run)
            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out)
            text = _read_text(out)
            self.assertIn('data-moic="2.55"', text)
            self.assertIn('data-irr="0.21"', text)
            self.assertIn("data-entry-ev=", text)


class TestFilterBar(unittest.TestCase):
    """B64: client-side filter bar on the deal table."""

    def test_filter_bar_controls_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            run = os.path.join(tmp, "r")
            _seed_pe_run(run)
            register_snapshot(store, "ccf", "hold", run_dir=run)
            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out)
            text = _read_text(out)
            for ctl in ("rcm-filter-text", "rcm-filter-stage",
                        "rcm-filter-covenant", "rcm-filter-concerning",
                        "rcm-filter-count"):
                self.assertIn(ctl, text)

    def test_deal_rows_carry_data_attributes(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            run = os.path.join(tmp, "r")
            _seed_pe_run(run, concerning=2)
            register_snapshot(store, "ccf_2026", "hold", run_dir=run)
            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out)
            text = _read_text(out)
            # Data attributes on each deal row drive the filter
            self.assertIn('data-deal-id="ccf_2026"', text)
            self.assertIn('data-stage="hold"', text)
            self.assertIn('data-covenant="SAFE"', text)
            self.assertIn('data-concerning="2"', text)

    def test_filter_js_embedded(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            register_snapshot(store, "ccf", "sourced")
            out = os.path.join(tmp, "dash.html")
            build_portfolio_dashboard(store, out)
            text = _read_text(out)
            # Script block listens on the filter controls
            self.assertIn("addEventListener", text)
            self.assertIn("applyFilter", text)


class TestPortfolioDashboardCLI(unittest.TestCase):
    def test_dashboard_subcommand_writes_file(self):
        import io
        import sys

        from rcm_mc.portfolio_cmd import main as portfolio_main

        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            out = os.path.join(tmp, "dash.html")
            buf = io.StringIO()
            saved = sys.stdout
            sys.stdout = buf
            try:
                rc = portfolio_main([
                    "--db", db, "dashboard", "--out", out, "--title", "TestCo",
                ])
            finally:
                sys.stdout = saved
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.isfile(out))
            html = _read_text(out)
            self.assertIn("TestCo", html)
