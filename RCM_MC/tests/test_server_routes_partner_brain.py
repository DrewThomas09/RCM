"""Tests for Partner Brain routes (Phase 0).

Covers:
- ``/partner-brain`` hub landing page
- ``/partner-brain/review`` — demo path (no deal_id) + review shape
- ``/partner-brain/<unknown>`` — category stub
- ``/partner-brain/failures`` — known category stub ("PHASE 1")

Strategy mirrors ``test_server.py``: renderers are exercised directly
for structural assertions (fast), then a single live-server spin
confirms the route blocks are actually wired.
"""
from __future__ import annotations

import os
import socket as _socket
import tempfile
import threading
import time
import unittest
import urllib.request

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.server import build_server
from rcm_mc.ui.data_public.partner_brain_hub_page import (
    render_partner_brain_hub,
    render_partner_brain_category_stub,
)
from rcm_mc.ui.data_public.partner_review_page import render_partner_review


def _start_server(db_path: str):
    s = _socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    server, _ = build_server(port=port, db_path=db_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    return server, port


class TestPartnerBrainHubRender(unittest.TestCase):
    def test_hub_renders_with_categories(self):
        html = render_partner_brain_hub({})
        self.assertIn("Partner Brain", html)
        self.assertIn("Partner Review", html)
        self.assertIn("IC Decision", html)
        self.assertIn("Named Failures", html)
        self.assertIn("18", html)  # category count in KPI strip

    def test_hub_cards_link_to_category_slugs(self):
        html = render_partner_brain_hub({})
        self.assertIn('href="/partner-brain/review"', html)
        self.assertIn('href="/partner-brain/failures"', html)
        self.assertIn('href="/partner-brain/ic-decision"', html)

    def test_hub_identifies_live_vs_pending(self):
        html = render_partner_brain_hub({})
        self.assertIn("LIVE", html)
        self.assertIn("PHASE 1", html)


class TestPartnerBrainCategoryStub(unittest.TestCase):
    def test_known_category_shows_module_count(self):
        html = render_partner_brain_category_stub({"slug": "failures"})
        self.assertIn("Named Failures", html)
        self.assertIn("Coming in Phase 1", html)
        self.assertIn("denial_fix_pace_detector", html)

    def test_unknown_slug_shows_hub_link(self):
        html = render_partner_brain_category_stub({"slug": "nonexistent"})
        self.assertIn("Unknown category", html)
        self.assertIn("/partner-brain", html)

    def test_review_slug_handled_elsewhere_but_stub_renders(self):
        # /partner-brain/review is routed to the review page; the stub
        # still renders a meaningful page if someone reaches it.
        html = render_partner_brain_category_stub({"slug": "review"})
        self.assertIn("Partner Review", html)


class TestPartnerReviewPage(unittest.TestCase):
    def test_demo_path_renders_full_review(self):
        html = render_partner_review({})
        self.assertIn("Partner Review", html)
        self.assertIn("DEMO DATA", html)
        self.assertIn("/partner-brain", html)
        # Core review pieces should be present on demo data
        self.assertIn("Recommendation", html)
        self.assertIn("Narrative", html)
        self.assertIn("Heuristic hits", html)
        self.assertIn("Reasonableness bands", html)
        self.assertIn("Context summary", html)

    def test_unresolvable_deal_id_falls_back_to_demo(self):
        html = render_partner_review({"deal_id": "nonexistent_deal_xyz"})
        # Falls back to demo silently — page still renders
        self.assertIn("Partner Review", html)
        self.assertIn("DEMO DATA", html)

    def test_demo_review_contains_seeded_deal_name(self):
        html = render_partner_review({})
        self.assertIn("Acme Regional", html)

    def test_demo_review_mentions_band_verdicts(self):
        html = render_partner_review({})
        # At least one band verdict badge should be present from the
        # reasonableness checks on the seeded context.
        self.assertTrue(
            any(v in html for v in ("IN_BAND", "STRETCH", "OUT_OF_BAND", "UNKNOWN")),
            "expected at least one band verdict badge",
        )


class TestPartnerBrainLiveRoutes(unittest.TestCase):
    def test_hub_route_returns_200(self):
        with tempfile.TemporaryDirectory() as tmp:
            PortfolioStore(os.path.join(tmp, "p.db"))  # initialize
            server, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/partner-brain"
                ) as r:
                    self.assertEqual(r.status, 200)
                    body = r.read().decode()
                    self.assertIn("Partner Brain", body)
                    self.assertIn("Partner Review", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_review_route_returns_200_without_deal_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            PortfolioStore(os.path.join(tmp, "p.db"))
            server, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/partner-brain/review"
                ) as r:
                    self.assertEqual(r.status, 200)
                    body = r.read().decode()
                    self.assertIn("Partner Review", body)
                    self.assertIn("DEMO DATA", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_category_stub_route_returns_200(self):
        with tempfile.TemporaryDirectory() as tmp:
            PortfolioStore(os.path.join(tmp, "p.db"))
            server, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/partner-brain/ic-decision"
                ) as r:
                    self.assertEqual(r.status, 200)
                    body = r.read().decode()
                    self.assertIn("IC Decision", body)
                    self.assertIn("Coming in Phase 1", body)
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
