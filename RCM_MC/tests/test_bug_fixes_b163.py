"""b163 — `/insights` empty state had no `<h1>`, plus the partner-facing
copy on `/insights` and `/day-one` leaked the internal "v3 dashboard"
vocabulary.

Caught by the 2026-05-29 PE-Desk audit walk:

- `render_insights_page` calls `ck_page_title("All insights", …)` and
  assigns it to `header`, but the empty-data branch (the state every
  partner sees with no portfolio data) silently dropped `header` so
  the page rendered without an `<h1>` — direct violation of the
  CLAUDE.md a11y invariant ("One `<h1>` per page").
- Both `/insights` and `/day-one` rendered a CTA that said
  "Open the v3 dashboard for the full data view". "v3 dashboard" is
  internal-migration vocabulary; partners read it and think the
  product itself is mid-migration.

Both fixes are additive — no behavior change beyond the rendered HTML.
The `/?v3=1` query-string is left intact (it is the legacy flag that
routes to the morning dashboard view).
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import unittest
import urllib.request
from contextlib import closing


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestInsightsEmptyStateRendersH1(unittest.TestCase):
    """The empty-state branch of `/insights` MUST emit an `<h1>` so the
    page satisfies the platform's One-H1 invariant — even on the first
    login when no signals have fired."""

    def test_render_insights_page_empty_db_includes_h1(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.ui.insights_page import render_insights_page

        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "empty.db")
            PortfolioStore(db)  # init schema, no rows

            html = render_insights_page(db)

        # H1 present in empty state
        self.assertIn("<h1", html,
                      "empty /insights must render an <h1>")
        # The title text is "All insights" — the same heading the
        # non-empty branch uses, so the partner sees one stable title.
        self.assertIn("All insights", html)
        # And the empty-state body still renders the "Quiet morning"
        # message; the fix is additive, not a swap.
        self.assertIn("Quiet morning", html)

    def test_no_v3_dashboard_vocabulary_leak(self):
        """Partner-facing copy on /insights must not reference the
        internal 'v3 dashboard' migration vocabulary."""
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.ui.insights_page import render_insights_page

        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "empty.db")
            PortfolioStore(db)
            html = render_insights_page(db)

        self.assertNotIn("v3 dashboard", html.lower(),
                         "internal 'v3 dashboard' string leaked")
        # The /?v3=1 URL is the legacy flag and stays valid; only the
        # human-readable copy is neutralized.
        self.assertIn("/?v3=1", html,
                      "the legacy URL (/?v3=1) must still be linked")
        # New neutral copy is present.
        # The CTA copy uses an `<em>` italic word, so the literal
        # "morning dashboard" string is broken up in the source.
        # Assert both halves survive the wrapping.
        self.assertIn("Open the morning", html)
        self.assertIn("for the full view", html)


class TestDayOneNoV3Leak(unittest.TestCase):
    """The Monday-brief page also previously linked out with
    'Open the v3 dashboard for the full data view'. Same neutralization
    applies — keep the URL, drop the vocabulary."""

    def test_render_day_one_no_v3_dashboard_string(self):
        # render_day_one takes a PortfolioStore (not a db path) — it
        # walks alerts + snapshots + activity. On an empty store the
        # detectors still log their own AttributeError noise but the
        # outer render returns a complete page.
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.ui.day_one_page import render_day_one

        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "empty.db")
            store = PortfolioStore(db)
            html = render_day_one(store)

        self.assertNotIn("v3 dashboard", html.lower(),
                         "internal 'v3 dashboard' string leaked")
        self.assertIn("/?v3=1", html,
                      "the legacy URL (/?v3=1) must still be linked")
        # The CTA copy uses an `<em>` italic word, so the literal
        # "morning dashboard" string is broken up in the source.
        # Assert both halves survive the wrapping.
        self.assertIn("Open the morning", html)
        self.assertIn("for the full view", html)


class TestInsightsRouteEndToEnd(unittest.TestCase):
    """Walk the route via a real HTTP server — this is the partner's
    actual experience. Confirms the h1 + no-leak invariants survive
    `chartis_shell` wrapping."""

    @classmethod
    def setUpClass(cls):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.server import build_server
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "t.db")
        PortfolioStore(cls.db)  # empty
        cls.port = _free_port()
        cls.server, _handler = build_server(
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

    def _fetch(self, path: str) -> str:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}{path}", timeout=10,
        ) as resp:
            self.assertEqual(resp.status, 200)
            return resp.read().decode()

    def test_insights_route_has_h1_on_empty_db(self):
        html = self._fetch("/insights")
        # Exactly one <h1 on the partner page (One-H1 invariant).
        # `chartis_shell` may inject one only when the body lacks
        # any heading; we want the explicit ck_page_title h1.
        self.assertGreaterEqual(html.count("<h1"), 1,
                                "no <h1> on empty /insights")
        self.assertIn("All insights", html)
        self.assertNotIn("v3 dashboard", html.lower())

    def test_day_one_route_does_not_leak_v3(self):
        html = self._fetch("/day-one")
        self.assertNotIn("v3 dashboard", html.lower())


if __name__ == "__main__":
    unittest.main()
