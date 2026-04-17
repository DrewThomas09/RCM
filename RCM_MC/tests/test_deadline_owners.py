"""Tests for per-deadline owner assignment (Brick 116)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.parse as _p
import urllib.request as _u
from datetime import date, timedelta

from rcm_mc.deals.deal_deadlines import (
    add_deadline, assign_deadline_owner, list_deadlines, overdue, upcoming,
)
from rcm_mc.deals.deal_owners import assign_owner
from rcm_mc.portfolio.store import PortfolioStore
from tests.test_alerts import _seed_with_pe_math


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestDeadlineOwnerCore(unittest.TestCase):
    def test_add_with_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            did = add_deadline(store, deal_id="ccf", label="x",
                               due_date="2026-12-01", owner="AT")
            df = list_deadlines(store)
            self.assertEqual(df.iloc[0]["owner"], "AT")

    def test_reassign(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            did = add_deadline(store, deal_id="ccf", label="x",
                               due_date="2026-12-01", owner="AT")
            self.assertTrue(assign_deadline_owner(store, did, "SB"))
            df = list_deadlines(store)
            self.assertEqual(df.iloc[0]["owner"], "SB")

    def test_filter_by_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            today = date.today()
            add_deadline(store, deal_id="d1", label="at-task",
                         due_date=(today + timedelta(days=3)).isoformat(),
                         owner="AT")
            add_deadline(store, deal_id="d2", label="sb-task",
                         due_date=(today + timedelta(days=3)).isoformat(),
                         owner="SB")
            mine = list_deadlines(store, owner="AT")
            self.assertEqual(len(mine), 1)
            self.assertEqual(mine.iloc[0]["label"], "at-task")

    def test_upcoming_and_overdue_filter_by_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            today = date.today()
            add_deadline(store, deal_id="d1", label="at-past",
                         due_date=(today - timedelta(days=2)).isoformat(),
                         owner="AT")
            add_deadline(store, deal_id="d2", label="sb-soon",
                         due_date=(today + timedelta(days=2)).isoformat(),
                         owner="SB")
            self.assertEqual(len(overdue(store, owner="AT")), 1)
            self.assertEqual(len(overdue(store, owner="SB")), 0)
            self.assertEqual(len(upcoming(store, owner="AT")), 0)
            self.assertEqual(len(upcoming(store, owner="SB")), 1)


class TestDeadlineOwnerHttp(unittest.TestCase):
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

    def test_deadline_form_prefills_deal_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            assign_owner(store, deal_id="ccf", owner="AT")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/ccf") as r:
                    body = r.read().decode()
                    # Add-deadline form should prefill owner = AT
                    self.assertIn('name="owner" value="AT"', body)
            finally:
                server.shutdown(); server.server_close()

    def test_post_deadline_with_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf")
            server, port = self._start(tmp)
            try:
                future = (date.today() + timedelta(days=10)).isoformat()
                body = _p.urlencode({
                    "label": "refi review",
                    "due_date": future,
                    "owner": "AT",
                }).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/deals/ccf/deadlines",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                _u.urlopen(req)
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/ccf/deadlines"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertEqual(data[0]["owner"], "AT")
            finally:
                server.shutdown(); server.server_close()

    def test_deadlines_page_filters_by_owner_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            today = date.today()
            add_deadline(store, deal_id="ccf", label="AT item",
                         due_date=(today + timedelta(days=3)).isoformat(),
                         owner="AT")
            add_deadline(store, deal_id="ccf", label="SB item",
                         due_date=(today + timedelta(days=3)).isoformat(),
                         owner="SB")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/deadlines?owner=AT"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("AT item", body)
                    self.assertNotIn("SB item", body)
            finally:
                server.shutdown(); server.server_close()

    def test_post_reassign_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            did = add_deadline(store, deal_id="ccf", label="x",
                               due_date="2026-12-01", owner="AT")
            server, port = self._start(tmp)
            try:
                body = _p.urlencode({"owner": "SB"}).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/deadlines/{did}/assign",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                )
                with _u.urlopen(req) as r:
                    data = json.loads(r.read().decode())
                    self.assertTrue(data["ok"])
                self.assertEqual(
                    list_deadlines(store).iloc[0]["owner"], "SB",
                )
            finally:
                server.shutdown(); server.server_close()

    def test_api_deadlines_inbox_owner_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            today = date.today()
            add_deadline(store, deal_id="ccf", label="AT past",
                         due_date=(today - timedelta(days=3)).isoformat(),
                         owner="AT")
            add_deadline(store, deal_id="ccf", label="SB past",
                         due_date=(today - timedelta(days=3)).isoformat(),
                         owner="SB")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/deadlines?owner=AT"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertEqual(len(data["overdue"]), 1)
                    self.assertEqual(data["overdue"][0]["label"], "AT past")
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
