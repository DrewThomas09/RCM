"""Tests for per-deal deadlines + portfolio inbox (Brick 114)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.parse as _p
import urllib.request as _u
from datetime import date, timedelta

from rcm_mc.deals.deal_deadlines import (
    add_deadline, complete_deadline, list_deadlines, overdue, upcoming,
)
from rcm_mc.portfolio.store import PortfolioStore
from tests.test_alerts import _seed_with_pe_math


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestDeadlineCore(unittest.TestCase):
    def test_add_and_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            future = (date.today() + timedelta(days=10)).isoformat()
            add_deadline(store, deal_id="ccf", label="board prep",
                         due_date=future)
            df = list_deadlines(store)
            self.assertEqual(len(df), 1)
            self.assertEqual(df.iloc[0]["status"], "open")

    def test_invalid_date_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            for bad in ("2026-13-40", "not a date", "20260101", ""):
                with self.assertRaises(ValueError):
                    add_deadline(store, deal_id="ccf", label="x", due_date=bad)

    def test_missing_label_or_deal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            with self.assertRaises(ValueError):
                add_deadline(store, deal_id="", label="x",
                             due_date="2026-05-01")
            with self.assertRaises(ValueError):
                add_deadline(store, deal_id="ccf", label="",
                             due_date="2026-05-01")

    def test_complete_marks_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            did = add_deadline(store, deal_id="ccf", label="x",
                               due_date="2026-05-01")
            self.assertTrue(complete_deadline(store, did))
            self.assertFalse(complete_deadline(store, did))  # already done
            df = list_deadlines(store, include_completed=True)
            self.assertEqual(df.iloc[0]["status"], "completed")
            # Default list excludes completed
            self.assertTrue(list_deadlines(store).empty)

    def test_upcoming_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            today = date.today()
            add_deadline(store, deal_id="ccf", label="soon",
                         due_date=(today + timedelta(days=3)).isoformat())
            add_deadline(store, deal_id="ccf", label="far",
                         due_date=(today + timedelta(days=60)).isoformat())
            up = upcoming(store, days_ahead=14, today=today)
            self.assertEqual(len(up), 1)
            self.assertEqual(up.iloc[0]["label"], "soon")

    def test_overdue_includes_only_past(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            today = date.today()
            add_deadline(store, deal_id="ccf", label="missed",
                         due_date=(today - timedelta(days=5)).isoformat())
            add_deadline(store, deal_id="ccf", label="future",
                         due_date=(today + timedelta(days=5)).isoformat())
            od = overdue(store, today=today)
            self.assertEqual(len(od), 1)
            self.assertEqual(od.iloc[0]["label"], "missed")
            self.assertEqual(od.iloc[0]["days_overdue"], 5)


class TestDeadlinesHttp(unittest.TestCase):
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

    def test_deadlines_page_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deadlines") as r:
                    body = r.read().decode()
                    self.assertIn("Nothing overdue", body)
            finally:
                server.shutdown(); server.server_close()

    def test_deal_page_has_deadline_form(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/ccf") as r:
                    body = r.read().decode()
                    self.assertIn("/api/deals/ccf/deadlines", body)
                    self.assertIn('name="due_date"', body)
                    self.assertIn("Deadlines", body)
            finally:
                server.shutdown(); server.server_close()

    def test_post_add_deadline_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf")
            server, port = self._start(tmp)
            try:
                future = (date.today() + timedelta(days=14)).isoformat()
                body = _p.urlencode({
                    "label": "covenant test",
                    "due_date": future,
                }).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/deals/ccf/deadlines",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                with _u.urlopen(req) as r:
                    pass  # 303 redirect handled by urllib
                # Verify via API
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/ccf/deadlines"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertEqual(len(data), 1)
                    self.assertEqual(data[0]["label"], "covenant test")
            finally:
                server.shutdown(); server.server_close()

    def test_post_add_invalid_date_returns_400(self):
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                body = _p.urlencode({
                    "label": "x", "due_date": "garbage",
                }).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/deals/ccf/deadlines",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                with self.assertRaises(HTTPError) as ctx:
                    _u.urlopen(req)
                self.assertEqual(ctx.exception.code, 400)
            finally:
                server.shutdown(); server.server_close()

    def test_complete_endpoint_marks_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            did = add_deadline(store, deal_id="ccf", label="x",
                               due_date="2026-12-31")
            server, port = self._start(tmp)
            try:
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/deadlines/{did}/complete",
                    data=b"", method="POST",
                    headers={"Accept": "application/json"},
                )
                with _u.urlopen(req) as r:
                    data = json.loads(r.read().decode())
                    self.assertTrue(data["completed"])
                self.assertTrue(list_deadlines(store).empty)
            finally:
                server.shutdown(); server.server_close()

    def test_api_deadlines_inbox_buckets(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            today = date.today()
            add_deadline(store, deal_id="ccf", label="overdue",
                         due_date=(today - timedelta(days=2)).isoformat())
            add_deadline(store, deal_id="ccf", label="soon",
                         due_date=(today + timedelta(days=2)).isoformat())
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/deadlines"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertEqual(len(data["overdue"]), 1)
                    self.assertEqual(len(data["upcoming"]), 1)
            finally:
                server.shutdown(); server.server_close()

    def test_dashboard_has_deadlines_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/") as r:
                    body = r.read().decode()
                    self.assertIn('href="/deadlines"', body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
