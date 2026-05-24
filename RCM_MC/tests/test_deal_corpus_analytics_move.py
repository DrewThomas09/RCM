"""PR C — Portfolio Analytics reframed as Deal Corpus Analytics, moved to
Research, with a redirect from the old route.

The 655-deal page is a BENCHMARK CORPUS, not the user's portfolio. Pins:
- /deal-corpus-analytics renders (200) with the corrected title + chip;
- /portfolio-analytics redirects to it (no longer renders as "Portfolio
  Analytics");
- nav: the page is under Research, not Portfolio;
- no misleading "Portfolio Analytics" page framing remains.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import closing


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):  # don't follow — observe the 3xx
        return None


class DealCorpusAnalyticsMoveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.port = _free_port()
        from rcm_mc.server import build_server
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=os.path.join(cls.tmp.name, "t.db"), auth=None)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()
        cls.thread.join(timeout=5); cls.tmp.cleanup()

    def _get(self, path, follow=True):
        url = f"http://127.0.0.1:{self.port}{path}"
        opener = (urllib.request.build_opener()
                  if follow else urllib.request.build_opener(_NoRedirect))
        try:
            with opener.open(url, timeout=30) as resp:
                return resp.status, resp.headers.get("Location"), \
                    resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.headers.get("Location"), \
                exc.read().decode("utf-8", "replace")

    def test_new_route_renders(self):
        status, _, html = self._get("/deal-corpus-analytics")
        self.assertEqual(status, 200, msg=html[:400])
        self.assertIn("Deal Corpus Analytics", html)
        self.assertIn("BENCHMARK CORPUS", html)         # data-universe chip

    def test_old_route_redirects(self):
        status, location, _ = self._get("/portfolio-analytics", follow=False)
        self.assertIn(status, (301, 302, 303, 307, 308))
        self.assertIn("/deal-corpus-analytics", location or "")

    def test_old_route_preserves_query_on_redirect(self):
        status, location, _ = self._get(
            "/portfolio-analytics?subsector=ASC", follow=False)
        self.assertIn(status, (301, 302, 303, 307, 308))
        self.assertIn("subsector=ASC", location or "")

    def test_new_route_not_misframed_as_portfolio(self):
        _, _, html = self._get("/deal-corpus-analytics")
        # The page title must not present as the user's portfolio.
        self.assertNotIn("PORTFOLIO ANALYTICS", html)

    def test_nav_places_under_research_not_portfolio(self):
        from rcm_mc.ui._chartis_kit import _SUB_NAV, _resolve_sub_section
        research = [i["href"] for i in _SUB_NAV["research"]]
        portfolio = [i["href"] for i in _SUB_NAV["portfolio"]]
        self.assertIn("/deal-corpus-analytics", research)
        self.assertNotIn("/portfolio-analytics", portfolio)
        self.assertNotIn("/deal-corpus-analytics", portfolio)
        self.assertEqual(_resolve_sub_section("/deal-corpus-analytics"), "research")


if __name__ == "__main__":
    unittest.main()
