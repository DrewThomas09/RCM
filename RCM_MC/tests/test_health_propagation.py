"""Tests for health column propagation (Brick 136)."""
from __future__ import annotations

import os
import tempfile
import unittest
import urllib.request as _u

from rcm_mc.deals.deal_owners import assign_owner
from rcm_mc.deals.deal_tags import add_tag
from rcm_mc.deals.watchlist import star_deal
from tests.test_alerts import _seed_with_pe_math


class TestHealthPropagation(unittest.TestCase):
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

    def test_watchlist_shows_health(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            star_deal(store, "ccf")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/watchlist") as r:
                    body = r.read().decode()
                    self.assertIn("<th>Health</th>", body)
                    # ccf is covenant TRIPPED → health 60
                    self.assertIn(">60</td>", body)
            finally:
                server.shutdown(); server.server_close()

    def test_owner_detail_shows_health(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            assign_owner(store, deal_id="ccf", owner="AT")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/owner/AT") as r:
                    body = r.read().decode()
                    self.assertIn("<th>Health</th>", body)
                    self.assertIn(">60</td>", body)
            finally:
                server.shutdown(); server.server_close()

    def test_cohort_detail_shows_health(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            add_tag(store, deal_id="ccf", tag="watch")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/cohort/watch") as r:
                    body = r.read().decode()
                    self.assertIn("<th>Health</th>", body)
                    self.assertIn(">60</td>", body)
            finally:
                server.shutdown(); server.server_close()

    def test_my_dashboard_shows_health(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            assign_owner(store, deal_id="ccf", owner="AT")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/my/AT") as r:
                    body = r.read().decode()
                    self.assertIn("<th>Health</th>", body)
                    self.assertIn(">60</td>", body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
