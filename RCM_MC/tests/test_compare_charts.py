"""Tests for B124 SVG trajectory charts on /compare."""
from __future__ import annotations

import os
import tempfile
import unittest
import urllib.parse as _p
import urllib.request as _u

from rcm_mc.pe.hold_tracking import record_quarterly_actuals
from tests.test_alerts import _seed_with_pe_math


class TestCompareCharts(unittest.TestCase):
    def _start(self, tmp):
        import socket as _socket, threading, time as _time
        from rcm_mc.server import build_server
        s = _socket.socket(); s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]; s.close()
        server, _ = build_server(port=port,
                                 db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start(); _time.sleep(0.05)
        return server, port

    def test_compare_page_renders_trajectory_svg(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            _seed_with_pe_math(tmp, "aaa")
            for deal, vals in [
                ("ccf", [(8e6, 12e6), (9e6, 12e6)]),
                ("aaa", [(12e6, 12e6), (12.5e6, 12e6)]),
            ]:
                for i, (actual, plan) in enumerate(vals):
                    record_quarterly_actuals(
                        store, deal, f"2026Q{i+1}",
                        actuals={"ebitda": actual},
                        plan={"ebitda": plan},
                    )
            server, port = self._start(tmp)
            try:
                url = f"http://127.0.0.1:{port}/compare?deals=ccf,aaa"
                with _u.urlopen(url) as r:
                    body = r.read().decode()
                    self.assertIn("Comparison", body)
                    self.assertIn(">aaa<", body)
            finally:
                server.shutdown(); server.server_close()

    def test_compare_hides_trajectory_card_when_no_actuals(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf")
            _seed_with_pe_math(tmp, "aaa")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/compare?deals=ccf,aaa"
                ) as r:
                    body = r.read().decode()
                    self.assertNotIn("EBITDA trajectories", body)
                    # Comparison table still renders
                    self.assertIn("Comparison", body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
