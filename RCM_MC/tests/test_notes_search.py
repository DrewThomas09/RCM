"""Tests for full-text notes search (Brick 110)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.request as _u

from rcm_mc.deals.deal_notes import record_note, search_notes, delete_note
from rcm_mc.portfolio.store import PortfolioStore


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestSearchNotes(unittest.TestCase):
    def test_empty_query_returns_empty_df(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            record_note(store, deal_id="ccf", body="board meeting notes")
            df = search_notes(store, "")
            self.assertTrue(df.empty)

    def test_substring_case_insensitive_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            record_note(store, deal_id="ccf",
                        body="Covenant RESET discussed today")
            record_note(store, deal_id="aaa",
                        body="normal quarterly review")
            df = search_notes(store, "covenant reset")
            self.assertEqual(len(df), 1)
            self.assertEqual(df.iloc[0]["deal_id"], "ccf")

    def test_deal_id_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            record_note(store, deal_id="ccf", body="covenant concern")
            record_note(store, deal_id="aaa", body="covenant concern")
            df = search_notes(store, "covenant", deal_id="aaa")
            self.assertEqual(len(df), 1)
            self.assertEqual(df.iloc[0]["deal_id"], "aaa")

    def test_soft_deleted_notes_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            nid = record_note(store, deal_id="ccf",
                              body="secret covenant info")
            delete_note(store, nid)
            df = search_notes(store, "secret")
            self.assertTrue(df.empty)

    def test_limit_applied(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            for i in range(5):
                record_note(store, deal_id="ccf",
                            body=f"watchlist entry {i}")
            df = search_notes(store, "watchlist", limit=3)
            self.assertEqual(len(df), 3)


class TestNotesSearchHttp(unittest.TestCase):
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

    def test_notes_page_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/notes") as r:
                    body = r.read().decode()
                    self.assertIn("Enter a query above", body)
            finally:
                server.shutdown(); server.server_close()

    def test_notes_page_search_finds_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            record_note(store, deal_id="ccf",
                        body="urgent covenant reset needed")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/notes?q=covenant"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("urgent", body)
                    self.assertIn("ccf", body)
                    self.assertIn("<mark", body)
            finally:
                server.shutdown(); server.server_close()

    def test_notes_page_no_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            record_note(store, deal_id="ccf", body="some text")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/notes?q=xyzzy"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("No notes match", body)
            finally:
                server.shutdown(); server.server_close()

    def test_api_notes_search_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            record_note(store, deal_id="ccf", body="audit completed Q1")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/notes/search?q=audit"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertEqual(len(data), 1)
                    self.assertEqual(data[0]["deal_id"], "ccf")
            finally:
                server.shutdown(); server.server_close()

    def test_dashboard_has_notes_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/") as r:
                    body = r.read().decode()
                    self.assertIn('href="/notes"', body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
