"""Regression tests for the Cmd-K command palette coverage.

Context: the legacy shell (`_chartis_kit_legacy.py`) ships its own
Cmd-K palette via `_PALETTE_ENTRIES` and `_palette_html()`. Earlier
in this session, I added a second palette injection in the shell
dispatcher — which created two modals both binding to Cmd-K and
opening simultaneously. This regression guard checks:

  1. The legacy shell's palette entries include every web-
     deployment surface a partner would want to jump to (watchlist,
     alerts, lp-update, team, data-refresh, etc.) AND the curated-
     analysis launchers from /dashboard's "What you can run" table.

  2. No page ships two palette modals (no `id="wc-cmdk"` extra on
     shell-rendered pages — only the legacy `id="ck-palette-bd"`).

  3. `universal_palette_bundle()` remains available for dashboard-
     specific explicit use (kept as the helper, but not
     auto-injected globally).
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


class TestLegacyPaletteEntries(unittest.TestCase):
    """The legacy palette is the one partners actually see —
    verify it covers the enhanced set."""

    def test_web_deployment_surfaces_in_palette(self):
        from rcm_mc.ui._chartis_kit_legacy import _PALETTE_ENTRIES
        labels = {label for _, label, _ in _PALETTE_ENTRIES}
        for expected in ("Dashboard (web)", "Downloads", "Data refresh",
                         "Watchlist", "My inbox", "Team activity",
                         "LP quarterly update", "Notifications",
                         "New deal wizard"):
            self.assertIn(expected, labels,
                          msg=f"{expected!r} missing from legacy palette")

    def test_curated_analyses_in_palette(self):
        from rcm_mc.ui._chartis_kit_legacy import _PALETTE_ENTRIES
        labels = {label for _, label, _ in _PALETTE_ENTRIES}
        for expected in ("Thesis Pipeline", "HCRIS Peer X-Ray",
                         "Bear Case Generator", "Covenant Stress Lab",
                         "IC Packet Builder"):
            self.assertIn(expected, labels,
                          msg=f"{expected!r} missing from legacy palette")

    def test_run_category_present(self):
        from rcm_mc.ui._chartis_kit_legacy import _PALETTE_ENTRIES
        categories = {cat for cat, _, _ in _PALETTE_ENTRIES}
        self.assertIn("RUN", categories,
                      msg="RUN category for curated launchers should exist")


class TestNoDuplicatePaletteModal(unittest.TestCase):
    """Shell-rendered pages must ship ONE palette modal, not two."""

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

    def test_single_legacy_modal_per_shell_page(self):
        """Every shell-rendered page should have exactly 1
        `ck-palette-bd` modal and 0 `wc-cmdk` backup modals."""
        for path in ("/watchlist", "/alerts", "/pipeline", "/team",
                     "/exports", "/data/refresh", "/lp-update"):
            html = self._get(path)
            ck_count = html.count('id="ck-palette-bd"')
            self.assertEqual(ck_count, 1,
                             msg=f"{path} should have exactly 1 legacy "
                                 f"palette modal, got {ck_count}")
            wc_count = html.count('id="wc-cmdk"')
            self.assertEqual(wc_count, 0,
                             msg=f"{path} leaked the universal-palette "
                                 f"duplicate modal ({wc_count} wc-cmdk)")

    def test_dashboard_has_exactly_one_palette(self):
        """/dashboard uses the shell and therefore the legacy
        palette — not a second wc-cmdk modal."""
        html = self._get("/dashboard")
        ck_count = html.count('id="ck-palette-bd"')
        wc_count = html.count('id="wc-cmdk"')
        total = ck_count + wc_count
        self.assertEqual(total, 1,
                         msg=f"dashboard should have exactly 1 palette "
                             f"modal, got {total} "
                             f"(legacy={ck_count}, wc={wc_count})")


class TestUniversalPaletteHelperRetained(unittest.TestCase):
    """The universal_palette_bundle() helper was kept for possible
    future use on pages that DON'T use chartis_shell (e.g. marketing
    pages, standalone HTML exports). Confirm it still works."""

    def test_bundle_is_self_contained(self):
        from rcm_mc.ui._web_components import universal_palette_bundle
        bundle = universal_palette_bundle()
        self.assertIn("<style>", bundle)
        self.assertIn(".wc-cmdk-backdrop", bundle)
        self.assertIn('id="wc-cmdk"', bundle)
        self.assertIn("<script>", bundle)
        self.assertIn("e.key === 'k'", bundle)

    def test_universal_commands_still_exported(self):
        from rcm_mc.ui._web_components import universal_palette_commands
        commands = universal_palette_commands()
        self.assertGreater(len(commands), 10,
                           msg="universal_palette_commands should "
                               "still expose the canonical set")


if __name__ == "__main__":
    unittest.main()
