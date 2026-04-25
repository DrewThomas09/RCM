"""Tests for the universal Cmd-K command palette injection.

The palette used to only live on /dashboard. A PE analyst pressing
⌘K on /watchlist or /alerts expected the jump-anywhere UX and got
nothing. This regression guards against the muscle-memory gap —
every authenticated page that routes through ``chartis_shell`` now
carries the palette.
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


class TestUniversalPaletteHelpers(unittest.TestCase):
    def test_bundle_is_self_contained(self):
        """universal_palette_bundle() must include CSS, modal HTML,
        and JS in one string — caller doesn't need web_styles()."""
        from rcm_mc.ui._web_components import universal_palette_bundle
        bundle = universal_palette_bundle()
        self.assertIn("<style>", bundle)
        self.assertIn(".wc-cmdk-backdrop", bundle)
        self.assertIn('id="wc-cmdk"', bundle)
        self.assertIn("<script>", bundle)
        self.assertIn("e.key === 'k'", bundle)  # Cmd-K trigger
        self.assertIn("metaKey", bundle)         # modifier check

    def test_universal_commands_cover_daily_workflow(self):
        """Every Daily-workflow shortcut on the dashboard must also
        be a Cmd-K command, so typing the label surfaces it."""
        from rcm_mc.ui._web_components import universal_palette_commands
        commands = universal_palette_commands()
        labels = {label for _, label, _ in commands}
        for expected in ("Active alerts", "Watchlist",
                         "Pipeline & saved searches",
                         "Data refresh", "LP quarterly update",
                         "Team activity"):
            self.assertIn(expected, labels,
                          msg=f"{expected!r} missing from universal palette")

    def test_universal_commands_include_analyses(self):
        from rcm_mc.ui._web_components import universal_palette_commands
        commands = universal_palette_commands()
        labels = [l for _, l, _ in commands]
        # At least one curated analysis made it through
        self.assertIn("Thesis Pipeline", labels)


class TestPaletteOnEveryPage(unittest.TestCase):
    """Boot a real server and confirm the palette appears on the
    Daily-workflow pages that previously lacked it."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "t.db")
        cls.port = _free_port()
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

    def _get(self, path: str) -> str:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}{path}", timeout=10,
        ) as resp:
            return resp.read().decode()

    def _assert_has_palette(self, path: str, html: str) -> None:
        self.assertIn('id="wc-cmdk"', html,
                      msg=f"{path} missing palette modal")
        self.assertIn('id="wc-cmdk-input"', html,
                      msg=f"{path} missing palette input")
        self.assertIn("e.key === 'k'", html,
                      msg=f"{path} missing Cmd-K handler")

    def test_dashboard_has_palette(self):
        self._assert_has_palette("/dashboard", self._get("/dashboard"))

    def test_watchlist_has_palette(self):
        self._assert_has_palette("/watchlist", self._get("/watchlist"))

    def test_alerts_has_palette(self):
        self._assert_has_palette("/alerts", self._get("/alerts"))

    def test_pipeline_has_palette(self):
        self._assert_has_palette("/pipeline", self._get("/pipeline"))

    def test_team_has_palette(self):
        self._assert_has_palette("/team", self._get("/team"))

    def test_exports_has_palette(self):
        self._assert_has_palette("/exports", self._get("/exports"))

    def test_data_refresh_has_palette(self):
        self._assert_has_palette("/data/refresh", self._get("/data/refresh"))

    def test_lp_update_has_palette(self):
        self._assert_has_palette("/lp-update", self._get("/lp-update"))

    def test_dashboard_has_only_one_palette_modal(self):
        """Regression guard: dashboard used to inject its own palette
        AND chartis_shell injected another, yielding duplicate
        #wc-cmdk elements. Only one modal should ship now."""
        html = self._get("/dashboard")
        count = html.count('id="wc-cmdk"')
        self.assertEqual(count, 1,
                         msg=f"dashboard should have exactly 1 palette modal, got {count}")


if __name__ == "__main__":
    unittest.main()
