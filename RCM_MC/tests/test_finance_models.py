"""Tests for finance models: DCF, LBO, regression, market analysis.

DCF:
 1. build_dcf produces valid projections.
 2. Sensitivity matrix has multiple WACC/growth combos.
 3. API endpoint returns DCF for a deal.

LBO:
 4. build_lbo produces sources & uses + returns.
 5. MOIC > 1 for reasonable assumptions.
 6. API endpoint returns LBO for a deal.

REGRESSION:
 7. run_regression returns coefficients and R-squared.
 8. Portfolio regression endpoint works.

MARKET:
 9. analyze_market returns competitors and moat.
10. API endpoint returns market analysis.
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request

import pandas as pd

from rcm_mc.finance.dcf_model import build_dcf, build_dcf_from_deal
from rcm_mc.finance.lbo_model import build_lbo, build_lbo_from_deal
from rcm_mc.finance.regression import run_regression
from rcm_mc.portfolio.store import PortfolioStore


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestDCF(unittest.TestCase):

    def test_dcf_produces_projections(self):
        result = build_dcf(revenue_base=400e6, ebitda_margin_base=0.12)
        self.assertEqual(len(result.projections), 5)
        self.assertGreater(result.enterprise_value, 0)
        self.assertGreater(result.terminal_value, 0)

    def test_dcf_sensitivity(self):
        result = build_dcf(revenue_base=400e6)
        sens = result.sensitivity["wacc_vs_terminal_growth"]
        self.assertGreater(len(sens), 10)
        self.assertIn("enterprise_value", sens[0])

    def test_dcf_from_deal(self):
        result = build_dcf_from_deal({"net_revenue": 400e6, "current_ebitda": 50e6})
        self.assertGreater(result.enterprise_value, 0)

    def test_dcf_projection_exposes_fcf_under_ui_key(self):
        """Regression: the DCF UI renders projections with p.get('free_cash_flow').

        The model's internal field name is ``fcf``; callers in
        ``ui/models_page.py`` read ``free_cash_flow`` and ``pv_fcf``.
        The serialized projection dict must expose both keys so the
        table renders real numbers rather than em-dashes.
        """
        result = build_dcf(revenue_base=400e6, ebitda_margin_base=0.12)
        result_dict = result.to_dict()
        proj_dicts = result_dict["projections"]
        self.assertEqual(len(proj_dicts), 5)
        for p in proj_dicts:
            self.assertIn("free_cash_flow", p,
                          "UI projection dict must expose 'free_cash_flow'")
            self.assertIsInstance(p["free_cash_flow"], (int, float))
            # Legacy 'fcf' key is preserved for any downstream consumers
            # that use the short name.
            self.assertIn("fcf", p)
            self.assertEqual(p["free_cash_flow"], p["fcf"])

    def test_dcf_projection_exposes_pv_fcf_per_year(self):
        """Regression: the DCF UI renders a PV(FCF) column per year.

        The aggregate ``pv_cash_flows`` was computed once in
        ``build_dcf`` and the per-year discounted cash flow was never
        persisted on the projection row. Sum of per-year ``pv_fcf``
        must equal the aggregate ``pv_cash_flows`` to within rounding.
        """
        result = build_dcf(revenue_base=400e6, ebitda_margin_base=0.12,
                           wacc=0.10)
        proj_dicts = result.to_dict()["projections"]
        for p in proj_dicts:
            self.assertIn("pv_fcf", p,
                          "UI projection dict must expose 'pv_fcf'")
            self.assertIsInstance(p["pv_fcf"], (int, float))
        total_pv = sum(p["pv_fcf"] for p in proj_dicts)
        self.assertAlmostEqual(total_pv, result.pv_cash_flows, places=0)

    def test_dcf_api(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha",
                              profile={"net_revenue": 400e6, "current_ebitda": 50e6})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/dcf",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("projections", body)
                self.assertIn("enterprise_value", body)
                self.assertIn("sensitivity", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestLBO(unittest.TestCase):

    def test_lbo_produces_returns(self):
        result = build_lbo(entry_ebitda=50e6, revenue_base=400e6)
        self.assertEqual(len(result.projections), 5)
        self.assertGreater(result.returns.moic, 0)
        self.assertGreater(result.returns.equity_invested, 0)

    def test_lbo_moic_reasonable(self):
        result = build_lbo(entry_ebitda=50e6, revenue_base=400e6)
        self.assertGreater(result.returns.moic, 1.0)
        self.assertLess(result.returns.moic, 10.0)

    def test_lbo_sources_uses_balance(self):
        result = build_lbo(entry_ebitda=50e6)
        su = result.sources_and_uses
        self.assertAlmostEqual(su.total_sources, su.total_uses, places=0)

    def test_lbo_entry_and_exit_are_consistent_on_revenue_override(self):
        """Regression: MOIC=64x / IRR=130% was the visible symptom.

        When build_lbo is called with revenue_base overridden but not
        entry_ebitda, the projection loop uses the new revenue × margin
        while the entry capitalization still uses the default
        entry_ebitda of $50M. That mismatch balloons MOIC by ~30x.
        """
        result = build_lbo(revenue_base=8_944_000_000, ebitda_margin_base=0.12)
        a = result.assumptions
        expected_entry_ebitda = a.revenue_base * a.ebitda_margin_base
        self.assertAlmostEqual(
            a.entry_ebitda, expected_entry_ebitda, delta=1.0,
            msg=("entry_ebitda must be consistent with revenue_base × "
                 "ebitda_margin_base; mismatch produces absurd MOIC"),
        )
        self.assertLess(result.returns.moic, 10.0,
                        f"MOIC {result.returns.moic:.2f}x is implausible "
                        f"for a 5-yr LBO with 4% rev growth")
        self.assertGreater(result.returns.moic, 0.5)

    def test_lbo_from_deal_honors_margin(self):
        """Regression: server called build_lbo(ebitda_margin=...) but
        the dataclass field is ebitda_margin_base. The mismatched kwarg
        was silently dropped. build_lbo_from_deal must honour the
        profile's margin so callers don't stumble on kwarg drift.
        """
        result = build_lbo_from_deal({
            "net_revenue": 400_000_000,
            "ebitda_margin": 0.15,
        })
        self.assertAlmostEqual(
            result.assumptions.ebitda_margin_base, 0.15, places=3,
            msg="build_lbo_from_deal must honour the profile's margin",
        )

    def test_lbo_api(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha",
                              profile={"net_revenue": 400e6, "current_ebitda": 50e6})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/lbo",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("sources_and_uses", body)
                self.assertIn("returns", body)
                self.assertIn("moic", body["returns"])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_lbo_fmt_pct_handles_large_irr(self):
        """Regression: _fmt_pct auto-detected fraction vs. already-%
        using abs(v) < 1, so an IRR of 1.3022 (= 130.2%) rendered as
        '1.3%'. Partners mis-read that as a broken deal.

        The IRR field on LBOReturns is a fraction (0.22 = 22%). The
        formatter must treat it as a fraction regardless of magnitude
        when an explicit ``is_fraction=True`` signal is passed.
        """
        from rcm_mc.ui.models_page import _fmt_pct
        self.assertEqual(_fmt_pct(0.22, is_fraction=True), "22.0%")
        self.assertEqual(_fmt_pct(1.3022, is_fraction=True), "130.2%")
        # Legacy auto-detect path preserved for assumptions like
        # WACC=0.10 — still rendered as 10.0%.
        self.assertEqual(_fmt_pct(0.10), "10.0%")


class TestRegression(unittest.TestCase):

    def test_regression_runs(self):
        df = pd.DataFrame({
            "denial_rate": [10, 12, 15, 18, 20, 14, 16],
            "bed_count": [200, 150, 300, 250, 180, 220, 280],
            "days_in_ar": [45, 50, 55, 60, 48, 52, 58],
        })
        result = run_regression(df, "denial_rate", ["bed_count", "days_in_ar"])
        self.assertEqual(result.target, "denial_rate")
        self.assertEqual(result.n_observations, 7)
        self.assertGreaterEqual(result.r_squared, 0)
        self.assertLessEqual(result.r_squared, 1)
        self.assertEqual(len(result.coefficients), 2)

    def test_correlation_matrix(self):
        df = pd.DataFrame({
            "a": [1, 2, 3, 4, 5],
            "b": [2, 4, 6, 8, 10],
            "c": [5, 3, 1, 2, 4],
        })
        result = run_regression(df, "a", ["b", "c"])
        self.assertIn("a", result.correlation_matrix)
        self.assertGreater(len(result.top_correlations), 0)


class TestMarketAnalysis(unittest.TestCase):

    def test_market_api(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Southeast Health",
                              profile={"bed_count": 332, "net_revenue": 386e6,
                                       "state": "AL", "county": "HOUSTON"})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/market",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("market_size", body)
                self.assertIn("competitors", body)
                self.assertIn("moat", body)
                self.assertIn("moat_rating", body["moat"])
                self.assertIn("hhi_index", body["moat"])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
