"""b165 — chartis_shell auto-h1 backstop for chartis-direct callers.

The 2026-05-29 audit walk found that even after the b164 fix to the
legacy `_ui_kit.shell()` helper, six chartis-direct routes still
rendered without any `<h1>`:

  /runs, /query, /settings, /engagements, /fund-learning,
  /admin/audit-chain

These pages call `chartis_shell()` directly with a plain panel body
and no editorial cadence signals. `chartis_shell` already has two
auto-inject paths for editorial pages — when ``editorial_intro=`` is
supplied, and when the body itself contains a ``ck-section-intro`` —
but neither catches plain-body callers.

Fix: a third backstop path inside `chartis_shell`. When the body
contains no ``<h1`` at all and the `title` arg is non-default, inject
a ``ck_page_title`` carrying the title. Idempotent: skip when the
body already has any h1 (which covers all 176 ``editorial_intro``
callers and every ``ck_page_title`` caller).

A new ``omit_h1: bool = False`` kwarg on `chartis_shell` lets a
caller explicitly opt out — the legacy ``_ui_kit.shell()`` helper
forwards its existing ``omit_h1`` argument so callers that already
opted out at the legacy layer keep that intent.
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


class TestChartisShellAutoInjectsH1(unittest.TestCase):
    """Helper-level coverage of the new backstop."""

    def test_plain_body_no_h1_gets_one_from_title(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        html = chartis_shell(
            body_html="<div class='cad-card'><p>plain content</p></div>",
            title="Run History",
        )
        self.assertGreaterEqual(html.count("<h1"), 1,
                                "expected an auto-injected h1")
        self.assertIn("Run History", html)

    def test_body_with_existing_h1_is_left_alone(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        html = chartis_shell(
            body_html="<h1>Existing heading</h1><p>x</p>",
            title="Should Not Appear",
        )
        # Exactly one h1 in body; backstop didn't double up.
        self.assertEqual(html.count("<h1"), 1)
        self.assertIn("Existing heading", html)
        self.assertNotIn(">Should Not Appear</h1>", html)

    def test_omit_h1_true_opts_out_of_backstop(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        html = chartis_shell(
            body_html="<p>no heading anywhere</p>",
            title="Suppressed",
            omit_h1=True,
        )
        self.assertEqual(html.count("<h1"), 0,
                         "omit_h1=True must skip the backstop")

    def test_editorial_intro_path_unaffected(self):
        """Pages passing editorial_intro hit the EARLIER auto-inject
        path (ck_page_title before ck_section_intro). The backstop
        must NOT add a second h1 in that case."""
        from rcm_mc.ui._chartis_kit import chartis_shell
        html = chartis_shell(
            body_html="<p>panels</p>",
            title="Editorial Page",
            editorial_intro={
                "eyebrow": "SECTION",
                "headline": "Bold headline here",
                "italic_word": "Bold",
            },
        )
        # Exactly one h1 — the editorial path's ck_page_title.
        # The backstop sees that h1 and skips.
        self.assertEqual(html.count("<h1"), 1,
                         "editorial_intro path must produce exactly 1 h1")

    def test_default_title_pe_desk_does_not_inject(self):
        """When no real title is provided, the shell defaults to
        'PE Desk'. The backstop must not promote the placeholder to
        a real h1 — pages with no title intent should still render
        without one."""
        from rcm_mc.ui._chartis_kit import chartis_shell
        html = chartis_shell(body_html="<p>x</p>")  # no title
        # No h1 because the synthetic 'PE Desk' title is filtered out
        # of the backstop check.
        self.assertEqual(html.count("<h1"), 0)


class TestPreviouslyMissingH1ChartisRoutes(unittest.TestCase):
    """End-to-end coverage: the six chartis-direct no-h1 routes from
    the 2026-05-29 audit all now render with at least one `<h1>`."""

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

    def test_runs_has_h1(self):
        self.assertGreaterEqual(self._fetch("/runs").count("<h1"), 1)

    def test_query_has_h1(self):
        self.assertGreaterEqual(self._fetch("/query").count("<h1"), 1)

    def test_settings_has_h1(self):
        self.assertGreaterEqual(self._fetch("/settings").count("<h1"), 1)

    def test_engagements_has_h1(self):
        self.assertGreaterEqual(self._fetch("/engagements").count("<h1"), 1)

    def test_fund_learning_has_h1(self):
        self.assertGreaterEqual(
            self._fetch("/fund-learning").count("<h1"), 1)

    def test_admin_audit_chain_has_h1(self):
        self.assertGreaterEqual(
            self._fetch("/admin/audit-chain").count("<h1"), 1)


if __name__ == "__main__":
    unittest.main()
