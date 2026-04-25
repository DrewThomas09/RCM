"""Tests for the Cmd-K / Ctrl-K command palette.

No browser driver — the palette is pure HTML + inline JS that's a
thin client on top of the existing ``/api/deals/search`` endpoint.
These tests verify:
  1. The modal markup + CSS + JS helpers exist and are well-formed.
  2. The dashboard actually includes them (discoverability hint +
     modal HTML + JS handler).
  3. The backing search endpoint returns the shape the JS expects.
  4. HTML-escape in the JS renderer guards against XSS from
     attacker-controlled deal names.
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


class TestPaletteHelpers(unittest.TestCase):
    def test_modal_markup_well_formed(self):
        from rcm_mc.ui._web_components import command_palette
        html = command_palette()
        # Structural markers
        self.assertIn('id="wc-cmdk"', html)
        self.assertIn('role="dialog"', html)
        self.assertIn('aria-hidden="true"', html,
                      msg="modal must start hidden")
        self.assertIn('id="wc-cmdk-input"', html)
        self.assertIn('id="wc-cmdk-results"', html)
        # Keyboard hint footer lists the three nav keys
        for key in ("↑", "↓", "⏎", "esc"):
            self.assertIn(key, html)

    def test_js_wires_cmdk_keyboard_shortcut(self):
        from rcm_mc.ui._web_components import command_palette_js
        js = command_palette_js()
        # Global keyboard handler fires on 'k' + modifier
        self.assertIn("e.key === 'k'", js)
        self.assertIn("metaKey", js)
        self.assertIn("ctrlKey", js)

    def test_js_escapes_html_in_results(self):
        """Deal names could contain attacker-controlled HTML
        (quotes, angle brackets). The JS escape() helper must
        neutralize them before injecting into the result list.
        """
        from rcm_mc.ui._web_components import command_palette_js
        js = command_palette_js()
        # The escape helper + the char class it handles
        self.assertIn("function escape(", js)
        for char_entity in ("&amp;", "&lt;", "&gt;", "&quot;", "&#39;"):
            self.assertIn(char_entity, js,
                          msg=f"escape() must produce {char_entity!r}")

    def test_js_navigation_keys(self):
        from rcm_mc.ui._web_components import command_palette_js
        js = command_palette_js()
        for key in ("ArrowUp", "ArrowDown", "Enter", "Escape"):
            self.assertIn(key, js)

    def test_js_hits_the_real_search_endpoint(self):
        from rcm_mc.ui._web_components import command_palette_js
        js = command_palette_js()
        self.assertIn("/api/deals/search?q=", js)
        # Uses credentials: same-origin so the session cookie flows
        self.assertIn("same-origin", js)

    def test_css_has_modal_styles(self):
        from rcm_mc.ui._web_components import web_styles
        css = web_styles()
        for cls in (".wc-cmdk-backdrop", ".wc-cmdk-card",
                    ".wc-cmdk-input", ".wc-cmdk-results",
                    ".wc-cmdk-row", ".wc-cmdk-active"):
            self.assertIn(cls, css,
                          msg=f"CSS class {cls} missing from web_styles")


class TestDashboardIncludesPalette(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        PortfolioStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_dashboard_has_modal(self):
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertIn('id="wc-cmdk"', html)
        self.assertIn('id="wc-cmdk-input"', html)

    def test_dashboard_has_cmdk_js(self):
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertIn("e.key === 'k'", html,
                      msg="dashboard must include the Cmd-K JS handler")

    def test_dashboard_shows_discoverability_hint(self):
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        # Hint strip above the dashboard so the feature is findable
        # even by a partner who doesn't know the SaaS convention.
        self.assertIn("⌘K", html)
        self.assertIn("Ctrl-K", html)
        self.assertIn("jump to a deal", html.lower())


class TestStaticCommands(unittest.TestCase):
    """The palette now supports baked-in static commands (navigation
    and curated-analysis launches) alongside live deal search.

    The Python helper serializes a list of (category, label, href)
    tuples into a JS array; the JS filters them client-side. These
    tests verify the serialization + filtering logic.
    """

    def test_commands_serialize_to_json_array(self):
        from rcm_mc.ui._web_components import command_palette_js
        js = command_palette_js(static_commands=[
            ("Go", "Alerts", "/alerts"),
            ("Run", "Thesis Pipeline", "/diligence/thesis-pipeline"),
        ])
        self.assertIn('"category": "Go"', js)
        self.assertIn('"label": "Alerts"', js)
        self.assertIn('"href": "/alerts"', js)
        self.assertIn('"Thesis Pipeline"', js)

    def test_commands_escape_quotes(self):
        """A command label with a quote would break the JSON literal
        if inserted raw. json.dumps handles it, but verify."""
        from rcm_mc.ui._web_components import command_palette_js
        js = command_palette_js(static_commands=[
            ("Run", 'Quote"Test', "/x"),
        ])
        self.assertIn(r'"Quote\"Test"', js)

    def test_empty_commands_preserves_backward_compat(self):
        """Passing no static_commands should yield JS that works
        like the deal-only original."""
        from rcm_mc.ui._web_components import command_palette_js
        js = command_palette_js()
        self.assertIn("STATIC_COMMANDS = []", js)
        # Still has the fetch to /api/deals/search
        self.assertIn("/api/deals/search?q=", js)

    def test_js_filters_commands_by_label_or_category(self):
        from rcm_mc.ui._web_components import command_palette_js
        js = command_palette_js(static_commands=[("Go", "Alerts", "/a")])
        # Filter function checks both label AND category so typing
        # "go" surfaces navigation commands + typing "alerts" surfaces
        # the specific page.
        self.assertIn("c.label.toLowerCase()", js)
        self.assertIn("c.category.toLowerCase()", js)

    def test_section_labels_group_commands_vs_deals(self):
        from rcm_mc.ui._web_components import command_palette_js
        js = command_palette_js(static_commands=[("Go", "X", "/x")])
        self.assertIn("wc-cmdk-section", js)
        self.assertIn("Deals & hospitals", js)


class TestDashboardWiresPaletteCommands(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        PortfolioStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_dashboard_includes_navigation_commands(self):
        """Dashboard must feed the 8 workflow pages + curated
        analyses into the palette so typing "alerts" or "thesis"
        finds them without a server round-trip."""
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        # Navigation hops
        self.assertIn('"label": "Active alerts"', html)
        self.assertIn('"label": "Watchlist"', html)
        self.assertIn('"label": "Downloads"', html)
        # Curated analyses
        self.assertIn('"label": "Thesis Pipeline"', html)
        self.assertIn('"label": "HCRIS Peer X-Ray"', html)
        # Categories
        self.assertIn('"category": "Go"', html)
        self.assertIn('"category": "Run"', html)


class TestSearchEndpointContract(unittest.TestCase):
    """The JS depends on ``{"results": [{deal_id, name, archived}]}``.
    Guard the contract end-to-end by actually hitting the endpoint."""

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

    def test_empty_query_returns_empty_results(self):
        import json
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/api/deals/search?q=",
            timeout=5,
        ) as resp:
            body = json.loads(resp.read())
        self.assertEqual(body.get("query"), "")
        self.assertEqual(body.get("results"), [])

    def test_query_returns_structured_shape(self):
        """Regardless of whether there are matches, results is a
        list. Each item (if any) has deal_id + name + archived."""
        import json
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/api/deals/search?q=hospital",
            timeout=5,
        ) as resp:
            body = json.loads(resp.read())
        self.assertIsInstance(body.get("results"), list)
        for r in body["results"]:
            self.assertIn("deal_id", r)
            self.assertIn("name", r)


if __name__ == "__main__":
    unittest.main()
