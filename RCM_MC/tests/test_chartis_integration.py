"""Smoke tests for the five Phase 2A Chartis routes.

Wires the server on a free port and hits each route with urllib.
Assertions are intentionally shallow — we only verify the route
exists and renders without crashing. Deeper behavioural tests are
deferred to Phase 2B / 2C.

Covered:

  - GET  /home
  - GET  /pe-intelligence
  - GET  /library              (deals corpus; was /deals-library)
  - GET  /methodology          (methodology hub; was /library)
  - GET  /deals-library        301 → /library  (preserves query)
  - GET  /deal/<id>/partner-review
  - GET  /deal/<id>/red-flags
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from tests.test_alerts import _seed_with_pe_math


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _ServerHarness:
    """Context-manager wrapping build_server on a free port."""

    def __init__(self, tmp: str) -> None:
        self.tmp = tmp
        self.port = _free_port()
        self.server = None

    def __enter__(self):
        from rcm_mc.server import build_server
        self.server, _ = build_server(
            port=self.port,
            db_path=os.path.join(self.tmp, "p.db"),
        )
        t = threading.Thread(target=self.server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.05)
        return self

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def __exit__(self, exc_type, exc, tb):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()


def _fetch(url: str, *, timeout: float = 10.0) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, (exc.read() or b"").decode("utf-8", errors="replace")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Make 301/302/303 visible instead of auto-following."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # type: ignore[return-value]


def _fetch_no_redirect(url: str, *, timeout: float = 10.0):
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(url, timeout=timeout) as r:
            return r.status, r.headers.get("Location"), r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Location"), exc.read()


class TestChartisLandingRoutes(unittest.TestCase):
    """The four no-deal-required landing pages."""

    def test_home_renders_seven_panel_landing(self):
        with tempfile.TemporaryDirectory() as tmp, _ServerHarness(tmp) as srv:
            status, body = _fetch(srv.url("/home"))
            self.assertEqual(status, 200)
            self.assertIn("Seeking Chartis", body)
            self.assertIn("Home", body)
            # Panel titles that are always present even with zero deals.
            self.assertIn("Pipeline Funnel", body)
            self.assertIn("PE Intelligence Highlights", body)
            self.assertIn("Corpus Insights", body)

    def test_pe_intelligence_hub_renders(self):
        with tempfile.TemporaryDirectory() as tmp, _ServerHarness(tmp) as srv:
            status, body = _fetch(srv.url("/pe-intelligence"))
            self.assertEqual(status, 200)
            self.assertIn("PE Intelligence", body)
            self.assertIn("SEVEN PARTNER REFLEXES", body)
            self.assertIn("Archetype Library", body)

    def test_library_serves_deals_corpus(self):
        with tempfile.TemporaryDirectory() as tmp, _ServerHarness(tmp) as srv:
            status, body = _fetch(srv.url("/library"))
            self.assertEqual(status, 200)
            self.assertIn("Deals Library", body)
            self.assertIn("DEAL CORPUS", body)

    def test_methodology_serves_reference_hub(self):
        with tempfile.TemporaryDirectory() as tmp, _ServerHarness(tmp) as srv:
            status, body = _fetch(srv.url("/methodology"))
            self.assertEqual(status, 200)
            self.assertIn("Methodology", body)
            self.assertIn("Valuation Models", body)

    def test_deals_library_301_redirects_to_library(self):
        with tempfile.TemporaryDirectory() as tmp, _ServerHarness(tmp) as srv:
            status, location, _ = _fetch_no_redirect(srv.url("/deals-library"))
            self.assertEqual(status, 301)
            self.assertEqual(location, "/library")

    def test_deals_library_301_preserves_query(self):
        with tempfile.TemporaryDirectory() as tmp, _ServerHarness(tmp) as srv:
            status, location, _ = _fetch_no_redirect(
                srv.url("/deals-library?sector=Hospital&regime=expansion")
            )
            self.assertEqual(status, 301)
            self.assertEqual(location, "/library?sector=Hospital&regime=expansion")


class TestChartisPerDealRoutes(unittest.TestCase):
    """The two per-deal brain surfaces."""

    def test_partner_review_renders_for_seeded_deal(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "testdeal")
            with _ServerHarness(tmp) as srv:
                status, body = _fetch(srv.url("/deal/testdeal/partner-review"))
                self.assertEqual(status, 200)
                self.assertIn("testdeal", body)
                self.assertIn("Partner Review", body)

    def test_partner_review_handles_missing_deal_without_500(self):
        with tempfile.TemporaryDirectory() as tmp, _ServerHarness(tmp) as srv:
            status, body = _fetch(srv.url("/deal/nonexistent/partner-review"))
            self.assertEqual(status, 200)
            self.assertIn("nonexistent", body)
            self.assertIn("INSUFFICIENT DATA", body)

    def test_red_flags_renders_for_seeded_deal(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "testdeal")
            with _ServerHarness(tmp) as srv:
                status, body = _fetch(srv.url("/deal/testdeal/red-flags"))
                self.assertEqual(status, 200)
                self.assertIn("testdeal", body)
                self.assertIn("Red Flags", body)

    def test_red_flags_handles_missing_deal_without_500(self):
        with tempfile.TemporaryDirectory() as tmp, _ServerHarness(tmp) as srv:
            status, body = _fetch(srv.url("/deal/nonexistent/red-flags"))
            self.assertEqual(status, 200)
            self.assertIn("nonexistent", body)
            self.assertIn("UNAVAILABLE", body)


if __name__ == "__main__":
    unittest.main()
