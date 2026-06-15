"""Healthcare Verticals & Life-Sciences deep-dive page.

The page is a static sector-intelligence brief surfaced under Research.
These tests pin (1) that it renders the headline figures and all 15
verticals, (2) that it is reachable on a real server at
``/healthcare-verticals/life-sciences``, and (3) that the nav/palette wiring is
present so the subnav-integrity walker keeps it openable.
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


class HealthcareVerticalsRenderTests(unittest.TestCase):
    def setUp(self):
        from rcm_mc.ui.healthcare_verticals_deepdive_page import (
            render_healthcare_verticals_deepdive,
        )
        self.html = render_healthcare_verticals_deepdive()

    def test_renders_headline_anchor_figures(self):
        for needle in ("127.28", "$81.4B", "80%", "$262 billion"):
            self.assertIn(needle, self.html, msg=f"missing {needle!r}")

    def test_renders_all_fifteen_verticals(self):
        import html as _html
        from rcm_mc.ui.healthcare_verticals_deepdive_page import _VERTICALS
        self.assertEqual(len(_VERTICALS), 15)
        for v in _VERTICALS:
            # names carry "&" (escaped to &amp; in the rendered HTML).
            self.assertIn(_html.escape(v["name"]), self.html,
                          msg=f"missing {v['name']}")

    def test_carries_provider_and_life_science_groups(self):
        self.assertIn("Group A", self.html)
        self.assertIn("Group B", self.html)


class HealthcareVerticalsRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.port = _free_port()
        from rcm_mc.server import build_server
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=os.path.join(cls.tmp.name, "t.db"), auth=None,
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

    def test_route_opens_200(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/healthcare-verticals/life-sciences", timeout=15,
        ) as resp:
            self.assertEqual(resp.status, 200)
            body = resp.read().decode("utf-8", "replace")
        self.assertIn("Healthcare Verticals", body)
        self.assertIn("127.28", body)


class HealthcareVerticalsNavWiringTests(unittest.TestCase):
    def test_in_research_subnav(self):
        from rcm_mc.ui._chartis_kit import _SUB_NAV
        hrefs = {s["href"] for s in _SUB_NAV["research"] if isinstance(s, dict)}
        self.assertIn("/healthcare-verticals/life-sciences", hrefs)

    def test_in_section_map(self):
        from rcm_mc.ui._chartis_kit import _SUB_SECTION_MAP
        self.assertEqual(
            _SUB_SECTION_MAP.get("/healthcare-verticals/life-sciences"), "research")

    def test_in_command_palette(self):
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/healthcare-verticals/life-sciences", routes)


if __name__ == "__main__":
    unittest.main()
