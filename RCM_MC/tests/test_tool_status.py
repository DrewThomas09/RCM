"""Tool data-lineage status resolver (the colored status dot).

Status is a provenance claim, so these tests pin: every catalog tool is
explicitly classified (never relying on the safe default), known anchors
resolve correctly, the safe default never overclaims "live", and the dot
is accessible (not color-only).
"""
from __future__ import annotations

import unittest

import rcm_mc.data_public.module_index as mi
from rcm_mc.ui.tool_status import (
    SOURCE_META,
    audit_defaulted_routes,
    resolve_tool_status,
    status_dot,
    _illustrative_routes_from_pages,
)


class ResolverTests(unittest.TestCase):
    def test_three_states_only(self):
        self.assertEqual(set(SOURCE_META), {"live", "cms", "illustrative"})

    def test_every_catalog_tool_is_explicitly_classified(self):
        # No module in the canonical catalog may rely on the safe default —
        # each must be in the audited override or carry the illustrative
        # signal. (Keeps provenance dots evidence-based, not guessed.)
        routes = [m.route for m in mi._build_modules()]
        self.assertEqual(audit_defaulted_routes(routes), [])

    def test_known_anchors(self):
        cases = {
            "/sponsor-heatmap": "live",
            "/exit-timing": "live",       # loads realized corpus
            "/cms-sources": "cms",
            "/deal-origination": "illustrative",
            "/platform-maturity": "illustrative",  # hardcoded, no loader
            "/ic-memo-gen": "illustrative",
        }
        for route, expected in cases.items():
            self.assertEqual(resolve_tool_status(route)[0], expected, route)

    def test_safe_default_is_illustrative_never_live(self):
        # An unaudited route must default conservatively — underclaim, never
        # overclaim "live".
        status, reason = resolve_tool_status("/some-brand-new-unaudited-tool")
        self.assertEqual(status, "illustrative")
        self.assertIn("default", reason)

    def test_illustrative_note_signal_nonempty(self):
        sig = _illustrative_routes_from_pages()
        self.assertTrue(sig)  # many data_public pages declare it
        self.assertIn("/deal-origination", sig)

    def test_resolver_reasons_are_present(self):
        for route in ("/sponsor-heatmap", "/cms-sources", "/deal-origination"):
            self.assertTrue(resolve_tool_status(route)[1].strip())


class StatusDotAccessibilityTests(unittest.TestCase):
    def test_dot_is_not_color_only(self):
        dot = status_dot("/sponsor-heatmap")
        self.assertIn("tool-status-dot", dot)
        self.assertIn("aria-label=", dot)   # screen-reader text
        self.assertIn("title=", dot)         # hover tooltip
        self.assertIn('role="img"', dot)

    def test_dot_color_matches_status(self):
        live = status_dot("/sponsor-heatmap")
        illus = status_dot("/deal-origination")
        self.assertIn("sc-positive", live)    # green token
        self.assertIn("sc-warning", illus)    # amber token

    def test_label_variant(self):
        self.assertIn("tool-status-label", status_dot("/cms-sources", show_label=True))


class ModuleIndexDotsTests(unittest.TestCase):
    def test_every_module_gets_a_dot(self):
        from rcm_mc.ui.data_public.module_index_page import render_module_index
        html = render_module_index({})
        n_modules = len(mi._build_modules())
        # one dot per module card (+ a few in the legend)
        self.assertGreaterEqual(html.count('class="tool-status-dot"'), n_modules)
        self.assertIn(".tool-status-dot{", html)  # scoped CSS present


if __name__ == "__main__":
    unittest.main()
