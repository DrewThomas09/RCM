"""Tests for aggregate (avg) health on /owners and /cohorts (B137)."""
from __future__ import annotations

import os
import tempfile
import unittest
import urllib.request as _u

from rcm_mc.deals.deal_owners import assign_owner
from rcm_mc.deals.deal_tags import add_tag
from tests.test_alerts import _seed_with_pe_math


class TestAggregateHealth(unittest.TestCase):
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

    def test_owners_avg_health(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "clean", headroom=2.0)
            _seed_with_pe_math(tmp, "broken", headroom=-0.5)
            assign_owner(store, deal_id="clean", owner="AT")
            assign_owner(store, deal_id="broken", owner="AT")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/owners") as r:
                    body = r.read().decode()
                    self.assertIn("<th>Avg health</th>", body)
                    # (100 + 60) / 2 = 80
                    self.assertIn(">80</td>", body)
            finally:
                server.shutdown(); server.server_close()

    def test_cohorts_avg_health(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            add_tag(store, deal_id="ccf", tag="watch")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/cohorts") as r:
                    body = r.read().decode()
                    self.assertIn("Avg health", body)
                    self.assertIn(">60</td>", body)
            finally:
                server.shutdown(); server.server_close()

    def test_owners_avg_health_missing_when_no_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            # Assign to a deal that's not in the latest snapshot
            assign_owner(store, deal_id="ghost", owner="AT")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/owners") as r:
                    body = r.read().decode()
                    self.assertIn("Avg health", body)
                    # AT owns only "ghost" which has no snapshot → em-dash
                    self.assertIn("—", body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
