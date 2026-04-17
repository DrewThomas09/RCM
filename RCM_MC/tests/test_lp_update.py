"""Tests for /lp-update partner-digest page (Brick 107)."""
from __future__ import annotations

import os
import tempfile
import unittest
import urllib.request as _u

from rcm_mc.deals.deal_tags import add_tag
from tests.test_alerts import _seed_with_pe_math


class TestLpUpdatePage(unittest.TestCase):
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

    def test_lp_update_empty_portfolio_still_renders(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/lp-update") as r:
                    self.assertEqual(r.status, 200)
                    body = r.read().decode()
                    self.assertIn("LP Update", body)
                    self.assertIn("Active alerts", body)
                    self.assertIn("Recent activity", body)
            finally:
                server.shutdown(); server.server_close()

    def test_lp_update_shows_headline_kpis(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/lp-update") as r:
                    body = r.read().decode()
                    self.assertIn("Weighted MOIC", body)
                    self.assertIn("Weighted IRR", body)
                    self.assertIn("Active deals", body)
                    self.assertIn("Covenant trips", body)
            finally:
                server.shutdown(); server.server_close()

    def test_lp_update_lists_active_red_alert(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/lp-update") as r:
                    body = r.read().decode()
                    self.assertIn("RED", body)
                    self.assertIn("Covenant TRIPPED", body)
            finally:
                server.shutdown(); server.server_close()

    def test_lp_update_cohort_section_shown_when_tags_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            add_tag(store, deal_id="ccf", tag="growth")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/lp-update") as r:
                    body = r.read().decode()
                    self.assertIn("Cohort breakdown", body)
                    self.assertIn("growth", body)
            finally:
                server.shutdown(); server.server_close()

    def test_lp_update_cohort_section_hidden_when_no_tags(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/lp-update") as r:
                    body = r.read().decode()
                    self.assertNotIn("Cohort breakdown", body)
            finally:
                server.shutdown(); server.server_close()

    def test_lp_update_download_sends_attachment_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            server, port = self._start(tmp)
            try:
                req = _u.Request(
                    f"http://127.0.0.1:{port}/lp-update?download=1"
                )
                with _u.urlopen(req) as r:
                    cd = r.headers.get("Content-Disposition", "")
                    self.assertIn("attachment", cd)
                    self.assertIn("lp_update_", cd)
            finally:
                server.shutdown(); server.server_close()

    def test_lp_update_days_window_query_param(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/lp-update?days=7"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("window 7 days", body)
            finally:
                server.shutdown(); server.server_close()

    def test_dashboard_has_lp_update_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/") as r:
                    body = r.read().decode()
                    self.assertIn('href="/lp-update"', body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
