"""Tests for watchlist / deal starring (Brick 111)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.parse as _p
import urllib.request as _u

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.deals.watchlist import (
    is_starred, list_starred, star_deal, toggle_star, unstar_deal,
)
from tests.test_alerts import _seed_with_pe_math


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestStarCore(unittest.TestCase):
    def test_default_is_unstarred(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            self.assertFalse(is_starred(store, "ccf"))

    def test_star_then_unstar(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            self.assertTrue(star_deal(store, "ccf"))
            self.assertTrue(is_starred(store, "ccf"))
            self.assertTrue(unstar_deal(store, "ccf"))
            self.assertFalse(is_starred(store, "ccf"))

    def test_star_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            self.assertTrue(star_deal(store, "ccf"))
            self.assertFalse(star_deal(store, "ccf"))  # already starred

    def test_toggle_flips_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            self.assertTrue(toggle_star(store, "ccf"))
            self.assertFalse(toggle_star(store, "ccf"))
            self.assertTrue(toggle_star(store, "ccf"))

    def test_list_starred_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            import time
            star_deal(store, "a")
            time.sleep(0.01)
            star_deal(store, "b")
            self.assertEqual(list_starred(store), ["b", "a"])


class TestStarHttp(unittest.TestCase):
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

    def test_post_star_toggles_and_returns_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf")
            server, port = self._start(tmp)
            try:
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/deals/ccf/star",
                    data=b"", method="POST",
                    headers={"Accept": "application/json"},
                )
                with _u.urlopen(req) as r:
                    data = json.loads(r.read().decode())
                    self.assertTrue(data["starred"])
                # Toggle again → unstar
                with _u.urlopen(req) as r:
                    data = json.loads(r.read().decode())
                    self.assertFalse(data["starred"])
            finally:
                server.shutdown(); server.server_close()

    def test_watchlist_page_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/watchlist") as r:
                    body = r.read().decode()
                    self.assertIn("No starred deals yet", body)
            finally:
                server.shutdown(); server.server_close()

    def test_watchlist_page_shows_starred_deal(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            star_deal(store, "ccf")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/watchlist") as r:
                    body = r.read().decode()
                    self.assertIn("ccf", body)
                    self.assertIn("★", body)
            finally:
                server.shutdown(); server.server_close()

    def test_deal_page_has_star_button(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/ccf") as r:
                    body = r.read().decode()
                    self.assertIn("/api/deals/ccf/star", body)
                    self.assertIn("☆ Star", body)
            finally:
                server.shutdown(); server.server_close()

    def test_deal_page_shows_starred_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            star_deal(store, "ccf")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/ccf") as r:
                    body = r.read().decode()
                    self.assertIn("★ Starred", body)
            finally:
                server.shutdown(); server.server_close()

    def test_api_watchlist_returns_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            star_deal(store, "ccf")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/watchlist"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertEqual(data["starred"], ["ccf"])
            finally:
                server.shutdown(); server.server_close()

    def test_dashboard_has_watchlist_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/") as r:
                    body = r.read().decode()
                    self.assertIn('href="/watchlist"', body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
