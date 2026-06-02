"""Mobile-responsiveness guard for the shared chartis shell (2026-06).

A 390px-viewport audit found ~50 of ~51 sampled PE Desk pages forced
horizontal *page* scroll on phones, from systemic shared-shell causes:
the topbar never wrapped (~600px), wide data tables overflowed, the
viz|data pair blocks sat side-by-side, and provenance tooltip cards
(``visibility:hidden`` but still in layout, ``min-width:240px``) pushed
the page wide.

The fix is a single ``@media (max-width:640px)`` block in the shell CSS.
This test locks it in so the mobile rules can't be silently dropped, and
asserts they stay **scoped to ≤640px** so the desktop layout (the
product's primary target) is never affected.
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.ui._chartis_kit import chartis_shell


class MobileResponsiveShellTests(unittest.TestCase):
    def setUp(self):
        self.html = chartis_shell("<p>body</p>", title="Mobile Guard")

    def test_mobile_media_block_present(self):
        self.assertIn(
            "@media (max-width:640px)", self.html,
            "the ≤640px mobile block is missing from the shell CSS — "
            "phones will horizontally-scroll every page again.",
        )

    def test_key_mobile_rules_present(self):
        # Each systemic mobile fix must survive.
        for frag in (
            ".ck-topbar-inner{ flex-wrap:wrap",   # topbar wraps
            ".ck-nav{ flex-wrap:wrap",            # nav links wrap
            ".ck-pair{ grid-template-columns:1fr",  # viz|data stacks
            ".ck-prov-tt-card{ display:none",     # tooltip leaves layout
        ):
            self.assertIn(frag, self.html, f"missing mobile rule: {frag}")
        # wide tables scroll in place rather than widening the page
        self.assertTrue(
            re.search(r"\.ck-data-table[^}]*overflow-x:auto", self.html),
            "data tables must scroll-x on mobile",
        )

    def test_mobile_rules_are_scoped_to_small_screens(self):
        # The whole block must live inside the ≤640px media query — never
        # leak to desktop. Slice from the media query to its matching brace
        # depth and assert the rules live within that window.
        i = self.html.index("@media (max-width:640px)")
        # find the block body between the first '{' after the query and its
        # matching close brace
        start = self.html.index("{", i)
        depth, j = 0, start
        while j < len(self.html):
            if self.html[j] == "{":
                depth += 1
            elif self.html[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        block = self.html[start:j]
        self.assertIn(".ck-prov-tt-card{ display:none", block)
        self.assertIn(".ck-pair{ grid-template-columns:1fr", block)


if __name__ == "__main__":
    unittest.main()
