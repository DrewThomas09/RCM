"""Tests for the CDD Analytics Engines catalog (/cdd/tools).

The catalog renders every registered rcm_mc.cdd exhibit in the partner view.
The load-bearing guarantees: the registered REF reference engines surface here,
the partner render never leaks internal assumption nodes onto the page, and the
route is wired into the server, palette, and breadcrumb map.
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.cdd import registry
from rcm_mc.ui.cdd_tools_page import _catalog, render_cdd_tools


class CddToolsPageTests(unittest.TestCase):
    def test_renders_title_and_explainer(self):
        html = render_cdd_tools()
        self.assertIn("CDD Analytics Engines", html)
        self.assertIn("DILIGENCE · CDD CATALOG", html)

    def test_every_registered_feature_is_carded(self):
        html = render_cdd_tools()
        groups, n = _catalog()
        self.assertEqual(n, len(registry.all_features()))
        for feat in registry.all_features():
            # Each feature id appears as the card anchor id.
            self.assertIn(f'id="{feat.feature_id}"', html,
                          msg=f"{feat.feature_id} not rendered on /cdd/tools")

    def test_ref_reference_layer_surfaces(self):
        html = render_cdd_tools()
        self.assertIn("Benchmarking reference layer", html)
        for fid in ("REF-01", "REF-02", "REF-03", "REF-04", "REF-05", "REF-06"):
            self.assertIn(f'id="{fid}"', html)

    def test_partner_render_does_not_leak_assumptions(self):
        # The page renders internal_mode=False, so no assumption-node values
        # should bleed through. Spot-check a known internal-only series name.
        html = render_cdd_tools()
        self.assertNotIn("Target vs national detail", html)
        self.assertNotIn("Missing decision entries", html)

    def test_reconciled_engines_show_badge(self):
        # At least one engine reconciles, so the catalog shows the badge.
        self.assertIn("reconciled", render_cdd_tools())

    def test_route_wired_in_server_palette_and_breadcrumbs(self):
        import rcm_mc.server as server_mod
        with open(server_mod.__file__, encoding="utf-8") as f:
            handled = set(re.findall(r"""path\s*==\s*['"](/[^'"]+)['"]""", f.read()))
        self.assertIn("/cdd/tools", handled)

        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, _SUB_SECTION_MAP,
        )
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/cdd/tools", routes)
        self.assertEqual(_SUB_SECTION_MAP.get("/cdd/tools"), "diligence")


if __name__ == "__main__":
    unittest.main()
