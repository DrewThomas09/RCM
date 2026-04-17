"""Tests for /my/<owner> analyst dashboard (Brick 117)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.request as _u
from datetime import date, timedelta

from rcm_mc.deals.deal_deadlines import add_deadline
from rcm_mc.deals.deal_owners import assign_owner
from tests.test_alerts import _seed_with_pe_math


class TestMyDashboard(unittest.TestCase):
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

    def test_my_empty_analyst(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/my/AT") as r:
                    body = r.read().decode()
                    self.assertIn("No deals currently assigned", body)
                    self.assertIn("Nothing active", body)
                    self.assertIn("Nothing assigned", body)
            finally:
                server.shutdown(); server.server_close()

    def test_my_shows_owned_deals(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            assign_owner(store, deal_id="ccf", owner="AT")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/my/AT") as r:
                    body = r.read().decode()
                    self.assertIn("My deals (1)", body)
                    self.assertIn("ccf", body)
            finally:
                server.shutdown(); server.server_close()

    def test_my_alerts_scoped_to_owned_deals(self):
        with tempfile.TemporaryDirectory() as tmp:
            # ccf is red and owned by AT → should show
            # other is red but unowned → should NOT show on AT's view
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            _seed_with_pe_math(tmp, "other", headroom=-0.5)
            assign_owner(store, deal_id="ccf", owner="AT")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/my/AT") as r:
                    body = r.read().decode()
                    self.assertIn(">ccf<", body)
                    self.assertNotIn(">other<", body)
            finally:
                server.shutdown(); server.server_close()

    def test_my_deadlines_filtered_by_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            today = date.today()
            add_deadline(store, deal_id="ccf", label="AT task",
                         due_date=(today - timedelta(days=2)).isoformat(),
                         owner="AT")
            add_deadline(store, deal_id="ccf", label="SB task",
                         due_date=(today - timedelta(days=2)).isoformat(),
                         owner="SB")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/my/AT") as r:
                    body = r.read().decode()
                    self.assertIn("AT task", body)
                    self.assertNotIn("SB task", body)
            finally:
                server.shutdown(); server.server_close()

    def test_api_my_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            assign_owner(store, deal_id="ccf", owner="AT")
            today = date.today()
            add_deadline(store, deal_id="ccf", label="x",
                         due_date=(today - timedelta(days=1)).isoformat(),
                         owner="AT")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/api/my/AT") as r:
                    data = json.loads(r.read().decode())
                    self.assertEqual(data["owner"], "AT")
                    self.assertEqual(data["deals"], ["ccf"])
                    self.assertTrue(len(data["alerts"]) >= 1)
                    self.assertEqual(len(data["overdue"]), 1)
            finally:
                server.shutdown(); server.server_close()

    def test_owners_page_links_to_my_view(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            assign_owner(store, deal_id="ccf", owner="AT")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/owners") as r:
                    body = r.read().decode()
                    self.assertIn("href='/my/AT'", body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
