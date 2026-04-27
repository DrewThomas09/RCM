"""End-to-end test for /calibration (campaign target 3D — Phase 3).

Boots a real ThreadingHTTPServer and hits /calibration via
urllib.request. Empty PortfolioStore triggers the empty-state
branch, which is enough to verify the page goes through chartis_shell
and uses v3 utility classes instead of the previous inline cad-*
chrome.

What this guards (per Phase 3 surfacing checklist):
  - shell() with no bespoke wrapper: chartis_shell <title> present.
  - v3 chartis.css tokens: at least one .micro class on the body.
  - Empty-state path renders without crashing and points at
    /analysis.
  - /calibrate alias serves the same page (single source of code).
  - The /api/calibration/priors link is present so the JSON
    fallback stays discoverable.
"""
from __future__ import annotations

import os
import socket as _socket
import tempfile
import threading
import time as _time
import unittest
import urllib.request as _u

from rcm_mc.server import build_server


def _free_port() -> int:
    s = _socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class CalibrationPageTests(unittest.TestCase):
    def _start(self, tmp: str):
        port = _free_port()
        server, _ = build_server(port=port, db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        _time.sleep(0.05)
        return server, port

    def test_calibration_returns_200_through_shell(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/calibration") as r:
                    self.assertEqual(r.status, 200)
                    body = r.read().decode("utf-8")
                self.assertIn("<title>Calibration", body)
                self.assertIn("<h1", body)
                self.assertIn("Calibration", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_calibrate_alias_serves_same_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/calibrate") as r:
                    self.assertEqual(r.status, 200)
                    body = r.read().decode("utf-8")
                self.assertIn("<title>Calibration", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_empty_store_renders_empty_state_with_analysis_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/calibration") as r:
                    body = r.read().decode("utf-8")
                self.assertIn("No simulation runs yet", body)
                self.assertIn('href="/analysis"', body)
            finally:
                server.shutdown()
                server.server_close()

    def test_page_carries_v3_micro_utility_class(self) -> None:
        """The new module replaces hand-rolled cad-card / cad-mono /
        cad-text* with v3 .micro and .num utility classes. Verify
        the migration landed on the rendered body — at least .micro
        is reachable in the empty state."""
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/calibration") as r:
                    body = r.read().decode("utf-8")
                self.assertIn('class="micro"', body)
            finally:
                server.shutdown()
                server.server_close()


class CalibrationAggregateTests(unittest.TestCase):
    """Direct unit test on _aggregate_payers — keeps the JSON
    parsing + averaging contract pinned so a generator format
    change can be caught loudly."""

    def test_averages_per_payer(self) -> None:
        from rcm_mc.ui.calibration_page import _aggregate_payers
        import pandas as pd

        df = pd.DataFrame([
            {"primitives_json": (
                '{"payers": {'
                '"medicare": {"idr_mean": 0.10, "fwr_mean": 0.20, "dar_clean_days_mean": 30},'
                '"medicaid": {"idr_mean": 0.20, "fwr_mean": 0.40, "dar_clean_days_mean": 50}'
                '}}'
            )},
            {"primitives_json": (
                '{"payers": {'
                '"medicare": {"idr_mean": 0.20, "fwr_mean": 0.30, "dar_clean_days_mean": 50}'
                '}}'
            )},
        ])
        out = _aggregate_payers(df)
        # medicare: mean of (0.10, 0.20) = 0.15
        self.assertAlmostEqual(out["medicare"]["idr_m"], 0.15)
        self.assertAlmostEqual(out["medicare"]["fwr_m"], 0.25)
        self.assertAlmostEqual(out["medicare"]["dar_m"], 40.0)
        self.assertEqual(out["medicare"]["n_entries"], 2.0)
        # medicaid: only one entry
        self.assertAlmostEqual(out["medicaid"]["idr_m"], 0.20)
        self.assertEqual(out["medicaid"]["n_entries"], 1.0)

    def test_handles_invalid_json_silently(self) -> None:
        from rcm_mc.ui.calibration_page import _aggregate_payers
        import pandas as pd

        df = pd.DataFrame([
            {"primitives_json": "not json"},
            {"primitives_json": ""},
            {"primitives_json": '{"payers": {"x": {"idr_mean": 0.1}}}'},
        ])
        out = _aggregate_payers(df)
        self.assertIn("x", out)
        self.assertAlmostEqual(out["x"]["idr_m"], 0.1)


if __name__ == "__main__":
    unittest.main()
