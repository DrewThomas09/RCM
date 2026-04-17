"""Tests for B144 portfolio pulse one-liner."""
from __future__ import annotations

import os
import tempfile
import unittest
import urllib.request as _u
from datetime import date, timedelta

from rcm_mc.deals.deal_deadlines import add_deadline
from tests.test_alerts import _seed_with_pe_math


class TestPortfolioPulse(unittest.TestCase):
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

    def test_hidden_when_clean_portfolio(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=2.0)  # no alerts
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/") as r:
                    body = r.read().decode()
                    self.assertNotIn(">Pulse<", body)
            finally:
                server.shutdown(); server.server_close()

    def test_shows_red_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=-0.5)  # red covenant
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/") as r:
                    body = r.read().decode()
                    self.assertIn(">Pulse<", body)
                    self.assertIn("1 red", body)
            finally:
                server.shutdown(); server.server_close()

    def test_shows_overdue_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            past = (date.today() - timedelta(days=2)).isoformat()
            add_deadline(store, deal_id="ccf", label="x", due_date=past)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/") as r:
                    body = r.read().decode()
                    self.assertIn("1 overdue", body)
            finally:
                server.shutdown(); server.server_close()

    def test_shows_upcoming_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            soon = (date.today() + timedelta(days=3)).isoformat()
            add_deadline(store, deal_id="ccf", label="x", due_date=soon)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/") as r:
                    body = r.read().decode()
                    self.assertIn("1 upcoming", body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
