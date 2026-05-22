"""The /module-index shows per-module data-source trust badges.

Each module is tagged LIVE (realized-deal corpus) / CMS (public data) /
ILLUSTRATIVE (representative template) per docs/PEDESK_UNDERSTANDING/08,
so a partner sees at a glance which surfaces are sourced vs templates.
Routes with an uncertain classification carry NO badge (honest silence
over a wrong label).
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
        # Unmapped / uncertain route → no badge (honest silence).
        self.assertEqual(_source_badge("/platform-maturity"), "")
        self.assertEqual(_source_badge("/some-unknown-route"), "")

    def test_page_renders_badges_and_legend(self):
        html = render_module_index({})
        self.assertIn("dir-trust-legend", html)
        self.assertIn('class="dir-src"', html)
        self.assertIn("realized-deal corpus", html)
        # a live and an illustrative module both surface their tag
        self.assertIn("Live", html)
        self.assertIn("Illustrative", html)


if __name__ == "__main__":
    unittest.main()
