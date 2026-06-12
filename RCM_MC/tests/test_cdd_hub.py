"""Tests for the Commercial Due Diligence hub (/cdd).

The hub is pure navigation, so the load-bearing guarantee is link
integrity: every card must point at a route the server actually
serves. A hub with dead links is worse than no hub."""
from __future__ import annotations

import html as _html
import re
import unittest

from rcm_mc.ui.cdd_hub_page import _MODULES, render_cdd_hub


class CddHubTests(unittest.TestCase):
    def test_renders_five_modules(self):
        html = render_cdd_hub()
        self.assertIn("Commercial Due Diligence Hub", html)
        for title, _, _ in _MODULES:
            self.assertIn(_html.escape(title), html)

    def test_every_card_href_is_a_served_route(self):
        # _discover_all_routes filters illustrative pages off the /tools
        # grid, so check the raw handler literals instead: every hub
        # href must have an exact `path == "..."` handler in server.py.
        import rcm_mc.server as server_mod
        with open(server_mod.__file__, encoding="utf-8") as f:
            src = f.read()
        handled = set(re.findall(r"""path\s*==\s*['"](/[^'"]+)['"]""", src))
        for _, _, links in _MODULES:
            for label, href, _ in links:
                self.assertIn(
                    href, handled,
                    msg=f"CDD hub card {label!r} points at {href} "
                        f"which has no exact handler in server.py")

    def test_new_wave_surfaces_are_carded(self):
        hrefs = {href for _, _, links in _MODULES
                 for _, href, _ in links}
        for new in ("/voc-survey", "/win-loss", "/rate-environment",
                    "/excel-templates"):
            self.assertIn(new, hrefs)

    def test_registered_in_palette_nav_and_breadcrumbs(self):
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, _SUB_NAV, _SUB_SECTION_MAP,
        )
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/cdd", routes)
        self.assertEqual(_SUB_SECTION_MAP.get("/cdd"), "diligence")
        diligence_hrefs = {e["href"] for e in _SUB_NAV["diligence"]}
        self.assertIn("/cdd", diligence_hrefs)


if __name__ == "__main__":
    unittest.main()
