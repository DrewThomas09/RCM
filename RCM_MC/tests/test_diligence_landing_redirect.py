"""tests for the /diligence landing redirect.

PROMPTS.md Phase 3 / Prompt 40: Checklist is the spine of the
diligence workflow, not a tab among 16. ``/diligence`` (with or
without a deal in context) redirects to ``/diligence/checklist``;
the deal_id query param is preserved so the partner lands inside
the deal's checklist with the right context.
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


class _NoFollow(urllib.request.HTTPRedirectHandler):
    def http_error_301(self, *a, **kw): return None
    def http_error_302(self, *a, **kw): return None


class DiligenceLandingRedirects(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.server import build_server

        cls.tmp = tempfile.mkdtemp(prefix="rcm_p40_")
        cls.db = os.path.join(cls.tmp, "p.db")
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        cls.server, _ = build_server(port=port, db_path=cls.db)
        cls.base = f"http://127.0.0.1:{port}"
        t = threading.Thread(target=cls.server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.05)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()

    def _get_no_follow(self, path: str) -> tuple[int, str]:
        req = urllib.request.Request(self.base + path)
        opener = urllib.request.build_opener(_NoFollow())
        try:
            opener.open(req, timeout=5)
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("Location", "")
        # If we got here, the response was a 200 — return that.
        return 200, ""

    def test_diligence_no_deal_redirects_to_checklist(self) -> None:
        code, location = self._get_no_follow("/diligence")
        self.assertEqual(code, 302)
        self.assertEqual(location, "/diligence/checklist")

    def test_diligence_with_deal_preserves_deal_id(self) -> None:
        code, location = self._get_no_follow("/diligence?deal_id=aurora")
        self.assertEqual(code, 302)
        self.assertEqual(location, "/diligence/checklist?deal_id=aurora")

    def test_deal_id_url_encoded(self) -> None:
        # Spaces and reserved chars in a deal id must reach the
        # target URL-safely.
        code, location = self._get_no_follow(
            "/diligence?deal_id=Project%20Aurora",
        )
        self.assertEqual(code, 302)
        self.assertIn("Project%20Aurora", location)


if __name__ == "__main__":
    unittest.main()
