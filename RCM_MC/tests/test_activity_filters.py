"""Tests for /activity owner + kind filters (Brick 119)."""
from __future__ import annotations

import os
import tempfile
import unittest
import urllib.request as _u

from rcm_mc.deals.deal_notes import record_note
from rcm_mc.deals.deal_owners import assign_owner
from tests.test_alerts import _seed_with_pe_math


class TestActivityFilters(unittest.TestCase):
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

    def test_activity_filter_form_rendered(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/activity") as r:
                    body = r.read().decode()
                    self.assertIn('name="owner"', body)
                    self.assertIn('name="kind"', body)
            finally:
                server.shutdown(); server.server_close()

    def test_activity_owner_filter_narrows_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            _seed_with_pe_math(tmp, "other")
            record_note(store, deal_id="ccf", body="AT deal note")
            record_note(store, deal_id="other", body="unowned deal note")
            assign_owner(store, deal_id="ccf", owner="AT")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/activity?owner=AT"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("AT deal note", body)
                    self.assertNotIn("unowned deal note", body)
                    self.assertIn("owner = AT", body)
            finally:
                server.shutdown(); server.server_close()

    def test_activity_kind_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            record_note(store, deal_id="ccf", body="a chat")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/activity?kind=note"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("a chat", body)
                    # Snapshot events should be excluded
                    self.assertNotIn("STAGE", body)
            finally:
                server.shutdown(); server.server_close()

    def test_activity_unknown_owner_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            record_note(store, deal_id="ccf", body="hello")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/activity?owner=nobody"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("No activity matches", body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
