"""Tests for deal tags (Brick 86)."""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.deals.deal_tags import (
    _normalize,
    add_tag,
    all_tags,
    deals_by_tag,
    remove_tag,
    tags_for,
)
from rcm_mc.portfolio.store import PortfolioStore


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestNormalize(unittest.TestCase):
    def test_lowercases_and_trims(self):
        self.assertEqual(_normalize("  Growth  "), "growth")

    def test_preserves_valid_punctuation(self):
        self.assertEqual(_normalize("region:tx"), "region:tx")
        self.assertEqual(_normalize("owner:at"), "owner:at")
        self.assertEqual(_normalize("fund_3"), "fund_3")
        self.assertEqual(_normalize("q2-review"), "q2-review")

    def test_rejects_empty(self):
        for bad in ("", "   ", None):
            with self.assertRaises(ValueError):
                _normalize(bad)  # type: ignore[arg-type]

    def test_rejects_spaces(self):
        with self.assertRaises(ValueError):
            _normalize("watch list")

    def test_rejects_too_long(self):
        with self.assertRaises(ValueError):
            _normalize("a" * 41)

    def test_rejects_invalid_leading_char(self):
        with self.assertRaises(ValueError):
            _normalize("-growth")  # leading dash


class TestAddRemoveTag(unittest.TestCase):
    def test_add_returns_true_when_new(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            self.assertTrue(add_tag(store, "ccf", "growth"))

    def test_add_returns_false_on_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            add_tag(store, "ccf", "growth")
            self.assertFalse(add_tag(store, "ccf", "growth"))

    def test_case_insensitive_dedup(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            add_tag(store, "ccf", "Growth")
            self.assertFalse(add_tag(store, "ccf", "growth"))
            self.assertEqual(tags_for(store, "ccf"), ["growth"])

    def test_remove_returns_true_when_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            add_tag(store, "ccf", "growth")
            self.assertTrue(remove_tag(store, "ccf", "growth"))

    def test_remove_returns_false_when_not_tagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            self.assertFalse(remove_tag(store, "ccf", "growth"))


class TestTagsFor(unittest.TestCase):
    def test_empty_store_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(tags_for(_store(tmp), "nope"), [])

    def test_sorted_alphabetically(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            for t in ("zebra", "apple", "mango"):
                add_tag(store, "ccf", t)
            self.assertEqual(tags_for(store, "ccf"), ["apple", "mango", "zebra"])

    def test_per_deal_scoping(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            add_tag(store, "ccf", "growth")
            add_tag(store, "mgh", "core")
            self.assertEqual(tags_for(store, "ccf"), ["growth"])
            self.assertEqual(tags_for(store, "mgh"), ["core"])


class TestDealsByTag(unittest.TestCase):
    def test_returns_all_deals_with_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            for did in ("ccf", "mgh", "nyp"):
                add_tag(store, did, "watch")
            self.assertEqual(
                sorted(deals_by_tag(store, "watch")),
                ["ccf", "mgh", "nyp"],
            )

    def test_case_insensitive_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            add_tag(store, "ccf", "Growth")
            self.assertEqual(deals_by_tag(store, "GROWTH"), ["ccf"])


class TestAllTags(unittest.TestCase):
    def test_usage_counts_and_ordering(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            # "watch" used 3x, "growth" 1x
            for did in ("a", "b", "c"):
                add_tag(store, did, "watch")
            add_tag(store, "a", "growth")
            tags = all_tags(store)
            self.assertEqual(tags[0], ("watch", 3))
            self.assertEqual(tags[1], ("growth", 1))


class TestTagsHttpIntegration(unittest.TestCase):
    def _start(self, db_path):
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

    def test_post_tag_adds_to_store(self):
        import urllib.parse as _p
        import urllib.request as _u
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(os.path.join(tmp, "p.db"))
            try:
                body = _p.urlencode({"tag": "growth"}).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/deals/ccf/tags",
                    data=body,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    method="POST",
                )
                class _NoRedirect(_u.HTTPRedirectHandler):
                    def http_error_303(self, *a, **kw):
                        return None
                try:
                    _u.build_opener(_NoRedirect).open(req)
                except HTTPError:
                    pass
                self.assertEqual(
                    tags_for(PortfolioStore(os.path.join(tmp, "p.db")), "ccf"),
                    ["growth"],
                )
            finally:
                server.shutdown()
                server.server_close()

    def test_post_bad_tag_returns_400(self):
        import urllib.parse as _p
        import urllib.request as _u
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(os.path.join(tmp, "p.db"))
            try:
                body = _p.urlencode({"tag": "bad tag with spaces"}).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/deals/ccf/tags",
                    data=body,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    method="POST",
                )
                with self.assertRaises(HTTPError) as ctx:
                    _u.urlopen(req)
                self.assertEqual(ctx.exception.code, 400)
            finally:
                server.shutdown()
                server.server_close()

    def test_remove_tag_via_post(self):
        import urllib.request as _u
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            add_tag(store, "ccf", "growth")
            server, port = self._start(os.path.join(tmp, "p.db"))
            try:
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/deals/ccf/tags/growth/remove",
                    data=b"", method="POST",
                )
                class _NoRedirect(_u.HTTPRedirectHandler):
                    def http_error_303(self, *a, **kw):
                        return None
                try:
                    _u.build_opener(_NoRedirect).open(req)
                except HTTPError:
                    pass
                self.assertEqual(tags_for(store, "ccf"), [])
            finally:
                server.shutdown()
                server.server_close()

    def test_api_tags_returns_portfolio_usage(self):
        import json as _json
        import urllib.request as _u
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            add_tag(store, "a", "watch")
            add_tag(store, "b", "watch")
            add_tag(store, "a", "growth")
            server, port = self._start(os.path.join(tmp, "p.db"))
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/api/tags") as r:
                    data = _json.loads(r.read().decode())
                    tags = {d["tag"]: d["count"] for d in data}
                    self.assertEqual(tags["watch"], 2)
                    self.assertEqual(tags["growth"], 1)
            finally:
                server.shutdown()
                server.server_close()

    def test_deal_page_renders_tags_card(self):
        import urllib.request as _u
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            from rcm_mc.portfolio.portfolio_snapshots import register_snapshot
            register_snapshot(store, "ccf", "hold")
            add_tag(store, "ccf", "growth")
            add_tag(store, "ccf", "region:tx")
            server, port = self._start(os.path.join(tmp, "p.db"))
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/ccf") as r:
                    body = r.read().decode()
                    # Tags section label (whitespace-tolerant)
                    self.assertRegex(body, r">\s*Tags\s*<")
                    # Each tag value renders inside a badge
                    self.assertIn("growth", body)
                    self.assertIn("region:tx", body)
                    # Remove button POST action
                    self.assertIn("/api/deals/ccf/tags/growth/remove", body)
                    # Add form
                    self.assertIn('action="/api/deals/ccf/tags"', body)
            finally:
                server.shutdown()
                server.server_close()
