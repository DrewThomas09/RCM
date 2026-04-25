"""Tests for the morning digest — the daily "comes to you" feature.

A partner shouldn't have to remember to open the dashboard. The
morning digest emails (or browser-previews) the same key signals
the dashboard surfaces, so the partner gets the morning view in
their inbox at 8 AM.

Reuses the same compute as the /dashboard sections, so this test
suite also pins that the email and the web view never disagree.
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import unittest
import urllib.request
from contextlib import closing
from datetime import datetime, timezone


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _seed_deal(store, deal_id: str, name: str,
               sector: str = "hospital") -> None:
    with store.connect() as con:
        con.execute(
            "INSERT INTO deals (deal_id, name, created_at, profile_json) "
            "VALUES (?, ?, ?, ?)",
            (deal_id, name, datetime.now(timezone.utc).isoformat(),
             json.dumps({"sector": sector})),
        )
        con.commit()


class TestPayloadBuilder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)
        self.store.init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def test_empty_db_returns_empty_payload(self):
        from rcm_mc.infra.morning_digest import build_morning_digest
        p = build_morning_digest(self.db)
        self.assertEqual(p.portfolio_size, 0)
        self.assertIsNone(p.headline_insight)
        self.assertEqual(p.needs_attention, [])
        self.assertEqual(p.predicted_outcomes, [])

    def test_payload_carries_portfolio_size(self):
        for i in range(4):
            _seed_deal(self.store, f"D{i}", f"Hospital {i}")
        from rcm_mc.infra.morning_digest import build_morning_digest
        p = build_morning_digest(self.db)
        self.assertEqual(p.portfolio_size, 4)

    def test_payload_includes_headline_for_healthy_portfolio(self):
        # 3+ healthy deals → all_green insight fires
        for i in range(3):
            _seed_deal(self.store, f"D{i}", f"Hospital {i}")
        from rcm_mc.infra.morning_digest import build_morning_digest
        p = build_morning_digest(self.db)
        self.assertIsNotNone(p.headline_insight)
        self.assertEqual(p.headline_insight.get("kind"), "all_green")

    def test_predicted_outcomes_for_starred_deals(self):
        from rcm_mc.deals.watchlist import star_deal
        from rcm_mc.data_public.deals_corpus import DealsCorpus
        _seed_deal(self.store, "WATCH_1", "Watch A")
        star_deal(self.store, "WATCH_1")
        DealsCorpus(self.db).seed(skip_if_populated=True)

        from rcm_mc.infra.morning_digest import build_morning_digest
        p = build_morning_digest(self.db)
        # At least one predicted-outcome entry
        self.assertGreaterEqual(len(p.predicted_outcomes), 1)
        # Carries the median MOIC
        self.assertIsNotNone(p.predicted_outcomes[0].get("median_moic"))


class TestRenderers(unittest.TestCase):
    def test_text_render_is_plain(self):
        """Plain-text rendering should have no HTML tags."""
        from rcm_mc.infra.morning_digest import (
            DigestPayload, digest_to_text,
        )
        p = DigestPayload(
            generated_at="2026-04-25T08:00:00+00:00",
            portfolio_size=12,
            headline_insight={
                "headline": "Covenant TRIPPED on DEAL_042",
                "body": "Action today.",
                "href": "/deal/DEAL_042",
                "tone": "alert",
            },
            needs_attention=[
                {"deal_id": "DEAL_042", "name": "Tripped LP",
                 "reasons": ["covenant TRIPPED"], "priority": 100,
                 "href": "/deal/DEAL_042"},
            ],
        )
        out = digest_to_text(p, base_url="https://x.com")
        # Plain text shouldn't contain HTML *tags*. Single chars like
        # `>>>` (used as a section marker) are fine; tags aren't.
        import re
        self.assertNotRegex(out, r"<[a-zA-Z/]")
        self.assertIn("Covenant TRIPPED on DEAL_042", out)
        self.assertIn("Tripped LP", out)
        self.assertIn("https://x.com/deal/DEAL_042", out)

    def test_html_render_has_inline_styles(self):
        """Email clients strip <style>; everything must be inline."""
        from rcm_mc.infra.morning_digest import (
            DigestPayload, digest_to_html,
        )
        p = DigestPayload(
            generated_at="2026-04-25T08:00:00+00:00",
            portfolio_size=5,
            headline_insight={
                "headline": "All 5 deals healthy",
                "body": "Quiet morning.",
                "href": "/pipeline",
                "tone": "positive",
            },
        )
        html = digest_to_html(p)
        self.assertNotIn("<style>", html)
        self.assertIn("All 5 deals healthy", html)
        # Tone-driven palette renders the green positive box
        self.assertIn("#f0fdf4", html)

    def test_html_escapes_user_strings(self):
        """Headlines could carry attacker-controlled text on a
        compromised deal_id field. Verify escaping."""
        from rcm_mc.infra.morning_digest import (
            DigestPayload, digest_to_html,
        )
        p = DigestPayload(
            headline_insight={
                "headline": '"><script>alert(1)</script>',
                "body": "x", "href": "#", "tone": "neutral",
            },
        )
        html = digest_to_html(p)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)


class TestHttpRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "t.db")
        cls.port = _free_port()
        # Seed minimal data so the digest has something to compute
        from rcm_mc.portfolio.store import PortfolioStore
        store = PortfolioStore(cls.db)
        store.init_db()
        for i in range(3):
            _seed_deal(store, f"DG_{i}", f"Hospital {i}")

        from rcm_mc.server import build_server
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=cls.db, auth=None,
        )
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    def test_json_preview_returns_payload_shape(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/api/digest/morning",
            timeout=10,
        ) as resp:
            self.assertEqual(resp.status, 200)
            body = json.loads(resp.read())
        for field in ("generated_at", "portfolio_size",
                      "headline_insight", "needs_attention",
                      "predicted_outcomes", "recent_events"):
            self.assertIn(field, body)
        self.assertEqual(body["portfolio_size"], 3)

    def test_html_preview_renders(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/digest/morning",
            timeout=10,
        ) as resp:
            html = resp.read().decode()
        self.assertIn("Morning digest", html)
        self.assertIn("active deals", html)


if __name__ == "__main__":
    unittest.main()
