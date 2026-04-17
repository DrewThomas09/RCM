"""Tests for note tagging (Brick 123)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.parse as _p
import urllib.request as _u
from urllib.error import HTTPError

from rcm_mc.deals.deal_notes import record_note, search_notes
from rcm_mc.deals.note_tags import (
    add_note_tag, all_note_tags, remove_note_tag,
    search_notes_by_tag, tags_for_note, tags_for_notes,
)
from rcm_mc.portfolio.store import PortfolioStore


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestNoteTagsCore(unittest.TestCase):
    def test_add_and_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            nid = record_note(store, deal_id="ccf", body="board prep")
            self.assertTrue(add_note_tag(store, nid, "board_meeting"))
            self.assertEqual(tags_for_note(store, nid), ["board_meeting"])

    def test_add_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            nid = record_note(store, deal_id="ccf", body="x")
            self.assertTrue(add_note_tag(store, nid, "flag"))
            self.assertFalse(add_note_tag(store, nid, "flag"))

    def test_remove(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            nid = record_note(store, deal_id="ccf", body="x")
            add_note_tag(store, nid, "flag")
            self.assertTrue(remove_note_tag(store, nid, "flag"))
            self.assertFalse(remove_note_tag(store, nid, "flag"))

    def test_invalid_tag_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            nid = record_note(store, deal_id="ccf", body="x")
            for bad in ("", "has space", "A" * 100):
                with self.assertRaises(ValueError):
                    add_note_tag(store, nid, bad)

    def test_search_by_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            n1 = record_note(store, deal_id="ccf", body="A")
            n2 = record_note(store, deal_id="aaa", body="B")
            add_note_tag(store, n1, "board_meeting")
            add_note_tag(store, n2, "board_meeting")
            add_note_tag(store, n1, "blocker")
            df = search_notes_by_tag(store, "board_meeting")
            self.assertEqual(len(df), 2)

    def test_tags_for_notes_bulk(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            n1 = record_note(store, deal_id="ccf", body="A")
            n2 = record_note(store, deal_id="aaa", body="B")
            add_note_tag(store, n1, "tag1")
            add_note_tag(store, n1, "tag2")
            out = tags_for_notes(store, [n1, n2])
            self.assertEqual(out[n1], ["tag1", "tag2"])
            self.assertEqual(out[n2], [])

    def test_all_note_tags_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            n1 = record_note(store, deal_id="ccf", body="A")
            n2 = record_note(store, deal_id="aaa", body="B")
            add_note_tag(store, n1, "flag")
            add_note_tag(store, n2, "flag")
            add_note_tag(store, n1, "blocker")
            out = dict(all_note_tags(store))
            self.assertEqual(out, {"flag": 2, "blocker": 1})


class TestSearchNotesTagFilter(unittest.TestCase):
    def test_tag_filter_intersects_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            n1 = record_note(store, deal_id="ccf",
                             body="covenant reset discussed")
            n2 = record_note(store, deal_id="aaa",
                             body="covenant update")
            add_note_tag(store, n1, "board_meeting")
            df = search_notes(store, "covenant", tags=["board_meeting"])
            self.assertEqual(len(df), 1)
            self.assertEqual(df.iloc[0]["note_id"], n1)

    def test_tag_only_no_query_returns_tagged_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            n = record_note(store, deal_id="ccf", body="anything")
            add_note_tag(store, n, "blocker")
            df = search_notes(store, "", tags=["blocker"])
            self.assertEqual(len(df), 1)

    def test_multiple_tags_are_and(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            n1 = record_note(store, deal_id="ccf", body="A")
            n2 = record_note(store, deal_id="ccf", body="B")
            add_note_tag(store, n1, "board_meeting")
            add_note_tag(store, n1, "flag")
            add_note_tag(store, n2, "board_meeting")
            df = search_notes(store, "", tags=["board_meeting", "flag"])
            self.assertEqual(len(df), 1)
            self.assertEqual(df.iloc[0]["note_id"], n1)


class TestNoteTagsHttp(unittest.TestCase):
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

    def test_notes_page_has_tags_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/notes") as r:
                    body = r.read().decode()
                    self.assertIn('name="tags"', body)
            finally:
                server.shutdown(); server.server_close()

    def test_notes_page_tag_filter_narrows(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            n1 = record_note(store, deal_id="ccf", body="covenant notes")
            n2 = record_note(store, deal_id="aaa", body="covenant chat")
            add_note_tag(store, n1, "board_meeting")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/notes?q=covenant"
                    f"&tags=board_meeting"
                ) as r:
                    body = r.read().decode()
                    # Body text: the word "notes" follows the highlighted match
                    # for the n1 note. The n2 note body ("covenant chat")
                    # must not appear since its tag is absent.
                    self.assertIn(" notes</div>", body)
                    self.assertNotIn("chat", body)
                    # Pill rendered
                    self.assertIn(">board_meeting<", body)
            finally:
                server.shutdown(); server.server_close()

    def test_post_add_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            nid = record_note(store, deal_id="ccf", body="x")
            server, port = self._start(tmp)
            try:
                body = _p.urlencode({"tag": "flag"}).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/notes/{nid}/tags",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                )
                with _u.urlopen(req) as r:
                    data = json.loads(r.read().decode())
                    self.assertTrue(data["changed"])
                # Verify via API
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/notes/{nid}/tags"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertEqual(data["tags"], ["flag"])
            finally:
                server.shutdown(); server.server_close()

    def test_post_remove_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            nid = record_note(store, deal_id="ccf", body="x")
            add_note_tag(store, nid, "flag")
            server, port = self._start(tmp)
            try:
                body = _p.urlencode({"tag": "flag"}).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/notes/{nid}/tags/remove",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                )
                with _u.urlopen(req) as r:
                    data = json.loads(r.read().decode())
                    self.assertTrue(data["changed"])
                self.assertEqual(tags_for_note(store, nid), [])
            finally:
                server.shutdown(); server.server_close()

    def test_post_add_invalid_tag_400(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            nid = record_note(store, deal_id="ccf", body="x")
            server, port = self._start(tmp)
            try:
                body = _p.urlencode({"tag": "has space"}).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/notes/{nid}/tags",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                )
                with self.assertRaises(HTTPError) as ctx:
                    _u.urlopen(req)
                self.assertEqual(ctx.exception.code, 400)
            finally:
                server.shutdown(); server.server_close()

    def test_api_note_tags_global_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            n1 = record_note(store, deal_id="ccf", body="x")
            n2 = record_note(store, deal_id="aaa", body="y")
            add_note_tag(store, n1, "flag")
            add_note_tag(store, n2, "flag")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/note-tags"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertEqual(len(data), 1)
                    self.assertEqual(data[0]["tag"], "flag")
                    self.assertEqual(data[0]["count"], 2)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
