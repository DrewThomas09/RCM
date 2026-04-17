"""Production hardening tests — edge cases, NaN handling, malformed inputs."""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error

import numpy as np
import pandas as pd


def _sample_hcris_with_nans(n=100):
    """HCRIS-like data with realistic missing values and edge cases."""
    rng = np.random.RandomState(42)
    df = pd.DataFrame({
        "ccn": [f"{i:06d}" for i in range(1, n + 1)],
        "name": [f"Hospital {i}" for i in range(1, n + 1)],
        "state": rng.choice(["CA", "TX", "NY", "FL"], n),
        "county": rng.choice(["County A", "County B", None], n),
        "beds": rng.choice([np.nan, 0, 25, 100, 300, 500], n).astype(float),
        "net_patient_revenue": rng.choice([np.nan, 0, 1e5, 5e7, 3e9], n),
        "operating_expenses": rng.choice([np.nan, 0, 1e5, 6e7, 3.5e9], n),
        "gross_patient_revenue": rng.choice([np.nan, 0, 5e8, 8e9], n),
        "medicare_day_pct": rng.choice([np.nan, 0, 0.3, 0.5, 0.8], n),
        "medicaid_day_pct": rng.choice([np.nan, 0, 0.1, 0.25], n),
        "total_patient_days": rng.choice([np.nan, 0, 5000, 50000], n).astype(float),
        "bed_days_available": rng.choice([np.nan, 0, 10000, 100000], n).astype(float),
    })
    return df


class TestSafeFloat(unittest.TestCase):

    def test_none(self):
        from rcm_mc.ui.ebitda_bridge_page import _safe_float
        self.assertEqual(_safe_float(None), 0.0)
        self.assertEqual(_safe_float(None, 42), 42)

    def test_nan(self):
        from rcm_mc.ui.ebitda_bridge_page import _safe_float
        self.assertEqual(_safe_float(float('nan')), 0.0)
        self.assertEqual(_safe_float(np.nan, 5), 5)

    def test_normal(self):
        from rcm_mc.ui.ebitda_bridge_page import _safe_float
        self.assertEqual(_safe_float(3.14), 3.14)
        self.assertEqual(_safe_float(0), 0.0)
        self.assertEqual(_safe_float(-5.0), -5.0)

    def test_string(self):
        from rcm_mc.ui.ebitda_bridge_page import _safe_float
        self.assertEqual(_safe_float("bad"), 0.0)
        self.assertEqual(_safe_float("3.5"), 3.5)

    def test_pandas_nan(self):
        from rcm_mc.ui.ebitda_bridge_page import _safe_float
        s = pd.Series([np.nan])
        self.assertEqual(_safe_float(s.iloc[0]), 0.0)


class TestDivisionSafety(unittest.TestCase):

    def test_regression_margin_no_inf(self):
        from rcm_mc.ui.regression_page import _add_computed_features
        df = _sample_hcris_with_nans()
        result = _add_computed_features(df)
        if "operating_margin" in result.columns:
            margins = result["operating_margin"].dropna()
            self.assertTrue(all(np.isfinite(margins)))
            self.assertTrue(all(margins >= -1))
            self.assertTrue(all(margins <= 1))

    def test_bridge_zero_revenue(self):
        from rcm_mc.ui.ebitda_bridge_page import _compute_bridge
        result = _compute_bridge(0, 0, medicare_pct=0.4)
        # With zero revenue, impact is minimal (only claims-volume-based cost savings)
        self.assertLess(abs(result["total_ebitda_impact"]), 1e6)

    def test_returns_grid_negative_ebitda(self):
        from rcm_mc.ui.ebitda_bridge_page import _compute_returns_grid
        grid = _compute_returns_grid(-10e6, 5e6, [10.0], [10.0])
        self.assertEqual(len(grid), 1)


class TestPagesWithBadData(unittest.TestCase):

    def test_ebitda_bridge_missing_hospital(self):
        from rcm_mc.ui.ebitda_bridge_page import render_ebitda_bridge
        df = _sample_hcris_with_nans(10)
        html = render_ebitda_bridge("999999", df)
        self.assertIn("not found", html)

    def test_ic_memo_missing_hospital(self):
        from rcm_mc.ui.ic_memo_page import render_ic_memo
        from rcm_mc.ui.regression_page import _add_computed_features
        df = _add_computed_features(_sample_hcris_with_nans(10))
        html = render_ic_memo("999999", df)
        self.assertIn("not found", html.lower() if html else "")

    def test_scenario_modeler_missing(self):
        from rcm_mc.ui.scenario_modeler_page import render_scenario_modeler
        df = _sample_hcris_with_nans(10)
        html = render_scenario_modeler("999999", df)
        self.assertIn("not found", html)

    def test_ebitda_bridge_nan_data(self):
        from rcm_mc.ui.ebitda_bridge_page import render_ebitda_bridge
        df = _sample_hcris_with_nans(50)
        # Pick a hospital that exists but may have NaN data
        ccn = df.iloc[0]["ccn"]
        html = render_ebitda_bridge(ccn, df)
        self.assertIsInstance(html, str)
        self.assertNotIn("NaN", html)


class TestCCNSanitization(unittest.TestCase):

    def test_strips_special_chars(self):
        from rcm_mc.server import RCMHandler
        self.assertEqual(RCMHandler._sanitize_ccn("010001"), "010001")
        self.assertEqual(RCMHandler._sanitize_ccn("01<script>"), "01script")
        self.assertEqual(RCMHandler._sanitize_ccn("'; DROP TABLE--"), "DROPTABLE")
        self.assertEqual(RCMHandler._sanitize_ccn("../../etc/passwd"), "etcpasswd")

    def test_length_limit(self):
        from rcm_mc.server import RCMHandler
        self.assertEqual(len(RCMHandler._sanitize_ccn("A" * 100)), 10)


class TestInputValidation(unittest.TestCase):

    def test_screener_bad_params(self):
        from rcm_mc.ui.predictive_screener import render_predictive_screener
        df = _sample_hcris_with_nans(50)
        # Bad numeric params should not crash
        html = render_predictive_screener(df, "min_beds=abc&max_margin=xyz")
        self.assertIsInstance(html, str)
        self.assertIn("SeekingChartis", html)

    def test_screener_negative_beds(self):
        from rcm_mc.ui.predictive_screener import render_predictive_screener
        df = _sample_hcris_with_nans(50)
        html = render_predictive_screener(df, "min_beds=-100")
        self.assertIsInstance(html, str)


class TestServerErrorPages(unittest.TestCase):

    def _start(self, db_path):
        from rcm_mc.server import build_server
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        server, _ = build_server(port=port, db_path=db_path)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.05)
        return server, port

    def test_ebitda_bridge_bad_ccn(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = self._start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/ebitda-bridge/NONEXISTENT"
                ) as r:
                    body = r.read().decode()
                self.assertIn("not found", body)
            finally:
                server.shutdown()
                server.server_close()
        finally:
            os.unlink(tf.name)

    def test_ic_memo_bad_ccn(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = self._start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/ic-memo/999999"
                ) as r:
                    body = r.read().decode()
                self.assertIn("SeekingChartis", body)
            finally:
                server.shutdown()
                server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
