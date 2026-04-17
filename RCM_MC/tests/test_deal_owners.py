"""Tests for deal ownership (Brick 113)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.parse as _p
import urllib.request as _u

from rcm_mc.deals.deal_owners import (
    all_owners, assign_owner, current_owner, deals_by_owner, owner_history,
)
from rcm_mc.portfolio.store import PortfolioStore
from tests.test_alerts import _seed_with_pe_math


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestAssignOwner(unittest.TestCase):
    def test_current_owner_none_when_unassigned(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(current_owner(_store(tmp), "ccf"))

    def test_assign_sets_current_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            assign_owner(store, deal_id="ccf", owner="AT")
            self.assertEqual(current_owner(store, "ccf"), "AT")

    def test_reassign_overwrites_current_and_appends_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            assign_owner(store, deal_id="ccf", owner="AT")
            assign_owner(store, deal_id="ccf", owner="SB", note="AT on leave")
            self.assertEqual(current_owner(store, "ccf"), "SB")
            hist = owner_history(store, "ccf")
            self.assertEqual(len(hist), 2)
            self.assertEqual(hist.iloc[0]["owner"], "SB")
            self.assertEqual(hist.iloc[0]["note"], "AT on leave")

    def test_invalid_owner_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            for bad in ("", "has space", "a" * 100, None):
                with self.assertRaises(ValueError):
                    assign_owner(store, deal_id="ccf", owner=bad)

    def test_valid_owner_patterns(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            for ok in ("AT", "sarah.brown", "AT_2", "user@firm.com", "a-b"):
                assign_owner(store, deal_id="ccf", owner=ok)
                self.assertEqual(current_owner(store, "ccf"), ok)

    def test_deals_by_owner_returns_current_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            assign_owner(store, deal_id="d1", owner="AT")
            assign_owner(store, deal_id="d2", owner="AT")
            assign_owner(store, deal_id="d1", owner="SB")  # reassigned
            # AT is current on d2 only
            self.assertEqual(deals_by_owner(store, "AT"), ["d2"])
            self.assertEqual(deals_by_owner(store, "SB"), ["d1"])

    def test_all_owners_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            assign_owner(store, deal_id="d1", owner="AT")
            assign_owner(store, deal_id="d2", owner="AT")
            assign_owner(store, deal_id="d3", owner="SB")
            owners = dict(all_owners(store))
            self.assertEqual(owners, {"AT": 2, "SB": 1})


class TestOwnersHttp(unittest.TestCase):
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

    def test_deal_page_has_owner_form(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/ccf") as r:
                    body = r.read().decode()
                    self.assertIn("/api/deals/ccf/owner", body)
                    self.assertIn('name="owner"', body)
            finally:
                server.shutdown(); server.server_close()

    def test_post_assign_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf")
            server, port = self._start(tmp)
            try:
                body = _p.urlencode({"owner": "AT"}).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/deals/ccf/owner",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                with _u.urlopen(req) as r:
                    self.assertIn(r.status, (200, 303))
                # Reload deal page — owner prefills
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/ccf") as r:
                    body = r.read().decode()
                    self.assertIn('value="AT"', body)
            finally:
                server.shutdown(); server.server_close()

    def test_owners_page_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/owners") as r:
                    body = r.read().decode()
                    self.assertIn("No deal owners assigned yet", body)
            finally:
                server.shutdown(); server.server_close()

    def test_owners_page_lists_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            assign_owner(store, deal_id="ccf", owner="AT")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/owners") as r:
                    body = r.read().decode()
                    self.assertIn("AT", body)
                    self.assertIn("href='/owner/AT'", body)
            finally:
                server.shutdown(); server.server_close()

    def test_owner_detail_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            assign_owner(store, deal_id="ccf", owner="AT")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/owner/AT") as r:
                    body = r.read().decode()
                    self.assertIn("ccf", body)
            finally:
                server.shutdown(); server.server_close()

    def test_api_owners_returns_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            assign_owner(store, deal_id="ccf", owner="AT")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/api/owners") as r:
                    data = json.loads(r.read().decode())
                    self.assertEqual(len(data), 1)
                    self.assertEqual(data[0]["owner"], "AT")
                    self.assertEqual(data[0]["deal_count"], 1)
            finally:
                server.shutdown(); server.server_close()

    def test_dashboard_has_owners_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/") as r:
                    body = r.read().decode()
                    self.assertIn('href="/owners"', body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
