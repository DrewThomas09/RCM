"""P1 slice 1 — ambient active-deal context: cookies, redirect guard, shim."""
from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):  # noqa: D401
        return None


class DealContextRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.server import build_server
        db = os.path.join(tempfile.mkdtemp(prefix="dealctx_"), "t.db")
        cls.server, _ = build_server(port=0, db_path=db, host="127.0.0.1")
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        time.sleep(0.4)
        cls.opener = urllib.request.build_opener(_NoRedirect())

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def _get(self, path):
        try:
            return self.opener.open(
                f"http://127.0.0.1:{self.port}{path}", timeout=10)
        except urllib.error.HTTPError as e:   # 3xx surfaces as HTTPError
            return e

    def test_set_writes_both_cookies_and_redirects(self):
        r = self._get("/deal-context?set=atlas&return=/portfolio")
        self.assertEqual(r.status, 303)
        self.assertEqual(r.headers.get("Location"), "/portfolio")
        cookies = "\n".join(r.headers.get_all("Set-Cookie") or [])
        self.assertIn("pedesk_active_deal=atlas", cookies)
        self.assertIn("pedesk_active_deal_meta=", cookies)
        self.assertIn("SameSite=Lax", cookies)

    def test_clear_expires_cookies(self):
        r = self._get("/deal-context?set=&return=/portfolio")
        cookies = "\n".join(r.headers.get_all("Set-Cookie") or [])
        self.assertIn("pedesk_active_deal=; Max-Age=0", cookies)
        self.assertIn("pedesk_active_deal_meta=; Max-Age=0", cookies)

    def test_open_redirect_guarded(self):
        for evil in ("//evil.example", "https://evil.example", "evil"):
            r = self._get(f"/deal-context?set=x&return={evil}")
            self.assertEqual(r.headers.get("Location"), "/portfolio", evil)


class ShellShimTests(unittest.TestCase):
    def test_every_shell_page_ships_the_bar_shim(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        h = chartis_shell("<main>x</main>", "T")
        self.assertIn("ck-deal-bar", h)
        self.assertIn("pedesk_active_deal", h)
        # pre-scoped links built from the meta cookie
        self.assertIn("hcris-xray?ccn=", h)
        self.assertIn("cim-crosscheck", h)

    def test_bare_pages_skip_the_bar(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        h = chartis_shell("<main>x</main>", "Login", show_chrome=False)
        self.assertNotIn("ck-deal-bar", h)


if __name__ == "__main__":
    unittest.main()
