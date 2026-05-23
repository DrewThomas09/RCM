"""The /module-index shows a data-lineage status dot for EVERY module.

Each module carries a colored dot — LIVE (realized-deal corpus / live
portfolio), CMS (public data), or ILLUSTRATIVE (representative template) —
from the shared resolver in rcm_mc.ui.tool_status. Unlike the prior
honest-silence map, every module now resolves to an explicit status; an
unaudited route defaults conservatively to ILLUSTRATIVE (never overclaims
live). Classifications + audit reasons live in tool_status._OVERRIDE.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.module_index_page import (
    _source_badge,
    render_module_index,
)


class ModuleIndexDataTrustTests(unittest.TestCase):
    def test_badge_classification(self):
        self.assertIn("Live", _source_badge("/base-rates"))
        self.assertIn("CMS", _source_badge("/cms-data-browser"))
        self.assertIn("Illustrative", _source_badge("/locum-tracker"))
        # Previously-unmapped routes now resolve explicitly (no blank badge).
        self.assertIn("Illustrative", _source_badge("/platform-maturity"))
        # Safe default: an unknown route underclaims as illustrative.
        self.assertIn("Illustrative", _source_badge("/some-unknown-route"))

    def test_every_badge_is_a_status_dot(self):
        # No empty badges anymore — every call yields an accessible dot.
        for route in ("/base-rates", "/platform-maturity", "/some-unknown-route"):
            badge = _source_badge(route)
            self.assertIn("tool-status-dot", badge)
            self.assertIn("aria-label=", badge)

    def test_page_renders_dots_and_legend(self):
        html = render_module_index({})
        self.assertIn("dir-trust-legend", html)
        self.assertIn('class="tool-status-dot"', html)
        self.assertIn(".tool-status-dot{", html)        # scoped CSS present
        self.assertIn("realized-deal corpus", html)
        # both a live and an illustrative module surface their label
        self.assertIn("Live", html)
        self.assertIn("Illustrative", html)


if __name__ == "__main__":
    unittest.main()
