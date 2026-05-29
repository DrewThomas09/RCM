"""b164 — legacy ``_ui_kit.shell()`` now auto-injects an editorial ``<h1>``
from its ``title`` argument when the supplied body has none.

The 2026-05-29 PE Desk audit walk found 11 partner-facing pages routed
through the legacy ``shell()`` helper that rendered without any
``<h1>``: /cohorts, /deadlines, /owners, /variance, /initiatives,
/jobs, /upload, /users, plus /activity and /audit (which already had
chrome-injected h1s and remain unaffected).

The fix lives in one place — ``_ui_kit.shell()`` now honors the
already-existing ``omit_h1`` kwarg: when False (default) and the body
contains no ``<h1`` opening tag, an editorial-styled h1 is prepended
carrying the page title. Pages that already emit their own h1 (via
``ck_page_title`` or hand-rolled markup) are detected and skipped, so
the change can never produce a double-h1.

Three classes of regression coverage here:

1. Direct helper exercise — assert ``shell(body_without_h1, title)``
   produces exactly one ``<h1>`` and ``shell(body_with_h1, title)``
   leaves the existing h1 untouched.
2. End-to-end HTTP walk — assert the 8 audit-named routes each
   render with at least one ``<h1>``.
3. Negative test — assert ``omit_h1=True`` keeps the legacy
   no-injection behavior for callers that want it.
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


class TestShellAutoInjectsH1WhenMissing(unittest.TestCase):
    """Direct helper-level coverage of the new behavior."""

    def test_body_without_h1_gets_one(self):
        from rcm_mc.ui._ui_kit import shell
        html = shell(body="<p>just some paragraph content</p>",
                     title="Cohorts")
        self.assertEqual(html.count("<h1"), 1,
                         "expected one h1 auto-injected from title")
        self.assertIn(">Cohorts</h1>", html)

    def test_body_already_having_h1_left_alone(self):
        from rcm_mc.ui._ui_kit import shell
        body = "<h1>Existing heading</h1><p>body content</p>"
        html = shell(body=body, title="Whatever")
        # Exactly one h1 — the existing one. The auto-inject must not
        # fire because the body already carries `<h1`.
        self.assertEqual(html.count("<h1"), 1,
                         "auto-inject must not double the h1")
        self.assertIn("Existing heading", html)
        # The title-derived h1 must NOT appear since the body had one.
        self.assertNotIn(">Whatever</h1>", html)

    def test_omit_h1_opt_out_keeps_no_h1(self):
        from rcm_mc.ui._ui_kit import shell
        html = shell(body="<p>no heading</p>",
                     title="Diagnostic", omit_h1=True)
        # `omit_h1=True` is now honored; no auto-inject.
        self.assertEqual(html.count("<h1"), 0,
                         "omit_h1=True must skip auto-inject")

    def test_title_with_html_chars_is_escaped(self):
        from rcm_mc.ui._ui_kit import shell
        # A partner-supplied title with HTML metacharacters must be
        # escaped before landing in the h1 — same contract as the rest
        # of the shell.
        html = shell(body="<p>x</p>", title="<script>alert(1)</script>")
        # Title escaped in the h1 (no raw <script> tag in the body
        # heading) — chartis_shell also escapes the <title> tag, so a
        # raw "<script>alert" outside of attribute context shouldn't
        # land anywhere.
        self.assertNotIn("<h1 class=\"ck-page-h1\"><script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)


class TestPreviouslyMissingH1RoutesNowHaveOne(unittest.TestCase):
    """End-to-end walk: every audit-flagged legacy-shell route now
    renders at least one `<h1>` over real HTTP. The empty-DB case is
    intentional — that's the state in which the audit caught the
    invariant violation."""

    @classmethod
    def setUpClass(cls):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.server import build_server
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "t.db")
        PortfolioStore(cls.db)
        cls.port = _free_port()
        cls.server, _h = build_server(
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
            self.assertEqual(resp.status, 200, msg=f"{path} → {resp.status}")
            return resp.read().decode()

    def test_cohorts_has_h1(self):
        self.assertGreaterEqual(self._fetch("/cohorts").count("<h1"), 1)

    def test_deadlines_has_h1(self):
        self.assertGreaterEqual(self._fetch("/deadlines").count("<h1"), 1)

    def test_owners_has_h1(self):
        self.assertGreaterEqual(self._fetch("/owners").count("<h1"), 1)

    def test_variance_has_h1(self):
        self.assertGreaterEqual(self._fetch("/variance").count("<h1"), 1)

    def test_initiatives_has_h1(self):
        self.assertGreaterEqual(
            self._fetch("/initiatives").count("<h1"), 1)

    def test_jobs_has_h1(self):
        self.assertGreaterEqual(self._fetch("/jobs").count("<h1"), 1)

    def test_upload_has_h1(self):
        self.assertGreaterEqual(self._fetch("/upload").count("<h1"), 1)

    def test_users_has_h1(self):
        self.assertGreaterEqual(self._fetch("/users").count("<h1"), 1)


if __name__ == "__main__":
    unittest.main()
