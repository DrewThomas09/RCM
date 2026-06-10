"""P12 — Cmd-K entity jump by CCN.

A 6-digit query in the command palette is a CMS CCN; the palette surfaces a
synthetic 'HCRIS X-Ray for CCN ######' result that routes straight to that
facility's X-Ray. Pure client-side (route built from the digits) — no backend
call, no 6,123-row entity list inlined. These tests pin the markup + JS the
client behaviour depends on (the live nav is verified separately by a headless
browser run).
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import chartis_shell, ck_command_palette


class EntityJumpMarkupTests(unittest.TestCase):
    def test_palette_carries_hidden_entity_jump_item(self):
        h = ck_command_palette([{"id": "x", "title": "X", "route": "/x"}])
        self.assertIn("data-entity-jump", h)
        self.assertIn("cp-entity-title", h)
        self.assertIn("cp-entity-route", h)
        # starts hidden + display:none so visibleItems() excludes it until a
        # CCN is typed.
        self.assertIn('hidden style="display:none"', h)

    def test_placeholder_advertises_ccn_jump(self):
        h = ck_command_palette([])
        self.assertIn("6-digit CCN", h)

    def test_js_builds_xray_route_from_six_digits(self):
        # The filter() handler must (a) recognise a /^\d{6}$/ query and
        # (b) build the X-Ray route from the digits.
        shell = chartis_shell("<p>x</p>", "T")
        self.assertIn("/^\\d{6}$/", shell)
        self.assertIn("/diligence/hcris-xray?ccn=", shell)
        self.assertIn("data-entity-jump", shell)

    def test_entity_item_excluded_from_text_filter_loop(self):
        # The static-item text filter must skip the synthetic row (it's driven
        # by the CCN branch, not text matching) — guard the early-continue.
        shell = chartis_shell("<p>x</p>", "T")
        self.assertIn("hasAttribute('data-entity-jump')", shell)


if __name__ == "__main__":
    unittest.main()
