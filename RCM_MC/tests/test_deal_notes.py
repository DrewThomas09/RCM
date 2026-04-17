"""Tests for per-deal notes (Brick 71)."""
from __future__ import annotations

import os
import tempfile
import time
import unittest

from rcm_mc.deals.deal_notes import (
    delete_note,
    hard_delete_note,
    list_notes,
    record_note,
    undelete_note,
)
from rcm_mc.portfolio.store import PortfolioStore


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestRecordNote(unittest.TestCase):
    def test_returns_id_on_insert(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            nid = record_note(store, deal_id="ccf", body="Call at 3pm")
            self.assertIsInstance(nid, int)
            self.assertGreater(nid, 0)

    def test_empty_body_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            with self.assertRaises(ValueError):
                record_note(store, deal_id="ccf", body="")
            with self.assertRaises(ValueError):
                record_note(store, deal_id="ccf", body="   ")

    def test_author_optional_and_trimmed(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            record_note(store, deal_id="ccf", body="x", author="  AT  ")
            df = list_notes(store, "ccf")
            self.assertEqual(df.iloc[0]["author"], "AT")

    def test_body_trimmed(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            record_note(store, deal_id="ccf", body="  hello  ")
            self.assertEqual(list_notes(store, "ccf").iloc[0]["body"], "hello")


class TestListNotes(unittest.TestCase):
    def test_empty_store_returns_empty_frame(self):
        with tempfile.TemporaryDirectory() as tmp:
            df = list_notes(_store(tmp), "ghost")
            self.assertTrue(df.empty)

    def test_newest_first_ordering(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            record_note(store, deal_id="ccf", body="first")
            time.sleep(0.01)
            record_note(store, deal_id="ccf", body="second")
            df = list_notes(store, "ccf")
            # Newest first
            self.assertEqual(df.iloc[0]["body"], "second")
            self.assertEqual(df.iloc[1]["body"], "first")

    def test_filter_by_deal(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            record_note(store, deal_id="ccf", body="x")
            record_note(store, deal_id="other", body="y")
            self.assertEqual(len(list_notes(store, "ccf")), 1)
            self.assertEqual(len(list_notes(store, "other")), 1)
            self.assertEqual(len(list_notes(store)), 2)  # all deals


class TestDeleteNote(unittest.TestCase):
    def test_soft_delete_hides_from_default_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            nid = record_note(store, deal_id="ccf", body="temp")
            self.assertTrue(delete_note(store, nid))
            self.assertTrue(list_notes(store, "ccf").empty)

    def test_soft_delete_preserves_row_in_trash(self):
        """B91: soft-deleted row stays in table with deleted_at stamp."""
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            nid = record_note(store, deal_id="ccf", body="temp")
            delete_note(store, nid)
            trash = list_notes(store, "ccf", include_deleted=True)
            self.assertEqual(len(trash), 1)
            self.assertIsNotNone(trash.iloc[0]["deleted_at"])

    def test_delete_missing_note_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            self.assertFalse(delete_note(store, 99999))

    def test_undelete_restores(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            nid = record_note(store, deal_id="ccf", body="temp")
            delete_note(store, nid)
            self.assertTrue(undelete_note(store, nid))
            self.assertEqual(len(list_notes(store, "ccf")), 1)

    def test_undelete_on_active_note_returns_false(self):
        """Restore a note that wasn't deleted: no-op, returns False."""
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            nid = record_note(store, deal_id="ccf", body="temp")
            self.assertFalse(undelete_note(store, nid))

    def test_hard_delete_removes_permanently(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            nid = record_note(store, deal_id="ccf", body="temp")
            delete_note(store, nid)
            self.assertTrue(hard_delete_note(store, nid))
            # Gone from all lists including trash
            trash = list_notes(store, "ccf", include_deleted=True)
            self.assertTrue(trash.empty)

    def test_soft_delete_idempotent(self):
        """Calling delete twice doesn't move the row further — first call wins."""
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            nid = record_note(store, deal_id="ccf", body="temp")
            self.assertTrue(delete_note(store, nid))
            # Second call on already-deleted note: no-op, returns False
            self.assertFalse(delete_note(store, nid))


class TestNotesHttpIntegration(unittest.TestCase):
    """B71 server integration — POST /api/deals/<id>/notes path."""

    def _start(self, db_path: str):
        import socket as _socket
        import threading
        import time as _time
        from rcm_mc.server import build_server
        s = _socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        server, _ = build_server(port=port, db_path=db_path)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        _time.sleep(0.05)
        return server, port

    def test_post_note_persists_to_store(self):
        import urllib.parse as _urlparse
        import urllib.request as _urlreq
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            # Seed an empty snapshot so the deal exists in the store
            from rcm_mc.portfolio.portfolio_snapshots import register_snapshot
            register_snapshot(store, "ccf", "ioi")

            server, port = self._start(os.path.join(tmp, "p.db"))
            try:
                body = _urlparse.urlencode({
                    "author": "Analyst X",
                    "body": "Management confirmed one-time Q3 item; normalize.",
                }).encode()
                req = _urlreq.Request(
                    f"http://127.0.0.1:{port}/api/deals/ccf/notes",
                    data=body,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    method="POST",
                )
                class _NoRedirect(_urlreq.HTTPRedirectHandler):
                    def http_error_303(self, *a, **kw):
                        return None
                try:
                    _urlreq.build_opener(_NoRedirect).open(req)
                except HTTPError:
                    pass
                # Note landed
                df = list_notes(store, "ccf")
                self.assertEqual(len(df), 1)
                self.assertEqual(df.iloc[0]["author"], "Analyst X")
                self.assertIn("normalize", df.iloc[0]["body"])
            finally:
                server.shutdown()
                server.server_close()

    def test_deal_page_renders_notes_section(self):
        import urllib.request as _urlreq
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            from rcm_mc.portfolio.portfolio_snapshots import register_snapshot
            register_snapshot(store, "ccf", "ioi")
            record_note(store, deal_id="ccf",
                        body="First call — good fit.", author="AT")
            server, port = self._start(os.path.join(tmp, "p.db"))
            try:
                with _urlreq.urlopen(
                    f"http://127.0.0.1:{port}/deal/ccf"
                ) as r:
                    page = r.read().decode()
                    self.assertIn("Notes (1)", page)
                    self.assertIn("First call — good fit.", page)
                    self.assertIn("AT", page)
                    # Form for new note
                    self.assertIn('action="/api/deals/ccf/notes"', page)
            finally:
                server.shutdown()
                server.server_close()

    def test_api_notes_endpoint_returns_json(self):
        import json as _json
        import urllib.request as _urlreq
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            record_note(store, deal_id="ccf", body="one")
            record_note(store, deal_id="ccf", body="two")
            server, port = self._start(os.path.join(tmp, "p.db"))
            try:
                with _urlreq.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/ccf/notes"
                ) as r:
                    self.assertEqual(r.status, 200)
                    data = _json.loads(r.read().decode())
                    self.assertIn("notes", data)
                    self.assertEqual(len(data["notes"]), 2)
                    bodies = {n["body"] for n in data["notes"]}
                    self.assertEqual(bodies, {"one", "two"})
            finally:
                server.shutdown()
                server.server_close()

    def test_delete_note_via_post(self):
        import urllib.request as _urlreq
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            nid = record_note(store, deal_id="ccf", body="erase me")
            server, port = self._start(os.path.join(tmp, "p.db"))
            try:
                req = _urlreq.Request(
                    f"http://127.0.0.1:{port}/api/deals/ccf/notes/{nid}/delete",
                    data=b"",
                    method="POST",
                )
                class _NoRedirect(_urlreq.HTTPRedirectHandler):
                    def http_error_303(self, *a, **kw):
                        return None
                try:
                    _urlreq.build_opener(_NoRedirect).open(req)
                except HTTPError:
                    pass
                self.assertTrue(list_notes(store, "ccf").empty)
            finally:
                server.shutdown()
                server.server_close()

    def test_post_empty_note_body_returns_400(self):
        import urllib.parse as _urlparse
        import urllib.request as _urlreq
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(os.path.join(tmp, "p.db"))
            try:
                body = _urlparse.urlencode({"body": ""}).encode()
                req = _urlreq.Request(
                    f"http://127.0.0.1:{port}/api/deals/x/notes",
                    data=body,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    method="POST",
                )
                with self.assertRaises(HTTPError) as ctx:
                    _urlreq.urlopen(req)
                self.assertEqual(ctx.exception.code, 400)
            finally:
                server.shutdown()
                server.server_close()
