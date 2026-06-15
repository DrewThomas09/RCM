"""Tests for the CDD analytics tools catalog (/cdd/tools).

The page is a live window onto the rcm_mc.cdd registry, so the
load-bearing guarantees are: the index lists every registered tool, a
detail page runs each tool's demo without 500-ing, the audience
separation holds (the partner render never carries assumption nodes the
internal render does), and the page is wired into nav, palette, and
breadcrumbs.
"""
from __future__ import annotations

import html as _html
import unittest

from rcm_mc.cdd import registry
from rcm_mc.ui.cdd_tools_page import (
    cdd_tools_catalog, cdd_tools_index_csv, render_cdd_tool_detail,
    render_cdd_tools,
)


class CddToolsIndexTests(unittest.TestCase):
    def test_index_lists_every_registered_tool(self):
        html = render_cdd_tools()
        self.assertIn("CDD Analytics Engines", html)
        for feat in registry.all_features():
            self.assertIn(_html.escape(feat.feature_id), html)
            self.assertIn(f"/cdd/tools/{feat.feature_id}", html)

    def test_catalog_matches_registry(self):
        cat = cdd_tools_catalog()
        self.assertEqual(
            {c["feature_id"] for c in cat},
            set(registry.feature_ids()))
        for c in cat:
            self.assertIn("title", c)
            self.assertIn("audience", c)
            self.assertIn("family", c)

    def test_csv_header_and_row_count(self):
        csv = cdd_tools_index_csv()
        lines = [ln for ln in csv.splitlines() if ln]
        self.assertEqual(lines[0], "feature_id,title,audience,family")
        self.assertEqual(len(lines) - 1, len(registry.feature_ids()))


class CddToolsDetailTests(unittest.TestCase):
    def test_every_tool_renders_in_both_audiences(self):
        for feat in registry.all_features():
            for params in ({}, {"internal": "1"}):
                html = render_cdd_tool_detail(feat.feature_id, params)
                self.assertIn("<html", html.lower(),
                              msg=f"{feat.feature_id} did not render")
                self.assertIn(_html.escape(feat.title), html)

    def test_partner_render_hides_internal_assumption_nodes(self):
        # NEW-01 (tam_sam_som) carries internal-only assumption nodes; the
        # partner detail must not surface the "Assumption nodes (internal)"
        # block, the internal detail must.
        partner = render_cdd_tool_detail("NEW-01", {})
        internal = render_cdd_tool_detail("NEW-01", {"internal": "1"})
        self.assertNotIn("Assumption nodes", partner)
        self.assertIn("Assumption nodes", internal)

    def test_flags_surface_on_detail(self):
        # NEW-21 fires wide_estimate_divergence + basis_mismatch on its demo.
        html = render_cdd_tool_detail("NEW-21", {})
        self.assertIn("wide_estimate_divergence", html)
        self.assertIn("basis_mismatch", html)

    def test_reconciliation_status_shown(self):
        html = render_cdd_tool_detail("NEW-21", {})
        self.assertIn("Reconciliation", html)

    def test_unknown_tool_is_not_found_not_error(self):
        html = render_cdd_tool_detail("NOPE-99", {})
        self.assertIn("not found", html.lower())
        self.assertIn("<html", html.lower())


class CddToolsWiringTests(unittest.TestCase):
    def test_registered_in_palette_nav_and_breadcrumbs(self):
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, _SUB_NAV, _SUB_SECTION_MAP,
        )
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/cdd/tools", routes)
        self.assertEqual(_SUB_SECTION_MAP.get("/cdd/tools"), "diligence")
        diligence_hrefs = {e["href"] for e in _SUB_NAV["diligence"]}
        self.assertIn("/cdd/tools", diligence_hrefs)

    def test_server_serves_the_routes(self):
        import re
        import rcm_mc.server as server_mod
        with open(server_mod.__file__, encoding="utf-8") as f:
            src = f.read()
        handled = set(re.findall(r"""path\s*==\s*['"](/[^'"]+)['"]""", src))
        self.assertIn("/cdd/tools", handled)
        self.assertIn("/api/cdd/tools", handled)
        self.assertIn('path.startswith("/cdd/tools/")', src)


if __name__ == "__main__":
    unittest.main()
